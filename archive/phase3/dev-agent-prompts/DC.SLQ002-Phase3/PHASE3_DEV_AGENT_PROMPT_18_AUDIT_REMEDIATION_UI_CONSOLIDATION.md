# Phase 3 — Prompt 18: System Audit Remediation + UI Consolidation

## Context

A full production health check was run on 2026-07-10 before this prompt. Data findings
and Ethan's explicit UI feedback are both incorporated below. This is a consolidation +
cleanup prompt — no new features.

---

## Health Check Findings

**Zero hard data issues.** Confirmed clean:
- Single alembic head `c3d4e5f6a7b8`
- 114 documents (94 Released, 20 Obsolete), 199 revisions, 199 files
- 1,029 admin_docs files across 11 libraries, 0 orphaned records
- 4 users (2 admin, 1 staff, 1 auditor), 0 test accounts
- 4 CAPAs seeded correctly
- 34 training assignments for ethanr@silq.tech, 0 acknowledged yet
- system_settings table is empty (quality objectives not entered yet — expected)

**Operational warnings (real data, not bugs):**
- Equipment overdue CAL: ST-006, ST-007, ST-011, ST-012, ST-013, ST-015
- Equipment overdue PM: ST-004, ST-008, ST-009, ST-016
- These are genuine service backlog items visible in the Equipment Schedule page

**Anomaly — legacy database tables:**
The production database contains tables that appear to be leftover from an earlier
development phase with no active code references:
`doctor_billing_data`, `doctors`, `hospital_doctor_affiliations`.
Also present but low-confidence: `quality_docs`, `training_docs`, `rep_documents`.

**Action for dev agent:**
1. Search the codebase for any imports/references to `Doctor`, `DoctorBillingData`,
   `HospitalDoctorAffiliation` models. If zero references exist, generate a migration
   to drop these three tables. If references exist, report to coordinator.
2. Similarly check `quality_docs`, `training_docs`, `rep_documents` — if not referenced
   by any active model or blueprint, propose dropping them (but wait for coordinator
   review before committing those drops; these three are lower-confidence).

---

## UI Consolidation (Ethan's explicit feedback)

Current QMS System column has 10 cards. Target is 6. Exact changes below.

### Change 1 — Move System Status strip to Admin Tools

The System Status strip (9 coloured tiles: overdue cal, overdue PM, etc.) currently
renders at the top of the main dashboard for all `admin.view` users, including staff.

**New location:** Move it to the Admin Tools page (`/admin/diagnostics`, gated
`admin.edit`). Remove it from the main dashboard template entirely. Staff should see a
clean dashboard without the operational noise.

The strip's data (`dashboard_stats`) should be computed only on the Admin Tools page,
not in the main dashboard route. Remove `dashboard_stats` from the `admin.index` view
function's context entirely.

Keep the quick-links below the strip (Equipment Schedule, Supplier Schedule, Quality
Objectives, CAPAs, Reports) — move those to the Admin Tools page as well.

### Change 2 — Remove DCO Log / Change History from dashboard column

The "DCO Log / Change History" card in the QMS System column is redundant: the DCO Log
is already accessible via the "DCO Log" button on the Document Control page header (added
in Prompt 7). Remove the card from the dashboard. Do not change the route or the button
on the Document Control page — just stop featuring it as a top-level dashboard card.

Similarly, remove the "QMS Document Index" card from the QMS System column. The QMS
Index is already a button on the Document Control page. Users can navigate to it from
there. Remove the dashboard card only.

### Change 3 — Merge CAPA Documents + CAPAs into one card

Currently there are two CAPA entries in QMS System:
- "CAPA Documents" → `/admin/capas-library` (admin_docs file browser)
- "CAPAs" → `/admin/capas` (structured tracker)

**Merge into one "CAPAs" card** pointing to `/admin/capas` (the structured tracker).
The CAPA detail page already links through to the admin_docs library subfolder for each
CAPA. Remove the standalone "CAPA Documents" card from the dashboard.

Also remove the "CAPA Documents" card from wherever else it appears (it was previously
in QMS System per the template; confirm it is fully removed from dashboard navigation).

### Change 4 — Remove Forms, Templates & Travelers from QMS System column

