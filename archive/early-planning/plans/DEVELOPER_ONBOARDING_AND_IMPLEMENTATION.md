# Developer Onboarding: SilqeQMS System Reliability and Cleanup

**Date:** 2026-01-27  
**Purpose:** Comprehensive guide for new developer to understand system objectives, implement reliability fixes, and remove legacy code.  
**Scope:** No new features. Focus on correctness, reliability, and cleanup.

---

## Part 1: System Overview and Objectives

### What is SilqeQMS?

**SilqeQMS** is a Flask-based modular monolith eQMS (Electronic Quality Management System) designed for small teams. It provides:

- **Rep Traceability Module:** Distribution Log, Sales Orders, Customer Profiles, Sales Dashboard, Tracing Reports
- **Equipment & Supplies Module:** Equipment master data, calibration/PM tracking, supplier management
- **Manufacturing Module:** Production lot tracking (Suspension, ClearTract Foley Catheters)
- **Document Control Module:** QMS document management
- **Core Infrastructure:** RBAC, audit trail, storage abstraction (local/S3), Alembic migrations

**Key Design Principles:**
- **No rep pages:** All functionality under `/admin/*` only
- **No email sending:** Approvals are `.eml` uploads only
- **Admin has full editability:** No complex approval gates (RBAC stays, but Admin can do everything)
- **Modular monolith:** Single deployable web service with clear module boundaries

### System Architecture

**Technology Stack:**
- **Framework:** Flask (Python 3.12+)
- **Database:** SQLite (dev) / PostgreSQL (production)
- **Migrations:** Alembic
- **Server:** Flask dev server (local) / Gunicorn (production)
- **Storage:** Local filesystem (dev) / S3-compatible (production)
- **Deployment:** DigitalOcean App Platform

**Project Structure:**
```
SilqQMS/
├── app/
│   ├── eqms/                    # Core eQMS modules
│   │   ├── modules/             # Feature modules
│   │   │   ├── rep_traceability/ # Distribution Log, Sales Orders, Customers, Dashboard
│   │   │   ├── customer_profiles/ # Customer management
│   │   │   ├── shipstation_sync/ # ShipStation API integration
│   │   │   └── ...
│   │   ├── auth.py              # Authentication
│   │   ├── rbac.py              # Role-Based Access Control
│   │   ├── audit.py             # Audit trail
│   │   └── storage.py           # Storage abstraction
│   └── wsgi.py                  # WSGI entry point
├── migrations/                  # Alembic migrations
├── scripts/                     # Utility scripts
│   ├── start.py                # Production startup (runs migrations + gunicorn)
│   ├── release.py              # Migrations + seed
│   └── init_db.py              # Database initialization/seed
├── docs/                        # Documentation
└── requirements.txt             # Python dependencies
```

---

## Part 2: Canonical Data Pipeline (CRITICAL)

### The Intended Flow

**Correct Pipeline:**
```
ShipStation API
    ↓
Distribution Log Entry (clean, normalized, sales_order_id = NULL)
    ↓
PDF Import / Manual Entry → Sales Order (source of truth for customer)
    ↓
Sales Order → Customer (created/updated from SO ship-to fields)
    ↓
Distribution matched to Sales Order (sales_order_id set, customer_id from SO)
    ↓
Sales Dashboard (reads ONLY matched distributions: sales_order_id IS NOT NULL)
```

### System Invariants (Must Enforce)

**Invariant 1: Customer Profile Existence**
- A Customer profile appears **only if** there exists ≥1 matched Sales Order
- Customers are created/updated **only** from Sales Orders (PDF import, manual entry)
- ShipStation sync **must not** create customers directly
- Customers with 0 matched Sales Orders **must not** appear in Customer Database UI

**Invariant 2: Sales Dashboard Aggregation**
- Dashboard aggregates **only** from matched Sales Orders (`sales_order_id IS NOT NULL`)
- Unmatched distributions **must not** count toward:
  - Total orders
  - Total units
  - Total customers
  - First-time vs repeat classification
  - SKU breakdown
  - Lot tracking

**Invariant 3: Distribution Independence**
- Distributions can exist without a matched Sales Order temporarily
- Until matched, distributions are "orphaned" and excluded from aggregations
- Distributions can be matched later via PDF upload or manual match

**Invariant 4: Sales Order as Customer Source of Truth**
- When a distribution is matched to a Sales Order, `distribution.customer_id = sales_order.customer_id`
- Customer identity comes from Sales Order ship-to fields, **not** ShipStation raw data

