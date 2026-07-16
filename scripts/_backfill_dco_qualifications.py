"""
Retroactively seed ``dco_auto_qualified`` TrainingAssignment records from the
DCO documents (DCO087–096) that released the current QM.SLQ SOP revisions.

DCO number, effective date, covered QM.SLQ documents, and approver names come
from the hardcoded ``DCO_DATA`` table below (the source of truth). Where a
``.docx`` DCO form exists in ``QMSInProcess/<DCO>/``, we additionally parse it
and log a warning if the parsed values diverge from ``DCO_DATA``.

For each (approver-user, covered-document) pair we create a pre-acknowledged
``dco_auto_qualified`` assignment stamped with the DCO effective date. Idempotent.

Usage:
    python scripts/_backfill_dco_qualifications.py            # dry-run
    python scripts/_backfill_dco_qualifications.py --execute  # write records
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv

QMS_IN_PROCESS = os.path.join(os.path.dirname(__file__), "..", "QMSInProcess")

DCO_DATA = {
    "DCO087": {
        "date": "2025-12-10",
        "docs": ["QM.SLQ022"],
        "approvers": ["Ethan Rao", "Brian McVerry"],  # Verne Sharma no longer active — omit
    },
    "DCO088": {
        "date": "2026-03-13",
        "docs": ["QM.SLQ034"],
        "approvers": ["Ethan Rao", "Brian McVerry"],
    },
    "DCO089": {
        "date": "2026-04-30",
        "docs": ["QM.SLQ004"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chris Turner", "Na He"],
    },
    "DCO090": {
        # Design review DCO covering DC.SLQ002 (internal project) — no QM.SLQ docs.
        "date": None,
        "docs": [],
        "approvers": [],
    },
    "DCO091": {
        "date": "2026-05-28",
        "docs": ["QM.SLQ001", "QM.SLQ014"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chris Turner", "Na He"],
    },
    "DCO092": {
        "date": "2026-06-09",
        "docs": ["QM.SLQ003", "QM.SLQ015", "QM.SLQ017", "QM.SLQ020", "QM.SLQ036"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner"],
    },
    "DCO093": {
        "date": "2026-07-08",
        "docs": [
            "QM.SLQ012", "QM.SLQ013", "QM.SLQ016", "QM.SLQ018",
            "QM.SLQ021", "QM.SLQ022", "QM.SLQ023", "QM.SLQ028", "QM.SLQ030",
        ],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner", "Tom Downey"],
    },
    "DCO094": {
        "date": "2026-06-25",
        "docs": [
            "QM.SLQ011", "QM.SLQ026", "QM.SLQ027", "QM.SLQ029",
            "QM.SLQ033", "QM.SLQ037", "QM.SLQ038", "QM.SLQ039",
            "QM.SLQ040", "QM.SLQ043", "QM.SLQ045", "QM.SLQ046",
            "QM.SLQ047", "QM.SLQ048", "QM.SLQ049", "QM.SLQ050", "QM.SLQ051",
        ],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner", "Tom Downey"],
    },
    "DCO095": {
        "date": "2026-07-09",
        "docs": ["QM.SLQ052"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner", "Tom Downey"],
    },
    "DCO096": {
        "date": "2026-07-16",
        "docs": ["QM.SLQ053"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner", "Tom Downey"],
    },
}


def _norm_name(name: str) -> str:
    return " ".join((name or "").split()).strip().lower()


def _parse_dco_docx(path: str) -> dict | None:
    """Best-effort parse of a DCO .docx for verification (not the source of truth)."""
    try:
        from docx import Document as Docx
    except Exception:  # noqa: BLE001
        return None
    if not os.path.isfile(path):
        return None
    try:
        doc = Docx(path)
    except Exception:  # noqa: BLE001
        return None

    parsed = {"date": None, "docs": [], "approvers": []}
    for table in doc.tables:
        headers = [c.text.strip() for c in table.rows[0].cells] if table.rows else []
        headers_l = [h.lower() for h in headers]

        # Label/value tables (DCO # / Req. Effective Date).
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            for i, cell in enumerate(cells):
                label = cell.rstrip(":").strip().lower()
                if label in ("req. effective date", "effective date") and i + 1 < len(cells):
                    parsed["date"] = cells[i + 1] or parsed["date"]

        # Covered documents table.
        if any("document" in h and ("part" in h or "number" in h) for h in headers_l):
            idx = next(i for i, h in enumerate(headers_l) if "document" in h)
            for row in table.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if idx < len(cells) and cells[idx].upper().startswith("QM.SLQ"):
                    parsed["docs"].append(cells[idx].split()[0])

        # Approvals table.
        if any("printed name" in h for h in headers_l):
            idx = next(i for i, h in enumerate(headers_l) if "printed name" in h)
            for row in table.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if idx < len(cells) and cells[idx]:
                    parsed["approvers"].append(cells[idx])
    return parsed


def _verify(dco_id: str, hard: dict, parsed: dict | None) -> None:
    if not parsed:
        return
    hard_docs = {d.upper().split()[0] for d in hard["docs"]}
    parsed_docs = {d.upper().split()[0] for d in parsed.get("docs", [])}
    if parsed_docs and parsed_docs != hard_docs:
        print(f"  WARN  {dco_id} parsed docs {sorted(parsed_docs)} != hardcoded {sorted(hard_docs)}")
    hard_appr = {_norm_name(a) for a in hard["approvers"]}
    parsed_appr = {_norm_name(a) for a in parsed.get("approvers", [])}
    # Verne Sharma is intentionally omitted from hardcoded data; ignore that diff.
    parsed_appr.discard("verne sharma")
    if parsed_appr and parsed_appr != hard_appr:
        print(f"  WARN  {dco_id} parsed approvers {sorted(parsed_appr)} != hardcoded {sorted(hard_appr)}")


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import User
    from app.eqms.modules.training.models import TrainingAssignment
    from app.eqms.modules.training.service import resolve_current_revision
    from app.eqms.utils import utcnow

    app = create_app()
    with app.app_context():
        s = db_session()
        actor = s.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
        if actor is None:
            print("No active user found to attribute records to. Aborting.")
            return

        users = s.query(User).all()
        users_by_name = {}
        for u in users:
            if u.display_name:
                users_by_name[_norm_name(u.display_name)] = u

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print()

        total_created = 0
        per_dco: dict[str, int] = {}
        skips: list[str] = []

        for dco_id, data in DCO_DATA.items():
            per_dco[dco_id] = 0
            _verify(dco_id, data, _parse_dco_docx(os.path.join(QMS_IN_PROCESS, dco_id, f"{dco_id}.docx")))

            if not data["docs"]:
                print(f"  SKIP  {dco_id} — no covered QM.SLQ documents")
                continue

            dco_date = data["date"]
            ack_dt = (
                datetime.combine(date.fromisoformat(dco_date), time(0, 0))
                if dco_date else utcnow()
            )

            # Resolve documents once per DCO.
            resolved_docs = []
            for doc_number in data["docs"]:
                resolved = resolve_current_revision(s, doc_number)
                if not resolved:
                    msg = f"SKIP  {dco_id}  {doc_number} — document not found in DB"
                    print(f"  {msg}")
                    skips.append(msg)
                    continue
                resolved_docs.append((doc_number, resolved[0], resolved[1]))

            # Resolve approver users once per DCO.
            resolved_users = []
            for approver in data["approvers"]:
                u = users_by_name.get(_norm_name(approver))
                if u is None:
                    msg = f"SKIP  {dco_id}  {approver} — no matching user"
                    print(f"  {msg}")
                    skips.append(msg)
                    continue
                if not u.is_active:
                    msg = f"SKIP  {dco_id}  {approver} — user inactive"
                    print(f"  {msg}")
                    skips.append(msg)
                    continue
                resolved_users.append(u)

            for u in resolved_users:
                for _doc_number, doc, rev in resolved_docs:
                    exists = (
                        s.query(TrainingAssignment)
                        .filter(
                            TrainingAssignment.assigned_to_user_id == u.id,
                            TrainingAssignment.document_id == doc.id,
                            TrainingAssignment.training_type == "dco_auto_qualified",
                            TrainingAssignment.source_reference == dco_id,
                        )
                        .first()
                    )
                    if exists:
                        continue
                    print(f"  CREATE {dco_id}  {u.display_name} <- {doc.doc_number} "
                          f"Rev {rev.revision if rev else '?'}")
                    total_created += 1
                    per_dco[dco_id] += 1
                    if not DRY_RUN:
                        s.add(TrainingAssignment(
                            item_type="document",
                            item_title=f"{doc.doc_number} Rev {rev.revision if rev else '?'} — {doc.title}",
                            document_id=doc.id,
                            document_revision_id=rev.id if rev else None,
                            assigned_to_user_id=u.id,
                            assigned_by_user_id=actor.id,
                            training_type="dco_auto_qualified",
                            source_reference=dco_id,
                            acknowledged_at=ack_dt,
                            assigned_at=utcnow(),
                            created_at=utcnow(),
                        ))

        if not DRY_RUN:
            s.commit()

        print()
        print("=" * 48)
        print(f"Total records created: {total_created}")
        for dco_id, n in per_dco.items():
            print(f"  {dco_id}: {n}")
        if skips:
            print(f"Skipped items: {len(skips)}")
        if DRY_RUN:
            print("DRY RUN — re-run with --execute to write records.")


if __name__ == "__main__":
    main()
