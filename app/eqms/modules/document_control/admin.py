from __future__ import annotations

from datetime import datetime

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy.orm import Session

from app.eqms.audit import record_event
from app.eqms.db import db_session
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

bp = Blueprint("doc_control", __name__)


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        # RBAC decorator should prevent this, but keep defensive.
        raise RuntimeError("No current user")
    return u


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


@bp.get("/")
@require_permission("docs.view")
def list_documents():
    s = db_session()
    docs = s.query(Document).order_by(Document.doc_number.asc()).all()
    return render_template("admin/modules/document_control/list.html", documents=docs)


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
        metadata={"doc_number": d.doc_number, "revision": r.revision},
    )
    s.commit()

    flash("Document created (Draft).", "success")
    return redirect(url_for("doc_control.document_detail", doc_id=d.id))


@bp.get("/<int:doc_id>")
@require_permission("docs.view")
def document_detail(doc_id: int):
    s = db_session()
    d = _get_doc_or_404(s, doc_id)
    return render_template("admin/modules/document_control/detail.html", document=d)


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

    r.change_summary = change_summary
    r.effective_date = eff
    r.released_at = datetime.utcnow()
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

    record_event(
        s,
        actor=u,
        action="doc.download",
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

