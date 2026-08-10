# Developer Prompt: ShipStation as Source of Truth for SKUs, Lots, and Quantities

**Date:** 2026-01-27  
**Priority:** P0 (Critical - Data Integrity)  
**Scope:** Fix sales dashboard aggregation, ensure ShipStation is source-of-truth for SKUs/Lots/Qtys, handle blanket sales orders correctly, verify multiple SKUs per order are handled. **NO new features - only correctness fixes.**

---

## Executive Summary

This prompt addresses a **critical data integrity issue**: the sales dashboard is showing incorrect totals because the system is not properly handling multiple SKUs per order and is potentially using Sales Order data instead of ShipStation distribution data for aggregations.

**Key Problem:** Sales Order 0000125 is a "blanket sales order" that applies to multiple distributions. The system must:
1. **ShipStation is source-of-truth for SKUs, Lots, and Quantities** - Never overwrite ShipStation data with Sales Order data
2. **Sales Orders are source-of-truth for Customer Information ONLY** - Customer name, address, contact info
3. **Multiple SKUs per order must be handled correctly** - One distribution entry per SKU/Lot combination
4. **Sales dashboard must aggregate from ShipStation distributions** - Not from Sales Orders or Sales Order Lines

**Critical Rules:**
- **SKUs, Lots, Qtys come from ShipStation distributions** (or manual entry/CSV)
- **Customer information comes from Sales Orders** (after PDF import)
- **One Sales Order can match to multiple distributions** (blanket order scenario)
- **Sales dashboard aggregates from `DistributionLogEntry` records, NOT from Sales Orders**

---

## Part 1: Problem Analysis

### Issue 1: Sales Dashboard Showing Incorrect Totals

**Problem:** Sales dashboard totals are incorrect because:
1. System may be reading only one SKU per distribution when there can be several
2. System may be aggregating from Sales Orders instead of ShipStation distributions
3. Blanket sales orders (like 0000125) are not handled correctly

**Evidence:**
- Sales Order 0000125 applies to several different distributions
- Dashboard shows incorrect SKU breakdown and total units
- User reports "system only seems to be reading in one SKU/distribution when there can be several different SKUs"

**Root Cause Analysis:**

**A. ShipStation Sync Creates Multiple Distributions (CORRECT):**
Looking at `shipstation_sync/service.py:451-491`, ShipStation sync DOES create one distribution entry per SKU:
```python
for sku, units in sku_units.items():
    # Creates one DistributionLogEntry per SKU
    e = create_distribution_entry(s, payload, ...)
```

This is CORRECT. One order with multiple SKUs should create multiple distribution entries.

**B. Sales Dashboard Aggregation (NEEDS VERIFICATION):**
Looking at `rep_traceability/service.py:664-667`, the dashboard aggregates from distribution entries:
```python
sku_totals: dict[str, int] = {}
for e in window_entries:
    sku_totals[e.sku] = sku_totals.get(e.sku, 0) + int(e.quantity or 0)
```

This SHOULD work correctly IF:
- Multiple distribution entries exist per order (one per SKU)
- All entries are matched (`sales_order_id IS NOT NULL`)
- No data is being overwritten during matching

**C. Potential Issues:**
1. **Matching logic may overwrite ShipStation data** - When distributions are matched to Sales Orders, SKU/Lot/Qty might be overwritten
2. **Sales Order Lines might be used instead of distributions** - Dashboard might be reading from `SalesOrderLine` instead of `DistributionLogEntry`
3. **Blanket orders not handled** - One Sales Order matching multiple distributions might cause aggregation issues

---

### Issue 2: ShipStation Data Must Never Be Overwritten

**Problem:** When a distribution is matched to a Sales Order, the system must NOT overwrite:
- SKU (from ShipStation)
- Lot Number (from ShipStation, with LotLog corrections)
- Quantity (from ShipStation)

**Current Matching Logic:**
Looking at `rep_traceability/admin.py:1861-1872`, when PDF import creates a Sales Order, it matches existing distributions:
```python
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
    udist.customer_id = customer.id  # Link via SO's customer (canonical)
```

**This is CORRECT** - it only updates `sales_order_id` and `customer_id`, not SKU/Lot/Qty.

**But we need to verify:**
- No other code path overwrites ShipStation SKU/Lot/Qty
- Customer name is updated from Sales Order (canonical), but SKU/Lot/Qty remain from ShipStation

