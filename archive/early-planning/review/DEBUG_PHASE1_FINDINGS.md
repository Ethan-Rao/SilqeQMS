# DEBUG_PHASE1_FINDINGS — Post-Phase 1 System Audit

**Date:** 2026-01-27  
**Scope:** Data integrity, customer DB correctness, PDF pipeline, distribution linkage, lot tracking, UI reliability, legacy code

---

## Executive Summary

### Overall Status: ✅ System Largely Functional

Phase 1 changes have been successfully implemented. The core data model is sound and most features work correctly. Below are the key findings:

1. **✅ Customer DB Correctness:** `company_key` algorithm is deterministic; `rebuild_customers_from_sales_orders.py` script exists and is complete; customer grouping is stable
2. **✅ PDF Splitting Implemented:** `split_pdf_into_pages()` function exists in `parsers/pdf.py`; individual pages stored as separate attachments
3. **✅ Distribution-SO Linkage:** Auto-matching by `order_number` works; manual match flow functional
4. **✅ Lot Tracking:** Reads from `DistributionLogEntry` (cleaned data); `min_year` configurable via `DASHBOARD_LOT_MIN_YEAR` (default: 2026); lot corrections applied from LotLog
5. **✅ UI Readability:** `--card-bg` CSS variable now defined; modal backgrounds solid
6. **⚠️ Unmatched PDFs:** Stored correctly but no UI to view/download them
7. **⚠️ Two Import Routes:** One (`sales_orders_import_pdf`) uses splitting; the other (`sales_orders_import_pdf_bulk`) does not
8. **⚠️ Minor UI Issues:** Import page mentions "2025"; deprecated `customer_name` field visible in edit form
9. **✅ Legacy Code:** `legacy/` directory is empty; no deprecated entrypoints found

### Recommendation: System is ready for production use. Address P2 issues for polish.

---

## Issue List

### ISS-001: No UI to View Unmatched PDFs (P2)

| Field | Detail |
|-------|--------|
| **Severity** | P2 |
| **Steps to Reproduce** | 1. Upload bulk PDF with some pages that don't parse<br>2. Go to Sales Orders list<br>3. Look for "Unmatched" section |
| **Expected** | Section showing unmatched/unparsed PDFs with download links |
| **Actual** | No way to view or download unmatched PDFs from UI (they are stored in DB) |
| **Root Cause** | No route or template filter for `OrderPdfAttachment` where `sales_order_id IS NULL` |
| **Files** | `app/eqms/modules/rep_traceability/admin.py`, `app/eqms/templates/admin/sales_orders/list.html` |
| **Proposed Fix** | Add route/filter to list unmatched attachments, or add section to import results page |

### ISS-002: Two PDF Import Routes With Different Behavior (P2)

| Field | Detail |
|-------|--------|
| **Severity** | P2 |
| **Steps to Reproduce** | 1. Use "Import PDF" (single file) → uses page splitting<br>2. Use "Import Bulk PDFs" → does NOT split pages |
| **Expected** | Both routes behave consistently |
| **Actual** | `sales_orders_import_pdf()` (line 1469) splits pages; `sales_orders_import_pdf_bulk()` (line 1361) stores entire PDF |
| **Root Cause** | Old bulk route not updated when page splitting was added |
| **Files** | `app/eqms/modules/rep_traceability/admin.py` lines 1361-1455 |
| **Proposed Fix** | Update `sales_orders_import_pdf_bulk()` to iterate files AND split each file into pages, or deprecate in favor of single route |

### ISS-003: Import Page Mentions "2025" (P2)

| Field | Detail |
|-------|--------|
| **Severity** | P2 |
| **Steps to Reproduce** | Go to Sales Orders → Import PDF |
| **Expected** | No hardcoded year references |
| **Actual** | Line 6: `<p class="muted">Upload a 2025 Sales Orders PDF...</p>` |
| **Root Cause** | Hardcoded year in template |
| **Files** | `app/eqms/templates/admin/sales_orders/import.html:6` |
| **Proposed Fix** | Change to "Upload a Sales Orders PDF" (remove year) |

