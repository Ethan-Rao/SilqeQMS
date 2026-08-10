# COMPREHENSIVE DEBUG & LEGACY CODE AUDIT — SilqQMS

**Date:** 2026-03-11  
**Baseline Commit:** `0836bb1`  
**Objective:** Perform a deep, file-by-file debug and legacy code review of every component in the SilqQMS application. Identify all bugs, dead code, orphaned references, inconsistencies, and potential failure modes. Produce a structured findings document — do NOT implement any changes.

---

## Your Mission

You are a senior QA engineer performing a comprehensive debug audit on a Flask-based Quality Management System (SilqQMS) for a medical device company. The system has undergone rapid development over the past month with many features added, refactored, and reorganized. Your job is to find every issue that could cause a failure, data loss, or user confusion — **and** to identify any legacy/dead code that should be removed.

**Output:** A single Markdown document titled `SYSTEM_AUDIT_FINDINGS_2026_03_11.md` placed in `docs/audits/`. Structured with numbered findings, severity levels, affected files, and recommended fix strategies.

**CRITICAL RULES:**
1. Do NOT modify any code. Only read, analyze, and document.
2. Read EVERY file — do not skim or skip files.
3. For large files, use semantic search or read in chunks, but ensure full coverage.
4. Push the findings doc to `main` when complete.

---

## System Overview

SilqQMS is a Flask application deployed on DigitalOcean App Platform (PostgreSQL + S3 storage). It manages quality, manufacturing, and commercial operations for a medical device company.

### Current Architecture
- **68 Python files**, **71 HTML templates**, **27 Alembic migrations**, **14 utility scripts**
- **Backend:** Flask 3.x, SQLAlchemy ORM, Alembic, PostgreSQL (prod) / SQLite (dev)
- **Frontend:** Server-rendered Jinja2, custom dark-theme CSS design system
- **Storage:** Abstract `Storage` → `LocalStorage` or `S3Storage` (DigitalOcean Spaces)
- **Auth:** Session-based, RBAC with per-endpoint permissions, CSRF protection
- **File Viewing:** Centralized `document_viewer.py` — .docx→HTML (mammoth), .xlsx/.xls→HTML tables (openpyxl), .csv→HTML tables, PDF/images/text natively in browser
- **PDF Parsing:** pdfplumber + PyPDF2 for sales orders, shipping labels, purchase orders
- **External API:** ShipStation REST API for distribution sync

### Admin Dashboard — 4 Columns

| Quality Management | Silq Operations | External Relationships | QMS System |
|---|---|---|---|
| QM Documents | Manufacturing | Distribution Log | Document Control (DCOs) |
| Management Reviews & Audits | Equipment | Sales Dashboard | CAPAs |
| Post Market Surveillance | Supplies | Customers | Forms, Templates & Travelers |
| Risk Management | Purchasing | Suppliers | Admin Tools |
| Design History Files | NCRs | NRE Projects | My Account |
| Regulatory Standards | Employee Training | | |

### 11 Document Libraries (admin_docs module)
`qms_documents`, `employee_training`, `management_reviews`, `ncrs`, `capas`, `post_market_surveillance`, `regulatory_standards`, `work_orders`, `risk_management`, `dhfs`, `forms_templates_travelers`

---

## Complete File Inventory

### Core Application Files
```
app/eqms/__init__.py          — App factory, blueprint registration, error handlers, security headers, schema health check
app/eqms/config.py            — Settings from env vars
app/eqms/db.py                — SQLAlchemy engine/session management
app/eqms/models.py            — Core models (User, Role, Permission, AuditEvent, Base) + all module model imports
app/eqms/auth.py              — Login/logout, session management, rate limiting with TTL cleanup
app/eqms/admin.py             — Admin dashboard, diagnostics, data reset, user accounts, audit log, customer merge
app/eqms/rbac.py              — @require_permission decorator
app/eqms/security.py          — CSRF token helpers (ensure_csrf_token, validate_csrf)
app/eqms/audit.py             — record_event() for audit trail
app/eqms/storage.py           — LocalStorage, S3Storage (with cached boto3 client), storage_from_config()
app/eqms/document_viewer.py   — Centralized .docx/.xlsx/.csv → HTML rendering with HTML sanitization
app/eqms/utils.py             — utcnow(), current_user(), allow_inline_view(), parse_custom_fields(), validate_managed_document()
app/eqms/constants.py         — Application constants
app/eqms/routes.py            — Public routes (index, /health, /health/deep)
```

