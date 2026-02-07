# SYSTEM AUDIT REPORT
**Date:** 2026-02-02  
**Auditor:** AI Agent

## Executive Summary
The system is generally cohesive and implements strong guardrails (RBAC, CSRF, schema health checks, storage diagnostics), but there are several high-impact reliability gaps in the PDF import pipeline and storage behavior that can cause silent data loss or incomplete Sales Orders. These issues are concentrated in parsing logic and the order in which file storage and database writes occur.

User experience and administrative clarity are also impacted by permission-blind navigation, diagnostics gating behavior, and weak feedback when core reference data (LotLog) is missing. These issues do not necessarily break the app, but they make it appear unreliable or incomplete to end users and admins.

## Critical Issues (Immediate Action Required)

### ISSUE: PDF table parsing drops line items when columns shift

**Location:** `app/eqms/modules/rep_traceability/parsers/pdf.py` (around `_parse_silq_sales_order_page`, lines ~328-377)

**Severity:** CRITICAL

**Symptoms:**  
Sales Orders imported from PDFs can have missing or empty line items. Users see Sales Orders without expected SKUs/Qty, or orders are skipped entirely when a PDF table shifts columns.

**Root Cause:**  
The parser assumes column order `[Item, Description, Qty, Lot]`. When PDFs shift and the quantity column contains a lot number (e.g., `81000412231`), the code skips the entire row:
```python
if _is_lot_number(raw_qty):
    logger.debug("Skipping row: quantity column looks like lot number (%s)", raw_qty)
    continue
```
This discards valid lines instead of recovering by searching for quantity in other columns.

**Correction Strategy:**
1. When the quantity column looks like a lot, attempt to find a numeric quantity in remaining columns.
2. If a lot is detected in the quantity column, treat it as a lot value and continue parsing.
3. Record a parse warning when the row is repaired to keep audits transparent.

**Code Changes Required:**
```python
# Before:
raw_qty = (row[2] or "").strip() if len(row) > 2 else ""
if _is_lot_number(raw_qty):
    logger.debug("Skipping row: quantity column looks like lot number (%s)", raw_qty)
    continue
quantity = _parse_quantity(raw_qty)
lot_number = None
if len(row) > 3:
    lot_number = _normalize_lot(row[3] or "")

# After:
raw_qty = (row[2] or "").strip() if len(row) > 2 else ""
lot_number = None
if _is_lot_number(raw_qty):
    lot_number = _normalize_lot(raw_qty)
    # Look for a numeric qty in later columns
    raw_qty = next((str(c).strip() for c in row[3:] if c and not _is_lot_number(str(c))), "")
quantity = _parse_quantity(raw_qty)
if lot_number is None and len(row) > 3:
    lot_number = _normalize_lot(row[3] or "")
```

**Testing Steps:**
1. Import a PDF where the quantity column contains a lot number (e.g., `SLQ-81000412231`).
2. Confirm the order line is created with correct SKU/Qty and lot is captured.
3. Verify that an order with multi-SKU lines imports all lines.

---

### ISSUE: PDF storage writes can orphan files when DB commit fails

**Location:** `app/eqms/modules/rep_traceability/admin.py` (PDF import routes, lines ~1760-2065 and ~2360-2489)

**Severity:** CRITICAL

**Symptoms:**  
After a DB error during PDF import, files exist in storage but are not linked in the database. Users cannot see or download the PDFs that were uploaded.

**Root Cause:**  
The import flow writes PDF files to storage before database commit succeeds. On commit failure, the DB is rolled back but stored files remain, creating orphaned storage objects and broken audit trails.

**Correction Strategy:**
1. Track stored keys and delete them if the DB commit fails.
2. Alternatively, defer storage writes until after DB commit by using a staging table or temporary storage.
3. Report storage rollback failures in logs.

**Code Changes Required:**
```python
# Before:
_store_pdf_attachment(...)
...
s.commit()

# After:
stored_keys = []
storage_key = _store_pdf_attachment(...)
stored_keys.append(storage_key)
...
try:
    s.commit()
except Exception:
    s.rollback()
    for key in stored_keys:
        storage.delete(key)
    raise
```

**Testing Steps:**
1. Force a DB error during PDF import (e.g., shut down DB or violate a constraint).
2. Confirm no new files remain in `storage/` or S3 after rollback.
3. Re-run import with DB available and verify attachments persist.

## High Priority Issues

### ISSUE: Local storage root depends on process working directory

