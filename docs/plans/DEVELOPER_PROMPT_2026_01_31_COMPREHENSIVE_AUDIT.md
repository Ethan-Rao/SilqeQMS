# DEVELOPER PROMPT: Comprehensive System Audit & Fixes
**Date:** January 31, 2026  
**Priority:** CRITICAL  
**Estimated Issues:** 15+

---

## EXECUTIVE SUMMARY

This audit addresses:
1. **CRITICAL:** 404 error at `/admin/diagnostics` in production
2. **CRITICAL:** PDF import `integer out of range` error (lot numbers parsed as quantities)
3. **HIGH:** Lot tracking fallback for SKUs without 2025+ manufactured lots
4. **HIGH:** New shipping label PDF import functionality
5. **10+ additional issues** identified during system review

---

## CRITICAL ISSUE #1: Admin Diagnostics 404 in Production

### Problem
The `/admin/diagnostics` route returns 404 in production because of a security check.

### Root Cause
```python
# app/eqms/admin.py lines 29-34
def _diagnostics_allowed() -> bool:
    import os
    env = (os.environ.get("ENV") or "development").strip().lower()
    enabled = (os.environ.get("ADMIN_DIAGNOSTICS_ENABLED") or "").strip() == "1"
    return env != "production" or enabled
```

In production (`ENV=production`), this returns `False` unless `ADMIN_DIAGNOSTICS_ENABLED=1` is set.

### Solution Options

**Option A (Recommended):** Set environment variable in DigitalOcean App Platform:
```
ADMIN_DIAGNOSTICS_ENABLED=1
```

**Option B:** Modify the check to always allow admin users (less secure but more convenient):

```python
# app/eqms/admin.py - Replace _diagnostics_allowed()
def _diagnostics_allowed() -> bool:
    """
    Allow diagnostics access if:
    - Not in production, OR
    - ADMIN_DIAGNOSTICS_ENABLED=1 is set, OR
    - User has admin.edit permission (authenticated admin)
    """
    import os
    from flask import g
    
    env = (os.environ.get("ENV") or "development").strip().lower()
    if env != "production":
        return True
    
    enabled = (os.environ.get("ADMIN_DIAGNOSTICS_ENABLED") or "").strip() == "1"
    if enabled:
        return True
    
    # Allow authenticated admins in production
    user = getattr(g, "current_user", None)
    if user and user.is_active:
        from app.eqms.rbac import user_has_permission
        if user_has_permission(user, "admin.edit"):
            return True
    
    return False
```

### Files to Modify
- `app/eqms/admin.py` (if using Option B)
- OR set `ADMIN_DIAGNOSTICS_ENABLED=1` in production environment variables

---

## CRITICAL ISSUE #2: PDF Import Integer Out of Range Error

### Error Message
```
psycopg2.errors.NumericValueOutOfRange: integer out of range
...
'quantity__1': 81000412231, 'sku__1': '211410SPT'
'quantity__2': 81020403231, 'sku__2': '211810SPT'
```

### Root Cause
Lot numbers (e.g., `SLQ-81000412231`) are being parsed as quantities. The values `81000412231` and `81020403231` are lot numbers from the LotLog:

```csv
# From app/eqms/data/LotLog.csv
SLQ-81000412231,211410SPT,...
SLQ-81020403231,211810SPT,...
```

### Why This Happens

1. **Table column misidentification:** The PDF table extraction assumes:
   - Column 0 = item code
   - Column 1 = description  
   - Column 2 = quantity
   - Column 3 = lot number (optional)
   
   But shipping labels/packing slips may have different column layouts.

2. **No quantity validation:** The `_parse_quantity()` function accepts any numeric sequence:

```python
# app/eqms/modules/rep_traceability/parsers/pdf.py lines 146-157
def _parse_quantity(raw_qty: str) -> int:
    s = (raw_qty or "").strip()
    if not s:
        return 1
    match = re.search(r'(\d+)', s)  # Matches ANY digits
    if match:
        try:
            qty = int(match.group(1))
            return qty if qty > 0 else 1  # NO UPPER BOUND CHECK!
        except ValueError:
            pass
    return 1
```