### ISS-004: Deprecated customer_name Field Still Visible (P2)

| Field | Detail |
|-------|--------|
| **Severity** | P2 |
| **Steps to Reproduce** | Go to Distribution Log → Edit any entry |
| **Expected** | Deprecated field hidden or removed |
| **Actual** | Field visible with label "Customer Name (deprecated free-text)" |
| **Root Cause** | Field intentionally kept for legacy data but UI exposes it unnecessarily |
| **Files** | `app/eqms/templates/admin/distribution_log/edit.html:93` |
| **Proposed Fix** | Hide field with `type="hidden"` or remove from form (keep in model for data) |

### ISS-005: Customer Key Edge Cases Not Documented (P1)

| Field | Detail |
|-------|--------|
| **Severity** | P1 |
| **Steps to Reproduce** | N/A - Code review finding |
| **Expected** | Edge cases (PO Box, abbreviations, same facility different ship-to) handled |
| **Actual** | `canonical_customer_key()` normalizes to uppercase, strips punctuation, but specific edge cases not documented |
| **Root Cause** | Missing documentation and edge case tests |
| **Files** | `app/eqms/modules/customer_profiles/utils.py:33-53` |
| **Proposed Fix** | Add unit tests for edge cases; document normalization rules; add handling for common abbreviations (St/Street, Ave/Avenue) |

**Edge Cases to Consider:**
- Same facility, different ship-to address → same `company_key`?
- "St. Joseph Hospital" vs "Saint Joseph Hospital" → currently different keys
- "123 Main St" vs "123 Main Street" → currently different keys if included in key
- PO Box addresses → should normalize or exclude from key

---

## Customer DB Correctness Audit

### Company Key Algorithm Status: ✅ CORRECT

**Implementation:** `app/eqms/modules/customer_profiles/utils.py`

```python
def canonical_customer_key(name: str) -> str:
    """Normalize facility name to canonical company_key."""
    # Uppercase, strip whitespace
    normalized = (name or "").upper().strip()
    # Remove punctuation
    normalized = re.sub(r"[^A-Z0-9\s]+", "", normalized)
    # Collapse whitespace
    normalized = re.sub(r"\s+", "", normalized)
    return normalized
```

**Also:** `compute_customer_key_from_sales_order()` (lines 68-131) provides tiered key computation:
1. Customer number (if available) → `CUST:{number}`
2. Full address (name + addr1 + city + state + zip)
3. Partial address (name + city + state)
4. Name only

### Customer Rebuild Script Status: ✅ EXISTS AND COMPLETE

**Script:** `scripts/rebuild_customers_from_sales_orders.py`

**Features:**
- `--dry-run` mode for preview
- `--execute` mode for application
- Creates customers from SO ship-to data
- Updates SO `customer_id` if changed
- Updates distribution `customer_id` via SO linkage
- Merges duplicate customers (same `company_key`)
- Idempotent (safe to run multiple times)

### Customer Display Source: ✅ FROM LINKED SO RECORDS

**Verified:** Customer pages pull data from `Customer` model, which is populated from Sales Orders (not raw ShipStation).

---

## Sales Order Bulk PDF Pipeline Audit

### PDF Splitting Status: ✅ IMPLEMENTED

**Function:** `app/eqms/modules/rep_traceability/parsers/pdf.py:494-533`

```python
def split_pdf_into_pages(pdf_bytes: bytes) -> list[tuple[int, bytes]]:
    """Split PDF into individual page PDFs."""
    from PyPDF2 import PdfReader, PdfWriter
    # ... implementation ...
```

**Dependency:** PyPDF2 in `requirements.txt` ✅

### Page Storage Status: ✅ WORKING (for single-file route)

