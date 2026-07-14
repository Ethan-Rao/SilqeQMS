"""
Prompt 22 — Quality Planning redesign + Design & Development Records accordion.

Covers:
- Task A: the dhfs library renders as an accordion (<details> tree).
- Task B1: four objectives, Employee Training removed, Q2 defaults visible.
- Task B2: Q3 2026 scorecard rendered with status badges (e.g. Needs Follow-Up).
- Task B3: Quality Plans & Reports section (empty-state tolerant).
- Read-only staff access + admin save.
"""
import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFolder


ADMIN_PERMS = ["admin.view", "admin.edit", "staff.view", "docs.view", "docs.download"]
STAFF_PERMS = ["staff.view", "docs.view", "docs.download"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    engine = application.extensions["sqlalchemy_engine"]
    tables = [
        Base.metadata.tables[t]
        for t in (
            "users", "roles", "permissions", "user_roles", "role_permissions",
            "audit_events", "system_settings", "admin_doc_folders", "admin_doc_files",
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        all_keys = sorted(set(ADMIN_PERMS + STAFF_PERMS))
        perms = {k: Permission(key=k, name=k) for k in all_keys}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms[k] for k in ADMIN_PERMS)
        staff_role = Role(key="staff", name="Staff")
        staff_role.permissions.extend(perms[k] for k in STAFF_PERMS)
        admin_user = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        admin_user.roles.append(admin_role)
        staff_user = User(email="staff@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        staff_user.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin_user, staff_user])
        s.flush()

        # A folder so the dhfs accordion renders a <details> node.
        s.add(AdminDocFolder(library_key="dhfs", name="Design History File",
                             created_by_user_id=admin_user.id))

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@example.com"):
    r = client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=False)
    assert r.status_code in (302, 303)


def _get_csrf(client):
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
        if not token:
            import secrets
            token = secrets.token_urlsafe(32)
            sess["csrf_token"] = token
        return token


def _url(app, endpoint, **kw):
    with app.test_request_context():
        from flask import url_for
        return url_for(endpoint, **kw)


# ── Task A: dhfs accordion ──────────────────────────────────────────────────

def test_dhfs_renders_accordion_admin_and_staff(client, app):
    url = _url(app, "admin_docs.dhfs")
    _login(client, "admin@example.com")
    r = client.get(url)
    assert r.status_code == 200
    assert "<details" in r.get_data(as_text=True)
    client.get("/auth/logout")
    _login(client, "staff@example.com")
    r = client.get(url)
    assert r.status_code == 200
    assert "<details" in r.get_data(as_text=True)


# ── Task B: Quality Planning page ───────────────────────────────────────────

def test_quality_planning_200_admin_and_staff(client, app):
    url = _url(app, "admin.quality_objectives")
    _login(client, "admin@example.com")
    assert client.get(url).status_code == 200
    client.get("/auth/logout")
    _login(client, "staff@example.com")
    assert client.get(url).status_code == 200


def test_quality_planning_removes_employee_training(client, app):
    """Objective 4 (Employee Training) removed — its target threshold is gone.

    ("Dynamic Employee Training Program" still appears as a Q3 scorecard action
    item, which is expected; only the objective row is removed.)
    """
    _login(client)
    body = client.get(_url(app, "admin.quality_objectives")).get_data(as_text=True)
    assert "training activities per year" not in body
    assert "≥ 10 training" not in body


def test_quality_planning_shows_new_objectives(client, app):
    _login(client)
    body = client.get(_url(app, "admin.quality_objectives")).get_data(as_text=True)
    assert "Incoming Material Quality" in body
    assert "Active Post-Market Surveillance" in body


def test_quality_planning_shows_q2_defaults(client, app):
    _login(client)
    body = client.get(_url(app, "admin.quality_objectives")).get_data(as_text=True)
    assert "N/A — no lots received" in body
    assert "Q2 2026" in body


def test_scorecard_badge_needs_follow_up_present(client, app):
    _login(client)
    body = client.get(_url(app, "admin.quality_objectives")).get_data(as_text=True)
    assert "Needs Follow-Up" in body
    assert "Q3 2026 Quality Plan Scorecard" in body


def test_admin_can_save_objectives(client, app):
    _login(client)
    csrf = _get_csrf(client)
    r = client.post(
        _url(app, "admin.quality_objectives_save"),
        data={
            "csrf_token": csrf,
            "incoming_lot_acceptance": "95%",
            "incoming_lot_acceptance_notes": "Improved",
            "incoming_lot_acceptance_period": "Q3 2026",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    # Value persisted and shown on reload.
    body = client.get(_url(app, "admin.quality_objectives")).get_data(as_text=True)
    assert "95%" in body


def test_admin_can_save_scorecard(client, app):
    _login(client)
    csrf = _get_csrf(client)
    r = client.post(
        _url(app, "admin.quality_scorecard_save"),
        data={
            "csrf_token": csrf,
            "scorecard_json": '[{"item": "Test Item", "owner": "QA", "target": "Q3 2026", "status": "In Progress", "notes": "n"}]',
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    body = client.get(_url(app, "admin.quality_objectives")).get_data(as_text=True)
    assert "Test Item" in body


def test_staff_cannot_save_objectives(client, app):
    _login(client, "staff@example.com")
    csrf = _get_csrf(client)
    r = client.post(
        _url(app, "admin.quality_objectives_save"),
        data={"csrf_token": csrf, "incoming_lot_acceptance": "1%"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 403)
