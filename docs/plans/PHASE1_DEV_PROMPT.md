# Phase 1 Developer Prompt: Data Integrity Fixes + Customer Rebuild

**Date:** 2026-01-26  
**Priority:** P0 (Critical)  
**Scope:** Fix data integrity, rebuild customer database from Sales Orders, implement bulk PDF splitting, ensure correct matching. **No new features.**

---

## Project Snapshot

### What's Working Now

- ✅ Core models: `SalesOrder`, `DistributionLogEntry`, `Customer`, `OrderPdfAttachment` exist
- ✅ PDF parsing: `parse_sales_orders_pdf()` extracts orders from PDFs
- ✅ PDF storage: `_store_pdf_attachment()` stores PDFs and creates `OrderPdfAttachment` records
- ✅ Distribution-SO linking: `DistributionLogEntry.sales_order_id` FK exists (nullable)
- ✅ Customer deduplication: `canonical_customer_key()` function exists
- ✅ Manual matching: "Match" button exists in distribution log for unmatched entries

### What's Broken (Must Fix)

1. **Customer database broken:** Customers created from ShipStation ship-to (inconsistent), not from Sales Orders (canonical)
2. **Bulk PDF not split:** Bulk PDF upload stores entire file, not individual per-page PDFs
3. **Per-page PDFs not downloadable:** Even if split, individual pages not accessible from distribution details
4. **Customer grouping incorrect:** Distributions matched to SOs with same customer should group correctly, but currently relies on ShipStation data
5. **Unprofessional UI text:** "Source of truth for customer orders and distributions." appears in sales orders list
6. **Detail modals readability:** (If still present) modals may have readability issues

---

## Data Model Decisions

### Current Schema (Verified)

**Sales Orders:**
- `sales_orders` table: `id`, `order_number`, `order_date`, `ship_date`, `customer_id` (FK), `source`, `external_key`, etc.
- `sales_order_lines` table: `id`, `sales_order_id` (FK), `sku`, `quantity`, `lot_number`
- **Relationship:** One `SalesOrder` → Many `SalesOrderLine` (already correct)

**Distribution Log:**
- `distribution_log_entries` table: `id`, `order_number`, `ship_date`, `customer_id` (FK, nullable), `sales_order_id` (FK, nullable), `sku`, `lot_number`, `quantity`, etc.
- **Relationship:** Many `DistributionLogEntry` → One `SalesOrder` (via `sales_order_id` FK) — **already supports 1-to-many**

**PDF Attachments:**
- `order_pdf_attachments` table: `id`, `sales_order_id` (FK, nullable), `distribution_entry_id` (FK, nullable), `storage_key`, `filename`, `pdf_type`, etc.
- **Relationship:** One `SalesOrder` → Many `OrderPdfAttachment` (already correct)
- **Current limitation:** Bulk PDF stored as single file, not split into pages

**Customers:**
- `customers` table: `id`, `company_key` (unique), `facility_name`, `address1`, `city`, `state`, `zip`, etc.
- **Relationship:** One `Customer` → Many `SalesOrder` (via `customer_id` FK) — **already correct**

### Required Changes (No Schema Changes Needed)

**All relationships already support requirements:**
- ✅ One SO → Many distributions (via `distribution_log_entries.sales_order_id`)
- ✅ One SO → Many PDF attachments (via `order_pdf_attachments.sales_order_id`)
- ✅ One Customer → Many SOs (via `sales_orders.customer_id`)

**What needs to change:**
- **PDF splitting logic:** Split bulk PDF into individual pages, store each page as separate `OrderPdfAttachment`
- **Customer rebuild logic:** Recompute customers from Sales Orders (not ShipStation)
- **Matching logic:** Ensure distributions link to SOs correctly
- **UI:** Remove unprofessional text, ensure PDF downloads visible

---

## Customer Rebuild Strategy

### Deterministic Customer Key from Sales Orders

**Strategy:**
1. **Primary key:** If Sales Order has customer number/account number → use that (normalized)
2. **Fallback key:** Normalized `ship_to_name` + `ship_to_address1` + `city` + `state` + `zip` (if all present)
3. **Minimal key:** Normalized `ship_to_name` + `city` + `state` (if address missing)
4. **Last resort:** Normalized `ship_to_name` only

