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
from app.eqms.modules.training.models import EffectivenessReview, TrainingAssignment
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

    total = len(assignments)
    acknowledged = sum(1 for a in assignments if a.acknowledged_at is not None)

    # Two clear sections: pending (unacknowledged) and acknowledged (incl.
    # pre-acknowledged DCO / originator records). Pending sorted by due date;
    # acknowledged sorted most-recently-acknowledged first.
    pending_items = [a for a in assignments if a.acknowledged_at is None]
    acknowledged_items = sorted(
        (a for a in assignments if a.acknowledged_at is not None),
        key=lambda a: a.acknowledged_at,
        reverse=True,
    )

    return render_template(
        "admin/training/my_training.html",
        assignments=assignments,
        pending_items=pending_items,
        acknowledged_items=acknowledged_items,
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
    overdue_by_user: dict[int, int] = {}
    for a in all_assignments:
        stats = completion_by_user.setdefault(a.assigned_to_user_id, [0, 0])
        stats[1] += 1
        if a.acknowledged_at is not None:
            stats[0] += 1
        elif assignment_status(a, today)["state"] == "overdue":
            overdue_by_user[a.assigned_to_user_id] = overdue_by_user.get(a.assigned_to_user_id, 0) + 1

    # Per-user summary cards (one card per active user with any assignment).
    active_users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()
    users_by_id = {u.id: u for u in active_users}
    users_summary = []
    for uid, counts in completion_by_user.items():
        u = users_by_id.get(uid)
        if not u:
            continue
        users_summary.append({
            "user": u,
            "total": counts[1],
            "acknowledged": counts[0],
            "overdue": overdue_by_user.get(uid, 0),
        })
    users_summary.sort(key=lambda r: (r["user"].display_name or r["user"].email or "").lower())

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
        users_summary=users_summary,
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


def _cell_status(a: TrainingAssignment | None, today: date) -> str:
    """Reduce an assignment (or absence) to a matrix/record cell status."""
    if a is None:
        return "not_assigned"
    if a.acknowledged_at is not None:
        return "dco_qualified" if a.training_type == "dco_auto_qualified" else "acknowledged"
    return "overdue" if assignment_status(a, today)["state"] == "overdue" else "assigned"


def _best_assignment(assignments: list[TrainingAssignment]) -> TrainingAssignment | None:
    """Pick the most representative assignment: acknowledged (most recent) else open (most recent)."""
    if not assignments:
        return None
    acked = [a for a in assignments if a.acknowledged_at is not None]
    if acked:
        return max(acked, key=lambda a: a.acknowledged_at)
    return max(assignments, key=lambda a: a.assigned_at)


@bp.get("/training/user/<int:user_id>")
@require_permission("training.manage")
def user_training(user_id: int):
    from app.eqms.modules.training.service import (
        MATRIX_CATEGORIES,
        _doc_base,
        matrix_required_for_doc_numbers,
        resolve_current_revision,
    )

    s = db_session()
    today = date.today()
    user = s.get(User, user_id)
    if not user or not user.is_active:
        abort(404)

    assignments = (
        s.query(TrainingAssignment)
        .filter(TrainingAssignment.assigned_to_user_id == user_id)
        .order_by(
            TrainingAssignment.acknowledged_at.is_(None).desc(),
            TrainingAssignment.acknowledged_at.desc(),
        )
        .all()
    )
    reviews = (
        s.query(EffectivenessReview)
        .filter(EffectivenessReview.user_id == user_id)
        .order_by(EffectivenessReview.review_year.desc())
        .all()
    )

    # Index this user's document assignments by base doc number.
    by_doc_base: dict[str, list[TrainingAssignment]] = {}
    for a in assignments:
        if a.item_type == "document" and a.document:
            by_doc_base.setdefault(_doc_base(a.document.doc_number), []).append(a)

    required = set(matrix_required_for_doc_numbers(user.email))

    # Build category-grouped rows for the required-training table.
    categories = []
    ack_count = 0
    for cat_label, doc_numbers in MATRIX_CATEGORIES:
        rows = []
        for dn in doc_numbers:
            if dn not in required:
                continue
            resolved = resolve_current_revision(s, dn)
            doc = resolved[0] if resolved else None
            rev = resolved[1] if resolved else None
            base = _doc_base(dn)
            a = _best_assignment(by_doc_base.get(base, []))
            status = _cell_status(a, today)
            if status in ("acknowledged", "dco_qualified"):
                ack_count += 1
            rows.append({
                "doc_number": dn,
                "doc": doc,
                "rev_label": (rev.revision if rev else None),
                "assignment": a,
                "status": status,
            })
        if rows:
            categories.append({"label": cat_label, "rows": rows})

    required_count = len(required)

    return render_template(
        "admin/training/user_detail.html",
        user=user,
        categories=categories,
        reviews=reviews,
        required_count=required_count,
        acknowledged_count=ack_count,
        today=today,
    )


@bp.get("/training/matrix")
@require_permission("training.manage")
def training_matrix():
    from app.eqms.modules.training.service import (
        MATRIX,
        MATRIX_CATEGORIES,
        _doc_base,
        resolve_current_revision,
    )

    s = db_session()
    today = date.today()
    users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()

    # Index all document assignments by (user_id, base doc number).
    all_assignments = (
        s.query(TrainingAssignment)
        .filter(TrainingAssignment.item_type == "document")
        .all()
    )
    by_user_doc: dict[tuple[int, str], list[TrainingAssignment]] = {}
    for a in all_assignments:
        if a.document:
            key = (a.assigned_to_user_id, _doc_base(a.document.doc_number))
            by_user_doc.setdefault(key, []).append(a)

    def _email_required(user, doc_number: str) -> bool:
        fragments = MATRIX.get(doc_number, [])
        if "all" in fragments:
            return True
        email = (user.email or "").lower()
        return any(f in email for f in fragments)

    categories = []
    for cat_label, doc_numbers in MATRIX_CATEGORIES:
        rows = []
        for dn in doc_numbers:
            resolved = resolve_current_revision(s, dn)
            doc = resolved[0] if resolved else None
            base = _doc_base(dn)
            cells = {}
            for u in users:
                if not _email_required(u, dn):
                    cells[u.id] = "not_required"
                    continue
                a = _best_assignment(by_user_doc.get((u.id, base), []))
                cells[u.id] = _cell_status(a, today)
            rows.append({
                "doc_number": dn,
                "doc_title": (doc.title if doc else None),
                "doc": doc,
                "cells": cells,
            })
        categories.append({"label": cat_label, "rows": rows})

    return render_template(
        "admin/training/matrix.html",
        users=users,
        categories=categories,
        today=today,
    )


@bp.get("/training/effectiveness")
@require_permission("training.manage")
def effectiveness_index():
    s = db_session()
    reviews = (
        s.query(EffectivenessReview)
        .order_by(EffectivenessReview.review_year.desc(), EffectivenessReview.review_date.desc())
        .all()
    )
    users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()
    return render_template("admin/training/effectiveness.html", reviews=reviews, users=users)


@bp.post("/training/effectiveness/create")
@require_permission("training.manage")
def effectiveness_create():
    from app.eqms.audit import record_event

    s = db_session()
    actor = _current_user()

    try:
        user_id = int(request.form.get("user_id") or 0)
    except (TypeError, ValueError):
        user_id = 0
    try:
        review_year = int(request.form.get("review_year") or 0)
    except (TypeError, ValueError):
        review_year = 0
    if not user_id or not review_year:
        flash("Employee and review year are required.", "danger")
        return redirect(url_for("training.effectiveness_index"))

    user = s.get(User, user_id)
    if not user:
        flash("Selected employee was not found.", "danger")
        return redirect(url_for("training.effectiveness_index"))

    review_date = parse_date(request.form.get("review_date"))
    score = None
    score_s = (request.form.get("score") or "").strip()
    if score_s:
        try:
            score = float(score_s)
        except ValueError:
            score = None
    # Pass/fail: explicit field if present, else derived from score (>= 7 of 10).
    passed_field = (request.form.get("passed") or "").strip().lower()
    if passed_field in ("1", "true", "pass", "yes", "on"):
        passed = True
    elif passed_field in ("0", "false", "fail", "no"):
        passed = False
    else:
        passed = bool(score is not None and score >= 7.0)
    notes = (request.form.get("notes") or "").strip() or None

    review = EffectivenessReview(
        user_id=user_id,
        review_year=review_year,
        review_date=review_date,
        score=score,
        passed=passed,
        notes=notes,
        reviewed_by_user_id=actor.id if actor else None,
    )
    s.add(review)
    s.flush()
    record_event(
        s, actor=actor, action="training.effectiveness_review.create",
        entity_type="EffectivenessReview", entity_id=str(review.id),
        metadata={"user_id": user_id, "review_year": review_year, "passed": passed},
    )
    s.commit()
    flash("Effectiveness review added.", "success")
    return redirect(url_for("training.effectiveness_index"))


@bp.post("/training/effectiveness/<int:review_id>/delete")
@require_permission("training.manage")
def effectiveness_delete(review_id: int):
    from app.eqms.audit import record_event

    s = db_session()
    actor = _current_user()
    review = s.get(EffectivenessReview, review_id)
    if not review:
        abort(404)
    record_event(
        s, actor=actor, action="training.effectiveness_review.delete",
        entity_type="EffectivenessReview", entity_id=str(review_id),
        metadata={"user_id": review.user_id, "review_year": review.review_year},
    )
    s.delete(review)
    s.commit()
    flash("Effectiveness review removed.", "success")
    return redirect(url_for("training.effectiveness_index"))


@bp.get("/training/dco-qualify")
@require_permission("training.manage")
def dco_qualify_get():
    s = db_session()
    from app.eqms.modules.document_control.models import Document

    users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()
    documents = s.query(Document).order_by(Document.doc_number.asc()).all()
    return render_template(
        "admin/training/dco_qualify.html",
        users=users,
        documents=documents,
        today=date.today(),
    )


@bp.post("/training/dco-qualify")
@require_permission("training.manage")
def dco_qualify_post():
    from datetime import datetime

    from app.eqms.modules.training.service import resolve_current_revision

    s = db_session()
    actor = _current_user()

    dco_number = (request.form.get("dco_number") or "").strip()
    docs_raw = (request.form.get("doc_numbers") or "").strip()
    approval_date_s = (request.form.get("approval_date") or "").strip()
    approver_ids = [int(x) for x in request.form.getlist("approver_ids") if x.strip().isdigit()]

    if not dco_number:
        flash("DCO Number is required.", "danger")
        return redirect(url_for("training.dco_qualify_get"))
    if not docs_raw:
        flash("Enter at least one document number.", "danger")
        return redirect(url_for("training.dco_qualify_get"))
    if not approver_ids:
        flash("Select at least one approver.", "danger")
        return redirect(url_for("training.dco_qualify_get"))
    approval_date = parse_date(approval_date_s)
    if not approval_date:
        flash("A valid DCO approval date is required.", "danger")
        return redirect(url_for("training.dco_qualify_get"))

    acknowledged_at = datetime(approval_date.year, approval_date.month, approval_date.day, 12, 0, 0)
    # Split on commas and newlines.
    numbers = [n.strip() for n in docs_raw.replace("\n", ",").split(",") if n.strip()]

    created_total = 0
    unknown: list[str] = []
    try:
        for num in numbers:
            resolved = resolve_current_revision(s, num)
            if resolved is None:
                unknown.append(num)
                continue
            doc, rev = resolved
            created = create_assignments(
                s,
                item_type="document",
                document_id=doc.id,
                document_revision_id=rev.id if rev else None,
                admin_doc_file_id=None,
                free_text_title=None,
                instructions=None,
                user_ids=approver_ids,
                due_date=None,
                actor=actor,
                training_type="dco_auto_qualified",
                source_reference=dco_number,
                acknowledged_at=acknowledged_at,
            )
            created_total += len(created)
    except Exception as e:  # noqa: BLE001
        s.rollback()
        current_app.logger.exception("DCO batch qualification failed: %s", e)
        flash(f"Could not record DCO qualification: {e}", "danger")
        return redirect(url_for("training.dco_qualify_get"))

    s.commit()
    flash(f"Created {created_total} DCO qualification record(s) for {dco_number}.", "success" if created_total else "info")
    if unknown:
        flash(f"Skipped {len(unknown)} unknown doc number(s): {', '.join(unknown)}", "warning")
    return redirect(url_for("training.manage_index"))


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

    # Training-type / source / backdated-acknowledgement (QM.SLQ053 §5.4, §8).
    training_type = (request.form.get("training_type") or "read_acknowledge").strip()
    source_reference = (request.form.get("source_reference") or "").strip() or None
    acknowledged_date_s = (request.form.get("acknowledged_date") or "").strip()
    acknowledged_at = None
    if acknowledged_date_s:
        from datetime import datetime

        d = parse_date(acknowledged_date_s)
        if d:
            acknowledged_at = datetime(d.year, d.month, d.day, 12, 0, 0)

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
                    training_type=training_type,
                    source_reference=source_reference,
                    acknowledged_at=acknowledged_at,
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
            training_type=training_type,
            source_reference=source_reference,
            acknowledged_at=acknowledged_at,
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
