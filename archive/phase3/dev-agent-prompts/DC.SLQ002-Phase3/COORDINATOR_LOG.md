# Phase 3 Coordinator Log

Rolling internal reference for the coordinator. Workflow (as of 2026-07-08): **one
self-contained dev-agent prompt file per kickoff** (no more single evolving doc). Dev agent
auto-deploys; coordinator reviews deploy logs and greenlights the next prompt.

## Deploy state
- Prod healthy on `55ea8e8` (E4). LIVE: Checkpoints 3-5, E1-E4, Prompts 6-9.
  Roles: `admin` + `staff` (+ external `auditor`); `readonly` retired and auto-migrated.
  Topbar menu trimmed (no Home/Search/Distribution Log; +NRE Projects) per Ethan.
  Latest migration head: z8a9b0c1d2e3. E-series (E1-E4) COMPLETE.
- **Track A COMPLETE:** 119 controlled documents, 210 revisions, 209 S3 files live in prod.
  Import Spaces key ([REDACTED_SPACES_KEY]) should be revoked by Ethan if not already done.
- A checkpoint is "shipped" ONLY when DO logs show `=== SilqQMS release done ===` +
  gunicorn listening + `/healthz` 200. Local green tests are NOT proof of a live deploy.

## Root causes found (keep in mind)
1. **Silent rollback since Checkpoint 3:** committed `purchasing/admin.py` imported
   `merge_import_metadata` / `parse_po_hints_from_filename`, but their defs in
   `parsers/pdf.py` were left uncommitted. Alembic imports the app at release time ->
   `release.py` crashed non-zero -> DO auto-rolled back every deploy. Fixed in `8249067`.
   Guard: pre-push `import app.wsgi` from a CLEAN checkout.
2. **Staff dashboard "unchanged":** the `staff` role seeding is correct (full read-only
   across all modules). The live team account `silqrepservice@gmail.com` was on the legacy
   **`readonly`** role (`{admin.view, docs.view}` only), which renders exactly the limited
   card set observed. **Decision (Ethan): delete `readonly`; keep only `admin` + `staff`
   (and `auditor` for the external portal).** Prompt 6 has the dev agent remove `readonly`
   from seeding, auto-migrate any `readonly` user -> `staff` (fixes silqrepservice on next
   deploy, no manual step), retarget SW.SLQ010 TC8 access-control coverage to the `staff`
   role, and restrict account-management role choices to admin/staff/auditor.
   QA follow-up: SW.SLQ010 is a controlled doc naming the read-only tester role -- may need a
   doc update/DCO for readonly->staff.

## Key facts / gates
- Dashboard cards: QM/records cards gate on `has_any_perm("admin.view","staff.view")`;
  operational + external cards gate on specific `*.view` perms; `Admin Tools` gates on
  `admin.edit` (staff never gets it). `staff` role holds all needed `*.view`.
- `readonly` = `{admin.view, docs.view}` -- BEING DELETED in Prompt 6 (folded into `staff`).
  `auditor` = `auditor_portal.access` (kept, external portal).
- Global search: `search.global_search`, GET, `/admin/search`, param `q`.
- Deploy pipeline: `scripts/start.py` -> `scripts/release.py` (alembic upgrade head + seed) -> gunicorn.

## Prompt series (Phase 3)
- Prompts 1-5: staff access, module review, housecleaning, reconciliation Part A, E1 (done/live).
- **Prompt 6 (SHIPPED `a674d54`):** retire `readonly`, dashboard search box, import guard.
- **Prompt 7 (SHIPPED `07639d2`):** E2 -- QMS Document Index + in-app DCO Log. No migration.
- **Prompt 8 (SHIPPED `838f7d3`):** E3 -- training revision targeting (added nullable
  `document_revision_id`, migration z8a9b0c1d2e3) + related-documents via shared `slq_family()`.
- **Prompt 9 (SHIPPED `55ea8e8`):** E4 -- usability and readiness sweep. No migration. E-series DONE.
- **Track A (COMPLETE):** 119 docs / 210 revisions / 209 S3 files live. One-off script
  `scripts/_run_prod_import.py`. Spaces key should be revoked.
- **Prompt 10 (COMPLETE -- coordinator executed cleanup):** 5 test docs, 50 admin_docs files,
  3 folders, and 2 test user accounts deleted from production. Script not committed.