**Implementation:**
- Use existing `canonical_customer_key()` function but **input from Sales Order ship-to fields**, not ShipStation
- Store customer number/account number in `customers` table if available (may need new field or use `company_key` with prefix)

**Customer Key Algorithm:**
```python
def compute_customer_key_from_sales_order(sales_order_data: dict) -> str:
    """
    Compute deterministic customer_key from sales order ship-to data.
    
    Priority:
    1. customer_number (if present in SO) → "CUST:{normalized_number}"
    2. ship_to_name + address1 + city + state + zip → canonical_key(ship_to_name + address1 + city + state + zip)
    3. ship_to_name + city + state → canonical_key(ship_to_name + city + state)
    4. ship_to_name only → canonical_key(ship_to_name)
    """
    from app.eqms.modules.customer_profiles.utils import canonical_customer_key
    
    # Priority 1: Customer number
    if sales_order_data.get("customer_number"):
        normalized = re.sub(r"[^A-Z0-9]+", "", str(sales_order_data["customer_number"]).upper())
        return f"CUST:{normalized}"
    
    # Priority 2: Full address
    name = sales_order_data.get("ship_to_name") or ""
    addr1 = sales_order_data.get("ship_to_address1") or ""
    city = sales_order_data.get("ship_to_city") or ""
    state = sales_order_data.get("ship_to_state") or ""
    zip_code = sales_order_data.get("ship_to_zip") or ""
    
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
```

### Customer Rebuild Process

**Option A: Soft-Delete + Rebuild (Recommended)**
1. Mark existing customers as `is_active = False` (add column if missing, or use `deleted_at` timestamp)
2. Recompute customers from all Sales Orders using new key algorithm
3. Create new customer records with correct `company_key`
4. Update `sales_orders.customer_id` to point to new customers
5. Update `distribution_log_entries.customer_id` via `sales_orders.customer_id`
6. Delete old inactive customers (after verification)

**Option B: In-Place Update (Simpler)**
1. For each existing customer, find all linked Sales Orders
2. Recompute `company_key` from most recent/complete Sales Order
3. If `company_key` changes, update customer record
4. Merge customers with same new `company_key` (keep one, update FKs)

**Recommendation:** **Option B (In-Place Update)** — simpler, less risky, no schema changes needed.

**Idempotent Rebuild Command:**
```python
# scripts/rebuild_customers_from_sales_orders.py

def rebuild_customers_from_sales_orders():
    """
    Rebuild customer database from Sales Orders (idempotent).
    
    Steps:
    1. For each Sales Order, compute customer_key from ship-to data
    2. Find or create customer with that key
    3. Update customer fields from Sales Order (if more complete)
    4. Update sales_orders.customer_id to point to correct customer
    5. Update distribution_log_entries.customer_id via sales_orders.customer_id
    6. Merge duplicate customers (same company_key)
    """
    pass
```

---

## Matching Strategy

### Distribution → Sales Order Matching

**Automatic Matching (Priority Order):**

1. **By Order Number (Exact Match):**
   ```python
   matching_order = (
       s.query(SalesOrder)
       .filter(SalesOrder.order_number == distribution.order_number)
       .first()
   )
   if matching_order:
       distribution.sales_order_id = matching_order.id
   ```

2. **By Order Number + Ship Date (Fuzzy Match):**
   ```python
   matching_order = (
       s.query(SalesOrder)
       .filter(
           SalesOrder.order_number == distribution.order_number,
           SalesOrder.ship_date == distribution.ship_date
       )
       .first()
   )
   ```

3. **By Customer + Ship Date (Fallback):**
   ```python
   # Only if distribution has customer_id and SO has same customer_id
   matching_order = (
       s.query(SalesOrder)
       .filter(
           SalesOrder.customer_id == distribution.customer_id,
           SalesOrder.ship_date == distribution.ship_date,
           SalesOrder.sales_order_id.is_(None)  # Not already matched
       )
       .first()
   )
   ```

**Manual Fallback (Admin "Match" Flow):**
- Current "Match" button in distribution log → Opens modal
- Admin can:
  - Search/select existing Sales Order
  - Upload PDF to create new Sales Order and match
- **Ensure:** After manual match, set `distribution.sales_order_id` and store PDF attachment if uploaded

