# Phase 2 Developer Prompt: Data Integrity + Canonical Pipeline Enforcement

**Date:** 2026-01-27  
**Priority:** P0 (Critical) + P1 (High) + P2 (Polish)  
**Scope:** Fix ShipStation → Distribution → Sales Order → Customer pipeline, address Phase 1 findings, cleanup. **No new features.**

---

## Project Snapshot

### What's Working (From Phase 1)

- ✅ Customer rebuild script exists and works
- ✅ PDF splitting implemented (single-file route)
- ✅ Distribution-SO auto-matching works
- ✅ Lot tracking reads from Distribution Log (cleaned data)
- ✅ UI readability fixed (`--card-bg` defined)
- ✅ Customer grouping stable (`company_key` algorithm correct)

### What's Broken (Must Fix)

**P0 Critical:**
1. **ShipStation sync creates customers directly** — Should create distributions only, match to Sales Orders, let Sales Orders drive customer creation
2. **Bulk PDF import doesn't split pages** — `sales_orders_import_pdf_bulk()` stores entire PDF, not per-page

**P1 High:**
3. **Customer key edge cases undocumented** — Abbreviations, PO Box, etc. need tests/documentation
4. **No UI for unmatched PDFs** — Unmatched pages stored but not visible/downloadable

**P2 Polish:**
5. **Hardcoded "2025" in import page** — Should be generic
6. **Deprecated `customer_name` field visible** — Should be hidden
7. **Empty `legacy/` directory** — Should be deleted

---

## Canonical Pipeline (Must Enforce)

**Correct Flow:**
```
ShipStation API
    ↓
Distribution Log Entry (clean, normalized)
    ↓
Match to Sales Order (by order_number)
    ↓
Sales Order (source of truth for customer identity)
    ↓
Customer (created/updated from Sales Order ship-to)
    ↓
Dashboard (reads from Distribution Log + Sales Orders)
```

**Current Broken Flow:**
```
ShipStation API
    ↓
Customer created directly from ShipStation ship_to ❌
    ↓
Distribution Log Entry
    ↓
Sales Order (may or may not match)
```

**Fix:** ShipStation sync must **NOT** create customers. It should:
1. Create `DistributionLogEntry` records (clean, normalized)
2. Try to auto-match to existing `SalesOrder` by `order_number`
3. If matched, link distribution to SO; customer comes from SO
4. If unmatched, distribution remains unmatched (admin matches later via PDF upload or manual match)
5. Customers are **only** created/updated from Sales Orders (PDF import, manual entry)

---

## Dependency-Ordered Implementation Plan

### P0-1: Fix ShipStation Sync to Use Canonical Pipeline

**Objective:** ShipStation sync creates distributions only; customers come from Sales Orders (not ShipStation raw data).

**Root Cause:** `_get_customer_from_ship_to()` in `shipstation_sync/service.py:46-64` creates customers directly from ShipStation `ship_to` data. This bypasses the Sales Order → Customer pipeline.

**Files to Change:**
- `app/eqms/modules/shipstation_sync/service.py`

**Step-by-Step Implementation:**

1. **Remove customer creation from ShipStation sync:**
   - Find `_get_customer_from_ship_to()` function (line 46)
   - **Delete or deprecate** this function (or mark as "DO NOT USE")
   - Update `run_sync()` to **not** call `_get_customer_from_ship_to()`

2. **Update distribution creation to NOT set customer_id:**
   - In `run_sync()`, when creating `DistributionLogEntry`:
     - **Do NOT** set `customer_id` directly
     - **Do NOT** call `_get_customer_from_ship_to()`
     - Set `customer_id = None` initially
     - After creating distribution, try to match to existing Sales Order:
       ```python
       # After creating distribution entry:
       if order_number:
           matching_order = (
               s.query(SalesOrder)
               .filter(SalesOrder.order_number == order_number)
               .first()
           )
           if matching_order:
               entry.sales_order_id = matching_order.id
               entry.customer_id = matching_order.customer_id  # Link via SO
       ```

