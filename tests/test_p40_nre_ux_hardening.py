"""
Prompt 40 — NRE UX polish + P39 hardening (fill-nulls, parser, storage cleanup).
"""
from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.purchasing.models import InvoiceReceivedAttachment, InvoiceReceivedEntry
from app.eqms.modules.rep_traceability.admin import _fill_so_parsed_fields
from app.eqms.modules.rep_traceability.models import SalesOrder
from app.eqms.modules.rep_traceability.parsers.pdf import (
    extract_order_amount,
    extract_po_reference,
)

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
            city="Austin",
            state="TX",
            sold_to_address1="100 Customer Fallback St",
            sold_to_city="Austin",
            sold_to_state="TX",
            sold_to_zip="78701",
            address1="200 Ship Fallback Rd",
        )
        s.add(cust)
        s.flush()
        s.add(SalesOrder(
            order_number="9001",
            order_date=date(2026, 7, 15),
            customer_id=cust.id,
            source="manual",
            status="completed",
            order_amount=Decimal("1500.00"),
            po_reference="PO-KEEP",
            order_description="Keep me",
            sold_to_address1="1 Recent Sold",
            sold_to_city="Dallas",
            sold_to_state="TX",
            sold_to_zip="75201",
            ship_to_name="Receiving Dock",
            ship_to_address1="9 Ship Lane",
            ship_to_city="Dallas",
            ship_to_state="TX",
            ship_to_zip="75202",
        ))
        s.add(SalesOrder(
            order_number="9000",
            order_date=date(2026, 4, 1),
            customer_id=cust.id,
            source="manual",
            status="completed",
            order_amount=Decimal("500.00"),
        ))

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


def _customer_id(app):
    with session_scope(app) as s:
        return s.query(Customer).one().id


# --------------------------------------------------------------------------- #
# A1 — fill-nulls-only
# --------------------------------------------------------------------------- #
def test_fill_so_parsed_fields_does_not_clobber_non_null():
    order = SalesOrder(
        order_number="1",
        order_date=date(2026, 1, 1),
        customer_id=1,
        source="manual",
        status="pending",
        order_amount=Decimal("100.00"),
        po_reference="EXISTING",
        order_description="Old desc",
        sold_to_city="KeepCity",
    )
    _fill_so_parsed_fields(order, {
        "order_amount": Decimal("999.00"),
        "po_reference": "NEW-PO",
        "order_description": "New desc",
        "city": "OverwriteCity",
        "address1": "New Addr",
        "ship_to_city": "ShipCity",
    })
    assert order.order_amount == Decimal("100.00")
    assert order.po_reference == "EXISTING"
    assert order.order_description == "Old desc"
    assert order.sold_to_city == "KeepCity"
    assert order.sold_to_address1 == "New Addr"  # was null → filled
    assert order.ship_to_city == "ShipCity"


def test_fill_so_parsed_fields_fills_nulls():
    order = SalesOrder(
        order_number="2",
        order_date=date(2026, 1, 1),
        customer_id=1,
        source="manual",
        status="pending",
    )
    _fill_so_parsed_fields(order, {
        "order_amount": Decimal("42.50"),
        "po_reference": "PO-42",
        "order_description": "Widget job",
    })
    assert order.order_amount == Decimal("42.50")
    assert order.po_reference == "PO-42"
    assert order.order_description == "Widget job"
    assert getattr(order, "invoice_date", None) is None


# --------------------------------------------------------------------------- #
# A2 — parser fixtures
# --------------------------------------------------------------------------- #
def test_extract_order_amount_cents_and_whole_dollar():
    assert extract_order_amount("Order Total: $1,500.00\nSubtotal $10.00") == Decimal("1500.00")
    assert extract_order_amount("Grand Total $2,000\nTax Total $50.00") == Decimal("2000")
    assert extract_order_amount("Amount Due: 99.99") == Decimal("99.99")


