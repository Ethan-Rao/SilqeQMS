from __future__ import annotations

import re
from datetime import date, datetime
from typing import TYPE_CHECKING

from app.eqms.audit import record_event
from app.eqms.utils import utcnow
from app.eqms.modules.training.models import (
    ITEM_ADMIN_DOC,
    ITEM_DOCUMENT,
    ITEM_FREE_TEXT,
    VALID_ITEM_TYPES,
    TrainingAssignment,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.models import User


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


_REV_SUFFIX = re.compile(r"\s+[A-Za-z]{1,2}$")


def _doc_base(doc_number: str | None) -> str:
    """Normalize a doc number to its base (drops a trailing ' <rev>' and case)."""
    return _REV_SUFFIX.sub("", (doc_number or "").strip().upper())


def resolve_current_revision(s: "Session", doc_number: str):
    """
    Resolve a doc number (e.g. "QM.SLQ052") to its Document and current revision.

    Matches on the base doc number so "QM.SLQ001" resolves whether the stored
    doc_number is "QM.SLQ001" or "QM.SLQ001 B". Returns (Document, DocumentRevision|None)
    or None when no document matches.
    """
    from app.eqms.modules.document_control.models import Document

    norm = _doc_base(doc_number)
    if not norm:
        return None
    for d in s.query(Document).all():
        if _doc_base(d.doc_number) == norm or (d.doc_number or "").strip().upper() == norm:
            return d, d.current_revision
    return None


def assignment_status(a: TrainingAssignment, today: date | None = None) -> dict:
    """
    Derive an at-a-glance status for a training assignment.

    States: "acknowledged", "overdue" (open and past due), "due_soon" (open,
    due within 7 days), "open" (assigned, no urgency).
    """
    if today is None:
        today = date.today()
    if a.acknowledged_at is not None:
        return {"state": "acknowledged", "label": "Acknowledged"}
    if a.due_date is not None:
        days = (a.due_date - today).days
        if days < 0:
            return {"state": "overdue", "label": f"Overdue {abs(days)}d"}
        if days <= 7:
            return {"state": "due_soon", "label": f"Due in {days}d"}
    return {"state": "open", "label": "Assigned"}


def _resolve_item(
    s: "Session",
    item_type: str,
    document_id: int | None,
    admin_doc_file_id: int | None,
    document_revision_id: int | None = None,
) -> tuple[str, int | None, int | None, int | None, str | None]:
    """
    Validate the chosen item and return
    (item_type, document_id, admin_doc_file_id, document_revision_id, cached_title).
    Raises ValueError on an invalid selection.
    """
    if item_type == ITEM_DOCUMENT:
        from app.eqms.modules.document_control.models import Document, DocumentRevision

        if not document_id:
            raise ValueError("Select a controlled document to assign.")
        doc = s.get(Document, int(document_id))
        if not doc:
            raise ValueError("The selected controlled document was not found.")

        # Target a specific revision if chosen, else default to the current one.
        rev = None
        if document_revision_id:
            rev = s.get(DocumentRevision, int(document_revision_id))
            if not rev or rev.document_id != doc.id:
                raise ValueError("The selected revision does not belong to that document.")
        elif doc.current_revision_id:
            rev = s.get(DocumentRevision, doc.current_revision_id)

        if rev is not None:
            title = f"{doc.doc_number} Rev {rev.revision} — {doc.title}"
            return ITEM_DOCUMENT, doc.id, None, rev.id, title
        title = f"{doc.doc_number} — {doc.title}"
        return ITEM_DOCUMENT, doc.id, None, None, title
    if item_type == ITEM_ADMIN_DOC:
        from app.eqms.modules.admin_docs.models import AdminDocFile

        if not admin_doc_file_id:
            raise ValueError("Select a library file to assign.")
        f = s.get(AdminDocFile, int(admin_doc_file_id))
        if not f:
            raise ValueError("The selected library file was not found.")
        return ITEM_ADMIN_DOC, None, f.id, None, f.filename
    if item_type == ITEM_FREE_TEXT:
        return ITEM_FREE_TEXT, None, None, None, None
    raise ValueError("Invalid training item type.")


def document_revision_status(a: TrainingAssignment) -> dict | None:
    """
    For a document-linked assignment, compare the assigned revision to the
    document's current revision so a stale acknowledgement is obvious.

    Returns None for non-document items or when the document is gone. Otherwise
    {assigned, current, is_stale} where is_stale is True when a strictly newer
    revision is now current.
    """
    from app.eqms.modules.document_control.dco_log import rev_order_key
    from app.eqms.modules.training.models import ITEM_DOCUMENT

    if a.item_type != ITEM_DOCUMENT or a.document is None:
        return None
    current = a.document.current_revision
    current_label = current.revision if current else None
    assigned_label = a.document_revision.revision if a.document_revision else None
    is_stale = bool(
        assigned_label
        and current_label
        and assigned_label != current_label
        and rev_order_key(current_label) > rev_order_key(assigned_label)
    )
    return {"assigned": assigned_label, "current": current_label, "is_stale": is_stale}


def create_assignments(
    s: "Session",
    *,
    item_type: str,
    document_id: int | None,
    admin_doc_file_id: int | None,
    free_text_title: str | None,
    instructions: str | None,
    user_ids: list[int],
    due_date: date | None,
    actor: "User",
    document_revision_id: int | None = None,
) -> list[TrainingAssignment]:
    """
    Create one assignment per user for the chosen item. Skips users who already
    have an open (unacknowledged) assignment for the same item (and, for document
    items, the same revision) so re-assigning is idempotent.
    """
    if item_type not in VALID_ITEM_TYPES:
        raise ValueError("Invalid training item type.")
    if not user_ids:
        raise ValueError("Select at least one user to assign.")

    resolved_type, doc_id, adf_id, doc_rev_id, cached_title = _resolve_item(
        s, item_type, document_id, admin_doc_file_id, document_revision_id
    )

    if resolved_type == ITEM_FREE_TEXT:
        title = (free_text_title or "").strip()
        if not title:
            raise ValueError("Enter a title for the free-text training item.")
    else:
        title = cached_title or "Training item"

    instr = (instructions or "").strip() or None
    now = utcnow()
    created: list[TrainingAssignment] = []

    for uid in user_ids:
        # Skip if an identical, still-open assignment already exists.
        existing = (
            s.query(TrainingAssignment)
            .filter(
                TrainingAssignment.assigned_to_user_id == uid,
                TrainingAssignment.item_type == resolved_type,
                TrainingAssignment.document_id == doc_id,
                TrainingAssignment.document_revision_id == doc_rev_id,
                TrainingAssignment.admin_doc_file_id == adf_id,
                TrainingAssignment.item_title == title,
                TrainingAssignment.acknowledged_at.is_(None),
            )
            .first()
        )
        if existing:
            # Refresh the due date / instructions on the existing open item.
            existing.due_date = due_date
            existing.instructions = instr
            continue

        a = TrainingAssignment(
            item_type=resolved_type,
            item_title=title,
            instructions=instr,
            document_id=doc_id,
            document_revision_id=doc_rev_id,
            admin_doc_file_id=adf_id,
            assigned_to_user_id=uid,
            assigned_by_user_id=actor.id,
            due_date=due_date,
            assigned_at=now,
            created_at=now,
        )
        s.add(a)
        created.append(a)

    s.flush()
    record_event(
        s,
        actor=actor,
        action="training.assign",
        entity_type="TrainingAssignment",
        entity_id="bulk",
        metadata={
            "item_type": resolved_type,
            "item_title": title,
            "document_id": doc_id,
            "document_revision_id": doc_rev_id,
            "admin_doc_file_id": adf_id,
            "user_ids": list(user_ids),
            "created": len(created),
            "due_date": due_date.isoformat() if due_date else None,
        },
    )
    return created


def acknowledge_assignment(s: "Session", a: TrainingAssignment, actor: "User") -> bool:
    """
    Mark an assignment acknowledged by its assignee. Returns False if it was
    already acknowledged (no-op). Writes a training.acknowledge audit event.
    """
    if a.acknowledged_at is not None:
        return False
    a.acknowledged_at = utcnow()
    record_event(
        s,
        actor=actor,
        action="training.acknowledge",
        entity_type="TrainingAssignment",
        entity_id=str(a.id),
        metadata={
            "item_type": a.item_type,
            "item_title": a.item_title,
            "document_id": a.document_id,
            "admin_doc_file_id": a.admin_doc_file_id,
        },
    )
    return True
