# DEBUG_PHASE3_AUDIT_FOR_DEV — Production Incident Response & Fixes

**Date:** 2026-01-27  
**Priority:** P0  
**Scope:** Storage failure, console command failure, pipeline enforcement, data correctness

---

## 1. Executive Summary

### P0 Blockers (Critical)

1. **PDF Import Dead-on-Arrival:** Bulk SO PDF import fails with `botocore.exceptions.ClientError: InvalidAccessKeyId`. All PDF storage operations are broken in production.
2. **Console Commands Non-Functional:** Maintenance scripts (`dedupe_customers.py`, `cleanup_zero_order_customers.py`) produce no output in DigitalOcean console—either shell is non-interactive, container lacks scripts, or silent failures.
3. **No Storage Health Check:** App starts and serves traffic without verifying storage credentials are valid, leading to 500 errors at upload time.
4. **Customer Stats Include Unmatched Distributions:** Customer list page aggregates ALL distributions, not just matched ones—violates canonical pipeline.

### P1/P2 Issues

5. **P1:** Customers can be created from CSV import/manual entry without matching SO (pipeline leak)
6. **P1:** Label upload links to distribution but doesn't verify SO exists—could contribute to incorrect customer data if labels affect stats
7. **P2:** No UI to view/download unmatched PDF attachments
8. **P2:** Import page mentions "2025" (hardcoded year)

### Stop-the-Bleeding Recommendations

1. **Fix storage credentials immediately** — verify `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT`, `S3_BUCKET` in DO environment
2. **Add startup storage self-check** — fail loudly in logs if storage is misconfigured
3. **Add graceful error handling** — return user-facing message "Upload failed: storage not configured" instead of 500
4. **Fix customer stats query** — filter by `sales_order_id.isnot(None)`
5. **Provide admin-accessible maintenance endpoints** — since console doesn't work

---

## 2. Spec Compliance Checklist (Phase 3 Invariants)

| Invariant | Status | Evidence | Fix Required |
|-----------|--------|----------|--------------|
| Customer profiles only for customers with ≥1 matched SO | **FAIL** | `customer_profiles/admin.py:65-71` stats query has no SO filter | Add `sales_order_id.isnot(None)` filter |
| Sales dashboard aggregates only matched distributions | **PASS** | `service.py:550-551, 569-570, 581, 617` all filter `sales_order_id.isnot(None)` | N/A |
| ShipStation sync never creates customers | **PASS** | `shipstation_sync/service.py:46-64` uses `_get_existing_customer_from_ship_to()` which only looks up, never creates | N/A |
| Sales Order is customer identity source-of-truth | **PARTIAL** | PDF import uses `find_or_create_customer()` correctly, but CSV import and manual entry also call it without requiring SO | Enforce SO-first for all customer creation |
| Label PDFs link to distributions, don't affect customer/dashboard unless matched SO exists | **PASS** | `admin.py:685-728` stores label linked to distribution; dashboard filters by `sales_order_id` | N/A |
| Storage functional for PDF uploads | **FAIL** | `InvalidAccessKeyId` error in production | Fix credentials + add health check |

---

## 3. P0 Incident Report — PDF Import Broken Due to Storage Misconfiguration

### A) Repro + Exact Stack Trace Mapping

**Route:** `POST /admin/sales-orders/import-pdf-bulk`

**Call Chain:**
```
sales_orders_import_pdf_bulk()                    # admin.py:1475
  → _store_pdf_attachment()                       # admin.py:47-78
    → storage_from_config(current_app.config)     # admin.py:60, storage.py:87-99
    → S3Storage.put_bytes()                       # storage.py:69-73
      → boto3.client().put_object()               # storage.py:73
        → FAILS: InvalidAccessKeyId
```

**Affected Routes (all use `_store_pdf_attachment`):**
- `POST /admin/sales-orders/import-pdf-bulk` — bulk PDF import
- `POST /admin/sales-orders/import-pdf` — single-file PDF import  
- `POST /admin/sales-orders/<id>/upload-pdf` — upload to specific SO
- `POST /admin/distribution-log/<id>/upload-pdf` — upload from distribution detail
- `POST /admin/distribution-log/<id>/upload-label` — label upload