def test_extract_po_reference():
    text = "Customer PO: ABC-12345\nOrder Total: $10.00"
    assert extract_po_reference(text) == "ABC-12345"


# --------------------------------------------------------------------------- #
# B — NRE index UX
# --------------------------------------------------------------------------- #
def test_nre_index_dashboard_before_cards_and_project_rows(client, app):
    _login(client)
    body = client.get("/admin/nre-projects/?start=2026-07-01&end=2026-07-31").get_data(as_text=True)
    dash_pos = body.find('id="nre-dashboard"')
    grid_pos = body.find('id="nre-customer-grid"')
    assert dash_pos != -1 and grid_pos != -1
    assert dash_pos < grid_pos
    assert "9001" in body
    assert "Expanded View" not in body
    assert 'aria-label="Expand orders"' in body
    assert "↓" in body
    # Slim cards: code/city not in card body (ACME / Austin still ok on profile only).
    # Card section should not show customer code badge or city line near expand control.
    card_chunk = body[grid_pos:grid_pos + 2500]
    assert "ACME" not in card_chunk
    assert "Austin, TX" not in card_chunk
    assert "Customer Profile" in card_chunk
    assert "nre-dash-projects" in body
    assert "Acme NRE" in body


def test_nre_index_filter_excludes_out_of_range(client, app):
    _login(client)
    body = client.get("/admin/nre-projects/?start=2026-07-01&end=2026-07-31").get_data(as_text=True)
    # 9001 in July window; 9000 (April) should not appear in dashboard table rows
    # (may still appear in expand panels). Check dash table section.
    start = body.find('id="nre-dash-projects"')
    end = body.find('id="nre-customer-grid"')
    dash_table = body[start:end]
    assert "9001" in dash_table
    assert "9000" not in dash_table


# --------------------------------------------------------------------------- #
# C — contacts + addresses
# --------------------------------------------------------------------------- #
def test_edit_customer_persists_contacts(client, app):
    _login(client)
    token = _csrf(client)
    cid = _customer_id(app)
    r = client.post(
        f"/admin/nre-projects/{cid}/edit",
        data={
            "csrf_token": token,
            "facility_name": "Acme NRE",
            "customer_code": "ACME",
            "customer_type": "nre",
            "contact_name": "Jane Doe",
            "contact_email": "jane@acme.example",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        c = s.get(Customer, cid)
        assert c.contact_name == "Jane Doe"
        assert c.contact_email == "jane@acme.example"
    page = client.get(f"/admin/nre-projects/{cid}").get_data(as_text=True)
    assert "Jane Doe" in page
    assert "jane@acme.example" in page
    assert "Sold To" in page
    assert "1 Recent Sold" in page
    assert "Ship To" in page
    assert "9 Ship Lane" in page
    assert "Receiving Dock" in page


# --------------------------------------------------------------------------- #
# A3 — invoice delete cleans storage
# --------------------------------------------------------------------------- #
def test_invoice_received_delete_calls_storage_delete(client, app):
    _login(client)
    token = _csrf(client)
    with session_scope(app) as s:
        entry = InvoiceReceivedEntry(
            date_received=date(2026, 7, 20),
            payee="PayeeCo",
            description="Inv",
            amount=Decimal("10.00"),
        )
        s.add(entry)
        s.flush()
        s.add(InvoiceReceivedAttachment(
            invoice_received_entry_id=entry.id,
            filename="inv.pdf",
            storage_key="purchasing/invoice_received_files/1/inv.pdf",
            content_type="application/pdf",
            size_bytes=12,
        ))
        eid = entry.id

    mock_storage = MagicMock()
    with patch("app.eqms.modules.purchasing.admin.storage_from_config", return_value=mock_storage):
        r = client.delete(
            f"/admin/purchasing/invoices-received/{eid}",
            headers={"X-CSRF-Token": token},
        )
    assert r.status_code == 200
    mock_storage.delete.assert_called()
    with session_scope(app) as s:
        assert s.query(InvoiceReceivedEntry).count() == 0
