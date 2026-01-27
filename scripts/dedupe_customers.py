#!/usr/bin/env python
"""
Customer Deduplication Script (P1-1)

Identifies and optionally merges duplicate customer records.
Uses multi-tier matching:
- Strong: Same company_key (first 8 chars) + same state, or same address (city+state+zip)
- Weak: Same email domain (business only)

Usage:
    # List candidates (dry run)
    python scripts/dedupe_customers.py --list
    
    # Merge specific pair
    python scripts/dedupe_customers.py --merge --master=123 --duplicate=456
    
    # Merge all strong matches (requires confirmation)
    python scripts/dedupe_customers.py --merge-strong --confirm

Environment:
    DATABASE_URL: PostgreSQL connection string
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, ".")

from app.eqms.db import Session
from app.eqms.models import User
from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
from app.eqms.modules.customer_profiles.service import (
    find_merge_candidates,
    merge_customers,
    MergeCandidate,
)
from app.eqms.modules.customer_profiles.utils import extract_email_domain


def list_candidates(limit: int = 100) -> None:
    """List potential duplicate customer pairs."""
    with Session() as s:
        candidates = find_merge_candidates(s, limit=limit)
        
        if not candidates:
            print("No duplicate candidates found.")
            return
        
        print(f"Found {len(candidates)} potential duplicate pairs:\n")
        
        strong = [c for c in candidates if c.confidence == 'strong']
        weak = [c for c in candidates if c.confidence == 'weak']
        
        if strong:
            print("=== STRONG MATCHES (recommended for merge) ===")
            for i, c in enumerate(strong, 1):
                print(f"\n{i}. {c.match_reason}")
                print(f"   Customer A (ID {c.customer1.id}): {c.customer1.facility_name}")
                print(f"      Location: {c.customer1.city}, {c.customer1.state} {c.customer1.zip}")
                print(f"   Customer B (ID {c.customer2.id}): {c.customer2.facility_name}")
                print(f"      Location: {c.customer2.city}, {c.customer2.state} {c.customer2.zip}")
        
        if weak:
            print("\n=== WEAK MATCHES (review manually) ===")
            for i, c in enumerate(weak, 1):
                print(f"\n{i}. {c.match_reason}")
                print(f"   Customer A (ID {c.customer1.id}): {c.customer1.facility_name}")
                print(f"   Customer B (ID {c.customer2.id}): {c.customer2.facility_name}")


def merge_pair(master_id: int, duplicate_id: int) -> None:
    """Merge a specific pair of customers."""
    with Session() as s:
        master = s.query(Customer).filter(Customer.id == master_id).one_or_none()
        duplicate = s.query(Customer).filter(Customer.id == duplicate_id).one_or_none()
        
        if not master:
            print(f"ERROR: Master customer (ID {master_id}) not found.")
            return
        if not duplicate:
            print(f"ERROR: Duplicate customer (ID {duplicate_id}) not found.")
            return
        
        print(f"Merging duplicate into master:")
        print(f"  MASTER (ID {master.id}): {master.facility_name}")
        print(f"  DUPLICATE (ID {duplicate.id}): {duplicate.facility_name}")
        
        # Get system user for audit
        system_user = s.query(User).filter(User.email.ilike('%admin%')).first()
        if not system_user:
            system_user = s.query(User).first()
        if not system_user:
            print("ERROR: No user found for audit. Create at least one user.")
            return
        
        result = merge_customers(
            s,
            master_id=master_id,
            duplicate_id=duplicate_id,
            user=system_user,
        )
        
        s.commit()
        print(f"SUCCESS: Merged into {result.facility_name} (ID {result.id})")


def merge_strong_matches(confirm: bool = False) -> None:
    """Merge all strong match candidates."""
    with Session() as s:
        candidates = find_merge_candidates(s, limit=500)
        strong = [c for c in candidates if c.confidence == 'strong']
        
        if not strong:
            print("No strong matches found.")
            return
        
        print(f"Found {len(strong)} strong match pairs to merge.")
        
        if not confirm:
            print("\nRun with --confirm to actually merge these pairs.")
            print("Review the list first with --list")
            return
        
        # Get system user for audit
        system_user = s.query(User).filter(User.email.ilike('%admin%')).first()
        if not system_user:
            system_user = s.query(User).first()
        if not system_user:
            print("ERROR: No user found for audit.")
            return
        
        merged = 0
        for c in strong:
            # Keep the customer with lower ID as master (older record)
            if c.customer1.id < c.customer2.id:
                master_id = c.customer1.id
                duplicate_id = c.customer2.id
            else:
                master_id = c.customer2.id
                duplicate_id = c.customer1.id
            
            try:
                merge_customers(
                    s,
                    master_id=master_id,
                    duplicate_id=duplicate_id,
                    user=system_user,
                )
                merged += 1
                print(f"  Merged: {c.customer2.facility_name} -> {c.customer1.facility_name}")
            except Exception as e:
                print(f"  ERROR merging {duplicate_id}: {e}")
        
        s.commit()
        print(f"\nMerged {merged} duplicate customers.")


def main():
    parser = argparse.ArgumentParser(description="Customer deduplication tool")
    parser.add_argument("--list", action="store_true", help="List duplicate candidates")
    parser.add_argument("--merge", action="store_true", help="Merge a specific pair")
    parser.add_argument("--master", type=int, help="Master customer ID (for --merge)")
    parser.add_argument("--duplicate", type=int, help="Duplicate customer ID (for --merge)")
    parser.add_argument("--merge-strong", action="store_true", help="Merge all strong matches")
    parser.add_argument("--confirm", action="store_true", help="Confirm merge operations")
    parser.add_argument("--limit", type=int, default=100, help="Limit for --list")
    
    args = parser.parse_args()
    
    if args.list:
        list_candidates(limit=args.limit)
    elif args.merge:
        if not args.master or not args.duplicate:
            print("ERROR: --merge requires --master and --duplicate")
            sys.exit(1)
        merge_pair(args.master, args.duplicate)
    elif args.merge_strong:
        merge_strong_matches(confirm=args.confirm)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
