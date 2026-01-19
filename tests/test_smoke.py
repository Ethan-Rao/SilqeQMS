import os

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    app = create_app()

    engine = app.extensions["sqlalchemy_engine"]
    Base.metadata.create_all(bind=engine)

    with session_scope(app) as s:
        p = Permission(key="admin.view", name="Admin: view shell")
        r = Role(key="admin", name="Administrator")
        r.permissions.append(p)
        u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        u.roles.append(r)
        s.add_all([p, r, u])

    return app.test_client()


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["ok"] is True


def test_login_and_admin_access(client):
    # Anonymous should be forbidden
    r = client.get("/admin/")
    assert r.status_code in (302, 403)

    # Login
    r = client.post("/auth/login", data={"email": "admin@example.com", "password": "pw"}, follow_redirects=False)
    assert r.status_code == 302

    # Now admin should be accessible
    r = client.get("/admin/")
    assert r.status_code == 200

