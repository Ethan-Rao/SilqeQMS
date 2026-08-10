# Developer Prompt: QMS Transition Plan — FileHold to SilqQMS

**Date:** 2026-03-23  
**Requested by:** Ethan Rao, Director R&D, QA, Regulatory Affairs  
**Purpose:** Create a comprehensive transition plan document covering the migration of Silq's Quality Management System from FileHold (legacy document management) to the SilqQMS eQMS application, including a document-by-document disposition for all 46 QM procedures.

---

## Objective

Produce a single, self-contained markdown document at:

**`docs/transition-plan/Output/QMS_TRANSITION_PLAN_FILEHOLD_TO_SILQQMS.md`**

This document will serve as the master plan for the QMS platform transition. It should be written for the Silq leadership team and quality system users, covering what changes, what stays, what needs revision, and the sequence of execution.

---

## Input Artifacts (read all before starting)

### Primary References

1. **Gap Analysis Report** — `docs/gap-analysis/QMS_GAP_ANALYSIS_ISO13485_QMSR_2026_03.md`  
   Contains the 12-item QMSR action plan, clause-by-clause findings, and specific SOP revision recommendations. This is the authoritative source for what document changes are needed.

2. **QMS Document Inventory** — `docs/gap-analysis/QMS_DOCUMENT_INVENTORY_2026_03.md`  
   Complete inventory of ~986 QMS files across 16 subsystem folders with file counts, document IDs, revision levels, and cross-reference matrix.

3. **General Quality Plan Attachment** — `docs/gap-analysis/QMS_GAP_ANALYSIS_ATTACHMENT_GENERAL_QUALITY_PLAN_2026_03.md`  
   Non-QMSR quality improvement items separated from the main report.

### SilqQMS Application References

4. **Application README** — `README.md`  
   Describes the SilqQMS eQMS application architecture, modules, and capabilities.

5. **Admin Docs Library Definitions** — `app/eqms/modules/admin_docs/admin.py`  
   Defines the 11 document libraries in the target system (read lines 18-30 for the `LIBRARIES` dictionary).

6. **Document Control Model** — `app/eqms/modules/document_control/models.py`  
   The formal document control system: `Document` (doc_number, title, type, status: Draft→Released→Obsolete), `DocumentRevision` (revision letter, change summary, effective date, release tracking), `DocumentFile` (storage, SHA256, content type).

7. **Admin Docs Model** — `app/eqms/modules/admin_docs/models.py`  
   The library/folder/file storage system: `AdminDocFolder` (library_key, parent folder tree, name), `AdminDocFile` (filename, storage_key, content_type, size).

8. **Bulk Import Script** — `scripts/bulk_import_admin_docs.py`  
   Existing script for importing files from a local directory into admin_docs libraries. Already configured for `--library qms_documents --folder "Original - FileHold"`.

### Regulatory Standards (for understanding QMSR revision requirements)

9. **ISO 13485:2016** — `RegulatoryStandards&Approvals/ISO/ISO_13485_2016.pdf`
10. **FDA QMSR Final Rule** — `RegulatoryStandards&Approvals/ISO/2024-01709. FDAQMSRFinalRule.pdf`

---

## What You Need to Know About the Current State

### FileHold (Legacy System)

FileHold is the current document management system. All 46 QM SOPs/WIs were authored and controlled in FileHold as `.docx` files with revision control (Rev A, B, C, etc.). FileHold provides:
- Document storage and retrieval
- Version/revision tracking
- Folder organization
- Electronic signatures (referenced in `QM.SLQ014` Electronic Doc System WI)

The `QM Documents/` folder in the repository contains the full set of 46 QM documents exported from FileHold. Several other QMS record folders also contain FileHold exports (some as "Copied from FileHold..." ZIP archives).

### SilqQMS (Target System)

SilqQMS is a Flask/PostgreSQL web application with two document management subsystems:

**1. Document Control Module** (`document_control`)  
For formal numbered, revision-controlled QMS documents. Supports:
- Document number, title, type, owner
- Status lifecycle: Draft → Released → Obsolete
- Revision tracking with revision letter, change summary, effective date
- File attachments with SHA256 integrity verification
- Release authorization tracking

**2. Admin Docs Libraries** (`admin_docs`)  
For browsable document libraries organized by QMS subsystem. 11 libraries are defined:

| Library Key | Display Name |
|---|---|
| `qms_documents` | Quality Management Documents |
| `employee_training` | Employee Training |
| `management_reviews` | Management Reviews, Audits & Approvals |
| `ncrs` | NCRs |
| `capas` | CAPAs |
| `post_market_surveillance` | Post Market Surveillance |
| `regulatory_standards` | Regulatory Standards & Approvals |
| `work_orders` | Work Orders |
| `risk_management` | Risk Management |
| `dhfs` | Design History Files (DHFs) |
| `forms_templates_travelers` | Forms, Templates & Travelers |

