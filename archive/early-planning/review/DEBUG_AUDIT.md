# DEBUG_AUDIT — Silq eQMS Full System Audit

**Date:** 2026-01-26  
**Focus:** Stability, correctness, data integrity, UI/UX reliability, cleanup

---

## A. Executive Summary

### Highest-Impact User-Facing Issues

1. **BUG-001 (P0):** Modal backgrounds use undefined CSS variable `--card-bg` causing potential transparency/readability issues on all detail modals system-wide
2. **BUG-002 (P1):** Lot tracking hardcoded to 2025 (`min_year = 2025`) — should be 2026 or configurable
3. **BUG-003 (P1):** Sales dashboard order details modal shows limited info — no PDF attachments visible in modal
4. **BUG-004 (P1):** No bulk customer refresh from sales orders — customers created from ShipStation ship-to, not normalized sales order facility data
5. **BUG-005 (P2):** Distribution log entry-details modal shows raw lot strings from distribution entries, not corrected LotLog canonical names
6. **BUG-006 (P2):** Sales orders list has no "View Detail" button inline — requires extra click

### Highest-Risk Data Integrity Issues

1. **DATA-001 (P0):** Customer identity derived from ShipStation ship-to fields (`company`, `name`) rather than sales order canonical facility data
2. **DATA-002 (P1):** Lot names in distribution entries may not match LotLog corrections — displayed raw from ShipStation internal_notes
3. **DATA-003 (P1):** Distribution entries can exist without linked sales_order_id (FK is nullable)
4. **DATA-004 (P1):** Customer dedup/merge not automatically triggered — relies on manual admin merge
5. **DATA-005 (P2):** Sales order lines store lot_number which may differ from distribution entry lot_number for same order

### Stop-the-Bleeding Recommendations

1. **Immediate:** Add `--card-bg: var(--panel);` to `design-system.css` `:root` block
2. **Immediate:** Change `min_year = 2025` to `min_year = 2026` in `service.py` compute_sales_dashboard
3. **Short-term:** Add customer refresh script that updates customers from sales order ship-to fields
4. **Short-term:** Ensure lot_number in distributions uses LotLog-corrected values consistently

---

## B. Reproducible Bug List (Prioritized)

### BUG-001: Modal Backgrounds Undefined (P0)

| Field | Value |
|-------|-------|
| **ID** | BUG-001 |
| **Title** | CSS variable `--card-bg` not defined causing modal background issues |
| **Severity** | P0 |
| **Where** | Multiple templates using `var(--card-bg)`: `_layout.html:61`, `distribution_log/list.html:153-154`, `sales_dashboard/index.html:226`, `debug_permissions.html:42` |
| **Repro Steps** | 1. Login as admin 2. Go to Distribution Log 3. Click "Details" on any entry 4. Observe modal background |
| **Expected** | Solid dark panel background (`#0f1a30`) |
| **Actual** | Browser default (often white/transparent) or fallback color |
| **Root Cause** | `design-system.css` defines `--panel: #0f1a30` but templates reference `--card-bg` which is never defined |
| **Fix Outline** | Add `--card-bg: var(--panel);` or `--card-bg: #0f1a30;` to `:root` in `design-system.css` |
| **Files to Change** | `app/eqms/static/design-system.css` |
| **Verification** | Open any detail modal, inspect element, confirm `background: var(--card-bg)` resolves to solid color |

### BUG-002: Lot Tracking Year Hardcoded to 2025 (P1)

| Field | Value |
|-------|-------|
| **ID** | BUG-002 |
| **Title** | Sales dashboard lot tracking shows 2025+ lots instead of 2026+ |
| **Severity** | P1 |
| **Where** | `app/eqms/modules/rep_traceability/service.py:592` |
| **Repro Steps** | 1. Go to Sales Dashboard 2. View "Lot Tracking" section |
| **Expected** | Show only lots distributed in 2026 |
| **Actual** | Shows lots from 2025 onwards |
| **Root Cause** | Hardcoded `min_year = 2025` on line 592 |
| **Fix Outline** | Change to `min_year = 2026` or make configurable via env var `DASHBOARD_LOT_MIN_YEAR` |
| **Files to Change** | `app/eqms/modules/rep_traceability/service.py` |
| **Verification** | Dashboard lot tracking table shows only 2026+ lot entries; totals still include all-time distributions |

