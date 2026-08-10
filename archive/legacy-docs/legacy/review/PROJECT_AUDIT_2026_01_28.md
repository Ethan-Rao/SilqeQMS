# Project Audit
**Date:** 2026-01-28

## Issues and fixes
- **P0** Topbar and document titles show "Silqe eQMS" instead of "Silq eQMS". Fix: update `app/eqms/templates/_layout.html` and `app/eqms/templates/public/index.html`.
- **P1** Admin home lists stub modules (Design Controls, Manufacturing File Output, Employee Training) that route to placeholders. Fix: remove these cards until implemented or replace with disabled "Coming soon" tiles; remove `admin.module_stub` and `admin/module_stub.html` if not used.
- **P1** Navigation renders links for any authenticated user without permission checks, leading to 403s. Fix: gate nav items by RBAC permissions and hide links the user cannot access.
- **P1** Public landing exposes internal "Health" link and an admin entry point before login. Fix: remove from UI and redirect `/` to login or a neutral landing page.
- **P1** Multiple destructive reset endpoints (`/admin/reset-data`, `/admin/maintenance/reset-all-data`, `/admin/customers/reset`) create high accidental-loss risk. Fix: consolidate into a single, guarded maintenance flow requiring superadmin + environment flag + reason.
- **P2** ShipStation "Run Sync" is enabled even when API credentials are missing. Fix: disable the action when `api_key_set` or `api_secret_set` is false and show setup guidance.
- **P2** Debug/diagnostic pages are available in production (`/admin/debug/permissions`, `/admin/diagnostics`, `/shipstation/diag`). Fix: restrict behind environment flags or remove from production routes.
- **P2** Deprecated `customer_name` hidden field remains in the distribution log edit form. Fix: remove once migration verifies `customer_id` is canonical.

## Legacy code to delete
- `admin.module_stub` route and `app/eqms/templates/admin/module_stub.html`.
- Admin index cards that route to stub modules (`design-controls`, `mfg-output`, `training`).
- Duplicate reset endpoints after consolidation (`/admin/maintenance/reset-all-data` or `/admin/reset-data`).
- Root-level sample artifacts (`*.pdf`, `*.docx`, `*.xlsx`) and local databases (`eqms.db`, `qa_eval.db`) once migrated to `storage/` or `docs/sample-data/`.
- Redundant `README.txt` if `README.md` is the canonical guide.

## Enhancements
- Add permission-aware navigation and a compact admin landing that groups modules by function (Traceability, QMS, Manufacturing, Admin).
- Add consistent empty states and next-step CTAs across list pages (e.g., "Import PDF", "Add Customer", "Log Entry").
- Add a System Status card for admins (DB, storage, ShipStation credentials, last sync) using existing diagnostics data.
- Add role-specific dashboards (rep vs admin) with tailored quick links and reduced clutter.
- Add inline help tooltips for key fields (SKU, lot, order number, reason for change) to reduce data entry errors.
