# Lean Migration Plan: Customer Profiles + Sales Dashboard

**Date:** 2026-01-15  
**Purpose:** Dependency-ordered checklist for bringing Customer Profiles and Sales Dashboard into SilqeQMS

---

## Priority Levels

- **P0 (Must Have):** Critical for production use
- **P1 (Important):** Needed for business visibility, can be deferred if necessary
- **P2 (Nice to Have):** Enhanced features, can be added later

---

## P0 Tasks (Must Have - If Customer Linking Required)

### Task 1: Create Customers Table Migration

**Files to Create/Modify:**
- `migrations/versions/<revision>_add_customers_table.py` (new file)
- `app/eqms/modules/customer_profiles/models.py` (new file)
- `app/eqms/models.py` (add import at bottom)

**Steps:**
1. Run `alembic revision -m "add customers table"`
2. Implement `upgrade()` with:
   - `customers` table (see `04_MINIMAL_DATA_MODEL_EXTENSIONS.md`)
   - `customer_notes` table (optional, for CRM)
   - `customer_rep_assignments` table (if rep assignments needed)
   - Indexes as specified
3. Implement `downgrade()` to drop tables
4. Create `Customer`, `CustomerNote` models in `app/eqms/modules/customer_profiles/models.py`
5. Import models in `app/eqms/models.py` tail

**Acceptance Test:**
- `alembic upgrade head` runs without errors
- `alembic downgrade -1` runs without errors
- All tables exist with correct columns and constraints
- Models import without errors

**Definition of Done:**
- Migration file created and tested
- Models match schema from `04_MINIMAL_DATA_MODEL_EXTENSIONS.md` exactly
- Alembic autogenerate detects no differences

---

### Task 2: Add customer_id FK to distribution_log_entries

**Files to Create/Modify:**
- `migrations/versions/<revision>_add_customer_id_fk_to_distribution_log.py` (new file)
- `app/eqms/modules/rep_traceability/models.py` (add `customer_id` FK column)

**Steps:**
1. Run `alembic revision -m "add customer_id fk to distribution_log_entries"`
2. Implement `upgrade()`:
   - Add `customer_id` INTEGER column (nullable)
   - Add FK constraint to `customers(id)`
   - Add index on `customer_id`
   - Migrate existing `customer_name` values (optional, can be done manually later)
3. Update `DistributionLogEntry` model to include `customer_id` FK
4. Keep `customer_name` text field for backward compatibility (deprecated)

**Acceptance Test:**
- Migration runs without errors
- `distribution_log_entries` table has `customer_id` column and FK
- Existing entries remain valid (FK nullable)

**Definition of Done:**
- Migration file created and tested
- Model updated with `customer_id` FK
- Existing data remains intact

---

### Task 3: Create Customer Profiles Service Functions

**Files to Create/Modify:**
- `app/eqms/modules/customer_profiles/service.py` (new file)

**Functions to Implement:**
- `find_or_create_customer(session, facility_name: str, ...) -> Customer`
  - Find by `company_key` (canonicalized facility name)
  - Create if not found
  - Update if fields changed
- `canonical_customer_key(name: str) -> str`
  - Normalize facility name to canonical key (uppercase, special chars removed)
- `ensure_rep_assignment(session, customer_id: int, rep_id: int, ...) -> None`
  - Assign rep to customer
  - Handle primary rep logic
- `get_customer_by_id(session, customer_id: int) -> Customer | None`
- `create_customer(session, data: dict, user: User) -> Customer`
- `update_customer(session, customer: Customer, data: dict, user: User) -> Customer`

**Acceptance Test:**
- `find_or_create_customer()` finds existing by company_key
- `find_or_create_customer()` creates new if not found
- `canonical_customer_key()` normalizes correctly (e.g., "Hospital A" → "HOSPITALA")
- Rep assignment logic works correctly

**Definition of Done:**
- All service functions implemented
- Functions handle edge cases (null values, empty strings)
- Audit logging via `record_event()` on create/update

---

### Task 4: Create Customer Profiles Routes

