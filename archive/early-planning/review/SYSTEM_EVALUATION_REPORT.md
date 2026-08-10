# SYSTEM EVALUATION REPORT — SilqQMS (Admin workflows)

## 1) Executive summary (1 page max)

**Overall status: 🔴 unstable**

This evaluation executed the required Admin workflow end-to-end using a fresh, seeded database and the current Flask codebase. Core routes exist for Distribution Log, Tracing Reports (immutable CSV), Approval `.eml` evidence upload/download, Customer Profiles, Sales Dashboard, and audit event recording. However, **Customer Profiles writes do not persist** (missing DB commits), which **breaks core linking** (customers ↔ distribution entries), and there is **no Audit Trail UI surface** (404) despite audit events being recorded.

### Top 5 critical issues (with severity)

1. **Critical** — Customer create/update/notes do not persist (no DB commit) → breaks required Customer Profiles feature and causes downstream linkage corruption.
2. **Critical** — Customer ↔ Distribution linking can silently point to the wrong customer id (caused by non-persisted customers + later id reuse) and Facility fields are not guaranteed to be overwritten when `customer_id` is provided but missing.
3. **High** — Audit Trail is required but there is **no UI** to view audit events (`/admin/audit` returns 404).
4. **High** — Auth + RBAC UX: after logout, admin routes return **403** (no redirect to login), increasing confusion and support load.
5. **Medium** — Approval `.eml` “parsed metadata display” is incomplete: UI shows subject/from/to but **does not display parsed date**.

### Top 5 “lean wins” (small changes with big payoff)

1. **Commit Customer Profiles transactions** in `customer_profiles/admin.py` (create/update/note add/edit/delete).
2. **Validate `customer_id` existence** on Distribution Log create/edit when provided; fail fast with flash message.
3. **Add a minimal Audit Trail page** listing recent `audit_events` with basic filters (action, date range, actor).
4. **Show `email_date`** on tracing report approval evidence list (template-only change).
5. **Adjust RBAC** to redirect unauthenticated users to `/auth/login` instead of returning 403.

---

## 2) Test environment

- **Date/time of evaluation**: 2026-01-19 (local Windows), ~20:30
- **App URL evaluated**: `http://127.0.0.1:8080` (local). Production URL not provided in-agent.
- **Browser used**: N/A (primary evidence captured via Flask `test_client`); templates/routes reviewed directly.
- **User role tested (Admin)**: `admin@silqeqms.com` (seeded via `scripts/init_db.py`)
- **Data state assumption**: Fresh SQLite DB (`qa_eval.db`) migrated via Alembic and seeded (clean state).

---

## 3) Functional test results (systematic)

Evidence style used:
- **Script output** from an end-to-end run using Flask `test_client`
- **Exact HTTP status codes** and **exact routes**
- **DB read (SQLAlchemy) counts** for audit events

### A) Authentication / Login / Logout

- **Test steps performed**:
  - `GET /health`
  - `POST /auth/login` with seeded admin credentials
  - `GET /admin/` after login
  - `GET /auth/logout`
  - `GET /admin/` after logout
- **Expected result**:
  - Login succeeds and redirects to Admin
  - Logout clears session and Admin routes redirect to login
- **Actual result**:
  - Login succeeded (`302 → /admin/`, then `200`)
  - Logout succeeded (`302 → /`)
  - After logout, `GET /admin/` returns **403** (no redirect)
- **Pass/Fail**: **Fail** (logout UX / post-logout navigation)
- **Evidence**:
  - `POST /auth/login 302 Location=/admin/`, `GET /admin/ 200`
  - `GET /auth/logout 302 Location=/`, then `GET /admin/ after logout 403`

### B) Navigation + Admin shell

- **Test steps performed**:
  - `GET /admin/` after login
  - Checked presence of required module links in admin shell/template
- **Expected result**:
  - Admin dashboard loads; navigation links resolve
