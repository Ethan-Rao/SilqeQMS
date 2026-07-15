from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, send_file, session, url_for

from app.eqms.db import db_session
from app.eqms.document_viewer import needs_server_render, render_document_to_response
from app.eqms.models import User
from app.eqms.modules.equipment.models import Equipment, EquipmentSupplier, ManagedDocument
from app.eqms.modules.equipment.service import (
    add_supplier_to_equipment,
    create_equipment,
    delete_equipment_document,
    due_status,
    import_equipment_master,
    remove_supplier_from_equipment,
    update_equipment,
    upload_equipment_document,
    validate_equipment_payload,
)
from app.eqms.modules.supplies.models import Supply
from app.eqms.modules.supplies.service import create_supply, upload_supply_document
from app.eqms.modules.suppliers.models import Supplier
from app.eqms.rbac import require_permission
from app.eqms.storage import storage_from_config
from app.eqms.utils import allow_inline_view, current_user as _current_user, parse_custom_fields

bp = Blueprint("equipment", __name__)

DOCUMENT_CATEGORIES = {
    "requirements_form": "Requirements Form",
    "spec_document": "Specification",
    "calibration": "Calibration",
    "manual": "Manual",
    "qualification": "Qualification",
    "coa": "COA",
    "general": "General",
}

SPEC_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"



# ---------- List ----------
@bp.get("/equipment")
@require_permission("equipment.view")
def equipment_list():
    s = db_session()

    from sqlalchemy import or_

    # Filters
    search = (request.args.get("q") or "").strip()
    status_filter = (request.args.get("status") or "").strip()
    location_filter = (request.args.get("location") or "").strip()
    cal_overdue = request.args.get("cal_overdue") == "1"
    pm_overdue = request.args.get("pm_overdue") == "1"
    # Single "Service overdue" checkbox sets both (CAL OR PM overdue).
    service_overdue = request.args.get("service_overdue") == "1"
    if service_overdue:
        cal_overdue = pm_overdue = True

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 50

    q = s.query(Equipment)

    if search:
        like = f"%{search}%"
        q = q.filter(
            (Equipment.equip_code.ilike(like))
            | (Equipment.description.ilike(like))
            | (Equipment.mfg.ilike(like))
            | (Equipment.model_no.ilike(like))
            | (Equipment.serial_no.ilike(like))
        )

    if status_filter:
        q = q.filter(Equipment.status == status_filter)

    if location_filter:
        q = q.filter(Equipment.location == location_filter)

    today = date.today()
    if cal_overdue and pm_overdue:
        q = q.filter(or_(Equipment.cal_due_date < today, Equipment.pm_due_date < today))
    elif cal_overdue:
        q = q.filter(Equipment.cal_due_date < today)
    elif pm_overdue:
        q = q.filter(Equipment.pm_due_date < today)

    total = q.count()
    equipment = q.order_by(Equipment.equip_code.asc()).offset((page - 1) * per_page).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page

    # Get unique locations for filter dropdown
    locations = s.query(Equipment.location).filter(Equipment.location.isnot(None)).distinct().all()
    locations = sorted([loc[0] for loc in locations if loc[0]])

    # Build pagination URL helper
    def build_url(p):
        args = dict(request.args)
        args["page"] = p
        return url_for("equipment.equipment_list", **args)

    # At-a-glance summary computed over ALL active (non-retired) equipment, not
    # just the current page, so the status cards reflect the whole fleet.
    summary = {
        "active": 0, "cal_overdue": 0, "pm_overdue": 0, "due_soon": 0,
        "cal_overdue_items": [], "pm_overdue_items": [], "due_soon_items": [],
    }
    summary_rows = (
        s.query(
            Equipment.equip_code,
            Equipment.cal_due_date,
            Equipment.pm_due_date,
            Equipment.cal_interval_text,
            Equipment.pm_interval_text,
            Equipment.status,
        )
        .filter(Equipment.status != "Retired")
        .order_by(Equipment.equip_code.asc())
        .all()
    )
    for code, cal_due, pm_due, cal_it, pm_it, st in summary_rows:
        if st != "Active":
            continue
        summary["active"] += 1
        cal = due_status(cal_due, cal_it, today)
        pm = due_status(pm_due, pm_it, today)
        if cal["state"] == "overdue":
            summary["cal_overdue"] += 1
            summary["cal_overdue_items"].append({"code": code, "due": cal_due})
        if pm["state"] == "overdue":
            summary["pm_overdue"] += 1
            summary["pm_overdue_items"].append({"code": code, "due": pm_due})
        if cal["state"] == "due_soon" or pm["state"] == "due_soon":
            summary["due_soon"] += 1
            summary["due_soon_items"].append({"code": code, "cal_due": cal_due, "pm_due": pm_due})

    from app.eqms.modules.admin_docs.models import AdminDocFile

    equipment_master_file = (
        s.query(AdminDocFile)
        .filter(
            AdminDocFile.library_key == "equipment_files",
            AdminDocFile.folder_id.is_(None),
            AdminDocFile.filename.ilike("%Equipment Master%"),
        )
        .first()
    )

    return render_template(
        "admin/equipment/list.html",
        equipment=equipment,
        search=search,
        status_filter=status_filter,
        location_filter=location_filter,
        cal_overdue=cal_overdue,
        pm_overdue=pm_overdue,
        service_overdue=service_overdue,
        locations=locations,
        today=today,
        page=page,
        total=total,
        total_pages=total_pages,
        build_url=build_url,
        due_status=due_status,
        summary=summary,
        equipment_master_file=equipment_master_file,
    )


