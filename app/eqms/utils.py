from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from flask import g

from app.eqms.modules.equipment.models import ManagedDocument


# ---------------------------------------------------------------------------
# Shared helpers (used across all modules)
# ---------------------------------------------------------------------------

def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime.

    Use as a SQLAlchemy column default:  ``default=utcnow``
    Use for explicit assignments:        ``obj.updated_at = utcnow()``
    """
    return datetime.now(timezone.utc)


def current_user():
    """Return the currently-authenticated User or raise RuntimeError."""
    from app.eqms.models import User  # avoid circular import

    u: User | None = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


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
    """
    Determine if a file should be viewed inline (True) or downloaded (False).

    Only returns True for file types the **browser** can render natively
    (PDF, images, plain text).  Types that need server-side conversion
    (.docx, .xlsx, .xls, .csv) are handled by the document_viewer module
    before this function is ever reached.
    """
    ext = Path(filename or "").suffix.lower()
    # Types that must always download
    if ext in {".eml"} or (content_type or "").lower() == "message/rfc822":
        return False
    # Types that need server-side rendering — should NOT be sent raw inline
    # (the view routes handle them via render_document_to_response first)
    # .doc is excluded: mammoth cannot render it, so it falls through to download.
    if ext in {".docx", ".xlsx", ".xls", ".csv"}:
        return False
    # Natively renderable by browsers
    if content_type:
        if content_type.startswith("image/"):
            return True
        if content_type in {
            "application/pdf",
            "text/plain",
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
    }:
        return True
    return False