- **Actual result**:
  - Admin dashboard loads in the current codebase evaluation (`GET /admin/ 200`)
  - Observed earlier runtime logs from an older-running dev server showing `BuildError` for missing `rep_traceability.*` endpoints (stale process / misregistered blueprint), causing `GET /admin/` to 500 when logged in.
- **Pass/Fail**: **🟡 Partial**
- **Evidence**:
  - Pass: `GET /admin/ 200`
  - Reliability note (from runtime log): `werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'rep_traceability.distribution_log_list'` on `/admin/` (500)

### C) Customer Profiles

#### create / edit / notes

- **Test steps performed**:
  - `POST /admin/customers/new` to create “Test Hospital A”
  - DB read to confirm customer persisted
- **Expected result**:
  - Customer row persists; Customer audit event recorded
- **Actual result**:
  - Route returned redirect to `/admin/customers/1`, but **DB did not contain the customer** (not persisted).
  - `customer.create` audit event count remained **0**
- **Pass/Fail**: **Fail**
- **Evidence**:
  - `POST /admin/customers/new 302 Location=/admin/customers/1`
  - DB check: `DB has customer A? False`
  - Audit evidence: `audit_counts['customer.create'] = 0`

#### link customer to distribution entries

- **Test steps performed**:
  - Attempted to create distribution entry linked to the newly-created customer id
- **Expected result**:
  - Distribution entry links to correct customer and uses customer master facility fields
- **Actual result**:
  - Because customer create was not committed, the customer id was later reused by a different customer (created via CSV import), causing **silent mis-linking**.
  - Distribution entry `facility_name` remained as submitted (not overwritten).
- **Pass/Fail**: **Fail**
- **Evidence**:
  - Distribution entry DB read: `{'customer_id': 1, 'facility_name': 'SHOULD_BE_OVERRIDDEN'}` while customer id 1 belonged to “Test Hospital B”

### D) Distribution Log

#### manual create

- **Test steps performed**:
  - `POST /admin/distribution-log/new` with valid ship date, SKU, lot, quantity
- **Expected result**:
  - Entry created and persisted; audit event created
- **Actual result**:
  - Entry created (`302 → /admin/distribution-log`)
  - `distribution_log_entry.create` audit event recorded
- **Pass/Fail**: **Pass**
- **Evidence**:
  - `POST /admin/distribution-log/new 302 Location=/admin/distribution-log`
  - Audit evidence: `audit_counts['distribution_log_entry.create'] = 2` (manual + CSV-created entry)

#### edit

- **Test steps performed**:
  - Not executed (requires reason-for-change form submission; code review indicates implemented)
- **Expected result**:
  - Edit requires reason; audit event recorded with reason + diff
- **Actual result**:
  - Not executed in this run
- **Pass/Fail**: **Not tested**
- **Evidence**:
  - Template enforces reason field for edits/deletes (`admin/distribution_log/edit.html`)

#### delete

- **Test steps performed**:
  - Not executed (requires reason; not needed to surface defects found)
- **Expected result**:
  - Delete requires reason; audit event recorded
- **Actual result**:
  - Not executed
- **Pass/Fail**: **Not tested**
- **Evidence**: N/A

#### CSV import (duplicates behavior)

- **Test steps performed**:
  - `POST /admin/distribution-log/import-csv` with a CSV containing two identical rows
- **Expected result**:
  - First row creates entry; second is detected as duplicate and skipped; duplicates are shown on results page
- **Actual result**:
  - Import returned 200 (rendered results page) and **“Duplicates skipped” was present**.
  - Import summary audit event recorded
- **Pass/Fail**: **Pass**
- **Evidence**:
  - `POST /admin/distribution-log/import-csv 200`
  - `import page contains "Duplicates skipped"? True`
  - Audit evidence: `audit_counts['distribution_log_entry.import_csv'] = 1`

#### export filtered

- **Test steps performed**:
  - Not executed (code review indicates handler exists and records audit)
- **Expected result**:
  - CSV download includes filter set; audit event recorded
