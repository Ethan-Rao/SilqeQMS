from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.eqms.audit import record_event
from app.eqms.models import User
from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
from app.eqms.modules.customer_profiles.utils import canonical_customer_key


def get_customer_by_id(s, customer_id: int) -> Customer | None:
    return s.query(Customer).filter(Customer.id == customer_id).one_or_none()


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
    Ported (lean) from legacy: find by company_key; create if missing; update if fields changed.
    """
    facility_name = (facility_name or "").strip()
    if not facility_name:
        raise ValueError("facility_name is required")

    ck = canonical_customer_key(facility_name)
    if not ck:
        raise ValueError("facility_name cannot be normalized to a company_key")

    c = s.query(Customer).filter(Customer.company_key == ck).one_or_none()
    now = datetime.utcnow()
    if not c:
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
        s.flush()
        return c

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

