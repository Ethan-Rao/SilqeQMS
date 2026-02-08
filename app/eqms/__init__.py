import os
from datetime import timedelta

from flask import Flask, g, render_template, request, session
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
from app.eqms.modules.equipment.admin import bp as equipment_bp
from app.eqms.modules.suppliers.admin import bp as suppliers_bp
from app.eqms.modules.supplies.admin import bp as supplies_bp
from app.eqms.modules.manufacturing.admin import bp as manufacturing_bp
from app.eqms.modules.nre_projects.admin import bp as nre_projects_bp


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(load_config())
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
    app.config["SESSION_REFRESH_EACH_REQUEST"] = True
    
    # Allow up to 50MB uploads (for bulk PDF imports)
    # Individual file limits (10MB) enforced in route handlers
    app.config.setdefault("MAX_CONTENT_LENGTH", 50 * 1024 * 1024)  # 50MB

    # CSRF protection (minimal)
    from app.eqms.security import ensure_csrf_token, validate_csrf

    @app.context_processor
    def _inject_csrf() -> dict:
        return {"csrf_token": ensure_csrf_token()}

    @app.context_processor
    def _inject_permissions() -> dict:
        from app.eqms.rbac import user_has_permission
        from flask import g as _g

        def has_perm(key: str) -> bool:
            return user_has_permission(getattr(_g, "current_user", None), key)

        return {"has_perm": has_perm}

    @app.template_filter("dateformat")
    def _dateformat_filter(value, format: str = "%Y-%m-%d") -> str:
        if value is None:
            return "—"
        if hasattr(value, "strftime"):
            return value.strftime(format)
        return str(value)

    @app.before_request
    def _csrf_guard():
        if request.path.startswith(("/static/", "/health", "/healthz")):
            return None
        ensure_csrf_token()
        session.permanent = True
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            # Allow safe auth endpoints to pass through (login/logout)
            if (request.endpoint or "").startswith("auth."):
                return None
            if not validate_csrf(request):
                return render_template("errors/400.html", message="CSRF token missing or invalid."), 400

    # Production guardrails (fail fast with clear logs)
    env = (app.config.get("ENV") or "").strip().lower()
    if env in ("prod", "production"):
        if not app.config.get("DATABASE_URL") or str(app.config["DATABASE_URL"]).strip() == "":
            raise RuntimeError("DATABASE_URL is required in production.")
        if str(app.config["DATABASE_URL"]).startswith("sqlite"):
            raise RuntimeError("DATABASE_URL must be Postgres in production (not sqlite).")
        if not app.config.get("SECRET_KEY") or str(app.config["SECRET_KEY"]) in ("", "change-me"):
            raise RuntimeError("SECRET_KEY must be set to a strong value in production (not default).")

    # DISABLED: Migration-on-start was causing deployment hangs.
    # Run migrations manually via DO Console: alembic upgrade head && python scripts/init_db.py
    # if (os.environ.get("RUN_MIGRATIONS_ON_START") or "").strip() == "1":
    #     from scripts.release import run_release
    #     app.logger.warning("RUN_MIGRATIONS_ON_START=1 set; running migrations + seed before boot.")
    #     run_release()

    init_db(app)

    def _dispose_engine_on_fork() -> None:
        import os
        if hasattr(os, "register_at_fork"):
            def _after_fork_child():
                engine = app.extensions.get("sqlalchemy_engine")
                if engine:
                    engine.dispose()
                    app.logger.info("Disposed DB engine after fork (pid=%s)", os.getpid())

            os.register_at_fork(after_in_child=_after_fork_child)

    _dispose_engine_on_fork()

    # Storage health check (fail loudly on misconfiguration)
    if app.config.get("STORAGE_BACKEND") == "s3":
        missing_s3 = []
        for key in ("S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
            if not app.config.get(key):
                missing_s3.append(key)
        if missing_s3:
            app.logger.error("STORAGE CONFIG ERROR: Missing required S3 env vars: %s", ", ".join(missing_s3))
        else:
            # Quick connectivity check (try to verify bucket access—fails fast if creds wrong)
            try:
                from app.eqms.storage import storage_from_config, S3Storage
                storage = storage_from_config(app.config)
                if isinstance(storage, S3Storage):
                    storage._client().head_bucket(Bucket=storage.bucket)
                    app.logger.info("Storage health check PASSED: S3 bucket '%s' accessible", storage.bucket)
            except Exception as e:
                app.logger.error("STORAGE CONFIG ERROR: Cannot access S3 bucket: %s", e)

    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doc_control_bp, url_prefix="/admin/modules/document-control")
    app.register_blueprint(rep_traceability_bp, url_prefix="/admin")
    app.register_blueprint(customer_profiles_bp, url_prefix="/admin")
    app.register_blueprint(shipstation_sync_bp, url_prefix="/admin")
    app.register_blueprint(equipment_bp, url_prefix="/admin")
    app.register_blueprint(suppliers_bp, url_prefix="/admin")
    app.register_blueprint(supplies_bp, url_prefix="/admin")
    app.register_blueprint(manufacturing_bp, url_prefix="/admin/manufacturing")
    app.register_blueprint(nre_projects_bp)

    def _load_user_wrapper():
        if request.path.startswith(("/static/", "/health", "/healthz")):
            g.current_user = None
            return None
        return load_current_user()

    app.before_request(_load_user_wrapper)
    app.teardown_appcontext(teardown_db_session)

    # Migration health (lean): detect drift between code expectations and DB schema.
    app.config.setdefault("_schema_health_ok", True)
    app.config.setdefault("_schema_health_missing", [])
    app.config.setdefault("_schema_health_logged", False)

    def _run_schema_health_check() -> None:
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
                for col in ("generated_by_user_id", "report_storage_key", "filters_json"):
                    if col not in cols:
                        missing.append(f"tracing_reports.{col}")

            if insp.has_table("shipstation_skipped_orders"):
                cols = {c["name"] for c in insp.get_columns("shipstation_skipped_orders")}
                if "details_json" not in cols:
                    missing.append("shipstation_skipped_orders.details_json")

            if not insp.has_table("sales_orders"):
                missing.append("sales_orders (table)")
            if not insp.has_table("sales_order_lines"):
                missing.append("sales_order_lines (table)")

            if insp.has_table("distribution_log_entries"):
                cols = {c["name"] for c in insp.get_columns("distribution_log_entries")}
                if "sales_order_id" not in cols:
                    missing.append("distribution_log_entries.sales_order_id")

        except Exception as e:
            app.logger.exception("Schema health check failed: %s", e)

        if missing:
            ok = False
            app.config["_schema_health_missing"] = missing
            if not app.config.get("_schema_health_logged"):
                app.config["_schema_health_logged"] = True
                app.logger.error("DB schema out of date; run `alembic upgrade head`. Missing: %s", ", ".join(missing))

        app.config["_schema_health_ok"] = ok

    _run_schema_health_check()

    @app.before_request
    def _schema_health_guardrail():  # type: ignore[no-redef]
        if app.config.get("_schema_health_ok"):
            return None
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

    @app.errorhandler(413)
    def _err_413(e):  # type: ignore[no-redef]
        from flask import flash, redirect, url_for

        flash("File too large. Maximum size is 50MB.", "danger")
        referrer = request.referrer
        if referrer and referrer.startswith(request.host_url):
            return redirect(referrer), 302
        return redirect(url_for("admin.index")), 302

    # Startup logging
    import logging
    logging.getLogger(__name__).info("create_app() complete; app ready to serve")

    return app

