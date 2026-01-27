# Phase 3: Data Correctness and PDF Import Fixes

**Date:** 2026-01-27  
**Priority:** P0 (Critical)  
**Scope:** Fix data integrity, PDF import failures, customer deduplication, sales dashboard correctness, broken distribution detail views. **No new features.**

---

## Section 1: System Truth Table / Invariants

### Invariant 1: Customer Profile Existence
**Rule:** A Customer profile appears in the Customer Database **only if** there exists ≥1 matched Sales Order linked to that customer.

**Enforcement:**
- Customer records are created/updated **only** from Sales Orders (PDF import, manual entry)
- ShipStation sync **must not** create customers directly
- Customers with 0 matched Sales Orders **must not** appear in Customer Database UI (or must be marked as "inactive")

**Violation Detection:**
```sql
-- Customers with no matched sales orders
SELECT c.id, c.facility_name, c.created_at
FROM customers c
LEFT JOIN sales_orders so ON so.customer_id = c.id
WHERE so.id IS NULL;
```

### Invariant 2: Sales Dashboard Aggregation Source
**Rule:** Sales dashboard aggregates **only** from matched Sales Orders (distributions with `sales_order_id IS NOT NULL`).

**Enforcement:**
- Dashboard queries must filter: `WHERE distribution_log_entries.sales_order_id IS NOT NULL`
- Unmatched distributions (`sales_order_id IS NULL`) **must not** count toward:
  - Total orders
  - Total units
  - Total customers
  - First-time vs repeat classification
  - SKU breakdown
  - Lot tracking

**Violation Detection:**
```sql
-- Distributions counted in dashboard but unmatched
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NULL;
-- If > 0, dashboard is incorrectly including unmatched data
```

### Invariant 3: Distribution Independence
**Rule:** Distributions can exist without a matched Sales Order temporarily, but they **must not** generate customer metrics or appear in sales dashboard.

**Enforcement:**
- Distributions created from ShipStation sync have `sales_order_id = NULL` initially
- Distributions can be matched later via PDF upload or manual match
- Until matched, distributions are "orphaned" and excluded from aggregations

### Invariant 4: Sales Order as Customer Source of Truth
**Rule:** A Sales Order is the source-of-truth for customer identity once matched.

**Enforcement:**
- When a distribution is matched to a Sales Order, `distribution.customer_id = sales_order.customer_id`
- Customer identity (name, address) comes from Sales Order ship-to fields, not ShipStation raw data
- If Sales Order customer is updated, linked distributions should reflect the change (via FK relationship)

### Invariant 5: Label PDF Linkage
**Rule:** Label PDFs are linked to a Distribution **only when** address/distribution linkage is satisfied.

**Enforcement:**
- Label PDFs uploaded from distribution detail view are linked via `distribution_entry_id`
- Label PDFs uploaded via batch must match by address (ship-to name/address from label matches distribution facility/address)
- Label PDFs without a match are stored as `distribution_entry_id = NULL` (unmatched)

---

## Section 2: Data Model + Relationship Audit

### Tables and Key Fields

#### `distribution_log_entries`
**Key Fields:**
- `id` (PK)
- `sales_order_id` (FK to `sales_orders.id`, **nullable** - required for dashboard inclusion)
- `customer_id` (FK to `customers.id`, **nullable** - should be set via SO match)
- `order_number` (Text, required)
- `facility_name` (Text, required - free-text fallback)
- `customer_name` (Text, nullable - deprecated, kept for legacy data)
- `source` (Text, required - 'shipstation', 'manual', 'csv_import', 'pdf_import')

**Current Issues:**
- `customer_id` can be set independently of `sales_order_id` (violates pipeline)
- `customer_name` still used in some queries (should be deprecated)

**Proposed Fix:**
- `customer_id` should **only** be set when `sales_order_id` is set (via `sales_order.customer_id`)
- Remove `customer_name` from aggregation queries (use `customer_id` or `facility_name` as fallback)

#### `sales_orders`
**Key Fields:**
- `id` (PK)
- `customer_id` (FK to `customers.id`, **NOT NULL** - source of truth)
- `order_number` (Text, required, indexed)
- `order_date` (Date, required)
- `ship_date` (Date, nullable)
- `source` (Text, required - 'shipstation', 'manual', 'csv_import', 'pdf_import')
- `external_key` (Text, nullable - for idempotency per source)

**Current Issues:**
- `customer_id` is NOT NULL, but some code paths try to create SOs without customer (will fail)

