# SilqQMS System Audit — March 2026

**Audit Date:** 2026-03-10  
**Auditor:** AI Agent (comprehensive codebase audit)  
**Scope:** Full application audit — bugs, inconsistencies, UX issues, missing features, dead code, security, deployment, and test coverage.  
**Codebase Snapshot:** All files under `app/eqms/`, `scripts/`, `tests/`, `migrations/`, `Dockerfile`, `requirements.txt`

---

## Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 5 |
| 🟠 High | 12 |
| 🟡 Medium | 18 |
| 🔵 Low | 13 |
| **Total** | **48** |

---

## Findings

---

### F-001 · `DistributionLogEntry.rep_id` FK Points to `users` Instead of `reps`

**Severity:** 🔴 Critical  
**Category:** Data Integrity / Schema Bug  
**Affected Files:** `app/eqms/modules/rep_traceability/models.py` (line 203)

**Description:**  
`DistributionLogEntry.rep_id` is declared as `ForeignKey("users.id")`, but `SalesOrder.rep_id` (line 51) correctly references `ForeignKey("reps.id")`. The `Rep` model (in `customer_profiles/models.py`) is a separate entity from `User` — reps do NOT log in. This means distribution log entries that store a `rep_id` are linking to the wrong table. Queries that join on `rep_id` expecting a `Rep` object will get a `User` instead, causing silent data corruption or misattribution.

**Recommended Fix:**  
Change `DistributionLogEntry.rep_id` FK target from `users.id` to `reps.id`. Create a migration to update any existing rows that reference `users.id` values, mapping them to the correct `reps.id` values where possible.

---

### F-002 · `datetime.utcnow()` Deprecated — Used Pervasively as Column Default

**Severity:** 🔴 Critical  
**Category:** Correctness / Deprecation  
**Affected Files:** `app/eqms/models.py`, `modules/rep_traceability/models.py`, `modules/customer_profiles/models.py`, `modules/equipment/models.py`, `modules/suppliers/models.py`, `modules/supplies/models.py`, `modules/purchasing/models.py`, `modules/manufacturing/models.py`, `modules/document_control/models.py`, `modules/admin_docs/models.py`, `app/eqms/auth.py`, and ~15 service files

**Description:**  
`datetime.utcnow()` is deprecated as of Python 3.12 (the runtime version per the Dockerfile). It returns a naive datetime that does not carry timezone information, which can cause subtle bugs when comparing with timezone-aware datetimes. It is used in:
- **All model `created_at`/`updated_at` column defaults** (as `default=datetime.utcnow` — note: without parentheses, this is a callable default, which is correct usage, but the function itself is deprecated).
- **Explicit calls** in `auth.py` rate limiting (`_check_rate_limit`, `_record_attempt`).
- **Explicit calls** in ~15 service/admin files for manual `updated_at` assignment.

**Recommended Fix:**  
Replace all usages with `datetime.now(timezone.utc)` (from `datetime import datetime, timezone`). For SQLAlchemy column defaults, use `default=lambda: datetime.now(timezone.utc)` or define a helper function. Consider using `DateTime(timezone=True)` columns for full timezone awareness.

---

### F-003 · In-Memory Rate Limiting Ineffective with Multiple Gunicorn Workers

**Severity:** 🔴 Critical  
**Category:** Security  
**Affected Files:** `app/eqms/auth.py` (lines 15–28)

**Description:**  
Login rate limiting uses a module-level `defaultdict` (`_login_attempts`) to track attempts per IP. The Dockerfile and `scripts/start.py` both configure `--workers 2`. Each gunicorn worker is a separate process with its own memory space, so the rate limit counter is not shared. An attacker can distribute brute-force attempts across workers, effectively doubling (or more) the allowed attempts before being blocked.

**Recommended Fix:**  
Move rate limiting to a shared store (database table or Redis). Alternatively, use a reverse proxy (nginx, Cloudflare) for rate limiting. As a minimal fix, use `--preload` with a shared multiprocessing data structure, though this is fragile.

---

### F-004 · No `updated_at` Auto-Update — Manual Assignment Required

**Severity:** 🔴 Critical  
**Category:** Data Integrity  
**Affected Files:** All model files with `updated_at` columns

**Description:**  
No model uses SQLAlchemy's `onupdate` parameter for `updated_at` columns. Every update requires explicit `obj.updated_at = datetime.utcnow()` in the route/service handler. A grep shows ~30 explicit assignments, but any route that modifies an object and forgets to set `updated_at` will leave stale timestamps. This is especially risky for maintenance operations (merge, bulk import, status changes) where it's easy to forget.

**Recommended Fix:**  
Add `onupdate=datetime.utcnow` (or the timezone-aware equivalent per F-002) to all `updated_at` column definitions. This ensures automatic updates on any `UPDATE` statement.

---

### F-005 · Logout via GET — CSRF-Susceptible

**Severity:** 🔴 Critical  
**Category:** Security  
**Affected Files:** `app/eqms/auth.py` (lines 110–118)

