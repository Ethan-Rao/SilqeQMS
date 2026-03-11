# SilqQMS System Audit Findings — March 11, 2026

**Audit Date:** 2026-03-11  
**Auditor:** Claude (Comprehensive Debug & Legacy Code Audit)  
**Commit:** `0836bb1`  
**Scope:** Full file-by-file review of 68 Python files, 71 HTML templates, 27 Alembic migrations, 14 utility scripts, deployment configuration

---

## Executive Summary

SilqQMS is a maturing Flask-based Quality Management System with comprehensive coverage across quality, manufacturing, commercial, and regulatory domains. The architecture is well-structured with clean separation into 11 module blueprints, a centralized document viewer, abstract storage layer, and robust RBAC. The codebase reflects rapid development over the past month with many features added in parallel.

**Overall Health: B+** — The core application is functional and well-organized. However, the audit identified **3 Critical**, **11 High**, **18 Medium**, and **14 Low** severity findings totaling **46 issues**. The most concerning issues are: (1) two broken utility scripts that will crash on execution, (2) a missing runtime import in `suppliers/service.py` that will crash supplier document uploads, and (3) unpinned dependencies in `requirements.txt` that could break production deploys at any time.

Key risk areas: **Script reliability** (3 broken scripts), **deployment stability** (unpinned deps, hardcoded DB URL in alembic.ini), **cross-module consistency** (manufacturing module diverges from `_current_user()` pattern), and **security surface** (deep health check leaks internal errors, CSP allows unsafe-inline).

---

## Legacy Code & Dead Code Identified

### Dead Imports

| File | Import | Reason |
|------|--------|--------|
| `scripts/dedupe_customers.py:40` | `from app.eqms.modules.customer_profiles.utils import extract_email_domain` | Imported but never called in the script — only used internally by `find_merge_candidates` in `service.py` |
| `scripts/import_equipment_and_suppliers.py:17` | `import re` | Imported but never used in the file |
| `scripts/import_equipment_and_suppliers.py:29` | `from app.eqms.models import Permission, Role` | `Permission` and `Role` are imported but only `User` is used |

### Dead Routes (defined but never linked)

| Module | Route | Function | Notes |
|--------|-------|----------|-------|
| `admin.py` | `/admin/diagnostics/storage` | `diagnostics_storage` | Linked only from `diagnostics.html` — functional but no sidebar/nav link |
| `admin.py` | `/admin/debug-permissions` | `debug_permissions` | Linked only from `diagnostics.html` — functional but no sidebar/nav link |

### Orphaned Templates (never rendered)

No orphaned templates found. All 71 templates are rendered by at least one route.

### Unused Functions

| File | Function | Reason |
|------|----------|--------|
| `app/eqms/modules/rep_traceability/service.py` | `normalize_address()` (line ~17) | Only called internally within `match_distribution_to_sales_order()` — not dead but only used in one place; could be inlined |
| `app/eqms/modules/document_control/service.py` | `to_download_fileobj()` | Defined but appears unused — download routes use `storage.open()` directly |

### Obsolete Scripts

| Script | Reason |
|--------|--------|
| `scripts/cleanup_pdf_import_distributions.py` | One-time cleanup script for a now-fixed bug. The source `pdf_import` is no longer generated. Safe to archive. |
| `scripts/dedupe_customers.py` | **Broken** — uses `from app.eqms.db import Session` as a context manager, but `Session` from `app.eqms.db` is `sqlalchemy.orm.Session` (not a bound sessionmaker). Will fail at runtime. The deduplication feature is also available via the admin UI (`/admin/customers/merge`). |

### Deprecated Model Columns

| Model | Column | Reason |
|-------|--------|--------|
| `DistributionLogEntry` | `customer_name` | Redundant — replaced by `Customer` relationship via `customer_id` FK. Still written and read in service.py but the `Customer.facility_name` is the canonical source. |
| `DistributionLogEntry` | `rep_name` | Partially redundant — `Rep` model exists via `rep_id` FK. The `rep_name` field is still used as a convenience field for display. |
| `DistributionLogEntry` | `external_key` | Added via drift-fix migration but appears unused in service/admin code — no route writes or reads this field. |

---

## Findings

### Critical (Breaks functionality or causes data loss)

#### C-001: `suppliers/service.py` — Missing Runtime Import of `validate_managed_document`

- **Severity:** Critical
- **Location:** `app/eqms/modules/suppliers/service.py`, lines 16 and 213
- **Description:** `validate_managed_document` is imported under `if TYPE_CHECKING:` (line 16), which means it's only available for static type checkers, not at runtime. However, it's called at runtime on line 213 inside `upload_supplier_document()`. Unlike `ManagedDocument` which has a lazy import inside the function body, `validate_managed_document` does not.
- **Impact:** Any attempt to upload a document to a supplier will crash with `NameError: name 'validate_managed_document' is not defined`.
- **Reproduction:** Navigate to any supplier detail page → Upload a document → Server 500 error.
- **Recommended Fix:** Add `from app.eqms.utils import validate_managed_document` inside the `upload_supplier_document()` function body, alongside the existing `from app.eqms.modules.equipment.models import ManagedDocument` lazy import.
- **Files to Modify:** `app/eqms/modules/suppliers/service.py`

