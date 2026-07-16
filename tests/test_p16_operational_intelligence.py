"""
Prompt 16 (Phase 8) — Operational Intelligence.

Covers: equipment cal/PM schedule section groupings + badges, supplier re-eval
schedule, quality objectives (admin POST / staff read-only), and the What's Due
report CSV section column.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, SystemSetting, User
from app.eqms.modules.equipment.models import Equipment
from app.eqms.modules.suppliers.models import Supplier
from app.eqms.modules.training.models import TrainingAssignment


PW = "pw"
ADMIN_PERMS = ["admin.view", "admin.edit", "equipment.view", "suppliers.view",
               "training.view", "training.manage"]
STAFF_PERMS = ["admin.view", "equipment.view", "suppliers.view", "training.view"]


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
            Equipment(equip_code="ST-OVERDUE", status="Active", description="Overdue scale",
                      cal_due_date=today - dt.timedelta(days=10), cal_interval_text="Annual"),
            Equipment(equip_code="ST-THISMONTH", status="Active", description="Due now",
                      pm_due_date=today, pm_interval_text="Annual"),
            Equipment(equip_code="ST-BEYOND", status="Active", description="Far future",
                      cal_due_date=today + dt.timedelta(days=200), cal_interval_text="Annual"),
            Equipment(equip_code="ST-RETIRED", status="Retired", description="Gone",
                      cal_due_date=today - dt.timedelta(days=1)),
        ])
        s.add(Supplier(name="Overdue Vendor", status="Approved",
                       next_reevaluation_date=today - dt.timedelta(days=5)))
        s.add(TrainingAssignment(item_type="free_text", item_title="QM.SLQ052 Rev A",
                                 assigned_to_user_id=staff.id,
                                 due_date=today - dt.timedelta(days=3), acknowledged_at=None))

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
# Task A — equipment schedule
# --------------------------------------------------------------------------- #
def test_equipment_schedule_groupings(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/equipment/schedule")
    assert r.status_code == 200
    body = r.data.decode()
    assert "ST-OVERDUE" in body
    assert "ST-THISMONTH" in body
    assert "ST-BEYOND" in body
    assert "ST-RETIRED" not in body  # retired excluded
    assert "badge--danger" in body


def test_equipment_schedule_print(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/equipment/schedule?print=1")
    assert r.status_code == 200
    assert "Equipment Cal/PM Schedule" in r.data.decode()


# --------------------------------------------------------------------------- #
# Task B — supplier schedule
# --------------------------------------------------------------------------- #
def test_supplier_schedule_view(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/suppliers?view=schedule")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Re-evaluation Schedule" in body
    assert "Overdue Vendor" in body


# --------------------------------------------------------------------------- #
# Task C — quality objectives
# --------------------------------------------------------------------------- #
def test_quality_objectives_admin_can_post(client, app):
    _login(client, "admin@example.com")
    r = client.get("/admin/quality-objectives")
    assert r.status_code == 200
    assert "Quality Planning" in r.data.decode()

    r = client.post("/admin/quality-objectives",
                    data={"incoming_lot_acceptance": "95%", "csrf_token": _csrf(client)},
                    follow_redirects=True)
    assert r.status_code == 200
    with session_scope(app) as s:
        row = s.get(SystemSetting, "quality_objectives")
        assert row is not None and "95%" in row.value


def test_quality_objectives_labels_visible_when_empty(client):
    """Prompt 19 Task D: titles/targets + guidance render even with no saved values."""
    _login(client, "admin@example.com")
    body = client.get("/admin/quality-objectives").data.decode()
    # Objective titles and targets render from QM.SLQ037 even with empty settings.
    assert "Incoming Material Quality" in body
    assert "Lot acceptance rate" in body
    # Employee Training objective removed in Prompt 22; its target is gone.
    assert "training activities per year" not in body
    # Guidance note and placeholder (not a bare blank field).
    assert "Values default to the last recorded Q2 2026 figures until updated." in body
    assert "Not yet entered" in body


def test_quality_objectives_staff_readonly(client):
    _login(client, "staff@example.com")
    r = client.get("/admin/quality-objectives")
    assert r.status_code == 200
    # Staff cannot POST (admin.edit gated on the admin blueprint).
    r = client.post("/admin/quality-objectives",
                    data={"incoming_lot_acceptance": "50%", "csrf_token": _csrf(client)})
    assert r.status_code == 403


# --------------------------------------------------------------------------- #
# Task D — What's Due report CSV
# --------------------------------------------------------------------------- #
def test_report_csv_sections(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/reports/due-this-period.csv?months=3")
    assert r.status_code == 200
    assert r.mimetype == "text/csv"
    body = r.data.decode()
    lines = body.splitlines()
    assert lines[0] == "section,item,due_date,status,notes"
    sections = {ln.split(",")[0] for ln in lines[1:] if ln}
    assert "Equipment CAL" in sections
    assert "Supplier Re-eval" in sections
    assert "Training" in sections


def test_report_csv_forbidden_for_staff(client):
    _login(client, "staff@example.com")
    r = client.get("/admin/reports/due-this-period.csv")
    assert r.status_code == 403