**Description:**  
The logout endpoint (`/auth/logout`) uses `@bp.get`, meaning any page can trigger logout via an `<img>` tag or link without user consent. The CSRF guard in `__init__.py` explicitly skips validation for `auth.*` endpoints (line 70). While logout CSRF is lower severity than data-modifying CSRF, it is still a nuisance attack vector that can disrupt sessions.

**Recommended Fix:**  
Change logout to a POST request with CSRF validation. Add a small form with a submit button in the nav template instead of a plain link.

---

### F-006 · Missing 404 Error Template

**Severity:** 🟠 High  
**Category:** UX / Error Handling  
**Affected Files:** `app/eqms/templates/errors/` (only has `400.html`, `403.html`, `500.html`, `schema_out_of_date.html`)

**Description:**  
There is no `404.html` template and no `@app.errorhandler(404)` registered in `__init__.py`. Flask will render its default ugly HTML 404 page, which is inconsistent with the application's design system and provides no navigation back to the app.

**Recommended Fix:**  
Create `templates/errors/404.html` extending `_layout.html` and register a `@app.errorhandler(404)` handler in `create_app()`.

---

### F-007 · `requirements.txt` Has No Pinned Versions

**Severity:** 🟠 High  
**Category:** Deployment / Reproducibility  
**Affected Files:** `requirements.txt`

**Description:**  
All 14 dependencies are listed without version constraints (e.g., `Flask`, `SQLAlchemy`, `boto3`). Any `pip install` will grab the latest version, which can introduce breaking changes. Flask 3.x, SQLAlchemy 2.x, and other packages have had breaking API changes between major versions. This makes builds non-reproducible and susceptible to supply chain issues.

**Recommended Fix:**  
Pin all dependencies to specific versions (e.g., `Flask==3.1.0`). Use `pip freeze > requirements.txt` on a known-good environment. Consider adding a `requirements-dev.txt` for test-only dependencies (`pytest`).

---

### F-008 · `pytest` in Production `requirements.txt`

**Severity:** 🟠 High  
**Category:** Deployment  
**Affected Files:** `requirements.txt` (line 7)

**Description:**  
`pytest` is included in the production requirements file and will be installed in the Docker image. This increases image size and attack surface unnecessarily. Test dependencies should be separated from production dependencies.

**Recommended Fix:**  
Move `pytest` to a separate `requirements-dev.txt` or `requirements-test.txt`. Adjust the `Dockerfile` to only install production dependencies.

---

### F-009 · Potential XSS via `|safe` Filter in Document Viewer

**Severity:** 🟠 High  
**Category:** Security  
**Affected Files:** `app/eqms/templates/admin/document_viewer.html` (line 28)

**Description:**  
The document viewer template renders mammoth-converted DOCX HTML using `{{ rendered_html|safe }}`. If a user uploads a malicious `.docx` file containing embedded JavaScript (e.g., via SVG or event handlers), mammoth may pass it through to the HTML output, which would then execute in the context of the authenticated user's session.

**Recommended Fix:**  
Sanitize the `rendered_html` output from mammoth using a library like `bleach` or `nh3` before passing it to the template. Strip all `<script>` tags, event handler attributes (`onclick`, `onerror`, etc.), and `<iframe>`/`<object>` elements.

---

### F-010 · S3Storage Creates a New `boto3.client` on Every Operation

**Severity:** 🟠 High  
**Category:** Performance  
**Affected Files:** `app/eqms/storage.py` (lines 76–87)

**Description:**  
`S3Storage._client()` creates a new `boto3.client("s3", ...)` on every call to `put_bytes`, `open`, `exists`, or `delete`. `boto3` client creation involves parsing configs, setting up retry logic, and establishing connection pools. This is unnecessarily expensive for high-frequency file operations (e.g., bulk PDF import with hundreds of pages).

**Recommended Fix:**  
Cache the `boto3.client` instance on the `S3Storage` dataclass (using `__post_init__` or a lazy property). Since `S3Storage` is a frozen dataclass, use `object.__setattr__` in a `@property` or convert to a regular class.

---

### F-011 · CSRF Bypass for All Auth Endpoints

**Severity:** 🟠 High  
**Category:** Security  
**Affected Files:** `app/eqms/__init__.py` (lines 69–71)

**Description:**  
The CSRF guard exempts all endpoints whose `request.endpoint` starts with `"auth."`. Currently this is only `login_get`, `login_post`, and `logout`. However, if any new endpoints are added to the `auth` blueprint (e.g., password change, 2FA setup, API tokens), they will automatically be CSRF-exempt. This is a footgun.

**Recommended Fix:**  
Explicitly exempt only `auth.login_post` (and optionally `auth.login_get`). All other auth endpoints should require CSRF validation.

---

### F-012 · Default `SECRET_KEY` is `"change-me"` in Development

**Severity:** 🟠 High  
**Category:** Security  
**Affected Files:** `app/eqms/config.py` (line 26)

**Description:**  
The default `SECRET_KEY` when `SECRET_KEY` env var is not set is `"change-me"`. While there is a production guardrail in `__init__.py` that rejects this value when `ENV` is `prod`/`production`, any non-production environment (staging, QA, demo) will use this predictable key. Session cookies signed with this key can be forged by anyone.