**Location:** `app/eqms/storage.py` (lines ~104-116)

**Severity:** HIGH

**Symptoms:**  
PDFs appear missing after app restarts or under different run contexts (Gunicorn/Windows services). Downloads fail because files are saved in a different folder than expected.

**Root Cause:**  
`LocalStorage` uses `Path(os.getcwd()) / "storage"`, which changes depending on how the app is started.

**Correction Strategy:**
1. Add `STORAGE_LOCAL_ROOT` config with absolute path.
2. Default to `app.instance_path / "storage"` or project root instead of `cwd`.

**Code Changes Required:**
```python
# Before:
root = Path(os.getcwd()) / "storage"
return LocalStorage(root=root)

# After:
root = Path(config.get("STORAGE_LOCAL_ROOT") or Path(__file__).resolve().parents[2] / "storage")
return LocalStorage(root=root)
```

**Testing Steps:**
1. Start app from a different working directory.
2. Upload a PDF and verify it stores under a fixed root.
3. Restart app and verify PDFs are still downloadable.

---

### ISSUE: Navigation shows modules without permission checks

**Location:** `app/eqms/templates/_layout.html` (lines ~21-36)

**Severity:** HIGH

**Symptoms:**  
Users see navigation links they cannot access, resulting in repeated 403 errors and a poor UX.

**Root Cause:**  
Topbar links are only gated by `g.current_user` and not RBAC permissions.

**Correction Strategy:**
1. Wrap each nav item in `has_perm()` checks.
2. Remove or hide links without permission.

**Code Changes Required:**
```html
<!-- Before -->
{% if g.current_user %}
  <a href="{{ url_for('rep_traceability.tracing_list') }}">Tracing Reports</a>
{% endif %}

<!-- After -->
{% if has_perm("tracing_reports.view") %}
  <a href="{{ url_for('rep_traceability.tracing_list') }}">Tracing Reports</a>
{% endif %}
```

**Testing Steps:**
1. Login as a limited role without `tracing_reports.view`.
2. Confirm the link is hidden and no 403 appears.

---

### ISSUE: Diagnostics 404 for admin-view users in production

**Location:** `app/eqms/admin.py` (`_diagnostics_allowed()`, lines ~29-40)

**Severity:** HIGH

**Symptoms:**  
Admins with `admin.view` but not `admin.edit` see a 404 on `/admin/diagnostics`, which appears broken.

**Root Cause:**  
The diagnostics allowlist requires `admin.edit` in production even though the route itself requires `admin.view`.

**Correction Strategy:**
1. Align diagnostics allowlist with `admin.view`.
2. Keep a separate environment flag if desired for production.

**Code Changes Required:**
```python
# Before:
if user and user.is_active:
    return user_has_permission(user, "admin.edit")

# After:
if user and user.is_active:
    return user_has_permission(user, "admin.view")
```

**Testing Steps:**
1. Login as an admin with `admin.view` only.
2. Confirm `/admin/diagnostics` renders instead of 404.

---

### ISSUE: Lot tracking silently degrades when LotLog.csv missing

**Location:** `app/eqms/modules/rep_traceability/service.py` (lines ~809-933)

**Severity:** HIGH

**Symptoms:**  
Sales dashboard shows "—" and 0s for lot tracking with no warning, making the dashboard appear broken.

**Root Cause:**  
`load_lot_log_with_inventory()` returns empty dicts when the file is missing. The UI does not warn or indicate missing reference data.

**Correction Strategy:**
1. Detect missing/empty lot log and surface a warning banner.
2. Add diagnostics or a status pill in the dashboard.

**Code Changes Required:**
```python
# Before:
lot_to_sku, lot_corrections, lot_inventory, lot_years = load_lot_log_with_inventory(lotlog_path)

# After:
lot_to_sku, lot_corrections, lot_inventory, lot_years = load_lot_log_with_inventory(lotlog_path)
lotlog_missing = not lot_to_sku
```

**Testing Steps:**
1. Temporarily move `LotLog.csv`.
2. Load the dashboard and confirm a warning is displayed.

## Medium Priority Issues

### ISSUE: Quantity cap can downscale legitimate large orders

**Location:** `app/eqms/modules/rep_traceability/parsers/pdf.py` (`_parse_quantity`, lines ~147-160)

**Severity:** MEDIUM

**Symptoms:**  
Large orders may show a quantity of `1` if quantity exceeds `MAX_REASONABLE_QUANTITY` (50,000).

