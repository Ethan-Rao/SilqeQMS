"""Align customer profiles with the distribution log and sales dashboard.

Both the sales dashboard and the customer detail page key strictly on
``customer_id`` (D41: address-based identity, never facility name). Four classes
of defect break that keying; each task below fixes one and writes an audit event
through the normal service layer.

  M  merge duplicate profiles that describe one physical site
  V  move the two VA shipments that were credited to the wrong medical center
  N  normalise distribution order_number text so the dashboard stops
     double counting one order
  R  repair facility names that are misspelt or ambiguous

Dry run by default; pass --execute to write.

    python scripts/dist_customer_alignment_fix.py
    python scripts/dist_customer_alignment_fix.py --execute
    python scripts/dist_customer_alignment_fix.py --only M,V --execute
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

LOG: list[str] = []


def say(msg: str = "") -> None:
    print(msg, flush=True)
    LOG.append(msg)


# --------------------------------------------------------------------------- M
# (master, duplicate). Master is the curated profile: it holds the customer_code
# and/or the bulk of the history. The duplicate was auto-created from a
# ShipStation ship-to whose street text differed enough to miss the address key.
MERGES = [
    # 7601 E Imperial Parkway == 7601 Imperial Hwy, Downey CA 90242
    (609, 692, "Rancho Los Amigos: '7601 E Imperial Parkway' and '7601 IMPERIAL HWY' "
               "are the same Downey CA 90242 site; Imperial Hwy and Imperial Pkwy "
               "are the same road."),
    # 3300 Westhill Dr == 330 Westhill Drive (dropped digit), Wausau WI 54401
    (614, 691, "Aspirus Wausau: '330 WESTHILL DRIVE' is a dropped-digit variant of "
               "'3300 Westhill Dr.', same Wausau WI 54401 site."),
    # 751 S Bascom Ave, San Jose CA 95128 -- duplicate carried a floor/dept suffix
    (630, 713, "Santa Clara Valley Medical Center: duplicate address carried the "
               "'# 4th FLR Urology' suite suffix, same 751 S Bascom Ave site."),
    # N Shore Drive (no street number) == 2251 N Shore Dr, Rhinelander WI 54501
    (657, 707, "Aspirus Rhinelander Urology: master address was missing its street "
               "number ('N Shore Drive'), duplicate has the full '2251 N SHORE DR'."),
    # 'Gina Koehler' is the contact at Cleveland Clinic, not a separate facility.
    (704, 771, "Cleveland Clinic Foundation: profile #771 was filed under the "
               "contact's name 'Gina Koehler' with the misspelt street "
               "'9500 Euclid Avneue', carries customer_code 'CCF', and its "
               "shipment went to 9500 EUCLID AVE, Cleveland OH 44195-0002 -- the "
               "same site as #704."),
]

# merge_customers() fills only empty fields and does not carry customer_code, so
# payer codes worth keeping are restated here.
CODE_CARRYOVER = {704: "CCF"}

# Address repairs applied after the merges. Each adopts the USPS-standardised
# form that the shipping records carry, so a later import of the same site keys
# to the surviving profile instead of creating the duplicate again.
ADDRESS_REPAIRS = [
    {
        "customer_id": 657,
        "address1": "2251 N Shore Dr",
        "zip": "54501-6710",
        "reason": "Address was stored without its street number, so the address key "
                  "could never match a ShipStation ship-to. Completed from the "
                  "merged duplicate profile #707.",
    },
    {
        "customer_id": 609,
        "address1": "7601 Imperial Hwy",
        "zip": "90242-3496",
        "reason": "All 30 shipments to this site carry the USPS-validated form "
                  "'7601 IMPERIAL HWY, DOWNEY CA 90242-3496', which is also the "
                  "facility's official address. The stored '7601 E Imperial "
                  "Parkway' keyed to nothing the shipping system emits, which is "
                  "how duplicate profile #692 came to exist.",
    },
]

# --------------------------------------------------------------------------- V
# Sales order PDFs for 0000198 / 0000209 read "SHIP TO: VAMC - LOMA LINDA", but
# both packing slips and the ShipStation label show the goods went to VA Long
# Beach. The consignee is what 21 CFR 820.160 records, so these belong to #622.
VA_MOVE = {
    "from_customer_id": 628,
    "to_customer_id": 622,
    "distribution_ids": [785, 796],
    "order_numbers": ["0000198", "0000209"],
    "consignee": "VA LONG BCH. HEALTHCARE SYS.",
    "reason": "Packing slips (Jul25PackingSlips.pdf p5, Aug25PackingSlips.pdf p2) "
              "and the ShipStation label both show ship-to 'VA LONG BCH. "
              "HEALTHCARE SYS., 5901 E 7TH ST BLDG 149, LONG BEACH CA 90822-5201' "
              "(contact Biancia.Yarbrough@va.gov). The sales order Ship To block "
              "reads 'VAMC - LOMA LINDA' and is contradicted by the shipping "
              "records; the distribution record follows the actual consignee.",
}

# --------------------------------------------------------------------------- N
# dist 933's slip is printed as SO 0000334 but annotated by hand "This was
# shipped against SO 0000335!", and no sales order 0000334 exists in any export.
# Its sales_order_id already points at 0000335; only the text was left stale.
ORDER_NUMBER_OVERRIDES = {
    933: ("SO 0000335", "Packing slip (May26PackingSlips.pdf p6) is printed "
                        "'SO 0000334' but annotated 'This was shipped against "
                        "SO 0000335!'. No sales order 0000334 exists in any "
                        "export; sales_order_id already points at 0000335."),
}

# 'SO 00001129' has eight digits and no sales order link, so the intended order
# cannot be determined from the data. Left untouched and reported instead.
ORDER_NUMBER_SKIP = {"SO 00001129"}

CANONICAL_RE = re.compile(r"^SO \d{7}$")


def canonical_order_number(raw: str) -> str | None:
    """Return the canonical 'SO 0000123' form, or None if it cannot be derived."""
    digits = re.sub(r"\D", "", raw or "")
    if not digits:
        return None
    # Order numbers are seven digits; strip accidental leading zero padding.
    trimmed = digits.lstrip("0").zfill(7)
    if len(trimmed) != 7:
        return None
    return f"SO {trimmed}"


# --------------------------------------------------------------------------- R
# Renames. Each either fixes a misspelling or disambiguates two profiles that
# share a name but are different physical sites.
RENAMES = [
    (625, "Aspirus Wisconsin Rapids",
     "Facility name was the misspelt city 'Wiscosin Rapids'. Confirmed as the "
     "Aspirus site at 400 Dewey St, Wisconsin Rapids WI."),
    (677, "Temple University Health System - Fort Washington",
     "Shared the exact name of #651 (333 Cottman Ave, Philadelphia) while being "
     "a different site (515 Pennsylvania Ave, Fort Washington), making the two "
     "indistinguishable on the dashboard."),
    (668, "University Of Michigan - Brighton",
     "Shared the exact name of #643 (1500 E Medical Center Dr, Ann Arbor) while "
     "being a different site (7500 Challis Rd, Brighton), making the two "
     "indistinguishable on the dashboard."),
]


def full_payload(c) -> dict:
    """update_customer() treats absent keys as cleared, so send every field."""
    return {
        "facility_name": c.facility_name,
        "address1": c.address1,
        "address2": c.address2,
        "city": c.city,
        "state": c.state,
        "zip": c.zip,
        "sold_to_address1": c.sold_to_address1,
        "sold_to_city": c.sold_to_city,
        "sold_to_state": c.sold_to_state,
        "sold_to_zip": c.sold_to_zip,
        "contact_name": c.contact_name,
        "contact_phone": c.contact_phone,
        "contact_email": c.contact_email,
        "primary_rep_id": str(c.primary_rep_id or ""),
        "is_distributor": bool(c.is_distributor),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--only", default="", help="comma list of task letters, e.g. M,V")
    args = ap.parse_args()
    dry = not args.execute
    only = {t.strip().upper() for t in args.only.split(",") if t.strip()}

    def want(task: str) -> bool:
        return not only or task in only

    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.customer_profiles.service import merge_customers, update_customer
    from app.eqms.modules.customer_profiles.utils import compute_facility_key_from_ship_to
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )
        say("=" * 92)
        say(f"CUSTOMER PROFILE ALIGNMENT   mode={'DRY RUN' if dry else 'EXECUTE'}")
        say(f"actor={actor.email}  {datetime.now().isoformat(timespec='seconds')}")
        say("=" * 92)

        # ------------------------------------------------------- M: merge dupes
        if want("M"):
            say()
            say("-- M: merge duplicate profiles ------------------------------------------")
            for master_id, dup_id, reason in MERGES:
                master = s.get(Customer, master_id)
                dup = s.get(Customer, dup_id)
                if dup is None:
                    say(f"   #{dup_id} already merged away; skipping")
                    continue
                nd = s.query(DistributionLogEntry).filter(
                    DistributionLogEntry.customer_id == dup_id).count()
                no = s.query(SalesOrder).filter(SalesOrder.customer_id == dup_id).count()
                say(f"   #{dup_id} {dup.facility_name!r} ({nd} dists, {no} orders)")
                say(f"     -> #{master_id} {master.facility_name!r}")
                say(f"     {reason}")
                if not dry:
                    merge_customers(s, master_id=master_id, duplicate_id=dup_id, user=actor)
                    record_event(
                        s,
                        actor=actor,
                        action="customer.merge.rationale",
                        entity_type="Customer",
                        entity_id=str(master_id),
                        reason=reason,
                        metadata={"duplicate_id": dup_id, "distributions_moved": nd,
                                  "sales_orders_moved": no},
                    )
                    s.commit()

            for cid, code in CODE_CARRYOVER.items():
                c = s.get(Customer, cid)
                if c is None or c.customer_code == code:
                    continue
                say(f"   #{cid} customer_code: {c.customer_code!r} -> {code!r} "
                    "(carried over from the merged duplicate)")
                if not dry:
                    before = c.customer_code
                    c.customer_code = code
                    record_event(
                        s,
                        actor=actor,
                        action="customer.customer_code.set",
                        entity_type="Customer",
                        entity_id=str(cid),
                        reason="Payer code preserved from the merged duplicate profile.",
                        metadata={"before": before, "after": code},
                    )
                    s.commit()

            # Adopt the shipped address form now that the duplicates are gone.
            for rep in ADDRESS_REPAIRS:
                c = s.get(Customer, rep["customer_id"])
                if c is None or c.address1 == rep["address1"]:
                    say(f"   #{rep['customer_id']}: address already correct; skipping")
                    continue
                new_key = compute_facility_key_from_ship_to(
                    address1=rep["address1"], city=c.city, state=c.state,
                    zip=rep["zip"], facility_name=c.facility_name)
                clash = (
                    s.query(Customer)
                    .filter(Customer.company_key == new_key, Customer.id != c.id)
                    .first()
                )
                if clash is not None:
                    say(f"   #{c.id}: new key {new_key!r} already held by #{clash.id}; skipping")
                    continue
                say()
                say(f"   #{c.id} address repair: {c.address1!r} -> {rep['address1']!r}")
                say(f"     company_key {c.company_key!r} -> {new_key!r}")
                say(f"     {rep['reason']}")
                if not dry:
                    payload = full_payload(c)
                    payload["address1"] = rep["address1"]
                    payload["zip"] = rep["zip"]
                    update_customer(s, c, payload, user=actor, reason=rep["reason"])
                    old_key = c.company_key
                    c.company_key = new_key
                    record_event(
                        s,
                        actor=actor,
                        action="customer.company_key.recompute",
                        entity_type="Customer",
                        entity_id=str(c.id),
                        reason="Address key recomputed after adopting the shipped "
                               "address form.",
                        metadata={"before": old_key, "after": new_key},
                    )
                    s.commit()

        # --------------------------------------------- V: correct VA consignee
        if want("V"):
            say()
            say("-- V: move VA shipments to the actual consignee --------------------------")
            src = s.get(Customer, VA_MOVE["from_customer_id"])
            dst = s.get(Customer, VA_MOVE["to_customer_id"])
            say(f"   from #{src.id} {src.facility_name!r}")
            say(f"   to   #{dst.id} {dst.facility_name!r}  ({dst.address1}, {dst.city})")
            say(f"   {VA_MOVE['reason']}")
            for did in VA_MOVE["distribution_ids"]:
                d = s.get(DistributionLogEntry, did)
                if d is None or d.customer_id == VA_MOVE["to_customer_id"]:
                    say(f"   dist {did}: already correct; skipping")
                    continue
                say(f"   dist {did} {d.order_number} {d.ship_date} x{d.quantity}: "
                    f"customer #{d.customer_id} -> #{dst.id}, "
                    f"facility {d.facility_name!r} -> {VA_MOVE['consignee']!r}")
                if not dry:
                    before = {"customer_id": d.customer_id, "facility_name": d.facility_name}
                    d.customer_id = VA_MOVE["to_customer_id"]
                    d.facility_name = VA_MOVE["consignee"]
                    record_event(
                        s,
                        actor=actor,
                        action="distribution.customer.correct",
                        entity_type="DistributionLogEntry",
                        entity_id=str(d.id),
                        reason=VA_MOVE["reason"],
                        metadata={"before": before,
                                  "after": {"customer_id": d.customer_id,
                                            "facility_name": d.facility_name}},
                    )
            for num in VA_MOVE["order_numbers"]:
                so = s.query(SalesOrder).filter(SalesOrder.order_number == num).first()
                if so is None or so.customer_id == VA_MOVE["to_customer_id"]:
                    say(f"   SO {num}: already correct or absent; skipping")
                    continue
                say(f"   SO {num}: customer #{so.customer_id} -> #{dst.id} "
                    "(keeps the order with its shipment on one profile)")
                if not dry:
                    before = so.customer_id
                    so.customer_id = VA_MOVE["to_customer_id"]
                    record_event(
                        s,
                        actor=actor,
                        action="sales_order.customer.correct",
                        entity_type="SalesOrder",
                        entity_id=str(so.id),
                        reason=VA_MOVE["reason"],
                        metadata={"before": {"customer_id": before},
                                  "after": {"customer_id": so.customer_id}},
                    )
            if not dry:
                s.commit()

        # ------------------------------- N: normalise order_number text on dists
        if want("N"):
            say()
            say("-- N: normalise distribution order_number text ---------------------------")
            changed = 0
            for d in s.query(DistributionLogEntry).order_by(DistributionLogEntry.id).all():
                raw = d.order_number or ""
                if not raw or raw in ORDER_NUMBER_SKIP:
                    continue
                if d.id in ORDER_NUMBER_OVERRIDES:
                    new, reason = ORDER_NUMBER_OVERRIDES[d.id]
                else:
                    if CANONICAL_RE.match(raw):
                        continue
                    new = canonical_order_number(raw)
                    reason = ("Order number text normalised to the canonical "
                              "'SO 0000000' form so the dashboard counts one order once.")
                    if new is None:
                        say(f"   dist {d.id}: cannot canonicalise {raw!r}; left as is")
                        continue
                if new == raw:
                    continue
                linked = s.get(SalesOrder, d.sales_order_id) if d.sales_order_id else None
                flag = ""
                if linked and canonical_order_number(linked.order_number) != new:
                    flag = f"  [linked SO is {linked.order_number}]"
                say(f"   dist {d.id}: {raw!r} -> {new!r}{flag}")
                changed += 1
                if not dry:
                    record_event(
                        s,
                        actor=actor,
                        action="distribution.order_number.normalize",
                        entity_type="DistributionLogEntry",
                        entity_id=str(d.id),
                        reason=reason,
                        metadata={"before": raw, "after": new},
                    )
                    d.order_number = new
            say(f"   rows to change: {changed}")
            for skipped in sorted(ORDER_NUMBER_SKIP):
                say(f"   left for manual review: {skipped!r} (8 digits, no order link)")
            if not dry:
                s.commit()

        # ------------------------------------------------- R: facility renames
        if want("R"):
            say()
            say("-- R: repair facility names ----------------------------------------------")
            for cid, new_name, reason in RENAMES:
                c = s.get(Customer, cid)
                if c is None or c.facility_name == new_name:
                    say(f"   #{cid}: already correct or absent; skipping")
                    continue
                say(f"   #{cid}: {c.facility_name!r} -> {new_name!r}")
                say(f"     {reason}")
                if not dry:
                    payload = full_payload(c)
                    payload["facility_name"] = new_name
                    update_customer(s, c, payload, user=actor, reason=reason)
            if not dry:
                s.commit()

        say()
        say("=" * 92)
        say("DRY RUN -- nothing written" if dry else "EXECUTED")
        say("=" * 92)

    out = ROOT / "_dist_alignment_log.txt"
    out.write_text("\n".join(LOG), encoding="utf-8")
    print(f"\nlog: {out}")


if __name__ == "__main__":
    main()
