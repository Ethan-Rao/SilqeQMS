# 09 DEBUG AUDIT + FIX PLAN — Sales System (Dashboard/Lots/Customers/ShipStation/RBAC) + Legacy Cleanup

Baseline spec used (source-of-truth): `docs/plans/SALES_DASHBOARD_REDESIGN_AND_SYSTEM_IMPROVEMENTS.md`

Additional project inputs inspected:
- Lot Log source-of-truth: `app/eqms/data/LotLog.csv` (also supported via `SHIPSTATION_LOTLOG_PATH` / `LotLog_Path`)
- 2025 sales orders reference: `2025 Sales Orders.pdf`
- Legacy reference archive (behavior reference only; do not port): `legacy/_archive.zip` and `legacy/DO_NOT_USE__REFERENCE_ONLY/*`

Scope emphasis (per request): Sales Dashboard, Lot Tracking, Customers, Distribution Log, Sales Orders PDF import, ShipStation sync, RBAC/permissions, data integrity, UX gaps, and legacy/duplicate code.

---

## 1) Snapshot summary (highest-impact findings)

- **Blocker: ShipStation “Run Sync” POST will crash** due to missing `request` import in `app/eqms/modules/shipstation_sync/admin.py` (`shipstation_run()` references `request.form`).
- **Blocker in production (reported): `/admin/sales-orders/import-pdf` returns 403** “Missing permission `sales_orders.import`” for `ethanr@silq.tech` — the code expects the permission + admin role assignment to exist in the DB.
- **Sales Dashboard is close to spec** (two-column layout, recent NEW vs REPEAT lists, right-column SKU + Lot Tracking, current-year lot filter, active inventory column), but **inline note-taking UX is not implemented** (spec requires inline editor + persistence + cross-surface visibility).
- **Sales Dashboard “Total Units” card is windowed (since start_date)**; spec calls for **Total Units (All Time)** (windowing should apply to orders/customers counts, not the all-time units card).
- **Active Inventory calculation likely incorrect for lots spanning multiple years** because current implementation subtracts **distributed units in the current year only**, not total distributed-to-date.
- **Distribution Log Details modal exists and is permission-protected**, but **does not support notes add/edit in-place** (spec requires notes to propagate everywhere).
- **Customer list now supports recency sort + rep filter + year filter** (good), but **“delete zero-order customers” is only available as a script** (`scripts/cleanup_zero_order_customers.py`), not discoverable or executable from the admin UI.
- **ShipStation month-scoped sync capability exists end-to-end** (month input in UI + date-range support in service), but **hard limits can silently prevent full backfills** (see `SHIPSTATION_MAX_PAGES`, `SHIPSTATION_MAX_ORDERS` and “LIMIT REACHED” messaging).
- **Sales Orders as source-of-truth is implemented**: ShipStation creates `sales_orders` + `sales_order_lines` and links `distribution_log_entries.sales_order_id`; PDF import also creates orders/lines and linked distributions.
- **Security gap: no CSRF protection** on state-changing POST routes (notes, imports, delete, sync run).
- **Legacy payload in `legacy/DO_NOT_USE__REFERENCE_ONLY/*` should be deleted/quarantined** to avoid accidental reuse and confusion.

---

## 2) Spec compliance matrix (baseline vs current)

Legend: ✅ implemented, 🟡 partially implemented, ❌ missing/broken

