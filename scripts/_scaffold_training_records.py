"""
Scaffold the Training Records (employee_training) admin_docs library.

- Deletes top-level folders that don't belong to an active employee (except the
  retained non-employee folders).
- Ensures a top-level folder for each of the 7 active employees.
- Ensures 'Silq eQMS Training Records' and 'Historical Records' subfolders in each.
- Ensures top-level 'Training Matrix' and 'Effectiveness Reviews' folders.

Existing files inside retained folders are NOT modified.

Usage:
    python scripts/_scaffold_training_records.py            # dry-run (default)
    python scripts/_scaffold_training_records.py --execute  # apply
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv

LIBRARY = "employee_training"

EMPLOYEE_FOLDERS = [
    "EthanRao", "BrianMcVerry", "ChrisTurner", "ChuckGreiner",
    "TomDowney", "NaHe", "HaleyShomo",
]
EMPLOYEE_SUBFOLDERS = ["Silq eQMS Training Records", "Historical Records"]
NON_EMPLOYEE_TOP_LEVEL = ["Training Matrix", "Effectiveness Reviews"]
# Retained top-level folders that are neither employee nor auto-created.
RETAINED_EXTRA = ["JobDescriptions"]


def _norm(name: str) -> str:
    return (name or "").lower().replace(" ", "").replace("_", "")


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from flask import current_app

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
    from app.eqms.modules.admin_docs.service import create_folder
    from app.eqms.storage import storage_from_config

    keep_norms = {_norm(n) for n in (EMPLOYEE_FOLDERS + NON_EMPLOYEE_TOP_LEVEL + RETAINED_EXTRA)}

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()

        all_folders = s.query(AdminDocFolder).filter(AdminDocFolder.library_key == LIBRARY).all()
        children_by_parent: dict[int | None, list] = {}
        for f in all_folders:
            children_by_parent.setdefault(f.parent_id, []).append(f)

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Library: {LIBRARY} — {len(all_folders)} folders")
        print()

        # 5A. Delete unwanted top-level folders + contents.
        deleted = 0
        top_level = children_by_parent.get(None, [])
        for f in top_level:
            if _norm(f.name) in keep_norms:
                continue
            # Collect descendant folder ids for storage cleanup.
            ids = []

            def _collect(fid):
                ids.append(fid)
                for c in children_by_parent.get(fid, []):
                    _collect(c.id)

            _collect(f.id)
            files = (
                s.query(AdminDocFile)
                .filter(AdminDocFile.library_key == LIBRARY, AdminDocFile.folder_id.in_(ids))
                .all()
            )
            print(f"  DELETE top-level folder '{f.name}' ({len(files)} file(s) in subtree)")
            deleted += 1
            if not DRY_RUN:
                storage = storage_from_config(current_app.config)
                for fi in files:
                    try:
                        storage.delete(fi.storage_key)
                    except Exception as e:  # noqa: BLE001
                        current_app.logger.warning("Could not delete storage %s: %s", fi.storage_key, e)
                s.delete(f)  # cascade removes children + documents
        if not DRY_RUN and deleted:
            s.commit()

        # Refresh top-level list after deletions.
        top_level = (
            s.query(AdminDocFolder)
            .filter(AdminDocFolder.library_key == LIBRARY, AdminDocFolder.parent_id.is_(None))
            .all()
        )
        by_norm = {_norm(f.name): f for f in top_level}

        def _ensure_top(name: str):
            existing = by_norm.get(_norm(name))
            if existing:
                return existing
            print(f"  CREATE top-level folder '{name}'")
            if DRY_RUN:
                return None
            folder = create_folder(s, LIBRARY, name, actor, parent=None)
            by_norm[_norm(name)] = folder
            return folder

        # 5B + 5C. Employee folders + standard subfolders.
        for emp in EMPLOYEE_FOLDERS:
            emp_folder = _ensure_top(emp)
            if emp_folder is None:
                # Dry-run: subfolders would be created too.
                for sub in EMPLOYEE_SUBFOLDERS:
                    print(f"    CREATE subfolder '{emp}/{sub}'")
                continue
            existing_subs = {
                _norm(c.name)
                for c in s.query(AdminDocFolder)
                .filter(AdminDocFolder.library_key == LIBRARY, AdminDocFolder.parent_id == emp_folder.id)
                .all()
            }
            for sub in EMPLOYEE_SUBFOLDERS:
                if _norm(sub) in existing_subs:
                    continue
                print(f"    CREATE subfolder '{emp}/{sub}'")
                if not DRY_RUN:
                    create_folder(s, LIBRARY, sub, actor, parent=emp_folder)

        # 5D. Non-employee top-level folders.
        for name in NON_EMPLOYEE_TOP_LEVEL:
            _ensure_top(name)

        if not DRY_RUN:
            s.commit()
            print()
            print("Done.")
        else:
            print()
            print("DRY RUN — re-run with --execute to apply.")


if __name__ == "__main__":
    main()