### B) Root Cause Hypothesis (Ranked)

| # | Hypothesis | Confidence | Evidence/Reasoning |
|---|------------|------------|-------------------|
| 1 | **Missing/incorrect S3_ACCESS_KEY_ID in DO env vars** | HIGH | Error is specifically `InvalidAccessKeyId` (not InvalidSignature, NoSuchBucket, etc.) |
| 2 | Wrong endpoint format for DO Spaces | MEDIUM | DO Spaces endpoint should be `sfo3.digitaloceanspaces.com` (not `https://` prefix—code adds that) |
| 3 | Key rotation / drift between environments | MEDIUM | Credentials may have worked in dev but not set or different in prod |
| 4 | AWS SDK vs DO Spaces incompatibility | LOW | boto3 generally works with S3-compatible APIs |
| 5 | Bucket name or permissions wrong | LOW | Error is access key, not bucket/permission |

### C) Concrete Fixes (Minimal)

**Option 1 (PREFERRED): Fix config + add startup self-check**

**Step 1: Verify DO Environment Variables**

In DigitalOcean App Platform → Settings → Environment Variables, confirm:

```
STORAGE_BACKEND=s3
S3_ENDPOINT=sfo3.digitaloceanspaces.com   # NO https:// prefix
S3_REGION=sfo3
S3_BUCKET=raoeqms-files                   # Actual bucket name
S3_ACCESS_KEY_ID=<actual-key>             # 20+ chars
S3_SECRET_ACCESS_KEY=<actual-secret>      # 40+ chars
```

**Step 2: Add startup storage self-check**

**File:** `app/eqms/__init__.py`

Add after app configuration, before blueprint registration:

```python
# Storage health check (fail loudly on misconfiguration)
if app.config.get("STORAGE_BACKEND") == "s3":
    missing = []
    for key in ("S3_ENDPOINT", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        if not app.config.get(key):
            missing.append(key)
    if missing:
        app.logger.error("STORAGE CONFIG ERROR: Missing required S3 env vars: %s", ", ".join(missing))
    else:
        # Quick connectivity check (try to list bucket—fails fast if creds wrong)
        try:
            from app.eqms.storage import storage_from_config, S3Storage
            storage = storage_from_config(app.config)
            if isinstance(storage, S3Storage):
                storage._client().head_bucket(Bucket=storage.bucket)
                app.logger.info("Storage health check PASSED: S3 bucket '%s' accessible", storage.bucket)
        except Exception as e:
            app.logger.error("STORAGE CONFIG ERROR: Cannot access S3 bucket: %s", e)
```

**Step 3: Graceful error handling in upload routes**

**File:** `app/eqms/modules/rep_traceability/admin.py`

Update `_store_pdf_attachment()` to catch storage errors:

```python
def _store_pdf_attachment(
    s,
    pdf_bytes: bytes,
    filename: str,
    pdf_type: str,
    sales_order_id: int | None,
    distribution_entry_id: int | None,
    user: User,
) -> str:
    from werkzeug.utils import secure_filename
    from datetime import datetime
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
    from app.eqms.storage import StorageError

    storage = storage_from_config(current_app.config)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(filename) or "document.pdf"
    if sales_order_id:
        storage_key = f"sales_orders/{sales_order_id}/pdfs/{pdf_type}_{timestamp}_{safe_name}"
    else:
        storage_key = f"sales_orders/unlinked/{pdf_type}_{timestamp}_{safe_name}"
    
    try:
        storage.put_bytes(storage_key, pdf_bytes, content_type="application/pdf")
    except Exception as e:
        current_app.logger.error("Storage write failed for key=%s: %s", storage_key, e)
        raise StorageError(f"Failed to store PDF: storage not configured or inaccessible. Contact admin.") from e

    attachment = OrderPdfAttachment(
        sales_order_id=sales_order_id,
        distribution_entry_id=distribution_entry_id,
        storage_key=storage_key,
        filename=filename,
        pdf_type=pdf_type,
        uploaded_by_user_id=user.id,
    )
    s.add(attachment)
    return storage_key
```

