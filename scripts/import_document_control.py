"""
Bulk import controlled documents (with full revision history) into Document Control.

Unlike the interactive UI (which builds one Draft revision at a time), this loads
superseded revisions directly so version history is preserved for Track A.

Usage:
    python scripts/import_document_control.py \
        --manifest docs/track-a/dc_manifest.json \
        --base-dir "QM Documents" \
        [--dry-run]

Manifest format (JSON list). Revisions must be listed in ascending order:

    [
      {
        "doc_number": "QM.SLQ001",
        "title": "Document Control SOP",
        "doc_type": "SOP",
        "category": "Quality Management",
        "status": "Released",
        "revisions": [
          {"revision": "A", "file": "QM.SLQ001 A.pdf", "effective_date": "2020-01-01",
           "change_summary": "Initial release", "released": true},
          {"revision": "B", "file": "QM.SLQ001 B.pdf", "effective_date": "2023-05-01",
           "change_summary": "Updated scope", "released": true}
        ]
      },
      {
        "doc_number": "QM.SLQ099",
        "title": "Retired SOP",
        "doc_type": "SOP",
        "category": "Quality Management",
        "status": "Obsolete",
        "obsolete_reason": "Superseded by QM.SLQ001",
        "revisions": [
          {"revision": "A", "file": "QM.SLQ099 A.pdf", "released": true}
        ]
      }
    ]

The importer is idempotent: re-running skips documents/revisions that already
exist (matched by doc_number and revision label). Requires Flask app context
(reads .env for DB + storage config).
"""
import argparse
import json
import mimetypes
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.eqms import create_app
from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.document_control.service import import_document_with_revisions


def _parse_date(value):
    if not value:
        return None
    return date.fromisoformat(str(value).strip())


def _load_revisions(entry, base_dir, dry_run):
    revisions = []
    for rev in entry.get("revisions", []):
        r = {
            "revision": rev["revision"],
            "change_summary": rev.get("change_summary", ""),
            "effective_date": _parse_date(rev.get("effective_date")),
            "released": rev.get("released", True),
        }
        file_name = rev.get("file")
        if file_name:
            fp = base_dir / file_name
            if not fp.is_file():
                raise FileNotFoundError(f"{entry['doc_number']} rev {rev['revision']}: missing file {fp}")
            r["filename"] = fp.name
            r["content_type"] = mimetypes.guess_type(fp.name)[0] or "application/octet-stream"
            # In dry-run we avoid reading bytes but still flag that a file is present.
            r["file_bytes"] = b"" if dry_run else fp.read_bytes()
            if dry_run:
                # Signal "a file would be attached" without loading it.
                r["file_bytes"] = b"\x00"
        revisions.append(r)
    return revisions


def _enrich_from_dco_log(entries):
    """Fill empty change_summary / effective_date on each revision from the
    consolidated DCO_Log_v2.csv (keyed by doc_number + target revision)."""
    from app.eqms.modules.document_control.dco_log import change_by_revision

    for entry in entries:
        by_rev = change_by_revision(entry.get("doc_number", ""))
        if not by_rev:
            continue
        for rev in entry.get("revisions", []):
            row = by_rev.get(str(rev.get("revision", "")).strip().upper())
            if not row:
                continue
            if not (rev.get("change_summary") or "").strip() and row.change_description:
                rev["change_summary"] = row.change_description
            if not rev.get("effective_date") and row.effective_date:
                rev["effective_date"] = row.effective_date


def main():
    parser = argparse.ArgumentParser(description="Import controlled documents with revision history")
    parser.add_argument("--manifest", "-m", help="Path to a JSON manifest (list of documents)")
    parser.add_argument("--manifest-dir", help="Directory of per-document JSON manifests (e.g. reconciliation/manifests)")
    parser.add_argument("--base-dir", "-b", required=True, help="Directory holding the revision files")
    parser.add_argument("--enrich-dco", action="store_true", help="Fill change summaries/effective dates from DCO_Log_v2.csv")
    parser.add_argument("--dry-run", action="store_true", help="Report the plan without writing anything")
    args = parser.parse_args()

    if not args.manifest and not args.manifest_dir:
        print("ERROR: provide --manifest or --manifest-dir.")
        sys.exit(1)

    base_dir = Path(args.base_dir)
    if not base_dir.is_dir():
        base_dir = ROOT / args.base_dir
    if not base_dir.is_dir():
        print(f"ERROR: Base dir not found: {args.base_dir}")
        sys.exit(1)

    entries = []
    if args.manifest:
        manifest_path = Path(args.manifest)
        if not manifest_path.is_file():
            manifest_path = ROOT / args.manifest
        if not manifest_path.is_file():
            print(f"ERROR: Manifest not found: {args.manifest}")
            sys.exit(1)
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            print("ERROR: --manifest must be a JSON list of documents.")
            sys.exit(1)
        entries.extend(loaded)
    if args.manifest_dir:
        mdir = Path(args.manifest_dir)
        if not mdir.is_dir():
            mdir = ROOT / args.manifest_dir
        if not mdir.is_dir():
            print(f"ERROR: Manifest dir not found: {args.manifest_dir}")
            sys.exit(1)
        for fp in sorted(mdir.glob("*.json")):
            doc = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(doc, dict):
                entries.append(doc)
            elif isinstance(doc, list):
                entries.extend(doc)

    if not entries:
        print("ERROR: No documents found to import.")
        sys.exit(1)

    if args.enrich_dco:
        _enrich_from_dco_log(entries)

    app = create_app()
    with app.app_context(), app.test_request_context():
        s = db_session()
        admin_user = s.query(User).join(User.roles).filter_by(key="admin").first()
        if not admin_user:
            print("ERROR: No admin user found. Run init_db.py first.")
            sys.exit(1)

        totals = {"docs": 0, "created": 0, "skipped": 0, "files": 0, "errors": 0}
        for entry in entries:
            try:
                revisions = _load_revisions(entry, base_dir, args.dry_run)
                summary = import_document_with_revisions(
                    s,
                    doc_number=entry["doc_number"],
                    title=entry["title"],
                    doc_type=entry["doc_type"],
                    category=entry.get("category"),
                    owner_user=admin_user,
                    status=entry.get("status", "Released"),
                    obsolete_reason=entry.get("obsolete_reason"),
                    revisions=revisions,
                    dry_run=args.dry_run,
                )
            except Exception as e:  # noqa: BLE001 - report and continue
                totals["errors"] += 1
                print(f"  FAIL {entry.get('doc_number', '?')}: {e}")
                continue

            totals["docs"] += 1
            totals["created"] += len(summary["revisions_created"])
            totals["skipped"] += len(summary["revisions_skipped"])
            totals["files"] += len(summary["files_added"])
            prefix = "[DRY RUN] " if args.dry_run else ""
            print(
                f"  {prefix}{summary['doc_number']} ({summary['document_action']}, "
                f"final={summary['final_status']}): "
                f"created={summary['revisions_created']} "
                f"skipped={summary['revisions_skipped']} "
                f"files={summary['files_added']}"
            )

        if not args.dry_run and totals["errors"] == 0:
            s.commit()
        elif not args.dry_run:
            s.rollback()
            print("\nRolled back due to errors; fix the manifest and re-run.")

        print(
            f"\n{'[DRY RUN] ' if args.dry_run else ''}Done: {totals['docs']} documents, "
            f"{totals['created']} revisions created, {totals['skipped']} skipped, "
            f"{totals['files']} files, {totals['errors']} errors"
        )


if __name__ == "__main__":
    main()
