# Rep QMS Migration Master Specification

**Date:** 2025-01-XX  
**Lead Agent:** Refactoring Team  
**Purpose:** Complete inventory and migration plan for porting essential Rep QMS functionality into SilqeQMS (clean eQMS starter)

---

## Executive Summary

This document specifies the migration of essential Rep QMS functionality from the current bloated system (`Proto1.py`) into the new SilqeQMS codebase. The migration focuses on three core features: **Distribution Log**, **Tracing Reports**, and **Approval Evidence (.eml uploads)**. All rep-specific pages and email-sending functionality are explicitly excluded.

### Essential Subset (What We Are Porting)

1. **Distribution Log** (P0 - must-have)
   - Ingest: ShipStation sync, CSV import, manual entry, PDF imports
   - View/edit/export capabilities
   - Required columns: Ship Date, Order #, Facility, Rep, SKU, Lot, Quantity, Source
   - Audit trail (who created/modified, when)

2. **Tracing Reports** (P0 - must-have)
   - Generate from Distribution Log only
   - Filters: rep, ShipStation/manual source, month, SKU, customer
   - Format: CSV (minimal, no PDF)
   - Immutable once generated (versioned storage)

3. **Approval Evidence** (P0 - must-have)
   - Upload .eml files as proof of approval
   - Link to specific tracing report version
   - Store with metadata: who uploaded, date, subject/from/to
   - Minimal parsing (basic header extraction)

### Explicit Exclusions

- **Rep Pages**: No `/rep/<slug>` routes, no rep-specific folders, no rep dashboards, no rep navigation
- **Email Sending**: No SMTP code, no email dispatch functions, no automatic email generation
- **Analytics/Stats**: No heavy dashboards, no complex aggregations beyond basic counts
- **Rep Workflows**: No rep login/logout, no rep document uploads, no rep-facing UI

---

## Data Sources & Truth Hierarchy

### Current Source of Truth

**Primary:** `devices_distributed` and `device_distribution_records` tables in PostgreSQL

- `devices_distributed`: One row per shipment/order
  - Key columns: `id`, `order_number`, `ship_date`, `rep_id`, `customer_id`, `source` ('shipstation', 'manual', 'csv_import')
  - `ss_shipment_id`: Unique identifier from ShipStation (if source='shipstation')

- `device_distribution_records`: One row per SKU/Lot combination per distribution
  - Key columns: `dist_id` (FK), `stored_filename`, `fields_json` (canonical fields), `uploaded_at`
  - `fields_json` contains: Facility Name, SKU, Lot, Quantity, Address, Contact info

**Secondary Sources:**
- ShipStation API export (sync creates `devices_distributed` records)
- CSV imports (admin uploads "Distribution Log (distributions).csv")
- PDF imports (master sales order PDFs, label bulk PDFs)
- Manual entry (admin creates via form)

### New Source of Truth (After Migration)

