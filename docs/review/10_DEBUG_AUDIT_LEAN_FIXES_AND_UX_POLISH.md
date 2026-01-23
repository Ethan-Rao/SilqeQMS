# 10 DEBUG AUDIT — Lean Fixes & UX Polish (Correctness • Maintainability • Professional Admin UX)

**Audit Date:** 2026-01-23  
**Baseline Spec:** `docs/plans/IMMEDIATE_FIXES_AND_UI_IMPROVEMENTS.md`

Example PDFs inspected (present in project root):
- `2025 Sales Orders.pdf`
- `Label1.pdf`

LotLog source-of-truth:
- `app/eqms/data/LotLog.csv` (also referenced via `SHIPSTATION_LOTLOG_PATH` / `LotLog_Path`)

---

## ⚠️ DEPLOYMENT STATUS — CRITICAL FAILURE ANALYSIS

### Latest Deployment Logs (Jan 23 00:43)

```
Jan 23 00:43:11  === SilqeQMS release start ===
Jan 23 00:43:11  ENV=production
Jan 23 00:43:11  Running Alembic migrations...
Jan 23 00:43:13  [diag] sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
Jan 23 00:43:14  INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
Jan 23 00:43:14  INFO  [alembic.runtime.migration] Will assume transactional DDL.
Jan 23 00:43:14  Migrations complete.
Jan 23 00:43:14  Seeding permissions/admin (idempotent)...
Jan 23 00:43:14  Initialized database (seed_only).
Jan 23 00:43:14  Admin email: ethanr@silq.tech
Jan 23 00:43:14  Seed complete.
Jan 23 00:43:14  === SilqeQMS release done ===
Jan 23 00:42:44  ERROR failed health checks after 8 attempts with error Readiness probe failed: dial tcp 10.244.22.91:8080: connect: connection refused
```

### Key Observations

1. **✅ Migrations PASSED** — The diagnostic shows `server_default=sa.text("false")` (correct Postgres boolean)
2. **✅ Release script COMPLETED** — "=== SilqeQMS release done ===" logged
3. **❌ Health check FAILED** — "connection refused" on port 8080 means gunicorn never started

### Root Cause: PORT Environment Variable Missing

**Current Run Command:**
```bash
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload
```

**Problem:** `$PORT` expands to empty string if PORT is not set, causing:
```bash
gunicorn app.wsgi:app --bind 0.0.0.0: --workers 2 ...
#                                  ↑ INVALID BIND ADDRESS
```

**Environment Variables Listed:** PORT is NOT in the list provided. DigitalOcean App Platform should inject it automatically, but it appears missing.

### Immediate Fix Options

**Option A: Add PORT to environment variables**
```
PORT=8080
```

**Option B: Fix run command to use default (RECOMMENDED)**
```bash
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60 --preload
```

**Option C: Use Dockerfile CMD instead**
The Dockerfile already has the correct command with fallback:
```dockerfile
CMD ["sh", "-c", "gunicorn app.wsgi:app --preload --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60"]
```
Remove the custom Run Command in DO settings and let it use Dockerfile CMD.

### Additional Environment Variable Issue

**SECRET_KEY shows a placeholder:**
```
SECRET_KEY=<generate-new-random-32-char-key>
```

This is literally set to a placeholder string with angle brackets. While it won't crash the app (since it's not exactly "change-me"), it's:
1. Not cryptographically random
2. Contains special characters that could cause issues
3. Should be replaced with an actual 32+ character random string

**Generate a proper secret key:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 🔧 QUICK FIX CHECKLIST

1. **Add to Environment Variables:**
   ```
   PORT=8080
   ```

2. **Replace SECRET_KEY with:**
   ```
   SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
   ```

3. **Redeploy** — No code changes needed, just env var updates.

4. **Verify:**
   - Check DO logs for "Listening at: http://0.0.0.0:8080"
   - Visit app URL and confirm it loads

---

## A) Snapshot Summary (Top 10 findings)

1. **🚨 P0 DEPLOYMENT BLOCKER**: Gunicorn fails to start because `$PORT` env var is missing/empty. Run command uses `--bind 0.0.0.0:$PORT` without fallback. **Fix: Add `PORT=8080` to env vars OR change run command to use `${PORT:-8080}`**.

2. **✅ MIGRATION NOW PASSING**: Latest deployment shows `server_default=sa.text("false")` diagnostic — Postgres boolean issue is RESOLVED. Migrations complete successfully.

