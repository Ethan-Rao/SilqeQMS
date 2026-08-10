# Data Flow for REP Traceability

**Date:** 2026-01-15  
**Purpose:** Data flow diagrams and descriptions for Distribution Log ingestion, Tracing Report generation, and Approval Evidence linkage

---

## Overview

This document describes how data flows through the REP traceability system:

1. **Distribution Log Ingestion** (P0: manual entry, CSV import; P1: PDF import, ShipStation sync)
2. **Tracing Report Generation** (P0: generate CSV from Distribution Log, store immutable artifacts)
3. **Approval Evidence Upload** (P0: upload .eml files, link to tracing reports)

**Key Principles:**
- Distribution Log (`distribution_log_entries`) is the single source of truth
- Tracing Reports are immutable artifacts generated from Distribution Log (never stored separately, only generated artifacts)
- Approval .eml files are stored separately, linked to tracing report versions

---

## Data Sources & Truth Hierarchy

### Primary Source of Truth

**Distribution Log (`distribution_log_entries` table):**
- All distributions stored in normalized table
- Supports multiple ingestion methods: manual entry, CSV import, PDF import, ShipStation sync
- Single source of truth for all device distributions

### Generated Artifacts

**Tracing Reports:**
- Generated on-demand from Distribution Log with filters
- Stored as immutable CSV files (versioned by generation timestamp)
- Metadata stored in `tracing_reports` table (not the report itself)

**Approval Evidence:**
- Uploaded .eml files stored separately (linked to tracing report versions)
- Metadata stored in `approvals_eml` table
- Files stored in storage abstraction (local or S3-compatible)

---

## Distribution Log Ingestion Flows

### Flow 1: Manual Entry (P0)

**Trigger:** Admin submits manual entry form

**Steps:**
1. Admin fills form: Ship Date, Order Number (optional, auto-generated if blank), Facility Name, Rep, SKU, Lot, Quantity, Source (`manual`), optional address/contact/tracking, optional evidence file (PDF/image)
2. Route: `POST /admin/distribution-log/manual-entry`
3. Validation: Validate SKU (one of valid values), lot format (`SLQ-#####`), quantity (positive integer), ship date (valid date, not future)
4. Create `DistributionLogEntry`:
   - Set `source = 'manual'`
   - Set `created_by_user_id = current_user.id`
   - If evidence file uploaded: store via `storage.put_bytes()`, set `evidence_file_storage_key`
   - If order_number blank: auto-generate (e.g., `MAN-{timestamp}`)
5. Deduplication check: Check if `order_number + ship_date + facility_name` already exists (warn, allow override)
6. Insert into `distribution_log_entries` table
7. Log audit event: `distribution_log.create` with metadata (entry_id, facility_name, sku, lot, quantity)
8. Redirect to list page with success message

**Storage:**
- Evidence files (if uploaded): `distribution_log/{entry_id}/evidence_{filename}` (optional)

**Audit Trail:**
- Event: `distribution_log.create`
- Actor: `current_user.id`
- Entity: `distribution_log_entry`
- Entity ID: `entry.id`
- Metadata: `{facility_name, sku, lot, quantity, source: 'manual'}`

---

### Flow 2: CSV Import (P0)

**Trigger:** Admin uploads CSV file

**Steps:**
1. Admin uploads CSV file via form: `POST /admin/distribution-log/import-csv`
2. Parse CSV: `parsers.csv.parse_distribution_csv(file_bytes)`
   - Read CSV rows
   - Map columns: Ship Date → `ship_date`, Order Number → `order_number`, Facility Name → `facility_name`, SKU → `sku`, Lot → `lot_number`, Quantity → `quantity`, optional fields
   - Validate each row: SKU, lot format, quantity, date
   - Return list of normalized dicts, error list for invalid rows
3. For each valid row:
   - Create `DistributionLogEntry` via `service.create_distribution_entry()`
   - Set `source = 'csv_import'`
   - Set `created_by_user_id = current_user.id`
   - Deduplication check: Check if `order_number + ship_date + facility_name` already exists (warn, allow override)
   - Insert into `distribution_log_entries` table
4. Display import results: success count, errors (invalid rows), duplicates (warned)
5. Log audit event: `distribution_log.import_csv` with metadata (rows_processed, rows_created, rows_errors, rows_duplicates)

**Storage:**
- None (CSV is parsed, not stored)

**Audit Trail:**
- Event: `distribution_log.import_csv`
- Actor: `current_user.id`
- Entity: `distribution_log_entry` (one per row)
- Metadata: `{rows_processed, rows_created, rows_errors, rows_duplicates, filename}`

---

### Flow 3: PDF Import (P1 - Deferred)

**Trigger:** Admin uploads PDF file

