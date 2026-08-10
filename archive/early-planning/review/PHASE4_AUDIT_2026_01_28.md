# Phase 4 System Audit
**Date:** 2026-01-28  
**Focus:** Distribution Details Modal, Multi-SKU Orders, PDF Matching Pipeline

---

## Executive Summary

This audit identifies **5 critical issues** and **2 architectural improvements** needed. The primary issues are:

1. **P0**: Distribution details modal broken (`OrderPdfAttachment` not imported)
2. **P0**: Multi-SKU order architecture mismatch - current model is 1 row per SKU, user expects 1 row per order
3. **P1**: No UI for manually matching unmatched PDF pages to distributions
4. **P1**: Distribution log table shows SKU/Lot columns - makes no sense for multi-SKU orders
5. **P2**: ShipStation duplicate warnings are noisy but not actual errors

---

## P0-1: Distribution Details Modal Broken (CRITICAL)

### Symptom
Clicking "Details" button on any distribution entry shows:
```
Error loading details
```

### Runtime Error
```
NameError: name 'OrderPdfAttachment' is not defined
File "/app/app/eqms/modules/rep_traceability/admin.py", line 471, in distribution_log_entry_details
    attachment_filters.append(OrderPdfAttachment.sales_order_id == entry.sales_order_id)
```

### Root Cause
`OrderPdfAttachment` is imported inside `_store_pdf_attachment()` function (line 68) but NOT at module level. The `distribution_log_entry_details()` function uses it directly without importing.

### Fix
**File:** `app/eqms/modules/rep_traceability/admin.py`

Add `OrderPdfAttachment` to the imports at line 15:

```python
# BEFORE (line 15):
from app.eqms.modules.rep_traceability.models import ApprovalEml, DistributionLogEntry, TracingReport

# AFTER:
from app.eqms.modules.rep_traceability.models import (
    ApprovalEml, 
    DistributionLogEntry, 
    OrderPdfAttachment,
    TracingReport,
)
```

### Verification
1. Go to Distribution Log: `https://silqeqms.com/admin/distribution-log`
2. Click "Details" on any entry
3. Modal should open with distribution details, NOT "Error loading details"

---

## P0-2: Multi-SKU Order Architecture (ARCHITECTURAL CHANGE)

### Current Situation
**ShipStation orders commonly have 2+ SKUs** (e.g., 211610SPT and 211810SPT on the same order).

Current data model:
- `DistributionLogEntry` has **one** `sku` and **one** `lot_number` per row
- ShipStation sync creates **one entry per SKU per shipment**
- So an order with 2 SKUs = 2 distribution log entries

Current UI:
- Distribution log table has SKU and Lot columns
- Each row is one SKU, not one order
- This is confusing when an order has multiple SKUs

### User Expectation
- **One row per order** in distribution log
- Multiple SKUs shown in the **details modal**
- SKU/Lot columns should NOT be in the main table

### Recommended Solution: Schema Change

Add a new model `DistributionLine` (similar to `SalesOrderLine`):

**1. New Model: `DistributionLine`**

```python
# app/eqms/modules/rep_traceability/models.py

class DistributionLine(Base):
    """Individual SKU/lot on a distribution entry."""
    __tablename__ = "distribution_lines"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    distribution_entry_id: Mapped[int] = mapped_column(
        ForeignKey("distribution_log_entries.id", ondelete="CASCADE"), 
        nullable=False
    )
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    lot_number: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**2. Migration Strategy**

Create an Alembic migration that:
1. Creates `distribution_lines` table
2. For each existing `DistributionLogEntry`, creates a `DistributionLine` with the entry's SKU/lot/qty
3. Adds relationship to `DistributionLogEntry`
4. Does NOT remove sku/lot_number columns from DistributionLogEntry (keep for backward compatibility initially)

**3. Update ShipStation Sync**

Modify `app/eqms/modules/shipstation_sync/service.py`:

Current behavior (line 452-500):
```python
for sku, units in sku_units.items():
    # Creates one DistributionLogEntry per SKU
    ...
    e = create_distribution_entry(s, payload, ...)
```

New behavior:
```python
# Create ONE distribution entry per order
e = create_distribution_entry(s, base_payload, ...)

