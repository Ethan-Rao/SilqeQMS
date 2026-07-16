from __future__ import annotations

from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError

from app.eqms.audit import record_event
from app.eqms.db import db_session
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.capas import bp
from app.eqms.modules.capas.models import CAPARecord, ROOT_CAUSE_CATEGORIES, STATUSES
from app.eqms.rbac import require_permission
from app.eqms.utils import current_user as _current_user

_DATE_FIELDS = (
    "opened_date", "target_close_date", "closed_date", "effectiveness_check_date",
    "section_1_date", "section_2_date", "section_3_date",
    "section_4_date", "section_5_date", "section_6_date",
)
_TEXT_FIELDS = (
    "title", "status", "root_cause_category", "description", "corrective_actions",
    "effectiveness_result", "linked_doc_number",
    "initiated_by", "closed_by", "on_time_status",
)


def _parse_date(s: str | None) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _norm(s: str | None) -> str:
    return (s or "").replace(" ", "").replace("-", "").upper()


def _matching_folder(s, capa_number: str) -> AdminDocFolder | None:
    """Find the capas-library folder whose name matches the CAPA number prefix."""
    prefix = _norm(capa_number.split("-")[0])  # e.g. CAPA001-2025 -> CAPA001
    if not prefix:
        return None
    folders = s.query(AdminDocFolder).filter(AdminDocFolder.library_key == "capas").all()
    for f in folders:
        if _norm(f.name).startswith(prefix):
            return f
    return None


@bp.get("/capas")
@require_permission("admin.view")
def capas_list():
    from collections import defaultdict

    s = db_session()
    today = date.today()
    capas = s.query(CAPARecord).order_by(CAPARecord.capa_number.asc()).all()

    # NCR accordion data (mirrors the admin_docs accordion tree, built in-memory).
    ncr_folders = (
        s.query(AdminDocFolder)
        .filter(AdminDocFolder.library_key == "ncrs")
        .order_by(AdminDocFolder.name)
        .all()
    )
    ncr_files_all = s.query(AdminDocFile).filter(AdminDocFile.library_key == "ncrs").all()
    ncr_folders_by_id = {f.id: f for f in ncr_folders}
    ncr_children_by_parent = defaultdict(list)
    for f in ncr_folders:
        ncr_children_by_parent[f.parent_id].append(f)
    ncr_files_by_folder = defaultdict(list)
    for fi in ncr_files_all:
        ncr_files_by_folder[fi.folder_id].append(fi)
    for lst in ncr_files_by_folder.values():
        lst.sort(key=lambda x: (x.filename or "").lower())
    ncr_root_folders = ncr_children_by_parent.get(None, [])
    ncr_root_files = ncr_files_by_folder.get(None, [])

    return render_template(
        "admin/capas/list.html",
        capas=capas,
        today=today,
        ncr_folders_by_id=ncr_folders_by_id,
        ncr_children_by_parent=ncr_children_by_parent,
        ncr_files_by_folder=ncr_files_by_folder,
        ncr_root_folders=ncr_root_folders,
        ncr_root_files=ncr_root_files,
    )


@bp.get("/capas/new")
@require_permission("admin.edit")
def capas_new_get():
    return render_template(
        "admin/capas/form.html",
        capa=None,
        statuses=STATUSES,
        root_causes=ROOT_CAUSE_CATEGORIES,
    )


@bp.post("/capas/new")
@require_permission("admin.edit")
def capas_new_post():
    s = db_session()
    u = _current_user()
    capa_number = (request.form.get("capa_number") or "").strip()
    title = (request.form.get("title") or "").strip()
    if not capa_number or not title:
        flash("CAPA number and title are required.", "danger")
        return redirect(url_for("capas.capas_new_get"))

    capa = CAPARecord(capa_number=capa_number, created_by_user_id=u.id if u else None)
    _apply_form(capa, request.form)
    if u:
        capa.updated_by_user_id = u.id
    s.add(capa)
    try:
        s.flush()
        record_event(s, actor=u, action="capa.create", entity_type="CAPARecord",
                     entity_id=str(capa.id), reason=f"Created {capa.capa_number}")
        s.commit()
    except IntegrityError:
        s.rollback()
        flash(f"A CAPA with number '{capa_number}' already exists.", "danger")
        return redirect(url_for("capas.capas_new_get"))
    flash(f"CAPA {capa.capa_number} created.", "success")
    return redirect(url_for("capas.capas_detail", capa_id=capa.id))


@bp.get("/capas/<int:capa_id>")
@require_permission("admin.view")
def capas_detail(capa_id: int):
    s = db_session()
    capa = s.get(CAPARecord, capa_id)
    if capa is None:
        abort(404)
    today = date.today()
    folder = _matching_folder(s, capa.capa_number)
    files = []
    library_url = None
    if folder is not None:
        library_url = url_for("admin_docs.capas", folder_id=folder.id)
        files = (
            s.query(AdminDocFile)
            .filter(AdminDocFile.library_key == "capas", AdminDocFile.folder_id == folder.id)
            .order_by(AdminDocFile.filename.asc())
            .all()
        )
    return render_template(
        "admin/capas/detail.html",
        capa=capa,
        today=today,
        library_url=library_url,
        folder=folder,
        files=files,
    )


@bp.get("/capas/<int:capa_id>/edit")
@require_permission("admin.edit")
def capas_edit_get(capa_id: int):
    s = db_session()
    capa = s.get(CAPARecord, capa_id)
    if capa is None:
        abort(404)
    return render_template(
        "admin/capas/form.html",
        capa=capa,
        statuses=STATUSES,
        root_causes=ROOT_CAUSE_CATEGORIES,
    )


@bp.post("/capas/<int:capa_id>/edit")
@require_permission("admin.edit")
def capas_edit_post(capa_id: int):
    s = db_session()
    capa = s.get(CAPARecord, capa_id)
    if capa is None:
        abort(404)
    u = _current_user()
    _apply_form(capa, request.form)
    if u:
        capa.updated_by_user_id = u.id
    record_event(s, actor=u, action="capa.update", entity_type="CAPARecord",
                 entity_id=str(capa.id), reason=f"Updated {capa.capa_number}")
    s.commit()
    flash(f"CAPA {capa.capa_number} updated.", "success")
    return redirect(url_for("capas.capas_detail", capa_id=capa.id))


def _apply_form(capa: CAPARecord, form) -> None:
    for field in _TEXT_FIELDS:
        value = (form.get(field) or "").strip()
        setattr(capa, field, value or None)
    if not capa.status:
        capa.status = "Open"
    for field in _DATE_FIELDS:
        setattr(capa, field, _parse_date(form.get(field)))
