"""Read-only audit of customer profiles against the distribution log and dashboard.

The sales dashboard and the customer detail page both key strictly on
``customer_id`` (D41: never on facility name). Anything that breaks that key
splits or misattributes a customer's history:

* a distribution whose customer differs from its own sales order's customer
* two customer profiles for one physical site, which double counts the customer
  and miscounts first-time vs repeat
* a distribution whose address resolves to a different customer than it is
  linked to

    python scripts/_dist_customer_alignment_audit.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

findings: list[tuple[str, str]] = []


def head(title: str) -> None:
    print()
    print("=" * 96)
    print(title)
    print("=" * 96)


def flag(sev: str, msg: str) -> None:
    findings.append((sev, msg))


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.customer_profiles.utils import (
        compute_facility_key_from_ship_to,
        normalize_street_for_key,
    )
    from app.eqms.modules.rep_traceability.models import (
        DistributionLogEntry,
        SalesOrder,
    )
    from app.eqms.modules.rep_traceability.service import (
        find_unique_customer_for_distribution_ship_to,
        sum_distribution_units,
    )

    app = create_app()
    with app.app_context():
        s = db_session()
        customers = s.query(Customer).all()
        by_id = {c.id: c for c in customers}
        dists = s.query(DistributionLogEntry).all()
        orders = s.query(SalesOrder).all()

        head("1. KEYING INTEGRITY (what the dashboard counts on)")
        d_nocust = [d for d in dists if not d.customer_id]
        o_nocust = [o for o in orders if not o.customer_id]
        print(f"  distributions            : {len(dists)}")
        print(f"  distributions w/o customer: {len(d_nocust)}")
        print(f"  sales orders             : {len(orders)}")
        print(f"  sales orders w/o customer: {len(o_nocust)}")
        print(f"  customer profiles        : {len(customers)}")
        if d_nocust:
            flag("HIGH", f"{len(d_nocust)} distributions have no customer and are "
                         "silently dropped from dashboard customer counts")
            for d in d_nocust[:10]:
                print(f"     dist {d.id} {d.order_number} {d.facility_name!r}")
        if o_nocust:
            flag("HIGH", f"{len(o_nocust)} sales orders have no customer and appear on no profile")
            for o in o_nocust[:10]:
                print(f"     SO {o.order_number} ({o.order_date})")

        head("2. DISTRIBUTION vs ITS OWN SALES ORDER")
        mismatch = [
            d for d in dists
            if d.sales_order_id and d.customer_id
            and (so := s.get(SalesOrder, d.sales_order_id)) is not None
            and so.customer_id and so.customer_id != d.customer_id
        ]
        print(f"  distributions whose customer differs from their order's: {len(mismatch)}")
        for d in mismatch:
            so = s.get(SalesOrder, d.sales_order_id)
            dc, oc = by_id.get(d.customer_id), by_id.get(so.customer_id)
            print(f"     dist {d.id} order {d.order_number}")
            print(f"        shipment -> #{d.customer_id} {dc.facility_name if dc else '?'!r}")
            print(f"        order    -> #{so.customer_id} {oc.facility_name if oc else '?'!r}")
        if mismatch:
            flag("HIGH", f"{len(mismatch)} distributions sit on a different profile than their "
                         "sales order, so units and orders show on different customers")

        head("3. DUPLICATE CUSTOMER PROFILES (one site, two records)")
        # Same normalized street + state, which is the identity the resolver uses.
        groups: dict[tuple, list] = defaultdict(list)
        for c in customers:
            st = (c.state or "").strip().upper()
            street = normalize_street_for_key(c.address1)
            if street and st:
                groups[(street, st)].append(c)
        dups = {k: v for k, v in groups.items() if len(v) > 1}
        units_by_cust = defaultdict(int)
        orders_by_cust = defaultdict(set)
        for d in dists:
            if d.customer_id:
                units_by_cust[d.customer_id] += sum_distribution_units([d])
                if d.order_number:
                    orders_by_cust[d.customer_id].add(d.order_number)
        print(f"  address groups holding more than one profile: {len(dups)}")
        for (street, st), cs in sorted(dups.items()):
            print(f"     {street} | {st}")
            for c in cs:
                print("        #{:<5} {!r:<52} key={} units={} orders={}".format(
                    c.id, c.facility_name, c.company_key,
                    units_by_cust.get(c.id, 0), len(orders_by_cust.get(c.id, set()))))
            active = [c for c in cs if units_by_cust.get(c.id)]
            if len(active) > 1:
                flag("HIGH", f"{street}|{st}: {len(active)} profiles each carry shipments; "
                             "this site is counted twice on the dashboard")
            else:
                flag("LOW", f"{street}|{st}: duplicate profile exists but only one has shipments")

        # Same facility name, different records.
        namegroups: dict[str, list] = defaultdict(list)
        for c in customers:
            n = (c.facility_name or "").strip().upper()
            if n:
                namegroups[n].append(c)
        namedups = {k: v for k, v in namegroups.items() if len(v) > 1}
        if namedups:
            print(f"  identical facility names on different profiles: {len(namedups)}")
            for n, cs in sorted(namedups.items()):
                print(f"     {n!r}: " + ", ".join(
                    f"#{c.id}(units={units_by_cust.get(c.id,0)})" for c in cs))
                flag("MED", f"facility name {n!r} is used by {len(cs)} profiles")

        head("4. LINKED CUSTOMER vs ADDRESS-RESOLVED CUSTOMER")
        disagree = 0
        unresolvable = 0
        shown = 0
        for d in dists:
            if not d.customer_id:
                continue
            try:
                resolved = find_unique_customer_for_distribution_ship_to(s, d)
            except Exception:
                unresolvable += 1
                continue
            if resolved.id != d.customer_id:
                disagree += 1
                if shown < 15:
                    a, b = by_id.get(d.customer_id), resolved
                    print(f"     dist {d.id} {d.order_number} {d.facility_name!r}")
                    print(f"        linked   -> #{d.customer_id} {a.facility_name if a else '?'!r}")
                    print(f"        resolves -> #{b.id} {b.facility_name!r}")
                    shown += 1
        print(f"  linked customer disagrees with address resolution: {disagree}")
        print(f"  address not resolvable to a unique customer       : {unresolvable}")
        if disagree:
            flag("MED", f"{disagree} distributions are linked to a different customer than "
                        "their ship-to address resolves to")

        head("5. DISPLAY NAME DRIFT (distribution ship-to vs profile)")
        drift = Counter()
        for d in dists:
            if not d.customer_id:
                continue
            c = by_id.get(d.customer_id)
            if not c:
                continue
            a = (d.facility_name or "").strip().upper()
            b = (c.facility_name or "").strip().upper()
            if a and b and a != b:
                drift[(d.customer_id, c.facility_name, d.facility_name)] += 1
        print(f"  distinct ship-to/profile name pairs that differ: {len(drift)}")
        for (cid, cname, dname), n in drift.most_common():
            print(f"     #{cid} profile={cname!r}")
            print(f"            ship-to={dname!r}  x{n}")
        if drift:
            flag("LOW", f"{len(drift)} ship-to names differ in text from their profile name "
                        "(cosmetic; linkage is by address)")

        head("6. ONE ORDER NUMBER ACROSS MULTIPLE CUSTOMERS")
        by_order: dict[str, set] = defaultdict(set)
        for d in dists:
            num = "".join(ch for ch in (d.order_number or "") if ch.isdigit()).zfill(7)
            if d.customer_id:
                by_order[num].add(d.customer_id)
        split = {k: v for k, v in by_order.items() if len(v) > 1}
        print(f"  order numbers whose shipments span >1 customer: {len(split)}")
        for num, ids in sorted(split.items()):
            names = ", ".join(f"#{i} {by_id[i].facility_name!r}" for i in sorted(ids) if i in by_id)
            print(f"     {num}: {names}")
            flag("HIGH", f"order {num} has shipments on {len(ids)} different customers")

        head("7. UNUSED CUSTOMER PROFILES")
        used = {d.customer_id for d in dists if d.customer_id} | {
            o.customer_id for o in orders if o.customer_id
        }
        unused = [c for c in customers if c.id not in used]
        print(f"  profiles with no sales order and no distribution: {len(unused)} of {len(customers)}")
        for c in unused[:40]:
            print(f"     #{c.id} {c.facility_name!r} ({c.city}, {c.state})")
        if len(unused) > 40:
            print(f"     ... and {len(unused) - 40} more")

        head("8. SALES ORDERS ON A PROFILE WITH NO MATCHING SHIPMENTS")
        dist_cust_by_order = {}
        for d in dists:
            if d.sales_order_id:
                dist_cust_by_order.setdefault(d.sales_order_id, set()).add(d.customer_id)
        noship = [o for o in orders if o.id not in dist_cust_by_order]
        print(f"  sales orders with no linked distribution: {len(noship)}")
        for o in sorted(noship, key=lambda x: x.order_number or "")[:40]:
            c = by_id.get(o.customer_id)
            print(f"     {o.order_number} {o.order_date} -> "
                  f"#{o.customer_id} {c.facility_name if c else '?'!r}")
        if len(noship) > 40:
            print(f"     ... and {len(noship) - 40} more")

        head("9. DASHBOARD TOTALS CROSS-CHECK")
        from app.eqms.modules.rep_traceability.service import compute_sales_dashboard
        from datetime import date

        data = compute_sales_dashboard(s, start_date=date(2000, 1, 1), end_date=None)
        st = data["stats"]
        hdr_units = sum(int(d.quantity or 0) for d in dists)
        line_units = sum_distribution_units(dists)
        distinct_cust = len({d.customer_id for d in dists if d.customer_id})
        print(f"  dashboard total_units_all_time : {st['total_units_all_time']}")
        print(f"  sum of distribution lines      : {line_units}")
        print(f"  sum of entry header quantities : {hdr_units}")
        print(f"  dashboard total_customers      : {st['total_customers']}")
        print(f"  distinct customer_id on dists  : {distinct_cust}")
        print(f"  dashboard total_orders         : {st['total_orders']}")
        print(f"  first_time / repeat            : {st['first_time_customers']} / {st['repeat_customers']}")
        if st["total_units_all_time"] != line_units:
            flag("HIGH", "dashboard all-time units disagree with the distribution lines")
        if st["total_customers"] != distinct_cust:
            flag("MED", f"dashboard counts {st['total_customers']} customers but "
                        f"{distinct_cust} distinct customer_ids carry shipments")

        head("FINDINGS")
        if not findings:
            print("  No misalignments found.")
        for sev in ("HIGH", "MED", "LOW"):
            rows = [m for s_, m in findings if s_ == sev]
            if rows:
                print(f"  [{sev}] {len(rows)}")
                for m in rows:
                    print(f"     - {m}")


if __name__ == "__main__":
    main()