# ---------- Cal/PM Schedule ----------
@bp.get("/equipment/schedule")
@require_permission("equipment.view")
def equipment_schedule():
    import calendar
    from datetime import timedelta

    s = db_session()
    today = date.today()
    last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
    horizon90 = today + timedelta(days=90)

    equipment = (
        s.query(Equipment)
        .filter(Equipment.status != "Retired")
        .order_by(Equipment.equip_code.asc())
        .all()
    )

    def _primary(e):
        ds = [d for d in (e.cal_due_date, e.pm_due_date) if d is not None]
        return min(ds) if ds else None

    def _cal_provider(e) -> str:
        for assoc in e.supplier_associations:
            if (assoc.relationship_type or "").strip().lower() == "calibration service provider":
                return assoc.supplier.name if assoc.supplier else ""
        return ""

    overdue, this_month, next_90, beyond = [], [], [], []
    for e in equipment:
        pd = _primary(e)
        if pd is None:
            beyond.append(e)
        elif pd < today:
            overdue.append(e)
        elif pd <= last_day:
            this_month.append(e)
        elif pd <= horizon90:
            next_90.append(e)
        else:
            beyond.append(e)

    overdue.sort(key=lambda e: _primary(e))
    this_month.sort(key=lambda e: _primary(e))
    next_90.sort(key=lambda e: _primary(e))

    # Group next-90 items by month heading.
    next_90_months: list[dict] = []
    for e in next_90:
        label = _primary(e).strftime("%B %Y")
        if not next_90_months or next_90_months[-1]["label"] != label:
            next_90_months.append({"label": label, "items": []})
        next_90_months[-1]["items"].append(e)

    cal_providers = {e.id: _cal_provider(e) for e in equipment}

    print_mode = request.args.get("print") == "1"
    template = "admin/equipment/schedule_print.html" if print_mode else "admin/equipment/schedule.html"
    return render_template(
        template,
        overdue=overdue,
        this_month=this_month,
        next_90_months=next_90_months,
        beyond=beyond,
        cal_providers=cal_providers,
        due_status=due_status,
        today=today,
    )


# ---------- New ----------
@bp.get("/equipment/new")
@require_permission("equipment.create")
def equipment_new_get():
    return render_template("admin/equipment/new.html")


