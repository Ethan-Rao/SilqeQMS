from __future__ import annotations

import hashlib
from datetime import datetime, date
from typing import TYPE_CHECKING

from werkzeug.utils import secure_filename

from app.eqms.audit import record_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.models import User
    from app.eqms.modules.supplies.models import Supply, SupplySupplier, SupplyDocument
    from app.eqms.modules.suppliers.models import Supplier


def validate_supply_payload(payload: dict) -> list[str]:
    errors = []
    if not (payload.get("supply_code") or "").strip():
        errors.append("Supply code is required.")
    return errors


def create_supply(s: "Session", payload: dict, user: "User") -> "Supply":
    from app.eqms.modules.supplies.models import Supply

    now = datetime.utcnow()
    supply = Supply(
        supply_code=(payload.get("supply_code") or "").strip(),
        status=(payload.get("status") or "Active").strip(),
        description=(payload.get("description") or "").strip() or None,
        manufacturer=(payload.get("manufacturer") or "").strip() or None,
        part_number=(payload.get("part_number") or "").strip() or None,
        min_stock_level=payload.get("min_stock_level"),
        current_stock=payload.get("current_stock"),
        unit_of_measure=(payload.get("unit_of_measure") or "").strip() or None,
        comments=(payload.get("comments") or "").strip() or None,
        custom_fields=payload.get("custom_fields"),
        created_at=now,
        updated_at=now,
        created_by_user_id=user.id,
    )
    s.add(supply)
    s.flush()

    record_event(
        s,
        actor=user,
        action="supply.create",
        entity_type="Supply",
        entity_id=str(supply.id),
        metadata={"supply_code": supply.supply_code},
    )
    return supply


def update_supply(s: "Session", supply: "Supply", payload: dict, user: "User", reason: str | None = None) -> "Supply":
    changes = {}

    def _set(attr: str, val):
        nonlocal changes
        if val != getattr(supply, attr):
            changes[attr] = {"old": getattr(supply, attr), "new": val}
            setattr(supply, attr, val)

    _set("status", (payload.get("status") or supply.status).strip())
    _set("description", (payload.get("description") or "").strip() or None)
    _set("manufacturer", (payload.get("manufacturer") or "").strip() or None)
    _set("part_number", (payload.get("part_number") or "").strip() or None)
    _set("min_stock_level", payload.get("min_stock_level"))
    _set("current_stock", payload.get("current_stock"))
    _set("unit_of_measure", (payload.get("unit_of_measure") or "").strip() or None)
    _set("comments", (payload.get("comments") or "").strip() or None)

    supply.updated_at = datetime.utcnow()

    record_event(
        s,
        actor=user,
        action="supply.edit",
        entity_type="Supply",
        entity_id=str(supply.id),
        reason=reason,
        metadata={"changes": changes},
    )
    return supply


def _digest(file_bytes: bytes) -> tuple[str, int]:
    h = hashlib.sha256()
    h.update(file_bytes)
    return h.hexdigest(), len(file_bytes)


def build_supply_storage_key(supply_code: str, filename: str, upload_date: date | None = None) -> str:
    if upload_date is None:
        upload_date = date.today()
    safe_code = supply_code.replace("/", "_").replace("\\", "_")
    safe_filename = secure_filename(filename) or "document.bin"
    return f"supplies/{safe_code}/{upload_date.isoformat()}/{safe_filename}"


def upload_supply_document(
    s: "Session",
    supply: "Supply",
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user: "User",
    category: str = "general",
    description: str | None = None,
    is_primary: bool = False,
) -> "SupplyDocument":
    from app.eqms.storage import storage_from_config
    from app.eqms.modules.supplies.models import SupplyDocument
    from flask import current_app

    sha256, size_bytes = _digest(file_bytes)
    storage_key = build_supply_storage_key(supply.supply_code, filename)

    storage = storage_from_config(current_app.config)
    storage.put_bytes(storage_key, file_bytes, content_type=content_type)

    doc = SupplyDocument(
        supply_id=supply.id,
        storage_key=storage_key,
        original_filename=secure_filename(filename) or "document.bin",
        content_type=content_type,
        size_bytes=size_bytes,
        category=category,
        is_primary=is_primary,
        description=description,
        uploaded_by_user_id=user.id,
    )
    s.add(doc)
    s.flush()

    record_event(
        s,
        actor=user,
        action="supply.document_upload",
        entity_type="SupplyDocument",
        entity_id=str(doc.id),
        metadata={"supply_id": supply.id, "filename": doc.original_filename, "category": category},
    )
    return doc


def delete_supply_document(s: "Session", doc: "SupplyDocument", user: "User", reason: str | None = None) -> None:
    from app.eqms.storage import storage_from_config
    from flask import current_app

    storage = storage_from_config(current_app.config)
    try:
        storage.delete(doc.storage_key)
    except Exception:
        pass

    record_event(
        s,
        actor=user,
        action="supply.document_delete",
        entity_type="SupplyDocument",
        entity_id=str(doc.id),
        reason=reason,
        metadata={"supply_id": doc.supply_id, "filename": doc.original_filename},
    )
    s.delete(doc)


def add_supplier_to_supply(
    s: "Session",
    supply: "Supply",
    supplier: "Supplier",
    relationship_type: str | None,
    notes: str | None,
    user: "User",
) -> "SupplySupplier":
    from app.eqms.modules.supplies.models import SupplySupplier

    assoc = SupplySupplier(
        supply_id=supply.id,
        supplier_id=supplier.id,
        relationship_type=relationship_type,
        notes=notes,
    )
    s.add(assoc)

    record_event(
        s,
        actor=user,
        action="supply.supplier_add",
        entity_type="SupplySupplier",
        entity_id="new",
        metadata={"supply_id": supply.id, "supplier_id": supplier.id, "relationship_type": relationship_type},
    )
    return assoc


def remove_supplier_from_supply(s: "Session", assoc: "SupplySupplier", user: "User", reason: str | None = None) -> None:
    record_event(
        s,
        actor=user,
        action="supply.supplier_remove",
        entity_type="SupplySupplier",
        entity_id=str(assoc.id),
        reason=reason,
        metadata={"supply_id": assoc.supply_id, "supplier_id": assoc.supplier_id},
    )
    s.delete(assoc)
