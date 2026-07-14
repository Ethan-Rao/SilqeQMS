from __future__ import annotations

from pathlib import Path

from flask import abort, current_app, flash, g, redirect, render_template, request, send_file, url_for

from app.eqms.db import db_session
from app.eqms.document_viewer import needs_server_render, render_document_to_response
from app.eqms.models import User
from app.eqms.modules.admin_docs import bp
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.admin_docs.service import create_folder, upload_document
from app.eqms.rbac import require_any_permission, require_permission
from app.eqms.storage import storage_from_config
from app.eqms.utils import allow_inline_view, current_user as _current_user


LIBRARIES = {
    "qms_documents": "Quality Management Documents",
    "employee_training": "Employee Training",
    "management_reviews": "Management Reviews, Audits & Approvals",
    "ncrs": "NCRs",
    "capas": "CAPAs",
    "post_market_surveillance": "Post Market Surveillance",
    "regulatory_standards": "Regulatory Standards & Approvals",
    "work_orders": "Work Orders",
    "risk_management": "Risk Management",
    "dhfs": "Design & Development Records",
    "forms_templates_travelers": "Forms, Templates & Travelers",
}

LIBRARY_ENDPOINTS = {
    "qms_documents": "admin_docs.qms_documents",
    "employee_training": "admin_docs.employee_training",
    "management_reviews": "admin_docs.management_reviews",
    "ncrs": "admin_docs.ncrs",
    "capas": "admin_docs.capas",
    "post_market_surveillance": "admin_docs.post_market_surveillance",
    "regulatory_standards": "admin_docs.regulatory_standards",
    "work_orders": "admin_docs.work_orders",
    "risk_management": "admin_docs.risk_management",
    "dhfs": "admin_docs.dhfs",
    "forms_templates_travelers": "admin_docs.forms_templates_travelers",
}




def _library_or_404(library_key: str) -> str:
    if library_key not in LIBRARIES:
        abort(404)
    return LIBRARIES[library_key]


@bp.get("/qms-documents")
@require_any_permission("admin.view", "staff.view")
def qms_documents():
    return _render_library("qms_documents")


@bp.get("/employee-training")
@require_any_permission("admin.view", "staff.view")
def employee_training():
    return _render_library("employee_training")


@bp.get("/management-reviews")
@require_any_permission("admin.view", "staff.view")
def management_reviews():
    return _render_library("management_reviews")


@bp.get("/ncrs")
@require_any_permission("admin.view", "staff.view")
def ncrs():
    return _render_library("ncrs")


# Path moved to /capas-library so the structured CAPA tracker can own /admin/capas.
# Endpoint name (admin_docs.capas) is unchanged, so existing url_for calls still resolve.
@bp.get("/capas-library")
@require_any_permission("admin.view", "staff.view")
def capas():
    return _render_library("capas")


@bp.get("/post-market-surveillance")
@require_any_permission("admin.view", "staff.view")
def post_market_surveillance():
    return _render_library("post_market_surveillance")


@bp.get("/regulatory-standards")
@require_any_permission("admin.view", "staff.view")
def regulatory_standards():
    return _render_library("regulatory_standards")


@bp.get("/work-orders")
@require_any_permission("manufacturing.view", "staff.view")
def work_orders():
    return _render_library("work_orders")


@bp.get("/risk-management")
@require_any_permission("admin.view", "staff.view")
def risk_management():
    return _render_library("risk_management")


@bp.get("/dhfs")
@require_any_permission("admin.view", "staff.view")
def dhfs():
    return _render_library("dhfs")


@bp.get("/forms-templates-travelers")
@require_any_permission("admin.view", "staff.view")
def forms_templates_travelers():
    return _render_library("forms_templates_travelers")


def _folder_path_label(folder, folder_map: dict) -> str:
    """Build a 'Root / A / B' path string for a folder using an in-memory map (no N+1)."""
    parts = []
    cursor = folder
    guard = 0
    while cursor is not None and guard < 50:
        parts.append(cursor.name)
        cursor = folder_map.get(cursor.parent_id) if cursor.parent_id else None
        guard += 1
    parts.reverse()
    return "Root / " + " / ".join(parts) if parts else "Root"


