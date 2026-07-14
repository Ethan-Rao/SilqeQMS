"""
Quality Planning (QM.SLQ037 Rev B) tracking.

Two persisted blobs in the ``system_settings`` key-value table:
- ``quality_objectives`` — four manually-entered objectives (value + notes + period).
- ``quality_plan_scorecard`` — the quarterly Quality Plan action-item scorecard
  (a JSON list of {item, owner, target, status, notes}).

Both fall back to pre-populated Q2/Q3 2026 defaults when never saved.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.eqms.utils import utcnow

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.eqms.models import User

SETTING_KEY = "quality_objectives"
SCORECARD_KEY = "quality_plan_scorecard"

# QM.SLQ037 Rev B / DCO094 objectives (Employee Training removed in Prompt 22).
OBJECTIVES = [
    {"key": "incoming_lot_acceptance", "name": "Incoming Material Quality",
     "target": "Lot acceptance rate ≥ 90%"},
    {"key": "complaint_rate", "name": "Finished Product Complaint Rate",
     "target": "< 1% of distributed product"},
    {"key": "pms_activities", "name": "Active Post-Market Surveillance Activities",
     "target": "≥ 12 activities per year"},
    {"key": "qp_execution", "name": "Quarterly Quality Plan Execution",
     "target": "≥ 80% of action items on-schedule (min 5 tracked)"},
]

# Q2 2026 defaults, used until an admin saves the first time.
DEFAULTS = {
    "incoming_lot_acceptance": {"value": "N/A — no lots received",
                                "notes": "Tracking resumes at next material receipt",
                                "period": "Q2 2026"},
    "complaint_rate": {"value": "0% (0 complaints)",
                       "notes": "Target: <1% — on track",
                       "period": "Q2 2026"},
    "pms_activities": {"value": "3 of 12 activities YTD",
                       "notes": "On pace for annual target (3/qtr)",
                       "period": "Q2 2026"},
    "qp_execution": {"value": "92% (12/13 items)",
                     "notes": "Q2 execution rate — exceeds 80% target",
                     "period": "Q2 2026"},
}

OBJECTIVE_KEYS = [o["key"] for o in OBJECTIVES]

# Q3 2026 Quality Plan scorecard (from the Q2 2026 Quality Report, Section 6).
# Status ∈ {Complete, In Progress, Deferred, Not Yet Due, Needs Follow-Up}.
DEFAULT_SCORECARD = [
    {"item": "QMSR Supplementary Provision Mapping", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO094 (QM.SLQ027 Rev F)"},
    {"item": "Medical Device File Framework", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO094 (QM.SLQ027 and QM.SLQ048)"},
    {"item": "QMS Platform Transition DC.SLQ002", "owner": "Ethan Rao", "target": "Per schedule",
     "status": "In Progress", "notes": "Procedure revisions complete (DCO091-095); file migration underway"},
    {"item": "Systemic Legacy Part 820 References", "owner": "Ethan Rao", "target": "Q3 2026",
     "status": "Not Yet Due", "notes": "Substantially addressed through DCO091-095; final confirmation at Q3"},
    {"item": "Quality Objectives — Revise Existing", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO094 (QM.SLQ037 Rev B); thresholds tightened"},
    {"item": "Quality Objectives — Add Three New", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO094; PMS, training, and QP-execution objectives added"},
    {"item": "New Hire Training — Haley Shomo", "owner": "Ethan Rao", "target": "Q3 2026",
     "status": "Deferred", "notes": "All training activities moved to Q3 per management direction"},
    {"item": "QMSR Transition Training", "owner": "Ethan Rao", "target": "Q3 2026",
     "status": "Deferred", "notes": "All training activities moved to Q3 per management direction"},
    {"item": "Regulatory Reference Materials (AAMI/ISO 13485 Guide)", "owner": "Verne Sharma", "target": "Q2 2026",
     "status": "Complete", "notes": "AAMI/ISO 13485:2016 Practical Guide and regulatory standards purchased"},
    {"item": "Design Control Retraining (CAPA 2025-003 effectiveness confirmation)", "owner": "Ethan Rao",
     "target": "Q3 2026", "status": "Deferred",
     "notes": "Training execution moved to Q3; this is the effectiveness confirmation for CAPA 2025-003"},
    {"item": "Complaint and MDR Escalation Pathway", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO093 (QM.SLQ021 cross-reference section)"},
    {"item": "Valve Modification Design Assessment (DC.SLQ001)", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Design review signed; Letter to File finalized; project closed"},
    {"item": "Design Control Procedure Revisions (CAPA 2025-003)", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO095 (QM.SLQ052 Pathway C mandatory supplier trigger)"},
    {"item": "Supplier Audit — Pathway MedTech", "owner": "Ethan Rao", "target": "Q4 2026",
     "status": "Not Yet Due", "notes": "On-site audit scheduled for Q4"},
    {"item": "Feedback Governance Procedure", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO094 (QM.SLQ033 feedback governance section)"},
    {"item": "Active Post-Market Surveillance Program (formal establishment)", "owner": "Ethan Rao",
     "target": "Q3 2026", "status": "Needs Follow-Up",
     "notes": "Formal program establishment not completed in Q2; active surveillance activities underway (3 YTD); carried to Q3"},
    {"item": "Complaint Non-Investigation Rationale", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO093 (QM.SLQ021)"},
    {"item": "Regulatory Reporting QMSR Framing", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Completed via DCO093 (QM.SLQ022 and QM.SLQ030)"},
    {"item": "CAPA 2025-001 Effectiveness Confirmation", "owner": "Ethan Rao", "target": "Nov 2026",
     "status": "Not Yet Due", "notes": "Monitoring complaints through November 2026"},
    {"item": "CAPA 2025-002 Effectiveness Confirmation", "owner": "Ethan Rao", "target": "Dec 2026",
     "status": "Not Yet Due", "notes": "Evaluating complaints through December 2026"},
    {"item": "CAPA 2025-003 Corrective Action Completion", "owner": "Ethan Rao", "target": "Q3 2026",
     "status": "In Progress", "notes": "Procedure revisions and DC.SLQ001 complete; retraining deferred to Q3"},
    {"item": "Post-Production Risk File Update Triggers", "owner": "Ethan Rao", "target": "Q3 2026",
     "status": "Not Yet Due", "notes": "Decision framework added to QM.SLQ012 via DCO093; Q3 review"},
    {"item": "Failure Mode and Probability Rating Review", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "RM-0018 through RM-0021 and related files reviewed against complaint history"},
    {"item": "ASTM F623-25 Risk Management Alignment", "owner": "Ethan Rao", "target": "Q3 2026",
     "status": "Not Yet Due", "notes": "Risk management policy evaluation and update"},
    {"item": "Packaging Inspection for ASTM F1886", "owner": "Ethan Rao", "target": "Q2 2026",
     "status": "Complete", "notes": "Visual inspection of existing finished goods completed; compliance confirmed"},
    {"item": "Gage R&R Study (UV and Rinse Test)", "owner": "Ethan Rao", "target": "Upon next production",
     "status": "Not Yet Due", "notes": "Timing dependent on next C.SLQ001 production run"},
    {"item": "UV Spectroscopy Test Protocol Development", "owner": "Na He", "target": "Q3 2026",
     "status": "Not Yet Due", "notes": "Protocol development for incoming and finished catheter analysis"},
    {"item": "Dynamic Employee Training Program", "owner": "Ethan Rao", "target": "Q3 2026",
     "status": "Not Yet Due", "notes": "Comprehension-based training assessment program"},
]

_SCORECARD_FIELDS = ("item", "owner", "target", "status", "notes")


def _load_json(s: "Session", key: str):
    from app.eqms.models import SystemSetting

    row = s.get(SystemSetting, key)
    if row is None or not row.value:
        return None
    try:
        return json.loads(row.value)
    except (ValueError, TypeError):
        return None


def _save_json(s: "Session", key: str, data, user: "User | None") -> None:
    from app.eqms.models import SystemSetting

    row = s.get(SystemSetting, key)
    if row is None:
        row = SystemSetting(key=key)
        s.add(row)
    row.value = json.dumps(data)
    row.updated_at = utcnow()
    if user is not None:
        row.updated_by_user_id = user.id


def get_objectives(s: "Session") -> list[dict]:
    """Return the four objectives enriched with current value/notes/period.

    Falls back to the Q2 2026 defaults per-objective until an admin saves.
    """
    blob = _load_json(s, SETTING_KEY) or {}
    out = []
    for o in OBJECTIVES:
        entry = dict(o)
        saved = blob.get(o["key"]) or {}
        default = DEFAULTS.get(o["key"], {})
        entry["value"] = saved.get("value") if saved.get("value") is not None else default.get("value", "")
        entry["notes"] = saved.get("notes") if saved.get("notes") is not None else default.get("notes", "")
        entry["period"] = saved.get("period") or default.get("period", "")
        entry["updated_at"] = saved.get("updated_at", "")
        out.append(entry)
    return out


def save_objectives(s: "Session", form: dict, user: "User | None") -> None:
    """Persist objective value/notes/period from the submitted form."""
    blob = _load_json(s, SETTING_KEY) or {}
    now = utcnow().isoformat(timespec="seconds")
    for key in OBJECTIVE_KEYS:
        if key in form:
            blob[key] = {
                "value": (form.get(key) or "").strip(),
                "notes": (form.get(key + "_notes") or "").strip(),
                "period": (form.get(key + "_period") or "").strip(),
                "updated_at": now,
            }
    _save_json(s, SETTING_KEY, blob, user)


def get_scorecard(s: "Session") -> list[dict]:
    """Return the Quality Plan scorecard, falling back to Q3 2026 defaults."""
    data = _load_json(s, SCORECARD_KEY)
    if not isinstance(data, list) or not data:
        return [dict(row) for row in DEFAULT_SCORECARD]
    cleaned = []
    for row in data:
        if isinstance(row, dict):
            cleaned.append({f: (row.get(f) or "") for f in _SCORECARD_FIELDS})
    return cleaned or [dict(row) for row in DEFAULT_SCORECARD]


def save_scorecard(s: "Session", raw_json: str, user: "User | None") -> tuple[bool, str]:
    """Parse and persist the scorecard JSON. Returns (ok, message)."""
    try:
        data = json.loads(raw_json)
    except (ValueError, TypeError) as e:
        return False, f"Invalid JSON: {e}"
    if not isinstance(data, list):
        return False, "Scorecard must be a JSON list of action items."
    cleaned = []
    for row in data:
        if not isinstance(row, dict):
            return False, "Each action item must be a JSON object."
        cleaned.append({f: str(row.get(f, "") or "") for f in _SCORECARD_FIELDS})
    _save_json(s, SCORECARD_KEY, cleaned, user)
    return True, f"Scorecard saved ({len(cleaned)} action items)."
