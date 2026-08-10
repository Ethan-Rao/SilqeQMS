# Phase 3 Dev Agent Prompt 2
# Corrections to Priority 1, plus a module-by-module review and enhancement mandate

Prepared by: Phase 3 Coordinator agent
For use by: Development agent
Workspace root: C:\Users\Ethan\OneDrive\Desktop\SilqQMS
Production site: silqeqms.com (DigitalOcean App Platform, Cloudflare, DO Spaces)
Repository: Ethan-Rao/SilqeQMS

Writing convention: do not use asterisk characters in any document text or paste block intended for Ethan.

---

## 0. Context and where we are

Priority 1 is largely good, but the staff access model is wrong in two ways and must be corrected before anything else. Ethan has also expanded the mandate: he wants a full, module-by-module review and enhancement pass so the eQMS becomes a fully functioning, intuitive, and useful QMS. You are explicitly not bound by the current state of the code. Refactor where it improves clarity, alignment with the QMS documents, and usability, as long as you do not break existing behavior for the admin user and you keep every change tested and deployed in reviewable increments.

Ethan reviews the live site. He is not a programmer. You perform all coding, testing, and deployment. Deliver in small increments and pause for his review at each checkpoint described in Section 5.

---

## 1. Corrected staff access model (do this first)

Ethan clarified the team model. SILQ is a small team. All employees should have full read access to everything in the QMS. Their only restriction is that they are read-only. The commercial and external-relationship areas (Distribution Log, Sales Dashboard, Customers, Suppliers, NRE Projects) are in fact the staff's primary interest, because Ethan owns the quality side and the staff focus on commercialization and external relationships. Staff must not be able to reach admin-only system tasks.

Two concrete defects to fix, confirmed on the live site:

1. Staff cannot see the External Relationships column or most of the Silq Operations column. The staff role was granted only admin.view, staff.view, and docs.view, so cards gated by module-specific view permissions (distribution_log.view, customers.view, sales_dashboard.view, suppliers.view, sales_orders.view, manufacturing.view, equipment.view, supplies.view, purchasing.view) are hidden.
2. The Admin Tools card is still displayed to staff, because it is gated by has_perm("admin.view") and staff were granted admin.view. The card links to admin diagnostics, an admin-only tool.

### 1.1 Required end state for the staff role

The staff role (read-only) must be able to view and read and download every module, and must not be able to change anything or reach admin-only tools. Precise matrix:

Staff CAN (read-only) view, open, view files, and download or export where those actions do not change state, across all of:
- Quality Management: QM Documents, Management Reviews and Audits, Post Market Surveillance, Risk Management, Design History Files, Regulatory Standards.
- Silq Operations: Manufacturing, Equipment, Supplies, Purchasing, NCRs, Employee Training.
- External Relationships: Distribution Log, Sales Dashboard, Customers, Suppliers, NRE Projects.
- QMS System: Document Control (view controlled documents and revisions), CAPAs, Forms Templates and Travelers, My Account (view and edit their own profile only).
- Their own training queue (once the training feature exists).

Staff CANNOT (must return the clean 403 page and must not see the control in the UI):
- Any create, edit, delete, upload, import, move, release, obsolete, generate, run-sync, disposition, notes, merge, or reset action in any module.
- Admin Tools and everything behind it: system diagnostics, storage diagnostics, debug permissions, the audit trail admin pages and export, account management, data maintenance, reset data, LotLog and Disposition Log uploads, and the auditor access log.

Notes:
- Read-only means view plus download or CSV export of what they can already see. It excludes anything that writes to the database or storage. For example, staff may view a tracing report and download its CSV, but may not generate a new tracing report. Staff may view the Sales Dashboard and export it, but may not upload a LotLog. Staff may view a distribution entry but not edit or import.
- My Account is self-service: a staff user may view and update their own profile fields. That is not an admin task.

### 1.2 Fix the permission architecture (root cause)

