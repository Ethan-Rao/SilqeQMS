from __future__ import annotations

import uuid

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.eqms.audit import record_event
from app.eqms.db import db_session
from app.eqms.models import User

bp = Blueprint("auth", __name__)


def load_current_user() -> None:
    """
    Loads g.current_user from the signed session cookie.
    Also assigns a simple per-request request_id (for audit/log correlation).
    """
    if not getattr(g, "request_id", None):
        g.request_id = uuid.uuid4().hex

    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return

    s = db_session()
    user = s.get(User, int(user_id))
    if not user or not user.is_active:
        session.pop("user_id", None)
        g.current_user = None
        return
    g.current_user = user


@bp.get("/login")
def login_get():
    return render_template("auth/login.html")


@bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

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
    record_event(s, actor=user, action="auth.login", entity_type="User", entity_id=str(user.id))
    s.commit()
    return redirect(url_for("admin.index"))


@bp.get("/logout")
def logout():
    s = db_session()
    user = getattr(g, "current_user", None)
    if user:
        record_event(s, actor=user, action="auth.logout", entity_type="User", entity_id=str(user.id))
        s.commit()
    session.pop("user_id", None)
    return redirect(url_for("routes.index"))

