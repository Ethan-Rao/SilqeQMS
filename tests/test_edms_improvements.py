import csv
import io
from datetime import timedelta

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.document_control.models import Document, DocumentFile, DocumentRevision


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


def test_session_timeout_is_8_hours(client):
    """Test 3: PERMANENT_SESSION_LIFETIME matches create_app (8h signed session)."""
    app = client.application
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(hours=8)