**Files to Create/Modify:**
- `app/eqms/modules/customer_profiles/admin.py` (new file)
- `app/eqms/__init__.py` (register blueprint)

**Routes:**
- `GET /admin/customers` → `customer_list()` (with filters: search query, state, rep)
- `GET /admin/customers/new` → `customer_new_get()`
- `POST /admin/customers/new` → `customer_new_post()`
- `GET /admin/customers/<id>` → `customer_detail(customer_id)`
- `POST /admin/customers/<id>` → `customer_update(customer_id)` (requires reason-for-change)
- `POST /admin/customers/<id>/notes` → `customer_note_add(customer_id)`
- `POST /admin/customers/<id>/notes/<note_id>/edit` → `customer_note_edit(customer_id, note_id)`
- `POST /admin/customers/<id>/notes/<note_id>/delete` → `customer_note_delete(customer_id, note_id)`
- `POST /admin/customers/<id>/reps` → `customer_rep_assign(customer_id)`

**Permissions:**
- List: `customers.view`
- Create: `customers.create`
- Edit: `customers.edit`
- Delete: `customers.delete` (if implemented)
- Notes: `customers.notes` (same as edit)

**Acceptance Test:**
- List page shows customers with filters
- Create form creates customer and redirects to list
- Detail page shows customer profile, notes, rep assignments, order history
- Edit form updates customer with reason-for-change
- Notes can be added/edited/deleted
- Rep assignments can be updated

**Definition of Done:**
- All routes implemented with RBAC decorators
- Forms validate inputs using service functions
- Audit events logged on create/update/delete
- Navigation updated to include Customers menu item

---

### Task 5: Create Customer Profiles Templates

**Files to Create/Modify:**
- `app/eqms/templates/admin/customers/list.html` (new file)
- `app/eqms/templates/admin/customers/detail.html` (new file)
- `app/eqms/templates/admin/customers/edit.html` (new file)
- `app/eqms/templates/_layout.html` (add Customers menu item)

**Requirements:**
- Reuse `_layout.html` base template
- Use existing design system (`design-system.css`)
- List: table with filters (search, state, rep), pagination
- Detail: customer profile with edit form, notes section, rep assignments, order history
- Edit: form with all fields from schema (required/optional marked)

**Acceptance Test:**
- Templates render without errors
- Forms submit correctly
- Filters work via query params
- UI matches existing admin pages style

**Definition of Done:**
- All templates created and functional
- Consistent with existing admin UI patterns
- Navigation menu includes Customers link

---

### Task 6: Update Distribution Log Forms to Select Customers

**Files to Create/Modify:**
- `app/eqms/templates/admin/distribution_log/edit.html` (add customer dropdown)
- `app/eqms/modules/rep_traceability/admin.py` (update create/update logic)
- `app/eqms/modules/rep_traceability/service.py` (update to handle customer_id)

**Steps:**
1. Add customer dropdown to manual entry/edit form
2. Allow creating new customer inline (or redirect to customer form)
3. Update `create_distribution_entry()` to accept `customer_id`
4. Update `update_distribution_entry()` to handle customer linking
5. Auto-link customer when facility_name matches (via `find_or_create_customer()`)

**Acceptance Test:**
- Manual entry form shows customer dropdown
- Selecting customer populates facility_name and address fields
- Creating entry links to selected customer
- Auto-linking works when facility_name matches existing customer

**Definition of Done:**
- Forms updated to support customer selection
- Service functions handle customer_id FK
- Backward compatible with existing entries (customer_id nullable)

---

### Task 7: Extend Seed Script with Customer Permissions

**Files to Create/Modify:**
- `scripts/init_db.py`

**Steps:**
1. Add permission creation for:
   - `customers.view` - View customer list
   - `customers.create` - Create customers
   - `customers.edit` - Edit customers
   - `customers.delete` - Delete customers (if implemented)
   - `customers.notes` - Add/edit/delete notes
2. Grant all customer permissions to `admin` role
3. Optionally grant to `quality`, `ops` roles

