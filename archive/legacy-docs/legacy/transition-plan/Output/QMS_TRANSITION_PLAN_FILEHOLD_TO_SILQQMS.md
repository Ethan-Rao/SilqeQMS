# QMS Transition Plan: FileHold to SilqQMS

**Date:** 2026-03-23  
**Requested by:** Ethan Rao, Director R&D, QA, Regulatory Affairs  
**Scope:** Transition of controlled QMS documents and records from FileHold-based operation to SilqQMS as system of record, with QMSR-driven document updates and release sequencing.

---

## Part 1: Executive Summary

### Purpose and Scope

This plan defines how Silq will transition QMS document control from FileHold to SilqQMS while simultaneously implementing the QMSR transition updates identified in the current gap analysis (`docs/gap-analysis/QMS_GAP_ANALYSIS_ISO13485_QMSR_2026_03.md`).

The plan covers:
- Platform transition (FileHold -> SilqQMS)
- Content transition (QMSR/ISO citation and procedural updates)
- Controlled release and training
- Verification/validation and final cutover

### High-Level Phases

1. **Preserve** - import FileHold originals into SilqQMS Admin Docs.
2. **Revise** - execute document updates per 46-document disposition matrix.
3. **Release** - route/approve and publish controlled revisions in Document Control.
4. **Train** - train users on system and content updates.
5. **Cutover** - make SilqQMS system of record and retire routine FileHold usage.

### Governance and Stakeholders

| Role | Primary Responsibility |
|---|---|
| President/CEO | Management oversight, decision gates, final cutover approval |
| VP of QA | QMS transition owner, change-control governance, risk/CAPA integration |
| VP of RA CA | Regulatory crosswalk owner (`§820.10(b)`, 803/806/821/830 mapping) |
| Director or Manager Manufacturing | Labeling/packaging, servicing, equipment-control implementation |
| Quality Specialist | Drafting support, checklist implementation, audit module and trend reporting |
| Chief Technology Officer | SilqQMS platform readiness and software validation coordination |

---

## Part 2: Current State - FileHold

### What FileHold Provides Today

FileHold has served as Silq’s legacy controlled-document system for:
- Storage/retrieval of QM procedures (`.docx`)
- Revision/version history
- Folder-based organization
- Electronic-signature process references (current `QM.SLQ014`)

### Current Control Method

- 46 QM documents currently exist as FileHold-era controlled exports.
- Supporting controlled artifacts (forms/templates/traveler) are maintained in repository folders and linked by parent SOP convention.
- Several records are still represented as exports and archived sets from prior FileHold transfer activity.

### Transition Drivers and Limitations

- Legacy 820 citation model is not aligned to revised QMSR structure.
- QMSR supplemental controls (`§820.35`, `§820.45`) are not yet uniformly explicit in SOP/forms.
- FileHold description in `QM.SLQ014` is no longer target-state aligned.
- SilqQMS now has required modules to unify controlled lifecycle + evidence integrity in one platform.

### `QM.SLQ014` Dependency

`QM.SLQ014 Rev B` currently describes FileHold practices and requires **full rewrite** for SilqQMS workflows, release states, and role responsibilities.

---

## Part 3: Target State - SilqQMS

### Platform Capabilities

SilqQMS provides two complementary document subsystems:

1. **Document Control module** (`document_control`) for formal controlled documents:
   - `Document`: `doc_number`, `title`, `doc_type`, owner, `status` (Draft -> Released -> Obsolete)
   - `DocumentRevision`: revision, change summary, effective date, release tracking
   - `DocumentFile`: storage, SHA256, content type, size, uploader metadata

2. **Admin Docs libraries** (`admin_docs`) for browseable record libraries:
   - `AdminDocFolder`: library + hierarchical folder tree
   - `AdminDocFile`: filename/storage/content metadata + folder association

### 11 Library Mapping

