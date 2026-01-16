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
    create_distribution_entry,
    delete_distribution_entry,
    generate_tracing_report_csv,
    query_distribution_entries,
    update_distribution_entry,
    upload_approval_eml,
    validate_distribution_payload,
)
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


def _parse_filters() -> dict:
    return parse_distribution_filters(request.args)


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
    return render_template(
        "admin/distribution_log/list.html",
        entries=entries,
        filters=filters,
        page=page,
        per_page=per_page,
        total=total,
        has_prev=has_prev,
        has_next=has_next,
    )


@bp.get("/distribution-log/new")
@require_permission("distribution_log.create")
def distribution_log_new_get():
    return render_template("admin/distribution_log/edit.html", entry=None)


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
    }

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
    s = db_session()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        from flask import abort

        abort(404)
    return render_template("admin/distribution_log/edit.html", entry=entry)


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
        "customer_name": request.form.get("customer_name"),
        "source": request.form.get("source"),
        "sku": request.form.get("sku"),
        "lot_number": request.form.get("lot_number"),
        "quantity": request.form.get("quantity"),
        "city": request.form.get("city"),
        "state": request.form.get("state"),
        "tracking_number": request.form.get("tracking_number"),
    }

    errs = validate_distribution_payload(payload)
    if errs:
        flash("; ".join([f"{e.field}: {e.message}" for e in errs]), "danger")
        return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))

    update_distribution_entry(s, entry, payload, user=u, reason=reason)
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
    # P1 placeholder: no parsing implemented
    return render_template("admin/distribution_log/import.html", mode="pdf")


@bp.post("/distribution-log/import-pdf")
@require_permission("distribution_log.import")
def distribution_log_import_pdf_post():
    flash("PDF import is P1 and not implemented yet.", "danger")
    return redirect(url_for("rep_traceability.distribution_log_import_pdf_get"))


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
        w.writerow(
            [
                str(e.ship_date),
                e.order_number,
                e.facility_name,
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
    return render_template("admin/tracing/generate.html")


@bp.post("/tracing/generate")
@require_permission("tracing_reports.generate")
def tracing_generate_post():
    s = db_session()
    u = _current_user()

    month = normalize_text(request.form.get("month"))
    rep_id = normalize_text(request.form.get("rep_id"))
    source = normalize_source(request.form.get("source"))
    sku = normalize_text(request.form.get("sku"))
    customer = normalize_text(request.form.get("customer"))

    if not month:
        flash("Month is required (YYYY-MM).", "danger")
        return redirect(url_for("rep_traceability.tracing_generate_get"))

    try:
        tr = generate_tracing_report_csv(
            s,
            user=u,
            filters={"month": month, "rep_id": rep_id or None, "source": source or "all", "sku": sku or "all", "customer": customer},
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

