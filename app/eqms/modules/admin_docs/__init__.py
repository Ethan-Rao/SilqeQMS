"""
Admin document libraries for simple folder + document storage.
"""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint("admin_docs", __name__, url_prefix="/admin")