**Proposed Fix:**
- Ensure all Sales Order creation paths have a valid `customer_id` (create customer first if needed)

#### `customers`
**Key Fields:**
- `id` (PK)
- `company_key` (Text, required, unique - canonical key for deduplication)
- `facility_name` (Text, required)
- `address1`, `address2`, `city`, `state`, `zip` (Text, nullable)
- `contact_name`, `contact_phone`, `contact_email` (Text, nullable)

**Current Issues:**
- Duplicates created due to inconsistent normalization (abbreviations, punctuation)
- Customers with 0 orders (from development/backfills)

**Proposed Fix:**
- Use `company_key` for all customer lookups (not free-text `facility_name`)
- Delete or hide customers with 0 matched Sales Orders

#### `order_pdf_attachments`
**Key Fields:**
- `id` (PK)
- `sales_order_id` (FK to `sales_orders.id`, **nullable** - for unmatched PDFs)
- `distribution_entry_id` (FK to `distribution_log_entries.id`, **nullable** - for label PDFs)
- `pdf_type` (Text, required - 'sales_order_page', 'shipping_label', 'unmatched', 'unparsed', etc.)
- `storage_key` (Text, required)
- `filename` (Text, required)

**Current Issues:**
- Unmatched PDFs stored but not visible in UI (already fixed in Phase 2, but verify)

### Nullability Rules

| Field | Current | Should Be | Why |
|-------|---------|-----------|-----|
| `distribution_log_entries.sales_order_id` | Nullable | Nullable (correct) | Distributions can exist unmatched |
| `distribution_log_entries.customer_id` | Nullable | Nullable (but set via SO) | Should be set from `sales_order.customer_id` |
| `sales_orders.customer_id` | NOT NULL | NOT NULL (correct) | SO is source of truth for customer |
| `order_pdf_attachments.sales_order_id` | Nullable | Nullable (correct) | Unmatched PDFs exist |

### Canonical Keys

**Customer Identity:**
- Primary: `customers.company_key` (normalized facility name)
- Fallback: Address-based matching (city + state + zip) if `company_key` not available
- **Do NOT use:** Free-text `customer_name` or `facility_name` for deduplication

**Sales Order Identity:**
- Primary: `sales_orders.order_number` (unique per order)
- Idempotency: `sales_orders.source + sales_orders.external_key` (unique constraint)

**Distribution Identity:**
- Idempotency: `distribution_log_entries.source + distribution_log_entries.external_key` (unique constraint)

---

## Section 3: Root-Cause Analysis Plan (PDF Import Failure)

### Step 1: Reproduce the Error

**Endpoints to Test:**
1. **Bulk PDF Import:** `POST /admin/sales-orders/import-pdf-bulk`
   - Route: `sales_orders_import_pdf_bulk()` in `app/eqms/modules/rep_traceability/admin.py:1361`
   - Template: `app/eqms/templates/admin/sales_orders/import.html`
   - Form: `<form action="{{ url_for('rep_traceability.sales_orders_import_pdf_bulk') }}" method="post" enctype="multipart/form-data">`

2. **Single PDF Import:** `POST /admin/sales-orders/import-pdf`
   - Route: `sales_orders_import_pdf()` in `app/eqms/modules/rep_traceability/admin.py:1469`
   - Same template, different form action

**Steps to Reproduce:**
1. Go to `/admin/sales-orders/import-pdf`
2. Select one or more PDF files
3. Click "Import Bulk PDFs" or "Import PDF"
4. Observe error (Internal Server Error 500)

### Step 2: Identify Likely Failure Points

**A. PDF Parsing Errors:**
- **Exception:** `pdfplumber.PDFSyntaxError`, `pdfplumber.PDFException`, `AttributeError` (missing `pages` attribute)
- **Code Path:** `app/eqms/modules/rep_traceability/parsers/pdf.py::parse_sales_orders_pdf()`
- **Likely Cause:** Corrupted PDF, unsupported PDF version, encrypted PDF, image-only PDF (no text layer)

**B. PDF Splitting Errors:**
- **Exception:** `PyPDF2.errors.PdfReadError`, `AttributeError` (missing `pages` attribute)
- **Code Path:** `app/eqms/modules/rep_traceability/parsers/pdf.py::split_pdf_into_pages()`
- **Likely Cause:** Same as parsing errors, or memory issues with large PDFs

**C. File Handling Errors:**
- **Exception:** `IOError`, `OSError`, `PermissionError`
- **Code Path:** `request.files.getlist("pdf_files")` or `f.read()`
- **Likely Cause:** File too large (exceeds request size limit), file permissions, disk full

