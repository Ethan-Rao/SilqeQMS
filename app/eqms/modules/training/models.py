from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base
from app.eqms.utils import utcnow

if TYPE_CHECKING:
    from app.eqms.models import User
    from app.eqms.modules.document_control.models import Document, DocumentRevision


# Kinds of training item an assignment may point at.
ITEM_DOCUMENT = "document"      # controlled document (document_control)
ITEM_ADMIN_DOC = "admin_doc"    # a file in an admin_docs record library
ITEM_FREE_TEXT = "free_text"    # a free-text instruction with no linked file
VALID_ITEM_TYPES = (ITEM_DOCUMENT, ITEM_ADMIN_DOC, ITEM_FREE_TEXT)


class TrainingAssignment(Base):
    """
    A read-and-acknowledge training item assigned to a single user (QM.SLQ003).

    One row per (item, user). The admin assigns a controlled document, an
    admin_docs file, or a free-text item to specific users with an optional due
    date. The assignee opens the linked item via the existing viewer and
    acknowledges it, which stamps acknowledged_at and writes an audit event.
    """

    __tablename__ = "training_assignments"
    __table_args__ = (
        Index("idx_training_assignee", "assigned_to_user_id"),
        Index("idx_training_assignee_ack", "assigned_to_user_id", "acknowledged_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # What is being assigned.
    item_type: Mapped[str] = mapped_column(String(16), nullable=False, default=ITEM_FREE_TEXT)
    # Cached display title so the queue renders even if a linked item is later removed.
    item_title: Mapped[str] = mapped_column(String(255), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional links (exactly one is set for document / admin_doc types).
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    # For document items, the specific revision this training targets (E3).
    # Nullable: older rows and non-document items have none.
    document_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_revisions.id", ondelete="SET NULL"), nullable=True
    )
    admin_doc_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("admin_doc_files.id", ondelete="SET NULL"), nullable=True
    )

    # How the training was completed / qualified.
    # read_acknowledge (default) | interactive | dco_auto_qualified | document_originator
    training_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="read_acknowledge", server_default="read_acknowledge"
    )
    # Free-text reference for the training source, e.g. "DCO-096", "Authored QM.SLQ053 Rev A".
    source_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Who / when.
    assigned_to_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow)

    assignee: Mapped["User"] = relationship("User", foreign_keys=[assigned_to_user_id], lazy="selectin")
    assigned_by: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_by_user_id], lazy="selectin")

    document: Mapped["Document | None"] = relationship(
        "Document", foreign_keys=[document_id], lazy="selectin"
    )
    document_revision: Mapped["DocumentRevision | None"] = relationship(
        "DocumentRevision", foreign_keys=[document_revision_id], lazy="selectin"
    )


class EffectivenessReview(Base):
    """Annual Effectiveness Review record per QM.SLQ053 Section 11."""

    __tablename__ = "effectiveness_reviews"
    __table_args__ = (
        Index("idx_eff_review_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    review_year: Mapped[int] = mapped_column(Integer, nullable=False)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # e.g. 9.0 (of 10)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    reviewed_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[reviewed_by_user_id], lazy="selectin"
    )
