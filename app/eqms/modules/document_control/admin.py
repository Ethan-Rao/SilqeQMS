from __future__ import annotations

from datetime import datetime

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy.orm import Session

from app.eqms.audit import record_event
from app.eqms.db import db_session
from app.eqms.document_viewer import needs_server_render, render_document_to_response
from app.eqms.models import User
from app.eqms.modules.document_control.models import Document, DocumentFile, DocumentRevision
from app.eqms.modules.document_control.service import (
    file_digest_and_bytes,
    next_revision,
    normalize_doc_number,
    parse_effective_date,
    sanitize_upload_filename,
)
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config
from app.eqms.utils import allow_inline_view, current_user as _current_user, utcnow

bp = Blueprint("doc_control", __name__)


# Ordered subsystem list for the QM Documents browse view (Prompt 20). Tunable
# here without touching the classification map. Any subsystem returned by
# classify() that is missing from this list is appended just before
# "Unclassified" (which stays pinned last).
BROWSE_SUBSYSTEM_ORDER = [
    "Production & Service",
    "Equipment & Calibration",
    "Purchasing & Suppliers",
    "Nonconforming Material",
    "CAPA",
    "Post-Market",
    "Audits",
    "Management",
    "Quality Planning",
    "Training",
    "Design Control",
    "Risk Management",
    "Document Control",
    "Sales & Customer",
    "Regulatory",
    "Administration Forms",
    "Unclassified",
]

# doc_type values that are children of a parent SOP/WI/Policy.
_BROWSE_CHILD_TYPES = {"Form", "Template", "Traveler"}


def _get_doc_or_404(s: Session, doc_id: int) -> Document:
    d = s.get(Document, doc_id)
    if not d:
        from flask import abort

        abort(404)
    return d


def _get_rev_or_404(s: Session, rev_id: int) -> DocumentRevision:
    r = s.get(DocumentRevision, rev_id)
    if not r:
        from flask import abort

        abort(404)
    return r


UNCATEGORIZED_LABEL = "Uncategorized"


@bp.get("/")
@require_permission("docs.view")
def list_documents():
    """
    Browse controlled documents grouped by category (subsystem).

    Query params:
      - q: case-insensitive match on doc_number or title
      - category: restrict to a single category
      - show_obsolete: "1" to include Obsolete documents (hidden by default)
    """
    s = db_session()

    q = (request.args.get("q") or "").strip()
    category_filter = (request.args.get("category") or "").strip()
    type_filter = (request.args.get("doc_type") or "").strip()
    status_filter = (request.args.get("status") or "").strip()
    show_obsolete = (request.args.get("show_obsolete") or "").strip() == "1"

    query = s.query(Document)
    if status_filter:
        query = query.filter(Document.status == status_filter)
    elif not show_obsolete:
        query = query.filter(Document.status != "Obsolete")
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(
            (Document.doc_number.ilike(like)) | (Document.title.ilike(like))
        )
    if category_filter:
        if category_filter == UNCATEGORIZED_LABEL:
            query = query.filter(Document.category.is_(None))
        else:
            query = query.filter(Document.category == category_filter)
    if type_filter:
        query = query.filter(Document.doc_type == type_filter)

    docs = query.order_by(Document.doc_number.asc()).all()

    # Group for the browse view (category -> list of documents).
    grouped: dict[str, list[Document]] = {}
    for d in docs:
        key = d.category or UNCATEGORIZED_LABEL
        grouped.setdefault(key, []).append(d)
    grouped_sorted = dict(sorted(grouped.items(), key=lambda kv: kv[0].lower()))

    # Filter control vocabularies (independent of the current filter).
    all_categories = sorted(
        {
            (row[0] or UNCATEGORIZED_LABEL)
            for row in s.query(Document.category).distinct().all()
        },
        key=lambda c: c.lower(),
    )
    all_doc_types = sorted(
        {row[0] for row in s.query(Document.doc_type).distinct().all() if row[0]},
        key=lambda c: c.lower(),
    )
    all_statuses = ["Draft", "Released", "Obsolete"]

    # Distinguish "nothing exists yet" from "nothing matches the filters".
    has_any_documents = s.query(Document.id).first() is not None
    has_active_filters = bool(q or category_filter or type_filter or status_filter)

    return render_template(
        "admin/modules/document_control/list.html",
        documents=docs,
        grouped=grouped_sorted,
        all_categories=all_categories,
        all_doc_types=all_doc_types,
        all_statuses=all_statuses,
        q=q,
        category_filter=category_filter,
        type_filter=type_filter,
        status_filter=status_filter,
        show_obsolete=show_obsolete,
        total_count=len(docs),
        has_any_documents=has_any_documents,
        has_active_filters=has_active_filters,
        uncategorized_label=UNCATEGORIZED_LABEL,
    )


