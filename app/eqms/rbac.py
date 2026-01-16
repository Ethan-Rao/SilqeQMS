from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import abort, g

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
            if not user_has_permission(user, permission_key):
                abort(403)
            return fn(*args, **kwargs)

        return wrapped

    return decorator

