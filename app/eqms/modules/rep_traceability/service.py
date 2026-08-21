from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.eqms.utils import utcnow
from email.parser import BytesParser
from email.policy import default as email_policy_default
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any, Sequence

from werkzeug.utils import secure_filename

from app.eqms.audit import record_event
from app.eqms.models import User
from app.eqms.modules.rep_traceability.models import ApprovalEml, DistributionLine, DistributionLogEntry, TracingReport
from app.eqms.storage import storage_from_config
from app.eqms.modules.customer_profiles.service import canonical_customer_key
from app.eqms.modules.rep_traceability.utils import (
    VALID_SKUS,
    VALID_SOURCES,
    normalize_source,
    normalize_text,
    parse_ship_date,
    validate_lot_number,
    validate_quantity,
    validate_ship_date,
    validate_sku,
)


CATHETER_SKUS = frozenset({"211810SPT", "211610SPT", "211410SPT"})


def sales_order_tab_units(order) -> int:
    """Total Units on the customer Sales Orders tab (D69).

    Linked distributions win (same helper as the overview). An order with no
    linked distributions falls back to the sales-order line sum.
    """
    dists = list(getattr(order, "distributions", None) or [])
    if dists:
        return sum_distribution_units(dists)
    return sum(int(line.quantity or 0) for line in (getattr(order, "lines", None) or []))


def packing_slip_display_filename(
    customer_name: str | None,
    ship_date,
    order_number: str | None,
    *,
    existing: set[str] | None = None,
) -> str:
    """D65 display name: ``{Customer}_{YYYY-MM-DD}_SO{7-digit}.pdf``."""
    token = re.sub(r"[^A-Za-z0-9]", "", customer_name or "") or "Customer"
    if hasattr(ship_date, "isoformat"):
        date_s = ship_date.isoformat()
    else:
        date_s = str(ship_date or "")
    digits = normalize_order_number(order_number)
    padded = (digits or "0").zfill(7)
    base = f"{token}_{date_s}_SO{padded}.pdf"
    if not existing or base not in existing:
        return base
    n = 2
    while True:
        cand = f"{token}_{date_s}_SO{padded}_{n}.pdf"
        if cand not in existing:
            return cand
        n += 1


def sum_distribution_units(entries: Sequence[DistributionLogEntry]) -> int:
    """Single source of truth for distribution unit totals (P4-07).

    Prefer sum(DistributionLine.quantity) when line rows exist; otherwise fall back to
    DistributionLogEntry.quantity. Never adds both.
    """
    total = 0
    for e in entries:
        lines = list(getattr(e, "lines", None) or [])
        if lines:
            total += sum(int(l.quantity or 0) for l in lines)
        else:
            total += int(e.quantity or 0)
    return int(total)


def recent_customers_for_weekly_brief(s, limit: int = 5) -> list[dict]:
    """Five most recent distinct customers by latest distribution ship date (D60).

    Units are for that most recent order only, not lifetime. Name comes from the
    Customer record when customer_id is set; otherwise the distribution facility name.
    """
    from collections import defaultdict

    entries = s.query(DistributionLogEntry).all()
    groups: dict[tuple, list] = defaultdict(list)
    for e in entries:
        if e.customer_id is not None:
            groups[("id", e.customer_id)].append(e)
        else:
            groups[("fac", (e.facility_name or "").strip())].append(e)

    rows: list[dict] = []
    for group in groups.values():
        best = max(group, key=lambda e: (e.ship_date or date.min, e.order_number or ""))
        order_entries = [e for e in group if e.order_number == best.order_number]
        if best.customer_id and best.customer is not None:
            name = best.customer.facility_name
        else:
            name = best.facility_name
        rows.append({
            "name": name,
            "order_date": best.ship_date,
            "units": sum_distribution_units(order_entries),
        })
    rows.sort(key=lambda r: (r["order_date"] or date.min, r["name"] or ""), reverse=True)
    return rows[:limit]


def distribution_unit_breakdown(entries: Sequence[DistributionLogEntry]) -> dict[str, int]:
    """Total units plus unmatched portion for customer displays (D40)."""
    unmatched = [e for e in entries if e.sales_order_id is None]
    return {
        "total_units": sum_distribution_units(entries),
        "unmatched_units": sum_distribution_units(unmatched),
        "unmatched_entry_count": len(unmatched),
    }


def format_unmatched_units_note(*, unmatched_units: int, unmatched_entry_count: int) -> str | None:
    """Plain factual note for unmatched portion (D40 / D18: no lateness wording)."""
    if unmatched_units <= 0 or unmatched_entry_count <= 0:
        return None
    noun = "distribution" if unmatched_entry_count == 1 else "distributions"
    return (
        f"{unmatched_units} on {unmatched_entry_count} {noun} "
        "not yet matched to a sales order"
    )


def find_unique_customer_by_facility_key(s, facility_name: str):
    """Resolve exactly one Customer by company_key from a facility/company name (D41)."""
    from app.eqms.modules.customer_profiles.models import Customer

    key = canonical_customer_key(facility_name)
    matches = s.query(Customer).filter(Customer.company_key == key).all()
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one customer with company_key={key!r} "
            f"for name={facility_name!r}, found {len(matches)}"
        )
    return matches[0]


def find_unique_customer_by_company_key(s, company_key: str):
    """Resolve exactly one Customer by its stored company_key (D41)."""
    from app.eqms.modules.customer_profiles.models import Customer

    key = (company_key or "").strip()
    if not key:
        raise ValueError("company_key is required")
    matches = s.query(Customer).filter(Customer.company_key == key).all()
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one customer with company_key={key!r}, found {len(matches)}"
        )
    return matches[0]


def find_unique_customer_for_distribution_ship_to(s, entry: DistributionLogEntry):
    """Resolve customer by address-based keyed identity from a distribution ship-to (D41).

    Prefer exact ``compute_facility_key_from_ship_to`` match. If zip drift yields zero
    hits, require exactly one customer whose company_key shares the same street|STATE|
    prefix. Never falls back to facility-name string matching.
    """
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.customer_profiles.utils import (
        compute_facility_key_from_ship_to,
        normalize_addr_part,
        normalize_street_for_key,
    )
    import re

    exact = compute_facility_key_from_ship_to(
        address1=entry.address1,
        city=entry.city,
        state=entry.state,
        zip=entry.zip,
        facility_name=entry.facility_name,
    )
    matches = s.query(Customer).filter(Customer.company_key == exact).all()
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"Expected exactly one customer with company_key={exact!r}, found {len(matches)}"
        )

    street = normalize_street_for_key(entry.address1)
    st = re.sub(r"[^A-Z0-9]+", "", normalize_addr_part(entry.state))
    if not street or not st:
        raise ValueError(
            f"No customer for company_key={exact!r} and cannot form street|state prefix "
            f"from distribution id={entry.id}"
        )
    prefix = f"{street}|{st}|"
    matches = s.query(Customer).filter(Customer.company_key.like(f"{prefix}%")).all()
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one customer with company_key prefix={prefix!r} "
            f"(exact key {exact!r} missed), found {len(matches)}"
        )
    return matches[0]


