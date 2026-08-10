# 08 DEBUG AUDIT — Sales System (Parity/Dedupe/2025) + Legacy Cleanup (Silq eQMS / Rep‑QMS)

Baseline spec used as source-of-truth: `docs/plans/SALES_SYSTEM_PARITY_DEDUPE_2025.md`.

Additional inputs inspected:
- Legacy reference archive: `legacy/_archive.zip` and `legacy/DO_NOT_USE__REFERENCE_ONLY/*` (reference only; do not port)
- 2025 import source PDF: `2025 Sales Orders.pdf`
- ShipStation sync module + admin UI: `app/eqms/modules/shipstation_sync/*`, templates under `app/eqms/templates/admin/shipstation/*`
- Sales/Customers/Distributions/Notes: `app/eqms/modules/customer_profiles/*`, `app/eqms/modules/rep_traceability/*`, templates under `app/eqms/templates/admin/*`

---

## 1) Snapshot summary

- **Blocker: sales system schema is not safely deployable without migrations** — core sales features now depend on `sales_orders` + `sales_order_lines`, but local evaluation DB (`qa_eval.db`) does **not** contain those tables → routes like `GET /admin/distribution-log/new`, `POST /admin/distribution-log/import-pdf`, ShipStation sync, and `/admin/sales-orders/*` will crash with “no such table” if migrations are not applied (`migrations/versions/b1c2d3e4f5g6_add_sales_orders_tables.py`).
- **Blocker: PDF import will hard-fail if `pdfplumber` isn’t installed at runtime** — parser returns `pdfplumber not installed...` and import routes surface an error; in this environment, `pdfplumber` is **not installed** even though it is listed in `requirements.txt` (`app/eqms/modules/rep_traceability/parsers/pdf.py`, `requirements.txt`).
- **ShipStation 2025 “missing” is now primarily caused by conservative hard limits**: sync defaults to `since=2025-01-01` (good), but default `SHIPSTATION_MAX_PAGES=10` / `SHIPSTATION_MAX_ORDERS=100` makes backfill extremely likely to stop early → older 2025 orders remain invisible (`app/eqms/modules/shipstation_sync/service.py::run_sync`).
- **Sales Orders “source-of-truth” is partially implemented**: models/migration exist and ShipStation creates `sales_orders` + `sales_order_lines` and links distributions; **CSV import and manual entry still create distributions without creating/linking an order by default** (spec requires all distributions link to orders) (`rep_traceability` admin/service).
- **Duplicate/competing PDF import paths exist**: `POST /admin/distribution-log/import-pdf` creates sales orders + lines + distributions, but `POST /admin/sales-orders/import-pdf` creates only sales orders + lines (no distributions). This is a parity + maintenance trap; only one should remain (`app/eqms/modules/rep_traceability/admin.py`).
- **UI correctness issue: Distribution Log import page still claims PDF import is “P1 placeholder”** while PDF import is implemented and writes data → misleading ops UX (`app/eqms/templates/admin/distribution_log/import.html` vs `rep_traceability.admin::distribution_log_import_pdf_post`).
- **Navigation gap: top nav omits Sales Orders** — Sales Orders exists in Admin cards but is missing from `_layout` header nav (`app/eqms/templates/_layout.html`, `app/eqms/templates/admin/index.html`).
- **Sales Orders templates use Bootstrap-only classes** (`btn`, `badge`, `table`, grid classes) but the app ships a custom `design-system.css` (no Bootstrap) → pages may render unstyled/“broken looking”, harming usability even if routes work (`app/eqms/templates/admin/sales_orders/*.html`).
- **Dropdown detail menus are only partially implemented**: Sales Dashboard has a `<details>` breakdown for Top Customers, but Customer Database + Distribution Log list do not have parity “expand rows” detail menus yet (baseline requirement) (`app/eqms/templates/admin/sales_dashboard/index.html`, `app/eqms/templates/admin/customers/list.html`, `app/eqms/templates/admin/distribution_log/list.html`).
- **Customer de-dupe logic is stronger than earlier state**: canonicalization now strips common suffixes and `find_or_create_customer()` supports Tier‑2 matching (address/email domain) — but there is still **no merge workflow/UI**, so existing duplicates (different `company_key`s) remain a manual clean-up problem (`app/eqms/modules/customer_profiles/utils.py`, `.../service.py`).

