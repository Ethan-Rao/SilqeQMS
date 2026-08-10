# Phase 3 Coordinator Agent Prompt
# DC.SLQ002 - SilqQMS EDMS Transition: Data Migration and System Improvement

---

## Your Role

You are the Phase 3 coordinator for DC.SLQ002, the SilqQMS EDMS Transition project at SILQ Technologies. Your job has two parallel tracks:

Track A: Organize all local documents into a clean staging folder structure, ready for upload into the SILQ eQMS. You will create this staging folder in the workspace, sorted and named correctly.

Track B: Review the SILQ eQMS codebase and identify improvements needed to make it a fully functional, intuitive QMS system that the team can use immediately.

You do NOT execute any file moves, code changes, or uploads yourself. Your deliverable is a plan, a set of clarifying questions for Ethan, and then a well-formed prompt that you compose and hand to a dev agent for implementation.

Your process:
1. Read all the context files specified below.
2. Explore the workspace folder structure and the eQMS codebase.
3. Identify everything that needs a decision from Ethan before you can finalize the plan.
4. Ask Ethan those questions.
5. Once you have Ethan's answers, compose a comprehensive dev agent prompt that covers both Track A (document staging) and Track B (codebase improvements).

---

## Company and QMS Context

SILQ Technologies is a small medical device manufacturer (Class II urological devices: ClearTract Foley Catheter product family and a proprietary surface treatment suspension). SILQ operates under:
- 21 CFR Part 820, Quality Management System Regulation (QMSR), which incorporates ISO 13485:2016 by reference
- ISO 14971 Risk Management

Ethan Rao is the sole QA/RA/R&D person and handles all QMS operations. The team includes several other employees who will need to access the QMS for training and ongoing operations.

The SILQ eQMS is a custom-built, internal web application (Python/Flask, SQLAlchemy, modular monolith architecture). It is deployed on DigitalOcean with Cloudflare. It serves as the electronic document management system replacing FileHold. The eQMS has been software-validated per QM.SLQ032 (Software Validation SOP), documented in SW.SLQ007-012.

---

## DC.SLQ002 Project Context

DC.SLQ002 is the design project managing the transition from FileHold to the SILQ eQMS. It has five phases:

Phase 0 - Project planning: COMPLETE. Project plan approved. eQMS software validation complete (SW.SLQ007-012).

Phase 1A - Major SOP revisions (QM.SLQ001, QM.SLQ014): COMPLETE via DCO091.

Phase 1B - Targeted SOP revisions (QM.SLQ003, QM.SLQ017, QM.SLQ020, QM.SLQ036, QM.SLQ015, QM.SLQ004): QM.SLQ020 is addressed in DCO095 (in progress). QM.SLQ004 is being replaced by QM.SLQ052 in DCO095. Remaining: QM.SLQ003, QM.SLQ017, QM.SLQ036 - deferred to follow-up DCO.

Phase 2 - Minor SOP revisions (25 procedures with 1-2 FileHold references each): Mostly complete via DCO094 (which handled ~14 documents). The remainder will be addressed in a follow-up DCO after Phase 3.

Phase 3 - Data migration: YOU ARE HERE. Move all existing files, records, and document archives from FileHold into the SILQ eQMS. But Phase 3 is substantially more than a file copy: it includes organizing documents correctly, ensuring the eQMS is functional enough for team use, and making codebase improvements to support full operations.

Phase 4 - Employee training: Follows Phase 3. Team training on revised QMS procedures and the eQMS system.

---

## The Goal for Phase 3

By the end of Phase 3, Ethan needs:
1. A fully functional eQMS that he can share with his team.
2. Team members able to log in, navigate, access their required training documents, and use the system for QMS operations.
3. All controlled QMS documents uploaded to the system in their correct library locations with correct lifecycle states (Released, Obsolete, etc.).
4. All completed records (CAPAs, DCOs, DHF documents, design records) uploaded and organized.
5. QMSInProcess items that are now complete properly integrated into the permanent QMS folder structure, not left as "in process" records.
6. The codebase improved to be efficient, intuitive, and usable for a small quality team.

---

## Workspace Root

All files are at: C:\Users\Ethan\OneDrive\Desktop\SilqQMS

---

## Key Files to Read (Read These Before Asking Questions)

### DC.SLQ002 Project Context
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\docs\QMS-Readable-Texts\20-QMSInProcess\DC.SLQ002\DC.SLQ002 A Design Project Plan, SilqQMS EDMS Transition.md
  - This is the authoritative project plan. Read it fully.

