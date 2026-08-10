# Port vs Rewrite Decisions

**Date:** 2026-01-15  
**Purpose:** Two lists: "Safe to port" (small utilities/parsers) vs "Rewrite only" (bloat) with justifications

---

## Safe to Port (Small Utilities/Parsers/Mappers)

These are small, focused functions that can be extracted and reused without introducing bloat.

### 1. `canonical_customer_key(name: str) -> str`

**Location:** `Proto1.py` line ~2158, calls `normalize_company_key()` from `shipstation_sync.py`

**What it does:**
- Normalizes facility name to canonical key (uppercase, special chars removed)
- Example: "Hospital A" → "HOSPITALA", "St. Mary's Hospital" → "STMARYSHOSPITAL"
- Used for customer deduplication

**Port path:**
- Port to `app/eqms/modules/customer_profiles/utils.py` or `service.py`
- Keep dependency on `normalize_company_key()` if it's a small utility, or inline if needed

**Justification:**
- Small utility function (few lines)
- No dependencies on legacy DB or templates
- Core logic for customer deduplication
- Already used in SilqeQMS for similar purposes (if exists in `shipstation_sync`)

**Risk:** Low - isolated function, easy to test

---

### 2. `find_or_create_customer(...)`

**Location:** `Proto1.py` lines 136-211 (module-scope) and 2184-2253 (function-scope)

**What it does:**
- Finds existing customer by `company_key` (canonical key)
- Creates new customer if not found
- Updates existing customer if fields changed
- Returns customer dict/object

**Port path:**
- Port to `app/eqms/modules/customer_profiles/service.py`
- Adapt to use SQLAlchemy models instead of raw SQL
- Use SilqeQMS `db_session()` instead of `_customer_helpers_query_db()`

**Justification:**
- Core customer management logic
- Reusable pattern (find-or-create)
- No dependencies on rep-specific features
- Can be adapted to SilqeQMS patterns easily

**Risk:** Low - core logic, needs SQLAlchemy adaptation

---

### 3. `ensure_rep_assignment(customer_id, rep_id, ...)`

**Location:** `Proto1.py` lines 214-241

**What it does:**
- Assigns rep to customer (many-to-many)
- Handles primary rep logic (syncs with `customers.primary_rep_id`)
- Creates `customer_rep_assignments` record if not exists

**Port path:**
- Port to `app/eqms/modules/customer_profiles/service.py`
- Adapt to use SQLAlchemy models
- Use SilqeQMS `db_session()` and relationships

**Justification:**
- Small helper function
- Core logic for rep assignments
- No dependencies on legacy features
- Straightforward to adapt

**Risk:** Low - isolated function

---

### 4. `_normalize_ship_date_ymd(...)`

**Location:** `Proto1.py` lines 1271-1295 (helper function), used at line 4795

**What it does:**
- Normalizes ship dates to YYYY-MM-DD string format
- Handles datetime objects, date objects, strings, None
- Prevents "datetime object is not subscriptable" template errors

**Port path:**
- Already partially ported in `app/eqms/modules/rep_traceability/utils.py` (`parse_ship_date()`)
- Verify if additional normalization is needed

**Justification:**
- Small utility function
- Prevents template errors
- Already exists in SilqeQMS utils (verify completeness)

**Risk:** Low - already ported or partially ported

---

### 5. Field Normalization Helpers

**Location:** Various functions in `Proto1.py`

**What they do:**
- Text normalization (trim, strip, uppercase)
- SKU validation (check against valid values)
- Lot validation (check format `SLQ-#####`)
- Quantity validation (positive integer)

**Port path:**
- Already ported in `app/eqms/modules/rep_traceability/utils.py`
- Verify if additional helpers needed

**Justification:**
- Already partially implemented in SilqeQMS
- Small utilities, no bloat
- Core validation logic

**Risk:** Low - already ported

---

### 6. CSV Parsing Logic (if not already ported)

**Location:** `Proto1.py` CSV import functions (line ~4455)

**What it does:**
- Parses CSV rows
- Maps columns to distribution log fields
- Validates rows (SKU, lot format, quantity, date)

