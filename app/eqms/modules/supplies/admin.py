from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for, current_app

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.supplies.models import Supply, SupplyDocument, SupplySupplier
from app.eqms.modules.supplies.service import (
    add_supplier_to_supply,
    create_supply,
    delete_supply_document,
    update_supply,
    upload_supply_document,
    validate_supply_payload,
)
from app.eqms.modules.suppliers.models import Supplier
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config
from app.eqms.utils import parse_custom_fields

bp = Blueprint("supplies", __name__)

SUPPLY_DOC_CATEGORIES = {
    "spec_document": "Specification",
    "coa": "COA",
    "sds": "SDS",
    "general": "General",
}


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


def _parse_int(value: str | None) -> int | None:
    v = (value or "").strip()
    if not v:
        return None
    try:
        return int(v)
    except Exception:
        return None


@bp.get("/supplies")
@require_permission("supplies.view")
def supplies_list():
    s = db_session()
    search = (request.args.get("q") or "").strip()
    q = s.query(Supply)
    if search:
        like = f"%{search}%"
        q = q.filter((Supply.supply_code.ilike(like)) | (Supply.description.ilike(like)))
    supplies = q.order_by(Supply.supply_code.asc()).all()
    return render_template("admin/supplies/list.html", supplies=supplies, search=search)


@bp.get("/supplies/new")
@require_permission("supplies.create")
def supplies_new_get():
    return render_template("admin/supplies/new.html")


@bp.post("/supplies/new")
@require_permission("supplies.create")
def supplies_new_post():
    s = db_session()
    u = _current_user()

    custom_fields, custom_fields_error = parse_custom_fields(request.form.get("custom_fields"))
    if custom_fields_error:
        flash(custom_fields_error, "danger")
        return redirect(url_for("supplies.supplies_new_get"))

    payload = {
        "supply_code": request.form.get("supply_code"),
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "manufacturer": request.form.get("manufacturer"),
        "part_number": request.form.get("part_number"),
        "min_stock_level": _parse_int(request.form.get("min_stock_level")),
        "current_stock": _parse_int(request.form.get("current_stock")),
        "unit_of_measure": request.form.get("unit_of_measure"),
        "comments": request.form.get("comments"),
        "custom_fields": custom_fields,
    }
    errors = validate_supply_payload(payload)
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("supplies.supplies_new_get"))

    existing = s.query(Supply).filter(Supply.supply_code == (payload.get("supply_code") or "").strip()).one_or_none()
    if existing:
        flash("Supply code already exists.", "danger")
        return redirect(url_for("supplies.supplies_new_get"))

    supply = create_supply(s, payload, u)
    s.commit()
    flash("Supply created.", "success")
    return redirect(url_for("supplies.supplies_detail", supply_id=supply.id))


@bp.get("/supplies/<int:supply_id>")
@require_permission("supplies.view")
def supplies_detail(supply_id: int):
    s = db_session()
    supply = s.get(Supply, supply_id)
    if not supply:
        abort(404)

    documents = s.query(SupplyDocument).filter(SupplyDocument.supply_id == supply.id).order_by(SupplyDocument.uploaded_at.desc()).all()
    documents_by_category = {k: [] for k in SUPPLY_DOC_CATEGORIES}
    for doc in documents:
        documents_by_category.setdefault(doc.category or "general", []).append(doc)
    primary_spec = next((d for d in documents_by_category.get("spec_document", []) if d.is_primary), None)

    associated_supplier_ids = {assoc.supplier_id for assoc in supply.supplier_associations}
    available_suppliers = s.query(Supplier).filter(~Supplier.id.in_(associated_supplier_ids)).order_by(Supplier.name).all() if associated_supplier_ids else s.query(Supplier).order_by(Supplier.name).all()

    return render_template(
        "admin/supplies/detail.html",
        supply=supply,
        documents_by_category=documents_by_category,
        primary_spec=primary_spec,
        doc_categories=SUPPLY_DOC_CATEGORIES,
        available_suppliers=available_suppliers,
        today=date.today(),
    )


@bp.get("/supplies/<int:supply_id>/edit")
@require_permission("supplies.edit")
def supplies_edit_get(supply_id: int):
    s = db_session()
    supply = s.get(Supply, supply_id)
    if not supply:
        abort(404)
    return render_template("admin/supplies/edit.html", supply=supply)


