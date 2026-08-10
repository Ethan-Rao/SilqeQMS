"""
Generate a per-employee training record CSV and upload it to each employee's
'Silq eQMS Training Records' subfolder in the Training Records (employee_training)
admin_docs library.

Replace-in-place: any prior '<Name>_Training_Record_*.csv' in that folder is
deleted before the fresh CSV is uploaded (keep only the most recent).

Usage:
    python scripts/_export_training_records.py            # dry-run (default)
    python scripts/_export_training_records.py --execute  # upload
"""
from __future__ import annotations

import csv
import io
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv

LIBRARY = "employee_training"
SUBFOLDER = "Silq eQMS Training Records"

TRAINING_TYPE_LABELS = {
    "read_acknowledge": "Read and Acknowledge",
    "dco_auto_qualified": "DCO Auto-Qualified",
    "document_originator": "Document Originator",
    "interactive": "Interactive",
}

CSV_HEADER = [
    "Document Number", "Document Title", "Revision",
    "Required (per QM.SLQ053 Matrix)", "Status",
    "Acknowledged Date", "Training Type", "Source Reference",
]


def _norm(name: str) -> str:
    return (name or "").lower().replace(" ", "").replace("_", "")


def _display(user) -> str:
    if user.display_name:
        return user.display_name.replace(" ", "")
    return (user.email or "user").split("@")[0]


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from flask import current_app

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
    from app.eqms.modules.admin_docs.service import upload_document
    from app.eqms.modules.training.models import TrainingAssignment
    from app.eqms.modules.training.service import (
        _doc_base,
        matrix_required_for_doc_numbers,
        resolve_current_revision,
    )
    from app.eqms.storage import storage_from_config

    today = date.today()
    today_s = today.isoformat()

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
        users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()

        top_level = (
            s.query(AdminDocFolder)
            .filter(AdminDocFolder.library_key == LIBRARY, AdminDocFolder.parent_id.is_(None))
            .all()
        )
        top_by_norm = {_norm(f.name): f for f in top_level}

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Active users: {len(users)}")
        print()

        generated = 0
        for u in users:
            display = _display(u)
            assignments = (
                s.query(TrainingAssignment)
                .filter(
                    TrainingAssignment.assigned_to_user_id == u.id,
                    TrainingAssignment.item_type == "document",
                )
                .all()
            )
            required = matrix_required_for_doc_numbers(u.email)
            required_bases = {_doc_base(dn) for dn in required}

            rows = []
            covered_bases = set()
            for a in assignments:
                doc_number = a.document.doc_number if a.document else ""
                base = _doc_base(doc_number)
                covered_bases.add(base)
                if a.acknowledged_at is not None:
                    status = "Acknowledged"
                elif a.due_date is not None and a.due_date < today:
                    status = "Overdue"
                else:
                    status = "Pending"
                rows.append([
                    doc_number,
                    a.document.title if a.document else a.item_title,
                    a.document_revision.revision if a.document_revision else "",
                    "Yes" if base in required_bases else "No",
                    status,
                    a.acknowledged_at.strftime("%Y-%m-%d") if a.acknowledged_at else "",
                    TRAINING_TYPE_LABELS.get(a.training_type, a.training_type or ""),
                    a.source_reference or "",
                ])

            # Required docs with no assignment → Not Assigned rows.
            for dn in required:
                if _doc_base(dn) in covered_bases:
                    continue
                resolved = resolve_current_revision(s, dn)
                doc = resolved[0] if resolved else None
                rev = resolved[1] if resolved else None
                rows.append([
                    dn,
                    doc.title if doc else "",
                    rev.revision if rev else "",
                    "Yes",
                    "Not Assigned",
                    "", "", "",
                ])

            rows.sort(key=lambda r: r[0])

            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(CSV_HEADER)
            writer.writerows(rows)
            csv_bytes = buf.getvalue().encode("utf-8")
            filename = f"{display}_Training_Record_{today_s}.csv"

            emp_folder = top_by_norm.get(_norm(u.display_name or "")) or top_by_norm.get(_norm(display))
            if emp_folder is None:
                print(f"  SKIP  {u.email} — no matching top-level folder (run scaffold first)")
                continue

            # P38 A2: CSV lands directly in the employee's top-level folder, not the
            # 'Silq eQMS Training Records' subfolder (that subfolder is reserved for
            # DCO form copies and effectiveness review attachments).
            target = emp_folder

            prefix = f"{display}_Training_Record_"
            existing = (
                s.query(AdminDocFile)
                .filter(AdminDocFile.library_key == LIBRARY, AdminDocFile.folder_id == target.id)
                .all()
            )
            stale = [f for f in existing if (f.filename or "").startswith(prefix)]

            print(f"  {u.email}: {len(rows)} row(s) -> {emp_folder.name}/{filename}"
                  + (f" (replaces {len(stale)} old)" if stale else ""))
            generated += 1

            if not DRY_RUN:
                storage = storage_from_config(current_app.config)
                for f in stale:
                    try:
                        storage.delete(f.storage_key)
                    except Exception as e:  # noqa: BLE001
                        current_app.logger.warning("Could not delete storage %s: %s", f.storage_key, e)
                    s.delete(f)
                s.flush()
                upload_document(s, LIBRARY, target, csv_bytes, filename, "text/csv", actor)

        if not DRY_RUN:
            s.commit()
            print()
            print(f"Done. {generated} record CSV(s) uploaded.")
        else:
            print()
            print(f"DRY RUN: {generated} record CSV(s) would be generated. Re-run with --execute.")


if __name__ == "__main__":
    main()
