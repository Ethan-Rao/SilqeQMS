import json
from typing import Any

from flask import g, request
from sqlalchemy.orm import Session

from app.eqms.models import AuditEvent, User


def record_event(
    s: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> AuditEvent:
    """
    Append-only audit event helper.
    """
    rid = request_id or getattr(g, "request_id", None)
    ev = AuditEvent(
        request_id=rid,
        actor_user_id=actor.id if actor else None,
        actor_user_email=actor.email if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        reason=reason,
        metadata_json=json.dumps(metadata, sort_keys=True) if metadata else None,
        client_ip=request.remote_addr if request else None,
    )
    s.add(ev)
    return ev

