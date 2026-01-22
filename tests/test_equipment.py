"""Tests for Equipment module."""
import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User


def _seed_all_permissions(s):
    """Seed all permissions needed for equipment tests."""
    perm_keys = [
        ("admin.view", "Admin: view shell"),
        ("equipment.view", "Equipment: view"),
        ("equipment.create", "Equipment: create"),
        ("equipment.edit", "Equipment: edit"),
        ("equipment.upload", "Equipment: upload"),
    ]
    perms = []
    for key, name in perm_keys:
        p = Permission(key=key, name=name)
        s.add(p)
        perms.append(p)
    return perms


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
        perms = _seed_all_permissions(s)
        r = Role(key="admin", name="Administrator")
        for p in perms:
            r.permissions.append(p)
        u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        u.roles.append(r)
        s.add_all([r, u])

    return app.test_client()


def _login(client):
    client.post("/auth/login", data={"email": "admin@example.com", "password": "pw"}, follow_redirects=True)


def test_equipment_list_requires_auth(client):
    r = client.get("/admin/equipment")
    assert r.status_code in (302, 403)


def test_equipment_list_ok(client):
    _login(client)
    r = client.get("/admin/equipment")
    assert r.status_code == 200
    assert b"Equipment" in r.data


def test_equipment_create(client):
    _login(client)
    r = client.post(
        "/admin/equipment/new",
        data={
            "equip_code": "TEST-001",
            "status": "Active",
            "description": "Test Equipment",
            "mfg": "Test Manufacturer",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"TEST-001" in r.data or b"created" in r.data.lower()


def test_equipment_pagination_vars_present(client):
    _login(client)
    r = client.get("/admin/equipment")
    assert r.status_code == 200
    # Check that pagination info is rendered
    assert b"Showing" in r.data
