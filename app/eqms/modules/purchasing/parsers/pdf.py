"""Silq purchase-order PDF parser (P4-06C).

Layout rules target the Silq-generated PURCHASE ORDER template observed across
Purchasing/POs readable extracts (P.O. NUMBER / ORDER DATE / VENDOR NUMBER /
VENDOR: SHIP TO: / ITEM CODE table with /M CHRG rows). Generic keyword scans
were retired because the first hit on \"PURCHASE ORDER\" blocked \"P.O. NUMBER\".
"""
from __future__ import annotations

import io
import os
import re
from datetime import date, datetime

_MONTH_ABBREV_TO_MONTH = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

# Filename: PO <digits> <supplier token(s)> <DD><MMM><YYYY>.pdf (SILQ convention)
_FILENAME_HINT_PATTERN = re.compile(
    r"^PO\s+(\d+)\s+(.+?)\s+(\d{1,2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(\d{4})\s*\.pdf$",
    re.IGNORECASE,
)

# Silq template anchors (Task A / Task B evidence).
_PO_NUMBER_RE = re.compile(r"P\.O\.\s*NUMBER\s*:\s*([0-9][A-Z0-9\-]*)", re.IGNORECASE)
_ORDER_DATE_RE = re.compile(
    r"ORDER\s*DATE\s*:\s*("
    r"\d{1,2}/\d{1,2}/\d{2,4}"
    r"|\d{1,2}-\d{1,2}-\d{2,4}"
    r"|\d{1,2}\s+[A-Za-z]{3}\s+\d{4}"
    r"|\d{1,2}[A-Za-z]{3}\d{4}"
    r")",
    re.IGNORECASE,
)
_VENDOR_NUMBER_RE = re.compile(r"VENDOR\s*NUMBER\s*:\s*([^\n\r]+)", re.IGNORECASE)
_VENDOR_SHIP_HEADER_RE = re.compile(r"VENDOR\s*:\s*SHIP\s*TO\s*:", re.IGNORECASE)
_SHIP_TO_CUT_RE = re.compile(
    r"\s+(?:Silq\s+Technologies(?:\s+Corporation|\s+Inc\.?)?|Brian\s+McVerry|C/O\b|Hydrophilix)\b",
    re.IGNORECASE,
)
_ITEM_ROW_RE = re.compile(
    r"/M\s+CHRG\s+(.+?)\s+EACH\s+(\d+(?:\.\d+)?)\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+(\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_ITEM_SECTION_END_RE = re.compile(r"^(?:NET\s+ORDER|SALES\s+TAX|By accepting this PO)\b", re.IGNORECASE)


def parse_po_hints_from_filename(filename: str) -> dict | None:
    """
    Extract PO number, supplier token, and order date from a SILQ-style PO PDF filename.

    Example: PO 0000161 BENTEC 15JAN2025.pdf → po_number 0000161, supplier BENTEC, date 2025-01-15.

    Returns None if basename does not match. Multi-word suppliers are supported by scanning up to
    the date token at the end (extension points: tighten patterns if new filename layouts appear).
    """
    base = os.path.basename(filename or "").strip()
    if not base:
        return None
    m = _FILENAME_HINT_PATTERN.match(base)
    if not m:
        return None
    po_digits, supplier_raw, day_s, mon_abbrev, year_s = m.groups()
    month = _MONTH_ABBREV_TO_MONTH.get(mon_abbrev.upper())
    if not month:
        return None
    try:
        day = int(day_s)
        year = int(year_s)
        order_date = date(year, month, day)
    except ValueError:
        return None
    supplier_name = " ".join(supplier_raw.split())
    return {
        "po_number": po_digits,
        "order_date": order_date,
        "supplier_name": supplier_name,
    }


def merge_import_metadata(filename: str, parsed: dict) -> dict:
    """
    Combine optional filename hints with PDF extraction.

    When filename matches SILQ convention, po_number, order_date, and supplier_name come from the
    filename; line items still come from parsed PDF text. Otherwise PDF fields are used, but a
    PO value with no digits (header/footer noise like a company name) is dropped.

    Always includes ``sources`` mapping each field to ``\"filename\"``, ``\"pdf\"``, or ``None``,
    and ``filename_conforming`` for whether the basename matched the SILQ pattern.
    """
    hints = parse_po_hints_from_filename(filename)
    items = parsed.get("items") or []
    if hints:
        return {
            "po_number": hints["po_number"],
            "order_date": hints["order_date"],
            "supplier_name": (hints.get("supplier_name") or "").strip(),
            "items": items,
            "sources": {
                "po_number": "filename",
                "order_date": "filename",
                "supplier_name": "filename",
            },
            "filename_conforming": True,
        }
    po_number = (parsed.get("po_number") or "").strip()
    if po_number and not any(ch.isdigit() for ch in po_number):
        po_number = ""
    pdf_supplier = (parsed.get("supplier_name") or "").strip()
    return {
        "po_number": po_number or None,
        "order_date": parsed.get("order_date"),
        "supplier_name": pdf_supplier,
        "items": items,
        "sources": {
            "po_number": "pdf" if po_number else None,
            "order_date": "pdf" if parsed.get("order_date") else None,
            "supplier_name": "pdf" if pdf_supplier else None,
        },
        "filename_conforming": False,
    }


def _parse_date(raw_date: str) -> date | None:
    s = (raw_date or "").strip()
    if not s:
        return None
    candidates = [
        ("%m/%d/%Y", None),
        ("%m-%d-%Y", None),
        ("%m/%d/%y", None),
        ("%d %b %Y", None),
        ("%d%b%Y", None),
    ]
    for fmt, _ in candidates:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # Spaced day + month abbrev + year already covered; try collapsing spaces.
    compact = re.sub(r"\s+", "", s)
    try:
        return datetime.strptime(compact, "%d%b%Y").date()
    except Exception:
        return None


def _extract_supplier_name(text: str) -> str | None:
    """Silq template: legal name on the line under ``VENDOR: SHIP TO:``."""
    m = _VENDOR_SHIP_HEADER_RE.search(text)
    if m:
        after = text[m.end() :]
        for line in after.splitlines():
            candidate = " ".join(line.split()).strip()
            if not candidate:
                continue
            if candidate.upper().startswith("CONFIRM"):
                break
            cut = _SHIP_TO_CUT_RE.search(candidate)
            if cut:
                candidate = candidate[: cut.start()].strip(" -,\t")
            if candidate:
                return candidate
            break

    vn = _VENDOR_NUMBER_RE.search(text)
    if vn:
        token = " ".join(vn.group(1).split()).strip()
        # Stop at trailing address fragments that sometimes share the line.
        token = re.split(r"\s{2,}|\s+(?=Sunny|323\b)", token)[0].strip()
        if token:
            return token
    return None


def _extract_line_items(text: str) -> list[dict]:
    """Silq ITEM CODE table rows that start with ``/M CHRG`` (observed on all textful POs)."""
    items: list[dict] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = " ".join(lines[i].split()).strip()
        m = _ITEM_ROW_RE.search(line)
        if not m:
            i += 1
            continue
        code_or_desc = m.group(1).strip()
        try:
            qty = int(float(m.group(2)))
        except ValueError:
            qty = 1
        unit_price = m.group(3).strip()
        desc_parts: list[str] = []
        # Prefer short token as item_code when it looks like a SKU; else description-only.
        if re.fullmatch(r"[A-Z0-9][A-Z0-9\-/.]{1,31}", code_or_desc, re.IGNORECASE) and " " not in code_or_desc:
            item_code = code_or_desc
        else:
            item_code = None
            desc_parts.append(code_or_desc)

        j = i + 1
        while j < len(lines):
            nxt = " ".join(lines[j].split()).strip()
            if not nxt or _ITEM_SECTION_END_RE.match(nxt) or _ITEM_ROW_RE.search(nxt):
                break
            if nxt.upper().startswith("REFERENCE PRICING"):
                j += 1
                continue
            desc_parts.append(nxt)
            j += 1
            # One continuation line is typical on Silq POs.
            break

        items.append(
            {
                "item_code": item_code,
                "description": " ".join(desc_parts).strip() or None,
                "quantity": max(qty, 1),
                "unit_price": unit_price,
            }
        )
        i = j if j > i + 1 else i + 1
    return items


def parse_purchase_order_pdf(pdf_bytes: bytes) -> dict:
    """Parse a purchase order PDF and extract key fields (Silq template anchors)."""
    try:
        import pdfplumber  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError("pdfplumber required for PDF parsing.") from e

    result = {
        "po_number": None,
        "order_date": None,
        "supplier_name": None,
        "items": [],
        "raw_text": "",
        "page_count": 0,
    }

    if not pdf_bytes:
        return result

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        result["page_count"] = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text() or ""
            result["raw_text"] += text + "\n"

    text = result["raw_text"]
    # Image-only / empty text layer: leave fields None (Task A — no OCR).
    if len(text.strip()) < 50:
        return result

    po_match = _PO_NUMBER_RE.search(text)
    if po_match:
        cand = po_match.group(1).strip()
        if any(ch.isdigit() for ch in cand):
            result["po_number"] = cand

    date_match = _ORDER_DATE_RE.search(text)
    if date_match:
        result["order_date"] = _parse_date(date_match.group(1))

    result["supplier_name"] = _extract_supplier_name(text)
    result["items"] = _extract_line_items(text)
    return result