Update bulk import to catch `StorageError` and flash user-friendly message.

### D) Storage Diagnostics Endpoint

**File:** `app/eqms/admin.py`

Add new route:

```python
@bp.get("/diagnostics/storage")
@require_permission("admin.view")
def diagnostics_storage():
    """Storage diagnostics (admin-only). Shows config status without exposing secrets."""
    from flask import current_app, jsonify
    from app.eqms.storage import storage_from_config, S3Storage, LocalStorage
    
    result = {
        "backend": current_app.config.get("STORAGE_BACKEND", "local"),
        "configured": False,
        "accessible": False,
        "error": None,
        "details": {},
    }
    
    storage = storage_from_config(current_app.config)
    
    if isinstance(storage, S3Storage):
        result["details"] = {
            "endpoint": storage.endpoint or "(default AWS)",
            "region": storage.region,
            "bucket": storage.bucket,
            "access_key_prefix": storage.access_key_id[:4] + "..." if storage.access_key_id else "(missing)",
        }
        result["configured"] = bool(storage.bucket and storage.access_key_id and storage.secret_access_key)
        
        if result["configured"]:
            try:
                storage._client().head_bucket(Bucket=storage.bucket)
                result["accessible"] = True
            except Exception as e:
                result["error"] = str(e)[:200]
    elif isinstance(storage, LocalStorage):
        result["details"] = {"root": str(storage.root)}
        result["configured"] = True
        result["accessible"] = storage.root.exists() or True  # Will create on first write
    
    return jsonify(result)
```

**Template:** Add link to diagnostics page in `admin/diagnostics.html`.

---

## 4. Console / Maintenance Scripts Failure (P0)

### Problem Analysis

Commands provided:
```bash
python scripts/dedupe_customers.py --list
python scripts/cleanup_zero_order_customers.py
```

These produce no output in DigitalOcean console. Possible causes:

| # | Cause | Likelihood | How to Confirm |
|---|-------|------------|----------------|
| 1 | DO console is not an interactive shell into the running container | HIGH | DO App Platform's "Console" may connect to a build environment, not the deployed app |
| 2 | Scripts require Flask app context not available when run standalone | MEDIUM | Scripts use `Session()` directly but may hit import errors |
| 3 | Working directory is wrong | MEDIUM | Scripts do `sys.path.insert(0, ".")` which assumes `/app` |
| 4 | Silent failures (no error output) | MEDIUM | Scripts don't have comprehensive error handling |

### Proposed Fix: Admin-Only Web Endpoints

Since console is unreliable, add protected admin endpoints:

**File:** `app/eqms/admin.py`

