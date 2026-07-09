"""
E1 — Unified discovery + Document Control at scale (Phase 3 Prompt 5).

Rendered-HTML assertion tests: global search spans Document Control + admin_docs,
the DC list filters by type/status/category with an obsolete toggle, the detail
page renders the full revision-history timeline (current badge, superseded notes,
obsolete banner), and the shared DCO_Log_v2 loader maps changes per revision.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.document_control import dco_log
from app.eqms.modules.document_control.models import Document, DocumentRevision


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
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    application.config["_schema_health_ok"] = True

    # By default point the DCO loader at a missing file (hermetic; no repo CSV).
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", tmp_path / "no_dco_log.csv")

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

        # Multi-revision Released document (A -> B -> C -> D current).
        capa = Document(doc_number="QM.SLQ016", title="CAPA SOP", doc_type="SOP",
                        category="CAPA & Complaints", owner_user_id=owner_id, status="Released")
        s.add(capa)
        s.flush()
        last_rev = None
        for i, label in enumerate(["A", "B", "C", "D"]):
            r = DocumentRevision(
                document_id=capa.id, revision=label, change_summary=f"Rev {label} change",
                effective_date=dt.date(2020 + i, 1, 1), created_by_user_id=owner_id,
                released_at=dt.datetime(2020 + i, 1, 2), released_by_user_id=owner_id,
            )
            s.add(r)
            s.flush()
            last_rev = r
        capa.current_revision_id = last_rev.id

        # Obsolete document.
        old = Document(doc_number="QM.SLQ099", title="Retired SOP", doc_type="SOP",
                       category="Legacy", owner_user_id=owner_id, status="Obsolete")
        s.add(old)
        s.flush()
        r_old = DocumentRevision(document_id=old.id, revision="A", change_summary="", created_by_user_id=owner_id,
                                 released_at=dt.datetime(2019, 1, 2), released_by_user_id=owner_id)
        s.add(r_old)
        s.flush()
        old.current_revision_id = r_old.id

        # A Form (distinct doc_type for filter tests).
        form = Document(doc_number="FM1-QM.SLQ020", title="Purchase Order Form", doc_type="Form",
                        category="Purchasing", owner_user_id=owner_id, status="Released")
        s.add(form)
        s.flush()
        r_form = DocumentRevision(document_id=form.id, revision="A", change_summary="", created_by_user_id=owner_id,
                                  released_at=dt.datetime(2021, 1, 2), released_by_user_id=owner_id)
        s.add(r_form)
        s.flush()
        form.current_revision_id = r_form.id

        # An admin_docs library file (cross-system search target).
        folder = AdminDocFolder(library_key="qms_documents", name="SOPs", created_by_user_id=owner_id)
        s.add(folder)
        s.flush()
        s.add(AdminDocFile(
            library_key="qms_documents", folder_id=folder.id,
            filename="QM.SLQ021 D Product Complaint System SOP.docx",
            storage_key="k", content_type="application/octet-stream", size_bytes=10,
            description="Handling of product complaints", uploaded_by_user_id=owner_id,
        ))

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@example.com"):
    r = client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=False)
    assert r.status_code in (302, 303)


# --- Global search ----------------------------------------------------------
def test_search_finds_controlled_document_by_number(client):
    _login(client)
    html = client.get("/admin/search?q=QM.SLQ016").get_data(as_text=True)
    assert "CAPA SOP" in html
    assert "/admin/modules/document-control/" in html  # deep link to DC detail


def test_search_finds_admin_doc_file_by_keyword(client):
    _login(client)
    html = client.get("/admin/search?q=complaint").get_data(as_text=True)
    assert "Product Complaint System SOP" in html
    assert "/admin/admin-docs/documents/" in html  # deep link to admin_docs viewer


def test_staff_can_search_read_only(client):
    _login(client, email="staff@example.com")
    resp = client.get("/admin/search?q=CAPA")
    assert resp.status_code == 200
    assert "CAPA SOP" in resp.get_data(as_text=True)


# --- Document Control list at scale ----------------------------------------
def test_list_type_filter(client):
    _login(client)
    html = client.get("/admin/modules/document-control/?doc_type=Form").get_data(as_text=True)
    assert "Purchase Order Form" in html
    assert "CAPA SOP" not in html


def test_list_hides_obsolete_by_default_and_shows_with_toggle(client):
    _login(client)
    default_html = client.get("/admin/modules/document-control/").get_data(as_text=True)
    assert "Retired SOP" not in default_html
    with_obsolete = client.get("/admin/modules/document-control/?show_obsolete=1").get_data(as_text=True)
    assert "Retired SOP" in with_obsolete


def test_list_status_filter_obsolete(client):
    _login(client)
    html = client.get("/admin/modules/document-control/?status=Obsolete").get_data(as_text=True)
    assert "Retired SOP" in html
    assert "CAPA SOP" not in html


# --- Detail: revision timeline + obsolete clarity ---------------------------
def test_detail_renders_full_lineage_with_current_and_superseded(client):
    _login(client)
    doc_id = _doc_id(client, "QM.SLQ016")
    html = client.get(f"/admin/modules/document-control/{doc_id}").get_data(as_text=True)
    assert "Revision history" in html
    for label in ("Revision A", "Revision B", "Revision C", "Revision D"):
        assert label in html
    assert "CURRENT / ACTIVE" in html
    assert "Superseded by Rev" in html  # prior revisions flagged


def test_detail_obsolete_banner(client):
    _login(client)
    doc_id = _doc_id(client, "QM.SLQ099")
    html = client.get(f"/admin/modules/document-control/{doc_id}").get_data(as_text=True)
    assert "This document is obsolete." in html


def test_detail_shows_dco_reference_from_log(client, app, tmp_path, monkeypatch):
    # Point the shared loader at a controlled temp CSV mapping QM.SLQ016 D -> DCO093.
    csv_path = tmp_path / "dco.csv"
    csv_path.write_text(
        "dco_number,document_number,document_title,from_rev,to_rev,change_description,"
        "originator,date_requested,effective_date,impact_assessments\n"
        "093,QM.SLQ016,CAPA SOP,C,D,Aligned to ISO 13485,J. Smith,2024-02-01,2024-03-01,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", csv_path)
    dco_log._cache.clear()

    _login(client)
    doc_id = _doc_id(client, "QM.SLQ016")
    html = client.get(f"/admin/modules/document-control/{doc_id}").get_data(as_text=True)
    assert "DCO 093" in html or "DCO093" in html
    # DCO reference line surfaces the originator/date from the log.
    assert "J. Smith" in html


def _doc_id(client, doc_number):
    # Resolve the DB id via the search results deep link.
    html = client.get(f"/admin/search?q={doc_number}").get_data(as_text=True)
    import re
    m = re.search(r"/admin/modules/document-control/(\d+)", html)
    assert m, f"no detail link found for {doc_number}"
    return int(m.group(1))


# --- Shared DCO_Log_v2 loader (reused by E2) --------------------------------
def test_dco_log_loader_maps_changes(tmp_path):
    csv_path = tmp_path / "dco.csv"
    csv_path.write_text(
        "dco_number,document_number,document_title,from_rev,to_rev,change_description,"
        "originator,date_requested,effective_date,impact_assessments\n"
        "003,QM.SLQ016,CAPA SOP,-,A,Initial release,,,2020-09-25,\n"
        "009,QM.SLQ016,CAPA SOP,A,B,Updated scope,,,2022-03-17,\n"
        "062,QM.SLQ016,CAPA SOP,B,C,Clarified steps,,,2023-01-30,\n",
        encoding="utf-8",
    )
    dco_log._cache.clear()
    by_rev = dco_log.change_by_revision("QM.SLQ016", path=csv_path)
    assert set(by_rev.keys()) == {"A", "B", "C"}
    assert by_rev["B"].dco_number == "009"
    assert by_rev["B"].effective_date == "2022-03-17"

    rows = dco_log.changes_for_document("qm.slq016", path=csv_path)  # case-insensitive
    assert [r.to_rev for r in rows] == ["A", "B", "C"]


def test_dco_log_missing_file_is_empty(tmp_path):
    dco_log._cache.clear()
    assert dco_log.load_rows(tmp_path / "nope.csv") == []
    assert dco_log.change_by_revision("QM.SLQ016", path=tmp_path / "nope.csv") == {}


def test_rev_order_key_orders_correctly():
    assert dco_log.rev_order_key("A") < dco_log.rev_order_key("B")
    assert dco_log.rev_order_key("Z") < dco_log.rev_order_key("AA")
    assert dco_log.rev_order_key("") < dco_log.rev_order_key("A")