The current conflation of admin.view as both see the admin shell and gate admin-only tools is the root defect. Separate these cleanly. Recommended approach (choose the cleanest implementation, but achieve this end state):

- Treat admin.view as access the admin shell and read shared QMS content. Grant it to both admin and staff.
- Introduce or reuse a distinct capability for admin-only system tools. The simplest is to gate all admin-only tool routes and cards on admin.edit, which staff never receive. Account management, maintenance, reset, and uploads already require admin.edit; extend the same gate to the Admin Tools dashboard card, system diagnostics, storage diagnostics, debug permissions, and the audit trail admin pages and export, and the auditor access log. If you prefer an explicit permission such as admin.tools or system.admin, that is acceptable; seed it, grant it only to admin, and gate the same surfaces on it.
- Grant the staff role every module view permission so the dashboard cards, which are gated by the specific view permissions, appear for staff: docs.view, distribution_log.view, distribution_log.export, tracing_reports.view, tracing_reports.download, approvals.view, approvals.download, customers.view, sales_dashboard.view, sales_dashboard.export, sales_orders.view, shipstation.view, equipment.view, suppliers.view, manufacturing.view, supplies.view, purchasing.view, plus admin.view and staff.view. Do not grant any create, edit, delete, upload, import, generate, run, disposition, notes, merge, or admin.edit permission to staff.
- Update the dashboard template so that cards are gated on the specific view permission for that module (which staff now hold), and the Admin Tools card is gated on the admin-only capability (admin.edit or the new tools permission), not on admin.view. Verify that a staff user sees a full dashboard with all four columns populated and no Admin Tools card.

### 1.3 Enforcement and verification

- Enforce read-only at the route level, not only by hiding buttons. Every mutation route in every module must require the appropriate write permission via require_permission, so a staff user hitting the URL directly gets 403. Add or confirm the defense-in-depth guard so staff cannot POST to admin-only blueprints.
- Update the existing staff read-only tests so the seeded staff role in the test matches the real seeded staff role (same permission set), and add assertions that: the staff dashboard shows Distribution Log, Sales Dashboard, Customers, Suppliers, NRE, Manufacturing, Equipment, Supplies, and Purchasing cards; the Admin Tools card is absent; direct GET of /admin/diagnostics, /admin/accounts, /admin/audit, and /admin/reset-data returns 403 for staff; and representative mutation POSTs in the commercial modules (for example creating a customer, generating a tracing report, importing distributions) return 403 for staff.
- Keep the readonly role unchanged (admin.view plus docs.view); it is used by the software validation test cases. Introduce all changes on the staff role.

Deliver Section 1 as the first increment, deploy it, and have Ethan confirm the staff dashboard looks correct on silqeqms.com before moving on.

---

## 2. Module-by-module review and enhancement mandate

After the staff model is corrected and approved, review and enhance each module below. For each module:

1. Read the governing QMS document or documents in docs\QMS-Readable-Texts\ so the module reflects how SILQ actually works. Alignment with the released procedures is a primary goal.
2. Assess the module against three lenses: alignment with the QMS documents, expected user needs and desires (Ethan for quality, staff for commercialization and external relationships), and ease of the FileHold-to-eQMS transition.
3. Propose concrete enhancements in a short written plan for that module, then implement the approved ones. Keep each module change tested, backwards-compatible for the admin experience, and read-only-safe for staff.
4. Flag anything that would change controlled document content or require a decision from Ethan rather than deciding yourself.

