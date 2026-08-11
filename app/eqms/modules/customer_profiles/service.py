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
from app.eqms.modules.customer_profiles.models import Customer, CustomerNote, CustomerRep
from app.eqms.modules.customer_profiles.utils import (
    canonical_customer_key,
    compute_facility_key_from_ship_to,
    extract_email_domain,
    facility_display_name,
    is_person_shaped_customer_name,
    names_likely_same_company,
    preferred_company_display_name,
    normalize_facility_name,
)
from app.eqms.utils import utcnow


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
    Tier 2: Strong match by company_key only.

    Previously this also matched by city+state+zip and email domain, but those
    heuristics were too aggressive and caused distinct customers to be merged
    (e.g., two different hospitals in the same zip code).

    Customer grouping is now driven by:
      - Priority 0: customer_code (from Sales Order PDF)
      - Tier 1/2: Exact company_key (normalized facility name)
    """
    # Exact company_key match
    c = find_customer_exact_match(s, facility_name)
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
    customer_code: str | None = None,
    address1: str | None = None,
    address2: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip: str | None = None,
    contact_name: str | None = None,
    contact_phone: str | None = None,
    contact_email: str | None = None,
    primary_rep_id: int | None = None,
    sold_to_address1: str | None = None,
    sold_to_city: str | None = None,
    sold_to_state: str | None = None,
    sold_to_zip: str | None = None,
    identity: str = "company",
    customer_type: str | None = None,
) -> Customer:
    """
    Find-or-create customer.

    identity:
      - ``company`` (default, NRE / Sold-To): match by customer_code then
        name-based ``company_key`` (legacy).
      - ``facility`` (catheter Ship-To): match by Ship-To address key
        ``{normalized_street}|{STATE}|{ZIP5}`` (suite/abbrev/word-order
        collapsed; city ignored when zip present). Does **not** match solely
        by payer ``customer_code`` (avoids collapsing Marathon sites).

    Address convention:
      address1/city/state/zip       = Ship To (physical delivery location)
      sold_to_address1/city/state/zip = Sold To (billing address from PDF)
    """
    facility_name = (facility_name or "").strip()
    if not facility_name:
        raise ValueError("facility_name is required")

    identity = (identity or "company").strip().lower()
    if identity not in ("company", "facility"):
        identity = "company"

    if identity == "facility":
        ck = compute_facility_key_from_ship_to(
            address1=address1,
            city=city,
            state=state,
            zip=zip,
            facility_name=facility_name,
        )
    else:
        ck = canonical_customer_key(facility_name)
    if not ck:
        raise ValueError("facility_name cannot be normalized to a company_key")

    now = utcnow()
    customer_code_clean = (customer_code or "").strip().upper() or None
    c = None

    if identity == "facility":
        # Match by Ship-To facility key only (never payer code alone).
        c = s.query(Customer).filter(Customer.company_key == ck).one_or_none()
    else:
        # Priority 0: Match by customer_code if provided
        if customer_code_clean:
            c = s.query(Customer).filter(Customer.customer_code == customer_code_clean).one_or_none()
        # Tier 1: Exact match by company_key
        if not c:
            c = find_customer_exact_match(s, facility_name)

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

        # Ship To address (primary address fields)
        _set("address1", address1)
        _set("address2", address2)
        _set("city", city)
        _set("state", state)
        _set("zip", zip)

        # Sold To address (billing address)
        _set("sold_to_address1", sold_to_address1)
        _set("sold_to_city", sold_to_city)
        _set("sold_to_state", sold_to_state)
        _set("sold_to_zip", sold_to_zip)

        _set("contact_name", contact_name)
        _set("contact_phone", contact_phone)
        _set("contact_email", contact_email)
        if identity != "facility":
            _set("customer_code", customer_code_clean)
        elif customer_code_clean and not c.customer_code:
            c.customer_code = customer_code_clean
            changed = True

        if primary_rep_id is not None and c.primary_rep_id != primary_rep_id:
            c.primary_rep_id = primary_rep_id
            changed = True

        if customer_type and c.customer_type != customer_type and c.customer_type == "auto":
            c.customer_type = customer_type
            changed = True

        if changed:
            c.updated_at = now
        return c

    # No match found - create new customer
    # Race Condition Fix: Use nested transaction with retry logic
    from sqlalchemy.exc import IntegrityError

    create_type = customer_type if customer_type in ("auto", "catheter", "nre") else "auto"
    try:
        with s.begin_nested():  # SAVEPOINT for idempotency
            c = Customer(
                customer_code=customer_code_clean,
                company_key=ck,
                facility_name=facility_name,
                customer_type=create_type,
                address1=(address1 or "").strip() or None,
                address2=(address2 or "").strip() or None,
                city=(city or "").strip() or None,
                state=(state or "").strip() or None,
                zip=(zip or "").strip() or None,
                sold_to_address1=(sold_to_address1 or "").strip() or None,
                sold_to_city=(sold_to_city or "").strip() or None,
                sold_to_state=(sold_to_state or "").strip() or None,
                sold_to_zip=(sold_to_zip or "").strip() or None,
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
        c = s.query(Customer).filter(Customer.company_key == ck).one_or_none()
        if c:
            return c
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
        sold_to_address1=payload.get("sold_to_address1"),
        sold_to_city=payload.get("sold_to_city"),
        sold_to_state=payload.get("sold_to_state"),
        sold_to_zip=payload.get("sold_to_zip"),
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
        "sold_to_address1": c.sold_to_address1,
        "sold_to_city": c.sold_to_city,
        "sold_to_state": c.sold_to_state,
        "sold_to_zip": c.sold_to_zip,
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
    c.sold_to_address1 = (payload.get("sold_to_address1") or "").strip() or None
    c.sold_to_city = (payload.get("sold_to_city") or "").strip() or None
    c.sold_to_state = (payload.get("sold_to_state") or "").strip() or None
    c.sold_to_zip = (payload.get("sold_to_zip") or "").strip() or None
    c.contact_name = (payload.get("contact_name") or "").strip() or None
    c.contact_phone = (payload.get("contact_phone") or "").strip() or None
    c.contact_email = (payload.get("contact_email") or "").strip() or None
    c.primary_rep_id = int(payload["primary_rep_id"]) if (payload.get("primary_rep_id") or "").strip() else None
    c.updated_at = utcnow()

    after = {
        "facility_name": c.facility_name,
        "address1": c.address1,
        "address2": c.address2,
        "city": c.city,
        "state": c.state,
        "zip": c.zip,
        "sold_to_address1": c.sold_to_address1,
        "sold_to_city": c.sold_to_city,
        "sold_to_state": c.sold_to_state,
        "sold_to_zip": c.sold_to_zip,
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
        updated_at=utcnow(),
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
    note.updated_at = utcnow()
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
                  'sold_to_address1', 'sold_to_city', 'sold_to_state', 'sold_to_zip',
                  'contact_name', 'contact_phone', 'contact_email']:
        master_val = getattr(master, field)
        duplicate_val = getattr(duplicate, field)
        if not master_val and duplicate_val:
            setattr(master, field, duplicate_val)
            fields_merged.append(field)
    
    master.updated_at = utcnow()
    
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


@dataclass
class RekeyPreview:
    source_id: int
    source_name: str
    source_key: str
    proposed_key: str
    surviving_name: str
    customer_type: str
    merge_target_id: int | None
    merge_target_name: str | None
    survivor_id: int
    loser_id: int | None
    sales_orders: int
    distributions: int
    notes: int
    rep_assignments: int


def _linked_record_count(s, customer_id: int) -> int:
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder

    so_n = s.query(SalesOrder).filter(SalesOrder.customer_id == customer_id).count()
    dist_n = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.customer_id == customer_id)
        .count()
    )
    return so_n + dist_n


def _move_counts(s, customer_id: int) -> dict[str, int]:
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder

    return {
        "sales_orders": s.query(SalesOrder).filter(SalesOrder.customer_id == customer_id).count(),
        "distributions": (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.customer_id == customer_id)
            .count()
        ),
        "notes": s.query(CustomerNote).filter(CustomerNote.customer_id == customer_id).count(),
        "rep_assignments": (
            s.query(CustomerRep).filter(CustomerRep.customer_id == customer_id).count()
        ),
    }


def find_company_merge_target(s, *, source: Customer, proposed_key: str, proposed_name: str):
    """Find an existing customer that already owns this company identity."""
    # Exact key holder (not self).
    hit = (
        s.query(Customer)
        .filter(Customer.company_key == proposed_key, Customer.id != source.id)
        .one_or_none()
    )
    if hit:
        return hit

    # Best-guess: another row whose name maps to the same company (incl. AB / Advanced Bionics).
    for other in s.query(Customer).filter(Customer.id != source.id).all():
        if names_likely_same_company(proposed_name, other.facility_name):
            return other
        if other.company_key == proposed_key:
            return other
    return None


def preview_rekey_to_company(
    s,
    customer_id: int,
    *,
    surviving_name: str | None = None,
) -> RekeyPreview:
    """Preview converting a customer to company-level NRE identity (optional merge)."""
    source = s.query(Customer).filter(Customer.id == customer_id).one()
    chosen_name = (surviving_name or "").strip() or source.facility_name
    proposed_key = canonical_customer_key(chosen_name)
    if not proposed_key:
        raise ValueError("Surviving name cannot be normalized to a company key.")

    target = find_company_merge_target(
        s, source=source, proposed_key=proposed_key, proposed_name=chosen_name
    )

    if target is None:
        survivor_id = source.id
        loser_id = None
        display = chosen_name
        move_orders = 0
        move_dists = 0
        move_notes = 0
        move_reps = 0
    else:
        src_score = _linked_record_count(s, source.id)
        tgt_score = _linked_record_count(s, target.id)
        if src_score > tgt_score or (src_score == tgt_score and source.id < target.id):
            survivor, loser = source, target
        else:
            survivor, loser = target, source
        display = preferred_company_display_name(
            chosen_name, survivor.facility_name, loser.facility_name
        )
        if (surviving_name or "").strip():
            display = (surviving_name or "").strip()
        proposed_key = canonical_customer_key(display)
        survivor_id = survivor.id
        loser_id = loser.id
        loser_counts = _move_counts(s, loser.id)
        move_orders = loser_counts["sales_orders"]
        move_dists = loser_counts["distributions"]
        move_notes = loser_counts["notes"]
        move_reps = loser_counts["rep_assignments"]

    return RekeyPreview(
        source_id=source.id,
        source_name=source.facility_name,
        source_key=source.company_key,
        proposed_key=proposed_key,
        surviving_name=display,
        customer_type="nre",
        merge_target_id=target.id if target else None,
        merge_target_name=target.facility_name if target else None,
        survivor_id=survivor_id,
        loser_id=loser_id,
        sales_orders=move_orders,
        distributions=move_dists,
        notes=move_notes,
        rep_assignments=move_reps,
    )


def apply_rekey_to_company(
    s,
    customer_id: int,
    *,
    surviving_name: str,
    user: User | None,
) -> Customer:
    """Re-key a customer to company identity; merge into key holder when present.

    Order: move FKs from loser → survivor, release loser key, set survivor key/type/name,
    delete loser. Notes and rep assignments move before delete (CASCADE would destroy them).
    """
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder

    preview = preview_rekey_to_company(s, customer_id, surviving_name=surviving_name)
    display = (surviving_name or "").strip() or preview.surviving_name
    after_key = canonical_customer_key(display)
    if not after_key:
        raise ValueError("Surviving name cannot be normalized to a company key.")

    survivor = s.get(Customer, preview.survivor_id)
    if not survivor:
        raise ValueError("Survivor customer not found.")

    before_survivor_key = survivor.company_key
    before_survivor_name = survivor.facility_name
    loser = s.get(Customer, preview.loser_id) if preview.loser_id else None
    before_loser_key = loser.company_key if loser else None
    before_loser_name = loser.facility_name if loser else None
    before_source_key = preview.source_key
    before_source_name = preview.source_name

    moved = {"sales_orders": 0, "distributions": 0, "notes": 0, "rep_assignments": 0}

    if loser is not None:
        # 1. Repoint sales orders
        moved["sales_orders"] = (
            s.query(SalesOrder)
            .filter(SalesOrder.customer_id == loser.id)
            .update({"customer_id": survivor.id}, synchronize_session="fetch")
        )
        # 2. Repoint distributions explicitly (do not rely on SET NULL)
        moved["distributions"] = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.customer_id == loser.id)
            .update(
                {
                    "customer_id": survivor.id,
                    "facility_name": display,
                },
                synchronize_session="fetch",
            )
        )
        # 3. Move notes before delete (CASCADE would destroy them)
        moved["notes"] = (
            s.query(CustomerNote)
            .filter(CustomerNote.customer_id == loser.id)
            .update({"customer_id": survivor.id}, synchronize_session="fetch")
        )
        # 4. Move rep assignments with de-dupe
        survivor_rep_ids = {
            r.rep_id
            for r in s.query(CustomerRep).filter(CustomerRep.customer_id == survivor.id).all()
        }
        loser_rep_rows = (
            s.query(CustomerRep).filter(CustomerRep.customer_id == loser.id).all()
        )
        drop_ids = [cr.id for cr in loser_rep_rows if cr.rep_id in survivor_rep_ids]
        if drop_ids:
            (
                s.query(CustomerRep)
                .filter(CustomerRep.id.in_(drop_ids))
                .delete(synchronize_session=False)
            )
        moved["rep_assignments"] = (
            s.query(CustomerRep)
            .filter(CustomerRep.customer_id == loser.id)
            .update({"customer_id": survivor.id}, synchronize_session="fetch")
        )
        s.flush()
        # Drop in-memory collections so deleting loser cannot CASCADE-orphan moved rows.
        s.expire(loser)

        # Release loser's unique company_key before assigning survivor (no transient dup).
        loser.company_key = f"__deleted_{loser.id}__"
        s.flush()

    # If survivor already holds after_key, fine; else set it (may need to clear collision).
    if survivor.company_key != after_key:
        collision = (
            s.query(Customer)
            .filter(Customer.company_key == after_key, Customer.id != survivor.id)
            .one_or_none()
        )
        if collision is not None:
            raise ValueError(
                f"Cannot set company_key={after_key!r}: held by customer id={collision.id}."
            )
        survivor.company_key = after_key

    survivor.facility_name = display
    survivor.customer_type = "nre"
    s.flush()

    if loser is not None:
        s.delete(loser)
        s.flush()

    record_event(
        s,
        actor=user,
        action="customer.rekeyed_merged",
        entity_type="Customer",
        entity_id=str(survivor.id),
        metadata={
            "source_customer_id": customer_id,
            "survivor_id": survivor.id,
            "loser_id": preview.loser_id,
            "before_source_id": customer_id,
            "before_source_name": before_source_name,
            "before_source_key": before_source_key,
            "before_survivor_id": survivor.id,
            "before_survivor_name": before_survivor_name,
            "before_survivor_key": before_survivor_key,
            "before_loser_id": preview.loser_id,
            "before_loser_name": before_loser_name,
            "before_loser_key": before_loser_key,
            "after_key": after_key,
            "surviving_name": display,
            "moved_sales_orders": moved["sales_orders"],
            "moved_distributions": moved["distributions"],
            "moved_notes": moved["notes"],
            "moved_rep_assignments": moved["rep_assignments"],
        },
    )
    s.flush()
    return survivor


def is_nre_rekey_candidate(s, customer: Customer) -> bool:
    """Selection rule for Task D backfill (all must hold)."""
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
    from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_NRE_PROJECT

    orders = s.query(SalesOrder).filter(SalesOrder.customer_id == customer.id).all()
    if not orders:
        return False
    if any(o.order_type != ORDER_TYPE_NRE_PROJECT for o in orders):
        return False
    dist_n = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.customer_id == customer.id)
        .count()
    )
    if dist_n != 0:
        return False
    name_key = canonical_customer_key(customer.facility_name)
    if not name_key:
        return False
    # Already a pure name-derived key → skip.
    if customer.company_key == name_key:
        return False
    return True

