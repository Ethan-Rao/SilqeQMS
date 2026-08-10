"""
Read-only reconciliation report for sales orders vs distributions (P4-02 Task D).

Sizes later work (P4-03 customer re-keying, P4-08 linking). No writes.

Usage:
    python scripts/_report_order_reconciliation.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from collections import Counter

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
    from app.eqms.modules.rep_traceability.order_type import (
        ORDER_TYPE_CLEARTRACT_IN_PROCESS,
        ORDER_TYPE_NRE_PROJECT,
    )
    from app.eqms.modules.rep_traceability.service import normalize_order_number

    app = create_app()
    with app.app_context():
        s = db_session()

        orders = s.query(SalesOrder).all()
        type_counts: Counter[str] = Counter()
        null_type = 0
        needs_review = 0
        for o in orders:
            if o.order_type is None:
                null_type += 1
            else:
                type_counts[o.order_type] += 1
            if o.order_type_needs_review:
                needs_review += 1

        print("=== 1. Sales orders by order_type ===")
        print(f"Total sales orders: {len(orders)}")
        for t, n in sorted(type_counts.items()):
            print(f"  {t}: {n}")
        print(f"  order_type IS NULL: {null_type}")
        print(f"  order_type_needs_review true: {needs_review}")
        print()

        # Build normalized maps
        unmatched_dists = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.sales_order_id.is_(None))
            .all()
        )
        unmatched_by_norm: dict[str, list] = {}
        for d in unmatched_dists:
            key = normalize_order_number(d.order_number)
            if key:
                unmatched_by_norm.setdefault(key, []).append(d)

        so_by_norm: dict[str, list] = {}
        for o in orders:
            key = normalize_order_number(o.order_number)
            if key:
                so_by_norm.setdefault(key, []).append(o)

        in_process = [o for o in orders if o.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS]
        print("=== 2. cleartract_in_process orders ===")
        print(f"Count: {len(in_process)}")
        with_candidate = 0
        for o in in_process:
            cust_name = o.customer.facility_name if o.customer else "-"
            key = normalize_order_number(o.order_number)
            has_cand = bool(key and unmatched_by_norm.get(key))
            if has_cand:
                with_candidate += 1
            print(
                f"  order={o.order_number} date={o.order_date} "
                f"customer={cust_name} unmatched_candidate={'yes' if has_cand else 'no'}"
            )
        print(
            f"Summary: {with_candidate} of {len(in_process)} in-process orders "
            f"have a candidate unmatched distribution"
        )
        print()

        print("=== 3. Unmatched distributions ===")
        print(f"Distributions with sales_order_id IS NULL: {len(unmatched_dists)}")
        linkable = 0
        for d in unmatched_dists:
            key = normalize_order_number(d.order_number)
            if key and so_by_norm.get(key):
                linkable += 1
        print(f"Of those, linkable by normalized order number: {linkable}")
        print()

        print("=== 4. Empty customer shells ===")
        cust_ids_with_so = {o.customer_id for o in orders}
        dist_cust_rows = (
            s.query(DistributionLogEntry.customer_id)
            .filter(DistributionLogEntry.customer_id.isnot(None))
            .distinct()
            .all()
        )
        cust_ids_with_dist = {r[0] for r in dist_cust_rows}

        empty = (
            s.query(Customer)
            .filter(~Customer.id.in_(cust_ids_with_so | cust_ids_with_dist))
            .order_by(Customer.id.asc())
            .all()
        )
        print(f"Customers with zero sales orders and zero distributions: {len(empty)}")
        for c in empty[:40]:
            print(f"  id={c.id} facility_name={c.facility_name}")
        if len(empty) > 40:
            print(f"  ... and {len(empty) - 40} more")
        print()

        print("=== 5. Catheter customers whose only orders are nre_project ===")
        mismatches = []
        cath_customers = (
            s.query(Customer).filter(Customer.customer_type == "catheter").all()
        )
        for c in cath_customers:
            cust_orders = [o for o in orders if o.customer_id == c.id]
            if not cust_orders:
                continue
            if all(o.order_type == ORDER_TYPE_NRE_PROJECT for o in cust_orders):
                mismatches.append(c)
        print(f"Count: {len(mismatches)}")
        for c in mismatches[:40]:
            print(f"  id={c.id} facility_name={c.facility_name} company_key={c.company_key}")
        if len(mismatches) > 40:
            print(f"  ... and {len(mismatches) - 40} more")
        print()

        print("=== 6. nre_project orders with null order_amount ===")
        nre_null_amt = [
            o
            for o in orders
            if o.order_type == ORDER_TYPE_NRE_PROJECT and o.order_amount is None
        ]
        print(f"Count: {len(nre_null_amt)}")


if __name__ == "__main__":
    main()
