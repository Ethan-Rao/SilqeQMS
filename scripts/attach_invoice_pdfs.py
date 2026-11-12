"""Attach the 2026 packing slips and eight sales-order pages from inside the app.

Runs after gunicorn is listening, where production storage credentials exist.
A put from a laptop key is rejected and must not be used.

Idempotent: a page whose storage key is already on the order or distribution
is left in place.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "scripts" / "_invoice_pdfs_2026"

PACKING_SLIPS = (
    "Sep26PackingSlips.pdf",
    "Oct26PackingSlips.pdf",
    "Nov26PackingSlips.pdf",
)
SALES_ORDERS = "Oct26SalesOrders.pdf"
EIGHT = (
    "0000435",
    "0000436",
    "0000438",
    "0000439",
    "0000440",
    "0000441",
    "0000442",
    "0000443",
)
PROBE_KEY = "tmp/invoice_pdf_2026_put_probe.txt"


def run_on_listen() -> None:
    """Upload the PDFs. Prints the result. Never raises."""
    try:
        _run()
    except Exception as exc:
        print(f"Invoice PDF upload skipped: {type(exc).__name__}.", flush=True)


def _run() -> None:
    missing = [name for name in (*PACKING_SLIPS, SALES_ORDERS) if not (PDF_DIR / name).is_file()]
    if missing:
        print(f"Invoice PDF upload skipped: missing {', '.join(missing)}.", flush=True)
        return

    from flask import current_app

    from app.eqms import create_app
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.admin import _match_distribution_for_label
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment, SalesOrder
    from app.eqms.modules.rep_traceability.parsers.pdf import (
        _parse_date,
        parse_sales_orders_pdf,
        split_pdf_into_pages,
    )
    from app.eqms.modules.rep_traceability.service import (
        find_sales_order_by_normalized_number,
        normalize_order_number,
    )
    from app.eqms.storage import storage_from_config
    from werkzeug.utils import secure_filename

    app = create_app()
    with app.app_context():
        storage = storage_from_config(current_app.config)
        try:
            storage.put_bytes(PROBE_KEY, b"probe", content_type="text/plain")
            storage.delete(PROBE_KEY)
        except Exception:
            print("Invoice PDF upload skipped: storage probe failed.", flush=True)
            return
        print("Storage probe succeeded.", flush=True)

        session_factory = app.extensions["sqlalchemy_sessionmaker"]
        session = session_factory()
        try:
            actor = session.query(User).filter(User.email.ilike("ethanr@silq.tech")).first()
            packing_stored = 0
            sales_stored = 0
            ship_dates = []

            def storage_key(order_number: str, pdf_type: str, filename: str, distribution_id: int | None) -> str:
                suffix = f"_de{distribution_id}" if distribution_id else ""
                safe = secure_filename(filename) or "document.pdf"
                return f"sales_orders/{order_number}/pdfs/{pdf_type}{suffix}_{safe}"

            def already(key: str) -> bool:
                return (
                    session.query(OrderPdfAttachment)
                    .filter(OrderPdfAttachment.storage_key == key)
                    .first()
                    is not None
                )

            def store(order, pdf_type: str, filename: str, data: bytes, distribution_id: int | None) -> bool:
                key = storage_key(order.order_number, pdf_type, filename, distribution_id)
                if already(key):
                    return True
                storage.put_bytes(key, data, content_type="application/pdf")
                session.add(
                    OrderPdfAttachment(
                        sales_order_id=order.id,
                        distribution_entry_id=distribution_id,
                        storage_key=key,
                        filename=filename,
                        pdf_type=pdf_type,
                        content_type="application/pdf",
                        size_bytes=len(data),
                        uploaded_by_user_id=actor.id if actor else None,
                    )
                )
                session.flush()
                return True

            def maybe_ship_date(order, printed) -> None:
                if order.ship_date is not None or printed is None:
                    return
                order.ship_date = printed
                ship_dates.append(f"{order.order_number} {printed.isoformat()}")

            for name in PACKING_SLIPS:
                pages = split_pdf_into_pages((PDF_DIR / name).read_bytes())
                for page_num, page_bytes in pages:
                    text = _page_text(page_bytes)
                    ship_by_order = _ship_dates(text, _parse_date)
                    result = parse_sales_orders_pdf(page_bytes)
                    numbers = []
                    for label in result.labels or []:
                        number = (label.get("order_number") or "").strip()
                        if number and number not in numbers:
                            numbers.append(number)
                    if not numbers:
                        continue
                    filename = f"{Path(name).stem}_p{page_num}.pdf"
                    page_stored = False
                    for number in numbers:
                        label = next(
                            item for item in result.labels if (item.get("order_number") or "").strip() == number
                        )
                        order = find_sales_order_by_normalized_number(session, number)
                        if order is None:
                            print(f"Packing slip unmatched: {number}.", flush=True)
                            continue
                        matched = _match_distribution_for_label(
                            session,
                            tracking_number=label.get("tracking_number"),
                            ship_to=label.get("ship_to"),
                            order_number=number,
                        )
                        distribution_id = None
                        if matched is not None and normalize_order_number(matched.order_number) == normalize_order_number(number):
                            distribution_id = matched.id
                        if store(order, "packing_slip", filename, page_bytes, distribution_id):
                            page_stored = True
                        maybe_ship_date(order, ship_by_order.get(normalize_order_number(number)))
                    if page_stored:
                        packing_stored += 1

            so_pages = split_pdf_into_pages((PDF_DIR / SALES_ORDERS).read_bytes())
            seen = set()
            for page_num, page_bytes in so_pages:
                result = parse_sales_orders_pdf(page_bytes)
                for parsed in result.orders or []:
                    number = (parsed.get("order_number") or "").strip()
                    if number not in EIGHT or number in seen:
                        continue
                    order = find_sales_order_by_normalized_number(session, number)
                    if order is None:
                        print(f"Sales-order page unmatched: {number}.", flush=True)
                        continue
                    filename = f"Oct26SalesOrders_{number}.pdf"
                    if store(order, "sales_order_page", filename, page_bytes, None):
                        sales_stored += 1
                        seen.add(number)

            _delete_empty_rancho(session)
            session.commit()
            print(f"Packing-slip pages stored: {packing_stored}", flush=True)
            print(f"Sales-order pages stored: {sales_stored}", flush=True)
            if ship_dates:
                print("Ship dates set: " + ", ".join(ship_dates), flush=True)
            else:
                print("Ship dates set: none", flush=True)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _page_text(page_bytes: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(page_bytes)) as pdf:
        if not pdf.pages:
            return ""
        return pdf.pages[0].extract_text() or ""


def _ship_dates(text: str, parse_date) -> dict[str, object]:
    from app.eqms.modules.rep_traceability.parsers.pdf import split_text_into_packing_slip_segments
    from app.eqms.modules.rep_traceability.service import normalize_order_number

    found = {}
    for segment in split_text_into_packing_slip_segments(text):
        order = re.search(r"Order\s*#\s*SO\s*(\d{4,10})", segment, re.IGNORECASE)
        ship = re.search(r"Ship\s+Date\s+(\d{1,2}/\d{1,2}/\d{2,4})", segment, re.IGNORECASE)
        if not order or not ship:
            continue
        parsed = parse_date(ship.group(1))
        if parsed is not None:
            found[normalize_order_number(order.group(1))] = parsed
    return found


def _delete_empty_rancho(session) -> None:
    from sqlalchemy.exc import IntegrityError

    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.models import SalesOrder

    customer = session.get(Customer, 786)
    if customer is None:
        print("Customer 786 already absent.", flush=True)
        return
    orders = session.query(SalesOrder).filter(SalesOrder.customer_id == 786).count()
    if orders:
        print("Customer 786 kept: sales_orders still points at it.", flush=True)
        return
    try:
        with session.begin_nested():
            session.delete(customer)
            session.flush()
    except IntegrityError as exc:
        message = str(getattr(exc, "orig", exc))
        print(f"Customer 786 kept: foreign key blocked the delete. {message}", flush=True)
        return
    print("Customer 786 deleted.", flush=True)
