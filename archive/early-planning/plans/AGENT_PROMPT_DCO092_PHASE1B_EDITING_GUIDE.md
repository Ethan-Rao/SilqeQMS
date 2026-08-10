# Agent Prompt: DCO092 Phase 1B — Detailed Document Editing Guide

**For use by:** New agent session
**Prepared by:** QMS management agent, May 28, 2026
**Context document:** `docs/plans/AGENT_PROMPT_DCO092_PHASE1B_EDITING_GUIDE.md`

---

## YOUR TASK

You are a quality management system (QMS) expert agent working within the SilqQMS project folder (`c:\Users\Ethan\OneDrive\Desktop\SilqQMS`).

Your task is to produce a **very detailed, specific, document-by-document editing guide** for DCO092 — the Phase 1B document revision package under design project DC.SLQ002 ("Silq eQMS EDMS Transition"). This guide will be used by the document originator (Ethan Rao) to write the actual revised documents.

**Do not create or modify any actual SOP documents.** Your only output is the editing guide itself, which you will write to:

```
docs/DCO092/DCO092_PHASE1B_EDITING_GUIDE.md
```

If the `docs/DCO092/` folder does not exist, create it.

---

## BACKGROUND CONTEXT (read this carefully)

### Design Project: DC.SLQ002

SILQ is executing design project DC.SLQ002, "Silq eQMS Electronic Document Management System Transition Plan." This project transitions SILQ's quality document operations from the legacy **FileHold** document management system to the **Silq eQMS** system (a custom-developed web-based EDMS at silqeqms.com, validated per SW.SLQ007–012).

**Phase 1A** (DCO091, currently in process) completed major rewrites of:
- `QM.SLQ001 Rev A → B` (Document Control SOP)
- `QM.SLQ014 Rev B → C` (Electronic Document System WI)
- `FM1-QM.SLQ014 Rev A → B` (Electronic Signature Acknowledgement Form)

**Phase 1B** (DCO092, you are guiding this work) requires **line-by-line review and revision** of six SOPs and their associated forms, removing all FileHold-specific references and replacing them with Silq eQMS–equivalent operations. Each document must ALSO address relevant compliance findings from the IA-2025 internal audit.

### Two Drivers for Every Phase 1B Document

Every document in Phase 1B must be revised for **two distinct reasons**, and the editing guide must address both:

1. **EDMS Transition (DC.SLQ002):** Replace all references to "FileHold" (including FileHold-specific workflows, UI mechanics, import/scan procedures, sign-off sheet windows, drawer/folder names, etc.) with Silq eQMS–equivalent operations, consistent with the language established in QM.SLQ001 Rev B and QM.SLQ014 Rev C.

2. **Audit Compliance (IA-2025, CAPA004):** Implement specific procedural changes to address the Minor Non-Compliances (mNCs) and applicable Opportunities for Improvement (OFIs) from the IA-2025 internal audit (conducted April 23–24, 2026 by Stephen Page, MedReg Associates Inc.).

### FileHold → Silq eQMS Translation Rules (from Phase 1A)

The following is the approved translation language from QM.SLQ001 Rev B and QM.SLQ014 Rev C. Apply these consistently:

| Old (FileHold) | New (Silq eQMS) |
|---|---|
| "FileHold" (in Definitions) | "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ." |
| "scan and import into FileHold" | "upload to Silq eQMS" |
| "import into [Folder] within FileHold" | "upload to Silq eQMS Admin Docs, [library name], [subfolder]" |
| "checked in/out of FileHold" | "uploaded to / retrieved from Silq eQMS" |
| "file within appropriate [X] folder within FileHold" | "file in Silq eQMS Admin Docs, [appropriate library], [subfolder]" |
| "Sign-off sheet window in FileHold" | "Silq eQMS training record sign-off" |
| "Retrieved from FileHold" / "See QM.SLQ014 for instructions to retrieve" | "Accessed in Silq eQMS per QM.SLQ014" |
| "Maintained in FileHold" | "Maintained in Silq eQMS" |
| "FileHold drawer" | "Silq eQMS Admin Docs library" |
| Regulatory references to "21 CFR 820" / "QSR" alone | Update to include "21 CFR Part 820 Quality Management System Regulation (QMSR)" |
| "QSR" abbreviation definition | Update to "QMSR: Quality Management System Regulation (21 CFR Part 820, as revised)" |

