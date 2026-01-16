from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.eqms.audit import record_event
from app.eqms.models import User
from app.eqms.modules.rep_traceability.models import DistributionLogEntry

VALID_SKUS = ("211810SPT", "211610SPT", "211410SPT")
VALID_SOURCES = ("shipstation", "manual", "csv_import", "pdf_import")


def normalize_text(s: str | None) -> str:
    return (s or "").strip()


def normalize_source(s: str | None) -> str:
    v = normalize_text(s).lower()
    if not v:
        return ""
    if v == "csv":
        return "csv_import"
    if v == "pdf":
        return "pdf_import"
    if v in ("shipstation", "manual", "csv_import", "pdf_import"):
        return v
    if v == "all":
        return "all"
    return v


def validate_sku(sku: str) -> bool:
    return normalize_text(sku) in VALID_SKUS


_LOT_RE = re.compile(r"^SLQ-\d{5}$")


def validate_lot_number(lot: str) -> bool:
    return bool(_LOT_RE.fullmatch(normalize_text(lot)))


def validate_quantity(qty: int) -> bool:
    return isinstance(qty, int) and qty > 0


def parse_ship_date(s: str) -> date:
    s = normalize_text(s)
    if not s:
        raise ValueError("Ship Date is required (YYYY-MM-DD).")
    return date.fromisoformat(s)


def validate_ship_date(d: date) -> bool:
    return d <= date.today()


def _autogen_order_number(prefix: str) -> str:
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


def check_duplicate_shipstation(s, ss_shipment_id: str) -> DistributionLogEntry | None:
    ss_shipment_id = normalize_text(ss_shipment_id)
    if not ss_shipment_id:
        return None
    return s.query(DistributionLogEntry).filter(DistributionLogEntry.ss_shipment_id == ss_shipment_id).one_or_none()


def check_duplicate_manual_csv(s, order_number: str, ship_date: date, facility_name: str) -> DistributionLogEntry | None:
    """
    Dedupe for manual/csv/pdf: order_number + ship_date + facility_name.

    Per master spec: warn on duplicate, allow override. For CSV import we default to skipping duplicates
    unless caller explicitly forces insert.
    """
    order_number = normalize_text(order_number)
    facility_name = normalize_text(facility_name)
    if not order_number or not facility_name:
        return None
    return (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.order_number == order_number)
        .filter(DistributionLogEntry.ship_date == ship_date)
        .filter(DistributionLogEntry.facility_name == facility_name)
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

    source = normalize_source(payload.get("source"))
    if source and source != "all" and source not in VALID_SOURCES:
        errs.append(ValidationError("source", f"Source must be one of: {', '.join(VALID_SOURCES)}"))

    return errs


def create_distribution_entry(s, payload: dict[str, Any], *, user: User, source_default: str) -> DistributionLogEntry:
    sd = payload["ship_date"]
    if isinstance(sd, str):
        sd = parse_ship_date(sd)

    order_number = normalize_text(payload.get("order_number"))
    if not order_number:
        order_number = _autogen_order_number("MAN" if source_default == "manual" else "CSV")

    e = DistributionLogEntry(
        ship_date=sd,
        order_number=order_number,
        facility_name=normalize_text(payload.get("facility_name")),
        rep_id=int(payload["rep_id"]) if payload.get("rep_id") else None,
        sku=normalize_text(payload.get("sku")),
        lot_number=normalize_text(payload.get("lot_number")),
        quantity=int(payload.get("quantity")),
        source=normalize_source(payload.get("source")) or source_default,
        customer_name=normalize_text(payload.get("customer_name")) or None,
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
        updated_at=datetime.utcnow(),
    )
    s.add(e)
    s.flush()

    record_event(
        s,
        actor=user,
        action="distribution_log.create",
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
    return e


def update_distribution_entry(s, entry: DistributionLogEntry, payload: dict[str, Any], *, user: User, reason: str) -> DistributionLogEntry:
    before = {
        "ship_date": str(entry.ship_date),
        "order_number": entry.order_number,
        "facility_name": entry.facility_name,
        "rep_id": entry.rep_id,
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

    entry.ship_date = sd
    entry.order_number = normalize_text(payload.get("order_number")) or entry.order_number
    entry.facility_name = normalize_text(payload.get("facility_name"))
    entry.rep_id = int(payload["rep_id"]) if payload.get("rep_id") else None
    entry.sku = normalize_text(payload.get("sku"))
    entry.lot_number = normalize_text(payload.get("lot_number"))
    entry.quantity = int(payload.get("quantity"))
    entry.source = normalize_source(payload.get("source")) or entry.source
    entry.customer_name = normalize_text(payload.get("customer_name")) or None
    entry.rep_name = normalize_text(payload.get("rep_name")) or None
    entry.city = normalize_text(payload.get("city")) or None
    entry.state = normalize_text(payload.get("state")) or None
    entry.tracking_number = normalize_text(payload.get("tracking_number")) or None

    entry.updated_at = datetime.utcnow()
    entry.updated_by_user_id = user.id

    after = {
        "ship_date": str(entry.ship_date),
        "order_number": entry.order_number,
        "facility_name": entry.facility_name,
        "rep_id": entry.rep_id,
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
        action="distribution_log.edit",
        entity_type="DistributionLogEntry",
        entity_id=str(entry.id),
        reason=reason,
        metadata={"before": before, "after": after, "fields_changed": fields_changed},
    )
    return entry


def delete_distribution_entry(s, entry: DistributionLogEntry, *, user: User, reason: str) -> None:
    record_event(
        s,
        actor=user,
        action="distribution_log.delete",
        entity_type="DistributionLogEntry",
        entity_id=str(entry.id),
        reason=reason,
        metadata={"order_number": entry.order_number, "ship_date": str(entry.ship_date), "facility_name": entry.facility_name},
    )
    s.delete(entry)


def query_distribution_entries(s, *, filters: dict[str, Any]):
    q = s.query(DistributionLogEntry)

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

    customer = normalize_text(filters.get("customer"))
    if customer:
        q = q.filter(DistributionLogEntry.customer_name == customer)

    return q


