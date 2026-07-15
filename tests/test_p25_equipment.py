"""Prompt 25 — Equipment list UX enhancements."""
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.equipment.models import Equipment


def _seed_perms(s, keys):
    perms = []
    for key in keys:
        p = Permission(key=key, name=key)
        s.add(p)
        perms.append(p)
    return perms


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    app = create_app()
    engine = app.extensions["sqlalchemy_engine"]
    Base.metadata.create_all(bind=engine)
    app.config["_schema_health_ok"] = True

    admin_keys = ["admin.view", "admin.edit", "equipment.view", "equipment.create", "equipment.edit", "equipment.upload"]
    staff_keys = ["admin.view", "staff.view", "equipment.view"]
    all_keys = sorted(set(admin_keys) | set(staff_keys))

    with session_scope(app) as s:
        perms = {p.key: p for p in _seed_perms(s, all_keys)}

        admin_role = Role(key="admin", name="Administrator")
        for key in admin_keys:
            admin_role.permissions.append(perms[key])

        staff_role = Role(key="staff", name="Staff")
        for key in staff_keys:
            staff_role.permissions.append(perms[key])

        admin_u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        admin_u.roles.append(admin_role)
        staff_u = User(email="staff@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        staff_u.roles.append(staff_role)
        s.add_all([admin_role, staff_role, admin_u, staff_u])

        # An active equipment item with an overdue calibration.
        overdue = date.today() - timedelta(days=30)
        s.add(Equipment(
            equip_code="ST-OVR",
            status="Active",
            description="Overdue calibration scale",
            cal_interval_text="Annual",
            cal_due_date=overdue,
        ))

    return app.test_client()


def _login(client, email="admin@example.com"):
    client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=True)


def test_list_200_admin_and_staff(client):
    _login(client, "admin@example.com")
    assert client.get("/admin/equipment").status_code == 200
    client.get("/auth/logout", follow_redirects=True)
    _login(client, "staff@example.com")
    assert client.get("/admin/equipment").status_code == 200


def test_combined_service_status_column(client):
    _login(client)
    r = client.get("/admin/equipment")
    body = r.data.decode()
    assert "Service Status" in body
    assert "CAL Status" not in body
    assert "PM Status" not in body


def test_docs_and_suppliers_columns_removed(client):
    _login(client)
    body = client.get("/admin/equipment").data.decode()
    assert "#Docs" not in body
    assert "#Suppliers" not in body


def test_summary_card_lists_overdue_item(client):
    _login(client)
    body = client.get("/admin/equipment").data.decode()
    # The overdue item code should appear in the status card detail list.
    assert "ST-OVR" in body


def test_new_button_present_import_master_absent(client):
    _login(client)
    body = client.get("/admin/equipment").data.decode()
    assert "New Equipment" in body
    assert "Import Master List" not in body
    assert "Bulk Import" not in body
    assert "Cal/PM Schedule" not in body


def test_service_overdue_filter_returns_overdue(client):
    _login(client)
    r = client.get("/admin/equipment?service_overdue=1")
    assert r.status_code == 200
    assert "ST-OVR" in r.data.decode()