**Steps:**
1. Admin uploads PDF file via form: `POST /admin/distribution-log/import-pdf`
2. Parse PDF: `parsers.pdf.parse_distribution_pdf(file_bytes)` (P1)
   - Extract text from PDF
   - Extract order number (from PDF header)
   - Extract facility name, SKU, lot, quantity (from PDF text via regex)
   - Return list of normalized dicts (one per page or one per order), error list for pages with extraction failures
3. For each valid entry:
   - Create `DistributionLogEntry` via `service.create_distribution_entry()`
   - Set `source = 'pdf_import'`
   - Set `created_by_user_id = current_user.id`
   - Deduplication check: Check if `order_number` already exists (warn, allow override)
   - Insert into `distribution_log_entries` table
4. Display import results: pages processed, entries created, errors (extraction failures), duplicates (warned)
5. Log audit event: `distribution_log.import_pdf` with metadata (pages_processed, entries_created, pages_errors, entries_duplicates)

**Storage:**
- None (PDF is parsed, not stored)

**Audit Trail:**
- Event: `distribution_log.import_pdf`
- Actor: `current_user.id`
- Entity: `distribution_log_entry` (one per entry)
- Metadata: `{pages_processed, entries_created, pages_errors, entries_duplicates, filename}`

**Note:** PDF import is **P1 (deferred)**. May be stubbed or return 404/501 for Step 1.

---

### Flow 4: ShipStation Sync (P1 - Deferred)

**Trigger:** Background job (cron or admin-triggered sync)

**Steps:**
1. Background job runs: `shipstation.sync.sync_orders()` (P1)
   - Connect to ShipStation API (credentials from environment)
   - Fetch orders from ShipStation (filter by date range or status)
   - For each order:
     - Parse ShipStation order data: `ss_shipment_id`, `order_number`, `ship_date`, `tracking_number`, `facility_name`, `address`, etc.
     - Create `DistributionLogEntry` via `service.create_distribution_entry()`
     - Set `source = 'shipstation'`
     - Set `ss_shipment_id = order.shipment_id`
     - Set `created_by_user_id = system_user.id` (or sync_user.id)
     - Deduplication check: Check if `ss_shipment_id` already exists (unique constraint prevents duplicates)
     - Insert into `distribution_log_entries` table
2. Log audit event: `distribution_log.sync_shipstation` with metadata (orders_fetched, orders_created, orders_skipped)

**Storage:**
- None (API data is normalized, not stored)

**Audit Trail:**
- Event: `distribution_log.sync_shipstation`
- Actor: `system_user.id` (or sync_user.id)
- Entity: `distribution_log_entry` (one per order)
- Metadata: `{orders_fetched, orders_created, orders_skipped, sync_timestamp}`

**Note:** ShipStation sync is **P1 (deferred)**. Not implemented in Step 1.

---

## Distribution Log Edit Flow

### Flow 5: Edit Entry (P0)

**Trigger:** Admin submits edit form

**Steps:**
1. Admin edits entry: `POST /admin/distribution-log/<id>/edit`
2. Load `DistributionLogEntry` by ID (404 if not found)
3. Validation: Same as manual entry (SKU, lot format, quantity, date)
4. Update entry:
   - Set `updated_by_user_id = current_user.id`
   - Set `updated_at = current_timestamp()`
   - Update fields from form (rep reassignment, quantity/lot corrections, optional fields)
5. Insert into `distribution_log_entries` table (update existing row)
6. Log audit event: `distribution_log.update` with reason-for-change and before/after values
7. Redirect to list page with success message

**Audit Trail:**
- Event: `distribution_log.update`
- Actor: `current_user.id`
- Entity: `distribution_log_entry`
- Entity ID: `entry.id`
- Reason: `request.form.get('reason')` (required)
- Metadata: `{before: {...}, after: {...}, fields_changed: [...]}`

---

## Tracing Report Generation Flow

### Flow 6: Generate Tracing Report (P0)

**Trigger:** Admin submits generate report form

**Steps:**
1. Admin selects filters: Month (required, YYYY-MM), Rep (optional), Source (optional: `all`, `shipstation`, `manual`), SKU (optional), Customer (optional)
2. Route: `POST /admin/tracing/generate`
3. Build filters dict: `{month, rep_id, source, sku, customer_id}`
4. Query `distribution_log_entries` with filters:
   - Filter by `ship_date` within month (e.g., `ship_date >= '2025-01-01' AND ship_date < '2025-02-01'`)
   - Filter by `rep_id` if provided
   - Filter by `source` if provided (not `all`)
   - Filter by `sku` if provided
   - Filter by `customer_id` if provided
5. Flatten to one row per SKU/Lot combination:
   - Group by shipment (order_number + ship_date) if multiple SKUs per order
   - One row per SKU/Lot combination