#### C-002: `scripts/import_equipment_and_suppliers.py` — Broken Indentation / Scope Error

- **Severity:** Critical
- **Location:** `scripts/import_equipment_and_suppliers.py`, lines 383–423
- **Description:** The `with script_session(database_url) as s:` block (line 384) exits at line 389 (the function returns inside the block). Lines 391–417 then use `s` (the session variable) outside the context manager scope. Lines 419–420 (`s.commit()` and print) have inconsistent indentation that attempts to re-enter the `with` block but is syntactically incorrect. The script will crash with `IndentationError` on execution.
- **Impact:** The equipment and supplier import script is completely non-functional. Cannot be run.
- **Reproduction:** `python scripts/import_equipment_and_suppliers.py` → `IndentationError`
- **Recommended Fix:** Restructure `main()` so that all operations (import equipment, import suppliers, link, commit) happen inside a single `with script_session(database_url) as s:` block. Also fix the early-return logic.
- **Files to Modify:** `scripts/import_equipment_and_suppliers.py`

#### C-003: `scripts/dedupe_customers.py` — Unbound SQLAlchemy Session

- **Severity:** Critical
- **Location:** `scripts/dedupe_customers.py`, line 46
- **Description:** The script does `from app.eqms.db import Session` and then `with Session() as s:`. The `Session` symbol in `db.py` is `sqlalchemy.orm.Session` (imported at module top level), NOT a configured `sessionmaker` bound to an engine. Creating `Session()` without a `bind` argument produces an unbound session that cannot execute queries.
- **Impact:** All script operations (`--list`, `--merge`, `--merge-strong`) will crash with a database error when attempting the first query.
- **Reproduction:** `python scripts/dedupe_customers.py --list` → runtime error on first query.
- **Recommended Fix:** Replace `from app.eqms.db import Session` with `from scripts._db_utils import script_session` and use `with script_session(db_url) as s:` like other scripts do. Or use `create_app()` + `app.app_context()` + `db_session()` pattern.
- **Files to Modify:** `scripts/dedupe_customers.py`

---

### High (Significant bugs or security issues)

#### H-001: `requirements.txt` — No Version Pinning

- **Severity:** High
- **Location:** `requirements.txt`
- **Description:** All 14 dependencies are listed without version pins (e.g., `Flask` instead of `Flask==3.1.0`). A new `pip install` could pull incompatible versions of any dependency, breaking the application silently.
- **Impact:** Deployments could break at any time due to upstream package changes. Particularly risky for `SQLAlchemy` (ORM changes between versions), `Flask` (API changes), and `mammoth` (rendering differences).
- **Recommended Fix:** Run `pip freeze > requirements.txt` on the current working environment to capture exact versions. Consider separating `requirements-dev.txt` for `pytest`.
- **Files to Modify:** `requirements.txt`

#### H-002: `alembic.ini` — Hardcoded SQLite Database URL

- **Severity:** High
- **Location:** `alembic.ini`, line 89
- **Description:** `sqlalchemy.url = sqlite:///eqms.db` is hardcoded in `alembic.ini`. While `migrations/env.py` overrides this with `DATABASE_URL` from the environment, if `DATABASE_URL` is accidentally unset during a migration run, Alembic would silently migrate the wrong database.
- **Impact:** Potential data loss or schema corruption if migrations run against the wrong database.
- **Recommended Fix:** Change to `sqlalchemy.url = ` (empty) or add a comment. The `env.py` already handles the override, but removing the default prevents silent fallback.
- **Files to Modify:** `alembic.ini`

#### H-003: In-Memory Rate Limiting Fails with Multiple Workers

- **Severity:** High
- **Location:** `app/eqms/auth.py`, line 14
- **Description:** `_login_attempts` is a module-level `defaultdict` storing login attempt timestamps in memory. The Dockerfile and `start.py` configure Gunicorn with `--workers 2`. Each worker has its own memory space, so an attacker can exceed the rate limit by having requests routed to different workers.
- **Impact:** Rate limiting effectiveness is halved (or worse) with multiple workers. An attacker gets 5 attempts per worker instead of 5 total.
- **Recommended Fix:** For immediate fix, reduce to `--workers 1` if acceptable. For production-grade fix, use Redis-backed rate limiting or database-backed attempt tracking. Alternatively, use Gunicorn's `--preload` (already configured) which shares the module state, but only if using threads, not pre-fork workers.
- **Files to Modify:** `app/eqms/auth.py`, `Dockerfile`, `scripts/start.py`

#### H-004: `/health/deep` Endpoint Leaks Internal Error Details

- **Severity:** High
- **Location:** `app/eqms/routes.py`, lines 44–45, 57–58
- **Description:** The deep health check returns internal error messages (`f"error: {e}"`) in the JSON response. This endpoint is unauthenticated and publicly accessible. Database connection strings, S3 bucket names, and internal stack traces could be exposed.
- **Impact:** Information disclosure to unauthenticated users. Could reveal database host, credentials in connection errors, or S3 bucket configuration.
- **Recommended Fix:** Replace error details with generic messages like `"error": "unavailable"`. Log the full error server-side. Consider adding authentication or IP allowlisting for the deep health check.
- **Files to Modify:** `app/eqms/routes.py`

