from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from flask import abort, flash, g, jsonify, redirect, render_template, request, url_for, current_app, send_file

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.rbac import require_permission
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder, OrderPdfAttachment
from app.eqms.modules.nre_projects import bp
from app.eqms.modules.nre_projects.models import INVOICE_STATUSES, NREProjectEntry
from app.eqms.storage import storage_from_config
from app.eqms.utils import allow_inline_view, current_user as _current_user, utcnow




def _nre_customers(s):
    """Return the list of customers classified as NRE, honoring customer_type overrides.

    - "auto": has sales orders but no order matched to a distribution (legacy logic)
    - "catheter": always excluded
    - "nre": always included
    """
    from sqlalchemy import or_, select

    customers_with_orders = (
        select(Customer.id)
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .distinct()
    )
    customers_with_matched_distributions = (
        select(Customer.id)
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .join(DistributionLogEntry, DistributionLogEntry.sales_order_id == SalesOrder.id)
        .distinct()
    )

    auto_nre_customer_ids = (
        select(Customer.id)
        .where(Customer.customer_type == "auto")
        .where(Customer.id.in_(customers_with_orders))
        .where(~Customer.id.in_(customers_with_matched_distributions))
    )
    forced_nre_customer_ids = (
        select(Customer.id).where(Customer.customer_type == "nre")
    )

    return (
        s.query(Customer)
        .filter(
            or_(
                Customer.id.in_(auto_nre_customer_ids),
                Customer.id.in_(forced_nre_customer_ids),
            )
        )
        .order_by(Customer.facility_name.asc())
        .all()
    )


@bp.get("/")
@require_permission("sales_orders.view")
def nre_projects_index():
    """NRE Projects dashboard.

    Lists customers classified as NRE (see ``_nre_customers``): auto-classified
    customers with orders but no matched distributions, plus any customer forced
    to ``customer_type == "nre"``. ``"catheter"`` customers are always excluded.
    """
    s = db_session()

    nre_customers = _nre_customers(s)
    nre_customer_ids = [c.id for c in nre_customers]

    order_counts: dict[int, int] = {}
    for c in nre_customers:
        order_counts[c.id] = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()

    # Build aggregate tracker rows: all sales orders for NRE customers, with
    # their existing NREProjectEntry (if any), customer name, and order number.
    tracker_rows: list[dict] = []
    if nre_customer_ids:
        nre_orders = (
            s.query(SalesOrder, Customer)
            .join(Customer, Customer.id == SalesOrder.customer_id)
            .filter(SalesOrder.customer_id.in_(nre_customer_ids))
            .order_by(SalesOrder.order_date.desc())
            .all()
        )
        order_ids = [o.id for o, _ in nre_orders]
        entries_by_order: dict[int, NREProjectEntry] = {}
        if order_ids:
            for e in s.query(NREProjectEntry).filter(NREProjectEntry.sales_order_id.in_(order_ids)).all():
                entries_by_order[e.sales_order_id] = e

        for order, customer in nre_orders:
            entry = entries_by_order.get(order.id)
            tracker_rows.append({
                "customer_id": customer.id,
                "customer_name": customer.facility_name,
                "order_id": order.id,
                "order_number": order.order_number,
                "order_date": order.order_date,
                "entry": entry,
            })

    return render_template(
        "admin/nre_projects/index.html",
        nre_customers=nre_customers,
        order_counts=order_counts,
        tracker_rows=tracker_rows,
        invoice_statuses=INVOICE_STATUSES,
    )


