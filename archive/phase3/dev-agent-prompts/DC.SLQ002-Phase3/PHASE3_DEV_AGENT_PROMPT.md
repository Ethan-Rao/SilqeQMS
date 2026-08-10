# Phase 3 Dev Agent Prompt
# DC.SLQ002 - SilqQMS EDMS Transition: System Readiness and Data Migration

Prepared by: Phase 3 Coordinator agent
For use by: Development agent
Workspace root: C:\Users\Ethan\OneDrive\Desktop\SilqQMS
Production site: silqeqms.com (DigitalOcean App Platform, Cloudflare DNS, DO Spaces storage)
Repository: Ethan-Rao/SilqeQMS

---

## 0. Read this first

You are the development agent for Phase 3 of the SILQ eQMS EDMS transition. Ethan Rao (sole QA/RA/R&D) has approved the decisions in this prompt. Ethan is not a programmer. You perform all code changes, testing, and deployment. Ethan reviews the running site.

Two hard sequencing rules:

1. Deliver code improvements first (Section 5), get Ethan's review and approval, and only then perform the document staging and production data load (Section 6). Do not load documents into production until the code improvements are approved. Ethan asked for strong emphasis on system readiness and usability before any documents are rushed in.
2. Never modify the content of controlled QMS documents (the Word or PDF files). You work on the codebase, the staging folder structure, and the import tooling only.

Writing convention for any document text or paste block you produce for Ethan: do not use asterisk characters. Use headers, plain sentences, and dash bullets.

Before writing any code, read the files in Section 2 and confirm your understanding of the existing patterns. Reuse existing patterns; do not reinvent auth, RBAC, storage, audit, or the document viewer.

---

## 1. Confirmed decisions from Ethan

These are settled. Do not re-litigate them; implement them.