#### H-005: `ManagedDocument.is_deleted == False` — SQLAlchemy Best Practice Violation

- **Severity:** High (potential subtle bugs)
- **Location:** `app/eqms/modules/equipment/admin.py:211`, `app/eqms/modules/suppliers/admin.py:172`
- **Description:** Using `== False` with SQLAlchemy boolean columns can produce incorrect SQL in some database backends. The correct SQLAlchemy idiom is `.is_(False)` or `~ManagedDocument.is_deleted`.
- **Impact:** On PostgreSQL, `== False` generally works correctly but is flagged by SQLAlchemy linters. On some backends or with `None` values, the comparison may not behave as expected (NULL != False).
- **Recommended Fix:** Replace `ManagedDocument.is_deleted == False` with `ManagedDocument.is_deleted.is_(False)`.
- **Files to Modify:** `app/eqms/modules/equipment/admin.py`, `app/eqms/modules/suppliers/admin.py`

#### H-006: CSP Header Allows `'unsafe-inline'` for Scripts

- **Severity:** High
- **Location:** `app/eqms/__init__.py`, `_security_headers` function
- **Description:** The Content-Security-Policy includes `script-src 'self' 'unsafe-inline'`. The `'unsafe-inline'` directive defeats the purpose of CSP for XSS prevention. This is currently necessary because several templates use inline `<script>` blocks and `onclick` handlers.
- **Impact:** CSP does not protect against XSS attacks involving inline script injection.
- **Recommended Fix:** Long-term: move all inline scripts to external `.js` files and use CSP nonces. Short-term: document this as an accepted risk.
- **Files to Modify:** `app/eqms/__init__.py`, multiple templates

#### H-007: `datetime.utcnow()` Still Used in Import Script

- **Severity:** High (consistency)
- **Location:** `scripts/import_equipment_and_suppliers.py`, lines 180, 181, 272, 273, 309, 310, 369
- **Description:** Despite the codebase-wide migration to `utcnow()` from `app.eqms.utils`, the import script still uses `datetime.utcnow()` in 7 places. This produces naive datetimes that are deprecated in Python 3.12+.
- **Impact:** Deprecation warnings. Inconsistency with the rest of the codebase. Potential issues if the app later enforces timezone-aware datetimes.
- **Recommended Fix:** Import `utcnow` from `app.eqms.utils` and replace all instances.
- **Files to Modify:** `scripts/import_equipment_and_suppliers.py`

#### H-008: Manufacturing Module Uses `g.current_user` Directly Instead of `_current_user()`

- **Severity:** High (consistency / error handling)
- **Location:** `app/eqms/modules/manufacturing/admin.py`, lines 207, 322, 374, 427, 487, 595, 643, 675, 729, 761
- **Description:** All other modules import `current_user as _current_user` from `app.eqms.utils` and call `_current_user()`, which raises `RuntimeError` with a clear message if no user is authenticated. The manufacturing module accesses `g.current_user` directly, which returns `None` if no user is loaded, potentially causing `AttributeError` later when `user.id` is accessed.
- **Impact:** Less clear error messages on auth failures in manufacturing routes. Potential `AttributeError: 'NoneType' object has no attribute 'id'` instead of clean `RuntimeError`.
- **Recommended Fix:** Add `from app.eqms.utils import current_user as _current_user` and replace all `g.current_user` references with `_current_user()`.
- **Files to Modify:** `app/eqms/modules/manufacturing/admin.py`

#### H-009: `openNotesModal` Fetch Error Not Handled

- **Severity:** High (UX)
- **Location:** `app/eqms/templates/_layout.html`, line 104
- **Description:** The `openNotesModal` function calls `fetch()` without a try/catch or `.catch()`. If the server returns a non-200 response or the network fails, the modal will show "Loading..." indefinitely.
- **Impact:** Users see a stuck loading spinner with no indication of what went wrong. No retry option.
- **Recommended Fix:** Wrap the fetch in try/catch, show an error message in the modal on failure, and optionally add a retry button.
- **Files to Modify:** `app/eqms/templates/_layout.html`

#### H-010: No `conftest.py` — Test Fixtures Duplicated Across Files

- **Severity:** High (maintainability)
- **Location:** `tests/` directory
- **Description:** Each test file defines its own `client` fixture with identical boilerplate (create app, set up test DB, seed user). There is no shared `conftest.py`.
- **Impact:** Test maintenance burden. Changes to app initialization require updating 6+ files. Risk of test fixtures diverging.
- **Recommended Fix:** Create `tests/conftest.py` with a shared `client` fixture and remove duplicated fixtures from individual test files.
- **Files to Modify:** `tests/conftest.py` (new), `tests/test_*.py` (all)

#### H-011: S3Storage `_cached_client` Uses `object.__setattr__` on Frozen Dataclass

