#!/usr/bin/env python3
"""Delete customers with 0 orders (safe deletion).

This script finds customers with no associated distribution_log_entries AND no sales_orders,
and optionally deletes them after confirmation.

Usage:
    python scripts/cleanup_zero_order_customers.py           # Interactive mode
    python scripts/cleanup_zero_order_customers.py --dry-run # Preview only
    python scripts/cleanup_zero_order_customers.py --yes     # Delete without confirmation
"""

import sys
from pathlib import Path
import os
import argparse

# Ensure repo root is on sys.path when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager

from app.eqms.models import User
from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
from app.eqms.audit import record_event


@contextmanager
def _session_scope(database_url: str):
    engine = create_engine(database_url, future=True)
    sm = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    s: Session = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def find_zero_order_customers(s: Session) -> list[Customer]:
    """Find customers with 0 orders and 0 distributions."""
    # Subquery for distribution counts
    dist_count_subq = (
        s.query(DistributionLogEntry.customer_id, func.count(DistributionLogEntry.id).label("dist_count"))
        .group_by(DistributionLogEntry.customer_id)
        .subquery()
    )
    
    # Subquery for sales order counts
    order_count_subq = (
        s.query(SalesOrder.customer_id, func.count(SalesOrder.id).label("order_count"))
        .group_by(SalesOrder.customer_id)
        .subquery()
    )
    
    # Find customers with 0 in both
    zero_order_customers = (
        s.query(Customer)
        .outerjoin(dist_count_subq, Customer.id == dist_count_subq.c.customer_id)
        .outerjoin(order_count_subq, Customer.id == order_count_subq.c.customer_id)
        .filter(
            (dist_count_subq.c.dist_count == None) | (dist_count_subq.c.dist_count == 0),
            (order_count_subq.c.order_count == None) | (order_count_subq.c.order_count == 0)
        )
        .order_by(Customer.facility_name)
        .all()
    )
    
    return zero_order_customers


def delete_customers(s: Session, customers: list[Customer], admin_user: User) -> int:
    """Delete customers and record audit events."""
    deleted_count = 0
    
    for customer in customers:
        # Delete associated notes first (should cascade, but be explicit)
        s.query(CustomerNote).filter(CustomerNote.customer_id == customer.id).delete()
        
        # Record audit event
        record_event(
            s,
            actor=admin_user,
            action="customer.delete_zero_orders",
            entity_type="Customer",
            entity_id=str(customer.id),
            metadata={
                "facility_name": customer.facility_name,
                "company_key": customer.company_key,
                "reason": "Zero orders cleanup",
            },
        )
        
        # Delete customer
        s.delete(customer)
        deleted_count += 1
    
    return deleted_count


def main():
    parser = argparse.ArgumentParser(description="Delete customers with 0 orders")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't delete")
    parser.add_argument("--yes", "-y", action="store_true", help="Delete without confirmation")
    args = parser.parse_args()
    
    db_url = (os.environ.get("DATABASE_URL") or "sqlite:///eqms.db").strip()
    admin_email = (os.environ.get("ADMIN_EMAIL") or "admin@silqeqms.com").strip().lower()
    
    print(f"Database: {db_url[:50]}...")
    print(f"Admin email: {admin_email}")
    print()
    
    with _session_scope(db_url) as s:
        # Find admin user
        admin_user = s.query(User).filter(User.email == admin_email).one_or_none()
        if not admin_user:
            print(f"ERROR: Admin user {admin_email} not found")
            sys.exit(1)
        
        # Find zero-order customers
        zero_order_customers = find_zero_order_customers(s)
        
        if not zero_order_customers:
            print("✓ No zero-order customers found. Database is clean.")
            return
        
        print(f"Found {len(zero_order_customers)} zero-order customers:")
        print("-" * 60)
        for i, c in enumerate(zero_order_customers[:50], 1):  # Show first 50
            print(f"  {i:3}. {c.facility_name[:50]:<50} (ID: {c.id})")
        
        if len(zero_order_customers) > 50:
            print(f"  ... and {len(zero_order_customers) - 50} more")
        
        print("-" * 60)
        
        if args.dry_run:
            print("\n[DRY RUN] No changes made.")
            return
        
        # Confirm deletion
        if not args.yes:
            response = input(f"\nDelete these {len(zero_order_customers)} customers? (yes/no): ")
            if response.lower() != "yes":
                print("Cancelled.")
                return
        
        # Delete customers
        deleted_count = delete_customers(s, zero_order_customers, admin_user)
        print(f"\n✓ Deleted {deleted_count} customers.")


if __name__ == "__main__":
    main()
