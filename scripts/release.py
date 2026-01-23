"""
Release-phase helper for DigitalOcean App Platform.

Goal:
- Fail fast if DATABASE_URL is missing (avoid silently using SQLite in prod).
- Run alembic migrations.
- Seed permissions/roles/admin user (idempotent; does NOT overwrite existing passwords).

Usage:
  python scripts/release.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _require_env(name: str) -> str:
    v = (os.environ.get(name) or "").strip()
    if not v:
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            "On DigitalOcean App Platform, set this in Settings → Environment Variables."
        )
    return v


def run_release() -> None:
    db_url = _require_env("DATABASE_URL")
    # Guardrail: prevent accidental prod deploys against SQLite.
    env = (os.environ.get("ENV") or "").strip().lower()
    if env in ("prod", "production") and db_url.startswith("sqlite"):
        raise RuntimeError("Refusing to run release on sqlite DATABASE_URL in production. Set DATABASE_URL to Postgres.")

    print("=== SilqeQMS release start ===", flush=True)
    print(f"ENV={env or '(unset)'}", flush=True)
    print("Running Alembic migrations...", flush=True)

    from alembic import command
    from alembic.config import Config

    # Diagnostic: confirm migration content for customer_reps default
    try:
        migration_path = ROOT / "migrations" / "versions" / "e4f5a6b7c8d9_add_customer_reps_table.py"
        if migration_path.exists():
            with migration_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if "is_primary" in line:
                        print(f"[diag] {line.strip()}", flush=True)
                        break
    except Exception as e:
        print(f"[diag] failed to read migration file: {e}", flush=True)

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")
    print("Migrations complete.", flush=True)

    print("Seeding permissions/admin (idempotent)...", flush=True)
    from scripts import init_db

    init_db.seed_only(database_url=db_url)
    print("Seed complete.", flush=True)
    print("=== SilqeQMS release done ===", flush=True)


def main() -> None:
    run_release()


if __name__ == "__main__":
    main()