---

## 2) Spec compliance matrix (baseline vs current)

| Spec Requirement | Current Status | Evidence (file/route/model) | Notes (what’s missing/broken) |
|---|---:|---|---|
| Sales Dashboard parity: metric cards + tables (by month, by SKU, top customers) | 🟡 | `GET /admin/sales-dashboard` → `rep_traceability.admin::sales_dashboard`; `compute_sales_dashboard()`; template `admin/sales_dashboard/index.html` | By-month table exists; Top Customers exists. Still lacks full “dropdown details” parity on orders/customers and may have performance issues (Python `.all()` over lifetime rows). |
| Sales Dashboard: dropdown detail menus for customer/order rows (SKUs/lots/shipments) | 🟡 | Template `admin/sales_dashboard/index.html` | Only Top Customers has `<details>` showing SKU breakdown + recent lots; no shipments/order-level details. |
| Customer DB parity: searchable + year/type filters + expandable row details | ❌ | `GET /admin/customers` (`customer_profiles.admin::customers_list` + template `admin/customers/list.html`) | Filters exist; **expandable row details not implemented**; year semantics may not match spec (verify in `customers_list()`). |
| Customer de-duplication: prevent duplicates going forward (enhanced normalization + tiered matching) | 🟡 | `customer_profiles.utils::canonical_customer_key`, `customer_profiles.service::find_or_create_customer` | Implemented tiers exist; still no merge workflow for existing duplicates. |
| Sales Orders are source-of-truth: `sales_orders` + `sales_order_lines` tables exist via migration | 🟡 | Models: `rep_traceability.models::SalesOrder`, `SalesOrderLine`; migration: `b1c2d3e4f5g6_add_sales_orders_tables.py` | Code exists, but DB must be migrated everywhere; local `qa_eval.db` currently lacks these tables. |
| Distribution entries link to orders via `distribution_log_entries.sales_order_id` | 🟡 | Model: `DistributionLogEntry.sales_order_id`; migration adds FK/index | ShipStation + PDF import populate it; manual/CSV do not by default. |
| Manual distributions enforce customer selection | ✅ | `rep_traceability.admin::distribution_log_new_post`; template `admin/distribution_log/edit.html` (`customer_id` required) | Meets baseline. Still allows sales_order_id blank. |
| ShipStation sync completeness since 2025‑01‑01 | 🟡 | `shipstation_sync.service::run_sync` | Since-date default is correct, but default limits are too low for a real backfill. |
| ShipStation sync writes SalesOrders + lines, and links distributions to the SalesOrder | ✅ | `shipstation_sync.service::run_sync` creates order via `_find_or_create_sales_order` + `_create_sales_order_line`, sets `payload["sales_order_id"]` | Depends on DB migration being applied. |
| 2025 Sales Orders PDF ingestion exists and imports | 🟡 | Parser: `rep_traceability/parsers/pdf.py`; routes: `POST /admin/distribution-log/import-pdf`, `POST /admin/sales-orders/import-pdf` | Implemented, but **runtime dependency `pdfplumber` must be installed**, and the two routes are inconsistent (one creates distributions, one doesn’t). |
| Dropdown detail menus on Distribution Log rows (order context, mismatch flags) | ❌ | `admin/distribution_log/list.html` | Not implemented (no expandable row details; no mismatch flags). |
| Dropdown/accordion menus on Customer DB rows (order history, SKUs/lots, quick actions) | ❌ | `admin/customers/list.html` | Not implemented. |
| Sales Orders UI: list + detail pages | 🟡 | `rep_traceability.admin::sales_orders_list`, `sales_order_detail`; templates `admin/sales_orders/list.html`, `detail.html` | Functional but likely unstyled (Bootstrap classes without Bootstrap CSS). |

---

## 3) Critical runtime breakages (Blockers)

### B1) DB not migrated → missing `sales_orders` / `sales_order_lines` tables

