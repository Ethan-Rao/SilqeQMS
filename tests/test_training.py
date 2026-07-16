"""Checkpoint 4: Employee Training read-and-acknowledge (QM.SLQ003).

Covers the status helper, admin assignment, per-user queue isolation (a staff
user can never see or acknowledge another user's items), the acknowledge audit
event, and read-only gating of the admin manage routes for staff.
"""
from datetime import date, datetime, timedelta

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.training.models import TrainingAssignment
from app.eqms.modules.training.service import assignment_status


PW = "pw"
PERM_KEYS = [
    ("admin.view", "Admin: view shell"),
    ("admin.edit", "Admin: edit"),
    ("docs.view", "Docs: view"),
    ("training.view", "Training: view own"),
    ("training.manage", "Training: manage"),
]
STAFF_KEYS = ["admin.view", "docs.view", "training.view"]


# --------------------------------------------------------------------------- #
# Status helper (pure)
# --------------------------------------------------------------------------- #

def _mk(ack=None, due=None):
    return TrainingAssignment(
        item_type="free_text", item_title="X", assigned_to_user_id=1,
        acknowledged_at=ack, due_date=due,
    )


def test_assignment_status_states():
    today = date(2026, 7, 8)
    assert assignment_status(_mk(ack=datetime(2026, 7, 1)), today)["state"] == "acknowledged"
    assert assignment_status(_mk(due=today - timedelta(days=1)), today)["state"] == "overdue"
    assert assignment_status(_mk(due=today + timedelta(days=3)), today)["state"] == "due_soon"
    assert assignment_status(_mk(due=today + timedelta(days=60)), today)["state"] == "open"
    assert assignment_status(_mk(), today)["state"] == "open"


# --------------------------------------------------------------------------- #
# App-backed
# --------------------------------------------------------------------------- #

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
        admin = User(email="admin@example.com", password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(admin_role)

        staff_role = Role(key="staff", name="Staff (read-only)")
        for key in STAFF_KEYS:
            staff_role.permissions.append(perms[key])
        staff1 = User(email="staff1@example.com", password_hash=generate_password_hash(PW), is_active=True)
        staff2 = User(email="staff2@example.com", password_hash=generate_password_hash(PW), is_active=True)
        staff1.roles.append(staff_role)
        staff2.roles.append(staff_role)

        s.add_all([admin_role, admin, staff_role, staff1, staff2])

    return app


def _login(client, email):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            sess["csrf_token"] = token
        return token


def _uid(app, email):
    with session_scope(app) as s:
        return s.query(User).filter(User.email == email).one().id


def _assign_free_text(client, title, user_ids, due=None):
    data = {
        "item_type": "free_text",
        "free_text_title": title,
        "instructions": "Please read.",
        "user_ids": [str(u) for u in user_ids],
        "csrf_token": _csrf(client),
    }
    if due:
        data["due_date"] = due
    return client.post("/admin/training/new", data=data, follow_redirects=True)


def test_admin_assigns_and_only_assignee_sees_item(app):
    client = app.test_client()
    _login(client, "admin@example.com")
    s1 = _uid(app, "staff1@example.com")
    r = _assign_free_text(client, "Gowning SOP read", [s1])
    assert r.status_code == 200

    with session_scope(app) as s:
        rows = s.query(TrainingAssignment).all()
        assert len(rows) == 1
        assert rows[0].assigned_to_user_id == s1
        assert rows[0].item_title == "Gowning SOP read"

    # staff1 sees it
    c1 = app.test_client()
    _login(c1, "staff1@example.com")
    r1 = c1.get("/admin/my-training")
    assert r1.status_code == 200
    assert b"Gowning SOP read" in r1.data

    # staff2 does not
    c2 = app.test_client()
    _login(c2, "staff2@example.com")
    r2 = c2.get("/admin/my-training")
    assert r2.status_code == 200
    assert b"Gowning SOP read" not in r2.data


def test_staff_cannot_acknowledge_another_users_item(app):
    client = app.test_client()
    _login(client, "admin@example.com")
    s1 = _uid(app, "staff1@example.com")
    _assign_free_text(client, "Item for staff1", [s1])

    with session_scope(app) as s:
        aid = s.query(TrainingAssignment).one().id

    # staff2 attempts to acknowledge staff1's item
    c2 = app.test_client()
    _login(c2, "staff2@example.com")
    r = c2.post(
        f"/admin/my-training/{aid}/acknowledge",
        data={"csrf_token": _csrf(c2)},
        follow_redirects=False,
    )
    assert r.status_code == 403

    with session_scope(app) as s:
        assert s.query(TrainingAssignment).one().acknowledged_at is None


def test_acknowledge_marks_and_writes_audit(app):
    client = app.test_client()
    _login(client, "admin@example.com")
    s1 = _uid(app, "staff1@example.com")
    _assign_free_text(client, "Ack me", [s1])
    with session_scope(app) as s:
        aid = s.query(TrainingAssignment).one().id

    c1 = app.test_client()
    _login(c1, "staff1@example.com")
    r = c1.post(
        f"/admin/my-training/{aid}/acknowledge",
        data={"csrf_token": _csrf(c1)},
        follow_redirects=True,
    )
    assert r.status_code == 200

    with session_scope(app) as s:
        a = s.query(TrainingAssignment).one()
        assert a.acknowledged_at is not None
        ev = (
            s.query(AuditEvent)
            .filter(AuditEvent.action == "training.acknowledge", AuditEvent.entity_id == str(aid))
            .one()
        )
        assert ev.actor_user_email == "staff1@example.com"


def test_staff_cannot_reach_manage_routes(app):
    c1 = app.test_client()
    _login(c1, "staff1@example.com")
    # P38 C1: non-managers who hit the admin index are redirected to their own
    # queue instead of getting a hard 403.
    r_index = c1.get("/admin/training", follow_redirects=False)
    assert r_index.status_code == 302
    assert "/admin/my-training" in r_index.headers["Location"]
    # The actual management routes remain hard-gated.
    assert c1.get("/admin/training/new").status_code == 403
    r = c1.post(
        "/admin/training/new",
        data={"item_type": "free_text", "free_text_title": "x", "user_ids": [str(_uid(app, "staff1@example.com"))], "csrf_token": _csrf(c1)},
        follow_redirects=False,
    )
    assert r.status_code == 403
    with session_scope(app) as s:
        assert s.query(TrainingAssignment).count() == 0


def test_admin_can_reach_manage(app):
    client = app.test_client()
    _login(client, "admin@example.com")
    assert client.get("/admin/training").status_code == 200
    assert client.get("/admin/training/new").status_code == 200


def test_reassigning_open_item_is_idempotent(app):
    client = app.test_client()
    _login(client, "admin@example.com")
    s1 = _uid(app, "staff1@example.com")
    _assign_free_text(client, "Dup item", [s1])
    _assign_free_text(client, "Dup item", [s1])
    with session_scope(app) as s:
        assert s.query(TrainingAssignment).filter(TrainingAssignment.item_title == "Dup item").count() == 1
