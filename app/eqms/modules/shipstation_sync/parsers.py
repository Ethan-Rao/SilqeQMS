from __future__ import annotations

import csv
import re
from pathlib import Path


VALID_SKUS = ("211810SPT", "211610SPT", "211410SPT")

LOT_RX = re.compile(r"\bSLQ-?\d{5}\b", re.IGNORECASE)
LOT_LABEL_RX = re.compile(r"LOT[:\s]*([A-Z0-9\-]+)", re.IGNORECASE)


def canonicalize_sku(raw: str) -> str | None:
    s = (raw or "").upper()
    if s in VALID_SKUS:
        return s
    if "14" in s:
        return "211410SPT"
    if "16" in s:
        return "211610SPT"
    if "18" in s:
        return "211810SPT"
    return None


def normalize_lot(code: str) -> str:
    c = (code or "").strip().upper()
    if not c:
        return ""
    if c.startswith("SLQ") and not c.startswith("SLQ-"):
        # SLQ12345 -> SLQ-12345
        if c.startswith("SLQ") and len(c) > 3:
            c = "SLQ-" + c[3:].lstrip("-")
    return c


def extract_lot(text: str) -> str | None:
    """
    Lean lot heuristic:
    - Prefer explicit "LOT: <code>".
    - Otherwise, look for SLQ-12345 / SLQ12345 patterns.
    """
    t = (text or "").strip()
    if not t:
        return None
    m = LOT_LABEL_RX.search(t)
    if m:
        lot = normalize_lot(m.group(1))
        return lot or None
    m2 = LOT_RX.search(t)
    if m2:
        lot = normalize_lot(m2.group(0))
        return lot or None
    return None


def infer_units(item_name: str, quantity: int) -> int:
    name = (item_name or "").lower()
    qty = int(quantity or 0)
    if qty <= 0:
        return 0
    if "10-pack" in name or "10 pack" in name or "10pk" in name:
        return qty * 10
    return qty


def load_lot_log(path_str: str) -> dict[str, str]:
    """
    Load LotLog.csv mapping (lot -> sku). Best-effort; safe to use in prod.
    """
    p = Path(path_str)
    if not p.exists():
        return {}
    lot_to_sku: dict[str, str] = {}
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lot = normalize_lot(str(row.get("Lot") or ""))
            sku = canonicalize_sku(str(row.get("SKU") or "")) or str(row.get("SKU") or "").strip().upper()
            if not lot or not sku:
                continue
            lot_to_sku[lot] = sku
            # also store without prefix
            if lot.startswith("SLQ-"):
                lot_to_sku[lot[4:]] = sku
    return lot_to_sku

