from __future__ import annotations

import csv
import io
from datetime import date

from flask import Blueprint, flash, g, redirect, render_template, request, send_file, url_for, current_app

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.rep_traceability.models import ApprovalEml, DistributionLogEntry, TracingReport
from app.eqms.modules.rep_traceability.parsers.csv import parse_distribution_csv
from app.eqms.modules.rep_traceability.service import (
    check_duplicate_manual_csv,
    compute_sales_dashboard,
    create_distribution_entry,
    delete_distribution_entry,
    generate_tracing_report_csv,
    query_distribution_entries,
    update_distribution_entry,
    upload_approval_eml,
    validate_distribution_payload,
)
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.customer_profiles.service import find_or_create_customer
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config
from app.eqms.modules.rep_traceability.utils import (
    normalize_text,
    normalize_source,
    parse_distribution_filters,
    parse_ship_date,
    parse_tracing_filters,
)

bp = Blueprint("rep_traceability", __name__)


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


def _store_pdf_attachment(
    s,
    *,
    pdf_bytes: bytes,
    filename: str,
    pdf_type: str,
    sales_order_id: int | None,
    distribution_entry_id: int | None,
    user: User,
) -> str:
    from werkzeug.utils import secure_filename
    from datetime import datetime
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment

    storage = storage_from_config(current_app.config)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(filename) or "document.pdf"
    if sales_order_id:
        storage_key = f"sales_orders/{sales_order_id}/pdfs/{pdf_type}_{timestamp}_{safe_name}"
    else:
        storage_key = f"sales_orders/unlinked/{pdf_type}_{timestamp}_{safe_name}"
    storage.put_bytes(storage_key, pdf_bytes, content_type="application/pdf")

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


def _parse_filters() -> dict:
    return parse_distribution_filters(request.args)

def _customers_for_select(s) -> list[Customer]:
    return s.query(Customer).order_by(Customer.facility_name.asc(), Customer.id.asc()).limit(500).all()


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
    reps = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()

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
        "sku": request.form.get("sku"),
        "lot_number": request.form.get("lot_number"),
        "quantity": request.form.get("quantity"),
        "address1": request.form.get("address1"),
        "city": request.form.get("city"),
        "state": request.form.get("state"),
        "zip": request.form.get("zip"),
        "tracking_number": request.form.get("tracking_number"),
        "sales_order_id": request.form.get("sales_order_id"),  # Link to sales order
    }

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

    errs = validate_distribution_payload(payload)
    if errs:
        flash("; ".join([f"{e.field}: {e.message}" for e in errs]), "danger")
        return redirect(url_for("rep_traceability.distribution_log_new_get"))

    ship_date = parse_ship_date(str(payload["ship_date"]))
    dupe = check_duplicate_manual_csv(
        s,
        order_number=payload.get("order_number") or "",
        ship_date=ship_date,
        facility_name=payload.get("facility_name") or "",
        sku=payload.get("sku") or "",
        lot_number=payload.get("lot_number") or "",
    )
    if dupe:
        flash("Duplicate detected (order_number + ship_date + facility_name + sku + lot). Entry created anyway (Admin override).", "danger")

    create_distribution_entry(s, payload, user=u, source_default="manual")
    s.commit()
    flash("Distribution entry created.", "success")
    return redirect(url_for("rep_traceability.distribution_log_list"))


