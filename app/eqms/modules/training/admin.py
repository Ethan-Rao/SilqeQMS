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
    from app.eqms.modules.document_control.qms_index import classify, slq_family
    from app.eqms.modules.training.service import _doc_base

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

    total = len(assignments)
    acknowledged = sum(1 for a in assignments if a.acknowledged_at is not None)

    # Group document assignments that share an SLQ family (>= 2 items) under a
    # collapsible heading; everything else stays in a flat "ungrouped" section.
    fam_of: dict[int, int | None] = {}
    fam_counts: dict[int, int] = {}
    for a in assignments:
        fam = slq_family(a.document.doc_number) if (a.item_type == "document" and a.document) else None
        fam_of[a.id] = fam
        if fam is not None:
            fam_counts[fam] = fam_counts.get(fam, 0) + 1
    grouped_fams = {f for f, c in fam_counts.items() if c >= 2}

    groups: list[dict] = []
    group_map: dict[int, dict] = {}
    ungrouped: list = []
    for a in assignments:
        fam = fam_of[a.id]
        if fam in grouped_fams:
            g = group_map.get(fam)
            if g is None:
                base = _doc_base(a.document.doc_number)
                g = {"heading": f"{base} — {classify(a.document.doc_number).subsystem}", "assignments": []}
                group_map[fam] = g
                groups.append(g)
            g["assignments"].append(a)
        else:
            ungrouped.append(a)
    if ungrouped:
        groups.append({"heading": None, "assignments": ungrouped})

    return render_template(
        "admin/training/my_training.html",
        assignments=assignments,
        groups=groups,
        total=total,
        acknowledged=acknowledged,
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
        if a.document is not None and a.document_revision is not None:
            flash(f"Acknowledged: {a.document.title} Rev {a.document_revision.revision}.", "success")
        else:
            flash(f"Acknowledged: {a.item_title}.", "success")
    else:
        flash("This item was already acknowledged.", "info")
    return redirect(url_for("training.my_training"))


# --------------------------------------------------------------------------- #
# Admin: manage assignments across users
# --------------------------------------------------------------------------- #

@bp.get("/training")
@require_permission("training.manage")
def manage_index():
    from app.eqms.modules.training.service import _doc_base

    s = db_session()
    status_filter = (request.args.get("status") or "").strip()
    doc_number_filter = (request.args.get("doc_number") or "").strip()

    all_assignments = (
        s.query(TrainingAssignment)
        .order_by(
            TrainingAssignment.acknowledged_at.is_(None).desc(),
            TrainingAssignment.assigned_at.desc(),
        )
        .all()
    )
    today = date.today()

    # Per-user completion (acknowledged / total) computed across ALL assignments,
    # independent of the current filters.
    completion_by_user: dict[int, list[int]] = {}
    for a in all_assignments:
        stats = completion_by_user.setdefault(a.assigned_to_user_id, [0, 0])
        stats[1] += 1
        if a.acknowledged_at is not None:
            stats[0] += 1

    assignments = all_assignments
    if status_filter:
        assignments = [
            a for a in assignments if assignment_status(a, today)["state"] == status_filter
        ]
    if doc_number_filter:
        norm = _doc_base(doc_number_filter)
        assignments = [
            a
            for a in assignments
            if (a.item_type == "document" and a.document and _doc_base(a.document.doc_number) == norm)
            or norm in (a.item_title or "").upper()
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
        completion_by_user=completion_by_user,
        today=today,
        status_filter=status_filter,
        doc_number_filter=doc_number_filter,
        total=total,
        open_count=open_count,
        overdue_count=overdue_count,
    )


@bp.get("/training/export.csv")
@require_permission("training.manage")
def export_csv():
    import csv
    import io

    from flask import Response

    s = db_session()
    today = date.today()
    assignments = (
        s.query(TrainingAssignment)
        .order_by(TrainingAssignment.assigned_at.desc())
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["user_email", "document", "revision", "assigned_date", "due_date", "acknowledged_at", "status"]
    )
    for a in assignments:
        email = a.assignee.email if a.assignee else ""
        document = a.item_title or ""
        revision = a.document_revision.revision if a.document_revision else ""
        assigned_date = a.assigned_at.strftime("%Y-%m-%d") if a.assigned_at else ""
        due = a.due_date.isoformat() if a.due_date else ""
        ack = a.acknowledged_at.strftime("%Y-%m-%d %H:%M") if a.acknowledged_at else ""
        status = assignment_status(a, today)["state"]
        writer.writerow([email, document, revision, assigned_date, due, ack, status])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=training_assignments.csv"},
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
    bulk_doc_numbers = (request.form.get("bulk_doc_numbers") or "").strip()

    # Bulk-by-document-list mode: one document assignment per doc number per user,
    # each resolved to the document's current revision.
    if bulk_doc_numbers:
        from app.eqms.modules.training.service import resolve_current_revision

        if not user_ids:
            flash("Select at least one user to assign.", "danger")
            return redirect(url_for("training.new_get"))

        numbers = [ln.strip() for ln in bulk_doc_numbers.splitlines() if ln.strip()]
        created_total = 0
        matched_docs = 0
        unknown: list[str] = []
        try:
            for num in numbers:
                resolved = resolve_current_revision(s, num)
                if resolved is None:
                    unknown.append(num)
                    continue
                doc, rev = resolved
                matched_docs += 1
                created = create_assignments(
                    s,
                    item_type="document",
                    document_id=doc.id,
                    document_revision_id=rev.id if rev else None,
                    admin_doc_file_id=None,
                    free_text_title=None,
                    instructions=instructions,
                    user_ids=user_ids,
                    due_date=due_date,
                    actor=actor,
                )
                created_total += len(created)
        except Exception as e:  # noqa: BLE001
            s.rollback()
            current_app.logger.exception("Bulk training assignment failed: %s", e)
            flash(f"Could not create bulk assignments: {e}", "danger")
            return redirect(url_for("training.new_get"))

        s.commit()
        flash(
            f"Bulk assign: {created_total} assignment(s) created across {matched_docs} document(s) for {len(user_ids)} user(s).",
            "success" if created_total else "info",
        )
        if unknown:
            flash(f"Skipped {len(unknown)} unknown doc number(s): {', '.join(unknown)}", "warning")
        return redirect(url_for("training.manage_index"))

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