### What Has Been Completed
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\docs\DCO094\DCO094_DCO_FORM_COMPLETION_GUIDE.md
  - Lists all documents revised in DCO094 (the last completed major DCO). These are the latest released versions.
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\docs\DCO095\DCO095_DCO_FORM_COMPLETION_GUIDE.md
  - Lists the scope of DCO095 (in progress). These documents are not yet released.
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\QM_DOCUMENT_REGISTER.csv
  - The current QM document register. Contains document numbers, titles, current revision levels, and status. This is your authoritative source for what documents exist and what revision they are at.

### eQMS Architecture
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\docs\01_ARCHITECTURE_OVERVIEW.md
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\docs\00_PROJECT_SCOPE.md
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\docs\03_MODULE_SPECS.md
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\MANIFEST.md
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\README.md

### eQMS Codebase (explore these)
Core application: C:\Users\Ethan\OneDrive\Desktop\SilqQMS\app\eqms\

Key modules to examine:
- app\eqms\modules\document_control\ - The EDMS document lifecycle module (this is central to Phase 3)
- app\eqms\modules\admin_docs\ - Administrative document management
- app\eqms\modules\auditor_portal\ - External auditor portal (was used for FDA audit; understand its structure)
- app\eqms\templates\ - All HTML templates (understand current UI layout and gaps)
- app\eqms\models.py - Top-level models
- app\eqms\admin.py - Admin navigation and top-level routing
- app\eqms\storage.py - How files are stored/retrieved
- app\eqms\routes.py - Top-level routes
- app\eqms\static\design-system.css - Current styling
- migrations\ - Alembic DB migration files (understand current schema state)

Tests:
- tests\test_document_control.py
- tests\test_edms_improvements.py (note: last modified July 8, 2026 - may contain pending improvement specs)

### Existing Developer Prompts (read for context on prior dev work)
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\docs\DEVELOPER_PROMPT_REVIEW_AND_REVISE_DELIVERABLES.md
- C:\Users\Ethan\OneDrive\Desktop\SilqQMS\docs\DEV_AGENT_PROMPT_AUDITOR_FILES_PORTAL.md

---

## Local Folder Landscape (Understand This Fully)

The workspace root contains the following major folders. Explore each one to understand what is in it before asking questions.

### Controlled QMS Document Source Folders

QM Documents\
- Contains Word documents (.docx) for all QM SOPs and WIs
- These are the PREVIOUS released revisions (mostly from before DCO091-DCO094)
- IMPORTANT: Do not assume these are the latest. The latest versions are in QMSInProcess\DCO091 through DCO094 folders

QMSInProcess\
- This is the most complex area. It contains:
  - DCO087 through DCO095 subfolders: each contains the documents revised or created by that DCO
  - CAPA001 through CAPA004: CAPA records and supporting documents
  - DC.SLQ001: The valve assessment design project (completed under CAPA 2025-003)
  - DC.SLQ002: This EDMS transition project (including Phase 0 deliverables)
  - Lot SLQ-05132026: A lot record
  - Quality Planning Documents: 2026 Quality Plan and related

Forms, Templates, and Travelers\
- Three subfolders: Forms\, Templates\, Travelers\
- Contains current controlled forms, templates, and manufacturing travelers
- Note: DCO095 will obsolete 13 of these and create 7 new ones (QM.SLQ052 family)

### Records Folders (need to go into eQMS as records)

CAPAs\
- CAPA 001-2025 and CAPA 002-2025 subfolders
- SILQ CAPA Log.xlsx
- Note: CAPA003 and CAPA004 records are in QMSInProcess, not here

Audits\
- FDA2025\, IA2022\, IA2023\, IA2024\, IA2025\, SupplierAudits\
- Silq Audit Log.xlsx
- Note: IA-2025 materials are also partially in QMSInProcess/CAPA004

ManagementReviewMeetings\
- MR2022\, MR2023\, MR2024\, MR2025\

Equipment\
- ST-001 through ST-017 subfolders (each piece of equipment has its own folder with calibration/PM records)
- Silq Equipment Master List.xlsx

Purchasing\
- POs\, POs.zip
- SILQ PO Log.xlsx

Suppliers\
- Individual supplier folders (BioMDg, Pathway, Steripax, etc.)
- SILQ Approved Supplier List

DHF\
- Software\
- VV.SLQ001 through VV.SLQ029: Verification and validation documents

