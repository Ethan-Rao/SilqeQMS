"""
Prompt 20 — QM Documents browse view.

Rendered-HTML assertion tests for the accordion browse page: grouped by QMS
subsystem, child forms nested under parent SOPs by SLQ family, administration
forms surfaced from the forms_templates_travelers admin_docs library, and the
configured subsystem ordering. Read-only and staff-accessible (docs.view).
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
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
            "audit_events", "documents", "document_revisions", "document_files",
            "admin_doc_folders", "admin_doc_files",
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

        def _doc(number, title, doc_type, status="Released"):
            d = Document(doc_number=number, title=title, doc_type=doc_type,
                         category=None, owner_user_id=owner_id, status=status)
            s.add(d)
            s.flush()
            r = DocumentRevision(document_id=d.id, revision="A", change_summary="",
                                 effective_date=dt.date(2022, 1, 1), created_by_user_id=owner_id,
                                 released_at=dt.datetime(2022, 1, 2), released_by_user_id=owner_id)
            s.add(r)
            s.flush()
            d.current_revision_id = r.id
            return d

        # CAPA (family 16): a parent SOP with a child form nested beneath it.
        _doc("QM.SLQ016", "CAPA SOP", "SOP")
        _doc("FM1-QM.SLQ016", "CAPA Report Form", "Form")
        # Design Control (family 4) and Production & Service (family 19) for ordering.
        _doc("QM.SLQ004", "Design Control Program SOP", "SOP")
        _doc("QM.SLQ019", "Identification and Traceability SOP", "SOP")
        # A draft doc must NOT appear (only Released are browsable).
        _doc("QM.SLQ099", "Draft Only", "SOP", status="Draft")

        # Administration forms: one blank template (shown) + one inside a
        # "Completed" folder (a filled record — must be skipped).
        blank = AdminDocFolder(library_key="forms_templates_travelers", name="Blank Forms",
                               created_by_user_id=owner_id)
        completed = AdminDocFolder(library_key="forms_templates_travelers", name="Completed Records",
                                   created_by_user_id=owner_id)
        s.add_all([blank, completed])
        s.flush()
        s.add_all([
            AdminDocFile(library_key="forms_templates_travelers", folder_id=blank.id,
                         filename="AD.SLQ001 A Patient Experience Release Form.pdf",
                         storage_key="k-blank", content_type="application/pdf", size_bytes=1,
                         uploaded_by_user_id=owner_id),
            AdminDocFile(library_key="forms_templates_travelers", folder_id=completed.id,
                         filename="AD.SLQ001 FILLED 2025.pdf",
                         storage_key="k-filled", content_type="application/pdf", size_bytes=1,
                         uploaded_by_user_id=owner_id),
        ])

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@example.com"):
    r = client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=False)
    assert r.status_code in (302, 303)


def _browse_url(app):
    with app.test_request_context():
        from flask import url_for
        return url_for("doc_control.browse")


def test_browse_200_admin_and_staff(client, app):
    url = _browse_url(app)
    _login(client, "admin@example.com")
    assert client.get(url).status_code == 200
    client.get("/auth/logout")
    _login(client, "staff@example.com")
    r = client.get(url)
    assert r.status_code == 200
    # Read-only staff still gets links into the existing detail viewer.
    assert "document-control" in r.get_data(as_text=True)


def test_browse_has_details_accordion(client, app):
    _login(client)
    body = client.get(_browse_url(app)).get_data(as_text=True)
    assert "<details" in body


def test_browse_filter_query_includes_capa_row(client, app):
    """Client-side filter: the server still renders the CAPA SOP row for ?q=SLQ016."""
    _login(client)
    body = client.get(_browse_url(app) + "?q=SLQ016").get_data(as_text=True)
    assert "QM.SLQ016" in body
    assert "CAPA SOP" in body


def test_browse_subsystem_ordering(client, app):
    """Production & Service must appear before Design Control."""
    _login(client)
    body = client.get(_browse_url(app)).get_data(as_text=True)
    assert "Production &amp; Service" in body
    assert "Design Control" in body
    assert body.index("Production &amp; Service") < body.index("Design Control")


def test_browse_nests_child_form_under_parent(client, app):
    _login(client)
    body = client.get(_browse_url(app)).get_data(as_text=True)
    assert "FM1-QM.SLQ016" in body
    assert "CAPA Report Form" in body


def test_browse_admin_forms_section_skips_completed(client, app):
    _login(client)
    body = client.get(_browse_url(app)).get_data(as_text=True)
    assert "Patient Experience Release Form" in body   # blank template shown
    assert "AD.SLQ001 FILLED 2025.pdf" not in body     # completed record skipped


def test_browse_excludes_draft_documents(client, app):
    _login(client)
    body = client.get(_browse_url(app)).get_data(as_text=True)
    assert "Draft Only" not in body
