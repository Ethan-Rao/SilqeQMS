"""P4-08B — Distribution cleanup: import guards, filename, units, shared storage."""
import json
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import (
    DistributionLine,
    DistributionLogEntry,
    OrderPdfAttachment,
    SalesOrder,
    SalesOrderLine,
)
from app.eqms.modules.rep_traceability.order_type import (
    ORDER_TYPE_CLEARTRACT_DELIVERY,
    ORDER_TYPE_CLEARTRACT_IN_PROCESS,
)
from app.eqms.modules.rep_traceability.parsers.pdf import ParseResult
from app.eqms.modules.rep_traceability.service import (
    create_distribution_entry,
    delete_distribution_entry,
    packing_slip_display_filename,
    sales_order_tab_units,
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
    "distribution_log.create",
    "distribution_log.delete",
    "distribution_log.import",
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


def _login(client, email="admin@silq.tech"):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets

    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


def _user(s) -> User:
    return s.query(User).filter(User.email == "admin@silq.tech").one()


def _order_data(num, name, lines):
    return {
        "order_number": num,
        "order_date": date(2026, 5, 19),
        "customer_name": name,
        "customer_code": None,
        "ship_date": date(2026, 5, 19),
        "lines": lines,
        "ship_to_name": name,
        "ship_to_address1": "1 Harbor",
        "ship_to_city": "Torrance",
        "ship_to_state": "CA",
        "ship_to_zip": "90502",
        "address1": "1 Harbor",
        "city": "Torrance",
        "state": "CA",
        "zip": "90502",
    }


def test_packing_slip_import_matches_order_and_keeps_so_pdf(app, client):
    with session_scope(app) as s:
        cust = Customer(
            facility_name="Harbor UCLA",
            company_key="HARBOR08B",
            customer_type="catheter",
        )
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="0000336",
            order_date=date(2026, 5, 19),
            customer_id=cust.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()
        dist = DistributionLogEntry(
            ship_date=date(2026, 5, 19),
            order_number="0000336",
            facility_name=cust.facility_name,
            sku="211610SPT",
            lot_number="SLQ-05012025",
            quantity=30,
            source="shipstation",
            sales_order_id=so.id,
            customer_id=cust.id,
        )
        s.add(dist)
        s.flush()
        so_pdf = OrderPdfAttachment(
            sales_order_id=so.id,
            distribution_entry_id=None,
            storage_key="sales_orders/0000336/pdfs/SO_0000336.pdf",
            filename="SO_0000336.pdf",
            pdf_type="sales_order_page",
        )
        s.add(so_pdf)
        s.flush()
        so_id, dist_id, so_pdf_id = so.id, dist.id, so_pdf.id

    fake = ParseResult(
        orders=[],
        lines=[],
        labels=[{"order_number": "0000336", "tracking_number": None, "ship_to": "Harbor", "ss_shipment_id": None}],
        errors=[],
        total_rows_processed=1,
    )
    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.rep_traceability.parsers.pdf.split_pdf_into_pages",
        return_value=[(1, b"%PDF-1.4 slip")],
    ), patch(
        "app.eqms.modules.rep_traceability.parsers.pdf.parse_sales_orders_pdf",
        return_value=fake,
    ), patch(
        "app.eqms.modules.rep_traceability.admin.storage_from_config",
    ) as mock_storage_cfg:
        mock_storage = MagicMock()
        mock_storage.put_bytes.return_value = None
        mock_storage.delete.return_value = None
        mock_storage_cfg.return_value = mock_storage
        r = client.post(
            "/admin/packing-slips/import-bulk",
            data={"csrf_token": token, "pdf_files": (BytesIO(b"%PDF-1.4 slip"), "May26PackingSlips.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert r.status_code == 200

    with session_scope(app) as s:
        assert s.get(OrderPdfAttachment, so_pdf_id) is not None
        slips = (
            s.query(OrderPdfAttachment)
            .filter(
                OrderPdfAttachment.distribution_entry_id == dist_id,
                OrderPdfAttachment.pdf_type == "packing_slip",
            )
            .all()
        )
        assert len(slips) == 1
        assert s.get(OrderPdfAttachment, so_pdf_id).pdf_type == "sales_order_page"
        assert s.get(SalesOrder, so_id).order_number == "0000336"


def test_reimport_does_not_delete_packing_slip_or_manual_upload(app, client):
    with session_scope(app) as s:
        cust = Customer(
            facility_name="Keep Slip Facility",
            company_key="KEEPSLIP08B",
            customer_type="catheter",
            address1="1 Main",
            city="Austin",
            state="TX",
            zip="78701",
        )
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="0000998",
            order_date=date(2026, 1, 1),
            customer_id=cust.id,
            source="pdf_import",
            status="completed",
        )
        s.add(so)
        s.flush()
        dist = DistributionLogEntry(
            ship_date=date(2026, 1, 2),
            order_number="0000998",
            facility_name=cust.facility_name,
            sku="211610SPT",
            lot_number="SLQ-05012025",
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
            storage_key="sales_orders/0000998/pdfs/old_page.pdf",
            filename="SO_0000998.pdf",
            pdf_type="sales_order_page",
        )
        slip_att = OrderPdfAttachment(
            sales_order_id=so.id,
            distribution_entry_id=dist.id,
            storage_key="sales_orders/0000998/pdfs/slip.pdf",
            filename="slip.pdf",
            pdf_type="packing_slip",
        )
        photo_att = OrderPdfAttachment(
            sales_order_id=so.id,
            distribution_entry_id=dist.id,
            storage_key="sales_orders/0000998/pdfs/photo.jpg",
            filename="trunk.jpg",
            pdf_type="delivery_verification",
        )
        s.add_all([page_att, slip_att, photo_att])
        s.flush()
        so_id, slip_id, photo_id, page_id = so.id, slip_att.id, photo_att.id, page_att.id

    fake = ParseResult(
        orders=[_order_data("0000998", "Keep Slip Facility", [{"sku": "211610SPT", "quantity": 2}])],
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
        return_value=fake,
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
        assert s.get(OrderPdfAttachment, slip_id) is not None
        assert s.get(OrderPdfAttachment, photo_id) is not None
        assert s.get(OrderPdfAttachment, page_id) is None
        types = {
            a.pdf_type
            for a in s.query(OrderPdfAttachment).filter(OrderPdfAttachment.sales_order_id == so_id).all()
        }
        assert "packing_slip" in types
        assert "delivery_verification" in types
        assert "sales_order_page" in types


def test_packing_slip_display_filename_d65():
    assert (
        packing_slip_display_filename("Harbor UCLA", date(2026, 5, 19), "0000336")
        == "HarborUCLA_2026-05-19_SO0000336.pdf"
    )
    existing = {"HarborUCLA_2026-05-19_SO0000336.pdf"}
    assert (
        packing_slip_display_filename("Harbor UCLA", date(2026, 5, 19), "336", existing=existing)
        == "HarborUCLA_2026-05-19_SO0000336_2.pdf"
    )


def test_manual_distribution_moves_in_process_to_delivery(app):
    with session_scope(app) as s:
        cust = Customer(
            facility_name="Day Kimball",
            company_key="DK08B",
            customer_type="catheter",
        )
        s.add(cust)
        s.flush()
        so = SalesOrder(
            order_number="0000366",
            order_date=date(2026, 7, 7),
            customer_id=cust.id,
            source="pdf_import",
            status="pending",
            order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
        )
        s.add(so)
        s.flush()
        s.add(SalesOrderLine(sales_order_id=so.id, sku="211610SPT", quantity=4, line_number=1))
        s.flush()
        user = _user(s)
        create_distribution_entry(
            s,
            {
                "ship_date": date(2026, 7, 7),
                "order_number": "0000366",
                "facility_name": cust.facility_name,
                "customer_id": cust.id,
                "sales_order_id": so.id,
                "sku": "211610SPT",
                "lot_number": "SLQ-05012025",
                "quantity": 4,
            },
            user=user,
            source_default="manual",
        )
        s.flush()
        refreshed = s.get(SalesOrder, so.id)
        assert refreshed.order_type == ORDER_TYPE_CLEARTRACT_DELIVERY


def test_delete_duplicate_keeps_shared_storage_object(app):
    with app.app_context():
      with session_scope(app) as s:
        cust = Customer(facility_name="Harbor UCLA", company_key="HARBDEL08B", customer_type="catheter")
        s.add(cust)
        s.flush()
        keep = DistributionLogEntry(
            ship_date=date(2025, 11, 1),
            order_number="0000302",
            facility_name=cust.facility_name,
            sku="211610SPT",
            lot_number="SLQ-05012025",
            quantity=30,
            source="shipstation",
            customer_id=cust.id,
        )
        drop = DistributionLogEntry(
            ship_date=date(2025, 11, 1),
            order_number="0000302",
            facility_name=cust.facility_name,
            sku="211610SPT",
            lot_number="SLQ-05012025",
            quantity=30,
            source="shipstation",
            customer_id=cust.id,
        )
        s.add_all([keep, drop])
        s.flush()
        shared_key = "sales_orders/0000302/pdfs/shared_slip.pdf"
        s.add_all(
            [
                OrderPdfAttachment(
                    distribution_entry_id=keep.id,
                    storage_key=shared_key,
                    filename="keep.pdf",
                    pdf_type="packing_slip",
                ),
                OrderPdfAttachment(
                    distribution_entry_id=drop.id,
                    storage_key=shared_key,
                    filename="drop.pdf",
                    pdf_type="packing_slip",
                ),
            ]
        )
        s.flush()
        keep_id, drop_id = keep.id, drop.id
        user = _user(s)
        with patch("app.eqms.modules.rep_traceability.service.storage_from_config") as mock_cfg:
            mock_storage = MagicMock()
            mock_cfg.return_value = mock_storage
            delete_distribution_entry(s, drop, user=user, reason="P4-08B duplicate")
            s.flush()
            deleted_keys = [c.args[0] for c in mock_storage.delete.call_args_list]
            assert shared_key not in deleted_keys
        assert s.get(DistributionLogEntry, drop_id) is None
        assert s.get(DistributionLogEntry, keep_id) is not None
        surviving = (
            s.query(OrderPdfAttachment)
            .filter(OrderPdfAttachment.distribution_entry_id == keep_id)
            .one()
        )
        assert surviving.storage_key == shared_key
        ev = (
            s.query(AuditEvent)
            .filter(
                AuditEvent.action == "distribution_log_entry.delete",
                AuditEvent.entity_id == str(drop_id),
            )
            .one()
        )
        meta = json.loads(ev.metadata_json or "{}")
        assert meta["snapshot"]["id"] == drop_id
        assert meta["snapshot"]["order_number"] == "0000302"


def test_customer_sales_orders_tab_uses_distribution_units(app, client):
    with session_scope(app) as s:
        cust = Customer(facility_name="Harbor UCLA", company_key="HARBORUNITS08B", customer_type="catheter")
        s.add(cust)
        s.flush()
        so_linked = SalesOrder(
            order_number="0000312",
            order_date=date(2025, 11, 10),
            customer_id=cust.id,
            source="pdf_import",
            status="completed",
        )
        so_open = SalesOrder(
            order_number="0000376",
            order_date=date(2026, 8, 1),
            customer_id=cust.id,
            source="pdf_import",
            status="pending",
            order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
        )
        s.add_all([so_linked, so_open])
        s.flush()
        s.add(SalesOrderLine(sales_order_id=so_linked.id, sku="211610SPT", quantity=2, line_number=1))
        s.add(SalesOrderLine(sales_order_id=so_linked.id, sku="211610SPT", quantity=2, line_number=2))
        s.add(SalesOrderLine(sales_order_id=so_linked.id, sku="211610SPT", quantity=2, line_number=3))
        s.add(SalesOrderLine(sales_order_id=so_open.id, sku="211610SPT", quantity=8, line_number=1))
        dist = DistributionLogEntry(
            ship_date=date(2025, 11, 10),
            order_number="0000312",
            facility_name=cust.facility_name,
            sku="211610SPT",
            lot_number="SLQ-05012025",
            quantity=30,
            source="shipstation",
            sales_order_id=so_linked.id,
            customer_id=cust.id,
        )
        s.add(dist)
        s.flush()
        s.add(DistributionLine(distribution_entry_id=dist.id, sku="211610SPT", lot_number="SLQ-05012025", quantity=10))
        s.add(DistributionLine(distribution_entry_id=dist.id, sku="211610SPT", lot_number="SLQ-05022025", quantity=10))
        s.add(DistributionLine(distribution_entry_id=dist.id, sku="211810SPT", lot_number="SLQ-05012025", quantity=10))
        s.flush()
        assert sales_order_tab_units(so_linked) == 30
        assert sales_order_tab_units(so_open) == 8
        cust_id = cust.id

    _login(client)
    html = client.get(f"/admin/customers/{cust_id}?tab=sales_orders").get_data(as_text=True)
    assert "0000312" in html
    assert ">30<" in html
    assert "0000376" in html
    assert ">8<" in html
    # Line-sum residue (6) must not be the displayed Total Units for 0000312.
    assert not (html.count(">6<") and html.split("0000312")[1].split("0000376")[0].count(">6<"))


def test_task_a_skips_existing_sales_order(app):
    from scripts.p4_08b_distribution_cleanup import task_a_execute

    with app.app_context():
        with session_scope(app) as s:
            cust = Customer(facility_name="Harbor UCLA", company_key="HARBORSKIP08B", customer_type="catheter")
            s.add(cust)
            s.flush()
            so = SalesOrder(
                order_number="0000275",
                order_date=date(2025, 12, 16),
                customer_id=cust.id,
                source="pdf_import",
                status="completed",
            )
            s.add(so)
            s.flush()
            s.add(SalesOrderLine(sales_order_id=so.id, sku="211810SPT", quantity=10, line_number=1))
            s.flush()
            so_id = so.id
            user = _user(s)
            fake = ParseResult(
                orders=[_order_data("0000275", "Harbor UCLA", [{"sku": "211810SPT", "quantity": 2}])],
                lines=[],
                labels=[],
                errors=[],
                total_rows_processed=1,
            )
            with patch(
                "app.eqms.modules.rep_traceability.parsers.pdf.parse_sales_orders_pdf",
                return_value=fake,
            ), patch(
                "app.eqms.modules.rep_traceability.admin._store_pdf_attachment",
            ) as store:
                task_a_execute(s, user, [(1, b"%PDF-1.4")])
                store.assert_not_called()
            lines = s.query(SalesOrderLine).filter(SalesOrderLine.sales_order_id == so_id).all()
            assert [(ln.sku, ln.quantity) for ln in lines] == [("211810SPT", 10)]
            assert s.query(SalesOrder).filter(SalesOrder.order_number == "0000275").count() == 1


def test_file_import_marker_and_trunk_complete(app):
    from scripts.p4_08b_distribution_cleanup import (
        MARKER_ACTION,
        file_import_already_complete,
        write_file_import_marker,
    )

    with app.app_context():
        with session_scope(app) as s:
            assert file_import_already_complete(s) is False
            write_file_import_marker(s, _user(s))
            s.flush()
            assert file_import_already_complete(s) is True
            ev = s.query(AuditEvent).filter(AuditEvent.action == MARKER_ACTION).one()
            assert ev.entity_id == "p4_08b_abc"


def test_run_abc_on_release_skips_storage_failure(app, tmp_path, capsys):
    from scripts.p4_08b_distribution_cleanup import run_abc_on_release

    pdf = tmp_path / "SalesOrders2025-Aug2126.pdf"
    pdf.write_bytes(b"%PDF")
    with patch("app.eqms.create_app", return_value=app), patch(
        "scripts.p4_08b_distribution_cleanup.SO_PDF", pdf
    ), patch(
        "scripts.p4_08b_distribution_cleanup.file_import_already_complete", return_value=False
    ), patch(
        "scripts.p4_08b_distribution_cleanup._storage_writable", return_value=False
    ), patch(
        "scripts.p4_08b_distribution_cleanup._run_abc"
    ) as run_abc:
        run_abc_on_release()
        run_abc.assert_not_called()
    out = capsys.readouterr().out
    assert "P4-08B file import skipped: storage put_bytes failed." in out


def test_run_release_does_not_run_file_import(monkeypatch, capsys):
    from scripts import release as release_mod

    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("ENV", "test")

    with patch("alembic.command.upgrade"), patch("scripts.init_db.seed_only"), patch(
        "scripts.p4_08b_distribution_cleanup.run_abc_on_release"
    ) as run_abc:
        release_mod.run_release()
        run_abc.assert_not_called()
    out = capsys.readouterr().out
    assert "=== SilqQMS release done ===" in out
    assert "P4-08B file import" not in out


def test_when_ready_swallows_import_errors(capsys):
    from scripts.gunicorn_conf import when_ready

    with patch(
        "scripts.release.run_file_import_after_listen",
        side_effect=RuntimeError("nope"),
    ):
        when_ready(None)
    assert "P4-08B file import skipped: RuntimeError." in capsys.readouterr().out


def test_file_import_after_listen_swallows_errors(capsys):
    from scripts import release as release_mod

    with patch(
        "scripts.p4_08b_distribution_cleanup.run_abc_on_release",
        side_effect=RuntimeError("nope"),
    ):
        release_mod.run_file_import_after_listen()
    assert "P4-08B file import skipped: RuntimeError." in capsys.readouterr().out
