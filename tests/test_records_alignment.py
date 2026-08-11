"""Checkpoint 3: records-and-data alignment for Equipment, Suppliers, Purchasing.

Covers the calibration/PM and supplier re-evaluation status helpers, the PO Log
date coercion + importer, and read-only gating of the new admin-only import routes.
"""
import io
from datetime import date, datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.equipment.service import due_status
from app.eqms.modules.purchasing.service import coerce_po_date, import_po_log
from app.eqms.modules.suppliers.service import date_status


# --------------------------------------------------------------------------- #
# Pure helpers (no app/db needed)
# --------------------------------------------------------------------------- #

def test_due_status_states():
    today = date(2026, 7, 8)
    assert due_status(None, "N/A", today)["state"] == "none"
    assert due_status(None, "Annual", today)["state"] == "unscheduled"
    assert due_status(today - timedelta(days=5), "Annual", today)["state"] == "overdue"
    assert due_status(today + timedelta(days=10), "Annual", today)["state"] == "due_soon"
    assert due_status(today + timedelta(days=400), "Annual", today)["state"] == "ok"


def test_date_status_states():
    today = date(2026, 7, 8)
    assert date_status(None, today)["state"] == "none"
    assert date_status(today - timedelta(days=1), today)["state"] == "overdue"
    assert date_status(today + timedelta(days=5), today)["state"] == "due_soon"
    assert date_status(today + timedelta(days=400), today)["state"] == "ok"


def test_coerce_po_date_variants():
    assert coerce_po_date(datetime(2019, 10, 24, 0, 0)) == date(2019, 10, 24)
    assert coerce_po_date(date(2024, 3, 5)) == date(2024, 3, 5)
    assert coerce_po_date("05 Mar 2024") == date(2024, 3, 5)
    assert coerce_po_date("3 March 2025") == date(2025, 3, 3)
    assert coerce_po_date("2019-10-24 00:00:00") == date(2019, 10, 24)
    # Excel serial 44631 -> 2022-03-11 (epoch 1899-12-30 + 44631 days)
    assert coerce_po_date(44631) == date(2022, 3, 11)
    assert coerce_po_date("N/A") is None
    assert coerce_po_date(None) is None
    assert coerce_po_date("") is None


# --------------------------------------------------------------------------- #
# App-backed tests
# --------------------------------------------------------------------------- #

PERM_KEYS = [
    ("admin.view", "Admin: view shell"),
    ("admin.edit", "Admin: edit"),
    ("purchasing.view", "Purchasing: view"),
    ("purchasing.create", "Purchasing: create"),
    ("purchasing.edit", "Purchasing: edit"),
    ("purchasing.upload", "Purchasing: upload"),
]

STAFF_KEYS = ["admin.view", "purchasing.view"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    app = create_app()
    engine = app.extensions["sqlalchemy_engine"]
    Base.metadata.create_all(bind=engine)
    app.config["_schema_health_ok"] = True

    with session_scope(app) as s:
        perms = {}
        for key, name in PERM_KEYS:
            p = Permission(key=key, name=name)
            s.add(p)
            perms[key] = p

        admin_role = Role(key="admin", name="Administrator")
        for p in perms.values():
            admin_role.permissions.append(p)
        admin = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        admin.roles.append(admin_role)

        staff_role = Role(key="staff", name="Staff (read-only)")
        for key in STAFF_KEYS:
            staff_role.permissions.append(perms[key])
        staff = User(email="staff@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        staff.roles.append(staff_role)

        s.add_all([admin_role, admin, staff_role, staff])

    return app


def _login(client, email):
    client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            sess["csrf_token"] = token
        return token


def _build_po_log_xlsx() -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "2019 - 2024"
    ws.append(["The P.O. Log process is defined in QM.SLQ020 Purchasing Controls SOP."])
    ws.append(["Obtain P.O. Number"])
    ws.append([
        "P.O. Number", "Supplier/Vendor Name and identification", "Date",
        "Target Delivery Date", "Actual Delivery Date",
        "Product/Service Meets Requirement(s)?\nYes / No", "Verified how?",
        "Closed by\nInitials / Date", "Cost Info.", "References", "Notes/Comments",
    ])
    ws.append([
        "0000044", "Pathway", datetime(2021, 12, 9), datetime(2021, 12, 9), 44631,
        "Yes", "Receiving inspection /CoC/packinglist", "DP / 14Oct2022", "3871.36", "see attached", "",
    ])
    ws.append([
        "0000008", "*not used*", None, None, None, None, None, None, None, None, None,
    ])
    ws.append([
        "0000109", "MorganFranklin Consulting, LLC", "05 Mar 2024", "05 Mar 2024", "N/A",
        "Yes", "Email confirmation", "ER / 09Jul2024", "2108.93", "", "professional services",
    ])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_import_po_log_creates_rows(app):
    from app.eqms.modules.purchasing.models import PurchaseOrder

    file_bytes = _build_po_log_xlsx()
    with app.test_request_context():
        with session_scope(app) as s:
            user = s.query(User).filter(User.email == "admin@example.com").one()
            result = import_po_log(s, file_bytes, user)

    assert result["created"] == 2
    assert result["skipped"] == 1  # the *not used* row
    assert not result["errors"]

    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter(PurchaseOrder.po_number == "0000044").one()
        assert po.amount == "3871.36"
        assert po.meets_requirements == "Yes"
        assert po.received_date == date(2022, 3, 11)  # serial 44631
        assert po.status == "received"
        assert "Receiving inspection" in po.verified_how

        po2 = s.query(PurchaseOrder).filter(PurchaseOrder.po_number == "0000109").one()
        assert po2.order_date == date(2024, 3, 5)
        assert po2.received_date is None  # "N/A"
        assert po2.status == "pending"


def test_import_po_log_is_idempotent(app):
    from app.eqms.modules.purchasing.models import PurchaseOrder  # noqa: F811

    file_bytes = _build_po_log_xlsx()
    with app.test_request_context():
        with session_scope(app) as s:
            user = s.query(User).filter(User.email == "admin@example.com").one()
            import_po_log(s, file_bytes, user)
    with app.test_request_context():
        with session_scope(app) as s:
            user = s.query(User).filter(User.email == "admin@example.com").one()
            result = import_po_log(s, file_bytes, user)

    assert result["created"] == 0
    # Fill-blanks-only: second pass finds nothing to fill, so rows are skipped.
    assert result["updated"] == 0
    assert result["skipped"] >= 2
    with session_scope(app) as s:
        assert s.query(PurchaseOrder).count() == 2


def test_staff_cannot_reach_po_log_import(app):
    client = app.test_client()
    _login(client, "staff@example.com")
    assert client.get("/admin/purchasing/import-log").status_code == 403
    r = client.post(
        "/admin/purchasing/import-log",
        data={"csrf_token": _csrf(client)},
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_admin_can_reach_po_log_import(app):
    client = app.test_client()
    _login(client, "admin@example.com")
    assert client.get("/admin/purchasing/import-log").status_code == 200


def test_staff_sees_purchasing_list_without_edit_controls(app):
    client = app.test_client()
    _login(client, "staff@example.com")
    r = client.get("/admin/purchasing")
    assert r.status_code == 200
    assert b"Import PO Log" not in r.data
    assert b"New PO" not in r.data
