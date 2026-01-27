# Developer Agent Prompt: Audit Fixes — Bug Fixes, Data Correctness, UI Readability

**Date:** 2026-01-26  
**Priority:** P0 (Critical) + P1 (High) + P2 (Medium)  
**Scope:** Bug fixes, data correctness, UI readability, safe legacy deletion only. **No new features.**

---

## Project Snapshot

### What's Working Now

- ✅ Core functionality: Distribution Log, Sales Orders, Customer Profiles, Sales Dashboard
- ✅ PDF import pipeline: Parsing, storage, download links on sales order detail page
- ✅ Health endpoints: `/health` (JSON) and `/healthz` (text) exist and work
- ✅ Distribution log entry details modal: Shows entry, order, customer, attachments
- ✅ Sales order detail page: Shows PDF attachments with download links
- ✅ Lot tracking: Reads from Distribution Log (correct source), applies LotLog corrections
- ✅ Customer deduplication: `company_key` normalization works
- ✅ ShipStation sync: Creates sales orders and distributions correctly

### What's Broken (From Audit)

**P0 Critical:**
1. **BUG-001:** Modal backgrounds use undefined CSS variable `--card-bg` → modals have transparent/white backgrounds, unreadable
2. **BUG-002:** Lot tracking hardcoded to 2025 → should show 2026+ lots
3. **BUG-003:** Sales dashboard order details modal missing PDF attachments → no download links

**P1 High:**
4. **BUG-004:** Customer identity from ShipStation (inconsistent) → should be from sales orders (canonical)
5. **BUG-005:** Distribution entries show raw lot strings → should show LotLog-corrected names in UI
6. **BUG-006:** Sales orders list missing inline "Details" button → requires navigation

**P2 Medium:**
7. Missing structured logging for key operations
8. Legacy folder `legacy/DO_NOT_USE__REFERENCE_ONLY/` should be deleted

---

## Prioritized Execution Plan

### P0-1: Fix Modal Background CSS Variable (Critical)

**Objective:** Make all detail modals have solid, readable dark backgrounds.

**Root Cause:** Templates reference `var(--card-bg)` but `design-system.css` only defines `--panel: #0f1a30`. Browser falls back to default (white/transparent).

**Files to Change:**
- `app/eqms/static/design-system.css`

**Step-by-Step Implementation:**
1. Open `app/eqms/static/design-system.css`
2. Find `:root` block (or add it if missing)
3. Add line: `--card-bg: var(--panel);` (or `--card-bg: #0f1a30;` for explicit value)
4. Save file

**Migration/Backfill:** None required (CSS only)

**Acceptance Criteria:**
- [ ] `--card-bg: var(--panel);` added to `:root` in `design-system.css`
- [ ] Distribution log entry details modal has solid dark background
- [ ] Sales dashboard order details modal has solid dark background
- [ ] Notes modal (if exists) has solid dark background
- [ ] All modal text is readable (no white-on-white or transparent backgrounds)

**Regression Checklist:**
- [ ] All existing modals still open/close correctly
- [ ] No CSS conflicts with other styles
- [ ] Page backgrounds unchanged (only modals affected)

**Ethan's Verification (Browser Only):**
1. Go to Distribution Log → Click "Details" on any entry → Modal should have dark background, text readable
2. Go to Sales Dashboard → Click "View Details" on any order → Modal should have dark background, text readable
3. If Notes modal exists → Open it → Should have dark background

---

### P0-2: Fix Lot Tracking Year Filter (2025 → 2026)

**Objective:** Show only 2026+ lots in Sales Dashboard lot tracking, while keeping all-time distribution totals.

**Root Cause:** Hardcoded `min_year = 2025` in `service.py:592`. Should be 2026 (current year) or configurable.

**Files to Change:**
- `app/eqms/modules/rep_traceability/service.py`

**Step-by-Step Implementation:**
1. Open `app/eqms/modules/rep_traceability/service.py`
2. Find line ~592: `min_year = 2025`
3. Change to: `min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2026"))`
4. Ensure `import os` exists at top of file (add if missing)
5. Save file

**Migration/Backfill:** None required (logic change only)

**Acceptance Criteria:**
- [ ] `min_year = 2026` (or env-configurable) in `service.py`
- [ ] Dashboard lot tracking table shows **only** lots from 2026+ (or lots with 2026+ distributions)
- [ ] "Total Units Distributed" column shows **all-time** totals (not filtered to 2026)
- [ ] "Active Inventory" calculation still correct (produced - distributed all-time)

