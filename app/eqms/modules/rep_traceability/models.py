from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base


class SalesOrder(Base):
    """Sales order - source of truth for customer identity and order assignment."""
    __tablename__ = "sales_orders"
    __table_args__ = (
        CheckConstraint(
            "source IN ('shipstation','manual','csv_import','pdf_import')",
            name="ck_sales_orders_source",
        ),
        CheckConstraint(
            "status IN ('pending','shipped','cancelled','completed')",
            name="ck_sales_orders_status",
        ),
        Index("idx_sales_orders_customer_id", "customer_id"),
        Index("idx_sales_orders_order_number", "order_number"),
        Index("idx_sales_orders_order_date", "order_date"),
        Index("idx_sales_orders_ship_date", "ship_date"),
        Index("idx_sales_orders_source", "source"),
        Index("idx_sales_orders_status", "status"),
        Index("uq_sales_orders_source_external_key", "source", "external_key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Order identification
    order_number: Mapped[str] = mapped_column(Text, nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    ship_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Customer (source of truth)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)

    # Source
    source: Mapped[str] = mapped_column(Text, nullable=False)

    # External references
    ss_order_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional metadata
    rep_id: Mapped[int | None] = mapped_column(ForeignKey("reps.id", ondelete="SET NULL"), nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")
    lines: Mapped[list["SalesOrderLine"]] = relationship(
        "SalesOrderLine",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    distributions: Mapped[list["DistributionLogEntry"]] = relationship(
        "DistributionLogEntry",
        back_populates="sales_order",
        lazy="selectin",
    )
    pdf_attachments: Mapped[list["OrderPdfAttachment"]] = relationship(
        "OrderPdfAttachment",
        back_populates="sales_order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SalesOrderLine(Base):
    """Sales order line item - individual SKU/quantity on an order."""
    __tablename__ = "sales_order_lines"
    __table_args__ = (
        CheckConstraint(
            "sku IN ('211810SPT','211610SPT','211410SPT')",
            name="ck_sales_order_lines_sku",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_sales_order_lines_quantity",
        ),
        Index("idx_sales_order_lines_sales_order_id", "sales_order_id"),
        Index("idx_sales_order_lines_sku", "sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Link to order
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False)

    # Line item details
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    lot_number: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Line item metadata
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    # Relationships
    order: Mapped[SalesOrder] = relationship("SalesOrder", back_populates="lines", lazy="selectin")


class OrderPdfAttachment(Base):
    __tablename__ = "order_pdf_attachments"
    __table_args__ = (
        Index("idx_order_pdf_attachments_sales_order_id", "sales_order_id"),
        Index("idx_order_pdf_attachments_distribution_entry_id", "distribution_entry_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=True)
    distribution_entry_id: Mapped[int | None] = mapped_column(ForeignKey("distribution_log_entries.id", ondelete="SET NULL"), nullable=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_type: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    sales_order: Mapped[SalesOrder | None] = relationship("SalesOrder", back_populates="pdf_attachments", lazy="selectin")


class DistributionLine(Base):
    """Individual SKU/lot on a distribution entry."""
    __tablename__ = "distribution_lines"
    __table_args__ = (
        CheckConstraint(
            "sku IN ('211810SPT','211610SPT','211410SPT')",
            name="ck_distribution_lines_sku",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_distribution_lines_quantity",
        ),
        Index("idx_distribution_lines_entry_id", "distribution_entry_id"),
        Index("idx_distribution_lines_sku", "sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    distribution_entry_id: Mapped[int] = mapped_column(
        ForeignKey("distribution_log_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    lot_number: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    distribution_entry: Mapped["DistributionLogEntry"] = relationship("DistributionLogEntry", back_populates="lines", lazy="selectin")


class DistributionLogEntry(Base):
    __tablename__ = "distribution_log_entries"
    __table_args__ = (
        CheckConstraint(
            "sku IN ('211810SPT','211610SPT','211410SPT')",
            name="ck_distribution_log_sku",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_distribution_log_quantity",
        ),
        CheckConstraint(
            "source IN ('shipstation','manual','csv_import','pdf_import')",
            name="ck_distribution_log_source",
        ),
        # Indexes for filtering/search
        Index("idx_distribution_log_ship_date", "ship_date"),
        Index("idx_distribution_log_source", "source"),
        Index("idx_distribution_log_rep_id", "rep_id"),
        Index("idx_distribution_log_sku", "sku"),
        Index("idx_distribution_log_order_number", "order_number"),
        Index("idx_distribution_log_customer_name", "customer_name"),
        Index("idx_distribution_log_customer_id", "customer_id"),
        Index("idx_distribution_log_facility_name", "facility_name"),
        Index("idx_distribution_log_sales_order_id", "sales_order_id"),
        # ShipStation idempotency (external_key is per-source unique; NULL allowed for manual/csv)
        Index("uq_distribution_log_source_external_key", "source", "external_key", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Required
    ship_date: Mapped[date] = mapped_column(Date, nullable=False)
    order_number: Mapped[str] = mapped_column(Text, nullable=False)
    facility_name: Mapped[str] = mapped_column(Text, nullable=False)
    rep_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    lot_number: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional (lean: keep customer as text; no CRM table in v1)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    rep_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    address1: Mapped[str | None] = mapped_column(Text, nullable=True)
    address2: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    zip: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(Text, nullable=True, default="USA")

    contact_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    ss_shipment_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_file_storage_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Link to sales order (source of truth)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    customer: Mapped["Customer | None"] = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")
    sales_order: Mapped["SalesOrder | None"] = relationship("SalesOrder", back_populates="distributions", lazy="selectin")
    lines: Mapped[list["DistributionLine"]] = relationship(
        "DistributionLine",
        back_populates="distribution_entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TracingReport(Base):
    __tablename__ = "tracing_reports"
    __table_args__ = (
        CheckConstraint("report_format = 'csv'", name="ck_tracing_reports_format"),
        CheckConstraint("status IN ('draft','final')", name="ck_tracing_reports_status"),
        Index("idx_tracing_reports_generated_at", "generated_at"),
        Index("idx_tracing_reports_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    generated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    filters_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string (Postgres JSONB-ready later)

    report_storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    report_format: Mapped[str] = mapped_column(String(16), nullable=False, default="csv")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")

    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    approvals: Mapped[list["ApprovalEml"]] = relationship(
        "ApprovalEml",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ApprovalEml(Base):
    __tablename__ = "approvals_eml"
    __table_args__ = (
        Index("idx_approvals_eml_report_id", "report_id"),
        Index("idx_approvals_eml_uploaded_at", "uploaded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    report_id: Mapped[int] = mapped_column(ForeignKey("tracing_reports.id", ondelete="CASCADE"), nullable=False)

    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)

    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    from_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    report: Mapped[TracingReport] = relationship("TracingReport", back_populates="approvals", lazy="selectin")

