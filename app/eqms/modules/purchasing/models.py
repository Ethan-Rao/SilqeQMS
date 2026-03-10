from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text
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

    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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
