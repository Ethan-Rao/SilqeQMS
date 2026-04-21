from __future__ import annotations

import csv
import io
import os
import sys

import pytest
from werkzeug.security import generate_password_hash

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture()
def log_client(tmp_path, monkeypatch):
    from app.eqms import create_app
    from app.eqms.db import session_scope
    from app.eqms.models import Permission, Role, User
    from app.eqms.modules.auditor_portal import fs as auditor_fs

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'l.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "blobs"))
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    auditor_fs.reset_auditor_root_cache_for_tests()
    root = tmp_path / "Auditor Files"
    (root / "A").mkdir(parents=True)
    (root / "A" / "f.txt").write_text("ok", encoding="utf-8")

    app = create_app()
    app.config["_schema_health_ok"] = True
    app.config["AUDITOR_PORTAL_ENABLED"] = "1"
    app.config["AUDITOR_FILES_ROOT"] = str(root)

    engine = app.extensions["sqlalchemy_engine"]
    from tests._auditor_schema import create_auditor_test_schema

    create_auditor_test_schema(engine, include_admin_docs=False)

    with session_scope(app) as s:
        pa = Permission(key="auditor_portal.access", name="a")
        pm = Permission(key="auditor_portal.admin", name="m")
        pv = Permission(key="admin.view", name="v")
        s.add_all([pa, pm, pv])
        s.flush()
        r_aud = Role(key="auditor", name="Auditor")
        r_aud.permissions.append(pa)
        r_adm = Role(key="admin", name="Admin")
        r_adm.permissions.extend([pv, pm])
        u_aud = User(email="al_aud@test.com", password_hash=generate_password_hash("a"), is_active=True)
        u_aud.roles.append(r_aud)
        u_adm = User(email="al_adm@test.com", password_hash=generate_password_hash("b"), is_active=True)
        u_adm.roles.append(r_adm)
        s.add_all([r_aud, r_adm, u_aud, u_adm])

    c = app.test_client()
    yield c, app
    auditor_fs.reset_auditor_root_cache_for_tests()


def test_access_events_recorded(log_client):
    from app.eqms.db import session_scope
    from app.eqms.modules.auditor_portal.models import AuditorAccessEvent

    client, app = log_client
    client.post("/auth/login", data={"email": "al_aud@test.com", "password": "a"})
    client.get("/auditor/")
    client.get("/auditor/browse/A")
    client.get("/auditor/file/A/f.txt")

    with session_scope(app) as s:
        rows = s.query(AuditorAccessEvent).order_by(AuditorAccessEvent.id.asc()).all()
        actions = [r.action for r in rows]
        assert "view_dashboard" in actions
        assert "view_folder" in actions
        assert "view_file" in actions


def test_admin_log_filter_and_export(log_client):
    client, app = log_client
    client.post("/auth/login", data={"email": "al_aud@test.com", "password": "a"})
    client.get("/auditor/")

    client.post("/auth/logout")
    client.post("/auth/login", data={"email": "al_adm@test.com", "password": "b"})
    r = client.get("/admin/auditor-access-log?action=view_dashboard")
    assert r.status_code == 200
    assert b"view_dashboard" in r.data

    ex = client.get("/admin/auditor-access-log/export?action=view_dashboard")
    assert ex.status_code == 200
    assert ex.headers.get("Content-Type", "").startswith("text/csv")
    buf = io.StringIO(ex.get_data(as_text=True))
    header = next(csv.reader(buf))
    assert "rel_path" in header