```python
@bp.get("/maintenance/customers/duplicates")
@require_permission("admin.view")
def maintenance_list_duplicates():
    """List potential duplicate customers (read-only)."""
    from flask import jsonify
    from app.eqms.modules.customer_profiles.service import find_merge_candidates
    
    s = db_session()
    candidates = find_merge_candidates(s, limit=100)
    
    result = []
    for c in candidates:
        result.append({
            "customer1_id": c.customer1.id,
            "customer1_name": c.customer1.facility_name,
            "customer1_location": f"{c.customer1.city}, {c.customer1.state}",
            "customer2_id": c.customer2.id,
            "customer2_name": c.customer2.facility_name,
            "customer2_location": f"{c.customer2.city}, {c.customer2.state}",
            "confidence": c.confidence,
            "match_reason": c.match_reason,
        })
    
    return jsonify({"duplicates": result, "count": len(result)})


@bp.get("/maintenance/customers/zero-orders")
@require_permission("admin.view")
def maintenance_list_zero_orders():
    """List customers with 0 matched sales orders (read-only)."""
    from flask import jsonify
    from sqlalchemy import func
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.customer_profiles.models import Customer
    
    s = db_session()
    
    # Customers with 0 sales orders
    order_count_subq = (
        s.query(SalesOrder.customer_id, func.count(SalesOrder.id).label("order_count"))
        .group_by(SalesOrder.customer_id)
        .subquery()
    )
    
    zero_order_customers = (
        s.query(Customer)
        .outerjoin(order_count_subq, Customer.id == order_count_subq.c.customer_id)
        .filter(
            (order_count_subq.c.order_count == None) | (order_count_subq.c.order_count == 0)
        )
        .order_by(Customer.facility_name)
        .limit(200)
        .all()
    )
    
    result = [
        {"id": c.id, "facility_name": c.facility_name, "company_key": c.company_key}
        for c in zero_order_customers
    ]
    
    return jsonify({"zero_order_customers": result, "count": len(result)})


@bp.post("/maintenance/customers/merge")
@require_permission("admin.edit")
def maintenance_merge_customers():
    """Merge duplicate customers. Requires master_id, duplicate_id, confirm_token."""
    from flask import jsonify, request
    import hashlib
    from app.eqms.modules.customer_profiles.service import merge_customers
    from app.eqms.modules.customer_profiles.models import Customer
    
    master_id = request.json.get("master_id")
    duplicate_id = request.json.get("duplicate_id")
    confirm_token = request.json.get("confirm_token")
    
    if not master_id or not duplicate_id:
        return jsonify({"error": "master_id and duplicate_id required"}), 400
    
    # Require confirmation token = md5(master_id:duplicate_id:CONFIRM)
    expected_token = hashlib.md5(f"{master_id}:{duplicate_id}:CONFIRM".encode()).hexdigest()[:8]
    if confirm_token != expected_token:
        return jsonify({
            "error": "Confirmation required",
            "confirm_token": expected_token,
            "message": f"To confirm merge, POST with confirm_token='{expected_token}'"
        }), 400
    
    s = db_session()
    user = _current_user()
    
    master = s.query(Customer).filter(Customer.id == master_id).one_or_none()
    duplicate = s.query(Customer).filter(Customer.id == duplicate_id).one_or_none()
    
    if not master or not duplicate:
        return jsonify({"error": "Customer not found"}), 404
    
    try:
        result = merge_customers(s, master_id=master_id, duplicate_id=duplicate_id, user=user)
        s.commit()
        return jsonify({
            "success": True,
            "merged_into": {"id": result.id, "facility_name": result.facility_name}
        })
    except Exception as e:
        s.rollback()
        return jsonify({"error": str(e)}), 500
```

### Alternative: One-Off Task via DO "Run Command"

For one-time cleanup, you can run a different entrypoint:

1. Go to DO App Platform → Settings → Components → Web Service
2. Edit "Run Command" temporarily to:
   ```
   python scripts/cleanup_zero_order_customers.py --dry-run && gunicorn ...
   ```
3. Deploy, check logs
4. Change back to normal run command

**This is fragile**—prefer web endpoints for repeatability.

---

## 5. Reproducible Bug Catalog (Prioritized)

### DBG-001: Bulk PDF Import Fails — InvalidAccessKeyId (P0)

| Field | Detail |
|-------|--------|
| **Severity** | P0 |
| **Repro** | 1. Go to Sales Orders → Import PDF<br>2. Select PDF file(s)<br>3. Click "Import" |
| **Expected** | PDF parsed, SO created, attachment stored |
| **Actual** | 500 error, `botocore.exceptions.ClientError: InvalidAccessKeyId` |
| **Root Cause** | `S3_ACCESS_KEY_ID` invalid or missing in production env vars |
| **Files** | `app/eqms/storage.py`, `app/eqms/__init__.py`, DO env vars |
| **Fix** | See Section 3C above |
| **Verification** | Import PDF succeeds; `/admin/diagnostics/storage` returns `{"accessible": true}` |

### DBG-002: Single-Page SO Upload Fails (P0)