- **Where**:
  - Migration: `migrations/versions/b1c2d3e4f5g6_add_sales_orders_tables.py`
  - Models referenced by runtime routes:
    - `rep_traceability.admin::distribution_log_new_get` queries `SalesOrder`
    - `rep_traceability.admin::distribution_log_edit_get` queries `SalesOrder`
    - `rep_traceability.admin::distribution_log_import_pdf_post` creates `SalesOrder`/`SalesOrderLine`
    - `rep_traceability.admin::sales_orders_list` queries `SalesOrder`
    - `shipstation_sync.service::run_sync` creates `SalesOrder`/`SalesOrderLine`
- **Symptom**:
  - If the DB has not applied `b1c2d3e4f5g6`, these routes will throw SQL errors like:
    - SQLite: `no such table: sales_orders`
    - Postgres: `relation "sales_orders" does not exist`
- **Concrete evidence (local)**:
  - In this workspace, `qa_eval.db` currently reports `HAS_sales_orders False` and `HAS_sales_order_lines False`.
- **Severity**: **Blocker**
- **Fix direction**:
  - Ensure production and any evaluation DBs run `alembic upgrade head` (or explicit upgrade to `b1c2d3e4f5g6`) before enabling these pages.
  - Keep the existing schema health guardrail aligned with the new tables (if guardrail only checks columns, it won’t catch missing tables).
- **How to verify**:
  - Run:
    - `alembic heads` (should show `b1c2d3e4f5g6 (head)`)
    - `alembic current`
  - Verify tables exist:
    - Postgres: `\dt sales_orders` and `\dt sales_order_lines`
    - SQLite: `SELECT name FROM sqlite_master WHERE type='table' AND name IN ('sales_orders','sales_order_lines');`

### B2) PDF import hard-fails if `pdfplumber` is missing at runtime

- **Where**: `app/eqms/modules/rep_traceability/parsers/pdf.py::parse_sales_orders_pdf`
- **Symptom**:
  - Parser returns `ParseError("pdfplumber not installed...")` and import routes show flash error; no import occurs.
- **Concrete evidence (local)**:
  - In this workspace runtime environment, `pdfplumber_installed False` and `parse_sales_orders_pdf(2025 Sales Orders.pdf)` returns 0 lines + 1 error.
- **Severity**: **Blocker** (spec requires 2025 PDF ingestion)
- **Fix direction**:
  - Ensure deployment actually installs `requirements.txt` and includes `pdfplumber` in the runtime image.
  - Add a startup diagnostics check (or admin page health indicator) that confirms PDF ingestion dependencies are installed.
- **How to verify**:
  - `python -c "import pdfplumber; print(pdfplumber.__version__)"`
  - Upload `2025 Sales Orders.pdf` via the import route; verify non-zero parsed lines and created rows.

---

## 4) ShipStation sync deep dive (why 2025 is missing)

### 4.1 Where `since_date` is set (env vs default)

- **Where**: `app/eqms/modules/shipstation_sync/service.py::run_sync`
- **Current behavior**:
  - If `SHIPSTATION_SINCE_DATE` is present and parseable: `start_dt = that date @ UTC midnight`.
  - Else: **defaults to `2025-01-01`** (baseline requirement).
- **Implication**:
  - The “missing 2025” symptom is no longer primarily caused by `SHIPSTATION_DEFAULT_DAYS`. It is now dominated by limits/pagination (next sections).

### 4.2 Ordering + pagination behavior (stopping early / max_pages/max_orders)

- **Where**: `shipstation_sync.service::run_sync`
- **Hard limits**:
  - `SHIPSTATION_MAX_PAGES` default **10**
  - `SHIPSTATION_MAX_ORDERS` default **100**
- **Mechanism**:
  - Orders are fetched via `/orders` paged 100/page; loop stops at `max_pages`.
  - Processing stops once `orders_seen >= max_orders` (sets `hit_limit=True`).
- **Why 2025 can remain missing**:
  - If ShipStation returns orders **most-recent-first**, then processing only 100 orders will likely cover only recent 2026 orders and never reach earlier 2025 orders even though the date window starts at 2025‑01‑01.
- **Amplifying factor**:
  - Sync also pre-fetches shipments by date range, but uses the same `max_pages` limit to page `/shipments` by shipDate. With `max_pages=10`, only the first ~1000 shipments (likely recent) are available in `shipments_by_order`. Orders outside that range may be treated as `no_shipments` and skipped.