---

### Issue 3: Blanket Sales Orders (e.g., 0000125)

**Problem:** One Sales Order (0000125) applies to multiple distributions. The system must:
1. Allow one Sales Order to match multiple distributions
2. Aggregate correctly across all matched distributions
3. Never use Sales Order Line data to overwrite distribution data

**Current Behavior:**
- ShipStation sync creates multiple distributions (one per SKU) for order 0000125
- PDF import creates one Sales Order 0000125
- Matching links all distributions to the same Sales Order
- **This should work correctly**, but we need to verify aggregation doesn't double-count or use wrong source

---

## Part 2: Implementation Plan

### Task 1: Verify ShipStation Sync Creates Multiple Distributions Per Order (P0)

**Objective:** Ensure ShipStation sync creates one `DistributionLogEntry` per SKU/Lot combination.

**File:** `app/eqms/modules/shipstation_sync/service.py`

**Current Code (lines 451-491):**
```python
for sku, units in sku_units.items():
    # Creates one distribution per SKU
    e = create_distribution_entry(s, payload, ...)
```

**Verification Required:**
1. **Verify `sku_units` contains all SKUs** - Check that ShipStation order with multiple items creates multiple entries in `sku_units` dict
2. **Verify each SKU gets its own distribution** - Check that loop creates separate `DistributionLogEntry` for each SKU
3. **Verify lot numbers are per-SKU** - Check that `sku_lot_pairs.get(sku)` is used correctly

**Test Case:**
- ShipStation order with 3 SKUs (211810SPT x10, 211610SPT x5, 211410SPT x3)
- **Expected:** 3 distribution entries created
- **Verify:** All 3 entries have correct SKU, quantity, and lot number

**Acceptance Criteria:**
- [ ] ShipStation order with N SKUs creates N distribution entries
- [ ] Each distribution entry has correct SKU, quantity, lot number
- [ ] All distributions share same order_number
- [ ] All distributions can be matched to same Sales Order (blanket order scenario)

---

### Task 2: Verify Matching Logic Never Overwrites ShipStation Data (P0)

**Objective:** Ensure when distributions are matched to Sales Orders, SKU/Lot/Qty from ShipStation are NEVER overwritten.

**Files to Review:**
- `app/eqms/modules/rep_traceability/admin.py:1861-1872` (PDF import matching)
- `app/eqms/modules/rep_traceability/service.py` (matching utility functions)
- `app/eqms/modules/rep_traceability/admin.py:507` (distribution upload PDF matching)

**Current Matching Code (PDF Import):**
```python
for udist in unmatched_dists:
    udist.sales_order_id = sales_order.id
    udist.customer_id = customer.id  # Link via SO's customer (canonical)
    # NOTE: SKU, lot_number, quantity are NOT updated - CORRECT
```

**Verification Required:**
1. **No code path overwrites SKU/Lot/Qty during matching** - Search for any code that updates these fields when `sales_order_id` is set
2. **Customer name is updated from Sales Order** - This is CORRECT (canonical customer name)
3. **Facility name is updated from Sales Order customer** - This is CORRECT (canonical facility name)

**Files to Check:**
```bash
# Search for code that might overwrite ShipStation data
grep -r "entry.sku\|entry.lot_number\|entry.quantity" app/eqms/modules/rep_traceability/
grep -r "distribution.*sku\|distribution.*lot\|distribution.*quantity" app/eqms/modules/rep_traceability/
```

**Acceptance Criteria:**
- [ ] Matching only updates: `sales_order_id`, `customer_id`, `facility_name` (from SO customer)
- [ ] Matching NEVER updates: `sku`, `lot_number`, `quantity`
- [ ] ShipStation distributions retain their original SKU/Lot/Qty after matching

---

### Task 3: Verify Sales Dashboard Aggregates from Distributions Only (P0)

**Objective:** Ensure sales dashboard reads from `DistributionLogEntry` records, NOT from Sales Orders or Sales Order Lines.

**File:** `app/eqms/modules/rep_traceability/service.py:594-811` (`compute_sales_dashboard`)

**Current Code Analysis:**

