"""
Prompt 14 (Phase 6) — dashboard stats + admin_docs in-library search.

Covers: _dashboard_stats() shape/values and the rendered System Status strip
(Task C), and the admin_docs in-library search + folder counts (Task D).
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.admin import _dashboard_stats
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.equipment.models import Equipment
from app.eqms.modules.purchasing.models import PurchaseOrder
from app.eqms.modules.suppliers.models import Supplier


PERMS = ["admin.view", "admin.edit", "equipment.view", "suppliers.view", "purchasing.view", "docs.view"]

EXPECTED_KEYS = {
    "equipment_overdue_cal", "equipment_overdue_pm", "equipment_due_soon",
    "suppliers_attention", "training_open", "training_overdue",
    "docs_released_30d", "pos_pending", "capas_open",
}


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

    today = dt.date.today()
    with session_scope(application) as s:
        perms = {k: Permission(key=k, name=k) for k in PERMS}
        role = Role(key="admin", name="Administrator")
        role.permissions.extend(perms.values())
        u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        u.roles.append(role)
        s.add_all(list(perms.values()) + [role, u])
        s.flush()
        uid = u.id

        s.add(Equipment(equip_code="ST-001", status="Active",
                        cal_due_date=today - dt.timedelta(days=5)))
        s.add(Supplier(name="Flagged Vendor", status="Approved",
                       certification_expiration=today - dt.timedelta(days=1)))
        s.add(PurchaseOrder(po_number="0000001", order_date=today, status="pending",
                            created_by_user_id=uid))

        # admin_docs: a folder tree with files for the in-library search.
        lib = "qms_documents"
        parent = AdminDocFolder(library_key=lib, name="SOPs", created_by_user_id=uid)
        s.add(parent)
        s.flush()
        child = AdminDocFolder(library_key=lib, name="Quality", parent_id=parent.id, created_by_user_id=uid)
        s.add(child)
        s.flush()
        s.add_all([
            AdminDocFile(library_key=lib, folder_id=child.id, filename="QM.SLQ016 CAPA SOP.pdf",
                         storage_key="k1", content_type="application/pdf", size_bytes=1, uploaded_by_user_id=uid),
            AdminDocFile(library_key=lib, folder_id=parent.id, filename="index.txt",
                         storage_key="k2", content_type="text/plain", size_bytes=1, uploaded_by_user_id=uid),
        ])

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client):
    client.post("/auth/login", data={"email": "admin@example.com", "password": "pw"}, follow_redirects=True)


# ---------- Task C ----------
def test_dashboard_stats_shape(app):
    with app.app_context():
        stats = _dashboard_stats()
    assert set(stats.keys()) == EXPECTED_KEYS
    for k, v in stats.items():
        assert isinstance(v, int) and v >= 0, f"{k}={v!r}"
    # Seeded overdue-cal equipment, attention supplier, pending PO -> at least 1 each.
    assert stats["equipment_overdue_cal"] >= 1
    assert stats["suppliers_attention"] >= 1
    assert stats["pos_pending"] >= 1


def test_dashboard_renders_system_status_strip(client):
    _login(client)
    r = client.get("/admin/")
    assert r.status_code == 200
    body = r.data.decode()
    assert "System Status" in body
    assert "Overdue calibrations" in body
    assert "POs pending" in body


# ---------- Task D ----------
def test_library_search_returns_matching_file(client):
    _login(client)
    r = client.get("/admin/qms-documents?q=CAPA")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Search results" in body
    assert "QM.SLQ016 CAPA SOP.pdf" in body
    # Path context is shown for the matched file.
    assert "SOPs / Quality" in body
    # index.txt does not match "CAPA".
    assert "index.txt" not in body


def test_library_tree_view_when_q_empty(client):
    _login(client)
    r = client.get("/admin/qms-documents")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Folders" in body
    assert "Documents" in body
    assert "Search results" not in body
    # Folder card shows direct file/subfolder counts.
    assert "1 file, 1 subfolder" in body


def test_library_search_no_match(client):
    _login(client)
    r = client.get("/admin/qms-documents?q=zzzznotfound")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Search results" in body
    assert "match" in body.lower()
