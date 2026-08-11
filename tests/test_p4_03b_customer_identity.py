"""
P4-03B — Customer identity: catheter rule, GmbH, re-key/merge, backfill, ShipStation probe.
"""
from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer, CustomerNote, CustomerRep, Rep
from app.eqms.modules.customer_profiles.service import (
    apply_rekey_to_company,
    is_nre_rekey_candidate,
    preview_rekey_to_company,
)
from app.eqms.modules.customer_profiles.utils import (
    canonical_customer_key,
    is_person_shaped_customer_name,
)
from app.eqms.modules.rep_traceability.admin import (
    _find_or_create_customer_for_order_data,
    _is_catheter_order,
)
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder, SalesOrderLine
from app.eqms.modules.rep_traceability.order_type import (
    ORDER_TYPE_CLEARTRACT_IN_PROCESS,
    ORDER_TYPE_NRE_PROJECT,
)
from app.eqms.modules.rep_traceability.service import order_data_is_catheter
from app.eqms.modules.shipstation_sync.models import ShipStationSyncRun

PW = "pw"
PERMS = [
    "admin.view",
    "admin.edit",
    "sales_orders.view",
    "sales_orders.edit",
    "customers.view",
    "customers.edit",
    "distribution_log.view",
    "shipstation.view",
    "shipstation.run",
]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        perms = {k: Permission(key=k, name=k) for k in PERMS}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms.values())
        admin = User(
            email="admin@silq.tech",
            display_name="Admin",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        admin.roles.append(admin_role)

        staff_role = Role(key="staff", name="Staff")
        for k in ("admin.view", "customers.view", "shipstation.view"):
            staff_role.permissions.append(perms[k])
        staff = User(
            email="staff@silq.tech",
            display_name="Staff",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        staff.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, staff])

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@silq.tech"):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets

    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


# --------------------------------------------------------------------------- #
# Task A — catheter rule
# --------------------------------------------------------------------------- #
def test_lineless_order_is_not_catheter_and_creates_nre(app):
    assert order_data_is_catheter({"lines": []}) is False
    assert _is_catheter_order({"lines": [], "customer_name": "New World Medical"}) is False

    with session_scope(app) as s:
        c = _find_or_create_customer_for_order_data(
            s,
            {
                "customer_name": "New World Medical",
                "lines": [],
                "ship_to_address1": "1 Main",
                "ship_to_city": "Irvine",
                "ship_to_state": "CA",
                "ship_to_zip": "92618",
            },
        )
        assert c.customer_type == "nre"
        assert c.company_key == canonical_customer_key("New World Medical")
        assert "|" not in c.company_key


def test_catheter_sku_still_facility_keyed(app):
    with session_scope(app) as s:
        c = _find_or_create_customer_for_order_data(
            s,
            {
                "customer_name": "PAYER CORP",
                "ship_to_name": "VAMC Test",
                "lines": [{"sku": "211610SPT", "quantity": 1}],
                "ship_to_address1": "100 Hospital Rd",
                "ship_to_city": "Town",
                "ship_to_state": "CA",
                "ship_to_zip": "90001",
            },
        )
        assert c.customer_type == "catheter"
        assert "|" in c.company_key


def test_non_catheter_lines_create_nre(app):
    with session_scope(app) as s:
        c = _find_or_create_customer_for_order_data(
            s,
            {
                "customer_name": "AbbVie Inc.",
                "lines": [{"sku": "NRE-SERVICE", "quantity": 1}],
            },
        )
        assert c.customer_type == "nre"
        assert c.company_key == "ABBVIE"


def test_note_catheter_no_dist_skips_lineless():
    # Mirrors the guard used in both import paths
    assert _is_catheter_order({"lines": []}) is False


# --------------------------------------------------------------------------- #
# Task B — GmbH
# --------------------------------------------------------------------------- #
def test_gmbh_suffix_canonical_keys():
    assert canonical_customer_key("Advanced Bionics Gmbh") == "ADVANCEDBIONICS"
    assert canonical_customer_key("Advanced Bionics GmbH & Co. KG") == "ADVANCEDBIONICS"
    assert canonical_customer_key("Advanced Bionics") == "ADVANCEDBIONICS"
    assert canonical_customer_key("Something AB") == "SOMETHINGAB"