**Invariant 5: Label PDF Linkage**
- Label PDFs are linked to a Distribution when address/distribution linkage is satisfied
- Unmatched label PDFs stored with `distribution_entry_id = NULL`

---

## Part 3: Current System State

### What's Working

✅ **Core Infrastructure:**
- Authentication and RBAC
- Audit trail
- Storage abstraction (local + S3)
- Alembic migrations
- Admin shell UI

✅ **Rep Traceability Module:**
- Distribution Log (manual entry, CSV import, view/edit/export)
- Sales Orders (list, detail, PDF import routes exist)
- Customer Profiles (list, detail, notes)
- Sales Dashboard (route exists, aggregates computed)
- Tracing Reports (generate CSV, upload .eml approvals)

✅ **PDF Infrastructure:**
- PDF splitting implemented (`split_pdf_into_pages()`)
- PDF parsing implemented (`parse_sales_orders_pdf()`)
- Page-level storage (individual pages stored as attachments)

✅ **Customer Rebuild Script:**
- `scripts/rebuild_customers_from_sales_orders.py` exists and works
- Creates customers from Sales Orders (canonical source)

### What's Broken (Must Fix)

❌ **P0 Critical Issues:**

1. **Sales Dashboard Shows Wrong Data**
   - **Problem:** Dashboard aggregates from **all** distributions (including unmatched)
   - **Location:** `app/eqms/modules/rep_traceability/service.py:529` (`compute_sales_dashboard()`)
   - **Fix Required:** Filter to only matched distributions: `WHERE sales_order_id IS NOT NULL`

2. **PDF Import Failing (Internal Server Error)**
   - **Problem:** Bulk PDF import route throws 500 errors, no error handling
   - **Location:** `app/eqms/modules/rep_traceability/admin.py:1361` (`sales_orders_import_pdf_bulk()`)
   - **Fix Required:** Add comprehensive error handling, size validation, dependency checks

3. **ShipStation Sync Still Creates Customers**
   - **Problem:** `_get_existing_customer_from_ship_to()` still called as fallback
   - **Location:** `app/eqms/modules/shipstation_sync/service.py:358`
   - **Fix Required:** Remove customer creation, set `customer_id = NULL` initially

4. **Distribution Detail PDF Upload Fails**
   - **Problem:** Tries to create SO without customer if `entry.customer_id` is NULL
   - **Location:** `app/eqms/modules/rep_traceability/admin.py:479` (`distribution_log_upload_pdf()`)
   - **Fix Required:** Create customer from PDF data before creating SO

5. **Label PDF Upload Route Missing**
   - **Problem:** No route for uploading label PDFs from distribution detail
   - **Fix Required:** Implement `POST /admin/distribution-log/<id>/upload-label`

❌ **P1 High Priority Issues:**

6. **Customer Database Has Duplicates**
   - **Problem:** Multiple customers with same `company_key` (should be unique)
   - **Fix Required:** Deduplication script + merge logic

7. **Customers with 0 Orders**
   - **Problem:** Customers with no matched Sales Orders (from dev/backfills)
   - **Fix Required:** Cleanup script to delete or hide 0-order customers

8. **Customer Creation Race Conditions**
   - **Problem:** Concurrent customer creation can cause duplicate `company_key` errors
   - **Location:** `app/eqms/modules/customer_profiles/service.py:99` (`find_or_create_customer()`)
   - **Fix Required:** Add retry logic for `IntegrityError`

9. **Distribution Detail Attachments Not Shown**
   - **Problem:** Attachments not queried for unmatched distributions
   - **Location:** `app/eqms/modules/rep_traceability/admin.py:349` (`distribution_log_entry_details()`)
   - **Fix Required:** Query attachments for both `sales_order_id` and `distribution_entry_id`

---

## Part 4: Implementation Checklist

### P0 Critical Fixes (Must Do First)

#### P0-1: Fix Sales Dashboard to Use Only Matched Sales Orders

**Objective:** Dashboard must only aggregate from distributions with `sales_order_id IS NOT NULL`.

**Files to Change:**
- `app/eqms/modules/rep_traceability/service.py:529` (`compute_sales_dashboard()`)

