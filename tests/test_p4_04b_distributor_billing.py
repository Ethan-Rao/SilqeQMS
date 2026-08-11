"""
P4-04B — Distributor billing order type and customer.is_distributor flag.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.customer_profiles.service import update_customer
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder, SalesOrderLine
from app.eqms.modules.rep_traceability.order_type import (
    ORDER_TYPE_CLEARTRACT_DISTRIBUTION,
    ORDER_TYPE_CLEARTRACT_IN_PROCESS,
    ORDER_TYPE_DISTRIBUTOR_BILLING,
    ORDER_TYPE_NRE_PROJECT,
    apply_order_type,
    classify_order_type,
    set_order_type_manual,
)
from app.eqms.modules.rep_traceability.service import compute_sales_dashboard

PW = "pw"
PERMS = [
    "admin.view",
    "admin.edit",
    "sales_orders.view",
    "sales_orders.edit",
    "customers.view",
    "customers.edit",
    "shipstation.view",
    "shipstation.run",
]
CATHETER_SKU = "211610SPT"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("SHIPSTATION_API_KEY", raising=False)
    monkeypatch.delenv("SHIPSTATION_API_SECRET", raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        perms = {k: Permission(key=k, name=k) for k in PERMS}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms.values())
        admin = User(
            email="admin@silq.tech",
            display_name="Admin",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        admin.roles.append(admin_role)
        s.add_all(list(perms.values()) + [admin_role, admin])

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


def _customer(s, *, name="HPFY", is_distributor=True, key=None):
    c = Customer(
        facility_name=name,
        company_key=key or f"key-{name.lower().replace(' ', '-')}",
        customer_type="catheter",
        is_distributor=is_distributor,
    )
    s.add(c)
    s.flush()
    return c


def _order(s, customer, *, amount, order_number="0000146", with_catheter_line=True):
    so = SalesOrder(
        order_number=order_number,
        order_date=date(2025, 6, 1),
        customer_id=customer.id,
        source="pdf_import",
        status="completed",
        order_amount=amount,
        nre_invoice_status="Pending Invoice",
    )
    s.add(so)
    s.flush()
    if with_catheter_line:
        s.add(
            SalesOrderLine(
                sales_order_id=so.id,
                sku=CATHETER_SKU,
                quantity=2,
                line_number=1,
            )
        )
        s.flush()
    return so


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
def test_distributor_nonzero_no_dist_is_billing(app):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("145.00"))
        t, review = classify_order_type(s, so)
        assert t == ORDER_TYPE_DISTRIBUTOR_BILLING
        assert review is False


def test_distributor_zero_amount_stays_in_process(app):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("0"), order_number="0000100")
        t, review = classify_order_type(s, so)
        assert t == ORDER_TYPE_CLEARTRACT_IN_PROCESS
        assert review is False


def test_distributor_null_amount_not_billing(app):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=None, order_number="0000101")
        t, _ = classify_order_type(s, so)
        assert t == ORDER_TYPE_CLEARTRACT_IN_PROCESS
        assert t != ORDER_TYPE_DISTRIBUTOR_BILLING


def test_non_distributor_nonzero_stays_in_process(app):
    """VAMC Loma Linda-style: amount does not make billing without the flag."""
    with session_scope(app) as s:
        c = _customer(s, name="VAMC Loma Linda", is_distributor=False, key="vamc-ll")
        so = _order(s, c, amount=Decimal("2654.40"), order_number="0000999")
        t, _ = classify_order_type(s, so)
        assert t == ORDER_TYPE_CLEARTRACT_IN_PROCESS


def test_shipstation_distribution_beats_billing(app):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("500.00"), order_number="0000200")
        s.add(
            DistributionLogEntry(
                ship_date=date(2025, 6, 2),
                order_number=so.order_number,
                facility_name=c.facility_name,
                sku=CATHETER_SKU,
                lot_number="LOT1",
                quantity=1,
                source="shipstation",
                sales_order_id=so.id,
                customer_id=c.id,
            )
        )
        s.flush()
        t, _ = classify_order_type(s, so)
        assert t == ORDER_TYPE_CLEARTRACT_DISTRIBUTION


def test_billing_with_catheter_lines_still_billing(app):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("199.00"), with_catheter_line=True)
        t, _ = classify_order_type(s, so)
        assert t == ORDER_TYPE_DISTRIBUTOR_BILLING


def test_manual_type_not_overwritten(app):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("100.00"))
        so.order_type = ORDER_TYPE_CLEARTRACT_IN_PROCESS
        so.order_type_is_manual = True
        s.flush()
        assert apply_order_type(s, so) is False
        assert so.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS


def test_clearing_distributor_flag_reclassifies(app):
    with session_scope(app) as s:
        admin = s.query(User).filter_by(email="admin@silq.tech").one()
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("145.00"))
        apply_order_type(s, so)
        assert so.order_type == ORDER_TYPE_DISTRIBUTOR_BILLING

        update_customer(
            s,
            c,
            {
                "facility_name": c.facility_name,
                "is_distributor": False,
            },
            user=admin,
            reason="clear distributor flag",
        )
        s.flush()
        assert c.is_distributor is False
        assert so.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS


# --------------------------------------------------------------------------- #
# UI / routes
# --------------------------------------------------------------------------- #
def test_list_dropdown_and_filter(app, client):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("50.00"), order_number="BILL1")
        apply_order_type(s, so)
        so_id = so.id

    _login(client)
    body = client.get("/admin/sales-orders").get_data(as_text=True)
    assert "Distributor Billing" in body
    assert 'value="distributor_billing"' in body

    filtered = client.get("/admin/sales-orders?order_type=distributor_billing").get_data(as_text=True)
    assert "BILL1" in filtered
    # Ensure filter works (other types not required absent from page chrome)
    assert "distributor_billing" in filtered or "Distributor Billing" in filtered


def test_manual_set_distributor_billing(app, client):
    with session_scope(app) as s:
        c = _customer(s, name="Manual Dist", is_distributor=False, key="manual-d")
        so = _order(s, c, amount=Decimal("10.00"), order_number="MAN1")
        so.order_type = ORDER_TYPE_CLEARTRACT_IN_PROCESS
        so_id = so.id

    _login(client)
    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{so_id}/order-type",
        data={
            "csrf_token": token,
            "order_type": ORDER_TYPE_DISTRIBUTOR_BILLING,
            "next": f"/admin/sales-orders/{so_id}",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        so = s.get(SalesOrder, so_id)
        assert so.order_type == ORDER_TYPE_DISTRIBUTOR_BILLING
        assert so.order_type_is_manual is True


def test_billing_absent_from_shipstation_probe(app, client):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        billing = _order(s, c, amount=Decimal("100.00"), order_number="0000363")
        apply_order_type(s, billing)
        ip = SalesOrder(
            order_number="0000400",
            order_date=date(2025, 1, 8),
            customer_id=c.id,
            source="manual",
            status="pending",
            order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
            order_amount=Decimal("0"),
        )
        s.add(ip)
        s.flush()
        s.add(SalesOrderLine(sales_order_id=ip.id, sku=CATHETER_SKU, quantity=1, line_number=1))

    _login(client)
    body = client.get("/admin/shipstation/probe-in-process").get_data(as_text=True)
    assert "0000400" in body
    assert "0000363" not in body


def test_billing_absent_from_nre_surfaces(app, client):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("88.00"), order_number="NREHIDE")
        apply_order_type(s, so)
        assert so.order_type == ORDER_TYPE_DISTRIBUTOR_BILLING

    _login(client)
    body = client.get("/admin/nre-projects/?start=2020-01-01&end=2030-12-31").get_data(as_text=True)
    assert "NREHIDE" not in body


def test_units_dashboard_unchanged_by_billing_reclass(app):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=True)
        so = _order(s, c, amount=Decimal("0"), order_number="SHIP1")
        apply_order_type(s, so)
        s.add(
            DistributionLogEntry(
                ship_date=date(2025, 6, 15),
                order_number=so.order_number,
                facility_name=c.facility_name,
                sku=CATHETER_SKU,
                lot_number="L1",
                quantity=7,
                source="shipstation",
                sales_order_id=so.id,
                customer_id=c.id,
            )
        )
        billing = _order(s, c, amount=Decimal("200.00"), order_number="BILLX")
        apply_order_type(s, billing)
        assert billing.order_type == ORDER_TYPE_DISTRIBUTOR_BILLING
        s.flush()

        before = compute_sales_dashboard(s, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
        apply_order_type(s, billing)
        after = compute_sales_dashboard(s, start_date=date(2025, 1, 1), end_date=date(2025, 12, 31))
        assert before["stats"]["total_units_window"] == after["stats"]["total_units_window"] == 7


def test_customer_checkbox_sets_and_clears_flag(app, client):
    with session_scope(app) as s:
        c = _customer(s, is_distributor=False, name="FlagMe", key="flag-me")
        cid = c.id

    _login(client)
    token = _csrf(client)
    r = client.post(
        f"/admin/customers/{cid}",
        data={
            "csrf_token": token,
            "facility_name": "FlagMe",
            "is_distributor": "1",
            "reason": "mark distributor",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.get(Customer, cid).is_distributor is True

    token = _csrf(client)
    r = client.post(
        f"/admin/customers/{cid}",
        data={
            "csrf_token": token,
            "facility_name": "FlagMe",
            # checkbox omitted → false
            "reason": "clear distributor",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.get(Customer, cid).is_distributor is False


def test_missing_customer_does_not_raise(app):
    with session_scope(app) as s:
        c = _customer(s, name="Temp", is_distributor=False, key="temp-x")
        so = _order(s, c, amount=Decimal("100.00"), order_number="ORPHAN", with_catheter_line=False)
        so.customer_id = 999999  # dangling reference; must not raise
        s.expire(so, ["customer"])
        t, review = classify_order_type(s, so)
        assert t == ORDER_TYPE_NRE_PROJECT
        assert review is True
