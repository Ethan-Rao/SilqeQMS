# REP QMS Feature Map: Essential Subset

**Date:** 2026-01-15  
**Purpose:** Inventory of essential Rep QMS features (Distribution Log, Customer Profiles, Sales Dashboard) extracted from legacy `Proto1.py`

---

## Scope

This document maps only the essential subset that must be migrated:
- **Distribution Log** (P0 - already implemented in SilqeQMS)
- **Customer Profiles** (P0/P1 - missing, needed for distribution linking)
- **Sales Dashboard** (P1/P2 - missing, analytics/reporting)

**Explicitly excluded:**
- Rep pages (`/rep/<slug>` routes)
- Email sending (SMTP code)
- Hospital targeting/facility search (not core)
- Complex analytics/clutter
- ShipStation sync (P1, can be deferred)

---

## Feature 1: Distribution Log

**Status:** ✅ Implemented in SilqeQMS (`app/eqms/modules/rep_traceability/`)

### User Story

**As an admin, I want to:**
- Create distribution entries manually (ship date, order number, facility, rep, SKU, lot, quantity)
- Import distributions from CSV files
- View and filter distribution log entries (by date, source, rep, customer, SKU)
- Edit distribution entries (with reason-for-change)
- Export filtered distributions as CSV

### Required Data Inputs

**Manual Entry:**
- Ship Date (YYYY-MM-DD, required)
- Order Number (optional, auto-generated if blank)
- Facility Name (required)
- Rep (FK to users, optional)
- Source (`'manual'`, `'csv_import'`, `'pdf_import'`, `'shipstation'`)
- SKU (one of: `211810SPT`, `211610SPT`, `211410SPT`, required)
- Lot Number (format: `SLQ-#####`, required)
- Quantity (positive integer, required)
- Optional: Address, City, State, Zip, Contact info, Tracking number, Evidence file (PDF/image)

**CSV Import:**
- CSV file with columns: Ship Date, Order Number, Facility Name, SKU, Lot, Quantity, Address, City, State, Zip, Contact info

**PDF Import (P1):**
- PDF file (master sales order PDF, shipping label PDF)
- Extracts: Order number, Facility name, SKU, Lot, Quantity (regex-based text extraction)

### UI Screens/Routes

**Legacy Rep QMS (`Proto1.py`):**
- `/admin/distribution-log` (line ~5385) - List with filters
- `/admin/manual-distribution-entry` (line ~6026) - Manual entry form
- `/admin/distributions/<id>/edit` (line ~6256) - Edit form
- `/admin/import-csv` (line ~4455) - CSV import
- `/admin/distribution-records/import-master` (line ~6886) - PDF import

**SilqeQMS Implementation:**
- `GET /admin/distribution-log` - List with filters (✅ implemented)
- `POST /admin/distribution-log/new` - Manual entry (✅ implemented)
- `GET /admin/distribution-log/<id>/edit` - Edit form (✅ implemented)
- `POST /admin/distribution-log/<id>/edit` - Update with reason (✅ implemented)
- `POST /admin/distribution-log/<id>/delete` - Delete with reason (✅ implemented)
- `POST /admin/distribution-log/import-csv` - CSV import (✅ implemented)
- `GET /admin/distribution-log/export` - CSV export (✅ implemented)
- `POST /admin/distribution-log/import-pdf` - PDF import (🟡 stub route, P1)

### Data Model Entities/Tables

**Legacy Rep QMS:**
- `devices_distributed` - One row per shipment/order
  - Columns: `id`, `order_number`, `ship_date`, `rep_id`, `customer_id`, `source`, `ss_shipment_id`
- `device_distribution_records` - One row per SKU/Lot combination per distribution
  - Columns: `dist_id` (FK), `stored_filename`, `fields_json` (canonical fields), `uploaded_at`

