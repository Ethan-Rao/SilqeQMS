"""
P4-04 — NRE Invoice Tracker match + ShipStation probe bulk rewrite.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.models import NREProjectEntry, NRETrackerAttachment
from app.eqms.modules.nre_projects.service import (
    MatchError,
    PDF_TYPE_NRE_TRACKER_FILE,
    match_tracker_to_sales_order,
    unmatch_tracker_from_sales_order,
)
from app.eqms.modules.rep_traceability.models import OrderPdfAttachment, SalesOrder, SalesOrderLine
from app.eqms.modules.rep_traceability.order_type import (
    ORDER_TYPE_CLEARTRACT_IN_PROCESS,
    ORDER_TYPE_NRE_PROJECT,
    safe_apply_order_type,
)
from app.eqms.modules.shipstation_sync.models import ShipStationSkippedOrder, ShipStationSyncRun

PW = "pw"
PERMS = [
    "admin.view",
    "admin.edit",
    "sales_orders.view",
    "sales_orders.edit",
    "sales_orders.import",
    "customers.view",
    "shipstation.view",
    "shipstation.run",
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

        staff_role = Role(key="staff", name="Staff")
        for k in ("admin.view", "sales_orders.view", "shipstation.view"):
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


def _seed_nre_order(s, *, order_number="0000290", amount=None, nre_status="Pending Invoice", status="completed"):
    c = Customer(
        facility_name="NRE Co",
        company_key="nre-co",
        customer_type="nre",
    )
    s.add(c)
    s.flush()
    so = SalesOrder(
        order_number=order_number,
        order_date=date(2026, 3, 1),
        customer_id=c.id,
        source="pdf_import",
        status=status,
        order_type=ORDER_TYPE_NRE_PROJECT,
        order_amount=amount,
        nre_invoice_status=nre_status,
    )
    s.add(so)
    s.flush()
    return c, so


def _seed_entry(s, *, order_ref="0000290", amount=None, invoice_status="Pending Invoice", with_files=True):
    e = NREProjectEntry(
        entry_date=date(2026, 2, 1),
        customer_name="NRE Co",
        order_ref=order_ref,
        invoice_amount=amount,
        invoice_status=invoice_status,
    )
    s.add(e)
    s.flush()
    keys = []
    if with_files:
        for name, ctype in (
            ("notes.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("spec.pdf", "application/pdf"),
        ):
            key = f"nre/tracker_files/{e.id}/{name}"
            att = NRETrackerAttachment(
                nre_entry_id=e.id,
                filename=name,
                storage_key=key,
                content_type=ctype,
                size_bytes=12,
            )
            s.add(att)
            keys.append(key)
        s.flush()
    return e, keys


# --------------------------------------------------------------------------- #
# Match moves files
# --------------------------------------------------------------------------- #
def test_manual_match_moves_attachments_same_storage_key(app, client):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s, amount=Decimal("100.00"))
        e, keys = _seed_entry(s, amount=Decimal("100.00"))
        so_id, entry_id = so.id, e.id

    _login(client)
    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{so_id}/match-tracker",
        data={"csrf_token": token, "entry_id": entry_id},
        follow_redirects=True,
    )
    assert r.status_code == 200

    with session_scope(app) as s:
        e = s.get(NREProjectEntry, entry_id)
        assert e.sales_order_id == so_id
        assert s.query(NRETrackerAttachment).filter_by(nre_entry_id=entry_id).count() == 0
        moved = (
            s.query(OrderPdfAttachment)
            .filter_by(sales_order_id=so_id, pdf_type=PDF_TYPE_NRE_TRACKER_FILE)
            .all()
        )
        assert len(moved) == 2
        assert {a.storage_key for a in moved} == set(keys)
        assert any(a.content_type and "spreadsheet" in a.content_type for a in moved)
        aud = (
            s.query(AuditEvent)
            .filter_by(action="nre_tracker.matched_sales_order")
            .order_by(AuditEvent.id.desc())
            .first()
        )
        assert aud is not None


def test_delete_matched_entry_keeps_order_files(app):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s)
        e, keys = _seed_entry(s)
        match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
        so_id, entry_id = so.id, e.id
        s.flush()
        s.delete(e)
        s.flush()
        remaining = (
            s.query(OrderPdfAttachment)
            .filter_by(sales_order_id=so_id, pdf_type=PDF_TYPE_NRE_TRACKER_FILE)
            .all()
        )
        assert len(remaining) == 2
        assert {a.storage_key for a in remaining} == set(keys)
        assert s.get(NREProjectEntry, entry_id) is None


def test_reimport_does_not_delete_nre_tracker_file(app, client):
    from app.eqms.modules.rep_traceability.parsers.pdf import ParseResult

    with session_scope(app) as s:
        cust, so = _seed_nre_order(s, order_number="0000999")
        e, _ = _seed_entry(s, order_ref="0000999")
        match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
        page = OrderPdfAttachment(
            sales_order_id=so.id,
            distribution_entry_id=None,
            storage_key="sales_orders/0000999/pdfs/old.pdf",
            filename="SO_0000999.pdf",
            pdf_type="sales_order_page",
        )
        s.add(page)
        s.flush()
        so_id = so.id
        tracker_count_before = (
            s.query(OrderPdfAttachment)
            .filter_by(sales_order_id=so_id, pdf_type=PDF_TYPE_NRE_TRACKER_FILE)
            .count()
        )
        assert tracker_count_before == 2

    fake_result = ParseResult(
        orders=[
            {
                "order_number": "0000999",
                "order_date": date(2026, 3, 1),
                "ship_date": date(2026, 3, 2),
                "customer_name": "NRE Co",
                "customer_code": None,
                "lines": [],
                "ship_to_name": "NRE Co",
                "ship_to_address1": "1 Main",
                "ship_to_city": "Town",
                "ship_to_state": "CA",
                "ship_to_zip": "90001",
                "address1": "1 Main",
                "city": "Town",
                "state": "CA",
                "zip": "90001",
            }
        ],
        lines=[],
        labels=[],
        errors=[],
        total_rows_processed=1,
    )

    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.rep_traceability.parsers.pdf.split_pdf_into_pages",
        return_value=[(1, b"%PDF-1.4 fake")],
    ), patch(
        "app.eqms.modules.rep_traceability.parsers.pdf.parse_sales_orders_pdf",
        return_value=fake_result,
    ), patch(
        "app.eqms.modules.rep_traceability.admin.storage_from_config",
    ) as mock_storage_cfg:
        mock_storage = MagicMock()
        mock_storage.put_bytes.return_value = None
        mock_storage.delete.return_value = None
        mock_storage_cfg.return_value = mock_storage
        r = client.post(
            "/admin/sales-orders/import-pdf",
            data={"csrf_token": token, "pdf_file": (BytesIO(b"%PDF-1.4 fake"), "so.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert r.status_code == 200

    with session_scope(app) as s:
        tracker = (
            s.query(OrderPdfAttachment)
            .filter_by(sales_order_id=so_id, pdf_type=PDF_TYPE_NRE_TRACKER_FILE)
            .count()
        )
        assert tracker == 2


def test_moved_xlsx_served_with_own_content_type(app, client):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s)
        e, _ = _seed_entry(s)
        match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
        xlsx = (
            s.query(OrderPdfAttachment)
            .filter(
                OrderPdfAttachment.sales_order_id == so.id,
                OrderPdfAttachment.filename == "notes.xlsx",
            )
            .one()
        )
        att_id = xlsx.id

    _login(client)
    with patch("app.eqms.modules.rep_traceability.admin.storage_from_config") as cfg:
        mock_storage = MagicMock()
        mock_storage.open.return_value = BytesIO(b"xlsx-bytes")
        cfg.return_value = mock_storage
        r = client.get(f"/admin/sales-orders/pdf/{att_id}/download")
    assert r.status_code == 200
    assert "spreadsheet" in (r.mimetype or "")


# --------------------------------------------------------------------------- #
# Auto match both directions
# --------------------------------------------------------------------------- #
def test_auto_match_on_order_type_by_normalized_number(app):
    with session_scope(app) as s:
        c = Customer(facility_name="NRE Co", company_key="nre-co2", customer_type="nre")
        s.add(c)
        s.flush()
        so = SalesOrder(
            order_number="SO 0000290",
            order_date=date(2026, 3, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
            order_type=None,
        )
        s.add(so)
        s.flush()
        e, keys = _seed_entry(s, order_ref="0000290")
        safe_apply_order_type(s, so)
        s.flush()
        assert e.sales_order_id == so.id
        assert s.query(NRETrackerAttachment).count() == 0
        assert (
            s.query(OrderPdfAttachment)
            .filter_by(sales_order_id=so.id, pdf_type=PDF_TYPE_NRE_TRACKER_FILE)
            .count()
        ) == 2


def test_auto_match_on_tracker_create(app, client):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s, order_number="0000300")
        so_id = so.id

    _login(client)
    token = _csrf(client)
    r = client.post(
        "/admin/nre-projects/tracker/create",
        json={
            "entry_date": "2026-02-01",
            "customer_name": "NRE Co",
            "order_ref": "0000300",
            "invoice_amount": "50",
        },
        headers={"X-CSRF-Token": token},
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        e = s.query(NREProjectEntry).order_by(NREProjectEntry.id.desc()).first()
        assert e.sales_order_id == so_id


def test_no_match_on_customer_or_amount_alone(app):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s, order_number="0000400", amount=Decimal("999.00"))
        e, _ = _seed_entry(s, order_ref="0000401", amount=Decimal("999.00"), with_files=True)
        from app.eqms.modules.nre_projects.service import safe_auto_match_order, safe_auto_match_entry

        safe_auto_match_order(s, so)
        safe_auto_match_entry(s, e)
        s.flush()
        assert e.sales_order_id is None
        assert s.query(NRETrackerAttachment).filter_by(nre_entry_id=e.id).count() == 2


def test_match_refuses_non_nre_order(app):
    with session_scope(app) as s:
        c = Customer(facility_name="Catheter Co", company_key="cath", customer_type="catheter")
        s.add(c)
        s.flush()
        so = SalesOrder(
            order_number="0000500",
            order_date=date(2026, 1, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
            order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
        )
        s.add(so)
        s.flush()
        e, _ = _seed_entry(s, order_ref="0000500")
        with pytest.raises(MatchError):
            match_tracker_to_sales_order(s, entry=e, order=so, how="manual")


def test_match_idempotent(app):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s)
        e, _ = _seed_entry(s)
        match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
        match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
        s.flush()
        assert (
            s.query(OrderPdfAttachment)
            .filter_by(sales_order_id=so.id, pdf_type=PDF_TYPE_NRE_TRACKER_FILE)
            .count()
        ) == 2


# --------------------------------------------------------------------------- #
# Amount + status
# --------------------------------------------------------------------------- #
def test_amount_copy_and_disagreement(app):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s, amount=None)
        e, _ = _seed_entry(s, amount=Decimal("250.00"), with_files=False)
        meta = match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
        assert so.order_amount == Decimal("250.00")
        assert meta["amount"]["action"] == "copied_from_tracker"

        so2 = SalesOrder(
            order_number="0000291",
            order_date=date(2026, 3, 2),
            customer_id=so.customer_id,
            source="pdf_import",
            status="completed",
            order_type=ORDER_TYPE_NRE_PROJECT,
            order_amount=Decimal("100.00"),
            nre_invoice_status="Pending Invoice",
        )
        s.add(so2)
        s.flush()
        e2 = NREProjectEntry(
            entry_date=date(2026, 2, 2),
            order_ref="0000291",
            invoice_amount=Decimal("200.00"),
            invoice_status="Pending Invoice",
        )
        s.add(e2)
        s.flush()
        meta2 = match_tracker_to_sales_order(s, entry=e2, order=so2, how="manual")
        assert so2.order_amount == Decimal("100.00")
        assert e2.invoice_amount == Decimal("200.00")
        assert meta2["amount"]["action"] == "disagreement"


def test_status_mapping_all_values(app):
    cases = [
        ("Pending Invoice", "Pending Invoice", "completed"),
        ("50% Invoiced", "50% Invoiced", "completed"),
        ("Invoiced", "100% Invoiced", "completed"),
        ("Paid", "Payment Received", "completed"),
    ]
    with session_scope(app) as s:
        c = Customer(facility_name="Map Co", company_key="map", customer_type="nre")
        s.add(c)
        s.flush()
        for i, (tracker_st, expect_dash, expect_status) in enumerate(cases):
            so = SalesOrder(
                order_number=f"M{i}",
                order_date=date(2026, 1, 1),
                customer_id=c.id,
                source="pdf_import",
                status="completed",
                order_type=ORDER_TYPE_NRE_PROJECT,
                nre_invoice_status="Pending Invoice",
            )
            s.add(so)
            s.flush()
            e = NREProjectEntry(
                order_ref=f"M{i}",
                invoice_status=tracker_st,
                entry_date=date(2026, 1, 1),
            )
            s.add(e)
            s.flush()
            match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
            assert so.nre_invoice_status == expect_dash
            assert so.status == expect_status

        so_c = SalesOrder(
            order_number="MC",
            order_date=date(2026, 1, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
            order_type=ORDER_TYPE_NRE_PROJECT,
            nre_invoice_status="Pending Invoice",
        )
        s.add(so_c)
        s.flush()
        e_c = NREProjectEntry(order_ref="MC", invoice_status="Cancelled", entry_date=date(2026, 1, 1))
        s.add(e_c)
        s.flush()
        match_tracker_to_sales_order(s, entry=e_c, order=so_c, how="manual")
        assert so_c.status == "cancelled"

        so_u = SalesOrder(
            order_number="MU",
            order_date=date(2026, 1, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
            order_type=ORDER_TYPE_NRE_PROJECT,
            nre_invoice_status="Pending Invoice",
        )
        s.add(so_u)
        s.flush()
        e_u = NREProjectEntry(order_ref="MU", invoice_status="Weird Free Text", entry_date=date(2026, 1, 1))
        s.add(e_u)
        s.flush()
        meta = match_tracker_to_sales_order(s, entry=e_u, order=so_u, how="manual")
        assert so_u.nre_invoice_status == "Pending Invoice"
        assert meta["status"]["action"] == "unrecognized_tracker_status"


def test_operator_status_not_overwritten(app):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s, nre_status="100% Invoiced")
        e, _ = _seed_entry(s, invoice_status="Paid", with_files=False)
        meta = match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
        assert so.nre_invoice_status == "100% Invoiced"
        assert meta["status"]["applied"] is False


def test_upcoming_filter_and_totals_separate(app, client):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s, order_number="0000600", amount=Decimal("1000.00"))
        e_matched, _ = _seed_entry(s, order_ref="0000600", amount=Decimal("1000.00"), with_files=False)
        match_tracker_to_sales_order(s, entry=e_matched, order=so, how="manual")
        e_open = NREProjectEntry(
            entry_date=date(2026, 4, 1),
            customer_name="Forecast Co",
            order_ref="FUTURE1",
            invoice_amount=Decimal("500.00"),
            invoice_status="Pending Invoice",
        )
        s.add(e_open)

    _login(client)
    body = client.get("/admin/nre-projects/?start=2026-01-01&end=2026-12-31").get_data(as_text=True)
    assert "FUTURE1" in body
    assert "0000600" in body  # on dashboard as sales order
    # Matched entry leaves Upcoming: order_ref cell for matched entry gone from tracker table section
    # Expected forecast shows 500
    assert "Expected (unmatched)" in body
    assert "500" in body


def test_unmatch_returns_files(app, client):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s)
        e, keys = _seed_entry(s)
        match_tracker_to_sales_order(s, entry=e, order=so, how="manual")
        entry_id, so_id = e.id, so.id

    _login(client)
    token = _csrf(client)
    r = client.post(
        f"/admin/nre-projects/tracker/{entry_id}/unmatch",
        data={
            "csrf_token": token,
            "next": f"/admin/sales-orders/{so_id}",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        e = s.get(NREProjectEntry, entry_id)
        assert e.sales_order_id is None
        assert s.query(NRETrackerAttachment).filter_by(nre_entry_id=entry_id).count() == 2
        assert (
            s.query(OrderPdfAttachment)
            .filter_by(sales_order_id=so_id, pdf_type=PDF_TYPE_NRE_TRACKER_FILE)
            .count()
        ) == 0
        returned = s.query(NRETrackerAttachment).filter_by(nre_entry_id=entry_id).all()
        assert {a.storage_key for a in returned} == set(keys)


def test_match_failure_does_not_abort_apply_order_type(app):
    with session_scope(app) as s:
        c = Customer(facility_name="Safe Co", company_key="safe", customer_type="nre")
        s.add(c)
        s.flush()
        so = SalesOrder(
            order_number="0000700",
            order_date=date(2026, 1, 1),
            customer_id=c.id,
            source="pdf_import",
            status="completed",
            order_type=None,
        )
        s.add(so)
        s.flush()
        s.add(SalesOrderLine(sales_order_id=so.id, sku="NRE-1", quantity=1, line_number=1))
        s.flush()

        with patch(
            "app.eqms.modules.nre_projects.service.match_tracker_to_sales_order",
            side_effect=RuntimeError("boom"),
        ):
            # Force a path that would call match: seed an unmatched entry with same number
            e = NREProjectEntry(order_ref="0000700", entry_date=date(2026, 1, 1))
            s.add(e)
            s.flush()
            safe_apply_order_type(s, so)
        s.flush()
        # Classification still applied despite match boom (wrapped)
        assert so.order_type == ORDER_TYPE_NRE_PROJECT


def test_match_routes_permission_and_csrf(client, app):
    with session_scope(app) as s:
        _, so = _seed_nre_order(s)
        e, _ = _seed_entry(s, with_files=False)
        so_id, entry_id = so.id, e.id

    _login(client, email="staff@silq.tech")
    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{so_id}/match-tracker",
        data={"csrf_token": token, "entry_id": entry_id},
    )
    assert r.status_code == 403
    r = client.post(
        f"/admin/nre-projects/tracker/{entry_id}/match",
        data={"csrf_token": token, "sales_order_id": so_id},
    )
    assert r.status_code == 403

    _login(client)
    r = client.post(
        f"/admin/sales-orders/{so_id}/match-tracker",
        data={"entry_id": entry_id},
    )
    assert r.status_code == 400
    r = client.post(
        f"/admin/nre-projects/tracker/{entry_id}/unmatch",
        data={},
    )
    assert r.status_code == 400


# --------------------------------------------------------------------------- #
# Probe addendum
# --------------------------------------------------------------------------- #
class _CountingClient:
    def __init__(self, *, orders=None, shipments=None, sleep_s=0):
        self.calls = 0
        self._orders = orders or []
        self._shipments = shipments or []
        self._sleep_s = sleep_s

    def list_orders(self, **kwargs):
        self.calls += 1
        if self._sleep_s:
            import time

            time.sleep(self._sleep_s)
        page = kwargs.get("page") or 1
        if page == 1:
            return list(self._orders)
        return []

    def list_shipments_by_date(self, **kwargs):
        self.calls += 1
        page = kwargs.get("page") or 1
        if page == 1:
            return list(self._shipments)
        return []


def _seed_in_process(s, n: int):
    c = Customer(facility_name="IP Co", company_key=f"ip-{n}", customer_type="catheter")
    s.add(c)
    s.flush()
    ids = []
    for i in range(n):
        so = SalesOrder(
            order_number=f"{1000 + i:07d}",
            order_date=date(2025, 1, 8),
            customer_id=c.id,
            source="manual",
            status="pending",
            order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
        )
        s.add(so)
        s.flush()
        ids.append(so.id)
    return ids


def test_probe_api_calls_bounded_not_scaling(app, client, monkeypatch):
    monkeypatch.setenv("SHIPSTATION_API_KEY", "k")
    monkeypatch.setenv("SHIPSTATION_API_SECRET", "s")

    stub = _CountingClient(
        orders=[{"orderId": "1", "orderNumber": "0001000", "orderStatus": "awaiting_shipment"}],
        shipments=[],
    )
    with session_scope(app) as s:
        _seed_in_process(s, 3)

    _login(client)
    with patch(
        "app.eqms.modules.shipstation_sync.shipstation_client.ShipStationClient",
        return_value=stub,
    ):
        r = client.get("/admin/shipstation/probe-in-process")
    assert r.status_code == 200
    calls_3 = stub.calls

    stub2 = _CountingClient(
        orders=[{"orderId": "1", "orderNumber": "0001000", "orderStatus": "awaiting_shipment"}],
        shipments=[],
    )
    with session_scope(app) as s:
        # add more in-process orders
        c = s.query(Customer).filter_by(company_key="ip-3").one()
        for i in range(27):
            s.add(
                SalesOrder(
                    order_number=f"{2000 + i:07d}",
                    order_date=date(2025, 2, 1),
                    customer_id=c.id,
                    source="manual",
                    status="pending",
                    order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
                )
            )

    with patch(
        "app.eqms.modules.shipstation_sync.shipstation_client.ShipStationClient",
        return_value=stub2,
    ):
        r = client.get("/admin/shipstation/probe-in-process")
    assert r.status_code == 200
    assert stub2.calls == calls_3
    assert stub2.calls == 2  # one orders page + one shipments page


def test_probe_resolves_normalized_order_number(app, client, monkeypatch):
    monkeypatch.setenv("SHIPSTATION_API_KEY", "k")
    monkeypatch.setenv("SHIPSTATION_API_SECRET", "s")
    with session_scope(app) as s:
        c = Customer(facility_name="IP", company_key="ip-norm", customer_type="catheter")
        s.add(c)
        s.flush()
        s.add(
            SalesOrder(
                order_number="0000290",
                order_date=date(2025, 1, 8),
                customer_id=c.id,
                source="manual",
                status="pending",
                order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
            )
        )

    stub = _CountingClient(
        orders=[{"orderId": "99", "orderNumber": "SO 0000290", "orderStatus": "shipped"}],
        shipments=[
            {"orderId": "99", "orderNumber": "SO 0000290", "trackingNumber": "1Z"},
        ],
    )
    _login(client)
    with patch(
        "app.eqms.modules.shipstation_sync.shipstation_client.ShipStationClient",
        return_value=stub,
    ):
        r = client.get("/admin/shipstation/probe-in-process")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "yes" in body
    assert "1Z" in body


def test_probe_three_bucket_summary(app, client, monkeypatch):
    monkeypatch.setenv("SHIPSTATION_API_KEY", "k")
    monkeypatch.setenv("SHIPSTATION_API_SECRET", "s")
    with session_scope(app) as s:
        c = Customer(facility_name="IP", company_key="ip-b", customer_type="catheter")
        s.add(c)
        s.flush()
        for num in ("0000001", "0000002", "0000003"):
            s.add(
                SalesOrder(
                    order_number=num,
                    order_date=date(2025, 1, 8),
                    customer_id=c.id,
                    source="manual",
                    status="pending",
                    order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
                )
            )

    stub = _CountingClient(
        orders=[
            {"orderId": "1", "orderNumber": "0000001", "orderStatus": "shipped"},
            {"orderId": "2", "orderNumber": "0000002", "orderStatus": "awaiting_shipment"},
        ],
        shipments=[{"orderId": "1", "orderNumber": "0000001", "trackingNumber": "T1"}],
    )
    _login(client)
    with patch(
        "app.eqms.modules.shipstation_sync.shipstation_client.ShipStationClient",
        return_value=stub,
    ):
        r = client.get("/admin/shipstation/probe-in-process")
    assert r.status_code == 200
    # with_shipments=1, with_order_no_ship=1, no_order=1 — cards show counts
    body = r.get_data(as_text=True)
    assert ">1<" in body


def test_probe_time_budget_partial(app, client, monkeypatch):
    monkeypatch.setenv("SHIPSTATION_API_KEY", "k")
    monkeypatch.setenv("SHIPSTATION_API_SECRET", "s")
    with session_scope(app) as s:
        _seed_in_process(s, 2)

    _login(client)
    times = [0.0]

    def fake_monotonic():
        times[0] += 30.0
        return times[0]

    with patch("time.monotonic", side_effect=fake_monotonic), patch(
        "app.eqms.modules.shipstation_sync.shipstation_client.ShipStationClient",
        return_value=_CountingClient(
            orders=[{"orderId": "1", "orderNumber": "0001000", "orderStatus": "x"}],
            shipments=[],
        ),
    ):
        r = client.get("/admin/shipstation/probe-in-process")
    assert r.status_code == 200
    assert b"Partial" in r.data or b"partial" in r.data


def test_probe_no_writes(app, client, monkeypatch):
    monkeypatch.setenv("SHIPSTATION_API_KEY", "k")
    monkeypatch.setenv("SHIPSTATION_API_SECRET", "s")
    with session_scope(app) as s:
        _seed_in_process(s, 1)
        before_runs = s.query(ShipStationSyncRun).count()
        before_skip = s.query(ShipStationSkippedOrder).count()

    stub = _CountingClient(orders=[], shipments=[])
    _login(client)
    with patch(
        "app.eqms.modules.shipstation_sync.shipstation_client.ShipStationClient",
        return_value=stub,
    ):
        r = client.get("/admin/shipstation/probe-in-process")
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.query(ShipStationSyncRun).count() == before_runs
        assert s.query(ShipStationSkippedOrder).count() == before_skip


def test_probe_without_creds_shows_skipped_and_window(app, client):
    with session_scope(app) as s:
        _seed_in_process(s, 1)
        s.add(
            ShipStationSkippedOrder(
                order_id="584051980",
                order_number="0001000",
                reason="no_shipments",
            )
        )

    _login(client)
    r = client.get("/admin/shipstation/probe-in-process")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "credentials" in body.lower()
    assert "Probe window" in body
    assert "Routine sync window" in body
    assert "no_shipments" in body
