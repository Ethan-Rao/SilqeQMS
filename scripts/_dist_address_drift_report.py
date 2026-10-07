"""Generate the follow-up report on customer address drift.

Compares each customer's stored Ship To address against the addresses its own
shipments actually carried, and classifies the difference so the remaining work
can be triaged. Read-only.
"""
from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

OUT = ROOT / "docs" / "Distribution Reconciliation" / "CUSTOMER_ADDRESS_DRIFT_2026-10-06.md"


def street_number(addr: str | None) -> str:
    m = re.match(r"\s*(\d+)", addr or "")
    return m.group(1) if m else ""


def has_street_number(addr: str | None) -> bool:
    return bool(street_number(addr))


def main() -> None:
    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.customer_profiles.utils import compute_facility_key_from_ship_to
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry

    app = create_app()
    rows = []
    with app.app_context():
        s = db_session()
        for c in s.query(Customer).order_by(Customer.id).all():
            ds = s.query(DistributionLogEntry).filter(
                DistributionLogEntry.customer_id == c.id).all()
            if not ds:
                continue
            addrs = collections.Counter()
            keys = collections.Counter()
            for d in ds:
                if not (d.address1 or "").strip():
                    continue
                addrs[(d.address1, d.city, d.zip)] += 1
                try:
                    keys[compute_facility_key_from_ship_to(
                        address1=d.address1, city=d.city, state=d.state, zip=d.zip,
                        facility_name=d.facility_name)] += 1
                except Exception:
                    pass
            if not addrs or c.company_key in keys:
                continue
            top, n = addrs.most_common(1)[0]
            rows.append({
                "id": c.id, "name": c.facility_name,
                "stored": c.address1, "stored_city": c.city, "stored_zip": c.zip,
                "key": c.company_key,
                "ship": top[0], "ship_city": top[1], "ship_zip": top[2],
                "n": n, "total": sum(addrs.values()),
            })

    def zip5(z: str | None) -> str:
        return re.sub(r"\D", "", z or "")[:5]

    cat_a, cat_b, cat_c = [], [], []
    for r in rows:
        if not has_street_number(r["stored"]):
            cat_a.append(r)
        elif (street_number(r["stored"]) == street_number(r["ship"])
              and zip5(r["stored_zip"]) == zip5(r["ship_zip"])):
            cat_b.append(r)
        else:
            cat_c.append(r)

    def table(rs) -> list[str]:
        out = ["| # | Profile | Stored Ship To | Address on shipments | Shipments |",
               "|---|---|---|---|---|"]
        for r in rs:
            stored = f"{r['stored']}, {r['stored_city']} {r['stored_zip']}"
            ship = f"{r['ship']}, {r['ship_city']} {r['ship_zip']}"
            out.append(f"| {r['id']} | {r['name']} | {stored} | {ship} | "
                       f"{r['n']} of {r['total']} |")
        return out

    L = [
        "# Customer address drift — follow-up list",
        "",
        "Generated 2026-10-06 after the customer profile alignment pass.",
        "",
        "## Why this matters",
        "",
        "Customer identity is keyed on the Ship To address, never on the facility",
        "name. When a profile's stored address does not normalise to the same key as",
        "the address its shipments actually carry, two things follow:",
        "",
        "1. Importing a future sales order for that site creates a **second profile**",
        "   instead of matching the existing one. Every duplicate merged in this pass",
        "   was created that way.",
        "2. The admin tool that attaches an unmatched distribution to a customer",
        "   cannot resolve the site and has to be done by hand.",
        "",
        "None of this changes any current dashboard figure — the shipments are already",
        "attached to the right profiles. It is about preventing the duplicates from",
        "coming back.",
        "",
        f"{len(rows)} profiles drifted, in three groups.",
        "",
        "## A. Stored address is not a street address",
        "",
        f"{len(cat_a)} profiles were created with a person's or practice's name in the",
        "street field, so they have no usable address key at all. The real street is",
        "known from the shipping record and can be adopted directly.",
        "",
    ]
    L += table(cat_a)
    L += [
        "",
        "## B. Same building, different spelling",
        "",
        f"{len(cat_b)} profiles carry the same street number as their shipments but a",
        "different spelling — abbreviations (Turnpike vs TPKE, Third vs 3RD), a",
        "suite suffix, or a typo. Adopting the USPS-validated form from the shipping",
        "record is safe; these are the same address.",
        "",
    ]
    L += table(cat_b)
    L += [
        "",
        "## C. Conflicting address — needs your confirmation",
        "",
        f"{len(cat_c)} profiles disagree with their shipments on the street number or",
        "the town, so one of the two is wrong and the data cannot say which. These are",
        "left untouched.",
        "",
    ]
    L += table(cat_c)
    L += [
        "",
        "Notes on group C:",
        "",
        "- **#611 Juistine Delmastro** — stored `38 Powel Avenue, Newport RI`, shipped",
        "  `70 KENYON AVE STE 210, WAKEFIELD RI`. Different towns entirely.",
        "- **#636 Rio Grande Primary** — `2201` vs `2210 N Stanton St`, a likely digit",
        "  transposition, but either could be the real one.",
        "- **#653 Onawa** — same street number but stored as `West Des Moines IA 50266`",
        "  against a shipment to `ONAWA IA 51040`. The profile name matches the",
        "  shipment, so the stored city and ZIP are probably the wrong ones.",
        "- **#658 Carolinas Rehabilitation** — stored `1100 Blythe Blvd.`, shipped",
        "  `1000 BLYTHE BLVD`, which is also where #652 Carolinas Healthcare System",
        "  shipped. If those two profiles are one site they should be merged.",
        "- **#666 Ethan Rao** — shipped to `MSB 2224, LOS ANGELES 90095`, a UCLA",
        "  building code rather than a street. The stored `607 Charles E Yound Drive E`",
        "  also misspells `Young`.",
        "",
        "## Profiles that drifted on only some shipments",
        "",
        "Two Aspirus profiles already key correctly for part of their history, so they",
        "are not in the tables above, but their shipments are inconsistent:",
        "",
        "- **#614 Aspirus Urology Wausau** — stored `3300 Westhill Dr.`; ten shipments",
        "  say `330 Westhill Drive` with no ZIP+4, one says `3300 WESTHILL DR` with",
        "  ZIP+4 `54401-4710`. Only the `3300` form carries USPS validation, so the",
        "  stored address is most likely right and the repeated `330` is a copied typo.",
        "  This is the drift that produced the duplicate profile merged in this pass.",
        "- **#625 Aspirus Wisconsin Rapids** — three shipments to `400 DEWEY ST` and",
        "  three to `410 DEWEY ST`, both with ZIP+4 `54494-4715`. Needs confirmation of",
        "  which building, or whether both are in use.",
        "",
        "## Separate observation: profiles named after people",
        "",
        "Twenty-two profiles are filed under an individual's name rather than the",
        "facility. One of them, `Gina Koehler`, turned out to be a duplicate of",
        "Cleveland Clinic Foundation and was merged in this pass. The rest each have",
        "their own address and are not duplicates of anything, so they were left",
        "alone — but they read oddly on the sales dashboard, where they appear as",
        "customers alongside hospital names.",
        "",
        "## Closed: Health Products For You orders without shipments",
        "",
        "HPFY (#620) has 32 sales orders, of which 20 have no shipment attached. The",
        "orders with shipments are round bulk quantities (10, 20, 30, 40, 50 units)",
        "while the orders without are irregular (5, 6, 8, 9, 11, 12, 13, 14, 15, 16,",
        "19 units), and the two kinds are interleaved under consecutive order numbers.",
        "",
        "Confirmed 7 Oct 2026 that these orders are not relevant to distribution",
        "tracking and can be disregarded. They are not missing distribution records.",
        "",
        "## Left for manual review",
        "",
        "- Distribution with order number `SO 00001129` — eight digits, no sales order",
        "  link, and the intended order cannot be determined from the data.",
        "- 32 distributions from orders 0000102–0000164 still have no sales order,",
        "  pending the 2024 sales order PDFs.",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"  A (no street number): {len(cat_a)}")
    print(f"  B (same number, spelling): {len(cat_b)}")
    print(f"  C (conflicting): {len(cat_c)}")


if __name__ == "__main__":
    main()
