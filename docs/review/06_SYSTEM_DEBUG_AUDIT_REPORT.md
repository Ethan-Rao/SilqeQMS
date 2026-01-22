# 06 SYSTEM DEBUG AUDIT REPORT — SilqeQMS / Rep-QMS (Repo-wide)

This is an evidence-backed **gap + bug + cleanup** audit intended for the Planning Agent to convert into a development plan. It reflects the required method: start from README claims, then do a static inventory of routes/blueprints/models/migrations/templates, then identify suspect/dead/duplicated areas, and finally propose lean fix directions with verification steps.

---

### 1) Snapshot summary

- **Manufacturing module document upload/download is currently broken** due to **storage API mismatch** (`storage_from_config()` called without config; uses `storage.put`/`storage.get` that do not exist) → **Blocker** (`app/eqms/modules/manufacturing/admin.py`, `app/eqms/modules/manufacturing/service.py`, `app/eqms/storage.py`).
- **CSRF protection is absent** across the admin surface (many POST routes including deletes/uploads) → high-risk even for “admin-only” systems (no CSRF tokens, no Flask-WTF) (`app/eqms/templates/*`, `app/eqms/*`).
- **RUN_MIGRATIONS_ON_START is documented but disabled in code**, creating operational drift between README/runbooks and actual deployment behavior (README vs `app/eqms/__init__.py`).
- **Admin shell has confusing duplication**: “Manufacturing” appears twice (real module + stub) which is a navigation trap (`app/eqms/templates/admin/index.html`).
- **Schema drift handling exists but is messy and duplicated across multiple migrations**, increasing risk for future upgrades and making DB state hard to reason about (`migrations/versions/7f9a...`, `8b1c...`, `9c0d...`, `a1b2c...` + runtime `_schema_health_guardrail` in `app/eqms/__init__.py`).
- **Manufacturing uses flash categories not supported by the CSS design system**, so errors/warnings may render without visual severity cues (`flash("...", "error")` vs CSS defines only `flash--danger`/`flash--success`) (`app/eqms/modules/manufacturing/admin.py`, `app/eqms/static/design-system.css`).
- **ShipStation sync runs synchronously in the request thread** (admin-triggered). A slow API or parsing issue can tie up worker threads and trigger timeouts; no background job or rate limiting is present (`app/eqms/modules/shipstation_sync/admin.py`, `.../service.py`).
- **Local storage backend uses `os.getcwd()/storage`**, which is sensitive to working directory and can lead to “files not found” in production if cwd differs between runtime and release/migration steps (`app/eqms/storage.py`, tests rely on `monkeypatch.chdir`).
- **Document storage key sanitization is inconsistent**: some modules rely on `secure_filename`, others do partial string replacements and may not defend against `..` segments in user-controlled identifiers (e.g. lot_number, equip_code) (`app/eqms/modules/*/service.py`).
- **Polymorphic document model (`ManagedDocument`) can become internally inconsistent** (entity_type/entity_id vs optional equipment_id/supplier_id) because the DB does not enforce “exactly one FK matches the entity_type” (`app/eqms/modules/equipment/models.py`, migration `199268f34bba...`).
- **Legacy directory contains large proto implementations** (including SMTP/email, direct psycopg2 SQL, `requests`) that are not aligned with the current minimal Flask app and are likely dead/unsafe → should be quarantined or deleted (`legacy/repqms_Proto1_reference.py.py`, `legacy/repqms_shipstation_sync.py.py`).
- **Optional import scripts require deps not in requirements** (`openpyxl`, `python-docx`, `requests`) and will fail if run without manual pip installs; this is a support trap if not clearly documented as optional tooling (`scripts/import_equipment_and_suppliers.py`, `legacy/*.py.py`).
- **Tests cover Document Control + Rep Traceability** but **do not cover** Equipment, Suppliers, Manufacturing, or ShipStation sync modules → high regression risk for newly added modules (`tests/`).

---

### 2) System map (current reality)

#### 2.1 README claims vs repo reality (high-signal)

- README claims the system includes **Equipment & Supplies**, **Suppliers**, and **Manufacturing** modules — these modules do exist and are registered (`README.md`, `app/eqms/__init__.py`).
- README recommends a fallback toggle `RUN_MIGRATIONS_ON_START=1`; code explicitly disables it (“causing deployment hangs”) and recommends manual DO console migration → **operational mismatch** (`README.md` vs `app/eqms/__init__.py`).

