"""
Prompt 28 — Lot log integration, ClearTract lots, equipment download, CAPA section dates.

Covers:
- New model columns on ManufacturingLot (quantity/expiration_date/part_revision)
  and CAPARecord (initiated_by, section_1..6_date, closed_by, on_time_status).
- Manufacturing index redesign: Suspension production-lot table (+ DHR/RI toggles)
  and ClearTract lots grouped by SKU.
- equipment_files admin_docs library route + Equipment list download button.
- CAPA list section-progress dots, detail section-dates panel, and edit form fields.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFile
from app.eqms.modules.capas.models import CAPARecord
from app.eqms.modules.manufacturing.models import ManufacturingLot

PW = "pw"
ADMIN_PERMS = ["admin.view", "admin.edit", "manufacturing.view", "equipment.view"]
STAFF_PERMS = ["admin.view", "staff.view", "manufacturing.view", "equipment.view"]


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

        # Production lots
        s.add_all([
            ManufacturingLot(lot_number="2209-01-1", product_code="Suspension", status="Released",
                             work_order="2209-01", manufacture_date=dt.date(2022, 9, 28),
                             quantity="101.9 kg", operator="CT", part_revision="B"),
            ManufacturingLot(lot_number="SLQ-05012025", product_code="SLQ-211610SPT", status="Released",
                             manufacture_date=dt.date(2025, 5, 31),
                             expiration_date=dt.date(2028, 5, 31), quantity="1298 units"),
        ])

        # CAPA with a partial section-progress set
        s.add(CAPARecord(
            capa_number="CAPA001-2025", title="Inspection", status="Open",
            initiated_by="ER", on_time_status="On time",
            section_1_date=dt.date(2025, 1, 10), section_2_date=dt.date(2025, 2, 10),
        ))

        # Equipment master list file (equipment_files library, root)
        s.add(AdminDocFile(
            library_key="equipment_files", folder_id=None,
            filename="Silq Equipment Master List.xlsx",
            storage_key="equipment_files/master.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            size_bytes=1234,
        ))

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
# Section A — model columns round-trip
# --------------------------------------------------------------------------- #
def test_lot_columns_roundtrip(app):
    with session_scope(app) as s:
        lot = s.query(ManufacturingLot).filter_by(lot_number="2209-01-1").one()
        assert lot.quantity == "101.9 kg"
        assert lot.part_revision == "B"
        ct = s.query(ManufacturingLot).filter_by(lot_number="SLQ-05012025").one()
        assert ct.expiration_date == dt.date(2028, 5, 31)


def test_capa_section_columns_roundtrip(app):
    with session_scope(app) as s:
        capa = s.query(CAPARecord).filter_by(capa_number="CAPA001-2025").one()
        assert capa.initiated_by == "ER"
        assert capa.section_1_date == dt.date(2025, 1, 10)
        assert capa.section_3_date is None
        assert capa.on_time_status == "On time"


# --------------------------------------------------------------------------- #
# Section B/C — Manufacturing index
# --------------------------------------------------------------------------- #
def test_manufacturing_index_suspension_lot_table(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/manufacturing/")
    assert r.status_code == 200
    body = r.data.decode()
    assert "2209-01-1" in body
    assert "101.9 kg" in body
    assert 'data-target="dhr-' in body   # DHR toggle
    assert 'data-target="ri-' in body    # RI toggle


def test_manufacturing_index_cleartract_by_sku(client):
    _login(client, "admin@example.com")
    body = client.get("/admin/manufacturing/").data.decode()
    assert "16 Fr (211610SPT)" in body   # SKU display name
    assert "SLQ-05012025" in body
    assert "1298 units" in body


# --------------------------------------------------------------------------- #
# Section D — equipment_files library + download button
# --------------------------------------------------------------------------- #
def test_equipment_files_library_route(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/equipment-files")
    assert r.status_code == 200
    assert "Equipment Documents" in r.data.decode()


def test_equipment_list_download_button(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/equipment")
    assert r.status_code == 200
    assert "Download Equipment Master List" in r.data.decode()


# --------------------------------------------------------------------------- #
# Section E — CAPA UI
# --------------------------------------------------------------------------- #
def test_capa_list_section_progress(client):
    _login(client, "admin@example.com")
    body = client.get("/admin/capas").data.decode()
    assert "Section 1:" in body   # dot tooltip
    assert "Sections" in body     # column header


def test_capa_detail_section_panel(client, app):
    with session_scope(app) as s:
        capa_id = s.query(CAPARecord).filter_by(capa_number="CAPA001-2025").one().id
    _login(client, "admin@example.com")
    body = client.get(f"/admin/capas/{capa_id}").data.decode()
    assert "Section Completion Dates" in body
    assert "Immediate Containment" in body
    assert "On-time status" in body


def test_capa_edit_form_and_save_section_dates(client, app):
    with session_scope(app) as s:
        capa_id = s.query(CAPARecord).filter_by(capa_number="CAPA001-2025").one().id
    _login(client, "admin@example.com")

    form = client.get(f"/admin/capas/{capa_id}/edit").data.decode()
    assert 'name="section_3_date"' in form
    assert 'name="initiated_by"' in form
    assert 'name="on_time_status"' in form

    r = client.post(f"/admin/capas/{capa_id}/edit", data={
        "title": "Inspection", "status": "Open",
        "initiated_by": "BW", "on_time_status": "Late",
        "section_3_date": "2025-03-15",
        "csrf_token": _csrf(client),
    }, follow_redirects=False)
    assert r.status_code == 302
    with session_scope(app) as s:
        capa = s.get(CAPARecord, capa_id)
        assert capa.section_3_date == dt.date(2025, 3, 15)
        assert capa.initiated_by == "BW"
        assert capa.on_time_status == "Late"
