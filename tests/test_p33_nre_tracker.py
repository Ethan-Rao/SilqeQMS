"""
Prompt 33 — NRE Invoice Tracker (free-form ledger) + per-order document subfolders.

Covers:
- NREProjectEntry now supports free-form entries (sales_order_id nullable + new columns).
- POST /tracker/create builds a free-form ledger entry (JSON) with all new fields.
- PATCH /tracker/<id> persists the new fields (entry_date/customer_name/order_ref/description).
- DELETE /tracker/<id> removes an entry.
- Index page renders the "NRE Invoice Tracker" card, entries, and empty state.
- Detail Sales Orders section renders "📁 Documents" link once folders are scaffolded.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.models import NREProjectEntry
from app.eqms.modules.rep_traceability.models import SalesOrder

PW = "pw"
PERMS = ["admin.view", "admin.edit", "sales_orders.view", "sales_orders.edit"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        perms = {k: Permission(key=k, name=k) for k in PERMS}
        role = Role(key="admin", name="Administrator")
        role.permissions.extend(perms.values())
        admin = User(email="admin@example.com", password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(role)
        s.add_all(list(perms.values()) + [role, admin])
        s.flush()

        c = Customer(company_key="scionti", facility_name="Scionti Prostate Center", customer_type="nre")
        s.add(c)
        s.flush()
        o = SalesOrder(order_number="0000202", order_date=dt.date(2026, 1, 1), customer_id=c.id,
                       source="pdf_import", external_key="pdf:0000202", status="pending")
        s.add(o)

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client):
    client.post("/auth/login", data={"email": "admin@example.com", "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


# --------------------------------------------------------------------------- #
# Model: free-form entry
# --------------------------------------------------------------------------- #
def test_freeform_entry_roundtrip(app):
    with session_scope(app) as s:
        e = NREProjectEntry(
            sales_order_id=None,
            entry_date=dt.date(2026, 7, 15),
            customer_name="Acme Labs",
            order_ref="PO-42",
            description="Prototype tooling",
            invoice_status="Pending Invoice",
        )
        s.add(e)
        s.flush()
        eid = e.id
    with session_scope(app) as s:
        e = s.get(NREProjectEntry, eid)
        assert e.sales_order_id is None
        assert e.customer_name == "Acme Labs"
        assert e.order_ref == "PO-42"
        assert e.description == "Prototype tooling"
        assert e.entry_date == dt.date(2026, 7, 15)


# --------------------------------------------------------------------------- #
# Ledger CRUD
# --------------------------------------------------------------------------- #
def test_tracker_create_freeform(client, app):
    _login(client)
    token = _csrf(client)
    r = client.post(
        "/admin/nre-projects/tracker/create",
        json={
            "entry_date": "2026-07-15", "customer_name": "Fearsome Limited",
            "order_ref": "SO-0000289", "description": "NRE milestone 1",
            "invoice_amount": "3,400.00", "expected_invoice_date": "2026-08-01",
            "invoice_status": "Invoiced", "notes": "half now",
        },
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] and data["entry"]["id"]
    assert data["entry"]["customer_name"] == "Fearsome Limited"
    assert data["entry"]["order_ref"] == "SO-0000289"
    assert data["entry"]["invoice_status"] == "Invoiced"
    eid = data["entry"]["id"]
    with session_scope(app) as s:
        e = s.get(NREProjectEntry, eid)
        assert e.sales_order_id is None
        assert str(e.invoice_amount) == "3400.00"
        assert e.entry_date == dt.date(2026, 7, 15)


def test_tracker_patch_new_fields(client, app):
    _login(client)
    token = _csrf(client)
    r = client.post("/admin/nre-projects/tracker/create",
                    json={"customer_name": "Neptune"}, headers={"X-CSRF-Token": token})
    eid = r.get_json()["entry"]["id"]

    r = client.patch(f"/admin/nre-projects/tracker/{eid}",
                     json={"customer_name": "Neptune Systems", "order_ref": "SO-0000294",
                           "description": "revised scope", "invoice_status": "Paid"},
                     headers={"X-CSRF-Token": token})
    assert r.status_code == 200 and r.get_json()["ok"]
    with session_scope(app) as s:
        e = s.get(NREProjectEntry, eid)
        assert e.customer_name == "Neptune Systems"
        assert e.order_ref == "SO-0000294"
        assert e.description == "revised scope"
        assert e.invoice_status == "Paid"


def test_tracker_delete(client, app):
    _login(client)
    token = _csrf(client)
    r = client.post("/admin/nre-projects/tracker/create",
                    json={"customer_name": "Momentum LLC"}, headers={"X-CSRF-Token": token})
    eid = r.get_json()["entry"]["id"]
    r = client.delete(f"/admin/nre-projects/tracker/{eid}", headers={"X-CSRF-Token": token})
    assert r.status_code == 200 and r.get_json()["ok"]
    with session_scope(app) as s:
        assert s.get(NREProjectEntry, eid) is None


# --------------------------------------------------------------------------- #
# Index page rendering
# --------------------------------------------------------------------------- #
def test_index_shows_tracker_card_and_empty_state(client):
    _login(client)
    body = client.get("/admin/nre-projects/").data.decode()
    assert "NRE Invoice Tracker" in body
    assert "No invoice entries yet." in body
    assert "+ Add Entry" in body


def test_index_lists_created_entry(client, app):
    _login(client)
    token = _csrf(client)
    client.post("/admin/nre-projects/tracker/create",
                json={"customer_name": "Hybron Technologies", "order_ref": "SO-0000274"},
                headers={"X-CSRF-Token": token})
    body = client.get("/admin/nre-projects/").data.decode()
    assert "Hybron Technologies" in body
    assert "SO-0000274" in body


# --------------------------------------------------------------------------- #
# Detail Sales Orders section documents link
# --------------------------------------------------------------------------- #
def test_detail_documents_link_after_scaffold(client, app):
    with session_scope(app) as s:
        cid = s.query(Customer).filter_by(company_key="scionti").one().id
    _login(client)
    # Before scaffold: muted hint
    body = client.get(f"/admin/nre-projects/{cid}").data.decode()
    assert "Run Refresh Folders to create." in body
    # Scaffold folders, then Documents link appears in Sales Orders section
    client.post("/admin/nre-projects/refresh-folders", data={"csrf_token": _csrf(client)})
    body = client.get(f"/admin/nre-projects/{cid}").data.decode()
    assert "📁 Documents" in body
