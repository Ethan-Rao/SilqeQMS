from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.eqms.models import Base
from app.eqms.utils import utcnow

STATUSES = ["Open", "Pending Effectiveness", "Closed", "Cancelled"]
ROOT_CAUSE_CATEGORIES = [
    "Process", "Equipment", "Supplier", "Documentation", "Training", "Design", "Other",
]


class CAPARecord(Base):
    """A Corrective and Preventive Action record (QM.SLQ016)."""

    __tablename__ = "capa_records"
    __table_args__ = (
        Index("idx_capa_records_status", "status"),
        Index("idx_capa_records_number", "capa_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    capa_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Open")

    opened_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    root_cause_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrective_actions: Mapped[str | None] = mapped_column(Text, nullable=True)

    effectiveness_check_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effectiveness_result: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Section completion tracking (from SILQ CAPA Log, QM.SLQ016)
    initiated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    section_1_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    section_2_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    section_3_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    section_4_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    section_5_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    section_6_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    on_time_status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    linked_doc_number: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, default=utcnow, onupdate=utcnow
    )
