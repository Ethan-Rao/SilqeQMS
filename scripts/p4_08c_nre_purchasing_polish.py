"""P4-08C: delete SO 0000383 and retype remaining nre+catheter rows.

Usage:
    python scripts/p4_08c_nre_purchasing_polish.py
    python scripts/p4_08c_nre_purchasing_polish.py --execute
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DRY_RUN = "--execute" not in sys.argv
TARGET_NUM = "0000383"
TARGET_ID = 1457
EXPECTED_LINES = {("211610SPT", 2), ("211810SPT", 2)}


def _ascii(s: object) -> str:
    return ("" if s is None else str(s)).encode("ascii", "replace").decode("ascii")


def _admin(s):
    from app.eqms.models import User

    u = s.query(User).filter(User.email.ilike("%ethan%")).first()
    if u:
        return u
    return s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()


def _find_target(s):
    from app.eqms.modules.rep_traceability.service import find_sales_order_by_normalized_number

    return find_sales_order_by_normalized_number(s, TARGET_NUM)


def _line_pairs(so) -> set:
    return {(ln.sku, int(ln.quantity or 0)) for ln in (so.lines or [])}


def _nre_catheter_rows(s):
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_NRE_PROJECT
    from app.eqms.modules.rep_traceability.service import sales_order_has_catheter_sku

    rows = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_type == ORDER_TYPE_NRE_PROJECT)
        .all()
    )
    return [o for o in rows if sales_order_has_catheter_sku(o)]


def preview(s) -> None:
    from app.eqms.modules.nre_projects.models import NREProjectEntry
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, OrderPdfAttachment

    so = _find_target(s)
    print("TASK A preview")
    if so is None:
        print("  0000383 not found")
        return
    dists = s.query(DistributionLogEntry).filter(DistributionLogEntry.sales_order_id == so.id).count()
    atts = s.query(OrderPdfAttachment).filter(OrderPdfAttachment.sales_order_id == so.id).all()
    tracker = s.query(NREProjectEntry).filter(NREProjectEntry.sales_order_id == so.id).all()
    print(
        f"  id={so.id} type={_ascii(so.order_type)} status={_ascii(so.status)} "
        f"amount={so.order_amount} nre_status={_ascii(so.nre_invoice_status)}"
    )
    print(
        f"  customer_id={so.customer_id} name={_ascii(so.customer.facility_name if so.customer else None)}"
    )
    print(f"  lines={[(ln.sku, ln.quantity) for ln in (so.lines or [])]}")
    print(f"  dists={dists} atts={[ _ascii(a.filename) for a in atts ]} tracker={len(tracker)}")
    ok = so.id == TARGET_ID and dists == 0 and _line_pairs(so) == EXPECTED_LINES
    print(f"  guards_ok={ok} expect id={TARGET_ID} zero dists lines={sorted(EXPECTED_LINES)}")

    print("TASK C preview nre_project + catheter SKU:")
    others = _nre_catheter_rows(s)
    for o in others:
        print(
            f"  id={o.id} {_ascii(o.order_number)} manual={bool(o.order_type_is_manual)} "
            f"lines={[(ln.sku, ln.quantity) for ln in (o.lines or [])]}"
        )
    if not others:
        print("  (none)")


def execute(s, user) -> None:
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.nre_projects.models import NREProjectEntry
    from app.eqms.modules.nre_projects.service import compute_nre_dashboard
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry
    from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type
    from app.eqms.modules.rep_traceability.service import delete_sales_order_with_cleanup
    from app.eqms.storage import storage_from_config
    from flask import current_app

    so = _find_target(s)
    if so is None:
        print("TASK A execute: 0000383 already gone")
    else:
        dists = s.query(DistributionLogEntry).filter(DistributionLogEntry.sales_order_id == so.id).count()
        if so.id != TARGET_ID or dists != 0 or _line_pairs(so) != EXPECTED_LINES:
            print("TASK A STOP: id/lines/dists do not match frozen target")
            print(f"  id={so.id} dists={dists} lines={_line_pairs(so)}")
            raise SystemExit(2)
        tracker = s.query(NREProjectEntry).filter(NREProjectEntry.sales_order_id == so.id).all()
        for ent in tracker:
            print(f"  nulling tracker entry id={ent.id}")
            ent.sales_order_id = None
        cust_id = so.customer_id
        storage = storage_from_config(current_app.config)
        result = delete_sales_order_with_cleanup(
            s,
            so,
            user=user,
            storage=storage,
            delete_orphan_customer=False,
        )
        s.flush()
        ucsd = s.get(Customer, cust_id) if cust_id else None
        print(
            f"TASK A execute: deleted id={TARGET_ID} customer_kept={ucsd is not None} "
            f"name={_ascii(ucsd.facility_name if ucsd else None)} "
            f"storage_deleted={result.get('storage_deleted')} "
            f"storage_failed={result.get('storage_failed')}"
        )
        if ucsd is None:
            print("TASK A STOP: UCSD customer missing after delete")
            raise SystemExit(3)

    print("TASK C execute retype:")
    remaining = _nre_catheter_rows(s)
    for o in remaining:
        before = o.order_type
        if o.order_type_is_manual:
            print(f"  skip manual id={o.id} {_ascii(o.order_number)}")
            continue
        safe_apply_order_type(s, o, user=user)
        print(f"  id={o.id} {_ascii(o.order_number)} {before} -> {o.order_type}")
    if not remaining:
        print("  (none)")

    today = date.today()
    qstart = date(today.year, ((today.month - 1) // 3) * 3 + 1, 1)
    dash = compute_nre_dashboard(s, start_date=qstart, end_date=today)
    print(
        f"Still to invoice current quarter: {dash['still_to_invoice']} "
        f"(invoiced={dash['revenue']} projects={dash['project_count']})"
    )
    leftover = [o.order_number for o in dash["orders"] if o.order_number and "383" in str(o.order_number)]
    print(f"0000383 on dashboard: {bool(leftover)}")


def main() -> None:
    from app.eqms import create_app
    from app.eqms.db import db_session

    print(f"Mode: {'EXECUTE' if not DRY_RUN else 'DRY RUN'}")
    app = create_app()
    with app.app_context():
        s = db_session()
        user = _admin(s)
        print(f"actor={_ascii(user.email if user else None)} id={user.id if user else None}")
        try:
            preview(s)
            if DRY_RUN:
                s.rollback()
                print("DRY RUN -- re-run with --execute to write.")
                return
            execute(s, user)
            s.commit()
            print("COMMITTED")
        except Exception:
            s.rollback()
            raise


if __name__ == "__main__":
    main()
