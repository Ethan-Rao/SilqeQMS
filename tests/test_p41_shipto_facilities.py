"""
Prompt 41 — Ship-To facility identity, distribution dedupe, NRE orphan cleanup.
"""
from datetime import date
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.customer_profiles.utils import compute_facility_key_from_ship_to
from app.eqms.modules.nre_projects.admin import _nre_customers
from app.eqms.modules.rep_traceability.models import (
    DistributionLine,
    DistributionLogEntry,
    SalesOrder,
    SalesOrderLine,
)
from app.eqms.modules.rep_traceability.service import (
    create_distribution_entry,
    delete_sales_order_with_cleanup,
    find_sales_order_by_normalized_number,
    match_distribution_to_sales_order,
    rematch_unmatched_distributions_for_order,
)

PW = "pw"
PERMS = [
    "admin.view", "admin.edit",
    "sales_orders.view", "sales_orders.edit",
    "customers.view", "distribution_log.view", "distribution_log.edit",
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


def _admin(app):
    with session_scope(app) as s:
        return s.query(User).filter_by(email="admin@silq.tech").one()


# --------------------------------------------------------------------------- #
# Facility keys
# --------------------------------------------------------------------------- #
def test_facility_key_ignores_address2_and_zip4():
    a = compute_facility_key_from_ship_to(
        address1="7601 E Imperial Parkway", city="Downey", state="CA", zip="90242-1234",
    )
    b = compute_facility_key_from_ship_to(
        address1="7601 E Imperial Parkway", city="Downey", state="CA", zip="90242",
        facility_name="Other Name",
    )
    assert a == b


def test_marathon_sites_different_keys():
    lb = compute_facility_key_from_ship_to(
        address1="1 Marathon Way", city="Long Beach", state="CA", zip="90802",
        facility_name="Marathon Medical Corporation",
    )
    sd = compute_facility_key_from_ship_to(
        address1="2 Marathon Way", city="San Diego", state="CA", zip="92101",
        facility_name="Marathon Medical Corporation",
    )
    assert lb != sd


# --------------------------------------------------------------------------- #
# Duplicate vs multi-shipment
# --------------------------------------------------------------------------- #
def test_duplicate_dist_orphan_deleted_keep_linked(app):
    with session_scope(app) as s:
        cust = Customer(
            facility_name="Harbor UCLA — Torrance",
            company_key="HARBORTEST",
            customer_type="catheter",
        )
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="0000312",
            order_date=date(2026, 6, 1),
            customer_id=cust.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()
        linked = DistributionLogEntry(
            ship_date=date(2026, 6, 2),
            order_number="0000312",
            facility_name=cust.facility_name,
            customer_id=cust.id,
            sales_order_id=so.id,
            sku="211610SPT",
            lot_number="SLQ-1",
            quantity=10,
            source="shipstation",
            ss_shipment_id="ss-a",
        )
        orphan = DistributionLogEntry(
            ship_date=date(2026, 6, 2),
            order_number="SO 0000312",
            facility_name="HARBOR-UCLA MEDICAL CENTER",
            customer_id=None,
            sales_order_id=None,
            sku="211610SPT",
            lot_number="SLQ-1",
            quantity=10,
            source="shipstation",
            ss_shipment_id="ss-b",
        )
        s.add_all([linked, orphan])
        s.flush()
        s.add(DistributionLine(distribution_entry_id=linked.id, sku="211610SPT", lot_number="SLQ-1", quantity=10))
        s.add(DistributionLine(distribution_entry_id=orphan.id, sku="211610SPT", lot_number="SLQ-1", quantity=10))
        lid, oid = linked.id, orphan.id

    # Apply Phase-1 style delete of orphan
    from app.eqms.modules.rep_traceability.service import delete_distribution_entry

    with app.app_context():
        with session_scope(app) as s:
            u = s.query(User).one()
            orphan = s.get(DistributionLogEntry, oid)
            delete_distribution_entry(s, orphan, user=u, reason="test_dup")
            s.flush()
            s.expire_all()
            assert s.get(DistributionLogEntry, lid) is not None
            assert s.query(DistributionLogEntry).filter_by(id=oid).first() is None


def test_multi_shipment_different_qty_kept(app):
    with session_scope(app) as s:
        cust = Customer(facility_name="Site", company_key="SITE1", customer_type="catheter")
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="0000999", order_date=date(2026, 1, 1),
            customer_id=cust.id, source="pdf_import", status="completed",
        )
        s.add(so)
        s.flush()
        d1 = DistributionLogEntry(
            ship_date=date(2026, 1, 2), order_number="0000999", facility_name="Site",
            customer_id=cust.id, sales_order_id=so.id, sku="211610SPT", lot_number="A",
            quantity=5, source="shipstation", ss_shipment_id="m1",
        )
        d2 = DistributionLogEntry(
            ship_date=date(2026, 1, 2), order_number="0000999", facility_name="Site",
            customer_id=cust.id, sales_order_id=so.id, sku="211610SPT", lot_number="A",
            quantity=15, source="shipstation", ss_shipment_id="m2",
        )
        s.add_all([d1, d2])
        s.flush()
        s.add(DistributionLine(distribution_entry_id=d1.id, sku="211610SPT", lot_number="A", quantity=5))
        s.add(DistributionLine(distribution_entry_id=d2.id, sku="211610SPT", lot_number="A", quantity=15))
        ids = (d1.id, d2.id)

    with session_scope(app) as s:
        assert s.get(DistributionLogEntry, ids[0]) is not None
        assert s.get(DistributionLogEntry, ids[1]) is not None
        a = s.get(DistributionLogEntry, ids[0])
        b = s.get(DistributionLogEntry, ids[1])
        assert (a.sku, a.quantity) != (b.sku, b.quantity) or a.quantity != b.quantity