@bp.get("/index")
@require_permission("docs.view")
def qms_index():
    """QMS Document Index: navigate the controlled set by ISO 13485 clause or
    by QMS subsystem. Read-only; reuses existing Document data + the maintainable
    qms_index mapping. Obsolete hidden by default (matches the list toggle)."""
    from app.eqms.modules.document_control.qms_index import UNCLASSIFIED, classify

    s = db_session()
    show_obsolete = (request.args.get("show_obsolete") or "").strip() == "1"
    group_mode = (request.args.get("group") or "clause").strip().lower()
    if group_mode not in ("clause", "subsystem"):
        group_mode = "clause"

    query = s.query(Document)
    if not show_obsolete:
        query = query.filter(Document.status != "Obsolete")
    docs = query.order_by(Document.doc_number.asc()).all()

    grouped: dict[str, list[Document]] = {}
    mapped_count = 0
    for d in docs:
        c = classify(d.doc_number)
        if c.subsystem != UNCLASSIFIED:
            mapped_count += 1
        key = (c.iso_clause if group_mode == "clause" else c.subsystem) or UNCLASSIFIED
        grouped.setdefault(key, []).append(d)

    # Buckets alpha-sorted, with the "Unclassified" gap bucket pinned last.
    def _bucket_key(k: str):
        return (1, "") if k == UNCLASSIFIED else (0, k.lower())

    grouped_sorted = dict(sorted(grouped.items(), key=lambda kv: _bucket_key(kv[0])))

    return render_template(
        "admin/modules/document_control/qms_index.html",
        grouped=grouped_sorted,
        group_mode=group_mode,
        show_obsolete=show_obsolete,
        total_count=len(docs),
        mapped_count=mapped_count,
        unclassified_label=UNCLASSIFIED,
    )


@bp.get("/browse")
@require_permission("docs.view")
def browse():
    """User-friendly browse view of the active controlled document set (Prompt 20).

    Groups Released documents by QMS subsystem (accordion), nesting child
    forms/templates/travelers under their parent SOP by shared SLQ family.
    Administration forms (AD.* blank templates) from the forms_templates_travelers
    admin_docs library are surfaced in the "Administration Forms" section.
    Read-only; every link opens an existing docs.view-gated detail/viewer route.
    """
    from collections import defaultdict

    from sqlalchemy.orm import selectinload

    from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
    from app.eqms.modules.document_control.qms_index import (
        UNCLASSIFIED,
        classify,
        slq_family,
    )

    s = db_session()

    docs = (
        s.query(Document)
        .options(selectinload(Document.current_revision))
        .filter(Document.status == "Released")
        .order_by(Document.doc_number.asc())
        .all()
    )

    # Split each subsystem into parent SOPs vs child forms/templates/travelers.
    buckets: dict[str, dict[str, list[Document]]] = defaultdict(
        lambda: {"parents": [], "children": []}
    )
    for d in docs:
        sub = classify(d.doc_number).subsystem
        role = "children" if (d.doc_type or "") in _BROWSE_CHILD_TYPES else "parents"
        buckets[sub][role].append(d)

    subsys_data: dict[str, dict] = {}
    for sub, b in buckets.items():
        parents, children = b["parents"], b["children"]

        parent_by_fam: dict[int, Document] = {}
        for p in parents:
            fam = slq_family(p.doc_number)
            if fam is not None:
                parent_by_fam.setdefault(fam, p)

        groups = {id(p): {"parent": p, "children": []} for p in parents}
        other: list[Document] = []
        for c in children:
            fam = slq_family(c.doc_number)
            parent = parent_by_fam.get(fam) if fam is not None else None
            if parent is not None:
                groups[id(parent)]["children"].append(c)
            else:
                other.append(c)

        group_list = list(groups.values())
        for g in group_list:
            g["children"].sort(key=lambda x: x.doc_number)
        # Most-used workflows first (most children), then by SLQ family ascending.
        group_list.sort(
            key=lambda g: (-len(g["children"]), slq_family(g["parent"].doc_number) or 9999)
        )
        other.sort(key=lambda x: x.doc_number)

        subsys_data[sub] = {
            "name": sub,
            "groups": group_list,
            "other": other,
            "admin_files": [],
            "count": len(parents) + len(children),
        }

    # Administration forms (blank AD.* templates) from the admin_docs library.
    # Skip anything inside a folder whose name contains "Completed" (filled records).
    folder_map = {
        f.id: f
        for f in s.query(AdminDocFolder)
        .filter(AdminDocFolder.library_key == "forms_templates_travelers")
        .all()
    }

    def _in_completed(folder_id: int | None) -> bool:
        seen: set[int] = set()
        fid = folder_id
        while fid is not None and fid not in seen:
            seen.add(fid)
            fol = folder_map.get(fid)
            if fol is None:
                break
            if "completed" in (fol.name or "").lower():
                return True
            fid = fol.parent_id
        return False

    admin_files = []
    for f in (
        s.query(AdminDocFile)
        .filter(AdminDocFile.library_key == "forms_templates_travelers")
        .order_by(AdminDocFile.filename.asc())
        .all()
    ):
        if _in_completed(f.folder_id):
            continue
        fol = folder_map.get(f.folder_id) if f.folder_id else None
        admin_files.append({"file": f, "folder_name": fol.name if fol else ""})

    if admin_files:
        entry = subsys_data.setdefault(
            "Administration Forms",
            {"name": "Administration Forms", "groups": [], "other": [], "admin_files": [], "count": 0},
        )
        entry["admin_files"] = admin_files
        entry["count"] += len(admin_files)

    # Order subsystems: configured order, extras (alpha) appended before Unclassified.
    known = [x for x in BROWSE_SUBSYSTEM_ORDER if x != UNCLASSIFIED]
    extras = sorted(set(subsys_data) - set(BROWSE_SUBSYSTEM_ORDER))
    final_order = known + extras + [UNCLASSIFIED]

    subsystems = [
        subsys_data[name]
        for name in final_order
        if name in subsys_data and subsys_data[name]["count"] > 0
    ]
    total_count = sum(sd["count"] for sd in subsystems)

    return render_template(
        "admin/modules/document_control/browse.html",
        subsystems=subsystems,
        total_count=total_count,
    )