### 4.3 Idempotency logic (duplicates prevented incorrectly? inserts skipped?)

- **Sales orders**:
  - Unique key: `(source, external_key)` on `sales_orders` (`uq_sales_orders_source_external_key`)
  - External key used for ShipStation orders: `external_key = f"ss:{order_id}"` (idempotent)
  - **Where**: `_find_or_create_sales_order()` and `SalesOrder` model
- **Distributions**:
  - Unique key: `(source, external_key)` on `distribution_log_entries` (`uq_distribution_log_source_external_key`)
  - External key used: `"{shipmentId}:{sku}:{lot}"` (idempotent)
  - **Where**: `_build_external_key()` and `DistributionLogEntry` model
- **Assessment**:
  - Idempotency is conceptually correct; “missing 2025” is unlikely caused by duplicate skipping unless the lot is frequently `UNKNOWN` (collision risk). The dominant issue is limits + paging.

### 4.4 What tables are written today (distributions only? orders table missing?)

- **Current implementation writes BOTH**:
  - `sales_orders` + `sales_order_lines` (source of truth)
  - `distribution_log_entries` linked to `sales_order_id`
- **Where**: `shipstation_sync.service::run_sync`
- **Key dependency**:
  - Requires `b1c2d3e4f5g6` migration to be applied, otherwise sync will crash.

### 4.5 Verification SQL (months present; confirm 2025 absence/presence)

**ShipStation distribution coverage by month (Postgres):**

```sql
SELECT DATE_TRUNC('month', ship_date) AS month, COUNT(*) AS entries
FROM distribution_log_entries
WHERE source = 'shipstation'
GROUP BY 1
ORDER BY 1;
```

**ShipStation sales order coverage by order_date (Postgres):**

```sql
SELECT DATE_TRUNC('month', order_date) AS month, COUNT(*) AS orders
FROM sales_orders
WHERE source = 'shipstation'
GROUP BY 1
ORDER BY 1;
```

**Was the sync limit hit?**

```sql
SELECT ran_at, orders_seen, shipments_seen, synced_count, skipped_count, message
FROM shipstation_sync_runs
ORDER BY ran_at DESC
LIMIT 10;
```

### 4.6 Precise fix direction + how to confirm it’s fixed

- **Fix direction (P0)**:
  - Increase backfill capacity safely:
    - Set production env for a one-time backfill: `SHIPSTATION_MAX_PAGES` and `SHIPSTATION_MAX_ORDERS` high enough to cover 2025→now.
    - Ensure the ShipStation admin UI surfaces `hit_limit` as a prominent warning (message already includes a “LIMIT REACHED” warning; make it visually unavoidable).
  - Consider splitting limits:
    - Separate shipment prefetch paging limit from order paging limit (currently both use `max_pages`).
  - Keep default `since=2025-01-01` (good), but avoid defaults so low they guarantee incomplete history.
- **How to verify**:
  - Re-run sync with higher limits.
  - Confirm queries in 4.5 show **2025 months** present for both `sales_orders` and `distribution_log_entries`.
  - Open `/admin/sales-dashboard?start_date=2025-01-01` and confirm metrics reflect 2025 volume.

---

## 5) Customer duplicates: root cause + evidence

### 5.1 Expected duplicate patterns (per baseline spec)

The baseline spec anticipates duplicates across variants like:
- Name suffixes: “Hospital A” vs “Hospital A, Inc.”
- Punctuation/spaces: “St. Mary’s” vs “St Marys”
- Address variants: same org, different address formatting
- Email domain linkage: same org, different facility name but shared domain

### 5.2 Where dedupe is supposed to happen (and where it can be bypassed)

- **Tiered dedupe is implemented in `find_or_create_customer()`**:
  - Tier 1 exact: `company_key` from `canonical_customer_key()`
  - Tier 2 strong: address match (city/state/zip) OR business email domain match
  - Tier 3 weak: prefix match candidates (returns list) but no review queue table/UI
- **Where**:
  - `app/eqms/modules/customer_profiles/utils.py` (`normalize_facility_name()`, `canonical_customer_key()`, `extract_email_domain()`)
  - `app/eqms/modules/customer_profiles/service.py::find_or_create_customer`
