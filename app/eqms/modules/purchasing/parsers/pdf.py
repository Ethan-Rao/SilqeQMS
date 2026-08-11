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
        ("%m/%d/%Y", r"\d{1,2}/\d{1,2}/\d{4}"),
        ("%m-%d-%Y", r"\d{1,2}-\d{1,2}-\d{4}"),
        ("%m/%d/%y", r"\d{1,2}/\d{1,2}/\d{2}"),
    ]
    for fmt, _ in candidates:
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None


def parse_purchase_order_pdf(pdf_bytes: bytes) -> dict:
    """Parse a purchase order PDF and extract key fields."""
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
    }

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            result["raw_text"] += text + "\n"

            if not result["po_number"]:
                po_match = re.search(
                    r"(?:PO|P\.O\.|Purchase\s*Order)\s*(?:#|No\.?|Number)?\s*:?\s*([A-Z0-9\-]+)",
                    text,
                    re.IGNORECASE,
                )
                if po_match:
                    cand = po_match.group(1).strip()
                    # Reject alphabetic-only tokens (e.g. vendor name near "Purchase Order")
                    if any(ch.isdigit() for ch in cand):
                        result["po_number"] = cand

            if not result["order_date"]:
                date_match = re.search(
                    r"(?:Date|Order\s*Date)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                    text,
                    re.IGNORECASE,
                )
                if date_match:
                    result["order_date"] = _parse_date(date_match.group(1))

            if not result["supplier_name"]:
                supplier_match = re.search(
                    r"(?:Vendor|Supplier|Sold\s*To)\s*:?\s*(.+)",
                    text,
                    re.IGNORECASE,
                )
                if supplier_match:
                    result["supplier_name"] = supplier_match.group(1).strip()

    return result