**Port path:**
- Already ported in `app/eqms/modules/rep_traceability/parsers/csv.py`
- Verify completeness

**Justification:**
- Already implemented in SilqeQMS
- Core import logic
- No dependencies on legacy features

**Risk:** Low - already ported

---

## Rewrite Only (Bloat/Complexity)

These features should be rewritten in SilqeQMS using existing patterns, not ported as-is.

### 1. `fetch_distribution_records()` (Normalization Logic)

**Location:** `Proto1.py` lines ~1573-1730 (complex function)

**What it does:**
- Normalizes data from `devices_distributed` + `device_distribution_records` tables
- Joins multiple tables
- Normalizes fields_json
- Groups shipments into orders

**Why rewrite:**
- SilqeQMS already has normalized schema (`distribution_log_entries` is one row per SKU/Lot)
- Legacy function is complex (150+ lines) with legacy table dependencies
- Not needed in SilqeQMS (schema is already normalized)
- Would introduce unnecessary complexity

**Rewritten approach:**
- Query `DistributionLogEntry` directly via SQLAlchemy
- No normalization needed (schema is normalized)
- Use relationships if needed

**Justification:**
- Legacy function works around denormalized legacy schema
- SilqeQMS schema is already normalized, no need for this complexity
- Porting would introduce bloat

---

### 2. `_build_distributions()` (Grouping Logic)

**Location:** `Proto1.py` (if exists, similar grouping logic)

**What it does:**
- Groups shipments into orders
- Aggregates items by SKU/lot

**Why rewrite:**
- Can be simplified for SilqeQMS normalized schema
- Use SQL GROUP BY instead of Python dict grouping
- Simpler aggregation logic

**Rewritten approach:**
- Query `distribution_log_entries` with GROUP BY
- Aggregate in SQL or simple Python dict
- No complex grouping logic needed

**Justification:**
- SilqeQMS normalized schema makes grouping simpler
- Porting legacy grouping logic would add unnecessary complexity

---

### 3. Sales Dashboard Aggregation Logic (Complex)

**Location:** `Proto1.py` lines 4633-4976 (`admin_sales_dashboard()`)

**What it does:**
- Computes aggregations (orders, units, customers)
- Classifies first-time vs repeat customers
- Aggregates SKU/lot breakdown
- Handles sync freshness checks
- Complex date normalization

**Why rewrite:**
- Contains bloat (sync freshness checks, iframe auth, complex date normalization)
- Can be simplified for SilqeQMS (no sync freshness needed initially)
- Normalized schema makes aggregations simpler

**Rewritten approach:**
- Compute aggregations on-demand from `distribution_log_entries`
- Simple SQL queries or SQLAlchemy aggregations
- Remove sync freshness complexity (not needed initially)
- Remove iframe token auth (if not needed)
- Simplify date normalization (use SQL date functions)

**Justification:**
- Legacy function is 350+ lines with lots of complexity
- SilqeQMS normalized schema makes aggregations straightforward
- Porting would bring in unnecessary bloat (sync checks, auth tokens)

---

### 4. Customer Notes/CRM Features

**Location:** `Proto1.py` customer note routes (lines 5175-5382)

**What it does:**
- Customer notes CRUD
- JSON API for notes (AJAX)
- Note editing/deletion

**Why rewrite:**
- Can use SilqeQMS existing patterns (similar to document_control module)
- Legacy code may have unnecessary complexity (AJAX/JSON handling)
- SilqeQMS templates can handle notes inline (no AJAX needed initially)

**Rewritten approach:**
- Use existing SilqeQMS form patterns
- Simple CRUD routes (no AJAX initially, can add later if needed)
- Reuse existing template patterns

**Justification:**
- Legacy may have AJAX complexity not needed initially
- SilqeQMS patterns are cleaner and consistent
- Can add AJAX later if needed (P2)

---

### 5. Hospital Targeting/Facility Search

**Location:** `Proto1.py` hospital/doctor targeting features

**What it does:**
- Facility cache (Parquet/CSV)
- Doctor search by facility
- Zip code to lat/lon mapping
- Leaflet map integration

