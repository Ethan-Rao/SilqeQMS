# DCO096 — QM.SLQ003 Employee Training SOP Revision

## Instructions to the Change Order Agent

You are a regulatory document specialist preparing an **editing guide** for revising SILQ's Employee Training SOP (QM.SLQ003 Rev B → Rev C). Your deliverable is a complete, section-by-section editing guide formatted in the same style as prior editing guides in this project (e.g., `docs/DCO091/EDITOR_QM_SLQ001_DCO091.md`).

The editing guide is a set of precise written instructions that a human editor can apply directly in Microsoft Word to produce the revised document. Use **FIND** → **REPLACE** blocks, **DELETE** instructions, and **INSERT** blocks with exact proposed language as appropriate. Every change must be unambiguous — the editor should not have to make any independent writing decisions.

At the end of your output, include a **QUESTIONS FOR ETHAN** section listing any items you are uncertain about and need confirmed before the guide is finalized. Do not block on these — produce the complete guide using your best judgment and flag questions separately.

---

## Context

SILQ Medical is a small ISO 13485 / 21 CFR Part 820 medical device company (catheters and related products). The current Employee Training SOP was written for a large organization with a dedicated training department and a legacy document management system (FileHold). It is now operationally unworkable for a 7-person team and must be right-sized.

The company has recently deployed a custom eQMS web platform (Silq eQMS) that handles document control, training assignments, acknowledgment records, and audit trails. All references to "FileHold" must be replaced with "Silq eQMS."

### Team as of the effective date of Rev C

| Name | Title |
|---|---|
| Ethan Rao | Director of R&D, QA, and RA — *Training Coordinator* |
| Brian McVerry | CTO |
| Na He | R&D Scientist |
| Chris Turner | Director of Manufacturing |
| Chuck Greiner | Chief Commercial Officer |
| Tom Downey | CFO / Executive Management |
| Haley Shomo | Administrative Manager |

### Design decisions already approved by management (Ethan Rao, QA)

These are **not** open questions — apply them directly in the editing guide:

1. **Default training type is Read & Acknowledge.** Employees open the document in the Silq eQMS and click Acknowledge. The timestamped acknowledgment record in the eQMS IS the training record. No separate paper or digital training record form is required for Read & Acknowledge training.

2. **DCO signers are automatically trained.** Any person who reviews and approves a DCO is deemed trained on every document revision covered by that DCO, effective on the DCO approval date. The DCO approval record constitutes the training record. No additional acknowledgment assignment is required for DCO approvers.

3. **Interactive training** is retained only for hands-on manufacturing procedures when explicitly required by the DCO originator on the DCO form. When interactive training is required, the trainer notes completion in the eQMS or submits a brief record to Ethan.

4. **Per-document effectiveness evaluations are eliminated.** Effectiveness of training is assessed through a single Annual Effectiveness Review (see Section 10 of the revised SOP below).

5. **Annual Effectiveness Review (new).** Once per calendar year, Ethan prepares a written assessment for each employee. The assessment contains approximately 10 questions drawn from the employee's current training scope and tailored to their role. An 80% pass rate is required. The completed assessment (score, pass/fail, date) is retained as a record in the eQMS or the employee's training folder. Failure triggers targeted review of failed areas and a single re-assessment, also documented.

6. **Annual Quality Policy re-acknowledgment.** Each January, Ethan assigns a Quality Policy re-acknowledgment to all employees in the eQMS. Completion is logged automatically.

7. **Monthly training matrix printouts and monthly discrepancy reports are eliminated.** The training matrix is maintained live in the eQMS. Ethan reviews it at least annually or when job responsibilities change.

8. **Historical records / fresh start.** All current employees will receive fresh training assignments in the eQMS following the effective date of Rev C. Pre-system paper records are acknowledged as an organizational transition and need not be mirrored.

9. **Contractors and consultants.** A contractor or consultant must receive and acknowledge a project-specific training assignment covering the SILQ Quality Policy and any directly relevant procedure(s) for their scope of work within 10 business days of engagement start. No training program form is required for contractors. No effectiveness evaluation is required for contractors.

