# Step 1 REP Migration Checklist

**Date:** 2026-01-15  
**Purpose:** Dependency-ordered task checklist for migrating essential Rep QMS subset (Distribution Log + Tracing Reports + Approval Evidence .eml) into SilqeQMS

---

## Scope

**P0 (Must Have):**
- Distribution Log: browse, edit, manual entry, CSV import/export
- Tracing Reports: generate CSV from Distribution Log, store immutable artifacts with metadata
- Approval Evidence: upload .eml files, link to tracing reports

**P1 (Deferred to Later):**
- ShipStation sync import
- PDF import
- Advanced filters beyond UI map basics

---

## Database & Migrations

### Task 1.1: Create Alembic Migration for REP Tables

**Files Touched:**
- `migrations/versions/<revision>_add_rep_traceability_tables.py` (new file)

**Steps:**
1. Run `alembic revision -m "add rep traceability tables"`
2. Implement `upgrade()` with:
   - `distribution_log_entries` table (from `REP_SYSTEM_MINIMAL_SCHEMA.md`)
   - `tracing_reports` table
   - `approvals_eml` table
   - Indexes as specified in schema doc
3. Implement `downgrade()` to drop tables

**Acceptance Test:**
- `alembic upgrade head` runs without errors
- `alembic downgrade -1` runs without errors
- All three tables exist with correct columns and constraints
- Indexes are created

**Definition of Done:**
- Migration file created and tested
- Schema matches `REP_SYSTEM_MINIMAL_SCHEMA.md` exactly (Postgres-compatible, works on SQLite via `render_as_batch`)

---

### Task 1.2: Update Models for Alembic Autogenerate

**Files Touched:**
- `app/eqms/modules/rep_traceability/models.py` (new file)
- `app/eqms/models.py` (add import at bottom)

**Steps:**
1. Create `app/eqms/modules/rep_traceability/__init__.py`
2. Create `app/eqms/modules/rep_traceability/models.py` with SQLAlchemy models:
   - `DistributionLogEntry`
   - `TracingReport`
   - `ApprovalEml`
3. Import models in `app/eqms/models.py` tail: `from app.eqms.modules.rep_traceability.models import DistributionLogEntry, TracingReport, ApprovalEml`

**Acceptance Test:**
- Models import without errors
- `alembic revision --autogenerate -m "check"` detects no differences (schema matches migration)

**Definition of Done:**
- Models exist and match table schemas exactly
- Import chain ensures Alembic sees all tables

---

### Task 1.3: Extend Seed Script with REP Permissions & Roles

**Files Touched:**
- `scripts/init_db.py`

**Steps:**
1. Add permission creation for:
   - `distribution_log.view`, `distribution_log.create`, `distribution_log.edit`, `distribution_log.delete`, `distribution_log.export`
   - `tracing_reports.view`, `tracing_reports.generate`, `tracing_reports.download`
   - `approvals.view`, `approvals.upload`
2. Ensure `admin` role gets all REP permissions
3. Optionally create `quality`, `ops`, `readonly` roles per UI map and grant appropriate permissions:
   - `quality`: all REP permissions (same as admin)
   - `ops`: all REP permissions except user management
   - `readonly`: `distribution_log.view`, `tracing_reports.view`, `tracing_reports.download`, `approvals.view`

**Acceptance Test:**
- Run `python scripts/init_db.py`
- Check database: all permissions exist
- Check `admin` role has all REP permissions
- Verify role/permission mappings match UI map

**Definition of Done:**
- All REP permission keys seeded
- `admin` role has full access
- Optional roles created if implemented (quality/ops/readonly)

---

## Distribution Log Module

### Task 2.1: Create Distribution Log Models

**Files Touched:**
- `app/eqms/modules/rep_traceability/models.py` (from Task 1.2)

**Acceptance Test:**
- Model `DistributionLogEntry` has all required fields from schema
- Relationships work: `rep_id` → `users.id`, `customer_id` → `customers.id` (nullable)
- Constraints: SKU CHECK, lot_number CHECK, quantity CHECK, source CHECK