3. **Ensure Sales Order creation happens first (if needed):**
   - ShipStation sync should **optionally** create Sales Orders if they don't exist
   - But Sales Order creation should use Sales Order → Customer pipeline (not ShipStation → Customer)
   - **OR:** ShipStation sync creates distributions only; Sales Orders created separately (PDF import, manual)
   - **Recommendation:** ShipStation sync creates distributions only; admin creates Sales Orders via PDF import or manual entry, then matches distributions

4. **Update customer linking logic:**
   - After distribution is matched to Sales Order, set `distribution.customer_id = sales_order.customer_id`
   - This ensures customer comes from Sales Order (canonical), not ShipStation

**Code Changes:**

**File:** `app/eqms/modules/shipstation_sync/service.py`

**Change 1: Remove customer creation from sync**
```python
# DELETE or comment out _get_customer_from_ship_to() function
# Or mark as deprecated:
# def _get_customer_from_ship_to(...):  # DEPRECATED: Do not use. Customers come from Sales Orders.

# In run_sync(), remove calls to _get_customer_from_ship_to()
# OLD:
# customer = _get_customer_from_ship_to(s, ship_to)
# NEW:
customer = None  # Will be set via Sales Order match
```

**Change 2: Update distribution creation**
```python
# In run_sync(), when creating DistributionLogEntry:
entry = DistributionLogEntry(
    # ... existing fields ...
    customer_id=None,  # Will be set via Sales Order match
    sales_order_id=None,  # Will be set if match found
)

# After creating entry, try to match to Sales Order:
if order_number:
    matching_order = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_number == order_number)
        .first()
    )
    if matching_order:
        entry.sales_order_id = matching_order.id
        entry.customer_id = matching_order.customer_id  # Link via SO
```

**Change 3: Update Sales Order creation (if sync creates SOs)**
```python
# If ShipStation sync creates Sales Orders (optional):
# Use find_or_create_customer() but with Sales Order ship-to data, not ShipStation ship_to
# OR: Don't create Sales Orders in sync; let admin create via PDF import
```

**Migration/Backfill:** None required (logic change only)

**Acceptance Criteria:**
- [ ] ShipStation sync **does not** call `_get_customer_from_ship_to()`
- [ ] Distributions created from ShipStation have `customer_id = None` initially
- [ ] After matching to Sales Order, `distribution.customer_id = sales_order.customer_id`
- [ ] Customers are **only** created from Sales Orders (PDF import, manual entry)
- [ ] ShipStation raw data is **not** used for customer identity

**Regression Checklist:**
- [ ] ShipStation sync still works (creates distributions)
- [ ] Distributions can be matched to Sales Orders
- [ ] Customer database shows correct grouping (from Sales Orders, not ShipStation)

**Ethan's Verification (Browser Only):**
1. Run ShipStation sync (if accessible via admin UI)
2. Go to Distribution Log → Check new entries → Should show `customer_id = NULL` initially (or linked via SO)
3. Match a distribution to a Sales Order → Verify `customer_id` set from SO
4. Go to Customer Database → Verify customers created from Sales Orders (not ShipStation raw data)

---

### P0-2: Fix Bulk PDF Import to Split Pages

**Objective:** `sales_orders_import_pdf_bulk()` should split each PDF into pages (like single-file route does).