**When Matching Happens:**
- **On Distribution Creation:** Try to match immediately (manual entry, CSV import, ShipStation sync)
- **On Sales Order Creation:** Try to match existing distributions by `order_number`
- **On Bulk PDF Import:** After creating SOs, try to match distributions
- **On Customer Rebuild:** Re-link distributions via `sales_orders.customer_id`

---

## Bulk PDF Handling

### Current Flow (Broken)

**Current:** `sales_orders_import_pdf_bulk()` (line 1361):
- Uploads bulk PDF file
- Parses entire PDF (may have multiple pages/orders)
- Creates Sales Orders from parsed data
- Stores **entire PDF file** as single attachment

**Problem:** Cannot download individual page for a specific Sales Order.

### Required Flow (Fixed)

**Step 1: Split PDF into Pages**
```python
import pdfplumber
import io

def split_pdf_into_pages(pdf_bytes: bytes) -> list[bytes]:
    """Split PDF into individual page bytes."""
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num in range(len(pdf.pages)):
            # Extract single page as new PDF
            # (pdfplumber doesn't support this directly; use PyPDF2 or similar)
            # For now, store page text and recreate PDF, or use PyPDF2
            pass
    return pages
```

**Step 2: Parse Each Page Individually**
- For each page, call `parse_sales_orders_pdf(page_bytes)` (or page-specific parser)
- Extract order number, ship-to, items from that page only

**Step 3: Create/Update Sales Order**
- For each parsed page, create or find existing Sales Order
- Store **that specific page** as `OrderPdfAttachment` linked to that Sales Order

**Step 4: Store Per-Page PDFs**
```python
# For each page:
storage_key = f"sales_orders/{sales_order_id}/pdfs/page_{page_num}_{timestamp}_{filename}"
_store_pdf_attachment(
    s,
    pdf_bytes=page_bytes,
    filename=f"{filename}_page_{page_num}.pdf",
    pdf_type="sales_order_page",
    sales_order_id=sales_order.id,
    distribution_entry_id=None,
    user=u,
)
```

**Step 5: Handle Unmatched Pages**
- If page doesn't parse (no order number, invalid format), store as `OrderPdfAttachment` with `sales_order_id = NULL`
- Mark as `pdf_type = "unmatched"` or `pdf_type = "unparsed"`
- Show in Sales Orders UI as "Unmatched" section