@bp.get("/distribution-log/<int:entry_id>/edit")
@require_permission("distribution_log.edit")
def distribution_log_edit_get(entry_id: int):
    from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
    s = db_session()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        from flask import abort

        abort(404)
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

    payload = {
        "ship_date": request.form.get("ship_date"),
        "order_number": request.form.get("order_number"),
        "facility_name": request.form.get("facility_name"),
        "rep_id": request.form.get("rep_id"),
        "rep_name": request.form.get("rep_name"),
        "customer_id": request.form.get("customer_id"),
        "customer_name": request.form.get("customer_name"),
        "source": request.form.get("source"),
        "sku": request.form.get("sku"),
        "lot_number": request.form.get("lot_number"),
        "quantity": request.form.get("quantity"),
        "city": request.form.get("city"),
        "state": request.form.get("state"),
        "zip": request.form.get("zip"),
        "tracking_number": request.form.get("tracking_number"),
        "sales_order_id": request.form.get("sales_order_id"),  # Link to sales order
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
        # Canonicalize facility fields from customer master record (for consistency)
        payload["facility_name"] = c.facility_name
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
                return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
            if so.customer_id and so.customer_id != c.id:
                flash(f"Sales order #{so.order_number} belongs to a different customer. Please select a matching customer or remove the sales order link.", "danger")
                return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    errs = validate_distribution_payload(payload)
    if errs:
        flash("; ".join([f"{e.field}: {e.message}" for e in errs]), "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    update_distribution_entry(s, entry, payload, user=u, reason=reason)
    # Keep facility fields consistent (service-layer update doesn't touch zip today)
    entry.zip = normalize_text(payload.get("zip")) or None
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


@bp.get("/distribution-log/entry-details/<int:entry_id>")
@require_permission("distribution_log.view")
def distribution_log_entry_details(entry_id: int):
    """Return JSON with entry details for in-page modal."""
    from flask import jsonify
    from sqlalchemy import func
    from app.eqms.modules.rep_traceability.models import SalesOrder
    
    s = db_session()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    
    # Get linked sales order if exists
    order_data = None
    attachments = []
    if entry.sales_order_id:
        order = s.get(SalesOrder, entry.sales_order_id)
        if order:
            order_data = {
                "order_number": order.order_number,
                "order_date": str(order.order_date) if order.order_date else None,
                "ship_date": str(order.ship_date) if order.ship_date else None,
                "status": order.status,
            }
            attachments = (
                s.query(OrderPdfAttachment)
                .filter(OrderPdfAttachment.sales_order_id == order.id)
                .order_by(OrderPdfAttachment.uploaded_at.desc())
                .limit(10)
                .all()
            )
    
    # Get customer data and stats
    customer_data = None
    customer_stats = None
    if entry.customer_id:
        from app.eqms.modules.customer_profiles.models import Customer, CustomerRep
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
                (r.rep.email if r.rep else str(r.rep_id)) for r in rep_rows
            ]
            
            # Calculate customer stats
            customer_entries = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.customer_id == customer.id)
                .all()
            )
            
            if customer_entries:
                first_order = min(e.ship_date for e in customer_entries if e.ship_date)
                last_order = max(e.ship_date for e in customer_entries if e.ship_date)
                total_orders = len({e.order_number for e in customer_entries if e.order_number})
                total_units = sum(int(e.quantity or 0) for e in customer_entries)
                
                # Top SKUs
                sku_totals: dict[str, int] = {}
                for e in customer_entries:
                    if e.sku:
                        sku_totals[e.sku] = sku_totals.get(e.sku, 0) + int(e.quantity or 0)
                top_skus = sorted(sku_totals.items(), key=lambda kv: kv[1], reverse=True)[:5]
                
                # Recent lots (unique)
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
    
    return jsonify({
        "entry": {
            "id": entry.id,
            "ship_date": str(entry.ship_date) if entry.ship_date else None,
            "order_number": entry.order_number,
            "facility_name": entry.facility_name,
            "sku": entry.sku,
            "lot_number": entry.lot_number,
            "quantity": entry.quantity,
            "source": entry.source,
            "customer_id": entry.customer_id,
        },
        "order": order_data,
        "customer": customer_data,
        "customer_stats": customer_stats,
        "attachments": [
            {"id": a.id, "filename": a.filename, "pdf_type": a.pdf_type}
            for a in attachments
        ],
    })


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

    rows, errors = parse_distribution_csv(f.read())

    created = 0
    duplicates = 0
    duplicates_sample: list[dict] = []
    for r in rows:
        # Auto-link/create customer by facility_name (lean P0 behavior).
        facility_name = normalize_text(r.get("facility_name"))
        if facility_name:
            c = find_or_create_customer(
                s,
                facility_name=facility_name,
                address1=r.get("address1"),
                city=r.get("city"),
                state=r.get("state"),
                zip=r.get("zip"),
                contact_name=r.get("contact_name"),
                contact_phone=r.get("contact_phone"),
                contact_email=r.get("contact_email"),
            )
            r["customer_id"] = c.id
            r["customer_name"] = c.facility_name
            r["facility_name"] = c.facility_name
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
    reps = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()
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

    start_date_s = normalize_text(request.args.get("start_date")) or "2025-01-01"
    try:
        start_date = date.fromisoformat(start_date_s)
    except Exception:
        flash("Invalid start_date. Use YYYY-MM-DD.", "danger")
        return redirect(url_for("rep_traceability.sales_dashboard"))

    data = compute_sales_dashboard(s, start_date=start_date)

    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="sales_dashboard.view",
        entity_type="SalesDashboard",
        entity_id="view",
        metadata={"start_date": str(start_date)},
    )
    s.commit()

    return render_template(
        "admin/sales_dashboard/index.html",
        start_date=str(start_date),
        stats=data["stats"],
        sku_breakdown=data["sku_breakdown"],
        lot_tracking=data["lot_tracking"],
        lot_min_year=data.get("lot_min_year"),
        recent_orders_new=data.get("recent_orders_new") or [],
        recent_orders_repeat=data.get("recent_orders_repeat") or [],
    )


