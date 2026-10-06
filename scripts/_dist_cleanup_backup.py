"""Pre-cleanup logical backup of the production database.

Writes, into a timestamped folder OUTSIDE the repo:
  - <table>.csv for every public table (full logical backup)
  - restore_<table>.sql for the tables the cleanup will modify, as
    replayable DELETE + INSERT statements
  - manifest.txt with row counts and the schema snapshot

Read-only against the database.
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

load_dotenv(ROOT / ".env")

BACKUP_ROOT = Path.home() / "SilqQMS_backups"

# Tables the cleanup will write to; these get full SQL restore files.
AFFECTED = [
    "sales_orders",
    "sales_order_lines",
    "distribution_log_entries",
    "distribution_lines",
    "order_pdf_attachments",
]


def sql_literal(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = BACKUP_ROOT / f"pre_dist_cleanup_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)

    manifest = [f"SilqQMS production logical backup", f"taken: {dt.datetime.now().isoformat()}", ""]

    with engine.connect() as c:
        tables = [
            r[0]
            for r in c.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY 1"
                )
            )
        ]

        manifest.append(f"tables: {len(tables)}")
        manifest.append("")

        total_rows = 0
        for t in tables:
            rows = c.execute(text(f'SELECT * FROM "{t}"')).fetchall()
            cols = list(rows[0]._fields) if rows else [
                r[0]
                for r in c.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name=:t ORDER BY ordinal_position"
                    ),
                    {"t": t},
                )
            ]
            with open(outdir / f"{t}.csv", "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(cols)
                for r in rows:
                    w.writerow(["" if v is None else v for v in r])
            total_rows += len(rows)
            manifest.append(f"{len(rows):7d}  {t}")

            if t in AFFECTED:
                collist = ", ".join(f'"{col}"' for col in cols)
                with open(outdir / f"restore_{t}.sql", "w", encoding="utf-8") as fh:
                    fh.write(f"-- Restore {t} to state at {stamp}\nBEGIN;\n")
                    fh.write(f'DELETE FROM "{t}";\n')
                    for r in rows:
                        vals = ", ".join(sql_literal(v) for v in r)
                        fh.write(f'INSERT INTO "{t}" ({collist}) VALUES ({vals});\n')
                    seq = c.execute(
                        text("SELECT pg_get_serial_sequence(:t,'id')"), {"t": t}
                    ).scalar()
                    if seq:
                        fh.write(
                            f"SELECT setval('{seq}', "
                            f'(SELECT COALESCE(MAX("id"),1) FROM "{t}"));\n'
                        )
                    fh.write("COMMIT;\n")

        manifest.append("")
        manifest.append(f"total rows: {total_rows}")
        manifest.append("")
        manifest.append("SQL restore files written for:")
        for t in AFFECTED:
            manifest.append(f"  restore_{t}.sql")

    (outdir / "manifest.txt").write_text("\n".join(manifest), encoding="utf-8")
    print(f"backup written to: {outdir}")
    print("\n".join(manifest[-12:]))


if __name__ == "__main__":
    main()
