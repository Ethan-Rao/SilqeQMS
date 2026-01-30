#!/usr/bin/env python3
"""
Delete distributions created from PDF import (source='pdf_import').
Use after deploying the fix that stops PDF import from creating distributions.
"""
from __future__ import annotations

import os

from app.eqms.modules.rep_traceability.models import DistributionLogEntry
from scripts._db_utils import script_session


def main() -> None:
    db_url = (os.environ.get("DATABASE_URL") or "sqlite:///eqms.db").strip()
    with script_session(db_url) as s:
        rows = s.query(DistributionLogEntry).filter(DistributionLogEntry.source == "pdf_import").all()
        count = len(rows)
        for r in rows:
            s.delete(r)
        print(f"Deleted {count} pdf_import distributions.")


if __name__ == "__main__":
    main()