| Spec requirement (paraphrase) | Status | Evidence (file/route/model) | Notes |
|---|---:|---|---|
| Remove “Sales by Month” from Sales Dashboard | ✅ | `app/eqms/templates/admin/sales_dashboard/index.html` | Section is gone; dashboard is two-column. |
| Remove “Top Customers” from Sales Dashboard | ✅ | `app/eqms/templates/admin/sales_dashboard/index.html` | No top-customers table. |
| Add “Recent Orders from NEW customers” list (limit 20, recent) | ✅ | Template + `compute_sales_dashboard()` | `app/eqms/templates/admin/sales_dashboard/index.html`; `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard` |
| Add “Recent Orders from REPEAT customers” list (limit 20, recent) | ✅ | Template + service | Same as above. |
| Recent Orders rows have actions: View Details / Add Note / View Profile | 🟡 | Sales dashboard template | “+ Note” links to profile anchor; no “View Details” action. |
| Inline note editor (AJAX) from Sales Dashboard; notes persist and appear on customer profile + customer DB | ❌ | Spec requires new routes; not present | No `/admin/sales-dashboard/order-note*` endpoints; no inline editor; customers list doesn’t show note badges. |
| Sales-by-SKU table in right column | ✅ | Sales dashboard template | `app/eqms/templates/admin/sales_dashboard/index.html` |
| Lot Tracking in right column, current-year only | ✅ | `compute_sales_dashboard()` + template | Service filters `ship_date` to current-year; template shows `current_year`. |
| LotLog corrections applied to lot tracking | ✅ | `compute_sales_dashboard()` | Uses `load_lot_log_with_inventory()` and `lot_corrections`. |
| Filter out SKU names shown as lots | ✅ | `compute_sales_dashboard()` | Filters lots not matching `^SLQ-\d{5,12}$` and skips known SKUs. |
| Active Inventory column = Produced (LotLog) − Distributed (system) | 🟡 | `compute_sales_dashboard()` | Subtracts **current-year distributed** for that lot; spec implies distributed-to-date. |
| Distribution Log: add Details button + in-page modal | ✅ | Template + JSON endpoint | `app/eqms/templates/admin/distribution_log/list.html`; `GET /admin/distribution-log/entry-details/<id>` in `app/eqms/modules/rep_traceability/admin.py`. |
| Distribution Log details include order context + customer stats + top SKUs/lots | 🟡 | `distribution_log_entry_details()` | Includes linked `SalesOrder` summary and basic stats; top lots are “recent lots” only (not “top lots”). |
| Distribution Log: rep filter | ✅ | Template + filters | Rep select exists in template; list route must pass `reps`. |
| Notes can be added/edited from Distribution Log and propagate everywhere | ❌ | Not implemented | No notes editor on distribution log modal/list. |
| Customers list: remove “Find Duplicates” | ✅ | `app/eqms/templates/admin/customers/list.html` | No “Find Duplicates” button. |
| Customers list: default sorting = most recent order → oldest | ✅ | `customer_profiles.customers_list()` | Uses max ship_date subquery ordering. |
| Customers cleanup: delete customers with 0 orders | 🟡 | Script exists | `scripts/cleanup_zero_order_customers.py` exists; no admin UI workflow. |
| Rep assignment on customer profile | ✅ | Customer detail UI + model | `Customer.primary_rep_id` exists; `customer_profiles` supports rep selection/validation. |
| Rep address fields with ZIP validation | ✅ | Admin “Me” page | `app/eqms/models.py::User` has address fields; `app/eqms/admin.py::me_update()` validates ZIP. |
| ShipStation sync: month-scoped sync (throttling) | 🟡 | UI + service exist; POST handler broken | UI month picker: `app/eqms/templates/admin/shipstation/index.html`; service supports date range: `shipstation_sync/service.py::run_sync`; **POST crashes** due to missing import. |
| Permission fix: superadmin must have `sales_orders.import` (PDF import not 403) | 🟡 | Code + seed exist; DB state may be wrong | Route requires permission; seed creates it; production user/role may not be aligned. |
| Diagnostic permissions view | ✅ | Route exists | `GET /admin/debug/permissions` in `app/eqms/admin.py`. |

---

## 3) Critical runtime breakages (Blockers)

### B1) ShipStation Run Sync crashes (NameError)
- **Where**: `app/eqms/modules/shipstation_sync/admin.py::shipstation_run()` (`POST /admin/shipstation/run`)
- **Symptom**: Clicking “Run Sync” returns 500; logs show `NameError: name 'request' is not defined`.
- **Root cause**: `request` is used (`request.form.get("month")`) but not imported in this module.
- **Severity**: **Blocker**
- **Fix direction**:
  - Add `request` to the Flask imports at top of `shipstation_sync/admin.py` (same pattern as other blueprints).
- **Verification**:
  - Log in as admin → `/admin/shipstation` → submit Run Sync (with and without month) → should redirect back with success/flash (not 500).

### B2) PDF import route 403 for ethanr
- **Where**: `app/eqms/modules/rep_traceability/admin.py::sales_orders_import_pdf_get/post` (`GET/POST /admin/sales-orders/import-pdf`)
- **Symptom**: `403 Forbidden` with missing permission `sales_orders.import` (rendered in `errors/403.html`).
- **Root cause**: DB state mismatch: permission and/or role assignment missing for the logged-in user (details in Section 4).
- **Severity**: **Blocker** (blocks 2025 ingestion workflow)
- **Fix direction**: seed + role assignment remediation (Section 4).
- **Verification**: `/admin/debug/permissions` shows `sales_orders.import` and page returns 200.