#### 2.2 Blueprints/modules (registered)

Entry point: `app/wsgi.py` → `app.eqms.create_app()` in `app/eqms/__init__.py`.

Blueprints wired (URL prefixes from `app/eqms/__init__.py`):

- **Public routes**: `routes` (`/`, `/health`) — `app/eqms/routes.py`
- **Auth**: `auth` (`/auth/*`) — `app/eqms/auth.py`
- **Admin shell + audit UI**: `admin` (`/admin/*`) — `app/eqms/admin.py`
- **Document Control**: `doc_control` (`/admin/modules/document-control/*`) — `app/eqms/modules/document_control/admin.py`
- **Rep Traceability**: `rep_traceability` (`/admin/*`) — `app/eqms/modules/rep_traceability/admin.py`
- **Customer Profiles**: `customer_profiles` (`/admin/*`) — `app/eqms/modules/customer_profiles/admin.py`
- **ShipStation Sync**: `shipstation_sync` (`/admin/*`) — `app/eqms/modules/shipstation_sync/admin.py`
- **Equipment**: `equipment` (`/admin/*`) — `app/eqms/modules/equipment/admin.py`
- **Suppliers**: `suppliers` (`/admin/*`) — `app/eqms/modules/suppliers/admin.py`
- **Manufacturing**: `manufacturing` (`/admin/manufacturing/*`) — `app/eqms/modules/manufacturing/admin.py`

#### 2.3 Key routes/endpoints (selected)

Auth:
- `GET/POST /auth/login`, `GET /auth/logout` — `app/eqms/auth.py`

Admin + Audit:
- `GET /admin/`, `GET /admin/me`, `GET /admin/audit` — `app/eqms/admin.py`

Document Control:
- `GET /admin/modules/document-control/` list
- `POST /admin/modules/document-control/new` create doc + rev A
- `POST /admin/modules/document-control/<doc_id>/revisions/<rev_id>/upload`
- `POST /admin/modules/document-control/<doc_id>/revisions/<rev_id>/release`
- `GET /admin/modules/document-control/files/<file_id>/download`

Rep Traceability:
- Distribution: `/admin/distribution-log*` (list/new/edit/delete/import/export)
- Tracing reports: `/admin/tracing*` (list/generate/detail/download)
- Approvals evidence: `/admin/tracing/<id>/approvals/upload` and `/admin/approvals/<id>/download`
- Sales dashboard: `/admin/sales-dashboard*`

Customers:
- `/admin/customers*` (list/new/detail/update/notes)

ShipStation:
- `/admin/shipstation` (index), `/admin/shipstation/run` (sync), `/admin/shipstation/diag` (diagnostics)

Equipment/Suppliers:
- `/admin/equipment*` and `/admin/suppliers*` plus document upload/download/delete and association endpoints

Manufacturing (Suspension):
- `/admin/manufacturing/` (landing)
- `/admin/manufacturing/suspension*` (list/new/detail/edit/status/disposition/docs/equipment/materials)

#### 2.4 Key tables/models

Core:
- `users`, `roles`, `permissions`, `user_roles`, `role_permissions` — `app/eqms/models.py`
- `audit_events` — `app/eqms/models.py`

Document Control:
- `documents`, `document_revisions`, `document_files` — `app/eqms/modules/document_control/models.py`

Rep Traceability:
- `distribution_log_entries` (includes `external_key` idempotency for ShipStation)
- `tracing_reports`, `approvals_eml` — `app/eqms/modules/rep_traceability/models.py`

Customer Profiles:
- `customers`, `customer_notes` — `app/eqms/modules/customer_profiles/models.py`

ShipStation Sync:
- `shipstation_sync_runs`, `shipstation_skipped_orders` — `app/eqms/modules/shipstation_sync/models.py`

Equipment/Suppliers:
- `equipment`, `suppliers`, `equipment_suppliers`, `managed_documents` — `app/eqms/modules/equipment/models.py`, `.../suppliers/models.py`

Manufacturing:
- `manufacturing_lots`, `manufacturing_lot_documents`, `manufacturing_lot_equipment`, `manufacturing_lot_materials` — `app/eqms/modules/manufacturing/models.py`

#### 2.5 Storage strategy (current)

Single abstraction: `app/eqms/storage.py`
- **Local**: `LocalStorage(root=Path(os.getcwd()) / "storage")` with `put_bytes/open/exists`
- **S3-compatible**: `S3Storage` via `boto3` (present in requirements), uses `put_object` / `get_object`

