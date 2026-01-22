# Developer Agent Prompt: Sales Parity Fixes & System Stabilization

**Reference Documents:**
- [docs/review/07_DEBUG_AUDIT_SYSTEM_AND_SALES_PARITY.md](docs/review/07_DEBUG_AUDIT_SYSTEM_AND_SALES_PARITY.md)
- [docs/planning/08_SALES_SYSTEM_LEGACY_PARITY_AND_UX_OVERHAUL.md](docs/planning/08_SALES_SYSTEM_LEGACY_PARITY_AND_UX_OVERHAUL.md)

---

## Task

Fix critical bugs and missing features identified in the sales parity audit. Prioritize blockers first (ShipStation 2025 sync, orphan distribution entries), then high-severity issues (missing features, incorrect filters).

---

## Critical Requirements

### Code Quality & Safety

1. **Follow Existing Patterns:**
   - Use `app/eqms/modules/rep_traceability/` and `app/eqms/modules/customer_profiles/` as reference patterns
   - Match validation patterns: use service layer functions (`validate_distribution_payload`, `find_or_create_customer`)
   - Match error handling: use `flash()` with `"danger"` category, redirect on validation failure

2. **No New Dependencies:**
   - Do NOT add Flask-WTF or other heavy dependencies unless explicitly required
   - Keep fixes minimal and surgical

3. **Test After Each Fix:**
   - Verify the fix works before moving to the next item
   - Use manual browser tests or SQL verification queries

---

## Priority 1: Blockers (Must Fix Immediately)

### Fix 1: ShipStation Sync Default to 2025-01-01 (BLOCKER)

**Severity:** Blocker  
**Issue:** ShipStation sync defaults to last 30 days instead of `2025-01-01`, causing missing 2025 orders

**File to Fix:**
- `app/eqms/modules/shipstation_sync/service.py` (line 81-93)

**Current (Broken) Code:**
```python
days = int((os.environ.get("SHIPSTATION_DEFAULT_DAYS") or "30").strip() or "30")
start_dt = now - timedelta(days=days)  # Only last 30 days!
```

**Fix:**
```python
# Default to 2025-01-01 if SHIPSTATION_SINCE_DATE is not set
since_date_str = os.environ.get("SHIPSTATION_SINCE_DATE", "").strip()
if since_date_str:
    try:
        since_date = datetime.fromisoformat(since_date_str).replace(tzinfo=timezone.utc)
        start_dt = since_date
    except Exception:
        # Fallback to 2025-01-01 if invalid format
        start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
else:
    # Default to 2025-01-01 (baseline requirement)
    start_dt = datetime(2025, 1, 1, tzinfo=timezone.utc)
```

**Also Update:**
- `app/eqms/modules/shipstation_sync/admin.py::shipstation_diag()` - Use same date logic (line ~70-80)

**Acceptance Test:**
- Run sync without `SHIPSTATION_SINCE_DATE` env var
- Verify sync pulls from `2025-01-01` onwards
- Check `/admin/shipstation` UI shows "Since Date: 2025-01-01" (not "last 30 days")
- Run SQL verification query:
  ```sql
  SELECT DATE_TRUNC('month', ship_date) AS month, COUNT(*) AS entries
  FROM distribution_log_entries
  WHERE source = 'shipstation' AND ship_date >= '2025-01-01'
  GROUP BY month ORDER BY month;
  ```
- Verify rows exist for 2025 months

---

### Fix 2: ShipStation Skip Rows When Customer Resolution Fails (BLOCKER)

**Severity:** Blocker  
**Issue:** ShipStation sync inserts distribution entries with `customer_id=NULL` when customer cannot be resolved, creating orphan rows

**File to Fix:**
- `app/eqms/modules/shipstation_sync/service.py` (line 45-64, ~200-250)

**Current (Broken) Code:**
```python
customer = _get_customer_from_ship_to(s, ship_to)
# ... later ...
# Creates entry even if customer is None
```

