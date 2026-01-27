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
    
    Algorithm:
    1. Remove common business suffixes (Inc., LLC, Corp., etc.) via normalize_facility_name()
    2. Convert to uppercase
    3. Remove all non-alphanumeric characters (spaces, punctuation, etc.)
    
    Examples:
        >>> canonical_customer_key("Hospital A, Inc.")
        'HOSPITALA'
        >>> canonical_customer_key("St. Joseph Hospital")
        'STJOSEPHHOSPITAL'
        >>> canonical_customer_key("123 Main St Medical Center")
        '123MAINSTMEDICALCENTER'
        >>> canonical_customer_key("Hospital A")
        'HOSPITALA'
    
    Edge Cases (Documented Behavior):
    - Abbreviations are NOT normalized:
        - "St" stays as "ST", "Street" stays as "STREET" → Different keys
        - "Ave" stays as "AVE", "Avenue" stays as "AVENUE" → Different keys
        - This is by design: abbreviation normalization would require complex heuristics
        
    - PO Box addresses:
        - PO Box is included if part of the name input
        - "Hospital PO Box 123" → "HOSPITALPOBOX123"
        
    - Same facility, different ship-to addresses:
        - Will produce different keys (by design)
        - Use compute_customer_key_from_sales_order() for address-aware matching
        
    - Business suffixes (removed automatically):
        - Inc., LLC, Corp., Ltd., Co., Company, etc.
        - "Hospital A, Inc." and "Hospital A" → Same key: "HOSPITALA"
    
    Note:
        This function operates on NAME ONLY. For address-based customer matching,
        use compute_customer_key_from_sales_order() which considers full ship-to data.
        
        The canonical pipeline for customer identity is:
        ShipStation → Distribution → Sales Order → Customer (via Sales Order)
        
        Sales Orders are the source of truth for customer identity.
    
    Args:
        name: Facility/company name to normalize
        
    Returns:
        Uppercase alphanumeric string suitable for use as a lookup key
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


def compute_customer_key_from_sales_order(sales_order_data: dict) -> str:
    """
    Compute deterministic customer_key from sales order ship-to data.
    
    This is the canonical source of truth for customer identity.
    
    Priority:
    1. customer_number (if present in SO) → "CUST:{normalized_number}"
    2. ship_to_name + address1 + city + state + zip → canonical_key(combined)
    3. ship_to_name + city + state → canonical_key(combined)
    4. ship_to_name only → canonical_key(ship_to_name)
    
    Args:
        sales_order_data: Dict with ship-to fields:
            - customer_number (optional)
            - ship_to_name / facility_name / customer_name
            - ship_to_address1 / address1
            - ship_to_city / city
            - ship_to_state / state
            - ship_to_zip / zip
    
    Returns:
        Canonical customer key string
    """
    # Priority 1: Customer number (most stable identifier)
    customer_number = sales_order_data.get("customer_number") or sales_order_data.get("account_number")
    if customer_number:
        normalized = re.sub(r"[^A-Z0-9]+", "", str(customer_number).upper())
        if normalized:
            return f"CUST:{normalized}"
    
    # Get ship-to fields (support multiple field names)
    name = (
        sales_order_data.get("ship_to_name") or 
        sales_order_data.get("facility_name") or 
        sales_order_data.get("customer_name") or 
        ""
    ).strip()
    
    addr1 = (
        sales_order_data.get("ship_to_address1") or 
        sales_order_data.get("address1") or 
        ""
    ).strip()
    
    city = (
        sales_order_data.get("ship_to_city") or 
        sales_order_data.get("city") or 
        ""
    ).strip()
    
    state = (
        sales_order_data.get("ship_to_state") or 
        sales_order_data.get("state") or 
        ""
    ).strip()
    
    zip_code = (
        sales_order_data.get("ship_to_zip") or 
        sales_order_data.get("zip") or 
        ""
    ).strip()
    
    # Priority 2: Full address
    if name and addr1 and city and state and zip_code:
        combined = f"{name} {addr1} {city} {state} {zip_code}"
        return canonical_customer_key(combined)
    
    # Priority 3: Name + city + state
    if name and city and state:
        combined = f"{name} {city} {state}"
        return canonical_customer_key(combined)
    
    # Priority 4: Name only
    if name:
        return canonical_customer_key(name)
    
    # Fallback (should not happen)
    return canonical_customer_key("UNKNOWN")