Modules generally use `storage_from_config(current_app.config)` + `put_bytes/open`, except **Manufacturing**, which uses an older API shape (see Blockers).

---

### 3) Critical runtime breakages (Blockers)

#### B1) Manufacturing document upload/download uses non-existent storage API

- **Where**:
  - `app/eqms/modules/manufacturing/service.py::upload_lot_document` calls `storage = storage_from_config()` and `storage.put(...)`
  - `app/eqms/modules/manufacturing/admin.py::suspension_document_download` calls `storage = storage_from_config()` and `storage.get(...)`
  - `app/eqms/storage.py` defines `storage_from_config(config: dict)` and storage methods `put_bytes/open/exists` only
- **Symptom**:
  - Any Manufacturing document upload will crash (AttributeError / TypeError).
  - Any Manufacturing document download will crash (TypeError calling `storage_from_config()` without config; plus `.get` missing).
- **Root cause hypothesis**: Manufacturing module was ported from an older storage abstraction (with `.put/.get` and configless initialization) but storage layer was later standardized to `put_bytes/open`.
- **Severity**: **Blocker**
- **Fix direction** (lean):
  - In `manufacturing/service.py`, replace `storage_from_config()` with `storage_from_config(current_app.config)` and `storage.put(...)` with `storage.put_bytes(...)`.
  - In `manufacturing/admin.py`, use `storage_from_config(current_app.config)` and return `send_file(storage.open(key), ...)` (mirroring Rep Traceability and Equipment/Suppliers patterns).
  - Add a focused pytest vertical slice for manufacturing doc upload/download to lock the API contract.
- **How to verify**:
  - `pytest -q tests/test_manufacturing.py` (new) or manual:
    - Create lot → upload doc → download doc (200) → audit event present.

#### B2) Manufacturing flash categories are not supported by the design system CSS

- **Where**:
  - `app/eqms/modules/manufacturing/admin.py` uses `flash(..., "error")` and `flash(..., "warning")`
  - `app/eqms/static/design-system.css` defines only `.flash--danger` and `.flash--success`
- **Symptom**:
  - Manufacturing errors/warnings may render with no visual border severity, making user-facing errors easy to miss.
- **Root cause hypothesis**: Newer modules standardized on `danger/success`; Manufacturing kept legacy category names.
- **Severity**: **High** (UX + supportability)
- **Fix direction**:
  - Normalize manufacturing flash categories to `danger`/`success` (and optionally add `flash--warning` CSS if desired).
- **How to verify**:
  - Trigger a validation failure on `/admin/manufacturing/suspension/new` and confirm flash styling matches other modules.

#### B3) README/runbook deployment instructions diverge from actual code behavior for migrations

- **Where**:
  - README describes `RUN_MIGRATIONS_ON_START=1` fallback.
  - `app/eqms/__init__.py` explicitly disables migration-on-start and recommends manual migrations via DO console.
- **Symptom**:
  - Operators follow README, set the env var, but nothing happens; schema drift persists and triggers runtime issues.
- **Root cause hypothesis**: Migration-on-start caused deployment hangs, so it was disabled without fully updating docs.
- **Severity**: **High** (operational reliability)
- **Fix direction**:
  - Update README/runbooks to remove/replace the toggle advice and clearly require `python scripts/release.py` in DO release step (preferred), or a documented manual procedure.
- **How to verify**:
  - Documentation review + a “cold deploy” checklist run.

---

### 4) High-impact functional defects

#### F1) Manufacturing module likely partially functional beyond basic lot CRUD (docs broken; also storage key sanitization gaps)

- **Where**:
  - Breakage: see B1
  - Key sanitization: `app/eqms/modules/manufacturing/service.py::build_lot_document_storage_key`
- **Symptom**:
  - Lot document features unusable; status transition rules that require documents (“Label”, “QC Report”, “COA”) will be blocked in practice because documents can’t be uploaded.
  - Potential path/key injection: `lot_number` is only partially normalized (slashes/spaces), does not protect against `..`.
- **Root cause hypothesis**: A large module landed with inconsistent storage + incomplete hardening.
- **Severity**: **High**
- **Fix direction**:
  - Fix storage API usage (B1) first.
  - Harden `safe_lot` by applying `secure_filename` (or a strict allowlist) to lot_number used in key paths.
