"""
Create Haley Shomo's read-only (staff role) account.

Usage:
    python scripts/_create_haley_account.py           # dry-run
    python scripts/_create_haley_account.py --execute # commit to DB

Idempotent — skips if the account already exists. After creation, run
scripts/_init_training_matrix.py --execute so she gets her assignments.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv

EMAIL = "Haleys@silq.tech"
DISPLAY_NAME = "Haley Shomo"
ROLE_KEY = "staff"
TEMP_PASSWORD = "Silq2026!"


def main() -> None:
    os.environ.setdefault("FLASK_ENV", "production")
    os.environ.setdefault("STORAGE_BACKEND", "local")

    from werkzeug.security import generate_password_hash

    from app.eqms import create_app
    from app.eqms.db import db_session
    from app.eqms.models import Role, User

    app = create_app()
    with app.app_context():
        s = db_session()

        role = s.query(Role).filter(Role.key == ROLE_KEY).first()
        if not role:
            print(f"ERROR: Role '{ROLE_KEY}' not found in DB. Cannot proceed.")
            sys.exit(1)

        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Role: id={role.id} name={role.name!r}")
        print(f"Temp password: {TEMP_PASSWORD}")
        print()

        existing = s.query(User).filter(User.email.ilike(EMAIL)).first()
        if existing:
            print(f"  SKIP  {EMAIL} — account already exists (id={existing.id})")
            return

        print(f"  CREATE {EMAIL} ({DISPLAY_NAME})")
        if not DRY_RUN:
            user = User(
                email=EMAIL,
                display_name=DISPLAY_NAME,
                password_hash=generate_password_hash(TEMP_PASSWORD),
                is_active=True,
            )
            s.add(user)
            s.flush()
            user.roles.append(role)
            s.commit()
            print(f"  Done. Created {EMAIL} (id={user.id}).")
            print("  Next: run scripts/_init_training_matrix.py --execute to seed her assignments.")
        else:
            print()
            print("DRY RUN — re-run with --execute to apply.")


if __name__ == "__main__":
    main()
