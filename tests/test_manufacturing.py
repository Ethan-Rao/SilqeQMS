"""Tests for Manufacturing module."""
import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User


def _seed_all_permissions(s):
    """Seed all permissions needed for manufacturing tests."""
    perm_keys = [
        ("admin.view", "Admin: view shell"),
        ("manufacturing.view", "Manufacturing: view"),
        ("manufacturing.create", "Manufacturing: create lots"),
        ("manufacturing.edit", "Manufacturing: edit lots"),
        ("manufacturing.upload", "Manufacturing: upload documents"),
        ("manufacturing.disposition", "Manufacturing: record QA disposition"),
        ("equipment.view", "Equipment: view"),  # Needed for lot detail dropdown
        ("suppliers.view", "Suppliers: view"),  # Needed for lot detail dropdown
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


def test_manufacturing_index_requires_auth(client):
    r = client.get("/admin/manufacturing/")
    assert r.status_code in (302, 403)


def test_manufacturing_index_ok(client):
    _login(client)
    r = client.get("/admin/manufacturing/")
    assert r.status_code == 200
    assert b"Manufacturing" in r.data
    assert b"Suspension" in r.data


def test_suspension_list_ok(client):
    _login(client)
    r = client.get("/admin/manufacturing/suspension")
    assert r.status_code == 200
    assert b"Suspension Lots" in r.data


def test_lot_create(client):
    _login(client)
    r = client.post(
        "/admin/manufacturing/suspension/new",
        data={
            "lot_number": "C.SLQ001-2026-TEST",
            "work_order": "WO-TEST",
            "operator": "Test Operator",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"C.SLQ001-2026-TEST" in r.data or b"created" in r.data.lower()


def test_lot_detail_ok(client):
    _login(client)
    # First create a lot
    client.post(
        "/admin/manufacturing/suspension/new",
        data={"lot_number": "C.SLQ001-2026-DET"},
        follow_redirects=True,
    )
    # Then view it
    r = client.get("/admin/manufacturing/suspension/1")
    assert r.status_code == 200
    assert b"Lot Details" in r.data


def test_cleartract_placeholder_ok(client):
    _login(client)
    r = client.get("/admin/manufacturing/cleartract-foley-catheters")
    assert r.status_code == 200
    assert b"Coming Soon" in r.data or b"coming soon" in r.data.lower()


def test_lot_status_change(client):
    _login(client)
    # Create a lot
    client.post(
        "/admin/manufacturing/suspension/new",
        data={"lot_number": "C.SLQ001-2026-STATUS"},
        follow_redirects=True,
    )
    # Change status from Draft to In-Process
    r = client.post(
        "/admin/manufacturing/suspension/1/status",
        data={"new_status": "In-Process", "reason": "Starting production"},
        follow_redirects=True,
    )
    assert r.status_code == 200
