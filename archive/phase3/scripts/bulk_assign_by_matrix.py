"""
Preview training assignments for one user from the parsed training matrix.

Phase 7 (Prompt 15 Task C2). Committed, no prod credentials, DRY_RUN is hardcoded
True — this script only PRINTS the plan. It reads docs/training_matrix_parsed.json
(produced by parse_training_matrix.py) and lists every document required for a given
role, so onboarding a new employee is a one-command preview once their account and
role are known.

Usage:
    python scripts/bulk_assign_by_matrix.py --user-email ethan@silq.tech --role "Dir R&D/Eng [ethan]"
    python scripts/bulk_assign_by_matrix.py --role "CEO [verne]"          # list roles if omitted
    python scripts/bulk_assign_by_matrix.py --list-roles

Wiring to the live database (creating TrainingAssignment rows) is intentionally left
to a credentialed one-off script; this utility is the safe, committed preview step.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX_JSON = ROOT / "docs" / "training_matrix_parsed.json"

DRY_RUN = True  # hardcoded — this utility never writes.


def _load() -> dict:
    if not MATRIX_JSON.exists():
        raise SystemExit(
            f"{MATRIX_JSON.relative_to(ROOT)} not found — run parse_training_matrix.py first."
        )
    return json.loads(MATRIX_JSON.read_text(encoding="utf-8"))


def main():
    ap = argparse.ArgumentParser(description="Preview matrix-driven training for a role.")
    ap.add_argument("--user-email", default=None, help="Target user email (for the printed plan).")
    ap.add_argument("--role", default=None, help='Matrix role label, e.g. "Dir R&D/Eng [ethan]".')
    ap.add_argument("--list-roles", action="store_true", help="List available role labels and exit.")
    args = ap.parse_args()

    data = _load()
    roles = data.get("employees", [])

    if args.list_roles or not args.role:
        print("Available roles:")
        for r in roles:
            print(f"  - {r}")
        if not args.role:
            print("\nPass --role \"<label>\" to preview assignments.")
        return

    if args.role not in roles:
        print(f"Role not found: {args.role!r}")
        print("Available roles: " + ", ".join(roles))
        return

    matched = [a for a in data.get("assignments", []) if args.role in a.get("required_for", [])]

    target = args.user_email or "(unspecified user)"
    print(f"Plan for role {args.role!r} -> user {target}")
    print(f"DRY_RUN = {DRY_RUN} (no writes)\n")
    print(f"{len(matched)} training item(s) required for this role:")
    for a in matched:
        print(f"  + {a['doc_number']:40s} {a['item']}")


if __name__ == "__main__":
    main()
