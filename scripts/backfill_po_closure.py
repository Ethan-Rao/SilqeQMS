"""
Backfill purchase_orders.is_closed / closed_at from existing closed_by text (P4-06 / D39).

Dry-run by default; writes only with --execute.
Never modifies closed_by. Does not infer closure from status == received.

Usage:
    python scripts/backfill_po_closure.py
    python scripts/backfill_po_closure.py --execute
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.purchasing.models import PurchaseOrder
    from app.eqms.modules.purchasing.service import parse_closed_by_date
    from sqlalchemy import func

    app = create_app()
    with app.app_context():
        s = db_session()

        total = s.query(func.count(PurchaseOrder.id)).scalar() or 0
        open_before = (
            s.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.is_closed.is_(False))
            .scalar()
            or 0
        )
        closed_before = (
            s.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.is_closed.is_(True))
            .scalar()
            or 0
        )

        with_closed_by = (
            s.query(PurchaseOrder)
            .filter(PurchaseOrder.closed_by.isnot(None))
            .filter(PurchaseOrder.closed_by != "")
            .order_by(PurchaseOrder.po_number.asc())
            .all()
        )
        received_blank = (
            s.query(PurchaseOrder)
            .filter(PurchaseOrder.status == "received")
            .filter((PurchaseOrder.closed_by.is_(None)) | (PurchaseOrder.closed_by == ""))
            .order_by(PurchaseOrder.po_number.asc())
            .all()
        )

        would_close = 0
        with_date = 0
        unparseable: list[tuple[str, str]] = []
        pending_but_closed_by = 0

        for po in with_closed_by:
            would_close += 1
            if po.status == "pending":
                pending_but_closed_by += 1
            parsed = parse_closed_by_date(po.closed_by)
            if parsed:
                with_date += 1
            else:
                unparseable.append((po.po_number, po.closed_by or ""))

            if not DRY_RUN:
                po.is_closed = True
                if parsed and po.closed_at is None:
                    po.closed_at = parsed

        if not DRY_RUN:
            s.commit()

        open_after = (
            s.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.is_closed.is_(False))
            .scalar()
            or 0
        )
        closed_after = (
            s.query(func.count(PurchaseOrder.id))
            .filter(PurchaseOrder.is_closed.is_(True))
            .scalar()
            or 0
        )

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Total POs: {total}")
        print(f"Open/Closed before: {open_before} / {closed_before}")
        print(f"Rows with closed_by text: {len(with_closed_by)}")
        print(f"Would set / set is_closed: {would_close}")
        print(f"Parseable closed_at: {with_date}")
        print(f"Unparseable date (still closed): {len(unparseable)}")
        print(f"pending + closed_by (badge flip candidates): {pending_but_closed_by}")
        print(f"received + blank closed_by (stay open): {len(received_blank)}")
        for p in received_blank:
            print(f"  stay-open received: {p.po_number}")
        if unparseable:
            print("Unparseable closed_by dates:")
            for num, text in unparseable:
                print(f"  {num}: {text}")
        print(f"Open/Closed after: {open_after} / {closed_after}")


if __name__ == "__main__":
    main()
