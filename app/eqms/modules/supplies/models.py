from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base

if TYPE_CHECKING:
    from app.eqms.modules.suppliers.models import Supplier


class Supply(Base):
    __tablename__ = "supplies"
    __table_args__ = (
        Index("idx_supplies_code", "supply_code"),
        Index("idx_supplies_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    supply_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="Active")

    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True)

    min_stock_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_of_measure: Mapped[str | None] = mapped_column(String(32), nullable=True)

    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    supplier_associations: Mapped[list["SupplySupplier"]] = relationship(
        "SupplySupplier",
        back_populates="supply",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[list["SupplyDocument"]] = relationship(
        "SupplyDocument",
        back_populates="supply",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SupplySupplier(Base):
    __tablename__ = "supply_suppliers"
    __table_args__ = (
        Index("idx_supply_suppliers_supply", "supply_id"),
        Index("idx_supply_suppliers_supplier", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    supply: Mapped["Supply"] = relationship("Supply", back_populates="supplier_associations")
    supplier: Mapped["Supplier"] = relationship("Supplier", backref="supply_associations")


class SupplyDocument(Base):
    __tablename__ = "supply_documents"
    __table_args__ = (
        Index("idx_supply_docs_supply", "supply_id"),
        Index("idx_supply_docs_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id", ondelete="CASCADE"), nullable=False)

    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/pdf")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    supply: Mapped["Supply"] = relationship("Supply", back_populates="documents")