- **Severity:** High (correctness edge case)
- **Location:** `app/eqms/storage.py`, line ~73
- **Description:** `S3Storage` is a `frozen=True` dataclass but uses `object.__setattr__(self, "_cached_client", client)` to cache the boto3 client. While this works, it bypasses the frozen protection and could cause subtle issues if the dataclass is used in sets or as dict keys (since `__hash__` is auto-generated for frozen dataclasses based on field values, but `_cached_client` is not a field).
- **Impact:** Low risk in practice since `S3Storage` instances aren't typically hashed. But it's a code smell that could confuse future developers.
- **Recommended Fix:** Use `functools.lru_cache` on `_client()` method or use a module-level cache dict keyed by the storage configuration tuple.
- **Files to Modify:** `app/eqms/storage.py`

---

### Medium (Functional issues, inconsistencies, UX problems)

#### M-001: `release.py` Prints "SilqeQMS" Instead of "SilqQMS"

- **Severity:** Medium (cosmetic)
- **Location:** `scripts/release.py`, lines 42 and 71
- **Description:** Log messages say "SilqeQMS" (with extra 'e') instead of "SilqQMS".
- **Impact:** Confusing log output in deployment. Minor brand inconsistency.
- **Recommended Fix:** Change "SilqeQMS" to "SilqQMS" in both print statements.
- **Files to Modify:** `scripts/release.py`

#### M-002: Document Control Service `to_download_fileobj()` Appears Unused

- **Severity:** Medium
- **Location:** `app/eqms/modules/document_control/service.py`
- **Description:** `to_download_fileobj()` creates a `BytesIO` wrapper but no route in `document_control/admin.py` calls it — downloads use `storage.open()` directly.
- **Impact:** Dead code. Adds maintenance burden.
- **Recommended Fix:** Verify no callers exist (confirmed via grep), then remove the function.
- **Files to Modify:** `app/eqms/modules/document_control/service.py`

#### M-003: Schema Health Check Expected Tables May Drift

- **Severity:** Medium
- **Location:** `app/eqms/__init__.py`, `_run_schema_health_check` function
- **Description:** The expected tables list is hardcoded in the schema health check. When new tables are added (via migrations), this list must be manually updated. A forgotten update causes false-positive schema warnings.
- **Impact:** Could trigger the schema-out-of-date error page incorrectly, or miss actual schema drift.
- **Recommended Fix:** Auto-derive the expected tables from `Base.metadata.tables.keys()` instead of hardcoding.
- **Files to Modify:** `app/eqms/__init__.py`

#### M-004: Missing Pagination on List Pages

- **Severity:** Medium (performance)
- **Location:** All `admin.py` list routes across modules
- **Description:** Most list pages (equipment, suppliers, supplies, manufacturing lots, purchasing, admin_docs) load all records with `.all()` without pagination. Only the distribution log list and customers list have any kind of limiting.
- **Impact:** As data grows (hundreds of documents per library, hundreds of equipment items), list pages will become slow. Particularly concerning for admin_docs which may have hundreds of files per library.
- **Recommended Fix:** Add pagination with `LIMIT`/`OFFSET` or cursor-based pagination. Add page navigation UI.
- **Files to Modify:** Multiple `admin.py` files across all modules

#### M-005: Bulk Equipment Import (`equipment/admin.py`) Doesn't Validate File Size Before Reading

- **Severity:** Medium
- **Location:** `app/eqms/modules/equipment/admin.py`, bulk import route
- **Description:** The bulk import reads the entire uploaded file into memory without checking file size first. While the app has a 100MB limit globally, a large Excel file could still consume significant memory.
- **Impact:** Memory exhaustion for very large files.
- **Recommended Fix:** Check `request.content_length` before processing. Add a specific file size limit for bulk imports (e.g., 10MB).
- **Files to Modify:** `app/eqms/modules/equipment/admin.py`

#### M-006: ShipStation Sync Service — Broad `except Exception: pass` Blocks

- **Severity:** Medium
- **Location:** `app/eqms/modules/shipstation_sync/service.py`, lines 266, 291, 321, 569, 593
- **Description:** Multiple bare `except Exception: pass` blocks silently swallow errors during sync processing. This makes debugging sync issues very difficult.
- **Impact:** Silent data loss or missed records during ShipStation sync. No visibility into failures.
- **Recommended Fix:** At minimum, log the exception. Consider collecting errors and reporting them in the sync summary.
- **Files to Modify:** `app/eqms/modules/shipstation_sync/service.py`

#### M-007: `DistributionLogEntry.external_key` Column Added but Never Used

- **Severity:** Medium (dead schema)
- **Location:** Migration `8b1c2d3e4f50`, `DistributionLogEntry` model
- **Description:** The `external_key` column was added in a drift-fix migration, and a unique index on `(source, external_key)` was created, but no code in `service.py` or `admin.py` reads or writes this field.
- **Impact:** Wasted database space and an unused unique index. Could cause confusion for future developers.
- **Recommended Fix:** Either implement the deduplication logic using `external_key` (it was likely intended for ShipStation dedup), or drop the column and index in a new migration.
- **Files to Modify:** `app/eqms/modules/rep_traceability/models.py`, new migration

#### M-008: No N+1 Query Protection on Several List Routes

