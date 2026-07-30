from __future__ import annotations

import csv
import io
import logging
from datetime import date

from flask import Blueprint, flash, g, redirect, render_template, request, send_file, url_for, current_app

# Module-level logger for PDF import and other operations
logger = logging.getLogger(__name__)

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.rep_traceability.models import (
    ApprovalEml,
    DistributionLine,
    DistributionLogEntry,
    OrderPdfAttachment,
    TracingReport,
)
from app.eqms.modules.rep_traceability.parsers.csv import parse_distribution_csv
from app.eqms.modules.rep_traceability.service import (
    check_duplicate_manual_csv,
    compute_sales_dashboard,
    create_distribution_entry,
    delete_distribution_entry,
    generate_tracing_report_csv,
    order_data_is_catheter,
    query_distribution_entries,
    rematch_unmatched_distributions_for_order,
    update_distribution_entry,
    upload_approval_eml,
    validate_distribution_payload,
)
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.customer_profiles.service import find_or_create_customer
from app.eqms.modules.customer_profiles.utils import facility_display_name
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config
from app.eqms.utils import allow_inline_view, current_user as _current_user, utcnow
from app.eqms.modules.rep_traceability.utils import (
    VALID_SKUS,
    is_packing_slip_pdf_type,
    normalize_source,
    normalize_text,
    parse_distribution_filters,
    parse_ship_date,
    parse_tracing_filters,
    validate_lot_number,
    validate_sku,
)

bp = Blueprint("rep_traceability", __name__)


def _fill_so_parsed_fields(order, order_data: dict) -> None:
    """Fill SalesOrder parseable fields from PDF dict — nulls only (never clobber).

    Matches the backfill script without ``--force``. Never writes ``invoice_date``.
    """
    if order.order_amount is None and order_data.get("order_amount") is not None:
        order.order_amount = order_data["order_amount"]
    if order.po_reference is None and order_data.get("po_reference"):
        order.po_reference = order_data["po_reference"]
    if order.order_description is None and order_data.get("order_description"):
        order.order_description = order_data["order_description"]

    # Per-order addresses (P40) — fill-nulls-only.
    addr_map = (
        ("sold_to_address1", "address1"),
        ("sold_to_city", "city"),
        ("sold_to_state", "state"),
        ("sold_to_zip", "zip"),
        ("ship_to_name", "ship_to_name"),
        ("ship_to_address1", "ship_to_address1"),
        ("ship_to_city", "ship_to_city"),
        ("ship_to_state", "ship_to_state"),
        ("ship_to_zip", "ship_to_zip"),
    )
    for attr, key in addr_map:
        if getattr(order, attr, None) is None and order_data.get(key):
            setattr(order, attr, order_data[key])


def _find_sales_order_by_number(s, order_number: str):
    """Find a SalesOrder by order number, using normalized matching.
    
    First tries exact match, then falls back to normalized comparison
    (strips 'SO' prefix, non-digits, and leading zeros).
    """
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.rep_traceability.service import normalize_order_number

    # Exact match first (fast)
    exact = s.query(SalesOrder).filter(SalesOrder.order_number == order_number).first()
    if exact:
        return exact

    # Normalized fallback — compare with leading-zero-stripped digits
    target = normalize_order_number(order_number)
    if not target:
        return None
    candidates = s.query(SalesOrder).all()
    for so in candidates:
        if normalize_order_number(so.order_number) == target:
            return so
    return None


def _store_pdf_attachment(
    s,
    *,
    pdf_bytes: bytes,
    filename: str,
    pdf_type: str,
    sales_order_id: int | None,
    distribution_entry_id: int | None,
    user: User,
    order_number: str | None = None,
) -> str:
    """
    Store PDF bytes to configured storage backend and create OrderPdfAttachment record.
    
    Uses order_number (not DB id) for stable storage keys that survive delete/reimport.
    
    Raises:
        StorageError: If storage is misconfigured or inaccessible
    """
    from werkzeug.utils import secure_filename
    from datetime import datetime
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
    from app.eqms.storage import StorageError

    storage = storage_from_config(current_app.config)
    timestamp = utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(filename) or "document.pdf"
    if order_number:
        # Stable key: uses order_number; include distribution id to avoid collisions when one SO has many shipments.
        de = f"_de{distribution_entry_id}" if distribution_entry_id else ""
        storage_key = f"sales_orders/{order_number}/pdfs/{pdf_type}{de}_{safe_name}"
    elif sales_order_id:
        storage_key = f"sales_orders/{sales_order_id}/pdfs/{pdf_type}_{timestamp}_{safe_name}"
    else:
        storage_key = f"sales_orders/unlinked/{pdf_type}_{timestamp}_{safe_name}"
    
    # Graceful error handling for storage failures
    try:
        storage.put_bytes(storage_key, pdf_bytes, content_type="application/pdf")
    except Exception as e:
        current_app.logger.error("Storage write failed for key=%s: %s", storage_key, e)
        raise StorageError(f"Failed to store PDF: storage not configured or inaccessible. Contact admin.") from e

    attachment = OrderPdfAttachment(
        sales_order_id=sales_order_id,
        distribution_entry_id=distribution_entry_id,
        storage_key=storage_key,
        filename=filename,
        pdf_type=pdf_type,
        uploaded_by_user_id=user.id,
    )
    s.add(attachment)
    return storage_key


def _delete_packing_slip_attachments_for_distribution(s, distribution_entry_id: int) -> None:
    """Remove prior packing slip PDFs for this distribution so re-uploads supersede old files."""
    rows = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.distribution_entry_id == distribution_entry_id)
        .all()
    )
    storage = storage_from_config(current_app.config)
    for a in rows:
        if not is_packing_slip_pdf_type(a.pdf_type):
            continue
        try:
            storage.delete(a.storage_key)
        except Exception as exc:
            current_app.logger.warning("Storage delete failed for key=%s: %s", a.storage_key, exc)
        s.delete(a)


def _match_distribution_for_label(
    s,
    *,
    tracking_number: str | None,
    ship_to: str | None,
    order_number: str | None = None,
    ss_shipment_id: str | None = None,
) -> DistributionLogEntry | None:
    """Match a parsed packing-slip segment to a distribution (supports one sales order → many distributions)."""
    from app.eqms.modules.rep_traceability.service import normalize_order_number

    tracking = normalize_text(tracking_number)
    ship_to_norm = normalize_text(ship_to)
    ss_norm = normalize_text(ss_shipment_id)

    if tracking:
        rows = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.tracking_number == tracking)
            .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
            .all()
        )
        if len(rows) == 1:
            return rows[0]
        if len(rows) > 1 and ss_norm:
            for r in rows:
                if normalize_text(r.ss_shipment_id) == ss_norm:
                    return r
        if rows:
            return rows[0]

    target = normalize_order_number(order_number) if order_number else ""
    if target:
        rough = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.order_number.ilike(f"%{target}%"))
            .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
            .limit(500)
            .all()
        )
        candidates = [e for e in rough if normalize_order_number(e.order_number) == target]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            if tracking:
                hits = [c for c in candidates if normalize_text(c.tracking_number) == tracking]
                if len(hits) == 1:
                    return hits[0]
            if ship_to_norm:
                fac_hits = [
                    c
                    for c in candidates
                    if ship_to_norm in normalize_text(c.facility_name)
                    or normalize_text(c.facility_name) in ship_to_norm
                ]
                if len(fac_hits) == 1:
                    return fac_hits[0]
            return None

    if ship_to_norm:
        like = f"%{ship_to_norm}%"
        rows = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.facility_name.ilike(like))
            .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
            .all()
        )
        if len(rows) == 1:
            return rows[0]
    return None


def _parse_filters() -> dict:
    return parse_distribution_filters(request.args)

def _customers_for_select(s) -> list[Customer]:
    return s.query(Customer).order_by(Customer.facility_name.asc(), Customer.id.asc()).limit(500).all()


def _is_catheter_order(order_data: dict) -> bool:
    """
    Determine if a sales order is a catheter order.

    Rules:
    - If ANY line has a catheter SKU -> catheter order (True)
    - If order has NO lines at all -> assume catheter (True) — parse error, not NRE
    - If order has lines but NONE are catheter SKUs -> NRE (False)
    """
    return order_data_is_catheter(order_data)


def _find_or_create_customer_for_order_data(s, order_data: dict):
    """Create/match Customer: Ship-To facility key for catheter; company key for NRE.

    Catheter display name = clinical Ship-To facility name (not payer ALL-CAPS + city).
    """
    customer_name = order_data.get("customer_name") or ""
    customer_code = order_data.get("customer_code")
    is_catheter = _is_catheter_order(order_data)
    ship_name = order_data.get("ship_to_name") or customer_name
    if is_catheter:
        display = facility_display_name(
            ship_name,
            sold_to_name=customer_name,
            city=order_data.get("ship_to_city"),
        )
        return find_or_create_customer(
            s,
            facility_name=display,
            customer_code=customer_code,
            address1=order_data.get("ship_to_address1"),
            city=order_data.get("ship_to_city"),
            state=order_data.get("ship_to_state"),
            zip=order_data.get("ship_to_zip"),
            contact_name=order_data.get("ship_to_name"),
            contact_email=order_data.get("contact_email"),
            sold_to_address1=order_data.get("address1"),
            sold_to_city=order_data.get("city"),
            sold_to_state=order_data.get("state"),
            sold_to_zip=order_data.get("zip"),
            identity="facility",
            customer_type="catheter",
        )
    return find_or_create_customer(
        s,
        facility_name=customer_name,
        customer_code=customer_code,
        address1=order_data.get("ship_to_address1"),
        city=order_data.get("ship_to_city"),
        state=order_data.get("ship_to_state"),
        zip=order_data.get("ship_to_zip"),
        contact_name=order_data.get("ship_to_name"),
        contact_email=order_data.get("contact_email"),
        sold_to_address1=order_data.get("address1"),
        sold_to_city=order_data.get("city"),
        sold_to_state=order_data.get("state"),
        sold_to_zip=order_data.get("zip"),
        identity="company",
    )


@bp.get("/distribution-log")
@require_permission("distribution_log.view")
def distribution_log_list():
    s = db_session()
    filters = _parse_filters()
    page = int(filters.get("page") or 1)
    per_page = 50
    q = query_distribution_entries(s, filters=filters)
    total = q.count()
    entries = (
        q.order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    has_prev = page > 1
    has_next = page * per_page < total

    # Jinja cannot splat **kwargs in url_for; precompute pagination/export URLs here.
    filters_for_urls = {k: v for k, v in (filters or {}).items() if k != "page" and v not in (None, "", "all")}
    prev_url = url_for("rep_traceability.distribution_log_list", page=page - 1, **filters_for_urls) if has_prev else None
    next_url = url_for("rep_traceability.distribution_log_list", page=page + 1, **filters_for_urls) if has_next else None
    export_url = url_for("rep_traceability.distribution_log_export", **filters_for_urls)
    from app.eqms.modules.customer_profiles.models import Rep
    reps = s.query(Rep).filter(Rep.is_active.is_(True)).order_by(Rep.name.asc()).all()

    return render_template(
        "admin/distribution_log/list.html",
        entries=entries,
        filters=filters,
        reps=reps,
        export_url=export_url,
        page=page,
        per_page=per_page,
        total=total,
        has_prev=has_prev,
        has_next=has_next,
        prev_url=prev_url,
        next_url=next_url,
    )


@bp.get("/distribution-log/new")
@require_permission("distribution_log.create")
def distribution_log_new_get():
    from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
    s = db_session()
    customers = _customers_for_select(s)
    # Recent sales orders for dropdown (most recent 100)
    sales_orders = (
        s.query(SalesOrder)
        .order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc())
        .limit(100)
        .all()
    )
    return render_template("admin/distribution_log/edit.html", entry=None, customers=customers, sales_orders=sales_orders)


