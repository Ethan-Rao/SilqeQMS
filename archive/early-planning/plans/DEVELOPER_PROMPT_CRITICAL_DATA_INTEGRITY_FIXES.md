# Developer Prompt: Critical Data Integrity Fixes

**Date:** 2026-01-27  
**Priority:** P0 (Critical - Data Integrity)  
**Scope:** Fix PDF import creating distributions, restore LotLog.csv usage, fix matching logic, remove editorial text. **NO new features - only correctness fixes.**

---

## Executive Summary

This prompt addresses **critical data integrity issues** that are causing duplicate distributions and missing lot numbers. The core problem is that **PDF import is incorrectly creating distributions** when it should ONLY create Sales Orders (for customer information). Additionally, LotLog.csv is not being properly used for lot number normalization, causing "UNKNOWN" lot numbers in the distribution log.

**Key Objectives:**
1. **Stop PDF import from creating distributions** - PDFs should ONLY create Sales Orders
2. **Restore LotLog.csv usage** - Ensure lot numbers are always normalized and corrected
3. **Fix matching logic** - ShipStation distributions must match to Sales Orders (not vice versa)
4. **Remove editorial text** - Clean up home page marketing text
5. **Ensure lot numbers are paramount** - Lot numbers are critical for lot tracking

---

## Part 1: Critical Issue Analysis

### Issue 1: PDF Import Creating Distributions (CRITICAL BUG)

**Problem:** PDF import (`sales_orders_import_pdf_bulk()`) is creating `DistributionLogEntry` records (lines 1903-1937 in `admin.py`). This is **WRONG**.

**Evidence from Distribution Log:**
- Multiple entries with `source="pdf_import"` showing "UNKNOWN" lot numbers
- Duplicate entries for same order (e.g., `0000270` has both `pdf_import` and `ShipStation` entries)
- PDF import entries have incorrect facility names (duplicated, e.g., "Riverside County Regional Medical Center Riverside County Regional Medical Center")

**Root Cause:**
- Code at lines 1885-1937 creates distribution entries for each order line
- This violates the canonical pipeline: **Only ShipStation or Manual Entry can create distributions**

**Correct Behavior:**
- PDF import should **ONLY** create:
  1. `SalesOrder` records (customer information source-of-truth)
  2. `SalesOrderLine` records (SKU/quantity from PDF - for reference only, NOT for distributions)
  3. `OrderPdfAttachment` records (store the PDF)