**Root Cause:**  
Quantities above 50k are forced to 1 to avoid lot-number misreads.

**Correction Strategy:**
1. Treat large quantities as parsing errors with a warning, not silently as `1`.
2. Allow higher ceiling if known order sizes exceed 50k.

**Code Changes Required:**
```python
# Before:
if qty > MAX_REASONABLE_QUANTITY:
    logger.warning("Quantity %s exceeds max (%s); treating as lot number", qty, MAX_REASONABLE_QUANTITY)
    return 1

# After:
if qty > MAX_REASONABLE_QUANTITY:
    logger.warning("Quantity %s exceeds max (%s); flagging parse error", qty, MAX_REASONABLE_QUANTITY)
    return 0
```

**Testing Steps:**
1. Import a PDF with quantity > 50,000.
2. Confirm the row surfaces a warning and does not silently become `1`.

---

### ISSUE: PDF import accepts files even when pdfplumber is missing

**Location:** `app/eqms/modules/rep_traceability/admin.py` (`sales_orders_import_pdf_post`, lines ~2350-2430)

**Severity:** MEDIUM

**Symptoms:**  
If pdfplumber is missing, users can still POST to the import endpoint, resulting in unmatched PDFs with no clear reason.

**Root Cause:**  
The GET view hides the form, but the POST route does not explicitly block imports when dependencies are missing.

**Correction Strategy:**
1. Add dependency checks in POST routes similar to bulk import.
2. Return a clear error message and avoid storing files.

**Code Changes Required:**
```python
# Before:
from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf, split_pdf_into_pages

# After:
try:
    from app.eqms.modules.rep_traceability.parsers.pdf import parse_sales_orders_pdf, split_pdf_into_pages
except ImportError:
    flash("PDF parsing libraries are not installed. Please contact support.", "danger")
    return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
```

**Testing Steps:**
1. Uninstall pdfplumber.
2. POST to `/admin/sales-orders/import-pdf`.
3. Confirm a clear error and no storage writes.

## Low Priority Issues

### ISSUE: Unmatched PDF matching only supports order number search

**Location:** `app/eqms/modules/rep_traceability/admin.py` (`sales_orders_match_pdf`, lines ~2290-2344)

**Severity:** LOW

**Symptoms:**  
Admin must manually enter an order number with no search/autocomplete, leading to mismatches or slow workflows.

**Root Cause:**  
The modal only accepts freeform order numbers with no assisted lookup.

**Correction Strategy:**
1. Add autocomplete endpoint for recent orders.
2. Provide a dropdown or typeahead in the modal.

**Code Changes Required:**
```python
# After (new endpoint idea):
@bp.get("/sales-orders/search")
def sales_orders_search():
    ...
```

**Testing Steps:**
1. Open Unmatched PDFs page.
2. Use search to select a Sales Order.
3. Confirm match attaches PDF correctly.

## Legacy Code for Deletion
| File | Lines | Description | Safe to Delete? |
|------|-------|-------------|-----------------|
| `app/eqms/admin.py` | ~35-39 | `module_stub` route for placeholder modules | Yes (if no UI links remain) |
| `app/eqms/templates/admin/module_stub.html` | ~1-12 | Placeholder template for stub modules | Yes |
| `app/eqms/modules/rep_traceability/admin.py` | ~1061-1077 | Redirect-only `/distribution-log/import-pdf` routes | Needs Review |
| `README.txt` | N/A | Duplicate of `README.md` | Yes |
| `eqms.db`, `qa_eval.db` | N/A | Local dev DBs in repo root | Yes (move to `.gitignore`) |
| Root-level PDFs/Docs (`*.pdf`, `*.docx`, `*.xlsx`) | N/A | Sample artifacts in repo root | Needs Review (move to `docs/sample-data/`) |

## Recommended Implementation Order
1. Fix PDF table parsing to prevent dropped line items.
2. Add rollback cleanup for stored PDFs on DB commit failure.
3. Stabilize local storage root with explicit config.
4. Gate topbar navigation by permissions.
5. Add diagnostics access alignment and lot-log warnings.

## Testing Checklist
- [ ] Import PDF with shifted table columns and verify all lines created.
- [ ] Simulate DB failure during PDF import and verify no orphaned storage.
- [ ] Restart app from a different working directory and verify PDFs are retrievable.
- [ ] Verify nav links appear only when RBAC permits.
- [ ] Validate sales dashboard shows a warning when `LotLog.csv` is missing.
- [ ] Verify diagnostics page access for admin-view roles in production.