**Definition of Done:**
- Model matches `REP_SYSTEM_MINIMAL_SCHEMA.md` `distribution_log_entries` table exactly

---

### Task 2.2: Create Distribution Log Service Functions

**Files Touched:**
- `app/eqms/modules/rep_traceability/service.py` (new file)

**Steps:**
1. Create validation functions:
   - `validate_sku(sku: str) -> bool`
   - `validate_lot_number(lot: str) -> bool`
   - `validate_quantity(qty: int) -> bool`
   - `validate_ship_date(date: date) -> bool`
2. Create deduplication helpers:
   - `check_duplicate_shipstation(session, ss_shipment_id: str) -> DistributionLogEntry | None`
   - `check_duplicate_manual_csv(session, order_number: str, ship_date: date, facility_name: str) -> DistributionLogEntry | None`
3. Create CRUD helpers:
   - `create_distribution_entry(session, data: dict, user: User) -> DistributionLogEntry`
   - `update_distribution_entry(session, entry_id: int, data: dict, user: User) -> DistributionLogEntry`
   - `delete_distribution_entry(session, entry_id: int, user: User) -> None`

**Acceptance Test:**
- Validation functions reject invalid inputs correctly
- Deduplication detects existing ShipStation orders
- CRUD helpers create/update/delete entries and log audit events

**Definition of Done:**
- All service functions implemented and tested manually
- Audit logging via `record_event()` on create/update/delete

---

### Task 2.3: Create CSV Parser for Distribution Log Import

**Files Touched:**
- `app/eqms/modules/rep_traceability/parsers/__init__.py` (new file)
- `app/eqms/modules/rep_traceability/parsers/csv.py` (new file)

**Steps:**
1. Implement `parse_distribution_csv(file_bytes: bytes) -> list[dict]`
2. Map CSV columns to `distribution_log_entries` fields:
   - Ship Date → `ship_date`
   - Order Number → `order_number`
   - Facility Name → `facility_name`
   - SKU → `sku`
   - Lot → `lot_number`
   - Quantity → `quantity`
   - Optional: Address, City, State, Zip, Contact info, Tracking number
3. Validate each row (SKU, lot format, quantity, date)
4. Return list of normalized dicts, with error list for invalid rows

**Acceptance Test:**
- Parse valid CSV file: returns list of dicts
- Invalid rows: returns error list with row numbers
- Missing required columns: raises clear error
- Handles empty rows gracefully

**Definition of Done:**
- CSV parser extracts all required fields
- Validation errors reported clearly
- Returns data ready for `create_distribution_entry()`

---

### Task 2.4: Create Distribution Log Routes (List, Manual Entry, Edit, Export)

**Files Touched:**
- `app/eqms/modules/rep_traceability/admin.py` (new file)

**Routes:**
- `GET /admin/distribution-log` → `list_distributions()` (with filters: date range, source, rep, customer, SKU)
- `POST /admin/distribution-log/manual-entry` → `create_manual_entry()`
- `GET /admin/distribution-log/<id>/edit` → `edit_distribution_form()`
- `POST /admin/distribution-log/<id>/edit` → `update_distribution()` (requires reason-for-change)
- `GET /admin/distribution-log/export` → `export_csv()` (filtered view)

**Permissions:**
- List: `distribution_log.view`
- Create: `distribution_log.create`
- Edit: `distribution_log.edit`
- Delete: `distribution_log.delete` (if implemented)
- Export: `distribution_log.export`

**Acceptance Test:**
- List page shows distributions with pagination
- Filters work: date range, source, rep, customer, SKU
- Manual entry form creates entry and redirects to list
- Edit form loads entry, updates save changes with audit log
- Export downloads CSV with filtered results

**Definition of Done:**
- All routes implemented with RBAC decorators
- Forms validate inputs using service functions
- Audit events logged on create/update/delete
- Export generates valid CSV matching Distribution Log columns

---

### Task 2.5: Create Distribution Log Import Routes (CSV)