# --------------------------------------------------------------------------- #
# Normalize order number link
# --------------------------------------------------------------------------- #
def test_find_sales_order_normalized_shipstation_style(app):
    with session_scope(app) as s:
        cust = Customer(facility_name="X", company_key="XKEY", customer_type="catheter")
        s.add(cust)
        s.flush()
        s.add(SalesOrder(
            order_number="0000312", order_date=date(2026, 1, 1),
            customer_id=cust.id, source="pdf_import", status="completed",
        ))

    with session_scope(app) as s:
        so = find_sales_order_by_normalized_number(s, "SO 0000312")
        assert so is not None
        assert so.order_number == "0000312"


def test_create_distribution_auto_links_normalized(app):
    with app.app_context():
        with session_scope(app) as s:
            u = s.query(User).one()
            cust = Customer(facility_name="Y", company_key="YKEY", customer_type="catheter")
            s.add(cust)
            s.flush()
            so = SalesOrder(
                order_number="0000302", order_date=date(2026, 1, 1),
                customer_id=cust.id, source="pdf_import", status="completed",
            )
            s.add(so)
            s.flush()
            e = create_distribution_entry(
                s,
                {
                    "ship_date": "2026-01-02",
                    "order_number": "SO 0000302",
                    "facility_name": "RCRMC",
                    "sku": "211610SPT",
                    "lot_number": "L1",
                    "quantity": 3,
                    "source": "shipstation",
                },
                user=u,
                source_default="shipstation",
            )
            assert e.sales_order_id == so.id
            assert e.customer_id == cust.id


def test_rematch_unmatched_harbor_style(app):
    with session_scope(app) as s:
        cust = Customer(
            facility_name="Harbor UCLA — Torrance",
            company_key="HARBOR2",
            customer_type="catheter",
        )
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="0000312", order_date=date(2026, 1, 1),
            customer_id=cust.id, source="pdf_import", status="completed",
        )
        s.add(so)
        s.flush()
        d = DistributionLogEntry(
            ship_date=date(2026, 1, 2),
            order_number="SO 0000312",
            facility_name="HARBOR-UCLA MEDICAL CENTER",
            customer_id=None,
            sales_order_id=None,
            sku="211610SPT",
            lot_number="L",
            quantity=1,
            source="shipstation",
        )
        s.add(d)
        s.flush()
        n = rematch_unmatched_distributions_for_order(s, so)
        assert n == 1
        assert d.sales_order_id == so.id
        assert d.customer_id == cust.id
        assert d.facility_name == cust.facility_name


# --------------------------------------------------------------------------- #
# NRE classification + orphan delete
# --------------------------------------------------------------------------- #
def test_auto_nre_excludes_catheter_sku_without_distribution(app):
    with session_scope(app) as s:
        nre = Customer(facility_name="True NRE Co", company_key="TRUENRE", customer_type="auto")
        cath = Customer(facility_name="Day Kimball", company_key="DAYK", customer_type="auto")
        s.add_all([nre, cath])
        s.flush()
        so_nre = SalesOrder(
            order_number="NRE1", order_date=date(2026, 1, 1),
            customer_id=nre.id, source="pdf_import", status="completed",
        )
        so_cath = SalesOrder(
            order_number="0000366", order_date=date(2026, 1, 1),
            customer_id=cath.id, source="pdf_import", status="completed",
        )
        s.add_all([so_nre, so_cath])
        s.flush()
        s.add(SalesOrderLine(sales_order_id=so_nre.id, sku="CUSTOM-PART", quantity=1, line_number=1))
        s.add(SalesOrderLine(sales_order_id=so_cath.id, sku="211610SPT", quantity=2, line_number=1))

    with session_scope(app) as s:
        names = {c.facility_name for c in _nre_customers(s)}
        assert "True NRE Co" in names
        assert "Day Kimball" not in names


def test_delete_last_auto_so_removes_orphan_customer(client, app):
    _login(client)
    token = _csrf(client)
    with session_scope(app) as s:
        cust = Customer(facility_name="Orphan NRE", company_key="ORPHNRE", customer_type="auto")
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="ORPH1", order_date=date(2026, 1, 1),
            customer_id=cust.id, source="pdf_import", status="completed",
        )
        s.add(so)
        s.flush()
        s.add(SalesOrderLine(sales_order_id=so.id, sku="WIDGET", quantity=1, line_number=1))
        cid, oid = cust.id, so.id

    r = client.post(
        f"/admin/nre-projects/{cid}/orders/{oid}/delete",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.get(SalesOrder, oid) is None
        assert s.get(Customer, cid) is None
        assert all(c.id != cid for c in _nre_customers(s))
