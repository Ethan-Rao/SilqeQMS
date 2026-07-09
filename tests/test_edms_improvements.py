import csv
import io
from datetime import timedelta

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.document_control.models import Document, DocumentFile, DocumentRevision
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder


@pytest.fixture()
def client(tmp_path, monkeypatch):
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
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables_needed)
    app.config["_schema_health_ok"] = True

    with session_scope(app) as s:
        perms = [
            Permission(key="admin.view", name="Admin: view shell"),
            Permission(key="admin.edit", name="Admin: edit"),
            Permission(key="docs.view", name="Docs: view"),
            Permission(key="docs.create", name="Docs: create"),
            Permission(key="docs.edit", name="Docs: edit drafts"),
            Permission(key="docs.release", name="Docs: release"),
            Permission(key="docs.obsolete", name="Docs: obsolete"),
            Permission(key="docs.download", name="Docs: download"),
        ]
        r = Role(key="admin", name="Administrator")
        r.permissions.extend(perms)
        u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        u.roles.append(r)
        s.add_all(perms + [r, u])

    return app.test_client()


def _get_csrf(client):
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
        if not token:
            import secrets
            token = secrets.token_urlsafe(32)
            sess["csrf_token"] = token
        return token


def _login(client):
    client.post("/auth/login", data={"email": "admin@example.com", "password": "pw"}, follow_redirects=False)


def _post(client, url, data=None, **kwargs):
    """POST with automatic CSRF token injection."""
    csrf = _get_csrf(client)
    if data is None:
        data = {}
    data["csrf_token"] = csrf
    return client.post(url, data=data, **kwargs)


def _create_and_release_document(client, app, doc_number="QMS-T01"):
    """Helper: create doc, upload a file, release it. Returns (doc_id, rev_id, file_id)."""
    _post(client, "/admin/modules/document-control/new",
          data={"doc_number": doc_number, "title": "Test Doc", "doc_type": "QMS"},
          follow_redirects=False)

    with session_scope(app) as s:
        d = s.query(Document).filter(Document.doc_number == doc_number).one()
        rev = s.query(DocumentRevision).filter(DocumentRevision.document_id == d.id).one()
        doc_id, rev_id = d.id, rev.id

    csrf = _get_csrf(client)
    client.post(
        f"/admin/modules/document-control/{doc_id}/revisions/{rev_id}/upload",
        data={"file": (io.BytesIO(b"test content"), "test.pdf"), "csrf_token": csrf},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    with session_scope(app) as s:
        df = s.query(DocumentFile).filter(DocumentFile.revision_id == rev_id).one()
        file_id = df.id

    _post(client, f"/admin/modules/document-control/{doc_id}/revisions/{rev_id}/release",
          data={"reason": "Initial release", "change_summary": "First release", "effective_date": "2026-01-15"},
          follow_redirects=False)

    return doc_id, rev_id, file_id


def test_obsolete_document_download_creates_distinct_audit_event(client):
    """Test 1: downloading from an obsolete doc records doc.download_obsolete."""
    app = client.application
    _login(client)
    doc_id, rev_id, file_id = _create_and_release_document(client, app)

    _post(client, f"/admin/modules/document-control/{doc_id}/obsolete",
          data={"reason": "Replaced by QMS-T02"},
          follow_redirects=False)

    with session_scope(app) as s:
        d = s.get(Document, doc_id)
        assert d.status == "Obsolete"

    r = client.get(f"/admin/modules/document-control/files/{file_id}/download")
    assert r.status_code == 200
    assert r.data == b"test content"

    with session_scope(app) as s:
        actions = [e.action for e in s.query(AuditEvent).order_by(AuditEvent.id.asc()).all()]
        assert "doc.download_obsolete" in actions
        assert "doc.download" not in actions


def test_obsolete_document_view_creates_distinct_audit_event(client):
    """Test 1 (view): viewing an obsolete doc records doc.view_obsolete."""
    app = client.application
    _login(client)
    doc_id, rev_id, file_id = _create_and_release_document(client, app, doc_number="QMS-V01")

    _post(client, f"/admin/modules/document-control/{doc_id}/obsolete",
          data={"reason": "Superseded"},
          follow_redirects=False)

    r = client.get(f"/admin/modules/document-control/files/{file_id}/view")
    assert r.status_code == 200

    with session_scope(app) as s:
        actions = [e.action for e in s.query(AuditEvent).order_by(AuditEvent.id.asc()).all()]
        assert "doc.view_obsolete" in actions


def test_audit_trail_csv_export(client):
    """Test 2: GET /admin/audit/export returns a valid CSV with all events."""
    app = client.application
    _login(client)

    _post(client, "/admin/modules/document-control/new",
          data={"doc_number": "QMS-E01", "title": "Export Test", "doc_type": "QMS"},
          follow_redirects=False)

    r = client.get("/admin/audit/export")
    assert r.status_code == 200
    assert r.content_type.startswith("text/csv")
    assert "attachment" in r.headers.get("Content-Disposition", "")

    text = r.data.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    expected_headers = {
        "id", "created_at", "action", "actor_user_email",
        "entity_type", "entity_id", "reason", "metadata_json",
        "client_ip", "request_id",
    }
    assert expected_headers == set(reader.fieldnames)
    assert len(rows) >= 2  # at least login + doc.create

    actions_in_csv = {row["action"] for row in rows}
    assert "doc.create" in actions_in_csv


def test_audit_trail_csv_export_with_date_filter(client):
    """Test 2 (filters): date filtering narrows the CSV output."""
    _login(client)

    _post(client, "/admin/modules/document-control/new",
          data={"doc_number": "QMS-F01", "title": "Filter Test", "doc_type": "QMS"},
          follow_redirects=False)

    r = client.get("/admin/audit/export?date_from=2099-01-01&date_to=2099-12-31")
    assert r.status_code == 200
    text = r.data.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert len(rows) == 0


def test_session_timeout_is_60_minutes(client):
    """SRS-4.3: PERMANENT_SESSION_LIFETIME must be 60 minutes (sliding window)."""
    app = client.application
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=60)
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is True