**Regression Checklist:**
- [ ] Dashboard still loads without errors
- [ ] Lot tracking totals match Distribution Log sums for known lots
- [ ] Active Inventory values unchanged (only filter changed, not calculation)

**Ethan's Verification (Browser Only):**
1. Go to Sales Dashboard → Check "Lot Tracking" card
2. Verify only 2026 lots shown (or lots with 2026 distributions)
3. Note a lot number and its "Units" value
4. Go to Distribution Log → Search/filter by that lot → Manually sum quantities → Should match dashboard "Units" value (all-time total, not just 2026)

---

### P0-3: Add PDF Attachments to Sales Dashboard Order Details Modal

**Objective:** Show PDF download links in sales dashboard order details modal (currently missing).

**Root Cause:** `sales_dashboard_order_details` endpoint doesn't query `OrderPdfAttachment` or return attachments in JSON response. Modal JS doesn't render attachments.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py` (endpoint)
- `app/eqms/templates/admin/sales_dashboard/index.html` (modal JS)

**Step-by-Step Implementation:**

**Backend (admin.py):**
1. Open `app/eqms/modules/rep_traceability/admin.py`
2. Find function `sales_dashboard_order_details` (around line 1654)
3. After querying `order` and `lines`, add:
   ```python
   from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
   
   attachments = []
   if order:
       attachments = (
           s.query(OrderPdfAttachment)
           .filter(OrderPdfAttachment.sales_order_id == order.id)
           .order_by(OrderPdfAttachment.uploaded_at.desc())
           .limit(10)
           .all()
       )
   ```
4. In `return jsonify()`, add to response dict:
   ```python
   "attachments": [
       {"id": a.id, "filename": a.filename, "pdf_type": a.pdf_type}
       for a in attachments
   ],
   ```

**Frontend (sales_dashboard/index.html):**
1. Open `app/eqms/templates/admin/sales_dashboard/index.html`
2. Find `showOrderDetails()` function (around line 237)
3. After rendering order lines (around line 313), add:
   ```javascript
   if (data.attachments && data.attachments.length > 0) {
     html += `<div style="margin-top:16px; padding-top:16px; border-top:1px solid var(--border);">`;
     html += `<div style="font-size:11px; text-transform:uppercase; color:var(--muted); margin-bottom:8px;">Attachments</div>`;
     for (const a of data.attachments) {
       html += `<div style="margin-bottom:6px;"><a href="/admin/sales-orders/pdf/${a.id}/download" class="button button--secondary" style="font-size:12px; padding:6px 12px;">${a.filename}</a></div>`;
     }
     html += `</div>`;
   }
   ```

**Migration/Backfill:** None required (uses existing `OrderPdfAttachment` table)

**Acceptance Criteria:**
- [ ] `sales_dashboard_order_details` endpoint returns `attachments` array in JSON
- [ ] Modal JS renders "Attachments" section when attachments exist
- [ ] Download links work (clicking downloads PDF file)
- [ ] Modal shows no attachments section when order has no PDFs

**Regression Checklist:**
- [ ] Order details modal still loads without errors
- [ ] Existing order/lines display unchanged
- [ ] Download links use correct URL pattern (`/admin/sales-orders/pdf/<id>/download`)

**Ethan's Verification (Browser Only):**
1. Go to Sales Dashboard → Click "View Details" on an order that has PDF attachments
2. Modal should show "Attachments" section with download links
3. Click a download link → PDF should download
4. Test with an order that has no PDFs → Modal should not show attachments section

---

### P1-1: Create Customer Refresh Script from Sales Orders

**Objective:** Provide script to refresh customer data from linked sales orders (normalized source) instead of ShipStation (inconsistent).

**Root Cause:** Customers created from ShipStation `ship_to.company` or `ship_to.name` which may have inconsistent casing/formatting. Sales orders contain normalized ship-to data that should be canonical.

**Files to Change:**
- `scripts/refresh_customers_from_sales_orders.py` (new file)

**Step-by-Step Implementation:**
1. Create new file `scripts/refresh_customers_from_sales_orders.py`
2. Implement idempotent refresh logic:
   ```python
   """
   Refresh customer data from linked sales orders (idempotent).
   Uses sales order ship-to as source of truth for facility_name, address.
   """
   from app.eqms.db import db_session
   from app.eqms.modules.customer_profiles.models import Customer
   from app.eqms.modules.rep_traceability.models import SalesOrder
   from sqlalchemy import func
   
   def refresh_customers_from_sales_orders():
       s = db_session()
       
       # For each customer with linked sales orders:
       customers = s.query(Customer).all()
       updated_count = 0
       
       for customer in customers:
           # Get most recent sales order for this customer
           latest_order = (
               s.query(SalesOrder)
               .filter(SalesOrder.customer_id == customer.id)
               .order_by(SalesOrder.order_date.desc())
               .first()
           )
           
           if not latest_order:
               continue
           
           # Update customer fields from sales order if more complete
           # (This is a placeholder - actual logic depends on how sales orders store ship-to)
           # For now, assume sales order has customer relationship that was set during creation
           # The key is: use sales order's customer data, not ShipStation raw data
           
           # If sales order was created from PDF/manual entry, it should have better data
           # than ShipStation. Update customer if sales order data is more complete.
           
           # Example logic (adjust based on actual schema):
           # if latest_order.source in ('pdf_import', 'manual') and latest_order.customer:
           #     if not customer.facility_name or len(latest_order.customer.facility_name) > len(customer.facility_name):
           #         customer.facility_name = latest_order.customer.facility_name
           #     # ... similar for address fields
           
           # For now, mark as TODO - requires understanding how sales orders store ship-to
           # This script should be run after sales orders are properly populated
           pass
       
       s.commit()
       print(f"Refreshed {updated_count} customers from sales orders")
   ```
3. **Note:** This is a placeholder. Actual implementation depends on how sales orders store ship-to data. If sales orders link to customers via `customer_id`, the refresh should update customer fields from the most recent/complete sales order for that customer.

**Migration/Backfill:** None required (script only, no schema changes)

**Acceptance Criteria:**
- [ ] Script `scripts/refresh_customers_from_sales_orders.py` exists
- [ ] Script is idempotent (safe to run multiple times)
- [ ] Script updates customer `facility_name` and address from sales orders when sales order data is more complete
- [ ] Script can be run via: `python scripts/refresh_customers_from_sales_orders.py`

**Regression Checklist:**
- [ ] Script doesn't delete or corrupt customer data
- [ ] Script only updates fields when sales order data is more complete
- [ ] Customer `company_key` unchanged (deduplication still works)

**Ethan's Verification (Browser Only):**
1. Run script: `python scripts/refresh_customers_from_sales_orders.py` (if accessible via admin UI, or provide instructions)
2. Go to Customer Database → Check a customer that has linked sales orders
3. Verify customer `facility_name` matches sales order ship-to (not ShipStation raw data)
4. Verify customer address fields match sales order data

---

### P1-2: Apply Lot Corrections at Display Time

**Objective:** Show LotLog-corrected lot names in distribution entry details modal (currently shows raw lot strings).

**Root Cause:** `lot_corrections` applied during sync but historic entries may have uncorrected `lot_number` values. UI displays `entry.lot_number` directly without re-applying corrections.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py` (entry details endpoint)