**SilqeQMS (Normalized):**
- `distribution_log_entries` - One row per SKU/Lot combination (normalized)
  - All required fields: `ship_date`, `order_number`, `facility_name`, `rep_id`, `sku`, `lot_number`, `quantity`, `source`
  - Optional: `customer_name` (text), `customer_id` (FK not implemented yet), address/contact fields
  - Audit: `created_by_user_id`, `updated_by_user_id`, `created_at`, `updated_at`

### Exports/Reports

**Legacy Rep QMS:**
- CSV export of filtered distribution log entries
- Columns: Ship Date, Order #, Facility, City, State, SKU, Lot, Quantity, Rep, Source

**SilqeQMS:**
- `GET /admin/distribution-log/export` - CSV download (✅ implemented)
- Filters applied: date range, source, rep, customer, SKU
- Same column format as legacy

### Audit Events

**Legacy Rep QMS:**
- Minimal audit logging (if any)

**SilqeQMS:**
- `distribution_log_entry.create` - Manual entry, CSV import
- `distribution_log_entry.update` - Edit with reason-for-change
- `distribution_log_entry.delete` - Delete with reason-for-change
- `distribution_log_entry.import_csv` - CSV import (bulk, with metadata)
- `distribution_log_entry.export` - CSV export (with filters)

### Minimal Implementation Path in SilqeQMS

**Status:** ✅ Already implemented

**Files:**
- `app/eqms/modules/rep_traceability/models.py` - `DistributionLogEntry` model
- `app/eqms/modules/rep_traceability/admin.py` - Routes
- `app/eqms/modules/rep_traceability/service.py` - CRUD, validation, deduplication
- `app/eqms/modules/rep_traceability/parsers/csv.py` - CSV parser
- `app/eqms/templates/admin/distribution_log/` - Templates

**Gaps:**
- PDF import not implemented (P1)
- `customer_id` FK not implemented (using `customer_name` text field)

---

## Feature 2: Customer Profiles

**Status:** ❌ Missing in SilqeQMS

### User Story

**As an admin, I want to:**
- View a list of all customers (facilities) with filters (name, state, rep)
- View/edit a customer profile (facility name, address, contact info, rep assignments)
- Assign reps to customers (primary rep, secondary reps)
- Add notes to customers (CRM-style activity log)
- See recent order history for each customer

### Required Data Inputs

**Customer Creation/Update:**
- Facility Name (required)
- Address (optional): address1, address2, city, state, zip
- Contact info (optional): contact_name, contact_phone, contact_email
- Rep assignments (optional): primary_rep_id, secondary rep IDs

**Customer Notes:**
- Note text (required)
- Note date (optional, defaults to today)
- Author (optional, defaults to current user)

**Filters:**
- Search query (facility name, company key)
- State filter
- Rep filter

### UI Screens/Routes

**Legacy Rep QMS (`Proto1.py`):**
- `/admin/customers` (line ~5627) - Customer list with filters
- `/admin/customers/<int:customer_id>` (line ~5760) - Customer CRM profile (edit form, notes, orders, rep assignments)
- `/admin/customer/note/add` (line ~5175) - Add note (POST)
- `/admin/customer/<int:customer_id>/note/<int:note_id>/edit` (line ~5240) - Edit note (POST)
- `/admin/customer/<int:customer_id>/note/<int:note_id>/delete` (line ~5329) - Delete note (POST/DELETE)
- `/admin/customer/<int:customer_id>/notes/json` (line ~5997) - Get notes as JSON (AJAX)

**SilqeQMS Implementation:**
- ❌ Not implemented yet

**Recommended Implementation:**
- `GET /admin/customers` - Customer list with filters
- `GET /admin/customers/new` - Create customer form
- `POST /admin/customers/new` - Create customer
- `GET /admin/customers/<id>` - Customer profile (view/edit, notes, rep assignments, order history)
- `POST /admin/customers/<id>` - Update customer
- `POST /admin/customers/<id>/notes` - Add note
- `POST /admin/customers/<id>/notes/<note_id>/edit` - Edit note
- `POST /admin/customers/<id>/notes/<note_id>/delete` - Delete note
- `POST /admin/customers/<id>/reps` - Assign/update rep assignments