3. **⚠️ SECRET_KEY is placeholder**: Set to literal `<generate-new-random-32-char-key>` — should be replaced with actual random hex string.

4. **✅ ORM Ambiguity FIXED**: `CustomerRep.rep` relationship correctly specifies `foreign_keys=[rep_id]` (line 90 of `customer_profiles/models.py`).

5. **✅ Notes System WORKING**: Global notes modal in `_layout.html` (lines 60–125) correctly calls `/admin/notes/modal/<entity_type>/<entity_id>` and `/admin/notes/create`. CSRF token properly sent.

6. **✅ Lot Tracking CORRECTLY IMPLEMENTED**: `compute_sales_dashboard()` (lines 577–641) loads `lot_years` from LotLog, filters to 2025+ lots, aggregates **all-time** distributions.

7. **🟡 PDF Parsing PARTIALLY WORKING**: Parser exists with text fallback + label detection. Fails when PDFs contain images/non-selectable text (expected limitation).

8. **✅ Distribution Details Modal COMPLETE**: All spec sections present: Entry, Order, Customer, Stats, Attachments, Notes, Quick Actions.

9. **✅ LEGACY CODE MINIMAL**: Only `legacy/DO_NOT_USE__REFERENCE_ONLY/` contains reference HTML files. No active legacy code.

10. **🔴 IMMEDIATE ACTION**: Fix PORT env var to unblock deployment. Generate proper SECRET_KEY.

---

## B) Spec Compliance Matrix (from IMMEDIATE_FIXES_AND_UI_IMPROVEMENTS.md)

| Spec Item | Status | Evidence | Fix Note |
|-----------|--------|----------|----------|
| **A) Distribution Log modal readability** | ✅ | `distribution_log/list.html:162-338` — modal has 700px width, 80vh height, backdrop, sections, scroll containment | Complete |
| **B) Sales Dashboard two-column layout** | ✅ | `sales_dashboard/index.html:55-214` — left column has NEW/REPEAT lists, right has SKU/Lot | Complete |
| **C) Lot Tracking accuracy (2025+, all-time, Active Inventory)** | ✅ | `service.py:577-641` — loads `lot_years`, filters to ≥2025, aggregates all-time, computes active inventory | Complete |
| **D) Customers page crash fix** | 🟡 | Model fixed (`models.py:90`), but deployment blocked by migration failure | Fix deployment |
| **D) Rep assignment UI** | ✅ | `customer_profiles/admin.py:customer_reps_update`, customer detail template has multi-select | Complete |
| **E) PDF import robustness** | 🟡 | `parsers/pdf.py` has text fallback + label parsing; stores PDFs on failure; but extraction limited when text not selectable | Document limitation |
| **E) PDF bulk upload** | ✅ | `admin.py:1200-1294` — `sales_orders_import_pdf_bulk` accepts multiple files | Complete |
| **E) PDF per-order upload** | ✅ | `admin.py:1148-1178` — `sales_order_upload_pdf` route exists | Complete |
| **E) PDF download links** | ✅ | `admin.py:1179-1198` — `sales_order_pdf_download` route exists; shown in detail modal | Complete |
| **F) Notes global modal** | ✅ | `_layout.html:60-125` — `openNotesModal()` function, `/admin/notes/*` routes | Complete |
| **F) Notes cross-surface** | ✅ | Distribution modal (line 304), Sales Dashboard (line 120), Customers list all call `openNotesModal()` | Complete |
| **G) Professional aesthetics** | 🟡 | `design-system.css` exists; inline styles still scattered | Consolidate CSS |

---

## C) P0 Breakages (must-fix now)

### C1) Deployment Failure — Gunicorn Not Starting (PORT Missing)

**Symptom:** Health check fails with "connection refused" on port 8080, even though release script completes successfully.

**Evidence from logs:**
```
Jan 23 00:43:14  === SilqeQMS release done ===
Jan 23 00:42:44  ERROR failed health checks after 8 attempts with error Readiness probe failed: dial tcp 10.244.22.91:8080: connect: connection refused
```

**Root Cause:** The custom run command uses `$PORT` without a default fallback:
```bash
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload
```

If `PORT` environment variable is not set, this expands to `--bind 0.0.0.0:` which is invalid.

**Evidence:** The provided environment variables list does NOT include `PORT`.

**Minimal Fix (choose one):**