- **Actual result**:
  - Not executed
- **Pass/Fail**: **Not tested**
- **Evidence**: N/A

### E) Tracing Reports

#### generate (month + filters)

- **Test steps performed**:
  - `POST /admin/tracing/generate` with `month=YYYY-MM`
- **Expected result**:
  - New immutable report created; audit event recorded
- **Actual result**:
  - Generated successfully (`302 → /admin/tracing/1`)
  - Report row_count reflected 2 distributions in the month
- **Pass/Fail**: **Pass**
- **Evidence**:
  - `POST /admin/tracing/generate 302 Location=/admin/tracing/1`
  - DB: `tracing_report: {'id': 1, 'row_count': 2}`

#### download CSV

- **Test steps performed**:
  - `GET /admin/tracing/1/download`
- **Expected result**:
  - CSV downloads; audit event recorded
- **Actual result**:
  - Download succeeded (`200`, `Content-Type: text/csv; charset=utf-8`)
  - Audit event recorded
- **Pass/Fail**: **Pass**
- **Evidence**:
  - `GET /admin/tracing/<id>/download 200 bytes=229`
  - Audit evidence: `tracing_report.download = 1`

#### immutability (regenerate creates new report)

- **Test steps performed**:
  - Code-level verification of storage key generation includes timestamp and new DB row each run
- **Expected result**:
  - Regeneration creates a new TracingReport and new storage key; does not overwrite prior report
- **Actual result**:
  - Implementation writes storage key `tracing_reports/<month>/<hash>_<timestamp>.csv` and inserts new row
- **Pass/Fail**: **Pass (code-verified)**
- **Evidence**:
  - `app/eqms/modules/rep_traceability/service.py::generate_tracing_report_csv` uses timestamped `storage_key` and creates a new `TracingReport` row

### F) Approvals .eml

#### upload .eml to tracing report

- **Test steps performed**:
  - `POST /admin/tracing/1/approvals/upload` with `approval.eml`
- **Expected result**:
  - Upload succeeds; evidence is stored; audit event recorded
- **Actual result**:
  - Upload succeeded (`302 → /admin/tracing/1`)
  - Audit event recorded
- **Pass/Fail**: **Pass**
- **Evidence**:
  - `POST /admin/tracing/<id>/approvals/upload 302 Location=/admin/tracing/1`
  - Audit: `approval_eml.upload = 1`

#### parsed metadata display (subject/from/date)

- **Test steps performed**:
  - Uploaded `.eml` with Subject/From/To/Date headers; checked DB parse results and template display behavior
- **Expected result**:
  - Subject, From, and Date are displayed on the report detail page
- **Actual result**:
  - DB parsing succeeded (email_date populated), UI displays Subject/From/To but **does not display Date**
- **Pass/Fail**: **Fail**
- **Evidence**:
  - DB: `parsed: {'subject': 'QA Approval', 'from': 'approver@example.com', 'email_date': '2026-01-19 16:11:12'}`
  - Template `admin/tracing/detail.html` shows subject/from/to but no email date field

#### download .eml

- **Test steps performed**:
  - `GET /admin/approvals/1/download`
- **Expected result**:
  - Download succeeds and is `message/rfc822`; audit event recorded
- **Actual result**:
  - Download succeeded (`200`, `Content-Type: message/rfc822`)
  - Audit event recorded
- **Pass/Fail**: **Pass**
- **Evidence**:
  - `GET /admin/approvals/<id>/download 200 ct=message/rfc822`
  - Audit: `approval_eml.download = 1`

### G) Sales Dashboard

#### view dashboard with date filters

- **Test steps performed**:
  - `GET /admin/sales-dashboard?start_date=YYYY-MM-DD`
- **Expected result**:
  - Page renders and uses provided start_date
- **Actual result**:
  - Page rendered (`200`) and recorded audit event
- **Pass/Fail**: **Pass**
- **Evidence**:
  - `GET /admin/sales-dashboard 200`
  - Audit: `sales_dashboard.view = 1`