**Files Touched:**
- `app/eqms/modules/rep_traceability/admin.py` (add routes)

**Routes:**
- `GET /admin/distribution-log/import-csv` → `import_csv_form()`
- `POST /admin/distribution-log/import-csv` → `import_csv_post()`

**Steps:**
1. Upload CSV file via form
2. Parse CSV using `parse_distribution_csv()`
3. For each row: create entry via `create_distribution_entry()` (handle duplicates: warn, allow override)
4. Display import results: success count, errors, duplicates

**Acceptance Test:**
- Upload valid CSV: entries created, success message shown
- Upload CSV with errors: error list displayed, valid rows imported
- Upload CSV with duplicates: warning shown, option to override

**Definition of Done:**
- CSV import route works end-to-end
- Error handling clear for users
- Duplicates handled gracefully

---

### Task 2.6: Create Distribution Log Templates

**Files Touched:**
- `app/eqms/templates/admin/distribution_log/list.html` (new file)
- `app/eqms/templates/admin/distribution_log/edit.html` (new file)
- `app/eqms/templates/admin/distribution_log/import.html` (new file)

**Requirements:**
- Reuse `_layout.html` base template
- Use existing design system (`design-system.css`)
- List: table with filters, pagination, actions
- Edit: form with all fields from schema (required/optional marked)
- Import: file upload form, results display

**Acceptance Test:**
- Templates render without errors
- Forms submit correctly
- Filters work via query params
- UI matches existing admin pages style

**Definition of Done:**
- All templates created and functional
- Consistent with existing admin UI patterns

---

## Tracing Reports Module

### Task 3.1: Create Tracing Report Models

**Files Touched:**
- `app/eqms/modules/rep_traceability/models.py` (add `TracingReport` model)

**Acceptance Test:**
- Model `TracingReport` has all fields from schema
- `filters_json` is JSONB-compatible (or JSON on SQLite)
- Relationships work: `generated_by_user_id` → `users.id`

**Definition of Done:**
- Model matches `REP_SYSTEM_MINIMAL_SCHEMA.md` `tracing_reports` table exactly

---

### Task 3.2: Create Tracing Report Generation Service

**Files Touched:**
- `app/eqms/modules/rep_traceability/service.py` (add functions)

**Functions:**
- `generate_tracing_report_csv(session, filters: dict, user: User) -> tuple[bytes, str]`
  - Query `distribution_log_entries` with filters
  - Filter by month (required), rep (optional), source (optional), SKU (optional), customer (optional)
  - Flatten to one row per SKU/Lot combination
  - Sort by ship_date ASC
  - Generate CSV bytes with columns: Ship Date, Order #, Facility, City, State, SKU, Lot, Quantity, Rep, Source
  - Generate storage key: `tracing_reports/{month}/{filters_hash}_{generated_at_iso}.csv`
  - Store CSV via `storage.put_bytes()`
  - Create `TracingReport` metadata record
  - Return (csv_bytes, storage_key)

**Acceptance Test:**
- Generate report with month filter: CSV created and stored
- Filters work correctly: rep, source, SKU, customer
- CSV format correct: header row, sorted by date
- Metadata record created with correct filters_json

**Definition of Done:**
- Report generation creates immutable CSV artifact
- Storage key follows versioned path convention
- Metadata links to artifact correctly

---

### Task 3.3: Create Tracing Report Routes (List, Generate, Download)

**Files Touched:**
- `app/eqms/modules/rep_traceability/admin.py` (add routes)

**Routes:**
- `GET /admin/tracing` → `list_tracing_reports()`
- `POST /admin/tracing/generate` → `generate_report()`
- `GET /admin/tracing/<id>` → `tracing_report_detail()`
- `GET /admin/tracing/<id>/download` → `download_report()`

**Permissions:**
- List: `tracing_reports.view`
- Generate: `tracing_reports.generate`
- Download: `tracing_reports.download`