| Library Key | Display Name | Intended QMS Use |
|---|---|---|
| `qms_documents` | Quality Management Documents | Controlled originals, historical FileHold exports, and reference copies |
| `employee_training` | Employee Training | Training records and training evidence |
| `management_reviews` | Management Reviews, Audits & Approvals | MR packs, audits, inspection response records |
| `ncrs` | NCRs | NC records and supporting evidence |
| `capas` | CAPAs | CAPA files and closure evidence |
| `post_market_surveillance` | Post Market Surveillance | Complaints, MDR/eMDR, PMS trend records |
| `regulatory_standards` | Regulatory Standards & Approvals | Standards, clearances, registrations |
| `work_orders` | Work Orders | Work orders and related manufacturing control records |
| `risk_management` | Risk Management | RM plans/reviews/FMEAs and related files |
| `dhfs` | Design History Files (DHFs) | V&V and DHF evidence |
| `forms_templates_travelers` | Forms, Templates & Travelers | Controlled forms/templates/travelers |

### Entity-Linked Records

SilqQMS also supports module-linked documents for records tied to entities (equipment, suppliers, supplies, lots, purchasing). This supports retrieval by context (e.g., asset, supplier, lot) instead of only folder path.

### End-User Workflow Changes

- Users will browse/upload reference records in Admin Docs by subsystem library.
- Controlled QM document lifecycle (draft/release/obsolete/revision) will be managed in Document Control.
- Approval and release evidence becomes centralized in SilqQMS metadata + file integrity fields.

---

## Part 4: Document Disposition Matrix (All 46 QM Documents)

### Disposition Legend
- **Maintain**: no procedural content change needed in this transition wave
- **Revise**: targeted content/citation updates required
- **Rewrite**: substantial replacement required
- **Retire**: obsolete/superseded (none proposed in this phase)

