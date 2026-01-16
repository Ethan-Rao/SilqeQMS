from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

from app.eqms.modules.rep_traceability.utils import (
    VALID_SKUS,
    normalize_source,
    normalize_text,
    parse_ship_date,
    validate_lot_number,
    validate_quantity,
    validate_sku,
)


@dataclass(frozen=True)
class CsvRowError:
    row_number: int
    message: str


def _get(row: dict[str, str], *names: str) -> str:
    for n in names:
        if n in row and row[n] is not None:
            return str(row[n]).strip()
    return ""


def parse_distribution_csv(file_bytes: bytes) -> tuple[list[dict], list[CsvRowError]]:
    """
    Parse a distribution log CSV export.

    Expected headers (case sensitive, but we support a few common variants):
    - Ship Date
    - Order Number
    - Facility Name
    - SKU
    - Lot (or Lot Number)
    - Quantity

    Optional headers:
    - Rep
    - Source
    - Address, City, State, Zip

    Returns:
      (rows, errors)
    Where each row is a dict suitable for service.create_distribution_entry().
    """
    text = file_bytes.decode("utf-8-sig", errors="replace")
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")

    rows: list[dict] = []
    errors: list[CsvRowError] = []

    for idx, raw in enumerate(reader, start=2):  # 1 = header
        # Skip fully empty rows
        if not raw or all((v or "").strip() == "" for v in raw.values()):
            continue

        ship_date_s = _get(raw, "Ship Date", "ShipDate", "ship_date")
        order_number = _get(raw, "Order Number", "Order #", "Order", "order_number")
        facility_name = _get(raw, "Facility Name", "Facility", "facility_name")
        sku = _get(raw, "SKU", "sku")
        lot = _get(raw, "Lot", "Lot Number", "lot_number")
        qty_s = _get(raw, "Quantity", "Qty", "quantity")
        source = _get(raw, "Source", "source")

        try:
            ship_date: date = parse_ship_date(ship_date_s)
        except Exception as e:
            errors.append(CsvRowError(idx, f"Invalid Ship Date: {e}"))
            continue

        sku = normalize_text(sku)
        if sku and not validate_sku(sku):
            errors.append(CsvRowError(idx, f"Invalid SKU {sku!r}. Must be one of: {', '.join(VALID_SKUS)}"))
            continue

        lot = normalize_text(lot)
        if lot and not validate_lot_number(lot):
            errors.append(CsvRowError(idx, "Invalid Lot. Expected format SLQ-##### (e.g. SLQ-12345)."))
            continue

        try:
            quantity = int((qty_s or "").strip())
        except Exception:
            errors.append(CsvRowError(idx, "Invalid Quantity. Must be an integer."))
            continue
        if not validate_quantity(quantity):
            errors.append(CsvRowError(idx, "Invalid Quantity. Must be a positive integer."))
            continue

        d = {
            "ship_date": ship_date,
            "order_number": normalize_text(order_number),
            "facility_name": normalize_text(facility_name),
            "sku": sku,
            "lot_number": lot,
            "quantity": quantity,
            "source": normalize_source(source) or "csv_import",
            "city": normalize_text(_get(raw, "City", "city")),
            "state": normalize_text(_get(raw, "State", "state")),
            "zip": normalize_text(_get(raw, "Zip", "ZIP", "zip")),
            "address1": normalize_text(_get(raw, "Address", "Address1", "address1")),
            "tracking_number": normalize_text(_get(raw, "Tracking Number", "Tracking", "tracking_number")),
            "rep_name": normalize_text(_get(raw, "Rep", "rep")),
            "customer_name": normalize_text(_get(raw, "Customer", "customer")),
        }

        # Required fields check
        if not d["facility_name"]:
            errors.append(CsvRowError(idx, "Facility Name is required."))
            continue
        if not d["sku"]:
            errors.append(CsvRowError(idx, "SKU is required."))
            continue
        if not d["lot_number"]:
            errors.append(CsvRowError(idx, "Lot is required."))
            continue
        if not d["order_number"]:
            # We'll allow blank and autogenerate, but keep it explicit.
            d["order_number"] = ""

        rows.append(d)

    return rows, errors