@bp.post("/supplies/<int:supply_id>/edit")
@require_permission("supplies.edit")
def supplies_edit_post(supply_id: int):
    s = db_session()
    u = _current_user()
    supply = s.get(Supply, supply_id)
    if not supply:
        abort(404)

    custom_fields, custom_fields_error = parse_custom_fields(request.form.get("custom_fields"))
    if custom_fields_error:
        flash(custom_fields_error, "danger")
        return redirect(url_for("supplies.supplies_edit_get", supply_id=supply_id))

    payload = {
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "manufacturer": request.form.get("manufacturer"),
        "part_number": request.form.get("part_number"),
        "min_stock_level": _parse_int(request.form.get("min_stock_level")),
        "current_stock": _parse_int(request.form.get("current_stock")),
        "unit_of_measure": request.form.get("unit_of_measure"),
        "comments": request.form.get("comments"),
        "custom_fields": custom_fields,
    }
    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for change is required.", "danger")
        return redirect(url_for("supplies.supplies_edit_get", supply_id=supply_id))

    update_supply(s, supply, payload, u, reason=reason)
    s.commit()
    flash("Supply updated.", "success")
    return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))


@bp.post("/supplies/<int:supply_id>/documents/<category>")
@require_permission("supplies.upload")
def supplies_document_upload(supply_id: int, category: str):
    s = db_session()
    u = _current_user()
    supply = s.get(Supply, supply_id)
    if not supply:
        abort(404)

    if category not in SUPPLY_DOC_CATEGORIES:
        flash("Invalid document category.", "danger")
        return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))

    if category == "spec_document":
        (
            s.query(SupplyDocument)
            .filter(SupplyDocument.supply_id == supply.id, SupplyDocument.category == category, SupplyDocument.is_primary.is_(True))
            .update({"is_primary": False})
        )
        is_primary = True
    else:
        is_primary = False

    upload_supply_document(
        s,
        supply,
        f.read(),
        f.filename,
        (f.mimetype or "application/octet-stream").strip(),
        u,
        category=category,
        description=(request.form.get("description") or "").strip() or None,
        is_primary=is_primary,
    )
    s.commit()
    flash("Document uploaded.", "success")
    return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))


@bp.get("/supplies/<int:supply_id>/documents/<int:doc_id>/download")
@require_permission("supplies.view")
def supplies_document_download(supply_id: int, doc_id: int):
    s = db_session()
    doc = s.get(SupplyDocument, doc_id)
    if not doc or doc.supply_id != supply_id:
        abort(404)
    storage = storage_from_config(current_app.config)
    fobj = storage.open(doc.storage_key)
    return send_file(fobj, mimetype=doc.content_type, as_attachment=True, download_name=doc.original_filename)


@bp.post("/supplies/<int:supply_id>/documents/<int:doc_id>/delete")
@require_permission("supplies.upload")
def supplies_document_delete(supply_id: int, doc_id: int):
    s = db_session()
    u = _current_user()
    doc = s.get(SupplyDocument, doc_id)
    if not doc or doc.supply_id != supply_id:
        abort(404)
    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for deletion is required.", "danger")
        return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))
    delete_supply_document(s, doc, u, reason)
    s.commit()
    flash("Document deleted.", "success")
    return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))


@bp.post("/supplies/<int:supply_id>/suppliers")
@require_permission("supplies.edit")
def supplies_supplier_add(supply_id: int):
    s = db_session()
    u = _current_user()
    supply = s.get(Supply, supply_id)
    if not supply:
        abort(404)
    supplier_id = request.form.get("supplier_id")
    if not supplier_id:
        flash("Please select a supplier.", "danger")
        return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))
    supplier = s.get(Supplier, int(supplier_id))
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))

    existing = (
        s.query(SupplySupplier)
        .filter(SupplySupplier.supply_id == supply_id, SupplySupplier.supplier_id == supplier.id)
        .one_or_none()
    )
    if existing:
        flash("Supplier already associated.", "danger")
        return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))

    relationship_type = (request.form.get("relationship_type") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None
    add_supplier_to_supply(s, supply, supplier, relationship_type, notes, u)
    s.commit()
    flash("Supplier associated.", "success")
    return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))


@bp.post("/supplies/<int:supply_id>/suppliers/<int:supplier_id>/remove")
@require_permission("supplies.edit")
def supplies_supplier_remove(supply_id: int, supplier_id: int):
    s = db_session()
    u = _current_user()
    assoc = (
        s.query(SupplySupplier)
        .filter(SupplySupplier.supply_id == supply_id, SupplySupplier.supplier_id == supplier_id)
        .one_or_none()
    )
    if not assoc:
        abort(404)
    remove_reason = (request.form.get("reason") or "").strip()
    if not remove_reason:
        flash("Reason is required.", "danger")
        return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))
    from app.eqms.modules.supplies.service import remove_supplier_from_supply
    remove_supplier_from_supply(s, assoc, u, reason=remove_reason)
    s.commit()
    flash("Supplier association removed.", "success")
    return redirect(url_for("supplies.supplies_detail", supply_id=supply_id))
