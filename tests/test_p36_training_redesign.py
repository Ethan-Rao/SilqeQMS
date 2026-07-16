"""
Prompt 36 — Training module redesign.

Covers:
- New model fields (training_type, source_reference) and EffectivenessReview.
- matrix_required_for_doc_numbers helper.
- Pre-acknowledged (backdated / DCO auto-qualified) assignment creation.
- Matrix / user-detail / effectiveness routes (200 admin, 403 staff).
- Effectiveness create + delete.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.document_control.models import Document, DocumentRevision
from app.eqms.modules.training.models import EffectivenessReview, TrainingAssignment
from app.eqms.modules.training.service import matrix_required_for_doc_numbers

PW = "pw"
ADMIN_PERMS = ["admin.view", "admin.edit", "docs.view", "training.view", "training.manage"]
STAFF_PERMS = ["admin.view", "docs.view", "training.view"]


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
        # Emails chosen so matrix fragments match ("ethan", "christ").
        admin = User(email="ethan@silq.tech", display_name="Ethan Rao",
                     password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(admin_role)
        staff = User(email="christ@silq.tech", display_name="Chris Turner",
                     password_hash=generate_password_hash(PW), is_active=True)
        staff.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, staff])
        s.flush()
        owner = admin.id

        def _doc(number, title, revs=("A",)):
            d = Document(doc_number=number, title=title, doc_type="SOP", category=None,
                         owner_user_id=owner, status="Released")
            s.add(d)
            s.flush()
            last = None
            for i, label in enumerate(revs):
                r = DocumentRevision(document_id=d.id, revision=label, change_summary="",
                                     effective_date=dt.date(2024 + i, 1, 1), created_by_user_id=owner,
                                     released_at=dt.datetime(2024 + i, 1, 2), released_by_user_id=owner)
                s.add(r)
                s.flush()
                last = r
            d.current_revision_id = last.id
            return d

        _doc("QM.SLQ035", "Quality Policy", revs=("D",))
        _doc("QM.SLQ001", "Document Control SOP", revs=("A", "B"))

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


def _uid(app, email):
    with session_scope(app) as s:
        return s.query(User).filter(User.email == email).one().id


def _doc_id(app, number):
    with session_scope(app) as s:
        return s.query(Document).filter(Document.doc_number == number).one().id


# --------------------------------------------------------------------------- #
# Matrix helper
# --------------------------------------------------------------------------- #
def test_matrix_required_helper():
    req = matrix_required_for_doc_numbers("christ@silq.tech")
    assert "QM.SLQ035" in req  # "all"
    assert "QM.SLQ001" in req  # "christ" fragment
    # A random email only gets the "all" docs.
    base = matrix_required_for_doc_numbers("nobody@example.com")
    assert "QM.SLQ035" in base
    assert "QM.SLQ001" not in base


# --------------------------------------------------------------------------- #
# Routes: access control + render
# --------------------------------------------------------------------------- #
def test_matrix_page_renders_for_admin(client):
    _login(client, "ethan@silq.tech")
    r = client.get("/admin/training/matrix")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Training Matrix" in body
    assert "QM.SLQ035" in body


def test_matrix_blocked_for_staff(client):
    _login(client, "christ@silq.tech")
    assert client.get("/admin/training/matrix").status_code == 403


def test_user_detail_renders(client, app):
    _login(client, "ethan@silq.tech")
    cid = _uid(app, "christ@silq.tech")
    r = client.get(f"/admin/training/user/{cid}")
    assert r.status_code == 200
    body = r.data.decode()
    assert "User Training Record" in body
    assert "QM.SLQ001" in body  # christ is required on QM.SLQ001


def test_effectiveness_blocked_for_staff(client):
    _login(client, "christ@silq.tech")
    assert client.get("/admin/training/effectiveness").status_code == 403


# --------------------------------------------------------------------------- #
# Pre-acknowledged / DCO auto-qualified assignment
# --------------------------------------------------------------------------- #
def test_new_post_dco_preacknowledged(client, app):
    _login(client, "ethan@silq.tech")
    token = _csrf(client)
    cid = _uid(app, "christ@silq.tech")
    did = _doc_id(app, "QM.SLQ001")
    r = client.post("/admin/training/new", data={
        "csrf_token": token,
        "item_type": "document",
        "document_id": str(did),
        "user_ids": str(cid),
        "training_type": "dco_auto_qualified",
        "source_reference": "DCO-096",
        "acknowledged_date": "2026-07-16",
    }, follow_redirects=True)
    assert r.status_code == 200
    with session_scope(app) as s:
        a = (s.query(TrainingAssignment)
             .filter(TrainingAssignment.assigned_to_user_id == cid,
                     TrainingAssignment.document_id == did)
             .one())
        assert a.acknowledged_at is not None
        assert a.acknowledged_at.date() == dt.date(2026, 7, 16)
        assert a.training_type == "dco_auto_qualified"
        assert a.source_reference == "DCO-096"


def test_preacknowledged_coexists_with_open(client, app):
    """A pending open item and a pre-acknowledged record can both exist."""
    _login(client, "ethan@silq.tech")
    token = _csrf(client)
    cid = _uid(app, "christ@silq.tech")
    did = _doc_id(app, "QM.SLQ001")

    # 1) Pending assignment (no ack date).
    client.post("/admin/training/new", data={
        "csrf_token": token, "item_type": "document", "document_id": str(did),
        "user_ids": str(cid),
    }, follow_redirects=True)
    # 2) Pre-acknowledged historical record.
    client.post("/admin/training/new", data={
        "csrf_token": token, "item_type": "document", "document_id": str(did),
        "user_ids": str(cid), "acknowledged_date": "2025-01-01",
        "training_type": "document_originator", "source_reference": "Authored QM.SLQ001 Rev A",
    }, follow_redirects=True)

    with session_scope(app) as s:
        rows = (s.query(TrainingAssignment)
                .filter(TrainingAssignment.assigned_to_user_id == cid,
                        TrainingAssignment.document_id == did)
                .all())
        assert len(rows) == 2
        assert any(a.acknowledged_at is None for a in rows)
        assert any(a.acknowledged_at is not None for a in rows)


# --------------------------------------------------------------------------- #
# Effectiveness create + delete
# --------------------------------------------------------------------------- #
def test_effectiveness_create_and_delete(client, app):
    _login(client, "ethan@silq.tech")
    token = _csrf(client)
    cid = _uid(app, "christ@silq.tech")

    r = client.post("/admin/training/effectiveness/create", data={
        "csrf_token": token, "user_id": str(cid), "review_year": "2026",
        "review_date": "2026-03-01", "score": "9.0", "notes": "Strong",
    }, follow_redirects=True)
    assert r.status_code == 200
    with session_scope(app) as s:
        rev = s.query(EffectivenessReview).filter(EffectivenessReview.user_id == cid).one()
        rid = rev.id
        assert rev.passed is True  # score >= 7 auto-pass
        assert rev.review_year == 2026

    r = client.post(f"/admin/training/effectiveness/{rid}/delete",
                    data={"csrf_token": token}, follow_redirects=True)
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.query(EffectivenessReview).filter(EffectivenessReview.id == rid).first() is None