**SKU Breakdown (lines 664-667):**
```python
sku_totals: dict[str, int] = {}
for e in window_entries:  # window_entries = DistributionLogEntry records
    sku_totals[e.sku] = sku_totals.get(e.sku, 0) + int(e.quantity or 0)
```
**This is CORRECT** - aggregates from distribution entries.

**Total Units (lines 641-648):**
```python
total_units_window = sum(int(e.quantity or 0) for e in window_entries)
total_units_all_time = int(
    s.query(func.coalesce(func.sum(DistributionLogEntry.quantity), 0))
    .filter(DistributionLogEntry.sales_order_id.isnot(None))
    .scalar() or 0
)
```
**This is CORRECT** - aggregates from distribution entries.

**Order Count (line 640):**
```python
total_orders = len({e.order_number for e in window_entries if e.order_number})
```
**This is CORRECT** - counts distinct order numbers from distributions.

**Potential Issue:**
- If multiple distributions share the same order_number (blanket order), they should all be counted
- But `total_orders` counts distinct order_numbers, which is CORRECT (one order = one count, even if multiple distributions)

**Verification Required:**
1. **Verify `window_entries` contains all distributions** - Check that all matched distributions are included
2. **Verify no filtering by Sales Order** - Check that we're not accidentally filtering to one distribution per Sales Order
3. **Verify blanket orders are handled** - Sales Order 0000125 with 5 distributions should contribute 5 entries to aggregation

**Test Case:**
- Sales Order 0000125 matches 5 distributions (different SKUs/Lots)
- **Expected:** Dashboard shows all 5 distributions in totals
- **Verify:** SKU breakdown includes all SKUs, total units includes all quantities

**Acceptance Criteria:**
- [ ] Dashboard aggregates from `DistributionLogEntry` records only
- [ ] Dashboard does NOT read from `SalesOrder` or `SalesOrderLine` tables
- [ ] Blanket orders (one SO → multiple distributions) aggregate correctly
- [ ] Multiple SKUs per order are all included in totals

---

### Task 4: Add Diagnostic Queries to Verify Data Integrity (P0)

**Objective:** Add SQL queries to verify that ShipStation data is not being overwritten and that multiple SKUs per order are handled correctly.

**File:** `app/eqms/admin.py` (add to diagnostics endpoint)

**Queries to Add:**

1. **Verify ShipStation distributions have correct SKU/Lot/Qty:**
   ```sql
   -- Count distributions by source
   SELECT source, COUNT(*) as count 
   FROM distribution_log_entries 
   GROUP BY source;
   
   -- Verify ShipStation distributions have lot numbers (not UNKNOWN)
   SELECT COUNT(*) as unknown_lots
   FROM distribution_log_entries 
   WHERE source = 'shipstation' AND (lot_number = 'UNKNOWN' OR lot_number IS NULL);
   -- Expected: 0 (all ShipStation entries should have lot numbers)
   ```

2. **Verify multiple SKUs per order:**
   ```sql
   -- Find orders with multiple SKUs
   SELECT order_number, COUNT(DISTINCT sku) as sku_count, COUNT(*) as dist_count
   FROM distribution_log_entries
   WHERE source = 'shipstation' AND sales_order_id IS NOT NULL
   GROUP BY order_number
   HAVING COUNT(DISTINCT sku) > 1
   ORDER BY sku_count DESC
   LIMIT 10;
   -- Should show orders like 0000125 with multiple SKUs
   ```

3. **Verify blanket orders (one SO → multiple distributions):**
   ```sql
   -- Find Sales Orders with multiple distributions
   SELECT so.order_number, COUNT(DISTINCT d.id) as dist_count, COUNT(DISTINCT d.sku) as sku_count
   FROM sales_orders so
   JOIN distribution_log_entries d ON d.sales_order_id = so.id
   GROUP BY so.id, so.order_number
   HAVING COUNT(DISTINCT d.id) > 1
   ORDER BY dist_count DESC
   LIMIT 10;
   -- Should show Sales Order 0000125 with multiple distributions
   ```

