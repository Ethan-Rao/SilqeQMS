from __future__ import annotations

import json

from app.eqms.modules.equipment.models import ManagedDocument


def parse_custom_fields(raw: str | None) -> tuple[dict | None, str | None]:
    """Parse JSON custom fields from form input."""
    if not raw or not raw.strip():
        return None, None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"Custom fields JSON is invalid: {e}"
    if not isinstance(value, dict):
        return None, "Custom fields must be a JSON object."
    return value, None


def validate_managed_document(doc: ManagedDocument) -> None:
    """Ensure ManagedDocument fields are consistent with entity_type."""
    if doc.entity_type == "equipment":
        if doc.equipment_id != doc.entity_id or doc.supplier_id is not None:
            raise ValueError("ManagedDocument equipment linkage mismatch.")
    elif doc.entity_type == "supplier":
        if doc.supplier_id != doc.entity_id or doc.equipment_id is not None:
            raise ValueError("ManagedDocument supplier linkage mismatch.")