#### first-time vs repeat logic sanity check

- **Test steps performed**:
  - Code-level sanity check: customer key uses `customer_id` when present else canonical key; classification uses lifetime distinct orders
- **Expected result**:
  - Stable classification independent of window
- **Actual result**:
  - Logic matches stated rules; however, correctness depends on reliable customer linkage (currently broken by Customer Profiles persistence bug)
- **Pass/Fail**: **🟡 Partial**
- **Evidence**:
  - `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard` uses `customer_id` first, else canonical key

#### export dashboard CSV

- **Test steps performed**:
  - `GET /admin/sales-dashboard/export?start_date=YYYY-MM-DD`
- **Expected result**:
  - CSV downloads; audit event recorded
- **Actual result**:
  - Download succeeded (`200`, `text/csv`) and recorded audit event
- **Pass/Fail**: **Pass**
- **Evidence**:
  - `GET /admin/sales-dashboard/export 200 ct=text/csv`
  - Audit: `sales_dashboard.export = 1`

### H) Audit Trail

- **Test steps performed**:
  - Confirmed audit events were created for login, distribution create/import, tracing generate/download, approval upload/download, sales dashboard view/export via DB query
  - Checked for an admin UI to view audit events
- **Expected result**:
  - Audit events exist and there is a way for Admin to review them in-app
- **Actual result**:
  - Audit events exist (append-only) for most key actions
  - **No audit UI route exists** (`GET /admin/audit 404`)
  - Customer-related audit events did not appear because customer writes did not persist/commit
- **Pass/Fail**: **Fail** (required review surface missing; customer actions not recorded)
- **Evidence**:
  - Audit counts included: `auth.login=1`, `distribution_log_entry.create=2`, `distribution_log_entry.import_csv=1`, `tracing_report.generate=1`, `tracing_report.download=1`, `approval_eml.upload=1`, `approval_eml.download=1`
  - Missing: `customer.create=0`, `customer.update=0`
  - `GET /admin/audit 404`

---

## 4) Performance / reliability checks (lightweight)

- **Pages that feel slow (roughly)**: Not measured with a browser in-agent.
- **Any errors in DO logs while navigating**: DO logs not accessible in-agent; local runtime logs reviewed.
- **Any “500” occurrences and which routes caused them**:
  - Observed in local runtime logs (older running process): `/admin/` 500 due to missing endpoint `rep_traceability.distribution_log_list` (BuildError).
  - In the fresh evaluation run, no 500s occurred.
- **Other reliability notes**:
  - `GET /favicon.ico` returned 404 repeatedly in logs (minor).

---

## 5) Precision fix recommendations (most important section)

Ranked fixes (lean, surgical, file-level).

### Fix 1 — Customer Profiles writes do not persist (missing commit)

- **Severity**: Critical
- **Symptom**: Creating/editing a customer “works” (redirects to detail page) but the customer is not saved; notes/edits likely vanish on refresh.
- **Root-cause hypothesis**: Request handlers in Customer Profiles never call `s.commit()`, so session closes without persisting changes.
- **Exact location**:
  - `app/eqms/modules/customer_profiles/admin.py`
    - `customers_new_post`
    - `customer_update_post`
    - `customer_note_add`
    - `customer_note_edit`
    - `customer_note_delete`
- **Minimal fix approach**:
  - Add `s.commit()` after successful create/update/note add/edit/delete.
  - On exception paths, call `s.rollback()` before redirecting/flashing.
  - Ensure audit events are committed in the same transaction.
- **Risk**: Low/Medium — changes transaction boundaries; may expose validation errors earlier.
- **Acceptance test**:
  - Create “Test Hospital A”, refresh list, confirm it persists.
  - Edit customer with reason, refresh detail, confirm changes persist.
  - Add/edit/delete note; confirm note list updates after refresh.
  - Confirm `audit_events` includes `customer.create`, `customer.update`, `customer_note.*`.

