"""P4-08D — NRE/Purchasing width, auto-save date, file-clip, filter bar."""
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.models import NREProjectEntry
from app.eqms.modules.purchasing.models import InvoiceReceivedAttachment, InvoiceReceivedEntry
from app.eqms.modules.rep_traceability.models import SalesOrder
from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_NRE_PROJECT

PW = "pw"
PERMS = [
    "admin.view",
    "admin.edit",
    "sales_orders.view",
    "sales_orders.edit",
    "customers.view",
    "purchasing.view",
    "purchasing.edit",
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


def _nre_so(s):
    cust = Customer(facility_name="Abryx Visual", customer_type="nre", company_key="abryx-08d")
    s.add(cust)
    s.flush()
    so = SalesOrder(
        order_number="0000385",
        order_date=date.today(),
        customer_id=cust.id,
        source="manual",
        status="completed",
        order_amount=Decimal("7590.00"),
        nre_invoice_status="50% Invoiced",
        order_type=ORDER_TYPE_NRE_PROJECT,
    )
    s.add(so)
    return so


def test_nre_dashboard_has_no_invoice_date_save(app, client):
    with session_scope(app) as s:
        _nre_so(s)
    _login(client)
    html = client.get("/admin/nre-projects/").get_data(as_text=True)
    assert "nre-inv-date-save" not in html
    dash = html.split('id="nre-dash-projects"')[1].split("</table>")[0]
    assert ">Save<" not in dash


def test_nre_invoice_date_posts_on_change(app, client):
    with session_scope(app) as s:
        _nre_so(s)
    _login(client)
    html = client.get("/admin/nre-projects/").get_data(as_text=True)
    assert "/invoice-date" in html
    assert 'name="invoice_date"' in html
    assert "onchange=\"this.form.submit()\"" in html


def test_wide_container_only_on_nre_and_purchasing(app, client):
    with session_scope(app) as s:
        _nre_so(s)
    _login(client)
    nre = client.get("/admin/nre-projects/").get_data(as_text=True)
    purch = client.get("/admin/purchasing").get_data(as_text=True)
    dash = client.get("/admin/").get_data(as_text=True)
    assert 'class="container container--wide"' in nre
    assert 'class="container container--wide"' in purch
    assert "container--wide" not in dash.split("<main")[1].split("</main>")[0]


def test_design_system_has_wide_and_hidden_override():
    css = Path("app/eqms/static/design-system.css").read_text(encoding="utf-8")
    assert ".container--wide" in css
    assert "[hidden], .button[hidden], button[hidden]" in css
    assert "display: none !important;" in css
    assert ".file-clip" in css


def test_invoice_received_file_clip(app, client):
    with session_scope(app) as s:
        empty = InvoiceReceivedEntry(
            date_received=date(2026, 8, 2),
            payee="EmptyFiles",
            description="None",
            amount=Decimal("1.00"),
        )
        s.add(empty)
        s.flush()
        filled = InvoiceReceivedEntry(
            date_received=date(2026, 8, 3),
            payee="HasFile",
            description="One",
            amount=Decimal("2.00"),
        )
        s.add(filled)
        s.flush()
        s.add(
            InvoiceReceivedAttachment(
                invoice_received_entry_id=filled.id,
                filename="UNIQUE_INVOICE_FILE_XYZ.pdf",
                storage_key="tmp/unique-inv.pdf",
            )
        )
    _login(client)
    html = client.get("/admin/purchasing").get_data(as_text=True)
    invoices = html.split("Invoices Received")[1].split("Purchase Orders")[0]
    assert invoices.count("file-clip-add") >= 1
    assert "file-clip-open" in invoices
    assert 'title="UNIQUE_INVOICE_FILE_XYZ.pdf"' in invoices
    assert ">UNIQUE_INVOICE_FILE_XYZ.pdf<" not in invoices


def test_po_filter_not_inside_form_class(app, client):
    _login(client)
    html = client.get("/admin/purchasing").get_data(as_text=True)
    bar = html.split("Purchase Orders")[1].split("result")[0]
    assert 'class="po-filter-bar"' in bar
    assert 'class="form"' not in bar
    assert "max-width: 420px" not in bar
    row = bar.split('class="po-filter-bar"')[1].split("</form>")[0]
    assert "Search" in row
    assert "Status" in row
    assert "Apply" in row
    assert "Clear" in row


def test_tracker_match_is_in_details(app, client):
    with session_scope(app) as s:
        _nre_so(s)
        s.add(
            NREProjectEntry(
                customer_name="Open job",
                description="Unmatched",
                invoice_status="Pending Invoice",
            )
        )
    _login(client)
    html = client.get("/admin/nre-projects/").get_data(as_text=True)
    tracker = html.split("Upcoming NRE Invoice Tracker")[1].split("NRE Dashboard")[0]
    assert "<details" in tracker
    assert 'class="nre-match-group"' in tracker
    match_bit = tracker.split("<details")[1].split("</details>")[0]
    assert "Match" in match_bit
    assert 'type="submit"' in match_bit