**Root Cause:** `sales_orders_import_pdf_bulk()` (line 1361) calls `parse_sales_orders_pdf()` on entire PDF, then stores entire PDF as single attachment. Should split into pages first.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py` (bulk import route)

**Step-by-Step Implementation:**

1. **Update `sales_orders_import_pdf_bulk()` to split pages:**
   ```python
   # Import split function
   from app.eqms.modules.rep_traceability.parsers.pdf import split_pdf_into_pages, parse_sales_orders_pdf
   
   # In sales_orders_import_pdf_bulk():
   for f in files:
       if not f or not f.filename:
           continue
       pdf_bytes = f.read()
       
       # Split PDF into pages
       pages = split_pdf_into_pages(pdf_bytes)
       
       # Process each page individually
       for page_num, page_bytes in pages:
           # Parse this page
           result = parse_sales_orders_pdf(page_bytes)
           
           # Create/find Sales Order from parsed data
           # Store THIS PAGE as attachment (not entire PDF)
           _store_pdf_attachment(
               s,
               pdf_bytes=page_bytes,  # Single page, not entire PDF
               filename=f"{f.filename}_page_{page_num}.pdf",
               pdf_type="sales_order_page",
               sales_order_id=sales_order.id if sales_order else None,
               distribution_entry_id=None,
               user=u,
           )
   ```

2. **Handle unmatched pages:**
   - If page doesn't parse, store as `pdf_type="unmatched"` with `sales_order_id=None`

**Migration/Backfill:** None required (logic change only)

**Acceptance Criteria:**
- [ ] Bulk PDF import splits each file into pages
- [ ] Each page stored as separate `OrderPdfAttachment` record
- [ ] Each page PDF downloadable from Sales Order detail page
- [ ] Unmatched pages stored with `sales_order_id = NULL`

**Regression Checklist:**
- [ ] Bulk import still works (processes multiple files)
- [ ] Single-file import still works (unchanged)
- [ ] Page attachments downloadable

**Ethan's Verification (Browser Only):**
1. Go to Sales Orders → Import PDF → Upload multiple PDFs (bulk)
2. Verify import results show "X pages processed"
3. Open a created Sales Order → Verify PDF attachments show individual pages (not entire bulk file)
4. Download a page → Verify it's a single page PDF

---

### P1-1: Add Customer Key Edge Case Tests + Documentation

**Objective:** Document and test `canonical_customer_key()` edge cases (abbreviations, PO Box, etc.).

**Root Cause:** Edge cases not documented or tested. May cause duplicate customers or incorrect grouping.

**Files to Change:**
- `app/eqms/modules/customer_profiles/utils.py` (add docstring, edge case handling)
- `tests/test_customer_key.py` (new file, unit tests)

**Step-by-Step Implementation:**

1. **Add comprehensive docstring to `canonical_customer_key()`:**
   ```python
   def canonical_customer_key(name: str) -> str:
       """
       Normalize facility name to a stable canonical key for customer deduplication.
       
       Algorithm:
       1. Remove common business suffixes (Inc., LLC, Corp., etc.)
       2. Convert to uppercase
       3. Remove all non-alphanumeric characters
       4. Collapse whitespace
       
       Examples:
       - "Hospital A, Inc." → "HOSPITALA"
       - "123 Main St" → "123MAINST"
       - "St. Joseph Hospital" → "STJOSEPHHOSPITAL"
       
       Edge Cases:
       - Abbreviations (St/Street, Ave/Avenue) → NOT normalized (different keys)
       - PO Box addresses → Included in key if part of name
       - Same facility, different ship-to → Different keys (by design)
       
       Note: This function does NOT handle address normalization.
       For address-based keys, use compute_customer_key_from_sales_order().
       """
   ```

2. **Add edge case normalization (optional enhancement):**
   ```python
   # Add abbreviation normalization (optional):
   abbreviations = {
       r'\bST\b': 'STREET',
       r'\bAVE\b': 'AVENUE',
       r'\bBLVD\b': 'BOULEVARD',
       r'\bRD\b': 'ROAD',
       r'\bDR\b': 'DRIVE',
       r'\bCT\b': 'COURT',
       r'\bLN\b': 'LANE',
   }
   # Apply before removing punctuation
   ```

3. **Create unit tests:**
   ```python
   # tests/test_customer_key.py
   def test_canonical_customer_key_basic():
       assert canonical_customer_key("Hospital A") == "HOSPITALA"
       assert canonical_customer_key("Hospital A, Inc.") == "HOSPITALA"
   
   def test_canonical_customer_key_abbreviations():
       # Currently: "123 Main St" != "123 Main Street"
       # Document this behavior
       assert canonical_customer_key("123 Main St") == "123MAINST"
       assert canonical_customer_key("123 Main Street") == "123MAINSTREET"
   
   def test_canonical_customer_key_po_box():
       # PO Box included if part of name
       assert canonical_customer_key("Hospital PO Box 123") == "HOSPITALPOBOX123"
   ```

**Migration/Backfill:** None required (documentation/tests only)

**Acceptance Criteria:**
- [ ] `canonical_customer_key()` has comprehensive docstring
- [ ] Unit tests cover edge cases (abbreviations, PO Box, suffixes)
- [ ] Edge case behavior documented (what is/isn't normalized)

**Regression Checklist:**
- [ ] Existing customer keys unchanged (tests verify current behavior)
- [ ] Customer deduplication still works

**Ethan's Verification (Browser Only):**
- N/A (code-level tests, no browser verification needed)

---

### P1-2: Add UI to View Unmatched PDFs

**Objective:** Admin can view and download unmatched PDFs (pages that didn't parse or match to Sales Orders).

**Root Cause:** Unmatched PDFs stored in DB (`OrderPdfAttachment` with `sales_order_id = NULL`) but no UI to view them.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py` (add route)
- `app/eqms/templates/admin/sales_orders/list.html` (add filter/section)

