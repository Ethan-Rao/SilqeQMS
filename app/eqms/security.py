import secrets
from flask import session, Request


def ensure_csrf_token() -> str:
    """Ensure a CSRF token exists in the session and return it."""
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf(req: Request) -> bool:
    """Validate CSRF token from form or header."""
    token = req.headers.get("X-CSRF-Token") or req.form.get("csrf_token")
    return bool(token and token == session.get("csrf_token"))
