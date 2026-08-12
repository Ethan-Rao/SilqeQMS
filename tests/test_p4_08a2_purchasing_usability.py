"""
P4-08A2 — Purchasing usability: density, free-text supplier, verification files, brief customers.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

import pytest
from flask import render_template
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.purchasing.models import (
    InvoiceReceivedEntry,
    PaymentEntry,
    PaymentLineItem,
    PurchaseOrder,
    PurchaseOrderAttachment,
)
from app.eqms.modules.purchasing.service import (
    build_weekly_brief_payment_rows,
    mark_invoice_paid,
)
from app.eqms.modules.rep_traceability.models import DistributionLogEntry
from app.eqms.modules.rep_traceability.service import recent_customers_for_weekly_brief
from app.eqms.modules.suppliers.models import Supplier

PW = "pw"
PERMS = [
    "admin.view",
    "admin.edit",
    "purchasing.view",
    "purchasing.edit",
    "purchasing.create",
    "purchasing.upload",
]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path / "storage"))
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
            email="admin@silq.tech",
            display_name="Admin",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        admin.roles.append(role)
        s.add_all(list(perms.values()) + [role, admin])

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


def _user(s) -> User:
    return s.query(User).filter_by(email="admin@silq.tech").one()


def _dist(s, *, ship_date, order_number, facility_name, quantity, customer_id=None):
    e = DistributionLogEntry(
        ship_date=ship_date,
        order_number=order_number,
        facility_name=facility_name,
        sku="211610SPT",
        lot_number="LOT-1",
        quantity=quantity,
        source="manual",
        customer_id=customer_id,
    )
    s.add(e)
    return e


def test_upcoming_empty_lines_no_summary_row(app, client):
    with session_scope(app) as s:
        s.add(PaymentEntry(vendor="Steris", description="Service", amount=Decimal("10.00")))
    _login(client)
    html = client.get("/admin/purchasing").get_data(as_text=True)
    upcoming = html.split("Upcoming Payments")[1].split("Invoices Received")[0]
    assert "No line items" not in upcoming
    assert "pay-lines-summary" not in upcoming
    assert "Line items (0)" not in upcoming
    assert "Lines (0)" not in upcoming


def test_upcoming_with_lines_shows_descriptions(app, client):
    with session_scope(app) as s:
        pay = PaymentEntry(vendor="Pathway", description="Monthly", amount=Decimal("18966.95"))
        s.add(pay)
        s.flush()
        s.add(PaymentLineItem(payment_entry_id=pay.id, description="July invoice", amount=Decimal("18966.95")))
    _login(client)
    html = client.get("/admin/purchasing").get_data(as_text=True)
    assert "July invoice" in html
    assert "pay-lines-summary" in html
    assert "Lines (1)" in html


def test_po_select_includes_amount_no_max_width(app, client):
    with session_scope(app) as s:
        s.add(
            PurchaseOrder(
                po_number="0000500",
                order_date=date(2026, 7, 15),
                status="pending",
                amount="999.50",
            )
        )
        s.add(
            InvoiceReceivedEntry(
                payee="A",
                description="B",
                amount=Decimal("1.00"),
                date_received=date(2026, 8, 1),
                disposition=InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
            )
        )
    _login(client)
    html = client.get("/admin/purchasing").get_data(as_text=True)
    received = html.split("Invoices Received")[1].split("Purchase Orders")[0]
    assert "$999.50" in received
    assert "max-width:150px" not in received


def test_mark_paid_button_and_routing(app, client):
    with session_scope(app) as s:
        inv = InvoiceReceivedEntry(
            payee="Min",
            description="Period",
            amount=Decimal("50.00"),
            date_received=date(2026, 8, 1),
            disposition=InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
        )
        s.add(inv)
        s.flush()
        iid = inv.id
    _login(client)
    html = client.get("/admin/purchasing").get_data(as_text=True)
    received = html.split("Invoices Received")[1].split("Purchase Orders")[0]
    assert "Mark paid" in received
    assert 'class="button button--small"' in received
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/mark-paid",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    html = client.get("/admin/purchasing").get_data(as_text=True)
    received = html.split("Invoices Received")[1].split("Purchase Orders")[0]
    assert "Min" not in received or "Period" not in received
    other = html.split("Other Payments")[1]
    assert "Min" in other
    assert "(Paid)" in other


def test_typed_supplier_name_does_not_create_supplier(app, client):
    before = 0
    with session_scope(app) as s:
        before = s.query(Supplier).count()
    _login(client)
    token = _csrf(client)
    r = client.post(
        "/admin/purchasing/new",
        data={
            "csrf_token": token,
            "po_number": "0000179",
            "order_date": "2026-08-01",
            "status": "pending",
            "supplier_id": "",
            "supplier_name": "university",
            "amount": "100.00",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000179").one()
        assert po.supplier_id is None
        assert po.supplier_name == "university"
        assert s.query(Supplier).count() == before


def test_selected_supplier_ignores_typed_name(app, client):
    with session_scope(app) as s:
        sup = Supplier(name="Approved Co")
        s.add(sup)
        s.flush()
        sid = sup.id
    _login(client)
    token = _csrf(client)
    client.post(
        "/admin/purchasing/new",
        data={
            "csrf_token": token,
            "po_number": "0000180",
            "order_date": "2026-08-01",
            "status": "pending",
            "supplier_id": str(sid),
            "supplier_name": "university",
        },
        follow_redirects=True,
    )
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000180").one()
        assert po.supplier_id == sid
        assert po.supplier_name is None
        assert s.query(Supplier).filter_by(name="university").count() == 0


def test_new_po_with_verification_file(app, client):
    _login(client)
    token = _csrf(client)
    r = client.post(
        "/admin/purchasing/new",
        data={
            "csrf_token": token,
            "po_number": "0000181",
            "order_date": "2026-08-01",
            "status": "pending",
            "attachment_type": "verification_evidence",
            "file": (BytesIO(b"%PDF-1.4 evidence"), "coa.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000181").one()
        assert len(po.attachments) == 1
        assert po.attachments[0].attachment_type == "verification_evidence"
        assert po.attachments[0].filename == "coa.pdf"


def test_weekly_brief_five_customers_latest_order_units(app):
    with session_scope(app) as s:
        customers = []
        for i in range(5):
            c = Customer(
                facility_name=f"Hospital {i}",
                company_key=f"hospital-{i}",
                customer_type="catheter",
            )
            s.add(c)
            s.flush()
            customers.append(c)
        # Customer 0: two orders; later order has fewer units.
        _dist(s, ship_date=date(2026, 1, 1), order_number="SO-OLD", facility_name="Hospital 0", quantity=10, customer_id=customers[0].id)
        _dist(s, ship_date=date(2026, 6, 1), order_number="SO-NEW", facility_name="Hospital 0", quantity=3, customer_id=customers[0].id)
        for i in range(1, 5):
            _dist(
                s,
                ship_date=date(2026, 5, i),
                order_number=f"SO-{i}",
                facility_name=f"Hospital {i}",
                quantity=7 + i,
                customer_id=customers[i].id,
            )
        s.flush()
        rows = recent_customers_for_weekly_brief(s, limit=5)
        assert len(rows) == 5
        names = [r["name"] for r in rows]
        assert names.count("Hospital 0") == 1
        h0 = next(r for r in rows if r["name"] == "Hospital 0")
        assert h0["units"] == 3
        assert h0["order_date"] == date(2026, 6, 1)

        with app.app_context():
            with app.test_request_context("/"):
                html = render_template(
                    "email/weekly_brief.html",
                    generated_at=datetime(2026, 8, 12),
                    quarter_start=date(2026, 7, 1),
                    quarter_label=3,
                    stats={
                        "total_units_window": 0,
                        "total_orders": 0,
                        "total_customers": 0,
                        "first_time_customers": 0,
                        "repeat_customers": 0,
                    },
                    recent_customers=rows,
                    payment_rows=[],
                    nre_entries=[],
                )
        assert ">SKU<" not in html
        assert "% of Total" not in html
        assert html.count("<tr>") >= 6  # header + 5
        assert html.count("Hospital 0") == 1
        assert ">3<" in html or ">3</td>" in html


def test_paid_invoice_absent_from_brief_rows(app):
    with session_scope(app) as s:
        inv = InvoiceReceivedEntry(
            payee="PaidCo",
            description="Done",
            amount=Decimal("9.00"),
            date_received=date(2026, 8, 1),
            disposition=InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
        )
        s.add(inv)
        s.flush()
        mark_invoice_paid(s, invoice=inv, user=_user(s))
        s.flush()
        rows = build_weekly_brief_payment_rows(s)
        assert not any(getattr(r["entry"], "payee", None) == "PaidCo" for r in rows)
        with app.app_context():
            with app.test_request_context("/"):
                html = render_template(
                    "email/weekly_brief.html",
                    generated_at=datetime(2026, 8, 12),
                    quarter_start=date(2026, 7, 1),
                    quarter_label=3,
                    stats={
                        "total_units_window": 0,
                        "total_orders": 0,
                        "total_customers": 0,
                        "first_time_customers": 0,
                        "repeat_customers": 0,
                    },
                    recent_customers=[],
                    payment_rows=rows,
                    nre_entries=[],
                )
        assert "PaidCo" not in html


def test_parse_check_not_in_po_toolbar(app, client):
    _login(client)
    html = client.get("/admin/purchasing").get_data(as_text=True)
    po_block = html.split("Purchase Orders")[1].split("Other Payments")[0]
    toolbar = po_block.split("<form")[0]
    assert "New PO" in toolbar
    assert "PDF parse check" not in toolbar
    assert "PDF text dump" not in toolbar
    assert "PDF parse check" in html
    assert "PDF text dump" in html
