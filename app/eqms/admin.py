import csv
import io
from datetime import date, datetime, time, timedelta

from flask import Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, url_for

from app.eqms.db import db_session
from app.eqms.models import AuditEvent, User, Role
from app.eqms.rbac import require_any_permission, require_permission, user_has_permission
from app.eqms.utils import current_user as _current_user

bp = Blueprint("admin", __name__)


@bp.before_request
def _guard_admin_shell():
    """
    Gate the admin shell.

    Capability model (Phase 3):
    - admin.edit  = full admin. Unrestricted access to the admin shell.
    - admin.view  = access the admin shell and read shared QMS content. Held by
      both admins and read-only users (staff, readonly). A user with admin.view
      but NOT admin.edit is read-only: every state-changing request on the admin
      blueprint is rejected with 403 as defence-in-depth on top of per-route
      permission checks. The sole allowed write is self-service profile update
      (My Account), which changes only the acting user's own record.
    - Auditor-only users (auditor portal access, no admin shell) are blocked.
    """
    user = getattr(g, "current_user", None)
    if not user:
        return None
    if user_has_permission(user, "admin.edit"):
        return None
    if user_has_permission(user, "admin.view"):
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.endpoint != "admin.me_update":
            g.missing_permission = "admin.edit"  # type: ignore[attr-defined]
            abort(403)
        return None
    if user_has_permission(user, "auditor_portal.access"):
        abort(403)
    return None


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None




def _diagnostics_allowed() -> bool:
    import os
    from app.eqms.rbac import user_has_permission

    env = (os.environ.get("ENV") or "development").strip().lower()
    enabled = (os.environ.get("ADMIN_DIAGNOSTICS_ENABLED") or "").strip() == "1"
    if env != "production" or enabled:
        return True
    user = getattr(g, "current_user", None)
    if user and user.is_active:
        return user_has_permission(user, "admin.view")
    return False


@bp.get("/")
@require_permission("admin.view")
def index():
    # System Status strip moved to Admin Tools (Prompt 18) — keep the main
    # dashboard clean and avoid computing dashboard_stats here.
    # Cheap single-count exception: overdue-training badge for training managers.
    # Guarded so a degraded/partial schema never 500s the dashboard.
    training_overdue_count = 0
    if user_has_permission(getattr(g, "current_user", None), "training.manage"):
        from app.eqms.modules.training.models import TrainingAssignment

        try:
            s = db_session()
            training_overdue_count = (
                s.query(TrainingAssignment)
                .filter(
                    TrainingAssignment.acknowledged_at.is_(None),
                    TrainingAssignment.due_date.isnot(None),
                    TrainingAssignment.due_date < date.today(),
                )
                .count()
            )
        except Exception:  # noqa: BLE001
            db_session().rollback()
            training_overdue_count = 0
    return render_template("admin/index.html", training_overdue_count=training_overdue_count)


def _add_months(d: date, months: int) -> date:
    """Return d shifted forward by `months` calendar months (clamped day)."""
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    # Clamp to the last valid day of the target month.
    import calendar

    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@bp.get("/quality-objectives")
@require_any_permission("admin.view", "staff.view")
def quality_objectives():
    import json

    from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
    from app.eqms.modules.quality_objectives import get_objectives, get_scorecard

    s = db_session()
    objectives = get_objectives(s)
    scorecard = get_scorecard(s)

    # Quality Plans & Reports: files in the management_reviews "Quality Planning" folder.
    qp_files = []
    qp_folder = (
        s.query(AdminDocFolder)
        .filter(AdminDocFolder.library_key == "management_reviews", AdminDocFolder.name == "Quality Planning")
        .first()
    )
    if qp_folder is not None:
        qp_files = (
            s.query(AdminDocFile)
            .filter(AdminDocFile.library_key == "management_reviews", AdminDocFile.folder_id == qp_folder.id)
            .order_by(AdminDocFile.uploaded_at.desc())
            .all()
        )

    return render_template(
        "admin/quality_objectives.html",
        objectives=objectives,
        scorecard=scorecard,
        scorecard_json=json.dumps(scorecard, indent=2),
        qp_files=qp_files,
        can_edit=user_has_permission(getattr(g, "current_user", None), "admin.edit"),
    )


@bp.post("/quality-objectives")
@require_permission("admin.edit")
def quality_objectives_save():
    from app.eqms.modules.quality_objectives import save_objectives

    s = db_session()
    save_objectives(s, request.form.to_dict(), _current_user())
    s.commit()
    flash("Quality objective values saved.", "success")
    return redirect(url_for("admin.quality_objectives"))


@bp.post("/quality-objectives/scorecard")
@require_permission("admin.edit")
def quality_scorecard_save():
    from app.eqms.modules.quality_objectives import save_scorecard

    s = db_session()
    ok, message = save_scorecard(s, request.form.get("scorecard_json") or "", _current_user())
    if ok:
        s.commit()
        flash(message, "success")
    else:
        flash(message, "danger")
    return redirect(url_for("admin.quality_objectives"))


@bp.get("/reports/due-this-period.csv")
@require_permission("admin.edit")
def reports_due_csv():
    """"What's Due" report: overdue items plus items due within the next N months."""
    from app.eqms.modules.equipment.models import Equipment
    from app.eqms.modules.equipment.service import due_status
    from app.eqms.modules.suppliers.models import Supplier
    from app.eqms.modules.suppliers.service import date_status
    from app.eqms.modules.training.models import TrainingAssignment
    from app.eqms.modules.training.service import assignment_status

    s = db_session()
    today = date.today()
    months = request.args.get("months", 3, type=int) or 3
    cutoff = _add_months(today, months)

    def _cal_supplier(eq) -> str:
        for assoc in eq.supplier_associations:
            if (assoc.relationship_type or "").strip().lower() == "calibration service provider":
                return assoc.supplier.name if assoc.supplier else ""
        return ""

    def _in_window(d: date | None) -> bool:
        return d is not None and d <= cutoff  # includes all overdue (past) dates

    rows: list[list[str]] = []

    equipment = (
        s.query(Equipment).filter(Equipment.status != "Retired").order_by(Equipment.equip_code).all()
    )
    for eq in equipment:
        label = f"{eq.equip_code} — {eq.description or ''}".strip(" —")
        supplier = _cal_supplier(eq)
        if _in_window(eq.cal_due_date):
            st = due_status(eq.cal_due_date, eq.cal_interval_text, today)
            rows.append(["Equipment CAL", label, eq.cal_due_date.isoformat(), st["label"], supplier])
        if _in_window(eq.pm_due_date):
            st = due_status(eq.pm_due_date, eq.pm_interval_text, today)
            rows.append(["Equipment PM", label, eq.pm_due_date.isoformat(), st["label"], supplier])

    suppliers = s.query(Supplier).order_by(Supplier.name).all()
    for sup in suppliers:
        if _in_window(sup.next_reevaluation_date):
            st = date_status(sup.next_reevaluation_date, today)
            rows.append(["Supplier Re-eval", sup.name, sup.next_reevaluation_date.isoformat(),
                         st["label"], "Next re-evaluation date"])

    assignments = (
        s.query(TrainingAssignment)
        .filter(TrainingAssignment.acknowledged_at.is_(None))
        .order_by(TrainingAssignment.due_date)
        .all()
    )
    for a in assignments:
        if _in_window(a.due_date):
            st = assignment_status(a, today)
            email = a.assignee.email if a.assignee else ""
            rows.append(["Training", a.item_title, a.due_date.isoformat(), st["label"], email])

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["section", "item", "due_date", "status", "notes"])
    writer.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=due-this-period-{today.isoformat()}.csv"},
    )


