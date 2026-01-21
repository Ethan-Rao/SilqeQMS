from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base

if TYPE_CHECKING:
    from app.eqms.modules.equipment.models import Equipment
    from app.eqms.modules.suppliers.models import Supplier


class ManufacturingLot(Base):
    __tablename__ = "manufacturing_lots"
    __table_args__ = (
        Index("idx_manufacturing_lots_lot_number", "lot_number"),
        Index("idx_manufacturing_lots_status", "status"),
        Index("idx_manufacturing_lots_product", "product_code"),
        Index("idx_manufacturing_lots_manufacture_date", "manufacture_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Required
    lot_number: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)  # e.g., "C.SLQ001-2026-001"
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, default="Suspension")  # "Suspension" or future products
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Draft")  # Draft, In-Process, Quarantined, Released, Rejected

    # Optional metadata
    work_order: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manufacture_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Start date or completion date
    manufacture_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Completion date (if different)

    # Operators (free text for now)
    operator: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Primary operator
    operator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # Additional operator info

    # QA Disposition (for Quarantined → Released/Rejected transition)
    disposition: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "Released", "Rejected"
    disposition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disposition_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    disposition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # QA review notes

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    documents: Mapped[list["ManufacturingLotDocument"]] = relationship(
        "ManufacturingLotDocument",
        back_populates="lot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    equipment_used: Mapped[list["ManufacturingLotEquipment"]] = relationship(
        "ManufacturingLotEquipment",
        back_populates="lot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    materials_used: Mapped[list["ManufacturingLotMaterial"]] = relationship(
        "ManufacturingLotMaterial",
        back_populates="lot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ManufacturingLotDocument(Base):
    __tablename__ = "manufacturing_lot_documents"
    __table_args__ = (
        Index("idx_manufacturing_lot_docs_lot", "lot_id"),
        Index("idx_manufacturing_lot_docs_type", "document_type"),
        Index("idx_manufacturing_lot_docs_uploaded_at", "uploaded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    lot_id: Mapped[int] = mapped_column(ForeignKey("manufacturing_lots.id", ondelete="CASCADE"), nullable=False)

    # File metadata
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Document categorization
    document_type: Mapped[str | None] = mapped_column(String(128), nullable=True)  # "Traveler", "QC Report", "COA", "Label", etc.
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    deleted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # Relationships
    lot: Mapped["ManufacturingLot"] = relationship("ManufacturingLot", back_populates="documents", lazy="selectin")


class ManufacturingLotEquipment(Base):
    __tablename__ = "manufacturing_lot_equipment"
    __table_args__ = (
        UniqueConstraint("lot_id", "equipment_id", name="uq_lot_equipment"),
        Index("idx_manufacturing_lot_equipment_lot", "lot_id"),
        Index("idx_manufacturing_lot_equipment_equipment", "equipment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    lot_id: Mapped[int] = mapped_column(ForeignKey("manufacturing_lots.id", ondelete="CASCADE"), nullable=False)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True)

    # Fallback if equipment not linked
    equipment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Optional metadata
    usage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    lot: Mapped["ManufacturingLot"] = relationship("ManufacturingLot", back_populates="equipment_used", lazy="selectin")
    equipment: Mapped["Equipment | None"] = relationship("Equipment", foreign_keys=[equipment_id], lazy="selectin")


class ManufacturingLotMaterial(Base):
    __tablename__ = "manufacturing_lot_materials"
    __table_args__ = (
        UniqueConstraint("lot_id", "material_identifier", name="uq_lot_material"),
        Index("idx_manufacturing_lot_materials_lot", "lot_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    lot_id: Mapped[int] = mapped_column(ForeignKey("manufacturing_lots.id", ondelete="CASCADE"), nullable=False)

    # Material identification
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    material_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    material_identifier: Mapped[str] = mapped_column(String(255), nullable=False)

    # Optional metadata
    quantity: Mapped[str | None] = mapped_column(String(128), nullable=True)  # "5 kg", "2 drums", etc.
    lot_number: Mapped[str | None] = mapped_column(String(128), nullable=True)  # Material lot number
    usage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    lot: Mapped["ManufacturingLot"] = relationship("ManufacturingLot", back_populates="materials_used", lazy="selectin")
    supplier: Mapped["Supplier | None"] = relationship("Supplier", foreign_keys=[supplier_id], lazy="selectin")
