from __future__ import annotations

from datetime import date

import json

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, send_file, url_for

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.equipment.models import Equipment, EquipmentSupplier, ManagedDocument
from app.eqms.modules.equipment.service import (
    add_supplier_to_equipment,
    create_equipment,
    delete_equipment_document,
    remove_supplier_from_equipment,
    update_equipment,
    upload_equipment_document,
    validate_equipment_payload,
)
from app.eqms.modules.suppliers.models import Supplier
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config

bp = Blueprint("equipment", __name__)


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


def _parse_custom_fields(raw: str | None) -> tuple[dict | None, str | None]:
    if not raw or not raw.strip():
        return None, None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"Custom fields JSON is invalid: {e}"
    if not isinstance(value, dict):
        return None, "Custom fields must be a JSON object."
    return value, None


# ---------- List ----------
@bp.get("/equipment")
@require_permission("equipment.view")
def equipment_list():
    s = db_session()

    # Filters
    search = (request.args.get("q") or "").strip()
    status_filter = (request.args.get("status") or "").strip()
    location_filter = (request.args.get("location") or "").strip()
    cal_overdue = request.args.get("cal_overdue") == "1"
    pm_overdue = request.args.get("pm_overdue") == "1"

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 50

    q = s.query(Equipment)

    if search:
        like = f"%{search}%"
        q = q.filter(
            (Equipment.equip_code.ilike(like))
            | (Equipment.description.ilike(like))
            | (Equipment.mfg.ilike(like))
            | (Equipment.model_no.ilike(like))
            | (Equipment.serial_no.ilike(like))
        )

    if status_filter:
        q = q.filter(Equipment.status == status_filter)

    if location_filter:
        q = q.filter(Equipment.location == location_filter)

    today = date.today()
    if cal_overdue:
        q = q.filter(Equipment.cal_due_date < today)

    if pm_overdue:
        q = q.filter(Equipment.pm_due_date < today)

    total = q.count()
    equipment = q.order_by(Equipment.equip_code.asc()).offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page

    # Get unique locations for filter dropdown
    locations = s.query(Equipment.location).filter(Equipment.location.isnot(None)).distinct().all()
    locations = sorted([loc[0] for loc in locations if loc[0]])

    # Build pagination URL helper
    def build_url(p):
        args = dict(request.args)
        args["page"] = p
        return url_for("equipment.equipment_list", **args)

    return render_template(
        "admin/equipment/list.html",
        equipment=equipment,
        search=search,
        status_filter=status_filter,
        location_filter=location_filter,
        cal_overdue=cal_overdue,
        pm_overdue=pm_overdue,
        locations=locations,
        today=today,
        page=page,
        total=total,
        total_pages=total_pages,
        build_url=build_url,
    )


# ---------- New ----------
@bp.get("/equipment/new")
@require_permission("equipment.create")
def equipment_new_get():
    return render_template("admin/equipment/new.html")