4. **Verify no overwriting of ShipStation data:**
   ```sql
   -- Compare ShipStation distributions to Sales Order Lines
   -- ShipStation distributions should have their own SKU/Lot/Qty, not from SO lines
   SELECT 
       d.order_number,
       d.sku as dist_sku,
       d.lot_number as dist_lot,
       d.quantity as dist_qty,
       sol.sku as so_line_sku,
       sol.lot_number as so_line_lot,
       sol.quantity as so_line_qty
   FROM distribution_log_entries d
   JOIN sales_orders so ON d.sales_order_id = so.id
   LEFT JOIN sales_order_lines sol ON sol.sales_order_id = so.id AND sol.sku = d.sku
   WHERE d.source = 'shipstation'
   LIMIT 20;
   -- dist_sku/lot/qty should be from ShipStation, may differ from so_line_sku/lot/qty
   ```

**Implementation:**
```python
# In admin.py diagnostics endpoint
@bp.get("/diagnostics")
@require_permission("admin.view")
def diagnostics():
    # ... existing code ...
    
    # Add ShipStation data integrity checks
    diag["shipstation_integrity"] = {}
    
    # Count distributions by source
    source_counts = (
        s.query(DistributionLogEntry.source, func.count(DistributionLogEntry.id))
        .group_by(DistributionLogEntry.source)
        .all()
    )
    diag["shipstation_integrity"]["distributions_by_source"] = {src: cnt for src, cnt in source_counts}
    
    # Count ShipStation distributions with UNKNOWN lots
    unknown_lots = (
        s.query(func.count(DistributionLogEntry.id))
        .filter(
            DistributionLogEntry.source == "shipstation",
            or_(
                DistributionLogEntry.lot_number == "UNKNOWN",
                DistributionLogEntry.lot_number.is_(None)
            )
        )
        .scalar() or 0
    )
    diag["shipstation_integrity"]["shipstation_unknown_lots"] = unknown_lots
    
    # Find orders with multiple SKUs
    multi_sku_orders = (
        s.query(
            DistributionLogEntry.order_number,
            func.count(func.distinct(DistributionLogEntry.sku)).label("sku_count"),
            func.count(DistributionLogEntry.id).label("dist_count")
        )
        .filter(
            DistributionLogEntry.source == "shipstation",
            DistributionLogEntry.sales_order_id.isnot(None)
        )
        .group_by(DistributionLogEntry.order_number)
        .having(func.count(func.distinct(DistributionLogEntry.sku)) > 1)
        .order_by(func.count(func.distinct(DistributionLogEntry.sku)).desc())
        .limit(10)
        .all()
    )
    diag["shipstation_integrity"]["multi_sku_orders"] = [
        {"order_number": o, "sku_count": s, "dist_count": d}
        for o, s, d in multi_sku_orders
    ]
    
    # Find Sales Orders with multiple distributions (blanket orders)
    blanket_orders = (
        s.query(
            SalesOrder.order_number,
            func.count(func.distinct(DistributionLogEntry.id)).label("dist_count"),
            func.count(func.distinct(DistributionLogEntry.sku)).label("sku_count")
        )
        .join(DistributionLogEntry, DistributionLogEntry.sales_order_id == SalesOrder.id)
        .group_by(SalesOrder.id, SalesOrder.order_number)
        .having(func.count(func.distinct(DistributionLogEntry.id)) > 1)
        .order_by(func.count(func.distinct(DistributionLogEntry.id)).desc())
        .limit(10)
        .all()
    )
    diag["shipstation_integrity"]["blanket_orders"] = [
        {"order_number": o, "dist_count": d, "sku_count": s}
        for o, d, s in blanket_orders
    ]
    
    return render_template("admin/diagnostics.html", diag=diag)
```

**Acceptance Criteria:**
- [ ] Diagnostics endpoint shows distribution counts by source
- [ ] Diagnostics shows ShipStation distributions with UNKNOWN lots (should be 0)
- [ ] Diagnostics shows orders with multiple SKUs
- [ ] Diagnostics shows blanket orders (one SO → multiple distributions)

---

### Task 5: Verify Sales Dashboard Query Logic (P0)

**Objective:** Ensure sales dashboard query includes ALL matched distributions, even for blanket orders.

**File:** `app/eqms/modules/rep_traceability/service.py:594-811`

**Current Query (lines 632-638):**
```python
q = s.query(DistributionLogEntry).filter(
    DistributionLogEntry.sales_order_id.isnot(None)  # Only matched
)
if start_date:
    q = q.filter(DistributionLogEntry.ship_date >= start_date)
window_entries = q.order_by(DistributionLogEntry.ship_date.asc(), DistributionLogEntry.id.asc()).all()
```