### BUG-003: Order Details Modal Missing PDF Attachments (P1)

| Field | Value |
|-------|-------|
| **ID** | BUG-003 |
| **Title** | Sales dashboard order-details modal doesn't show PDF attachments |
| **Severity** | P1 |
| **Where** | Route: `/admin/sales-dashboard/order-details/<order_number>`, Template: `sales_dashboard/index.html:237-277` |
| **Repro Steps** | 1. Go to Sales Dashboard 2. Click "View Details" on any order 3. Observe modal content |
| **Expected** | If order has PDF attachments, show download links |
| **Actual** | Only shows order/lines info, no attachments section |
| **Root Cause** | `sales_dashboard_order_details` endpoint (line 1654) doesn't query `OrderPdfAttachment` and doesn't return attachments in JSON response |
| **Fix Outline** | Add attachments query to endpoint, include in JSON response, render in modal JS |
| **Files to Change** | `app/eqms/modules/rep_traceability/admin.py:1654-1736`, `app/eqms/templates/admin/sales_dashboard/index.html` |
| **Verification** | Order details modal shows "Attachments" section with download links when PDFs exist |

### BUG-004: Customer Identity From ShipStation Not Sales Orders (P1)

| Field | Value |
|-------|-------|
| **ID** | BUG-004 |
| **Title** | Customer profile created from ShipStation ship-to, not normalized sales order data |
| **Severity** | P1 |
| **Where** | `app/eqms/modules/shipstation_sync/service.py:46-64` (`_get_customer_from_ship_to`) |
| **Repro Steps** | 1. Run ShipStation sync 2. Check new customers 3. Compare to sales order ship-to |
| **Expected** | Customer facility_name matches canonical sales order ship-to name |
| **Actual** | Customer created from raw ShipStation `company` or `name` field which may have inconsistent casing/formatting |
| **Root Cause** | `_get_customer_from_ship_to` extracts directly from ShipStation API response, not from a normalized sales order source |
| **Fix Outline** | After creating sales order, use sales order's linked customer (which was created during order creation) consistently. Alternatively, add a customer refresh script that normalizes existing customers. |
| **Files to Change** | `app/eqms/modules/shipstation_sync/service.py`, potentially new script `scripts/refresh_customers_from_sales_orders.py` |
| **Verification** | Customers have consistent, normalized facility_name; duplicates merged |

### BUG-005: Distribution Entries Show Raw Lot Strings (P2)

| Field | Value |
|-------|-------|
| **ID** | BUG-005 |
| **Title** | Distribution entry lot_number may not use LotLog-corrected canonical name |
| **Severity** | P2 |
| **Where** | Distribution log entry details modal, `entry.lot_number` display |
| **Repro Steps** | 1. Open distribution entry detail 2. Check lot number field |
| **Expected** | Shows LotLog-corrected canonical lot name (e.g., `SLQ-05012026`) |
| **Actual** | May show raw extracted lot string (e.g., `SLQ-050120` without year correction) |
| **Root Cause** | `lot_corrections` applied during sync but historic entries may have uncorrected values |
| **Fix Outline** | Display corrected lot in UI by applying `lot_corrections` at render time, or run backfill to correct existing entries |
| **Files to Change** | `app/eqms/modules/rep_traceability/admin.py` (entry details endpoint), or backfill script |
| **Verification** | All displayed lot numbers match LotLog canonical format |

### BUG-006: Sales Orders List Missing Inline Details Button (P2)

| Field | Value |
|-------|-------|
| **ID** | BUG-006 |
| **Title** | Sales orders list requires navigation to view details |
| **Severity** | P2 |
| **Where** | `app/eqms/templates/admin/sales_orders/list.html` |
| **Repro Steps** | 1. Go to Sales Orders list 2. Each row only has "View" link |
| **Expected** | In-page "Details" button that opens a modal (like distribution log) |
| **Actual** | Must click through to full page detail view |
| **Root Cause** | No modal/AJAX pattern implemented for sales orders list |
| **Fix Outline** | Add inline details button + modal similar to distribution log pattern |
| **Files to Change** | `app/eqms/templates/admin/sales_orders/list.html`, possibly new endpoint or reuse existing |
| **Verification** | Can view order details in modal without leaving list page |

