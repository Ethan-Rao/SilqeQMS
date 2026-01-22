# 07 DEBUG AUDIT — System + Sales Parity (SilqQMS / SilqeQMS)

This report audits the current repo end-to-end with a **Sales parity focus**, using `docs/planning/08_SALES_SYSTEM_LEGACY_PARITY_AND_UX_OVERHAUL.md` as the baseline for what the sales/customer/distribution/ShipStation areas **should** do.

> Note on the `/mnt/data/...` baseline reference in the prompt: that path is not present in this workspace environment. The repo contains the same baseline spec at `docs/planning/08_SALES_SYSTEM_LEGACY_PARITY_AND_UX_OVERHAUL.md`, and this audit treats it as the authoritative baseline.

---

### 1) Snapshot summary

- **ShipStation 2025 “missing orders” is primarily a configuration + default behavior problem**: the sync still falls back to **last N days (default 30)** unless `SHIPSTATION_SINCE_DATE` is set → production will naturally show “only 2026” if sync is being run in 2026 (`app/eqms/modules/shipstation_sync/service.py::run_sync`).
- **ShipStation backfill can also silently stop early due to hard limits** (`SHIPSTATION_MAX_ORDERS` default 500; `SHIPSTATION_MAX_PAGES` default 50). If ShipStation returns most-recent-first, a wide backfill window + low limits yields “only recent orders” even with a since-date (`app/eqms/modules/shipstation_sync/service.py::run_sync`).
- **Manual Distribution Log entry allows “orphan” rows (no `customer_id`)** even though baseline spec expects customer linking to be required for manual entry → breaks cohesion and downstream dashboards/top customers (`app/eqms/templates/admin/distribution_log/edit.html`, `app/eqms/modules/rep_traceability/service.py::validate_distribution_payload`).
- **ShipStation sync can also write “orphan” distribution entries** if it cannot resolve a customer from `shipTo` (customer_id becomes empty string → stored NULL) even though baseline spec expects `customer_id` present for ShipStation entries (`app/eqms/modules/shipstation_sync/service.py::_get_customer_from_ship_to` + `run_sync`).
- **Customer Database “Year” filter is logically wrong for sales parity**: current code treats “Year=2025” as “has any order with year >= 2025”, so customers with 2026 orders will still show under “2025” (not legacy-parity and confusing) (`app/eqms/modules/customer_profiles/admin.py::customers_list`).
- **Sales Dashboard lacks baseline “Sales by Month” table** (a key legacy feature) and computes “lifetime order counts” by loading *all* distribution rows into Python → performance risk as data grows (`app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard` and `app/eqms/templates/admin/sales_dashboard/index.html`).
- **Customer Profile tabs exist but are not baseline-parity**: missing Distributions tab; Orders table is line-level, not grouped items-per-order; missing year/date-range filtering and export (`app/eqms/templates/admin/customers/detail.html`, `app/eqms/modules/customer_profiles/admin.py::customer_detail`).
- **ShipStation diagnostics endpoint likely exposes sensitive operational data** (internal notes, shipTo, shipment IDs) to any Admin with `shipstation.view` → should be disabled in production or further restricted (`app/eqms/modules/shipstation_sync/admin.py::shipstation_diag`, `app/eqms/templates/admin/shipstation/diag.html`).
- **CSRF protection is absent** across admin POST surfaces including deletes/uploads/sync run, which is high-risk even for admin-only deployments (no CSRF token in forms) (`app/eqms/templates/**`, route handlers across modules).
- **Legacy prototypes remain in the repo** and are large/unsafe/confusing (raw SQL, psycopg2, SMTP, requests, background-thread sync), creating a real risk of “wrong code path” usage during future work (`legacy/_archive/repqms_Proto1_reference.py.py`, `legacy/_archive/repqms_shipstation_sync.py.py`).

---

### 2) Spec compliance matrix (baseline vs current)