@bp.post("/equipment/new")
@require_permission("equipment.create")
def equipment_new_post():
    s = db_session()
    u = _current_user()

    custom_fields, custom_fields_error = parse_custom_fields(request.form.get("custom_fields"))
    if custom_fields_error:
        flash(custom_fields_error, "danger")
        return redirect(url_for("equipment.equipment_new_get"))

    payload = {
        "equip_code": request.form.get("equip_code"),
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "mfg": request.form.get("mfg"),
        "model_no": request.form.get("model_no"),
        "serial_no": request.form.get("serial_no"),
        "date_in_service": request.form.get("date_in_service"),
        "location": request.form.get("location"),
        "cal_interval": request.form.get("cal_interval"),
        "cal_interval_text": request.form.get("cal_interval_text"),
        "last_cal_date": request.form.get("last_cal_date"),
        "cal_due_date": request.form.get("cal_due_date"),
        "pm_interval": request.form.get("pm_interval"),
        "pm_interval_text": request.form.get("pm_interval_text"),
        "last_pm_date": request.form.get("last_pm_date"),
        "pm_due_date": request.form.get("pm_due_date"),
        "comments": request.form.get("comments"),
        "custom_fields": custom_fields,
    }

    errors = validate_equipment_payload(payload)
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("equipment.equipment_new_get"))

    # Check for duplicate equip_code
    existing = s.query(Equipment).filter(Equipment.equip_code == payload["equip_code"].strip()).one_or_none()
    if existing:
        flash("Equipment code already exists.", "danger")
        return redirect(url_for("equipment.equipment_new_get"))

    equipment = create_equipment(s, payload, u)

    pdf_ref = (request.form.get("pdf_ref") or "").strip()
    if pdf_ref and f"equipment_pdf_{pdf_ref}" in session:
        pdf_info = session.pop(f"equipment_pdf_{pdf_ref}")
        try:
            storage = storage_from_config(current_app.config)
            fobj = storage.open(pdf_info["storage_key"])
            file_bytes = fobj.read()
            upload_equipment_document(
                s,
                equipment,
                file_bytes,
                pdf_info.get("filename") or "document.pdf",
                pdf_info.get("content_type") or "application/pdf",
                u,
                description="Equipment Requirements Form (auto-attached from extraction)",
                document_type="Requirements Form",
                extracted_text=pdf_info.get("raw_text"),
                category="requirements_form",
                is_primary=True,
            )
            storage.delete(pdf_info["storage_key"])
        except Exception as e:
            current_app.logger.warning("Failed to attach extracted PDF: %s", e)

    s.commit()

    flash("Equipment created.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment.id))


# ---------- Detail ----------
@bp.get("/equipment/<int:equipment_id>")
@require_permission("equipment.view")
def equipment_detail(equipment_id: int):
    s = db_session()
    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    # Get non-deleted documents
    documents = (
        s.query(ManagedDocument)
        .filter(ManagedDocument.entity_type == "equipment")
        .filter(ManagedDocument.entity_id == equipment.id)
        .filter(ManagedDocument.is_deleted.is_(False))
        .order_by(ManagedDocument.uploaded_at.desc())
        .all()
    )

    documents_by_category: dict[str, list[ManagedDocument]] = {k: [] for k in DOCUMENT_CATEGORIES}
    for doc in documents:
        documents_by_category.setdefault(doc.category or "general", []).append(doc)
    primary_docs = {
        "requirements_form": next((d for d in documents_by_category.get("requirements_form", []) if d.is_primary), None),
        "spec_document": next((d for d in documents_by_category.get("spec_document", []) if d.is_primary), None),
    }

    # Get all suppliers for the "Add Supplier" dropdown (excluding already associated)
    associated_supplier_ids = {assoc.supplier_id for assoc in equipment.supplier_associations}
    available_suppliers = s.query(Supplier).filter(~Supplier.id.in_(associated_supplier_ids)).order_by(Supplier.name).all() if associated_supplier_ids else s.query(Supplier).order_by(Supplier.name).all()

    return render_template(
        "admin/equipment/detail.html",
        equipment=equipment,
        documents=documents,
        documents_by_category=documents_by_category,
        primary_docs=primary_docs,
        doc_categories=DOCUMENT_CATEGORIES,
        available_suppliers=available_suppliers,
        today=date.today(),
        due_status=due_status,
    )


@bp.get("/equipment/import-master")
@require_permission("equipment.edit")
def equipment_import_master_get():
    return render_template("admin/equipment/import_master.html")


@bp.post("/equipment/import-master")
@require_permission("equipment.edit")
def equipment_import_master_post():
    s = db_session()
    u = _current_user()
    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please choose an Equipment Master List .xlsx file.", "danger")
        return redirect(url_for("equipment.equipment_import_master_get"))
    if not f.filename.lower().endswith(".xlsx"):
        flash("File must be an .xlsx spreadsheet.", "danger")
        return redirect(url_for("equipment.equipment_import_master_get"))

    try:
        result = import_equipment_master(s, f.read(), u)
    except Exception as e:  # noqa: BLE001
        current_app.logger.exception("Equipment master import failed: %s", e)
        flash(f"Import failed: {e}", "danger")
        return redirect(url_for("equipment.equipment_import_master_get"))

    if result["errors"]:
        s.commit()
        flash(
            f"Imported with issues: {result['created']} created, {result['updated']} updated, "
            f"{result['skipped']} skipped. First issue: {result['errors'][0]}",
            "warning",
        )
    else:
        s.commit()
        flash(f"Import complete: {result['created']} created, {result['updated']} updated.", "success")
    return redirect(url_for("equipment.equipment_list"))


@bp.get("/equipment/bulk-import")
@require_permission("equipment.edit")
def equipment_bulk_import_get():
    import os

    requirements_forms: list[str] = []
    spec_documents: list[str] = []

    req_folder = "docs/EquipmentRequirementsForm"
    if os.path.exists(req_folder):
        requirements_forms = [f for f in os.listdir(req_folder) if f.lower().endswith(".pdf")]

    spec_folder = "docs/SpecificationsForm"
    if os.path.exists(spec_folder):
        spec_documents = [f for f in os.listdir(spec_folder) if f.lower().endswith(".docx")]

    return render_template(
        "admin/equipment/bulk_import.html",
        requirements_forms=sorted(requirements_forms),
        spec_documents=sorted(spec_documents),
        req_folder=req_folder,
        spec_folder=spec_folder,
    )


@bp.post("/equipment/bulk-import")
@require_permission("equipment.edit")
def equipment_bulk_import_post():
    import os
    from app.eqms.modules.equipment.parsers.pdf import (
        EQUIPMENT_SPEC_MAP,
        parse_requirements_form_filename,
        parse_spec_document_filename,
    )

    s = db_session()
    u = _current_user()
    req_folder = "docs/EquipmentRequirementsForm"
    spec_folder = "docs/SpecificationsForm"

    imported = {"requirements": 0, "specs": 0, "supplies": 0, "skipped": 0}

    def _process_requirements_file(fname: str, file_bytes: bytes) -> None:
        info = parse_requirements_form_filename(fname)
        equip_code = info.get("equip_code")
        if not equip_code:
            imported["skipped"] += 1
            return
        description = info.get("description")
        equipment = s.query(Equipment).filter(Equipment.equip_code == equip_code).one_or_none()
        if not equipment:
            payload = {"equip_code": equip_code, "status": "Active", "description": description}
            equipment = create_equipment(s, payload, u)
        elif description and not (equipment.description or "").strip():
            equipment.description = description
        upload_equipment_document(
            s,
            equipment,
            file_bytes,
            fname,
            "application/pdf",
            u,
            description="Requirements Form",
            document_type="Requirements Form",
            category="requirements_form",
            is_primary=True,
        )
        imported["requirements"] += 1

    def _process_spec_file(fname: str, file_bytes: bytes) -> None:
        info = parse_spec_document_filename(fname)
        spec_code = info.get("spec_code")
        spec_type = info.get("type")
        description = info.get("description")
        if not spec_code:
            imported["skipped"] += 1
            return

        if spec_type == "equipment":
            equip_code = None
            for k, v in EQUIPMENT_SPEC_MAP.items():
                if v == spec_code:
                    equip_code = k
                    break
            if not equip_code:
                imported["skipped"] += 1
                return
            equipment = s.query(Equipment).filter(Equipment.equip_code == equip_code).one_or_none()
            if not equipment:
                payload = {"equip_code": equip_code, "status": "Active", "description": description}
                equipment = create_equipment(s, payload, u)
            elif description and not (equipment.description or "").strip():
                equipment.description = description

            upload_equipment_document(
                s,
                equipment,
                file_bytes,
                fname,
                SPEC_CONTENT_TYPE,
                u,
                description="Specification Document",
                document_type="Specification",
                category="spec_document",
                is_primary=True,
            )
            imported["specs"] += 1
        else:
            supply = s.query(Supply).filter(Supply.supply_code == spec_code).one_or_none()
            if not supply:
                payload = {"supply_code": spec_code, "status": "Active", "description": description}
                supply = create_supply(s, payload, u)
            upload_supply_document(
                s,
                supply,
                file_bytes,
                fname,
                SPEC_CONTENT_TYPE,
                u,
                category="spec_document",
                description="Specification Document",
                is_primary=True,
            )
            imported["supplies"] += 1

    uploaded_req_files = request.files.getlist("requirements_files")
    uploaded_spec_files = request.files.getlist("spec_files")
    use_server_folders = (request.form.get("use_server_folders") or "").lower() == "true"

    for f in uploaded_req_files:
        if not f or not f.filename:
            continue
        if not f.filename.lower().endswith(".pdf"):
            imported["skipped"] += 1
            continue
        _process_requirements_file(f.filename, f.read())

    for f in uploaded_spec_files:
        if not f or not f.filename:
            continue
        if not f.filename.lower().endswith(".docx"):
            imported["skipped"] += 1
            continue
        _process_spec_file(f.filename, f.read())

    if use_server_folders:
        req_files = [f for f in os.listdir(req_folder) if f.lower().endswith(".pdf")] if os.path.exists(req_folder) else []
        spec_files = [f for f in os.listdir(spec_folder) if f.lower().endswith(".docx")] if os.path.exists(spec_folder) else []

        for fname in req_files:
            file_path = os.path.join(req_folder, fname)
            with open(file_path, "rb") as fobj:
                file_bytes = fobj.read()
            _process_requirements_file(fname, file_bytes)

        for fname in spec_files:
            file_path = os.path.join(spec_folder, fname)
            with open(file_path, "rb") as fobj:
                file_bytes = fobj.read()
            _process_spec_file(fname, file_bytes)

    s.commit()
    flash(
        f"Bulk import completed. Requirements: {imported['requirements']}, Specs: {imported['specs']}, Supplies: {imported['supplies']}, Skipped: {imported['skipped']}.",
        "success",
    )
    return redirect(url_for("equipment.equipment_list"))


# ---------- Edit ----------
@bp.get("/equipment/<int:equipment_id>/edit")
@require_permission("equipment.edit")
def equipment_edit_get(equipment_id: int):
    s = db_session()
    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)
    return render_template("admin/equipment/edit.html", equipment=equipment)