### Modules (each under app/eqms/modules/)
```
admin_docs/          — 11 document libraries (QMS, training, NCRs, CAPAs, risk mgmt, DHFs, etc.)
  admin.py           — LIBRARIES dict, LIBRARY_ENDPOINTS dict, 11 route functions, CRUD for folders/files, view/download/move
  models.py          — AdminDocFolder, AdminDocFile
  service.py         — create_folder(), upload_document()
  utils.py           — (check if used or legacy)

customer_profiles/   — Customer CRUD, notes, merge, address tracking
  admin.py           — Customer list, detail (tabbed: info, sales orders, distributions, notes), notes CRUD
  models.py          — Customer, CustomerNote, CustomerRep, Rep
  service.py         — find_or_create_customer(), canonical_customer_key(), get/update customers
  utils.py           — canonical_customer_key(), normalize_facility_name(), extract_email_domain()

document_control/    — DCO lifecycle (draft → released → obsolete)
  admin.py           — Document list, create, detail, revision upload, release, edit
  models.py          — Document, DocumentRevision, DocumentFile
  service.py         — DCO business logic

equipment/           — Equipment inventory, calibration, PM tracking, document attachments
  admin.py           — Equipment CRUD, bulk import, document upload/view/download
  models.py          — Equipment, EquipmentSupplier, ManagedDocument
  parsers/pdf.py     — Equipment PDF parser
  service.py         — Equipment CRUD logic

manufacturing/       — Lot tracking for suspension production, document attachments
  admin.py           — Manufacturing index, lot CRUD, document upload/view/download
  models.py          — ManufacturingLot, ManufacturingLotDocument, ManufacturingLotEquipment, ManufacturingLotMaterial
  service.py         — Lot CRUD logic

nre_projects/        — Non-recurring engineering projects
  admin.py           — NRE dashboard, project detail with sales order tab

purchasing/          — Purchase orders with PDF import and EML viewing
  admin.py           — PO CRUD, import, attachment upload/view/download, EML viewer
  models.py          — PurchaseOrder, PurchaseOrderLine, PurchaseOrderAttachment
  parsers/pdf.py     — PO PDF parser
  service.py         — PO business logic

rep_traceability/    — Distribution log, sales orders, tracing reports, sales dashboard
  admin.py           — Distribution log CRUD+import, sales orders import+list+detail, tracing reports, sales dashboard, lot log upload
  models.py          — DistributionLogEntry, DistributionLine, SalesOrder, SalesOrderLine, OrderPdfAttachment, TracingReport, ApprovalEml
  parsers/csv.py     — Distribution CSV parser
  parsers/pdf.py     — Sales order PDF parser, shipping label parser
  service.py         — Sales dashboard computations, distribution matching
  utils.py           — (check if used or legacy)

shipstation_sync/    — ShipStation API integration
  admin.py           — Sync UI, trigger sync, diagnostics
  models.py          — ShipStationSyncRun, ShipStationSkippedOrder
  parsers.py         — LotLog.csv parser, lot corrections, lot date loading
  service.py         — Sync orchestration, order processing
  shipstation_client.py — REST API wrapper

suppliers/           — Approved supplier management
  admin.py           — Supplier CRUD, document upload/view/download
  models.py          — Supplier
  service.py         — Supplier CRUD logic

supplies/            — Consumables/supply inventory
  admin.py           — Supply CRUD, document upload/view/download
  models.py          — Supply, SupplySupplier, SupplyDocument
  service.py         — Supply CRUD logic
```

