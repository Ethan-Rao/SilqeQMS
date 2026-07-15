from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for

from app.eqms.db import db_session
from app.eqms.document_viewer import needs_server_render, render_document_to_response
from app.eqms.models import User
from app.eqms.modules.purchasing.models import PurchaseOrder, PurchaseOrderAttachment, PurchaseOrderLine
from app.eqms.modules.purchasing.parsers.pdf import merge_import_metadata, parse_purchase_order_pdf
from app.eqms.modules.purchasing.service import (
    create_purchase_order,
    import_po_log,
    parse_date,
    parse_eml_file,
    parse_line_items,
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
    from sqlalchemy import and_, case, func

    s = db_session()
    search = (request.args.get("q") or "").strip()
    status_filter = (request.args.get("status") or "").strip()
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
    if status_filter:
        q = q.filter(PurchaseOrder.status == status_filter)
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

    # At-a-glance summary over ALL purchase orders (not the paginated page).
    current_year = date.today().year
    row = s.query(
        func.count(PurchaseOrder.id),
        func.sum(case((PurchaseOrder.status.in_(("pending", "partial")), 1), else_=0)),
        func.sum(case(
            (and_(PurchaseOrder.status == "received",
                  func.extract("year", PurchaseOrder.order_date) == current_year), 1),
            else_=0,
        )),
        func.sum(case((PurchaseOrder.supplier_id.is_(None), 1), else_=0)),
    ).one()
    summary = {
        "total": int(row[0] or 0),
        "open": int(row[1] or 0),
        "received_ytd": int(row[2] or 0),
        "unlinked": int(row[3] or 0),
    }

    # Filter dropdown sources.
    year_rows = (
        s.query(func.extract("year", PurchaseOrder.order_date))
        .filter(PurchaseOrder.order_date.isnot(None))
        .distinct()
        .all()
    )
    years = sorted({int(r[0]) for r in year_rows if r[0] is not None}, reverse=True)
    suppliers = s.query(Supplier).order_by(Supplier.name.asc()).all()

    return render_template(
        "admin/purchasing/list.html",
        purchase_orders=purchase_orders,
        search=search,
        status_filter=status_filter,
        unlinked_only=unlinked_only,
        supplier_filter=supplier_filter,
        year_filter=year_filter,
        summary=summary,
        years=years,
        suppliers=suppliers,
        current_year=current_year,
        page=page,
        total_pages=total_pages,
        total=total,
    )


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
    return render_template("admin/purchasing/detail.html", po=po)


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

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for change is required.", "danger")
        return redirect(url_for("purchasing.purchasing_edit_get", po_id=po_id))

    payload = {
        "order_date": parse_date(request.form.get("order_date")),
        "expected_date": parse_date(request.form.get("expected_date")),
        "received_date": parse_date(request.form.get("received_date")),
        "supplier_id": request.form.get("supplier_id") or None,
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "notes": request.form.get("notes"),
        "amount": request.form.get("amount"),
        "meets_requirements": request.form.get("meets_requirements"),
        "verified_how": request.form.get("verified_how"),
        "closed_by": request.form.get("closed_by"),
        "reference": request.form.get("reference"),
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
    pdfplumber_available = True
    try:
        import pdfplumber  # noqa: F401
    except Exception:
        pdfplumber_available = False
    return render_template("admin/purchasing/import.html", pdfplumber_available=pdfplumber_available)


@bp.post("/purchasing/import-pdf")
@require_permission("purchasing.create")
def purchasing_import_pdf_post():
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
    po_number = (merged.get("po_number") or "").strip()
    order_date = merged.get("order_date") or date.today()
    supplier_name = (merged.get("supplier_name") or "").strip()

    if not po_number:
        flash("Unable to detect PO number from PDF. Please enter manually.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    supplier_id = None
    if supplier_name:
        supplier = s.query(Supplier).filter(Supplier.name.ilike(supplier_name)).one_or_none()
        if supplier:
            supplier_id = supplier.id

    notes = None
    if supplier_name and supplier_id is None:
        notes = f"Supplier from import: {supplier_name}"

    po = s.query(PurchaseOrder).filter(PurchaseOrder.po_number == po_number).one_or_none()
    if not po:
        payload = {
            "po_number": po_number,
            "order_date": order_date,
            "expected_date": None,
            "received_date": None,
            "supplier_id": supplier_id,
            "status": "pending",
            "description": None,
            "notes": notes,
            "lines": merged.get("items") or [],
        }
        po = create_purchase_order(s, payload, u)
    else:
        po.updated_at = utcnow()

    stored_keys: list[str] = []
    try:
        attachment = upload_purchase_order_attachment(
            s,
            po,
            file_bytes,
            f.filename,
            "application/pdf",
            u,
            "po_pdf",
        )
        stored_keys.append(attachment.storage_key)
        s.commit()
    except Exception as e:
        s.rollback()
        storage = storage_from_config(current_app.config)
        for key in stored_keys:
            try:
                storage.delete(key)
            except Exception:
                pass
        current_app.logger.exception("PO PDF import failed to save: %s", e)
        flash("Database error occurred. PDF upload rolled back.", "danger")
        return redirect(url_for("purchasing.purchasing_import_pdf_get"))

    flash(f"PDF imported for PO {po.po_number}.", "success")
    return redirect(url_for("purchasing.purchasing_detail", po_id=po.id))