| Document ID | Rev (Current) | Title | Disposition | Revision Scope | QMSR Citation Update | Target Rev | Priority | Associated Forms/Templates | Gap Analysis Cross-Reference |
|---|---:|---|---|---|---|---|---|---|---|
| QM.SLQ001 | A | Document Control SOP | Revise | Add explicit `§820.35` supplemental record control language; align to revised 820 structure | Yes | B | High | FM1-QM.SLQ001; FM2-QM.SLQ001; TMP1-QM.SLQ001 | Part 3.4; Part 7 #6 |
| QM.SLQ002 | B | Good Documentation Practices SOP | Revise | Citation modernization and consistency updates for revised QMSR terminology | Yes | C | Medium | None identified in inventory | Part 3.4; Part 7 #6 |
| QM.SLQ003 | B | Employee Training SOP | Revise | Add implementation language for QMSR-transition training wave and revised-document training completion criteria | Yes | C | Medium | FM1-QM.SLQ003; FM2-QM.SLQ003 | Part 3.8; Part 8 |
| QM.SLQ004 | A | Design Control Program SOP | Revise | Citation-only modernization to ISO/QMSR structure | Yes | B | Medium | FM1-QM.SLQ004 | Part 3.12; Part 7 #6 |
| QM.SLQ005 | B | Design Project Planning SOP | Revise | Citation-only modernization; confirm risk-planning linkage references | Yes | C | Medium | TMP1-QM.SLQ005 | Part 3.10; Part 7 #6 |
| QM.SLQ006 | A | Design Input SOP | Revise | Citation-only modernization | Yes | B | Medium | TMP1-QM.SLQ006; TMP2-QM.SLQ006 | Part 3.12; Part 7 #6 |
| QM.SLQ007 | A | Design Output SOP | Revise | Citation-only modernization | Yes | B | Medium | TMP1-QM.SLQ007; TMP2-QM.SLQ007 | Part 3.12; Part 7 #6 |
| QM.SLQ008 | A | Design Review SOP | Revise | Citation-only modernization | Yes | B | Medium | FM1-QM.SLQ008 | Part 3.12; Part 7 #6 |
| QM.SLQ009 | A | Design VV SOP | Revise | Citation-only modernization; confirm V&V traceability references | Yes | B | Medium | FM1-QM.SLQ009; TMP1-QM.SLQ009; TMP2-QM.SLQ009; TMP3-QM.SLQ009 | Part 3.12; Part 7 #6 |
| QM.SLQ010 | A | Design Transfer SOP | Revise | Citation-only modernization | Yes | B | Medium | TMP1-QM.SLQ010; TMP2-QM.SLQ010 | Part 3.12; Part 7 #6 |
| QM.SLQ011 | A | Statistical Techniques WI | Maintain | No content change in this wave; verify citations and update only if legacy references found | Review required | A (or B if citation update required) | Low | None identified in inventory | Part 3.21 |
| QM.SLQ012 | B | Risk Management SOP | Revise | Add formal complaint/CAPA/MDR trigger-to-risk update workflow and RM traceability requirement | Yes | C | High | TMP1-QM.SLQ012 | Part 5; Part 7 #9 |
| QM.SLQ013 | B | Risk Analysis SOP | Revise | Citation modernization; align hazard/FMEA references to current RM file governance | Yes | C | Medium | TMP1-QM.SLQ013; TMP2-QM.SLQ013; TMP3-QM.SLQ013 | Part 5; Part 7 #9 |
| QM.SLQ014 | B | Electronic Doc System WI | Rewrite | Complete rewrite from FileHold model to SilqQMS model (Document Control + Admin Docs + release workflow) | Yes | C | Critical | FM1-QM.SLQ014 | Part 2; Part 3.4; Part 7 #6 |
| QM.SLQ015 | B | Supplier QA SOP | Revise | Citation modernization and risk-based supplier evidence traceability updates | Yes | C | Medium | FM1-QM.SLQ015; FM2-QM.SLQ015; FM3-QM.SLQ015; FM4-QM.SLQ015; FM5-QM.SLQ015; FM6-QM.SLQ015; FM7-QM.SLQ015; FM8-QM.SLQ015 | Part 3.13; Part 7 #6 |
| QM.SLQ016 | C | CAPA SOP | Revise | Tighten effectiveness verification criteria and QMSR-linked closure evidence language | Yes | D | High | FM1-QM.SLQ016 | Part 3.24 |
| QM.SLQ017 | A | Internal Audits SOP | Revise | Add QMSR-focused audit module (`§820.10`, `§820.35`, `§820.45`) and evidence sampling rules | Yes | B | High | FM1-QM.SLQ017; FM2-QM.SLQ017; FM3-QM.SLQ017; FM4-QM.SLQ017; FM5-QM.SLQ017 | Part 3.20; Part 7 #8 |
| QM.SLQ018 | A | Management Review SOP | Revise | Add QMSR readiness KPI block and required transition-status inputs/outputs | Yes | B | High | FM1-QM.SLQ018 | Part 3.7; Part 7 #7 |
| QM.SLQ019 | C | Identification and Traceability SOP | Revise | Add explicit part 830/821 mapping and UDI capture controls per `§820.35(c)` | Yes | D | Critical | None identified in inventory | Part 3.16; Part 7 #2/#5 |
| QM.SLQ020 | D | Purchasing Controls SOP | Revise | Citation modernization and evidence linkage to incoming verification trend controls | Yes | E | Medium | FM1-QM.SLQ020 | Part 3.13; Part 7 #6 |
| QM.SLQ021 | D | Product Complaint System SOP | Revise | Add mandatory seven-element `§820.35(a)` checklist and file completeness controls | Yes | E | Critical | FM1-QM.SLQ021; TMP1-QM.SLQ021 | Part 3.19; Part 7 #1 |
| QM.SLQ022 | A | Medical Device Reporting | Revise | Confirm alignment to part 803 references and revised QMSR crosswalk language | Yes | B | Medium | None identified in inventory | Part 3.19; Part 4 |
| QM.SLQ023 | A | eMDR Submission Work Instruction | Revise | Citation/terminology modernization, confirm part 803 process references | Yes | B | Medium | None identified in inventory | Part 3.19; Part 4 |
| QM.SLQ025 | A | Quality Planning SOP | Revise | Add QMSR transition planning/KPI linkage language | Yes | B | Medium | None identified in inventory | Part 3.5; Part 7 #7 |
| QM.SLQ026 | C | Part Number Assignment WI | Revise | Citation-only modernization with traceability alignment checks | Yes | D | Medium | None identified in inventory | Part 3.16; Part 7 #6 |
| QM.SLQ027 | E | Quality Manual | Revise | Add QMS process/risk interaction map and ISO-to-QMSR overlay matrix; update legacy citations | Yes | F | Critical | None identified in inventory | Part 3.1/3.2; Part 7 #6 |
| QM.SLQ028 | A | Protection of Confidential Patient Information | Maintain | No substantive QMSR change expected; confirm no legacy 820 citations | Review required | A (or B if citation update required) | Low | None identified in inventory | Part 3.2 |
| QM.SLQ029 | A | DHR Review and Approval SOP | Revise | Ensure UDI/traceability fields and release evidence align with `§820.35(c)` and `§820.45` controls | Yes | B | High | FM1-QM.SLQ029 | Part 3.16; Part 7 #2/#3 |
| QM.SLQ030 | A | Advisory Notices and Recalls SOP | Revise | Verify/update part 806 cross-references per `§820.10(b)(4)` | Yes | B | High | FM1-QM.SLQ030; FM2-QM.SLQ030; FM3-QM.SLQ030; FM4-QM.SLQ030 | Part 3.11; Part 7 #5 |
| QM.SLQ032 | A | Software Validation SOP | Revise | Confirm SilqQMS validation scope/UAT evidence requirements for transition | Yes | B | High | None identified in inventory | Part 9; Part 7 #9 |
| QM.SLQ033 | A | Post-Market Surveillance SOP | Revise | Ensure complaint/MDR trend feedback loop to RM/CAPA is explicit | Yes | B | Medium | None identified in inventory | Part 3.19; Part 5 |
| QM.SLQ034 | F | Organization Chart | Maintain | Update only if role/responsibility changes required for transition governance | No | F (or G if changed) | Low | None identified in inventory | Part 1 governance |
| QM.SLQ035 | D | Quality Policy | Maintain | No direct procedural change expected; optional wording refresh for QMSR transition | No | D (or E if refreshed) | Low | None identified in inventory | Part 3.5 |
| QM.SLQ036 | E | Sales Order SOP | Revise | Confirm customer-process references and records routing to controlled locations | Yes | F | Medium | FM1-QM.SLQ036 | Part 3.11 |
| QM.SLQ037 | A | Quality Objectives | Revise | Add explicit QMSR transition KPI targets (completion rates, audit results, citation closure) | No (content KPI update) | B | Medium | None identified in inventory | Part 3.5; Part 7 #7/#11 |
| QM.SLQ038 | B | Managing Regulatory Inspections | Revise | Add revised QMSR inspection-readiness evidence checklist | Yes | C | Medium | None identified in inventory | Part 2; Part 6 |
| QM.SLQ039 | B | Receiving Inspection SOP | Revise | Confirm incoming-record fields support traceability and supplier-control evidence | Yes | C | Medium | FM1-QM.SLQ039; FM2-QM.SLQ039 | Part 3.13/3.16 |
| QM.SLQ040 | B | Nonconforming Materials SOP | Revise | Strengthen NC trend-to-CAPA linkage and objective closure evidence | Yes | C | High | FM1-QM.SLQ040; FM2-QM.SLQ040 | Part 3.22; Part 3.24 |
| QM.SLQ043 | A | Work Order SOP | Revise | Citation modernization and work-order evidence routing to SilqQMS libraries | Yes | B | Medium | FM1-QM.SLQ043 | Part 3.14; Part 6 |
| QM.SLQ045 | A | Receiving SOP | Revise | Citation modernization and records-location control updates | Yes | B | Medium | TMP1-QM.SLQ045 | Part 3.11/3.16 |
| QM.SLQ046 | A | Shipping SOP | Revise | Citation modernization and controlled shipping-record routing updates | Yes | B | Medium | FM1-QM.SLQ046; TMP1-QM.SLQ046 | Part 3.11/3.16 |
| QM.SLQ047 | A | Process Validation SOP | Revise | Add outsourced sterilization control appendix and acceptance/change-notification controls | Yes | B | High | None identified in inventory | Part 3.15; Part 7 #9 |
| QM.SLQ048 | A | Device Master Record SOP | Revise | Citation modernization and DMR/MDF traceability language updates | Yes | B | Medium | None identified in inventory | Part 3.3 |
| QM.SLQ049 | A | Workstation Practices SOP | Revise | Citation modernization and environment/control evidence wording updates | Yes | B | Medium | None identified in inventory | Part 3.9 |
| QM.SLQ050 | A | Calibration and Preventive Maintenance SOP | Revise | Add calibration-required vs not-required classification framework and evidence standards | Yes | B | High | FM1-QM.SLQ050; FM2-QM.SLQ050; FM3-QM.SLQ050; FM4-QM.SLQ050; FM5-QM.SLQ050; FM6-QM.SLQ050 | Part 3.17; Part 7 #10 |
| QM.SLQ051 | A | Environmental Monitoring | Revise | Citation modernization and management review trend linkage | Yes | B | Medium | FM1-QM.SLQ051 | Part 3.9 |

