from datetime import date, datetime, time, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.eqms.db import db_session
from app.eqms.models import AuditEvent, User, Role
from app.eqms.rbac import require_permission

bp = Blueprint("admin", __name__)


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


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
    import os
    from sqlalchemy import text

    s = db_session()
    status = {
        "env": (os.environ.get("ENV") or "development").strip().lower(),
        "db_connected": False,
        "db_error": None,
        "storage_backend": None,
        "storage_configured": False,
        "storage_error": None,
        "shipstation_ready": False,
        "shipstation_error": None,
        "last_shipstation_sync": None,
    }

    # DB connectivity (lightweight)
    try:
        s.execute(text("SELECT 1"))
        status["db_connected"] = True
    except Exception as e:
        status["db_error"] = str(e)

    # Storage config (no network calls)
    storage_backend = os.environ.get("STORAGE_BACKEND", "local").strip().lower()
    status["storage_backend"] = storage_backend or "local"
    if storage_backend == "s3":
        missing = []
        for key in ("S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
            if not os.environ.get(key):
                missing.append(key)
        status["storage_configured"] = not missing
        if missing:
            status["storage_error"] = f"Missing: {', '.join(missing)}"
    else:
        status["storage_configured"] = True

    # ShipStation credentials + last sync
    api_key = (os.environ.get("SHIPSTATION_API_KEY") or "").strip()
    api_secret = (os.environ.get("SHIPSTATION_API_SECRET") or "").strip()
    status["shipstation_ready"] = bool(api_key and api_secret)
    if not status["shipstation_ready"]:
        status["shipstation_error"] = "Missing API credentials"
    try:
        from app.eqms.modules.shipstation_sync.models import ShipStationSyncRun

        last_sync = (
            s.query(ShipStationSyncRun)
            .order_by(ShipStationSyncRun.ran_at.desc(), ShipStationSyncRun.id.desc())
            .first()
        )
        if last_sync:
            status["last_shipstation_sync"] = {
                "ran_at": str(last_sync.ran_at),
                "synced": last_sync.synced_count,
                "skipped": last_sync.skipped_count,
            }
    except Exception:
        pass

    return render_template("admin/index.html", system_status=status, diagnostics_allowed=_diagnostics_allowed())


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
@require_permission("admin.view")
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

    events = q.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(200).all()
    return render_template(
        "admin/audit/list.html",
        events=events,
        action=action,
        actor_email=actor_email,
        date_from=(request.args.get("date_from") or "").strip(),
        date_to=(request.args.get("date_to") or "").strip(),
    )


@bp.get("/debug/permissions")
@require_permission("admin.view")
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
@require_permission("admin.view")
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
    
    return render_template("admin/diagnostics.html", diag=diag)


@bp.get("/diagnostics/storage")
@require_permission("admin.view")
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
@require_permission("admin.view")
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
@require_permission("admin.view")
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
    from flask import jsonify
    import hashlib
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
    from app.eqms.modules.rep_traceability.models import SalesOrder, DistributionLogEntry
    from app.eqms.audit import record_event
    
    data = request.get_json() or {}
    master_id = data.get("master_id")
    duplicate_id = data.get("duplicate_id")
    confirm_token = data.get("confirm_token")
    
    if not master_id or not duplicate_id:
        return jsonify({"error": "master_id and duplicate_id required"}), 400
    
    # Require confirmation token = md5(master_id:duplicate_id:CONFIRM)
    expected_token = hashlib.md5(f"{master_id}:{duplicate_id}:CONFIRM".encode()).hexdigest()[:8]
    if confirm_token != expected_token:
        return jsonify({
            "error": "Confirmation required",
            "confirm_token": expected_token,
            "message": f"To confirm merge, POST with confirm_token='{expected_token}'"
        }), 400
    
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
    return render_template("admin/reset_data.html", message=None, success=False, deleted=None)


@bp.post("/reset-data")
@require_permission("admin.edit")
def reset_data_post():
    """Handle the reset data form submission."""
    from sqlalchemy import text
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote, CustomerRep
    from app.eqms.modules.rep_traceability.models import (
        SalesOrder, SalesOrderLine, DistributionLogEntry, OrderPdfAttachment,
        TracingReport, ApprovalEml
    )
    from app.eqms.modules.shipstation_sync.models import ShipStationSyncRun, ShipStationSkippedOrder
    
    confirm_phrase = (request.form.get("confirm_phrase") or "").strip()
    if confirm_phrase != "DELETE ALL DATA":
        flash("You must type 'DELETE ALL DATA' exactly to confirm.", "danger")
        return redirect(url_for("admin.reset_data_get"))
    
    s = db_session()
    user = _current_user()

    counts_before = {
        "customers": s.query(Customer).count(),
        "distributions": s.query(DistributionLogEntry).count(),
        "sales_orders": s.query(SalesOrder).count(),
        "sales_order_lines": s.query(SalesOrderLine).count(),
        "pdf_attachments": s.query(OrderPdfAttachment).count(),
        "customer_notes": s.query(CustomerNote).count(),
        "customer_reps": s.query(CustomerRep).count(),
        "tracing_reports": s.query(TracingReport).count(),
        "approval_emls": s.query(ApprovalEml).count(),
        "shipstation_sync_runs": s.query(ShipStationSyncRun).count(),
        "shipstation_skipped": s.query(ShipStationSkippedOrder).count(),
    }

    if (request.form.get("dry_run") or "").lower() == "true":
        message = "Dry run only. No data deleted."
        return render_template("admin/reset_data.html", message=message, success=True, deleted=counts_before)
    
    def _reset_all_data_sql():
        deleted_counts = {}
        errors = []

        # Prefer TRUNCATE ... CASCADE for Postgres to avoid FK violations.
        if s.bind and s.bind.dialect.name == "postgresql":
            tables = [
                "approvals_eml",
                "order_pdf_attachments",
                "sales_order_lines",
                "distribution_log_entries",
                "sales_orders",
                "customer_notes",
                "customer_reps",
                "customers",
                "tracing_reports",
                "shipstation_skipped_orders",
                "shipstation_sync_runs",
                "devices_distributed",
            ]
            try:
                s.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
                s.commit()
                for t in tables:
                    deleted_counts[t] = -1  # -1 indicates TRUNCATE (count not available)
                return deleted_counts, errors
            except Exception as e:
                s.rollback()
                errors.append(f"truncate: {str(e)[:120]}")

        # Fallback: DELETE in FK-safe order (non-Postgres)
        delete_statements = [
            "DELETE FROM approvals_eml",
            "DELETE FROM order_pdf_attachments",
            "DELETE FROM sales_order_lines",
            "DELETE FROM distribution_log_entries",
            "DELETE FROM sales_orders",
            "DELETE FROM customer_notes",
            "DELETE FROM customer_reps",
            "DELETE FROM customers",
            "DELETE FROM tracing_reports",
            "DELETE FROM shipstation_skipped_orders",
            "DELETE FROM shipstation_sync_runs",
            "DELETE FROM devices_distributed",
        ]

        for stmt in delete_statements:
            table_name = stmt.replace("DELETE FROM ", "")
            try:
                result = s.execute(text(stmt))
                deleted_counts[table_name] = result.rowcount
                s.commit()
            except Exception as e:
                s.rollback()
                if "does not exist" in str(e) or "doesn't exist" in str(e):
                    deleted_counts[table_name] = 0
                else:
                    errors.append(f"{table_name}: {str(e)[:100]}")
        return deleted_counts, errors

    deleted_counts, errors = _reset_all_data_sql()
    
    if errors:
        message = f"Reset completed with errors: {'; '.join(errors)}"
        success = False
    else:
        message = "All data has been successfully reset!"
        success = True
        # Record audit event
        from app.eqms.audit import record_event
        try:
            record_event(
                s,
                actor=user,
                action="maintenance.reset_all_data",
                entity_type="System",
                entity_id="reset",
                metadata={"counts_deleted": deleted_counts},
            )
            s.commit()
        except Exception:
            pass  # Audit failure shouldn't block success message
    
    return render_template("admin/reset_data.html", message=message, success=success, deleted=deleted_counts)


@bp.get("/maintenance/reset-all-data")
@require_permission("admin.edit")
def maintenance_reset_all_data_get():
    """Redirect to the reset confirmation page (browser-friendly)."""
    return redirect(url_for("admin.reset_data_get"))


@bp.post("/maintenance/reset-all-data")
@require_permission("admin.edit")
def maintenance_reset_all_data():
    """
    NUCLEAR OPTION: Delete ALL customers, distributions, sales orders.
    Use this to start fresh. Requires confirm=true and confirm_phrase="DELETE ALL DATA".
    """
    from flask import jsonify

    if request.is_json:
        return jsonify({
            "error": "Reset endpoint consolidated",
            "message": "Use /admin/reset-data to reset the system.",
        }), 410

    flash("Reset endpoint consolidated. Use the Reset Data page.", "warning")
    return redirect(url_for("admin.reset_data_get"))


@bp.get("/login")
def login_redirect():
    return redirect(url_for("auth.login_get"))


# ============================================================================
# ACCOUNT MANAGEMENT (Admin Only)
# ============================================================================

@bp.get("/accounts")
@require_permission("admin.edit")
def accounts_list():
    s = db_session()
    users = s.query(User).order_by(User.email.asc()).all()
    roles = s.query(Role).order_by(Role.name.asc()).all()
    return render_template("admin/accounts/list.html", users=users, roles=roles)


@bp.get("/accounts/new")
@require_permission("admin.edit")
def accounts_new_get():
    s = db_session()
    roles = s.query(Role).order_by(Role.name.asc()).all()
    return render_template("admin/accounts/new.html", roles=roles)


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
    roles = s.query(Role).order_by(Role.name.asc()).all()
    return render_template("admin/accounts/detail.html", account=user, roles=roles)


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


def _is_valid_email(email: str) -> bool:
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