### Data Model Entities/Tables

**Legacy Rep QMS (`Proto1.py` lines 1023-1086):**

**`customers` table:**
- `id` (PK)
- `company_key` (unique, canonical key from facility name)
- `facility_name` (required)
- `address1`, `address2`, `city`, `state`, `zip`
- `contact_name`, `contact_phone`, `contact_email`
- `primary_rep_id` (FK to reps)
- `created_at`, `updated_at`

**`customer_notes` table:**
- `id` (PK)
- `customer_id` (FK to customers, CASCADE delete)
- `note_text` (required)
- `note_date` (optional, defaults to CURRENT_DATE)
- `author` (text, optional)
- `created_at`, `updated_at`

**`customer_rep_assignments` table:**
- `id` (PK)
- `customer_id` (FK to customers, CASCADE delete)
- `rep_id` (FK to reps)
- `is_primary` (boolean, defaults to FALSE)
- `created_at`
- Unique constraint: `(customer_id, rep_id)`

**SilqeQMS (Proposed):**
- Same schema (see `04_MINIMAL_DATA_MODEL_EXTENSIONS.md`)

### Exports/Reports

**Legacy Rep QMS:**
- No explicit export, but customer data visible in Sales Dashboard export

**SilqeQMS (Recommended):**
- No export needed initially (can be added later if needed)
- Customer data visible in Distribution Log export (via `customer_id` FK)

### Audit Events

**Legacy Rep QMS:**
- Minimal audit logging (if any)

**SilqeQMS (Recommended):**
- `customer.create` - Customer creation
- `customer.update` - Customer update (with reason-for-change for edits)
- `customer.delete` - Customer deletion (if implemented)
- `customer_note.create` - Note added
- `customer_note.update` - Note edited
- `customer_note.delete` - Note deleted
- `customer_rep_assignment.create` - Rep assigned
- `customer_rep_assignment.update` - Rep assignment updated
- `customer_rep_assignment.delete` - Rep assignment removed

### Minimal Implementation Path in SilqeQMS

**Recommended:** Implement as new module `app/eqms/modules/customer_profiles/`

**Files to Create:**
- `app/eqms/modules/customer_profiles/__init__.py`
- `app/eqms/modules/customer_profiles/models.py` - `Customer`, `CustomerNote` models
- `app/eqms/modules/customer_profiles/admin.py` - Routes
- `app/eqms/modules/customer_profiles/service.py` - CRUD, rep assignment logic
- `app/eqms/templates/admin/customers/list.html` - Customer list
- `app/eqms/templates/admin/customers/detail.html` - Customer profile

**Key Functions to Port:**
- `find_or_create_customer()` - Find or create customer by `company_key`
- `canonical_customer_key()` - Normalize facility name to canonical key
- `ensure_rep_assignment()` - Assign rep to customer
- `pick_rep_for_customer()` - Get primary rep for customer

**What NOT to Port:**
- Complex customer merge logic (if exists)
- Customer file storage paths (rep-specific)
- Legacy `new_customer_records` table (not needed)

---

## Feature 3: Sales Dashboard

**Status:** ❌ Missing in SilqeQMS

### User Story

**As an admin, I want to:**
- View a sales dashboard showing aggregated statistics (total orders, units, customers)
- See breakdown of first-time vs repeat customers
- See SKU breakdown (total units per SKU)
- See lot consumption (which lots used, first/last used dates)
- Filter by date window (e.g., Q1 2026 onwards)
- Export dashboard data as CSV

### Required Data Inputs

**Dashboard View:**
- Date window filter (start date, e.g., `2026-01-01`)
- All distribution log entries (queried from `distribution_log_entries`)

