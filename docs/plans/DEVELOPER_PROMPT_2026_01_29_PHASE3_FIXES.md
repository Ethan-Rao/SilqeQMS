# Developer Prompt: Phase 3 Fixes & Enhancements
**Date:** 2026-01-29  
**Priority:** Critical, High, Medium

---

## Executive Summary

This document addresses three user-reported issues plus 10 additional system issues identified during code review. Focus areas include:
1. Customer address backfill fixes (duplicated address, only 1 customer found)
2. Sales Dashboard lot tracking for SKUs without 2025+ lots
3. PDF parsing improvements for Bill To vs Ship To address handling
4. Multiple code quality and reliability issues

---

## Critical Issues (User-Reported)

### ISSUE 1: Backfill Script Only Finding 1 Customer

**Current Problem:**
The `scripts/backfill_customer_addresses.py` script is only backfilling 1 customer. This occurs because:
1. The script queries for customers where `address1 IS NULL OR address1 == ""`, but SQLAlchemy's `is_()` comparison may not match all empty strings
2. The script only processes customers that have a `sales_order_page` PDF attachment

**File:** `scripts/backfill_customer_addresses.py`

**Root Cause Analysis:**
```python
# Current query (lines 30-34):
customers_without_address = (
    s.query(Customer)
    .filter((Customer.address1.is_(None)) | (Customer.address1 == ""))
    .all()
)
```

The issue is that the query only finds customers where the PDF attachment exists with `pdf_type == "sales_order_page"`. Most customers may have been imported before PDF storage was implemented or have no PDF attached.

**Fix:**

```python
"""
One-time script to backfill customer addresses from their first matched Sales Order PDF.

Run: python scripts/backfill_customer_addresses.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.eqms import create_app
from app.eqms.db import db_session
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
from app.eqms.modules.rep_traceability.parsers.pdf import (
    _extract_text,
    _parse_customer_email,
    _parse_ship_to_block,
    _parse_bill_to_block,  # NEW: Must implement this
)
from app.eqms.storage import storage_from_config


def backfill_addresses() -> None:
    app = create_app()
    with app.app_context():
        s = db_session()

        # More robust query - find ALL customers without complete address
        # A customer needs address backfill if address1 is NULL, empty string, or whitespace-only
        customers_without_address = (
            s.query(Customer)
            .filter(
                (Customer.address1.is_(None)) |
                (Customer.address1 == "") |
                (Customer.address1.like("    %"))  # Whitespace-only
            )
            .all()
        )

        # Alternative: Process ALL customers and only update if data is missing
        # This ensures we don't miss anyone
        all_customers = s.query(Customer).all()
        customers_to_process = [
            c for c in all_customers
            if not (c.address1 or "").strip()  # No address yet
        ]

        print(f"Found {len(customers_to_process)} customers without addresses")

        updated = 0
        storage = storage_from_config(app.config)

        for customer in customers_to_process:
            # Get the FIRST (oldest) sales order for this customer
            first_order = (
                s.query(SalesOrder)
                .filter(SalesOrder.customer_id == customer.id)
                .order_by(SalesOrder.order_date.asc())
                .first()
            )
            if not first_order:
                print(f"  Skip: {customer.facility_name} - no sales orders")
                continue

            # Find PDF attachment - try sales_order_page first, then any type
            attachment = (
                s.query(OrderPdfAttachment)
                .filter(OrderPdfAttachment.sales_order_id == first_order.id)
                .filter(OrderPdfAttachment.pdf_type == "sales_order_page")
                .first()
            )
            if not attachment:
                # Try any PDF type as fallback
                attachment = (
                    s.query(OrderPdfAttachment)
                    .filter(OrderPdfAttachment.sales_order_id == first_order.id)
                    .first()
                )
            if not attachment:
                print(f"  Skip: {customer.facility_name} - no PDF attachment for SO#{first_order.order_number}")
                continue

            try:
                with storage.open(attachment.storage_key) as fobj:
                    pdf_bytes = fobj.read()
                text = _extract_text(pdf_bytes)

                # PRIORITY: Address from BILL TO (the billing/company address)
                bill_to = _parse_bill_to_block(text)
                
                # Contact name from SHIP TO (the actual recipient)
                ship_to = _parse_ship_to_block(text)
                
                contact_email = _parse_customer_email(text)
                
                changed = False
                
                # Address fields: Prefer BILL TO over SHIP TO
                if bill_to.get("bill_to_address1") and not (customer.address1 or "").strip():
                    customer.address1 = bill_to.get("bill_to_address1")
                    customer.city = bill_to.get("bill_to_city")
                    customer.state = bill_to.get("bill_to_state")
                    customer.zip = bill_to.get("bill_to_zip")
                    changed = True
                elif ship_to.get("ship_to_address1") and not (customer.address1 or "").strip():
                    # Fallback to ship_to if no bill_to address
                    customer.address1 = ship_to.get("ship_to_address1")
                    customer.city = ship_to.get("ship_to_city")
                    customer.state = ship_to.get("ship_to_state")
                    customer.zip = ship_to.get("ship_to_zip")
                    changed = True
                    
                # Contact name: Use SHIP TO name (the actual recipient/contact)
                if ship_to.get("ship_to_name") and not (customer.contact_name or "").strip():
                    customer.contact_name = ship_to.get("ship_to_name")
                    changed = True
                    
                # Email: Use any found email
                if contact_email and not (customer.contact_email or "").strip():
                    customer.contact_email = contact_email
                    changed = True
                
                if changed:
                    updated += 1
                    print(f"Updated: {customer.facility_name} from SO#{first_order.order_number}")
                    print(f"  - Address: {customer.address1}, {customer.city}, {customer.state} {customer.zip}")
                    print(f"  - Contact: {customer.contact_name} / {customer.contact_email}")
                    
            except Exception as e:
                print(f"Error processing {customer.facility_name}: {e}")
                continue

        s.commit()
        print(f"\nBackfill complete: {updated} customers updated")


if __name__ == "__main__":
    backfill_addresses()
```