@bp.post("/distribution-log/new")
@require_permission("distribution_log.create")
def distribution_log_new_post():
    s = db_session()
    u = _current_user()

    payload = {
        "ship_date": request.form.get("ship_date"),
        "order_number": request.form.get("order_number"),
        "facility_name": request.form.get("facility_name"),
        "rep_id": request.form.get("rep_id"),
        "rep_name": request.form.get("rep_name"),
        "customer_id": request.form.get("customer_id"),
        "customer_name": request.form.get("customer_name"),
        "source": "manual",
        "address1": request.form.get("address1"),
        "city": request.form.get("city"),
        "state": request.form.get("state"),
        "zip": request.form.get("zip"),
        "tracking_number": request.form.get("tracking_number"),
        "sales_order_id": request.form.get("sales_order_id"),  # Link to sales order
    }

    skus = request.form.getlist("skus[]") or request.form.getlist("skus")
    lots = request.form.getlist("lots[]") or request.form.getlist("lots")
    quantities = request.form.getlist("quantities[]") or request.form.getlist("quantities")

    rows: list[dict[str, str]] = []
    if skus or lots or quantities:
        max_len = max(len(skus), len(lots), len(quantities))
        for i in range(max_len):
            sku = skus[i].strip() if i < len(skus) and skus[i] else ""
            lot = lots[i].strip() if i < len(lots) and lots[i] else ""
            qty = quantities[i].strip() if i < len(quantities) and quantities[i] else ""
            if not (sku or lot or qty):
                continue
            rows.append({"sku": sku, "lot_number": lot, "quantity": qty})
    else:
        # Backward-compatible single row
        rows.append({
            "sku": request.form.get("sku") or "",
            "lot_number": request.form.get("lot_number") or "",
            "quantity": request.form.get("quantity") or "",
        })

    # Customer selection is REQUIRED for manual entries (data cohesion)
    customer_id = normalize_text(payload.get("customer_id"))
    if not customer_id:
        flash("Customer selection is required for manual entries.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_new_get"))
    
    c = s.query(Customer).filter(Customer.id == int(customer_id)).one_or_none()
    if not c:
        flash("Selected customer was not found. Please re-select and try again.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_new_get"))
    
    # Canonicalize facility fields from customer master record (for consistency)
    payload["customer_id"] = str(c.id)
    payload["customer_name"] = c.facility_name  # deprecated text mirror
    payload["facility_name"] = c.facility_name
    payload["address1"] = c.address1
    payload["city"] = c.city
    payload["state"] = c.state
    payload["zip"] = c.zip

    # Validate sales_order_id matches customer_id (if provided)
    sales_order_id = normalize_text(payload.get("sales_order_id"))
    if sales_order_id:
        from app.eqms.modules.rep_traceability.models import SalesOrder
        so = s.query(SalesOrder).filter(SalesOrder.id == int(sales_order_id)).one_or_none()
        if not so:
            flash("Selected sales order was not found.", "danger")
            return redirect(url_for("rep_traceability.distribution_log_new_get"))
        if so.customer_id and so.customer_id != c.id:
            flash(f"Sales order #{so.order_number} belongs to a different customer. Please select a matching customer or remove the sales order link.", "danger")
            return redirect(url_for("rep_traceability.distribution_log_new_get"))

    if not rows:
        flash("At least one SKU/Lot/Quantity row is required.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_new_get"))

    # Validate all rows before creating entries
    for idx, row in enumerate(rows, start=1):
        row_payload = payload.copy()
        row_payload.update(row)
        errs = validate_distribution_payload(row_payload)
        if errs:
            msg = "; ".join([f"{e.field}: {e.message}" for e in errs])
            flash(f"Row {idx} validation failed: {msg}", "danger")
            return redirect(url_for("rep_traceability.distribution_log_new_get"))

    ship_date = parse_ship_date(str(payload["ship_date"]))
    created_count = 0
    for row in rows:
        row_payload = payload.copy()
        row_payload.update(row)
        dupe = check_duplicate_manual_csv(
            s,
            order_number=row_payload.get("order_number") or "",
            ship_date=ship_date,
            facility_name=row_payload.get("facility_name") or "",
            sku=row_payload.get("sku") or "",
            lot_number=row_payload.get("lot_number") or "",
        )
        if dupe:
            flash(
                f"Duplicate detected for SKU {row_payload.get('sku')} + lot {row_payload.get('lot_number')} (entry created anyway).",
                "danger",
            )
        create_distribution_entry(s, row_payload, user=u, source_default="manual")
        created_count += 1
    s.commit()
    flash(f"Created {created_count} distribution entr{'y' if created_count == 1 else 'ies'}.", "success")
    return redirect(url_for("rep_traceability.distribution_log_list"))


@bp.get("/distribution-log/<int:entry_id>/edit")
@require_permission("distribution_log.edit")
def distribution_log_edit_get(entry_id: int):
    from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
    from sqlalchemy import or_
    
    s = db_session()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        from flask import abort
        abort(404)
    
    # Load PDF attachments for this distribution
    attachments = (
        s.query(OrderPdfAttachment)
        .filter(
            or_(
                OrderPdfAttachment.distribution_entry_id == entry_id,
                (OrderPdfAttachment.sales_order_id == entry.sales_order_id) if entry.sales_order_id else False,
            )
        )
        .order_by(OrderPdfAttachment.uploaded_at.desc())
        .all()
    )
    entry.attachments = attachments
    
    customers = _customers_for_select(s)
    # Recent sales orders for dropdown (most recent 100)
    sales_orders = (
        s.query(SalesOrder)
        .order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc())
        .limit(100)
        .all()
    )
    return render_template("admin/distribution_log/edit.html", entry=entry, customers=customers, sales_orders=sales_orders)