**Fix:**
```python
# In run_sync(), after getting customer:
customer = _get_customer_from_ship_to(s, ship_to)
if not customer:
    skipped += 1
    try:
        with s.begin_nested():
            s.add(
                ShipStationSkippedOrder(
                    order_id=order_id or None,
                    order_number=order_number or None,
                    reason="missing_customer",
                    details_json=json.dumps({
                        "shipTo": ship_to,
                        "facility": _safe_text(ship_to.get("company")) or _safe_text(ship_to.get("name")),
                    }, default=str)[:4000],
                )
            )
    except Exception:
        pass
    continue  # Skip this order, don't create distribution entry
```

**Acceptance Test:**
- Run sync with an order that has invalid/missing shipTo data
- Verify order is logged as `ShipStationSkippedOrder` with `reason="missing_customer"`
- Verify NO distribution entry is created (no orphan row)
- Query: `SELECT COUNT(*) FROM distribution_log_entries WHERE source='shipstation' AND customer_id IS NULL;` should be 0 (or not increase)

---

### Fix 3: Manual Distribution Log Require Customer Selection (BLOCKER)

**Severity:** Blocker  
**Issue:** Manual distribution entries can be created without `customer_id`, violating data cohesion

**Files to Fix:**
- `app/eqms/templates/admin/distribution_log/edit.html` (customer field)
- `app/eqms/modules/rep_traceability/admin.py::distribution_log_new_post()` (line 99)
- `app/eqms/modules/rep_traceability/service.py::validate_distribution_payload()` (add customer_id check)

**Current (Broken) Code:**
```html
<!-- Template says "Customer (optional, preferred)" -->
```

**Fix:**

1. **Template:** `app/eqms/templates/admin/distribution_log/edit.html`
   - Change customer field label to: "Customer *" (required)
   - Add `required` attribute to customer select
   - Update help text: "Customer selection is required for data cohesion"

2. **Route:** `app/eqms/modules/rep_traceability/admin.py::distribution_log_new_post()`
   ```python
   customer_id = normalize_text(payload.get("customer_id"))
   if not customer_id:
       flash("Customer selection is required.", "danger")
       return redirect(url_for("rep_traceability.distribution_log_new_get"))
   ```

3. **Service:** `app/eqms/modules/rep_traceability/service.py::validate_distribution_payload()`
   ```python
   # Add to validation errors list:
   if source == "manual" and not payload.get("customer_id"):
       errors.append(ValidationError("customer_id", "Customer is required for manual entries"))
   ```

**Also Fix Edit Route:**
- `app/eqms/modules/rep_traceability/admin.py::distribution_log_edit_post()` (line 175)
- Same validation: require `customer_id` for manual entries

**Acceptance Test:**
- Attempt to create manual distribution entry without selecting customer
- Verify form validation fails with flash message "Customer selection is required"
- Create entry with customer selected → succeeds
- Verify `customer_id` is set and facility/address fields are auto-filled from customer record

---

## Priority 2: High-Severity Issues

### Fix 4: Customer Database Year Filter Logic Incorrect

**Severity:** High  
**Issue:** Year filter uses `>=` comparison, so "Year=2025" shows customers with 2026 orders

**File to Fix:**
- `app/eqms/modules/customer_profiles/admin.py::customers_list()` (line 30-73)

**Current (Broken) Code:**
```python
# Year filter logic uses >=
if year_filter:
    year_int = int(year_filter)
    # ... compares first_order.year >= year_int or last_order.year >= year_int
```

**Fix:**
```python
# Option A: Filter by last order year (recommended for sales analysis)
if year_filter:
    year_int = int(year_filter)
    # Subquery: customers with last order in that year
    from sqlalchemy import func, case
    last_order_subq = (
        s.query(
            DistributionLogEntry.customer_id,
            func.max(DistributionLogEntry.ship_date).label('last_ship_date')
        )
        .filter(DistributionLogEntry.customer_id.isnot(None))
        .group_by(DistributionLogEntry.customer_id)
        .subquery()
    )
    query = query.join(
        last_order_subq,
        Customer.id == last_order_subq.c.customer_id
    ).filter(
        func.extract('year', last_order_subq.c.last_ship_date) == year_int
    )
```

**Alternative (Simpler):**
```python
# Option B: Filter by any order in that year (easier to implement)
if year_filter:
    year_int = int(year_filter)
    # Join to distribution entries and filter by year
    query = query.join(
        DistributionLogEntry,
        Customer.id == DistributionLogEntry.customer_id
    ).filter(
        func.extract('year', DistributionLogEntry.ship_date) == year_int
    ).distinct()
```