### Numbering Gaps

Unused numbers available for future procedures:
- `QM.SLQ024`
- `QM.SLQ031`
- `QM.SLQ041`
- `QM.SLQ042`
- `QM.SLQ044`

---

## Part 5: Forms, Templates, and Travelers Disposition

### Count Reconciliation Note

Prompt baseline states 65 controlled artifacts (44 forms, 20 templates, 1 traveler).  
Current inventory listing provides 62 explicitly enumerated artifacts (41 forms, 20 templates, 1 traveler).  
Transition action: perform a controlled reconciliation during Phase 1 to identify any additional forms not listed in the current inventory register.

### Comprehensive Register (Inventory-Enumerated Controlled Artifacts)

| ID | Type | Parent | Disposition | Transition Note |
|---|---|---|---|---|
| FM1-QM.SLQ001 | Form | QM.SLQ001 | Revise with parent | Validate DCO and approval workflow language |
| FM2-QM.SLQ001 | Form | QM.SLQ001 | Revise with parent | Validate approver structure and release routing |
| FM1-QM.SLQ003 | Form | QM.SLQ003 | Revise with parent | Add transition-training tracking fields if needed |
| FM2-QM.SLQ003 | Form | QM.SLQ003 | Revise with parent | Align training completion evidence conventions |
| FM1-QM.SLQ004 | Form | QM.SLQ004 | Review with parent | Citation-only impact check |
| FM1-QM.SLQ008 | Form | QM.SLQ008 | Review with parent | Citation-only impact check |
| FM1-QM.SLQ009 | Form | QM.SLQ009 | Review with parent | Citation-only impact check |
| FM1-QM.SLQ014 | Form | QM.SLQ014 | Revise with parent | Replace FileHold-specific acknowledgement content |
| FM1-QM.SLQ015 | Form | QM.SLQ015 | Review with parent | Supplier evidence metadata alignment |
| FM2-QM.SLQ015 | Form | QM.SLQ015 | Review with parent | Supplier evidence metadata alignment |
| FM3-QM.SLQ015 | Form | QM.SLQ015 | Review with parent | Supplier evidence metadata alignment |
| FM4-QM.SLQ015 | Form | QM.SLQ015 | Review with parent | Supplier evidence metadata alignment |
| FM5-QM.SLQ015 | Form | QM.SLQ015 | Review with parent | Supplier evidence metadata alignment |
| FM6-QM.SLQ015 | Form | QM.SLQ015 | Review with parent | Supplier evidence metadata alignment |
| FM7-QM.SLQ015 | Form | QM.SLQ015 | Review with parent | Supplier evidence metadata alignment |
| FM8-QM.SLQ015 | Form | QM.SLQ015 | Review with parent | Supplier evidence metadata alignment |
| FM1-QM.SLQ016 | Form | QM.SLQ016 | Revise with parent | CAPA effectiveness evidence fields |
| FM1-QM.SLQ017 | Form | QM.SLQ017 | Revise with parent | Add QMSR supplemental module prompts |
| FM2-QM.SLQ017 | Form | QM.SLQ017 | Revise with parent | Add QMSR supplemental module prompts |
| FM3-QM.SLQ017 | Form | QM.SLQ017 | Revise with parent | Add QMSR supplemental module prompts |
| FM4-QM.SLQ017 | Form | QM.SLQ017 | Revise with parent | Add QMSR supplemental module prompts |
| FM5-QM.SLQ017 | Form | QM.SLQ017 | Revise with parent | Add QMSR supplemental module prompts |
| FM1-QM.SLQ018 | Form | QM.SLQ018 | Revise with parent | Add QMSR readiness KPI block capture |
| FM1-QM.SLQ020 | Form | QM.SLQ020 | Review with parent | Citation-only update impact check |
| FM1-QM.SLQ021 | Form | QM.SLQ021 | **Critical independent update** | Add mandatory seven `§820.35(a)` fields and completion checklist |
| FM1-QM.SLQ029 | Form | QM.SLQ029 | Revise with parent | Add UDI consistency fields/checks |
| FM1-QM.SLQ030 | Form | QM.SLQ030 | Revise with parent | Verify part 806 workflow fields |
| FM2-QM.SLQ030 | Form | QM.SLQ030 | Revise with parent | Verify part 806 workflow fields |
| FM3-QM.SLQ030 | Form | QM.SLQ030 | Revise with parent | Verify part 806 workflow fields |
| FM4-QM.SLQ030 | Form | QM.SLQ030 | Revise with parent | Verify part 806 workflow fields |
| FM1-QM.SLQ036 | Form | QM.SLQ036 | Review with parent | Controlled routing/retention checks |
| FM1-QM.SLQ039 | Form | QM.SLQ039 | Review with parent | Traceability/supplier evidence check |
| FM2-QM.SLQ039 | Form | QM.SLQ039 | Review with parent | Traceability/supplier evidence check |
| FM1-QM.SLQ040 | Form | QM.SLQ040 | Revise with parent | NC trend/CAPA trigger fields |
| FM2-QM.SLQ040 | Form | QM.SLQ040 | Revise with parent | NC trend/CAPA trigger fields |
| FM1-QM.SLQ043 | Form | QM.SLQ043 | Review with parent | Work-order record routing check |
| FM1-QM.SLQ046 | Form | QM.SLQ046 | Review with parent | Shipping record routing check |
| FM1-QM.SLQ050 | Form | QM.SLQ050 | Revise with parent | Calibration-required classification support |
| FM2-QM.SLQ050 | Form | QM.SLQ050 | Revise with parent | Calibration-required classification support |
| FM3-QM.SLQ050 | Form | QM.SLQ050 | Revise with parent | Calibration-required classification support |
| FM4-QM.SLQ050 | Form | QM.SLQ050 | Revise with parent | Calibration-required classification support |
| FM5-QM.SLQ050 | Form | QM.SLQ050 | Revise with parent | Calibration-required classification support |
| FM6-QM.SLQ050 | Form | QM.SLQ050 | Revise with parent | Calibration-required classification support |
| FM1-QM.SLQ051 | Form | QM.SLQ051 | Review with parent | Trend linkage fields if needed |
| TMP1-QM.SLQ001 | Template | QM.SLQ001 | Review with parent | Citation/control wording check |
| TMP1-QM.SLQ005 | Template | QM.SLQ005 | Review with parent | Citation-only impact check |
| TMP1-QM.SLQ006 | Template | QM.SLQ006 | Review with parent | Citation-only impact check |
| TMP2-QM.SLQ006 | Template | QM.SLQ006 | Review with parent | Citation-only impact check |
| TMP1-QM.SLQ007 | Template | QM.SLQ007 | Review with parent | Citation-only impact check |
| TMP2-QM.SLQ007 | Template | QM.SLQ007 | Review with parent | Citation-only impact check |
| TMP1-QM.SLQ009 | Template | QM.SLQ009 | Review with parent | Citation-only impact check |
| TMP2-QM.SLQ009 | Template | QM.SLQ009 | Review with parent | Citation-only impact check |
| TMP3-QM.SLQ009 | Template | QM.SLQ009 | Review with parent | Citation-only impact check |
| TMP1-QM.SLQ010 | Template | QM.SLQ010 | Review with parent | Citation-only impact check |
| TMP2-QM.SLQ010 | Template | QM.SLQ010 | Review with parent | Citation-only impact check |
| TMP1-QM.SLQ012 | Template | QM.SLQ012 | Revise with parent | Add RM trigger/traceability expectations |
| TMP1-QM.SLQ013 | Template | QM.SLQ013 | Review with parent | Risk analysis wording alignment |
| TMP2-QM.SLQ013 | Template | QM.SLQ013 | Review with parent | Risk analysis wording alignment |
| TMP3-QM.SLQ013 | Template | QM.SLQ013 | Review with parent | Risk analysis wording alignment |
| TMP1-QM.SLQ021 | Template | QM.SLQ021 | **Critical independent update** | Align response template with `§820.35(a)` completeness logic |
| TMP1-QM.SLQ045 | Template | QM.SLQ045 | Review with parent | Routing/retention check |
| TMP1-QM.SLQ046 | Template | QM.SLQ046 | Review with parent | Routing/retention check |
| TMP1-QC-C.SLQ001 | Template | QC-C.SLQ001 | Maintain | No direct QMSR transition change expected |
| TMP2-QC-C.SLQ001 | Template | QC-C.SLQ001 | Maintain | No direct QMSR transition change expected |
| TR-C.SLQ001 | Traveler | QM.SLQ043 / manufacturing workflow | Review | Confirm work-order traceability and UDI data capture alignment |

