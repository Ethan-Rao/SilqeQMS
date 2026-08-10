# DEV AGENT: QM Documents Bulk Upload Implementation

**Date:** 2026-03-10  
**Priority:** High  
**Push when done:** Yes

---

## Context

We have **46 QM policy documents** (`.docx` files) in the local folder `QM Documents/` at the project root. These are the original FileHold-era versions of our Quality Management System documents. They need to be uploaded to the **Quality Management Documents** library (`qms_documents`) in the admin_docs module.

These documents follow the naming convention:  
`QM.SLQ### [Rev] [Title] [Type].docx`  
Example: `QM.SLQ001 A Document Control SOP.DOCX`  
Where the letter (A, B, C, D, E, F) is the FileHold revision level.

### Strategic Goal

The originals must be preserved in the system permanently for auditor reference. As documents are later updated to align with SilqQMS and current regulatory standards, the originals serve as the "before" in a clear change trail.

### Organization Plan

```
Quality Management Documents (qms_documents library root)
└── Original - FileHold/          ← All 46 originals uploaded here
    ├── QM.SLQ001 A Document Control SOP.DOCX
    ├── QM.SLQ002 B Good Documentation Practices SOP.docx
    ├── ... (46 files total)
```

Later (NOT part of this task), updated documents will be placed in the library root or in categorized subfolders, while originals remain untouched in `Original - FileHold/`.

---

## Implementation Tasks

### Task 1: Add Multi-File Upload Support to Admin Docs

The current upload form only accepts a single file. Modify it to accept **multiple files** in one submission.

**File: `app/eqms/modules/admin_docs/admin.py`**

Modify the `admin_docs_upload_document` route:

```python
@bp.post("/admin-docs/documents/upload")
@require_permission("admin.view")
def admin_docs_upload_document():
    s = db_session()
    u = _current_user()
    library_key = (request.form.get("library_key") or "").strip()
    _library_or_404(library_key)

    folder_id = request.form.get("folder_id", type=int)
    folder = s.get(AdminDocFolder, folder_id) if folder_id else None
    if folder and folder.library_key != library_key:
        flash("Invalid folder.", "danger")
        return redirect(url_for(LIBRARY_ENDPOINTS[library_key]))

    # Support multiple files
    files = request.files.getlist("file")
    if not files or all(not f.filename for f in files):
        flash("Please select a file to upload.", "danger")
        return redirect(url_for(LIBRARY_ENDPOINTS[library_key], folder_id=folder_id))

    description = request.form.get("description")
    uploaded_count = 0
    errors = []

    for f in files:
        if not f or not f.filename:
            continue
        file_bytes = f.read()
        if len(file_bytes) > 50 * 1024 * 1024:  # Raise to 50MB for bulk uploads
            errors.append(f"{f.filename}: too large (max 50MB)")
            continue
        content_type = f.mimetype or "application/octet-stream"
        try:
            upload_document(s, library_key, folder, file_bytes, f.filename, content_type, u, description=description)
            uploaded_count += 1
        except Exception as e:
            current_app.logger.exception("Upload failed for %s: %s", f.filename, e)
            errors.append(f"{f.filename}: upload failed")

    if uploaded_count > 0:
        s.commit()
        flash(f"Successfully uploaded {uploaded_count} document(s).", "success")
    if errors:
        flash(f"Errors: {'; '.join(errors)}", "warning")
    if uploaded_count == 0 and not errors:
        flash("No files were uploaded.", "warning")

    return redirect(url_for(LIBRARY_ENDPOINTS[library_key], folder_id=folder_id))
```

**Key changes:**
- `request.files.getlist("file")` instead of `request.files.get("file")`
- Loop over all files
- Track success count and errors
- Single `s.commit()` after all files processed
- Raise file size limit from 10MB to 50MB (our largest QM doc is ~7MB, but future Excel/PDF files may be larger)

### Task 2: Update the Upload Form Template to Accept Multiple Files

**File: `app/eqms/templates/admin/admin_docs/index.html`**

Find the upload form's file input and add the `multiple` attribute:

```html
<input type="file" name="file" multiple required ...>
```

Also update the label/help text to indicate multiple files are supported. Something like:
```html
<p class="muted" style="font-size:12px;">Select one or more files (max 50MB each). Hold Ctrl/Cmd to select multiple.</p>
```

### Task 3: Build a Bulk Import Management Command

Create `scripts/bulk_import_admin_docs.py` — a reusable script that reads all files from a local directory and uploads them to a specified library + folder in the admin_docs system.

