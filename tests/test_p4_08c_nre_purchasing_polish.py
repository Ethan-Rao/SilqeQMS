"""P4-08C — NRE remaining-to-invoice, catheter classify, purchasing/NRE scan."""
from datetime import date
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.models import nre_remaining_to_invoice
from app.eqms.modules.nre_projects.service import compute_nre_dashboard
from app.eqms.modules.purchasing.models import InvoiceReceivedEntry, PaymentEntry, PurchaseOrder
from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
from app.eqms.modules.rep_traceability.order_type import (
    ORDER_TYPE_CLEARTRACT_IN_PROCESS,
    ORDER_TYPE_NRE_PROJECT,
    classify_order_type,
)
from app.eqms.modules.rep_traceability.service import sales_order_has_catheter_sku
from app.eqms.modules.suppliers.models import Supplier

PW = "pw"
PERMS = [
    "admin.view",
    "admin.edit",
    "sales_orders.view",
    "sales_orders.edit",
    "customers.view",
    "purchasing.view",
    "purchasing.edit",
    "purchasing.create",
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


def test_nre_remaining_to_invoice_math():
    assert nre_remaining_to_invoice("50% Invoiced", Decimal("7590")) == Decimal("3795.00")
    assert nre_remaining_to_invoice("Pending Invoice", Decimal("7590")) == Decimal("7590.00")
    assert nre_remaining_to_invoice("100% Invoiced", Decimal("7590")) == Decimal("0.00")
    assert nre_remaining_to_invoice("Payment Received", Decimal("7590")) == Decimal("0.00")
    assert nre_remaining_to_invoice(None, Decimal("7590")) == Decimal("7590.00")
    assert nre_remaining_to_invoice("", Decimal("100")) == Decimal("100.00")


def test_compute_nre_dashboard_still_to_invoice(app):
    today = date.today()
    with session_scope(app) as s:
        cust = Customer(facility_name="Abryx", customer_type="nre", company_key="abryx-08c")
        s.add(cust)
        s.flush()
        s.add(
            SalesOrder(
                order_number="0000385",
                order_date=today,
                customer_id=cust.id,
                source="manual",
                status="completed",
                order_amount=Decimal("7590.00"),
                nre_invoice_status="50% Invoiced",
                order_type=ORDER_TYPE_NRE_PROJECT,
            )
        )
        s.add(
            SalesOrder(
                order_number="0000399",
                order_date=today,
                customer_id=cust.id,
                source="manual",
                status="completed",
                order_amount=Decimal("1000.00"),
                nre_invoice_status="Pending Invoice",
                order_type=ORDER_TYPE_NRE_PROJECT,
            )
        )
        s.flush()
        dash = compute_nre_dashboard(s, start_date=today, end_date=today)
        expected = nre_remaining_to_invoice("50% Invoiced", Decimal("7590")) + nre_remaining_to_invoice(
            "Pending Invoice", Decimal("1000")
        )
        assert dash["still_to_invoice"] == expected
        assert expected == Decimal("4795.00")


def test_nre_index_still_to_invoice_and_no_subtitle(app, client):
    today = date.today()
    with session_scope(app) as s:
        cust = Customer(facility_name="Abryx Co", customer_type="nre", company_key="abryx-08c-html")
        s.add(cust)
        s.flush()
        s.add(
            SalesOrder(
                order_number="0000385",
                order_date=today,
                customer_id=cust.id,
                source="manual",
                status="completed",
                order_amount=Decimal("7590.00"),
                nre_invoice_status="50% Invoiced",
                order_type=ORDER_TYPE_NRE_PROJECT,
            )
        )
    _login(client)
    html = client.get("/admin/nre-projects/").get_data(as_text=True)
    assert "Still to invoice" in html
    assert "$3,795.00" in html
    assert "NRE projects and engineering engagements." not in html


def test_catheter_sku_seen_after_stale_empty_lines(app):
    with app.app_context():
        with session_scope(app) as s:
            cust = Customer(facility_name="UCSD", customer_type="catheter", company_key="ucsd-08c")
            s.add(cust)
            s.flush()
            so = SalesOrder(
                order_number="0000383",
                order_date=date(2026, 8, 11),
                customer_id=cust.id,
                source="pdf_import",
                status="completed",
                order_amount=Decimal("0"),
                nre_invoice_status="Pending Invoice",
                order_type=ORDER_TYPE_NRE_PROJECT,
            )
            s.add(so)
            s.flush()
            _ = list(so.lines)
            assert list(so.lines) == []
            s.add(SalesOrderLine(sales_order_id=so.id, sku="211610SPT", quantity=2, line_number=1))
            s.add(SalesOrderLine(sales_order_id=so.id, sku="211810SPT", quantity=2, line_number=2))
            s.flush()
            assert sales_order_has_catheter_sku(so) is True
            typ, _review = classify_order_type(s, so)
            assert typ == ORDER_TYPE_CLEARTRACT_IN_PROCESS


def test_catheter_order_omitted_from_nre_dashboard(app):
    today = date.today()
    with session_scope(app) as s:
        cust = Customer(facility_name="UCSD NRE leak", customer_type="nre", company_key="ucsd-leak-08c")
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="0000383",
            order_date=today,
            customer_id=cust.id,
            source="pdf_import",
            status="completed",
            order_amount=Decimal("0"),
            nre_invoice_status="Pending Invoice",
            order_type=ORDER_TYPE_NRE_PROJECT,
        )
        s.add(so)
        s.flush()
        s.add(SalesOrderLine(sales_order_id=so.id, sku="211610SPT", quantity=2, line_number=1))
        s.flush()
        dash = compute_nre_dashboard(s, start_date=today, end_date=today)
        assert dash["orders"] == []
        assert dash["rows"] == []
        assert dash["project_count"] == 0


