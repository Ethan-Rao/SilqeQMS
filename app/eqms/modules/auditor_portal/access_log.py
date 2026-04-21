from __future__ import annotations

from flask import g, request
from sqlalchemy.orm import Session

from app.eqms.audit import record_event
from app.eqms.models import User
from app.eqms.modules.auditor_portal.models import AuditorAccessEvent


def record_access(
    s: Session,
    *,
    user: User | None,
    action: str,
    rel_path: str,
    file_size: int | None = None,
) -> None:
    """Persist one access row and mirror a coarse row to audit_events."""
    ev = AuditorAccessEvent(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        rel_path=rel_path,
        file_size=file_size,
        ip=request.remote_addr if request else None,
        user_agent=(request.headers.get("User-Agent") or "")[:512] if request else None,
        request_id=getattr(g, "request_id", None),
    )
    s.add(ev)
    s.commit()
    record_event(
        s,
        actor=user,
        action=f"auditor_portal.{action}",
        entity_type="AuditorFile",
        entity_id=rel_path[:128],
    )
    s.commit()