Each library supports nested folder trees and file uploads with metadata.

**3. Entity-Linked Documents**  
Equipment, suppliers, supplies, manufacturing lots, and purchasing modules each have their own document/attachment models for records linked to specific entities.

### Key Constraint: QM.SLQ014 (Electronic Doc System WI)

`QM.SLQ014 Rev B — Electronic Doc System WI` currently describes the FileHold system and electronic signature practices. This document will require a **complete rewrite** to describe SilqQMS. It is the single most impacted document in the transition.

---

## Complete QM Document Register

The transition plan must include a disposition for every one of these 46 documents. Here is the full register with current revision levels:

| # | Document ID | Rev | Title | Type |
|---|---|---|---|---|
| 1 | QM.SLQ001 | A | Document Control SOP | SOP |
| 2 | QM.SLQ002 | B | Good Documentation Practices SOP | SOP |
| 3 | QM.SLQ003 | B | Employee Training SOP | SOP |
| 4 | QM.SLQ004 | A | Design Control Program SOP | SOP |
| 5 | QM.SLQ005 | B | Design Project Planning SOP | SOP |
| 6 | QM.SLQ006 | A | Design Input SOP | SOP |
| 7 | QM.SLQ007 | A | Design Output SOP | SOP |
| 8 | QM.SLQ008 | A | Design Review SOP | SOP |
| 9 | QM.SLQ009 | A | Design VV SOP | SOP |
| 10 | QM.SLQ010 | A | Design Transfer SOP | SOP |
| 11 | QM.SLQ011 | A | Statistical Techniques WI | WI |
| 12 | QM.SLQ012 | B | Risk Management SOP | SOP |
| 13 | QM.SLQ013 | B | Risk Analysis SOP | SOP |
| 14 | QM.SLQ014 | B | Electronic Doc System WI | WI |
| 15 | QM.SLQ015 | B | Supplier QA SOP | SOP |
| 16 | QM.SLQ016 | C | CAPA SOP | SOP |
| 17 | QM.SLQ017 | A | Internal Audits SOP | SOP |
| 18 | QM.SLQ018 | A | Management Review SOP | SOP |
| 19 | QM.SLQ019 | C | Identification and Traceability SOP | SOP |
| 20 | QM.SLQ020 | D | Purchasing Controls SOP | SOP |
| 21 | QM.SLQ021 | D | Product Complaint System SOP | SOP |
| 22 | QM.SLQ022 | A | Medical Device Reporting | SOP |
| 23 | QM.SLQ023 | A | eMDR Submission Work Instruction | WI |
| 24 | QM.SLQ025 | A | Quality Planning SOP | SOP |
| 25 | QM.SLQ026 | C | Part Number Assignment WI | WI |
| 26 | QM.SLQ027 | E | Quality Manual | Manual |
| 27 | QM.SLQ028 | A | Protection of Confidential Patient Information | SOP |
| 28 | QM.SLQ029 | A | DHR Review and Approval SOP | SOP |
| 29 | QM.SLQ030 | A | Advisory Notices and Recalls SOP | SOP |
| 30 | QM.SLQ032 | A | Software Validation SOP | SOP |
| 31 | QM.SLQ033 | A | Post-Market Surveillance SOP | SOP |
| 32 | QM.SLQ034 | F | Organization Chart | Ref Doc |
| 33 | QM.SLQ035 | D | Quality Policy | Ref Doc |
| 34 | QM.SLQ036 | E | Sales Order SOP | SOP |
| 35 | QM.SLQ037 | A | Quality Objectives | Ref Doc |
| 36 | QM.SLQ038 | B | Managing Regulatory Inspections | SOP |
| 37 | QM.SLQ039 | B | Receiving Inspection SOP | SOP |
| 38 | QM.SLQ040 | B | Nonconforming Materials SOP | SOP |
| 39 | QM.SLQ043 | A | Work Order SOP | SOP |
| 40 | QM.SLQ045 | A | Receiving SOP | SOP |
| 41 | QM.SLQ046 | A | Shipping SOP | SOP |
| 42 | QM.SLQ047 | A | Process Validation SOP | SOP |
| 43 | QM.SLQ048 | A | Device Master Record SOP | SOP |
| 44 | QM.SLQ049 | A | Workstation Practices SOP | SOP |
| 45 | QM.SLQ050 | A | Calibration and Preventive Maintenance SOP | SOP |
| 46 | QM.SLQ051 | A | Environmental Monitoring | SOP |

