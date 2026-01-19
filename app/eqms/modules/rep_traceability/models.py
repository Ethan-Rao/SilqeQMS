from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base


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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    customer: Mapped["Customer | None"] = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")


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

