"""Filename hints and merge behavior for purchasing PDF import (auxiliary module)."""

from __future__ import annotations

from datetime import date

from app.eqms.modules.purchasing.parsers.pdf import merge_import_metadata, parse_po_hints_from_filename


def test_parse_po_hints_from_filename_standard():
    h = parse_po_hints_from_filename("PO 0000161 BENTEC 15JAN2025.pdf")
    assert h is not None
    assert h["po_number"] == "0000161"
    assert h["supplier_name"] == "BENTEC"
    assert h["order_date"] == date(2025, 1, 15)


def test_parse_po_hints_from_filename_uses_basename():
    h = parse_po_hints_from_filename("Purchasing/POs/PO 0000161 BENTEC 15JAN2025.pdf")
    assert h is not None
    assert h["po_number"] == "0000161"


def test_parse_po_hints_from_filename_multiword_supplier():
    h = parse_po_hints_from_filename("PO 0000161 ACME WIDGET CORP 01DEC2026.pdf")
    assert h is not None
    assert h["po_number"] == "0000161"
    assert h["supplier_name"] == "ACME WIDGET CORP"
    assert h["order_date"] == date(2026, 12, 1)


def test_parse_po_hints_from_filename_non_matching_returns_none():
    assert parse_po_hints_from_filename("invoice.pdf") is None
    assert parse_po_hints_from_filename("") is None


def test_merge_import_metadata_filename_wins_over_junk_pdf_fields():
    parsed = {
        "po_number": "Silq",
        "order_date": date(2025, 1, 27),
        "supplier_name": "",
        "items": [{"description": "Line", "quantity": 1}],
    }
    merged = merge_import_metadata("PO 0000161 BENTEC 15JAN2025.pdf", parsed)
    assert merged["po_number"] == "0000161"
    assert merged["order_date"] == date(2025, 1, 15)
    assert merged["supplier_name"] == "BENTEC"
    assert merged["items"] == parsed["items"]


def test_merge_import_metadata_pdf_only_drops_alphabetic_po_number():
    parsed = {
        "po_number": "Silq",
        "order_date": date(2025, 1, 27),
        "supplier_name": "Vendor",
        "items": [],
    }
    merged = merge_import_metadata("not_a_po_pattern.pdf", parsed)
    assert merged["po_number"] is None
    assert merged["order_date"] == date(2025, 1, 27)


def test_merge_import_metadata_pdf_numeric_po_unchanged_without_hints():
    parsed = {
        "po_number": "0000999",
        "order_date": date(2024, 6, 1),
        "supplier_name": "ACME",
        "items": [],
    }
    merged = merge_import_metadata("scan.pdf", parsed)
    assert merged["po_number"] == "0000999"
    assert merged["order_date"] == date(2024, 6, 1)
