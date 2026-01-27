#!/usr/bin/env python3
"""
Rebuild customer database from Sales Orders (idempotent).

Sales Orders are the source of truth for customer identity, NOT ShipStation.

This script:
1. For each Sales Order, computes customer_key from ship-to data
2. Finds or creates customer with that key
3. Updates customer fields from SO if more complete
4. Updates sales_orders.customer_id if changed
5. Updates distribution_log_entries.customer_id via linked sales_order
6. Merges duplicate customers (same company_key)

Usage:
    python scripts/rebuild_customers_from_sales_orders.py --dry-run   # Preview
    python scripts/rebuild_customers_from_sales_orders.py --execute   # Apply

Safe to run multiple times - only updates when data is more complete.
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Rebuild customers from Sales Orders")
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
        from app.eqms.modules.customer_profiles.utils import (
            canonical_customer_key,
            compute_customer_key_from_sales_order,
        )
        from app.eqms.modules.rep_traceability.models import SalesOrder, DistributionLogEntry
        
        s = db_session()
        
        # Stats
        customers_created = 0
        customers_updated = 0
        so_customer_links_updated = 0
        dist_customer_links_updated = 0
        duplicates_merged = 0
        
        # Step 1: Build mapping from Sales Orders
        # Group distributions by order_number to get ship-to data
        print("Step 1: Analyzing Sales Orders and Distributions...")
        
        sales_orders = s.query(SalesOrder).all()
        print(f"  Found {len(sales_orders)} Sales Orders")
        
        # For each SO, find linked distributions to get ship-to data
        # (Since SOs may not have ship-to fields, we use distributions)
        key_to_customers: dict[str, list[Customer]] = defaultdict(list)
        
        for so in sales_orders:
            # Get ship-to data from linked distribution (if any)
            dist = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.sales_order_id == so.id)
                .first()
            )
            
            # Build ship-to data dict
            ship_to_data = {}
            
            if dist:
                ship_to_data = {
                    "facility_name": dist.facility_name,
                    "address1": dist.address1,
                    "city": dist.city,
                    "state": dist.state,
                    "zip": dist.zip,
                }
            elif so.customer:
                # Fall back to existing customer data
                ship_to_data = {
                    "facility_name": so.customer.facility_name,
                    "address1": so.customer.address1,
                    "city": so.customer.city,
                    "state": so.customer.state,
                    "zip": so.customer.zip,
                }
            
            if not ship_to_data.get("facility_name"):
                continue
            
            # Compute canonical key
            computed_key = compute_customer_key_from_sales_order(ship_to_data)
            
            if not computed_key or computed_key == "UNKNOWN":
                continue
            
            # Find or create customer with this key
            existing_customer = (
                s.query(Customer)
                .filter(Customer.company_key == computed_key)
                .first()
            )
            
            if existing_customer:
                # Update SO to point to this customer if different
                if so.customer_id != existing_customer.id:
                    if args.execute:
                        so.customer_id = existing_customer.id
                    so_customer_links_updated += 1
                    print(f"  SO #{so.id} ({so.order_number}): customer_id {so.customer_id} -> {existing_customer.id}")
                
                # Update customer fields if distribution has more complete data
                if dist:
                    changes = []
                    if dist.facility_name and (
                        not existing_customer.facility_name or 
                        len(dist.facility_name) > len(existing_customer.facility_name)
                    ):
                        if args.execute:
                            existing_customer.facility_name = dist.facility_name
                        changes.append(f"facility_name: {existing_customer.facility_name!r} -> {dist.facility_name!r}")
                    
                    for field in ["address1", "city", "state", "zip"]:
                        dist_val = getattr(dist, field, None)
                        cust_val = getattr(existing_customer, field, None)
                        if dist_val and not cust_val:
                            if args.execute:
                                setattr(existing_customer, field, dist_val)
                            changes.append(f"{field}: {cust_val!r} -> {dist_val!r}")
                    
                    if changes:
                        customers_updated += 1
                        print(f"  Customer #{existing_customer.id}: {'; '.join(changes)}")
                
                key_to_customers[computed_key].append(existing_customer)
            else:
                # Create new customer
                facility_name = ship_to_data.get("facility_name", "Unknown")
                if args.execute:
                    new_customer = Customer(
                        company_key=computed_key,
                        facility_name=facility_name,
                        address1=ship_to_data.get("address1"),
                        city=ship_to_data.get("city"),
                        state=ship_to_data.get("state"),
                        zip=ship_to_data.get("zip"),
                    )
                    s.add(new_customer)
                    s.flush()
                    so.customer_id = new_customer.id
                    key_to_customers[computed_key].append(new_customer)
                    print(f"  Created customer #{new_customer.id}: {facility_name} (key={computed_key})")
                else:
                    print(f"  Would create customer: {facility_name} (key={computed_key})")
                customers_created += 1
        
        # Step 2: Update distributions linked to SOs
        print("\nStep 2: Updating distribution customer links via Sales Orders...")
        
        for so in sales_orders:
            if not so.customer_id:
                continue
            
            dists = (
                s.query(DistributionLogEntry)
                .filter(
                    DistributionLogEntry.sales_order_id == so.id,
                    DistributionLogEntry.customer_id != so.customer_id
                )
                .all()
            )
            
            for dist in dists:
                if args.execute:
                    dist.customer_id = so.customer_id
                dist_customer_links_updated += 1
                print(f"  Distribution #{dist.id}: customer_id -> {so.customer_id}")
        
        # Step 3: Merge duplicate customers (same company_key)
        print("\nStep 3: Checking for duplicate customers to merge...")
        
        all_customers = s.query(Customer).all()
        key_counts: dict[str, list[Customer]] = defaultdict(list)
        
        for cust in all_customers:
            if cust.company_key:
                key_counts[cust.company_key].append(cust)
        
        for key, custs in key_counts.items():
            if len(custs) > 1:
                # Keep the one with the most linked orders
                custs_with_counts = []
                for c in custs:
                    order_count = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()
                    custs_with_counts.append((c, order_count))
                
                custs_with_counts.sort(key=lambda x: x[1], reverse=True)
                keep_customer = custs_with_counts[0][0]
                merge_customers = [c for c, _ in custs_with_counts[1:]]
                
                for merge_cust in merge_customers:
                    print(f"  Merge customer #{merge_cust.id} into #{keep_customer.id} (key={key})")
                    
                    if args.execute:
                        # Update all references from merge_cust to keep_customer
                        s.query(SalesOrder).filter(SalesOrder.customer_id == merge_cust.id).update(
                            {"customer_id": keep_customer.id}
                        )
                        s.query(DistributionLogEntry).filter(DistributionLogEntry.customer_id == merge_cust.id).update(
                            {"customer_id": keep_customer.id}
                        )
                        # Delete the duplicate
                        s.delete(merge_cust)
                    
                    duplicates_merged += 1
        
        # Commit
        if args.execute:
            s.commit()
            print("\n=== COMMITTED ===")
        else:
            print("\n=== DRY RUN (no changes applied) ===")
        
        print(f"\nSummary:")
        print(f"  Customers created: {customers_created}")
        print(f"  Customers updated: {customers_updated}")
        print(f"  SO customer links updated: {so_customer_links_updated}")
        print(f"  Distribution customer links updated: {dist_customer_links_updated}")
        print(f"  Duplicate customers merged: {duplicates_merged}")


if __name__ == "__main__":
    main()
