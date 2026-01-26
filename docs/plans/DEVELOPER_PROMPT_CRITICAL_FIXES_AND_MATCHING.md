# Developer Agent Prompt: Critical Fixes + Sales Order Matching + UX Improvements

**Date:** 2026-01-23  
**Priority:** P0 (Critical) + P1  
**Context:** Production deployment reliability, data accuracy, and user experience fixes

---

## Current State Summary

**What's Already Implemented:**
- ✅ Fixed 500 bug: `OrderPdfAttachment` import added to `sales_order_detail`
- ✅ UI: Distribution log list shows ⚠ icon for unmatched entries (`sales_order_id` NULL) + "Match" button
- ✅ Upload endpoint: `POST /admin/distribution-log/<id>/upload-pdf` exists
- ✅ Upload modal + JS flow in `distribution_log/list.html`
- ✅ `create_app()` and startup logging in `__init__.py`
- ✅ Health endpoints: `/health` (JSON) and `/healthz` (text "ok") exist in `app/eqms/routes.py`

**Current Run Command:** `python scripts/start.py` (runs migrations + starts gunicorn)  
**DigitalOcean Constraint:** No Release Commands available; health check supports TCP or HTTP with Port field

**Known Issues:**
- No health checks configured in DigitalOcean
- Lot tracking reads from wrong source (needs Distribution Log)
- Sales orders not matching to distributions correctly
- PDF bulk upload not splitting pages
- Customer database not refreshed from sales orders
- Detail views still unreadable
- Customer detail view missing order history + SKU breakdown

---

## P0 Tasks (Must Do Immediately)

### P0-A: DigitalOcean Health Check Configuration + Deployment Reliability

**Problem:** No health checks configured. Deployment may fail if readiness probe doesn't work. Need exact DO settings and admin-visible diagnostics.

**Requirements:**

1. **Ensure `/healthz` endpoint is fast and dependency-free**
   - Current: `app/eqms/routes.py` has `/healthz` returning `"ok"` 200
   - **Verify:** No DB queries, no heavy imports, returns in <100ms
   - **If needed:** Add explicit check that app is bound to port (e.g. verify `PORT` env var exists)