**Recommended Fix:**  
Generate a random key at startup when none is provided (for development only) and log a warning. Reject `"change-me"` in any non-development environment, not just production.

---

### F-013 · `teardown_db_session` Closes but Does Not Rollback

**Severity:** 🟠 High  
**Category:** Data Integrity  
**Affected Files:** `app/eqms/db.py` (lines 59–66)

**Description:**  
`teardown_db_session` only calls `s.close()` without first rolling back. If a request handler raises an exception after modifying objects but before calling `s.commit()`, the session may have flushed dirty objects. While `close()` on a non-committed session does eventually discard changes, the behavior depends on the SQLAlchemy session state and connection pool. An explicit `s.rollback()` before `s.close()` is safer.

**Recommended Fix:**  
Add `s.rollback()` before `s.close()` in `teardown_db_session`, or at minimum when `_exc` is not `None`.

---

### F-014 · `selectin` Eager Loading on All Relationships Causes N+1 Inversions

**Severity:** 🟠 High  
**Category:** Performance  
**Affected Files:** All model files (54 total `lazy="selectin"` declarations)

**Description:**  
Nearly every relationship in the application uses `lazy="selectin"`, which eagerly loads related objects in a second query whenever the parent is loaded. This is appropriate when the related objects are almost always needed, but many relationships (e.g., `SalesOrder.distributions`, `SalesOrder.pdf_attachments`, `DistributionLogEntry.lines`, `Customer.notes`, `Customer.reps`) are loaded even on list pages where only summary data is needed. For list pages with 50+ rows, this generates hundreds of extra queries.

**Recommended Fix:**  
Use `lazy="select"` (default lazy loading) for relationships not needed on list pages, and use `joinedload()` or `selectinload()` query options explicitly where eager loading is needed. Profile key list pages to identify the worst offenders.

---

### F-015 · Admin Password Seeded as `"change-me"` with No Enforcement

**Severity:** 🟠 High  
**Category:** Security  
**Affected Files:** `scripts/init_db.py` (line 22)

**Description:**  
The seed script defaults `ADMIN_PASSWORD` to `"change-me"` if the env var is not set. While the script notes this is idempotent and won't overwrite existing passwords, the initial deployment will have a predictable admin password. There is no forced password change mechanism, and the password meets the 8-character minimum check (it's 9 characters).

**Recommended Fix:**  
Require `ADMIN_PASSWORD` env var to be set explicitly (fail the seed if not present). Add a "must change password on first login" flag, or generate a random password and print it to logs.

---

### F-016 · Confirmation Token for Customer Merge is Predictable MD5

**Severity:** 🟠 High  
**Category:** Security  
**Affected Files:** `app/eqms/admin.py` (lines 470–476)

**Description:**  
The customer merge endpoint uses `md5(f"{master_id}:{duplicate_id}:CONFIRM")[:8]` as a confirmation token. This is a deterministic function of public IDs — any user with admin access who knows the master and duplicate IDs can compute the token. It provides no real protection against accidental or malicious merges beyond a second API call.

**Recommended Fix:**  
Use a cryptographically random token stored in the session or database with a TTL. The confirmation flow should require the user to acknowledge specific details (customer names, order counts) before proceeding.

---

### F-017 · `.doc` (Legacy Word) Files: `needs_server_render` Returns True but Rendering Returns None

**Severity:** 🟡 Medium  
**Category:** UX / Bug  
**Affected Files:** `app/eqms/document_viewer.py` (lines 24–52)

**Description:**  
`needs_server_render()` returns `True` for `.doc` files, but `render_document_to_response()` returns `None` for `.doc` because mammoth doesn't support legacy Word format. The comment on line 51 acknowledges this: "fall through to download". However, view routes that check `needs_server_render()` may attempt server-side rendering, get `None`, and then either show an error or silently redirect. The user experience is confusing — the "View" button appears but doesn't work for `.doc` files.

**Recommended Fix:**  
Either exclude `.doc` from `needs_server_render()` or add a user-facing message explaining that `.doc` files cannot be previewed and must be downloaded.

---

### F-018 · No Pagination on Several Key List Endpoints

**Severity:** 🟡 Medium  
**Category:** Performance / UX  
**Affected Files:** `app/eqms/modules/nre_projects/admin.py`, `app/eqms/modules/customer_profiles/admin.py` (customer detail — orders list), `app/eqms/admin.py` (audit log)

**Description:**  
Several list pages load all records without pagination:
- NRE Projects dashboard loads all unmatched customers and their orders.
- Customer detail page loads all associated sales orders and distribution entries.
- The audit log page has pagination but loads up to 200 events per page with no total count indicator.

As data grows (thousands of orders/customers), these pages will become slow or unresponsive.

**Recommended Fix:**  
Add standard pagination (page number + page size) to all list endpoints. The distribution log and equipment list already implement pagination well and can serve as templates.

---

### F-019 · `DistributionLogEntry` Has Both `sku`/`lot_number`/`quantity` and `DistributionLine` Children

