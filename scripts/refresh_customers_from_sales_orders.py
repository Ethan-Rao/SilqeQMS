#!/usr/bin/env python3
"""
Refresh customer data from linked sales orders (idempotent).

Uses sales order ship-to as source of truth for facility_name, address fields.
Only updates customer fields when sales order data is more complete/normalized.

Usage:
    python scripts/refresh_customers_from_sales_orders.py --dry-run   # Preview
    python scripts/refresh_customers_from_sales_orders.py --execute   # Apply

Safe to run multiple times - only updates when sales order data is more complete.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Refresh customer data from linked sales orders")
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
        from app.eqms.modules.customer_profiles.models import Customer
        from app.eqms.modules.rep_traceability.models import SalesOrder, DistributionLogEntry
        from sqlalchemy import func
        
        s = db_session()
        
        customers = s.query(Customer).all()
        print(f"Total customers: {len(customers)}")
        
        updated_count = 0
        skipped_count = 0
        
        for customer in customers:
            # Get most recent sales order for this customer (PDF or manual preferred)
            latest_order = (
                s.query(SalesOrder)
                .filter(SalesOrder.customer_id == customer.id)
                .filter(SalesOrder.source.in_(["pdf_import", "manual"]))  # Prefer canonical sources
                .order_by(SalesOrder.order_date.desc())
                .first()
            )
            
            if not latest_order:
                # Fall back to any sales order
                latest_order = (
                    s.query(SalesOrder)
                    .filter(SalesOrder.customer_id == customer.id)
                    .order_by(SalesOrder.order_date.desc())
                    .first()
                )
            
            if not latest_order:
                # No sales orders, try distributions with this customer
                latest_dist = (
                    s.query(DistributionLogEntry)
                    .filter(DistributionLogEntry.customer_id == customer.id)
                    .filter(DistributionLogEntry.source.in_(["pdf_import", "manual", "csv_import"]))
                    .order_by(DistributionLogEntry.ship_date.desc())
                    .first()
                )
                
                if latest_dist and latest_dist.facility_name:
                    # Use distribution data
                    changes = []
                    if latest_dist.facility_name and (
                        not customer.facility_name or 
                        len(latest_dist.facility_name) > len(customer.facility_name)
                    ):
                        if args.execute:
                            customer.facility_name = latest_dist.facility_name
                        changes.append(f"facility_name: {customer.facility_name!r} -> {latest_dist.facility_name!r}")
                    
                    if changes:
                        print(f"  Customer #{customer.id} ({customer.facility_name}): {'; '.join(changes)}")
                        updated_count += 1
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1
                continue
            
            # Update customer fields from sales order distributions (which have ship-to)
            # Sales orders themselves don't store ship-to directly, but distributions do
            order_dists = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.sales_order_id == latest_order.id)
                .first()
            )
            
            changes = []
            
            # Check if we should update facility_name
            if order_dists and order_dists.facility_name:
                dist_name = order_dists.facility_name.strip()
                curr_name = (customer.facility_name or "").strip()
                
                # Update if distribution name is longer (more complete) or properly cased
                if dist_name and (
                    not curr_name or
                    len(dist_name) > len(curr_name) or
                    (dist_name != dist_name.upper() and curr_name == curr_name.upper())  # Prefer mixed case over ALL CAPS
                ):
                    if args.execute:
                        customer.facility_name = dist_name
                    changes.append(f"facility_name: {curr_name!r} -> {dist_name!r}")
            
            # Check address fields
            if order_dists:
                for field in ["address1", "city", "state", "zip"]:
                    dist_val = getattr(order_dists, field, None)
                    curr_val = getattr(customer, field, None)
                    
                    if dist_val and not curr_val:
                        if args.execute:
                            setattr(customer, field, dist_val)
                        changes.append(f"{field}: {curr_val!r} -> {dist_val!r}")
            
            if changes:
                print(f"  Customer #{customer.id} ({customer.facility_name}): {'; '.join(changes)}")
                updated_count += 1
            else:
                skipped_count += 1
        
        if args.execute:
            s.commit()
            print(f"\nCOMMITTED: {updated_count} customers updated from sales orders.")
        else:
            print(f"\nDRY RUN: Would update {updated_count} customers from sales orders.")
        
        print(f"Skipped (no changes needed): {skipped_count}")


if __name__ == "__main__":
    main()
