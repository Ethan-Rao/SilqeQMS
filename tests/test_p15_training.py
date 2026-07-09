"""
Prompt 15 (Phase 7) — Training activation UX.

Covers: /admin/training/export.csv (200 + text/csv + headers for training.manage,
403 for staff), bulk-assign by doc-number list (creates N assignments, skips unknown
with a warning flash), and the My Training pulsing overdue badge.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.document_control.models import Document, DocumentRevision
from app.eqms.modules.training.models import TrainingAssignment


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
        admin = User(email="admin@example.com", password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(admin_role)
        staff = User(email="staff@example.com", password_hash=generate_password_hash(PW), is_active=True)
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

        _doc("QM.SLQ001", "Document Control SOP", revs=("A", "B"))
        _doc("QM.SLQ052", "Design Control Changes SOP", revs=("A",))

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


# --------------------------------------------------------------------------- #
# A2 — export.csv
# --------------------------------------------------------------------------- #
def test_export_csv_ok_for_manager(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/training/export.csv")
    assert r.status_code == 200
    assert r.mimetype == "text/csv"
    header = r.data.decode().splitlines()[0]
    assert header == "user_email,document,revision,assigned_date,due_date,acknowledged_at,status"


def test_export_csv_forbidden_for_staff(client):
    _login(client, "staff@example.com")
    r = client.get("/admin/training/export.csv")
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# A3 — bulk assign by document list
# --------------------------------------------------------------------------- #
def test_bulk_assign_creates_and_skips_unknown(client, app):
    _login(client, "admin@example.com")
    staff_id = _uid(app, "staff@example.com")
    r = client.post(
        "/admin/training/new",
        data={
            "item_type": "document",
            "bulk_doc_numbers": "QM.SLQ001\nQM.SLQ052\nQM.SLQ999",
            "user_ids": [str(staff_id)],
            "due_date": "2026-07-31",
            "csrf_token": _csrf(client),
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    body = r.data.decode()
    # Two valid docs -> two assignments; one unknown skipped with a warning.
    assert "2 assignment(s) created across 2 document(s)" in body
    assert "QM.SLQ999" in body  # named in the skipped-warning flash

    with session_scope(app) as s:
        rows = s.query(TrainingAssignment).filter(
            TrainingAssignment.assigned_to_user_id == staff_id
        ).all()
        assert len(rows) == 2
        assert all(a.item_type == "document" and a.document_revision_id is not None for a in rows)


# --------------------------------------------------------------------------- #
# A1 — pulsing overdue badge on My Training
# --------------------------------------------------------------------------- #
def test_my_training_shows_overdue_badge(client, app):
    staff_id = _uid(app, "staff@example.com")
    with session_scope(app) as s:
        s.add(TrainingAssignment(
            item_type="free_text", item_title="Read the overdue thing",
            assigned_to_user_id=staff_id,
            due_date=dt.date.today() - dt.timedelta(days=3),
            acknowledged_at=None,
        ))

    _login(client, "staff@example.com")
    r = client.get("/admin/my-training")
    assert r.status_code == 200
    assert "badge--overdue" in r.data.decode()
