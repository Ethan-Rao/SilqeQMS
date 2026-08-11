"""
P4-06C — Evidence-led PO PDF extraction, review form, line items, supplier resolve.
"""
from __future__ import annotations

import io
import json
import re
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.purchasing.models import PurchaseOrder, PurchaseOrderAttachment, PurchaseOrderLine
from app.eqms.modules.purchasing.parsers.pdf import merge_import_metadata, parse_purchase_order_pdf
from app.eqms.modules.purchasing.service import resolve_supplier_by_extracted_name
from app.eqms.modules.suppliers.models import Supplier
from app.eqms.storage import storage_from_config

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
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "storage"))
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True
    application.config["STORAGE_BACKEND"] = "local"
    application.config["STORAGE_LOCAL_ROOT"] = str(tmp_path / "storage")

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


def _silq_po_pdf_bytes() -> bytes:
    """Fixture matching the Silq PURCHASE ORDER template observed in Task A readable dumps."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    y = 750
    lines = [
        "PURCHASE ORDER",
        "Silq Technologies Corporation P.O. NUMBER: 0000175",
        "ORDER DATE: 6/30/2025",
        "323 Sunny Isles Blvd. 7th Floor",
        "VENDOR NUMBER: BENTEC",
        "Sunny Isles Beach, FL 33160",
        "VENDOR: SHIP TO:",
        "Bentec Medical OpCo LLC Brian McVerry - Silq Technologies Corporation",
        "1380 East Beamer Street C/O University of California Los Angeles",
        "CONFIRM TO:",
        "REQUIRED DATE SHIP VIA F.O.B. TERMS",
        "ITEM CODE DESCRIPTION UNIT ORDERED RECEIVED BACK ORD UNIT COST AMOUNT",
        "/M CHRG BM3-2350 EACH 1.0000 0.0000 0.0000 77.0000 77.00",
        "Silicone Platinum Bulk Tubing 0.058 x 0.077 50'",
        "NET ORDER: 77.00",
        "By accepting this PO, supplier agrees to notify Silq Technologies Corporation",
    ]
    for line in lines:
        c.drawString(40, y, line)
        y -= 14
    c.showPage()
    c.save()
    return buf.getvalue()


def _blank_pdf_bytes() -> bytes:
    """PDF with no extractable text layer."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    # Draw only a filled rectangle — no text operators.
    c.setFillGray(0.9)
    c.rect(100, 100, 200, 200, fill=1, stroke=0)
    c.showPage()
    c.save()
    return buf.getvalue()


def test_extraction_against_silq_template_fixture():
    parsed = parse_purchase_order_pdf(_silq_po_pdf_bytes())
    assert parsed["po_number"] == "0000175"
    assert parsed["order_date"] == date(2025, 6, 30)
    assert parsed["supplier_name"] and "Bentec" in parsed["supplier_name"]
    assert parsed["items"]
    assert parsed["items"][0]["item_code"] == "BM3-2350"
    assert parsed["items"][0]["quantity"] == 1
    assert parsed["items"][0]["unit_price"] == "77.0000"


def test_no_text_layer_returns_none_fields():
    parsed = parse_purchase_order_pdf(_blank_pdf_bytes())
    assert parsed["po_number"] is None
    assert parsed["order_date"] is None
    assert parsed["supplier_name"] is None
    assert parsed["items"] == []
    assert len((parsed.get("raw_text") or "").strip()) < 50


def test_conforming_filename_wins_over_pdf_text():
    parsed = {
        "po_number": "9999999",
        "order_date": date(2020, 1, 1),
        "supplier_name": "Wrong PDF Supplier",
        "items": [{"item_code": "X", "description": "y", "quantity": 2, "unit_price": "1"}],
    }
    merged = merge_import_metadata("PO 0000161 BENTEC 15JAN2025.pdf", parsed)
    assert merged["po_number"] == "0000161"
    assert merged["order_date"] == date(2025, 1, 15)
    assert merged["supplier_name"] == "BENTEC"
    assert merged["sources"]["po_number"] == "filename"
    assert merged["items"][0]["item_code"] == "X"