- PDF import should **NOT** create `DistributionLogEntry` records
- PDF import should **NOT** extract lot numbers (PDFs don't have reliable lot numbers)

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py:1885-1937` (REMOVE distribution creation)

---

### Issue 2: LotLog.csv Not Being Used (CRITICAL)

**Problem:** LotLog.csv exists at `app/eqms/data/LotLog.csv` but lot numbers from PDF imports show "UNKNOWN". ShipStation entries have correct lot numbers, but PDF-created distributions (which shouldn't exist) have "UNKNOWN".

**Root Cause:**
1. PDF import creates distributions with `lot_number="UNKNOWN"` (line 1890)
2. LotLog.csv is only used in ShipStation sync, not in PDF import (which shouldn't create distributions anyway)

**Correct Behavior:**
- LotLog.csv should be used in:
  1. **ShipStation sync** - Normalize and correct lot numbers from ShipStation data
  2. **Manual entry validation** - Warn if lot number doesn't match LotLog
  3. **Display time** - Show corrected lot numbers in UI (already done in some places)

**Files to Verify/Change:**
- `app/eqms/modules/shipstation_sync/service.py` - Verify LotLog is loaded and used
- `app/eqms/modules/shipstation_sync/parsers.py` - Verify `load_lot_log()` is called
- `app/eqms/modules/rep_traceability/admin.py:349` - Verify lot corrections applied in detail view

**LotLog.csv Location:**
- File exists at: `app/eqms/data/LotLog.csv`
- Path resolution: `os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv"`

---

### Issue 3: Matching Logic Incorrect (CRITICAL)

**Problem:** The system should match ShipStation distributions to Sales Orders, but the current logic may be backwards or incomplete.

**Current Behavior (from code):**
- PDF import auto-matches existing unmatched distributions (lines 1861-1872)
- This is correct, but PDF import shouldn't create distributions in the first place

**Correct Behavior:**
1. **ShipStation sync** creates distributions with:
   - `source="shipstation"`
   - `sales_order_id=NULL` (unmatched)
   - Lot numbers from LotLog corrections
   - Order number from ShipStation (may be "SO 0000270" format)

2. **PDF import** creates Sales Orders with:
   - `source="pdf_import"`
   - Customer information (facility name, address)
   - Order number from PDF (may be "0000270" format, without "SO" prefix)

3. **Matching logic** should:
   - Match ShipStation distributions to Sales Orders by:
     - Order number (normalize: "SO 0000270" == "0000270")
     - Address matching (if order number doesn't match)
     - Customer name normalization (if address doesn't match)
   - Update distribution: `sales_order_id = matched_order.id`, `customer_id = matched_order.customer_id`
   - Update customer name in distribution to match Sales Order (canonical customer name)

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py` - Add matching function after PDF import
- `app/eqms/modules/rep_traceability/service.py` - Add matching utility function

---

### Issue 4: Editorial Text on Home Page (MINOR)

**Problem:** Home page (`app/eqms/templates/public/index.html`) has marketing text: "Minimal ISO 13485-aligned platform scaffold: auth, RBAC primitives, audit logging, storage abstraction, and admin shell."

**Required Change:**
- Remove or replace with simple, professional text
- Keep it minimal and functional

**Files to Change:**
- `app/eqms/templates/public/index.html:7`

---

## Part 2: Implementation Plan

### Task 1: Remove Distribution Creation from PDF Import (P0)

**Objective:** PDF import must NOT create distributions. Only Sales Orders and Order Lines.

**File:** `app/eqms/modules/rep_traceability/admin.py`

**Changes Required:**

1. **Remove distribution creation code (lines 1885-1937):**
   ```python
   # DELETE THIS ENTIRE BLOCK:
   # Create order lines AND linked distribution entries
   seen_dist_keys: set[str] = set()
   for line_num, line_data in enumerate(order_data["lines"], start=1):
       sku = line_data["sku"]
       quantity = line_data["quantity"]
       lot_number = line_data.get("lot_number") or "UNKNOWN"
       
       # Create order line
       order_line = SalesOrderLine(...)
       s.add(order_line)
       total_lines += 1
       
       # Create linked distribution entry  <-- DELETE THIS
       dist_external_key = f"pdf:{order_number}:{order_date.isoformat()}:{sku}:{lot_number}"
       if dist_external_key in seen_dist_keys:
           continue
       seen_dist_keys.add(dist_external_key)
       existing_dist = ...
       if not existing_dist:
           dist = DistributionLogEntry(...)  <-- DELETE THIS
           s.add(dist)
           total_distributions += 1
   ```

2. **Keep only Sales Order Line creation:**
   ```python
   # Create order lines (for reference, NOT for distributions)
   for line_num, line_data in enumerate(order_data["lines"], start=1):
       sku = line_data["sku"]
       quantity = line_data["quantity"]
       # Note: lot_number from PDF is unreliable, don't store it in order line
       # Lot numbers come from ShipStation or manual entry only
       
       order_line = SalesOrderLine(
           sales_order_id=sales_order.id,
           sku=sku,
           quantity=quantity,
           lot_number=None,  # PDFs don't have reliable lot numbers
           line_number=line_num,
       )
       s.add(order_line)
       total_lines += 1
   ```

3. **Update audit metadata:**
   ```python
   # Remove "distributions_created" from metadata
   metadata={
       "files_processed": len([f for f in files if f and f.filename]),
       "total_pages": total_pages,
       "orders_created": total_orders,
       "lines_created": total_lines,
       # "distributions_created": total_distributions,  <-- REMOVE
       "skipped_duplicates": skipped_duplicates,
       "unmatched_pages": total_unmatched,
       "total_errors": total_errors,
       "storage_errors": storage_errors,
   }
   ```

4. **Update success message:**
   ```python
   msg = f"Bulk PDF import: {total_pages} pages processed, {total_orders} orders, {total_lines} lines."
   # Remove: ", {total_distributions} distributions"
   ```

5. **Keep auto-matching logic (lines 1861-1872):**
   ```python
   # This is CORRECT - match existing ShipStation distributions to new Sales Order
   unmatched_dists = (
       s.query(DistributionLogEntry)
       .filter(
           DistributionLogEntry.order_number == order_number,
           DistributionLogEntry.sales_order_id.is_(None)
       )
       .all()
   )
   for udist in unmatched_dists:
       udist.sales_order_id = sales_order.id
       udist.customer_id = customer.id  # Use SO's customer (canonical)
       # Update facility_name to match SO's customer (canonical name)
       udist.facility_name = customer.facility_name
   ```

**Acceptance Criteria:**
- [ ] PDF import creates Sales Orders only
- [ ] PDF import creates Sales Order Lines only
- [ ] PDF import does NOT create DistributionLogEntry records
- [ ] PDF import matches existing ShipStation distributions to new Sales Orders
- [ ] No "pdf_import" source distributions in database after fix

---

### Task 2: Ensure LotLog.csv is Loaded and Used (P0)

**Objective:** Verify LotLog.csv is properly loaded in ShipStation sync and used for lot normalization.

**Files to Verify/Change:**
- `app/eqms/modules/shipstation_sync/service.py`
- `app/eqms/modules/shipstation_sync/parsers.py`

**Verification Steps:**

1. **Check LotLog.csv exists:**
   ```python
   # In shipstation_sync/service.py, verify path resolution:
   lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or 
                  os.environ.get("LotLog_Path") or 
                  "app/eqms/data/LotLog.csv").strip()
   
   # Ensure path is relative to project root, not current working directory
   from pathlib import Path
   project_root = Path(__file__).resolve().parents[4]  # Adjust as needed
   lotlog_path = str(project_root / "app" / "eqms" / "data" / "LotLog.csv")
   ```

2. **Verify LotLog is loaded in sync:**
   ```python
   # In shipstation_sync/service.py:sync_shipstation_orders()
   lot_to_sku, lot_corrections = load_lot_log(lotlog_path)
   if not lot_to_sku:
       logger.warning(f"LotLog.csv not found or empty at {lotlog_path}. Lot numbers may not be normalized.")
   ```

3. **Verify lot normalization is applied:**
   ```python
   # In shipstation_sync/service.py, when creating distributions:
   raw_lot = extract_lot(...)  # From ShipStation data
   normalized_lot = normalize_lot(raw_lot)
   corrected_lot = lot_corrections.get(normalized_lot, normalized_lot)
   
   # Use corrected_lot in DistributionLogEntry
   dist = DistributionLogEntry(
       lot_number=corrected_lot,  # Use corrected lot, not raw
       ...
   )
   ```

4. **Add diagnostic endpoint to verify LotLog loading:**
   ```python
   # In shipstation_sync/admin.py, add to diagnostics:
   try:
       lot_to_sku, lot_corrections = load_lot_log(lotlog_path)
       diag_info["lotlog_loaded"] = True
       diag_info["lotlog_entries"] = len(lot_to_sku)
       diag_info["lot_corrections"] = len(lot_corrections)
   except Exception as e:
       diag_info["lotlog_error"] = str(e)
   ```

**Acceptance Criteria:**
- [ ] LotLog.csv is found and loaded in ShipStation sync
- [ ] Lot numbers are normalized using LotLog corrections
- [ ] Diagnostic endpoint shows LotLog is loaded
- [ ] ShipStation distributions have correct lot numbers (not "UNKNOWN")

---

### Task 3: Improve Matching Logic (P0)

**Objective:** After PDF import creates Sales Orders, match existing ShipStation distributions to those Sales Orders.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py` - Add matching function
- `app/eqms/modules/rep_traceability/service.py` - Add matching utility

**Implementation:**

1. **Add matching utility function:**
   ```python
   # In rep_traceability/service.py
   def match_distribution_to_sales_order(
       s,
       distribution: DistributionLogEntry,
       sales_order: SalesOrder,
   ) -> bool:
       """
       Match a ShipStation distribution to a Sales Order.
       Updates distribution with sales_order_id and customer_id.
       Returns True if matched, False otherwise.
       """
       # Already matched?
       if distribution.sales_order_id:
           return False
       
       # Normalize order numbers for comparison
       dist_order = normalize_order_number(distribution.order_number)
       so_order = normalize_order_number(sales_order.order_number)
       
       # Match by order number (primary)
       if dist_order == so_order:
           distribution.sales_order_id = sales_order.id
           distribution.customer_id = sales_order.customer_id
           # Update facility name to match SO's customer (canonical)
           if sales_order.customer:
               distribution.facility_name = sales_order.customer.facility_name
           return True
       
       # Match by address (secondary) - if order numbers don't match
       if distribution.address1 and sales_order.customer:
           dist_addr = normalize_address(distribution.address1, distribution.city, distribution.state, distribution.zip)
           so_addr = normalize_address(sales_order.customer.address1, sales_order.customer.city, sales_order.customer.state, sales_order.customer.zip)
           if dist_addr == so_addr and dist_addr:  # Non-empty match
               distribution.sales_order_id = sales_order.id
               distribution.customer_id = sales_order.customer_id
               distribution.facility_name = sales_order.customer.facility_name
               return True
       
       return False
   
   def normalize_order_number(order_num: str) -> str:
       """Normalize order number for comparison (remove 'SO' prefix, strip whitespace)."""
       if not order_num:
           return ""
       # Remove "SO" prefix if present
       normalized = order_num.strip().upper()
       if normalized.startswith("SO"):
           normalized = normalized[2:].strip()
       # Remove leading zeros? No, keep as-is for now
       return normalized.strip()
   
   def normalize_address(addr1: str, city: str, state: str, zip_code: str) -> str:
       """Normalize address for comparison."""
       parts = [normalize_text(addr1), normalize_text(city), normalize_text(state), normalize_text(zip_code)]
       return " ".join(p for p in parts if p).upper()
   ```

2. **Call matching after PDF import:**
   ```python
   # In sales_orders_import_pdf_bulk(), after creating Sales Order:
   # Auto-match existing unmatched distributions by order_number
   unmatched_dists = (
       s.query(DistributionLogEntry)
       .filter(
           DistributionLogEntry.order_number.like(f"%{order_number}%"),  # Flexible matching
           DistributionLogEntry.sales_order_id.is_(None),
           DistributionLogEntry.source == "shipstation",  # Only match ShipStation distributions
       )
       .all()
   )
   for udist in unmatched_dists:
       if match_distribution_to_sales_order(s, udist, sales_order):
           logger.info(f"Matched distribution {udist.id} to Sales Order {sales_order.id}")
   ```

3. **Add manual matching endpoint (optional, for admin):**
   ```python
   # In rep_traceability/admin.py
   @bp.post("/distribution-log/<int:entry_id>/match-sales-order")
   @require_permission("distribution_log.edit")
   def distribution_log_match_sales_order(entry_id: int):
       """Manually match a distribution to a sales order."""
       s = db_session()
       u = _current_user()
       
       entry = s.get(DistributionLogEntry, entry_id)
       if not entry:
           flash("Distribution entry not found.", "danger")
           return redirect(url_for("rep_traceability.distribution_log_list"))
       
       sales_order_id = request.form.get("sales_order_id")
       if not sales_order_id:
           flash("Please select a sales order.", "danger")
           return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
       
       order = s.get(SalesOrder, int(sales_order_id))
       if not order:
           flash("Sales order not found.", "danger")
           return redirect(url_for("rep_traceability.distribution_log_edit_get", entry_id=entry_id))
       
       from app.eqms.modules.rep_traceability.service import match_distribution_to_sales_order
       if match_distribution_to_sales_order(s, entry, order):
           s.commit()
           flash(f"Matched distribution to Sales Order {order.order_number}.", "success")
       else:
           flash("Could not match distribution to sales order.", "warning")
       
       return redirect(url_for("rep_traceability.distribution_log_list"))
   ```

**Acceptance Criteria:**
- [ ] ShipStation distributions are matched to Sales Orders by order number
- [ ] Customer name in distribution is updated to match Sales Order (canonical)
- [ ] Matching works with "SO 0000270" vs "0000270" format differences
- [ ] Address matching works as fallback
- [ ] Manual matching endpoint works (if implemented)

---

### Task 4: Remove Editorial Text (P1)

**Objective:** Remove marketing/editorial text from home page.

**File:** `app/eqms/templates/public/index.html`

**Change:**
```html
<!-- BEFORE: -->
<p class="muted">
  Minimal ISO 13485-aligned platform scaffold: auth, RBAC primitives, audit logging, storage abstraction, and admin shell.
</p>

<!-- AFTER: -->
<p class="muted">
  Quality Management System
</p>
```

**Acceptance Criteria:**
- [ ] Home page shows simple, professional text
- [ ] No marketing/editorial language

---

## Part 3: Data Cleanup (After Fixes)

### Cleanup Existing Duplicate Distributions

**After implementing fixes, existing duplicate distributions need to be cleaned up:**

1. **Delete all `source="pdf_import"` distributions:**
   ```sql
   -- Run this SQL after fixes are deployed
   DELETE FROM distribution_log_entries WHERE source = 'pdf_import';
   ```

2. **Or create cleanup script:**
   ```python
   # scripts/cleanup_pdf_import_distributions.py
   from app.eqms.db import db_session
   from app.eqms.modules.rep_traceability.models import DistributionLogEntry
   
   s = db_session()
   pdf_import_dists = s.query(DistributionLogEntry).filter(DistributionLogEntry.source == "pdf_import").all()
   count = len(pdf_import_dists)
   for dist in pdf_import_dists:
       s.delete(dist)
   s.commit()
   print(f"Deleted {count} pdf_import distributions")
   ```

**Note:** This cleanup should be done AFTER the fix is deployed, not before.

---

## Part 4: Testing Plan

### Test 1: PDF Import Does Not Create Distributions

**Steps:**
1. Reset data (clean system)
2. Import a Sales Order PDF (`2025_1SOs.pdf`)
3. Check Distribution Log

**Expected:**
- Sales Order created
- Sales Order Lines created
- NO distributions created
- Distribution Log is empty (or only has ShipStation entries)

**Verification:**
```sql
SELECT COUNT(*) FROM distribution_log_entries WHERE source = 'pdf_import';
-- Should be 0
```

---

### Test 2: LotLog.csv is Loaded

**Steps:**
1. Go to `/admin/shipstation/diag`
2. Check LotLog diagnostics

**Expected:**
- `lotlog_loaded: true`
- `lotlog_entries: > 0`
- `lot_corrections: > 0` (if corrections exist)

---

### Test 3: ShipStation Distributions Have Correct Lot Numbers

**Steps:**
1. Run ShipStation sync
2. Check Distribution Log

**Expected:**
- All ShipStation entries have lot numbers (not "UNKNOWN")
- Lot numbers are normalized (e.g., "SLQ-05012025")
- No "UNKNOWN" lot numbers from ShipStation

---

### Test 4: Matching Works

**Steps:**
1. Run ShipStation sync (creates unmatched distributions)
2. Import Sales Order PDF (creates Sales Orders)
3. Check Distribution Log

**Expected:**
- ShipStation distributions are matched to Sales Orders
- Distribution `sales_order_id` is set
- Distribution `customer_id` is set
- Distribution `facility_name` matches Sales Order customer name (canonical)

**Verification:**
```sql
-- Should show matched distributions
SELECT COUNT(*) FROM distribution_log_entries 
WHERE source = 'shipstation' AND sales_order_id IS NOT NULL;

-- Should show unmatched distributions (if any)
SELECT COUNT(*) FROM distribution_log_entries 
WHERE source = 'shipstation' AND sales_order_id IS NULL;
```

---

## Part 5: Files to Change Summary

### Backend Files

1. **`app/eqms/modules/rep_traceability/admin.py`**
   - Remove distribution creation from PDF import (lines 1885-1937)
   - Keep Sales Order and Order Line creation
   - Keep auto-matching logic (improve if needed)
   - Add manual matching endpoint (optional)

2. **`app/eqms/modules/rep_traceability/service.py`**
   - Add `match_distribution_to_sales_order()` function
   - Add `normalize_order_number()` function
   - Add `normalize_address()` function

3. **`app/eqms/modules/shipstation_sync/service.py`**
   - Verify LotLog.csv is loaded
   - Verify lot normalization is applied
   - Add error handling if LotLog not found

4. **`app/eqms/modules/shipstation_sync/admin.py`**
   - Add LotLog diagnostics to diag endpoint

### Frontend Files

1. **`app/eqms/templates/public/index.html`**
   - Remove editorial text (line 7)

### Cleanup Scripts (Optional)

1. **`scripts/cleanup_pdf_import_distributions.py`** (new file)
   - Delete all `source="pdf_import"` distributions

---

## Part 6: Definition of Done

**For Each Task:**
- [ ] Code changes implemented
- [ ] Manual browser verification completed
- [ ] SQL verification queries pass
- [ ] No regressions (existing functionality works)

**Overall Success Criteria:**
- ✅ PDF import does NOT create distributions
- ✅ LotLog.csv is loaded and used in ShipStation sync
- ✅ ShipStation distributions have correct lot numbers (not "UNKNOWN")
- ✅ ShipStation distributions are matched to Sales Orders
- ✅ Customer names in distributions match Sales Order customer names (canonical)
- ✅ No duplicate distributions from PDF import
- ✅ Editorial text removed from home page

---

## Part 7: Critical Rules (MUST ENFORCE)

### Rule 1: Only ShipStation or Manual Entry Can Create Distributions

**Enforcement:**
- PDF import must NOT create `DistributionLogEntry` records
- CSV import can create distributions (this is correct)
- Manual entry can create distributions (this is correct)
- ShipStation sync can create distributions (this is correct)

### Rule 2: Sales Order is Source of Truth for Customer Information ONLY

**Enforcement:**
- Sales Order provides: customer name, address, contact info
- Sales Order does NOT provide: SKU, lot number, quantity (these come from ShipStation or manual entry)
- When distribution is matched to Sales Order, update `customer_id` and `facility_name` from Sales Order

### Rule 3: Lot Numbers are Paramount

**Enforcement:**
- Lot numbers come from:
  1. ShipStation data (with LotLog corrections)
  2. Manual entry (validated against LotLog)
  3. CSV import (validated format)
- Lot numbers are NEVER from PDFs (PDFs don't have reliable lot numbers)
- Lot numbers must be normalized using LotLog.csv corrections
- "UNKNOWN" lot numbers are only acceptable for unmatched distributions temporarily

### Rule 4: Matching Logic

**Enforcement:**
- ShipStation distributions are matched to Sales Orders (not vice versa)
- Matching criteria (in order):
  1. Order number (normalized: "SO 0000270" == "0000270")
  2. Address matching (if order number doesn't match)
  3. Customer name normalization (if address doesn't match)
- After matching, update distribution with Sales Order's customer information

---

## Part 8: Data Reset Sequence (For Ethan)

### After Developer Completes Fixes

**Ethan's Sequence:**

1. **Verify Fixes are Deployed**
   - Check that PDF import no longer creates distributions
   - Check that LotLog.csv is loaded (via diagnostics)

2. **Run Data Reset**
   - Go to `/admin/reset-data`
   - Type "DELETE ALL DATA"
   - Confirm reset
   - Verify all counts = 0

3. **Run ShipStation Sync**
   - Go to `/admin/shipstation`
   - Run sync
   - Verify distributions created with correct lot numbers (not "UNKNOWN")

4. **Import Sales Order PDFs**
   - Go to `/admin/sales-orders/import-pdf`
   - Upload `2025_1SOs.pdf`
   - Verify Sales Orders created
   - Verify NO distributions created
   - Verify ShipStation distributions are matched to Sales Orders

5. **Verify Distribution Log**
   - Go to `/admin/distribution-log`
   - Verify:
     - Only ShipStation (and manual/CSV if any) distributions exist
     - No `pdf_import` source distributions
     - All distributions have lot numbers (not "UNKNOWN")
     - Matched distributions show correct customer names (from Sales Orders)

6. **Verify Sales Dashboard**
   - Go to `/admin/sales-dashboard`
   - Verify lot tracking shows correct lot numbers
   - Verify totals match SQL queries

---

## Part 9: Reference Documents

**Planning Documents:**
- `docs/plans/DEVELOPER_PROMPT_RELIABILITY_AND_USABILITY_ENHANCEMENTS.md`
- `docs/review/SYSTEM_DEBUG_SWEEP_2026_01_27.md`

**System Documentation:**
- `README.md` - Setup guide
- `docs/REP_SYSTEM_MIGRATION_MASTER.md` - Master spec

**LotLog.csv:**
- Location: `app/eqms/data/LotLog.csv`
- Format: CSV with columns: Lot, SKU, Correct Lot Name, Manufacturing Date, Expiration Date, Total Units in Lot

---

**End of Developer Prompt**
