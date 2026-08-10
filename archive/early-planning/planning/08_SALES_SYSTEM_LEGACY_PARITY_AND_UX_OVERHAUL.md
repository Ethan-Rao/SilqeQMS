# Sales System Legacy Parity & UX Overhaul — Implementation Spec

**Date:** 2026-01-19  
**Purpose:** Developer-ready implementation plan to achieve functional parity with legacy Rep QMS sales/admin features while implementing a professional UI/UX overhaul and fixing ShipStation sync completeness.

---

## 1) Executive Summary

### What's Missing Today vs Legacy

**Current State:**
- ✅ Sales Dashboard exists (`/admin/sales-dashboard`) but is minimal (basic stats, no visual polish)
- ✅ Customer Database exists (`/admin/customers`) with pagination and basic filters
- ✅ Customer Profile exists (`/admin/customers/<id>`) with notes, but lacks order/distribution history tabs
- ✅ Distribution Log exists with customer linking capability
- ❌ **ShipStation sync only pulls last 30 days** (default `SHIPSTATION_DEFAULT_DAYS=30`) → **missing all 2025 orders**
- ❌ UI lacks professional polish (legacy has Bootstrap cards, better typography, visual hierarchy)
- ❌ Notes created from Sales Dashboard don't have clear workflow
- ❌ Customer Profile doesn't show unified order/distribution history (only "Recent distributions" snippet)

**Legacy System (Functional Reference):**
- Professional Bootstrap-based UI with cards, accordions, visual metrics
- Customer Database with expandable accordion cards showing full order history inline
- Customer Profile with tabs/sections: Overview, Order History, Notes, Documents
- Sales Dashboard with visual metric cards (Total Units, Total Orders, Unique Customers)
- Monthly breakdowns, SKU breakdowns, Top Customers table with links
- Notes workflow integrated into dashboard and profile

### What We're Changing

1. **UX/UI Overhaul:**
   - Implement consistent design system (cards, tables, filters, spacing)
   - Add visual metrics cards to Sales Dashboard
   - Redesign Customer Database with better visual hierarchy
   - Add tabbed Customer Profile (Overview / Orders / Distributions / Notes)
   - Improve Distribution Log entry flow (better customer selection UX)

2. **Feature Parity:**
   - Ensure all legacy functionality exists (monthly breakdowns, SKU breakdowns, top customers)
   - Add year filter to Customer Database (2025/2026 visibility)
   - Unify order/distribution history on Customer Profile
   - Ensure notes workflow works from Sales Dashboard → Customer Profile

3. **Data Cohesion:**
   - Enforce single source of truth for customers (`customers` table)
   - Ensure all distributions link to canonical `customer_id`
   - Ensure notes are tied to `customer_id` (already implemented)

4. **ShipStation Sync Completeness:**
   - Fix sync to pull from `2025-01-01` instead of last 30 days
   - Add backfill capability for 2025 orders
   - Add admin UI to show sync status and last order date

---

## 2) Current-State Inventory (New System)

### Routes/Endpoints

**Sales Dashboard:**
- `GET /admin/sales-dashboard` → `rep_traceability.sales_dashboard()` (`app/eqms/modules/rep_traceability/admin.py` line ~520)
- `GET /admin/sales-dashboard/export` → `rep_traceability.sales_dashboard_export()` (line ~540)
- Template: `app/eqms/templates/admin/sales_dashboard/index.html`

**Customer Database:**
- `GET /admin/customers` → `customer_profiles.customers_list()` (`app/eqms/modules/customer_profiles/admin.py` line 30)
- `GET /admin/customers/new` → `customer_profiles.customers_new_get()` (line 76)
- `POST /admin/customers/new` → `customer_profiles.customers_new_post()` (line 82)
- `GET /admin/customers/<id>` → `customer_profiles.customer_detail()` (line 114)
- `POST /admin/customers/<id>` → `customer_profiles.customer_update_post()` (line 133)
- Templates: `app/eqms/templates/admin/customers/list.html`, `detail.html`

**Customer Notes:**
- `POST /admin/customers/<id>/notes` → `customer_profiles.customer_note_add()` (line 176)
- `POST /admin/customers/<id>/notes/<note_id>/edit` → `customer_profiles.customer_note_edit()` (line 201)
- `POST /admin/customers/<id>/notes/<note_id>/delete` → `customer_profiles.customer_note_delete()` (line 220)

**Distribution Log:**
- `GET /admin/distribution-log` → `rep_traceability.distribution_log_list()` (`app/eqms/modules/rep_traceability/admin.py` line 53)
- `GET /admin/distribution-log/new` → `rep_traceability.distribution_log_new_get()` (line 91)
- `POST /admin/distribution-log/new` → `rep_traceability.distribution_log_new_post()` (line 99)
- `GET /admin/distribution-log/<id>/edit` → `rep_traceability.distribution_log_edit_get()` (line 155)
- `POST /admin/distribution-log/<id>/edit` → `rep_traceability.distribution_log_edit_post()` (line 175)
- Templates: `app/eqms/templates/admin/distribution_log/list.html`, `edit.html`

**ShipStation Sync:**
- `GET /admin/shipstation` → `shipstation_sync.shipstation_index()` (`app/eqms/modules/shipstation_sync/admin.py`)
- `POST /admin/shipstation/run` → `shipstation_sync.shipstation_run()` (triggers `run_sync()`)
- Service: `app/eqms/modules/shipstation_sync/service.py::run_sync()` (line 66)

### Models/Tables

