"""Apply the lot numbers confirmed against the manufacturing records.

The reconciliation of 6 Oct 2026 left 15 distribution_lines holding a value that
was not a lot number. They were deliberately not inferred, because a lot guessed
from a neighbouring shipment would misdirect a recall. These are the ones since
confirmed from the manufacturing records.

Each correction is checked against LotLog.csv before it is written: the lot must
exist, must be registered to the SKU on that line, and must have been
manufactured before the shipment went out.

Where the corrected line carries the parent entry's primary SKU, the entry's own
lot_number is updated with it, so the header and the lines agree.

    python scripts/dist_lot_corrections_2026_10.py
    python scripts/dist_lot_corrections_2026_10.py --execute
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

# line_id -> (lot, rationale)
CORRECTIONS = {
    1614: ("SLQ-05132026", "Confirmed from manufacturing records: the 16 Fr on "
                           "SO 0000391 was picked from SLQ-05132026."),
    1649: ("SLQ-05132026", "Confirmed from manufacturing records: the 16 Fr on "
                           "SO 0000403 was picked from SLQ-05132026."),
    1181: ("SLQ-01242025", "Confirmed from manufacturing records: the 2025 18 Fr "
                           "shipments in this set were picked from SLQ-01242025."),
    1223: ("SLQ-01242025", "Confirmed from manufacturing records: the 2025 18 Fr "
                           "shipments in this set were picked from SLQ-01242025."),
    1266: ("SLQ-01242025", "Confirmed from manufacturing records: the 2025 18 Fr "
                           "shipments in this set were picked from SLQ-01242025."),
    1257: ("SLQ-11192024", "Confirmed from manufacturing records: SO 0000216 was "
                           "picked from SLQ-11192024."),
}

LOG: list[str] = []


def as_date(v):
    """LotLog dates come back as text; accept either form."""
    if v is None or isinstance(v, date):
        return v
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(str(v).strip(), fmt).date()
        except ValueError:
            continue
    return None


def say(msg: str = "") -> None:
    print(msg, flush=True)
    LOG.append(msg)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    dry = not args.execute

    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.rep_traceability.models import DistributionLine, DistributionLogEntry
    from app.eqms.modules.shipstation_sync.parsers import (
        load_lot_log_with_inventory,
        resolve_lotlog_path,
    )

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )
        lot_to_sku, _corr, lot_inventory, _years = load_lot_log_with_inventory(
            resolve_lotlog_path())
        from app.eqms.modules.shipstation_sync.parsers import load_lot_dates
        lot_mfg, _exp = load_lot_dates(resolve_lotlog_path())

        say("=" * 92)
        say(f"LOT CORRECTIONS   mode={'DRY RUN' if dry else 'EXECUTE'}")
        say(f"actor={actor.email}  {datetime.now().isoformat(timespec='seconds')}")
        say(f"LotLog lots loaded: {len(set(lot_to_sku.values()) or [])} SKUs, "
            f"{len(lot_inventory)} lots with inventory")
        say("=" * 92)

        blocked = 0
        applied = 0
        for line_id, (lot, reason) in CORRECTIONS.items():
            line = s.get(DistributionLine, line_id)
            if line is None:
                say(f"  line {line_id}: NOT FOUND; skipping")
                blocked += 1
                continue
            entry = s.get(DistributionLogEntry, line.distribution_entry_id)

            # Guard 1: the lot must be registered to this SKU in the LotLog.
            registered_sku = lot_to_sku.get(lot.upper())
            if registered_sku and registered_sku.upper() != (line.sku or "").upper():
                say(f"  line {line_id}: BLOCKED -- {lot} is registered to "
                    f"{registered_sku}, but the line is {line.sku}")
                blocked += 1
                continue
            if not registered_sku:
                say(f"  line {line_id}: BLOCKED -- {lot} is not in LotLog.csv")
                blocked += 1
                continue

            # Guard 2: the lot must predate the shipment.
            mfg = as_date(lot_mfg.get(lot.upper()))
            if mfg and entry.ship_date and mfg > entry.ship_date:
                say(f"  line {line_id}: BLOCKED -- {lot} was made {mfg}, after the "
                    f"{entry.ship_date} shipment")
                blocked += 1
                continue

            primary = (entry.sku or "").upper() == (line.sku or "").upper()
            say(f"  line {line_id}  dist {entry.id}  {entry.order_number}  "
                f"{entry.ship_date}  {line.sku} x{line.quantity}")
            say(f"     lot {line.lot_number!r} -> {lot!r}   "
                f"(LotLog: {registered_sku}, made {mfg})")
            if primary:
                say(f"     entry header lot {entry.lot_number!r} -> {lot!r} "
                    "(line carries the entry's primary SKU)")
            applied += 1

            if not dry:
                before = {"line_lot": line.lot_number, "entry_lot": entry.lot_number}
                line.lot_number = lot
                if primary:
                    entry.lot_number = lot
                record_event(
                    s,
                    actor=actor,
                    action="distribution.lot.correct",
                    entity_type="DistributionLine",
                    entity_id=str(line.id),
                    reason=reason,
                    metadata={
                        "before": before,
                        "after": {"line_lot": line.lot_number,
                                  "entry_lot": entry.lot_number},
                        "distribution_entry_id": entry.id,
                        "order_number": entry.order_number,
                        "sku": line.sku,
                        "quantity": line.quantity,
                        "lotlog_sku": registered_sku,
                    },
                )
        if not dry:
            s.commit()

        say()
        say(f"  corrections applied: {applied}   blocked: {blocked}")

        # ------------------------------------------------ lot consumption check
        say()
        say("-- lot consumption after these corrections ------------------------------")
        from sqlalchemy import func
        for lot in sorted({l for l, _ in CORRECTIONS.values()}):
            shipped = (
                s.query(func.coalesce(func.sum(DistributionLine.quantity), 0))
                .filter(func.upper(DistributionLine.lot_number) == lot.upper())
                .scalar()
            )
            total = lot_inventory.get(lot.upper())
            if total is None:
                say(f"   {lot}: shipped {shipped}, lot size unknown")
            else:
                say(f"   {lot}: shipped {shipped} of {total} "
                    f"({'OVER-CONSUMED' if shipped > total else 'ok'})")

        # --------------------------------------------------- what is still open
        say()
        say("-- lines still holding a value that is not a lot ------------------------")
        from sqlalchemy import text
        rows = s.execute(text("""
            SELECT l.id lid, l.sku, l.lot_number, l.quantity,
                   d.id did, d.order_number, d.ship_date, d.facility_name
            FROM distribution_lines l
            JOIN distribution_log_entries d ON d.id = l.distribution_entry_id
            WHERE l.lot_number !~* '^SLQ-([0-9]{8}|[0-9]{11})$'
            ORDER BY d.ship_date, l.id""")).mappings().all()
        pre, post = 0, 0
        for r in rows:
            if r["ship_date"].year < 2025:
                pre += 1
                continue
            post += 1
            say(f"   line {r['lid']} dist {r['did']} {r['order_number']} "
                f"{r['ship_date']} {r['sku']} x{r['quantity']} {r['lot_number']!r} "
                f"{r['facility_name']}")
        say(f"   2025-onward still open: {post}")
        say(f"   pre-2025 (no remediation required): {pre}")

        say()
        say("=" * 92)
        say("DRY RUN -- nothing written" if dry else "EXECUTED")
        say("=" * 92)

    (ROOT / "_dist_lot_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
