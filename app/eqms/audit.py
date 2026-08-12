import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from flask import g, request
from sqlalchemy.orm import Session

from app.eqms.models import AuditEvent, User


def _json_default(obj: Any) -> Any:
    """Fallback for date/datetime/Decimal so audit writes never 500."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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
    from flask import has_app_context, has_request_context

    rid = request_id
    if rid is None and has_app_context():
        rid = getattr(g, "request_id", None)
    client_ip = request.remote_addr if has_request_context() else None
    # default= is only invoked for non-serializable values; clean metadata stays byte-identical.
    metadata_json = (
        json.dumps(metadata, sort_keys=True, default=_json_default) if metadata else None
    )
    ev = AuditEvent(
        request_id=rid,
        actor_user_id=actor.id if actor else None,
        actor_user_email=actor.email if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        reason=reason,
        metadata_json=metadata_json,
        client_ip=client_ip,
    )
    s.add(ev)
    return ev