@bp.get("/dco-log")
@require_permission("docs.view")
def dco_log_view():
    """In-app DCO Log / change-history view over DCO_Log_v2.csv (read-only).
    Filters: dco, document_number, and free-text q. Empty-state if CSV absent."""
    from app.eqms.modules.document_control.dco_log import load_rows, rev_order_key

    s = db_session()
    rows = load_rows()

    dco_filter = (request.args.get("dco") or "").strip()
    docnum_filter = (request.args.get("document_number") or "").strip()
    q = (request.args.get("q") or "").strip()

    def _match(r) -> bool:
        if dco_filter and dco_filter.lower() not in r.dco_number.lower():
            return False
        if docnum_filter and docnum_filter.lower() not in r.document_number.lower():
            return False
        if q:
            hay = " ".join((r.document_number, r.document_title, r.change_description)).lower()
            if q.lower() not in hay:
                return False
        return True

    filtered = [r for r in rows if _match(r)]
    # Default sort: DCO number descending, then target revision (rev_order_key).
    filtered.sort(key=lambda r: (r.dco_number, rev_order_key(r.to_rev)), reverse=True)

    # doc_number (upper) -> id, for back-links into Document Control detail.
    doc_ids = {
        (dn or "").strip().upper(): did
        for did, dn in s.query(Document.id, Document.doc_number).all()
    }

    return render_template(
        "admin/modules/document_control/dco_log.html",
        rows=filtered,
        total_rows=len(rows),
        doc_ids=doc_ids,
        dco_filter=dco_filter,
        docnum_filter=docnum_filter,
        q=q,
    )


@bp.get("/new")
@require_permission("docs.create")
def new_document_get():
    return render_template("admin/modules/document_control/new.html")