**Recommendation:** Use Option B (simpler, matches "has orders in that year" semantics)

**Acceptance Test:**
- Create customer with orders in 2025 and 2026
- Filter by Year=2025 → customer appears (has 2025 orders)
- Filter by Year=2026 → customer appears (has 2026 orders)
- Filter by Year=2024 → customer does NOT appear (no 2024 orders)

---

### Fix 5: Sales Dashboard Missing "Sales by Month" Table

**Severity:** High  
**Issue:** Baseline spec requires "Sales by Month" table, but it's not computed or rendered

**Files to Fix:**
- `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard()` (line 499)
- `app/eqms/templates/admin/sales_dashboard/index.html`

**Fix:**

1. **Service:** Add month aggregation to `compute_sales_dashboard()`
   ```python
   # Add after SKU breakdown computation (around line 553):
   from sqlalchemy import func
   
   # Sales by Month (SQL aggregation)
   month_agg = (
       s.query(
           func.date_trunc('month', DistributionLogEntry.ship_date).label('month'),
           func.count(func.distinct(DistributionLogEntry.order_number)).label('order_count'),
           func.sum(DistributionLogEntry.quantity).label('unit_count')
       )
       .filter(DistributionLogEntry.ship_date >= start_date) if start_date else s.query(...)
       .group_by(func.date_trunc('month', DistributionLogEntry.ship_date))
       .order_by(func.date_trunc('month', DistributionLogEntry.ship_date).desc())
       .all()
   )
   
   by_month = [
       {
           "month": row.month.strftime("%Y-%m") if hasattr(row.month, 'strftime') else str(row.month)[:7],
           "order_count": row.order_count,
           "unit_count": int(row.unit_count or 0)
       }
       for row in month_agg
   ]
   ```

2. **Return Value:** Add to return dict
   ```python
   return {
       "stats": {...},
       "sku_breakdown": sku_breakdown,
       "lot_tracking": lot_tracking,
       "top_customers": top_customers,
       "by_month": by_month,  # Add this
       ...
   }
   ```

3. **Template:** Add table to `app/eqms/templates/admin/sales_dashboard/index.html`
   ```html
   <div style="height: 14px;"></div>
   <div class="card">
     <h2 style="margin-top:0;">Sales by Month</h2>
     {% if by_month %}
       <table class="table">
         <thead><tr><th>Month</th><th>Orders</th><th>Units</th></tr></thead>
         <tbody>
           {% for row in by_month %}
             <tr>
               <td>{{ row.month|e }}</td>
               <td class="text-end">{{ row.order_count }}</td>
               <td class="text-end">{{ row.unit_count }}</td>
             </tr>
           {% endfor %}
         </tbody>
       </table>
     {% else %}
       <p class="muted">No monthly data in the selected window.</p>
     {% endif %}
   </div>
   ```

**Note:** For SQLite compatibility, use `func.strftime('%Y-%m', DistributionLogEntry.ship_date)` instead of `date_trunc`

**Acceptance Test:**
- Open Sales Dashboard with data spanning multiple months
- Verify "Sales by Month" table appears
- Verify month rows match SQL query:
  ```sql
  SELECT DATE_TRUNC('month', ship_date) AS month, COUNT(DISTINCT order_number), SUM(quantity)
  FROM distribution_log_entries WHERE ship_date >= '2025-01-01'
  GROUP BY month ORDER BY month DESC;
  ```

---

### Fix 6: ShipStation Limit Warnings in UI

**Severity:** High  
**Issue:** Sync can stop early due to `max_orders`/`max_pages` limits without clear warning

**Files to Fix:**
- `app/eqms/modules/shipstation_sync/service.py::run_sync()` (store `hit_limit` in run record)
- `app/eqms/modules/shipstation_sync/admin.py::shipstation_index()` (display warning)
- `app/eqms/templates/admin/shipstation/index.html` (show warning banner)

**Fix:**

1. **Service:** Update `ShipStationSyncRun` message when limit hit
   ```python
   # In run_sync(), when creating run record:
   run = ShipStationSyncRun(
       started_at=start,
       completed_at=_now_utc(),
       orders_seen=orders_seen,
       shipments_seen=shipments_seen,
       synced=synced,
       skipped=skipped,
       message=f"Sync completed. {'⚠️ LIMIT REACHED: Only synced {orders_seen} orders (max={max_orders}). Increase SHIPSTATION_MAX_ORDERS for full backfill.' if hit_limit else 'All available orders processed.'}"
   )
   ```