### Solution

**Step 1:** Add validation to `_parse_quantity()` to reject unreasonable values:

```python
# app/eqms/modules/rep_traceability/parsers/pdf.py

MAX_REASONABLE_QUANTITY = 50000  # Silq products ship max ~1000/order

def _parse_quantity(raw_qty: str) -> int:
    """
    Parse quantity from raw string.
    Returns 1 if value is missing, invalid, or unreasonably large.
    """
    s = (raw_qty or "").strip()
    if not s:
        return 1
    
    # Skip if this looks like a lot number (contains lot patterns)
    if re.search(r'SLQ|^\d{8,}$', s, re.IGNORECASE):
        return 1
    
    match = re.search(r'(\d+)', s)
    if match:
        try:
            qty = int(match.group(1))
            # Validate reasonable range
            if qty > MAX_REASONABLE_QUANTITY:
                logger.warning(f"Quantity {qty} exceeds max ({MAX_REASONABLE_QUANTITY}), treating as lot number")
                return 1
            return qty if qty > 0 else 1
        except ValueError:
            pass
    return 1
```

**Step 2:** Add lot number detection before quantity parsing in table extraction:

```python
# app/eqms/modules/rep_traceability/parsers/pdf.py
# In _parse_silq_sales_order_page(), modify table extraction:

def _is_lot_number(value: str) -> bool:
    """Check if a value looks like a lot number."""
    v = (value or "").strip().upper()
    if not v:
        return False
    # SLQ prefix
    if v.startswith("SLQ"):
        return True
    # 8+ digit number (lot codes)
    if re.match(r'^\d{8,}$', v):
        return True
    return False

# Then in the table processing loop:
for table in tables:
    for row in table or []:
        if not row or len(row) < 3:
            continue
        raw_code = (row[0] or "").strip()
        raw_desc = (row[1] or "").strip() if len(row) > 1 else ""
        raw_qty = (row[2] or "").strip() if len(row) > 2 else ""
        
        # Skip if quantity column contains a lot number
        if _is_lot_number(raw_qty):
            logger.debug(f"Skipping row - quantity column contains lot number: {raw_qty}")
            continue
        
        sku = _normalize_sku(raw_code, raw_desc)
        if not sku:
            continue
        quantity = _parse_quantity(raw_qty)
        # ... rest of parsing
```

### Files to Modify
- `app/eqms/modules/rep_traceability/parsers/pdf.py`

---

## HIGH PRIORITY ISSUE #3: Lot Tracking Fallback for SKUs Without 2025+ Lots

### Current Behavior
The sales dashboard displays lot tracking for SKUs with lots manufactured since 2025. For SKUs without 2025+ lots, the fallback logic exists but may not be working correctly.

