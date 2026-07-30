"""Prompt 27 — Purchasing redesign (payments ledger, open/closed, $ formatting)."""
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.purchasing.models import (
    PurchaseOrder,
    PurchaseOrderAttachment,
)
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

    admin_keys = ["admin.view", "admin.edit", "purchasing.view", "purchasing.create", "purchasing.edit", "purchasing.upload"]
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
        s.flush()

        sup = Supplier(name="Acme Supplies", status="Approved")
        s.add(sup)
        s.flush()

        year = date.today().year
        linked = PurchaseOrder(po_number="PO-LINK-1", order_date=date(year, 3, 1), status="received", supplier_id=sup.id, amount="3871.36")
        unlinked = PurchaseOrder(
            po_number="PO-UNLINK-1", order_date=date(year, 4, 1), status="pending",
            supplier_id=None, notes="Supplier from PO Log: VendorX",
        )
        s.add_all([linked, unlinked])
        s.flush()

        s.add(PurchaseOrderAttachment(
            purchase_order_id=linked.id, attachment_type="po_pdf",
            storage_key="fake/key.pdf", filename="quote.pdf",
            content_type="application/pdf", size_bytes=10,
            uploaded_by_user_id=admin_u.id,
        ))
        # Stash the linked PO id for the detail test.
        app.config["_LINKED_PO_ID"] = linked.id

    return app.test_client()


def _login(client, email="admin@example.com"):
    client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=True)


def test_list_200_admin_and_staff(client):
    _login(client, "admin@example.com")
    assert client.get("/admin/purchasing").status_code == 200
    client.get("/auth/logout", follow_redirects=True)
    _login(client, "staff@example.com")
    assert client.get("/admin/purchasing").status_code == 200


def test_upcoming_payments_section_present(client):
    _login(client)
    body = client.get("/admin/purchasing").data.decode()
    assert "Upcoming Payments" in body


def test_add_payment_button_admin_only(client):
    _login(client, "admin@example.com")
    assert "+ Add Payment" in client.get("/admin/purchasing").data.decode()
    client.get("/auth/logout", follow_redirects=True)
    _login(client, "staff@example.com")
    assert "+ Add Payment" not in client.get("/admin/purchasing").data.decode()


def test_unlinked_tag_absent_vendor_shown(client):
    _login(client)
    body = client.get("/admin/purchasing").data.decode()
    assert "(unlinked)" not in body
    assert "VendorX" in body


def test_amount_dollar_formatted(client):
    _login(client)
    body = client.get("/admin/purchasing").data.decode()
    assert "$3,871.36" in body


def test_status_badge_open_closed(client):
    _login(client)
    body = client.get("/admin/purchasing").data.decode()
    assert "Open" in body
    assert "Closed" in body
    # Granular DB status values should not surface as badge/label text on the list.
    # P39 adds "Invoices Received" / "Date Received" copy — strip those before checking.
    scrubbed = (
        body.replace("Invoices Received", "")
        .replace("Date Received", "")
        .replace("No invoices received yet.", "")
    )
    assert "Pending" not in scrubbed
    assert "Received" not in scrubbed


def test_year_supplier_dropdowns_absent(client):
    _login(client)
    body = client.get("/admin/purchasing").data.decode()
    assert 'name="year"' not in body
    assert 'name="supplier_id"' not in body


def test_detail_documents_panel_present(client, monkeypatch):
    _login(client)
    app = client.application
    po_id = app.config["_LINKED_PO_ID"]
    body = client.get(f"/admin/purchasing/{po_id}").data.decode()
    assert "Documents" in body
    assert "<details" in body
    assert "quote.pdf" in body


def test_payment_create_and_delete(client):
    _login(client)
    # Create a payment entry via JSON.
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
    r = client.post(
        "/admin/purchasing/payments",
        json={"vendor": "Test Vendor", "amount": "$1,234.50", "csrf_token": token},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["vendor"] == "Test Vendor"
    assert data["amount"] == "1234.50"
    entry_id = data["id"]
    # Delete it.
    r = client.delete(f"/admin/purchasing/payments/{entry_id}", headers={"X-CSRF-Token": token})
    assert r.status_code == 200