The `forms_templates_travelers` admin_docs library (6 files, 2 folders) is accessible
via global search and via the Admin_docs library browser if someone navigates there
directly. It does not need a dashboard card.

Remove the "Forms, Templates & Travelers" card from the QMS System column and from
any other dashboard column. The library will remain in the system and be accessible via
search — just not surfaced as a prominent navigation item. No data deletion.

### Change 5 — Combine Reports into one card

Currently there are two separate report cards:
- "Reports: What's Due" → `GET /admin/reports/due-this-period.csv`
- "Management Review Report" → `GET /admin/reports/management-review`

**Replace both with a single "Reports" card** pointing to a new lightweight landing
page `GET /admin/reports` (gated `admin.edit`) that lists both reports with a one-line
description and direct links/buttons. This is a minimal HTML page — no new data queries.

Update all existing `url_for('admin.reports_due_csv')` and
`url_for('admin.management_review')` references in templates to point users through
this landing page or directly to the report endpoints (either approach is fine; prefer
the landing page so the Reports card always has a stable URL).

### Resulting QMS System column (6 cards)

After the above changes, the column should contain exactly:
1. **Document Control** (was "Document Control (DCOs)") — rename to remove "(DCOs)"
   since the column title no longer needs to disambiguate
2. **CAPAs** (merged tracker + documents) → `/admin/capas`
3. **Quality Objectives** → `/admin/quality-objectives`
4. **Reports** → `/admin/reports`
5. **Admin Tools** → `/admin/diagnostics`
6. **My Account** → `/admin/me`

---

## Additional Cleanup

### Cleanup A — Dead code audit
Search the codebase for any routes, templates, or service functions that were added in
Prompts 1–17 and are now unreachable or superseded. Specifically check:
- Any route that pointed to `/admin/capas` as the admin_docs library (now `/admin/capas-library`)
  — ensure all `url_for('admin_docs.capas')` calls in templates point to the new path.
- Any `readonly` role references left in tests or seeds after Prompt 6's retirement.
- Any references to the deleted test documents (SRS-TEST-001 etc.) in test fixtures.

### Cleanup B — Drop legacy tables (doctors schema)
If the search in the health-check action above confirms zero references to the Doctor
models, generate and push an additive (destructive) migration to drop:
- `doctor_billing_data`
- `doctors`
- `hospital_doctor_affiliations`

Migration must include proper `upgrade()` (DROP TABLE) and `downgrade()` (recreate)
functions. Run `alembic heads` to confirm single head after adding it.

Do NOT drop `quality_docs`, `training_docs`, or `rep_documents` without coordinator
confirmation — hold those for Prompt 19 after we verify their usage.

### Cleanup C — Template fragment deduplication
The `_macros.html` breadcrumb and empty-state macros were added in Prompt 9. Confirm
they are being used consistently across all module list/detail pages (equipment, suppliers,
purchasing, supplies, CAPAs, training). Any page that rolls its own breadcrumb HTML
instead of using the macro should be updated to use `{{ breadcrumbs(...) }}`.

---

## Deploy Discipline

This is a UI/template-heavy prompt with one potential schema change (legacy table drop).
- All UI changes: no migration
- Legacy table drop: one migration (if confirmed dead code)
- Full test suite must pass; update any tests that reference removed dashboard cards or
  old URL patterns
- Import guard must pass
- Single migration head enforced

Tests to update/add:
- Dashboard: assert System Status strip tiles are NOT present in `admin.index` response
- Admin Tools page: assert System Status strip IS present for admin users
- QMS System column: assert DCO Log card, QMS Index card, CAPA Documents card, and
  Forms/Templates card are NOT in the dashboard response
- CAPAs card: assert one card pointing to `/admin/capas` is present
- Reports card: assert one card pointing to `/admin/reports` is present

---

## Deliverables

1. Main dashboard (`/admin`) shows clean 4-column layout with 6-card QMS System column.
2. Admin Tools page shows System Status strip with all tiles.
3. `/admin/reports` landing page lists both report types.
4. Legacy `doctors` tables dropped via migration (if confirmed dead).
5. All `url_for('admin_docs.capas')` → confirm routing works after path change.
6. Full suite green; coordinator confirms dashboard on live site before Prompt 19.
