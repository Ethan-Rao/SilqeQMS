# SYSTEM AUDIT PROMPT — SilqQMS Comprehensive Debug & Review

**Date:** 2026-03-10  
**Objective:** Perform a thorough audit of the entire SilqQMS application. Identify every bug, inconsistency, UX issue, missing feature, dead code, and potential failure. Produce a structured findings document — do NOT implement any changes.

---

## Your Mission

You are a QA/audit agent assigned to review a Flask-based Quality Management System (SilqQMS) for a medical device company. Your job is to go through every file, every route, every template, every model, and every script — and document everything that is wrong, broken, inconsistent, or improvable.

**Output:** A single Markdown document titled `SYSTEM_AUDIT_FINDINGS_2026_03.md` placed in `docs/audits/`. It must be structured with numbered findings, severity levels, affected files, and a recommended fix strategy for each issue.

**CRITICAL:** Do NOT modify any code. Do NOT fix anything. Only read, analyze, and document.

---

## System Overview

SilqQMS is a Flask application deployed on Render (with PostgreSQL + S3 storage). It manages:

- **Quality Management Documents** — document libraries for QMS policies, SOPs, work instructions
- **Document Control (DCOs)** — formal document change orders with version control
- **Distribution Log** — tracking medical device shipments via ShipStation sync + manual CSV import
- **Sales Orders** — parsed from uploaded bulk PDFs, matched to distribution entries
- **Customer Profiles** — auto-created from sales orders, with address/history tracking
- **NRE Projects** — non-recurring engineering projects (customers with sales orders but no matched distributions)
- **Sales Dashboard** — metrics, lot tracking, inventory by lot
- **Equipment** — equipment inventory, calibration tracking, document attachments
- **Suppliers** — approved supplier management with document attachments
- **Supplies** — consumables inventory with document attachments
- **Manufacturing** — lot tracking for suspension production (C.SLQ001), document attachments, work orders
- **Purchasing** — purchase orders with PDF import and EML confirmation viewing
- **ShipStation Sync** — API integration to pull distribution data
- **Admin Tools** — diagnostics, data reset, user accounts, audit log
- **Admin Doc Libraries** — 8 document libraries (QMS Documents, Employee Training, Management Reviews, NCRs, CAPAs, Post Market Surveillance, Regulatory Standards, Work Orders)

### Tech Stack
- **Backend:** Flask, SQLAlchemy ORM, Alembic migrations, PostgreSQL (prod) / SQLite (dev)
- **Frontend:** Server-rendered Jinja2 templates, custom CSS design system (dark theme)
- **Storage:** Abstract Storage class → LocalStorage or S3Storage
- **Auth:** Session-based, RBAC with permissions, CSRF protection
- **File Viewing:** Centralized `document_viewer.py` handles .docx (mammoth→HTML), .xlsx/.csv (openpyxl→HTML table), PDF/images/text (native browser)
- **PDF Parsing:** pdfplumber + PyPDF2 for sales orders, shipping labels, purchase orders
- **External API:** ShipStation REST API for distribution sync

---

## File Structure to Audit

### Core Application Files
```
app/eqms/__init__.py          — App factory, blueprint registration
app/eqms/config.py            — Settings from env vars
app/eqms/db.py                — SQLAlchemy engine/session management
app/eqms/models.py            — Core models (User, Role, Permission, AuditEvent, Base)
app/eqms/auth.py              — Login/logout, session management, rate limiting
app/eqms/admin.py             — Admin dashboard, diagnostics, data reset, user accounts
app/eqms/rbac.py              — @require_permission decorator
app/eqms/security.py          — CSRF token helpers
app/eqms/audit.py             — record_event() for audit trail
app/eqms/storage.py           — LocalStorage, S3Storage, storage_from_config()
app/eqms/document_viewer.py   — Centralized .docx/.xlsx/.csv → HTML rendering
app/eqms/utils.py             — allow_inline_view(), parse_custom_fields()
app/eqms/constants.py         — Application constants
app/eqms/routes.py            — Public routes (index, health check)
```