### Templates (71 total)
```
_layout.html                             — Base layout (nav, flash messages, CSS, logout POST form)
admin/index.html                         — Admin dashboard (4 columns, 17 cards)
admin/document_viewer.html               — Universal .docx/.xlsx/.csv viewer
admin/admin_docs/index.html              — Document library browser (subfolders, upload, move modal)
admin/customers/detail.html              — Customer profile (tabs: info, sales orders, distributions, notes)
admin/customers/list.html                — Customer list
admin/customers/merge_candidates.html    — Customer merge candidates
admin/customers/merge.html               — Customer merge confirmation
admin/distribution_log/list.html         — Distribution log list
admin/distribution_log/edit.html         — Distribution log edit
admin/distribution_log/import.html       — Distribution CSV import
admin/equipment/list.html                — Equipment list
admin/equipment/detail.html              — Equipment detail
admin/equipment/edit.html                — Equipment edit
admin/equipment/new.html                 — Equipment create
admin/equipment/bulk_import.html         — Equipment bulk import
admin/manufacturing/index.html           — Manufacturing index
admin/manufacturing/suspension/list.html — Suspension lots list
admin/manufacturing/suspension/detail.html — Suspension lot detail
admin/manufacturing/suspension/edit.html — Suspension lot edit
admin/manufacturing/suspension/new.html  — Suspension lot create
admin/manufacturing/cleartract_placeholder.html — ClearTract placeholder
admin/purchasing/list.html               — PO list
admin/purchasing/detail.html             — PO detail
admin/purchasing/edit.html               — PO edit
admin/purchasing/new.html                — PO create
admin/purchasing/import.html             — PO PDF import
admin/purchasing/view_eml.html           — EML viewer
admin/sales_dashboard/index.html         — Sales metrics + lot inventory
admin/sales_orders/list.html             — Sales order list
admin/sales_orders/detail.html           — Sales order detail
admin/sales_orders/import.html           — Sales order PDF import
admin/sales_orders/unmatched_pdfs.html   — Unmatched PDFs
admin/nre_projects/index.html            — NRE project dashboard
admin/nre_projects/detail.html           — NRE project detail
admin/tracing/list.html                  — Tracing report list
admin/tracing/detail.html                — Tracing report detail
admin/tracing/generate.html              — Generate tracing report
admin/shipstation/index.html             — ShipStation sync UI
admin/shipstation/diag.html              — ShipStation diagnostics
admin/suppliers/list.html                — Supplier list
admin/suppliers/detail.html              — Supplier detail
admin/suppliers/edit.html                — Supplier edit
admin/suppliers/new.html                 — Supplier create
admin/supplies/list.html                 — Supply list
admin/supplies/detail.html               — Supply detail
admin/supplies/edit.html                 — Supply edit
admin/supplies/new.html                  — Supply create
admin/reps/list.html                     — Rep list
admin/reps/edit.html                     — Rep edit
admin/accounts/list.html                 — User accounts list
admin/accounts/detail.html               — User account detail
admin/accounts/new.html                  — Create user account
admin/me.html                            — Current user profile
admin/diagnostics.html                   — System diagnostics page
admin/reset_data.html                    — Data reset page
admin/upload_lotlog.html                 — Lot log upload page
admin/audit/list.html                    — Audit log viewer
admin/debug_permissions.html             — Permissions debug page
admin/_notes_modal_content.html          — Notes AJAX modal fragment
admin/modules/document_control/list.html — DCO list
admin/modules/document_control/detail.html — DCO detail
admin/modules/document_control/new.html  — DCO create
auth/login.html                          — Login form
errors/400.html                          — Bad Request
errors/403.html                          — Forbidden
errors/404.html                          — Not Found
errors/405.html                          — Method Not Allowed
errors/500.html                          — Internal Server Error
errors/schema_out_of_date.html           — Schema drift warning
public/index.html                        — Public landing page
```

