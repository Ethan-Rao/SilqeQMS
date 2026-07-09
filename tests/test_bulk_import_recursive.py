"""
Phase 3 Prompt 11 — recursive bulk-import behavior.

Verifies that `bulk_import_admin_docs.run_import`:
- treats --folder as a nested path (creates each level),
- with recursive=True mirrors the source subfolder tree under the target folder,
- imports each directory's DIRECT files into the matching folder,
- skips unsupported extensions,
- is idempotent (re-run uploads nothing),
- and respects dry-run (no DB writes).

Uses the local storage backend, so no S3 call is made.
"""
import importlib.util
import sys
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Role, User
from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder

ROOT = Path(__file__).resolve().parents[1]


def _load_importer():
    """Load scripts/bulk_import_admin_docs.py as a module (not on sys.path)."""
    spec = importlib.util.spec_from_file_location(
        "bulk_import_admin_docs", ROOT / "scripts" / "bulk_import_admin_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "storage"))
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    engine = application.extensions["sqlalchemy_engine"]
    tables = [
        Base.metadata.tables[t]
        for t in (
            "users", "roles", "permissions", "user_roles", "role_permissions",
            "audit_events", "admin_doc_folders", "admin_doc_files",
        )
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        admin_role = Role(key="admin", name="Administrator")
        admin_user = User(
            email="admin@example.com",
            password_hash=generate_password_hash("pw"),
            is_active=True,
        )
        admin_user.roles.append(admin_role)
        s.add_all([admin_role, admin_user])

    return application


@pytest.fixture()
def source_tree(tmp_path):
    """
    src/
      top.txt
      sub1/
        b.txt
        sub1a/
          c.txt
      sub2/
        d.pdf
        ignore.zzz   (unsupported)
    """
    src = tmp_path / "src"
    (src / "sub1" / "sub1a").mkdir(parents=True)
    (src / "sub2").mkdir(parents=True)
    (src / "top.txt").write_text("top", encoding="utf-8")
    (src / "sub1" / "b.txt").write_text("b", encoding="utf-8")
    (src / "sub1" / "sub1a" / "c.txt").write_text("c", encoding="utf-8")
    (src / "sub2" / "d.pdf").write_bytes(b"%PDF-1.4 d")
    (src / "sub2" / "ignore.zzz").write_text("nope", encoding="utf-8")
    return src


def _folder_by_path(s, library_key, path_parts):
    parent_id = None
    folder = None
    for name in path_parts:
        folder = (
            s.query(AdminDocFolder)
            .filter_by(library_key=library_key, parent_id=parent_id, name=name)
            .first()
        )
        assert folder is not None, f"missing folder {name} under {path_parts}"
        parent_id = folder.id
    return folder


def _admin(s):
    return s.query(User).join(User.roles).filter_by(key="admin").first()


def test_recursive_import_mirrors_tree(app, source_tree):
    mod = _load_importer()
    with app.app_context():
        with session_scope(app) as s:
            summary = mod.run_import(
                s,
                library_key="qms_documents",
                folder_path="Records/Root",
                source_dir=source_tree,
                admin_user=_admin(s),
                recursive=True,
                dry_run=False,
            )
        assert summary["errors"] == []
        # top.txt + b.txt + c.txt + d.pdf = 4 supported; ignore.zzz skipped.
        assert summary["uploaded"] == 4
        assert summary["skipped_unsupported"] == 1

        with session_scope(app) as s:
            root = _folder_by_path(s, "qms_documents", ["Records", "Root"])
            sub1 = _folder_by_path(s, "qms_documents", ["Records", "Root", "sub1"])
            sub1a = _folder_by_path(s, "qms_documents", ["Records", "Root", "sub1", "sub1a"])
            sub2 = _folder_by_path(s, "qms_documents", ["Records", "Root", "sub2"])

            def _names(folder):
                return {
                    f.filename
                    for f in s.query(AdminDocFile)
                    .filter_by(library_key="qms_documents", folder_id=folder.id)
                    .all()
                }

            assert _names(root) == {"top.txt"}
            assert _names(sub1) == {"b.txt"}
            assert _names(sub1a) == {"c.txt"}
            assert _names(sub2) == {"d.pdf"}


def test_recursive_import_is_idempotent(app, source_tree):
    mod = _load_importer()
    with app.app_context():
        for _ in range(2):
            with session_scope(app) as s:
                summary = mod.run_import(
                    s,
                    library_key="qms_documents",
                    folder_path="Records/Root",
                    source_dir=source_tree,
                    admin_user=_admin(s),
                    recursive=True,
                    dry_run=False,
                )
        # Second pass uploads nothing; everything already present.
        assert summary["uploaded"] == 0
        assert summary["skipped_existing"] == 4

        with session_scope(app) as s:
            total_files = s.query(AdminDocFile).count()
            assert total_files == 4


def test_reuses_preexisting_folder_no_duplicate(app, source_tree):
    """If the target folder path already exists (e.g. created by a prior run or
    a separate command), re-running must reuse it, not create a duplicate."""
    mod = _load_importer()
    with app.app_context():
        # Pre-create the "Records/Root" path via a separate call, then import.
        from app.eqms.modules.admin_docs.service import create_folder
        with session_scope(app) as s:
            admin = _admin(s)
            records = create_folder(s, "qms_documents", "Records", admin)
            s.flush()
            create_folder(s, "qms_documents", "Root", admin, parent=records)

        with session_scope(app) as s:
            mod.run_import(
                s,
                library_key="qms_documents",
                folder_path="Records/Root",
                source_dir=source_tree,
                admin_user=_admin(s),
                recursive=True,
                dry_run=False,
            )

        with session_scope(app) as s:
            # Exactly one "Records" and one "Root" — no duplicates.
            assert s.query(AdminDocFolder).filter_by(
                library_key="qms_documents", parent_id=None, name="Records"
            ).count() == 1
            root = _folder_by_path(s, "qms_documents", ["Records", "Root"])
            assert s.query(AdminDocFolder).filter_by(
                library_key="qms_documents", parent_id=root.id, name="sub1"
            ).count() == 1


def test_dry_run_writes_nothing(app, source_tree):
    mod = _load_importer()
    with app.app_context():
        with session_scope(app) as s:
            summary = mod.run_import(
                s,
                library_key="qms_documents",
                folder_path="Records/Root",
                source_dir=source_tree,
                admin_user=_admin(s),
                recursive=True,
                dry_run=True,
            )
        assert summary["uploaded"] == 4  # would-upload count
        with session_scope(app) as s:
            assert s.query(AdminDocFile).count() == 0
            assert s.query(AdminDocFolder).count() == 0