**Option A — Add PORT env var (quick fix):**
```
PORT=8080
```

**Option B — Fix run command (recommended):**
```bash
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60 --preload
```

**Option C — Remove custom run command:**
Let DigitalOcean use the Dockerfile CMD which already has the correct fallback:
```dockerfile
CMD ["sh", "-c", "gunicorn app.wsgi:app --preload --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60"]
```

**Verification:**
1. Deploy with fix applied
2. Check DO logs for `Listening at: http://0.0.0.0:8080`
3. Health checks should pass

---

### C1b) Previous Issue — Boolean Default Mismatch (NOW RESOLVED)

**Status:** ✅ FIXED

**Evidence:** Latest deployment logs show correct diagnostic:
```
Jan 23 00:43:13  [diag] sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
Jan 23 00:43:14  Migrations complete.
```

The migration now uses Postgres-safe `server_default=sa.text("false")` and completes successfully.

---

### C2) Customers Page 500 — LIKELY RESOLVED

**Symptom:** `/admin/customers` returns Internal Server Error.

**Historical Root Cause:** `AmbiguousForeignKeysError` on `CustomerRep.rep` relationship — two FKs to `users` table without explicit `foreign_keys`.

**Current Code State:** FIXED in `app/eqms/modules/customer_profiles/models.py:90`:
```python
rep = relationship("User", foreign_keys=[rep_id], lazy="selectin")
```

**Status:** Fix is in codebase but deployment is blocked. Will be verified after C1 is resolved.

**Verification:**
```bash
# After deployment:
curl -s -o /dev/null -w "%{http_code}" https://<app>/admin/customers
# Expected: 200
```

---

### C3) Notes System — WORKING

**Symptom (historical):** "Add Note" button does nothing.

**Current Status:** WORKING. The global notes modal is correctly implemented.

**Evidence:**
- `_layout.html:88-122` — `openNotesModal(entityType, entityId)` function
- `_layout.html:107-114` — POST to `/admin/notes/create` with `X-CSRF-Token` header
- `rep_traceability/admin.py:836-914` — `notes_modal` and `notes_create` endpoints with `@require_permission("customers.notes")`

**No duplicate inline note form exists** — grep for `toggleNoteForm|order-note|_note_form` returns no matches.

**Verification:**
1. Login as admin
2. Go to Sales Dashboard
3. Click "Notes" button on any order row
4. Add note text and submit
5. Note should appear in list immediately

---

### C4) PDF Import — PARTIALLY WORKING

**Symptom:** PDF import shows "No tables found, only text" for some PDFs.

**Current Pipeline:** `app/eqms/modules/rep_traceability/parsers/pdf.py:308-481`
1. Try `page.extract_tables()` (pdfplumber)
2. If no tables, try `page.extract_text()` → `_parse_text_page()`
3. Also try `_parse_label_page()` for shipping labels
4. Normalize Unicode dashes (`_normalize_text()` at line 273)

**Why It Can Fail:**
- Text extraction depends on PDF having selectable text
- SKU pattern matching (`_extract_items()` line 220) requires literal SKU strings in text
- Scanned/image PDFs will fail completely

**Current Behavior (GOOD):**
- Even on parse failure, PDFs are stored: `admin.py:1222-1227` stores as `pdf_type="unparsed"`
- Admin can manually associate stored PDFs with orders

**Minimal Improvement (optional):**
- Add admin UI message: "PDF stored but could not be parsed automatically. Please enter order details manually."

**Verification:**
1. Upload a text-based PDF → should parse
2. Upload an image PDF → should store but show parse errors
3. Check `/admin/sales-orders/<id>` → PDF should be downloadable

---

### C5) Lot Tracking — CORRECTLY IMPLEMENTED

**Symptom (historical):** Shows only 2026, wrong totals.

**Current Implementation:** `app/eqms/modules/rep_traceability/service.py:577-641`

**Correct Behavior Verified:**
1. Loads LotLog with inventory: `line 580` — returns `lot_corrections`, `lot_inventory`, `lot_years`
2. Filters to 2025+ lots: `line 617-630` — uses `lot_years` from LotLog or regex extraction
3. Aggregates ALL-TIME distributions: `line 585-614` — queries all entries without year filter
4. Computes Active Inventory: `line 636-640` — `total_produced - rec["units"]`

**No fix needed.** Implementation matches spec.

