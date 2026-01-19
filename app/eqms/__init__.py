import os

from flask import Flask, g, render_template, request
from dotenv import load_dotenv
from sqlalchemy import inspect as sa_inspect

from app.eqms.config import load_config
from app.eqms.db import init_db, teardown_db_session
from app.eqms.routes import bp as routes_bp
from app.eqms.auth import bp as auth_bp, load_current_user
from app.eqms.admin import bp as admin_bp
from app.eqms.modules.document_control.admin import bp as doc_control_bp
from app.eqms.modules.rep_traceability.admin import bp as rep_traceability_bp
from app.eqms.modules.customer_profiles.admin import bp as customer_profiles_bp
from app.eqms.modules.shipstation_sync.admin import bp as shipstation_sync_bp


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(load_config())

    # Production guardrails (fail fast with clear logs)
    env = (app.config.get("ENV") or "").strip().lower()
    if env in ("prod", "production"):
        if not app.config.get("DATABASE_URL") or str(app.config["DATABASE_URL"]).strip() == "":
            raise RuntimeError("DATABASE_URL is required in production.")
        if str(app.config["DATABASE_URL"]).startswith("sqlite"):
            raise RuntimeError("DATABASE_URL must be Postgres in production (not sqlite).")
        if not app.config.get("SECRET_KEY") or str(app.config["SECRET_KEY"]) in ("", "change-me"):
            raise RuntimeError("SECRET_KEY must be set to a strong value in production (not default).")

    # Optional one-time boot migration/seed (DigitalOcean toggle). Default OFF.
    if (os.environ.get("RUN_MIGRATIONS_ON_START") or "").strip() == "1":
        from scripts.release import run_release

        app.logger.warning("RUN_MIGRATIONS_ON_START=1 set; running migrations + seed before boot.")
        run_release()

    init_db(app)

    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doc_control_bp, url_prefix="/admin/modules/document-control")
    app.register_blueprint(rep_traceability_bp, url_prefix="/admin")
    app.register_blueprint(customer_profiles_bp, url_prefix="/admin")
    app.register_blueprint(shipstation_sync_bp, url_prefix="/admin")

    app.before_request(load_current_user)
    app.teardown_appcontext(teardown_db_session)

    # Migration health (lean): detect drift between code expectations and DB schema.
    app.config.setdefault("_schema_health_checked", False)
    app.config.setdefault("_schema_health_ok", True)
    app.config.setdefault("_schema_health_missing", [])
    app.config.setdefault("_schema_health_logged", False)

    @app.before_request
    def _schema_health_guardrail():  # type: ignore[no-redef]
        if not app.config.get("_schema_health_checked"):
            ok = True
            missing: list[str] = []
            try:
                engine = app.extensions.get("sqlalchemy_engine")
                if engine is None:
                    raise RuntimeError("sqlalchemy_engine not initialized")
                insp = sa_inspect(engine)
                if insp.has_table("distribution_log_entries"):
                    cols = {c["name"] for c in insp.get_columns("distribution_log_entries")}
                    if "external_key" not in cols:
                        missing.append("distribution_log_entries.external_key")
                if insp.has_table("tracing_reports"):
                    cols = {c["name"] for c in insp.get_columns("tracing_reports")}
                    if "generated_by_user_id" not in cols:
                        missing.append("tracing_reports.generated_by_user_id")
            except Exception as e:
                # If we can't inspect, don't break the app here—leave it to normal errors/logs.
                app.logger.exception("Schema health check failed: %s", e)

            if missing:
                ok = False
                app.config["_schema_health_missing"] = missing
                if not app.config.get("_schema_health_logged"):
                    app.config["_schema_health_logged"] = True
                    app.logger.error("DB schema out of date; run `alembic upgrade head`. Missing: %s", ", ".join(missing))

            app.config["_schema_health_ok"] = ok
            app.config["_schema_health_checked"] = True

        ok = bool(app.config.get("_schema_health_ok"))
        if ok:
            return None

        # Only short-circuit admin routes; keep public pages functional.
        if request.path.startswith("/admin") and getattr(g, "current_user", None):
            return render_template("errors/schema_out_of_date.html", missing=app.config.get("_schema_health_missing") or []), 500
        return None

    @app.errorhandler(500)
    def _err_500(e):  # type: ignore[no-redef]
        # Ensure stack trace shows in DO logs.
        try:
            from flask import g as _g

            rid = getattr(_g, "request_id", None)
        except Exception:
            rid = None
        app.logger.exception("Unhandled 500 (request_id=%s)", rid)
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def _err_403(e):  # type: ignore[no-redef]
        missing = getattr(g, "missing_permission", None)
        if missing:
            try:
                app.logger.warning("Forbidden: missing_permission=%s request_id=%s", missing, getattr(g, "request_id", None))
            except Exception:
                pass
        return render_template("errors/403.html", missing_permission=missing), 403

    return app