**Severity:** 🟡 Medium  
**Category:** Data Integrity / Design  
**Affected Files:** `app/eqms/modules/rep_traceability/models.py` (lines 168–244)

**Description:**  
`DistributionLogEntry` has top-level `sku`, `lot_number`, and `quantity` columns AND a `lines` relationship to `DistributionLine` objects that also have `sku`, `lot_number`, and `quantity`. This dual representation creates ambiguity: which is the source of truth? Some code reads from the entry-level fields (CSV export, manual entry), while ShipStation sync creates both entry-level and line-level records. If they diverge, aggregation queries will produce different results depending on which source they read.

**Recommended Fix:**  
Choose one canonical source of truth. If `DistributionLine` is the correct granular representation, deprecate the entry-level `sku`/`lot_number`/`quantity` columns and migrate all reads to aggregate from `lines`. If the entry-level fields are authoritative, document when `lines` should be used and ensure they stay in sync.

---

### F-020 · `customer_name` Deprecated but Still Written and Read

**Severity:** 🟡 Medium  
**Category:** Technical Debt  
**Affected Files:** `app/eqms/modules/rep_traceability/models.py` (line 209–211), `modules/rep_traceability/service.py`, `modules/rep_traceability/admin.py`

**Description:**  
`DistributionLogEntry.customer_name` is annotated with a comment: "deprecated; prefer customer_id -> Customer.facility_name". However, it is still written to on every create/update, and some templates read from it. This creates confusion about which field to trust and adds maintenance burden.

**Recommended Fix:**  
Formally deprecate: stop writing to `customer_name` in new code paths, migrate reads to `customer.facility_name`, and eventually drop the column. Alternatively, keep it as a denormalized cache but document it clearly.

---

### F-021 · `DistributionLine` SKU CHECK Constraint is Hardcoded

**Severity:** 🟡 Medium  
**Category:** Maintainability  
**Affected Files:** `app/eqms/modules/rep_traceability/models.py` (lines 143–145)

**Description:**  
The `ck_distribution_lines_sku` CHECK constraint hardcodes the valid SKU list: `"sku IN ('211810SPT','211610SPT','211410SPT')"`. The same constraint exists on `DistributionLogEntry` (line 172). If new products are added, both the `VALID_SKUS` constant in `constants.py` and multiple CHECK constraints in the database must be updated via migration. This is error-prone.

**Recommended Fix:**  
Consider removing the database-level CHECK constraints and relying on application-level validation (which already exists in `utils.py/is_valid_sku`). Alternatively, create a `valid_skus` reference table and use a FK constraint.

---

### F-022 · No File Type Validation on Uploads — Only Extension Checked

**Severity:** 🟡 Medium  
**Category:** Security  
**Affected Files:** Multiple admin modules (equipment, suppliers, supplies, manufacturing, purchasing, admin_docs)

**Description:**  
File uploads check the file extension (via `secure_filename`) but do not validate the actual file content (magic bytes / MIME type). An attacker could upload a malicious file with a `.pdf` extension that is actually an executable or HTML file with embedded JavaScript.

**Recommended Fix:**  
Add server-side MIME type validation using `python-magic` or similar library. Verify that the file's magic bytes match the expected type for the given extension.

---

### F-023 · Missing Test Coverage for Major Modules

**Severity:** 🟡 Medium  
**Category:** Quality / Testing  
**Affected Files:** `tests/` directory

**Description:**  
The test suite has 7 test files covering: smoke, customer keys, document control, equipment, manufacturing, rep traceability, and suppliers. Missing test coverage for:
- **Purchasing** module (no `test_purchasing.py`)
- **Supplies** module (no `test_supplies.py`)
- **NRE Projects** module (no `test_nre_projects.py`)
- **Admin Docs** module (no `test_admin_docs.py`)
- **ShipStation Sync** (no `test_shipstation_sync.py`)
- **Customer Profiles** CRUD (no `test_customer_profiles.py` — only key functions tested)
- **RBAC/Auth** edge cases (rate limiting, permission checks, CSRF)
- **Storage** (no `test_storage.py` — S3 integration)

**Recommended Fix:**  
Add test files for each untested module. Prioritize ShipStation sync (most complex integration), purchasing (financial data), and RBAC edge cases.

---

### F-024 · `os.register_at_fork` Not Available on Windows

**Severity:** 🟡 Medium  
**Category:** Compatibility  
**Affected Files:** `app/eqms/__init__.py` (lines 94–104)

**Description:**  
The `_dispose_engine_on_fork` function uses `os.register_at_fork`, which only exists on Unix systems. The code correctly guards with `hasattr(os, "register_at_fork")`, but the function name and logging imply it's expected to work. On Windows development environments, the engine will never be disposed after forking (which doesn't happen on Windows anyway, since gunicorn doesn't support Windows). This is a minor issue but could confuse developers.

**Recommended Fix:**  
Add a log message when `register_at_fork` is not available, or remove the function entirely since gunicorn (the production server) runs on Linux.

---

### F-025 · Hardcoded Start Date `"2025-01-01"` in Sales Dashboard and Reports

