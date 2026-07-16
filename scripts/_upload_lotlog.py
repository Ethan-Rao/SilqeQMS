"""Upload the local LotLog.csv to S3 storage so the Sales Dashboard picks it up.

Usage:
    python scripts/_upload_lotlog.py              # dry run
    python scripts/_upload_lotlog.py --execute    # write to S3
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOCAL_CSV = ROOT / "app" / "eqms" / "data" / "LotLog.csv"
STORAGE_KEY = "data/LotLog.csv"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload LotLog.csv to S3")
    parser.add_argument("--execute", action="store_true", help="Write to S3 (default: dry run)")
    args = parser.parse_args()
    dry_run = not args.execute

    if not LOCAL_CSV.is_file():
        print(f"ERROR: local LotLog not found: {LOCAL_CSV}")
        sys.exit(1)

    data = LOCAL_CSV.read_bytes()
    rows = list(csv.DictReader(data.decode("utf-8").splitlines()))
    print(f"Local LotLog.csv: {len(rows)} data rows ({len(data):,} bytes)")
    for r in rows:
        print(f"  {r.get('Lot', '?'):<30}  SKU={r.get('SKU', '?'):<12}  Units={r.get('Total Units in Lot', '?')}")

    if dry_run:
        print(f"\n[DRY RUN] Would upload to storage key: {STORAGE_KEY}")
        print("Re-run with --execute to write to S3.")
        return

    import os
    os.environ.setdefault("STORAGE_BACKEND", "s3")

    from app.eqms import create_app
    app = create_app()
    with app.app_context():
        from app.eqms.storage import storage_from_config
        storage = storage_from_config(app.config)
        storage.put_bytes(STORAGE_KEY, data, content_type="text/csv")
        print(f"\nUploaded to storage: {STORAGE_KEY}")
        print("Sales Dashboard inventory will reflect the new data immediately.")


if __name__ == "__main__":
    main()
