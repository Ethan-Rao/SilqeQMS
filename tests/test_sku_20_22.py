"""20 Fr and 22 Fr catalogs pass the importer, ShipStation mapping, and distribution checks."""
from datetime import date

from app.eqms.modules.rep_traceability.parsers.pdf import _parse_item_rows
from app.eqms.modules.rep_traceability.service import validate_distribution_payload
from app.eqms.modules.shipstation_sync.parsers import canonicalize_sku, load_lot_log


def _row(item: str, ordered: str, continuation: str) -> str:
    return (
        f"{item} ClearTract 2-way Foley Catheter EA {ordered} 10.00 10.00 10/26/2026\n"
        f"{continuation}\n"
    )


def test_importer_20_fr_box_is_ten_units():
    rows = _parse_item_rows(_row("22000101003", "1.0000", "Balloon, Straight Tip, Box of 10"))
    assert rows == [{"sku": "212010SPT", "quantity": 10, "lot_number": None}]


def test_importer_22_fr_box_is_ten_units():
    rows = _parse_item_rows(_row("22200101003", "2.0000", "Box of 10"))
    assert rows == [{"sku": "212210SPT", "quantity": 20, "lot_number": None}]


def test_importer_20_fr_single_unit_code():
    rows = _parse_item_rows(_row("22000101004", "3.0000", "1 Unit"))
    assert rows == [{"sku": "212010SPT", "quantity": 3, "lot_number": None}]


def test_importer_18_fr_box_unchanged():
    rows = _parse_item_rows(_row("21800101003", "1.0000", "Box of 10"))
    assert rows == [{"sku": "211810SPT", "quantity": 10, "lot_number": None}]


def test_item_code_starting_with_22_is_not_22_fr():
    assert canonicalize_sku("22000101003") == "212010SPT"
    assert canonicalize_sku("22200101003") == "212210SPT"


def test_gtin_is_not_a_sku():
    assert canonicalize_sku("10850041415175") is None
    assert canonicalize_sku("10850041415182") is None
    assert canonicalize_sku("10850041415151") is None


def test_18_fr_name_still_maps():
    assert canonicalize_sku("ClearTract 18 Fr") == "211810SPT"
    assert canonicalize_sku("211810SPT") == "211810SPT"


def test_distribution_validation_accepts_new_catalogs():
    payload = {
        "ship_date": date(2026, 10, 26),
        "sku": "212010SPT",
        "lot_number": "SLQ-08272026",
        "quantity": 10,
        "facility_name": "University of Michigan",
    }
    assert validate_distribution_payload(payload) == []
    payload["sku"] = "212210SPT"
    payload["lot_number"] = "SLQ-08282026"
    assert validate_distribution_payload(payload) == []


def test_distribution_validation_rejects_gtin():
    payload = {
        "ship_date": date(2026, 10, 26),
        "sku": "10850041415175",
        "lot_number": "SLQ-08272026",
        "quantity": 10,
        "facility_name": "University of Michigan",
    }
    errs = validate_distribution_payload(payload)
    assert any(e.field == "sku" for e in errs)


def test_lot_log_maps_new_lots(tmp_path):
    path = tmp_path / "LotLog.csv"
    path.write_text(
        "Lot,SKU,Correct Lot Name,Manufacturing Date,Expiration Date,Total Units in Lot\n"
        "SLQ-08272026,212010SPT,SLQ-08272026,,,60\n"
        "SLQ-08282026,212210SPT,SLQ-08282026,,,60\n"
        "SLQ-05022025,211810SPT,SLQ-05022025,5/31/2025,5/31/2028,3268\n",
        encoding="utf-8",
    )
    lot_to_sku, _corrections = load_lot_log(str(path))
    assert lot_to_sku["SLQ-08272026"] == "212010SPT"
    assert lot_to_sku["SLQ-08282026"] == "212210SPT"
    assert lot_to_sku["SLQ-05022025"] == "211810SPT"