6. Sort by `ship_date` ASC
7. Generate CSV bytes:
   - Columns: `Ship Date`, `Order #`, `Facility`, `City`, `State`, `SKU`, `Lot`, `Quantity`, `Rep`, `Source`
   - Header row included
   - One row per SKU/Lot combination
8. Generate storage key: `tracing_reports/{month}/{filters_hash}_{generated_at_iso}.csv`
   - `filters_hash`: SHA256 hash of `filters_json` (ensures same filters = same hash)
   - `generated_at_iso`: ISO format timestamp (e.g., `2025-01-15T10-30-00`)
   - Example: `tracing_reports/2025-01/abc123def_2025-01-15T10-30-00.csv`
9. Store CSV artifact: `storage.put_bytes(storage_key, csv_bytes, content_type='text/csv')`
10. Create `TracingReport` metadata record:
    - `generated_at = current_timestamp()`
    - `generated_by_user_id = current_user.id`
    - `filters_json = filters_dict` (as JSON)
    - `report_storage_key = storage_key`
    - `report_format = 'csv'`
    - `status = 'draft'`
11. Insert into `tracing_reports` table
12. Log audit event: `tracing_reports.generate` with metadata (report_id, filters_json, storage_key)
13. Redirect to report detail page: `/admin/tracing/<id>`

**Storage:**
- CSV artifact: `tracing_reports/{month}/{filters_hash}_{generated_at_iso}.csv`
- Immutable: Never overwrite (each generation creates new file)

**Audit Trail:**
- Event: `tracing_reports.generate`
- Actor: `current_user.id`
- Entity: `tracing_report`
- Entity ID: `report.id`
- Metadata: `{filters_json, report_storage_key, report_format: 'csv', status: 'draft'}`

---

## Tracing Report Download Flow

### Flow 7: Download Report (P0)

**Trigger:** Admin clicks download link

**Steps:**
1. Admin clicks download: `GET /admin/tracing/<id>/download`
2. Load `TracingReport` by ID (404 if not found)
3. Read CSV file from storage: `storage.open(report_storage_key)`
4. Return CSV file download (Content-Type: `text/csv`, filename: `tracing_report_{id}_{month}.csv`)
5. Log audit event: `tracing_reports.download` with metadata (report_id, storage_key)

**Storage:**
- Read from: `tracing_reports/{month}/{filters_hash}_{generated_at_iso}.csv`

**Audit Trail:**
- Event: `tracing_reports.download`
- Actor: `current_user.id`
- Entity: `tracing_report`
- Entity ID: `report.id`
- Metadata: `{report_storage_key}`

---

## Approval Evidence Upload Flow

### Flow 8: Upload Approval .eml (P0)

**Trigger:** Admin uploads .eml file

**Steps:**
1. Admin uploads .eml file: `POST /admin/tracing/<report_id>/upload-approval`
2. Load `TracingReport` by ID (404 if not found)
3. Read uploaded .eml file: `eml_bytes = request.files['eml_file'].read()`
4. Parse .eml headers: `parse_eml_headers(eml_bytes)`
   - Use Python `email.parser.BytesParser` to parse .eml file
   - Extract headers only: `subject`, `from`, `to`, `date`
   - Parse `date` to ISO format (or None if invalid)
   - Extract first email address from `from` and `to` headers
   - Return dict: `{subject, from_email, to_email, email_date}`
5. Generate storage key: `approvals/{report_id}/{uploaded_at_iso}_{sanitized_subject}.eml`
   - `uploaded_at_iso`: ISO format timestamp (e.g., `2025-01-15T10-30-00`)
   - `sanitized_subject`: Remove special chars, limit to 100 chars (e.g., `Approval_Tracing_Report_2025-01`)
   - Example: `approvals/123/2025-01-15T10-30-00_Approval_Tracing_Report_2025-01.eml`
6. Store .eml file: `storage.put_bytes(storage_key, eml_bytes, content_type='message/rfc822')`
7. Create `ApprovalEml` metadata record:
   - `report_id = report.id`
   - `storage_key = storage_key`
   - `original_filename = request.files['eml_file'].filename`
   - `subject = parsed_headers['subject']`
   - `from_email = parsed_headers['from_email']`
   - `to_email = parsed_headers['to_email']`
   - `email_date = parsed_headers['email_date']`
   - `uploaded_at = current_timestamp()`
   - `uploaded_by_user_id = current_user.id`
   - `notes = request.form.get('notes')` (optional)
8. Insert into `approvals_eml` table
9. Log audit event: `approvals.upload` with metadata (approval_id, report_id, storage_key, subject)
10. Redirect to report detail page: `/admin/tracing/<report_id>`

**Storage:**
- .eml file: `approvals/{report_id}/{uploaded_at_iso}_{sanitized_subject}.eml`
- Immutable: Never overwrite (each upload creates new file)