**D. Missing Dependencies:**
- **Exception:** `ImportError: No module named 'pdfplumber'` or `ImportError: No module named 'PyPDF2'`
- **Code Path:** Import statements in `parsers/pdf.py`
- **Likely Cause:** Dependencies not installed in production environment

**E. Memory Errors:**
- **Exception:** `MemoryError`, `OSError: [Errno 12] Cannot allocate memory`
- **Code Path:** `f.read()` or `split_pdf_into_pages(pdf_bytes)`
- **Likely Cause:** PDF too large, multiple large PDFs uploaded at once

**F. Database Errors:**
- **Exception:** `sqlalchemy.exc.IntegrityError`, `sqlalchemy.exc.OperationalError`
- **Code Path:** `s.add(sales_order)`, `s.commit()`
- **Likely Cause:** Duplicate `external_key`, missing `customer_id` (NOT NULL constraint), database connection lost

**G. Customer Creation Errors:**
- **Exception:** `sqlalchemy.exc.IntegrityError` (duplicate `company_key`), `ValueError` (empty facility_name)
- **Code Path:** `find_or_create_customer()` in `app/eqms/modules/customer_profiles/service.py:99`
- **Likely Cause:** Race condition (concurrent customer creation), invalid input data

### Step 3: Logs to Capture

**DigitalOcean App Logs:**
```bash
# Access via DO dashboard or CLI
doctl apps logs <app-id> --type run --follow

# Look for:
# - Stack traces (Python traceback)
# - "Internal Server Error" messages
# - "PDF parse failed" warnings
# - "IntegrityError" or "OperationalError" exceptions
# - Memory errors
# - Import errors
```

**Gunicorn Error Logs:**
- Location: Configured in `scripts/start.py` (likely `--error-logfile` or stderr)
- Look for: Same as above, plus worker crashes

**Application Logs:**
- Check `current_app.logger.warning()` calls in `admin.py:512` (PDF parse failures)
- Check `logger.info()` calls in `shipstation_sync/service.py` (if sync-related)

**Expected Log Patterns:**
```
ERROR: Exception on /admin/sales-orders/import-pdf-bulk [POST]
Traceback (most recent call last):
  File ".../admin.py", line 1361, in sales_orders_import_pdf_bulk
    ...
```

### Step 4: Code Files to Inspect

**Primary Suspects (in order of likelihood):**

1. **`app/eqms/modules/rep_traceability/admin.py:1361`** (`sales_orders_import_pdf_bulk()`)
   - **Why:** Bulk import route, handles multiple files, calls splitting logic
   - **Check:** Exception handling around `split_pdf_into_pages()`, `parse_sales_orders_pdf()`, `find_or_create_customer()`

2. **`app/eqms/modules/rep_traceability/parsers/pdf.py`**
   - **Why:** PDF parsing and splitting logic
   - **Check:** `parse_sales_orders_pdf()` exception handling, `split_pdf_into_pages()` error handling

3. **`app/eqms/modules/customer_profiles/service.py:99`** (`find_or_create_customer()`)
   - **Why:** Customer creation can fail with duplicate `company_key` or invalid input
   - **Check:** Exception handling, idempotency logic

4. **`app/eqms/modules/rep_traceability/admin.py:1469`** (`sales_orders_import_pdf()`)
   - **Why:** Single-file import route (may have different error path)
   - **Check:** Same as bulk import

### Step 5: Expected Fix Approach

**A. Add Comprehensive Error Handling:**
```python
# In sales_orders_import_pdf_bulk():
try:
    pdf_bytes = f.read()
    pages = split_pdf_into_pages(pdf_bytes)
except Exception as e:
    current_app.logger.error(f"PDF split failed for {f.filename}: {e}", exc_info=True)
    # Store as unmatched PDF
    _store_pdf_attachment(..., pdf_type="unparsed", ...)
    total_errors += 1
    continue

# In parse_sales_orders_pdf():
try:
    # ... parsing logic ...
except Exception as e:
    current_app.logger.warning(f"PDF parse failed: {e}", exc_info=True)
    return ParseResult(orders=[], errors=[ParseError(...)])
```

**B. Validate Dependencies:**
```python
# At route level:
try:
    import pdfplumber
    import PyPDF2
except ImportError as e:
    flash(f"PDF parsing libraries not installed: {e}", "danger")
    return redirect(...)
```

