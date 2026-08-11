from __future__ import annotations

import re


def normalize_facility_name(name: str) -> str:
    """
    Remove common business suffixes before canonicalization.
    This helps match "Hospital A" with "Hospital A, Inc."

    Used for company-key computation via ``canonical_customer_key`` — not as a
    display-name transform. Do not add ``AB`` (Swedish form): here AB is the
    operator's abbreviation for Advanced Bionics.
    """
    s = (name or "").strip()
    # Longer / compound suffixes first (GmbH & Co. KG before GmbH / mbH).
    suffixes = [
        r'\s*,?\s+gmbh\s+(?:&|und)\s+co\.?\s*kg\.?$',
        r'\s*,?\s+gmbh\.?$',
        r'\s*,?\s+mbh\.?$',
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


# Street-type expansions → short form (applied before keying).
_STREET_ABBREV = (
    (r"\bSTREET\b", "ST"),
    (r"\bDRIVE\b", "DR"),
    (r"\bAVENUE\b", "AVE"),
    (r"\bBOULEVARD\b", "BLVD"),
    (r"\bPARKWAY\b", "PKWY"),
    (r"\bHIGHWAY\b", "HWY"),
    (r"\bROAD\b", "RD"),
    (r"\bLANE\b", "LN"),
    (r"\bCOURT\b", "CT"),
    (r"\bPLACE\b", "PL"),
    (r"\bCIRCLE\b", "CIR"),
    (r"\bTERRACE\b", "TER"),
    (r"\bSUITE\b", "STE"),
    (r"\bBUILDING\b", "BLDG"),
    (r"\bFLOOR\b", "FL"),
    (r"\bROOM\b", "RM"),
    (r"\bCENTER\b", "CTR"),
    (r"\bNORTH\b", "N"),
    (r"\bSOUTH\b", "S"),
    (r"\bEAST\b", "E"),
    (r"\bWEST\b", "W"),
    (r"\bSAINT\b", "ST"),
)

# Suite / unit / building designators + following token — ignored for facility key.
# ``#`` cannot use ``\b`` (non-word char), so it is handled separately.
_UNIT_RE = re.compile(
    r"(?:\b(?:STE|SUITE|APT|APARTMENT|UNIT|BLDG|BUILDING|FL|FLOOR|RM|ROOM|STOP|DEPT|DEPARTMENT|"
    r"LEVEL|LVL)\b\s*[A-Z0-9\-]*|#\s*[A-Z0-9\-]*)",
    re.IGNORECASE,
)


def normalize_street_for_key(address1: str | None) -> str:
    """
    Normalize street line for facility matching.

    - Uppercase, strip punctuation
    - Collapse street-type abbreviations (STREET→ST, DRIVE→DR, …)
    - Drop suite/unit/bldg/floor designators (merge suite variants)
    - Keep house number; sort remaining tokens so word-order variants match
      (``6010 Amarillo Blvd West`` == ``6010 West Amarillo Blvd``)
    """
    s = normalize_addr_part(address1)
    if not s:
        return ""
    s = _UNIT_RE.sub(" ", s)
    s = re.sub(r"[^\w\s]", " ", s)
    for pat, repl in _STREET_ABBREV:
        s = re.sub(pat, repl, s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = re.findall(r"[A-Z0-9]+", s)
    if not tokens:
        return ""
    house = tokens[0] if tokens[0].isdigit() else ""
    rest = [t for t in tokens if t != house]
    rest_sorted = "".join(sorted(rest))
    return f"{house}{rest_sorted}" if house else rest_sorted


def prettify_facility_name(name: str | None) -> str:
    """Title-case a facility name; preserve common medical acronyms."""
    raw = re.sub(r"\s+", " ", (name or "").strip())
    if not raw:
        return "Unknown Facility"
    # Drop prior P41 payer shout suffix only: " — AMARILLO" / " — SAN DIEGO"
    # (em dash + ALL-CAPS city). Keep hyphenated clinical names like "VAMC - LOMA LINDA".
    raw = re.sub(r"\s+—\s+[A-Z][A-Z\s]{1,}$", "", raw).strip() or raw
    titled = raw.title()
    # Fix common acronyms after title-case.
    fixes = {
        r"\bUcla\b": "UCLA",
        r"\bVa\b": "VA",
        r"\bVamc\b": "VAMC",
        r"\bVa\s*-\s*": "VA ",
        r"\bUsc\b": "USC",
        r"\bNy\b": "NY",
        r"\bNj\b": "NJ",
        r"\bPa\b": "PA",
        r"\bCa\b": "CA",
        r"\bTx\b": "TX",
        r"\bFl\b": "FL",
        r"\bLlc\b": "LLC",
        r"\bIi\b": "II",
        r"\bIii\b": "III",
        r"\bPc\b": "PC",
        r"\bChi\b": "CHI",
        r"\bUnc\b": "UNC",
        r"\bMusc\b": "MUSC",
        r"\bUpmc\b": "UPMC",
    }
    for pat, repl in fixes.items():
        titled = re.sub(pat, repl, titled)
    return titled


def facility_display_name(
    ship_to_name: str | None,
    *,
    sold_to_name: str | None = None,
    city: str | None = None,
) -> str:
    """
    Display name for a catheter Ship-To facility Customer.

    Prefer the **clinical Ship-To facility name** (decision 1A). Do not brand
    profiles as payer ALL-CAPS + city (e.g. ``Marathon Medical Corporation — AMARILLO``).
    """
    base = (ship_to_name or "").strip()
    if not base or _is_weak_display_name(base):
        base = (sold_to_name or base or "Unknown Facility").strip()
    return prettify_facility_name(base)


def _is_weak_display_name(name: str) -> bool:
    s = (name or "").strip()
    if len(s) < 3:
        return True
    # Pure city/state fragments sometimes land in ship_to.
    if re.fullmatch(r"[A-Za-z .]+,\s*[A-Z]{2}\s*\d*", s):
        return True
    return False


def compute_facility_key_from_ship_to(
    *,
    address1: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip: str | None = None,
    facility_name: str | None = None,
) -> str:
    """
    Catheter facility key.

    Primary (when street + state + zip5 present):
        ``{normalized_street}|{STATE}|{ZIP5}``

    Street normalization collapses abbreviations, drops suite/unit tokens, and
    sorts non-numeric tokens so word-order / suite variants merge. ``address2``
    and city spelling variants are ignored when zip5 is present.

    Incomplete address → name tie-break + available parts.
    """
    street = normalize_street_for_key(address1)
    st = re.sub(r"[^A-Z0-9]+", "", normalize_addr_part(state))
    z = normalize_zip5(zip)
    name = re.sub(r"[^A-Z0-9]+", "", normalize_addr_part(facility_name))
    city_part = re.sub(r"[^A-Z0-9]+", "", normalize_addr_part(city))

    if street and st and z:
        return f"{street}|{st}|{z}"

    parts = [p for p in (name, street, city_part, st, z) if p]
    if parts:
        return "|".join(parts)
    return "UNKNOWN"


def compute_customer_key_from_sales_order(sales_order_data: dict) -> str:
    """
    Compute deterministic customer key from sales-order / distribution ship-to data.

    Prefer Ship-To address fields. Do **not** use payer account / customer_number
    alone (collapses multi-site payers like Marathon).
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


_COMPANYISH_TOKENS = frozenset(
    {
        "medical",
        "hospital",
        "clinic",
        "health",
        "healthcare",
        "urology",
        "university",
        "technologies",
        "technology",
        "scientific",
        "sciences",
        "corporation",
        "company",
        "associates",
        "systems",
        "medtech",
        "bio",
        "children",
        "childrens",
        "pathway",
        "momentum",
        "neptune",
        "supira",
        "hybron",
        "tingo",
        "abbvie",
        "boston",
        "aspero",
        "fearsome",
        "richman",
        "chemical",
        "limited",
        "gmbh",
        "inc",
        "llc",
        "ltd",
        "corp",
    }
)


def name_initials(name: str) -> str:
    """Initials of significant tokens after suffix strip (Advanced Bionics -> AB)."""
    base = normalize_facility_name(name)
    words = re.findall(r"[A-Za-z0-9]+", base)
    return "".join(w[0] for w in words if w).upper()


def names_likely_same_company(name_a: str, name_b: str) -> bool:
    """Same company-level identity: equal canonical keys, or short name = initials of long."""
    ka = canonical_customer_key(name_a)
    kb = canonical_customer_key(name_b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    # "AB" vs "Advanced Bionics Gmbh" — short form equals initials of the longer name.
    if len(ka) <= 3 and ka == name_initials(name_b):
        return True
    if len(kb) <= 3 and kb == name_initials(name_a):
        return True
    return False


def preferred_company_display_name(*names: str) -> str:
    """Prefer the most complete company name (longer, not a short abbreviation)."""
    scored: list[tuple[int, int, str]] = []
    for raw in names:
        name = (raw or "").strip()
        if not name:
            continue
        key = canonical_customer_key(name)
        # Short all-caps abbreviations score poorly vs full legal names.
        abbrev_penalty = -50 if len(key) <= 3 else 0
        scored.append((len(key) + abbrev_penalty, len(name), name))
    if not scored:
        return ""
    scored.sort(reverse=True)
    return scored[0][2]


def is_person_shaped_customer_name(name: str) -> bool:
    """Crude hold rule: two alphabetic tokens, no company-ish word, no corporate suffix.

    Transparent so the operator can audit it. Known case: Aniq Darr.
    """
    raw = (name or "").strip()
    if not raw:
        return False
    if normalize_facility_name(raw) != raw:
        return False
    tokens = [t for t in re.split(r"\s+", raw) if t]
    if len(tokens) != 2:
        return False
    for t in tokens:
        letters = re.sub(r"[^A-Za-z]", "", t)
        if not letters or not re.fullmatch(r"[A-Za-z]+", letters):
            return False
        if letters.lower() in _COMPANYISH_TOKENS:
            return False
        if len(letters) > 14:
            return False
    return True