---

## 4) Permissions/RBAC deep dive (403 on import PDF)

### What the code expects (current reality)
- **Route protection**:
  - `GET/POST /admin/sales-orders/import-pdf` requires `@require_permission("sales_orders.import")` in `app/eqms/modules/rep_traceability/admin.py`.
- **Permission seeding**:
  - `scripts/init_db.py` creates `sales_orders.import` and appends it to the `admin` role permissions.
- **RBAC enforcement**:
  - `app/eqms/rbac.py::require_permission()` checks `g.current_user.roles[].permissions[]` and aborts 403 if missing.
- **Built-in diagnostic**:
  - `GET /admin/debug/permissions` shows current user roles + permission keys (`app/eqms/admin.py::debug_permissions`).

### Root cause (concrete diagnosis)
The 403 “Missing permission `sales_orders.import`” for `ethanr@silq.tech` happens when **the DB’s role/permission graph is not aligned to the logged-in user**:

1) **User has no `admin` role** in `user_roles`, even if the role + permission exist.
- Most likely when production was seeded with default `ADMIN_EMAIL=admin@silqeqms.com`, but the operator logs in as `ethanr@silq.tech`.

2) **Permission exists but is not linked to role** in `role_permissions` (older DB seeded before `sales_orders.import` was added; seeding not re-run).

3) **Permission row itself is missing** (seeding never ran at all on that DB).

### Minimal fix (seed update + safe re-run plan)
- **P0 fix strategy** (no schema change required):
  - Re-run idempotent seeding against production DB: `python scripts/init_db.py`
  - Ensure seeding runs with **the actual admin email**:
    - Set env `ADMIN_EMAIL=ethanr@silq.tech` before running seed (or manually attach role in DB).
  - If you cannot change `ADMIN_EMAIL`, add a one-off “attach admin role to existing user” script (tiny) or run a single SQL insert (see below).

### Verification query checklist (roles/permissions joins)

Run these against the production DB (SQLite syntax; adjust quoting for Postgres):

1) Confirm permission exists:
```sql
SELECT id, key, name FROM permissions WHERE key = 'sales_orders.import';
```

2) Confirm admin role exists:
```sql
SELECT id, key, name FROM roles WHERE key = 'admin';
```

3) Confirm admin role has the permission:
```sql
SELECT r.key AS role_key, p.key AS perm_key
FROM roles r
JOIN role_permissions rp ON rp.role_id = r.id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.key = 'admin' AND p.key = 'sales_orders.import';
```

4) Confirm ethanr user exists:
```sql
SELECT id, email, is_active FROM users WHERE lower(email) = lower('ethanr@silq.tech');
```

5) Confirm ethanr has admin role:
```sql
SELECT u.email, r.key
FROM users u
JOIN user_roles ur ON ur.user_id = u.id
JOIN roles r ON r.id = ur.role_id
WHERE lower(u.email) = lower('ethanr@silq.tech');
```

If (5) is missing, attach admin role (one-time):
```sql
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u, roles r
WHERE lower(u.email) = lower('ethanr@silq.tech')
  AND r.key = 'admin';
```

### Regression prevention
- Keep `scripts/init_db.py` as the canonical idempotent seed and **ensure the release/runbook always re-runs it** after migrations.
- Keep `/admin/debug/permissions` in admin navigation (or at least documented) as the fast path to diagnose future 403s.

---

## 5) Sales Dashboard audit (layout + functionality per spec)

### What’s implemented
- **Layout**: Two-column layout is implemented (Recent Orders left; SKU + Lot Tracking right): `app/eqms/templates/admin/sales_dashboard/index.html`.
- **New vs Repeat**: `compute_sales_dashboard()` computes:
  - windowed stats
  - `recent_orders_new` (lifetime order count ≤ 1)
  - `recent_orders_repeat` (lifetime order count ≥ 2)
  - Evidence: `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard`.
- **Sales-by-SKU**: present and placed in the right column.
- **Lot Tracking**: current-year, corrected, active inventory column is rendered (see Section 6).

### Gaps / flaws

