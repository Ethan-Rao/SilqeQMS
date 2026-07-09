"""
Bulk import documents from a local directory into the admin_docs system.

Usage:
    python scripts/bulk_import_admin_docs.py \
        --directory "QM Documents" \
        --library qms_documents \
        --folder "Original - FileHold" \
        [--dry-run]

The script will:
1. Create the target folder if it doesn't exist
2. Read all files from the specified directory
3. Upload each to storage + create AdminDocFile records
4. Skip files that already exist in the target folder (by filename)
5. Report results

Requires Flask app context (reads .env for DB + storage config).
"""
import sys
import os
import argparse
import mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.eqms import create_app
from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.admin_docs.models import AdminDocFolder, AdminDocFile
from app.eqms.modules.admin_docs.service import create_folder, upload_document

# File extensions to include (add more as needed)
ALLOWED_EXTENSIONS = {
    ".docx", ".doc", ".pdf", ".xlsx", ".xls", ".csv", ".txt",
    ".png", ".jpg", ".jpeg", ".gif", ".eml", ".pptx", ".ppt",
}


def select_new_files(source_files, existing_filenames):
    """
    Idempotency planner: given candidate file paths and the set of filenames
    already present in the target folder, return (to_import, skipped_unsupported,
    skipped_existing). Filenames are compared using secure_filename, matching how
    upload_document stores them, so re-runs are safe (no duplicates).
    """
    from werkzeug.utils import secure_filename

    to_import = []
    skipped_unsupported = []
    skipped_existing = []
    for file_path in sorted(source_files):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
            skipped_unsupported.append(file_path)
            continue
        if secure_filename(file_path.name) in existing_filenames:
            skipped_existing.append(file_path)
            continue
        to_import.append(file_path)
    return to_import, skipped_unsupported, skipped_existing


def main():
    parser = argparse.ArgumentParser(description="Bulk import documents into admin_docs")
    parser.add_argument("--directory", "-d", required=True, help="Local directory to import from")
    parser.add_argument("--library", "-l", required=True, help="Library key (e.g. qms_documents)")
    parser.add_argument("--folder", "-f", required=True, help="Target folder name (created if missing)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded without doing it")
    args = parser.parse_args()

    source_dir = Path(args.directory)
    if not source_dir.exists():
        # Try relative to project root
        source_dir = ROOT / args.directory
    if not source_dir.is_dir():
        print(f"ERROR: Directory not found: {args.directory}")
        sys.exit(1)

    app = create_app()
    with app.app_context():
        s = db_session()

        # Get admin user (first admin role user)
        admin_user = s.query(User).join(User.roles).filter_by(key="admin").first()
        if not admin_user:
            print("ERROR: No admin user found. Run init_db.py first.")
            sys.exit(1)

        # Find or create the target folder
        folder = (
            s.query(AdminDocFolder)
            .filter_by(library_key=args.library, parent_id=None, name=args.folder)
            .first()
        )
        if not folder:
            if args.dry_run:
                print(f"[DRY RUN] Would create folder: {args.folder}")
            else:
                folder = create_folder(s, args.library, args.folder, admin_user)
                s.flush()
                print(f"Created folder: {args.folder} (id={folder.id})")

        # Get existing filenames in the folder to skip duplicates
        existing_filenames = set()
        if folder:
            existing = s.query(AdminDocFile.filename).filter_by(
                library_key=args.library, folder_id=folder.id
            ).all()
            existing_filenames = {row[0] for row in existing}

        # Collect files (idempotency planner is shared + unit-tested)
        files_to_import, skipped_unsupported, skipped_existing = select_new_files(
            list(source_dir.iterdir()), existing_filenames
        )
        for fp in skipped_unsupported:
            print(f"  SKIP (unsupported type): {fp.name}")
        for fp in skipped_existing:
            print(f"  SKIP (already exists): {fp.name}")

        print(f"\nFound {len(files_to_import)} files to import into {args.library}/{args.folder}")

        if args.dry_run:
            for fp in files_to_import:
                size_kb = fp.stat().st_size / 1024
                print(f"  [DRY RUN] Would upload: {fp.name} ({size_kb:.1f} KB)")
            print(f"\n[DRY RUN] Total: {len(files_to_import)} files")
            return

        # Upload each file
        uploaded = 0
        errors = []
        for fp in files_to_import:
            try:
                file_bytes = fp.read_bytes()
                content_type = mimetypes.guess_type(fp.name)[0] or "application/octet-stream"
                upload_document(
                    s, args.library, folder, file_bytes, fp.name, content_type, admin_user
                )
                uploaded += 1
                print(f"  OK {fp.name} ({len(file_bytes) / 1024:.1f} KB)")
            except Exception as e:
                errors.append(f"{fp.name}: {e}")
                print(f"  FAIL {fp.name}: {e}")

        if uploaded > 0:
            s.commit()

        print(f"\nDone: {uploaded} uploaded, {len(errors)} errors")
        if errors:
            print("Errors:")
            for err in errors:
                print(f"  - {err}")


if __name__ == "__main__":
    main()
