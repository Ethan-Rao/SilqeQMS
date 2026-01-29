from __future__ import annotations

import csv
import re
from pathlib import Path


VALID_SKUS = ("211810SPT", "211610SPT", "211410SPT")
EXCLUDED_SKUS = ("SLQ-4007",)  # IFUs and non-device items

# Regex patterns for lot extraction from text
LOT_RX = re.compile(r"\bSLQ-?\d+\b", re.IGNORECASE)
LOT_LABEL_RX = re.compile(r"LOT[:\s]*([A-Z0-9\-]+)", re.IGNORECASE)
# Bare numeric lot pattern (e.g., "05012025" in notes)
BARE_LOT_RX = re.compile(r"\b(\d{6,12})\b")
# Multi-SKU lot pattern: "SKU: 21600101003 LOT: SLQ-05012025"
SKU_LOT_PAIR_RX = re.compile(r"SKU[:\s]*(\d+)[^A-Z0-9]*LOT[:\s]*([A-Z0-9\-]+)", re.IGNORECASE)


def canonicalize_sku(raw: str) -> str | None:
    s = (raw or "").upper().strip()
    # Exclude IFUs and non-device items
    if s in EXCLUDED_SKUS or s.upper() in [x.upper() for x in EXCLUDED_SKUS]:
        return None
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
    """
    Normalize lot to always have SLQ- prefix (legacy behavior).
    - Uppercase + strip
    - SLQ123 -> SLQ-123
    - 05012025 -> SLQ-05012025
    """
    c = (code or "").strip().upper()
    if not c:
        return ""
    # Already has SLQ- prefix
    if c.startswith("SLQ-"):
        return c
    # Has SLQ but no dash (SLQ12345 -> SLQ-12345)
    if c.startswith("SLQ"):
        return "SLQ-" + c[3:].lstrip("-")
    # Bare number or other code -> prefix with SLQ-
    return "SLQ-" + c


def extract_lot(text: str) -> str | None:
    """
    Lean lot heuristic:
    - Prefer explicit "LOT: <code>".
    - Otherwise, look for SLQ-12345 / SLQ12345 patterns.
    - Fall back to bare numeric codes (6-12 digits).
    """
    t = (text or "").strip()
    if not t:
        return None
    # 1) Explicit LOT: label
    m = LOT_LABEL_RX.search(t)
    if m:
        lot = normalize_lot(m.group(1))
        return lot or None
    # 2) SLQ pattern
    m2 = LOT_RX.search(t)
    if m2:
        lot = normalize_lot(m2.group(0))
        return lot or None
    # 3) Bare numeric (e.g., "05012025")
    m3 = BARE_LOT_RX.search(t)
    if m3:
        lot = normalize_lot(m3.group(1))
        return lot or None
    return None


def extract_sku_lot_pairs(text: str) -> dict[str, str]:
    """
    Extract multiple SKU→LOT pairs from internal notes.
    
    Example input: "SKU: 21600101003 lot: SLQ-05012025 SKU: 21800101003 LOT: SLQ-05022025"
    Returns: {"211610SPT": "SLQ-05012025", "211810SPT": "SLQ-05022025"}
    """
    t = (text or "").strip()
    if not t:
        return {}
    
    pairs: dict[str, str] = {}
    for match in SKU_LOT_PAIR_RX.finditer(t):
        raw_sku = match.group(1)
        raw_lot = match.group(2)
        canonical_sku = canonicalize_sku(raw_sku)
        if canonical_sku:
            normalized_lot = normalize_lot(raw_lot)
            if normalized_lot:
                pairs[canonical_sku] = normalized_lot
    
    return pairs


def infer_units(item_name: str, quantity: int) -> int:
    name = (item_name or "").lower()
    qty = int(quantity or 0)
    if qty <= 0:
        return 0
    if "10-pack" in name or "10 pack" in name or "10pk" in name:
        return qty * 10
    return qty


