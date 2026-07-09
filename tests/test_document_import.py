"""Checkpoint 5: Track-A import tooling.

Covers the Document Control multi-revision importer (create, idempotent re-run,
obsolete history, dry-run) and the admin_docs bulk-import idempotency planner.
"""
from datetime import date
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.document_control.models import Document, DocumentFile, DocumentRevision
from app.eqms.modules.document_control.service import import_document_with_revisions


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
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables_needed)
    app.config["_schema_health_ok"] = True

    with session_scope(app) as s:
        r = Role(key="admin", name="Administrator")
        u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        u.roles.append(r)
        s.add_all([r, u])

    return app


def _admin(s):
    return s.query(User).filter(User.email == "admin@example.com").one()


def _released_revisions():
    return [
        {
            "revision": "A",
            "file_bytes": b"rev-a-bytes",
            "filename": "QM.SLQ001 A.pdf",
            "content_type": "application/pdf",
            "change_summary": "Initial release",
            "effective_date": date(2020, 1, 1),
            "released": True,
        },
        {
            "revision": "B",
            "file_bytes": b"rev-b-bytes",
            "filename": "QM.SLQ001 B.pdf",
            "content_type": "application/pdf",
            "change_summary": "Updated scope",
            "effective_date": date(2023, 5, 1),
            "released": True,
        },
    ]


def test_import_creates_document_with_full_revision_history(app):
    with app.app_context(), app.test_request_context():
        with session_scope(app) as s:
            summary = import_document_with_revisions(
                s,
                doc_number="QM.SLQ001",
                title="Document Control SOP",
                doc_type="SOP",
                category="Quality Management",
                owner_user=_admin(s),
                status="Released",
                revisions=_released_revisions(),
            )

        assert summary["document_action"] == "create"
        assert summary["revisions_created"] == ["A", "B"]
        assert summary["files_added"] == ["A", "B"]
        assert summary["final_status"] == "Released"

        with session_scope(app) as s:
            d = s.query(Document).filter(Document.doc_number == "QM.SLQ001").one()
            assert d.status == "Released"
            assert d.category == "Quality Management"
            revs = {r.revision: r for r in d.revisions}
            assert set(revs) == {"A", "B"}
            # Current/active revision is the latest released one.
            assert d.current_revision_id == revs["B"].id
            # One file per revision, digests distinct.
            for label in ("A", "B"):
                files = revs[label].files
                assert len(files) == 1
                assert files[0].sha256
            # Prior revision retained + released.
            assert revs["A"].released_at is not None


def test_import_is_idempotent_on_rerun(app):
    with app.app_context(), app.test_request_context():
        with session_scope(app) as s:
            import_document_with_revisions(
                s,
                doc_number="QM.SLQ001",
                title="Document Control SOP",
                doc_type="SOP",
                owner_user=_admin(s),
                revisions=_released_revisions(),
            )

        with session_scope(app) as s:
            summary = import_document_with_revisions(
                s,
                doc_number="QM.SLQ001",
                title="Document Control SOP",
                doc_type="SOP",
                owner_user=_admin(s),
                revisions=_released_revisions(),
            )
        assert summary["document_action"] == "update"
        assert summary["revisions_created"] == []
        assert set(summary["revisions_skipped"]) == {"A", "B"}

        with session_scope(app) as s:
            d = s.query(Document).filter(Document.doc_number == "QM.SLQ001").one()
            assert len(d.revisions) == 2
            total_files = s.query(DocumentFile).count()
            assert total_files == 2


def test_import_obsolete_marks_status_and_audits(app):
    with app.app_context(), app.test_request_context():
        with session_scope(app) as s:
            import_document_with_revisions(
                s,
                doc_number="QM.SLQ099",
                title="Retired SOP",
                doc_type="SOP",
                owner_user=_admin(s),
                status="Obsolete",
                obsolete_reason="Superseded by QM.SLQ001",
                revisions=[{
                    "revision": "A",
                    "file_bytes": b"old",
                    "filename": "old.pdf",
                    "content_type": "application/pdf",
                    "released": True,
                }],
            )

        with session_scope(app) as s:
            d = s.query(Document).filter(Document.doc_number == "QM.SLQ099").one()
            assert d.status == "Obsolete"
            actions = [e.action for e in s.query(AuditEvent).all()]
            assert "doc.import" in actions
            assert "doc.obsolete" in actions


def test_import_obsolete_requires_reason(app):
    with app.app_context(), app.test_request_context():
        with session_scope(app) as s:
            with pytest.raises(ValueError):
                import_document_with_revisions(
                    s,
                    doc_number="QM.SLQ098",
                    title="Retired",
                    doc_type="SOP",
                    owner_user=_admin(s),
                    status="Obsolete",
                    revisions=[{"revision": "A", "released": True}],
                )


def test_dry_run_writes_nothing(app):
    with app.app_context(), app.test_request_context():
        with session_scope(app) as s:
            summary = import_document_with_revisions(
                s,
                doc_number="QM.SLQ001",
                title="Document Control SOP",
                doc_type="SOP",
                owner_user=_admin(s),
                revisions=_released_revisions(),
                dry_run=True,
            )
        assert summary["dry_run"] is True
        assert summary["revisions_created"] == ["A", "B"]

        with session_scope(app) as s:
            assert s.query(Document).count() == 0
            assert s.query(DocumentRevision).count() == 0
            assert s.query(DocumentFile).count() == 0
            assert s.query(AuditEvent).count() == 0


def test_admin_docs_import_planner_is_idempotent(tmp_path):
    """The bulk_import_admin_docs planner skips unsupported + already-present files."""
    import scripts.bulk_import_admin_docs as bulk

    (tmp_path / "a.pdf").write_bytes(b"a")
    (tmp_path / "b.docx").write_bytes(b"b")
    (tmp_path / "c.zip").write_bytes(b"c")  # unsupported
    sub = tmp_path / "sub"
    sub.mkdir()  # directory, ignored

    source = list(tmp_path.iterdir())

    # First pass: nothing exists yet.
    to_import, unsupported, existing = bulk.select_new_files(source, set())
    assert {p.name for p in to_import} == {"a.pdf", "b.docx"}
    assert {p.name for p in unsupported} == {"c.zip"}
    assert existing == []

    # Second pass: a.pdf already imported -> skipped, no duplicate.
    to_import2, _, existing2 = bulk.select_new_files(source, {"a.pdf"})
    assert {p.name for p in to_import2} == {"b.docx"}
    assert {p.name for p in existing2} == {"a.pdf"}