# Create multiple lines per SKU
for sku, units in sku_units.items():
    lot_for_row = sku_lot_pairs.get(sku) or fallback_lot
    line = DistributionLine(
        distribution_entry_id=e.id,
        sku=sku,
        lot_number=lot_for_row,
        quantity=units,
    )
    s.add(line)
```

**4. Update UI**

- **Distribution Log Table** (`app/eqms/templates/admin/distribution_log/list.html`):
  - Remove SKU and Lot columns
  - Add "Lines" column showing count (e.g., "2 SKUs")
  - Or show aggregated quantity across all lines

- **Details Modal**: Show all SKU/Lot/Qty lines in a mini-table

**5. Update Unique Constraint**

Current constraint: `(source, external_key)` where external_key = `{shipment_id}:{sku}:{lot}`

New constraint: `(source, external_key)` where external_key = `{shipment_id}` (one per shipment, not per SKU)

### Alternative: UI-Only Aggregation (Less Invasive)

If schema change is too risky, aggregate by `order_number` in the UI:

1. Group distribution entries by `order_number` when rendering the list
2. Show aggregated totals
3. In details modal, show all entries for that order_number

**Pros:** No migration needed  
**Cons:** Doesn't fix the underlying data model; grouping logic is complex

### Recommendation
**Implement schema change** (new `DistributionLine` table). This is the correct long-term architecture and aligns with `SalesOrder → SalesOrderLine` pattern already in use.

---

## P1-1: No Manual PDF Matching UI

### Problem
When bulk PDF import creates unmatched pages, there's no UI to manually match them to existing distributions.

The "Unmatched PDFs" page (`/admin/sales-orders/unmatched-pdfs`) only shows download links.

### Required Features

1. **Match to Distribution** button on each unmatched PDF row
2. Modal that lets admin:
   - Search/select a distribution by order number
   - Confirm match
3. On match:
   - Update `OrderPdfAttachment.sales_order_id` and/or `distribution_entry_id`
   - Optionally parse the PDF and create a Sales Order

### Implementation

**File:** `app/eqms/templates/admin/sales_orders/unmatched_pdfs.html`

Add a "Match" button next to each row:

```html
<button class="button button--secondary" 
        onclick="showMatchModal({{ a.id }}, '{{ a.filename }}')"
        title="Match to Distribution">
    🔗 Match
</button>
```

**Add match modal and JavaScript:**

```html
<dialog id="match-pdf-modal">
    <form method="post" action="/admin/sales-orders/pdf/match">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <input type="hidden" name="attachment_id" id="match-attachment-id">
        
        <label>Order Number:</label>
        <input type="text" name="order_number" id="match-order-number" 
               placeholder="e.g., 0000273" required>
        
        <button type="submit">Match PDF</button>
    </form>
</dialog>
```

**New route:** `app/eqms/modules/rep_traceability/admin.py`

```python
@bp.post("/sales-orders/pdf/match")
@require_permission("sales_orders.edit")
def match_pdf_to_order():
    """Manually match an unmatched PDF to a distribution/sales order."""
    s = db_session()
    u = _current_user()
    
    attachment_id = request.form.get("attachment_id")
    order_number = request.form.get("order_number", "").strip()
    
    attachment = s.get(OrderPdfAttachment, int(attachment_id))
    if not attachment:
        flash("Attachment not found.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_unmatched_pdfs"))
    
    # Find matching sales order or distribution
    from app.eqms.modules.rep_traceability.service import normalize_order_number
    normalized = normalize_order_number(order_number)
    
    # Try to find existing Sales Order
    sales_order = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_number.ilike(f"%{normalized}%"))
        .first()
    )
    
    if sales_order:
        attachment.sales_order_id = sales_order.id
        attachment.pdf_type = "matched_upload"
        s.commit()
        flash(f"PDF matched to Sales Order {sales_order.order_number}.", "success")
    else:
        # Try to find unmatched distribution
        dist = (
            s.query(DistributionLogEntry)
            .filter(
                DistributionLogEntry.order_number.ilike(f"%{normalized}%"),
                DistributionLogEntry.sales_order_id.is_(None),
            )
            .first()
        )
        if dist:
            attachment.distribution_entry_id = dist.id
            attachment.pdf_type = "matched_upload"
            s.commit()
            flash(f"PDF matched to Distribution {dist.order_number}.", "success")
        else:
            flash(f"No order or distribution found matching '{order_number}'.", "warning")
    
    return redirect(url_for("rep_traceability.sales_orders_unmatched_pdfs"))
