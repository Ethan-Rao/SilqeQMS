from __future__ import annotations

import json
from pathlib import Path

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


def allow_inline_view(filename: str | None, content_type: str | None) -> bool:
    """Determine if a file should be viewed inline (True) or downloaded (False)."""
    ext = Path(filename or "").suffix.lower()
    if ext in {".eml"} or (content_type or "").lower() == "message/rfc822":
        return False
    if content_type:
        if content_type.startswith("image/"):
            return True
        if content_type in {
            "application/pdf",
            "text/plain",
            "text/csv",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }:
            return True
    if ext in {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".txt",
        ".csv",
        ".doc",
        ".docx",
        ".xlsx",
        ".xls",
    }:
        return True
    return False