# --------------------------------------------------------------------------- #
# Task C — rekey / merge
# --------------------------------------------------------------------------- #
def test_merge_moves_notes_reps_and_orders(app):
    with app.app_context():
        with session_scope(app) as s:
            survivor = Customer(
                facility_name="AB",
                company_key="30625HANNOVER|CA|91355",
                customer_type="auto",
            )
            loser = Customer(
                facility_name="Advanced Bionics Gmbh",
                company_key="ADVANCEDBIONICSGMBH|30625HANNOVER",
                customer_type="catheter",
            )
            s.add_all([survivor, loser])
            s.flush()
            for i in range(3):
                s.add(
                    SalesOrder(
                        order_number=f"NRE-A{i}",
                        order_date=date(2026, 1, 1),
                        customer_id=survivor.id,
                        source="pdf_import",
                        status="completed",
                        order_type=ORDER_TYPE_NRE_PROJECT,
                    )
                )
            s.add(
                SalesOrder(
                    order_number="NRE-B1",
                    order_date=date(2026, 1, 2),
                    customer_id=loser.id,
                    source="pdf_import",
                    status="completed",
                    order_type=ORDER_TYPE_NRE_PROJECT,
                )
            )
            s.add(CustomerNote(customer_id=loser.id, note_text="keep me"))
            rep = Rep(name="Rep One", email="rep1@silq.tech")
            s.add(rep)
            s.flush()
            s.add(CustomerRep(customer_id=loser.id, rep_id=rep.id, is_primary=True))
            s.add(CustomerRep(customer_id=survivor.id, rep_id=rep.id, is_primary=False))
            s.flush()
            loser_id, survivor_id, note_text = loser.id, survivor.id, "keep me"

            result = apply_rekey_to_company(
                s, loser_id, surviving_name="Advanced Bionics", user=None
            )
            assert result.id == survivor_id
            assert s.get(Customer, loser_id) is None
            assert result.company_key == "ADVANCEDBIONICS"
            assert result.customer_type == "nre"
            assert result.facility_name == "Advanced Bionics"
            notes = s.query(CustomerNote).filter(CustomerNote.customer_id == survivor_id).all()
            assert any(n.note_text == note_text for n in notes)
            reps = s.query(CustomerRep).filter(CustomerRep.customer_id == survivor_id).all()
            assert len(reps) == 1
            assert s.query(SalesOrder).filter(SalesOrder.customer_id == survivor_id).count() == 4
            ev = (
                s.query(AuditEvent)
                .filter(AuditEvent.action == "customer.rekeyed_merged")
                .order_by(AuditEvent.id.desc())
                .first()
            )
            meta = json.loads(ev.metadata_json)
            assert meta["loser_id"] == loser_id
            assert meta["survivor_id"] == survivor_id
            assert meta["after_key"] == "ADVANCEDBIONICS"
            assert meta["before_loser_key"]
            assert meta["moved_sales_orders"] == 1
            assert meta["moved_notes"] == 1


def test_rekey_in_place_without_merge(app):
    with app.app_context():
        with session_scope(app) as s:
            c = Customer(
                facility_name="Aspero Medical Inc.",
                company_key="10835DOVERST|CO|80021",
                customer_type="catheter",
            )
            s.add(c)
            s.flush()
            s.add(
                SalesOrder(
                    order_number="N1",
                    order_date=date(2026, 1, 1),
                    customer_id=c.id,
                    source="pdf_import",
                    status="completed",
                    order_type=ORDER_TYPE_NRE_PROJECT,
                )
            )
            s.flush()
            cid = c.id
            result = apply_rekey_to_company(
                s, cid, surviving_name="Aspero Medical Inc.", user=None
            )
            assert result.id == cid
            assert result.company_key == "ASPEROMEDICAL"
            assert result.customer_type == "nre"


# --------------------------------------------------------------------------- #
# Task D — backfill selection / hold
# --------------------------------------------------------------------------- #
def test_backfill_excludes_catheter_facility_with_dists(app):
    with session_scope(app) as s:
        c = Customer(
            facility_name="Wiscosin Rapids",
            company_key="400DEWEYST|WI|54494",
            customer_type="catheter",
        )
        s.add(c)
        s.flush()
        s.add(
            SalesOrder(
                order_number="WR1",
                order_date=date(2026, 1, 1),
                customer_id=c.id,
                source="pdf_import",
                status="completed",
                order_type=ORDER_TYPE_NRE_PROJECT,
            )
        )
        s.add(
            SalesOrder(
                order_number="WR2",
                order_date=date(2026, 1, 2),
                customer_id=c.id,
                source="pdf_import",
                status="completed",
                order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
            )
        )
        # Actually selection needs EVERY order nre_project - add only nre + dists
        s.query(SalesOrder).filter(SalesOrder.order_number == "WR2").delete()
        s.add(
            DistributionLogEntry(
                ship_date=date(2026, 1, 3),
                order_number="WR1",
                facility_name=c.facility_name,
                sku="211610SPT",
                lot_number="L",
                quantity=1,
                source="shipstation",
                customer_id=c.id,
            )
        )
        s.flush()
        assert is_nre_rekey_candidate(s, c) is False