| Spec Requirement (quote/short paraphrase) | Current Status | Evidence (file/route) | Notes (what’s missing/broken) |
|---|---:|---|---|
| Sales Dashboard exists at `/admin/sales-dashboard` | ✅ | `GET /admin/sales-dashboard` → `app/eqms/modules/rep_traceability/admin.py::sales_dashboard` | Route exists and renders. |
| Sales Dashboard default `start_date` should be `2025-01-01` | ✅ | `app/eqms/modules/rep_traceability/admin.py::sales_dashboard` (`start_date_s ... or "2025-01-01"`) | Meets baseline default. |
| Sales Dashboard must include metric cards (units/orders/customers/first-time/repeat) | ✅ | `app/eqms/templates/admin/sales_dashboard/index.html` | Cards exist. |
| Sales Dashboard must include “Sales by Month” table | ❌ | `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard` + template | No month aggregation computed or rendered. |
| Sales Dashboard must include “Sales by SKU” table | ✅ | `app/eqms/templates/admin/sales_dashboard/index.html` | Present (SKU breakdown). |
| Sales Dashboard must include “Top Customers” with profile links | ✅ | `app/eqms/templates/admin/sales_dashboard/index.html` | Present, linked to `customer_profiles.customer_detail`. |
| Notes workflow from dashboard → customer profile | 🟡 | Dashboard has `+ Note` link to `...customer_detail...#notes` | Navigation is there; no inline note creation on dashboard; relies on profile Notes tab. |
| Customer Database at `/admin/customers` with pagination (50/page) | ✅ | `app/eqms/modules/customer_profiles/admin.py::customers_list` | Server-side pagination exists. |
| Customer Database filters: search + state + year (2025/2026) + type (first/repeat) | 🟡 | `app/eqms/templates/admin/customers/list.html` + `customers_list()` | UI has search/state/year/type; **rep filter missing**; **year logic is wrong** (see Section 5/6). |
| Customer Profile tabbed interface (Overview / Orders / Distributions / Notes) | 🟡 | `app/eqms/templates/admin/customers/detail.html` | Tabs exist but **no Distributions tab** (only Overview/Orders/Notes/Edit). |
| Customer Profile Orders tab should be per-order (items + total qty) with year/date filters | ❌ | `app/eqms/templates/admin/customers/detail.html` | Current Orders tab is **line-level per `DistributionLogEntry`**, no year/date filters, no grouping. |
| Customer Profile Distributions tab must show all entries (manual+CSV+ShipStation) | ❌ | (missing) | Not implemented; current Orders tab shows all entries without separation. |
| Distribution Log list view filters + export | ✅ | `app/eqms/modules/rep_traceability/admin.py::distribution_log_list` + `distribution_log_export` | Filters + export exist; pagination exists. |
| Manual Distribution entry must require customer selection (prevent orphans) | ❌ | `app/eqms/templates/admin/distribution_log/edit.html` says “Customer optional”; validation doesn’t require it | Orphan entries are currently allowed. |
| CSV Import should auto-create/link customers | ✅ | `app/eqms/modules/rep_traceability/admin.py::distribution_log_import_csv_post` | Uses `find_or_create_customer` and sets `customer_id`. |
| ShipStation sync should pull from `2025-01-01` onwards (not last 30 days) | 🟡 | `app/eqms/modules/shipstation_sync/service.py::run_sync` | Supports `SHIPSTATION_SINCE_DATE`, but **default behavior still uses last 30 days** if env var not set. |
| ShipStation sync must be idempotent | ✅ | Unique index `(source, external_key)` in model + migration | Implemented (`uq_distribution_log_source_external_key`). |
| ShipStation UI should show sync status + last order date | ✅ | `GET /admin/shipstation` + template | Shows since config and SS min/max ship_date. |

---

### 3) Critical runtime breakages (Blockers)

