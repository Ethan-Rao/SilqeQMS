from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base
from app.eqms.utils import utcnow

if TYPE_CHECKING:
    from app.eqms.modules.rep_traceability.models import SalesOrder

INVOICE_STATUSES = ["Pending Invoice", "Invoiced", "Paid", "Cancelled"]


class NREProjectEntry(Base):
    __tablename__ = "nre_project_entries"
    __table_args__ = (
        Index("idx_nre_entries_order", "sales_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nullable so the tracker supports free-form entries not tied to a sales order.
    sales_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, unique=False
    )

    # Free-form ledger fields
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    expected_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_status: Mapped[str] = mapped_column(String(32), nullable=False, default="Pending Invoice")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow, onupdate=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    sales_order: Mapped["SalesOrder"] = relationship("SalesOrder", lazy="selectin")
    attachments: Mapped[list["NRETrackerAttachment"]] = relationship(
        "NRETrackerAttachment", back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )


class NRETrackerAttachment(Base):
    """File attached to an NRE invoice-tracker entry."""

    __tablename__ = "nre_tracker_attachments"
    __table_args__ = (
        Index("idx_nre_att_entry", "nre_entry_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nre_entry_id: Mapped[int] = mapped_column(ForeignKey("nre_project_entries.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    entry: Mapped["NREProjectEntry"] = relationship("NREProjectEntry", back_populates="attachments")
