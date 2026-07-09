"""
Bulk import documents from a local directory into the admin_docs system.

Usage:
    python scripts/bulk_import_admin_docs.py \
        --directory "QM Documents" \
        --library qms_documents \
        --folder "Original - FileHold" \
        [--recursive] [--dry-run]

The script will:
1. Create the target folder path if it doesn't exist (--folder may be a nested
   path like "DCO Log/Completed", creating each level as needed).
2. Read files from the specified directory (recursively with --recursive,
   mirroring the source subfolder tree under the target folder).
3. Upload each to storage + create AdminDocFile records.
4. Skip files that already exist in the target folder (by filename) — idempotent.
5. Report results.

Requires Flask app context (reads env / .env for DB + storage config).
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


def _split_path(path: str) -> list[str]:
    """Split a folder path like 'A/B/C' into non-empty segments."""
    return [seg.strip() for seg in str(path).replace("\\", "/").split("/") if seg.strip()]


def ensure_folder_path(s, library_key, path, admin_user, *, dry_run, announced):
    """
    Find-or-create a nested folder path under a library. Returns
    (leaf_folder_or_None, full_path_str). In dry-run, folders that don't yet
    exist are reported once (via `announced`) and represented as None (virtual),
    so their descendants are treated as not-yet-existing too.
    """
    parts = _split_path(path)
    parent = None  # AdminDocFolder or None (root)
    parent_exists = True
    accumulated: list[str] = []
    for name in parts:
        accumulated.append(name)
        full = "/".join(accumulated)
        found = None
        if parent_exists:
            found = (
                s.query(AdminDocFolder)
                .filter_by(library_key=library_key, parent_id=(parent.id if parent else None), name=name)
                .first()
            )
        if found is not None:
            parent = found
            continue
        # Needs creating.
        if dry_run:
            if full not in announced:
                print(f"[DRY RUN] Would create folder: {library_key} / {full}")
                announced.add(full)
            parent = None
            parent_exists = False
        else:
            parent = create_folder(s, library_key, name, admin_user, parent=parent)
            s.flush()
            print(f"Created folder: {library_key} / {full} (id={parent.id})")
    return parent, "/".join(parts)


def import_directory(s, library_key, folder, source_dir, admin_user, *, dry_run):
    """
    Import the DIRECT files of `source_dir` into `folder` (which may be None in
    dry-run for a not-yet-created folder). Returns (uploaded, skipped_existing,
    skipped_unsupported, errors)."""
    existing_filenames = set()
    if folder is not None:
        rows = s.query(AdminDocFile.filename).filter_by(
            library_key=library_key, folder_id=folder.id
        ).all()
        existing_filenames = {r[0] for r in rows}

    direct = [p for p in source_dir.iterdir() if p.is_file()]
    to_import, skipped_unsupported, skipped_existing = select_new_files(direct, existing_filenames)
    for fp in skipped_unsupported:
        print(f"  SKIP (unsupported type): {fp.name}")
    for fp in skipped_existing:
        print(f"  SKIP (already exists): {fp.name}")

    uploaded = 0
    errors: list[str] = []
    for fp in to_import:
        if dry_run:
            size_kb = fp.stat().st_size / 1024
            print(f"  [DRY RUN] Would upload: {fp.name} ({size_kb:.1f} KB)")
            uploaded += 1
            continue
        try:
            file_bytes = fp.read_bytes()
            content_type = mimetypes.guess_type(fp.name)[0] or "application/octet-stream"
            upload_document(s, library_key, folder, file_bytes, fp.name, content_type, admin_user)
            uploaded += 1
            print(f"  OK {fp.name} ({len(file_bytes) / 1024:.1f} KB)")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{fp.name}: {e}")
            print(f"  FAIL {fp.name}: {e}")
    return uploaded, len(skipped_existing), len(skipped_unsupported), errors


def run_import(s, *, library_key, folder_path, source_dir, admin_user, recursive, dry_run):
    """
    Orchestrate an import. Non-recursive imports the direct files of source_dir
    into folder_path. Recursive mirrors the source subfolder tree under
    folder_path (depth-first, parents before children) and imports each
    directory's direct files. Returns a summary dict.
    """
    source_dir = Path(source_dir)
    announced: set[str] = set()
    total_uploaded = 0
    total_skipped_existing = 0
    total_skipped_unsupported = 0
    folders_touched = 0
    errors: list[str] = []

    if not recursive:
        folder, _ = ensure_folder_path(s, library_key, folder_path, admin_user, dry_run=dry_run, announced=announced)
        folders_touched = 1
        up, se, su, errs = import_directory(s, library_key, folder, source_dir, admin_user, dry_run=dry_run)
        total_uploaded, total_skipped_existing, total_skipped_unsupported = up, se, su
        errors += errs
    else:
        # os.walk top-down => parents created before children.
        for dirpath, _dirnames, _filenames in os.walk(source_dir):
            dpath = Path(dirpath)
            rel = dpath.relative_to(source_dir)
            rel_parts = [p for p in rel.parts if p not in (".", "")]
            target_path = "/".join(_split_path(folder_path) + list(rel_parts))
            folder, _ = ensure_folder_path(s, library_key, target_path, admin_user, dry_run=dry_run, announced=announced)
            folders_touched += 1
            up, se, su, errs = import_directory(s, library_key, folder, dpath, admin_user, dry_run=dry_run)
            total_uploaded += up
            total_skipped_existing += se
            total_skipped_unsupported += su
            errors += errs

    return {
        "uploaded": total_uploaded,
        "skipped_existing": total_skipped_existing,
        "skipped_unsupported": total_skipped_unsupported,
        "folders": folders_touched,
        "errors": errors,
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
    parser.add_argument("--folder", "-f", required=True, help="Target folder path (created if missing; may be nested e.g. 'A/B')")
    parser.add_argument("--recursive", action="store_true", help="Walk subfolders and mirror the tree under the target folder")
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

        mode = "RECURSIVE" if args.recursive else "flat"
        print(f"Importing ({mode}) {source_dir} -> {args.library} / {args.folder}"
              + ("  [DRY RUN]" if args.dry_run else ""))

        summary = run_import(
            s,
            library_key=args.library,
            folder_path=args.folder,
            source_dir=source_dir,
            admin_user=admin_user,
            recursive=args.recursive,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            print(f"\n[DRY RUN] Total: {summary['uploaded']} files across {summary['folders']} folder(s)"
                  f" ({summary['skipped_existing']} already present, {summary['skipped_unsupported']} unsupported)")
            return

        if summary["errors"]:
            # Partial failures: keep what succeeded (idempotent re-run fixes the rest).
            s.commit()
            print(f"\nDone: {summary['uploaded']} uploaded across {summary['folders']} folder(s),"
                  f" {len(summary['errors'])} error(s)")
            print("Errors:")
            for err in summary["errors"]:
                print(f"  - {err}")
        else:
            s.commit()
            print(f"\nDone: {summary['uploaded']} uploaded across {summary['folders']} folder(s),"
                  f" 0 errors ({summary['skipped_existing']} already present,"
                  f" {summary['skipped_unsupported']} unsupported)")


if __name__ == "__main__":
    main()
