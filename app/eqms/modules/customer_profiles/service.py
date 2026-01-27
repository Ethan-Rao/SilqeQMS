"""
CANONICAL CUSTOMER PIPELINE
===========================

Customers are created ONLY from Sales Orders (PDF import, manual SO entry).

Source                  | Creates Customer? | Correct Behavior
------------------------|-------------------|------------------
ShipStation sync        | NO                | Lookup only - creates distribution with customer_id=None
CSV distribution import | NO                | Lookup only - leaves customer_id=None if no match
PDF import              | YES               | Creates customer + SO together (correct)
Manual SO entry         | YES               | Creates customer + SO together (correct)
Manual distribution     | NO                | Uses existing customer_id from dropdown

This ensures the Customer Database only contains entities with verified order history
(at least one Sales Order). Customers without matched SOs violate the canonical pipeline.

INVARIANTS:
- Customer profiles appear in Customer Database ONLY IF they have ≥1 matched Sales Order
- Sales dashboard aggregates ONLY from matched distributions (sales_order_id IS NOT NULL)
- Unmatched distributions don't affect dashboard or customer stats

CLEANUP:
- Zero-order customers can be identified via /admin/maintenance/customers/zero-orders
- Duplicate customers can be identified via /admin/maintenance/customers/duplicates
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.eqms.audit import record_event
from app.eqms.models import User
from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
from app.eqms.modules.customer_profiles.utils import canonical_customer_key, normalize_facility_name, extract_email_domain


def get_customer_by_id(s, customer_id: int) -> Customer | None:
    return s.query(Customer).filter(Customer.id == customer_id).one_or_none()


def find_customer_exact_match(s, facility_name: str) -> Customer | None:
    """
    Tier 1: Exact match by company_key.
    Highest confidence - same normalized facility name.
    """
    ck = canonical_customer_key(facility_name)
    if not ck:
        return None
    return s.query(Customer).filter(Customer.company_key == ck).one_or_none()


def find_customer_strong_match(
    s,
    facility_name: str,
    city: str | None = None,
    state: str | None = None,
    zip_code: str | None = None,
    contact_email: str | None = None,
) -> Customer | None:
    """
    Tier 2: Strong match by address or email domain.
    Medium confidence - same location or organization.
    """
    # First try company_key (exact match)
    c = find_customer_exact_match(s, facility_name)
    if c:
        return c
    
    # Try address match (city + state + zip)
    if city and state and zip_code:
        city_clean = (city or "").strip().upper()
        state_clean = (state or "").strip().upper()
        zip_clean = (zip_code or "").strip()
        if city_clean and state_clean and zip_clean:
            c = (
                s.query(Customer)
                .filter(
                    Customer.city.ilike(city_clean),
                    Customer.state.ilike(state_clean),
                    Customer.zip == zip_clean,
                )
                .first()
            )
            if c:
                return c
    
    # Try email domain match
    if contact_email:
        domain = extract_email_domain(contact_email)
        if domain and domain not in ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'):
            # Only match on business domains, not personal email
            c = (
                s.query(Customer)
                .filter(Customer.contact_email.ilike(f"%@{domain}"))
                .first()
            )
            if c:
                return c
    
    return None


def find_customer_weak_match(s, facility_name: str, state: str | None = None) -> list[Customer]:
    """
    Tier 3: Weak match by fuzzy name + state.
    Low confidence - candidates for manual review.
    Returns up to 10 potential matches.
    """
    ck_base = canonical_customer_key(facility_name)
    if not ck_base or len(ck_base) < 5:
        return []
    
    prefix = ck_base[:5]
    query = s.query(Customer).filter(Customer.company_key.like(f"{prefix}%"))
    
    if state:
        state_clean = (state or "").strip().upper()
        if state_clean:
            query = query.filter(Customer.state.ilike(state_clean))
    
    return query.limit(10).all()


def find_or_create_customer(
    s,
    *,
    facility_name: str,
    address1: str | None = None,
    address2: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip: str | None = None,
    contact_name: str | None = None,
    contact_phone: str | None = None,
    contact_email: str | None = None,
    primary_rep_id: int | None = None,
) -> Customer:
    """
    Enhanced find-or-create with multi-tier matching:
    - Tier 1: Exact match by company_key (normalized facility name)
    - Tier 2: Strong match by address (city+state+zip) or email domain
    - Tier 3: Create new customer (weak matches flagged for review separately)
    """
    facility_name = (facility_name or "").strip()
    if not facility_name:
        raise ValueError("facility_name is required")

    ck = canonical_customer_key(facility_name)
    if not ck:
        raise ValueError("facility_name cannot be normalized to a company_key")

    now = datetime.utcnow()

    # Tier 1: Exact match by company_key
    c = find_customer_exact_match(s, facility_name)
    
    # Tier 2: Strong match by address or email domain
    if not c:
        c = find_customer_strong_match(
            s,
            facility_name=facility_name,
            city=city,
            state=state,
            zip_code=zip,
            contact_email=contact_email,
        )
    
    # If found, update fields and return
    if c:
        changed = False

        def _set(attr: str, val: str | None) -> None:
            nonlocal changed
            v = (val or "").strip() or None
            if v is not None and getattr(c, attr) != v:
                setattr(c, attr, v)
                changed = True

        # Keep facility_name up to date if it changes (but don't overwrite with empty).
        if facility_name and c.facility_name != facility_name:
            c.facility_name = facility_name
            changed = True

        _set("address1", address1)
        _set("address2", address2)
        _set("city", city)
        _set("state", state)
        _set("zip", zip)
        _set("contact_name", contact_name)
        _set("contact_phone", contact_phone)
        _set("contact_email", contact_email)

        if primary_rep_id is not None and c.primary_rep_id != primary_rep_id:
            c.primary_rep_id = primary_rep_id
            changed = True

        if changed:
            c.updated_at = now
        return c

    # Tier 3: No match found - create new customer
    # Note: Weak matches are NOT auto-merged here; they can be flagged separately
    # 
    # Race Condition Fix: Use nested transaction with retry logic
    # Another process may create the same customer between our lookup and insert
    from sqlalchemy.exc import IntegrityError
    
    try:
        with s.begin_nested():  # SAVEPOINT for idempotency
            c = Customer(
                company_key=ck,
                facility_name=facility_name,
                address1=(address1 or "").strip() or None,
                address2=(address2 or "").strip() or None,
                city=(city or "").strip() or None,
                state=(state or "").strip() or None,
                zip=(zip or "").strip() or None,
                contact_name=(contact_name or "").strip() or None,
                contact_phone=(contact_phone or "").strip() or None,
                contact_email=(contact_email or "").strip() or None,
                primary_rep_id=primary_rep_id,
                updated_at=now,
            )
            s.add(c)
            s.flush()  # Force unique constraint check
        return c
    except IntegrityError:
        # Race condition: another process created the customer
        # Rollback nested transaction and retry lookup
        # The nested transaction (SAVEPOINT) handles the rollback automatically
        c = find_customer_exact_match(s, facility_name)
        if c:
            return c
        # Still not found - this is unexpected, re-raise
        raise


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str


def validate_customer_payload(payload: dict[str, Any]) -> list[ValidationError]:
    errs: list[ValidationError] = []
    if not (payload.get("facility_name") or "").strip():
        errs.append(ValidationError("facility_name", "Facility name is required."))
    rep_id = (payload.get("primary_rep_id") or "").strip()
    if rep_id:
        try:
            int(rep_id)
        except Exception:
            errs.append(ValidationError("primary_rep_id", "Primary rep id must be a number."))
    return errs


def create_customer(s, payload: dict[str, Any], *, user: User) -> Customer:
    c = find_or_create_customer(
        s,
        facility_name=str(payload.get("facility_name") or ""),
        address1=payload.get("address1"),
        address2=payload.get("address2"),
        city=payload.get("city"),
        state=payload.get("state"),
        zip=payload.get("zip"),
        contact_name=payload.get("contact_name"),
        contact_phone=payload.get("contact_phone"),
        contact_email=payload.get("contact_email"),
        primary_rep_id=int(payload["primary_rep_id"]) if (payload.get("primary_rep_id") or "").strip() else None,
    )
    record_event(
        s,
        actor=user,
        action="customer.create",
        entity_type="Customer",
        entity_id=str(c.id),
        metadata={"company_key": c.company_key, "facility_name": c.facility_name},
    )
    return c


def update_customer(s, c: Customer, payload: dict[str, Any], *, user: User, reason: str) -> Customer:
    before = {
        "facility_name": c.facility_name,
        "address1": c.address1,
        "address2": c.address2,
        "city": c.city,
        "state": c.state,
        "zip": c.zip,
        "contact_name": c.contact_name,
        "contact_phone": c.contact_phone,
        "contact_email": c.contact_email,
        "primary_rep_id": c.primary_rep_id,
    }

    c.facility_name = (payload.get("facility_name") or "").strip()
    c.address1 = (payload.get("address1") or "").strip() or None
    c.address2 = (payload.get("address2") or "").strip() or None
    c.city = (payload.get("city") or "").strip() or None
    c.state = (payload.get("state") or "").strip() or None
    c.zip = (payload.get("zip") or "").strip() or None
    c.contact_name = (payload.get("contact_name") or "").strip() or None
    c.contact_phone = (payload.get("contact_phone") or "").strip() or None
    c.contact_email = (payload.get("contact_email") or "").strip() or None
    c.primary_rep_id = int(payload["primary_rep_id"]) if (payload.get("primary_rep_id") or "").strip() else None
    c.updated_at = datetime.utcnow()

    after = {
        "facility_name": c.facility_name,
        "address1": c.address1,
        "address2": c.address2,
        "city": c.city,
        "state": c.state,
        "zip": c.zip,
        "contact_name": c.contact_name,
        "contact_phone": c.contact_phone,
        "contact_email": c.contact_email,
        "primary_rep_id": c.primary_rep_id,
    }
    fields_changed = [k for k in before.keys() if before[k] != after[k]]
    record_event(
        s,
        actor=user,
        action="customer.update",
        entity_type="Customer",
        entity_id=str(c.id),
        reason=reason,
        metadata={"before": before, "after": after, "fields_changed": fields_changed},
    )
    return c


def add_customer_note(s, customer: Customer, *, note_text: str, note_date: str | None, user: User) -> CustomerNote:
    text = (note_text or "").strip()
    if not text:
        raise ValueError("Note text is required.")
    d: date | None = None
    if (note_date or "").strip():
        d = date.fromisoformat(str(note_date))
    n = CustomerNote(
        customer_id=customer.id,
        note_text=text,
        note_date=d or date.today(),
        author=user.email,
        updated_at=datetime.utcnow(),
    )
    s.add(n)
    s.flush()
    record_event(
        s,
        actor=user,
        action="customer_note.create",
        entity_type="CustomerNote",
        entity_id=str(n.id),
        metadata={"customer_id": customer.id},
    )
    return n


def edit_customer_note(s, note: CustomerNote, *, note_text: str, user: User) -> CustomerNote:
    text = (note_text or "").strip()
    if not text:
        raise ValueError("Note text is required.")
    before = {"note_text": note.note_text}
    note.note_text = text
    note.updated_at = datetime.utcnow()
    record_event(
        s,
        actor=user,
        action="customer_note.update",
        entity_type="CustomerNote",
        entity_id=str(note.id),
        metadata={"before": before, "after": {"note_text": note.note_text}, "customer_id": note.customer_id},
    )
    return note


def delete_customer_note(s, note: CustomerNote, *, user: User) -> None:
    record_event(
        s,
        actor=user,
        action="customer_note.delete",
        entity_type="CustomerNote",
        entity_id=str(note.id),
        metadata={"customer_id": note.customer_id},
    )
    s.delete(note)


# ============================================================================
# Customer Merge Functions
# ============================================================================

@dataclass(frozen=True)
class MergeCandidate:
    """Represents two customers that may be duplicates."""
    customer1: Customer
    customer2: Customer
    confidence: str  # 'strong' or 'weak'
    match_reason: str


def find_merge_candidates(s, *, limit: int = 100) -> list[MergeCandidate]:
    """
    Find potential duplicate customers.
    
    Returns candidates sorted by confidence (strong first).
    """
    candidates: list[MergeCandidate] = []
    seen_pairs: set[tuple[int, int]] = set()
    
    # Get all customers
    all_customers = s.query(Customer).order_by(Customer.id.asc()).all()
    
    for i, c1 in enumerate(all_customers):
        for c2 in all_customers[i + 1:]:
            if (c1.id, c2.id) in seen_pairs or (c2.id, c1.id) in seen_pairs:
                continue
            
            # Check for exact company_key match (strong - shouldn't happen due to unique constraint)
            if c1.company_key and c1.company_key == c2.company_key:
                candidates.append(MergeCandidate(c1, c2, 'strong', 'exact_company_key'))
                seen_pairs.add((c1.id, c2.id))
                continue
            
            # Check for similar company_key (first 8 chars match + same state)
            if (c1.company_key and c2.company_key 
                and len(c1.company_key) >= 8 and len(c2.company_key) >= 8
                and c1.company_key[:8] == c2.company_key[:8]):
                if c1.state and c2.state and c1.state.upper() == c2.state.upper():
                    candidates.append(MergeCandidate(c1, c2, 'strong', 'similar_name_same_state'))
                    seen_pairs.add((c1.id, c2.id))
                    continue
                else:
                    candidates.append(MergeCandidate(c1, c2, 'weak', 'similar_name'))
                    seen_pairs.add((c1.id, c2.id))
                    continue
            
            # Check for same address (city + state + zip)
            if (c1.city and c2.city and c1.state and c2.state and c1.zip and c2.zip
                and c1.city.upper() == c2.city.upper()
                and c1.state.upper() == c2.state.upper()
                and c1.zip == c2.zip):
                candidates.append(MergeCandidate(c1, c2, 'strong', 'same_address'))
                seen_pairs.add((c1.id, c2.id))
                continue
            
            # Check for same email domain (business domains only)
            if c1.contact_email and c2.contact_email:
                domain1 = extract_email_domain(c1.contact_email)
                domain2 = extract_email_domain(c2.contact_email)
                personal_domains = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'}
                if (domain1 and domain2 and domain1 == domain2 
                    and domain1 not in personal_domains):
                    candidates.append(MergeCandidate(c1, c2, 'weak', f'same_email_domain:{domain1}'))
                    seen_pairs.add((c1.id, c2.id))
                    continue
            
            if len(candidates) >= limit:
                break
        if len(candidates) >= limit:
            break
    
    # Sort by confidence (strong first)
    candidates.sort(key=lambda c: (0 if c.confidence == 'strong' else 1, c.customer1.id))
    return candidates[:limit]


def merge_customers(
    s,
    *,
    master_id: int,
    duplicate_id: int,
    user: User,
) -> Customer:
    """
    Merge duplicate customer into master.
    
    Updates all references (distributions, notes, sales orders) from duplicate to master.
    Merges non-null fields from duplicate into master if master has null.
    Deletes the duplicate customer.
    """
    master = s.query(Customer).filter(Customer.id == master_id).one()
    duplicate = s.query(Customer).filter(Customer.id == duplicate_id).one()
    
    # Store duplicate data for audit
    duplicate_data = {
        "id": duplicate.id,
        "facility_name": duplicate.facility_name,
        "company_key": duplicate.company_key,
        "address1": duplicate.address1,
        "city": duplicate.city,
        "state": duplicate.state,
        "zip": duplicate.zip,
        "contact_email": duplicate.contact_email,
    }
    
    # Update all distribution_log_entries references
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
    
    dist_count = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.customer_id == duplicate_id)
        .update({"customer_id": master_id})
    )
    
    # Update all customer_notes references
    notes_count = (
        s.query(CustomerNote)
        .filter(CustomerNote.customer_id == duplicate_id)
        .update({"customer_id": master_id})
    )
    
    # Update all sales_orders references
    orders_count = (
        s.query(SalesOrder)
        .filter(SalesOrder.customer_id == duplicate_id)
        .update({"customer_id": master_id})
    )
    
    # Merge fields (keep non-null from duplicate if master is null)
    fields_merged = []
    for field in ['address1', 'address2', 'city', 'state', 'zip', 
                  'contact_name', 'contact_phone', 'contact_email']:
        master_val = getattr(master, field)
        duplicate_val = getattr(duplicate, field)
        if not master_val and duplicate_val:
            setattr(master, field, duplicate_val)
            fields_merged.append(field)
    
    master.updated_at = datetime.utcnow()
    
    # Delete duplicate
    s.delete(duplicate)
    
    # Audit event
    record_event(
        s,
        actor=user,
        action="customer.merge",
        entity_type="Customer",
        entity_id=str(master_id),
        metadata={
            "merged_customer_id": duplicate_id,
            "merged_facility_name": duplicate_data["facility_name"],
            "merged_company_key": duplicate_data["company_key"],
            "distributions_updated": dist_count,
            "notes_updated": notes_count,
            "orders_updated": orders_count,
            "fields_merged": fields_merged,
        },
    )
    
    return master