def _management_review_data() -> list[dict]:
    """
    Build the ISO 13485 management-review input sections. Each section is a dict:
      {title, summary: [(label, value)], table: {cols, rows} | None, note: str | None}
    Degrades gracefully (empty sections) if a table is missing in a hermetic test DB.
    """
    from sqlalchemy import func, or_

    from app.eqms.models import SystemSetting  # noqa: F401 (ensures table registered)
    from app.eqms.modules.admin_docs.models import AdminDocFile, AdminDocFolder
    from app.eqms.modules.capas.models import CAPARecord
    from app.eqms.modules.document_control.models import Document, DocumentRevision
    from app.eqms.modules.equipment.models import Equipment
    from app.eqms.modules.purchasing.models import PurchaseOrder
    from app.eqms.modules.quality_objectives import get_objectives
    from app.eqms.modules.suppliers.models import Supplier
    from app.eqms.modules.training.models import TrainingAssignment
    from app.eqms.utils import utcnow

    s = db_session()
    today = date.today()
    since_dt = utcnow() - timedelta(days=365)
    since_date = today - timedelta(days=365)
    sections: list[dict] = []

    def _count(model_col, *filters) -> int:
        return int(s.query(func.count(model_col)).filter(*filters).scalar() or 0)

    try:
        # Section 1 — Document Control Activity
        cat_rows = (
            s.query(Document.category, func.count(func.distinct(Document.id)))
            .join(DocumentRevision, DocumentRevision.document_id == Document.id)
            .filter(DocumentRevision.released_at >= since_dt)
            .group_by(Document.category)
            .all()
        )
        recent = (
            s.query(DocumentRevision)
            .filter(DocumentRevision.released_at.isnot(None))
            .order_by(DocumentRevision.released_at.desc())
            .limit(10)
            .all()
        )
        sections.append({
            "title": "1. Document Control Activity",
            "summary": [("Documents released (12 mo), total", sum(c for _, c in cat_rows))]
                       + [(f"  {cat or 'Uncategorized'}", c) for cat, c in sorted(cat_rows, key=lambda x: (x[0] or ""))],
            "table": {
                "cols": ["Document", "Revision", "Effective date"],
                "rows": [
                    [f"{r.document.doc_number} — {r.document.title}" if r.document else "—",
                     r.revision, r.effective_date.isoformat() if r.effective_date else "—"]
                    for r in recent
                ],
            },
            "note": "10 most recently released revisions.",
        })

        # Section 2 — Customer Feedback & Complaints (file-count proxy)
        pms_recent = _count(
            AdminDocFile.id,
            AdminDocFile.library_key == "post_market_surveillance",
            AdminDocFile.uploaded_at >= since_dt,
        )
        emdr_folder_ids = [
            f.id for f in s.query(AdminDocFolder)
            .filter(AdminDocFolder.library_key == "post_market_surveillance",
                    AdminDocFolder.name.ilike("%emdr%")).all()
        ]
        emdr_count = 0
        if emdr_folder_ids:
            emdr_count = _count(AdminDocFile.id, AdminDocFile.folder_id.in_(emdr_folder_ids))
        sections.append({
            "title": "2. Customer Feedback & Complaints",
            "summary": [
                ("PMS files uploaded (12 mo)", pms_recent),
                ("eMDR files on file", emdr_count),
            ],
            "table": None,
            "note": "File-count proxy — no structured complaint model exists.",
        })

        # Section 3 — Process Performance / Quality Objectives
        objectives = get_objectives(s)
        sections.append({
            "title": "3. Process Performance / Quality Objectives",
            "summary": [],
            "table": {
                "cols": ["Objective", "Target", "Current value"],
                "rows": [[o["name"], o["target"], o.get("value") or "—"] for o in objectives],
            },
            "note": None,
        })

        # Section 4 — Equipment Status (Active only; Inactive tagged-out units excluded)
        overdue_cal = _count(Equipment.id, Equipment.cal_due_date < today, Equipment.status == "Active")
        overdue_pm = _count(Equipment.id, Equipment.pm_due_date < today, Equipment.status == "Active")
        due_soon = _count(
            Equipment.id, Equipment.status == "Active",
            or_(Equipment.cal_due_date.between(today, today + timedelta(days=30)),
                Equipment.pm_due_date.between(today, today + timedelta(days=30))),
        )
        overdue_items = (
            s.query(Equipment)
            .filter(Equipment.status == "Active",
                    or_(Equipment.cal_due_date < today, Equipment.pm_due_date < today))
            .order_by(Equipment.equip_code).all()
        )
        sections.append({
            "title": "4. Equipment Status",
            "summary": [
                ("Active", _count(Equipment.id, Equipment.status == "Active")),
                ("Overdue calibration", overdue_cal),
                ("Overdue PM", overdue_pm),
                ("Due soon (30 days)", due_soon),
            ],
            "table": {
                "cols": ["Equipment", "CAL due", "PM due"],
                "rows": [[f"{e.equip_code} — {e.description or ''}".strip(" —"),
                          e.cal_due_date.isoformat() if e.cal_due_date else "—",
                          e.pm_due_date.isoformat() if e.pm_due_date else "—"] for e in overdue_items],
            },
            "note": "Currently overdue items listed." if overdue_items else "No overdue equipment.",
        })

        # Section 5 — Supplier Status
        expired_certs = (
            s.query(Supplier)
            .filter(Supplier.certification_expiration.isnot(None),
                    Supplier.certification_expiration < today)
            .order_by(Supplier.name).all()
        )
        sections.append({
            "title": "5. Supplier Status",
            "summary": [
                ("Approved", _count(Supplier.id, Supplier.status == "Approved")),
                ("Conditional", _count(Supplier.id, Supplier.status == "Conditional")),
                ("Pending", _count(Supplier.id, Supplier.status == "Pending")),
                ("Re-evaluation overdue", _count(Supplier.id, Supplier.next_reevaluation_date < today)),
            ],
            "table": {
                "cols": ["Supplier", "Certification expired"],
                "rows": [[sup.name, sup.certification_expiration.isoformat()] for sup in expired_certs],
            },
            "note": "Expired certifications listed." if expired_certs else "No expired certifications.",
        })

        # Section 6 — CAPAs
        open_pending = (
            s.query(CAPARecord)
            .filter(CAPARecord.status.in_(["Open", "Pending Effectiveness"]))
            .order_by(CAPARecord.capa_number).all()
        )
        closed_12mo = _count(
            CAPARecord.id, CAPARecord.status == "Closed",
            or_(CAPARecord.closed_date.is_(None), CAPARecord.closed_date >= since_date),
        )
        sections.append({
            "title": "6. CAPAs",
            "summary": [
                ("Open", _count(CAPARecord.id, CAPARecord.status == "Open")),
                ("Pending Effectiveness", _count(CAPARecord.id, CAPARecord.status == "Pending Effectiveness")),
                ("Closed (12 mo)", closed_12mo),
            ],
            "table": {
                "cols": ["CAPA", "Title", "Status", "Target close"],
                "rows": [[c.capa_number, c.title, c.status,
                          c.target_close_date.isoformat() if c.target_close_date else "—"] for c in open_pending],
            },
            "note": "Open and pending-effectiveness CAPAs listed.",
        })

        # Section 7 — Training
        acked_year = _count(
            TrainingAssignment.id,
            TrainingAssignment.acknowledged_at.isnot(None),
            func.extract("year", TrainingAssignment.acknowledged_at) == today.year,
        )
        open_ct = _count(TrainingAssignment.id, TrainingAssignment.acknowledged_at.is_(None))
        overdue_ct = _count(
            TrainingAssignment.id, TrainingAssignment.acknowledged_at.is_(None),
            TrainingAssignment.due_date < today,
        )
        overdue_users = (
            s.query(User.email, func.count(TrainingAssignment.id))
            .join(TrainingAssignment, TrainingAssignment.assigned_to_user_id == User.id)
            .filter(TrainingAssignment.acknowledged_at.is_(None), TrainingAssignment.due_date < today)
            .group_by(User.email).all()
        )
        sections.append({
            "title": "7. Training",
            "summary": [
                ("Acknowledged this year (objective 4)", acked_year),
                ("Open training items", open_ct),
                ("Overdue training items", overdue_ct),
            ],
            "table": {
                "cols": ["User", "Overdue items"],
                "rows": [[email, cnt] for email, cnt in overdue_users],
            },
            "note": "Users with overdue training listed." if overdue_users else "No overdue training.",
        })

        # Section 8 — Purchasing / Supplier Performance
        sections.append({
            "title": "8. Purchasing / Supplier Performance",
            "summary": [
                ("Pending", _count(PurchaseOrder.id, PurchaseOrder.status == "pending")),
                ("Received", _count(PurchaseOrder.id, PurchaseOrder.status == "received")),
                ("Partial", _count(PurchaseOrder.id, PurchaseOrder.status == "partial")),
                ("Cancelled", _count(PurchaseOrder.id, PurchaseOrder.status == "cancelled")),
                ("POs in last 12 months", _count(PurchaseOrder.id, PurchaseOrder.order_date >= since_date)),
            ],
            "table": None,
            "note": None,
        })
    except Exception:  # noqa: BLE001 - never 500 the review page over an incomplete schema
        s.rollback()

    return sections


