from __future__ import annotations

from datetime import date

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.training.models import TrainingAssignment
from app.eqms.modules.training.service import (
    acknowledge_assignment,
    assignment_status,
    create_assignments,
    document_revision_status,
    parse_date,
)
from app.eqms.rbac import require_permission
from app.eqms.utils import current_user as _current_user

bp = Blueprint("training", __name__)


# --------------------------------------------------------------------------- #
# Staff / self-service: My Training
# --------------------------------------------------------------------------- #

@bp.get("/my-training")
@require_permission("training.view")
def my_training():
    s = db_session()
    u = _current_user()
    assignments = (
        s.query(TrainingAssignment)
        .filter(TrainingAssignment.assigned_to_user_id == u.id)
        .order_by(
            TrainingAssignment.acknowledged_at.is_(None).desc(),
            TrainingAssignment.due_date.is_(None),
            TrainingAssignment.due_date.asc(),
            TrainingAssignment.assigned_at.desc(),
        )
        .all()
    )
    return render_template(
        "admin/training/my_training.html",
        assignments=assignments,
        assignment_status=assignment_status,
        document_revision_status=document_revision_status,
        today=date.today(),
    )


@bp.post("/my-training/<int:assignment_id>/acknowledge")
@require_permission("training.view")
def my_training_acknowledge(assignment_id: int):
    s = db_session()
    u = _current_user()
    a = s.get(TrainingAssignment, assignment_id)
    if not a:
        abort(404)
    # Ownership: a user may only acknowledge their OWN item. Never another user's.
    if a.assigned_to_user_id != u.id:
        abort(403)

    changed = acknowledge_assignment(s, a, u)
    s.commit()
    if changed:
        flash(f"Acknowledged: {a.item_title}", "success")
    else:
        flash("This item was already acknowledged.", "info")
    return redirect(url_for("training.my_training"))


# --------------------------------------------------------------------------- #
# Admin: manage assignments across users
# --------------------------------------------------------------------------- #

@bp.get("/training")
@require_permission("training.manage")
def manage_index():
    s = db_session()
    status_filter = (request.args.get("status") or "").strip()

    assignments = (
        s.query(TrainingAssignment)
        .order_by(
            TrainingAssignment.acknowledged_at.is_(None).desc(),
            TrainingAssignment.assigned_at.desc(),
        )
        .all()
    )
    today = date.today()
    if status_filter:
        assignments = [
            a for a in assignments if assignment_status(a, today)["state"] == status_filter
        ]

    total = len(assignments)
    open_count = sum(1 for a in assignments if a.acknowledged_at is None)
    overdue_count = sum(
        1 for a in assignments if assignment_status(a, today)["state"] == "overdue"
    )

    return render_template(
        "admin/training/manage.html",
        assignments=assignments,
        assignment_status=assignment_status,
        today=today,
        status_filter=status_filter,
        total=total,
        open_count=open_count,
        overdue_count=overdue_count,
    )


@bp.get("/training/new")
@require_permission("training.manage")
def new_get():
    s = db_session()
    from app.eqms.modules.document_control.dco_log import rev_order_key
    from app.eqms.modules.document_control.models import Document
    from app.eqms.modules.admin_docs.models import AdminDocFile

    documents = s.query(Document).order_by(Document.doc_number.asc()).all()
    library_files = s.query(AdminDocFile).order_by(AdminDocFile.library_key.asc(), AdminDocFile.filename.asc()).all()
    users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()

    # Revisions per document (newest-first) for the revision picker; current
    # revision is flagged so the form can default to it.
    revisions_by_doc: dict[int, list[dict]] = {}
    for d in documents:
        revs = sorted(d.revisions, key=lambda r: rev_order_key(r.revision), reverse=True)
        revisions_by_doc[d.id] = [
            {"id": r.id, "label": r.revision, "current": (d.current_revision_id == r.id)}
            for r in revs
        ]

    return render_template(
        "admin/training/new.html",
        documents=documents,
        library_files=library_files,
        users=users,
        revisions_by_doc=revisions_by_doc,
        today=date.today(),
    )


@bp.post("/training/new")
@require_permission("training.manage")
def new_post():
    s = db_session()
    actor = _current_user()

    item_type = (request.form.get("item_type") or "").strip()
    document_id = request.form.get("document_id") or None
    document_revision_id = request.form.get("document_revision_id") or None
    admin_doc_file_id = request.form.get("admin_doc_file_id") or None
    free_text_title = request.form.get("free_text_title")
    instructions = request.form.get("instructions")
    due_date = parse_date(request.form.get("due_date"))
    user_ids = [int(x) for x in request.form.getlist("user_ids") if x.strip().isdigit()]

    try:
        created = create_assignments(
            s,
            item_type=item_type,
            document_id=int(document_id) if document_id else None,
            document_revision_id=int(document_revision_id) if document_revision_id else None,
            admin_doc_file_id=int(admin_doc_file_id) if admin_doc_file_id else None,
            free_text_title=free_text_title,
            instructions=instructions,
            user_ids=user_ids,
            due_date=due_date,
            actor=actor,
        )
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("training.new_get"))
    except Exception as e:  # noqa: BLE001
        s.rollback()
        current_app.logger.exception("Training assignment failed: %s", e)
        flash(f"Could not create assignments: {e}", "danger")
        return redirect(url_for("training.new_get"))

    s.commit()
    flash(
        f"Assigned to {len(created)} user(s)."
        + ("" if created else " (No new assignments — those users already had this open item.)"),
        "success" if created else "info",
    )
    return redirect(url_for("training.manage_index"))


@bp.post("/training/<int:assignment_id>/delete")
@require_permission("training.manage")
def delete_assignment(assignment_id: int):
    from app.eqms.audit import record_event

    s = db_session()
    actor = _current_user()
    a = s.get(TrainingAssignment, assignment_id)
    if not a:
        abort(404)
    title = a.item_title
    record_event(
        s,
        actor=actor,
        action="training.unassign",
        entity_type="TrainingAssignment",
        entity_id=str(a.id),
        metadata={"item_title": a.item_title, "assigned_to_user_id": a.assigned_to_user_id},
    )
    s.delete(a)
    s.commit()
    flash(f"Removed assignment: {title}", "success")
    return redirect(url_for("training.manage_index"))
