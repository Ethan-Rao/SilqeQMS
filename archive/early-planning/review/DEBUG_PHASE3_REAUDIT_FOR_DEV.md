# DEBUG_PHASE3_REAUDIT_FOR_DEV — Full System Verification

**Date:** 2026-01-27  
**Scope:** Phase 1–3 regression validation, endpoint verification, storage robustness, data pipeline correctness

---

## 1. Correct the Verification Model (Mandatory)

### A) DigitalOcean Console Reality

**CRITICAL CLARIFICATION:** The DigitalOcean Console is a **shell** (bash/sh), not an HTTP client.

| ❌ Invalid | ✅ Valid |
|-----------|---------|
| `GET /admin/diagnostics/storage` | `curl -i https://yourapp.com/admin/diagnostics/storage` |
| Direct HTTP verbs | Browser navigation while logged in |

**The previous audit incorrectly presented HTTP verbs as console commands.** This caused confusion—the commands did nothing because `GET` is not a shell command.

### B) Two Verification Paths

#### Path 1: Browser Verification (RECOMMENDED for Ethan)

1. Log in as admin at `https://yourapp.com/auth/login`
2. Navigate directly to URLs in the browser address bar
3. For JSON endpoints, browser will display raw JSON
4. For POST endpoints, use browser dev tools or a simple HTML form

#### Path 2: curl Verification (Developer Reference Only)

```bash
# First, get session cookie by logging in via browser
# Then use cookie for curl requests:

curl -i -H "Cookie: session=YOUR_SESSION_COOKIE" https://yourapp.com/admin/diagnostics/storage

# For POST with JSON:
curl -X POST -H "Cookie: session=..." -H "Content-Type: application/json" \
  -d '{"confirm": true}' https://yourapp.com/admin/maintenance/customers/delete-zero-orders
```

**Note:** curl requires session cookie extracted from browser. For Ethan, browser-first is simpler.

---

## 2. Phase 1–3 Regression Matrix

### Storage / PDFs

| Workflow | Status | Evidence | Browser Verification |
|----------|--------|----------|---------------------|
| Storage diagnostics endpoint exists | ✅ PASS | `admin.py:230-267` | Navigate to `/admin/diagnostics/storage` |
| Diagnostics does not expose secrets | ✅ PASS | Only shows `access_key_prefix` (first 4 chars) | Verify JSON contains `"access_key_prefix": "DO00..."` |
| Diagnostics tests actual bucket access | ✅ PASS | Uses `head_bucket()` call | Verify `"accessible": true` in response |
| Startup storage health check logs | ✅ PASS | `__init__.py:62-79` logs PASSED/ERROR | Check DO App logs for "Storage health check PASSED" or "STORAGE CONFIG ERROR" |
| Bulk SO PDF import | ⚠️ PARTIAL | Route exists; storage errors swallowed | Go to Sales Orders → Import PDF → Upload file |
| Single SO PDF import | ⚠️ PARTIAL | Route exists; same error handling issue | Same as above (single file mode) |
| SO upload from Distribution details | ⚠️ PARTIAL | `admin.py:479-676` | Distribution Log → Details → "Upload PDF to Match" |
| Label upload from Distribution details | ⚠️ PARTIAL | `admin.py:685-728` | Distribution Log → Edit → Upload Label |
| View/download attachments | ✅ PASS | `admin.py:1454-1473` | Sales Order detail page → Attachments section → Download |
| Unmatched PDFs page | ✅ PASS | `admin.py:1777-1808` | Sales Orders → "Unmatched PDFs" button |

**Issue Found:** Storage errors during import are caught with `except Exception: pass` (lines 1548, 1569, 1593) which silently swallows errors. Import shows "success" even if all PDFs failed to store.

### Customer Cleanup Endpoints