@bp.post("/equipment/new")
@require_permission("equipment.create")
def equipment_new_post():
    s = db_session()
    u = _current_user()

    custom_fields, custom_fields_error = _parse_custom_fields(request.form.get("custom_fields"))
    if custom_fields_error:
        flash(custom_fields_error, "danger")
        return redirect(url_for("equipment.equipment_new_get"))

    payload = {
        "equip_code": request.form.get("equip_code"),
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "mfg": request.form.get("mfg"),
        "model_no": request.form.get("model_no"),
        "serial_no": request.form.get("serial_no"),
        "date_in_service": request.form.get("date_in_service"),
        "location": request.form.get("location"),
        "cal_interval": request.form.get("cal_interval"),
        "last_cal_date": request.form.get("last_cal_date"),
        "cal_due_date": request.form.get("cal_due_date"),
        "pm_interval": request.form.get("pm_interval"),
        "last_pm_date": request.form.get("last_pm_date"),
        "pm_due_date": request.form.get("pm_due_date"),
        "comments": request.form.get("comments"),
        "custom_fields": custom_fields,
    }

    errors = validate_equipment_payload(payload)
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("equipment.equipment_new_get"))

    # Check for duplicate equip_code
    existing = s.query(Equipment).filter(Equipment.equip_code == payload["equip_code"].strip()).one_or_none()
    if existing:
        flash("Equipment code already exists.", "danger")
        return redirect(url_for("equipment.equipment_new_get"))

    equipment = create_equipment(s, payload, u)
    s.commit()

    flash("Equipment created.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment.id))


# ---------- Detail ----------
@bp.get("/equipment/<int:equipment_id>")
@require_permission("equipment.view")
def equipment_detail(equipment_id: int):
    s = db_session()
    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    # Get non-deleted documents
    documents = (
        s.query(ManagedDocument)
        .filter(ManagedDocument.entity_type == "equipment")
        .filter(ManagedDocument.entity_id == equipment.id)
        .filter(ManagedDocument.is_deleted == False)
        .order_by(ManagedDocument.uploaded_at.desc())
        .all()
    )

    # Get all suppliers for the "Add Supplier" dropdown (excluding already associated)
    associated_supplier_ids = {assoc.supplier_id for assoc in equipment.supplier_associations}
    available_suppliers = s.query(Supplier).filter(~Supplier.id.in_(associated_supplier_ids)).order_by(Supplier.name).all() if associated_supplier_ids else s.query(Supplier).order_by(Supplier.name).all()

    return render_template(
        "admin/equipment/detail.html",
        equipment=equipment,
        documents=documents,
        available_suppliers=available_suppliers,
        today=date.today(),
    )


# ---------- Edit ----------
@bp.get("/equipment/<int:equipment_id>/edit")
@require_permission("equipment.edit")
def equipment_edit_get(equipment_id: int):
    s = db_session()
    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)
    return render_template("admin/equipment/edit.html", equipment=equipment)


