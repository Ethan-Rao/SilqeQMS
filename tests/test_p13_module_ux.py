"""
Prompt 13 (Task D) — module UI/usability rendered-HTML assertions.

Covers: equipment due-date summary bar (D1), equipment detail category grouping
(D2), supplier expiry/re-eval flags + Attention-needed filter (D3), purchasing
list vendor surfacing (D4), and global search over equipment + suppliers (D5).
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.equipment.models import Equipment, ManagedDocument
from app.eqms.modules.purchasing.models import PurchaseOrder
from app.eqms.modules.suppliers.models import Supplier


PERMS = [
    "admin.view",
    "equipment.view", "equipment.upload",
    "suppliers.view",
    "purchasing.view",
]


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
    app.config["_schema_health_ok"] = True

    today = dt.date.today()
    with session_scope(app) as s:
        perms = {k: Permission(key=k, name=k) for k in PERMS}
        role = Role(key="admin", name="Administrator")
        role.permissions.extend(perms.values())
        u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        u.roles.append(role)
        s.add_all(list(perms.values()) + [role, u])
        s.flush()
        uid = u.id

        # Equipment: one Active + calibration overdue, one Active healthy.
        overdue = Equipment(
            equip_code="ST-001", status="Active", description="Overdue scale",
            mfg="Acme", cal_interval_text="Annual", cal_due_date=today - dt.timedelta(days=10),
        )
        healthy = Equipment(
            equip_code="ST-002", status="Active", description="Healthy meter",
            mfg="Beta", cal_interval_text="Annual", cal_due_date=today + dt.timedelta(days=300),
        )
        s.add_all([overdue, healthy])
        s.flush()

        # Two calibration docs (newest first check) + a manual doc.
        s.add_all([
            ManagedDocument(
                entity_type="equipment", entity_id=overdue.id, equipment_id=overdue.id,
                storage_key="k1", original_filename="cal_2024.pdf", sha256="a", size_bytes=1,
                category="calibration", uploaded_by_user_id=uid,
                uploaded_at=dt.datetime(2024, 1, 1),
            ),
            ManagedDocument(
                entity_type="equipment", entity_id=overdue.id, equipment_id=overdue.id,
                storage_key="k2", original_filename="cal_2025.pdf", sha256="b", size_bytes=1,
                category="calibration", uploaded_by_user_id=uid,
                uploaded_at=dt.datetime(2025, 1, 1),
            ),
            ManagedDocument(
                entity_type="equipment", entity_id=overdue.id, equipment_id=overdue.id,
                storage_key="k3", original_filename="manual.pdf", sha256="c", size_bytes=1,
                category="manual", uploaded_by_user_id=uid,
                uploaded_at=dt.datetime(2023, 1, 1),
            ),
        ])

        # Suppliers: one with expired cert + past re-eval, one healthy.
        flagged = Supplier(
            name="Flagged Vendor", status="Approved", category="Component Supplier",
            product_service_provided="Reagents",
            certification_expiration=today - dt.timedelta(days=5),
            next_reevaluation_date=today - dt.timedelta(days=5),
        )
        ok_sup = Supplier(
            name="Healthy Vendor", status="Approved", category="Service Provider",
            product_service_provided="Calibration",
            certification_expiration=today + dt.timedelta(days=400),
            next_reevaluation_date=today + dt.timedelta(days=400),
        )
        s.add_all([flagged, ok_sup])
        s.flush()

        # PO with no linked supplier but freetext vendor recorded in notes.
        s.add(PurchaseOrder(
            po_number="0000001", order_date=today, status="pending",
            notes="Supplier from PO Log: Shopify New York City",
            created_by_user_id=uid,
        ))

    return app.test_client()


def _login(client):
    client.post("/auth/login", data={"email": "admin@example.com", "password": "pw"}, follow_redirects=True)


# ---------- D1 ----------
def test_equipment_summary_bar(client):
    _login(client)
    r = client.get("/admin/equipment")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Overdue (CAL)" in body
    assert "Due soon (CAL or PM)" in body
    # Quick-filter link present.
    assert "cal_overdue=1" in body


def test_equipment_cal_overdue_filter(client):
    _login(client)
    r = client.get("/admin/equipment?cal_overdue=1")
    assert r.status_code == 200
    body = r.data.decode()
    assert "ST-001" in body
    assert "ST-002" not in body


# ---------- D2 ----------
def test_equipment_detail_category_grouping(client):
    _login(client)
    with client.application.app_context():
        pass
    # ST-001 is id 1.
    r = client.get("/admin/equipment/1")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Calibration" in body
    assert "Manual" in body
    # Newest calibration cert appears before the older one in the grouped list.
    assert body.index("cal_2025.pdf") < body.index("cal_2024.pdf")


# ---------- D3 ----------
def test_supplier_flags_rendered(client):
    _login(client)
    r = client.get("/admin/suppliers")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Cert Expired" in body
    assert "Re-eval Due" in body


def test_supplier_attention_filter(client):
    _login(client)
    r = client.get("/admin/suppliers?attention=1")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Flagged Vendor" in body
    assert "Healthy Vendor" not in body


# ---------- D4 ----------
def test_purchasing_unlinked_vendor_surfaced(client):
    _login(client)
    r = client.get("/admin/purchasing")
    assert r.status_code == 200
    body = r.data.decode()
    # Vendor text from the PO Log still surfaces for unlinked POs; the
    # "(unlinked)" tag was removed in the Prompt 27 redesign.
    assert "Shopify New York City" in body


# ---------- D5 ----------
def test_global_search_includes_equipment_and_suppliers(client):
    _login(client)
    r = client.get("/admin/search?q=ST-001")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Equipment" in body
    assert "ST-001" in body

    r2 = client.get("/admin/search?q=Flagged")
    body2 = r2.data.decode()
    assert "Suppliers" in body2
    assert "Flagged Vendor" in body2
