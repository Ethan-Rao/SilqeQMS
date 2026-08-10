"""
Create read-only (staff role) accounts for the SILQ team.

Usage:
    python scripts/_create_team_accounts.py           # dry-run
    python scripts/_create_team_accounts.py --execute # commit to DB

Accounts created with a temporary password that Ethan must distribute.
Each user should change their password on first login via the Profile page.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DRY_RUN = "--execute" not in sys.argv

TEAM = [
    {"email": "Brianm@silq.tech",  "display_name": "Brian McVerry"},
    {"email": "Nah@silq.tech",      "display_name": "Na He"},
    {"email": "Christ@silq.tech",   "display_name": "Chris Turner"},
    {"email": "Tomd@silq.tech",     "display_name": "Tom Downey"},
    {"email": "Chuckg@silq.tech",   "display_name": "Chuck Greiner"},
]

TEMP_PASSWORD = "Silq2026!"   # Distribute to team; each user should change on first login.
STAFF_ROLE_KEY = "staff"


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

        staff_role = s.query(Role).filter(Role.key == STAFF_ROLE_KEY).first()
        if not staff_role:
            print(f"ERROR: Role '{STAFF_ROLE_KEY}' not found in DB. Cannot proceed.")
            sys.exit(1)

        print(f"Staff role found: id={staff_role.id} name={staff_role.name!r}")
        print(f"Mode: {'DRY RUN' if DRY_RUN else 'EXECUTE'}")
        print(f"Temp password: {TEMP_PASSWORD}")
        print()

        created = 0
        skipped = 0

        for member in TEAM:
            email = member["email"]
            display_name = member["display_name"]

            existing = s.query(User).filter(
                User.email.ilike(email)
            ).first()

            if existing:
                print(f"  SKIP  {email} — account already exists (id={existing.id})")
                skipped += 1
                continue

            print(f"  CREATE {email} ({display_name})")
            if not DRY_RUN:
                user = User(
                    email=email,
                    display_name=display_name,
                    password_hash=generate_password_hash(TEMP_PASSWORD),
                    is_active=True,
                )
                s.add(user)
                s.flush()  # get user.id before assigning role
                user.roles.append(staff_role)
                s.flush()
            created += 1

        if not DRY_RUN:
            s.commit()
            print()
            print(f"Done. {created} account(s) created, {skipped} skipped.")
            print()
            print("Next steps for Ethan:")
            print(f"  1. Distribute temp password '{TEMP_PASSWORD}' to each team member.")
            print("  2. Each user should log in and change their password via the Profile page.")
            print("  3. Run scripts/_init_training_matrix.py to create initial training assignments.")
        else:
            print()
            print(f"DRY RUN: {created} account(s) would be created, {skipped} would be skipped.")
            print("Re-run with --execute to apply.")


if __name__ == "__main__":
    main()
