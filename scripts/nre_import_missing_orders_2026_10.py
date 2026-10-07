"""Import the NRE sales orders the October bulk load dropped, and type the rest.

``scripts/_dist_cleanup_customers.py`` skipped any order with no catheter device
line, which is every NRE order, so four jobs in AugSep26SalesOrders.pdf never
reached the database. Their tracker entries had nothing to match against.

Totals are taken from the ORDER TOTAL printed on each page, not the line sum:
0000419 carries $100 freight that the lines do not show.

Task O imports the four orders. Task T backfills order_type on orders that were
never classified, which makes them invisible to every typed view.

    python scripts/nre_import_missing_orders_2026_10.py            # dry run
    python scripts/nre_import_missing_orders_2026_10.py --execute
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

LOG: list[str] = []


def say(line: str = "") -> None:
    print(line)
    LOG.append(line)


SOURCE_PDF = "AugSep26SalesOrders.pdf"

ORDERS = [
    {
        "order_number": "0000399",
        "order_date": date(2026, 8, 27),
        "customer_code": "ASPERO",
        "order_amount": Decimal("1804.04"),
        "po_reference": "176",
        "order_description": "Coating services to produce 3in lengths for testing",
        "page": 21,
    },
    {
        "order_number": "0000400",
        "order_date": date(2026, 8, 27),
        "customer_code": "AB",
        "order_amount": Decimal("4982.50"),
        "po_reference": "Quote 82026-1",
        "order_description": (
            "Device coating machine cleaning, preparation and shutdown; "
            "electrode coating; electrochemical analysis"
        ),
        "page": 22,
    },
    {
        "order_number": "0000419",
        "order_date": date(2026, 9, 21),
        "customer_code": "FEARSOME",
        "order_amount": Decimal("7570.00"),
        "po_reference": "PO-PRN-1727",
        "order_description": (
            "Device coating, 5 coated PEEK tube samples; surface analysis with "
            "dye testing; UV LED connector assembly"
        ),
        "page": 39,
    },
    {
        "order_number": "0000420",
        "order_date": date(2026, 9, 28),
        "customer_code": "NEPTUNE",
        "order_amount": Decimal("4830.00"),
        "po_reference": "TR3121",
        "order_description": (
            "PMMA coating process development, scientific analysis report, "
            "sample production of selected formulations"
        ),
        "ship_to_name": "Gregory Yeh",
        "ship_to_address1": "1828 El Camino Real Suite 508",
        "ship_to_city": "Burlingame",
        "ship_to_state": "CA",
        "ship_to_zip": "94010",
        "page": 40,
    },
]

REASON = (
    "Order was present in {pdf} page {page} but the October bulk import skipped "
    "every order with no catheter device line, so this NRE job never reached the "
    "database and its invoice-tracker entry had nothing to match against."
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--only", default="", help="comma list of task letters, e.g. O")
    args = ap.parse_args()
    dry = not args.execute
    only = {t.strip().upper() for t in args.only.split(",") if t.strip()}

    def want(task: str) -> bool:
        return not only or task in only

    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.nre_projects.models import NREProjectEntry
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type
    from app.eqms.modules.rep_traceability.service import (
        find_sales_order_by_normalized_number,
    )

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )

        say("=" * 92)
        say("NRE orders missed by the October bulk import")
        say("=" * 92)

        # ------------------------------------------------ O: import the orders
        if want("O"):
            say()
            say("-- O: import dropped NRE sales orders ------------------------------------")
            for spec in ORDERS:
                num = spec["order_number"]
                say()
                if find_sales_order_by_normalized_number(s, num):
                    say(f"   {num}: already present; skipping")
                    continue
                cust = (
                    s.query(Customer)
                    .filter(Customer.customer_code == spec["customer_code"])
                    .one_or_none()
                )
                if cust is None:
                    say(f"   {num}: no customer with code {spec['customer_code']!r}; skipping")
                    continue

                say(f"   {num} {spec['order_date']}  {cust.facility_name} (#{cust.id})")
                say(f"     amount {spec['order_amount']}  PO {spec['po_reference']!r}")
                say(f"     {spec['order_description']}")
                say(f"     source {SOURCE_PDF} page {spec['page']}")

                open_entries = [
                    e for e in s.query(NREProjectEntry)
                    .filter(NREProjectEntry.sales_order_id.is_(None)).all()
                    if (e.customer_name or "").lower().startswith(
                        cust.facility_name.split()[0].lower())
                ]
                for e in open_entries:
                    say(f"     candidate tracker entry {e.id}: {e.description!r} "
                        f"{e.invoice_amount}")

                if dry:
                    continue

                so = SalesOrder(
                    order_number=num,
                    order_date=spec["order_date"],
                    customer_id=cust.id,
                    source="pdf_import",
                    status="completed",
                    order_amount=spec["order_amount"],
                    po_reference=spec["po_reference"],
                    order_description=spec["order_description"],
                    sold_to_address1=cust.sold_to_address1,
                    sold_to_city=cust.sold_to_city,
                    sold_to_state=cust.sold_to_state,
                    sold_to_zip=cust.sold_to_zip,
                    ship_to_name=spec.get("ship_to_name"),
                    ship_to_address1=spec.get("ship_to_address1"),
                    ship_to_city=spec.get("ship_to_city"),
                    ship_to_state=spec.get("ship_to_state"),
                    ship_to_zip=spec.get("ship_to_zip"),
                    created_by_user_id=actor.id if actor else None,
                    updated_by_user_id=actor.id if actor else None,
                )
                s.add(so)
                s.flush()
                record_event(
                    s,
                    actor=actor,
                    action="sales_order.created_from_source_document",
                    entity_type="SalesOrder",
                    entity_id=str(so.id),
                    reason=REASON.format(pdf=SOURCE_PDF, page=spec["page"]),
                    metadata={
                        "order_number": num,
                        "order_date": str(spec["order_date"]),
                        "customer_id": cust.id,
                        "order_amount": str(spec["order_amount"]),
                        "po_reference": spec["po_reference"],
                        "source_document": f"{SOURCE_PDF}#p{spec['page']}",
                    },
                )
                # Classifies as nre_project, then runs the tracker auto-match.
                safe_apply_order_type(s, so, user=actor)
                s.flush()
                matched = (
                    s.query(NREProjectEntry)
                    .filter(NREProjectEntry.sales_order_id == so.id)
                    .first()
                )
                say(f"     -> SO #{so.id} type={so.order_type}")
                if matched:
                    say(f"     -> auto-matched tracker entry {matched.id} "
                        f"{matched.description!r} (tracker {matched.invoice_amount})")
                    say(f"        dashboard status now {so.nre_invoice_status!r}")
                else:
                    say("     -> no confident tracker match; left for manual Match")
                s.commit()

        # --------------------------------------------- T: classify untyped orders
        if want("T"):
            say()
            say("-- T: backfill order_type on unclassified orders --------------------------")
            untyped = (
                s.query(SalesOrder)
                .filter(SalesOrder.order_type.is_(None))
                .order_by(SalesOrder.order_date)
                .all()
            )
            if not untyped:
                say("   none")
            for o in untyped:
                cust = s.get(Customer, o.customer_id) if o.customer_id else None
                say(f"   {o.order_number} {o.order_date} "
                    f"{cust.facility_name if cust else '-'}")
                if dry:
                    from app.eqms.modules.rep_traceability.order_type import (
                        classify_order_type,
                    )

                    new_type, review = classify_order_type(s, o)
                    say(f"     would become {new_type!r} (needs_review={review})")
                    continue
                safe_apply_order_type(s, o, user=actor)
                s.flush()
                say(f"     -> {o.order_type!r} (needs_review={o.order_type_needs_review})")
            if not dry:
                s.commit()

        say()
        say("=" * 92)
        say("DRY RUN -- nothing written" if dry else "EXECUTED")
        say("=" * 92)

    (ROOT / "_nre_import_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
