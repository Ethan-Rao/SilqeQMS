"""Distribution data cleanup, October 2026.

Reconciles live sales-order and distribution records against the authoritative
source documents in Distribution/ (sales order PDFs and packing slips).

Authority model
---------------
* Sales order PDFs  -> what was ORDERED. The ORDERED column is in boxes or in
  single units depending on the packaging named on the row ("Box of 10" vs
  "1 Unit"); the UNIT column always reads "EA" and is not a reliable indicator.
* Packing slips     -> what was SHIPPED. The Qty column is in individual units.
  One packing slip == one shipment, so the number of distinct slips for an order
  is what distinguishes a genuine multi-package shipment from a duplicated
  distribution record.

Usage
    python scripts/dist_cleanup_2026_10.py            # dry run (default)
    python scripts/dist_cleanup_2026_10.py --execute  # apply changes
    python scripts/dist_cleanup_2026_10.py --execute --only=A,C
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

PARSED_SO = ROOT / "_dist_parsed_sales_orders.json"
PARSED_PS = ROOT / "_dist_parsed_packing_slips.json"
LOG = ROOT / "_dist_cleanup_log.txt"

REASON = "Distribution reconciliation Oct-2026: corrected against source sales order PDFs and packing slips"

# Duplicate distribution rows, each confirmed by a packing slip showing a single
# shipment where the database holds two. Keep -> Drop.
CONFIRMED_DUPLICATES = [
    # (drop_id, keep_id, order_number, slip_evidence)
    (1045, 871, "0000302", "Mar26PackingSlips.pdf#p2.2 = 30u, one slip"),
    (1046, 879, "0000312", "Apr26PackingSlips.pdf#p2.1 = 30u, one slip"),
    (1047, 940, "0000346", "Jun26PackingSlips.pdf#p1.1 = 40u, one slip"),
    (1048, 983, "0000353", "Jun26PackingSlips.pdf#p5.2 = 30u, one slip"),
    (1078, 1079, "0000398", "Sep26PackingSlips.pdf#p9.2 = 20u on 10/1, one slip"),
    (1082, 1081, "0000403", "Sep26PackingSlips.pdf#p10.2 = 20u on 10/1, one slip"),
]

# Genuine multi-package shipments - must NOT be touched. Each has one packing
# slip per package and the slip totals match the order exactly.
PROTECTED_MULTI_PACKAGE = {
    "0000203": "2 slips x 60u = 120u",
    "0000251": "2 slips (100u 18Fr + 100u 16Fr) = 200u",
    "0000287": "2 slips (50u 16Fr + 60u 18Fr) = 110u",
}

# 20 Fr / 22 Fr item codes have no SKU in the system and cannot be stored while
# VALID_SKUS and the distribution_log_entries SKU CHECK exclude them.
UNSUPPORTED_ITEM_CODES = {"22000101003", "22200101003"}

PDF_PRIORITY = [
    "2025Sales Orders.pdf", "SalesOrders2025-Aug2126.pdf", "Jan26SalesOrders.pdf",
    "Feb26SalesOrders.pdf", "Mar26SalesOrders.pdf", "Apr26SalesOrders.pdf",
    "May26SalesOrders1.pdf", "May26SalesOrders2.pdf", "Jun26SalesOrders1.pdf",
    "Jul26SalesOrders.pdf", "AugSep26SalesOrders.pdf", "SalesOrder0000125.pdf",
    "SalesOrder0000145.pdf", "SalesOrder0000202.pdf", "SalesOrder0000335.pdf",
]
PRIO = {n: i for i, n in enumerate(PDF_PRIORITY)}

out_lines: list[str] = []


def say(msg: str = "") -> None:
    print(msg)
    out_lines.append(msg)


def load_authority() -> dict[str, dict]:
    """One authoritative parsed sales order per order number."""
    parsed = json.loads(PARSED_SO.read_text(encoding="utf-8"))
    by_num: dict[str, list[dict]] = defaultdict(list)
    for o in parsed:
        by_num[o["order_number"]].append(o)
    auth = {}
    for num, pages in by_num.items():
        dev = [p for p in pages if any(l["is_device"] for l in p["lines"])]
        pool = dev or pages
        pool.sort(key=lambda p: (PRIO.get(p["source_pdf"], 999), p["page"]))
        auth[num] = pool[-1]
    return auth


def load_slips() -> dict[str, list[dict]]:
    """Deduplicated packing slips per order number.

    A shipment near a month boundary appears in two consecutive monthly exports,
    so the same slip must only be counted once. Collapse on (ship_date, line
    content) but *only across different source PDFs*: two identical slips inside
    one export are two real packages (two boxes of the same SKU shipped
    together), and collapsing those would understate what shipped.
    """
    slips = json.loads(PARSED_PS.read_text(encoding="utf-8"))
    by_num: dict[str, dict[tuple, dict]] = defaultdict(dict)
    for s in slips:
        if not s.get("order_number") or not s.get("lines"):
            continue
        key = (
            s.get("ship_date"),
            tuple(sorted((l["sku"], l["qty"]) for l in s["lines"])),
        )
        kept = by_num[s["order_number"]].get(key)
        if kept is None:
            by_num[s["order_number"]][key] = s
        elif kept.get("source_pdf") == s.get("source_pdf"):
            # Same export, so this is a genuinely separate package.
            by_num[s["order_number"]][key + (s.get("page"), s.get("slip_on_page"))] = s
    return {k: list(v.values()) for k, v in by_num.items()}


LOT_RE = re.compile(r"^SLQ-(\d{8}|\d{11})$", re.IGNORECASE)


def is_plausible_lot(lot: str | None) -> bool:
    """True only for a well-formed Silq lot: SLQ- plus a date or an 11-digit code.

    Used to vet repair candidates. A candidate that is not a well-formed lot is
    never written, even when it is the only thing the source document offers.
    """
    return bool(LOT_RE.match((lot or "").strip()))


def is_bad_lot(lot: str | None, order_number: str, sku: str | None) -> bool:
    """True when a lot value is not a lot at all.

    Three corruptions are present in the live data: the field was left as
    ``UNKNOWN``, the lot was truncated to its ``SLQ-`` prefix, or the order
    number / SKU was written into the lot field instead of the lot.
    """
    v = (lot or "").strip().upper()
    if not v or v in {"UNKNOWN", "N/A", "NA", "TBD", "NONE"}:
        return True
    if v.rstrip("-") == "SLQ":
        return True
    tail = v[4:] if v.startswith("SLQ-") else v
    if sku and tail == sku.strip().upper():
        return True
    digits = "".join(ch for ch in tail if ch.isdigit())
    if digits and digits.zfill(7) == order_number:
        return True
    return False


def device_units(o: dict) -> int:
    return sum(l["units"] for l in o["lines"] if l["is_device"])


def correct_lines(o: dict) -> list[dict]:
    dev = [l for l in o["lines"] if l["is_device"]]
    return [
        {"sku": l["sku"], "quantity": int(l["units"]), "line_number": i + 1}
        for i, l in enumerate(dev)
    ]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true", help="apply changes")
    ap.add_argument("--only", default="", help="comma list of tasks: A,B,C,D,E")
    args = ap.parse_args()
    dry = not args.execute
    only = {t.strip().upper() for t in args.only.split(",") if t.strip()} or {
        "F", "A", "B", "C", "D", "E"
    }

    os.environ.setdefault("FLASK_ENV", "production")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.models import (
        DistributionLogEntry,
        SalesOrder,
        SalesOrderLine,
    )
    from app.eqms.modules.rep_traceability.service import (
        delete_distribution_entry,
        find_sales_order_by_normalized_number,
        find_unique_customer_for_distribution_ship_to,
        rematch_unmatched_distributions_for_order,
    )

    def resolve_customer_id(entry) -> int | None:
        """Customer for a distribution via the system's address-keyed identity.

        Deliberately not a facility-name match: the ShipStation ship-to names are
        free text and several differ from the customer record for the same site.
        """
        if entry.customer_id:
            return entry.customer_id
        try:
            return find_unique_customer_for_distribution_ship_to(s, entry).id
        except Exception:
            return None

    auth = load_authority()
    slips = load_slips()

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User)
            .filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", "")))
            .first()
            or s.query(User).order_by(User.id).first()
        )
        if not actor:
            say("ERROR: no user found to attribute changes to; aborting.")
            sys.exit(1)

        say("=" * 100)
        say(f"DISTRIBUTION CLEANUP  mode={'DRY RUN' if dry else 'EXECUTE'}  tasks={sorted(only)}")
        say(f"actor={actor.email}  started={datetime.now().isoformat(timespec='seconds')}")
        say("=" * 100)

        # ---------------------------------------------------------------- F
        # Link distributions that carry no customer. Runs first because tasks B
        # and D need the customer to exist on the distribution.
        if "F" in only:
            say("\n[F] LINK DISTRIBUTIONS TO CUSTOMERS")
            unlinked = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.customer_id.is_(None))
                .order_by(DistributionLogEntry.order_number, DistributionLogEntry.id)
                .all()
            )
            say(f"    {len(unlinked)} distribution(s) have no customer")
            linked_c = 0
            unresolved: list[tuple] = []
            for d in unlinked:
                cid = resolve_customer_id(d)
                if not cid:
                    unresolved.append(
                        (d.id, d.order_number, d.facility_name, d.address1, d.city, d.state, d.zip)
                    )
                    continue
                cust = s.get(Customer, cid)
                say(
                    f"  dist {d.id} {d.order_number} {d.facility_name!r} "
                    f"-> customer {cid} {cust.facility_name!r}"
                )
                if not dry:
                    d.customer_id = cid
                    d.updated_by_user_id = actor.id
                    s.flush()
                linked_c += 1
            say(f"  -> {linked_c} distribution(s) linked")
            if unresolved:
                say(f"  -> {len(unresolved)} NEED A NEW CUSTOMER RECORD (not created here):")
                for row in unresolved:
                    say("       dist {} {} {!r}".format(row[0], row[1], row[2]))
                    say("            {}, {}, {} {}".format(row[3], row[4], row[5], row[6]))

        # ---------------------------------------------------------------- A
        # Correct sales_order_lines quantities against the sales order PDFs.
        if "A" in only:
            say("\n[A] SALES ORDER LINE QUANTITY CORRECTIONS")
            fixed = skipped_unsupported = 0
            before_tot = after_tot = 0
            for num, o in sorted(auth.items()):
                if any(
                    l["item_code"] in UNSUPPORTED_ITEM_CODES for l in o["lines"]
                ):
                    skipped_unsupported += 1
                    continue
                want = correct_lines(o)
                if not want:
                    continue
                so = find_sales_order_by_normalized_number(s, num)
                if not so:
                    continue
                cur = list(so.lines or [])
                cur_sig = tuple(sorted((l.sku, l.quantity) for l in cur))
                new_sig = tuple(sorted((l["sku"], l["quantity"]) for l in want))
                if cur_sig == new_sig:
                    continue
                before_tot += sum(l.quantity for l in cur)
                after_tot += sum(l["quantity"] for l in want)
                say(
                    f"  {num}: {sum(l.quantity for l in cur):4d}u -> "
                    f"{sum(l['quantity'] for l in want):4d}u   "
                    f"[{', '.join(f'{a}x{b}' for a, b in cur_sig)}] -> "
                    f"[{', '.join(f'{a}x{b}' for a, b in new_sig)}]  ({o['source_pdf']}#p{o['page']})"
                )
                if not dry:
                    for l in cur:
                        s.delete(l)
                    s.flush()
                    for w in want:
                        s.add(
                            SalesOrderLine(
                                sales_order_id=so.id,
                                sku=w["sku"],
                                quantity=w["quantity"],
                                line_number=w["line_number"],
                            )
                        )
                    s.flush()
                fixed += 1
            say(f"  -> {fixed} orders corrected; ordered units {before_tot} -> {after_tot}")
            say(f"  -> {skipped_unsupported} orders skipped (20/22 Fr SKUs not supported)")

        # ---------------------------------------------------------------- B
        # Create sales orders that exist on paper but are missing from the DB.
        if "B" in only:
            say("\n[B] CREATE MISSING SALES ORDERS")
            created = 0
            for num, o in sorted(auth.items()):
                if find_sales_order_by_normalized_number(s, num):
                    continue
                want = correct_lines(o)
                if not want:
                    continue
                if any(l["item_code"] in UNSUPPORTED_ITEM_CODES for l in o["lines"]):
                    say(f"  {num}: SKIP (20/22 Fr SKU not supported)")
                    continue
                # Customer comes from a distribution already recorded for this order.
                cust_id = None
                for d in (
                    s.query(DistributionLogEntry)
                    .filter(DistributionLogEntry.order_number.ilike(f"%{num}%"))
                    .all()
                ):
                    cust_id = resolve_customer_id(d)
                    if cust_id:
                        break
                if not cust_id:
                    say(f"  {num}: SKIP (no customer resolvable from distributions)")
                    continue
                od = datetime.strptime(o["order_date"], "%m/%d/%Y").date()
                detail = ", ".join("{}x{}".format(w["sku"], w["quantity"]) for w in want)
                say(
                    f"  {num}: CREATE date={od} customer_id={cust_id} "
                    f"units={sum(w['quantity'] for w in want)} [{detail}]"
                )
                if not dry:
                    so = SalesOrder(
                        order_number=num,
                        order_date=od,
                        customer_id=cust_id,
                        source="pdf_import",
                        status="completed",
                        created_by_user_id=actor.id,
                        updated_by_user_id=actor.id,
                    )
                    s.add(so)
                    s.flush()
                    for w in want:
                        s.add(
                            SalesOrderLine(
                                sales_order_id=so.id,
                                sku=w["sku"],
                                quantity=w["quantity"],
                                line_number=w["line_number"],
                            )
                        )
                    s.flush()
                created += 1
            say(f"  -> {created} sales orders created")

        # ---------------------------------------------------------------- C
        # Delete duplicate distribution rows confirmed against packing slips.
        if "C" in only:
            say("\n[C] DELETE DUPLICATE DISTRIBUTIONS")
            say("    protected genuine multi-package orders: "
                + ", ".join(f"{k} ({v})" for k, v in PROTECTED_MULTI_PACKAGE.items()))
            removed = 0
            for drop_id, keep_id, num, evidence in CONFIRMED_DUPLICATES:
                if num in PROTECTED_MULTI_PACKAGE:
                    say(f"  {num}: REFUSING - order is protected as multi-package")
                    continue
                drop = s.get(DistributionLogEntry, drop_id)
                keep = s.get(DistributionLogEntry, keep_id)
                if not drop:
                    say(f"  dist {drop_id} ({num}): already absent, nothing to do")
                    continue
                if not keep:
                    say(f"  dist {drop_id} ({num}): SKIP - keeper {keep_id} missing")
                    continue
                dunits = sum(l.quantity for l in (drop.lines or [])) or drop.quantity
                kunits = sum(l.quantity for l in (keep.lines or [])) or keep.quantity
                say(
                    f"  {num}: DROP dist {drop_id} ({dunits}u, ship={drop.ss_shipment_id}) "
                    f"KEEP dist {keep_id} ({kunits}u, ship={keep.ss_shipment_id})"
                )
                say(f"        evidence: {evidence}")
                if not dry:
                    delete_distribution_entry(
                        s, drop, user=actor, reason=f"{REASON}. Duplicate of #{keep_id}. {evidence}"
                    )
                removed += 1
            say(f"  -> {removed} duplicate distributions removed")

        # ---------------------------------------------------------------- D
        # Re-link orphaned distributions to their sales orders.
        if "D" in only:
            say("\n[D] RE-LINK ORPHANED DISTRIBUTIONS")
            orphan_nums = sorted(
                {
                    "".join(ch for ch in (d.order_number or "") if ch.isdigit()).zfill(7)
                    for d in s.query(DistributionLogEntry)
                    .filter(DistributionLogEntry.sales_order_id.is_(None))
                    .all()
                }
            )
            linked = 0
            for num in orphan_nums:
                so = find_sales_order_by_normalized_number(s, num)
                if not so:
                    say(f"  {num}: no sales order to link to")
                    continue
                if dry:
                    cnt = (
                        s.query(DistributionLogEntry)
                        .filter(
                            DistributionLogEntry.sales_order_id.is_(None),
                            DistributionLogEntry.order_number.ilike(f"%{num}%"),
                        )
                        .count()
                    )
                    if cnt:
                        say(f"  {num}: would link {cnt} distribution(s) to SO #{so.id}")
                        linked += cnt
                    continue
                n = rematch_unmatched_distributions_for_order(s, so)
                if n:
                    say(f"  {num}: linked {n} distribution(s) to SO #{so.id}")
                    linked += n
            say(f"  -> {linked} distributions linked")

        # ---------------------------------------------------------------- E
        # Repair lot numbers using packing slip evidence.
        if "E" in only:
            say("\n[E] REPAIR LOT NUMBERS")
            repaired = manual = 0
            for d in sorted(s.query(DistributionLogEntry).all(), key=lambda x: x.ship_date or ""):
                num = "".join(ch for ch in (d.order_number or "") if ch.isdigit()).zfill(7)
                targets = [(None, d)] + [(ln.id, ln) for ln in (d.lines or [])]
                for line_id, obj in targets:
                    if not is_bad_lot(obj.lot_number, num, obj.sku):
                        continue
                    # Only direct documentary evidence: a packing slip lot for
                    # this same order and SKU. A lot is not inferred from other
                    # shipments on the same date - a wrong lot would misdirect a
                    # recall, which is worse than a recorded UNKNOWN.
                    cands = {
                        l["lot"].strip()
                        for sl in slips.get(num, [])
                        for l in sl["lines"]
                        if l["sku"] == obj.sku and is_plausible_lot(l.get("lot"))
                    }
                    where = f"dist {d.id}" if line_id is None else f"dist {d.id} line {line_id}"
                    say(
                        f"  {where} order={num} {obj.sku} x{obj.quantity} "
                        f"{d.ship_date} lot={obj.lot_number!r}"
                    )
                    if len(cands) == 1:
                        newlot = cands.pop()
                        if not dry:
                            obj.lot_number = newlot
                            s.flush()
                        say(f"        -> set lot {newlot}")
                        repaired += 1
                    else:
                        say(
                            "        -> MANUAL REVIEW (candidates: {})".format(
                                sorted(cands) or "none"
                            )
                        )
                        manual += 1
            say(f"  -> {repaired} lot numbers repaired, {manual} need manual review")

        if dry:
            s.rollback()
            say("\nDRY RUN - transaction rolled back, nothing written.")
        else:
            s.commit()
            say("\nCOMMITTED.")

    LOG.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\nlog -> {LOG}")


if __name__ == "__main__":
    main()