**Implementation:**
```python
# CURRENT (WRONG):
q = s.query(DistributionLogEntry)
if start_date:
    q = q.filter(DistributionLogEntry.ship_date >= start_date)
window_entries = q.order_by(...).all()  # Includes unmatched!

# FIXED:
q = s.query(DistributionLogEntry).filter(
    DistributionLogEntry.sales_order_id.isnot(None)  # Only matched
)
if start_date:
    q = q.filter(DistributionLogEntry.ship_date >= start_date)
window_entries = q.order_by(...).all()
```

**Also Fix:** Recent orders classification (line 662):
```python
# CURRENT (WRONG):
if not e.order_number or not e.customer_id:
    continue

# FIXED:
if not e.order_number or not e.customer_id or not e.sales_order_id:
    continue  # Only process matched distributions
```

**Acceptance Criteria:**
- [ ] Dashboard totals match SQL: `SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NOT NULL`
- [ ] Unmatched distributions do not appear in customer lists
- [ ] First-time vs repeat classification uses only matched distributions

**Verification:**
```sql
-- Should match dashboard totals
SELECT COUNT(DISTINCT order_number) FROM distribution_log_entries WHERE sales_order_id IS NOT NULL;
```

---

#### P0-2: Fix PDF Import Error Handling

**Objective:** Add comprehensive error handling to bulk PDF import route.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py:1361` (`sales_orders_import_pdf_bulk()`)
- `app/eqms/__init__.py` (add `MAX_CONTENT_LENGTH` config)
- `app/eqms/templates/admin/sales_orders/import.html` (add client-side validation)

**Implementation Steps:**

1. **Add request size validation:**
   ```python
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
   MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB total
   # Validate before processing
   ```

2. **Add dependency checks:**
   ```python
   try:
       import pdfplumber
       import PyPDF2
   except ImportError as e:
       flash("PDF parsing libraries are not installed.", "danger")
       return redirect(...)
   ```

3. **Wrap all operations in try/except:**
   - PDF splitting
   - PDF parsing
   - Customer creation
   - Sales Order creation
   - Database commits

4. **Add structured logging:**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.error(f"PDF split failed: {e}", exc_info=True)
   ```

5. **Set Flask request size limit:**
   ```python
   # In app/eqms/__init__.py (create_app()):
   app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
   ```

6. **Add client-side validation:**
   - JavaScript to check file sizes before submission
   - Show loading indicator during upload

**Acceptance Criteria:**
- [ ] Large files rejected with clear error message
- [ ] Missing dependencies detected and user-friendly error shown
- [ ] All exceptions caught and logged with stack traces
- [ ] User sees clear error messages for all failure modes
- [ ] Unmatched/unparsed PDFs stored for later review
- [ ] Success message shows accurate counts

**Verification:**
- Upload 15MB PDF → Should show "File too large" error
- Temporarily remove pdfplumber → Should show "libraries not installed" error
- Upload corrupted PDF → Should store as unmatched, show warning message

---

#### P0-3: Fix ShipStation Sync to Not Create Customers

**Objective:** ShipStation sync creates distributions only; customers come from Sales Orders.

**Files to Change:**
- `app/eqms/modules/shipstation_sync/service.py:358`

**Implementation:**
```python
# CURRENT (WRONG):
if existing_sales_order and existing_sales_order.customer_id:
    customer = s.query(Customer).filter(Customer.id == existing_sales_order.customer_id).first()
else:
    # Fallback: Try to find existing customer (DO NOT create new ones)
    customer = _get_existing_customer_from_ship_to(s, ship_to)  # ❌ Still creates customers!

# FIXED:
if existing_sales_order and existing_sales_order.customer_id:
    customer = s.query(Customer).filter(Customer.id == existing_sales_order.customer_id).first()
else:
    # No customer - distribution will be unmatched (admin matches via PDF import later)
    customer = None

# When creating distribution:
entry = DistributionLogEntry(
    # ... existing fields ...
    customer_id=None,  # Will be set via Sales Order match
    sales_order_id=None,  # Will be set if match found
)

# After creating entry, try to match to Sales Order:
if order_number:
    matching_order = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_number == order_number)
        .first()
    )
    if matching_order:
        entry.sales_order_id = matching_order.id
        entry.customer_id = matching_order.customer_id  # Link via SO
```

**Also:** Mark `_get_existing_customer_from_ship_to()` as deprecated or delete it.