---

### ISSUE 2: Duplicated Address Line 1 from Bill To / Ship To

**Current Problem:**
The PDF parser is using `_parse_ship_to_block()` for both customer name AND address. When the Bill To and Ship To have the same address line, the system may capture it twice or from the wrong section.

**Business Rule Clarification:**
- **Customer Name:** First line under "Sold To" (the company/facility name)
- **Customer Address:** From "Bill To" section (the billing address)
- **Contact Name:** First line under "Ship To" (the recipient name on shipping label)

**File:** `app/eqms/modules/rep_traceability/parsers/pdf.py`

**Add New Function - `_parse_bill_to_block()`:**

```python
def _parse_bill_to_block(text: str) -> dict[str, str | None]:
    """
    Parse BILL TO block from SILQ Sales Order PDF.
    
    This is the company's billing address - different from Ship To which is
    the delivery address. Bill To is used for the customer's canonical address.
    
    Expected format:
    BILL TO:
    Company Name
    123 Street Address
    City, ST 12345
    """
    result = {
        "bill_to_name": None,
        "bill_to_address1": None,
        "bill_to_city": None,
        "bill_to_state": None,
        "bill_to_zip": None,
    }

    # Try to find BILL TO section
    bill_to_match = re.search(
        r"Bill\s*To\s*[:\n](.+?)(?=\n\s*\n|Ship\s*To|Salesperson:|Terms|P\.?O\.?\s*#|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    
    # If no explicit BILL TO, try SOLD TO as the billing entity
    if not bill_to_match:
        bill_to_match = re.search(
            r"Sold\s*To\s*[:\n](.+?)(?=\n\s*\n|Ship\s*To|Salesperson:|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
    
    if not bill_to_match:
        return result

    lines = [l.strip() for l in bill_to_match.group(1).strip().split("\n") if l.strip()]

    # First non-numeric line is typically the company name
    for line in lines:
        if line and len(line) > 2 and not re.match(r"^\d+\s", line):
            result["bill_to_name"] = line
            break

    # Look for address line (starts with number or contains street indicators)
    for line in lines:
        if re.match(r"^\d+\s+\w", line) or any(
            x in line.lower()
            for x in ["street", "st.", "ave", "blvd", "road", "rd.", "drive", "dr.", "lane", "ln.", "suite", "ste"]
        ):
            result["bill_to_address1"] = line
            break

    # City, State ZIP pattern
    city_state_zip_pattern = re.compile(
        r"^([A-Za-z\s\.]+)[,\s]+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)(?:\s+[A-Z]{2})?$"
    )
    for line in lines:
        match = city_state_zip_pattern.match(line)
        if match:
            result["bill_to_city"] = match.group(1).strip()
            result["bill_to_state"] = match.group(2)
            result["bill_to_zip"] = match.group(3)
            break

    return result
```

