from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, send_file, url_for

from app.eqms.audit import record_event
from app.eqms.db import db_session
from app.eqms.document_viewer import needs_server_render, render_document_to_response
from app.eqms.models import User
from app.eqms.modules.purchasing.models import (
    InvoiceReceivedAttachment,
    InvoiceReceivedEntry,
    PaymentEntry,
    PaymentEntryAttachment,
    PaymentLineItem,
    PaymentLineItemAttachment,
    PurchaseOrder,
    PurchaseOrderAttachment,
    PurchaseOrderLine,
)
from app.eqms.modules.purchasing.parsers.pdf import merge_import_metadata, parse_purchase_order_pdf
from app.eqms.modules.purchasing.service import (
    _invoice_row_snapshot,
    _payment_row_snapshot,
    append_po_lines_if_empty,
    apply_po_blank_fills,
    build_po_log_xlsx,
    cleanup_stale_temp_po_pdfs,
    create_purchase_order,
    delete_staged_po_pdf,
    document_po_closed,
    import_po_log,
    InvoiceFlowError,
    mark_invoice_other_payment,
    match_invoice_to_po,
    migrate_payment_to_invoice,
    parse_date,
    parse_eml_file,
    parse_line_items,
    reopen_po,
    resolve_supplier_by_extracted_name,
    return_invoice_to_received,
    return_invoice_to_upcoming,
    stage_po_pdf_bytes,
    unmatch_invoice_from_po,
    update_purchase_order,
    upload_purchase_order_attachment,
    validate_purchase_order_payload,
)
from app.eqms.modules.suppliers.models import Supplier
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config
from app.eqms.utils import allow_inline_view, current_user as _current_user, utcnow

bp = Blueprint("purchasing", __name__)