**This is CORRECT** - queries all matched distributions.

**Potential Issue:**
- If there's any GROUP BY or DISTINCT that collapses multiple distributions per order, totals would be wrong
- Need to verify no such grouping exists

**Verification Required:**
1. **Verify no GROUP BY on order_number** - Check that we're not grouping distributions by order
2. **Verify all distributions are included** - For Sales Order 0000125 with 5 distributions, all 5 should be in `window_entries`
3. **Verify SKU breakdown includes all SKUs** - Each SKU should be counted separately

**Test Query:**
```python
# In compute_sales_dashboard, add debug logging:
logger.info(f"Sales dashboard: {len(window_entries)} distributions in window")
logger.info(f"Sales dashboard: {len(set(e.order_number for e in window_entries))} distinct orders")
logger.info(f"Sales dashboard: {len(set(e.sku for e in window_entries))} distinct SKUs")

# For Sales Order 0000125 specifically:
so_0000125_dists = [e for e in window_entries if e.order_number == "0000125" or e.order_number == "SO 0000125"]
logger.info(f"Sales dashboard: SO 0000125 has {len(so_0000125_dists)} distributions")
for d in so_0000125_dists:
    logger.info(f"  - SKU: {d.sku}, Qty: {d.quantity}, Lot: {d.lot_number}")
```

**Acceptance Criteria:**
- [ ] Sales dashboard query includes ALL matched distributions
- [ ] No GROUP BY that collapses multiple distributions per order
- [ ] Blanket orders contribute all their distributions to totals
- [ ] SKU breakdown includes all SKUs from all distributions

---

### Task 6: Add Explicit Validation That ShipStation Data Is Never Overwritten (P0)

**Objective:** Add code-level validation to prevent any code path from overwriting ShipStation SKU/Lot/Qty data.

**File:** `app/eqms/modules/rep_traceability/service.py` (add validation function)

**Implementation:**
```python
def validate_shipstation_data_not_overwritten(
    entry: DistributionLogEntry,
    updates: dict[str, Any],
) -> list[str]:
    """
    Validate that ShipStation distribution data (SKU, lot_number, quantity) is not being overwritten.
    Returns list of warnings if ShipStation data would be changed.
    """
    warnings = []
    
    if entry.source != "shipstation":
        return warnings  # Only validate ShipStation entries
    
    if "sku" in updates and updates["sku"] != entry.sku:
        warnings.append(f"WARNING: Attempting to overwrite ShipStation SKU {entry.sku} with {updates['sku']}")
    
    if "lot_number" in updates and updates["lot_number"] != entry.lot_number:
        # Allow lot number updates if they're corrections (e.g., from LotLog)
        # But log a warning
        warnings.append(f"WARNING: Attempting to overwrite ShipStation lot {entry.lot_number} with {updates['lot_number']}")
    
    if "quantity" in updates and updates["quantity"] != entry.quantity:
        warnings.append(f"WARNING: Attempting to overwrite ShipStation quantity {entry.quantity} with {updates['quantity']}")
    
    return warnings

# In update_distribution_entry():
def update_distribution_entry(s, entry: DistributionLogEntry, payload: dict[str, Any], *, user: User, reason: str) -> DistributionLogEntry:
    # ... existing code ...
    
    # Validate ShipStation data is not overwritten
    if entry.source == "shipstation":
        warnings = validate_shipstation_data_not_overwritten(entry, payload)
        if warnings:
            logger.warning(f"Distribution {entry.id} update warnings: {'; '.join(warnings)}")
            # Don't prevent update, but log warning
            # Admin can override if needed, but should be aware
    
    # ... rest of update logic ...
```

**Acceptance Criteria:**
- [ ] Validation function detects attempts to overwrite ShipStation data
- [ ] Warnings are logged (not errors - admin can override if needed)
- [ ] No silent overwrites of ShipStation SKU/Lot/Qty

---

## Part 3: Testing Plan

### Test 1: Multiple SKUs Per Order from ShipStation

**Steps:**
1. Reset data
2. Run ShipStation sync for an order with multiple SKUs (e.g., 3 SKUs)
3. Check Distribution Log

**Expected:**
- 3 distribution entries created (one per SKU)
- All entries have same order_number
- All entries have correct SKU, quantity, lot number from ShipStation
- All entries have `source="shipstation"`

