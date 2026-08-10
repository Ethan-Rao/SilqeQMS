# QMS Transition Plan: FileHold to SilqQMS

**Date:** 2026-03-24  
**Audience:** Silq leadership team (CEO, VP QA, VP RA, Director of Manufacturing, Quality Specialist)  
**Purpose:** Define what needs to change in QMS procedures to transition from FileHold to SilqQMS.

---

## 1. Introduction

This document is the platform-transition plan for moving Silq's quality document operations from FileHold to SilqQMS. It is written for leadership decision-making and is intended to show scope, impact, and sequence of required procedure updates.

The transition is needed because many current QM procedures explicitly describe FileHold-specific workflows (for example: FileHold login, check-in/check-out, routing folders, and records filing language). SilqQMS is now the intended system and has different user flow and organizational structure. To avoid procedural mismatch, every FileHold reference must be evaluated and updated.

**How to use this document:**
- **Sections 2-3** provide context: what we have today and where we're going.
- **Section 4** is the core — a document-by-document breakdown of what needs to change, grouped by effort level.
- **Sections 5-6** cover associated artifacts and recommended sequencing.
- **Section 7** clarifies what is explicitly out of scope.

All document counts and FileHold reference data in this plan are based on a systematic text analysis of every QM procedure's actual content.

---

## 2. Current State: How Our QMS Works Today

### QMS document landscape

The current QM set contains 46 procedures/work instructions. Based on extracted document text analysis:
- 33 of 46 documents reference FileHold
- 13 of 46 documents do not reference FileHold

FileHold references appear at four practical levels:
- Deep procedural dependency (entire workflow built around FileHold)
- Multi-step procedural references
- Light boilerplate references (glossary + records filing line)
- No dependency

### How FileHold is used in daily quality operations

From reviewed source procedures, FileHold is used as:
- The named system for controlled document access and workflow execution
- The storage location for records and archives
- The location for logs (DCO log, purchase order log, audit schedule/status, etc.)
- The user-facing workflow mechanism for routing, approvals, and sign-offs

Examples from reviewed documents:
- `QM.SLQ014` is a FileHold operating instruction (login, routing folders, check-in/check-out, approvals, training workflows).
- `QM.SLQ001` repeatedly directs users and administrators to FileHold folders and operations for release, prior revision handling, external documents, and retention.
- `QM.SLQ003`, `QM.SLQ017`, and `QM.SLQ020` require records to be scanned/imported/filed in FileHold.

### What is driving the change

Our existing procedures are well-structured, operationally detailed, and reflect years of established practice. The issue is not the quality of our procedures — it is that they are tightly coupled to a specific platform name and its specific UI mechanics. As SilqQMS replaces FileHold as our working system, retaining FileHold-specific instructions creates a mismatch between what the procedures say and how work is actually done. This transition is about bringing our documented procedures into alignment with our operating reality.

---

## 3. Target State: How Things Will Work in SilqQMS

### What SilqQMS provides (plain language)

SilqQMS provides a centralized environment for:
- Controlled quality documentation
- Organized document libraries by QMS subsystem
- Searchable and retrievable records
- Association of records to specific quality entities (for example equipment, suppliers, lots)

In practical terms, users transition from a FileHold-centric operating model to a SilqQMS-centric one for storing, retrieving, and controlling QMS documents and records.

### Document library organization

SilqQMS has 11 admin document libraries:
- Quality Management Documents
- Employee Training
- Management Reviews, Audits & Approvals
- NCRs
- CAPAs
- Post Market Surveillance
- Regulatory Standards & Approvals
- Work Orders
- Risk Management
- Design History Files (DHFs)
- Forms, Templates & Travelers

### What changes for users in daily work

Day-to-day quality work — creating records, routing documents, retrieving evidence — stays fundamentally the same. What changes is the procedure language that describes *how* to do it. Instructions that currently say "log in to FileHold," "check in/check out in FileHold," or "file in the FileHold drawer" will be updated to reflect SilqQMS workflows instead.

This is not a change to what we do. It is a change to how our procedures describe the system we use to do it.

---

## 4. Document-by-Document Disposition

This section is the core execution register for all 46 QM documents.

## Group 1: Complete Rewrite

These procedures are deeply embedded in FileHold operations and cannot be handled by simple text replacement.

### QM.SLQ014 Rev B - Electronic Doc System WI

- **Why rewrite is required:** The document is effectively a FileHold user/administrator manual, with 80 FileHold references and extensive UI/workflow steps tied to FileHold behavior.
- **What it currently describes:** Account setup, login, folder navigation, local copy operations, DCO routing and approval steps, release actions, training workflow operations, and signature handling in FileHold.
- **Key sections needing attention:** Access, DCO initiation/routing, review/approval flow, release flow, training workflows, retrieval instructions, and all FileHold-specific terminology.
- **Associated artifacts to review with parent:** `FM1-QM.SLQ014` (Electronic Signature Acknowledgement), plus alignment check with referenced templates/forms from document control usage.