@bp.get("/purchasing")
@require_permission("purchasing.view")
def purchasing_list():
    from sqlalchemy import func

    s = db_session()
    search = (request.args.get("q") or "").strip()
    status_filter = (request.args.get("status") or "").strip().lower()
    unlinked_only = request.args.get("unlinked") == "1"
    supplier_filter = (request.args.get("supplier_id") or "").strip()
    year_filter = (request.args.get("year") or "").strip()
    try:
        page = max(1, int(request.args.get("page") or 1))
    except (TypeError, ValueError):
        page = 1
    per_page = 25

    def _apply_search(query):
        if search:
            like = f"%{search}%"
            query = query.outerjoin(Supplier, PurchaseOrder.supplier_id == Supplier.id).filter(
                (PurchaseOrder.po_number.ilike(like))
                | (PurchaseOrder.description.ilike(like))
                | (Supplier.name.ilike(like))
            )
        return query

    q = _apply_search(s.query(PurchaseOrder))
    # Open/Closed derives from is_closed (D35), not receipt status.
    if status_filter == "open":
        q = q.filter(PurchaseOrder.is_closed.is_(False))
    elif status_filter == "closed":
        q = q.filter(PurchaseOrder.is_closed.is_(True))
    if unlinked_only:
        q = q.filter(PurchaseOrder.supplier_id.is_(None))
    if supplier_filter:
        try:
            q = q.filter(PurchaseOrder.supplier_id == int(supplier_filter))
        except (TypeError, ValueError):
            supplier_filter = ""
    if year_filter:
        try:
            q = q.filter(func.extract("year", PurchaseOrder.order_date) == int(year_filter))
        except (TypeError, ValueError):
            year_filter = ""

    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    purchase_orders = (
        q.order_by(PurchaseOrder.order_date.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    payment_entries = _sorted_payment_entries(s)
    invoice_received_entries = _sorted_invoice_received(s)
    other_payment_entries = _sorted_other_payments(s)

    from collections import defaultdict

    entry_ids = [e.id for e in payment_entries]
    attachments_by_payment: dict[int, list[PaymentEntryAttachment]] = defaultdict(list)
    if entry_ids:
        atts = (
            s.query(PaymentEntryAttachment)
            .filter(PaymentEntryAttachment.payment_entry_id.in_(entry_ids))
            .all()
        )
        for a in atts:
            attachments_by_payment[a.payment_entry_id].append(a)

    inv_ids = [e.id for e in invoice_received_entries]
    other_ids = [e.id for e in other_payment_entries]
    all_inv_ids = inv_ids + other_ids
    attachments_by_invoice: dict[int, list[InvoiceReceivedAttachment]] = defaultdict(list)
    if all_inv_ids:
        iatts = (
            s.query(InvoiceReceivedAttachment)
            .filter(InvoiceReceivedAttachment.invoice_received_entry_id.in_(all_inv_ids))
            .all()
        )
        for a in iatts:
            attachments_by_invoice[a.invoice_received_entry_id].append(a)

    source_payment_by_invoice: dict[int, PaymentEntry] = {}
    if all_inv_ids:
        linked = (
            s.query(PaymentEntry)
            .filter(PaymentEntry.invoice_received_entry_id.in_(all_inv_ids))
            .all()
        )
        for p in linked:
            if p.invoice_received_entry_id is not None:
                source_payment_by_invoice[p.invoice_received_entry_id] = p

    po_options = (
        s.query(PurchaseOrder)
        .order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.po_number.asc())
        .limit(500)
        .all()
    )

    return render_template(
        "admin/purchasing/list.html",
        purchase_orders=purchase_orders,
        payment_entries=payment_entries,
        attachments_by_payment=attachments_by_payment,
        invoice_received_entries=invoice_received_entries,
        other_payment_entries=other_payment_entries,
        attachments_by_invoice=attachments_by_invoice,
        source_payment_by_invoice=source_payment_by_invoice,
        po_options=po_options,
        search=search,
        status_filter=status_filter,
        unlinked_only=unlinked_only,
        page=page,
        total_pages=total_pages,
        total=total,
        today=date.today(),
    )


# ---------- Upcoming Payments ledger ----------
def _sorted_payment_entries(s) -> list[PaymentEntry]:
    from sqlalchemy import case

    return (
        s.query(PaymentEntry)
        .filter(PaymentEntry.invoice_received_entry_id.is_(None))
        .order_by(
            case((PaymentEntry.payment_due_date.is_(None), 1), else_=0),
            PaymentEntry.payment_due_date.asc(),
            PaymentEntry.id.asc(),
        )
        .all()
    )


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


def _payment_to_dict(e: PaymentEntry) -> dict:
    return {
        "id": e.id,
        "order_date": e.order_date.isoformat() if e.order_date else "",
        "vendor": e.vendor or "",
        "description": e.description or "",
        "amount": str(e.amount) if e.amount is not None else "",
        "payment_due_date": e.payment_due_date.isoformat() if e.payment_due_date else "",
    }


def _apply_payment_fields(e: PaymentEntry, src) -> None:
    """Populate a PaymentEntry from a form dict or JSON dict (partial-friendly)."""
    if "order_date" in src:
        e.order_date = parse_date((src.get("order_date") or "").strip() or None)
    if "vendor" in src:
        e.vendor = (src.get("vendor") or "").strip() or None
    if "description" in src:
        e.description = (src.get("description") or "").strip() or None
    if "amount" in src:
        e.amount = _parse_amount(src.get("amount"))
    if "payment_due_date" in src:
        e.payment_due_date = parse_date((src.get("payment_due_date") or "").strip() or None)


@bp.get("/purchasing/payments")
@require_permission("purchasing.view")
def purchasing_payments_list():
    s = db_session()
    return jsonify([_payment_to_dict(e) for e in _sorted_payment_entries(s)])


@bp.post("/purchasing/payments")
@require_permission("purchasing.edit")
def purchasing_payment_create():
    s = db_session()
    u = _current_user()
    src = request.get_json(silent=True) if request.is_json else request.form
    src = src or {}
    entry = PaymentEntry(created_by_id=u.id)
    # Ensure all fields considered on create.
    merged = {k: src.get(k) for k in ("order_date", "vendor", "description", "amount", "payment_due_date")}
    _apply_payment_fields(entry, merged)
    s.add(entry)
    s.flush()
    record_event(
        s, actor=u, action="payment_entry.create",
        entity_type="PaymentEntry", entity_id=str(entry.id),
    )
    s.commit()
    if request.is_json:
        return jsonify(_payment_to_dict(entry))
    return redirect(url_for("purchasing.purchasing_list"))


@bp.post("/purchasing/payments/<int:entry_id>")
@require_permission("purchasing.edit")
def purchasing_payment_update(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(PaymentEntry, entry_id)
    if not entry:
        abort(404)
    src = request.get_json(silent=True) if request.is_json else request.form
    _apply_payment_fields(entry, src or {})
    entry.updated_at = utcnow()
    record_event(
        s, actor=u, action="payment_entry.update",
        entity_type="PaymentEntry", entity_id=str(entry.id),
    )
    s.commit()
    if request.is_json:
        return jsonify(_payment_to_dict(entry))
    return redirect(url_for("purchasing.purchasing_list"))


@bp.delete("/purchasing/payments/<int:entry_id>")
@require_permission("purchasing.edit")
def purchasing_payment_delete(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(PaymentEntry, entry_id)
    if not entry:
        abort(404)
    meta = _payment_row_snapshot(entry)
    # Delete storage blobs before DB cascade (parent files + line-item files).
    storage = storage_from_config(current_app.config)
    for a in list(entry.attachments or []):
        try:
            storage.delete(a.storage_key)
        except Exception:
            pass
    for li in list(entry.line_items or []):
        for a in list(li.attachments or []):
            try:
                storage.delete(a.storage_key)
            except Exception:
                pass
    s.delete(entry)
    record_event(
        s, actor=u, action="payment_entry.delete",
        entity_type="PaymentEntry", entity_id=str(entry_id),
        metadata=meta,
    )
    s.commit()
    return jsonify({"ok": True})


# ---------- Payment entry file attachments ----------
@bp.post("/purchasing/payments/<int:entry_id>/files")
@require_permission("purchasing.edit")
def payment_attach_file(entry_id: int):
    from werkzeug.utils import secure_filename

    s = db_session()
    u = _current_user()
    entry = s.get(PaymentEntry, entry_id)
    if not entry:
        abort(404)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    file_bytes = f.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        flash("File too large (max 50MB).", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    safe_name = secure_filename(f.filename) or "file"
    storage_key = f"purchasing/payment_files/{entry_id}/{safe_name}"
    storage = storage_from_config(current_app.config)
    try:
        storage.put_bytes(storage_key, file_bytes, content_type=f.mimetype or "application/octet-stream")
    except Exception as e:  # noqa: BLE001
        flash(f"Storage error: {e}", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    att = PaymentEntryAttachment(
        payment_entry_id=entry_id,
        filename=f.filename,
        storage_key=storage_key,
        content_type=f.mimetype or "application/octet-stream",
        size_bytes=len(file_bytes),
        uploaded_by_user_id=u.id if u else None,
    )
    s.add(att)
    record_event(
        s, actor=u, action="payment_entry.attach_file",
        entity_type="PaymentEntryAttachment", entity_id=str(entry_id),
        metadata={"filename": f.filename},
    )
    s.commit()
    flash("File uploaded.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.get("/purchasing/payments/files/<int:att_id>/view")
@require_permission("purchasing.view")
def payment_file_view(att_id: int):
    s = db_session()
    att = s.get(PaymentEntryAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)

    if needs_server_render(att.filename):
        file_bytes = storage.get_bytes(att.storage_key)
        download_url = url_for("purchasing.payment_file_download", att_id=att_id)
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


@bp.get("/purchasing/payments/files/<int:att_id>/download")
@require_permission("purchasing.view")
def payment_file_download(att_id: int):
    s = db_session()
    att = s.get(PaymentEntryAttachment, att_id)
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


@bp.post("/purchasing/payments/files/<int:att_id>/delete")
@require_permission("purchasing.edit")
def payment_file_delete(att_id: int):
    s = db_session()
    u = _current_user()
    att = s.get(PaymentEntryAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)
    try:
        storage.delete(att.storage_key)
    except Exception:
        pass
    record_event(
        s, actor=u, action="payment_entry.delete_file",
        entity_type="PaymentEntryAttachment", entity_id=str(att_id),
        metadata={"filename": att.filename},
    )
    s.delete(att)
    s.commit()
    flash("File deleted.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


# ---------- Payment line items (optional sub-rows) ----------
def _line_item_to_dict(li: PaymentLineItem) -> dict:
    if li.amount is None:
        amount_display = ""
    else:
        amount_display = f"${li.amount:,.2f}"
    return {
        "id": li.id,
        "payment_entry_id": li.payment_entry_id,
        "description": li.description or "",
        "amount": str(li.amount) if li.amount is not None else "",
        "amount_display": amount_display,
        "sort_order": li.sort_order,
        "attachments": [
            {
                "id": a.id,
                "filename": a.filename,
                "view_url": url_for("purchasing.payment_line_file_view", att_id=a.id),
                "download_url": url_for("purchasing.payment_line_file_download", att_id=a.id),
                "delete_url": url_for("purchasing.payment_line_file_delete", att_id=a.id),
            }
            for a in (li.attachments or [])
        ],
    }


def _get_line_for_entry(s, entry_id: int, line_id: int) -> PaymentLineItem:
    li = s.get(PaymentLineItem, line_id)
    if not li or li.payment_entry_id != entry_id:
        abort(404)
    return li


@bp.get("/purchasing/payments/<int:entry_id>/lines")
@require_permission("purchasing.view")
def payment_lines_list(entry_id: int):
    s = db_session()
    entry = s.get(PaymentEntry, entry_id)
    if not entry:
        abort(404)
    lines = (
        s.query(PaymentLineItem)
        .filter(PaymentLineItem.payment_entry_id == entry_id)
        .order_by(PaymentLineItem.sort_order.asc(), PaymentLineItem.id.asc())
        .all()
    )
    return jsonify([_line_item_to_dict(li) for li in lines])


@bp.post("/purchasing/payments/<int:entry_id>/lines")
@require_permission("purchasing.edit")
def payment_line_create(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(PaymentEntry, entry_id)
    if not entry:
        abort(404)
    src = request.get_json(silent=True) if request.is_json else request.form
    src = src or {}
    max_sort = (
        s.query(PaymentLineItem)
        .filter(PaymentLineItem.payment_entry_id == entry_id)
        .count()
    )
    li = PaymentLineItem(
        payment_entry_id=entry_id,
        description=(src.get("description") or "").strip() or None,
        amount=_parse_amount(src.get("amount")),
        sort_order=max_sort,
        created_by_user_id=u.id if u else None,
    )
    s.add(li)
    s.flush()
    record_event(
        s, actor=u, action="payment_line_item.create",
        entity_type="PaymentLineItem", entity_id=str(li.id),
        metadata={"payment_entry_id": entry_id},
    )
    s.commit()
    return jsonify(_line_item_to_dict(li))


@bp.post("/purchasing/payments/<int:entry_id>/lines/<int:line_id>")
@require_permission("purchasing.edit")
def payment_line_update(entry_id: int, line_id: int):
    s = db_session()
    u = _current_user()
    li = _get_line_for_entry(s, entry_id, line_id)
    src = request.get_json(silent=True) if request.is_json else request.form
    src = src or {}
    if "description" in src:
        li.description = (src.get("description") or "").strip() or None
    if "amount" in src:
        li.amount = _parse_amount(src.get("amount"))
    if "sort_order" in src:
        try:
            li.sort_order = int(src.get("sort_order"))
        except (TypeError, ValueError):
            pass
    li.updated_at = utcnow()
    record_event(
        s, actor=u, action="payment_line_item.update",
        entity_type="PaymentLineItem", entity_id=str(li.id),
    )
    s.commit()
    return jsonify(_line_item_to_dict(li))


@bp.delete("/purchasing/payments/<int:entry_id>/lines/<int:line_id>")
@require_permission("purchasing.edit")
def payment_line_delete(entry_id: int, line_id: int):
    s = db_session()
    u = _current_user()
    li = _get_line_for_entry(s, entry_id, line_id)
    storage = storage_from_config(current_app.config)
    for a in list(li.attachments or []):
        try:
            storage.delete(a.storage_key)
        except Exception:
            pass
    record_event(
        s, actor=u, action="payment_line_item.delete",
        entity_type="PaymentLineItem", entity_id=str(line_id),
        metadata={"payment_entry_id": entry_id},
    )
    s.delete(li)
    s.commit()
    return jsonify({"ok": True})


@bp.post("/purchasing/payments/<int:entry_id>/lines/<int:line_id>/files")
@require_permission("purchasing.edit")
def payment_line_attach_file(entry_id: int, line_id: int):
    from werkzeug.utils import secure_filename

    s = db_session()
    u = _current_user()
    li = _get_line_for_entry(s, entry_id, line_id)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    file_bytes = f.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        flash("File too large (max 50MB).", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    safe_name = secure_filename(f.filename) or "file"
    storage_key = f"purchasing/payment_line_files/{line_id}/{safe_name}"
    storage = storage_from_config(current_app.config)
    try:
        storage.put_bytes(storage_key, file_bytes, content_type=f.mimetype or "application/octet-stream")
    except Exception as e:  # noqa: BLE001
        flash(f"Storage error: {e}", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    att = PaymentLineItemAttachment(
        payment_line_item_id=line_id,
        filename=f.filename,
        storage_key=storage_key,
        content_type=f.mimetype or "application/octet-stream",
        size_bytes=len(file_bytes),
        uploaded_by_user_id=u.id if u else None,
    )
    s.add(att)
    record_event(
        s, actor=u, action="payment_line_item.attach_file",
        entity_type="PaymentLineItemAttachment", entity_id=str(line_id),
        metadata={"filename": f.filename},
    )
    s.commit()
    flash("File uploaded.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.get("/purchasing/payments/lines/files/<int:att_id>/view")
@require_permission("purchasing.view")
def payment_line_file_view(att_id: int):
    s = db_session()
    att = s.get(PaymentLineItemAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)
    if needs_server_render(att.filename):
        file_bytes = storage.get_bytes(att.storage_key)
        download_url = url_for("purchasing.payment_line_file_download", att_id=att_id)
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


@bp.get("/purchasing/payments/lines/files/<int:att_id>/download")
@require_permission("purchasing.view")
def payment_line_file_download(att_id: int):
    s = db_session()
    att = s.get(PaymentLineItemAttachment, att_id)
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


@bp.post("/purchasing/payments/lines/files/<int:att_id>/delete")
@require_permission("purchasing.edit")
def payment_line_file_delete(att_id: int):
    s = db_session()
    u = _current_user()
    att = s.get(PaymentLineItemAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)
    try:
        storage.delete(att.storage_key)
    except Exception:
        pass
    record_event(
        s, actor=u, action="payment_line_item.delete_file",
        entity_type="PaymentLineItemAttachment", entity_id=str(att_id),
        metadata={"filename": att.filename},
    )
    s.delete(att)
    s.commit()
    flash("File deleted.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.post("/purchasing/payments/<int:entry_id>/upload-invoice")
@require_permission("purchasing.edit")
def payment_upload_invoice(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(PaymentEntry, entry_id)
    if not entry:
        abort(404)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select an invoice file to upload.", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    file_bytes = f.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        flash("File too large (max 50MB).", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    date_received = parse_date((request.form.get("date_received") or "").strip() or None)
    storage = storage_from_config(current_app.config)
    try:
        migrate_payment_to_invoice(
            s,
            payment=entry,
            file_bytes=file_bytes,
            filename=f.filename,
            content_type=f.mimetype or "application/octet-stream",
            date_received=date_received,
            user=u,
            storage=storage,
        )
        s.commit()
    except InvoiceFlowError as e:
        s.rollback()
        flash(str(e), "danger")
        return redirect(url_for("purchasing.purchasing_list"))
    except Exception as e:  # noqa: BLE001
        s.rollback()
        flash(f"Could not migrate invoice: {e}", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    flash("Invoice uploaded — entry moved to Invoices Received.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


# ---------- Invoices Received ledger ----------
def _sorted_invoice_received(s) -> list[InvoiceReceivedEntry]:
    from sqlalchemy import case

    return (
        s.query(InvoiceReceivedEntry)
        .filter(
            InvoiceReceivedEntry.disposition.in_(
                [
                    InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
                    InvoiceReceivedEntry.DISPOSITION_PO_MATCHED,
                ]
            )
        )
        .order_by(
            case((InvoiceReceivedEntry.date_received.is_(None), 1), else_=0),
            InvoiceReceivedEntry.date_received.desc(),
            InvoiceReceivedEntry.id.desc(),
        )
        .all()
    )


def _sorted_other_payments(s) -> list[InvoiceReceivedEntry]:
    from sqlalchemy import case

    return (
        s.query(InvoiceReceivedEntry)
        .filter(InvoiceReceivedEntry.disposition == InvoiceReceivedEntry.DISPOSITION_OTHER_PAYMENT)
        .order_by(
            case((InvoiceReceivedEntry.date_received.is_(None), 1), else_=0),
            InvoiceReceivedEntry.date_received.desc(),
            InvoiceReceivedEntry.id.desc(),
        )
        .all()
    )


def _invoice_to_dict(e: InvoiceReceivedEntry) -> dict:
    return {
        "id": e.id,
        "date_received": e.date_received.isoformat() if e.date_received else "",
        "payee": e.payee or "",
        "description": e.description or "",
        "amount": str(e.amount) if e.amount is not None else "",
        "due_date": e.due_date.isoformat() if e.due_date else "",
        "disposition": e.disposition or InvoiceReceivedEntry.DISPOSITION_UNASSIGNED,
        "purchase_order_id": e.purchase_order_id,
    }


def _apply_invoice_fields(e: InvoiceReceivedEntry, src) -> None:
    if "date_received" in src:
        e.date_received = parse_date((src.get("date_received") or "").strip() or None)
    if "payee" in src:
        e.payee = (src.get("payee") or "").strip() or None
    if "description" in src:
        e.description = (src.get("description") or "").strip() or None
    if "amount" in src:
        e.amount = _parse_amount(src.get("amount"))
    if "due_date" in src:
        e.due_date = parse_date((src.get("due_date") or "").strip() or None)


@bp.get("/purchasing/invoices-received")
@require_permission("purchasing.view")
def invoices_received_list():
    s = db_session()
    return jsonify([_invoice_to_dict(e) for e in _sorted_invoice_received(s)])


@bp.post("/purchasing/invoices-received")
@require_permission("purchasing.edit")
def invoices_received_create():
    s = db_session()
    u = _current_user()
    src = request.get_json(silent=True) if request.is_json else request.form
    src = src or {}
    entry = InvoiceReceivedEntry(created_by_id=u.id)
    merged = {k: src.get(k) for k in ("date_received", "payee", "description", "amount", "due_date")}
    _apply_invoice_fields(entry, merged)
    s.add(entry)
    s.flush()
    record_event(
        s, actor=u, action="invoice_received.create",
        entity_type="InvoiceReceivedEntry", entity_id=str(entry.id),
    )
    s.commit()
    if request.is_json:
        return jsonify(_invoice_to_dict(entry))
    return redirect(url_for("purchasing.purchasing_list"))


@bp.post("/purchasing/invoices-received/<int:entry_id>")
@require_permission("purchasing.edit")
def invoices_received_update(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(InvoiceReceivedEntry, entry_id)
    if not entry:
        abort(404)
    before = _invoice_row_snapshot(entry)
    src = request.get_json(silent=True) if request.is_json else request.form
    _apply_invoice_fields(entry, src or {})
    entry.updated_at = utcnow()
    record_event(
        s, actor=u, action="invoice_received.update",
        entity_type="InvoiceReceivedEntry", entity_id=str(entry.id),
        metadata={"before": before, "after": _invoice_row_snapshot(entry)},
    )
    s.commit()
    if request.is_json:
        return jsonify(_invoice_to_dict(entry))
    return redirect(url_for("purchasing.purchasing_list"))


@bp.delete("/purchasing/invoices-received/<int:entry_id>")
@require_permission("purchasing.edit")
def invoices_received_delete(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(InvoiceReceivedEntry, entry_id)
    if not entry:
        abort(404)
    linked = (
        s.query(PaymentEntry)
        .filter(PaymentEntry.invoice_received_entry_id == entry_id)
        .first()
    )
    if linked:
        # Refuse: migration re-homed payment files onto this invoice by storage_key.
        # Deleting here would destroy the payment's original files (Task H1).
        msg = (
            "This invoice is linked to an Upcoming payment. "
            "Use Return to Upcoming first, then delete if needed."
        )
        if request.is_json or request.accept_mimetypes.best == "application/json":
            return jsonify({"ok": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    meta = _invoice_row_snapshot(entry)
    storage = storage_from_config(current_app.config)
    for a in list(entry.attachments or []):
        try:
            storage.delete(a.storage_key)
        except Exception:
            pass
    s.delete(entry)
    record_event(
        s, actor=u, action="invoice_received.delete",
        entity_type="InvoiceReceivedEntry", entity_id=str(entry_id),
        metadata=meta,
    )
    s.commit()
    return jsonify({"ok": True})


@bp.post("/purchasing/invoices-received/<int:entry_id>/files")
@require_permission("purchasing.edit")
def invoice_received_attach_file(entry_id: int):
    from werkzeug.utils import secure_filename

    s = db_session()
    u = _current_user()
    entry = s.get(InvoiceReceivedEntry, entry_id)
    if not entry:
        abort(404)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    file_bytes = f.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        flash("File too large (max 50MB).", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    safe_name = secure_filename(f.filename) or "file"
    storage_key = f"purchasing/invoice_received_files/{entry_id}/{safe_name}"
    storage = storage_from_config(current_app.config)
    try:
        storage.put_bytes(storage_key, file_bytes, content_type=f.mimetype or "application/octet-stream")
    except Exception as e:  # noqa: BLE001
        flash(f"Storage error: {e}", "danger")
        return redirect(url_for("purchasing.purchasing_list"))

    att = InvoiceReceivedAttachment(
        invoice_received_entry_id=entry_id,
        filename=f.filename,
        storage_key=storage_key,
        content_type=f.mimetype or "application/octet-stream",
        size_bytes=len(file_bytes),
        uploaded_by_user_id=u.id if u else None,
    )
    s.add(att)
    record_event(
        s, actor=u, action="invoice_received.attach_file",
        entity_type="InvoiceReceivedAttachment", entity_id=str(entry_id),
        metadata={"filename": f.filename},
    )
    s.commit()
    flash("File uploaded.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.get("/purchasing/invoices-received/files/<int:att_id>/view")
@require_permission("purchasing.view")
def invoice_received_file_view(att_id: int):
    s = db_session()
    att = s.get(InvoiceReceivedAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)
    if needs_server_render(att.filename):
        file_bytes = storage.get_bytes(att.storage_key)
        download_url = url_for("purchasing.invoice_received_file_download", att_id=att_id)
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


@bp.get("/purchasing/invoices-received/files/<int:att_id>/download")
@require_permission("purchasing.view")
def invoice_received_file_download(att_id: int):
    s = db_session()
    att = s.get(InvoiceReceivedAttachment, att_id)
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


@bp.post("/purchasing/invoices-received/files/<int:att_id>/delete")
@require_permission("purchasing.edit")
def invoice_received_file_delete(att_id: int):
    s = db_session()
    u = _current_user()
    att = s.get(InvoiceReceivedAttachment, att_id)
    if not att:
        abort(404)
    storage = storage_from_config(current_app.config)
    try:
        storage.delete(att.storage_key)
    except Exception:
        pass
    record_event(
        s, actor=u, action="invoice_received.delete_file",
        entity_type="InvoiceReceivedAttachment", entity_id=str(att_id),
        metadata={"filename": att.filename},
    )
    s.delete(att)
    s.commit()
    flash("File deleted.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.post("/purchasing/invoices-received/<int:entry_id>/return-to-upcoming")
@require_permission("purchasing.edit")
def invoice_return_to_upcoming(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(InvoiceReceivedEntry, entry_id)
    if not entry:
        abort(404)
    try:
        return_invoice_to_upcoming(s, invoice=entry, user=u)
        s.commit()
    except InvoiceFlowError as e:
        s.rollback()
        flash(str(e), "danger")
        return redirect(url_for("purchasing.purchasing_list"))
    flash("Invoice returned to Upcoming Payments.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.post("/purchasing/invoices-received/<int:entry_id>/match-po")
@require_permission("purchasing.edit")
def invoice_match_po(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(InvoiceReceivedEntry, entry_id)
    if not entry:
        abort(404)

    raw_po = (request.form.get("purchase_order_id") or "").strip()
    try:
        if not raw_po:
            unmatch_invoice_from_po(s, invoice=entry, user=u)
            s.commit()
            flash("Purchase order unmatched.", "success")
        else:
            po = s.get(PurchaseOrder, int(raw_po))
            if not po:
                flash("Purchase order not found.", "danger")
                return redirect(url_for("purchasing.purchasing_list"))
            match_invoice_to_po(s, invoice=entry, purchase_order=po, user=u)
            s.commit()
            flash(f"Matched to PO {po.po_number}.", "success")
    except (InvoiceFlowError, ValueError, TypeError) as e:
        s.rollback()
        flash(str(e), "danger")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.post("/purchasing/invoices-received/<int:entry_id>/mark-other")
@require_permission("purchasing.edit")
def invoice_mark_other(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(InvoiceReceivedEntry, entry_id)
    if not entry:
        abort(404)
    try:
        mark_invoice_other_payment(s, invoice=entry, user=u)
        s.commit()
    except InvoiceFlowError as e:
        s.rollback()
        flash(str(e), "danger")
        return redirect(url_for("purchasing.purchasing_list"))
    flash("Moved to Other Payments.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.post("/purchasing/invoices-received/<int:entry_id>/return-to-received")
@require_permission("purchasing.edit")
def invoice_return_to_received(entry_id: int):
    s = db_session()
    u = _current_user()
    entry = s.get(InvoiceReceivedEntry, entry_id)
    if not entry:
        abort(404)
    try:
        return_invoice_to_received(s, invoice=entry, user=u)
        s.commit()
    except InvoiceFlowError as e:
        s.rollback()
        flash(str(e), "danger")
        return redirect(url_for("purchasing.purchasing_list"))
    flash("Returned to Invoices Received.", "success")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.get("/purchasing/new")
@require_permission("purchasing.create")
def purchasing_new_get():
    s = db_session()
    suppliers = s.query(Supplier).order_by(Supplier.name.asc()).all()
    return render_template("admin/purchasing/new.html", suppliers=suppliers, today=date.today())


@bp.post("/purchasing/new")
@require_permission("purchasing.create")
def purchasing_new_post():
    s = db_session()
    u = _current_user()

    payload = {
        "po_number": request.form.get("po_number"),
        "order_date": parse_date(request.form.get("order_date")),
        "expected_date": parse_date(request.form.get("expected_date")),
        "received_date": parse_date(request.form.get("received_date")),
        "payment_due_date": parse_date(request.form.get("payment_due_date")),
        "supplier_id": request.form.get("supplier_id") or None,
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "notes": request.form.get("notes"),
        "amount": request.form.get("amount"),
        "meets_requirements": request.form.get("meets_requirements"),
        "verified_how": request.form.get("verified_how"),
        "closed_by": request.form.get("closed_by"),
        "reference": request.form.get("reference"),
        "lines": parse_line_items(request.form.get("line_items")),
    }
    if payload["supplier_id"]:
        payload["supplier_id"] = int(payload["supplier_id"])

    errors = validate_purchase_order_payload(payload)
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("purchasing.purchasing_new_get"))

    existing = s.query(PurchaseOrder).filter(PurchaseOrder.po_number == (payload.get("po_number") or "").strip()).one_or_none()
    if existing:
        flash("PO number already exists.", "danger")
        return redirect(url_for("purchasing.purchasing_new_get"))

    po = create_purchase_order(s, payload, u)
    s.commit()
    flash("Purchase order created.", "success")
    return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))


@bp.get("/purchasing/<int:po_id>")
@require_permission("purchasing.view")
def purchasing_detail(po_id: int):
    s = db_session()
    po = s.get(PurchaseOrder, po_id)
    if not po:
        abort(404)
    related_invoices = (
        s.query(InvoiceReceivedEntry)
        .filter(InvoiceReceivedEntry.purchase_order_id == po_id)
        .order_by(InvoiceReceivedEntry.date_received.desc(), InvoiceReceivedEntry.id.desc())
        .all()
    )
    return render_template(
        "admin/purchasing/detail.html",
        po=po,
        related_invoices=related_invoices,
    )


@bp.post("/purchasing/<int:po_id>/document-closed")
@require_permission("purchasing.edit")
def purchasing_document_closed(po_id: int):
    s = db_session()
    u = _current_user()
    po = s.get(PurchaseOrder, po_id)
    if not po:
        abort(404)
    document_po_closed(s, po=po, user=u)
    s.commit()
    flash("Purchase order documented as closed.", "success")
    return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))


@bp.post("/purchasing/<int:po_id>/reopen")
@require_permission("purchasing.edit")
def purchasing_reopen(po_id: int):
    s = db_session()
    u = _current_user()
    po = s.get(PurchaseOrder, po_id)
    if not po:
        abort(404)
    reopen_po(s, po=po, user=u)
    s.commit()
    flash("Purchase order reopened.", "success")
    return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))


@bp.get("/purchasing/export-log")
@require_permission("purchasing.view")
def purchasing_export_log():
    import io

    s = db_session()
    u = _current_user()
    pos = s.query(PurchaseOrder).order_by(PurchaseOrder.po_number.asc()).all()
    odd_dates = [p.po_number for p in pos if p.order_date and p.order_date.year < 1990]
    data = build_po_log_xlsx(pos)
    record_event(
        s,
        actor=u,
        action="purchase_order.export_log",
        entity_type="PurchaseOrder",
        entity_id="bulk",
        metadata={
            "row_count": len(pos),
            "odd_order_dates": odd_dates,
        },
    )
    s.commit()
    return send_file(
        io.BytesIO(data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="SILQ PO Log.xlsx",
    )


@bp.get("/purchasing/parse-check")
@require_permission("purchasing.view")
def purchasing_parse_check():
    """Server-side read-only PO PDF parse accuracy diagnostic (D22 / Task D1)."""
    import time

    from app.eqms.modules.purchasing.parsers.pdf import parse_purchase_order_pdf

    BUDGET_SECONDS = 25.0
    DOC_CAP = 80

    s = db_session()
    storage = storage_from_config(current_app.config)
    atts = (
        s.query(PurchaseOrderAttachment)
        .filter(PurchaseOrderAttachment.attachment_type == "po_pdf")
        .order_by(PurchaseOrderAttachment.id.asc())
        .limit(DOC_CAP)
        .all()
    )
    total_available = (
        s.query(PurchaseOrderAttachment)
        .filter(PurchaseOrderAttachment.attachment_type == "po_pdf")
        .count()
    )

    started = time.monotonic()
    empty = lambda: {"agree": 0, "disagree": 0, "not_found": 0}
    field_stats_text = {
        "po_number": empty(),
        "order_date": empty(),
        "supplier_name": empty(),
    }
    field_stats_merged = {
        "po_number": empty(),
        "order_date": empty(),
        "supplier_name": empty(),
    }
    samples: list[dict] = []
    processed = 0
    errors = 0
    incomplete = False
    incomplete_reason = None
    conforming_filenames = 0

    from app.eqms.modules.purchasing.parsers.pdf import merge_import_metadata
    from app.eqms.modules.purchasing.service import supplier_name_for_export
    from app.eqms.modules.rep_traceability.service import normalize_order_number

    def _budget_ok() -> bool:
        return (time.monotonic() - started) < BUDGET_SECONDS

    def _score_po_number(candidate, stored, bucket):
        cand = (candidate or "").strip() or None
        if not cand:
            bucket["not_found"] += 1
            return "not_found"
        if normalize_order_number(cand) == normalize_order_number(stored):
            bucket["agree"] += 1
            return "agree"
        bucket["disagree"] += 1
        return f"disagree ({cand!r})"

    def _score_date(candidate, stored, bucket):
        if not candidate:
            bucket["not_found"] += 1
            return "not_found"
        if candidate == stored:
            bucket["agree"] += 1
            return "agree"
        bucket["disagree"] += 1
        return f"disagree ({candidate})"

    def _score_supplier(candidate, stored_supplier, bucket):
        from app.eqms.modules.customer_profiles.utils import canonical_customer_key

        cand = (candidate or "").strip() or None
        if not cand:
            bucket["not_found"] += 1
            return "not_found"
        if stored_supplier and (
            cand.lower() == stored_supplier.lower()
            or canonical_customer_key(cand) == canonical_customer_key(stored_supplier)
        ):
            bucket["agree"] += 1
            return "agree"
        if not stored_supplier:
            bucket["not_found"] += 1
            return f"parsed_only ({cand!r})"
        bucket["disagree"] += 1
        return f"disagree ({cand!r} vs {stored_supplier!r})"

    for att in atts:
        if not _budget_ok():
            incomplete = True
            incomplete_reason = f"Stopped after {BUDGET_SECONDS:.0f}s budget ({processed} of {len(atts)} loaded)."
            break
        po = s.get(PurchaseOrder, att.purchase_order_id)
        if not po:
            continue
        try:
            raw = storage.get_bytes(att.storage_key)
            parsed = parse_purchase_order_pdf(raw)
        except Exception as e:  # noqa: BLE001
            errors += 1
            samples.append(
                {
                    "po_number": po.po_number,
                    "filename": att.filename,
                    "error": str(e)[:200],
                }
            )
            processed += 1
            continue

        processed += 1
        merged = merge_import_metadata(att.filename or "", parsed)
        if merged.get("filename_conforming"):
            conforming_filenames += 1
        stored_supplier = supplier_name_for_export(po)
        row = {
            "po_number": po.po_number,
            "filename": att.filename,
            "filename_conforming": bool(merged.get("filename_conforming")),
            "fields_text": {},
            "fields_merged": {},
        }

        row["fields_text"]["po_number"] = _score_po_number(
            parsed.get("po_number"), po.po_number, field_stats_text["po_number"]
        )
        row["fields_merged"]["po_number"] = _score_po_number(
            merged.get("po_number"), po.po_number, field_stats_merged["po_number"]
        )
        row["fields_text"]["order_date"] = _score_date(
            parsed.get("order_date"), po.order_date, field_stats_text["order_date"]
        )
        row["fields_merged"]["order_date"] = _score_date(
            merged.get("order_date"), po.order_date, field_stats_merged["order_date"]
        )
        row["fields_text"]["supplier_name"] = _score_supplier(
            parsed.get("supplier_name"), stored_supplier, field_stats_text["supplier_name"]
        )
        row["fields_merged"]["supplier_name"] = _score_supplier(
            merged.get("supplier_name"), stored_supplier, field_stats_merged["supplier_name"]
        )

        if len(samples) < 25:
            samples.append(row)

    if not incomplete and total_available > processed:
        incomplete = True
        incomplete_reason = f"Document cap {DOC_CAP} reached ({processed} of {total_available} po_pdf attachments)."

    elapsed = time.monotonic() - started
    return render_template(
        "admin/purchasing/parse_check.html",
        field_stats_text=field_stats_text,
        field_stats_merged=field_stats_merged,
        samples=samples,
        processed=processed,
        total_available=total_available,
        errors=errors,
        incomplete=incomplete,
        incomplete_reason=incomplete_reason,
        elapsed=elapsed,
        budget_seconds=BUDGET_SECONDS,
        conforming_filenames=conforming_filenames,
    )


@bp.get("/purchasing/pdf-text")
@require_permission("purchasing.view")
def purchasing_pdf_text():
    """Server-side read-only PO PDF text dump (P4-06C Task A)."""
    import time

    from app.eqms.modules.purchasing.parsers.pdf import parse_po_hints_from_filename, parse_purchase_order_pdf

    BUDGET_SECONDS = 25.0
    DOC_CAP = 80

    s = db_session()
    storage = storage_from_config(current_app.config)
    atts = (
        s.query(PurchaseOrderAttachment)
        .filter(PurchaseOrderAttachment.attachment_type == "po_pdf")
        .order_by(PurchaseOrderAttachment.id.asc())
        .limit(DOC_CAP)
        .all()
    )
    total_available = (
        s.query(PurchaseOrderAttachment)
        .filter(PurchaseOrderAttachment.attachment_type == "po_pdf")
        .count()
    )

    started = time.monotonic()
    samples: list[dict] = []
    processed = 0
    errors = 0
    incomplete = False
    incomplete_reason = None
    text_lengths: list[int] = []
    no_text_count = 0
    conforming_filenames = 0

    def _budget_ok() -> bool:
        return (time.monotonic() - started) < BUDGET_SECONDS

    for att in atts:
        if not _budget_ok():
            incomplete = True
            incomplete_reason = f"Stopped after {BUDGET_SECONDS:.0f}s budget ({processed} of {len(atts)} loaded)."
            break
        po = s.get(PurchaseOrder, att.purchase_order_id)
        if not po:
            continue
        filename = att.filename or ""
        conforming = parse_po_hints_from_filename(filename) is not None
        if conforming:
            conforming_filenames += 1
        try:
            raw = storage.get_bytes(att.storage_key)
            parsed = parse_purchase_order_pdf(raw)
        except Exception as e:  # noqa: BLE001
            errors += 1
            processed += 1
            samples.append(
                {
                    "po_number": po.po_number,
                    "filename": filename,
                    "filename_conforming": conforming,
                    "error": str(e)[:200],
                    "char_count": None,
                    "page_count": None,
                    "preview_lines": [],
                }
            )
            continue

        processed += 1
        raw_text = parsed.get("raw_text") or ""
        char_count = len(raw_text.strip())
        text_lengths.append(char_count)
        if char_count < 50:
            no_text_count += 1
        preview_lines = [ln for ln in raw_text.splitlines() if ln.strip()][:40]
        samples.append(
            {
                "po_number": po.po_number,
                "filename": filename,
                "filename_conforming": conforming,
                "char_count": char_count,
                "page_count": parsed.get("page_count") or 0,
                "preview_lines": preview_lines,
                "error": None,
            }
        )

    if not incomplete and total_available > processed:
        incomplete = True
        incomplete_reason = f"Document cap {DOC_CAP} reached ({processed} of {total_available} po_pdf attachments)."

    # Bucket distribution for the processed set.
    buckets = {
        "0-49": 0,
        "50-199": 0,
        "200-999": 0,
        "1000-4999": 0,
        "5000+": 0,
    }
    for n in text_lengths:
        if n < 50:
            buckets["0-49"] += 1
        elif n < 200:
            buckets["50-199"] += 1
        elif n < 1000:
            buckets["200-999"] += 1
        elif n < 5000:
            buckets["1000-4999"] += 1
        else:
            buckets["5000+"] += 1

    elapsed = time.monotonic() - started
    return render_template(
        "admin/purchasing/pdf_text.html",
        samples=samples,
        processed=processed,
        total_available=total_available,
        errors=errors,
        incomplete=incomplete,
        incomplete_reason=incomplete_reason,
        elapsed=elapsed,
        budget_seconds=BUDGET_SECONDS,
        conforming_filenames=conforming_filenames,
        no_text_count=no_text_count,
        buckets=buckets,
        text_lengths=text_lengths,
    )


# P4-06C Task D: PDF-text supplier stays gated unless measurement clears the 95% bar.
TRUST_PDF_TEXT_SUPPLIER = False


def _po_import_conflicts(po: PurchaseOrder | None, *, order_date, supplier_id, supplier_trusted: bool) -> list[dict]:
    """Conflicts only when an existing non-blank value disagrees with extracted fill (D51)."""
    conflicts: list[dict] = []
    if not po:
        return conflicts
    if order_date and po.order_date and po.order_date != order_date:
        conflicts.append(
            {
                "field": "order_date",
                "existing": str(po.order_date),
                "extracted": str(order_date),
            }
        )
    if supplier_trusted and supplier_id and po.supplier_id and int(po.supplier_id) != int(supplier_id):
        conflicts.append(
            {
                "field": "supplier_id",
                "existing": str(po.supplier_id),
                "extracted": str(supplier_id),
            }
        )
    return conflicts


def _resolve_import_supplier(s, supplier_name: str, sources: dict) -> tuple[int | None, str | None, str | None, bool]:
    """Returns supplier_id, notes, flag (none|ambiguous), discarded_pdf_supplier."""
    supplier_from_filename = sources.get("supplier_name") == "filename"
    supplier_trusted = supplier_from_filename or (
        TRUST_PDF_TEXT_SUPPLIER and sources.get("supplier_name") == "pdf"
    )
    name = (supplier_name or "").strip()
    if not name:
        return None, None, None, False
    if not supplier_trusted:
        return None, None, None, True
    supplier, status = resolve_supplier_by_extracted_name(s, name)
    if status == "unique" and supplier is not None:
        return int(supplier.id), None, None, False
    return None, f"Supplier from import: {name}", status, False


def _flash_import_success(po, filled_fields, line_status, discarded_pdf_supplier, supplier_flag):
    if filled_fields:
        msg = f"PDF imported for PO {po.po_number}. Filled blank fields: {', '.join(filled_fields)}."
    else:
        msg = f"PDF imported for PO {po.po_number}."
    if line_status == "lines_added":
        msg += " Line items added from PDF."
    elif line_status == "lines_skipped_existing":
        msg += " PDF line items were not written because this PO already has lines."
    if discarded_pdf_supplier:
        msg += (
            " PDF-text supplier was ignored (not from filename); "
            "set supplier manually if needed."
        )
    if supplier_flag == "none":
        msg += " Extracted supplier name did not match an existing supplier; recorded in notes."
    elif supplier_flag == "ambiguous":
        msg += " Extracted supplier name matched multiple suppliers; left blank and recorded in notes."
    flash(msg, "success")


def _apply_po_pdf_import(
    s,
    *,
    u,
    file_bytes: bytes,
    filename: str,
    content_type: str,
    merged: dict,
    sources: dict,
    staged_key: str | None = None,
    force: bool = False,
):
    """
    Create/fill PO and attach PDF.

    Returns dict with keys: ok, conflicts, po, ...
    On DB failure raises after rolling back newly uploaded keys only.
    """
    po_number = (merged.get("po_number") or "").strip()
    if not po_number:
        raise ValueError("po_number required")

    order_date = merged.get("order_date") or date.today()
    supplier_id, notes, supplier_flag, discarded_pdf_supplier = _resolve_import_supplier(
        s, merged.get("supplier_name") or "", sources
    )
    supplier_trusted = sources.get("supplier_name") == "filename" or (
        TRUST_PDF_TEXT_SUPPLIER and sources.get("supplier_name") == "pdf"
    )

    po = s.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).one_or_none()
    conflicts = [] if force else _po_import_conflicts(
        po,
        order_date=merged.get("order_date"),
        supplier_id=supplier_id,
        supplier_trusted=supplier_trusted,
    )
    if conflicts:
        return {"ok": False, "conflicts": conflicts, "discarded_pdf_supplier": discarded_pdf_supplier, "supplier_flag": supplier_flag}

    filled_fields: list[str] = []
    line_status = None
    if not po:
        po = create_purchase_order(
            s,
            {
                "po_number": po_number,
                "order_date": order_date,
                "expected_date": None,
                "received_date": None,
                "supplier_id": supplier_id,
                "status": "pending",
                "description": None,
                "notes": notes,
                "lines": merged.get("items") or [],
            },
            u,
        )
        if merged.get("items"):
            line_status = "lines_added"
    else:
        fills: dict = {"order_date": order_date if order_date else None}
        if supplier_trusted:
            fills["supplier_id"] = supplier_id
            fills["notes"] = notes
        filled_fields = apply_po_blank_fills(po, fills)
        po.updated_at = utcnow()
        line_status = append_po_lines_if_empty(s, po, merged.get("items") or [])

    stored_keys: list[str] = []
    try:
        attachment = upload_purchase_order_attachment(
            s,
            po,
            file_bytes,
            filename,
            content_type or "application/pdf",
            u,
            "po_pdf",
        )
        stored_keys.append(attachment.storage_key)
        s.commit()
    except Exception:
        s.rollback()
        storage = storage_from_config(current_app.config)
        for key in stored_keys:
            try:
                storage.delete(key)
            except Exception:
                pass
        raise

    if staged_key:
        delete_staged_po_pdf(staged_key)

    return {
        "ok": True,
        "po": po,
        "filled_fields": filled_fields,
        "line_status": line_status,
        "discarded_pdf_supplier": discarded_pdf_supplier,
        "supplier_flag": supplier_flag,
    }


@bp.get("/purchasing/<int:po_id>/edit")
@require_permission("purchasing.edit")
def purchasing_edit_get(po_id: int):
    s = db_session()
    po = s.get(PurchaseOrder, po_id)
    if not po:
        abort(404)
    suppliers = s.query(Supplier).order_by(Supplier.name.asc()).all()
    line_items_text = "\n".join(
        f"{line.item_code or ''} | {line.description or ''} | {line.quantity} | {line.unit_price or ''}"
        for line in po.lines
    )
    return render_template(
        "admin/purchasing/edit.html",
        po=po,
        suppliers=suppliers,
        line_items_text=line_items_text,
    )


@bp.post("/purchasing/<int:po_id>/edit")
@require_permission("purchasing.edit")
def purchasing_edit_post(po_id: int):
    s = db_session()
    u = _current_user()
    po = s.get(PurchaseOrder, po_id)
    if not po:
        abort(404)

    reason = (request.form.get("reason") or "").strip() or None

    payload = {
        "order_date": parse_date(request.form.get("order_date")),
        "expected_date": parse_date(request.form.get("expected_date")),
        "received_date": parse_date(request.form.get("received_date")),
        "payment_due_date": parse_date(request.form.get("payment_due_date")),
        "supplier_id": request.form.get("supplier_id") or None,
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "notes": request.form.get("notes"),
        "amount": request.form.get("amount"),
        "meets_requirements": request.form.get("meets_requirements"),
        "verified_how": request.form.get("verified_how"),
        "closed_by": request.form.get("closed_by"),
        "reference": request.form.get("reference"),
        "is_closed": (request.form.get("is_closed") or "").strip() == "1",
    }
    if payload["supplier_id"]:
        payload["supplier_id"] = int(payload["supplier_id"])

    update_purchase_order(s, po, payload, u, reason=reason)

    line_items = parse_line_items(request.form.get("line_items"))
    po.lines.clear()
    for line in line_items:
        po.lines.append(
            PurchaseOrderLine(
                item_code=(line.get("item_code") or "").strip() or None,
                description=(line.get("description") or "").strip() or None,
                quantity=int(line.get("quantity") or 1),
                unit_price=(line.get("unit_price") or "").strip() or None,
            )
        )

    s.commit()
    flash("Purchase order updated.", "success")
    return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))


@bp.post("/purchasing/<int:po_id>/upload")
@require_permission("purchasing.upload")
def purchasing_upload_attachment(po_id: int):
    s = db_session()
    u = _current_user()
    po = s.get(PurchaseOrder, po_id)
    if not po:
        abort(404)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))

    attachment_type = (request.form.get("attachment_type") or "other").strip()
    if attachment_type not in ("po_pdf", "confirmation_pdf", "confirmation_eml", "other"):
        flash("Invalid attachment type.", "danger")
        return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))

    file_bytes = f.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        flash("File too large (max 10MB).", "danger")
        return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))

    content_type = f.mimetype or "application/octet-stream"
    upload_purchase_order_attachment(s, po, file_bytes, f.filename, content_type, u, attachment_type)
    s.commit()
    flash("Attachment uploaded.", "success")
    return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))


@bp.get("/purchasing/attachments/<int:attachment_id>/download")
@require_permission("purchasing.view")
def purchasing_attachment_download(attachment_id: int):
    s = db_session()
    attachment = s.get(PurchaseOrderAttachment, attachment_id)
    if not attachment:
        abort(404)
    storage = storage_from_config(current_app.config)
    fobj = storage.open(attachment.storage_key)
    return send_file(
        fobj,
        mimetype=attachment.content_type,
        as_attachment=True,
        download_name=attachment.filename,
    )


@bp.get("/purchasing/attachments/<int:attachment_id>/view")
@require_permission("purchasing.view")
def purchasing_attachment_view(attachment_id: int):
    s = db_session()
    attachment = s.get(PurchaseOrderAttachment, attachment_id)
    if not attachment:
        abort(404)

    storage = storage_from_config(current_app.config)

    # EML files: parse and render in a custom template
    if attachment.attachment_type == "confirmation_eml":
        eml_bytes = storage.get_bytes(attachment.storage_key)
        parsed = parse_eml_file(eml_bytes)
        return render_template("admin/purchasing/view_eml.html", attachment=attachment, eml=parsed)

    # Server-side rendering for .docx, .xlsx, .xls, .csv
    if needs_server_render(attachment.filename):
        file_bytes = storage.get_bytes(attachment.storage_key)
        download_url = url_for("purchasing.purchasing_attachment_download", attachment_id=attachment_id)
        response = render_document_to_response(
            file_bytes, attachment.filename, attachment.content_type,
            download_url=download_url,
        )
        if response:
            return response

    # Native browser rendering (PDF, images, text)
    fobj = storage.open(attachment.storage_key)
    inline = allow_inline_view(attachment.filename, attachment.content_type)
    return send_file(
        fobj,
        mimetype=attachment.content_type,
        as_attachment=not inline,
        download_name=attachment.filename,
    )


@bp.get("/purchasing/import-log")
@require_permission("purchasing.edit")
def purchasing_import_log_get():
    return render_template("admin/purchasing/import_log.html")


@bp.post("/purchasing/import-log")
@require_permission("purchasing.edit")
def purchasing_import_log_post():
    s = db_session()
    u = _current_user()

    f = request.files.get("xlsx_file")
    if not f or not f.filename:
        flash("Choose the SILQ PO Log (.xlsx) to import.", "danger")
        return redirect(url_for("purchasing.purchasing_import_log_get"))
    if not f.filename.lower().endswith(".xlsx"):
        flash("Please upload an .xlsx file.", "danger")
        return redirect(url_for("purchasing.purchasing_import_log_get"))

    file_bytes = f.read()
    if len(file_bytes) > 15 * 1024 * 1024:
        flash("File too large (max 15MB).", "danger")
        return redirect(url_for("purchasing.purchasing_import_log_get"))

    try:
        result = import_po_log(s, file_bytes, u)
        s.commit()
    except Exception as e:  # noqa: BLE001
        s.rollback()
        current_app.logger.exception("PO Log import failed: %s", e)
        flash(f"PO Log import failed: {e}", "danger")
        return redirect(url_for("purchasing.purchasing_import_log_get"))

    msg = f"PO Log import complete: {result['created']} created, {result['updated']} updated, {result['skipped']} skipped."
    flash(msg, "success" if not result["errors"] else "warning")
    for err in result["errors"][:10]:
        flash(err, "danger")
    return redirect(url_for("purchasing.purchasing_list"))


@bp.get("/purchasing/import-pdf")
@require_permission("purchasing.create")
def purchasing_import_pdf_get():
    cleanup_stale_temp_po_pdfs(max_age_hours=24)
    pdfplumber_available = True
    try:
        import pdfplumber  # noqa: F401
    except Exception:
        pdfplumber_available = False
    return render_template("admin/purchasing/import.html", pdfplumber_available=pdfplumber_available)


@bp.post("/purchasing/import-pdf")
@require_permission("purchasing.create")
def purchasing_import_pdf_post():
    import json

    s = db_session()
    u = _current_user()

    f = request.files.get("pdf_file")
    if not f or not f.filename:
        flash("Choose a PDF file to import.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    file_bytes = f.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        flash("File too large (max 10MB).", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    try:
        parsed = parse_purchase_order_pdf(file_bytes)
    except ImportError:
        flash("PDF parsing libraries are not installed. Please contact support.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))
    except Exception as e:
        current_app.logger.exception("PO PDF import failed: %s", e)
        flash(f"PDF import failed: {e}", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    merged = merge_import_metadata(f.filename, parsed)
    sources = merged.get("sources") or {}
    po_number = (merged.get("po_number") or "").strip()

    # Stage bytes whenever we may need a review round-trip (D50).
    needs_review = not po_number
    if po_number:
        existing = s.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).one_or_none()
        supplier_id, _notes, supplier_flag, discarded = _resolve_import_supplier(
            s, merged.get("supplier_name") or "", sources
        )
        supplier_trusted = sources.get("supplier_name") == "filename" or (
            TRUST_PDF_TEXT_SUPPLIER and sources.get("supplier_name") == "pdf"
        )
        conflicts = _po_import_conflicts(
            existing,
            order_date=merged.get("order_date"),
            supplier_id=supplier_id,
            supplier_trusted=supplier_trusted,
        )
        if conflicts:
            needs_review = True
    else:
        conflicts = []
        supplier_flag = None
        discarded = False

    if needs_review:
        staged = stage_po_pdf_bytes(file_bytes, f.filename, "application/pdf")
        reason = "missing_po_number" if not po_number else "conflict"
        return render_template(
            "admin/purchasing/import_review.html",
            staged=staged,
            merged=merged,
            sources=sources,
            conflicts=conflicts,
            supplier_flag=supplier_flag if po_number else None,
            discarded_pdf_supplier=discarded if po_number else False,
            reason=reason,
            items=merged.get("items") or [],
            items_json=json.dumps(merged.get("items") or []),
        )

    try:
        result = _apply_po_pdf_import(
            s,
            u=u,
            file_bytes=file_bytes,
            filename=f.filename,
            content_type="application/pdf",
            merged=merged,
            sources=sources,
        )
    except Exception as e:
        current_app.logger.exception("PO PDF import failed to save: %s", e)
        flash("Database error occurred. PDF upload rolled back.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    if not result.get("ok"):
        staged = stage_po_pdf_bytes(file_bytes, f.filename, "application/pdf")
        return render_template(
            "admin/purchasing/import_review.html",
            staged=staged,
            merged=merged,
            sources=sources,
            conflicts=result.get("conflicts") or [],
            supplier_flag=result.get("supplier_flag"),
            discarded_pdf_supplier=result.get("discarded_pdf_supplier"),
            reason="conflict",
            items=merged.get("items") or [],
            items_json=json.dumps(merged.get("items") or []),
        )

    _flash_import_success(
        result["po"],
        result["filled_fields"],
        result["line_status"],
        result["discarded_pdf_supplier"],
        result["supplier_flag"],
    )
    return redirect(url_for("purchasing.purchasing_detail", po_id=result["po"].id))


@bp.post("/purchasing/import-pdf/confirm")
@require_permission("purchasing.create")
def purchasing_import_pdf_confirm():
    import json

    s = db_session()
    u = _current_user()
    storage = storage_from_config(current_app.config)

    staged_key = (request.form.get("staged_key") or "").strip()
    filename = (request.form.get("filename") or "document.pdf").strip()
    if not staged_key.startswith("temp_po_pdf/"):
        flash("Invalid staged upload.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    po_number = (request.form.get("po_number") or "").strip()
    if not po_number:
        flash("PO number is required.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    try:
        file_bytes = storage.get_bytes(staged_key)
    except Exception:
        flash("Staged PDF is no longer available. Please upload again.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    order_date = parse_date(request.form.get("order_date"))
    supplier_name = (request.form.get("supplier_name") or "").strip()
    try:
        items = json.loads(request.form.get("items_json") or "[]")
    except Exception:
        items = []

    source_po = (request.form.get("source_po_number") or "").strip() or None
    source_date = (request.form.get("source_order_date") or "").strip() or None
    source_supplier = (request.form.get("source_supplier_name") or "").strip() or None
    sources = {
        "po_number": source_po,
        "order_date": source_date,
        "supplier_name": source_supplier,
    }
    # Operator-entered PO number on review is authoritative for this save.
    if not sources.get("po_number"):
        sources["po_number"] = "manual"

    merged = {
        "po_number": po_number,
        "order_date": order_date,
        "supplier_name": supplier_name,
        "items": items if isinstance(items, list) else [],
        "sources": sources,
        "filename_conforming": False,
    }

    try:
        result = _apply_po_pdf_import(
            s,
            u=u,
            file_bytes=file_bytes,
            filename=filename,
            content_type="application/pdf",
            merged=merged,
            sources=sources,
            staged_key=staged_key,
            force=True,
        )
    except Exception as e:
        current_app.logger.exception("PO PDF confirm failed: %s", e)
        flash("Database error occurred. Staged PDF was kept; try again.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    _flash_import_success(
        result["po"],
        result["filled_fields"],
        result["line_status"],
        result["discarded_pdf_supplier"],
        result["supplier_flag"],
    )
    return redirect(url_for("purchasing.purchasing_detail", po_id=result["po"].id))


@bp.post("/purchasing/import-pdf/abandon")
@require_permission("purchasing.create")
def purchasing_import_pdf_abandon():
    staged_key = (request.form.get("staged_key") or "").strip()
    delete_staged_po_pdf(staged_key)
    flash("Import cancelled. Staged PDF removed.", "success")
    return redirect(url_for("purchasing.purchasing_import_pdf_get"))