The Silq eQMS Admin Docs library structure (use for file placement guidance):
- QM Documents
- Design History Files
- Supplier Quality Records
- Purchasing Records
- Sales Order Records
- Internal Audit Records
- Training Records
- CAPA Records
- Calibration & Maintenance Records
- Regulatory Standards and Approvals
- Environmental Monitoring

---

## IA-2025 AUDIT FINDINGS RELEVANT TO PHASE 1B DOCUMENTS

The full audit report is at:
`docs/QMS-Readable-Texts/20-QMSInProcess/CAPA004/IA-2025 Final Report Readable.md`

The findings relevant specifically to Phase 1B documents are:

**mNC #1 (QM.SLQ004 — Design Control Program SOP)**
The Design Control procedure does not consistently establish clear and comprehensive requirements to ensure effective planning, execution, and control of design and development activities. Specific gaps:
- No clear requirement that all design changes be evaluated under formal design change controls with documented determination of required V&V activities
- Absence of defined minimum planning requirements for design/development activities (review, verification, validation, design transfer responsibilities)
- Project plan updates tied to phase reviews but formal change control requirements for plan revisions are not defined
- Conflict resolution authority not clearly defined; procedure does not require documented rationale, functional review, or traceable approval
- Design outputs not consistently required to be formally controlled
- No defined responsibility/criteria for when preliminary/exploratory work product must be captured in the DHF
- V&V planning described as optional based on project scope, without ensuring required V&V activities are formally planned and controlled
- Procedure requires documentation of validation equivalence to production units but does not define criteria or methodology
- Design transfer sign-off via checklist allowed in lieu of a final design review, without ensuring formal review requirements

**mNC #4 (QM.SLQ015 — Supplier QA SOP)**
The procedure does not clearly define that supplier assessment and monitoring frequencies are determined based on risk. Fixed assessment intervals (annual/biennial) are assigned by category without a mechanism to adjust based on supplier performance risk.

**mNC #5 (QM.SLQ020 — Purchasing Controls SOP)**
The procedure uses "wherever possible" language for supplier change notification requirements (Section 6.3: "Contracts, Supplier Agreements, and Purchase Orders shall include, wherever possible, that SILQ be notified of any changes..."). This permissive language contributed to CAPA 2025-003. Supplier change notification must be established as a mandatory requirement.

**OFI #4 (QM.SLQ015 — Supplier QA SOP)**
The procedure does not clearly require documented justification when supplier approval is based on self-assessment and certification for higher-risk suppliers (Category I, III). Documented justification including an appropriate risk assessment should be required.

**OFI #7 (QM.SLQ003 — Employee Training SOP)**
The Employee Training procedure includes provisions for training effectiveness evaluation; however, discretionary language ("may be evaluated") in related sections may lead to inconsistent application. Language should be strengthened to require effectiveness evaluation based on risk and task complexity, consistent with Section 8.11 of the same procedure.

**OFI #8 (All Phase 1B documents)**
Outdated pre-QMSR regulatory references (references to 21 CFR 820 as "Quality System Regulation" rather than "Quality Management System Regulation") exist in all Phase 1B documents. Update all regulatory citations to reflect the current QMSR framework.

---

## PHASE 1B DOCUMENTS IN SCOPE FOR DCO092

