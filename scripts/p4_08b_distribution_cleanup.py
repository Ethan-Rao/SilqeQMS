"""P4-08B distribution cleanup. Dry-run by default; writes only with --execute.

Usage:
    python scripts/p4_08b_distribution_cleanup.py
    python scripts/p4_08b_distribution_cleanup.py --execute
    python scripts/p4_08b_distribution_cleanup.py --report
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DRY_RUN = "--execute" not in sys.argv
REPORT_ONLY = "--report" in sys.argv
ABC_ONLY = "--tasks-abc" in sys.argv

MARKER_ACTION = "p4_08b.file_import_complete"


def _resolve_dist_dir() -> Path:
    staged = ROOT / "scripts" / "_p4_08b_import_files"
    if (staged / "SalesOrders2025-Aug2126.pdf").exists():
        return staged
    return ROOT / "Distribution"


DIST_DIR = _resolve_dist_dir()
SO_PDF = DIST_DIR / "SalesOrders2025-Aug2126.pdf"
TRUNK_DIR = DIST_DIR / "TrunkStockDistributions"

DELETE_IDS = (1033, 1034, 1035, 1036)
KEEP_BOTH = ((789, 1032, "0000203"), (833, 834, "0000251"))


def _looks_like_silq_so(num: str | None) -> bool:
    digits = "".join(ch for ch in (num or "") if ch.isdigit())
    if not digits:
        return False
    n = int(digits)
    return 100 <= n <= 5000

TRUNK = [
    {
        "file": TRUNK_DIR / "Harbor 12.5.25SO 0000275.JPG",
        "order_number": "0000275",
        "ship_date": date(2025, 12, 5),
        "customer_hint": "Harbor",
        "lines": [("211810SPT", "SLQ-05022025", 10)],
        "so_qty": 10,
    },
    {
        "file": TRUNK_DIR / "DayKimball7726. SO0000366.jpeg",
        "order_number": "0000366",
        "ship_date": date(2026, 7, 7),
        "customer_hint": "Day Kimball",
        "lines": [("211610SPT", "SLQ-05012025", 4)],
        "so_qty": 4,
    },
    {
        "file": TRUNK_DIR / "UnivUtah12826 SO 000387.jpeg",
        "order_number": "0000387",
        "ship_date": date(2026, 1, 28),
        "customer_hint": "Utah",
        "lines": [("211810SPT", "SLQ-05022025", 4), ("211610SPT", "SLQ-05012025", 4)],
        "so_qty": 8,
    },
    {
        "file": TRUNK_DIR / "LinehanProvidenceStJohns 8.7.26 SO 388.JPG",
        "order_number": "0000388",
        "ship_date": date(2026, 8, 7),
        "customer_hint": "Saint John",
        "lines": [("211610SPT", "SLQ-05012025", 4), ("211810SPT", "SLQ-05022025", 4)],
        "so_qty": 8,
    },
    {
        "file": TRUNK_DIR / "Lyn Hopkins 2.2.26 390.JPG",
        "order_number": "0000390",
        "ship_date": date(2026, 2, 26),
        "customer_hint": "Hopkins",
        "lines": [("211610SPT", "SLQ-05012025", 2), ("211810SPT", "SLQ-05022025", 2)],
        "so_qty": 4,
    },
]


def _ascii(s: object) -> str:
    return ("" if s is None else str(s)).encode("ascii", "replace").decode("ascii")


def _admin(s):
    from app.eqms.models import User

    u = s.query(User).filter(User.email.ilike("%ethan%")).first()
    if u:
        return u
    return s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()


def _find_so(s, order_number: str):
    from app.eqms.modules.rep_traceability.service import find_sales_order_by_normalized_number

    return find_sales_order_by_normalized_number(s, order_number)


def _verification_atts(s, dist_id: int):
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
    from app.eqms.modules.rep_traceability.utils import is_packing_slip_pdf_type

    rows = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.distribution_entry_id == dist_id)
        .all()
    )
    return [a for a in rows if is_packing_slip_pdf_type(a.pdf_type)]


def task_a_preview(s) -> dict:
    from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf, split_pdf_into_pages

    pages = split_pdf_into_pages(SO_PDF.read_bytes())
    parsed = []
    errors = []
    for page_num, page_bytes in pages:
        try:
            result = parse_sales_orders_pdf(page_bytes)
        except Exception as exc:
            errors.append(f"page {page_num}: {exc}")
            continue
        for od in result.orders or []:
            parsed.append(od)
    created, present, qty_notes = [], [], []
    for od in parsed:
        num = od.get("order_number")
        if not _looks_like_silq_so(num):
            qty_notes.append(f"SKIP non-SO parse {num!r} customer={od.get('customer_name')}")
            continue
        so = _find_so(s, num)
        lines = od.get("lines") or []
        line_q = sum(int(x.get("quantity") or 0) for x in lines)
        if so:
            present.append(num)
            stored = sum(int(ln.quantity or 0) for ln in (so.lines or []))
            if num in ("0000275", "0000366") or stored != line_q:
                qty_notes.append(
                    f"{num} stored={stored} parsed={line_q} lines={[(x.get('sku'), x.get('quantity')) for x in lines]}"
                )
        else:
            created.append(num)
    print("TASK A preview")
    print(f"  pages={len(pages)} parsed_orders={len(parsed)} new={len(created)} existing={len(present)}")
    print(f"  new: {', '.join(_ascii(x) for x in created[:40])}{' ...' if len(created) > 40 else ''}")
    for note in qty_notes:
        print(f"  qty: {_ascii(note)}")
    if errors:
        print(f"  parse_errors={len(errors)}")
        for e in errors[:8]:
            print(f"    {_ascii(e)}")
    return {"created": created, "present": present, "parsed": parsed, "pages": pages, "qty_notes": qty_notes}


def task_a_execute(s, user, pages) -> None:
    from app.eqms.modules.rep_traceability.admin import (
        _fill_so_parsed_fields,
        _find_or_create_customer_for_order_data,
        _find_sales_order_by_number,
        _store_pdf_attachment,
    )
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
    from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type
    from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf
    from app.eqms.modules.rep_traceability.service import rematch_unmatched_distributions_for_order

    created = updated = 0
    for page_num, page_bytes in pages:
        result = parse_sales_orders_pdf(page_bytes)
        for order_data in result.orders or []:
            order_number = order_data["order_number"]
            if not _looks_like_silq_so(order_number):
                print(f"  skip bogus order_number={order_number!r}")
                continue
            existing = _find_so(s, order_number) or _find_sales_order_by_number(s, order_number)
            if existing:
                continue
            customer = _find_or_create_customer_for_order_data(s, order_data)
            so = SalesOrder(
                order_number=order_number,
                order_date=order_data["order_date"],
                ship_date=order_data.get("ship_date") or order_data["order_date"],
                customer_id=customer.id,
                source="pdf_import",
                external_key=f"pdf:{order_number}",
                status="completed",
                created_by_user_id=user.id,
                updated_by_user_id=user.id,
                nre_invoice_status="Pending Invoice",
            )
            _fill_so_parsed_fields(so, order_data)
            s.add(so)
            s.flush()
            rematch_unmatched_distributions_for_order(s, so)
            _store_pdf_attachment(
                s,
                pdf_bytes=page_bytes,
                filename=f"SO_{order_number}.pdf",
                pdf_type="sales_order_page",
                sales_order_id=so.id,
                distribution_entry_id=None,
                user=user,
                order_number=order_number,
            )
            for line_num, line_data in enumerate(order_data.get("lines") or [], start=1):
                sku = line_data.get("sku")
                quantity = line_data.get("quantity")
                if not sku or not quantity or int(quantity) <= 0:
                    continue
                s.add(
                    SalesOrderLine(
                        sales_order_id=so.id,
                        sku=sku,
                        quantity=quantity,
                        line_number=line_num,
                    )
                )
            s.flush()
            _apply_new_so_qty_override(s, so, order_number)
            safe_apply_order_type(s, so, user=user)
            created += 1
    print(f"TASK A execute: created={created} updated={updated}")


NEW_SO_QTY = {
    "0000387": [("211610SPT", 4), ("211810SPT", 4)],
    "0000388": [("211610SPT", 4), ("211810SPT", 4)],
}


def _apply_new_so_qty_override(s, so, order_number: str) -> None:
    from app.eqms.modules.rep_traceability.models import SalesOrderLine
    from app.eqms.modules.rep_traceability.service import normalize_order_number

    key = None
    digits = normalize_order_number(order_number)
    for raw, lines in NEW_SO_QTY.items():
        if normalize_order_number(raw) == digits:
            key = raw
            new_lines = lines
            break
    if key is None:
        return
    for ln in list(so.lines or []):
        s.delete(ln)
    s.flush()
    for i, (sku, qty) in enumerate(new_lines, start=1):
        s.add(SalesOrderLine(sales_order_id=so.id, sku=sku, quantity=qty, line_number=i))


def _correct_quantities_and_day_kimball(s, user) -> None:
    from app.eqms.audit import record_event
    from app.eqms.modules.customer_profiles.service import find_or_create_customer
    from app.eqms.modules.rep_traceability.models import SalesOrderLine
    from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type

    dk = find_or_create_customer(
        s,
        facility_name="Day Kimball Health Urology",
        address1="30 Pomfret Street",
        city="Putnam",
        state="CT",
        zip="06260",
        identity="facility",
        customer_type="catheter",
    )
    print(f"  Day Kimball customer id={dk.id} key={_ascii(dk.company_key)} name={_ascii(dk.facility_name)}")

    fixes = {
        "0000275": [("211810SPT", 10)],
        "0000366": [("211610SPT", 4)],
        "0000387": [("211610SPT", 4), ("211810SPT", 4)],
        "0000388": [("211610SPT", 4), ("211810SPT", 4)],
    }
    for num, new_lines in fixes.items():
        so = _find_so(s, num)
        if not so:
            print(f"  missing SO {num} for qty fix")
            continue
        stored = [(ln.sku, ln.quantity) for ln in (so.lines or [])]
        print(f"  {num} lines before={stored} -> {new_lines}")
        if DRY_RUN:
            continue
        for ln in list(so.lines or []):
            s.delete(ln)
        s.flush()
        for i, (sku, qty) in enumerate(new_lines, start=1):
            s.add(SalesOrderLine(sales_order_id=so.id, sku=sku, quantity=qty, line_number=i))
        record_event(
            s,
            actor=user,
            action="sales_order.line_qty_corrected",
            entity_type="SalesOrder",
            entity_id=str(so.id),
            reason="P4-08B PDF quantity cleanup",
            metadata={"order_number": num, "before": stored, "after": new_lines},
        )

    for so_num in ("0000366", "0000376"):
        so = _find_so(s, so_num)
        if not so:
            continue
        print(
            f"  rekey {so_num} customer_id={so.customer_id} name={_ascii(so.customer.facility_name if so.customer else None)} -> dk={dk.id} {_ascii(dk.facility_name)}"
        )
        if DRY_RUN:
            continue
        before = so.customer_id
        so.customer_id = dk.id
        record_event(
            s,
            actor=user,
            action="sales_order.customer_rekeyed",
            entity_type="SalesOrder",
            entity_id=str(so.id),
            reason="P4-08B Day Kimball",
            metadata={"order_number": so_num, "before": before, "after": dk.id},
        )
        safe_apply_order_type(s, so, user=user)


def task_b_preview_and_maybe_execute(s, user) -> dict:
    from app.eqms.modules.rep_traceability.admin import (
        _delete_packing_slip_attachments_for_distribution,
        _match_distribution_for_label,
        _store_pdf_attachment,
    )
    from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf, split_pdf_into_pages

    files = sorted(DIST_DIR.glob("*PackingSlips.pdf"))
    matched = unmatched = 0
    unmatched_pages = []
    for path in files:
        pages = split_pdf_into_pages(path.read_bytes())
        for page_num, page_bytes in pages:
            result = parse_sales_orders_pdf(page_bytes)
            labels = result.labels or []
            if not labels:
                unmatched += 1
                unmatched_pages.append(f"{path.name} p{page_num} no-label")
                if _unmatched_slip_already_stored(s, path.name, page_num):
                    continue
                if not DRY_RUN:
                    _store_pdf_attachment(
                        s,
                        pdf_bytes=page_bytes,
                        filename=f"{path.name}_page_{page_num}.pdf",
                        pdf_type="packing_slip",
                        sales_order_id=None,
                        distribution_entry_id=None,
                        user=user,
                    )
                continue
            seen: set[int] = set()
            had_unmatched = False
            for label in labels:
                entry = _match_distribution_for_label(
                    s,
                    tracking_number=label.get("tracking_number"),
                    ship_to=label.get("ship_to"),
                    order_number=label.get("order_number"),
                    ss_shipment_id=label.get("ss_shipment_id"),
                )
                if entry and entry.id not in seen:
                    seen.add(entry.id)
                    matched += 1
                    if _verification_atts(s, entry.id):
                        continue
                    if not DRY_RUN:
                        _delete_packing_slip_attachments_for_distribution(s, entry.id)
                        _store_pdf_attachment(
                            s,
                            pdf_bytes=page_bytes,
                            filename=f"{path.name}_page_{page_num}.pdf",
                            pdf_type="packing_slip",
                            sales_order_id=entry.sales_order_id,
                            distribution_entry_id=entry.id,
                            user=user,
                            order_number=entry.order_number or None,
                        )
                elif not entry:
                    had_unmatched = True
            if had_unmatched:
                unmatched += 1
                unmatched_pages.append(
                    f"{path.name} p{page_num} orders={[l.get('order_number') for l in labels]}"
                )
                if _unmatched_slip_already_stored(s, path.name, page_num):
                    continue
                if not DRY_RUN:
                    _store_pdf_attachment(
                        s,
                        pdf_bytes=page_bytes,
                        filename=f"{path.name}_page_{page_num}.pdf",
                        pdf_type="packing_slip",
                        sales_order_id=None,
                        distribution_entry_id=None,
                        user=user,
                    )
    print(f"TASK B files={len(files)} matched_slips={matched} unmatched_pages={unmatched}")
    for row in unmatched_pages[:25]:
        print(f"  unmatched {_ascii(row)}")
    return {"matched": matched, "unmatched": unmatched}


def _unmatched_slip_already_stored(s, source_name: str, page_num: int) -> bool:
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment

    filename = f"{source_name}_page_{page_num}.pdf"
    return (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.filename == filename)
        .first()
        is not None
    )


def _trunk_exists_for_so(s, order_number: str) -> bool:
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry
    from app.eqms.modules.rep_traceability.service import normalize_order_number

    target = normalize_order_number(order_number)
    rows = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.source == "manual")
        .all()
    )
    return any(normalize_order_number(r.order_number) == target for r in rows)


def _all_trunk_exist(s) -> bool:
    return all(_trunk_exists_for_so(s, spec["order_number"]) for spec in TRUNK)


def _has_file_import_marker(s) -> bool:
    from app.eqms.models import AuditEvent

    return s.query(AuditEvent).filter(AuditEvent.action == MARKER_ACTION).first() is not None


def file_import_already_complete(s) -> bool:
    return _has_file_import_marker(s) or _all_trunk_exist(s)


def write_file_import_marker(s, user) -> None:
    from app.eqms.audit import record_event

    record_event(
        s,
        actor=user,
        action=MARKER_ACTION,
        entity_type="DistributionLogEntry",
        entity_id="p4_08b_abc",
        reason="P4-08B Tasks A-C complete",
    )


def task_c_preview_and_maybe_execute(s, user) -> None:
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.admin import _store_pdf_attachment
    from app.eqms.modules.rep_traceability.models import DistributionLine, DistributionLogEntry
    from app.eqms.modules.rep_traceability.service import create_distribution_entry

    print("TASK C trunk-stock")
    for spec in TRUNK:
        so = _find_so(s, spec["order_number"])
        existing = _trunk_exists_for_so(s, spec["order_number"])
        cust = so.customer if so else None
        if cust is None:
            cust = (
                s.query(Customer)
                .filter(Customer.facility_name.ilike(f"%{spec['customer_hint']}%"))
                .first()
            )
        print(
            f"  SO={spec['order_number']} so_id={so.id if so else None} "
            f"cust={_ascii(cust.facility_name if cust else None)} "
            f"date={spec['ship_date']} qty={spec['so_qty']} lines={spec['lines']} "
            f"file={spec['file'].name} exists={spec['file'].exists()} "
            f"already={int(bool(existing))}"
        )
        if DRY_RUN or existing or so is None or cust is None:
            if so is None:
                print("    SKIP missing sales order")
            continue
        first_sku, first_lot, first_qty = spec["lines"][0]
        entry = create_distribution_entry(
            s,
            {
                "ship_date": spec["ship_date"],
                "order_number": spec["order_number"],
                "facility_name": cust.facility_name,
                "customer_id": cust.id,
                "sales_order_id": so.id,
                "sku": first_sku,
                "lot_number": first_lot,
                "quantity": spec["so_qty"],
                "source": "manual",
            },
            user=user,
            source_default="manual",
            create_line=False,
        )
        for sku, lot, qty in spec["lines"]:
            s.add(
                DistributionLine(
                    distribution_entry_id=entry.id,
                    sku=sku,
                    lot_number=lot,
                    quantity=qty,
                )
            )
        raw = spec["file"].read_bytes()
        ctype = "image/jpeg"
        _store_pdf_attachment(
            s,
            pdf_bytes=raw,
            filename=spec["file"].name,
            pdf_type="delivery_verification",
            sales_order_id=so.id,
            distribution_entry_id=entry.id,
            user=user,
            order_number=spec["order_number"],
            content_type=ctype,
        )
        print(f"    created dist id={entry.id}")


def task_d_preview_and_maybe_execute(s, user) -> None:
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry
    from app.eqms.modules.rep_traceability.service import delete_distribution_entry, sum_distribution_units

    print("TASK D duplicates")
    for keep_a, keep_b, num in KEEP_BOTH:
        rows = [s.get(DistributionLogEntry, keep_a), s.get(DistributionLogEntry, keep_b)]
        units = sum_distribution_units([r for r in rows if r])
        print(f"  KEEP {num} ids={keep_a},{keep_b} present={[r.id for r in rows if r]} units={units}")
    for dist_id in DELETE_IDS:
        row = s.get(DistributionLogEntry, dist_id)
        if not row:
            print(f"  DELETE {dist_id} already gone")
            continue
        print(
            f"  DELETE {dist_id} order={_ascii(row.order_number)} date={row.ship_date} "
            f"qty={row.quantity} fac={_ascii(row.facility_name)}"
        )
        if not DRY_RUN:
            delete_distribution_entry(s, row, user=user, reason="P4-08B confirmed duplicate")


def task_e_preview_and_maybe_execute(s) -> int:
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, OrderPdfAttachment
    from app.eqms.modules.rep_traceability.service import packing_slip_display_filename
    from app.eqms.modules.rep_traceability.utils import is_packing_slip_pdf_type

    atts = s.query(OrderPdfAttachment).all()
    planned: list[tuple] = []
    used: set[str] = set()
    for att in atts:
        if not is_packing_slip_pdf_type(att.pdf_type):
            continue
        if not att.distribution_entry_id:
            continue
        dist = s.get(DistributionLogEntry, att.distribution_entry_id)
        if dist is None:
            continue
        name = None
        if dist.customer is not None:
            name = dist.customer.facility_name
        else:
            name = dist.facility_name or dist.customer_name
        new_name = packing_slip_display_filename(name, dist.ship_date, dist.order_number, existing=used)
        used.add(new_name)
        if att.filename != new_name:
            planned.append((att, new_name))
    print(f"TASK E rename {len(planned)} packing-slip filenames")
    for att, new_name in planned[:15]:
        print(f"  {att.id} {_ascii(att.filename)} -> {_ascii(new_name)}")
    if len(planned) > 15:
        print(f"  ... {len(planned) - 15} more")
    if not DRY_RUN:
        for att, new_name in planned:
            att.filename = new_name
    return len(planned)


def task_f_report(s) -> None:
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
    from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_CLEARTRACT_IN_PROCESS
    from app.eqms.modules.rep_traceability.service import (
        normalize_order_number,
        sum_distribution_units,
    )

    cutoff = date(2025, 1, 1)
    dists = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.ship_date >= cutoff)
        .order_by(DistributionLogEntry.ship_date.asc(), DistributionLogEntry.id.asc())
        .all()
    )
    no_so = []
    no_file = []
    multi_file = []
    for d in dists:
        if d.sales_order_id is None:
            no_so.append(d)
        atts = _verification_atts(s, d.id)
        if d.sales_order_id and not atts:
            no_file.append(d)
        if len(atts) > 1:
            multi_file.append(d)

    print("TASK F coverage")
    print("1. 2025+ distributions with no sales order:")
    for d in no_so:
        print(f"   id={d.id} order={_ascii(d.order_number)} date={d.ship_date} qty={d.quantity} {_ascii(d.facility_name)}")
    if not no_so:
        print("   (none)")

    print("2. 2025+ with sales order but no verification file:")
    for d in no_file:
        print(f"   id={d.id} order={_ascii(d.order_number)} date={d.ship_date} qty={d.quantity}")
    if not no_file:
        print("   (none)")

    print("3. 2025+ with more than one verification file:")
    for d in multi_file:
        print(f"   id={d.id} order={_ascii(d.order_number)} files={len(_verification_atts(s, d.id))}")
    if not multi_file:
        print("   (none)")

    print("4. Trunk-stock rows:")
    for spec in TRUNK:
        rows = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.source == "manual")
            .filter(DistributionLogEntry.order_number == spec["order_number"])
            .filter(DistributionLogEntry.ship_date == spec["ship_date"])
            .all()
        )
        if not rows:
            print(f"   {spec['order_number']} MISSING")
            continue
        for d in rows:
            lots = [(ln.lot_number, ln.quantity, ln.sku) for ln in (d.lines or [])]
            atts = _verification_atts(s, d.id)
            fn = atts[0].filename if atts else None
            print(
                f"   dist={d.id} SO={_ascii(d.order_number)} date={d.ship_date} "
                f"qty={sum_distribution_units([d])} lots={lots} "
                f"cust={_ascii(d.customer.facility_name if d.customer else d.facility_name)} "
                f"file={_ascii(fn)}"
            )

    print("5. Remaining cleartract_in_process:")
    open_orders = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS)
        .order_by(SalesOrder.order_number.asc())
        .all()
    )
    for so in open_orders:
        print(f"   {so.order_number} id={so.id} cust={_ascii(so.customer.facility_name if so.customer else None)}")

    harbor_203 = [
        d
        for d in dists
        if normalize_order_number(d.order_number) == normalize_order_number("0000203")
    ]
    print(
        f"6. Harbor 0000203 rows={len(harbor_203)} ids={[d.id for d in harbor_203]} "
        f"units={sum_distribution_units(harbor_203)} (expect 120)"
    )
    print("   Dashboard unit delta expected: +34 trunk-stock -130 deleted dups = -96")


def _storage_writable(app) -> bool:
    from app.eqms.storage import storage_from_config

    st = storage_from_config(app.config)
    key = "tmp/p4_08b_put_probe.txt"
    try:
        st.put_bytes(key, b"p4-08b-probe", content_type="text/plain")
        st.delete(key)
        return True
    except Exception:
        return False


def _run_abc(s, user) -> None:
    preview = task_a_preview(s)
    task_a_execute(s, user, preview["pages"])
    task_b_preview_and_maybe_execute(s, user)
    task_c_preview_and_maybe_execute(s, user)
    if _all_trunk_exist(s):
        if not _has_file_import_marker(s):
            write_file_import_marker(s, user)
            print("P4-08B file import marker written.", flush=True)
        else:
            print("P4-08B file import complete.", flush=True)
    else:
        print("P4-08B file import incomplete; will retry next deploy.", flush=True)


def run_abc_on_release() -> None:
    """Idempotent Tasks A–C for App Platform release. Never raises to the caller."""
    global DRY_RUN
    if not SO_PDF.exists():
        print("P4-08B file import skipped: import files not in image.", flush=True)
        return
    from app.eqms import create_app
    from app.eqms.db import db_session

    prev = DRY_RUN
    DRY_RUN = False
    app = create_app()
    with app.app_context():
        s = db_session()
        try:
            if file_import_already_complete(s):
                print("P4-08B file import already complete; skip.", flush=True)
                s.rollback()
                return
            if not _storage_writable(app):
                print("P4-08B file import skipped: storage put_bytes failed.", flush=True)
                s.rollback()
                return
            user = _admin(s)
            _run_abc(s, user)
            s.commit()
        except Exception as exc:
            s.rollback()
            print(f"P4-08B file import skipped: {type(exc).__name__}.", flush=True)
        finally:
            DRY_RUN = prev


def main() -> None:
    from app.eqms import create_app
    from app.eqms.db import db_session

    print(f"Mode: {'EXECUTE' if not DRY_RUN and not REPORT_ONLY else 'DRY RUN / REPORT'}")
    if not SO_PDF.exists():
        raise SystemExit(f"missing {SO_PDF}")

    app = create_app()
    with app.app_context():
        s = db_session()
        user = _admin(s)
        print(f"actor={_ascii(user.email if user else None)} id={user.id if user else None}")
        storage_ok = _storage_writable(app)
        if not storage_ok:
            print("P4-08B file import skipped: storage put_bytes failed.", flush=True)
        try:
            if REPORT_ONLY:
                task_f_report(s)
                s.rollback()
                return
            if ABC_ONLY:
                if file_import_already_complete(s):
                    print("P4-08B file import already complete; skip.", flush=True)
                    s.rollback()
                    return
                if DRY_RUN or not storage_ok:
                    if storage_ok:
                        preview = task_a_preview(s)
                        print(f"DRY RUN A-C new={preview.get('created')}")
                    s.rollback()
                    return
                _run_abc(s, user)
                s.commit()
                print("COMMITTED")
                return
            preview = task_a_preview(s)
            if not DRY_RUN and storage_ok:
                task_a_execute(s, user, preview["pages"])
            _correct_quantities_and_day_kimball(s, user)
            if storage_ok and not DRY_RUN:
                task_b_preview_and_maybe_execute(s, user)
                task_c_preview_and_maybe_execute(s, user)
            if not ABC_ONLY:
                task_d_preview_and_maybe_execute(s, user)
                task_e_preview_and_maybe_execute(s)
            task_f_report(s)
            if DRY_RUN:
                s.rollback()
                print("DRY RUN — re-run with --execute to write.")
            else:
                s.commit()
                print("COMMITTED")
        except Exception:
            s.rollback()
            raise


if __name__ == "__main__":
    main()