**Step-by-Step Implementation:**

**Option A: Add Filter to Sales Orders List (Recommended)**
1. Add filter dropdown: "All Orders" / "Matched" / "Unmatched PDFs"
2. When "Unmatched PDFs" selected, show `OrderPdfAttachment` records where `sales_order_id IS NULL`
3. Display as table: Filename, Upload Date, PDF Type, Download Link

**Option B: Add Separate Section**
1. Add "Unmatched PDFs" section to Sales Orders list page
2. Show list of unmatched attachments with download links

**Implementation (Option A - Filter):**

**Backend:**
```python
@bp.get("/sales-orders/unmatched-pdfs")
@require_permission("sales_orders.view")
def sales_orders_unmatched_pdfs():
    """List unmatched PDF attachments."""
    s = db_session()
    attachments = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.sales_order_id.is_(None))
        .order_by(OrderPdfAttachment.uploaded_at.desc())
        .limit(100)
        .all()
    )
    return render_template(
        "admin/sales_orders/unmatched_pdfs.html",
        attachments=attachments,
    )
```

**Frontend:**
- Add link/button in Sales Orders list: "View Unmatched PDFs"
- Or add filter dropdown in list page

**Migration/Backfill:** None required (UI only)

**Acceptance Criteria:**
- [ ] Route `/admin/sales-orders/unmatched-pdfs` exists
- [ ] Unmatched PDFs listed with filename, upload date, download link
- [ ] Download links work (return PDF files)
- [ ] Unmatched PDFs clearly labeled as "Unmatched" or "Unparsed"

**Regression Checklist:**
- [ ] Sales Orders list still works
- [ ] Matched PDFs still downloadable
- [ ] No broken links

**Ethan's Verification (Browser Only):**
1. Upload bulk PDF with some unmatched pages
2. Go to Sales Orders → Click "View Unmatched PDFs" (or use filter)
3. Verify unmatched PDFs listed
4. Click download → Verify PDF downloads

---

### P2-1: Remove Hardcoded "2025" from Import Page

**Objective:** Remove year reference from import page text.

**Root Cause:** Template has hardcoded "2025" in line 6.

**Files to Change:**
- `app/eqms/templates/admin/sales_orders/import.html`

**Step-by-Step Implementation:**
1. Open `app/eqms/templates/admin/sales_orders/import.html`
2. Find line 6: `<p class="muted">Upload a 2025 Sales Orders PDF...</p>`
3. Change to: `<p class="muted">Upload a Sales Orders PDF to import orders, lines, and linked distributions.</p>`

**Migration/Backfill:** None required (UI text only)

**Acceptance Criteria:**
- [ ] Import page no longer mentions "2025"
- [ ] Text is generic and professional

**Regression Checklist:**
- [ ] Import page still loads
- [ ] Import functionality unchanged

**Ethan's Verification (Browser Only):**
1. Go to Sales Orders → Import PDF
2. Verify page text doesn't mention "2025"

---

### P2-2: Hide Deprecated customer_name Field

**Objective:** Hide deprecated `customer_name` field from distribution edit form (keep in model for data compatibility).

**Root Cause:** Field marked deprecated but still visible in UI.

**Files to Change:**
- `app/eqms/templates/admin/distribution_log/edit.html`

