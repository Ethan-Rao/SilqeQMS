from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.eqms.audit import record_event
from app.eqms.db import db_session
from app.eqms.models import User

bp = Blueprint("auth", __name__)
_login_attempts: dict[str, list[datetime]] = defaultdict(list)
_LOGIN_RATE_LIMIT = 5
_LOGIN_RATE_WINDOW = 300  # seconds


def _check_rate_limit(ip: str) -> bool:
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=_LOGIN_RATE_WINDOW)
    _login_attempts[ip] = [t for t in _login_attempts[ip] if t > cutoff]
    return len(_login_attempts[ip]) >= _LOGIN_RATE_LIMIT


def _record_attempt(ip: str) -> None:
    _login_attempts[ip].append(datetime.utcnow())


def load_current_user() -> None:
    """
    Loads g.current_user from the signed session cookie.
    Also assigns a simple per-request request_id (for audit/log correlation).
    """
    if not getattr(g, "request_id", None):
        g.request_id = uuid.uuid4().hex
    if request.path.startswith(("/static/", "/health", "/healthz")):
        g.current_user = None
        return

    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return

    try:
        s = db_session()
        user = s.get(User, int(user_id))
        if not user or not user.is_active:
            session.pop("user_id", None)
            g.current_user = None
            return
        g.current_user = user
    except Exception as e:
        current_app.logger.error("load_current_user DB error (clearing session): %s", e)
        session.pop("user_id", None)
        g.current_user = None


@bp.get("/login")
def login_get():
    nxt = (request.args.get("next") or "").strip()
    return render_template("auth/login.html", next=nxt)


@bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    nxt = (request.form.get("next") or "").strip()
    ip = request.remote_addr or "unknown"

    if _check_rate_limit(ip):
        flash("Too many login attempts. Please wait 5 minutes.", "danger")
        return redirect(url_for("auth.login_get"))

    _record_attempt(ip)

    try:
        s = db_session()
        user = s.query(User).filter(User.email == email).one_or_none()
        if not user or not user.is_active or not check_password_hash(user.password_hash, password):
            record_event(
                s,
                actor=None,
                action="auth.login_failed",
                entity_type="User",
                entity_id=email,
                reason="Invalid credentials",
                metadata={"email": email},
            )
            s.commit()
            flash("Invalid credentials.", "danger")
            return redirect(url_for("auth.login_get"))

        session["user_id"] = user.id
        _login_attempts[ip].clear()
        record_event(s, actor=user, action="auth.login", entity_type="User", entity_id=str(user.id))
        s.commit()
        # Optional "next" redirect (only allow local paths to avoid open redirects).
        if nxt.startswith("/") and not nxt.startswith("//"):
            return redirect(nxt)
        return redirect(url_for("admin.index"))
    except Exception:
        current_app.logger.exception("Login POST crashed (email=%s request_id=%s)", email, getattr(g, "request_id", None))
        raise


@bp.get("/logout")
def logout():
    s = db_session()
    user = getattr(g, "current_user", None)
    if user:
        record_event(s, actor=user, action="auth.logout", entity_type="User", entity_id=str(user.id))
        s.commit()
    session.pop("user_id", None)
    return redirect(url_for("routes.index"))