**Audit Trail:**
- Event: `approvals.upload`
- Actor: `current_user.id`
- Entity: `approval_eml`
- Entity ID: `approval.id`
- Metadata: `{report_id, storage_key, subject, from_email, uploaded_at}`

---

## Approval Evidence Download Flow

### Flow 9: Download Approval .eml (P0)

**Trigger:** Admin clicks download link

**Steps:**
1. Admin clicks download: `GET /admin/approvals/<id>/download`
2. Load `ApprovalEml` by ID (404 if not found)
3. Read .eml file from storage: `storage.open(approval.storage_key)`
4. Return .eml file download (Content-Type: `message/rfc822` or `application/octet-stream`, filename: `approval_{id}_{sanitized_subject}.eml`)
5. Log audit event: `approvals.download` with metadata (approval_id, storage_key)

**Storage:**
- Read from: `approvals/{report_id}/{uploaded_at_iso}_{sanitized_subject}.eml`

**Audit Trail:**
- Event: `approvals.download`
- Actor: `current_user.id`
- Entity: `approval_eml`
- Entity ID: `approval.id`
- Metadata: `{storage_key}`

---

## Storage Key Conventions

### Distribution Log Evidence Files

**Format:** `distribution_log/{entry_id}/evidence_{filename}`

**Example:** `distribution_log/123/evidence_sales_order_2025-01-15.pdf`

**Note:** Optional (only if evidence file uploaded during manual entry)

---

### Tracing Report CSV Artifacts

**Format:** `tracing_reports/{month}/{filters_hash}_{generated_at_iso}.csv`

**Example:** `tracing_reports/2025-01/abc123def456_2025-01-15T10-30-00.csv`

**Properties:**
- `{month}`: YYYY-MM format (e.g., `2025-01`)
- `{filters_hash}`: SHA256 hash of `filters_json` (ensures same filters = same hash)
- `{generated_at_iso}`: ISO format timestamp (e.g., `2025-01-15T10-30-00`)
- Immutable: Never overwrite (each generation creates new file)

---

### Approval .eml Files

**Format:** `approvals/{report_id}/{uploaded_at_iso}_{sanitized_subject}.eml`

**Example:** `approvals/123/2025-01-15T10-30-00_Approval_Tracing_Report_2025-01.eml`

**Properties:**
- `{report_id}`: FK to `tracing_reports.id`
- `{uploaded_at_iso}`: ISO format timestamp (e.g., `2025-01-15T10-30-00`)
- `{sanitized_subject}`: Email subject with special chars removed, limited to 100 chars
- Immutable: Never overwrite (each upload creates new file)

---

## Data Flow Diagram Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Distribution Log Ingestion                   │
├─────────────────────────────────────────────────────────────────────┤
│ Manual Entry (P0) → distribution_log_entries                        │
│ CSV Import (P0)    → distribution_log_entries                        │
│ PDF Import (P1)    → distribution_log_entries                        │
│ ShipStation Sync   → distribution_log_entries                        │
│ (P1)                                                               │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ (single source of truth)
┌─────────────────────────────────────────────────────────────────────┐
│                    Tracing Report Generation                         │
├─────────────────────────────────────────────────────────────────────┤
│ Filters → Query distribution_log_entries → Generate CSV            │
│ → Store CSV artifact (immutable)                                     │
│ → Create tracing_reports metadata                                    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓ (linked by report_id)
┌─────────────────────────────────────────────────────────────────────┐
│                      Approval Evidence Upload                        │
├─────────────────────────────────────────────────────────────────────┤
│ Upload .eml → Parse headers → Store .eml artifact (immutable)       │
│ → Create approvals_eml metadata → Link to tracing_reports           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## P0 vs P1 Scope

**P0 (Must Have - Step 1):**
- Manual entry (Flow 1)
- CSV import (Flow 2)
- Edit entry (Flow 5)
- Generate tracing report (Flow 6)
- Download report (Flow 7)
- Upload approval .eml (Flow 8)
- Download approval .eml (Flow 9)

**P1 (Deferred - Not in Step 1):**
- PDF import (Flow 3)
- ShipStation sync (Flow 4)

---

## References

- **Master Spec:** [docs/REP_SYSTEM_MIGRATION_MASTER.md](docs/REP_SYSTEM_MIGRATION_MASTER.md)
- **Schema:** [docs/REP_SYSTEM_MINIMAL_SCHEMA.md](docs/REP_SYSTEM_MINIMAL_SCHEMA.md)
- **UI Map:** [docs/REP_SYSTEM_UI_MAP.md](docs/REP_SYSTEM_UI_MAP.md)
- **Storage Abstraction:** [app/eqms/storage.py](app/eqms/storage.py)
- **Audit Trail:** [app/eqms/audit.py](app/eqms/audit.py)
