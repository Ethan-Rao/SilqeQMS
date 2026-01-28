#!/usr/bin/env python3
"""
Delete distributions created from PDF import (source='pdf_import').
Use after deploying the fix that stops PDF import from creating distributions.
"""
from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.eqms.modules.rep_traceability.models import DistributionLogEntry


def main() -> None:
    db_url = (os.environ.get("DATABASE_URL") or "sqlite:///eqms.db").strip()
    engine = create_engine(db_url, future=True)
    with Session(engine) as s:
        rows = s.query(DistributionLogEntry).filter(DistributionLogEntry.source == "pdf_import").all()
        count = len(rows)
        for r in rows:
            s.delete(r)
        s.commit()
        print(f"Deleted {count} pdf_import distributions.")


if __name__ == "__main__":
    main()
