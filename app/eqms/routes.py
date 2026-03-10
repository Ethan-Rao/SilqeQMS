from flask import Blueprint, current_app, render_template
from sqlalchemy import text as sa_text

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


@bp.get("/health/deep")
def health_deep():
    """Deep health check — verifies database connectivity and storage.

    Use this for readiness probes that need to confirm the app can actually
    serve requests (F-047).
    """
    checks: dict[str, object] = {"ok": True}

    # Database check
    try:
        engine = current_app.extensions.get("sqlalchemy_engine")
        if engine is None:
            raise RuntimeError("No engine")
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        checks["ok"] = False

    # Storage check
    try:
        from app.eqms.storage import storage_from_config, S3Storage
        storage = storage_from_config(current_app.config)
        if isinstance(storage, S3Storage):
            storage._client().head_bucket(Bucket=storage.bucket)
            checks["storage"] = "ok (s3)"
        else:
            checks["storage"] = "ok (local)"
    except Exception as e:
        checks["storage"] = f"error: {e}"
        checks["ok"] = False

    status_code = 200 if checks["ok"] else 503
    return checks, status_code