**Aggregations:**
- Total orders (count distinct order_number per facility)
- Total units (sum quantity)
- Total customers (count distinct facility/customer)
- First-time customers (customers with exactly 1 order ever)
- Repeat customers (customers with 2+ orders)
- SKU breakdown (sum quantity per SKU)
- Lot consumption (sum quantity per lot, track first/last used dates)

### UI Screens/Routes

**Legacy Rep QMS (`Proto1.py`):**
- `/admin/sales-dashboard` (line ~4633) - Dashboard view
- `/admin/sales-dashboard/export` (line ~4983) - Export CSV

**SilqeQMS Implementation:**
- ❌ Not implemented yet

**Recommended Implementation:**
- `GET /admin/sales-dashboard` - Dashboard view (aggregations computed on-demand)
- `GET /admin/sales-dashboard/export` - Export CSV (same aggregations)

### Data Model Entities/Tables

**Legacy Rep QMS:**
- No separate aggregates table
- Aggregations computed on-demand from `devices_distributed` + `device_distribution_records`
- Uses `fetch_distribution_records()` helper to normalize data

**SilqeQMS (Recommended):**
- No separate aggregates table initially (compute on-demand from `distribution_log_entries`)
- Add caching layer later if performance becomes issue (P2)
- Store aggregations in Redis or materialized view if needed

### Exports/Reports

**Legacy Rep QMS (`Proto1.py` lines 4983-5173):**
- CSV export with columns:
  - Type (First-Time / Repeat)
  - Ship Date, Order Number, Facility Name, Address, City, State, Zip
  - Total Units, Item Count
  - SKU, Lot, Quantity (one row per SKU/Lot)
  - Source, Customer ID, Dist ID

**SilqeQMS (Recommended):**
- Same CSV format
- Export via `GET /admin/sales-dashboard/export`

### Audit Events

**Legacy Rep QMS:**
- No audit events for dashboard view

**SilqeQMS (Recommended):**
- `sales_dashboard.view` - Dashboard viewed (optional, for access tracking)
- `sales_dashboard.export` - Dashboard exported (with filters)

### Minimal Implementation Path in SilqeQMS

**Recommended:** Implement as view-only route in `rep_traceability` module (or separate `sales_dashboard` module if it grows)

**Files to Create/Modify:**
- `app/eqms/modules/rep_traceability/admin.py` - Add dashboard routes
- `app/eqms/modules/rep_traceability/service.py` - Add aggregation functions
- `app/eqms/templates/admin/sales_dashboard/index.html` - Dashboard template

**Key Functions to Port (Simplified):**
- Aggregation logic from `admin_sales_dashboard()` (lines 4633-4976)
- First-time vs repeat classification (lines 4812-4826)
- SKU/lot breakdown (lines 4770-4780)
- Export logic from `admin_sales_dashboard_export()` (lines 4983-5173)

**What NOT to Port:**
- Complex sync freshness metrics (if not needed)
- Dashboard refresh button logic (keep simple, no auto-refresh)
- Per-company totals from external CSV (if exists, remove)
- Complex facility targeting/search features

**Key Simplifications:**
- Remove date normalization complexity (use simple date filtering)
- Remove sync status checks (if not needed)
- Remove iframe token auth (if not needed)
- Keep aggregations on-demand (no materialized views initially)

---

## Feature Comparison: Legacy vs SilqeQMS

### Distribution Log

| Aspect | Legacy Rep QMS | SilqeQMS | Status |
|--------|----------------|----------|--------|
| Manual entry | ✅ | ✅ | ✅ Implemented |
| CSV import | ✅ | ✅ | ✅ Implemented |
| PDF import | ✅ | ❌ | 🟡 P1 stub route |
| Edit/Delete | ✅ | ✅ | ✅ Implemented |
| Export | ✅ | ✅ | ✅ Implemented |
| Filters | ✅ | ✅ | ✅ Implemented |
| Customer linking | ✅ (FK) | 🟡 (text field) | 🟡 Partial |
| Audit trail | ❌ | ✅ | ✅ Implemented |