### Modules (each has admin.py routes, models.py, service.py)
```
modules/admin_docs/            — 8 document libraries (QMS, training, NCRs, CAPAs, etc.)
modules/customer_profiles/     — Customer CRUD, notes, merge, address tracking
modules/document_control/      — DCO lifecycle (draft → released → obsolete)
modules/equipment/             — Equipment inventory, calibration, documents, suppliers
modules/manufacturing/         — Lot tracking, DHR documents, work orders
modules/nre_projects/          — NRE project dashboard and detail pages
modules/purchasing/            — Purchase orders, PDF import, EML viewing
modules/rep_traceability/      — Distribution log, sales orders, PDF import, tracing reports, sales dashboard, approval EMLs
modules/shipstation_sync/      — ShipStation API client, CSV parsing, lot log
modules/suppliers/             — Supplier management, documents, equipment links
modules/supplies/              — Supply inventory, documents, supplier links
```

### Templates
```
templates/_layout.html                    — Base layout (nav, flash messages, CSS)
templates/admin/index.html                — Admin dashboard (4-column layout)
templates/admin/document_viewer.html      — Universal .docx/.xlsx viewer
templates/admin/admin_docs/index.html     — Document library browser
templates/admin/customers/detail.html     — Customer profile (tabs: info, sales orders, distributions, notes)
templates/admin/distribution_log/*.html   — Distribution log CRUD + import
templates/admin/equipment/*.html          — Equipment CRUD
templates/admin/manufacturing/*.html      — Manufacturing lot CRUD
templates/admin/purchasing/*.html         — Purchase order CRUD + import
templates/admin/sales_dashboard/index.html — Sales metrics + lot inventory
templates/admin/sales_orders/*.html       — Sales order list, detail, import, unmatched
templates/admin/suppliers/*.html          — Supplier CRUD
templates/admin/supplies/*.html           — Supply CRUD
templates/admin/nre_projects/*.html       — NRE dashboard + detail
templates/admin/tracing/*.html            — Tracing reports
templates/admin/shipstation/*.html        — ShipStation sync UI
templates/admin/accounts/*.html           — User account management
templates/admin/me.html                   — Current user profile
templates/admin/diagnostics.html          — System diagnostics page
templates/admin/reset_data.html           — Data reset page
templates/admin/audit/list.html           — Audit log viewer
templates/errors/*.html                   — Error pages (400, 403, 500, schema_out_of_date)
templates/auth/login.html                 — Login form
templates/public/index.html               — Public landing page
```

### Scripts
```
scripts/init_db.py                          — Seed permissions, roles, admin user
scripts/_db_utils.py                        — Reusable script_session context manager
scripts/attach_admin_role.py                — Assign admin role to user
scripts/backfill_customer_addresses.py      — Backfill customer addresses from sales orders
scripts/backfill_sales_order_matching.py    — Backfill sales order → distribution matching
scripts/bulk_import_admin_docs.py           — Bulk import documents from local directory
scripts/cleanup_pdf_import_distributions.py — Clean up orphaned distribution entries from PDF import
scripts/cleanup_zero_order_customers.py     — Remove customers with no orders
scripts/dedupe_customers.py                 — Deduplicate customer records
scripts/import_equipment_and_suppliers.py   — Import equipment/supplier data
scripts/rebuild_customers_from_sales_orders.py — Rebuild customer records from sales order data
scripts/refresh_customers_from_sales_orders.py — Refresh customer addresses from parsed PDFs
scripts/release.py                          — Deployment release script (migrations + seed)
scripts/start.py                            — Gunicorn start wrapper
```

### Other
```
migrations/versions/*.py       — 27 Alembic migration files
tests/*.py                     — Test files
app/eqms/data/LotLog.csv      — Lot log reference data
app/eqms/static/design-system.css — Global CSS
requirements.txt               — Python dependencies
Dockerfile                     — Container build
alembic.ini                    — Alembic config
```

---

## Audit Checklist — What to Examine

### 1. ROUTES & ENDPOINTS
For every route in every module's `admin.py`:
- [ ] Does it have the correct `@require_permission` decorator?
- [ ] Does it validate all user inputs (form data, query params, file uploads)?
- [ ] Does it handle missing/invalid data gracefully (flash message, not 500 error)?
- [ ] Are all `url_for()` references valid (correct blueprint name, correct function name, correct arguments)?
- [ ] Do POST routes have CSRF protection?
- [ ] Do redirects after actions point to sensible destinations?
- [ ] Are database transactions properly committed/rolled back?
- [ ] Are there any routes that should exist but don't (e.g., missing delete, edit, or export functionality)?

