"""
Prompt 35 — Weekly Brief email tool.

Covers:
- GET /admin/reports/weekly-brief renders the form for admins (200) and is
  blocked for read-only staff (403).
- POST with empty recipients → error flash, no send attempt.
- POST with recipients but no RESEND_API_KEY → meaningful error, no crash.
- Reports index links to the tool.
"""
import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User

PW = "pw"
ADMIN_PERMS = ["admin.view", "admin.edit"]
STAFF_PERMS = ["admin.view", "staff.view"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
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


def test_get_renders_form_for_admin(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/reports/weekly-brief")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Weekly Brief" in body
    assert 'name="to_emails"' in body


def test_get_blocked_for_staff(client):
    _login(client, "staff@example.com")
    assert client.get("/admin/reports/weekly-brief").status_code == 403


def test_reports_index_links_tool(client):
    _login(client, "admin@example.com")
    body = client.get("/admin/reports").data.decode()
    assert "/admin/reports/weekly-brief" in body


def test_send_empty_recipients_errors(client):
    _login(client, "admin@example.com")
    token = _csrf(client)
    r = client.post("/admin/reports/weekly-brief/send",
                    data={"csrf_token": token, "to_emails": "  \n , "},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "at least one recipient" in r.data.decode().lower()


def test_send_without_api_key_errors_gracefully(client):
    _login(client, "admin@example.com")
    token = _csrf(client)
    r = client.post("/admin/reports/weekly-brief/send",
                    data={"csrf_token": token, "to_emails": "person@example.com"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "RESEND_API_KEY is not configured" in r.data.decode()
