"""Create the sales orders that exist on paper but shipped nothing.

These three could not be created alongside the rest because the customer is
normally taken from a recorded distribution and they have none. The customer is
instead resolved from the CUSTOMER NUMBER printed on the sales order PDF.

    python scripts/_dist_cleanup_paper_orders.py            # dry run
    python scripts/_dist_cleanup_paper_orders.py --execute
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
TARGETS = ("0000383", "0000404", "0000414")

# Sites with no customer record, taken from the SHIP TO block of the sales order.
NEW_CUSTOMER_BY_CODE = {
    "UMASS": {
        "facility_name": "U Mass Memorial Medical Center",
        "address1": "33 Kendall Street",
        "city": "Worcester", "state": "MA", "zip": "01605",
    },
}


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
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
    from app.eqms.modules.rep_traceability.service import (
        find_sales_order_by_normalized_number,
    )

    parsed = json.loads(PARSED_SO.read_text(encoding="utf-8"))
    best: dict[str, dict] = {}
    for o in parsed:
        n = o.get("order_number")
        if n in TARGETS and (
            n not in best or (o.get("device_units") or 0) > (best[n].get("device_units") or 0)
        ):
            best[n] = o

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )
        print(f"mode={'DRY RUN' if dry else 'EXECUTE'}  actor={actor.email}\n")

        created = 0
        for num in TARGETS:
            o = best.get(num)
            if not o:
                print(f"  {num}: not found in parsed sales orders")
                continue
            if find_sales_order_by_normalized_number(s, num):
                print(f"  {num}: already exists")
                continue
            code = (o.get("customer_number") or "").strip().upper()
            matches = (
                s.query(Customer).filter(Customer.customer_code.ilike(code)).all() if code else []
            )
            if len(matches) == 1:
                cust = matches[0]
            elif not matches and code in NEW_CUSTOMER_BY_CODE:
                spec = NEW_CUSTOMER_BY_CODE[code]
                key = compute_facility_key_from_ship_to(
                    address1=spec["address1"], city=spec["city"],
                    state=spec["state"], zip=spec["zip"],
                    facility_name=spec["facility_name"],
                )
                cust = s.query(Customer).filter(Customer.company_key == key).first()
                if cust:
                    print(f"  {num}: customer {code} already exists as #{cust.id}")
                else:
                    print(f"  {num}: CREATE customer {spec['facility_name']!r} key={key}")
                    if dry:
                        continue
                    cust = Customer(
                        company_key=key, facility_name=spec["facility_name"],
                        customer_code=code, address1=spec["address1"],
                        city=spec["city"], state=spec["state"], zip=spec["zip"],
                        customer_type="facility", is_distributor=False,
                    )
                    s.add(cust)
                    s.flush()
                    record_event(
                        s, actor=actor, action="customer.created",
                        entity_type="customer", entity_id=str(cust.id),
                        reason="Distribution reconciliation Oct-2026: customer taken from "
                               "the SHIP TO block of the sales order",
                        metadata={**spec, "company_key": key, "customer_code": code,
                                  "source_order": num},
                    )
                    print(f"        -> customer #{cust.id}")
            else:
                print(f"  {num}: customer_code={code!r} matched {len(matches)} customers; SKIP")
                for m in matches:
                    print(f"        #{m.id} {m.facility_name!r}")
                continue
            dev = [l for l in o["lines"] if l["is_device"]]
            if not dev:
                print(f"  {num}: no device lines; SKIP")
                continue
            od = datetime.strptime(o["order_date"], "%m/%d/%Y").date()
            detail = ", ".join("{}x{}".format(l["sku"], int(l["units"])) for l in dev)
            print(f"  {num}: CREATE {od} cust #{cust.id} {cust.facility_name!r} [{detail}]")
            if not dry:
                so = SalesOrder(
                    order_number=num, order_date=od, customer_id=cust.id,
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
                record_event(
                    s, actor=actor, action="sales_order.created_from_source_document",
                    entity_type="sales_order", entity_id=num,
                    reason="Distribution reconciliation Oct-2026: order exists on paper "
                           "with no shipments; customer resolved from the printed "
                           "CUSTOMER NUMBER on the sales order",
                    metadata={
                        "order_date": str(od), "customer_id": cust.id,
                        "customer_code": code, "lines": detail,
                        "source_document": f"{o['source_pdf']}#p{o['page']}",
                        "distributions": 0,
                    },
                )
                print(f"        -> SO #{so.id}")
            created += 1

        if dry:
            s.rollback()
            print(f"\n{created} would be created. DRY RUN - nothing written.")
        else:
            s.commit()
            print(f"\nCOMMITTED {created} sales order(s).")


if __name__ == "__main__":
    main()