@bp.get("/sales-dashboard/order-note-form/<int:customer_id>")
@require_permission("customers.notes")
def sales_dashboard_order_note_form(customer_id: int):
    """Return HTML fragment for inline note form."""
    s = db_session()
    from app.eqms.modules.customer_profiles.service import get_customer_by_id

    customer = get_customer_by_id(s, customer_id)
    if not customer:
        from flask import abort

        abort(404)
    return render_template(
        "admin/sales_dashboard/_note_form.html",
        customer=customer,
        today=date.today().isoformat(),
    )


@bp.post("/sales-dashboard/order-note")
@require_permission("customers.notes")
def sales_dashboard_order_note_post():
    """Create a customer note from Sales Dashboard (AJAX)."""
    from flask import jsonify
    from app.eqms.modules.customer_profiles.service import add_customer_note, get_customer_by_id
    from app.eqms.modules.customer_profiles.models import CustomerNote

    s = db_session()
    u = _current_user()

    payload = request.get_json(silent=True) or {}
    customer_id = payload.get("customer_id") or request.form.get("customer_id")
    note_text = payload.get("note_text") or request.form.get("note_text")
    note_date = payload.get("note_date") or request.form.get("note_date")

    if not customer_id or not note_text:
        return jsonify({"error": "customer_id and note_text are required"}), 400

    customer = get_customer_by_id(s, int(customer_id))
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    note = add_customer_note(s, customer, note_text=note_text, note_date=note_date, user=u)

    # Return updated note count
    note_count = (
        s.query(CustomerNote)
        .filter(CustomerNote.customer_id == customer.id)
        .count()
    )
    s.commit()

    return jsonify({
        "id": note.id,
        "note_text": note.note_text,
        "note_date": str(note.note_date) if note.note_date else None,
        "note_count": note_count,
    })


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

    start_date_s = normalize_text(request.args.get("start_date")) or "2025-01-01"
    try:
        start_date = date.fromisoformat(start_date_s)
    except Exception:
        flash("Invalid start_date. Use YYYY-MM-DD.", "danger")
        return redirect(url_for("rep_traceability.sales_dashboard"))

    data = compute_sales_dashboard(s, start_date=start_date)
    window_entries = data["window_entries"]
    orders_by_customer = data["orders_by_customer"]
    customer_key_fn = data["customer_key_fn"]

    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(
        [
            "Customer Type",
            "Ship Date",
            "Order #",
            "Facility",
            "City",
            "State",
            "SKU",
            "Lot",
            "Quantity",
            "Source",
            "Customer ID",
            "Customer Key",
        ]
    )
    for e in window_entries:
        key = customer_key_fn(e.customer_id, e.facility_name, e.customer_name)
        lifetime_orders = len({o for o in orders_by_customer.get(key, set()) if o})
        cust_type = "First-Time" if lifetime_orders <= 1 else "Repeat"
        w.writerow(
            [
                cust_type,
                str(e.ship_date),
                e.order_number,
                e.facility_name,
                e.city or "",
                e.state or "",
                e.sku,
                e.lot_number,
                e.quantity,
                e.source,
                e.customer_id or "",
                key,
            ]
        )

    from app.eqms.audit import record_event

    record_event(
        s,
        actor=u,
        action="sales_dashboard.export",
        entity_type="SalesDashboard",
        entity_id="export",
        metadata={"start_date": str(start_date), "row_count": len(window_entries)},
    )
    s.commit()

    data_bytes = out.getvalue().encode("utf-8")
    filename = f"sales_dashboard_{start_date.strftime('%Y%m%d')}.csv"
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
        },
    )