1. System of record for controlled documents:
   - Only the QM documents in the QM.SLQ family (QM.SLQ001 through QM.SLQ052), including their controlled Forms (FM#-QM.SLQxxx) and Templates (TMP#-QM.SLQxxx), are formally controlled with full Draft, Released, Obsolete lifecycle, revision letters, effective dates, and change reasons. These live in the Document Control module.
   - Everything else (CAPAs, audits, DHF and V&V records, risk management files, management reviews, equipment, suppliers, purchasing, post-market, NCMR, training records, DMR artifacts, distribution) is treated as simple files in the admin_docs libraries. No lifecycle needed on those.
2. Staging folder location: a new top-level folder at the workspace root. Use eQMS_Upload_Staging\.
3. DCO095 timing: treat DCO095 as released now. The QM.SLQ052 family is uploaded as Released Rev A, the 20 superseded design documents are marked Obsolete, and the six revised documents go in at their new revisions.
4. Prior revisions: upload superseded revisions as Obsolete or prior-revision records so version history is preserved in the eQMS. Current released revisions must be clearly the active version.
5. Team access: build a non-admin staff role plus a read-only staff experience. Staff can see the whole dashboard content in read-only form, minus admin tools and minus any create, edit, upload, release, obsolete, delete, import, or maintenance action. Ethan alone performs all uploads and edits for now.
6. Training: build a read-and-acknowledge training feature with per-person assignment. Ethan assigns specific documents or training items to specific people; each staff member sees a personal My Training queue of items to read and acknowledge, and acknowledgements are recorded with a timestamp and audit event.
7. Deployment: you perform all deployment. Code ships by pushing to the GitHub repository, which DigitalOcean App Platform auto-builds and releases. The production document load runs from the local machine against the production database and DO Spaces bucket (see Section 7). Ethan will provide the production environment values needed for the data load.
8. Audit trail fresh start: the compliance audit trail (audit_events) is append-only and validated. Do not wipe it as part of routine work. A clean audit cutover, if desired, is a deliberate go-live step planned for after Phase 4 training. Do not build anything that silently clears audit history.

---

## 2. Files and code to read before you start

Project and transition context:
- docs\QMS-Readable-Texts\20-QMSInProcess\DC.SLQ002\DC.SLQ002 A Design Project Plan, SilqQMS EDMS Transition.md
- docs\DCO094\DCO094_DCO_FORM_COMPLETION_GUIDE.md (the 19 items DCO094 released; these are current released versions)
- docs\DCO095\DCO095_DCO_FORM_COMPLETION_GUIDE.md (the 34 items: 8 new, 6 revised, 20 obsoleted)
- QM_DOCUMENT_REGISTER.csv (authoritative list of documents, revisions, and source folders)

eQMS codebase (core):
- app\eqms\__init__.py (create_app, blueprint registration, CSRF, CSP, schema-health gate)
- app\eqms\config.py (env-driven config)
- app\eqms\auth.py (login, logout, load_current_user, post-login redirect)
- app\eqms\rbac.py (require_permission, user_has_permission)
- app\eqms\audit.py (record_event, append-only)
- app\eqms\storage.py (LocalStorage, S3Storage, storage_from_config)
- app\eqms\models.py (User, Role, Permission, AuditEvent; bottom-of-file module model imports for the schema-health gate)
- app\eqms\admin.py (admin shell, account management, diagnostics, maintenance)
- app\eqms\document_viewer.py (needs_server_render, render_document_to_response)

Document systems:
- app\eqms\modules\document_control\models.py (Document, DocumentRevision, DocumentFile; states Draft, Released, Obsolete; one file per revision; doc_number unique)
- app\eqms\modules\document_control\service.py (next_revision, normalize_doc_number, parse_effective_date, file hashing)
- app\eqms\modules\document_control\admin.py (create, upload, release, revise, obsolete, view, download)
- app\eqms\modules\admin_docs\models.py (AdminDocFolder, AdminDocFile; library_key + folder tree)
- app\eqms\modules\admin_docs\admin.py (the 11 LIBRARIES map and library views)
- app\eqms\modules\admin_docs\service.py (create_folder, upload_document, storage key builder)

Templates and navigation:
- app\eqms\templates\_layout.html (global layout and top bar with permission-gated nav)
- app\eqms\templates\admin\index.html (dashboard, 4-column card grid)
- app\eqms\templates\admin\modules\document_control\*.html (list, new, detail)
- app\eqms\templates\admin\admin_docs\index.html (library browser)

Seed, scripts, deployment:
- scripts\init_db.py (seed_only; permissions, roles admin/auditor/readonly, admin user)
- scripts\bulk_import_admin_docs.py (existing local bulk import pattern for admin_docs)
- scripts\release.py and scripts\start.py (DO release phase: alembic upgrade head then seed)
- Dockerfile and README.md (deployment and runbook)
- docs\07_DEPLOYMENT_DIGITALOCEAN_CLOUDFLARE.md (App Platform + Cloudflare)
- migrations\ (Alembic; find current head before adding a migration)

Tests to model your new tests on:
- tests\test_document_control.py
- tests\test_edms_improvements.py

Reference example of an isolated feature with its own model, migration, seed, routes, templates, and tests:
- docs\DEV_AGENT_PROMPT_AUDITOR_FILES_PORTAL.md and app\eqms\modules\auditor_portal\*

---

## 3. Current-state summary you must understand

There are two parallel document repositories today:

- Document Control module (dashboard card Document Control (DCOs), routes under /admin/modules/document-control): the validated EDMS from SW.SLQ007 through SW.SLQ012. It implements the Draft, Released, Obsolete lifecycle, revision letters, effective dates, release reason, obsolete reason, and a full audit trail. It is currently empty of real documents and has no library or subsystem categorization and no browse-by-subsystem view. It enforces one document per doc number and one file per revision.
- admin_docs module (the 11 dashboard libraries): a folder and file browser with no lifecycle, no revisions, no doc number or effective date. bulk_import_admin_docs.py loads files here.

Eleven admin_docs libraries exist: qms_documents, employee_training, management_reviews, ncrs, capas, post_market_surveillance, regulatory_standards, work_orders, risk_management, dhfs, forms_templates_travelers.

Access model today: everything is under /admin/* gated by admin.view. Seeded roles are admin (full), auditor (portal only), readonly (admin.view plus docs.view). There is no staff or team-member role and no read-only staff experience. Account creation exists at /admin/accounts.

There is no training module in code. Employee Training is only a file library. The module spec describes assignments and completions, but none of that exists yet.

Deployment today: live at silqeqms.com on DigitalOcean App Platform, Cloudflare DNS, storage backend s3 pointing at DO Spaces bucket raoeqms-files. Ethan is the only user. An external auditor account was used once successfully. No team member has logged in. Ethan currently uses the Distribution folder, LotLog upload, ShipStation sync, and Sales Dashboard.

Important git and image facts: the source QMS document folders (QM Documents, CAPAs, DHF, and so on) and loose pdf, docx, xlsx files at the repo root are git-ignored on purpose. Only Auditor Files\ is un-ignored and shipped in the image. Therefore documents are not shipped in the Docker image and must be loaded into production from the local machine against the production database and Spaces bucket. Do not commit the source documents to git and do not add large binary document trees to the image.

---

## 4. Global constraints

- Do not break existing functionality. Every change is backwards-compatible or is accompanied by a forward Alembic migration. The existing rep traceability, customer profiles, ShipStation sync, sales dashboard, admin_docs, document_control, and auditor_portal features must keep working exactly as they do now for the admin user.
- Any new model must be added to the bottom-of-file import block in app\eqms\models.py so the schema-health gate in create_app sees it, and must ship with its Alembic migration in the same change. Confirm alembic upgrade head succeeds on a fresh SQLite database and does not error re-applying.
- Reuse require_permission for authorization, record_event for audit, storage_from_config for files, and the document_viewer for in-browser viewing. Do not add SaaS viewers.
- Respect CSRF on all new POST forms (include the csrf_token field) and do not weaken CSP. Do not embed PDFs via iframe or object; serve them as application/pdf on their own URL.
- Do not hard-code secrets. Read configuration from current_app.config, which is populated in config.py.
- Produce working, tested code. Add pytest tests for every new behavior, following the fixtures in tests\test_edms_improvements.py (cherry-picked Base.metadata.create_all for the tables a test needs, CSRF helper, login helper).
- Keep the readonly role as-is; tests depend on its exact permission set (admin.view plus docs.view). Introduce the staff role as a new role, do not repurpose readonly.

---

## 5. Track B: code improvements (deliver and get approval before Track A)

Deliver this track first. Group the work by priority. Ethan wants system readiness and usability, not a rushed import.

### Priority 1: staff access, read-only experience, and the controlled-document experience

P1.1 Staff role and permissions.
- Problem: there is no non-admin role and no way for a team member to log in and read documents without full admin power.
- Desired behavior: seed a new role staff. Introduce read-only view permissions that the staff role carries and that gate viewing without granting any mutation. Introduce or reuse view permissions per area (for example docs.view already exists for the document control module; add read-only view permissions for the admin_docs libraries and for each area shown on the dashboard, or add a single coarse staff.view that the read-only routes accept in addition to admin.view). Whatever approach you choose, a staff user must be able to open a page and read and view and download document content, and must receive a 403 on every create, edit, upload, release, obsolete, delete, import, maintenance, account, and diagnostics route.
- Implementation notes: extend scripts\init_db.py seed_only idempotently to create the staff role and its permissions using the existing ensure_perm and if p not in role.permissions patterns. Do not grant staff any of the edit, create, release, obsolete, import, or admin.edit permissions. Add a defensive before_request or per-route checks so a staff user cannot reach mutation endpoints even by direct URL.
- Files: scripts\init_db.py, app\eqms\rbac.py if a helper is useful, app\eqms\admin.py before_request guards, and the module admin.py files where view routes currently require admin.view.

P1.2 Read-only staff dashboard and navigation.
- Problem: the current dashboard and nav expose admin tools and mutation actions.
- Desired behavior: a logged-in staff user sees the same dashboard content areas (whole dashboard, read-only, per Ethan) but with all admin tools and all action buttons hidden, and with the underlying routes enforcing read-only. Hide the Admin Tools card, the account and maintenance and diagnostics and reset-data entry points, and all New, Upload, Edit, Release, Obsolete, Delete, Import, and Move controls in templates when the current user lacks the corresponding permission.
- Implementation notes: use the existing has_perm helper in templates to gate every mutation control. Prefer gating by the specific mutation permission so the same templates serve both admin and staff. Do not build a separate parallel set of templates unless necessary; gate in place. The top bar in _layout.html must not show admin-only destinations to staff.
- Acceptance: logging in as a staff user shows a clean, read-only dashboard; no button that a staff user sees results in a state change; every mutation URL returns 403 for staff.

P1.3 Document Control module: subsystem browsing, Released and Obsolete visibility, and readability.
- Problem: the Document Control module has no categorization, no browse-by-subsystem, and no clean reading view; it also enforces one file per revision, which is fine, but there is no way to group the QM family for a reader.
- Desired behavior:
  - Add a category or library field to Document so controlled QM documents can be grouped by subsystem for browsing (for example QM SOPs and WIs, Controlled Forms, Controlled Templates, or by ISO subsystem). Provide a browse view that lists documents by category with their current revision, status, and effective date, and a filter for Released only versus show Obsolete.
  - The list and detail views must clearly show the current released revision as the active version, list prior revisions as history, and mark Obsolete documents distinctly.
  - Reuse document_viewer so a reader can view docx, xlsx, and pdf in the browser and download the original.
  - Preserve the existing audit actions (doc.release, doc.obsolete, doc.view, doc.view_obsolete, doc.download, doc.download_obsolete). Do not rename them; tests depend on them.
- Implementation notes: add the field via a new model column and Alembic migration with a sensible default so existing rows are valid. Keep changes backwards-compatible. Do not remove the unique doc_number constraint. If the QM family needs multiple controlled files under one logical document (a SOP plus its forms), model that by giving each controlled item its own doc_number (for example QM.SLQ016 and FM1-QM.SLQ016 are separate documents), which matches the register.

P1.4 Support obsolete and prior-revision history for the import.
- Problem: Ethan wants superseded revisions preserved as Obsolete or prior-revision history.
- Desired behavior: the Document Control data model already supports multiple revisions per document and an Obsolete status. Confirm the import (Section 6) can create a released current revision and can represent superseded prior revisions. Where a document is entirely superseded (for example QM.SLQ004 through QM.SLQ010 under DCO095), the document status is Obsolete with an obsolete reason referencing the superseding document. Where only an older revision is superseded by a newer released revision of the same document, keep the newest as Released current and older revisions as history under the same document.

### Priority 2: training read-and-acknowledge feature

P2.1 Training model and assignment.
- Desired behavior: build a minimal training module. Ethan (admin) can create a training assignment that links a specific controlled document or a specific admin_docs file (or a free-text training item) to one or more specific users, with an optional due date. Each assignment produces a per-user item.
- Entities (minimal): TrainingItem (what must be read or done, linked to a Document id or an AdminDocFile id or a title and description), TrainingAssignment (item plus assigned user plus assigned date plus optional due date plus status), TrainingCompletion or an acknowledged_at field on the assignment (who acknowledged, when, and an audit event).
- Implementation notes: new module app\eqms\modules\training\ with models.py, service.py, admin.py; register the blueprint in create_app; add models to the bottom-of-file import block in models.py; ship the Alembic migration. Seed training permissions (training.view for staff to see their own queue and acknowledge; training.manage for admin to assign). Staff can view their own queue and acknowledge their own items only; they cannot assign or see other users' items.

P2.2 My Training staff experience.
- Desired behavior: a staff user sees a My Training page listing items assigned to them with status (assigned, acknowledged, overdue), a link to read or view the linked document via the existing viewer, and an Acknowledge action. Acknowledging records acknowledged_at and the acting user and writes an audit event (for example training.acknowledge). An admin sees an assignment and status view across users.
- Acceptance: admin assigns a document to a user; that user logs in, sees the item under My Training, opens and reads it, clicks Acknowledge; the acknowledgement is recorded with a timestamp and an audit event; the admin sees the item as acknowledged. A staff user cannot acknowledge on behalf of another user and cannot view another user's queue.

### Priority 3: usability across the modules

Ethan asked for usability improvements to several modules. Apply focused, low-risk improvements. For each, keep the change backwards-compatible and covered by a test where practical.

- Navigation and consistency: ensure the dashboard, the top bar, and each module list page use consistent headings, back links, and empty states. A reader should always be able to get back to the dashboard and to the parent library or list.
- Document search and browse: add a simple search or filter to the Document Control browse view (by doc number, title, status) and to the admin_docs library views (filter by filename within a library or folder). Keep it server-side and simple.
- admin_docs library clarity: ensure each of the 11 libraries has a clear title, breadcrumb, and folder navigation, and that view and download work for docx, xlsx, and pdf via the existing viewer. Confirm the move control is gated so staff never see it.
- Equipment calibration and supplier status visibility: if low-risk, surface a simple status column or badge (for example calibration or PM due) on the equipment list, using existing data only; do not add new external integrations. If the data model does not support it cleanly, note it as a follow-up rather than forcing it.
- Error and permission feedback: ensure a staff user hitting a mutation route gets the existing clean 403 page, not a stack trace, and that flash messages are clear.

For any Priority 3 item that turns out to be larger than a small, safe change, implement the safe part, and record the rest as a written follow-up recommendation for Ethan rather than expanding scope.

### Track B delivery and review

- Land Track B as a reviewable change set (one pull request or a clearly described branch) with all tests passing.
- Deploy Track B to production by pushing to the repository so DigitalOcean builds and releases it (Section 7). The release step runs alembic upgrade head and the idempotent seed, which creates the staff and training roles and permissions.
- Provide Ethan a short, plain-language summary of what changed and exactly what to click to verify: log in as admin, create a test staff account at /admin/accounts, assign it the staff role, log in as that staff user in a separate browser, confirm read-only behavior and the My Training flow. Do not proceed to Track A until Ethan approves.

---

## 6. Track A: document staging and production data load (after Track B approval)

Do this only after Ethan approves Track B.

### 6.1 Create the staging folder and manifest

- Create eQMS_Upload_Staging\ at the workspace root. Do not use the migrations\ folder.
- Build a subfolder structure that mirrors the destination organization:
  - Controlled_QM_Documents\ with subfolders SOPs_and_WIs\, Controlled_Forms\, Controlled_Templates\ (these become formally controlled Document Control entries).
  - Records\ with one subfolder per admin_docs library (CAPAs, Audits_and_Management_Reviews, NCRs, Post_Market_Surveillance, Risk_Management, DHF_and_VV, Regulatory_Standards, Employee_Training, Work_Orders, Equipment, Suppliers, Purchasing, DMR, Distribution as applicable).
  - Obsolete_and_Prior_Revisions\ for superseded versions.
- Do not copy the controlled Word or PDF files in a way that alters them. If you stage physical copies, copy bytes unchanged. Prefer a manifest that points at the authoritative source paths rather than duplicating large binaries, unless copying is needed for a clean import run.
- Write eQMS_Upload_Staging\MANIFEST.csv (and a readable MANIFEST.md summary) listing every item to be loaded with these columns: source_path, destination_system (document_control or admin_docs), destination_library_or_category, doc_number (if applicable), title, revision, lifecycle_state (Released, Obsolete, or Prior), effective_date (if known), and notes. No asterisk characters in the manifest text.

### 6.2 Determine correct versions and states

Use QM_DOCUMENT_REGISTER.csv, the DCO094 guide, and the DCO095 guide as the authority. Apply these rules:

- The DCO094 revised documents in QMSInProcess\DCO094\ are the current Released versions for those 19 items (for example QM.SLQ027 Rev F, QM.SLQ040 Rev C, QM.SLQ050 Rev B, FM4-QM.SLQ050 Rev B, FM1-QM.SLQ040 Rev B). The matching older copies in QM Documents\ are prior revisions, loaded as history or Obsolete, not as the active Released version.
- Apply DCO095 as released now:
  - Load the 8 new QM.SLQ052 family documents as Released Rev A (QM.SLQ052, FM1 through FM4-QM.SLQ052, TMP1 through TMP3-QM.SLQ052).
  - Load the 6 revised documents at their new revisions (QM.SLQ027, QM.SLQ020, QM.SLQ012, QM.SLQ013, QM.SLQ025, QM.SLQ029), accounting for whether DCO094 already advanced QM.SLQ027 to Rev F, in which case DCO095 takes it to Rev G.
  - Mark the 20 superseded design documents Obsolete (QM.SLQ004 through QM.SLQ010 and their 13 associated forms and templates), each with an obsolete reason naming the superseding QM.SLQ052 item.
- Forms and templates in the QM family are formally controlled documents (Ethan confirmed). Load them into the Document Control module with their revision letters.
- Everything else (CAPAs, audits, DHF and VV records, risk management, management reviews, equipment, suppliers, purchasing, post-market, NCMR, DMR artifacts, training records, distribution) loads into the appropriate admin_docs library as simple files.
- QMSInProcess handling: DCO packages that are complete become part of the permanent structure. Their released documents load per the register and DCO guides. Active or in-process records (for example active CAPAs, in-process design projects) load into the appropriate records library as working records with a clear note in the manifest; do not represent an in-process item as a formally released controlled document. DC.SLQ001 deliverables load into the DHF records library.
- Flag any item where the correct revision or lifecycle state cannot be determined from the register or the DCO guides. Do not guess a controlled document's revision or state. List every flagged item in the manifest notes and in your summary to Ethan, and pause on those items for his decision.

### 6.3 Build a tested import tool

- Create scripts\import_qms_staging.py (model it on scripts\bulk_import_admin_docs.py). It reads eQMS_Upload_Staging\MANIFEST.csv and:
  - For document_control rows: creates the Document if absent (correct doc_number, title, category), creates the revision, uploads the file to storage, sets change summary and effective date, and sets the lifecycle state (release the current revision; mark Obsolete where the manifest says Obsolete with the given reason). Reuse the document_control service functions and the same audit actions.
  - For admin_docs rows: ensures the target library and folder exist and uploads the file, reusing create_folder and upload_document.
  - Is idempotent and safe to re-run: skip a document_control item if the doc_number and revision already exist; skip an admin_docs file if the same filename already exists in the target folder. Report created, skipped, and failed counts.
  - Supports a dry-run mode that prints exactly what it would do without writing.
- Add tests that run the importer against a temporary SQLite database and local storage using a tiny fixture manifest and fixture files, asserting that document_control entries get the right state and audit events, and that admin_docs files land in the right library and folder. Follow the test fixture style in tests\test_edms_improvements.py.

### 6.4 Load production

- Run the importer in dry-run first and share the dry-run report with Ethan.
- After Ethan confirms the dry-run, run the importer against production (Section 7) so documents land in the production database and the DO Spaces bucket. Do not commit the source documents to git.
- After the load, verify on silqeqms.com that the controlled QM documents appear with correct revisions and states, that Obsolete items are marked Obsolete, that records appear in the right libraries, and that a staff user can read (but not change) them. Provide Ethan a completion report listing counts loaded per destination and any flagged items still awaiting his decision.

---

## 7. Deployment pathway (you perform this)

Standard SILQ eQMS deployment works like this:

Code deployment:
1. Commit your changes on a branch and open a pull request, or commit to the deployment branch that DigitalOcean App Platform watches on the Ethan-Rao/SilqeQMS repository.
2. Pushing to the watched branch triggers DigitalOcean App Platform to build the Dockerfile and run the release phase. The release phase runs scripts\release.py (or scripts\start.py), which executes alembic upgrade head and then the idempotent seed in scripts\init_db.py. This is how new tables, permissions, and roles reach production.
3. Cloudflare fronts silqeqms.com; DNS does not need changes. Health check path is /health.
4. Confirm the deploy succeeded (build logs show migrations complete and seed complete) and smoke-test on silqeqms.com.

Required env vars already set in App Platform: SECRET_KEY, DATABASE_URL (Postgres), ADMIN_EMAIL, ADMIN_PASSWORD, STORAGE_BACKEND=s3, and the S3 Spaces variables (S3_ENDPOINT, S3_REGION, S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY). Do not print or commit these values.

Production data load (Track A):
1. The source documents live on Ethan's local machine and are git-ignored. To load them into production without manual per-file upload, run scripts\import_qms_staging.py on the local machine with the environment pointed at production: DATABASE_URL set to the production Postgres URL and STORAGE_BACKEND=s3 with the production Spaces credentials. Ethan will provide these production values (for example in a local .env that is not committed) so you can run the load. Never commit that .env.
2. Always run dry-run first, share the report, then run for real after Ethan confirms.
3. Because the importer is idempotent, a re-run after a partial failure is safe.

Safety rules for deployment:
- Never force-push. Never change git config. Do not run destructive database operations against production. The RESET DATA admin tool only clears rep, customer, distribution, and ShipStation data; do not use it as part of this work, and never build anything that clears the audit_events table.
- If a migration or import fails in production, stop, report the exact error to Ethan, and propose a fix; do not attempt destructive recovery.

---

## 8. Deliverables checklist

Track B (deliver and get approval first):
- Staff role and read-only permissions seeded idempotently in init_db.py; staff cannot reach any mutation route (403), verified by tests.
- Read-only staff dashboard and navigation with all admin tools and mutation controls hidden and enforced.
- Document Control module enhanced with subsystem or category browsing, Released and Obsolete visibility, prior-revision history, search or filter, and in-browser viewing, without breaking existing audit action strings or the doc_number uniqueness.
- Training module with per-person assignment, a staff My Training queue, read-and-acknowledge with timestamp and audit event, and admin assignment and status views; permissions seeded; tests passing.
- Priority 3 usability improvements that are safe and small, with any larger items written up as follow-up recommendations.
- All new models added to the models.py bottom-of-file import block and shipped with Alembic migrations that apply cleanly on a fresh database and on the existing production schema.
- Full pytest suite passing locally.
- Deployed to production by push; migrations and seed confirmed in the release logs; a plain-language verification guide for Ethan.

Track A (only after Track B approval):
- eQMS_Upload_Staging\ folder and MANIFEST.csv and MANIFEST.md with every item classified, versioned, and stated, and every ambiguous item flagged.
- scripts\import_qms_staging.py, idempotent, dry-run capable, with tests.
- Dry-run report shared with Ethan; production load performed after confirmation; post-load verification and completion report with per-destination counts and outstanding flagged items.

---

## 9. Things to flag back to Ethan rather than deciding yourself

- Any controlled document whose current revision or lifecycle state cannot be determined from QM_DOCUMENT_REGISTER.csv, the DCO094 guide, or the DCO095 guide.
- Whether DCO094 advanced QM.SLQ027 to Rev F before DCO095, which determines whether DCO095 takes it to Rev F or Rev G.
- Any admin_docs record that is genuinely in-process (for example an active CAPA) where it is unclear whether Ethan wants it loaded now or held until closure.
- Any Priority 3 usability change that would require a larger refactor or a new external integration.
- Anything that would require touching the content of a controlled Word or PDF document, which is out of scope for you.

End of prompt.