#### SD1) “Total Units” is not “All Time”
- **Where**: `compute_sales_dashboard()` and template card label
- **Symptom**: “Total Units” changes when start_date changes; spec expects “Total Units (All Time)” regardless of the date window.
- **Root cause**: `total_units` is computed from `window_entries`, not from lifetime entries.
- **Severity**: **High** (incorrect KPI semantics)
- **Fix direction**:
  - Add `total_units_all_time` computed from an aggregate over all `DistributionLogEntry.quantity` (or from `sales_order_lines` if that becomes canonical).
  - Keep the existing windowed units as a separate metric if needed.
- **Verification**:
  - Change start_date from 2025-01-01 to 2026-01-01; “Total Units (All Time)” should remain constant.

#### SD2) Notes workflow is not inline / not surfaced across pages
- **Where**: Sales dashboard template uses “+ Note” link to `customer_profiles.customer_detail#notes`.
- **Symptom**: No inline note editor; notes are not displayed on dashboard rows; customer database page does not show a note indicator.
- **Root cause**: Spec-required AJAX endpoints + template fragments are not implemented for dashboard notes.
- **Severity**: **High** (core UX workflow missing)
- **Fix direction**:
  - Add endpoints per spec (see Section 13 P0/P1 tasks):
    - `GET /admin/sales-dashboard/order-note-form/<customer_id>` (HTML fragment)
    - `POST /admin/sales-dashboard/order-note` (JSON)
  - Reuse existing note service functions (`customer_profiles.service.add_customer_note`) and permissions (`customers.notes`).
- **Verification**:
  - Add note from dashboard → note appears immediately on dashboard row, on customer profile notes, and is discoverable from customers list (badge or count).

#### SD3) “View Details” action missing for dashboard orders
- **Where**: Dashboard recent order rows
- **Symptom**: No in-page details/accordion to see SKU/lot breakdown for the order.
- **Root cause**: No order-details endpoint or modal wiring for dashboard.
- **Severity**: **Medium**
- **Fix direction**:
  - Add a lightweight details modal:
    - `GET /admin/sales-orders/<id>` already exists (page)
    - optionally add `GET /admin/sales-orders/<id>/json` to power a modal.
- **Verification**: Click “Details” shows SKU/lot lines and linked distributions without leaving the page.

### Performance notes (dashboard)
- **Issue**: `compute_sales_dashboard()` loads:
  - all lifetime rows (`.all()` on `DistributionLogEntry` columns)
  - all windowed entries (`.all()`)
  - all current-year entries for lots (`.all()`)
- **Risk**: will degrade with a large order history (slow page, high RAM).
- **Lean optimization direction**: replace `.all()` with grouped aggregates (`GROUP BY`) and limit recent orders via SQL ordering/limit.

---

## 6) Lot Tracking audit (correct lots only + active inventory)

### What’s implemented (good)
- **LotLog is loaded and used** (inventory + corrections): `app/eqms/modules/shipstation_sync/parsers.py::load_lot_log_with_inventory`.
- **Canonical mapping applied**:
  - Distribution lots normalized (`normalize_lot`)
  - Corrections applied (`lot_corrections`)
- **SKU values are filtered out / invalid lot formats removed**:
  - Filters via regex `^SLQ-\d{5,12}$` and known SKU list.
- **Current-year filter is applied**:
  - `ship_date >= year_start AND ship_date < year_end`
- **Active inventory column exists in UI** and negative values are flagged:
  - Template shows ⚠️ for negative.

### Remaining correctness gap

#### LT1) Active Inventory subtracts only current-year distributions
- **Where**: `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard` lot tracking section
- **Symptom**: Active Inventory appears too high for lots that had distributions in prior years (or outside the current-year window).
- **Root cause**: `rec["units"]` is computed from `lot_entries` filtered to current-year, then used in `active_inventory = produced - rec["units"]`.
- **Severity**: **High** (inventory correctness)
- **Fix direction** (lean):
  - Keep the **display list** limited to current-year lots, but compute `distributed_units_to_date` per lot using an all-time aggregate for those lots:
    - Query: `SELECT corrected_lot, SUM(quantity) FROM distribution_log_entries GROUP BY corrected_lot` (apply correction logic in SQL or post-process).
  - Store both values if useful:
    - `units_current_year`
    - `units_all_time`
    - `active_inventory = produced - units_all_time`