2. **Provide exact DigitalOcean App Platform settings**

   **Option 1: HTTP Readiness Check (Recommended)**
   - **Type:** HTTP
   - **Path:** `/healthz`
   - **Port:** `$PORT` (or `8080` if PORT not set)
   - **Initial Delay:** `20` seconds (accounts for migrations in `start.py`)
   - **Timeout:** `5` seconds
   - **Period:** `10` seconds
   - **Failure Threshold:** `3` attempts

   **Option 2: TCP Readiness Check (Fallback if HTTP doesn't work)**
   - **Type:** TCP
   - **Port:** `$PORT` (or `8080`)
   - **Initial Delay:** `20` seconds
   - **Timeout:** `5` seconds
   - **Period:** `10` seconds
   - **Failure Threshold:** `3` attempts

   **Developer Action:** Test both locally, recommend HTTP first. Provide exact copy-paste values for DO UI.

3. **Make startup more robust**
   - **Current:** `scripts/start.py` runs `release.py` (migrations) then starts gunicorn
   - **Ensure:** `PORT` env var is validated (fail fast if missing)
   - **Ensure:** Gunicorn binds to `0.0.0.0:$PORT` (not `127.0.0.1`)
   - **Ensure:** Health endpoint responds **immediately after gunicorn binds** (don't wait for first request)
   - **Add:** Startup logging: `"Gunicorn bound to 0.0.0.0:{port}; health check ready"`

4. **Create admin diagnostics page**
   - **Route:** `GET /admin/diagnostics` (or `/admin/system-status`)
   - **Permission:** `admin.view` (or create `system.diagnostics` permission)
   - **Display:**
     - App version/commit (if available from env var `APP_VERSION` or git)
     - Database connectivity: `SELECT 1` test (show "Connected" or error)
     - Last ShipStation sync: query `shipstation_sync_runs` table, show last run date/status
     - Counts (simple SQL):
       - Total customers: `SELECT COUNT(*) FROM customers`
       - Total distribution log rows: `SELECT COUNT(*) FROM distribution_log_entries`
       - Total sales orders: `SELECT COUNT(*) FROM sales_orders`
       - Unmatched distributions: `SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NULL`
     - Health endpoint status: show last check time (optional, or just link to `/healthz`)
   - **Template:** `app/eqms/templates/admin/diagnostics.html` (simple card layout, readable)

**Files to Touch:**
- `app/eqms/routes.py` (verify `/healthz` is fast)
- `scripts/start.py` (add PORT validation, startup logging)
- `app/eqms/admin.py` (add diagnostics route)
- `app/eqms/templates/admin/diagnostics.html` (new)
- `scripts/init_db.py` (add `system.diagnostics` permission if needed)

**Acceptance Criteria:**
- [ ] `/healthz` returns `"ok"` 200 in <100ms (no DB queries)
- [ ] DO health check passes within 30 seconds of deploy start
- [ ] `/admin/diagnostics` page loads and shows all required info
- [ ] Startup logs show "Gunicorn bound to 0.0.0.0:{port}; health check ready"

**Ethan's Verification (Browser Only):**
1. After deploy, wait 30 seconds
2. Open DigitalOcean → App Platform → Logs
3. Look for: "Gunicorn bound to 0.0.0.0:8080" and "health check ready"
4. In browser: Go to `https://<app-url>/healthz` → Should see "ok"
5. In browser: Go to `https://<app-url>/admin/diagnostics` (login if needed) → Should see all counts and statuses

---

### P0-B: Fix System-Wide View-Details Readability

**Problem:** Detail views (sales order detail page, distribution detail modal, customer detail page, etc.) are still unreadable: cramped spacing, poor typography, overflow issues, overlapping sections.

**Requirements:**

1. **Identify all affected templates:**
   - `app/eqms/templates/admin/sales_orders/detail.html` (full page)
   - `app/eqms/templates/admin/distribution_log/list.html` (entry-details modal)
   - `app/eqms/templates/admin/sales_dashboard/index.html` (order-details modal)
   - `app/eqms/templates/admin/customers/detail.html` (full page)
   - Any other detail modals or full-page detail views

2. **Apply consistent readability rules everywhere:**
   - **Section headers:** `font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--text);`
   - **Field labels:** `font-size: 12px; color: var(--muted); margin-bottom: 4px;`
   - **Field values:** `font-size: 14px; line-height: 1.6; margin-bottom: 12px; word-wrap: break-word;`
   - **Section spacing:** `margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border);`
   - **Content padding:** `24px` (not 16px or 20px)
   - **Modal max-width:** `700px`
   - **Modal max-height:** `80vh`
   - **Scroll area:** `max-height: calc(80vh - 120px); overflow-y: auto; overflow-x: hidden;`
   - **Long strings:** Use `word-wrap: break-word;` for emails, IDs, addresses
   - **Tables:** Ensure readable on 1366px+ width (responsive columns, horizontal scroll only if necessary)
   - **Badges/buttons:** Consistent alignment, no overlapping

3. **Create shared CSS class or include:**
   - Option A: Add `.detail-panel` class to `app/eqms/static/design-system.css` (or `_layout.html` styles)
   - Option B: Create `app/eqms/templates/admin/_detail_section.html` Jinja include
   - Apply to all detail surfaces consistently

**Files to Touch:**
- `app/eqms/templates/admin/sales_orders/detail.html`
- `app/eqms/templates/admin/distribution_log/list.html` (modal)
- `app/eqms/templates/admin/sales_dashboard/index.html` (modal)
- `app/eqms/templates/admin/customers/detail.html`
- `app/eqms/static/design-system.css` (or `_layout.html` for shared styles)

**Acceptance Criteria:**
- [ ] All detail pages/modals use consistent typography and spacing
- [ ] No horizontal scrolling required on 1366px+ width (except for wide tables with explicit horizontal scroll)
- [ ] Long strings (emails, IDs, addresses) wrap properly
- [ ] Modals scroll correctly (content doesn't overlap backdrop)
- [ ] Sections are clearly separated with headers
- [ ] All primary fields readable without zooming

**Ethan's Verification (Browser Only):**
1. Open Sales Order detail page → Check spacing, readability, no overflow
2. Open Distribution Log → Click "Details" on any row → Check modal readability, scroll behavior
3. Open Sales Dashboard → Click "View Details" on any order → Check modal readability
4. Open Customer detail page → Check all tabs (Overview, Orders, Distributions) → Verify readability
5. Resize browser to 1366px width → Verify no horizontal scroll (except wide tables)

---

### P0-C: Fix Lot Tracking to Use Distribution Log (Not ShipStation)

**Problem:** Sales Dashboard "Lot Tracking" card appears to read from ShipStation data. **Correct source of truth is Distribution Log** (contains processed ShipStation + future manual entries).

**Current Code Location:**
- `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard()` (lines ~577-641)
- Currently queries `DistributionLogEntry` (correct!) but verify it's not also reading ShipStation

**Requirements:**

1. **Verify lot tracking reads ONLY from Distribution Log:**
   - Current code (lines 585-641) queries `DistributionLogEntry` → **This is correct**
   - **Verify:** No queries to `shipstation_orders` or `shipstation_shipments` tables
   - **Verify:** Aggregation uses `DistributionLogEntry.lot_number` and `DistributionLogEntry.quantity`

2. **Ensure proper aggregation:**
   - Group by lot (normalized/corrected via Lot Log)
   - Sum quantities from `DistributionLogEntry.quantity` (not ShipStation)
   - Filter to 2025+ lots (existing logic)
   - Calculate Active Inventory (produced - distributed) from Lot Log CSV

3. **Add acceptance check:**
   - Create a test query that compares:
     - Distribution Log count for a known lot: `SELECT SUM(quantity) FROM distribution_log_entries WHERE lot_number = 'SLQ-XXXXX'`
     - Dashboard lot tracking output for same lot
   - They must match (or document why they differ, e.g. lot corrections)

**Files to Touch:**
- `app/eqms/modules/rep_traceability/service.py` (verify `compute_sales_dashboard()` lot tracking logic)
- Add comments/documentation if lot tracking logic is correct but unclear

**Acceptance Criteria:**
- [ ] Lot tracking queries ONLY `DistributionLogEntry` table (no ShipStation tables)
- [ ] Lot totals match Distribution Log sums for known lots
- [ ] Active Inventory calculated correctly (Lot Log produced - Distribution Log distributed)

**Ethan's Verification (Browser Only):**
1. Go to Sales Dashboard
2. Note a lot number and its "Units" value from Lot Tracking card
3. Go to Distribution Log
4. Filter by that lot number (if filter exists) or search
5. Manually sum quantities for that lot → Should match dashboard value
6. If mismatch, report lot number and values

---

### P0-D: Fix Sales Orders ↔ Distribution Log Matching + PDF Splitting

**Problem:** Sales orders ingest but don't match to distributions. Bulk PDF uploads need splitting into individual pages. Matching logic is broken.

**Requirements:**

1. **PDF Splitting Pipeline:**
   - **Current:** `app/eqms/modules/rep_traceability/parsers/pdf.py` has `parse_sales_orders_pdf()` that processes entire PDF
   - **Change:** Split bulk PDF into individual pages (one sales order per page)
   - **Storage:** Store each page as separate PDF attachment:
     - Storage key: `sales_orders/{order_id}/pdfs/page_{page_num}_{timestamp}_{filename}`
     - Or: `sales_orders/{order_id}/pdfs/{order_number}_page_{page_num}_{timestamp}.pdf`
   - **Database:** Create `OrderPdfAttachment` record per page (link to `sales_order_id`)

2. **Matching Algorithm:**
   - **Rule 1:** Match by `order_number` (exact string match, normalized)
   - **Rule 2:** Match by `order_number` + `ship_date` (if order_number ambiguous)
   - **Rule 3:** Match by customer `facility_name` + `ship_date` (fallback, lower confidence)
   - **Implementation:**
     - When PDF is parsed and sales order created, immediately try to match existing `DistributionLogEntry` rows:
       ```python
       # In PDF import route, after creating sales_order:
       matching_distributions = (
           s.query(DistributionLogEntry)
           .filter(
               DistributionLogEntry.order_number == sales_order.order_number,
               DistributionLogEntry.sales_order_id.is_(None)  # Not already matched
           )
           .all()
       )
       for dist in matching_distributions:
           dist.sales_order_id = sales_order.id
       ```
     - When distribution is created (manual/CSV/ShipStation), try to match existing sales order:
       ```python
       # In distribution creation, after creating entry:
       matching_order = (
           s.query(SalesOrder)
           .filter(SalesOrder.order_number == entry.order_number)
           .first()
       )
       if matching_order:
           entry.sales_order_id = matching_order.id
       ```

3. **One-to-Many Mapping:**
   - **Current:** `DistributionLogEntry.sales_order_id` FK exists (nullable)
   - **Support:** One `SalesOrder` → Many `DistributionLogEntry` (already supported by FK)
   - **UI:** Show all distributions linked to a sales order on sales order detail page

4. **Ignore Irrelevant Pages:**
   - **Rule:** If PDF page doesn't extract valid `order_number` or valid SKU items, skip it (don't create sales order)
   - **Log:** Record skipped pages in import results (show in UI: "X pages processed, Y orders created, Z pages skipped")

5. **Download Links in UI:**
   - **Sales Order Detail:** List all PDF attachments (per-page PDFs) with download links
   - **Distribution Detail Modal:** Show linked sales order PDFs (if `sales_order_id` exists)

6. **Admin Workflow to Confirm/Override Matches:**
   - **Distribution Log:** Show "Match" button for unmatched entries → Opens modal to:
     - Search/select existing sales order
     - Or upload PDF to create new sales order and match
   - **Sales Order Detail:** Show "Link Distributions" button → Opens modal to:
     - Search/select distributions by order_number
     - Bulk link selected distributions

7. **Backfill Existing Data:**
   - **SQL Script:** Match existing distributions to sales orders by `order_number`:
     ```sql
     UPDATE distribution_log_entries d
     SET sales_order_id = (
         SELECT s.id FROM sales_orders s 
         WHERE s.order_number = d.order_number 
         LIMIT 1
     )
     WHERE d.sales_order_id IS NULL
       AND EXISTS (SELECT 1 FROM sales_orders s WHERE s.order_number = d.order_number);
     ```
   - **Run:** Provide one-time script or admin UI button to run backfill

**Files to Touch:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (add page splitting, store per-page PDFs)
- `app/eqms/modules/rep_traceability/admin.py` (PDF import route: create sales orders, match distributions, store attachments)
- `app/eqms/modules/rep_traceability/service.py` (distribution creation: auto-match sales orders)
- `app/eqms/modules/rep_traceability/models.py` (verify `OrderPdfAttachment` supports per-page storage)
- `app/eqms/templates/admin/sales_orders/detail.html` (show PDF attachments, link distributions UI)
- `app/eqms/templates/admin/distribution_log/list.html` (enhance "Match" button modal)
- `scripts/backfill_sales_order_matching.py` (new: one-time backfill script)

**Acceptance Criteria:**
- [ ] Bulk PDF upload splits into individual pages, stores each as separate attachment
- [ ] Each page PDF is downloadable from sales order detail page
- [ ] Matching by `order_number` works automatically on import
- [ ] Unmatched distributions show ⚠ icon + "Match" button (already exists, verify it works)
- [ ] Admin can manually link distributions to sales orders via UI
- [ ] Backfill script matches existing data by `order_number`
- [ ] One sales order can link to multiple distributions (1-to-many)

**Ethan's Verification (Browser Only):**
1. Upload bulk PDF of sales orders → Check import results: "X pages processed, Y orders created"
2. Open a sales order detail page → Verify PDF attachments listed (one per page)
3. Download a PDF attachment → Verify it's the correct page
4. Check Distribution Log → Verify matched entries show no ⚠ icon
5. Check unmatched entry → Click "Match" → Verify can select sales order or upload PDF
6. After matching, verify distribution shows linked sales order in Details modal

---

### P0-E: Customer Database Derived from Sales Orders (Not ShipStation)

**Problem:** Customer information should come from sales orders (consistent), not ShipStation (inconsistent spelling/abbreviation).

**Requirements:**

1. **Deterministic Customer Identity Strategy:**
   - **Key Fields:** `facility_name`, `address1`, `city`, `state`, `zip` (from sales order ship-to)
   - **Normalization:** Use existing `canonical_customer_key()` from `app/eqms/modules/customer_profiles/utils.py`
   - **Matching:** When sales order is created/imported:
     - Extract ship-to: `facility_name`, `address1`, `city`, `state`, `zip`
     - Compute `company_key = canonical_customer_key(facility_name)`
     - Find existing customer by `company_key` OR create new customer
     - **Update customer fields from sales order** (if sales order data is more complete):
       - If customer `facility_name` is empty/abbreviated and sales order has full name → update
       - If customer address is missing and sales order has address → update
       - **Do NOT overwrite** with ShipStation data (only sales order data)

2. **Update/Refresh Customers from Matched Sales Orders:**
   - **On Sales Order Import:** When sales order is created, update linked customer:
     ```python
     # In PDF import or sales order creation:
     customer = find_or_create_customer(s, facility_name=ship_to_name, ...)
     # Update customer from sales order if more complete:
     if sales_order_data.get("facility_name") and (not customer.facility_name or len(sales_order_data["facility_name"]) > len(customer.facility_name)):
         customer.facility_name = sales_order_data["facility_name"]
     if sales_order_data.get("address1") and not customer.address1:
         customer.address1 = sales_order_data["address1"]
     # ... similar for city, state, zip
     ```

3. **Distribution Log Links to Customers Consistently:**
   - **Rule:** When distribution is created, link to customer via `sales_order.customer_id` (if `sales_order_id` exists)
   - **Fallback:** If no sales order, use existing customer matching logic (but prefer sales-order–derived customers)

4. **Refresh Script (One-Time):**
   - **SQL/Service:** Update all customers from their linked sales orders:
     ```python
     # For each customer with linked sales orders:
     # Get most recent/complete sales order
     # Update customer fields from that sales order
     ```
   - **Run:** Provide admin UI button or one-time script

**Files to Touch:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (extract ship-to, create/update customer from sales order data)
- `app/eqms/modules/rep_traceability/admin.py` (PDF import: customer creation/update)
- `app/eqms/modules/customer_profiles/service.py` (enhance `find_or_create_customer()` to accept sales order data, update if more complete)
- `app/eqms/modules/rep_traceability/service.py` (distribution creation: link customer via sales order)
- `scripts/refresh_customers_from_sales_orders.py` (new: one-time refresh script)

**Acceptance Criteria:**
- [ ] Customer `facility_name` and address come from sales orders (not ShipStation) when sales order exists
- [ ] Customer fields updated from sales orders if sales order data is more complete
- [ ] Distribution log entries link to customers via `sales_order.customer_id` when matched
- [ ] Refresh script updates existing customers from their sales orders

**Ethan's Verification (Browser Only):**
1. Import a sales order PDF → Check customer database → Verify customer name matches sales order ship-to (not ShipStation)
2. Check a customer profile → Verify facility name and address match sales order data
3. Check Distribution Log → Verify customer names are consistent (not abbreviated/inconsistent)
4. Run refresh script (if provided) → Verify customer data updated from sales orders

---

### P0-F: Customer Detail View — Order History + SKU Distribution (P1, but include plan)

**Problem:** Customer detail view exists but missing order history and SKU breakdown.

**Requirements:**

1. **Order History Tab:**
   - **Current:** `app/eqms/templates/admin/customers/detail.html` has "Orders" tab (line ~32)
   - **Enhance:** Show list of sales orders tied to customer:
     - Columns: Order Number, Order Date, Ship Date, Status, Total Units, Actions (View Order)
     - Sort by order date DESC (newest first)
     - Link to sales order detail page

2. **Distribution History:**
   - **Current:** "Distributions" tab exists (line ~34)
   - **Enhance:** Show distribution entries with:
     - Columns: Ship Date, Order Number, SKU, Lot, Quantity, Source, Actions (View Details)
     - Sort by ship date DESC
     - Link to distribution detail modal or edit page

3. **SKU Totals and Breakdown:**
   - **Add to Overview Tab:** Table showing:
     - SKU → Total Units (all-time)
     - Optional: By Month (if requested, show monthly breakdown)
   - **Data Source:** Aggregate from `DistributionLogEntry` for this customer

4. **Navigation to Underlying Entries:**
   - Order History: Click order number → Navigate to `/admin/sales-orders/<id>`
   - Distribution History: Click "View Details" → Open distribution detail modal (or navigate to edit page)

**Files to Touch:**
- `app/eqms/modules/customer_profiles/admin.py` (enhance `customer_detail()` to fetch sales orders, compute SKU breakdown)
- `app/eqms/templates/admin/customers/detail.html` (enhance Orders tab, add SKU breakdown to Overview)

**Acceptance Criteria:**
- [ ] Customer detail "Orders" tab shows all sales orders for customer
- [ ] Customer detail "Distributions" tab shows all distributions (already exists, verify it works)
- [ ] Customer detail "Overview" tab shows SKU totals table
- [ ] Clicking order number navigates to sales order detail
- [ ] Clicking "View Details" on distribution opens modal or navigates

**Ethan's Verification (Browser Only):**
1. Open a customer profile → Check "Orders" tab → Verify sales orders listed
2. Check "Distributions" tab → Verify distributions listed
3. Check "Overview" tab → Verify SKU totals table shows correct totals
4. Click an order number → Verify navigates to sales order detail
5. Click "View Details" on a distribution → Verify modal opens or navigates

---

## P1 Tasks (After P0 Complete)

### P1-A: Additional Polish (Optional)

- Add monthly SKU breakdown to customer detail (if needed)
- Enhance matching algorithm with fuzzy matching for order numbers
- Add bulk matching UI (match multiple distributions at once)

---

## Files Likely to Change

**Backend:**
- `app/eqms/routes.py` (verify `/healthz`)
- `scripts/start.py` (PORT validation, startup logging)
- `app/eqms/admin.py` (diagnostics route)
- `app/eqms/modules/rep_traceability/service.py` (lot tracking verification, distribution matching, customer linking)
- `app/eqms/modules/rep_traceability/admin.py` (PDF import, matching UI, customer refresh)
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (page splitting, per-page storage)
- `app/eqms/modules/customer_profiles/service.py` (customer update from sales orders)
- `app/eqms/modules/customer_profiles/admin.py` (customer detail: sales orders, SKU breakdown)

**Frontend:**
- `app/eqms/templates/admin/diagnostics.html` (new)
- `app/eqms/templates/admin/sales_orders/detail.html` (readability, PDF attachments, link distributions)
- `app/eqms/templates/admin/distribution_log/list.html` (readability, matching UI)
- `app/eqms/templates/admin/sales_dashboard/index.html` (readability)
- `app/eqms/templates/admin/customers/detail.html` (readability, order history, SKU breakdown)
- `app/eqms/static/design-system.css` (shared readability styles)

**Scripts:**
- `scripts/backfill_sales_order_matching.py` (new)
- `scripts/refresh_customers_from_sales_orders.py` (new)

**Migrations:**
- None required (existing schema supports all features)

---

## How Ethan Verifies After Deploy (Browser Only)

### Step 1: Health Check + Diagnostics
1. Wait 30 seconds after deploy
2. Open DigitalOcean → App Platform → Logs
3. Look for: "Gunicorn bound to 0.0.0.0:8080" and "health check ready"
4. In browser: Go to `https://<app-url>/healthz` → Should see "ok"
5. In browser: Go to `https://<app-url>/admin/diagnostics` → Should see counts and statuses

### Step 2: View-Details Readability
1. Open Sales Order detail page → Check spacing, no overflow
2. Open Distribution Log → Click "Details" → Check modal readability
3. Open Sales Dashboard → Click "View Details" → Check modal readability
4. Open Customer detail → Check all tabs → Verify readability

### Step 3: Lot Tracking
1. Go to Sales Dashboard
2. Note a lot number and "Units" from Lot Tracking card
3. Go to Distribution Log, search/filter by that lot
4. Manually sum quantities → Should match dashboard

### Step 4: Sales Order Matching
1. Upload bulk PDF → Check import results
2. Open sales order detail → Verify PDF attachments (one per page)
3. Check Distribution Log → Verify matched entries (no ⚠ icon)
4. Check unmatched entry → Click "Match" → Verify can link

### Step 5: Customer Refresh
1. Import sales order → Check customer database → Verify name matches sales order (not ShipStation)
2. Open customer profile → Verify facility name/address from sales order

### Step 6: Customer Detail View
1. Open customer profile → Check "Orders" tab → Verify sales orders listed
2. Check "Overview" tab → Verify SKU totals table
3. Click order number → Verify navigates to sales order detail

---

## Deployment Notes Checklist

**What Changed:**
- [ ] Health check configuration (DO settings provided)
- [ ] Admin diagnostics page added (`/admin/diagnostics`)
- [ ] View-details readability improved (all detail pages/modals)
- [ ] Lot tracking verified to use Distribution Log (not ShipStation)
- [ ] PDF splitting implemented (bulk PDF → individual pages)
- [ ] Sales order matching algorithm implemented (auto-match by order_number)
- [ ] Customer database refresh from sales orders (not ShipStation)
- [ ] Customer detail view enhanced (order history, SKU breakdown)

**Database Changes:**
- [ ] None (existing schema sufficient)

**Environment Variables:**
- [ ] `PORT` (already required)
- [ ] `APP_VERSION` (optional, for diagnostics page)

**One-Time Scripts to Run:**
- [ ] `scripts/backfill_sales_order_matching.py` (match existing distributions to sales orders)
- [ ] `scripts/refresh_customers_from_sales_orders.py` (update customers from sales orders)

**DigitalOcean Settings:**
- [ ] Health Check Type: HTTP (or TCP if HTTP doesn't work)
- [ ] Health Check Path: `/healthz` (if HTTP)
- [ ] Health Check Port: `$PORT` (or `8080`)
- [ ] Initial Delay: `20` seconds
- [ ] Timeout: `5` seconds
- [ ] Period: `10` seconds
- [ ] Failure Threshold: `3`

---

## Important Notes

1. **No Release Commands:** All migrations/seed must run in `scripts/start.py` (already does via `release.py`)

2. **Health Check Timing:** 20-second initial delay accounts for migrations. If migrations take longer, increase delay.

3. **Matching Safety:** Matching by `order_number` is safe (exact string match). Fuzzy matching (P1) can be added later if needed.

4. **Customer Refresh:** Only update customer fields from sales orders if sales order data is more complete. Don't overwrite with empty/null values.

5. **PDF Splitting:** Store each page as separate attachment. If a page fails to parse, skip it (don't break entire import).

6. **Backfill Scripts:** Run once after deploy. Provide admin UI buttons or one-time CLI scripts.

---

**End of Developer Prompt**
