"""Read-only P4-07 report: matched-only vs all-row customer units on prod."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _ascii(s: object) -> str:
    return ("" if s is None else str(s)).encode("ascii", "replace").decode("ascii")


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from collections import defaultdict

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry
    from app.eqms.modules.rep_traceability.service import sum_distribution_units

    app = create_app()
    with app.app_context():
        s = db_session()
        entries = s.query(DistributionLogEntry).filter(DistributionLogEntry.customer_id.isnot(None)).all()
        by: dict[int, list] = defaultdict(list)
        for e in entries:
            by[int(e.customer_id)].append(e)

        rows = []
        for cid, ents in by.items():
            matched = [e for e in ents if e.sales_order_id is not None]
            before = sum_distribution_units(matched)
            after = sum_distribution_units(ents)
            if after != before:
                c = s.get(Customer, cid)
                name = _ascii(c.facility_name if c else "?")
                rows.append((cid, name, before, after, after - before, len(ents) - len(matched)))

        rows.sort(key=lambda r: (-r[4], r[0]))
        print(f"affected_customers={len(rows)}")
        print(f"aggregate_rise={sum(r[4] for r in rows)}")
        for r in rows:
            print(
                f"id={r[0]} name={r[1]} before={r[2]} after={r[3]} "
                f"delta={r[4]} unmatched_entries={r[5]}"
            )
        total_all = sum_distribution_units(s.query(DistributionLogEntry).all())
        print(f"dashboard_all_units={total_all}")
        for o in s.query(DistributionLogEntry).filter(DistributionLogEntry.id.in_([1037, 1038, 1039])).all():
            print(
                f"orphan id={o.id} customer_id={o.customer_id} so={o.sales_order_id} "
                f"qty={o.quantity} name={_ascii(o.facility_name)}"
            )


if __name__ == "__main__":
    main()