@bp.post("/distribution-log/<int:entry_id>/edit")
@require_permission("distribution_log.edit")
def distribution_log_edit_post(entry_id: int):
    from app.eqms.modules.rep_traceability.models import SalesOrder, DistributionLine
    s = db_session()
    u = _current_user()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        from flask import abort
        abort(404)

    reason = normalize_text(request.form.get("reason"))
    if not reason:
        flash("Reason is required for edits.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    # ── Parse multi-line SKU/lot/qty arrays ──
    skus_raw = request.form.getlist("skus[]")
    lots_raw = request.form.getlist("lots[]")
    qtys_raw = request.form.getlist("quantities[]")
    line_ids_raw = request.form.getlist("line_ids[]")

    parsed_lines: list[dict] = []
    for i in range(len(skus_raw)):
        sku_val = normalize_text(skus_raw[i]) if i < len(skus_raw) else ""
        lot_val = normalize_text(lots_raw[i]) if i < len(lots_raw) else ""
        qty_val = qtys_raw[i].strip() if i < len(qtys_raw) else ""
        if not sku_val and not lot_val and not qty_val:
            continue  # skip blank rows
        if not sku_val or not validate_sku(sku_val):
            flash(f"Line {i+1}: Invalid SKU. Must be one of: {', '.join(VALID_SKUS)}", "danger")
            return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
        if not lot_val or not validate_lot_number(lot_val):
            flash(f"Line {i+1}: Invalid Lot Number. Format: SLQ-##### or UNKNOWN.", "danger")
            return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
        try:
            qty_int = int(qty_val)
            if qty_int < 1:
                raise ValueError()
        except (ValueError, TypeError):
            flash(f"Line {i+1}: Quantity must be a positive integer.", "danger")
            return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
        parsed_lines.append({"sku": sku_val, "lot_number": lot_val, "quantity": qty_int})

    if not parsed_lines:
        flash("At least one distribution line is required.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    # Use the first line for the parent-level entry fields (backward compat)
    first_line = parsed_lines[0]
    total_qty = sum(ln["quantity"] for ln in parsed_lines)

    payload = {
        "ship_date": request.form.get("ship_date"),
        "order_number": request.form.get("order_number"),
        "facility_name": request.form.get("facility_name"),
        "rep_id": request.form.get("rep_id"),
        "rep_name": request.form.get("rep_name"),
        "customer_id": request.form.get("customer_id"),
        "customer_name": request.form.get("customer_name"),
        "source": request.form.get("source") or entry.source,
        "sku": first_line["sku"],
        "lot_number": first_line["lot_number"],
        "quantity": str(first_line["quantity"]),
        "city": request.form.get("city"),
        "state": request.form.get("state"),
        "zip": request.form.get("zip"),
        "tracking_number": request.form.get("tracking_number"),
        "sales_order_id": request.form.get("sales_order_id"),
    }

    # Customer selection is required for manual/CSV entries (data cohesion)
    customer_id = normalize_text(payload.get("customer_id"))
    source = normalize_source(payload.get("source") or entry.source)
    if source in ("manual", "csv_import") and not customer_id:
        flash("Customer selection is required for manual/CSV entries.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    if customer_id:
        c = s.query(Customer).filter(Customer.id == int(customer_id)).one_or_none()
        if not c:
            flash("Selected customer was not found. Please re-select and try again.", "danger")
            return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
        payload["customer_id"] = str(c.id)
        payload["customer_name"] = c.facility_name
        payload["facility_name"] = c.facility_name
        payload["city"] = c.city
        payload["state"] = c.state
        payload["zip"] = c.zip

        # Validate sales_order_id matches customer_id (if provided)
        sales_order_id = normalize_text(payload.get("sales_order_id"))
        if sales_order_id:
            so = s.query(SalesOrder).filter(SalesOrder.id == int(sales_order_id)).one_or_none()
            if not so:
                flash("Selected sales order was not found.", "danger")
                return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
            if so.customer_id and so.customer_id != c.id:
                flash(f"Sales order #{so.order_number} belongs to a different customer.", "danger")
                return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    errs = validate_distribution_payload(payload)
    if errs:
        flash("; ".join([f"{e.field}: {e.message}" for e in errs]), "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    update_distribution_entry(s, entry, payload, user=u, reason=reason)
    entry.zip = normalize_text(payload.get("zip")) or None

    # ── Rebuild distribution lines ──
    # Delete all existing lines and recreate from parsed_lines
    for old_line in list(entry.lines):
        s.delete(old_line)
    s.flush()

    for ln in parsed_lines:
        new_line = DistributionLine(
            distribution_entry_id=entry.id,
            sku=ln["sku"],
            lot_number=ln["lot_number"],
            quantity=ln["quantity"],
        )
        s.add(new_line)

    s.commit()
    flash("Distribution entry updated.", "success")
    return redirect(url_for("rep_traceability.distribution_log_list"))


@bp.post("/distribution-log/<int:entry_id>/delete")
@require_permission("distribution_log.delete")
def distribution_log_delete(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        from flask import abort

        abort(404)

    reason = normalize_text(request.form.get("reason"))
    if not reason:
        flash("Reason is required for deletes.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    delete_distribution_entry(s, entry, user=u, reason=reason)
    s.commit()
    flash("Distribution entry deleted.", "success")
    return redirect(url_for("rep_traceability.distribution_log_list"))


@bp.post("/distribution-log/<int:entry_id>/upload-pdf")
@require_permission("distribution_log.edit")
def distribution_upload_pdf(entry_id: int):
    """Upload a PDF to a distribution entry.
    
    If the PDF is a parseable sales order, creates/updates the linked
    SalesOrder and links the distribution to it.  Otherwise stores as
    a generic attachment.
    """
    from werkzeug.utils import secure_filename
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
    from app.eqms.modules.rep_traceability.service import normalize_order_number
    
    s = db_session()
    u = _current_user()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        flash("Distribution entry not found.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))
    
    pdf_file = request.files.get("pdf_file")
    if not pdf_file or not pdf_file.filename:
        flash("Please select a PDF file.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
    
    pdf_bytes = pdf_file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        flash("File too large (max 10MB).", "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
    
    # ── Try to PARSE the PDF as a sales order ──
    parsed_order = None
    try:
        from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf
        result = parse_sales_orders_pdf(pdf_bytes)
        if result.orders:
            parsed_order = result.orders[0]
    except Exception:
        pass  # Fall through to generic attachment storage
    
    if parsed_order:
        order_number = parsed_order["order_number"]
        order_date = parsed_order["order_date"]
        customer_name = parsed_order["customer_name"]
        customer_code = parsed_order.get("customer_code")
        
        # Find or create customer
        try:
            customer = find_or_create_customer(
                s,
                facility_name=customer_name,
                customer_code=customer_code,
                address1=parsed_order.get("ship_to_address1"),
                city=parsed_order.get("ship_to_city"),
                state=parsed_order.get("ship_to_state"),
                zip=parsed_order.get("ship_to_zip"),
                contact_name=parsed_order.get("ship_to_name"),
                contact_email=parsed_order.get("contact_email"),
                sold_to_address1=parsed_order.get("address1"),
                sold_to_city=parsed_order.get("city"),
                sold_to_state=parsed_order.get("state"),
                sold_to_zip=parsed_order.get("zip"),
            )
        except Exception as e:
            current_app.logger.warning(f"Error creating customer '{customer_name}': {e}")
            customer = None
        
        # Upsert SalesOrder
        existing_so = _find_sales_order_by_number(s, order_number)
        
        if existing_so:
            existing_so.order_date = order_date
            existing_so.ship_date = order_date
            if customer:
                existing_so.customer_id = customer.id
            existing_so.updated_by_user_id = u.id
            
            # Delete old lines and recreate
            for old_line in list(existing_so.lines):
                s.delete(old_line)
            # Delete old attachments for this order
            old_atts = s.query(OrderPdfAttachment).filter(OrderPdfAttachment.sales_order_id == existing_so.id).all()
            storage = storage_from_config(current_app.config)
            for att in old_atts:
                try:
                    storage.delete(att.storage_key)
                except Exception:
                    pass
                s.delete(att)
            
            sales_order = existing_so
        else:
            sales_order = SalesOrder(
                order_number=order_number,
                order_date=order_date,
                ship_date=order_date,
                customer_id=customer.id if customer else None,
                source="pdf_import",
                external_key=f"pdf:{order_number}",
                status="completed",
                created_by_user_id=u.id,
                updated_by_user_id=u.id,
            )
            s.add(sales_order)
            s.flush()
        
        # Create order lines
        for line_num, line_data in enumerate(parsed_order.get("lines", []), start=1):
            sku = line_data.get("sku")
            quantity = line_data.get("quantity")
            if not sku or not quantity or int(quantity) <= 0:
                continue
            s.add(SalesOrderLine(
                sales_order_id=sales_order.id,
                sku=sku, quantity=quantity,
                lot_number=None, line_number=line_num,
            ))
        
        # Store the PDF attachment linked to the SalesOrder
        _store_pdf_attachment(
            s,
            pdf_bytes=pdf_bytes,
            filename=f"SO_{order_number}.pdf",
            pdf_type="sales_order_page",
            sales_order_id=sales_order.id,
            distribution_entry_id=entry_id,
            user=u,
            order_number=order_number,
        )
        
        # Link THIS distribution (and siblings with same order) to the SalesOrder
        dist_order_norm = normalize_order_number(entry.order_number)
        so_order_norm = normalize_order_number(order_number)
        if dist_order_norm and so_order_norm and dist_order_norm == so_order_norm:
            entry.sales_order_id = sales_order.id
            if customer:
                entry.customer_id = customer.id
                entry.facility_name = customer.facility_name
            # Also link sibling distributions with the same order number
            siblings = (
                s.query(DistributionLogEntry)
                .filter(
                    DistributionLogEntry.id != entry.id,
                    DistributionLogEntry.sales_order_id.is_(None),
                )
                .all()
            )
            for sib in siblings:
                sib_norm = normalize_order_number(sib.order_number)
                if sib_norm == so_order_norm:
                    sib.sales_order_id = sales_order.id
                    if customer:
                        sib.customer_id = customer.id
                        sib.facility_name = customer.facility_name
        
        s.commit()
        flash(f"Sales order {order_number} created/updated and linked.", "success")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
    
    # ── Fallback: store as generic attachment ──
    timestamp = utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(pdf_file.filename) or "document.pdf"
    storage_key = f"distributions/{entry_id}/pdfs/manual_{timestamp}_{safe_name}"
    
    storage = storage_from_config(current_app.config)
    try:
        storage.put_bytes(storage_key, pdf_bytes, content_type="application/pdf")
    except Exception as e:
        flash(f"Storage error: {e}", "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
    
    attachment = OrderPdfAttachment(
        sales_order_id=entry.sales_order_id,
        distribution_entry_id=entry_id,
        storage_key=storage_key,
        filename=pdf_file.filename,
        pdf_type="manual_upload",
        uploaded_by_user_id=u.id,
    )
    s.add(attachment)
    s.commit()
    
    flash(f"PDF '{pdf_file.filename}' uploaded (not recognized as a sales order).", "info")
    return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))


@bp.get("/pdf-attachments/<int:attachment_id>/download")
@require_permission("distribution_log.view")
def download_pdf_attachment(attachment_id: int):
    """Download a PDF attachment."""
    import io
    
    s = db_session()
    attachment = s.query(OrderPdfAttachment).filter(OrderPdfAttachment.id == attachment_id).one_or_none()
    if not attachment:
        flash("Attachment not found.", "danger")
        return redirect(request.referrer or url_for("rep_traceability.distribution_log_list"))
    
    storage = storage_from_config(current_app.config)
    try:
        pdf_bytes = storage.get_bytes(attachment.storage_key)
    except Exception:
        flash("PDF not found in storage.", "danger")
        return redirect(request.referrer or url_for("rep_traceability.distribution_log_list"))
    
    return send_file(
        io.BytesIO(pdf_bytes),
        download_name=attachment.filename,
        as_attachment=True,
        mimetype="application/pdf",
    )


@bp.get("/pdf-attachments/<int:attachment_id>/view")
@require_permission("distribution_log.view")
def view_pdf_attachment(attachment_id: int):
    """View a PDF attachment inline when supported."""
    s = db_session()
    attachment = s.query(OrderPdfAttachment).filter(OrderPdfAttachment.id == attachment_id).one_or_none()
    if not attachment:
        flash("Attachment not found.", "danger")
        return redirect(request.referrer or url_for("rep_traceability.distribution_log_list"))

    storage = storage_from_config(current_app.config)
    try:
        fobj = storage.open(attachment.storage_key)
    except Exception:
        flash("PDF not found in storage.", "danger")
        return redirect(request.referrer or url_for("rep_traceability.distribution_log_list"))

    inline = allow_inline_view(attachment.filename, "application/pdf")
    return send_file(
        fobj,
        download_name=attachment.filename,
        as_attachment=not inline,
        mimetype="application/pdf",
    )


@bp.get("/distribution-log/entry-details/<int:entry_id>")
@require_permission("distribution_log.view")
def distribution_log_entry_details(entry_id: int):
    """Return JSON with entry details for in-page modal."""
    from flask import jsonify, url_for
    from sqlalchemy import func
    from app.eqms.modules.rep_traceability.models import SalesOrder, DistributionLine
    import os
    
    s = db_session()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    
    # Apply LotLog corrections for display
    corrected_lot = entry.lot_number
    lines_data: list[dict[str, Any]] = []
    try:
        from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory, normalize_lot, resolve_lotlog_path
        lotlog_path = resolve_lotlog_path()
        _, lot_corrections, _, _ = load_lot_log_with_inventory(lotlog_path)
        raw_lot = (entry.lot_number or "").strip()
        if raw_lot:
            normalized = normalize_lot(raw_lot)
            corrected_lot = lot_corrections.get(normalized, normalized)
        entry_lines = (
            s.query(DistributionLine)
            .filter(DistributionLine.distribution_entry_id == entry.id)
            .order_by(DistributionLine.id.asc())
            .all()
        )
        for line in entry_lines:
            line_lot = (line.lot_number or "").strip()
            corrected_line_lot = line_lot
            if line_lot:
                normalized_line = normalize_lot(line_lot)
                corrected_line_lot = lot_corrections.get(normalized_line, normalized_line)
            lines_data.append(
                {
                    "sku": line.sku,
                    "lot_number": line.lot_number,
                    "lot_corrected": corrected_line_lot,
                    "quantity": int(line.quantity or 0),
                }
            )
    except Exception:
        pass  # Graceful fallback if LotLog unavailable
    if not lines_data:
        entry_lines = (
            s.query(DistributionLine)
            .filter(DistributionLine.distribution_entry_id == entry.id)
            .order_by(DistributionLine.id.asc())
            .all()
        )
        for line in entry_lines:
            lines_data.append(
                {
                    "sku": line.sku,
                    "lot_number": line.lot_number,
                    "lot_corrected": line.lot_number,
                    "quantity": int(line.quantity or 0),
                }
            )
    
    # Get linked sales order if exists
    order_data = None
    if entry.sales_order_id:
        order = s.get(SalesOrder, entry.sales_order_id)
        if order:
            order_data = {
                "order_number": order.order_number,
                "order_date": str(order.order_date) if order.order_date else None,
                "ship_date": str(order.ship_date) if order.ship_date else None,
                "status": order.status,
            }
    
    # Get attachments linked to EITHER sales_order OR distribution entry
    # This ensures both SO-level PDFs and distribution-level labels are shown
    from sqlalchemy import or_
    attachment_filters = []
    if entry.sales_order_id:
        attachment_filters.append(OrderPdfAttachment.sales_order_id == entry.sales_order_id)
    attachment_filters.append(OrderPdfAttachment.distribution_entry_id == entry.id)
    
    attachments = (
        s.query(OrderPdfAttachment)
        .filter(or_(*attachment_filters))
        .order_by(OrderPdfAttachment.uploaded_at.desc())
        .limit(20)
        .all()
    )
    
    # Get customer data and stats
    customer_data = None
    customer_stats = None
    notes_data = []
    if entry.customer_id:
        from app.eqms.modules.customer_profiles.models import Customer, CustomerRep
        from app.eqms.modules.customer_profiles.models import CustomerNote
        customer = s.get(Customer, entry.customer_id)
        if customer:
            customer_data = {
                "id": customer.id,
                "facility_name": customer.facility_name,
                "city": customer.city,
                "state": customer.state,
            }
            # Assigned reps
            rep_rows = (
                s.query(CustomerRep)
                .filter(CustomerRep.customer_id == customer.id)
                .all()
            )
            assigned_reps = [
                (r.rep.name if r.rep else str(r.rep_id)) for r in rep_rows
            ]
            
            # Calculate customer stats - ONLY from matched distributions
            customer_entries = (
                s.query(DistributionLogEntry)
                .filter(
                    DistributionLogEntry.customer_id == customer.id,
                    DistributionLogEntry.sales_order_id.isnot(None)  # Only matched
                )
                .all()
            )
            customer_lines = (
                s.query(DistributionLine, DistributionLogEntry.ship_date)
                .join(DistributionLogEntry, DistributionLogEntry.id == DistributionLine.distribution_entry_id)
                .filter(
                    DistributionLogEntry.customer_id == customer.id,
                    DistributionLogEntry.sales_order_id.isnot(None),
                )
                .order_by(DistributionLogEntry.ship_date.desc(), DistributionLine.id.desc())
                .all()
            )
            
            if customer_entries:
                first_order = min(e.ship_date for e in customer_entries if e.ship_date)
                last_order = max(e.ship_date for e in customer_entries if e.ship_date)
                total_orders = len({e.order_number for e in customer_entries if e.order_number})
                if customer_lines:
                    total_units = sum(int(line.quantity or 0) for line, _ in customer_lines)
                else:
                    total_units = sum(int(e.quantity or 0) for e in customer_entries)
                
                # Top SKUs
                sku_totals: dict[str, int] = {}
                if customer_lines:
                    for line, _ in customer_lines:
                        if line.sku:
                            sku_totals[line.sku] = sku_totals.get(line.sku, 0) + int(line.quantity or 0)
                else:
                    for e in customer_entries:
                        if e.sku:
                            sku_totals[e.sku] = sku_totals.get(e.sku, 0) + int(e.quantity or 0)
                top_skus = sorted(sku_totals.items(), key=lambda kv: kv[1], reverse=True)[:5]
                
                # Recent lots (unique)
                if customer_lines:
                    recent_lots = list(dict.fromkeys(
                        line.lot_number for line, _ in customer_lines if line.lot_number
                    ))[:5]
                else:
                    recent_lots = list(dict.fromkeys(
                        e.lot_number for e in sorted(customer_entries, key=lambda x: x.ship_date or date.min, reverse=True)
                        if e.lot_number
                    ))[:5]
                
                customer_stats = {
                    "first_order": str(first_order) if first_order else None,
                    "last_order": str(last_order) if last_order else None,
                    "total_orders": total_orders,
                    "total_units": total_units,
                    "top_skus": [{"sku": sku, "units": units} for sku, units in top_skus],
                    "recent_lots": recent_lots,
                    "assigned_reps": assigned_reps,
                }
            
            # Latest notes for customer
            notes = (
                s.query(CustomerNote)
                .filter(CustomerNote.customer_id == customer.id)
                .order_by(CustomerNote.created_at.desc())
                .limit(10)
                .all()
            )
            notes_data = [
                {
                    "id": n.id,
                    "note_text": n.note_text,
                    "note_date": str(n.note_date) if n.note_date else None,
                    "author": n.author,
                    "created_at": str(n.created_at) if n.created_at else None,
                }
                for n in notes
            ]

    # Audit info (created/updated by)
    from app.eqms.models import User
    created_by = s.get(User, entry.created_by_user_id) if entry.created_by_user_id else None
    updated_by = s.get(User, entry.updated_by_user_id) if entry.updated_by_user_id else None
    
    return jsonify({
        "entry": {
            "id": entry.id,
            "ship_date": str(entry.ship_date) if entry.ship_date else None,
            "order_number": entry.order_number,
            "facility_name": entry.facility_name,
            "sku": entry.sku,
            "lot_number": corrected_lot,  # Display-time corrected lot name
            "quantity": entry.quantity,
            "source": entry.source,
            "customer_id": entry.customer_id,
            "has_sales_order": entry.sales_order_id is not None,
            "sales_order_id": entry.sales_order_id,
            "rep_id": entry.rep_id,
            "rep_name": entry.rep_name,
            "address1": entry.address1,
            "address2": entry.address2,
            "city": entry.city,
            "state": entry.state,
            "zip": entry.zip,
            "country": entry.country,
            "contact_name": entry.contact_name,
            "contact_phone": entry.contact_phone,
            "contact_email": entry.contact_email,
            "tracking_number": entry.tracking_number,
            "created_at": str(entry.created_at) if entry.created_at else None,
            "updated_at": str(entry.updated_at) if entry.updated_at else None,
            "created_by": created_by.email if created_by else None,
            "updated_by": updated_by.email if updated_by else None,
        },
        "lines": lines_data,
        "order": order_data,
        "customer": customer_data,
        "customer_stats": customer_stats,
        "attachments": [
            {
                "id": a.id,
                "filename": a.filename,
                "pdf_type": a.pdf_type,
                "uploaded_at": str(a.uploaded_at) if a.uploaded_at else None,
                "download_url": url_for(
                    "rep_traceability.distribution_log_attachment_download",
                    attachment_id=a.id,
                    entry_id=entry.id,
                ),
            }
            for a in attachments
        ],
        "notes": notes_data,
    })


@bp.post("/distribution-log/<int:entry_id>/upload-pdf")
@require_permission("distribution_log.edit")
def distribution_log_upload_pdf(entry_id: int):
    """
    Upload PDF to match an unmatched distribution entry.
    Creates or matches a sales order and links it to the distribution.
    """
    from flask import jsonify
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine, OrderPdfAttachment
    from app.eqms.audit import record_event
    
    s = db_session()
    u = _current_user()
    
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        flash("Distribution entry not found.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))
    
    f = request.files.get("pdf_file")
    if not f or not f.filename:
        flash("Please select a PDF file to upload.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))
    
    pdf_bytes = f.read()
    filename = f.filename or "upload.pdf"
    
    # Try to parse the PDF
    parsed_orders = []
    try:
        from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf
        result = parse_sales_orders_pdf(pdf_bytes)
        parsed_orders = result.orders
        if result.errors:
            current_app.logger.warning(
                "PDF parse errors for distribution %s: %s",
                entry_id,
                "; ".join([f"Page {e.row_index}: {e.message}" for e in result.errors[:5]]),
            )
    except Exception as e:
        current_app.logger.warning(f"PDF parse failed for distribution {entry_id}: {e}")
    
    order = None
    if parsed_orders:
        # Use first parsed order
        po = parsed_orders[0]
        # Check if order already exists
        existing = (
            s.query(SalesOrder)
            .filter(SalesOrder.order_number == po.get("order_number", entry.order_number))
            .first()
        )
        if existing:
            order = existing
            # Linked SO owns the distribution customer
            if order.customer_id:
                entry.customer_id = order.customer_id
        else:
            # Determine customer_id - create customer if needed
            customer_id = entry.customer_id
            if not customer_id:
                # Try to create customer from parsed data or entry facility_name
                customer_name = (
                    po.get("customer_name") or 
                    entry.facility_name or 
                    entry.customer_name or 
                    "UNKNOWN"
                )
                try:
                    customer = find_or_create_customer(
                        s,
                        facility_name=customer_name,
                        customer_code=po.get("customer_code"),
                        address1=entry.address1,
                        city=entry.city,
                        state=entry.state,
                        zip=entry.zip,
                    )
                    customer_id = customer.id
                    entry.customer_id = customer_id  # Link distribution to customer
                except Exception as e:
                    current_app.logger.warning(f"Failed to create customer for distribution {entry_id}: {e}")
            
            if customer_id:
                # Create new sales order
                order = SalesOrder(
                    order_number=po.get("order_number", entry.order_number),
                    order_date=po.get("order_date") or entry.ship_date,
                    ship_date=po.get("ship_date") or entry.ship_date,
                    customer_id=customer_id,
                    source="pdf_import",
                    status="shipped",
                    created_by_user_id=u.id,
                )
                s.add(order)
                s.flush()
                
                # Create lines from parsed data or entry data
                lines = po.get("lines", [])
                if not lines:
                    lines = [{"sku": entry.sku, "quantity": entry.quantity, "lot_number": entry.lot_number}]
                for line_data in lines:
                    if not line_data.get("sku") or not line_data.get("quantity") or int(line_data.get("quantity") or 0) <= 0:
                        continue
                    line = SalesOrderLine(
                        sales_order_id=order.id,
                        sku=line_data.get("sku", entry.sku),
                        quantity=line_data.get("quantity", entry.quantity),
                        lot_number=line_data.get("lot_number", entry.lot_number),
                    )
                    s.add(line)
    else:
        # No parse result - create minimal order from entry data
        existing = (
            s.query(SalesOrder)
            .filter(SalesOrder.order_number == entry.order_number)
            .first()
        )
        if existing:
            order = existing
            # Linked SO owns the distribution customer
            if order.customer_id:
                entry.customer_id = order.customer_id
        else:
            # Determine customer_id - create customer if needed
            customer_id = entry.customer_id
            if not customer_id:
                customer_name = entry.facility_name or entry.customer_name or "UNKNOWN"
                try:
                    customer = find_or_create_customer(
                        s,
                        facility_name=customer_name,
                        customer_code=po.get("customer_code"),
                        address1=entry.address1,
                        city=entry.city,
                        state=entry.state,
                        zip=entry.zip,
                    )
                    customer_id = customer.id
                    entry.customer_id = customer_id  # Link distribution to customer
                except Exception as e:
                    current_app.logger.warning(f"Failed to create customer for distribution {entry_id}: {e}")
            
            if customer_id:
                order = SalesOrder(
                    order_number=entry.order_number,
                    order_date=entry.ship_date,
                    ship_date=entry.ship_date,
                    customer_id=customer_id,
                    source="pdf_import",
                    status="shipped",
                    created_by_user_id=u.id,
                )
                s.add(order)
                s.flush()
                
                line = SalesOrderLine(
                    sales_order_id=order.id,
                    sku=entry.sku,
                    quantity=entry.quantity,
                    lot_number=entry.lot_number,
                )
                s.add(line)
    
    # Link distribution to order
    if order:
        entry.sales_order_id = order.id
        
        # Store PDF attachment (Sales Order slot)
        _store_pdf_attachment(
            s,
            pdf_bytes=pdf_bytes,
            filename=filename,
            pdf_type="sales_order",
            sales_order_id=order.id,
            distribution_entry_id=entry.id,
            user=u,
        )
        
        from app.eqms.audit import record_event
        record_event(
            s,
            actor=u,
            action="distribution_log_entry.match_order",
            entity_type="DistributionLogEntry",
            entity_id=str(entry.id),
            metadata={"sales_order_id": order.id},
        )
        
        s.commit()
        flash(f"Distribution matched to sales order #{order.order_number}.", "success")
    else:
        # Just store PDF without linking (no customer_id to create order)
        _store_pdf_attachment(
            s,
            pdf_bytes=pdf_bytes,
            filename=filename,
            pdf_type="sales_order",
            sales_order_id=None,
            distribution_entry_id=entry.id,
            user=u,
        )
        s.commit()
        flash("PDF stored but could not create sales order (missing customer).", "warning")
    
    return redirect(url_for("rep_traceability.distribution_log_list"))


@bp.post("/distribution-log/<int:entry_id>/upload-packing-slip")
@require_permission("distribution_log.edit")
def distribution_log_upload_packing_slip(entry_id: int):
    """
    Upload packing slip PDF to a distribution entry.
    Replaces any prior packing slip attachment for this distribution.
    """
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()

    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        flash("Distribution entry not found.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))

    f = request.files.get("label_file") or request.files.get("packing_slip_file")
    if not f or not f.filename:
        flash("Please select a packing slip PDF file to upload.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))

    pdf_bytes = f.read()
    filename = f.filename or "packing-slip.pdf"

    _delete_packing_slip_attachments_for_distribution(s, entry.id)
    _store_pdf_attachment(
        s,
        pdf_bytes=pdf_bytes,
        filename=filename,
        pdf_type="packing_slip",
        sales_order_id=entry.sales_order_id,
        distribution_entry_id=entry.id,
        user=u,
        order_number=entry.order_number or None,
    )

    record_event(
        s,
        actor=u,
        action="distribution_log_entry.upload_packing_slip",
        entity_type="DistributionLogEntry",
        entity_id=str(entry.id),
        metadata={"filename": filename},
    )

    s.commit()
    flash(f"Packing slip PDF '{filename}' uploaded and linked to distribution.", "success")

    return redirect(url_for("rep_traceability.distribution_log_list"))


@bp.get("/distribution-log/import-csv")
@require_permission("distribution_log.import")
def distribution_log_import_csv_get():
    return redirect(url_for("rep_traceability.distribution_log_import_get"))


@bp.get("/distribution-log/import")
@require_permission("distribution_log.import")
def distribution_log_import_get():
    return render_template("admin/distribution_log/import.html", mode="csv")


@bp.post("/distribution-log/import-csv")
@require_permission("distribution_log.import")
def distribution_log_import_csv_post():
    s = db_session()
    u = _current_user()

    f = request.files.get("csv_file")
    if not f or not f.filename:
        flash("Choose a CSV file to import.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_import_csv_get"))

    # Load lot corrections for CSV import (same as ShipStation sync)
    from app.eqms.modules.shipstation_sync.parsers import load_lot_log, resolve_lotlog_path
    lotlog_path = resolve_lotlog_path()
    _lot_to_sku, lot_corrections = load_lot_log(lotlog_path)

    rows, errors = parse_distribution_csv(f.read(), lot_corrections=lot_corrections)

    created = 0
    duplicates = 0
    duplicates_sample: list[dict] = []
    for r in rows:
        # Lookup-only: find existing customer by facility_name (canonical pipeline compliance).
        # CSV import does NOT create new customers - customers are only created through SO/PDF import.
        # If no match, leave customer_id = None; distribution will be unmatched until SO is imported.
        facility_name = normalize_text(r.get("facility_name"))
        if facility_name:
            from app.eqms.modules.customer_profiles.utils import canonical_customer_key
            ck = canonical_customer_key(facility_name)
            c = s.query(Customer).filter(Customer.company_key == ck).one_or_none() if ck else None
            if c:
                r["customer_id"] = c.id
                r["customer_name"] = c.facility_name
                r["facility_name"] = c.facility_name
            else:
                # No existing customer found - leave unlinked
                r["customer_id"] = None
                r["customer_name"] = None
                # Keep original facility_name for reference
        ship_date: date = r["ship_date"]
        dupe = check_duplicate_manual_csv(
            s,
            order_number=r.get("order_number") or "",
            ship_date=ship_date,
            facility_name=r.get("facility_name") or "",
            sku=r.get("sku") or "",
            lot_number=r.get("lot_number") or "",
        )
        if dupe:
            duplicates += 1
            if len(duplicates_sample) < 25:
                duplicates_sample.append(
                    {
                        "ship_date": str(ship_date),
                        "order_number": r.get("order_number") or "",
                        "facility_name": r.get("facility_name") or "",
                        "sku": r.get("sku") or "",
                        "lot_number": r.get("lot_number") or "",
                    }
                )
            # P0 requirement: skip duplicates and report them
            continue
        create_distribution_entry(s, r, user=u, source_default="csv_import")
        created += 1

    # Single audit event summarizing the import
    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="distribution_log_entry.import_csv",
        entity_type="DistributionLogEntry",
        entity_id="bulk",
        metadata={
            "filename": f.filename,
            "rows_processed": len(rows),
            "rows_created": created,
            "rows_errors": len(errors),
            "rows_duplicates": duplicates,
        },
    )

    s.commit()

    if errors:
        flash(f"CSV import completed with {len(errors)} errors; created {created}, duplicates {duplicates}.", "danger")
        return render_template("admin/distribution_log/import.html", mode="csv", errors=errors, duplicates=duplicates_sample)

    flash(f"CSV import completed: created {created}, duplicates {duplicates}.", "success")
    if duplicates:
        # show duplicates on the import page so user can review
        return render_template("admin/distribution_log/import.html", mode="csv", duplicates=duplicates_sample)
    return redirect(url_for("rep_traceability.distribution_log_list"))


@bp.get("/distribution-log/import-pdf")
@require_permission("distribution_log.import")
def distribution_log_import_pdf_get():
    """Redirect to consolidated Sales Orders PDF import."""
    return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))


@bp.post("/distribution-log/import-pdf")
@require_permission("distribution_log.import")
def distribution_log_import_pdf_post():
    """Redirect POST to consolidated Sales Orders PDF import.
    
    Note: This redirect won't preserve the file upload, but since GET also redirects,
    users should never hit this route directly - they'll already be on sales-orders.
    """
    return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))


@bp.get("/distribution-log/export")
@require_permission("distribution_log.export")
def distribution_log_export():
    s = db_session()
    u = _current_user()

    filters = _parse_filters()
    q = query_distribution_entries(s, filters=filters)
    entries = q.order_by(DistributionLogEntry.ship_date.asc(), DistributionLogEntry.id.asc()).all()

    out = io.StringIO()
    w = csv.writer(out)
    header = [
        "Ship Date",
        "Order #",
        "Facility",
        "City",
        "State",
        "Rep",
        "Source",
        "tracking_number",
        "ss_shipment_id",
        "sales_order_id",
        "sku_1",
        "lot_1",
        "qty_1",
        "sku_2",
        "lot_2",
        "qty_2",
        "sku_3",
        "lot_3",
        "qty_3",
        "line_quantity_total",
        "overflow_lines",
    ]
    w.writerow(header)
    for e in entries:
        facility = e.customer.facility_name if getattr(e, "customer", None) else e.facility_name
        lines = sorted(e.lines or [], key=lambda ln: ln.id)
        if not lines:
            slots = [(e.sku, e.lot_number, e.quantity)]
            line_total = int(e.quantity or 0)
        else:
            slots = [(ln.sku, ln.lot_number, ln.quantity) for ln in lines]
            line_total = sum(int(ln.quantity or 0) for ln in lines)
        overflow = ""
        if len(slots) > 3:
            overflow = "; ".join(f"{sku}/{lot}/{qty}" for sku, lot, qty in slots[3:])
            slots = slots[:3]
        while len(slots) < 3:
            slots.append(("", "", ""))
        w.writerow(
            [
                str(e.ship_date),
                e.order_number,
                facility,
                e.city or "",
                e.state or "",
                e.rep_name or (str(e.rep_id) if e.rep_id else ""),
                e.source,
                e.tracking_number or "",
                e.ss_shipment_id or "",
                e.sales_order_id or "",
                slots[0][0],
                slots[0][1],
                slots[0][2],
                slots[1][0],
                slots[1][1],
                slots[1][2],
                slots[2][0],
                slots[2][1],
                slots[2][2],
                line_total,
                overflow,
            ]
        )

    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="distribution_log_entry.export",
        entity_type="DistributionLogEntry",
        entity_id="export",
        metadata={"filters": filters, "row_count": len(entries)},
    )
    s.commit()

    data = out.getvalue().encode("utf-8")
    filename = f"distribution_log_export_{date.today().strftime('%Y%m%d')}.csv"
    return send_file(
        io.BytesIO(data),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


# Tracing Reports + approvals are implemented in later commits.
# Keep these stub routes so navigation and templates can resolve url_for() safely.


@bp.get("/tracing")
@require_permission("tracing_reports.view")
def tracing_list():
    s = db_session()
    reports = s.query(TracingReport).order_by(TracingReport.generated_at.desc(), TracingReport.id.desc()).limit(200).all()
    return render_template("admin/tracing/list.html", reports=reports)


@bp.get("/tracing/generate")
@require_permission("tracing_reports.generate")
def tracing_generate_get():
    s = db_session()
    from app.eqms.modules.customer_profiles.models import Rep
    reps = s.query(Rep).filter(Rep.is_active.is_(True)).order_by(Rep.name.asc()).all()
    return render_template("admin/tracing/generate.html", reps=reps)


@bp.post("/tracing/generate")
@require_permission("tracing_reports.generate")
def tracing_generate_post():
    s = db_session()
    u = _current_user()
    f = parse_tracing_filters(request.form)
    month = normalize_text(f.get("month"))

    if not month:
        flash("Month is required (YYYY-MM).", "danger")
        return redirect(url_for("rep_traceability.tracing_generate_get"))

    try:
        tr = generate_tracing_report_csv(
            s,
            user=u,
            filters=f,
            app_config=current_app.config,
        )
        s.commit()
    except Exception as e:
        s.rollback()
        flash(f"Failed to generate report: {e}", "danger")
        return redirect(url_for("rep_traceability.tracing_generate_get"))

    flash("Tracing report generated.", "success")
    return redirect(url_for("rep_traceability.tracing_detail", report_id=tr.id))


@bp.get("/tracing/<int:report_id>")
@require_permission("tracing_reports.view")
def tracing_detail(report_id: int):
    s = db_session()
    r = s.get(TracingReport, report_id)
    if not r:
        from flask import abort

        abort(404)
    approvals = (
        s.query(ApprovalEml)
        .filter(ApprovalEml.report_id == r.id)
        .order_by(ApprovalEml.uploaded_at.desc(), ApprovalEml.id.desc())
        .all()
    )
    return render_template("admin/tracing/detail.html", report=r, approvals=approvals)


@bp.get("/tracing/<int:report_id>/download")
@require_permission("tracing_reports.download")
def tracing_download(report_id: int):
    s = db_session()
    u = _current_user()
    r = s.get(TracingReport, report_id)
    if not r:
        from flask import abort

        abort(404)

    storage = storage_from_config(current_app.config)
    fobj = storage.open(r.report_storage_key)

    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="tracing_report.download",
        entity_type="TracingReport",
        entity_id=str(r.id),
        metadata={"storage_key": r.report_storage_key},
    )
    s.commit()

    filename = f"tracing_report_{r.id}.csv"
    return send_file(fobj, mimetype="text/csv", as_attachment=True, download_name=filename, max_age=0)


@bp.post("/tracing/<int:report_id>/approvals/upload")
@require_permission("approvals.upload")
def approval_upload(report_id: int):
    s = db_session()
    u = _current_user()
    r = s.get(TracingReport, report_id)
    if not r:
        from flask import abort

        abort(404)

    f = request.files.get("eml_file")
    if not f or not f.filename:
        flash("Choose an .eml file to upload.", "danger")
        return redirect(url_for("rep_traceability.tracing_detail", report_id=report_id))

    notes = request.form.get("notes")
    upload_approval_eml(
        s,
        report=r,
        eml_bytes=f.read(),
        filename=f.filename,
        user=u,
        notes=notes,
        app_config=current_app.config,
    )
    s.commit()
    flash("Approval evidence uploaded.", "success")
    return redirect(url_for("rep_traceability.tracing_detail", report_id=report_id))


@bp.get("/approvals/<int:approval_id>/download")
@require_permission("approvals.download")
def approval_download(approval_id: int):
    s = db_session()
    u = _current_user()
    a = s.get(ApprovalEml, approval_id)
    if not a:
        from flask import abort

        abort(404)

    storage = storage_from_config(current_app.config)
    fobj = storage.open(a.storage_key)

    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="approval_eml.download",
        entity_type="ApprovalEml",
        entity_id=str(a.id),
        metadata={"storage_key": a.storage_key, "report_id": a.report_id},
    )
    s.commit()

    filename = a.original_filename or f"approval_{a.id}.eml"
    return send_file(fobj, mimetype="message/rfc822", as_attachment=True, download_name=filename, max_age=0)


@bp.get("/sales-dashboard")
@require_permission("sales_dashboard.view")
def sales_dashboard():
    s = db_session()
    u = _current_user()

    # F-025: Default to Jan 1 of the current year instead of a hardcoded date
    _default_start = f"{date.today().year}-01-01"
    start_date_s = normalize_text(request.args.get("start_date")) or _default_start
    try:
        start_date = date.fromisoformat(start_date_s)
    except Exception:
        flash("Invalid start_date. Use YYYY-MM-DD.", "danger")
        return redirect(url_for("rep_traceability.sales_dashboard"))

    end_date_s = normalize_text(request.args.get("end_date")) or None
    end_date = None
    if end_date_s:
        try:
            end_date = date.fromisoformat(end_date_s)
        except Exception:
            flash("Invalid end_date. Use YYYY-MM-DD.", "danger")
            return redirect(url_for("rep_traceability.sales_dashboard"))

    try:
        data = compute_sales_dashboard(s, start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.error("Sales dashboard computation failed: %s", e, exc_info=True)
        data = {
            "stats": {
                "total_orders": 0,
                "total_units_all_time": 0,
                "total_units_window": 0,
                "total_customers": 0,
                "first_time_customers": 0,
                "repeat_customers": 0,
            },
            "sku_breakdown": [],
            "sku_breakdown_alltime": [],
            "lot_tracking": [],
            "active_lot_tracking": [],
            "sku_lot_summary": [],
            "lotlog_missing": False,
            "disposition_log_missing": False,
            "recent_orders_new": [],
            "recent_orders_repeat": [],
        }
        flash("Error loading dashboard data. Some statistics may be incomplete.", "danger")

    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="sales_dashboard.view",
        entity_type="SalesDashboard",
        entity_id="view",
        metadata={"start_date": str(start_date), "end_date": str(end_date) if end_date else ""},
    )
    s.commit()

    return render_template(
        "admin/sales_dashboard/index.html",
        start_date=str(start_date),
        end_date=str(end_date) if end_date else "",
        stats=data["stats"],
        sku_breakdown=data["sku_breakdown"],
        sku_breakdown_alltime=data.get("sku_breakdown_alltime") or data["sku_breakdown"],
        lot_tracking=data["lot_tracking"],
        active_lot_tracking=data.get("active_lot_tracking") or data["lot_tracking"],
        sku_lot_summary=data.get("sku_lot_summary") or [],
        lotlog_missing=bool(data.get("lotlog_missing")),
        disposition_log_missing=bool(data.get("disposition_log_missing")),
        recent_orders_new=data.get("recent_orders_new") or [],
        recent_orders_repeat=data.get("recent_orders_repeat") or [],
    )




@bp.get("/notes/modal/<entity_type>/<int:entity_id>")
@require_permission("customers.notes")
def notes_modal(entity_type: str, entity_id: int):
    """Return HTML for notes modal content (AJAX)."""
    s = db_session()
    from app.eqms.modules.customer_profiles.models import CustomerNote
    from app.eqms.modules.rep_traceability.models import SalesOrder

    customer_id = None
    if entity_type == "customer":
        customer_id = entity_id
    elif entity_type == "order":
        order = s.get(SalesOrder, entity_id)
        customer_id = order.customer_id if order else None
    elif entity_type == "distribution":
        entry = s.get(DistributionLogEntry, entity_id)
        customer_id = entry.customer_id if entry else None

    notes = []
    if customer_id:
        notes = (
            s.query(CustomerNote)
            .filter(CustomerNote.customer_id == customer_id)
            .order_by(CustomerNote.created_at.desc())
            .limit(50)
            .all()
        )

    return render_template(
        "admin/_notes_modal_content.html",
        notes=notes,
        entity_type=entity_type,
        entity_id=entity_id,
        customer_id=customer_id,
    )


@bp.post("/notes/create")
@require_permission("customers.notes")
def notes_create():
    """Create note via AJAX and return JSON."""
    from flask import jsonify
    from app.eqms.modules.customer_profiles.models import CustomerNote
    from app.eqms.modules.customer_profiles.service import add_customer_note, get_customer_by_id
    from app.eqms.modules.rep_traceability.models import SalesOrder

    s = db_session()
    u = _current_user()
    payload = request.get_json(silent=True) or {}
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")
    note_text = (payload.get("note_text") or "").strip()
    note_date = payload.get("note_date")

    if not note_text or not entity_type or not entity_id:
        return jsonify({"error": "note_text, entity_type, entity_id required"}), 400
    
    # Validate entity_type (P2-1 improvement)
    VALID_ENTITY_TYPES = {"customer", "distribution", "sales_order", "order"}
    if entity_type not in VALID_ENTITY_TYPES:
        return jsonify({"error": f"Invalid entity_type. Must be one of: {sorted(VALID_ENTITY_TYPES)}"}), 400

    customer_id = None
    if entity_type == "customer":
        customer_id = int(entity_id)
    elif entity_type == "order":
        order = s.get(SalesOrder, int(entity_id))
        customer_id = order.customer_id if order else None
    elif entity_type == "distribution":
        entry = s.get(DistributionLogEntry, int(entity_id))
        customer_id = entry.customer_id if entry else None

    if not customer_id:
        return jsonify({"error": "Customer not found for note"}), 404

    customer = get_customer_by_id(s, int(customer_id))
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    note = add_customer_note(s, customer, note_text=note_text, note_date=note_date, user=u)
    note_count = s.query(CustomerNote).filter(CustomerNote.customer_id == customer.id).count()
    s.commit()

    return jsonify({"id": note.id, "note_count": note_count})


@bp.get("/notes/list/<entity_type>/<int:entity_id>")
@require_permission("customers.notes")
def notes_list(entity_type: str, entity_id: int):
    """Return notes list as JSON."""
    from flask import jsonify
    from app.eqms.modules.customer_profiles.models import CustomerNote
    from app.eqms.modules.rep_traceability.models import SalesOrder

    s = db_session()
    customer_id = None
    if entity_type == "customer":
        customer_id = entity_id
    elif entity_type == "order":
        order = s.get(SalesOrder, entity_id)
        customer_id = order.customer_id if order else None
    elif entity_type == "distribution":
        entry = s.get(DistributionLogEntry, entity_id)
        customer_id = entry.customer_id if entry else None

    notes = []
    if customer_id:
        notes = (
            s.query(CustomerNote)
            .filter(CustomerNote.customer_id == customer_id)
            .order_by(CustomerNote.created_at.desc())
            .limit(50)
            .all()
        )

    return jsonify({
        "notes": [
            {
                "id": n.id,
                "note_text": n.note_text,
                "note_date": str(n.note_date) if n.note_date else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ]
    })


@bp.get("/sales-dashboard/export")
@require_permission("sales_dashboard.export")
def sales_dashboard_export():
    s = db_session()
    u = _current_user()

    # F-025: Default to Jan 1 of the current year instead of a hardcoded date
    _default_start = f"{date.today().year}-01-01"
    start_date_s = normalize_text(request.args.get("start_date")) or _default_start
    try:
        start_date = date.fromisoformat(start_date_s)
    except Exception:
        flash("Invalid start_date. Use YYYY-MM-DD.", "danger")
        return redirect(url_for("rep_traceability.sales_dashboard"))

    end_date_s = normalize_text(request.args.get("end_date")) or None
    end_date = None
    if end_date_s:
        try:
            end_date = date.fromisoformat(end_date_s)
        except Exception:
            flash("Invalid end_date. Use YYYY-MM-DD.", "danger")
            return redirect(url_for("rep_traceability.sales_dashboard"))

    try:
        data = compute_sales_dashboard(s, start_date=start_date, end_date=end_date)
    except Exception as e:
        logger.error("Sales dashboard export failed: %s", e, exc_info=True)
        flash("Error exporting dashboard data. Please try again.", "danger")
        return redirect(url_for("rep_traceability.sales_dashboard"))
    window_entries = data["window_entries"]
    orders_by_customer = data["orders_by_customer"]
    customer_key_fn = data["customer_key_fn"]
    entry_line_totals = data["entry_line_totals"]
    lot_tracking = data.get("active_lot_tracking", data.get("lot_tracking", []))

    out = io.StringIO()
    w = csv.writer(out)

    # Build per-customer aggregates from window_entries
    from collections import defaultdict
    customer_units: dict[str, int] = defaultdict(int)
    customer_meta: dict[str, dict] = {}

    for e in window_entries:
        key = customer_key_fn(e.customer_id, e.facility_name, e.customer_name)
        if key == "k:":
            continue
        unit_count = entry_line_totals.get(e.id, int(e.quantity or 0))
        customer_units[key] += unit_count
        if key not in customer_meta:
            customer_meta[key] = {
                "facility_name": e.facility_name or e.customer_name or "",
                "city": e.city or "",
                "state": e.state or "",
                "customer_id": e.customer_id or "",
            }
        elif e.customer_id and not customer_meta[key]["customer_id"]:
            customer_meta[key]["customer_id"] = e.customer_id

    period_label = f"{start_date} to {end_date}" if end_date else f"{start_date} to present"

    w.writerow([
        "Customer Type",
        "Customer Key",
        "Facility",
        "City",
        "State",
        "Customer ID",
        f"Total Units ({period_label})",
        "Total Orders Lifetime",
    ])

    for key, meta in sorted(customer_meta.items(), key=lambda kv: kv[1]["facility_name"].lower()):
        lifetime_orders = len({o for o in orders_by_customer.get(key, set()) if o})
        cust_type = "First-Time" if lifetime_orders <= 1 else "Repeat"
        w.writerow([
            cust_type,
            key,
            meta["facility_name"],
            meta["city"],
            meta["state"],
            meta["customer_id"],
            customer_units[key],
            lifetime_orders,
        ])

    if lot_tracking:
        w.writerow([])
        w.writerow(["Lot Inventory (Active Lots with MFG/EXP Dates)"])
        w.writerow(["SKU", "Lot Name", "Mfg Date", "Exp Date", "Total Produced", "Total Consumed", "Remaining"])
        for row in lot_tracking:
            w.writerow(
                [
                    row.get("sku"),
                    row.get("lot"),
                    row.get("mfg_date", ""),
                    row.get("exp_date", ""),
                    row.get("total_produced"),
                    row.get("total_consumed", row.get("total_distributed")),
                    row.get("remaining"),
                ]
            )

    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="sales_dashboard.export",
        entity_type="SalesDashboard",
        entity_id="export",
        metadata={
            "start_date": str(start_date),
            "end_date": str(end_date) if end_date else "",
            "row_count": len(customer_meta),
        },
    )
    s.commit()

    data_bytes = out.getvalue().encode("utf-8")
    end_label = end_date.strftime("%Y%m%d") if end_date else "present"
    filename = f"sales_dashboard_{start_date.strftime('%Y%m%d')}_to_{end_label}.csv"
    return send_file(
        io.BytesIO(data_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )


# ============================================================================
# Sales Orders Routes (Source of Truth)
# ============================================================================

@bp.get("/sales-orders")
@require_permission("sales_orders.view")
def sales_orders_list():
    """List all sales orders with filters."""
    from app.eqms.modules.rep_traceability.models import SalesOrder
    
    s = db_session()
    page = int(request.args.get("page") or 1)
    per_page = 50
    
    # Filters
    source = normalize_text(request.args.get("source"))
    customer_id = request.args.get("customer_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    search = normalize_text(request.args.get("search"))
    status_filter = normalize_text(request.args.get("status")) or ""

    q = s.query(SalesOrder)

    if source:
        q = q.filter(SalesOrder.source == source)
    if customer_id:
        try:
            q = q.filter(SalesOrder.customer_id == int(customer_id))
        except ValueError:
            pass
    if start_date:
        try:
            q = q.filter(SalesOrder.order_date >= date.fromisoformat(start_date))
        except ValueError:
            pass
    if end_date:
        try:
            q = q.filter(SalesOrder.order_date <= date.fromisoformat(end_date))
        except ValueError:
            pass
    if search:
        q = q.filter(
            SalesOrder.order_number.ilike(f"%{search}%")
        )
    if status_filter:
        q = q.filter(SalesOrder.status == status_filter)

    total = q.count()
    orders = q.order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

    has_prev = page > 1
    has_next = page * per_page < total
    total_pages = (total + per_page - 1) // per_page

    # Filter options
    customers = _customers_for_select(s)

    return render_template(
        "admin/sales_orders/list.html",
        orders=orders,
        page=page,
        total=total,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        customers=customers,
        filters={
            "source": source or "",
            "customer_id": customer_id or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
            "search": search or "",
            "status": status_filter,
        },
    )


@bp.get("/sales-orders/<int:order_id>")
@require_permission("sales_orders.view")
def sales_order_detail(order_id: int):
    """View sales order detail with lines and distributions."""
    from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
    
    s = db_session()
    order = s.get(SalesOrder, order_id)
    if not order:
        from flask import abort
        abort(404)
    
    # Get distributions linked to this order
    distributions = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.sales_order_id == order_id)
        .order_by(DistributionLogEntry.ship_date.desc())
        .all()
    )

    pdf_attachments = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.sales_order_id == order_id)
        .order_by(OrderPdfAttachment.uploaded_at.desc(), OrderPdfAttachment.id.desc())
        .all()
    )
    
    return render_template(
        "admin/sales_orders/detail.html",
        order=order,
        distributions=distributions,
        pdf_attachments=pdf_attachments,
    )


@bp.post("/sales-orders/<int:order_id>/upload-pdf")
@require_permission("sales_orders.edit")
def sales_order_upload_pdf(order_id: int):
    from app.eqms.modules.rep_traceability.models import SalesOrder

    s = db_session()
    u = _current_user()
    order = s.get(SalesOrder, order_id)
    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_list"))

    f = request.files.get("pdf_file")
    if not f or not f.filename:
        flash("Choose a PDF to upload.", "danger")
        return redirect(url_for("rep_traceability.sales_order_detail", order_id=order_id))

    _store_pdf_attachment(
        s,
        pdf_bytes=f.read(),
        filename=f.filename,
        pdf_type="sales_order",
        sales_order_id=order.id,
        distribution_entry_id=None,
        user=u,
    )
    s.commit()
    flash("PDF uploaded.", "success")
    return redirect(url_for("rep_traceability.sales_order_detail", order_id=order_id))


@bp.get("/distribution-log/pdf/<int:attachment_id>/download")
@require_permission("distribution_log.view")
def distribution_log_attachment_download(attachment_id: int):
    """Download a PDF shown on the distribution entry modal (does not require sales_orders.view)."""
    from flask import abort

    entry_id = request.args.get("entry_id", type=int)
    if not entry_id:
        abort(400)

    s = db_session()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        abort(404)
    attachment = s.get(OrderPdfAttachment, attachment_id)
    if not attachment:
        abort(404)

    allowed = False
    if attachment.distribution_entry_id == entry.id:
        allowed = True
    elif (
        attachment.sales_order_id
        and entry.sales_order_id
        and attachment.sales_order_id == entry.sales_order_id
    ):
        allowed = True
    if not allowed:
        abort(404)

    storage = storage_from_config(current_app.config)
    fh = storage.open(attachment.storage_key)
    return send_file(
        fh,
        download_name=attachment.filename,
        as_attachment=True,
        mimetype="application/pdf",
    )


@bp.get("/sales-orders/pdf/<int:attachment_id>/download")
@require_permission("sales_orders.view")
def sales_order_pdf_download(attachment_id: int):
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment

    s = db_session()
    attachment = s.get(OrderPdfAttachment, attachment_id)
    if not attachment:
        from flask import abort
        abort(404)

    storage = storage_from_config(current_app.config)
    fh = storage.open(attachment.storage_key)
    return send_file(
        fh,
        download_name=attachment.filename,
        as_attachment=True,
        mimetype="application/pdf",
    )


@bp.get("/sales-orders/pdf/<int:attachment_id>/view")
@require_permission("sales_orders.view")
def sales_order_pdf_view(attachment_id: int):
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment

    s = db_session()
    attachment = s.get(OrderPdfAttachment, attachment_id)
    if not attachment:
        from flask import abort
        abort(404)

    storage = storage_from_config(current_app.config)
    fh = storage.open(attachment.storage_key)
    inline = allow_inline_view(attachment.filename, "application/pdf")
    return send_file(
        fh,
        download_name=attachment.filename,
        as_attachment=not inline,
        mimetype="application/pdf",
    )


@bp.post("/sales-orders/import-pdf-bulk")
@require_permission("sales_orders.import")
def sales_orders_import_pdf_bulk():
    """Bulk PDF import (multiple files) - splits each PDF into pages.
    
    Each page is parsed individually and stored as a separate attachment.
    Creates Sales Orders + Sales Order Lines only (NO distributions).
    
    File size limits:
    - 10MB per file
    - 50MB total across all files
    """
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
    from datetime import datetime
    
    s = db_session()
    u = _current_user()
    
    # Validate request has files
    files = request.files.getlist("pdf_files")
    if not files or not any(f.filename for f in files if f):
        flash("Please select one or more PDF files to upload.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    # Validate dependencies upfront
    try:
        from app.eqms.modules.rep_traceability.parsers.pdf import (
            PdfSplitError,
            parse_sales_orders_pdf,
            split_pdf_into_pages,
        )
    except ImportError as e:
        logger.error(f"PDF dependencies missing: {e}", exc_info=True)
        flash("PDF parsing libraries are not installed. Please contact support.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    # Validate file sizes before processing (10MB per file, 50MB total)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB
    total_upload_size = 0
    
    for f in files:
        if not f or not f.filename:
            continue
        # Check file size without reading entire file
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        f.seek(0)  # Reset to start
        
        if file_size > MAX_FILE_SIZE:
            flash(f"File '{f.filename}' is too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB per file.", "danger")
            return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
        
        total_upload_size += file_size
    
    if total_upload_size > MAX_TOTAL_SIZE:
        flash(f"Total upload size ({total_upload_size / 1024 / 1024:.1f}MB) exceeds maximum ({MAX_TOTAL_SIZE / 1024 / 1024:.0f}MB).", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))

    logger.info(f"Bulk PDF import started: {len([f for f in files if f and f.filename])} files, {total_upload_size / 1024 / 1024:.1f}MB total")

    total_pages = 0
    total_orders = 0
    total_updated = 0
    total_lines = 0
    total_unmatched = 0
    total_labels = 0
    parse_error_messages: list[str] = []
    
    total_errors = 0
    storage_errors = 0  # Track storage-specific failures
    stored_keys: list[str] = []

    def _store_and_track(*args, **kwargs):
        key = _store_pdf_attachment(*args, **kwargs)
        stored_keys.append(key)
        return key
    
    try:
        for f in files:
            if not f or not f.filename:
                continue
            
            original_filename = f.filename or "upload.pdf"
            
            # Read PDF bytes with error handling
            try:
                pdf_bytes = f.read()
            except Exception as e:
                logger.error(f"Failed to read PDF {original_filename}: {e}", exc_info=True)
                total_errors += 1
                continue
            
            # Validate PDF size (10MB limit)
            MAX_PDF_SIZE = 10 * 1024 * 1024  # 10MB
            if len(pdf_bytes) > MAX_PDF_SIZE:
                logger.warning(f"PDF too large: {original_filename} ({len(pdf_bytes)} bytes)")
                # Store as unparsed for manual review
                try:
                    _store_and_track(
                        s,
                        pdf_bytes=pdf_bytes,
                        filename=original_filename,
                        pdf_type="unparsed",
                        sales_order_id=None,
                        distribution_entry_id=None,
                        user=u,
                    )
                except Exception as e:
                    logger.error(f"Storage error storing oversized PDF {original_filename}: {e}")
                    storage_errors += 1
                total_errors += 1
                continue
            
            # Split PDF into individual pages with error handling
            try:
                pages = split_pdf_into_pages(pdf_bytes)
            except PdfSplitError as e:
                logger.error("Cannot split multi-page PDF %s: %s", original_filename, e)
                parse_error_messages.append(f"{original_filename}: {e}")
                total_errors += 1
                continue
            except Exception as e:
                logger.error(f"Failed to split PDF {original_filename}: {e}", exc_info=True)
                # Store as unparsed for manual review
                try:
                    _store_and_track(
                        s,
                        pdf_bytes=pdf_bytes,
                        filename=original_filename,
                        pdf_type="unparsed",
                        sales_order_id=None,
                        distribution_entry_id=None,
                        user=u,
                    )
                except Exception as e2:
                    logger.error(f"Storage error storing unsplit PDF {original_filename}: {e2}")
                    storage_errors += 1
                total_errors += 1
                continue
            
            total_pages += len(pages)
            
            # Process each page individually (same logic as single-file import)
            for page_num, page_bytes in pages:
                try:
                    result = parse_sales_orders_pdf(page_bytes)
                except Exception as e:
                    logger.error(f"Failed to parse page {page_num} of {original_filename}: {e}", exc_info=True)
                    # Store as unmatched for manual review
                    try:
                        _store_and_track(
                            s,
                            pdf_bytes=page_bytes,
                            filename=f"{original_filename}_page_{page_num}.pdf",
                            pdf_type="unparsed",
                            sales_order_id=None,
                            distribution_entry_id=None,
                            user=u,
                        )
                    except Exception as e2:
                        logger.error(f"Storage error storing unparsed page {page_num} of {original_filename}: {e2}")
                        storage_errors += 1
                    total_unmatched += 1
                    continue
                
                if result.errors:
                    parse_error_messages.extend(
                        [f"Page {page_num}: {e.message}" for e in result.errors if e.message]
                    )

                # Handle packing slip pages (matched to distributions when possible)
                if result.labels:
                    seen_matched_ids: set[int] = set()
                    had_unmatched_label = False
                    for label in result.labels:
                        matched_entry = _match_distribution_for_label(
                            s,
                            tracking_number=label.get("tracking_number"),
                            ship_to=label.get("ship_to"),
                            order_number=label.get("order_number"),
                            ss_shipment_id=label.get("ss_shipment_id"),
                        )
                        if matched_entry:
                            if matched_entry.id in seen_matched_ids:
                                continue
                            seen_matched_ids.add(matched_entry.id)
                            _delete_packing_slip_attachments_for_distribution(s, matched_entry.id)
                            _store_and_track(
                                s,
                                pdf_bytes=page_bytes,
                                filename=f"{original_filename}_page_{page_num}.pdf",
                                pdf_type="packing_slip",
                                sales_order_id=matched_entry.sales_order_id,
                                distribution_entry_id=matched_entry.id,
                                user=u,
                                order_number=matched_entry.order_number or None,
                            )
                            total_labels += 1
                        else:
                            had_unmatched_label = True
                    if had_unmatched_label:
                        _store_and_track(
                            s,
                            pdf_bytes=page_bytes,
                            filename=f"{original_filename}_page_{page_num}.pdf",
                            pdf_type="packing_slip",
                            sales_order_id=None,
                            distribution_entry_id=None,
                            user=u,
                        )
                        total_labels += 1

                if not result.orders and not result.labels:
                    # Page didn't parse - store as unmatched
                    _store_and_track(
                        s,
                        pdf_bytes=page_bytes,
                        filename=f"{original_filename}_page_{page_num}.pdf",
                        pdf_type="unmatched",
                        sales_order_id=None,
                        distribution_entry_id=None,
                        user=u,
                    )
                    total_unmatched += 1
                    continue
                
                # Process parsed orders from this page
                for order_data in result.orders:
                    order_number = order_data["order_number"]
                    order_date = order_data["order_date"]
                    customer_name = order_data["customer_name"]
                    customer_code = order_data.get("customer_code")
                    
                    # Find or create customer (Ship-To facility key for catheter; company for NRE)
                    try:
                        customer = _find_or_create_customer_for_order_data(s, order_data)
                    except Exception as e:
                        logger.warning(f"Error creating customer '{customer_name}': {e}")
                        continue
                    
                    # Check if sales order already exists — UPSERT (replace)
                    existing_order = _find_sales_order_by_number(s, order_number)
                    
                    if existing_order:
                        # UPDATE existing order instead of skipping
                        existing_order.order_date = order_date
                        existing_order.ship_date = order_data.get("ship_date") or order_date
                        existing_order.customer_id = customer.id
                        existing_order.updated_by_user_id = u.id
                        _fill_so_parsed_fields(existing_order, order_data)
                        if customer_code and not customer.customer_code:
                            customer.customer_code = customer_code

                        # Delete old lines and recreate
                        for old_line in list(existing_order.lines):
                            s.delete(old_line)

                        # Delete old PDF attachments for this order
                        from app.eqms.modules.rep_traceability.models import OrderPdfAttachment as _OPA
                        old_attachments = (
                            s.query(_OPA)
                            .filter(_OPA.sales_order_id == existing_order.id)
                            .all()
                        )
                        _storage = storage_from_config(current_app.config)
                        for att in old_attachments:
                            try:
                                _storage.delete(att.storage_key)
                            except Exception:
                                pass
                            s.delete(att)

                        # Store new PDF attachment
                        _store_and_track(
                            s,
                            pdf_bytes=page_bytes,
                            filename=f"SO_{order_number}.pdf",
                            pdf_type="sales_order_page",
                            sales_order_id=existing_order.id,
                            distribution_entry_id=None,
                            user=u,
                            order_number=order_number,
                        )

                        # Create new order lines
                        for line_num, line_data in enumerate(order_data["lines"], start=1):
                            sku = line_data["sku"]
                            quantity = line_data["quantity"]
                            if not sku or not quantity or int(quantity) <= 0:
                                continue
                            order_line = SalesOrderLine(
                                sales_order_id=existing_order.id,
                                sku=sku,
                                quantity=quantity,
                                lot_number=None,
                                line_number=line_num,
                            )
                            s.add(order_line)
                            total_lines += 1

                        rematch_unmatched_distributions_for_order(s, existing_order)
                        total_updated += 1
                        continue
                    
                    external_key = f"pdf:{order_number}"
                    # Create sales order (NRE classification is dynamic, not static metadata)
                    sales_order = SalesOrder(
                        order_number=order_number,
                        order_date=order_date,
                        ship_date=order_data.get("ship_date") or order_date,
                        customer_id=customer.id,
                        source="pdf_import",
                        external_key=external_key,
                        status="completed",
                        notes=None,
                        created_by_user_id=u.id,
                        updated_by_user_id=u.id,
                    )
                    _fill_so_parsed_fields(sales_order, order_data)
                    s.add(sales_order)
                    s.flush()
                    total_orders += 1
                    
                    rematch_unmatched_distributions_for_order(s, sales_order)

                    # Store THIS PAGE's PDF as attachment (named by order number)
                    _store_and_track(
                        s,
                        pdf_bytes=page_bytes,
                        filename=f"SO_{order_number}.pdf",
                        pdf_type="sales_order_page",
                        sales_order_id=sales_order.id,
                        distribution_entry_id=None,
                        user=u,
                        order_number=order_number,
                    )
                    
                    # Create order lines (do NOT create distributions)
                    for line_num, line_data in enumerate(order_data["lines"], start=1):
                        sku = line_data["sku"]
                        quantity = line_data["quantity"]
                        if not sku or not quantity or int(quantity) <= 0:
                            continue
                        
                        # Create order line
                        order_line = SalesOrderLine(
                            sales_order_id=sales_order.id,
                            sku=sku,
                            quantity=quantity,
                            lot_number=None,
                            line_number=line_num,
                        )
                        s.add(order_line)
                        total_lines += 1
        
        # Audit event
        from app.eqms.audit import record_event
        record_event(
            s,
            actor=u,
            action="sales_orders.import_pdf_bulk",
            entity_type="SalesOrder",
            entity_id="pdf_import_bulk",
            metadata={
                "files_processed": len([f for f in files if f and f.filename]),
                "total_pages": total_pages,
                "orders_created": total_orders,
                "orders_updated": total_updated,
                "lines_created": total_lines,
                "unmatched_pages": total_unmatched,
                "total_errors": total_errors,
                "storage_errors": storage_errors,
            },
        )
        
        # Commit all changes
        try:
            s.commit()
        except Exception as e:
            logger.error(f"Database commit failed during bulk PDF import: {e}", exc_info=True)
            s.rollback()
            try:
                storage = storage_from_config(current_app.config)
                for key in stored_keys:
                    storage.delete(key)
            except Exception as cleanup_err:
                logger.error("Failed to rollback stored PDFs after DB error: %s", cleanup_err, exc_info=True)
            flash("Database error occurred. Some data may not have been saved. Check logs for details.", "danger")
            return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))

        msg = f"Bulk PDF import: {total_pages} pages processed, {total_orders} new orders, {total_lines} lines."
        if total_updated:
            msg += f" {total_updated} existing orders updated."
        if total_unmatched:
            msg += f" {total_unmatched} pages could not be parsed."
        if total_labels:
            msg += f" {total_labels} packing slip page(s) stored."
        if parse_error_messages:
            preview = "; ".join(parse_error_messages[:3])
            msg += f" {len(parse_error_messages)} parse warning(s). Example: {preview}"
        if total_errors:
            msg += f" {total_errors} file errors."
        
        # Determine flash category based on errors
        flash_category = "success"
        if storage_errors > 0:
            msg += f" WARNING: {storage_errors} PDFs failed to store. Check /admin/diagnostics/storage"
            flash_category = "danger"
        elif total_errors > 0 or total_unmatched > 0 or parse_error_messages:
            flash_category = "warning"
        
        logger.info(f"Bulk PDF import completed: {total_orders} new + {total_updated} updated orders, {total_pages} pages, {total_errors} errors, {storage_errors} storage errors")
        flash(msg, flash_category)
        
    except Exception as e:
        logger.error(f"Bulk PDF import failed unexpectedly: {e}", exc_info=True)
        s.rollback()
        flash(f"Import failed: {str(e)}. Please check logs for details.", "danger")
    
    return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))