- **ShipStation 2025 backfill is effectively “broken” in typical production configs** unless `SHIPSTATION_SINCE_DATE` is explicitly set (or code default changed). This manifests as “system only shows 2026 orders” and blocks sales parity requirements for 2025 visibility.  
  - **Where**: `app/eqms/modules/shipstation_sync/service.py::run_sync` (`SHIPSTATION_SINCE_DATE` empty → uses `SHIPSTATION_DEFAULT_DAYS` default 30).  
  - **Severity**: **Blocker** (baseline explicitly requires 2025 sales visibility).  
  - **Fix direction**: see Section 4.

*(Other non-sales blockers exist in the repo-wide debug audit, e.g., manufacturing storage API mismatch, but this report stays scoped to baseline sales parity and system stability around those pages.)*

---

### 4) ShipStation sync: root cause analysis for missing 2025

#### 4.1 Current date filter behavior (env vars + defaults)

- **Where**: `app/eqms/modules/shipstation_sync/service.py::run_sync`
- **Behavior**:
  - If `SHIPSTATION_SINCE_DATE` is set (ISO date `YYYY-MM-DD`): use it as `start_dt` (UTC midnight).
  - Else: use `SHIPSTATION_DEFAULT_DAYS` (default `"30"`) and compute `start_dt = now_utc - days`.
- **Impact**:
  - In 2026, a last-30-days window naturally yields mostly/only 2026 orders. This matches the reported symptom: **“system only shows 2026 orders”**.
- **Secondary risk**: `shipstation_diag` hardcodes a last-30-days window too (`app/eqms/modules/shipstation_sync/admin.py::shipstation_diag`), which can mislead operators into thinking “ShipStation has no older data” when it’s just the diagnostic window.

#### 4.2 Pagination behavior / early-stop risks

- **Where**: `app/eqms/modules/shipstation_sync/service.py::run_sync`
- **Pagination**:
  - Orders paging: `for page in range(1, max_pages + 1)`; stop when ShipStation returns `[]`.
  - Shipments paging: pages 1..10; stop when empty or `len(chunk) < 100`.
- **Hard limits that can stop early**:
  - `SHIPSTATION_MAX_ORDERS` default **500**: stops after `orders_seen >= max_orders`.
  - `SHIPSTATION_MAX_PAGES` default **50**: maximum 50 pages of 100 orders = 5000 orders.
- **Why this matters for 2025**:
  - If ShipStation returns orders in **reverse chronological order** (typical), then a wide range (2025→now) + low limits can import only “recent” orders and never reach early 2025.
  - The run will still “complete successfully,” but older orders are missing.
- **Evidence surfaced in UI**:
  - The ShipStation admin UI shows `Since Date` as either the env var or `(last N days)` (`app/eqms/modules/shipstation_sync/admin.py::_get_sync_config`, template `app/eqms/templates/admin/shipstation/index.html`). This is a key operational clue for diagnosing 2025 missing.

#### 4.3 Idempotency constraints that might cause “silent skipping”

- **Where**:
  - Unique constraint: `Index("uq_distribution_log_source_external_key", "source", "external_key", unique=True)` in `app/eqms/modules/rep_traceability/models.py::DistributionLogEntry`
  - Migration ensures it exists: `migrations/versions/7f9a1c2d3e4b_add_shipstation_sync_tables_and_external_key.py`
  - External key construction: `app/eqms/modules/shipstation_sync/service.py::_build_external_key`
- **Behavior**:
  - Duplicates trigger `IntegrityError` and are recorded as `ShipStationSkippedOrder(reason="duplicate_external_key")`.
- **Assessment**:
  - This should not cause “missing 2025 entirely”; it affects duplicates, not entire years.
  - However, **bad lot extraction** can inflate collisions (e.g., lot = `UNKNOWN`), causing more duplicates than expected and reducing coverage.

#### 4.4 DB write failures or schema mismatches