- **How to verify**:
  - Create lot → upload “Label” doc → transition to Quarantined succeeds.

#### F2) Admin shell navigation contains duplicate/contradictory module entries

- **Where**: `app/eqms/templates/admin/index.html`
- **Symptom**:
  - “Manufacturing” appears twice: one routes to `manufacturing.manufacturing_index`, another routes to `admin.module_stub` for manufacturing.
- **Root cause hypothesis**: Scaffold cards were never removed when real module was added.
- **Severity**: **Medium**
- **Fix direction**:
  - Remove the stub card (or hide with feature flag) to avoid user confusion.
- **How to verify**:
  - `/admin/` shows a single Manufacturing entry that routes to the real module.

#### F3) Equipment/Suppliers list views are unpaginated (scales poorly)

- **Where**:
  - `app/eqms/modules/equipment/admin.py::equipment_list` uses `.all()`
  - `app/eqms/modules/suppliers/admin.py::suppliers_list` uses `.all()`
- **Symptom**:
  - As data grows, list pages will slow, and server memory/DB time will increase.
- **Root cause hypothesis**: Implemented as MVP without pagination.
- **Severity**: **Medium**
- **Fix direction**:
  - Add `page`/`per_page` and `.offset/.limit`, matching patterns used in Distribution Log and Manufacturing lot list.
- **How to verify**:
  - Add 1k rows; list remains responsive and supports next/prev pages.

#### F4) ShipStation sync is synchronous and can block worker threads

- **Where**:
  - `app/eqms/modules/shipstation_sync/admin.py::shipstation_run` calls `run_sync(...)` directly and commits
  - `app/eqms/modules/shipstation_sync/service.py::run_sync` loops through pages/orders/shipments
- **Symptom**:
  - Triggering sync can cause timeouts, slow UI, or worker starvation.
  - Failures may leave partial state (though nested transactions reduce blast radius for inserts).
- **Root cause hypothesis**: Designed for “lean” admin-triggered sync, but may outgrow request/response model.
- **Severity**: **Medium**
- **Fix direction** (still minimal):
  - Add explicit time budget / max pages / max orders per run via env vars.
  - Consider spawning a background thread within the process for sync and writing progress to DB (still no new dependencies).
- **How to verify**:
  - Run sync against a large date window; UI remains responsive and run completes within configured time.

#### F5) Document storage model has integrity holes (ManagedDocument polymorphism not enforced)

- **Where**: `app/eqms/modules/equipment/models.py::ManagedDocument`, migration `199268f34bba_add_equipment_and_suppliers_tables.py`
- **Symptom**:
  - Rows can exist where `entity_type="equipment"` but `equipment_id` is NULL (or supplier_id is set), or where `entity_id` doesn’t match the FK column.
- **Root cause hypothesis**: Schema intentionally flexible but lacks DB constraints.
- **Severity**: **Medium**
- **Fix direction**:
  - Add a `CHECK` constraint: `(entity_type='equipment' AND equipment_id IS NOT NULL AND supplier_id IS NULL) OR (entity_type='supplier' AND supplier_id IS NOT NULL AND equipment_id IS NULL)`.
  - In services, always set both `entity_type/entity_id` and the matching FK, and validate.
- **How to verify**:
  - Attempt to insert invalid combinations; DB rejects.

---

### 5) Legacy / outdated code and duplication

#### L1) `legacy/` contains large prototype code with conflicting architecture and unsafe capabilities

- **Where**:
  - `legacy/repqms_Proto1_reference.py.py` (very large; includes SMTP/email, psycopg2 direct SQL, additional sync/progress modules)
  - `legacy/repqms_shipstation_sync.py.py` (uses `requests` + raw SQL DDL; different schema than current)
- **Symptom**:
  - Confuses maintainers, introduces copy/paste risk, and includes features explicitly out of scope (email sending) and dependencies not in requirements.
- **Root cause hypothesis**: Historical reference files carried forward.
- **Severity**: **High** (maintenance + accidental reintroduction of unsafe behavior)
- **Fix direction**:
  - **Quarantine**: move to `legacy/_archive/` and add a README stating “not imported, not supported”.
  - Or **delete** if no longer needed.
- **How to verify**:
  - `rg`/imports show no code path depends on these files; application still runs.

#### L2) Drift-fix migrations are duplicated and overlapping