- **Prompt 11 (COMPLETE -- shipped `d86168c`/`e6e13ae`):** --recursive importer deployed +
  Phase 4 records import complete: 1,029 files / 138 folders across 11 libraries.
- **Prompt 12 (COMPLETE -- coordinator ran scripts directly):** Phase 5 module data
  populated. 17 equipment records seeded + 125 files attached. 22 suppliers created + 95
  files attached. Purchasing folder inspected (149 PO PDFs + importable xlsx PO log).
- **Prompt 13 (COMPLETE -- deployed `d3c5a09`, coordinator ran A/B/C):** PO log imported
  (156 POs + 149 PDFs attached). 12 supply records + 18 files. Module UX improvements
  deployed: Equipment due-date summary bar, grouped document sections, Supplier expiry
  flags, global search extended to Equipment + Suppliers.
- **Prompt 14 (COMPLETE -- deployed `98b061a`, coordinator ran A/B):** Dashboard status
  strip, admin_docs in-library search + folder counts, supplier PO panel deployed.
  67 POs linked to supplier records; 7 equipment-supplier service associations created.
  36 unmatched PO vendors are genuinely non-QMS (Amazon, NAMSA, Bentec, etc.) -- left NULL.
- **Prompt 15 (COMPLETE -- deployed `3480555`, coordinator ran Task B):** Training UX
  deployed (progress bar, bulk-assign, CSV export, overdue badge). 34 training assignments
  created for ethanr@silq.tech covering DCO091-095 (due 2026-07-31; QM.SLQ052 due 2026-07-15).
  Training matrix parsed -> `docs/training_matrix_parsed.json`. `bulk_assign_by_matrix.py`
  committed for future employee onboarding.
- **Prompt 16 (COMPLETE -- deployed `c6192b5`):** Equipment cal/PM schedule, supplier
  re-eval schedule, quality objectives page (obj 4 auto-computed from training data),
  "What's Due" period report CSV. Migration `f1a2b3c4d5e6` (system_settings table).
- **Prompt 17 (COMPLETE -- deployed `c7be8cf`, coordinator seeded 4 CAPAs):** CAPA tracker
  live (`/admin/capas`), migration `c3d4e5f6a7b8`. CAPA001-004 seeded. Management review
  report live at `/admin/reports/management-review` (HTML + CSV, 8 ISO 13485 sections).
- **Prompt 18 (SHIPPED `b48b480`):** System audit + UI consolidation. Dropped 3 legacy
  doctor tables (migration d4e5f6a7b8c9). Dashboard QMS System column: 10 cards -> 6.
  System Status strip moved to Admin Tools. DCO Log + QMS Index cards removed from dash.
  Two CAPA cards merged into one. Forms/Templates card removed. Two Reports cards merged
  into one landing page at `/admin/reports`. Suite: 219 passed, 1 skipped.
- **Prompt 19 (SHIPPED -- confirmed live):** Final polish. Legacy tables (quality_docs,
  training_docs, rep_documents) dropped. Breadcrumbs on all module pages. Quality
  Objectives empty-state guidance. Admin Tools overdue context note. earao72419 account
  deletion script written (coordinator to run).
- **Folder setup (coordinator, 2026-07-14):** Merged CAPA duplicate folders (CAPA001,
  CAPA002 consolidated). Created Risk Management product subfolders (C.SLQ001 Pathway,
  SLQ-211410SPT, SLQ-211610SPT, SLQ-211810SPT, General). Created NCR year subfolders
  (2022-2026).
- **Prompt 20 (SHIPPED `2957838`, coordinator ran Task E 2026-07-14):** QM Documents
  browse view at /admin/modules/document-control/browse. Accordion grouped by 16
  subsystems; forms/templates expand under parent SOPs; client-side search. Dashboard
  QM Documents card -> browse. Quality Objectives renamed Quality Planning, moved to
  Quality Management column. DHF library renamed Design & Development Records.
  Data migration: Device Master Record (44 files) + Project Archives (33 files) moved
  to dhfs; Quality Planning folder (2 files) moved to management_reviews. Suite: 230
  passed.

## Pending manual action for Ethan
- Confirm Prompt 18 DO deploy log shows release done (migration d4e5f6a7b8c9 ran)
- After Prompt 19 ships: coordinator runs _delete_user.py (dry-run then live)
- Spaces key ([REDACTED_SPACES_KEY]) still active -- revoke when convenient