@bp.post("/packing-slips/import-bulk")
@require_permission("sales_orders.import")
def packing_slips_import_bulk():
    """Bulk packing slip PDF import (no sales orders created)."""
    from app.eqms.modules.rep_traceability.parsers.pdf import (
        PdfSplitError,
        parse_sales_orders_pdf,
        split_pdf_into_pages,
    )

    s = db_session()
    u = _current_user()

    files = request.files.getlist("pdf_files")
    if not files or not any(f.filename for f in files if f):
        flash("Please select one or more PDF files to upload.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB
    total_upload_size = 0

    for f in files:
        if not f or not f.filename:
            continue
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(0)
        if file_size > MAX_FILE_SIZE:
            flash(f"File '{f.filename}' is too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB per file.", "danger")
            return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
        total_upload_size += file_size

    if total_upload_size > MAX_TOTAL_SIZE:
        flash(f"Total upload size ({total_upload_size / 1024 / 1024:.1f}MB) exceeds maximum ({MAX_TOTAL_SIZE / 1024 / 1024:.0f}MB).", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))

    total_pages = 0
    total_matched = 0
    total_unmatched = 0
    parse_error_messages: list[str] = []
    storage_errors = 0
    stored_keys: list[str] = []

    def _store_and_track(*args, **kwargs):
        key = _store_pdf_attachment(*args, **kwargs)
        stored_keys.append(key)
        return key

    try:
        for f in files:
            if not f or not f.filename:
                continue
            original_filename = f.filename or "packing-slips.pdf"
            pdf_bytes = f.read()
            if len(pdf_bytes) > MAX_FILE_SIZE:
                continue
            try:
                pages = split_pdf_into_pages(pdf_bytes)
            except PdfSplitError as e:
                logger.error("Packing slip import split failed for %s: %s", original_filename, e)
                flash(f"Cannot import multi-page file '{original_filename}': {e}", "danger")
                continue
            total_pages += len(pages)
            for page_num, page_bytes in pages:
                try:
                    result = parse_sales_orders_pdf(page_bytes)
                except Exception as e:
                    logger.error("Failed to parse packing slip page %s of %s: %s", page_num, original_filename, e, exc_info=True)
                    parse_error_messages.append(f"Page {page_num}: parse error")
                    continue

                if result.errors:
                    parse_error_messages.extend(
                        [f"Page {page_num}: {e.message}" for e in result.errors if e.message]
                    )

                labels = result.labels or []
                if not labels:
                    try:
                        _store_and_track(
                            s,
                            pdf_bytes=page_bytes,
                            filename=f"{original_filename}_page_{page_num}.pdf",
                            pdf_type="packing_slip",
                            sales_order_id=None,
                            distribution_entry_id=None,
                            user=u,
                        )
                        total_unmatched += 1
                    except Exception as e:
                        logger.error("Storage error storing packing slip page %s of %s: %s", page_num, original_filename, e)
                        storage_errors += 1
                    continue

                seen_matched_ids: set[int] = set()
                had_unmatched_label = False
                for label in labels:
                    matched_entry = _match_distribution_for_label(
                        s,
                        tracking_number=label.get("tracking_number"),
                        ship_to=label.get("ship_to"),
                        order_number=label.get("order_number"),
                        ss_shipment_id=label.get("ss_shipment_id"),
                    )
                    try:
                        if matched_entry:
                            if matched_entry.id in seen_matched_ids:
                                continue
                            seen_matched_ids.add(matched_entry.id)
                            _delete_packing_slip_attachments_for_distribution(s, matched_entry.id)
                            _store_and_track(
                                s,
                                pdf_bytes=page_bytes,
                                filename=f"{original_filename}_page_{page_num}.pdf",
                                pdf_type="packing_slip",
                                sales_order_id=matched_entry.sales_order_id,
                                distribution_entry_id=matched_entry.id,
                                user=u,
                                order_number=matched_entry.order_number or None,
                            )
                            total_matched += 1
                        else:
                            had_unmatched_label = True
                    except Exception as e:
                        logger.error("Storage error storing packing slip page %s of %s: %s", page_num, original_filename, e)
                        storage_errors += 1
                if had_unmatched_label:
                    try:
                        _store_and_track(
                            s,
                            pdf_bytes=page_bytes,
                            filename=f"{original_filename}_page_{page_num}.pdf",
                            pdf_type="packing_slip",
                            sales_order_id=None,
                            distribution_entry_id=None,
                            user=u,
                        )
                        total_unmatched += 1
                    except Exception as e:
                        logger.error("Storage error storing unmatched packing slip page %s: %s", page_num, e)
                        storage_errors += 1

        from app.eqms.audit import record_event

        record_event(
            s,
            actor=u,
            action="packing_slips.import_bulk",
            entity_type="OrderPdfAttachment",
            entity_id="packing_slip_import",
            metadata={
                "files_processed": len([f for f in files if f and f.filename]),
                "total_pages": total_pages,
                "matched": total_matched,
                "unmatched": total_unmatched,
                "storage_errors": storage_errors,
            },
        )
        try:
            s.commit()
        except Exception as e:
            logger.error("Database commit failed during packing slip import: %s", e, exc_info=True)
            s.rollback()
            try:
                storage = storage_from_config(current_app.config)
                for key in stored_keys:
                    storage.delete(key)
            except Exception as cleanup_err:
                logger.error("Failed to rollback stored packing slip PDFs after DB error: %s", cleanup_err, exc_info=True)
            flash("Database error occurred. Some data may not have been saved. Check logs for details.", "danger")
            return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))

        msg = f"Packing slip import: {total_pages} pages processed."
        if total_matched:
            msg += f" {total_matched} matched."
        if total_unmatched:
            msg += f" {total_unmatched} unmatched."
        flash_category = "success" if storage_errors == 0 else "warning"
        if storage_errors:
            msg += f" WARNING: {storage_errors} storage errors."
        flash(msg, flash_category)
    except Exception as e:
        logger.error("Packing slip import failed: %s", e, exc_info=True)
        s.rollback()
        flash(f"Import failed: {str(e)}", "danger")

    return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))