---

## C. Data Lineage / Source-of-Truth Audit

### Distribution Log (`distribution_log_entries`)

| Aspect | Detail |
|--------|--------|
| **Canonical Table** | `distribution_log_entries` |
| **Model** | `app/eqms/modules/rep_traceability/models.py:DistributionLogEntry` |
| **Who Writes** | ShipStation sync (`shipstation_sync/service.py`), Manual entry, CSV import, PDF import |
| **Who Reads** | Sales dashboard, tracing reports, customer stats, lot tracking |
| **Source of Truth** | ✅ Yes — this is the canonical distribution record |
| **Leakage Issues** | `lot_number` may contain raw ShipStation extraction without LotLog correction |

### Sales Orders (`sales_orders`)

| Aspect | Detail |
|--------|--------|
| **Canonical Table** | `sales_orders` |
| **Model** | `app/eqms/modules/rep_traceability/models.py:SalesOrder` |
| **Who Writes** | ShipStation sync, PDF import, Manual entry |
| **Who Reads** | Distribution linkage, customer profile, PDF attachments |
| **Source of Truth** | ✅ Yes — canonical order identity, links distributions to customers |
| **Leakage Issues** | None identified; properly linked via `customer_id` FK |

### Customers (`customers`)

| Aspect | Detail |
|--------|--------|
| **Canonical Table** | `customers` |
| **Model** | `app/eqms/modules/customer_profiles/models.py:Customer` |
| **Who Writes** | `find_or_create_customer` called from ShipStation sync and manual entry |
| **Who Reads** | Sales orders, distributions, customer profile pages |
| **Source of Truth** | 🟡 Partial — should be derived from sales orders, currently created from ShipStation ship-to |
| **Leakage Issues** | **Customer `facility_name` comes from ShipStation `ship_to.company` or `ship_to.name`**, not normalized sales order data |

### LotLog (CSV File)

| Aspect | Detail |
|--------|--------|
| **Canonical Location** | `app/eqms/data/LotLog.csv` (or env `SHIPSTATION_LOTLOG_PATH`) |
| **Parser** | `app/eqms/modules/shipstation_sync/parsers.py:load_lot_log_with_inventory` |
| **Who Reads** | Sales dashboard lot tracking, ShipStation sync (for corrections) |
| **Source of Truth** | ✅ Yes — canonical lot names, inventory counts, SKU mappings |
| **Leakage Issues** | Corrections applied at sync time but not retroactively to existing distribution entries |

### ShipStation Raw Data (`shipstation_skipped_orders`)

