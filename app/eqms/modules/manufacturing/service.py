"""
Manufacturing service layer.
Handles lot CRUD, status transitions, validation, and document management.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import TYPE_CHECKING

from werkzeug.utils import secure_filename
from sqlalchemy.orm import Session

from app.eqms.audit import record_event
from app.eqms.storage import storage_from_config

from .models import (
    ManufacturingLot,
    ManufacturingLotDocument,
    ManufacturingLotEquipment,
    ManufacturingLotMaterial,
)

if TYPE_CHECKING:
    from app.eqms.models import User


# Valid statuses
VALID_STATUSES = {"Draft", "In-Process", "Quarantined", "Released", "Rejected"}

# Valid status transitions
STATUS_TRANSITIONS = {
    "Draft": {"In-Process"},
    "In-Process": {"Quarantined"},
    "Quarantined": {"Released", "Rejected"},
    "Released": set(),
    "Rejected": set(),
}

# Document types for suspension lots
DOCUMENT_TYPES = [
    "Traveler",
    "QC Report",
    "COA",
    "Label",
    "Release Evidence",
    "Receiving",
    "Environmental Monitoring",
    "In-Process Record",
    "Other",
]


def create_lot(
    s: Session,
    *,
    lot_number: str,
    product_code: str = "Suspension",
    status: str = "Draft",
    work_order: str | None = None,
    manufacture_date: date | None = None,
    manufacture_end_date: date | None = None,
    operator: str | None = None,
    operator_notes: str | None = None,
    notes: str | None = None,
    user: User,
) -> ManufacturingLot:
    """Create a new manufacturing lot."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    lot = ManufacturingLot(
        lot_number=lot_number.strip(),
        product_code=product_code,
        status=status,
        work_order=work_order.strip() if work_order else None,
        manufacture_date=manufacture_date,
        manufacture_end_date=manufacture_end_date,
        operator=operator.strip() if operator else None,
        operator_notes=operator_notes.strip() if operator_notes else None,
        notes=notes.strip() if notes else None,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    s.add(lot)
    s.flush()  # Get ID

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.create",
        entity_type="ManufacturingLot",
        entity_id=str(lot.id),
        metadata={
            "lot_number": lot.lot_number,
            "product_code": lot.product_code,
            "status": lot.status,
        },
    )

    return lot


def update_lot(
    s: Session,
    lot: ManufacturingLot,
    *,
    reason: str,
    user: User,
    work_order: str | None = None,
    manufacture_date: date | None = None,
    manufacture_end_date: date | None = None,
    operator: str | None = None,
    operator_notes: str | None = None,
    notes: str | None = None,
) -> ManufacturingLot:
    """Update a manufacturing lot (non-status fields only)."""
    changes = {}

    if work_order is not None and lot.work_order != work_order:
        changes["work_order"] = {"from": lot.work_order, "to": work_order}
        lot.work_order = work_order.strip() if work_order else None

    if manufacture_date is not None and lot.manufacture_date != manufacture_date:
        changes["manufacture_date"] = {
            "from": str(lot.manufacture_date) if lot.manufacture_date else None,
            "to": str(manufacture_date) if manufacture_date else None,
        }
        lot.manufacture_date = manufacture_date

    if manufacture_end_date is not None and lot.manufacture_end_date != manufacture_end_date:
        changes["manufacture_end_date"] = {
            "from": str(lot.manufacture_end_date) if lot.manufacture_end_date else None,
            "to": str(manufacture_end_date) if manufacture_end_date else None,
        }
        lot.manufacture_end_date = manufacture_end_date

    if operator is not None and lot.operator != operator:
        changes["operator"] = {"from": lot.operator, "to": operator}
        lot.operator = operator.strip() if operator else None

    if operator_notes is not None and lot.operator_notes != operator_notes:
        changes["operator_notes"] = {"from": "...", "to": "..."}  # Don't log full text
        lot.operator_notes = operator_notes.strip() if operator_notes else None

    if notes is not None and lot.notes != notes:
        changes["notes"] = {"from": "...", "to": "..."}  # Don't log full text
        lot.notes = notes.strip() if notes else None

    lot.updated_at = datetime.utcnow()
    lot.updated_by_user_id = user.id

    if changes:
        record_event(
            s,
            actor=user,
            action="manufacturing.lot.edit",
            entity_type="ManufacturingLot",
            entity_id=str(lot.id),
            reason=reason,
            metadata={
                "lot_number": lot.lot_number,
                "changes": changes,
            },
        )

    return lot


def can_transition_to(lot: ManufacturingLot, new_status: str) -> tuple[bool, list[str]]:
    """Check if lot can transition to new_status."""
    errors = []

    if lot.status not in STATUS_TRANSITIONS:
        errors.append(f"Current status '{lot.status}' is invalid")
        return False, errors

    if new_status not in STATUS_TRANSITIONS[lot.status]:
        errors.append(f"Cannot transition from '{lot.status}' to '{new_status}'")
        return False, errors

    if new_status == "Quarantined":
        return can_transition_to_quarantined(lot)
    elif new_status == "Released":
        return can_transition_to_released(lot)
    elif new_status == "Rejected":
        return can_transition_to_rejected(lot)

    return True, []