def test_purchasing_po_select_min_width_and_amount(app, client):
    with session_scope(app) as s:
        sup = Supplier(name="university")
        s.add(sup)
        s.flush()
        po = PurchaseOrder(
            po_number="0000179",
            order_date=date(2026, 8, 1),
            supplier_id=sup.id,
            amount="1234.00",
        )
        s.add(po)
        s.flush()
        s.add(
            InvoiceReceivedEntry(
                date_received=date(2026, 8, 2),
                payee="university",
                description="Inv",
                amount=Decimal("1234.00"),
            )
        )
    _login(client)
    r = client.get("/admin/purchasing")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'class="inv-po-select"' in html
    select_html = html.split('class="inv-po-select"')[1].split("</select>")[0]
    assert "max-width:150px" not in select_html
    assert "min-width:260px" not in select_html
    assert "$1,234.00" in select_html
    assert "0000179" in select_html


def test_upcoming_upload_invoice_is_button_with_panel(app, client):
    with session_scope(app) as s:
        s.add(PaymentEntry(vendor="Acme", description="Widgets", amount=Decimal("50.00")))
    _login(client)
    r = client.get("/admin/purchasing")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert "pay-upload-toggle" in html
    assert "button--small" in html
    assert "button--secondary" in html
    assert "pay-upload-panel" in html
    assert "Upload invoice" in html


def test_nre_dashboard_save_hidden_until_date_changes(app, client):
    today = date.today()
    with session_scope(app) as s:
        cust = Customer(facility_name="Abryx Save", customer_type="nre", company_key="abryx-save-08c")
        s.add(cust)
        s.flush()
        s.add(
            SalesOrder(
                order_number="0000385",
                order_date=today,
                customer_id=cust.id,
                source="manual",
                status="completed",
                order_amount=Decimal("7590.00"),
                nre_invoice_status="50% Invoiced",
                invoice_date=date(2026, 8, 1),
                order_type=ORDER_TYPE_NRE_PROJECT,
            )
        )
    _login(client)
    html = client.get("/admin/nre-projects/").get_data(as_text=True)
    assert "nre-inv-date-save" not in html
    assert "nre_order_invoice_date" in html or "/invoice-date" in html
    assert 'name="invoice_date"' in html
    assert "onchange=\"this.form.submit()\"" in html
    assert 'name="nre_invoice_status"' in html