@bp.post("/equipment/<int:equipment_id>/edit")
@require_permission("equipment.edit")
def equipment_edit_post(equipment_id: int):
    s = db_session()
    u = _current_user()
    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    custom_fields, custom_fields_error = _parse_custom_fields(request.form.get("custom_fields"))
    if custom_fields_error:
        flash(custom_fields_error, "danger")
        return redirect(url_for("equipment.equipment_edit_get", equipment_id=equipment_id))

    payload = {
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "mfg": request.form.get("mfg"),
        "model_no": request.form.get("model_no"),
        "serial_no": request.form.get("serial_no"),
        "date_in_service": request.form.get("date_in_service"),
        "location": request.form.get("location"),
        "cal_interval": request.form.get("cal_interval"),
        "last_cal_date": request.form.get("last_cal_date"),
        "cal_due_date": request.form.get("cal_due_date"),
        "pm_interval": request.form.get("pm_interval"),
        "last_pm_date": request.form.get("last_pm_date"),
        "pm_due_date": request.form.get("pm_due_date"),
        "comments": request.form.get("comments"),
        "custom_fields": custom_fields,
    }

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for change is required.", "danger")
        return redirect(url_for("equipment.equipment_edit_get", equipment_id=equipment_id))

    update_equipment(s, equipment, payload, u, reason=reason)
    s.commit()

    flash("Equipment updated.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))


# ---------- Document Upload ----------
@bp.post("/equipment/<int:equipment_id>/documents/upload")
@require_permission("equipment.upload")
def equipment_document_upload(equipment_id: int):
    s = db_session()
    u = _current_user()
    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    description = (request.form.get("description") or "").strip() or None
    document_type = (request.form.get("document_type") or "").strip() or None
    content_type = (f.mimetype or "application/octet-stream").strip()
    file_bytes = f.read()

    upload_equipment_document(
        s,
        equipment,
        file_bytes,
        f.filename,
        content_type,
        u,
        description=description,
        document_type=document_type,
    )
    s.commit()

    flash("Document uploaded.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))


@bp.post("/equipment/extract-from-pdf")
@require_permission("equipment.create")
def equipment_extract_from_pdf_new():
    """Extract field values from uploaded PDF for new equipment forms."""
    from app.eqms.modules.equipment.parsers.pdf import extract_equipment_fields_from_pdf

    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf_file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    pdf_bytes = file.read()
    extracted = extract_equipment_fields_from_pdf(pdf_bytes)
    return jsonify(
        {
            "success": True,
            "extracted_fields": extracted,
            "message": f"Extracted {len(extracted)} field(s) from PDF. Review and edit as needed.",
        }
    )


@bp.post("/equipment/<int:equipment_id>/extract-from-pdf")
@require_permission("equipment.upload")
def equipment_extract_from_pdf(equipment_id: int):
    """Extract field values from uploaded PDF and return as JSON for form auto-fill."""
    from app.eqms.modules.equipment.parsers.pdf import extract_equipment_fields_from_pdf

    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf_file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    pdf_bytes = file.read()
    extracted = extract_equipment_fields_from_pdf(pdf_bytes)
    return jsonify(
        {
            "success": True,
            "extracted_fields": extracted,
            "message": f"Extracted {len(extracted)} field(s) from PDF. Review and edit as needed.",
        }
    )


# ---------- Document Download ----------
@bp.get("/equipment/<int:equipment_id>/documents/<int:doc_id>/download")
@require_permission("equipment.view")
def equipment_document_download(equipment_id: int, doc_id: int):
    from flask import current_app
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    doc = s.get(ManagedDocument, doc_id)
    if not doc or doc.equipment_id != equipment_id or doc.is_deleted:
        abort(404)

    storage = storage_from_config(current_app.config)
    fobj = storage.open(doc.storage_key)

    record_event(
        s,
        actor=u,
        action="equipment.document_download",
        entity_type="ManagedDocument",
        entity_id=str(doc.id),
        metadata={"equipment_id": equipment_id, "filename": doc.original_filename},
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
@bp.post("/equipment/<int:equipment_id>/documents/<int:doc_id>/delete")
@require_permission("equipment.upload")
def equipment_document_delete(equipment_id: int, doc_id: int):
    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    doc = s.get(ManagedDocument, doc_id)
    if not doc or doc.equipment_id != equipment_id or doc.is_deleted:
        abort(404)

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for deletion is required.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    delete_equipment_document(s, doc, u, reason)
    s.commit()

    flash("Document deleted.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))


# ---------- Add Supplier ----------
@bp.post("/equipment/<int:equipment_id>/suppliers")
@require_permission("equipment.edit")
def equipment_supplier_add(equipment_id: int):
    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    supplier_id = request.form.get("supplier_id")
    if not supplier_id:
        flash("Please select a supplier.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    supplier = s.get(Supplier, int(supplier_id))
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    # Check for duplicate association
    existing = (
        s.query(EquipmentSupplier)
        .filter(EquipmentSupplier.equipment_id == equipment_id)
        .filter(EquipmentSupplier.supplier_id == supplier.id)
        .one_or_none()
    )
    if existing:
        flash("Supplier is already associated with this equipment.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    relationship_type = (request.form.get("relationship_type") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    add_supplier_to_equipment(s, equipment, supplier, relationship_type, notes, u)
    s.commit()

    flash(f"Supplier '{supplier.name}' associated.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))


# ---------- Remove Supplier ----------
@bp.post("/equipment/<int:equipment_id>/suppliers/<int:supplier_id>/remove")
@require_permission("equipment.edit")
def equipment_supplier_remove(equipment_id: int, supplier_id: int):
    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    assoc = (
        s.query(EquipmentSupplier)
        .filter(EquipmentSupplier.equipment_id == equipment_id)
        .filter(EquipmentSupplier.supplier_id == supplier_id)
        .one_or_none()
    )
    if not assoc:
        flash("Association not found.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for removal is required.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    remove_supplier_from_equipment(s, assoc, u, reason)
    s.commit()

    flash("Supplier association removed.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))