**Verification:**
```sql
SELECT order_number, sku, quantity, lot_number, source
FROM distribution_log_entries
WHERE order_number = 'SO 0000125'  -- or test order number
ORDER BY sku;
-- Should show multiple rows, one per SKU
```

---

### Test 2: Blanket Sales Order Matching

**Steps:**
1. Run ShipStation sync (creates multiple distributions for order 0000125)
2. Import Sales Order PDF for 0000125 (creates one Sales Order)
3. Check Distribution Log

**Expected:**
- Multiple distributions exist (one per SKU)
- All distributions have `sales_order_id` set to same Sales Order
- All distributions retain their ShipStation SKU/Lot/Qty
- Customer name in distributions matches Sales Order customer (canonical)

**Verification:**
```sql
SELECT 
    d.order_number,
    d.sku,
    d.quantity,
    d.lot_number,
    d.source,
    d.sales_order_id,
    so.order_number as so_order_number,
    c.facility_name as so_customer_name
FROM distribution_log_entries d
JOIN sales_orders so ON d.sales_order_id = so.id
JOIN customers c ON so.customer_id = c.id
WHERE d.order_number LIKE '%0000125%'
ORDER BY d.sku;
-- Should show multiple distributions, all linked to same SO, all with ShipStation SKU/Lot/Qty
```

---

### Test 3: Sales Dashboard Aggregation

**Steps:**
1. Ensure Sales Order 0000125 has multiple matched distributions
2. Go to Sales Dashboard
3. Check totals

**Expected:**
- Total units includes all quantities from all distributions
- SKU breakdown shows all SKUs with correct totals
- Order count shows 1 (one order, even though multiple distributions)

**Verification:**
```sql
-- Manual calculation for comparison
SELECT 
    COUNT(DISTINCT order_number) as total_orders,
    SUM(quantity) as total_units,
    sku,
    SUM(quantity) as sku_units
FROM distribution_log_entries
WHERE sales_order_id IS NOT NULL
  AND ship_date >= '2025-01-01'
GROUP BY sku;
-- Compare to dashboard totals
```

---

### Test 4: Verify No Data Overwriting

**Steps:**
1. Create ShipStation distribution with SKU=211810SPT, Qty=10, Lot=SLQ-05012025
2. Match to Sales Order (via PDF import)
3. Check distribution after matching

**Expected:**
- Distribution SKU still = 211810SPT (from ShipStation)
- Distribution quantity still = 10 (from ShipStation)
- Distribution lot_number still = SLQ-05012025 (from ShipStation)
- Distribution customer_id and facility_name updated from Sales Order (canonical)

**Verification:**
```sql
-- Before matching
SELECT sku, quantity, lot_number, customer_id, facility_name
FROM distribution_log_entries
WHERE id = <distribution_id>;

-- After matching
SELECT sku, quantity, lot_number, customer_id, facility_name, sales_order_id
FROM distribution_log_entries
WHERE id = <distribution_id>;
-- SKU, quantity, lot_number should be unchanged
-- customer_id, facility_name, sales_order_id should be updated
```

---

## Part 4: Files to Change Summary

### Backend Files

1. **`app/eqms/modules/shipstation_sync/service.py`**
   - Verify multiple distributions are created per order (one per SKU)
   - Add logging to show how many distributions created per order

2. **`app/eqms/modules/rep_traceability/service.py`**
   - Verify `compute_sales_dashboard()` aggregates from distributions only
   - Add validation function to prevent overwriting ShipStation data
   - Add debug logging for blanket orders

3. **`app/eqms/modules/rep_traceability/admin.py`**
   - Verify matching logic never overwrites SKU/Lot/Qty
   - Add logging when distributions are matched

4. **`app/eqms/admin.py`**
   - Add ShipStation data integrity diagnostics
   - Add queries to verify multiple SKUs per order
   - Add queries to verify blanket orders

### No Frontend Changes Required

- Dashboard template should already display aggregated data correctly
- No UI changes needed (this is a data integrity fix)

---

## Part 5: Critical Rules (MUST ENFORCE)

### Rule 1: ShipStation is Source-of-Truth for SKUs, Lots, Quantities