@bp.get("/reports/management-review")
@require_permission("admin.edit")
def management_review():
    sections = _management_review_data()
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    if (request.args.get("format") or "").lower() == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["section", "item", "value"])
        for sec in sections:
            for label, value in sec["summary"]:
                writer.writerow([sec["title"], str(label).strip(), value])
            if sec.get("table"):
                cols = sec["table"]["cols"]
                for row in sec["table"]["rows"]:
                    item = str(row[0])
                    rest = " | ".join(str(c) for c in row[1:])
                    writer.writerow([sec["title"], item, rest])
        return Response(
            buf.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=management-review-{date.today().isoformat()}.csv"},
        )

    template = (
        "admin/reports/management_review_print.html"
        if request.args.get("print") == "1"
        else "admin/reports/management_review.html"
    )
    return render_template(template, sections=sections, generated=generated)


@bp.get("/reports")
@require_permission("admin.edit")
def reports_index():
    """Lightweight landing page linking the available reports."""
    return render_template("admin/reports/index.html")


@bp.get("/reports/weekly-brief")
@require_permission("admin.edit")
def weekly_brief_index():
    """Admin-only tool page for composing/sending the Weekly Brief email."""
    return render_template("admin/reports/weekly_brief.html")


@bp.post("/reports/weekly-brief/send")
@require_permission("admin.edit")
def weekly_brief_send():
    """Build the Weekly Brief HTML and dispatch it via the Resend API."""
    import os
    import re

    from sqlalchemy import nulls_last

    from app.eqms.modules.nre_projects.models import NREProjectEntry
    from app.eqms.modules.nre_projects.service import compute_nre_dashboard
    from app.eqms.modules.purchasing.service import build_weekly_brief_payment_rows
    from app.eqms.modules.rep_traceability.service import (
        compute_sales_dashboard,
        recent_customers_for_weekly_brief,
    )

    # 1. Parse recipients (comma- and/or newline-separated).
    raw = request.form.get("to_emails") or ""
    recipients = [tok.strip() for tok in re.split(r"[,\n]", raw) if tok.strip()]
    if not recipients:
        flash("Please enter at least one recipient email address.", "danger")
        return redirect(url_for("admin.weekly_brief_index"))

    s = db_session()

    # 2. Current-quarter sales snapshot.
    today = date.today()
    quarter_month_start = ((today.month - 1) // 3) * 3 + 1  # 1, 4, 7, or 10
    quarter_start = date(today.year, quarter_month_start, 1)
    quarter_label = (quarter_month_start - 1) // 3 + 1  # 1-4
    data = compute_sales_dashboard(s, start_date=quarter_start, end_date=None)
    stats = data["stats"]
    recent_customers = recent_customers_for_weekly_brief(s, limit=5)

    payment_rows = build_weekly_brief_payment_rows(s)

    nre_dash = compute_nre_dashboard(s, start_date=quarter_start, end_date=today)

    # 4. Active NRE invoice entries (exclude Paid / Cancelled), most recent first.
    nre_entries = (
        s.query(NREProjectEntry)
        .filter(~NREProjectEntry.invoice_status.in_(["Paid", "Cancelled"]))
        .order_by(nulls_last(NREProjectEntry.entry_date.desc()))
        .all()
    )

    # 6. Subject.
    subject = (request.form.get("subject") or "").strip() or "Silq eQMS — Weekly Brief"

    # 7. Render the self-contained HTML email.
    email_html = render_template(
        "email/weekly_brief.html",
        generated_at=datetime.utcnow(),
        quarter_start=quarter_start,
        quarter_label=quarter_label,
        stats=stats,
        recent_customers=recent_customers,
        payment_rows=payment_rows,
        nre_entries=nre_entries,
        nre_dash_project_count=nre_dash["project_count"],
        nre_dash_customer_count=nre_dash["customer_count"],
        nre_dash_revenue=nre_dash["revenue"],
        nre_dash_rows=nre_dash["rows"],
    )

    # 7. Send via Resend.
    api_key = os.environ.get("RESEND_API_KEY", "")
    from_addr = os.environ.get("EMAIL_FROM", "reports@silqeqms.com")
    if not api_key:
        flash("RESEND_API_KEY is not configured.", "danger")
        return redirect(url_for("admin.weekly_brief_index"))

    try:
        import resend

        resend.api_key = api_key
        resend.Emails.send({
            "from": f"Silq eQMS <{from_addr}>",
            "to": recipients,
            "subject": subject,
            "html": email_html,
        })
        flash(f"Brief sent to {len(recipients)} recipient(s).", "success")
    except Exception as e:  # noqa: BLE001
        current_app.logger.exception("Weekly Brief send failed: %s", e)
        flash(f"Send failed: {e}", "danger")
    return redirect(url_for("admin.weekly_brief_index"))


def _dashboard_stats() -> dict:
    """
    Single-query aggregations for the dashboard "System Status" strip (Phase 6).

    Each value is an int >= 0. Kept to simple COUNT(*) queries (no N+1). Read-only.
    """
    from sqlalchemy import func, or_

    from app.eqms.modules.document_control.models import DocumentRevision
    from app.eqms.modules.equipment.models import Equipment
    from app.eqms.modules.capas.models import CAPARecord
    from app.eqms.modules.purchasing.models import PurchaseOrder
    from app.eqms.modules.suppliers.models import Supplier
    from app.eqms.modules.training.models import TrainingAssignment
    from app.eqms.utils import utcnow

    keys = (
        "equipment_overdue_cal", "equipment_overdue_pm", "equipment_due_soon",
        "suppliers_attention", "training_open", "training_overdue",
        "docs_released_30d", "pos_pending", "capas_open",
    )
    s = db_session()
    today = date.today()
    soon = today + timedelta(days=30)
    cert_cut = today + timedelta(days=90)
    released_since = utcnow() - timedelta(days=30)

    def _count(model_col, *filters) -> int:
        return int(s.query(func.count(model_col)).filter(*filters).scalar() or 0)

    try:
        return {
            # Active only — Inactive/Retired (e.g. tagged-out ST-013) must not warn.
            "equipment_overdue_cal": _count(
                Equipment.id, Equipment.cal_due_date < today, Equipment.status == "Active"
            ),
            "equipment_overdue_pm": _count(
                Equipment.id, Equipment.pm_due_date < today, Equipment.status == "Active"
            ),
            "equipment_due_soon": _count(
                Equipment.id,
                Equipment.status == "Active",
                or_(
                    Equipment.cal_due_date.between(today, soon),
                    Equipment.pm_due_date.between(today, soon),
                ),
            ),
            "suppliers_attention": _count(
                Supplier.id,
                or_(
                    Supplier.certification_expiration < cert_cut,
                    Supplier.next_reevaluation_date < cert_cut,
                ),
            ),
            "training_open": _count(TrainingAssignment.id, TrainingAssignment.acknowledged_at.is_(None)),
            "training_overdue": _count(
                TrainingAssignment.id,
                TrainingAssignment.acknowledged_at.is_(None),
                TrainingAssignment.due_date < today,
            ),
            "docs_released_30d": _count(DocumentRevision.id, DocumentRevision.released_at >= released_since),
            "pos_pending": _count(PurchaseOrder.id, PurchaseOrder.status == "pending"),
            "capas_open": _count(
                CAPARecord.id, CAPARecord.status.in_(["Open", "Pending Effectiveness"])
            ),
        }
    except Exception:  # noqa: BLE001 - never let the dashboard 500 over its status strip
        s.rollback()
        return {k: 0 for k in keys}


@bp.get("/me")
@require_permission("admin.view")
def me():
    user = getattr(g, "current_user", None)
    role_keys: list[str] = []
    perm_keys: list[str] = []
    if user:
        role_keys = sorted({r.key for r in (user.roles or [])})
        perms = set()
        for r in user.roles or []:
            for p in r.permissions or []:
                perms.add(p.key)
        perm_keys = sorted(perms)
    return render_template("admin/me.html", user=user, role_keys=role_keys, perm_keys=perm_keys)


@bp.post("/me")
@require_permission("admin.view")
def me_update():
    """Update current user's address fields (rep contact info)."""
    import re

    s = db_session()
    user = getattr(g, "current_user", None)
    if not user:
        flash("No current user.", "danger")
        return redirect(url_for("admin.me"))

    zip_code = (request.form.get("zip") or "").strip()
    if zip_code and not re.fullmatch(r"\d{5}(-\d{4})?", zip_code):
        flash("ZIP must be 5 digits or 5+4 (e.g., 12345 or 12345-6789).", "danger")
        return redirect(url_for("admin.me"))

    user.address1 = (request.form.get("address1") or "").strip() or None
    user.address2 = (request.form.get("address2") or "").strip() or None
    user.city = (request.form.get("city") or "").strip() or None
    user.state = (request.form.get("state") or "").strip() or None
    user.zip = zip_code or None

    from app.eqms.audit import record_event
    record_event(
        s,
        actor=user,
        action="user.update_profile",
        entity_type="User",
        entity_id=str(user.id),
        metadata={"address1": user.address1, "city": user.city, "state": user.state, "zip": user.zip},
    )
    s.commit()
    flash("Profile updated.", "success")
    return redirect(url_for("admin.me"))


@bp.get("/audit")
@require_permission("admin.edit")
def audit_list():
    """
    Minimal audit trail UI (last 200 events) with simple filters:
    - action (exact/contains)
    - actor_email (contains)
    - date range (YYYY-MM-DD)
    """
    s = db_session()
    action = (request.args.get("action") or "").strip()
    actor_email = (request.args.get("actor_email") or "").strip()
    date_from = _parse_date(request.args.get("date_from") or "")
    date_to = _parse_date(request.args.get("date_to") or "")

    if (request.args.get("date_from") or "").strip() and not date_from:
        flash("date_from must be YYYY-MM-DD", "danger")
    if (request.args.get("date_to") or "").strip() and not date_to:
        flash("date_to must be YYYY-MM-DD", "danger")

    q = s.query(AuditEvent)
    if action:
        like = f"%{action}%"
        q = q.filter(AuditEvent.action.like(like))
    if actor_email:
        like = f"%{actor_email.lower()}%"
        q = q.filter(AuditEvent.actor_user_email.like(like))
    if date_from:
        q = q.filter(AuditEvent.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        # inclusive end-date (treat as whole day)
        q = q.filter(AuditEvent.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    events = q.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(500).all()
    return render_template(
        "admin/audit/list.html",
        events=events,
        action=action,
        actor_email=actor_email,
        date_from=(request.args.get("date_from") or "").strip(),
        date_to=(request.args.get("date_to") or "").strip(),
    )


@bp.get("/audit/<int:event_id>")
@require_permission("admin.edit")
def audit_detail(event_id: int):
    """
    Read-only detail page for a single audit event (SRS-6.2 verification).
    Surfaces every field SRS-6.2 requires -- timestamp (UTC), actor email,
    action, entity type/id, reason, metadata_json, client_ip, and request_id --
    so SW.SLQ010 Step 9-3 can be executed without database access.
    No edit/delete affordances are exposed (SRS-6.6).
    """
    s = db_session()
    ev = s.get(AuditEvent, event_id)
    if not ev:
        abort(404)
    return render_template("admin/audit/detail.html", event=ev)


@bp.get("/audit/export")
@require_permission("admin.edit")
def audit_export():
    s = db_session()
    u = _current_user()

    action_filter = (request.args.get("action") or "").strip()
    actor_email = (request.args.get("actor_email") or "").strip()
    date_from = _parse_date(request.args.get("date_from") or "")
    date_to = _parse_date(request.args.get("date_to") or "")

    q = s.query(AuditEvent)
    if action_filter:
        q = q.filter(AuditEvent.action.like(f"%{action_filter}%"))
    if actor_email:
        q = q.filter(AuditEvent.actor_user_email.like(f"%{actor_email.lower()}%"))
    if date_from:
        q = q.filter(AuditEvent.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        q = q.filter(AuditEvent.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    events = q.order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "created_at", "action", "actor_user_email",
        "entity_type", "entity_id", "reason", "metadata_json",
        "client_ip", "request_id",
    ])
    for ev in events:
        writer.writerow([
            ev.id,
            ev.created_at.isoformat() if ev.created_at else "",
            ev.action,
            ev.actor_user_email or "",
            ev.entity_type or "",
            ev.entity_id or "",
            ev.reason or "",
            ev.metadata_json or "",
            ev.client_ip or "",
            ev.request_id or "",
        ])

    from app.eqms.audit import record_event
    record_event(
        s,
        actor=u,
        action="audit.export",
        entity_type="AuditEvent",
        entity_id=None,
        metadata={
            "filters": {
                "action": action_filter or None,
                "actor_email": actor_email or None,
                "date_from": str(date_from) if date_from else None,
                "date_to": str(date_to) if date_to else None,
            },
            "event_count": len(events),
        },
    )
    s.commit()

    today = date.today().isoformat()
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="audit_export_{today}.csv"'},
    )


def _auditor_portal_enabled() -> bool:
    v = (current_app.config.get("AUDITOR_PORTAL_ENABLED") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


@bp.get("/auditor-access-log")
@require_permission("auditor_portal.admin")
def auditor_access_log_list():
    from app.eqms.modules.auditor_portal.models import AuditorAccessEvent

    s = db_session()
    q = s.query(AuditorAccessEvent)

    email = (request.args.get("email") or "").strip()
    action = (request.args.get("action") or "").strip()
    path_q = (request.args.get("path") or "").strip()
    date_from = _parse_date(request.args.get("date_from") or "")
    date_to = _parse_date(request.args.get("date_to") or "")

    if email:
        q = q.filter(AuditorAccessEvent.user_email.ilike(f"%{email}%"))
    if action:
        q = q.filter(AuditorAccessEvent.action == action)
    if path_q:
        q = q.filter(AuditorAccessEvent.rel_path.ilike(f"%{path_q}%"))
    if date_from:
        q = q.filter(AuditorAccessEvent.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        q = q.filter(AuditorAccessEvent.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    try:
        page = max(1, int((request.args.get("page") or "1").strip()))
    except ValueError:
        page = 1
    per_page = 100
    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    offset = (page - 1) * per_page
    rows = q.order_by(AuditorAccessEvent.created_at.desc(), AuditorAccessEvent.id.desc()).offset(offset).limit(per_page).all()

    return render_template(
        "admin/auditor_access/list.html",
        rows=rows,
        email=email,
        action=action,
        path_q=path_q,
        date_from=(request.args.get("date_from") or "").strip(),
        date_to=(request.args.get("date_to") or "").strip(),
        page=page,
        pages=pages,
        total=total,
        portal_enabled=_auditor_portal_enabled(),
    )


@bp.get("/auditor-access-log/export")
@require_permission("auditor_portal.admin")
def auditor_access_log_export():
    from app.eqms.modules.auditor_portal.models import AuditorAccessEvent

    s = db_session()
    q = s.query(AuditorAccessEvent)

    email = (request.args.get("email") or "").strip()
    action = (request.args.get("action") or "").strip()
    path_q = (request.args.get("path") or "").strip()
    date_from = _parse_date(request.args.get("date_from") or "")
    date_to = _parse_date(request.args.get("date_to") or "")

    if email:
        q = q.filter(AuditorAccessEvent.user_email.ilike(f"%{email}%"))
    if action:
        q = q.filter(AuditorAccessEvent.action == action)
    if path_q:
        q = q.filter(AuditorAccessEvent.rel_path.ilike(f"%{path_q}%"))
    if date_from:
        q = q.filter(AuditorAccessEvent.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        q = q.filter(AuditorAccessEvent.created_at < datetime.combine(date_to + timedelta(days=1), time.min))

    rows = q.order_by(AuditorAccessEvent.created_at.asc(), AuditorAccessEvent.id.asc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "created_at", "user_email", "action", "rel_path", "file_size", "ip", "user_agent", "request_id"]
    )
    for ev in rows:
        writer.writerow(
            [
                ev.id,
                ev.created_at.isoformat() if ev.created_at else "",
                ev.user_email or "",
                ev.action,
                ev.rel_path,
                ev.file_size if ev.file_size is not None else "",
                ev.ip or "",
                ev.user_agent or "",
                ev.request_id or "",
            ]
        )

    today = date.today().isoformat()
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="auditor_access_{today}.csv"'},
    )


@bp.get("/debug/permissions")
@require_permission("admin.edit")
def debug_permissions():
    """Show current user's permissions for debugging permission issues."""
    if not _diagnostics_allowed():
        abort(404)
    user = getattr(g, "current_user", None)
    roles = []
    permissions = []
    
    if user:
        roles = list(user.roles or [])
        for role in roles:
            for perm in role.permissions or []:
                permissions.append({
                    "role": role.key,
                    "permission": perm.key,
                    "name": perm.name,
                })
    
    # Sort permissions by key for easy scanning
    permissions.sort(key=lambda p: p["permission"])
    
    return render_template("admin/debug_permissions.html", 
        user=user, 
        roles=roles, 
        permissions=permissions
    )


@bp.get("/diagnostics")
@require_permission("admin.edit")
def diagnostics():
    """System diagnostics page showing database connectivity, counts, and status."""
    if not _diagnostics_allowed():
        abort(404)
    import os
    from flask import current_app
    from sqlalchemy import text, func, or_
    
    s = db_session()
    diag = {
        "app_version": os.environ.get("APP_VERSION", "dev"),
        "port": os.environ.get("PORT", "8080"),
        "env": os.environ.get("ENV", "unknown"),
        "db_connected": False,
        "db_error": None,
        "counts": {},
        "last_shipstation_sync": None,
        "unmatched_distributions": 0,
        "pdf_dependencies": {
            "pdfplumber": False,
            "pdfplumber_version": None,
            "PyPDF2": False,
            "PyPDF2_version": None,
        },
        "shipstation_integrity": {},
    }
    
    # Check PDF dependencies
    try:
        import pdfplumber
        diag["pdf_dependencies"]["pdfplumber"] = True
        diag["pdf_dependencies"]["pdfplumber_version"] = getattr(pdfplumber, "__version__", "unknown")
    except ImportError:
        pass
    
    try:
        import PyPDF2
        diag["pdf_dependencies"]["PyPDF2"] = True
        diag["pdf_dependencies"]["PyPDF2_version"] = getattr(PyPDF2, "__version__", "unknown")
    except ImportError:
        pass
    
    # Test database connectivity
    try:
        s.execute(text("SELECT 1"))
        diag["db_connected"] = True
    except Exception as e:
        diag["db_error"] = str(e)
    
    # Get counts
    if diag["db_connected"]:
        try:
            from app.eqms.modules.customer_profiles.models import Customer
            from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
            from app.eqms.modules.shipstation_sync.models import ShipStationSyncRun
            
            diag["counts"]["customers"] = s.query(Customer).count()
            diag["counts"]["distributions"] = s.query(DistributionLogEntry).count()
            diag["counts"]["sales_orders"] = s.query(SalesOrder).count()
            diag["counts"]["unmatched_distributions"] = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.sales_order_id.is_(None))
                .count()
            )
            diag["unmatched_distributions"] = diag["counts"]["unmatched_distributions"]
            
            # Last ShipStation sync
            last_sync = (
                s.query(ShipStationSyncRun)
                .order_by(ShipStationSyncRun.ran_at.desc())
                .first()
            )
            if last_sync:
                diag["last_shipstation_sync"] = {
                    "ran_at": str(last_sync.ran_at),
                    "synced_count": last_sync.synced_count,
                    "skipped_count": last_sync.skipped_count,
                    "message": last_sync.message,
                }

            # ShipStation integrity diagnostics
            source_counts = (
                s.query(DistributionLogEntry.source, func.count(DistributionLogEntry.id))
                .group_by(DistributionLogEntry.source)
                .all()
            )
            diag["shipstation_integrity"]["distributions_by_source"] = {src: int(cnt) for src, cnt in source_counts}

            unknown_lots = (
                s.query(func.count(DistributionLogEntry.id))
                .filter(
                    DistributionLogEntry.source == "shipstation",
                    or_(
                        DistributionLogEntry.lot_number == "UNKNOWN",
                        DistributionLogEntry.lot_number.is_(None),
                    ),
                )
                .scalar() or 0
            )
            diag["shipstation_integrity"]["shipstation_unknown_lots"] = int(unknown_lots)

            multi_sku_orders = (
                s.query(
                    DistributionLogEntry.order_number,
                    func.count(func.distinct(DistributionLogEntry.sku)).label("sku_count"),
                    func.count(DistributionLogEntry.id).label("dist_count"),
                )
                .filter(
                    DistributionLogEntry.source == "shipstation",
                    DistributionLogEntry.sales_order_id.isnot(None),
                )
                .group_by(DistributionLogEntry.order_number)
                .having(func.count(func.distinct(DistributionLogEntry.sku)) > 1)
                .order_by(func.count(func.distinct(DistributionLogEntry.sku)).desc())
                .limit(10)
                .all()
            )
            diag["shipstation_integrity"]["multi_sku_orders"] = [
                {"order_number": o, "sku_count": int(sku_c), "dist_count": int(dist_c)}
                for o, sku_c, dist_c in multi_sku_orders
            ]

            blanket_orders = (
                s.query(
                    SalesOrder.order_number,
                    func.count(func.distinct(DistributionLogEntry.id)).label("dist_count"),
                    func.count(func.distinct(DistributionLogEntry.sku)).label("sku_count"),
                )
                .join(DistributionLogEntry, DistributionLogEntry.sales_order_id == SalesOrder.id)
                .group_by(SalesOrder.id, SalesOrder.order_number)
                .having(func.count(func.distinct(DistributionLogEntry.id)) > 1)
                .order_by(func.count(func.distinct(DistributionLogEntry.id)).desc())
                .limit(10)
                .all()
            )
            diag["shipstation_integrity"]["blanket_orders"] = [
                {"order_number": o, "dist_count": int(dist_c), "sku_count": int(sku_c)}
                for o, dist_c, sku_c in blanket_orders
            ]
        except Exception as e:
            diag["db_error"] = f"Count query failed: {e}"

    unmatched_preview = []
    if diag.get("db_connected") and diag.get("unmatched_distributions"):
        try:
            from app.eqms.modules.rep_traceability.models import DistributionLogEntry

            unmatched_preview = (
                s.query(DistributionLogEntry)
                .filter(DistributionLogEntry.sales_order_id.is_(None))
                .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
                .limit(8)
                .all()
            )
        except Exception:  # noqa: BLE001
            unmatched_preview = []

    return render_template(
        "admin/diagnostics.html",
        diag=diag,
        dashboard_stats=_dashboard_stats(),
        unmatched_preview=unmatched_preview,
    )


@bp.get("/diagnostics/unmatched-distributions")
@require_permission("distribution_log.view")
def unmatched_distributions():
    """Admin Tools workspace: distributions with no linked Sales Order."""
    if not _diagnostics_allowed():
        abort(404)
    s = db_session()
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry

    q = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.sales_order_id.is_(None))
        .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
    )
    total = q.count()
    entries = q.limit(200).all()
    return render_template(
        "admin/unmatched_distributions.html",
        entries=entries,
        total=total,
    )