def test_next_revision_sequential_alphabetical():
    """SRS-1.11: revision letters follow sequential alphabetical order A → B → C → ... → Z → AA."""
    from app.eqms.modules.document_control.service import next_revision

    assert next_revision("A") == "B"
    assert next_revision("B") == "C"
    assert next_revision("Y") == "Z"
    assert next_revision("Z") == "AA"
    assert next_revision("AA") == "AB"
    assert next_revision("AZ") == "BA"
    assert next_revision("ZZ") == "AAA"


def test_admin_docs_audit_action_strings_match_test_procedure(client):
    """
    SW.SLQ010 Step 9-2 lists the exact action strings expected in the audit
    trail. Verify folder creation and file upload emit
    `admin_docs.folder.create` and `admin_docs.file.upload` (dotted-namespace,
    consistent with `auth.X` and `doc.X`).
    """
    app = client.application
    engine = app.extensions["sqlalchemy_engine"]
    # The test fixture only creates document_control tables by default; we need
    # admin_docs tables for this test.
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Base.metadata.tables["admin_doc_folders"],
            Base.metadata.tables["admin_doc_files"],
        ],
    )

    _login(client)

    # Create a folder via HTTP (carries app context through test client).
    r = _post(client, "/admin/admin-docs/folders/new",
              data={"library_key": "qms_documents", "name": "Audit-Action-Test"},
              follow_redirects=False)
    assert r.status_code == 302

    # Upload a file via HTTP.
    csrf = _get_csrf(client)
    r = client.post(
        "/admin/admin-docs/documents/upload",
        data={
            "library_key": "qms_documents",
            "file": (io.BytesIO(b"hello"), "audit_action.bin"),
            "csrf_token": csrf,
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    with session_scope(app) as s:
        actions = {e.action for e in s.query(AuditEvent).all()}
        assert "admin_docs.folder.create" in actions, (
            f"Folder creation must emit admin_docs.folder.create; got actions={actions}"
        )
        assert "admin_docs.file.upload" in actions, (
            f"File upload must emit admin_docs.file.upload; got actions={actions}"
        )
        # The legacy action strings must NOT appear -- they would silently break
        # SW.SLQ010 Step 9-2 LIKE filters and orphan future audit queries.
        assert "admin_docs.folder_create" not in actions
        assert "admin_docs.document_upload" not in actions


def test_audit_event_detail_view_exposes_srs_6_2_fields(client):
    """
    SRS-6.2 / SW.SLQ010 Step 9-3: clicking an audit row must surface every
    required field (timestamp, actor email, action, entity, reason,
    metadata_json, client_ip, request_id) without database access.
    """
    app = client.application
    _login(client)
    _post(client, "/admin/modules/document-control/new",
          data={"doc_number": "QMS-D03", "title": "Detail Test", "doc_type": "QMS"},
          follow_redirects=False)

    with session_scope(app) as s:
        ev = (
            s.query(AuditEvent)
            .filter(AuditEvent.action == "doc.create")
            .order_by(AuditEvent.id.desc())
            .first()
        )
        assert ev is not None
        ev_id = ev.id

    r = client.get(f"/admin/audit/{ev_id}")
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    # Every SRS-6.2 field label must be visible on the page.
    for label in (
        "created_at",
        "action",
        "actor_user_email",
        "entity_type",
        "entity_id",
        "reason",
        "metadata_json",
        "client_ip",
        "request_id",
    ):
        assert label in body, f"Audit detail page missing field label: {label}"
    # And no edit/delete affordances (SRS-6.6 / SRS-8.x).
    assert ">Delete<" not in body
    assert ">Edit<" not in body


def test_audit_detail_404_for_unknown_event_id(client):
    """audit_detail must return 404 (not 500) for a non-existent event id."""
    _login(client)
    r = client.get("/admin/audit/999999")
    assert r.status_code == 404


def test_init_db_retires_readonly_role_and_migrates_users_to_staff(tmp_path, monkeypatch):
    """
    SW.SLQ010 Test Case 8 (Access Control, SRS-5.2): the read-only tester
    persona is now the `staff` role. The legacy `readonly` role is retired —
    seeding must not create it, and any pre-existing `readonly` user is
    auto-migrated to `staff` on the (idempotent) seed. A `staff`-role user is
    authenticated but carries no mutation permissions, so docs.create / edit /
    release / obsolete actions produce a real 403.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = f"sqlite:///{tmp_path/'init.db'}"
    monkeypatch.setenv("ADMIN_EMAIL", "admin@silqeqms.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-password-123")

    # Create only the auth-related tables needed by seed_only. Other tables in
    # Base.metadata reference Postgres-specific types (e.g., JSONB) that SQLite
    # cannot compile, so we cherry-pick.
    rbac_tables = [
        Base.metadata.tables[name]
        for name in ("users", "roles", "permissions", "user_roles", "role_permissions")
    ]
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(bind=engine, tables=rbac_tables)

    # Simulate a live account stuck on the legacy `readonly` role.
    SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with SessionLocal() as s:
        ro = Role(key="readonly", name="Read-only")
        s.add(ro)
        u = User(
            email="silqrepservice@example.com",
            password_hash=generate_password_hash("legacy-password"),
            is_active=True,
        )
        u.roles.append(ro)
        s.add(u)
        s.commit()
    engine.dispose()

    from scripts.init_db import seed_only

    seed_only(database_url=db_url)
    seed_only(database_url=db_url)  # idempotent re-run must not error/duplicate

    engine = create_engine(db_url, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with SessionLocal() as s:
        # The legacy `readonly` role is gone from seed data.
        assert s.query(Role).filter(Role.key == "readonly").one_or_none() is None
        # The pre-existing user was migrated onto `staff` (and off `readonly`).
        u = s.query(User).filter(User.email == "silqrepservice@example.com").one()
        assert {r.key for r in u.roles} == {"staff"}
        # `staff` exists and carries read access but NO mutation permission, so
        # every docs.create/edit/release/obsolete action returns a real 403.
        staff = s.query(Role).filter(Role.key == "staff").one()
        staff_keys = {p.key for p in staff.permissions}
        assert {"admin.view", "docs.view"} <= staff_keys
        for mutation in ("docs.create", "docs.edit", "docs.release", "docs.obsolete", "admin.edit"):
            assert mutation not in staff_keys, f"staff must not carry {mutation}"
    engine.dispose()


def test_document_viewer_offers_download_original(client):
    """
    SW.SLQ010 Step 3-4 / SRS-1.7: server-rendered preview of office formats
    must include a visible "Download original" link. CSV is used here because
    its renderer has no third-party dependency (it always succeeds), so this
    test reliably exercises the viewer template branch.
    """
    app = client.application
    _login(client)

    _post(client, "/admin/modules/document-control/new",
          data={"doc_number": "QMS-DV1", "title": "Viewer Test", "doc_type": "QMS"},
          follow_redirects=False)

    with session_scope(app) as s:
        d = s.query(Document).filter(Document.doc_number == "QMS-DV1").one()
        rev = s.query(DocumentRevision).filter(DocumentRevision.document_id == d.id).one()
        doc_id, rev_id = d.id, rev.id

    csrf = _get_csrf(client)
    csv_bytes = b"col1,col2\nfoo,bar\nbaz,qux\n"
    client.post(
        f"/admin/modules/document-control/{doc_id}/revisions/{rev_id}/upload",
        data={"file": (io.BytesIO(csv_bytes), "data.csv"), "csrf_token": csrf},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    with session_scope(app) as s:
        df = s.query(DocumentFile).filter(DocumentFile.revision_id == rev_id).one()
        file_id = df.id

    r = client.get(f"/admin/modules/document-control/files/{file_id}/view")
    assert r.status_code == 200
    assert r.content_type.startswith("text/html"), (
        f"CSV view should be server-rendered to HTML; got {r.content_type}"
    )
    assert b"Download original" in r.data, (
        "Document viewer did not include the 'Download original' link "
        "required by SW.SLQ010 Step 3-4"
    )


def test_admin_docs_move_file_between_libraries(client):
    """
    SRS-3.7 / SW.SLQ010 Steps 6-13, 6-14: POST move must update library_key and
    folder_id and redirect to the destination library view.
    """
    app = client.application
    engine = app.extensions["sqlalchemy_engine"]
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Base.metadata.tables["admin_doc_folders"],
            Base.metadata.tables["admin_doc_files"],
        ],
    )

    _login(client)

    _post(
        client,
        "/admin/admin-docs/folders/new",
        data={"library_key": "qms_documents", "name": "SRS Test Folder"},
        follow_redirects=False,
    )

    with session_scope(app) as s:
        folder = (
            s.query(AdminDocFolder)
            .filter(
                AdminDocFolder.library_key == "qms_documents",
                AdminDocFolder.name == "SRS Test Folder",
            )
            .one()
        )
        folder_id = folder.id

    csrf = _get_csrf(client)
    r = client.post(
        "/admin/admin-docs/documents/upload",
        data={
            "library_key": "qms_documents",
            "folder_id": str(folder_id),
            "file": (io.BytesIO(b"moved"), "move_me.pdf"),
            "csrf_token": csrf,
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    with session_scope(app) as s:
        adf = s.query(AdminDocFile).filter(AdminDocFile.filename == "move_me.pdf").one()
        doc_pk = adf.id
        assert adf.library_key == "qms_documents"
        assert adf.folder_id == folder_id

    r = _post(
        client,
        f"/admin/admin-docs/documents/{doc_pk}/move",
        data={"library_key": "ncrs", "folder_id": ""},
        follow_redirects=False,
    )
    assert r.status_code == 302
    loc = r.headers.get("Location") or ""
    assert "ncrs" in loc.lower()

    with session_scope(app) as s:
        adf = s.get(AdminDocFile, doc_pk)
        assert adf.library_key == "ncrs"
        assert adf.folder_id is None

    r = _post(
        client,
        f"/admin/admin-docs/documents/{doc_pk}/move",
        data={"library_key": "qms_documents", "folder_id": str(folder_id)},
        follow_redirects=False,
    )
    assert r.status_code == 302
    loc = r.headers.get("Location") or ""
    assert "qms-documents" in loc.lower() or "folder_id=" in loc.lower()

    with session_scope(app) as s:
        adf = s.get(AdminDocFile, doc_pk)
        assert adf.library_key == "qms_documents"
        assert adf.folder_id == folder_id


def test_admin_docs_library_page_includes_visible_move_modal_markup(client):
    """
    Regression: move dialogs were inside <tr style="display:none">, which hides
    the entire subtree in CSS — the Move overlay never appeared. Modals must be
    siblings outside the table.
    """
    app = client.application
    engine = app.extensions["sqlalchemy_engine"]
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Base.metadata.tables["admin_doc_folders"],
            Base.metadata.tables["admin_doc_files"],
        ],
    )
    _login(client)

    csrf = _get_csrf(client)
    client.post(
        "/admin/admin-docs/documents/upload",
        data={
            "library_key": "qms_documents",
            "file": (io.BytesIO(b"x"), "modal_check.pdf"),
            "csrf_token": csrf,
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    with session_scope(app) as s:
        doc_pk = s.query(AdminDocFile).filter(AdminDocFile.filename == "modal_check.pdf").one().id

    r = client.get("/admin/qms-documents")
    assert r.status_code == 200
    body = r.data.decode("utf-8")
    assert f'id="moveModal{doc_pk}"' in body
    idx_table = body.rfind("</table>")
    idx_modal = body.find(f'id="moveModal{doc_pk}"')
    assert idx_modal > idx_table > -1, "Move modal markup must follow the documents table, not sit in a hidden <tr>"
