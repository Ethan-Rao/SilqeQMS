# Sales System Parity, De-duplication & 2025 Sales Orders — Implementation Spec

**Date:** 2026-01-19  
**Purpose:** Developer-ready implementation plan for sales system parity, customer de-duplication, sales orders as source of truth, 2025 PDF ingestion, and dropdown detail menus.

---

## Overview

### Scope + Goals

**What "Done" Means:**

1. **Sales Dashboard Parity:** Content and functionality match legacy system exactly (appearance can be modern, but capabilities must match)
2. **Customer De-duplication:** All duplicate customers identified, merged, and prevented going forward
3. **Sales Orders = Source of Truth:** New `sales_orders` and `sales_order_lines` tables; all distributions link to orders
4. **2025 Sales Orders PDF Ingestion:** System can parse and import `2025 Sales Orders.pdf` matching legacy behavior
5. **Dropdown Detail Menus:** Sales Dashboard, Distribution Log, and Customer Database have expandable detail rows
6. **ShipStation Sync Completeness:** All orders since 2025-01-01 are synced and visible

**Non-Negotiable Rules:**
- Sales Orders are source-of-truth for customer identity and order assignment
- System must support 2025 and 2026 sales views (and any future years) with consistent logic
- No breaking current working flows; changes must be incremental and safe
- Lean code only: use legacy code as reference for behavior, but do not port legacy code wholesale

---

## Current Observed Issues

### Issue 1: Sales Dashboard Content/Functionality Differs from Legacy

**Current State:**
- Sales Dashboard exists but lacks some legacy features
- Missing: Some metrics may be computed differently
- Missing: Dropdown detail menus for orders/customers

**Legacy Reference:**
- Visual metric cards: Total Units (All Time), Total Orders, Unique Customers
- Sales by Month table (month, orders, units)
- Sales by SKU table (SKU, total units)
- Top Customers table with expandable details (SKU line items, lot numbers, shipments)

### Issue 2: Customer DB Contains Duplicates

**Current State:**
- `customers` table uses `company_key` (unique constraint) for deduplication
- `canonical_customer_key()` normalizes facility names (uppercase, remove special chars)
- **Problem:** Duplicates still exist, likely due to:
  - Variations in facility name that normalize to different keys (e.g., "Hospital A" vs "Hospital A, Inc.")
  - Address-based variations not considered
  - Email/domain matching not used
  - Manual entry bypassing deduplication logic

**Evidence Needed:**
- Query: `SELECT company_key, COUNT(*) FROM customers GROUP BY company_key HAVING COUNT(*) > 1;`
- Query: `SELECT facility_name, company_key FROM customers ORDER BY company_key;` (inspect similar keys)

### Issue 3: ShipStation Sync Appears to Only Show 2026 Orders (Missing 2025)

**Current State:**
- ShipStation sync defaults to `2025-01-01` (recently fixed)
- **Problem:** May still show only 2026 if:
  - `SHIPSTATION_SINCE_DATE` not set in production
  - Hard limits (`max_orders`, `max_pages`) stopping early
  - Orders returned in reverse chronological order (most recent first)

**Verification Needed:**
- SQL query: `SELECT DATE_TRUNC('month', ship_date) AS month, COUNT(*) FROM distribution_log_entries WHERE source='shipstation' AND ship_date >= '2025-01-01' GROUP BY month ORDER BY month;`
- Should show rows for 2025 months

### Issue 4: No Sales Orders Table (Orders Are Just Grouped from Distributions)

**Current State:**
- Orders are derived by grouping `distribution_log_entries` by `order_number` + `ship_date`
- No separate `sales_orders` table exists
- **Problem:** Cannot enforce order-level constraints, cannot track order-level metadata, distributions can exist without orders

**Required Change:**
- Create `sales_orders` and `sales_order_lines` tables
- Link `distribution_log_entries.sales_order_id` FK
- Make orders the source of truth for customer identity

---

## Target Behavior (Parity Requirements)

### A) Sales Dashboard Parity

**Required Metrics/Cards:**
1. **Total Units (All Time)** - Blue card, large number
2. **Total Orders (Windowed)** - Green card, large number (distinct order_number in date window)
3. **Unique Customers (Windowed)** - Info card, large number (distinct customers in date window)
4. **First-Time Customers (Windowed)** - Success card (customers with exactly 1 order ever)
5. **Repeat Customers (Windowed)** - Primary card (customers with 2+ orders ever)

**Required Tables:**
1. **Sales by Month** - Columns: Month (YYYY-MM), Orders (count distinct order_number), Units (sum quantity)
2. **Sales by SKU** - Columns: SKU, Total Units (sum quantity)
3. **Top Customers** - Columns: Customer Name (linked), Total Orders, Total Units, Last Order Date

