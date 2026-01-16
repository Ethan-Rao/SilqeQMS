import io

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

    app = create_app()
    engine = app.extensions["sqlalchemy_engine"]
    Base.metadata.create_all(bind=engine)

    with session_scope(app) as s:
        perms = [
            Permission(key="admin.view", name="Admin: view shell"),
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


def test_document_control_vertical_slice_creates_releases_downloads_and_audits(client):
    # Login
    r = client.post("/auth/login", data={"email": "admin@example.com", "password": "pw"}, follow_redirects=False)
    assert r.status_code == 302

    # Create document (Draft) -> rev A
    r = client.post(
        "/admin/modules/document-control/new",
        data={"doc_number": "QMS-001", "title": "Quality Manual", "doc_type": "QMS"},
        follow_redirects=False,
    )
    assert r.status_code == 302

    # Fetch created ids from DB
    app = client.application
    with session_scope(app) as s:
        d = s.query(Document).filter(Document.doc_number == "QMS-001").one()
        rev = s.query(DocumentRevision).filter(DocumentRevision.document_id == d.id).one()
        assert d.status == "Draft"
        assert d.current_revision_id == rev.id
        assert rev.revision == "A"

    # Upload file to draft revision
    r = client.post(
        f"/admin/modules/document-control/{d.id}/revisions/{rev.id}/upload",
        data={"file": (io.BytesIO(b"hello world"), "qms-001.pdf")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    with session_scope(app) as s:
        df = s.query(DocumentFile).filter(DocumentFile.revision_id == rev.id).one()
        assert df.filename == "qms-001.pdf"

    # Release revision
    r = client.post(
        f"/admin/modules/document-control/{d.id}/revisions/{rev.id}/release",
        data={"reason": "Initial release", "change_summary": "Initial release", "effective_date": "2026-01-15"},
        follow_redirects=False,
    )
    assert r.status_code == 302

    with session_scope(app) as s:
        d2 = s.get(Document, d.id)
        rev2 = s.get(DocumentRevision, rev.id)
        assert d2.status == "Released"
        assert rev2.released_at is not None

    # Download file (logs audit)
    r = client.get(f"/admin/modules/document-control/files/{df.id}/download")
    assert r.status_code == 200
    assert r.data == b"hello world"

    # Audit trail contains expected actions
    with session_scope(app) as s:
        actions = [e.action for e in s.query(AuditEvent).order_by(AuditEvent.id.asc()).all()]
        assert "doc.create" in actions
        assert "doc.upload" in actions
        assert "doc.release" in actions
        assert "doc.download" in actions

