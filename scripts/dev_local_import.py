"""
DEV-ONLY local import harness (Phase 3 Prompt 5 / E1 evidence).

Populates a **local, throwaway** database + storage with the reconciled controlled
documents (114 docs with full revision history) plus a representative set of
admin_docs library files, so the new discovery/list/timeline UI can be exercised
against realistic data.

Safety
------
This script HARD-OVERRIDES the environment to a local sqlite DB and local file
storage *before* the app config loads, so it can never touch the production
Postgres/Spaces configured in .env. It refuses to run if DATABASE_URL still
points at a non-sqlite backend.

Usage
-----
    python scripts/dev_local_import.py            # build/refresh the local corpus
    python scripts/dev_local_import.py --reset     # delete the local DB/storage first

Then run the app against the same local env, e.g. (PowerShell):
    $env:DATABASE_URL="sqlite:///dev_local.db"; $env:STORAGE_BACKEND="local";
    $env:STORAGE_LOCAL_ROOT="dev_local_storage"; $env:ENV="development";
    $env:ADMIN_PASSWORD="admin"; python -m flask --app app.wsgi run
Log in as admin@silqeqms.com / admin (or the printed password).
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV_DB = ROOT / "dev_local.db"
DEV_STORAGE = ROOT / "dev_local_storage"


def _force_local_env() -> None:
    os.environ["ENV"] = "development"
    os.environ["DATABASE_URL"] = f"sqlite:///{DEV_DB.as_posix()}"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["STORAGE_LOCAL_ROOT"] = str(DEV_STORAGE)
    os.environ.setdefault("SECRET_KEY", "dev-local-secret")
    os.environ.setdefault("ADMIN_PASSWORD", "admin")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local dev corpus for E1")
    parser.add_argument("--reset", action="store_true", help="Delete the local DB/storage first")
    args = parser.parse_args()

    _force_local_env()
    if not os.environ["DATABASE_URL"].startswith("sqlite"):
        print("REFUSING TO RUN: DATABASE_URL is not sqlite. This script is local-only.")
        sys.exit(1)

    if args.reset:
        if DEV_DB.exists():
            DEV_DB.unlink()
        if DEV_STORAGE.exists():
            shutil.rmtree(DEV_STORAGE, ignore_errors=True)
        print("Reset: removed local dev DB + storage.")

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from app.eqms import create_app
    from app.eqms.models import Base
    from scripts.init_db import seed_only

    app = create_app()
    with app.app_context():
        engine = app.extensions["sqlalchemy_engine"]
        Base.metadata.create_all(engine)
        print("Schema created (sqlite).")
    seed_only()
    print("Seeded permissions/roles/admin.")

    staging_dc = ROOT / "eQMS_Upload_Staging" / "document_control"
    manifests = ROOT / "eQMS_Upload_Staging" / "reconciliation" / "manifests"
    py = sys.executable

    # 1) Controlled documents with full revision history (114 docs).
    print("\n=== Importing controlled documents (Document Control) ===")
    subprocess.run(
        [py, str(ROOT / "scripts" / "import_document_control.py"),
         "--manifest-dir", str(manifests), "--base-dir", str(staging_dc), "--enrich-dco"],
        check=False, env=os.environ.copy(),
    )

    # 2) A representative admin_docs library so cross-system search has content.
    #    The bulk importer reads a flat directory, so point it at the flat
    #    "QM Documents" folder (real QMS files) rather than the nested staging tree.
    qm_docs = ROOT / "QM Documents"
    if qm_docs.is_dir():
        print("\n=== Importing a representative admin_docs library (QM Documents) ===")
        subprocess.run(
            [py, str(ROOT / "scripts" / "bulk_import_admin_docs.py"),
             "--directory", str(qm_docs), "--library", "qms_documents",
             "--folder", "QM Documents"],
            check=False, env=os.environ.copy(),
        )

    print("\nLocal corpus ready. Start the app with the same env to browse it (see header).")


if __name__ == "__main__":
    main()