This script is for the initial mass migration of documents. It runs within Flask app context so it can use the same storage backend (S3 in production) and create proper DB records.

```python
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

        # Collect files
        files_to_import = []
        for file_path in sorted(source_dir.iterdir()):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                print(f"  SKIP (unsupported type): {file_path.name}")
                continue
            # Use secure_filename equivalent check
            from werkzeug.utils import secure_filename
            safe_name = secure_filename(file_path.name)
            if safe_name in existing_filenames:
                print(f"  SKIP (already exists): {file_path.name}")
                continue
            files_to_import.append(file_path)

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
                print(f"  ✓ {fp.name} ({len(file_bytes) / 1024:.1f} KB)")
            except Exception as e:
                errors.append(f"{fp.name}: {e}")
                print(f"  ✗ {fp.name}: {e}")

        if uploaded > 0:
            s.commit()

        print(f"\nDone: {uploaded} uploaded, {len(errors)} errors")
        if errors:
            print("Errors:")
            for err in errors:
                print(f"  - {err}")


if __name__ == "__main__":
    main()
```

**Key features:**
- Creates the target folder automatically if it doesn't exist
- Skips files already uploaded (idempotent — safe to re-run)
- `--dry-run` flag to preview without uploading
- Uses Flask app context so it connects to the correct DB + storage backend
- Works with both local and S3 storage (reads from `.env`)
- Reusable for future bulk imports of other document folders

### Task 4: Increase Flask Request Size Limit

The default Flask `MAX_CONTENT_LENGTH` may be too small for bulk uploads of 46 files. Set it in `create_app()`.

**File: `app/eqms/__init__.py`**

Add to the `create_app()` function, after `app.config.from_mapping(load_config())`:

```python
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max request size
```

This allows uploading multiple large files in one request (46 × ~7MB max ≈ ~320MB theoretical, but most files are under 500KB).

**Note:** Actually, for the web upload, the user will likely upload in batches. Set it to 100MB which covers any reasonable batch. The bulk import script bypasses this limit since it reads from disk.

---

## Verification

After implementation:

1. **Test multi-file upload via UI:**
   - Navigate to Quality Management Documents
   - Create a folder called "Test Upload"
   - Select multiple files and upload
   - Verify all files appear in the folder
   - Verify "View" works for .docx files
   - Delete the test folder

2. **Test bulk import script (dry run):**
   ```bash
   python scripts/bulk_import_admin_docs.py \
       --directory "QM Documents" \
       --library qms_documents \
       --folder "Original - FileHold" \
       --dry-run
   ```
   Verify it lists all 46 files.

3. **Verify the script handles re-runs gracefully** (idempotent skip logic).

---

## Files to Modify

| File | Change |
|------|--------|
| `app/eqms/modules/admin_docs/admin.py` | Multi-file upload support in `admin_docs_upload_document` |
| `app/eqms/templates/admin/admin_docs/index.html` | Add `multiple` to file input, update help text |
| `app/eqms/__init__.py` | Set `MAX_CONTENT_LENGTH` to 100MB |
| `scripts/bulk_import_admin_docs.py` | **NEW** — Bulk import CLI script |

---

## Post-Implementation: How to Run the Bulk Import

After the dev agent pushes the changes:

### Option A: Via the Web UI (Recommended)
1. Log into SilqQMS as admin
2. Go to **Quality Management Documents**
3. Click **Create Folder** → name it `Original - FileHold`
4. Open the `Original - FileHold` folder
5. Click **Upload** → select all 46 `.docx` files from the `QM Documents` folder → submit
6. Verify all 46 files appear and are viewable

### Option B: Via the Bulk Import Script (for large batches)
```bash
# From the project root, with .env configured:
python scripts/bulk_import_admin_docs.py \
    --directory "QM Documents" \
    --library qms_documents \
    --folder "Original - FileHold"
```

This will create the folder and upload all 46 files in one operation.

---

## Important Notes

- The `QM Documents/` folder is in `.gitignore` — these binary files should NOT be committed to git.
- The documents are stored in the configured storage backend (S3 in production, local `storage/` in development).
- `secure_filename()` from Werkzeug will normalize filenames (e.g., spaces → underscores), which is expected and desired.
- The 46 files total ~19.5MB. The largest file is `QM.SLQ014 B Electronic Doc System WI.docx` at ~6.9MB.
- All files are `.docx` (Word) format. The system already supports viewing/downloading `.docx` files.