**C. Add Request Size Limits:**
```python
# In Flask app config or route:
MAX_PDF_SIZE = 10 * 1024 * 1024  # 10MB
if len(pdf_bytes) > MAX_PDF_SIZE:
    flash(f"PDF too large: {len(pdf_bytes)} bytes (max {MAX_PDF_SIZE})", "danger")
    return redirect(...)
```

**D. Fix Customer Creation Race Conditions:**
```python
# In find_or_create_customer():
try:
    with s.begin_nested():  # Use nested transaction for idempotency
        customer = Customer(...)
        s.add(customer)
        s.flush()
except IntegrityError as e:
    # Duplicate company_key - retry lookup
    s.rollback()
    customer = find_customer_exact_match(s, facility_name)
    if not customer:
        raise  # Re-raise if still not found
```

### Step 6: Tests to Add

**Unit Tests:**
```python
# tests/test_pdf_import.py
def test_bulk_import_handles_corrupted_pdf():
    # Upload corrupted PDF, verify error handled gracefully

def test_bulk_import_handles_missing_dependencies():
    # Mock ImportError, verify user-friendly error message

def test_bulk_import_handles_large_pdf():
    # Upload 20MB PDF, verify size limit enforced

def test_bulk_import_handles_duplicate_customer_creation():
    # Simulate race condition, verify idempotency
```

**Integration Tests:**
```python
def test_bulk_import_end_to_end():
    # Upload valid PDF, verify Sales Order created, distributions linked
```

---

## Section 4: Customer Dedupe + Cleanup Strategy

### Phase 1: Stop the Bleeding

**A. Enforce Customer Creation Only from Sales Orders:**
- **File:** `app/eqms/modules/shipstation_sync/service.py`
- **Change:** Remove all calls to `_get_existing_customer_from_ship_to()` or `find_or_create_customer()` from ShipStation sync
- **Result:** ShipStation sync creates distributions only; customers come from Sales Orders

**B. Prevent Duplicate Customer Creation:**
- **File:** `app/eqms/modules/customer_profiles/service.py:99` (`find_or_create_customer()`)
- **Change:** Add retry logic for `IntegrityError` (duplicate `company_key`):
  ```python
  try:
      customer = Customer(...)
      s.add(customer)
      s.flush()
  except IntegrityError:
      s.rollback()
      # Retry lookup (another process may have created it)
      customer = find_customer_exact_match(s, facility_name)
      if not customer:
          raise  # Still not found - re-raise
  ```

**C. Hide 0-Order Customers from UI:**
- **File:** `app/eqms/modules/customer_profiles/admin.py` (customer list route)
- **Change:** Filter out customers with no matched Sales Orders:
  ```python
  customers = (
      s.query(Customer)
      .join(SalesOrder, SalesOrder.customer_id == Customer.id)
      .distinct()
      .all()
  )
  ```

### Phase 2: Clean Existing Data

**A. Define Canonical Customer Identity Source:**
- **Source:** Sales Order ship-to fields (`sales_orders` → `customers` via `customer_id`)
- **Key Fields:** `facility_name`, `address1`, `city`, `state`, `zip` (from Sales Order, not ShipStation)
- **Normalization:** Use `canonical_customer_key(facility_name)` for deduplication

**B. Dedupe Rules:**
1. **Exact Match:** Same `company_key` → Merge into one customer
2. **Strong Match:** Same address (city + state + zip) + similar `company_key` → Merge (manual review recommended)
3. **Weak Match:** Similar `company_key` prefix + same state → Flag for manual review (do not auto-merge)

**C. Merge Strategy:**
```python
# Script: scripts/dedupe_customers.py
def merge_customers(s, keep_customer_id: int, merge_customer_ids: list[int]):
    """
    Merge multiple customers into one.
    - Keep: customer with most matched Sales Orders (or oldest if tie)
    - Merge: Update all Sales Orders and Distributions to point to kept customer
    - Delete: Remove merged customer records (after FK updates)
    """
    keep_customer = s.get(Customer, keep_customer_id)
    
    for merge_id in merge_customer_ids:
        merge_customer = s.get(Customer, merge_id)
        
        # Update Sales Orders
        s.query(SalesOrder).filter(SalesOrder.customer_id == merge_id).update({
            "customer_id": keep_customer_id
        })
        
        # Update Distributions
        s.query(DistributionLogEntry).filter(
            DistributionLogEntry.customer_id == merge_id
        ).update({
            "customer_id": keep_customer_id
        })
        
        # Update Customer Notes (if any)
        s.query(CustomerNote).filter(
            CustomerNote.customer_id == merge_id
        ).update({
            "customer_id": keep_customer_id
        })
        
        # Delete merged customer
        s.delete(merge_customer)
    
    s.commit()
```