10. **Training Coordinator is Ethan Rao** in his capacity as Director of QA/RA.

11. **Admin editing rights.** During the initial training alignment phase following Rev C effective date, the Silq eQMS system administrator has full rights to create, edit, and backdate training assignments on behalf of any user to support the transition. This authority is noted in the SOP and expires once initial alignment is confirmed complete by Ethan.

12. **FM2-QM.SLQ003 (Employee Training Record Form) is retired.** The eQMS acknowledgment record replaces it. Update the Associated Forms section accordingly and note the retirement.

13. **FM1-QM.SLQ003 (Employee Training Program Form) is retired** and replaced by the training matrix maintained in the eQMS and documented in Appendix 1 of the revised SOP.

---

## Regulatory baseline to maintain

The revised SOP must remain fully compliant with:

- **ISO 13485:2016 § 6.2** — Human Resources: determine necessary competence; take actions to achieve competence; evaluate effectiveness of actions taken; ensure awareness; maintain records.
- **21 CFR Part 820.25** (QS/MDR 2024, formerly 21 CFR 820.25 QSR) — Personnel: training to perform assigned responsibilities; understanding of adverse events/device defects; maintenance of records.

The Annual Effectiveness Review (decision 5 above) satisfies the "evaluate effectiveness" requirement of ISO 13485 §6.2 on a consolidated annual basis rather than per-document. This is compliant provided it is documented and failures trigger retraining.

The DCO signer auto-qualification (decision 2) is consistent with the existing provision in QM.SLQ003 Rev B (Section 10 — "Document Originator — individual who created the document (and is deemed trained)"), extended to all DCO approvers.

---

## Proposed section-by-section changes

Use these as the basis for your editing guide instructions. Produce exact replacement text for each section.

### Purpose (Section 1)

**Goal:** Shorten to 2–3 sentences. Remove sub-bullets listing process steps (these will be reflected in the procedure sections). Remove reference to the "formal training system" framing. Update eQMS reference.

**Retain:** The dual regulatory citations (ISO 13485:2016 §6.2 and 21 CFR Part 820 §820.25).

**Proposed replacement language:**

> This Standard Operating Procedure defines SILQ's process for identifying training requirements, providing training to personnel performing activities affecting product quality or the quality management system, documenting training completion, and evaluating training effectiveness. This procedure is structured to comply with ISO 13485:2016 § 6.2 and 21 CFR Part 820 § 820.25. Training records are maintained within the Silq eQMS electronic quality management system.

### Scope (Section 2)

No substantive change. Update the contractor/consultant language to reflect the simplified contractor requirements (10-business-day acknowledgment window; Quality Policy + relevant procedures).

### Documents (Section 3)

**Reference Documents:** Retain QM.SLQ001 and QM.SLQ014 (updated to current revision). Remove FileHold-specific references if any remain. Remove the stand-alone ISO 13485 and 21 CFR 820 bibliography entries (these are cited in Purpose; their repetition here is unnecessary for a lean SOP — mark this as a question for Ethan if he prefers to keep them).

**Associated Forms:**
- **RETIRE** FM2-QM.SLQ003 — Employee Training Record Form. Add a note: "Retired Rev C — replaced by Silq eQMS acknowledgment record."
- **RETIRE** FM1-QM.SLQ003 — Employee Training Program Form. Add a note: "Retired Rev C — replaced by the Training Matrix in Appendix 1 of this SOP."
- The SOP now references **Appendix 1 — Training Matrix** (internal to this SOP document, not a separate form).

### Definitions (Section 4)

**Delete** the "FileHold" definition entirely.

**Update** "Employee Training Program":
> A role-specific list of controlled documents and procedures for which an employee is required to complete and maintain training. The current Training Matrix (Appendix 1) defines training requirements by role.

**Update** "Employee Training Record":
> The timestamped acknowledgment record generated in the Silq eQMS when an employee completes a training assignment, or the DCO approval record when a DCO approver is auto-qualified. For interactive training, a brief written record is submitted to the Training Coordinator and retained in the eQMS.

