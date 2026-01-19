from datetime import date, datetime, time, timedelta

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.eqms.db import db_session
from app.eqms.models import AuditEvent, User
from app.eqms.rbac import require_permission

bp = Blueprint("admin", __name__)


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


@bp.get("/")
@require_permission("admin.view")
def index():
    return render_template("admin/index.html")


@bp.get("/modules/<module_key>")
@require_permission("admin.view")
def module_stub(module_key: str):
    # Minimal scaffold route; real module pages will be built in the new eQMS repo.
    return render_template("admin/module_stub.html", module_key=module_key)


@bp.get("/me")
@require_permission("admin.view")
def me():
    user = getattr(g, "current_user", None)
    role_keys: list[str] = []
    perm_keys: list[str] = []
    if user:
        role_keys = sorted({r.key for r in (user.roles or [])})
        perms = set()
        for r in user.roles or []:
            for p in r.permissions or []:
                perms.add(p.key)
        perm_keys = sorted(perms)
    return render_template("admin/me.html", user=user, role_keys=role_keys, perm_keys=perm_keys)


@bp.get("/audit")
@require_permission("admin.view")
def audit_list():
    """
    Minimal audit trail UI (last 200 events) with simple filters:
    - action (exact/contains)
    - actor_email (contains)
    - date range (YYYY-MM-DD)
    """
    s = db_session()
    action = (request.args.get("action") or "").strip()
    actor_email = (request.args.get("actor_email") or "").strip()
    date_from = _parse_date(request.args.get("date_from") or "")
    date_to = _parse_date(request.args.get("date_to") or "")

    if (request.args.get("date_from") or "").strip() and not date_from:
        flash("date_from must be YYYY-MM-DD", "danger")
    if (request.args.get("date_to") or "").strip() and not date_to:
        flash("date_to must be YYYY-MM-DD", "danger")

    q = s.query(AuditEvent)
    if action:
        like = f"%{action}%"
        q = q.filter(AuditEvent.action.like(like))
    if actor_email:
        like = f"%{actor_email.lower()}%"
        q = q.filter(AuditEvent.actor_user_email.like(like))
    if date_from:
        q = q.filter(AuditEvent.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        # inclusive end-date (treat as whole day)
        q = q.filter(AuditEvent.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    events = q.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(200).all()
    return render_template(
        "admin/audit/list.html",
        events=events,
        action=action,
        actor_email=actor_email,
        date_from=(request.args.get("date_from") or "").strip(),
        date_to=(request.args.get("date_to") or "").strip(),
    )


@bp.get("/login")
def login_redirect():
    return redirect(url_for("auth.login_get"))

