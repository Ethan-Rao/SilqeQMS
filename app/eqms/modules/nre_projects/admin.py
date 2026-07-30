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
from app.eqms.modules.nre_projects.models import INVOICE_STATUSES, NREProjectEntry, NRETrackerAttachment
from app.eqms.storage import storage_from_config
from app.eqms.utils import allow_inline_view, current_user as _current_user, utcnow




def _nre_customers(s):
    """Return the list of customers classified as NRE, honoring customer_type overrides.

    - "auto": has sales orders, no matched distribution, and **no catheter-SKU SOs**
      (P41: catheter product without a distribution must not auto-classify as NRE)
    - "catheter": always excluded
    - "nre": always included
    """
    from sqlalchemy import or_, select

    from app.eqms.modules.rep_traceability.models import SalesOrderLine
    from app.eqms.modules.rep_traceability.service import CATHETER_SKUS

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
    customers_with_catheter_sku_orders = (
        select(Customer.id)
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .join(SalesOrderLine, SalesOrderLine.sales_order_id == SalesOrder.id)
        .where(SalesOrderLine.sku.in_(tuple(CATHETER_SKUS)))
        .distinct()
    )

    auto_nre_customer_ids = (
        select(Customer.id)
        .where(Customer.customer_type == "auto")
        .where(Customer.id.in_(customers_with_orders))
        .where(~Customer.id.in_(customers_with_matched_distributions))
        .where(~Customer.id.in_(customers_with_catheter_sku_orders))
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
    from datetime import date as date_cls
    from decimal import Decimal

    s = db_session()

    nre_customers = _nre_customers(s)
    nre_ids = [c.id for c in nre_customers]

    # Orders per customer (for expand panels + sort by most recent order_date).
    orders_by_customer: dict[int, list[SalesOrder]] = defaultdict(list)
    order_counts: dict[int, int] = {}
    latest_order_date: dict[int, date_cls | None] = {}
    if nre_ids:
        all_orders = (
            s.query(SalesOrder)
            .filter(SalesOrder.customer_id.in_(nre_ids))
            .order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc())
            .all()
        )
        for o in all_orders:
            orders_by_customer[o.customer_id].append(o)
        for cid, orders in orders_by_customer.items():
            order_counts[cid] = len(orders)
            latest_order_date[cid] = orders[0].order_date if orders else None

    # Sort customer cards by most recent sales order date (desc); no orders last.
    nre_customers = sorted(
        nre_customers,
        key=lambda c: (latest_order_date.get(c.id) is not None, latest_order_date.get(c.id) or date_cls.min),
        reverse=True,
    )

    # Free-form NRE invoice ledger (most recent first)
    tracker_entries = (
        s.query(NREProjectEntry)
        .order_by(NREProjectEntry.entry_date.desc().nullslast(), NREProjectEntry.created_at.desc())
        .all()
    )

    entry_ids = [e.id for e in tracker_entries]
    attachments_by_nre: dict[int, list[NRETrackerAttachment]] = defaultdict(list)
    if entry_ids:
        atts = (
            s.query(NRETrackerAttachment)
            .filter(NRETrackerAttachment.nre_entry_id.in_(entry_ids))
            .all()
        )
        for a in atts:
            attachments_by_nre[a.nre_entry_id].append(a)

    # NRE Dashboard metrics — filter by Order Date; default = current calendar quarter → today.
    today = date_cls.today()
    quarter_month_start = ((today.month - 1) // 3) * 3 + 1
    default_start = date_cls(today.year, quarter_month_start, 1)
    start_s = (request.args.get("start") or "").strip()
    end_s = (request.args.get("end") or "").strip()
    try:
        dash_start = date_cls.fromisoformat(start_s) if start_s else default_start
    except ValueError:
        dash_start = default_start
    try:
        dash_end = date_cls.fromisoformat(end_s) if end_s else today
    except ValueError:
        dash_end = today

    filtered_orders = []
    if nre_ids:
        filtered_orders = (
            s.query(SalesOrder)
            .filter(
                SalesOrder.customer_id.in_(nre_ids),
                SalesOrder.order_date >= dash_start,
                SalesOrder.order_date <= dash_end,
            )
            .order_by(SalesOrder.order_date.desc(), SalesOrder.order_number.desc())
            .all()
        )
    dash_project_count = len(filtered_orders)
    dash_customer_count = len({o.customer_id for o in filtered_orders})
    amounts = [o.order_amount for o in filtered_orders if o.order_amount is not None]
    dash_revenue = sum(amounts, Decimal("0"))
    dash_missing_amounts = dash_project_count - len(amounts)
    customers_by_id = {c.id: c for c in nre_customers}

    return render_template(
        "admin/nre_projects/index.html",
        nre_customers=nre_customers,
        order_counts=order_counts,
        orders_by_customer=orders_by_customer,
        tracker_entries=tracker_entries,
        invoice_statuses=INVOICE_STATUSES,
        attachments_by_nre=attachments_by_nre,
        dash_start=dash_start,
        dash_end=dash_end,
        dash_project_count=dash_project_count,
        dash_customer_count=dash_customer_count,
        dash_revenue=dash_revenue,
        dash_missing_amounts=dash_missing_amounts,
        dash_orders=filtered_orders,
        customers_by_id=customers_by_id,
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
        .order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc())
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

    # Most recent SO drives Sold To / Ship To display (P40).
    latest = orders[0] if orders else None
    sold_to = {
        "address1": (latest.sold_to_address1 if latest and latest.sold_to_address1 else customer.sold_to_address1),
        "city": (latest.sold_to_city if latest and latest.sold_to_city else customer.sold_to_city),
        "state": (latest.sold_to_state if latest and latest.sold_to_state else customer.sold_to_state),
        "zip": (latest.sold_to_zip if latest and latest.sold_to_zip else customer.sold_to_zip),
    }
    ship_to = {
        "name": (latest.ship_to_name if latest else None),
        "address1": (latest.ship_to_address1 if latest and latest.ship_to_address1 else customer.address1),
        "city": (latest.ship_to_city if latest and latest.ship_to_city else customer.city),
        "state": (latest.ship_to_state if latest and latest.ship_to_state else customer.state),
        "zip": (latest.ship_to_zip if latest and latest.ship_to_zip else customer.zip),
    }

    return render_template(
        "admin/nre_projects/detail.html",
        customer=customer,
        orders=orders,
        attachments_by_order=attachments_by_order,
        cust_folder=cust_folder,
        order_folder_ids=order_folder_ids,
        sold_to=sold_to,
        ship_to=ship_to,
    )


@bp.post("/<int:customer_id>/orders/<int:order_id>/invoice-date")
@require_permission("sales_orders.edit")
def nre_order_invoice_date(customer_id: int, order_id: int):
    """Set SalesOrder.invoice_date from the NRE customer profile."""
    from app.eqms.audit import record_event
    from app.eqms.modules.purchasing.service import parse_date

    s = db_session()
    u = _current_user()
    customer = s.query(Customer).filter(Customer.id == customer_id).one_or_none()
    order = s.get(SalesOrder, order_id)
    if not customer or not order or order.customer_id != customer.id:
        abort(404)
    raw = (request.form.get("invoice_date") or "").strip()
    order.invoice_date = parse_date(raw) if raw else None
    record_event(
        s, actor=u, action="sales_order.invoice_date",
        entity_type="SalesOrder", entity_id=str(order.id),
        metadata={"invoice_date": order.invoice_date.isoformat() if order.invoice_date else None},
    )
    s.commit()
    flash("Invoice date updated.", "success")
    if (request.form.get("next") or "").strip() == "index":
        return redirect(url_for("nre_projects.nre_projects_index"))
    return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))