| Aspect | Detail |
|--------|--------|
| **Canonical Table** | `shipstation_skipped_orders` (for diagnostics only) |
| **Model** | `app/eqms/modules/shipstation_sync/models.py:ShipStationSkippedOrder` |
| **Who Writes** | ShipStation sync (orders that couldn't be processed) |
| **Who Reads** | Admin diagnostics page only |
| **Source of Truth** | ❌ No — raw upstream data, not canonical |
| **Leakage Issues** | None — appropriately isolated to diagnostics |

### Leakage Summary

```
ShipStation API
      │
      ▼
  ship_to.company / ship_to.name
      │
      ├──► Customer.facility_name  ← LEAKAGE: Should be normalized from sales order
      │
      ▼
  internalNotes (lot extraction)
      │
      ├──► lot_corrections applied
      │
      ▼
  DistributionLogEntry.lot_number  ← PARTIAL: Corrections applied on insert, not retroactive
```

---

## D. Detail View Failure Deep Dive

### Network Requests Analysis

| Modal | Endpoint | Status | Payload |
|-------|----------|--------|---------|
| Distribution Entry Details | `/admin/distribution-log/entry-details/<id>` | 200 OK | JSON with entry, order, customer, attachments |
| Sales Dashboard Order Details | `/admin/sales-dashboard/order-details/<order_number>` | 200 OK | JSON with order, lines, distributions (missing attachments) |
| Notes Modal | `/admin/notes/modal/<entity_type>/<id>` | 200 OK | HTML partial |

### JS Errors

No JS errors identified in modal fetch logic. Error handling exists:
```javascript
// distribution_log/list.html:340
} catch (e) {
  content.innerHTML = `<div style="color:var(--danger); text-align:center; padding:20px;">Error loading details</div>`;
}
```

### Template/Layout Issues

**Root Cause: Missing CSS Variable**

```css
/* Templates reference: */
background: var(--card-bg);

/* But design-system.css only defines: */
--panel: #0f1a30;
/* NO --card-bg defined! */
```

**Affected Locations:**
- `_layout.html:61` (notes modal)
- `distribution_log/list.html:153-154` (entry details modal)
- `sales_dashboard/index.html:226` (order details modal)
- `debug_permissions.html:42` (table header)

### Auth/CSRF Issues

None identified. CSRF token properly injected via `<meta name="csrf-token">` and auto-added to forms.

### CSS/Readability Fix

**Minimal Fix:**

```css
/* Add to app/eqms/static/design-system.css :root block */
--card-bg: var(--panel);
```

**Alternative (more explicit):**

```css
--card-bg: #0f1a30;
```

This single line fix will make all detail modals have solid, readable backgrounds.

---

## E. Sales Order PDF Pipeline Audit

### Current Pipeline Flow

```
1. PDF Upload (bulk or single)
   └── POST /admin/sales-orders/import-pdf-bulk
   └── POST /admin/sales-orders/<id>/upload-pdf
       │
       ▼
2. Parse PDF (pdfplumber)
   └── app/eqms/modules/rep_traceability/parsers/pdf.py:parse_sales_orders_pdf
       │
       ▼
3. Store Original PDF
   └── _store_pdf_attachment() → S3 storage
   └── Storage key: sales_orders/{order_id}/pdfs/{type}_{timestamp}_{filename}
       │
       ▼
4. Create OrderPdfAttachment Record
   └── Links to sales_order_id
   └── Optionally links to distribution_entry_id
       │
       ▼
5. PDF Available for Download
   └── GET /admin/sales-orders/pdf/<attachment_id>/download
```

### Attachment Model

```python
# app/eqms/modules/rep_traceability/models.py:124-141
class OrderPdfAttachment(Base):
    __tablename__ = "order_pdf_attachments"
    
    id: Mapped[int]
    sales_order_id: Mapped[int | None]  # FK to sales_orders
    distribution_entry_id: Mapped[int | None]  # FK to distribution_log_entries
    storage_key: Mapped[str]  # S3 path
    filename: Mapped[str]
    pdf_type: Mapped[str]  # 'sales_order', 'shipping_label', etc.
    uploaded_at: Mapped[datetime]
    uploaded_by_user_id: Mapped[int | None]
```

### Where Download Links Exist

| Location | Has Download? | Notes |
|----------|---------------|-------|
| Sales Order Detail Page | ✅ Yes | `sales_orders/detail.html:139` |
| Distribution Log Entry Details Modal | ✅ Yes | `distribution_log/list.html:313` |
| Sales Dashboard Order Modal | ❌ No | Missing attachments query |
| Sales Orders List | ❌ No | No inline action |

### Missing Download Links Fix

**Sales Dashboard Order Modal:**

```python
# Add to admin.py:1654 sales_dashboard_order_details()
# After getting distributions, add:
from app.eqms.modules.rep_traceability.models import OrderPdfAttachment

attachments = []
if order:
    attachments = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.sales_order_id == order.id)
        .order_by(OrderPdfAttachment.uploaded_at.desc())
        .limit(10)
        .all()
    )

# Include in return jsonify():
"attachments": [
    {"id": a.id, "filename": a.filename, "pdf_type": a.pdf_type}
    for a in attachments
],
```

**Update Modal JS in `sales_dashboard/index.html`:**

```javascript
// After lines rendering, add:
if (data.attachments && data.attachments.length > 0) {
  html += `<div style="margin-top:16px;"><div style="font-size:11px; text-transform:uppercase; color:var(--muted); margin-bottom:8px;">Attachments</div>`;
  for (const a of data.attachments) {
    html += `<div style="margin-bottom:6px;"><a href="/admin/sales-orders/pdf/${a.id}/download" class="button button--secondary" style="font-size:12px;">${a.filename}</a></div>`;
  }
  html += `</div>`;
}
```

---

## F. Customer Refresh From Sales Orders

### Current Customer Creation Flow

```
ShipStation Sync
    │
    ▼
_get_customer_from_ship_to(s, ship_to)
    │
    ├── ship_to.company or ship_to.name → facility_name
    │
    ▼
find_or_create_customer(s, facility_name=..., address1=..., ...)
    │
    ▼
Customer record created/updated
```

**Problem:** Customer identity derived from raw ShipStation `ship_to` data, not from canonical sales order fields.

### Fields Coming From ShipStation Today

| Customer Field | Source |
|----------------|--------|
| `facility_name` | `ship_to.company` or `ship_to.name` |
| `address1` | `ship_to.street1` |
| `city` | `ship_to.city` |
| `state` | `ship_to.state` or `ship_to.stateCode` |
| `zip` | `ship_to.postalCode` |

### Fields That Should Come From Sales Orders

Sales orders (especially PDF imports) contain normalized ship-to data that should be canonical:
- Parsed facility name from PDF header
- Parsed address block
- This is more reliable than ShipStation's `ship_to` which may have inconsistent capitalization

### Dedup/Grouping Key Strategy

Current: `company_key = canonical_customer_key(facility_name)` — lowercased, stripped, punctuation removed.

**This is correct** but the input (`facility_name`) comes from ShipStation rather than normalized sales order data.

### Backfill Approach

**Script: `scripts/refresh_customers_from_sales_orders.py`**

```python
"""
Refresh customer data from linked sales orders (idempotent).
Uses sales order ship-to as source of truth for facility_name, address.
"""
def refresh_customers_from_sales_orders():
    # For each customer with linked sales orders:
    # 1. Get most recent sales order
    # 2. If sales order has better facility data, update customer
    # 3. Merge duplicates with same company_key
    pass
```

**Migration Notes:**
- No schema changes required
- Run after sales orders are properly populated
- Idempotent — safe to run multiple times

---

## G. Lot Tracking Logic Audit

### Current Dashboard Query Logic

**File:** `app/eqms/modules/rep_traceability/service.py:588-652`

```python
# Line 592 - HARDCODED YEAR
min_year = 2025
min_year_date = date(min_year, 1, 1)

# Line 596-601 - Query ALL distribution entries with lot_number
all_entries = (
    s.query(DistributionLogEntry)
    .filter(DistributionLogEntry.lot_number.isnot(None))
    .order_by(...)
    .all()
)

# Line 606-625 - Build lot_map with ALL-TIME totals (correct!)
for e in all_entries:
    # ... normalize lot, apply corrections ...
    rec["units"] += int(e.quantity or 0)  # All-time total
    
    # Track if lot appeared in 2025+ distributions
    if e.ship_date and e.ship_date >= min_year_date:
        lot_recent_flags[corrected_lot] = True

# Line 627-641 - Filter to qualifying lots (2025+ built OR 2025+ distributed)
for lot_key in lot_map.keys():
    lot_year = lot_years.get(lot_key)  # From LotLog
    if lot_year and lot_year >= min_year:
        qualifying_lots.add(lot_key)
    elif lot_recent_flags.get(lot_key):
        qualifying_lots.add(lot_key)
```

### How Lot Name Is Derived

1. **Extraction:** `extract_lot(internal_notes)` from ShipStation
2. **Normalization:** `normalize_lot(raw_lot)` — uppercase, strip, format
3. **Correction:** `lot_corrections.get(normalized_lot, normalized_lot)` from LotLog

**Problem:** Corrections applied at sync time but:
- Historic entries may have uncorrected lot_number values
- UI displays `entry.lot_number` directly without re-applying corrections

### Correct Filter Implementation

**Current (Correct Pattern):**
- Show rows where lot is 2025+ built **OR** has 2025+ distributions
- Totals include ALL-TIME distributions

**Fix Needed:**
- Change `min_year = 2025` to `min_year = 2026`

**File:** `app/eqms/modules/rep_traceability/service.py`

```python
# Line 592 - Change from:
min_year = 2025

# To:
min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2026"))
```

### Verification SQL

```sql
-- Check lot_number values in distributions
SELECT DISTINCT lot_number, COUNT(*) as cnt
FROM distribution_log_entries
WHERE lot_number IS NOT NULL
GROUP BY lot_number
ORDER BY cnt DESC
LIMIT 50;

-- Lots with 2026 distributions
SELECT DISTINCT lot_number
FROM distribution_log_entries
WHERE ship_date >= '2026-01-01'
  AND lot_number IS NOT NULL;

-- Compare to LotLog canonical names
-- (manual check against LotLog.csv)
```

---

## H. Legacy / Dead Code Cleanup Candidates

### Confirmed Legacy Files

| Path | Reason | Action | Risk if Kept | Verification |
|------|--------|--------|--------------|--------------|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/` | Clearly marked legacy reference templates | DELETE folder | Confusion, accidental use | `grep -r "legacy/DO_NOT_USE" app/` returns nothing |
| `legacy/DO_NOT_USE__REFERENCE_ONLY/README.md` | Documents legacy status | DELETE with folder | None | N/A |

### Potentially Unused Templates

| Path | Likely Status | Action | Verification |
|------|---------------|--------|--------------|
| `app/eqms/templates/admin/module_stub.html` | Scaffold placeholder | KEEP (used for empty modules) | Check if rendered by any route |

### Deprecated Code Patterns

| Location | Pattern | Action | Notes |
|----------|---------|--------|-------|
| `admin.py:184` | `customer_name` field marked "deprecated text mirror" | Monitor | Still used for backward compat |

### Unused Routes

None identified. All routes in `rep_traceability/admin.py` have corresponding templates and are reachable from navigation.

### Duplicate Utilities

None identified. Code is relatively clean with single implementations.

### Cleanup Recommendation

```bash
# Safe to delete:
rm -rf legacy/DO_NOT_USE__REFERENCE_ONLY/

# Verify no references:
grep -r "DO_NOT_USE" .
grep -r "legacy" app/eqms/
```

---

## I. Logging / Observability

### Current Logging Status

| Area | Has Logging? | Level | Notes |
|------|--------------|-------|-------|
| ShipStation sync | ✅ Yes | INFO/WARNING/ERROR | Good coverage |
| PDF parsing | 🟡 Partial | WARNING on failures | Could add more detail |
| Customer creation | ❌ No | — | Add INFO on create/update |
| Dashboard queries | ❌ No | — | Add timing logs |
| Detail fetches | ❌ No | — | Add INFO on modal loads |

### Recommended Log Lines

**PDF Split/Store:**
```python
# In _store_pdf_attachment()
logger.info("PDF stored: storage_key=%s sales_order_id=%s", storage_key, sales_order_id)
```

**Customer Refresh:**
```python
# In find_or_create_customer()
logger.info("Customer %s: action=%s facility=%s", customer.id, "created" if created else "updated", facility_name)
```

**Dashboard Queries:**
```python
# In compute_sales_dashboard()
import time
start = time.time()
# ... query logic ...
logger.info("Dashboard computed: window=%s-%s entries=%d duration=%.2fs", start_date, end_date, len(window_entries), time.time() - start)
```

**Detail Fetch:**
```python
# In distribution_log_entry_details()
logger.info("Entry details fetched: entry_id=%d has_order=%s has_customer=%s", entry_id, bool(order_data), bool(customer_data))
```

---

## J. Final Developer Prompt Inputs

### Prioritized Task List

#### P0 — Critical (Do Immediately)

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| P0-1 | Add `--card-bg` CSS variable | All modals have solid dark background, no transparency |
| P0-2 | Change lot tracking min_year to 2026 | Dashboard shows only 2026+ lots, totals still all-time |
| P0-3 | Add attachments to sales dashboard order modal | Modal shows PDF download links when attachments exist |

#### P1 — High (This Sprint)

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| P1-1 | Create customer refresh script | Can run `python scripts/refresh_customers_from_sales_orders.py` to normalize customer data |
| P1-2 | Apply lot corrections at display time | Entry details modal shows corrected lot names |
| P1-3 | Add inline details button to sales orders list | Can view order details in modal without navigation |

#### P2 — Medium (Backlog)

| ID | Task | Acceptance Criteria |
|----|------|---------------------|
| P2-1 | Add structured logging | Key operations have INFO-level logs |
| P2-2 | Delete legacy folder | `legacy/DO_NOT_USE__REFERENCE_ONLY/` removed |
| P2-3 | Backfill distribution lot_number corrections | Historic entries have corrected lot names |

### Files Most Likely to Change

```
app/eqms/static/design-system.css          # P0-1: Add --card-bg
app/eqms/modules/rep_traceability/service.py  # P0-2: min_year change
app/eqms/modules/rep_traceability/admin.py    # P0-3, P1-2: Attachments, lot display
app/eqms/templates/admin/sales_dashboard/index.html  # P0-3: Modal JS
app/eqms/templates/admin/sales_orders/list.html      # P1-3: Inline details
scripts/refresh_customers_from_sales_orders.py       # P1-1: New script
```

### Acceptance Criteria per P0 Item

**P0-1: CSS Variable Fix**
- [ ] `--card-bg: var(--panel);` added to `:root` in `design-system.css`
- [ ] All modals (distribution details, order details, notes) have solid background
- [ ] Text readable on all modals

**P0-2: Lot Tracking Year**
- [ ] `min_year = 2026` in `service.py:592` (or env-configurable)
- [ ] Dashboard lot table shows only 2026+ lots
- [ ] "Total Units Distributed" column shows all-time totals (not filtered to 2026)
- [ ] "Active Inventory" calculation correct

**P0-3: Sales Dashboard Attachments**
- [ ] `sales_dashboard_order_details` returns `attachments` array
- [ ] Modal JS renders attachments with download links
- [ ] Download links work (return PDF files)

### Required Workflow While Debugging

1. **Grep Routes:**
   ```bash
   grep -rn "@bp.get\|@bp.post" app/eqms/modules/rep_traceability/admin.py
   ```

2. **Validate JS Fetch URLs:**
   - Distribution details: `/admin/distribution-log/entry-details/${entryId}` ✅ Exists
   - Order details: `/admin/sales-dashboard/order-details/${orderNumber}` ✅ Exists
   - Notes modal: `/admin/notes/modal/${entityType}/${entityId}` ✅ Exists

3. **Inspect DB Models:**
   ```bash
   grep -rn "class.*Base" app/eqms/modules/
   ```
   
   Key relationships:
   - `DistributionLogEntry.sales_order_id` → `SalesOrder.id`
   - `SalesOrder.customer_id` → `Customer.id`
   - `OrderPdfAttachment.sales_order_id` → `SalesOrder.id`

4. **Check ShipStation Usage:**
   ```bash
   grep -rn "ShipStation\|shipstation" app/eqms/modules/rep_traceability/
   ```
   
   Should only appear in:
   - `service.py:40` (duplicate check helper)
   - `service.py:589` (LotLog parser import)

---

## Verification SQL Queries

```sql
-- Check distributions without sales_order_id
SELECT COUNT(*) as unlinked_distributions
FROM distribution_log_entries
WHERE sales_order_id IS NULL;

-- Check for duplicate customers (same company_key)
SELECT company_key, COUNT(*) as cnt
FROM customers
GROUP BY company_key
HAVING COUNT(*) > 1;

-- Lot names not matching SLQ-MMDDYYYY format
SELECT DISTINCT lot_number
FROM distribution_log_entries
WHERE lot_number IS NOT NULL
  AND lot_number NOT SIMILAR TO 'SLQ-[0-9]{8,10}';

-- Distributions in 2026 (for lot tracking verification)
SELECT COUNT(*) as distributions_2026
FROM distribution_log_entries
WHERE ship_date >= '2026-01-01';

-- PDF attachments count
SELECT COUNT(*) as pdf_attachments
FROM order_pdf_attachments;

-- Attachments linked to sales orders vs unlinked
SELECT 
  COUNT(CASE WHEN sales_order_id IS NOT NULL THEN 1 END) as linked,
  COUNT(CASE WHEN sales_order_id IS NULL THEN 1 END) as unlinked
FROM order_pdf_attachments;
```

---

*End of DEBUG_AUDIT.md*