- **Where**:
  - `migrations/versions/7f9a...` adds external_key + shipstation tables
  - `8b1c...` re-adds external_key + generated_by_user_id
  - `9c0d...` adds filters_json + shipstation metrics columns
  - `a1b2c...` “complete drift fix” adds multiple possibly duplicated columns, and does not downgrade
- **Symptom**:
  - Upgrade path is harder to reason about; risk of divergent schema across environments.
- **Root cause hypothesis**: Production drift required emergency additive migrations.
- **Severity**: **Medium/High**
- **Fix direction**:
  - Add a short `docs/` note describing the drift-migration sequence and when each is safe.
  - In the long run, consider squashing drift fixes into a single well-documented migration on a stable release boundary (planning-level item).
- **How to verify**:
  - Spin up a DB from `56a470...` and upgrade to head; ensure no exceptions.

#### L3) Optional import tooling depends on unpinned/absent dependencies

- **Where**: `scripts/import_equipment_and_suppliers.py`
- **Symptom**:
  - Running the script fails unless `openpyxl` and `python-docx` are manually installed; not pinned in `requirements.txt`.
- **Root cause hypothesis**: Tooling script is intentionally optional but not clearly separated.
- **Severity**: **Low/Medium**
- **Fix direction**:
  - Add a header note: “Optional tool; requires `pip install openpyxl python-docx`”.
  - Prefer a separate `requirements-tools.txt` (if allowed) or documentation only.
- **How to verify**:
  - Running the script prints clear actionable error messages (it currently does).

---

### 6) Data layer & migration risks

#### D1) Manufacturing migration is not idempotent (unlike recent equipment migration)

- **Where**: `migrations/versions/2b9d749fc12f_add_manufacturing_lots_tables.py`
- **Symptom**:
  - If applied to a DB that already has some tables (partial deploy), it will fail with “table already exists”.
- **Root cause hypothesis**: Migration was written as a standard create-table migration, not a “drift-safe” one.
- **Severity**: **Medium**
- **Fix direction**:
  - Either accept strictness (preferred for clean DBs) and document it, or add inspector existence checks for parity with other drift-safe migrations.
- **How to verify**:
  - Apply migrations on a DB that already contains manufacturing tables; confirm behavior matches intended policy.

#### D2) Schema drift strategy mixes “model constraints” and “drift-safe nullable columns”

- **Where**:
  - Models declare many columns non-null (e.g., `TracingReport.report_storage_key`), but drift migrations add them nullable for safety (`a1b2c...`)
  - Runtime guardrail checks only a subset of required columns (`app/eqms/__init__.py::_schema_health_guardrail`)
- **Symptom**:
  - Old rows may remain with NULLs; code that assumes non-null can crash later (especially download handlers).
- **Root cause hypothesis**: Emergency migrations favored availability over strictness.
- **Severity**: **Medium**
- **Fix direction**:
  - Add a one-time data backfill migration (or admin script) to populate required fields / mark rows invalid.
  - Expand `_schema_health_guardrail` checks for the columns that are truly required for runtime.
- **How to verify**:
  - Create a DB missing those columns/values and confirm guardrail blocks admin routes with `schema_out_of_date.html`.

#### D3) Distribution idempotency relies on unique index with NULL external_key behavior (DB-specific nuances)

- **Where**:
  - `distribution_log_entries` unique index: `(source, external_key)` (`app/eqms/modules/rep_traceability/models.py`, migration `7f9a...`)
- **Symptom**:
  - Uniqueness semantics for NULL vary across databases (Postgres allows multiple NULLs; SQLite too). That’s intended, but needs to be explicit.
- **Root cause hypothesis**: Using NULL external_key for manual/csv, set external_key for shipstation.
- **Severity**: **Low** (likely acceptable)
- **Fix direction**:
  - Ensure ShipStation always sets external_key and source='shipstation' to benefit from idempotency.
- **How to verify**:
  - Run ShipStation sync twice; second run produces only skipped duplicates and no new inserts.

---

### 7) Storage & document management risks

#### S1) Manufacturing storage integration is broken (see Blocker B1)

This is the top storage risk.

#### S2) Storage key sanitization is inconsistent; risk of path/key abuse in local backend

- **Where**:
  - Local storage maps keys to filesystem paths without removing `..` segments (`app/eqms/storage.py::LocalStorage._path`)
  - Manufacturing key builder does not remove `..` (`app/eqms/modules/manufacturing/service.py::build_lot_document_storage_key`)
  - Equipment key builder only replaces slashes (`app/eqms/modules/equipment/service.py::build_equipment_storage_key`)
  - Document Control key includes doc_number (less sanitized) (`app/eqms/modules/document_control/admin.py::upload_file`)