def attach_distributions_to_customer(
    s,
    *,
    distribution_ids: list[int],
    customer_id: int,
    actor: User | None = None,
    execute: bool = False,
) -> dict[str, Any]:
    """Assign customer_id on distributions. Never sets or clears sales_order_id (D41)."""
    from app.eqms.modules.customer_profiles.models import Customer

    customer = s.get(Customer, customer_id)
    if customer is None:
        raise ValueError(f"customer_id={customer_id} not found")

    entries = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.id.in_(list(distribution_ids)))
        .order_by(DistributionLogEntry.id.asc())
        .all()
    )
    found = {e.id for e in entries}
    missing = [i for i in distribution_ids if i not in found]
    if missing:
        raise ValueError(f"distribution ids not found: {missing}")

    existing = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.customer_id == customer_id)
        .all()
    )
    units_before = sum_distribution_units(existing)

    row_previews: list[dict[str, Any]] = []
    newly_attached: list[DistributionLogEntry] = []
    for e in entries:
        before = {
            "id": e.id,
            "customer_id": e.customer_id,
            "sales_order_id": e.sales_order_id,
            "order_number": e.order_number,
            "facility_name": e.facility_name,
            "customer_name": e.customer_name,
            "quantity": int(e.quantity or 0),
        }
        after = dict(before)
        after["customer_id"] = customer_id
        units = sum_distribution_units([e])
        row_previews.append({"before": before, "after": after, "units": units})
        if e.customer_id != customer_id:
            newly_attached.append(e)
            if execute:
                e.customer_id = customer_id
                record_event(
                    s,
                    actor=actor,
                    action="distribution.customer_attached",
                    entity_type="distribution_log_entry",
                    entity_id=str(e.id),
                    reason="P4-07 D41 attach orphan distribution to customer by keyed identity",
                    metadata={"before": before, "after": after},
                )

    units_after = units_before + sum_distribution_units(newly_attached)
    return {
        "execute": bool(execute),
        "customer_id": customer_id,
        "customer_facility_name": customer.facility_name,
        "customer_company_key": customer.company_key,
        "distribution_ids": [e.id for e in entries],
        "rows": row_previews,
        "units_before": units_before,
        "units_after": units_after,
        "units_added": sum_distribution_units(newly_attached),
    }


def normalize_order_number(order_num: str | None) -> str:
    """Normalize order numbers for comparison.
    
    Strips "SO" prefix, non-digit chars, and leading zeros so that
    "SO 000290", "SO 0000290", and "0000290" all resolve to "290".
    """
    if not order_num:
        return ""
    s = normalize_text(order_num).upper()
    s = re.sub(r"^SO\s*#?\s*", "", s)
    digits = re.sub(r"\D", "", s)
    if digits:
        return digits.lstrip("0") or "0"
    return s


def find_sales_order_by_normalized_number(s, order_number: str | None):
    """Find SalesOrder by exact order_number, then normalized digit match."""
    from app.eqms.modules.rep_traceability.models import SalesOrder

    order_number = normalize_text(order_number)
    if not order_number:
        return None
    exact = s.query(SalesOrder).filter(SalesOrder.order_number == order_number).first()
    if exact:
        return exact
    target = normalize_order_number(order_number)
    if not target:
        return None
    # Narrow with ilike on trailing digits when possible, then exact normalize.
    rough = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_number.ilike(f"%{target}%"))
        .limit(500)
        .all()
    )
    for so in rough:
        if normalize_order_number(so.order_number) == target:
            return so
    return None


def order_data_is_catheter(order_data: dict | None) -> bool:
    """True iff at least one line SKU is in CATHETER_SKUS.

    An order with no parsed lines is **not** catheter. NRE sales-order PDFs are
    often free text with no line-item table, so zero lines is the normal NRE case.
    """
    lines = (order_data or {}).get("lines") or []
    for line in lines:
        if (line.get("sku") or "") in CATHETER_SKUS:
            return True
    return False


def sales_order_has_catheter_sku(order) -> bool:
    """True if any SalesOrderLine SKU is a catheter SKU."""
    for line in getattr(order, "lines", None) or []:
        if (getattr(line, "sku", None) or "") in CATHETER_SKUS:
            return True
    return False


def normalize_address(addr1: str | None, city: str | None, state: str | None, zip_code: str | None) -> str:
    parts = [normalize_text(addr1), normalize_text(city), normalize_text(state), normalize_text(zip_code)]
    return " ".join(p for p in parts if p).upper()


def sync_distribution_customer_from_sales_order(distribution, sales_order) -> bool:
    """Force dist customer/facility from the linked SalesOrder (SO is source of truth)."""
    if not distribution or not sales_order:
        return False
    changed = False
    if distribution.sales_order_id != sales_order.id:
        distribution.sales_order_id = sales_order.id
        changed = True
    if sales_order.customer_id and distribution.customer_id != sales_order.customer_id:
        distribution.customer_id = sales_order.customer_id
        changed = True
    if sales_order.customer and distribution.facility_name != sales_order.customer.facility_name:
        distribution.facility_name = sales_order.customer.facility_name
        changed = True
    return changed


def match_distribution_to_sales_order(
    s,
    distribution: DistributionLogEntry,
    sales_order,
) -> bool:
    """
    Match a ShipStation distribution to a Sales Order by order number only.

    Uses normalized order number comparison (strips SO prefix, leading zeros)
    so that "SO 000290" matches "0000290". When already linked to this SO,
    still syncs customer_id/facility_name from the SO.
    """
    from app.eqms.modules.rep_traceability.models import SalesOrder

    if not isinstance(sales_order, SalesOrder):
        return False

    if distribution.sales_order_id and distribution.sales_order_id != sales_order.id:
        return False

    if distribution.sales_order_id == sales_order.id:
        return sync_distribution_customer_from_sales_order(distribution, sales_order)

    dist_order = normalize_order_number(distribution.order_number)
    so_order = normalize_order_number(sales_order.order_number)

    if dist_order and so_order and dist_order == so_order:
        return sync_distribution_customer_from_sales_order(distribution, sales_order)

    return False