@bp.post("/diagnostics/unmatched-distributions/<int:entry_id>/link")
@require_permission("distribution_log.edit")
def unmatched_distribution_link(entry_id: int):
    """Manually link an unmatched distribution to a Sales Order."""
    if not _diagnostics_allowed():
        abort(404)
    from app.eqms.audit import record_event
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
    from app.eqms.modules.rep_traceability.service import (
        find_sales_order_by_normalized_number,
        sync_distribution_customer_from_sales_order,
    )

    s = db_session()
    u = _current_user()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        abort(404)
    raw = (request.form.get("order_number") or "").strip()
    so = None
    if raw.isdigit():
        # Prefer order number match; fall back to numeric SO id
        so = find_sales_order_by_normalized_number(s, raw)
        if not so:
            so = s.get(SalesOrder, int(raw))
    else:
        so = find_sales_order_by_normalized_number(s, raw)
    if not so:
        flash(f"No Sales Order found for {raw!r}.", "danger")
        return redirect(url_for("admin.unmatched_distributions"))
    sync_distribution_customer_from_sales_order(entry, so)
    record_event(
        s, actor=u, action="distribution.link_sales_order",
        entity_type="DistributionLogEntry", entity_id=str(entry.id),
        metadata={"sales_order_id": so.id, "order_number": so.order_number},
    )
    from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type

    safe_apply_order_type(s, so, user=u)
    s.commit()
    flash(f"Linked distribution #{entry.id} to Sales Order {so.order_number}.", "success")
    return redirect(url_for("admin.unmatched_distributions"))


