"""
P4-03B — Re-key facility-keyed NRE customers to company identity.

Dry-run by default; writes only with --execute.
Reuses apply_rekey_to_company / is_nre_rekey_candidate (no second merge impl).

Usage:
    python scripts/backfill_customer_identity.py
    python scripts/backfill_customer_identity.py --execute
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv


def _ascii(s: object) -> str:
    text = "" if s is None else str(s)
    return text.encode("ascii", "replace").decode("ascii")


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.customer_profiles.service import (
        apply_rekey_to_company,
        is_nre_rekey_candidate,
        preview_rekey_to_company,
    )
    from app.eqms.modules.customer_profiles.utils import (
        canonical_customer_key,
        is_person_shaped_customer_name,
    )
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_NRE_PROJECT

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Actor: {_ascii(actor.email if actor else None)}")
        print()

        customers = s.query(Customer).order_by(Customer.id.asc()).all()
        candidates = [c for c in customers if is_nre_rekey_candidate(s, c)]

        # Explicit exclusion check for known catheter misclassifications
        excluded_check_ids = {625, 614}  # Wiscosin Rapids, Aspirus Urology Wausau
        excluded_present = []
        for cid in excluded_check_ids:
            c = s.get(Customer, cid)
            if c and not is_nre_rekey_candidate(s, c):
                excluded_present.append(
                    f"id={cid} name={_ascii(c.facility_name)} (excluded by selection rule)"
                )
            elif c:
                excluded_present.append(
                    f"id={cid} name={_ascii(c.facility_name)} WARNING still a candidate"
                )
        print("=== Exclusion check (Wisconsin Rapids / Aspirus Wausau) ===")
        for line in excluded_present or ["(customers not present in this DB)"]:
            print(f"  {line}")
        print()

        print(f"=== Candidates ({len(candidates)}) ===")
        rekeyed = 0
        merged = 0
        held = 0
        skipped = 0
        held_rows: list[str] = []

        # Process longer/more-complete names first so ADVANCEDBIONICS exists before AB merges.
        candidates.sort(
            key=lambda c: (-len(canonical_customer_key(c.facility_name)), c.id)
        )

        for c in candidates:
            if is_person_shaped_customer_name(c.facility_name):
                orders = (
                    s.query(SalesOrder)
                    .filter(
                        SalesOrder.customer_id == c.id,
                        SalesOrder.order_type == ORDER_TYPE_NRE_PROJECT,
                    )
                    .all()
                )
                order_nums = ", ".join(_ascii(o.order_number) for o in orders)
                line = (
                    f"HOLD id={c.id} name={_ascii(c.facility_name)} "
                    f"key={_ascii(c.company_key)} reason=person_shaped "
                    f"orders=[{order_nums}]"
                )
                print(f"  {line}")
                held_rows.append(line)
                held += 1
                continue

            try:
                preview = preview_rekey_to_company(s, c.id)
            except Exception as e:
                print(
                    f"  SKIP id={c.id} name={_ascii(c.facility_name)} "
                    f"error={_ascii(e)}"
                )
                skipped += 1
                continue

            merge_txt = (
                f"merge_into={preview.merge_target_id}({_ascii(preview.merge_target_name)})"
                if preview.merge_target_id
                else "merge_into=none"
            )
            print(
                f"  id={c.id} name={_ascii(c.facility_name)} "
                f"key={_ascii(c.company_key)} proposed={_ascii(preview.proposed_key)} "
                f"{merge_txt} survivor={preview.survivor_id} "
                f"moves so={preview.sales_orders} dist={preview.distributions} "
                f"notes={preview.notes} reps={preview.rep_assignments} "
                f"surviving_name={_ascii(preview.surviving_name)}"
            )

            if DRY_RUN:
                if preview.merge_target_id:
                    merged += 1
                else:
                    rekeyed += 1
                continue

            try:
                apply_rekey_to_company(
                    s,
                    c.id,
                    surviving_name=preview.surviving_name,
                    user=actor,
                )
                s.commit()
                if preview.merge_target_id:
                    merged += 1
                else:
                    rekeyed += 1
            except Exception as e:
                s.rollback()
                print(f"    EXECUTE FAILED: {_ascii(e)}")
                skipped += 1

        print()
        print("=== Summary ===")
        print(f"rekeyed_in_place: {rekeyed}")
        print(f"merged: {merged}")
        print(f"held_person_shaped: {held}")
        print(f"skipped: {skipped}")
        if held_rows:
            print("Held detail:")
            for line in held_rows:
                print(f"  {line}")

        if not DRY_RUN:
            print()
            print("=== Verification ===")
            from collections import Counter

            types = Counter(
                (c.customer_type or "null") for c in s.query(Customer).all()
            )
            for t, n in sorted(types.items()):
                print(f"  customer_type={t}: {n}")

            bad = []
            for c in s.query(Customer).all():
                nre_orders = (
                    s.query(SalesOrder)
                    .filter(
                        SalesOrder.customer_id == c.id,
                        SalesOrder.order_type == ORDER_TYPE_NRE_PROJECT,
                    )
                    .count()
                )
                if nre_orders == 0:
                    continue
                name_key = canonical_customer_key(c.facility_name)
                if c.company_key != name_key and not is_person_shaped_customer_name(
                    c.facility_name
                ):
                    # Address-derived leftovers
                    if "|" in (c.company_key or ""):
                        bad.append(c)
            print(
                f"nre_project customers still address-keyed (excl. held persons): {len(bad)}"
            )
            for c in bad:
                print(
                    f"  id={c.id} name={_ascii(c.facility_name)} "
                    f"key={_ascii(c.company_key)}"
                )


if __name__ == "__main__":
    main()