**Missing numbers in sequence:** QM.SLQ024, QM.SLQ031, QM.SLQ041, QM.SLQ042, QM.SLQ044. These are not used and should be noted as available for future procedures.

---

## Forms, Templates, and Travelers

The transition plan should also account for the controlled forms and templates that support the SOPs. There are:

- **44 Forms** (FM-series, e.g., FM1-QM.SLQ001 through FM1-QM.SLQ051)
- **20 Templates** (TMP-series, e.g., TMP1-QM.SLQ001 through TMP3-QM.SLQ013)
- **1 Traveler** (TR-C.SLQ001 Suspension Processing Traveler)

Forms and templates are children of their parent SOP — if a parent SOP is revised, its associated forms/templates should be reviewed for compatibility. The full listing is in the QMS Document Inventory Section 3.6.

---

## Gap Analysis Action Items That Drive Document Revisions

The gap analysis identifies specific documents that need revision. Cross-reference these when building the disposition matrix:

### Documents Requiring QMSR Content Revisions (from Gap Analysis Part 3 + Part 7)

| Document | Gap Analysis Reference | Required Change |
|---|---|---|
| **QM.SLQ027** (Quality Manual) | 3.1, 3.2, Action #6 | Add QMS process interaction/risk map; add ISO-to-QMSR overlay matrix; update all legacy 820 citations |
| **QM.SLQ021** (Product Complaint SOP) | 3.19, Action #1 | Add mandatory `§820.35(a)` seven-element checklist; update forms FM1-QM.SLQ021, TMP1-QM.SLQ021 |
| **QM.SLQ019** (Identification and Traceability SOP) | 3.16, Action #2 | Add explicit parts 830/821 mapping, UDI capture controls per `§820.35(c)` |
| **QM.SLQ001** (Document Control SOP) | 3.4 | Add `§820.35` supplemental record requirements to control language |
| **QM.SLQ014** (Electronic Doc System WI) | 3.4, system transition | **Complete rewrite** — replace FileHold references with SilqQMS system description |
| **QM.SLQ030** (Advisory Notices and Recalls SOP) | 3.11 | Verify/update part 806 cross-references per `§820.10(b)(4)` |
| **QM.SLQ047** (Process Validation SOP) | 3.15 | Add outsourced sterilization control appendix |
| **QM.SLQ017** (Internal Audits SOP) | Action #8 | Add QMSR-focused audit checklist module for `§820.10`, `§820.35`, `§820.45` |
| **QM.SLQ018** (Management Review SOP) | Action #7 | Add QMSR readiness KPI block to MR input/output requirements |
| **QM.SLQ012** (Risk Management SOP) | Action #9 | Add formal complaint/CAPA trigger-to-risk update workflow |
| **QM.SLQ050** (Calibration and PM SOP) | Action #10 | Add calibration-required vs. not-required classification framework |

### Documents Requiring Citation-Only Updates (QMSR Modernization)

All 46 QM documents should be reviewed for legacy "21 CFR 820.xx" citations that need updating to the revised 820 structure + ISO 13485 clause references. Gap Analysis Action #6 calls for a single controlled citation release package.

### Documents That Can Be Maintained As-Is (Pending Citation Review)

Documents not flagged for content changes in the gap analysis — primarily the design control suite (QM.SLQ004–QM.SLQ010), statistical techniques (QM.SLQ011), and several operational SOPs — may only need the citation modernization pass without substantive content revision.

---

## Required Output Document Structure

The transition plan should follow this structure:

### Part 1: Executive Summary
- Purpose and scope of the transition
- Timeline overview (high-level phases)
- Key stakeholders and governance

### Part 2: Current State — FileHold
- What FileHold provides today
- How documents are currently controlled, accessed, and revised
- Known limitations driving the transition
- Reference to `QM.SLQ014` as the current system WI

### Part 3: Target State — SilqQMS
- Overview of the SilqQMS eQMS platform capabilities
- Document Control module (formal revision-controlled documents)
- Admin Docs libraries (browsable document libraries by subsystem)
- Entity-linked documents (equipment, suppliers, manufacturing, etc.)
- Library-to-subsystem mapping table (how the 11 libraries map to the QMS)
- What changes for end users in daily workflow

### Part 4: Document Disposition Matrix
This is the core of the plan. A table covering every QM document with these columns:

| Column | Description |
|---|---|
| Document ID | QM.SLQ### |
| Rev (Current) | Current FileHold revision |
| Title | Document title |
| Disposition | One of: **Maintain** (no content change), **Revise** (content update needed), **Rewrite** (substantial new content), **Retire** (obsolete/supersede) |
| Revision Scope | Brief description of what changes, if any |
| QMSR Citation Update | Yes/No — does the document contain legacy 820 citations? |
| Target Rev | Next revision letter after transition |
| Priority | Critical / High / Medium / Low |
| Associated Forms/Templates | FM/TMP IDs that need review if parent changes |
| Gap Analysis Cross-Reference | Which gap analysis section/action item drives this |