| Field | Detail |
|-------|--------|
| **Severity** | P0 |
| **Repro** | 1. Go to Distribution Log<br>2. Click "Details" on unmatched entry<br>3. Click "Upload PDF to Match"<br>4. Select PDF |
| **Expected** | PDF stored, SO created, distribution linked |
| **Actual** | Same `InvalidAccessKeyId` error |
| **Root Cause** | Same as DBG-001 |
| **Files** | Same as DBG-001 |
| **Fix** | Same as DBG-001 |
| **Verification** | Upload from distribution detail succeeds |

### DBG-003: Label Upload Fails (P0)

| Field | Detail |
|-------|--------|
| **Severity** | P0 |
| **Repro** | 1. Go to Distribution Log<br>2. Edit an entry<br>3. Upload label PDF |
| **Expected** | Label stored and linked to distribution |
| **Actual** | Same storage error |
| **Root Cause** | Same as DBG-001 |
| **Files** | `admin.py:685-728` (uses `_store_pdf_attachment`) |
| **Fix** | Same as DBG-001 |
| **Verification** | Label upload succeeds |

### DBG-004: Customer Stats Include Unmatched Distributions (P1)

| Field | Detail |
|-------|--------|
| **Severity** | P1 |
| **Repro** | 1. Go to Customer Database<br>2. View any customer's order count / total units |
| **Expected** | Stats only from distributions linked to SOs |
| **Actual** | Stats include ALL distributions (including unmatched) |
| **Root Cause** | `customer_profiles/admin.py:65-71` query lacks `sales_order_id.isnot(None)` filter |
| **Files** | `app/eqms/modules/customer_profiles/admin.py` |
| **Fix** | Add `.filter(DistributionLogEntry.sales_order_id.isnot(None))` to stats query |
| **Verification** | Customer stats match sales dashboard totals |

### DBG-005: Maintenance Scripts Silent in DO Console (P0)

| Field | Detail |
|-------|--------|
| **Severity** | P0 |
| **Repro** | 1. Open DO Console<br>2. Run `python scripts/dedupe_customers.py --list`<br>3. Observe no output |
| **Expected** | List of duplicate candidates printed |
| **Actual** | Nothing happens |
| **Root Cause** | DO Console may not be interactive shell into running container |
| **Files** | `scripts/*.py`, DO console setup |
| **Fix** | Add admin web endpoints (see Section 4) |
| **Verification** | `GET /admin/maintenance/customers/duplicates` returns JSON list |

### DBG-006: Distribution Detail Modal Reliability (P2)

| Field | Detail |
|-------|--------|
| **Severity** | P2 |
| **Repro** | 1. Go to Distribution Log<br>2. Click "Details" on any entry |
| **Expected** | Modal opens with solid background, all sections load |
| **Actual** | Generally works, but verify no JS errors |
| **Root Cause** | N/A (likely working) |
| **Files** | `distribution_log/list.html` |
| **Fix** | Verify `--card-bg` is defined (it is in design-system.css:3) |
| **Verification** | Modal opens cleanly, no console errors |

---

## 6. Data Correctness Audit

### SQL Queries to Detect Pipeline Violations

```sql
-- 1. Customers with zero matched Sales Orders (should not exist per pipeline)
SELECT c.id, c.facility_name, c.company_key
FROM customers c
LEFT JOIN sales_orders so ON so.customer_id = c.id
GROUP BY c.id, c.facility_name, c.company_key
HAVING COUNT(so.id) = 0
ORDER BY c.facility_name;

-- 2. Duplicate customers by canonical company_key
SELECT company_key, COUNT(*) as cnt, 
       string_agg(facility_name || ' (ID ' || id || ')', ', ') as facilities
FROM customers
GROUP BY company_key
HAVING COUNT(*) > 1
ORDER BY cnt DESC;

-- 3. Distributions with customer_id but no sales_order_id (pipeline violation)
SELECT d.id, d.order_number, d.facility_name, d.customer_id, d.ship_date
FROM distribution_log_entries d
WHERE d.customer_id IS NOT NULL 
  AND d.sales_order_id IS NULL
ORDER BY d.ship_date DESC
LIMIT 100;

-- 4. Dashboard counts vs reality (should match)
-- Matched distribution total:
SELECT COUNT(*), SUM(quantity) FROM distribution_log_entries WHERE sales_order_id IS NOT NULL;
-- All distribution total (should be >= matched):
SELECT COUNT(*), SUM(quantity) FROM distribution_log_entries;
```