@bp.post("/equipment/<int:equipment_id>/edit")
@require_permission("equipment.edit")
def equipment_edit_post(equipment_id: int):
    s = db_session()
    u = _current_user()
    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    custom_fields, custom_fields_error = parse_custom_fields(request.form.get("custom_fields"))
    if custom_fields_error:
        flash(custom_fields_error, "danger")
        return redirect(url_for("equipment.equipment_edit_get", equipment_id=equipment_id))

    payload = {
        "status": request.form.get("status"),
        "description": request.form.get("description"),
        "mfg": request.form.get("mfg"),
        "model_no": request.form.get("model_no"),
        "serial_no": request.form.get("serial_no"),
        "date_in_service": request.form.get("date_in_service"),
        "location": request.form.get("location"),
        "cal_interval": request.form.get("cal_interval"),
        "cal_interval_text": request.form.get("cal_interval_text"),
        "last_cal_date": request.form.get("last_cal_date"),
        "cal_due_date": request.form.get("cal_due_date"),
        "pm_interval": request.form.get("pm_interval"),
        "pm_interval_text": request.form.get("pm_interval_text"),
        "last_pm_date": request.form.get("last_pm_date"),
        "pm_due_date": request.form.get("pm_due_date"),
        "comments": request.form.get("comments"),
        "custom_fields": custom_fields,
    }

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for change is required.", "danger")
        return redirect(url_for("equipment.equipment_edit_get", equipment_id=equipment_id))

    update_equipment(s, equipment, payload, u, reason=reason)
    s.commit()

    flash("Equipment updated.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))


def _upload_equipment_document(
    *,
    s,
    equipment: Equipment,
    file_storage,
    user: User,
    category: str,
    description: str | None,
    document_type: str | None,
) -> None:
    if category not in DOCUMENT_CATEGORIES:
        raise ValueError("Invalid document category.")

    if category in ("requirements_form", "spec_document"):
        (
            s.query(ManagedDocument)
            .filter(
                ManagedDocument.equipment_id == equipment.id,
                ManagedDocument.category == category,
                ManagedDocument.is_primary.is_(True),
            )
            .update({"is_primary": False})
        )
        is_primary = True
    else:
        is_primary = False

    content_type = (file_storage.mimetype or "application/octet-stream").strip()
    file_bytes = file_storage.read()

    upload_equipment_document(
        s,
        equipment,
        file_bytes,
        file_storage.filename,
        content_type,
        user,
        description=description,
        document_type=document_type,
        category=category,
        is_primary=is_primary,
    )


# ---------- Document Upload ----------
@bp.post("/equipment/<int:equipment_id>/documents/<category>")
@require_permission("equipment.upload")
def equipment_document_upload(equipment_id: int, category: str):
    s = db_session()
    u = _current_user()
    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    f = request.files.get("file")
    if not f or not f.filename:
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    description = (request.form.get("description") or "").strip() or None
    document_type = (request.form.get("document_type") or "").strip() or None

    try:
        _upload_equipment_document(
            s=s,
            equipment=equipment,
            file_storage=f,
            user=u,
            category=category,
            description=description,
            document_type=document_type,
        )
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))
    s.commit()

    flash("Document uploaded.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))


@bp.post("/equipment/<int:equipment_id>/documents/upload")
@require_permission("equipment.upload")
def equipment_document_upload_legacy(equipment_id: int):
    """Backward-compatible upload route (general category)."""
    return equipment_document_upload(equipment_id, "general")


@bp.post("/equipment/extract-from-pdf")
@require_permission("equipment.upload")
def equipment_extract_from_pdf():
    """Extract field values from uploaded PDF and return as JSON for form auto-fill."""
    from app.eqms.modules.equipment.parsers.pdf import extract_equipment_fields_from_pdf, _extract_text
    from werkzeug.utils import secure_filename
    import hashlib

    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf_file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    pdf_bytes = file.read()
    extracted = extract_equipment_fields_from_pdf(pdf_bytes, filename=file.filename)

    pdf_ref = None
    if request.form.get("store_pdf") == "1":
        raw_text = _extract_text(pdf_bytes)
        sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        pdf_ref = sha256[:16]
        temp_key = f"temp_equipment_pdf/{pdf_ref}"
        storage = storage_from_config(current_app.config)
        storage.put_bytes(temp_key, pdf_bytes, content_type="application/pdf")
        session[f"equipment_pdf_{pdf_ref}"] = {
            "filename": secure_filename(file.filename),
            "storage_key": temp_key,
            "raw_text": raw_text,
            "content_type": "application/pdf",
            "size_bytes": len(pdf_bytes),
        }

    return jsonify(
        {
            "success": True,
            "extracted_fields": extracted,
            "pdf_ref": pdf_ref,
            "message": f"Extracted {len(extracted)} field(s) from PDF. Review and edit as needed.",
        }
    )


# ---------- Document Download ----------
@bp.get("/equipment/<int:equipment_id>/documents/<int:doc_id>/download")
@require_permission("equipment.view")
def equipment_document_download(equipment_id: int, doc_id: int):
    from flask import current_app
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    doc = s.get(ManagedDocument, doc_id)
    if not doc or doc.equipment_id != equipment_id or doc.is_deleted:
        abort(404)

    storage = storage_from_config(current_app.config)
    fobj = storage.open(doc.storage_key)

    record_event(
        s,
        actor=u,
        action="equipment.document_download",
        entity_type="ManagedDocument",
        entity_id=str(doc.id),
        metadata={"equipment_id": equipment_id, "filename": doc.original_filename},
    )
    s.commit()

    return send_file(
        fobj,
        mimetype=doc.content_type,
        as_attachment=True,
        download_name=doc.original_filename,
        max_age=0,
    )


@bp.get("/equipment/<int:equipment_id>/documents/<int:doc_id>/view")
@require_permission("equipment.view")
def equipment_document_view(equipment_id: int, doc_id: int):
    from flask import current_app
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    doc = s.get(ManagedDocument, doc_id)
    if not doc or doc.equipment_id != equipment_id or doc.is_deleted:
        abort(404)

    storage = storage_from_config(current_app.config)

    record_event(
        s,
        actor=u,
        action="equipment.document_view",
        entity_type="ManagedDocument",
        entity_id=str(doc.id),
        metadata={"equipment_id": equipment_id, "filename": doc.original_filename},
    )
    s.commit()

    # Server-side rendering for .docx, .xlsx, .xls, .csv
    if needs_server_render(doc.original_filename):
        file_bytes = storage.get_bytes(doc.storage_key)
        download_url = url_for("equipment.equipment_document_download", equipment_id=equipment_id, doc_id=doc_id)
        back_url = url_for("equipment.equipment_detail", equipment_id=equipment_id)
        response = render_document_to_response(
            file_bytes, doc.original_filename, doc.content_type,
            download_url=download_url, back_url=back_url,
        )
        if response:
            return response

    fobj = storage.open(doc.storage_key)
    inline = allow_inline_view(doc.original_filename, doc.content_type)
    return send_file(
        fobj,
        mimetype=doc.content_type,
        as_attachment=not inline,
        download_name=doc.original_filename,
        max_age=0,
    )


# ---------- Document Delete ----------
@bp.post("/equipment/<int:equipment_id>/documents/<int:doc_id>/delete")
@require_permission("equipment.upload")
def equipment_document_delete(equipment_id: int, doc_id: int):
    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    doc = s.get(ManagedDocument, doc_id)
    if not doc or doc.equipment_id != equipment_id or doc.is_deleted:
        abort(404)

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for deletion is required.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    delete_equipment_document(s, doc, u, reason)
    s.commit()

    flash("Document deleted.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))


# ---------- Add Supplier ----------
@bp.post("/equipment/<int:equipment_id>/suppliers")
@require_permission("equipment.edit")
def equipment_supplier_add(equipment_id: int):
    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    supplier_id = request.form.get("supplier_id")
    if not supplier_id:
        flash("Please select a supplier.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    supplier = s.get(Supplier, int(supplier_id))
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    # Check for duplicate association
    existing = (
        s.query(EquipmentSupplier)
        .filter(EquipmentSupplier.equipment_id == equipment_id)
        .filter(EquipmentSupplier.supplier_id == supplier.id)
        .one_or_none()
    )
    if existing:
        flash("Supplier is already associated with this equipment.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    relationship_type = (request.form.get("relationship_type") or "").strip() or None
    notes = (request.form.get("notes") or "").strip() or None

    add_supplier_to_equipment(s, equipment, supplier, relationship_type, notes, u)
    s.commit()

    flash(f"Supplier '{supplier.name}' associated.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))


# ---------- Remove Supplier ----------
@bp.post("/equipment/<int:equipment_id>/suppliers/<int:supplier_id>/remove")
@require_permission("equipment.edit")
def equipment_supplier_remove(equipment_id: int, supplier_id: int):
    s = db_session()
    u = _current_user()

    equipment = s.get(Equipment, equipment_id)
    if not equipment:
        abort(404)

    assoc = (
        s.query(EquipmentSupplier)
        .filter(EquipmentSupplier.equipment_id == equipment_id)
        .filter(EquipmentSupplier.supplier_id == supplier_id)
        .one_or_none()
    )
    if not assoc:
        flash("Association not found.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for removal is required.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))

    remove_supplier_from_equipment(s, assoc, u, reason)
    s.commit()

    flash("Supplier association removed.", "success")
    return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))