**Customers:**
- `app/eqms/modules/customer_profiles/models.py::Customer`
- Table: `customers` (id, company_key [unique], facility_name, address fields, contact fields, primary_rep_id, timestamps)
- `customer_notes` (id, customer_id [FK], note_text, note_date, author, timestamps)

**Distribution Log:**
- `app/eqms/modules/rep_traceability/models.py::DistributionLogEntry`
- Table: `distribution_log_entries` (id, ship_date, order_number, facility_name, customer_id [FK nullable], sku, lot_number, quantity, source, timestamps)

**ShipStation Sync:**
- `app/eqms/modules/shipstation_sync/models.py::ShipStationSyncRun`, `ShipStationSkippedOrder`

### Notes Storage

**Current Implementation:**
- Notes stored in `customer_notes` table (`app/eqms/modules/customer_profiles/models.py::CustomerNote`)
- Notes can be created from Customer Profile detail page (`POST /admin/customers/<id>/notes`)
- Notes are NOT currently creatable from Sales Dashboard (missing workflow)

**Service Functions:**
- `app/eqms/modules/customer_profiles/service.py::add_customer_note()`, `edit_customer_note()`, `delete_customer_note()`

### ShipStation Sync Entrypoints & Date Logic

**Current Implementation:**
- Entrypoint: `app/eqms/modules/shipstation_sync/service.py::run_sync()` (line 66)
- Date filter: Line 81-93
  ```python
  days = int((os.environ.get("SHIPSTATION_DEFAULT_DAYS") or "30").strip() or "30")
  start_dt = now - timedelta(days=days)  # Only last 30 days!
  ```
- API call: Line 113
  ```python
  orders = client.list_orders(create_date_start=_iso_utc(start_dt), create_date_end=_iso_utc(now), page=page, page_size=100)
  ```

**Problem:** Default `SHIPSTATION_DEFAULT_DAYS=30` means only orders from last 30 days are synced. To get 2025 orders, need to sync from `2025-01-01`.

**Schedule/Trigger:**
- Admin-triggered via `/admin/shipstation/run` (no automatic cron)

---

## 3) Legacy System Inventory (Functional Reference)

### Legacy Files (Behavioral Reference Only)

**Location:** `legacy/_archive/`
- `admin_sales_dashboard.html` - Bootstrap-based dashboard with metric cards, monthly/SKU breakdowns, top customers table
- `admin_customer_database.html` - Accordion-based customer list with inline order history, search/filter UI
- `admin_customer_profile.html` - Tabbed profile with Overview, Order History, Notes sections

### Key Features in Legacy (Must Match Functionally)

**Sales Dashboard:**
- Visual metric cards: Total Units (All Time), Total Orders, Unique Customers
- Sales by Month table (month, orders, units)
- Sales by SKU table (SKU, total units)
- Top Customers table (customer name [linked], total orders, total units, last order date)
- Date filter (start_date) for windowed metrics
- Export CSV functionality

**Customer Database:**
- Search bar (facility name, city, state)
- State filter dropdown
- Type filter (First-Time Only / Repeat Customers)
- Accordion cards per customer showing:
  - Contact Information section
  - Order Summary (total orders, total units, SKU breakdown)
  - Order History (scrollable list with order number, date, items, quantities)
- Real-time client-side filtering (JavaScript)

