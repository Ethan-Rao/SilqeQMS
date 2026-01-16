from __future__ import annotations

import re


def canonical_customer_key(name: str) -> str:
    """
    Ported (lean) from legacy: normalize facility name to a stable canonical key.
    Rule: uppercase, remove non-alphanumeric.
    """
    s = (name or "").strip().upper()
    return re.sub(r"[^A-Z0-9]+", "", s)

