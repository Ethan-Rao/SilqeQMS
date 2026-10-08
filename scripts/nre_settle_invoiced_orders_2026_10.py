"""Advance fully-invoiced NRE orders to "Payment Received".

Twenty-four NRE orders going back to August 2025 sit at ``100% Invoiced``.
Nothing ever moved them on, because until now the dashboard had no reason to
make the distinction visible: a filter on order date hid anything older than
the current quarter, so a stale status cost nothing.

The carry-forward view changed that. Unsettled orders from earlier periods now
stay on screen, and ``100% Invoiced`` is what keeps them there. Left alone,
these two dozen would crowd out the handful of jobs that genuinely still need
an invoice raised.

Writes the same field and audit action as the dashboard dropdown
(``sales_order.nre_invoice_status``), so the history reads the same whether a
status was changed here or in the UI. A reason records that this was a bulk
reconciliation rather than someone clicking through two dozen menus.

    python scripts/nre_settle_invoiced_orders_2026_10.py            # dry run
    python scripts/nre_settle_invoiced_orders_2026_10.py --execute
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FROM_STATUS = "100% Invoiced"
TO_STATUS = "Payment Received"
REASON = (
    "Bulk reconciliation: NRE orders invoiced in full and paid, advanced to "
    "Payment Received so the dashboard carry-forward shows only work still "
    "owed. Authorised by the quality/sales owner 2026-10-08."
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.nre_projects.models import NRE_DASHBOARD_STATUSES
    from app.eqms.modules.rep_traceability.models import SalesOrder

    assert TO_STATUS in NRE_DASHBOARD_STATUSES, TO_STATUS

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )

        orders = (
            s.query(SalesOrder)
            .filter(
                SalesOrder.order_type == "nre_project",
                SalesOrder.nre_invoice_status == FROM_STATUS,
            )
            .order_by(SalesOrder.order_date)
            .all()
        )

        mode = "EXECUTE" if args.execute else "DRY RUN"
        print(f"[{mode}] actor={actor.email if actor else None}")
        print(f"[{mode}] {len(orders)} NRE order(s) at {FROM_STATUS!r}\n")

        total = 0
        for o in orders:
            amount = float(o.order_amount or 0)
            total += amount
            cust = getattr(o.customer, "name", None) or o.customer_id
            print(f"  {o.order_number}  {o.order_date}  {amount:>10,.2f}  {str(cust)[:40]}")
            if args.execute:
                o.nre_invoice_status = TO_STATUS
                record_event(
                    s,
                    actor=actor,
                    action="sales_order.nre_invoice_status",
                    entity_type="SalesOrder",
                    entity_id=str(o.id),
                    reason=REASON,
                    metadata={
                        "nre_invoice_status": TO_STATUS,
                        "nre_invoice_status_before": FROM_STATUS,
                        "bulk": "nre_settle_invoiced_orders_2026_10",
                    },
                )

        print(f"\n  {len(orders)} order(s), {total:,.2f} total")
        if args.execute:
            s.commit()
            remaining = (
                s.query(SalesOrder)
                .filter(
                    SalesOrder.order_type == "nre_project",
                    SalesOrder.nre_invoice_status == FROM_STATUS,
                )
                .count()
            )
            print(f"  committed; {remaining} order(s) still at {FROM_STATUS!r}")
        else:
            print("  no changes written; re-run with --execute")


if __name__ == "__main__":
    main()
