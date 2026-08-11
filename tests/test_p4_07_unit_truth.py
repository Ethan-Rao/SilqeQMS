"""
P4-07 — One unit-counting helper; unmatched on customer totals; Harbor attach; ShipStation wording.
"""
from __future__ import annotations

import json
import re
from datetime import date
from types import SimpleNamespace

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.customer_profiles.utils import canonical_customer_key
from app.eqms.modules.rep_traceability.models import DistributionLine, DistributionLogEntry, SalesOrder
from app.eqms.modules.rep_traceability.service import (
    attach_distributions_to_customer,
    compute_sales_dashboard,
    distribution_unit_breakdown,
    format_unmatched_units_note,
    sum_distribution_units,
)
from app.eqms.modules.shipstation_sync.models import ShipStationSkippedOrder, ShipStationSyncRun

PW = "pw"
PERMS = [
    "admin.view",
    "customers.view",
    "customers.edit",
    "distribution_log.view",
    "sales_orders.view",
    "shipstation.view",
    "shipstation.run",
]

LATENESS_WORDS = re.compile(
    r"\b(late|lateness|overdue|aging|stale|past.?due)\b",
    re.IGNORECASE,
)


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
            display_name="Ethan Rao",
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


def _entry(*, ship_date, order_number, facility_name, quantity, customer_id=None, sales_order_id=None, sku="211610SPT", source="manual", external_key=None):
    return DistributionLogEntry(
        ship_date=ship_date,
        order_number=order_number,
        facility_name=facility_name,
        sku=sku,
        lot_number="LOT-1",
        quantity=quantity,
        source=source,
        customer_id=customer_id,
        sales_order_id=sales_order_id,
        external_key=external_key,
    )


def test_helper_prefers_lines_then_falls_back_to_entry_quantity():
    with_lines = SimpleNamespace(
        quantity=99,
        lines=[SimpleNamespace(quantity=10), SimpleNamespace(quantity=5)],
        sales_order_id=1,
    )
    without_lines = SimpleNamespace(quantity=7, lines=[], sales_order_id=None)
    assert sum_distribution_units([with_lines]) == 15
    assert sum_distribution_units([without_lines]) == 7
    assert sum_distribution_units([with_lines, without_lines]) == 22