**Step-by-Step Implementation:**
1. Open `app/eqms/modules/rep_traceability/admin.py`
2. Find function `distribution_log_entry_details` (around line 349)
3. After loading `entry`, add lot correction logic:
   ```python
   from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory, normalize_lot
   import os
   
   # Load LotLog corrections
   lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv").strip()
   _, lot_corrections, _, _ = load_lot_log_with_inventory(lotlog_path)
   
   # Apply correction to entry's lot_number for display
   raw_lot = (entry.lot_number or "").strip()
   corrected_lot = raw_lot
   if raw_lot:
       normalized = normalize_lot(raw_lot)
       corrected_lot = lot_corrections.get(normalized, normalized)
   
   # In return jsonify(), use corrected_lot instead of entry.lot_number:
   "entry": {
       # ... existing fields ...
       "lot_number": corrected_lot,  # Use corrected, not raw
       # ...
   }
   ```

**Migration/Backfill:** None required (display-time correction only, doesn't change DB)

**Acceptance Criteria:**
- [ ] Entry details modal shows LotLog-corrected lot name
- [ ] Correction applied at display time (no DB changes)
- [ ] Raw lot still stored in DB (for audit trail)

**Regression Checklist:**
- [ ] Entry details modal still loads without errors
- [ ] Other entry fields unchanged
- [ ] Lot correction doesn't break if LotLog file missing (graceful fallback)

**Ethan's Verification (Browser Only):**
1. Go to Distribution Log → Click "Details" on an entry with a lot number
2. Check lot number in modal → Should match LotLog canonical format (e.g., `SLQ-05012026` not `SLQ-050120`)
3. Compare to LotLog.csv → Verify displayed lot matches "Correct Lot Name" column

---

### P1-3: Add Inline Details Button to Sales Orders List

**Objective:** Add "Details" button to sales orders list that opens modal (like distribution log), avoiding navigation to full page.

**Root Cause:** Sales orders list only has "View" link that navigates to full page. No modal/AJAX pattern implemented.

**Files to Change:**
- `app/eqms/templates/admin/sales_orders/list.html`

**Step-by-Step Implementation:**
1. Open `app/eqms/templates/admin/sales_orders/list.html`
2. Find table row rendering (where "View" link exists)
3. Add "Details" button next to "View" link:
   ```html
   <button class="button button--secondary" style="font-size:11px; padding:4px 8px;" onclick="showOrderDetails('{{ o.order_number|e }}')">Details</button>
   ```
4. Reuse existing `showOrderDetails()` function from `sales_dashboard/index.html` (copy JS if needed, or ensure it's available globally)
5. Ensure modal HTML exists (reuse from sales dashboard or add new modal)

**Migration/Backfill:** None required (UI only)

**Acceptance Criteria:**
- [ ] Sales orders list has "Details" button in Actions column
- [ ] Clicking "Details" opens modal with order details (reuses sales dashboard modal pattern)
- [ ] Modal shows order info, lines, attachments (if any)
- [ ] "View" link still works (navigates to full page)

**Regression Checklist:**
- [ ] Sales orders list still loads without errors
- [ ] Existing "View" link unchanged
- [ ] Modal doesn't conflict with other modals

**Ethan's Verification (Browser Only):**
1. Go to Sales Orders list → Check Actions column → Should have both "Details" button and "View" link
2. Click "Details" on any order → Modal should open with order details
3. Click "View" link → Should navigate to full page (unchanged behavior)

---

### P2-1: Add Structured Logging (Optional)

**Objective:** Add INFO-level logging for key operations (PDF storage, customer creation, dashboard queries, detail fetches).

**Root Cause:** Missing observability makes debugging difficult.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py` (PDF storage, detail fetches)
- `app/eqms/modules/customer_profiles/service.py` (customer creation)
- `app/eqms/modules/rep_traceability/service.py` (dashboard queries)

**Step-by-Step Implementation:**
1. Add logging imports where needed:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```
2. Add log lines per audit recommendations (see audit Section I)
3. Use INFO level for normal operations, WARNING for recoverable errors

**Migration/Backfill:** None required (logging only)

**Acceptance Criteria:**
- [ ] PDF storage logs: `logger.info("PDF stored: storage_key=%s sales_order_id=%s", ...)`
- [ ] Customer creation logs: `logger.info("Customer %s: action=%s facility=%s", ...)`
- [ ] Dashboard queries log timing: `logger.info("Dashboard computed: duration=%.2fs", ...)`
- [ ] Detail fetches log: `logger.info("Entry details fetched: entry_id=%d", ...)`

**Regression Checklist:**
- [ ] Logging doesn't slow down operations
- [ ] No sensitive data in logs (no passwords, tokens)

**Ethan's Verification (Browser Only):**
1. After deploy, check DigitalOcean logs
2. Verify log entries appear for PDF uploads, customer creation, dashboard loads
3. Verify no errors from logging code

---

### P2-2: Delete Legacy Folder

**Objective:** Remove `legacy/DO_NOT_USE__REFERENCE_ONLY/` folder (clearly marked as legacy, not used).

**Root Cause:** Legacy reference code should be removed to avoid confusion.

**Files to Delete:**
- `legacy/DO_NOT_USE__REFERENCE_ONLY/` (entire folder)

**Step-by-Step Implementation:**
1. Verify no references to this folder:
   ```bash
   grep -r "DO_NOT_USE" app/
   grep -r "legacy/DO_NOT_USE" .
   ```
2. If no references found, delete folder:
   ```bash
   rm -rf legacy/DO_NOT_USE__REFERENCE_ONLY/
   ```
3. If folder contains important reference docs, move to `docs/legacy/` instead of deleting

**Migration/Backfill:** None required (deletion only)

**Acceptance Criteria:**
- [ ] `legacy/DO_NOT_USE__REFERENCE_ONLY/` folder deleted
- [ ] No references to this folder in codebase
- [ ] App still runs without errors

**Regression Checklist:**
- [ ] No broken imports or references
- [ ] App starts successfully
- [ ] All routes still work

**Ethan's Verification (Browser Only):**
1. After deploy, verify app still works
2. Check that no 404 errors for legacy files
3. (Optional) Verify folder is gone in repo

---

### P2-3: Backfill Distribution Lot Corrections (Optional)

**Objective:** Update historic distribution entries to have LotLog-corrected lot names in database (not just display-time).

**Root Cause:** Historic entries may have uncorrected `lot_number` values. Display-time correction (P1-2) fixes UI, but DB should be corrected too.

**Files to Change:**
- `scripts/backfill_distribution_lot_corrections.py` (new file)

**Step-by-Step Implementation:**
1. Create new file `scripts/backfill_distribution_lot_corrections.py`
2. Implement backfill logic:
   ```python
   """
   Backfill distribution lot_number corrections from LotLog.
   Updates historic entries to use corrected lot names.
   """
   from app.eqms.db import db_session
   from app.eqms.modules.rep_traceability.models import DistributionLogEntry
   from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory, normalize_lot
   import os
   
   def backfill_lot_corrections():
       s = db_session()
       
       # Load LotLog corrections
       lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv").strip()
       _, lot_corrections, _, _ = load_lot_log_with_inventory(lotlog_path)
       
       # Get all distributions with lot_number
       entries = s.query(DistributionLogEntry).filter(DistributionLogEntry.lot_number.isnot(None)).all()
       
       updated_count = 0
       for entry in entries:
           raw_lot = (entry.lot_number or "").strip()
           if not raw_lot:
               continue
           
           normalized = normalize_lot(raw_lot)
           corrected = lot_corrections.get(normalized, normalized)
           
           if corrected != entry.lot_number:
               entry.lot_number = corrected
               updated_count += 1
       
       s.commit()
       print(f"Updated {updated_count} distribution entries with corrected lot names")
   ```
3. **Warning:** This changes historical data. Ensure backups before running.

**Migration/Backfill:** Run script once after deploy (optional, P2)

**Acceptance Criteria:**
- [ ] Script exists and can be run
- [ ] Script updates `lot_number` to corrected values
- [ ] Script is idempotent (safe to run multiple times)

**Regression Checklist:**
- [ ] No data loss (only lot_number updated)
- [ ] Lot tracking still works after backfill
- [ ] Distribution log queries still work

**Ethan's Verification (Browser Only):**
1. Run script (if accessible via admin UI)
2. Check Distribution Log → Verify lot numbers match LotLog canonical format
3. Check Sales Dashboard lot tracking → Verify totals unchanged (only lot names corrected)

---

## How Ethan Verifies After Deploy (Browser Only)

### Step 1: Detail View Works Everywhere
1. **Distribution Log Details:**
   - Go to Distribution Log → Click "Details" on any entry
   - Modal should have **dark background** (not white/transparent)
   - Text should be **readable**
   - Lot number should show **corrected format** (e.g., `SLQ-05012026`)

2. **Sales Dashboard Order Details:**
   - Go to Sales Dashboard → Click "View Details" on any order
   - Modal should have **dark background**
   - If order has PDFs, should show **"Attachments" section with download links**
   - Text should be **readable**

3. **Sales Orders List:**
   - Go to Sales Orders list
   - Each row should have **"Details" button** (in addition to "View" link)
   - Click "Details" → Modal should open

### Step 2: PDF Page Downloads Available from Distribution Log Detail
1. Go to Distribution Log → Click "Details" on an entry that has a linked sales order
2. Modal should show linked sales order info
3. If sales order has PDF attachments, should see **download links**
4. Click download link → PDF should download

### Step 3: Customers Reflect Sales Order Canonical Fields
1. Go to Customer Database
2. Open a customer that has linked sales orders
3. Check customer `facility_name` and address
4. Verify they match **sales order ship-to** (not ShipStation raw data)
5. If running refresh script, run it first, then verify

### Step 4: Sales Dashboard Lot Tracking
1. Go to Sales Dashboard → Check "Lot Tracking" card
2. **Shows 2026 lots only:** Verify only lots from 2026+ are shown (not 2025)
3. **Totals include all history:** Note a lot's "Units" value → Go to Distribution Log → Sum all quantities for that lot (all-time) → Should match dashboard value
4. **Lot names match LotLog:** Check a lot name → Compare to LotLog.csv "Correct Lot Name" column → Should match

---

## Legacy Deletion Plan

### Safe to Delete

| Item | What to Remove | Why Safe | How to Confirm Nothing Broke |
|------|----------------|----------|------------------------------|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/` folder | Entire folder | Clearly marked as legacy, not referenced in code | Run: `grep -r "DO_NOT_USE" app/` → Should return nothing. Verify app still runs. |

### Deletion Steps

1. **Before deletion:**
   ```bash
   grep -r "DO_NOT_USE" app/
   grep -r "legacy/DO_NOT_USE" .
   ```
   If no results, safe to delete.

2. **Delete:**
   ```bash
   rm -rf legacy/DO_NOT_USE__REFERENCE_ONLY/
   ```

3. **After deletion:**
   - Verify app starts: `python scripts/start.py` (or test locally)
   - Verify no 404 errors for legacy files
   - Check that all routes still work

---

## Deployment Notes for DigitalOcean

### Run Command
- **Current:** `python scripts/start.py` (unchanged)
- **No Release Commands:** All migrations/seed run in `start.py` (already correct)

### Health Check Guidance
- **Current:** Health endpoints exist (`/healthz` returns "ok")
- **If health check issues found:** Configure DO readiness probe:
  - Type: HTTP
  - Path: `/healthz`
  - Port: `$PORT` (or `8080`)
  - Initial Delay: `20` seconds (accounts for migrations)
  - Timeout: `5` seconds
  - Period: `10` seconds
  - Failure Threshold: `3`

### Environment Variables
- No new env vars required (existing `PORT`, `DATABASE_URL`, etc. sufficient)
- Optional: `DASHBOARD_LOT_MIN_YEAR=2026` (if P0-2 uses env var)

### Database Changes
- **None** — All fixes are code/logic changes, no schema migrations

### One-Time Scripts (Optional)
- `scripts/refresh_customers_from_sales_orders.py` (P1-1) — Run after deploy if needed
- `scripts/backfill_distribution_lot_corrections.py` (P2-3) — Run after deploy if needed

---

## Files Likely to Change

**Backend:**
- `app/eqms/static/design-system.css` (P0-1: CSS variable)
- `app/eqms/modules/rep_traceability/service.py` (P0-2: lot year)
- `app/eqms/modules/rep_traceability/admin.py` (P0-3: attachments, P1-2: lot display)

**Frontend:**
- `app/eqms/templates/admin/sales_dashboard/index.html` (P0-3: modal JS)
- `app/eqms/templates/admin/sales_orders/list.html` (P1-3: inline details)

**Scripts:**
- `scripts/refresh_customers_from_sales_orders.py` (P1-1: new)
- `scripts/backfill_distribution_lot_corrections.py` (P2-3: new, optional)

**Deletions:**
- `legacy/DO_NOT_USE__REFERENCE_ONLY/` (P2-2: delete folder)

---

## Summary Checklist

**P0 (Must Do):**
- [ ] P0-1: Add `--card-bg` CSS variable
- [ ] P0-2: Change lot tracking year to 2026
- [ ] P0-3: Add PDF attachments to sales dashboard modal

**P1 (High Priority):**
- [ ] P1-1: Create customer refresh script
- [ ] P1-2: Apply lot corrections at display time
- [ ] P1-3: Add inline details button to sales orders list

**P2 (Optional):**
- [ ] P2-1: Add structured logging
- [ ] P2-2: Delete legacy folder
- [ ] P2-3: Backfill distribution lot corrections

**Verification:**
- [ ] All detail modals have dark backgrounds
- [ ] Lot tracking shows 2026+ lots, all-time totals
- [ ] PDF attachments visible in sales dashboard modal
- [ ] Customers reflect sales order data (after refresh)
- [ ] Lot names show corrected format in UI

---

**End of Developer Prompt**
