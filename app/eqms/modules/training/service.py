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


# --------------------------------------------------------------------------- #
# Training matrix (QM.SLQ053 Appendix 1)
# --------------------------------------------------------------------------- #
# Maps doc_number → list of email fragments that require that training.
# A fragment matches if it appears anywhere in user.email.lower().
# The special fragment "all" matches every active user.
MATRIX: dict[str, list[str]] = {
    # BASE — all employees
    "QM.SLQ035": ["all"],
    "QM.SLQ027": ["all"],
    "QM.SLQ002": ["all"],
    "QM.SLQ053": ["all"],
    # Quality System Management
    "QM.SLQ001": ["ethan", "nah", "christ", "haley"],
    "QM.SLQ014": ["ethan", "nah", "christ", "haley"],
    "QM.SLQ016": ["ethan", "brianm", "christ", "tomd"],
    "QM.SLQ017": ["ethan", "brianm", "tomd"],
    "QM.SLQ018": ["ethan", "brianm", "tomd"],
    "QM.SLQ037": ["ethan", "brianm", "tomd"],
    "QM.SLQ025": ["ethan", "brianm", "tomd"],
    "QM.SLQ038": ["ethan", "brianm", "tomd"],
    "QM.SLQ028": ["ethan", "brianm", "nah", "chuckg", "tomd", "haley"],
    # Design & Development
    # QM.SLQ004–QM.SLQ010 obsoleted by DCO095; replaced by QM.SLQ052 Design Control SOP
    "QM.SLQ052": ["ethan", "brianm", "nah"],
    "QM.SLQ012": ["ethan", "brianm", "nah"],
    "QM.SLQ013": ["ethan", "brianm", "nah"],
    "QM.SLQ011": ["ethan", "nah"],
    "QM.SLQ032": ["ethan", "brianm", "nah"],
    "QM.SLQ033": ["ethan", "brianm", "nah"],
    "QM.SLQ048": ["ethan", "nah", "christ"],
    "QM.SLQ029": ["ethan", "christ"],
    "QM.SLQ047": ["ethan", "nah", "christ"],
    # Manufacturing & Operations
    "QM.SLQ019": ["ethan", "christ"],
    "QM.SLQ040": ["ethan", "christ"],
    "QM.SLQ039": ["ethan", "christ"],
    "QM.SLQ043": ["ethan", "christ"],
    "QM.SLQ045": ["ethan", "christ", "haley"],
    "QM.SLQ046": ["ethan", "christ", "chuckg"],
    "QM.SLQ049": ["ethan", "christ"],
    "QM.SLQ050": ["ethan", "christ"],
    "QM.SLQ051": ["ethan", "christ"],
    "QM.SLQ026": ["ethan", "nah", "christ"],
    # Supplier & Purchasing
    "QM.SLQ015": ["ethan", "christ", "haley"],
    "QM.SLQ020": ["ethan", "christ", "chuckg", "tomd", "haley"],
    # Commercial & Post-Market
    "QM.SLQ036": ["ethan", "chuckg", "haley"],
    "QM.SLQ021": ["ethan", "chuckg"],
    "QM.SLQ022": ["ethan", "chuckg"],
    "QM.SLQ023": ["ethan"],
    "QM.SLQ030": ["ethan", "brianm", "chuckg"],
}

# Ordered category grouping for the matrix grid view.
MATRIX_CATEGORIES: list[tuple[str, list[str]]] = [
    ("Base Requirements", ["QM.SLQ035", "QM.SLQ027", "QM.SLQ002", "QM.SLQ053"]),
    ("Quality System Management", ["QM.SLQ001", "QM.SLQ014", "QM.SLQ016", "QM.SLQ017",
                                    "QM.SLQ018", "QM.SLQ037", "QM.SLQ025", "QM.SLQ038", "QM.SLQ028"]),
    # QM.SLQ004–QM.SLQ010 obsoleted by DCO095; replaced by QM.SLQ052
    ("Design and Development", ["QM.SLQ052", "QM.SLQ012", "QM.SLQ013",
                                 "QM.SLQ011", "QM.SLQ032", "QM.SLQ033", "QM.SLQ048", "QM.SLQ029", "QM.SLQ047"]),
    ("Manufacturing and Operations", ["QM.SLQ019", "QM.SLQ040", "QM.SLQ039", "QM.SLQ043",
                                       "QM.SLQ045", "QM.SLQ046", "QM.SLQ049", "QM.SLQ050", "QM.SLQ051", "QM.SLQ026"]),
    ("Supplier and Purchasing", ["QM.SLQ015", "QM.SLQ020"]),
    ("Commercial and Post-Market", ["QM.SLQ036", "QM.SLQ021", "QM.SLQ022", "QM.SLQ023", "QM.SLQ030"]),
]


def matrix_required_for_doc_numbers(user_email: str) -> list[str]:
    """Return all doc numbers the user is required to be trained on per the matrix."""
    email = (user_email or "").lower()
    return [
        doc_num
        for doc_num, fragments in MATRIX.items()
        if "all" in fragments or any(f in email for f in fragments)
    ]


def matrix_users_for_doc(s: "Session", doc_number: str) -> list["User"]:
    """Return active users required to be trained on ``doc_number`` per the matrix."""
    from app.eqms.models import User

    fragments = MATRIX.get(doc_number)
    if not fragments:
        return []
    users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()
    if "all" in fragments:
        return users
    return [u for u in users if any(f in (u.email or "").lower() for f in fragments)]


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
    training_type: str = "read_acknowledge",
    source_reference: str | None = None,
    acknowledged_at: datetime | None = None,
) -> list[TrainingAssignment]:
    """
    Create one assignment per user for the chosen item. Skips users who already
    have an open (unacknowledged) assignment for the same item (and, for document
    items, the same revision) so re-assigning is idempotent.

    When ``acknowledged_at`` is provided (admin backdating / DCO auto-qualification),
    the record is created pre-acknowledged. A pre-acknowledged record is a distinct
    thing from a pending one, so the open-assignment dedup check is skipped in that
    case (an acknowledged historical record and a pending open item can coexist).
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
    src_ref = (source_reference or "").strip() or None
    now = utcnow()
    created: list[TrainingAssignment] = []

    for uid in user_ids:
        # Skip if an identical, still-open assignment already exists — but only
        # when we are NOT creating a pre-acknowledged record. A pre-acknowledged
        # historical/DCO record is distinct from a pending open item.
        if acknowledged_at is None:
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
            training_type=training_type or "read_acknowledge",
            source_reference=src_ref,
            acknowledged_at=acknowledged_at,
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
