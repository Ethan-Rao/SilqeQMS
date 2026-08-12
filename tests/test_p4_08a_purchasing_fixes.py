"""
P4-08A — Purchasing defects: audit serialization, weekly brief, mark paid, restore.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.audit import record_event
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.purchasing.models import (
    InvoiceReceivedAttachment,
    InvoiceReceivedEntry,
    PaymentEntry,
    PurchaseOrder,
    PurchaseOrderLine,
)
from app.eqms.modules.purchasing.service import (
    build_weekly_brief_payment_rows,
    document_po_closed,
    mark_invoice_paid,
    restore_payment_entry_from_audit_snapshot,
    update_purchase_order,
)
from app.eqms.storage import storage_from_config

PW = "pw"
PERMS = [
    "admin.view",
    "admin.edit",
    "purchasing.view",
    "purchasing.edit",
    "purchasing.create",
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


def _login(client):
    client.post("/auth/login", data={"email": "admin@silq.tech", "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets

    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


def _user(s) -> User:
    return s.query(User).filter_by(email="admin@silq.tech").one()


def _po(s, **kwargs) -> PurchaseOrder:
    defaults = dict(
        po_number="0000183",
        order_date=date(2026, 7, 15),
        status="pending",
        is_closed=False,
        amount="173.00",
    )
    defaults.update(kwargs)
    po = PurchaseOrder(**defaults)
    s.add(po)
    s.flush()
    return po


def test_record_event_serializes_date_datetime_decimal(app):
    with session_scope(app) as s:
        u = _user(s)
        ev = record_event(
            s,
            actor=u,
            action="test.non_serializable",
            entity_type="Test",
            entity_id="1",
            metadata={
                "d": date(2026, 8, 12),
                "dt": datetime(2026, 8, 12, 16, 23, 28),
                "amt": Decimal("173.00"),
            },
        )
        s.flush()
        parsed = json.loads(ev.metadata_json)
        assert parsed["d"] == "2026-08-12"
        assert parsed["dt"].startswith("2026-08-12T16:23:28")
        assert parsed["amt"] == "173.00"


def test_record_event_clean_metadata_byte_identical(app):
    meta = {"a": 1, "b": "x", "nested": {"ok": True}}
    expected = json.dumps(meta, sort_keys=True)
    with session_scope(app) as s:
        u = _user(s)
        ev = record_event(
            s,
            actor=u,
            action="test.clean_meta",
            entity_type="Test",
            entity_id="1",
            metadata=meta,
        )
        s.flush()
        assert ev.metadata_json == expected


def test_edit_po_order_date_records_iso(app):
    with session_scope(app) as s:
        u = _user(s)
        po = _po(s, po_number="0000200")
        pid = po.id
        update_purchase_order(
            s,
            po,
            {"order_date": date(2026, 8, 1), "status": "pending"},
            u,
        )
        s.flush()
        ev = (
            s.query(AuditEvent)
            .filter_by(action="purchase_order.edit", entity_id=str(pid))
            .order_by(AuditEvent.id.desc())
            .first()
        )
        assert ev is not None
        changes = json.loads(ev.metadata_json)["changes"]
        assert changes["order_date"]["old"] == "2026-07-15"
        assert changes["order_date"]["new"] == "2026-08-01"


def test_edit_form_mark_closed_succeeds(app, client):
    with session_scope(app) as s:
        po = _po(s, po_number="0000183")
        pid = po.id
    _login(client)
    token = _csrf(client)
    r = client.post(
        f"/admin/purchasing/{pid}/edit",
        data={
            "csrf_token": token,
            "order_date": "2026-07-15",
            "status": "pending",
            "amount": "173.00",
            "is_closed": "1",
            "closed_by": "ER / 12Aug2026",
            "line_items": "",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"Purchase order updated." in r.data
    with session_scope(app) as s:
        po = s.get(PurchaseOrder, pid)
        assert po.is_closed is True
        assert po.closed_at == date.today()
        assert (
            s.query(AuditEvent)
            .filter_by(action="purchase_order.edit", entity_id=str(pid))
            .count()
            >= 1
        )


def test_document_as_closed_records_event(app):
    with session_scope(app) as s:
        u = _user(s)
        po = _po(s, po_number="0000184")
        pid = po.id
        document_po_closed(s, po=po, user=u, when=date(2026, 8, 12))
        s.flush()
        assert po.is_closed is True
        assert po.closed_at == date(2026, 8, 12)
        ev = (
            s.query(AuditEvent)
            .filter_by(action="purchase_order.closed", entity_id=str(pid))
            .one()
        )
        meta = json.loads(ev.metadata_json)
        assert meta["after"]["closed_at"] == "2026-08-12"


def test_migrated_payment_one_weekly_brief_row(app):
    with session_scope(app) as s:
        inv = InvoiceReceivedEntry(
            payee="Pathway",
            description="Monthly",
            amount=Decimal("18966.95"),
            date_received=date(2026, 8, 10),
            disposition=InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
            is_paid=False,
        )
        s.add(inv)
        s.flush()
        pay = PaymentEntry(
            vendor="Pathway",
            description="Monthly",
            amount=Decimal("18966.95"),
            payment_due_date=date(2026, 8, 1),
            invoice_received_entry_id=inv.id,
        )
        s.add(pay)
        s.flush()
        rows = build_weekly_brief_payment_rows(s)
        kinds = [(r["kind"], r["entry"].id) for r in rows]
        assert ("upcoming", pay.id) not in kinds
        assert ("received", inv.id) in kinds
        assert sum(1 for k, eid in kinds if eid in (pay.id, inv.id)) == 1


def test_paid_invoice_excluded_from_weekly_brief(app):
    with session_scope(app) as s:
        inv = InvoiceReceivedEntry(
            payee="Vendor",
            description="Widget",
            amount=Decimal("50.00"),
            date_received=date(2026, 8, 1),
            disposition=InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
            is_paid=False,
        )
        s.add(inv)
        s.flush()
        iid = inv.id
        assert any(r["entry"].id == iid for r in build_weekly_brief_payment_rows(s))
        mark_invoice_paid(s, invoice=inv, user=_user(s))
        s.flush()
        assert not any(r["entry"].id == iid for r in build_weekly_brief_payment_rows(s))


def test_mark_paid_with_po_stays_on_related_invoices(app, client):
    with session_scope(app) as s:
        po = _po(s, po_number="0000300")
        inv = InvoiceReceivedEntry(
            payee="Micro",
            description="Cal",
            amount=Decimal("173.00"),
            date_received=date(2026, 8, 1),
            disposition=InvoiceReceivedEntry.DISPOSITION_PO_MATCHED,
            purchase_order_id=po.id,
            is_paid=False,
        )
        s.add(inv)
        s.flush()
        key = f"purchasing/invoice_received_files/{inv.id}/inv.pdf"
        s.add(
            InvoiceReceivedAttachment(
                invoice_received_entry_id=inv.id,
                filename="inv.pdf",
                storage_key=key,
                content_type="application/pdf",
                size_bytes=4,
            )
        )
        storage_from_config(app.config).put_bytes(key, b"inv1", content_type="application/pdf")
        iid, pid = inv.id, po.id

    _login(client)
    token = _csrf(client)
    r = client.post(
        f"/admin/purchasing/invoices-received/{iid}/mark-paid",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        inv = s.get(InvoiceReceivedEntry, iid)
        assert inv.is_paid is True
        assert inv.purchase_order_id == pid
        assert inv.disposition == InvoiceReceivedEntry.DISPOSITION_PO_MATCHED
        assert len(inv.attachments) == 1
        # Left Invoices Received list
        from app.eqms.modules.purchasing.admin import _sorted_invoice_received

        assert all(e.id != iid for e in _sorted_invoice_received(s))
    detail = client.get(f"/admin/purchasing/{pid}").get_data(as_text=True)
    assert "Related invoices" in detail
    assert "Paid" in detail
    assert "inv.pdf" in detail


def test_mark_paid_no_po_moves_to_other_payments(app, client):
    with session_scope(app) as s:
        inv = InvoiceReceivedEntry(
            payee="Min",
            description="Period",
            amount=Decimal("1562.30"),
            date_received=date(2026, 8, 1),
            disposition=InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
            is_paid=False,
        )
        s.add(inv)
        s.flush()
        key = f"purchasing/invoice_received_files/{inv.id}/bill.pdf"
        s.add(
            InvoiceReceivedAttachment(
                invoice_received_entry_id=inv.id,
                filename="bill.pdf",
                storage_key=key,
                content_type="application/pdf",
                size_bytes=4,
            )
        )
        storage_from_config(app.config).put_bytes(key, b"bill", content_type="application/pdf")
        iid = inv.id

    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/mark-paid",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    with session_scope(app) as s:
        inv = s.get(InvoiceReceivedEntry, iid)
        assert inv.is_paid is True
        assert inv.disposition == InvoiceReceivedEntry.DISPOSITION_OTHER_PAYMENT
        assert inv.purchase_order_id is None
        assert len(inv.attachments) == 1
    html = client.get("/admin/purchasing").get_data(as_text=True)
    other = html.split("Other Payments")[1]
    assert "bill.pdf" in other
    assert "(Paid)" in other or "Paid" in other


def test_mark_paid_leaves_po_untouched(app):
    with session_scope(app) as s:
        po = _po(s, po_number="0000400", status="pending", is_closed=False, closed_at=None)
        inv = InvoiceReceivedEntry(
            payee="X",
            description="Y",
            amount=Decimal("10.00"),
            date_received=date(2026, 8, 1),
            disposition=InvoiceReceivedEntry.DISPOSITION_PO_MATCHED,
            purchase_order_id=po.id,
        )
        s.add(inv)
        s.flush()
        mark_invoice_paid(s, invoice=inv, user=_user(s))
        s.flush()
        assert po.status == "pending"
        assert po.is_closed is False
        assert po.closed_at is None


def test_restore_payment_from_audit_snapshot(app):
    snapshot = {
        "amount": "173.00",
        "description": "ST012 Calibration",
        "files": [],
        "id": 2,
        "invoice_received_entry_id": None,
        "line_item_files": [],
        "payment_due_date": "2026-08-18",
        "vendor": "Microprecision Calibration",
    }
    with session_scope(app) as s:
        u = _user(s)
        entry = restore_payment_entry_from_audit_snapshot(
            s, snapshot=snapshot, source_event_id=6265, user=u
        )
        s.flush()
        assert entry.vendor == "Microprecision Calibration"
        assert entry.description == "ST012 Calibration"
        assert entry.amount == Decimal("173.00")
        assert entry.payment_due_date == date(2026, 8, 18)
        ev = (
            s.query(AuditEvent)
            .filter_by(action="payment_entry.restored", entity_id=str(entry.id))
            .one()
        )
        meta = json.loads(ev.metadata_json)
        assert meta["source_audit_event_id"] == 6265


def test_po_dropdown_includes_amount(app, client):
    with session_scope(app) as s:
        _po(s, po_number="0000500", amount="999.50")
        _po(s, po_number="0000501", amount=None)
        inv = InvoiceReceivedEntry(
            payee="A",
            description="B",
            amount=Decimal("1.00"),
            date_received=date(2026, 8, 1),
            disposition=InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
        )
        s.add(inv)
    _login(client)
    html = client.get("/admin/purchasing").get_data(as_text=True)
    assert "0000500" in html
    assert "$999.50" in html
    assert "0000501" in html


def test_delete_invoice_refused_while_payment_linked(app, client):
    with session_scope(app) as s:
        inv = InvoiceReceivedEntry(
            payee="V",
            description="D",
            amount=Decimal("10.00"),
            date_received=date(2026, 8, 10),
            disposition=InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
        )
        s.add(inv)
        s.flush()
        pay = PaymentEntry(
            vendor="V",
            description="D",
            amount=Decimal("10.00"),
            payment_due_date=date(2026, 9, 1),
            invoice_received_entry_id=inv.id,
        )
        s.add(pay)
        s.flush()
        iid = inv.id
    _login(client)
    token = _csrf(client)
    r = client.delete(
        f"/admin/purchasing/invoices-received/{iid}",
        headers={"X-CSRF-Token": token, "Accept": "application/json"},
    )
    assert r.status_code == 400
    body = r.get_data(as_text=True).lower()
    assert "linked" in body or "upcoming" in body
    with session_scope(app) as s:
        assert s.get(InvoiceReceivedEntry, iid) is not None


def test_empty_line_items_textarea_does_not_wipe(app, client):
    with session_scope(app) as s:
        po = _po(s, po_number="0000600")
        s.add(
            PurchaseOrderLine(
                purchase_order_id=po.id,
                item_code="A1",
                description="From PDF",
                quantity=2,
                unit_price="10.00",
            )
        )
        pid = po.id
    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/{pid}/edit",
        data={
            "csrf_token": token,
            "order_date": "2026-07-15",
            "status": "pending",
            "amount": "173.00",
            "line_items": "",
        },
        follow_redirects=True,
    )
    with session_scope(app) as s:
        po = s.get(PurchaseOrder, pid)
        assert len(po.lines) == 1
        assert po.lines[0].description == "From PDF"