def can_transition_to_quarantined(lot: ManufacturingLot) -> tuple[bool, list[str]]:
    """Check if lot can transition to Quarantined."""
    errors = []

    if not lot.manufacture_date:
        errors.append("Manufacture date is required")

    # Check for label document
    has_label = any(
        doc.document_type == "Label" and not doc.is_deleted
        for doc in lot.documents
    )
    if not has_label:
        errors.append("Label document is required")

    return len(errors) == 0, errors


def can_transition_to_released(lot: ManufacturingLot) -> tuple[bool, list[str]]:
    """Check if lot can transition to Released."""
    errors = []

    if lot.status != "Quarantined":
        errors.append("Lot must be Quarantined before release")

    # Check for QC Report
    has_qc = any(
        doc.document_type == "QC Report" and not doc.is_deleted
        for doc in lot.documents
    )
    if not has_qc:
        errors.append("QC Report is required")

    # Check for COA
    has_coa = any(
        doc.document_type == "COA" and not doc.is_deleted
        for doc in lot.documents
    )
    if not has_coa:
        errors.append("COA is required")

    # Check for disposition
    if not lot.disposition or lot.disposition != "Released":
        errors.append("QA disposition must be 'Released'")

    if not lot.disposition_notes:
        errors.append("Disposition notes are required")

    if not lot.disposition_by_user_id:
        errors.append("Disposition must be recorded by a user")

    return len(errors) == 0, errors


def can_transition_to_rejected(lot: ManufacturingLot) -> tuple[bool, list[str]]:
    """Check if lot can transition to Rejected."""
    errors = []

    if lot.status != "Quarantined":
        errors.append("Lot must be Quarantined before rejection")

    if not lot.disposition or lot.disposition != "Rejected":
        errors.append("QA disposition must be 'Rejected'")

    if not lot.disposition_notes:
        errors.append("Disposition notes are required")

    if not lot.disposition_by_user_id:
        errors.append("Disposition must be recorded by a user")

    return len(errors) == 0, errors


