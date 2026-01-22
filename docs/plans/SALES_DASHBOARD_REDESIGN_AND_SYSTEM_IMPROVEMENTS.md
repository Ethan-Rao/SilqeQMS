# Sales Dashboard Redesign & System Improvements — Implementation Spec

**Date:** 2026-01-19  
**Purpose:** Developer-ready implementation plan for professional sales/admin dashboard redesign, lot tracking accuracy, customer cleanup, rep assignment, permission fixes, and ShipStation sync improvements.

---

## 1) Executive Summary

### What Changes and Why

**Primary Goals:**
1. **Professional Sales Dashboard:** Redesign to match legacy template styling, remove clutter (month-by-month tables, "Top Customers"), add focused "Recent Orders" lists for NEW vs REPEAT customers with inline note-taking
2. **Lot Tracking Accuracy:** Use Lot Log CSV as source of truth, map incorrect lot names to canonical names, show only correct lots from current year, calculate Active Inventory
3. **Distribution Log Enhancement:** Add in-page detail modals showing order context and customer stats without navigation
4. **Permission Fix:** Resolve 403 Forbidden on PDF import route for ethanr@silq.tech (superadmin must have all permissions)
5. **Customer Cleanup:** Delete customers with 0 orders, sort by most recent order, remove "Find Duplicates" button, enforce Sales Orders as source of truth
6. **Rep Assignment:** Support rep assignment to customers, filter distribution log by rep, generate tracing reports by rep, store rep addresses with ZIP validation
7. **ShipStation Sync Throttling:** Add month-scoped sync capability to prevent timeouts

**Impact:**
- **User Experience:** More professional, less cluttered interface with in-page functionality
- **Data Integrity:** Lot tracking uses authoritative source, customer cleanup prevents orphaned records
- **Performance:** Month-scoped sync reduces API timeouts
- **Accessibility:** Superadmin has full access to all features

---

## 2) Current Problems

### Problem 1: Sales Dashboard Looks Amateur
- **Issue:** Current dashboard has "Sales by Month" table (not needed) and "Top Customers" table (not desired)
- **User Impact:** Cluttered interface, hard to focus on actionable information
- **Evidence:** Template shows month-by-month breakdown and top customers by volume

### Problem 2: Lot Tracking Shows Incorrect Lots
- **Issue:** Several "lots" displayed are actually SKU names (e.g., "211810SPT" shown as lot)
- **User Impact:** Incorrect inventory tracking, confusion about actual lot numbers
- **Evidence:** Lot Log CSV contains "Correct Lot Name" column for mapping, but system may not be applying corrections consistently

### Problem 3: Lot Tracking Shows All Years
- **Issue:** Lot Tracking view shows lots from all years, not just current year
- **User Impact:** Cluttered view, hard to see current inventory
- **Evidence:** No year filter applied to lot tracking aggregation

### Problem 4: No Active Inventory Calculation
- **Issue:** Cannot see remaining inventory per lot (produced - distributed)
- **User Impact:** Cannot track which lots are still available for distribution
- **Evidence:** Lot Log CSV has "Total Units in Lot" column, but system doesn't calculate remaining inventory

### Problem 5: Distribution Log Lacks In-Page Details
- **Issue:** Must navigate away to see order context or customer stats
- **User Impact:** Slow workflow, context switching required
- **Evidence:** No detail modals or expandable rows in distribution log list

### Problem 6: 403 Forbidden on PDF Import
- **Issue:** `/admin/sales-orders/import-pdf` returns 403 with message "Missing permission sales_orders.import"
- **User Impact:** ethanr@silq.tech cannot import PDF files
- **Evidence:** Route requires `sales_orders.import` permission, but admin role may not have it assigned
- **Root Cause:** Permission exists in `scripts/init_db.py` but may not be assigned to admin role, or user may not have admin role

### Problem 7: Customers with 0 Orders Clutter Database
- **Issue:** Customers exist with no associated orders/distributions
- **User Impact:** Cluttered customer list, confusion about active customers
- **Evidence:** No cleanup script to remove orphaned customers

### Problem 8: Customer Database Not Sorted by Recency
- **Issue:** Customers sorted alphabetically, not by most recent order
- **User Impact:** Hard to find recently active customers
- **Evidence:** Current sort is `ORDER BY facility_name ASC`

### Problem 9: "Find Duplicates" Button Exists
- **Issue:** UI has "Find Duplicates" button that should be removed
- **User Impact:** Cluttered UI, unnecessary feature
- **Evidence:** Button exists in customer database template

### Problem 10: No Rep Assignment on Customer Profiles
- **Issue:** Cannot assign a rep to a customer account
- **User Impact:** Cannot track which rep manages which customer
- **Evidence:** `customers.primary_rep_id` exists but may not be editable in UI

### Problem 11: Cannot Filter Distribution Log by Rep
- **Issue:** Distribution log filter doesn't include rep filter
- **User Impact:** Cannot see distributions for a specific rep
- **Evidence:** Filter form may not include rep dropdown

### Problem 12: Tracing Reports Cannot Be Filtered by Rep
- **Issue:** Tracing report generation doesn't support rep filter
- **User Impact:** Cannot generate rep-specific compliance reports
- **Evidence:** Tracing report filters may not include `rep_id`

### Problem 13: Rep Address Not Stored
- **Issue:** Reps (users) don't have address fields for US ZIP code validation
- **User Impact:** Cannot store rep contact information
- **Evidence:** `users` table only has `email`, `password_hash`, `is_active`

### Problem 14: ShipStation Sync Times Out
- **Issue:** Full sync from 2025-01-01 times out due to too many API requests
- **User Impact:** Cannot complete sync, missing data
- **Evidence:** No month-scoped sync capability

---

## 3) Target UX / Page-by-Page Requirements

### 3.1 Sales Dashboard

**Layout Structure:**
```
[Header: Sales Dashboard]
  [Date Filter: Since: YYYY-MM-DD] [Apply] [+ Log Entry] [Export CSV]

[Metric Cards Row]
  [Total Units (All Time)] [Total Orders (Windowed)] [Unique Customers] [First-Time] [Repeat]

[Main Content: Two-Column Layout]
  [Left Column: Recent Orders Lists]
    [Recent Orders from NEW Customers]
    [Recent Orders from REPEAT Customers]
  [Right Column: SKU & Lot Tracking]
    [Sales by SKU]
    [Lot Tracking (Current Year Only)]
```

**Required Changes:**
1. **Remove "Sales by Month" table** - Delete entire section (lines 56-83 in current template)
2. **Remove "Top Customers" table** - Delete entire section (lines 148-218 in current template)
3. **Add "Recent Orders from NEW Customers" list:**
   - Show orders from customers with exactly 1 lifetime order
   - Limit to 20 most recent orders (by `ship_date DESC`)
   - Each row shows:
     - Customer name (linked to profile)
     - Order date
     - Order number
     - Total units for that order
     - Quick actions: [View Details] [Add Note] [View Profile]
   - Inline note editor: Click "Add Note" → Inline form appears → Save → Note appears in list item and propagates to customer profile
4. **Add "Recent Orders from REPEAT Customers" list:**
   - Show orders from customers with 2+ lifetime orders
   - Same structure as NEW customers list
   - Limit to 20 most recent orders
5. **Move "Sales by SKU" to Right Column:**
   - Keep existing table structure
   - Position in right column (not left)
6. **Move "Lot Tracking" to Right Column:**
   - Keep existing table structure
   - Add "Active Inventory" column (right-most)
   - Filter to current year only (ship_date >= current_year-01-01 AND ship_date < next_year-01-01)
   - Show only correct lot numbers (mapped via Lot Log)
7. **Styling:**
   - Match legacy template: Bootstrap card styling, consistent spacing (14px gaps), clean typography
   - Remove any "debuggy" blocks or unnecessary stats

**Note-Taking Workflow:**
- Click "Add Note" on any order row → Inline form appears (text input + date picker + Save button)
- Save → Note created via AJAX POST to `/admin/customers/<customer_id>/notes`
- Note appears in list item (small badge/icon indicating note exists)
- Note automatically appears on customer profile and customer database page
- Notes are editable: Click note badge → Edit form appears → Save updates note everywhere