**Implementation Files:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py` — Add `split_pdf_into_pages()` function
- `app/eqms/modules/rep_traceability/admin.py` — Update `sales_orders_import_pdf_bulk()` to split and process per-page

**Dependencies:**
- May need `PyPDF2` or `pypdf` library for page extraction (if `pdfplumber` doesn't support)

---

## UI Requirements

### Distribution Details Must Show SO Link + PDF Download

**Current:** Distribution log entry details modal shows linked sales order info, but PDF download may be missing.

**Required:**
1. **Distribution Details Modal:**
   - Show linked Sales Order (if `sales_order_id` exists)
   - Show **"View PDF"** or **"Download PDF"** button for the specific page PDF
   - If multiple PDFs exist for that SO, show list or most recent

2. **Implementation:**
   - `GET /admin/distribution-log/entry-details/<id>` endpoint already returns order data
   - **Add:** Query `OrderPdfAttachment` for that `sales_order_id`
   - **Add:** Include attachment info in JSON response
   - **Update:** Modal JS to render PDF download link

**Files:**
- `app/eqms/modules/rep_traceability/admin.py` (entry details endpoint)
- `app/eqms/templates/admin/distribution_log/list.html` (modal JS)

### Sales Orders List/Detail Must Show Page Attachment

**Current:** Sales order detail page shows PDF attachments (line 139 in `detail.html`).

**Required:**
- ✅ Already implemented on detail page
- **Verify:** List page modal also shows attachments (already added in previous fixes)
- **Ensure:** "Unmatched" PDFs visible in Sales Orders area (filter or separate section)

### Remove Unprofessional UI Text

**Current:** `app/eqms/templates/admin/sales_orders/list.html:8` has:
```html
<p class="muted" style="margin:0;">Source of truth for customer orders and distributions.</p>
```

**Fix:** Delete this line.

**Files:**
- `app/eqms/templates/admin/sales_orders/list.html`

---

## Implementation Plan

### P0-1: Implement Bulk PDF Splitting

**Objective:** Split bulk PDF into individual pages, store each page as separate attachment.

**Files:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (add `split_pdf_into_pages()`)
- `app/eqms/modules/rep_traceability/admin.py` (update `sales_orders_import_pdf_bulk()`)

**Steps:**
1. Add PDF splitting function (use `PyPDF2` or `pypdf`):
   ```python
   def split_pdf_into_pages(pdf_bytes: bytes) -> list[tuple[int, bytes]]:
       """Split PDF into (page_num, page_bytes) tuples."""
       from PyPDF2 import PdfReader, PdfWriter
       import io
       
       reader = PdfReader(io.BytesIO(pdf_bytes))
       pages = []
       for page_num in range(len(reader.pages)):
           writer = PdfWriter()
           writer.add_page(reader.pages[page_num])
           page_bytes = io.BytesIO()
           writer.write(page_bytes)
           pages.append((page_num + 1, page_bytes.getvalue()))
       return pages
   ```

2. Update `sales_orders_import_pdf_bulk()`:
   - Split PDF into pages
   - For each page: parse, create/find SO, store page PDF as attachment
   - Handle unmatched pages (store with `sales_order_id = NULL`)

**Acceptance Criteria:**
- [ ] Bulk PDF upload splits into individual pages
- [ ] Each page stored as separate `OrderPdfAttachment` record
- [ ] Each page PDF downloadable from Sales Order detail page
- [ ] Unmatched pages stored and visible in "Unmatched" section

### P0-2: Implement Customer Rebuild from Sales Orders

**Objective:** Rebuild customer database using Sales Orders as source of truth (not ShipStation).

**Files:**
- `scripts/rebuild_customers_from_sales_orders.py` (new)
- `app/eqms/modules/customer_profiles/utils.py` (add `compute_customer_key_from_sales_order()`)
- `app/eqms/modules/customer_profiles/service.py` (update `find_or_create_customer()` to accept SO data)

**Steps:**
1. Add `compute_customer_key_from_sales_order()` function (see algorithm above)
2. Create rebuild script:
   ```python
   def rebuild_customers_from_sales_orders():
       s = db_session()
       
       # For each Sales Order:
       for so in s.query(SalesOrder).all():
           # Extract ship-to data (may need to add fields to SalesOrder model or parse from PDF)
           # Compute customer_key
           # Find or create customer
           # Update customer fields from SO if more complete
           # Update sales_orders.customer_id
       pass
   ```

3. **Note:** May need to add ship-to fields to `SalesOrder` model if not present:
   - `ship_to_name`, `ship_to_address1`, `ship_to_city`, `ship_to_state`, `ship_to_zip`, `customer_number`

**Acceptance Criteria:**
- [ ] Script `rebuild_customers_from_sales_orders.py` exists and runs
- [ ] Customers have `company_key` computed from Sales Order data (not ShipStation)
- [ ] Distributions linked to SOs with same customer are grouped correctly
- [ ] Customer database shows correct grouping (no duplicates from ShipStation inconsistency)

### P0-3: Ensure Distribution-SO Matching Works

**Objective:** Distributions automatically match to Sales Orders, manual fallback works.

**Files:**
- `app/eqms/modules/rep_traceability/service.py` (distribution creation: auto-match)
- `app/eqms/modules/rep_traceability/admin.py` (PDF import: match after SO creation, manual match flow)

**Steps:**
1. **On Distribution Creation:** Add auto-match logic:
   ```python
   # In create_distribution_entry() or similar:
   if entry.order_number:
       matching_order = (
           s.query(SalesOrder)
           .filter(SalesOrder.order_number == entry.order_number)
           .first()
       )
       if matching_order:
           entry.sales_order_id = matching_order.id
   ```

2. **On Sales Order Creation:** Add auto-match logic:
   ```python
   # In PDF import, after creating sales_order:
   matching_distributions = (
       s.query(DistributionLogEntry)
       .filter(
           DistributionLogEntry.order_number == sales_order.order_number,
           DistributionLogEntry.sales_order_id.is_(None)
       )
       .all()
   )
   for dist in matching_distributions:
       dist.sales_order_id = sales_order.id
   ```

3. **Manual Match Flow:** Verify existing "Match" button works:
   - Sets `distribution.sales_order_id`
   - Stores PDF if uploaded
   - Updates customer link via SO

**Acceptance Criteria:**
- [ ] Distributions created from CSV/manual entry auto-match to existing SOs by `order_number`
- [ ] SOs created from PDF auto-match to existing distributions by `order_number`
- [ ] Manual "Match" button sets `sales_order_id` correctly
- [ ] After matching, distribution shows linked SO in details modal

### P0-4: Add PDF Download to Distribution Details

**Objective:** Distribution details modal shows linked SO PDF download link.

**Files:**
- `app/eqms/modules/rep_traceability/admin.py` (entry details endpoint)
- `app/eqms/templates/admin/distribution_log/list.html` (modal JS)

**Steps:**
1. Update `distribution_log_entry_details()` endpoint:
   ```python
   # After getting order_data, add:
   attachments = []
   if entry.sales_order_id:
       attachments = (
           s.query(OrderPdfAttachment)
           .filter(OrderPdfAttachment.sales_order_id == entry.sales_order_id)
           .order_by(OrderPdfAttachment.uploaded_at.desc())
           .limit(5)
           .all()
       )
   
   # In return jsonify(), add:
   "attachments": [
       {"id": a.id, "filename": a.filename, "pdf_type": a.pdf_type}
       for a in attachments
   ],
   ```

2. Update modal JS to render PDF download links (similar to sales dashboard modal)

**Acceptance Criteria:**
- [ ] Distribution details modal shows "Attachments" section when SO has PDFs
- [ ] Download links work (return PDF files)
- [ ] Multiple PDFs shown if exist (or most recent)

### P0-5: Remove Unprofessional UI Text

**Objective:** Delete "Source of truth..." sentence from sales orders list.

**Files:**
- `app/eqms/templates/admin/sales_orders/list.html`

**Steps:**
1. Delete line 8: `<p class="muted" style="margin:0;">Source of truth for customer orders and distributions.</p>`

**Acceptance Criteria:**
- [ ] Sales orders list page no longer shows "Source of truth..." text

### P0-6: Fix Detail Modals Readability (If Still Present)

**Objective:** Ensure all detail modals have solid backgrounds and readable text.

**Files:**
- `app/eqms/static/design-system.css` (verify `--card-bg` is defined)
- All modal templates (verify they use correct CSS)

**Steps:**
1. Verify `--card-bg: var(--panel);` exists in `design-system.css`
2. Check all modals use `background: var(--card-bg);`
3. Fix any readability issues (spacing, typography)

**Acceptance Criteria:**
- [ ] All modals have solid dark backgrounds
- [ ] All modal text is readable
- [ ] No overlapping sections

---

## Acceptance Criteria (DoD Checklist)

### After Upload, Admin Can Click Distribution → See Linked SO + Download Page

- [ ] Upload bulk PDF → PDF splits into pages
- [ ] Each page creates/finds Sales Order
- [ ] Each page PDF stored as separate attachment
- [ ] Go to Distribution Log → Click "Details" on matched entry
- [ ] Modal shows linked Sales Order info
- [ ] Modal shows "Download PDF" button/link
- [ ] Clicking download returns the specific page PDF

### Same Customer Across Multiple SOs Collapses into Single Customer Record

- [ ] Run `rebuild_customers_from_sales_orders.py` script
- [ ] Check Customer Database → Verify customers with multiple SOs show as single record
- [ ] Verify `company_key` computed from Sales Order data (not ShipStation)
- [ ] Verify no duplicate customers with same `company_key`

### Customer Database Shows Correct Grouping and Order History + SKU Totals

- [ ] Customer list page shows customers grouped correctly
- [ ] Customer detail page shows:
  - Order history (all Sales Orders for that customer)
  - SKU totals/breakdown (aggregated from distributions linked via SOs)
- [ ] Totals match Distribution Log sums for that customer

### Unmatched SO Pages Remain Stored and Downloadable

- [ ] Upload bulk PDF with some unmatched pages
- [ ] Unmatched pages stored as `OrderPdfAttachment` with `sales_order_id = NULL`
- [ ] Sales Orders area shows "Unmatched" section or filter
- [ ] Unmatched PDFs are downloadable

---

## Test Plan

### Browser-Only Verification

**Test 1: Bulk PDF Upload + Splitting**
1. Go to Sales Orders → Click "Import PDF"
2. Upload bulk PDF (multiple pages)
3. **Expected:** Import results show "X pages processed, Y orders created, Z unmatched"
4. Go to a created Sales Order detail page
5. **Expected:** See PDF attachment(s) for that specific page
6. Click download → **Expected:** PDF downloads (should be single page, not entire bulk file)

**Test 2: Distribution-SO Matching**
1. Go to Distribution Log → Find entry with `order_number` that matches a Sales Order
2. **Expected:** Entry shows no ⚠ icon (matched)
3. Click "Details" → **Expected:** Modal shows linked Sales Order
4. **Expected:** Modal shows "Download PDF" link
5. Click download → **Expected:** PDF downloads

**Test 3: Customer Rebuild**
1. Run rebuild script (if accessible via admin UI, or provide instructions)
2. Go to Customer Database → Check a customer that has multiple Sales Orders
3. **Expected:** Customer shows as single record (not duplicates)
4. Open customer detail → **Expected:** Order history shows all SOs
5. **Expected:** SKU totals match Distribution Log for that customer

**Test 4: Unmatched Pages**
1. Upload bulk PDF with some pages that don't parse
2. Go to Sales Orders → **Expected:** See "Unmatched" section or filter
3. **Expected:** Unmatched PDFs listed and downloadable

### Optional curl Routes (If Needed)

```bash
# Test PDF download
curl -H "Cookie: session=..." https://<app>/admin/sales-orders/pdf/<attachment_id>/download -o test.pdf

