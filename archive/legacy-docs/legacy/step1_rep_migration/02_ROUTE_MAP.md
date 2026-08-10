# Route Map for REP Traceability Module

**Date:** 2026-01-15  
**Purpose:** Exact route mapping from REP UI map to SilqeQMS implementation files

---

## Source of Truth

All routes copied verbatim from: [docs/REP_SYSTEM_UI_MAP.md](docs/REP_SYSTEM_UI_MAP.md)

---

## Module Structure

**Recommended implementation location (lean, consistent with modular monolith):**
- `app/eqms/modules/rep_traceability/__init__.py`
- `app/eqms/modules/rep_traceability/admin.py` (single blueprint, all routes)
- `app/eqms/modules/rep_traceability/models.py`
- `app/eqms/modules/rep_traceability/service.py`
- `app/eqms/modules/rep_traceability/parsers/__init__.py`
- `app/eqms/modules/rep_traceability/parsers/csv.py` (P0)
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (P1 - deferred)

**Blueprint registration:**
- Import in `app/eqms/__init__.py`: `from app.eqms.modules.rep_traceability.admin import bp as rep_traceability_bp`
- Register: `app.register_blueprint(rep_traceability_bp, url_prefix="/admin")`

**Note:** Routes in blueprint are prefixed (e.g., `/distribution-log`, `/tracing`), so final URLs are `/admin/distribution-log`, `/admin/tracing`, etc.

---

## Distribution Log Routes

### 1. `GET /admin/distribution-log`

**Route Handler:** `list_distributions()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.view`  
**Template:** `app/eqms/templates/admin/distribution_log/list.html`

**Query Parameters (Filters):**
- `date_from` (optional): YYYY-MM-DD
- `date_to` (optional): YYYY-MM-DD
- `source` (optional): `all`, `shipstation`, `manual`, `csv_import`, `pdf_import`
- `rep_id` (optional): integer (FK to users)
- `customer_id` (optional): integer (FK to customers)
- `sku` (optional): `all`, `211810SPT`, `211610SPT`, `211410SPT`
- `page` (optional): integer (pagination)

**Functionality:**
- Query `distribution_log_entries` with filters
- Apply pagination
- Display table with columns: Ship Date, Order #, Facility, Rep, SKU, Lot, Quantity, Source, Actions
- Show filters form at top
- Display actions: [Manual Entry], [Import CSV], [Import PDF], [Export]

**Permissions:**
- **View:** All authenticated users (via `distribution_log.view`)
- **Create/Edit/Delete/Import:** Admin, Quality, Ops roles (via `distribution_log.create|edit|delete`)

---

### 2. `POST /admin/distribution-log/manual-entry`

**Route Handler:** `create_manual_entry()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.create`  
**Template:** `app/eqms/templates/admin/distribution_log/edit.html` (GET)  
**Redirect:** `/admin/distribution-log` (POST success)

**Form Fields (POST):**
- `ship_date` (required): YYYY-MM-DD
- `order_number` (optional): string (auto-generate if blank)
- `facility_name` (required): string
- `rep_id` (optional): integer (FK to users)
- `source` (required): `manual` (default)
- `sku` (required): `211810SPT`, `211610SPT`, or `211410SPT`
- `lot_number` (required): string (format: `SLQ-#####`)
- `quantity` (required): integer > 0
- Optional: `address1`, `address2`, `city`, `state`, `zip`, `country`, `contact_name`, `contact_phone`, `contact_email`, `tracking_number`
- Optional: `evidence_file` (file upload: PDF/image)

**Functionality:**
- Validate form inputs (SKU, lot format, quantity, date)
- Create `DistributionLogEntry` via `service.create_distribution_entry()`
- If evidence file uploaded: store via `storage.put_bytes()`, set `evidence_file_storage_key`
- Log audit event: `distribution_log.create`
- Redirect to list with success message

**Permissions:**
- **Create:** Admin, Quality, Ops roles (via `distribution_log.create`)

---

### 3. `GET /admin/distribution-log/<id>/edit`

**Route Handler:** `edit_distribution_form(entry_id: int)`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.edit`  
**Template:** `app/eqms/templates/admin/distribution_log/edit.html`

**Functionality:**
- Load `DistributionLogEntry` by ID (404 if not found)
- Pre-fill form with entry data
- Render edit form

**Permissions:**
- **Edit:** Admin, Quality, Ops roles (via `distribution_log.edit`)

---

### 4. `POST /admin/distribution-log/<id>/edit`

**Route Handler:** `update_distribution(entry_id: int)`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.edit`  
**Redirect:** `/admin/distribution-log` (success) or back to edit form (error)