def rematch_unmatched_distributions_for_order(s, sales_order) -> int:
    """Link unmatched shipstation distributions and sync already-linked ones to this SO."""
    if not sales_order:
        return 0
    normalized_order = normalize_order_number(sales_order.order_number)
    # Unmatched by SO link
    unmatched_q = s.query(DistributionLogEntry).filter(
        DistributionLogEntry.source == "shipstation",
        DistributionLogEntry.sales_order_id.is_(None),
    )
    if normalized_order:
        unmatched_q = unmatched_q.filter(
            DistributionLogEntry.order_number.ilike(f"%{normalized_order}%")
        )
    matched = 0
    for udist in unmatched_q.all():
        if match_distribution_to_sales_order(s, udist, sales_order):
            matched += 1
    # Already linked to this SO — force customer sync
    for d in (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.sales_order_id == sales_order.id)
        .all()
    ):
        if sync_distribution_customer_from_sales_order(d, sales_order):
            matched += 1
    from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type

    safe_apply_order_type(s, sales_order)
    return matched


def _autogen_order_number(prefix: str) -> str:
    return f"{prefix}-{utcnow().strftime('%Y%m%d%H%M%S')}"


def check_duplicate_shipstation(s, ss_shipment_id: str) -> DistributionLogEntry | None:
    ss_shipment_id = normalize_text(ss_shipment_id)
    if not ss_shipment_id:
        return None
    return s.query(DistributionLogEntry).filter(DistributionLogEntry.ss_shipment_id == ss_shipment_id).one_or_none()


def check_duplicate_manual_csv(
    s,
    *,
    order_number: str,
    ship_date: date,
    facility_name: str,
    sku: str,
    lot_number: str,
) -> DistributionLogEntry | None:
    """
    Minimal dedupe rule for CSV import (P0):
    same (order_number + ship_date + facility_name + sku + lot_number).
    Callers may choose to skip duplicates and report them.
    """
    order_number = normalize_text(order_number)
    facility_name = normalize_text(facility_name)
    sku = normalize_text(sku)
    lot_number = normalize_text(lot_number)
    if not order_number or not facility_name:
        return None
    return (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.order_number == order_number)
        .filter(DistributionLogEntry.ship_date == ship_date)
        .filter(DistributionLogEntry.facility_name == facility_name)
        .filter(DistributionLogEntry.sku == sku)
        .filter(DistributionLogEntry.lot_number == lot_number)
        .one_or_none()
    )


@dataclass(frozen=True)
class ValidationError:
    field: str
    message: str


def validate_distribution_payload(payload: dict[str, Any]) -> list[ValidationError]:
    errs: list[ValidationError] = []

    try:
        sd = payload.get("ship_date")
        if isinstance(sd, str):
            sd = parse_ship_date(sd)
        if not isinstance(sd, date):
            raise ValueError("Invalid date")
        if not validate_ship_date(sd):
            errs.append(ValidationError("ship_date", "Ship date cannot be in the future."))
    except Exception:
        errs.append(ValidationError("ship_date", "Ship date is required (YYYY-MM-DD)."))

    sku = normalize_text(payload.get("sku"))
    if not sku or not validate_sku(sku):
        errs.append(ValidationError("sku", f"SKU must be one of: {', '.join(VALID_SKUS)}"))

    lot = normalize_text(payload.get("lot_number"))
    if not lot or not validate_lot_number(lot):
        errs.append(ValidationError("lot_number", "Lot number must match format: SLQ-##### (e.g. SLQ-12345)."))

    try:
        qty = int(payload.get("quantity"))
        if not validate_quantity(qty):
            raise ValueError()
    except Exception:
        errs.append(ValidationError("quantity", "Quantity must be a positive integer."))

    facility = normalize_text(payload.get("facility_name"))
    if not facility:
        errs.append(ValidationError("facility_name", "Facility Name is required."))

    customer_id = normalize_text(payload.get("customer_id"))
    if customer_id:
        try:
            int(customer_id)
        except Exception:
            errs.append(ValidationError("customer_id", "Customer id must be numeric."))

    source = normalize_source(payload.get("source"))
    if source and source != "all" and source not in VALID_SOURCES:
        errs.append(ValidationError("source", f"Source must be one of: {', '.join(VALID_SOURCES)}"))

    return errs


