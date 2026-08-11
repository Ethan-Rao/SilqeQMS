"""
P4-03 — Sales-order detail control surface: customer, link/unlink, status, type.
"""
from __future__ import annotations

import json
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.admin import _nre_customers
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder, SalesOrderLine
from app.eqms.modules.rep_traceability.order_type import (
    ORDER_TYPE_CLEARTRACT_DELIVERY,
    ORDER_TYPE_CLEARTRACT_DISTRIBUTION,
    ORDER_TYPE_CLEARTRACT_IN_PROCESS,
    ORDER_TYPE_NRE_PROJECT,
)

PW = "pw"
PERMS = [
    "admin.view",
    "admin.edit",
    "sales_orders.view",
    "sales_orders.edit",
    "sales_orders.import",
    "customers.view",
    "distribution_log.view",
    "distribution_log.edit",
]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

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

        staff_role = Role(key="staff", name="Staff")
        for k in ("admin.view", "sales_orders.view"):
            staff_role.permissions.append(perms[k])
        staff = User(
            email="staff@silq.tech",
            display_name="Staff",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        staff.roles.append(staff_role)

        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, staff])

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@silq.tech"):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets

    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


def _seed_base(s):
    c1 = Customer(facility_name="VAMC - Loma Linda", company_key="VAMC-LL", customer_type="catheter")
    c2 = Customer(facility_name="Other Hospital", company_key="OTHER-H", customer_type="catheter")
    s.add_all([c1, c2])
    s.flush()
    so = SalesOrder(
        order_number="0000165",
        order_date=date(2025, 3, 18),
        customer_id=c1.id,
        source="pdf_import",
        status="pending",
        order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
        order_type_is_manual=False,
        order_type_needs_review=False,
    )
    s.add(so)
    s.flush()
    s.add(SalesOrderLine(sales_order_id=so.id, sku="211610SPT", quantity=1, line_number=1))
    s.flush()
    return so, c1, c2


def _audit_meta(s, action: str):
    ev = s.query(AuditEvent).filter(AuditEvent.action == action).order_by(AuditEvent.id.desc()).first()
    assert ev is not None
    return json.loads(ev.metadata_json or "{}")


# --------------------------------------------------------------------------- #
# Task A — customer reassignment
# --------------------------------------------------------------------------- #
def test_reassign_customer_resyncs_distributions(client, app):
    _login(client)
    with session_scope(app) as s:
        so, c1, c2 = _seed_base(s)
        dist = DistributionLogEntry(
            ship_date=date(2025, 3, 19),
            order_number="SO 0000164",
            facility_name=c1.facility_name,
            sku="211610SPT",
            lot_number="L1",
            quantity=1,
            source="shipstation",
            sales_order_id=so.id,
            customer_id=c1.id,
        )
        s.add(dist)
        s.flush()
        oid, new_cid, old_name, new_name = so.id, c2.id, c1.facility_name, c2.facility_name
        dist_id = dist.id

    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{oid}/customer",
        data={"customer_id": str(new_cid), "csrf_token": token},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert old_name.encode() in r.data
    assert new_name.encode() in r.data

    with session_scope(app) as s:
        so = s.get(SalesOrder, oid)
        dist = s.get(DistributionLogEntry, dist_id)
        assert so.customer_id == new_cid
        assert dist.customer_id == new_cid
        assert dist.facility_name == new_name
        meta = _audit_meta(s, "sales_order.customer_reassigned")
        assert meta["after_customer_id"] == new_cid
        assert meta["distributions_resynced"] == 1


def test_reassign_creates_new_customer(client, app):
    _login(client)
    with session_scope(app) as s:
        so, c1, _ = _seed_base(s)
        oid = so.id
        old_cid = c1.id

    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{oid}/customer",
        data={"new_customer_name": "Brand New Facility LLC", "csrf_token": token},
        follow_redirects=True,
    )
    assert r.status_code == 200

    with session_scope(app) as s:
        so = s.get(SalesOrder, oid)
        assert so.customer.facility_name == "Brand New Facility LLC"
        assert so.customer_id != old_cid


# --------------------------------------------------------------------------- #
# Task B — link / unlink
# --------------------------------------------------------------------------- #
def test_link_allows_differing_order_numbers(client, app):
    _login(client)
    with session_scope(app) as s:
        so, c1, _ = _seed_base(s)
        dist = DistributionLogEntry(
            ship_date=date(2025, 3, 19),
            order_number="SO 0000164",
            facility_name="VAMC - LOMA LINDA",
            sku="211610SPT",
            lot_number="L1",
            quantity=1,
            source="shipstation",
            sales_order_id=None,
            customer_id=None,
        )
        s.add(dist)
        s.flush()
        oid, did = so.id, dist.id

    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{oid}/distributions/link",
        data={"distribution_id": str(did), "csrf_token": token},
        follow_redirects=True,
    )
    assert r.status_code == 200

    with session_scope(app) as s:
        dist = s.get(DistributionLogEntry, did)
        so = s.get(SalesOrder, oid)
        assert dist.sales_order_id == oid
        assert dist.customer_id == so.customer_id
        assert so.order_type == ORDER_TYPE_CLEARTRACT_DISTRIBUTION
        meta = _audit_meta(s, "distribution.link_sales_order")
        assert meta["numbers_differed"] is True
        assert meta["distribution_order_number"] == "SO 0000164"
        assert meta["order_number"] == "0000165"


