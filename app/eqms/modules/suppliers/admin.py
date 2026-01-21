from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, send_file, url_for

from app.eqms.audit import record_event
from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.equipment.models import Equipment, EquipmentSupplier, ManagedDocument
from app.eqms.modules.equipment.service import add_supplier_to_equipment, remove_supplier_from_equipment
from app.eqms.modules.suppliers.models import Supplier
from app.eqms.modules.suppliers.service import (
    create_supplier,
    delete_supplier_document,
    update_supplier,
    upload_supplier_document,
    validate_supplier_payload,
)
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config

bp = Blueprint("suppliers", __name__)


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


# ---------- List ----------
@bp.get("/suppliers")
@require_permission("suppliers.view")
def suppliers_list():
    s = db_session()

    # Filters
    search = (request.args.get("q") or "").strip()
    status_filter = (request.args.get("status") or "").strip()
    category_filter = (request.args.get("category") or "").strip()

    q = s.query(Supplier)

    if search:
        like = f"%{search}%"
        q = q.filter(
            (Supplier.name.ilike(like))
            | (Supplier.product_service_provided.ilike(like))
        )

    if status_filter:
        q = q.filter(Supplier.status == status_filter)

    if category_filter:
        q = q.filter(Supplier.category == category_filter)

    suppliers = q.order_by(Supplier.name.asc()).all()

    # Get unique categories for filter dropdown
    categories = s.query(Supplier.category).filter(Supplier.category.isnot(None)).distinct().all()
    categories = sorted([cat[0] for cat in categories if cat[0]])

    return render_template(
        "admin/suppliers/list.html",
        suppliers=suppliers,
        search=search,
        status_filter=status_filter,
        category_filter=category_filter,
        categories=categories,
        today=date.today(),
    )


# ---------- New ----------
@bp.get("/suppliers/new")
@require_permission("suppliers.create")
def suppliers_new_get():
    return render_template("admin/suppliers/new.html")


@bp.post("/suppliers/new")
@require_permission("suppliers.create")
def suppliers_new_post():
    s = db_session()
    u = _current_user()

    payload = {
        "name": request.form.get("name"),
        "status": request.form.get("status"),
        "category": request.form.get("category"),
        "product_service_provided": request.form.get("product_service_provided"),
        "address": request.form.get("address"),
        "initial_listing_date": request.form.get("initial_listing_date"),
        "certification_expiration": request.form.get("certification_expiration"),
        "notes": request.form.get("notes"),
    }

    errors = validate_supplier_payload(payload)
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("suppliers.suppliers_new_get"))

    supplier = create_supplier(s, payload, u)
    s.commit()

    flash("Supplier created.", "success")
    return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier.id))


# ---------- Detail ----------
@bp.get("/suppliers/<int:supplier_id>")
@require_permission("suppliers.view")
def supplier_detail(supplier_id: int):
    s = db_session()
    supplier = s.get(Supplier, supplier_id)
    if not supplier:
        abort(404)

    # Get non-deleted documents
    documents = (
        s.query(ManagedDocument)
        .filter(ManagedDocument.entity_type == "supplier")
        .filter(ManagedDocument.entity_id == supplier.id)
        .filter(ManagedDocument.is_deleted == False)
        .order_by(ManagedDocument.uploaded_at.desc())
        .all()
    )

    # Get all equipment for the "Add Equipment" dropdown (excluding already associated)
    associated_equipment_ids = {assoc.equipment_id for assoc in supplier.equipment_associations}
    available_equipment = s.query(Equipment).filter(~Equipment.id.in_(associated_equipment_ids)).order_by(Equipment.equip_code).all() if associated_equipment_ids else s.query(Equipment).order_by(Equipment.equip_code).all()

    return render_template(
        "admin/suppliers/detail.html",
        supplier=supplier,
        documents=documents,
        available_equipment=available_equipment,
        today=date.today(),
    )


# ---------- Edit ----------
@bp.get("/suppliers/<int:supplier_id>/edit")
@require_permission("suppliers.edit")
def supplier_edit_get(supplier_id: int):
    s = db_session()
    supplier = s.get(Supplier, supplier_id)
    if not supplier:
        abort(404)
    return render_template("admin/suppliers/edit.html", supplier=supplier)


@bp.post("/suppliers/<int:supplier_id>/edit")
@require_permission("suppliers.edit")
def supplier_edit_post(supplier_id: int):
    s = db_session()
    u = _current_user()
    supplier = s.get(Supplier, supplier_id)
    if not supplier:
        abort(404)

    payload = {
        "name": request.form.get("name"),
        "status": request.form.get("status"),
        "category": request.form.get("category"),
        "product_service_provided": request.form.get("product_service_provided"),
        "address": request.form.get("address"),
        "initial_listing_date": request.form.get("initial_listing_date"),
        "certification_expiration": request.form.get("certification_expiration"),
        "notes": request.form.get("notes"),
    }

    reason = (request.form.get("reason") or "").strip()
    old_status = supplier.status
    new_status = (payload.get("status") or "").strip()

    # Require reason if status changes
    if new_status and new_status != old_status and not reason:
        flash("Reason for change is required when changing status.", "danger")
        return redirect(url_for("suppliers.supplier_edit_get", supplier_id=supplier_id))

    update_supplier(s, supplier, payload, u, reason=reason or None)
    s.commit()

    flash("Supplier updated.", "success")
    return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))