**Form Fields (POST):**
- All fields from manual entry (editable)
- `reason` (required): string (reason-for-change)

**Functionality:**
- Load `DistributionLogEntry` by ID (404 if not found)
- Validate form inputs
- Update entry via `service.update_distribution_entry()`
- Log audit event: `distribution_log.update` (with reason-for-change)
- Redirect to list with success message

**Permissions:**
- **Edit:** Admin, Quality, Ops roles (via `distribution_log.edit`)

---

### 5. `POST /admin/distribution-log/<id>/delete`

**Route Handler:** `delete_distribution(entry_id: int)`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.delete`  
**Redirect:** `/admin/distribution-log` (success)

**Form Fields (POST):**
- `reason` (required): string (reason-for-change)

**Functionality:**
- Load `DistributionLogEntry` by ID (404 if not found)
- Delete entry via `service.delete_distribution_entry()`
- Log audit event: `distribution_log.delete` (with reason-for-change)
- Redirect to list with success message

**Permissions:**
- **Delete:** Admin, Quality, Ops roles (via `distribution_log.delete`)

**Note:** Deletion is optional (may not be implemented in Step 1). If not implemented, hide delete button in UI.

---

### 6. `GET /admin/distribution-log/import-csv`

**Route Handler:** `import_csv_form()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.create`  
**Template:** `app/eqms/templates/admin/distribution_log/import.html` (CSV tab)

**Functionality:**
- Display file upload form for CSV
- Show expected columns: Ship Date, Order Number, Facility Name, SKU, Lot, Quantity, etc.

**Permissions:**
- **Import:** Admin, Ops roles (via `distribution_log.create`)

---

### 7. `POST /admin/distribution-log/import-csv`

**Route Handler:** `import_csv_post()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.create`  
**Redirect:** `/admin/distribution-log` (success) or back to import form (error)

**Form Fields (POST):**
- `csv_file` (required): file upload (CSV)

**Functionality:**
- Read uploaded CSV file
- Parse CSV via `parsers.csv.parse_distribution_csv()`
- For each row: create entry via `service.create_distribution_entry()`
- Handle duplicates: warn if `order_number + ship_date + facility_name` exists (allow override)
- Display import results: success count, errors, duplicates
- Log audit event: `distribution_log.import_csv`

**Permissions:**
- **Import:** Admin, Ops roles (via `distribution_log.create`)

---

### 8. `GET /admin/distribution-log/import-pdf`

**Route Handler:** `import_pdf_form()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.create`  
**Template:** `app/eqms/templates/admin/distribution_log/import.html` (PDF tab)

**Functionality:**
- Display file upload form for PDF
- Show supported formats: Master Sales Order PDF, Shipping Label PDF

**Permissions:**
- **Import:** Admin, Ops roles (via `distribution_log.create`)

**Note:** PDF import is **P1 (deferred)**. Route may be stubbed or return 404/501 for Step 1.

---

### 9. `POST /admin/distribution-log/import-pdf`

**Route Handler:** `import_pdf_post()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.create`  
**Redirect:** `/admin/distribution-log` (success) or back to import form (error)

**Form Fields (POST):**
- `pdf_file` (required): file upload (PDF)

**Functionality:**
- Read uploaded PDF file
- Parse PDF via `parsers.pdf.parse_distribution_pdf()` (P1)
- Extract order number, facility, SKU/lot from PDF text
- For each entry: create entry via `service.create_distribution_entry()`
- Handle duplicates: warn if `order_number` exists
- Display import results: pages processed, entries created, errors
- Log audit event: `distribution_log.import_pdf`

**Permissions:**
- **Import:** Admin, Ops roles (via `distribution_log.create`)

**Note:** PDF import is **P1 (deferred)**. Route may be stubbed or return 404/501 for Step 1.

---

### 10. `GET /admin/distribution-log/export`

**Route Handler:** `export_csv()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `distribution_log.export`  
**Response:** CSV file download

**Query Parameters (Filters - same as list):**
- `date_from`, `date_to`, `source`, `rep_id`, `customer_id`, `sku`

**Functionality:**
- Query `distribution_log_entries` with filters (same as list)
- Generate CSV with columns: Ship Date, Order #, Facility, City, State, SKU, Lot, Quantity, Rep, Source
- Sort by ship_date ASC
- Return CSV file download (Content-Type: `text/csv`)
- Log audit event: `distribution_log.export`