**D. Delete 0-Order Customers:**
```python
# Script: scripts/cleanup_zero_order_customers.py
def cleanup_zero_order_customers(s, dry_run: bool = True):
    """
    Delete or hide customers with 0 matched Sales Orders.
    - Check: LEFT JOIN sales_orders, filter WHERE so.id IS NULL
    - Action: Delete (if safe) or mark as inactive (if FK constraints prevent deletion)
    """
    zero_order_customers = (
        s.query(Customer)
        .outerjoin(SalesOrder, SalesOrder.customer_id == Customer.id)
        .filter(SalesOrder.id.is_(None))
        .all()
    )
    
    for customer in zero_order_customers:
        if dry_run:
            print(f"Would delete: {customer.id} - {customer.facility_name}")
        else:
            # Check for FK constraints (distributions, notes, etc.)
            dist_count = s.query(DistributionLogEntry).filter(
                DistributionLogEntry.customer_id == customer.id
            ).count()
            
            if dist_count == 0:
                s.delete(customer)
            else:
                # Keep customer but mark as inactive (add `is_active` field if needed)
                # Or: Set customer_id = NULL on distributions (if safe)
                pass
    
    if not dry_run:
        s.commit()
```

**E. Rollback Approach:**
- **Backup:** Export customer data before cleanup:
  ```sql
  COPY (SELECT * FROM customers) TO '/tmp/customers_backup.csv' CSV HEADER;
  ```
- **Restore:** Import backup if needed:
  ```sql
  COPY customers FROM '/tmp/customers_backup.csv' CSV HEADER;
  ```
- **Audit:** Log all merge/delete operations in `audit_events` table

---

## Section 5: Sales Dashboard Correctness

### Current Problem

**File:** `app/eqms/modules/rep_traceability/service.py:529` (`compute_sales_dashboard()`)

**Issue:** Dashboard reads from `DistributionLogEntry` directly (line 540-561) without filtering for matched Sales Orders:

```python
# CURRENT (WRONG):
q = s.query(DistributionLogEntry)
if start_date:
    q = q.filter(DistributionLogEntry.ship_date >= start_date)
window_entries = q.order_by(...).all()  # Includes unmatched distributions!
```

**Result:** Unmatched distributions are counted in:
- Total orders (line 563)
- Total units (line 564)
- Total customers (line 572)
- First-time vs repeat classification (line 576-581)
- SKU breakdown (line 584-586)
- Recent orders lists (line 661-688)

### Required Fix

**Change:** Filter to only matched distributions:

```python
# FIXED:
q = s.query(DistributionLogEntry).filter(
    DistributionLogEntry.sales_order_id.isnot(None)  # Only matched distributions
)
if start_date:
    q = q.filter(DistributionLogEntry.ship_date >= start_date)
window_entries = q.order_by(...).all()
```

**Also Fix:** Recent orders classification (line 662):
```python
# CURRENT (WRONG):
if not e.order_number or not e.customer_id:
    continue  # Skips unmatched, but still processes if customer_id set

# FIXED:
if not e.order_number or not e.customer_id or not e.sales_order_id:
    continue  # Only process matched distributions
```

### Test Cases

**Test 1: Unmatched Distributions Excluded**
```python
def test_dashboard_excludes_unmatched_distributions():
    # Create unmatched distribution (sales_order_id = NULL)
    # Create matched distribution (sales_order_id = 1)
    # Verify dashboard only counts matched distribution
```

**Test 2: Customer Count Correct**
```python
def test_dashboard_customer_count_from_matched_so():
    # Create 2 distributions for same customer, 1 matched, 1 unmatched
    # Verify dashboard counts customer only once (from matched SO)
```

**Test 3: First-Time vs Repeat Classification**
```python
def test_dashboard_classification_from_matched_so():
    # Create customer with 1 matched order, 1 unmatched order
    # Verify customer classified as "first-time" (only matched order counts)
```

---

## Section 6: Matching Logic Improvements

### Current Matching Precedence

**From Code Review:**
1. **Order Number Exact Match:** `SalesOrder.order_number == DistributionLogEntry.order_number` (line 1470-1481 in `admin.py`)
2. **Fallback:** Manual match via PDF upload (line 479-621 in `admin.py`)

### Proposed Matching Rules (Deterministic)

