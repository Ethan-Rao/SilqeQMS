#!/usr/bin/env python3
"""
One-time backfill script: Match existing distribution_log_entries to sales_orders by order_number.

Usage:
    python scripts/backfill_sales_order_matching.py --dry-run   # Preview changes
    python scripts/backfill_sales_order_matching.py --execute   # Apply changes

This script:
1. Finds all distributions with sales_order_id IS NULL
2. Matches them to sales_orders by order_number (exact match)
3. Updates distribution_log_entries.sales_order_id

Safe to run multiple times - only updates unmatched entries.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Backfill sales_order_id on distribution_log_entries")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--execute", action="store_true", help="Apply changes")
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("ERROR: Specify --dry-run or --execute")
        print(__doc__)
        sys.exit(1)
    
    # Load Flask app for DB access
    from app.eqms import create_app
    app = create_app()
    
    with app.app_context():
        from app.eqms.db import db_session
        from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
        from sqlalchemy import func
        
        s = db_session()
        
        # Count unmatched distributions
        unmatched_count = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.sales_order_id.is_(None))
            .count()
        )
        print(f"Unmatched distributions: {unmatched_count}")
        
        if unmatched_count == 0:
            print("Nothing to do - all distributions are matched.")
            return
        
        # Build order_number → sales_order_id mapping
        order_map: dict[str, int] = {}
        sales_orders = s.query(SalesOrder).all()
        for so in sales_orders:
            if so.order_number:
                key = so.order_number.strip().upper()
                if key not in order_map:
                    order_map[key] = so.id
        
        print(f"Sales orders available for matching: {len(order_map)}")
        
        # Find matches
        unmatched = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.sales_order_id.is_(None))
            .all()
        )
        
        matched = 0
        unmatched_order_numbers: set[str] = set()
        
        for entry in unmatched:
            if not entry.order_number:
                continue
            key = entry.order_number.strip().upper()
            so_id = order_map.get(key)
            if so_id:
                if args.execute:
                    entry.sales_order_id = so_id
                matched += 1
                print(f"  Match: Distribution #{entry.id} (order {entry.order_number}) -> SalesOrder #{so_id}")
            else:
                unmatched_order_numbers.add(entry.order_number)
        
        if args.execute:
            s.commit()
            print(f"\nCOMMITTED: {matched} distributions matched to sales orders.")
        else:
            print(f"\nDRY RUN: Would match {matched} distributions to sales orders.")
        
        still_unmatched = unmatched_count - matched
        if still_unmatched > 0:
            print(f"\nStill unmatched: {still_unmatched} distributions")
            print(f"Unique unmatched order numbers: {len(unmatched_order_numbers)}")
            if unmatched_order_numbers and len(unmatched_order_numbers) <= 20:
                print("Order numbers with no matching sales order:")
                for on in sorted(unmatched_order_numbers)[:20]:
                    print(f"  - {on}")


if __name__ == "__main__":
    main()
