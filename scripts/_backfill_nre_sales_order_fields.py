"""
Backfill SalesOrder order fields + addresses from PDF text.

Re-parses PDF attachments on sales orders and fills null fields when extractable.
Never overwrites non-null invoice_date.
By default does not overwrite non-null amounts / PO / description / addresses unless --force.

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

# (SalesOrder attr, parse-dict key)
_FIELD_MAP = (
    ("order_amount", "order_amount"),
    ("po_reference", "po_reference"),
    ("order_description", "order_description"),
    ("sold_to_address1", "address1"),
    ("sold_to_city", "city"),
    ("sold_to_state", "state"),
    ("sold_to_zip", "zip"),
    ("ship_to_name", "ship_to_name"),
    ("ship_to_address1", "ship_to_address1"),
    ("ship_to_city", "ship_to_city"),
    ("ship_to_state", "ship_to_state"),
    ("ship_to_zip", "ship_to_zip"),
)


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from flask import current_app
    from sqlalchemy import or_

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
                or_(
                    SalesOrder.order_amount.is_(None),
                    SalesOrder.po_reference.is_(None),
                    SalesOrder.order_description.is_(None),
                    SalesOrder.sold_to_address1.is_(None),
                    SalesOrder.sold_to_city.is_(None),
                    SalesOrder.sold_to_state.is_(None),
                    SalesOrder.sold_to_zip.is_(None),
                    SalesOrder.ship_to_name.is_(None),
                    SalesOrder.ship_to_address1.is_(None),
                    SalesOrder.ship_to_city.is_(None),
                    SalesOrder.ship_to_state.is_(None),
                    SalesOrder.ship_to_zip.is_(None),
                )
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
            for attr, key in _FIELD_MAP:
                new_val = parsed.get(key)
                if new_val is None or new_val == "":
                    continue
                cur = getattr(order, attr, None)
                if cur is not None and not FORCE:
                    continue
                changes.append(f"{attr}={new_val!r}" if attr != "order_amount" else f"{attr}={new_val}")
                if not DRY_RUN:
                    setattr(order, attr, new_val)

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
