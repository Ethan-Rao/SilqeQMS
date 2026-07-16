"""
Prompt 37 — Training Records overhaul + My Training fixes.

Covers:
- Training Records library label rename.
- Per-user scoping of the employee_training accordion (staff sees only own folder).
- DCO Batch Qualification tool (render, access control, end-to-end record creation).
- My Training Pending/Acknowledged sections with DCO Auto badge.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFolder
from app.eqms.modules.document_control.models import Document, DocumentRevision
from app.eqms.modules.training.models import TrainingAssignment

PW = "pw"
ADMIN_PERMS = ["admin.view", "admin.edit", "staff.view", "docs.view", "training.view", "training.manage"]
STAFF_PERMS = ["admin.view", "staff.view", "docs.view", "training.view"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        keys = sorted(set(ADMIN_PERMS + STAFF_PERMS))
        perms = {k: Permission(key=k, name=k) for k in keys}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms[k] for k in ADMIN_PERMS)
        staff_role = Role(key="staff", name="Staff")
        staff_role.permissions.extend(perms[k] for k in STAFF_PERMS)
        admin = User(email="ethanr@silq.tech", display_name="Ethan Rao",
                     password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(admin_role)
        staff = User(email="brianm@silq.tech", display_name="Brian McVerry",
                     password_hash=generate_password_hash(PW), is_active=True)
        staff.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, staff])
        s.flush()
        oid = admin.id

        # Training Records (employee_training) top-level folders.
        for name in ("EthanRao", "BrianMcVerry", "VerneSharma"):
            s.add(AdminDocFolder(library_key="employee_training", name=name, created_by_user_id=oid))

        # A controlled document for DCO qualification.
        d = Document(doc_number="QM.SLQ001", title="Document Control SOP", doc_type="SOP",
                     category=None, owner_user_id=oid, status="Released")
        s.add(d)
        s.flush()
        r = DocumentRevision(document_id=d.id, revision="A", change_summary="",
                             effective_date=dt.date(2024, 1, 1), created_by_user_id=oid,
                             released_at=dt.datetime(2024, 1, 2), released_by_user_id=oid)
        s.add(r)
        s.flush()
        d.current_revision_id = r.id

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


def _url(app, endpoint, **kw):
    with app.test_request_context():
        from flask import url_for
        return url_for(endpoint, **kw)


def _uid(app, email):
    with session_scope(app) as s:
        return s.query(User).filter(User.email == email).one().id


# --------------------------------------------------------------------------- #
# Task 1 — label rename
# --------------------------------------------------------------------------- #
def test_library_titled_training_records(client, app):
    _login(client, "ethanr@silq.tech")
    body = client.get(_url(app, "admin_docs.employee_training")).get_data(as_text=True)
    assert "Training Records" in body
    assert "Employee Training" not in body


# --------------------------------------------------------------------------- #
# Task 3 — per-user scoping
# --------------------------------------------------------------------------- #
def test_staff_sees_only_own_folder(client, app):
    _login(client, "brianm@silq.tech")
    body = client.get(_url(app, "admin_docs.employee_training")).get_data(as_text=True)
    assert "BrianMcVerry" in body
    assert "EthanRao" not in body
    assert "VerneSharma" not in body


def test_admin_sees_all_folders(client, app):
    _login(client, "ethanr@silq.tech")
    body = client.get(_url(app, "admin_docs.employee_training")).get_data(as_text=True)
    assert "EthanRao" in body
    assert "BrianMcVerry" in body
    assert "VerneSharma" in body


# --------------------------------------------------------------------------- #
# Task 7 — DCO Batch Qualification
# --------------------------------------------------------------------------- #
def test_dco_qualify_page_admin_only(client, app):
    _login(client, "brianm@silq.tech")
    assert client.get(_url(app, "training.dco_qualify_get")).status_code == 403
    client.get("/auth/logout")
    _login(client, "ethanr@silq.tech")
    assert client.get(_url(app, "training.dco_qualify_get")).status_code == 200


def test_dco_qualify_creates_records(client, app):
    _login(client, "ethanr@silq.tech")
    token = _csrf(client)
    bid = _uid(app, "brianm@silq.tech")
    r = client.post(_url(app, "training.dco_qualify_post"), data={
        "csrf_token": token,
        "dco_number": "DCO-091",
        "doc_numbers": "QM.SLQ001",
        "approval_date": "2026-07-16",
        "approver_ids": str(bid),
    }, follow_redirects=True)
    assert r.status_code == 200
    with session_scope(app) as s:
        a = (s.query(TrainingAssignment)
             .filter(TrainingAssignment.assigned_to_user_id == bid)
             .one())
        assert a.training_type == "dco_auto_qualified"
        assert a.source_reference == "DCO-091"
        assert a.acknowledged_at is not None
        assert a.acknowledged_at.date() == dt.date(2026, 7, 16)


# --------------------------------------------------------------------------- #
# Task 8 — My Training sections + DCO badge
# --------------------------------------------------------------------------- #
def test_my_training_shows_sections_and_dco_badge(client, app):
    # First create a DCO-qualified (pre-acknowledged) record for Brian.
    _login(client, "ethanr@silq.tech")
    token = _csrf(client)
    bid = _uid(app, "brianm@silq.tech")
    client.post(_url(app, "training.dco_qualify_post"), data={
        "csrf_token": token, "dco_number": "DCO-091", "doc_numbers": "QM.SLQ001",
        "approval_date": "2026-07-16", "approver_ids": str(bid),
    }, follow_redirects=True)
    client.get("/auth/logout")

    _login(client, "brianm@silq.tech")
    body = client.get(_url(app, "training.my_training")).get_data(as_text=True)
    assert "Pending" in body
    assert "Acknowledged" in body
    assert "DCO Auto" in body
    assert "DCO-091" in body