| Endpoint | Status | Evidence | Browser Verification |
|----------|--------|----------|---------------------|
| `GET /admin/maintenance/customers/duplicates` | ✅ EXISTS | `admin.py:270-317` | Navigate to URL, see JSON |
| `GET /admin/maintenance/customers/zero-orders` | ✅ EXISTS | `admin.py:320-354` | Navigate to URL, see JSON |
| `POST /admin/maintenance/customers/merge` | ✅ EXISTS | `admin.py:357-449` | Requires JSON body via fetch/curl |
| `POST /admin/maintenance/customers/delete-zero-orders` | ✅ EXISTS | `admin.py:452-528` | Requires JSON body via fetch/curl |
| RBAC protection (admin.view/edit) | ✅ PASS | All use `@require_permission()` | Verify 403 when not logged in |
| CSRF handling | ✅ HANDLED | JSON endpoints exempt from CSRF (API-style) | N/A |
| Confirmation required for destructive actions | ✅ PASS | merge requires `confirm_token`, delete requires `{"confirm": true}` | See response prompts |

### Pipeline Enforcement

| Invariant | Status | Evidence | Verification |
|-----------|--------|----------|--------------|
| ShipStation sync never creates customers | ✅ PASS | `shipstation_sync/service.py:46-64` — `_get_existing_customer_from_ship_to()` only looks up, never creates | Code review; verified comment |
| Customer stats filter by matched SO | ✅ PASS | `customer_profiles/admin.py:72-74` includes `sales_order_id.isnot(None)` | Code review |
| Dashboard filters by matched SO | ✅ PASS | `service.py:550, 569, 581, 617` all filter matched | Code review |
| Unmatched distributions don't affect dashboard | ✅ PASS | All queries filter `sales_order_id.isnot(None)` | Code review |

### UI Reliability

| Element | Status | Evidence | Verification |
|---------|--------|----------|--------------|
| Distribution details modal | ✅ PASS | `distribution_log/list.html` | Click "Details" on any entry |
| Solid background on modals | ✅ PASS | `design-system.css:3` defines `--card-bg: #0f1a30` | Visual inspection |
| Import pages error handling | ⚠️ PARTIAL | Storage errors logged but user sees "success" with error count | Test with broken storage |

---

## 3. P0: Storage Failure Robustness

### Environment Variables Used

**File:** `app/eqms/storage.py:87-96`

```python
backend = config.get("STORAGE_BACKEND")  # "s3" or "local"
endpoint = config.get("S3_ENDPOINT")      # e.g., "sfo3.digitaloceanspaces.com"
region = config.get("S3_REGION")          # e.g., "sfo3"
bucket = config.get("S3_BUCKET")          # e.g., "raoeqms-files"
access_key_id = config.get("S3_ACCESS_KEY_ID")
secret_access_key = config.get("S3_SECRET_ACCESS_KEY")
```

### Diagnostics Endpoint Verification

**Confirmed Working:** `/admin/diagnostics/storage` (`admin.py:230-267`)

- ✅ Uses `head_bucket()` to verify actual access (not just configured)
- ✅ Does NOT expose secrets (only `access_key_prefix` = first 4 chars)
- ✅ Returns clear `accessible: true/false`
- ✅ Returns error message if access fails

**Expected Response (healthy):**
```json
{
  "backend": "s3",
  "configured": true,
  "accessible": true,
  "error": null,
  "details": {
    "endpoint": "sfo3.digitaloceanspaces.com",
    "region": "sfo3",
    "bucket": "raoeqms-files",
    "access_key_prefix": "DO00..."
  }
}
```

### Startup Health Check

**File:** `app/eqms/__init__.py:62-79`

- ✅ Checks for missing env vars → logs "STORAGE CONFIG ERROR: Missing required S3 env vars: ..."
- ✅ Attempts `head_bucket()` → logs "Storage health check PASSED: S3 bucket 'X' accessible"
- ✅ On failure → logs "STORAGE CONFIG ERROR: Cannot access S3 bucket: ..."

**Where to verify:** DigitalOcean App Platform → Runtime Logs

### Issue: Silent Error Swallowing in Import

**Problem Location:** `admin.py:1548, 1569, 1593`

```python
try:
    _store_pdf_attachment(...)
except Exception:
    pass  # ← ERROR SILENTLY SWALLOWED
```

**Impact:** When storage is broken, PDFs fail to store but import continues and shows "success" message. User has no clear indication that attachments weren't saved.

**Proposed Fix:**

```python
# Replace silent catch with explicit storage error tracking
storage_errors = 0

try:
    _store_pdf_attachment(...)
except Exception as e:
    current_app.logger.error(f"Storage error storing {filename}: {e}")
    storage_errors += 1

# At end of import, if storage_errors > 0:
if storage_errors > 0:
    flash(f"WARNING: {storage_errors} PDFs failed to store. Storage may be misconfigured. Check /admin/diagnostics/storage", "danger")
```