2. **Admin Route:** Check for limit warning
   ```python
   # In shipstation_index():
   last_run = s.query(ShipStationSyncRun).order_by(ShipStationSyncRun.started_at.desc()).first()
   limit_warning = last_run and "LIMIT REACHED" in (last_run.message or "")
   ```

3. **Template:** Display warning banner
   ```html
   {% if limit_warning %}
   <div class="card" style="border-left: 4px solid #f59e0b; background-color: #fef3c7;">
     <h3 style="margin-top:0; color: #92400e;">⚠️ Sync Limit Reached</h3>
     <p style="color: #78350f;">The last sync stopped early due to order/page limits. Increase SHIPSTATION_MAX_ORDERS and SHIPSTATION_MAX_PAGES for full backfill.</p>
   </div>
   {% endif %}
   ```

**Acceptance Test:**
- Run sync with `SHIPSTATION_MAX_ORDERS=10` (low limit)
- Verify sync completes but shows warning in UI
- Verify warning message explains the limit and how to increase it

---

## Priority 3: Medium-Severity Issues

### Fix 7: Customer Profile Add Distributions Tab

**Severity:** Medium  
**Issue:** Baseline spec requires separate "Distributions" tab, but only "Orders" tab exists

**Files to Fix:**
- `app/eqms/templates/admin/customers/detail.html`
- `app/eqms/modules/customer_profiles/admin.py::customer_detail()` (line 114)

**Fix:**

1. **Route:** Add distributions query
   ```python
   # In customer_detail():
   # Current: orders = s.query(DistributionLogEntry)...
   # Split into:
   orders = (
       s.query(DistributionLogEntry)
       .filter(DistributionLogEntry.customer_id == c.id)
       .filter(DistributionLogEntry.source.in_(['shipstation', 'manual', 'csv_import']))
       .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
       .limit(100)
       .all()
   )
   distributions = (
       s.query(DistributionLogEntry)
       .filter(DistributionLogEntry.customer_id == c.id)
       .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
       .limit(100)
       .all()
   )
   ```

2. **Template:** Add Distributions tab
   ```html
   <!-- Add to tab navigation -->
   <div class="tabs">
     <a href="#overview" class="tab">Overview</a>
     <a href="#orders" class="tab">Orders</a>
     <a href="#distributions" class="tab">Distributions</a>
     <a href="#notes" class="tab">Notes</a>
   </div>
   
   <!-- Add Distributions tab content -->
   <div id="distributions" class="tab-content">
     <h2>Distributions</h2>
     <p class="muted">All distribution entries (manual + CSV + ShipStation)</p>
     <table class="table">
       <!-- Same structure as Orders tab -->
     </table>
   </div>
   ```

**Acceptance Test:**
- Open customer profile
- Verify "Distributions" tab appears
- Verify Distributions tab shows ALL entries (manual + CSV + ShipStation)
- Verify Orders tab shows only ShipStation/manual/CSV entries (as before)

---

### Fix 8: Customer Profile Orders Grouped by Order Number

**Severity:** Medium  
**Issue:** Orders tab shows line-level entries (one row per SKU), should group by order number

**Files to Fix:**
- `app/eqms/modules/customer_profiles/admin.py::customer_detail()` (line 114)
- `app/eqms/templates/admin/customers/detail.html`

**Fix:**

1. **Route:** Group entries by order_number
   ```python
   # In customer_detail(), replace orders query with grouped data:
   from collections import defaultdict
   
   all_entries = (
       s.query(DistributionLogEntry)
       .filter(DistributionLogEntry.customer_id == c.id)
       .filter(DistributionLogEntry.source.in_(['shipstation', 'manual', 'csv_import']))
       .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.order_number.asc())
       .all()
   )
   
   # Group by (order_number, ship_date)
   orders_grouped = defaultdict(lambda: {"ship_date": None, "order_number": None, "source": None, "items": [], "total_qty": 0})
   for e in all_entries:
       key = (e.order_number or f"entry-{e.id}", e.ship_date)
       orders_grouped[key]["ship_date"] = e.ship_date
       orders_grouped[key]["order_number"] = e.order_number
       orders_grouped[key]["source"] = e.source
       orders_grouped[key]["items"].append({
           "sku": e.sku,
           "lot": e.lot_number,
           "quantity": e.quantity
       })
       orders_grouped[key]["total_qty"] += e.quantity
   
   orders = list(orders_grouped.values())
   ```

