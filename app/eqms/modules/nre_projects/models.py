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

# Legacy tracker presets (kept for reference; tracker Status is free-text as of P42).
INVOICE_STATUSES = [
    "Pending Invoice",
    "50% Invoiced",
    "Invoiced",
    "Paid",
    "Cancelled",
]

# NRE Dashboard SalesOrder.nre_invoice_status presets (exact labels).
NRE_DASHBOARD_STATUSES = [
    "Pending Invoice",
    "50% Invoiced",
    "100% Invoiced",
    "Payment Received",
]


def nre_invoiced_amount(status: str | None, order_amount) -> "Decimal":
    """Weighted contribution of an SO toward Total Amount Invoiced."""
    from decimal import Decimal

    amt = Decimal("0") if order_amount is None else Decimal(str(order_amount))
    st = (status or "").strip()
    if st == "Pending Invoice":
        return Decimal("0")
    if st == "50% Invoiced":
        return (amt * Decimal("0.5")).quantize(Decimal("0.01"))
    if st in ("100% Invoiced", "Payment Received"):
        return amt
    return Decimal("0")


def nre_remaining_to_invoice(status: str | None, order_amount) -> "Decimal":
    """Amount not yet invoiced. Empty/unknown status is treated as Pending Invoice."""
    from decimal import Decimal

    amt = Decimal("0") if order_amount is None else Decimal(str(order_amount))
    rem = amt - nre_invoiced_amount(status, order_amount)
    if rem < 0:
        rem = Decimal("0")
    return rem.quantize(Decimal("0.01"))


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
