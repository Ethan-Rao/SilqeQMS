from flask import Blueprint, g, redirect, render_template, url_for

from app.eqms.rbac import require_permission

bp = Blueprint("admin", __name__)


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
    return render_template("admin/me.html", user=getattr(g, "current_user", None))


@bp.get("/login")
def login_redirect():
    return redirect(url_for("auth.login_get"))