2. **Template:** Render grouped orders
   ```html
   {% for order in orders %}
     <tr>
       <td>{{ order.ship_date }}</td>
       <td><code>{{ order.order_number|e }}</code> <span class="badge">{{ order.source|e }}</span></td>
       <td>
         <ul class="list-unstyled">
           {% for item in order.items %}
             <li>{{ item.sku }} × {{ item.quantity }} (Lot: {{ item.lot }})</li>
           {% endfor %}
         </ul>
       </td>
       <td><strong>{{ order.total_qty }}</strong></td>
     </tr>
   {% endfor %}
   ```

**Acceptance Test:**
- Create customer with multi-item order (same order_number, multiple SKUs)
- Open customer profile Orders tab
- Verify order appears as ONE row with items listed
- Verify total quantity is sum of all items

---

### Fix 9: ShipStation Diagnostics Endpoint Disable in Production

**Severity:** Medium/High  
**Issue:** Diagnostics endpoint exposes sensitive data (internal notes, order IDs) to any admin

**File to Fix:**
- `app/eqms/modules/shipstation_sync/admin.py::shipstation_diag()` (line ~70)

**Fix:**
```python
@bp.get("/shipstation/diag")
@require_permission("shipstation.view")
def shipstation_diag():
    # Disable in production unless explicitly enabled
    if current_app.config.get("ENV") in ("prod", "production"):
        diag_enabled = os.environ.get("SHIPSTATION_DIAG_ENABLED", "").strip() == "1"
        if not diag_enabled:
            from flask import abort
            abort(404)  # Hide endpoint in production
    
    # ... rest of diagnostic code
```

**Acceptance Test:**
- Set `ENV=production` in config
- Attempt to access `/admin/shipstation/diag`
- Verify 404 (endpoint hidden)
- Set `SHIPSTATION_DIAG_ENABLED=1` in env
- Verify endpoint accessible

---

### Fix 10: Quarantine Legacy Prototypes

**Severity:** Medium (maintenance risk)  
**Issue:** Legacy files contain unsafe patterns (psycopg2, SMTP, raw SQL) that could be accidentally copied

**Files to Handle:**
- `legacy/_archive/repqms_Proto1_reference.py.py`
- `legacy/_archive/repqms_shipstation_sync.py.py`
- `legacy/_archive/*.html`

**Fix:**
1. Create `legacy/DO_NOT_USE__REFERENCE_ONLY/` directory
2. Move all files from `legacy/_archive/` to `legacy/DO_NOT_USE__REFERENCE_ONLY/`
3. Create `legacy/DO_NOT_USE__REFERENCE_ONLY/README.md`:
   ```markdown
   # DO NOT USE — REFERENCE ONLY
   
   These files are **NOT imported** and **NOT executed**.
   
   They are kept for historical reference only.
   
   **DO NOT copy code from these files into the main codebase.**
   
   - `repqms_Proto1_reference.py.py` - Monolithic prototype (psycopg2, SMTP, raw SQL)
   - `repqms_shipstation_sync.py.py` - Old sync implementation (different schema)
   - `*.html` - Legacy admin templates (visual reference only)
   ```

**Acceptance Test:**
- Verify no imports reference legacy files: `grep -r "from legacy\|import legacy" app/`
- Application still runs after moving files
- Legacy files are clearly marked as archived

---

## Implementation Order

1. **Fix 1** (ShipStation default date) - BLOCKER, do first
2. **Fix 2** (Skip orphan ShipStation rows) - BLOCKER, do next
3. **Fix 3** (Require customer for manual) - BLOCKER, do next
4. **Fix 4** (Year filter logic) - High, data correctness
5. **Fix 5** (Sales by Month table) - High, baseline feature
6. **Fix 6** (Limit warnings) - High, operational clarity
7. **Fix 7** (Distributions tab) - Medium, baseline parity
8. **Fix 8** (Grouped orders) - Medium, UX improvement
9. **Fix 9** (Disable diagnostics) - Medium/High, security
10. **Fix 10** (Quarantine legacy) - Medium, maintenance