@bp.post("/diagnostics/unmatched-distributions/<int:entry_id>/clear")
@require_permission("distribution_log.edit")
def unmatched_distribution_clear(entry_id: int):
    """Clear sales_order_id on a distribution (manual unlink)."""
    if not _diagnostics_allowed():
        abort(404)
    from app.eqms.audit import record_event
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry

    s = db_session()
    u = _current_user()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        abort(404)
    prev_so_id = entry.sales_order_id
    entry.sales_order_id = None
    record_event(
        s, actor=u, action="distribution.clear_sales_order",
        entity_type="DistributionLogEntry", entity_id=str(entry.id),
        metadata={},
    )
    if prev_so_id:
        from app.eqms.modules.rep_traceability.order_type import safe_apply_order_type

        safe_apply_order_type(s, prev_so_id, user=u)
    s.commit()
    flash(f"Cleared Sales Order link on distribution #{entry.id}.", "success")
    return redirect(url_for("admin.unmatched_distributions"))


@bp.post("/diagnostics/unmatched-distributions/<int:entry_id>/delete")
@require_permission("distribution_log.delete")
def unmatched_distribution_delete(entry_id: int):
    """Delete an unmatched distribution from the Admin Tools workspace."""
    if not _diagnostics_allowed():
        abort(404)
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry
    from app.eqms.modules.rep_traceability.service import delete_distribution_entry

    s = db_session()
    u = _current_user()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        abort(404)
    reason = (request.form.get("reason") or "unmatched_workspace_delete").strip()
    delete_distribution_entry(s, entry, user=u, reason=reason)
    s.commit()
    flash(f"Deleted distribution #{entry_id}.", "success")
    return redirect(url_for("admin.unmatched_distributions"))