@bp.get("/sales-orders/import-pdf")
@require_permission("sales_orders.import")
def sales_orders_import_pdf_get():
    """Sales Orders PDF import page (consolidated PDF import for orders + distributions)."""
    pdfplumber_available = False
    try:
        import pdfplumber  # noqa: F401
        pdfplumber_available = True
    except ImportError:
        pass
    return render_template("admin/sales_orders/import.html", pdfplumber_available=pdfplumber_available)


@bp.get("/sales-orders/unmatched-pdfs")
@require_permission("sales_orders.view")
def sales_orders_unmatched_pdfs():
    """List unmatched PDF attachments (pages that couldn't be parsed or matched to orders)."""
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
    
    s = db_session()
    
    # Get unmatched PDFs (no sales_order_id)
    attachments = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.sales_order_id.is_(None))
        .order_by(OrderPdfAttachment.uploaded_at.desc())
        .limit(200)
        .all()
    )
    
    # Group by pdf_type for display
    unmatched_count = len([a for a in attachments if a.pdf_type == "unmatched"])
    unparsed_count = len([a for a in attachments if a.pdf_type == "unparsed"])
    label_count = len([a for a in attachments if is_packing_slip_pdf_type(a.pdf_type)])
    other_count = len(attachments) - unmatched_count - unparsed_count - label_count
    
    return render_template(
        "admin/sales_orders/unmatched_pdfs.html",
        attachments=attachments,
        unmatched_count=unmatched_count,
        unparsed_count=unparsed_count,
        label_count=label_count,
        other_count=other_count,
    )