@bp.get("/sales-orders/<int:order_id>")
@require_permission("sales_orders.view")
def sales_order_detail(order_id: int):
    """View sales order detail with lines and distributions."""
    from app.eqms.modules.rep_traceability.models import SalesOrder
    
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


@bp.post("/sales-orders/import-pdf-bulk")
@require_permission("sales_orders.import")
def sales_orders_import_pdf_bulk():
    """Bulk PDF import (multiple files)."""
    from app.eqms.modules.rep_traceability.models import SalesOrder
    s = db_session()
    u = _current_user()
    files = request.files.getlist("pdf_files")
    if not files:
        flash("Choose one or more PDFs to upload.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))

    total_orders = 0
    total_errors = 0
    for f in files:
        if not f or not f.filename:
            continue
        pdf_bytes = f.read()
        result = parse_sales_orders_pdf(pdf_bytes)
        if result.errors and not result.lines:
            total_errors += len(result.errors)
            # Store unlinked PDF for manual review
            _store_pdf_attachment(
                s,
                pdf_bytes=pdf_bytes,
                filename=f.filename,
                pdf_type="unparsed",
                sales_order_id=None,
                distribution_entry_id=None,
                user=u,
            )
            continue

        # Process parsed orders
        for order_data in result.orders:
            order_number = order_data["order_number"]
            order_date = order_data["order_date"]
            customer_name = order_data["customer_name"]

            try:
                customer = find_or_create_customer(s, facility_name=customer_name)
            except Exception:
                total_errors += 1
                continue

            external_key = f"pdf:{order_number}:{order_date.isoformat()}"
            existing_order = (
                s.query(SalesOrder)
                .filter(SalesOrder.source == "pdf_import", SalesOrder.external_key == external_key)
                .first()
            )
            if existing_order:
                continue

            sales_order = SalesOrder(
                order_number=order_number,
                order_date=order_date,
                ship_date=order_data.get("ship_date") or order_date,
                customer_id=customer.id,
                source="pdf_import",
                external_key=external_key,
                status="completed",
                created_by_user_id=u.id,
                updated_by_user_id=u.id,
            )
            s.add(sales_order)
            s.flush()

            _store_pdf_attachment(
                s,
                pdf_bytes=pdf_bytes,
                filename=f.filename,
                pdf_type="sales_order",
                sales_order_id=sales_order.id,
                distribution_entry_id=None,
                user=u,
            )
            total_orders += 1

        s.commit()

    flash(f"Bulk PDF import processed. Orders created: {total_orders}. Errors: {total_errors}.", "success")
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


@bp.post("/sales-orders/import-pdf")
@require_permission("sales_orders.import")
def sales_orders_import_pdf_post():
    """Import sales orders, lines, AND linked distributions from PDF.
    
    This is the consolidated PDF import route - creates complete records
    with sales_order → sales_order_lines → distribution_log_entries linkage.
    """
    from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
    from datetime import datetime
    
    s = db_session()
    u = _current_user()
    
    f = request.files.get("pdf_file")
    if not f or not f.filename:
        flash("Choose a PDF file to import.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    # Parse PDF
    pdf_bytes = f.read()
    result = parse_sales_orders_pdf(pdf_bytes)
    
    if result.errors and not result.lines:
        error_msgs = [e.message for e in result.errors[:5]]
        _store_pdf_attachment(
            s,
            pdf_bytes=pdf_bytes,
            filename=f.filename,
            pdf_type="unparsed",
            sales_order_id=None,
            distribution_entry_id=None,
            user=u,
        )
        s.commit()
        flash(f"PDF parse errors: {'; '.join(error_msgs)}", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    # Process parsed orders
    created_orders = 0
    created_lines = 0
    created_distributions = 0
    skipped_duplicates = 0
    
    for order_data in result.orders:
        order_number = order_data["order_number"]
        order_date = order_data["order_date"]
        customer_name = order_data["customer_name"]
        
        # Find or create customer
        try:
            customer = find_or_create_customer(s, facility_name=customer_name)
        except Exception as e:
            flash(f"Error creating customer '{customer_name}': {e}", "danger")
            continue
        
        # Check if sales order already exists
        external_key = f"pdf:{order_number}:{order_date.isoformat()}"
        existing_order = (
            s.query(SalesOrder)
            .filter(SalesOrder.source == "pdf_import", SalesOrder.external_key == external_key)
            .first()
        )
        
        if existing_order:
            skipped_duplicates += 1
            continue
        
        # Create sales order
        sales_order = SalesOrder(
            order_number=order_number,
            order_date=order_date,
            ship_date=order_date,
            customer_id=customer.id,
            source="pdf_import",
            external_key=external_key,
            status="completed",
            created_by_user_id=u.id,
            updated_by_user_id=u.id,
        )
        s.add(sales_order)
        s.flush()
        created_orders += 1

        _store_pdf_attachment(
            s,
            pdf_bytes=pdf_bytes,
            filename=f.filename,
            pdf_type="sales_order",
            sales_order_id=sales_order.id,
            distribution_entry_id=None,
            user=u,
        )
        
        # Create order lines AND linked distribution entries
        for line_num, line_data in enumerate(order_data["lines"], start=1):
            sku = line_data["sku"]
            quantity = line_data["quantity"]
            lot_number = line_data.get("lot_number") or "UNKNOWN"
            
            # Create order line
            order_line = SalesOrderLine(
                sales_order_id=sales_order.id,
                sku=sku,
                quantity=quantity,
                lot_number=lot_number,
                line_number=line_num,
            )
            s.add(order_line)
            created_lines += 1
            
            # Create linked distribution entry
            dist_external_key = f"pdf:{order_number}:{order_date.isoformat()}:{sku}:{lot_number}"
            existing_dist = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.source == "pdf_import", DistributionLogEntry.external_key == dist_external_key)
                .first()
            )
            
            if not existing_dist:
                dist = DistributionLogEntry(
                    ship_date=order_date,
                    order_number=order_number,
                    facility_name=customer.facility_name,
                    customer_id=customer.id,
                    customer_name=customer.facility_name,
                    sales_order_id=sales_order.id,
                    sku=sku,
                    lot_number=lot_number,
                    quantity=quantity,
                    source="pdf_import",
                    external_key=dist_external_key,
                    created_by_user_id=u.id,
                    updated_by_user_id=u.id,
                    updated_at=datetime.utcnow(),
                )
                s.add(dist)
                created_distributions += 1
    
    # Audit event
    from app.eqms.audit import record_event
    record_event(
        s,
        actor=u,
        action="sales_orders.import_pdf",
        entity_type="SalesOrder",
        entity_id="pdf_import",
        metadata={
            "orders_created": created_orders,
            "lines_created": created_lines,
            "distributions_created": created_distributions,
            "skipped_duplicates": skipped_duplicates,
            "parse_errors": len(result.errors),
        },
    )
    s.commit()
    
    msg = f"PDF import complete: {created_orders} orders, {created_lines} lines, {created_distributions} distributions."
    if skipped_duplicates:
        msg += f" {skipped_duplicates} duplicate orders skipped."
    if result.errors:
        msg += f" {len(result.errors)} parse warnings."
    
    flash(msg, "success")
    return redirect(url_for("rep_traceability.sales_orders_list"))


# ============================================================================
# Sales Dashboard AJAX Endpoints (Dropdown Details)
# ============================================================================

@bp.get("/sales-dashboard/order-details/<order_number>")
@require_permission("sales_dashboard.view")
def sales_dashboard_order_details(order_number: str):
    """Return JSON with order details for dropdown."""
    from flask import jsonify
    from app.eqms.modules.rep_traceability.models import SalesOrder, SalesOrderLine
    
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
    })