**Acceptance Test:**
- Run `python scripts/init_db.py`
- Check database: all permissions exist
- Check `admin` role has all customer permissions

**Definition of Done:**
- All customer permission keys seeded
- `admin` role has full access

---

## P1 Tasks (Important)

### Task 8: Implement Sales Dashboard Route

**Files to Create/Modify:**
- `app/eqms/modules/rep_traceability/admin.py` (add dashboard routes)
- `app/eqms/modules/rep_traceability/service.py` (add aggregation functions)
- `app/eqms/templates/admin/sales_dashboard/index.html` (new file)

**Routes:**
- `GET /admin/sales-dashboard` → `sales_dashboard()`
- `GET /admin/sales-dashboard/export` → `sales_dashboard_export()`

**Aggregations (compute on-demand):**
- Total orders (count distinct order_number per facility, within date window)
- Total units (sum quantity, within date window)
- Total customers (count distinct facility/customer, lifetime)
- First-time customers (customers with exactly 1 order ever)
- Repeat customers (customers with 2+ orders)
- SKU breakdown (sum quantity per SKU, within date window)
- Lot tracking (sum quantity per lot, first/last used dates)

**Steps:**
1. Implement `compute_dashboard_aggregates(session, start_date: date | None) -> dict`:
   - Query all `distribution_log_entries`
   - Group by facility/customer (canonical key)
   - Compute first-time vs repeat classification
   - Aggregate SKU/lot totals
   - Return dict with stats
2. Implement `sales_dashboard()` route:
   - Call `compute_dashboard_aggregates()`
   - Render dashboard template with stats
3. Implement `sales_dashboard_export()` route:
   - Same aggregations as dashboard
   - Export as CSV (one row per order, with Type: First-Time/Repeat)

**Acceptance Test:**
- Dashboard page loads and shows stats
- Aggregations match Distribution Log data
- First-time vs repeat classification is correct
- SKU breakdown sums match Distribution Log
- Export generates valid CSV

**Definition of Done:**
- Dashboard route implemented and functional
- Aggregations computed correctly from `distribution_log_entries`
- Export works end-to-end
- Audit events logged (view, export)

---

### Task 9: Create Sales Dashboard Template

**Files to Create/Modify:**
- `app/eqms/templates/admin/sales_dashboard/index.html` (new file)
- `app/eqms/templates/_layout.html` (add Sales Dashboard menu item)

**Requirements:**
- Display stats: total orders, units, customers (lifetime, windowed)
- Show first-time vs repeat customer breakdown
- Show SKU breakdown (table or list)
- Show lot tracking (table with first/last used dates)
- Date window filter (default: 2026-01-01 onwards)
- Export button

