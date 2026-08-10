"""
P4-01 — Explicit sales-order type, NRE classification, re-import data-loss fixes.
"""
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.admin import _nre_customers
from app.eqms.modules.rep_traceability.models import (
    DistributionLogEntry,
    OrderPdfAttachment,
    SalesOrder,
    SalesOrderLine,
)
from app.eqms.modules.rep_traceability.order_type import (
    ORDER_TYPE_CLEARTRACT_DELIVERY,
    ORDER_TYPE_CLEARTRACT_DISTRIBUTION,
    ORDER_TYPE_CLEARTRACT_IN_PROCESS,
    ORDER_TYPE_NRE_PROJECT,
    apply_order_type,
    classify_order_type,
    set_order_type_manual,
)
from app.eqms.modules.rep_traceability.parsers.pdf import ParseResult
from app.eqms.modules.rep_traceability.service import (
    create_distribution_entry,
    delete_distribution_entry,
)

PW = "pw"
PERMS = [
    "admin.view", "admin.edit",
    "sales_orders.view", "sales_orders.edit", "sales_orders.import",
    "customers.view", "distribution_log.view", "distribution_log.edit",
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


def _make_order(s, *, num="1001", cust=None, lines=None, order_type=None):
    if cust is None:
        cust = Customer(facility_name="Test Co", company_key=f"key-{num}", customer_type="auto")
        s.add(cust)
        s.flush()
    so = SalesOrder(
        order_number=num,
        order_date=date(2026, 1, 15),
        customer_id=cust.id,
        source="pdf_import",
        status="completed",
        order_type=order_type,
    )
    s.add(so)
    s.flush()
    for i, (sku, qty) in enumerate(lines or [], start=1):
        s.add(SalesOrderLine(sales_order_id=so.id, sku=sku, quantity=qty, line_number=i))
    s.flush()
    return so, cust


# --------------------------------------------------------------------------- #
# classify / apply / set
# --------------------------------------------------------------------------- #
def test_classify_shipstation_distribution(app):
    with session_scope(app) as s:
        so, _ = _make_order(s, num="C1")
        s.add(
            DistributionLogEntry(
                ship_date=date(2026, 1, 16),
                order_number="C1",
                facility_name="F",
                sku="211610SPT",
                lot_number="L1",
                quantity=1,
                source="shipstation",
                sales_order_id=so.id,
            )
        )
        s.flush()
        assert classify_order_type(s, so) == (ORDER_TYPE_CLEARTRACT_DISTRIBUTION, False)


def test_classify_manual_distribution(app):
    with session_scope(app) as s:
        so, _ = _make_order(s, num="C2")
        s.add(
            DistributionLogEntry(
                ship_date=date(2026, 1, 16),
                order_number="C2",
                facility_name="F",
                sku="211610SPT",
                lot_number="L1",
                quantity=1,
                source="manual",
                sales_order_id=so.id,
            )
        )
        s.flush()
        assert classify_order_type(s, so) == (ORDER_TYPE_CLEARTRACT_DELIVERY, False)


def test_classify_catheter_sku_no_distribution(app):
    with session_scope(app) as s:
        so, _ = _make_order(s, num="C3", lines=[("211610SPT", 2)])
        assert classify_order_type(s, so) == (ORDER_TYPE_CLEARTRACT_IN_PROCESS, False)


def test_classify_nre_no_lines_no_distribution(app):
    with session_scope(app) as s:
        so, _ = _make_order(s, num="C4")
        assert classify_order_type(s, so) == (ORDER_TYPE_NRE_PROJECT, True)


def test_classify_nre_non_catheter_lines(app):
    with session_scope(app) as s:
        so, _ = _make_order(s, num="C5", lines=[("CUSTOM-PART", 1)])
        assert classify_order_type(s, so) == (ORDER_TYPE_NRE_PROJECT, True)


def test_apply_skips_manual(app):
    with session_scope(app) as s:
        so, _ = _make_order(s, num="C6", order_type=ORDER_TYPE_NRE_PROJECT)
        so.order_type_is_manual = True
        so.order_type_needs_review = False
        s.flush()
        s.add(
            DistributionLogEntry(
                ship_date=date(2026, 1, 16),
                order_number="C6",
                facility_name="F",
                sku="211610SPT",
                lot_number="L1",
                quantity=1,
                source="shipstation",
                sales_order_id=so.id,
            )
        )
        s.flush()
        changed = apply_order_type(s, so)
        assert changed is False
        assert so.order_type == ORDER_TYPE_NRE_PROJECT


def test_set_order_type_manual(app):
    with app.app_context():
        with session_scope(app) as s:
            so, _ = _make_order(s, num="C7")
            so.order_type_needs_review = True
            admin = s.query(User).filter_by(email="admin@silq.tech").one()
            set_order_type_manual(s, so, ORDER_TYPE_CLEARTRACT_DELIVERY, user=admin)
            assert so.order_type == ORDER_TYPE_CLEARTRACT_DELIVERY
            assert so.order_type_is_manual is True
            assert so.order_type_needs_review is False
            with pytest.raises(ValueError):
                set_order_type_manual(s, so, "not_a_type", user=admin)


def test_link_and_unlink_distribution_flips_type(app):
    with app.app_context():
        with session_scope(app) as s:
            so, cust = _make_order(s, num="C8", lines=[("211610SPT", 1)])
            apply_order_type(s, so)
            assert so.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS
            assert so.order_type_needs_review is False

            admin = s.query(User).filter_by(email="admin@silq.tech").one()
            entry = create_distribution_entry(
                s,
                {
                    "ship_date": "2026-01-20",
                    "order_number": "C8",
                    "facility_name": cust.facility_name,
                    "customer_id": str(cust.id),
                    "sku": "211610SPT",
                    "lot_number": "L9",
                    "quantity": 1,
                    "sales_order_id": str(so.id),
                },
                user=admin,
                source_default="manual",
            )
            assert so.order_type == ORDER_TYPE_CLEARTRACT_DELIVERY
            assert so.order_type_needs_review is False

            delete_distribution_entry(s, entry, user=admin, reason="test")
            assert so.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS


def test_nre_dashboard_uses_order_type_not_customer_type(app):
    with session_scope(app) as s:
        nre_cust = Customer(
            facility_name="NRE Cust", company_key="NREC", customer_type="catheter"
        )
        cath_cust = Customer(
            facility_name="Cath Cust", company_key="CATHC", customer_type="catheter"
        )
        s.add_all([nre_cust, cath_cust])
        s.flush()
        so_nre = SalesOrder(
            order_number="N1",
            order_date=date(2026, 1, 1),
            customer_id=nre_cust.id,
            source="pdf_import",
            status="completed",
            order_type=ORDER_TYPE_NRE_PROJECT,
        )
        so_cath = SalesOrder(
            order_number="N2",
            order_date=date(2026, 1, 1),
            customer_id=cath_cust.id,
            source="pdf_import",
            status="completed",
            order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
        )
        s.add_all([so_nre, so_cath])
        s.flush()

        names = {c.facility_name for c in _nre_customers(s)}
        assert "NRE Cust" in names
        assert "Cath Cust" not in names


# --------------------------------------------------------------------------- #
# Re-import regressions
# --------------------------------------------------------------------------- #
def _order_data(order_number, customer_name, lines=None):
    return {
        "order_number": order_number,
        "order_date": date(2026, 2, 1),
        "ship_date": date(2026, 2, 2),
        "customer_name": customer_name,
        "customer_code": None,
        "lines": lines or [],
        "ship_to_name": customer_name,
        "ship_to_address1": "1 Main",
        "ship_to_city": "Austin",
        "ship_to_state": "TX",
        "ship_to_zip": "78701",
        "address1": "1 Main",
        "city": "Austin",
        "state": "TX",
        "zip": "78701",
    }


def test_reimport_preserves_packing_slip(client, app):
    with session_scope(app) as s:
        cust = Customer(
            facility_name="Keep Me Facility",
            company_key="KEEPME",
            customer_type="catheter",
            address1="1 Main",
            city="Austin",
            state="TX",
            zip="78701",
        )
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="0000999",
            order_date=date(2026, 1, 1),
            customer_id=cust.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()
        dist = DistributionLogEntry(
            ship_date=date(2026, 1, 2),
            order_number="0000999",
            facility_name=cust.facility_name,
            sku="211610SPT",
            lot_number="LOT1",
            quantity=1,
            source="manual",
            sales_order_id=so.id,
            customer_id=cust.id,
        )
        s.add(dist)
        s.flush()
        page_att = OrderPdfAttachment(
            sales_order_id=so.id,
            distribution_entry_id=None,
            storage_key="sales_orders/0000999/pdfs/sales_order_page_old.pdf",
            filename="SO_0000999.pdf",
            pdf_type="sales_order_page",
        )
        slip_att = OrderPdfAttachment(
            sales_order_id=so.id,
            distribution_entry_id=dist.id,
            storage_key="sales_orders/0000999/pdfs/packing_slip.pdf",
            filename="packing.pdf",
            pdf_type="packing_slip",
        )
        s.add_all([page_att, slip_att])
        s.flush()
        so_id, slip_id, page_id = so.id, slip_att.id, page_att.id

    fake_result = ParseResult(
        orders=[_order_data("0000999", "Keep Me Facility", lines=[{"sku": "211610SPT", "quantity": 2}])],
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
            data={
                "csrf_token": token,
                "pdf_file": (BytesIO(b"%PDF-1.4 fake"), "so.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert r.status_code == 200

    with session_scope(app) as s:
        assert s.get(OrderPdfAttachment, slip_id) is not None
        assert s.get(OrderPdfAttachment, page_id) is None
        remaining = (
            s.query(OrderPdfAttachment)
            .filter(OrderPdfAttachment.sales_order_id == so_id)
            .all()
        )
        types = {a.pdf_type for a in remaining}
        assert "packing_slip" in types
        assert "sales_order_page" in types


def test_reimport_does_not_repoint_customer(client, app):
    with session_scope(app) as s:
        stored = Customer(
            facility_name="Original Customer",
            company_key="ORIGCUST",
            customer_type="nre",
        )
        s.add(stored)
        s.flush()
        so = SalesOrder(
            order_number="0000888",
            order_date=date(2026, 1, 1),
            customer_id=stored.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()
        so_id, stored_id = so.id, stored.id

    # Different ship-to identity so find_or_create makes a different facility customer
    fake_result = ParseResult(
        orders=[
            _order_data(
                "0000888",
                "Different Name",
                lines=[],
            )
        ],
        lines=[],
        labels=[],
        errors=[],
        total_rows_processed=1,
    )
    # Empty lines => catheter path for customer identity; change ship-to address
    fake_result.orders[0]["ship_to_address1"] = "999 Other St"
    fake_result.orders[0]["ship_to_city"] = "Dallas"
    fake_result.orders[0]["ship_to_state"] = "TX"
    fake_result.orders[0]["ship_to_zip"] = "75201"

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
            data={
                "csrf_token": token,
                "pdf_file": (BytesIO(b"%PDF-1.4 fake"), "so.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert r.status_code == 200

    with session_scope(app) as s:
        so = s.get(SalesOrder, so_id)
        assert so.customer_id == stored_id


def test_order_type_post_requires_edit_and_csrf(client, app):
    with session_scope(app) as s:
        so, _ = _make_order(s, num="POST1", order_type=ORDER_TYPE_NRE_PROJECT)
        oid = so.id

    # Staff has view only -> 403 on edit permission (after valid CSRF)
    _login(client, email="staff@silq.tech")
    token = _csrf(client)
    r = client.post(
        f"/admin/sales-orders/{oid}/order-type",
        data={"order_type": ORDER_TYPE_CLEARTRACT_DELIVERY, "csrf_token": token},
    )
    assert r.status_code == 403

    # Admin missing CSRF -> 400
    _login(client, email="admin@silq.tech")
    r = client.post(
        f"/admin/sales-orders/{oid}/order-type",
        data={"order_type": ORDER_TYPE_CLEARTRACT_DELIVERY},
    )
    assert r.status_code == 400