**Update `_parse_silq_sales_order_page()` (lines 267-346):**

```python
def _parse_silq_sales_order_page(page, text: str, page_num: int) -> dict[str, Any] | None:
    # ... existing order number and date parsing ...
    
    # Customer name from SOLD TO
    customer_name = _parse_sold_to_block(text) or "Unknown Customer"
    
    # Address from BILL TO (billing address = company address)
    bill_to = _parse_bill_to_block(text)
    
    # Contact info from SHIP TO (shipping recipient = contact person)
    ship_to = _parse_ship_to_block(text)
    
    contact_email = _parse_customer_email(text)

    # ... existing item parsing ...

    return {
        "order_number": order_number,
        "order_date": order_date,
        "ship_date": order_date,
        "customer_name": customer_name,
        # ADDRESS: From Bill To (company billing address)
        "address1": bill_to.get("bill_to_address1"),
        "city": bill_to.get("bill_to_city"),
        "state": bill_to.get("bill_to_state"),
        "zip": bill_to.get("bill_to_zip"),
        # CONTACT: From Ship To (shipping recipient)
        "contact_name": ship_to.get("ship_to_name"),
        "contact_email": contact_email,
        # Keep ship_to fields for backward compatibility
        "ship_to_name": ship_to.get("ship_to_name"),
        "ship_to_address1": ship_to.get("ship_to_address1"),
        "ship_to_city": ship_to.get("ship_to_city"),
        "ship_to_state": ship_to.get("ship_to_state"),
        "ship_to_zip": ship_to.get("ship_to_zip"),
        "lines": items,
    }
```

**Update `find_or_create_customer` call in `admin.py` (around line 1902):**

```python
customer = find_or_create_customer(
    s,
    facility_name=customer_name,
    # Use bill_to address (company address) - NOT ship_to
    address1=order_data.get("address1") or order_data.get("ship_to_address1"),
    city=order_data.get("city") or order_data.get("ship_to_city"),
    state=order_data.get("state") or order_data.get("ship_to_state"),
    zip=order_data.get("zip") or order_data.get("ship_to_zip"),
    # Contact from ship_to (recipient)
    contact_name=order_data.get("contact_name"),
    contact_email=order_data.get("contact_email"),
)
```

---

### ISSUE 3: Sales Dashboard - SKUs Without 2025+ Lots Should Show Most Recent Lot

**Current Problem:**
The "Inventory by SKU" table only shows lots manufactured since 2025. If a SKU has no lots manufactured since 2025, it shows "—" for the current lot. The user wants to see the most recent lot from LotLog even if it was manufactured before 2025.

**File:** `app/eqms/modules/rep_traceability/service.py` (lines 900-920)

**Current Logic:**
```python
lot_tracking = []
for sku in VALID_SKUS:
    total_produced = sku_total_produced.get(sku, 0)
    total_distributed = sku_total_distributed.get(sku, 0)
    current_lot = sku_latest_lot.get(sku, "—")  # <-- Returns "—" if no 2025+ lot
    # ...
```

**Fix - Add fallback to find most recent lot from LotLog:**

```python
# Add after line 898 and before the lot_tracking construction

# Find most recent lot per SKU from LotLog (for fallback display)
sku_most_recent_lot: dict[str, str] = {}
for lot, sku in lot_to_sku.items():
    if not sku or sku not in VALID_SKUS:
        continue
    # Only consider canonical lots (normalized with SLQ- prefix)
    if not lot.startswith("SLQ-"):
        continue
    # Track the lot with highest year (most recent)
    lot_year = lot_years.get(lot, 0)
    current_year = sku_most_recent_lot.get(sku)
    if current_year:
        current_best_year = lot_years.get(current_year, 0)
        if lot_year > current_best_year:
            sku_most_recent_lot[sku] = lot
    else:
        sku_most_recent_lot[sku] = lot

lot_tracking = []
for sku in VALID_SKUS:
    total_produced = sku_total_produced.get(sku, 0)
    total_distributed = sku_total_distributed.get(sku, 0)
    
    # Current lot: From 2025+ distributions if available, otherwise from LotLog
    if sku in sku_latest_lot:
        current_lot = sku_latest_lot[sku]
        last_date = sku_last_date.get(sku)
    else:
        # Fallback: Most recent lot from LotLog (even if pre-2025)
        current_lot = sku_most_recent_lot.get(sku, "—")
        last_date = None  # No distribution date since this is from LotLog only
    
    remaining = total_produced - total_distributed if total_produced > 0 else None

    lot_tracking.append(
        {
            "sku": sku,
            "lot": current_lot,
            "total_produced": total_produced,
            "total_distributed": total_distributed,
            "remaining": remaining,
            "last_date": last_date,
        }
    )

lot_tracking = sorted(lot_tracking, key=lambda x: x["sku"], reverse=True)
```