def create_distribution_entry(
    s,
    payload: dict[str, Any],
    *,
    user: User,
    source_default: str,
    create_line: bool = True,
) -> DistributionLogEntry:
    sd = payload["ship_date"]
    if isinstance(sd, str):
        sd = parse_ship_date(sd)

    order_number = normalize_text(payload.get("order_number"))
    if not order_number:
        order_number = _autogen_order_number("MAN" if source_default == "manual" else "CSV")

    # Sales order link (source of truth)
    sales_order_id = None
    if payload.get("sales_order_id"):
        try:
            sales_order_id = int(payload["sales_order_id"])
        except (ValueError, TypeError):
            pass

    customer_id = int(payload["customer_id"]) if payload.get("customer_id") else None

    # Auto-match to existing sales order if not provided (normalized order #)
    matching_order = None
    if sales_order_id:
        from app.eqms.modules.rep_traceability.models import SalesOrder as _SO
        matching_order = s.get(_SO, sales_order_id)
    elif order_number:
        matching_order = find_sales_order_by_normalized_number(s, order_number)
        if matching_order:
            sales_order_id = matching_order.id

    # Linked SO owns the distribution customer (decision 2A)
    if matching_order and matching_order.customer_id:
        customer_id = matching_order.customer_id

    customer_name = normalize_text(payload.get("customer_name")) or None
    if customer_id:
        from app.eqms.modules.customer_profiles.models import Customer
        customer = s.get(Customer, customer_id)
        if customer:
            customer_name = customer.facility_name

    e = DistributionLogEntry(
        ship_date=sd,
        order_number=order_number,
        facility_name=normalize_text(payload.get("facility_name")),
        rep_id=int(payload["rep_id"]) if payload.get("rep_id") else None,
        customer_id=customer_id,
        sales_order_id=sales_order_id,
        sku=normalize_text(payload.get("sku")),
        lot_number=normalize_text(payload.get("lot_number")),
        quantity=int(payload.get("quantity")),
        source=normalize_source(payload.get("source")) or source_default,
        customer_name=customer_name,
        rep_name=normalize_text(payload.get("rep_name")) or None,
        address1=normalize_text(payload.get("address1")) or None,
        address2=normalize_text(payload.get("address2")) or None,
        city=normalize_text(payload.get("city")) or None,
        state=normalize_text(payload.get("state")) or None,
        zip=normalize_text(payload.get("zip")) or None,
        country=normalize_text(payload.get("country")) or "USA",
        contact_name=normalize_text(payload.get("contact_name")) or None,
        contact_phone=normalize_text(payload.get("contact_phone")) or None,
        contact_email=normalize_text(payload.get("contact_email")) or None,
        tracking_number=normalize_text(payload.get("tracking_number")) or None,
        ss_shipment_id=normalize_text(payload.get("ss_shipment_id")) or None,
        evidence_file_storage_key=normalize_text(payload.get("evidence_file_storage_key")) or None,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
        updated_at=utcnow(),
    )
    s.add(e)
    s.flush()

    if create_line:
        s.add(
            DistributionLine(
                distribution_entry_id=e.id,
                sku=e.sku,
                lot_number=e.lot_number,
                quantity=int(e.quantity or 0),
            )
        )

    record_event(
        s,
        actor=user,
        action="distribution_log_entry.create",
        entity_type="DistributionLogEntry",
        entity_id=str(e.id),
        metadata={
            "ship_date": str(e.ship_date),
            "order_number": e.order_number,
            "facility_name": e.facility_name,
            "sku": e.sku,
            "lot_number": e.lot_number,
            "quantity": e.quantity,
            "source": e.source,
        },
    )
    if e.sales_order_id:
        from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type

        safe_apply_order_type(s, e.sales_order_id, user=user)
    return e


def update_distribution_entry(s, entry: DistributionLogEntry, payload: dict[str, Any], *, user: User, reason: str) -> DistributionLogEntry:
    prev_sales_order_id = entry.sales_order_id
    before = {
        "ship_date": str(entry.ship_date),
        "order_number": entry.order_number,
        "facility_name": entry.facility_name,
        "rep_id": entry.rep_id,
        "customer_id": entry.customer_id,
        "sku": entry.sku,
        "lot_number": entry.lot_number,
        "quantity": entry.quantity,
        "source": entry.source,
        "customer_name": entry.customer_name,
        "city": entry.city,
        "state": entry.state,
        "tracking_number": entry.tracking_number,
    }

    sd = payload["ship_date"]
    if isinstance(sd, str):
        sd = parse_ship_date(sd)

    # Guard against overwriting ShipStation SKU/Lot/Qty
    if entry.source == "shipstation":
        from logging import getLogger
        logger = getLogger(__name__)
        if payload.get("sku") and normalize_text(payload.get("sku")) != entry.sku:
            logger.warning("ShipStation SKU overwrite attempt: %s -> %s (entry_id=%s)", entry.sku, payload.get("sku"), entry.id)
        if payload.get("lot_number") and normalize_text(payload.get("lot_number")) != entry.lot_number:
            logger.warning("ShipStation lot overwrite attempt: %s -> %s (entry_id=%s)", entry.lot_number, payload.get("lot_number"), entry.id)
        if payload.get("quantity") and int(payload.get("quantity")) != entry.quantity:
            logger.warning("ShipStation qty overwrite attempt: %s -> %s (entry_id=%s)", entry.quantity, payload.get("quantity"), entry.id)

        # Keep ShipStation SKU/Lot/Qty intact
        payload = dict(payload)
        payload["sku"] = entry.sku
        payload["lot_number"] = entry.lot_number
        payload["quantity"] = entry.quantity

    entry.ship_date = sd
    entry.order_number = normalize_text(payload.get("order_number")) or entry.order_number
    entry.facility_name = normalize_text(payload.get("facility_name"))
    entry.rep_id = int(payload["rep_id"]) if payload.get("rep_id") else None
    entry.customer_id = int(payload["customer_id"]) if payload.get("customer_id") else None
    entry.sku = normalize_text(payload.get("sku"))
    entry.lot_number = normalize_text(payload.get("lot_number"))
    entry.quantity = int(payload.get("quantity"))
    entry.source = normalize_source(payload.get("source")) or entry.source
    entry.customer_name = normalize_text(payload.get("customer_name")) or None
    entry.rep_name = normalize_text(payload.get("rep_name")) or None
    entry.city = normalize_text(payload.get("city")) or None
    entry.state = normalize_text(payload.get("state")) or None
    entry.tracking_number = normalize_text(payload.get("tracking_number")) or None
    
    # Sales order link (source of truth)
    if payload.get("sales_order_id"):
        try:
            entry.sales_order_id = int(payload["sales_order_id"])
        except (ValueError, TypeError):
            pass
    elif "sales_order_id" in payload and not payload["sales_order_id"]:
        entry.sales_order_id = None  # Explicitly clear the link

    if entry.customer_id:
        from app.eqms.modules.customer_profiles.models import Customer
        customer = s.get(Customer, entry.customer_id)
        if customer:
            entry.customer_name = customer.facility_name

    entry.updated_at = utcnow()
    entry.updated_by_user_id = user.id

    after = {
        "ship_date": str(entry.ship_date),
        "order_number": entry.order_number,
        "facility_name": entry.facility_name,
        "rep_id": entry.rep_id,
        "customer_id": entry.customer_id,
        "sku": entry.sku,
        "lot_number": entry.lot_number,
        "quantity": entry.quantity,
        "source": entry.source,
        "customer_name": entry.customer_name,
        "city": entry.city,
        "state": entry.state,
        "tracking_number": entry.tracking_number,
    }
    fields_changed = [k for k in before.keys() if before[k] != after[k]]

    record_event(
        s,
        actor=user,
        action="distribution_log_entry.update",
        entity_type="DistributionLogEntry",
        entity_id=str(entry.id),
        reason=reason,
        metadata={"before": before, "after": after, "fields_changed": fields_changed},
    )
    if prev_sales_order_id != entry.sales_order_id:
        from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type

        if prev_sales_order_id:
            safe_apply_order_type(s, prev_sales_order_id, user=user)
        if entry.sales_order_id:
            safe_apply_order_type(s, entry.sales_order_id, user=user)
    return entry