@bp.post("/sales-orders/pdf/match")
@require_permission("sales_orders.edit")
def sales_orders_match_pdf():
    """Manually match an unmatched PDF to a Sales Order or Distribution."""
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment, SalesOrder
    from app.eqms.modules.rep_traceability.service import normalize_order_number

    s = db_session()
    attachment_id = request.form.get("attachment_id")
    order_number = (request.form.get("order_number") or "").strip()

    if not attachment_id or not order_number:
        flash("Attachment and order number are required.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_unmatched_pdfs"))

    try:
        attachment_id_int = int(attachment_id)
    except Exception:
        flash("Invalid attachment id.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_unmatched_pdfs"))

    attachment = s.get(OrderPdfAttachment, attachment_id_int)
    if not attachment:
        flash("Attachment not found.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_unmatched_pdfs"))

    normalized = normalize_order_number(order_number)
    sales_order = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_number.ilike(f"%{normalized}%"))
        .order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc())
        .first()
    )
    if sales_order:
        attachment.sales_order_id = sales_order.id
        attachment.pdf_type = "matched_upload"
        s.commit()
        flash(f"PDF matched to Sales Order {sales_order.order_number}.", "success")
        return redirect(url_for("rep_traceability.sales_orders_unmatched_pdfs"))

    dist = (
        s.query(DistributionLogEntry)
        .filter(
            DistributionLogEntry.order_number.ilike(f"%{normalized}%"),
            DistributionLogEntry.sales_order_id.is_(None),
        )
        .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
        .first()
    )
    if dist:
        attachment.distribution_entry_id = dist.id
        attachment.pdf_type = "matched_upload"
        s.commit()
        flash(f"PDF matched to Distribution {dist.order_number}.", "success")
        return redirect(url_for("rep_traceability.sales_orders_unmatched_pdfs"))

    flash(f"No order or distribution found matching '{order_number}'.", "warning")
    return redirect(url_for("rep_traceability.sales_orders_unmatched_pdfs"))


