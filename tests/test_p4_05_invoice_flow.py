"""
P4-05 — Invoice upload, received ledger, PO matching, Other Payments.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.purchasing.models import (
    InvoiceReceivedAttachment,
    InvoiceReceivedEntry,
    PaymentEntry,
    PaymentEntryAttachment,
    PaymentLineItem,
    PaymentLineItemAttachment,
    PurchaseOrder,
)
from app.eqms.modules.purchasing.service import (
    InvoiceFlowError,
    mark_invoice_other_payment,
    match_invoice_to_po,
    migrate_payment_to_invoice,
    return_invoice_to_received,
    return_invoice_to_upcoming,
    unmatch_invoice_from_po,
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

    # SQLite needs an explicit PRAGMA for ON DELETE SET NULL / CASCADE to fire.
    from sqlalchemy import event

    @event.listens_for(application.extensions["sqlalchemy_engine"], "connect")
    def _sqlite_fk(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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

        view_role = Role(key="viewer", name="Viewer")
        view_role.permissions.append(perms["admin.view"])
        view_role.permissions.append(perms["purchasing.view"])
        viewer = User(
            email="viewer@silq.tech",
            display_name="Viewer",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        viewer.roles.append(view_role)
        s.add_all(list(perms.values()) + [admin_role, view_role, admin, viewer])

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


def _seed_payment(s, *, vendor="Acme", amount="100.00", with_files=True, with_line=True):
    pay = PaymentEntry(
        order_date=date(2026, 1, 10),
        vendor=vendor,
        description="Widgets",
        amount=Decimal(amount),
        payment_due_date=date(2026, 2, 1),
    )
    s.add(pay)
    s.flush()
    keys = []
    if with_files:
        key = f"purchasing/payment_files/{pay.id}/quote.pdf"
        att = PaymentEntryAttachment(
            payment_entry_id=pay.id,
            filename="quote.pdf",
            storage_key=key,
            content_type="application/pdf",
            size_bytes=12,
        )
        s.add(att)
        keys.append(key)
    if with_line:
        li = PaymentLineItem(
            payment_entry_id=pay.id,
            description="Line A",
            amount=Decimal("40.00"),
            sort_order=0,
        )
        s.add(li)
        s.flush()
        if with_files:
            lkey = f"purchasing/payment_line_files/{li.id}/line.pdf"
            s.add(
                PaymentLineItemAttachment(
                    payment_line_item_id=li.id,
                    filename="line.pdf",
                    storage_key=lkey,
                    content_type="application/pdf",
                    size_bytes=8,
                )
            )
            keys.append(lkey)
    return pay, keys


def _put_keys(app, keys):
    storage = storage_from_config(app.config)
    for k in keys:
        storage.put_bytes(k, b"payload-" + k.encode(), content_type="application/pdf")
    return storage


def _seed_po(s, *, po_number="PO-100"):
    po = PurchaseOrder(
        po_number=po_number,
        order_date=date(2026, 1, 5),
        status="pending",
        description="Test PO",
        amount="100.00",
    )
    s.add(po)
    s.flush()
    return po


# ---- 1–5 migrate / return ----


def test_upload_invoice_migrates_and_links(app, client):
    with session_scope(app) as s:
        pay, keys = _seed_payment(s)
        pid = pay.id
    storage = _put_keys(app, keys)

    _login(client)
    token = _csrf(client)
    rv = client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={
            "csrf_token": token,
            "date_received": "2026-03-15",
            "file": (BytesIO(b"%PDF-invoice"), "invoice.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert rv.status_code == 200

    with session_scope(app) as s:
        pay = s.get(PaymentEntry, pid)
        assert pay.invoice_received_entry_id is not None
        inv = s.get(InvoiceReceivedEntry, pay.invoice_received_entry_id)
        assert inv is not None
        assert inv.payee == "Acme"
        assert inv.amount == Decimal("100.00")
        assert inv.due_date == date(2026, 2, 1)
        assert inv.date_received == date(2026, 3, 15)
        assert inv.disposition == InvoiceReceivedEntry.DISPOSITION_UNASSIGNED
        names = {a.filename for a in inv.attachments}
        assert "invoice.pdf" in names
        assert "quote.pdf" in names
        assert "line.pdf" in names


def test_migrated_entry_leaves_upcoming_appears_received(app, client):
    with session_scope(app) as s:
        pay, keys = _seed_payment(s)
        pid = pay.id
    _put_keys(app, keys)

    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={
            "csrf_token": token,
            "file": (BytesIO(b"inv"), "invoice.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    html = client.get("/admin/purchasing").data.decode()
    # Upcoming table should not list Acme as an editable upcoming row with upload
    with session_scope(app) as s:
        upcoming = s.query(PaymentEntry).filter(PaymentEntry.invoice_received_entry_id.is_(None)).all()
        received = (
            s.query(InvoiceReceivedEntry)
            .filter(
                InvoiceReceivedEntry.disposition.in_(
                    [
                        InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
                        InvoiceReceivedEntry.DISPOSITION_PO_MATCHED,
                    ]
                )
            )
            .all()
        )
        assert upcoming == []
        assert len(received) == 1
        assert received[0].payee == "Acme"
    assert "Invoices Received" in html
    assert "Acme" in html


def test_storage_object_survives_migration(app, client):
    """Critical data-loss guard: same storage_key, storage.exists still true."""
    with session_scope(app) as s:
        pay, keys = _seed_payment(s, with_line=False)
        pid = pay.id
        quote_key = keys[0]
    storage = _put_keys(app, keys)
    assert storage.exists(quote_key)

    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={
            "csrf_token": token,
            "file": (BytesIO(b"inv"), "invoice.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with session_scope(app) as s:
        pay = s.get(PaymentEntry, pid)
        inv = s.get(InvoiceReceivedEntry, pay.invoice_received_entry_id)
        moved = [a for a in inv.attachments if a.filename == "quote.pdf"]
        assert len(moved) == 1
        assert moved[0].storage_key == quote_key
        assert s.query(PaymentEntryAttachment).filter_by(payment_entry_id=pid).count() == 0
    assert storage.exists(quote_key)


def test_line_item_attachments_migrate_lines_survive(app, client):
    with session_scope(app) as s:
        pay, keys = _seed_payment(s)
        pid = pay.id
        line_key = keys[1]
    storage = _put_keys(app, keys)

    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={
            "csrf_token": token,
            "file": (BytesIO(b"inv"), "invoice.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with session_scope(app) as s:
        pay = s.get(PaymentEntry, pid)
        assert len(pay.line_items) == 1
        assert pay.line_items[0].description == "Line A"
        assert pay.line_items[0].attachments == []
        inv = s.get(InvoiceReceivedEntry, pay.invoice_received_entry_id)
        assert any(a.storage_key == line_key for a in inv.attachments)
    assert storage.exists(line_key)


def test_return_to_upcoming_reverses_without_deleting_storage(app, client):
    with session_scope(app) as s:
        pay, keys = _seed_payment(s, with_line=False)
        pid = pay.id
        quote_key = keys[0]
    storage = _put_keys(app, keys)

    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={
            "csrf_token": token,
            "file": (BytesIO(b"inv"), "invoice.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    with session_scope(app) as s:
        pay = s.get(PaymentEntry, pid)
        iid = pay.invoice_received_entry_id

    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/return-to-upcoming",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    with session_scope(app) as s:
        pay = s.get(PaymentEntry, pid)
        assert pay.invoice_received_entry_id is None
        assert s.get(InvoiceReceivedEntry, iid) is None
        names = {a.filename for a in pay.attachments}
        assert "quote.pdf" in names
        assert "invoice.pdf" in names
        assert any(a.storage_key == quote_key for a in pay.attachments)
        upcoming = s.query(PaymentEntry).filter(PaymentEntry.invoice_received_entry_id.is_(None)).all()
        assert len(upcoming) == 1
    assert storage.exists(quote_key)


# ---- 6 SET NULL on invoice delete ----


def test_deleting_received_invoice_refused_while_payment_linked(app, client):
    """Task H1 (also covered in P4-06): refuse delete while payment linked."""
    with session_scope(app) as s:
        pay, keys = _seed_payment(s, with_files=False, with_line=False)
        pid = pay.id
    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={
            "csrf_token": token,
            "file": (BytesIO(b"inv"), "invoice.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    with session_scope(app) as s:
        pay = s.get(PaymentEntry, pid)
        iid = pay.invoice_received_entry_id
        assert iid is not None

    token = _csrf(client)
    rv = client.delete(
        f"/admin/purchasing/invoices-received/{iid}",
        headers={"X-CSRF-Token": token, "Accept": "application/json"},
    )
    assert rv.status_code == 400
    with session_scope(app) as s:
        assert s.get(InvoiceReceivedEntry, iid) is not None
        assert s.get(PaymentEntry, pid).invoice_received_entry_id == iid


# ---- 7–12 PO match / other ----


def test_match_po_and_related_invoices_on_detail(app, client):
    with session_scope(app) as s:
        pay, keys = _seed_payment(s, with_files=False, with_line=False)
        pid = pay.id
        po = _seed_po(s)
        po_id = po.id
        po_number = po.po_number
    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={
            "csrf_token": token,
            "file": (BytesIO(b"inv"), "invoice.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    with session_scope(app) as s:
        pay = s.get(PaymentEntry, pid)
        iid = pay.invoice_received_entry_id

    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/match-po",
        data={"csrf_token": token, "purchase_order_id": str(po_id)},
        follow_redirects=True,
    )

    with session_scope(app) as s:
        inv = s.get(InvoiceReceivedEntry, iid)
        assert inv.purchase_order_id == po_id
        assert inv.disposition == InvoiceReceivedEntry.DISPOSITION_PO_MATCHED

    detail = client.get(f"/admin/purchasing/{po_id}").data.decode()
    assert "Related invoices" in detail
    assert "Acme" in detail
    assert "invoice.pdf" in detail
    assert po_number


def test_unmatch_returns_unassigned_and_leaves_po_page(app, client):
    with session_scope(app) as s:
        pay, keys = _seed_payment(s, with_files=False, with_line=False)
        pid = pay.id
        po = _seed_po(s)
        po_id = po.id
    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={"csrf_token": token, "file": (BytesIO(b"inv"), "invoice.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    with session_scope(app) as s:
        iid = s.get(PaymentEntry, pid).invoice_received_entry_id

    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/match-po",
        data={"csrf_token": token, "purchase_order_id": str(po_id)},
        follow_redirects=True,
    )
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/match-po",
        data={"csrf_token": token, "purchase_order_id": ""},
        follow_redirects=True,
    )

    with session_scope(app) as s:
        inv = s.get(InvoiceReceivedEntry, iid)
        assert inv.purchase_order_id is None
        assert inv.disposition == InvoiceReceivedEntry.DISPOSITION_UNASSIGNED

    detail = client.get(f"/admin/purchasing/{po_id}").data.decode()
    assert "No invoices matched" in detail


def test_mark_other_moves_to_other_payments_section(app, client):
    with session_scope(app) as s:
        pay, _ = _seed_payment(s, with_files=False, with_line=False)
        pid = pay.id
    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={"csrf_token": token, "file": (BytesIO(b"inv"), "invoice.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    with session_scope(app) as s:
        iid = s.get(PaymentEntry, pid).invoice_received_entry_id

    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/mark-other",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    with session_scope(app) as s:
        inv = s.get(InvoiceReceivedEntry, iid)
        assert inv.disposition == InvoiceReceivedEntry.DISPOSITION_OTHER_PAYMENT

    html = client.get("/admin/purchasing").data.decode()
    assert "Other Payments" in html
    # Still on page under Other Payments; not in unassigned/po_matched query
    with session_scope(app) as s:
        received = (
            s.query(InvoiceReceivedEntry)
            .filter(
                InvoiceReceivedEntry.disposition.in_(
                    [
                        InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
                        InvoiceReceivedEntry.DISPOSITION_PO_MATCHED,
                    ]
                )
            )
            .count()
        )
        other = (
            s.query(InvoiceReceivedEntry)
            .filter(InvoiceReceivedEntry.disposition == InvoiceReceivedEntry.DISPOSITION_OTHER_PAYMENT)
            .count()
        )
        assert received == 0
        assert other == 1


def test_mark_other_refused_while_po_matched(app):
    with session_scope(app) as s:
        pay, _ = _seed_payment(s, with_files=False, with_line=False)
        storage = storage_from_config(app.config)
        user = s.query(User).filter_by(email="admin@silq.tech").one()
        inv = migrate_payment_to_invoice(
            s,
            payment=pay,
            file_bytes=b"inv",
            filename="invoice.pdf",
            content_type="application/pdf",
            date_received=date.today(),
            user=user,
            storage=storage,
        )
        po = _seed_po(s)
        match_invoice_to_po(s, invoice=inv, purchase_order=po, user=user)
        with pytest.raises(InvoiceFlowError):
            mark_invoice_other_payment(s, invoice=inv, user=user)


def test_matched_invoice_stays_in_invoices_received(app, client):
    with session_scope(app) as s:
        pay, _ = _seed_payment(s, with_files=False, with_line=False)
        pid = pay.id
        po = _seed_po(s)
        po_id = po.id
        po_number = po.po_number
    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={"csrf_token": token, "file": (BytesIO(b"inv"), "invoice.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    with session_scope(app) as s:
        iid = s.get(PaymentEntry, pid).invoice_received_entry_id
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/match-po",
        data={"csrf_token": token, "purchase_order_id": str(po_id)},
        follow_redirects=True,
    )
    html = client.get("/admin/purchasing").data.decode()
    assert "Invoices Received" in html
    assert po_number in html
    assert "Acme" in html


def test_deleting_po_clears_invoice_fk(app):
    from sqlalchemy import text

    with session_scope(app) as s:
        pay, _ = _seed_payment(s, with_files=False, with_line=False)
        storage = storage_from_config(app.config)
        user = s.query(User).filter_by(email="admin@silq.tech").one()
        inv = migrate_payment_to_invoice(
            s,
            payment=pay,
            file_bytes=b"inv",
            filename="invoice.pdf",
            content_type="application/pdf",
            date_received=date.today(),
            user=user,
            storage=storage,
        )
        po = _seed_po(s)
        match_invoice_to_po(s, invoice=inv, purchase_order=po, user=user)
        iid = inv.id
        po_id = po.id
        s.flush()

    with session_scope(app) as s:
        # Enforce FKs on this connection (SQLite defaults to off).
        s.connection().execute(text("PRAGMA foreign_keys=ON"))
        po = s.get(PurchaseOrder, po_id)
        assert po is not None
        s.delete(po)
        s.flush()
        s.expire_all()
        inv = s.get(InvoiceReceivedEntry, iid)
        assert inv is not None
        assert inv.purchase_order_id is None


# ---- 13 permissions ----


def test_view_only_cannot_upload_match_or_mark(app, client):
    with session_scope(app) as s:
        pay, keys = _seed_payment(s, with_files=False, with_line=False)
        pid = pay.id
        po = _seed_po(s)
        po_id = po.id
        storage = storage_from_config(app.config)
        user = s.query(User).filter_by(email="admin@silq.tech").one()
        inv = migrate_payment_to_invoice(
            s,
            payment=s.get(PaymentEntry, pid),
            file_bytes=b"inv",
            filename="invoice.pdf",
            content_type="application/pdf",
            date_received=date.today(),
            user=user,
            storage=storage,
        )
        iid = inv.id

    _login(client, email="viewer@silq.tech")
    token = _csrf(client)

    # Create a fresh upcoming payment for upload attempt
    with session_scope(app) as s:
        pay2, _ = _seed_payment(s, vendor="ViewerTarget", with_files=False, with_line=False)
        pid2 = pay2.id

    rv = client.post(
        f"/admin/purchasing/payments/{pid2}/upload-invoice",
        data={"csrf_token": token, "file": (BytesIO(b"x"), "x.pdf")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert rv.status_code in (302, 403)
    # If redirected to login or forbidden page — not success migrate
    with session_scope(app) as s:
        assert s.get(PaymentEntry, pid2).invoice_received_entry_id is None

    rv = client.post(
        f"/admin/purchasing/invoices-received/{iid}/match-po",
        data={"csrf_token": token, "purchase_order_id": str(po_id)},
        follow_redirects=False,
    )
    assert rv.status_code in (302, 403)
    with session_scope(app) as s:
        assert s.get(InvoiceReceivedEntry, iid).purchase_order_id is None

    rv = client.post(
        f"/admin/purchasing/invoices-received/{iid}/mark-other",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert rv.status_code in (302, 403)
    with session_scope(app) as s:
        assert s.get(InvoiceReceivedEntry, iid).disposition == InvoiceReceivedEntry.DISPOSITION_UNASSIGNED


def test_edit_can_upload_match_and_mark(app, client):
    with session_scope(app) as s:
        pay, _ = _seed_payment(s, with_files=False, with_line=False)
        pid = pay.id
        po = _seed_po(s)
        po_id = po.id
    _login(client)
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/payments/{pid}/upload-invoice",
        data={"csrf_token": token, "file": (BytesIO(b"inv"), "invoice.pdf")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    with session_scope(app) as s:
        iid = s.get(PaymentEntry, pid).invoice_received_entry_id
        assert iid is not None
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/match-po",
        data={"csrf_token": token, "purchase_order_id": str(po_id)},
        follow_redirects=True,
    )
    with session_scope(app) as s:
        assert s.get(InvoiceReceivedEntry, iid).disposition == "po_matched"
    token = _csrf(client)
    # Unmatch then mark other
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/match-po",
        data={"csrf_token": token, "purchase_order_id": ""},
        follow_redirects=True,
    )
    token = _csrf(client)
    client.post(
        f"/admin/purchasing/invoices-received/{iid}/mark-other",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    with session_scope(app) as s:
        assert s.get(InvoiceReceivedEntry, iid).disposition == "other_payment"


# ---- 14 audit ----


def test_transitions_write_audit_with_file_metadata(app):
    import json

    with session_scope(app) as s:
        pay, keys = _seed_payment(s, with_line=False)
        storage = storage_from_config(app.config)
        for k in keys:
            storage.put_bytes(k, b"x", content_type="application/pdf")
        user = s.query(User).filter_by(email="admin@silq.tech").one()
        inv = migrate_payment_to_invoice(
            s,
            payment=pay,
            file_bytes=b"inv",
            filename="invoice.pdf",
            content_type="application/pdf",
            date_received=date.today(),
            user=user,
            storage=storage,
        )
        po = _seed_po(s)
        match_invoice_to_po(s, invoice=inv, purchase_order=po, user=user)
        unmatch_invoice_from_po(s, invoice=inv, user=user)
        mark_invoice_other_payment(s, invoice=inv, user=user)
        return_invoice_to_received(s, invoice=inv, user=user)
        return_invoice_to_upcoming(s, invoice=inv, user=user)
        s.flush()

        actions = {
            e.action: e
            for e in s.query(AuditEvent)
            .filter(
                AuditEvent.action.in_(
                    [
                        "payment_entry.invoice_received",
                        "payment_entry.returned_to_upcoming",
                        "invoice_received.po_matched",
                        "invoice_received.po_unmatched",
                        "invoice_received.marked_other",
                        "invoice_received.returned_to_received",
                    ]
                )
            )
            .all()
        }
        assert set(actions) == {
            "payment_entry.invoice_received",
            "payment_entry.returned_to_upcoming",
            "invoice_received.po_matched",
            "invoice_received.po_unmatched",
            "invoice_received.marked_other",
            "invoice_received.returned_to_received",
        }
        mig = actions["payment_entry.invoice_received"]
        assert mig.metadata_json
        meta = json.loads(mig.metadata_json)
        assert meta.get("files_moved")
        assert "invoice.pdf" in meta["files_moved"] or "quote.pdf" in meta["files_moved"]
        ret = actions["payment_entry.returned_to_upcoming"]
        assert ret.metadata_json
        assert json.loads(ret.metadata_json).get("files_moved")
