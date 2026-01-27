from datetime import date, datetime, time, timedelta

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.eqms.db import db_session
from app.eqms.models import AuditEvent, User
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


@bp.get("/")
@require_permission("admin.view")
def index():
    return render_template("admin/index.html")


@bp.get("/modules/<module_key>")
@require_permission("admin.view")
def module_stub(module_key: str):
    # Minimal scaffold route; real module pages will be built in the new eQMS repo.
    return render_template("admin/module_stub.html", module_key=module_key)


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
    import os
    from flask import current_app
    from sqlalchemy import text
    
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
        except Exception as e:
            diag["db_error"] = f"Count query failed: {e}"
    
    return render_template("admin/diagnostics.html", diag=diag)


@bp.get("/diagnostics/storage")
@require_permission("admin.view")
def diagnostics_storage():
    """Storage diagnostics (admin-only). Shows config status without exposing secrets."""
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


@bp.post("/maintenance/reset-all-data")
@require_permission("admin.edit")
def maintenance_reset_all_data():
    """
    NUCLEAR OPTION: Delete ALL customers, distributions, sales orders.
    Use this to start fresh. Requires confirm=true and confirm_phrase="DELETE ALL DATA".
    """
    from flask import jsonify
    from sqlalchemy import text
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote, CustomerRep
    from app.eqms.modules.rep_traceability.models import (
        SalesOrder, SalesOrderLine, DistributionLogEntry, OrderPdfAttachment,
        TracingReport, ApprovalEml
    )
    from app.eqms.modules.shipstation_sync.models import ShipStationSyncRun, ShipStationSkippedOrder
    from app.eqms.audit import record_event
    
    data = request.get_json() or {}
    if not data.get("confirm") or data.get("confirm_phrase") != "DELETE ALL DATA":
        return jsonify({
            "error": "Confirmation required",
            "message": 'POST with {"confirm": true, "confirm_phrase": "DELETE ALL DATA", "csrf_token": "..."} to reset all data'
        }), 400
    
    s = db_session()
    user = _current_user()
    
    try:
        # Count before deletion
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
        
        # Use synchronize_session=False for PostgreSQL compatibility
        # Delete in strict FK order (children first, parents last)
        
        # 0. Legacy tables that may exist in production but not in codebase
        # These are cleaned up via raw SQL to handle unknown schemas
        legacy_tables = [
            "devices_distributed",  # Old legacy table with FK to customers
        ]
        for table_name in legacy_tables:
            try:
                s.execute(text(f"DELETE FROM {table_name}"))
            except Exception:
                pass  # Table may not exist, that's fine
        
        # 1. Approval EMls (FK to tracing_reports)
        s.query(ApprovalEml).delete(synchronize_session=False)
        
        # 2. Tracing Reports (FK to users only, not to our data)
        s.query(TracingReport).delete(synchronize_session=False)
        
        # 3. PDF attachments (FK to sales_orders, distribution_log_entries)
        s.query(OrderPdfAttachment).delete(synchronize_session=False)
        
        # 4. Sales order lines (FK to sales_orders)
        s.query(SalesOrderLine).delete(synchronize_session=False)
        
        # 5. Distribution log entries (FK to sales_orders, customers)
        # Must be before sales_orders and customers
        s.query(DistributionLogEntry).delete(synchronize_session=False)
        
        # 6. Sales orders (FK to customers - this is the key one!)
        # Must be BEFORE customers because of RESTRICT constraint
        s.query(SalesOrder).delete(synchronize_session=False)
        
        # 7. Customer notes (FK to customers)
        s.query(CustomerNote).delete(synchronize_session=False)
        
        # 8. Customer reps (FK to customers)
        s.query(CustomerRep).delete(synchronize_session=False)
        
        # 9. Customers (all FKs pointing to it should now be gone)
        s.query(Customer).delete(synchronize_session=False)
        
        # 10. ShipStation sync data (optional, for clean slate)
        s.query(ShipStationSkippedOrder).delete(synchronize_session=False)
        s.query(ShipStationSyncRun).delete(synchronize_session=False)
        
        # Flush to ensure all deletes are sent to DB
        s.flush()
        
        # Audit event
        record_event(
            s,
            actor=user,
            action="maintenance.reset_all_data",
            entity_type="System",
            entity_id="reset",
            metadata={"counts_deleted": counts_before},
        )
        
        s.commit()
        
        return jsonify({
            "success": True,
            "message": "All data has been reset",
            "deleted": counts_before,
        })
    except Exception as e:
        s.rollback()
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@bp.get("/login")
def login_redirect():
    return redirect(url_for("auth.login_get"))

