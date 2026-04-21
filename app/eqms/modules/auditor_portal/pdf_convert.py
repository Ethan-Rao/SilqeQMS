from __future__ import annotations

import hashlib
import io
import logging
from typing import Any

from flask import current_app

from app.eqms.document_viewer import sanitize_viewer_html
from app.eqms.storage import StorageError, storage_from_config

logger = logging.getLogger(__name__)

_EXCEL_ROW_LIMIT = 2000


def render_excel_to_html(file_bytes: bytes) -> str | None:
    """Return standalone HTML (body content suitable for wrapping) for Excel files."""
    try:
        import openpyxl  # type: ignore
    except ImportError:
        return None
    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception:
        return None
    parts: list[str] = []
    try:
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows_raw: list[list[str]] = []
            for row in ws.iter_rows(values_only=True):
                rows_raw.append([str(c) if c is not None else "" for c in row])
            total = max(0, len(rows_raw) - 1)
            truncated = False
            if len(rows_raw) > _EXCEL_ROW_LIMIT + 1:
                rows_raw = rows_raw[: _EXCEL_ROW_LIMIT + 1]
                truncated = True
            if not rows_raw:
                continue
            banner = ""
            if truncated:
                banner = (
                    f'<div class="banner">Showing first {_EXCEL_ROW_LIMIT} of {total} data rows '
                    f"on sheet {_esc(sheet_name)}.</div>"
                )
            thead = "<thead><tr>" + "".join(f"<th>{_esc(c)}</th>" for c in rows_raw[0]) + "</tr></thead>"
            tbody_rows = rows_raw[1:] if len(rows_raw) > 1 else []
            tbody = "<tbody>" + "".join(
                "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in r) + "</tr>" for r in tbody_rows
            ) + "</tbody>"
            parts.append(
                f'<section class="sheet" style="page-break-after:always;">'
                f"<h2>{_esc(sheet_name)}</h2>{banner}"
                f'<table border="1" cellpadding="4" cellspacing="0">{thead}{tbody}</table></section>'
            )
        wb.close()
    except Exception:
        return None
    if not parts:
        return None
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        "<style>body{font-family:sans-serif;font-size:10pt;} table{border-collapse:collapse;width:100%;}"
        ".banner{background:#fee;padding:8px;margin:8px 0;} h2{font-size:12pt;}</style></head><body>"
        + "".join(parts)
        + "</body></html>"
    )


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def html_to_pdf_bytes(html: str, base_url: str | None = None) -> bytes:
    backend = (current_app.config.get("AUDITOR_PDF_BACKEND") or "xhtml2pdf").strip().lower()
    if backend == "weasyprint":
        try:
            from weasyprint import HTML  # type: ignore

            return HTML(string=html, base_url=base_url).write_pdf()
        except Exception as e:
            logger.warning("WeasyPrint failed (%s); falling back to xhtml2pdf", e)
    buf = io.BytesIO()
    try:
        from xhtml2pdf import pisa  # type: ignore
    except ImportError as e:
        raise RuntimeError("xhtml2pdf not installed") from e
    pisa.CreatePDF(io.StringIO(html), dest=buf, encoding="utf-8")
    return buf.getvalue()


def docx_bytes_to_pdf(file_bytes: bytes) -> bytes:
    try:
        import mammoth  # type: ignore
    except ImportError as e:
        raise RuntimeError("mammoth not installed") from e
    result = mammoth.convert_to_html(io.BytesIO(file_bytes))
    body = sanitize_viewer_html(result.value)
    shell = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'/>"
        "<style>body{font-family:sans-serif;font-size:11pt;} table{border-collapse:collapse;}"
        "td,th{border:1px solid #ccc;padding:4px;}</style></head><body>"
        f"{body}</body></html>"
    )
    return html_to_pdf_bytes(shell)


def xlsx_bytes_to_pdf(file_bytes: bytes) -> bytes:
    html = render_excel_to_html(file_bytes)
    if not html:
        raise RuntimeError("excel html failed")
    return html_to_pdf_bytes(html)


class CachedPdfStore:
    def __init__(self, config: dict[str, Any]) -> None:
        self._storage = storage_from_config(config)

    def get(self, namespace: str, cache_key: str) -> bytes | None:
        key = f"auditor-cache/{namespace}/{cache_key}.pdf"
        try:
            if hasattr(self._storage, "exists") and not self._storage.exists(key):
                return None
            return self._storage.get_bytes(key)
        except Exception as e:
            logger.debug("auditor cache miss/read error: %s", e)
            return None

    def put(self, namespace: str, cache_key: str, data: bytes) -> None:
        key = f"auditor-cache/{namespace}/{cache_key}.pdf"
        try:
            self._storage.put_bytes(key, data, content_type="application/pdf")
        except StorageError:
            logger.warning("auditor cache write failed for key=%s", key)
        except Exception as e:
            logger.warning("auditor cache write failed: %s", e)