@bp.post("/<int:customer_id>/orders/<int:order_id>/delete")
@require_permission("sales_orders.edit")
def nre_order_delete(customer_id: int, order_id: int):
    """Delete a sales order; remove orphan auto-customer when no SOs/dists remain."""
    from app.eqms.modules.rep_traceability.service import delete_sales_order_with_cleanup

    s = db_session()
    u = _current_user()
    customer = s.query(Customer).filter(Customer.id == customer_id).one_or_none()
    order = s.get(SalesOrder, order_id)
    if not customer or not order or order.customer_id != customer.id:
        abort(404)

    storage = storage_from_config(current_app.config)
    result = delete_sales_order_with_cleanup(s, order, user=u, storage=storage)
    s.commit()

    if result.get("deleted_customer_id"):
        flash(
            f"Deleted sales order {result['order_number']} and removed orphan customer profile.",
            "success",
        )
        return redirect(url_for("nre_projects.nre_projects_index"))
    flash(f"Deleted sales order {result['order_number']}.", "success")
    return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))


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

    contact_name = (request.form.get("contact_name") or "").strip() or None
    contact_email_raw = (request.form.get("contact_email") or "").strip()
    contact_email = contact_email_raw or None
    if contact_email and ("@" not in contact_email or " " in contact_email):
        flash("Contact email looks invalid.", "danger")
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))

    if not new_name:
        flash("Customer name is required.", "danger")
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))
    
    before = {
        "facility_name": customer.facility_name,
        "customer_code": customer.customer_code,
        "customer_type": customer.customer_type,
        "contact_name": customer.contact_name,
        "contact_email": customer.contact_email,
    }
    customer.facility_name = new_name
    customer.customer_code = new_code
    customer.customer_type = new_type
    customer.contact_name = contact_name
    customer.contact_email = contact_email
    customer.updated_at = utcnow()
    
    record_event(
        s,
        actor=u,
        action="nre_customer.update",
        entity_type="Customer",
        entity_id=str(customer_id),
        metadata={
            "before": before,
            "after": {
                "facility_name": new_name,
                "customer_code": new_code,
                "customer_type": new_type,
                "contact_name": contact_name,
                "contact_email": contact_email,
            },
        },
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
        "entry_date": e.entry_date.isoformat() if e.entry_date else "",
        "customer_name": e.customer_name or "",
        "order_ref": e.order_ref or "",
        "description": e.description or "",
        "invoice_amount": str(e.invoice_amount) if e.invoice_amount is not None else "",
        "expected_invoice_date": e.expected_invoice_date.isoformat() if e.expected_invoice_date else "",
        "invoice_status": e.invoice_status,
        "notes": e.notes or "",
    }