### QM.SLQ001 Rev A - Document Control SOP

- **Why rewrite is required:** FileHold is woven through core document control operations (76 references), including release, archiving, access, external documents, and retention controls.
- **What it currently describes:** DCO handling, release mechanics, current/prior revision handling, external document placement, storage/retention language, and records/log maintenance in FileHold.
- **Key sections needing attention:** Definitions, creating/releasing/changing documents, document access, external document controls, storage and retention language, and all FileHold location/process references.
- **Associated artifacts to review with parent:** `FM1-QM.SLQ001`, `FM2-QM.SLQ001`, `TMP1-QM.SLQ001`.

---

## Group 2: Targeted Revision

These have multiple FileHold references embedded in process steps. They require line-by-line procedure review, not bulk replacement.

| Document | Rev | FileHold Refs | Why targeted revision is needed | Associated forms/templates to review |
|---|---|---:|---|---|
| QM.SLQ003 Employee Training SOP | B | 14 | Training coordinator steps, record import language, retrieval language, and matrix archival steps explicitly name FileHold workflow/storage operations. | `FM1-QM.SLQ003`, `FM2-QM.SLQ003` |
| QM.SLQ017 Internal Audits SOP | A | 6 | Auditor qualification filing, schedule/report archival, and audit record filing instructions include FileHold-specific storage language. | `FM1-QM.SLQ017`, `FM2-QM.SLQ017`, `FM3-QM.SLQ017`, `FM4-QM.SLQ017`, `FM5-QM.SLQ017` |
| QM.SLQ020 Purchasing Controls SOP | D | 6 | Purchase order completion, closure, and log-update instructions include FileHold check-in/check-out language. | `FM1-QM.SLQ020` |
| QM.SLQ036 Sales Order SOP | E | 5 | Sales order log filing and record retention language references FileHold directly in operational steps. | `FM1-QM.SLQ036` |
| QM.SLQ015 Supplier QA SOP | B | 4 | Supplier assessment storage, self-assessment filing, and record retention language includes FileHold instructions. | `FM1-QM.SLQ015`, `FM2-QM.SLQ015`, `FM3-QM.SLQ015`, `FM4-QM.SLQ015`, `FM5-QM.SLQ015`, `FM6-QM.SLQ015`, `FM7-QM.SLQ015`, `FM8-QM.SLQ015` |
| QM.SLQ004 Design Control Program SOP | A | 3 | DHF archival and design-scope record filing language references FileHold-based storage operations. | `FM1-QM.SLQ004` |

Practical note for Group 2: each parent SOP revision package should include its associated forms/templates for compatibility review so parent and child artifacts remain aligned after system-language changes.

---

## Group 3: Simple Text Update

These documents have 1-2 FileHold references and follow a light boilerplate pattern (typically glossary definition and/or records-filing sentence). They are suitable for batched controlled updates.

| Document | Rev | Title | FileHold Refs |
|---|---|---|---:|
| QM.SLQ005 | B | Design Project Planning SOP | 2 |
| QM.SLQ006 | A | Design Input SOP | 2 |
| QM.SLQ007 | A | Design Output SOP | 2 |
| QM.SLQ008 | A | Design Review SOP | 2 |
| QM.SLQ009 | A | Design VV SOP | 2 |
| QM.SLQ010 | A | Design Transfer SOP | 2 |
| QM.SLQ012 | B | Risk Management SOP | 2 |
| QM.SLQ013 | B | Risk Analysis SOP | 2 |
| QM.SLQ016 | C | CAPA SOP | 2 |
| QM.SLQ018 | A | Management Review SOP | 2 |
| QM.SLQ021 | D | Product Complaint System SOP | 2 |
| QM.SLQ023 | A | eMDR Submission Work Instruction | 2 |
| QM.SLQ028 | A | Protection of Confidential Patient Info | 2 |
| QM.SLQ029 | A | DHR Review and Approval SOP | 2 |
| QM.SLQ030 | A | Advisory Notices and Recalls SOP | 2 |
| QM.SLQ038 | B | Managing Regulatory Inspections | 2 |
| QM.SLQ043 | A | Work Order SOP | 2 |
| QM.SLQ046 | A | Shipping SOP | 2 |
| QM.SLQ048 | A | Device Master Record SOP | 2 |
| QM.SLQ051 | A | Environmental Monitoring | 2 |
| QM.SLQ027 | E | Quality Manual | 1 |
| QM.SLQ039 | B | Receiving Inspection SOP | 1 |
| QM.SLQ045 | A | Receiving SOP | 1 |
| QM.SLQ049 | A | Workstation Practices SOP | 1 |
| QM.SLQ050 | A | Calibration and Preventive Maintenance SOP | 1 |

