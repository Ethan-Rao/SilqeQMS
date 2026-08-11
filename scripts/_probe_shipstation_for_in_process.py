"""
Read-only ShipStation probe for cleartract_in_process sales orders (P4-03 Task E).

For each in-process catheter order, ask whether ShipStation already has an order
and shipments. No DB writes, no sync, no distribution creation.

Usage:
    python scripts/_probe_shipstation_for_in_process.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _ascii(s: object) -> str:
    text = "" if s is None else str(s)
    return text.encode("ascii", "replace").decode("ascii")


def _order_number_candidates(order_number: str) -> list[str]:
    raw = (order_number or "").strip()
    if not raw:
        return []
    cands = [raw]
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits:
        cands.append(digits)
        cands.append(digits.lstrip("0") or "0")
        cands.append(f"SO {digits}")
        cands.append(f"SO{digits}")
    # Preserve order, drop dupes
    seen: set[str] = set()
    out: list[str] = []
    for c in cands:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_CLEARTRACT_IN_PROCESS
    from app.eqms.modules.shipstation_sync.shipstation_client import ShipStationClient

    api_key = (os.environ.get("SHIPSTATION_API_KEY") or "").strip()
    api_secret = (os.environ.get("SHIPSTATION_API_SECRET") or "").strip()

    app = create_app()
    with app.app_context():
        s = db_session()
        orders = (
            s.query(SalesOrder)
            .filter(SalesOrder.order_type == ORDER_TYPE_CLEARTRACT_IN_PROCESS)
            .order_by(SalesOrder.order_date.asc(), SalesOrder.id.asc())
            .all()
        )
        print(f"cleartract_in_process orders: {len(orders)}")

        if not api_key or not api_secret:
            print("ERROR: SHIPSTATION_API_KEY or SHIPSTATION_API_SECRET not set")
            for o in orders:
                cust = o.customer.facility_name if o.customer else "-"
                print(
                    f"  order={_ascii(o.order_number)} date={o.order_date} "
                    f"customer={_ascii(cust)} ss_order=credentials_missing "
                    f"ss_status=- shipments=- tracking=-"
                )
            print("Summary: aborted (missing credentials)")
            return

        client = ShipStationClient(api_key=api_key, api_secret=api_secret)

        with_shipments = 0
        with_order_no_ship = 0
        no_order = 0
        errors = 0

        for o in orders:
            cust = o.customer.facility_name if o.customer else "-"
            ss_order = None
            ss_status = "-"
            shipment_count = 0
            tracking: list[str] = []
            err = None

            try:
                for cand in _order_number_candidates(o.order_number):
                    found = client.list_orders_by_order_number(cand)
                    if found:
                        ss_order = found[0]
                        break
                if ss_order:
                    ss_status = _ascii(ss_order.get("orderStatus") or "-")
                    ss_id = str(ss_order.get("orderId") or "").strip()
                    if ss_id:
                        page = 1
                        while True:
                            batch = client.list_shipments_for_order(ss_id, page=page, page_size=100)
                            if not batch:
                                break
                            shipment_count += len(batch)
                            for sh in batch:
                                tn = (sh.get("trackingNumber") or "").strip()
                                if tn:
                                    tracking.append(_ascii(tn))
                            if len(batch) < 100:
                                break
                            page += 1
            except Exception as e:
                err = _ascii(e)
                errors += 1

            if err:
                print(
                    f"  order={_ascii(o.order_number)} date={o.order_date} "
                    f"customer={_ascii(cust)} ss_order=error "
                    f"ss_status=- shipments=- tracking=- error={err}"
                )
            elif ss_order is None:
                no_order += 1
                print(
                    f"  order={_ascii(o.order_number)} date={o.order_date} "
                    f"customer={_ascii(cust)} ss_order=no "
                    f"ss_status=- shipments=0 tracking=-"
                )
            elif shipment_count > 0:
                with_shipments += 1
                print(
                    f"  order={_ascii(o.order_number)} date={o.order_date} "
                    f"customer={_ascii(cust)} ss_order=yes "
                    f"ss_status={ss_status} shipments={shipment_count} "
                    f"tracking={','.join(tracking) if tracking else '-'}"
                )
            else:
                with_order_no_ship += 1
                print(
                    f"  order={_ascii(o.order_number)} date={o.order_date} "
                    f"customer={_ascii(cust)} ss_order=yes "
                    f"ss_status={ss_status} shipments=0 tracking=-"
                )

        print()
        print("=== Summary ===")
        print(f"SS order with shipment(s) [sync gaps]: {with_shipments}")
        print(f"SS order with no shipment: {with_order_no_ship}")
        print(f"No SS order: {no_order}")
        print(f"API errors: {errors}")


if __name__ == "__main__":
    main()
