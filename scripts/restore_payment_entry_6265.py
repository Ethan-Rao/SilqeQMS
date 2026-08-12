"""
P4-08A / D54 — Restore PaymentEntry deleted in audit event 6265.

Dry-run by default; writes only with --execute.
Does not reuse id 2. Records payment_entry.restored citing the source event.

Usage:
    python scripts/restore_payment_entry_6265.py
    python scripts/restore_payment_entry_6265.py --execute
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv
SOURCE_EVENT_ID = 6265


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import AuditEvent
    from app.eqms.modules.purchasing.service import restore_payment_entry_from_audit_snapshot

    app = create_app()
    with app.app_context():
        s = db_session()
        ev = s.get(AuditEvent, SOURCE_EVENT_ID)
        if ev is None:
            raise SystemExit(f"Audit event {SOURCE_EVENT_ID} not found")
        if ev.action != "payment_entry.delete":
            raise SystemExit(
                f"Audit event {SOURCE_EVENT_ID} action is {ev.action!r}, expected payment_entry.delete"
            )
        snapshot = json.loads(ev.metadata_json or "{}")
        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Source audit event id={SOURCE_EVENT_ID} at {ev.created_at}")
        print("Will insert PaymentEntry:")
        print(f"  vendor={snapshot.get('vendor')!r}")
        print(f"  description={snapshot.get('description')!r}")
        print(f"  amount={snapshot.get('amount')!r}")
        print(f"  payment_due_date={snapshot.get('payment_due_date')!r}")
        print(f"  invoice_received_entry_id=None (not linked)")
        print(f"  attachments=none (snapshot files={snapshot.get('files')})")
        print(f"  original_id={snapshot.get('id')} (new id will be assigned)")

        if DRY_RUN:
            print("DRY RUN — re-run with --execute to write.")
            return

        entry = restore_payment_entry_from_audit_snapshot(
            s,
            snapshot=snapshot,
            source_event_id=SOURCE_EVENT_ID,
            user=None,
        )
        s.commit()
        print(
            f"Restored PaymentEntry id={entry.id} vendor={entry.vendor!r} "
            f"amount={entry.amount} due={entry.payment_due_date}"
        )


if __name__ == "__main__":
    main()
