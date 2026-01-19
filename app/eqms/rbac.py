from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import abort, g, redirect, request, url_for

from app.eqms.models import User


def user_has_permission(user: User | None, permission_key: str) -> bool:
    if not user or not user.is_active:
        return False
    for role in user.roles:
        for perm in role.permissions:
            if perm.key == permission_key:
                return True
    return False


def require_permission(permission_key: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any):
            user: User | None = getattr(g, "current_user", None)
            # Unauthenticated → redirect to login (UX + reduces confusion).
            if not user or not user.is_active:
                nxt = request.full_path or request.path
                # Avoid trailing '?' from full_path when there is no query string.
                if nxt.endswith("?"):
                    nxt = nxt[:-1]
                return redirect(url_for("auth.login_get", next=nxt))
            # Authenticated but unauthorized → 403
            if not user_has_permission(user, permission_key):
                abort(403)
            return fn(*args, **kwargs)

        return wrapped

    return decorator

