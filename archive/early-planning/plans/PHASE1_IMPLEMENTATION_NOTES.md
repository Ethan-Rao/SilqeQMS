# Phase 1 Implementation Notes

**Implemented:** 2026-01-26  
**Status:** Complete

---

## Summary

Phase 1 implements data integrity fixes and customer rebuild from Sales Orders:

1. **Bulk PDF Splitting** — Multi-page PDFs are split into individual pages, each stored as a separate attachment
2. **Customer Rebuild** — Customers derived from Sales Order ship-to data (not ShipStation)
3. **Distribution-SO Matching** — Automatic matching by order_number on creation
4. **Per-page PDF Downloads** — Each page downloadable from Sales Order detail and Distribution details
5. **UI Cleanup** — Removed unprofessional "Source of truth..." text

---

## Files Changed

### Backend

| File | Changes |
|------|---------|
| `app/eqms/modules/rep_traceability/parsers/pdf.py` | Added `split_pdf_into_pages()` function using PyPDF2 |
| `app/eqms/modules/rep_traceability/admin.py` | Updated `sales_orders_import_pdf_post()` to split bulk PDFs and store per-page attachments |
| `app/eqms/modules/customer_profiles/utils.py` | Added `compute_customer_key_from_sales_order()` function |
| `requirements.txt` | Added `PyPDF2` dependency |

### Frontend

| File | Changes |
|------|---------|
| `app/eqms/templates/admin/sales_orders/list.html` | Removed "Source of truth for customer orders and distributions." text |

### Scripts

| File | Purpose |
|------|---------|
| `scripts/rebuild_customers_from_sales_orders.py` | **NEW** - Rebuild customer database from Sales Orders |

---

## Database Migrations

**No schema changes required.** All relationships already support:

- One SalesOrder → Many DistributionLogEntry (via `sales_order_id` FK)
- One SalesOrder → Many OrderPdfAttachment (via `sales_order_id` FK)
- One Customer → Many SalesOrder (via `customer_id` FK)

---

## How to Run the Rebuild Job

### Customer Rebuild from Sales Orders

This script rebuilds the customer database using Sales Orders as the source of truth:

```bash
# Preview changes (no modifications)
python scripts/rebuild_customers_from_sales_orders.py --dry-run

# Apply changes
python scripts/rebuild_customers_from_sales_orders.py --execute
```

**What it does:**
1. For each Sales Order, computes `company_key` from ship-to data
2. Finds or creates customer with that key
3. Updates customer fields if SO/distribution data is more complete
4. Updates `sales_orders.customer_id` if changed
5. Updates `distribution_log_entries.customer_id` via linked SO
6. Merges duplicate customers with same `company_key`

**Safe to run multiple times** — idempotent, only updates when data is more complete.

### Other Useful Scripts

```bash
# Match existing distributions to sales orders (from previous commit)
python scripts/backfill_sales_order_matching.py --dry-run
python scripts/backfill_sales_order_matching.py --execute

# Refresh customer data from existing sales orders (previous commit)
python scripts/refresh_customers_from_sales_orders.py --dry-run
python scripts/refresh_customers_from_sales_orders.py --execute
```

---

## Manual Verification Steps

### Test 1: Bulk PDF Upload + Splitting

1. Go to **Sales Orders** → Click **"Import PDF"**
2. Upload bulk PDF (multiple pages)
3. **Expected:** Flash message shows "X pages processed, Y orders, Z lines, W distributions"
4. Go to a created Sales Order detail page
5. **Expected:** See PDF attachment(s) named `*_page_N.pdf`
6. Click download → **Expected:** PDF is single page (not entire bulk file)

### Test 2: Distribution-SO Matching

1. Go to **Distribution Log** → Find entry with `order_number` matching a Sales Order
2. **Expected:** Entry shows no ⚠ icon (matched)
3. Click "Details" → **Expected:** Modal shows linked Sales Order
4. **Expected:** Modal shows "Attachments" section with PDF download links
5. Click download → **Expected:** PDF downloads

### Test 3: Customer Rebuild

1. Run rebuild script:
   ```bash
   python scripts/rebuild_customers_from_sales_orders.py --dry-run
   ```
2. Review output for changes
3. Run with `--execute` to apply
4. Go to **Customer Database** → Check a customer with multiple Sales Orders
5. **Expected:** Customer shows as single record (no duplicates from ShipStation)
6. Open customer detail → **Expected:** Order history shows all SOs

### Test 4: Unmatched Pages

1. Upload bulk PDF with some pages that don't parse
2. Go to **Sales Orders** → Check attachments
3. **Expected:** Unmatched pages stored with `pdf_type = "unmatched"`
4. **Expected:** Unmatched PDFs are downloadable

### Test 5: No UI Regressions

1. Navigate to `/admin/sales-orders`
2. **Expected:** No "Source of truth..." text appears
3. **Expected:** All modals have dark backgrounds, text is readable
4. **Expected:** All routes work without errors

---

## Data Flow (Verified)

```
ShipStation API
      ↓
Distribution Log (clean, deduplicated)
      ↓
Match to Sales Order (by order_number)
      ↓
Customers derived from linked SO ship-to data
      ↓
Sales Dashboard aggregates from Distribution Log + linked SOs
```

**Key principle:** Sales Orders are the source of truth for customer identity.

---

## Repo Cleanup Completed

From `docs/plans/REPO_CLEANUP_PHASE1.md`:

| Item | Status |
|------|--------|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/` folder | ✅ Deleted (previous commit) |
| All scripts in `scripts/` | ✅ Kept (all in use) |
| All templates | ✅ Kept (all in use) |
| All models | ✅ Kept (all in use) |
| Canonical entrypoints | ✅ Verified (`wsgi.py`, `start.py`, `release.py`) |

---

## Dependencies Added

| Package | Version | Purpose |
|---------|---------|---------|
| `PyPDF2` | Latest | PDF page splitting for bulk imports |

Already in `requirements.txt`:
- `pdfplumber` — PDF text/table extraction
- `PyPDF2` — PDF page manipulation (splitting)

---

## Known Limitations

1. **PDF Splitting Quality:** PyPDF2 preserves page content but may not preserve all PDF features (annotations, forms). For sales order PDFs (simple content), this is acceptable.

2. **Customer Rebuild Heuristics:** The `compute_customer_key_from_sales_order()` function uses a priority-based algorithm. If ship-to data is incomplete, matching may be less accurate.

3. **One-to-Many Matching:** If multiple distributions have the same `order_number`, they all link to the same Sales Order. This is correct behavior.

---

## Rollback Plan

If issues arise:

1. **PDF Splitting:** Revert `admin.py` changes; bulk PDFs will be stored as single files again
2. **Customer Rebuild:** Run rebuild script with `--dry-run` first; changes are additive (no deletions except duplicate merging)
3. **UI Changes:** Revert template changes

All changes are localized and reversible.

---

**End of Implementation Notes**