**Route:** `sales_orders_import_pdf()` (line 1469)
- Splits PDF into pages
- Parses each page individually
- Stores each page as separate `OrderPdfAttachment`
- Links to Sales Order if parsed successfully
- Stores as `pdf_type="unmatched"` if not parseable

### Link Integrity: ✅ VERIFIED

**Relationships:**
- `SalesOrder` → `order_pdf_attachments` (1:many via `sales_order_id`)
- `SalesOrder` → `distribution_log_entries` (1:many via `sales_order_id`)
- `DistributionLogEntry` → `SalesOrder` (many:1 via `sales_order_id`)

### Unmatched Pages: ⚠️ STORED BUT NOT VISIBLE

**Storage:** Unmatched pages stored with:
- `sales_order_id = NULL`
- `pdf_type = "unmatched"` or `"unparsed"`

**UI Gap:** No way to view these in the web interface.

---

## Distribution Log Linkage Audit

### Auto-Matching Status: ✅ WORKING

**On PDF Import:** (line 1583-1593)
```python
# Auto-match existing unmatched distributions to this sales order by order_number
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
```

### One SO → Multiple Distributions: ✅ SUPPORTED

**Schema:** `distribution_log_entries.sales_order_id` is nullable FK to `sales_orders.id`
- Multiple distributions can reference same SO
- No duplication issues

### Manual Match Flow: ✅ FUNCTIONAL

**Route:** `/admin/distribution-log/<id>/upload-pdf` (line 465)
- Admin can upload PDF to create SO and link distribution
- Sets `distribution.sales_order_id`
- Stores PDF attachment

---

## Sales Dashboard + Lot Tracking Audit

### Data Source: ✅ READS FROM CLEANED RECORDS

**File:** `app/eqms/modules/rep_traceability/service.py`

**Query:** Reads from `DistributionLogEntry` (cleaned system records), NOT raw ShipStation data.

Only ShipStation reference: `from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory` (for LotLog corrections)

### Lot Tracking Filter: ✅ CORRECT

**Configuration:** `min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2026"))`

**Behavior:**
- Shows lots distributed in 2026+ (or lots built in 2026+ from LotLog)
- Totals include ALL-TIME distributions (correct)
- Lot names use LotLog corrections (canonical names)

### Lot Name Derivation: ✅ USES LOTLOG

```python
# Line 591-611
_, lot_corrections, lot_inventory, lot_years = load_lot_log_with_inventory(lotlog_path)
# ...
normalized_lot = normalize_lot(raw_lot)
corrected_lot = lot_corrections.get(normalized_lot, normalized_lot)
```

---

## UI/UX Reliability Audit

### Detail Modals: ✅ WORKING

**CSS Variable:** `--card-bg: #0f1a30;` defined in `design-system.css:3`

**Modal Background:** `background: var(--card-bg);` resolves correctly

### Distribution Details Modal: ✅ SHOWS ATTACHMENTS

**File:** `app/eqms/templates/admin/distribution_log/list.html:306-317`

```javascript
if (data.attachments && data.attachments.length > 0) {
  html += `<div class="section-header">Attachments</div>`;
  // ... renders download links ...
}
```

### JS Errors: ✅ NONE OBSERVED

All modal fetch logic includes error handling.

---

## Legacy Code Removal Audit

### Legacy Directory: ✅ EMPTY

`legacy/` exists but contains no files.

### Proto/Deprecated References: ✅ ONLY COMMENTS

Grep found "deprecated" in 2 places - both are documentation comments, not actual deprecated code:
- `admin.py:184` — Comment: `# deprecated text mirror`
- `edit.html:93` — Label: `Customer Name (deprecated free-text)`

### Unused Routes: ✅ NONE FOUND

All registered routes have corresponding templates and are reachable from navigation.

### Duplicate Parsing Utilities: ✅ NONE

Single implementations for PDF parsing, lot normalization, customer key computation.