### Fix 2 — Distribution Log customer linking can silently mis-link / not overwrite facility fields

- **Severity**: Critical
- **Symptom**: Creating a distribution entry with `customer_id` can store `customer_id` that does not exist (or later points to a different customer), and `facility_name` can remain inconsistent.
- **Root-cause hypothesis**: In `distribution_log_new_post` and `distribution_log_edit_post`, customer lookup is best-effort; if `customer_id` does not resolve, the handler continues and writes the row anyway.
- **Exact location**:
  - `app/eqms/modules/rep_traceability/admin.py`
    - `distribution_log_new_post`
    - `distribution_log_edit_post`
  - (Optional hardening) `app/eqms/modules/rep_traceability/service.py::validate_distribution_payload`
- **Minimal fix approach**:
  - If `customer_id` is provided but lookup returns `None`, flash “Selected customer not found” and redirect back (do not create/update).
  - If customer exists, always override `facility_name` (and optionally city/state/zip) from customer record for consistency.
  - Optionally validate FK existence at service layer.
- **Risk**: Medium — could block entries where users previously typed arbitrary `customer_id`.
- **Acceptance test**:
  - Create a valid customer, create a distribution entry selecting it; confirm `facility_name` matches customer.
  - Submit an invalid `customer_id`; confirm the entry is not created and user sees an error.

### Fix 3 — Add minimal Audit Trail UI (required feature)

- **Severity**: High
- **Symptom**: Admin cannot review audit events in the UI; `/admin/audit` is 404.
- **Root-cause hypothesis**: Audit model exists and is written to, but no route/template is implemented.
- **Exact location**:
  - Add route in `app/eqms/admin.py` (or a small new blueprint file under `app/eqms/`).
  - Add template `app/eqms/templates/admin/audit/list.html`
  - Model: `app/eqms/models.py::AuditEvent`
- **Minimal fix approach**:
  - Implement `GET /admin/audit` behind `@require_permission("admin.view")`.
  - Query last 200 `AuditEvent` rows ordered by `created_at desc`.
  - Add basic filters via query params: `action`, `actor_email`, `date_from`, `date_to`.
  - Display: created_at, actor_email, action, entity_type/entity_id, reason, request_id (and optionally metadata_json truncated).
- **Risk**: Low — read-only view.
- **Acceptance test**:
  - Navigate to `/admin/audit` as Admin and verify list loads.
  - Perform an action (e.g., generate tracing report) and confirm a new audit row appears.

### Fix 4 — RBAC unauthenticated behavior should redirect to login (not 403)

- **Severity**: High
- **Symptom**: After logout (or with expired session), visiting `/admin/*` returns 403, which is confusing; expected is redirect to login.
- **Root-cause hypothesis**: `require_permission()` aborts 403 for both “not logged in” and “logged in but unauthorized”.
- **Exact location**:
  - `app/eqms/rbac.py::require_permission`
- **Minimal fix approach**:
  - If `g.current_user is None`, redirect to `url_for("auth.login_get")` (optionally include `next=` param).
  - Keep 403 for authenticated-but-unauthorized users.
- **Risk**: Low — changes UX; may affect tests expecting 403 when logged out.
- **Acceptance test**:
  - Logout and visit `/admin/`; confirm redirect to `/auth/login`.
  - Login as a user without `admin.view`; confirm `/admin/` still 403.

### Fix 5 — Approvals `.eml` metadata display missing Date

- **Severity**: Medium
- **Symptom**: Approval list on tracing report detail shows Subject/From/To but not Date, despite date being parsed and stored.
- **Root-cause hypothesis**: Template omission.
- **Exact location**:
  - `app/eqms/templates/admin/tracing/detail.html` (approval list loop)
- **Minimal fix approach**:
  - Add conditional display of `a.email_date` (formatted) alongside subject/from/to.
- **Risk**: Low (template-only).
- **Acceptance test**:
  - Upload an `.eml` with Date header; confirm Date displays in the approvals list.