---

## Part 6: Migration Approach

### Phase 1: Preserve (Import Originals)

Goal: preserve FileHold baseline documents in SilqQMS Admin Docs before editing.

Primary method: existing script `scripts/bulk_import_admin_docs.py`:

```powershell
python scripts/bulk_import_admin_docs.py --directory "QM Documents" --library qms_documents --folder "Original - FileHold"
```

Expected behavior:
- Creates target folder if missing
- Imports allowed file types
- Skips duplicates by filename in target folder

Technical notes:
- Run dry-run first for reconciliation.
- Capture import log and file-count reconciliation report.

### Phase 2: Revise (Controlled Content/Citation Updates)

Goal: execute matrix-driven updates in Document Control module:
- Create/confirm `Document` record (`doc_number`, owner, type)
- Create next `DocumentRevision` with change summary and effective date
- Attach revised file(s) as `DocumentFile` with SHA256

### Phase 3: Release

Goal: release approved revisions:
- Complete release authorization workflow
- Set statuses Draft -> Released
- Archive superseded revisions as non-current

### Phase 4: Train

Goal: train users on:
- system workflow changes
- revised SOP content and QMSR overlays
- required forms/checklist use (especially `§820.35` and `§820.45` controls)

### Phase 5: Cutover

Goal: SilqQMS becomes system of record:
- Freeze routine FileHold authoring/use
- Retain controlled read-only historical access if needed
- Update all references and onboarding materials