### Customer Profiles

| Aspect | Legacy Rep QMS | SilqeQMS | Status |
|--------|----------------|----------|--------|
| Customer table | ✅ | ❌ | ❌ Missing |
| Customer CRUD | ✅ | ❌ | ❌ Missing |
| Customer notes | ✅ | ❌ | ❌ Missing |
| Rep assignments | ✅ | ❌ | ❌ Missing |
| Customer list | ✅ | ❌ | ❌ Missing |
| Customer profile | ✅ | ❌ | ❌ Missing |

### Sales Dashboard

| Aspect | Legacy Rep QMS | SilqeQMS | Status |
|--------|----------------|----------|--------|
| Dashboard route | ✅ | ❌ | ❌ Missing |
| Aggregations | ✅ (on-demand) | ❌ | ❌ Missing |
| First-time/Repeat | ✅ | ❌ | ❌ Missing |
| SKU breakdown | ✅ | ❌ | ❌ Missing |
| Lot tracking | ✅ | ❌ | ❌ Missing |
| Export | ✅ | ❌ | ❌ Missing |

---

## Key Functions from Legacy Rep QMS

### Safe to Port (Small Utilities)

1. **`canonical_customer_key(name: str) -> str`** (line ~2158)
   - Normalizes facility name to canonical key (uppercase, special chars removed)
   - Used for customer deduplication
   - **Justification:** Small utility function, no dependencies

2. **`find_or_create_customer(...)`** (line ~2184)
   - Finds existing customer by `company_key` or creates new
   - Updates existing customer if fields changed
   - **Justification:** Core customer management logic, reusable

3. **`ensure_rep_assignment(customer_id, rep_id, ...)`** (line ~214)
   - Assigns rep to customer, handles primary rep logic
   - **Justification:** Small helper, reusable

4. **`_normalize_ship_date_ymd(...)`** (date normalization)
   - Normalizes ship dates to YYYY-MM-DD string format
   - **Justification:** Prevents datetime subscriptable errors

5. **Field normalization helpers**
   - Text normalization, SKU validation, lot validation
   - **Justification:** Already partially ported in SilqeQMS utils

### Rewrite Only (Bloat/Complexity)

1. **`fetch_distribution_records()`** (normalization logic)
   - Complex function that normalizes `devices_distributed` + `device_distribution_records`
   - **Justification:** SilqeQMS already has normalized schema, don't need this

2. **`_build_distributions()`** (grouping logic)
   - Groups shipments into orders
   - **Justification:** Can be simplified for SilqeQMS normalized schema

3. **Sales Dashboard aggregation logic** (lines 4633-4976)
   - Complex date normalization, sync freshness checks
   - **Justification:** Rewrite to use SilqeQMS normalized schema, remove bloat

4. **Hospital targeting/facility search** (if exists)
   - Facility cache, doctor search
   - **Justification:** Not core to distribution tracking

5. **Rep dashboard templates/logic**
   - `/rep/<slug>` routes, rep-specific UI
   - **Justification:** Explicitly excluded from migration

---

## References

- **Legacy Rep QMS:** `C:\Users\Ethan\OneDrive\Desktop\UI\RepsQMS\Proto1.py`
- **SilqeQMS Implementation:** `app/eqms/modules/rep_traceability/`
- **Master Spec:** [docs/REP_SYSTEM_MIGRATION_MASTER.md](docs/REP_SYSTEM_MIGRATION_MASTER.md)
- **Schema:** [docs/REP_SYSTEM_MINIMAL_SCHEMA.md](docs/REP_SYSTEM_MINIMAL_SCHEMA.md)
- **UI Map:** [docs/REP_SYSTEM_UI_MAP.md](docs/REP_SYSTEM_UI_MAP.md)
