from __future__ import annotations

import csv
import os
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.parser import BytesParser
from email.policy import default as email_policy_default
from email.utils import getaddresses, parsedate_to_datetime
from typing import Any

from werkzeug.utils import secure_filename

from app.eqms.audit import record_event
from app.eqms.models import User
from app.eqms.modules.rep_traceability.models import ApprovalEml, DistributionLogEntry, TracingReport
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


def _autogen_order_number(prefix: str) -> str:
    return f"{prefix}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"


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


def create_distribution_entry(s, payload: dict[str, Any], *, user: User, source_default: str) -> DistributionLogEntry:
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
    
    # Auto-match to existing sales order if not provided
    if not sales_order_id and order_number:
        from app.eqms.modules.rep_traceability.models import SalesOrder
        matching_order = (
            s.query(SalesOrder)
            .filter(SalesOrder.order_number == order_number)
            .first()
        )
        if matching_order:
            sales_order_id = matching_order.id

    e = DistributionLogEntry(
        ship_date=sd,
        order_number=order_number,
        facility_name=normalize_text(payload.get("facility_name")),
        rep_id=int(payload["rep_id"]) if payload.get("rep_id") else None,
        customer_id=int(payload["customer_id"]) if payload.get("customer_id") else None,
        sales_order_id=sales_order_id,
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
    return e


def update_distribution_entry(s, entry: DistributionLogEntry, payload: dict[str, Any], *, user: User, reason: str) -> DistributionLogEntry:
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

    entry.updated_at = datetime.utcnow()
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
    return entry


def delete_distribution_entry(s, entry: DistributionLogEntry, *, user: User, reason: str) -> None:
    record_event(
        s,
        actor=user,
        action="distribution_log_entry.delete",
        entity_type="DistributionLogEntry",
        entity_id=str(entry.id),
        reason=reason,
        metadata={"order_number": entry.order_number, "ship_date": str(entry.ship_date), "facility_name": entry.facility_name},
    )
    s.delete(entry)


def query_distribution_entries(s, *, filters: dict[str, Any]):
    from sqlalchemy.orm import selectinload

    q = s.query(DistributionLogEntry).options(selectinload(DistributionLogEntry.customer))

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
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
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
        generated_at=datetime.utcnow(),
        generated_by_user_id=user.id,
        filters_json=_json_dumps_sorted(db_filters),
        report_storage_key=storage_key,
        report_format="csv",
        status="draft",
        sha256=sha256,
        row_count=row_count,
        updated_at=datetime.utcnow(),
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
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
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
        uploaded_at=datetime.utcnow(),
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


def compute_sales_dashboard(s, *, start_date: date | None) -> dict[str, Any]:
    """
    Lean on-demand aggregates for /admin/sales-dashboard.

    Rules:
    - Windowed metrics use ship_date >= start_date (if provided).
    - Customer key = customer_id if present else canonicalized facility/customer name.
    - First-time vs repeat is classified by lifetime distinct order_number per customer key.
    """
    # Lifetime order counts by customer key
    lifetime_rows = (
        s.query(DistributionLogEntry.customer_id, DistributionLogEntry.facility_name, DistributionLogEntry.customer_name, DistributionLogEntry.order_number)
        .all()
    )
    orders_by_customer: dict[str, set[str]] = {}

    def _customer_key(customer_id: int | None, facility_name: str | None, customer_name: str | None) -> str:
        if customer_id:
            return f"id:{customer_id}"
        base = (facility_name or customer_name or "").strip()
        return f"k:{canonical_customer_key(base)}"

    for customer_id, facility_name, customer_name, order_number in lifetime_rows:
        key = _customer_key(customer_id, facility_name, customer_name)
        if key == "k:":
            continue
        orders_by_customer.setdefault(key, set()).add(order_number or "")

    # Windowed entries
    q = s.query(DistributionLogEntry)
    if start_date:
        q = q.filter(DistributionLogEntry.ship_date >= start_date)
    window_entries = q.order_by(DistributionLogEntry.ship_date.asc(), DistributionLogEntry.id.asc()).all()

    total_orders = len({e.order_number for e in window_entries if e.order_number})
    total_units_window = sum(int(e.quantity or 0) for e in window_entries)
    # All-time total units (ignores start_date window)
    from sqlalchemy import func
    total_units_all_time = int(s.query(func.coalesce(func.sum(DistributionLogEntry.quantity), 0)).scalar() or 0)

    window_customer_keys = [
        _customer_key(e.customer_id, e.facility_name, e.customer_name) for e in window_entries if _customer_key(e.customer_id, e.facility_name, e.customer_name) != "k:"
    ]
    total_customers = len(set(window_customer_keys))

    first_time = 0
    repeat = 0
    for key in set(window_customer_keys):
        lifetime_orders = len({o for o in orders_by_customer.get(key, set()) if o})
        if lifetime_orders <= 1:
            first_time += 1
        else:
            repeat += 1

    sku_totals: dict[str, int] = {}
    for e in window_entries:
        sku_totals[e.sku] = sku_totals.get(e.sku, 0) + int(e.quantity or 0)
    sku_breakdown = [{"sku": sku, "units": units} for sku, units in sorted(sku_totals.items(), key=lambda kv: kv[0])]

    # Lot tracking (2026+ lots, all-time distributions) with corrections + active inventory
    from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory, normalize_lot, VALID_SKUS
    lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv").strip()
    _, lot_corrections, lot_inventory, lot_years = load_lot_log_with_inventory(lotlog_path)
    min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2026"))
    min_year_date = date(min_year, 1, 1)

    lot_rx = re.compile(r"^SLQ-\d{5,12}$")
    all_entries = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.lot_number.isnot(None))
        .order_by(DistributionLogEntry.ship_date.asc(), DistributionLogEntry.id.asc())
        .all()
    )

    lot_map: dict[str, dict[str, Any]] = {}
    lot_recent_flags: dict[str, bool] = {}

    for e in all_entries:
        raw_lot = (e.lot_number or "").strip()
        if not raw_lot:
            continue
        normalized_lot = normalize_lot(raw_lot)
        corrected_lot = lot_corrections.get(normalized_lot, normalized_lot)
        if corrected_lot in VALID_SKUS or not lot_rx.match(corrected_lot):
            continue

        rec = lot_map.get(corrected_lot)
        if not rec:
            rec = {"lot": corrected_lot, "units": 0, "first_date": e.ship_date, "last_date": e.ship_date}
            lot_map[corrected_lot] = rec
        rec["units"] += int(e.quantity or 0)
        if e.ship_date and e.ship_date < rec["first_date"]:
            rec["first_date"] = e.ship_date
        if e.ship_date and e.ship_date > rec["last_date"]:
            rec["last_date"] = e.ship_date
        if e.ship_date and e.ship_date >= min_year_date:
            lot_recent_flags[corrected_lot] = True

    # Filter to lots built in 2025+ (or observed in distributions since 2025)
    qualifying_lots: set[str] = set()
    for lot_key in lot_map.keys():
        lot_year = lot_years.get(lot_key)
        if not lot_year:
            m = re.search(r"(20\d{2})", lot_key)
            if m:
                try:
                    lot_year = int(m.group(1))
                except Exception:
                    lot_year = None
        if lot_year and lot_year >= min_year:
            qualifying_lots.add(lot_key)
        elif lot_recent_flags.get(lot_key):
            qualifying_lots.add(lot_key)

    lot_tracking = []
    for rec in sorted(lot_map.values(), key=lambda r: (r["lot"])):
        if rec["lot"] not in qualifying_lots:
            continue
        total_produced = lot_inventory.get(rec["lot"])
        active_inventory = None
        if total_produced is not None:
            active_inventory = int(total_produced) - int(rec["units"])
        rec["active_inventory"] = active_inventory
        lot_tracking.append(rec)

    # Recent orders from NEW customers (first-time = 1 lifetime order)
    # Recent orders from REPEAT customers (2+ lifetime orders)
    recent_orders_new: list[dict[str, Any]] = []
    recent_orders_repeat: list[dict[str, Any]] = []
    
    # Group entries by order_number for order-level view
    orders_by_order_number: dict[str, dict[str, Any]] = {}
    for e in window_entries:
        if not e.order_number or not e.customer_id:
            continue
        if e.order_number not in orders_by_order_number:
            orders_by_order_number[e.order_number] = {
                "order_number": e.order_number,
                "ship_date": e.ship_date,
                "customer_id": e.customer_id,
                "facility_name": e.facility_name or e.customer_name or "",
                "total_units": 0,
            }
        orders_by_order_number[e.order_number]["total_units"] += int(e.quantity or 0)
        # Use latest ship_date if there are multiple entries
        if e.ship_date and e.ship_date > orders_by_order_number[e.order_number]["ship_date"]:
            orders_by_order_number[e.order_number]["ship_date"] = e.ship_date
    
    # Classify orders by customer type (NEW vs REPEAT)
    for order_data in sorted(orders_by_order_number.values(), key=lambda o: (o["ship_date"] or date.min, o["order_number"]), reverse=True):
        cid = order_data["customer_id"]
        customer_key = f"id:{cid}"
        lifetime_order_count = len({o for o in orders_by_customer.get(customer_key, set()) if o})
        
        if lifetime_order_count <= 1:
            if len(recent_orders_new) < 20:
                recent_orders_new.append(order_data)
        else:
            if len(recent_orders_repeat) < 20:
                recent_orders_repeat.append(order_data)

    # Attach note counts for dashboard visibility
    from app.eqms.modules.customer_profiles.models import CustomerNote
    customer_ids = {o["customer_id"] for o in (recent_orders_new + recent_orders_repeat)}
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
        o["note_count"] = note_counts.get(int(o["customer_id"]), 0)
    for o in recent_orders_repeat:
        o["note_count"] = note_counts.get(int(o["customer_id"]), 0)
    
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
        "lot_tracking": lot_tracking,
        "lot_min_year": min_year,
        "recent_orders_new": recent_orders_new,
        "recent_orders_repeat": recent_orders_repeat,
        "window_entries": window_entries,
        "customer_key_fn": _customer_key,
        "orders_by_customer": orders_by_customer,
    }


