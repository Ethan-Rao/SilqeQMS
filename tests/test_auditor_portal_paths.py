from __future__ import annotations

import os
import sys

import pytest
from werkzeug.exceptions import NotFound

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture()
def app_ctx(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'paths.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "blobs"))
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    from app.eqms import create_app
    from app.eqms.modules.auditor_portal import fs as auditor_fs

    auditor_fs.reset_auditor_root_cache_for_tests()
    root = tmp_path / "Auditor Files"
    root.mkdir(parents=True)
    (root / "Policies").mkdir()
    (root / "Policies" / "a.txt").write_text("x", encoding="utf-8")

    app = create_app()
    app.config["_schema_health_ok"] = True
    app.config["AUDITOR_FILES_ROOT"] = str(root)
    app.config["AUDITOR_PORTAL_ENABLED"] = "1"
    with app.app_context():
        yield app
    auditor_fs.reset_auditor_root_cache_for_tests()


def test_safe_resolve_clean(app_ctx):
    from app.eqms.modules.auditor_portal import fs

    p = fs._safe_resolve("Policies/a.txt")
    assert p.is_file()
    assert p.name == "a.txt"


def test_safe_resolve_traversal_404(app_ctx):
    from app.eqms.modules.auditor_portal import fs

    with pytest.raises(NotFound):
        fs._safe_resolve("..")

    with pytest.raises(NotFound):
        fs._safe_resolve("../../x")


@pytest.mark.skipif(os.name == "nt", reason="symlink escape test uses POSIX symlinks")
def test_safe_resolve_symlink_escape_404(app_ctx, tmp_path, monkeypatch):
    from app.eqms.modules.auditor_portal import fs

    root = tmp_path / "Auditor Files"
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = root / "evil"
    if not link.exists():
        link.symlink_to(outside)
    monkeypatch.setattr(fs, "_ROOT", None)
    fs.reset_auditor_root_cache_for_tests()
    monkeypatch.setitem(app_ctx.config, "AUDITOR_FILES_ROOT", str(root))

    with pytest.raises(NotFound):
        fs._safe_resolve("evil")