**Permissions:**
- **Export:** All authenticated users (via `distribution_log.export`)

---

## Tracing Reports Routes

### 11. `GET /admin/tracing`

**Route Handler:** `list_tracing_reports()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `tracing_reports.view`  
**Template:** `app/eqms/templates/admin/tracing/list.html`

**Functionality:**
- Query `tracing_reports` (all or filtered by month/rep/status)
- Display table with columns: Generated At, Filters, Status, Actions
- Show [Generate] button at top
- Display actions: [View], [Download]

**Permissions:**
- **View:** All authenticated users (via `tracing_reports.view`)
- **Generate:** Admin, Quality, Ops roles (via `tracing_reports.generate`)

---

### 12. `POST /admin/tracing/generate`

**Route Handler:** `generate_report()`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `tracing_reports.generate`  
**Redirect:** `/admin/tracing/<id>` (success) or back to generate form (error)

**Form Fields (POST):**
- `month` (required): YYYY-MM format
- `rep_id` (optional): integer (FK to users)
- `source` (optional): `all`, `shipstation`, `manual`
- `sku` (optional): `all`, `211810SPT`, `211610SPT`, `211410SPT`
- `customer_id` (optional): integer (FK to customers)

**Functionality:**
- Validate month format (YYYY-MM)
- Build filters dict: `{month, rep_id, source, sku, customer_id}`
- Generate report via `service.generate_tracing_report_csv()`
- Store CSV artifact via `storage.put_bytes()` (storage key: `tracing_reports/{month}/{filters_hash}_{generated_at_iso}.csv`)
- Create `TracingReport` metadata record with `filters_json`, `report_storage_key`, `status='draft'`
- Log audit event: `tracing_reports.generate`
- Redirect to report detail page

**Permissions:**
- **Generate:** Admin, Quality, Ops roles (via `tracing_reports.generate`)

---

### 13. `GET /admin/tracing/<id>`

**Route Handler:** `tracing_report_detail(report_id: int)`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `tracing_reports.view`  
**Template:** `app/eqms/templates/admin/tracing/detail.html`

**Functionality:**
- Load `TracingReport` by ID (404 if not found)
- Load all `ApprovalEml` records for this report
- Display report metadata: generated_at, generated_by_user_id, filters_json, status, report_storage_key
- Display [Download CSV] button
- Display "Approval Evidence" section with:
  - File upload form for .eml
  - List of uploaded approvals with download links, metadata (subject, from, uploaded_at)

**Permissions:**
- **View:** All authenticated users (via `tracing_reports.view`)
- **Upload Approval:** Admin, Quality, Ops roles (via `approvals.upload`)

---

### 14. `GET /admin/tracing/<id>/download`

**Route Handler:** `download_report(report_id: int)`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `tracing_reports.download`  
**Response:** CSV file download

**Functionality:**
- Load `TracingReport` by ID (404 if not found)
- Read CSV file from storage via `storage.open(report_storage_key)`
- Return CSV file download (Content-Type: `text/csv`)
- Log audit event: `tracing_reports.download`

**Permissions:**
- **Download:** All authenticated users (via `tracing_reports.download`)

---

## Approval Evidence Routes

### 15. `POST /admin/tracing/<report_id>/upload-approval`

**Route Handler:** `upload_approval_eml(report_id: int)`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `approvals.upload`  
**Redirect:** `/admin/tracing/<report_id>` (success) or back to report detail (error)

**Form Fields (POST):**
- `eml_file` (required): file upload (.eml)
- `notes` (optional): string (admin notes)

**Functionality:**
- Load `TracingReport` by ID (404 if not found)
- Read uploaded .eml file
- Parse .eml headers via `service.parse_eml_headers()` (extract subject, from, to, date)
- Generate storage key: `approvals/{report_id}/{uploaded_at_iso}_{sanitized_subject}.eml`
- Store .eml file via `storage.put_bytes()`
- Create `ApprovalEml` record with metadata
- Log audit event: `approvals.upload`
- Redirect to report detail page with success message

**Permissions:**
- **Upload:** Admin, Quality, Ops roles (via `approvals.upload`)

---

### 16. `GET /admin/approvals/<id>/download`

**Route Handler:** `download_approval_eml(approval_id: int)`  
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Permission:** `approvals.view`  
**Response:** .eml file download

**Functionality:**
- Load `ApprovalEml` by ID (404 if not found)
- Read .eml file from storage via `storage.open(storage_key)`
- Return .eml file download (Content-Type: `message/rfc822` or `application/octet-stream`)
- Log audit event: `approvals.download`

**Permissions:**
- **Download:** All authenticated users (via `approvals.view` or inherit from `tracing_reports.view`)

---

## Permission Summary

### Permission Keys (from UI Map)

**Distribution Log:**
- `distribution_log.view` - View distribution log list
- `distribution_log.create` - Create manual entry, import CSV/PDF
- `distribution_log.edit` - Edit distribution entries
- `distribution_log.delete` - Delete distribution entries
- `distribution_log.export` - Export CSV

**Tracing Reports:**
- `tracing_reports.view` - View tracing reports list
- `tracing_reports.generate` - Generate new reports
- `tracing_reports.download` - Download CSV files

**Approvals:**
- `approvals.view` - View approval evidence
- `approvals.upload` - Upload .eml files

### Role → Permission Mapping (from UI Map)

**Admin:**
- All permissions (full access)

**Quality:**
- All permissions (same as Admin, for compliance audits)

**Ops:**
- All REP permissions (same as Admin, no user management)

**ReadOnly:**
- `distribution_log.view`
- `tracing_reports.view`
- `tracing_reports.download`
- `approvals.view`

---

## Blueprint Implementation Structure

**File:** `app/eqms/modules/rep_traceability/admin.py`

```python
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from app.eqms.rbac import require_permission
from app.eqms.db import db_session
from app.eqms.audit import record_event
from app.eqms.storage import storage_from_config
from app.eqms.modules.rep_traceability.service import (
    create_distribution_entry,
    update_distribution_entry,
    delete_distribution_entry,
    generate_tracing_report_csv,
    upload_approval_eml,
    parse_distribution_csv,  # P0
)
from app.eqms.modules.rep_traceability.models import (
    DistributionLogEntry,
    TracingReport,
    ApprovalEml,
)

