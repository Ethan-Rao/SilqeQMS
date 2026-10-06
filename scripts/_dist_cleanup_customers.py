"""Finish the Oct-2026 reconciliation: new customers, then the remaining orders.

Three ship-to sites had no customer record and one (Aspirus Riverview, 410 Dewey
St) is the same Aspirus account as the existing 400 Dewey St record, so it is
linked rather than duplicated. With the customers in place the sales orders that
could not be created for want of a customer are created.

    python scripts/_dist_cleanup_customers.py            # dry run
    python scripts/_dist_cleanup_customers.py --execute
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

PARSED_SO = ROOT / "_dist_parsed_sales_orders.json"
LOG = ROOT / "_dist_customers_log.txt"

REASON = (
    "Distribution reconciliation Oct-2026: ship-to site had no customer record; "
    "created from the distribution ship-to address"
)

# Distributions whose ship-to needs a brand new customer profile.
NEW_CUSTOMERS = [
    {
        "dist_id": 1060,
        "facility_name": "Ancora Home Health and Hospice",
        "address1": "3501 Denali St Ste 202",
        "city": "Anchorage", "state": "AK", "zip": "99503",
    },
    {
        "dist_id": 1065,
        "facility_name": "Great Falls Clinic Capital City Specialty Center",
        "address1": "2231 N Montana Ave",
        "city": "Helena", "state": "MT", "zip": "59601",
    },
    {
        "dist_id": 1085,
        "facility_name": "Cleveland Clinic Avon Hospital",
        "address1": "33300 Cleveland Clinic Blvd",
        "city": "Avon", "state": "OH", "zip": "44011",
    },
]

# Aspirus Riverview at 410 Dewey St is the same account as the existing
# 400 Dewey St record; link, do not create a second customer.
LINK_TO_EXISTING = [
    {"dist_id": 1064, "customer_key_prefix": "400DEWEYST|WI|", "note": "Aspirus, 400 Dewey St"},
]

UNSUPPORTED_ITEM_CODES = {"22000101003", "22200101003"}

out: list[str] = []


def say(m: str = "") -> None:
    print(m)
    out.append(m)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    dry = not args.execute

    os.environ.setdefault("FLASK_ENV", "production")
    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.customer_profiles.utils import compute_facility_key_from_ship_to
    from app.eqms.modules.rep_traceability.models import (
        DistributionLogEntry,
        SalesOrder,
        SalesOrderLine,
    )
    from app.eqms.modules.rep_traceability.service import (
        find_sales_order_by_normalized_number,
        rematch_unmatched_distributions_for_order,
    )

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )

        say("=" * 92)
        say(f"CUSTOMERS + REMAINING ORDERS  mode={'DRY RUN' if dry else 'EXECUTE'}")
        say(f"actor={actor.email}  {datetime.now().isoformat(timespec='seconds')}")
        say("=" * 92)

        # ----------------------------------------------------------- new customers
        say("\n[1] CREATE CUSTOMER PROFILES")
        for spec in NEW_CUSTOMERS:
            d = s.get(DistributionLogEntry, spec["dist_id"])
            if not d:
                say(f"  dist {spec['dist_id']}: MISSING, skipping")
                continue
            key = compute_facility_key_from_ship_to(
                address1=d.address1, city=d.city, state=d.state, zip=d.zip,
                facility_name=spec["facility_name"],
            )
            existing = s.query(Customer).filter(Customer.company_key == key).first()
            if existing:
                say(f"  {spec['facility_name']}: already exists as #{existing.id}, linking")
                if not dry:
                    d.customer_id = existing.id
                    s.flush()
                continue
            say(f"  CREATE {spec['facility_name']!r}")
            say(f"         {d.address1}, {d.city}, {d.state} {d.zip}")
            say(f"         company_key={key}")
            if not dry:
                c = Customer(
                    company_key=key,
                    facility_name=spec["facility_name"],
                    address1=d.address1, city=d.city, state=d.state, zip=d.zip,
                    customer_type="facility",
                    is_distributor=False,
                )
                s.add(c)
                s.flush()
                d.customer_id = c.id
                d.facility_name = spec["facility_name"]
                s.flush()
                record_event(
                    s, actor=actor, action="customer.created",
                    entity_type="customer", entity_id=str(c.id), reason=REASON,
                    metadata={
                        "facility_name": spec["facility_name"], "company_key": key,
                        "address1": d.address1, "city": d.city,
                        "state": d.state, "zip": d.zip,
                        "from_distribution_id": d.id,
                        "ship_to_name_on_shipment": spec.get("ship_to_raw") or d.facility_name,
                    },
                )
                say(f"         -> customer #{c.id}")

        # -------------------------------------------------------- link to existing
        say("\n[2] LINK TO EXISTING CUSTOMER")
        for spec in LINK_TO_EXISTING:
            d = s.get(DistributionLogEntry, spec["dist_id"])
            if not d:
                say(f"  dist {spec['dist_id']}: MISSING, skipping")
                continue
            cust = (
                s.query(Customer)
                .filter(Customer.company_key.like(spec["customer_key_prefix"] + "%"))
                .first()
            )
            if not cust:
                say(f"  dist {d.id}: no customer matching {spec['customer_key_prefix']!r}")
                continue
            say(
                f"  dist {d.id} {d.facility_name!r} -> customer #{cust.id} "
                f"{cust.facility_name!r} ({spec['note']})"
            )
            if not dry:
                d.customer_id = cust.id
                s.flush()
                record_event(
                    s, actor=actor, action="distribution_log_entry.customer_linked",
                    entity_type="distribution_log_entry", entity_id=str(d.id),
                    reason="Distribution reconciliation Oct-2026: Aspirus Riverview at "
                           "410 Dewey St is the same account as the 400 Dewey St record",
                    metadata={
                        "customer_id": cust.id, "customer_facility": cust.facility_name,
                        "ship_to_name": d.facility_name, "order_number": d.order_number,
                    },
                )

        # ------------------------------------------------------- remaining orders
        say("\n[3] CREATE REMAINING SALES ORDERS")
        parsed = json.loads(PARSED_SO.read_text(encoding="utf-8"))
        best: dict[str, dict] = {}
        for o in parsed:
            n = o.get("order_number")
            if n and (n not in best or (o.get("device_units") or 0) > (best[n].get("device_units") or 0)):
                best[n] = o

        created = 0
        for num, o in sorted(best.items()):
            if find_sales_order_by_normalized_number(s, num):
                continue
            dev = [l for l in o["lines"] if l["is_device"]]
            if not dev:
                continue
            if any(l["item_code"] in UNSUPPORTED_ITEM_CODES for l in o["lines"]):
                say(f"  {num}: SKIP (20/22 Fr SKU not supported by VALID_SKUS)")
                continue
            cust_id = None
            for d in (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.order_number.ilike(f"%{num}%"))
                .all()
            ):
                if d.customer_id:
                    cust_id = d.customer_id
                    break
            if not cust_id:
                say(f"  {num}: SKIP (no distribution with a customer; order has no shipments)")
                continue
            od = datetime.strptime(o["order_date"], "%m/%d/%Y").date()
            detail = ", ".join("{}x{}".format(l["sku"], int(l["units"])) for l in dev)
            say(f"  {num}: CREATE date={od} customer_id={cust_id} [{detail}]")
            if not dry:
                so = SalesOrder(
                    order_number=num, order_date=od, customer_id=cust_id,
                    source="pdf_import", status="completed",
                    created_by_user_id=actor.id, updated_by_user_id=actor.id,
                )
                s.add(so)
                s.flush()
                for i, l in enumerate(dev):
                    s.add(SalesOrderLine(
                        sales_order_id=so.id, sku=l["sku"],
                        quantity=int(l["units"]), line_number=i + 1,
                    ))
                s.flush()
                n_linked = rematch_unmatched_distributions_for_order(s, so)
                record_event(
                    s, actor=actor, action="sales_order.created_from_source_document",
                    entity_type="sales_order", entity_id=num,
                    reason="Distribution reconciliation Oct-2026: order existed on paper "
                           "with recorded distributions but no sales order",
                    metadata={
                        "order_date": str(od), "customer_id": cust_id, "lines": detail,
                        "source_document": f"{o['source_pdf']}#p{o['page']}",
                        "distributions_linked": n_linked,
                    },
                )
                say(f"        -> SO #{so.id}, {n_linked} distribution(s) linked")
            created += 1
        say(f"  -> {created} sales order(s) created")

        if dry:
            s.rollback()
            say("\nDRY RUN - nothing written.")
        else:
            s.commit()
            say("\nCOMMITTED.")

    LOG.write_text("\n".join(out), encoding="utf-8")
    print(f"\nlog -> {LOG}")


if __name__ == "__main__":
    main()
