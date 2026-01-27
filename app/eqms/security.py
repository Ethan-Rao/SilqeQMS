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
    """Validate CSRF token from form, header, or JSON body."""
    token = req.headers.get("X-CSRF-Token") or req.form.get("csrf_token")
    
    # Also check JSON body for API-style requests
    if not token and req.is_json:
        try:
            json_data = req.get_json(silent=True) or {}
            token = json_data.get("csrf_token")
        except Exception:
            pass
    
    return bool(token and token == session.get("csrf_token"))