def test_four_call_sites_agree_on_same_entries(app):
    """Regression guard: helper is the single source for the four unit call sites."""
    with session_scope(app) as s:
        c = Customer(
            facility_name="VAMC - Loma Linda",
            company_key=canonical_customer_key("VAMC - Loma Linda"),
            customer_type="catheter",
        )
        s.add(c)
        s.flush()
        so = SalesOrder(
            order_number="SO 0000200",
            order_date=date(2026, 1, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()

        matched = _entry(
            ship_date=date(2026, 2, 1),
            order_number="SO 0000200",
            facility_name=c.facility_name,
            quantity=100,
            customer_id=c.id,
            sales_order_id=so.id,
            external_key="m1",
        )
        unmatched = _entry(
            ship_date=date(2026, 3, 1),
            order_number="SO 0000201",
            facility_name=c.facility_name,
            quantity=50,
            customer_id=c.id,
            sales_order_id=None,
            external_key="u1",
        )
        multi = _entry(
            ship_date=date(2026, 4, 1),
            order_number="SO 0000202",
            facility_name=c.facility_name,
            quantity=30,
            customer_id=c.id,
            sales_order_id=None,
            external_key="u2",
        )
        s.add_all([matched, unmatched, multi])
        s.flush()
        s.add(DistributionLine(distribution_entry_id=matched.id, sku="211610SPT", lot_number="A", quantity=40))
        s.add(DistributionLine(distribution_entry_id=matched.id, sku="211410SPT", lot_number="B", quantity=60))
        s.add(DistributionLine(distribution_entry_id=unmatched.id, sku="211610SPT", lot_number="C", quantity=50))
        s.add(DistributionLine(distribution_entry_id=multi.id, sku="211610SPT", lot_number="D", quantity=10))
        s.add(DistributionLine(distribution_entry_id=multi.id, sku="211810SPT", lot_number="E", quantity=20))
        s.flush()

        entries = s.query(DistributionLogEntry).filter(DistributionLogEntry.customer_id == c.id).all()
        expected = sum_distribution_units(entries)
        assert expected == 180

        dash = compute_sales_dashboard(s, start_date=None, end_date=None)
        assert dash["stats"]["total_units_all_time"] == expected

        breakdown = distribution_unit_breakdown(entries)
        assert breakdown["total_units"] == expected
        assert breakdown["unmatched_units"] == 80
        assert breakdown["unmatched_entry_count"] == 2

        # Customer list / detail / modal all use the same helper for this customer set.
        assert sum_distribution_units(entries) == breakdown["total_units"] == dash["stats"]["total_units_all_time"]


def test_customer_total_includes_unmatched_and_reports_portion(app, client):
    _login(client)
    with session_scope(app) as s:
        c = Customer(
            facility_name="VAMC - Loma Linda",
            company_key=canonical_customer_key("VAMC - Loma Linda"),
            customer_type="catheter",
        )
        s.add(c)
        s.flush()
        so = SalesOrder(
            order_number="SO 0000300",
            order_date=date(2026, 1, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()
        m = _entry(
            ship_date=date(2026, 2, 1),
            order_number="SO 0000300",
            facility_name=c.facility_name,
            quantity=200,
            customer_id=c.id,
            sales_order_id=so.id,
            external_key="ll-m",
        )
        u = _entry(
            ship_date=date(2026, 3, 1),
            order_number="SO 0000301",
            facility_name=c.facility_name,
            quantity=120,
            customer_id=c.id,
            sales_order_id=None,
            external_key="ll-u",
        )
        s.add_all([m, u])
        s.flush()
        s.add(DistributionLine(distribution_entry_id=m.id, sku="211610SPT", lot_number="A", quantity=200))
        s.add(DistributionLine(distribution_entry_id=u.id, sku="211610SPT", lot_number="B", quantity=120))
        cid = c.id

    r = client.get(f"/admin/customers/{cid}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "320" in body
    assert "120 on 1 distribution not yet matched to a sales order" in body
    assert "/admin/diagnostics/unmatched-distributions" in body
    assert LATENESS_WORDS.search(body) is None

    r_list = client.get("/admin/customers")
    assert r_list.status_code == 200
    list_body = r_list.get_data(as_text=True)
    assert "320" in list_body
    assert "not yet matched to a sales order" in list_body


def test_customer_with_no_unmatched_shows_no_unmatched_note(app, client):
    _login(client)
    with session_scope(app) as s:
        c = Customer(
            facility_name="Fully Matched Hospital",
            company_key=canonical_customer_key("Fully Matched Hospital"),
            customer_type="catheter",
        )
        s.add(c)
        s.flush()
        so = SalesOrder(
            order_number="SO 0000400",
            order_date=date(2026, 1, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()
        e = _entry(
            ship_date=date(2026, 2, 1),
            order_number="SO 0000400",
            facility_name=c.facility_name,
            quantity=10,
            customer_id=c.id,
            sales_order_id=so.id,
            external_key="fm-1",
        )
        s.add(e)
        s.flush()
        s.add(DistributionLine(distribution_entry_id=e.id, sku="211610SPT", lot_number="A", quantity=10))
        cid = c.id

    r = client.get(f"/admin/customers/{cid}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "not yet matched to a sales order" not in body
    assert format_unmatched_units_note(unmatched_units=0, unmatched_entry_count=0) is None


def test_sales_dashboard_total_unchanged_by_refactor(app):
    """Dashboard already counted all rows; refactor must not move the total."""
    with session_scope(app) as s:
        c = Customer(
            facility_name="Dash Cust",
            company_key="DASHCUST",
            customer_type="catheter",
        )
        s.add(c)
        s.flush()
        so = SalesOrder(
            order_number="SO 0000500",
            order_date=date(2026, 1, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()

        matched = _entry(
            ship_date=date(2026, 2, 1),
            order_number="SO 0000500",
            facility_name=c.facility_name,
            quantity=100,
            customer_id=c.id,
            sales_order_id=so.id,
            external_key="d-m",
        )
        unmatched = _entry(
            ship_date=date(2026, 3, 1),
            order_number="SO 0000501",
            facility_name=c.facility_name,
            quantity=50,
            customer_id=c.id,
            sales_order_id=None,
            external_key="d-u",
        )
        multi = _entry(
            ship_date=date(2026, 4, 1),
            order_number="SO 0000502",
            facility_name=c.facility_name,
            quantity=30,
            customer_id=c.id,
            sales_order_id=so.id,
            external_key="d-multi",
        )
        no_lines = _entry(
            ship_date=date(2026, 5, 1),
            order_number="SO 0000503",
            facility_name=c.facility_name,
            quantity=7,
            customer_id=c.id,
            sales_order_id=None,
            external_key="d-nl",
        )
        s.add_all([matched, unmatched, multi, no_lines])
        s.flush()
        s.add(DistributionLine(distribution_entry_id=matched.id, sku="211610SPT", lot_number="A", quantity=100))
        s.add(DistributionLine(distribution_entry_id=unmatched.id, sku="211610SPT", lot_number="B", quantity=50))
        s.add(DistributionLine(distribution_entry_id=multi.id, sku="211610SPT", lot_number="C", quantity=10))
        s.add(DistributionLine(distribution_entry_id=multi.id, sku="211410SPT", lot_number="D", quantity=20))
        # no_lines intentionally has no DistributionLine rows

        all_entries = s.query(DistributionLogEntry).all()
        # Pre-refactor dashboard semantics: sum every entry, line-aware with entry fallback.
        legacy_total = 0
        for e in all_entries:
            lines = list(e.lines or [])
            if lines:
                legacy_total += sum(int(l.quantity or 0) for l in lines)
            else:
                legacy_total += int(e.quantity or 0)

        dash = compute_sales_dashboard(s, start_date=None, end_date=None)
        assert dash["stats"]["total_units_all_time"] == legacy_total == 187
        assert dash["stats"]["total_units_all_time"] == sum_distribution_units(all_entries)


def test_multiline_entry_not_double_counted():
    e = SimpleNamespace(
        quantity=30,
        lines=[SimpleNamespace(quantity=10), SimpleNamespace(quantity=20)],
        sales_order_id=1,
    )
    assert sum_distribution_units([e]) == 30


def test_entry_without_lines_uses_entry_quantity():
    e = SimpleNamespace(quantity=12, lines=[], sales_order_id=None)
    assert sum_distribution_units([e]) == 12


def test_attach_orphan_records_audit_without_sales_order_link(app):
    with session_scope(app) as s:
        harbor = Customer(
            facility_name="Harbor UCLA Medical Center",
            company_key="1000CARSONSTW|CA|90509",
            customer_type="catheter",
            address1="1000 W Carson Street",
            city="Torrance",
            state="CA",
            zip="90509",
        )
        s.add(harbor)
        s.flush()
        orphan = _entry(
            ship_date=date(2026, 6, 1),
            order_number="SO 0000379",
            facility_name="HARBOR-UCLA MEDICAL CENTER",
            quantity=5,
            customer_id=None,
            sales_order_id=None,
            external_key="harbor-orphan",
        )
        orphan.address1 = "1000 W CARSON ST"
        orphan.city = "TORRANCE"
        orphan.state = "CA"
        orphan.zip = "90502-2059"
        s.add(orphan)
        s.flush()
        s.add(DistributionLine(distribution_entry_id=orphan.id, sku="211610SPT", lot_number="H", quantity=5))
        orphan_id = orphan.id
        harbor_id = harbor.id

        from app.eqms.modules.rep_traceability.service import find_unique_customer_for_distribution_ship_to

        found = find_unique_customer_for_distribution_ship_to(s, orphan)
        assert found.id == harbor_id

        preview = attach_distributions_to_customer(
            s,
            distribution_ids=[orphan_id],
            customer_id=harbor_id,
            execute=False,
        )
        assert preview["units_added"] == 5
        assert s.get(DistributionLogEntry, orphan_id).customer_id is None

        result = attach_distributions_to_customer(
            s,
            distribution_ids=[orphan_id],
            customer_id=harbor_id,
            execute=True,
        )
        s.flush()
        attached = s.get(DistributionLogEntry, orphan_id)
        assert attached.customer_id == harbor_id
        assert attached.sales_order_id is None
        assert result["units_after"] == 5

        ev = (
            s.query(AuditEvent)
            .filter(AuditEvent.action == "distribution.customer_attached")
            .filter(AuditEvent.entity_id == str(orphan_id))
            .one()
        )
        meta = json.loads(ev.metadata_json or "{}")
        assert meta["before"]["customer_id"] is None
        assert meta["after"]["customer_id"] == harbor_id
        assert meta["before"]["sales_order_id"] is None
        assert meta["after"]["sales_order_id"] is None


def test_shipstation_page_shows_reason_breakdown_and_new_label(app, client):
    _login(client)
    with session_scope(app) as s:
        s.add(
            ShipStationSyncRun(
                ran_at=date(2026, 8, 1),
                synced_count=1,
                skipped_count=2,
                orders_seen=3,
                shipments_seen=1,
                duration_seconds=1,
                message="Synced=1 not_yet_shipped=2.",
            )
        )
        s.add(ShipStationSkippedOrder(order_number="A1", reason="no_shipments"))
        s.add(ShipStationSkippedOrder(order_number="A2", reason="no_shipments"))
        s.add(ShipStationSkippedOrder(order_number="A3", reason="duplicate_external_key"))

    r = client.get("/admin/shipstation")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Not yet shipped" in body
    assert "Not-yet-shipped reason breakdown" in body
    assert "no_shipments" in body
    assert "duplicate_external_key" in body
    assert "are not errors" in body
    assert "Orders not yet shipped" in body
    assert LATENESS_WORDS.search(body) is None


def test_p4_07_wording_has_no_lateness():
    note = format_unmatched_units_note(unmatched_units=120, unmatched_entry_count=3)
    assert note is not None
    assert LATENESS_WORDS.search(note) is None
    assert "not yet matched" in note
