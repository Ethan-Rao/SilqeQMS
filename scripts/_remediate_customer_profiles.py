"""
P41b — Full customer-profile cleanup.

Decisions (Ethan 2026-07-30):
  1A  Display = clinical Ship-To facility name (prettified)
  2   Linked distributions always use SO.customer_id
  3   Merge suite / street-abbrev / word-order variants (same ZIP5 + fuzzy street)
  4A  SO PDF Ship-To is canonical address/name source
  Temple Philly vs Ft Washington stay separate; San Diego VAMC+Marathon merge

Phases:
  1. Sync every linked distribution onto its SO's customer
  2. Rekey / rename catheter customers from SO Ship-To (fallback: dist address)
  3. Merge customers that share the same fuzzy facility key
  4. Delete empty shells
  5. Report remaining mismatches

Usage:
    python scripts/_remediate_customer_profiles.py            # dry-run
    python scripts/_remediate_customer_profiles.py --execute
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


def _load_env() -> None:
    env_path = ROOT / ".env"
    if env_path.exists():
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


def _customer_score(s, customer_id: int, SalesOrder, DistributionLogEntry) -> tuple:
    so_n = s.query(SalesOrder).filter(SalesOrder.customer_id == customer_id).count()
    dist_n = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.customer_id == customer_id)
        .count()
    )
    return (so_n, dist_n, -customer_id)


def _best_clinical_name(candidates: list[str]) -> str | None:
    """Prefer clinical Ship-To facility names over payers / contact persons."""
    import re

    scored: list[tuple[int, str]] = []
    for raw in candidates:
        name = (raw or "").strip()
        if not name:
            continue
        score = 0
        upper = name.upper()
        # Strong clinical signals
        if any(t in upper for t in ("VAMC", "VA ", "VA-", "HOSPITAL", "UNIVERSITY")):
            score += 8
        if any(
            t in upper
            for t in (
                "UROLOGY", "CLINIC", "MEMORIAL", "HEALTHCARE", "MEDICAL CENTER",
                "REHABILITATION", "ASSOCIATES",
            )
        ):
            score += 5
        # Payer / distributor accounts are never the preferred display (decision 1A)
        if "MARATHON" in upper:
            score -= 20
        if upper.endswith(" CORPORATION") or " CORPORATION" in upper:
            score -= 8
        # Penalize short contact-looking names
        tokens = [t for t in re.split(r"\s+", name) if t and t not in ("—", "-")]
        if len(tokens) <= 2 and score < 5:
            score -= 3
        if re.fullmatch(r"[A-Za-z .]+,\s*[A-Z]{2}\s*\d*", name):
            score -= 5
        scored.append((score, name))
    if not scored:
        return None
    scored.sort(key=lambda x: (x[0], len(x[1])), reverse=True)
    return scored[0][1]


def main() -> None:
    _load_env()

    from app.eqms import create_app
    from app.eqms.audit import record_event
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
    from app.eqms.modules.customer_profiles.service import merge_customers
    from app.eqms.modules.customer_profiles.utils import (
        compute_facility_key_from_ship_to,
        facility_display_name,
        prettify_facility_name,
    )
    from app.eqms.modules.rep_traceability.models import (
        DistributionLogEntry,
        SalesOrder,
        SalesOrderLine,
    )
    from app.eqms.modules.rep_traceability.service import (
        CATHETER_SKUS,
        sync_distribution_customer_from_sales_order,
    )

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
        if not actor:
            print("ERROR: no active user")
            sys.exit(1)

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Actor: {actor.email}")
        print()

        synced = 0
        renamed = 0
        rekeyed = 0
        merged = 0
        shells = 0

        # ── Phase 1: linked dist -> SO customer ───────────────────────────
        print("=== Phase 1: Sync linked distributions to SO customer ===")
        linked = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.sales_order_id.isnot(None))
            .all()
        )
        for d in linked:
            so = s.get(SalesOrder, d.sales_order_id)
            if not so:
                continue
            before = (d.customer_id, d.facility_name)
            if sync_distribution_customer_from_sales_order(d, so):
                synced += 1
                print(
                    f"  SYNC dist#{d.id} SO {so.order_number}: "
                    f"cust {before[0]} -> {d.customer_id} "
                    f"name {before[1]!r} -> {d.facility_name!r}"
                )
        s.flush()

        # ── Phase 2: rekey/rename from SO Ship-To (canonical) ─────────────
        print()
        print("=== Phase 2: Rekey/rename catheter customers from SO Ship-To ===")
        catheter_order_ids = {
            r[0]
            for r in (
                s.query(SalesOrder.id)
                .join(SalesOrderLine, SalesOrderLine.sales_order_id == SalesOrder.id)
                .filter(SalesOrderLine.sku.in_(tuple(CATHETER_SKUS)))
                .distinct()
                .all()
            )
        }
        catheter_orders = (
            s.query(SalesOrder).filter(SalesOrder.id.in_(catheter_order_ids)).all()
            if catheter_order_ids
            else []
        )

        # Build preferred key/name/address per current customer from its SOs
        cust_meta: dict[int, dict] = {}
        for o in catheter_orders:
            if not o.customer_id:
                continue
            addr1 = o.ship_to_address1
            city = o.ship_to_city
            state = o.ship_to_state
            zip_code = o.ship_to_zip
            ship_name = o.ship_to_name
            # Fill city/state/zip from linked dists if SO ship fields sparse
            if not (addr1 and state and zip_code):
                for d in s.query(DistributionLogEntry).filter(
                    DistributionLogEntry.sales_order_id == o.id
                ).all():
                    addr1 = addr1 or d.address1
                    city = city or d.city
                    state = state or d.state
                    zip_code = zip_code or d.zip
                    ship_name = ship_name or d.facility_name
            key = compute_facility_key_from_ship_to(
                address1=addr1, city=city, state=state, zip=zip_code, facility_name=ship_name
            )
            display = facility_display_name(ship_name, city=city)
            meta = cust_meta.get(o.customer_id)
            if not meta or (addr1 and state and zip_code):
                cust_meta[o.customer_id] = {
                    "key": key,
                    "display": display,
                    "addr1": addr1,
                    "city": city,
                    "state": state,
                    "zip": zip_code,
                    "ship_name": ship_name,
                }

        # Also key customers that only have dists (no SO yet) from dist ship-to
        for c in s.query(Customer).all():
            if c.id in cust_meta:
                continue
            dists = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.customer_id == c.id)
                .all()
            )
            if not dists:
                continue
            d = dists[0]
            key = compute_facility_key_from_ship_to(
                address1=d.address1, city=d.city, state=d.state, zip=d.zip,
                facility_name=d.facility_name,
            )
            # Prefer SO name if any linked SO exists through dist
            ship_name = d.facility_name
            for dist in dists:
                if dist.sales_order_id:
                    so = s.get(SalesOrder, dist.sales_order_id)
                    if so and so.ship_to_name:
                        ship_name = so.ship_to_name
                        break
            cust_meta[c.id] = {
                "key": key,
                "display": facility_display_name(ship_name, city=d.city),
                "addr1": d.address1,
                "city": d.city,
                "state": d.state,
                "zip": d.zip,
                "ship_name": ship_name,
            }

        # Rename / fill address only in this phase. Keys are assigned after merges
        # so two profiles that collapse to the same fuzzy key never collide.
        for cid, meta in sorted(cust_meta.items()):
            c = s.get(Customer, cid)
            if not c:
                continue
            new_name = meta["display"]
            if new_name and c.facility_name != new_name:
                print(f"  RENAME id={c.id} {c.facility_name!r} -> {new_name!r}")
                renamed += 1
                c.facility_name = new_name
            if meta.get("addr1"):
                c.address1 = meta["addr1"]
            if meta.get("city"):
                c.city = meta["city"]
            if meta.get("state"):
                c.state = meta["state"]
            if meta.get("zip"):
                c.zip = meta["zip"]
            if c.customer_type == "auto":
                c.customer_type = "catheter"

        s.flush()

        # ── Phase 3: merge by desired fuzzy facility key ──────────────────
        print()
        print("=== Phase 3: Merge customers sharing facility key ===")
        key_groups: dict[str, list[Customer]] = defaultdict(list)
        desired_key: dict[int, str] = {}
        for c in s.query(Customer).all():
            meta = cust_meta.get(c.id)
            if meta:
                key = meta["key"]
            else:
                key = compute_facility_key_from_ship_to(
                    address1=c.address1, city=c.city, state=c.state, zip=c.zip,
                    facility_name=c.facility_name,
                )
            if not key or key == "UNKNOWN":
                continue
            if "|" not in key and (c.customer_type or "") == "nre":
                continue
            desired_key[c.id] = key
            key_groups[key].append(c)

        for key, group in sorted(key_groups.items(), key=lambda x: x[0]):
            if len(group) < 2:
                continue
            ranked = sorted(
                group,
                key=lambda c: _customer_score(s, c.id, SalesOrder, DistributionLogEntry),
                reverse=True,
            )
            master = ranked[0]
            for dup in ranked[1:]:
                print(
                    f"  MERGE key={key}: master id={master.id} {master.facility_name!r} "
                    f"<< dup id={dup.id} {dup.facility_name!r}"
                )
                merged += 1
                # Park dup key so unique constraint never blocks the merge
                dup.company_key = f"MERGE_TMP_{dup.id}"
                s.flush()
                candidates = []
                for cid in (master.id, dup.id):
                    m = cust_meta.get(cid)
                    if m and m.get("display"):
                        candidates.append(m["display"])
                for nm in (dup.facility_name, master.facility_name):
                    if nm:
                        candidates.append(prettify_facility_name(nm))
                best = _best_clinical_name(candidates) or (
                    cust_meta.get(master.id) or {}
                ).get("display")
                if best:
                    master.facility_name = best
                merge_customers(
                    s, master_id=master.id, duplicate_id=dup.id, user=actor
                )
                s.flush()

        # Re-sync dists after merges
        linked = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.sales_order_id.isnot(None))
            .all()
        )
        for d in linked:
            so = s.get(SalesOrder, d.sales_order_id)
            if so:
                sync_distribution_customer_from_sales_order(d, so)
        s.flush()

        # ── Phase 3b: assign canonical company_key on survivors ───────────
        print()
        print("=== Phase 3b: Assign canonical facility keys ===")
        # First park anyone whose key will change onto a temp key
        for c in s.query(Customer).all():
            key = desired_key.get(c.id) or compute_facility_key_from_ship_to(
                address1=c.address1, city=c.city, state=c.state, zip=c.zip,
                facility_name=c.facility_name,
            )
            if not key or key == "UNKNOWN":
                continue
            if "|" not in key and (c.customer_type or "") == "nre":
                continue
            desired_key[c.id] = key
            if c.company_key != key:
                c.company_key = f"REKEY_TMP_{c.id}"
        s.flush()

        for c in s.query(Customer).all():
            key = desired_key.get(c.id)
            if not key:
                continue
            if c.company_key == key:
                continue
            holder = (
                s.query(Customer)
                .filter(Customer.company_key == key, Customer.id != c.id)
                .first()
            )
            if holder:
                # Should have been merged; leave temp and report
                print(
                    f"  REKEY-SKIP id={c.id} {c.facility_name!r} -> {key} "
                    f"(still held by id={holder.id})"
                )
                continue
            print(f"  REKEY id={c.id} -> {key}")
            rekeyed += 1
            c.company_key = key
        s.flush()

        # ── Phase 4: empty shells ─────────────────────────────────────────
        print()
        print("=== Phase 4: Delete empty customer shells ===")
        for c in s.query(Customer).all():
            so_n = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()
            dist_n = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.customer_id == c.id)
                .count()
            )
            if so_n or dist_n:
                continue
            if (c.customer_type or "auto") == "nre":
                notes = s.query(CustomerNote).filter(CustomerNote.customer_id == c.id).count()
                if notes:
                    continue
            print(f"  DELETE shell id={c.id} {c.facility_name!r}")
            shells += 1
            record_event(
                s,
                actor=actor,
                action="customer.delete_shell",
                entity_type="Customer",
                entity_id=str(c.id),
                metadata={"facility_name": c.facility_name, "reason": "p41b_cleanup"},
            )
            s.delete(c)
        s.flush()

        # ── Phase 5: verification report ──────────────────────────────────
        print()
        print("=== Phase 5: Verification ===")
        mismatch = 0
        for d in s.query(DistributionLogEntry).filter(
            DistributionLogEntry.sales_order_id.isnot(None)
        ).all():
            so = s.get(SalesOrder, d.sales_order_id)
            if so and d.customer_id and so.customer_id and d.customer_id != so.customer_id:
                mismatch += 1
        zero_so = 0
        zero_so_mislinked = 0
        for c in s.query(Customer).all():
            so_n = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()
            dist_n = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.customer_id == c.id)
                .count()
            )
            if dist_n and not so_n:
                zero_so += 1
                mislinked = False
                for d in s.query(DistributionLogEntry).filter(
                    DistributionLogEntry.customer_id == c.id
                ).all():
                    if d.sales_order_id:
                        so = s.get(SalesOrder, d.sales_order_id)
                        if so and so.customer_id and so.customer_id != c.id:
                            mislinked = True
                            break
                if mislinked:
                    zero_so_mislinked += 1
                if zero_so <= 20:
                    tag = " MISLINKED" if mislinked else ""
                    print(f"  STILL 0-SO{tag} id={c.id} {c.facility_name!r} dists={dist_n}")

        # Focus checks
        focus_ids = {
            "Temple/Philly": [651],
            "Temple/FtWash": [677],
            "SanDiego/VAMC": [635],
            "LaMesa": [648],
            "Amarillo": [654],
            "LongBeachVA": [622],
            "Harbor": [610],
        }
        for label, ids in focus_ids.items():
            print(f"  FOCUS {label}:")
            for cid in ids:
                c = s.get(Customer, cid)
                if not c:
                    print(f"    id={cid} (deleted/merged)")
                    continue
                so_n = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()
                dist_n = (
                    s.query(DistributionLogEntry)
                    .filter(DistributionLogEntry.customer_id == c.id)
                    .count()
                )
                print(
                    f"    id={c.id} {c.facility_name!r} sos={so_n} dists={dist_n} "
                    f"key={c.company_key}"
                )
        marathonish = (
            s.query(Customer)
            .filter(Customer.facility_name.ilike("%Marathon%"))
            .all()
        )
        print(f"  FOCUS remaining Marathon-named: {len(marathonish)}")
        for c in marathonish:
            print(f"    id={c.id} {c.facility_name!r}")

        if not DRY_RUN:
            s.commit()
            print()
            print("COMMITTED.")
        else:
            s.rollback()
            print()
            print("DRY RUN — re-run with --execute to apply.")

        print()
        print("=== Summary ===")
        print(f"  synced_dists:     {synced}")
        print(f"  renamed:          {renamed}")
        print(f"  rekeyed:          {rekeyed}")
        print(f"  merged:           {merged}")
        print(f"  deleted_shells:   {shells}")
        print(f"  remaining_mismatch_dist_so: {mismatch}")
        print(f"  remaining_zero_so_with_dists: {zero_so}")
        print(f"  remaining_zero_so_mislinked: {zero_so_mislinked}")


if __name__ == "__main__":
    main()
