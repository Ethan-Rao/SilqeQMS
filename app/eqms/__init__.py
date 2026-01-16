from flask import Flask
from dotenv import load_dotenv

from app.eqms.config import load_config
from app.eqms.db import init_db, teardown_db_session
from app.eqms.routes import bp as routes_bp
from app.eqms.auth import bp as auth_bp, load_current_user
from app.eqms.admin import bp as admin_bp
from app.eqms.modules.document_control.admin import bp as doc_control_bp
from app.eqms.modules.rep_traceability.admin import bp as rep_traceability_bp


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_mapping(load_config())

    init_db(app)

    app.register_blueprint(routes_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doc_control_bp, url_prefix="/admin/modules/document-control")
    app.register_blueprint(rep_traceability_bp, url_prefix="/admin")

    app.before_request(load_current_user)
    app.teardown_appcontext(teardown_db_session)

    return app

