from __future__ import annotations

from pathlib import Path

from flask import abort, current_app, flash, g, redirect, render_template, request, send_file, url_for

from app.eqms.db import db_session
from app.eqms.document_viewer import needs_server_render, render_document_to_response
from app.eqms.models import User
from app.eqms.modules.admin_docs import bp
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.admin_docs.service import create_folder, upload_document
from app.eqms.rbac import require_any_permission, require_permission, user_has_permission
from app.eqms.storage import storage_from_config
from app.eqms.utils import allow_inline_view, current_user as _current_user


LIBRARIES = {
    "qms_documents": "Quality Management Documents",
    "employee_training": "Training Records",
    "management_reviews": "Management Reviews, Audits & Approvals",
    "ncrs": "NCRs",
    "capas": "CAPAs",
    "post_market_surveillance": "Post Market Surveillance",
    "regulatory_standards": "Regulatory Standards & Approvals",
    "work_orders": "Work Orders",
    "risk_management": "Risk Management",
    "dhfs": "Design & Development Records",
    "forms_templates_travelers": "Forms, Templates & Travelers",
    "purchasing": "Purchasing Documents",
    "equipment_files": "Equipment Documents",
    "supplies_inventory": "Supplies Inventory Snapshots",
    "nre_projects": "NRE Project Documents",
}

# Libraries rendered as a single-page full folder tree (Prompt 21 Task B)
# instead of the folder-by-folder index view.
ACCORDION_LIBRARIES: frozenset[str] = frozenset({
    "management_reviews",
    "post_market_surveillance",
    "risk_management",
    "dhfs",  # Design & Development Records
    "work_orders",
    "employee_training",
    "ncrs",
    "purchasing",
})

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
    "purchasing": "admin_docs.purchasing_docs",
    "equipment_files": "admin_docs.equipment_files",
    "supplies_inventory": "admin_docs.supplies_inventory",
    "nre_projects": "admin_docs.nre_project_docs",
}




def _library_or_404(library_key: str) -> str:
    if library_key not in LIBRARIES:
        abort(404)
    return LIBRARIES[library_key]


@bp.get("/qms-documents")
@require_any_permission("admin.view", "staff.view")
def qms_documents():
    return _render_library("qms_documents")


def _folder_visible_to_user(folder_name: str, user: "User") -> bool:
    """True if this top-level Training Records folder belongs to this user."""
    name_norm = folder_name.lower().replace(" ", "").replace("_", "")
    if user.display_name:
        dn_norm = user.display_name.lower().replace(" ", "")
        if dn_norm and (dn_norm in name_norm or name_norm in dn_norm):
            return True
    local = (user.email or "").split("@")[0].lower()
    if local and (local in name_norm or (name_norm[:6] and name_norm[:6] in local)):
        return True
    return False


@bp.get("/employee-training")
@require_any_permission("admin.view", "staff.view")
def employee_training():
    u = _current_user()
    is_admin = user_has_permission(u, "admin.edit")
    return _render_library("employee_training", restrict_to_user=None if is_admin else u)


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


@bp.get("/purchasing-docs")
@require_any_permission("admin.view", "staff.view")
def purchasing_docs():
    return _render_library("purchasing")


@bp.get("/equipment-files")
@require_any_permission("admin.view", "staff.view")
def equipment_files():
    return _render_library("equipment_files")


@bp.get("/supplies-inventory")
@require_any_permission("admin.view", "staff.view")
def supplies_inventory():
    return _render_library("supplies_inventory")


@bp.get("/nre-projects")
@require_any_permission("sales_orders.view", "admin.view")
def nre_project_docs():
    return _render_library("nre_projects")


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