**Acceptance Test:**
- List page shows generated reports with filters/status
- Generate form accepts filters, creates report, redirects to detail
- Detail page shows report metadata, download link, approval section
- Download returns CSV file with correct filename

**Definition of Done:**
- All routes implemented with RBAC
- Report generation triggers artifact storage
- Download reads from storage abstraction (local or S3)

---

### Task 3.4: Create Tracing Report Templates

**Files Touched:**
- `app/eqms/templates/admin/tracing/list.html` (new file)
- `app/eqms/templates/admin/tracing/generate.html` (new file)
- `app/eqms/templates/admin/tracing/detail.html` (new file)

**Requirements:**
- List: table of reports with generated_at, filters summary, status, actions
- Generate: form with month (required), rep, source, SKU, customer (optional)
- Detail: report metadata, download button, approval evidence section (from Task 4.x)

**Acceptance Test:**
- Templates render correctly
- Generate form validates month format (YYYY-MM)
- Detail page shows report info and approval upload form

**Definition of Done:**
- All templates created and functional

---

## Approval Evidence (.eml Upload) Module

### Task 4.1: Create Approval EML Models

**Files Touched:**
- `app/eqms/modules/rep_traceability/models.py` (add `ApprovalEml` model)

**Acceptance Test:**
- Model `ApprovalEml` has all fields from schema
- Relationship works: `report_id` → `tracing_reports.id` (CASCADE delete)
- Relationship works: `uploaded_by_user_id` → `users.id`

**Definition of Done:**
- Model matches `REP_SYSTEM_MINIMAL_SCHEMA.md` `approvals_eml` table exactly

---

### Task 4.2: Create .eml Parser Service

**Files Touched:**
- `app/eqms/modules/rep_traceability/service.py` (add functions)

**Functions:**
- `parse_eml_headers(eml_bytes: bytes) -> dict`
  - Use Python `email.parser.BytesParser` to parse .eml file
  - Extract headers only: `subject`, `from`, `to`, `date`
  - Parse `date` to ISO format (or None if invalid)
  - Extract first email address from `from` and `to` headers
  - Return dict: `{subject, from_email, to_email, email_date}`

**Acceptance Test:**
- Parse valid .eml file: extracts subject, from, to, date
- Invalid .eml: handles gracefully (returns None for missing fields)
- Date parsing works: converts email Date header to ISO

**Definition of Done:**
- .eml parser extracts metadata from headers only (no body/attachments)

---

### Task 4.3: Create Approval Upload Service

**Files Touched:**
- `app/eqms/modules/rep_traceability/service.py` (add functions)

**Functions:**
- `upload_approval_eml(session, report_id: int, eml_bytes: bytes, filename: str, user: User, notes: str | None = None) -> ApprovalEml`
  - Parse .eml headers via `parse_eml_headers()`
  - Generate storage key: `approvals/{report_id}/{uploaded_at_iso}_{sanitized_subject}.eml`
  - Sanitize subject: remove special chars, limit to 100 chars
  - Store .eml file via `storage.put_bytes()`
  - Create `ApprovalEml` record with metadata
  - Log audit event: `approvals.upload`
  - Return `ApprovalEml` record

**Acceptance Test:**
- Upload .eml file: stored in storage, metadata record created
- Storage key follows convention
- Audit event logged
- Link to report works correctly

**Definition of Done:**
- Upload service stores .eml files immutably
- Metadata extracted and stored
- Audit trail complete

---

### Task 4.4: Create Approval Upload Routes

**Files Touched:**
- `app/eqms/modules/rep_traceability/admin.py` (add routes)

**Routes:**
- `POST /admin/tracing/<report_id>/upload-approval` → `upload_approval_eml()`
- `GET /admin/approvals/<id>/download` → `download_approval_eml()`

**Permissions:**
- Upload: `approvals.upload`
- Download: `approvals.view` (or inherit from tracing_reports.view)

**Acceptance Test:**
- Upload form submits .eml file, redirects to report detail
- Approval appears in "Uploaded Approvals" list on report detail page
- Download returns .eml file with correct filename