@bp.post("/sales-orders/import-pdf")
@require_permission("sales_orders.import")
def sales_orders_import_pdf_post():
    """Import sales orders and lines from PDF (no distributions).
    
    This is the consolidated PDF import route - creates records
    with sales_order → sales_order_lines linkage only.
    
    BULK PDF SPLITTING: If PDF has multiple pages, splits into individual pages
    and stores each page as a separate attachment linked to its Sales Order.
    """
    try:
        from app.eqms.modules.rep_traceability.parsers.pdf import (
            PdfSplitError,
            parse_sales_orders_pdf,
            split_pdf_into_pages,
        )
    except ImportError:
        flash("PDF parsing libraries are not installed. Please contact support.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
    from datetime import datetime
    
    s = db_session()
    u = _current_user()
    
    f = request.files.get("pdf_file")
    if not f or not f.filename:
        flash("Choose a PDF file to import.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    original_filename = f.filename or "upload.pdf"
    pdf_bytes = f.read()
    
    try:
        pages = split_pdf_into_pages(pdf_bytes)
    except PdfSplitError as e:
        flash(f"Cannot import multi-page PDF: {e}", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    total_pages = len(pages)
    
    # Track results
    created_orders = 0
    updated_orders = 0
    created_lines = 0
    unmatched_pages = 0
    label_pages = 0
    parse_error_messages: list[str] = []
    page_to_order: dict[int, int] = {}  # page_num -> sales_order_id
    stored_keys: list[str] = []

    def _store_and_track(*args, **kwargs):
        key = _store_pdf_attachment(*args, **kwargs)
        stored_keys.append(key)
        return key
    
    # Process each page individually
    for page_num, page_bytes in pages:
        result = parse_sales_orders_pdf(page_bytes)
        if result.errors:
            parse_error_messages.extend(
                [f"Page {page_num}: {e.message}" for e in result.errors if e.message]
            )

        if result.labels:
            seen_matched_ids: set[int] = set()
            had_unmatched_label = False
            for label in result.labels:
                matched_entry = _match_distribution_for_label(
                    s,
                    tracking_number=label.get("tracking_number"),
                    ship_to=label.get("ship_to"),
                    order_number=label.get("order_number"),
                    ss_shipment_id=label.get("ss_shipment_id"),
                )
                if matched_entry:
                    if matched_entry.id in seen_matched_ids:
                        continue
                    seen_matched_ids.add(matched_entry.id)
                    _delete_packing_slip_attachments_for_distribution(s, matched_entry.id)
                    _store_and_track(
                        s,
                        pdf_bytes=page_bytes,
                        filename=f"packing-slip_page_{page_num}.pdf",
                        pdf_type="packing_slip",
                        sales_order_id=matched_entry.sales_order_id,
                        distribution_entry_id=matched_entry.id,
                        user=u,
                        order_number=matched_entry.order_number or None,
                    )
                    label_pages += 1
                else:
                    had_unmatched_label = True
            if had_unmatched_label:
                _store_and_track(
                    s,
                    pdf_bytes=page_bytes,
                    filename=f"packing-slip_page_{page_num}.pdf",
                    pdf_type="packing_slip",
                    sales_order_id=None,
                    distribution_entry_id=None,
                    user=u,
                )
                label_pages += 1

        if not result.orders and not result.labels:
            # Page didn't parse - store as unmatched
            _store_and_track(
                s,
                pdf_bytes=page_bytes,
                filename=f"unmatched_page_{page_num}.pdf",
                pdf_type="unmatched",
                sales_order_id=None,
                distribution_entry_id=None,
                user=u,
            )
            unmatched_pages += 1
            continue
        
        # Process parsed orders from this page
        for order_data in result.orders:
            order_number = order_data["order_number"]
            order_date = order_data["order_date"]
            customer_name = order_data["customer_name"]
            customer_code = order_data.get("customer_code")
            
            # Find or create customer (Ship-To facility key for catheter; company for NRE)
            try:
                customer = _find_or_create_customer_for_order_data(s, order_data)
            except Exception as e:
                current_app.logger.warning(f"Error creating customer '{customer_name}': {e}")
                continue
            
            # Check if sales order already exists — UPSERT (replace)
            existing_order = _find_sales_order_by_number(s, order_number)
            
            if existing_order:
                # UPDATE existing order instead of skipping
                existing_order.order_date = order_date
                existing_order.ship_date = order_date
                existing_order.customer_id = customer.id
                existing_order.updated_by_user_id = u.id
                # P39: best-effort parsed fields (do not overwrite non-null invoice_date).
                _fill_so_parsed_fields(existing_order, order_data)
                if customer_code and not customer.customer_code:
                    customer.customer_code = customer_code

                # Delete old lines and recreate
                for old_line in list(existing_order.lines):
                    s.delete(old_line)

                # Delete old PDF attachments for this order
                from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
                old_attachments = (
                    s.query(OrderPdfAttachment)
                    .filter(OrderPdfAttachment.sales_order_id == existing_order.id)
                    .all()
                )
                storage = storage_from_config(current_app.config)
                for att in old_attachments:
                    try:
                        storage.delete(att.storage_key)
                    except Exception:
                        pass
                    s.delete(att)

                # Store new PDF attachment
                _store_and_track(
                    s,
                    pdf_bytes=page_bytes,
                    filename=f"SO_{order_number}.pdf",
                    pdf_type="sales_order_page",
                    sales_order_id=existing_order.id,
                    distribution_entry_id=None,
                    user=u,
                    order_number=order_number,
                )

                # Create new order lines
                for line_num, line_data in enumerate(order_data["lines"], start=1):
                    sku = line_data["sku"]
                    quantity = line_data["quantity"]
                    if not sku or not quantity or int(quantity) <= 0:
                        continue
                    order_line = SalesOrderLine(
                        sales_order_id=existing_order.id,
                        sku=sku,
                        quantity=quantity,
                        lot_number=None,
                        line_number=line_num,
                    )
                    s.add(order_line)
                    created_lines += 1

                rematch_unmatched_distributions_for_order(s, existing_order)
                page_to_order[page_num] = existing_order.id
                updated_orders += 1
                continue
            
            is_nre = not _is_catheter_order(order_data)
            external_key = f"pdf:{order_number}"
            # Create sales order
            sales_order = SalesOrder(
                order_number=order_number,
                order_date=order_date,
                ship_date=order_date,
                customer_id=customer.id,
                source="pdf_import",
                external_key=external_key,
                status="completed",
                notes="NRE Project" if is_nre else None,
                created_by_user_id=u.id,
                updated_by_user_id=u.id,
            )
            _fill_so_parsed_fields(sales_order, order_data)
            s.add(sales_order)
            s.flush()
            created_orders += 1
            page_to_order[page_num] = sales_order.id
            
            rematch_unmatched_distributions_for_order(s, sales_order)

            # Store THIS PAGE's PDF as attachment (named by order number)
            _store_and_track(
                s,
                pdf_bytes=page_bytes,
                filename=f"SO_{order_number}.pdf",
                pdf_type="sales_order_page",
                sales_order_id=sales_order.id,
                distribution_entry_id=None,
                user=u,
                order_number=order_number,
            )
            
            # Create order lines only (no distributions)
            for line_num, line_data in enumerate(order_data["lines"], start=1):
                sku = line_data["sku"]
                quantity = line_data["quantity"]
                if not sku or not quantity or int(quantity) <= 0:
                    continue
                
                # Create order line
                order_line = SalesOrderLine(
                    sales_order_id=sales_order.id,
                    sku=sku,
                    quantity=quantity,
                    lot_number=None,
                    line_number=line_num,
                )
                s.add(order_line)
                created_lines += 1
    
    # Audit event
    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="sales_orders.import_pdf",
        entity_type="SalesOrder",
        entity_id="pdf_import",
        metadata={
            "total_pages": total_pages,
            "orders_created": created_orders,
            "orders_updated": updated_orders,
            "lines_created": created_lines,
            "unmatched_pages": unmatched_pages,
        },
    )
    try:
        s.commit()
    except Exception as e:
        logger.error("Database commit failed during PDF import: %s", e, exc_info=True)
        s.rollback()
        try:
            storage = storage_from_config(current_app.config)
            for key in stored_keys:
                storage.delete(key)
        except Exception as cleanup_err:
            logger.error("Failed to rollback stored PDFs after DB error: %s", cleanup_err, exc_info=True)
        flash("Database error occurred. Some data may not have been saved. Check logs for details.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    msg = f"PDF import complete: {total_pages} pages processed, {created_orders} new orders, {created_lines} lines."
    if updated_orders:
        msg += f" {updated_orders} existing orders updated."
    if unmatched_pages:
        msg += f" {unmatched_pages} pages could not be parsed (stored as unmatched)."
    if label_pages:
        msg += f" {label_pages} packing slip page(s) stored."
    if parse_error_messages:
        preview = "; ".join(parse_error_messages[:3])
        msg += f" {len(parse_error_messages)} parse warning(s). Example: {preview}"
    
    flash_category = "success"
    if unmatched_pages or parse_error_messages:
        flash_category = "warning"
    flash(msg, flash_category)
    return redirect(url_for("rep_traceability.sales_orders_list"))


# ============================================================================
# Sales Dashboard AJAX Endpoints (Dropdown Details)
# ============================================================================

@bp.get("/sales-dashboard/order-details/<order_number>")
@require_permission("sales_dashboard.view")
def sales_dashboard_order_details(order_number: str):
    """Return JSON with order details for dropdown."""
    from flask import jsonify
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine, OrderPdfAttachment
    
    s = db_session()
    
    # Find order by order_number (may have multiple matches, use most recent)
    order = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_number == order_number)
        .order_by(SalesOrder.order_date.desc())
        .first()
    )
    
    if not order:
        # Fall back to distributions if no sales order
        distributions = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.order_number == order_number)
            .order_by(DistributionLogEntry.ship_date.desc())
            .limit(20)
            .all()
        )
        
        if not distributions:
            return jsonify({"error": "Order not found"}), 404
        
        # Build response from distributions only
        return jsonify({
            "order_number": order_number,
            "order_date": str(distributions[0].ship_date) if distributions else None,
            "ship_date": str(distributions[0].ship_date) if distributions else None,
            "customer": distributions[0].facility_name if distributions else None,
            "has_sales_order": False,
            "lines": [],
            "distributions": [
                {
                    "id": d.id,
                    "sku": d.sku,
                    "lot": d.lot_number,
                    "quantity": d.quantity,
                    "ship_date": str(d.ship_date),
                }
                for d in distributions
            ],
        })
    
    # Build response from sales order
    lines = s.query(SalesOrderLine).filter(SalesOrderLine.sales_order_id == order.id).all()
    distributions = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.sales_order_id == order.id)
        .order_by(DistributionLogEntry.ship_date.desc())
        .all()
    )
    
    # Get PDF attachments for this order
    attachments = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.sales_order_id == order.id)
        .order_by(OrderPdfAttachment.uploaded_at.desc())
        .limit(10)
        .all()
    )
    
    return jsonify({
        "order_number": order.order_number,
        "order_date": str(order.order_date) if order.order_date else None,
        "ship_date": str(order.ship_date) if order.ship_date else None,
        "customer": order.customer.facility_name if order.customer else None,
        "customer_id": order.customer_id,
        "status": order.status,
        "source": order.source,
        "has_sales_order": True,
        "lines": [
            {"sku": l.sku, "quantity": l.quantity, "lot_number": l.lot_number}
            for l in lines
        ],
        "distributions": [
            {
                "id": d.id,
                "sku": d.sku,
                "lot": d.lot_number,
                "quantity": d.quantity,
                "ship_date": str(d.ship_date),
            }
            for d in distributions
        ],
        "attachments": [
            {"id": a.id, "filename": a.filename, "pdf_type": a.pdf_type}
            for a in attachments
        ],
    })

