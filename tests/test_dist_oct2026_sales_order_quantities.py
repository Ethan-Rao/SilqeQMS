"""Regression tests for the Oct-2026 distribution reconciliation parser fixes.

Two defects corrupted recorded quantities across the sales order history:

1. The item-row regex matched a digit inside the item *description* ("2-way")
   instead of the ORDERED column, so nearly every order was stored as 2 units.
2. The ORDERED column counts shelf cartons for box SKUs and individual
   catheters for single-unit SKUs, but the packaging multiplier was never
   applied, so a 7-box order read as 7 catheters instead of 70.

The UNIT column always reads "EA" in these documents and must not be used to
infer packaging; only the continuation line ("Box of 10" / "1 Unit") and the
item code suffix are reliable.
"""
from app.eqms.modules.rep_traceability.parsers.pdf import (
    _pack_size,
    _parse_item_rows,
)

BOX_OF_TEN_ROW = (
    "21800101003 ClearTract 2-way Foley Catheter, 18 Fr, 10 ml EA 7.0000 345.00 "
    "2,415.00 8/26/2026\n"
    "Balloon,Straight Tip, Box of 10\n"
)

SINGLE_UNIT_ROW = (
    "21600101004 ClearTract 2-way Foley Catheter, 16 Fr, 10 ml EA 30.0000 22.50 "
    "675.00 9/4/2026\n"
    "Balloon,Straight Tip, 1 Unit\n"
)

MIXED_ORDER = (
    "21400101003 ClearTract 2-way Foley Catheter, 14 Fr, 10 ml EA 2.0000 295.00 "
    "590.00 9/21/2026\n"
    "Balloon,Straight Tip, Box of 10\n"
    "21600101004 ClearTract 2-way Foley Catheter, 16 Fr, 10 ml EA 3.0000 22.50 "
    "67.50 9/21/2026\n"
    "Balloon,Straight Tip, 1 Unit\n"
)


def test_box_of_ten_multiplies_ordered_column():
    rows = _parse_item_rows(BOX_OF_TEN_ROW)
    assert len(rows) == 1
    assert rows[0]["sku"] == "211810SPT"
    # 7 boxes of 10, not the "2" in "2-way" and not 7 loose catheters.
    assert rows[0]["quantity"] == 70


def test_single_unit_row_is_not_multiplied():
    rows = _parse_item_rows(SINGLE_UNIT_ROW)
    assert len(rows) == 1
    assert rows[0]["sku"] == "211610SPT"
    assert rows[0]["quantity"] == 30


def test_quantity_never_comes_from_the_description():
    """Every ClearTract description contains "2-way"; none may yield 2."""
    for text in (BOX_OF_TEN_ROW, SINGLE_UNIT_ROW):
        rows = _parse_item_rows(text)
        assert rows and all(r["quantity"] != 2 for r in rows), text


def test_mixed_order_keeps_each_line_in_its_own_packaging():
    rows = _parse_item_rows(MIXED_ORDER)
    assert {(r["sku"], r["quantity"]) for r in rows} == {
        ("211410SPT", 20),
        ("211610SPT", 3),
    }


def test_pack_size_prefers_the_continuation_line_over_the_item_code():
    # Box code, but the row is explicitly a single unit.
    assert _pack_size("Balloon,Straight Tip, 1 Unit", "21800101003") == 1
    # Single-unit code, but the row is explicitly a carton.
    assert _pack_size("Balloon,Straight Tip, Box of 10", "21800101004") == 10


def test_pack_size_falls_back_to_the_item_code_suffix():
    assert _pack_size("", "21800101003") == 10
    assert _pack_size("", "21800101004") == 1


def test_non_ten_carton_size_is_honoured():
    assert _pack_size("Balloon,Straight Tip, Box of 5", "21800101003") == 5