**Severity:** 🟡 Medium  
**Category:** UX / Hardcoded Value  
**Affected Files:** `app/eqms/modules/rep_traceability/admin.py` (lines 1450, 1640)

**Description:**  
The sales dashboard and export endpoints default to `start_date = "2025-01-01"` when no filter is provided. As time progresses into 2026 and beyond, this will load increasingly large datasets by default, impacting performance. It also means the default view shows over a year of data, which may not be what users expect.

**Recommended Fix:**  
Default to a rolling window (e.g., last 12 months, or current calendar year) instead of a hardcoded date.

---

### F-026 · `ShipStation since_date` Defaults to Current Year Start

**Severity:** 🟡 Medium  
**Category:** Configuration  
**Affected Files:** `app/eqms/modules/shipstation_sync/admin.py` (lines 73–78), `modules/shipstation_sync/service.py` (lines 160–170)

**Description:**  
When `SHIPSTATION_SINCE_DATE` is not set, the sync defaults to January 1st of the current year. The service file (line 170) has a different fallback: `datetime(2025, 1, 1, tzinfo=timezone.utc)`. These two defaults are inconsistent and could cause the sync to pull different date ranges depending on which code path is executed.

**Recommended Fix:**  
Unify the default date logic in one place. Document the expected behavior clearly.

---

### F-027 · Multiple `before_request` Handlers — Execution Order Fragile

**Severity:** 🟡 Medium  
**Category:** Architecture  
**Affected Files:** `app/eqms/__init__.py`

**Description:**  
`create_app()` registers four `before_request` handlers:
1. `_csrf_guard` (line 62)
2. `_load_user_wrapper` (line 147)
3. `_schema_health_guardrail` (line 204)
Plus Flask's built-in handlers.

The order depends on registration order, but `_csrf_guard` runs before `_load_user_wrapper`, which means `g.current_user` is not yet set when CSRF validation runs. This is currently fine because CSRF doesn't need the user, but it's fragile. If any future CSRF logic needs user context, it will fail.

**Recommended Fix:**  
Document the intended execution order. Consider consolidating into a single `before_request` handler that calls sub-functions in the correct order.

---

### F-028 · `SalesOrder.updated_at` Not Set on onupdate — Must Be Manual

**Severity:** 🟡 Medium  
**Category:** Data Integrity  
**Affected Files:** `app/eqms/modules/rep_traceability/models.py` (line 60), `modules/shipstation_sync/service.py` (line 77)

**Description:**  
`SalesOrder.updated_at` has `default=datetime.utcnow` but no `onupdate`. The ShipStation sync service (line 77) manually sets `existing.updated_at = datetime.utcnow()` when updating an existing order, but other code paths that modify sales orders (admin edit, PDF import) may forget to update this field. Same issue applies to all models (see F-004), but sales orders are particularly important as source-of-truth records.

**Recommended Fix:**  
See F-004. As a priority, ensure all `SalesOrder` update paths set `updated_at`.

---

### F-029 · Bulk PDF Import Has No Idempotency — Re-import Creates Duplicates

**Severity:** 🟡 Medium  
**Category:** Data Integrity  
**Affected Files:** `app/eqms/modules/rep_traceability/admin.py` (bulk import routes)

**Description:**  
The bulk PDF import for sales orders and shipping labels splits PDFs into pages and creates new records for each page. If the same PDF is imported twice, it will create duplicate sales orders and distribution entries. There is no deduplication based on file hash or content.

**Recommended Fix:**  
Store the SHA-256 hash of each imported PDF page and check for duplicates before creating new records. Skip pages whose hash already exists in the database.

---

### F-030 · `notes` Modal AJAX Endpoint Has No Error Response Body

**Severity:** 🟡 Medium  
**Category:** UX  
**Affected Files:** `app/eqms/templates/_layout.html` (lines 115–127)

**Description:**  
The notes modal's `fetch('/admin/notes/create', ...)` call checks `resp.ok` but on failure only shows `alert('Failed to save note.')`. The server's error response body is not shown to the user, making it hard to diagnose why a note failed to save (validation error, permission issue, DB error, etc.).

**Recommended Fix:**  
Parse the error response body and display the specific error message in the modal UI, not a generic alert.

---

### F-031 · Migration Chain Has Multiple Merge Heads

**Severity:** 🟡 Medium  
**Category:** Database / Migrations  
**Affected Files:** `migrations/versions/` (3 merge migrations: `b7c8d9e0f1a2`, `d1e2f3a4b5c6`, `g1h2i3j4k5l6`)

**Description:**  
The migration history has three separate merge-head migrations, indicating the migration chain was branched and merged multiple times. While this is functional, it makes the migration history harder to reason about and increases the risk of conflicts in future migrations. Some migration filenames use non-hex revision IDs (e.g., `g1h2i3j4k5l6`, `h2i3j4k5l6m`, `i3j4k5l6m7`, `j4k5l6m7n8`, `k1l2m3n4o5`) which appear to be manually crafted rather than auto-generated by Alembic.

**Recommended Fix:**  
Consider squashing migrations into a single baseline migration for the next major release. Ensure all future migrations are generated via `alembic revision --autogenerate` to avoid manual ID collisions.

