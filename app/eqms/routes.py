from flask import Blueprint, render_template

bp = Blueprint("routes", __name__)


@bp.get("/")
def index():
    return render_template("public/index.html")


@bp.get("/health")
def health():
    return {"ok": True}