- **Where**: `app/eqms/modules/shipstation_sync/service.py::run_sync`
- **Behavior**:
  - Uses nested SAVEPOINTs (`s.begin_nested()`) to avoid rolling back the whole sync on per-row failure.
  - Any exceptions are logged as `ShipStationSkippedOrder(reason="insert_failed")`.
- **Schema**:
  - `external_key` column + unique index are added by migration `7f9a1c2d3e4b...`.
  - If production DB missed that migration, inserts would likely fail or behave unexpectedly. (This is a deployment hygiene risk; see verification below.)

#### 4.5 Concrete verification SQL queries (what dates exist in DB)

**Postgres (production-like)**:

```sql
-- ShipStation coverage range + total count
SELECT
  COUNT(*) AS ss_entries,
  MIN(ship_date) AS ss_min_ship_date,
  MAX(ship_date) AS ss_max_ship_date
FROM distribution_log_entries
WHERE source = 'shipstation';

-- ShipStation entries by year
SELECT EXTRACT(YEAR FROM ship_date)::int AS year, COUNT(*) AS entries
FROM distribution_log_entries
WHERE source = 'shipstation'
GROUP BY 1
ORDER BY 1;

-- ShipStation entries by month since 2025-01-01
SELECT DATE_TRUNC('month', ship_date) AS month, COUNT(*) AS entries, SUM(quantity) AS units
FROM distribution_log_entries
WHERE source = 'shipstation' AND ship_date >= '2025-01-01'
GROUP BY 1
ORDER BY 1;

-- Sanity: do we have *any* 2025 ship dates at all (any source)?
SELECT source, COUNT(*) AS entries
FROM distribution_log_entries
WHERE ship_date >= '2025-01-01' AND ship_date < '2026-01-01'
GROUP BY source
ORDER BY entries DESC;
```

**SQLite (local dev)**:

```sql
SELECT COUNT(*) AS ss_entries, MIN(ship_date) AS ss_min_ship_date, MAX(ship_date) AS ss_max_ship_date
FROM distribution_log_entries
WHERE source = 'shipstation';

SELECT substr(ship_date, 1, 4) AS year, COUNT(*) AS entries
FROM distribution_log_entries
WHERE source = 'shipstation'
GROUP BY year
ORDER BY year;
```

**Local evidence (this workspace’s `qa_eval.db`)**:
- ShipStation entries are currently **0** and the only date present is `2026-01-19` (non-ShipStation).  
  - This indicates ShipStation data is not present locally unless credentials are configured and `/admin/shipstation/run` is executed.

#### 4.6 Recommended fix direction + verification steps

**Primary fix (P0): make the default behavior match the baseline spec (2025 backfill)**  
- **Fix direction**:
  - In `run_sync()`, if `SHIPSTATION_SINCE_DATE` is not set, default to `2025-01-01` instead of last-30-days (or set `SHIPSTATION_SINCE_DATE=2025-01-01` in production env as an operational hotfix).
  - Keep `SHIPSTATION_DEFAULT_DAYS` only as an *explicit opt-in* behavior (e.g., if `SHIPSTATION_SINCE_DATE` is empty and `SHIPSTATION_DEFAULT_DAYS` is set to something non-default).
- **Verification**:
  - In `/admin/shipstation`, confirm “Since Date” shows `2025-01-01` (not “last 30 days”).
  - Run sync, then execute the monthly SQL query above and verify rows exist for 2025 months.
  - Open `/admin/sales-dashboard?start_date=2025-01-01` and confirm 2025 data contributes to metrics.

**Secondary fix (P0/P1): detect and surface early-stop limits**  
- **Fix direction**:
  - When `hit_limit` is true, persist that status in `ShipStationSyncRun.message` (already includes “limit reached”), and make the UI show a strong warning.
  - Consider temporarily increasing `SHIPSTATION_MAX_ORDERS`/`SHIPSTATION_MAX_PAGES` for one-time backfill.