### Guardrails to Prevent Re-Introducing Corruption

**1. ShipStation Sync:** ✅ Already correct — `_get_existing_customer_from_ship_to()` only looks up, never creates.

**2. CSV Import:** ⚠️ Needs guardrail — currently calls `find_or_create_customer()` which creates customers without requiring SO.

**Fix:** In `admin.py:765-776`, change to only link existing customer OR leave `customer_id = None` and require SO match:

```python
# BEFORE (creates customers):
if facility_name:
    c = find_or_create_customer(s, facility_name=facility_name, ...)
    
# AFTER (only links existing):
if facility_name:
    from app.eqms.modules.customer_profiles.service import find_customer_exact_match
    c = find_customer_exact_match(s, facility_name)
    # If no match, leave customer_id = None; customer created when SO matches
```

**3. Customer/Dashboard Queries:** 

- Dashboard: ✅ Already filters `sales_order_id.isnot(None)`
- Customer stats: ❌ Needs filter added (DBG-004)

---

## 7. Customer Cleanup Plan (Safe, Idempotent)

### What Should Be Hidden vs Deleted

| Category | Action | Rationale |
|----------|--------|-----------|
| Customers with 0 SOs | **DELETE** (after audit) | Violate pipeline; were created from ShipStation/CSV before fix |
| Duplicate customers (same company_key) | **MERGE** into lower ID | Unique constraint should prevent, but backfill may have created |
| Customers with only unmatched distributions | **KEEP but hide from stats** | May eventually get SO matched |

### Safe Merge Process (FK Updates)

```sql
-- To merge customer 456 into 123:

-- 1. Update sales_orders FK
UPDATE sales_orders SET customer_id = 123 WHERE customer_id = 456;

-- 2. Update distribution_log_entries FK
UPDATE distribution_log_entries SET customer_id = 123 WHERE customer_id = 456;

-- 3. Update customer_notes FK
UPDATE customer_notes SET customer_id = 123 WHERE customer_id = 456;

-- 4. Delete duplicate
DELETE FROM customers WHERE id = 456;
```

This is what `merge_customers()` in `service.py` does.

### How to Remove/Ignore 0-Order Customers

Option A (via web endpoint):
1. `GET /admin/maintenance/customers/zero-orders` — review list
2. For each, confirm no legitimate data, then delete via admin endpoint or direct SQL

Option B (via script if console works):
```bash
python scripts/cleanup_zero_order_customers.py --dry-run  # Preview
python scripts/cleanup_zero_order_customers.py --yes      # Execute
```

### Verify Post-Cleanup Correctness

```sql
-- Should return 0 rows:
SELECT COUNT(*) FROM customers c
LEFT JOIN sales_orders so ON so.customer_id = c.id
GROUP BY c.id HAVING COUNT(so.id) = 0;

-- Should return 0 rows:
SELECT company_key, COUNT(*) FROM customers
GROUP BY company_key HAVING COUNT(*) > 1;
```

---

## 8. Legacy/Dead Code Deletion Candidates

| Path | Why Legacy | Risk | Regression Check |
|------|------------|------|------------------|
| `legacy/` directory | Empty folder, marked legacy | None | `ls legacy/` is empty |
| `scripts/refresh_customers_from_sales_orders.py` | Overlaps with `rebuild_customers_from_sales_orders.py` | Low | Check if imported anywhere |
| `customer_name` field on DistributionLogEntry | Deprecated mirror of customer.facility_name | Medium | Used in some queries; keep in model, hide in UI |
| `admin.py:765-776` CSV import customer creation | Creates customers without SO (pipeline violation) | Medium | Change to lookup-only |

