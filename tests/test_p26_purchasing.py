"""Prompt 26 — Purchasing list UX enhancements."""
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.purchasing.models import PurchaseOrder
from app.eqms.modules.suppliers.models import Supplier


def _seed_perms(s, keys):
    return [Permission(key=k, name=k) for k in keys]


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

    admin_keys = ["admin.view", "admin.edit", "purchasing.view", "purchasing.create", "purchasing.edit"]
    staff_keys = ["admin.view", "staff.view", "purchasing.view"]
    all_keys = sorted(set(admin_keys) | set(staff_keys))

    with session_scope(app) as s:
        perms = {p.key: p for p in _seed_perms(s, all_keys)}
        s.add_all(list(perms.values()))

        admin_role = Role(key="admin", name="Administrator")
        for k in admin_keys:
            admin_role.permissions.append(perms[k])
        staff_role = Role(key="staff", name="Staff")
        for k in staff_keys:
            staff_role.permissions.append(perms[k])

        admin_u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        admin_u.roles.append(admin_role)
        staff_u = User(email="staff@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        staff_u.roles.append(staff_role)
        s.add_all([admin_role, staff_role, admin_u, staff_u])

        sup = Supplier(name="Acme Supplies", status="Approved")
        s.add(sup)
        s.flush()

        year = date.today().year
        s.add(PurchaseOrder(po_number="PO-LINK-1", order_date=date(year, 3, 1), status="received", supplier_id=sup.id))
        s.add(PurchaseOrder(
            po_number="PO-UNLINK-1", order_date=date(year, 4, 1), status="pending",
            supplier_id=None, notes="Supplier from PO Log: VendorX",
        ))

    return app.test_client()


def _login(client, email="admin@example.com"):
    client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=True)


def test_list_200_admin_and_staff(client):
    _login(client, "admin@example.com")
    assert client.get("/admin/purchasing").status_code == 200
    client.get("/auth/logout", follow_redirects=True)
    _login(client, "staff@example.com")
    assert client.get("/admin/purchasing").status_code == 200


def test_import_buttons_absent_new_present(client):
    _login(client)
    body = client.get("/admin/purchasing").data.decode()
    assert "New PO" in body
    assert "Import PDF" not in body
    assert "Import PO Log" not in body
    assert "Back to Admin" not in body


def test_summary_cards_present(client):
    _login(client)
    body = client.get("/admin/purchasing").data.decode()
    assert "Open (pending/partial)" in body
    assert "Received (" in body
    assert "Total POs" in body
    assert "Unlinked" in body


def test_year_and_supplier_filters_accepted(client):
    _login(client)
    year = date.today().year
    r = client.get(f"/admin/purchasing?year={year}&supplier_id=1")
    assert r.status_code == 200


def test_unlinked_filter_returns_only_unlinked(client):
    _login(client)
    body = client.get("/admin/purchasing?unlinked=1").data.decode()
    assert "PO-UNLINK-1" in body
    assert "PO-LINK-1" not in body


def test_verified_and_attachments_columns_absent(client):
    _login(client)
    body = client.get("/admin/purchasing").data.decode()
    assert "Verified" not in body
    assert "Attachments" not in body
