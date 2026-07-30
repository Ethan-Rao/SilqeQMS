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
    Normalize facility name to a stable canonical key for customer deduplication.

    Name-only key used for **company-level** identity (NRE / Sold-To accounts).
    For catheter Ship-To facilities use ``compute_customer_key_from_sales_order`` /
    ``compute_facility_key_from_ship_to``.
    """
    if name is None:
        return ""
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


def normalize_addr_part(value: str | None) -> str:
    """Trim, collapse whitespace, uppercase — for facility key material."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).upper()


def normalize_zip5(zip_code: str | None) -> str:
    """US ZIP: keep first 5 digits; empty if none."""
    digits = re.sub(r"\D", "", str(zip_code or ""))
    return digits[:5] if digits else ""


def facility_display_name(
    ship_to_name: str | None,
    *,
    sold_to_name: str | None = None,
    city: str | None = None,
) -> str:
    """
    Display name for a catheter Ship-To facility Customer.

    Prefer the ship-to company/name; fall back to sold-to. Append city when
    present and not already in the name so Marathon-style sites stay distinguishable
    (e.g. ``Marathon Medical Corporation — Long Beach``).
    """
    base = (ship_to_name or sold_to_name or "Unknown Facility").strip()
    city_s = (city or "").strip()
    if city_s and city_s.lower() not in base.lower():
        return f"{base} — {city_s}"
    return base


def compute_facility_key_from_ship_to(
    *,
    address1: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip: str | None = None,
    facility_name: str | None = None,
) -> str:
    """
    Catheter facility key (P41).

    Format when complete:
        canonical_customer_key(f"{ADDR1}|{CITY}|{STATE}|{ZIP5}")
    ``address2`` is intentionally ignored (suite/floor variants = one facility).

    If address is incomplete, fall back with normalized facility name plus
    whatever address parts exist (name as tie-break).
    """
    a1 = normalize_addr_part(address1)
    c = normalize_addr_part(city)
    st = normalize_addr_part(state)
    z = normalize_zip5(zip)
    name = normalize_addr_part(facility_name)

    if a1 and c and st and z:
        # Primary catheter key: address1|city|state|zip5 (no name, no address2).
        return canonical_customer_key(f"{a1}|{c}|{st}|{z}")

    # Incomplete address — name as tie-break with available parts.
    parts = [p for p in (name, a1, c, st, z) if p]
    if parts:
        return canonical_customer_key("|".join(parts))
    return canonical_customer_key("UNKNOWN")


def compute_customer_key_from_sales_order(sales_order_data: dict) -> str:
    """
    Compute deterministic customer key from sales-order / distribution ship-to data.

    P41 catheter facility identity:
      - Prefer address1|city|state|zip5 (ignore address2).
      - Do **not** use payer account / customer_number alone (collapses Marathon sites).
      - Incomplete address → name + available address parts.

    Field aliases: ship_to_* preferred; bare address1/city/state/zip also accepted.
    """
    name = (
        sales_order_data.get("ship_to_name")
        or sales_order_data.get("facility_name")
        or sales_order_data.get("customer_name")
        or ""
    )
    return compute_facility_key_from_ship_to(
        address1=sales_order_data.get("ship_to_address1") or sales_order_data.get("address1"),
        city=sales_order_data.get("ship_to_city") or sales_order_data.get("city"),
        state=sales_order_data.get("ship_to_state") or sales_order_data.get("state"),
        zip=sales_order_data.get("ship_to_zip") or sales_order_data.get("zip"),
        facility_name=name,
    )