- **Symptom**:
  - In local backend, a maliciously crafted identifier might create confusing paths or attempt traversal (depending on OS path semantics).
- **Root cause hypothesis**: Keys are assumed to be “safe because internal”.
- **Severity**: **Medium** (especially if any identifier can be user-entered)
- **Fix direction**:
  - Normalize path segments via `secure_filename` for all user-entered identifiers used in keys (doc_number, lot_number, equip_code).
  - Add a defensive check in `LocalStorage._path`: reject keys containing `..` path parts.
- **How to verify**:
  - Attempt to upload a file where lot_number contains `../`; ensure stored key/path is safe and contained under storage root.

#### S3) No file size limits / content-type validation beyond trusting browser MIME type

- **Where**: multiple upload routes use `f.read()` with no size cap (`document_control`, `rep_traceability`, `equipment`, `suppliers`, `manufacturing`)
- **Symptom**:
  - Memory pressure / DoS risk; large uploads could crash workers.
- **Severity**: **Medium**
- **Fix direction**:
  - Set Flask `MAX_CONTENT_LENGTH` (config-level) and add user-friendly flash message on 413.
  - Optionally restrict allowed extensions per module (e.g. `.eml` only for approvals).
- **How to verify**:
  - Upload a file over limit; receives 413 and UI displays a clear error.

---

### 8) Performance / reliability issues

- **ShipStation sync in-request** (see F4) is the dominant reliability concern.
- **Unpaginated lists** for Equipment/Suppliers (see F3).
- **Schema health guardrail caches results in `app.config`** and runs only once per process; if DB schema changes during runtime, the process won’t re-check until restart (`app/eqms/__init__.py`). This is likely acceptable but should be understood.
- **Local storage root depends on cwd** (see snapshot); in multi-worker deployments, ensure all workers share the same cwd and storage volume.

---

### 9) Security issues

#### Sec1) CSRF protection absent across admin

- **Where**: all POST forms/routes; no CSRF tokens in templates; no CSRF middleware configured.
- **Symptom**: A logged-in admin could be tricked into submitting destructive POSTs (delete docs, run ShipStation sync, etc.) via cross-site requests.
- **Severity**: **High**
- **Fix direction**:
  - Introduce a minimal CSRF token strategy (even without dependencies): store a per-session token and require it in POST forms.
  - Alternatively, add Flask-WTF CSRF (adds dependency; weigh carefully).
- **How to verify**:
  - POST without token fails; valid token succeeds.

#### Sec2) Cookie security hardening incomplete for production

- **Where**: `app/eqms/config.py` sets `SESSION_COOKIE_HTTPONLY` and `SAMESITE=Lax` but not `SESSION_COOKIE_SECURE`.
- **Symptom**: Session cookie could be sent over HTTP if misconfigured proxy/SSL termination occurs.
- **Severity**: **Medium**
- **Fix direction**:
  - Set `SESSION_COOKIE_SECURE=True` when `ENV=production`.
- **How to verify**:
  - In production, cookie has `Secure` flag.

#### Sec3) ShipStation diagnostics endpoint may expose sensitive operational data

- **Where**: `app/eqms/modules/shipstation_sync/admin.py::shipstation_diag`
- **Symptom**: Shows internal notes and partial order data; if permissions are mis-assigned, could leak PII.
- **Severity**: **Medium**
- **Fix direction**:
  - Keep behind strict permission (already `shipstation.view`), and consider trimming payload further or masking.
- **How to verify**:
  - Unauthorized users cannot access; audit logs show access patterns.

---

### 10) Prioritized remediation backlog