**Verification SQL:**
```sql
-- Pick a lot and verify all-time total:
SELECT lot_number, SUM(quantity) as total_distributed
FROM distribution_log_entries
WHERE lot_number = 'SLQ-05012025'
GROUP BY lot_number;

-- Compare to dashboard value
```

---

### C6) Distribution Details Modal — COMPLETE

**Symptom (historical):** Cramped, unreadable modal.

**Current Implementation:** `app/eqms/templates/admin/distribution_log/list.html:162-338`

**Sections Present:**
- ✅ Distribution Entry (ship date, order #, SKU, lot, quantity, source)
- ✅ Linked Sales Order (if exists)
- ✅ Customer (name, location)
- ✅ Customer Stats (first/last order, total orders/units, top SKUs, recent lots, assigned reps)
- ✅ Attachments (PDF download links)
- ✅ Notes (quick action button to open notes modal)
- ✅ Quick Actions (View Customer Profile, View Notes, Edit Entry)

**Styling:**
- Max-width: 700px
- Max-height: 80vh
- Scroll containment: `max-height:calc(80vh - 120px); overflow-y:auto`
- Backdrop: `::backdrop { background: rgba(0,0,0,0.5) }`

**No fix needed.**

---

## D) Data Integrity Audit

### D1) Customer Duplicates/Orphans

**Existing Protection:**
- `Customer.company_key` is unique (model + migration)
- Cleanup script: `scripts/cleanup_zero_order_customers.py`

**Verification SQL:**
```sql
-- Customers with 0 distributions AND 0 sales orders (orphans):
SELECT c.id, c.facility_name, c.company_key
FROM customers c
LEFT JOIN distribution_log_entries d ON d.customer_id = c.id
LEFT JOIN sales_orders o ON o.customer_id = c.id
GROUP BY c.id
HAVING COUNT(DISTINCT d.id) = 0 AND COUNT(DISTINCT o.id) = 0;

-- Duplicate company_keys (should return 0 rows):
SELECT company_key, COUNT(*) 
FROM customers 
GROUP BY company_key 
HAVING COUNT(*) > 1;
```

### D2) Lot Normalization

**Existing Implementation:**
- `shipstation_sync/parsers.py:36` — `normalize_lot()` uppercases and strips
- `shipstation_sync/parsers.py:172-245` — `load_lot_log_with_inventory()` applies corrections from "Correct Lot Name" column

**Verification SQL:**
```sql
-- Lots that look like SKUs (should be excluded from lot tracking):
SELECT lot_number, COUNT(*) 
FROM distribution_log_entries 
WHERE lot_number IN ('211810SPT', '211610SPT', '211410SPT')
GROUP BY lot_number;

-- Lots with unusual characters:
SELECT lot_number, COUNT(*) 
FROM distribution_log_entries 
WHERE lot_number LIKE '%–%' OR lot_number LIKE '%—%'
GROUP BY lot_number;
```

### D3) Active Inventory Correctness

**Formula:** Active Inventory = Total Units Produced (LotLog) − Total Units Distributed (all-time)

**Implementation:** `service.py:636-640`
```python
total_produced = lot_inventory.get(rec["lot"])
if total_produced is not None:
    active_inventory = int(total_produced) - int(rec["units"])
rec["active_inventory"] = active_inventory
```

**Verification:**
```sql
-- For a specific lot, verify distributed total matches dashboard:
SELECT lot_number, SUM(quantity) as distributed
FROM distribution_log_entries
WHERE lot_number = 'SLQ-05012025'
GROUP BY lot_number;
```

---

## E) PDF Parsing Pipeline Audit

### Current Pipeline

**Location:** `app/eqms/modules/rep_traceability/parsers/pdf.py`

**Flow:**
1. `parse_sales_orders_pdf(file_bytes)` — main entry point (line 308)
2. For each page:
   - Try `page.extract_tables()` (line 344)
   - If tables found: parse columns (order, date, customer, sku, qty, lot)
   - If no tables: `_parse_text_page()` (line 350) — regex extraction
   - Also try `_parse_label_page()` (line 355) — for shipping labels
3. Normalize Unicode dashes via `_normalize_text()` (line 273)
4. Group lines by order_number (line 454-468)

### Why It Fails on Some PDFs

1. **Image-based PDFs:** `pdfplumber` cannot extract text from images
2. **Non-standard layouts:** SKU regex patterns (line 222) may not match
3. **Shipping labels:** Rotated text or encoded text may not extract cleanly

### Current Robustness (GOOD)

- **Always stores PDFs:** Even on parse failure, `_store_pdf_attachment()` is called with `pdf_type="unparsed"` (admin.py:1222-1227)
- **Label detection:** `_parse_label_page()` attempts tracking number and ship-to extraction
- **Reversed text heuristic:** Line 287-291 tries reversing lines for rotated labels

### No Duplicate/Legacy Parsers

Only one PDF parser exists: `rep_traceability/parsers/pdf.py`. No other PDF parsing code in codebase.

### Recommendation

Document the limitation in UI:
- Add help text: "If PDF cannot be parsed automatically, it will be stored for manual reference."

---

## F) Notes System Audit

### Endpoints

| Route | Permission | Location |
|-------|------------|----------|
| `GET /admin/notes/modal/<entity_type>/<int:entity_id>` | `customers.notes` | `admin.py:836-870` |
| `POST /admin/notes/create` | `customers.notes` | `admin.py:873-914` |
| `GET /admin/notes/list/<entity_type>/<int:entity_id>` | `customers.notes` | `admin.py:917-958` |

### CSRF Handling

- Global CSRF is configured in `app/eqms/__init__.py`
- JavaScript in `_layout.html:107-114` sends `X-CSRF-Token` header with POST

### Cross-Surface Visibility

| Page | Implementation |
|------|----------------|
| Sales Dashboard | `index.html:120` — `onclick="openNotesModal('customer', {{ order.customer_id }})"` |
| Distribution Log Modal | `list.html:304` — `onclick="openNotesModal('customer', ${data.customer.id})"` |
| Customer Profile | Links to notes tab/section |

### No Issues Found

Notes system is correctly implemented. Previous failures were due to ORM mapper crash (now fixed).

---

## G) UI/UX Lean Polish Recommendations

### Completed (No Action Needed)

1. ✅ Modal sizing: 700px width, 80vh height
2. ✅ Scroll containment: Content area has max-height with overflow-y
3. ✅ Section headers: Uppercase, small font, muted color
4. ✅ Backdrop: Semi-transparent overlay with blur
5. ✅ Button hierarchy: Primary = solid, Secondary = outline

### Recommended Improvements (P2)

1. **Consolidate inline styles to CSS classes**
   - Many templates have inline styles that could be CSS classes in `design-system.css`
   - Example: `style="font-size:11px; text-transform:uppercase; color:var(--muted);"` → `.section-header`

2. **Add loading spinner to modals**
   - Current: Plain text "Loading..."
   - Improvement: SVG spinner or CSS animation

3. **Consistent table row hover**
   - Add hover state to all data tables for better scanability

---

## H) Legacy/Bloat Removal Plan (DECISIVE)

| File/Module | Action | Why | Verification |
|-------------|--------|-----|--------------|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/*.html` | QUARANTINE | Reference HTML files, not imported anywhere | Keep for behavioral reference, ensure no includes |
| `legacy/DO_NOT_USE__REFERENCE_ONLY/README.md` | KEEP | Documents purpose of legacy folder | N/A |
| `legacy/_archive.zip` | DELETE | Compressed archive of unknown content | Check contents first, then delete |

### No Active Legacy Code Found

- No Python files in `legacy/`
- No routes reference legacy templates
- No imports from legacy in any Python files

**Verification command:**
```bash
rg -l "DO_NOT_USE__REFERENCE_ONLY" app/
# Expected: no results
```

---

## I) Developer Fix Plan (Dependency Ordered)

### P0 — Deployment Blocker (DO IMMEDIATELY)

#### 1. Fix PORT Environment Variable

**Location:** DigitalOcean App Platform → Settings → Environment Variables

**Action (choose one):**

**Option A — Add PORT variable (simplest):**
```
PORT=8080
```
Add this to the environment variables list.

**Option B — Fix run command:**
Change the run command from:
```bash
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload
```
To:
```bash
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60 --preload
```

**Option C — Use Dockerfile CMD:**
Remove the custom Run Command entirely. Let DO use the Dockerfile's CMD which already has correct fallback.

**Acceptance Criteria:**
- Gunicorn starts and binds to port 8080
- Health checks pass
- App responds to requests

**Verification:**
```
# In DO logs, look for:
[INFO] Listening at: http://0.0.0.0:8080
```

---

#### 2. Generate Proper SECRET_KEY

**Location:** DigitalOcean App Platform → Settings → Environment Variables

**Current (BAD):**
```
SECRET_KEY=<generate-new-random-32-char-key>
```

**Action:** Generate a real secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Replace with (example):**
```
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

**Acceptance Criteria:**
- SECRET_KEY is 64 hex characters (32 bytes)
- No special characters or angle brackets

---

### P0 — Post-Deployment Verification (After Deploy Succeeds)

#### 3. Verify App Starts

**Action:** After deploying with PORT fix, check:
1. DO logs show "Listening at: http://0.0.0.0:8080"
2. Health checks pass
3. App URL is reachable

#### 4. Verify Customers Page Works

**Verification:**
1. Login as admin
2. Navigate to `/admin/customers`
3. Confirm page loads without error
4. Confirm customer list displays

#### 5. Verify Notes System Works

**Verification:**
1. Go to Sales Dashboard
2. Click "Notes" on any order
3. Add a note
4. Confirm note appears in list

---

### P1 — Documentation & UX Polish

#### 6. Add PDF Import Help Text

**Files:** `app/eqms/templates/admin/sales_orders/import.html`

**Change:** Add message explaining that unparseable PDFs will be stored but require manual entry.

**Acceptance Criteria:**
- User sees clear message about parser limitations
- User understands PDFs are saved even on parse failure

#### 7. Consolidate Inline Styles to CSS

**Files:** 
- `app/eqms/static/design-system.css`
- Various templates

**Change:** Extract repeated inline styles to named CSS classes.

**Acceptance Criteria:**
- Reduced inline style usage
- Consistent appearance maintained

---

### P2 — Optional Enhancements

#### 8. Add Loading Spinner to Modals

**Files:** `_layout.html`, `distribution_log/list.html`, `sales_dashboard/index.html`

**Change:** Replace "Loading..." text with CSS spinner.

#### 9. Delete Legacy Archive

**Files:** `legacy/_archive.zip`

**Action:** Review contents, then delete if not needed.

---

## Appendix A: Required Environment Variables (Production)

```bash
# === REQUIRED FOR APP TO START ===
PORT=8080
ENV=production
DATABASE_URL=postgresql://user:pass@host:port/dbname?sslmode=require
SECRET_KEY=<64-char-hex-string>  # Run: python -c "import secrets; print(secrets.token_hex(32))"

# === REQUIRED FOR ADMIN LOGIN ===
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<strong-password>

# === REQUIRED FOR FILE STORAGE ===
STORAGE_BACKEND=s3
S3_ENDPOINT=sfo3.digitaloceanspaces.com
S3_REGION=sfo3
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY_ID=<access-key>
S3_SECRET_ACCESS_KEY=<secret-key>

# === OPTIONAL: SHIPSTATION SYNC ===
SHIPSTATION_API_KEY=<api-key>
SHIPSTATION_API_SECRET=<api-secret>
SHIPSTATION_LOTLOG_PATH=app/eqms/data/LotLog.csv
SHIPSTATION_SINCE_DATE=2025-01-01
SHIPSTATION_MAX_ORDERS=1000
SHIPSTATION_MAX_PAGES=1000
```

**Note:** The user's current env is missing `PORT=8080` which causes gunicorn to fail binding.

---

## Appendix B: Key File Locations

| Component | Primary File |
|-----------|--------------|
| Customer models | `app/eqms/modules/customer_profiles/models.py` |
| Customer routes | `app/eqms/modules/customer_profiles/admin.py` |
| Distribution routes | `app/eqms/modules/rep_traceability/admin.py` |
| PDF parser | `app/eqms/modules/rep_traceability/parsers/pdf.py` |
| Dashboard service | `app/eqms/modules/rep_traceability/service.py` |
| LotLog loader | `app/eqms/modules/shipstation_sync/parsers.py` |
| Notes modal JS | `app/eqms/templates/_layout.html` |
| Distribution modal | `app/eqms/templates/admin/distribution_log/list.html` |
| Dashboard template | `app/eqms/templates/admin/sales_dashboard/index.html` |
| Migration (customer_reps) | `migrations/versions/e4f5a6b7c8d9_add_customer_reps_table.py` |
| Init/seed script | `scripts/init_db.py` |
| Release script | `scripts/release.py` |
| App factory | `app/eqms/__init__.py` |
| WSGI entry | `app/wsgi.py` |
| Config loader | `app/eqms/config.py` |
| Dockerfile | `Dockerfile` |