- **Severity:** Medium (performance)
- **Location:** `app/eqms/modules/equipment/admin.py`, `app/eqms/modules/suppliers/admin.py`, `app/eqms/modules/manufacturing/admin.py`
- **Description:** List routes query all records but don't use `selectinload` or `joinedload` for relationships. When templates access `equipment.suppliers` or `lot.documents`, each access triggers a separate query.
- **Impact:** Slow page loads as data grows. N+1 query pattern.
- **Recommended Fix:** Add `.options(selectinload(Equipment.suppliers))` and similar to list queries. The distribution log list already does this correctly — use it as a pattern.
- **Files to Modify:** Multiple `admin.py` files

#### M-009: Customer Merge Token Uses `hmac` but Doesn't Bind to Session

- **Severity:** Medium (security)
- **Location:** `app/eqms/admin.py`, merge endpoint
- **Description:** The merge confirmation uses an HMAC token to prevent tampering, but the token isn't bound to the user's session. A valid token generated for one admin user could potentially be reused by another.
- **Impact:** Low risk since only admins can access the merge page, but it's a defense-in-depth gap.
- **Recommended Fix:** Include `session['user_id']` in the HMAC input to bind tokens to sessions.
- **Files to Modify:** `app/eqms/admin.py`

#### M-010: EML Viewer Route Doesn't Sanitize HTML

- **Severity:** Medium (security)
- **Location:** `app/eqms/modules/purchasing/admin.py`, EML view route
- **Description:** The purchasing module renders EML files by parsing email headers and potentially rendering HTML email bodies. If the email body contains malicious HTML/JavaScript, it could execute in the admin's browser.
- **Impact:** Potential XSS via crafted EML files uploaded to purchase orders.
- **Recommended Fix:** Use the same `_sanitize_html()` function from `document_viewer.py` to sanitize EML body HTML before rendering.
- **Files to Modify:** `app/eqms/modules/purchasing/admin.py`

#### M-011: Missing `updated_by_user_id` on Several Models

- **Severity:** Medium (audit trail)
- **Location:** `Supply` model, `AdminDocFile` model, `AdminDocFolder` model
- **Description:** While `Equipment`, `Supplier`, and `ManufacturingLot` track `updated_by_user_id`, the `Supply`, `AdminDocFile`, and `AdminDocFolder` models do not. This creates inconsistency in the audit trail.
- **Impact:** Cannot determine who last modified a supply item or admin document.
- **Recommended Fix:** Add `updated_by_user_id` column to these models and update the service/admin code to set it.
- **Files to Modify:** Model files, migration, service/admin files

#### M-012: `backfill_customer_addresses.py` Doesn't Commit on Empty Updates

