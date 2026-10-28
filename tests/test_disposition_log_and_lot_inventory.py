"""Disposition log parsing and lot inventory consumption math."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base
from app.eqms.modules.rep_traceability.service import compute_lot_inventory_snapshot
from app.eqms.modules.shipstation_sync import parsers
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


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for key in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(key, raising=False)
    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    return application


def test_undated_20fr_lot_appears_and_undated_18fr_does_not(app, monkeypatch):
    monkeypatch.setattr(parsers, "resolve_lotlog_path", lambda: "lotlog")
    monkeypatch.setattr(
        parsers,
        "load_lot_log_with_inventory",
        lambda path: (
            {
                "SLQ-08272026": "212010SPT",
                "SLQ-UNDATED18": "211810SPT",
                "SLQ-DATED18": "211810SPT",
                "SLQ-ZERO20": "212010SPT",
            },
            {},
            {
                "SLQ-08272026": 494,
                "SLQ-UNDATED18": 100,
                "SLQ-DATED18": 50,
                "SLQ-ZERO20": 0,
            },
            {},
        ),
    )
    monkeypatch.setattr(
        parsers,
        "load_lot_dates",
        lambda path: ({"SLQ-DATED18": "5/31/2025"}, {"SLQ-DATED18": "5/31/2028"}),
    )
    monkeypatch.setattr(parsers, "resolve_disposition_log_path", lambda: "disp")
    monkeypatch.setattr(parsers, "_read_disposition_log_bytes", lambda path: None)
    monkeypatch.setattr(parsers, "load_disposition_log", lambda path, lot_corrections=None: {})

    with session_scope(app) as s:
        snap = compute_lot_inventory_snapshot(s)

    lots = {row["lot"]: row for row in snap["active_lot_tracking"]}
    assert "SLQ-08272026" in lots
    assert lots["SLQ-08272026"]["sku"] == "212010SPT"
    assert lots["SLQ-08272026"]["total_produced"] == 494
    assert lots["SLQ-08272026"]["remaining"] == 494
    assert not lots["SLQ-08272026"]["mfg_date"]
    assert not lots["SLQ-08272026"]["exp_date"]
    assert "SLQ-UNDATED18" not in lots
    assert "SLQ-ZERO20" not in lots
    assert "SLQ-DATED18" in lots


def test_parse_disposition_log_empty_workbook_returns_empty():
    from io import BytesIO

    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "Lot", "SKU", "Number of Units Dispositioned"])
    buf = BytesIO()
    wb.save(buf)
    assert parse_disposition_log_bytes(buf.getvalue()) == {}