@bp.get("/<int:customer_id>")
@require_permission("sales_orders.view")
def nre_customer_detail(customer_id: int):
    s = db_session()
    customer = s.query(Customer).filter(Customer.id == customer_id).one_or_none()
    if not customer:
        abort(404)

    orders = (
        s.query(SalesOrder)
        .filter(SalesOrder.customer_id == customer_id)
        .order_by(SalesOrder.order_date.desc())
        .all()
    )
    
    # Get PDF attachments for each order
    order_ids = [o.id for o in orders]
    attachments_by_order: dict[int, list[OrderPdfAttachment]] = defaultdict(list)
    if order_ids:
        attachments = (
            s.query(OrderPdfAttachment)
            .filter(OrderPdfAttachment.sales_order_id.in_(order_ids))
            .order_by(OrderPdfAttachment.uploaded_at.desc())
            .all()
        )
        for att in attachments:
            attachments_by_order[att.sales_order_id].append(att)

    # Project tracker entries keyed by sales_order_id
    tracker_by_order: dict[int, NREProjectEntry] = {}
    if order_ids:
        for entry in (
            s.query(NREProjectEntry)
            .filter(NREProjectEntry.sales_order_id.in_(order_ids))
            .all()
        ):
            tracker_by_order[entry.sales_order_id] = entry

    # Admin_docs folders for this customer + per-order subfolders
    from app.eqms.modules.admin_docs.models import AdminDocFolder

    cust_folder = (
        s.query(AdminDocFolder)
        .filter(
            AdminDocFolder.library_key == "nre_projects",
            AdminDocFolder.parent_id.is_(None),
            AdminDocFolder.name == customer.facility_name,
        )
        .first()
    )
    order_folder_ids: dict[int, int] = {}
    if cust_folder:
        for order in orders:
            subfolder = (
                s.query(AdminDocFolder)
                .filter(
                    AdminDocFolder.library_key == "nre_projects",
                    AdminDocFolder.parent_id == cust_folder.id,
                    AdminDocFolder.name == f"SO-{order.order_number}",
                )
                .first()
            )
            if subfolder:
                order_folder_ids[order.id] = subfolder.id

    return render_template(
        "admin/nre_projects/detail.html",
        customer=customer,
        orders=orders,
        attachments_by_order=attachments_by_order,
        tracker_by_order=tracker_by_order,
        invoice_statuses=INVOICE_STATUSES,
        cust_folder=cust_folder,
        order_folder_ids=order_folder_ids,
    )


@bp.post("/<int:customer_id>/edit")
@require_permission("sales_orders.edit")
def nre_customer_edit(customer_id: int):
    """Update NRE customer name and customer_code."""
    from app.eqms.audit import record_event
    
    s = db_session()
    u = _current_user()
    customer = s.query(Customer).filter(Customer.id == customer_id).one_or_none()
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for("nre_projects.nre_projects_index"))
    
    new_name = (request.form.get("facility_name") or "").strip()
    new_code = (request.form.get("customer_code") or "").strip().upper() or None
    new_type = (request.form.get("customer_type") or "").strip().lower()
    if new_type not in ("auto", "catheter", "nre"):
        new_type = customer.customer_type or "auto"

    if not new_name:
        flash("Customer name is required.", "danger")
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))
    
    before = {
        "facility_name": customer.facility_name,
        "customer_code": customer.customer_code,
        "customer_type": customer.customer_type,
    }
    customer.facility_name = new_name
    customer.customer_code = new_code
    customer.customer_type = new_type
    customer.updated_at = utcnow()
    
    record_event(
        s,
        actor=u,
        action="nre_customer.update",
        entity_type="Customer",
        entity_id=str(customer_id),
        metadata={"before": before, "after": {"facility_name": new_name, "customer_code": new_code, "customer_type": new_type}},
    )
    s.commit()
    flash("Customer updated.", "success")
    return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))


# ─────────────────────────────────────────────────────────────────────────────
# NRE Project Tracker (NREProjectEntry CRUD)
# ─────────────────────────────────────────────────────────────────────────────


def _parse_amount(value):
    from decimal import Decimal, InvalidOperation

    if value is None:
        return None
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def _parse_iso_date(value):
    from datetime import date as _date

    v = (str(value).strip() if value is not None else "")
    if not v:
        return None
    try:
        return _date.fromisoformat(v)
    except ValueError:
        return None


def _entry_to_dict(e: NREProjectEntry) -> dict:
    return {
        "id": e.id,
        "sales_order_id": e.sales_order_id,
        "invoice_amount": str(e.invoice_amount) if e.invoice_amount is not None else "",
        "expected_invoice_date": e.expected_invoice_date.isoformat() if e.expected_invoice_date else "",
        "invoice_status": e.invoice_status,
        "notes": e.notes or "",
    }


def _apply_entry_fields(e: NREProjectEntry, src) -> None:
    """Populate an NREProjectEntry from a form/JSON dict (partial-friendly)."""
    if "invoice_amount" in src:
        e.invoice_amount = _parse_amount(src.get("invoice_amount"))
    if "expected_invoice_date" in src:
        e.expected_invoice_date = _parse_iso_date(src.get("expected_invoice_date"))
    if "invoice_status" in src:
        status = (src.get("invoice_status") or "").strip()
        if status in INVOICE_STATUSES:
            e.invoice_status = status
    if "notes" in src:
        e.notes = (src.get("notes") or "").strip() or None