- **Verification**:
  - Pick a lot with shipments across years and confirm `active_inventory` matches:
    - Produced from LotLog − SUM(distributions all time for that lot).

---

## 7) Distribution Log audit (in-page “Details” + stats + rep filter)

### What’s implemented
- **Details button + modal**: `app/eqms/templates/admin/distribution_log/list.html` uses `<dialog>` and fetches JSON.
- **JSON endpoint exists and is permission-protected**:
  - `GET /admin/distribution-log/entry-details/<entry_id>`
  - `@require_permission("distribution_log.view")`
  - Implementation: `app/eqms/modules/rep_traceability/admin.py::distribution_log_entry_details`.
- **Rep filter exists** in UI and filter parsing supports it (and route passes reps): distribution log list template includes a rep dropdown.

### Gaps

#### DL1) Notes add/edit from Distribution Log is missing
- **Where**: Distribution log modal/template and backend
- **Symptom**: No way to add or edit notes from the distribution log “Details” workflow.
- **Root cause**: No endpoint or UI implemented for notes in this context.
- **Severity**: **Medium**
- **Fix direction**:
  - Add a minimal note editor in the modal (customer-level notes) using existing `customers.notes` permission and note services.
- **Verification**: Create/edit note from details modal → visible on customer profile and (optionally) dashboard and customer list.

#### DL2) Customer stats computation is not scalable
- **Where**: `distribution_log_entry_details()` loads all customer entries and computes in Python
- **Symptom**: Modal may be slow for high-volume customers.
- **Root cause**: `s.query(DistributionLogEntry).filter(customer_id=...).all()` then Python aggregation.
- **Severity**: **Medium**
- **Fix direction**:
  - Replace with SQL aggregates: first/last ship_date, count distinct orders, sum quantity, top SKUs via GROUP BY.
- **Verification**: For a customer with many rows, modal loads quickly and DB query count is bounded.

---

## 8) Customers audit (duplicates + cleanup + sorting)

### What’s implemented
- **Recency sorting**: customers list orders by max ship_date desc nulls last:
  - `app/eqms/modules/customer_profiles/admin.py::customers_list()`
- **Rep filter + year filter**: implemented in both handler and template:
  - `app/eqms/templates/admin/customers/list.html`
- **“Find Duplicates” removed**: not present in the current template.
- **Rep assignment**: customer create/edit supports `primary_rep_id` validation (active user) in `customer_profiles/admin.py`.

### Data integrity risks and root causes

#### C1) Customer duplicates remain likely due to multi-ingestion creation paths
- **Where**:
  - ShipStation creates/links customers (service-level)
  - PDF import may create/link customers (sales order import path)
  - Manual distribution entry can create or link customers
- **Symptom**: Same facility can appear as multiple customers (formatting differences, abbreviations, shipping “company” vs true facility).
- **Root cause**: Customer identity is still partially name-based; canonical keys can diverge across sources.
- **Severity**: **High**
- **Fix direction**:
  - Enforce a single canonicalization function for customer identity at all ingestion points (ShipStation + PDF + CSV + manual):
    - Always generate/update `Customer.company_key` using shared canonicalizer.
    - Prefer linking by `customer_id` when sales orders exist; avoid creating new customers if a matching `company_key` exists.
- **Verification**:
  - Run a duplicate report query before/after (group by company_key) and confirm reduction.

#### C2) Zero-order customers cleanup is not discoverable
- **Where**: only `scripts/cleanup_zero_order_customers.py`
- **Symptom**: Admin UX still shows “new” customers with 0 orders; requires CLI intervention.
- **Root cause**: Script exists but no admin UI affordance.
- **Severity**: **Medium**
- **Fix direction**:
  - Add an admin-only page or button that runs a **dry-run report** (no deletes) and instructs operator to run script with `--yes` when ready; or provide a minimal admin POST endpoint guarded by `admin.view` plus confirmation.
- **Verification**:
  - Dry-run output shows count; after execution, customer list no longer includes 0-order records.

---

## 9) ShipStation sync audit (month-scoped sync + stability)

### What’s implemented
- **Month picker exists**: `app/eqms/templates/admin/shipstation/index.html` (`<input type="month" name="month">`)
- **Month-scoped sync logic exists**:
  - `shipstation_sync/admin.py::shipstation_run()` parses month into `start_date/end_date`
  - `shipstation_sync/service.py::run_sync(..., start_date, end_date)` uses ShipStation shipments-by-date API
