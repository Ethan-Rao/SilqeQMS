"""
Quality Objectives (QM.SLQ037 Rev B) tracking.

Five objectives; objective 4 (training activities) is computed live from
TrainingAssignment data, the rest are manually entered and persisted in the
``system_settings`` key-value table under a single JSON blob.
"""
from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from app.eqms.utils import utcnow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.models import User

SETTING_KEY = "quality_objectives"

# The five objectives from QM.SLQ037 Rev B / DCO094. ``auto`` objectives are
# computed from live data and not manually editable.
OBJECTIVES = [
    {"key": "incoming_lot_acceptance", "name": "Incoming material quality",
     "target": "Lot acceptance rate ≥ 90%", "auto": False},
    {"key": "complaint_rate", "name": "Finished product complaint rate",
     "target": "< 1% of distributed product", "auto": False},
    {"key": "pms_activities", "name": "Active post-market surveillance",
     "target": "≥ 12 activities per year", "auto": False},
    {"key": "training_activities", "name": "Employee training program",
     "target": "≥ 10 training activities per year", "auto": True},
    {"key": "qp_execution", "name": "Quarterly QP execution",
     "target": "≥ 80% of action items on or ahead of schedule (min 5 items)", "auto": False},
]

MANUAL_KEYS = [o["key"] for o in OBJECTIVES if not o["auto"]]


def _load_blob(s: "Session") -> dict:
    from app.eqms.models import SystemSetting

    row = s.get(SystemSetting, SETTING_KEY)
    if row is None or not row.value:
        return {}
    try:
        return json.loads(row.value)
    except (ValueError, TypeError):
        return {}


def compute_training_activities(s: "Session", year: int | None = None) -> int:
    """Live value for objective 4: acknowledged training in the current year."""
    from sqlalchemy import func

    from app.eqms.modules.training.models import TrainingAssignment

    year = year or date.today().year
    return int(
        s.query(func.count(TrainingAssignment.id))
        .filter(
            TrainingAssignment.acknowledged_at.isnot(None),
            func.extract("year", TrainingAssignment.acknowledged_at) == year,
        )
        .scalar()
        or 0
    )


def get_objectives(s: "Session") -> list[dict]:
    """Return the objectives enriched with current value + last-updated metadata."""
    blob = _load_blob(s)
    out = []
    for o in OBJECTIVES:
        entry = dict(o)
        if o["auto"] and o["key"] == "training_activities":
            entry["value"] = str(compute_training_activities(s))
            entry["updated_at"] = "live"
        else:
            saved = blob.get(o["key"], {})
            entry["value"] = saved.get("value", "")
            entry["updated_at"] = saved.get("updated_at", "")
        out.append(entry)
    return out


def save_objectives(s: "Session", form: dict, user: "User | None") -> None:
    """Persist manually-entered objective values (auto objectives are ignored)."""
    from app.eqms.models import SystemSetting

    blob = _load_blob(s)
    now = utcnow().isoformat(timespec="seconds")
    for key in MANUAL_KEYS:
        if key in form:
            blob[key] = {"value": (form.get(key) or "").strip(), "updated_at": now}

    row = s.get(SystemSetting, SETTING_KEY)
    if row is None:
        row = SystemSetting(key=SETTING_KEY)
        s.add(row)
    row.value = json.dumps(blob)
    row.updated_at = utcnow()
    if user is not None:
        row.updated_by_user_id = user.id
