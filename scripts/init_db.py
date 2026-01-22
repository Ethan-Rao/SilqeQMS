import sys
from pathlib import Path
import os

from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager

# Ensure repo root is on sys.path when running as a script (Windows-friendly).
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.eqms.models import Permission, Role, User


@contextmanager
def _session_scope(database_url: str):
    engine = create_engine(database_url, future=True)
    sm = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    s: Session = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def seed_only(*, database_url: str | None = None) -> None:
    """
    Seed permissions/roles/admin user in an idempotent way.
    Does NOT overwrite an existing admin user's password.
    """
    admin_email = (os.environ.get("ADMIN_EMAIL") or "admin@silqeqms.com").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD") or "change-me"

    db_url = (database_url or os.environ.get("DATABASE_URL") or "sqlite:///eqms.db").strip()

    # Use direct engine/session so this can run in release without importing app.wsgi (avoids recursion).
    with _session_scope(db_url) as s:
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

        # Sales Orders (Source of Truth)
        p_sales_orders_view = ensure_perm("sales_orders.view", "Sales Orders: view")
        p_sales_orders_create = ensure_perm("sales_orders.create", "Sales Orders: create")
        p_sales_orders_edit = ensure_perm("sales_orders.edit", "Sales Orders: edit")
        p_sales_orders_import = ensure_perm("sales_orders.import", "Sales Orders: import PDF")

        # ShipStation Sync (P1, admin-triggered)
        p_shipstation_view = ensure_perm("shipstation.view", "ShipStation: view")
        p_shipstation_run = ensure_perm("shipstation.run", "ShipStation: run sync")

        # Equipment (P0)
        p_equipment_view = ensure_perm("equipment.view", "Equipment: view")
        p_equipment_create = ensure_perm("equipment.create", "Equipment: create")
        p_equipment_edit = ensure_perm("equipment.edit", "Equipment: edit")
        p_equipment_upload = ensure_perm("equipment.upload", "Equipment: upload documents")

        # Suppliers (P0)
        p_suppliers_view = ensure_perm("suppliers.view", "Suppliers: view")
        p_suppliers_create = ensure_perm("suppliers.create", "Suppliers: create")
        p_suppliers_edit = ensure_perm("suppliers.edit", "Suppliers: edit")
        p_suppliers_upload = ensure_perm("suppliers.upload", "Suppliers: upload documents")

        # Manufacturing (P0)
        p_manufacturing_view = ensure_perm("manufacturing.view", "Manufacturing: view")
        p_manufacturing_create = ensure_perm("manufacturing.create", "Manufacturing: create lots")
        p_manufacturing_edit = ensure_perm("manufacturing.edit", "Manufacturing: edit lots")
        p_manufacturing_upload = ensure_perm("manufacturing.upload", "Manufacturing: upload documents")
        p_manufacturing_disposition = ensure_perm("manufacturing.disposition", "Manufacturing: record QA disposition")

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
            p_sales_orders_view,
            p_sales_orders_create,
            p_sales_orders_edit,
            p_sales_orders_import,
            p_shipstation_view,
            p_shipstation_run,
            p_equipment_view,
            p_equipment_create,
            p_equipment_edit,
            p_equipment_upload,
            p_suppliers_view,
            p_suppliers_create,
            p_suppliers_edit,
            p_suppliers_upload,
            p_manufacturing_view,
            p_manufacturing_create,
            p_manufacturing_edit,
            p_manufacturing_upload,
            p_manufacturing_disposition,
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

    print("Initialized database (seed_only).")
    print(f"Admin email: {admin_email}")
    print("Admin password: (from ADMIN_PASSWORD)")


def main() -> None:
    seed_only(database_url=None)


if __name__ == "__main__":
    main()

