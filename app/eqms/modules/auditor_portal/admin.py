from __future__ import annotations

import io
import logging
import mimetypes
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

from app.eqms.db import db_session
from app.eqms.document_viewer import needs_server_render, render_document_to_response
from app.eqms.modules.auditor_portal.access_log import record_access
from app.eqms.modules.auditor_portal import fs
from app.eqms.modules.auditor_portal.pdf_convert import CachedPdfStore, docx_bytes_to_pdf, xlsx_bytes_to_pdf
from app.eqms.modules.auditor_portal.fs import cache_key_parts
from app.eqms.rbac import require_permission

logger = logging.getLogger(__name__)

bp = Blueprint("auditor_portal", __name__)

_AUDITOR_VIEWER = "auditor_portal/document_viewer.html"


def _portal_enabled() -> bool:
    v = (current_app.config.get("AUDITOR_PORTAL_ENABLED") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


@bp.before_request
def _gate_portal() -> None:
    if not _portal_enabled():
        abort(404)


def _parent_rel(rel_path: str) -> str:
    rel_path = (rel_path or "").replace("\\", "/").strip("/")
    if "/" not in rel_path:
        return ""
    return rel_path.rsplit("/", 1)[0]


def _breadcrumbs(rel_path: str) -> list[tuple[str, str | None]]:
    rel_path = (rel_path or "").replace("\\", "/").strip("/")
    if not rel_path:
        return []
    parts = rel_path.split("/")
    out: list[tuple[str, str | None]] = []
    acc: list[str] = []
    for i, p in enumerate(parts):
        acc.append(p)
        path_so_far = "/".join(acc)
        if i == len(parts) - 1:
            out.append((p, None))
        else:
            out.append((p, url_for("auditor_portal.browse_folder", rel_path=path_so_far)))
    return out


def _unsupported_ext(ext: str) -> bool:
    return ext not in {
        ".pdf",
        ".docx",
        ".doc",
        ".xlsx",
        ".xls",
        ".csv",
        ".txt",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
    }


@bp.get("/")
@require_permission("auditor_portal.access")
def dashboard():
    s = db_session()
    user = g.current_user
    record_access(s, user=user, action="view_dashboard", rel_path="")
    tiles = fs.top_level_folders()
    return render_template("auditor_portal/dashboard.html", tiles=tiles)


@bp.get("/browse/")
@bp.get("/browse/<path:rel_path>")
@require_permission("auditor_portal.access")
def browse_folder(rel_path: str = ""):
    rel_path = (rel_path or "").replace("\\", "/").strip("/")
    s = db_session()
    user = g.current_user
    record_access(s, user=user, action="view_folder", rel_path=rel_path or "")
    subdirs, files = fs.list_immediate(rel_path)
    crumbs = _breadcrumbs(rel_path)
    return render_template(
        "auditor_portal/folder.html",
        rel_path=rel_path,
        subdirs=subdirs,
        files=files,
        breadcrumbs=crumbs,
    )


@bp.get("/file/<path:rel_path>")
@require_permission("auditor_portal.access")
def file_view(rel_path: str):
    rel_path = (rel_path or "").replace("\\", "/").strip("/")
    as_mode = (request.args.get("as") or "").strip().lower()
    s = db_session()
    user = g.current_user
    p = fs._safe_resolve(rel_path)
    if not p.is_file():
        abort(404)

    try:
        st = p.stat()
    except OSError:
        abort(404)

    max_b = fs.max_file_bytes()
    if st.st_size > max_b:
        record_access(s, user=user, action="view_unsupported", rel_path=rel_path, file_size=st.st_size)
        parent = _parent_rel(rel_path)
        back = url_for("auditor_portal.browse_folder", rel_path=parent) if parent else url_for("auditor_portal.dashboard")
        return (
            render_template(
                "auditor_portal/file_not_viewable.html",
                message="This file is too large to preview in the browser. Ask your Silq contact if you need another format.",
                back_url=back,
            ),
            200,
        )

    filename = p.name
    ext = Path(filename).suffix.lower()
    parent = _parent_rel(rel_path)
    back_url = url_for("auditor_portal.browse_folder", rel_path=parent) if parent else url_for("auditor_portal.dashboard")

    if _unsupported_ext(ext):
        record_access(s, user=user, action="view_unsupported", rel_path=rel_path, file_size=st.st_size)
        return render_template(
            "auditor_portal/file_not_viewable.html",
            message="This file type cannot be previewed in the auditor portal.",
            back_url=back_url,
        )

    data, size = fs.read_file_bytes(rel_path)
    mtime_ns = getattr(st, "st_mtime_ns", None)
    if mtime_ns is None:
        mtime_ns = int(st.st_mtime * 1_000_000_000)
    mtype, _ = mimetypes.guess_type(filename)
    mtype = mtype or "application/octet-stream"

    pdf_url = url_for("auditor_portal.file_view", rel_path=rel_path) + "?as=pdf"

    if ext == ".doc":
        record_access(s, user=user, action="view_unsupported", rel_path=rel_path, file_size=size)
        return render_template(
            "auditor_portal/file_not_viewable.html",
            message="Legacy Word (.doc) files cannot be opened here. Please ask your Silq contact to re-save the document as a .docx file.",
            back_url=back_url,
        )

    if ext == ".pdf":
        record_access(s, user=user, action="view_file", rel_path=rel_path, file_size=size)
        return send_file(
            io.BytesIO(data),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=secure_filename(filename),
        )

    if ext in {".png", ".jpg", ".jpeg", ".gif"}:
        record_access(s, user=user, action="view_file", rel_path=rel_path, file_size=size)
        return send_file(
            io.BytesIO(data),
            mimetype=mtype,
            as_attachment=False,
            download_name=secure_filename(filename),
        )

    if ext == ".txt":
        record_access(s, user=user, action="view_file", rel_path=rel_path, file_size=size)
        text = data.decode("utf-8", errors="replace")
        return render_template(
            "auditor_portal/text_view.html",
            filename=filename,
            text=text,
            back_url=back_url,
        )

    if ext == ".csv" or needs_server_render(filename):
        if ext in {".xlsx", ".xls"}:
            if as_mode == "table":
                record_access(s, user=user, action="view_table", rel_path=rel_path, file_size=size)
                resp = render_document_to_response(
                    data,
                    filename,
                    mtype,
                    download_url="",
                    back_url=back_url,
                    pdf_url=pdf_url,
                    table_fallback_url="",
                    viewer_template=_AUDITOR_VIEWER,
                )
                if resp:
                    return resp
                flash("Could not render this spreadsheet as a table.", "warning")
                return redirect(url_for("auditor_portal.file_view", rel_path=rel_path))

            if as_mode == "pdf":
                record_access(s, user=user, action="view_pdf", rel_path=rel_path, file_size=size)
                return _xlsx_pdf_response(rel_path, data, mtime_ns, size, back_url)

            # Default xlsx/xls: PDF
            record_access(s, user=user, action="view_pdf", rel_path=rel_path, file_size=size)
            return _xlsx_pdf_response(rel_path, data, mtime_ns, size, back_url, on_fail_table=True)

        if ext == ".docx":
            if as_mode == "pdf":
                record_access(s, user=user, action="view_pdf", rel_path=rel_path, file_size=size)
                return _docx_pdf_response(rel_path, data, mtime_ns, size, back_url)

            record_access(s, user=user, action="view_file", rel_path=rel_path, file_size=size)
            resp = render_document_to_response(
                data,
                filename,
                mtype,
                download_url="",
                back_url=back_url,
                pdf_url=pdf_url,
                viewer_template=_AUDITOR_VIEWER,
            )
            if resp:
                return resp
            return render_template(
                "auditor_portal/file_not_viewable.html",
                message="This document could not be converted for preview.",
                back_url=back_url,
            )

        # .csv
        record_access(s, user=user, action="view_file", rel_path=rel_path, file_size=size)
        resp = render_document_to_response(
            data,
            filename,
            mtype,
            download_url="",
            back_url=back_url,
            viewer_template=_AUDITOR_VIEWER,
        )
        if resp:
            return resp
        return render_template(
            "auditor_portal/file_not_viewable.html",
            message="This CSV could not be displayed.",
            back_url=back_url,
        )

    record_access(s, user=user, action="view_unsupported", rel_path=rel_path, file_size=size)
    return render_template(
        "auditor_portal/file_not_viewable.html",
        message="This file type cannot be previewed.",
        back_url=back_url,
    )


def _docx_pdf_response(rel_path: str, data: bytes, mtime_ns: int, size: int, _back_url: str):
    store = CachedPdfStore(current_app.config)
    key = cache_key_parts(rel_path, size, mtime_ns)
    cached = store.get("pdf", key)
    if cached:
        return _inline_pdf(cached, Path(rel_path).name)

    try:
        pdf_bytes = docx_bytes_to_pdf(data)
    except Exception as e:
        current_app.logger.warning("PDF conversion failed for %s: %s", rel_path, e)
        flash("PDF rendering temporarily unavailable.", "warning")
        return redirect(url_for("auditor_portal.file_view", rel_path=rel_path))

    store.put("pdf", key, pdf_bytes)
    return _inline_pdf(pdf_bytes, Path(rel_path).name)


def _xlsx_pdf_response(rel_path: str, data: bytes, mtime_ns: int, size: int, back_url: str, *, on_fail_table: bool = False):
    store = CachedPdfStore(current_app.config)
    key = cache_key_parts(rel_path, size, mtime_ns)
    cached = store.get("pdf", key)
    if cached:
        return _inline_pdf(cached, Path(rel_path).name)

    try:
        pdf_bytes = xlsx_bytes_to_pdf(data)
    except Exception as e:
        current_app.logger.warning("PDF conversion failed for %s: %s", rel_path, e)
        if on_fail_table:
            flash("PDF rendering temporarily unavailable; showing table view instead.", "warning")
            return redirect(url_for("auditor_portal.file_view", rel_path=rel_path) + "?as=table")
        flash("PDF rendering temporarily unavailable.", "warning")
        return redirect(url_for("auditor_portal.file_view", rel_path=rel_path))

    store.put("pdf", key, pdf_bytes)
    return _inline_pdf(pdf_bytes, Path(rel_path).name)


def _inline_pdf(pdf_bytes: bytes, download_name: str):
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f'inline; filename="{secure_filename(download_name)}"'
    return resp