**Rule 1: Order Number Exact Match (Primary)**
- **When:** Distribution has `order_number`, Sales Order exists with same `order_number`
- **Action:** Auto-match: `distribution.sales_order_id = sales_order.id`, `distribution.customer_id = sales_order.customer_id`
- **Confidence:** High (exact match)

**Rule 2: Date + Ship-To + SKU/Qty Match (Secondary)**
- **When:** Order number match fails, but:
  - `distribution.ship_date == sales_order.ship_date` (or within 7 days)
  - `distribution.facility_name` matches `sales_order.customer.facility_name` (normalized)
  - `distribution.sku` and `distribution.quantity` match `sales_order.lines` (sum)
- **Action:** Auto-match with lower confidence flag (admin can review)
- **Confidence:** Medium (requires manual review)

**Rule 3: Label Address Match (Tertiary)**
- **When:** Label PDF uploaded, address extracted matches distribution address
- **Action:** Link label PDF to distribution, suggest Sales Order match (admin confirms)
- **Confidence:** Low (requires admin confirmation)

### Implementation

**File:** `app/eqms/modules/rep_traceability/service.py` (new function)

```python
def match_distribution_to_sales_order(
    s,
    distribution: DistributionLogEntry,
    sales_order: SalesOrder,
    confidence: str = "high"  # "high", "medium", "low"
) -> bool:
    """
    Match distribution to sales order and update customer_id.
    Returns True if match successful, False otherwise.
    """
    if distribution.sales_order_id:
        return False  # Already matched
    
    # Validate match criteria
    if confidence == "high":
        # Order number must match
        if distribution.order_number != sales_order.order_number:
            return False
    elif confidence == "medium":
        # Date + facility + SKU/qty must match
        if not _validate_medium_match(distribution, sales_order):
            return False
    
    # Perform match
    distribution.sales_order_id = sales_order.id
    distribution.customer_id = sales_order.customer_id  # Link via SO
    
    # Audit
    record_event(
        s,
        action="distribution_log_entry.match_order",
        entity_type="DistributionLogEntry",
        entity_id=str(distribution.id),
        metadata={"sales_order_id": sales_order.id, "confidence": confidence},
    )
    
    return True
```

**Admin Review Queue:**
- Create route: `GET /admin/distribution-log/unmatched` (list unmatched distributions)
- Add "Suggest Match" button (runs medium-confidence matching)
- Add "Confirm Match" button (admin confirms suggested match)

---

## Section 7: Broken Distribution Detail Views

### Issue Inventory

**A. Distribution Detail View (`GET /admin/distribution-log/entry-details/<id>`)**
- **File:** `app/eqms/modules/rep_traceability/admin.py:349`
- **Status:** Likely working (returns JSON for modal)
- **Potential Issues:**
  - Missing attachments if `sales_order_id` is NULL
  - Customer stats calculated from all distributions (including unmatched)

**B. Single-Page PDF Upload (`POST /admin/distribution-log/<id>/upload-pdf`)**
- **File:** `app/eqms/modules/rep_traceability/admin.py:479`
- **Status:** **BROKEN** - Tries to create Sales Order without customer if `entry.customer_id` is NULL
- **Issue:** `SalesOrder.customer_id` is NOT NULL, but code does:
  ```python
  customer_id=entry.customer_id or po.get("customer_id")  # Can be None!
  ```
- **Fix:** Create customer from PDF parsed data or entry facility_name before creating SO

**C. Label PDF Upload**
- **File:** Not found in current code (may be missing)
- **Status:** **MISSING** - No route for label upload from distribution detail
- **Required:** Route to upload label PDF, extract address, match to distribution

**D. Attachments Rendering**
- **File:** `app/eqms/modules/rep_traceability/admin.py:472-475`
- **Status:** Likely working (returns attachments list)
- **Potential Issues:**
  - Attachments not shown if `sales_order_id` is NULL (should show distribution-level attachments)

### Fix Checklist

**P0-1: Fix Single-Page PDF Upload**
- **File:** `app/eqms/modules/rep_traceability/admin.py:479`
- **Change:**
  ```python
  # BEFORE (BROKEN):
  customer_id=entry.customer_id or po.get("customer_id")
  
  # AFTER (FIXED):
  if not entry.customer_id:
      # Create customer from PDF parsed data or entry facility_name
      customer = find_or_create_customer(
          s,
          facility_name=po.get("customer_name") or entry.facility_name,
          address1=po.get("address1") or entry.address1,
          city=po.get("city") or entry.city,
          state=po.get("state") or entry.state,
          zip=po.get("zip") or entry.zip,
      )
      customer_id = customer.id
  else:
      customer_id = entry.customer_id
  ```