### Scripts (14 total)
```
scripts/init_db.py                          — Seed permissions, roles, admin user (requires ADMIN_PASSWORD env var)
scripts/_db_utils.py                        — Reusable script_session context manager
scripts/attach_admin_role.py                — Assign admin role to user
scripts/backfill_customer_addresses.py      — Backfill customer addresses from sales orders
scripts/backfill_sales_order_matching.py    — Backfill sales order → distribution matching
scripts/bulk_import_admin_docs.py           — Bulk import documents from local filesystem to S3
scripts/cleanup_pdf_import_distributions.py — Clean up orphaned distribution entries from PDF import
scripts/cleanup_zero_order_customers.py     — Remove customers with no orders
scripts/dedupe_customers.py                 — Deduplicate customer records
scripts/import_equipment_and_suppliers.py   — Import equipment/supplier data
scripts/rebuild_customers_from_sales_orders.py — Rebuild customer records
scripts/refresh_customers_from_sales_orders.py — Refresh customer addresses
scripts/release.py                          — Deployment release script (alembic upgrade head + seed)
scripts/start.py                            — Gunicorn start wrapper
```

### Migrations (27 files)
```
56a470f9ee55_initial_schema.py
199268f34bba_add_equipment_and_suppliers_tables.py
2b9d749fc12f_add_manufacturing_lots_tables.py
3c8d7e1f0a2b_add_customer_id_to_distribution_log_entries.py
7f9a1c2d3e4b_add_shipstation_sync_tables_and_external_key.py
8b1c2d3e4f50_fix_schema_drift_columns.py
9c0d1e2f3a4b_fix_more_prod_schema_drift.py
9f2c1a3d4b5c_add_customers_and_notes.py
a1b2c3d4e5f6_complete_schema_drift_fix.py
aa3f4c5d6e7f_add_distribution_lines.py
b1c2d3e4f5g6_add_sales_orders_tables.py
b7c8d9e0f1a2_merge_distribution_lines_head.py
c8f1b2a3d4e5_add_user_address_fields.py
d1e2f3a4b5c6_merge_heads.py
e4f5a6b7c8d9_add_customer_reps_table.py
ebb33122a9ce_add_rep_traceability_tables.py
f9a0b1c2d3e4_add_order_pdf_attachments.py
g1h2i3j4k5l6_merge_all_heads.py
h2i3j4k5l6m_create_reps_table.py
i3j4k5l6m7_add_custom_fields.py
j4k5l6m7n8_add_supplier_contacts_and_doc_text.py
k1l2m3n4o5_account_management_fields.py
l2m3n4o5p6_shipstation_salesorder_redesign.py
n1o2p3q4r5_add_document_categories.py
p1q2r3s4t5_add_supplies_module.py
q1r2s3t4u5_add_purchasing_module_tables.py
r1s2t3u4v5_add_admin_docs_library.py
```

---

## AUDIT AREAS — What to Examine

### AREA 1: LEGACY CODE & DEAD CODE DETECTION

This is a **primary focus** of this audit. The system has been through many refactors. Look for:

- [ ] **Unused imports** — imports at the top of files that are never referenced in the file body
- [ ] **Dead routes** — routes in `admin.py` files that are defined but never linked from any template
- [ ] **Orphaned templates** — HTML templates that no route renders
- [ ] **Dead model columns** — model columns that are defined but never read, written, or queried
- [ ] **Unused utility functions** — functions in `utils.py`, `service.py` that are never called
- [ ] **Obsolete scripts** — scripts in `scripts/` that perform operations superseded by newer code
- [ ] **Stale migration code** — migration files that reference deprecated models or columns
- [ ] **Duplicated logic** — similar code blocks in multiple modules that should use a shared helper (especially check all `admin.py` files for duplicated document upload/view/download patterns)
- [ ] **Commented-out code blocks** — commented code that should be deleted, not preserved
- [ ] **Deprecated model attributes** — e.g., `customer_name` on `DistributionLogEntry` that was replaced by the `Customer` relationship
- [ ] **Legacy constants** — hardcoded values that reference old system concepts
- [ ] **Ghost blueprint routes** — ensure every registered blueprint in `__init__.py` is actually needed and has working routes

### AREA 2: ROUTE & ENDPOINT VERIFICATION

For every route across all modules:
- [ ] Does it have the correct `@require_permission` decorator?
- [ ] Does it validate all user inputs (form data, query params, file uploads)?
- [ ] Does it handle missing/invalid data gracefully (flash + redirect, not 500)?
- [ ] Are all `url_for()` references valid (correct blueprint, function name, arguments)?
- [ ] Do POST routes have CSRF protection?
- [ ] Are database transactions properly committed/rolled back?
- [ ] Are there any routes that SHOULD exist but DON'T (e.g., missing edit/delete for a resource)?

