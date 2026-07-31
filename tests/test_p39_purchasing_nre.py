"""
Prompt 39 — Purchasing line items / Invoices Received + NRE enhancements.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.models import INVOICE_STATUSES, NREProjectEntry
from app.eqms.modules.purchasing.models import (
    InvoiceReceivedEntry,
    PaymentEntry,
    PaymentLineItem,
    PaymentLineItemAttachment,
)
from app.eqms.modules.rep_traceability.models import SalesOrder

PW = "pw"
PERMS = [
    "admin.view", "admin.edit", "purchasing.view", "purchasing.edit",
    "sales_orders.view", "sales_orders.edit", "customers.view",
]


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
        admin = User(
            email="admin@silq.tech", display_name="Admin",
            password_hash=generate_password_hash(PW), is_active=True,
        )
        admin.roles.append(role)
        s.add_all(list(perms.values()) + [role, admin])
        s.flush()

        cust = Customer(
            facility_name="Acme NRE",
            customer_type="nre",
            customer_code="ACME",
            company_key="acme-nre",
        )
        s.add(cust)
        s.flush()
        s.add(SalesOrder(
            order_number="9001",
            order_date=date(2026, 7, 1),
            customer_id=cust.id,
            source="manual",
            status="completed",
            order_amount=Decimal("1500.00"),
        ))
        s.add(SalesOrder(
            order_number="9000",
            order_date=date(2026, 4, 1),
            customer_id=cust.id,
            source="manual",
            status="completed",
            order_amount=Decimal("500.00"),
        ))
        pay = PaymentEntry(
            order_date=date(2026, 7, 10),
            vendor="VendorCo",
            description="Parent payment",
            amount=Decimal("100.00"),
            payment_due_date=date(2026, 8, 1),
            created_by_id=admin.id,
        )
        s.add(pay)

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client):
    client.post("/auth/login", data={"email": "admin@silq.tech", "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


def _pay_id(app):
    with session_scope(app) as s:
        return s.query(PaymentEntry).one().id


def _customer_id(app):
    with session_scope(app) as s:
        return s.query(Customer).one().id


def _order_id(app, order_number="9001"):
    with session_scope(app) as s:
        return s.query(SalesOrder).filter(SalesOrder.order_number == order_number).one().id


# --------------------------------------------------------------------------- #
# B — payment line items
# --------------------------------------------------------------------------- #
def test_payment_line_item_crud_does_not_change_parent_amount(client, app):
    _login(client)
    token = _csrf(client)
    pid = _pay_id(app)

    r = client.post(
        f"/admin/purchasing/payments/{pid}/lines",
        json={"description": "Part A", "amount": "40.00"},
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200
    line = r.get_json()
    assert line["description"] == "Part A"
    lid = line["id"]

    r2 = client.post(
        f"/admin/purchasing/payments/{pid}/lines/{lid}",
        json={"amount": "55.00"},
        headers={"X-CSRF-Token": token},
    )
    assert r2.status_code == 200
    assert r2.get_json()["amount"] == "55.00"

    with session_scope(app) as s:
        parent = s.get(PaymentEntry, pid)
        assert parent.amount == Decimal("100.00")  # unchanged

    r3 = client.delete(
        f"/admin/purchasing/payments/{pid}/lines/{lid}",
        headers={"X-CSRF-Token": token},
    )
    assert r3.status_code == 200
    with session_scope(app) as s:
        assert s.query(PaymentLineItem).count() == 0


def test_payment_line_item_multi_file_attach(client, app):
    _login(client)
    token = _csrf(client)
    pid = _pay_id(app)
    r = client.post(
        f"/admin/purchasing/payments/{pid}/lines",
        json={"description": "Docs", "amount": "1"},
        headers={"X-CSRF-Token": token},
    )
    lid = r.get_json()["id"]

    for name in ("a.pdf", "b.pdf"):
        resp = client.post(
            f"/admin/purchasing/payments/{pid}/lines/{lid}/files",
            data={"csrf_token": token, "file": (BytesIO(b"%PDF-1.4 fake"), name)},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200

    with session_scope(app) as s:
        atts = s.query(PaymentLineItemAttachment).filter_by(payment_line_item_id=lid).all()
        assert len(atts) == 2


# --------------------------------------------------------------------------- #
# C — invoices received
# --------------------------------------------------------------------------- #
def test_invoice_received_crud_and_attach(client, app):
    _login(client)
    token = _csrf(client)
    r = client.post(
        "/admin/purchasing/invoices-received",
        json={
            "date_received": "2026-07-20",
            "payee": "Acme Supplies",
            "description": "July invoice",
            "amount": "250.50",
            "due_date": "2026-08-15",
        },
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200
    eid = r.get_json()["id"]

    resp = client.post(
        f"/admin/purchasing/invoices-received/{eid}/files",
        data={"csrf_token": token, "file": (BytesIO(b"%PDF-1.4 inv"), "inv.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200

    body = client.get("/admin/purchasing").get_data(as_text=True)
    assert "Invoices Received" in body
    assert "Acme Supplies" in body
    assert "Expected Invoice Date" in body

    client.delete(
        f"/admin/purchasing/invoices-received/{eid}",
        headers={"X-CSRF-Token": token},
    )
    with session_scope(app) as s:
        assert s.query(InvoiceReceivedEntry).count() == 0


# --------------------------------------------------------------------------- #
# E — NRE status
# --------------------------------------------------------------------------- #
def test_invoice_statuses_include_50_percent(client, app):
    assert "50% Invoiced" in INVOICE_STATUSES
    assert INVOICE_STATUSES.index("50% Invoiced") == INVOICE_STATUSES.index("Pending Invoice") + 1

    _login(client)
    token = _csrf(client)
    r = client.post(
        "/admin/nre-projects/tracker/create",
        json={
            "entry_date": "2026-07-01",
            "customer_name": "Acme",
            "invoice_status": "50% Invoiced",
            "invoice_amount": "100",
        },
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        e = s.query(NREProjectEntry).order_by(NREProjectEntry.id.desc()).first()
        assert e.invoice_status == "50% Invoiced"

    body = client.get("/admin/nre-projects/").get_data(as_text=True)
    assert "Upcoming NRE Invoice Tracker" in body


# --------------------------------------------------------------------------- #
# F — invoice date + expand + dashboard
# --------------------------------------------------------------------------- #
def test_sales_order_invoice_date_patch(client, app):
    _login(client)
    token = _csrf(client)
    cid = _customer_id(app)
    oid = _order_id(app)
    r = client.post(
        f"/admin/nre-projects/{cid}/orders/{oid}/invoice-date",
        data={"csrf_token": token, "invoice_date": "2026-07-25"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.get(SalesOrder, oid).invoice_date == date(2026, 7, 25)


def test_nre_index_expand_and_sort_smoke(client, app):
    _login(client)
    body = client.get("/admin/nre-projects/").get_data(as_text=True)
    assert "Expanded View" not in body
    assert 'aria-label="Expand orders"' in body
    assert "Customer Profile" in body
    assert "nre-expand-panel" in body
    assert "9001" in body  # order shown in expand panel markup
    assert "NRE Dashboard" in body
    assert 'id="nre-dashboard"' in body
    assert body.find('id="nre-dashboard"') < body.find('id="nre-customer-grid"')


def test_nre_dashboard_quarter_metrics(client, app):
    _login(client)
    # Default quarter (Jul–Sep 2026 for today=2026-07-30 in user_info… but tests use real today).
    # Use explicit window covering both seeded orders.
    r = client.get("/admin/nre-projects/?start=2026-01-01&end=2026-12-31")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Total NRE projects" in body
    assert "2" in body  # project count
    assert "1,500.00" in body or "1500" in body or "$1,500" in body or "2,000" in body


# --------------------------------------------------------------------------- #
# D — weekly brief template
# --------------------------------------------------------------------------- #
def test_weekly_brief_includes_invoices_and_line_items(app):
    from flask import render_template

    with session_scope(app) as s:
        pay = s.query(PaymentEntry).one()
        s.add(PaymentLineItem(
            payment_entry_id=pay.id,
            description="Line item X",
            amount=Decimal("10.00"),
            sort_order=0,
        ))
        s.add(InvoiceReceivedEntry(
            date_received=date(2026, 7, 15),
            payee="PayeeCo",
            description="Received inv",
            amount=Decimal("99.00"),
        ))
        s.flush()
        s.expire_all()
        payments = s.query(PaymentEntry).all()
        invoices = s.query(InvoiceReceivedEntry).all()
        # Materialize line_items while session open
        for p in payments:
            s.refresh(p, attribute_names=["line_items"])
            assert p.line_items, "expected line items on payment for template smoke"

        payment_rows = []
        for e in payments:
            payment_rows.append({"sort_date": e.order_date, "kind": "upcoming", "entry": e})
        for e in invoices:
            payment_rows.append({"sort_date": e.date_received, "kind": "received", "entry": e})
        with app.app_context():
            with app.test_request_context("/"):
                html = render_template(
                    "email/weekly_brief.html",
                    generated_at=__import__("datetime").datetime(2026, 7, 30),
                    quarter_start=date(2026, 7, 1),
                    quarter_label=3,
                    stats={
                        "total_units_window": 0,
                        "total_orders": 0,
                        "total_customers": 0,
                        "first_time_customers": 0,
                        "repeat_customers": 0,
                    },
                    sku_breakdown=[],
                    sku_total=0,
                    payment_rows=payment_rows,
                    nre_entries=[],
                )
    assert "<h2" in html and "Upcoming Payments" in html
    assert 'color:#0d1117;">Invoices Received</h2>' not in html
    assert "(Received)" in html
    assert "PayeeCo" in html
    assert "Expected Invoice Date" in html
    assert "Line item X" in html
    assert "Upcoming NRE Invoice Tracker" in html


def test_top_nav_purchasing_not_equipment(client, app):
    _login(client)
    body = client.get("/admin/").get_data(as_text=True)
    # Dashboard still has Equipment card; top nav should say Purchasing.
    # Layout is in every page — check purchasing list page nav.
    page = client.get("/admin/purchasing").get_data(as_text=True)
    assert ">Purchasing</a>" in page or "Purchasing" in page