---

### F-032 · `.doc` Listed in `needs_server_render` but Cannot Be Rendered

**Severity:** 🟡 Medium  
**Category:** UX  
**Affected Files:** `app/eqms/document_viewer.py` (line 27), `app/eqms/utils.py` (line 47)

**Description:**  
Both `needs_server_render()` and `allow_inline_view()` list `.doc` as a type that needs server rendering / should not be viewed inline. However, the actual rendering logic returns `None` for `.doc` files. This means `.doc` files will fail to render inline silently, and the view button may appear but not work correctly depending on the calling route's fallback behavior.

**Recommended Fix:**  
Separate `.doc` handling: either exclude it from `needs_server_render()` (and allow download only), or add a clear error message explaining that legacy `.doc` format is not supported for preview.

---

### F-033 · Schema Health Check Only Validates a Subset of Tables/Columns

**Severity:** 🟡 Medium  
**Category:** Deployment  
**Affected Files:** `app/eqms/__init__.py` (lines 155–201)

**Description:**  
The schema health check only verifies a few specific columns (`distribution_log_entries.external_key`, `tracing_reports.generated_by_user_id`, etc.) and tables (`sales_orders`, `sales_order_lines`). It does not check newer tables like `admin_doc_folders`, `admin_doc_files`, `supplies`, `supply_suppliers`, `purchase_orders`, `purchase_order_lines`, or `manufacturing_lots`. If these tables are missing after a failed migration, the app will start but crash when those modules are accessed.

**Recommended Fix:**  
Extend the health check to validate all tables that the application expects, or iterate over `Base.metadata.tables` and check each against the database inspector.

---

### F-034 · No Input Length Validation on Text Fields

**Severity:** 🔵 Low  
**Category:** Data Integrity  
**Affected Files:** Multiple admin routes across all modules

**Description:**  
Most form handlers use `(request.form.get("field") or "").strip()` without checking maximum length. Database columns use `Text` type (unlimited length in Postgres) for fields like `facility_name`, `order_number`, `tracking_number`, etc. A malicious or accidental submission with extremely long values could cause storage bloat or UI rendering issues.

**Recommended Fix:**  
Add `maxlength` attributes to HTML input fields and server-side length validation in form handlers. Consider using `String(N)` column types with appropriate limits instead of `Text` for fields with known maximum lengths.

---

### F-035 · No Content Security Policy (CSP) Headers

**Severity:** 🔵 Low  
**Category:** Security  
**Affected Files:** `app/eqms/__init__.py`

**Description:**  
The application does not set any `Content-Security-Policy` headers. Combined with the `|safe` filter usage in the document viewer (F-009), this means there is no defense-in-depth against XSS. A CSP header could prevent execution of inline scripts even if XSS is injected.

**Recommended Fix:**  
Add a `Content-Security-Policy` header via `@app.after_request`. Start with a report-only policy to identify violations, then enforce. At minimum: `default-src 'self'; script-src 'self' 'unsafe-inline'` (noting the inline scripts in `_layout.html` require `'unsafe-inline'` or nonces).

---

### F-036 · No `@app.errorhandler(405)` for Method Not Allowed

**Severity:** 🔵 Low  
**Category:** UX  
**Affected Files:** `app/eqms/__init__.py`

**Description:**  
There is no custom handler for HTTP 405 (Method Not Allowed). If a user submits a GET request to a POST-only endpoint (e.g., by refreshing a form submission), they will see Flask's default error page.

**Recommended Fix:**  
Add a `@app.errorhandler(405)` that renders a user-friendly error template.

---

### F-037 · Loose Files in Repository Root

**Severity:** 🔵 Low  
**Category:** Housekeeping  
**Affected Files:** Repository root

**Description:**  
The repository root contains numerous loose files that appear to be raw data or test documents:
- `2025 Sales Orders.pdf`
- `SO_Sales Order February.pdf`
- `SO_Sales Order February.pdf_page_10.pdf`
- `SO_SalesOrder2_January 2026.pdf`
- `Packing Slips.pdf`
- `SAS TCI.pdf`
- `SILQ Approved Supplier List Feb 2025.docx`
- `Silq Equipment Master List.xlsx`
- `SILQ Training Matrix.xlsx`
- `Equipment Requirements Form, Equip ID ST-012 - Weighing Scale.pdf`
- `MP-C.SLQ001 B Manufacturing Procedure. Suspension Processing.docx`

These should not be in the application repository. They increase clone/build size, may contain sensitive data, and clutter the project structure.

**Recommended Fix:**  
Move these files to the `storage/` directory or a separate data repository. Add them to `.gitignore`. If they are test fixtures, move them to `tests/fixtures/`.

---

### F-038 · `Audits/`, `EmployeeTraining/`, `Manufacturing/`, etc. in Repo Root

**Severity:** 🔵 Low  
**Category:** Housekeeping  
**Affected Files:** Repository root directories: `Audits/`, `EmployeeTraining/`, `Equipment/`, `ManagementReviewMeetings/`, `NCMR/`, `PostMarketSurviellance/`, `Purchasing/`, `QM Documents/`, `RegulatoryStandards/`, `RiskManagement/`, `Suppliers/`, `Supplies/`