---

## 4. Customer DB Correctness and Cleanup

### Customer Creation Paths

| Path | Creates Customer? | Status | Notes |
|------|-------------------|--------|-------|
| ShipStation sync | NO | ✅ CORRECT | `_get_existing_customer_from_ship_to()` only looks up |
| PDF import | YES | ✅ CORRECT | Creates SO + customer together (pipeline correct) |
| CSV distribution import | YES | ⚠️ LEAK | `admin.py:783` creates customer without SO |
| Manual distribution entry | NO* | ✅ CORRECT | Uses existing customer_id |

**Pipeline Leak:** CSV import (`admin.py:775-796`) calls `find_or_create_customer()` which can create customers without requiring a Sales Order. This violates the canonical pipeline.

**Fix:** Change CSV import to only look up existing customers:

```python
# BEFORE (creates customers):
c = find_or_create_customer(s, facility_name=facility_name, ...)

# AFTER (lookup only):
from app.eqms.modules.customer_profiles.utils import canonical_customer_key
ck = canonical_customer_key(facility_name)
c = s.query(Customer).filter(Customer.company_key == ck).one_or_none()
if not c:
    # Leave customer_id = None; distribution will be unmatched
    r["customer_id"] = None
else:
    r["customer_id"] = c.id
```

### Customer Stats Query

**File:** `customer_profiles/admin.py:66-75`

**Status:** ✅ CORRECT — Already filters by `sales_order_id.isnot(None)`

```python
dist_query = s.query(...).filter(
    DistributionLogEntry.customer_id.isnot(None),
    DistributionLogEntry.sales_order_id.isnot(None),  # ← Correct filter
).group_by(DistributionLogEntry.customer_id)
```

### Cleanup Endpoints Verification

| Endpoint | RBAC | Confirmation | FK Safety | Idempotent |
|----------|------|--------------|-----------|------------|
| `/maintenance/customers/duplicates` | `admin.view` | N/A (read-only) | N/A | ✅ YES |
| `/maintenance/customers/zero-orders` | `admin.view` | N/A (read-only) | N/A | ✅ YES |
| `/maintenance/customers/merge` | `admin.edit` | `confirm_token` required | ✅ Updates FKs before delete | ✅ YES |
| `/maintenance/customers/delete-zero-orders` | `admin.edit` | `{"confirm": true}` required | ✅ Nullifies distribution FKs | ✅ YES |

**FK Safety Verified:**
- `merge` updates `SalesOrder.customer_id`, `DistributionLogEntry.customer_id`, `CustomerNote.customer_id` before deleting duplicate
- `delete-zero-orders` sets `DistributionLogEntry.customer_id = None` before deleting customer

---

## 5. Sales Dashboard Correctness

### Dashboard Query Audit

**File:** `app/eqms/modules/rep_traceability/service.py`

| Query | Filters Matched? | Line | Status |
|-------|------------------|------|--------|
| Lifetime order counts | ✅ YES | 550 | `.filter(DistributionLogEntry.sales_order_id.isnot(None))` |
| Window entries | ✅ YES | 569 | `.filter(DistributionLogEntry.sales_order_id.isnot(None))` |
| All-time total units | ✅ YES | 581 | `.filter(DistributionLogEntry.sales_order_id.isnot(None))` |
| Lot tracking entries | ✅ YES | 617 | `.filter(..., DistributionLogEntry.sales_order_id.isnot(None))` |

**All dashboard queries correctly filter by matched distributions only.**

### Lot Tracking

- ✅ Uses `LotLog.csv` for canonical lot names via `load_lot_log_with_inventory()`
- ✅ `min_year` configurable via `DASHBOARD_LOT_MIN_YEAR` env var (default: 2026)
- ✅ Lot corrections applied from LotLog before aggregation

---

## 6. PDF Import Pipeline: End-to-End

### Bulk PDF Import (`POST /admin/sales-orders/import-pdf-bulk`)