- **Verification**:
  - Confirm sync runs indicate whether limits were hit.
  - Confirm the monthly query continues to fill back beyond the previous max.

**Data cohesion fix (P0): enforce customer linking for ShipStation rows**  
- **Fix direction**:
  - If `_get_customer_from_ship_to()` returns None, treat it as `skipped` (reason `missing_customer`) rather than inserting a distribution row with NULL `customer_id`.
  - Alternatively, create a deterministic “Unknown Customer” record and link to it (less preferred; it pollutes customer DB).
- **Verification**:
  - Query: `SELECT COUNT(*) FROM distribution_log_entries WHERE source='shipstation' AND customer_id IS NULL;` should be 0 (or near 0, with explicit exceptions).

---

### 5) Sales pages functional defects

#### 5.1 Sales Dashboard (`/admin/sales-dashboard`)

- **Missing “Sales by Month” table (baseline requirement)**  
  - **Where**: `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard`, template `app/eqms/templates/admin/sales_dashboard/index.html`  
  - **Symptom**: dashboard lacks monthly breakdown; legacy parity not met.  
  - **Root cause**: no month aggregation computed.  
  - **Severity**: **High** (baseline feature).  
  - **Fix direction**: add a month aggregation (SQL group-by month) and render a simple table.
  - **Verify**: open dashboard with data spanning months; confirm month rows match DB.

- **Potential performance issue: lifetime classification loads full table into Python**  
  - **Where**: `compute_sales_dashboard()` loads all rows (`.all()`) into `lifetime_rows`.  
  - **Symptom**: dashboard slows as rows grow.  
  - **Severity**: Medium (becomes High with growth).  
  - **Fix direction**: compute lifetime order counts with SQL aggregates (group by `customer_id` and/or canonical key) instead of Python sets.  
  - **Verify**: benchmark dashboard on realistic DB size; ensure <2s typical.

#### 5.2 Customer Database (`/admin/customers`)

- **Year filter logic incorrect (includes “>= year”)**  
  - **Where**: `app/eqms/modules/customer_profiles/admin.py::customers_list` (year logic compares `.year >= year_int`)  
  - **Symptom**: selecting Year=2025 shows customers with 2026 orders; hard to isolate 2025-only activity.  
  - **Root cause**: year filter is implemented as a lower bound on first/last order year, not “orders in that year” or “last order in that year” (spec suggests last-order-year).  
  - **Severity**: **High** (sales analysis correctness).  
  - **Fix direction**: decide and implement one baseline-consistent behavior:
    - **Option A (legacy-ish)**: Year filter = `last_order.year == year`.
    - **Option B (more useful)**: Year filter = customer has any orders in that year (requires per-year dist query).
  - **Verify**: create a customer with orders in 2025 and 2026; ensure year=2025 filter behaves as intended.

- **Rep filter missing from UI**  
  - **Where**: route reads `rep_id`, template does not expose it (`app/eqms/templates/admin/customers/list.html`).  
  - **Severity**: Low/Medium (parity gap).  
  - **Fix direction**: either add a rep dropdown or remove dead param to reduce confusion.  
  - **Verify**: UI supports rep filter or route no longer advertises it.

#### 5.3 Customer Profile (`/admin/customers/<id>`)

- **Missing Distributions tab**  
  - **Where**: `app/eqms/templates/admin/customers/detail.html` (tabs: Overview/Orders/Notes/Edit)  
  - **Symptom**: baseline expects separate Orders vs Distributions; current “Orders” shows all entries and there’s no dedicated Distributions view.  
  - **Severity**: Medium (parity gap).  
  - **Fix direction**: add a Distributions tab; if Orders is meant to show only ShipStation entries, filter by source.  
  - **Verify**: Orders tab vs Distributions tab show expected subsets.