- **Sales Orders as source-of-truth**:
  - ShipStation sync creates/updates `sales_orders` + `sales_order_lines` and links distributions via `sales_order_id`.
- **Idempotency**:
  - Uses `SalesOrder.external_key` (`ss:<order_id>`) and `DistributionLogEntry.external_key` (shipment+sku+lot) to avoid duplicates.

### Critical defect (must fix)
- **Run Sync crashes** (Section 3 B1).

### Backfill completeness (2025 visibility)
- **If system “only shows 2026 orders”** after this code is deployed, the remaining causes are operational/config, not missing logic:
  - Sync not run for 2025 ranges
  - Limits too low (pages/orders), causing partial history
  - API credentials missing/invalid
  - ShipStation returns fewer shipments than expected for date range (filters/account)

**Verification SQL (to prove 2025 presence):**
```sql
SELECT MIN(ship_date) AS min_ship_date, MAX(ship_date) AS max_ship_date, COUNT(*) AS cnt
FROM distribution_log_entries
WHERE source = 'shipstation';
```
```sql
SELECT strftime('%Y', ship_date) AS y, COUNT(*) AS cnt
FROM distribution_log_entries
WHERE source='shipstation'
GROUP BY strftime('%Y', ship_date)
ORDER BY y;
```

### Duplicate / legacy sync implementations
- **Legacy**: `legacy/DO_NOT_USE__REFERENCE_ONLY/repqms_shipstation_sync.py.py` (do not use; delete/quarantine).
- **Current**: `app/eqms/modules/shipstation_sync/*` (authoritative).

---

## 10) Legacy/outdated/duplicate code inventory (DELETE list)