**Required Actions:**
- Export CSV (existing: `/admin/sales-dashboard/export`)
- Link to customer profile (existing: links work)
- "Add Note" link (existing: links to customer profile #notes)
- "Log Manual Distribution" button (existing: links to `/admin/distribution-log/new`)
- **NEW:** Dropdown detail menus on order rows showing SKU line items, lot numbers, shipments

**Date/Year Filtering:**
- Default `start_date = 2025-01-01`
- Windowed metrics use `ship_date >= start_date`
- Lifetime metrics (Total Units All Time) ignore date filter

### B) Customer Database Parity

**Required Features:**
- Search: Facility name, city, state (server-side LIKE)
- Filters: State dropdown, Year (2025/2026), Type (First-Time/Repeat)
- **NEW:** Dropdown detail menus on customer rows showing:
  - Order history summary (orders by date, totals)
  - Recent SKUs and lots
  - Quick link actions (view profile, add note, view distributions)

**Legacy Accordion Pattern:**
- Legacy uses Bootstrap accordion with inline order history
- **New System:** Use dropdown/accordion pattern but keep server-side pagination
- Each customer row expands to show: Contact Info, Order Summary, Order History

### C) Customer Profile Parity

**Required Tabs:**
- Overview: Stats cards, contact info, SKU breakdown
- Orders: Grouped by order_number, with year/date filters
- Distributions: All distribution entries (line items)
- Notes: Chronological list with add/edit/delete

**Required Features:**
- Orders grouped per order (not line-level)
- Year filter (2025/2026) on Orders tab
- Date range filter on Orders tab
- Export customer data (CSV)

### D) Distribution Log Parity

**Required Features:**
- Customer selection required for manual entries
- Auto-fill facility/address from customer
- **NEW:** Dropdown detail menus on distribution rows showing:
  - Associated sales order reference (if linked)
  - SKUs + quantities + lots tied to that order/distribution
  - Mismatch flags (e.g., distribution qty exceeds order qty)

---

## Data Model Changes

### New Tables: Sales Orders (Source of Truth)

**Table 1: `sales_orders`**

```sql
CREATE TABLE sales_orders (
    id SERIAL PRIMARY KEY,
    
    -- Order identification
    order_number TEXT NOT NULL,  -- Unique per source
    order_date DATE NOT NULL,  -- Order creation/placement date
    ship_date DATE,  -- Actual ship date (may differ from order_date)
    
    -- Customer (source of truth)
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    
    -- Source
    source TEXT NOT NULL CHECK (source IN ('shipstation', 'manual', 'csv_import', 'pdf_import')),
    
    -- External references
    ss_order_id TEXT,  -- ShipStation order ID (if source='shipstation')
    external_key TEXT,  -- For idempotency (e.g., "{ss_order_id}" or "{order_number}:{order_date}")
    
    -- Optional metadata
    rep_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    tracking_number TEXT,
    notes TEXT,
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'shipped', 'cancelled', 'completed')),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id),
    updated_by_user_id INTEGER REFERENCES users(id),
    
    -- Constraints
    UNIQUE(source, external_key) WHERE external_key IS NOT NULL,
    INDEX idx_sales_orders_customer_id (customer_id),
    INDEX idx_sales_orders_order_number (order_number),
    INDEX idx_sales_orders_order_date (order_date),
    INDEX idx_sales_orders_ship_date (ship_date),
    INDEX idx_sales_orders_source (source)
);
```

**Table 2: `sales_order_lines`**

```sql
CREATE TABLE sales_order_lines (
    id SERIAL PRIMARY KEY,
    
    -- Link to order
    sales_order_id INTEGER NOT NULL REFERENCES sales_orders(id) ON DELETE CASCADE,
    
    -- Line item details
    sku TEXT NOT NULL CHECK (sku IN ('211810SPT', '211610SPT', '211410SPT')),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    lot_number TEXT,  -- Optional (may not be known at order time)
    
    -- Line item metadata
    line_number INTEGER,  -- Order line number (if applicable)
    unit_price NUMERIC(10,2),  -- Optional (for future use)
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_sales_order_lines_sales_order_id (sales_order_id),
    INDEX idx_sales_order_lines_sku (sku)
);
```

### Modified Table: `distribution_log_entries`

**Add Foreign Key to Sales Orders:**

```sql
ALTER TABLE distribution_log_entries
ADD COLUMN sales_order_id INTEGER REFERENCES sales_orders(id) ON DELETE SET NULL;

CREATE INDEX idx_distribution_log_sales_order_id ON distribution_log_entries(sales_order_id);
```

**Rationale:**
- Distributions link to orders (many distributions can fulfill one order)
- If order deleted, distributions remain but `sales_order_id` becomes NULL
- Allows tracking which distributions fulfill which order lines

### Enhanced Customer Deduplication

**Current:** `company_key` (unique constraint) via `canonical_customer_key()`

**Enhanced Strategy (Multi-Tier Matching):**

**Tier 1: Exact Match (High Confidence)**
- `company_key` matches exactly → use existing customer

**Tier 2: Strong Match (Medium Confidence)**
- Normalized name matches + address matches (city + state + zip)
- Email domain matches (if contact_email exists)
- → Auto-merge or flag for review

**Tier 3: Weak Match (Low Confidence)**
- Normalized name similar (fuzzy match) + same state
- → Flag for manual review

**Implementation:**
- Add `customer_merge_candidates` table (optional, for review queue)
- Enhance `find_or_create_customer()` to check multiple tiers
- Add admin UI for reviewing merge candidates

**New Table: `customer_merge_candidates` (Optional, P1)**

```sql
CREATE TABLE customer_merge_candidates (
    id SERIAL PRIMARY KEY,
    
    -- Two customers that might be duplicates
    customer_id_1 INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    customer_id_2 INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Match confidence
    confidence TEXT NOT NULL CHECK (confidence IN ('strong', 'weak')),
    match_reason TEXT,  -- e.g., "name+address", "email_domain"
    
    -- Review status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'merged')),
    reviewed_by_user_id INTEGER REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(customer_id_1, customer_id_2),
    CHECK(customer_id_1 != customer_id_2)
);
```

---

## Import/Sync Logic

### ShipStation Sync

**Current Implementation:**
- `app/eqms/modules/shipstation_sync/service.py::run_sync()` (line 66)
- Defaults to `2025-01-01` (recently fixed)
- Creates `distribution_log_entries` directly

**Required Changes:**

1. **Create Sales Order First:**
   ```python
   # In run_sync(), for each order:
   # 1. Create or find sales_order
   sales_order = find_or_create_sales_order(
       s,
       order_number=order_number,
       order_date=order_date,  # from ShipStation order.createDate
       ship_date=ship_date,  # from shipment.shipDate
       customer_id=customer.id,  # from _get_customer_from_ship_to()
       source='shipstation',
       ss_order_id=order_id,
       external_key=f"ss:{order_id}",  # for idempotency
   )
   
   # 2. Create sales_order_lines from order items
   for item in items:
       create_sales_order_line(
           s,
           sales_order_id=sales_order.id,
           sku=canonicalize_sku(item.sku),
           quantity=infer_units(item),
           lot_number=None,  # May not be known at order time
       )
   
   # 3. Create distribution_log_entries from shipments
   for shipment in shipments:
       for sku, lot, qty in extract_sku_lot_pairs(shipment):
           create_distribution_entry(
               s,
               sales_order_id=sales_order.id,  # Link to order
               ship_date=ship_date,
               order_number=order_number,
               customer_id=customer.id,
               sku=sku,
               lot_number=lot,
               quantity=qty,
               source='shipstation',
           )
   ```

2. **Idempotency:**
   - `sales_orders.external_key` = `"ss:{order_id}"` (unique per source)
   - Re-running sync finds existing order, updates if needed, creates new distributions only

3. **Date Range Logic:**
   - Use `SHIPSTATION_SINCE_DATE` (default `2025-01-01`)
   - Query ShipStation orders: `create_date_start >= since_date`
   - Paginate through all pages until empty or limits hit

4. **Progress Reporting:**
   - Store `last_order_date` in `ShipStationSyncRun`
   - Display in UI: "Last synced order date: YYYY-MM-DD"
   - Show warning if limits hit: "⚠️ Sync stopped early due to max_orders limit"

### 2025 Sales Orders PDF Ingestion

**Source Document:** `2025 Sales Orders.pdf`

**Legacy Behavior (Reference):**
- Legacy parsed PDF tables to extract: Order Number, Order Date, Customer Name, SKU, Quantity, Lot (if present)
- Created distribution entries from parsed data
- Matched customers by facility name

**New Implementation:**

**PDF Parsing Strategy:**
1. Use `pdfplumber` or `PyPDF2` + `tabula-py` for table extraction
2. Extract tables from PDF pages
3. Map columns: Order Number, Order Date, Customer Name, SKU, Quantity, Lot
4. Validate: SKU format, quantity > 0, date format
5. Create sales orders + order lines + distribution entries

**Parsing Function:**
```python
# app/eqms/modules/rep_traceability/parsers/pdf.py

def parse_sales_orders_pdf(file_bytes: bytes) -> tuple[list[dict], list[ParseError]]:
    """
    Parse 2025 Sales Orders PDF.
    
    Returns:
        - List of order dicts: {
            "order_number": str,
            "order_date": date,
            "customer_name": str,
            "lines": [
                {"sku": str, "quantity": int, "lot_number": str | None}
            ]
          }
        - List of parse errors
    """
    # Implementation using pdfplumber or tabula-py
    # Extract tables, map columns, validate
    pass
```

**Import Route:**
- `POST /admin/sales-orders/import-pdf`
- Upload PDF file
- Parse → create sales orders + lines + distributions
- Show results: orders created, lines created, distributions created, errors

**Matching Strategy:**
- Customer: Use `find_or_create_customer()` with facility_name from PDF
- Order: Create new `sales_order` with `source='pdf_import'`, `external_key=f"pdf:{order_number}:{order_date}"`
- Distribution: Link to `sales_order_id`

**Success Criteria:**
- Row counts match PDF (spot-check sample orders)
- Date coverage: Orders span expected 2025 months
- Customer linking: All orders have `customer_id` set
- Distribution linking: All distributions have `sales_order_id` set

---

## De-duplication & Merge Plan

### Root Cause Analysis

**Why Duplicates Exist:**

1. **Name Variations:**
   - "Hospital A" vs "Hospital A, Inc." → different `company_key`
   - "St. Mary's Hospital" vs "St Marys Hospital" → different normalization
   - Solution: Enhanced normalization (remove common suffixes: Inc., LLC, Corp., etc.)

2. **Address Variations:**
   - Same facility, different address formats
   - Solution: Address-based matching (city + state + zip)

3. **Email Domain Matching:**
   - Same organization, different facility names but same email domain
   - Solution: Extract domain from `contact_email`, match by domain

4. **Manual Entry Bypass:**
   - Admin creates customer without checking for duplicates
   - Solution: Always use `find_or_create_customer()` (never direct `Customer()` creation)

### Enhanced Deduplication Strategy

**Tier 1: Exact Match (High Confidence)**
```python
def find_customer_exact_match(s, facility_name: str) -> Customer | None:
    ck = canonical_customer_key(facility_name)
    return s.query(Customer).filter(Customer.company_key == ck).one_or_none()
```

**Tier 2: Strong Match (Medium Confidence)**
```python
def find_customer_strong_match(
    s, 
    facility_name: str, 
    city: str | None, 
    state: str | None, 
    zip: str | None,
    email: str | None
) -> Customer | None:
    # Normalize name (remove common suffixes)
    normalized = normalize_facility_name(facility_name)  # Remove "Inc.", "LLC", etc.
    ck = canonical_customer_key(normalized)
    
    # Try company_key match first
    c = s.query(Customer).filter(Customer.company_key == ck).one_or_none()
    if c:
        return c
    
    # Try address match (city + state + zip)
    if city and state and zip:
        c = (
            s.query(Customer)
            .filter(
                Customer.city.ilike(city),
                Customer.state.ilike(state),
                Customer.zip == zip
            )
            .first()
        )
        if c:
            return c
    
    # Try email domain match
    if email:
        domain = email.split('@')[1] if '@' in email else None
        if domain:
            c = (
                s.query(Customer)
                .filter(Customer.contact_email.like(f"%@{domain}"))
                .first()
            )
            if c:
                return c
    
    return None
```

**Tier 3: Weak Match (Low Confidence - Manual Review)**
```python
def find_customer_weak_match(s, facility_name: str, state: str | None) -> list[Customer]:
    # Fuzzy name match + same state
    normalized = normalize_facility_name(facility_name)
    ck_base = canonical_customer_key(normalized)
    
    # Find customers with similar company_key (first N chars match)
    if len(ck_base) >= 5:
        prefix = ck_base[:5]
        candidates = (
            s.query(Customer)
            .filter(
                Customer.company_key.like(f"{prefix}%"),
                Customer.state == state if state else True
            )
            .limit(10)
            .all()
        )
        return candidates
    
    return []
```

### Merge Strategy for Existing Duplicates

**Step 1: Identify Duplicates**
```sql
-- Find potential duplicates (same company_key or similar names)
SELECT 
    c1.id AS id1, c1.facility_name AS name1, c1.company_key AS key1,
    c2.id AS id2, c2.facility_name AS name2, c2.company_key AS key2
FROM customers c1
JOIN customers c2 ON c1.id < c2.id
WHERE 
    c1.company_key = c2.company_key  -- Exact match
    OR (
        -- Similar names (first 8 chars match)
        SUBSTR(c1.company_key, 1, 8) = SUBSTR(c2.company_key, 1, 8)
        AND c1.state = c2.state
    );
```

**Step 2: Merge Process**
1. **Select "Master" Customer:**
   - Prefer customer with most orders (most `distribution_log_entries`)
   - Prefer customer with most complete data (address, contact info)
   - Prefer oldest customer (earliest `created_at`)

2. **Merge Data:**
   - Update all `distribution_log_entries.customer_id` from duplicate → master
   - Update all `customer_notes.customer_id` from duplicate → master
   - Update all `sales_orders.customer_id` from duplicate → master
   - Merge address/contact fields (keep non-null values from both)

3. **Delete Duplicate:**
   - Soft delete (add `is_deleted` flag) OR hard delete if no dependencies
   - Record merge in audit log

**Migration Script:**
```python
# scripts/merge_duplicate_customers.py

def merge_customers(s, master_id: int, duplicate_id: int, user: User):
    master = s.query(Customer).filter(Customer.id == master_id).one()
    duplicate = s.query(Customer).filter(Customer.id == duplicate_id).one()
    
    # Update all references
    s.query(DistributionLogEntry).filter(
        DistributionLogEntry.customer_id == duplicate_id
    ).update({"customer_id": master_id})
    
    s.query(CustomerNote).filter(
        CustomerNote.customer_id == duplicate_id
    ).update({"customer_id": master_id})
    
    s.query(SalesOrder).filter(
        SalesOrder.customer_id == duplicate_id
    ).update({"customer_id": master_id})
    
    # Merge fields (keep non-null from duplicate)
    if not master.address1 and duplicate.address1:
        master.address1 = duplicate.address1
    # ... repeat for other fields
    
    # Delete duplicate
    s.delete(duplicate)
    
    # Audit
    record_event(
        s,
        actor=user,
        action="customer.merge",
        entity_type="Customer",
        entity_id=str(master_id),
        metadata={
            "merged_customer_id": duplicate_id,
            "merged_facility_name": duplicate.facility_name,
        },
    )
```

### Prevention: Enhanced `find_or_create_customer()`

**Updated Function:**
```python
def find_or_create_customer(
    s,
    *,
    facility_name: str,
    address1: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip: str | None = None,
    contact_email: str | None = None,
    ...
) -> Customer:
    # Tier 1: Exact match
    c = find_customer_exact_match(s, facility_name)
    if c:
        # Update fields if provided
        update_customer_fields(c, address1, city, state, zip, contact_email, ...)
        return c
    
    # Tier 2: Strong match
    c = find_customer_strong_match(s, facility_name, city, state, zip, contact_email)
    if c:
        # Auto-merge or flag for review
        # For now: use existing customer, update fields
        update_customer_fields(c, address1, city, state, zip, contact_email, ...)
        return c
    
    # Tier 3: Weak match (create merge candidate for review)
    weak_matches = find_customer_weak_match(s, facility_name, state)
    if weak_matches:
        # Create merge candidate (don't block creation)
        for candidate in weak_matches:
            create_merge_candidate(s, candidate.id, facility_name, confidence='weak')
    
    # No match found: create new customer
    ck = canonical_customer_key(facility_name)
    c = Customer(
        company_key=ck,
        facility_name=facility_name,
        address1=address1,
        city=city,
        state=state,
        zip=zip,
        contact_email=contact_email,
        ...
    )
    s.add(c)
    s.flush()
    return c
```

**Normalization Enhancement:**
```python
def normalize_facility_name(name: str) -> str:
    """Remove common suffixes before canonicalization."""
    s = (name or "").strip()
    # Remove common suffixes (case-insensitive)
    suffixes = [
        r'\s+inc\.?$', r'\s+llc\.?$', r'\s+corp\.?$', r'\s+corporation$',
        r'\s+ltd\.?$', r'\s+limited$', r'\s+co\.?$', r'\s+company$',
    ]
    for pattern in suffixes:
        s = re.sub(pattern, '', s, flags=re.IGNORECASE)
    return s.strip()
```

---

## UI/UX Requirements

### Sales Dashboard Dropdowns

**Pattern:** Each order row (or customer card) has a dropdown/accordion that expands to show details

**Implementation:**
- Use HTML `<details>` element or JavaScript accordion
- Lazy-load detail data via AJAX endpoint

**Detail Content (per order/customer):**
- **SKU Line Items:** List of SKUs with quantities
- **Lot Numbers:** All lot numbers used in this order (if available)
- **Shipments/Fulfillment:** Shipment dates, tracking numbers (if available)
- **Distribution Entries:** Links to distribution log entries for this order

**Backend Endpoint:**
```python
@bp.get("/sales-dashboard/order-details/<order_number>")
@require_permission("sales_dashboard.view")
def order_details(order_number: str):
    """Return JSON with order details for dropdown."""
    s = db_session()
    order = s.query(SalesOrder).filter(SalesOrder.order_number == order_number).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    lines = s.query(SalesOrderLine).filter(
        SalesOrderLine.sales_order_id == order.id
    ).all()
    
    distributions = s.query(DistributionLogEntry).filter(
        DistributionLogEntry.sales_order_id == order.id
    ).all()
    
    return jsonify({
        "order_number": order.order_number,
        "order_date": order.order_date.isoformat(),
        "ship_date": order.ship_date.isoformat() if order.ship_date else None,
        "customer": order.customer.facility_name,
        "lines": [
            {"sku": l.sku, "quantity": l.quantity, "lot_number": l.lot_number}
            for l in lines
        ],
        "distributions": [
            {
                "id": d.id,
                "sku": d.sku,
                "lot": d.lot_number,
                "quantity": d.quantity,
                "ship_date": d.ship_date.isoformat(),
            }
            for d in distributions
        ],
    })
```

**Template Pattern:**
```html
<tr>
  <td>{{ order.order_number }}</td>
  <td>{{ order.customer.facility_name }}</td>
  <td>{{ order.total_units }}</td>
  <td>
    <details>
      <summary style="cursor:pointer; color:var(--primary);">View Details</summary>
      <div id="order-{{ order.order_number }}-details" data-order="{{ order.order_number }}">
        <!-- Lazy-loaded via AJAX -->
        <div class="muted">Loading...</div>
      </div>
    </details>
  </td>
</tr>

<script>
document.querySelectorAll('details').forEach(detail => {
  detail.addEventListener('toggle', function() {
    if (this.open && !this.dataset.loaded) {
      const orderNum = this.querySelector('[data-order]').dataset.order;
      fetch(`/admin/sales-dashboard/order-details/${orderNum}`)
        .then(r => r.json())
        .then(data => {
          // Render details
          this.dataset.loaded = 'true';
        });
    }
  });
});
</script>
```

### Distribution Log Dropdowns

**Pattern:** Each distribution entry row has dropdown showing order context

**Detail Content:**
- **Associated Sales Order:** Order number, order date, customer
- **Order Lines:** Which order lines this distribution fulfills
- **Mismatch Flags:** Warnings if distribution qty exceeds order line qty, or lot doesn't match

**Backend Endpoint:**
```python
@bp.get("/distribution-log/entry-details/<entry_id>")
@require_permission("distribution_log.view")
def distribution_entry_details(entry_id: int):
    """Return JSON with distribution entry details."""
    s = db_session()
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    
    order = entry.sales_order if entry.sales_order_id else None
    order_lines = []
    if order:
        order_lines = s.query(SalesOrderLine).filter(
            SalesOrderLine.sales_order_id == order.id,
            SalesOrderLine.sku == entry.sku
        ).all()
    
    # Check for mismatches
    mismatches = []
    if order_lines:
        total_ordered = sum(l.quantity for l in order_lines)
        if entry.quantity > total_ordered:
            mismatches.append(f"Distribution qty ({entry.quantity}) exceeds order qty ({total_ordered})")
    
    return jsonify({
        "entry_id": entry.id,
        "order": {
            "id": order.id if order else None,
            "order_number": order.order_number if order else None,
            "order_date": order.order_date.isoformat() if order and order.order_date else None,
        } if order else None,
        "order_lines": [
            {"sku": l.sku, "quantity": l.quantity, "lot_number": l.lot_number}
            for l in order_lines
        ],
        "mismatches": mismatches,
    })
```

### Customer DB Dropdowns

**Pattern:** Each customer row expands to show order history summary

**Detail Content:**
- **Order History Summary:** Orders by date (last 10 orders)
- **Recent SKUs and Lots:** Most recent SKUs and lot numbers used
- **Quick Actions:** Links to view profile, add note, view distributions

**Backend Endpoint:**
```python
@bp.get("/customers/<customer_id>/summary")
@require_permission("customers.view")
def customer_summary(customer_id: int):
    """Return JSON with customer summary for dropdown."""
    s = db_session()
    customer = s.get(Customer, customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    
    # Recent orders (last 10)
    recent_orders = (
        s.query(SalesOrder)
        .filter(SalesOrder.customer_id == customer_id)
        .order_by(SalesOrder.order_date.desc())
        .limit(10)
        .all()
    )
    
    # Recent SKUs and lots
    recent_distributions = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.customer_id == customer_id)
        .order_by(DistributionLogEntry.ship_date.desc())
        .limit(20)
        .all()
    )
    
    skus = sorted(set(d.sku for d in recent_distributions))
    lots = sorted(set(d.lot_number for d in recent_distributions if d.lot_number))[:10]
    
    return jsonify({
        "customer_id": customer.id,
        "facility_name": customer.facility_name,
        "recent_orders": [
            {
                "order_number": o.order_number,
                "order_date": o.order_date.isoformat(),
                "total_units": sum(l.quantity for l in o.lines),
            }
            for o in recent_orders
        ],
        "recent_skus": skus,
        "recent_lots": lots,
    })
```

**Performance Constraints:**
- Lazy-load: Details only fetched when dropdown opens
- Cache: Consider caching summary data for 5 minutes (optional, P1)
- Limit: Recent orders limited to 10, recent distributions to 20

---

## API/Backend Changes

### New Routes

**Sales Orders:**
- `GET /admin/sales-orders` - List sales orders (with filters: date, customer, source)
- `GET /admin/sales-orders/<id>` - Order detail (with lines + distributions)
- `POST /admin/sales-orders/new` - Create manual order
- `POST /admin/sales-orders/import-pdf` - Import from PDF
- `GET /admin/sales-orders/<id>/distributions` - List distributions for this order

**Dropdown Details (AJAX):**
- `GET /admin/sales-dashboard/order-details/<order_number>` - Order details JSON
- `GET /admin/distribution-log/entry-details/<entry_id>` - Distribution entry details JSON
- `GET /admin/customers/<customer_id>/summary` - Customer summary JSON

**Customer Merge:**
- `GET /admin/customers/merge-candidates` - List merge candidates (pending review)
- `POST /admin/customers/merge` - Merge two customers (master + duplicate)

### New Service Functions

**Sales Orders:**
```python
# app/eqms/modules/rep_traceability/service.py

def find_or_create_sales_order(
    s,
    *,
    order_number: str,
    order_date: date,
    ship_date: date | None,
    customer_id: int,
    source: str,
    external_key: str | None = None,
    ...
) -> SalesOrder:
    """Find existing order by external_key or create new."""
    pass

def create_sales_order_line(
    s,
    *,
    sales_order_id: int,
    sku: str,
    quantity: int,
    lot_number: str | None = None,
    ...
) -> SalesOrderLine:
    """Create order line."""
    pass

def link_distribution_to_order(
    s,
    *,
    distribution: DistributionLogEntry,
    sales_order_id: int,
) -> None:
    """Link distribution to sales order."""
    pass
```

**Customer Deduplication:**
```python
# app/eqms/modules/customer_profiles/service.py

def find_customer_exact_match(s, facility_name: str) -> Customer | None:
    """Tier 1: Exact company_key match."""
    pass

def find_customer_strong_match(
    s,
    facility_name: str,
    city: str | None,
    state: str | None,
    zip: str | None,
    email: str | None,
) -> Customer | None:
    """Tier 2: Strong match (name+address or email domain)."""
    pass

def find_customer_weak_match(s, facility_name: str, state: str | None) -> list[Customer]:
    """Tier 3: Weak match (fuzzy name + state)."""
    pass

def normalize_facility_name(name: str) -> str:
    """Remove common suffixes before canonicalization."""
    pass

def merge_customers(
    s,
    *,
    master_id: int,
    duplicate_id: int,
    user: User,
) -> Customer:
    """Merge duplicate customer into master."""
    pass
```

**PDF Parsing:**
```python
# app/eqms/modules/rep_traceability/parsers/pdf.py

def parse_sales_orders_pdf(file_bytes: bytes) -> tuple[list[dict], list[ParseError]]:
    """Parse 2025 Sales Orders PDF into order dicts."""
    pass
```

---

## Acceptance Criteria / Tests

### Sales Dashboard Parity

- [ ] **AC1:** Sales Dashboard shows all required metric cards (Total Units All Time, Total Orders Windowed, Unique Customers, First-Time, Repeat)
- [ ] **AC2:** Sales by Month table appears with correct data (month, orders, units)
- [ ] **AC3:** Sales by SKU table appears with correct data (SKU, units)
- [ ] **AC4:** Top Customers table appears with links to customer profiles
- [ ] **AC5:** Dropdown detail menus work on order/customer rows (lazy-load, show SKU items, lots, shipments)
- [ ] **AC6:** Export CSV works and includes all windowed data
- [ ] **AC7:** "Add Note" and "Log Manual Distribution" buttons work

### Customer De-duplication

- [ ] **AC8:** Enhanced `find_or_create_customer()` checks Tier 1 (exact), Tier 2 (strong), Tier 3 (weak) matches
- [ ] **AC9:** Existing duplicates are identified via SQL query
- [ ] **AC10:** Merge script successfully merges duplicate customers (distributions, notes, orders updated)
- [ ] **AC11:** No new duplicates created after merge (test: create customer with similar name → uses existing)
- [ ] **AC12:** Merge candidates table populated for weak matches (admin can review)

### Sales Orders = Source of Truth

- [ ] **AC13:** `sales_orders` and `sales_order_lines` tables exist
- [ ] **AC14:** ShipStation sync creates sales orders first, then order lines, then distributions
- [ ] **AC15:** All distributions have `sales_order_id` FK (or NULL for legacy orphaned entries)
- [ ] **AC16:** Manual distribution entry prompts to select/create sales order
- [ ] **AC17:** Customer identity comes from `sales_orders.customer_id` (not free-text facility_name)

### 2025 Sales Orders PDF Ingestion

- [ ] **AC18:** PDF import route exists (`POST /admin/sales-orders/import-pdf`)
- [ ] **AC19:** PDF parser extracts orders, order lines, and customer names correctly
- [ ] **AC20:** Import creates sales orders + order lines + distributions
- [ ] **AC21:** Row counts match PDF (spot-check: count orders in PDF vs DB)
- [ ] **AC22:** Date coverage: Orders span 2025 months (verify via SQL)
- [ ] **AC23:** Customer linking: All imported orders have `customer_id` set
- [ ] **AC24:** Distribution linking: All imported distributions have `sales_order_id` set

### Dropdown Detail Menus

- [ ] **AC25:** Sales Dashboard order rows have dropdowns that expand to show SKU items, lots, shipments
- [ ] **AC26:** Distribution Log entry rows have dropdowns that expand to show order context, mismatch flags
- [ ] **AC27:** Customer Database rows have dropdowns that expand to show order history, recent SKUs/lots
- [ ] **AC28:** Dropdowns lazy-load data (only fetch when opened)
- [ ] **AC29:** Dropdowns work without JavaScript errors

### ShipStation Sync Completeness

- [ ] **AC30:** ShipStation sync pulls from `2025-01-01` by default
- [ ] **AC31:** SQL verification query shows rows for 2025 months
- [ ] **AC32:** Spot-check: Known 2025 order IDs appear in `sales_orders` and `distribution_log_entries`
- [ ] **AC33:** Sales Dashboard shows 2025 data when `start_date=2025-01-01`
- [ ] **AC34:** Customer Profile shows 2025 orders in Orders tab

---

## Implementation Plan (P0/P1/P2)

### Phase 0: Foundation (P0 - Must Have)

**Task 0.1: Create Sales Orders Data Model**
- [ ] Create Alembic migration: `add_sales_orders_tables.py`
- [ ] Add `sales_orders` table (id, order_number, order_date, ship_date, customer_id, source, external_key, ...)
- [ ] Add `sales_order_lines` table (id, sales_order_id, sku, quantity, lot_number, ...)
- [ ] Add `sales_order_id` FK to `distribution_log_entries`
- [ ] Update models: `app/eqms/modules/rep_traceability/models.py` (add `SalesOrder`, `SalesOrderLine`)
- [ ] Run migration, verify tables exist

**Task 0.2: Enhance Customer Deduplication Logic**
- [ ] Update `canonical_customer_key()` to use `normalize_facility_name()` first (remove suffixes)
- [ ] Add `find_customer_strong_match()` (address + email domain matching)
- [ ] Add `find_customer_weak_match()` (fuzzy matching)
- [ ] Update `find_or_create_customer()` to use multi-tier matching
- [ ] Test: Create customer "Hospital A" → Create "Hospital A, Inc." → Should find existing

**Task 0.3: ShipStation Sync - Create Sales Orders**
- [ ] Update `app/eqms/modules/shipstation_sync/service.py::run_sync()`
- [ ] For each order: Create `SalesOrder` first, then `SalesOrderLine`, then `DistributionLogEntry`
- [ ] Link distributions to `sales_order_id`
- [ ] Test: Run sync, verify sales orders created, distributions linked

**Acceptance:** Sales orders exist, ShipStation sync creates them, distributions link to orders

### Phase 1: Core Features (P0/P1)

**Task 1.1: 2025 Sales Orders PDF Ingestion**
- [ ] Install PDF parsing library: `pdfplumber` or `tabula-py` (add to `requirements.txt`)
- [ ] Create `app/eqms/modules/rep_traceability/parsers/pdf.py`
- [ ] Implement `parse_sales_orders_pdf()` (extract tables, map columns, validate)
- [ ] Create route: `POST /admin/sales-orders/import-pdf`
- [ ] Import flow: Parse → Create sales orders → Create order lines → Create distributions
- [ ] Test: Import `2025 Sales Orders.pdf`, verify row counts, date coverage, customer linking

**Task 1.2: Manual Distribution Entry - Link to Sales Order**
- [ ] Update `app/eqms/templates/admin/distribution_log/edit.html`
- [ ] Add "Sales Order" dropdown (searchable, with "Create New Order" option)
- [ ] Update `distribution_log_new_post()` to require/select sales order
- [ ] If order selected: Auto-fill customer, order_number, ship_date from order
- [ ] If "Create New Order": Inline form to create order first, then distribution
- [ ] Test: Create manual distribution with order selection → Verify linking

**Task 1.3: Customer Merge Script + UI**
- [ ] Create `scripts/merge_duplicate_customers.py` (identify + merge duplicates)
- [ ] Create route: `GET /admin/customers/merge-candidates` (list pending merges)
- [ ] Create route: `POST /admin/customers/merge` (merge master + duplicate)
- [ ] Test: Identify duplicates → Merge → Verify all references updated

**Task 1.4: Sales Dashboard Dropdown Details**
- [ ] Create route: `GET /admin/sales-dashboard/order-details/<order_number>` (JSON)
- [ ] Update `app/eqms/templates/admin/sales_dashboard/index.html`
- [ ] Add dropdown/accordion to Top Customers table rows
- [ ] Add JavaScript to lazy-load details via AJAX
- [ ] Test: Expand dropdown → Verify details load, show SKU items, lots

**Acceptance:** PDF import works, manual entries link to orders, duplicates can be merged, dropdowns work

### Phase 2: Enhancements (P1/P2)

**Task 2.1: Distribution Log Dropdown Details**
- [ ] Create route: `GET /admin/distribution-log/entry-details/<entry_id>` (JSON)
- [ ] Update `app/eqms/templates/admin/distribution_log/list.html`
- [ ] Add dropdown to each distribution row
- [ ] Show: Associated order, order lines, mismatch flags
- [ ] Test: Expand dropdown → Verify order context, mismatch warnings

**Task 2.2: Customer Database Dropdown Details**
- [ ] Create route: `GET /admin/customers/<customer_id>/summary` (JSON)
- [ ] Update `app/eqms/templates/admin/customers/list.html`
- [ ] Add accordion/dropdown to each customer row (match legacy pattern)
- [ ] Show: Order history summary, recent SKUs/lots, quick actions
- [ ] Test: Expand dropdown → Verify order history, links work

**Task 2.3: Sales Orders List View**
- [ ] Create route: `GET /admin/sales-orders` (list with filters)
- [ ] Create template: `app/eqms/templates/admin/sales_orders/list.html`
- [ ] Filters: Date range, customer, source, status
- [ ] Columns: Order #, Order Date, Ship Date, Customer, Total Units, Status
- [ ] Test: List loads, filters work, links to order detail

**Task 2.4: Sales Order Detail View**
- [ ] Create route: `GET /admin/sales-orders/<id>` (order detail)
- [ ] Create template: `app/eqms/templates/admin/sales_orders/detail.html`
- [ ] Show: Order metadata, order lines table, linked distributions table
- [ ] Test: Order detail loads, shows lines and distributions

**Acceptance:** All dropdowns work, sales orders are viewable, system is cohesive

---

## Risks & Edge Cases

### Risk 1: PDF Parsing Failures

**Risk:** PDF format may vary, parsing may fail for some pages/orders

**Mitigation:**
- Use robust PDF library (`pdfplumber` recommended for table extraction)
- Validate extracted data (SKU format, quantity > 0, date format)
- Show parse errors in import results page
- Allow manual entry fallback for failed rows

**Edge Cases:**
- Multi-page orders (span multiple PDF pages)
- Missing columns (handle gracefully, use defaults)
- Malformed dates (try multiple formats, log errors)

### Risk 2: Customer Merge Data Loss

**Risk:** Merging customers may lose data if not careful

**Mitigation:**
- Always merge into "master" customer (most orders, most complete data)
- Merge fields intelligently (keep non-null values from both)
- Record merge in audit log (who merged, when, which customers)
- Test merge on duplicate data first

**Edge Cases:**
- Both customers have different addresses (keep master, log duplicate address in notes)
- Both customers have different rep assignments (keep master rep, log in notes)

### Risk 3: Sales Order → Distribution Mismatches

**Risk:** Distribution quantities may not match order line quantities (real-world: partial shipments, returns)

**Mitigation:**
- Allow distributions to exceed order quantities (flag as warning, not error)
- Track fulfillment status per order line (fulfilled_qty vs ordered_qty)
- Show mismatch flags in UI (dropdown details)

**Edge Cases:**
- Order has 10 units, but 12 units distributed (over-shipment)
- Order has lot "SLQ-12345", but distribution has lot "SLQ-12346" (lot mismatch)
- Order line has no lot_number, but distribution has lot (OK, lot assigned later)

### Risk 4: Performance with Large Datasets

**Risk:** Dashboard aggregations may slow with 1000s of orders

**Mitigation:**
- Use SQL aggregates (GROUP BY) instead of Python loops
- Add indexes on `sales_orders.order_date`, `sales_orders.customer_id`
- Limit dropdown detail queries (recent 10 orders, recent 20 distributions)
- Consider caching dashboard aggregates (P2, not P0)

**Edge Cases:**
- Customer with 1000+ orders (limit recent orders to 10 in dropdown)
- Dashboard with 5 years of data (use date filter, default to last year)

### Risk 5: Legacy Data Migration

**Risk:** Existing `distribution_log_entries` have no `sales_order_id`

**Mitigation:**
- Make `sales_order_id` nullable (allow NULL for legacy entries)
- Create migration script to backfill: Group distributions by `order_number` + `ship_date`, create sales orders
- Run backfill script after new tables created
- Mark legacy entries: `source='legacy_backfill'` or keep original source

**Edge Cases:**
- Distributions with same order_number but different customers (create separate orders)
- Distributions with missing order_number (create "UNKNOWN-{id}" order_number)

### Risk 6: PDF Library Dependencies

**Risk:** `pdfplumber` or `tabula-py` may have compatibility issues

**Mitigation:**
- Pin version in `requirements.txt`
- Test PDF parsing on sample pages first
- Document supported PDF formats
- Provide manual entry fallback

**Edge Cases:**
- PDF is scanned image (not text) → Use OCR (P2, not P0)
- PDF has complex table layouts → May need custom parsing logic

---

## Non-Negotiable Rules

1. **Sales Orders = Source of Truth:**
   - Customer identity comes from `sales_orders.customer_id`
   - Order assignment comes from `sales_orders.order_number`
   - Distributions link to orders via `sales_order_id` FK

2. **No Breaking Changes:**
   - Existing `distribution_log_entries` remain valid (NULL `sales_order_id` allowed)
   - Existing routes continue to work
   - Incremental migration: New data uses sales orders, legacy data remains functional

3. **Lean Code Only:**
   - Use legacy code as behavioral reference, not code to copy
   - Avoid porting monolithic functions
   - Use existing patterns (SQLAlchemy ORM, service layer, storage abstraction)

4. **2025 + 2026 + Future Years:**
   - All date filters support year selection (2025, 2026, future)
   - Logic is consistent across years (no hardcoded year checks)
   - Sales Dashboard default `start_date = 2025-01-01` (configurable)

5. **Customer Deduplication:**
   - Always use `find_or_create_customer()` (never direct `Customer()` creation)
   - Multi-tier matching (exact → strong → weak)
   - Merge candidates for manual review (weak matches)

6. **Dropdown Performance:**
   - Lazy-load details (only fetch when opened)
   - Limit result sets (recent 10 orders, recent 20 distributions)
   - No heavy queries on page load

---

## Files to Create/Modify

### New Files

**Models:**
- `app/eqms/modules/rep_traceability/models.py` (add `SalesOrder`, `SalesOrderLine` classes)

**Migrations:**
- `migrations/versions/XXXXX_add_sales_orders_tables.py`
- `migrations/versions/XXXXX_add_sales_order_id_to_distributions.py`
- `migrations/versions/XXXXX_add_customer_merge_candidates_table.py` (optional, P1)

**Parsers:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (new file)

**Routes:**
- `app/eqms/modules/rep_traceability/admin.py` (add sales orders routes)
- `app/eqms/modules/customer_profiles/admin.py` (add merge routes)

**Templates:**
- `app/eqms/templates/admin/sales_orders/list.html` (new)
- `app/eqms/templates/admin/sales_orders/detail.html` (new)

**Scripts:**
- `scripts/merge_duplicate_customers.py` (new)

### Modified Files

**Models:**
- `app/eqms/modules/rep_traceability/models.py` (add `sales_order_id` to `DistributionLogEntry`)

**Services:**
- `app/eqms/modules/rep_traceability/service.py` (add sales order functions)
- `app/eqms/modules/customer_profiles/service.py` (enhance deduplication)
- `app/eqms/modules/customer_profiles/utils.py` (add `normalize_facility_name()`)
- `app/eqms/modules/shipstation_sync/service.py` (create sales orders first)

**Routes:**
- `app/eqms/modules/rep_traceability/admin.py` (update distribution routes, add sales orders routes, add dropdown detail routes)
- `app/eqms/modules/customer_profiles/admin.py` (add merge routes, add summary route)

**Templates:**
- `app/eqms/templates/admin/sales_dashboard/index.html` (add dropdowns)
- `app/eqms/templates/admin/distribution_log/list.html` (add dropdowns)
- `app/eqms/templates/admin/distribution_log/edit.html` (add sales order selection)
- `app/eqms/templates/admin/customers/list.html` (add dropdowns/accordions)

**Dependencies:**
- `requirements.txt` (add `pdfplumber` or `tabula-py`)

---

## Implementation Checklist Summary

**P0 (Must Have):**
1. Create sales orders data model + migration
2. Enhance customer deduplication (multi-tier matching)
3. Update ShipStation sync to create sales orders
4. Implement 2025 PDF ingestion
5. Update manual distribution entry to link to sales orders
6. Add Sales Dashboard dropdown details
7. Verify ShipStation sync completeness (2025 data)

**P1 (Important):**
8. Customer merge script + UI
9. Distribution Log dropdown details
10. Customer Database dropdown details
11. Sales Orders list/detail views

**P2 (Nice to Have):**
12. Customer merge candidates table + review UI
13. Dashboard aggregation caching
14. Advanced PDF parsing (OCR for scanned PDFs)

---

## Definition of Done

**System is "done" when:**

1. ✅ Sales Dashboard matches legacy functionality (all metrics, tables, actions)
2. ✅ Customer duplicates identified and merged (or merge candidates created)
3. ✅ No new duplicates created (enhanced deduplication prevents them)
4. ✅ Sales orders exist as source of truth (all new distributions link to orders)
5. ✅ 2025 Sales Orders PDF can be imported (row counts match, dates correct)
6. ✅ ShipStation sync creates sales orders and pulls from 2025-01-01
7. ✅ Dropdown detail menus work on Sales Dashboard, Distribution Log, Customer DB
8. ✅ All acceptance criteria pass (AC1-AC34)

**Begin with Phase 0 (Foundation) - create sales orders data model and enhance deduplication first.**
