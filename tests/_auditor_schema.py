"""Minimal table set for auditor portal tests (avoids full-metadata FK ordering issues on SQLite)."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.eqms.models import AuditEvent, Base, Permission, Role, RolePermission, User, UserRole
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.auditor_portal.models import AuditorAccessEvent


def create_auditor_test_schema(engine: Engine, *, include_admin_docs: bool = False) -> None:
    tables = [
        Permission.__table__,
        Role.__table__,
        User.__table__,
        RolePermission.__table__,
        UserRole.__table__,
        AuditEvent.__table__,
        AuditorAccessEvent.__table__,
    ]
    if include_admin_docs:
        tables.extend([AdminDocFolder.__table__, AdminDocFile.__table__])
    Base.metadata.create_all(bind=engine, tables=tables)