- **Bypass vectors that still exist**:
  - Creating customers directly via raw SQL or direct `Customer()` construction would bypass tiers, but current admin routes use `create_customer()` which calls `find_or_create_customer()` (good). Legacy/proto code still contains direct SQL patterns (should remain quarantined).

### 5.3 Whether uniqueness constraints exist and if they’re effective

- **Constraint**: `customers.company_key` is `unique=True` (`customer_profiles.models::Customer`)
- **Effect**:
  - Exact duplicates by `company_key` should be impossible in a correctly migrated DB.
  - “Duplicates” in practice are likely **near-duplicates** that normalize to different keys (e.g., suffix stripping not sufficient), or pre-existing duplicates in older DBs without the unique constraint.

### 5.4 Verification queries (run/should run)

**A) Exact duplicates by `company_key` (should return 0 rows if constraint is active):**

```sql
SELECT company_key, COUNT(*) AS n
FROM customers
GROUP BY company_key
HAVING COUNT(*) > 1;
```

**B) Near-duplicates by prefix similarity (cheap heuristic):**

```sql
SELECT LEFT(company_key, 8) AS prefix, COUNT(*) AS n
FROM customers
GROUP BY LEFT(company_key, 8)
HAVING COUNT(*) > 1
ORDER BY n DESC;
```

**C) Potential duplicates by shared location (city/state/zip):**

```sql
SELECT UPPER(COALESCE(city,'')) AS city, UPPER(COALESCE(state,'')) AS state, COALESCE(zip,'') AS zip, COUNT(*) AS n
FROM customers
GROUP BY 1,2,3
HAVING COUNT(*) > 1
ORDER BY n DESC;
```

**D) Potential duplicates by business email domain (excluding personal domains):**

```sql
-- Postgres example: split_part(email,'@',2)
SELECT LOWER(SPLIT_PART(contact_email, '@', 2)) AS domain, COUNT(*) AS n
FROM customers
WHERE contact_email LIKE '%@%'
  AND LOWER(SPLIT_PART(contact_email, '@', 2)) NOT IN ('gmail.com','yahoo.com','hotmail.com','outlook.com','aol.com')
GROUP BY 1
HAVING COUNT(*) > 1
ORDER BY n DESC;
```

### 5.5 Fix direction (lean)

- **Short-term**:
  - Add a “merge customers” admin-only operation that re-points:
    - `sales_orders.customer_id`
    - `distribution_log_entries.customer_id`
    - `customer_notes.customer_id`
    - then deletes the losing customer (or marks inactive).
  - This matches the baseline “dedupe + merge” requirement and prevents long-lived duplicates.
- **Verification**:
  - Run the queries above before/after merges; confirm near-duplicate counts drop and FK references are consolidated.

---

## 6) Sales Orders “source of truth” gap analysis

### 6.1 Do `sales_orders` + `sales_order_lines` exist (models + migrations)?

- **Models exist**: `app/eqms/modules/rep_traceability/models.py` defines `SalesOrder` and `SalesOrderLine`.
- **Migration exists**: `migrations/versions/b1c2d3e4f5g6_add_sales_orders_tables.py` creates both tables and adds `distribution_log_entries.sales_order_id`.
- **Gap**: this is still a **deployment/migration risk** (see Blocker B1).

### 6.2 Do distributions have `sales_order_id` and is it populated by each ingestion path?

| Ingestion path | Populates `sales_orders`? | Populates `sales_order_lines`? | Populates `distribution_log_entries.sales_order_id`? | Evidence |
|---|---:|---:|---:|---|
| ShipStation sync | ✅ | ✅ | ✅ | `shipstation_sync.service::run_sync` |
| PDF import via **Distribution Log** page | ✅ | ✅ | ✅ | `rep_traceability.admin::distribution_log_import_pdf_post` |
| PDF import via **Sales Orders** page | ✅ | ✅ | ❌ | `rep_traceability.admin::sales_orders_import_pdf_post` |
| CSV import (distribution log) | ❌ | ❌ | 🟡 (only if user manually links later) | `rep_traceability.admin::distribution_log_import_csv_post` |
| Manual distribution entry | ❌ | ❌ | 🟡 (optional dropdown) | `rep_traceability.admin::distribution_log_new_post` + template |