**UI Layout (lean):**
```
┌─────────────────────────────────────────────────────────────┐
│ Sales Dashboard                                    [Export] │
├─────────────────────────────────────────────────────────────┤
│ Date Window: [2026-01-01] (YYYY-MM-DD)                     │
│                                                              │
│ Stats:                                                       │
│ - Total Orders: 123 (windowed), 456 (lifetime)              │
│ - Total Units: 1,234 (windowed)                             │
│ - Total Customers: 45 (lifetime)                            │
│   - First-Time: 12                                          │
│   - Repeat: 33                                              │
│                                                              │
│ SKU Breakdown (windowed):                                   │
│ - 211810SPT: 500 units                                      │
│ - 211610SPT: 400 units                                      │
│ - 211410SPT: 334 units                                      │
│                                                              │
│ Lot Tracking:                                                │
│ - SLQ-12345: 100 units (first: 2026-01-05, last: 2026-01-15)│
│ - ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

**Acceptance Test:**
- Dashboard renders without errors
- Stats display correctly
- Date filter works (if implemented)
- Export button triggers CSV download

**Definition of Done:**
- Template created and functional
- Stats displayed clearly
- Export button works

---

### Task 10: Extend Seed Script with Sales Dashboard Permissions

**Files to Create/Modify:**
- `scripts/init_db.py`

**Steps:**
1. Add permission creation:
   - `sales_dashboard.view` - View dashboard
   - `sales_dashboard.export` - Export dashboard data
2. Grant permissions to `admin` role
3. Optionally grant to `quality`, `ops`, `readonly` roles

**Acceptance Test:**
- Permissions seeded correctly
- Admin role has access

**Definition of Done:**
- Permissions created
- Role mappings configured

---

## P2 Tasks (Nice to Have - Deferred)

### Task 11: PDF Import Implementation (P2 - Deferred)

**Files to Create/Modify:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (new file)
- `app/eqms/modules/rep_traceability/admin.py` (update PDF import route)

**Steps:**
1. Implement PDF parser (extract text, parse order number, facility, SKU/lot)
2. Update `POST /admin/distribution-log/import-pdf` route
3. Handle extraction errors gracefully

**Priority:** P2 (deferred until needed)

---

### Task 12: ShipStation Sync (P2 - Deferred)

**Files to Create/Modify:**
- `app/eqms/modules/rep_traceability/shipstation/` (new module)
- Background job integration (cron or job queue)

**Steps:**
1. Extract ShipStation API client code
2. Create sync function that creates `distribution_log_entries`
3. Integrate with background job runner

**Priority:** P2 (deferred until needed)

---

## Dependency Order

**Phase 1: Customer Profiles (P0)**
1. Task 1: Create Customers Table Migration
2. Task 2: Add customer_id FK to distribution_log_entries
3. Task 3: Create Customer Profiles Service Functions
4. Task 4: Create Customer Profiles Routes
5. Task 5: Create Customer Profiles Templates
6. Task 6: Update Distribution Log Forms to Select Customers
7. Task 7: Extend Seed Script with Customer Permissions

**Phase 2: Sales Dashboard (P1)**
8. Task 8: Implement Sales Dashboard Route
9. Task 9: Create Sales Dashboard Template
10. Task 10: Extend Seed Script with Sales Dashboard Permissions

**Phase 3: Enhancements (P2)**
11. Task 11: PDF Import Implementation (deferred)
12. Task 12: ShipStation Sync (deferred)

---

## Priority Decisions

### Customer Profiles: P0 or P1?

**Decision Criteria:**
- **P0 (Must Have):** If customer linking is required for Distribution Log reliability
- **P1 (Important):** If standalone CRM is acceptable, customer linking can be added later

**Recommendation:** **P0** if production use requires reliable customer-based filtering/aggregation. **P1** if Distribution Log can work with free-text `customer_name` initially.

### Sales Dashboard: P1 or P2?

**Decision Criteria:**
- **P1 (Important):** If business visibility/analytics are needed soon
- **P2 (Nice to Have):** If manual calculation from Distribution Log export is acceptable

**Recommendation:** **P1** (important for business visibility, but not critical for core workflow).

---

## Acceptance Criteria Summary

**Customer Profiles:**
- Can view list of customers with filters
- Can create/edit customers
- Can add/edit/delete customer notes
- Can assign reps to customers
- Distribution Log entries can link to customers (FK)
- Forms support customer selection

**Sales Dashboard:**
- Can view dashboard with aggregations
- Aggregations computed correctly from Distribution Log
- First-time vs repeat classification accurate
- SKU breakdown matches Distribution Log
- Export generates valid CSV

---

## References

- **Progress Summary:** [docs/review/00_PROGRESS_SUMMARY.md](docs/review/00_PROGRESS_SUMMARY.md)
- **Feature Map:** [docs/review/01_REP_QMS_FEATURE_MAP.md](docs/review/01_REP_QMS_FEATURE_MAP.md)
- **Gap Matrix:** [docs/review/02_GAP_MATRIX.md](docs/review/02_GAP_MATRIX.md)
- **Data Model:** [docs/review/04_MINIMAL_DATA_MODEL_EXTENSIONS.md](docs/review/04_MINIMAL_DATA_MODEL_EXTENSIONS.md)
- **Schema Source:** [docs/REP_SYSTEM_MINIMAL_SCHEMA.md](docs/REP_SYSTEM_MINIMAL_SCHEMA.md)
