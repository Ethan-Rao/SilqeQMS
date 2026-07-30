"""
Backfill SalesOrder.order_amount / po_reference / order_description from PDF text.

Re-parses PDF attachments on sales orders (prefer pdf_import / NRE-related) and
fills null fields when extractable. Never overwrites non-null invoice_date.
By default does not overwrite non-null amounts / PO / description unless --force.

Usage:
    python scripts/_backfill_nre_sales_order_fields.py            # dry-run
    python scripts/_backfill_nre_sales_order_fields.py --execute
    python scripts/_backfill_nre_sales_order_fields.py --execute --force
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

    from flask import current_app

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment, SalesOrder
    from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf
    from app.eqms.storage import storage_from_config

    app = create_app()
    with app.app_context():
        s = db_session()
        storage = storage_from_config(current_app.config)

        q = s.query(SalesOrder)
        if not FORCE:
            q = q.filter(
                (SalesOrder.order_amount.is_(None))
                | (SalesOrder.po_reference.is_(None))
                | (SalesOrder.order_description.is_(None))
            )
        orders = q.order_by(SalesOrder.id.asc()).all()

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}{'  FORCE' if FORCE else ''}")
        print(f"Sales orders considered: {len(orders)}")
        print()

        updated = skipped_no_pdf = skipped_no_fields = 0
        for order in orders:
            atts = (
                s.query(OrderPdfAttachment)
                .filter(OrderPdfAttachment.sales_order_id == order.id)
                .order_by(OrderPdfAttachment.uploaded_at.desc())
                .all()
            )
            if not atts:
                skipped_no_pdf += 1
                continue

            parsed = None
            for att in atts:
                try:
                    data = storage.get_bytes(att.storage_key)
                except Exception as e:  # noqa: BLE001
                    print(f"  SKIP SO {order.order_number}: storage error {e}")
                    continue
                try:
                    result = parse_sales_orders_pdf(data)
                    results = list(result.orders or [])
                except Exception as e:  # noqa: BLE001
                    print(f"  SKIP SO {order.order_number}: parse error {e}")
                    continue
                # Prefer page matching this order number.
                match = next(
                    (r for r in results if str(r.get("order_number") or "") == str(order.order_number)),
                    None,
                )
                parsed = match or (results[0] if results else None)
                if parsed:
                    break

            if not parsed:
                skipped_no_fields += 1
                continue

            changes = []
            amt = parsed.get("order_amount")
            if amt is not None and (order.order_amount is None or FORCE):
                changes.append(f"order_amount={amt}")
                if not DRY_RUN:
                    order.order_amount = amt
            po = parsed.get("po_reference")
            if po and (order.po_reference is None or FORCE):
                changes.append(f"po_reference={po!r}")
                if not DRY_RUN:
                    order.po_reference = po
            desc = parsed.get("order_description")
            if desc and (order.order_description is None or FORCE):
                changes.append(f"order_description={desc[:40]!r}…")
                if not DRY_RUN:
                    order.order_description = desc

            if not changes:
                skipped_no_fields += 1
                continue
            print(f"  UPDATE SO {order.order_number}: {', '.join(changes)}")
            updated += 1

        if not DRY_RUN:
            s.commit()

        print()
        print(f"Summary: {updated} updated, {skipped_no_pdf} no PDF, {skipped_no_fields} nothing to fill.")
        if DRY_RUN:
            print("DRY RUN — re-run with --execute to write.")


if __name__ == "__main__":
    main()
