"""
Prompt 34 — Tracker file attachments, NRE detail cleanup, NCR embedded in CAPAs.

Covers:
- NRE detail page no longer renders the Project Tracker card.
- NRE tracker file attach / view / download / delete round-trip.
- Purchasing payment-entry file attach / delete round-trip + Files column.
- NCR accordion rendered inside the CAPAs list page.
- Dashboard NCRs card points at the CAPAs page.
"""
import datetime as dt
import io

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.models import NREProjectEntry, NRETrackerAttachment
from app.eqms.modules.purchasing.models import PaymentEntry, PaymentEntryAttachment

PW = "pw"
PERMS = [
    "admin.view", "admin.edit", "sales_orders.view", "sales_orders.edit",
    "purchasing.view", "purchasing.edit",
]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
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
        admin = User(email="admin@example.com", password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(role)
        s.add_all(list(perms.values()) + [role, admin])
        s.flush()

        c = Customer(company_key="fearsome", facility_name="Fearsome Limited", customer_type="nre")
        s.add(c)
        s.flush()

        # NCR library folder + file for the accordion
        folder = AdminDocFolder(library_key="ncrs", parent_id=None, name="2026")
        s.add(folder)
        s.flush()
        s.add(AdminDocFile(
            library_key="ncrs", folder_id=folder.id, filename="NCR-2026-001.pdf",
            storage_key="ncrs/NCR-2026-001.pdf", content_type="application/pdf",
            size_bytes=10, uploaded_by_user_id=admin.id,
        ))

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client):
    client.post("/auth/login", data={"email": "admin@example.com", "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


# --------------------------------------------------------------------------- #
# Part A — detail cleanup
# --------------------------------------------------------------------------- #
def test_detail_no_project_tracker(client, app):
    with session_scope(app) as s:
        cid = s.query(Customer).filter_by(company_key="fearsome").one().id
    _login(client)
    body = client.get(f"/admin/nre-projects/{cid}").data.decode()
    assert "Project Tracker" not in body
    assert "Sales Orders" in body


# --------------------------------------------------------------------------- #
# Part B — NRE tracker file attachments
# --------------------------------------------------------------------------- #
def test_nre_tracker_file_roundtrip(client, app):
    _login(client)
    token = _csrf(client)
    r = client.post("/admin/nre-projects/tracker/create",
                    json={"customer_name": "Fearsome Limited"}, headers={"X-CSRF-Token": token})
    eid = r.get_json()["entry"]["id"]

    # Upload
    data = {"csrf_token": token, "file": (io.BytesIO(b"hello pdf"), "invoice.pdf")}
    r = client.post(f"/admin/nre-projects/tracker/{eid}/files", data=data,
                    content_type="multipart/form-data", follow_redirects=False)
    assert r.status_code == 302
    with session_scope(app) as s:
        att = s.query(NRETrackerAttachment).filter_by(nre_entry_id=eid).one()
        att_id = att.id
        assert att.filename == "invoice.pdf"

    # Download
    r = client.get(f"/admin/nre-projects/tracker/files/{att_id}/download")
    assert r.status_code == 200
    assert r.data == b"hello pdf"

    # Index shows the file link
    body = client.get("/admin/nre-projects/").data.decode()
    assert "invoice.pdf" in body
    assert ">Files<" in body  # column header renamed from Notes

    # Delete
    r = client.post(f"/admin/nre-projects/tracker/files/{att_id}/delete",
                    data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 302
    with session_scope(app) as s:
        assert s.query(NRETrackerAttachment).filter_by(id=att_id).first() is None


# --------------------------------------------------------------------------- #
# Part B — Purchasing payment file attachments
# --------------------------------------------------------------------------- #
def test_payment_file_roundtrip(client, app):
    with session_scope(app) as s:
        e = PaymentEntry(vendor="Acme", amount=None)
        s.add(e)
        s.flush()
        eid = e.id
    _login(client)
    token = _csrf(client)

    data = {"csrf_token": token, "file": (io.BytesIO(b"po data"), "po.pdf")}
    r = client.post(f"/admin/purchasing/payments/{eid}/files", data=data,
                    content_type="multipart/form-data", follow_redirects=False)
    assert r.status_code == 302
    with session_scope(app) as s:
        att = s.query(PaymentEntryAttachment).filter_by(payment_entry_id=eid).one()
        att_id = att.id

    r = client.get(f"/admin/purchasing/payments/files/{att_id}/download")
    assert r.status_code == 200 and r.data == b"po data"

    body = client.get("/admin/purchasing").data.decode()
    assert "po.pdf" in body
    assert ">Files<" in body

    r = client.post(f"/admin/purchasing/payments/files/{att_id}/delete",
                    data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 302
    with session_scope(app) as s:
        assert s.query(PaymentEntryAttachment).filter_by(id=att_id).first() is None


# --------------------------------------------------------------------------- #
# Part C — NCR accordion in CAPAs + dashboard card
# --------------------------------------------------------------------------- #
def test_capas_list_shows_ncr_accordion(client):
    _login(client)
    body = client.get("/admin/capas").data.decode()
    assert "Non-Conformance Reports" in body
    assert "NCR-2026-001.pdf" in body
    assert "2026" in body  # NCR year folder


def test_dashboard_ncr_card_links_to_capas(client):
    _login(client)
    body = client.get("/admin/").data.decode()
    # NCRs card now points at the CAPAs page.
    assert 'href="/admin/capas"' in body