### Fix 6 — Customer detail “Recent distributions” lacks navigation to distribution entry edit

- **Severity**: Low
- **Symptom**: From customer detail, the “Recent distributions” table does not allow navigating to the linked distribution entry.
- **Root-cause hypothesis**: Template table omits an edit/view link.
- **Exact location**:
  - `app/eqms/templates/admin/customers/detail.html` (“Recent distributions” table)
- **Minimal fix approach**:
  - Add an “Edit” link per row to `/admin/distribution-log/<id>/edit`.
- **Risk**: Low.
- **Acceptance test**:
  - Open a customer with linked distributions; click Edit; confirm distribution edit page opens.

### Fix 7 — Distribution Log list should display customer name consistently when linked

- **Severity**: Low
- **Symptom**: List uses `e.facility_name` even when a linked Customer exists (can drift).
- **Root-cause hypothesis**: Template uses only entry field; export/report uses customer when available.
- **Exact location**:
  - `app/eqms/templates/admin/distribution_log/list.html`
- **Minimal fix approach**:
  - Display `e.customer.facility_name` when `e.customer` exists; fallback to `e.facility_name`.
- **Risk**: Low.
- **Acceptance test**:
  - With a linked customer, confirm list displays canonical facility name.

### Fix 8 — Provide a favicon (avoid noisy 404s)

- **Severity**: Low
- **Symptom**: `/favicon.ico` returns 404 repeatedly.
- **Root-cause hypothesis**: No favicon asset.
- **Exact location**:
  - Add `app/eqms/static/favicon.ico` (or update templates to reference an existing icon)
- **Minimal fix approach**:
  - Add a small favicon file and ensure static serving works.
- **Risk**: Low.
- **Acceptance test**:
  - `GET /favicon.ico` returns 200.

---

## 6) Bloat prevention notes

- **Duplicate helpers**: There are duplicated utility concepts between `app/eqms/modules/rep_traceability/utils.py` and `.../service.py` (e.g., month bounds / hash helpers and subject sanitization exist in both places). Prevent drift by keeping the canonical helper in `utils.py` and importing it in `service.py`.
- **Templates doing too much logic**: Currently acceptable; however, keep conditional presentation (e.g., choosing customer facility name) small and avoid adding more aggregation logic in Jinja.
- **Repeated queries**: Sales dashboard computes lifetime rows by loading all entries into memory. Keep it for P0/P1, but if data grows, consider small SQL-level distinct counts per customer key (still lean).

---

## 7) Appendix

### URLs tested

- `/health`
- `/auth/login` (POST)
- `/auth/logout`
- `/admin/`
- `/admin/customers/new`
- `/admin/distribution-log/new`
- `/admin/distribution-log/import-csv`
- `/admin/tracing/generate`
- `/admin/tracing/<id>/download`
- `/admin/tracing/<id>/approvals/upload`
- `/admin/approvals/<id>/download`
- `/admin/sales-dashboard`
- `/admin/sales-dashboard/export`
- `/admin/audit` (expected missing → 404)

### Sample CSV used (if any)

Filename: `qa_import.csv`

Rows (2 identical rows to validate dedupe):
- Ship Date = today
- Order Number = `QA-ORDER-CSV-001`
- Facility Name = `Test Hospital B`
- SKU = `211610SPT`
- Lot = `SLQ-54321`
- Quantity = `1`

### Any relevant log snippets (short)

- Local runtime (older running process) observed:
  - `BuildError: Could not build url for endpoint 'rep_traceability.distribution_log_list'` causing `/admin/` to 500 when logged in.

### How to test (must do these exact actions)

Using Admin user:

1. Login
2. Create customer “Test Hospital A”
3. Create distribution entry linked to that customer
4. Import a CSV that creates/links a second customer
5. Generate tracing report for the month and download CSV
6. Upload .eml approval to that report and download it
7. Open sales dashboard and export CSV
8. Confirm audit events were created (either via UI if exists or via DB read)