---

## High Priority Issues (System Review)

### ISSUE 4: Critical Bug - Escaped Regex in Lot Year Parsing

**Severity:** HIGH - Prevents lot year extraction from working

**File:** `app/eqms/modules/shipstation_sync/parsers.py` (lines 227, 234)

**Current Code (BROKEN):**
```python
# Line 227 - Double-escaped backslash breaks regex
m = re.search(r"(20\\d{2})", canonical_lot)

# Line 234 - Same issue
digits = re.sub(r"\\D", "", canonical_lot or "")
```

**Fix:**
```python
# Line 227 - Correct single backslash
m = re.search(r"(20\d{2})", canonical_lot)

# Line 234 - Correct single backslash
digits = re.sub(r"\D", "", canonical_lot or "")
```

**Impact:** This bug prevents the system from correctly extracting manufacturing years from lot numbers, causing lot_years dictionary to be incomplete.

---

### ISSUE 5: VALID_SKUS Defined in 4 Different Locations

**Problem:** The `VALID_SKUS` constant is duplicated across multiple files, risking inconsistency.

**Locations:**
1. `app/eqms/modules/shipstation_sync/parsers.py` - Line 8 (tuple)
2. `app/eqms/modules/rep_traceability/parsers/pdf.py` - Line 85 (set)
3. `app/eqms/modules/rep_traceability/utils.py` - Line 11 (tuple)
4. `app/eqms/modules/rep_traceability/service.py` - Imports from parsers.py

**Fix:**
Create a single source of truth in `app/eqms/constants.py`:

```python
"""
Central constants for the EQMS application.
"""

# Valid SKUs for SILQ products
VALID_SKUS = frozenset({"211810SPT", "211610SPT", "211410SPT"})

# Excluded SKUs (IFUs, non-device items)
EXCLUDED_SKUS = frozenset({"SLQ-4007", "NRE", "IFU"})

# Item code to SKU mapping
ITEM_CODE_TO_SKU = {
    '21400101003': '211410SPT',
    '21400101004': '211410SPT',
    '21600101003': '211610SPT',
    '21600101004': '211610SPT',
    '21800101003': '211810SPT',
    '21800101004': '211810SPT',
    '211410SPT': '211410SPT',
    '211610SPT': '211610SPT',
    '211810SPT': '211810SPT',
}
```

Then update all files to import from this central location:
```python
from app.eqms.constants import VALID_SKUS, EXCLUDED_SKUS, ITEM_CODE_TO_SKU
```

---

### ISSUE 6: PDF Attachment Query in Backfill Too Restrictive

**Problem:** The backfill script only looks for `pdf_type == "sales_order_page"` attachments. Many PDFs may have different types.

**File:** `scripts/backfill_customer_addresses.py`

**Current:**
```python
attachment = (
    s.query(OrderPdfAttachment)
    .filter(OrderPdfAttachment.sales_order_id == first_order.id)
    .filter(OrderPdfAttachment.pdf_type == "sales_order_page")
    .first()
)
```

**Fix:**
```python
# Try sales_order_page first (most reliable), then any PDF
attachment = (
    s.query(OrderPdfAttachment)
    .filter(OrderPdfAttachment.sales_order_id == first_order.id)
    .filter(OrderPdfAttachment.pdf_type == "sales_order_page")
    .first()
)
if not attachment:
    # Fallback to any PDF attachment
    attachment = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.sales_order_id == first_order.id)
        .order_by(OrderPdfAttachment.uploaded_at.asc())
        .first()
    )
```

---

### ISSUE 7: Deprecated `datetime.utcnow()` Usage

**Problem:** Python 3.12+ deprecates `datetime.utcnow()`. The codebase uses it extensively (85+ occurrences).

**Current:**
```python
from datetime import datetime
now = datetime.utcnow()  # Deprecated, returns naive datetime
```

