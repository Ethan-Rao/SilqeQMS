"""
Shared read-only loader for the consolidated change-history log (DCO_Log_v2.csv).

Produced by ``scripts/reconcile_controlled_docs.py`` (Prompt 4/5) and committed
under ``eQMS_Upload_Staging/reconciliation/``. This module gives the app a small,
cached, dependency-free view over that CSV so we can surface change history
without a schema change:

- E1 revision-history timeline (per-revision DCO reference + change summary).
- E2 in-app DCO Log / change-history traceability view.

It is intentionally report-derived and read-only. If the CSV is absent (e.g. a
fresh checkout before reconciliation runs) every accessor degrades gracefully to
empty results rather than raising.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

# app/eqms/modules/document_control/dco_log.py -> repo root is parents[4]
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_CSV = _REPO_ROOT / "eQMS_Upload_Staging" / "reconciliation" / "DCO_Log_v2.csv"

_FIELDS = (
    "dco_number",
    "document_number",
    "document_title",
    "from_rev",
    "to_rev",
    "change_description",
    "originator",
    "date_requested",
    "effective_date",
    "impact_assessments",
)


@dataclass(frozen=True)
class DcoLogRow:
    dco_number: str
    document_number: str
    document_title: str
    from_rev: str
    to_rev: str
    change_description: str
    originator: str
    date_requested: str
    effective_date: str
    impact_assessments: str


# Cache keyed by (resolved path, mtime) so edits to the CSV are picked up but we
# don't re-parse on every request.
_cache: dict[tuple[str, float], list[DcoLogRow]] = {}
_lock = Lock()


def _csv_path(override: str | Path | None = None) -> Path:
    if override:
        return Path(override)
    return _DEFAULT_CSV


def rev_order_key(rev: str) -> tuple[int, int | str]:
    """Sort key for revision labels: numeric revs first by value, then Excel-style
    base-26 alpha revs (A < B < ... < Z < AA). Blank/'-' sort lowest."""
    r = (rev or "").strip().upper()
    if not r or r == "-":
        return (0, 0)
    if r.isdigit():
        return (1, int(r))
    if re.fullmatch(r"[A-Z]+", r):
        n = 0
        for ch in r:
            n = n * 26 + (ord(ch) - ord("A") + 1)
        return (2, n)
    return (3, r)


def load_rows(path: str | Path | None = None) -> list[DcoLogRow]:
    """Return all DCO log rows (cached by file mtime). Empty list if missing."""
    p = _csv_path(path)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        return []
    key = (str(p.resolve()), mtime)
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached
        rows: list[DcoLogRow] = []
        with p.open(encoding="utf-8-sig", newline="") as fh:
            for raw in csv.DictReader(fh):
                rows.append(DcoLogRow(**{f: (raw.get(f) or "").strip() for f in _FIELDS}))
        _cache[key] = rows
        return rows


def changes_for_document(doc_number: str, path: str | Path | None = None) -> list[DcoLogRow]:
    """All log rows affecting a document, ordered by target revision (ascending)."""
    doc = (doc_number or "").strip().upper()
    rows = [r for r in load_rows(path) if r.document_number.strip().upper() == doc]
    rows.sort(key=lambda r: (rev_order_key(r.to_rev), rev_order_key(r.from_rev), r.dco_number))
    return rows


def change_by_revision(doc_number: str, path: str | Path | None = None) -> dict[str, DcoLogRow]:
    """Map target-revision label (upper) -> the most relevant DCO row that
    produced it. When multiple DCOs touch the same target rev, the last one
    (by ordering) wins so the timeline shows the change that set that revision."""
    out: dict[str, DcoLogRow] = {}
    for r in changes_for_document(doc_number, path):
        to_rev = (r.to_rev or "").strip().upper()
        if not to_rev or to_rev == "-":
            continue
        out[to_rev] = r
    return out