def delete_distribution_entry(s, entry: DistributionLogEntry, *, user: User, reason: str) -> None:
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment

    prev_sales_order_id = entry.sales_order_id
    lines = list(getattr(entry, "lines", None) or [])
    atts = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.distribution_entry_id == entry.id)
        .all()
    )
    snapshot = {
        "id": entry.id,
        "order_number": entry.order_number,
        "ship_date": str(entry.ship_date),
        "facility_name": entry.facility_name,
        "quantity": entry.quantity,
        "sku": entry.sku,
        "lot_number": entry.lot_number,
        "source": entry.source,
        "customer_id": entry.customer_id,
        "sales_order_id": entry.sales_order_id,
        "lines": [
            {"sku": ln.sku, "lot_number": ln.lot_number, "quantity": ln.quantity}
            for ln in lines
        ],
        "attachment_ids": [a.id for a in atts],
        "attachment_keys": [a.storage_key for a in atts],
    }
    storage = None
    try:
        from flask import current_app

        storage = storage_from_config(current_app.config)
    except Exception:
        storage = None
    for att in atts:
        shared = (
            s.query(OrderPdfAttachment)
            .filter(
                OrderPdfAttachment.storage_key == att.storage_key,
                OrderPdfAttachment.id != att.id,
            )
            .first()
        )
        if shared is None and storage is not None:
            try:
                storage.delete(att.storage_key)
            except Exception:
                pass
        s.delete(att)
    record_event(
        s,
        actor=user,
        action="distribution_log_entry.delete",
        entity_type="DistributionLogEntry",
        entity_id=str(entry.id),
        reason=reason,
        metadata={"snapshot": snapshot, "order_number": entry.order_number, "ship_date": str(entry.ship_date), "facility_name": entry.facility_name},
    )
    s.delete(entry)
    s.flush()
    if prev_sales_order_id:
        from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type

        safe_apply_order_type(s, prev_sales_order_id, user=user)


def delete_sales_order_with_cleanup(s, order, *, user: User, storage=None) -> dict:
    """Delete a SalesOrder, its PDF blobs, and orphan auto-customer if applicable.

    Returns metadata: ``{order_number, customer_id, deleted_customer_id}``.
    Distributions with ``sales_order_id`` SET NULL on delete (FK).
    """
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment, SalesOrder

    if not isinstance(order, SalesOrder):
        raise TypeError("order must be a SalesOrder")

    order_id = order.id
    order_number = order.order_number
    customer_id = order.customer_id
    deleted_customer_id = None

    atts = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.sales_order_id == order_id)
        .all()
    )
    if storage is not None:
        for att in atts:
            try:
                storage.delete(att.storage_key)
            except Exception:
                pass
            s.delete(att)

    record_event(
        s,
        actor=user,
        action="sales_order.delete",
        entity_type="SalesOrder",
        entity_id=str(order_id),
        metadata={"order_number": order_number, "customer_id": customer_id},
    )
    s.delete(order)
    s.flush()

    if customer_id:
        cust = s.get(Customer, customer_id)
        if cust and (cust.customer_type or "auto") == "auto":
            remaining_orders = (
                s.query(SalesOrder)
                .filter(SalesOrder.customer_id == customer_id)
                .count()
            )
            remaining_dists = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.customer_id == customer_id)
                .count()
            )
            if remaining_orders == 0 and remaining_dists == 0:
                record_event(
                    s,
                    actor=user,
                    action="customer.delete_orphan",
                    entity_type="Customer",
                    entity_id=str(customer_id),
                    metadata={
                        "facility_name": cust.facility_name,
                        "reason": "last_sales_order_deleted",
                        "order_number": order_number,
                    },
                )
                s.delete(cust)
                deleted_customer_id = customer_id

    return {
        "order_number": order_number,
        "customer_id": customer_id,
        "deleted_customer_id": deleted_customer_id,
    }


def query_distribution_entries(s, *, filters: dict[str, Any]):
    from sqlalchemy.orm import selectinload

    q = s.query(DistributionLogEntry).options(
        selectinload(DistributionLogEntry.customer),
        selectinload(DistributionLogEntry.lines),
    )

    if filters.get("date_from"):
        q = q.filter(DistributionLogEntry.ship_date >= parse_ship_date(str(filters["date_from"])))
    if filters.get("date_to"):
        q = q.filter(DistributionLogEntry.ship_date <= parse_ship_date(str(filters["date_to"])))

    source = normalize_source(filters.get("source"))
    if source and source != "all":
        q = q.filter(DistributionLogEntry.source == source)

    if filters.get("rep_id"):
        q = q.filter(DistributionLogEntry.rep_id == int(filters["rep_id"]))

    sku = normalize_text(filters.get("sku"))
    if sku and sku != "all":
        q = q.filter(DistributionLogEntry.sku == sku)

    q_text = normalize_text(filters.get("q"))
    if q_text:
        from sqlalchemy import or_

        like = f"%{q_text}%"
        q = q.filter(or_(DistributionLogEntry.facility_name.like(like), DistributionLogEntry.customer_name.like(like)))

    if filters.get("unmatched"):
        q = q.filter(DistributionLogEntry.sales_order_id.is_(None))

    return q


def _json_dumps_sorted(d: dict[str, Any]) -> str:
    return json.dumps(d, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _filters_hash(filters: dict[str, Any]) -> str:
    return _sha256_bytes(_json_dumps_sorted(filters).encode("utf-8"))[:12]


def _month_bounds(month: str) -> tuple[date, date]:
    m = normalize_text(month)
    if not re.fullmatch(r"\d{4}-\d{2}", m):
        raise ValueError("month must be YYYY-MM")
    y = int(m[:4])
    mo = int(m[5:7])
    start = date(y, mo, 1)
    if mo == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, mo + 1, 1)
    return start, end


