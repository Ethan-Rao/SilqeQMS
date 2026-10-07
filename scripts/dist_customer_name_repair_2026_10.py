"""Replace three customer facility names that record a person or a street.

These profiles were created from sales-order PDFs whose SHIP TO block carried a
contact's name or a fragment of the address instead of the facility. The name
is what the distribution log and the sales dashboard display, so the record did
not identify the consignee.

The shipping addresses are deliberately left alone. Customer matching on import
keys off ``company_key``, which is derived from the address, so editing an
address here would stop future shipments matching and spawn a duplicate.

    python scripts/dist_customer_name_repair_2026_10.py            # dry run
    python scripts/dist_customer_name_repair_2026_10.py --execute
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

LOG: list[str] = []


def say(line: str = "") -> None:
    print(line)
    LOG.append(line)


# Each entry: customer id, facility name, contact to retain, rationale.
RENAMES = [
    {
        "customer_id": 683,
        "facility_name": "CoMedical Inc.",
        "contact_name": "Tom Lamb",
        "reason": (
            "Facility name recorded the buyer's contact, 'Tom Lamb', rather than "
            "the consignee. The profile already carries customer_code 'COMED' and "
            "ships to 13500 Linden Ave N, Seattle WA 98133, CoMedical Inc.'s "
            "address. The person is retained as the contact."
        ),
    },
    {
        "customer_id": 666,
        "facility_name": "UC Los Angeles",
        "contact_name": "Ethan Rao",
        "reason": (
            "Facility name recorded the ordering contact, 'Ethan Rao', rather than "
            "the consignee. The ship-to address, 607 Charles E Young Drive E, Los "
            "Angeles CA 90095, is the UCLA campus. The person is retained as the "
            "contact."
        ),
    },
    {
        "customer_id": 660,
        "facility_name": "Temple University Health System - Rockledge",
        "contact_name": None,
        "reason": (
            "Facility name held 'Huntingdon', a fragment of the street address, "
            "rather than the consignee. Sales order 0000296 names the sold-to as "
            "Temple University Health System, Philadelphia PA, shipping to 50 "
            "Huntingdon Pike Fl 3, Rockledge PA 19046. Named to match the existing "
            "Temple sites #651 and #677."
        ),
    },
]


def full_payload(c) -> dict:
    """update_customer() treats absent keys as cleared, so send every field."""
    return {
        "facility_name": c.facility_name,
        "address1": c.address1,
        "address2": c.address2,
        "city": c.city,
        "state": c.state,
        "zip": c.zip,
        "sold_to_address1": c.sold_to_address1,
        "sold_to_city": c.sold_to_city,
        "sold_to_state": c.sold_to_state,
        "sold_to_zip": c.sold_to_zip,
        "contact_name": c.contact_name,
        "contact_phone": c.contact_phone,
        "contact_email": c.contact_email,
        "primary_rep_id": str(c.primary_rep_id or ""),
        "is_distributor": bool(c.is_distributor),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    dry = not args.execute

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.customer_profiles.service import update_customer
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = (
            s.query(User).filter(User.email.ilike(os.environ.get("ADMIN_EMAIL", ""))).first()
            or s.query(User).order_by(User.id).first()
        )

        say("=" * 92)
        say("Customer facility-name repair -- profiles named after a person or street")
        say("=" * 92)

        for item in RENAMES:
            cid = item["customer_id"]
            c = s.get(Customer, cid)
            say()
            if c is None:
                say(f"   #{cid}: profile absent; skipping")
                continue
            if c.facility_name == item["facility_name"]:
                say(f"   #{cid}: already {c.facility_name!r}; skipping")
                continue

            n = s.query(DistributionLogEntry).filter(
                DistributionLogEntry.customer_id == cid).count()
            say(f"   #{cid}: {c.facility_name!r} -> {item['facility_name']!r}")
            say(f"     {c.address1}, {c.city} {c.state} {c.zip} ({n} distributions)")
            contact = item["contact_name"]
            if contact and c.contact_name != contact:
                say(f"     contact_name: {c.contact_name!r} -> {contact!r}")
            say(f"     company_key {c.company_key!r} left as is")
            say(f"     {item['reason']}")

            if not dry:
                payload = full_payload(c)
                payload["facility_name"] = item["facility_name"]
                if contact:
                    payload["contact_name"] = contact
                update_customer(s, c, payload, user=actor, reason=item["reason"])
                s.commit()

        say()
        say("=" * 92)
        say("DRY RUN -- nothing written" if dry else "EXECUTED")
        say("=" * 92)

    (ROOT / "_dist_name_repair_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