def change_lot_status(
    s: Session,
    lot: ManufacturingLot,
    new_status: str,
    reason: str,
    user: User,
) -> ManufacturingLot:
    """Change lot status with validation."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {new_status}")

    can_change, errors = can_transition_to(lot, new_status)
    if not can_change:
        raise ValueError("; ".join(errors))

    old_status = lot.status
    lot.status = new_status
    lot.updated_at = datetime.utcnow()
    lot.updated_by_user_id = user.id

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.status_change",
        entity_type="ManufacturingLot",
        entity_id=str(lot.id),
        reason=reason,
        metadata={
            "lot_number": lot.lot_number,
            "from": old_status,
            "to": new_status,
            "status": new_status,
        },
    )

    return lot


def record_disposition(
    s: Session,
    lot: ManufacturingLot,
    *,
    disposition: str,
    notes: str,
    disposition_date: date | None = None,
    user: User,
) -> ManufacturingLot:
    """Record QA disposition and optionally change status to Released/Rejected."""
    if disposition not in ("Released", "Rejected"):
        raise ValueError(f"Invalid disposition: {disposition}")

    if lot.status != "Quarantined":
        raise ValueError("Lot must be Quarantined to record disposition")

    lot.disposition = disposition
    lot.disposition_notes = notes.strip()
    lot.disposition_date = disposition_date or date.today()
    lot.disposition_by_user_id = user.id
    lot.updated_at = datetime.utcnow()
    lot.updated_by_user_id = user.id

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.disposition",
        entity_type="ManufacturingLot",
        entity_id=str(lot.id),
        reason=notes.strip(),
        metadata={
            "lot_number": lot.lot_number,
            "disposition": disposition,
            "status": lot.status,
        },
    )

    return lot


def build_lot_document_storage_key(
    product_code: str,
    lot_number: str,
    filename: str,
    upload_date: date | None = None,
) -> str:
    """Build deterministic storage key for manufacturing lot document."""
    if upload_date is None:
        upload_date = date.today()

    # Normalize product_code and lot_number for path safety
    safe_product = product_code.lower().replace(" ", "-").replace("/", "_").replace("\\", "_")
    safe_lot = lot_number.replace("/", "_").replace("\\", "_").replace(" ", "_")
    safe_filename = secure_filename(filename) or "document.bin"

    return f"manufacturing/{safe_product}/{safe_lot}/{upload_date.isoformat()}/{safe_filename}"


def upload_lot_document(
    s: Session,
    lot: ManufacturingLot,
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user: User,
    document_type: str | None = None,
    description: str | None = None,
) -> ManufacturingLotDocument:
    """Upload a document to a manufacturing lot."""
    storage = storage_from_config()

    # Compute hash
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    size_bytes = len(file_bytes)

    # Build storage key
    storage_key = build_lot_document_storage_key(
        lot.product_code,
        lot.lot_number,
        filename,
    )

    # Upload to storage
    storage.put(storage_key, file_bytes, content_type=content_type)

    # Create record
    doc = ManufacturingLotDocument(
        lot_id=lot.id,
        storage_key=storage_key,
        original_filename=filename,
        content_type=content_type,
        sha256=sha256,
        size_bytes=size_bytes,
        document_type=document_type,
        description=description.strip() if description else None,
        uploaded_by_user_id=user.id,
    )
    s.add(doc)
    s.flush()

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.document_upload",
        entity_type="ManufacturingLotDocument",
        entity_id=str(doc.id),
        metadata={
            "lot_id": lot.id,
            "lot_number": lot.lot_number,
            "filename": filename,
            "document_type": document_type,
        },
    )

    return doc


def delete_lot_document(
    s: Session,
    doc: ManufacturingLotDocument,
    *,
    user: User,
    reason: str,
) -> None:
    """Soft-delete a lot document."""
    doc.is_deleted = True
    doc.deleted_at = datetime.utcnow()
    doc.deleted_by_user_id = user.id

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.document_delete",
        entity_type="ManufacturingLotDocument",
        entity_id=str(doc.id),
        reason=reason,
        metadata={
            "lot_id": doc.lot_id,
            "filename": doc.original_filename,
        },
    )


def add_equipment_to_lot(
    s: Session,
    lot: ManufacturingLot,
    *,
    equipment_id: int | None = None,
    equipment_name: str | None = None,
    usage_notes: str | None = None,
    user: User,
) -> ManufacturingLotEquipment:
    """Add equipment to a lot."""
    if equipment_id is None and not equipment_name:
        raise ValueError("Either equipment_id or equipment_name must be provided")

    assoc = ManufacturingLotEquipment(
        lot_id=lot.id,
        equipment_id=equipment_id,
        equipment_name=equipment_name.strip() if equipment_name else None,
        usage_notes=usage_notes.strip() if usage_notes else None,
        created_by_user_id=user.id,
    )
    s.add(assoc)
    s.flush()

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.equipment_added",
        entity_type="ManufacturingLotEquipment",
        entity_id=str(assoc.id),
        metadata={
            "lot_id": lot.id,
            "equipment_id": equipment_id,
            "equipment_name": equipment_name,
        },
    )

    return assoc


def remove_equipment_from_lot(
    s: Session,
    assoc: ManufacturingLotEquipment,
    *,
    user: User,
    reason: str,
) -> None:
    """Remove equipment from a lot."""
    lot_id = assoc.lot_id
    equipment_name = assoc.equipment_name or (assoc.equipment.equip_code if assoc.equipment else "Unknown")

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.equipment_removed",
        entity_type="ManufacturingLotEquipment",
        entity_id=str(assoc.id),
        reason=reason,
        metadata={
            "lot_id": lot_id,
            "equipment_name": equipment_name,
        },
    )

    s.delete(assoc)


def add_material_to_lot(
    s: Session,
    lot: ManufacturingLot,
    *,
    material_identifier: str,
    material_name: str | None = None,
    supplier_id: int | None = None,
    quantity: str | None = None,
    lot_number: str | None = None,
    usage_notes: str | None = None,
    user: User,
) -> ManufacturingLotMaterial:
    """Add material to a lot."""
    if not material_identifier:
        raise ValueError("material_identifier is required")

    assoc = ManufacturingLotMaterial(
        lot_id=lot.id,
        material_identifier=material_identifier.strip(),
        material_name=material_name.strip() if material_name else None,
        supplier_id=supplier_id,
        quantity=quantity.strip() if quantity else None,
        lot_number=lot_number.strip() if lot_number else None,
        usage_notes=usage_notes.strip() if usage_notes else None,
        created_by_user_id=user.id,
    )
    s.add(assoc)
    s.flush()

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.material_added",
        entity_type="ManufacturingLotMaterial",
        entity_id=str(assoc.id),
        metadata={
            "lot_id": lot.id,
            "material_identifier": material_identifier,
            "supplier_id": supplier_id,
        },
    )

    return assoc


def remove_material_from_lot(
    s: Session,
    assoc: ManufacturingLotMaterial,
    *,
    user: User,
    reason: str,
) -> None:
    """Remove material from a lot."""
    lot_id = assoc.lot_id
    material_name = assoc.material_name or assoc.material_identifier

    record_event(
        s,
        actor=user,
        action="manufacturing.lot.material_removed",
        entity_type="ManufacturingLotMaterial",
        entity_id=str(assoc.id),
        reason=reason,
        metadata={
            "lot_id": lot_id,
            "material_name": material_name,
        },
    )

    s.delete(assoc)


def group_documents_by_type(documents: list[ManufacturingLotDocument]) -> dict[str, list[ManufacturingLotDocument]]:
    """Group documents by document_type for display."""
    result: dict[str, list[ManufacturingLotDocument]] = {}
    for doc in documents:
        if doc.is_deleted:
            continue
        doc_type = doc.document_type or "Other"
        if doc_type not in result:
            result[doc_type] = []
        result[doc_type].append(doc)
    return result