**Step-by-Step Implementation:**
1. Open `app/eqms/templates/admin/distribution_log/edit.html`
2. Find line 93: Field with label "Customer Name (deprecated free-text)"
3. Change input to hidden:
   ```html
   <!-- OLD: -->
   <input name="customer_name" value="..." />
   
   <!-- NEW: -->
   <input type="hidden" name="customer_name" value="{% if entry and entry.customer_name %}{{ entry.customer_name|e }}{% endif %}" />
   ```
4. **OR:** Remove field entirely if backend doesn't require it

**Migration/Backfill:** None required (UI only, field kept in model)

**Acceptance Criteria:**
- [ ] `customer_name` field not visible in edit form
- [ ] Field still submitted (if backend requires it) or removed from form
- [ ] Edit form still works

**Regression Checklist:**
- [ ] Distribution edit form still loads
- [ ] Form submission still works
- [ ] No broken form validation

**Ethan's Verification (Browser Only):**
1. Go to Distribution Log → Edit any entry
2. Verify "Customer Name (deprecated)" field not visible
3. Save form → Verify still works

---

### P2-3: Delete Empty legacy/ Directory

**Objective:** Remove empty `legacy/` directory.

**Root Cause:** Directory exists but is empty; should be cleaned up.

**Files to Delete:**
- `legacy/` (entire directory)

**Step-by-Step Implementation:**
1. Verify directory is empty: `ls legacy/` (should show nothing)
2. Delete: `rm -rf legacy/` (or `git rm -r legacy/` if using Git)

**Migration/Backfill:** None required (deletion only)

**Acceptance Criteria:**
- [ ] `legacy/` directory deleted
- [ ] App still works (no broken references)

**Regression Checklist:**
- [ ] App imports without errors
- [ ] App starts successfully
- [ ] No 404 errors for legacy files

**Ethan's Verification (Browser Only):**
1. After deploy, verify app still works
2. Check that no broken links/imports

---

## Repo Cleanup Punch-List

### Safe to Delete

| Item | What to Remove | Why Safe | How to Confirm Nothing Broke |
|------|----------------|----------|------------------------------|
| `legacy/` directory | Entire directory | Empty, no content | 1. `ls legacy/` → Empty<br>2. `grep -r "legacy" app/` → No references<br>3. Verify app starts |
| `customer_name` field from edit form | Hide or remove from template | Deprecated, kept in model for data | Verify edit form still works |

### Safe to Rename/Refactor