def test_upload_missing_po_number_stages_file(app, client):
    _login(client)
    token = _csrf(client)
    pdf = _blank_pdf_bytes()
    rv = client.post(
        "/admin/purchasing/import-pdf",
        data={"csrf_token": token, "pdf_file": (BytesIO(pdf), "scan.pdf")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 200
    body = rv.get_data(as_text=True)
    assert "Review PO PDF import" in body
    assert "No PO number was detected" in body
    m = re.search(r'name="staged_key" value="([^"]+)"', body)
    assert m
    staged_key = m.group(1)
    assert staged_key.startswith("temp_po_pdf/")
    with app.app_context():
        storage = storage_from_config(app.config)
        assert storage.exists(staged_key)
        assert storage.get_bytes(staged_key) == pdf
    with session_scope(app) as s:
        assert s.query(PurchaseOrder).count() == 0


def test_confirm_review_creates_po_and_attaches_once(app, client):
    _login(client)
    token = _csrf(client)
    pdf = _silq_po_pdf_bytes()
    # Force missing number by renaming to non-conforming and blanking parse
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={
            "po_number": None,
            "order_date": date(2025, 6, 30),
            "supplier_name": "Bentec Medical OpCo LLC",
            "items": [{"item_code": "BM3-2350", "description": "tubing", "quantity": 1, "unit_price": "77"}],
            "raw_text": "x" * 60,
        },
    ):
        rv = client.post(
            "/admin/purchasing/import-pdf",
            data={"csrf_token": token, "pdf_file": (BytesIO(pdf), "scan.pdf")},
            content_type="multipart/form-data",
        )
    body = rv.get_data(as_text=True)
    staged = re.search(r'name="staged_key" value="([^"]+)"', body).group(1)
    token = _csrf(client)
    rv2 = client.post(
        "/admin/purchasing/import-pdf/confirm",
        data={
            "csrf_token": token,
            "staged_key": staged,
            "filename": "scan.pdf",
            "po_number": "0000175",
            "order_date": "2025-06-30",
            "supplier_name": "Bentec Medical OpCo LLC",
            "items_json": json.dumps(
                [{"item_code": "BM3-2350", "description": "tubing", "quantity": 1, "unit_price": "77"}]
            ),
            "source_order_date": "pdf",
            "source_supplier_name": "pdf",
        },
        follow_redirects=True,
    )
    assert rv2.status_code == 200
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000175").one()
        atts = s.query(PurchaseOrderAttachment).filter_by(purchase_order_id=po.id).all()
        assert len(atts) == 1
        assert len(po.lines) == 1
    with app.app_context():
        storage = storage_from_config(app.config)
        assert not storage.exists(staged)


def test_abandon_review_cleans_staging(app, client):
    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={"po_number": None, "order_date": None, "supplier_name": None, "items": [], "raw_text": ""},
    ):
        rv = client.post(
            "/admin/purchasing/import-pdf",
            data={"csrf_token": token, "pdf_file": (BytesIO(_blank_pdf_bytes()), "scan.pdf")},
            content_type="multipart/form-data",
        )
    staged = re.search(r'name="staged_key" value="([^"]+)"', rv.get_data(as_text=True)).group(1)
    token = _csrf(client)
    client.post(
        "/admin/purchasing/import-pdf/abandon",
        data={"csrf_token": token, "staged_key": staged},
        follow_redirects=True,
    )
    with session_scope(app) as s:
        assert s.query(PurchaseOrder).count() == 0
    with app.app_context():
        assert not storage_from_config(app.config).exists(staged)