bp = Blueprint("rep_traceability", __name__)

# Distribution Log Routes
@bp.get("/distribution-log")
@require_permission("distribution_log.view")
def list_distributions():
    # Implementation
    pass

@bp.post("/distribution-log/manual-entry")
@require_permission("distribution_log.create")
def create_manual_entry():
    # Implementation
    pass

# ... (all other routes)

# Tracing Reports Routes
@bp.get("/tracing")
@require_permission("tracing_reports.view")
def list_tracing_reports():
    # Implementation
    pass

# ... (all other routes)

# Approval Evidence Routes
@bp.post("/tracing/<int:report_id>/upload-approval")
@require_permission("approvals.upload")
def upload_approval_eml(report_id: int):
    # Implementation
    pass

# ... (all other routes)
```

---

## Route Registration in App Factory

**File:** `app/eqms/__init__.py`

Add import:
```python
from app.eqms.modules.rep_traceability.admin import bp as rep_traceability_bp
```

Register blueprint:
```python
app.register_blueprint(rep_traceability_bp, url_prefix="/admin")
```

**Final URLs:**
- `/admin/distribution-log`
- `/admin/distribution-log/manual-entry`
- `/admin/distribution-log/<id>/edit`
- `/admin/distribution-log/import-csv`
- `/admin/distribution-log/export`
- `/admin/tracing`
- `/admin/tracing/generate`
- `/admin/tracing/<id>`
- `/admin/tracing/<id>/download`
- `/admin/tracing/<report_id>/upload-approval`
- `/admin/approvals/<id>/download`

---

## Template File Mapping

**Distribution Log:**
- `app/eqms/templates/admin/distribution_log/list.html` - List page with filters
- `app/eqms/templates/admin/distribution_log/edit.html` - Manual entry / edit form
- `app/eqms/templates/admin/distribution_log/import.html` - CSV/PDF import forms

**Tracing Reports:**
- `app/eqms/templates/admin/tracing/list.html` - Reports list
- `app/eqms/templates/admin/tracing/generate.html` - Generate form (optional, may be modal)
- `app/eqms/templates/admin/tracing/detail.html` - Report detail with approvals

---

## References

- **Source Routes:** [docs/REP_SYSTEM_UI_MAP.md](docs/REP_SYSTEM_UI_MAP.md)
- **Blueprint Pattern:** [app/eqms/modules/document_control/admin.py](app/eqms/modules/document_control/admin.py)
- **RBAC Decorator:** [app/eqms/rbac.py](app/eqms/rbac.py)
- **App Factory:** [app/eqms/__init__.py](app/eqms/__init__.py)