@bp.get("/diagnostics/storage")
@require_permission("admin.edit")
def diagnostics_storage():
    """Storage diagnostics (admin-only). Shows config status without exposing secrets."""
    if not _diagnostics_allowed():
        abort(404)
    from flask import current_app, jsonify
    from app.eqms.storage import storage_from_config, S3Storage, LocalStorage
    
    result = {
        "backend": current_app.config.get("STORAGE_BACKEND", "local"),
        "configured": False,
        "accessible": False,
        "error": None,
        "details": {},
    }
    
    storage = storage_from_config(current_app.config)
    
    if isinstance(storage, S3Storage):
        result["details"] = {
            "endpoint": storage.endpoint or "(default AWS)",
            "region": storage.region,
            "bucket": storage.bucket,
            "access_key_prefix": storage.access_key_id[:4] + "..." if storage.access_key_id else "(missing)",
        }
        result["configured"] = bool(storage.bucket and storage.access_key_id and storage.secret_access_key)
        
        if result["configured"]:
            try:
                storage._client().head_bucket(Bucket=storage.bucket)
                result["accessible"] = True
            except Exception as e:
                result["error"] = str(e)[:200]
    elif isinstance(storage, LocalStorage):
        result["details"] = {"root": str(storage.root)}
        result["configured"] = True
        result["accessible"] = storage.root.exists() or True  # Will create on first write
    
    return jsonify(result)


@bp.get("/maintenance/customers/duplicates")
@require_permission("admin.edit")
def maintenance_list_duplicates():
    """List potential duplicate customers (by company_key)."""
    from flask import jsonify
    from sqlalchemy import func
    from app.eqms.modules.customer_profiles.models import Customer
    
    s = db_session()
    
    # Find company_keys with duplicates
    duplicate_keys = (
        s.query(Customer.company_key, func.count(Customer.id).label("cnt"))
        .group_by(Customer.company_key)
        .having(func.count(Customer.id) > 1)
        .order_by(func.count(Customer.id).desc())
        .limit(50)
        .all()
    )
    
    result = []
    for company_key, count in duplicate_keys:
        customers = (
            s.query(Customer)
            .filter(Customer.company_key == company_key)
            .order_by(Customer.id)
            .all()
        )
        
        from app.eqms.modules.rep_traceability.models import SalesOrder
        customer_details = []
        for c in customers:
            order_count = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()
            customer_details.append({
                "id": c.id,
                "facility_name": c.facility_name,
                "city": c.city,
                "state": c.state,
                "order_count": order_count,
            })
        
        result.append({
            "company_key": company_key,
            "count": count,
            "customers": customer_details,
        })
    
    return jsonify({"duplicates": result, "total_groups": len(result)})


@bp.get("/maintenance/customers/zero-orders")
@require_permission("admin.edit")
def maintenance_list_zero_orders():
    """List customers with 0 matched sales orders (read-only)."""
    from flask import jsonify
    from sqlalchemy import func
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.customer_profiles.models import Customer
    
    s = db_session()
    
    # Customers with 0 sales orders
    order_count_subq = (
        s.query(SalesOrder.customer_id, func.count(SalesOrder.id).label("order_count"))
        .group_by(SalesOrder.customer_id)
        .subquery()
    )
    
    zero_order_customers = (
        s.query(Customer)
        .outerjoin(order_count_subq, Customer.id == order_count_subq.c.customer_id)
        .filter(
            (order_count_subq.c.order_count == None) | (order_count_subq.c.order_count == 0)
        )
        .order_by(Customer.facility_name)
        .limit(200)
        .all()
    )
    
    result = [
        {"id": c.id, "facility_name": c.facility_name, "company_key": c.company_key}
        for c in zero_order_customers
    ]
    
    return jsonify({"zero_order_customers": result, "count": len(result)})


@bp.post("/maintenance/customers/merge")
@require_permission("admin.edit")
def maintenance_merge_customers():
    """Merge duplicate customers. Requires master_id, duplicate_id, confirm_token."""
    import secrets as _sec
    from flask import jsonify
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
    from app.eqms.modules.rep_traceability.models import SalesOrder, DistributionLogEntry
    from app.eqms.audit import record_event
    
    data = request.get_json() or {}
    master_id = data.get("master_id")
    duplicate_id = data.get("duplicate_id")
    confirm_token = data.get("confirm_token")
    
    if not master_id or not duplicate_id:
        return jsonify({"error": "master_id and duplicate_id required"}), 400
    
    # F-016: Use a cryptographic random token stored in session (not predictable MD5)
    session_key = f"merge_token:{master_id}:{duplicate_id}"
    if not confirm_token:
        # First call — generate & return a token
        token = _sec.token_urlsafe(16)
        session[session_key] = token
        return jsonify({
            "error": "Confirmation required",
            "confirm_token": token,
            "message": f"To confirm merge, POST with confirm_token='{token}'"
        }), 400
    expected_token = session.pop(session_key, None)
    if not expected_token or confirm_token != expected_token:
        return jsonify({"error": "Invalid or expired confirmation token. Please try again."}), 400
    
    s = db_session()
    user = _current_user()
    
    master = s.query(Customer).filter(Customer.id == master_id).one_or_none()
    duplicate = s.query(Customer).filter(Customer.id == duplicate_id).one_or_none()
    
    if not master or not duplicate:
        return jsonify({"error": "Customer not found"}), 404
    
    if master_id == duplicate_id:
        return jsonify({"error": "Cannot merge customer into itself"}), 400
    
    try:
        # Update Sales Orders FK
        so_updated = (
            s.query(SalesOrder)
            .filter(SalesOrder.customer_id == duplicate_id)
            .update({"customer_id": master_id})
        )
        
        # Update Distributions FK
        dist_updated = (
            s.query(DistributionLogEntry)
            .filter(DistributionLogEntry.customer_id == duplicate_id)
            .update({"customer_id": master_id})
        )
        
        # Update Notes FK
        notes_updated = (
            s.query(CustomerNote)
            .filter(CustomerNote.customer_id == duplicate_id)
            .update({"customer_id": master_id})
        )
        
        # Audit event
        record_event(
            s,
            actor=user,
            action="customer.merge",
            entity_type="Customer",
            entity_id=str(master_id),
            metadata={
                "merged_customer_id": duplicate_id,
                "merged_facility_name": duplicate.facility_name,
                "so_updated": so_updated,
                "dist_updated": dist_updated,
                "notes_updated": notes_updated,
            },
        )
        
        # Delete duplicate customer
        s.delete(duplicate)
        s.commit()
        
        return jsonify({
            "success": True,
            "merged_into": {"id": master.id, "facility_name": master.facility_name},
            "updates": {
                "sales_orders": so_updated,
                "distributions": dist_updated,
                "notes": notes_updated,
            }
        })
    except Exception as e:
        s.rollback()
        return jsonify({"error": str(e)}), 500


@bp.post("/maintenance/customers/delete-zero-orders")
@require_permission("admin.edit")
def maintenance_delete_zero_orders():
    """Delete customers with 0 sales orders. Requires confirm=true in JSON body."""
    from flask import jsonify
    from sqlalchemy import func
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote, CustomerRep
    from app.eqms.modules.rep_traceability.models import SalesOrder, DistributionLogEntry
    from app.eqms.audit import record_event
    
    data = request.get_json() or {}
    if not data.get("confirm"):
        return jsonify({
            "error": "Confirmation required",
            "message": "POST with {\"confirm\": true} to delete zero-order customers"
        }), 400
    
    s = db_session()
    user = _current_user()
    
    # Find customers with 0 sales orders
    order_count_subq = (
        s.query(SalesOrder.customer_id, func.count(SalesOrder.id).label("order_count"))
        .group_by(SalesOrder.customer_id)
        .subquery()
    )
    
    zero_order_customers = (
        s.query(Customer)
        .outerjoin(order_count_subq, Customer.id == order_count_subq.c.customer_id)
        .filter(
            (order_count_subq.c.order_count == None) | (order_count_subq.c.order_count == 0)
        )
        .all()
    )
    
    if not zero_order_customers:
        return jsonify({"success": True, "deleted_count": 0, "message": "No zero-order customers found"})
    
    deleted_ids = []
    deleted_names = []
    
    try:
        for c in zero_order_customers:
            # Unlink distributions (set customer_id to NULL, don't delete)
            s.query(DistributionLogEntry).filter(DistributionLogEntry.customer_id == c.id).update({"customer_id": None})
            
            # Delete rep assignments
            s.query(CustomerRep).filter(CustomerRep.customer_id == c.id).delete()
            
            # Delete notes
            s.query(CustomerNote).filter(CustomerNote.customer_id == c.id).delete()
            
            # Record audit event
            record_event(
                s,
                actor=user,
                action="customer.delete_zero_orders",
                entity_type="Customer",
                entity_id=str(c.id),
                metadata={"facility_name": c.facility_name, "company_key": c.company_key},
            )
            
            deleted_ids.append(c.id)
            deleted_names.append(c.facility_name)
            
            # Delete customer
            s.delete(c)
        
        s.commit()
        
        return jsonify({
            "success": True,
            "deleted_count": len(deleted_ids),
            "deleted_ids": deleted_ids,
            "deleted_names": deleted_names[:20],  # Limit for response size
        })
    except Exception as e:
        s.rollback()
        return jsonify({"error": str(e)}), 500