@bp.post("/new")
@require_permission("docs.create")
def new_document_post():
    s = db_session()
    u = _current_user()

    doc_number = normalize_doc_number(request.form.get("doc_number") or "")
    title = (request.form.get("title") or "").strip()
    doc_type = (request.form.get("doc_type") or "").strip()
    category = (request.form.get("category") or "").strip() or None

    if not doc_number or not title or not doc_type:
        flash("doc_number, title, and doc_type are required.", "danger")
        return redirect(url_for("doc_control.new_document_get"))

    exists = s.query(Document).filter(Document.doc_number == doc_number).one_or_none()
    if exists:
        flash("Document number already exists.", "danger")
        return redirect(url_for("doc_control.new_document_get"))

    d = Document(
        doc_number=doc_number,
        title=title,
        doc_type=doc_type,
        category=category,
        owner_user_id=u.id,
        status="Draft",
    )
    s.add(d)
    s.flush()

    # Create initial draft revision
    r = DocumentRevision(
        document_id=d.id,
        revision="A",
        change_summary="",
        effective_date=None,
        created_by_user_id=u.id,
        released_at=None,
        released_by_user_id=None,
    )
    s.add(r)
    s.flush()
    d.current_revision_id = r.id

    record_event(
        s,
        actor=u,
        action="doc.create",
        entity_type="Document",
        entity_id=str(d.id),
        metadata={"doc_number": d.doc_number, "revision": r.revision, "category": d.category},
    )
    s.commit()

    flash("Document created (Draft).", "success")
    return redirect(url_for("doc_control.document_detail", doc_id=d.id))


@bp.get("/<int:doc_id>")
@require_permission("docs.view")
def document_detail(doc_id: int):
    import re

    from app.eqms.models import AuditEvent
    from app.eqms.modules.document_control.dco_log import change_by_revision, rev_order_key
    from app.eqms.modules.document_control.qms_index import slq_family

    s = db_session()
    d = _get_doc_or_404(s, doc_id)

    obsolete_reason = None
    if d.status == "Obsolete":
        evt = (
            s.query(AuditEvent)
            .filter(
                AuditEvent.action == "doc.obsolete",
                AuditEvent.entity_type == "Document",
                AuditEvent.entity_id == str(d.id),
            )
            .order_by(AuditEvent.created_at.desc())
            .first()
        )
        if evt:
            obsolete_reason = evt.reason

    # Full lineage newest-first, robust to import timestamps (order by revision).
    revisions_desc = sorted(d.revisions, key=lambda r: rev_order_key(r.revision), reverse=True)
    current_id = d.current_revision.id if d.current_revision else None

    # DCO reference + change description per revision from the consolidated log.
    dco_by_rev = change_by_revision(d.doc_number)

    # For each revision, the label of the next-higher revision that superseded it.
    superseded_by: dict[int, str] = {}
    newer_label: str | None = None
    for r in revisions_desc:  # newest -> oldest
        if newer_label is not None:
            superseded_by[r.id] = newer_label
        newer_label = r.revision

    # Related documents: other controlled docs sharing this SLQ family (parent
    # SOP + its forms/templates/travelers). Obsolete hidden by default.
    related_docs: list[Document] = []
    fam = slq_family(d.doc_number)
    if fam is not None:
        candidates = (
            s.query(Document)
            .filter(Document.id != d.id, Document.status != "Obsolete")
            .all()
        )
        related_docs = [c for c in candidates if slq_family(c.doc_number) == fam]
        # Parent SOP first (no FM/TMP prefix), then forms/templates by number.
        related_docs.sort(
            key=lambda c: (1 if re.match(r"^(FM|TMP)", c.doc_number.upper()) else 0, c.doc_number)
        )

    # P38 B2: release-form DCO approver checkbox list. Real employees only
    # (active + display_name set); pre-check users required per the training matrix.
    from app.eqms.models import User as _User
    from app.eqms.modules.training.service import matrix_users_for_doc

    release_users = (
        s.query(_User)
        .filter(_User.is_active.is_(True), _User.display_name.isnot(None))
        .order_by(_User.display_name.asc())
        .all()
    )
    release_prechecked_ids = {u.id for u in matrix_users_for_doc(s, d.doc_number)}

    return render_template(
        "admin/modules/document_control/detail.html",
        document=d,
        obsolete_reason=obsolete_reason,
        revisions_desc=revisions_desc,
        current_revision_id=current_id,
        dco_by_rev=dco_by_rev,
        superseded_by=superseded_by,
        related_docs=related_docs,
        release_users=release_users,
        release_prechecked_ids=release_prechecked_ids,
    )


