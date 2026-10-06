"""Record audit events for the October 2026 distribution reconciliation.

Tasks A, B, D and F of dist_cleanup_2026_10.py write through the ORM rather than
the distribution service, so they produce no audit event of their own. This reads
the committed run log and appends one audit event per change, plus a summary
event, so the reconciliation is traceable in the system of record.

    python scripts/_dist_cleanup_audit.py --execute
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

LOG = ROOT / "_dist_cleanup_log.txt"
REASON = (
    "Distribution reconciliation Oct-2026: corrected against source sales order "
    "PDFs and packing slips in Distribution/"
)

RE_A = re.compile(
    r"^\s{2}(?P<num>\d{7}):\s+(?P<before>\d+)u\s*->\s*(?P<after>\d+)u\s+"
    r"\[(?P<bsig>[^\]]*)\]\s*->\s*\[(?P<asig>[^\]]*)\]\s*\((?P<src>[^)]+)\)\s*$"
)
RE_B = re.compile(
    r"^\s{2}(?P<num>\d{7}): CREATE date=(?P<date>\S+) customer_id=(?P<cid>\d+) "
    r"units=(?P<units>\d+) \[(?P<sig>[^\]]*)\]\s*$"
)
RE_F = re.compile(
    r"^\s{2}dist (?P<did>\d+) (?P<ord>\S+ ?\d+) '(?P<fac>[^']*)' -> customer "
    r"(?P<cid>\d+) '(?P<cfac>[^']*)'\s*$"
)
RE_D = re.compile(
    r"^\s{2}(?P<num>\d{7}): linked (?P<n>\d+) distribution\(s\) to SO #(?P<soid>\d+)\s*$"
)
RE_E_HDR = re.compile(
    r"^\s{2}dist (?P<did>\d+)(?: line (?P<lid>\d+))? order=(?P<num>\d{7}) "
    r"(?P<sku>\S+) x(?P<qty>\d+) (?P<date>\S+) lot='(?P<lot>[^']*)'\s*$"
)
RE_E_SET = re.compile(r"^\s+-> set lot (?P<lot>\S+)\s*$")


def parse(text: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {"A": [], "B": [], "D": [], "E": [], "F": []}
    pending_e: dict | None = None
    for line in text.splitlines():
        if (m := RE_A.match(line)):
            out["A"].append(m.groupdict())
        elif (m := RE_B.match(line)):
            out["B"].append(m.groupdict())
        elif (m := RE_F.match(line)):
            out["F"].append(m.groupdict())
        elif (m := RE_D.match(line)):
            out["D"].append(m.groupdict())
        elif (m := RE_E_HDR.match(line)):
            pending_e = m.groupdict()
        elif pending_e and (m := RE_E_SET.match(line)):
            pending_e["new_lot"] = m.group("lot")
            out["E"].append(pending_e)
            pending_e = None
        elif pending_e and line.strip().startswith("->"):
            pending_e = None
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    changes = parse(LOG.read_text(encoding="utf-8"))
    for k, v in changes.items():
        print(f"  task {k}: {len(v)} change(s) parsed")
    total = sum(len(v) for v in changes.values())
    print(f"  total: {total}")
    if not args.execute:
        print("\nDRY RUN - pass --execute to append audit events.")
        return

    os.environ.setdefault("FLASK_ENV", "production")
    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )
        n = 0
        for c in changes["A"]:
            record_event(
                s, actor=actor, action="sales_order.lines_corrected",
                entity_type="sales_order", entity_id=c["num"], reason=REASON,
                metadata={
                    "units_before": int(c["before"]), "units_after": int(c["after"]),
                    "lines_before": c["bsig"], "lines_after": c["asig"],
                    "source_document": c["src"],
                    "root_cause": "PDF parser read a digit from the item description "
                                  "instead of the ORDERED column and ignored the "
                                  "box-of-10 packaging multiplier",
                },
            )
            n += 1
        for c in changes["B"]:
            record_event(
                s, actor=actor, action="sales_order.created_from_source_document",
                entity_type="sales_order", entity_id=c["num"], reason=REASON,
                metadata={
                    "order_date": c["date"], "customer_id": int(c["cid"]),
                    "units": int(c["units"]), "lines": c["sig"],
                    "note": "Order was present on paper and had distributions "
                            "recorded, but no sales order existed in the system",
                },
            )
            n += 1
        for c in changes["F"]:
            record_event(
                s, actor=actor, action="distribution_log_entry.customer_linked",
                entity_type="distribution_log_entry", entity_id=c["did"], reason=REASON,
                metadata={
                    "order_number": c["ord"], "ship_to_name": c["fac"],
                    "customer_id": int(c["cid"]), "customer_facility": c["cfac"],
                    "method": "address-keyed identity "
                              "(find_unique_customer_for_distribution_ship_to)",
                },
            )
            n += 1
        for c in changes["D"]:
            record_event(
                s, actor=actor, action="distribution_log_entry.rematched_to_sales_order",
                entity_type="sales_order", entity_id=c["num"], reason=REASON,
                metadata={"sales_order_id": int(c["soid"]), "distributions_linked": int(c["n"])},
            )
            n += 1
        for c in changes["E"]:
            record_event(
                s, actor=actor, action="distribution_log_entry.lot_corrected",
                entity_type="distribution_log_entry", entity_id=c["did"], reason=REASON,
                metadata={
                    "distribution_line_id": c.get("lid"), "order_number": c["num"],
                    "sku": c["sku"], "quantity": int(c["qty"]), "ship_date": c["date"],
                    "lot_before": c["lot"], "lot_after": c["new_lot"],
                    "evidence": "packing slip lot for this order and SKU",
                },
            )
            n += 1

        record_event(
            s, actor=actor, action="distribution.reconciliation_completed",
            entity_type="distribution_log", entity_id="2026-10", reason=REASON,
            metadata={
                "completed_at": datetime.now().isoformat(timespec="seconds"),
                "sales_orders_corrected": len(changes["A"]),
                "sales_orders_created": len(changes["B"]),
                "distributions_customer_linked": len(changes["F"]),
                "distributions_rematched": sum(int(c["n"]) for c in changes["D"]),
                "lots_corrected": len(changes["E"]),
                "duplicate_distributions_deleted": 6,
                "backup": "C:/Users/Ethan/SilqQMS_backups/pre_dist_cleanup_20261006_150111",
                "open_items": [
                    "4 distributions await a new customer record "
                    "(Ancora Anchorage, Aspirus Riverview 410 Dewey St, "
                    "Great Falls Helena, Cleveland Clinic Avon)",
                    "15 distribution lines retain an unresolvable lot number",
                    "orders 0000371/0000372 are 20 Fr and 22 Fr and cannot be stored "
                    "while VALID_SKUS excludes them",
                    "order 0000238 shipped 33 units against 30 ordered",
                ],
            },
        )
        n += 1
        s.commit()
        print(f"\nCOMMITTED {n} audit events.")


if __name__ == "__main__":
    main()