- **Severity:** Medium
- **Location:** `scripts/backfill_customer_addresses.py`, line 115
- **Description:** The script calls `s.commit()` even if `updated == 0`, which is unnecessary but harmless. However, it also doesn't handle the case where `_parse_bill_to_block` or `_parse_ship_to_block` return partial data — it may overwrite existing city/state/zip with None values from an incomplete parse.
- **Impact:** Potential data loss if a PDF parse returns a partial address.
- **Recommended Fix:** Only update individual fields when the parsed value is truthy AND the existing value is empty/blank (the script already checks for empty existing values but doesn't check if parsed values are truthy for city/state/zip individually).
- **Files to Modify:** `scripts/backfill_customer_addresses.py`

#### M-013: `cleanup_pdf_import_distributions.py` Missing sys.path Setup

- **Severity:** Medium
- **Location:** `scripts/cleanup_pdf_import_distributions.py`, line 1
- **Description:** Unlike other scripts that add the project root to `sys.path`, this script directly imports from `app.eqms.modules` without path setup. It will fail with `ModuleNotFoundError` unless run from the project root.
- **Impact:** Script fails when run from a different directory.
- **Recommended Fix:** Add the standard `sys.path.insert(0, ...)` pattern used by other scripts.
- **Files to Modify:** `scripts/cleanup_pdf_import_distributions.py`

#### M-014: `supplies/service.py` `delete_supply_document` Also Deletes from Storage

- **Severity:** Medium (inconsistency)
- **Location:** `app/eqms/modules/supplies/service.py`, `delete_supply_document` function
- **Description:** This function performs a hard delete (`s.delete(doc)`) AND removes the file from storage. All other modules (equipment, suppliers, manufacturing) use soft-delete (`is_deleted = True`). This means supply documents are irrecoverable once deleted.
- **Impact:** Data loss risk. Inconsistent behavior across modules. No audit trail for the deletion (the audit event is recorded but the data is gone).
- **Recommended Fix:** Change to soft-delete pattern consistent with other modules. Add `is_deleted`, `deleted_at`, `deleted_by_user_id` columns to `SupplyDocument`.
- **Files to Modify:** `app/eqms/modules/supplies/service.py`, `app/eqms/modules/supplies/models.py`, new migration

#### M-015: Multiple Migration "Schema Drift Fix" Files Suggest Fragile Migration Process

- **Severity:** Medium (process)
- **Location:** `migrations/versions/8b1c2d3e4f50_*.py`, `9c0d1e2f3a4b_*.py`, `a1b2c3d4e5f6_*.py`
- **Description:** Three separate "fix schema drift" migrations exist, each adding columns that were missing in production. This suggests migrations were skipped or partially applied during earlier deploys.
- **Impact:** Migration chain fragility. Future schema drift is likely if the deployment process isn't tightened.
- **Recommended Fix:** Ensure `alembic upgrade head` runs reliably in every deployment (already handled by `release.py`). Consider adding a CI check that verifies migration chain integrity.
- **Files to Modify:** Process improvement, no code changes needed

#### M-016: `document_control/admin.py` Doesn't Use Document Viewer for Inline Rendering

- **Severity:** Medium (UX inconsistency)
- **Location:** `app/eqms/modules/document_control/admin.py`, view/download routes
- **Description:** While other modules (equipment, suppliers, supplies, purchasing, admin_docs) integrate the centralized `document_viewer.py` for rendering .docx/.xlsx/.csv files inline, the document control module appears to serve files directly without using `needs_server_render()` / `render_document_to_response()`.
- **Impact:** .docx files uploaded to DCOs won't render inline — they'll be offered as downloads instead. Inconsistent UX across modules.
- **Recommended Fix:** Integrate `document_viewer.py` into the document control view route, following the pattern used by equipment/suppliers/supplies.
- **Files to Modify:** `app/eqms/modules/document_control/admin.py`

#### M-017: Missing `__init__.py` for `scripts/` Directory

- **Severity:** Medium
- **Location:** `scripts/` directory
- **Description:** The `scripts/` directory is imported as a package in `release.py` (`from scripts import init_db`) and `start.py` (`from scripts.release import run_release`), but there is no `scripts/__init__.py` file. This works in Python 3 (implicit namespace packages) but can cause issues with some tools and IDEs.
- **Impact:** Potential import issues in some environments. Tool/IDE confusion.
- **Recommended Fix:** Add an empty `scripts/__init__.py` file.
- **Files to Modify:** `scripts/__init__.py` (new)

#### M-018: Sales Dashboard `compute_sales_dashboard` Is Very Long and Complex

- **Severity:** Medium (maintainability)
- **Location:** `app/eqms/modules/rep_traceability/service.py`, `compute_sales_dashboard` function
- **Description:** This function is approximately 200+ lines with deeply nested logic, multiple inline queries, and lot-tracking code that imports from the ShipStation parsers module. It's difficult to test, debug, or modify.
- **Impact:** High maintenance burden. Difficult to add new dashboard metrics. Potential for subtle calculation bugs.
- **Recommended Fix:** Break into smaller functions: `_compute_order_metrics()`, `_compute_customer_metrics()`, `_compute_sku_breakdown()`, `_compute_lot_tracking()`. Each can be tested independently.
- **Files to Modify:** `app/eqms/modules/rep_traceability/service.py`

---

### Low (Cleanup, minor improvements, code quality)

#### L-001: `release.py` Contains Diagnostic Code for Customer Reps Migration

- **Severity:** Low
- **Location:** `scripts/release.py`, lines 50–59
- **Description:** Diagnostic code reads a specific migration file and prints lines containing "is_primary". This was useful during development but is no longer needed.
- **Recommended Fix:** Remove the diagnostic block.
- **Files to Modify:** `scripts/release.py`

#### L-002: Inconsistent `secure_filename` Usage Across Modules

- **Severity:** Low
- **Location:** Multiple service files
- **Description:** Some modules apply `secure_filename()` to uploaded filenames, while others store the original filename directly. The `ManagedDocument` stores `secure_filename(filename) or "document.bin"`, but `ManufacturingLotDocument` stores `filename` directly.
- **Recommended Fix:** Standardize: always use `secure_filename()` for `original_filename` storage.
- **Files to Modify:** `app/eqms/modules/manufacturing/service.py`

#### L-003: Test Coverage Gaps

- **Severity:** Low
- **Location:** `tests/` directory
- **Description:** Only 39 test functions exist across 7 test files. Major modules with no dedicated tests: admin_docs, customer_profiles, purchasing, supplies, nre_projects, shipstation_sync. The existing tests are mostly smoke tests (login + basic route access).
- **Recommended Fix:** Add integration tests for critical paths: document upload/download chain, customer merge, ShipStation sync, sales order PDF import.
- **Files to Modify:** `tests/` directory (new test files)

#### L-004: `app/eqms/constants.py` — Verify Contents

- **Severity:** Low
- **Location:** `app/eqms/constants.py`
- **Description:** File exists but its contents were not fully audited. Verify constants are still in use.
- **Recommended Fix:** Grep for each constant and remove unused ones.
- **Files to Modify:** `app/eqms/constants.py`

#### L-005: No Type Hints on Several Route Functions

- **Severity:** Low (code quality)
- **Location:** Multiple `admin.py` files
- **Description:** Route handler functions lack return type annotations. While Flask doesn't require them, type hints improve IDE support and code documentation.
- **Recommended Fix:** Add `-> Response | str` return type hints to route handlers.
- **Files to Modify:** All `admin.py` files

#### L-006: `Dockerfile` — Missing `.dockerignore`

- **Severity:** Low
- **Location:** Project root
- **Description:** No `.dockerignore` file exists. The `COPY . /app` command copies all files including `.git/`, `__pycache__/`, `storage/`, test files, and local documents. This unnecessarily inflates the Docker image.
- **Recommended Fix:** Create `.dockerignore` with entries for `.git/`, `__pycache__/`, `*.pyc`, `.env`, `storage/`, `tests/`, `*.db`, and the document directories listed in `.gitignore`.
- **Files to Modify:** `.dockerignore` (new)

#### L-007: No Logging Configuration for Production

- **Severity:** Low
- **Location:** `app/eqms/__init__.py`
- **Description:** The application uses Flask's default logging configuration. In production, there's no structured logging, log level configuration, or log rotation.
- **Recommended Fix:** Add structured JSON logging for production environments. Configure log levels via environment variable.
- **Files to Modify:** `app/eqms/__init__.py`

#### L-008: `_sanitize_html` in Document Viewer Uses Regex Instead of Parser

- **Severity:** Low (security)
- **Location:** `app/eqms/document_viewer.py`
- **Description:** HTML sanitization uses regex patterns to strip dangerous tags. Regex-based HTML sanitization is notoriously fragile and can be bypassed with creative encoding or tag nesting.
- **Impact:** Low risk since the input is mammoth-converted HTML (not arbitrary user HTML), but it's a defense-in-depth concern.
- **Recommended Fix:** Consider using `bleach` or `nh3` library for robust HTML sanitization. Add to `requirements.txt`.
- **Files to Modify:** `app/eqms/document_viewer.py`, `requirements.txt`

#### L-009: Several Templates Use Inline Styles Extensively

- **Severity:** Low (maintainability)
- **Location:** Most admin templates
- **Description:** While a design system CSS exists (`design-system.css`), many templates contain extensive inline `style` attributes for layout, spacing, and colors. This makes the UI harder to maintain and update consistently.
- **Recommended Fix:** Extract common inline styles into CSS classes in the design system.
- **Files to Modify:** `app/eqms/static/design-system.css`, multiple templates

#### L-010: `admin_docs/service.py` TYPE_CHECKING Import Pattern

- **Severity:** Low
- **Location:** `app/eqms/modules/admin_docs/service.py`
- **Description:** Uses `if TYPE_CHECKING:` for `Session` import but the function signatures use string annotations `"Session"`. This is fine but inconsistent with other service files that use `from __future__ import annotations` instead.
- **Recommended Fix:** Add `from __future__ import annotations` to standardize.
- **Files to Modify:** `app/eqms/modules/admin_docs/service.py`

#### L-011: `tests/test_customer_key.py` Has 20 Tests but Other Test Files Are Minimal

- **Severity:** Low (testing imbalance)
- **Location:** `tests/`
- **Description:** Customer key logic has thorough unit tests (20 functions), but most other test files have 1-7 tests. The testing effort is unevenly distributed.
- **Recommended Fix:** Prioritize adding tests for critical business logic: lot status transitions, sales dashboard computations, distribution matching, PDF parsing.
- **Files to Modify:** `tests/` (expand existing files)

#### L-012: `customer_profiles/service.py` Has Redundant `find_merge_candidates` Logic

- **Severity:** Low
- **Location:** `app/eqms/modules/customer_profiles/service.py` and `app/eqms/admin.py`
- **Description:** Customer merge logic exists in both `customer_profiles/service.py` (the service layer) and `admin.py` (with inline merge logic for the admin routes). The admin.py version was built for the UI flow and may have slightly different merge behavior.
- **Recommended Fix:** Ensure admin.py delegates entirely to the service layer for merge operations. Remove any duplicated logic.
- **Files to Modify:** `app/eqms/admin.py`

#### L-013: Commented-Out Migration-on-Start Code

- **Severity:** Low
- **Location:** `app/eqms/__init__.py`, line 92
- **Description:** There's a commented-out block: `# if (os.environ.get("RUN_MIGRATIONS_ON_START") or "").strip() == "1":` that previously ran migrations on app start. It's disabled with a comment about deployment hangs.
- **Recommended Fix:** Remove the commented-out code. The `release.py` script handles migrations.
- **Files to Modify:** `app/eqms/__init__.py`

#### L-014: `pytest` Listed as Production Dependency

- **Severity:** Low
- **Location:** `requirements.txt`, line 7
- **Description:** `pytest` is listed in the main `requirements.txt` and will be installed in the production Docker image. It's only needed for development/testing.
- **Recommended Fix:** Move `pytest` to a separate `requirements-dev.txt`.
- **Files to Modify:** `requirements.txt`, `requirements-dev.txt` (new)

---

## Module-by-Module Health Report

### 1. Core (`app/eqms/`) — Grade: A-
Well-structured app factory, clean RBAC, proper session management. Minor issues: CSP unsafe-inline, commented-out code, schema health check uses hardcoded table list.

### 2. Admin (`app/eqms/admin.py`) — Grade: B+
Comprehensive admin dashboard with diagnostics, user management, customer merge, data reset. Clean route organization. Minor: merge token not session-bound.

### 3. Admin Docs — Grade: A
Clean 11-library architecture. Folder/file CRUD works well. Document viewer integrated. No significant issues found.

### 4. Customer Profiles — Grade: A-
Solid CRUD with tabs, notes, merge functionality. Good canonical key system. Minor: some redundancy between admin.py and service.py merge logic.

### 5. Document Control — Grade: B
Functional DCO lifecycle. Missing: document viewer integration for inline rendering of .docx/.xlsx files. Unused `to_download_fileobj()` function.

### 6. Equipment — Grade: A-
Comprehensive CRUD, bulk import, PDF extraction, document management. Minor: `is_deleted == False` instead of `.is_(False)`.

### 7. Manufacturing — Grade: B
Lot lifecycle well-implemented with proper status transitions. Issues: uses `g.current_user` instead of `_current_user()`, no eager loading on list queries.

### 8. NRE Projects — Grade: B+
Clean implementation. PDF upload/view/download for unmatched sales orders. No significant issues.

### 9. Purchasing — Grade: B
PO CRUD with PDF import and EML viewing. Issue: EML body HTML not sanitized before rendering.

### 10. Rep Traceability — Grade: B
Most complex module (~2500 lines in admin.py). Distribution log, sales orders, tracing reports, sales dashboard all functional. Issues: `compute_sales_dashboard` is very long, some N+1 queries.

### 11. ShipStation Sync — Grade: B-
Functional sync with API. Issues: many silent `except Exception: pass` blocks, in-memory rate limiting doesn't work with multiple workers.

### 12. Suppliers — Grade: B-
**Critical bug**: `validate_managed_document` not available at runtime (C-001). Otherwise functional CRUD with document management.

### 13. Supplies — Grade: B
Functional CRUD. Issue: hard-deletes documents instead of soft-delete (inconsistent with other modules).

---

## Document Viewing Chain Verification

| # | Context | View Route | Download Route | Server Render | Status |
|---|---------|------------|----------------|---------------|--------|
| 1 | Admin Docs (11 libraries) | ✅ `admin_docs_document_view` | ✅ `admin_docs_document_download` | ✅ Uses `render_document_to_response` | **PASS** |
| 2 | Equipment Docs | ✅ `equipment_document_view` | ✅ `equipment_document_download` | ✅ Uses `render_document_to_response` | **PASS** |
| 3 | Supplier Docs | ✅ `supplier_document_view` | ✅ `supplier_document_download` | ✅ Uses `render_document_to_response` | **PASS** (but upload crashes — C-001) |
| 4 | Supply Docs | ✅ `supplies_document_view` | ✅ `supplies_document_download` | ✅ Uses `render_document_to_response` | **PASS** |
| 5 | Manufacturing Lot Docs | ✅ `suspension_lot_document_view` | ✅ `suspension_lot_document_download` | ✅ Uses `render_document_to_response` | **PASS** |
| 6 | Document Control (DCOs) | ✅ `view_file` | ✅ `download_file` | ❌ Missing integration | **PARTIAL** — M-016 |
| 7 | Purchase Order Attachments | ✅ `purchasing_attachment_view` | ✅ `purchasing_attachment_download` | ✅ Uses `render_document_to_response` | **PASS** |
| 8 | Sales Order PDFs | ✅ View via `rep_traceability` | ✅ Download route | N/A (PDFs only) | **PASS** |
| 9 | NRE Project PDFs | ✅ `nre_view_pdf` | ✅ `nre_download_pdf` | N/A (PDFs only) | **PASS** |
| 10 | Approval EMLs | ✅ Via tracing report detail | ✅ Download route | N/A (EMLs served raw) | **PASS** |

**Summary:** 9/10 contexts pass fully. Document Control (DCO) module is missing the centralized document viewer integration for non-PDF files.

---

## Recommended Priority Order

### Immediate (Fix before next deployment)

1. **C-001** — Fix `suppliers/service.py` missing runtime import (supplier uploads broken)
2. **H-001** — Pin dependency versions in `requirements.txt` (deployment stability)
3. **C-002** — Fix `import_equipment_and_suppliers.py` indentation (script non-functional)
4. **C-003** — Fix `dedupe_customers.py` session binding (script non-functional)

### High Priority (Fix within 1 week)

5. **H-002** — Remove hardcoded SQLite URL from `alembic.ini`
6. **H-004** — Sanitize error messages in `/health/deep`
7. **H-005** — Fix `is_deleted == False` to `.is_(False)`
8. **H-007** — Replace `datetime.utcnow()` in import script
9. **H-008** — Standardize manufacturing module to use `_current_user()`
10. **H-009** — Add error handling to `openNotesModal` fetch

### Medium Priority (Fix within 2 weeks)

11. **M-001** — Fix "SilqeQMS" typo in release.py
12. **M-010** — Sanitize EML HTML in purchasing viewer
13. **M-014** — Change supplies document deletion to soft-delete
14. **M-016** — Integrate document viewer into document control module
15. **M-006** — Replace silent exception handling in ShipStation sync
16. **M-004** — Add pagination to list pages

### Deferred (Address during next feature sprint)

17. **H-003** — Implement Redis-backed rate limiting (requires infrastructure)
18. **H-006** — Move inline scripts to external files for proper CSP
19. **M-018** — Refactor `compute_sales_dashboard`
20. **L-003** — Expand test coverage
21. **L-006** — Create `.dockerignore`
22. **L-008** — Switch to `bleach`/`nh3` for HTML sanitization

---

*End of audit. 46 findings documented. No code was modified during this audit.*