**Fix - Create helper function:**
```python
# app/eqms/utils.py
from datetime import datetime, timezone

def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)

def utcnow_naive() -> datetime:
    """Return current UTC time as naive datetime (for DB compatibility)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
```

Then replace all `datetime.utcnow()` calls:
```python
from app.eqms.utils import utcnow_naive
# ...
now = utcnow_naive()
```

**Low Priority:** This can be addressed incrementally as files are modified.

---

## Medium Priority Issues

### ISSUE 8: Broad Exception Handling Masks Errors

**Problem:** 101 instances of `except Exception` in the codebase. Many swallow errors silently or log without re-raising.

**Example (bad):**
```python
try:
    # complex operation
except Exception as e:
    logger.warning("Something failed: %s", e)
    pass  # Silently continue
```

**Fix Pattern:**
```python
try:
    # complex operation
except SpecificException as e:
    logger.warning("Specific failure: %s", e)
    # Handle gracefully
except Exception as e:
    logger.error("Unexpected error: %s", e, exc_info=True)
    raise  # Re-raise or handle appropriately
```

**High-impact locations to fix first:**
1. `app/eqms/modules/rep_traceability/admin.py` - PDF parsing
2. `app/eqms/modules/shipstation_sync/service.py` - API sync
3. `app/eqms/storage.py` - File operations

---

### ISSUE 9: Temp PDF Files May Not Be Cleaned Up

**Problem:** Equipment and Supplier PDF extraction stores temp files but cleanup only happens on successful form submission.

**File:** `app/eqms/modules/equipment/admin.py` (lines 158-178)

**Current:** If user extracts PDF but abandons form, temp file remains in storage.

**Fix - Add cleanup job or TTL:**
```python
# Option 1: Add TTL to session data
session[f"equipment_pdf_{pdf_ref}"] = {
    "filename": secure_filename(file.filename),
    "storage_key": temp_key,
    "raw_text": raw_text,
    "created_at": datetime.utcnow().isoformat(),  # Add timestamp
}

# Option 2: Add cleanup endpoint/job
@bp.delete("/equipment/extract-cleanup/<pdf_ref>")
@require_permission("equipment.upload")
def equipment_cleanup_pdf(pdf_ref: str):
    """Clean up orphaned temp PDF."""
    key = f"equipment_pdf_{pdf_ref}"
    if key in session:
        info = session.pop(key)
        try:
            storage = storage_from_config(current_app.config)
            storage.delete(info["storage_key"])
        except Exception:
            pass
    return jsonify({"success": True})
```

---

### ISSUE 10: Manufacturing Date Parsing Fails for M/D/YYYY Format

**Problem:** The LotLog CSV has dates in `M/D/YYYY` format (e.g., "5/31/2025"), but the parsing tries `mfg_date[:4]` expecting ISO format.

**File:** `app/eqms/modules/shipstation_sync/parsers.py` (lines 219-226)

**Current (broken for M/D/YYYY):**
```python
mfg_date = (str(row.get("Manufacturing Date") or "")).strip()
year_val = None
if mfg_date:
    try:
        year_val = int(mfg_date[:4])  # Assumes YYYY-MM-DD
    except Exception:
        year_val = None
```

**Fix:**
```python
mfg_date = (str(row.get("Manufacturing Date") or "")).strip()
year_val = None
if mfg_date:
    # Try multiple date formats
    # Format: M/D/YYYY (e.g., "5/31/2025")
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", mfg_date)
    if m:
        try:
            year_val = int(m.group(3))
        except Exception:
            pass
    # Format: YYYY-MM-DD
    if not year_val:
        m = re.match(r"(\d{4})-\d{2}-\d{2}", mfg_date)
        if m:
            try:
                year_val = int(m.group(1))
            except Exception:
                pass
```

---

### ISSUE 11: Customer Address Query Uses String Equality Instead of IS NULL

**Problem:** SQLAlchemy `== ""` doesn't behave consistently across databases for NULL vs empty string.

**File:** `scripts/backfill_customer_addresses.py`

**Current:**
```python
.filter((Customer.address1.is_(None)) | (Customer.address1 == ""))
```

**Fix (more robust):**
```python
from sqlalchemy import or_, func

.filter(
    or_(
        Customer.address1.is_(None),
        Customer.address1 == "",
        func.trim(Customer.address1) == "",
    )
)
```

---

### ISSUE 12: Ship To Regex May Match Unintended Sections

