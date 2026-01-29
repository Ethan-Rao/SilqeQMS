from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base

if TYPE_CHECKING:
    from app.eqms.modules.suppliers.models import Supplier


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        Index("idx_equipment_code", "equip_code"),
        Index("idx_equipment_status", "status"),
        Index("idx_equipment_location", "location"),
        Index("idx_equipment_cal_due", "cal_due_date"),
        Index("idx_equipment_pm_due", "pm_due_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Required
    equip_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # e.g., "ST-001"
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="Active")  # Active, Inactive, Retired, Calibration Overdue, PM Overdue

    # Optional metadata
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mfg: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Manufacturer
    model_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Dates
    date_in_service: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Location
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Calibration tracking
    cal_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Days between calibrations
    last_cal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cal_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # PM tracking
    pm_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Days between PMs
    last_pm_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pm_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Notes
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Custom fields (admin-defined, stored as JSON)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    supplier_associations: Mapped[list["EquipmentSupplier"]] = relationship(
        "EquipmentSupplier",
        back_populates="equipment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[list["ManagedDocument"]] = relationship(
        "ManagedDocument",
        back_populates="equipment",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="ManagedDocument.equipment_id",
    )


class EquipmentSupplier(Base):
    __tablename__ = "equipment_suppliers"
    __table_args__ = (
        UniqueConstraint("equipment_id", "supplier_id", name="uq_equipment_supplier"),
        Index("idx_equipment_suppliers_equipment", "equipment_id"),
        Index("idx_equipment_suppliers_supplier", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)

    # Optional relationship metadata
    relationship_type: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g., "Manufacturer", "Service Provider", "Parts Supplier"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="supplier_associations", lazy="selectin")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="equipment_associations", lazy="selectin")


class ManagedDocument(Base):
    __tablename__ = "managed_documents"
    __table_args__ = (
        Index("idx_managed_docs_entity", "entity_type", "entity_id"),
        Index("idx_managed_docs_uploaded_at", "uploaded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Entity linkage (polymorphic)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "equipment" or "supplier"
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FK to equipment.id or suppliers.id

    # Optional explicit FKs for referential integrity
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=True)

    # File metadata
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Document metadata
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g., "Calibration Cert", "PM Record", "Audit Report", "COI"
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    deleted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # Relationships
    equipment: Mapped["Equipment | None"] = relationship("Equipment", foreign_keys=[equipment_id], lazy="selectin")
    supplier: Mapped["Supplier | None"] = relationship("Supplier", foreign_keys=[supplier_id], lazy="selectin")