| ID | Issue | Severity | Effort (S/M/L) | Recommended owner (Dev / Plan / Both) | Dependencies | Verification steps |
|---:|---|---|---|---|---|---|
| 1 | Fix Manufacturing storage API mismatch (`storage_from_config`, `put/get` vs `put_bytes/open`) | Blocker | S | Dev | None | Create lot → upload doc → download doc (200); run new pytest slice |
| 2 | Add CSRF protection for admin POST routes | High | M | Both | Decide approach (custom token vs Flask-WTF) | POST without token fails; with token succeeds |
| 3 | Update README/runbook to match migrations reality (toggle disabled; use release step) | High | S | Plan | None | Docs updated; deploy checklist validated |
| 4 | Normalize Manufacturing flash categories or add CSS support for `error/warning` | High | S | Dev | None | Trigger errors and confirm consistent styling |
| 5 | Add pagination to Equipment/Suppliers list routes | Medium | S | Dev | None | 1k rows; list paginates and stays responsive |
| 6 | Harden storage key/path sanitization (reject `..`; secure_filename on identifiers) | Medium | M | Dev | None | Attempt traversal inputs; keys remain safe |
| 7 | Add ManagedDocument integrity constraints (entity_type ↔ FK coherence) | Medium | M | Both | Migration policy decision | Invalid combinations rejected; existing data migrated cleanly |
| 8 | Add manufacturing + equipment/suppliers pytest coverage (vertical slices) | Medium | M | Dev | None | `pytest -q` includes new tests; green |
| 9 | ShipStation sync reliability: time budget + max pages/orders env knobs | Medium | S | Dev | None | Sync respects configured limits; no timeouts |
| 10 | Quarantine/delete legacy proto files under `legacy/` | High | S | Both | Confirm no imports | App runs; searches show no references |
| 11 | Consolidate/clarify drift migrations (document the sequence; reduce overlap) | Medium | M | Plan | None | New doc explains upgrade path; smoke upgrade passes |
| 12 | Production cookie hardening (`SESSION_COOKIE_SECURE`) | Medium | S | Dev | ENV detection | Cookies in prod have Secure flag |

---

### 11) “Fast wins” patch set

Small, safe edits to stabilize the system quickly:

1. **Manufacturing storage fixes**:
   - Update `app/eqms/modules/manufacturing/admin.py` to use `storage_from_config(current_app.config)` and `send_file(storage.open(...))`.
   - Update `app/eqms/modules/manufacturing/service.py` to use `storage_from_config(current_app.config)` and `put_bytes`.
2. **Flash category normalization**:
   - Replace `flash(..., "error")` with `flash(..., "danger")` and `warning` with `danger` (or add CSS class).
3. **Remove duplicate Manufacturing card**:
   - Edit `app/eqms/templates/admin/index.html` to remove `admin.module_stub` manufacturing card.
4. **LocalStorage path hardening**:
   - In `app/eqms/storage.py::LocalStorage._path`, reject keys containing `..` path parts.
5. **Identifier sanitization for storage keys**:
   - Apply `secure_filename` (or strict allowlist) to `doc_number`, `lot_number`, `equip_code` segments used in storage keys.
6. **Set `SESSION_COOKIE_SECURE` in production**:
   - In `app/eqms/config.py`, set `SESSION_COOKIE_SECURE=True` when `ENV=production`.
7. **Add `MAX_CONTENT_LENGTH`**:
   - In `app/eqms/config.py`, set a reasonable limit (e.g. 25MB) and handle 413 with a friendly error page/flash.
8. **ShipStation sync hard limits**:
   - Add env-driven caps (`SHIPSTATION_MAX_PAGES`, `SHIPSTATION_MAX_ORDERS`) in `shipstation_sync/service.py`.
9. **Quarantine legacy code**:
   - Move `legacy/*.py.py` into a clearly named archive folder with a `README` warning.
10. **Add missing tests**:
   - New tests: `tests/test_equipment.py`, `tests/test_suppliers.py`, `tests/test_manufacturing.py` (basic create + upload/download + audit).

---

### Optional: suggested pytest targets + minimal smoke matrix

Suggested targets (existing):
- `pytest -q tests/test_smoke.py`
- `pytest -q tests/test_document_control.py`
- `pytest -q tests/test_rep_traceability.py`

Minimal smoke matrix for `/admin/*` routes (admin user):
- `/admin/` loads
- `/admin/audit` loads
- `/admin/modules/document-control/` list loads; create doc; upload; release; download
- `/admin/distribution-log` list loads; create; import CSV; export CSV
- `/admin/tracing` list loads; generate; download; upload `.eml`; download `.eml`
- `/admin/customers` list loads; create; edit; add note
- `/admin/equipment` list loads; create; upload doc; download doc
- `/admin/suppliers` list loads; create; upload doc; download doc
- `/admin/manufacturing/suspension` list loads; create lot; upload doc; download doc; status transition
- `/admin/shipstation` loads (even without API creds; should show a friendly error or disabled state); `/admin/shipstation/run` handles missing creds gracefully

