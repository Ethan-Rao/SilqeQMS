"""
P4-06B — Trust filename supplier only; fix parse-check measurement.
"""
from __future__ import annotations

from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.purchasing.models import PurchaseOrder
from app.eqms.modules.purchasing.parsers.pdf import merge_import_metadata
from app.eqms.modules.suppliers.models import Supplier

PW = "pw"
PERMS = [
    "admin.view",
    "purchasing.view",
    "purchasing.edit",
    "purchasing.create",
    "purchasing.upload",
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


def _csrf(client):
    import secrets

    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


def _po(s, **kwargs):
    defaults = dict(
        po_number="0000038",
        order_date=date(2024, 1, 15),
        status="pending",
        is_closed=False,
        supplier_id=None,
        notes=None,
    )
    defaults.update(kwargs)
    po = PurchaseOrder(**defaults)
    s.add(po)
    s.flush()
    return po


_PARSED_BAD_SUPPLIER = {
    "po_number": "0000038",
    "order_date": date(2024, 1, 15),  # match existing PO to avoid D51 conflict review
    "supplier_name": "Silq Technologies Inc",  # Sold-To noise
    "items": [],
    "raw_text": "Sold To: Silq Technologies Inc",
}


def test_merge_reports_provenance_both_directions():
    parsed = {
        "po_number": "junk",
        "order_date": date(2020, 1, 1),
        "supplier_name": "From PDF",
        "items": [],
    }
    from_file = merge_import_metadata("PO 0000161 BENTEC 15JAN2025.pdf", parsed)
    assert from_file["sources"]["po_number"] == "filename"
    assert from_file["sources"]["order_date"] == "filename"
    assert from_file["sources"]["supplier_name"] == "filename"
    assert from_file["filename_conforming"] is True
    assert from_file["supplier_name"] == "BENTEC"

    from_pdf = merge_import_metadata("scan.pdf", parsed)
    assert from_pdf["sources"]["po_number"] is None  # alphabetic junk dropped
    assert from_pdf["sources"]["order_date"] == "pdf"
    assert from_pdf["sources"]["supplier_name"] == "pdf"
    assert from_pdf["filename_conforming"] is False

    numeric = merge_import_metadata(
        "scan.pdf",
        {"po_number": "0000038", "order_date": None, "supplier_name": "", "items": []},
    )
    assert numeric["sources"]["po_number"] == "pdf"
    assert numeric["sources"]["supplier_name"] is None


def test_pdf_text_supplier_does_not_fill_blank(app, client):
    with session_scope(app) as s:
        _po(s, po_number="0000038", supplier_id=None, notes=None)
        # Ensure a matching supplier exists so an accidental fill would succeed
        s.add(Supplier(name="Silq Technologies Inc", status="Pending"))

    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value=_PARSED_BAD_SUPPLIER,
    ):
        rv = client.post(
            "/admin/purchasing/import-pdf",
            data={
                "csrf_token": token,
                "pdf_file": (BytesIO(b"%PDF-1.4"), "invoice_scan.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert rv.status_code == 200
    body = rv.get_data(as_text=True)
    assert "PDF-text supplier was ignored" in body
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000038").one()
        assert po.supplier_id is None
        assert po.notes is None


def test_filename_supplier_does_populate(app, client):
    with session_scope(app) as s:
        _po(s, po_number="0000161", supplier_id=None, notes=None, order_date=date(2025, 1, 15))
        sup = Supplier(name="BENTEC", status="Pending")
        s.add(sup)
        s.flush()
        sid = sup.id

    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={
            "po_number": None,
            "order_date": None,
            "supplier_name": "Wrong From PDF",
            "items": [],
            "raw_text": "",
        },
    ):
        client.post(
            "/admin/purchasing/import-pdf",
            data={
                "csrf_token": token,
                "pdf_file": (BytesIO(b"%PDF-1.4"), "PO 0000161 BENTEC 15JAN2025.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000161").one()
        assert po.supplier_id == sid
        assert po.notes is None


def test_order_date_still_fills_from_pdf_text(app, client):
    with session_scope(app) as s:
        # SQLite / model: order_date is NOT NULL, so seed a sentinel and clear via raw? 
        # apply_po_blank_fills only fills blanks — use a create path instead:
        # Import creates new PO when number unknown; for update, order_date is never blank.
        # Test create path: new PO gets order_date from PDF text when filename does not conform.
        pass

    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={
            "po_number": "0000991",
            "order_date": date(2025, 6, 1),
            "supplier_name": "Garbage Sold To",
            "items": [],
            "raw_text": "",
        },
    ):
        client.post(
            "/admin/purchasing/import-pdf",
            data={
                "csrf_token": token,
                "pdf_file": (BytesIO(b"%PDF"), "loose_scan.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000991").one()
        assert po.order_date == date(2025, 6, 1)
        assert po.supplier_id is None
        assert po.notes is None


def test_populated_supplier_never_overwritten(app, client):
    with session_scope(app) as s:
        keep = Supplier(name="Keep Me", status="Pending")
        other = Supplier(name="BENTEC", status="Pending")
        s.add_all([keep, other])
        s.flush()
        _po(s, po_number="0000161", supplier_id=keep.id, order_date=date(2025, 1, 15))
        keep_id = keep.id

    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={"po_number": None, "order_date": None, "supplier_name": "x", "items": [], "raw_text": ""},
    ):
        rv = client.post(
            "/admin/purchasing/import-pdf",
            data={
                "csrf_token": token,
                "pdf_file": (BytesIO(b"%PDF"), "PO 0000161 BENTEC 15JAN2025.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    body = rv.get_data(as_text=True)
    # D51: conflicting supplier triggers review; confirming still fill-blanks-only.
    if "Review PO PDF import" in body:
        import re

        m = re.search(r'name="staged_key" value="([^"]+)"', body)
        assert m
        token = _csrf(client)
        client.post(
            "/admin/purchasing/import-pdf/confirm",
            data={
                "csrf_token": token,
                "staged_key": m.group(1),
                "filename": "PO 0000161 BENTEC 15JAN2025.pdf",
                "po_number": "0000161",
                "order_date": "2025-01-15",
                "supplier_name": "BENTEC",
                "items_json": "[]",
                "source_po_number": "filename",
                "source_order_date": "filename",
                "source_supplier_name": "filename",
            },
            follow_redirects=True,
        )
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000161").one()
        assert po.supplier_id == keep_id

def test_parse_check_dual_columns_and_normalized_po(app, client):
    from app.eqms.modules.purchasing.models import PurchaseOrderAttachment

    with session_scope(app) as s:
        po = _po(s, po_number="0000038", order_date=date(2025, 1, 15))
        s.add(
            PurchaseOrderAttachment(
                purchase_order_id=po.id,
                attachment_type="po_pdf",
                storage_key="k/a.pdf",
                filename="PO 0000038 BENTEC 15JAN2025.pdf",
                content_type="application/pdf",
                size_bytes=4,
                uploaded_by_user_id=s.query(User).one().id,
            )
        )

    _login(client)
    with patch(
        "app.eqms.modules.purchasing.admin.storage_from_config"
    ) as factory, patch(
        "app.eqms.modules.purchasing.parsers.pdf.parse_purchase_order_pdf",
        return_value={
            "po_number": "PO 38",
            "order_date": date(2025, 1, 15),
            "supplier_name": "Wrong",
            "items": [],
            "raw_text": "",
        },
    ):
        factory.return_value = MagicMock(get_bytes=MagicMock(return_value=b"%PDF"))
        html = client.get("/admin/purchasing/parse-check").get_data(as_text=True)

    assert "Filename-merged" in html
    assert "Text-only" in html
    assert "normalized" in html.lower()
    assert "Conforming filenames" in html
    # Normalized: PO 38 agrees with 0000038
    assert ">1<" in html or "agree" in html.lower()

    with session_scope(app) as s:
        assert s.query(AuditEvent).filter_by(action="purchase_order.edit").count() == 0
        assert s.query(PurchaseOrder).filter_by(po_number="0000038").one().supplier_id is None
