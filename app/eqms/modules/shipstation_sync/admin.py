from __future__ import annotations

from flask import Blueprint, flash, g, redirect, render_template, url_for
from sqlalchemy import func

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.rep_traceability.models import DistributionLogEntry
from app.eqms.modules.shipstation_sync.models import ShipStationSkippedOrder, ShipStationSyncRun
from app.eqms.modules.shipstation_sync.service import run_sync
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
    return {
        "total": total,
        "by_source": {src: cnt for src, cnt in by_source},
        "min_ship_date": date_range[0],
        "max_ship_date": date_range[1],
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
    return render_template(
        "admin/shipstation/index.html",
        runs=runs,
        skipped=skipped,
        diag=diag,
        sync_run_count=sync_run_count,
        skipped_count=skipped_count,
    )


@bp.post("/shipstation/run")
@require_permission("shipstation.run")
def shipstation_run():
    s = db_session()
    u = _current_user()
    try:
        run = run_sync(s, user=u)
        s.commit()
        flash(f"ShipStation sync completed. Synced={run.synced_count} skipped={run.skipped_count}.", "success")
    except Exception as e:
        s.rollback()
        flash(f"ShipStation sync failed: {e}", "danger")
    return redirect(url_for("shipstation_sync.shipstation_index"))