```

---

## P1-2: Remove SKU/Lot Columns from Distribution Log Table

### Current State
The distribution log table has these columns:
- Date
- Order
- Facility
- **SKU** ← Remove
- **Lot** ← Remove
- Qty
- Source
- Actions

### Reason to Remove
With multi-SKU orders, showing one SKU per row is misleading. Users expect one row per order.

### Fix
**File:** `app/eqms/templates/admin/distribution_log/list.html`

Remove these column headers (lines 81-82):
```html
<!-- REMOVE THESE -->
<th>SKU</th>
<th>Lot</th>
```

Remove these cell renderings (lines 100-101):
```html
<!-- REMOVE THESE -->
<td><code>{{ e.sku|e }}</code></td>
<td><code>{{ e.lot_number|e }}</code></td>
```

**Optional Replacement:** Show "Lines" count instead:
```html
<th>Lines</th>
...
<td>
    {% if e.lines %}
        {{ e.lines|length }} SKU{{ 's' if e.lines|length > 1 else '' }}
    {% else %}
        1 SKU
    {% endif %}
</td>
```

*(This requires the schema change from P0-2)*

---

## P2-1: ShipStation Duplicate Warnings (Low Priority)

### Symptom
Logs show warnings like:
```
WARNING in service: SYNC: duplicate order=SO 0000273 ext_key=394098265:211410SPT:SLQ-11192024 
err=(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint
```

### Analysis
This is **expected behavior** - the unique constraint prevents duplicate distribution entries. The warning is just informational.

However, the warning message is noisy and could be confusing.

### Fix (Optional)
Change from `WARNING` to `DEBUG` level in `app/eqms/modules/shipstation_sync/service.py` line 503:

```python
# BEFORE:
logger.warning("SYNC: duplicate order=%s ext_key=%s err=%s", ...)

# AFTER:
logger.debug("SYNC: skipped duplicate order=%s ext_key=%s", ...)
```

---

## Summary: Implementation Order

### Phase 1: Immediate Fixes (Deploy Today)

1. **P0-1**: Add `OrderPdfAttachment` import (5 minutes)

### Phase 2: Short-Term (This Week)

2. **P1-2**: Remove SKU/Lot columns from distribution log table (if not doing schema change)
3. **P1-1**: Add manual PDF matching UI

### Phase 3: Schema Change (Next Sprint)

4. **P0-2**: Implement `DistributionLine` model and migrate data
   - Create migration
   - Update ShipStation sync
   - Update UI
   - Test thoroughly before deploying

### Phase 4: Polish

5. **P2-1**: Reduce duplicate log noise

---

## Files to Modify

| File | Changes |
|------|---------|
| `app/eqms/modules/rep_traceability/admin.py` | Add `OrderPdfAttachment` import; add PDF match route |
| `app/eqms/modules/rep_traceability/models.py` | Add `DistributionLine` model |
| `app/eqms/modules/shipstation_sync/service.py` | Update sync to create one entry per order |
| `app/eqms/templates/admin/distribution_log/list.html` | Remove SKU/Lot columns |
| `app/eqms/templates/admin/sales_orders/unmatched_pdfs.html` | Add match button and modal |
| `migrations/versions/xxx_add_distribution_lines.py` | New migration |

---

## Verification After All Changes

1. **Distribution Details Modal**: Click "Details" on any distribution → Modal opens without error
2. **Distribution Log Table**: No SKU/Lot columns; shows order-level data
3. **ShipStation Sync**: Multi-SKU orders create ONE distribution entry with multiple lines
4. **PDF Matching**: Can manually match unmatched PDFs from Unmatched PDFs page
5. **Data Integrity**: Run `/admin/diagnostics` → `shipstation_integrity.multi_sku_orders` should be empty after re-sync

---

## Post-Implementation Data Reset

After developer completes all changes:

1. Go to: `https://silqeqms.com/admin/reset-data`
2. Type: `DELETE ALL DATA`
3. Click: Reset All Data
4. Run ShipStation sync (start with one month at a time)
5. Import Sales Order PDFs
6. Verify multi-SKU orders show correctly
