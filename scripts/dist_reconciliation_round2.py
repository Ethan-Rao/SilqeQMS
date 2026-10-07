"""Second round of distribution reconciliation fixes, 7 Oct 2026.

Tasks, each independently selectable with --only:

  L  the last two lot questions, now answered from the manufacturing records
  C  merge Carolinas Rehabilitation into Carolinas Healthcare System
  A  adopt the shipped address on profiles whose stored address cannot key
  O  create sales order 0000145 from its PDF and link its two shipments

Dry run by default; pass --execute to write.

    python scripts/dist_reconciliation_round2.py
    python scripts/dist_reconciliation_round2.py --execute
    python scripts/dist_reconciliation_round2.py --only A --execute
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

# --------------------------------------------------------------------------- L
# line_id -> (lot, rationale)
LOT_CORRECTIONS = {
    1456: ("SLQ-81020515241",
           "Confirmed from manufacturing records: the 18 Fr on SO 0000323 was "
           "picked from SLQ-81020515241."),
    1295: ("SLQ-05012025",
           "'SLQ-05021025' is not a real lot. It was first read as a misprint of "
           "SLQ-05022025, but both affected lines are 16 Fr and SLQ-05022025 is "
           "the 18 Fr lot. Confirmed as SLQ-05012025, the 16 Fr lot of that "
           "vintage, which matches the SKU on the line."),
    1337: ("SLQ-05012025",
           "'SLQ-05021025' is not a real lot. It was first read as a misprint of "
           "SLQ-05022025, but both affected lines are 16 Fr and SLQ-05022025 is "
           "the 18 Fr lot. Confirmed as SLQ-05012025, the 16 Fr lot of that "
           "vintage, which matches the SKU on the line."),
}

# --------------------------------------------------------------------------- C
CAROLINAS_MERGE = (652, 658,
                   "Carolinas Rehabilitation (#658, stored 1100 Blythe Blvd) and "
                   "Carolinas Healthcare System (#652, stored with no street at "
                   "all) both shipped to 1000 BLYTHE BLVD, Charlotte NC "
                   "28203-5812. Confirmed as one site.")

# --------------------------------------------------------------------------- O
SO_145 = {
    "order_number": "0000145",
    "order_date": date(2024, 12, 13),
    "customer_id": 635,          # VAMC-San Diego Healthcare, the actual consignee
    "sku": "211810SPT",
    "quantity": 50,              # 5 x Box of 10
    "order_amount": "1764.00",
    "distribution_ids": [887, 753],   # 20 units Dec-2024 + 30 units Feb-2025
    "source_pdf": "Silq SO_SalesOrders 145.pdf",
    "reason": "Sales order recovered from its source PDF. The SHIP TO block "
              "prints Marathon Medical's own Aurora CO address because Marathon "
              "is the distributor of record; both shipments went to VAMC San "
              "Diego, so the order is filed against the consignee. The 5 boxes "
              "of 10 reconcile exactly with the 20 and 30 unit shipments.",
}

LOG: list[str] = []


def say(msg: str = "") -> None:
    print(msg, flush=True)
    LOG.append(msg)


def as_date(v):
    if v is None or isinstance(v, date):
        return v
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except ValueError:
            continue
    return None


def street_number(addr: str | None) -> str:
    m = re.match(r"\s*(\d+)", addr or "")
    return m.group(1) if m else ""


def zip5(z: str | None) -> str:
    return re.sub(r"\D", "", z or "")[:5]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    dry = not args.execute
    only = {t.strip().upper() for t in args.only.split(",") if t.strip()}

    def want(t: str) -> bool:
        return not only or t in only

    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.customer_profiles.service import merge_customers, update_customer
    from app.eqms.modules.customer_profiles.utils import compute_facility_key_from_ship_to
    from app.eqms.modules.rep_traceability.models import (
        DistributionLine,
        DistributionLogEntry,
        SalesOrder,
        SalesOrderLine,
    )
    from app.eqms.modules.shipstation_sync.parsers import (
        load_lot_dates,
        load_lot_log_with_inventory,
        resolve_lotlog_path,
    )

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )
        say("=" * 92)
        say(f"RECONCILIATION ROUND 2   mode={'DRY RUN' if dry else 'EXECUTE'}")
        say(f"actor={actor.email}  {datetime.now().isoformat(timespec='seconds')}")
        say("=" * 92)

        # ------------------------------------------------------------- L: lots
        if want("L"):
            say()
            say("-- L: remaining lot corrections -----------------------------------------")
            lot_to_sku, _c, lot_inv, _y = load_lot_log_with_inventory(resolve_lotlog_path())
            lot_mfg, _e = load_lot_dates(resolve_lotlog_path())
            for line_id, (lot, reason) in LOT_CORRECTIONS.items():
                line = s.get(DistributionLine, line_id)
                if line is None:
                    say(f"   line {line_id}: NOT FOUND; skipping")
                    continue
                if (line.lot_number or "").upper() == lot.upper():
                    say(f"   line {line_id}: already {lot}; skipping")
                    continue
                entry = s.get(DistributionLogEntry, line.distribution_entry_id)
                reg = lot_to_sku.get(lot.upper())
                if not reg or reg.upper() != (line.sku or "").upper():
                    say(f"   line {line_id}: BLOCKED -- {lot} registered to {reg}, "
                        f"line is {line.sku}")
                    continue
                mfg = as_date(lot_mfg.get(lot.upper()))
                if mfg and entry.ship_date and mfg > entry.ship_date:
                    say(f"   line {line_id}: BLOCKED -- {lot} made {mfg}, after "
                        f"{entry.ship_date}")
                    continue
                primary = (entry.sku or "").upper() == (line.sku or "").upper()
                say(f"   line {line_id} dist {entry.id} {entry.order_number} "
                    f"{entry.ship_date} {line.sku} x{line.quantity}")
                say(f"      lot {line.lot_number!r} -> {lot!r} (LotLog: {reg}, made {mfg})")
                if primary:
                    say(f"      entry header lot {entry.lot_number!r} -> {lot!r}")
                if not dry:
                    before = {"line_lot": line.lot_number, "entry_lot": entry.lot_number}
                    line.lot_number = lot
                    if primary:
                        entry.lot_number = lot
                    record_event(
                        s, actor=actor, action="distribution.lot.correct",
                        entity_type="DistributionLine", entity_id=str(line.id),
                        reason=reason,
                        metadata={"before": before,
                                  "after": {"line_lot": line.lot_number,
                                            "entry_lot": entry.lot_number},
                                  "distribution_entry_id": entry.id,
                                  "order_number": entry.order_number,
                                  "sku": line.sku, "quantity": line.quantity,
                                  "lotlog_sku": reg},
                    )
            if not dry:
                s.commit()

        # -------------------------------------------------------- C: Carolinas
        if want("C"):
            say()
            say("-- C: merge Carolinas profiles ------------------------------------------")
            master_id, dup_id, reason = CAROLINAS_MERGE
            dup = s.get(Customer, dup_id)
            if dup is None:
                say(f"   #{dup_id} already merged away; skipping")
            else:
                master = s.get(Customer, master_id)
                nd = s.query(DistributionLogEntry).filter(
                    DistributionLogEntry.customer_id == dup_id).count()
                no = s.query(SalesOrder).filter(SalesOrder.customer_id == dup_id).count()
                say(f"   #{dup_id} {dup.facility_name!r} ({nd} dists, {no} orders)")
                say(f"     -> #{master_id} {master.facility_name!r}")
                say(f"     {reason}")
                if not dry:
                    merge_customers(s, master_id=master_id, duplicate_id=dup_id, user=actor)
                    record_event(
                        s, actor=actor, action="customer.merge.rationale",
                        entity_type="Customer", entity_id=str(master_id),
                        reason=reason,
                        metadata={"duplicate_id": dup_id, "distributions_moved": nd,
                                  "sales_orders_moved": no},
                    )
                    s.commit()

        # --------------------------------------------------------- A: addresses
        if want("A"):
            say()
            say("-- A: adopt the shipped address where the stored one cannot key ---------")
            say("   (groups A and B of the drift report: no street number, or the same")
            say("    street number and ZIP with different spelling)")
            changed = 0
            for c in s.query(Customer).order_by(Customer.id).all():
                ds = s.query(DistributionLogEntry).filter(
                    DistributionLogEntry.customer_id == c.id).all()
                if not ds:
                    continue
                addrs = collections.Counter()
                keys = set()
                for d in ds:
                    if not (d.address1 or "").strip():
                        continue
                    addrs[(d.address1, d.city, d.state, d.zip)] += 1
                    try:
                        keys.add(compute_facility_key_from_ship_to(
                            address1=d.address1, city=d.city, state=d.state, zip=d.zip,
                            facility_name=d.facility_name))
                    except Exception:
                        pass
                if not addrs or c.company_key in keys:
                    continue
                (a1, city, st, zp), n = addrs.most_common(1)[0]
                # Group A: stored address has no street number at all.
                # Group B: same street number and ZIP5, different spelling.
                group = None
                if not street_number(c.address1):
                    group = "A"
                elif (street_number(c.address1) == street_number(a1)
                      and zip5(c.zip) == zip5(zp)):
                    group = "B"
                if group is None:
                    continue

                new_key = compute_facility_key_from_ship_to(
                    address1=a1, city=city, state=st, zip=zp, facility_name=c.facility_name)
                clash = (
                    s.query(Customer)
                    .filter(Customer.company_key == new_key, Customer.id != c.id)
                    .first()
                )
                if clash is not None:
                    say(f"   #{c.id} {c.facility_name!r}: new key {new_key!r} already "
                        f"held by #{clash.id} {clash.facility_name!r}; skipping")
                    continue

                # A stored person's name is information worth keeping.
                moved_contact = None
                if (group == "A" and not (c.contact_name or "").strip()
                        and (c.address1 or "").strip()
                        and (c.address1 or "").strip().upper() != (c.facility_name or "").strip().upper()):
                    moved_contact = c.address1.strip()

                say(f"   [{group}] #{c.id} {c.facility_name!r}  ({n} of {sum(addrs.values())} shipments)")
                say(f"       addr {c.address1!r} -> {a1!r}")
                say(f"       city {c.city!r} {c.state!r} {c.zip!r} -> {city!r} {st!r} {zp!r}")
                say(f"       key  {c.company_key!r} -> {new_key!r}")
                if moved_contact:
                    say(f"       contact_name <- {moved_contact!r} (kept from the old address)")
                changed += 1

                if not dry:
                    payload = {
                        "facility_name": c.facility_name,
                        "address1": a1, "address2": c.address2,
                        "city": city, "state": st, "zip": zp,
                        "sold_to_address1": c.sold_to_address1,
                        "sold_to_city": c.sold_to_city,
                        "sold_to_state": c.sold_to_state,
                        "sold_to_zip": c.sold_to_zip,
                        "contact_name": moved_contact or c.contact_name,
                        "contact_phone": c.contact_phone,
                        "contact_email": c.contact_email,
                        "primary_rep_id": str(c.primary_rep_id or ""),
                        "is_distributor": bool(c.is_distributor),
                    }
                    old_key = c.company_key
                    update_customer(
                        s, c, payload, user=actor,
                        reason=f"Drift group {group}: stored Ship To did not key to the "
                               f"address its own shipments carry, so future imports of "
                               f"this site would create a duplicate profile. Adopted the "
                               f"USPS-validated form from the shipping record "
                               f"({n} of {sum(addrs.values())} shipments).",
                    )
                    c.company_key = new_key
                    record_event(
                        s, actor=actor, action="customer.company_key.recompute",
                        entity_type="Customer", entity_id=str(c.id),
                        reason="Address key recomputed after adopting the shipped address.",
                        metadata={"before": old_key, "after": new_key, "group": group},
                    )
            say(f"   profiles to change: {changed}")
            if not dry:
                s.commit()

        # ------------------------------------------------------- O: SO 0000145
        if want("O"):
            say()
            say("-- O: recover sales order 0000145 ---------------------------------------")
            spec = SO_145
            existing = s.query(SalesOrder).filter(
                SalesOrder.order_number == spec["order_number"]).first()
            if existing is not None:
                say(f"   SO {spec['order_number']} already exists as #{existing.id}; "
                    "checking links only")
                so = existing
            else:
                cust = s.get(Customer, spec["customer_id"])
                say(f"   CREATE SO {spec['order_number']} {spec['order_date']} "
                    f"cust #{cust.id} {cust.facility_name!r} "
                    f"[{spec['sku']} x{spec['quantity']}] ${spec['order_amount']}")
                say(f"     {spec['reason']}")
                so = None
                if not dry:
                    from decimal import Decimal
                    so = SalesOrder(
                        order_number=spec["order_number"],
                        order_date=spec["order_date"],
                        customer_id=spec["customer_id"],
                        source="pdf_import",
                        status="completed",
                        order_amount=Decimal(spec["order_amount"]),
                        created_by_user_id=actor.id,
                        updated_by_user_id=actor.id,
                    )
                    s.add(so)
                    s.flush()
                    s.add(SalesOrderLine(
                        sales_order_id=so.id, sku=spec["sku"],
                        quantity=spec["quantity"], line_number=1,
                    ))
                    s.flush()
                    record_event(
                        s, actor=actor,
                        action="sales_order.created_from_source_document",
                        entity_type="sales_order", entity_id=spec["order_number"],
                        reason=spec["reason"],
                        metadata={"order_date": str(spec["order_date"]),
                                  "customer_id": spec["customer_id"],
                                  "sku": spec["sku"], "quantity": spec["quantity"],
                                  "source_document": spec["source_pdf"]},
                    )
                    say(f"     -> SO #{so.id}")

            for did in spec["distribution_ids"]:
                d = s.get(DistributionLogEntry, did)
                if d is None:
                    say(f"   dist {did}: NOT FOUND")
                    continue
                if d.sales_order_id:
                    say(f"   dist {did}: already linked to SO id {d.sales_order_id}")
                    continue
                say(f"   dist {did} {d.order_number} {d.ship_date} x{d.quantity}: "
                    f"link to SO {spec['order_number']}")
                if not dry and so is not None:
                    d.sales_order_id = so.id
                    record_event(
                        s, actor=actor, action="distribution.sales_order_linked",
                        entity_type="DistributionLogEntry", entity_id=str(d.id),
                        reason=spec["reason"],
                        metadata={"order_number": spec["order_number"],
                                  "sales_order_id": so.id},
                    )
            if not dry:
                s.commit()

        say()
        say("=" * 92)
        say("DRY RUN -- nothing written" if dry else "EXECUTED")
        say("=" * 92)

    (ROOT / "_dist_round2_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