### Data Integrity Verification Approach

- Pre/post import file counts by folder
- Spot checks by hash or exact binary compare
- Verify record discoverability in expected library/folder path

---

## Part 7: QMSR Revision Execution Plan

### Wave 1 (Critical)

Documents:
- `QM.SLQ021`, `QM.SLQ019`, `QM.SLQ027`, `QM.SLQ014`

Primary outcomes:
- `§820.35(a)` complaint completeness implemented
- `§820.35(c)` UDI capture implemented
- Quality manual crosswalk + process/risk map implemented
- FileHold WI replaced with SilqQMS WI

### Wave 2 (High)

Documents:
- `QM.SLQ001`, `QM.SLQ017`, `QM.SLQ018`, `QM.SLQ030`, `QM.SLQ047`, `QM.SLQ012`, `QM.SLQ050`, `QM.SLQ029`, `QM.SLQ032`, `QM.SLQ016`

Primary outcomes:
- QMSR audit module deployed
- Management review readiness KPI block deployed
- Advisory/recall references aligned
- Outsourced sterilization controls clarified
- Equipment classification framework deployed

### Wave 3 (Medium/Low)

Documents:
- Remaining citation-only or low-impact updates

Primary outcomes:
- legacy citation cleanup completed
- consistency across all QM docs

