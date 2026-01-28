from __future__ import annotations

import json
import os

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from sqlalchemy import func

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.rep_traceability.models import DistributionLogEntry
from app.eqms.modules.shipstation_sync.models import ShipStationSkippedOrder, ShipStationSyncRun
from app.eqms.modules.shipstation_sync.service import run_sync
from app.eqms.modules.shipstation_sync.parsers import canonicalize_sku, load_lot_log
from app.eqms.rbac import require_permission

bp = Blueprint("shipstation_sync", __name__)


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


def _get_distribution_diagnostics(s) -> dict:
    """Lean diagnostics for distribution_log_entries."""
    total = s.query(func.count(DistributionLogEntry.id)).scalar() or 0
    by_source = (
        s.query(DistributionLogEntry.source, func.count(DistributionLogEntry.id))
        .group_by(DistributionLogEntry.source)
        .all()
    )
    date_range = s.query(func.min(DistributionLogEntry.ship_date), func.max(DistributionLogEntry.ship_date)).one()
    
    # ShipStation-specific stats
    ss_date_range = (
        s.query(func.min(DistributionLogEntry.ship_date), func.max(DistributionLogEntry.ship_date))
        .filter(DistributionLogEntry.source == "shipstation")
        .one()
    )
    ss_count = (
        s.query(func.count(DistributionLogEntry.id))
        .filter(DistributionLogEntry.source == "shipstation")
        .scalar() or 0
    )
    return {
        "total": total,
        "by_source": {src: cnt for src, cnt in by_source},
        "min_ship_date": date_range[0],
        "max_ship_date": date_range[1],
        "ss_min_ship_date": ss_date_range[0],
        "ss_max_ship_date": ss_date_range[1],
        "ss_count": ss_count,
    }


def _get_top_skip_reasons(s, limit: int = 10) -> list[tuple[str, int]]:
    """Get top skipped reasons by count."""
    rows = (
        s.query(ShipStationSkippedOrder.reason, func.count(ShipStationSkippedOrder.id))
        .group_by(ShipStationSkippedOrder.reason)
        .order_by(func.count(ShipStationSkippedOrder.id).desc())
        .limit(limit)
        .all()
    )
    return [(reason, cnt) for reason, cnt in rows]


def _get_sync_config() -> dict:
    """Get current sync configuration from environment."""
    since_date = (os.environ.get("SHIPSTATION_SINCE_DATE") or "").strip()
    if not since_date:
        # Dynamic default: start of current year (P3-2 improvement)
        from datetime import date
        current_year = date.today().year
        since_date = f"{current_year}-01-01"
    max_pages = int((os.environ.get("SHIPSTATION_MAX_PAGES") or "50").strip() or "50")
    max_orders = int((os.environ.get("SHIPSTATION_MAX_ORDERS") or "500").strip() or "500")
    return {
        "since_date": since_date,
        "max_pages": max_pages,
        "max_orders": max_orders,
        "api_key_set": bool((os.environ.get("SHIPSTATION_API_KEY") or "").strip()),
        "api_secret_set": bool((os.environ.get("SHIPSTATION_API_SECRET") or "").strip()),
    }


@bp.get("/shipstation")
@require_permission("shipstation.view")
def shipstation_index():
    s = db_session()
    runs = s.query(ShipStationSyncRun).order_by(ShipStationSyncRun.ran_at.desc(), ShipStationSyncRun.id.desc()).limit(20).all()
    skipped = (
        s.query(ShipStationSkippedOrder)
        .order_by(ShipStationSkippedOrder.created_at.desc(), ShipStationSkippedOrder.id.desc())
        .limit(50)
        .all()
    )
    # Lean diagnostics
    diag = _get_distribution_diagnostics(s)
    sync_run_count = s.query(func.count(ShipStationSyncRun.id)).scalar() or 0
    skipped_count = s.query(func.count(ShipStationSkippedOrder.id)).scalar() or 0
    top_skip_reasons = _get_top_skip_reasons(s)
    sync_config = _get_sync_config()
    
    # Check if last run hit limits
    last_run = runs[0] if runs else None
    limit_warning = last_run and "LIMIT REACHED" in (last_run.message or "")
    
    return render_template(
        "admin/shipstation/index.html",
        runs=runs,
        skipped=skipped,
        diag=diag,
        sync_run_count=sync_run_count,
        skipped_count=skipped_count,
        top_skip_reasons=top_skip_reasons,
        sync_config=sync_config,
        limit_warning=limit_warning,
    )


@bp.post("/shipstation/run")
@require_permission("shipstation.run")
def shipstation_run():
    from datetime import date
    from calendar import monthrange
    
    s = db_session()
    u = _current_user()
    
    # Check for month parameter (YYYY-MM format)
    month_str = (request.form.get("month") or "").strip()
    start_date = None
    end_date = None
    
    if month_str:
        try:
            parts = month_str.split("-")
            year = int(parts[0])
            month = int(parts[1])
            start_date = date(year, month, 1)
            # Last day of month
            _, last_day = monthrange(year, month)
            end_date = date(year, month, last_day)
        except (ValueError, IndexError):
            flash(f"Invalid month format: {month_str}. Use YYYY-MM.", "danger")
            return redirect(url_for("shipstation_sync.shipstation_index"))
    
    try:
        run = run_sync(s, user=u, start_date=start_date, end_date=end_date)
        s.commit()
        if month_str:
            flash(f"ShipStation sync completed for {month_str}. Synced={run.synced_count} skipped={run.skipped_count}.", "success")
        else:
            flash(f"ShipStation sync completed. Synced={run.synced_count} skipped={run.skipped_count}.", "success")
    except Exception as e:
        s.rollback()
        flash(f"ShipStation sync failed: {e}", "danger")
    return redirect(url_for("shipstation_sync.shipstation_index"))