**Enforcement:**
- ShipStation distributions MUST retain their original SKU, lot_number, quantity
- Matching to Sales Orders MUST NOT overwrite these fields
- Sales Order Lines are for reference only, NOT used for aggregations

### Rule 2: Sales Orders are Source-of-Truth for Customer Information ONLY

**Enforcement:**
- Sales Orders provide: customer name, address, contact info
- Sales Orders do NOT provide: SKU, lot number, quantity
- When distribution is matched to Sales Order, update customer_id and facility_name only

### Rule 3: Multiple SKUs Per Order Must Create Multiple Distributions

**Enforcement:**
- ShipStation order with N SKUs creates N distribution entries
- Each distribution entry has one SKU, one quantity, one lot number
- All distributions share same order_number
- All distributions can match to same Sales Order (blanket order)

### Rule 4: Sales Dashboard Aggregates from Distributions Only

**Enforcement:**
- Dashboard reads from `DistributionLogEntry` table only
- Dashboard does NOT read from `SalesOrder` or `SalesOrderLine` tables
- All matched distributions are included in aggregations
- Blanket orders contribute all their distributions to totals

---

## Part 6: Definition of Done

**For Each Task:**
- [ ] Code changes implemented
- [ ] Manual browser verification completed
- [ ] SQL verification queries pass
- [ ] No regressions (existing functionality works)

**Overall Success Criteria:**
- ✅ ShipStation sync creates multiple distributions per order (one per SKU)
- ✅ Matching never overwrites ShipStation SKU/Lot/Qty data
- ✅ Sales dashboard aggregates from distributions only (not Sales Orders)
- ✅ Blanket orders (one SO → multiple distributions) aggregate correctly
- ✅ Multiple SKUs per order are all included in dashboard totals
- ✅ Diagnostics show data integrity metrics

---

## Part 7: SQL Verification Queries (For Ethan)

**After developer completes fixes, run these queries to verify:**

```sql
-- 1. Verify multiple SKUs per order
SELECT order_number, COUNT(DISTINCT sku) as sku_count, COUNT(*) as dist_count
FROM distribution_log_entries
WHERE source = 'shipstation' AND sales_order_id IS NOT NULL
GROUP BY order_number
HAVING COUNT(DISTINCT sku) > 1
ORDER BY sku_count DESC
LIMIT 10;
-- Should show orders like 0000125 with multiple SKUs

-- 2. Verify blanket orders
SELECT so.order_number, COUNT(DISTINCT d.id) as dist_count
FROM sales_orders so
JOIN distribution_log_entries d ON d.sales_order_id = so.id
GROUP BY so.id, so.order_number
HAVING COUNT(DISTINCT d.id) > 1
ORDER BY dist_count DESC
LIMIT 10;
-- Should show Sales Order 0000125 with multiple distributions

-- 3. Verify ShipStation data not overwritten
SELECT 
    d.order_number,
    d.sku,
    d.quantity,
    d.lot_number,
    d.source,
    sol.sku as so_line_sku,
    sol.quantity as so_line_qty
FROM distribution_log_entries d
JOIN sales_orders so ON d.sales_order_id = so.id
LEFT JOIN sales_order_lines sol ON sol.sales_order_id = so.id
WHERE d.source = 'shipstation'
  AND d.sales_order_id IS NOT NULL
LIMIT 20;
-- dist_sku/quantity should be from ShipStation, may differ from so_line_sku/quantity

-- 4. Verify dashboard totals match SQL
SELECT 
    COUNT(DISTINCT order_number) as total_orders,
    SUM(quantity) as total_units,
    sku,
    SUM(quantity) as sku_units
FROM distribution_log_entries
WHERE sales_order_id IS NOT NULL
  AND ship_date >= '2025-01-01'
GROUP BY sku;
-- Compare to dashboard display
```

---

## Part 8: Reference Documents

**Planning Documents:**
- `docs/plans/DEVELOPER_PROMPT_CRITICAL_DATA_INTEGRITY_FIXES.md`
- `docs/plans/DEVELOPER_PROMPT_RELIABILITY_AND_USABILITY_ENHANCEMENTS.md`
- `docs/review/SYSTEM_DEBUG_SWEEP_2026_01_27.md`

**System Documentation:**
- `README.md` - Setup guide
- `docs/REP_SYSTEM_MIGRATION_MASTER.md` - Master spec

---

**End of Developer Prompt**
