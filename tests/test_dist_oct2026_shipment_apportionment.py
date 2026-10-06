"""Regression tests for per-shipment quantity apportionment in the ShipStation sync.

When an order ships in more than one package (routine during the Sep-2026 14 Fr
backorder, where the balance shipped weeks later), the sync previously applied
the whole *order* quantity to every shipment, double counting the order. Each
distribution must instead carry only what its own shipment contained.
"""
from app.eqms.modules.shipstation_sync.service import _shipment_sku_units


def _item(sku, name, qty):
    return {"sku": sku, "name": name, "quantity": qty}


def test_units_come_from_the_shipment_not_the_order():
    shipment = {
        "shipmentItems": [
            _item("211410SPT", "ClearTract 14 Fr, 1 Unit", 20),
        ]
    }
    assert _shipment_sku_units(shipment) == {"211410SPT": 20}


def test_two_shipments_of_one_order_are_counted_separately():
    first = {
        "shipmentItems": [
            _item("211610SPT", "ClearTract 16 Fr, 1 Unit", 20),
            _item("211810SPT", "ClearTract 18 Fr, 1 Unit", 20),
        ]
    }
    second = {"shipmentItems": [_item("211410SPT", "ClearTract 14 Fr, 1 Unit", 20)]}

    a, b = _shipment_sku_units(first), _shipment_sku_units(second)
    assert a == {"211610SPT": 20, "211810SPT": 20}
    assert b == {"211410SPT": 20}
    # The backordered SKU must not appear on the first package.
    assert "211410SPT" not in a
    assert sum(a.values()) + sum(b.values()) == 60


def test_repeated_sku_lines_in_one_shipment_accumulate():
    shipment = {
        "shipmentItems": [
            _item("211810SPT", "ClearTract 18 Fr, 1 Unit", 10),
            _item("211810SPT", "ClearTract 18 Fr, 1 Unit", 5),
        ]
    }
    assert _shipment_sku_units(shipment) == {"211810SPT": 15}


def test_missing_item_detail_returns_empty_so_caller_will_not_guess():
    """An empty result is the signal to skip rather than reuse order quantities."""
    assert _shipment_sku_units({}) == {}
    assert _shipment_sku_units({"shipmentItems": None}) == {}
    assert _shipment_sku_units({"shipmentItems": []}) == {}


def test_unusable_rows_are_ignored():
    shipment = {
        "shipmentItems": [
            _item("211610SPT", "ClearTract 16 Fr, 1 Unit", 10),
            _item("", "no sku at all", 5),
            _item("211810SPT", "ClearTract 18 Fr, 1 Unit", 0),
            _item("211410SPT", "ClearTract 14 Fr, 1 Unit", "not a number"),
            "not even a dict",
        ]
    }
    assert _shipment_sku_units(shipment) == {"211610SPT": 10}


def test_box_quantities_are_expanded_to_individual_units():
    shipment = {"shipmentItems": [_item("211610SPT", "ClearTract 16 Fr, Box of 10", 3)]}
    assert _shipment_sku_units(shipment) == {"211610SPT": 30}