### Citation Modernization Strategy

Use **single controlled citation release package** for most docs where only references change, with:
- unified redline rationale
- impact statement
- batched training acknowledgement

### Dependency Sequence

1. `QM.SLQ014` (system WI) early
2. `QM.SLQ027` (manual) early
3. `QM.SLQ021` + forms/templates early
4. `QM.SLQ019` + traceability forms
5. audit/MR/risk/equipment high-priority controls
6. citation-only cleanup wave

---

## Part 8: Training Plan

### System Training (SilqQMS Platform)

Audience:
- QA/RA, manufacturing leadership, document owners, approvers

Topics:
- Document Control lifecycle (Draft/Released/Obsolete)
- Revision and release workflow
- Admin Docs navigation and upload conventions

### Content Training (Revised SOPs)

Priority training modules:
- `QM.SLQ021` complaint completeness (`§820.35(a)`)
- `QM.SLQ019` traceability/UDI (`§820.35(c)`)
- `QM.SLQ014` new electronic doc system workflow
- `QM.SLQ017` QMSR audit module
- `QM.SLQ018` management review KPI requirements

### Training Record Requirements

Training should be captured per `QM.SLQ003` expectations:
- assigned audience
- completion date
- effectiveness verification where required
- retrievable evidence in SilqQMS training library