**Recommendation:** Focus on fixing behavior, not deleting code in this pass.

---

## 9. Minimal Patch Set (Developer-Ready)

### P0 Fixes (Do First)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 1 | Verify/fix S3 credentials in DO env vars | DO Dashboard | `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT`, `S3_BUCKET` all set correctly |
| 2 | Add startup storage health check | `app/eqms/__init__.py` | Logs show "Storage health check PASSED" or "STORAGE CONFIG ERROR" |
| 3 | Add graceful error handling to `_store_pdf_attachment` | `app/eqms/modules/rep_traceability/admin.py` | Upload failure shows "storage not configured" flash, not 500 |
| 4 | Add storage diagnostics endpoint | `app/eqms/admin.py` | `GET /admin/diagnostics/storage` returns JSON with `accessible: true/false` |
| 5 | Add maintenance endpoints (list duplicates, list zero-orders, merge) | `app/eqms/admin.py` | Endpoints return correct JSON; merge requires confirm_token |

### P1 Fixes (After P0)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 6 | Fix customer stats query to filter by `sales_order_id.isnot(None)` | `app/eqms/modules/customer_profiles/admin.py:65-71` | Customer list stats only count matched distributions |
| 7 | Run customer cleanup (via new endpoints) | N/A | Zero-order customers removed; duplicates merged |
| 8 | Verify dashboard counts match customer stats | Manual check | Numbers consistent |

### P2 Fixes (Polish)

| # | Task | Files | Acceptance Criteria |
|---|------|-------|---------------------|
| 9 | Change CSV import to lookup-only for customers | `admin.py:765-776` | CSV import doesn't create new customers |
| 10 | Remove "2025" from import page | `templates/admin/sales_orders/import.html:6` | No hardcoded year |
| 11 | Add UI for viewing unmatched PDF attachments | `templates/admin/sales_orders/list.html` | Can see and download unmatched PDFs |

---

## 10. Production Verification Runbook (Browser-First)

### Step 1: Verify Storage Configuration

1. Go to **Admin → Diagnostics** (add link if needed)
2. Look for **Storage** section or go to `/admin/diagnostics/storage`
3. **Expected:** `{"backend": "s3", "configured": true, "accessible": true}`
4. **If FAIL:** Check DO env vars, fix credentials

### Step 2: Test Bulk PDF Import

1. Go to **Sales Orders → Import PDF**
2. Select a small test PDF (single page)
3. Click **Import**
4. **Expected:** Flash message "X pages processed, Y orders created..."
5. **If FAIL with 500:** Check logs for storage error; verify Step 1 passed

### Step 3: Test Distribution Detail Upload

1. Go to **Distribution Log**
2. Find an unmatched entry (⚠ icon)
3. Click **Details**
4. Click **Upload PDF to Match**
5. Select a PDF, submit
6. **Expected:** SO created, distribution matched, PDF downloadable
7. **Verify:** Modal shows "Linked Sales Order" section with attachment download

### Step 4: Test Label Upload

1. Go to **Distribution Log**
2. Click **Edit** on any entry
3. Scroll to **Upload Label** section
4. Select a PDF, submit
5. **Expected:** Flash "Label uploaded"
6. **Verify:** Entry shows label attachment in details modal

### Step 5: Verify Customer Page Stats

1. Go to **Customers**
2. Note total customers and order counts
3. Compare to **Sales Dashboard** totals
4. **Expected:** Customer stats only reflect matched distributions

### Step 6: Run Customer Cleanup (After P0 Fixed)

1. Go to `/admin/maintenance/customers/duplicates`
2. Review JSON output for duplicates
3. For each pair, decide master/duplicate
4. `POST /admin/maintenance/customers/merge` with `master_id`, `duplicate_id`
5. First call returns `confirm_token`
6. Second call with token executes merge
7. Repeat for `/admin/maintenance/customers/zero-orders` review
8. **Verify:** Rerun queries from Section 6 return 0 rows

---

**End of DEBUG_PHASE3_AUDIT_FOR_DEV.md**
