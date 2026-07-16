"""Delete empty year folders (2022-2026) from the NCRs admin_docs library.

Usage:
    python scripts/_delete_ncr_year_folders.py            # dry run
    python scripts/_delete_ncr_year_folders.py --execute  # delete
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

YEAR_NAMES = {"2022", "2023", "2024", "2025", "2026", "2027"}
LIBRARY = "ncrs"
DRY_RUN = "--execute" not in sys.argv


def main() -> None:
    from app.eqms import create_app
    app = create_app()
    with app.app_context():
        from app.eqms.db import db_session
        from app.eqms.modules.admin_docs.models import AdminDocFolder, AdminDocFile

        s = db_session()
        year_folders = (
            s.query(AdminDocFolder)
            .filter(
                AdminDocFolder.library_key == LIBRARY,
                AdminDocFolder.name.in_(YEAR_NAMES),
            )
            .all()
        )

        if not year_folders:
            print("No year folders found in NCRs library.")
            return

        deleted = 0
        skipped = 0
        for folder in year_folders:
            # Only delete if truly empty (no files, no subfolders)
            file_count = s.query(AdminDocFile).filter(AdminDocFile.folder_id == folder.id).count()
            subfolder_count = s.query(AdminDocFolder).filter(AdminDocFolder.parent_id == folder.id).count()
            if file_count > 0 or subfolder_count > 0:
                print(f"  SKIP (not empty) {folder.name!r} — {file_count} files, {subfolder_count} subfolders")
                skipped += 1
            else:
                print(f"  {'[DRY RUN] would delete' if DRY_RUN else 'DELETE'} folder: {folder.name!r}")
                if not DRY_RUN:
                    s.delete(folder)
                deleted += 1

        if DRY_RUN:
            print(f"\n[DRY RUN] Would delete {deleted} folder(s), skip {skipped}. Re-run with --execute.")
        else:
            s.commit()
            print(f"\nDone: deleted {deleted} folder(s), skipped {skipped}.")


if __name__ == "__main__":
    main()