### 2. TEMPLATES
For every Jinja2 template:
- [ ] Are all `url_for()` calls valid and correctly parameterized?
- [ ] Are all variables properly escaped with `|e` where needed?
- [ ] Do all forms include CSRF tokens?
- [ ] Do all forms have the correct `action` URL and `method`?
- [ ] Are there broken links, missing buttons, or UI elements that reference nonexistent routes?
- [ ] Is the navigation consistent (breadcrumbs, back buttons, sidebar links)?
- [ ] Are flash message categories handled consistently?
- [ ] Do all pages extend `_layout.html`?
- [ ] Are there hardcoded strings that should be dynamic?
- [ ] Do tables handle empty states gracefully ("No records found" instead of empty tables)?

### 3. MODELS & DATABASE
For every SQLAlchemy model:
- [ ] Are foreign keys correct with appropriate `ondelete` behavior?
- [ ] Are nullable/non-nullable constraints correct?
- [ ] Are indexes defined for commonly queried columns?
- [ ] Are relationship `back_populates` / `cascade` settings correct?
- [ ] Are there orphan-deletion issues (deleting a parent without cleaning children)?
- [ ] Do all models have appropriate `__repr__` for debugging?
- [ ] Are there any circular dependency issues between models?

### 4. MIGRATIONS
- [ ] Is the migration chain linear (no multiple heads)?
- [ ] Do all migrations have correct `down_revision` pointers?
- [ ] Are there any migrations that reference columns/tables that no longer exist?
- [ ] Can the full migration chain run cleanly from scratch on a fresh database?

### 5. STORAGE & FILE HANDLING
- [ ] Does `storage_from_config()` handle all edge cases?
- [ ] Are storage keys built consistently across all modules?
- [ ] Do all file upload routes validate file size and type?
- [ ] Are there any orphaned storage files possible (upload succeeds but DB insert fails)?
- [ ] Does the document viewer handle all claimed file types correctly?
- [ ] Are download routes properly authenticated?
- [ ] Does `allow_inline_view()` correctly categorize all file types?

### 6. PARSERS (PDF, CSV, ShipStation)
- [ ] Sales order PDF parser: Does it handle multi-page PDFs, missing fields, malformed tables?
- [ ] Distribution CSV parser: Does it handle encoding issues, missing columns, duplicate rows?
- [ ] Purchase order PDF parser: Does it handle all PO formats?
- [ ] ShipStation sync: Does it handle API rate limits, missing fields, pagination?
- [ ] Lot log parser: Does it handle missing dates, duplicate lot entries, encoding?
- [ ] Are parser errors surfaced to the user clearly (not swallowed silently)?

### 7. BUSINESS LOGIC
- [ ] NRE classification: Are NRE projects correctly identified (sales orders with NO matched distributions)?
- [ ] Customer matching: Does `find_or_create_customer` / `canonical_customer_key` handle all edge cases?
- [ ] Lot corrections: Are ShipStation lot typos properly corrected everywhere they appear?
- [ ] Sales dashboard calculations: Are Produced/Distributed/Remaining counts accurate?
- [ ] Distribution auto-matching: Does it correctly match sales orders to ShipStation entries?
- [ ] Address extraction: Does the Sold To parser handle all address formats?
- [ ] Are there any places where business logic is duplicated instead of centralized?

### 8. AUTHENTICATION & SECURITY
- [ ] Is every admin route protected by `@require_permission`?
- [ ] Are there any routes accessible without login?
- [ ] Does rate limiting work correctly for login attempts?
- [ ] Are CSRF tokens validated on all state-changing requests?
- [ ] Is the session lifetime reasonable?
- [ ] Are passwords hashed properly?
- [ ] Is there any sensitive data in error messages or logs?
- [ ] Are SQL injection risks mitigated (all queries using ORM, no raw SQL with user input)?

### 9. ERROR HANDLING
- [ ] Do all routes have try/except for database operations?
- [ ] Are error pages (400, 403, 500) properly registered?
- [ ] Does the schema_out_of_date error page trigger correctly?
- [ ] Are storage errors handled gracefully?
- [ ] Are API errors (ShipStation) handled with user-friendly messages?