**Add** "Annual Effectiveness Review":
> A written assessment administered by the Training Coordinator once per calendar year to verify employee comprehension across their current training scope. The assessment contains approximately 10 role-relevant questions; a score of 80% or above constitutes a pass. Results are documented and retained.

**Update** "Trainer":
> An individual who possesses appropriate knowledge of the subject matter and has been approved by the Training Coordinator to conduct interactive training. Document originators and DCO approvers are considered trained and may act as trainers for documents they have originated or approved.

**Update** "Training Coordinator":
> Ethan Rao, Director of R&D, QA, and RA, in his capacity as the designated Quality Assurance lead. The Training Coordinator is responsible for maintaining the training matrix, creating training assignments in the eQMS, administering the Annual Effectiveness Review, and ensuring training records are complete.

**Delete** "Employee Number" and "Trainer" definition variants that reference FileHold sign-off sheet windows.

### Responsibilities (Section 5)

**Replace the entire Responsibilities section** with the following:

> **5.1** Ethan Rao (Training Coordinator) is responsible for: maintaining the training matrix (Appendix 1); creating and managing training assignments in the Silq eQMS; administering the Annual Effectiveness Review; ensuring training records are accurate and complete; and updating training requirements when job responsibilities or controlled documents change.
>
> **5.2** Department management (each employee's functional manager) is responsible for ensuring their direct reports complete assigned training within specified timeframes and for notifying the Training Coordinator when an employee's responsibilities change.
>
> **5.3** All employees are responsible for completing training assignments in the Silq eQMS by the specified due dates; passing the Annual Effectiveness Review; asking for clarification when training material is not understood; and refraining from performing tasks for which they have not yet completed training unless supervised by a trained individual.
>
> **5.4** During the initial training alignment period following the effective date of this revision, the Silq eQMS system administrator has full authority to create, modify, and backdate training assignments on behalf of any user to support organizational transition. This authority is limited to the initial alignment period, which concludes when Ethan Rao confirms alignment is complete in writing (an email or eQMS note is sufficient).
>
> **5.5** Contractors and consultants are responsible for completing their project-specific onboarding training assignment within 10 business days of engagement start.

### Procedure: Training Matrix (new Section 6 — replaces former Section 9)

> **6.1** The SILQ Training Matrix defines, by role, the controlled documents and procedures for which each employee is required to maintain current training. The current Training Matrix is maintained in Appendix 1 of this SOP.
>
> **6.2** The Training Coordinator reviews and updates the Training Matrix at minimum annually or whenever: a new controlled document is released; an employee's job responsibilities change; a new employee joins the organization; or an employee's role is changed.
>
> **6.3** The Training Matrix is the authoritative source for determining training requirements. Individual employee training programs are derived from it and maintained within the Silq eQMS training module.

### Procedure: Training Assignment and Acknowledgment (new Section 7 — replaces former Sections 7, 10, 11)

> **7.1** The Training Coordinator creates training assignments in the Silq eQMS for each employee based on the Training Matrix and any additional requirements specified on DCO forms.
>
> **7.2** The default training type for all QMS document training is **Read and Acknowledge**. The employee opens the linked document or document revision in the Silq eQMS, reads it, and clicks Acknowledge. The system records the employee name, document revision, and timestamp. This acknowledgment record constitutes the training record; no separate form is required.
>
> **7.3** **Interactive training** is required only when explicitly designated on the DCO form by the DCO originator, or when directed by the Training Coordinator for hands-on manufacturing or laboratory procedures. For interactive training: the trainer reviews the material with the trainee; upon completion, the trainer records completion in the Silq eQMS (if system access permits) or submits a brief written note (employee name, document, date, trainer name) to the Training Coordinator, who uploads it as the training record.
>
> **7.4** Employees may not independently perform tasks governed by a procedure for which they have not completed training, unless supervised by a currently trained individual. The supervising trainer countersigns any associated quality records.
>
> **7.5** Training assignments carry a default due date of 30 days from the assignment date unless a different deadline is specified on the DCO form or by the Training Coordinator.
>
> **7.6** The Training Coordinator may perform training to documents not listed in an employee's training profile whenever operational needs require it. Such training follows the standard Read and Acknowledge process and is logged in the eQMS.

### Procedure: DCO Signer Auto-Qualification (new Section 8)

> **8.1** Any employee who reviews and approves a Document Change Order (DCO) in the Silq eQMS is automatically deemed trained on every controlled document revision covered by that DCO. This qualification takes effect on the DCO approval date.
>
> **8.2** The DCO approval record in the Silq eQMS serves as the training record for DCO-approver qualification. The Training Coordinator is not required to create a separate training assignment for DCO approvers on documents covered by that DCO.
>
> **8.3** DCO originator qualification: consistent with prior versions of this SOP, a document originator is deemed trained on the document they authored.

### Procedure: Retraining on Document Changes (new Section 9 — replaces former Section 8)

> **9.1** When a controlled document is revised, the DCO originator specifies the training requirements (affected roles, training type) on the DCO form. The Training Coordinator creates the corresponding training assignments in the Silq eQMS for the affected employee population per the Training Matrix.
>
> **9.2** Employees listed as DCO approvers on the associated DCO are auto-qualified per Section 8 and do not require a separate retraining assignment.
>
> **9.3** Affected employees must complete retraining (acknowledge the new revision) within the timeframe specified on the DCO form. If no timeframe is specified, the default is 30 days from the document's effective date.
>
> **9.4** Ad hoc retraining may be initiated at any time by the Training Coordinator or department management in response to a quality issue, CAPA, or identified knowledge gap.

### Procedure: Annual Quality Policy Re-Acknowledgment (new Section 10)

> **10.1** In January of each calendar year, the Training Coordinator creates a Read and Acknowledge training assignment for the current revision of the SILQ Quality Policy and assigns it to all active employees.
>
> **10.2** Employees must complete the re-acknowledgment by February 28 of the same year.
>
> **10.3** The eQMS acknowledgment record serves as the annual Quality Policy training record.

### Procedure: Annual Effectiveness Review (new Section 11)

> **11.1** Once per calendar year, the Training Coordinator administers a written Annual Effectiveness Review to each active employee.
>
> **11.2** The review consists of approximately 10 questions drawn from the employee's current training scope (as defined in the Training Matrix, Appendix 1) and tailored to their role and responsibilities. The Training Coordinator prepares the questions; they may be delivered as a printed or electronic document.
>
> **11.3** A score of 80% or above (i.e., 8 of 10 questions correct) constitutes a passing result.
>
> **11.4** The Training Coordinator documents each review: employee name, date of review, score, and pass/fail result. The completed record is uploaded to the employee's training folder in the Silq eQMS.
>
> **11.5** If an employee scores below 80%, the Training Coordinator conducts a brief targeted review of the failed topic areas with the employee and administers a re-assessment. The re-assessment is documented as a separate record. Persistent failure is escalated to department management.
>
> **11.6** The first Annual Effectiveness Review for the current team is to be completed no later than December 31, 2026.

### Procedure: New Employee Onboarding (new Section 12 — replaces portions of former Section 7)

> **12.1** Upon hiring, the Training Coordinator creates training assignments for the new employee in the Silq eQMS, covering: (a) Base Requirements (Quality Policy, Employee Training SOP, Good Documentation Practices SOP, and Quality Manual), and (b) role-specific documents per the Training Matrix.
>
> **12.2** Base Requirements training must be completed within 30 days of the employee's start date.
>
> **12.3** Role-specific training must be completed within 60 days of the employee's start date.
>
> **12.4** New employees who join mid-year are included in the next scheduled Annual Effectiveness Review cycle.
>
> **12.5** Documentation of the employee's qualifications (e.g., resume, credentials) is maintained in the employee's personnel file.

### Procedure: Contractor and Consultant Training (new Section 13)

> **13.1** Prior to or within 10 business days of commencing work for SILQ, each contractor or consultant performing activities that may affect product quality or the quality system must acknowledge the SILQ Quality Policy and any procedures directly relevant to their scope of work.
>
> **13.2** The Training Coordinator creates the appropriate Read and Acknowledge assignments in the Silq eQMS, or provides document copies with a written acknowledgment form if the contractor does not have eQMS access.
>
> **13.3** No Annual Effectiveness Review is required for contractors or consultants.

### Procedure: Training Records and Retrieval (new Section 14 — replaces former Sections 11, 12)

> **14.1** All training records are maintained within the Silq eQMS training module. Records include: document title, document revision, employee name, training type, completion date, and (for effectiveness reviews) score and pass/fail result.
>
> **14.2** Training records are retained in accordance with SILQ's document retention schedule and applicable regulatory requirements.
>
> **14.3** Training records are accessible to authorized users via the Silq eQMS. The Training Coordinator may export records for audit purposes.
>
> **14.4** Monthly matrix printouts and monthly discrepancy reports are not required. The Training Coordinator monitors training compliance on an ongoing basis using eQMS dashboards and reports.

### APPENDIX 1 — Training Matrix

Add a new Appendix 1 at the end of the document. This is a table listing controlled documents by functional category and indicating which roles require training.

**Instructions to the editor:** Insert the following table as Appendix 1 in the Word document. Format as a standard Word table. Use check marks (✓) for required and leave blank (—) for not required.

The proposed Training Matrix is drafted below. **The agent should review the full QMS document list and propose any corrections or additions, and flag these in the QUESTIONS FOR ETHAN section.**

**Legend:**
- **E** = Ethan Rao (QA/RA/R&D Director — trained on all)
- **B** = Brian McVerry (CTO)
- **N** = Na He (R&D Scientist)
- **C** = Chris Turner (Director of Manufacturing)
- **Ch** = Chuck Greiner (CCO)
- **T** = Tom Downey (CFO/Executive Mgmt)
- **H** = Haley Shomo (Administrative Manager)

| Document | Number | E | B | N | C | Ch | T | H |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **BASE — All Employees** | | | | | | | | |
| Quality Policy | QM.SLQ035 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Quality Manual | QM.SLQ027 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Good Documentation Practices SOP | QM.SLQ002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Employee Training SOP | QM.SLQ003 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **QUALITY SYSTEM MANAGEMENT** | | | | | | | | |
| Document Control SOP | QM.SLQ001 | ✓ | — | ✓ | ✓ | — | — | ✓ |
| Electronic Document System WI | QM.SLQ014 | ✓ | — | ✓ | ✓ | — | — | ✓ |
| CAPA SOP | QM.SLQ016 | ✓ | ✓ | — | ✓ | — | ✓ | — |
| Internal Audits SOP | QM.SLQ017 | ✓ | ✓ | — | — | — | ✓ | — |
| Management Review SOP | QM.SLQ018 | ✓ | ✓ | — | — | — | ✓ | — |
| Quality Objectives | QM.SLQ037 | ✓ | ✓ | — | — | — | ✓ | — |
| Quality Planning SOP | QM.SLQ025 | ✓ | ✓ | — | — | — | ✓ | — |
| Managing Regulatory Inspections | QM.SLQ038 | ✓ | ✓ | — | — | — | ✓ | — |
| Protection of Confidential Patient Info | QM.SLQ028 | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| **DESIGN & DEVELOPMENT** | | | | | | | | |
| Design Control Program SOP | QM.SLQ004 | ✓ | ✓ | ✓ | — | — | — | — |
| Design Project Planning SOP | QM.SLQ005 | ✓ | ✓ | ✓ | — | — | — | — |
| Design Input SOP | QM.SLQ006 | ✓ | ✓ | ✓ | — | — | — | — |
| Design Output SOP | QM.SLQ007 | ✓ | ✓ | ✓ | — | — | — | — |
| Design Review SOP | QM.SLQ008 | ✓ | ✓ | ✓ | — | — | — | — |
| Design Verification & Validation SOP | QM.SLQ009 | ✓ | ✓ | ✓ | — | — | — | — |
| Design Transfer SOP | QM.SLQ010 | ✓ | ✓ | ✓ | ✓ | — | — | — |
| Risk Management SOP | QM.SLQ012 | ✓ | ✓ | ✓ | — | — | — | — |
| Risk Analysis SOP | QM.SLQ013 | ✓ | ✓ | ✓ | — | — | — | — |
| Statistical Techniques WI | QM.SLQ011 | ✓ | — | ✓ | — | — | — | — |
| Software Validation SOP | QM.SLQ032 | ✓ | ✓ | ✓ | — | — | — | — |
| Post-Market Surveillance SOP | QM.SLQ033 | ✓ | ✓ | ✓ | — | — | — | — |
| Device Master Record SOP | QM.SLQ048 | ✓ | — | ✓ | ✓ | — | — | — |
| DHR Review and Approval SOP | QM.SLQ029 | ✓ | — | — | ✓ | — | — | — |
| Process Validation SOP | QM.SLQ047 | ✓ | — | ✓ | ✓ | — | — | — |
| **MANUFACTURING & OPERATIONS** | | | | | | | | |
| Identification and Traceability SOP | QM.SLQ019 | ✓ | — | — | ✓ | — | — | — |
| Nonconforming Materials SOP | QM.SLQ040 | ✓ | — | — | ✓ | — | — | — |
| Receiving Inspection SOP | QM.SLQ039 | ✓ | — | — | ✓ | — | — | — |
| Work Order SOP | QM.SLQ043 | ✓ | — | — | ✓ | — | — | — |
| Receiving SOP | QM.SLQ045 | ✓ | — | — | ✓ | — | — | ✓ |
| Shipping SOP | QM.SLQ046 | ✓ | — | — | ✓ | ✓ | — | — |
| Workstation Practices SOP | QM.SLQ049 | ✓ | — | — | ✓ | — | — | — |
| Calibration and Preventive Maintenance SOP | QM.SLQ050 | ✓ | — | — | ✓ | — | — | — |
| Environmental Monitoring SOP | QM.SLQ051 | ✓ | — | — | ✓ | — | — | — |
| Part Number Assignment WI | QM.SLQ026 | ✓ | — | ✓ | ✓ | — | — | — |
| **SUPPLIER & PURCHASING** | | | | | | | | |
| Supplier Quality Assurance SOP | QM.SLQ015 | ✓ | — | — | ✓ | — | — | ✓ |
| Purchasing Controls SOP | QM.SLQ020 | ✓ | — | — | ✓ | — | ✓ | ✓ |
| **COMMERCIAL & COMPLAINTS** | | | | | | | | |
| Sales Order SOP | QM.SLQ036 | ✓ | — | — | — | ✓ | — | ✓ |
| Product Complaint System SOP | QM.SLQ021 | ✓ | — | — | — | ✓ | — | — |
| Medical Device Reporting SOP | QM.SLQ022 | ✓ | — | — | — | ✓ | — | — |
| eMDR Submission Work Instruction | QM.SLQ023 | ✓ | — | — | — | — | — | — |
| Advisory Notices and Recalls SOP | QM.SLQ030 | ✓ | ✓ | — | — | ✓ | — | — |

**Note to agent:** The table above covers documents found in `docs/QMS-Readable-Texts/01-QM-Documents/`. Verify this list against the eQMS document register and flag any released QMS documents that are missing from the matrix.

---

## Sections to DELETE entirely from Rev B

The following sections of QM.SLQ003 Rev B should be **deleted** in Rev C. Include explicit DELETE instructions in the editing guide for each:

| Section Title | Reason |
|---|---|
| Section 9 — Procedure: Completing Employee Training Program Forms | Replaced by eQMS training matrix; forms retired |
| Section 10 — Procedure: Completing the Employee Training Record | Replaced by eQMS acknowledgment record |
| Section 11 — Retrieval of Training Programs and Training Records | Replaced by Section 14 of Rev C |
| Section 12 (if numbered) — Procedure: Training Coordinator monthly matrix/discrepancy reporting | Replaced by eQMS; monthly printing eliminated |

---

## Sections to RETAIN with targeted edits

| Section | Change |
|---|---|
| All FileHold references | Replace "FileHold" with "Silq eQMS" throughout |
| "Employee file folder within FileHold" | Replace with "employee training folder in Silq eQMS" |
| "Scan and import" language | Delete wherever it appears (not applicable to eQMS) |
| Section 7.2 (Completion on Training Record) | Remove "Sign off on training records may be done electronically in FileHold or manually" — replaced by Section 7 of Rev C |
| Section 8.1 (Retraining) — "document administrator will determine from DCO form if retraining is required" | Update to say "Training Coordinator creates assignments per Section 9 of this SOP" |
| Section 7.10 — Effectiveness evaluations per-document | **Delete** this subsection; replace with cross-reference to Section 11 (Annual Effectiveness Review) |

---

## DCO form fields (for the agent to draft the DCO record)

| Field | Value |
|---|---|
| DCO Number | DCO096 (confirm against current DCO log — last confirmed was DCO089; DCO090–095 may have been issued during the eQMS transition) |
| Document Affected | QM.SLQ003 — Employee Training SOP |
| Current Revision | B |
| Proposed Revision | C |
| Reason for Change | Right-size training system for a 7-person team; transition from FileHold to Silq eQMS; eliminate manual forms and monthly printouts; add DCO signer auto-qualification; add Annual Effectiveness Review; revise training matrix to reflect current roles and responsibilities |
| Training Required | All employees — Read and Acknowledge this revised SOP; no effectiveness evaluation required for this DCO (the annual review covers it) |
| Originator | Ethan Rao |

---

## Questions for Ethan (agent must append these at the end of the editing guide)

The agent should confirm:

1. **Training Matrix accuracy:** Is the proposed Appendix 1 training matrix correct for each role? Specifically:
   - Should Brian (CTO) be included on any manufacturing or operations SOPs given his technical oversight role?
   - Should Tom (CFO) be added to Purchasing Controls (QM.SLQ020) given financial approval of POs?
   - Should Na He (R&D Scientist) be included on CAPA (QM.SLQ016) given R&D involvement in product quality?
   - Is Haley's scope correct (Receiving SOP, Purchasing, Sales Order, Document Control, Training SOP)?

2. **Reference documents:** Should the ISO 13485 and 21 CFR 820 bibliography entries be retained in Section 3 (Documents) or removed from the body of the SOP now that they are cited in the Purpose?

3. **Section numbering:** The current SOP uses a section-header numbering system rather than explicit section numbers in the body. Confirm: should Rev C use explicit numbered sections (1.0, 2.0, etc.) matching the structure above, or should the heading-only style be preserved?

4. **DCO number:** Confirm the next available DCO number. The last logged form was DCO089; however, DCO090–095 may have been issued since. Please check the Silq DCO Log and confirm.

5. **Annual Effectiveness Review timing:** The SOP proposes the first review be completed by December 31, 2026. Is this acceptable, or should a specific earlier target date be set?

6. **FM1 / FM2 retirement timing:** Should the two forms be formally retired as part of this DCO (listed on the DCO form as "Retired"), or simply noted as superseded in the SOP text?

7. **Organization Chart cross-reference:** QM.SLQ034 (Organization Chart) will need updating when the training matrix lists by role. Should that be included as a second document on DCO096, or handled separately?

---

## Output format reminder

Your output should be a complete editing guide document saved as:

`docs/DCO096/EDITOR_QM_SLQ003_REV_C_DCO096.md`

Structure it as:
- **Part A** — Deletions (exact section text to delete)
- **Part B** — Replacements (FIND → REPLACE blocks, section by section)
- **Part C** — Insertions (new sections with exact proposed text)
- **Part D** — Appendix 1 (Training Matrix table)
- **Part E** — Verification checklist (things the editor should confirm after editing)
- **Part F** — DCO096 record fields
- **Part G** — Questions for Ethan
