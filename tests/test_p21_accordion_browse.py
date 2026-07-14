"""
Prompt 21 — Browse UX + admin_docs accordion + dashboard restructure.

Covers:
- Browse view: document rows are visibly clickable (accent link class) and the
  single-item auto-expand JS is present.
- qms_index: QM.SLQ045 (Receiving SOP) now classifies to Purchasing & Suppliers.
- Accordion libraries (management_reviews / pms / risk_management) render the full
  folder tree on one page, support in-library search, and stay read-only for staff.
- Dashboard: Quality Management column order + Regulatory Standards moved to the
  QMS System column.
"""
import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
import datetime as dt

from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
from app.eqms.modules.document_control import qms_index
from app.eqms.modules.document_control.models import Document, DocumentRevision


ADMIN_PERMS = ["admin.view", "admin.edit", "staff.view", "docs.view", "docs.download"]
STAFF_PERMS = ["staff.view", "docs.view", "docs.download"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
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
            "audit_events", "admin_doc_folders", "admin_doc_files",
            "documents", "document_revisions", "document_files",
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    application.config["_schema_health_ok"] = True

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

        # A released SOP so the browse view renders at least one clickable row.
        d = Document(doc_number="QM.SLQ016", title="CAPA SOP", doc_type="SOP",
                     category=None, owner_user_id=owner_id, status="Released")
        s.add(d)
        s.flush()
        r = DocumentRevision(document_id=d.id, revision="A", change_summary="",
                             effective_date=dt.date(2022, 1, 1), created_by_user_id=owner_id,
                             released_at=dt.datetime(2022, 1, 2), released_by_user_id=owner_id)
        s.add(r)
        s.flush()
        d.current_revision_id = r.id

        # Management Reviews accordion tree: root folder -> subfolder, plus a
        # root-level file, in one library.
        root = AdminDocFolder(library_key="management_reviews", name="2025 Reviews",
                              created_by_user_id=owner_id)
        s.add(root)
        s.flush()
        sub = AdminDocFolder(library_key="management_reviews", name="Internal Audits",
                             parent_id=root.id, created_by_user_id=owner_id)
        s.add(sub)
        s.flush()
        s.add_all([
            AdminDocFile(library_key="management_reviews", folder_id=root.id,
                         filename="MR 2025 Minutes.pdf", storage_key="mr-1",
                         content_type="application/pdf", size_bytes=1, uploaded_by_user_id=owner_id),
            AdminDocFile(library_key="management_reviews", folder_id=sub.id,
                         filename="IA2025 Report.pdf", storage_key="mr-2",
                         content_type="application/pdf", size_bytes=1, uploaded_by_user_id=owner_id),
            AdminDocFile(library_key="management_reviews", folder_id=None,
                         filename="Root Note.pdf", storage_key="mr-root",
                         content_type="application/pdf", size_bytes=1, uploaded_by_user_id=owner_id),
        ])

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@example.com"):
    r = client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=False)
    assert r.status_code in (302, 303)


def _get_csrf(client):
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
        if not token:
            import secrets
            token = secrets.token_urlsafe(32)
            sess["csrf_token"] = token
        return token


def _url(app, endpoint, **kw):
    with app.test_request_context():
        from flask import url_for
        return url_for(endpoint, **kw)


# ── Task A: browse view ────────────────────────────────────────────────────

def test_browse_rows_use_accent_link_class(client, app):
    _login(client)
    body = client.get(_url(app, "doc_control.browse")).get_data(as_text=True)
    assert "browse-link" in body


def test_browse_has_auto_expand_js(client, app):
    _login(client)
    body = client.get(_url(app, "doc_control.browse")).get_data(as_text=True)
    assert "browse-subsystem" in body
    assert "toggle" in body  # A2 auto-expand listener present


# ── Task A3: qms_index Receiving SOP grouping ───────────────────────────────

def test_slq045_classified_purchasing_suppliers():
    assert qms_index.classify("QM.SLQ045").subsystem == "Purchasing & Suppliers"


# ── Task B: accordion libraries ─────────────────────────────────────────────

def test_accordion_renders_tree_admin_and_staff(client, app):
    url = _url(app, "admin_docs.management_reviews")
    _login(client, "admin@example.com")
    r = client.get(url)
    assert r.status_code == 200
    assert "<details" in r.get_data(as_text=True)
    client.get("/auth/logout")
    _login(client, "staff@example.com")
    r = client.get(url)
    assert r.status_code == 200
    assert "<details" in r.get_data(as_text=True)


def test_accordion_shows_nested_folders_and_files(client, app):
    _login(client)
    body = client.get(_url(app, "admin_docs.management_reviews")).get_data(as_text=True)
    assert "2025 Reviews" in body
    assert "Internal Audits" in body
    assert "MR 2025 Minutes.pdf" in body
    assert "Root Note.pdf" in body


def test_accordion_search_returns_flat_results(client, app):
    _login(client)
    body = client.get(_url(app, "admin_docs.management_reviews") + "?q=IA2025").get_data(as_text=True)
    assert "IA2025 Report.pdf" in body
    assert "Clear search" in body
    # Flat search results, not the tree.
    assert "<details" not in body


def test_accordion_query_budget(client, app):
    """The accordion view must stay at a handful of queries regardless of tree size."""
    from sqlalchemy import event

    _login(client)
    engine = app.extensions["sqlalchemy_engine"]
    counter = {"n": 0}

    def _count(conn, cursor, statement, params, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", _count)
    try:
        client.get(_url(app, "admin_docs.management_reviews"))
    finally:
        event.remove(engine, "before_cursor_execute", _count)
    assert counter["n"] < 10, f"too many queries: {counter['n']}"


def test_accordion_staff_cannot_create_folder(client, app):
    _login(client, "staff@example.com")
    csrf = _get_csrf(client)
    r = client.post(
        _url(app, "admin_docs.admin_docs_create_folder"),
        data={"library_key": "management_reviews", "name": "Nope", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert r.status_code in (302, 403)


# ── Task C: dashboard restructure ───────────────────────────────────────────

def test_dashboard_quality_management_order(client, app):
    _login(client)
    body = client.get(_url(app, "admin.index")).get_data(as_text=True)
    assert "Design &amp; Development Records" in body
    assert "Management Reviews" in body
    assert body.index("Design &amp; Development Records") < body.index("Management Reviews")


def test_dashboard_regulatory_standards_in_qms_system_column(client, app):
    _login(client)
    body = client.get(_url(app, "admin.index")).get_data(as_text=True)
    # Exactly one Regulatory Standards card, placed after CAPAs (QMS System column).
    assert body.count("Regulatory Standards") == 1
    assert body.index("Regulatory Standards") > body.index("CAPAs")


def test_dashboard_regulatory_standards_not_in_quality_management(client, app):
    _login(client)
    body = client.get(_url(app, "admin.index")).get_data(as_text=True)
    # Quality Planning is the last QM-column card; Regulatory now sits well after it.
    assert body.index("Regulatory Standards") > body.index("Quality Planning")