**Problem:** The Ship To regex can capture content beyond the actual Ship To block.

**File:** `app/eqms/modules/rep_traceability/parsers/pdf.py`

**Current regex (line 198-202):**
```python
ship_to_match = re.search(
    r"Ship\s*To\s*[:\n](.+?)(?=\n\s*\n|Bill\s+To|Shipping\s+Method|Salesperson:|F\.?O\.?B\.?|TERMS|$)",
    text,
    re.IGNORECASE | re.DOTALL,
)
```

**Fix - Add more terminators:**
```python
ship_to_match = re.search(
    r"Ship\s*To\s*[:\n](.+?)(?=\n\s*\n|Bill\s+To|Sold\s+To|Shipping\s+Method|Salesperson:|F\.?O\.?B\.?|TERMS|P\.?O\.?\s*#|Order\s+Date|Item|Qty|$)",
    text,
    re.IGNORECASE | re.DOTALL,
)
```

---

### ISSUE 13: Minimal Test Coverage

**Problem:** Only smoke tests exist. No unit tests for PDF parsing, customer matching, or lot tracking.

**Recommendation:** Add focused tests for:

1. **PDF Parsing Tests** (`tests/test_pdf_parsing.py`):
```python
def test_parse_bill_to_extracts_address():
    text = """
    BILL TO:
    Acme Hospital
    123 Main Street
    Boston, MA 02101
    """
    result = _parse_bill_to_block(text)
    assert result["bill_to_name"] == "Acme Hospital"
    assert result["bill_to_address1"] == "123 Main Street"
    assert result["bill_to_city"] == "Boston"
    assert result["bill_to_state"] == "MA"
    assert result["bill_to_zip"] == "02101"

def test_parse_ship_to_extracts_contact():
    text = """
    SHIP TO:
    Dr. Jane Smith
    456 Oak Ave Suite 200
    Chicago, IL 60601
    """
    result = _parse_ship_to_block(text)
    assert result["ship_to_name"] == "Dr. Jane Smith"
```

2. **Lot Year Parsing Tests** (`tests/test_lot_parsing.py`):
```python
def test_extract_year_from_mdy_date():
    # Test M/D/YYYY format
    pass

def test_extract_year_from_lot_number():
    # Test SLQ-05012025 -> 2025
    pass
```

---

## Implementation Order

### Phase 1: Critical Fixes (Do First)
1. Fix escaped regex bug in `parsers.py` (Issue 4)
2. Add `_parse_bill_to_block()` function (Issue 2)
3. Update backfill script with new logic (Issues 1, 6, 11)
4. Fix lot tracking fallback for pre-2025 lots (Issue 3)

### Phase 2: High Priority
5. Fix manufacturing date parsing (Issue 10)
6. Consolidate VALID_SKUS (Issue 5)
7. Improve Ship To regex (Issue 12)

### Phase 3: Medium Priority
8. Add temp PDF cleanup (Issue 9)
9. Address deprecated utcnow() (Issue 7)
10. Improve exception handling (Issue 8)
11. Add tests (Issue 13)

---

## Testing Checklist

- [ ] Run backfill script - should find more than 1 customer
- [ ] Verify no duplicate address lines in customer profiles
- [ ] Check sales dashboard shows lots for all SKUs
- [ ] Verify lot year extraction works (check lot_years dict has entries)
- [ ] Test PDF import with sample sales order
- [ ] Verify Bill To and Ship To are parsed separately
- [ ] Run existing tests: `pytest tests/`

---

## Files Modified

| File | Changes |
|------|---------|
| `app/eqms/modules/rep_traceability/parsers/pdf.py` | Add `_parse_bill_to_block()`, update `_parse_silq_sales_order_page()` |
| `app/eqms/modules/rep_traceability/admin.py` | Update `find_or_create_customer` call |
| `app/eqms/modules/rep_traceability/service.py` | Add lot fallback logic |
| `app/eqms/modules/shipstation_sync/parsers.py` | Fix regex escaping, fix date parsing |
| `scripts/backfill_customer_addresses.py` | Complete rewrite with new logic |
| `app/eqms/constants.py` | New file for shared constants |

---

## Notes

- The Bill To vs Ship To distinction is critical for medical device companies where the facility name (billing entity) differs from the delivery recipient
- Contact name from Ship To is typically the person who will receive/use the product
- Always test with real PDF samples before deploying