**Description:**  
The repository root contains many directories that appear to be QMS document archives (audit reports, training records, regulatory documents, etc.). These are operational/business documents, not application code. Including them in the code repository:
- Massively increases repository size
- Creates merge conflicts when documents are updated
- Mixes application code with business data
- May expose sensitive compliance documents to anyone with repo access

**Recommended Fix:**  
Move these directories to the admin docs library (which is already built for this purpose) or an external document management system. Add them to `.gitignore`.

---

### F-039 · `PostMarketSurviellance` Directory Name is Misspelled

**Severity:** 🔵 Low  
**Category:** Housekeeping  
**Affected Files:** `PostMarketSurviellance/` (should be `PostMarketSurveillance`)

**Description:**  
The directory name `PostMarketSurviellance` is misspelled (should be "Surveillance"). If any code or documentation references this path, it may cause confusion.

**Recommended Fix:**  
Rename to `PostMarketSurveillance` (or remove from repo per F-038).

---

### F-040 · `_login_attempts` Dict Grows Unbounded

**Severity:** 🔵 Low  
**Category:** Memory Leak  
**Affected Files:** `app/eqms/auth.py` (lines 15–28)

**Description:**  
The `_login_attempts` dictionary stores timestamps per IP address and only prunes entries within the 5-minute window when `_check_rate_limit` is called for that specific IP. If many unique IPs make login attempts over time, their entries will persist in memory indefinitely (even after the 5-minute window) until that specific IP makes another attempt.

**Recommended Fix:**  
Add periodic cleanup (e.g., in `_check_rate_limit`, prune all IPs with no recent attempts) or use a TTL-based cache like `cachetools.TTLCache`.

---

### F-041 · No Audit Logging for Supplier, Supply, or Equipment Delete Operations

**Severity:** 🔵 Low  
**Category:** Compliance / Audit Trail  
**Affected Files:** `app/eqms/modules/equipment/admin.py`, `modules/suppliers/admin.py`, `modules/supplies/admin.py`

**Description:**  
While most create/update operations are logged via `record_event`, delete operations for supplier associations, equipment documents, and supply documents log the deletion but some paths may miss the audit event. For a QMS application where audit trail completeness is critical for regulatory compliance, every data modification should be logged.

**Recommended Fix:**  
Audit all delete/remove routes in equipment, suppliers, and supplies modules to ensure every destructive operation calls `record_event` before committing.

---

### F-042 · Duplicated `_current_user()` Helper Across Multiple Files

**Severity:** 🔵 Low  
**Category:** Code Quality / DRY  
**Affected Files:** `app/eqms/admin.py`, `app/eqms/modules/rep_traceability/admin.py`, `app/eqms/modules/manufacturing/admin.py` (and potentially others)

**Description:**  
The pattern `def _current_user() -> User: u = getattr(g, "current_user", None); if not u: raise RuntimeError("No current user"); return u` is duplicated in at least 3 admin files. This is a simple helper but maintaining identical copies in multiple files violates DRY and risks divergence.

**Recommended Fix:**  
Move `_current_user()` to a shared utility module (e.g., `app/eqms/rbac.py` or `app/eqms/utils.py`) and import it in all admin modules.

---

### F-043 · Test Fixtures Duplicated Across All Test Files

**Severity:** 🔵 Low  
**Category:** Code Quality / Testing  
**Affected Files:** `tests/test_smoke.py`, `tests/test_document_control.py`, `tests/test_equipment.py`, `tests/test_rep_traceability.py`, `tests/test_manufacturing.py`, `tests/test_suppliers.py`

**Description:**  
Every test file contains an almost identical `client` fixture that creates an app, sets up the database, and seeds permissions/roles/users. The only difference is which permissions are seeded. This is ~30 lines of boilerplate duplicated 6+ times.

**Recommended Fix:**  
Create a `tests/conftest.py` with shared fixtures. Use a parameterized or composable fixture that accepts permission lists.

---

### F-044 · No Request Timeout for PDF Parsing Operations

**Severity:** 🔵 Low  
**Category:** Reliability  
**Affected Files:** `app/eqms/modules/rep_traceability/parsers/pdf.py`, `modules/purchasing/parsers/pdf.py`, `modules/equipment/parsers/pdf.py`

**Description:**  
PDF parsing using `pdfplumber` and `PyPDF2` can be slow for large or malformed PDFs. There is no timeout mechanism — a single malicious/corrupt PDF upload could hang a worker thread indefinitely. The gunicorn timeout is 60 seconds, which provides some protection, but a hung worker degrades capacity for other users.

**Recommended Fix:**  
Add a timeout wrapper around PDF parsing operations using `signal.alarm` (Unix) or `concurrent.futures.ThreadPoolExecutor` with a timeout. Add file size checks before parsing (some routes already check 10MB limits, but not all).

---

### F-045 · `MANIFEST.md` Purpose Unclear — Potentially Stale

**Severity:** 🔵 Low  
**Category:** Documentation  
**Affected Files:** `MANIFEST.md`