**P0-2: Add Label PDF Upload Route**
- **File:** `app/eqms/modules/rep_traceability/admin.py` (new route)
- **Route:** `POST /admin/distribution-log/<id>/upload-label`
- **Logic:**
  1. Upload label PDF
  2. Parse address from label (use PDF parser or text extraction)
  3. Match address to distribution address (normalized)
  4. Link PDF to distribution: `distribution_entry_id = entry.id`, `pdf_type = "shipping_label"`
  5. If address matches, suggest Sales Order match (admin confirms)

**P0-3: Fix Attachments Rendering**
- **File:** `app/eqms/modules/rep_traceability/admin.py:349` (`distribution_log_entry_details()`)
- **Change:** Query attachments for both `sales_order_id` and `distribution_entry_id`:
  ```python
  attachments = (
      s.query(OrderPdfAttachment)
      .filter(
          db.or_(
              OrderPdfAttachment.sales_order_id == entry.sales_order_id,
              OrderPdfAttachment.distribution_entry_id == entry.id
          )
      )
      .all()
  )
  ```

**P1-1: Fix Customer Stats Calculation**
- **File:** `app/eqms/modules/rep_traceability/admin.py:420-453`
- **Change:** Filter customer stats to only matched distributions:
  ```python
  customer_entries = (
      s.query(DistributionLogEntry)
      .filter(
          DistributionLogEntry.customer_id == customer.id,
          DistributionLogEntry.sales_order_id.isnot(None)  # Only matched
      )
      .all()
  )
  ```

### Minimal UI Expectations

**Distribution Detail Modal:**
- Show distribution info (ship date, order number, SKU, lot, quantity)
- Show linked Sales Order (if matched) with link to SO detail
- Show customer info (if matched) with link to customer profile
- Show attachments (both SO-level and distribution-level) with download links
- Show "Upload PDF" button (if unmatched) to match distribution
- Show "Upload Label" button to upload shipping label

**Upload PDF Form:**
- File input for PDF
- Submit button
- Success message with link to created/matched Sales Order
- Error message if PDF parse fails or customer creation fails

---

## Section 8: Implementation Checklist

### P0 (Critical - Must Fix)

- [ ] **P0-1: Fix Sales Dashboard to Use Only Matched Sales Orders**
  - **File:** `app/eqms/modules/rep_traceability/service.py:529`
  - **Change:** Add filter `DistributionLogEntry.sales_order_id.isnot(None)` to all dashboard queries
  - **Test:** Verify unmatched distributions excluded from all metrics
  - **Validation:** Dashboard shows 0 orders if all distributions unmatched

- [ ] **P0-2: Fix ShipStation Sync to Not Create Customers**
  - **File:** `app/eqms/modules/shipstation_sync/service.py:358`
  - **Change:** Remove call to `_get_existing_customer_from_ship_to()`, set `customer_id = None` initially
  - **Test:** Verify ShipStation sync creates distributions only, customers come from SOs
  - **Validation:** New distributions have `customer_id = NULL` until matched to SO

- [ ] **P0-3: Fix PDF Import Error Handling**
  - **File:** `app/eqms/modules/rep_traceability/admin.py:1361`
  - **Change:** Add try/except around PDF parsing, splitting, customer creation
  - **Test:** Upload corrupted PDF, verify graceful error handling
  - **Validation:** Error messages shown to user, unmatched PDFs stored

- [ ] **P0-4: Fix Single-Page PDF Upload from Distribution Detail**
  - **File:** `app/eqms/modules/rep_traceability/admin.py:479`
  - **Change:** Create customer before creating Sales Order if `entry.customer_id` is NULL
  - **Test:** Upload PDF to unmatched distribution, verify SO created and linked
  - **Validation:** Distribution detail shows matched SO after upload

- [ ] **P0-5: Add Label PDF Upload Route**
  - **File:** `app/eqms/modules/rep_traceability/admin.py` (new route)
  - **Change:** Create `POST /admin/distribution-log/<id>/upload-label` route
  - **Test:** Upload label PDF, verify linked to distribution
  - **Validation:** Label PDF appears in distribution detail attachments

### P1 (High Priority)

- [ ] **P1-1: Customer Deduplication Script**
  - **File:** `scripts/dedupe_customers.py` (new)
  - **Change:** Implement merge logic for duplicate customers
  - **Test:** Run dry-run, verify correct merges identified
  - **Validation:** Customers merged, Sales Orders and Distributions updated