**Acceptance Criteria:**
- [ ] ShipStation sync does NOT call `_get_existing_customer_from_ship_to()`
- [ ] Distributions created from ShipStation have `customer_id = NULL` initially
- [ ] After matching to Sales Order, `distribution.customer_id = sales_order.customer_id`
- [ ] Customers are **only** created from Sales Orders

**Verification:**
```sql
-- Should return 0 rows (customers created with or after SOs)
SELECT c.id, c.facility_name, c.created_at, so.created_at
FROM customers c
JOIN sales_orders so ON so.customer_id = c.id
WHERE c.created_at < so.created_at;
```

---

#### P0-4: Fix Distribution Detail PDF Upload

**Objective:** Create customer from PDF data before creating Sales Order if distribution has no customer.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py:479` (`distribution_log_upload_pdf()`)

**Implementation:**
```python
# CURRENT (BROKEN):
customer_id=entry.customer_id or po.get("customer_id")  # Can be None!

# FIXED:
if not entry.customer_id:
    # Create customer from PDF parsed data or entry facility_name
    from app.eqms.modules.customer_profiles.service import find_or_create_customer
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

# Then create Sales Order with valid customer_id
sales_order = SalesOrder(
    # ...
    customer_id=customer_id,  # Now guaranteed to be valid
    # ...
)
```

**Acceptance Criteria:**
- [ ] Upload PDF to unmatched distribution (no customer_id) → SO created successfully
- [ ] Customer created from PDF data if not exists
- [ ] Distribution linked to SO after upload

**Verification:**
- Go to Distribution Log → Find unmatched distribution → Upload PDF → Verify SO created and distribution matched

---

#### P0-5: Add Label PDF Upload Route

**Objective:** Implement route for uploading label PDFs from distribution detail view.

**Files to Create/Change:**
- `app/eqms/modules/rep_traceability/admin.py` (new route)

**Implementation:**
```python
@bp.post("/distribution-log/<int:entry_id>/upload-label")
@require_permission("distribution_log.edit")
def distribution_log_upload_label(entry_id: int):
    """Upload shipping label PDF to distribution entry."""
    s = db_session()
    u = _current_user()
    
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        flash("Distribution entry not found.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))
    
    f = request.files.get("label_file")
    if not f or not f.filename:
        flash("Please select a label PDF file.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))
    
    pdf_bytes = f.read()
    filename = f.filename or "label.pdf"
    
    # Try to parse address from label (optional - can be done later)
    # For now, just store the PDF linked to distribution
    
    _store_pdf_attachment(
        s,
        pdf_bytes=pdf_bytes,
        filename=filename,
        pdf_type="shipping_label",
        sales_order_id=None,
        distribution_entry_id=entry.id,  # Link to distribution
        user=u,
    )
    
    s.commit()
    flash(f"Label PDF uploaded and linked to distribution.", "success")
    return redirect(url_for("rep_traceability.distribution_log_list"))
```

**Also:** Add upload button to distribution detail modal/template.

**Acceptance Criteria:**
- [ ] Route exists and accepts label PDF uploads
- [ ] Label PDF stored with `distribution_entry_id` set
- [ ] Label PDF appears in distribution detail attachments

**Verification:**
- Go to Distribution Log → Click "Details" → Upload label PDF → Verify label appears in attachments

---

### P1 High Priority Fixes

#### P1-1: Customer Deduplication Script

**Objective:** Merge duplicate customers with same `company_key`.

**Files to Create:**
- `scripts/dedupe_customers.py` (new)

**Implementation:**
- Find customers with duplicate `company_key`
- Keep customer with most matched Sales Orders (or oldest if tie)
- Update all FKs (Sales Orders, Distributions, Notes) to point to kept customer
- Delete merged customer records
- Log all operations in audit trail

**Acceptance Criteria:**
- [ ] Script identifies duplicate customers
- [ ] Merges customers correctly (all FKs updated)
- [ ] No data loss (all relationships preserved)

**Verification:**
```sql
-- Should return 0 rows after deduplication
SELECT company_key, COUNT(*) FROM customers GROUP BY company_key HAVING COUNT(*) > 1;
```

---

#### P1-2: Cleanup 0-Order Customers

**Objective:** Delete or hide customers with no matched Sales Orders.

**Files to Create/Update:**
- `scripts/cleanup_zero_order_customers.py` (new or update existing)

**Implementation:**
- Find customers with no matched Sales Orders: `LEFT JOIN sales_orders WHERE so.id IS NULL`
- Check for FK constraints (distributions, notes)
- Delete if safe, or mark as inactive if FKs prevent deletion
- Log operations

**Acceptance Criteria:**
- [ ] Customers with 0 orders identified
- [ ] Safely deleted or hidden
- [ ] No broken FKs

**Verification:**
```sql
-- Should return 0 rows after cleanup
SELECT COUNT(*) FROM customers c LEFT JOIN sales_orders so ON so.customer_id = c.id WHERE so.id IS NULL;
```

---

#### P1-3: Fix Customer Creation Race Condition

**Objective:** Add retry logic for concurrent customer creation.

**Files to Change:**
- `app/eqms/modules/customer_profiles/service.py:99` (`find_or_create_customer()`)

**Implementation:**
```python
try:
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

**Acceptance Criteria:**
- [ ] Concurrent customer creation doesn't cause duplicate key errors
- [ ] Idempotent (safe to call multiple times)

---

#### P1-4: Fix Distribution Detail Attachments Query

**Objective:** Show attachments for both matched and unmatched distributions.

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py:349` (`distribution_log_entry_details()`)

**Implementation:**
```python
# CURRENT (MISSING):
attachments = (
    s.query(OrderPdfAttachment)
    .filter(OrderPdfAttachment.sales_order_id == entry.sales_order_id)
    .all()
)  # Only shows SO-level attachments

# FIXED:
attachments = (
    s.query(OrderPdfAttachment)
    .filter(
        db.or_(
            OrderPdfAttachment.sales_order_id == entry.sales_order_id,
            OrderPdfAttachment.distribution_entry_id == entry.id
        )
    )
    .all()
)  # Shows both SO-level and distribution-level attachments
```

**Acceptance Criteria:**
- [ ] Attachments shown for matched distributions (SO-level)
- [ ] Attachments shown for unmatched distributions (distribution-level)
- [ ] Label PDFs appear in distribution detail

---

### P2 Polish (Optional, Can Defer)

#### P2-1: Matching Logic Service Function
- Implement `match_distribution_to_sales_order()` with confidence levels
- Add admin review queue for suggested matches

#### P2-2: Customer Key Edge Case Tests
- Add unit tests for `canonical_customer_key()` edge cases
- Document normalization rules

---

## Part 5: Legacy Code Removal

### Safe to Delete

**1. Empty `legacy/` Directory**
- **Path:** `legacy/` (if exists and empty)
- **Action:** Delete entire directory
- **Verification:** `grep -r "legacy" app/` → Should return nothing

**2. Deprecated `customer_name` Field from UI**
- **Path:** `app/eqms/templates/admin/distribution_log/edit.html:93`
- **Action:** Hide field (change to `type="hidden"` or remove from form)
- **Note:** Keep field in model for data compatibility

**3. Deprecated Functions**
- **Path:** `app/eqms/modules/shipstation_sync/service.py` (`_get_existing_customer_from_ship_to()`)
- **Action:** Mark as deprecated or delete if not used elsewhere
- **Verification:** `grep -r "_get_existing_customer_from_ship_to" app/` → Should return nothing after P0-3 fix

### Keep (All in Use)

✅ All scripts in `scripts/` (all appear to be in use)  
✅ All templates (all appear to be rendered by routes)  
✅ All models (all appear to be used by routes)  
✅ All parsers (all appear to be used by import routes)

---

## Part 6: Verification and Testing

### SQL Verification Queries

**1. Dashboard Correctness:**
```sql
-- Unmatched distributions should NOT be counted
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NULL;

-- Dashboard totals should match:
SELECT COUNT(DISTINCT order_number) FROM distribution_log_entries WHERE sales_order_id IS NOT NULL;
```

**2. Customer Cleanliness:**
```sql
-- No duplicates
SELECT company_key, COUNT(*) FROM customers GROUP BY company_key HAVING COUNT(*) > 1;

-- No 0-order customers
SELECT COUNT(*) FROM customers c LEFT JOIN sales_orders so ON so.customer_id = c.id WHERE so.id IS NULL;
```

**3. Pipeline Enforcement:**
```sql
-- Customers created from Sales Orders (not ShipStation)
SELECT c.id, c.facility_name, c.created_at, so.created_at
FROM customers c
JOIN sales_orders so ON so.customer_id = c.id
WHERE c.created_at < so.created_at;
-- Should return 0 rows
```

### Browser Verification

**1. Sales Dashboard:**
- Go to `/admin/sales-dashboard`
- Verify totals match SQL query results (only matched distributions)
- Verify unmatched distributions do not appear

**2. PDF Import:**
- Upload bulk PDFs via `/admin/sales-orders/import-pdf`
- Verify no 500 errors
- Verify Sales Orders created and linked to distributions
- Verify unmatched PDFs stored (if parse fails)

**3. Distribution Detail:**
- Go to Distribution Log → Click "Details" on unmatched distribution
- Upload PDF → Verify SO created and distribution matched
- Upload label PDF → Verify label linked to distribution
- Verify attachments shown (both SO-level and distribution-level)

**4. Customer Database:**
- Go to `/admin/customers`
- Verify no duplicates (same facility name appears only once)
- Verify all customers have ≥1 matched Sales Order

---

## Part 7: Implementation Order

### Phase 1: Critical Fixes (P0) - Do First

1. **P0-1:** Fix Sales Dashboard (filter to matched SOs only)
2. **P0-2:** Fix PDF Import (error handling, size validation)
3. **P0-3:** Fix ShipStation Sync (remove customer creation)
4. **P0-4:** Fix Distribution Detail PDF Upload (create customer if missing)
5. **P0-5:** Add Label PDF Upload Route

### Phase 2: Data Cleanup (P1) - Do After P0

6. **P1-1:** Customer Deduplication Script
7. **P1-2:** Cleanup 0-Order Customers
8. **P1-3:** Fix Customer Creation Race Condition
9. **P1-4:** Fix Distribution Detail Attachments Query

### Phase 3: Legacy Cleanup - Do After P0/P1

10. Delete empty `legacy/` directory (if exists)
11. Hide deprecated `customer_name` field from UI
12. Remove deprecated `_get_existing_customer_from_ship_to()` function

---

## Part 8: Definition of Done

**For Each Task:**
- [ ] Code changes implemented
- [ ] Unit tests added and passing (if applicable)
- [ ] Manual browser verification completed
- [ ] SQL verification queries run (if applicable)
- [ ] No regressions (existing functionality still works)
- [ ] Documentation updated (if needed)

**Overall Success Criteria:**
- ✅ Sales dashboard shows only matched Sales Orders
- ✅ PDF import works reliably (no 500 errors, proper error handling)
- ✅ Customer database is clean (no duplicates, no 0-order customers)
- ✅ ShipStation sync creates distributions only (no direct customer creation)
- ✅ Distribution detail views work (PDF upload, label upload, attachments)
- ✅ All verification queries pass (SQL + browser)
- ✅ No legacy code interfering with maintainability

---

## Part 9: Reference Documents

**Planning Documents:**
- `docs/plans/PHASE3_DATA_CORRECTNESS_AND_PDF_IMPORT.md` - Detailed Phase 3 plan
- `docs/plans/PHASE3_EXEC_SUMMARY.md` - Executive summary
- `docs/plans/DEVELOPER_PROMPT_PDF_IMPORT_FIXES.md` - PDF import fixes
- `docs/plans/REPO_CLEANUP_PHASE1.md` - Legacy code cleanup

**System Documentation:**
- `README.md` - Setup and usage guide
- `docs/REP_SYSTEM_MIGRATION_MASTER.md` - Master migration spec
- `docs/REP_SYSTEM_MINIMAL_SCHEMA.md` - Database schema
- `docs/REP_SYSTEM_UI_MAP.md` - UI routes map

---

## Part 10: Getting Started

### Step 1: Understand the System
- Read this document completely
- Review `README.md` for setup instructions
- Review `docs/plans/PHASE3_EXEC_SUMMARY.md` for problem summary

### Step 2: Set Up Development Environment
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set up database
alembic upgrade head
python scripts\init_db.py

# Start server
python -m flask --app app.wsgi run --port 8080
```

### Step 3: Start with P0-1 (Sales Dashboard Fix)
- This is the most critical fix
- Easiest to verify (SQL query + browser check)
- Sets the foundation for other fixes

### Step 4: Work Through P0 Tasks Sequentially
- Each P0 task builds on the previous
- Test after each change
- Commit after each working fix

### Step 5: Move to P1 Tasks
- Only after all P0 tasks complete
- Run cleanup scripts in dry-run mode first
- Verify data before and after cleanup

### Step 6: Legacy Cleanup
- Only after all fixes are working
- Verify nothing breaks after deletion

---

**End of Developer Onboarding Document**