| Step | Status | Evidence |
|------|--------|----------|
| PDF split into pages | ✅ WORKING | `split_pdf_into_pages()` called (line 1555) |
| Per-page parsing | ✅ WORKING | `parse_sales_orders_pdf(page_bytes)` (line 1579) |
| Per-page attachment stored | ⚠️ FRAGILE | `_store_pdf_attachment()` called but errors swallowed |
| Unmatched pages retained | ✅ WORKING | Stored with `pdf_type="unmatched"` |
| Unmatched pages viewable | ✅ WORKING | `/admin/sales-orders/unmatched-pdfs` page |
| Customer created only with SO | ✅ CORRECT | `find_or_create_customer()` called, SO created immediately after |
| Distribution linked to SO | ✅ CORRECT | `sales_order_id=sales_order.id` set on creation |

### Single PDF Import (`POST /admin/sales-orders/import-pdf`)

| Step | Status | Evidence |
|------|--------|----------|
| Uses same logic as bulk | ✅ WORKING | Calls same `_store_pdf_attachment()` |
| Per-page splitting | ✅ WORKING | `split_pdf_into_pages()` called |

### Distribution Detail Upload (`POST /admin/distribution-log/<id>/upload-pdf`)

| Step | Status | Evidence |
|------|--------|----------|
| Route exists | ✅ YES | `admin.py:479-676` |
| Creates/matches SO | ✅ YES | Creates SO and links distribution |
| Storage error handling | ⚠️ FRAGILE | Same issue—errors caught silently |

### Label Upload (`POST /admin/distribution-log/<id>/upload-label`)

| Step | Status | Evidence |
|------|--------|----------|
| Route exists | ✅ YES | `admin.py:685-728` |
| Links to distribution | ✅ YES | `distribution_entry_id=entry_id` |
| Does NOT affect customer/dashboard | ✅ CORRECT | Labels don't trigger customer creation |

---

## 7. Bloat & Legacy Code "Delete/Keep" Matrix

| File/Path | Purpose | Referenced? | Bloat Reason | Risk | Action |
|-----------|---------|-------------|--------------|------|--------|
| `legacy/` | Empty directory | NO | Placeholder from past cleanup | None | **DELETE** |
| `scripts/refresh_customers_from_sales_orders.py` | Refresh customer data | YES (manual) | Overlaps with `rebuild_customers_from_sales_orders.py` | Low | **KEEP** (different purpose) |
| `scripts/dedupe_customers.py` | CLI deduplication | REPLACED | Admin endpoints now handle this | Low | **KEEP** (backup option if web fails) |
| `scripts/cleanup_zero_order_customers.py` | CLI cleanup | REPLACED | Admin endpoints now handle this | Low | **KEEP** (backup) |
| `customer_name` field | Deprecated mirror | YES | Legacy; hidden in UI | Medium | **KEEP** (data compat) |

### Files Confirmed Safe

| File | Status | Reason |
|------|--------|--------|
| No Proto* files found | ✅ CLEAN | `glob_file_search` returned 0 results |
| No duplicate storage handlers | ✅ CLEAN | Single `storage.py` implementation |
| No duplicate parsing utilities | ✅ CLEAN | Single `parsers/pdf.py` |
| No dead routes found | ✅ CLEAN | All routes have corresponding templates |

---

## 8. Developer-Ready Patch List

### P0 Fixes (Critical)

#### P0-1: Fix Silent Storage Error Swallowing

**Files:** `app/eqms/modules/rep_traceability/admin.py`

**Locations:** Lines 1548, 1569, 1593, and any other `except Exception: pass` around `_store_pdf_attachment()`

**Change:**
```python
# Track storage errors
storage_errors = 0

# Replace each:
try:
    _store_pdf_attachment(...)
except Exception:
    pass

# With:
try:
    _store_pdf_attachment(...)
except Exception as e:
    current_app.logger.error(f"Storage error: {e}")
    storage_errors += 1

# At end of route, add:
if storage_errors > 0:
    flash(f"WARNING: {storage_errors} files failed to store. Check /admin/diagnostics/storage", "danger")
```

**Acceptance Criteria:**
- [ ] Storage errors logged with context
- [ ] User sees warning flash if any PDFs failed to store
- [ ] Import still completes for files that did store

**Browser Verification:**
1. Temporarily misconfigure S3 credentials
2. Go to Sales Orders → Import PDF → Upload file
3. Should see warning message about storage failures
4. Check Runtime Logs for error details

#### P0-2: Verify Storage Configuration in Production

**No code change needed.**

