"""
Prompt 31 — NRE Projects: customer_type classification, tracker CRUD, admin_docs.

Covers:
- customer_type overrides in the NRE index classification (auto/catheter/nre).
- NREProjectEntry upsert / patch / delete JSON routes.
- nre_projects admin_docs library route + folder scaffolding via refresh-folders.
- Detail page renders the Project Tracker + classification dropdown.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFolder
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.models import NREProjectEntry
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder

PW = "pw"
PERMS = ["admin.view", "admin.edit", "sales_orders.view", "sales_orders.edit"]


def _customer(s, name, key, ctype="auto"):
    c = Customer(company_key=key, facility_name=name, customer_type=ctype)
    s.add(c)
    s.flush()
    return c


def _order(s, customer_id, num, ext):
    o = SalesOrder(order_number=num, order_date=dt.date(2026, 1, 1), customer_id=customer_id,
                   source="pdf_import", external_key=ext, status="pending")
    s.add(o)
    s.flush()
    return o


def _dist(s, order):
    d = DistributionLogEntry(
        ship_date=dt.date(2026, 1, 2), order_number=order.order_number,
        facility_name="F", sku="211610SPT", lot_number="L1", quantity=1,
        source="shipstation", sales_order_id=order.id,
    )
    s.add(d)
    s.flush()
    return d


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
        perms = {k: Permission(key=k, name=k) for k in PERMS}
        role = Role(key="admin", name="Administrator")
        role.permissions.extend(perms.values())
        admin = User(email="admin@example.com", password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(role)
        s.add_all(list(perms.values()) + [role, admin])
        s.flush()

        auto = _customer(s, "AbbVie Inc.", "abbvie", "auto")       # NRE (order, no dist)
        _order(s, auto.id, "0000300", "pdf:0000300")
        cath = _customer(s, "A Caring Hand", "acaring", "catheter")  # excluded
        _order(s, cath.id, "0000179", "pdf:0000179")
        forced = _customer(s, "Forced NRE Co", "forced", "nre")      # forced NRE despite dist
        fo = _order(s, forced.id, "0000400", "pdf:0000400")
        _dist(s, fo)
        auto_match = _customer(s, "Catheter Auto", "cauto", "auto")  # excluded (has dist)
        ao = _order(s, auto_match.id, "0000500", "pdf:0000500")
        _dist(s, ao)

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client):
    client.post("/auth/login", data={"email": "admin@example.com", "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
def test_index_classification(client):
    _login(client)
    body = client.get("/admin/nre-projects/").data.decode()
    assert "AbbVie Inc." in body        # auto + no dist → NRE
    assert "Forced NRE Co" in body      # forced nre (even with dist)
    assert "A Caring Hand" not in body  # forced catheter → excluded
    assert "Catheter Auto" not in body  # auto + dist → excluded


def test_detail_has_tracker_and_dropdown(client, app):
    with session_scope(app) as s:
        cid = s.query(Customer).filter_by(company_key="abbvie").one().id
    _login(client)
    body = client.get(f"/admin/nre-projects/{cid}").data.decode()
    assert "Project Tracker" in body
    assert 'name="customer_type"' in body
    assert "Force NRE" in body


def test_edit_saves_customer_type(client, app):
    with session_scope(app) as s:
        cid = s.query(Customer).filter_by(company_key="abbvie").one().id
    _login(client)
    r = client.post(f"/admin/nre-projects/{cid}/edit",
                    data={"facility_name": "AbbVie Inc.", "customer_type": "catheter",
                          "csrf_token": _csrf(client)})
    assert r.status_code in (302, 200)
    with session_scope(app) as s:
        assert s.get(Customer, cid).customer_type == "catheter"


# --------------------------------------------------------------------------- #
# Tracker CRUD
# --------------------------------------------------------------------------- #
def test_tracker_upsert_patch_delete(client, app):
    with session_scope(app) as s:
        cust = s.query(Customer).filter_by(company_key="abbvie").one()
        cid = cust.id
        oid = s.query(SalesOrder).filter_by(customer_id=cid).one().id
    _login(client)
    token = _csrf(client)

    # Create
    r = client.post(f"/admin/nre-projects/{cid}/tracker",
                    json={"sales_order_id": oid, "invoice_amount": "1,250.50",
                          "invoice_status": "Invoiced", "notes": "n"},
                    headers={"X-CSRF-Token": token})
    assert r.status_code == 200
    data = r.get_json()
    assert data["ok"] and data["entry"]["id"]
    entry_id = data["entry"]["id"]
    with session_scope(app) as s:
        e = s.get(NREProjectEntry, entry_id)
        assert str(e.invoice_amount) == "1250.50"
        assert e.invoice_status == "Invoiced"

    # Patch
    r = client.patch(f"/admin/nre-projects/tracker/{entry_id}",
                     json={"invoice_status": "Paid"}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200 and r.get_json()["ok"]
    with session_scope(app) as s:
        assert s.get(NREProjectEntry, entry_id).invoice_status == "Paid"

    # Delete
    r = client.delete(f"/admin/nre-projects/tracker/{entry_id}", headers={"X-CSRF-Token": token})
    assert r.status_code == 200 and r.get_json()["ok"]
    with session_scope(app) as s:
        assert s.get(NREProjectEntry, entry_id) is None


# --------------------------------------------------------------------------- #
# Admin_docs library + folder scaffold
# --------------------------------------------------------------------------- #
def test_nre_project_docs_library_route(client):
    _login(client)
    r = client.get("/admin/nre-projects")  # admin_docs library route
    assert r.status_code == 200
    assert "NRE Project Documents" in r.data.decode()


def test_refresh_folders_creates_folders(client, app):
    _login(client)
    r = client.post("/admin/nre-projects/refresh-folders",
                    data={"csrf_token": _csrf(client)}, follow_redirects=False)
    assert r.status_code == 302
    with session_scope(app) as s:
        cust_folder = (
            s.query(AdminDocFolder)
            .filter_by(library_key="nre_projects", parent_id=None, name="AbbVie Inc.")
            .first()
        )
        assert cust_folder is not None
        sub = (
            s.query(AdminDocFolder)
            .filter_by(library_key="nre_projects", parent_id=cust_folder.id, name="SO-0000300")
            .first()
        )
        assert sub is not None
