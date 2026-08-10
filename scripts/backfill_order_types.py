"""
Backfill SalesOrder.order_type from distribution / line evidence.

Dry-run by default; writes only with --execute.
Default fills only order_type IS NULL; --force recomputes non-manual types.

Usage:
    python scripts/backfill_order_types.py
    python scripts/backfill_order_types.py --execute
    python scripts/backfill_order_types.py --execute --force
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv
FORCE = "--force" in sys.argv


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from collections import Counter

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.rep_traceability.order_type import (
        ORDER_TYPE_NRE_PROJECT,
        classify_order_type,
    )

    app = create_app()
    with app.app_context():
        s = db_session()

        q = s.query(SalesOrder)
        if not FORCE:
            q = q.filter(SalesOrder.order_type.is_(None))
        orders = q.order_by(SalesOrder.id.asc()).all()

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}{'  FORCE' if FORCE else ''}")
        print(f"Orders considered: {len(orders)}")

        type_counts: Counter[str] = Counter()
        needs_review_count = 0
        disagreements: list[tuple[str, str, str]] = []
        skipped_manual = 0

        for order in orders:
            if order.order_type_is_manual:
                skipped_manual += 1
                continue

            new_type, needs_review = classify_order_type(s, order)
            type_counts[new_type] += 1
            if needs_review:
                needs_review_count += 1

            cust = order.customer
            if cust is not None and cust.customer_type == "nre" and new_type != ORDER_TYPE_NRE_PROJECT:
                disagreements.append(
                    (
                        order.order_number,
                        cust.facility_name or "",
                        new_type,
                    )
                )

            if not DRY_RUN:
                order.order_type = new_type
                order.order_type_needs_review = needs_review

        if not DRY_RUN:
            s.commit()

        print("Counts by type:")
        for t, n in sorted(type_counts.items()):
            print(f"  {t}: {n}")
        print(f"Needs review: {needs_review_count}")
        print(f"Skipped manual: {skipped_manual}")
        print()
        print("customer_type=nre disagreements (did not classify as nre_project):")
        if not disagreements:
            print("  (none)")
        else:
            for order_number, cust_name, resulting in disagreements:
                print(f"  order={order_number} customer={cust_name} type={resulting}")


if __name__ == "__main__":
    main()