| Item | Why legacy/unused/risky | Action | Risk if kept | How to verify safe removal |
|---|---|---:|---|---|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/repqms_Proto1_reference.py.py` | Prototype reference code; not imported; easy to confuse for “real” implementation | **DELETE** | Someone copies/ports insecure/incorrect patterns | `grep -R "repqms_Proto1_reference" -n` should be empty outside legacy |
| `legacy/DO_NOT_USE__REFERENCE_ONLY/repqms_shipstation_sync.py.py` | Competing sync logic; may be outdated and non-idempotent | **DELETE** | Accidental execution/backfill with different semantics | `grep -R "repqms_shipstation_sync" -n` should be empty outside legacy |
| `legacy/DO_NOT_USE__REFERENCE_ONLY/*.html` | Old UI reference; can drift and confuse UX decisions | **QUARANTINE** (keep as reference or move under docs) | Designers/Dev implement from wrong template | Ensure no Jinja extends/includes reference these files |
| `legacy/_archive.zip` | Reference-only binary archive | **QUARANTINE** | People unzip and run old code | Ensure not referenced by any scripts; keep documented as reference only |

---

## 11) Security and data-safety findings

- **CSRF missing**:
  - Many POST routes (distribution deletes, PDF import, sync run, notes) accept cross-site POSTs if user is logged in.
  - **Fix direction**: add minimal CSRF token mechanism or Flask-WTF (dependency tradeoff) or a lightweight custom token in session.
- **PDF upload safety**:
  - PDF is read into memory (`f.read()`); no explicit size limit.
  - **Fix direction**: enforce `MAX_CONTENT_LENGTH` in Flask config; validate content type/extension; handle parse errors cleanly.
- **ShipStation diagnostics endpoint risk**:
  - `GET /admin/shipstation/diag` can expose raw order data; it is disabled in production unless `SHIPSTATION_DIAG_ENABLED=1`.
  - **Fix direction**: keep disabled; consider also requiring `admin.view` + `shipstation.view` (currently only `shipstation.view`).
- **Path traversal / storage safety**:
  - Review `app/eqms/storage.py` for local key sanitization and ensure keys cannot escape storage root (defense-in-depth).

---

## 12) Performance & reliability findings

- **Dashboard aggregates scale poorly**:
  - Multiple `.all()` calls across entire `distribution_log_entries` and year subsets; will degrade with history growth.
  - **Lean fix**: shift to SQL `GROUP BY` aggregates and `LIMIT` queries for recent orders.
- **Distribution log details endpoint can be slow for large customers**:
  - Loads all customer entries and aggregates in Python.
  - **Lean fix**: SQL aggregates for stats + top SKUs.
- **Indexing considerations** (verify in migrations; add if missing):
  - `distribution_log_entries`: `(ship_date)`, `(customer_id)`, `(order_number)`, `(source)`, unique `(external_key)`
  - `sales_orders`: unique `(source, external_key)`, `(customer_id)`, `(order_date)`

---

## 13) Developer-ready Fix Plan (what to implement)

Dependency-ordered checklist with acceptance criteria and verification.

### P0 (must-fix blockers + correctness)

#### P0.1 Fix ShipStation Run Sync crash
- **Files**: `app/eqms/modules/shipstation_sync/admin.py`
- **Change**: import `request` from Flask.
- **AC**:
  - “Run Sync” works (200/302) and records a sync run row.
- **Verify**:
  - UI: `/admin/shipstation` submit Run Sync.
  - DB: `SELECT COUNT(*) FROM shipstation_sync_runs;` increases.

#### P0.2 Fix `/admin/sales-orders/import-pdf` 403 for ethanr
- **Files**: `scripts/init_db.py`, operational runbook (or tiny role-attach script)
- **Change**:
  - Ensure seed is rerun against prod DB and `ethanr@silq.tech` has `admin` role.
- **AC**:
  - `/admin/debug/permissions` shows `sales_orders.import`
  - `/admin/sales-orders/import-pdf` returns 200 for ethanr
- **Verify**:
  - Use SQL queries in Section 4.

#### P0.3 Correct “Total Units (All Time)” semantics
- **Files**: `app/eqms/modules/rep_traceability/service.py`, `app/eqms/templates/admin/sales_dashboard/index.html`
- **Change**:
  - Add all-time units metric and update label.
- **AC**:
  - Total Units card does not change when changing start_date.
- **Verify**:
  - Load dashboard with different start_date values and compare.

#### P0.4 Fix Active Inventory to subtract distributed-to-date
- **Files**: `app/eqms/modules/rep_traceability/service.py`
- **Change**:
  - For the lots shown (current-year list), compute total distributed across all time for those lots and subtract from LotLog produced units.
- **AC**:
  - Active inventory matches `produced - distributed_all_time` for each lot.
- **Verify**:
  - Spot-check via SQL sum for a known lot.

### P1 (important usability / professionalism)

#### P1.1 Implement dashboard inline note-taking (spec workflow)
- **Files**:
  - `app/eqms/modules/rep_traceability/admin.py` (new endpoints)
  - `app/eqms/templates/admin/sales_dashboard/index.html` (inline UI + fetch)
  - `app/eqms/modules/customer_profiles/service.py` (reuse note creation)
- **Change**:
  - Add spec endpoints:
    - `GET /admin/sales-dashboard/order-note-form/<customer_id>`
    - `POST /admin/sales-dashboard/order-note`
  - Require `customers.notes`.
  - Add inline editor and show note badge/count.
- **AC**:
  - Add note inline on dashboard; appears without navigation; shows on customer profile and persists.
- **Verify**:
  - Create note → reload dashboard and customer profile → note present.

#### P1.2 Add “Details” for Sales Dashboard recent orders
- **Files**:
  - `app/eqms/templates/admin/sales_dashboard/index.html`
  - Optionally add a JSON endpoint under `rep_traceability/admin.py`
- **Change**:
  - Add a modal similar to distribution log that shows SKU/lot lines for the order.
- **AC**:
  - “View Details” shows order SKU breakdown and linked distributions.

#### P1.3 Add notes editing from Distribution Log details modal
- **Files**:
  - `app/eqms/templates/admin/distribution_log/list.html`
  - `customer_profiles` note endpoints (reuse) or add minimal JSON proxy
- **AC**:
  - Note created/edited from distribution details and visible on customer profile.

### P2 (optimizations / hardening)

#### P2.1 Reduce dashboard query load
- **Files**: `app/eqms/modules/rep_traceability/service.py`
- **Change**:
  - Replace `.all()`-heavy logic with aggregate queries and `LIMIT` for recent orders.
- **AC**:
  - Dashboard remains responsive with large datasets; DB query time bounded.

#### P2.2 Add/request CSRF protection
- **Files**: app factory/config, templates, POST handlers
- **Change**: add minimal CSRF token checks for all POST forms and JSON endpoints.
- **AC**: CSRF attempts fail; normal usage passes.