def _apply_entry_fields(e: NREProjectEntry, src) -> None:
    """Populate an NREProjectEntry from a form/JSON dict (partial-friendly)."""
    if "entry_date" in src:
        e.entry_date = _parse_iso_date(src.get("entry_date"))
    if "customer_name" in src:
        e.customer_name = (src.get("customer_name") or "").strip() or None
    if "order_ref" in src:
        e.order_ref = (src.get("order_ref") or "").strip() or None
    if "description" in src:
        e.description = (src.get("description") or "").strip() or None
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


@bp.post("/tracker/create")
@require_permission("sales_orders.edit")
def nre_tracker_create():
    """Create a free-form NRE invoice ledger entry (not tied to a sales order)."""
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()
    src = request.get_json(silent=True) if request.is_json else request.form
    src = dict(src or {})

    entry = NREProjectEntry(created_by_user_id=u.id if u else None)
    _apply_entry_fields(entry, src)
    if u:
        entry.updated_by_user_id = u.id
    s.add(entry)
    s.flush()
    record_event(
        s, actor=u, action="nre_tracker.create",
        entity_type="NREProjectEntry", entity_id=str(entry.id),
    )
    s.commit()
    return jsonify({"ok": True, "entry": _entry_to_dict(entry)})


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

    entry = s.query(NREProjectEntry).filter(NREProjectEntry.sales_order_id == sales_order_id).first()
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