def load_lot_log(path_str: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Load LotLog.csv mapping:
    - lot_to_sku: {lot_variant -> canonical_sku}
    - lot_corrections: {raw_lot -> correct_lot} (from "Correct Lot Name" column)
    
    Stores multiple variants for reliable lookup:
    - Normalized lot (SLQ-05012025)
    - Without prefix (05012025)
    - Raw uppercase
    """
    p = Path(path_str.replace("\\", "/"))  # Handle Windows paths
    if not p.exists():
        return {}, {}
    
    lot_to_sku: dict[str, str] = {}
    lot_corrections: dict[str, str] = {}
    
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_lot = (str(row.get("Lot") or "")).strip().upper()
            correct_lot_name = (str(row.get("Correct Lot Name") or "")).strip().upper()
            sku_raw = str(row.get("SKU") or "")
            sku = canonicalize_sku(sku_raw)
            
            if not raw_lot or not sku:
                continue
            
            # Determine the canonical lot (prefer "Correct Lot Name" if present)
            if correct_lot_name:
                canonical_lot = normalize_lot(correct_lot_name)
                # Store correction mapping
                norm_raw = normalize_lot(raw_lot)
                if norm_raw != canonical_lot:
                    lot_corrections[norm_raw] = canonical_lot
                    lot_corrections[raw_lot] = canonical_lot
            else:
                canonical_lot = normalize_lot(raw_lot)
            
            # Store multiple variants -> SKU
            lot_to_sku[canonical_lot] = sku
            lot_to_sku[raw_lot] = sku
            lot_to_sku[normalize_lot(raw_lot)] = sku
            
            # Store without SLQ- prefix
            if canonical_lot.startswith("SLQ-"):
                lot_to_sku[canonical_lot[4:]] = sku
            if raw_lot.startswith("SLQ-"):
                lot_to_sku[raw_lot[4:]] = sku
    
    return lot_to_sku, lot_corrections


def load_lot_log_with_inventory(path_str: str) -> tuple[dict[str, str], dict[str, str], dict[str, int], dict[str, int]]:
    """
    Load LotLog.csv with inventory data:
    - lot_to_sku: {lot_variant -> canonical_sku}
    - lot_corrections: {raw_lot -> correct_lot}
    - lot_inventory: {canonical_lot -> total_units_produced}
    - lot_years: {canonical_lot -> manufacturing_year}
    """
    p = Path(path_str.replace("\\", "/"))  # Handle Windows paths
    if not p.exists():
        return {}, {}, {}, {}

    lot_to_sku: dict[str, str] = {}
    lot_corrections: dict[str, str] = {}
    lot_inventory: dict[str, int] = {}
    lot_years: dict[str, int] = {}

    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_lot = (str(row.get("Lot") or "")).strip().upper()
            correct_lot_name = (str(row.get("Correct Lot Name") or "")).strip().upper()
            sku_raw = str(row.get("SKU") or "")
            sku = canonicalize_sku(sku_raw)

            if not raw_lot or not sku:
                continue

            # Determine canonical lot (prefer "Correct Lot Name")
            if correct_lot_name:
                canonical_lot = normalize_lot(correct_lot_name)
                norm_raw = normalize_lot(raw_lot)
                if norm_raw != canonical_lot:
                    lot_corrections[norm_raw] = canonical_lot
                    lot_corrections[raw_lot] = canonical_lot
            else:
                canonical_lot = normalize_lot(raw_lot)

            # Store inventory (Total Units in Lot)
            try:
                total_units = int(float(row.get("Total Units in Lot") or 0))
            except Exception:
                total_units = 0
            if canonical_lot:
                lot_inventory[canonical_lot] = total_units

            # Manufacturing year (from Lot Log or lot string)
            mfg_date = (str(row.get("Manufacturing Date") or "")).strip()
            year_val = None
            if mfg_date:
                try:
                    year_val = int(mfg_date[:4])
                except Exception:
                    year_val = None
            if not year_val:
                m = re.search(r"(20\\d{2})", canonical_lot)
                if m:
                    try:
                        year_val = int(m.group(1))
                    except Exception:
                        year_val = None
            if year_val:
                lot_years[canonical_lot] = year_val

            # Store multiple variants -> SKU
            lot_to_sku[canonical_lot] = sku
            lot_to_sku[raw_lot] = sku
            lot_to_sku[normalize_lot(raw_lot)] = sku
            if canonical_lot.startswith("SLQ-"):
                lot_to_sku[canonical_lot[4:]] = sku
            if raw_lot.startswith("SLQ-"):
                lot_to_sku[raw_lot[4:]] = sku

    return lot_to_sku, lot_corrections, lot_inventory, lot_years