**Why rewrite (actually, don't port):**
- Not core to distribution tracking
- Complex caching logic
- External API dependencies
- Rep-specific features

**Justification:**
- Explicitly excluded from migration (not core)
- Adds unnecessary complexity
- Not needed for Distribution Log, Tracing Reports, Customer Profiles, Sales Dashboard

---

### 6. Rep Dashboard Templates/Logic

**Location:** `Proto1.py` `/rep/<slug>` routes, `templates/rep_dashboard.html`

**What it does:**
- Rep-specific dashboard
- Rep login/logout
- Rep document uploads
- Rep portal UI

**Why rewrite (actually, don't port):**
- Explicitly excluded from migration (no rep pages)
- Rep-specific features not needed
- Would violate core constraints

**Justification:**
- Explicitly excluded in requirements
- Would introduce rep pages (violates constraints)
- Not needed for admin-only workflow

---

### 7. Email Sending Code

**Location:** `Proto1.py` email sending functions (`send_distribution_log_email()`, etc.)

**What it does:**
- SMTP email sending
- Email template rendering
- Attachment handling

**Why rewrite (actually, don't port):**
- Explicitly excluded from migration (no email sending)
- Replaced with .eml upload feature

**Justification:**
- Explicitly excluded in requirements
- Replaced with .eml upload (better audit trail)
- Would violate core constraints

---

### 8. PDF Parsing Logic (if complex)

**Location:** `Proto1.py` PDF import functions (line ~6886)

**What it does:**
- PDF text extraction
- Regex-based parsing (order number, facility, SKU/lot)
- Fragile (breaks on PDF format changes)

**Why rewrite (with caution):**
- Legacy PDF parsing is fragile (regex-based)
- Should be minimal (extract basic fields only)
- Document known limitations
- Provide manual entry fallback

**Rewritten approach:**
- Minimal PDF parsing (extract order number, basic fields)
- Use PDF library (PyPDF2 or pdfplumber)
- Document supported formats
- Provide manual entry fallback if parsing fails

**Justification:**
- Legacy parsing may be too complex or fragile
- Start fresh with minimal approach
- Document limitations clearly

**Priority:** P1/P2 (can be deferred)

---

## Decision Summary

### Safe to Port (Immediate)

1. ✅ `canonical_customer_key()` - Small utility
2. ✅ `find_or_create_customer()` - Core logic, adapt to SQLAlchemy
3. ✅ `ensure_rep_assignment()` - Small helper
4. ✅ Field normalization helpers - Already partially ported
5. ✅ CSV parsing logic - Already ported

### Rewrite Only (Simplified Implementation)

1. ❌ `fetch_distribution_records()` - Not needed (schema normalized)
2. ❌ `_build_distributions()` - Simplify with SQL GROUP BY
3. ❌ Sales Dashboard aggregation - Remove bloat, simplify
4. ❌ Customer notes/CRM - Use SilqeQMS patterns
5. ❌ PDF parsing - Start fresh, minimal approach

### Don't Port (Explicitly Excluded)

1. 🔵 Hospital targeting/facility search - Not core
2. 🔵 Rep dashboard - Explicitly excluded
3. 🔵 Email sending - Explicitly excluded
4. 🔵 Rep-specific file storage - Not needed

---

## Key Principle

**Port only small, focused utilities.** Rewrite everything else using SilqeQMS patterns to avoid bringing in legacy bloat.

**Rule of thumb:**
- If function is < 50 lines and has no dependencies on legacy features → **Port**
- If function is > 50 lines or has complex dependencies → **Rewrite**
- If feature is explicitly excluded → **Don't port**

---

## References

- **Legacy Rep QMS:** `C:\Users\Ethan\OneDrive\Desktop\UI\RepsQMS\Proto1.py`
- **Feature Map:** [docs/review/01_REP_QMS_FEATURE_MAP.md](docs/review/01_REP_QMS_FEATURE_MAP.md)
- **Migration Plan:** [docs/review/03_LEAN_MIGRATION_PLAN.md](docs/review/03_LEAN_MIGRATION_PLAN.md)