Governing documents to consult per module (read the current released revision; use DCO094 and DCO095 guidance for the latest revisions):
- Document Control: QM.SLQ001 Document Control SOP, QM.SLQ014 Electronic Doc System WI, QM.SLQ002 Good Documentation Practices.
- Employee Training: QM.SLQ003 Employee Training SOP.
- CAPA: QM.SLQ016 CAPA SOP.
- NCR and NCMR: QM.SLQ040 Nonconforming Materials SOP.
- Equipment and calibration: QM.SLQ050 Calibration and Preventive Maintenance SOP.
- Suppliers: QM.SLQ015 Supplier QA SOP.
- Purchasing: QM.SLQ020 Purchasing Controls SOP.
- Manufacturing and lots: QM.SLQ043 Work Order SOP, QM.SLQ019 Identification and Traceability SOP, MP-C.SLQ001, DMR documents.
- Receiving and shipping: QM.SLQ039, QM.SLQ045, QM.SLQ046.
- Sales orders and distribution: QM.SLQ036 Sales Order SOP.
- Management review and audits: QM.SLQ018 Management Review SOP, QM.SLQ017 Internal Audits SOP.
- Post-market and complaints: QM.SLQ021 Product Complaint SOP, QM.SLQ033 Post-Market Surveillance SOP, QM.SLQ022 and QM.SLQ023 MDR.
- Risk management: QM.SLQ012 and QM.SLQ013.
- DHF and design control: QM.SLQ052 family (per DCO095).

### 2.1 Document Control (formal controlled documents)

Target state: a clean, intuitive controlled-document experience that a reader can browse by subsystem and that an admin can lifecycle per QM.SLQ001 and QM.SLQ014.
- Confirm the Priority 1 category browsing, status badges, current-revision highlighting, search, and filters are intuitive. Add breadcrumbs and clear empty states.
- Ensure a reader can open and read docx, xlsx, and pdf in the browser and download the original, and that Obsolete documents are clearly marked and separated from active ones.
- Ensure the model and UI cleanly support the Track A import: multiple revisions per document, a released current revision, prior revisions as history, and Obsolete documents with an obsolete reason that names the superseding document.
- Verify the DCO concept is represented sensibly. If Ethan needs to see which DCO drove a revision, consider a change reason or DCO reference field on the revision (backwards-compatible), populated during import from the DCO guides.

### 2.2 Admin Docs libraries (records)

Target state: eleven clear, browsable record libraries with folders, consistent titles, breadcrumbs, per-library filtering by filename, and reliable in-browser view and download. Confirm the move and upload controls are admin-only and hidden from staff. Consider whether any library needs a default folder structure created up front to make the Track A record load land cleanly.

### 2.3 Employee Training

Target state: the read-and-acknowledge training feature from the first prompt, aligned to QM.SLQ003. Admin assigns a specific controlled document or admin_docs file or a free-text training item to specific users, with an optional due date. Each staff user has a My Training queue showing assigned, acknowledged, and overdue items, can open and read the linked item via the viewer, and can acknowledge it, which records who and when and writes an audit event. Admin sees assignment and completion status across users. Seed training.view for staff (own queue only) and training.manage for admin. This becomes the mechanism to record Phase 4 training.

### 2.4 CAPA

Target state: review whether CAPAs should remain simple files in the CAPAs library or gain light structure (a CAPA record with number, title, status, dates, and linked files) aligned to QM.SLQ016. Propose the smallest change that gives Ethan a usable CAPA list and status view. Do not over-build. Flag to Ethan whether he wants structured CAPA tracking now or after go-live.

### 2.5 NCR and NCMR

Target state: review against QM.SLQ040. Decide with Ethan whether NCRs stay as files or gain a minimal record (number, description, disposition, risk assessment flag for use-as-is, linkage to lots). Implement the approved minimal version.

### 2.6 Equipment

Target state: review against QM.SLQ050. Surface calibration and PM status clearly (for example a due or overdue badge and next-due date) using existing data. If the data model lacks calibration or PM due dates, propose adding them and an import from the Equipment Master List. Make the equipment list a genuinely useful at-a-glance calibration status view for the team.

### 2.7 Suppliers

Target state: review against QM.SLQ015. Ensure the Approved Supplier List is browsable and reflects supplier status, scope, and category. Surface supplier documents (assessments, agreements) cleanly. Consider approval status and re-evaluation date visibility.