def _render_library(library_key: str):
    from sqlalchemy import func

    title = _library_or_404(library_key)
    s = db_session()
    folder_id = request.args.get("folder_id", type=int)
    query = (request.args.get("q") or "").strip()
    current_folder = s.get(AdminDocFolder, folder_id) if folder_id else None
    if current_folder and current_folder.library_key != library_key:
        abort(404)

    # Direct (non-recursive) file/subfolder counts per folder for the tree cards.
    file_counts = dict(
        s.query(AdminDocFile.folder_id, func.count(AdminDocFile.id))
        .filter(AdminDocFile.library_key == library_key)
        .group_by(AdminDocFile.folder_id)
        .all()
    )
    subfolder_counts = dict(
        s.query(AdminDocFolder.parent_id, func.count(AdminDocFolder.id))
        .filter(AdminDocFolder.library_key == library_key)
        .group_by(AdminDocFolder.parent_id)
        .all()
    )

    # In-library search: flat list of matching files across all descendant folders.
    search_results = []
    if query:
        folder_map = {
            f.id: f
            for f in s.query(AdminDocFolder).filter(AdminDocFolder.library_key == library_key).all()
        }
        like = f"%{query}%"
        matches = (
            s.query(AdminDocFile)
            .filter(AdminDocFile.library_key == library_key, AdminDocFile.filename.ilike(like))
            .order_by(AdminDocFile.filename.asc())
            .all()
        )
        search_results = [
            {"file": f, "path": _folder_path_label(folder_map.get(f.folder_id), folder_map) if f.folder_id else "Root"}
            for f in matches
        ]

    subfolders = (
        s.query(AdminDocFolder)
        .filter(AdminDocFolder.library_key == library_key, AdminDocFolder.parent_id == (current_folder.id if current_folder else None))
        .order_by(AdminDocFolder.name.asc())
        .all()
    )
    documents = (
        s.query(AdminDocFile)
        .filter(AdminDocFile.library_key == library_key, AdminDocFile.folder_id == (current_folder.id if current_folder else None))
        .order_by(AdminDocFile.uploaded_at.desc())
        .all()
    )

    breadcrumbs = []
    cursor = current_folder
    while cursor:
        breadcrumbs.append(cursor)
        cursor = cursor.parent
    breadcrumbs.reverse()

    # All folders across all libraries for the move modal
    all_folders = (
        s.query(AdminDocFolder)
        .order_by(AdminDocFolder.library_key.asc(), AdminDocFolder.name.asc())
        .all()
    )

    return render_template(
        "admin/admin_docs/index.html",
        library_key=library_key,
        title=title,
        current_folder=current_folder,
        subfolders=subfolders,
        documents=documents,
        breadcrumbs=breadcrumbs,
        library_endpoint=LIBRARY_ENDPOINTS[library_key],
        libraries=LIBRARIES,
        all_folders=all_folders,
        q=query,
        search_results=search_results,
        file_counts=file_counts,
        subfolder_counts=subfolder_counts,
    )


@bp.post("/admin-docs/folders/new")
@require_permission("admin.edit")
def admin_docs_create_folder():
    s = db_session()
    u = _current_user()
    library_key = (request.form.get("library_key") or "").strip()
    _library_or_404(library_key)

    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Folder name is required.", "danger")
        return redirect(url_for(LIBRARY_ENDPOINTS[library_key], folder_id=request.form.get("parent_id") or None))

    parent_id = request.form.get("parent_id", type=int)
    parent = s.get(AdminDocFolder, parent_id) if parent_id else None
    if parent and parent.library_key != library_key:
        flash("Invalid parent folder.", "danger")
        return redirect(url_for(LIBRARY_ENDPOINTS[library_key], folder_id=None))

    create_folder(s, library_key, name, u, parent=parent)
    s.commit()
    flash("Folder created.", "success")
    return redirect(url_for(LIBRARY_ENDPOINTS[library_key], folder_id=parent_id))