### 6.3 Manual distribution entry: does it enforce linking to an order or produce “pending assignment”?

- **Current**:
  - Customer selection is required.
  - Sales order selection is optional (dropdown of 100 recent orders).
  - There is no “pending assignment” workflow or reconciliation view.
- **Where**:
  - Template: `app/eqms/templates/admin/distribution_log/edit.html` (`sales_order_id` optional)
  - Handler: `rep_traceability.admin::distribution_log_new_post` passes `sales_order_id` through if provided.
- **Gap vs spec**: spec expects “sales orders are source-of-truth” and all distributions link to orders; current manual flow does not enforce it.

### 6.4 Data integrity risks when linking distributions to orders

- **Mismatch risk**: user can select a `sales_order_id` that belongs to a different customer than the selected `customer_id` (no server-side validation observed in `distribution_log_new_post`).
- **Fix direction**:
  - When `sales_order_id` is provided, validate:
    - `sales_order.customer_id == selected customer_id`
    - else reject with a clear flash error.
- **How to verify**:
  - Attempt to link a distribution for Customer A to a Sales Order for Customer B; it should be blocked.

---

## 7) 2025 Sales Orders PDF ingestion audit

### 7.1 Parsing libs present in requirements?

- **Yes**: `pdfplumber` is listed in `requirements.txt`.
- **But**: runtime environments must actually install it; in this environment, `pdfplumber` is not installed (Blocker B2).

### 7.2 Where parsing code lives

- **Parser**: `app/eqms/modules/rep_traceability/parsers/pdf.py::parse_sales_orders_pdf`
  - Uses `pdfplumber.open(...).pages[].extract_tables()`
  - Attempts to infer columns from table headers and normalize SKU/lot/date/quantity
  - Returns a grouped `ParseResult` with `orders`, `lines`, `errors`

### 7.3 Import routes and what they write

- **Route A (Distribution Log PDF import)**:
  - `POST /admin/distribution-log/import-pdf` → `rep_traceability.admin::distribution_log_import_pdf_post`
  - Writes:
    - `customers` via `find_or_create_customer`
    - `sales_orders` + `sales_order_lines`
    - `distribution_log_entries` **and sets `sales_order_id`** (good)
- **Route B (Sales Orders PDF import)**:
  - `POST /admin/sales-orders/import-pdf` → `rep_traceability.admin::sales_orders_import_pdf_post`
  - Writes:
    - `customers` via `find_or_create_customer`
    - `sales_orders` + `sales_order_lines`
    - **Does NOT create `distribution_log_entries`** (gap vs baseline “distributions link to orders” and the spec’s “import creates distributions” guidance)

### 7.4 UX / error reporting issues

- **Misleading UI**: Distribution Log import page labels PDF import as “P1 placeholder / not implemented”, but it is implemented and writes data.
  - **Where**: `app/eqms/templates/admin/distribution_log/import.html`
  - **Risk**: operators won’t trust/import 2025 data even though path exists.
- **Styling mismatch**: Sales Orders templates are Bootstrap-styled but app ships only `design-system.css` (no Bootstrap), so those pages likely look broken/unprofessional (may hide buttons/controls depending on CSS).
  - **Where**: `app/eqms/templates/admin/sales_orders/*.html`

### 7.5 Fix direction + verification

- **Fix direction (P0)**:
  - Install/ensure `pdfplumber` in runtime (and add a health indicator).
  - Remove duplication: make **one** canonical PDF import entrypoint. Recommended:
    - Keep `/admin/sales-orders/import-pdf` as spec-defined entrypoint and have it also create the linked `distribution_log_entries` (like the distribution-log import currently does).
    - Convert `/admin/distribution-log/import-pdf` to a redirect to `/admin/sales-orders/import-pdf` (or delete the post route) to avoid two competing behaviors.
  - Update `admin/distribution_log/import.html` copy to reflect reality (PDF import is implemented, and what it creates).