@bp.get("/reset-data")
@require_permission("admin.edit")
def reset_data_get():
    """Show the reset data confirmation page."""
    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.rep_traceability.models import SalesOrder, DistributionLogEntry, OrderPdfAttachment

    s = db_session()
    counts = {
        "customers": s.query(Customer).count(),
        "distributions": s.query(DistributionLogEntry).count(),
        "sales_orders": s.query(SalesOrder).count(),
        "pdf_attachments": s.query(OrderPdfAttachment).count(),
    }
    return render_template("admin/reset_data.html", counts=counts, message=None, success=False, deleted=None)


@bp.post("/reset-data")
@require_permission("admin.edit")
def reset_data_post():
    """Handle the reset data form submission."""
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote, CustomerRep
    from app.eqms.modules.rep_traceability.models import (
        SalesOrder, SalesOrderLine, DistributionLogEntry, DistributionLine, OrderPdfAttachment,
        TracingReport, ApprovalEml
    )
    from app.eqms.modules.shipstation_sync.models import ShipStationSyncRun, ShipStationSkippedOrder
    from app.eqms.storage import storage_from_config
    
    confirm_phrase = (request.form.get("confirm_phrase") or "").strip()
    if confirm_phrase != "DELETE ALL DATA":
        flash("You must type 'DELETE ALL DATA' exactly to confirm.", "danger")
        return redirect(url_for("admin.reset_data_get"))
    
    dry_run = request.form.get("dry_run") == "true"
    reset_customers = request.form.get("reset_customers") == "1"
    reset_distributions = request.form.get("reset_distributions") == "1"
    reset_sales_orders = request.form.get("reset_sales_orders") == "1"
    reset_pdfs = request.form.get("reset_pdfs") == "1"
    reset_storage = request.form.get("reset_storage") == "1"
    reset_shipstation = request.form.get("reset_shipstation") == "1"
    
    s = db_session()
    user = _current_user()
    deleted = {}

    if dry_run:
        if reset_pdfs:
            deleted["pdf_attachments"] = s.query(OrderPdfAttachment).count()
        if reset_distributions:
            deleted["distribution_lines"] = s.query(DistributionLine).count()
            deleted["distributions"] = s.query(DistributionLogEntry).count()
        if reset_sales_orders:
            deleted["sales_order_lines"] = s.query(SalesOrderLine).count()
            deleted["sales_orders"] = s.query(SalesOrder).count()
        if reset_customers:
            deleted["customer_notes"] = s.query(CustomerNote).count()
            deleted["customer_reps"] = s.query(CustomerRep).count()
            deleted["customers"] = s.query(Customer).count()
        if reset_shipstation:
            deleted["shipstation_sync_runs"] = s.query(ShipStationSyncRun).count()
            deleted["shipstation_skipped"] = s.query(ShipStationSkippedOrder).count()

        return render_template(
            "admin/reset_data.html",
            counts=deleted,
            message="DRY RUN - No data deleted. Counts show what would be deleted.",
            success=True,
            deleted=deleted,
        )

    try:
        if reset_storage and reset_pdfs:
            storage = storage_from_config(current_app.config)
            attachments = s.query(OrderPdfAttachment).all()
            storage_deleted = 0
            for att in attachments:
                try:
                    storage.delete(att.storage_key)
                    storage_deleted += 1
                except Exception:
                    pass
            deleted["storage_files"] = storage_deleted

        if reset_pdfs:
            deleted["pdf_attachments"] = s.query(OrderPdfAttachment).delete()

        if reset_distributions:
            deleted["distribution_lines"] = s.query(DistributionLine).delete()
            deleted["distributions"] = s.query(DistributionLogEntry).delete()

        if reset_sales_orders:
            deleted["sales_order_lines"] = s.query(SalesOrderLine).delete()
            deleted["sales_orders"] = s.query(SalesOrder).delete()

        if reset_customers:
            deleted["customer_notes"] = s.query(CustomerNote).delete()
            deleted["customer_reps"] = s.query(CustomerRep).delete()
            deleted["customers"] = s.query(Customer).delete()
    
        if reset_shipstation:
            deleted["shipstation_skipped"] = s.query(ShipStationSkippedOrder).delete()
            deleted["shipstation_sync_runs"] = s.query(ShipStationSyncRun).delete()

        s.commit()

        from app.eqms.audit import record_event
        record_event(
            s,
            actor=user,
            action="maintenance.selective_reset",
            entity_type="System",
            entity_id="reset",
            metadata={"deleted": deleted},
        )
        s.commit()

        message = "Data reset completed successfully!"
        success = True
    except Exception as e:
        s.rollback()
        message = f"Reset failed: {str(e)}"
        success = False

    counts = {
        "customers": s.query(Customer).count(),
        "distributions": s.query(DistributionLogEntry).count(),
        "sales_orders": s.query(SalesOrder).count(),
        "pdf_attachments": s.query(OrderPdfAttachment).count(),
    }

    return render_template(
        "admin/reset_data.html",
        counts=counts,
        message=message,
        success=success,
        deleted=deleted,
    )


# ============================================================================
# ACCOUNT MANAGEMENT (Admin Only)
# ============================================================================

# Internal personas offered in account management (Prompt 6). `readonly` is
# retired; `auditor` backs the external auditor portal. `staff` is the default
# for a new non-admin team member.
ROLE_DESCRIPTIONS = {
    "admin": "Full access — manage documents, records, users, and settings.",
    "staff": "Full read-only access to the entire QMS (no create/edit/delete).",
    "auditor": "External auditor — limited access to the auditor portal only.",
}
_ASSIGNABLE_ROLE_ORDER = {"staff": 0, "admin": 1, "auditor": 2}


def _assignable_roles(s):
    """Roles an admin may assign, ordered (staff first as the team default)."""
    roles = [r for r in s.query(Role).all() if r.key in _ASSIGNABLE_ROLE_ORDER]
    roles.sort(key=lambda r: _ASSIGNABLE_ROLE_ORDER[r.key])
    return roles


@bp.get("/accounts")
@require_permission("admin.edit")
def accounts_list():
    s = db_session()
    users = s.query(User).order_by(User.email.asc()).all()
    roles = _assignable_roles(s)
    return render_template("admin/accounts/list.html", users=users, roles=roles,
                           role_descriptions=ROLE_DESCRIPTIONS)


@bp.get("/accounts/new")
@require_permission("admin.edit")
def accounts_new_get():
    s = db_session()
    roles = _assignable_roles(s)
    selected_role_id = next((r.id for r in roles if r.key == "staff"), None)
    return render_template("admin/accounts/new.html", roles=roles,
                           role_descriptions=ROLE_DESCRIPTIONS,
                           selected_role_id=selected_role_id)


@bp.post("/accounts/new")
@require_permission("admin.edit")
def accounts_new_post():
    from werkzeug.security import generate_password_hash
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()

    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    role_ids = request.form.getlist("role_ids")

    errors = []
    if not email:
        errors.append("Email is required.")
    elif not _is_valid_email(email):
        errors.append("Invalid email format.")
    else:
        existing = s.query(User).filter(User.email == email).one_or_none()
        if existing:
            errors.append("An account with this email already exists.")

    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif password != password_confirm:
        errors.append("Passwords do not match.")

    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("admin.accounts_new_get"))

    new_user = User(
        email=email,
        password_hash=generate_password_hash(password),
        is_active=True,
    )
    s.add(new_user)
    s.flush()

    if role_ids:
        roles = s.query(Role).filter(Role.id.in_([int(r) for r in role_ids])).all()
        for role in roles:
            if role not in new_user.roles:
                new_user.roles.append(role)

    record_event(
        s,
        actor=u,
        action="user.create",
        entity_type="User",
        entity_id=str(new_user.id),
        metadata={"email": email, "roles": [r.key for r in new_user.roles]},
    )
    s.commit()
    flash(f"Account created for {email}.", "success")
    return redirect(url_for("admin.accounts_list"))