def test_link_manual_yields_delivery_type(client, app):
    _login(client)
    with session_scope(app) as s:
        so, c1, _ = _seed_base(s)
        dist = DistributionLogEntry(
            ship_date=date(2025, 4, 1),
            order_number="0000165",
            facility_name=c1.facility_name,
            sku="211610SPT",
            lot_number="L2",
            quantity=1,
            source="manual",
            sales_order_id=None,
        )
        s.add(dist)
        s.flush()
        oid, did = so.id, dist.id

    token = _csrf(client)
    client.post(
        f"/admin/sales-orders/{oid}/distributions/link",
        data={"distribution_id": str(did), "csrf_token": token},
        follow_redirects=True,
    )

    with session_scope(app) as s:
        assert s.get(SalesOrder, oid).order_type == ORDER_TYPE_CLEARTRACT_DELIVERY


def test_link_repoints_from_other_order(client, app):
    _login(client)
    with session_scope(app) as s:
        so_a, c1, c2 = _seed_base(s)
        so_b = SalesOrder(
            order_number="0000999",
            order_date=date(2025, 5, 1),
            customer_id=c2.id,
            source="pdf_import",
            status="pending",
            order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
        )
        s.add(so_b)
        s.flush()
        s.add(SalesOrderLine(sales_order_id=so_b.id, sku="211610SPT", quantity=1, line_number=1))
        dist = DistributionLogEntry(
            ship_date=date(2025, 5, 2),
            order_number="0000999",
            facility_name=c2.facility_name,
            sku="211610SPT",
            lot_number="L3",
            quantity=1,
            source="shipstation",
            sales_order_id=so_b.id,
            customer_id=c2.id,
        )
        s.add(dist)
        s.flush()
        # Give so_b a type reflecting the link
        so_b.order_type = ORDER_TYPE_CLEARTRACT_DISTRIBUTION
        oid_a, oid_b, did = so_a.id, so_b.id, dist.id

    token = _csrf(client)
    client.post(
        f"/admin/sales-orders/{oid_a}/distributions/link",
        data={"distribution_id": str(did), "csrf_token": token},
        follow_redirects=True,
    )

    with session_scope(app) as s:
        dist = s.get(DistributionLogEntry, did)
        so_a = s.get(SalesOrder, oid_a)
        so_b = s.get(SalesOrder, oid_b)
        assert dist.sales_order_id == oid_a
        assert so_a.order_type == ORDER_TYPE_CLEARTRACT_DISTRIBUTION
        assert so_b.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS
        meta = _audit_meta(s, "distribution.link_sales_order")
        assert meta["previous_sales_order_id"] == oid_b