Suggested batch pattern for Group 3 execution:
- Update FileHold glossary definition language
- Update records filing sentence(s)
- Confirm no leftover FileHold wording in section headers/footers
- Release as controlled grouped package(s) in manageable review size

---

## Group 4: No FileHold Changes Needed

These 13 documents contain zero FileHold references and require no edits for the platform transition.

| Document | Rev | Title |
|---|---|---|
| QM.SLQ002 | B | Good Documentation Practices SOP |
| QM.SLQ011 | A | Statistical Techniques WI |
| QM.SLQ019 | C | Identification and Traceability SOP |
| QM.SLQ022 | A | Medical Device Reporting |
| QM.SLQ025 | A | Quality Planning SOP |
| QM.SLQ026 | C | Part Number Assignment WI |
| QM.SLQ032 | A | Software Validation SOP |
| QM.SLQ033 | A | Post-Market Surveillance SOP |
| QM.SLQ034 | F | Organization Chart |
| QM.SLQ035 | D | Quality Policy |
| QM.SLQ037 | A | Quality Objectives |
| QM.SLQ040 | B | Nonconforming Materials SOP |
| QM.SLQ047 | A | Process Validation SOP |

---

## 5. Forms, Templates, and Travelers Impact

When a parent SOP is revised for this platform transition, associated controlled artifacts should be reviewed with it to keep language and handling instructions consistent.

Key known impacts from required review set:
- `QM.SLQ001` has 3 associated controlled artifacts:
  - `FM1-QM.SLQ001`
  - `FM2-QM.SLQ001`
  - `TMP1-QM.SLQ001`
- `QM.SLQ014` has 1 associated form:
  - `FM1-QM.SLQ014` (Electronic Signature Acknowledgement)
- Group 2 parent SOPs also have associated artifacts that should be reviewed with their parent revision package (listed in Group 2 table).

This plan intentionally does not assign speculative final disposition to every form/template/traveler. The required action is parent-linked compatibility review during each SOP revision wave.

---

## 6. Recommended Sequence

The sequence below is designed to reduce rework and keep foundational system-language changes ahead of dependent procedures.

### Wave 1: Foundation rewrite

1. **QM.SLQ014 first**  
   Rationale: It is the direct system work instruction and currently describes FileHold operating behavior in detail. Updating this first establishes shared transition language for the rest of the system.

2. **QM.SLQ001 second**  
   Rationale: It is the master document control SOP and controls language used across document lifecycle and records retention activities.

### Wave 2: Targeted procedural revisions

3. **Group 2 documents next** (`QM.SLQ003`, `QM.SLQ017`, `QM.SLQ020`, `QM.SLQ036`, `QM.SLQ015`, `QM.SLQ004`)  
   Rationale: These have procedural FileHold instructions that affect day-to-day operations and records evidence handling.

### Wave 3: Batched light updates

4. **Group 3 documents as controlled batches**  
   Rationale: These are mostly boilerplate-level references and can be updated efficiently once foundation language is stable.

Group 4 documents (no FileHold references) require no action for this transition.

---

## 7. What This Plan Does Not Cover

This plan is intentionally focused on a single question: *which QMS procedures need to be updated to replace FileHold references with SilqQMS references, and in what order?* The following are explicitly out of scope:

- **Regulatory gap analysis** — A separate project will assess whether our QMS procedures satisfy the requirements of the new FDA QMSR (which incorporates ISO 13485:2016 by reference). That analysis covers regulatory citation accuracy, procedural adequacy against ISO clauses, and QMSR-specific requirements. Some documents will need both platform-transition revisions (this plan) and regulatory-alignment revisions (the gap analysis). Coordinating the two will be a leadership decision once both scopes are defined.

- **Data migration** — Moving existing files, records, and document archives from FileHold into SilqQMS is a separate operational and technical activity. This plan covers procedure text updates, not the logistics of transferring historical data between systems.

- **Software validation of SilqQMS** — Validation planning and execution for the new system are separate technical/quality activities.

- **Training** — This plan identifies where procedure revisions are needed. The training plan for rolling out those changes to staff will follow once leadership confirms the revision scope and sequencing.

- **Specific future procedure wording** — This document identifies *what* needs to change and *why*. The actual revised procedure language is a decision for leadership and document owners, not this plan.

---

## Appendix: Workload Summary

| Group | Documents | Effort Level |
|---|---:|---|
| Complete Rewrite | 2 | High — foundational procedures that define system workflows |
| Targeted Revision | 6 | Moderate — procedural steps reference FileHold operations |
| Simple Text Update | 25 | Low — boilerplate glossary/records-filing language only |
| No Changes Needed | 13 | None — no FileHold content |
| **Total** | **46** | |

**Bottom line:** 33 of 46 QM documents need some level of revision. The vast majority (25) are simple text updates. The heavy lifting is concentrated in 8 documents — 2 foundational rewrites and 6 targeted revisions.
