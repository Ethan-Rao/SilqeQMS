from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import TYPE_CHECKING

from werkzeug.utils import secure_filename

from app.eqms.audit import record_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.models import User
    from app.eqms.modules.equipment.models import Equipment, EquipmentSupplier, ManagedDocument
    from app.eqms.modules.suppliers.models import Supplier


VALID_STATUSES = ("Active", "Inactive", "Retired", "Calibration Overdue", "PM Overdue")


def parse_date(s: str | None) -> date | None:
    """Parse YYYY-MM-DD date string."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    return date.fromisoformat(s)


def parse_int(s: str | None) -> int | None:
    """Parse integer string."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    return int(s)


def validate_equipment_payload(payload: dict) -> list[str]:
    """Validate equipment creation/update payload. Returns list of errors."""
    errors = []
    equip_code = (payload.get("equip_code") or "").strip()
    if not equip_code:
        errors.append("Equipment code is required.")
    status = (payload.get("status") or "").strip()
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
    return errors


def create_equipment(s: "Session", payload: dict, user: "User") -> "Equipment":
    """Create new equipment."""
    from app.eqms.modules.equipment.models import Equipment

    now = datetime.utcnow()
    equipment = Equipment(
        equip_code=(payload.get("equip_code") or "").strip(),
        status=(payload.get("status") or "Active").strip(),
        description=(payload.get("description") or "").strip() or None,
        mfg=(payload.get("mfg") or "").strip() or None,
        model_no=(payload.get("model_no") or "").strip() or None,
        serial_no=(payload.get("serial_no") or "").strip() or None,
        date_in_service=parse_date(payload.get("date_in_service")),
        location=(payload.get("location") or "").strip() or None,
        cal_interval=parse_int(payload.get("cal_interval")),
        last_cal_date=parse_date(payload.get("last_cal_date")),
        cal_due_date=parse_date(payload.get("cal_due_date")),
        pm_interval=parse_int(payload.get("pm_interval")),
        last_pm_date=parse_date(payload.get("last_pm_date")),
        pm_due_date=parse_date(payload.get("pm_due_date")),
        comments=(payload.get("comments") or "").strip() or None,
        created_at=now,
        updated_at=now,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    s.add(equipment)
    s.flush()

    record_event(
        s,
        actor=user,
        action="equipment.create",
        entity_type="Equipment",
        entity_id=str(equipment.id),
        metadata={"equip_code": equipment.equip_code, "status": equipment.status, "description": equipment.description},
    )
    return equipment


def update_equipment(s: "Session", equipment: "Equipment", payload: dict, user: "User", reason: str | None = None) -> "Equipment":
    """Update existing equipment."""
    changes = {}

    # equip_code is read-only after creation, but track if provided
    new_status = (payload.get("status") or "").strip()
    if new_status and new_status != equipment.status:
        changes["status"] = {"old": equipment.status, "new": new_status}
        equipment.status = new_status

    new_description = (payload.get("description") or "").strip() or None
    if new_description != equipment.description:
        changes["description"] = {"old": equipment.description, "new": new_description}
        equipment.description = new_description

    new_mfg = (payload.get("mfg") or "").strip() or None
    if new_mfg != equipment.mfg:
        changes["mfg"] = {"old": equipment.mfg, "new": new_mfg}
        equipment.mfg = new_mfg

    new_model_no = (payload.get("model_no") or "").strip() or None
    if new_model_no != equipment.model_no:
        changes["model_no"] = {"old": equipment.model_no, "new": new_model_no}
        equipment.model_no = new_model_no

    new_serial_no = (payload.get("serial_no") or "").strip() or None
    if new_serial_no != equipment.serial_no:
        changes["serial_no"] = {"old": equipment.serial_no, "new": new_serial_no}
        equipment.serial_no = new_serial_no

    new_date_in_service = parse_date(payload.get("date_in_service"))
    if new_date_in_service != equipment.date_in_service:
        changes["date_in_service"] = {"old": str(equipment.date_in_service), "new": str(new_date_in_service)}
        equipment.date_in_service = new_date_in_service

    new_location = (payload.get("location") or "").strip() or None
    if new_location != equipment.location:
        changes["location"] = {"old": equipment.location, "new": new_location}
        equipment.location = new_location

    new_cal_interval = parse_int(payload.get("cal_interval"))
    if new_cal_interval != equipment.cal_interval:
        changes["cal_interval"] = {"old": equipment.cal_interval, "new": new_cal_interval}
        equipment.cal_interval = new_cal_interval

    new_last_cal_date = parse_date(payload.get("last_cal_date"))
    if new_last_cal_date != equipment.last_cal_date:
        changes["last_cal_date"] = {"old": str(equipment.last_cal_date), "new": str(new_last_cal_date)}
        equipment.last_cal_date = new_last_cal_date

    new_cal_due_date = parse_date(payload.get("cal_due_date"))
    if new_cal_due_date != equipment.cal_due_date:
        changes["cal_due_date"] = {"old": str(equipment.cal_due_date), "new": str(new_cal_due_date)}
        equipment.cal_due_date = new_cal_due_date

    new_pm_interval = parse_int(payload.get("pm_interval"))
    if new_pm_interval != equipment.pm_interval:
        changes["pm_interval"] = {"old": equipment.pm_interval, "new": new_pm_interval}
        equipment.pm_interval = new_pm_interval

    new_last_pm_date = parse_date(payload.get("last_pm_date"))
    if new_last_pm_date != equipment.last_pm_date:
        changes["last_pm_date"] = {"old": str(equipment.last_pm_date), "new": str(new_last_pm_date)}
        equipment.last_pm_date = new_last_pm_date

    new_pm_due_date = parse_date(payload.get("pm_due_date"))
    if new_pm_due_date != equipment.pm_due_date:
        changes["pm_due_date"] = {"old": str(equipment.pm_due_date), "new": str(new_pm_due_date)}
        equipment.pm_due_date = new_pm_due_date

    new_comments = (payload.get("comments") or "").strip() or None
    if new_comments != equipment.comments:
        changes["comments"] = {"old": equipment.comments, "new": new_comments}
        equipment.comments = new_comments

    equipment.updated_at = datetime.utcnow()
    equipment.updated_by_user_id = user.id

    record_event(
        s,
        actor=user,
        action="equipment.edit",
        entity_type="Equipment",
        entity_id=str(equipment.id),
        reason=reason,
        metadata={"equip_code": equipment.equip_code, "changes": changes},
    )
    return equipment


def build_equipment_storage_key(equip_code: str, filename: str, upload_date: date | None = None) -> str:
    """Build deterministic storage key for equipment document."""
    if upload_date is None:
        upload_date = date.today()
    safe_code = equip_code.replace("/", "_").replace("\\", "_")  # Prevent path traversal
    safe_filename = secure_filename(filename) or "document.bin"
    return f"equipment/{safe_code}/{upload_date.isoformat()}/{safe_filename}"


def file_digest_and_bytes(file_bytes: bytes) -> tuple[str, int]:
    """Compute SHA256 digest and size."""
    h = hashlib.sha256()
    h.update(file_bytes)
    return (h.hexdigest(), len(file_bytes))


def upload_equipment_document(
    s: "Session",
    equipment: "Equipment",
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user: "User",
    description: str | None = None,
    document_type: str | None = None,
) -> "ManagedDocument":
    """Upload a document to equipment."""
    from flask import current_app
    from app.eqms.storage import storage_from_config
    from app.eqms.modules.equipment.models import ManagedDocument

    sha256, size_bytes = file_digest_and_bytes(file_bytes)
    storage_key = build_equipment_storage_key(equipment.equip_code, filename)

    storage = storage_from_config(current_app.config)
    storage.put_bytes(storage_key, file_bytes, content_type=content_type)

    doc = ManagedDocument(
        entity_type="equipment",
        entity_id=equipment.id,
        equipment_id=equipment.id,
        storage_key=storage_key,
        original_filename=secure_filename(filename) or "document.bin",
        content_type=content_type,
        sha256=sha256,
        size_bytes=size_bytes,
        description=description,
        document_type=document_type,
        uploaded_by_user_id=user.id,
    )
    s.add(doc)
    s.flush()

    record_event(
        s,
        actor=user,
        action="equipment.document_upload",
        entity_type="ManagedDocument",
        entity_id=str(doc.id),
        metadata={
            "equipment_id": equipment.id,
            "equip_code": equipment.equip_code,
            "filename": doc.original_filename,
            "document_type": document_type,
        },
    )
    return doc


def delete_equipment_document(s: "Session", document: "ManagedDocument", user: "User", reason: str) -> None:
    """Soft-delete an equipment document."""
    document.is_deleted = True
    document.deleted_at = datetime.utcnow()
    document.deleted_by_user_id = user.id

    record_event(
        s,
        actor=user,
        action="equipment.document_delete",
        entity_type="ManagedDocument",
        entity_id=str(document.id),
        reason=reason,
        metadata={
            "equipment_id": document.equipment_id,
            "filename": document.original_filename,
        },
    )


def add_supplier_to_equipment(
    s: "Session",
    equipment: "Equipment",
    supplier: "Supplier",
    relationship_type: str | None,
    notes: str | None,
    user: "User",
) -> "EquipmentSupplier":
    """Add supplier association to equipment."""
    from app.eqms.modules.equipment.models import EquipmentSupplier

    assoc = EquipmentSupplier(
        equipment_id=equipment.id,
        supplier_id=supplier.id,
        relationship_type=relationship_type,
        notes=notes,
        created_by_user_id=user.id,
    )
    s.add(assoc)
    s.flush()

    record_event(
        s,
        actor=user,
        action="equipment.supplier_added",
        entity_type="EquipmentSupplier",
        entity_id=str(assoc.id),
        metadata={
            "equipment_id": equipment.id,
            "supplier_id": supplier.id,
            "relationship_type": relationship_type,
        },
    )
    return assoc


def remove_supplier_from_equipment(s: "Session", association: "EquipmentSupplier", user: "User", reason: str) -> None:
    """Remove supplier association from equipment."""
    equipment_id = association.equipment_id
    supplier_id = association.supplier_id
    assoc_id = association.id

    record_event(
        s,
        actor=user,
        action="equipment.supplier_removed",
        entity_type="EquipmentSupplier",
        entity_id=str(assoc_id),
        reason=reason,
        metadata={
            "equipment_id": equipment_id,
            "supplier_id": supplier_id,
        },
    )
    s.delete(association)
