"""
P4-08A2 — Backfill purchase_orders.supplier_name from notes prefix.

Dry-run by default; writes only with --execute.
Copies notes after 'Supplier from PO Log: ' when supplier_id is null.
Does not invent names for other notes (e.g. PO 0000179).

Usage:
    python scripts/backfill_po_supplier_name.py
    python scripts/backfill_po_supplier_name.py --execute
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv
PREFIX = "Supplier from PO Log: "


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.modules.purchasing.models import PurchaseOrder

    app = create_app()
    with app.app_context():
        s = db_session()
        rows = (
            s.query(PurchaseOrder)
            .filter(PurchaseOrder.supplier_id.is_(None))
            .filter(PurchaseOrder.notes.isnot(None))
            .all()
        )
        candidates = []
        skipped_179 = None
        for po in rows:
            notes = po.notes or ""
            if po.po_number == "0000179":
                skipped_179 = notes
            if notes.startswith(PREFIX):
                name = notes[len(PREFIX):].strip()
                if name:
                    candidates.append((po, name))

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"POs with null supplier_id and notes prefix: {len(candidates)}")
        for po, name in candidates[:20]:
            print(f"  {po.po_number} -> {name!r}")
        if len(candidates) > 20:
            print(f"  … and {len(candidates) - 20} more")
        if skipped_179 is not None:
            print(f"0000179 notes={skipped_179!r} — not backfilled")

        if DRY_RUN:
            print("DRY RUN — re-run with --execute to write.")
            return

        for po, name in candidates:
            po.supplier_name = name
        s.commit()
        print(f"Wrote supplier_name on {len(candidates)} purchase orders.")


if __name__ == "__main__":
    main()