# ─────────────────────────────────────────────────────────────────────────────
# NRE tracker file attachments
# ─────────────────────────────────────────────────────────────────────────────


@bp.post("/tracker/<int:entry_id>/files")
@require_permission("sales_orders.edit")
def nre_tracker_attach_file(entry_id: int):
    from werkzeug.utils import secure_filename
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()
    entry = s.get(NREProjectEntry, entry_id)
    if not entry:
        abort(404)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("nre_projects.nre_projects_index"))

    file_bytes = f.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        flash("File too large (max 50MB).", "danger")
        return redirect(url_for("nre_projects.nre_projects_index"))

    safe_name = secure_filename(f.filename) or "file"
    storage_key = f"nre/tracker_files/{entry_id}/{safe_name}"
    storage = storage_from_config(current_app.config)
    try:
        storage.put_bytes(storage_key, file_bytes, content_type=f.mimetype or "application/octet-stream")
    except Exception as e:  # noqa: BLE001
        flash(f"Storage error: {e}", "danger")
        return redirect(url_for("nre_projects.nre_projects_index"))

    att = NRETrackerAttachment(
        nre_entry_id=entry_id,
        filename=f.filename,
        storage_key=storage_key,
        content_type=f.mimetype or "application/octet-stream",
        size_bytes=len(file_bytes),
        uploaded_by_user_id=u.id if u else None,
    )
    s.add(att)
    record_event(
        s, actor=u, action="nre_tracker.attach_file",
        entity_type="NRETrackerAttachment", entity_id=str(entry_id),
        metadata={"filename": f.filename},
    )
    s.commit()
    flash("File uploaded.", "success")
    return redirect(url_for("nre_projects.nre_projects_index"))


@bp.get("/tracker/files/<int:att_id>/view")
@require_permission("sales_orders.view")
def nre_tracker_file_view(att_id: int):
    from app.eqms.document_viewer import needs_server_render, render_document_to_response

    s = db_session()
    att = s.get(NRETrackerAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)

    if needs_server_render(att.filename):
        file_bytes = storage.get_bytes(att.storage_key)
        download_url = url_for("nre_projects.nre_tracker_file_download", att_id=att_id)
        response = render_document_to_response(
            file_bytes, att.filename, att.content_type or "application/octet-stream",
            download_url=download_url,
        )
        if response:
            return response

    fobj = storage.open(att.storage_key)
    inline = allow_inline_view(att.filename, att.content_type or "application/octet-stream")
    return send_file(
        fobj,
        mimetype=att.content_type or "application/octet-stream",
        as_attachment=not inline,
        download_name=att.filename,
    )


@bp.get("/tracker/files/<int:att_id>/download")
@require_permission("sales_orders.view")
def nre_tracker_file_download(att_id: int):
    s = db_session()
    att = s.get(NRETrackerAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)
    fobj = storage.open(att.storage_key)
    return send_file(
        fobj,
        mimetype=att.content_type or "application/octet-stream",
        as_attachment=True,
        download_name=att.filename,
    )


@bp.post("/tracker/files/<int:att_id>/delete")
@require_permission("sales_orders.edit")
def nre_tracker_file_delete(att_id: int):
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()
    att = s.get(NRETrackerAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)
    try:
        storage.delete(att.storage_key)
    except Exception:
        pass
    record_event(
        s, actor=u, action="nre_tracker.delete_file",
        entity_type="NRETrackerAttachment", entity_id=str(att_id),
        metadata={"filename": att.filename},
    )
    s.delete(att)
    s.commit()
    flash("File deleted.", "success")
    return redirect(url_for("nre_projects.nre_projects_index"))


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