- **How to verify**:
  - Upload `2025 Sales Orders.pdf`
  - Verify counts:
    - `SELECT COUNT(*) FROM sales_orders WHERE source='pdf_import';`
    - `SELECT COUNT(*) FROM sales_order_lines l JOIN sales_orders o ON o.id=l.sales_order_id WHERE o.source='pdf_import';`
    - `SELECT COUNT(*) FROM distribution_log_entries WHERE source='pdf_import' AND sales_order_id IS NOT NULL;`
  - Spot-check a known order number from the PDF:
    - `SELECT * FROM sales_orders WHERE source='pdf_import' AND order_number='<X>';`
    - Confirm lines and linked distributions exist.

---

## 8) Legacy/outdated/duplicate code discovery (explicit deletion recommendations)

| Item | Recommendation | Why (risk if left) | Notes |
|---|---|---|---|
| `legacy/_archive.zip` | **DELETE** (preferred) or keep quarantined | Zip can be re-extracted/used accidentally; unclear provenance | If retained, keep only under `legacy/` with “DO NOT USE” README. |
| `legacy/DO_NOT_USE__REFERENCE_ONLY/repqms_Proto1_reference.py.py` | **QUARANTINE** (keep out of import path) | Monolithic legacy app with direct SQL, SMTP, PDF import variants; high chance of copy/paste regressions | Already quarantined; ensure nothing imports it. |
| `legacy/DO_NOT_USE__REFERENCE_ONLY/repqms_shipstation_sync.py.py` | **QUARANTINE** | Competing ShipStation sync logic + schema assumptions; can confuse devs during sync fixes | Already quarantined. |
| `admin/sales_orders/*.html` using Bootstrap classes | **REFACTOR** (if actively used) | Looks “broken” without Bootstrap; undermines admin usability | Convert to design-system components (`.card`, `.button`). |
| Duplicate PDF import behaviors (`/distribution-log/import-pdf` vs `/sales-orders/import-pdf`) | **REFACTOR** (remove one path) | Two entrypoints with different semantics will create data inconsistency and operator confusion | Consolidate to spec route. |

---

## 9) (System-wide) health notes impacting sales implementation

- **RBAC coverage**:
  - Sales Orders routes use `@require_permission("sales_orders.view")` and `@require_permission("sales_orders.import")`.
  - Ensure `scripts/init_db.py` seeds these permissions in production roles, otherwise routes 403.
- **CSRF**:
  - Admin POST routes (ShipStation run, imports, deletes) appear to lack CSRF tokens; this is a security risk even for admin-only systems.
- **Deployment hygiene**:
  - “Works in code” is not enough: sales parity features are tightly coupled to migrations + deps. Require a pre-flight checklist:
    - `alembic upgrade head`
    - verify `pdfplumber` installed
    - verify ShipStation limits configured for backfill run

---

## 10) Prioritized remediation backlog (lean)

| ID | Issue | Severity | Fix direction | Verification |
|---:|---|---|---|---|
| 1 | `sales_orders` schema not applied everywhere | **Blocker** | Ensure Alembic upgrades run before enabling sales routes | DB has tables; routes don’t error |
| 2 | `pdfplumber` missing in runtime → PDF import fails | **Blocker** | Install `pdfplumber` in runtime image/env; add dependency health check | Upload PDF succeeds; rows created |
| 3 | ShipStation backfill stops early due to low default limits | **High** | Increase limits for backfill; separate shipment/ order limits; surface limit warning prominently | 2025 months appear in `sales_orders` + `distribution_log_entries` |
| 4 | PDF import behavior split across two routes with different writes | **High** | Consolidate to `/admin/sales-orders/import-pdf` and make it create linked distributions; redirect/remove duplicate route | One import path; consistent row creation |
| 5 | Distribution Log import UI claims PDF is “P1 placeholder” | Medium | Update template copy and mode labeling | UI matches actual behavior |
| 6 | Manual/CSV distributions can exist without `sales_order_id` | Medium | Require/link sales orders (create “manual” sales orders on submit or require selection) | `sales_order_id` coverage improves; reconciliation view unnecessary |
| 7 | Sales Orders templates use Bootstrap-only CSS classes | Medium | Refactor templates to design system | Pages look consistent and usable |
| 8 | Navigation missing Sales Orders in top nav | Low | Add link in `_layout.html` for Sales Orders | Link present and working |