### 2.8 Purchasing

Target state: review against QM.SLQ020. Ensure purchase orders are browsable and legible, with the supplier-change notification and Pathway C trigger context reflected where relevant. Keep staff read-only.

### 2.9 Manufacturing, lots, and traceability

Target state: review against QM.SLQ043 and QM.SLQ019. Ensure lot and work order records are legible and traceable. Confirm the existing LotLog and disposition data flows remain intact and admin-only, and that staff can view lot and manufacturing records read-only.

### 2.10 Rep Traceability, Sales Dashboard, Customers, Sales Orders, ShipStation, NRE Projects

Target state: these commercial and external modules are the staff's primary interest, so make them clean, legible, and fully readable by staff. Review each for usability: clear lists, filters, detail pages, and exports. Confirm ShipStation sync, sales order import, and LotLog and Disposition uploads remain admin-only and continue to work exactly as they do today for Ethan. Do not alter the ShipStation matching logic or the sales-order-first import ordering. Make sure staff read-only does not break any admin data flow.

### 2.11 Management Reviews and Audits, Post-Market and Complaints, Risk Management, DHF

Target state: as record libraries, ensure they are browsable, well-organized, and viewable. Where a light structured record would clearly help (for example a management review record or a complaint record aligned to QM.SLQ021 and QM.SLQ018), propose it to Ethan before building. Default to keeping these as files unless Ethan asks for structure.

### 2.12 Auditor Portal

Target state: leave the temporary auditor portal functioning and isolated. Confirm the staff role does not gain auditor_portal.access or auditor_portal.admin, and that the corrected admin-tools gating does not expose the auditor access log to staff. Do not expand the auditor portal.

### 2.13 Admin, Accounts, Audit, Diagnostics

Target state: these remain admin-only. Confirm all are behind the admin-only capability after the Section 1 re-gating. Improve the account management UX if helpful (for example clearly labeling the Staff read-only role when Ethan assigns it). Ensure the audit trail continues to capture staff read actions and acknowledgements.

---

## 3. Cross-cutting quality goals

- Alignment with QMS documents: every module should reflect the released procedures. When a module and its SOP disagree, flag it to Ethan rather than silently choosing.
- Intuitive navigation: consistent headers, breadcrumbs, back links, empty states, and clear labels across all modules. A first-time staff user should be able to find and read what they need without instruction.
- Read-only safety: staff never see or reach a state-changing control anywhere. Cover this with tests as you touch each module.
- No regressions for the admin: Ethan's current workflows (Distribution, LotLog, ShipStation sync, Sales Dashboard, document viewing) keep working identically.
- Tests and migrations: every new model ships with an Alembic migration and is added to the bottom-of-file import block in app\eqms\models.py. Migrations apply cleanly on a fresh database and on the existing production schema.

---

## 4. Known issue to address

The test suite currently reports failures because suppliers.custom_fields uses Postgres JSONB, which SQLite cannot compile, so the full-app create_all path fails in some tests. The dev agent confirmed these are pre-existing and fail identically on baseline. Address this so the suite is trustworthy: either make the affected tests cherry-pick only the tables they need (the pattern already used in tests\test_edms_improvements.py), or make the JSONB column degrade to a portable JSON type on SQLite. Do not change production behavior on Postgres. A clean, fully green suite is important because it is the safety net for the module work.

---

## 5. Process, sequencing, and deployment

Operating rhythm (updated per Ethan): do not wait for Ethan's approval to deploy. Ethan cannot give useful feedback until a change is live, and his manual review is a last resort that delays progress. For each checkpoint: implement, test, then deploy. The Phase 3 coordinator reviews your written output and code between checkpoints and will flag any errors; if no errors are flagged, assume the checkpoint is accepted and proceed to the next one. Ethan reviews the live site only occasionally, when he chooses. Keep moving through checkpoints without pausing for sign-off.

