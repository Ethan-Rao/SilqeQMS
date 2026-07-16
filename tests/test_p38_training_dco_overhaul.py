"""
Prompt 38 — Training overhaul: DCO auto-qualification on release, access control,
per-employee card filtering, and library subtitle.

Covers:
- DocumentRevision.dco_number column + release flow auto-creating dco_auto_qualified
  training records for checked approvers.
- Release form UI exposes the DCO number field + approver checkboxes.
- manage_index redirects non-managers to My Training and excludes service accounts
  (no display_name) from the per-employee cards.
- Training Record Archive subtitle.
- Weekly Brief section ordering (NRE tracker above Upcoming Payments).
"""
import datetime as dt
import os

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFolder
from app.eqms.modules.document_control.models import Document, DocumentFile, DocumentRevision
from app.eqms.modules.training.models import TrainingAssignment

PW = "pw"
ADMIN_PERMS = [
    "admin.view", "admin.edit", "staff.view", "docs.view", "docs.edit",
    "docs.release", "docs.obsolete", "training.view", "training.manage",
]
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
        brian = User(email="brianm@silq.tech", display_name="Brian McVerry",
                     password_hash=generate_password_hash(PW), is_active=True)
        brian.roles.append(staff_role)
        chuck = User(email="chuckg@silq.tech", display_name="Chuck Greiner",
                     password_hash=generate_password_hash(PW), is_active=True)
        chuck.roles.append(staff_role)
        # Service/legacy account: active but no display_name — should be excluded
        # from per-employee cards (P38 Part E).
        service = User(email="earao72419@gmail.com", display_name=None,
                       password_hash=generate_password_hash(PW), is_active=True)
        service.roles.append(staff_role)

        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, brian, chuck, service])
        s.flush()
        oid = admin.id

        s.add(AdminDocFolder(library_key="employee_training", name="EthanRao", created_by_user_id=oid))

        # Draft document with a revision + file, ready to release.
        d = Document(doc_number="QM.SLQ099", title="Test SOP", doc_type="SOP",
                     category=None, owner_user_id=oid, status="Draft")
        s.add(d)
        s.flush()
        r = DocumentRevision(document_id=d.id, revision="A", change_summary="",
                             created_by_user_id=oid)
        s.add(r)
        s.flush()
        s.add(DocumentFile(revision_id=r.id, storage_key="documents/QM.SLQ099/rev-A/x.pdf",
                           filename="x.pdf", content_type="application/pdf",
                           sha256="0" * 64, size_bytes=10, uploaded_by_user_id=oid))

        # A pre-acknowledged DCO record for the service account so we can prove the
        # per-employee cards filter it out.
        s.add(TrainingAssignment(
            item_type="free_text", item_title="Service item",
            assigned_to_user_id=service.id, assigned_by_user_id=oid,
            training_type="read_acknowledge",
        ))
        s.add(TrainingAssignment(
            item_type="free_text", item_title="Brian item",
            assigned_to_user_id=brian.id, assigned_by_user_id=oid,
            training_type="read_acknowledge",
        ))

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


def _doc_id(app):
    with session_scope(app) as s:
        return s.query(Document).filter(Document.doc_number == "QM.SLQ099").one().id


def _rev_id(app):
    with session_scope(app) as s:
        return s.query(DocumentRevision).one().id


# --------------------------------------------------------------------------- #
# B2 — dco_number column + release flow
# --------------------------------------------------------------------------- #
def test_document_revision_has_dco_number_column():
    assert hasattr(DocumentRevision, "dco_number")


def test_release_form_shows_dco_fields(client, app):
    _login(client, "ethanr@silq.tech")
    body = client.get(_url(app, "doc_control.document_detail", doc_id=_doc_id(app))).get_data(as_text=True)
    assert "DCO Number" in body
    assert 'name="dco_approvers"' in body
    # Real employees listed; service account (no display_name) is not.
    assert "Brian McVerry" in body
    assert "earao72419" not in body


def test_release_with_dco_creates_auto_qualified_records(client, app):
    _login(client, "ethanr@silq.tech")
    token = _csrf(client)
    bid = _uid(app, "brianm@silq.tech")
    cid = _uid(app, "chuckg@silq.tech")
    r = client.post(
        _url(app, "doc_control.release_revision", doc_id=_doc_id(app), rev_id=_rev_id(app)),
        data={
            "csrf_token": token,
            "reason": "Initial release",
            "effective_date": "2026-07-16",
            "dco_number": "DCO097",
            "dco_approvers": [str(bid), str(cid)],
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        rows = (s.query(TrainingAssignment)
                .filter(TrainingAssignment.training_type == "dco_auto_qualified",
                        TrainingAssignment.source_reference == "DCO097")
                .all())
        assert {a.assigned_to_user_id for a in rows} == {bid, cid}
        for a in rows:
            assert a.acknowledged_at is not None
        rev = s.query(DocumentRevision).one()
        assert rev.dco_number == "DCO097"
        assert rev.document.status == "Released"


def test_release_without_approvers_still_releases(client, app):
    _login(client, "ethanr@silq.tech")
    token = _csrf(client)
    r = client.post(
        _url(app, "doc_control.release_revision", doc_id=_doc_id(app), rev_id=_rev_id(app)),
        data={
            "csrf_token": token,
            "reason": "Initial release",
            "dco_number": "DCO097",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.query(TrainingAssignment).filter(
            TrainingAssignment.training_type == "dco_auto_qualified"
        ).count() == 0
        assert s.query(DocumentRevision).one().document.status == "Released"


# --------------------------------------------------------------------------- #
# C1 — non-managers redirected to My Training
# --------------------------------------------------------------------------- #
def test_non_admin_redirected_from_training_admin(client, app):
    _login(client, "brianm@silq.tech")
    r = client.get(_url(app, "training.manage_index"), follow_redirects=False)
    assert r.status_code == 302
    assert "/admin/my-training" in r.headers["Location"]


# --------------------------------------------------------------------------- #
# Part E — service accounts excluded from per-employee cards
# --------------------------------------------------------------------------- #
def test_service_account_excluded_from_cards(client, app):
    _login(client, "ethanr@silq.tech")
    body = client.get(_url(app, "training.manage_index")).get_data(as_text=True)
    bid = _uid(app, "brianm@silq.tech")
    sid = _uid(app, "earao72419@gmail.com")
    # Per-employee cards link to each user's training record. Brian (a real
    # employee) has a card; the service account does not.
    assert _url(app, "training.user_training", user_id=bid) in body
    assert _url(app, "training.user_training", user_id=sid) not in body


# --------------------------------------------------------------------------- #
# A1 — Training Record Archive subtitle
# --------------------------------------------------------------------------- #
def test_training_record_archive_subtitle(client, app):
    _login(client, "ethanr@silq.tech")
    lib = client.get(_url(app, "admin_docs.employee_training")).get_data(as_text=True)
    assert "Training Record Archive" in lib
    dash = client.get(_url(app, "admin.index")).get_data(as_text=True)
    assert "Training Record Archive" in dash


# --------------------------------------------------------------------------- #
# Weekly Brief — NRE tracker above Upcoming Payments
# --------------------------------------------------------------------------- #
def test_weekly_brief_nre_above_payments():
    path = os.path.join(
        os.path.dirname(__file__), "..", "app", "eqms", "templates", "email", "weekly_brief.html"
    )
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert text.index("NRE Invoice Tracker") < text.index("Upcoming Payments")
