from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import abort, current_app, g, redirect, request, url_for

from app.eqms.models import User


def user_has_permission(user: User | None, permission_key: str) -> bool:
    if not user or not user.is_active:
        return False
    for role in user.roles:
        for perm in role.permissions:
            if perm.key == permission_key:
                return True
    return False


def user_has_any_permission(user: User | None, permission_keys: "tuple[str, ...] | list[str]") -> bool:
    """True if the user holds at least one of the given permission keys."""
    if not user or not user.is_active:
        return False
    keys = set(permission_keys)
    for role in user.roles:
        for perm in role.permissions:
            if perm.key in keys:
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
                # Make 403 debuggable in production.
                g.missing_permission = permission_key  # type: ignore[attr-defined]
                try:
                    current_app.logger.warning(
                        "RBAC denied: user=%s missing=%s path=%s",
                        getattr(user, "email", None),
                        permission_key,
                        request.path,
                    )
                except Exception:
                    pass
                abort(403)
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def require_any_permission(*permission_keys: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Authorize a route if the user holds ANY of the given permission keys.

    Used for read-only pages that both admins (admin.view) and staff
    (staff.view) may open. Mirrors require_permission behaviour: unauthenticated
    users are redirected to login, authenticated-but-unauthorized users get 403.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any):
            user: User | None = getattr(g, "current_user", None)
            if not user or not user.is_active:
                nxt = request.full_path or request.path
                if nxt.endswith("?"):
                    nxt = nxt[:-1]
                return redirect(url_for("auth.login_get", next=nxt))
            if not user_has_any_permission(user, permission_keys):
                g.missing_permission = " or ".join(permission_keys)  # type: ignore[attr-defined]
                try:
                    current_app.logger.warning(
                        "RBAC denied: user=%s missing_any=%s path=%s",
                        getattr(user, "email", None),
                        permission_keys,
                        request.path,
                    )
                except Exception:
                    pass
                abort(403)
            return fn(*args, **kwargs)

        return wrapped

    return decorator