---

## Files to Modify

**Priority 1 (Blockers):**
- `app/eqms/modules/shipstation_sync/service.py`
- `app/eqms/modules/shipstation_sync/admin.py`
- `app/eqms/templates/admin/distribution_log/edit.html`
- `app/eqms/modules/rep_traceability/admin.py`
- `app/eqms/modules/rep_traceability/service.py`

**Priority 2 (High):**
- `app/eqms/modules/customer_profiles/admin.py`
- `app/eqms/modules/rep_traceability/service.py`
- `app/eqms/templates/admin/sales_dashboard/index.html`
- `app/eqms/templates/admin/shipstation/index.html`

**Priority 3 (Medium):**
- `app/eqms/templates/admin/customers/detail.html`
- `app/eqms/modules/customer_profiles/admin.py`
- `legacy/_archive/*` (move to quarantine)

---

## Validation Checklist

After each fix, verify:

- [ ] **Fix 1:** ShipStation sync defaults to 2025-01-01, SQL query shows 2025 months
- [ ] **Fix 2:** ShipStation skips orders when customer resolution fails, no orphan rows created
- [ ] **Fix 3:** Manual distribution entry requires customer, validation enforces it
- [ ] **Fix 4:** Customer Database year filter shows only customers with orders in that year
- [ ] **Fix 5:** Sales Dashboard shows "Sales by Month" table with correct data
- [ ] **Fix 6:** ShipStation UI shows warning when limits are hit
- [ ] **Fix 7:** Customer Profile has Distributions tab showing all entries
- [ ] **Fix 8:** Customer Profile Orders tab groups entries by order number
- [ ] **Fix 9:** ShipStation diagnostics endpoint disabled in production
- [ ] **Fix 10:** Legacy files quarantined, no imports reference them

---

## SQL Verification Queries

After Fix 1-2, run these to verify 2025 data:

**Postgres:**
```sql
-- Verify 2025 months exist
SELECT DATE_TRUNC('month', ship_date) AS month, COUNT(*) AS entries, SUM(quantity) AS units
FROM distribution_log_entries
WHERE source = 'shipstation' AND ship_date >= '2025-01-01'
GROUP BY month ORDER BY month;

-- Verify no orphan ShipStation rows
SELECT COUNT(*) FROM distribution_log_entries
WHERE source = 'shipstation' AND customer_id IS NULL;
```

**SQLite:**
```sql
-- Verify 2025 months exist
SELECT substr(ship_date, 1, 7) AS month, COUNT(*) AS entries, SUM(quantity) AS units
FROM distribution_log_entries
WHERE source = 'shipstation' AND ship_date >= '2025-01-01'
GROUP BY month ORDER BY month;
```

---

## What NOT to Do

- ❌ Do NOT add Flask-WTF for CSRF (defer to later, use custom token if needed)
- ❌ Do NOT refactor beyond fixing the specific issues
- ❌ Do NOT change working code patterns (only fix broken/inconsistent code)
- ❌ Do NOT delete legacy files without quarantining (keep for reference)

---

## Notes

- **CSRF Protection:** Identified as high-severity but deferred to later (requires approach decision)
- **Performance Optimization:** Dashboard lifetime classification can be optimized later (not blocking)
- **Customer Database Rep Filter:** UI missing but route supports it; add dropdown or remove param

---

## Deliverables

When complete, you should have:
- ✅ ShipStation sync pulls from 2025-01-01 by default
- ✅ No orphan distribution entries (all have `customer_id`)
- ✅ Manual distribution entries require customer selection
- ✅ Customer Database year filter works correctly
- ✅ Sales Dashboard shows "Sales by Month" table
- ✅ ShipStation UI shows limit warnings
- ✅ Customer Profile has Distributions tab
- ✅ Customer Profile Orders are grouped by order number
- ✅ ShipStation diagnostics disabled in production
- ✅ Legacy files quarantined

**Begin with Fix 1 (ShipStation default date) - it's a blocker preventing 2025 data visibility.**