**Backend Requirements:**
- Service function: `get_recent_orders_by_customer_type(s, *, customer_type: 'new' | 'repeat', limit: int = 20, start_date: date | None) -> list[dict]`
- Endpoint: `GET /admin/sales-dashboard/order-note-form/<customer_id>` (returns HTML form fragment for AJAX)
- Endpoint: `POST /admin/sales-dashboard/order-note` (creates note via AJAX, returns JSON)

### 3.2 Lot Tracking

**Required Changes:**
1. **Filter to Current Year Only:**
   - Calculate current year bounds: `current_year-01-01` to `next_year-01-01`
   - Apply filter in `compute_sales_dashboard()` lot_tracking aggregation
   - Timezone-safe: Use UTC dates, ensure consistent year boundaries

2. **Apply Lot Log Corrections:**
   - Load Lot Log CSV: `app/eqms/data/LotLog.csv` or `SHIPSTATION_LOTLOG_PATH` env var
   - Map lot numbers: Use `load_lot_log()` to get `lot_corrections` dict
   - Before aggregating: Apply correction: `correct_lot = lot_corrections.get(normalize_lot(raw_lot), normalize_lot(raw_lot))`
   - Only show corrected lot numbers in table

3. **Filter Out SKU Names:**
   - Validate lot format: Must match `^SLQ-\d{5}$` pattern
   - If lot doesn't match pattern → Skip (don't show in table)
   - If lot maps to SKU in Lot Log → Skip (it's a SKU, not a lot)

4. **Add "Active Inventory" Column:**
   - Load Lot Log: Get "Total Units in Lot" for each lot
   - Calculate: `Active Inventory = Total Units in Lot (from Lot Log) - Total Units Distributed (from distribution_log_entries)`
   - Display in right-most column
   - Show negative values if distributed > produced (data inconsistency, flag with warning icon)

**Data Model Implications:**
- Lot Log CSV columns: `Lot`, `SKU`, `Correct Lot Name`, `Manufacturing Date`, `Expiration Date`, `Total Units in Lot`
- Join key: `distribution_log_entries.lot_number` (normalized) → `LotLog.Lot` (normalized) OR `LotLog."Correct Lot Name"` (normalized)
- Matching rule: Normalize both sides (uppercase, remove spaces), then match

**UI Requirements:**
- Table columns: Lot, Units Distributed, First Date, Last Date, Active Inventory
- Active Inventory cell: Show number, if negative show warning icon (⚠️)
- Empty state: "No lot data for current year"

### 3.3 Distribution Log

**Required Changes:**
1. **Add "Details" Button:**
   - Add column header: "Details"
   - Each row has button: `<button class="button button--secondary" data-entry-id="{{ e.id }}">Details</button>`
   - Click → Modal opens (or expandable panel)

2. **In-Page Detail Modal/Panel:**
   - Modal content (lazy-loaded via AJAX):
     - **Order Context:**
       - Sales Order # (if linked)
       - Order Date
       - Ship Date
       - Customer (linked)
     - **Distribution Details:**
       - SKU(s) with quantities
       - Lot Number(s)
       - Source (ShipStation/Manual/CSV)
     - **Customer Stats (for this customer):**
       - First order date
       - Most recent order date
       - Total orders (lifetime)
       - Total units (lifetime)
       - Top SKUs (last 5)
       - Recent lots (last 5)
     - **Quick Actions:**
       - [View Customer Profile]
       - [Add Note to Customer]
       - [View All Distributions for This Customer]

3. **Modal Implementation:**
   - Use HTML `<dialog>` element or lightweight modal library
   - Lazy-load: Fetch data via `GET /admin/distribution-log/entry-details/<entry_id>` (JSON)
   - Close button: X in top-right
   - Backdrop click: Closes modal

**Backend Requirements:**
- Endpoint: `GET /admin/distribution-log/entry-details/<entry_id>` (JSON)
- Returns: `{entry: {...}, order: {...}, customer_stats: {...}}`

### 3.4 Customers (List Page)

**Required Changes:**
1. **Sort by Most Recent Order:**
   - Default sort: `ORDER BY MAX(distribution_log_entries.ship_date) DESC NULLS LAST, customers.facility_name ASC`
   - Customers with no orders appear last (sorted alphabetically)

2. **Remove "Find Duplicates" Button:**
   - Delete button from template
   - No replacement needed

3. **Display Order Count:**
   - Show total orders per customer in table
   - Show last order date in table

**Backend Requirements:**
- Update `customers_list()` query to join with `distribution_log_entries` for sorting
- Use `func.max(DistributionLogEntry.ship_date)` for most recent order date

### 3.5 Customer Profiles (Detail Page)

**Required Changes:**
1. **Rep Assignment Field:**
   - Add "Primary Rep" dropdown in Overview tab
   - Options: All active users (filter: `users.is_active = True`)
   - Save updates `customers.primary_rep_id`
   - Display: Rep email or name if available

2. **Notes Display:**
   - Show all notes (chronological, newest first)
   - Notes created from Sales Dashboard appear here
   - Notes are editable inline

**Backend Requirements:**
- Update `customer_update_post()` to handle `primary_rep_id`
- Validate: Rep must exist and be active

### 3.6 Sales Orders Import (PDF)

**Required Changes:**
1. **Fix Permission Check:**
   - Ensure `sales_orders.import` permission exists
   - Ensure admin role has this permission
   - Ensure ethanr@silq.tech has admin role
   - Add diagnostic endpoint to check permissions

**Backend Requirements:**
- Verify `scripts/init_db.py` assigns `sales_orders.import` to admin role
- Add migration/script to backfill permission if missing
- Add diagnostic route: `GET /admin/debug/permissions` (shows current user's permissions)

---

## 4) Data Model & Data Integrity Rules

### 4.1 Lot Log Integration

**Source of Truth:** `/mnt/data/LotLog.csv` (or `SHIPSTATION_LOTLOG_PATH` env var)

**CSV Structure:**
```csv
Lot,SKU,Correct Lot Name,Manufacturing Date,Expiration Date,Total Units in Lot
SLQ-05012025,211810SPT,SLQ-05012025,2025-01-05,2027-01-05,1000
211810SPT,211810SPT,SLQ-05012025,,,0
```

**Matching Rules:**
1. **Normalize lot names:** Uppercase, remove spaces, ensure `SLQ-` prefix
2. **Primary match:** `distribution_log_entries.lot_number` (normalized) → `LotLog.Lot` (normalized)
3. **Correction match:** If primary match fails, try `LotLog."Correct Lot Name"` (normalized)
4. **SKU filtering:** If lot maps to SKU (e.g., "211810SPT" in Lot column), skip (it's not a lot)

**Active Inventory Calculation:**
```python
def calculate_active_inventory(lot_number: str, lot_log: dict, distributions: list) -> int:
    """Calculate remaining inventory for a lot."""
    # Get total units produced from Lot Log
    lot_row = lot_log.get(lot_number)
    if not lot_row:
        return None  # Lot not in Lot Log
    
    total_produced = int(lot_row.get("Total Units in Lot", 0))
    
    # Sum distributed units from distribution_log_entries
    total_distributed = sum(
        d.quantity for d in distributions 
        if normalize_lot(d.lot_number) == normalize_lot(lot_number)
    )
    
    return total_produced - total_distributed
```

**Data Integrity:**
- Lot Log is read-only (no writes from application)
- If lot not in Lot Log → Show in table but Active Inventory = "N/A"
- If distributed > produced → Show negative with warning

### 4.2 Customer Cleanup Rules

**Delete Criteria:**
- Customer has 0 orders: `COUNT(DISTINCT distribution_log_entries.id WHERE customer_id = customers.id) = 0`
- Customer has 0 sales orders: `COUNT(DISTINCT sales_orders.id WHERE customer_id = customers.id) = 0`
- Customer has 0 notes (optional, can keep customers with notes even if no orders)

**Safe Deletion Process:**
1. Check for dependencies:
   - `distribution_log_entries.customer_id` → Set to NULL (if FK allows) OR skip deletion
   - `sales_orders.customer_id` → RESTRICT (prevent deletion if orders exist)
   - `customer_notes.customer_id` → CASCADE (delete notes with customer)
2. Audit log: Record deletion with reason
3. Soft delete option: Add `is_deleted` flag (P1, not P0)

**Migration Script:**
```python
# scripts/cleanup_zero_order_customers.py
def cleanup_zero_order_customers(s, *, dry_run: bool = True):
    """Delete customers with 0 orders."""
    zero_order_customers = (
        s.query(Customer)
        .outerjoin(DistributionLogEntry, Customer.id == DistributionLogEntry.customer_id)
        .outerjoin(SalesOrder, Customer.id == SalesOrder.customer_id)
        .group_by(Customer.id)
        .having(
            func.count(DistributionLogEntry.id) == 0,
            func.count(SalesOrder.id) == 0
        )
        .all()
    )
    
    for customer in zero_order_customers:
        if dry_run:
            print(f"Would delete: {customer.facility_name} (ID: {customer.id})")
        else:
            # Delete customer (CASCADE deletes notes)
            s.delete(customer)
            record_event(s, ...)
```

### 4.3 Sales Orders as Source of Truth

**Customer Identity:**
- `sales_orders.customer_id` is the authoritative customer reference
- `distribution_log_entries.customer_id` should match `sales_orders.customer_id` (enforced via FK)
- ShipStation customer info is only used for matching/linking, not as source of truth

**Linking Algorithm:**
1. **ShipStation Sync:**
   - Extract customer name from `shipTo.company` or `shipTo.name`
   - Normalize: `canonical_customer_key(facility_name)`
   - Find existing customer: `SELECT * FROM customers WHERE company_key = ?`
   - If not found: Create new customer via `find_or_create_customer()`
   - Create sales order with `customer_id`
   - Create distribution entries with `customer_id` and `sales_order_id`

2. **Manual Entry:**
   - Admin selects customer from dropdown (required)
   - If customer doesn't exist: Create via inline form
   - Create sales order (or select existing) with `customer_id`
   - Create distribution entry with `customer_id` and `sales_order_id`

3. **CSV Import:**
   - Parse facility name from CSV
   - Match to existing customer via `canonical_customer_key()`
   - If not found: Create new customer
   - Create sales order and distribution entries

**Prevent Accidental Merges:**
- Always use `canonical_customer_key()` for matching (not free-text comparison)
- Require explicit admin action to merge customers (no auto-merge)
- Show merge candidates in admin UI (P1, not P0)

### 4.4 Rep Assignment Data Model

**New Fields (if not exists):**
- `users.address1` (TEXT, nullable)
- `users.address2` (TEXT, nullable)
- `users.city` (TEXT, nullable)
- `users.state` (TEXT, nullable)
- `users.zip` (TEXT, nullable) - US ZIP code format validation

**ZIP Validation:**
- Format: `^\d{5}(-\d{4})?$` (5 digits, optional +4)
- Examples: `12345`, `12345-6789`
- Validation: Client-side (HTML5 pattern) + server-side (Python regex)

**Rep Assignment:**
- `customers.primary_rep_id` (FK to `users.id`) - already exists
- `distribution_log_entries.rep_id` (FK to `users.id`) - already exists
- `sales_orders.rep_id` (FK to `users.id`) - already exists

**Filtering:**
- Distribution Log: Filter by `rep_id` (add to filter form)
- Tracing Reports: Filter by `rep_id` (add to generate form)
- Customer Database: Filter by `primary_rep_id` (add to filter form)

---

## 5) Backend/API Changes

### 5.1 New Routes

**Sales Dashboard:**
- `GET /admin/sales-dashboard/order-note-form/<customer_id>` - Returns HTML form fragment for inline note editor
- `POST /admin/sales-dashboard/order-note` - Creates note via AJAX (JSON request/response)

**Distribution Log:**
- `GET /admin/distribution-log/entry-details/<entry_id>` - Returns JSON with entry details, order context, customer stats

**Lot Tracking:**
- `GET /admin/lot-tracking` (optional, if separate page needed) - Shows lot tracking with Active Inventory

**Permissions Debug:**
- `GET /admin/debug/permissions` - Shows current user's roles and permissions (admin only)

**ShipStation Sync:**
- `POST /admin/shipstation/run-month` - Sync specific month (new route, or modify existing route to accept `month` parameter)

**Customer Cleanup:**
- `POST /admin/customers/cleanup-zero-orders` - Deletes customers with 0 orders (admin only, requires confirmation)

### 5.2 Modified Routes

**Sales Dashboard:**
- `GET /admin/sales-dashboard` - Update `compute_sales_dashboard()` to:
  - Remove `by_month` aggregation
  - Remove `top_customers` aggregation
  - Add `recent_orders_new` and `recent_orders_repeat` aggregations
  - Filter lot tracking to current year
  - Apply lot corrections from Lot Log
  - Calculate active inventory

**Distribution Log:**
- `GET /admin/distribution-log` - Add rep filter to filter form
- `GET /admin/distribution-log/entry-details/<entry_id>` - New endpoint for modal data

**Customers:**
- `GET /admin/customers` - Update sort to most recent order first
- `GET /admin/customers/<id>` - Ensure rep assignment field is editable
- `POST /admin/customers/<id>` - Handle `primary_rep_id` update

**Tracing Reports:**
- `GET /admin/tracing/generate` - Add rep filter to form
- `POST /admin/tracing/generate` - Include `rep_id` in filters

**Sales Orders Import:**
- `GET /admin/sales-orders/import-pdf` - Ensure permission check passes for admin
- `POST /admin/sales-orders/import-pdf` - No changes needed

**ShipStation Sync:**
- `POST /admin/shipstation/run` - Add optional `month` parameter (YYYY-MM format)
- If `month` provided: Sync only that month (start_date = month-01, end_date = next_month-01)
- If not provided: Use existing logic (default to 2025-01-01)

### 5.3 New Service Functions

**Sales Dashboard:**
```python
# app/eqms/modules/rep_traceability/service.py

def get_recent_orders_by_customer_type(
    s,
    *,
    customer_type: str,  # 'new' or 'repeat'
    limit: int = 20,
    start_date: date | None = None,
) -> list[dict[str, Any]]:
    """Get recent orders from NEW or REPEAT customers."""
    # Query sales_orders joined with customers
    # Filter by customer_type (lifetime order count)
    # Sort by ship_date DESC
    # Limit to N most recent
    pass

def compute_lot_tracking_with_inventory(
    s,
    *,
    year: int | None = None,  # Current year if None
    lot_log_path: str,
) -> list[dict[str, Any]]:
    """Compute lot tracking with Active Inventory from Lot Log."""
    # Load Lot Log CSV
    # Filter distributions to year
    # Apply lot corrections
    # Calculate active inventory per lot
    pass
```

**Distribution Log:**
```python
def get_distribution_entry_details(
    s,
    *,
    entry_id: int,
) -> dict[str, Any]:
    """Get distribution entry details for modal."""
    # Get entry
    # Get linked sales order (if exists)
    # Get customer stats (first order, last order, total orders, total units, top SKUs, recent lots)
    # Return JSON-serializable dict
    pass
```

**Lot Log:**
```python
# app/eqms/modules/shipstation_sync/parsers.py (enhance existing)

def load_lot_log_with_inventory(path_str: str) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    """Load Lot Log with inventory data.
    
    Returns:
        - lot_to_sku: {lot -> sku}
        - lot_corrections: {raw_lot -> correct_lot}
        - lot_inventory: {lot -> total_units_produced}
    """
    # Load CSV
    # Extract "Total Units in Lot" column
    # Return inventory dict
    pass
```

**Customer Cleanup:**
```python
# scripts/cleanup_zero_order_customers.py

def find_zero_order_customers(s) -> list[Customer]:
    """Find customers with 0 orders."""
    pass

def delete_zero_order_customers(s, *, customer_ids: list[int], user: User) -> int:
    """Delete customers with 0 orders (safe deletion)."""
    # Check dependencies
    # Delete customers
    # Record audit events
    # Return count deleted
    pass
```

### 5.4 Modified Service Functions

**Sales Dashboard:**
- `compute_sales_dashboard()` - Remove month aggregation, remove top customers, add recent orders lists, filter lot tracking to current year, apply lot corrections, calculate active inventory

**Distribution Log:**
- `query_distribution_entries()` - Add `rep_id` filter support

**Tracing Reports:**
- `generate_tracing_report_csv()` - Add `rep_id` filter support

**ShipStation Sync:**
- `run_sync()` - Add `month` parameter support (YYYY-MM format), if provided sync only that month

---

## 6) Frontend Changes

### 6.1 Sales Dashboard Template

**File:** `app/eqms/templates/admin/sales_dashboard/index.html`

**Changes:**
1. **Remove sections:**
   - Delete "Sales by Month" card (lines 56-83)
   - Delete "Top Customers" card (lines 148-218)

2. **Add Recent Orders Lists:**
   ```html
   <!-- Left Column: Recent Orders -->
   <div class="grid" style="grid-template-columns: 1fr 1fr; gap: 14px;">
     <!-- Recent Orders from NEW Customers -->
     <div class="card">
       <h2 style="margin-top:0; font-size:16px;">Recent Orders from NEW Customers</h2>
       {% if recent_orders_new %}
         <div style="max-height: 400px; overflow-y: auto;">
           {% for order in recent_orders_new %}
             <div class="order-row" style="padding:10px 12px; border-bottom:1px solid rgba(255,255,255,0.05);">
               <div style="display:flex; justify-content:space-between; align-items:start;">
                 <div>
                   <a href="{{ url_for('customer_profiles.customer_detail', customer_id=order.customer_id) }}" style="font-weight:500;">{{ order.customer_name|e }}</a>
                   <div class="muted" style="font-size:12px; margin-top:4px;">{{ order.order_date }} · {{ order.order_number|e }}</div>
                   <div style="font-size:13px; margin-top:4px;">{{ order.total_units }} units</div>
                 </div>
                 <div style="display:flex; gap:6px;">
                   <button class="button button--secondary" style="font-size:11px; padding:4px 8px;" onclick="showNoteForm({{ order.customer_id }}, '{{ order.order_number|e }}')">+ Note</button>
                   <a href="{{ url_for('customer_profiles.customer_detail', customer_id=order.customer_id) }}" style="font-size:11px; padding:4px 8px;">Profile</a>
                 </div>
               </div>
               <!-- Inline note form (hidden by default) -->
               <div id="note-form-{{ order.customer_id }}" style="display:none; margin-top:12px; padding:12px; background:rgba(255,255,255,0.05); border-radius:6px;">
                 <form onsubmit="saveNote(event, {{ order.customer_id }}, '{{ order.order_number|e }}')">
                   <input type="text" name="note_text" placeholder="Enter note..." required style="width:100%; margin-bottom:8px;" />
                   <input type="date" name="note_date" value="{{ today }}" style="width:auto; margin-bottom:8px;" />
                   <div style="display:flex; gap:6px;">
                     <button class="button" type="submit" style="font-size:11px; padding:4px 8px;">Save</button>
                     <button class="button button--secondary" type="button" onclick="hideNoteForm({{ order.customer_id }})" style="font-size:11px; padding:4px 8px;">Cancel</button>
                   </div>
                 </form>
               </div>
             </div>
           {% endfor %}
         </div>
       {% else %}
         <p class="muted">No recent orders from new customers.</p>
       {% endif %}
     </div>
     
     <!-- Recent Orders from REPEAT Customers -->
     <div class="card">
       <h2 style="margin-top:0; font-size:16px;">Recent Orders from REPEAT Customers</h2>
       <!-- Same structure as NEW customers -->
     </div>
   </div>
   ```

3. **Move SKU & Lot to Right Column:**
   ```html
   <!-- Right Column: SKU & Lot Tracking -->
   <div style="display:grid; grid-template-columns: 1fr; gap: 14px;">
     <!-- Sales by SKU (existing, keep structure) -->
     <div class="card">
       <h2 style="margin-top:0; font-size:16px;">Sales by SKU</h2>
       <!-- Existing SKU table -->
     </div>
     
     <!-- Lot Tracking (enhanced) -->
     <div class="card">
       <h2 style="margin-top:0; font-size:16px;">Lot Tracking ({{ current_year }})</h2>
       <table>
         <thead>
           <tr>
             <th>Lot</th>
             <th style="text-align:right;">Units Distributed</th>
             <th style="text-align:right;">First</th>
             <th style="text-align:right;">Last</th>
             <th style="text-align:right;">Active Inventory</th>
           </tr>
         </thead>
         <tbody>
           {% for row in lot_tracking %}
             <tr>
               <td><code>{{ row.lot|e }}</code></td>
               <td style="text-align:right;">{{ row.units }}</td>
               <td style="text-align:right;">{{ row.first_date }}</td>
               <td style="text-align:right;">{{ row.last_date }}</td>
               <td style="text-align:right;">
                 {% if row.active_inventory is not none %}
                   {% if row.active_inventory < 0 %}
                     <span style="color:var(--danger);">⚠️ {{ row.active_inventory }}</span>
                   {% else %}
                     {{ row.active_inventory }}
                   {% endif %}
                 {% else %}
                   <span class="muted">N/A</span>
                 {% endif %}
               </td>
             </tr>
           {% endfor %}
         </tbody>
       </table>
     </div>
   </div>
   ```

4. **JavaScript for Inline Notes:**
   ```javascript
   <script>
   function showNoteForm(customerId, orderNumber) {
     document.getElementById(`note-form-${customerId}`).style.display = 'block';
   }
   
   function hideNoteForm(customerId) {
     document.getElementById(`note-form-${customerId}`).style.display = 'none';
   }
   
   async function saveNote(event, customerId, orderNumber) {
     event.preventDefault();
     const formData = new FormData(event.target);
     const response = await fetch(`/admin/customers/${customerId}/notes`, {
       method: 'POST',
       body: formData,
     });
     if (response.ok) {
       // Reload page or update UI
       location.reload();
     } else {
       alert('Failed to save note');
     }
   }
   </script>
   ```

### 6.2 Distribution Log Template

**File:** `app/eqms/templates/admin/distribution_log/list.html`

**Changes:**
1. **Add Details Column:**
   ```html
   <th style="text-align:center; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Details</th>
   ```

2. **Add Details Button:**
   ```html
   <td style="padding:10px 12px; text-align:center;">
     <button class="button button--secondary" style="font-size:11px; padding:4px 8px;" onclick="showEntryDetails({{ e.id }})">Details</button>
   </td>
   ```

3. **Add Modal:**
   ```html
   <dialog id="entry-details-modal" style="max-width:600px; padding:24px; border-radius:12px; border:1px solid var(--border);">
     <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
       <h2 style="margin:0; font-size:18px;">Distribution Details</h2>
       <button onclick="document.getElementById('entry-details-modal').close()" style="background:none; border:none; font-size:24px; cursor:pointer;">×</button>
     </div>
     <div id="entry-details-content">
       <div class="muted">Loading...</div>
     </div>
   </dialog>
   
   <script>
   async function showEntryDetails(entryId) {
     const modal = document.getElementById('entry-details-modal');
     const content = document.getElementById('entry-details-content');
     content.innerHTML = '<div class="muted">Loading...</div>';
     modal.showModal();
     
     const response = await fetch(`/admin/distribution-log/entry-details/${entryId}`);
     const data = await response.json();
     
     // Render details
     content.innerHTML = `
       <div class="card" style="margin-bottom:12px;">
         <h3 style="margin-top:0; font-size:14px;">Order Context</h3>
         <div class="dl">
           <dt>Sales Order</dt><dd>${data.order?.order_number || 'N/A'}</dd>
           <dt>Order Date</dt><dd>${data.order?.order_date || 'N/A'}</dd>
           <dt>Ship Date</dt><dd>${data.entry.ship_date}</dd>
           <dt>Customer</dt><dd><a href="/admin/customers/${data.entry.customer_id}">${data.customer?.facility_name || 'N/A'}</a></dd>
         </div>
       </div>
       <div class="card" style="margin-bottom:12px;">
         <h3 style="margin-top:0; font-size:14px;">Distribution Details</h3>
         <div class="dl">
           <dt>SKU</dt><dd><code>${data.entry.sku}</code></dd>
           <dt>Lot</dt><dd><code>${data.entry.lot_number}</code></dd>
           <dt>Quantity</dt><dd>${data.entry.quantity}</dd>
           <dt>Source</dt><dd>${data.entry.source}</dd>
         </div>
       </div>
       <div class="card">
         <h3 style="margin-top:0; font-size:14px;">Customer Stats</h3>
         <div class="dl">
           <dt>First Order</dt><dd>${data.customer_stats.first_order || 'N/A'}</dd>
           <dt>Last Order</dt><dd>${data.customer_stats.last_order || 'N/A'}</dd>
           <dt>Total Orders</dt><dd>${data.customer_stats.total_orders}</dd>
           <dt>Total Units</dt><dd>${data.customer_stats.total_units}</dd>
         </div>
       </div>
       <div style="margin-top:16px; display:flex; gap:8px;">
         <a href="/admin/customers/${data.entry.customer_id}" class="button">View Customer Profile</a>
         <a href="/admin/customers/${data.entry.customer_id}#notes" class="button button--secondary">Add Note</a>
       </div>
     `;
   }
   </script>
   ```

### 6.3 Customers List Template

**File:** `app/eqms/templates/admin/customers/list.html`

**Changes:**
1. **Remove "Find Duplicates" Button:**
   - Delete button from template (search for "Find Duplicates" or "duplicates")

2. **Update Sort Display:**
   - Add indicator: "Sorted by: Most Recent Order" (small text below header)

### 6.4 Customer Profile Template

**File:** `app/eqms/templates/admin/customers/detail.html`

**Changes:**
1. **Add Rep Assignment Field:**
   ```html
   <div>
     <div class="label">Primary Rep</div>
     <select name="primary_rep_id" style="width:100%;">
       <option value="">(None)</option>
       {% for rep in reps %}
         <option value="{{ rep.id }}" {% if customer.primary_rep_id == rep.id %}selected{% endif %}>{{ rep.email }}</option>
       {% endfor %}
     </select>
   </div>
   ```

### 6.5 Distribution Log Filter Form

**File:** `app/eqms/templates/admin/distribution_log/list.html`

**Changes:**
1. **Add Rep Filter:**
   ```html
   <div>
     <div class="label">Rep</div>
     <select name="rep_id" style="width:100%;">
       <option value="">All Reps</option>
       {% for rep in reps %}
         <option value="{{ rep.id }}" {% if filters.rep_id == rep.id|string %}selected{% endif %}>{{ rep.email }}</option>
       {% endfor %}
     </select>
   </div>
   ```

### 6.6 Tracing Report Generate Form

**File:** `app/eqms/templates/admin/tracing/generate.html`

**Changes:**
1. **Add Rep Filter:**
   ```html
   <div>
     <div class="label">Rep (Optional)</div>
     <select name="rep_id" style="width:100%;">
       <option value="">All Reps</option>
       {% for rep in reps %}
         <option value="{{ rep.id }}">{{ rep.email }}</option>
       {% endfor %}
     </select>
   </div>
   ```

### 6.7 ShipStation Sync Template

**File:** `app/eqms/templates/admin/shipstation/index.html`

**Changes:**
1. **Add Month Picker:**
   ```html
   <form method="post" action="{{ url_for('shipstation_sync.shipstation_run') }}" style="max-width:400px;">
     <div>
       <div class="label">Sync Month (Optional)</div>
       <input type="month" name="month" placeholder="YYYY-MM" style="width:100%;" />
       <p class="muted" style="font-size:11px; margin-top:4px;">Leave empty to sync from 2025-01-01 to now</p>
     </div>
     <button class="button" type="submit">Run Sync</button>
   </form>
   ```

---

## 7) Permission/RBAC Fix Plan

### 7.1 Root Cause Analysis

**Problem:** `/admin/sales-orders/import-pdf` returns 403 with "Missing permission sales_orders.import"

**Possible Causes:**
1. Permission `sales_orders.import` not created in database
2. Permission exists but not assigned to `admin` role
3. User `ethanr@silq.tech` doesn't have `admin` role
4. Permission key mismatch (typo in route vs seed script)

**Investigation Steps:**
1. Check `scripts/init_db.py` line 93: `p_sales_orders_import = ensure_perm("sales_orders.import", ...)`
2. Check line 153: `p_sales_orders_import` in admin role permissions list
3. Check route: `app/eqms/modules/rep_traceability/admin.py` line 861: `@require_permission("sales_orders.import")`
4. Query database: `SELECT * FROM permissions WHERE key = 'sales_orders.import';`
5. Query database: `SELECT r.key, p.key FROM roles r JOIN role_permissions rp ON r.id = rp.role_id JOIN permissions p ON rp.permission_id = p.id WHERE r.key = 'admin' AND p.key = 'sales_orders.import';`
6. Query database: `SELECT u.email, r.key FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE u.email = 'ethanr@silq.tech';`

### 7.2 Fix Strategy

**Step 1: Verify Permission Exists**
- Run: `python scripts/init_db.py` (idempotent, creates permission if missing)
- Verify: `SELECT * FROM permissions WHERE key = 'sales_orders.import';` returns 1 row

**Step 2: Verify Admin Role Has Permission**
- Run: `python scripts/init_db.py` (idempotent, assigns permission to admin role if missing)
- Verify: `SELECT COUNT(*) FROM role_permissions rp JOIN roles r ON rp.role_id = r.id JOIN permissions p ON rp.permission_id = p.id WHERE r.key = 'admin' AND p.key = 'sales_orders.import';` returns 1

**Step 3: Verify User Has Admin Role**
- Query: `SELECT u.email, r.key FROM users u JOIN user_roles ur ON u.id = ur.user_id JOIN roles r ON ur.role_id = r.id WHERE u.email = 'ethanr@silq.tech';`
- If no admin role: Run migration script to assign admin role

**Step 4: Create Diagnostic Endpoint**
- Route: `GET /admin/debug/permissions`
- Shows: Current user's email, roles, permissions list
- Helps diagnose permission issues in production

**Step 5: Add Migration Script (If Needed)**
- Create: `migrations/versions/XXXXX_fix_sales_orders_import_permission.py`
- Ensures permission exists and is assigned to admin role
- Idempotent (can run multiple times safely)

### 7.3 Diagnostic Endpoint

**Route:** `GET /admin/debug/permissions`

**Implementation:**
```python
# app/eqms/admin.py

@bp.get("/debug/permissions")
@require_permission("admin.view")  # Only admins can access
def debug_permissions():
    """Show current user's permissions for debugging."""
    s = db_session()
    u = _current_user()
    
    roles = u.roles
    permissions = []
    for role in roles:
        for perm in role.permissions:
            permissions.append({
                "role": role.key,
                "permission": perm.key,
                "name": perm.name,
            })
    
    return render_template("admin/debug_permissions.html", 
        user=u, 
        roles=roles, 
        permissions=permissions
    )
```

**Template:** `app/eqms/templates/admin/debug_permissions.html`
```html
{% extends "_layout.html" %}
{% block title %}Permission Debug{% endblock %}
{% block content %}
  <div class="card">
    <h1>Permission Debug</h1>
    <div class="dl">
      <dt>User Email</dt><dd>{{ user.email }}</dd>
      <dt>Roles</dt><dd>{{ roles|map(attribute='key')|join(', ') }}</dd>
    </div>
  </div>
  
  <div class="card">
    <h2>Permissions</h2>
    <table>
      <thead>
        <tr>
          <th>Role</th>
          <th>Permission Key</th>
          <th>Permission Name</th>
        </tr>
      </thead>
      <tbody>
        {% for p in permissions %}
          <tr>
            <td>{{ p.role }}</td>
            <td><code>{{ p.permission }}</code></td>
            <td>{{ p.name }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
{% endblock %}
```

### 7.4 Acceptance Criteria

- [ ] **AC1:** Permission `sales_orders.import` exists in database
- [ ] **AC2:** Admin role has `sales_orders.import` permission
- [ ] **AC3:** User `ethanr@silq.tech` has admin role
- [ ] **AC4:** Route `/admin/sales-orders/import-pdf` returns 200 (not 403) for ethanr@silq.tech
- [ ] **AC5:** Diagnostic endpoint `/admin/debug/permissions` shows `sales_orders.import` in permissions list

---

## 8) Migration / Cleanup Plan

### 8.1 Delete Zero-Order Customers

**Script:** `scripts/cleanup_zero_order_customers.py`

**Implementation:**
```python
#!/usr/bin/env python3
"""Delete customers with 0 orders (safe deletion)."""

import sys
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager

from app.eqms.models import User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
from app.eqms.audit import record_event

@contextmanager
def _session_scope(database_url: str):
    engine = create_engine(database_url, future=True)
    sm = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    s: Session = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()

def find_zero_order_customers(s) -> list[Customer]:
    """Find customers with 0 orders and 0 distributions."""
    return (
        s.query(Customer)
        .outerjoin(DistributionLogEntry, Customer.id == DistributionLogEntry.customer_id)
        .outerjoin(SalesOrder, Customer.id == SalesOrder.customer_id)
        .group_by(Customer.id)
        .having(
            func.count(DistributionLogEntry.id) == 0,
            func.count(SalesOrder.id) == 0
        )
        .all()
    )

def main():
    db_url = (os.environ.get("DATABASE_URL") or "sqlite:///eqms.db").strip()
    admin_email = (os.environ.get("ADMIN_EMAIL") or "admin@silqeqms.com").strip().lower()
    
    with _session_scope(db_url) as s:
        # Find admin user
        admin_user = s.query(User).filter(User.email == admin_email).one_or_none()
        if not admin_user:
            print(f"ERROR: Admin user {admin_email} not found")
            sys.exit(1)
        
        # Find zero-order customers
        zero_order_customers = find_zero_order_customers(s)
        
        if not zero_order_customers:
            print("No zero-order customers found.")
            return
        
        print(f"Found {len(zero_order_customers)} zero-order customers:")
        for c in zero_order_customers:
            print(f"  - {c.facility_name} (ID: {c.id})")
        
        # Confirm deletion
        response = input("\nDelete these customers? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            return
        
        # Delete customers
        deleted_count = 0
        for c in zero_order_customers:
            # Record audit event
            record_event(
                s,
                actor=admin_user,
                action="customer.delete_zero_orders",
                entity_type="Customer",
                entity_id=str(c.id),
                metadata={"facility_name": c.facility_name, "reason": "Zero orders cleanup"},
            )
            s.delete(c)
            deleted_count += 1
        
        print(f"\nDeleted {deleted_count} customers.")

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
python scripts/cleanup_zero_order_customers.py
```

**Safety Checks:**
- Only deletes customers with 0 orders AND 0 distributions
- Requires explicit confirmation
- Records audit events
- Can be run multiple times (idempotent)

### 8.2 Customer Deduplication Rules

**Current Strategy:**
- Use `canonical_customer_key()` for matching (normalized facility name)
- `customers.company_key` is unique (prevents exact duplicates)
- ShipStation sync uses `find_or_create_customer()` (prevents new duplicates)

**Prevention Rules:**
1. **Always use `find_or_create_customer()`** - Never create `Customer()` directly
2. **Normalize before matching** - Use `canonical_customer_key()` for all lookups
3. **Sales Orders as source of truth** - Customer identity comes from `sales_orders.customer_id`, not free-text
4. **No auto-merge** - Require explicit admin action to merge customers

**Linking Algorithm (ShipStation):**
```python
# In shipstation_sync/service.py

def _get_customer_from_ship_to(s, ship_to: dict) -> Customer | None:
    facility = _safe_text(ship_to.get("company")) or _safe_text(ship_to.get("name"))
    if not facility:
        return None
    
    # Use find_or_create_customer (prevents duplicates)
    customer = find_or_create_customer(
        s,
        facility_name=facility,
        address1=_safe_text(ship_to.get("street1")),
        city=_safe_text(ship_to.get("city")),
        state=_safe_text(ship_to.get("state")),
        zip=_safe_text(ship_to.get("postalCode")),
    )
    return customer
```

**Avoid Accidental Merges:**
- Never merge customers automatically
- Show merge candidates in admin UI (P1, not P0)
- Require explicit confirmation for merges

---

## 9) Acceptance Criteria

### 9.1 Sales Dashboard Redesign

- [ ] **AC1:** "Sales by Month" table is removed from dashboard
- [ ] **AC2:** "Top Customers" table is removed from dashboard
- [ ] **AC3:** "Recent Orders from NEW Customers" list appears (shows orders from customers with 1 lifetime order)
- [ ] **AC4:** "Recent Orders from REPEAT Customers" list appears (shows orders from customers with 2+ lifetime orders)
- [ ] **AC5:** Each order row shows: customer name (linked), order date, order number, total units, quick actions
- [ ] **AC6:** "Add Note" button works: Click → Inline form appears → Save → Note created and appears in customer profile
- [ ] **AC7:** "Sales by SKU" table is in right column
- [ ] **AC8:** "Lot Tracking" table is in right column
- [ ] **AC9:** Dashboard matches legacy template styling (Bootstrap cards, consistent spacing, clean typography)

### 9.2 Lot Tracking Accuracy

- [ ] **AC10:** Lot Tracking shows only lots from current year (ship_date >= current_year-01-01 AND ship_date < next_year-01-01)
- [ ] **AC11:** Lot Tracking applies Lot Log corrections (incorrect lot names mapped to correct names)
- [ ] **AC12:** Lot Tracking filters out SKU names (only shows lots matching `^SLQ-\d{5}$` pattern)
- [ ] **AC13:** "Active Inventory" column appears in Lot Tracking table
- [ ] **AC14:** Active Inventory = Total Units Produced (Lot Log) - Total Units Distributed (distribution_log_entries)
- [ ] **AC15:** Negative Active Inventory shows warning icon (⚠️)

### 9.3 Distribution Log Improvements

- [ ] **AC16:** "Details" button appears in each distribution row
- [ ] **AC17:** Click "Details" → Modal opens with entry details, order context, customer stats
- [ ] **AC18:** Modal shows: Sales Order #, Order Date, Ship Date, Customer, SKU, Lot, Quantity, Source
- [ ] **AC19:** Modal shows customer stats: First order date, Last order date, Total orders, Total units, Top SKUs, Recent lots
- [ ] **AC20:** Modal has quick actions: View Customer Profile, Add Note, View All Distributions

### 9.4 Permission Fix

- [ ] **AC21:** Permission `sales_orders.import` exists in database
- [ ] **AC22:** Admin role has `sales_orders.import` permission
- [ ] **AC23:** User `ethanr@silq.tech` has admin role
- [ ] **AC24:** Route `/admin/sales-orders/import-pdf` returns 200 (not 403) for ethanr@silq.tech
- [ ] **AC25:** Diagnostic endpoint `/admin/debug/permissions` works and shows permissions

### 9.5 Customer Cleanup

- [ ] **AC26:** Customers with 0 orders are deleted (via cleanup script)
- [ ] **AC27:** Customer database is sorted by most recent order (customers with orders first, then alphabetically)
- [ ] **AC28:** "Find Duplicates" button is removed from customer database page
- [ ] **AC29:** Sales Orders are used as source of truth for customer identity (not free-text facility_name)

### 9.6 Rep Assignment

- [ ] **AC30:** Customer Profile has "Primary Rep" dropdown (shows all active users)
- [ ] **AC31:** Saving customer profile updates `primary_rep_id`
- [ ] **AC32:** Distribution Log filter form includes "Rep" dropdown
- [ ] **AC33:** Filtering by rep shows only distributions for that rep
- [ ] **AC34:** Tracing Report generate form includes "Rep" filter
- [ ] **AC35:** Generating tracing report with rep filter includes only that rep's distributions
- [ ] **AC36:** Rep address fields exist in `users` table (address1, city, state, zip)
- [ ] **AC37:** ZIP code validation works (5 digits, optional +4: `^\d{5}(-\d{4})?$`)

### 9.7 ShipStation Sync Throttling

- [ ] **AC38:** ShipStation sync form has "Month" picker (YYYY-MM format)
- [ ] **AC39:** Selecting a month syncs only that month (start_date = month-01, end_date = next_month-01)
- [ ] **AC40:** Leaving month empty uses default (2025-01-01 to now)
- [ ] **AC41:** Month-scoped sync completes without timeout

---

## 10) Implementation Plan (P0/P1/P2)

### Phase 0: Critical Fixes (P0 - Must Have)

**Task 0.1: Fix Permission 403 Error**
- **Files:** `scripts/init_db.py`, `app/eqms/admin.py`, `migrations/versions/XXXXX_fix_sales_orders_import_permission.py`
- **Steps:**
  1. Verify `sales_orders.import` permission exists in `init_db.py`
  2. Verify admin role has permission assigned
  3. Create migration to backfill permission if missing
  4. Add diagnostic endpoint `/admin/debug/permissions`
  5. Test: Access `/admin/sales-orders/import-pdf` as ethanr@silq.tech → Should return 200
- **Dependencies:** None
- **Acceptance:** AC21-AC25

**Task 0.2: Customer Cleanup Script**
- **Files:** `scripts/cleanup_zero_order_customers.py` (new)
- **Steps:**
  1. Create script to find zero-order customers
  2. Add safety checks (confirm deletion, audit logging)
  3. Test on dev database
  4. Run on production (with confirmation)
- **Dependencies:** None
- **Acceptance:** AC26

**Task 0.3: Customer Database Sort by Most Recent Order**
- **Files:** `app/eqms/modules/customer_profiles/admin.py::customers_list()`
- **Steps:**
  1. Update query to join with `distribution_log_entries`
  2. Sort by `MAX(distribution_log_entries.ship_date) DESC NULLS LAST`
  3. Update template to show sort indicator
- **Dependencies:** None
- **Acceptance:** AC27

**Task 0.4: Remove "Find Duplicates" Button**
- **Files:** `app/eqms/templates/admin/customers/list.html`
- **Steps:**
  1. Search for "Find Duplicates" or "duplicates" button
  2. Delete button element
  3. Test: Button no longer appears
- **Dependencies:** None
- **Acceptance:** AC28

### Phase 1: Core Features (P0/P1)

**Task 1.1: Sales Dashboard Redesign**
- **Files:** `app/eqms/templates/admin/sales_dashboard/index.html`, `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard()`, `app/eqms/modules/rep_traceability/admin.py::sales_dashboard()`
- **Steps:**
  1. Remove "Sales by Month" section from template
  2. Remove "Top Customers" section from template
  3. Add "Recent Orders from NEW Customers" list (left column)
  4. Add "Recent Orders from REPEAT Customers" list (left column)
  5. Move "Sales by SKU" to right column
  6. Move "Lot Tracking" to right column
  7. Update `compute_sales_dashboard()` to generate recent orders lists
  8. Add inline note editor JavaScript
  9. Match legacy template styling
- **Dependencies:** Task 0.1 (permission fix)
- **Acceptance:** AC1-AC9

**Task 1.2: Lot Tracking Accuracy + Active Inventory**
- **Files:** `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard()`, `app/eqms/modules/shipstation_sync/parsers.py::load_lot_log()`
- **Steps:**
  1. Filter lot tracking to current year only
  2. Load Lot Log CSV in `compute_sales_dashboard()`
  3. Apply lot corrections from Lot Log
  4. Filter out SKU names (validate lot format)
  5. Calculate Active Inventory (Lot Log total - distributed total)
  6. Update template to show Active Inventory column
  7. Add warning icon for negative inventory
- **Dependencies:** Task 1.1 (dashboard redesign)
- **Acceptance:** AC10-AC15

**Task 1.3: Distribution Log Details Modal**
- **Files:** `app/eqms/templates/admin/distribution_log/list.html`, `app/eqms/modules/rep_traceability/admin.py`, `app/eqms/modules/rep_traceability/service.py`
- **Steps:**
  1. Add "Details" button column to table
  2. Create modal HTML (dialog element)
  3. Add endpoint `GET /admin/distribution-log/entry-details/<entry_id>` (JSON)
  4. Add JavaScript to fetch and display details
  5. Show order context, distribution details, customer stats
  6. Add quick action links
- **Dependencies:** None
- **Acceptance:** AC16-AC20

**Task 1.4: Rep Assignment + Filtering**
- **Files:** `app/eqms/modules/customer_profiles/admin.py`, `app/eqms/modules/customer_profiles/models.py`, `app/eqms/templates/admin/customers/detail.html`, `app/eqms/templates/admin/distribution_log/list.html`, `app/eqms/templates/admin/tracing/generate.html`, `app/eqms/modules/rep_traceability/admin.py`, `app/eqms/modules/rep_traceability/service.py`
- **Steps:**
  1. Add rep assignment field to customer profile template
  2. Update `customer_update_post()` to handle `primary_rep_id`
  3. Add rep filter to distribution log filter form
  4. Update `query_distribution_entries()` to filter by `rep_id`
  5. Add rep filter to tracing report generate form
  6. Update `generate_tracing_report_csv()` to filter by `rep_id`
  7. Add migration to add rep address fields to `users` table (if not exists)
  8. Add ZIP validation (client-side + server-side)
- **Dependencies:** None
- **Acceptance:** AC30-AC37

**Task 1.5: ShipStation Sync Month-Scoped**
- **Files:** `app/eqms/modules/shipstation_sync/admin.py`, `app/eqms/modules/shipstation_sync/service.py::run_sync()`, `app/eqms/templates/admin/shipstation/index.html`
- **Steps:**
  1. Add month picker to sync form (YYYY-MM format)
  2. Update `run_sync()` to accept optional `month` parameter
  3. If month provided: Calculate start_date = month-01, end_date = next_month-01
  4. If not provided: Use default (2025-01-01 to now)
  5. Test: Sync single month completes without timeout
- **Dependencies:** None
- **Acceptance:** AC38-AC41

### Phase 2: Enhancements (P1/P2)

**Task 2.1: Enhanced Note-Taking Workflow**
- **Files:** `app/eqms/modules/customer_profiles/admin.py`, `app/eqms/templates/admin/sales_dashboard/index.html`
- **Steps:**
  1. Add AJAX endpoint for inline note creation
  2. Enhance note editor to support order context
  3. Add note badges/indicators on order rows
  4. Make notes editable inline
- **Dependencies:** Task 1.1
- **Acceptance:** Enhanced note workflow

**Task 2.2: Customer Merge UI (Optional)**
- **Files:** `app/eqms/modules/customer_profiles/admin.py`, `app/eqms/templates/admin/customers/list.html`
- **Steps:**
  1. Add merge candidates detection
  2. Add merge UI (select master + duplicate)
  3. Add merge endpoint
  4. Test merge process
- **Dependencies:** None
- **Acceptance:** Can merge duplicate customers safely

**Task 2.3: Performance Optimization**
- **Files:** `app/eqms/modules/rep_traceability/service.py`
- **Steps:**
  1. Add caching for Lot Log (load once, reuse)
  2. Optimize dashboard queries (use SQL aggregates)
  3. Add indexes if needed
- **Dependencies:** Task 1.2
- **Acceptance:** Dashboard loads in < 2 seconds

---

## 11) Suggested Appearance Enhancements

### 11.1 Consistent Spacing & Typography

**Typography Scale:**
- Page titles: `font-size: 24px; font-weight: 700;` (h1)
- Section headers: `font-size: 16px; font-weight: 600;` (h2)
- Table headers: `font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;`
- Body text: `font-size: 14px;`
- Muted text: `font-size: 12px; color: var(--muted);`

**Spacing:**
- Card gaps: `14px` (consistent across all pages)
- Card padding: `16px`
- Form field gaps: `12px`
- Table cell padding: `10px 12px`

**Apply to:** All admin pages

### 11.2 Modern Table Styling

**Table Features:**
- Sticky headers: `position: sticky; top: 0; background: var(--card-bg); z-index: 10;`
- Hover states: `tr:hover { background: rgba(255,255,255,0.05); }`
- Striped rows: `tr:nth-child(even) { background: rgba(255,255,255,0.02); }`
- Pagination: Consistent "Showing X-Y of Z" + Previous/Next buttons
- Empty states: Centered message with icon, helpful hint

**Apply to:** Distribution Log, Customers, Sales Orders, Lot Tracking

### 11.3 Search/Filter Controls

**Search Bars:**
- Full-width input with search icon
- Debounced (300ms) or submit-on-enter
- Placeholder: "Search by name, city, state..."

**Filter Dropdowns:**
- Consistent styling: `padding: 10px 12px; border-radius: 10px; border: 1px solid var(--border);`
- Grouped logically (date filters together, categorical filters together)
- "Clear Filters" link always visible

**Apply to:** Distribution Log, Customers, Sales Orders

### 11.4 Consistent Empty States

**Empty State Pattern:**
```html
<div style="text-align:center; padding:40px 20px;">
  <p class="muted" style="margin:0 0 12px 0;">No [items] found.</p>
  <p class="muted" style="font-size:12px; margin:0 0 16px 0;">[Helpful hint about what to do next]</p>
  <a class="button button--secondary" href="[action_url]">[Primary Action]</a>
</div>
```

**Apply to:** All list views (Distribution Log, Customers, Sales Orders, etc.)

### 11.5 Loading States

**Loading Indicator:**
- Show spinner or "Loading..." text during AJAX requests
- Disable buttons during submission
- Show success/error messages after completion

**Apply to:** Modal data loading, form submissions, AJAX note creation

### 11.6 Button Consistency

**Button Styles:**
- Primary: `.button` (blue, for main actions)
- Secondary: `.button--secondary` (gray, for secondary actions)
- Danger: `.button--danger` (red, for delete actions)
- Size: Consistent padding `6px 12px` for small, `10px 16px` for normal

**Apply to:** All pages

### 11.7 Reduce Clutter

**Remove:**
- Debug blocks (`{{ debug }}`, `{{ request }}` dumps)
- Unnecessary stats panels (only show metrics that are useful)
- Raw JSON dumps (format data properly)
- Internal IDs in UI (use human-readable labels)

**Apply to:** All pages

---

## 12) QA / Test Plan

### 12.1 Manual Test Script

**Test 1: Permission Fix**
1. Log in as ethanr@silq.tech
2. Navigate to `/admin/sales-orders/import-pdf`
3. **Expected:** Page loads (200 OK), not 403
4. Navigate to `/admin/debug/permissions`
5. **Expected:** Shows `sales_orders.import` in permissions list

**Test 2: Sales Dashboard Redesign**
1. Navigate to `/admin/sales-dashboard`
2. **Expected:** No "Sales by Month" table
3. **Expected:** No "Top Customers" table
4. **Expected:** "Recent Orders from NEW Customers" list appears
5. **Expected:** "Recent Orders from REPEAT Customers" list appears
6. **Expected:** "Sales by SKU" in right column
7. **Expected:** "Lot Tracking" in right column
8. Click "Add Note" on an order row
9. **Expected:** Inline form appears
10. Enter note text, save
11. **Expected:** Note appears in list, navigate to customer profile → Note appears there

**Test 3: Lot Tracking Accuracy**
1. Navigate to `/admin/sales-dashboard`
2. Scroll to "Lot Tracking" table
3. **Expected:** Only shows lots from current year (2026)
4. **Expected:** Only shows correct lot numbers (matching `SLQ-#####` pattern)
5. **Expected:** No SKU names appear as lots
6. **Expected:** "Active Inventory" column appears
7. **Expected:** Active Inventory = Lot Log total - Distributed total
8. Check for negative inventory → **Expected:** Warning icon (⚠️) appears

**Test 4: Distribution Log Details**
1. Navigate to `/admin/distribution-log`
2. Click "Details" button on any row
3. **Expected:** Modal opens
4. **Expected:** Shows order context (Sales Order #, Order Date, Ship Date, Customer)
5. **Expected:** Shows distribution details (SKU, Lot, Quantity, Source)
6. **Expected:** Shows customer stats (First order, Last order, Total orders, Total units)
7. **Expected:** Quick action links work (View Customer Profile, Add Note)

**Test 5: Customer Cleanup**
1. Run: `python scripts/cleanup_zero_order_customers.py`
2. **Expected:** Script finds zero-order customers
3. Confirm deletion
4. **Expected:** Customers deleted, audit events recorded
5. Navigate to `/admin/customers`
6. **Expected:** Zero-order customers no longer appear

**Test 6: Customer Database Sort**
1. Navigate to `/admin/customers`
2. **Expected:** Customers sorted by most recent order (customers with orders first)
3. **Expected:** Customers with no orders appear last (alphabetically)
4. **Expected:** No "Find Duplicates" button

**Test 7: Rep Assignment**
1. Navigate to `/admin/customers/<id>`
2. **Expected:** "Primary Rep" dropdown appears
3. Select a rep, save
4. **Expected:** `primary_rep_id` updated
5. Navigate to `/admin/distribution-log`
6. **Expected:** "Rep" filter dropdown appears
7. Select a rep, apply filter
8. **Expected:** Only that rep's distributions shown
9. Navigate to `/admin/tracing/generate`
10. **Expected:** "Rep" filter appears
11. Select rep, generate report
12. **Expected:** Report includes only that rep's distributions

**Test 8: ShipStation Sync Month-Scoped**
1. Navigate to `/admin/shipstation`
2. **Expected:** Month picker appears
3. Select month "2025-01", click "Run Sync"
4. **Expected:** Sync completes for January 2025 only
5. **Expected:** No timeout errors
6. Check distribution log → **Expected:** Only January 2025 distributions

### 12.2 Automated Tests (Feasible)

**Test: Permission Seeding**
```python
# tests/test_permissions.py

def test_sales_orders_import_permission_exists():
    """Verify sales_orders.import permission exists."""
    s = db_session()
    perm = s.query(Permission).filter(Permission.key == "sales_orders.import").one_or_none()
    assert perm is not None

def test_admin_role_has_sales_orders_import():
    """Verify admin role has sales_orders.import permission."""
    s = db_session()
    admin_role = s.query(Role).filter(Role.key == "admin").one()
    perm_keys = [p.key for p in admin_role.permissions]
    assert "sales_orders.import" in perm_keys
```

**Test: Lot Tracking Year Filter**
```python
# tests/test_lot_tracking.py

def test_lot_tracking_current_year_only():
    """Verify lot tracking shows only current year."""
    s = db_session()
    current_year = date.today().year
    result = compute_sales_dashboard(s, start_date=date(current_year, 1, 1))
    
    for lot in result["lot_tracking"]:
        # All lots should be from current year
        assert lot["first_date"].year == current_year or lot["last_date"].year == current_year
```

**Test: Active Inventory Calculation**
```python
# tests/test_lot_tracking.py

def test_active_inventory_calculation():
    """Verify active inventory = produced - distributed."""
    s = db_session()
    lot_log = load_lot_log_with_inventory("app/eqms/data/LotLog.csv")
    result = compute_lot_tracking_with_inventory(s, lot_log_path="app/eqms/data/LotLog.csv")
    
    for lot in result:
        produced = lot_log[2].get(lot["lot"], 0)  # lot_inventory dict
        distributed = lot["units"]
        expected_inventory = produced - distributed
        assert lot["active_inventory"] == expected_inventory
```

**Test: Customer Cleanup**
```python
# tests/test_customer_cleanup.py

def test_zero_order_customers_identified():
    """Verify zero-order customers are correctly identified."""
    s = db_session()
    zero_order = find_zero_order_customers(s)
    
    for customer in zero_order:
        dist_count = s.query(func.count(DistributionLogEntry.id)).filter(
            DistributionLogEntry.customer_id == customer.id
        ).scalar()
        order_count = s.query(func.count(SalesOrder.id)).filter(
            SalesOrder.customer_id == customer.id
        ).scalar()
        assert dist_count == 0
        assert order_count == 0
```

---

## Summary

This implementation spec provides a complete, developer-ready plan for:
1. **Sales Dashboard Redesign** - Professional, focused interface with recent orders lists and inline note-taking
2. **Lot Tracking Accuracy** - Current year only, Lot Log corrections, Active Inventory calculation
3. **Distribution Log Enhancement** - In-page detail modals
4. **Permission Fix** - Resolve 403 error for PDF import
5. **Customer Cleanup** - Delete zero-order customers, sort by recency
6. **Rep Assignment** - Full rep support (assignment, filtering, tracing reports)
7. **ShipStation Sync Throttling** - Month-scoped sync capability

All changes are incremental, safe, and maintain data integrity. The plan includes specific file paths, code examples, acceptance criteria, and test plans.