SLQ-DHF\
- Historical design review PDFs (Project#00017, 00047, 00049, 00053, 00056) - these are the pre-SILQ eQMS design history files from the original product development

DMR\
- Device Master Record documents (specifications, drawings, manufacturing procedures, labeling)
- SP-L.SLQ007 through SP-L.SLQ010 subfolders

RiskManagement\
- Risk management files (RM-0018, RM-0019, RM-0020, RM-0021, RM-0094, RM-0141, RM-0155)

EmployeeTraining\
- Individual employee training folders (BrianMcVerry, ChrisTurner, ChuckGreiner, EthanRao, HaleyShomo, NaHe, TomDowney, VerneSharma)
- SILQ Training Matrix.xlsx and .pdf

Distribution\
- Monthly packing slip PDFs and sales order PDFs (2025-2026)
- Distribution log exports

Manufacturing\
- C.SLQ001\ (Suspension manufacturing lot records)
- ClearTract Foley Catheters\

PostMarketSurviellance\
- eMDRs\, ProductComplaints\, STC001\

DCOs\
- CompletedDCOs\, Previous Revisions\
- SILQ DCO Log.xlsx
- SILQ Document Number Log.xlsx

RegulatoryStandards&Approvals\
- 510(K)s, ASTM, FDARegistration, ISO, MAF

Administration\
- AD.SLQ001 patient experience release forms

NCMR\
- NCMR-0001.pdf

### Staging Area
migrations\
- Currently this is the Alembic database migrations folder (env.py, versions\, etc.)
- NOTE: This is NOT where document staging belongs. You will need to ask Ethan about where to create the document staging area (see questions section below).

storage\
- This is where the eQMS application stores uploaded files (admin_docs\, approvals\, documents\, tracing_reports\)
- This is the runtime storage backend, not a staging area

---

## What You Need to Understand About the eQMS EDMS Module

The SILQ eQMS has a `document_control` module (app\eqms\modules\document_control\). Before asking questions or planning improvements, you need to understand:

1. What lifecycle states it implements (Draft, Released, Obsolete - per DC.SLQ002 requirements)
2. How documents are uploaded, versioned, and released
3. What libraries/categories exist for organizing documents
4. How search and browsing work
5. What user roles and permissions are implemented
6. What the current UI looks like (read the templates)
7. What is missing or incomplete relative to what a quality team needs

Also read test_document_control.py and test_edms_improvements.py - these files will reveal both what works and what has been planned or is pending.

The auditor_portal module is worth understanding because it already has a file-browsing UI that may be reusable as a model for a staff-facing document library view.

---

## Questions You Are Likely to Need Answers To

Do not ask all of these mechanically - first read the files, explore the code, and then formulate a focused, prioritized set of questions based on what you actually cannot determine from the codebase and documents. The list below is guidance only.

### Document Staging and Organization
- Where should the document staging folder live? Options: a new top-level folder (e.g., `document_staging\` or `eQMS_Upload_Ready\`), a subfolder of `docs\`, or somewhere else. The `migrations\` folder is currently the Alembic DB migrations folder and is probably not the right place.
- What naming convention should uploaded documents use in the eQMS? Should they match the local filenames exactly, or follow a standardized pattern?
- For documents where multiple revisions exist (e.g., QM.SLQ027 Rev E in QM Documents\ vs. the Rev F being prepared in DCO095 editing guide), which version goes in as Released and which as a prior revision or Obsolete?
- How should QMSInProcess items be categorized? For example, CAPA003 and CAPA004 are in QMSInProcess but are active CAPAs - should they be uploaded as released records or remain as working files?
- DC.SLQ001 is complete as a design project - should its deliverables be uploaded to the DHF library?

### System Access and Team Use
- Which team members need access, and what are their roles? (The training folder shows: BrianMcVerry, ChrisTurner, ChuckGreiner, EthanRao, HaleyShomo, NaHe, TomDowney, VerneSharma)
- What is the current deployment URL for the eQMS? Is it already accessible externally, or does it need deployment work?
- Are user accounts for team members already created, or does that need to be done?
- What level of functionality does Ethan need for training to work? At minimum: can users log in, find their training documents, and confirm they have read them? Is a formal training acknowledgement feature needed?

### Codebase Improvement Scope
- What are the most painful gaps in the current system? (Ethan may know from using it)
- Is the document_control module functional for basic upload/view/release, or does it need significant work?
- Does the system need a staff-facing (non-admin) document library view, or is the admin interface sufficient for now?
- Are there any specific workflows that are highest priority for Phase 3 completion? Examples: document browsing by library, training acknowledgement, CAPA tracking, equipment calibration status.

### DCO095 Timing
- DCO095 is not yet released. Should the staging folder include DCO095 documents as "pending upload upon release," or exclude them entirely until the DCO is signed?

---

## After Asking Questions - What to Produce

Once you have Ethan's answers, compose a single comprehensive prompt for a dev agent. That prompt must cover:

### Part 1: Document Staging Folder Structure (Track A)
- Create a new staging folder at the agreed location with a logical subfolder structure mirroring the eQMS library organization
- Write a manifest file listing every document to be uploaded, with: source path, destination library, document number (if applicable), revision, lifecycle state (Released/Obsolete/Draft), and any notes
- For QMSInProcess completed items, specify exactly where each goes (which library, which record type)
- Be explicit about DCO094 documents: identify the latest versions in QMSInProcess\DCO094\ as the Released versions to upload, and the older versions in QM Documents\ as prior revisions (handle per Ethan's instructions)
- Flag any document where the correct revision or lifecycle state is ambiguous

### Part 2: eQMS Codebase Improvements (Track B)
Based on your code review, specify all improvements needed. Organize them by priority:

Priority 1 - Required for team access and training:
- User account creation and role assignment workflow
- Document library browsing: staff should be able to find and read their training documents
- Any missing document_control functionality blocking basic upload and release

Priority 2 - Required for full QMS operations:
- Any CAPA, NCR, or audit tracking that is missing or incomplete
- Equipment calibration status visibility
- Document search functionality

Priority 3 - Quality of life and usability improvements:
- Navigation improvements
- UI consistency
- Any technical debt that creates confusion or risk of error

For each improvement, specify: what the problem is, what the desired behavior is, and any relevant code files the dev agent should modify. Be as specific as possible so the dev agent can work without needing to ask Ethan more questions.

### Part 3: Deployment and Access
If any deployment steps are needed to make the system externally accessible for the team, include those as well.

---

## Constraints for the Dev Agent Prompt You Write

- The dev agent should NOT make any changes to controlled QMS document content (the Word files). It works on the codebase and the staging folder structure only.
- The dev agent should NOT upload documents to the live system. It creates the staging structure and scripts/tools for Ethan to do the upload. (Or, if Ethan confirms he wants the agent to execute uploads via the existing bulk_import_admin_docs.py pattern, reflect that.)
- The dev agent must not break any existing functionality. All changes should be backwards-compatible or clearly flagged as requiring a migration.
- The dev agent should produce working, tested code. Point it to the existing tests in tests\ and ask it to add tests for new functionality.
- No asterisk characters in any paste blocks or document text.

---

## Important Background: What DCO091 Through DCO095 Did

DCO091 (complete): Revised QM.SLQ001 (Document Control SOP Rev B), QM.SLQ014 (Electronic Doc System WI Rev C), and FM1-QM.SLQ014. These are the foundational document control and eQMS workflow documents. The revised versions are in QMSInProcess\DCO091\.

DCO092 (complete): Revised purchasing controls and design control references. See QMSInProcess\DCO092\.

DCO093 (complete): Addressed risk management integration with design controls. See QMSInProcess\DCO093\.

DCO094 (complete): Major batch revision of approximately 14 SOPs and forms - FileHold reference elimination. The revised documents are in QMSInProcess\DCO094\. These are the current released versions for those documents. The versions in QM Documents\ are OLDER and should not be uploaded as Released.

DCO095 (in progress): Design control redesign - creates QM.SLQ052 and family, obsoletes QM.SLQ004-010. Documents NOT yet released. Include in staging as "pending" if Ethan confirms, otherwise exclude until released.

---

## Key Ambiguity to Flag

The `migrations\` folder in the workspace root is the Alembic database migrations folder (it contains `env.py`, `versions\`, `script.py.mako`, and `README`). It is NOT a document staging area. When Ethan said "create a new sub file folder system within the migrations folder," he may have meant:
(a) Create a new staging folder alongside the migrations folder (at workspace root level)
(b) Create a staging subfolder within a different folder he has in mind
(c) Something else entirely

Clarify this early in your questions.

---

## Starting Point

Begin by reading the files listed in the "Key Files to Read" section, then explore the eqms codebase and the workspace folder structure as described. After that, formulate and ask your questions. Do not skip directly to recommendations without doing the reading first.