@bp.get("/accounts/<int:user_id>")
@require_permission("admin.edit")
def accounts_detail(user_id: int):
    s = db_session()
    user = s.get(User, user_id)
    if not user:
        abort(404)
    roles = _assignable_roles(s)
    current = next((r for r in user.roles if r.key in _ASSIGNABLE_ROLE_ORDER), None)
    selected_role_id = current.id if current else next((r.id for r in roles if r.key == "staff"), None)
    return render_template("admin/accounts/detail.html", account=user, roles=roles,
                           role_descriptions=ROLE_DESCRIPTIONS,
                           selected_role_id=selected_role_id)


@bp.post("/accounts/<int:user_id>/update")
@require_permission("admin.edit")
def accounts_update(user_id: int):
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()
    user = s.get(User, user_id)
    if not user:
        abort(404)

    if user.id == u.id:
        flash("You cannot modify your own account from this page.", "danger")
        return redirect(url_for("admin.accounts_detail", user_id=user_id))

    before = {
        "is_active": user.is_active,
        "roles": [r.key for r in user.roles],
    }

    is_active = request.form.get("is_active") == "1"
    user.is_active = is_active

    role_ids = request.form.getlist("role_ids")
    user.roles.clear()
    if role_ids:
        roles = s.query(Role).filter(Role.id.in_([int(r) for r in role_ids])).all()
        for role in roles:
            user.roles.append(role)

    after = {
        "is_active": user.is_active,
        "roles": [r.key for r in user.roles],
    }

    record_event(
        s,
        actor=u,
        action="user.update",
        entity_type="User",
        entity_id=str(user.id),
        metadata={"before": before, "after": after},
    )
    s.commit()
    flash(f"Account updated for {user.email}.", "success")
    return redirect(url_for("admin.accounts_detail", user_id=user_id))


@bp.post("/accounts/<int:user_id>/reset-password")
@require_permission("admin.edit")
def accounts_reset_password(user_id: int):
    from werkzeug.security import generate_password_hash
    from app.eqms.audit import record_event

    s = db_session()
    u = _current_user()
    user = s.get(User, user_id)
    if not user:
        abort(404)

    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""

    errors = []
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif password != password_confirm:
        errors.append("Passwords do not match.")

    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("admin.accounts_detail", user_id=user_id))

    user.password_hash = generate_password_hash(password)

    record_event(
        s,
        actor=u,
        action="user.password_reset",
        entity_type="User",
        entity_id=str(user.id),
        metadata={"target_email": user.email, "reset_by": u.email},
    )
    s.commit()
    flash(f"Password reset for {user.email}.", "success")
    return redirect(url_for("admin.accounts_detail", user_id=user_id))


@bp.get("/upload-lotlog")
@require_permission("admin.edit")
def upload_lotlog_get():
    """Show the LotLog upload form."""
    from flask import current_app
    from app.eqms.storage import storage_from_config

    storage = storage_from_config(current_app.config)
    lotlog_exists = storage.exists("data/LotLog.csv")
    lotlog_size = None
    if lotlog_exists:
        try:
            data = storage.get_bytes("data/LotLog.csv")
            lotlog_size = len(data)
        except Exception:
            pass

    return render_template(
        "admin/upload_lotlog.html",
        lotlog_exists=lotlog_exists,
        lotlog_size=lotlog_size,
    )


@bp.post("/upload-lotlog")
@require_permission("admin.edit")
def upload_lotlog_post():
    """Upload LotLog.csv to storage backend."""
    from flask import current_app
    from app.eqms.storage import storage_from_config
    from app.eqms.audit import record_event

    s = db_session()
    user = _current_user()

    f = request.files.get("lotlog_file")
    if not f or not f.filename:
        flash("Please select a CSV file to upload.", "danger")
        return redirect(url_for("admin.upload_lotlog_get"))

    file_bytes = f.read()
    if not file_bytes:
        flash("File is empty.", "danger")
        return redirect(url_for("admin.upload_lotlog_get"))

    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        flash("LotLog file too large (max 10MB).", "danger")
        return redirect(url_for("admin.upload_lotlog_get"))

    # Validate CSV structure
    import csv
    import io
    try:
        text = file_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        if "Lot" not in headers or "SKU" not in headers:
            flash(f"Invalid CSV: requires 'Lot' and 'SKU' columns. Found: {', '.join(headers[:10])}", "danger")
            return redirect(url_for("admin.upload_lotlog_get"))
        row_count = sum(1 for _ in reader)
    except Exception as e:
        flash(f"Failed to parse CSV: {e}", "danger")
        return redirect(url_for("admin.upload_lotlog_get"))

    storage = storage_from_config(current_app.config)
    storage.put_bytes("data/LotLog.csv", file_bytes, content_type="text/csv")

    record_event(
        s,
        actor=user,
        action="admin.upload_lotlog",
        entity_type="System",
        entity_id="LotLog.csv",
        metadata={"size_bytes": len(file_bytes), "rows": row_count},
    )
    s.commit()

    flash(f"LotLog.csv uploaded successfully ({row_count} rows, {len(file_bytes):,} bytes). Sales Dashboard inventory will reflect the new data automatically.", "success")
    return redirect(url_for("admin.upload_lotlog_get"))


@bp.get("/upload-disposition-log")
@require_permission("admin.edit")
def upload_disposition_log_get():
    """Upload DispositionLog.xlsx for Sales Dashboard lot inventory adjustments."""
    from flask import current_app
    from app.eqms.storage import storage_from_config

    storage = storage_from_config(current_app.config)
    disposition_exists = storage.exists("data/DispositionLog.xlsx")
    disposition_size = None
    if disposition_exists:
        try:
            disposition_size = len(storage.get_bytes("data/DispositionLog.xlsx"))
        except Exception:
            pass

    return render_template(
        "admin/upload_disposition_log.html",
        disposition_exists=disposition_exists,
        disposition_size=disposition_size,
    )


@bp.post("/upload-disposition-log")
@require_permission("admin.edit")
def upload_disposition_log_post():
    """Upload DispositionLog.xlsx to storage backend."""
    from flask import current_app
    from app.eqms.storage import storage_from_config
    from app.eqms.audit import record_event
    from app.eqms.modules.shipstation_sync.parsers import parse_disposition_log_bytes

    s = db_session()
    user = _current_user()

    f = request.files.get("disposition_file")
    if not f or not f.filename:
        flash("Please select an Excel file to upload.", "danger")
        return redirect(url_for("admin.upload_disposition_log_get"))

    file_bytes = f.read()
    if not file_bytes:
        flash("File is empty.", "danger")
        return redirect(url_for("admin.upload_disposition_log_get"))

    if len(file_bytes) > 10 * 1024 * 1024:
        flash("Disposition log file too large (max 10MB).", "danger")
        return redirect(url_for("admin.upload_disposition_log_get"))

    if not (f.filename or "").lower().endswith(".xlsx"):
        flash("Invalid file type. Upload a .xlsx Disposition Log workbook.", "danger")
        return redirect(url_for("admin.upload_disposition_log_get"))

    try:
        totals = parse_disposition_log_bytes(file_bytes)
    except Exception as e:
        flash(f"Failed to parse Disposition Log: {e}", "danger")
        return redirect(url_for("admin.upload_disposition_log_get"))

    if not totals:
        flash(
            "No disposition rows found. Expected columns: Date, Lot, SKU, Number of Units Dispositioned.",
            "danger",
        )
        return redirect(url_for("admin.upload_disposition_log_get"))

    storage = storage_from_config(current_app.config)
    storage.put_bytes(
        "data/DispositionLog.xlsx",
        file_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    record_event(
        s,
        actor=user,
        action="admin.upload_disposition_log",
        entity_type="System",
        entity_id="DispositionLog.xlsx",
        metadata={"size_bytes": len(file_bytes), "lots": len(totals), "units": sum(totals.values())},
    )
    s.commit()

    flash(
        f"Disposition Log uploaded ({len(totals)} lots, {sum(totals.values())} units removed). "
        "Sales Dashboard lot inventory will update automatically.",
        "success",
    )
    return redirect(url_for("admin.upload_disposition_log_get"))


def _is_valid_email(email: str) -> bool:
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