**Customer Profile:**
- Header with customer name, ID, added date, order count
- Order Summary stats card (total orders, total units, device types, first/latest order dates)
- Order History table (date, order #, items, total qty)
- Notes section with add/edit/delete
- Export customer data (CSV)

**Notes Workflow:**
- Notes can be added from Customer Profile
- Notes appear in chronological list
- Notes show date, author, edit history

### What NOT to Port (Legacy Landmines)

**Files/Patterns to Avoid:**
- `repqms_Proto1_reference.py.py` - Monolithic Flask app with mixed concerns (SMTP, direct SQL, rep pages)
- `repqms_shipstation_sync.py.py` - Different schema, raw SQL DDL, not aligned with current architecture
- Direct `psycopg2` SQL queries (use SQLAlchemy ORM)
- Rep-specific routes (`/rep/<slug>`) - explicitly excluded
- Email sending code (SMTP) - explicitly excluded
- Hardcoded file paths (use storage abstraction)

**Anti-Patterns:**
- Duplicated customer matching logic (use `canonical_customer_key()` from `app/eqms/modules/customer_profiles/utils.py`)
- Hardcoded date ranges (use env vars or config)
- Brittle string matching for customer deduplication (use `company_key` unique constraint)
- Client-side only filtering without server-side pagination (combine both)

**Safe Equivalents:**
- Use `Customer.company_key` for deduplication (already implemented)
- Use `find_or_create_customer()` service function (already implemented)
- Use SQLAlchemy relationships (`customer.notes`, `customer.distributions`)
- Use existing storage abstraction for any file uploads

---

## 4) Target UX Spec (Professional Look)

### Global Page Layout Standards

**Header Structure:**
```
[Page Title (h1)]
[Subtitle/Description (muted text)]
[Primary Action Button] [Secondary Actions...]
```

**Breadcrumbs (where applicable):**
```
Admin > Sales Dashboard
Admin > Customers > [Customer Name]
Admin > Distribution Log > New Entry
```

**Primary Action Button Placement:**
- Top-right of page header
- Style: `.button` (primary blue)
- Secondary actions: `.button--secondary` (gray)

### Table Component Standards

**Search Bar:**
- Place above table, full-width input with search icon
- Debounced (300ms) or submit-on-enter
- Placeholder: "Search by name, city, state..."

**Filters:**
- Horizontal row above table
- Dropdown selects for: State, Rep, Source, Year (2025/2026)
- Apply button (or auto-apply on change)
- Clear filters link

**Table Structure:**
- Striped rows (`.table` with `.table-striped`)
- Hover effect (`.table-hover`)
- Responsive wrapper (`.table-responsive`)
- Empty state: Centered message with icon, "No data found" + helpful hint

**Pagination:**
- Bottom of table
- Format: "Showing 1-50 of 234" + Previous/Next buttons
- Page size: 50 items (consistent across all lists)

### Detail Page Structure (Customer Profile)

**Tabbed Interface:**
```
[Overview] [Orders] [Distributions] [Notes] [Documents (optional)]
```

**Overview Tab:**
- Summary card: Facility name, address, contact info, rep assignment
- Key dates: First order, last order, customer since
- Quick stats: Total orders, total units, SKU breakdown (mini table)

**Orders Tab:**
- Table: Date, Order #, Source (ShipStation/Manual), Items (SKU × Qty), Total Qty
- Filter: Year (2025/2026), Date range
- Link to Distribution Log entry if applicable

**Distributions Tab:**
- Same as Orders but includes manual entries + CSV imports
- Unified view of all `distribution_log_entries` where `customer_id` matches

**Notes Tab:**
- Chronological list (newest first)
- Each note: Date, Author, Text, Edit/Delete buttons
- Add Note form at top (inline or modal)

**Documents Tab (Optional, if in legacy):**
- List of uploaded documents
- Upload button
- Download links

### Styling Principles

**Spacing:**
- Consistent card gaps: `14px` between cards (`.card + .card { margin-top: 14px; }`)
- Card padding: `16px` (`.card-body { padding: 16px; }`)
- Form field gaps: `12px` (`.form > div + div { margin-top: 12px; }`)

**Typography:**
- Page title: `h1` (24px, bold)
- Section headers: `h2` (20px, bold, margin-top: 0 in cards)
- Table headers: Bold, uppercase small text
- Muted text: `.muted` class (gray)

**Colors:**
- Primary: Blue (`#0066cc` or design system primary)
- Success: Green (for positive metrics)
- Danger: Red (for errors, delete actions)
- Muted: Gray (`#6b7280`)

**What NOT to Show:**
- Debug blocks (remove any `{{ debug }}` or `{{ request }}` dumps)
- Unnecessary stats panels (only show metrics that exist in legacy and are useful)
- Raw JSON dumps (format data properly)
- Internal IDs in UI (use human-readable labels)

### Performance Expectations

**Pagination:**
- All list views paginated (50 items per page)
- Server-side pagination (not client-side only)

**Search:**
- Debounced input (300ms delay) OR submit-on-enter
- Server-side search (not client-side filtering only)

**Dashboard Aggregations:**
- Compute on-demand (no cached tables needed for P0)
- Acceptable latency: < 2 seconds for typical dataset

---

## 5) Data Model Cohesion (Single Source of Truth)

### Canonical `customers` Entity

**Table:** `customers` (`app/eqms/modules/customer_profiles/models.py::Customer`)

**Unique Constraints:**
- `company_key` (unique, indexed) - Normalized facility name for deduplication
- Generated by: `canonical_customer_key(facility_name)` from `app/eqms/modules/customer_profiles/utils.py`

**Normalization Strategy:**
- `canonical_customer_key()`: Uppercase, remove special chars, collapse spaces
- Example: "Hospital A, Inc." → "HOSPITALAINC"
- Used for: Finding existing customers, preventing duplicates

**Required Fields:**
- `facility_name` (required, non-empty)
- `company_key` (required, unique, auto-generated from facility_name)

**Optional Fields:**
- Address: `address1`, `address2`, `city`, `state`, `zip`
- Contact: `contact_name`, `contact_phone`, `contact_email`
- Rep: `primary_rep_id` (FK to `users.id`)

### `notes` Entity

**Table:** `customer_notes` (`app/eqms/modules/customer_profiles/models.py::CustomerNote`)

**Foreign Keys:**
- `customer_id` (FK to `customers.id`, CASCADE delete)

**Fields:**
- `note_text` (required)
- `note_date` (optional, defaults to today)
- `author` (optional, defaults to current user email from audit)
- `created_at`, `updated_at` (timestamps)

**Single Source of Truth:**
- Notes are ALWAYS tied to `customer_id`
- Notes created from Sales Dashboard must resolve to a `customer_id` first
- Notes appear on Customer Profile (chronological list)

### `orders` Entity (from ShipStation)

**Current:** ShipStation orders are stored as `distribution_log_entries` with `source='shipstation'`

**Matching Strategy:**
- ShipStation order → Customer matching in `app/eqms/modules/shipstation_sync/service.py::_get_customer_from_ship_to()` (line 45)
- Uses `canonical_customer_key()` to find existing customer
- If not found, calls `find_or_create_customer()` to create new customer
- Sets `distribution_log_entries.customer_id` FK

**Override Capability:**
- Admin can manually edit distribution entry and change `customer_id`
- Admin can merge customers (future feature, not in scope)

**Idempotency:**
- `distribution_log_entries.external_key` = `"{shipment_id}:{sku}:{lot_number}"`
- Unique constraint: `(source, external_key)` prevents duplicates
- Safe to re-run sync (skips duplicates)

### `distributions` Entity (Manual + Imported)

**Table:** `distribution_log_entries` (`app/eqms/modules/rep_traceability/models.py::DistributionLogEntry`)

**Foreign Keys:**
- `customer_id` (FK to `customers.id`, nullable, SET NULL on delete)
- `rep_id` (FK to `users.id`, nullable)

**Linking Rules:**
- Manual entry: Admin selects customer from dropdown (required)
- CSV import: Auto-creates/links customer via `find_or_create_customer()` (line 290 in `admin.py`)
- ShipStation sync: Auto-creates/links customer via `_get_customer_from_ship_to()` (line 45 in `service.py`)

**Prevent Duplicates:**
- Manual/CSV: No unique constraint (allow manual duplicates if needed)
- ShipStation: `(source, external_key)` unique constraint

### Supporting Entities (if needed)

**Addresses:** Not separate table (stored in `customers` table directly)

**Facilities:** Not separate table (same as customers, one customer = one facility)

**Contacts:** Not separate table (stored in `customers` table: `contact_name`, `contact_phone`, `contact_email`)

---

## 6) Functional Requirements by Page

### 6.1 Sales Dashboard

**Purpose:** Daily-use page for sales team to see metrics, top customers, and quickly add notes/log distributions.

**Must Include:**

1. **Visual Metric Cards (Top Row):**
   - Total Units (All Time) - Blue card, large number
   - Total Orders (Windowed) - Green card, large number
   - Unique Customers (Windowed) - Info card, large number
   - First-Time Customers (Windowed) - Success card
   - Repeat Customers (Windowed) - Primary card

2. **Date Filter:**
   - Input: `start_date` (YYYY-MM-DD)
   - Default: `2025-01-01` (to show all 2025+ data)
   - Apply button
   - Windowed metrics use `ship_date >= start_date`

3. **Sales by Month Table:**
   - Columns: Month (YYYY-MM), Orders (count), Units (sum)
   - Sorted by month descending
   - Empty state: "No monthly data in selected window"

4. **Sales by SKU Table:**
   - Columns: SKU, Total Units
   - Sorted by SKU ascending
   - Empty state: "No SKU data in selected window"

5. **Top Customers Table:**
   - Columns: Customer Name (linked to profile), Total Orders, Total Units, Last Order Date
   - Sorted by units descending, limit 25
   - Actions: "View" (link to customer profile), "Add Note" (link to customer profile #notes anchor)
   - Only shows customers with `customer_id` linked (not orphaned entries)

6. **Quick Actions:**
   - "Log Manual Distribution" button (link to `/admin/distribution-log/new`)
   - "Export CSV" button (existing route)

**Must NOT Include:**
- Unnecessary analytics panels (keep it lean)
- Debug information
- Raw data dumps

**Reference Implementation:**
- Service: `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard()` (line 499)
- Template: `app/eqms/templates/admin/sales_dashboard/index.html` (needs visual overhaul)

### 6.2 Customer Database (List)

**Purpose:** Browse/search all customers with quick access to profiles.

**Columns:**
- Facility Name (linked to profile)
- City, State
- Rep (primary rep name or ID)
- Total Orders (lifetime count)
- Total Units (lifetime sum)
- Last Order Date
- First Order Date (optional, if space allows)

**Sorting:**
- Default: Facility Name ascending
- Optional: Last Order Date descending, Total Units descending

**Filters:**
- Search: Facility name, city, state (server-side LIKE query)
- State: Dropdown (all unique states from customers)
- Rep: Dropdown (all users with rep role, if applicable)
- Year: Dropdown ("All", "2025", "2026") - filters by last order date year
- Type: "All", "First-Time Only" (1 order), "Repeat" (2+ orders)

**Pagination:**
- 50 items per page
- Previous/Next buttons
- "Showing X-Y of Z" text

**Empty State:**
- Icon + "No customers found"
- "Try adjusting filters or create a new customer"

**Reference Implementation:**
- Route: `app/eqms/modules/customer_profiles/admin.py::customers_list()` (line 30)
- Template: `app/eqms/templates/admin/customers/list.html` (needs visual overhaul)

### 6.3 Customer Profile (Detail)

**Purpose:** Single customer view with complete history and notes.

**Tabbed Interface:**

**Overview Tab:**
- Header: Facility Name, Customer ID, Added Date
- Summary Card:
  - Address (formatted)
  - Contact Info (name, phone, email if available)
  - Primary Rep (name or ID)
- Stats Card:
  - Total Orders (lifetime)
  - Total Units (lifetime)
  - First Order Date
  - Last Order Date
  - SKU Breakdown (mini table: SKU, Units)

**Orders Tab:**
- Table: Date, Order #, Source (badge: ShipStation/Manual/CSV), Items (SKU × Qty), Total Qty, Lot Numbers
- Filter: Year (2025/2026), Date range
- Link: "View in Distribution Log" (if entry exists)
- Empty state: "No orders recorded yet"

**Distributions Tab:**
- Same as Orders but includes ALL distribution entries (manual + CSV + ShipStation)
- Unified view of `distribution_log_entries` where `customer_id` matches
- Same table structure as Orders tab

**Notes Tab:**
- Add Note form (inline at top):
  - Note Text (textarea, required)
  - Note Date (date input, defaults to today)
  - Submit button
- Notes list (chronological, newest first):
  - Each note: Date, Author, Text, Edit button, Delete button
- Empty state: "No notes yet. Add one above."

**Documents Tab (Optional, if in legacy):**
- List of uploaded documents (if document storage exists)
- Upload button
- Download links

**Actions (Header):**
- "Edit Customer" button (link to edit form)
- "Back to List" button
- "Export Data" button (CSV of orders/distributions)

**Reference Implementation:**
- Route: `app/eqms/modules/customer_profiles/admin.py::customer_detail()` (line 114)
- Template: `app/eqms/templates/admin/customers/detail.html` (needs tabbed interface)

### 6.4 Distribution Log

**Purpose:** View/edit/manage all distribution entries (manual + imported + synced).

**List View:**
- Table: Ship Date, Order #, Facility Name (linked to customer if `customer_id` exists), Rep, SKU, Lot, Qty, Source
- Filters: Date range, Source, Rep, Customer (dropdown), SKU
- Pagination: 50 items per page
- Actions: "New Entry", "Import CSV", "Export CSV"

**Manual Entry Flow:**
1. Click "New Entry"
2. Form fields:
   - Ship Date (required, date input)
   - Order Number (optional, auto-generated if blank)
   - **Customer (required dropdown)** - Searchable select with "Create New Customer" option
   - If customer selected: Auto-fill facility_name, address, city, state, zip from customer record
   - If "Create New Customer": Inline form to create customer (facility_name, address, city, state, zip)
   - Rep (optional dropdown)
   - SKU (required dropdown: 211810SPT, 211610SPT, 211410SPT)
   - Lot Number (required, format: SLQ-#####)
   - Quantity (required, positive integer)
   - Tracking Number (optional)
3. Submit → Creates distribution entry with `customer_id` FK
4. Redirect to list

**Edit Flow:**
- Same form as manual entry
- Pre-filled with existing data
- Customer dropdown shows current customer
- Reason for change required (audit trail)

**CSV Import:**
- Upload CSV file
- Auto-create/link customers via `find_or_create_customer()`
- Show results: Created, Duplicates skipped
- Link to created entries

**Reference Implementation:**
- Routes: `app/eqms/modules/rep_traceability/admin.py` (lines 53-256)
- Templates: `app/eqms/templates/admin/distribution_log/list.html`, `edit.html`

---

## 7) ShipStation Sync Deep Dive (Fix + Verification)

### Root Cause Analysis

**Current Code:** `app/eqms/modules/shipstation_sync/service.py::run_sync()` (line 66)

**Problem:** Line 81-93
```python
days = int((os.environ.get("SHIPSTATION_DEFAULT_DAYS") or "30").strip() or "30")
start_dt = now - timedelta(days=days)  # Only last 30 days!
```

**Impact:** Only orders from last 30 days are synced. To get 2025 orders (Jan 1, 2025 onwards), need to sync from `2025-01-01`.

### Fix Strategy

**Option 1: Change Default Date (Recommended)**
- Change `SHIPSTATION_DEFAULT_DAYS` default to calculate days from `2025-01-01` to today
- Or add new env var: `SHIPSTATION_SINCE_DATE=2025-01-01`

**Option 2: Add "Since Date" Parameter**
- Add `since_date` parameter to `run_sync()` (optional, defaults to `2025-01-01`)
- Admin UI can specify custom date

**Recommended Implementation:**
```python
# In run_sync()
since_date_str = os.environ.get("SHIPSTATION_SINCE_DATE", "2025-01-01")
try:
    since_date = datetime.fromisoformat(since_date_str).replace(tzinfo=timezone.utc)
except Exception:
    # Fallback to 2025-01-01
    since_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

start_dt = since_date  # Use fixed date instead of days ago
```

### API Paging Strategy

**Current:** Line 112-115
```python
for page in range(1, max_pages + 1):
    orders = client.list_orders(create_date_start=_iso_utc(start_dt), create_date_end=_iso_utc(now), page=page, page_size=100)
    if not orders:
        break
```

**Correct Behavior:**
- Use `create_date_start=2025-01-01T00:00:00.000Z`
- Use `create_date_end=now` (current UTC time)
- Page through all orders (respect `max_pages` and `max_orders` limits)
- Stop when `orders` is empty or limits hit

### Idempotency Rules

**Current:** Line 36 in `models.py`
```python
Index("uq_distribution_log_source_external_key", "source", "external_key", unique=True)
```

**External Key Format:** Line 41-42
```python
def _build_external_key(*, shipment_id: str, sku: str, lot_number: str) -> str:
    return f"{shipment_id}:{sku}:{lot_number}"
```

**Behavior:**
- If `external_key` already exists for `source='shipstation'`, skip (IntegrityError caught, logged as skipped)
- Safe to re-run sync (won't create duplicates)

### Backfill Approach for 2025 Orders

**One-Time Backfill:**
1. Set `SHIPSTATION_SINCE_DATE=2025-01-01` in env
2. Run sync via `/admin/shipstation/run`
3. Monitor logs for: orders_seen, synced, skipped
4. Verify: Check `distribution_log_entries` for entries with `ship_date >= 2025-01-01` and `source='shipstation'`

**Verification Query:**
```sql
SELECT 
    DATE_TRUNC('month', ship_date) AS month,
    COUNT(*) AS entries,
    SUM(quantity) AS units
FROM distribution_log_entries
WHERE source = 'shipstation'
    AND ship_date >= '2025-01-01'
GROUP BY DATE_TRUNC('month', ship_date)
ORDER BY month;
```

**Expected Result:**
- Rows for each month from 2025-01 to current month
- Non-zero entries and units for each month

### Sync Cursor/Watermark Storage

**Current:** No persistent cursor (always syncs from `since_date` to `now`)

**Recommendation:** Store last sync date in `shipstation_sync_runs` table
- Add column: `last_order_date` (date of most recent order synced)
- On next sync, use `max(last_order_date, since_date)` as start date
- Update `last_order_date` after each successful sync

**Migration:**
```python
# Add to ShipStationSyncRun model
last_order_date: Mapped[date | None] = mapped_column(Date, nullable=True)
```

### Admin UI: Sync Status

**Current:** `app/eqms/modules/shipstation_sync/admin.py::shipstation_index()`

**Must Show:**
- Last sync run: Date/time, orders synced, skipped, errors
- Last order date present: `MAX(ship_date)` from `distribution_log_entries` where `source='shipstation'`
- Sync button: "Run Sync" (triggers `run_sync()`)
- Sync settings: `SHIPSTATION_SINCE_DATE` (display only, not editable in UI)

**Template:** `app/eqms/templates/admin/shipstation/index.html`

### Definition of Done for ShipStation Sync

**Verification Steps:**

1. **Query Verification:**
   ```sql
   -- Should return rows for 2025 months
   SELECT DATE_TRUNC('month', ship_date) AS month, COUNT(*) 
   FROM distribution_log_entries 
   WHERE source = 'shipstation' AND ship_date >= '2025-01-01'
   GROUP BY DATE_TRUNC('month', ship_date)
   ORDER BY month;
   ```

2. **Spot Check:**
   - Pick a known 2025 order ID from ShipStation
   - Verify it exists in `distribution_log_entries` with `source='shipstation'`
   - Verify `customer_id` is linked (not NULL)

3. **Dashboard/Profile Verification:**
   - Open Sales Dashboard with `start_date=2025-01-01`
   - Verify 2025 orders appear in stats
   - Open a customer profile that had 2025 orders
   - Verify Orders tab shows 2025 orders

4. **Idempotency Test:**
   - Run sync twice
   - Second run should show: `synced=0`, `skipped=N` (where N = total orders)
   - No duplicate entries created

---

## 8) Implementation Plan (Developer Checklist)

### Phase 1: ShipStation Sync Fix (P0 - Blocker)

**Task 1.1: Fix Date Filter**
- [ ] Modify `app/eqms/modules/shipstation_sync/service.py::run_sync()` (line 81-93)
- [ ] Change from `days` calculation to `SHIPSTATION_SINCE_DATE` env var (default `2025-01-01`)
- [ ] Update API call to use fixed `since_date` instead of `start_dt = now - timedelta(days)`
- [ ] Test: Run sync, verify 2025 orders are fetched

**Task 1.2: Add Sync Status UI**
- [ ] Update `app/eqms/modules/shipstation_sync/admin.py::shipstation_index()`
- [ ] Query: Last sync run, last order date present, sync stats
- [ ] Update template: `app/eqms/templates/admin/shipstation/index.html`
- [ ] Display: `SHIPSTATION_SINCE_DATE` value, last order date, sync button

**Task 1.3: Backfill 2025 Orders**
- [ ] Set `SHIPSTATION_SINCE_DATE=2025-01-01` in production env
- [ ] Run sync via admin UI
- [ ] Verify: Query `distribution_log_entries` for 2025 months
- [ ] Spot check: Known 2025 order IDs appear

**Acceptance:** Sales Dashboard and Customer Profiles show 2025 orders

### Phase 2: Data Model Cohesion (P0)

**Task 2.1: Enforce Customer Linking in Distribution Log**
- [ ] Update `app/eqms/modules/rep_traceability/admin.py::distribution_log_new_post()` (line 99)
- [ ] Make `customer_id` required (not nullable for manual entries)
- [ ] Add customer dropdown with search (use select2 or similar, or simple HTML select with search)
- [ ] Add "Create New Customer" inline form option
- [ ] Auto-fill facility/address fields from customer record

**Task 2.2: Update Distribution Log Edit Route**
- [ ] Verify `distribution_log_edit_post()` (line 175) enforces customer validation
- [ ] Ensure `facility_name` is ALWAYS overwritten from customer record when `customer_id` provided

**Task 2.3: Update CSV Import to Link Customers**
- [ ] Verify `distribution_log_import_csv_post()` (line 270) calls `find_or_create_customer()`
- [ ] Ensure all imported entries have `customer_id` set

**Acceptance:** All distribution entries have `customer_id` linked (no orphaned entries)

### Phase 3: UI/UX Overhaul - Sales Dashboard (P1)

**Task 3.1: Visual Metric Cards**
- [ ] Update `app/eqms/templates/admin/sales_dashboard/index.html`
- [ ] Add Bootstrap-style cards for: Total Units, Total Orders, Unique Customers, First-Time, Repeat
- [ ] Use design system colors (primary, success, info)
- [ ] Large numbers, small labels

**Task 3.2: Tables with Better Styling**
- [ ] Update Sales by Month table (add `.table-striped`, `.table-hover`)
- [ ] Update Sales by SKU table
- [ ] Update Top Customers table (add links to customer profiles, "Add Note" buttons)

**Task 3.3: Quick Actions**
- [ ] Add "Log Manual Distribution" button (link to `/admin/distribution-log/new`)
- [ ] Ensure "Export CSV" button is prominent

**Acceptance:** Sales Dashboard looks professional, matches legacy visual quality

### Phase 4: UI/UX Overhaul - Customer Database (P1)

**Task 4.1: Improve List View**
- [ ] Update `app/eqms/templates/admin/customers/list.html`
- [ ] Add year filter (2025/2026) to `customers_list()` route
- [ ] Update table styling (striped, hover, responsive)
- [ ] Add "Total Orders", "Total Units", "Last Order Date" columns
- [ ] Link facility name to customer profile

**Task 4.2: Add Type Filter (First-Time/Repeat)**
- [ ] Update `customers_list()` route to compute order counts per customer
- [ ] Add "Type" filter dropdown
- [ ] Filter logic: First-Time = 1 order, Repeat = 2+ orders

**Task 4.3: Improve Empty States**
- [ ] Add icon + helpful message when no customers found
- [ ] Add "Create Customer" button in empty state

**Acceptance:** Customer Database list is professional, fast, and filterable

### Phase 5: UI/UX Overhaul - Customer Profile (P1)

**Task 5.1: Add Tabbed Interface**
- [ ] Update `app/eqms/templates/admin/customers/detail.html`
- [ ] Add tabs: Overview, Orders, Distributions, Notes
- [ ] Use design system tab component (or simple button group)

**Task 5.2: Overview Tab**
- [ ] Summary card: Address, contact info, rep assignment
- [ ] Stats card: Total orders, total units, first/last order dates, SKU breakdown

**Task 5.3: Orders Tab**
- [ ] Query: `distribution_log_entries` where `customer_id` matches, `source IN ('shipstation', 'manual', 'csv_import')`
- [ ] Table: Date, Order #, Source (badge), Items, Total Qty, Lot Numbers
- [ ] Filter: Year (2025/2026), Date range
- [ ] Link to Distribution Log entry if applicable

**Task 5.4: Distributions Tab**
- [ ] Query: ALL `distribution_log_entries` where `customer_id` matches
- [ ] Same table structure as Orders tab

**Task 5.5: Notes Tab**
- [ ] Move existing notes section to Notes tab
- [ ] Ensure "Add Note" form is at top
- [ ] Chronological list (newest first)

**Acceptance:** Customer Profile is tabbed, shows complete history, professional appearance

### Phase 6: Notes Workflow from Sales Dashboard (P1)

**Task 6.1: Add "Add Note" Workflow**
- [ ] Update `app/eqms/templates/admin/sales_dashboard/index.html`
- [ ] In Top Customers table, "Add Note" button links to `/admin/customers/<id>#notes`
- [ ] Ensure Customer Profile Notes tab has anchor `id="notes"`

**Task 6.2: Verify Notes Persistence**
- [ ] Test: Create note from Sales Dashboard → Customer Profile
- [ ] Verify note appears in Customer Profile Notes tab
- [ ] Verify note is tied to correct `customer_id`

**Acceptance:** Notes created from Sales Dashboard appear in Customer Profile

### Phase 7: Distribution Log UX Improvements (P1)

**Task 7.1: Improve Customer Selection**
- [ ] Update `app/eqms/templates/admin/distribution_log/edit.html`
- [ ] Add searchable customer dropdown (or use select2/chosen)
- [ ] Add "Create New Customer" inline form (show/hide on toggle)
- [ ] Auto-fill facility/address when customer selected

**Task 7.2: Improve List View**
- [ ] Update `app/eqms/templates/admin/distribution_log/list.html`
- [ ] Link facility name to customer profile (if `customer_id` exists)
- [ ] Add customer filter dropdown
- [ ] Improve table styling (striped, hover)

**Acceptance:** Distribution Log entry flow is smooth, customer selection is easy

### Phase 8: Testing & Verification (P0)

**Task 8.1: Manual Browser Tests**
- [ ] Sales Dashboard: Verify metrics, tables, links work
- [ ] Customer Database: Verify search, filters, pagination work
- [ ] Customer Profile: Verify tabs, orders, distributions, notes work
- [ ] Distribution Log: Verify customer selection, auto-fill, linking work
- [ ] Notes: Verify creation from Sales Dashboard → Customer Profile

**Task 8.2: ShipStation Sync Verification**
- [ ] Run sync, verify 2025 orders appear
- [ ] Verify customer linking (no NULL `customer_id` for ShipStation entries)
- [ ] Verify idempotency (re-run doesn't create duplicates)

**Task 8.3: Data Integrity Checks**
- [ ] Query: All distribution entries have `customer_id` (except legacy orphaned entries)
- [ ] Query: All notes have valid `customer_id`
- [ ] Query: Customer profiles show correct order/distribution counts

**Acceptance:** All functionality works, data is cohesive, UI is professional

---

## 9) Acceptance Criteria (Must Be Unambiguous)

### ShipStation Sync

- [ ] **AC1:** ShipStation sync pulls orders from `2025-01-01` onwards (not just last 30 days)
- [ ] **AC2:** Verification query shows rows for 2025 months: `SELECT DATE_TRUNC('month', ship_date) AS month, COUNT(*) FROM distribution_log_entries WHERE source = 'shipstation' AND ship_date >= '2025-01-01' GROUP BY month ORDER BY month;`
- [ ] **AC3:** Spot check: Known 2025 order ID from ShipStation appears in `distribution_log_entries` with `source='shipstation'` and `customer_id` linked
- [ ] **AC4:** Sales Dashboard with `start_date=2025-01-01` shows 2025 orders in stats
- [ ] **AC5:** Customer Profile for a customer with 2025 orders shows 2025 orders in Orders tab
- [ ] **AC6:** Re-running sync doesn't create duplicate entries (idempotent)

### Data Cohesion

- [ ] **AC7:** All new manual distribution entries require `customer_id` (cannot save without customer)
- [ ] **AC8:** All CSV-imported distribution entries have `customer_id` set (auto-created/linked)
- [ ] **AC9:** All ShipStation-synced distribution entries have `customer_id` set (auto-created/linked)
- [ ] **AC10:** Notes created from Sales Dashboard appear in Customer Profile Notes tab
- [ ] **AC11:** Notes are tied to correct `customer_id` (single source of truth)

### UI/UX Professionalism

- [ ] **AC12:** Sales Dashboard has visual metric cards (Total Units, Total Orders, Unique Customers, First-Time, Repeat)
- [ ] **AC13:** Sales Dashboard tables are styled (striped, hover, responsive)
- [ ] **AC14:** Customer Database list has year filter (2025/2026), type filter (First-Time/Repeat), and professional table styling
- [ ] **AC15:** Customer Profile has tabbed interface (Overview, Orders, Distributions, Notes)
- [ ] **AC16:** Customer Profile Orders tab shows 2025 and 2026 orders (if they exist)
- [ ] **AC17:** Customer Profile Distributions tab shows all distribution entries (manual + CSV + ShipStation)
- [ ] **AC18:** Distribution Log entry form has searchable customer dropdown and "Create New Customer" option
- [ ] **AC19:** All pages have consistent spacing, typography, and color scheme
- [ ] **AC20:** No debug blocks or unnecessary stats panels visible in UI

### Performance

- [ ] **AC21:** All list views paginate (50 items per page, server-side)
- [ ] **AC22:** Search is debounced (300ms) or submit-on-enter, server-side
- [ ] **AC23:** Sales Dashboard loads in < 2 seconds for typical dataset

---

## 10) "Do Not Port" List (Legacy Landmines)

### Files/Patterns to NOT Bring Forward

1. **`repqms_Proto1_reference.py.py`**
   - **Why:** Monolithic Flask app with mixed concerns (SMTP, direct SQL, rep pages)
   - **Safe Equivalent:** Use modular architecture in `app/eqms/modules/`

2. **`repqms_shipstation_sync.py.py`**
   - **Why:** Different schema, raw SQL DDL, not aligned with current architecture
   - **Safe Equivalent:** Use `app/eqms/modules/shipstation_sync/service.py::run_sync()`

3. **Direct `psycopg2` SQL queries**
   - **Why:** Bypasses SQLAlchemy ORM, harder to maintain
   - **Safe Equivalent:** Use SQLAlchemy ORM (`s.query()`, relationships)

4. **Rep-specific routes (`/rep/<slug>`)**
   - **Why:** Explicitly excluded from scope
   - **Safe Equivalent:** All functionality under `/admin/*`

5. **Email sending code (SMTP)**
   - **Why:** Explicitly excluded from scope
   - **Safe Equivalent:** Use `.eml` upload for approval evidence

6. **Hardcoded file paths**
   - **Why:** Not portable, breaks in production
   - **Safe Equivalent:** Use storage abstraction (`storage_from_config()`)

### Anti-Patterns to Avoid

1. **Duplicated customer matching logic**
   - **Anti-Pattern:** Custom string matching in multiple places
   - **Safe Equivalent:** Use `canonical_customer_key()` from `app/eqms/modules/customer_profiles/utils.py`

2. **Hardcoded date ranges**
   - **Anti-Pattern:** `start_date = '2025-01-01'` hardcoded in code
   - **Safe Equivalent:** Use env var `SHIPSTATION_SINCE_DATE` or config

3. **Brittle string matching for deduplication**
   - **Anti-Pattern:** Fuzzy string matching, manual deduplication
   - **Safe Equivalent:** Use `company_key` unique constraint + `find_or_create_customer()`

4. **Client-side only filtering**
   - **Anti-Pattern:** JavaScript-only filtering without server-side pagination
   - **Safe Equivalent:** Combine server-side pagination + optional client-side search

5. **Orphaned distribution entries**
   - **Anti-Pattern:** Distribution entries without `customer_id` (free-text `facility_name` only)
   - **Safe Equivalent:** Require `customer_id` for all new entries, auto-link on import/sync

### Safe Equivalents (Already Implemented)

- ✅ `Customer.company_key` for deduplication (unique constraint)
- ✅ `find_or_create_customer()` service function
- ✅ SQLAlchemy relationships (`customer.notes`, `customer.distributions`)
- ✅ Storage abstraction for file uploads
- ✅ Audit trail via `record_event()`
- ✅ RBAC via `require_permission()`

---

## Implementation Notes

### Design System Reference

**Current Design System:** `app/eqms/static/design-system.css`

**Key Classes:**
- `.card` - Card container
- `.button` - Primary button
- `.button--secondary` - Secondary button
- `.table` - Table styling
- `.form` - Form styling
- `.muted` - Muted text color

**Extend as needed** for metric cards, tabs, etc. Keep consistent with existing patterns.

### Database Migrations

**If adding new columns:**
- Use Alembic: `alembic revision -m "description"`
- Follow existing migration patterns in `migrations/versions/`
- Test on SQLite (dev) and PostgreSQL (prod-compatible)

### Testing Strategy

**Manual Testing:**
- Test each page in browser (Chrome/Firefox)
- Verify all links work
- Verify filters/search work
- Verify pagination works
- Verify data appears correctly

**Data Verification:**
- Run SQL queries to verify data integrity
- Check `customer_id` linking
- Check note persistence
- Check order counts

**No Unit Tests Required** (unless explicitly requested, focus on manual E2E testing)

---

## Deliverables Summary

When complete, you should have:

1. ✅ **ShipStation sync fixed** - Pulls from 2025-01-01, backfilled 2025 orders
2. ✅ **Professional UI** - Visual metric cards, styled tables, consistent spacing
3. ✅ **Tabbed Customer Profile** - Overview, Orders, Distributions, Notes tabs
4. ✅ **Data cohesion** - All distributions linked to `customer_id`, notes tied to customers
5. ✅ **Notes workflow** - Can create notes from Sales Dashboard → Customer Profile
6. ✅ **Year filters** - Customer Database and Customer Profile show 2025/2026 data
7. ✅ **Improved Distribution Log** - Better customer selection, auto-fill, linking

**Begin with Phase 1 (ShipStation Sync Fix) - it's a blocker that prevents 2025 data from appearing.**
