"""Tests for packing slip parsing and strict PDF splitting (no DB — SQLite test DB cannot create_all full schema)."""

import io

import pytest

from app.eqms.modules.rep_traceability.parsers.pdf import (
    PdfSplitError,
    _parse_packing_slip_segment,
    split_pdf_into_pages,
    split_text_into_packing_slip_segments,
)


def test_split_text_into_two_packing_slip_segments():
    text = (
        "Packing Slip\nShip To:\nAcme\nOrder # SO 0000280\n211810SPT widget 5 EA\n"
        "Packing Slip\nShip To:\nBeta\nOrder # SO 0000281\n211610SPT x 2 EA\n"
    )
    segs = split_text_into_packing_slip_segments(text)
    assert len(segs) == 2
    assert "0000280" in segs[0]
    assert "0000281" in segs[1]


def test_packing_slip_segment_parses_reasonable_qty():
    seg = "Packing Slip\nOrder # SO 0000280\n211810SPT SLQ Catheter 12 EA\nLOT: SLQ-05012025"
    p = _parse_packing_slip_segment(seg, page_num=1, slip_index=1)
    assert p is not None
    assert p["order_number"] == "0000280"
    items = p.get("items") or []
    assert any(i["sku"] == "211810SPT" and i["quantity"] == 12 for i in items)


def test_split_multipage_pdf_raises_when_reader_fails(monkeypatch):
    import PyPDF2
    from PyPDF2 import PdfWriter

    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.add_blank_page(width=72, height=72)
    w.write(buf)
    pdf_bytes = buf.getvalue()

    def _raise(*_a, **_k):
        raise OSError("simulated reader failure")

    monkeypatch.setattr(PyPDF2, "PdfReader", _raise)
    with pytest.raises(PdfSplitError):
        split_pdf_into_pages(pdf_bytes, strict_multi_page=True)
