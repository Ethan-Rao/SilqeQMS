"""
Seed initial (pending) training assignments from the QM.SLQ053 training matrix.

For every active user, this creates a PENDING read-and-acknowledge assignment for
each doc number the user is required to be trained on (per the matrix), UNLESS the
user already has any training record — acknowledged or pending — for that document
(any revision). Nothing is pre-acknowledged; Ethan backdates / DCO-qualifies the
specific ones afterward through the UI.

Usage:
    python scripts/_init_training_matrix.py            # dry-run (default)
    python scripts/_init_training_matrix.py --execute  # commit to DB
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.training.models import TrainingAssignment
    from app.eqms.modules.training.service import (
        matrix_required_for_doc_numbers,
        resolve_current_revision,
    )
    from app.eqms.utils import utcnow

    app = create_app()
    with app.app_context():
        s = db_session()

        # An admin actor for assigned_by (best-effort; None if none found).
        actor = (
            s.query(User)
            .filter(User.is_active.is_(True))
            .order_by(User.id.asc())
            .first()
        )
        actor_id = actor.id if actor else None

        users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Active users: {len(users)}")
        print()

        created = 0
        users_covered: set[int] = set()
        matched_docs: set[str] = set()
        unmatched_docs: set[str] = set()
        now = utcnow()

        for u in users:
            required = matrix_required_for_doc_numbers(u.email)
            for dn in required:
                resolved = resolve_current_revision(s, dn)
                if resolved is None:
                    unmatched_docs.add(dn)
                    continue
                doc, rev = resolved
                matched_docs.add(dn)

                # Any existing record (acknowledged or pending) for this document?
                existing = (
                    s.query(TrainingAssignment)
                    .filter(
                        TrainingAssignment.assigned_to_user_id == u.id,
                        TrainingAssignment.item_type == "document",
                        TrainingAssignment.document_id == doc.id,
                    )
                    .first()
                )
                if existing:
                    continue

                if rev is not None:
                    title = f"{doc.doc_number} Rev {rev.revision} — {doc.title}"
                else:
                    title = f"{doc.doc_number} — {doc.title}"

                print(f"  CREATE  {u.email:32s}  {dn:12s}  {title}")
                created += 1
                users_covered.add(u.id)

                if not DRY_RUN:
                    s.add(TrainingAssignment(
                        item_type="document",
                        item_title=title,
                        document_id=doc.id,
                        document_revision_id=rev.id if rev else None,
                        assigned_to_user_id=u.id,
                        assigned_by_user_id=actor_id,
                        due_date=None,
                        assigned_at=now,
                        created_at=now,
                        training_type="read_acknowledge",
                    ))

        if not DRY_RUN:
            s.commit()

        print()
        print("Summary")
        print(f"  Assignments {'created' if not DRY_RUN else 'to create'}: {created}")
        print(f"  Users covered: {len(users_covered)}")
        print(f"  Documents matched: {len(matched_docs)}")
        if unmatched_docs:
            print(f"  Documents NOT found ({len(unmatched_docs)}): {', '.join(sorted(unmatched_docs))}")
        if DRY_RUN:
            print()
            print("DRY RUN — re-run with --execute to apply.")


if __name__ == "__main__":
    main()