Checkpoint 1 status: reviewed by the coordinator, no errors found, approved. Deploy it now (commit and push), then proceed.

Recommended order (adjusted to bring the records-and-data alignment forward, per Ethan):

1. Checkpoint 1 (done, approved): Section 1 staff access corrections. Deploy now.
2. Checkpoint 2: Section 4 test-suite fix (portable JSON or cherry-picked table fixtures) so the whole suite is green and trustworthy. Deploy.
3. Checkpoint 3: Records-and-data alignment for Suppliers, Equipment, and Purchasing (Sections 2.6, 2.7, 2.8), described in Section 5.1 below. This is a near-term priority for Ethan. Deploy.
4. Checkpoint 4: Training read-and-acknowledge feature (Section 2.3). Deploy.
5. Checkpoints 5 and beyond: the remaining module review and enhancement, grouped sensibly (Document Control and Admin Docs together; then the commercial and external modules; then the remaining record libraries). For each group, post a short written enhancement plan, implement, test, and deploy; the coordinator reviews between groups.

### 5.1 Records-and-data alignment (Checkpoint 3 detail)

Ethan wants the system's data model and displayed information to match the records SILQ actually keeps, and wants users to easily find the information they want. For Suppliers, Equipment, and Purchasing specifically:

- Examine the real existing records on disk to learn what information SILQ actually maintains: Suppliers\ (individual supplier folders, SILQ Approved Supplier List), Equipment\ (ST-001 through ST-017 folders, Silq Equipment Master List.xlsx), and Purchasing\ (POs, SILQ PO Log.xlsx). Also read the master list forms in the register (FM1-QM.SLQ050 Equipment Master List, FM6-QM.SLQ015 Approved Supplier List, FM1-QM.SLQ020 Purchase Order Form).
- Compare the fields and organization in those records against what the eQMS modules currently model and display. Identify gaps (fields SILQ tracks that the system does not show, or vice versa) and misalignments.
- Align each module so the fields and views reflect the information Ethan intends to provide, and so a user can quickly find what they want (clear lists, sensible columns, filters or search, and legible detail pages with associated documents). For Equipment, surface calibration and PM due status per QM.SLQ050. For Suppliers, reflect approval status, scope, category, and re-evaluation timing per QM.SLQ015. For Purchasing, make POs legible and searchable per QM.SLQ020.
- Where aligning would require importing the master-list data (for example equipment calibration dates from the Equipment Master List), propose and build a safe import path, but do not load production document archives (that is Track A, still gated). Keep all of this read-only for staff and admin-editable only.
- Post a short written findings-and-plan note for each of the three modules before implementing, so the coordinator can confirm direction; then implement, test, and deploy.

Deployment pathway (you perform it, without waiting for Ethan):
- Code deploys by committing and pushing to the branch DigitalOcean App Platform watches on Ethan-Rao/SilqeQMS. The release phase runs alembic upgrade head and the idempotent seed, which creates and updates the staff role and permissions. Cloudflare fronts silqeqms.com; health check is /health.
- Scope each commit to the checkpoint's own files; do not sweep in unrelated changes. Report each deploy with a plain-language summary and the exact click-path to verify on silqeqms.com.
- Never force-push, never change git config, never run destructive database operations against production, and never build anything that clears the audit_events table. The RESET DATA tool is not part of this work.
- Do not perform the Track A production document load in this prompt. That remains gated behind completion of the system improvements, per the first prompt.

---

## 6. What to flag back to Ethan rather than deciding

- Whether CAPAs, NCRs, complaints, and management reviews should gain structured records now or remain files until after go-live.
- Any place where a module conflicts with its governing SOP.
- Any enhancement that would require changing controlled document content, new external integrations, or a larger refactor with regression risk.
- Any ambiguity in controlled document revisions or lifecycle states (defer these to the Track A stage).

End of prompt.
