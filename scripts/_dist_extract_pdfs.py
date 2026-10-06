"""Extract authoritative sales-order and packing-slip data from Distribution/ PDFs.

Read-only. Writes two JSON files plus a human-readable report so the parsed
values can be reviewed before any database write.

Sales order line format (Silq template):
    <item> <description...> <UNIT> <ORDERED> <PRICE> <AMOUNT> <DATE DUE>
e.g.
    21800101004 ClearTract 2-way Foley Catheter, 18 Fr, 10 ml EA 30.0000 24.50 735.00 8/4/2026

The ORDERED column is the authoritative quantity in individual units (UNIT=EA).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pdfplumber  # noqa: E402

from app.eqms.constants import ITEM_CODE_TO_SKU  # noqa: E402

DIST = ROOT / "Distribution"
OUT_SO = ROOT / "_dist_parsed_sales_orders.json"
OUT_PS = ROOT / "_dist_parsed_packing_slips.json"
OUT_TXT = ROOT / "_dist_parsed_report.txt"

SO_PDFS = [
    "2025Sales Orders.pdf",
    "SalesOrders2025-Aug2126.pdf",
    "Jan26SalesOrders.pdf",
    "Feb26SalesOrders.pdf",
    "Mar26SalesOrders.pdf",
    "Apr26SalesOrders.pdf",
    "May26SalesOrders1.pdf",
    "May26SalesOrders2.pdf",
    "Jun26SalesOrders1.pdf",
    "Jul26SalesOrders.pdf",
    "AugSep26SalesOrders.pdf",
    "SalesOrder0000125.pdf",
    "SalesOrder0000145.pdf",
    "SalesOrder0000202.pdf",
    "SalesOrder0000335.pdf",
]

ORDER_NO_RE = re.compile(r"ORDER NUMBER:\s*([0-9]{5,10})", re.I)
ORDER_DATE_RE = re.compile(r"ORDER DATE:\s*(\d{1,2}/\d{1,2}/\d{2,4})", re.I)
CUST_NO_RE = re.compile(r"CUSTOMER NUMBER:\s*(\S+)", re.I)

# item  description...  UNIT  ORDERED  PRICE  AMOUNT  DATE
LINE_RE = re.compile(
    r"^(?P<item>[A-Z0-9][A-Z0-9\-\.]*)\s+"
    r"(?P<desc>.*?)\s+"
    r"(?P<unit>EA|BX|CS|CA|PK)\s+"
    r"(?P<ordered>[\d,]+(?:\.\d+)?)\s+"
    r"(?P<price>[\d,]+(?:\.\d+)?)\s+"
    r"(?P<amount>[\d,]+(?:\.\d+)?)\s+"
    r"(?P<due>\d{1,2}/\d{1,2}/\d{2,4})\s*$",
    re.I,
)

# The ORDERED column is in boxes or in single units depending on the packaging
# named on the line's continuation text. UNIT always reads "EA" either way.
BOX_RE = re.compile(r"\bbox\s+of\s+(\d+)\b", re.I)
SINGLE_RE = re.compile(r"\b1\s+unit\b", re.I)


def pack_size(continuation: str, item_code: str) -> tuple[int, str]:
    """Units per ORDERED increment, and how it was determined."""
    m = BOX_RE.search(continuation)
    if m:
        return int(m.group(1)), f"desc:box of {m.group(1)}"
    if SINGLE_RE.search(continuation):
        return 1, "desc:1 unit"
    if item_code.endswith("003"):
        return 10, "itemcode:003"
    if item_code.endswith("004"):
        return 1, "itemcode:004"
    return 1, "default"

# Packing slip: order no + shipped qty + lot
PS_ORDER_RE = re.compile(
    r"(?:ORDER\s*#|ORDER\s*(?:NUMBER|NO\.?)|SALES ORDER)\s*:?\s*(?:SO\s*)?([0-9]{5,10})", re.I
)
PS_ROW_RE = re.compile(r"^(?P<item>2[0-9]{10})\s+.*?\s+(?P<qty>\d{1,4})\s*$")
PS_ROWLOT_RE = re.compile(r"SKU:\s*(2[0-9]{10})\s*LOT:\s*(SLQ-?\s?[0-9]{6,10})", re.I)

# Packing slip PDFs use soft hyphens / non-breaking hyphens in place of '-'.
_DASHES = dict.fromkeys(map(ord, "\u00ad\u2010\u2011\u2012\u2013\u2014\u2212"), "-")


def norm_dashes(s: str) -> str:
    return s.translate(_DASHES)
PS_LOT_RE = re.compile(r"\b(SLQ-\d{6,10})\b", re.I)
PS_TRACK_RE = re.compile(r"\b(\d{12,22})\b")


def num(s: str) -> float:
    return float(s.replace(",", ""))


def parse_sales_orders() -> list[dict]:
    orders: list[dict] = []
    for name in SO_PDFS:
        p = DIST / name
        if not p.exists():
            print(f"  !! missing {name}")
            continue
        with pdfplumber.open(p) as pdf:
            for pno, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if "SALES ORDER" not in text.upper():
                    continue
                m = ORDER_NO_RE.search(text)
                if not m:
                    continue
                onum = m.group(1).zfill(7)
                md = ORDER_DATE_RE.search(text)
                mc = CUST_NO_RE.search(text)

                sold_to = ""
                for ln in text.splitlines():
                    if "SOLD TO:" in ln.upper():
                        continue
                lines_out = []
                raw_lines = [l.strip() for l in text.splitlines()]
                for idx, raw in enumerate(raw_lines):
                    lm = LINE_RE.match(raw)
                    if not lm:
                        continue
                    item = lm.group("item").upper()
                    sku = ITEM_CODE_TO_SKU.get(item)
                    # Packaging is named on the following (continuation) line.
                    cont = " ".join(raw_lines[idx + 1 : idx + 3])
                    psize, how = pack_size(cont, item)
                    ordered = num(lm.group("ordered"))
                    lines_out.append(
                        {
                            "item_code": item,
                            "sku": sku,
                            "description": lm.group("desc").strip(),
                            "continuation": cont[:80],
                            "unit": lm.group("unit").upper(),
                            "ordered": ordered,
                            "pack_size": psize,
                            "pack_basis": how,
                            "units": int(ordered * psize),
                            "price": num(lm.group("price")),
                            "amount": num(lm.group("amount")),
                            "due": lm.group("due"),
                            "is_device": sku is not None,
                        }
                    )
                orders.append(
                    {
                        "order_number": onum,
                        "order_date": md.group(1) if md else None,
                        "customer_number": mc.group(1) if mc else None,
                        "source_pdf": name,
                        "page": pno,
                        "lines": lines_out,
                        "device_units": sum(l["units"] for l in lines_out if l["is_device"]),
                    }
                )
    return orders


PS_SHIPDATE_RE = re.compile(r"Ship Date\s+(\d{1,2}/\d{1,2}/\d{2,4})", re.I)
PS_SHIPTO_RE = re.compile(r"Ship To:\s*(.*?)\s+Order\s*#", re.I)


def split_slips(page_text: str) -> list[str]:
    """A single PDF page can hold several packing slips; split on the header."""
    parts, cur = [], []
    for ln in page_text.splitlines():
        if ln.strip().lower() == "packing slip" and cur:
            parts.append("\n".join(cur))
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        parts.append("\n".join(cur))
    return [p for p in parts if p.strip()]


def parse_packing_slips() -> list[dict]:
    out = []
    for p in sorted(DIST.glob("*PackingSlips.pdf")):
        with pdfplumber.open(p) as pdf:
            for pno, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    continue
                for seg_i, text in enumerate(split_slips(page_text), start=1):
                    out.append(_parse_one_slip(text, p.name, pno, seg_i))
    return out


def _parse_one_slip(text: str, pdf_name: str, pno: int, seg: int) -> dict:
    flat = norm_dashes(text)
    mo = PS_ORDER_RE.search(flat)
    md = PS_SHIPDATE_RE.search(flat)
    mt = PS_SHIPTO_RE.search(flat)

    # Lot numbers quoted anywhere on this slip, keyed by item code where possible.
    lot_by_item: dict[str, str] = {}
    for lm in PS_ROWLOT_RE.finditer(flat):
        lot_by_item.setdefault(lm.group(1), lm.group(2).upper().replace(" ", ""))
    lots = sorted(set(lot_by_item.values()) | {
        x.upper().replace(" ", "") for x in PS_LOT_RE.findall(flat)
    })

    qty_lines = []
    for raw in flat.splitlines():
        # Row: "<item code> <description...> <lot info...> <Qty>"
        # Qty is the trailing integer, already expressed in individual units.
        rm = PS_ROW_RE.match(raw.strip())
        if not rm:
            continue
        sku = ITEM_CODE_TO_SKU.get(rm.group("item"))
        if not sku:
            continue
        qty_lines.append(
            {
                "sku": sku,
                "item_code": rm.group("item"),
                "qty": int(rm.group("qty")),
                "lot": lot_by_item.get(rm.group("item")),
            }
        )

    return {
        "source_pdf": pdf_name,
        "page": pno,
        "slip_on_page": seg,
        "order_number": mo.group(1).zfill(7) if mo else None,
        "ship_date": md.group(1) if md else None,
        "ship_to": mt.group(1).strip() if mt else None,
        "lots": lots,
        "tracking": sorted(set(PS_TRACK_RE.findall(flat))),
        "lines": qty_lines,
        "units": sum(l["qty"] for l in qty_lines),
    }


def main() -> None:
    print("parsing sales orders...")
    orders = parse_sales_orders()
    print(f"  {len(orders)} sales order pages parsed")

    print("parsing packing slips...")
    slips = parse_packing_slips()
    print(f"  {len(slips)} packing slip pages parsed")

    OUT_SO.write_text(json.dumps(orders, indent=1), encoding="utf-8")
    OUT_PS.write_text(json.dumps(slips, indent=1), encoding="utf-8")

    rep = []
    rep.append(f"sales order pages: {len(orders)}")
    uniq = {}
    for o in orders:
        uniq.setdefault(o["order_number"], []).append(o)
    rep.append(f"unique order numbers: {len(uniq)}")
    dupes = {k: v for k, v in uniq.items() if len(v) > 1}
    rep.append(f"order numbers appearing on >1 page: {len(dupes)}")
    for k, v in sorted(dupes.items()):
        rep.append(f"   {k}: " + ", ".join(f"{x['source_pdf']}#p{x['page']}" for x in v))

    noline = [o for o in orders if not o["lines"]]
    rep.append(f"\norders with ZERO parsed lines: {len(noline)}")
    for o in noline[:40]:
        rep.append(f"   {o['order_number']}  {o['source_pdf']}#p{o['page']}")

    nodev = [o for o in orders if o["lines"] and o["device_units"] == 0]
    rep.append(f"\norders with lines but NO device units (NRE/service only): {len(nodev)}")
    for o in nodev[:40]:
        items = ",".join(sorted({l["item_code"] for l in o["lines"]}))
        rep.append(f"   {o['order_number']}  items={items}")

    rep.append("\nnon-EA units encountered:")
    units = {}
    for o in orders:
        for l in o["lines"]:
            units[l["unit"]] = units.get(l["unit"], 0) + 1
    rep.append(f"   {units}")

    rep.append("\npack size x basis (device lines only) -- verify no pack size is missed:")
    packs = {}
    for o in orders:
        for l in o["lines"]:
            if l["is_device"]:
                packs[(l["pack_size"], l["pack_basis"])] = (
                    packs.get((l["pack_size"], l["pack_basis"]), 0) + 1
                )
    for k, v in sorted(packs.items()):
        rep.append(f"   pack={k[0]:3d} via {k[1]:20s} -> {v} lines")

    rep.append("\nprice sanity check (amount should equal ordered x price):")
    bad = []
    for o in orders:
        for l in o["lines"]:
            if l["is_device"] and l["price"]:
                exp = round(l["ordered"] * l["price"], 2)
                if abs(exp - l["amount"]) > 0.02:
                    bad.append(f"   {o['order_number']} {l['item_code']} "
                               f"ordered={l['ordered']} price={l['price']} "
                               f"amount={l['amount']} expected={exp}")
    rep.append(f"   lines where amount != ordered*price: {len(bad)}")
    rep.extend(bad[:20])

    rep.append("\nunmapped item codes (device-looking but no SKU):")
    unmapped = {}
    for o in orders:
        for l in o["lines"]:
            if not l["sku"]:
                unmapped[l["item_code"]] = unmapped.get(l["item_code"], 0) + 1
    for k, v in sorted(unmapped.items(), key=lambda x: -x[1]):
        rep.append(f"   {v:4d}  {k}")

    rep.append("\n" + "=" * 100)
    rep.append("PARSED DEVICE ORDERS (order_number, date, units, lines)")
    rep.append("=" * 100)
    for k in sorted(uniq):
        o = uniq[k][0]
        if o["device_units"] == 0:
            continue
        det = "; ".join(
            f"{l['sku']} {int(l['ordered'])}x{l['pack_size']}={l['units']}u"
            for l in o["lines"]
            if l["is_device"]
        )
        rep.append(f"{k} | {o['order_date']} | {o['device_units']:4d}u | {det}")

    rep.append("\n" + "=" * 100)
    rep.append("PACKING SLIP PAGES WITH AN ORDER NUMBER")
    rep.append("=" * 100)
    withno = [s for s in slips if s["order_number"]]
    rep.append(f"{len(withno)} of {len(slips)} pages had a detectable order number")
    for s in sorted(withno, key=lambda x: (x["order_number"], x["source_pdf"], x["page"])):
        det = "; ".join(f"{l['sku']} x{l['qty']}" for l in s["lines"])
        rep.append(
            f"{s['order_number']} | {s['ship_date']} | {s['units']:4d}u | "
            f"{s['source_pdf']}#p{s['page']}.{s['slip_on_page']} | "
            f"lots={','.join(s['lots'])} | {det}"
        )

    OUT_TXT.write_text("\n".join(rep), encoding="utf-8")
    print(f"wrote {OUT_TXT}")


if __name__ == "__main__":
    main()
