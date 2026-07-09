"""
E2 — QMS Document Index + in-app DCO Log / change-history view (Phase 3 Prompt 7).

Rendered-HTML assertion tests: the QMS Index groups the controlled set by ISO
13485 clause and by subsystem (hiding obsolete by default, surfacing unmapped
docs under "Unclassified"), and the DCO Log view lists DCO_Log_v2.csv rows with
DCO/document/free-text filters, empty-state, and bidirectional cross-links. Both
pages are read-only and available to staff (docs.view).
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.document_control import dco_log
from app.eqms.modules.document_control.models import Document, DocumentRevision
from app.eqms.modules.document_control.qms_index import classify


ADMIN_PERMS = ["admin.view", "admin.edit", "docs.view", "docs.create", "docs.edit",
               "docs.release", "docs.obsolete", "docs.download"]
STAFF_PERMS = ["admin.view", "docs.view", "docs.download"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    engine = application.extensions["sqlalchemy_engine"]
    tables = [
        Base.metadata.tables[t]
        for t in (
            "users", "roles", "permissions", "user_roles", "role_permissions",
            "audit_events", "documents", "document_revisions", "document_files",
            "admin_doc_folders", "admin_doc_files",
            # Global search also spans equipment + suppliers (Prompt 13 D5).
            "equipment", "suppliers",
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    application.config["_schema_health_ok"] = True

    # Default: point the DCO loader at a missing file (hermetic; no repo CSV).
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", tmp_path / "no_dco_log.csv")
    dco_log._cache.clear()

    with session_scope(application) as s:
        all_keys = sorted(set(ADMIN_PERMS + STAFF_PERMS))
        perms = {k: Permission(key=k, name=k) for k in all_keys}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms[k] for k in ADMIN_PERMS)
        staff_role = Role(key="staff", name="Staff")
        staff_role.permissions.extend(perms[k] for k in STAFF_PERMS)

        admin_user = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        admin_user.roles.append(admin_role)
        staff_user = User(email="staff@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        staff_user.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin_user, staff_user])
        s.flush()
        owner_id = admin_user.id

        def _released_doc(number, title, doc_type, category, status="Released", rev="A"):
            d = Document(doc_number=number, title=title, doc_type=doc_type,
                         category=category, owner_user_id=owner_id, status=status)
            s.add(d)
            s.flush()
            r = DocumentRevision(document_id=d.id, revision=rev, change_summary="",
                                 effective_date=dt.date(2022, 1, 1), created_by_user_id=owner_id,
                                 released_at=dt.datetime(2022, 1, 2), released_by_user_id=owner_id)
            s.add(r)
            s.flush()
            d.current_revision_id = r.id
            return d

        _released_doc("QM.SLQ016", "CAPA SOP", "SOP", "CAPA & Complaints")       # mapped -> CAPA
        _released_doc("QM.SLQ020", "Purchasing Controls SOP", "SOP", "Purchasing")  # mapped -> Purchasing & Suppliers
        _released_doc("QM.SLQ099", "Retired SOP", "SOP", "Legacy", status="Obsolete")  # obsolete, unmapped
        _released_doc("ZZZ-CUSTOM-1", "Uncontrolled Extra", "SOP", None)          # unmapped -> Unclassified

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@example.com"):
    r = client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=False)
    assert r.status_code in (302, 303)


def _doc_id(client, doc_number):
    import re
    html = client.get(f"/admin/search?q={doc_number}").get_data(as_text=True)
    m = re.search(r"/admin/modules/document-control/(\d+)", html)
    assert m, f"no detail link found for {doc_number}"
    return int(m.group(1))


# --- QMS Document Index -----------------------------------------------------
def test_qms_index_by_clause_groups_and_links(client):
    _login(client)
    html = client.get("/admin/modules/document-control/index").get_data(as_text=True)
    assert "QMS Document Index" in html
    assert "8.5 Improvement (CAPA)" in html          # ISO clause bucket for QM.SLQ016
    assert "CAPA SOP" in html
    assert "/admin/modules/document-control/" in html  # links to detail
    # Unmapped doc surfaces under the visible Unclassified bucket.
    assert "Unclassified" in html
    assert "Uncontrolled Extra" in html


def test_qms_index_by_subsystem(client):
    _login(client)
    html = client.get("/admin/modules/document-control/index?group=subsystem").get_data(as_text=True)
    assert "Purchasing &amp; Suppliers" in html or "Purchasing & Suppliers" in html
    assert "Purchasing Controls SOP" in html


def test_qms_index_hides_obsolete_by_default_and_shows_with_toggle(client):
    _login(client)
    default_html = client.get("/admin/modules/document-control/index").get_data(as_text=True)
    assert "Retired SOP" not in default_html
    shown = client.get("/admin/modules/document-control/index?show_obsolete=1").get_data(as_text=True)
    assert "Retired SOP" in shown
    assert "OBSOLETE" in shown


def test_qms_index_staff_read_only(client):
    _login(client, email="staff@example.com")
    resp = client.get("/admin/modules/document-control/index")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "New document" not in body  # no write affordances


# --- DCO Log / change-history view ------------------------------------------
def _write_csv(tmp_path):
    csv_path = tmp_path / "dco.csv"
    csv_path.write_text(
        "dco_number,document_number,document_title,from_rev,to_rev,change_description,"
        "originator,date_requested,effective_date,impact_assessments\n"
        "DCO003,QM.SLQ016,CAPA SOP,-,A,Initial release,J. Smith,2020-09-01,2020-09-25,\n"
        "DCO009,QM.SLQ016,CAPA SOP,A,B,Updated scope,A. Jones,2022-03-01,2022-03-17,Risk\n"
        "DCO020,QM.SLQ020,Purchasing Controls SOP,-,A,New purchasing SOP,J. Smith,2021-01-01,2021-02-01,\n",
        encoding="utf-8",
    )
    return csv_path


def test_dco_log_lists_rows_and_links_back(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", _write_csv(tmp_path))
    dco_log._cache.clear()
    _login(client)
    html = client.get("/admin/modules/document-control/dco-log").get_data(as_text=True)
    assert "DCO Log / Change History" in html
    assert "DCO009" in html and "Updated scope" in html
    # Rows for docs that exist in the DB link back to the detail page.
    assert "/admin/modules/document-control/" in html


def test_dco_log_filters_by_document_number(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", _write_csv(tmp_path))
    dco_log._cache.clear()
    _login(client)
    html = client.get("/admin/modules/document-control/dco-log?document_number=QM.SLQ020").get_data(as_text=True)
    assert "New purchasing SOP" in html
    assert "Updated scope" not in html


def test_dco_log_free_text_search(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", _write_csv(tmp_path))
    dco_log._cache.clear()
    _login(client)
    html = client.get("/admin/modules/document-control/dco-log?q=scope").get_data(as_text=True)
    assert "Updated scope" in html
    assert "New purchasing SOP" not in html


def test_dco_log_empty_state_when_csv_missing(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", tmp_path / "does_not_exist.csv")
    dco_log._cache.clear()
    _login(client)
    resp = client.get("/admin/modules/document-control/dco-log")
    assert resp.status_code == 200
    assert "No change-history log found" in resp.get_data(as_text=True)


def test_dco_log_staff_read_only(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", _write_csv(tmp_path))
    dco_log._cache.clear()
    _login(client, email="staff@example.com")
    resp = client.get("/admin/modules/document-control/dco-log")
    assert resp.status_code == 200


# --- Cross-linking from the detail timeline ---------------------------------
def test_detail_timeline_links_to_dco_log_filtered(client):
    _login(client)
    doc_id = _doc_id(client, "QM.SLQ016")
    html = client.get(f"/admin/modules/document-control/{doc_id}").get_data(as_text=True)
    assert "dco-log?document_number=QM.SLQ016" in html


# --- Mapping unit tests -----------------------------------------------------
def test_classify_maps_family_and_derivatives():
    assert classify("QM.SLQ016").subsystem == "CAPA"
    assert classify("FM1-QM.SLQ016").subsystem == "CAPA"        # form inherits parent
    assert classify("TMP1-QM.SLQ020").subsystem == "Purchasing & Suppliers"
    assert classify("QM.SLQ099").subsystem == "Unclassified"    # no family mapping
    assert classify("").subsystem == "Unclassified"
    assert classify(None).subsystem == "Unclassified"