**Description:**  
A `MANIFEST.md` file exists in the repository root. Its purpose and whether it's kept up-to-date is unclear. If it's a manual listing of files/features, it may be stale given the rapid development pace visible in the migration history.

**Recommended Fix:**  
Review `MANIFEST.md`. If it's a manual file listing, consider auto-generating it or removing it in favor of the README. If it serves a compliance purpose, ensure it's updated as part of the release process.

---

### F-046 · `SalesOrder.distributions` Uses `selectin` — Loads All Distributions on Every SO Access

**Severity:** 🔵 Low  
**Category:** Performance  
**Affected Files:** `app/eqms/modules/rep_traceability/models.py` (lines 72–76)

**Description:**  
`SalesOrder.distributions` eagerly loads all related `DistributionLogEntry` objects with `lazy="selectin"`. A single sales order can have dozens or hundreds of distribution entries. When the ShipStation sync processes hundreds of orders, each order access triggers an extra query to load all its distributions — even when the sync only needs to check for duplicates.

**Recommended Fix:**  
Change to `lazy="select"` (or `lazy="dynamic"` for query-like access) and explicitly eager-load only where needed.

---

### F-047 · No Health Check for Database Connectivity

**Severity:** 🔵 Low  
**Category:** Deployment / Monitoring  
**Affected Files:** `app/eqms/routes.py` (lines 11–23)

**Description:**  
The `/health` endpoint returns `{"ok": True}` without checking database connectivity. The `/healthz` endpoint explicitly says "No DB access, minimal overhead." While fast health checks are good for probes, there is no deep health check that verifies the database is actually accessible. If the database goes down, the health check will still report healthy.

**Recommended Fix:**  
Add a `/health/deep` or `/readyz` endpoint that performs a `SELECT 1` against the database and checks storage connectivity. Keep `/healthz` as a fast liveness probe.

---

### F-048 · `alembic.ini` May Contain Hardcoded Database URL

**Severity:** 🔵 Low  
**Category:** Security / Configuration  
**Affected Files:** `alembic.ini`

**Description:**  
The release script (`scripts/release.py`, line 62) sets `sqlalchemy.url` from the `DATABASE_URL` environment variable before running migrations. However, `alembic.ini` may contain a default `sqlalchemy.url` value (typically `sqlite:///` or a placeholder) that could be used if the env var override fails or if someone runs `alembic` directly without the release script.

**Recommended Fix:**  
Ensure `alembic.ini` contains a placeholder URL that will fail clearly (e.g., `sqlalchemy.url = driver://user:pass@localhost/dbname`). Consider using `env.py` to always read from the environment variable.

---

## Appendix: File-to-Finding Index

| File | Findings |
|------|----------|
| `app/eqms/__init__.py` | F-006, F-011, F-024, F-027, F-033, F-035, F-036 |
| `app/eqms/auth.py` | F-002, F-003, F-005, F-040 |
| `app/eqms/config.py` | F-012 |
| `app/eqms/db.py` | F-013 |
| `app/eqms/models.py` | F-002, F-004 |
| `app/eqms/storage.py` | F-010 |
| `app/eqms/document_viewer.py` | F-017, F-032 |
| `app/eqms/utils.py` | F-032 |
| `app/eqms/admin.py` | F-016, F-042 |
| `app/eqms/routes.py` | F-047 |
| `app/eqms/modules/rep_traceability/models.py` | F-001, F-002, F-004, F-019, F-020, F-021, F-028, F-046 |
| `app/eqms/modules/rep_traceability/admin.py` | F-018, F-025, F-029, F-042 |
| `app/eqms/modules/rep_traceability/parsers/pdf.py` | F-044 |
| `app/eqms/modules/customer_profiles/models.py` | F-002, F-004 |
| `app/eqms/modules/customer_profiles/admin.py` | F-018 |
| `app/eqms/modules/shipstation_sync/service.py` | F-002, F-026 |
| `app/eqms/modules/shipstation_sync/admin.py` | F-026 |
| `app/eqms/modules/equipment/models.py` | F-002, F-004 |
| `app/eqms/modules/suppliers/models.py` | F-002, F-004 |
| `app/eqms/modules/supplies/models.py` | F-002, F-004 |
| `app/eqms/modules/purchasing/models.py` | F-002, F-004 |
| `app/eqms/modules/manufacturing/models.py` | F-002, F-004 |
| `app/eqms/modules/document_control/models.py` | F-002 |
| `app/eqms/modules/admin_docs/service.py` | F-002 |
| `app/eqms/modules/nre_projects/admin.py` | F-018 |
| `app/eqms/templates/_layout.html` | F-030 |
| `app/eqms/templates/admin/document_viewer.html` | F-009 |
| `app/eqms/templates/errors/` | F-006, F-036 |
| `requirements.txt` | F-007, F-008 |
| `scripts/init_db.py` | F-015 |
| `scripts/release.py` | F-048 |
| `migrations/versions/` | F-031 |
| `tests/` | F-023, F-043 |
| Repository root | F-037, F-038, F-039, F-045 |

---

*End of audit report.*