### Expected Behavior
For any SKU where no lot has been manufactured since 2025, the system should:
1. Find the most recent lot from the LotLog (regardless of year)
2. Display that lot in the "Current Lot" column
3. Show N/A for Total Produced/Distributed/Remaining (since we're not aggregating non-2025 lots)

### Current Code (Already Implemented)
```python
# app/eqms/modules/rep_traceability/service.py lines 900-914
# Find most recent lot per SKU from LotLog (fallback if no 2025+ lots)
sku_most_recent_lot: dict[str, str] = {}
for lot, sku in lot_to_sku.items():
    if not sku or sku not in VALID_SKUS:
        continue
    if not lot.startswith("SLQ-"):
        continue
    lot_year = lot_years.get(lot, 0)
    current_best = sku_most_recent_lot.get(sku)
    if current_best:
        current_best_year = lot_years.get(current_best, 0)
        if lot_year > current_best_year:
            sku_most_recent_lot[sku] = lot
    else:
        sku_most_recent_lot[sku] = lot
```

### Verification Steps
1. Check if LotLog.csv has manufacturing dates for all lots
2. Verify the `lot_years` dict is being populated correctly
3. Test with a SKU that has no 2025+ lots (if one exists)

### Potential Fix (if fallback isn't working)
The issue may be that `lot_years.get(lot, 0)` returns 0 for lots without manufacturing dates, making year comparison unreliable. Fix by also tracking lot ordering by row position:

```python
# app/eqms/modules/rep_traceability/service.py
# Enhanced fallback logic:

# First, build a fallback map with explicit ordering
sku_most_recent_lot: dict[str, tuple[str, int, int]] = {}  # sku -> (lot, year, row_index)

for row_idx, (lot, sku) in enumerate(lot_to_sku.items()):
    if not sku or sku not in VALID_SKUS:
        continue
    if not lot.startswith("SLQ-"):
        continue
    
    lot_year = lot_years.get(lot, 0)
    current = sku_most_recent_lot.get(sku)
    
    if current:
        current_lot, current_year, current_idx = current
        # Prefer higher year, then later row (newer entry)
        if lot_year > current_year or (lot_year == current_year and row_idx > current_idx):
            sku_most_recent_lot[sku] = (lot, lot_year, row_idx)
    else:
        sku_most_recent_lot[sku] = (lot, lot_year, row_idx)

# Then in the lot_tracking loop:
for sku in VALID_SKUS:
    ...
    if sku not in sku_latest_lot:
        fallback = sku_most_recent_lot.get(sku)
        current_lot = fallback[0] if fallback else "—"
    ...
```

### Files to Modify
- `app/eqms/modules/rep_traceability/service.py`

---

## HIGH PRIORITY ISSUE #4: Separate Shipping Label PDF Import

### Requirement
User wants two separate cards on the PDF import page:
1. **Card 1:** Sales Order PDF upload (existing functionality)
2. **Card 2:** Shipping Label PDF upload (new functionality)

### Current State
The current import page at `/admin/sales-orders/import-pdf` handles both in a single upload, but:
- Sales order PDFs create SalesOrder + Customer + OrderLines
- Shipping labels are stored as "delivery_verification" attachments

### Solution

**Step 1:** Update the import template with two separate forms:

```html
<!-- app/eqms/templates/admin/sales_orders/import.html -->
{% extends "_layout.html" %}
{% block title %}Import PDFs{% endblock %}
{% block content %}
<div class="card">
    <h1 style="margin-top:0;">PDF Import</h1>
    <p class="muted">Upload Sales Order PDFs or Shipping Label PDFs to match with existing distributions.</p>
    
    <div style="display:flex; gap:10px; margin-bottom:16px;">
        <a class="button button--secondary" href="{{ url_for('rep_traceability.sales_orders_list') }}">&larr; Back to List</a>
    </div>
</div>

<div style="height: 14px;"></div>

<!-- Sales Order PDF Upload -->
<div class="card">
    {% if pdfplumber_available %}
    <h2 style="margin-top:0;">📄 Sales Order PDFs</h2>
    <p class="muted" style="margin-bottom:12px;">Upload Sales Order PDFs to create orders, customers, and order lines.</p>
    <form class="form" method="post" action="{{ url_for('rep_traceability.sales_orders_import_pdf_bulk') }}" enctype="multipart/form-data" id="sales-order-form">
        <div>
            <div class="label">Select Sales Order PDF Files</div>
            <input type="file" name="pdf_files" accept=".pdf,application/pdf" multiple required />
            <p class="muted" style="margin-top:4px; font-size:12px;">
                Max 10MB per file, 50MB total. Pages with "SALES ORDER" header will be processed.
            </p>
        </div>
        <button class="button" type="submit" id="sales-order-btn">Import Sales Orders</button>
    </form>
    {% else %}
    <div class="alert alert--danger">
        <strong>Error:</strong> PDF parsing library (pdfplumber) is not installed.
    </div>
    {% endif %}
</div>

<div style="height: 14px;"></div>

<!-- Shipping Label PDF Upload -->
<div class="card">
    {% if pdfplumber_available %}
    <h2 style="margin-top:0;">📦 Shipping Label PDFs (Packing Slips)</h2>
    <p class="muted" style="margin-bottom:12px;">Upload shipping labels to match with existing distributions via tracking number or address.</p>
    <form class="form" method="post" action="{{ url_for('rep_traceability.shipping_labels_import_bulk') }}" enctype="multipart/form-data" id="shipping-label-form">
        <div>
            <div class="label">Select Shipping Label PDF Files</div>
            <input type="file" name="pdf_files" accept=".pdf,application/pdf" multiple required />
            <p class="muted" style="margin-top:4px; font-size:12px;">
                Max 10MB per file, 50MB total. Labels are matched by tracking number or ship-to address.
            </p>
        </div>
        <button class="button" type="submit" id="shipping-label-btn">Import Shipping Labels</button>
    </form>
    {% else %}
    <div class="alert alert--danger">
        <strong>Error:</strong> PDF parsing library (pdfplumber) is not installed.
    </div>
    {% endif %}
</div>

<div style="height: 14px;"></div>

<div class="card">
    <h3 style="margin-top:0;">How It Works</h3>
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
        <div>
            <h4 style="margin-top:0; color:var(--primary);">Sales Orders</h4>
            <ul style="margin:8px 0; padding-left:20px;">
                <li>Creates Customer profiles</li>
                <li>Creates Sales Orders</li>
                <li>Creates Order Lines with SKU/Qty</li>
                <li>Auto-matches to ShipStation distributions</li>
            </ul>
        </div>
        <div>
            <h4 style="margin-top:0; color:var(--success);">Shipping Labels</h4>
            <ul style="margin:8px 0; padding-left:20px;">
                <li>Extracts tracking numbers</li>
                <li>Matches to existing distributions</li>
                <li>Stores as delivery verification</li>
                <li>Does NOT create distributions</li>
            </ul>
        </div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    ['sales-order-form', 'shipping-label-form'].forEach(function(formId) {
        var form = document.getElementById(formId);
        if (form) {
            form.addEventListener('submit', function(e) {
                var btn = form.querySelector('button[type="submit"]');
                if (btn) {
                    btn.disabled = true;
                    btn.textContent = 'Uploading...';
                }
            });
        }
    });
});
</script>
{% endblock %}
```

**Step 2:** Create dedicated shipping label import route:

```python
# app/eqms/modules/rep_traceability/admin.py
# Add new route for shipping label imports

@bp.post("/shipping-labels/import-bulk")
@require_permission("sales_orders.import")
def shipping_labels_import_bulk():
    """
    Bulk shipping label PDF import.
    
    Extracts tracking numbers and matches to existing distributions.
    Does NOT create distributions, orders, or customers.
    """
    from werkzeug.datastructures import FileStorage
    from app.eqms.modules.rep_traceability.parsers.pdf import (
        parse_sales_orders_pdf,
        split_pdf_into_pages,
    )
    
    s = db_session()
    u = _current_user()
    
    files = request.files.getlist("pdf_files")
    if not files:
        flash("No files uploaded.", "warning")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    total_pages = 0
    total_matched = 0
    total_unmatched = 0
    storage_errors = 0
    
    try:
        for f in files:
            if not f or not f.filename:
                continue
            
            original_filename = secure_filename(f.filename) or "label.pdf"
            pdf_bytes = f.read()
            
            if len(pdf_bytes) > 10 * 1024 * 1024:  # 10MB limit
                flash(f"File {original_filename} exceeds 10MB limit, skipped.", "warning")
                continue
            
            # Split into pages
            try:
                pages = split_pdf_into_pages(pdf_bytes)
            except Exception as e:
                logger.error(f"Failed to split PDF {original_filename}: {e}")
                continue
            
            total_pages += len(pages)
            
            for page_num, page_bytes in pages:
                try:
                    result = parse_sales_orders_pdf(page_bytes)
                except Exception as e:
                    logger.error(f"Failed to parse page {page_num}: {e}")
                    continue
                
                # Extract label data (tracking number, ship-to)
                if result.labels:
                    for label in result.labels:
                        matched_entry = _match_distribution_for_label(
                            s,
                            tracking_number=label.get("tracking_number"),
                            ship_to=label.get("ship_to"),
                        )
                        
                        try:
                            _store_pdf_attachment(
                                s,
                                pdf_bytes=page_bytes,
                                filename=f"{original_filename}_page_{page_num}.pdf",
                                pdf_type="shipping_label",
                                sales_order_id=matched_entry.sales_order_id if matched_entry else None,
                                distribution_entry_id=matched_entry.id if matched_entry else None,
                                user=u,
                            )
                            if matched_entry:
                                total_matched += 1
                            else:
                                total_unmatched += 1
                        except Exception as e:
                            logger.error(f"Storage error: {e}")
                            storage_errors += 1
                else:
                    # Try to extract from non-label pages too
                    from app.eqms.modules.rep_traceability.parsers.pdf import _extract_tracking_number, _extract_ship_to_name, _normalize_text
                    text = _normalize_text(page_bytes.decode('utf-8', errors='ignore'))
                    tracking = _extract_tracking_number(text)
                    ship_to = _extract_ship_to_name(text)
                    
                    if tracking or ship_to:
                        matched_entry = _match_distribution_for_label(
                            s,
                            tracking_number=tracking,
                            ship_to=ship_to,
                        )
                        try:
                            _store_pdf_attachment(
                                s,
                                pdf_bytes=page_bytes,
                                filename=f"{original_filename}_page_{page_num}.pdf",
                                pdf_type="shipping_label",
                                sales_order_id=matched_entry.sales_order_id if matched_entry else None,
                                distribution_entry_id=matched_entry.id if matched_entry else None,
                                user=u,
                            )
                            if matched_entry:
                                total_matched += 1
                            else:
                                total_unmatched += 1
                        except Exception as e:
                            logger.error(f"Storage error: {e}")
                            storage_errors += 1
                    else:
                        # Store as unmatched
                        try:
                            _store_pdf_attachment(
                                s,
                                pdf_bytes=page_bytes,
                                filename=f"{original_filename}_page_{page_num}.pdf",
                                pdf_type="unmatched",
                                sales_order_id=None,
                                distribution_entry_id=None,
                                user=u,
                            )
                            total_unmatched += 1
                        except Exception:
                            storage_errors += 1
        
        # Audit event
        from app.eqms.audit import record_event
        record_event(
            s,
            actor=u,
            action="shipping_labels.import_bulk",
            entity_type="OrderPdfAttachment",
            entity_id="shipping_label_import",
            metadata={
                "files_processed": len([f for f in files if f and f.filename]),
                "total_pages": total_pages,
                "matched": total_matched,
                "unmatched": total_unmatched,
                "storage_errors": storage_errors,
            },
        )
        
        s.commit()
        
        msg = f"Shipping label import: {total_pages} pages processed."
        if total_matched:
            msg += f" {total_matched} matched to distributions."
        if total_unmatched:
            msg += f" {total_unmatched} unmatched (stored for review)."
        
        flash_category = "success" if storage_errors == 0 else "warning"
        if storage_errors:
            msg += f" WARNING: {storage_errors} storage errors."
        
        flash(msg, flash_category)
        
    except Exception as e:
        logger.error(f"Shipping label import failed: {e}", exc_info=True)
        s.rollback()
        flash(f"Import failed: {str(e)}", "danger")
    
    return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
```

### Files to Modify
- `app/eqms/templates/admin/sales_orders/import.html`
- `app/eqms/modules/rep_traceability/admin.py`

---

## ADDITIONAL ISSUES IDENTIFIED

### ISSUE #5: Packing Slip Parser Enhancement

**Problem:** Current label parser only extracts tracking numbers. The uploaded Packing Slips PDF likely contains:
- Order numbers
- SKU/quantities
- Lot numbers
- Customer addresses

**Solution:** Create a dedicated packing slip parser:

```python
# app/eqms/modules/rep_traceability/parsers/pdf.py

def _parse_packing_slip_page(page, text: str, page_num: int) -> dict[str, Any] | None:
    """
    Parse packing slip/shipping label format.
    
    Expected content:
    - Order number
    - Ship-to address
    - Items with SKU, quantity, lot number
    - Tracking number (may be barcode)
    """
    result = {
        "order_number": None,
        "tracking_number": None,
        "ship_to_name": None,
        "ship_to_address": None,
        "items": [],
    }
    
    # Extract order number
    order_match = re.search(r'(?:Order|PO|SO)\s*#?\s*[:\s]*(\d{4,10})', text, re.IGNORECASE)
    if order_match:
        result["order_number"] = order_match.group(1)
    
    # Extract tracking number
    result["tracking_number"] = _extract_tracking_number(text)
    
    # Extract ship-to
    result["ship_to_name"] = _extract_ship_to_name(text)
    
    # Extract items (SKU + quantity pairs)
    # Pattern: SKU followed by quantity
    item_pattern = re.compile(
        r'(211[468]10SPT|2[14-8]\d{9})\s+.*?(\d{1,4})\s*(?:EA|Each|Units?)?',
        re.IGNORECASE
    )
    for match in item_pattern.finditer(text):
        sku = _normalize_sku(match.group(1), "")
        qty_str = match.group(2)
        if sku:
            qty = _parse_quantity(qty_str)
            if qty <= 10000:  # Sanity check
                result["items"].append({"sku": sku, "quantity": qty})
    
    # Only return if we found useful data
    if result["order_number"] or result["tracking_number"] or result["items"]:
        return result
    return None
```

### ISSUE #6: Account Management Templates Missing Styles

**Problem:** The account management pages exist but may lack consistent styling.

**Fix:** Verify templates follow design system. Already implemented at:
- `app/eqms/templates/admin/accounts/list.html`
- `app/eqms/templates/admin/accounts/new.html`
- `app/eqms/templates/admin/accounts/detail.html`

### ISSUE #7: Missing Input Validation on Password Fields

**Problem:** The account creation form should have client-side password validation.

**Fix:** Add JavaScript validation:

```html
<!-- app/eqms/templates/admin/accounts/new.html -->
<script>
document.querySelector('form').addEventListener('submit', function(e) {
    var pwd = document.querySelector('input[name="password"]').value;
    var confirm = document.querySelector('input[name="password_confirm"]').value;
    
    if (pwd.length < 8) {
        e.preventDefault();
        alert('Password must be at least 8 characters.');
        return;
    }
    if (pwd !== confirm) {
        e.preventDefault();
        alert('Passwords do not match.');
        return;
    }
});
</script>
```

### ISSUE #8: Hardcoded Lot Year Threshold

**Problem:** The `min_year = 2025` threshold is hardcoded in multiple places.

**Solution:** Already uses environment variable `DASHBOARD_LOT_MIN_YEAR`, but verify it's used consistently:

```python
min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2025"))
```

### ISSUE #9: Missing Error Boundary in Sales Dashboard

**Problem:** If `compute_sales_dashboard()` fails, the entire page crashes.

**Solution:** Add try/except wrapper in the route:

```python
# app/eqms/modules/rep_traceability/admin.py

@bp.get("/sales-dashboard")
@require_permission("reports.view")
def sales_dashboard():
    s = db_session()
    start_date_str = request.args.get("start_date", "")
    start_date = _parse_date(start_date_str) if start_date_str else None
    
    try:
        data = compute_sales_dashboard(s, start_date=start_date)
    except Exception as e:
        logger.error(f"Sales dashboard computation failed: {e}", exc_info=True)
        data = {
            "stats": {"total_orders": 0, "total_units_all_time": 0, "total_units_window": 0, 
                      "total_customers": 0, "first_time_customers": 0, "repeat_customers": 0},
            "sku_breakdown": [],
            "lot_tracking": [],
            "lot_min_year": 2025,
            "recent_orders_new": [],
            "recent_orders_repeat": [],
        }
        flash("Error loading dashboard data. Some statistics may be incomplete.", "danger")
    
    return render_template(...)
```

### ISSUE #10: LotLog Path Fallback Chain

**Problem:** Multiple environment variable names for LotLog path.

**Current:**
```python
lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv").strip()
```

**Recommendation:** Standardize on one name and document it:
- Use `LOTLOG_PATH` as the primary env var
- Keep backward compatibility for `SHIPSTATION_LOTLOG_PATH`

### ISSUE #11: PDF Parser Logging Too Verbose

**Problem:** The PDF parser logs every page preview, which can flood logs.

**Solution:** Reduce log level for routine operations:

```python
# Change INFO to DEBUG for routine logs
logger.debug("PDF page %s: text_length=%s preview=%s", page_num, len(text), text[:100])
```

### ISSUE #12: Missing Index on `order_number` Column

**Problem:** Queries filtering by `order_number` may be slow without an index.

**Solution:** Add migration for index:

```python
# migrations/versions/xxx_add_order_number_indexes.py
def upgrade():
    op.create_index('ix_distribution_log_entries_order_number', 'distribution_log_entries', ['order_number'])
    op.create_index('ix_sales_orders_order_number', 'sales_orders', ['order_number'])

def downgrade():
    op.drop_index('ix_distribution_log_entries_order_number')
    op.drop_index('ix_sales_orders_order_number')
```

### ISSUE #13: Session Lifetime Confirmation

**Problem:** Session lifetime is set to 8 hours, but should verify it's working correctly.

**Current (Correct):**
```python
# app/eqms/__init__.py
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True
```

### ISSUE #14: CSRF Token for AJAX Requests

**Problem:** Some AJAX forms may not include CSRF token properly.

**Solution:** Ensure all fetch/AJAX calls include the token:

```javascript
// Standard pattern for all fetch POST requests
const csrfToken = "{{ csrf_token }}";
fetch(url, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,  // Include in header
    },
    body: JSON.stringify(data),
});
```

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (Deploy Immediately)
- [ ] Set `ADMIN_DIAGNOSTICS_ENABLED=1` in production environment OR update `_diagnostics_allowed()`
- [ ] Fix `_parse_quantity()` to reject lot numbers (values > 50000)
- [ ] Add `_is_lot_number()` helper function
- [ ] Update table parsing to skip lot number columns

### Phase 2: High Priority
- [ ] Verify lot tracking fallback is working for SKUs without 2025+ lots
- [ ] Update PDF import template with two separate cards
- [ ] Create `/shipping-labels/import-bulk` route
- [ ] Test shipping label import with Packing Slips PDF

### Phase 3: Medium Priority
- [ ] Add error boundary to sales dashboard route
- [ ] Reduce PDF parser logging verbosity
- [ ] Add database indexes for `order_number` columns
- [ ] Add client-side password validation

### Phase 4: Cleanup
- [ ] Standardize `LOTLOG_PATH` environment variable
- [ ] Review all AJAX forms for CSRF token inclusion
- [ ] Add packing slip parser enhancement (optional)

---

## TESTING CHECKLIST

### After Critical Fixes
1. **Admin Diagnostics:**
   - [ ] Navigate to `https://silqeqms.com/admin/diagnostics`
   - [ ] Verify page loads without 404

2. **PDF Import:**
   - [ ] Upload a Sales Order PDF with lot numbers in data
   - [ ] Verify no "integer out of range" error
   - [ ] Verify quantities are parsed correctly (reasonable values)

3. **Shipping Label Import:**
   - [ ] Upload Packing Slips PDF
   - [ ] Verify labels are stored and matched where possible
   - [ ] Check unmatched PDFs page for stored labels

4. **Lot Tracking:**
   - [ ] View sales dashboard
   - [ ] For each SKU, verify "Current Lot" shows a valid lot
   - [ ] For SKUs without 2025 lots, verify fallback lot is displayed

---

## FILES MODIFIED SUMMARY

| File | Changes |
|------|---------|
| `app/eqms/admin.py` | Update `_diagnostics_allowed()` |
| `app/eqms/modules/rep_traceability/parsers/pdf.py` | Fix `_parse_quantity()`, add `_is_lot_number()` |
| `app/eqms/modules/rep_traceability/admin.py` | Add shipping label import route, error boundaries |
| `app/eqms/modules/rep_traceability/service.py` | Verify/fix lot tracking fallback |
| `app/eqms/templates/admin/sales_orders/import.html` | Two separate upload cards |
| `migrations/versions/xxx_add_indexes.py` | Add order_number indexes |

---

**END OF AUDIT DOCUMENT**
