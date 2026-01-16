import sys
from pathlib import Path
import os

from werkzeug.security import generate_password_hash

# Ensure repo root is on sys.path when running as a script (Windows-friendly).
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.wsgi import app
from app.eqms.db import session_scope
from app.eqms.models import Permission, Role, User


def main() -> None:
    # Run migrations (preferred) before seeding.
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", app.config["DATABASE_URL"])
    command.upgrade(cfg, "head")

    admin_email = (os.environ.get("ADMIN_EMAIL") or "admin@silqeqms.com").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD") or "change-me"

    with session_scope(app) as s:
        # Permissions (idempotent)
        def ensure_perm(key: str, name: str) -> Permission:
            p = s.query(Permission).filter(Permission.key == key).one_or_none()
            if not p:
                p = Permission(key=key, name=name)
                s.add(p)
            return p

        p_admin_view = ensure_perm("admin.view", "Admin: view shell")

        # Document Control (v1)
        p_docs_view = ensure_perm("docs.view", "Docs: view")
        p_docs_create = ensure_perm("docs.create", "Docs: create")
        p_docs_edit = ensure_perm("docs.edit", "Docs: edit drafts")
        p_docs_release = ensure_perm("docs.release", "Docs: release")
        p_docs_obsolete = ensure_perm("docs.obsolete", "Docs: obsolete")
        p_docs_download = ensure_perm("docs.download", "Docs: download")

        # REP Traceability (P0)
        p_dist_view = ensure_perm("distribution_log.view", "Distribution Log: view")
        p_dist_create = ensure_perm("distribution_log.create", "Distribution Log: create")
        p_dist_edit = ensure_perm("distribution_log.edit", "Distribution Log: edit")
        p_dist_delete = ensure_perm("distribution_log.delete", "Distribution Log: delete")
        p_dist_import = ensure_perm("distribution_log.import", "Distribution Log: import")
        p_dist_export = ensure_perm("distribution_log.export", "Distribution Log: export")

        p_tracing_view = ensure_perm("tracing_reports.view", "Tracing Reports: view")
        p_tracing_generate = ensure_perm("tracing_reports.generate", "Tracing Reports: generate")
        p_tracing_download = ensure_perm("tracing_reports.download", "Tracing Reports: download")

        p_approvals_view = ensure_perm("approvals.view", "Approvals: view")
        p_approvals_upload = ensure_perm("approvals.upload", "Approvals: upload")
        p_approvals_download = ensure_perm("approvals.download", "Approvals: download")

        # Customer Profiles (P0)
        p_customers_view = ensure_perm("customers.view", "Customers: view")
        p_customers_create = ensure_perm("customers.create", "Customers: create")
        p_customers_edit = ensure_perm("customers.edit", "Customers: edit")
        p_customers_notes = ensure_perm("customers.notes", "Customers: notes")

        # Sales Dashboard (P1)
        p_sales_view = ensure_perm("sales_dashboard.view", "Sales Dashboard: view")
        p_sales_export = ensure_perm("sales_dashboard.export", "Sales Dashboard: export")

        # Role
        role_admin = s.query(Role).filter(Role.key == "admin").one_or_none()
        if not role_admin:
            role_admin = Role(key="admin", name="Administrator")
            s.add(role_admin)
        if p_admin_view not in role_admin.permissions:
            role_admin.permissions.append(p_admin_view)
        for p in (
            p_docs_view,
            p_docs_create,
            p_docs_edit,
            p_docs_release,
            p_docs_obsolete,
            p_docs_download,
            p_dist_view,
            p_dist_create,
            p_dist_edit,
            p_dist_delete,
            p_dist_import,
            p_dist_export,
            p_tracing_view,
            p_tracing_generate,
            p_tracing_download,
            p_approvals_view,
            p_approvals_upload,
            p_approvals_download,
            p_customers_view,
            p_customers_create,
            p_customers_edit,
            p_customers_notes,
            p_sales_view,
            p_sales_export,
        ):
            if p not in role_admin.permissions:
                role_admin.permissions.append(p)

        # User
        user = s.query(User).filter(User.email == admin_email).one_or_none()
        if not user:
            user = User(email=admin_email, password_hash=generate_password_hash(admin_password), is_active=True)
            s.add(user)
        if role_admin not in user.roles:
            user.roles.append(role_admin)

    print("Initialized database.")
    print(f"Admin email: {admin_email}")
    print("Admin password: (from ADMIN_PASSWORD)")


if __name__ == "__main__":
    main()

