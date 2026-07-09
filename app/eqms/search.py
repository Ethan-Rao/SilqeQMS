"""
Unified document discovery (Phase 3, Prompt 5 / E1).

A single read-only search + landing that spans both controlled documents
(Document Control) and the admin_docs libraries, so users can find any document
without knowing which system it lives in. Results deep-link to the correct
viewer. Available to staff (gated by ``admin.view``; staff hold it).
"""
from __future__ import annotations

from flask import Blueprint, render_template, request

from app.eqms.db import db_session
from app.eqms.modules.admin_docs.admin import LIBRARIES, LIBRARY_ENDPOINTS
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.document_control.models import Document
from app.eqms.rbac import require_permission

bp = Blueprint("search", __name__)

_LIMIT = 100


@bp.get("/search")
@require_permission("admin.view")
def global_search():
    s = db_session()
    q = (request.args.get("q") or "").strip()

    doc_results: list[Document] = []
    admin_file_results: list[dict] = []
    folder_results: list[dict] = []

    if q:
        like = f"%{q.lower()}%"

        doc_results = (
            s.query(Document)
            .filter(
                Document.doc_number.ilike(like)
                | Document.title.ilike(like)
                | Document.doc_type.ilike(like)
                | Document.category.ilike(like)
            )
            .order_by(Document.doc_number.asc())
            .limit(_LIMIT)
            .all()
        )

        files = (
            s.query(AdminDocFile)
            .filter(
                AdminDocFile.filename.ilike(like)
                | AdminDocFile.description.ilike(like)
            )
            .order_by(AdminDocFile.filename.asc())
            .limit(_LIMIT)
            .all()
        )
        admin_file_results = [
            {"file": f, "library_label": LIBRARIES.get(f.library_key, f.library_key)}
            for f in files
        ]

        folders = (
            s.query(AdminDocFolder)
            .filter(AdminDocFolder.name.ilike(like))
            .order_by(AdminDocFolder.name.asc())
            .limit(_LIMIT)
            .all()
        )
        folder_results = [
            {"folder": fo, "library_label": LIBRARIES.get(fo.library_key, fo.library_key)}
            for fo in folders
        ]

    total = len(doc_results) + len(admin_file_results) + len(folder_results)

    return render_template(
        "admin/search.html",
        q=q,
        doc_results=doc_results,
        admin_file_results=admin_file_results,
        folder_results=folder_results,
        total=total,
        libraries=LIBRARIES,
        library_endpoints=LIBRARY_ENDPOINTS,
    )