### AREA 3: TEMPLATE VERIFICATION

For every Jinja2 template:
- [ ] Are all `url_for()` calls valid and correctly parameterized?
- [ ] Do all forms include `{{ csrf_token() }}` or equivalent?
- [ ] Do all forms have the correct `action` URL and `method`?
- [ ] Are there broken links, missing buttons, or UI elements that reference nonexistent routes?
- [ ] Is navigation consistent (breadcrumbs, back buttons)?
- [ ] Do tables handle empty states gracefully ("No records found")?
- [ ] Do all pages extend `_layout.html`?
- [ ] Are there hardcoded strings that should be dynamic?

### AREA 4: DOCUMENT VIEWING CHAIN — END TO END

This is critical. The system has 8 different modules that serve documents. Trace the entire chain for EACH module:

**Modules that serve documents:**
1. `admin_docs` — AdminDocFile (11 libraries)
2. `equipment` — ManagedDocument (equipment docs)
3. `suppliers` — ManagedDocument (supplier docs)
4. `supplies` — SupplyDocument
5. `manufacturing` — ManufacturingLotDocument
6. `document_control` — DocumentFile
7. `purchasing` — PurchaseOrderAttachment
8. `rep_traceability` — OrderPdfAttachment, ApprovalEml
9. `nre_projects` — OrderPdfAttachment (via sales orders)
10. `customer_profiles` — OrderPdfAttachment (via sales order tab)

For EACH:
- [ ] Is there a `/view` route? Does it call `needs_server_render()` → `render_document_to_response()` for .docx/.xlsx/.csv?
- [ ] Is there a `/download` route?
- [ ] Does it use `allow_inline_view()` consistently for native types?
- [ ] Do "View" and "Download" buttons appear in the template?
- [ ] Is `storage.open()` or `storage.get_bytes()` called correctly?
- [ ] Are file objects closed properly (no resource leaks)?
- [ ] What happens with unsupported file types (.zip, .pptx, .dymo, .msg)? Does the user get a download gracefully?

### AREA 5: MODEL & DATABASE INTEGRITY

For every SQLAlchemy model:
- [ ] Are foreign keys correct with appropriate `ondelete` behavior?
- [ ] Are `nullable` constraints correct?
- [ ] Are indexes defined for commonly queried columns?
- [ ] Are `relationship()` `back_populates` / `cascade` settings correct and symmetric?
- [ ] Is `onupdate=utcnow` set on all `updated_at` columns?
- [ ] Is `default=utcnow` (not `utcnow()` — the function reference, not a call) set on `created_at` columns?
- [ ] Are there any orphan-deletion issues?
- [ ] Is the `models.py` bottom-of-file import block complete (all module models imported for `Base.metadata`)?

### AREA 6: IMPORT CHAIN & CIRCULAR DEPENDENCIES