- **Orders are not grouped per order; missing year/date filters and export**  
  - **Where**: `customer_detail()` passes `orders=all_distributions` and template renders row-per-entry.  
  - **Severity**: Medium/High depending on operator needs.  
  - **Fix direction**: group by order number + ship date; render item summary; add year/date filter query params.  
  - **Verify**: a multi-item order renders as one row with items; filters work.

#### 5.4 Distribution Log (`/admin/distribution-log`)

- **Manual entry does not require customer selection** (violates baseline “orphan prevention”)  
  - **Where**:
    - UI: `app/eqms/templates/admin/distribution_log/edit.html` (“Customer (optional, preferred)”)
    - Validation: `app/eqms/modules/rep_traceability/service.py::validate_distribution_payload` does not require `customer_id`.  
  - **Symptom**: manual rows can be created with only free-text facility; dashboards/top customers won’t link.  
  - **Severity**: **High** (data cohesion).  
  - **Fix direction**: require `customer_id` for manual create/edit (at least for new manual rows); if not selected, block with flash.  
  - **Verify**: manual create without customer fails; create with customer succeeds and canonicalizes facility/address.

- **“Facility Name” is still required even when customer selected**  
  - **Where**: template marks facility required; route overwrites on submit if customer selected.  
  - **Severity**: Low (UX confusion).  
  - **Fix direction**: make facility name read-only/auto-filled when customer selected, or hide it to avoid mismatch.  
  - **Verify**: selecting customer prevents inconsistent edits.

#### 5.5 Notes workflow

- **Dashboard provides link-to-notes, but no guidance for creating notes “from dashboard”**  
  - **Where**: Sales Dashboard template uses `#notes` anchor; Profile notes form exists.  
  - **Severity**: Low (workflow mostly works).  
  - **Fix direction**: add explanatory microcopy on dashboard (“Add note opens customer profile Notes tab”).  
  - **Verify**: user can consistently add a note via dashboard link and see it on profile.

---

### 6) Data integrity & cohesion risks

- **Orphan distributions (`customer_id` NULL) are allowed and likely**  
  - **Where**:
    - Manual flow allows no customer: `app/eqms/templates/admin/distribution_log/edit.html`
    - ShipStation flow may fail to resolve customer: `app/eqms/modules/shipstation_sync/service.py::_get_customer_from_ship_to`  
  - **Symptom**: Top Customers table and Customer Profile rollups undercount/omit; “facility_name” string becomes a shadow customer system.  
  - **Severity**: **High**.  
  - **Fix direction**:
    - Require `customer_id` for manual.
    - For ShipStation, skip rows where customer resolution fails; log as skipped.
  - **Verify**: `SELECT COUNT(*) ... WHERE customer_id IS NULL` trends to zero for new data.

- **Duplicate customers vs dedupe**  
  - **Where**: customer dedupe relies on `company_key` unique + `canonical_customer_key()` via `find_or_create_customer()` (`app/eqms/modules/customer_profiles/service.py`).  
  - **Risk**: If facility_name has inconsistent punctuation/aliasing beyond what canonicalization handles, duplicates can still occur (though reduced).  
  - **Severity**: Medium.  
  - **Fix direction**: keep canonicalization centralized; avoid re-introducing alternate dedupe in ShipStation/CSV.

- **Customer Database “Year” filter currently misrepresents which customers belong to a year**  
  - **Where**: `customers_list()` (logic uses `>=`).  
  - **Severity**: High (reporting correctness).  
  - **Fix direction**: implement exact-year semantics using DB query.

- **Indexes/constraints**:
  - Distribution Log has helpful indexes including `customer_id`, `ship_date`, and `(source, external_key)` (`app/eqms/modules/rep_traceability/models.py`).  
  - Main gap is **policy enforcement** (customer linking), not missing indexes.

---

### 7) Legacy/outdated/duplicate code inventory