**Definition of Done:**
- Upload route stores .eml and links to report
- Download route reads from storage abstraction
- Approval list displays on report detail page

---

### Task 4.5: Update Tracing Report Detail Template with Approval Section

**Files Touched:**
- `app/eqms/templates/admin/tracing/detail.html` (update from Task 3.4)

**Requirements:**
- Add "Approval Evidence" section
- File upload form for .eml
- List of uploaded approvals with download links, metadata (subject, from, uploaded_at)

**Acceptance Test:**
- Approval section renders on report detail page
- Upload form works
- Approval list shows all approvals for report

**Definition of Done:**
- Approval UI integrated into report detail page

---

## Blueprint Registration & Navigation

### Task 5.1: Register REP Traceability Blueprint

**Files Touched:**
- `app/eqms/__init__.py`

**Steps:**
1. Import: `from app.eqms.modules.rep_traceability.admin import bp as rep_traceability_bp`
2. Register: `app.register_blueprint(rep_traceability_bp, url_prefix="/admin")`

**Note:** Routes in blueprint are already prefixed (e.g., `/distribution-log`, `/tracing`), so final URLs are `/admin/distribution-log`, `/admin/tracing`, etc.

**Acceptance Test:**
- Blueprint registered without errors
- Routes accessible at `/admin/distribution-log`, `/admin/tracing`, etc.

**Definition of Done:**
- Blueprint registered in app factory
- All routes accessible

---

### Task 5.2: Update Admin Navigation Menu

**Files Touched:**
- `app/eqms/templates/_layout.html` (or `admin/index.html` if navigation is there)

**Steps:**
1. Add menu items:
   - "Distribution Log" → `/admin/distribution-log`
   - "Tracing Reports" → `/admin/tracing`

**Acceptance Test:**
- Navigation menu shows new items
- Links work correctly

**Definition of Done:**
- Navigation updated to include REP modules

---

## Integration & Testing

### Task 6.1: End-to-End Manual Test (Distribution Log)

**Acceptance Test:**
1. Login as admin
2. Navigate to `/admin/distribution-log`
3. Create manual entry: fill form, submit
4. Entry appears in list
5. Edit entry: change quantity, save with reason
6. Export CSV: download, verify format
7. Import CSV: upload file, verify entries created

**Definition of Done:**
- Full workflow works without errors
- Audit events logged for all actions

---

### Task 6.2: End-to-End Manual Test (Tracing Reports)

**Acceptance Test:**
1. Navigate to `/admin/tracing`
2. Generate report: select month, filters, submit
3. Report appears in list
4. View report detail: metadata, download link
5. Download CSV: verify format and data

**Definition of Done:**
- Report generation works end-to-end
- CSV artifact stored and downloadable

---

### Task 6.3: End-to-End Manual Test (Approval Evidence)

**Acceptance Test:**
1. Open tracing report detail page
2. Upload .eml file: choose file, submit
3. Approval appears in list
4. Download approval: verify .eml file downloads correctly
5. Open .eml in email client: verify it opens

**Definition of Done:**
- .eml upload and download work end-to-end
- Approval linked to report correctly

---

## P1 Tasks (Deferred - Not in Step 1)

- **PDF Import**: Implement `parse_distribution_pdf()` in `parsers/pdf.py`, add route `POST /admin/distribution-log/import-pdf`
- **ShipStation Sync**: Create background job/sync script, import via same `distribution_log_entries` table
- **Advanced Filters**: Full-text search, complex queries beyond basic dropdowns
- **Retention Policies**: Cleanup old tracing reports (keep last 12 months, archive older)

---

## Notes

- **No rep pages**: All functionality under `/admin/*` only
- **No email sending**: Approvals are .eml uploads only
- **Audit trail**: All create/update/delete actions must log via `record_event()`
- **Reason-for-change**: Required for edit/delete operations (form field)
- **Storage abstraction**: Use `storage_from_config()` for local dev + S3-compatible production
- **Database**: SQLite for dev (via `render_as_batch`), Postgres-compatible schema for production
