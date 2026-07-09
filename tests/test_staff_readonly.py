"""
Phase 3 staff-access tests (corrected model, Dev Prompt 2 Section 1).

Team model: all staff get FULL read access to the whole QMS but are strictly
read-only. admin.view = access the admin shell + read shared content (granted to
admin and staff). admin.edit = admin-only system tools (admin only). Staff see
every dashboard card and can view/read/download/export, but every mutation route
and every admin tool returns a clean 403.

Follows the fixture style in tests/test_edms_improvements.py: cherry-pick the
tables each test needs, a CSRF helper, and a login helper. Mutation 403s are
enforced by require_permission decorators, which fire before any DB access, so
the commercial-module tables are not required for those assertions.
"""

import io

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.document_control.models import Document, DocumentFile, DocumentRevision


ADMIN_EMAIL = "admin@example.com"
STAFF_EMAIL = "staff@example.com"
PW = "pw"

# Canonical staff permission set. MUST match scripts/init_db.py staff_permissions.
STAFF_KEYS = {
    "staff.view",
    "admin.view",
    "docs.view",
    "docs.download",
    "distribution_log.view",
    "distribution_log.export",
    "tracing_reports.view",
    "tracing_reports.download",
    "approvals.view",
    "approvals.download",
    "customers.view",
    "sales_dashboard.view",
    "sales_dashboard.export",
    "sales_orders.view",
    "shipstation.view",
    "equipment.view",
    "suppliers.view",
    "supplies.view",
    "purchasing.view",
    "manufacturing.view",
    "training.view",
}

# Admin gets everything staff has, plus the admin-only edit/tools capability and
# the Document Control lifecycle permissions used by the test helpers.
ADMIN_EXTRA_KEYS = {
    "admin.edit",
    "docs.create",
    "docs.edit",
    "docs.release",
    "docs.obsolete",
    "training.manage",
}


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    app = create_app()
    engine = app.extensions["sqlalchemy_engine"]
    tables_needed = [
        Base.metadata.tables[t]
        for t in (
            "users", "roles", "permissions", "user_roles", "role_permissions",
            "audit_events", "documents", "document_revisions", "document_files",
            "admin_doc_folders", "admin_doc_files",
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables_needed)
    app.config["_schema_health_ok"] = True

    with session_scope(app) as s:
        all_keys = STAFF_KEYS | ADMIN_EXTRA_KEYS
        perms = {k: Permission(key=k, name=k) for k in all_keys}

        role_admin = Role(key="admin", name="Administrator")
        role_admin.permissions.extend(perms.values())  # admin holds everything
        role_staff = Role(key="staff", name="Staff (read-only)")
        role_staff.permissions.extend(perms[k] for k in STAFF_KEYS)

        admin_user = User(email=ADMIN_EMAIL, password_hash=generate_password_hash(PW), is_active=True)
        admin_user.roles.append(role_admin)
        staff_user = User(email=STAFF_EMAIL, password_hash=generate_password_hash(PW), is_active=True)
        staff_user.roles.append(role_staff)

        s.add_all(list(perms.values()) + [role_admin, role_staff, admin_user, staff_user])

    return app


def _get_csrf(client):
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
        if not token:
            import secrets
            token = secrets.token_urlsafe(32)
            sess["csrf_token"] = token
        return token


def _login(client, email):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=False)


def _post(client, url, data=None, **kwargs):
    csrf = _get_csrf(client)
    data = dict(data or {})
    data["csrf_token"] = csrf
    return client.post(url, data=data, **kwargs)


def _url(app, endpoint, **values):
    with app.test_request_context():
        from flask import url_for
        return url_for(endpoint, **values)


