from flask import Blueprint, render_template

bp = Blueprint("routes", __name__)


@bp.get("/")
def index():
    return render_template("public/index.html")


@bp.get("/health")
def health():
    """Health check endpoint. Returns JSON."""
    return {"ok": True}


@bp.get("/healthz")
def healthz():
    """
    Fast health check for k8s/DO probes. No DB access, minimal overhead.
    Configure DO readiness probe to use this endpoint.
    """
    return "ok", 200

