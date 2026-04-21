from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture()
def pdf_app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'p.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path / "blobs"))
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    from app.eqms import create_app

    app = create_app()
    app.config["_schema_health_ok"] = True
    app.config["AUDITOR_PDF_BACKEND"] = "xhtml2pdf"
    with app.app_context():
        yield app


def test_html_to_pdf_bytes(pdf_app):
    from app.eqms.modules.auditor_portal import pdf_convert

    html = "<!DOCTYPE html><html><body><p>Hi</p></body></html>"
    out = pdf_convert.html_to_pdf_bytes(html)
    assert out.startswith(b"%PDF")


def test_cache_hit_skips_conversion(pdf_app, monkeypatch):
    from app.eqms.modules.auditor_portal.pdf_convert import CachedPdfStore

    store = CachedPdfStore(pdf_app.config)
    calls = {"n": 0}

    def boom(*_a, **_k):
        calls["n"] += 1
        raise RuntimeError("should not run on cache hit")

    monkeypatch.setattr("app.eqms.modules.auditor_portal.pdf_convert.xlsx_bytes_to_pdf", boom)

    store.put("pdf", "abc", b"%PDF-1 fake")
    assert store.get("pdf", "abc") == b"%PDF-1 fake"


def test_cache_key_changes_with_mtime(tmp_path, monkeypatch):
    from app.eqms.modules.auditor_portal.fs import cache_key_parts

    k1 = cache_key_parts("f.xlsx", 100, 111)
    k2 = cache_key_parts("f.xlsx", 100, 222)
    assert k1 != k2