def _create_and_release_document(client, app, doc_number="QM.SLQ016", category="QM SOPs and WIs"):
    _post(client, "/admin/modules/document-control/new",
          data={"doc_number": doc_number, "title": "Test SOP", "doc_type": "SOP", "category": category},
          follow_redirects=False)
    with session_scope(app) as s:
        d = s.query(Document).filter(Document.doc_number == doc_number).one()
        rev = s.query(DocumentRevision).filter(DocumentRevision.document_id == d.id).one()
        doc_id, rev_id = d.id, rev.id
    csrf = _get_csrf(client)
    client.post(
        f"/admin/modules/document-control/{doc_id}/revisions/{rev_id}/upload",
        data={"file": (io.BytesIO(b"controlled content"), "sop.pdf"), "csrf_token": csrf},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    with session_scope(app) as s:
        file_id = s.query(DocumentFile).filter(DocumentFile.revision_id == rev_id).one().id
    _post(client, f"/admin/modules/document-control/{doc_id}/revisions/{rev_id}/release",
          data={"reason": "Initial release", "change_summary": "Rev A", "effective_date": "2026-01-15"},
          follow_redirects=False)
    return doc_id, rev_id, file_id


# ---------------------------------------------------------------------------
# Staff sees the whole dashboard, read-only, with no Admin Tools card
# ---------------------------------------------------------------------------

def test_admin_dashboard_shows_admin_tools(app):
    admin = app.test_client()
    _login(admin, ADMIN_EMAIL)
    r = admin.get("/admin/")
    assert r.status_code == 200
    assert b"Admin Tools" in r.data


def test_staff_dashboard_shows_all_columns_without_admin_tools(app):
    staff = app.test_client()
    _login(staff, STAFF_EMAIL)
    r = staff.get("/admin/")
    assert r.status_code == 200
    body = r.data.decode("utf-8")

    # Every module card must be visible to staff (all four dashboard columns).
    for label in (
        "QM Documents", "Management Reviews", "Post Market Surveillance",
        "Risk Management", "Design History Files", "Regulatory Standards",
        "Manufacturing", "Equipment", "Supplies", "Purchasing", "NCRs",
        "Employee Training", "Distribution Log", "Sales Dashboard",
        "Customers", "Suppliers", "NRE Projects",
        "Document Control", "CAPAs", "Forms, Templates",
    ):
        assert label in body, f"Staff dashboard is missing the '{label}' card"

    # The Admin Tools card must NOT appear for staff.
    assert "Admin Tools" not in body


# ---------------------------------------------------------------------------
# Staff read access
# ---------------------------------------------------------------------------

def test_staff_can_read_view_download_controlled_documents(app):
    admin = app.test_client()
    _login(admin, ADMIN_EMAIL)
    doc_id, rev_id, file_id = _create_and_release_document(admin, app)

    staff = app.test_client()
    _login(staff, STAFF_EMAIL)
    assert staff.get("/admin/modules/document-control/").status_code == 200
    assert staff.get(f"/admin/modules/document-control/{doc_id}").status_code == 200
    assert staff.get(f"/admin/modules/document-control/files/{file_id}/view").status_code == 200
    r = staff.get(f"/admin/modules/document-control/files/{file_id}/download")
    assert r.status_code == 200
    assert r.data == b"controlled content"


def test_staff_can_browse_admin_docs_library(app):
    staff = app.test_client()
    _login(staff, STAFF_EMAIL)
    assert staff.get("/admin/qms-documents").status_code == 200
    assert staff.get("/admin/capas").status_code == 200


# ---------------------------------------------------------------------------
# Admin-only tools return 403 for staff
# ---------------------------------------------------------------------------

def test_staff_403_on_admin_tools_get(app):
    staff = app.test_client()
    _login(staff, STAFF_EMAIL)
    for url in (
        "/admin/diagnostics", "/admin/diagnostics/storage", "/admin/debug/permissions",
        "/admin/accounts", "/admin/audit", "/admin/audit/export", "/admin/reset-data",
    ):
        assert staff.get(url).status_code == 403, f"{url} should be 403 for staff"


def test_admin_can_reach_admin_tools_get(app):
    admin = app.test_client()
    _login(admin, ADMIN_EMAIL)
    # Endpoints that only touch tables present in this fixture. Confirms the
    # admin.edit re-gating does not lock the admin out of admin tools.
    for url in ("/admin/diagnostics", "/admin/accounts", "/admin/audit", "/admin/debug/permissions"):
        assert admin.get(url).status_code == 200, f"{url} should be 200 for admin"


# ---------------------------------------------------------------------------
# Staff mutation routes must 403 (document control + commercial modules)
# ---------------------------------------------------------------------------

def test_staff_403_on_document_control_mutations(app):
    admin = app.test_client()
    _login(admin, ADMIN_EMAIL)
    doc_id, rev_id, file_id = _create_and_release_document(admin, app, doc_number="QM.SLQ017")

    staff = app.test_client()
    _login(staff, STAFF_EMAIL)
    assert staff.get("/admin/modules/document-control/new").status_code == 403
    assert _post(staff, "/admin/modules/document-control/new",
                 data={"doc_number": "QM.SLQ999", "title": "x", "doc_type": "SOP"}).status_code == 403
    assert _post(staff, f"/admin/modules/document-control/{doc_id}/obsolete",
                 data={"reason": "nope"}).status_code == 403
    assert _post(staff, f"/admin/modules/document-control/{doc_id}/revisions/new").status_code == 403


def test_staff_403_on_admin_docs_mutations(app):
    staff = app.test_client()
    _login(staff, STAFF_EMAIL)
    assert _post(staff, "/admin/admin-docs/folders/new",
                 data={"library_key": "qms_documents", "name": "nope"}).status_code == 403
    csrf = _get_csrf(staff)
    r = staff.post(
        "/admin/admin-docs/documents/upload",
        data={"library_key": "qms_documents", "file": (io.BytesIO(b"x"), "x.pdf"), "csrf_token": csrf},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 403


def test_staff_403_on_commercial_mutations(app):
    """Representative commercial-module write routes must 403 for staff."""
    staff = app.test_client()
    _login(staff, STAFF_EMAIL)

    create_customer = _url(app, "customer_profiles.customers_new_post")
    generate_tracing = _url(app, "rep_traceability.tracing_generate_post")
    import_dist = _url(app, "rep_traceability.distribution_log_import_csv_post")

    assert _post(staff, create_customer, data={"facility_name": "X"}).status_code == 403
    assert _post(staff, generate_tracing, data={}).status_code == 403
    assert _post(staff, import_dist, data={}).status_code == 403


def test_staff_can_update_own_profile_but_not_other_admin_writes(app):
    """My Account is self-service (allowed); other admin-blueprint writes 403."""
    staff = app.test_client()
    _login(staff, STAFF_EMAIL)
    # Self-service profile update is allowed by the admin-shell guard.
    r = _post(staff, "/admin/me", data={"city": "Anywhere"})
    assert r.status_code == 302
    # Any other admin-blueprint write is blocked (defence-in-depth + route perm).
    assert _post(staff, "/admin/reset-data", data={"confirm_phrase": "DELETE ALL DATA"}).status_code == 403


def test_admin_docs_upload_still_works_for_admin(app):
    admin = app.test_client()
    _login(admin, ADMIN_EMAIL)
    csrf = _get_csrf(admin)
    r = admin.post(
        "/admin/admin-docs/documents/upload",
        data={"library_key": "qms_documents", "file": (io.BytesIO(b"ok"), "ok.pdf"), "csrf_token": csrf},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302


# ---------------------------------------------------------------------------
# Document Control category browsing / filters (P1.3, unchanged)
# ---------------------------------------------------------------------------

def test_document_control_category_grouping_and_obsolete_filter(app):
    admin = app.test_client()
    _login(admin, ADMIN_EMAIL)
    alpha_id, _, _ = _create_and_release_document(admin, app, doc_number="ALPHA-100", category="Alpha")
    _create_and_release_document(admin, app, doc_number="BETA-200", category="Beta")

    _post(admin, f"/admin/modules/document-control/{alpha_id}/obsolete",
          data={"reason": "Superseded by QM.SLQ052"}, follow_redirects=False)

    r = admin.get("/admin/modules/document-control/")
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    assert "BETA-200" in body
    assert "ALPHA-100" not in body

    r = admin.get("/admin/modules/document-control/?show_obsolete=1")
    body = r.data.decode("utf-8")
    assert "ALPHA-100" in body
    assert "OBSOLETE" in body

    r = admin.get("/admin/modules/document-control/?category=Beta&show_obsolete=1")
    body = r.data.decode("utf-8")
    assert "BETA-200" in body
    assert "ALPHA-100" not in body


def test_document_control_search_filter(app):
    admin = app.test_client()
    _login(admin, ADMIN_EMAIL)
    _create_and_release_document(admin, app, doc_number="QM.SLQ025", category="QM SOPs and WIs")
    _create_and_release_document(admin, app, doc_number="QM.SLQ029", category="QM SOPs and WIs")

    r = admin.get("/admin/modules/document-control/?q=SLQ025")
    body = r.data.decode("utf-8")
    assert "QM.SLQ025" in body
    assert "QM.SLQ029" not in body


# ---------------------------------------------------------------------------
# Seed: staff role is created idempotently with exactly the read-only matrix
# ---------------------------------------------------------------------------

def test_init_db_seeds_staff_role_read_only(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = f"sqlite:///{tmp_path/'init.db'}"
    monkeypatch.setenv("ADMIN_EMAIL", "admin@silqeqms.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")

    rbac_tables = [
        Base.metadata.tables[name]
        for name in ("users", "roles", "permissions", "user_roles", "role_permissions")
    ]
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(bind=engine, tables=rbac_tables)
    engine.dispose()

    from scripts.init_db import seed_only

    seed_only(database_url=db_url)
    seed_only(database_url=db_url)  # idempotent re-run must not error/duplicate

    engine = create_engine(db_url, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with SessionLocal() as s:
        staff = s.query(Role).filter(Role.key == "staff").one_or_none()
        assert staff is not None, "staff role was not seeded"
        perm_keys = {p.key for p in staff.permissions}
        assert perm_keys == STAFF_KEYS, (
            f"seeded staff role does not match expected read-only matrix.\n"
            f"missing={STAFF_KEYS - perm_keys}\nextra={perm_keys - STAFF_KEYS}"
        )
        # readonly role must remain exactly admin.view + docs.view (validation dep).
        readonly = s.query(Role).filter(Role.key == "readonly").one()
        assert {p.key for p in readonly.permissions} == {"admin.view", "docs.view"}
    engine.dispose()