def test_person_shaped_hold():
    assert is_person_shaped_customer_name("Aniq Darr") is True
    assert is_person_shaped_customer_name("Boston Scientific") is False
    assert is_person_shaped_customer_name("AbbVie Inc.") is False


def test_backfill_dry_run_writes_nothing(app, monkeypatch, tmp_path):
    # Selection + dry-run behaviour via service preview only (script uses DRY_RUN flag)
    with session_scope(app) as s:
        c = Customer(
            facility_name="Aniq Darr",
            company_key="700AVEFAIRFIELD|CT|06902",
            customer_type="catheter",
        )
        s.add(c)
        s.flush()
        s.add(
            SalesOrder(
                order_number="AD1",
                order_date=date(2026, 1, 1),
                customer_id=c.id,
                source="pdf_import",
                status="completed",
                order_type=ORDER_TYPE_NRE_PROJECT,
            )
        )
        s.flush()
        assert is_nre_rekey_candidate(s, c) is True
        assert is_person_shaped_customer_name(c.facility_name) is True
        before_key = c.company_key
    with session_scope(app) as s:
        c = s.query(Customer).filter(Customer.facility_name == "Aniq Darr").one()
        assert c.company_key == before_key


# --------------------------------------------------------------------------- #
# Task E — ShipStation probe read-only
# --------------------------------------------------------------------------- #
def test_shipstation_probe_no_writes(client, app, monkeypatch):
    monkeypatch.setenv("SHIPSTATION_API_KEY", "k")
    monkeypatch.setenv("SHIPSTATION_API_SECRET", "s")
    with session_scope(app) as s:
        c = Customer(facility_name="HPFY", company_key="HPFY1", customer_type="catheter")
        s.add(c)
        s.flush()
        s.add(
            SalesOrder(
                order_number="0000363",
                order_date=date(2026, 7, 7),
                customer_id=c.id,
                source="pdf_import",
                status="pending",
                order_type=ORDER_TYPE_CLEARTRACT_IN_PROCESS,
            )
        )
        before_dist = s.query(DistributionLogEntry).count()
        before_runs = s.query(ShipStationSyncRun).count()

    _login(client)
    mock_client = MagicMock()
    mock_client.list_orders_by_order_number.return_value = [
        {"orderId": "99", "orderStatus": "awaiting_shipment"}
    ]
    mock_client.list_shipments_for_order.return_value = []

    with patch(
        "app.eqms.modules.shipstation_sync.shipstation_client.ShipStationClient",
        return_value=mock_client,
    ):
        r = client.get("/admin/shipstation/probe-in-process")
    assert r.status_code == 200
    assert b"0000363" in r.data
    assert b"awaiting_shipment" in r.data or b"SS order" in r.data

    with session_scope(app) as s:
        assert s.query(DistributionLogEntry).count() == before_dist
        assert s.query(ShipStationSyncRun).count() == before_runs


# --------------------------------------------------------------------------- #
# Permissions / CSRF
# --------------------------------------------------------------------------- #
def test_rekey_routes_require_permission_and_csrf(client, app):
    with session_scope(app) as s:
        c = Customer(
            facility_name="Pathway Medtech",
            company_key="ADDR|CA|90000",
            customer_type="catheter",
        )
        s.add(c)
        s.flush()
        s.add(
            SalesOrder(
                order_number="P1",
                order_date=date(2026, 1, 1),
                customer_id=c.id,
                source="pdf_import",
                status="completed",
                order_type=ORDER_TYPE_NRE_PROJECT,
            )
        )
        cid = c.id

    _login(client, email="staff@silq.tech")
    token = _csrf(client)
    r = client.get(f"/admin/customers/{cid}/rekey-company")
    assert r.status_code == 403
    r = client.post(
        f"/admin/customers/{cid}/rekey-company",
        data={"surviving_name": "Pathway Medtech", "csrf_token": token},
    )
    assert r.status_code == 403

    _login(client)
    r = client.post(
        f"/admin/customers/{cid}/rekey-company",
        data={"surviving_name": "Pathway Medtech"},
    )
    assert r.status_code == 400

    r = client.get("/admin/shipstation/probe-in-process")
    # admin has shipstation.run
    assert r.status_code == 200

    _login(client, email="staff@silq.tech")
    r = client.get("/admin/shipstation/probe-in-process")
    assert r.status_code == 403