@bp.post("/<int:customer_id>/tracker")
@require_permission("sales_orders.edit")
def nre_tracker_upsert(customer_id: int):
    """Create or update the tracker entry for a sales order (by sales_order_id)."""
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()
    src = request.get_json(silent=True) if request.is_json else request.form
    src = dict(src or {})

    try:
        sales_order_id = int(src.get("sales_order_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "sales_order_id required"}), 400

    order = (
        s.query(SalesOrder)
        .filter(SalesOrder.id == sales_order_id, SalesOrder.customer_id == customer_id)
        .one_or_none()
    )
    if not order:
        return jsonify({"ok": False, "error": "order not found"}), 404

    entry = s.query(NREProjectEntry).filter(NREProjectEntry.sales_order_id == sales_order_id).one_or_none()
    created = entry is None
    if entry is None:
        entry = NREProjectEntry(sales_order_id=sales_order_id, created_by_user_id=u.id if u else None)
        s.add(entry)
    _apply_entry_fields(entry, src)
    if u:
        entry.updated_by_user_id = u.id
    s.flush()
    record_event(
        s, actor=u,
        action="nre_tracker.create" if created else "nre_tracker.update",
        entity_type="NREProjectEntry", entity_id=str(entry.id),
    )
    s.commit()
    return jsonify({"ok": True, "entry": _entry_to_dict(entry)})


@bp.patch("/tracker/<int:entry_id>")
@require_permission("sales_orders.edit")
def nre_tracker_patch(entry_id: int):
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()
    entry = s.get(NREProjectEntry, entry_id)
    if not entry:
        abort(404)
    src = request.get_json(silent=True) if request.is_json else request.form
    _apply_entry_fields(entry, dict(src or {}))
    if u:
        entry.updated_by_user_id = u.id
    entry.updated_at = utcnow()
    record_event(
        s, actor=u, action="nre_tracker.update",
        entity_type="NREProjectEntry", entity_id=str(entry.id),
    )
    s.commit()
    return jsonify({"ok": True, "entry": _entry_to_dict(entry)})


@bp.delete("/tracker/<int:entry_id>")
@require_permission("sales_orders.edit")
def nre_tracker_delete(entry_id: int):
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()
    entry = s.get(NREProjectEntry, entry_id)
    if not entry:
        abort(404)
    s.delete(entry)
    record_event(
        s, actor=u, action="nre_tracker.delete",
        entity_type="NREProjectEntry", entity_id=str(entry_id),
    )
    s.commit()
    return jsonify({"ok": True})


@bp.post("/refresh-folders")
@require_permission("sales_orders.edit")
def nre_refresh_folders():
    """Create any missing admin_docs folders for NRE customers + their orders."""
    from app.eqms.modules.admin_docs.models import AdminDocFolder
    from app.eqms.modules.admin_docs.service import create_folder

    s = db_session()
    u = _current_user()
    created = skipped = 0

    for customer in _nre_customers(s):
        cust_folder = (
            s.query(AdminDocFolder)
            .filter(
                AdminDocFolder.library_key == "nre_projects",
                AdminDocFolder.parent_id.is_(None),
                AdminDocFolder.name == customer.facility_name,
            )
            .first()
        )
        if cust_folder is None:
            cust_folder = create_folder(s, "nre_projects", customer.facility_name, u, parent=None)
            created += 1
        else:
            skipped += 1

        orders = s.query(SalesOrder).filter(SalesOrder.customer_id == customer.id).all()
        for order in orders:
            sub_name = f"SO-{order.order_number}"
            existing = (
                s.query(AdminDocFolder)
                .filter(
                    AdminDocFolder.library_key == "nre_projects",
                    AdminDocFolder.parent_id == cust_folder.id,
                    AdminDocFolder.name == sub_name,
                )
                .first()
            )
            if existing is None:
                create_folder(s, "nre_projects", sub_name, u, parent=cust_folder)
                created += 1
            else:
                skipped += 1

    s.commit()
    flash(f"Folders refreshed: {created} created, {skipped} already existed.", "success")
    return redirect(url_for("nre_projects.nre_projects_index"))


@bp.post("/<int:customer_id>/orders/<int:order_id>/upload-pdf")
@require_permission("sales_orders.edit")
def nre_order_upload_pdf(customer_id: int, order_id: int):
    """Upload a PDF attachment to a specific sales order."""
    from werkzeug.utils import secure_filename
    
    s = db_session()
    u = _current_user()
    
    order = s.query(SalesOrder).filter(SalesOrder.id == order_id, SalesOrder.customer_id == customer_id).one_or_none()
    if not order:
        flash("Sales order not found.", "danger")
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))
    
    pdf_file = request.files.get("pdf_file")
    if not pdf_file or not pdf_file.filename:
        flash("Please select a PDF file.", "danger")
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))
    
    pdf_bytes = pdf_file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:  # 10MB limit
        flash("File too large (max 10MB).", "danger")
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))
    
    storage = storage_from_config(current_app.config)
    timestamp = utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(pdf_file.filename) or "document.pdf"
    # Use order_number for stable storage key
    storage_key = f"sales_orders/{order.order_number}/pdfs/manual_{timestamp}_{safe_name}"
    
    try:
        storage.put_bytes(storage_key, pdf_bytes, content_type="application/pdf")
    except Exception as e:
        flash(f"Storage error: {e}", "danger")
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))
    
    attachment = OrderPdfAttachment(
        sales_order_id=order_id,
        distribution_entry_id=None,
        storage_key=storage_key,
        filename=pdf_file.filename,
        pdf_type="manual_upload",
        uploaded_by_user_id=u.id,
    )
    s.add(attachment)
    s.commit()
    
    flash(f"PDF '{pdf_file.filename}' uploaded successfully.", "success")
    return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))