@bp.post("/admin-docs/documents/upload")
@require_permission("admin.edit")
def admin_docs_upload_document():
    s = db_session()
    u = _current_user()
    library_key = (request.form.get("library_key") or "").strip()
    _library_or_404(library_key)

    folder_id = request.form.get("folder_id", type=int)
    folder = s.get(AdminDocFolder, folder_id) if folder_id else None
    if folder and folder.library_key != library_key:
        flash("Invalid folder.", "danger")
        return redirect(url_for(LIBRARY_ENDPOINTS[library_key]))

    # Support multiple files
    files = request.files.getlist("file")
    if not files or all(not f.filename for f in files):
        flash("Please select a file to upload.", "danger")
        return redirect(url_for(LIBRARY_ENDPOINTS[library_key], folder_id=folder_id))

    description = request.form.get("description")
    uploaded_count = 0
    errors = []

    for f in files:
        if not f or not f.filename:
            continue
        file_bytes = f.read()
        if len(file_bytes) > 50 * 1024 * 1024:  # 50MB per file
            errors.append(f"{f.filename}: too large (max 50MB)")
            continue
        content_type = f.mimetype or "application/octet-stream"
        try:
            upload_document(s, library_key, folder, file_bytes, f.filename, content_type, u, description=description)
            uploaded_count += 1
        except Exception as e:
            current_app.logger.exception("Upload failed for %s: %s", f.filename, e)
            errors.append(f"{f.filename}: upload failed")

    if uploaded_count > 0:
        s.commit()
        flash(f"Successfully uploaded {uploaded_count} document(s).", "success")
    if errors:
        flash(f"Errors: {'; '.join(errors)}", "warning")
    if uploaded_count == 0 and not errors:
        flash("No files were uploaded.", "warning")

    return redirect(url_for(LIBRARY_ENDPOINTS[library_key], folder_id=folder_id))


@bp.get("/admin-docs/documents/<int:doc_id>/download")
@require_any_permission("admin.view", "staff.view")
def admin_docs_document_download(doc_id: int):
    s = db_session()
    doc = s.get(AdminDocFile, doc_id)
    if not doc:
        abort(404)
    storage = storage_from_config(current_app.config)
    fobj = storage.open(doc.storage_key)
    return send_file(fobj, mimetype=doc.content_type, as_attachment=True, download_name=doc.filename)


@bp.post("/admin-docs/documents/<int:doc_id>/move")
@require_permission("admin.edit")
def admin_docs_move_document(doc_id: int):
    s = db_session()
    doc = s.get(AdminDocFile, doc_id)
    if not doc:
        abort(404)

    new_library_key = (request.form.get("library_key") or "").strip()
    new_folder_id = request.form.get("folder_id", type=int)

    # Validate library
    if new_library_key and new_library_key not in LIBRARIES:
        flash("Invalid library.", "danger")
        return redirect(request.referrer or url_for("admin.index"))

    # Validate folder
    if new_folder_id:
        new_folder = s.get(AdminDocFolder, new_folder_id)
        if not new_folder:
            flash("Folder not found.", "danger")
            return redirect(request.referrer or url_for("admin.index"))
        # Use the folder's library_key if not explicitly provided
        if not new_library_key:
            new_library_key = new_folder.library_key
    else:
        new_folder_id = None

    if new_library_key:
        doc.library_key = new_library_key
    doc.folder_id = new_folder_id  # Can be None (root of library)

    s.commit()
    flash(f"Document moved to {LIBRARIES.get(doc.library_key, doc.library_key)}.", "success")
    return redirect(url_for(LIBRARY_ENDPOINTS.get(doc.library_key, "admin.index"), folder_id=new_folder_id))


@bp.get("/admin-docs/documents/<int:doc_id>/view")
@require_any_permission("admin.view", "staff.view")
def admin_docs_document_view(doc_id: int):
    s = db_session()
    doc = s.get(AdminDocFile, doc_id)
    if not doc:
        abort(404)

    storage = storage_from_config(current_app.config)
    download_url = url_for("admin_docs.admin_docs_document_download", doc_id=doc.id)

    # Server-side rendering for .docx, .xlsx, .xls, .csv
    if needs_server_render(doc.filename):
        file_bytes = storage.get_bytes(doc.storage_key)
        response = render_document_to_response(
            file_bytes, doc.filename, doc.content_type,
            download_url=download_url,
        )
        if response:
            return response
        # Fallback: download if rendering failed
        flash("Could not render document inline. Downloading instead.", "warning")
        return redirect(download_url)

    # Native browser rendering (PDF, images, text)
    fobj = storage.open(doc.storage_key)
    inline = allow_inline_view(doc.filename, doc.content_type)
    return send_file(
        fobj,
        mimetype=doc.content_type,
        as_attachment=not inline,
        download_name=doc.filename,
    )
