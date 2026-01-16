from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Mapping

from werkzeug.utils import secure_filename

VALID_SKUS = ("211810SPT", "211610SPT", "211410SPT")
VALID_SOURCES = ("shipstation", "manual", "csv_import", "pdf_import")

LOT_RE = re.compile(r"^SLQ-\d{5}$")


def normalize_text(s: str | None) -> str:
    return (s or "").strip()


def normalize_source(s: str | None) -> str:
    v = normalize_text(s).lower()
    if not v:
        return ""
    if v == "csv":
        return "csv_import"
    if v == "pdf":
        return "pdf_import"
    if v in ("shipstation", "manual", "csv_import", "pdf_import"):
        return v
    if v == "all":
        return "all"
    return v


def validate_sku(sku: str) -> bool:
    return normalize_text(sku) in VALID_SKUS


def validate_lot_number(lot: str) -> bool:
    return bool(LOT_RE.fullmatch(normalize_text(lot)))


def validate_quantity(qty: int) -> bool:
    return isinstance(qty, int) and qty > 0


def parse_ship_date(s: str) -> date:
    s = normalize_text(s)
    if not s:
        raise ValueError("Ship Date is required (YYYY-MM-DD).")
    return date.fromisoformat(s)


def validate_ship_date(d: date) -> bool:
    return d <= date.today()


def month_bounds(month: str) -> tuple[date, date]:
    m = normalize_text(month)
    if not re.fullmatch(r"\d{4}-\d{2}", m):
        raise ValueError("month must be YYYY-MM")
    y = int(m[:4])
    mo = int(m[5:7])
    start = date(y, mo, 1)
    if mo == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, mo + 1, 1)
    return start, end


def json_dumps_sorted(d: dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def filters_hash(filters: dict[str, Any]) -> str:
    return sha256_bytes(json_dumps_sorted(filters).encode("utf-8"))[:12]


def sanitize_subject_for_filename(subject: str | None) -> str:
    s = secure_filename(subject or "")
    return (s or "approval")[:100]


def parse_int(s: str | None) -> int | None:
    s = normalize_text(s)
    if not s:
        return None
    try:
        return int(s)
    except Exception:
        return None


def parse_page(args: Mapping[str, str | None]) -> int:
    p = parse_int(args.get("page"))
    return p if p and p > 0 else 1


def parse_distribution_filters(args: Mapping[str, str | None]) -> dict[str, Any]:
    """
    Distribution Log list filters (UI map):
    - date_from, date_to, source, rep_id, sku, customer/facility text filter.
    """
    return {
        "date_from": normalize_text(args.get("date_from")),
        "date_to": normalize_text(args.get("date_to")),
        "source": normalize_source(args.get("source")) or "all",
        "rep_id": parse_int(args.get("rep_id")),
        "sku": normalize_text(args.get("sku")) or "all",
        "q": normalize_text(args.get("q")),
        "page": parse_page(args),
    }


def parse_tracing_filters(form: Mapping[str, str | None]) -> dict[str, Any]:
    return {
        "month": normalize_text(form.get("month")),
        "rep_id": parse_int(form.get("rep_id")),
        "source": normalize_source(form.get("source")) or "all",
        "sku": normalize_text(form.get("sku")) or "all",
        "q": normalize_text(form.get("q")),
    }