def test_manual_order_type_survives_link_and_unlink(client, app):
    _login(client)
    with session_scope(app) as s:
        so, c1, _ = _seed_base(s)
        so.order_type = ORDER_TYPE_NRE_PROJECT
        so.order_type_is_manual = True
        dist = DistributionLogEntry(
            ship_date=date(2025, 6, 1),
            order_number="0000165",
            facility_name=c1.facility_name,
            sku="211610SPT",
            lot_number="L4",
            quantity=1,
            source="shipstation",
            sales_order_id=None,
        )
        s.add(dist)
        s.flush()
        oid, did = so.id, dist.id

    token = _csrf(client)
    client.post(
        f"/admin/sales-orders/{oid}/distributions/link",
        data={"distribution_id": str(did), "csrf_token": token},
        follow_redirects=True,
    )
    with session_scope(app) as s:
        so = s.get(SalesOrder, oid)
        assert so.order_type == ORDER_TYPE_NRE_PROJECT
        assert so.order_type_is_manual is True

    token = _csrf(client)
    client.post(
        f"/admin/sales-orders/{oid}/distributions/{did}/unlink",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    with session_scope(app) as s:
        so = s.get(SalesOrder, oid)
        assert so.order_type == ORDER_TYPE_NRE_PROJECT
        assert so.order_type_is_manual is True


def test_unlink_clears_and_audits_previous_id(client, app):
    _login(client)
    with session_scope(app) as s:
        so, c1, _ = _seed_base(s)
        so.order_type = ORDER_TYPE_CLEARTRACT_DISTRIBUTION
        dist = DistributionLogEntry(
            ship_date=date(2025, 3, 19),
            order_number="0000165",
            facility_name=c1.facility_name,
            sku="211610SPT",
            lot_number="L1",
            quantity=1,
            source="shipstation",
            sales_order_id=so.id,
            customer_id=c1.id,
        )
        s.add(dist)
        s.flush()
        oid, did = so.id, dist.id

    token = _csrf(client)
    client.post(
        f"/admin/sales-orders/{oid}/distributions/{did}/unlink",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    with session_scope(app) as s:
        dist = s.get(DistributionLogEntry, did)
        so = s.get(SalesOrder, oid)
        assert dist.sales_order_id is None
        assert so.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS
        meta = _audit_meta(s, "distribution.clear_sales_order")
        assert meta["previous_sales_order_id"] == oid


# --------------------------------------------------------------------------- #
# Task C — status cancelled
# --------------------------------------------------------------------------- #
def test_set_status_cancelled_and_reject_invalid(client, app):
    _login(client)
    with session_scope(app) as s:
        so, _, _ = _seed_base(s)
        oid = so.id

    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{oid}/status",
        data={"status": "cancelled", "csrf_token": token},
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.get(SalesOrder, oid).status == "cancelled"
        meta = _audit_meta(s, "sales_order.status_changed")
        assert meta["before"] == "pending"
        assert meta["after"] == "cancelled"

    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{oid}/status",
        data={"status": "bogus", "csrf_token": token},
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"Invalid status" in r.data
    with session_scope(app) as s:
        assert s.get(SalesOrder, oid).status == "cancelled"


def test_cancelled_hidden_from_in_process_unless_included(client, app):
    _login(client)
    with session_scope(app) as s:
        so, _, _ = _seed_base(s)
        so.status = "cancelled"
        so.order_type = ORDER_TYPE_CLEARTRACT_IN_PROCESS
        oid = so.id
        num = so.order_number

    r = client.get("/admin/sales-orders?order_type=cleartract_in_process")
    assert r.status_code == 200
    assert num.encode() not in r.data

    r = client.get("/admin/sales-orders?order_type=cleartract_in_process&include_cancelled=1")
    assert r.status_code == 200
    assert num.encode() in r.data
    assert b"Cancelled" in r.data


def test_cancelled_nre_excluded_from_dashboard(client, app):
    _login(client)
    with session_scope(app) as s:
        cust = Customer(facility_name="NRE Only Co", company_key="NREONLY", customer_type="auto")
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="NRE-CAN",
            order_date=date(2026, 1, 10),
            customer_id=cust.id,
            source="pdf_import",
            status="cancelled",
            order_type=ORDER_TYPE_NRE_PROJECT,
        )
        s.add(so)
        s.flush()
        names = {c.facility_name for c in _nre_customers(s)}
        assert "NRE Only Co" not in names

    r = client.get("/admin/nre-projects/")
    assert r.status_code == 200
    assert b"NRE Only Co" not in r.data


# --------------------------------------------------------------------------- #
# Task D — type dropdown on detail
# --------------------------------------------------------------------------- #
def test_detail_type_dropdown_returns_to_detail(client, app):
    _login(client)
    with session_scope(app) as s:
        so, _, _ = _seed_base(s)
        oid = so.id

    r = client.get(f"/admin/sales-orders/{oid}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'name="order_type"' in body
    assert 'name="status"' in body
    assert "Save customer" in body
    assert "Link a distribution" in body

    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{oid}/order-type",
        data={
            "order_type": ORDER_TYPE_CLEARTRACT_DELIVERY,
            "next": f"/admin/sales-orders/{oid}",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    assert f"/admin/sales-orders/{oid}" in (r.headers.get("Location") or "")

    with session_scope(app) as s:
        so = s.get(SalesOrder, oid)
        assert so.order_type == ORDER_TYPE_CLEARTRACT_DELIVERY
        assert so.order_type_is_manual is True


# --------------------------------------------------------------------------- #
# Permissions + CSRF
# --------------------------------------------------------------------------- #
def test_new_routes_require_permission_and_csrf(client, app):
    with session_scope(app) as s:
        so, _, _ = _seed_base(s)
        dist = DistributionLogEntry(
            ship_date=date(2025, 3, 19),
            order_number="SO 0000164",
            facility_name="X",
            sku="211610SPT",
            lot_number="L1",
            quantity=1,
            source="manual",
            sales_order_id=None,
        )
        s.add(dist)
        s.flush()
        oid, did = so.id, dist.id

    routes = [
        (f"/admin/sales-orders/{oid}/customer", {"customer_id": "1"}),
        (f"/admin/sales-orders/{oid}/status", {"status": "cancelled"}),
        (f"/admin/sales-orders/{oid}/distributions/link", {"distribution_id": str(did)}),
        (f"/admin/sales-orders/{oid}/distributions/{did}/unlink", {}),
    ]

    _login(client, email="staff@silq.tech")
    for path, extra in routes:
        token = _csrf(client)
        data = dict(extra)
        data["csrf_token"] = token
        r = client.post(path, data=data)
        assert r.status_code == 403, path

    _login(client)
    for path, extra in routes:
        r = client.post(path, data=extra)  # no csrf
        assert r.status_code == 400, path
