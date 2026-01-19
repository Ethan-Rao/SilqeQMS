from __future__ import annotations

from flask import Blueprint, flash, g, redirect, render_template, url_for

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.shipstation_sync.models import ShipStationSkippedOrder, ShipStationSyncRun
from app.eqms.modules.shipstation_sync.service import run_sync
from app.eqms.rbac import require_permission

bp = Blueprint("shipstation_sync", __name__)


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


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
    return render_template("admin/shipstation/index.html", runs=runs, skipped=skipped)


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