**Distribution Log** remains the single source of truth:
- All distributions stored in normalized `distribution_log_entries` table
- ShipStation sync continues to create entries (but via new system's import pipeline)
- Manual entry, CSV, PDF imports all write to same table
- Tracing reports generated on-demand from this table (never stored separately, only generated artifacts)

**Tracing Reports** become generated artifacts:
- Not stored in DB (only metadata)
- Generated on-demand from Distribution Log with filters
- Stored as immutable files (versioned by generation timestamp)
- Approval .eml files stored separately, linked by report version ID

---

## Essential Features (Ranked)

### P0 - Must Have (Core Workflow)

#### 1. Distribution Log

**Function:** Chronological record of all device distributions with full audit trail

**What it does:**
- Stores every shipment of devices to facilities
- Tracks: ship date, order number, facility, rep assignment, SKU/lot/quantity, source
- Supports multiple ingestion methods: ShipStation sync, CSV import, manual entry, PDF parsing

**Data it requires:**
- Input sources:
  - ShipStation API export (order data, tracking, shipment IDs)
  - CSV files (structured distribution log exports)
  - PDF files (sales order PDFs, shipping label PDFs)
  - Manual form entry (admin-typed data)
- Required fields per entry:
  - Ship Date (YYYY-MM-DD)
  - Order Number (string, can be ShipStation order ID or SO number)
  - Facility Name (string)
  - Rep (FK to users table, via RBAC)
  - SKU (one of: 211810SPT, 211610SPT, 211410SPT)
  - Lot Number (format: SLQ-#####)
  - Quantity (integer)
  - Source ('shipstation', 'manual', 'csv_import', 'pdf_import')
  - Optional: Address, City, State, Zip, Contact info, Tracking number

**What it outputs:**
- Database records in `distribution_log_entries` table
- UI: Browseable/editable list with filters (date range, customer, source, rep)
- Export: CSV download of filtered results
- Audit log entries (who created/modified, when)

**Minimal implementation:**
- Use existing `eqms_starter` auth + RBAC for permissions
- Use existing `eqms_starter/app/eqms/storage.py` for file storage (PDF attachments)
- Use existing `eqms_starter/app/eqms/audit.py` for audit trail
- Single table: `distribution_log_entries` (schema in `REP_SYSTEM_MINIMAL_SCHEMA.md`)
- Single admin route: `/admin/distribution-log` (view/edit/export)
- Import routes: `/admin/distribution-log/import-csv`, `/admin/distribution-log/import-pdf`, `/admin/distribution-log/manual-entry`

**Ingest validation rules:**
- SKU must be one of valid values (211810SPT, 211610SPT, 211410SPT)
- Lot must match pattern `SLQ-\d{5}`
- Quantity must be positive integer
- Ship Date must be valid date (not future)
- Order Number must be unique per source (or auto-generate if missing)

**Deduplication rules:**
- ShipStation: Match on `ss_shipment_id` (unique constraint)
- Manual/CSV: Match on `order_number + ship_date + facility_name` (warn on duplicate, allow override)
- PDF: Match on `order_number` (extracted from PDF header), warn on duplicate

**UI requirements:**
- Upload: File upload form (CSV/PDF), manual entry form
- Browse: Table with pagination, filters (date range, source, rep, customer)
- Edit: Click row → edit form (allow rep reassignment, quantity/lot corrections)
- Export: "Download CSV" button (current filtered view)

**Audit trail requirements:**
- Every insert/update/delete logged via `audit.py`
- Fields: `user_id`, `action` ('create', 'update', 'delete'), `entity_type` ('distribution_log_entry'), `entity_id`, `timestamp`, `changes_json`

---

#### 2. Tracing Reports

**Function:** Generate filtered reports from Distribution Log for regulatory compliance

**What it does:**
- Queries Distribution Log with filters (rep, source, month, SKU, customer)
- Generates CSV file with columns: Ship Date, Order #, Facility, City, State, SKU, Lot, Quantity
- Stores as immutable artifact (versioned by generation timestamp)
- Links approval .eml files to report versions

**Data it requires:**
- Input: Distribution Log entries (filtered by criteria)
- Filters:
  - `rep_id` (optional, FK to users)
  - `source` (optional, 'shipstation' or 'manual' or 'all')
  - `month` (required, YYYY-MM format)
  - `sku` (optional, filter by specific SKU)
  - `customer_id` (optional, FK to customers)

**What it outputs:**
- CSV file (immutable, stored in `storage/` with versioned path)
- Metadata record in `tracing_reports` table:
  - `id`, `generated_at`, `generated_by_user_id`, `filters_json`, `report_storage_key`, `status` ('draft', 'final')

**Minimal implementation:**
- Single route: `/admin/tracing/generate` (POST with filters)
- Query function: `generate_tracing_report(filters: dict) -> (csv_bytes, storage_key)`
- Storage: Use `storage.py` abstraction (local or Spaces)
- Storage key format: `tracing_reports/{month}/{filters_hash}_{timestamp}.csv`
- UI: Form with filter dropdowns/inputs, "Generate Report" button, list of generated reports with download links

**Report format requirements:**
- CSV format (not PDF/HTML, to keep it minimal)
- Columns: `Ship Date`, `Order #`, `Facility`, `City`, `State`, `SKU`, `Lot`, `Quantity`, `Rep`, `Source`
- Sorted by Ship Date (ascending)
- Header row included

**Generation logic:**
1. Query `distribution_log_entries` with filters
2. Group by shipment (order_number + ship_date) if multiple SKUs per order
3. Flatten to one row per SKU/Lot combination
4. Sort by ship_date ASC
5. Write CSV bytes
6. Store via `storage.py` (get storage_key)
7. Insert metadata into `tracing_reports` table

**Storage + versioning:**
- Reports are immutable (never overwrite)
- Each generation creates new file: `{month}/{filters_hash}_{generated_at_iso}.csv`
- `filters_hash`: SHA256 hash of filters_json (ensures same filters = same hash, but different timestamp = different file)
- Old reports kept for audit (cleanup policy: keep last 12 months, archive older)

---

#### 3. Approval Evidence via .eml Upload

**Function:** Upload .eml files as proof of approval for tracing reports

**What it does:**
- Admin uploads .eml file (email export from email client)
- System extracts basic metadata (subject, from, to, date)
- Links .eml file to specific tracing report version
- Stores .eml file in storage (immutable, linked by report_id)

**Data it requires:**
- Input: .eml file upload (multipart/form-data)
- Required fields:
  - `report_id` (FK to tracing_reports.id)
  - `eml_file` (file upload)
  - Optional: `notes` (admin notes about approval)

**What it outputs:**
- Stored .eml file (via `storage.py`)
- Metadata record in `approvals_eml` table:
  - `id`, `report_id`, `uploaded_at`, `uploaded_by_user_id`, `storage_key`, `subject`, `from_email`, `to_email`, `email_date`, `notes`

**Minimal implementation:**
- Single route: `/admin/tracing/<report_id>/upload-approval` (POST)
- File storage: Use `storage.py` (local or Spaces)
- Storage key format: `approvals/{report_id}/{timestamp}_{sanitized_filename}.eml`
- Minimal parsing: Use Python `email.parser` to extract headers (subject, from, to, date)
- No full email parsing (no body extraction, no attachments extraction)
- UI: "Upload Approval" button on tracing report detail page, file upload form, list of uploaded approvals with download links

**Metadata capture:**
- `subject`: Extracted from email header "Subject:"
- `from_email`: Extracted from email header "From:" (first address)
- `to_email`: Extracted from email header "To:" (first address)
- `email_date`: Extracted from email header "Date:" (parsed to ISO format)
- `uploaded_at`: Server timestamp (when file was uploaded)
- `uploaded_by_user_id`: Current user (from auth session)

**Where stored:**
- Storage key: `approvals/{report_id}/{uploaded_at_iso}_{sanitized_subject}.eml`
- Sanitization: Remove special chars, limit length to 100 chars
- Example: `approvals/123/2025-01-15T10-30-00_Approval_Tracing_Report_2025-01.eml`

**How linked:**
- `approvals_eml.report_id` → `tracing_reports.id` (foreign key)
- UI: Tracing report detail page shows "Approval Evidence" section with list of .eml files

**Minimal parsing approach:**
- Use Python standard library: `email.parser.BytesParser`
- Extract headers only (subject, from, to, date)
- Do NOT parse body, do NOT extract attachments
- Store raw .eml file as-is (let users open in email client if needed)

---

### P1 - Important (Supporting Features)

#### 4. ShipStation Sync Import

**Function:** Periodically sync orders from ShipStation API into Distribution Log

**Implementation:**
- Reuse existing `shipstation_sync.py` logic (minimal port)
- Extract: ShipStation API client code, order parsing, distribution record creation
- Run as background job (via cron or admin-triggered sync)
- Import via same `distribution_log_entries` table as manual/CSV imports

**Dependencies:**
- ShipStation API credentials (environment variables)
- Background job runner (use existing system's job queue if available, or simple cron)

---

#### 5. CSV/PDF Import

**Function:** Bulk import distributions from CSV or PDF files

**Implementation:**
- CSV: Simple CSV reader, map columns to `distribution_log_entries` fields
- PDF: Reuse minimal PDF parsing from `Proto1.py` (extract order number, facility, SKU/lot from PDF text)
- Import routes: `/admin/distribution-log/import-csv`, `/admin/distribution-log/import-pdf`
- Validation: Same as manual entry (SKU, lot format, quantity)

---

### P2 - Later (Nice to Have, Not in Initial Migration)

- Advanced search/filtering (full-text search, complex queries)
- Bulk edit operations
- Report templates (custom CSV formats)
- Automated report generation (scheduled monthly reports)

---

## Non-Goals / Explicitly Excluded

1. **Rep Pages**: No `/rep/<slug>` routes, no rep-specific folders, no rep dashboards, no rep login/logout
2. **Email Sending**: No SMTP code, no `send_email()` functions, no automatic email generation
3. **Analytics Dashboards**: No stats-heavy pages, no charts/graphs (beyond basic counts)
4. **Rep Workflows**: No rep-facing UI, no rep document uploads, no rep-specific features
5. **Complex Parsing**: No full email body parsing, no attachment extraction from .eml files
6. **PDF Report Generation**: No PDF generation (CSV only for tracing reports)

---

## Migration Mapping

### Old Files/Modules → New Location

#### Distribution Log

**Old:** `Proto1.py` routes:
- `/admin/distribution-log` (line ~5385)
- `/admin/manual-distribution-entry` (line ~6026)
- `/admin/distributions/<id>/edit` (line ~6256)
- `/admin/import-csv` (line ~4455)
- `/admin/distribution-records/import-master` (line ~6886)

**New:** `eqms_starter/app/eqms/routes.py`
- Module: `distribution_log` (new module)
- Routes:
  - `GET /admin/distribution-log` → `distribution_log.list()`
  - `POST /admin/distribution-log/manual-entry` → `distribution_log.create_manual()`
  - `GET /admin/distribution-log/<id>/edit` → `distribution_log.edit_form()`
  - `POST /admin/distribution-log/<id>/edit` → `distribution_log.update()`
  - `POST /admin/distribution-log/import-csv` → `distribution_log.import_csv()`
  - `POST /admin/distribution-log/import-pdf` → `distribution_log.import_pdf()`
  - `GET /admin/distribution-log/export` → `distribution_log.export_csv()`

**Reusable code:**
- `fetch_distribution_records()` function (normalization logic) → Port as `distribution_log/normalize.py`
- `_build_distributions()` grouping logic → Port as `distribution_log/grouping.py`
- CSV parsing (from `admin_import_csv`) → Port as `distribution_log/parsers/csv.py`
- PDF parsing (from `_run_master_salesorder_import_from_pdf_path`) → Port as `distribution_log/parsers/pdf.py`

**Rewrite recommended:**
- Template rendering (use new system's template structure)
- Form handling (use new system's form patterns)

---

#### Tracing Reports

**Old:** `Proto1.py` routes:
- `/admin/tracing` (line ~9394)
- `/admin/tracing/generate/<month>` (line ~9153)
- `generate_tracing_report_for_rep()` function (line ~2691)
- `generate_distribution_log_for_month()` function (line ~2971)

**New:** `eqms_starter/app/eqms/routes.py`
- Module: `tracing_reports` (new module)
- Routes:
  - `GET /admin/tracing` → `tracing_reports.list()`
  - `POST /admin/tracing/generate` → `tracing_reports.generate()`
  - `GET /admin/tracing/<id>/download` → `tracing_reports.download()`
  - `GET /admin/tracing/<id>` → `tracing_reports.detail()`

**Reusable code:**
- `generate_distribution_log_for_month()` filtering logic → Port as `tracing_reports/generate.py`
- CSV generation (simple CSV writer) → Reuse Python `csv` module

**Rewrite recommended:**
- Report generation UI (use new system's form patterns)
- Email sending logic (REMOVE, replace with .eml upload)

---

#### Approval .eml Uploads

**Old:** `Proto1.py` (minimal, mostly missing):
- `/admin/tracing/<id>/approve` (line ~9394) - currently manual approval, no .eml upload

**New:** `eqms_starter/app/eqms/routes.py`
- Module: `approvals` (new module)
- Routes:
  - `POST /admin/tracing/<report_id>/upload-approval` → `approvals.upload_eml()`
  - `GET /admin/tracing/<report_id>/approvals` → `approvals.list_for_report()`
  - `GET /admin/approvals/<id>/download` → `approvals.download_eml()`

**Reusable code:**
- None (new feature, implement from scratch)

**Rewrite recommended:**
- Everything (new feature, minimal .eml parsing with `email.parser`)

---

### Delete-List (What to Leave Behind)

**Files/Modules to NOT port:**
- `templates/rep_dashboard.html` (rep pages)
- `templates/rep_login.html` (rep authentication)
- `templates/rep_documents.html` (rep document uploads)
- All `/rep/<slug>` routes in `Proto1.py`
- `send_tracing_email_for_rep()` function (email sending)
- `send_global_tracing_email()` function (email sending)
- All SMTP configuration and email template code
- Rep-specific file storage directories (`uploads/rep_docs/`, `uploads/distributed/<slug>/`)
- Hospital targeting/facility search features (not core to distribution tracking)

---

## Implementation Plan

### Week 1: Foundation & Distribution Log

#### Milestone 1.1: Database Schema (Day 1-2)
- [ ] Create `distribution_log_entries` table (see `REP_SYSTEM_MINIMAL_SCHEMA.md`)
- [ ] Create `tracing_reports` table (metadata only)
- [ ] Create `approvals_eml` table
- [ ] Migration script: Export data from old `devices_distributed` → new `distribution_log_entries`

**Acceptance criteria:**
- Tables created in new system's DB
- Migration script runs without errors
- Sample data imported correctly

---

#### Milestone 1.2: Distribution Log Core (Day 3-5)
- [ ] Port `fetch_distribution_records()` normalization logic
- [ ] Implement `distribution_log.list()` route (browse with filters)
- [ ] Implement `distribution_log.create_manual()` route (manual entry form)
- [ ] Implement `distribution_log.update()` route (edit form)
- [ ] Implement `distribution_log.export_csv()` route (CSV download)
- [ ] Add audit logging (via `audit.py`)

**Acceptance criteria:**
- Can view list of distributions with filters (date, source, rep)
- Can create manual entry via form
- Can edit existing entry
- Can export filtered results as CSV
- All actions logged in audit table

---

#### Milestone 1.3: Import Functionality (Day 6-7)
- [ ] Port CSV import parser (`distribution_log/parsers/csv.py`)
- [ ] Port PDF import parser (`distribution_log/parsers/pdf.py`)
- [ ] Implement `distribution_log.import_csv()` route
- [ ] Implement `distribution_log.import_pdf()` route
- [ ] Add validation and deduplication logic

**Acceptance criteria:**
- Can upload CSV file, imports create distribution_log_entries
- Can upload PDF file, extracts order/facility/SKU/lot, creates entries
- Duplicate detection works (warns on duplicate ShipStation orders)
- Validation errors displayed clearly

---

### Week 2: Tracing Reports & Approvals

#### Milestone 2.1: Tracing Report Generation (Day 8-10)
- [ ] Implement `tracing_reports/generate.py` (filter + query logic)
- [ ] Implement `tracing_reports.generate()` route
- [ ] Implement CSV generation (from filtered distribution_log_entries)
- [ ] Implement storage via `storage.py` (versioned files)
- [ ] Implement `tracing_reports.list()` route (show generated reports)
- [ ] Implement `tracing_reports.download()` route (download CSV)

**Acceptance criteria:**
- Can generate report with filters (rep, source, month, SKU, customer)
- CSV file created in storage (versioned path)
- Metadata stored in `tracing_reports` table
- Can view list of generated reports
- Can download CSV file

---

#### Milestone 2.2: Approval .eml Upload (Day 11-12)
- [ ] Implement `approvals/upload_eml()` route
- [ ] Implement minimal .eml parsing (`email.parser` to extract headers)
- [ ] Implement storage via `storage.py` (linked to report_id)
- [ ] Implement `approvals.list_for_report()` route (show approvals for report)
- [ ] Implement `approvals.download_eml()` route (download .eml file)
- [ ] Update tracing report detail page to show approval evidence

**Acceptance criteria:**
- Can upload .eml file for a tracing report
- Metadata extracted (subject, from, to, date)
- .eml file stored in storage, linked to report_id
- Can view list of approvals for a report
- Can download .eml file

---

#### Milestone 2.3: Testing & Cleanup (Day 13-14)
- [ ] End-to-end test: Distribution Log → Tracing Report → Approval Upload
- [ ] Audit trail verification (all actions logged)
- [ ] RBAC verification (only authorized users can perform actions)
- [ ] Storage verification (files stored correctly, local + Spaces ready)
- [ ] Documentation update (user guide for new admin workflows)

**Acceptance criteria:**
- Full workflow tested: create distribution → generate report → upload approval
- All audit events logged correctly
- RBAC permissions work as expected
- Storage abstraction works (local dev + Spaces production)
- User documentation complete

---

## Top 5 Risks & Mitigation

### 1. **Data Migration Complexity**

**Risk:** Exporting from old `devices_distributed` + `device_distribution_records` tables requires complex normalization and deduplication.

**Mitigation:**
- Write migration script that processes old data in batches
- Validate each batch before importing (check for duplicates, missing required fields)
- Keep old system running in parallel during migration (dual-write period)
- Rollback plan: Keep old data export as backup

---

### 2. **PDF Parsing Reliability**

**Risk:** PDF parsing logic in `Proto1.py` is fragile (regex-based text extraction, may break on PDF format changes).

**Mitigation:**
- Port minimal PDF parsing (extract order number, basic fields only)
- Document known limitations (which PDF formats are supported)
- Provide manual entry fallback (if PDF parsing fails, admin can manually enter)
- Consider deprecating PDF import in favor of CSV/API imports

---

### 3. **ShipStation Sync Integration**

**Risk:** ShipStation API sync logic is tightly coupled to old system's rep/customer models.

**Mitigation:**
- Extract ShipStation API client code into separate module
- Map ShipStation data to new `distribution_log_entries` schema
- Test sync with sample data before production migration
- Run sync as background job (non-blocking, can be retried)

---

### 4. **Storage Abstraction Mismatch**

**Risk:** Old system uses filesystem paths, new system uses `storage.py` abstraction (local + Spaces).

**Mitigation:**
- Test storage abstraction with both local and Spaces backends
- Ensure storage keys are portable (no absolute paths)
- Migration script must copy files from old filesystem to new storage
- Verify file downloads work correctly (both local and Spaces)

---

### 5. **RBAC Permission Granularity**

**Risk:** Old system has implicit permissions (admin-only routes), new system requires explicit RBAC roles.

**Mitigation:**
- Define minimal roles: `Admin`, `Quality`, `Ops`, `ReadOnly`
- Map old admin-only routes to `Admin` role in new system
- Document required permissions for each feature
- Test RBAC with different user roles

---

## Dependencies & Risks Summary

**Dependencies:**
- New system's `eqms_starter` foundation (auth, RBAC, audit, storage) must be stable
- PostgreSQL database (migration from old SQLite if needed)
- ShipStation API credentials (environment variables)
- Storage backend (local filesystem or DigitalOcean Spaces)

**Risks:**
1. Data migration complexity (see above)
2. PDF parsing reliability (see above)
3. ShipStation sync integration (see above)
4. Storage abstraction mismatch (see above)
5. RBAC permission granularity (see above)

---

## Appendix: Code Module Recommendations

### Modules to Port (Reuse)

1. **`distribution_log/normalize.py`** - Field normalization logic (from `fetch_distribution_records()`)
2. **`distribution_log/grouping.py`** - Shipment grouping logic (from `_build_distributions()`)
3. **`distribution_log/parsers/csv.py`** - CSV import parser (from `admin_import_csv()`)
4. **`distribution_log/parsers/pdf.py`** - PDF import parser (from `_run_master_salesorder_import_from_pdf_path()`)
5. **`shipstation/sync.py`** - ShipStation API client (extract minimal client code)

### Modules to Rewrite (New Implementation)

1. **`distribution_log/routes.py`** - Use new system's route patterns
2. **`tracing_reports/generate.py`** - Rewrite to use new storage abstraction
3. **`approvals/upload.py`** - New feature, implement from scratch
4. **All templates** - Rewrite using new system's template structure

---

**End of Master Specification**
