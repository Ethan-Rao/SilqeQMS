from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users",
        lazy="selectin",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # e.g. "admin"
    name: Mapped[str] = mapped_column(String(128), nullable=False)  # display name
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    users: Mapped[list[User]] = relationship(secondary="user_roles", back_populates="roles", lazy="selectin")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)  # e.g. "admin.view"
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    roles: Mapped[list[Role]] = relationship(secondary="role_permissions", back_populates="permissions", lazy="selectin")


class AuditEvent(Base):
    """
    Append-only audit trail event.
    Keep this table intentionally generic; module-specific tables can refer to it by id if needed.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("request_id", "id", name="uq_audit_request_id_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_user_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    action: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. "user.login"
    entity_type: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g. "Document"
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)  # string for flexibility (uuid/int)

    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)  # reason-for-change
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # small JSON string


# Ensure module models are imported so Base.metadata includes their tables.
# (Kept at bottom to avoid circular imports.)
from app.eqms.modules.document_control.models import Document, DocumentFile, DocumentRevision  # noqa: E402,F401
from app.eqms.modules.rep_traceability.models import (  # noqa: E402,F401
    ApprovalEml,
    DistributionLogEntry,
    TracingReport,
)
from app.eqms.modules.customer_profiles.models import Customer, CustomerNote  # noqa: E402,F401
from app.eqms.modules.shipstation_sync.models import ShipStationSkippedOrder, ShipStationSyncRun  # noqa: E402,F401
from app.eqms.modules.suppliers.models import Supplier  # noqa: E402,F401
from app.eqms.modules.equipment.models import Equipment, EquipmentSupplier, ManagedDocument  # noqa: E402,F401
from app.eqms.modules.manufacturing.models import (  # noqa: E402,F401
    ManufacturingLot,
    ManufacturingLotDocument,
    ManufacturingLotEquipment,
    ManufacturingLotMaterial,
)