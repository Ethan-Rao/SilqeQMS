import os

from flask import Flask, render_template
from dotenv import load_dotenv

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

    return app

