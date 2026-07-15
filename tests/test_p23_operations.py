"""
Prompt 23 — Operations column accordion + dashboard restructure.

Covers:
- Task A: work_orders / employee_training / ncrs render as accordion trees.
- Task B: Operations column reordered, Work Orders card added, My Training +
  Training Assignments consolidated into a single Training card whose link
  depends on permissions.
- Task C: a library with exactly one root folder and no root files auto-opens
  that root <details>.
- Task D: employee_training accordion shows the "search by person" hint.
"""
import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder


ADMIN_PERMS = ["admin.view", "admin.edit", "staff.view", "docs.view", "docs.download",
               "training.view", "training.manage"]
# In production staff hold admin.view (read the admin shell) but not admin.edit.
STAFF_PERMS = ["admin.view", "staff.view", "docs.view", "docs.download", "training.view"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    engine = application.extensions["sqlalchemy_engine"]
    tables = [
        Base.metadata.tables[t]
        for t in (
            "users", "roles", "permissions", "user_roles", "role_permissions",
            "audit_events", "admin_doc_folders", "admin_doc_files", "training_assignments",
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        all_keys = sorted(set(ADMIN_PERMS + STAFF_PERMS))
        perms = {k: Permission(key=k, name=k) for k in all_keys}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms[k] for k in ADMIN_PERMS)
        staff_role = Role(key="staff", name="Staff")
        staff_role.permissions.extend(perms[k] for k in STAFF_PERMS)
        admin_user = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        admin_user.roles.append(admin_role)
        staff_user = User(email="staff@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        staff_user.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin_user, staff_user])
        s.flush()
        oid = admin_user.id

        # work_orders: single root folder + nested child, no root-level files (Task C).
        wo_root = AdminDocFolder(library_key="work_orders", name="Work Orders", created_by_user_id=oid)
        s.add(wo_root)
        s.flush()
        wo_child = AdminDocFolder(library_key="work_orders", name="ClearTract Foley Catheters",
                                  parent_id=wo_root.id, created_by_user_id=oid)
        s.add(wo_child)
        s.flush()
        s.add(AdminDocFile(library_key="work_orders", folder_id=wo_child.id, filename="WO-100.pdf",
                           storage_key="wo-1", content_type="application/pdf", size_bytes=1, uploaded_by_user_id=oid))

        # employee_training: per-person folders.
        et = AdminDocFolder(library_key="employee_training", name="Jane Doe", created_by_user_id=oid)
        s.add(et)
        s.flush()
        s.add(AdminDocFile(library_key="employee_training", folder_id=et.id, filename="Jane cert.pdf",
                           storage_key="et-1", content_type="application/pdf", size_bytes=1, uploaded_by_user_id=oid))

        # ncrs: root folder + year subfolder.
        ncr = AdminDocFolder(library_key="ncrs", name="NCRs", created_by_user_id=oid)
        s.add(ncr)
        s.flush()
        s.add(AdminDocFolder(library_key="ncrs", name="2025", parent_id=ncr.id, created_by_user_id=oid))

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@example.com"):
    r = client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=False)
    assert r.status_code in (302, 303)


def _url(app, endpoint, **kw):
    with app.test_request_context():
        from flask import url_for
        return url_for(endpoint, **kw)


# ── Task A: accordion for three Operations libraries ────────────────────────

@pytest.mark.parametrize("endpoint", ["admin_docs.work_orders", "admin_docs.employee_training", "admin_docs.ncrs"])
def test_operations_libraries_render_accordion(client, app, endpoint):
    url = _url(app, endpoint)
    _login(client, "admin@example.com")
    r = client.get(url)
    assert r.status_code == 200
    assert "<details" in r.get_data(as_text=True)
    client.get("/auth/logout")
    _login(client, "staff@example.com")
    r = client.get(url)
    assert r.status_code == 200
    assert "<details" in r.get_data(as_text=True)


# ── Task C: work_orders single root folder auto-opens ───────────────────────

def test_work_orders_root_folder_auto_opens(client, app):
    _login(client)
    body = client.get(_url(app, "admin_docs.work_orders")).get_data(as_text=True)
    assert 'accordion-folder" open' in body


# ── Task D: employee_training search hint ───────────────────────────────────

def test_employee_training_shows_search_hint(client, app):
    _login(client)
    body = client.get(_url(app, "admin_docs.employee_training")).get_data(as_text=True)
    assert "Search by employee name" in body


# ── Task B: dashboard Operations column ─────────────────────────────────────

def test_dashboard_has_work_orders_card(client, app):
    _login(client)
    body = client.get(_url(app, "admin.index")).get_data(as_text=True)
    assert "Work Orders" in body


def test_dashboard_consolidates_training_cards(client, app):
    _login(client)
    body = client.get(_url(app, "admin.index")).get_data(as_text=True)
    assert "My Training" not in body
    assert "Training Assignments" not in body
    assert ">Training</h3>" in body


def test_dashboard_training_card_link_admin_vs_staff(client, app):
    manage_url = _url(app, "training.manage_index")
    my_url = _url(app, "training.my_training")

    _login(client, "admin@example.com")
    admin_body = client.get(_url(app, "admin.index")).get_data(as_text=True)
    assert f'href="{manage_url}"' in admin_body
    client.get("/auth/logout")

    _login(client, "staff@example.com")
    staff_body = client.get(_url(app, "admin.index")).get_data(as_text=True)
    assert f'href="{my_url}"' in staff_body


def test_dashboard_work_orders_before_ncrs(client, app):
    _login(client)
    body = client.get(_url(app, "admin.index")).get_data(as_text=True)
    assert body.index("Work Orders") < body.index("NCRs")
