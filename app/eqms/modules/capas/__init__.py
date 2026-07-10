"""
CAPA tracker module — structured status/dates/workflow for Corrective and
Preventive Actions (complements the `capas` admin_docs document library).
"""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint("capas", __name__, url_prefix="/admin")