# ---------- Document Upload ----------
@bp.post("/suppliers/<int:supplier_id>/documents/upload")
@require_permission("suppliers.upload")
def supplier_document_upload(supplier_id: int):
    s = db_session()
    u = _current_user()
    supplier = s.get(Supplier, supplier_id)
    if not supplier:
        abort(404)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))

    description = (request.form.get("description") or "").strip() or None
    document_type = (request.form.get("document_type") or "").strip() or None
    content_type = (f.mimetype or "application/octet-stream").strip()
    file_bytes = f.read()

    upload_supplier_document(
        s,
        supplier,
        file_bytes,
        f.filename,
        content_type,
        u,
        description=description,
        document_type=document_type,
    )
    s.commit()

    flash("Document uploaded.", "success")
    return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))


# ---------- Document Download ----------
@bp.get("/suppliers/<int:supplier_id>/documents/<int:doc_id>/download")
@require_permission("suppliers.view")
def supplier_document_download(supplier_id: int, doc_id: int):
    from flask import current_app

    s = db_session()
    u = _current_user()

    supplier = s.get(Supplier, supplier_id)
    if not supplier:
        abort(404)

    doc = s.get(ManagedDocument, doc_id)
    if not doc or doc.supplier_id != supplier_id or doc.is_deleted:
        abort(404)

    storage = storage_from_config(current_app.config)
    fobj = storage.open(doc.storage_key)

    record_event(
        s,
        actor=u,
        action="supplier.document_download",
        entity_type="ManagedDocument",
        entity_id=str(doc.id),
        metadata={"supplier_id": supplier_id, "filename": doc.original_filename},
    )
    s.commit()

    return send_file(
        fobj,
        mimetype=doc.content_type,
        as_attachment=True,
        download_name=doc.original_filename,
        max_age=0,
    )


# ---------- Document Delete ----------
@bp.post("/suppliers/<int:supplier_id>/documents/<int:doc_id>/delete")
@require_permission("suppliers.upload")
def supplier_document_delete(supplier_id: int, doc_id: int):
    s = db_session()
    u = _current_user()

    supplier = s.get(Supplier, supplier_id)
    if not supplier:
        abort(404)

    doc = s.get(ManagedDocument, doc_id)
    if not doc or doc.supplier_id != supplier_id or doc.is_deleted:
        abort(404)

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for deletion is required.", "danger")
        return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))

    delete_supplier_document(s, doc, u, reason)
    s.commit()

    flash("Document deleted.", "success")
    return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))


# ---------- Add Equipment ----------
@bp.post("/suppliers/<int:supplier_id>/equipment")
@require_permission("suppliers.edit")
def supplier_equipment_add(supplier_id: int):
    s = db_session()
    u = _current_user()

    supplier = s.get(Supplier, supplier_id)
    if not supplier:
        abort(404)

    equipment_id = request.form.get("equipment_id")
    if not equipment_id:
        flash("Please select an equipment item.", "danger")
        return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))

    equipment = s.get(Equipment, int(equipment_id))
    if not equipment:
        flash("Equipment not found.", "danger")
        return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))

    # Check for duplicate association
    existing = (
        s.query(EquipmentSupplier)
        .filter(EquipmentSupplier.equipment_id == equipment.id)
        .filter(EquipmentSupplier.supplier_id == supplier_id)
        .one_or_none()
    )
    if existing:
        flash("Equipment is already associated with this supplier.", "danger")
        return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))

    relationship_type = (request.form.get("relationship_type") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    add_supplier_to_equipment(s, equipment, supplier, relationship_type, notes, u)
    s.commit()

    flash(f"Equipment '{equipment.equip_code}' associated.", "success")
    return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))


# ---------- Remove Equipment ----------
@bp.post("/suppliers/<int:supplier_id>/equipment/<int:equipment_id>/remove")
@require_permission("suppliers.edit")
def supplier_equipment_remove(supplier_id: int, equipment_id: int):
    s = db_session()
    u = _current_user()

    supplier = s.get(Supplier, supplier_id)
    if not supplier:
        abort(404)

    assoc = (
        s.query(EquipmentSupplier)
        .filter(EquipmentSupplier.equipment_id == equipment_id)
        .filter(EquipmentSupplier.supplier_id == supplier_id)
        .one_or_none()
    )
    if not assoc:
        flash("Association not found.", "danger")
        return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for removal is required.", "danger")
        return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))

    remove_supplier_from_equipment(s, assoc, u, reason)
    s.commit()

    flash("Equipment association removed.", "success")
    return redirect(url_for("suppliers.supplier_detail", supplier_id=supplier_id))
