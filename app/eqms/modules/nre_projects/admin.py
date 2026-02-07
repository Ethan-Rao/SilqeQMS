from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from flask import abort, flash, g, redirect, render_template, request, url_for, current_app, send_file

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.rbac import require_permission
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder, OrderPdfAttachment
from app.eqms.modules.nre_projects import bp
from app.eqms.storage import storage_from_config


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


@bp.get("/")
@require_permission("sales_orders.view")
def nre_projects_index():
    """
    NRE Projects dashboard.
    Customers with sales orders but no distributions.
    """
    s = db_session()

    customers_with_orders = (
        s.query(Customer.id)
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .distinct()
        .subquery()
    )

    customers_with_distributions = (
        s.query(Customer.id)
        .join(DistributionLogEntry, DistributionLogEntry.customer_id == Customer.id)
        .distinct()
        .subquery()
    )

    nre_customers = (
        s.query(Customer)
        .filter(Customer.id.in_(customers_with_orders))
        .filter(~Customer.id.in_(customers_with_distributions))
        .order_by(Customer.facility_name.asc())
        .all()
    )

    order_counts: dict[int, int] = {}
    for c in nre_customers:
        order_counts[c.id] = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()

    return render_template(
        "admin/nre_projects/index.html",
        nre_customers=nre_customers,
        order_counts=order_counts,
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

    return render_template(
        "admin/nre_projects/detail.html",
        customer=customer,
        orders=orders,
        attachments_by_order=attachments_by_order,
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
    
    if not new_name:
        flash("Customer name is required.", "danger")
        return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))
    
    before = {"facility_name": customer.facility_name, "customer_code": customer.customer_code}
    customer.facility_name = new_name
    customer.customer_code = new_code
    customer.updated_at = datetime.utcnow()
    
    record_event(
        s,
        actor=u,
        action="nre_customer.update",
        entity_type="Customer",
        entity_id=str(customer_id),
        metadata={"before": before, "after": {"facility_name": new_name, "customer_code": new_code}},
    )
    s.commit()
    flash("Customer updated.", "success")
    return redirect(url_for("nre_projects.nre_customer_detail", customer_id=customer_id))


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
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(pdf_file.filename) or "document.pdf"
    storage_key = f"sales_orders/{order_id}/pdfs/manual_{timestamp}_{safe_name}"
    
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