@bp.get("/attachments/<int:attachment_id>/download")
@require_permission("sales_orders.view")
def nre_download_pdf(attachment_id: int):
    """Download a PDF attachment."""
    import io
    
    s = db_session()
    attachment = s.query(OrderPdfAttachment).filter(OrderPdfAttachment.id == attachment_id).one_or_none()
    if not attachment:
        abort(404)
    
    storage = storage_from_config(current_app.config)
    try:
        pdf_bytes = storage.get_bytes(attachment.storage_key)
    except Exception:
        flash("PDF not found in storage.", "danger")
        return redirect(request.referrer or url_for("nre_projects.nre_projects_index"))
    
    return send_file(
        io.BytesIO(pdf_bytes),
        download_name=attachment.filename,
        as_attachment=True,
        mimetype="application/pdf",
    )


@bp.get("/attachments/<int:attachment_id>/view")
@require_permission("sales_orders.view")
def nre_view_pdf(attachment_id: int):
    """View a PDF attachment inline when supported."""
    s = db_session()
    attachment = s.query(OrderPdfAttachment).filter(OrderPdfAttachment.id == attachment_id).one_or_none()
    if not attachment:
        abort(404)

    storage = storage_from_config(current_app.config)
    try:
        fobj = storage.open(attachment.storage_key)
    except Exception:
        flash("PDF not found in storage.", "danger")
        return redirect(request.referrer or url_for("nre_projects.nre_projects_index"))

    inline = allow_inline_view(attachment.filename, "application/pdf")
    return send_file(
        fobj,
        download_name=attachment.filename,
        as_attachment=not inline,
        mimetype="application/pdf",
    )


@bp.post("/attachments/<int:attachment_id>/delete")
@require_permission("sales_orders.edit")
def nre_delete_pdf(attachment_id: int):
    """Delete a PDF attachment."""
    from app.eqms.audit import record_event
    
    s = db_session()
    u = _current_user()
    attachment = s.query(OrderPdfAttachment).filter(OrderPdfAttachment.id == attachment_id).one_or_none()
    if not attachment:
        flash("Attachment not found.", "danger")
        return redirect(request.referrer or url_for("nre_projects.nre_projects_index"))
    
    # Get the customer_id for redirect
    customer_id = None
    if attachment.sales_order_id:
        order = s.query(SalesOrder).filter(SalesOrder.id == attachment.sales_order_id).one_or_none()
        if order:
            customer_id = order.customer_id
    
    # Delete from storage
    storage = storage_from_config(current_app.config)
    try:
        storage.delete(attachment.storage_key)
    except Exception:
        pass  # File may not exist, continue with DB cleanup
    
    record_event(
        s,
        actor=u,
        action="pdf_attachment.delete",
        entity_type="OrderPdfAttachment",
        entity_id=str(attachment_id),
        metadata={"filename": attachment.filename, "storage_key": attachment.storage_key},
    )
    s.delete(attachment)
    s.commit()
    
    flash("PDF deleted.", "success")
    if customer_id:
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))
    return redirect(url_for("nre_projects.nre_projects_index"))
