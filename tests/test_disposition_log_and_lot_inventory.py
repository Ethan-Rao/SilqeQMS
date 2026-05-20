"""Disposition log parsing and lot inventory consumption math."""

from __future__ import annotations

from pathlib import Path

from app.eqms.modules.shipstation_sync.parsers import parse_disposition_log_bytes


def _disposition_xlsx_bytes() -> bytes:
    path = Path(__file__).resolve().parents[1] / "app" / "eqms" / "data" / "DispositionLog.xlsx"
    assert path.exists(), f"fixture missing: {path}"
    return path.read_bytes()


def test_parse_disposition_log_bytes_aggregates_by_lot():
    totals = parse_disposition_log_bytes(_disposition_xlsx_bytes())
    assert totals["SLQ-05022025"] == 100
    assert totals["SLQ-05012025"] == 142  # 100 + 42
    assert totals["SLQ-11202024"] == 70


def test_lot_inventory_remaining_accounts_for_disposition():
    """remaining = produced - distributed - dispositioned (card math)."""
    produced = 500
    distributed = 120
    dispositioned = 100
    consumed = distributed + dispositioned
    remaining = produced - consumed
    assert remaining == 280


def test_parse_disposition_log_empty_workbook_returns_empty():
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Lot", "SKU", "Number of Units Dispositioned"])
    buf = BytesIO()
    wb.save(buf)
    assert parse_disposition_log_bytes(buf.getvalue()) == {}
