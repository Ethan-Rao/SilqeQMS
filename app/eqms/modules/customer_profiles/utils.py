from __future__ import annotations

import re


def normalize_facility_name(name: str) -> str:
    """
    Remove common business suffixes before canonicalization.
    This helps match "Hospital A" with "Hospital A, Inc."
    """
    s = (name or "").strip()
    # Remove common suffixes (case-insensitive)
    suffixes = [
        r'\s*,?\s+inc\.?$',
        r'\s*,?\s+llc\.?$',
        r'\s*,?\s+corp\.?$',
        r'\s*,?\s+corporation$',
        r'\s*,?\s+ltd\.?$',
        r'\s*,?\s+limited$',
        r'\s*,?\s+co\.?$',
        r'\s*,?\s+company$',
        r'\s*,?\s+p\.?c\.?$',  # Professional Corporation
        r'\s*,?\s+p\.?a\.?$',  # Professional Association
        r'\s*,?\s+pllc\.?$',   # Professional Limited Liability Company
        r'\s*,?\s+lp\.?$',     # Limited Partnership
        r'\s*,?\s+llp\.?$',    # Limited Liability Partnership
    ]
    for pattern in suffixes:
        s = re.sub(pattern, '', s, flags=re.IGNORECASE)
    return s.strip()


def canonical_customer_key(name: str) -> str:
    """
    Ported (lean) from legacy: normalize facility name to a stable canonical key.
    Rule: normalize name, uppercase, remove non-alphanumeric.
    """
    normalized = normalize_facility_name(name)
    s = normalized.upper()
    return re.sub(r"[^A-Z0-9]+", "", s)


def extract_email_domain(email: str) -> str | None:
    """Extract domain from email address."""
    if not email or '@' not in email:
        return None
    try:
        return email.split('@')[1].lower().strip()
    except IndexError:
        return None