def generate_tracing_report_csv(s, *, user: User, filters: dict[str, Any], app_config: dict) -> TracingReport:
    """
    Generate a tracing report CSV from distribution_log_entries and store it as an immutable artifact.
    If re-generated, a NEW TracingReport row is created (no overwrites).
    """
    month = normalize_text(filters.get("month"))
    start, end = _month_bounds(month)

    db_filters: dict[str, Any] = {
        "month": month,
        "rep_id": int(filters["rep_id"]) if filters.get("rep_id") else None,
        "source": normalize_source(filters.get("source")) or "all",
        "sku": normalize_text(filters.get("sku")) or "all",
        "q": normalize_text(filters.get("q")) or "",
    }
    filters_hash = _filters_hash(db_filters)
    ts = utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    storage_key = f"tracing_reports/{month}/{filters_hash}_{ts}.csv"

    q = s.query(DistributionLogEntry).filter(DistributionLogEntry.ship_date >= start).filter(DistributionLogEntry.ship_date < end)
    if db_filters["rep_id"] is not None:
        q = q.filter(DistributionLogEntry.rep_id == db_filters["rep_id"])
    if db_filters["source"] and db_filters["source"] != "all":
        q = q.filter(DistributionLogEntry.source == db_filters["source"])
    if db_filters["sku"] and db_filters["sku"] != "all":
        q = q.filter(DistributionLogEntry.sku == db_filters["sku"])
    if db_filters["q"]:
        from sqlalchemy import or_

        like = f"%{db_filters['q']}%"
        q = q.filter(or_(DistributionLogEntry.facility_name.like(like), DistributionLogEntry.customer_name.like(like)))

    entries = q.order_by(DistributionLogEntry.ship_date.asc(), DistributionLogEntry.order_number.asc()).all()

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["Ship Date", "Order #", "Facility", "City", "State", "SKU", "Lot", "Quantity", "Rep", "Source"])
    for e in entries:
        facility = e.customer.facility_name if getattr(e, "customer", None) else e.facility_name
        w.writerow(
            [
                str(e.ship_date),
                e.order_number,
                facility,
                e.city or "",
                e.state or "",
                e.sku,
                e.lot_number,
                e.quantity,
                e.rep_name or (str(e.rep_id) if e.rep_id else ""),
                e.source,
            ]
        )

    csv_bytes = out.getvalue().encode("utf-8")
    sha256 = _sha256_bytes(csv_bytes)
    row_count = len(entries)

    storage = storage_from_config(app_config)
    storage.put_bytes(storage_key, csv_bytes, content_type="text/csv")

    tr = TracingReport(
        generated_at=utcnow(),
        generated_by_user_id=user.id,
        filters_json=_json_dumps_sorted(db_filters),
        report_storage_key=storage_key,
        report_format="csv",
        status="draft",
        sha256=sha256,
        row_count=row_count,
        updated_at=utcnow(),
    )
    s.add(tr)
    s.flush()

    record_event(
        s,
        actor=user,
        action="tracing_report.generate",
        entity_type="TracingReport",
        entity_id=str(tr.id),
        metadata={"filters": db_filters, "storage_key": storage_key, "sha256": sha256, "row_count": row_count},
    )

    return tr


def sanitize_subject_for_filename(subject: str | None) -> str:
    s = secure_filename(subject or "")
    if not s:
        return "approval"
    return s[:100]


def parse_eml_headers(eml_bytes: bytes) -> dict[str, Any]:
    msg = BytesParser(policy=email_policy_default).parsebytes(eml_bytes)
    subject = msg.get("subject")
    from_raw = msg.get("from")
    to_raw = msg.get("to")
    date_raw = msg.get("date")

    from_email = None
    to_email = None
    if from_raw:
        addrs = getaddresses([from_raw])
        if addrs:
            from_email = addrs[0][1] or None
    if to_raw:
        addrs = getaddresses([to_raw])
        if addrs:
            to_email = addrs[0][1] or None

    email_date = None
    if date_raw:
        try:
            email_date = parsedate_to_datetime(date_raw)
            if email_date and email_date.tzinfo:
                # Store naive UTC for consistency with the rest of the codebase.
                email_date = email_date.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            email_date = None

    return {"subject": subject, "from_email": from_email, "to_email": to_email, "email_date": email_date}


def upload_approval_eml(
    s,
    *,
    report: TracingReport,
    eml_bytes: bytes,
    filename: str,
    user: User,
    notes: str | None,
    app_config: dict,
) -> ApprovalEml:
    hdrs = parse_eml_headers(eml_bytes)
    ts = utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    subj = sanitize_subject_for_filename(hdrs.get("subject"))
    safe_fn = secure_filename(filename or "approval.eml") or "approval.eml"
    storage_key = f"approvals/{report.id}/{ts}_{subj}_{safe_fn}"

    storage = storage_from_config(app_config)
    storage.put_bytes(storage_key, eml_bytes, content_type="message/rfc822")

    a = ApprovalEml(
        report_id=report.id,
        storage_key=storage_key,
        original_filename=filename or safe_fn,
        subject=hdrs.get("subject"),
        from_email=hdrs.get("from_email"),
        to_email=hdrs.get("to_email"),
        email_date=hdrs.get("email_date"),
        uploaded_at=utcnow(),
        uploaded_by_user_id=user.id,
        notes=normalize_text(notes) or None,
    )
    s.add(a)
    s.flush()

    record_event(
        s,
        actor=user,
        action="approval_eml.upload",
        entity_type="ApprovalEml",
        entity_id=str(a.id),
        metadata={"report_id": report.id, "storage_key": storage_key, "subject": a.subject},
    )
    return a


