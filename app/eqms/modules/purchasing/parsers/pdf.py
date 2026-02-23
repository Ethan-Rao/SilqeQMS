from __future__ import annotations

import io
import re
from datetime import date, datetime


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
                    result["po_number"] = po_match.group(1).strip()

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