def test_existing_po_fills_blanks_only(app, client):
    with session_scope(app) as s:
        s.add(
            PurchaseOrder(
                po_number="0000200",
                order_date=date(2025, 2, 2),
                status="pending",
                is_closed=False,
                supplier_id=None,
                notes=None,
            )
        )

    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={
            "po_number": "0000200",
            "order_date": date(2025, 2, 2),
            "supplier_name": "Ignored PDF Supplier",
            "items": [],
            "raw_text": "x" * 80,
        },
    ):
        rv = client.post(
            "/admin/purchasing/import-pdf",
            data={"csrf_token": token, "pdf_file": (BytesIO(b"%PDF"), "scan.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    body = rv.get_data(as_text=True)
    assert "PDF imported for PO 0000200" in body
    assert "PDF-text supplier was ignored" in body
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000200").one()
        assert po.order_date == date(2025, 2, 2)
        assert po.supplier_id is None
        assert po.notes is None


def test_conflict_triggers_review(app, client):
    with session_scope(app) as s:
        s.add(
            PurchaseOrder(
                po_number="0000201",
                order_date=date(2024, 5, 5),
                status="pending",
                is_closed=False,
            )
        )

    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={
            "po_number": "0000201",
            "order_date": date(2025, 5, 5),
            "supplier_name": "",
            "items": [],
            "raw_text": "x" * 80,
        },
    ):
        rv = client.post(
            "/admin/purchasing/import-pdf",
            data={"csrf_token": token, "pdf_file": (BytesIO(b"%PDF"), "scan.pdf")},
            content_type="multipart/form-data",
        )
    assert "Review PO PDF import" in rv.get_data(as_text=True)
    assert "order_date" in rv.get_data(as_text=True)


def test_lines_written_when_po_has_none(app, client):
    _login(client)
    token = _csrf(client)
    items = [{"item_code": "A1", "description": "desc", "quantity": 3, "unit_price": "9.5"}]
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={
            "po_number": "0000202",
            "order_date": date(2025, 1, 1),
            "supplier_name": "",
            "items": items,
            "raw_text": "x" * 80,
        },
    ):
        client.post(
            "/admin/purchasing/import-pdf",
            data={"csrf_token": token, "pdf_file": (BytesIO(b"%PDF"), "scan.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000202").one()
        assert len(po.lines) == 1
        assert po.lines[0].item_code == "A1"
        assert po.lines[0].quantity == 3


def test_lines_not_written_when_po_has_lines(app, client):
    with session_scope(app) as s:
        po = PurchaseOrder(
            po_number="0000203",
            order_date=date(2025, 1, 1),
            status="pending",
            is_closed=False,
        )
        s.add(po)
        s.flush()
        s.add(
            PurchaseOrderLine(
                purchase_order_id=po.id,
                item_code="KEEP",
                description="existing",
                quantity=1,
                unit_price="1",
            )
        )

    _login(client)
    token = _csrf(client)
    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={
            "po_number": "0000203",
            "order_date": date(2025, 1, 1),
            "supplier_name": "",
            "items": [{"item_code": "NEW", "description": "n", "quantity": 9, "unit_price": "2"}],
            "raw_text": "x" * 80,
        },
    ):
        rv = client.post(
            "/admin/purchasing/import-pdf",
            data={"csrf_token": token, "pdf_file": (BytesIO(b"%PDF"), "scan.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    body = rv.get_data(as_text=True)
    assert "already has lines" in body
    with session_scope(app) as s:
        po = s.query(PurchaseOrder).filter_by(po_number="0000203").one()
        assert len(po.lines) == 1
        assert po.lines[0].item_code == "KEEP"


def test_supplier_resolve_unique_none_ambiguous(app):
    with session_scope(app) as s:
        s.add(Supplier(name="Bentec Medical OpCo LLC", status="Pending"))
        s.add(Supplier(name="Acme Inc", status="Pending"))
        s.add(Supplier(name="Acme LLC", status="Pending"))
        s.flush()

        unique, st = resolve_supplier_by_extracted_name(s, "Bentec Medical OpCo")
        assert st == "unique" and unique is not None

        none, st = resolve_supplier_by_extracted_name(s, "Totally Unknown Co")
        assert st == "none" and none is None

        amb, st = resolve_supplier_by_extracted_name(s, "Acme")
        assert st == "ambiguous" and amb is None
        assert s.query(Supplier).count() == 3


def test_failed_db_write_deletes_only_new_upload(app, client):
    with session_scope(app) as s:
        po = PurchaseOrder(
            po_number="0000204",
            order_date=date(2025, 1, 1),
            status="pending",
            is_closed=False,
        )
        s.add(po)
        s.flush()
        s.add(
            PurchaseOrderAttachment(
                purchase_order_id=po.id,
                attachment_type="po_pdf",
                storage_key="purchase_orders/keep/old.pdf",
                filename="old.pdf",
                content_type="application/pdf",
                size_bytes=4,
                uploaded_by_user_id=s.query(User).one().id,
            )
        )

    with app.app_context():
        storage = storage_from_config(app.config)
        storage.put_bytes("purchase_orders/keep/old.pdf", b"OLD1", content_type="application/pdf")

    _login(client)
    token = _csrf(client)

    with patch(
        "app.eqms.modules.purchasing.admin.parse_purchase_order_pdf",
        return_value={
            "po_number": "0000204",
            "order_date": date(2025, 1, 1),
            "supplier_name": "",
            "items": [],
            "raw_text": "x" * 80,
        },
    ), patch("sqlalchemy.orm.session.Session.commit", side_effect=RuntimeError("db boom")):
        rv = client.post(
            "/admin/purchasing/import-pdf",
            data={"csrf_token": token, "pdf_file": (BytesIO(b"%PDF-NEW"), "new.pdf")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert "rolled back" in rv.get_data(as_text=True).lower() or "error" in rv.get_data(as_text=True).lower()
    with app.app_context():
        storage = storage_from_config(app.config)
        assert storage.exists("purchase_orders/keep/old.pdf")
        assert storage.get_bytes("purchase_orders/keep/old.pdf") == b"OLD1"
        # New object under purchase_orders/0000204 should not remain after rollback cleanup
        remaining = [k for k in storage.list_keys("purchase_orders/") if "0000204" in k or "new.pdf" in k.lower()]
        assert remaining == []


def test_pdf_text_diagnostic_budget_and_partial(app, client):
    with session_scope(app) as s:
        uid = s.query(User).one().id
        for i in range(3):
            po = PurchaseOrder(
                po_number=f"00003{i:02d}",
                order_date=date(2025, 1, 1),
                status="pending",
                is_closed=False,
            )
            s.add(po)
            s.flush()
            s.add(
                PurchaseOrderAttachment(
                    purchase_order_id=po.id,
                    attachment_type="po_pdf",
                    storage_key=f"k/{i}.pdf",
                    filename=f"PO 00003{i:02d} BENTEC 15JAN2025.pdf",
                    content_type="application/pdf",
                    size_bytes=10,
                    uploaded_by_user_id=uid,
                )
            )

    _login(client)
    with patch("app.eqms.modules.purchasing.admin.storage_from_config") as factory:
        factory.return_value = MagicMock(get_bytes=MagicMock(return_value=_silq_po_pdf_bytes()))
        rv = client.get("/admin/purchasing/pdf-text")
    assert rv.status_code == 200
    body = rv.get_data(as_text=True)
    assert "PO PDF text diagnostic" in body
    assert "Text-length buckets" in body
    assert "chars=" in body
