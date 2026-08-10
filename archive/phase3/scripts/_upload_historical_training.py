"""
Re-upload historical training record files from the local ``EmployeeTraining/``
directory (workspace root) into the Training Records (employee_training)
admin_docs library.

The P37 scaffold script inadvertently removed these files from storage; this
script restores them from the local source.

Folder mapping:
    EmployeeTraining/<Employee>/*        -> <Employee>/Historical Records/
    EmployeeTraining/VerneSharma/*       -> Historical Records/         (top level)
    EmployeeTraining/JobDescriptions/*   -> Job Descriptions/           (top level)
    EmployeeTraining/Silq Training Matrix.pdf   -> Training Matrix/     (top level)
    EmployeeTraining/SILQ Training Matrix.xlsx  -> Training Matrix/     (top level)

Behavior:
    - Dry-run by default; ``--execute`` to commit.
    - Idempotent: a file whose (secure) filename already exists in the target
      folder is skipped (logged SKIP).
    - Prints a summary of uploaded / skipped / missing-locally counts.

Usage:
    python scripts/_upload_historical_training.py            # dry-run
    python scripts/_upload_historical_training.py --execute  # upload
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv

LIBRARY = "employee_training"
SOURCE_ROOT = os.path.join(os.path.dirname(__file__), "..", "EmployeeTraining")

# Active employees: files go into their "Historical Records" subfolder.
EMPLOYEES = [
    "BrianMcVerry", "ChrisTurner", "ChuckGreiner", "EthanRao",
    "HaleyShomo", "NaHe", "TomDowney",
]

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".csv": "text/csv",
}


def _norm(name: str) -> str:
    return (name or "").lower().replace(" ", "").replace("_", "")


def _content_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return CONTENT_TYPES.get(ext, "application/octet-stream")


def _local_files(*parts: str) -> list[str]:
    """Return absolute paths to files directly inside a local source directory."""
    d = os.path.join(SOURCE_ROOT, *parts)
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d)) if os.path.isfile(os.path.join(d, f))]


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from werkzeug.utils import secure_filename

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
    from app.eqms.modules.admin_docs.service import create_folder, upload_document

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
        if actor is None:
            print("No active user found to attribute uploads to. Aborting.")
            return

        folders = s.query(AdminDocFolder).filter(AdminDocFolder.library_key == LIBRARY).all()
        top_by_norm = {_norm(f.name): f for f in folders if f.parent_id is None}
        children_by_parent: dict[int, list] = {}
        for f in folders:
            if f.parent_id is not None:
                children_by_parent.setdefault(f.parent_id, []).append(f)

        def ensure_top(name: str):
            existing = top_by_norm.get(_norm(name))
            if existing:
                return existing
            print(f"  CREATE top-level folder '{name}'")
            if DRY_RUN:
                return None
            folder = create_folder(s, LIBRARY, name, actor, parent=None)
            top_by_norm[_norm(name)] = folder
            return folder

        def ensure_sub(parent, name: str):
            if parent is None:
                print(f"    CREATE subfolder '{name}' (parent pending — dry run)")
                return None
            for c in children_by_parent.get(parent.id, []):
                if _norm(c.name) == _norm(name):
                    return c
            print(f"  CREATE subfolder '{parent.name}/{name}'")
            if DRY_RUN:
                return None
            folder = create_folder(s, LIBRARY, name, actor, parent=parent)
            children_by_parent.setdefault(parent.id, []).append(folder)
            return folder

        # Build the (local source files, target folder) work list.
        # Each entry: (label, list_of_local_paths, target_folder_or_None)
        plan: list[tuple[str, list[str], object]] = []

        for emp in EMPLOYEES:
            target = ensure_sub(ensure_top(emp), "Historical Records")
            plan.append((f"{emp}/Historical Records", _local_files(emp), target))

        plan.append(("Historical Records (Verne Sharma)",
                     _local_files("VerneSharma"), ensure_top("Historical Records")))
        plan.append(("Job Descriptions",
                     _local_files("JobDescriptions"), ensure_top("Job Descriptions")))

        matrix_files = []
        for fn in ("Silq Training Matrix.pdf", "SILQ Training Matrix.xlsx"):
            p = os.path.join(SOURCE_ROOT, fn)
            if os.path.isfile(p):
                matrix_files.append(p)
        plan.append(("Training Matrix", matrix_files, ensure_top("Training Matrix")))

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Source root: {os.path.abspath(SOURCE_ROOT)}")
        print()

        uploaded = skipped = missing = 0

        for label, local_paths, target in plan:
            if not local_paths:
                print(f"  (no local files for {label})")
                continue

            existing_names = set()
            if target is not None:
                existing_names = {
                    _norm(f.filename)
                    for f in s.query(AdminDocFile)
                    .filter(AdminDocFile.library_key == LIBRARY, AdminDocFile.folder_id == target.id)
                    .all()
                }

            for path in local_paths:
                fname = os.path.basename(path)
                safe = secure_filename(fname) or "document.bin"
                if not os.path.isfile(path):
                    print(f"  MISSING  {label}/{fname}")
                    missing += 1
                    continue
                if _norm(safe) in existing_names or _norm(fname) in existing_names:
                    print(f"  SKIP     {label}/{fname} (already present)")
                    skipped += 1
                    continue
                print(f"  UPLOAD   {label}/{fname}")
                uploaded += 1
                if not DRY_RUN and target is not None:
                    with open(path, "rb") as fh:
                        data = fh.read()
                    upload_document(s, LIBRARY, target, data, fname, _content_type(fname), actor)
                    existing_names.add(_norm(safe))

        if not DRY_RUN:
            s.commit()

        print()
        print(f"Summary: {uploaded} uploaded, {skipped} skipped, {missing} missing locally.")
        if DRY_RUN:
            print("DRY RUN — re-run with --execute to upload.")


if __name__ == "__main__":
    main()