The system recently had a circular import bug (`utils.py` ↔ `equipment/models.py`). Check:
- [ ] Does `app/eqms/utils.py` have ANY top-level imports from `app.eqms.modules.*` or `app.eqms.models`? (It should NOT — all such imports must be lazy/inside functions)
- [ ] Does `app/eqms/models.py` import `utcnow` from `utils.py` at the top? (This is fine, but verify `utils.py` doesn't import back)
- [ ] Do any module `models.py` files import from each other? (Could create circular chains)
- [ ] Do any module `admin.py` files import models from other modules in a way that could cause issues during app initialization?
- [ ] Trace the full import chain from `app/eqms/__init__.py` → all blueprints → verify no circular paths

### AREA 7: PARSERS & DATA FLOW

- [ ] **Sales order PDF parser** (`rep_traceability/parsers/pdf.py`): Does it handle multi-page PDFs, missing fields, malformed tables, shifted rows?
- [ ] **Distribution CSV parser** (`rep_traceability/parsers/csv.py`): Encoding issues, missing columns, lot corrections applied?
- [ ] **Purchase order PDF parser** (`purchasing/parsers/pdf.py`): All PO formats handled?
- [ ] **ShipStation sync** (`shipstation_sync/service.py`): API rate limits, missing fields, pagination, partial failures?
- [ ] **Lot log parser** (`shipstation_sync/parsers.py`): Missing dates, duplicate lots, encoding? Is `load_lot_log_with_inventory()` indentation correct?
- [ ] **Customer matching** (`customer_profiles/service.py`): Does `find_or_create_customer` / `canonical_customer_key` handle all edge cases?
- [ ] Are parser errors surfaced to the user clearly (not swallowed silently)?

### AREA 8: SECURITY & AUTH

- [ ] Is every admin route protected by `@require_permission`?
- [ ] Are there routes accessible without login?
- [ ] Does rate limiting work correctly for login attempts?
- [ ] Are CSRF tokens validated on ALL state-changing POST/PUT/DELETE requests?
- [ ] Verify the CSRF exemption in `__init__.py` is correctly scoped (only `auth.login_post`)
- [ ] Is there any sensitive data in error messages or logs?
- [ ] Verify HTML sanitization in `document_viewer.py` works for crafted .docx files
- [ ] Are CSP headers set correctly? Do they block inline scripts?
- [ ] Does the `_login_attempts` TTL cleanup run correctly?

### AREA 9: ERROR HANDLING & EDGE CASES

- [ ] Do all routes have try/except for database operations?
- [ ] Are error pages (400, 403, 404, 405, 500) properly registered and rendering?
- [ ] Does the `schema_out_of_date` page trigger correctly? Verify the expected table list matches actual model `__tablename__` values
- [ ] Are storage errors handled gracefully (S3 down, file not found)?
- [ ] What happens on a bulk PDF import with 0 valid pages? With 100+ pages?
- [ ] What happens if a customer is deleted but their sales orders remain?
- [ ] What happens if storage returns an empty file?

### AREA 10: UX CONSISTENCY

- [ ] Verify ALL 17 admin dashboard cards link to working pages
- [ ] Verify all 11 document libraries are reachable and functional
- [ ] Is there consistent navigation across all modules (list → detail → edit → back)?
- [ ] Are confirmation dialogs present for ALL destructive actions?
- [ ] Do all list pages have consistent sorting?
- [ ] Is the CSS design system applied consistently across all templates?
- [ ] Are flash message categories (`success`, `danger`, `warning`, `info`) used consistently?

### AREA 11: CONFIGURATION & DEPLOYMENT

- [ ] Does `Dockerfile` build correctly?
- [ ] Does `scripts/release.py` run migrations and seeding properly?
- [ ] Are all required environment variables documented?
- [ ] Does `.gitignore` correctly exclude all binary/generated files?
- [ ] Are there any secrets or credentials in committed files?
- [ ] Is `requirements.txt` complete and version-pinned?
- [ ] Does `alembic.ini` contain a hardcoded database URL?

### AREA 12: CROSS-MODULE CONSISTENCY

- [ ] Do all modules that handle document uploads follow the same pattern? (validate size → read bytes → compute hash → store → create DB record)
- [ ] Do all modules use `utcnow()` from `app.eqms.utils` consistently? (Not `datetime.utcnow()`)
- [ ] Do all modules use `current_user()` from `app.eqms.utils` consistently? (Not a local `_current_user()` helper)
- [ ] Are all module `__init__.py` files registering blueprints the same way?
- [ ] Are flash message strings consistent in tone and format?

---

## Known Recent Changes (Context for the Auditor)

The following changes were recently made. Pay special attention to completeness and consistency of these:

1. **Datetime standardization** — All `datetime.utcnow()` replaced with `utcnow()` from `app.eqms.utils`. `onupdate=utcnow` added to `updated_at` columns. Verify no instances were missed.

2. **Circular import fix** — `ManagedDocument` import moved from top-level to lazy import in `validate_managed_document()`. `normalize_facility_name` / `extract_email_domain` import path corrected in `customer_profiles/service.py`. Verify no other circular paths exist.

3. **Schema health check** — Table name corrected from `approval_emls` to `approvals_eml`. Verify the full expected table list is accurate.

4. **Dashboard reorganization** — 4-column layout with NCRs and Employee Training moved to Silq Operations, CAPAs moved to QMS System. Verify all 17 cards link correctly.

5. **New libraries added** — `risk_management`, `dhfs`, `forms_templates_travelers` added to LIBRARIES dict. Verify routes exist, endpoints work, and the LIBRARY_ENDPOINTS dict is in sync.

6. **Centralized document viewer** — Integrated into 8+ modules. Verify ALL modules use it consistently.

7. **Security hardening** — CSRF on logout (POST), CSP headers, HTML sanitization, improved SECRET_KEY handling, cryptographic merge tokens. Verify nothing was broken.

8. **Consolidated `_current_user()`** — All modules should use `current_user()` from `app.eqms.utils`. Check for any remaining local `_current_user()` definitions.

---

## Output Format

Create `docs/audits/SYSTEM_AUDIT_FINDINGS_2026_03_11.md` with this structure:

```markdown
# SilqQMS System Audit Findings — March 11, 2026

**Audit Date:** 2026-03-11
**Auditor:** [agent name]
**Commit:** 0836bb1

## Executive Summary
[2-3 paragraphs: overall health, total findings count by severity, key risk areas]

## Legacy Code & Dead Code Identified
[List every piece of dead code found, with file path and line numbers]

### Dead Imports
| File | Import | Reason |
|------|--------|--------|

### Dead Routes (defined but never linked)
| Module | Route | Function |
|--------|-------|----------|

### Orphaned Templates (never rendered)
| Template Path | Expected Route |
|---------------|----------------|

### Unused Functions
| File | Function | Reason |
|------|----------|--------|

### Obsolete Scripts
| Script | Reason |
|--------|--------|

### Deprecated Model Columns
| Model | Column | Reason |
|-------|--------|--------|

## Findings

### Critical (Breaks functionality or causes data loss)
#### C-001: [Title]
- **Severity:** Critical
- **Location:** `[file path]`, line [N]
- **Description:** [What is wrong]
- **Impact:** [What breaks]
- **Reproduction:** [How to trigger]
- **Recommended Fix:** [Specific strategy]
- **Files to Modify:** [list]

### High (Significant bugs or security issues)
#### H-001: [Title]
...

### Medium (Functional issues, inconsistencies, UX problems)
#### M-001: [Title]
...

### Low (Cleanup, minor improvements, code quality)
#### L-001: [Title]
...

## Module-by-Module Health Report
[For each of the 12 modules: brief assessment, findings count, health grade A-F]

## Document Viewing Chain Verification
[For each of the 10 document-serving contexts: pass/fail status and notes]

## Recommended Priority Order
[Numbered list of which findings to fix first, grouped by theme]
```

---

## IMPORTANT NOTES FOR THE AUDITOR

1. **Be ruthless about dead code.** If a function is defined but never called anywhere in the codebase, flag it. If an import is unused, flag it. If a model column is written but never read (or vice versa), flag it. The goal is a lean, maintainable codebase.

2. **Trace every `url_for()` call.** In every template, follow every `url_for('blueprint.function', ...)` and verify the target exists, the argument names match, and the function is actually registered.

3. **Trace every import.** For each file, check that every import is used and that the imported symbol actually exists in the source module at the expected location.

4. **Check cross-module consistency exhaustively.** If `equipment/admin.py` handles document viewing one way and `suppliers/admin.py` handles it a slightly different way, that's a finding.

5. **Verify the complete LIBRARIES ↔ LIBRARY_ENDPOINTS ↔ route function ↔ dashboard card chain** for all 11 libraries. A mismatch anywhere breaks a library.

6. **Look for N+1 queries.** Routes that query a list and then access relationships without eager loading are performance issues.

7. **Test edge cases mentally.** For each form submission: What if every field is empty? What if the file is 0 bytes? What if the referenced ID doesn't exist? What if the user double-submits?

8. **Check the migration chain.** Verify it's linear (no multiple heads), all `down_revision` pointers are correct, and the chain can run cleanly from scratch.

9. **The system will soon have hundreds of documents uploaded.** Performance issues with list queries, eager loading, and pagination will matter.

10. **Commit and push your findings document when complete.** The findings will be reviewed and implemented by a separate agent.
