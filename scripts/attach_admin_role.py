#!/usr/bin/env python3
"""Attach admin role to a user (idempotent).

Usage:
  python scripts/attach_admin_role.py --email ethanr@silq.tech
"""

import sys
import os
import argparse
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.eqms.models import User, Role


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="User email to attach admin role")
    args = parser.parse_args()

    db_url = (os.environ.get("DATABASE_URL") or "sqlite:///eqms.db").strip()
    engine = create_engine(db_url, future=True)
    sm = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    s: Session = sm()
    try:
        user = s.query(User).filter(User.email.ilike(args.email)).one_or_none()
        if not user:
            print(f"User not found: {args.email}")
            return
        role = s.query(Role).filter(Role.key == "admin").one_or_none()
        if not role:
            print("Admin role not found. Run python scripts/init_db.py first.")
            return
        if role in (user.roles or []):
            print(f"User already has admin role: {args.email}")
            return
        user.roles.append(role)
        s.commit()
        print(f"Admin role attached to {args.email}")
    finally:
        s.close()


if __name__ == "__main__":
    main()