def _render_library_accordion(s, library_key: str, title: str, query: str, restrict_to_user=None):
    """Single-page full-tree view for accordion libraries (Prompt 21 Task B).

    Two queries only (all folders + all files for the library); the tree,
    per-folder counts, and in-library search are all derived in memory.
    """
    from collections import defaultdict

    all_folders = (
        s.query(AdminDocFolder)
        .filter(AdminDocFolder.library_key == library_key)
        .order_by(AdminDocFolder.name.asc())
        .all()
    )
    all_files = (
        s.query(AdminDocFile)
        .filter(AdminDocFile.library_key == library_key)
        .all()
    )

    folders_by_id = {f.id: f for f in all_folders}
    children_by_parent: dict[int | None, list] = defaultdict(list)
    for f in all_folders:
        children_by_parent[f.parent_id].append(f)
    files_by_folder: dict[int | None, list] = defaultdict(list)
    for fi in all_files:
        files_by_folder[fi.folder_id].append(fi)
    for lst in files_by_folder.values():
        lst.sort(key=lambda x: (x.filename or "").lower())

    # Per-user scoping: non-admin users only see their own top-level folder(s)
    # and everything beneath. Root-level loose files are hidden.
    visible_folder_ids: set[int] | None = None
    if restrict_to_user is not None:
        visible_roots = [
            f for f in children_by_parent.get(None, [])
            if _folder_visible_to_user(f.name, restrict_to_user)
        ]
        visible_folder_ids = set()

        def _collect(fid: int):
            visible_folder_ids.add(fid)
            for child in children_by_parent.get(fid, []):
                _collect(child.id)

        for rf in visible_roots:
            _collect(rf.id)

    # Flat search results (in-memory) when a query is present.
    search_results = []
    if query:
        needle = query.lower()
        matches = sorted(
            (
                fi for fi in all_files
                if needle in (fi.filename or "").lower()
                and (visible_folder_ids is None or fi.folder_id in visible_folder_ids)
            ),
            key=lambda x: (x.filename or "").lower(),
        )
        search_results = [
            {
                "file": fi,
                "path": _folder_path_label(folders_by_id.get(fi.folder_id), folders_by_id) if fi.folder_id else "Root",
            }
            for fi in matches
        ]

    # Total (recursive) file count per folder: direct files plus all descendants.
    def _total_files(fid):
        direct = len(files_by_folder.get(fid, []))
        return direct + sum(_total_files(child.id) for child in children_by_parent.get(fid, []))

    total_files_by_folder = {fid: _total_files(fid) for fid in folders_by_id}

    # Intra-library move targets (id/label) for the admin move control.
    folder_options = sorted(
        (
            {"id": f.id, "label": _folder_path_label(f, folders_by_id)}
            for f in all_folders
        ),
        key=lambda o: o["label"].lower(),
    )

    can_edit = user_has_permission(getattr(g, "current_user", None), "admin.edit")

    # Scoped users see only their matching root folders (and no loose root files).
    if restrict_to_user is not None:
        root_folders = [
            f for f in children_by_parent.get(None, [])
            if _folder_visible_to_user(f.name, restrict_to_user)
        ]
        root_files = []
    else:
        root_folders = children_by_parent.get(None, [])
        root_files = files_by_folder.get(None, [])

    return render_template(
        "admin/admin_docs/accordion.html",
        library_key=library_key,
        title=title,
        library_endpoint=LIBRARY_ENDPOINTS[library_key],
        folders_by_id=folders_by_id,
        children_by_parent=children_by_parent,
        files_by_folder=files_by_folder,
        total_files_by_folder=total_files_by_folder,
        root_folders=root_folders,
        root_files=root_files,
        folder_options=folder_options,
        libraries=LIBRARIES,
        can_edit=can_edit,
        q=query,
        search_results=search_results,
    )


def _render_library(library_key: str, restrict_to_user=None):
    from sqlalchemy import func

    title = _library_or_404(library_key)
    s = db_session()
    query = (request.args.get("q") or "").strip()

    # Accordion libraries render the whole tree on one page (folder_id ignored).
    if library_key in ACCORDION_LIBRARIES:
        return _render_library_accordion(s, library_key, title, query, restrict_to_user=restrict_to_user)

    folder_id = request.args.get("folder_id", type=int)
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