def compute_lot_inventory_snapshot(s) -> dict[str, Any]:
    """
    Real-time lot inventory for the Sales Dashboard Lot Inventory card only.

    - Uses all distribution log entries (matched or not; no sales_order filter).
    - Ignores dashboard date filters (caller must not pass start_date here).
    - Subtracts ClearTract units removed per DispositionLog.xlsx.
    """
    from app.eqms.modules.shipstation_sync.parsers import (
        load_disposition_log,
        load_lot_dates,
        load_lot_log_with_inventory,
        normalize_lot,
        resolve_disposition_log_path,
        resolve_lotlog_path,
        VALID_SKUS,
    )

    lotlog_path = resolve_lotlog_path()
    lot_to_sku, lot_corrections, lot_inventory, _lot_years = load_lot_log_with_inventory(lotlog_path)
    lotlog_missing = not lot_to_sku

    lot_mfg_dates, lot_exp_dates = load_lot_dates(lotlog_path)
    disposition_path = resolve_disposition_log_path()
    from app.eqms.modules.shipstation_sync.parsers import _read_disposition_log_bytes

    disposition_by_lot = load_disposition_log(disposition_path, lot_corrections=lot_corrections)
    disposition_log_missing = _read_disposition_log_bytes(disposition_path) is None

    # Open = lots with mfg + exp on LotLog (active inventory positions).
    canonical_lots: dict[str, dict] = {}
    for lot, units in lot_inventory.items():
        sku = lot_to_sku.get(lot)
        if not sku or sku not in VALID_SKUS:
            continue
        mfg = lot_mfg_dates.get(lot)
        exp = lot_exp_dates.get(lot)
        if not mfg or not exp:
            continue
        if lot not in canonical_lots:
            canonical_lots[lot] = {
                "lot": lot,
                "sku": sku,
                "total_produced": units,
                "total_distributed": 0,
                "total_dispositioned": 0,
                "mfg_date": mfg,
                "exp_date": exp,
            }

    def _add_distribution_units(raw_lot: str, qty: int) -> None:
        if not raw_lot or qty <= 0:
            return
        normalized = normalize_lot(raw_lot.strip())
        corrected = lot_corrections.get(normalized, normalized)
        if corrected in canonical_lots:
            canonical_lots[corrected]["total_distributed"] += qty

    # All distribution lines (every log entry, regardless of sales order attachment).
    all_lines = (
        s.query(DistributionLine, DistributionLogEntry)
        .join(DistributionLogEntry, DistributionLogEntry.id == DistributionLine.distribution_entry_id)
        .filter(DistributionLine.lot_number.isnot(None))
        .all()
    )
    for line, _entry in all_lines:
        _add_distribution_units(line.lot_number or "", int(line.quantity or 0))

    line_entry_ids = {
        row[0]
        for row in s.query(DistributionLine.distribution_entry_id).distinct().all()
    }
    fallback_q = s.query(DistributionLogEntry).filter(DistributionLogEntry.lot_number.isnot(None))
    if line_entry_ids:
        fallback_q = fallback_q.filter(~DistributionLogEntry.id.in_(line_entry_ids))
    for entry in fallback_q.all():
        _add_distribution_units(entry.lot_number or "", int(entry.quantity or 0))

    for lot, qty in disposition_by_lot.items():
        if lot in canonical_lots:
            canonical_lots[lot]["total_dispositioned"] = int(qty or 0)

    lot_tracking = []
    for lot_data in canonical_lots.values():
        consumed = lot_data["total_distributed"] + lot_data["total_dispositioned"]
        lot_data["total_consumed"] = consumed
        lot_data["remaining"] = lot_data["total_produced"] - consumed
        lot_tracking.append(lot_data)

    lot_tracking.sort(key=lambda x: (x["sku"], x.get("mfg_date") or "", x["lot"]))

    active_lot_tracking = [row for row in lot_tracking if row.get("mfg_date") and row.get("exp_date")]

    sku_lot_map: dict[str, dict] = {}
    for row in active_lot_tracking:
        sku = row["sku"]
        if sku not in sku_lot_map:
            sku_lot_map[sku] = {
                "sku": sku,
                "total_produced": 0,
                "total_distributed": 0,
                "total_dispositioned": 0,
                "total_consumed": 0,
                "remaining": 0,
                "lots": [],
            }
        sku_lot_map[sku]["total_produced"] += row["total_produced"]
        sku_lot_map[sku]["total_distributed"] += row["total_distributed"]
        sku_lot_map[sku]["total_dispositioned"] += row["total_dispositioned"]
        sku_lot_map[sku]["total_consumed"] += row["total_consumed"]
        sku_lot_map[sku]["remaining"] += row["remaining"]
        sku_lot_map[sku]["lots"].append(row)
    sku_lot_summary = sorted(sku_lot_map.values(), key=lambda x: x["sku"])

    return {
        "lot_tracking": lot_tracking,
        "active_lot_tracking": active_lot_tracking,
        "sku_lot_summary": sku_lot_summary,
        "lotlog_missing": lotlog_missing,
        "disposition_log_missing": disposition_log_missing,
    }