**Browser Verification:**
1. Log in as admin
2. Navigate to `/admin/diagnostics/storage`
3. Verify response shows:
   - `"configured": true`
   - `"accessible": true`
   - `"error": null`
4. If not, check DO environment variables

### P1 Fixes (High Priority)

#### P1-1: Fix CSV Import Customer Creation Leak

**File:** `app/eqms/modules/rep_traceability/admin.py`

**Location:** Lines 780-796

**Change:**
```python
# BEFORE:
if facility_name:
    c = find_or_create_customer(s, facility_name=facility_name, ...)
    r["customer_id"] = c.id

# AFTER:
if facility_name:
    from app.eqms.modules.customer_profiles.utils import canonical_customer_key
    ck = canonical_customer_key(facility_name)
    c = s.query(Customer).filter(Customer.company_key == ck).one_or_none()
    r["customer_id"] = c.id if c else None
    # Customer will be created when SO is imported and matched
```

**Acceptance Criteria:**
- [ ] CSV import does not create new customers
- [ ] Distributions import with `customer_id = None` if no existing match
- [ ] Customers only created through PDF/SO import

**Browser Verification:**
1. Import CSV with new facility name not in database
2. Verify distribution created with no customer link
3. Verify no new customer created in Customer Database

### P2 Cleanup (Polish)

#### P2-1: Delete Empty Legacy Directory

**Command:**
```bash
rm -rf legacy/
```

**Verification:** Directory should not exist

#### P2-2: Document Customer Pipeline in Code

**File:** `app/eqms/modules/customer_profiles/service.py`

Add docstring at top:
```python
"""
CANONICAL CUSTOMER PIPELINE
===========================
Customers are created ONLY from Sales Orders (PDF import, manual SO entry).

- ShipStation sync: NEVER creates customers (lookup only)
- CSV distribution import: NEVER creates customers (lookup only)
- PDF import: Creates customer + SO together (correct)
- Manual SO entry: Creates customer + SO together (correct)

This ensures customer database only contains entities with verified order history.
"""
```

---

## 9. Production Verification Runbook (Browser-First)

### Pre-Flight: Verify Storage

1. **Log in** to `https://yourapp.com/auth/login` as admin
2. **Navigate** to `https://yourapp.com/admin/diagnostics/storage`
3. **Verify** JSON response:
   ```json
   {
     "backend": "s3",
     "configured": true,
     "accessible": true,
     "error": null
   }
   ```
4. **If `accessible: false`:** Stop. Fix S3 credentials in DO environment variables first.

### Test 1: Bulk PDF Import

1. Navigate to **Sales Orders** (sidebar)
2. Click **Import PDF**
3. Select a test PDF file (multi-page preferred)
4. Click **Import Bulk PDFs**
5. **Expected:** Flash message shows pages processed, orders created
6. **Verify:** New Sales Order appears in list
7. Click into Sales Order → **Verify:** Attachments section shows PDF(s)
8. Click **Download** on attachment → **Verify:** PDF downloads

### Test 2: Distribution Detail + SO Upload

1. Navigate to **Distribution Log**
2. Find an entry with ⚠ (unmatched) icon
3. Click **Details**
4. Click **Upload PDF to Match**
5. Select a Sales Order PDF
6. **Expected:** Success message; distribution now linked to SO
7. Close modal → **Verify:** ⚠ icon gone

### Test 3: Customer Cleanup Review

1. Navigate to `https://yourapp.com/admin/maintenance/customers/zero-orders`
2. **Review** JSON list of zero-order customers
3. Navigate to `https://yourapp.com/admin/maintenance/customers/duplicates`
4. **Review** JSON list of duplicate groups
5. **Do NOT delete/merge yet** — just verify data looks correct

### Test 4: Sales Dashboard

1. Navigate to **Sales Dashboard**
2. **Verify:** Total orders, units, customers displayed
3. **Verify:** Lot tracking shows only 2026+ lots
4. Cross-check with Customer Database totals — should match

### Test 5: Unmatched PDFs

1. Navigate to **Sales Orders → Unmatched PDFs**
2. **Verify:** List shows any PDFs that couldn't be parsed
3. Click **Download** on any entry → **Verify:** PDF downloads

---

**End of DEBUG_PHASE3_REAUDIT_FOR_DEV.md**
