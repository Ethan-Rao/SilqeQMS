from __future__ import annotations

import hashlib
from datetime import date, datetime
from email import policy
from email.message import Message
from email.parser import BytesParser
from typing import TYPE_CHECKING

from werkzeug.utils import secure_filename

from app.eqms.utils import utcnow

from app.eqms.audit import record_event

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.models import User
    from app.eqms.modules.purchasing.models import PurchaseOrder, PurchaseOrderAttachment, PurchaseOrderLine


def parse_date(s: str | None) -> date | None:
    """Parse YYYY-MM-DD date string."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def validate_purchase_order_payload(payload: dict) -> list[str]:
    errors = []
    if not (payload.get("po_number") or "").strip():
        errors.append("PO number is required.")
    if not payload.get("order_date"):
        errors.append("Order date is required.")
    return errors


def _digest(file_bytes: bytes) -> tuple[str, int]:
    h = hashlib.sha256()
    h.update(file_bytes)
    return h.hexdigest(), len(file_bytes)


def build_po_storage_key(po_number: str, filename: str, upload_date: date | None = None) -> str:
    if upload_date is None:
        upload_date = date.today()
    safe_po = po_number.replace("/", "_").replace("\\", "_")
    safe_filename = secure_filename(filename) or "document.bin"
    return f"purchase_orders/{safe_po}/{upload_date.isoformat()}/{safe_filename}"


def parse_line_items(items_text: str | None) -> list[dict]:
    """Parse line items from newline-delimited text."""
    lines = []
    for raw in (items_text or "").splitlines():
        row = raw.strip()
        if not row:
            continue
        # Preferred: item_code | description | qty | unit_price
        if "|" in row:
            parts = [p.strip() for p in row.split("|")]
            item_code = parts[0] or None
            description = parts[1] if len(parts) > 1 else None
            qty = parts[2] if len(parts) > 2 else None
            unit_price = parts[3] if len(parts) > 3 else None
            lines.append(
                {
                    "item_code": item_code,
                    "description": description,
                    "quantity": int(qty) if qty and qty.isdigit() else 1,
                    "unit_price": unit_price,
                }
            )
            continue
        # Accept "qty x description" or "qty, description"
        qty = 1
        description = row
        if " x " in row.lower():
            parts = row.lower().split(" x ", 1)
            if parts[0].strip().isdigit():
                qty = int(parts[0].strip())
                description = row[len(parts[0]) + 3 :].strip()
        elif "," in row:
            parts = row.split(",", 1)
            if parts[0].strip().isdigit():
                qty = int(parts[0].strip())
                description = parts[1].strip()
        lines.append({"description": description or row, "quantity": qty})
    return lines


def create_purchase_order(s: "Session", payload: dict, user: "User") -> "PurchaseOrder":
    from app.eqms.modules.purchasing.models import PurchaseOrder, PurchaseOrderLine

    now = utcnow()
    po = PurchaseOrder(
        po_number=(payload.get("po_number") or "").strip(),
        order_date=payload.get("order_date"),
        expected_date=payload.get("expected_date"),
        received_date=payload.get("received_date"),
        supplier_id=payload.get("supplier_id"),
        status=(payload.get("status") or "pending").strip(),
        description=(payload.get("description") or "").strip() or None,
        notes=(payload.get("notes") or "").strip() or None,
        created_at=now,
        updated_at=now,
        created_by_user_id=user.id,
    )
    s.add(po)
    s.flush()

    for line in payload.get("lines") or []:
        item = PurchaseOrderLine(
            purchase_order_id=po.id,
            item_code=(line.get("item_code") or "").strip() or None,
            description=(line.get("description") or "").strip() or None,
            quantity=int(line.get("quantity") or 1),
            quantity_received=int(line.get("quantity_received") or 0),
            unit_price=(line.get("unit_price") or "").strip() or None,
        )
        s.add(item)

    record_event(
        s,
        actor=user,
        action="purchase_order.create",
        entity_type="PurchaseOrder",
        entity_id=str(po.id),
        metadata={"po_number": po.po_number},
    )
    return po


def update_purchase_order(s: "Session", po: "PurchaseOrder", payload: dict, user: "User", reason: str | None = None) -> "PurchaseOrder":
    changes = {}

    def _set(attr: str, val):
        nonlocal changes
        if val != getattr(po, attr):
            changes[attr] = {"old": getattr(po, attr), "new": val}
            setattr(po, attr, val)

    _set("order_date", payload.get("order_date") or po.order_date)
    _set("expected_date", payload.get("expected_date"))
    _set("received_date", payload.get("received_date"))
    _set("supplier_id", payload.get("supplier_id"))
    _set("status", (payload.get("status") or po.status).strip())
    _set("description", (payload.get("description") or "").strip() or None)
    _set("notes", (payload.get("notes") or "").strip() or None)
    po.updated_at = utcnow()

    record_event(
        s,
        actor=user,
        action="purchase_order.edit",
        entity_type="PurchaseOrder",
        entity_id=str(po.id),
        reason=reason,
        metadata={"changes": changes},
    )
    return po


def upload_purchase_order_attachment(
    s: "Session",
    po: "PurchaseOrder",
    file_bytes: bytes,
    filename: str,
    content_type: str,
    user: "User",
    attachment_type: str,
) -> "PurchaseOrderAttachment":
    from flask import current_app
    from app.eqms.storage import storage_from_config
    from app.eqms.modules.purchasing.models import PurchaseOrderAttachment

    sha256, size_bytes = _digest(file_bytes)
    storage_key = build_po_storage_key(po.po_number, filename)

    storage = storage_from_config(current_app.config)
    storage.put_bytes(storage_key, file_bytes, content_type=content_type)

    attachment = PurchaseOrderAttachment(
        purchase_order_id=po.id,
        attachment_type=attachment_type,
        storage_key=storage_key,
        filename=secure_filename(filename) or "document.bin",
        content_type=content_type,
        size_bytes=size_bytes,
        uploaded_by_user_id=user.id,
    )
    s.add(attachment)
    s.flush()

    record_event(
        s,
        actor=user,
        action="purchase_order.attachment_upload",
        entity_type="PurchaseOrderAttachment",
        entity_id=str(attachment.id),
        metadata={"po_id": po.id, "filename": attachment.filename, "type": attachment_type, "sha256": sha256},
    )
    return attachment


def parse_eml_file(eml_bytes: bytes) -> dict:
    """Parse EML file and extract viewable content."""
    msg: Message = BytesParser(policy=policy.default).parsebytes(eml_bytes)
    result = {
        "from": msg.get("From", ""),
        "to": msg.get("To", ""),
        "cc": msg.get("Cc", ""),
        "subject": msg.get("Subject", ""),
        "date": msg.get("Date", ""),
        "body_text": "",
        "body_html": "",
        "attachments": [],
    }

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" and not result["body_text"]:
                result["body_text"] = part.get_content()
            elif content_type == "text/html" and not result["body_html"]:
                result["body_html"] = part.get_content()
            elif part.get_filename():
                result["attachments"].append(
                    {"filename": part.get_filename(), "content_type": content_type}
                )
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            result["body_text"] = msg.get_content()
        elif content_type == "text/html":
            result["body_html"] = msg.get_content()
    return result