@bp.post("/<int:doc_id>/revisions/<int:rev_id>/upload")
@require_permission("docs.edit")
def upload_file(doc_id: int, rev_id: int):
    s = db_session()
    u = _current_user()

    d = _get_doc_or_404(s, doc_id)
    r = _get_rev_or_404(s, rev_id)

    if r.document_id != d.id:
        from flask import abort

        abort(404)

    if d.status != "Draft":
        flash("Files can only be uploaded while the document is Draft.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    if r.released_at is not None:
        flash("Cannot upload to a released revision.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    if r.files:
        flash("This draft revision already has a file. Create a new revision instead.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Choose a file to upload.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    filename = sanitize_upload_filename(f.filename)
    content_type = (f.mimetype or "application/octet-stream").strip()
    data = f.read()
    sha256, size_bytes = file_digest_and_bytes(data)

    storage_key = f"documents/{d.doc_number}/rev-{r.revision}/{filename}"
    from flask import current_app

    storage = storage_from_config(current_app.config)

    storage.put_bytes(storage_key, data, content_type=content_type)

    df = DocumentFile(
        revision_id=r.id,
        storage_key=storage_key,
        filename=filename,
        content_type=content_type,
        sha256=sha256,
        size_bytes=size_bytes,
        uploaded_by_user_id=u.id,
    )
    s.add(df)

    record_event(
        s,
        actor=u,
        action="doc.upload",
        entity_type="DocumentRevision",
        entity_id=str(r.id),
        metadata={
            "doc_id": d.id,
            "doc_number": d.doc_number,
            "revision": r.revision,
            "filename": filename,
            "sha256": sha256,
            "size_bytes": size_bytes,
        },
    )
    s.commit()
    flash("File uploaded.", "success")
    return redirect(url_for("doc_control.document_detail", doc_id=d.id))


@bp.post("/<int:doc_id>/revisions/<int:rev_id>/release")
@require_permission("docs.release")
def release_revision(doc_id: int, rev_id: int):
    s = db_session()
    u = _current_user()

    d = _get_doc_or_404(s, doc_id)
    r = _get_rev_or_404(s, rev_id)
    if r.document_id != d.id:
        from flask import abort

        abort(404)

    if d.status != "Draft":
        flash("Only Draft documents can be released.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))
    if r.released_at is not None:
        flash("Revision already released.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    reason = (request.form.get("reason") or "").strip()
    change_summary = (request.form.get("change_summary") or "").strip()
    eff = parse_effective_date(request.form.get("effective_date"))

    if not reason:
        flash("Release requires a reason.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))
    if not r.files:
        flash("Release requires an uploaded file.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    dco_number = (request.form.get("dco_number") or "").strip()
    dco_approver_ids = request.form.getlist("dco_approvers")

    r.change_summary = change_summary
    r.effective_date = eff
    r.dco_number = dco_number or None
    r.released_at = utcnow()
    r.released_by_user_id = u.id

    d.status = "Released"
    d.current_revision_id = r.id

    record_event(
        s,
        actor=u,
        action="doc.release",
        entity_type="DocumentRevision",
        entity_id=str(r.id),
        reason=reason,
        metadata={"doc_id": d.id, "doc_number": d.doc_number, "revision": r.revision},
    )

    # P38 B2: DCO auto-qualification — create pre-acknowledged training records
    # for the approvers who signed off on this DCO.
    if dco_number and dco_approver_ids:
        from app.eqms.models import User
        from app.eqms.modules.training.models import TrainingAssignment

        created = 0
        for raw_id in dco_approver_ids:
            try:
                uid = int(raw_id)
            except (TypeError, ValueError):
                continue
            approver = s.get(User, uid)
            if approver is None or not approver.is_active:
                continue
            exists = (
                s.query(TrainingAssignment)
                .filter(
                    TrainingAssignment.assigned_to_user_id == approver.id,
                    TrainingAssignment.document_id == d.id,
                    TrainingAssignment.training_type == "dco_auto_qualified",
                    TrainingAssignment.source_reference == dco_number,
                )
                .first()
            )
            if exists:
                continue
            s.add(TrainingAssignment(
                item_type="document",
                item_title=f"{d.doc_number} Rev {r.revision} — {d.title}",
                document_id=d.id,
                document_revision_id=r.id,
                assigned_to_user_id=approver.id,
                assigned_by_user_id=u.id,
                training_type="dco_auto_qualified",
                source_reference=dco_number,
                acknowledged_at=utcnow(),
                assigned_at=utcnow(),
                created_at=utcnow(),
            ))
            created += 1
        s.commit()
        flash(f"Revision released. {created} DCO auto-qualification record(s) created for {dco_number}.", "success")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    if dco_number and not dco_approver_ids:
        s.commit()
        flash("Revision released. DCO number recorded but no approvers were checked — no training records created.", "warning")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    s.commit()
    flash("Revision released.", "success")
    return redirect(url_for("doc_control.document_detail", doc_id=d.id))


@bp.post("/<int:doc_id>/revisions/new")
@require_permission("docs.edit")
def create_next_revision(doc_id: int):
    s = db_session()
    u = _current_user()

    d = _get_doc_or_404(s, doc_id)
    if d.status != "Released" or not d.current_revision:
        flash("You can only create a next revision from a Released document.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))
    if d.current_revision.released_at is None:
        flash("Current revision must be released before revising.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    from_rev = d.current_revision.revision
    new_rev = next_revision(from_rev)
    r = DocumentRevision(
        document_id=d.id,
        revision=new_rev,
        change_summary="",
        effective_date=None,
        created_by_user_id=u.id,
        released_at=None,
        released_by_user_id=None,
    )
    s.add(r)
    s.flush()
    d.status = "Draft"
    d.current_revision_id = r.id

    record_event(
        s,
        actor=u,
        action="doc.revise",
        entity_type="Document",
        entity_id=str(d.id),
        metadata={"doc_number": d.doc_number, "from": from_rev, "to": new_rev},
    )
    s.commit()
    flash(f"Created draft revision {new_rev}. Upload a new file to continue.", "success")
    return redirect(url_for("doc_control.document_detail", doc_id=d.id))


@bp.post("/<int:doc_id>/obsolete")
@require_permission("docs.obsolete")
def obsolete_document(doc_id: int):
    s = db_session()
    u = _current_user()
    d = _get_doc_or_404(s, doc_id)

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Obsoleting requires a reason.", "danger")
        return redirect(url_for("doc_control.document_detail", doc_id=d.id))

    d.status = "Obsolete"

    record_event(
        s,
        actor=u,
        action="doc.obsolete",
        entity_type="Document",
        entity_id=str(d.id),
        reason=reason,
        metadata={"doc_number": d.doc_number},
    )
    s.commit()
    flash("Document marked Obsolete.", "success")
    return redirect(url_for("doc_control.document_detail", doc_id=d.id))


@bp.get("/files/<int:file_id>/download")
@require_permission("docs.download")
def download_file(file_id: int):
    from flask import current_app, send_file

    s = db_session()
    u = _current_user()

    df = s.get(DocumentFile, file_id)
    if not df:
        from flask import abort

        abort(404)

    r = s.get(DocumentRevision, df.revision_id)
    d = s.get(Document, r.document_id) if r else None
    if not r or not d:
        from flask import abort

        abort(404)

    storage = storage_from_config(current_app.config)
    fobj = storage.open(df.storage_key)

    action = "doc.download_obsolete" if d.status == "Obsolete" else "doc.download"
    record_event(
        s,
        actor=u,
        action=action,
        entity_type="DocumentFile",
        entity_id=str(df.id),
        metadata={"doc_id": d.id, "doc_number": d.doc_number, "revision": r.revision, "filename": df.filename},
    )
    s.commit()

    return send_file(
        fobj,
        mimetype=df.content_type,
        as_attachment=True,
        download_name=df.filename,
        max_age=0,
    )


@bp.get("/files/<int:file_id>/view")
@require_permission("docs.view")
def view_file(file_id: int):
    from flask import current_app, send_file

    s = db_session()
    u = _current_user()

    df = s.get(DocumentFile, file_id)
    if not df:
        from flask import abort

        abort(404)

    r = s.get(DocumentRevision, df.revision_id)
    d = s.get(Document, r.document_id) if r else None
    if not r or not d:
        from flask import abort

        abort(404)

    storage = storage_from_config(current_app.config)

    action = "doc.view_obsolete" if d.status == "Obsolete" else "doc.view"
    record_event(
        s,
        actor=u,
        action=action,
        entity_type="DocumentFile",
        entity_id=str(df.id),
        metadata={"doc_id": d.id, "doc_number": d.doc_number, "revision": r.revision, "filename": df.filename},
    )
    s.commit()

    # Server-side rendering for .docx, .xlsx, .xls, .csv
    if needs_server_render(df.filename):
        file_bytes = storage.get_bytes(df.storage_key)
        download_url = url_for("doc_control.download_file", file_id=file_id)
        response = render_document_to_response(
            file_bytes, df.filename, df.content_type,
            download_url=download_url,
        )
        if response:
            return response

    fobj = storage.open(df.storage_key)
    inline = allow_inline_view(df.filename, df.content_type)
    return send_file(
        fobj,
        mimetype=df.content_type,
        as_attachment=not inline,
        download_name=df.filename,
        max_age=0,
    )