### 10. UX CONSISTENCY
- [ ] Is the 4-column admin dashboard complete and all links working?
- [ ] Can every document library be reached from the dashboard?
- [ ] Is the document viewer accessible from every module that has documents?
- [ ] Are "View" and "Download" buttons present everywhere documents appear?
- [ ] Do all list pages have consistent sorting, filtering, and pagination?
- [ ] Do all detail pages have consistent navigation (back button, edit link, delete option)?
- [ ] Are confirmation dialogs present for destructive actions (delete)?
- [ ] Is the CSS design system applied consistently?

### 11. DATA INTEGRITY
- [ ] Can the system handle a data reset cleanly?
- [ ] Are there any hard-coded references to specific database IDs?
- [ ] Do bulk imports handle partial failures correctly (rollback)?
- [ ] Are there any race conditions in concurrent requests?

### 12. DEAD CODE & CLEANUP
- [ ] Are there any unused imports in any Python file?
- [ ] Are there any routes defined but never linked from any template?
- [ ] Are there any templates that are never rendered?
- [ ] Are there any model columns that are defined but never read or written?
- [ ] Are there any utility functions that are never called?
- [ ] Are there any scripts that are obsolete given the current codebase?
- [ ] Are there loose files in the project root that don't belong?

### 13. DEPLOYMENT & CONFIGURATION
- [ ] Does `Dockerfile` build correctly?
- [ ] Does `scripts/release.py` run migrations and seeding properly?
- [ ] Does `scripts/start.py` start gunicorn with correct settings?
- [ ] Are all required environment variables documented?
- [ ] Does `.gitignore` correctly exclude all binary/generated files?
- [ ] Are there any secrets or credentials accidentally committed?

### 14. TESTS
- [ ] Do existing tests pass?
- [ ] What test coverage exists? What critical paths have no tests?
- [ ] Are there any test files that test deleted or changed functionality?

---

## Output Format

Create `docs/audits/SYSTEM_AUDIT_FINDINGS_2026_03.md` with this structure:

```markdown
# SilqQMS System Audit Findings — March 2026

**Audit Date:** [date]
**Auditor:** [agent name]
**Commit:** [current HEAD commit hash]

## Executive Summary
[2-3 paragraph overview of system health, number of findings by severity]

## Findings

### Critical (Breaks functionality or causes data loss)
#### C-001: [Title]
- **Severity:** Critical
- **Location:** `[file path]`, line [N]
- **Description:** [What is wrong]
- **Impact:** [What breaks or goes wrong for the user]
- **Reproduction:** [How to trigger this]
- **Recommended Fix:** [Specific strategy]
- **Files to Modify:** [list]

### High (Significant bugs or security issues)
#### H-001: [Title]
[same structure]

### Medium (Functional issues, inconsistencies, UX problems)
#### M-001: [Title]
[same structure]

### Low (Cleanup, minor improvements, code quality)
#### L-001: [Title]
[same structure]

## Module-by-Module Status
[For each module: brief health assessment, number of findings]

## Recommended Priority Order
[Numbered list of which findings to fix first]
```

---

## Important Notes for the Auditor

1. **Be extremely thorough.** Read every single file. Do not skim. Follow every `url_for()` to its destination. Follow every foreign key to its model. Follow every template variable to its source.

2. **Test mentally.** For each route, imagine: "What happens if I submit an empty form? What if the referenced ID doesn't exist? What if storage is down? What if the file is 500MB?"

3. **Check cross-module consistency.** If one module handles document viewing one way and another does it differently, that's a finding.

4. **Look for silent failures.** Code that catches `Exception` and does nothing (or just logs) is a bug if the user should be notified.

5. **Verify the data flow.** Follow data from upload → parse → store → display. Are there any points where data can be lost or corrupted?

6. **Check the templates carefully.** Missing `|e` escaping, broken `url_for` calls, and forms with wrong `action` URLs are some of the most common bugs.

7. **Review each migration file.** Ensure the chain is unbroken and there are no conflicting table/column definitions.

8. **The system recently underwent major changes:** NRE classification logic, customer naming, lot tracking, PDF naming, document libraries, and a centralized document viewer. Pay special attention to these areas for incomplete or inconsistent implementation.

9. **There are loose files in the project root** (PDFs, .docx, .xlsx) that appear to be test/import files. Note whether these should be cleaned up.

10. **The admin dashboard has 4 columns** — verify every link goes to a real, working page.
