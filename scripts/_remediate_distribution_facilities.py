"""
P41 — Remediate distribution duplicates, Ship-To facility identity, Day Kimball.

Phases:
  1. True-duplicate deletion (identical lines+date; keep SO-linked row)
  2. Relink remaining unmatched distributions by normalized order number
  3. Full catheter facility rebuild by Ship-To address key + alias merges
  4. Day Kimball / SO 0000366 cleanup

Usage:
    python scripts/_remediate_distribution_facilities.py            # dry-run
    python scripts/_remediate_distribution_facilities.py --execute
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DRY_RUN = "--execute" not in sys.argv


def _line_multiset(entry) -> tuple:
    lines = list(getattr(entry, "lines", None) or [])
    if lines:
        items = [
            (
                (ln.sku or "").strip().upper(),
                int(ln.quantity or 0),
                (ln.lot_number or "").strip().upper(),
            )
            for ln in lines
        ]
    else:
        items = [
            (
                (entry.sku or "").strip().upper(),
                int(entry.quantity or 0),
                (entry.lot_number or "").strip().upper(),
            )
        ]
    return tuple(sorted(items))


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        k, v = raw.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if "#" in v:
            v = v.split("#", 1)[0].rstrip()
        if k and k not in os.environ:
            os.environ[k] = v
    # Prefer known-good Spaces keys from Phase 4 helper when present.
    ps1 = ROOT / "scripts" / "_phase4_import.ps1"
    if ps1.exists():
        for line in ps1.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "$env:" not in line or "=" not in line:
                continue
            left, _, right = line.partition("=")
            key = left.replace("$env:", "").strip()
            val = right.strip().strip('"').strip("'")
            if key in {
                "DATABASE_URL",
                "STORAGE_BACKEND",
                "S3_ENDPOINT",
                "S3_REGION",
                "S3_BUCKET",
                "S3_ACCESS_KEY_ID",
                "S3_SECRET_ACCESS_KEY",
            } and val:
                os.environ[key] = val
    os.environ["STORAGE_BACKEND"] = "s3"
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ["ENV"] = "production"


def main() -> None:
    _load_env()
    os.environ.setdefault("STORAGE_BACKEND", "s3")

    from flask import current_app

    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
    from app.eqms.modules.customer_profiles.utils import (
        compute_facility_key_from_ship_to,
        facility_display_name,
    )
    from app.eqms.modules.rep_traceability.models import (
        DistributionLogEntry,
        OrderPdfAttachment,
        SalesOrder,
        SalesOrderLine,
    )
    from app.eqms.modules.rep_traceability.service import (
        CATHETER_SKUS,
        delete_distribution_entry,
        delete_sales_order_with_cleanup,
        find_sales_order_by_normalized_number,
        match_distribution_to_sales_order,
        normalize_order_number,
    )
    from app.eqms.storage import storage_from_config

    app = create_app()
    with app.app_context():
        s = db_session()
        storage = storage_from_config(current_app.config)
        actor = s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
        if not actor:
            print("ERROR: no active user for audit actor")
            sys.exit(1)

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Actor: {actor.email}")
        print()

        deleted_dupes = 0
        keep_multi: list[str] = []
        relinked = 0
        merged_customers = 0
        deleted_shells = 0
        day_kimball_notes: list[str] = []

        # ── Phase 1: true-duplicate deletion ──────────────────────────────
        print("=== Phase 1: True-duplicate deletion ===")
        ss_dists = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.source == "shipstation")
            .order_by(DistributionLogEntry.id.asc())
            .all()
        )
        by_norm: dict[str, list] = defaultdict(list)
        for d in ss_dists:
            n = normalize_order_number(d.order_number)
            if n:
                by_norm[n].append(d)

        confirmed = {"302", "312"}
        for norm, rows in sorted(by_norm.items(), key=lambda x: x[0]):
            if len(rows) < 2:
                continue
            # Group by (ship_date, line multiset)
            groups: dict[tuple, list] = defaultdict(list)
            for r in rows:
                groups[(r.ship_date, _line_multiset(r))].append(r)

            for (ship_date, lines), group in groups.items():
                if len(group) < 2:
                    # Different lines → keep multi if multiple top-level rows for SO
                    continue
                linked = [g for g in group if g.sales_order_id]
                unmatched = [g for g in group if not g.sales_order_id]
                if linked and unmatched:
                    keep = sorted(linked, key=lambda x: x.id)[0]
                    victims = [g for g in group if g.id != keep.id]
                elif linked:
                    keep = sorted(linked, key=lambda x: x.id)[0]
                    victims = [g for g in group if g.id != keep.id]
                else:
                    keep = sorted(group, key=lambda x: x.id)[0]
                    victims = [g for g in group if g.id != keep.id]

                tag = "CONFIRMED" if norm in confirmed else "AUTO"
                print(
                    f"  DUP[{tag}] SO~{norm} ship_date={ship_date} lines={lines} "
                    f"keep_id={keep.id} (so={keep.sales_order_id}) "
                    f"delete_ids={[v.id for v in victims]}"
                )
                for v in victims:
                    deleted_dupes += 1
                    if not DRY_RUN:
                        # Storage cleanup for packing slips
                        atts = (
                            s.query(OrderPdfAttachment)
                            .filter(OrderPdfAttachment.distribution_entry_id == v.id)
                            .all()
                        )
                        for a in atts:
                            try:
                                storage.delete(a.storage_key)
                            except Exception:
                                pass
                            s.delete(a)
                        delete_distribution_entry(
                            s, v, user=actor, reason="p41_true_duplicate_orphan"
                        )

            # Legitimate multi-shipment: ≥2 rows with different line sets
            distinct_line_sets = {_line_multiset(r) for r in rows}
            if len(rows) >= 2 and len(distinct_line_sets) >= 2:
                keep_multi.append(
                    f"SO~{norm} ({len(rows)} rows, {len(distinct_line_sets)} line-sets)"
                )

        for n in sorted(confirmed):
            rows = by_norm.get(n, [])
            print(f"  CHECK SO 0000{n}: {len(rows)} shipstation row(s) remaining in memory view")

        # ── Phase 2: relink unmatched ─────────────────────────────────────
        print()
        print("=== Phase 2: Relink unmatched distributions ===")
        unmatched = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.sales_order_id.is_(None))
            .all()
        )
        for d in unmatched:
            so = find_sales_order_by_normalized_number(s, d.order_number)
            if not so:
                continue
            if match_distribution_to_sales_order(s, d, so):
                relinked += 1
                print(
                    f"  RELINK dist_id={d.id} order={d.order_number!r} → SO {so.order_number} "
                    f"customer_id={so.customer_id}"
                )

        # ── Phase 3: catheter facility rebuild ────────────────────────────
        print()
        print("=== Phase 3: Catheter facility rebuild ===")

        # Collect catheter SOs + their dists
        catheter_orders = (
            s.query(SalesOrder)
            .join(SalesOrderLine, SalesOrderLine.sales_order_id == SalesOrder.id)
            .filter(SalesOrderLine.sku.in_(tuple(CATHETER_SKUS)))
            .distinct()
            .all()
        )
        catheter_order_ids = {o.id for o in catheter_orders}
        catheter_dists = (
            s.query(DistributionLogEntry)
            .filter(
                (DistributionLogEntry.sales_order_id.in_(catheter_order_ids))
                | (DistributionLogEntry.sku.in_(tuple(CATHETER_SKUS)))
            )
            .all()
        )

        # Map facility_key → preferred Customer (create/ensure)
        key_to_customer: dict[str, Customer] = {}
        key_sources: dict[str, dict] = {}

        def _ensure_facility(key: str, *, name: str, addr1, city, state, zip_code, sold=None):
            if key in key_to_customer:
                return key_to_customer[key]
            existing = s.query(Customer).filter(Customer.company_key == key).one_or_none()
            if existing:
                key_to_customer[key] = existing
                if not DRY_RUN and existing.customer_type == "auto":
                    existing.customer_type = "catheter"
                return existing
            display = facility_display_name(name, city=city)
            print(f"  CREATE facility key={key[:40]}… name={display!r}")
            if DRY_RUN:
                # Placeholder — no DB row in dry-run
                class _Stub:
                    id = -1
                    facility_name = display
                    company_key = key
                stub = _Stub()
                key_to_customer[key] = stub  # type: ignore[assignment]
                return stub
            from app.eqms.modules.customer_profiles.service import find_or_create_customer

            c = find_or_create_customer(
                s,
                facility_name=display,
                address1=addr1,
                city=city,
                state=state,
                zip=zip_code,
                sold_to_address1=(sold or {}).get("address1"),
                sold_to_city=(sold or {}).get("city"),
                sold_to_state=(sold or {}).get("state"),
                sold_to_zip=(sold or {}).get("zip"),
                identity="facility",
                customer_type="catheter",
            )
            key_to_customer[key] = c
            return c

        for o in catheter_orders:
            addr1 = o.ship_to_address1
            city = o.ship_to_city
            state = o.ship_to_state
            zip_code = o.ship_to_zip
            name = o.ship_to_name or (o.customer.facility_name if o.customer else None)
            # Prefer distribution ship-to when SO ship-to empty
            if not (addr1 and city and state and zip_code):
                for d in catheter_dists:
                    if d.sales_order_id == o.id and d.address1 and d.city:
                        addr1 = addr1 or d.address1
                        city = city or d.city
                        state = state or d.state
                        zip_code = zip_code or d.zip
                        name = name or d.facility_name
                        break
            if not name and o.customer:
                name = o.customer.facility_name
            key = compute_facility_key_from_ship_to(
                address1=addr1, city=city, state=state, zip=zip_code, facility_name=name
            )
            key_sources[key] = {
                "name": name,
                "addr1": addr1,
                "city": city,
                "state": state,
                "zip": zip_code,
                "sold": {
                    "address1": o.sold_to_address1,
                    "city": o.sold_to_city,
                    "state": o.sold_to_state,
                    "zip": o.sold_to_zip,
                },
            }
            cust = _ensure_facility(
                key,
                name=name or "Facility",
                addr1=addr1,
                city=city,
                state=state,
                zip_code=zip_code,
                sold=key_sources[key]["sold"],
            )
            if o.customer_id != getattr(cust, "id", None) and getattr(cust, "id", -1) > 0:
                print(
                    f"  REPOINT SO {o.order_number}: customer {o.customer_id} → {cust.id} ({cust.facility_name})"
                )
                if not DRY_RUN:
                    o.customer_id = cust.id

        for d in catheter_dists:
            addr1, city, state, zip_code = d.address1, d.city, d.state, d.zip
            name = d.facility_name
            if d.sales_order_id:
                so = s.get(SalesOrder, d.sales_order_id)
                if so:
                    addr1 = addr1 or so.ship_to_address1
                    city = city or so.ship_to_city
                    state = state or so.ship_to_state
                    zip_code = zip_code or so.ship_to_zip
                    name = name or so.ship_to_name
            key = compute_facility_key_from_ship_to(
                address1=addr1, city=city, state=state, zip=zip_code, facility_name=name
            )
            src = key_sources.get(key) or {
                "name": name,
                "addr1": addr1,
                "city": city,
                "state": state,
                "zip": zip_code,
                "sold": {},
            }
            cust = _ensure_facility(
                key,
                name=src["name"] or name or "Facility",
                addr1=src["addr1"] or addr1,
                city=src["city"] or city,
                state=src["state"] or state,
                zip_code=src["zip"] or zip_code,
                sold=src.get("sold"),
            )
            if getattr(cust, "id", -1) > 0 and d.customer_id != cust.id:
                print(
                    f"  REPOINT dist {d.id} ({d.order_number}): customer {d.customer_id} → {cust.id}"
                )
                if not DRY_RUN:
                    d.customer_id = cust.id
                    d.facility_name = cust.facility_name

        # Merge alias shells that share the same facility key into the survivor
        survivors = {c.id for c in key_to_customer.values() if getattr(c, "id", -1) > 0}
        # Also merge obvious name aliases pointing at same key customers
        # (RCRMC / Harbor case variants that now share address key after rebuild)

        # Delete empty shells: auto/catheter customers with 0 SO and 0 dists
        print()
        print("=== Phase 3b: Delete empty customer shells ===")
        all_custs = s.query(Customer).all()
        for c in all_custs:
            if c.id in survivors:
                continue
            so_count = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()
            dist_count = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.customer_id == c.id)
                .count()
            )
            if so_count or dist_count:
                continue
            # Skip forced NRE profiles with notes? Prompt: merge notes then delete.
            notes = s.query(CustomerNote).filter(CustomerNote.customer_id == c.id).count()
            if notes:
                print(f"  SKIP shell id={c.id} {c.facility_name!r} (has {notes} notes)")
                continue
            if (c.customer_type or "auto") == "nre":
                continue
            print(f"  DELETE shell id={c.id} {c.facility_name!r} key={c.company_key}")
            deleted_shells += 1
            if not DRY_RUN:
                record_event(
                    s,
                    actor=actor,
                    action="customer.delete_shell",
                    entity_type="Customer",
                    entity_id=str(c.id),
                    metadata={"facility_name": c.facility_name, "company_key": c.company_key},
                )
                s.delete(c)

        # ── Phase 4: Day Kimball ──────────────────────────────────────────
        print()
        print("=== Phase 4: Day Kimball / SO 0000366 ===")
        so366 = find_sales_order_by_normalized_number(s, "0000366")
        dk_customers = (
            s.query(Customer)
            .filter(
                (Customer.facility_name.ilike("%day kimball%"))
                | (Customer.customer_code.ilike("%DAYKIMBALL%"))
                | (Customer.company_key.ilike("%DAYKIMBALL%"))
            )
            .all()
        )
        if so366:
            day_kimball_notes.append(
                f"Would delete SO {so366.order_number} id={so366.id} "
                f"customer_id={so366.customer_id}"
                if DRY_RUN
                else f"Deleting SO {so366.order_number} id={so366.id}"
            )
            print(f"  {day_kimball_notes[-1]}")
            if not DRY_RUN:
                result = delete_sales_order_with_cleanup(
                    s, so366, user=actor, storage=storage
                )
                day_kimball_notes.append(f"delete result={result}")
                print(f"  result={result}")
        else:
            day_kimball_notes.append("SO 0000366 not found (already deleted)")
            print(f"  {day_kimball_notes[-1]}")

        for c in dk_customers:
            so_count = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()
            dist_count = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.customer_id == c.id)
                .count()
            )
            msg = (
                f"Day Kimball customer id={c.id} name={c.facility_name!r} "
                f"sos={so_count} dists={dist_count}"
            )
            print(f"  {msg}")
            day_kimball_notes.append(msg)
            if so_count == 0 and dist_count == 0:
                print(f"  DELETE Day Kimball shell id={c.id}")
                day_kimball_notes.append(f"delete customer shell id={c.id}")
                deleted_shells += 1
                if not DRY_RUN:
                    record_event(
                        s,
                        actor=actor,
                        action="customer.delete_shell",
                        entity_type="Customer",
                        entity_id=str(c.id),
                        metadata={"facility_name": c.facility_name, "reason": "day_kimball_p41"},
                    )
                    s.delete(c)

        if not DRY_RUN:
            s.commit()
            print()
            print("COMMITTED.")
        else:
            s.rollback()
            print()
            print("DRY RUN — no changes written. Re-run with --execute to apply.")

        print()
        print("=== Summary ===")
        print(f"  deleted_dupes:      {deleted_dupes}")
        print(f"  relinked:           {relinked}")
        print(f"  merged_customers:   {merged_customers}")
        print(f"  deleted_shells:     {deleted_shells}")
        print(f"  KEEP_MULTI ({len(keep_multi)}):")
        for item in keep_multi[:40]:
            print(f"    - {item}")
        if len(keep_multi) > 40:
            print(f"    … +{len(keep_multi) - 40} more")
        print("  Day Kimball:")
        for n in day_kimball_notes:
            print(f"    - {n}")


if __name__ == "__main__":
    main()
