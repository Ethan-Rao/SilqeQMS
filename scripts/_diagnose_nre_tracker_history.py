"""
Read-only diagnostic: NRE tracker audit history and current row counts.

Queries audit_events for entity_type == NREProjectEntry and reports action,
actor, timestamp, entity id, and metadata. Also reports current counts of
nre_project_entries and nre_tracker_attachments.

No writes. No --execute flag. Database only (does not touch Spaces).

Usage:
    python scripts/_diagnose_nre_tracker_history.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import AuditEvent
    from app.eqms.modules.nre_projects.models import NREProjectEntry, NRETrackerAttachment

    app = create_app()
    with app.app_context():
        s = db_session()

        entry_count = s.query(NREProjectEntry).count()
        att_count = s.query(NRETrackerAttachment).count()
        print(f"nre_project_entries count: {entry_count}")
        print(f"nre_tracker_attachments count: {att_count}")
        print()

        events = (
            s.query(AuditEvent)
            .filter(AuditEvent.entity_type == "NREProjectEntry")
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
            .all()
        )
        print(f"audit events for NREProjectEntry: {len(events)}")
        print("---")
        for ev in events:
            meta = ev.metadata_json or ""
            print(
                f"action={ev.action} actor={ev.actor_user_email or '-'} "
                f"at={ev.created_at} entity_id={ev.entity_id} metadata={meta}"
            )

        # Orphan attachments: rows whose nre_entry_id no longer exists
        print()
        print("Orphan tracker attachments (entry missing):")
        atts = s.query(NRETrackerAttachment).all()
        orphans = []
        for a in atts:
            parent = s.get(NREProjectEntry, a.nre_entry_id)
            if parent is None:
                orphans.append(a)
        if not orphans:
            print("  (none)")
        else:
            for a in orphans:
                print(
                    f"  id={a.id} nre_entry_id={a.nre_entry_id} "
                    f"filename={a.filename} storage_key={a.storage_key}"
                )


if __name__ == "__main__":
    main()