- [ ] **P1-2: Cleanup 0-Order Customers**
  - **File:** `scripts/cleanup_zero_order_customers.py` (new or update existing)
  - **Change:** Delete or hide customers with 0 matched Sales Orders
  - **Test:** Run dry-run, verify correct customers identified
  - **Validation:** Customer database shows only customers with ≥1 matched SO

- [ ] **P1-3: Fix Customer Creation Race Condition**
  - **File:** `app/eqms/modules/customer_profiles/service.py:99`
  - **Change:** Add retry logic for `IntegrityError` (duplicate `company_key`)
  - **Test:** Simulate concurrent customer creation, verify idempotency
  - **Validation:** No duplicate customers created under race conditions

- [ ] **P1-4: Fix Distribution Detail Attachments**
  - **File:** `app/eqms/modules/rep_traceability/admin.py:349`
  - **Change:** Query attachments for both `sales_order_id` and `distribution_entry_id`
  - **Test:** Verify attachments shown for both matched and unmatched distributions
  - **Validation:** Distribution detail shows all relevant attachments

### P2 (Polish)

- [ ] **P2-1: Add Matching Logic Service Function**
  - **File:** `app/eqms/modules/rep_traceability/service.py` (new function)
  - **Change:** Implement `match_distribution_to_sales_order()` with confidence levels
  - **Test:** Verify high/medium confidence matching works
  - **Validation:** Unmatched distributions can be auto-matched or suggested for review

- [ ] **P2-2: Add Admin Review Queue for Matches**
  - **File:** `app/eqms/modules/rep_traceability/admin.py` (new route)
  - **Change:** Create `GET /admin/distribution-log/unmatched` with "Suggest Match" buttons
  - **Test:** Verify suggested matches shown, admin can confirm/reject
  - **Validation:** Medium-confidence matches require admin confirmation

### Tests to Add

**Unit Tests:**
- `tests/test_sales_dashboard.py` - Verify unmatched distributions excluded
- `tests/test_pdf_import.py` - Verify error handling, customer creation
- `tests/test_customer_dedupe.py` - Verify merge logic, 0-order cleanup

**Integration Tests:**
- `tests/test_distribution_matching.py` - Verify distribution-SO matching pipeline
- `tests/test_label_upload.py` - Verify label PDF upload and matching

### Definition of Done

**For Each Task:**
- [ ] Code changes implemented
- [ ] Unit tests added and passing
- [ ] Integration tests added and passing
- [ ] Manual browser verification completed
- [ ] SQL verification queries run (if applicable)
- [ ] Documentation updated (if needed)

### How to Validate in Production

**1. Sales Dashboard Correctness:**
```sql
-- Count unmatched distributions
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NULL;

-- Count matched distributions
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NOT NULL;

-- Verify dashboard only counts matched
-- (Compare dashboard totals to matched count)
```

**2. Customer Deduplication:**
```sql
-- Find duplicate customers (same company_key)
SELECT company_key, COUNT(*) as cnt
FROM customers
GROUP BY company_key
HAVING COUNT(*) > 1;

-- Verify customers with 0 orders
SELECT c.id, c.facility_name
FROM customers c
LEFT JOIN sales_orders so ON so.customer_id = c.id
WHERE so.id IS NULL;
```

**3. PDF Import:**
- Upload bulk PDFs via `/admin/sales-orders/import-pdf`
- Verify no 500 errors
- Verify Sales Orders created
- Verify distributions linked
- Verify unmatched PDFs stored (if parse fails)

**4. Distribution Detail Views:**
- Go to Distribution Log → Click "Details" on matched distribution
- Verify modal shows Sales Order link, customer info, attachments
- Upload PDF to unmatched distribution
- Verify SO created and distribution matched
- Upload label PDF
- Verify label linked to distribution

---

## Summary

**Critical Fixes (P0):**
1. Sales dashboard must only count matched Sales Orders
2. ShipStation sync must not create customers
3. PDF import must handle errors gracefully
4. Distribution detail PDF upload must create customer if missing
5. Label PDF upload route must be implemented

**High Priority (P1):**
1. Customer deduplication script
2. Cleanup 0-order customers
3. Fix customer creation race conditions
4. Fix distribution detail attachments query

**Polish (P2):**
1. Matching logic service function
2. Admin review queue for matches

**Expected Outcome:**
- Data correctness: Only matched Sales Orders count toward metrics
- Customer database: Clean, no duplicates, no 0-order customers
- PDF import: Works reliably with proper error handling
- Distribution detail views: All uploads and views functional

---

**End of Phase 3 Plan**