| Location | Recommendation | Why it’s risky if left in place |
|---|---|---|
| `legacy/_archive/repqms_Proto1_reference.py.py` | **QUARANTINE** (or DELETE if policy allows) | Huge monolith with psycopg2, SMTP, background-thread sync; not aligned with current architecture; easy to accidentally copy/paste “wrong” patterns. |
| `legacy/_archive/repqms_shipstation_sync.py.py` | **QUARANTINE** (or DELETE) | Competing ShipStation implementation with raw SQL DDL and different tables; creates confusion during ShipStation work. |
| `legacy/_archive/*.html` (legacy admin pages) | **QUARANTINE** | Useful as visual reference only; should not be mistaken for active templates. |
| Any old sync scripts in `legacy/_archive/` | **DELETE/QUARANTINE** | Avoid “two ShipStation syncs” problem; Planning/Dev should treat `app/eqms/modules/shipstation_sync/*` as the only live sync path. |

Minimal quarantine approach:
- Move `legacy/_archive/` → `legacy/DO_NOT_USE__REFERENCE_ONLY/`
- Add a short `legacy/DO_NOT_USE__REFERENCE_ONLY/README.md` stating “not executed, do not import, reference only”.

---

### 8) Security & permission audit notes

- **CSRF missing across admin POST routes** (sync run, deletes, uploads).  
  - **Where**: templates lack CSRF token fields; Flask app doesn’t enable CSRF globally.  
  - **Severity**: **High**.  
  - **Fix direction**: add a minimal CSRF strategy (Flask-WTF or custom token). If dependencies are constrained, implement a lightweight session token + hidden input + validation decorator for POST.  
  - **Verify**: POST without token fails; legitimate form submits succeed.

- **ShipStation diagnostics endpoint may expose sensitive data**  
  - **Where**: `GET /admin/shipstation/diag` returns internal notes, order IDs, shipments, etc. (`app/eqms/modules/shipstation_sync/admin.py::shipstation_diag`).  
  - **Severity**: Medium/High depending on data sensitivity.  
  - **Fix direction**: disable in production (behind env flag) or require a stronger permission (e.g., `admin.view` + explicit `SHIPSTATION_DIAG_ENABLED=1`).  
  - **Verify**: endpoint returns 404 or access denied in production mode.

- **RBAC coverage for sales pages exists but must be kept consistent**  
  - **Where**: `@require_permission(...)` on routes; perms seeded in `scripts/init_db.py`.  
  - **Note**: Keep permission keys stable; avoid adding new keys unless needed for diag lockdown.

---

### 9) Performance & reliability observations

- **Sales Dashboard does two potentially heavy `.all()` reads**:
  - `lifetime_rows = s.query(...).all()` (full-table)
  - `window_entries = q...all()` (windowed, still potentially large)  
  - **Where**: `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard`
  - **Severity**: Medium now; grows with data volume.

- **Customer Database builds full `customer_stats` by querying all customer_id groups**:
  - **Where**: `app/eqms/modules/customer_profiles/admin.py::customers_list` (`dist_query.all()` then Python dict).  
  - **Severity**: Medium; can be optimized with subquery join + limit to current page customers.

- **ShipStation sync runs in request thread**:
  - **Where**: `/admin/shipstation/run` calls `run_sync()` directly.  
  - **Severity**: Medium; could cause timeouts or lock contention.  
  - **Fix direction**: even without new infra, add guardrails: “max runtime” messaging, clear limit warnings, and do not default to tiny last-30-days window that hides backfill needs.

---

### 10) Prioritized remediation backlog

