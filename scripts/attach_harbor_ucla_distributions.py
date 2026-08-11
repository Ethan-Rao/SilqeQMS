"""
P4-07 / D41 — Attach orphan Harbor-UCLA distributions to the keyed Harbor UCLA customer.

Dry-run by default; writes only with --execute.
Resolves the customer by address-based company_key (not facility-name matching).
Does not invent sales-order links. Records an audit event per row on execute.

Usage:
    python scripts/attach_harbor_ucla_distributions.py
    python scripts/attach_harbor_ucla_distributions.py --execute
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv

ORPHAN_DIST_IDS = [1037, 1038, 1039]


def _ascii(s: object) -> str:
    text = "" if s is None else str(s)
    return text.encode("ascii", "replace").decode("ascii")


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry
    from app.eqms.modules.rep_traceability.service import (
        attach_distributions_to_customer,
        find_unique_customer_for_distribution_ship_to,
        sum_distribution_units,
    )

    app = create_app()
    with app.app_context():
        s = db_session()
        seed = s.get(DistributionLogEntry, ORPHAN_DIST_IDS[0])
        if seed is None:
            raise SystemExit(f"distribution id={ORPHAN_DIST_IDS[0]} not found")

        customer = find_unique_customer_for_distribution_ship_to(s, seed)
        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(
            f"Harbor customer id={customer.id} key={_ascii(customer.company_key)} "
            f"name={_ascii(customer.facility_name)}"
        )

        preview = attach_distributions_to_customer(
            s,
            distribution_ids=ORPHAN_DIST_IDS,
            customer_id=customer.id,
            actor=None,
            execute=not DRY_RUN,
        )
        for row in preview["rows"]:
            b = row["before"]
            print(
                f"  dist id={b['id']} order={_ascii(b['order_number'])} "
                f"units={row['units']} customer_id {b['customer_id']} -> {row['after']['customer_id']} "
                f"sales_order_id={b['sales_order_id']}"
            )
        print(
            f"Customer units before={preview['units_before']} "
            f"after={preview['units_after']} added={preview['units_added']}"
        )

        if DRY_RUN:
            print("DRY RUN — re-run with --execute to write.")
            return

        s.commit()
        refreshed = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.customer_id == customer.id)
            .all()
        )
        print(f"EXECUTE complete. Customer unit total now={sum_distribution_units(refreshed)}")
        still_null = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.id.in_(ORPHAN_DIST_IDS))
            .filter(DistributionLogEntry.customer_id.is_(None))
            .count()
        )
        print(f"Orphans still null customer_id: {still_null}")


if __name__ == "__main__":
    main()
