"""
Manufacturing admin routes.
Handles Suspension lot tracking, documents, equipment, and materials.
"""
from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, send_file, url_for
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.eqms.db import db_session
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config

from .models import (
    ManufacturingLot,
    ManufacturingLotDocument,
    ManufacturingLotEquipment,
    ManufacturingLotMaterial,
)
from .service import (
    DOCUMENT_TYPES,
    STATUS_TRANSITIONS,
    VALID_STATUSES,
    add_equipment_to_lot,
    add_material_to_lot,
    build_lot_document_storage_key,
    can_transition_to,
    change_lot_status,
    create_lot,
    delete_lot_document,
    group_documents_by_type,
    record_disposition,
    remove_equipment_from_lot,
    remove_material_from_lot,
    update_lot,
    upload_lot_document,
)

bp = Blueprint("manufacturing", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Manufacturing Landing Page
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/")
@require_permission("manufacturing.view")
def manufacturing_index():
    """Manufacturing landing page - product selection."""
    return render_template("admin/manufacturing/index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot List
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension")
@require_permission("manufacturing.view")
def suspension_list():
    """List Suspension lots with filters."""
    s: Session = db_session()

    # Filters
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Base query - only Suspension products
    query = s.query(ManufacturingLot).filter(ManufacturingLot.product_code == "Suspension")

    # Apply filters
    if search:
        like_pat = f"%{search}%"
        query = query.filter(
            or_(
                ManufacturingLot.lot_number.ilike(like_pat),
                ManufacturingLot.work_order.ilike(like_pat),
                ManufacturingLot.operator.ilike(like_pat),
            )
        )

    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter(ManufacturingLot.status == status_filter)

    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(ManufacturingLot.manufacture_date >= df)
        except ValueError:
            pass

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(ManufacturingLot.manufacture_date <= dt)
        except ValueError:
            pass

    # Count and paginate
    total = query.count()
    lots = (
        query.order_by(ManufacturingLot.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    total_pages = (total + per_page - 1) // per_page

    # Build pagination URLs
    def build_url(p):
        args = dict(request.args)
        args["page"] = p
        return url_for("manufacturing.suspension_list", **args)

    return render_template(
        "admin/manufacturing/suspension/list.html",
        lots=lots,
        total=total,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        statuses=VALID_STATUSES,
        search=search,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        build_url=build_url,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot Create
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension/new", methods=["GET"])
@require_permission("manufacturing.create")
def suspension_new_get():
    """Show create lot form."""
    return render_template("admin/manufacturing/suspension/new.html")


@bp.route("/suspension/new", methods=["POST"])
@require_permission("manufacturing.create")
def suspension_new_post():
    """Create a new Suspension lot."""
    s: Session = db_session()

    lot_number = request.form.get("lot_number", "").strip()
    work_order = request.form.get("work_order", "").strip() or None
    manufacture_date_str = request.form.get("manufacture_date", "").strip()
    manufacture_end_date_str = request.form.get("manufacture_end_date", "").strip()
    operator = request.form.get("operator", "").strip() or None
    operator_notes = request.form.get("operator_notes", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    if not lot_number:
        flash("Lot number is required.", "danger")
        return render_template("admin/manufacturing/suspension/new.html")

    # Check uniqueness
    existing = s.query(ManufacturingLot).filter(ManufacturingLot.lot_number == lot_number).first()
    if existing:
        flash(f"Lot number '{lot_number}' already exists.", "danger")
        return render_template("admin/manufacturing/suspension/new.html")

    # Parse dates
    manufacture_date = None
    if manufacture_date_str:
        try:
            manufacture_date = datetime.strptime(manufacture_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid manufacture date format.", "danger")
            return render_template("admin/manufacturing/suspension/new.html")

    manufacture_end_date = None
    if manufacture_end_date_str:
        try:
            manufacture_end_date = datetime.strptime(manufacture_end_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid manufacture end date format.", "danger")
            return render_template("admin/manufacturing/suspension/new.html")

    try:
        lot = create_lot(
            s,
            lot_number=lot_number,
            product_code="Suspension",
            work_order=work_order,
            manufacture_date=manufacture_date,
            manufacture_end_date=manufacture_end_date,
            operator=operator,
            operator_notes=operator_notes,
            notes=notes,
            user=g.current_user,
        )
        s.commit()
        flash(f"Lot '{lot.lot_number}' created.", "success")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))
    except Exception as e:
        s.rollback()
        flash(f"Error creating lot: {e}", "danger")
        return render_template("admin/manufacturing/suspension/new.html")


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot Detail
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension/<int:lot_id>")
@require_permission("manufacturing.view")
def suspension_detail(lot_id: int):
    """View Suspension lot details."""
    s: Session = db_session()

    lot = s.query(ManufacturingLot).filter(ManufacturingLot.id == lot_id).first()
    if not lot:
        flash("Lot not found.", "danger")
        return redirect(url_for("manufacturing.suspension_list"))

    # Group documents by type
    documents_by_type = group_documents_by_type(lot.documents)

    # Get available status transitions
    available_transitions = STATUS_TRANSITIONS.get(lot.status, set())

    # Import Equipment model for dropdown
    from app.eqms.modules.equipment.models import Equipment
    from app.eqms.modules.suppliers.models import Supplier

    all_equipment = s.query(Equipment).filter(Equipment.status == "Active").order_by(Equipment.equip_code).all()
    all_suppliers = s.query(Supplier).filter(Supplier.status == "Approved").order_by(Supplier.name).all()

    return render_template(
        "admin/manufacturing/suspension/detail.html",
        lot=lot,
        documents_by_type=documents_by_type,
        document_types=DOCUMENT_TYPES,
        available_transitions=available_transitions,
        all_equipment=all_equipment,
        all_suppliers=all_suppliers,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot Edit
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension/<int:lot_id>/edit", methods=["GET"])
@require_permission("manufacturing.edit")
def suspension_edit_get(lot_id: int):
    """Show edit lot form."""
    s: Session = db_session()

    lot = s.query(ManufacturingLot).filter(ManufacturingLot.id == lot_id).first()
    if not lot:
        flash("Lot not found.", "danger")
        return redirect(url_for("manufacturing.suspension_list"))

    return render_template("admin/manufacturing/suspension/edit.html", lot=lot)


@bp.route("/suspension/<int:lot_id>/edit", methods=["POST"])
@require_permission("manufacturing.edit")
def suspension_edit_post(lot_id: int):
    """Update a Suspension lot."""
    s: Session = db_session()

    lot = s.query(ManufacturingLot).filter(ManufacturingLot.id == lot_id).first()
    if not lot:
        flash("Lot not found.", "danger")
        return redirect(url_for("manufacturing.suspension_list"))

    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Reason for change is required.", "danger")
        return render_template("admin/manufacturing/suspension/edit.html", lot=lot)

    work_order = request.form.get("work_order", "").strip() or None
    manufacture_date_str = request.form.get("manufacture_date", "").strip()
    manufacture_end_date_str = request.form.get("manufacture_end_date", "").strip()
    operator = request.form.get("operator", "").strip() or None
    operator_notes = request.form.get("operator_notes", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    # Parse dates
    manufacture_date = None
    if manufacture_date_str:
        try:
            manufacture_date = datetime.strptime(manufacture_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid manufacture date format.", "danger")
            return render_template("admin/manufacturing/suspension/edit.html", lot=lot)

    manufacture_end_date = None
    if manufacture_end_date_str:
        try:
            manufacture_end_date = datetime.strptime(manufacture_end_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid manufacture end date format.", "danger")
            return render_template("admin/manufacturing/suspension/edit.html", lot=lot)

    try:
        update_lot(
            s,
            lot,
            reason=reason,
            user=g.current_user,
            work_order=work_order,
            manufacture_date=manufacture_date,
            manufacture_end_date=manufacture_end_date,
            operator=operator,
            operator_notes=operator_notes,
            notes=notes,
        )
        s.commit()
        flash("Lot updated.", "success")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))
    except Exception as e:
        s.rollback()
        flash(f"Error updating lot: {e}", "danger")
        return render_template("admin/manufacturing/suspension/edit.html", lot=lot)


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot Status Change
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension/<int:lot_id>/status", methods=["POST"])
@require_permission("manufacturing.edit")
def suspension_change_status(lot_id: int):
    """Change lot status."""
    s: Session = db_session()

    lot = s.query(ManufacturingLot).filter(ManufacturingLot.id == lot_id).first()
    if not lot:
        flash("Lot not found.", "danger")
        return redirect(url_for("manufacturing.suspension_list"))

    new_status = request.form.get("new_status", "").strip()
    reason = request.form.get("reason", "").strip()

    if not new_status:
        flash("New status is required.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    if not reason:
        flash("Reason for status change is required.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    # Check if transition is valid
    can_change, errors = can_transition_to(lot, new_status)
    if not can_change:
        for err in errors:
            flash(err, "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    try:
        change_lot_status(s, lot, new_status, reason, g.current_user)
        s.commit()
        flash(f"Status changed to '{new_status}'.", "success")
    except Exception as e:
        s.rollback()
        flash(f"Error changing status: {e}", "danger")

    return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot Disposition
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension/<int:lot_id>/disposition", methods=["POST"])
@require_permission("manufacturing.disposition")
def suspension_record_disposition(lot_id: int):
    """Record QA disposition."""
    s: Session = db_session()

    lot = s.query(ManufacturingLot).filter(ManufacturingLot.id == lot_id).first()
    if not lot:
        flash("Lot not found.", "danger")
        return redirect(url_for("manufacturing.suspension_list"))

    disposition = request.form.get("disposition", "").strip()
    notes = request.form.get("disposition_notes", "").strip()
    disposition_date_str = request.form.get("disposition_date", "").strip()

    if not disposition:
        flash("Disposition is required.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    if not notes:
        flash("Disposition notes are required.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    disposition_date = None
    if disposition_date_str:
        try:
            disposition_date = datetime.strptime(disposition_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid disposition date format.", "danger")
            return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    try:
        record_disposition(
            s,
            lot,
            disposition=disposition,
            notes=notes,
            disposition_date=disposition_date,
            user=g.current_user,
        )

        # After disposition recorded, also change the status
        if disposition == "Released":
            can_release, errors = can_transition_to(lot, "Released")
            if can_release:
                lot.status = "Released"
            else:
                for err in errors:
                    flash(err, "warning")
        elif disposition == "Rejected":
            can_reject, errors = can_transition_to(lot, "Rejected")
            if can_reject:
                lot.status = "Rejected"
            else:
                for err in errors:
                    flash(err, "warning")

        s.commit()
        flash(f"Disposition '{disposition}' recorded.", "success")
    except Exception as e:
        s.rollback()
        flash(f"Error recording disposition: {e}", "danger")

    return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot Document Upload/Download/Delete
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension/<int:lot_id>/documents/upload", methods=["POST"])
@require_permission("manufacturing.upload")
def suspension_document_upload(lot_id: int):
    """Upload a document to a lot."""
    s: Session = db_session()

    lot = s.query(ManufacturingLot).filter(ManufacturingLot.id == lot_id).first()
    if not lot:
        flash("Lot not found.", "danger")
        return redirect(url_for("manufacturing.suspension_list"))

    f = request.files.get("file")
    if not f or f.filename == "":
        flash("No file selected.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    document_type = request.form.get("document_type", "").strip() or None
    description = request.form.get("description", "").strip() or None

    try:
        file_bytes = f.read()
        upload_lot_document(
            s,
            lot,
            file_bytes=file_bytes,
            filename=f.filename,
            content_type=f.content_type or "application/octet-stream",
            user=g.current_user,
            document_type=document_type,
            description=description,
            config=current_app.config,
        )
        s.commit()
        flash("Document uploaded.", "success")
    except Exception as e:
        s.rollback()
        flash(f"Error uploading document: {e}", "danger")

    return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))


@bp.route("/suspension/<int:lot_id>/documents/<int:doc_id>/download")
@require_permission("manufacturing.view")
def suspension_document_download(lot_id: int, doc_id: int):
    """Download a lot document."""
    s: Session = db_session()

    doc = (
        s.query(ManufacturingLotDocument)
        .filter(ManufacturingLotDocument.id == doc_id, ManufacturingLotDocument.lot_id == lot_id)
        .first()
    )
    if not doc or doc.is_deleted:
        flash("Document not found.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))

    storage = storage_from_config(current_app.config)
    try:
        fobj = storage.open(doc.storage_key)
        return send_file(
            fobj,
            mimetype=doc.content_type,
            as_attachment=True,
            download_name=doc.original_filename,
            max_age=0,
        )
    except Exception as e:
        flash(f"Error downloading document: {e}", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))


@bp.route("/suspension/<int:lot_id>/documents/<int:doc_id>/delete", methods=["POST"])
@require_permission("manufacturing.edit")
def suspension_document_delete(lot_id: int, doc_id: int):
    """Delete a lot document (soft-delete)."""
    s: Session = db_session()

    doc = (
        s.query(ManufacturingLotDocument)
        .filter(ManufacturingLotDocument.id == doc_id, ManufacturingLotDocument.lot_id == lot_id)
        .first()
    )
    if not doc:
        flash("Document not found.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))

    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Reason for deletion is required.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))

    try:
        delete_lot_document(s, doc, user=g.current_user, reason=reason)
        s.commit()
        flash("Document deleted.", "success")
    except Exception as e:
        s.rollback()
        flash(f"Error deleting document: {e}", "danger")

    return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot Equipment
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension/<int:lot_id>/equipment", methods=["POST"])
@require_permission("manufacturing.edit")
def suspension_equipment_add(lot_id: int):
    """Add equipment to a lot."""
    s: Session = db_session()

    lot = s.query(ManufacturingLot).filter(ManufacturingLot.id == lot_id).first()
    if not lot:
        flash("Lot not found.", "danger")
        return redirect(url_for("manufacturing.suspension_list"))

    equipment_id_str = request.form.get("equipment_id", "").strip()
    equipment_name = request.form.get("equipment_name", "").strip() or None
    usage_notes = request.form.get("usage_notes", "").strip() or None

    equipment_id = None
    if equipment_id_str:
        try:
            equipment_id = int(equipment_id_str)
        except ValueError:
            pass

    if not equipment_id and not equipment_name:
        flash("Select equipment or enter a name.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    try:
        add_equipment_to_lot(
            s,
            lot,
            equipment_id=equipment_id,
            equipment_name=equipment_name if not equipment_id else None,
            usage_notes=usage_notes,
            user=g.current_user,
        )
        s.commit()
        flash("Equipment added.", "success")
    except Exception as e:
        s.rollback()
        flash(f"Error adding equipment: {e}", "danger")

    return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))


@bp.route("/suspension/<int:lot_id>/equipment/<int:assoc_id>/remove", methods=["POST"])
@require_permission("manufacturing.edit")
def suspension_equipment_remove(lot_id: int, assoc_id: int):
    """Remove equipment from a lot."""
    s: Session = db_session()

    assoc = (
        s.query(ManufacturingLotEquipment)
        .filter(ManufacturingLotEquipment.id == assoc_id, ManufacturingLotEquipment.lot_id == lot_id)
        .first()
    )
    if not assoc:
        flash("Equipment association not found.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))

    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Reason for removal is required.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))

    try:
        remove_equipment_from_lot(s, assoc, user=g.current_user, reason=reason)
        s.commit()
        flash("Equipment removed.", "success")
    except Exception as e:
        s.rollback()
        flash(f"Error removing equipment: {e}", "danger")

    return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))


# ─────────────────────────────────────────────────────────────────────────────
# Suspension Lot Materials
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/suspension/<int:lot_id>/materials", methods=["POST"])
@require_permission("manufacturing.edit")
def suspension_material_add(lot_id: int):
    """Add material to a lot."""
    s: Session = db_session()

    lot = s.query(ManufacturingLot).filter(ManufacturingLot.id == lot_id).first()
    if not lot:
        flash("Lot not found.", "danger")
        return redirect(url_for("manufacturing.suspension_list"))

    material_identifier = request.form.get("material_identifier", "").strip()
    material_name = request.form.get("material_name", "").strip() or None
    supplier_id_str = request.form.get("supplier_id", "").strip()
    quantity = request.form.get("quantity", "").strip() or None
    mat_lot_number = request.form.get("lot_number", "").strip() or None
    usage_notes = request.form.get("usage_notes", "").strip() or None

    if not material_identifier:
        flash("Material identifier is required.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))

    supplier_id = None
    if supplier_id_str:
        try:
            supplier_id = int(supplier_id_str)
        except ValueError:
            pass

    try:
        add_material_to_lot(
            s,
            lot,
            material_identifier=material_identifier,
            material_name=material_name,
            supplier_id=supplier_id,
            quantity=quantity,
            lot_number=mat_lot_number,
            usage_notes=usage_notes,
            user=g.current_user,
        )
        s.commit()
        flash("Material added.", "success")
    except Exception as e:
        s.rollback()
        flash(f"Error adding material: {e}", "danger")

    return redirect(url_for("manufacturing.suspension_detail", lot_id=lot.id))


@bp.route("/suspension/<int:lot_id>/materials/<int:assoc_id>/remove", methods=["POST"])
@require_permission("manufacturing.edit")
def suspension_material_remove(lot_id: int, assoc_id: int):
    """Remove material from a lot."""
    s: Session = db_session()

    assoc = (
        s.query(ManufacturingLotMaterial)
        .filter(ManufacturingLotMaterial.id == assoc_id, ManufacturingLotMaterial.lot_id == lot_id)
        .first()
    )
    if not assoc:
        flash("Material association not found.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))

    reason = request.form.get("reason", "").strip()
    if not reason:
        flash("Reason for removal is required.", "danger")
        return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))

    try:
        remove_material_from_lot(s, assoc, user=g.current_user, reason=reason)
        s.commit()
        flash("Material removed.", "success")
    except Exception as e:
        s.rollback()
        flash(f"Error removing material: {e}", "danger")

    return redirect(url_for("manufacturing.suspension_detail", lot_id=lot_id))


# ─────────────────────────────────────────────────────────────────────────────
# ClearTract Foley Catheters Placeholder
# ─────────────────────────────────────────────────────────────────────────────


@bp.route("/cleartract-foley-catheters")
@require_permission("manufacturing.view")
def cleartract_placeholder():
    """ClearTract Foley Catheters placeholder page."""
    return render_template("admin/manufacturing/cleartract_placeholder.html")