def compute_sales_dashboard(s, *, start_date: date | None, end_date: date | None = None) -> dict[str, Any]:
    """
    Lean on-demand aggregates for /admin/sales-dashboard.

    Rules:
    - All distribution log entries count (matched or not; sales order optional).
    - Windowed metrics use ship_date >= start_date (if provided) and ship_date <= end_date (if provided).
    - Lot Inventory card uses compute_lot_inventory_snapshot() (all-time, not date-filtered).
    - Customer key = customer_id when present. Rows without customer_id are excluded from
      customer keying (logged loudly) — silent name-based fallback retired in P4-07 / D41.
    - First-time vs repeat is classified by lifetime distinct order_number per customer key.
    """
    import logging

    logger = logging.getLogger(__name__)

    # Lifetime order counts by customer key — all distribution entries
    lifetime_rows = (
        s.query(DistributionLogEntry.customer_id, DistributionLogEntry.facility_name, DistributionLogEntry.customer_name, DistributionLogEntry.order_number, DistributionLogEntry.id)
        .all()
    )
    orders_by_customer: dict[str, set[str]] = {}

    def _customer_key(customer_id: int | None, facility_name: str | None, customer_name: str | None, *, entry_id: int | None = None) -> str:
        if customer_id:
            return f"id:{customer_id}"
        # Do not silently key on canonicalized name next to address-based identity (D41).
        logger.error(
            "distribution entry missing customer_id; excluded from dashboard customer keying "
            "(entry_id=%s facility=%r customer_name=%r)",
            entry_id,
            facility_name,
            customer_name,
        )
        return ""

    for customer_id, facility_name, customer_name, order_number, entry_id in lifetime_rows:
        key = _customer_key(customer_id, facility_name, customer_name, entry_id=entry_id)
        if not key:
            continue
        orders_by_customer.setdefault(key, set()).add(order_number or "")

    # Windowed entries — all distribution log rows in the date range
    q = s.query(DistributionLogEntry)
    if start_date:
        q = q.filter(DistributionLogEntry.ship_date >= start_date)
    if end_date:
        q = q.filter(DistributionLogEntry.ship_date <= end_date)
    window_entries = q.order_by(DistributionLogEntry.ship_date.asc(), DistributionLogEntry.id.asc()).all()

    total_orders = len({e.order_number for e in window_entries if e.order_number})
    total_units_window = sum_distribution_units(window_entries)

    # All-time total units (ignores start_date window)
    all_entries = s.query(DistributionLogEntry).all()
    total_units_all_time = sum_distribution_units(all_entries)

    window_customer_keys = [
        _customer_key(e.customer_id, e.facility_name, e.customer_name, entry_id=e.id)
        for e in window_entries
    ]
    window_customer_keys = [k for k in window_customer_keys if k]
    total_customers = len(set(window_customer_keys))

    first_time = 0
    repeat = 0
    for key in set(window_customer_keys):
        lifetime_orders = len({o for o in orders_by_customer.get(key, set()) if o})
        if lifetime_orders <= 1:
            first_time += 1
        else:
            repeat += 1

    # --- SKU breakdown for the selected date window ---
    from sqlalchemy import func

    sku_totals: dict[str, int] = {}
    sku_rows = (
        s.query(DistributionLine.sku, func.sum(DistributionLine.quantity))
        .join(DistributionLogEntry, DistributionLogEntry.id == DistributionLine.distribution_entry_id)
    )
    if start_date:
        sku_rows = sku_rows.filter(DistributionLogEntry.ship_date >= start_date)
    if end_date:
        sku_rows = sku_rows.filter(DistributionLogEntry.ship_date <= end_date)
    sku_rows = sku_rows.group_by(DistributionLine.sku).all()
    for sku, units in sku_rows:
        if sku:
            sku_totals[sku] = int(units or 0)

    entry_line_totals: dict[int, int] = {}
    entry_line_rows = (
        s.query(DistributionLine.distribution_entry_id, func.sum(DistributionLine.quantity))
        .join(DistributionLogEntry, DistributionLogEntry.id == DistributionLine.distribution_entry_id)
    )
    if start_date:
        entry_line_rows = entry_line_rows.filter(DistributionLogEntry.ship_date >= start_date)
    if end_date:
        entry_line_rows = entry_line_rows.filter(DistributionLogEntry.ship_date <= end_date)
    entry_line_rows = entry_line_rows.group_by(DistributionLine.distribution_entry_id).all()
    for entry_id, units in entry_line_rows:
        entry_line_totals[int(entry_id)] = int(units or 0)

    line_entry_ids_window = set(entry_line_totals.keys())
    for e in window_entries:
        if e.id in line_entry_ids_window:
            continue
        if e.sku:
            sku_totals[e.sku] = sku_totals.get(e.sku, 0) + int(e.quantity or 0)
    sku_breakdown = [{"sku": sku, "units": units} for sku, units in sorted(sku_totals.items(), key=lambda kv: kv[0])]

    # Lot Inventory card: all-time, all distribution entries, includes dispositions (no date filter).
    lot_snapshot = compute_lot_inventory_snapshot(s)
    lot_tracking = lot_snapshot["lot_tracking"]
    active_lot_tracking = lot_snapshot["active_lot_tracking"]
    sku_lot_summary = lot_snapshot["sku_lot_summary"]
    lotlog_missing = lot_snapshot["lotlog_missing"]
    disposition_log_missing = lot_snapshot["disposition_log_missing"]

    # Recent orders from NEW customers (first-time = 1 lifetime order)
    # Recent orders from REPEAT customers (2+ lifetime orders)
    recent_orders_new: list[dict[str, Any]] = []
    recent_orders_repeat: list[dict[str, Any]] = []
    
    # Group entries by order_number for order-level view (all distribution rows)
    orders_by_order_number: dict[str, dict[str, Any]] = {}
    for e in window_entries:
        if not e.order_number:
            continue
        customer_key = _customer_key(e.customer_id, e.facility_name, e.customer_name, entry_id=e.id)
        if not customer_key:
            continue
        if e.order_number not in orders_by_order_number:
            orders_by_order_number[e.order_number] = {
                "order_number": e.order_number,
                "ship_date": e.ship_date,
                "customer_id": e.customer_id,
                "customer_key": customer_key,
                "facility_name": e.facility_name or e.customer_name or "",
                "total_units": 0,
            }
        elif e.customer_id and not orders_by_order_number[e.order_number]["customer_id"]:
            orders_by_order_number[e.order_number]["customer_id"] = e.customer_id
        orders_by_order_number[e.order_number]["total_units"] += entry_line_totals.get(e.id, int(e.quantity or 0))
        if e.ship_date and e.ship_date > orders_by_order_number[e.order_number]["ship_date"]:
            orders_by_order_number[e.order_number]["ship_date"] = e.ship_date

    # Classify orders by customer type (NEW vs REPEAT)
    for order_data in sorted(orders_by_order_number.values(), key=lambda o: (o["ship_date"] or date.min, o["order_number"]), reverse=True):
        customer_key = order_data["customer_key"]
        lifetime_order_count = len({o for o in orders_by_customer.get(customer_key, set()) if o})
        
        if lifetime_order_count <= 1:
            if len(recent_orders_new) < 20:
                recent_orders_new.append(order_data)
        else:
            if len(recent_orders_repeat) < 20:
                recent_orders_repeat.append(order_data)

    # Attach note counts for dashboard visibility
    from app.eqms.modules.customer_profiles.models import CustomerNote
    customer_ids = {o["customer_id"] for o in (recent_orders_new + recent_orders_repeat) if o.get("customer_id")}
    note_counts: dict[int, int] = {}
    if customer_ids:
        rows = (
            s.query(CustomerNote.customer_id, func.count(CustomerNote.id))
            .filter(CustomerNote.customer_id.in_(list(customer_ids)))
            .group_by(CustomerNote.customer_id)
            .all()
        )
        note_counts = {int(cid): int(cnt or 0) for cid, cnt in rows}
    for o in recent_orders_new:
        cid = o.get("customer_id")
        o["note_count"] = note_counts.get(int(cid), 0) if cid else 0
    for o in recent_orders_repeat:
        cid = o.get("customer_id")
        o["note_count"] = note_counts.get(int(cid), 0) if cid else 0
    
    return {
        "stats": {
            "total_orders": total_orders,
            "total_units_all_time": total_units_all_time,
            "total_units_window": total_units_window,
            "total_customers": total_customers,
            "first_time_customers": first_time,
            "repeat_customers": repeat,
        },
        "sku_breakdown": sku_breakdown,
        "sku_breakdown_alltime": sku_breakdown,
        "lot_tracking": lot_tracking,
        "active_lot_tracking": active_lot_tracking,
        "sku_lot_summary": sku_lot_summary,
        "lotlog_missing": lotlog_missing,
        "disposition_log_missing": disposition_log_missing,
        "recent_orders_new": recent_orders_new,
        "recent_orders_repeat": recent_orders_repeat,
        "window_entries": window_entries,
        "customer_key_fn": _customer_key,
        "orders_by_customer": orders_by_customer,
        "entry_line_totals": entry_line_totals,
    }


