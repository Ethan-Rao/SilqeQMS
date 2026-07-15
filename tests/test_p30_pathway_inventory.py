"""
Prompt 30 — Pathway Available Inventory table on the Supplies page.

Covers:
- supplies_inventory admin_docs library route.
- /admin/supplies renders the inventory table (with "As of" date, item codes,
  thousands-separated quantities + UOM) when a snapshot is present.
- Section is silently hidden when no snapshot exists.
"""
import io

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFile
from app.eqms.storage import storage_from_config

PW = "pw"
PERMS = ["admin.view", "staff.view", "supplies.view"]
STORAGE_KEY = "supplies/inventory/pathway_inventory_latest.xlsx"


def _make_xlsx() -> bytes:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    # Header row (A..H); parser skips row 0
    ws.append(["", "Item Code", "Description", "Vendor", "", "", "UOM", "Qty"])
    ws.append(["", "21600100001", "16 Fr Foley Catheters", "Ningbo", "", "", "Each", 18500])
    ws.append(["", "C.SLQ001", "Suspension", "Silq", "", "", "Liters", 46])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "storage"))
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        perms = {k: Permission(key=k, name=k) for k in PERMS}
        role = Role(key="admin", name="Administrator")
        role.permissions.extend(perms.values())
        admin = User(email="admin@example.com", password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(role)
        s.add_all(list(perms.values()) + [role, admin])

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client):
    client.post("/auth/login", data={"email": "admin@example.com", "password": PW}, follow_redirects=True)


def _seed_snapshot(app):
    with session_scope(app) as s:
        storage = storage_from_config(app.config)
        storage.put_bytes(STORAGE_KEY, _make_xlsx(), content_type="application/octet-stream")
        s.add(AdminDocFile(
            library_key="supplies_inventory", folder_id=None,
            filename="Pathway Inventory.xlsx", storage_key=STORAGE_KEY,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size_bytes=100, description="Jul 15, 2026",
        ))


def test_supplies_inventory_library_route(client):
    _login(client)
    r = client.get("/admin/supplies-inventory")
    assert r.status_code == 200
    assert "Supplies Inventory Snapshots" in r.data.decode()


def test_inventory_hidden_without_snapshot(client):
    _login(client)
    body = client.get("/admin/supplies").data.decode()
    assert "Pathway Available Inventory" not in body


def test_inventory_table_rendered(client, app):
    _seed_snapshot(app)
    _login(client)
    body = client.get("/admin/supplies").data.decode()
    assert "Pathway Available Inventory" in body
    assert "As of Jul 15, 2026" in body
    assert "21600100001" in body
    assert "18,500" in body      # thousands separator
    assert "Each" in body
    assert "Suspension" in body
    assert "Liters" in body
