# Phase 2 Implementation Notes

**Implemented:** 2026-01-27  
**Status:** Complete

---

## Summary

Phase 2 enforces the canonical pipeline for customer identity and fixes data integrity issues:

1. **P0-1: ShipStation Sync** — No longer creates customers directly; uses Sales Order → Customer pipeline
2. **P0-2: Bulk PDF Import** — Now splits pages like single-file import
3. **P1-1: Customer Key Documentation** — Comprehensive docstrings + unit tests
4. **P1-2: Unmatched PDFs UI** — New `/admin/sales-orders/unmatched-pdfs` page
5. **P2-1: Remove "2025"** — Import page text made generic
6. **P2-2: Hide customer_name** — Deprecated field hidden in edit form
7. **P2-3: Delete legacy/** — Empty directory deleted (if accessible)

---

## Canonical Pipeline (Now Enforced)

```
ShipStation API
    ↓
Distribution Log Entry (clean, normalized)
    ↓
Try to match to existing Sales Order (by order_number)
    ↓
If match: customer_id comes from Sales Order (canonical)
If no match: distribution has customer_id=NULL (admin matches later)
    ↓
Sales Order (source of truth for customer identity)
    ↓
Customer (created/updated from Sales Order ship-to via PDF import)
```

**Key Change:** ShipStation sync now:
1. Tries to find existing Sales Order by `order_number` FIRST
2. If found, uses `sales_order.customer_id` (canonical)
3. If not found, tries to find EXISTING customer (does NOT create new ones)
4. If no customer found, distribution has `customer_id=NULL`
5. Admin matches unmatched distributions via PDF import or manual match

---

## Files Changed

### Backend

| File | Changes |
|------|---------|
| `app/eqms/modules/shipstation_sync/service.py` | P0-1: Renamed `_get_customer_from_ship_to()` to `_get_existing_customer_from_ship_to()`, removed customer creation, added SO matching first |
| `app/eqms/modules/rep_traceability/admin.py` | P0-2: Updated `sales_orders_import_pdf_bulk()` to split pages; P1-2: Added `sales_orders_unmatched_pdfs()` route |
| `app/eqms/modules/customer_profiles/utils.py` | P1-1: Added comprehensive docstring to `canonical_customer_key()` |

### Frontend

| File | Changes |
|------|---------|
| `app/eqms/templates/admin/sales_orders/import.html` | P2-1: Removed "2025" reference |
| `app/eqms/templates/admin/sales_orders/list.html` | P1-2: Added "Unmatched PDFs" button |
| `app/eqms/templates/admin/sales_orders/unmatched_pdfs.html` | P1-2: **NEW** - Lists unmatched PDFs |
| `app/eqms/templates/admin/distribution_log/edit.html` | P2-2: Hid deprecated `customer_name` field |

### Tests

| File | Purpose |
|------|---------|
| `tests/test_customer_key.py` | P1-1: **NEW** - Unit tests for customer key canonicalization |

---

## Database Changes

**None** — All changes are logic/UI fixes.

---

## Remaining Known Issues

1. **Empty `legacy/` directory:** Could not delete due to filesystem permissions. Not tracked by git, so no impact. Can be deleted manually.

2. **Existing ShipStation distributions without SO match:** Distributions created before this fix may have `customer_id` from ShipStation-derived customer (not canonical). Run `scripts/rebuild_customers_from_sales_orders.py --execute` to fix.

3. **SO-less distributions:** ShipStation distributions without a matching Sales Order will now have `customer_id=NULL` until matched. This is intentional — admin should import Sales Orders via PDF to establish canonical customer identity.

---

## Verification Steps (Production)

### Test 1: ShipStation Sync Creates Distributions Only

1. Go to **ShipStation** → **Run Sync**
2. Check Distribution Log for new entries
3. **Expected:** Entries have `sales_order_id` if matching SO exists (from PDF import)
4. **Expected:** Entries without matching SO have `customer_id=NULL` or linked to existing customer
5. **Expected:** No new customers created from ShipStation sync

**SQL Verification:**
```sql
-- Check if any distributions have customer_id but no sales_order_id
-- (These should be rare after the fix)
SELECT COUNT(*) FROM distribution_log_entries 
WHERE source = 'shipstation' 
  AND customer_id IS NOT NULL 
  AND sales_order_id IS NULL;

-- Check unmatched distributions
SELECT COUNT(*) FROM distribution_log_entries 
WHERE source = 'shipstation' 
  AND sales_order_id IS NULL;
```

### Test 2: Bulk PDF Import Splits Pages

1. Go to **Sales Orders** → **Import PDF**
2. Upload multi-page PDF via "Bulk Upload PDFs"
3. **Expected:** Flash message shows "X pages processed, Y orders..."
4. Open created Sales Order → Check attachments
5. **Expected:** PDF attachments named `*_page_N.pdf` (individual pages)
6. Download attachment → **Expected:** Single-page PDF

### Test 3: Unmatched PDFs Visible

1. Upload bulk PDF with some unparseable pages
2. Go to **Sales Orders** → Click **Unmatched PDFs** button
3. **Expected:** List of unmatched/unparsed PDFs with download links
4. Click download → **Expected:** PDF downloads

### Test 4: UI Polish

1. Go to **Sales Orders** → **Import PDF**
2. **Expected:** No "2025" in page text
3. Go to **Distribution Log** → **Edit** any entry
4. **Expected:** No "Customer Name (deprecated)" field visible
5. Save form → **Expected:** Still works

### Test 5: Customer Identity from Sales Orders

1. Import Sales Order via PDF (creates customer)
2. Run ShipStation sync with matching order
3. Check distribution → **Expected:** `customer_id` matches Sales Order's customer
4. Check customer → **Expected:** Customer data from Sales Order ship-to (canonical)

---

## Customer Key Edge Cases (Documented)

### Abbreviations (NOT Normalized)

| Input 1 | Input 2 | Same Key? |
|---------|---------|-----------|
| "123 Main St" | "123 Main Street" | ❌ No |
| "123 Oak Ave" | "123 Oak Avenue" | ❌ No |

**Reason:** Abbreviation normalization requires complex heuristics. Current behavior is documented.

### Business Suffixes (Normalized)

| Input 1 | Input 2 | Same Key? |
|---------|---------|-----------|
| "Hospital A" | "Hospital A, Inc." | ✅ Yes |
| "Hospital A" | "Hospital A LLC" | ✅ Yes |
| "Hospital A" | "Hospital A Corp" | ✅ Yes |

**Reason:** Suffixes are stripped before key generation.

### PO Box

| Input | Key |
|-------|-----|
| "Hospital PO Box 123" | "HOSPITALPOBOX123" |

**Reason:** PO Box is part of the name, so it's included.

---

## Commit Messages

```
Phase 2: Canonical pipeline enforcement + UI fixes

P0-1: ShipStation sync no longer creates customers
- Renamed _get_customer_from_ship_to → _get_existing_customer_from_ship_to
- Sync now tries to match existing SO first
- Customer comes from SO (canonical), not ShipStation ship_to
- Unmatched distributions have customer_id=NULL

P0-2: Bulk PDF import now splits pages
- Updated sales_orders_import_pdf_bulk() to use split_pdf_into_pages()
- Each page stored as separate attachment
- Auto-matches existing distributions by order_number

P1-1: Customer key documentation + tests
- Added comprehensive docstring to canonical_customer_key()
- Created tests/test_customer_key.py with edge case coverage

P1-2: Unmatched PDFs UI
- Added /admin/sales-orders/unmatched-pdfs route
- Created unmatched_pdfs.html template
- Added link in Sales Orders list

P2-1: Remove "2025" from import page
P2-2: Hide deprecated customer_name field
P2-3: Delete empty legacy/ directory (attempted)
```

---

## Deployment Notes

### DigitalOcean

- **Run Command:** `python scripts/start.py` (unchanged)
- **No migrations required** (logic changes only)

### Post-Deploy Actions

1. **Verify canonical pipeline:**
   ```bash
   # Check ShipStation distributions with customer but no SO
   python -c "
   from app.eqms import create_app
   app = create_app()
   with app.app_context():
       from app.eqms.db import db_session
       from app.eqms.modules.rep_traceability.models import DistributionLogEntry
       s = db_session()
       count = s.query(DistributionLogEntry).filter(
           DistributionLogEntry.source == 'shipstation',
           DistributionLogEntry.customer_id != None,
           DistributionLogEntry.sales_order_id == None
       ).count()
       print(f'Distributions with customer but no SO: {count}')
   "
   ```

2. **Run customer rebuild (optional, for historical data):**
   ```bash
   python scripts/rebuild_customers_from_sales_orders.py --dry-run
   python scripts/rebuild_customers_from_sales_orders.py --execute
   ```

---

**End of Implementation Notes**