@bp.get("/shipstation/diag")
@require_permission("shipstation.view")
def shipstation_diag():
    """Diagnostic: show raw ShipStation data and parsing results without syncing."""
    # Disable in production unless SHIPSTATION_DIAG_ENABLED=1
    env = os.environ.get("ENV", "development").lower()
    diag_enabled = os.environ.get("SHIPSTATION_DIAG_ENABLED", "").strip() == "1"
    if env == "production" and not diag_enabled:
        flash("Diagnostics disabled in production. Set SHIPSTATION_DIAG_ENABLED=1 to enable.", "danger")
        return redirect(url_for("shipstation_sync.shipstation_index"))
    
    from datetime import datetime, timezone, timedelta
    from app.eqms.modules.shipstation_sync.shipstation_client import ShipStationClient
    from app.eqms.modules.shipstation_sync.parsers import extract_lot, normalize_lot, infer_units
    
    api_key = (os.environ.get("SHIPSTATION_API_KEY") or "").strip()
    api_secret = (os.environ.get("SHIPSTATION_API_SECRET") or "").strip()
    from pathlib import Path

    lotlog_env = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "").strip()
    if lotlog_env:
        lotlog_path = lotlog_env
    else:
        project_root = Path(__file__).resolve().parents[4]
        lotlog_path = str(project_root / "app" / "eqms" / "data" / "LotLog.csv")
    
    diag_info = {
        "api_key_set": bool(api_key),
        "api_secret_set": bool(api_secret),
        "lotlog_path": lotlog_path,
        "lotlog_exists": os.path.exists(lotlog_path.replace("\\", "/")),
        "lotlog_loaded": False,
        "orders": [],
        "lot_to_sku_sample": {},
        "error": None,
    }
    
    # Load LotLog sample
    try:
        lot_to_sku, lot_corrections = load_lot_log(lotlog_path)
        diag_info["lot_to_sku_count"] = len(lot_to_sku)
        diag_info["lot_corrections_count"] = len(lot_corrections)
        diag_info["lotlog_loaded"] = bool(lot_to_sku)
        # Show first 10 entries
        diag_info["lot_to_sku_sample"] = dict(list(lot_to_sku.items())[:10])
    except Exception as e:
        diag_info["lotlog_error"] = str(e)
    
    if not api_key or not api_secret:
        diag_info["error"] = "SHIPSTATION_API_KEY or SHIPSTATION_API_SECRET not set"
        return render_template("admin/shipstation/diag.html", diag=diag_info)
    
    try:
        client = ShipStationClient(api_key=api_key, api_secret=api_secret)
        now = datetime.now(timezone.utc)
        start_dt = now - timedelta(days=30)
        
        orders = client.list_orders(
            create_date_start=start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            create_date_end=now.strftime("%Y-%m-%dT%H:%M:%S"),
            page=1,
            page_size=10,
        )
        
        for o in orders[:5]:
            order_id = str(o.get("orderId") or "")
            order_number = (o.get("orderNumber") or "").strip()
            
            det = client.get_order(order_id) if order_id else {}
            items = det.get("items") if isinstance(det.get("items"), list) else []
            internal_notes = (det.get("internalNotes") or "").strip()
            
            parsed_items = []
            for it in items:
                raw_sku = (it.get("sku") or "").strip()
                raw_name = (it.get("name") or "").strip()
                canonical = canonicalize_sku(raw_sku or raw_name)
                parsed_items.append({
                    "raw_sku": raw_sku,
                    "raw_name": raw_name[:50],
                    "canonical_sku": canonical,
                    "quantity": it.get("quantity"),
                })
            
            raw_lot = extract_lot(internal_notes)
            normalized_lot = normalize_lot(raw_lot) if raw_lot else "UNKNOWN"
            
            # Also fetch shipments for this order to diagnose
            shipments_info = []
            try:
                shipments = client.list_shipments_for_order(order_id, page=1, page_size=10)
                for sh in (shipments or [])[:3]:
                    shipment_id_val = sh.get("shipmentId")
                    shipments_info.append({
                        "shipmentId": shipment_id_val,
                        "shipmentId_type": type(shipment_id_val).__name__,
                        "shipDate": sh.get("shipDate"),
                        "keys": list(sh.keys())[:15] if isinstance(sh, dict) else str(type(sh)),
                    })
            except Exception as e:
                shipments_info.append({"error": str(e)})
            
            diag_info["orders"].append({
                "order_id": order_id,
                "order_number": order_number,
                "internal_notes": internal_notes[:200] if internal_notes else "",
                "raw_lot": raw_lot,
                "normalized_lot": normalized_lot,
                "line_items": parsed_items,
                "shipments": shipments_info,
            })
    except Exception as e:
        diag_info["error"] = str(e)
    
    return render_template("admin/shipstation/diag.html", diag=diag_info)

