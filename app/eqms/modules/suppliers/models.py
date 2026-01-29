from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base

if TYPE_CHECKING:
    from app.eqms.modules.equipment.models import EquipmentSupplier, ManagedDocument


class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        Index("idx_suppliers_name", "name"),
        Index("idx_suppliers_status", "status"),
        Index("idx_suppliers_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Required
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="Pending")  # Approved, Conditional, Pending, Rejected

    # Optional metadata
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g., "Component Supplier", "Service Provider"
    product_service_provided: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Address (single text blob for simplicity)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Dates
    initial_listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    certification_expiration: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Custom fields (admin-defined, stored as JSON)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    equipment_associations: Mapped[list["EquipmentSupplier"]] = relationship(
        "EquipmentSupplier",
        back_populates="supplier",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[list["ManagedDocument"]] = relationship(
        "ManagedDocument",
        back_populates="supplier",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="ManagedDocument.supplier_id",
    )