Every one of the 46 QM documents must appear in this table.

### Part 5: Forms, Templates, and Travelers Disposition
- Summary table of all 65 forms/templates/travelers
- Which are impacted by parent SOP revisions
- Which need independent updates (e.g., complaint form for `§820.35(a)`)
- Which can be maintained

### Part 6: Migration Approach
- **Phase 1: Preserve** — Bulk import all current FileHold originals into SilqQMS `qms_documents` library under "Original - FileHold" folder (using existing `bulk_import_admin_docs.py` script)
- **Phase 2: Revise** — Execute document revisions per the disposition matrix, creating new revisions in the Document Control module
- **Phase 3: Release** — Formal release of revised documents through SilqQMS with electronic approval
- **Phase 4: Train** — Training on revised SOPs and new system
- **Phase 5: Cutover** — Decommission FileHold access; SilqQMS becomes system of record
- Technical migration steps for each phase
- Data integrity verification approach

### Part 7: QMSR Revision Execution Plan
- Grouped by priority wave (Critical → High → Medium)
- Revision sequence dependencies (e.g., QM.SLQ027 Quality Manual should be revised early since other SOPs reference it)
- Citation modernization approach (single controlled release vs. rolling updates)
- Relationship to Gap Analysis Part 7 action items

### Part 8: Training Plan
- System training (SilqQMS platform for all users)
- Content training (revised SOPs per QMSR changes)
- Training record requirements
- `QM.SLQ003` (Employee Training SOP) implications

### Part 9: Validation and Verification
- How to verify document integrity after migration (SHA256 checks, file counts)
- How to verify document control functionality in SilqQMS
- User acceptance testing approach
- `QM.SLQ032` (Software Validation SOP) applicability to SilqQMS

### Part 10: Timeline and Milestones
- Phase-by-phase timeline with target dates
- Align with Gap Analysis Part 7 target dates (earliest: 2026-04-15, latest: 2026-10-15)
- Decision gates between phases
- Risk factors and contingencies

### Part 11: Document Numbering Gaps and Future Procedures
- Note QM.SLQ024, 031, 041, 042, 044 as available
- Recommend any new procedures needed based on gap analysis findings (e.g., outsourced sterilization appendix could be a standalone procedure)

---

## Important Instructions

1. **Read the gap analysis report and document inventory completely before writing.** Every document disposition must be traceable to specific gap analysis findings or a "no change needed" rationale.

2. **Be specific in the disposition matrix.** Don't say "review needed" — say exactly what changes: "Add `§820.35(a)` seven-element checklist to complaint investigation section; update regulatory reference from 820.198 to §820.35(a)."

3. **Group citation-only changes separately from content changes.** Many documents may only need their regulatory reference sections updated without touching the procedural content. This distinction matters for change control efficiency — citation-only updates can potentially be batched in one Document Change Order.

4. **Account for form/template cascade effects.** When a parent SOP is revised, list which child forms/templates must be reviewed. For example, revising QM.SLQ021 (Complaint SOP) means FM1-QM.SLQ021 (Product Complaint File form) and TMP1-QM.SLQ021 (Complaint Response Letter template) must also be reviewed.

5. **Maintain a consultative, leadership-appropriate tone.** This is a planning document for executive review, not a technical implementation spec.

6. **Do not fabricate document content.** You cannot read the `.docx` files directly. Base all revision scope determinations on the gap analysis findings, the document inventory cross-reference matrix, and the document titles. If a disposition is uncertain, note it as "Review required — confirm legacy 820 citation presence."

7. **Reference the existing bulk import script** (`scripts/bulk_import_admin_docs.py`) when describing the initial migration step. It already exists and is configured for the task.

8. **Note CAPAs 2025-002 and 2025-003 as pending** — their upload is expected and should be included in the migration timeline.

9. **The only file you should create is** `docs/transition-plan/Output/QMS_TRANSITION_PLAN_FILEHOLD_TO_SILQQMS.md`.

---

## Constraints

- Target document length: 30-50 pages (comprehensive but readable)
- Format: Markdown with tables
- All document IDs must use exact format: `QM.SLQ###`
- All form IDs must use exact format: `FM#-QM.SLQ###`
- All template IDs must use exact format: `TMP#-QM.SLQ###`
- Priority levels must align with gap analysis terminology: Critical / High / Medium / Low
- Timeline dates must be realistic and align with gap analysis Part 7 dates where applicable