| Item | Current Name | New Name | Why | Risk |
|------|--------------|----------|-----|------|
| `_get_customer_from_ship_to()` | Function name | Mark as deprecated or delete | Should not be used; customers come from SOs | Low (only used in ShipStation sync, which we're fixing) |

### Safe to Migrate (Code Patterns)

| Pattern | Current | Migrate To | Why |
|---------|---------|------------|-----|
| ShipStation → Customer | Direct creation | ShipStation → Distribution → SO → Customer | Enforce canonical pipeline |

---

## Acceptance Criteria (DoD Checklist)

### P0 Critical

- [ ] **P0-1:** ShipStation sync does NOT create customers directly
- [ ] **P0-1:** Distributions from ShipStation have `customer_id = NULL` until matched to SO
- [ ] **P0-1:** After matching to SO, `distribution.customer_id = sales_order.customer_id`
- [ ] **P0-2:** Bulk PDF import splits each file into pages
- [ ] **P0-2:** Each page stored as separate attachment
- [ ] **P0-2:** Each page downloadable from Sales Order detail

### P1 High

- [ ] **P1-1:** `canonical_customer_key()` has comprehensive docstring
- [ ] **P1-1:** Unit tests cover edge cases
- [ ] **P1-2:** Unmatched PDFs visible in UI (filter or separate section)
- [ ] **P1-2:** Unmatched PDFs downloadable

### P2 Polish

- [ ] **P2-1:** Import page doesn't mention "2025"
- [ ] **P2-2:** Deprecated `customer_name` field hidden in edit form
- [ ] **P2-3:** Empty `legacy/` directory deleted

---

## Test Plan

### Browser-Only Verification

**Test 1: ShipStation Sync → Canonical Pipeline**
1. Run ShipStation sync (if accessible via admin UI)
2. Go to Distribution Log → Check new entries
3. **Expected:** Entries have `customer_id = NULL` initially (or linked via SO)
4. Match a distribution to a Sales Order
5. **Expected:** `customer_id` set from `sales_order.customer_id`
6. Go to Customer Database → **Expected:** Customers created from Sales Orders (not ShipStation)

**Test 2: Bulk PDF Import → Page Splitting**
1. Go to Sales Orders → Import PDF → Upload multiple PDFs
2. **Expected:** Import results show "X pages processed"
3. Open a created Sales Order → **Expected:** PDF attachments show individual pages
4. Download a page → **Expected:** Single page PDF (not entire bulk file)

**Test 3: Unmatched PDFs**
1. Upload bulk PDF with unmatched pages
2. Go to Sales Orders → "View Unmatched PDFs" (or filter)
3. **Expected:** Unmatched PDFs listed with download links
4. Click download → **Expected:** PDF downloads

**Test 4: UI Polish**
1. Go to Sales Orders → Import PDF → **Expected:** No "2025" mentioned
2. Go to Distribution Log → Edit entry → **Expected:** No "Customer Name (deprecated)" field visible
3. Verify app still works after `legacy/` deletion

### Optional SQL Verification

```sql
-- Verify ShipStation sync doesn't create customers directly
-- (Check that customers.created_at matches Sales Order creation, not ShipStation sync)
SELECT c.id, c.facility_name, c.created_at, so.created_at as so_created_at
FROM customers c
JOIN sales_orders so ON so.customer_id = c.id
WHERE c.created_at < so.created_at
LIMIT 10;
-- Expected: No rows (customers created with or after SOs)

-- Verify unmatched PDFs exist
SELECT COUNT(*) FROM order_pdf_attachments WHERE sales_order_id IS NULL;
-- Expected: Count > 0 if unmatched PDFs exist
```

---

## Files Likely to Change

**Backend:**
- `app/eqms/modules/shipstation_sync/service.py` (P0-1: remove customer creation)
- `app/eqms/modules/rep_traceability/admin.py` (P0-2: bulk import splitting, P1-2: unmatched PDFs route)
- `app/eqms/modules/customer_profiles/utils.py` (P1-1: docstring)

**Frontend:**
- `app/eqms/templates/admin/sales_orders/import.html` (P2-1: remove "2025")
- `app/eqms/templates/admin/distribution_log/edit.html` (P2-2: hide customer_name)
- `app/eqms/templates/admin/sales_orders/list.html` (P1-2: unmatched PDFs filter/section)
- `app/eqms/templates/admin/sales_orders/unmatched_pdfs.html` (P1-2: new template, if separate page)

**Tests:**
- `tests/test_customer_key.py` (P1-1: new file, unit tests)

**Deletions:**
- `legacy/` directory (P2-3: delete empty folder)

---

## Deployment Notes

### DigitalOcean Constraints

- **Run Command:** `python scripts/start.py` (unchanged)
- **No Release Commands:** All migrations/seed run in `start.py` (already correct)

### Database Changes

- **None** — All fixes are logic/UI changes, no schema migrations

### One-Time Scripts

- None required (all fixes are immediate)

### Environment Variables

- No new env vars required

---

## Summary Checklist

**P0 (Must Do):**
- [ ] P0-1: Fix ShipStation sync to use canonical pipeline (no direct customer creation)
- [ ] P0-2: Fix bulk PDF import to split pages

**P1 (High Priority):**
- [ ] P1-1: Add customer key edge case tests + documentation
- [ ] P1-2: Add UI to view unmatched PDFs

**P2 (Polish):**
- [ ] P2-1: Remove "2025" from import page
- [ ] P2-2: Hide deprecated customer_name field
- [ ] P2-3: Delete empty legacy/ directory

**Verification:**
- [ ] ShipStation sync creates distributions only (not customers)
- [ ] Distributions match to Sales Orders correctly
- [ ] Customers come from Sales Orders (not ShipStation)
- [ ] Bulk PDF import splits pages correctly
- [ ] Unmatched PDFs visible and downloadable
- [ ] UI text professional (no hardcoded years, no deprecated fields)

---

**End of Phase 2 Developer Prompt**