The following documents must be revised. For each document, your editing guide must provide:
1. A **complete list of all FileHold references** found in the document (quote the exact current text)
2. The **specific replacement text** for each FileHold reference (exact new wording)
3. The **specific audit compliance edits** (what section, what the current language is, and what new language is required)
4. Any **regulatory reference updates** (OFI #8)
5. **Definition section updates** (update "FileHold" definition, add "Silq eQMS" definition, update "QSR" to "QMSR")
6. **Document revision number** (next sequential letter)

### Document 1: QM.SLQ003 Employee Training SOP (Rev B → Rev C)
**Associated forms:** FM1-QM.SLQ003 Employee Training Program Form, FM2-QM.SLQ003 Employee Training Record Form

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ003 B Employee Training SOP.md`

**FileHold references to find and replace** (there are at least 8 — find all of them, quoting current text and specifying replacement):
- Section 5 Definitions: "FileHold: Software based document management system used to electronically store controlled documents."
- Section 5 Responsibilities (Training Coordinator): "The Training Coordinator is responsible for scanning and importing pdf of completed training records into appropriate employee training files within FileHold."
- Section 9 (Completing Employee Training Program Forms): "Once completed, the training coordinator scans the form, and imports into employee file folder within FileHold."
- Section 9: "the training coordinator scans and imports into employee file folder within FileHold"
- Section 10 (Completing Employee Training Record), Date field instruction: "if training signoffs are done electronically, the date of training is located within the 'Sign-off sheet' window in FileHold"
- Section 10, Trainer Date field instruction: "if training signoffs are done electronically, the date is located within the 'Sign-off sheet' window in FileHold"
- Section 10: "The training coordinator reviews the form for completeness and resolves any issues with the employee. Once complete, the training coordinator scans and imports into employee file folder within FileHold."
- Section 11 (Retrieval): "Employee training programs and training records are maintained in FileHold." and "See QM.SLQ014 for instructions on how to retrieve/access employee training programs and training records."
- Section 12 (Training Coordinator): "the training coordinator is to print a hard copy (or electronic copy) of the training matrix, initial/date, scan and import into FileHold"
- Section 12: "the training coordinator is to identify training discrepancies, print a hard copy (or electronic copy) of the file, initial/date, scan and import into FileHold"
- Section 12: "The training coordinator will initial note on the hard copy (or electronic copy) file indicating the notification action has been performed. Scan and import into FileHold."
- Section 10, sign-off instruction: "Sign off on training records may be done electronically in FileHold or manually."

**Audit compliance edits (OFI #7):**
- Locate the section on training effectiveness evaluation. Current language in Section 8.11 says effectiveness evaluations "will be conducted based on the complexity of the task/procedure and/or associated risk." However, related sections use "may be evaluated." Identify all instances of discretionary language ("may be evaluated," "may require") related to training effectiveness and upgrade to mandatory language consistent with Section 8.11. Provide the specific section numbers, current text, and required replacement text.

**Regulatory reference updates (OFI #8):**
- Update all references to "QSR" as an abbreviation to "QMSR"
- Update reference "21 CFR 820 Quality System Regulation (820.25 – Personnel)" to "21 CFR Part 820 Quality Management System Regulation (820.25 – Personnel)"
- In Definitions Abbreviations: Change "QSR: FDA Quality System Regulation" to "QMSR: Quality Management System Regulation (21 CFR Part 820, as revised)"

**Forms (FM1-QM.SLQ003 and FM2-QM.SLQ003):**
- Identify if either form contains any FileHold-specific instructions or references
- Current readable texts at:
  - `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ003 A Employee Training Program.md`
  - `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM2-QM.SLQ003 B Employee Training Record.md`
- Read these files and specify any required changes

---

### Document 2: QM.SLQ017 Internal Audits SOP (Rev A → Rev B)
**Associated forms:** FM1–FM5-QM.SLQ017 (Audit Schedule, Checklist, Final Report, Certificate, Auditor Qualification)

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ017 A Internal Audits SOP.md`

**FileHold references to find and replace** (there are at least 5):
- Section 5 Definitions: "FileHold: Software based document management system used to electronically store controlled documents."
- Section 7 (Auditor Requirements), FM5 filing: "Auditor Qualification Record, FM5-QM.SLQ017, shall be completed, scanned, imported into FileHold, and filed as follows: For internal auditors: File in employee's training folder. For external auditors: File within the auditor's Supplier Quality folder in the Supplier QA drawer."
- Section 10 (Post Audit): "A Certificate of Internal Audit, Form FM4-QM.SLQ017, shall be completed, scanned, imported into FileHold, and filed with the associated internal audit documents."
- Section 12 (Internal Quality Audit Schedule): "Hardcopy schedule shall be scanned and imported into appropriate Internal Audit folder within FileHold."
- Section 12: "Quality Assurance shall scan and import into appropriate Internal Audit folder within FileHold."
- Section 14 (Internal Quality Audit Records): "Scan all completed internal audit records and import into FileHold; file within appropriate Internal Audit folder."

**No audit compliance mNC/OFI directly assigned to QM.SLQ017 in IA-2025** — this document's revision is EDMS transition only (plus OFI #8 regulatory reference updates).

**Regulatory reference updates (OFI #8):**
- Update "21 CFR 820 Quality System Regulation (820.22 – Quality Audits)" to "21 CFR Part 820 Quality Management System Regulation (820.22 – Quality Audits)"
- Note: ISO 13485:2016 Section 8.2.4 reference is current and correct — retain as-is

**Forms (FM1–FM5-QM.SLQ017):**
- Current readable texts are in `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/` and `docs/QMS-Readable-Texts/22-Audits/IA2025/`
- Read each form and identify any FileHold-specific instructions embedded in form instructions/fields
- The FM3 and FM4 forms are blank template forms — note whether footer or instructions reference FileHold
- Specify all required changes

---

### Document 3: QM.SLQ020 Purchasing Controls SOP (Rev D → Rev E)
**Associated forms:** FM1-QM.SLQ020 Purchase Order Form

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ020 D Purchasing Controls SOP.md`

**FileHold references to find and replace** (there are at least 4):
- Section 4 Definitions: "FileHold: Software based document management system used to electronically store controlled documents."
- Section 6 (Purchasing), P.O. filing: "Completed purchase orders are to be scanned and imported into the appropriate Purchasing folder within FileHold."
- Section 7 (Closing Purchase Orders): "Closed purchase order is checked in to FileHold." AND "Purchase order log is checked out of FileHold, updated with closure information and checked back in to FileHold."
- Section 11 (Purchasing Records): "Import all completed purchasing records into FileHold; file within appropriate Purchasing folder."

**Audit compliance edits — mNC #5 (MANDATORY):**
The most critical edit. Current Section 6.3 reads:
> "Contracts, Supplier Agreements, and Purchase Orders shall include, wherever possible, that SILQ be notified of any changes made to the product and/or service prior to those changes becoming effective so that SILQ can determine the impact of changes to the quality of the final product or quality system."

The phrase "wherever possible" must be removed and replaced with mandatory language. Provide:
- The exact new text for Section 6.3 that establishes supplier change notification as a mandatory requirement
- Consider language such as: "Contracts, Supplier Agreements, and Purchase Orders shall require, as a standard condition, that SILQ be notified of any changes made to the product and/or service prior to those changes becoming effective. This requirement is mandatory and shall not be omitted. Supplier change notifications enable SILQ to determine the impact of changes on the quality of the final product or quality system prior to implementing or accepting such changes."
- Specify whether any additional subsection should be added to define what happens when a supplier change notification is received (e.g., triggering design change evaluation per QM.SLQ004 and QM.SLQ015 SCAR process)

**Regulatory reference updates (OFI #8):**
- Update all "21 CFR 820" references to include "Quality Management System Regulation (QMSR)" terminology
- Update "QSR:" abbreviation if present

**Form FM1-QM.SLQ020 (Purchase Order Form):**
- Read current form at: `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ020 B Purchase Order Form.md`
- Identify if the form contains any FileHold instructions
- Determine if any field should be added to the PO form to explicitly capture/confirm that supplier change notification requirement was communicated (to close mNC #5)

---

### Document 4: QM.SLQ036 Sales Order SOP (Rev E → Rev F)
**Associated forms:** FM1-QM.SLQ036 Sales Order Form

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ036 E Sales Order SOP.md`

**FileHold references to find and replace** (there are at least 3):
- Section 4 Definitions: "FileHold: Software-based document management system used to electronically store controlled documents."
- Section 6.2 (Sales Order Log): "Sales/Customer Service is to maintain a sales order log (filed in FileHold)..."
- Section 6.3 (Sales Order Approval): "The approved sales order is maintained in FileHold in accordance with Section 7."
- Section 8 (Sales Order Records Retention): "All sales orders and applicable documentation are filed and maintained in the Sales Order drawer of FileHold..." AND "Records are to be scanned and imported into FileHold and filed within appropriate Sales Order folder."

**No audit mNC directly assigned to QM.SLQ036** — this revision is EDMS transition only (plus OFI #8 regulatory reference updates).

**Regulatory reference updates (OFI #8):**
- Update the ISO 13485:2016 reference in Section 3 Reference Documents (Section 7.2 citation — this is accurate, retain content but check format)
- Note: QM.SLQ036 currently does not list a 21 CFR Part 820 reference — assess whether one should be added given QMSR update context, and advise accordingly

**Practical consideration — ShipStation references:**
- Section 6.5 contains detailed ShipStation UI instructions (login URL, figures, field-by-field entry). These are not FileHold-related and should be reviewed to determine if they are still current (https://ship13.shipstation.com/ etc.). Advise the originator whether this section needs a currency review and how to handle potentially outdated software UI instructions in a controlled document context.

**Form FM1-QM.SLQ036 (Sales Order Form):**
- Read current form at: `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ036 A Sales Order Form.md`
- Identify any FileHold references in the form

---

### Document 5: QM.SLQ015 Supplier Quality Assurance SOP (Rev B → Rev C)
**Associated forms:** FM1–FM8-QM.SLQ015

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ015 B Supplier QA SOP.md`

**FileHold references to find and replace** (there are at least 4):
- Section 4 Definitions: "FileHold: Software based document management system used to electronically store controlled documents."
- Section 10 (Completing Supplier Self-Assessments): "Scan and import into FileHold and file in the appropriate Supplier Quality folder."
- Section 12 (Supplier Re-Evaluation): "Document is scanned and imported into FileHold and filed in appropriate Supplier Quality file."
- Section 17 (Supplier Assessment Records): "Records and applicable documentation are to be scanned and imported into FileHold and filed within appropriate Supplier Quality Record file folder."

**Audit compliance edits — mNC #4 (MANDATORY):**
Current Section 6 defines supplier categories (I–V) and Section 8 defines re-evaluation frequencies as fixed: Category I = annual, Category III = biennial, Category IV = biennial, Category V = biennial. These fixed intervals are not linked to risk-based determination.

Required changes:
- In Section 15 (Supplier Assessment Schedule, Section 15 in the SOP), add explicit language that the assessment and re-evaluation frequency for each supplier shall be determined based on risk, including: supplier category, past performance, nature of products/services supplied, and results of prior assessments. The current fixed intervals (annual/biennial) represent minimums, not ceilings.
- In Section 8 (Supplier Qualification Requirements), add language within each category sub-section clarifying that re-evaluation frequency may be increased from the stated minimum based on risk assessment (e.g., poor performance, safety-critical products, post-SCAR situations).
- Provide specific draft language for these additions.

**Audit compliance edits — OFI #4 (recommended):**
For Category I and III suppliers where initial qualification is based on self-assessment and certification (not on-site audit), add a requirement for documented justification stating why self-assessment is sufficient given the supplier's risk level. This justification should be recorded in the Results section of the assessment form (FM1 or FM2-QM.SLQ015) and be subject to QA review and approval. Provide specific language for inclusion in Section 8, Category I and III initial qualification subsections.

**Regulatory reference updates (OFI #8):**
- Update "21 CFR 820 Quality System Regulation (820.50(a) – Evaluation of Suppliers...)" to "21 CFR Part 820 Quality Management System Regulation (820.50(a) – Purchasing Controls)"

**Forms (FM1–FM8-QM.SLQ015):**
- Read all forms at: `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/`
- Identify any FileHold references
- For FM1 and FM2 (Self-Assessment Survey Forms), determine if a field should be added to the Results section for documenting risk-based justification when self-assessment is used for higher-risk suppliers (to support OFI #4)
- For FM7 (Supplier Assessment Schedule Form), determine if a "Risk Basis for Frequency" column should be added to support mNC #4

---

### Document 6: QM.SLQ004 Design Control Program SOP (Rev B → Rev C)
**Associated forms:** FM1-QM.SLQ004 Design Project Scope Form

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ004 B Design Control Program SOP.md`

**FileHold references to find and replace** (there are at least 2):
- Section 4 Definitions: "FileHold: Software based document management system used to electronically store controlled documents."
- Section 15 (Design History File): "DHF documents are to be scanned and imported into FileHold and filed in the appropriate DHF."

**Audit compliance edits — mNC #1 (MANDATORY — most complex):**
This is the most extensive audit compliance edit. The IA-2025 identified nine distinct gaps in QM.SLQ004. The editing guide must provide specific new language for each gap, with precise placement in the document:

**Gap 1 — Design Changes: Formal evaluation requirement**
Current Section 16 (Design Changes) addresses major changes but lacks a clear requirement that ALL design changes (including those from suppliers per CAPA003) be formally evaluated under design change controls with documented determination of required V&V activities.
- Add to Section 16 a subsection establishing that ALL design changes, regardless of perceived magnitude, must be formally evaluated to determine: (a) whether a formal design change control (DCO) is required; (b) what V&V activities, if any, are required; and (c) the regulatory impact of the change. This evaluation must be documented.
- Provide draft language.

**Gap 2 — Design Project Planning: Minimum planning requirements**
Current Section 8 (Design Project Planning / 1B) states that a formalized design project plan is required but does not define minimum required content for planning documents.
- Add specific minimum planning requirements: the plan must include at minimum identification of required design review stages, V&V activities, design transfer responsibilities, and DHF deliverables for each phase.
- Provide draft language.

**Gap 3 — Project Plan Change Control**
Section 8 currently states plan status is updated as the project evolves with no formal change control requirement for plan modifications.
- Add a subsection requiring that significant changes to an approved project plan be documented, reviewed, and approved via DCO or equivalent change control mechanism, with rationale recorded.
- Provide draft language.

**Gap 4 — Conflict Resolution Authority**
No section currently addresses who resolves conflicts in design requirements or design input interpretation.
- Add a subsection to Section 10 (User Needs and Design Inputs) establishing that design requirement conflicts are resolved by documented functional review; final resolution authority rests with QA management with documented rationale.
- Provide draft language.

**Gap 5 — Design Outputs: Formal control requirement**
Section 11 (Design Outputs / Section 4 in the SOP) describes typical design output deliverables but does not explicitly require that design outputs be formally controlled.
- Add explicit language requiring design output documents to be released as controlled documents through the DCO process before use in V&V, manufacturing, packaging, labeling, or servicing activities.
- Provide draft language.

**Gap 6 — DHF Work Product Capture Criteria**
No section currently defines when preliminary or exploratory work product must be captured in the DHF vs. remaining as informal working documents.
- Add a subsection defining the criteria for when work product transitions from exploratory/preliminary to DHF-required controlled status. At minimum: any document that informs a design decision, supports a V&V activity, or constitutes a design input, output, review, or change record must be DHF-controlled.
- Provide draft language.

**Gap 7 — V&V Planning: Mandatory, not optional**
Section 12 (Design Verification and Validation) describes V&V activities but uses language that implies V&V planning scope is discretionary ("may include," project scope dependent).
- Modify this section to explicitly require that a V&V plan be established for all design projects. The V&V plan must formally identify all required verification and validation activities; discretionary omission of V&V without documented justification is not permitted.
- Provide draft language.

**Gap 8 — Production-Equivalent Unit Criteria for Validation**
Current Section 12 requires validation on "initial production units or representative test units" but does not define criteria or methodology for establishing equivalence when using representative units.
- Add a subsection defining minimum criteria for establishing that test units are representative of production units for validation purposes, and requiring that this equivalence be documented and approved.
- Provide draft language.

**Gap 9 — Design Transfer via Checklist vs. Final Design Review**
Current Section 14 (Design Transfer) does not explicitly prohibit or condition design transfer sign-off via checklist in lieu of a final design review. The procedure allows transfer without confirming that formal design review requirements have been incorporated.
- Clarify that the design transfer process must confirm that at least one formal design review (as required by Section 16 / Section 8 Design Review) has been conducted and documented in the DHF prior to design transfer. A transfer checklist may supplement but may not substitute for a required design review.
- Provide draft language.

**Important cross-reference note:** QM.SLQ004 Rev C is also a CAPA003 deliverable. Read the CAPA003 file at `docs/QMS-Readable-Texts/20-QMSInProcess/CAPA003/CAPA 003-2025.md` and the CAPA003 redline at `docs/QMS-Readable-Texts/20-QMSInProcess/CAPA003/QM.SLQ004 A Design Control Program SOP_RedLineV1.md` to understand what changes CAPA003 already requires for QM.SLQ004. The DCO092 Rev C should incorporate CAPA003 corrective actions **and** IA-2025 mNC #1 **and** the FileHold → Silq eQMS transition, all in a single revision. Your editing guide must clearly delineate all three sets of changes and note which changes originate from which requirement source.

**Form FM1-QM.SLQ004 (Design Project Scope Form):**
- Read current form at: `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ004 A Design Project Scope Form.md`
- Identify any FileHold references
- Based on mNC #1 Gap 3 (project plan change control) and Gap 9 (V&V planning), determine if the scope form should be updated to include fields that facilitate formal V&V determination and project plan change tracking

---

## DCO092 STRUCTURE GUIDANCE

Your editing guide should also include a section specifying the DCO092 document table (for use on FM1-QM.SLQ001 Rev B, the updated DCO form from DCO091). Include:

| Document Title | Document Number | Current Rev | Target Rev | Primary Change Drivers |
|---|---|---|---|---|
| Employee Training SOP | QM.SLQ003 | B | C | DC.SLQ002 EDMS Transition; OFI #7 (training effectiveness language); OFI #8 (regulatory refs) |
| Employee Training Program Form | FM1-QM.SLQ003 | A | B (if changes needed) | DC.SLQ002 EDMS Transition |
| Employee Training Record Form | FM2-QM.SLQ003 | B | C (if changes needed) | DC.SLQ002 EDMS Transition |
| Internal Audits SOP | QM.SLQ017 | A | B | DC.SLQ002 EDMS Transition; OFI #8 |
| Internal Audit Schedule Form | FM1-QM.SLQ017 | B | C (if changes needed) | DC.SLQ002 EDMS Transition |
| Internal Audit Checklist | FM2-QM.SLQ017 | A | B (if changes needed) | DC.SLQ002 EDMS Transition |
| Internal Audit Final Report Form | FM3-QM.SLQ017 | A | B (if changes needed) | DC.SLQ002 EDMS Transition |
| Certificate of Internal Audit Form | FM4-QM.SLQ017 | A | B (if changes needed) | DC.SLQ002 EDMS Transition |
| Auditor Qualification Record | FM5-QM.SLQ017 | A | B (if changes needed) | DC.SLQ002 EDMS Transition |
| Purchasing Controls SOP | QM.SLQ020 | D | E | DC.SLQ002 EDMS Transition; mNC #5 (mandatory supplier change notification); OFI #8 |
| Purchase Order Form | FM1-QM.SLQ020 | B | C (if changes needed) | DC.SLQ002 EDMS Transition; mNC #5 |
| Sales Order SOP | QM.SLQ036 | E | F | DC.SLQ002 EDMS Transition; OFI #8 |
| Sales Order Form | FM1-QM.SLQ036 | A | B (if changes needed) | DC.SLQ002 EDMS Transition |
| Supplier Quality Assurance SOP | QM.SLQ015 | B | C | DC.SLQ002 EDMS Transition; mNC #4 (risk-based frequencies); OFI #4 (self-assessment justification); OFI #8 |
| Supplier Assessment Schedule Form | FM7-QM.SLQ015 | A | B (if changes needed) | mNC #4 risk basis column |
| Design Control Program SOP | QM.SLQ004 | B | C | DC.SLQ002 EDMS Transition; mNC #1 (nine design control gaps); CAPA003 corrective actions; OFI #8 |
| Design Project Scope Form | FM1-QM.SLQ004 | A | B (if changes needed) | mNC #1 V&V determination; DC.SLQ002 |

For any associated forms where no changes are required after reading the current form content, note this explicitly in the DCO table with "No revision required."

---

## WHAT YOUR EDITING GUIDE MUST CONTAIN

For each of the six SOPs and all associated forms, provide a dedicated section with:

### Section Format for Each Document

```
## [Document Number] [Document Title] (Rev [X] → Rev [Y])

### Summary of Changes Required
[One paragraph overview of total change scope]

### 1. FileHold Reference Replacements
For each FileHold reference:
- **Location:** [Section number and name]
- **Current text (verbatim):** "[exact current text]"
- **Replace with:** "[exact new text]"
- **Notes:** [Any special considerations]

### 2. Audit Compliance Edits
For each mNC/OFI:
- **Finding:** [mNC #X or OFI #X — brief description]
- **Location:** [Section number and name]
- **Current text (verbatim):** "[exact current text, or 'No current text — addition required']"
- **Required change:** [Exact new language, or detailed description of addition]
- **Regulatory basis:** [ISO 13485:2016 clause, 21 CFR 820 section, etc.]

### 3. Regulatory Reference Updates (OFI #8)
For each regulatory reference:
- **Location:** [Section number and name]
- **Current text:** "[current]"
- **Replace with:** "[updated]"

### 4. Definition Section Updates
- Remove "FileHold" definition
- Add "Silq eQMS" definition (standard text from Phase 1A)
- Update "QSR" to "QMSR" if present

### 5. Associated Forms
For each associated form, after reading the current form content:
- [Either specify required changes, or state "No revision required"]
```

---

## HOW TO BEGIN

1. Read all six SOP readable texts listed above from the `docs/QMS-Readable-Texts/01-QM-Documents/` folder.
2. Read all associated form readable texts from `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/`.
3. Read the CAPA003 file and redline for QM.SLQ004 context: `docs/QMS-Readable-Texts/20-QMSInProcess/CAPA003/`.
4. Read the full IA-2025 Final Report: `docs/QMS-Readable-Texts/20-QMSInProcess/CAPA004/IA-2025 Final Report Readable.md`.
5. Read QM.SLQ001 Rev B at `docs/QMS-Readable-Texts/20-QMSInProcess/DCO091/QM.SLQ001 B Document Control SOP.md` to understand the established Phase 1A Silq eQMS language you must match.
6. Create the folder `docs/DCO092/` if it does not exist.
7. Write your complete editing guide to `docs/DCO092/DCO092_PHASE1B_EDITING_GUIDE.md`.

The editing guide should be thorough, precise, and immediately actionable — the document originator should be able to open each SOP in Word and make every required change directly from your guide without ambiguity. Quote verbatim current text for every change so the originator can find the exact location. Provide complete verbatim replacement text for every substitution.

---

## QUALITY EXPECTATIONS

- Every FileHold reference in every document must be identified and replaced. Do not miss any.
- Audit compliance language must address the specific regulatory gap identified, not just make cosmetic changes. For mNC #1 (QM.SLQ004), this means nine substantive procedural additions.
- New Silq eQMS storage location language must specify which Admin Docs library and appropriate subfolder for each document type.
- QMSR regulatory reference updates must be consistent and complete across all documents.
- For QM.SLQ004, you must integrate CAPA003 corrective actions, IA-2025 mNC #1 changes, and FileHold transition changes coherently — they must not conflict.
- The guide must be detailed enough that a reviewer can assess the adequacy of the proposed changes for regulatory compliance purposes.

---

*This prompt was prepared by the QMS management agent on May 28, 2026. All source documents referenced are in the SilqQMS project folder at `c:\Users\Ethan\OneDrive\Desktop\SilqQMS`.*
