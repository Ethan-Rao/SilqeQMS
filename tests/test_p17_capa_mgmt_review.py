"""
Prompt 17 — CAPA tracker + Management Review report.

Covers: CAPA list status badges, access control (list/detail = admin.view,
edit/new = admin.edit), create + duplicate rejection, and the management review
page (200 admin / 403 staff) + CSV section values.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.capas.models import CAPARecord


PW = "pw"
ADMIN_PERMS = ["admin.view", "admin.edit"]
STAFF_PERMS = ["admin.view", "staff.view"]


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

        s.add_all([
            CAPARecord(capa_number="CAPA001-2025", title="Open one", status="Open",
                       target_close_date=dt.date.today() - dt.timedelta(days=5)),
            CAPARecord(capa_number="CAPA002-2025", title="Pending one", status="Pending Effectiveness"),
            CAPARecord(capa_number="CAPA003-2025", title="Closed one", status="Closed"),
            CAPARecord(capa_number="CAPA004-2025", title="Cancelled one", status="Cancelled"),
        ])

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


# --------------------------------------------------------------------------- #
# Task A — CAPA tracker
# --------------------------------------------------------------------------- #
def test_capa_list_status_badges(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/capas")
    assert r.status_code == 200
    body = r.data.decode()
    assert "badge--warning" in body   # Open
    assert "badge--info" in body      # Pending Effectiveness
    assert "badge--success" in body   # Closed
    assert "CAPA001-2025" in body
    assert "d overdue" in body        # CAPA001 target close is in the past


def test_capa_list_detail_visible_to_staff(client, app):
    _login(client, "staff@example.com")
    assert client.get("/admin/capas").status_code == 200
    with session_scope(app) as s:
        capa_id = s.query(CAPARecord).filter_by(capa_number="CAPA001-2025").one().id
    assert client.get(f"/admin/capas/{capa_id}").status_code == 200


def test_capa_edit_requires_admin_edit(client, app):
    with session_scope(app) as s:
        capa_id = s.query(CAPARecord).filter_by(capa_number="CAPA001-2025").one().id
    _login(client, "staff@example.com")
    assert client.get(f"/admin/capas/{capa_id}/edit").status_code == 403
    assert client.get("/admin/capas/new").status_code == 403
    r = client.post("/admin/capas/new",
                    data={"capa_number": "CAPA999-2025", "title": "X", "csrf_token": _csrf(client)})
    assert r.status_code == 403


def test_capa_create_and_duplicate(client, app):
    _login(client, "admin@example.com")
    token = _csrf(client)
    r = client.post("/admin/capas/new",
                    data={"capa_number": "CAPA010-2026", "title": "New CAPA", "status": "Open",
                          "csrf_token": token},
                    follow_redirects=False)
    assert r.status_code == 302
    with session_scope(app) as s:
        assert s.query(CAPARecord).filter_by(capa_number="CAPA010-2026").count() == 1

    # Duplicate is rejected (no second row).
    r = client.post("/admin/capas/new",
                    data={"capa_number": "CAPA010-2026", "title": "Dup", "csrf_token": _csrf(client)},
                    follow_redirects=True)
    assert r.status_code == 200
    with session_scope(app) as s:
        assert s.query(CAPARecord).filter_by(capa_number="CAPA010-2026").count() == 1


def test_capa_edit_updates_status(client, app):
    with session_scope(app) as s:
        capa_id = s.query(CAPARecord).filter_by(capa_number="CAPA002-2025").one().id
    _login(client, "admin@example.com")
    r = client.post(f"/admin/capas/{capa_id}/edit",
                    data={"title": "Pending one", "status": "Closed",
                          "closed_date": "2026-06-01", "csrf_token": _csrf(client)},
                    follow_redirects=False)
    assert r.status_code == 302
    with session_scope(app) as s:
        capa = s.get(CAPARecord, capa_id)
        assert capa.status == "Closed"
        assert capa.closed_date == dt.date(2026, 6, 1)


# --------------------------------------------------------------------------- #
# Task B — Management Review report
# --------------------------------------------------------------------------- #
def test_management_review_admin_200_staff_403(client):
    _login(client, "staff@example.com")
    assert client.get("/admin/reports/management-review").status_code == 403

    _login(client, "admin@example.com")
    r = client.get("/admin/reports/management-review")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Management Review Report" in body
    assert "6. CAPAs" in body


def test_management_review_csv_sections(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/reports/management-review?format=csv")
    assert r.status_code == 200
    assert r.mimetype == "text/csv"
    body = r.data.decode()
    lines = body.splitlines()
    assert lines[0] == "section,item,value"
    sections = {ln.split(",")[0] for ln in lines[1:] if ln}
    assert "1. Document Control Activity" in sections
    assert "6. CAPAs" in sections
    assert "8. Purchasing / Supplier Performance" in sections