| ID | Issue | Severity | Effort | Dependencies | Recommended fix direction | Verification steps |
|---:|---|---|---|---|---|---|
| 1 | ShipStation sync default still effectively last 30 days → missing 2025 | **Blocker** | S | Production env access | Default to `2025-01-01` unless explicitly configured otherwise; set `SHIPSTATION_SINCE_DATE=2025-01-01` in prod | Run sync; SQL month counts show 2025 rows; dashboard shows 2025 stats |
| 2 | ShipStation backfill can stop early (max_orders/max_pages) without strong warning | High | S/M | None | Make `hit_limit` prominent in UI; raise limits for backfill; optionally add “continue backfill” guidance | Sync run shows warning; increasing limits increases month coverage |
| 3 | Manual Distribution Log allows orphan rows (no customer_id) | High | S | None | Require `customer_id` for manual create/edit; update template text + server validation | Attempt manual create w/o customer fails; with customer succeeds and links |
| 4 | ShipStation can write orphan rows if customer resolution fails | High | S | None | Skip instead of inserting when `_get_customer_from_ship_to()` returns None; log skip reason | `COUNT(*) source='shipstation' AND customer_id IS NULL` stops increasing |
| 5 | Customer Database Year filter incorrect (uses `>=`) | High | S/M | Decide semantics | Implement year semantics (last-order-year or any-order-in-year) via DB query; update tests | Customer with 2026 order doesn’t appear in 2025 view (if last-year semantics) |
| 6 | Sales Dashboard missing “Sales by Month” table | High | S | None | Add month group-by query and render table | Table appears; values match DB aggregates |
| 7 | Customer Profile missing Distributions tab + lacks year/date filters | Medium | M | Issue 3/4 helps | Add Distributions tab and year/date filter parameters; clarify Orders vs Distributions | Tabs show expected subsets; filters narrow results |
| 8 | Customer Profile Orders are line-level, not grouped per order | Medium | M | None | Group entries by `order_number` (+ ship_date); render items summary | Multi-line orders render as single order rows with item breakdown |
| 9 | ShipStation diagnostics endpoint exposure | Medium/High | S | Ops decision | Disable in prod by default; require explicit enable flag | Endpoint unavailable unless enabled |
| 10 | CSRF missing across admin | High | M/L | Approach decision | Add CSRF tokens and validate on POST | CSRF-negative tests fail; normal POST works |

---

### 11) Quick patch set (fast wins)

These are small, safe edits intended to stabilize sales parity work quickly.

1. **ShipStation: default to `2025-01-01`** when `SHIPSTATION_SINCE_DATE` is unset (align with baseline)  
   - `app/eqms/modules/shipstation_sync/service.py::run_sync`
2. **ShipStation: make “limit reached” highly visible in UI** (banner on `/admin/shipstation`)  
   - `app/eqms/templates/admin/shipstation/index.html`
3. **ShipStation: skip (don’t insert) when customer cannot be resolved** and record a clear skip reason  
   - `app/eqms/modules/shipstation_sync/service.py`
4. **Distribution Log: require customer for manual create** (template + server-side validation)  
   - `app/eqms/templates/admin/distribution_log/edit.html`, `app/eqms/modules/rep_traceability/admin.py::distribution_log_new_post`, `.../service.py::validate_distribution_payload`
5. **Customers: fix Year filter semantics** (stop using `>=`)  
   - `app/eqms/modules/customer_profiles/admin.py::customers_list`
6. **Sales Dashboard: add Sales-by-Month aggregation + table**  
   - `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard`, `app/eqms/templates/admin/sales_dashboard/index.html`
7. **Customer Profile: add Distributions tab stub** (even if initially identical to current Orders) to match baseline navigation  
   - `app/eqms/templates/admin/customers/detail.html`
8. **ShipStation diagnostics: disable by default** (env gate)  
   - `app/eqms/modules/shipstation_sync/admin.py::shipstation_diag`
9. **Quarantine legacy prototypes** (move under DO_NOT_USE folder + README)  
   - `legacy/_archive/*`
10. **Add minimal smoke queries to ShipStation UI** (e.g., “SS entries in 2025”) to immediately validate parity after a run  
   - `app/eqms/modules/shipstation_sync/admin.py::_get_distribution_diagnostics` and template

