"""
One-time script to backfill customer addresses from their first matched Sales Order PDF.

Run: python scripts/backfill_customer_addresses.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.eqms import create_app
from app.eqms.db import db_session
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
from app.eqms.modules.rep_traceability.parsers.pdf import _extract_text, _parse_ship_to_block
from app.eqms.storage import storage_from_config


def backfill_addresses() -> None:
    app = create_app()
    with app.app_context():
        s = db_session()

        customers_without_address = (
            s.query(Customer)
            .filter((Customer.address1.is_(None)) | (Customer.address1 == ""))
            .all()
        )

        print(f"Found {len(customers_without_address)} customers without addresses")

        updated = 0
        storage = storage_from_config(app.config)

        for customer in customers_without_address:
            first_order = (
                s.query(SalesOrder)
                .filter(SalesOrder.customer_id == customer.id)
                .order_by(SalesOrder.order_date.asc())
                .first()
            )
            if not first_order:
                continue

            attachment = (
                s.query(OrderPdfAttachment)
                .filter(OrderPdfAttachment.sales_order_id == first_order.id)
                .filter(OrderPdfAttachment.pdf_type == "sales_order_page")
                .first()
            )
            if not attachment:
                continue

            try:
                with storage.open(attachment.storage_key) as fobj:
                    pdf_bytes = fobj.read()
                text = _extract_text(pdf_bytes)
                ship_to = _parse_ship_to_block(text)

                if ship_to.get("ship_to_address1"):
                    customer.address1 = ship_to.get("ship_to_address1")
                    customer.city = ship_to.get("ship_to_city")
                    customer.state = ship_to.get("ship_to_state")
                    customer.zip = ship_to.get("ship_to_zip")
                    updated += 1
                    print(
                        f"Updated: {customer.facility_name} with address from SO#{first_order.order_number}"
                    )
            except Exception as e:
                print(f"Error processing {customer.facility_name}: {e}")
                continue

        s.commit()
        print(f"\nBackfill complete: {updated} customers updated")


if __name__ == "__main__":
    backfill_addresses()