# Test distribution details JSON
curl -H "Cookie: session=..." https://<app>/admin/distribution-log/entry-details/<id>
```

---

## Migration/Backfill Steps

### No Schema Changes Required

**All relationships already support requirements:**
- `distribution_log_entries.sales_order_id` (nullable FK) — supports 1-to-many
- `order_pdf_attachments.sales_order_id` (nullable FK) — supports 1-to-many
- `sales_orders.customer_id` (NOT NULL FK) — supports many-to-one

### Optional: Add Ship-To Fields to SalesOrder (If Missing)

**If Sales Orders don't store ship-to data:**
- Add fields: `ship_to_name`, `ship_to_address1`, `ship_to_city`, `ship_to_state`, `ship_to_zip`, `customer_number` (all nullable)
- Migration: `alembic revision -m "add_ship_to_fields_to_sales_orders"`
- Backfill: Extract from existing PDF attachments or leave NULL (populated on future imports)

### Customer Rebuild Script (One-Time)

**Script:** `scripts/rebuild_customers_from_sales_orders.py`

**Safety:**
- Idempotent (safe to run multiple times)
- No data deletion (only updates)
- Can be run in transaction (rollback on error)

**Steps:**
1. For each Sales Order, compute `company_key` from ship-to
2. Find or create customer with that key
3. Update customer fields from SO (if more complete)
4. Update `sales_orders.customer_id` if changed
5. Update `distribution_log_entries.customer_id` via `sales_orders.customer_id`
6. Merge duplicate customers (same `company_key`)

---

## Files Likely to Change

**Backend:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (add `split_pdf_into_pages()`)
- `app/eqms/modules/rep_traceability/admin.py` (bulk PDF import, entry details, matching logic)
- `app/eqms/modules/rep_traceability/service.py` (distribution creation: auto-match)
- `app/eqms/modules/customer_profiles/utils.py` (add `compute_customer_key_from_sales_order()`)
- `app/eqms/modules/customer_profiles/service.py` (update to accept SO data)

**Frontend:**
- `app/eqms/templates/admin/sales_orders/list.html` (remove "Source of truth" text)
- `app/eqms/templates/admin/distribution_log/list.html` (add PDF download to modal)

**Scripts:**
- `scripts/rebuild_customers_from_sales_orders.py` (new)

**Migrations (Optional):**
- `migrations/versions/xxx_add_ship_to_fields_to_sales_orders.py` (if needed)

---

## Deployment Notes

### DigitalOcean Constraints

- **Run Command:** `python scripts/start.py` (unchanged)
- **No Release Commands:** All migrations/seed run in `start.py` (already correct)

### One-Time Scripts

- `scripts/rebuild_customers_from_sales_orders.py` — Run after deploy (idempotent, safe)

### Dependencies

- May need to add `PyPDF2` or `pypdf` to `requirements.txt` for PDF page splitting

---

**End of Phase 1 Developer Prompt**