---

## Part 9: Validation and Verification

### Migration Integrity Verification

- Verify imported count of FileHold originals equals source count.
- Validate random sample file hashes.
- Confirm metadata (filename/type/upload date/folder) correctness.

### Document Control Function Verification

For each pilot document:
- Create revision
- Attach file
- set effective date/change summary
- release and set current revision
- retrieve released current revision from UI

### UAT Approach

Test personas:
- Document owner
- QA approver
- Admin uploader
- Read-only user

Critical UAT scenarios:
- complaint record checklist completion flow
- labeling release checklist storage/retrieval
- traceability/UDI field retrieval during mock audit
- audit checklist and management review KPI evidence retrieval

### `QM.SLQ032` Applicability

Because SilqQMS is used in quality system processes, execute validation activities consistent with `QM.SLQ032` before full cutover:
- define intended use
- define validation scope and acceptance criteria
- execute and retain objective evidence

---

## Part 10: Timeline and Milestones

### Master Timeline (Aligned to Gap Analysis Dates)

| Milestone | Target Date | Gate |
|---|---|---|
| Phase 1 preserve import complete + reconciliation | 2026-04-10 | Gate 1: import integrity signed |
| Critical Wave 1 document revisions complete | 2026-04-30 | Gate 2: critical controls approved |
| High-priority Wave 2 controls complete | 2026-06-30 | Gate 3: operational readiness |
| Risk/equipment hardening complete | 2026-08-15 | Gate 4: evidence robustness |
| Transition trend pack operational + medium wave closure | 2026-09-15 | Gate 5: sustained monitoring |
| Final housekeeping and retrieval-risk closure | 2026-10-15 | Gate 6: cutover authorization |

### Decision Gates

- **Gate 1:** no data loss / import fidelity
- **Gate 2:** critical QMSR controls in force (`§820.35(a)/(c)`, `§820.45`)
- **Gate 3:** training + release coverage adequate
- **Gate 4:** inspection-simulation pass for evidence retrieval
- **Gate 5:** KPI trend stability demonstrated
- **Gate 6:** leadership cutover approval

### Risks and Contingencies

| Risk | Impact | Mitigation |
|---|---|---|
| Citation updates delayed | Slips release wave | Batch citation-only package and parallel review |
| Form/template cascade underestimated | Rework and schedule pressure | Parent-child impact checklist per SOP |
| Incomplete training completion | Adoption/compliance risk | staged release contingent on training completion |
| Pending CAPAs 2025-002/003 arrive mid-transition | Change in priority sequencing | reserve capacity in Wave 2 for CAPA-linked updates |

---

## Part 11: Document Numbering Gaps and Future Procedures

### Available QM Numbers

Reserved opportunities:
- `QM.SLQ024`
- `QM.SLQ031`
- `QM.SLQ041`
- `QM.SLQ042`
- `QM.SLQ044`

### Recommended New Procedure Candidates (If Leadership Chooses)

Based on transition needs, consider whether to keep as appendices or establish standalone procedures:

1. **QMSR Supplemental Records Procedure** (could consolidate `§820.35` controls across complaint/servicing/UDI record logic).
2. **Labeling and Packaging Verification Procedure** (if expansion beyond current SOP architecture is preferred for `§820.45` controls).
3. **QMSR Regulatory Crosswalk Control Record** (controlled matrix artifact under QA/RA ownership).

---

## Implementation Notes

- CAPAs `2025-002` and `2025-003` are expected pending uploads and should be integrated into revision sequencing once available.
- This plan is designed to distinguish:
  - **QMSR transition-critical actions** (must complete for readiness), and
  - **broader quarterly quality improvements** (tracked separately).

---

## Final Transition Recommendation

Execute this plan as a controlled program with strict gate criteria, beginning with import preservation and Wave 1 critical revisions. Keep QMSR controls as the primary transition objective, and batch citation-only updates for efficiency. This approach minimizes operational disruption while delivering auditable, leadership-visible readiness by Q4 2026.

