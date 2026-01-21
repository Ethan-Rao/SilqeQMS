from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import TYPE_CHECKING

from werkzeug.utils import secure_filename

from app.eqms.audit import record_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.models import User
    from app.eqms.modules.suppliers.models import Supplier
    from app.eqms.modules.equipment.models import ManagedDocument


VALID_STATUSES = ("Approved", "Conditional", "Pending", "Rejected")


def parse_date(s: str | None) -> date | None:
    """Parse YYYY-MM-DD date string."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    return date.fromisoformat(s)


def validate_supplier_payload(payload: dict) -> list[str]:
    """Validate supplier creation/update payload. Returns list of errors."""
    errors = []
    name = (payload.get("name") or "").strip()
    if not name:
        errors.append("Name is required.")
    status = (payload.get("status") or "").strip()
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}")
    return errors


def create_supplier(s: "Session", payload: dict, user: "User") -> "Supplier":
    """Create a new supplier."""
    from app.eqms.modules.suppliers.models import Supplier

    now = datetime.utcnow()
    supplier = Supplier(
        name=(payload.get("name") or "").strip(),
        status=(payload.get("status") or "Pending").strip(),
        category=(payload.get("category") or "").strip() or None,
        product_service_provided=(payload.get("product_service_provided") or "").strip() or None,
        address=(payload.get("address") or "").strip() or None,
        initial_listing_date=parse_date(payload.get("initial_listing_date")),
        certification_expiration=parse_date(payload.get("certification_expiration")),
        notes=(payload.get("notes") or "").strip() or None,
        created_at=now,
        updated_at=now,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    s.add(supplier)
    s.flush()

    record_event(
        s,
        actor=user,
        action="supplier.create",
        entity_type="Supplier",
        entity_id=str(supplier.id),
        metadata={"name": supplier.name, "status": supplier.status},
    )
    return supplier


def update_supplier(s: "Session", supplier: "Supplier", payload: dict, user: "User", reason: str | None = None) -> "Supplier":
    """Update an existing supplier."""
    changes = {}
    old_status = supplier.status

    new_name = (payload.get("name") or "").strip()
    if new_name and new_name != supplier.name:
        changes["name"] = {"old": supplier.name, "new": new_name}
        supplier.name = new_name

    new_status = (payload.get("status") or "").strip()
    if new_status and new_status != supplier.status:
        changes["status"] = {"old": supplier.status, "new": new_status}
        supplier.status = new_status

    new_category = (payload.get("category") or "").strip() or None
    if new_category != supplier.category:
        changes["category"] = {"old": supplier.category, "new": new_category}
        supplier.category = new_category

    new_psp = (payload.get("product_service_provided") or "").strip() or None
    if new_psp != supplier.product_service_provided:
        changes["product_service_provided"] = {"old": supplier.product_service_provided, "new": new_psp}
        supplier.product_service_provided = new_psp

    new_address = (payload.get("address") or "").strip() or None
    if new_address != supplier.address:
        changes["address"] = {"old": supplier.address, "new": new_address}
        supplier.address = new_address

    new_ild = parse_date(payload.get("initial_listing_date"))
    if new_ild != supplier.initial_listing_date:
        changes["initial_listing_date"] = {"old": str(supplier.initial_listing_date), "new": str(new_ild)}
        supplier.initial_listing_date = new_ild

    new_ce = parse_date(payload.get("certification_expiration"))
    if new_ce != supplier.certification_expiration:
        changes["certification_expiration"] = {"old": str(supplier.certification_expiration), "new": str(new_ce)}
        supplier.certification_expiration = new_ce

    new_notes = (payload.get("notes") or "").strip() or None
    if new_notes != supplier.notes:
        changes["notes"] = {"old": supplier.notes, "new": new_notes}
        supplier.notes = new_notes

    supplier.updated_at = datetime.utcnow()
    supplier.updated_by_user_id = user.id

    record_event(
        s,
        actor=user,
        action="supplier.edit",
        entity_type="Supplier",
        entity_id=str(supplier.id),
        reason=reason,
        metadata={"name": supplier.name, "changes": changes},
    )
    return supplier


def build_supplier_storage_key(supplier_id: int, filename: str, upload_date: date | None = None) -> str:
    """Build deterministic storage key for supplier document."""
    if upload_date is None:
        upload_date = date.today()
    safe_filename = secure_filename(filename) or "document.bin"
    return f"suppliers/{supplier_id}/{upload_date.isoformat()}/{safe_filename}"


def file_digest_and_bytes(file_bytes: bytes) -> tuple[str, int]:
    """Compute SHA256 digest and size."""
    h = hashlib.sha256()
    h.update(file_bytes)
    return (h.hexdigest(), len(file_bytes))


def upload_supplier_document(
    s: "Session",
    supplier: "Supplier",
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user: "User",
    description: str | None = None,
    document_type: str | None = None,
) -> "ManagedDocument":
    """Upload a document to a supplier."""
    from flask import current_app
    from app.eqms.storage import storage_from_config
    from app.eqms.modules.equipment.models import ManagedDocument

    sha256, size_bytes = file_digest_and_bytes(file_bytes)
    storage_key = build_supplier_storage_key(supplier.id, filename)

    storage = storage_from_config(current_app.config)
    storage.put_bytes(storage_key, file_bytes, content_type=content_type)

    doc = ManagedDocument(
        entity_type="supplier",
        entity_id=supplier.id,
        supplier_id=supplier.id,
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
        action="supplier.document_upload",
        entity_type="ManagedDocument",
        entity_id=str(doc.id),
        metadata={
            "supplier_id": supplier.id,
            "name": supplier.name,
            "filename": doc.original_filename,
            "document_type": document_type,
        },
    )
    return doc


def delete_supplier_document(s: "Session", document: "ManagedDocument", user: "User", reason: str) -> None:
    """Soft-delete a supplier document."""
    document.is_deleted = True
    document.deleted_at = datetime.utcnow()
    document.deleted_by_user_id = user.id

    record_event(
        s,
        actor=user,
        action="supplier.document_delete",
        entity_type="ManagedDocument",
        entity_id=str(document.id),
        reason=reason,
        metadata={
            "supplier_id": document.supplier_id,
            "filename": document.original_filename,
        },
    )