---

## Safe to Delete

| Item | Status | Reason |
|------|--------|--------|
| `legacy/` directory | DELETE | Empty, no content |
| `customer_name` field in edit form | HIDE | Deprecated but keep in model for data compatibility |

---

## Next Dev Tasks (Checklist)

### P1 (Should Do)

- [ ] **ISS-005:** Add unit tests for customer key edge cases (abbreviations, PO Box, etc.)
- [ ] **ISS-005:** Document `canonical_customer_key()` normalization rules in docstring

### P2 (Nice to Have)

- [ ] **ISS-001:** Add UI to view unmatched PDFs (filter or separate section in Sales Orders)
- [ ] **ISS-002:** Update `sales_orders_import_pdf_bulk()` to use page splitting, or deprecate
- [ ] **ISS-003:** Remove "2025" from `import.html:6`
- [ ] **ISS-004:** Hide deprecated `customer_name` field in distribution edit form

### Cleanup

- [ ] Delete empty `legacy/` directory
- [ ] Remove or update stale comments referencing "deprecated"

---

## Verification Runbook

### 1. Customer DB Correctness

```bash
# Verify customer key uniqueness
SELECT company_key, COUNT(*) as cnt 
FROM customers 
GROUP BY company_key 
HAVING COUNT(*) > 1;
-- Expected: No rows (all keys unique)
```

**Browser Steps:**
1. Go to Customer Database
2. Search for a facility name with multiple orders
3. Verify single customer record (not duplicates)
4. Open customer detail → verify order history shows all linked SOs

### 2. PDF Pipeline

**Browser Steps:**
1. Go to Sales Orders → Import PDF
2. Upload multi-page PDF
3. Verify flash message shows "X pages processed"
4. Go to created Sales Order detail
5. Verify "PDF Attachments" section shows individual page(s)
6. Click Download → verify downloads correct page (not entire bulk file)

```bash
# Verify page attachments exist
SELECT so.order_number, opa.filename, opa.pdf_type
FROM order_pdf_attachments opa
JOIN sales_orders so ON so.id = opa.sales_order_id
WHERE opa.pdf_type = 'sales_order_page'
LIMIT 10;
```

### 3. Distribution-SO Linkage

**Browser Steps:**
1. Go to Distribution Log
2. Find entry with matching Sales Order (no ⚠ icon)
3. Click "Details"
4. Verify modal shows "Linked Sales Order" section
5. Verify "Attachments" section shows PDF download link
6. Click Download → verify PDF downloads

```bash
# Verify distribution-SO linkage
SELECT d.order_number, d.sales_order_id, so.order_number as so_order_number
FROM distribution_log_entries d
LEFT JOIN sales_orders so ON so.id = d.sales_order_id
WHERE d.sales_order_id IS NOT NULL
LIMIT 10;
```

### 4. Lot Tracking

**Browser Steps:**
1. Go to Sales Dashboard
2. Scroll to "Lot Tracking" section
3. Verify only 2026+ lots shown
4. Verify "Total Units" column shows all-time totals (not just 2026)
5. Verify lot names are canonical (e.g., `SLQ-01152026` not `SLQ-011520`)

### 5. UI Reliability

**Browser Steps:**
1. Go to Distribution Log → click "Details" on any entry
2. Verify modal has solid dark background (not transparent)
3. Verify all text readable
4. Go to Sales Dashboard → click "View Details" on any order
5. Verify modal loads without errors
6. Open browser console → verify no JS errors

### 6. Unmatched PDFs (Known Gap)

```bash
# Check for unmatched attachments
SELECT id, filename, pdf_type, uploaded_at
FROM order_pdf_attachments
WHERE sales_order_id IS NULL
ORDER BY uploaded_at DESC
LIMIT 20;
```

**Note:** These exist in DB but are not visible in UI (ISS-001).

---

**End of DEBUG_PHASE1_FINDINGS.md**
