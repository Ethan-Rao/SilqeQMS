from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base
from app.eqms.utils import utcnow


class PurchaseOrder(Base):
    """Purchase order from a supplier."""

    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','received','partial','cancelled')",
            name="ck_purchase_orders_status",
        ),
        Index("idx_purchase_orders_supplier_id", "supplier_id"),
        Index("idx_purchase_orders_po_number", "po_number"),
        Index("idx_purchase_orders_order_date", "order_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    po_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # PO Log alignment (SILQ PO Log.xlsx): cost, acceptance, verification, closure, references
    amount: Mapped[str | None] = mapped_column(String(64), nullable=True)  # "Cost Info." (kept as text; log holds bare numbers)
    meets_requirements: Mapped[str | None] = mapped_column(String(16), nullable=True)  # "Yes" / "No" / None
    verified_how: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g. "Receiving inspection", "Email confirmation"
    closed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)  # initials + date, e.g. "ER 01 Mar 2026"
    reference: Mapped[str | None] = mapped_column(Text, nullable=True)  # "References" column

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    supplier: Mapped["Supplier | None"] = relationship("Supplier", lazy="selectin")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="purchase_order", cascade="all, delete-orphan", lazy="selectin"
    )
    attachments: Mapped[list["PurchaseOrderAttachment"]] = relationship(
        "PurchaseOrderAttachment", back_populates="purchase_order", cascade="all, delete-orphan", lazy="selectin"
    )


class PurchaseOrderLine(Base):
    """Line item on a purchase order."""

    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        Index("idx_po_lines_purchase_order_id", "purchase_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)

    item_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[str | None] = mapped_column(String(32), nullable=True)

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")


class PurchaseOrderAttachment(Base):
    """Attachment (PDF, EML) for a purchase order."""

    __tablename__ = "purchase_order_attachments"
    __table_args__ = (
        CheckConstraint(
            "attachment_type IN ('po_pdf','confirmation_pdf','confirmation_eml','other')",
            name="ck_po_attachments_type",
        ),
        Index("idx_po_attachments_purchase_order_id", "purchase_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)

    attachment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="attachments")


class PaymentEntry(Base):
    """Lightweight, manually-maintained ledger of upcoming payments.

    Entries are ad-hoc (not tied to a PurchaseOrder FK) so the team can track
    pending payments whether or not they originate from a formal PO.
    """

    __tablename__ = "payment_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    payment_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    attachments: Mapped[list["PaymentEntryAttachment"]] = relationship(
        "PaymentEntryAttachment", back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )


class PaymentEntryAttachment(Base):
    """File attached to a payment-ledger entry."""

    __tablename__ = "payment_entry_attachments"
    __table_args__ = (
        Index("idx_pay_att_entry", "payment_entry_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_entry_id: Mapped[int] = mapped_column(ForeignKey("payment_entries.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    entry: Mapped["PaymentEntry"] = relationship("PaymentEntry", back_populates="attachments")
