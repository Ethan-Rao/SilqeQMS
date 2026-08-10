# DCO095 - Design Control Redesign: Editing Guide

Prepared by: QMS management agent
Date: June 30, 2026
For use by: Ethan Rao (QA/RA/R&D), SILQ Technologies
Basis: DCO095_DESIGN_CONTROL_REDESIGN_OUTLINE.md (approved June 30, 2026) and all source documents listed in the agent prompt

This guide tells you exactly what to create, edit, and obsolete to implement DCO095. It is execution-ready: every section contains the literal text to paste into Word, preceded by a short formatting note. No asterisk characters are used anywhere in this guide.

---

## SECTION 4.1 - Package Overview and Conventions

### 4.1.1 Scope of DCO095

DCO095 replaces SILQ's seven-SOP design control system (QM.SLQ004 through QM.SLQ010 and their 13 associated forms and templates) with a single, consolidated Design Control SOP (QM.SLQ052, Revision A) and a lean set of seven new forms and templates. The package also revises every other QMS document that references the superseded SOPs. DCO095 closes IA-2025 mNC 1 (nine sub-issues), addresses IA-2025 mNC 3 and OFI 2 through design-risk integration, addresses IA-2025 OFI 10 through risk-design linkage, closes CAPA 004-2025 Action 5, and completes the design-control corrective actions required by CAPA 2025-003 (FDA 483 Observation 2). DCO095 does not include employee training delivery, FileHold-to-eQMS data migration, transition of in-flight design projects DC.SLQ001 or DC.SLQ002, or any non-design Quality Plan items.

### 4.1.2 Formatting Conventions

Each edit in this guide is presented as follows:

- Formatting note (plain text, not in a paste block): the Word style or numbering scheme to apply.
- Paste block (indented, fenced with ---PASTE START--- and ---PASTE END--- markers): the exact text to paste into the Word document. The paste block contains only the literal document text. No markdown hash headings, no asterisks, and no markdown formatting appear inside any paste block.
- Where a figure is needed, an IMAGE-GENERATION INSTRUCTION BLOCK is provided. This is a self-contained paragraph the human can copy and paste to an image-generation agent.

### 4.1.3 Package Table

The table below lists every document in DCO095 with its action and the current revision being superseded or revised.

Note: DCO094 is being processed concurrently with DCO095. Before executing DCO095, confirm the current released revision of QM.SLQ027 (either Rev E or Rev F, depending on whether DCO094 has been released) and adjust the "Current Revision" column accordingly. The same applies to QM.SLQ011 (Rev A or B) and QM.SLQ047 (Rev A or B). This guide shows the pre-DCO094 revision as the base; add one letter if DCO094 has already gone effective.

Document Title | Document Number | Current Rev | DCO095 Action | New Rev
QM.SLQ052 Design Control SOP | QM.SLQ052 | (New) | New | A
FM1-QM.SLQ052 Design Project Scope and Plan | FM1-QM.SLQ052 | (New) | New | A
FM2-QM.SLQ052 Design Change Assessment | FM2-QM.SLQ052 | (New) | New | A
FM3-QM.SLQ052 Design Review Record | FM3-QM.SLQ052 | (New) | New | A
FM4-QM.SLQ052 Design V&V Deviation | FM4-QM.SLQ052 | (New) | New | A
TMP1-QM.SLQ052 Design Input, Output, and Traceability Matrix | TMP1-QM.SLQ052 | (New) | New | A
TMP2-QM.SLQ052 V&V Plan, Protocol, and Report | TMP2-QM.SLQ052 | (New) | New | A
TMP3-QM.SLQ052 Design Transfer Checklist | TMP3-QM.SLQ052 | (New) | New | A
Quality Manual | QM.SLQ027 | E (or F) | Revise | F (or G)
Purchasing Controls SOP | QM.SLQ020 | D | Revise | E
Risk Analysis SOP | QM.SLQ013 | B | Revise | C
Risk Management SOP | QM.SLQ012 | B | Revise | C
Process Validation SOP | QM.SLQ047 | A (or B) | Revise | B (or C)
Quality Planning SOP | QM.SLQ025 | A | Revise | B
Statistical Techniques WI | QM.SLQ011 | A (or B) | Revise | B (or C)
DMR SOP | QM.SLQ048 | A (or B) | Revise | B (or C)
DHR SOP | QM.SLQ029 | A (or B) | Revise | B (or C)
Supplier QA SOP | QM.SLQ015 | (current) | Verify/No change | (same)
CAPA SOP | QM.SLQ016 | (current) | Verify/No change | (same)
Mgmt Review Minutes Form | FM1-QM.SLQ018 | (current) | Revise | next
QM Document Register | (register) | (current) | Update entries | (current)
QM.SLQ004 Design Control Program SOP | QM.SLQ004 | B | Obsolete | (Obsolete)
QM.SLQ005 Design Project Planning SOP | QM.SLQ005 | B | Obsolete | (Obsolete)
QM.SLQ006 Design Input SOP | QM.SLQ006 | A | Obsolete | (Obsolete)
QM.SLQ007 Design Output SOP | QM.SLQ007 | A | Obsolete | (Obsolete)
QM.SLQ008 Design Review SOP | QM.SLQ008 | A | Obsolete | (Obsolete)
QM.SLQ009 Design V&V SOP | QM.SLQ009 | A | Obsolete | (Obsolete)
QM.SLQ010 Design Transfer SOP | QM.SLQ010 | A | Obsolete | (Obsolete)
FM1-QM.SLQ004 Design Project Scope Form | FM1-QM.SLQ004 | A | Obsolete | (Obsolete)
TMP1-QM.SLQ005 Design Project Plan Template | TMP1-QM.SLQ005 | A | Obsolete | (Obsolete)
TMP1-QM.SLQ006 User Needs Template | TMP1-QM.SLQ006 | A | Obsolete | (Obsolete)
TMP2-QM.SLQ006 Product Requirements Template | TMP2-QM.SLQ006 | A | Obsolete | (Obsolete)
TMP1-QM.SLQ007 Source Control Spec Template | TMP1-QM.SLQ007 | A | Obsolete | (Obsolete)
TMP2-QM.SLQ007 Design Input-Output Matrix Template | TMP2-QM.SLQ007 | A | Obsolete | (Obsolete)
FM1-QM.SLQ008 Design Review Minutes Form | FM1-QM.SLQ008 | A | Obsolete | (Obsolete)
FM1-QM.SLQ009 Design V&V Deviation Form | FM1-QM.SLQ009 | A | Obsolete | (Obsolete)
TMP1-QM.SLQ009 V&V Test Plan Template | TMP1-QM.SLQ009 | A | Obsolete | (Obsolete)
TMP2-QM.SLQ009 V&V Protocol Template | TMP2-QM.SLQ009 | A | Obsolete | (Obsolete)
TMP3-QM.SLQ009 V&V Final Report Template | TMP3-QM.SLQ009 | A | Obsolete | (Obsolete)
TMP1-QM.SLQ010 Clinical Transfer Checklist Template | TMP1-QM.SLQ010 | A | Obsolete | (Obsolete)
TMP2-QM.SLQ010 Design Transfer Checklist Template | TMP2-QM.SLQ010 | A | Obsolete | (Obsolete)

---

## SECTION 4.2 - New Document: QM.SLQ052 Design Control SOP, Revision A

### Instructions to Ethan

Create a new Word document using the standard SILQ SOP template. The document header must show:
- Document Number: QM.SLQ052
- Title: Design Control
- Revision: A
- Page count and standard header/footer per the SILQ document template

Apply heading styles as noted before each paste block. Every section heading inside a paste block is presented in plain text; apply the appropriate Word Heading style after pasting.

---

### Section 1 of QM.SLQ052: Purpose

Formatting note: Apply Word style "Heading 1" to the word "Purpose" and body text (Normal style) to the paragraph below.

---PASTE START---
Purpose

The purpose of this standard operating procedure is to define the complete design control program at SILQ Technologies, including all requirements for the planning, execution, review, verification, validation, transfer, and change control of medical device designs. This SOP consolidates the requirements previously distributed across QM.SLQ004 through QM.SLQ010 into a single, streamlined procedure applicable to new product development, design changes to released devices, and supplier- or CMO-initiated modifications.

This procedure is structured around three defined design pathways (Pathway A: Full Development; Pathway B: Design Change; Pathway C: Supplier or CMO-Initiated Change) and is designed to close IA-2025 mNC 1 (nine sub-issues), to implement the mandatory supplier-change trigger required by CAPA 2025-003 and the 2026 Quality Plan, and to establish the Medical Device File framework under ISO 13485:2016 clause 4.2.3.
---PASTE END---

---

### Section 2 of QM.SLQ052: Scope

Formatting note: Apply "Heading 1" to "Scope." Apply "Heading 2" to each sub-heading (2.1, 2.2, 2.3). Use Normal style for body paragraphs.

---PASTE START---
Scope

2.1 General

This procedure applies to all design and development activities for medical device product lines at SILQ, including:

(a) New products and new generations of existing products intended for commercial distribution or clinical investigation;

(b) Changes to any released device design, regardless of the perceived magnitude of the change;

(c) All modifications to a component, material, process, or labeling initiated by a supplier, contract manufacturer (CMO), or sub-tier supplier that may affect the finished device.

2.2 Subcontractor and CMO Obligations

All design and development activities performed by approved subcontractors, CMOs, or consultants for or in support of SILQ design projects must comply with the requirements defined in this procedure. Where a subcontractor's design control system is deficient or incomplete, the subcontractor shall follow the applicable requirements of QM.SLQ052. SILQ retains ownership and responsibility for all design control records and the Design History File regardless of where design activities are physically performed.

2.3 Exclusions

This procedure does not apply to product development activities that have not yet been classified as a formal design project by SILQ management. Pre-concept feasibility work is excluded until a design project is formally initiated by completion of FM1-QM.SLQ052. In-flight design projects DC.SLQ001 and DC.SLQ002, which were initiated under QM.SLQ004 through QM.SLQ010, shall be completed and closed under those superseded procedures. All new design work initiated on or after the effective date of QM.SLQ052 Revision A shall follow this procedure.
---PASTE END---

---

### Section 3 of QM.SLQ052: References and Standards

Formatting note: Apply "Heading 1" to "References and Standards." List items may be formatted as body text with a hanging indent (Word list style or manual tabs).

---PASTE START---
References and Standards

3.1 Regulatory Requirements

21 CFR Part 820 - Quality Management System Regulation (QMSR), effective February 2, 2026, which incorporates ISO 13485:2016 by reference. Section 820.30 addresses design controls.

21 CFR Part 807, Subpart E - Premarket Notification (510(k)) requirements.

3.2 Standards

ISO 13485:2016 - Medical devices - Quality management systems - Requirements for regulatory purposes. Clause 7.3 governs design and development.

ISO 14971:2019 - Medical devices - Application of risk management to medical devices.

ISO/TR 24971:2020 - Medical devices - Guidance on the application of ISO 14971.

3.3 FDA Guidance

FDA Guidance: Deciding When to Submit a 510(k) for a Change to an Existing Device (October 25, 2017). This guidance governs the regulatory assessment required in FM2-QM.SLQ052 for every change to a released device design.

3.4 Internal SILQ Documents

QM.SLQ001 - Document Control SOP
QM.SLQ012 - Risk Management SOP
QM.SLQ013 - Risk Analysis SOP
QM.SLQ015 - Supplier Quality Assurance SOP
QM.SLQ020 - Purchasing Controls SOP (supplier change notification requirements)
QM.SLQ025 - Quality Planning SOP
QM.SLQ027 - Quality Manual (Medical Device File framework)
QM.SLQ029 - Device History Record (DHR) Review and Approval SOP
QM.SLQ047 - Process Validation SOP
QM.SLQ048 - Device Master Record (DMR) SOP
---PASTE END---

---

### Section 4 of QM.SLQ052: Definitions

Formatting note: Apply "Heading 1" to "Definitions." Apply "Heading 2" to "4.1 Abbreviations and Acronyms" and "4.2 General Definitions." Use a definition list format (term bold, definition normal) for each entry.

---PASTE START---
Definitions

4.1 Abbreviations and Acronyms

BOM: Bill of Materials
CAPA: Corrective and Preventive Action
CMO: Contract Manufacturing Organization
DCA: Design Change Assessment (FM2-QM.SLQ052)
DCO: Document Change Order
DHF: Design History File
DHR: Device History Record
DMR: Device Master Record
MDF: Medical Device File
QMSR: Quality Management System Regulation (21 CFR Part 820, effective February 2, 2026)
QA: Quality Assurance
QMS: Quality Management System
RA: Regulatory Affairs
SOP: Standard Operating Procedure
V&V: Verification and Validation

4.2 General Definitions

Design Change Assessment (DCA): The record used in Pathway B and Pathway C to document the evaluation of any change to a released design, including design impact, risk determination, V&V determination, and regulatory assessment. Controlled as FM2-QM.SLQ052.

Design History File (DHF): A compilation of records that describes the design history of a finished device, maintained in the SILQ eQMS in accordance with this procedure and QM.SLQ027.

Design Input: The physical and performance requirements of the device relating to its intended use, including safety, functional, and regulatory requirements. Design inputs establish the basis for verifying design outputs and validating the device against user needs.

Design Output: The results of each design phase and of the total design effort. The finished design output is the basis for the Device Master Record. Design outputs must be formally controlled in accordance with this procedure.

Design Review: A documented, comprehensive, systematic examination of a design to evaluate the adequacy of design requirements, evaluate the capability of the design to meet those requirements, and identify problems. Gate reviews under Pathway A and change reviews under Pathways B and C are both design reviews for purposes of this definition.

Device Master Record (DMR): Also referred to as the Medical Device File. The compilation of all records containing procedures and specifications for a finished device. DMR requirements are defined in QM.SLQ048.

Document Change Order: The form (FM1-QM.SLQ001) used to add new or revise existing documents in the SILQ document control system. Design changes that result in revised controlled documents are executed through the DCO process per QM.SLQ001.

Gate Review: A formal design review that closes a defined development phase and authorizes progression to the next phase. Gate reviews are closed using FM3-QM.SLQ052 and require an independent reviewer.

Independent Reviewer: An individual who participates in a design review but does not have direct responsibility for the design stage being reviewed. The independent reviewer is identified by Quality Assurance management.

Medical Device File (MDF): The ISO 13485:2016 clause 4.2.3 construct that contains or references all documentation needed to demonstrate conformity of a medical device. At SILQ the MDF is the aggregate of the DHF, DMR, DHR, risk management file, labeling, and product specifications for a given device. See QM.SLQ027 for the MDF framework.

Pathway A: Full Development pathway. Used for new products, new generations, or any change with potential impact on safety or essential performance. Governed by three formal gate reviews.

Pathway B: Design Change pathway. Used for internally initiated changes to a released design that do not meet the criteria for Pathway A. Driven by FM2-QM.SLQ052.

Pathway C: Supplier or CMO-Initiated Change pathway. Mandatory for any notification of a supplier or CMO modification to a component, material, or process affecting the finished device, regardless of perceived significance. Driven by FM2-QM.SLQ052. Pathway C may escalate to Pathway A when the assessment identifies safety or essential performance impact.

Risk Management File: The part of the DHF containing all records produced by risk management activities for a given product, including the risk management plan, hazard analyses, FMEA worksheets, risk management report, and post-production review records. Governed by QM.SLQ012 and QM.SLQ013.

Traceability Matrix: The controlled record (TMP1-QM.SLQ052) that traces design inputs through design outputs to verification and validation activities and risk mitigations.

Validation: Confirmation by examination and provision of objective evidence that the particular product requirements (design inputs) for a specific intended use (user needs) can be consistently fulfilled.

Validation Equivalence: The documented demonstration that test units used for design validation are equivalent to initial production units with respect to materials, configuration, manufacturing method, and any other characteristic that could affect performance or safety.

Verification: Confirmation by examination and provision of objective evidence that specified requirements (design inputs) have been fulfilled by the product design (design outputs).
---PASTE END---

---

### Section 5 of QM.SLQ052: Roles, Responsibilities, and Authorities

Formatting note: Apply "Heading 1" to "Roles, Responsibilities, and Authorities." Apply "Heading 2" to each numbered role (5.1, 5.2, etc.). Use Normal style for body paragraphs.

---PASTE START---
Roles, Responsibilities, and Authorities

5.1 Quality Assurance Management

Quality Assurance management is responsible for ensuring this procedure and all associated forms and templates are followed during design and development activities at SILQ. Quality Assurance management is responsible for identifying independent reviewers for all design reviews, reviewing and approving the V&V determination in FM1-QM.SLQ052 and FM2-QM.SLQ052 when V&V is limited or omitted, and for auditing DHF completeness and retrievability.

5.2 R&D and Engineering Management

R&D and Engineering management is responsible for the technical execution of design and development activities, preparation of design inputs, design outputs, and V&V documentation, and ensuring that the DHF and DMR deliverables are correct and complete at each gate.

5.3 Project Leader

The Project Leader is responsible for coordinating design team activities, maintaining the Design Project Scope and Plan (FM1-QM.SLQ052), communicating roles and responsibilities to the project team, and ensuring that plan revisions are processed through change control per Section 7.4.

5.4 Executive Management

Executive Management is responsible for ensuring that appropriate regulatory approvals are obtained before releasing product for clinical use or commercial distribution, and for resolving conflicts between organizational priorities and quality or regulatory requirements, with documented rationale retained in the DHF.

5.5 Manufacturing Management

Manufacturing management is responsible for ensuring product designs are suitable for manufacture, that the DMR is formally released prior to commercial production, and that process validation activities are completed in accordance with QM.SLQ047.

5.6 Regulatory Affairs

Regulatory Affairs is responsible for conducting the regulatory assessment (Letter-to-File or 510(k) determination) required by FM2-QM.SLQ052 for all changes to released designs, in accordance with the FDA guidance Deciding When to Submit a 510(k) for a Change to an Existing Device.

5.7 Design Input Conflict Resolution Authority

In the event that incomplete, ambiguous, or conflicting design input requirements are identified, the Director of R&D, Quality, and Regulatory Affairs (or designated management representative) has final authority to resolve the conflict. Resolution must be documented in the project DHF with the following elements: (a) a description of the conflict, (b) the resolution decision and its rationale, and (c) traceable approval by the authority and Quality Assurance. All revisions to design input documents arising from conflict resolution are processed through the DCO process per QM.SLQ001.
---PASTE END---

---

### Section 6 of QM.SLQ052: Pathway Selection and Triage

Formatting note: Apply "Heading 1" to "Pathway Selection and Triage." Apply "Heading 2" to each sub-heading. Use Normal style for body paragraphs and a numbered list for the triage checklist.

---PASTE START---
Pathway Selection and Triage

6.1 Triage Requirement

Every design activity at SILQ must be assigned to exactly one pathway before work begins. The pathway assignment is documented in FM1-QM.SLQ052 (Pathway A) or FM2-QM.SLQ052 (Pathways B and C) and must be approved before design work proceeds. Triage results are not overridden informally; any change in pathway requires a revision to the relevant record through the change-control process.

6.2 Triage Checklist

Apply the following checklist in order. Answer each question Yes or No. The first "Yes" answer determines the pathway.

Question 1: Is this a new product, a new generation of an existing product, a new intended use or indication, or a new platform technology?
If Yes: Assign Pathway A.

Question 2: Did a supplier, CMO, sub-tier supplier, or contract service provider communicate any modification to a component, material, process, labeling, or packaging that may affect the finished device?
If Yes: Assign Pathway C immediately, regardless of perceived significance of the change.

Question 3: Does the proposed change have any potential impact on safety, essential performance, sterility, biocompatibility, dimensional fit, materials of construction, or regulatory clearance status?
If Yes: Assign Pathway A.

Question 4: Does the proposed change require new or modified V&V testing, a new regulatory submission, or revision to the DMR in a way that introduces a new hazard or alters risk acceptability?
If Yes: Assign Pathway A.

Question 5: Is the proposed change to a released design, initiated internally, that does not satisfy any of Questions 1 through 4?
If Yes: Assign Pathway B.

If no pathway can be assigned after completing the checklist, escalate to Quality Assurance management for a documented determination.

6.3 Triage Decision Tree

IMAGE-GENERATION INSTRUCTION BLOCK: Generate a landscape-format flowchart titled "QM.SLQ052 Design Control Pathway Triage Decision Tree." The flowchart uses the following logic. All shapes are rectangular except decision diamonds. Start with a single rectangular box at the top labeled "New Design Activity Identified." Draw a downward arrow to Decision Diamond 1: "New product, new generation, new intended use, or new platform?" If Yes, draw an arrow right to a rectangular outcome box labeled "Assign Pathway A (Full Development)." If No, draw a downward arrow to Decision Diamond 2: "Supplier, CMO, or sub-tier notification of any component, material, or process modification?" If Yes, draw an arrow right to a rectangular outcome box labeled "Assign Pathway C (Supplier/CMO-Initiated Change)." If No, draw a downward arrow to Decision Diamond 3: "Potential impact on safety, essential performance, sterility, biocompatibility, dimensional fit, materials, or regulatory clearance?" If Yes, draw an arrow right to "Assign Pathway A." If No, draw a downward arrow to Decision Diamond 4: "Requires new V&V, new regulatory submission, or introduces new hazard?" If Yes, draw an arrow right to "Assign Pathway A." If No, draw a downward arrow to a rectangular outcome box labeled "Assign Pathway B (Design Change)." Add a note at the bottom: "Pathway C may escalate to Pathway A if the Design Change Assessment identifies safety or essential performance impact." Use SILQ brand colors (navy blue for process boxes, yellow-amber for decision diamonds, green for outcome boxes). Include the document number QM.SLQ052 and revision A in a footer bar.

6.4 Escalation from Pathway C

When a Pathway C assessment under FM2-QM.SLQ052 determines that a supplier or CMO change has potential impact on safety or essential performance, the CAPA field on FM2-QM.SLQ052 shall be used to escalate the change to Pathway A. A new FM1-QM.SLQ052 is completed to initiate the Pathway A project. The Pathway C FM2 record is retained in the DHF as a predecessor document.
---PASTE END---

---

### Section 7 of QM.SLQ052: Pathway A - Full Development

Formatting note: Apply "Heading 1" to "Pathway A - Full Development." Apply "Heading 2" to each sub-heading (7.1 through 7.7). Apply "Heading 3" to gate headings within 7.3 through 7.5.

---PASTE START---
Pathway A - Full Development

7.1 Overview

Pathway A governs comprehensive development projects including new products, new device generations, and any change that requires a full design control cycle. Pathway A uses three compressed gate reviews that replace the legacy seven-phase structure. Optional interim technical reviews may be held at any time but do not substitute for gate reviews.

7.2 Design Project Scope and Plan (FM1-QM.SLQ052)

At the initiation of a Pathway A project, the Project Leader completes FM1-QM.SLQ052, the Design Project Scope and Plan. This single record defines:

(a) Project scope, purpose, endpoint, applicable markets, and reason for initiation;
(b) The design control activities and deliverables required for this project, with documented rationale for any standard deliverable that is scaled back or omitted;
(c) The V&V planning determination, including what verification and validation is planned, with a documented rationale line and QA approval signature when V&V is limited or omitted (closes IA-2025 mNC 1 sub-issue 7);
(d) The plan-revision change-control log, which records each plan revision under change control with a DCO reference or QA-approved minor revision notation (closes IA-2025 mNC 1 sub-issue 3);
(e) The three-gate milestone structure with target dates, key activities per gate, and resource assignments.

FM1-QM.SLQ052 is approved by Executive Management, R&D and Engineering, Quality Assurance, Regulatory Affairs, and Manufacturing before the project proceeds to Gate 1. Any updates to the approved plan are change-controlled per Section 7.4.

7.3 Gate 1 - Planning and Inputs

Gate 1 entry: The Project Leader and Quality Assurance confirm that FM1-QM.SLQ052 has been approved, the project scope is defined, and preliminary user needs and design inputs are documented.

Gate 1 deliverables:
(a) Approved FM1-QM.SLQ052 (Design Project Scope and Plan);
(b) Documented user needs (TMP1-QM.SLQ052, user needs columns);
(c) Draft design inputs and product requirements (TMP1-QM.SLQ052, design inputs columns), reviewed for completeness and testability;
(d) Preliminary risk analysis plan (or documented reference to QM.SLQ012 risk management plan) and initial hazard identification;
(e) Regulatory and clinical strategy summary;
(f) Identification of critical suppliers, CMOs, and consultants.

Gate 1 exit: A formal design review using FM3-QM.SLQ052 (gate selector set to Gate 1) is conducted, attended by the Project Leader, Engineering, Quality and Regulatory, and an Independent Reviewer. The gate closes when all Gate 1 deliverables are approved, all action items are resolved or assigned, and the Gate 1 FM3-QM.SLQ052 is signed by all required attendees. At Gate 1 closure, design inputs are frozen; any subsequent revision to released design inputs is change-controlled per QM.SLQ001. Exit criterion: inputs under control.

7.4 Plan Updates Between Gates

Any revision to the approved FM1-QM.SLQ052 Design Project Scope and Plan occurring between gates must be documented using the plan-revision change-control log on FM1-QM.SLQ052. Minor revisions (timeline shifts, resource adjustments, addition of optional deliverables) may be approved by Quality Assurance alone, noted in the log with a rationale entry and QA signature. Substantive revisions (scope changes, addition or removal of required deliverables, changes to gate structure) must be processed through the DCO process per QM.SLQ001. In all cases the revision is traceable in the DHF.

7.5 Gate 2 - Design Outputs and Verification and Validation

Gate 2 entry: Gate 1 is closed, all Gate 1 action items are resolved, and design outputs have been developed against the frozen design inputs.

Gate 2 deliverables:
(a) Controlled design outputs including engineering drawings, component and assembly specifications, BOM, labeling, packaging specifications, and software documentation, all under formal document control;
(b) Completed TMP1-QM.SLQ052 (Design Input, Output, and Traceability Matrix) linking each design input to one or more design outputs and to the corresponding V&V activities;
(c) Approved V&V plan, protocols, and results (TMP2-QM.SLQ052), demonstrating that each design output has been verified against the corresponding design input and that validation activities have been completed or are in progress on initial production units or documented equivalents;
(d) Validation equivalence documentation where validation was not conducted on initial production units (see Section 13.4);
(e) Updated risk management file (QM.SLQ012 and QM.SLQ013), including risk analysis updates reflecting the developed design and any new mitigations identified;
(f) Any V&V deviations recorded on FM4-QM.SLQ052.

Gate 2 exit: A formal design review using FM3-QM.SLQ052 (gate selector set to Gate 2) is conducted, attended by the Project Leader, Engineering, Quality and Regulatory, and an Independent Reviewer. Exit criterion: design verified and validated against inputs and user needs, traceability matrix substantially complete.

7.6 Gate 3 - Transfer and Closure

Gate 3 entry: Gate 2 is closed, all Gate 2 action items are resolved, and transfer readiness activities have been substantially completed.

Gate 3 deliverables:
(a) Formally released DMR (per QM.SLQ048) reflecting the transferred device design;
(b) Completed and signed TMP3-QM.SLQ052 (Design Transfer Checklist), including manufacturing readiness assessment;
(c) Process validation status report (per QM.SLQ047);
(d) DHF completeness audit confirming that all required design history records are present in the SILQ eQMS and retrievable;
(e) Final traceability matrix (TMP1-QM.SLQ052), completed;
(f) Risk Management Report (per QM.SLQ012), completed and approved;
(g) Regulatory clearance status and all required regulatory approvals prior to commercial distribution;
(h) Product-specific quality plans where required.

Gate 3 exit: A formal design review using FM3-QM.SLQ052 (gate selector set to Gate 3) is conducted as the final design review for the project. The transfer checklist does not substitute for this final design review. The gate review is attended by the Project Leader, Engineering, Quality and Regulatory, and an Independent Reviewer. Exit criterion: design released, DHF complete and retrievable, product ready for commercial distribution or clinical use as applicable.

7.7 Three-Gate Flow Diagram

IMAGE-GENERATION INSTRUCTION BLOCK: Generate a landscape-format process flow diagram titled "QM.SLQ052 Pathway A: Full Development Three-Gate Flow." Use the following structure. Draw three equally spaced vertical gate barriers labeled "Gate 1: Planning and Inputs," "Gate 2: Design Outputs and V&V," and "Gate 3: Transfer and Closure" from left to right. To the left of Gate 1 place a rectangular swim lane labeled "Pre-Gate Activities" containing one box: "Initiate project; complete FM1-QM.SLQ052 (Scope and Plan)." Between Gate 1 and Gate 2 place a swim lane labeled "Development Activities" containing three stacked boxes: "Develop design outputs (drawings, specs, BOM, labeling)"; "Conduct V&V per TMP2-QM.SLQ052"; "Update risk file and traceability matrix (TMP1-QM.SLQ052)." Between Gate 2 and Gate 3 place a swim lane labeled "Transfer Activities" containing three stacked boxes: "Release DMR (QM.SLQ048)"; "Complete Design Transfer Checklist (TMP3-QM.SLQ052)"; "Complete DHF audit and risk management report." To the right of Gate 3 place a swim lane labeled "Closure" containing one box: "DHF closed and filed in SILQ eQMS." Each gate barrier contains a diamond-shaped review symbol labeled "FM3-QM.SLQ052 Gate Review (Independent Reviewer Required)." Below each gate, add an exit criterion note: Gate 1: "Inputs frozen"; Gate 2: "Design verified and validated"; Gate 3: "Design transferred and DHF complete." Add a curved feedback arrow from Gate 3 back to Gate 1 labeled "Change-controlled per Pathway B." Use SILQ brand colors and include the document number QM.SLQ052 Revision A in the diagram footer.
---PASTE END---

---

### Section 8 of QM.SLQ052: Pathway B - Design Change

Formatting note: Apply "Heading 1" to "Pathway B - Design Change." Apply "Heading 2" to sub-headings.

---PASTE START---
Pathway B - Design Change

8.1 Overview

Pathway B applies to internally initiated changes to a released device design that do not meet any of the Pathway A triage criteria. Pathway B is driven by a single Design Change Assessment record (FM2-QM.SLQ052) and a scaled design review using FM3-QM.SLQ052.

8.2 Initiation

The originator of a Pathway B change completes FM2-QM.SLQ052 and routes it to Quality Assurance before any design documentation is revised. The triage result and rationale on FM2-QM.SLQ052 document the basis for the Pathway B assignment.

8.3 Assessment and Review

FM2-QM.SLQ052 documents:
(a) Change description and source;
(b) Design impact assessment identifying affected inputs, outputs, and interfaces;
(c) Risk determination with link to the current risk management file per QM.SLQ012 and QM.SLQ013;
(d) V&V determination (what verification or validation is required, or a documented rationale that none is needed);
(e) Regulatory assessment (Letter-to-File or 510(k) determination), retained in the DHF;
(f) Disposition and routing to the DCO process.

A scaled design review using FM3-QM.SLQ052 (gate selector set to Fast-Track) is required for all Pathway B changes. The Independent Reviewer requirement applies to all Pathway B design reviews.

8.4 Documentation and Closure

Upon approval of FM2-QM.SLQ052 and completion of the design review, revised controlled documents are updated through the DCO process per QM.SLQ001. The completed FM2-QM.SLQ052 and FM3-QM.SLQ052 records are filed in the appropriate DHF in the SILQ eQMS.
---PASTE END---

---

### Section 9 of QM.SLQ052: Pathway C - Supplier or CMO-Initiated Change

Formatting note: Apply "Heading 1" to "Pathway C - Supplier or CMO-Initiated Change." Apply "Heading 2" to sub-headings.

---PASTE START---
Pathway C - Supplier or CMO-Initiated Change

9.1 Mandatory Trigger

Receipt of any notification from a supplier, CMO, or sub-tier supplier of a modification to a component, material, manufacturing process, labeling, or packaging that may affect the finished device constitutes a mandatory trigger for Pathway C. This requirement applies regardless of the perceived significance of the change. The trigger applies at the moment notification is received, not at the time SILQ independently discovers the change.

This mandatory trigger is the corrective action for FDA 483 Observation 2 (October 2025) and CAPA 2025-003. Pathway C eliminates the gap that permitted a valve design modification to reach approximately 280 distributed devices without a completed design control review.

9.2 Hold Decision

Upon receipt of a supplier or CMO change notification, Quality Assurance must make and document a hold decision before continued manufacturing or distribution of the affected device. The hold decision is documented on FM2-QM.SLQ052. Options are:

(a) Place a manufacturing and distribution hold on devices produced with or after the modification, pending completion of the Design Change Assessment; or
(b) Allow manufacturing and distribution to continue with documented rationale and Quality Assurance approval, when there is objective evidence that the modification cannot affect the finished device and that risk to patients is not increased.

9.3 Linkage to Purchasing Controls

Pathway C links directly to QM.SLQ020 Purchasing Controls. Contracts, supplier agreements, and purchase orders for all components and manufacturing services shall require suppliers and CMOs to notify SILQ in writing of any modification to a supplied component, material, or process before that modification is implemented. This language is mandatory in all new and renewed supplier agreements per QM.SLQ020 Section 6.3.1 (revised). Non-compliance with the notification requirement is a supplier quality event handled under QM.SLQ015 Supplier Quality Assurance.

9.4 Assessment Procedure

The assessment under Pathway C follows the same FM2-QM.SLQ052 structure as Pathway B, with the following additions:

(a) Change source field must identify the supplier or CMO by name, reference the notification document number and date, and note the received-by date;
(b) Hold decision (Section 9.2 above) must be documented before the FM2-QM.SLQ052 assessment is finalized;
(c) If the assessment determines that the change has potential impact on safety or essential performance, the FM2-QM.SLQ052 record is escalated to Pathway A per Section 6.4.

9.5 Regulatory Assessment

All Pathway C assessments must include a regulatory assessment (Letter-to-File or 510(k) determination) in accordance with the FDA guidance Deciding When to Submit a 510(k) for a Change to an Existing Device. The regulatory determination is retained in the DHF. The Letter-to-File practice established in CAPA 2025-003 is hereby standardized for all supplier-initiated changes that do not require a new 510(k) submission.

9.6 Closure

The completed FM2-QM.SLQ052 and FM3-QM.SLQ052 records are filed in the appropriate DHF. Any revised controlled documents are updated through the DCO process. If the hold decision in Section 9.2 was a hold, Quality Assurance documents the hold release in FM2-QM.SLQ052 after the assessment is approved.
---PASTE END---

---

### Section 10 of QM.SLQ052: Design Inputs

Formatting note: Apply "Heading 1" to "Design Inputs." Apply "Heading 2" to sub-headings. Use Normal style for body paragraphs and lettered lists.

---PASTE START---
Design Inputs

10.1 Minimum Requirements

Design inputs shall address at minimum the following categories as applicable to the device:
(a) User needs: intended use, indications for use, patient population, user characteristics, and clinical procedure requirements;
(b) Functional and performance requirements: device function, performance specification, and essential performance;
(c) Safety requirements: biocompatibility, sterility, packaging integrity, and any specific safety standards;
(d) Regulatory constraints: applicable standards (e.g., ASTM, ISO), regulatory market requirements, and premarket submission requirements;
(e) Dimensional, mechanical, and material requirements sufficient to characterize the device fully and to detect future changes;
(f) Labeling and packaging requirements;
(g) Manufacturability and process requirements;
(h) Outputs from risk management (QM.SLQ012 and QM.SLQ013), including safety requirements derived from hazard analysis.

Design inputs shall be stated as testable requirements using "shall" or "must" statements. Optional requirements may be stated as "should" or "may." Requirements stated as "will" or "is" are design outputs and are not acceptable as design inputs.

10.2 Control and Freeze

Design input documents are developed using TMP1-QM.SLQ052. All design input documents are formally controlled documents processed through the DCO process per QM.SLQ001. Design inputs are frozen at Gate 1 closure. Any revision to frozen design inputs after Gate 1 is processed through the DCO process and recorded in the TMP1-QM.SLQ052 traceability matrix revision history.

10.3 Conflict Resolution

See Section 5.7 for the conflict resolution authority and requirements. All conflict resolutions are documented in the DHF with the rationale described in Section 5.7.

10.4 Design History File

Approved design input documents, including user needs and product requirements, are filed in the appropriate DHF in the SILQ eQMS under the Draft lifecycle state, and transitioned to Released upon approval through the DCO process.
---PASTE END---

---

### Section 11 of QM.SLQ052: Design Outputs

Formatting note: Apply "Heading 1" to "Design Outputs." Apply "Heading 2" to sub-headings.

---PASTE START---
Design Outputs

11.1 Formal Control Requirement

All design outputs are required to be formally controlled. The determination that a design output does not require formal document control is not permitted except for early-stage exploratory sketches or calculations that are not used as the basis for V&V testing or manufacturing. Any document relied upon for V&V testing, manufacturing, purchasing, labeling, or DMR compilation is a design output and must be under formal document control.

11.2 Types of Design Outputs

Design outputs include but are not limited to:
(a) Engineering drawings with dimensional tolerances sufficient to characterize the device and detect modifications;
(b) Component and assembly technical specifications;
(c) Raw material and source control specifications (content previously in TMP1-QM.SLQ007, now maintained as controlled specifications under QM.SLQ048);
(d) Bill of Materials;
(e) Assembly and build instructions;
(f) Packaging and labeling specifications;
(g) Software architecture, design, and source code documentation;
(h) Preliminary bench test reports used in V&V planning.

11.3 DHF Entry Criteria

Design output documents are entered into the DHF in the SILQ eQMS when they meet the following criteria:
(a) The document is in a format that enables verification against design inputs;
(b) The document is under revision control and has been reviewed and approved by appropriate personnel through the DCO process;
(c) The document defines the device or a component of the device in terms that support manufacturing, inspection, purchasing, or safety evaluation.

Exploratory work product that does not meet these criteria remains outside the formal DHF until it is formalized into a controlled design output.

11.4 DMR Basis

The finished design outputs are the basis for the Device Master Record. At Gate 3, all design outputs that form the DMR are formally released per QM.SLQ048.

11.5 Source Control Specifications

Source control specification content (formerly TMP1-QM.SLQ007) is maintained as part of individual component specifications and the BOM under QM.SLQ048. A standalone source control specification template is not required under QM.SLQ052; specifications are created and maintained as controlled documents under the DMR per QM.SLQ048.
---PASTE END---

---

### Section 12 of QM.SLQ052: Design Reviews

Formatting note: Apply "Heading 1" to "Design Reviews." Apply "Heading 2" to sub-headings.

---PASTE START---
Design Reviews

12.1 Types

All formal design reviews at SILQ use FM3-QM.SLQ052, which includes a gate selector for Gate 1, Gate 2, Gate 3, and Fast-Track (used for Pathways B and C). Optional interim technical reviews may be held during Pathway A development and documented on FM3-QM.SLQ052 (gate selector set to Technical Review). Optional reviews are not gate-closing events and do not replace gate reviews.

12.2 Mandatory Attendees

All formal design reviews require the following four attendees:
(a) Project Leader (required);
(b) Engineering representative (required);
(c) Quality and Regulatory representative (required);
(d) Independent Reviewer (required; identified by Quality Assurance management).

The Independent Reviewer shall not have direct responsibility for the design stage being reviewed. Additional attendees from other functions may be added at the discretion of the Project Leader or Quality Assurance.

12.3 Review Preparation

The Project Leader (or designee acting as moderator) is responsible for:
(a) Setting the time, date, and agenda for the review;
(b) Identifying the applicable deliverables, documents, and specifications to be reviewed;
(c) Distributing review materials to attendees in advance.

12.4 Action Items and Closure

All action items identified during a design review are recorded on FM3-QM.SLQ052. Action items must be assigned to a named responsible person with an estimated closure date. The design review meeting record is not considered closed until all action items are resolved and closure documentation is recorded on FM3-QM.SLQ052. Action item closure is audited as part of the DHF audit at Gate 3.

12.5 Approval

The completed FM3-QM.SLQ052 record is approved by signature of all required attendees. The Independent Reviewer confirms that the minutes reflect the results of the review and that all action items have been recorded. For gate reviews, the gate-closing signature on FM3-QM.SLQ052 constitutes the gate closure authorization.

12.6 DHF Filing

Completed FM3-QM.SLQ052 records are filed in the appropriate DHF in the SILQ eQMS.
---PASTE END---

---

### Section 13 of QM.SLQ052: Design Verification and Validation

Formatting note: Apply "Heading 1" to "Design Verification and Validation." Apply "Heading 2" to sub-headings.

---PASTE START---
Design Verification and Validation

13.1 V&V Always Planned and Controlled

Verification and validation planning is mandatory for all design projects and design changes under this procedure. The determination that no V&V is required for a given project or change must be documented, rationale provided, and approved by Quality Assurance. A project scope or pathway assignment is not sufficient justification by itself for omitting V&V planning.

For Pathway A projects, V&V planning is documented in FM1-QM.SLQ052 (V&V planning determination field) and executed using TMP2-QM.SLQ052. For Pathway B and C changes, V&V determination is documented on FM2-QM.SLQ052.

13.2 Verification Requirements

Design verification confirms that design outputs meet the corresponding design inputs. Verification testing is conducted on parts, subassemblies, and finished product described in change-controlled documents. All verification activities are carried out under approved protocols (TMP2-QM.SLQ052) and results are summarized in approved final reports. The results of verification, including the design, method, acceptance criteria, statistical rationale for sample size, test date, and performing individuals, are documented in the DHF.

13.3 Validation Requirements

Design validation confirms that the final product, when manufactured in accordance with the DMR, conforms to the established user needs and intended use. Validation testing must be performed on pre-production or production units, lots, or batches, or their documented equivalents. Validation activities include testing under actual or simulated use conditions. The results of validation are documented in the DHF with the same elements required for verification in Section 13.2.

13.4 Validation Equivalence

When design validation is not conducted on initial production units, equivalence to initial production must be documented. The validation equivalence record must demonstrate, for each characteristic that could affect safety or performance, that:
(a) The materials of construction are identical to those in the intended production configuration;
(b) The manufacturing method and process controls are representative of intended production;
(c) The dimensional and mechanical configuration of the test units matches the production specification;
(d) Any other characteristic relevant to the performance or safety of the device is equivalent.

Validation equivalence documentation is reviewed and approved by Quality Assurance and retained in the DHF.

13.5 Testing Under Subcontractors and Service Vendors

When approved subcontractors or testing service vendors are used for V&V activities, approved protocols must still be used. Subcontractors performing testing must be on the SILQ Approved Supplier List per QM.SLQ015. Final reports must reference the approved protocol document number and revision.

13.6 V&V Deviations

Deviations from approved test methods that do not affect the outcome of testing are documented on FM4-QM.SLQ052. Deviations must be described, justified, and approved by Quality Assurance. FM4-QM.SLQ052 is attached to the applicable final report and filed in the DHF. Deviations may not be used to modify acceptance criteria; if acceptance criteria must change, a revised protocol is required.

13.7 V&V Summary Report

Upon completion of all V&V activities defined in the V&V plan, an overall design V&V summary report is generated summarizing the results. The summary report is a Gate 2 deliverable for Pathway A projects.
---PASTE END---

---

### Section 14 of QM.SLQ052: Risk Management Integration

Formatting note: Apply "Heading 1" to "Risk Management Integration." Apply "Heading 2" to sub-headings.

---PASTE START---
Risk Management Integration

14.1 Risk Management Governed by QM.SLQ012 and QM.SLQ013

Risk management activities for SILQ medical devices are governed by QM.SLQ012 Risk Management SOP and QM.SLQ013 Risk Analysis SOP, which define the overall risk management process, planning requirements, risk acceptability criteria, and post-production review requirements in accordance with ISO 14971:2019. This section defines the integration points between risk management and design control.

14.2 Risk Evaluation Required for Every Change

A risk evaluation is required for every change to a released design, whether processed under Pathway A, B, or C. A full hazard analysis is not required for every change, but a documented evaluation of the change against the current risk management file is required in all cases. The risk evaluation is documented on FM2-QM.SLQ052 and must assess:
(a) Whether the change introduces any new hazard not previously identified in the risk management file;
(b) Whether the change alters the probability or severity of any previously identified hazard;
(c) Whether any existing risk control measure is affected by the change;
(d) Whether the overall residual risk acceptability determination remains valid.

If the evaluation identifies a new hazard, altered probability or severity, or invalidates a risk control measure, the risk management file must be updated per QM.SLQ012 before the change is implemented.

14.3 Traceability of Risk to Design Inputs and V&V

Risk analysis outputs (hazards, mitigations) are traced to design inputs and to V&V activities through TMP1-QM.SLQ052 (Design Input, Output, and Traceability Matrix). The traceability matrix shall include columns for each design input, the corresponding design output, the V&V activity that verifies the output, and any risk mitigation linked to that input or output. This traceability ensures that all safety-critical requirements are verified and that risk control effectiveness is confirmed through testing.

14.4 Risk Integration at Design Review Gates

At each gate review (FM3-QM.SLQ052), the review checklist includes a risk file status item confirming that the risk management file has been reviewed and updated as appropriate for the current gate deliverables. The gate review does not close until the risk file status is satisfactory to the Quality and Regulatory attendee and Independent Reviewer.

14.5 Post-Market Risk Review

Post-production information that may affect risk management activities is evaluated per QM.SLQ012 Section 14 and QM.SLQ033 Post-Market Surveillance SOP. Findings from post-market surveillance that indicate a need to revise design inputs, design outputs, or V&V methods for an in-production device are handled as Pathway B or C changes as applicable.
---PASTE END---

---

### Section 15 of QM.SLQ052: Design Transfer

Formatting note: Apply "Heading 1" to "Design Transfer." Apply "Heading 2" to sub-headings.

---PASTE START---
Design Transfer

15.1 Transfer Scope

Design transfer is the process of translating the final device design into production specifications suitable for reliable and repeatable manufacturing. Transfer applies to both clinical production for investigational use and commercial production for distribution.

15.2 Final Design Review Requirement

Completion and sign-off of the Design Transfer Checklist (TMP3-QM.SLQ052) does not substitute for a final design review. Gate 3 of Pathway A requires both the completed TMP3-QM.SLQ052 and a Gate 3 formal design review using FM3-QM.SLQ052. For Pathway B and C changes that result in a transfer, a Fast-Track design review using FM3-QM.SLQ052 is required in addition to any transfer checklist activities.

15.3 Gate 3 Transfer Activities

The following activities are required at or before Gate 3:
(a) The production DMR is released per QM.SLQ048 and verified to represent the design configuration used in V&V testing;
(b) Manufacturing readiness is assessed, including process validation status per QM.SLQ047;
(c) The DHF audit confirms that all design history records called for in FM1-QM.SLQ052 are present in the SILQ eQMS and retrievable. The DHF audit confirms that all action items from prior design reviews have been closed;
(d) All required regulatory approvals are confirmed before commercial distribution;
(e) Labeling is final and meets all applicable regulatory requirements.

15.4 Clinical Transfer

Product may be transferred for clinical production and use in investigational studies prior to completion of all validation activities. Clinical investigations are considered part of the overall validation phase. Before clinical use, the project team confirms:
(a) Sufficient V&V activities have been completed to ensure patient and user safety;
(b) Regulatory approval for investigational use has been obtained;
(c) Clinical labeling is complete and meets regulatory requirements;
(d) A clinical-unit DHR is established.

Clinical transfer activities are documented using TMP3-QM.SLQ052 (clinical transfer section).

15.5 R&D Materials

Materials purchased for R&D use may not be used in manufacturing finished devices for human use unless the transfer requirements in QM.SLQ020 Purchasing Controls have been met, including supplier qualification per QM.SLQ015.
---PASTE END---

---

### Section 16 of QM.SLQ052: Design Changes and the Design Change Assessment Record

Formatting note: Apply "Heading 1" to "Design Changes and the Design Change Assessment Record." Apply "Heading 2" to sub-headings.

---PASTE START---
Design Changes and the Design Change Assessment Record

16.1 All Changes to Released Designs Require Assessment

Any change to a released device design, regardless of type or perceived magnitude, requires completion of FM2-QM.SLQ052 (Design Change Assessment) before implementation. This requirement applies to:
(a) Changes proposed internally by SILQ;
(b) Changes to components, materials, or processes notified by a supplier, CMO, or sub-tier supplier (Pathway C);
(c) Changes arising from corrective actions, post-market findings, or regulatory agency requests.

16.2 Design Change Assessment Content

FM2-QM.SLQ052 captures the following at minimum:
(a) Change description and source, including for Pathway C the supplier notification reference and date;
(b) Triage result and rationale (Pathway A, B, or C);
(c) Design impact assessment: which design inputs, outputs, interfaces, and DHF records are affected;
(d) Risk determination per Section 14.2;
(e) V&V determination: what verification or validation is required, or documented rationale that none is needed with Quality Assurance approval;
(f) Regulatory assessment: Letter-to-File or 510(k) determination in accordance with the FDA guidance Deciding When to Submit a 510(k) for a Change to an Existing Device, retained in the DHF;
(g) Disposition and routing to the DCO process for revision of affected controlled documents;
(h) Design review record reference (FM3-QM.SLQ052);
(i) For Pathway C: hold decision per Section 9.2.

16.3 Routing to DCO Process

After the FM2-QM.SLQ052 is approved and the design review is complete, any revised controlled documents are updated through the DCO process per QM.SLQ001. The FM2-QM.SLQ052 and FM3-QM.SLQ052 records, together with any updated risk management documents and V&V records, are filed in the DHF.

16.4 Clinical and Market Feedback as a Change Source

Feedback from clinical investigations or post-market surveillance that indicates a need to change a design is evaluated using the triage process in Section 6. The resulting pathway assignment and FM2-QM.SLQ052 record are the formal response to the feedback. Post-market surveillance data is reviewed at management review meetings per QM.SLQ018.
---PASTE END---

---

### Section 17 of QM.SLQ052: Traceability

Formatting note: Apply "Heading 1" to "Traceability." Apply "Heading 2" to sub-headings.

---PASTE START---
Traceability

17.1 Single Traceability Matrix Concept

A single traceability matrix (TMP1-QM.SLQ052) is used throughout the design control lifecycle to trace design inputs through design outputs to V&V activities and risk mitigations. This matrix replaces the separate user needs templates, product requirements templates, and input-output matrix templates from the prior design control system.

17.2 Matrix Content

TMP1-QM.SLQ052 includes:
(a) Design input identifier (unique number retained even if the input is later obsoleted);
(b) User need or regulatory requirement driving the input;
(c) Corresponding design output(s) document number and revision;
(d) V&V activity (protocol number and revision) that verifies the output or validates the input;
(e) Risk mitigation reference (if any hazard is linked to this input or output);
(f) Acceptance criteria summary;
(g) Status (open, verified, validated, closed).

17.3 Maintenance and Updates

TMP1-QM.SLQ052 is updated as design activities proceed. If a design input is removed, the assigned identifier is retained in the matrix with the status "obsoleted" and a DCO reference. The matrix is reviewed and updated at each gate review and at Gate 3 must be complete.
---PASTE END---

---

### Section 18 of QM.SLQ052: Design History File and Medical Device File Linkage

Formatting note: Apply "Heading 1" to "Design History File and Medical Device File Linkage." Apply "Heading 2" to sub-headings.

---PASTE START---
Design History File and Medical Device File Linkage

18.1 DHF Storage and Lifecycle

The DHF for each design project is maintained in the SILQ eQMS. DHF documents follow the standard document lifecycle: Draft (during development and review), Released (upon approval), and Obsolete (when superseded or retired). All DHF records must be in a retrievable format. No physical-only storage of primary DHF records is permitted; original records are uploaded to the SILQ eQMS and the filing path is documented.

18.2 DHF Contents

The DHF for each device type or design project contains or references the following records as applicable:
(a) FM1-QM.SLQ052 (Design Project Scope and Plan);
(b) Design input documents and TMP1-QM.SLQ052 (Input, Output, and Traceability Matrix);
(c) Design output documents;
(d) FM3-QM.SLQ052 (Design Review Records for all gates and reviews);
(e) TMP2-QM.SLQ052 (V&V Plan, Protocol, and Report) and FM4-QM.SLQ052 (V&V Deviations);
(f) Risk management file (per QM.SLQ012);
(g) TMP3-QM.SLQ052 (Design Transfer Checklist);
(h) FM2-QM.SLQ052 (Design Change Assessment records for all post-release changes);
(i) Regulatory submissions, clearances, and Letter-to-File determinations;
(j) Any clinical study records used as validation evidence.

18.3 Medical Device File Framework

SILQ's Medical Device File (MDF) for each device type is the aggregate construct defined in ISO 13485:2016 clause 4.2.3. The MDF contains or references all documentation needed to demonstrate conformity of the device. At SILQ the MDF comprises:
(a) The DHF (design history, maintained per this procedure);
(b) The DMR, also called the Medical Device File by SILQ, containing procedures and specifications for the finished device (maintained per QM.SLQ048);
(c) The DHR, containing the production history for finished lots (maintained per QM.SLQ029);
(d) The risk management file (maintained per QM.SLQ012);
(e) Labeling and product specifications (referenced in the DMR);
(f) Post-market surveillance records where relevant to device conformity (per QM.SLQ033).

The MDF framework is defined and cross-referenced in QM.SLQ027 Quality Manual. The MDF does not require a single physical folder; it is the logical aggregate of the above records as maintained in the SILQ eQMS.

18.4 Records Created Under Superseded SOPs

Records and deliverables created under QM.SLQ004 through QM.SLQ010 for closed design projects (for example, deliverables from DC.SLQ001 and the Phase 0 records of DC.SLQ002) remain valid records and are retained in the DHF. They are not required to be reformatted under the new forms.
---PASTE END---

---

### Section 19 of QM.SLQ052: Records

Formatting note: Apply "Heading 1" to "Records." Use Normal style for the table description and list.

---PASTE START---
Records

The following records are generated and maintained under this procedure. All records are retained in the SILQ eQMS for the period specified in QM.SLQ001 Document Control, and in any case for the life of the device plus a minimum of two years or as required by applicable regulations.

FM1-QM.SLQ052 - Design Project Scope and Plan: One per Pathway A project, filed in the DHF.
FM2-QM.SLQ052 - Design Change Assessment: One per Pathway B or C change event, filed in the DHF.
FM3-QM.SLQ052 - Design Review Record: One per formal design review, filed in the DHF.
FM4-QM.SLQ052 - Design V&V Deviation: One per deviation from an approved protocol, attached to the applicable test report and filed in the DHF.
TMP1-QM.SLQ052 - Design Input, Output, and Traceability Matrix: One per project, updated throughout development, filed in the DHF.
TMP2-QM.SLQ052 - V&V Plan, Protocol, and Report: One per V&V activity set, filed in the DHF.
TMP3-QM.SLQ052 - Design Transfer Checklist: One per transfer event, filed in the DHF.
---PASTE END---

---

### Section 20 of QM.SLQ052: Associated Forms and Templates

Formatting note: Apply "Heading 1" to "Associated Forms and Templates." Use Normal style for the list.

---PASTE START---
Associated Forms and Templates

FM1-QM.SLQ052 - Design Project Scope and Plan
FM2-QM.SLQ052 - Design Change Assessment
FM3-QM.SLQ052 - Design Review Record
FM4-QM.SLQ052 - Design V&V Deviation
TMP1-QM.SLQ052 - Design Input, Output, and Traceability Matrix
TMP2-QM.SLQ052 - V&V Plan, Protocol, and Report
TMP3-QM.SLQ052 - Design Transfer Checklist
---PASTE END---

---

### Compliance Mapping Table for QM.SLQ052

Formatting note: This table is an appendix to the SOP. Place it at the end of the Word document as Appendix 1, with a heading "Appendix 1: Regulatory and Standards Clause-to-Section Mapping." Build the table as a standard Word table with two columns.

---PASTE START---
Appendix 1: Regulatory and Standards Clause-to-Section Mapping

Regulatory Requirement | QM.SLQ052 Section(s) Addressing It
21 CFR 820.30(a) - General design controls; design plans | Sections 6, 7, FM1-QM.SLQ052
21 CFR 820.30(b) - Design and development plans | Sections 7.2, 7.4, FM1-QM.SLQ052
21 CFR 820.30(c) - Design input | Section 10
21 CFR 820.30(d) - Design output | Section 11
21 CFR 820.30(e) - Design review | Section 12, FM3-QM.SLQ052
21 CFR 820.30(f) - Design verification | Section 13.2
21 CFR 820.30(g) - Design validation | Sections 13.3, 13.4
21 CFR 820.30(h) - Design transfer | Section 15
21 CFR 820.30(i) - Design changes | Sections 8, 9, 16, FM2-QM.SLQ052
21 CFR 820.30(j) - Design history file | Section 18, FM1 through TMP3
ISO 13485:2016 clause 7.3.1 - Design and development planning | Sections 6, 7.2, FM1-QM.SLQ052
ISO 13485:2016 clause 7.3.2 - Design and development inputs | Section 10, TMP1-QM.SLQ052
ISO 13485:2016 clause 7.3.3 - Design and development outputs | Section 11, TMP1-QM.SLQ052
ISO 13485:2016 clause 7.3.4 - Design and development review | Section 12, FM3-QM.SLQ052
ISO 13485:2016 clause 7.3.5 - Design and development verification | Section 13.2, TMP2-QM.SLQ052
ISO 13485:2016 clause 7.3.6 - Design and development validation | Sections 13.3, 13.4, TMP2-QM.SLQ052
ISO 13485:2016 clause 7.3.7 - Control of design and development changes | Sections 8, 9, 16, FM2-QM.SLQ052
ISO 13485:2016 clause 7.3.8 - Design and development transfer | Section 15, TMP3-QM.SLQ052
ISO 13485:2016 clause 7.3.9 - Control of design and development files | Section 18
ISO 13485:2016 clause 4.2.3 - Medical device file | Section 18.3, QM.SLQ027
ISO 14971:2019 - Risk management integration | Section 14, FM2-QM.SLQ052, TMP1-QM.SLQ052
FDA Guidance: 510(k) for changes to existing devices | Sections 9.5, 16.2(f), FM2-QM.SLQ052
---PASTE END---

---

## SECTION 4.3 - New Forms and Templates

This section provides complete field structures and build instructions for all seven new forms and templates. For each item, the formatting note describes the document layout. The paste blocks contain field labels, instructions, and standard text as they should appear in the Word document. Tables are described as build instructions rather than large markdown tables, per the formatting conventions.

---

### FM1-QM.SLQ052 - Design Project Scope and Plan

Formatting note: Build this as a Word form with a standard SILQ header showing document number FM1-QM.SLQ052, title "Design Project Scope and Plan," revision A, and page number. Use table cells for fill-in fields. The form is divided into six sections labeled with Word bold text. Build each labeled section as a bordered table or set of bordered table cells.

---PASTE START---
FM1-QM.SLQ052: Design Project Scope and Plan

Section A - Project Identification

Project or DHF Designation: [fill in]
Device Name and Description: [fill in]
Project Purpose (select all that apply): New product development / New generation of existing product / Design change or update / Corrective action / CMO or supplier change escalated to Pathway A / Other: [specify]
Project Endpoint: Commercial product / Clinical or investigational product / Validated design (pre-clinical only) / Design output only
Applicable Regulatory Markets: United States / European Union / Canada / Other: [specify]
Reason for Project Initiation: [fill in]
Pathway Assignment: Pathway A (Full Development)
External Partner Constraints: [fill in or N/A]
Regulatory Constraints: [fill in]
Additional Risk and Hazard Considerations: [fill in]

Section B - Scope Conclusion

Based on the above, provide a summary conclusion describing the scope of design control activities for this project, the anticipated development timeline, and any limitations or exclusions.

Scope Conclusion: [fill in]

Section C - Applicable Design Control Phases and Deliverables

Build a table with four columns: Design Control Activity, Gate or Phase, Applicable (Yes / No / N/A), and Rationale if Not Applicable. List the following rows:

Design Project Scope and Plan (FM1-QM.SLQ052) | Gate 1 | Yes/No/N/A | [rationale]
User Needs documentation | Gate 1 | Yes/No/N/A | [rationale]
Design Inputs and Product Requirements | Gate 1 | Yes/No/N/A | [rationale]
Preliminary Risk Analysis and Risk Management Plan | Gate 1 | Yes/No/N/A | [rationale]
Regulatory and Clinical Strategy | Gate 1 | Yes/No/N/A | [rationale]
Design Outputs (drawings, specs, BOM, labeling) | Gate 2 | Yes/No/N/A | [rationale]
Design Input, Output, and Traceability Matrix (TMP1-QM.SLQ052) | Gate 2 | Yes/No/N/A | [rationale]
V&V Plan, Protocol, and Report (TMP2-QM.SLQ052) | Gate 2 | Yes/No/N/A | [rationale]
Updated Risk Management File | Gate 2 | Yes/No/N/A | [rationale]
DMR Release (QM.SLQ048) | Gate 3 | Yes/No/N/A | [rationale]
Design Transfer Checklist (TMP3-QM.SLQ052) | Gate 3 | Yes/No/N/A | [rationale]
Process Validation (QM.SLQ047) | Gate 3 | Yes/No/N/A | [rationale]
DHF Audit | Gate 3 | Yes/No/N/A | [rationale]
Risk Management Report | Gate 3 | Yes/No/N/A | [rationale]
Regulatory Submission or Clearance | Gate 3 | Yes/No/N/A | [rationale]

Note: If any required deliverable in the table is marked No or N/A, the rationale column must contain a documented justification, and the V&V planning determination in Section D must address V&V specifically.

Section D - V&V Planning Determination (Required; closes IA-2025 mNC 1 sub-issue 7)

This section must be completed for every project. If verification and validation activities are planned, describe what V&V is planned. If V&V is limited in scope or omitted for any deliverable, provide the documented rationale and obtain QA approval before the project proceeds past Gate 1.

V&V Planned: [Describe the body of verification and validation planned for this project, including test types, whether V&V will be conducted on production units or equivalents, and any phasing of V&V activities across gates.]

Rationale for Any Limitation or Omission of V&V: [Fill in, or state "No limitation or omission; full V&V is planned as described above."]

QA Review and Approval for Any V&V Limitation or Omission:
QA Reviewer Printed Name: [fill in]
QA Reviewer Signature: [fill in]
Date: [fill in]

If no limitation or omission, QA Reviewer confirms by signing that V&V as described is adequate for the project scope:
QA Reviewer Signature: [fill in]
Date: [fill in]

Section E - Plan Revision Change-Control Log (Required; closes IA-2025 mNC 1 sub-issue 3)

Build a table with five columns: Revision Number, Date, Summary of Change to Plan, Change-Control Method (DCO Number if substantive; QA-approved minor revision notation), and QA Approval Signature and Date.

This table must be updated each time the approved plan is revised. Minor revisions (timeline, resource adjustments, addition of optional deliverables) require QA approval and a notation in this table. Substantive revisions (scope, gate structure, required deliverables) require a DCO reference in addition to QA approval.

Rev 1 | [date] | Initial approval of plan | N/A - initial issue | [QA signature and date]
[Add rows as revisions occur]

Section F - Gate Milestone Summary

Build a table with three columns: Gate, Target Completion Date, and Actual Completion Date (DHF FM3-QM.SLQ052 reference).

Gate 1 - Planning and Inputs | [target date] | [actual date and FM3 record number]
Gate 2 - Design Outputs and V&V | [target date] | [actual date and FM3 record number]
Gate 3 - Transfer and Closure | [target date] | [actual date and FM3 record number]

Section G - Approvals

Build a table with four columns: Printed Name, Department, Signature, Date.

Include rows for: Executive Management, R&D and Engineering, Quality Assurance, Regulatory Affairs, Manufacturing, Additional Approver (if needed).

---PASTE END---

---

### FM2-QM.SLQ052 - Design Change Assessment

Formatting note: Build this as a Word form with a standard SILQ header showing document number FM2-QM.SLQ052, title "Design Change Assessment," revision A, and page number. Use bordered table cells for all fill-in sections.

---PASTE START---
FM2-QM.SLQ052: Design Change Assessment

This record is mandatory for all changes to a released design under Pathway B (internally initiated) or Pathway C (supplier or CMO-initiated). Complete all sections before any design documentation is revised or any supplier change is accepted.

Section A - Change Identification

DCA Number: [sequential, assigned by QA]
Date Initiated: [fill in]
Initiated By: [name and title]
Related DCO (if known): [fill in or TBD]
Related CAPA (if any): [fill in or N/A]
Project or DHF Designation: [fill in]
Device Name and Description: [fill in]

Section B - Change Source (select one)

Internal - SILQ initiated
Supplier or CMO Notification (Pathway C mandatory trigger): Supplier or CMO Name: [fill in] / Notification Document Reference: [fill in] / Notification Received Date: [fill in]
Regulatory Agency Request
Post-Market Finding
Other: [specify]

Note: For Pathway C, the notification received date in Section B determines the clock for the hold decision in Section D. Any supplier notification, regardless of form (written, email, or verbal confirmed in writing), triggers this record.

Section C - Triage Result

Pathway assigned: Pathway B (Design Change) / Pathway C (Supplier or CMO-Initiated) / Escalate to Pathway A (Pathway C escalation)

Triage rationale: [Document the basis for the pathway assignment with reference to Section 6.2 of QM.SLQ052. If escalating to Pathway A, describe the specific safety or essential performance impact that triggers escalation.]

Section D - Hold Decision (Pathway C Only; leave blank for Pathway B)

Hold decision made by: [name and title]
Hold decision date: [fill in]
Hold decision: Manufacturing and distribution hold placed / Manufacturing and distribution may continue with documented rationale

If continuing manufacturing and distribution: Documented rationale and objective evidence that modification does not affect the finished device or patient risk:
[fill in rationale]

QA Approval for Continue Decision:
QA Printed Name: [fill in]
QA Signature: [fill in]
Date: [fill in]

Hold Release (complete after assessment is approved): Date hold released: [fill in] / QA approval: [signature and date]

Section E - Design Impact Assessment

Describe the change in detail, including any affected components, materials, processes, dimensions, specifications, or labeling:
[fill in]

Affected design input documents (document numbers and revisions): [fill in or N/A]
Affected design output documents (document numbers and revisions): [fill in or N/A]
Affected DHF records: [fill in or N/A]
Affected traceability matrix entries: [fill in or N/A]
Is the DMR affected? Yes / No. If yes, identify affected sections: [fill in]

Section F - Risk Determination

Current risk management file reference(s) (QM.SLQ012): [document numbers]

Does this change introduce any new hazard not previously identified in the risk management file?
Yes / No. If yes, describe: [fill in]

Does this change alter the probability or severity of any previously identified hazard?
Yes / No. If yes, describe: [fill in]

Does this change affect any existing risk control measure?
Yes / No. If yes, describe: [fill in]

Risk management file update required? Yes / No. If yes, DCO reference for updated risk file: [fill in]

Overall residual risk acceptability after this change: Acceptable per existing risk management file / Acceptable per updated risk management file / Risk acceptability determination pending additional analysis

Risk Determination Approved By: [name, title, signature, date]

Section G - V&V Determination

Is verification or validation required for this change? Yes / No / Partial (describe scope).

If Yes or Partial: Describe the V&V activities required, reference protocol(s) to be used or developed, and note whether validation equivalence documentation is needed:
[fill in]

If No: Document the rationale that no V&V is required:
[fill in rationale]

QA Approval of V&V Determination:
QA Printed Name: [fill in]
QA Signature: [fill in]
Date: [fill in]

Section H - Regulatory Assessment

Assessment conducted by: [name and title, Regulatory Affairs or designee]
Assessment date: [fill in]

Assessment basis: FDA Guidance - Deciding When to Submit a 510(k) for a Change to an Existing Device (October 25, 2017) and 21 CFR Part 807, Subpart E.

Does this change require a new 510(k) submission?
Yes - New 510(k) required before commercial distribution. 510(k) number (when received): [fill in]
No - Letter-to-File determination. Summary of basis for Letter-to-File: [fill in]

Letter-to-File or 510(k) determination is retained in the DHF. Reference location in SILQ eQMS: [fill in]

Section I - Disposition and Routing

Disposition: Approve change and proceed / Reject change (rationale): [fill in] / Defer pending additional information: [fill in]

Controlled documents to be revised (list document numbers): [fill in or N/A]
DCO to be initiated: DCO Number: [fill in]
Design Review required: Yes. FM3-QM.SLQ052 record number: [fill in]

Section J - Approvals

Build a table with four columns: Printed Name, Department, Signature, Date.

Include rows for: R&D and Engineering, Quality Assurance (required), Regulatory Affairs (required for Section H), Manufacturing (if DMR affected).

---PASTE END---

---

### FM3-QM.SLQ052 - Design Review Record

Formatting note: Build this as a Word form with a standard SILQ header showing document number FM3-QM.SLQ052, title "Design Review Record," revision A, and page number. This single form covers Gate 1, Gate 2, Gate 3, Fast-Track (Pathways B and C), and optional Technical Review. The gate selector in Section A drives which deliverable checklist items are displayed; in Word, use conditional content or build all checklists and instruct the user to check only the applicable gate section.

---PASTE START---
FM3-QM.SLQ052: Design Review Record

Section A - General Information

Project or DHF Designation: [fill in]
Device Name and Description: [fill in]
Review Type (select one): Gate 1 - Planning and Inputs / Gate 2 - Design Outputs and V&V / Gate 3 - Transfer and Closure / Fast-Track (Pathway B or C) / Technical Review (optional interim)
Related FM2-QM.SLQ052 DCA Number (for Fast-Track): [fill in or N/A]
Review Date: [fill in]
Meeting Start Time: [fill in]
Meeting End Time: [fill in]
Moderator Printed Name: [fill in]
Moderator Title: [fill in]

Prior Design Reviews for this Project (list FM3 record numbers): [fill in or None]

Section B - Attendee List

Build a table with four columns: Position, Printed Name, Attended Meeting (Yes/No), Signature (signature confirms agreement with meeting record).

Include rows for: Project Leader (required), Engineering (required), Quality and Regulatory (required), Independent Reviewer (required), Other (specify title), Other (specify title). Note at the bottom of the attendee table: Project Leader may also serve as Engineering or Quality and Regulatory representative if the same individual holds those roles.

Section C - Documents and Items Reviewed

Build a table with three columns: Item Number, Document Number and Revision (or description), and Reviewed (Yes/No/N/A).

Add rows as needed for documents and items reviewed during this session.

Section D - Gate or Review Deliverable Checklist

Complete only the section matching the gate or review type selected in Section A.

--- Gate 1 Deliverables Checklist ---

Build a table with four columns: Deliverable, Document Number or Reference, Acceptable (Yes/No), Action Item Number if Not Acceptable.

Row 1: FM1-QM.SLQ052 Design Project Scope and Plan approved
Row 2: User needs documented, complete, and adequate
Row 3: Design inputs documented, complete, testable, and adequate
Row 4: Preliminary risk analysis and risk management plan initiated
Row 5: Regulatory and clinical strategy defined
Row 6: Project team and critical suppliers identified
Row 7: Additional deliverables per FM1-QM.SLQ052 project-specific plan (list any)
Row 8: Prior design reviews complete and action items resolved (or None)

Are all Gate 1 deliverables acceptable and complete? Yes / No (action items required)

--- Gate 2 Deliverables Checklist ---

Row 1: Controlled design outputs (drawings, specs, BOM, labeling, software) reviewed and adequate
Row 2: TMP1-QM.SLQ052 Design Input, Output, and Traceability Matrix complete and accurate
Row 3: TMP2-QM.SLQ052 V&V Plan, Protocol, and Results - all V&V activities complete or documented as in progress with schedule
Row 4: Validation equivalence documentation (if applicable) complete and approved
Row 5: Risk management file updated and reviewed; risk acceptability confirmed
Row 6: V&V deviations (FM4-QM.SLQ052) reviewed and resolved
Row 7: Additional deliverables per FM1-QM.SLQ052 project-specific plan (list any)
Row 8: Gate 1 action items resolved

Are all Gate 2 deliverables acceptable and complete? Yes / No (action items required)

--- Gate 3 Deliverables Checklist ---

Row 1: DMR formally released (QM.SLQ048); production configuration matches V&V test configuration
Row 2: TMP3-QM.SLQ052 Design Transfer Checklist complete and signed
Row 3: Process validation status acceptable (QM.SLQ047)
Row 4: DHF audit complete - all required records present in SILQ eQMS and retrievable
Row 5: TMP1-QM.SLQ052 Traceability Matrix complete
Row 6: Risk Management Report complete (QM.SLQ012)
Row 7: Regulatory approvals confirmed prior to commercial distribution
Row 8: All prior design review action items resolved
Row 9: Product-specific quality plans complete (if required)
Row 10: Additional deliverables per FM1-QM.SLQ052 project-specific plan (list any)

Are all Gate 3 deliverables acceptable and complete? Yes / No (action items required)

--- Fast-Track Deliverables Checklist (Pathways B and C) ---

Row 1: FM2-QM.SLQ052 Design Change Assessment completed and approved
Row 2: Change description, design impact, risk determination reviewed and adequate
Row 3: V&V determination reviewed and adequate
Row 4: Regulatory assessment completed and Letter-to-File or 510(k) determination documented
Row 5: Affected design input documents reviewed (if any)
Row 6: Affected design output documents reviewed (if any)
Row 7: Updated traceability matrix reviewed (if applicable)
Row 8: Risk management file update confirmed or not required with rationale
Row 9: Hold decision reviewed and documented (Pathway C only)
Row 10: DMR changes identified and routed to DCO process (if any)

Are all Fast-Track deliverables acceptable and complete? Yes / No (action items required)

--- Technical Review Checklist (Optional Interim Review) ---

Row 1: Scope of technical review documented
Row 2: Technical aspects of design reviewed with findings recorded
Row 3: Adequacy of design outputs to meet design inputs assessed
Row 4: Identified issues and corrective actions recorded as action items

Section E - Action Items

Build a table with seven columns: Item Number, Description of Action Item (be specific; include document numbers if applicable), Responsible Person, Due Date, Status (Open/Completed/Transferred), Closure Notes and Document Reference, Initials and Date of Closure.

Instructions at top of table: Action items are numbered starting at 1 for this record. All action items must be closed before this review record is finalized and the gate is considered closed (for gate reviews). Closure notes must reference the DCO or document that resolves the item.

Section F - Review Conclusion

Provide a narrative conclusion of the review meeting, including overall assessment of the design stage reviewed, any significant risks or concerns identified, and the overall recommendation.

Conclusion: [fill in]

Section G - Gate Closure Statement (for Gate Reviews Only)

Complete only for Gate 1, Gate 2, or Gate 3 reviews.

Gate [1/2/3] closure is recommended: Yes / No (explain): [fill in]

If No, identify conditions that must be satisfied before gate closes: [fill in]

Section H - Approvals

Build a table with four columns: Position, Printed Name, Signature, Date.

Include rows for: Project Leader (required), Engineering (required), Quality and Regulatory (required), Independent Reviewer (required), Additional Approver (if needed).

Section I - DHF Closure Block

Complete at final gate closure (Gate 3) or after Fast-Track review closure.

All required DHF records for this review are present in the SILQ eQMS: Yes / No (if No, list missing records)

Reviewer confirming DHF filing completeness:
Printed Name: [fill in]
Title: [fill in]
Signature: [fill in]
Date: [fill in]

---PASTE END---

---

### FM4-QM.SLQ052 - Design V&V Deviation

Formatting note: Build this as a compact Word form, one page per deviation, with a standard SILQ header showing document number FM4-QM.SLQ052, title "Design V&V Deviation," revision A, and page number.

---PASTE START---
FM4-QM.SLQ052: Design V&V Deviation

DESIGN VERIFICATION AND VALIDATION DEVIATION

Protocol Number and Revision: [fill in]
Sequential Deviation Number for this Protocol: [sequential starting at 1]
Protocol Section: [fill in]

DESCRIPTION OF DEVIATION

Describe the deviation from the approved test method: [fill in]

Submitted By: [name]
Date Submitted: [fill in]

RESPONSE AND RESOLUTION

Results of investigation (if further action is required, include estimated completion date): [fill in]

Basis for determination that this deviation does not affect the validity or outcome of the test: [fill in]

Is retesting required? Yes / No

Submitted By: [name]
Date: [fill in]

QA Approval:
Approved By: [name]
Signature: [fill in]
Date: [fill in]

Note: This form may not be used to document changes to acceptance criteria. If acceptance criteria must change, a revised and re-approved protocol is required.

---PASTE END---

---

### TMP1-QM.SLQ052 - Design Input, Output, and Traceability Matrix

Formatting note: Build this as a controlled Word document (or Excel spreadsheet if preferred, with document control header matching SILQ standards). The template contains a cover page with standard SILQ header fields, followed by two tables. Table 1 is the User Needs table (5 columns, lean). Table 2 is the Design Input, Output, and Traceability table (6 columns). The previous draft of this template had 12 columns in Table 2; this revision reduces it to 6 by combining the design output document number and description into one cell, combining verification and validation protocol references into one cell, combining verification and validation status into one status cell, and moving risk references and N/A rationale into the Notes column. The template itself is the controlled blank form; the completed project-specific version is the DHF record.

---PASTE START---
TMP1-QM.SLQ052: Design Input, Output, and Traceability Matrix

Cover Page Information:
Document Number: TMP1-QM.SLQ052
Title: Design Input, Output, and Traceability Matrix
Revision: A
Project or DHF Designation: [fill in when completing for a project]
Device Name: [fill in]
Prepared By: [fill in]
QA Reviewed By: [fill in]
Date: [fill in]

Instructions for Use:
This template is completed once per design project (Pathway A) or per design change event (Pathways B and C) and filed in the DHF. Each design input is assigned a unique identifier (e.g., DI-001, DI-002) that is never reused or reassigned. If a design input is deleted, mark its row status as Obsoleted with the DCO reference. All columns must be completed to the extent applicable at each revision of the matrix.

Table 1: User Needs

Build a table with five columns and set column widths roughly as follows: UN-ID (narrow), User Need Statement (wide), Source (medium), Linked Design Input ID(s) (medium), Status (narrow).

Column headers:
UN-ID | User Need Statement | Source | Linked DI-ID(s) | Status

Notes on Table 1 columns:
UN-ID: e.g., UN-001, UN-002. Never reuse or reassign.
User Need Statement: state the need in plain language from the user or regulatory perspective. No shall/must language required here.
Source: use one of: User, Regulatory, Clinical, Market, Internal.
Linked DI-ID(s): list the DI-IDs in Table 2 that translate this user need into a design requirement.
Status: Open, Validated, or Obsoleted.

Table 2: Design Input, Output, and Traceability

Build a table with six columns. Set column widths to give the most space to columns 2 and 3. Suggested relative widths: DI-ID (narrow), Design Input Statement (widest), Design Output Reference (wide), V&V Protocol Reference(s) (wide), Status (narrow), Notes (medium).

Column headers:
DI-ID | Design Input Statement | Design Output Reference | V&V Protocol Reference(s) | Status | Notes

Notes on Table 2 columns:
DI-ID: e.g., DI-001, DI-002. Never reuse or reassign.
Design Input Statement: state the requirement using shall or must language. Include the acceptance criterion in the statement itself where practical (e.g., "The catheter balloon shall inflate to 10 cc within 30 seconds at 37 degrees C."). This keeps acceptance criteria where they are readable and removes the need for a separate acceptance-criteria column.
Design Output Reference: enter the document number, revision, and a brief description of the controlled output document that satisfies this input (e.g., "DWG-SLQ001 Rev B, Balloon Dimensional Drawing"). If multiple outputs satisfy one input, list each on a new line in the cell.
V&V Protocol Reference(s): enter the protocol document number and revision. If the same protocol covers both verification and validation, enter it once and note "Ver+Val" in parentheses. If separate protocols exist, list each on a new line. If no V&V is required for this input, enter N/A and record the rationale in the Notes column.
Status: use one of: Not Started, In Progress, Complete, N/A. At Gate 3 (or at design change closure for Pathways B and C), all rows must show Complete or N/A. N/A requires a rationale in Notes.
Notes: use this column for three purposes: (1) record the risk management file reference (hazard ID or control number) if this input is a risk mitigation measure; (2) record the rationale for any N/A status in V&V Protocol Reference(s) or Status; (3) record any open action or traceability gap that must be resolved before gate closure.

Footer instruction: Update this matrix at each gate review. At Gate 3, all rows in Table 2 must show Complete or N/A in the Status column. Any N/A row must have a documented rationale in the Notes column. This matrix, once completed and QA-reviewed, is filed in the DHF as a released record.

Old-to-new mapping note (for reference, not in the controlled template body): TMP1-QM.SLQ052 replaces TMP1-QM.SLQ006 (User Needs Template), TMP2-QM.SLQ006 (Product Requirements Template), and TMP2-QM.SLQ007 (Design Input-Output Matrix Template).

---PASTE END---

---

### TMP2-QM.SLQ052 - V&V Plan, Protocol, and Report

Formatting note: Build this as a controlled Word document with a standard SILQ header. The template is structured in three major sections separated by page breaks: Part 1 is the V&V Plan, Part 2 is the Test Protocol, and Part 3 is the Final Report. When used for a specific test activity, all three parts are completed in sequence and the document is controlled as a single DHF record. Part 1 Section 1.2 (Test Group Summary) uses a lean five-column table; statistical rationale and detailed purpose belong in Part 2, not the summary table.

---PASTE START---
TMP2-QM.SLQ052: V&V Plan, Protocol, and Report

Cover Page Information:
Document Number: TMP2-QM.SLQ052
Title: V&V Plan, Protocol, and Report
Revision: A
Project or DHF Designation: [fill in when completing for a project]
Test Group Title: [fill in, e.g., "Dimensional Verification - Foley Catheter SLQ-001"]
Document Type (select): Design Verification / Design Validation / Combined Verification and Validation
Prepared By: [fill in]
QA Reviewed and Approved By: [fill in]
Approval Date: [fill in]

Instructions for Use:
This template consolidates the V&V Plan, Protocol, and Final Report into a single controlled document per test group. Part 1 (Plan) is completed and approved before any testing begins. Part 2 (Protocol) is completed as part of initial approval. Part 3 (Report) is completed after testing and is approved as a separate approval action on the cover page. Deviations from the protocol are documented on FM4-QM.SLQ052 and attached.

PART 1: V&V PLAN

1.1 Scope and Purpose
Describe what this test group is intended to verify or validate. Reference the design input identifiers (DI-IDs from TMP1-QM.SLQ052) that this testing addresses.

Scope: [fill in]
Design Input Identifiers Addressed: [fill in, e.g., DI-001, DI-003, DI-007]

1.2 Test Group Summary Table
Build a table with five columns. The detailed purpose description, statistical rationale, and evidence documentation belong in Part 2 and Part 3 of this template, not in the summary table. Keep this table lean so it can be completed quickly and read at a glance.

Column headers:
Test ID | Test Group Title | Type | DI-IDs Addressed | Status

Notes on columns:
Test ID: e.g., TG-001, TG-002.
Test Group Title: a short descriptive name (e.g., "Dimensional Verification - Balloon Inflation").
Type: Verification, Validation, or Combined.
DI-IDs Addressed: list the DI-IDs from TMP1-QM.SLQ052 that this test group covers.
Status: Not Started, In Progress, or Complete.

1.3 V&V Planning Determination Reference
Reference the V&V planning determination in FM1-QM.SLQ052 Section D (for Pathway A) or FM2-QM.SLQ052 Section G (for Pathways B and C). Confirm that this test group is consistent with the approved plan.

1.4 Test Unit Configuration
Describe the test units: product number, lot or batch, configuration, and whether validation equivalence documentation is required. If validation equivalence is required, reference the equivalence record location in the DHF.

PART 2: TEST PROTOCOL

2.1 Test Scope and Objective
[fill in - specific to this test group]

2.2 Applicable Standards and References
[fill in - applicable ASTM, ISO, or SILQ test method references]

2.3 Test Equipment and Calibration
Build a table with columns: Equipment Description, Equipment Identification or Serial Number, Calibration Due Date, Calibration Control Number or Certificate Reference. Note: All measurement equipment must be calibrated before use. Calibration status is documented before test execution.

2.4 Test Procedure
[fill in - step-by-step test procedure. Number each step. Each step should be completable by a trained technician without additional verbal instruction.]

2.5 Acceptance Criteria
[fill in - state pass/fail criteria for each test measurement in objective, testable terms. No subjective criteria without defined judgment standards.]

2.6 Sample Size and Statistical Rationale
[fill in - state number of samples, confidence level, reliability level, and statistical method used. Reference QM.SLQ011 for statistical methods guidance.]

2.7 Protocol Approval
This protocol must be approved before testing begins. Approved by:
R&D and Engineering Approval: [name, signature, date]
QA Approval: [name, signature, date]

PART 3: FINAL REPORT

3.1 Test Execution Summary
Test execution dates: [fill in]
Test performed by: [name and title]
Test location: [fill in]
Protocol document number and revision used: [fill in]
Deviations from protocol: [None / See FM4-QM.SLQ052 deviation numbers: fill in]

3.2 Test Results
Build a table with columns: Test Step Number, Test Parameter Measured, Acceptance Criterion, Observed Result, Pass / Fail. Add rows for each test step with quantitative or objective result.

3.3 Data Analysis and Summary
[fill in - summarize the data, address any statistical analysis, and state whether the test group as a whole passed or failed]

3.4 Conclusions
[fill in - state whether this test group satisfactorily verifies or validates the referenced design inputs. State whether there are any open items or conditions.]

3.5 Attachments
List all raw data sheets, instrument calibration certificates, and FM4-QM.SLQ052 deviation forms attached to this report.

3.6 Final Report Approval
Approved by:
R&D and Engineering Approval: [name, signature, date]
QA Approval: [name, signature, date]

Old-to-new mapping note (for reference, not in the controlled template body): TMP2-QM.SLQ052 replaces TMP1-QM.SLQ009 (V&V Test Plan Template), TMP2-QM.SLQ009 (V&V Protocol Template), and TMP3-QM.SLQ009 (V&V Final Report Template).

---PASTE END---

---

### TMP3-QM.SLQ052 - Design Transfer Checklist

Formatting note: Build this as a controlled Word document with a standard SILQ header. The template contains a cover block for project identification, two checklist sections (one for commercial transfer and one for clinical or investigational transfer), and a closure signature block. TMP3 uses a four-column table structure (Activity, Document Reference, Status, Notes) throughout, which is already appropriately lean. No column restructuring is needed here.

---PASTE START---
TMP3-QM.SLQ052: Design Transfer Checklist

Cover Information:
Document Number: TMP3-QM.SLQ052
Title: Design Transfer Checklist
Revision: A
Project or DHF Designation: [fill in when completing for a project]
Device Name: [fill in]
Transfer Type: Commercial Transfer / Clinical or Investigational Transfer / Both
Prepared By: [fill in]
Transfer Date Target: [fill in]

Instructions for Use:
This checklist documents the completion status of activities required to transfer the device design to manufacturing for clinical or commercial use. Complete only the section applicable to the transfer type. For activities marked N/A, provide a documented rationale in the notes column. This checklist does not substitute for the final design review (FM3-QM.SLQ052, Gate 3 or Fast-Track); both documents are required.

SECTION 1: COMMERCIAL TRANSFER ACTIVITIES

Build a table with four columns: Activity, Document Reference, Status (Complete / In Progress / N/A), and Notes.

Activity rows:
1. DHF completeness audit conducted - all records present in SILQ eQMS and retrievable
2. All design review action items (from all FM3-QM.SLQ052 records) confirmed closed
3. Design output documents (drawings, specs, BOM) formally released and change-controlled
4. Device Master Record (DMR) released and approved per QM.SLQ048
5. Production DMR verified to represent the design configuration used in V&V testing (equivalence confirmed)
6. Process validation status confirmed acceptable per QM.SLQ047
7. Manufacturing readiness assessed - manufacturing facilities and equipment capable and ready
8. Product-specific quality plans released (if applicable)
9. Labeling finalized and meets all applicable regulatory requirements
10. Regulatory clearance or approval confirmed prior to commercial distribution
11. Risk Management Report completed and approved per QM.SLQ012
12. Traceability Matrix (TMP1-QM.SLQ052) complete and approved
13. Post-market surveillance plan initiated per QM.SLQ033
14. Supplier qualifications confirmed for all production suppliers per QM.SLQ015
15. Receiving inspection criteria aligned with released specifications

SECTION 2: CLINICAL OR INVESTIGATIONAL TRANSFER ACTIVITIES

Build a table with the same four columns as Section 1.

Activity rows:
1. Sufficient V&V completed to ensure patient and user safety at clinical use stage (document evidence)
2. Clinical and investigational regulatory approval obtained (IDE, IND, or applicable authorization)
3. Clinical labeling finalized and meets regulatory requirements for investigational use
4. Clinical unit DMR or equivalent configuration record established
5. Clinical unit DHR records initiated
6. All supplier qualifications met for clinical unit production per QM.SLQ015
7. Risk acceptability confirmed for clinical use at current stage of development
8. All relevant design review action items closed

SECTION 3: TRANSFER CLOSURE AND APPROVAL

This transfer checklist was reviewed and represents an accurate summary of transfer readiness as of the date signed.

Build a table with four columns: Printed Name, Department, Signature, Date.

Include rows for: Project Leader, R&D and Engineering, Quality Assurance (required), Manufacturing, Regulatory Affairs.

Note: This checklist and the Gate 3 (or Fast-Track) FM3-QM.SLQ052 design review record together constitute the complete transfer documentation package. Both must be approved before design closure.

Old-to-new mapping note (for reference, not in the controlled template body): TMP3-QM.SLQ052 replaces TMP1-QM.SLQ010 (Clinical Transfer Checklist Template) and TMP2-QM.SLQ010 (Design Transfer Checklist Template).

---PASTE END---

---

### Old-to-New Mapping Table

Formatting note: This table is for reference and belongs in the editing guide only, not in any controlled document. Build as needed for internal tracking.

The 13 old forms and templates collapse into 7 new items as follows:

Old Document | New Home
FM1-QM.SLQ004 Design Project Scope Form | FM1-QM.SLQ052 (Scope and Plan - Section A)
TMP1-QM.SLQ005 Design Project Plan Template | FM1-QM.SLQ052 (Sections C, D, E, F)
TMP1-QM.SLQ006 User Needs Template | TMP1-QM.SLQ052 (Table 1 - User Needs)
TMP2-QM.SLQ006 Product Requirements Template | TMP1-QM.SLQ052 (Table 2 - Design Inputs)
TMP1-QM.SLQ007 Source Control Spec Template | Folded into controlled specifications under QM.SLQ048; no standalone template
TMP2-QM.SLQ007 Design Input-Output Matrix Template | TMP1-QM.SLQ052 (Table 2 - Traceability Matrix)
FM1-QM.SLQ008 Design Review Minutes Form | FM3-QM.SLQ052 (Design Review Record, all sections)
FM1-QM.SLQ009 V&V Deviation Form | FM4-QM.SLQ052
TMP1-QM.SLQ009 V&V Test Plan Template | TMP2-QM.SLQ052 (Part 1 - V&V Plan)
TMP2-QM.SLQ009 V&V Protocol Template | TMP2-QM.SLQ052 (Part 2 - Test Protocol)
TMP3-QM.SLQ009 V&V Final Report Template | TMP2-QM.SLQ052 (Part 3 - Final Report)
TMP1-QM.SLQ010 Clinical Transfer Checklist Template | TMP3-QM.SLQ052 (Section 2 - Clinical Transfer)
TMP2-QM.SLQ010 Design Transfer Checklist Template | TMP3-QM.SLQ052 (Section 1 - Commercial Transfer)
(New) | FM2-QM.SLQ052 (Design Change Assessment - no predecessor)

---

## SECTION 4.4 - Revisions to Documents Not Obsoleted

This section provides exact find-and-replace edits for every document that references the old design SOPs or needs a design-related substantive revision. Read the current revision of each document before executing any edit to confirm the locate string is still present. All edits are presented as a Locate string and a Replacement string.

Notation: "Current Rev" means the latest released revision at the time DCO095 goes effective. If DCO094 has gone effective before DCO095, increment revisions accordingly.

---

### 4.4.1 QM.SLQ027 Quality Manual

Current revision at this edit: Rev E (or Rev F if DCO094 has gone effective). New revision under DCO095: Rev F (or Rev G).

Background: QM.SLQ027 lists the design control SOP series in three locations: (1) the Customer Focus section references QM.SLQ004, (2) the Design and Development Process section references all seven SOPs individually, and (3) Appendix 1 ISO 13485 Clause Correlations table lists all seven SOPs under clause 7.3. All three locations must be updated. The Medical Device File section in QM.SLQ027 (added in DCO094) already defines the MDF framework; the design-control reference within that section also needs updating.

Edit 1: Customer Focus section

Locate:
Customer needs are identified at the beginning of the design and development process in accordance with QM.SLQ004 Design Control Program.

Replace with (apply Normal body text style):

Customer needs are identified at the beginning of the design and development process in accordance with QM.SLQ052 Design Control SOP.

Edit 2: Design and Development Process section - first paragraph

Locate:
All design and development activities are planned and controlled in accordance with QM.SLQ004 Design Control Program. This procedure specifies the development of project plans that identify the responsibilities and resources for each design and development activity.

Replace with (apply Normal body text style):

All design and development activities are planned and controlled in accordance with QM.SLQ052 Design Control SOP. This procedure specifies the development of design project scope and plan records that identify the responsibilities, resources, pathways, and gate review structure for each design and development activity.

Edit 3: Design and Development Process section - DHF paragraph

Locate:
The DHF includes, but not limited to:

(No change to the DHF content list items. However, remove the parenthetical reference to QM.SLQ009 if present and replace the paragraph that currently ends with a reference to "QM.SLQ009 Design V&V.")

Locate (at the end of the design V&V paragraph):
Design verification and validation activities and requirements are further defined in QM.SLQ009 Design V&V.

Replace with (Normal style):
Design verification and validation activities and requirements are further defined in QM.SLQ052 Design Control SOP, Section 13, and TMP2-QM.SLQ052 V&V Plan, Protocol, and Report.

Edit 4: Design and Development Process - individual SOP references

Locate and replace each of the following in the Design and Development Process section:

Locate: QM.SLQ006 Design Input
Replace with: QM.SLQ052 Design Control SOP (Section 10 - Design Inputs)

Locate: QM.SLQ007 Design Output
Replace with: QM.SLQ052 Design Control SOP (Section 11 - Design Outputs)

Locate: QM.SLQ008 Design Review
Replace with: QM.SLQ052 Design Control SOP (Section 12 - Design Reviews) and FM3-QM.SLQ052

Locate: QM.SLQ010 Design Transfer
Replace with: QM.SLQ052 Design Control SOP (Section 15 - Design Transfer) and TMP3-QM.SLQ052

Edit 5: Appendix 1 ISO 13485 Clause Correlations table - Clause 7.3 row

Locate the row for Clause 7.3 in Appendix 1. The current cell content lists:
QM.SLQ001 Document Control, QM.SLQ004 Design Control Program, QM.SLQ006 Design Input, QM.SLQ007 Design Output, QM.SLQ008 Design Review, QM.SLQ009 Design V&V, QM.SLQ010 Design Transfer, QM.SLQ012 Risk Management

Replace the entire Clause 7.3 cell content with (paste into the table cell, maintaining table cell format):

QM.SLQ052 Design Control SOP (Sections 6-18)
QM.SLQ012 Risk Management SOP
QM.SLQ013 Risk Analysis SOP
FM1-QM.SLQ052 Design Project Scope and Plan
FM2-QM.SLQ052 Design Change Assessment
FM3-QM.SLQ052 Design Review Record
TMP1-QM.SLQ052 Design Input, Output, and Traceability Matrix
TMP2-QM.SLQ052 V&V Plan, Protocol, and Report
TMP3-QM.SLQ052 Design Transfer Checklist

Edit 6: Clause 5.2 row in Appendix 1

Locate the clause 5.2 row. Current content:
QM.SLQ004 Design Control Program

Replace with:
QM.SLQ052 Design Control SOP

Edit 7: Clause 7.1 row in Appendix 1

Locate the clause 7.1 row. Current content includes:
QM.SLQ004 Design Control Program

Replace QM.SLQ004 Design Control Program in that cell with:
QM.SLQ052 Design Control SOP

Edit 8: Clause 7.2 row in Appendix 1

Locate the clause 7.2 row. Current content includes:
QM.SLQ004 Design Control Program

Replace QM.SLQ004 Design Control Program in that cell with:
QM.SLQ052 Design Control SOP

Also add in the clause 7.2 row at the end of the existing list:
QM.SLQ020 Purchasing Controls SOP (Pathway C supplier notification)

Edit 9: Customer Related Processes section

Locate:
These activities are further defined in QM.SLQ036 Sales Order and QM.SLQ004 Design Control Program.

Replace with (Normal style):
These activities are further defined in QM.SLQ036 Sales Order and QM.SLQ052 Design Control SOP.

---

### 4.4.2 QM.SLQ020 Purchasing Controls SOP (HIGH PRIORITY)

Current revision: Rev D. New revision under DCO095: Rev E.

Background: QM.SLQ020 Rev D contains the "wherever possible" language for supplier change notification (Section 6.3.1 equivalent) that is the gap addressed by FDA 483 Observation 2 and CAPA 2025-003. This language must be changed to a mandatory requirement, and a direct link to FM2-QM.SLQ052 Pathway C must be added. QM.SLQ020 also contains several FileHold references that should be updated as part of this revision.

Edit 1: Supplier change notification - mandatory requirement

Locate the following sentence in the Purchasing procedure section:
Contracts, Supplier Agreements, and Purchase Orders shall include, wherever possible, that SILQ be notified of any changes made to the product and/or service prior to those changes becoming effective so that SILQ can determine the impact of changes to the quality of the final product or quality system.

Replace with (apply Normal body text style):

Contracts, Supplier Agreements, and Purchase Orders shall include as a mandatory requirement that suppliers, CMOs, and sub-tier suppliers notify SILQ in writing of any modification to a supplied component, material, manufacturing process, labeling, or packaging that may affect the finished device before that modification is implemented. This notification requirement is not discretionary and may not be waived on the basis that the change is perceived to be minor. Upon receipt of any such notification, Quality Assurance shall immediately initiate a Design Change Assessment under Pathway C of QM.SLQ052 Design Control SOP using FM2-QM.SLQ052, and shall make a documented hold decision per QM.SLQ052 Section 9.2 before continued manufacturing or distribution of the affected device.

Edit 2: Reference Documents section - add QM.SLQ052

Locate the Reference Documents list in the Documents section. After the existing entries, add:

QM.SLQ052     Design Control SOP (Pathway C supplier change trigger)

Edit 3: FileHold references - update to SILQ eQMS

Locate:
Completed purchase orders are to be scanned and imported into the appropriate Purchasing folder within FileHold.

Replace with (Normal style):
Completed purchase orders are to be filed in the SILQ eQMS in the applicable Purchasing Records folder.

Locate:
Closed purchase order is checked in to FileHold.

Replace with:
Closed purchase order is filed in the SILQ eQMS Purchasing Records folder.

Locate:
Purchase order log is checked out of FileHold, updated with closure information and checked back in to FileHold.

Replace with:
Purchase order log is updated with closure information and filed in the SILQ eQMS Purchasing Records folder.

Locate:
Import all completed purchasing records into FileHold; file within appropriate Purchasing folder.

Replace with:
All completed purchasing records are filed in the SILQ eQMS in the applicable Purchasing Records folder.

Edit 4: FileHold in Definitions section

Locate the definition:
FileHold: Software based document management system used to electronically store controlled documents.

Delete this definition entirely (or replace with):
SILQ eQMS: The SILQ proprietary electronic quality management system used to store and control quality records and documents, validated per DC.SLQ002.

Note: If the definitions section already contains an eQMS definition from a previous revision, do not duplicate it. If it does not, add the above definition.

Edit 5: Bump revision

In the document header, change the revision designation from D to E and update the revision history table with a new row noting the effective date and a summary: "Added mandatory supplier change notification requirement with link to QM.SLQ052 Pathway C and FM2-QM.SLQ052; updated FileHold references to SILQ eQMS."

---

### 4.4.3 QM.SLQ013 Risk Analysis SOP

Current revision: Rev B. New revision under DCO095: Rev C.

Note: Confirm before executing that mNC 3 and OFI 2 were not already fully addressed in DCO093. Per the DCO095 redesign outline, risk integration in QM.SLQ013 is addressed by the QM.SLQ052 design change assessment and traceability requirements; the edit to QM.SLQ013 is a reference update and a minimal substantive addition to address mNC 3.

Edit 1: Reference Documents section - replace QM.SLQ004 with QM.SLQ052

Locate in Reference Documents:
QM.SLQ004     Design Control Program

Replace with:
QM.SLQ052     Design Control SOP

Edit 2: Add mandatory risk evaluation for design changes (closes mNC 3)

Locate the section heading for "Procedure: Overall Risk Assessment Process" (or the equivalent section that describes when risk analysis is required). After the existing introductory paragraph for that section, add a new paragraph:

Formatting note: Insert as a new paragraph (Normal style) after the first paragraph of the Procedure: Overall Risk Assessment Process section.

---PASTE START---
Risk evaluation is mandatory for all design changes, whether processed under Pathway A, B, or C of QM.SLQ052 Design Control SOP. A full hazard analysis (PHA or FMEA) is not required for every change, but a documented risk evaluation against the current risk management file is required for all changes to released designs. The risk evaluation must address whether the change introduces any new hazard, alters the probability or severity of any identified hazard, or affects any existing risk control measure. If any of these conditions is identified, the risk management file must be updated before the change is implemented. This requirement closes the gap identified in IA-2025 mNC 3, which found that the procedure did not clearly require documented risk evaluation for design changes where a full hazard analysis was not triggered. The Design Change Assessment (FM2-QM.SLQ052, Section F) is the record for documenting this risk evaluation for Pathway B and C changes.
---PASTE END---

Edit 3: Add traceability requirement (closes OFI 2 if not already addressed in DCO093)

Locate the Risk Management File procedure section. After the existing paragraph on what the Risk Management File contains, add a new paragraph:

Formatting note: Insert as a new paragraph (Normal style) at the end of the Risk Management File section.

---PASTE START---
Risk analysis outputs, including identified hazards, risk mitigations, and verification activities that confirm mitigation effectiveness, shall be traced to the design inputs and verification and validation activities that address them. This traceability is documented in TMP1-QM.SLQ052 (Design Input, Output, and Traceability Matrix), which includes a risk mitigation reference column linking each design input to any hazard or mitigation in the risk management file. This traceability requirement ensures that all safety-critical design inputs are verified, that risk control effectiveness is confirmed through testing, and that any gap in coverage is identified at design review.
---PASTE END---

Edit 4: FileHold reference

Locate:
Risk Management documents are to be scanned and imported into FileHold and filed into the appropriate DHF.

Replace with:
Risk management documents are to be filed in the SILQ eQMS in the applicable DHF location.

---

### 4.4.4 QM.SLQ012 Risk Management SOP

Current revision: Rev B. New revision under DCO095: Rev C.

Note: Confirm before executing that OFI 10 was not already fully addressed in DCO093. The edit below adds the explicit FDA QMS integration linkage called out in OFI 10.

Edit 1: Reference Documents section - replace QM.SLQ004 with QM.SLQ052

Locate in Reference Documents:
QM.SLQ004     Design Control

Replace with:
QM.SLQ052     Design Control SOP

Edit 2: Add FDA QMS integration statement (closes OFI 10 if not already addressed)

Locate the section heading for "Procedure: Overall Risk Management Process." After the introductory paragraph for that section, add a new paragraph:

Formatting note: Insert as a new paragraph (Normal style) after the first paragraph of the Overall Risk Management Process section.

---PASTE START---
Risk management activities are integrated throughout the design control lifecycle per QM.SLQ052 Design Control SOP, Section 14. Specifically: risk management planning is initiated at project planning (Gate 1 of Pathway A); risk analysis is updated throughout design development and at each gate review; risk control verification is confirmed through V&V activities documented in TMP2-QM.SLQ052; all risk analysis outputs are traced to design inputs and V&V activities through TMP1-QM.SLQ052; and risk evaluation is required for every design change under Pathways B and C through FM2-QM.SLQ052. This integration ensures that risk management activities are not conducted in isolation but are embedded in and tracked through design control deliverables, consistent with FDA QMSR expectations and ISO 14971:2019.
---PASTE END---

Edit 3: FileHold reference

Locate:
Risk Management documents are to be scanned and imported into FileHold and filed into the appropriate DHF.

Replace with:
Risk management documents are to be filed in the SILQ eQMS in the applicable DHF location.

---

### 4.4.5 QM.SLQ047 Process Validation SOP

Current revision: Rev A (or Rev B if DCO094 has gone effective). New revision under DCO095: Rev B (or Rev C).

Edit 1: Reference Documents section - replace QM.SLQ004

Locate in Reference Documents:
QM.SLQ004     Design Control Program SOP

Replace with:
QM.SLQ052     Design Control SOP

Note: DCO094 already revised this document to remove the "when necessary" scope language and add documented justification requirements for non-validation. Do not re-edit those substantive changes; this edit is limited to the document reference update only. If DCO094 has not yet gone effective, apply both the DCO094 edits and this reference update in a single revision.

---

### 4.4.6 QM.SLQ025 Quality Planning SOP

Current revision: Rev A. New revision under DCO095: Rev B.

Edit 1: Reference Documents section - replace QM.SLQ004

Locate in Reference Documents:
QM.SLQ004     Design Control Program

Replace with:
QM.SLQ052     Design Control SOP

Edit 2: Procedure body - design control reference

Locate the following text in the Procedure section:
The organization shall establish documented procedures (reference QM.SLQ004 Design Control Program) for design and development processes including:

Replace with (Normal style):
The organization shall establish documented procedures (reference QM.SLQ052 Design Control SOP) for design and development processes including:

---

### 4.4.7 QM.SLQ011 Statistical Techniques WI

Current revision: Rev A (or Rev B if DCO094 has gone effective). New revision under DCO095: Rev B (or Rev C).

Confirm: QM.SLQ011 references QM.SLQ004 in the design V&V context. If DCO094 added the documented justification requirement for non-application of statistical methods and updated regulatory citations, apply only the reference update below. If DCO094 has not gone effective, apply both the DCO094 content changes and this reference update together.

Edit 1: Replace any reference to QM.SLQ004 in the document body

Locate (search for all occurrences in the document):
QM.SLQ004

Replace each occurrence with:
QM.SLQ052

Note: If QM.SLQ011 references QM.SLQ009 (Design V&V SOP) for protocol requirements, replace that reference as well:

Locate (if present):
QM.SLQ009

Replace with:
QM.SLQ052 (Section 13 and TMP2-QM.SLQ052)

---

### 4.4.8 FM1-QM.SLQ018 Management Review Meeting Minutes Form

Current revision: check current version in SILQ eQMS. New revision: next letter.

Edit 1: Replace any reference to QM.SLQ004 through QM.SLQ010 in the form body

Search the form for any checkbox, label, agenda item, or input row that references QM.SLQ004, QM.SLQ005, QM.SLQ006, QM.SLQ007, QM.SLQ008, QM.SLQ009, or QM.SLQ010 by number.

For any such reference found, replace the specific old document number with:
QM.SLQ052

Add a note to any design review status row or design control status input field: "(Under QM.SLQ052 Design Control SOP as of [DCO095 effective date])"

Note: If the current Management Review Minutes form does not explicitly reference the design control SOPs by number, no edit is required. Verify and document the finding.

---

### 4.4.9 QM.SLQ048 Device Master Record SOP

Current revision: Rev A (or Rev B if DCO094 has gone effective). New revision under DCO095: Rev B (or Rev C).

Background: QM.SLQ048 may reference QM.SLQ007 (Design Output) in the context of design outputs becoming the basis for the DMR. The Medical Device File section added in DCO094 already cross-references QM.SLQ027; update the design control reference to QM.SLQ052.

Edit 1: Replace any design SOP reference

Search the document for references to QM.SLQ004, QM.SLQ007, or QM.SLQ010.

For any such reference found, replace:
QM.SLQ004 / QM.SLQ007 / QM.SLQ010

With:
QM.SLQ052 Design Control SOP

Edit 2: Add design output-to-DMR linkage note

If the document contains a paragraph describing design outputs as the basis for the DMR but does not reference QM.SLQ052, add after the existing design-outputs-to-DMR paragraph:

Formatting note: Insert as a new sentence (Normal style) at the end of the design-outputs-to-DMR paragraph.

---PASTE START---
The criteria governing formal control of design outputs and the entry of design output documents into the Device Master Record are defined in QM.SLQ052 Design Control SOP, Section 11.
---PASTE END---

---

### 4.4.10 QM.SLQ029 Device History Record SOP

Current revision: Rev A (or Rev B if DCO094 has gone effective). New revision under DCO095: Rev B (or Rev C).

Edit 1: Replace any design SOP reference

Search the document for any reference to QM.SLQ004 through QM.SLQ010 by number.

For any such reference found, replace the old document number(s) with:
QM.SLQ052 Design Control SOP

Note: If QM.SLQ029 does not reference the old design SOPs by number, no substantive edit is required. Document the verification finding.

---

### 4.4.11 QM.SLQ015 Supplier Quality Assurance SOP

Current revision: check current version. Action: Verify only.

Search the current released version of QM.SLQ015 for any reference to QM.SLQ004, QM.SLQ005, QM.SLQ006, QM.SLQ007, QM.SLQ008, QM.SLQ009, or QM.SLQ010 by number.

If any such reference is found, replace with:
QM.SLQ052 Design Control SOP

If no reference is found, document the verification finding: "QM.SLQ015 [current revision] contains no direct reference to QM.SLQ004 through QM.SLQ010. No edit required under DCO095."

Note: Regardless of the verification finding, consider adding the following sentence to the section of QM.SLQ015 that governs supplier change notification requirements, in alignment with QM.SLQ020 Rev E:

Add (if not already present) to the supplier monitoring or supplier change section of QM.SLQ015:

---PASTE START---
Any notification received from a supplier or CMO of a modification to a component, material, or process that may affect the finished device shall be escalated to Quality Assurance immediately for initiation of a Pathway C Design Change Assessment per QM.SLQ052 Section 9 and FM2-QM.SLQ052. Failure of a supplier to provide timely notification of modifications is a supplier quality nonconformance handled under this procedure.
---PASTE END---

---

### 4.4.12 QM.SLQ016 CAPA SOP

Current revision: check current version. Action: Verify only.

Search the current released version of QM.SLQ016 for any reference to QM.SLQ004, QM.SLQ005, QM.SLQ006, QM.SLQ007, QM.SLQ008, QM.SLQ009, or QM.SLQ010 by number.

If any such reference is found, replace with:
QM.SLQ052 Design Control SOP

If no reference is found, document the verification finding: "QM.SLQ016 [current revision] contains no direct reference to QM.SLQ004 through QM.SLQ010. No edit required under DCO095."

---

### 4.4.13 QM Document Register

Action: Update design control SOP entries.

In the QM Document Register (or document master list), locate the rows for QM.SLQ004, QM.SLQ005, QM.SLQ006, QM.SLQ007, QM.SLQ008, QM.SLQ009, and QM.SLQ010. Change the status column for each to "Obsolete" and add a superseded-by notation of "QM.SLQ052 Rev A." Add a new row for QM.SLQ052 with status "Released" and effective date matching the DCO095 effective date.

Similarly, locate the rows for all 13 old forms and templates (FM1-QM.SLQ004, TMP1-QM.SLQ005, TMP1 and TMP2-QM.SLQ006, TMP1 and TMP2-QM.SLQ007, FM1-QM.SLQ008, FM1 and TMP1 through TMP3-QM.SLQ009, TMP1 and TMP2-QM.SLQ010). Change the status column for each to "Obsolete" with superseded-by notation referencing the applicable new QM.SLQ052 family document.

Add new rows for FM1, FM2, FM3, FM4-QM.SLQ052 and TMP1, TMP2, TMP3-QM.SLQ052 with status "Released" and effective date matching the DCO095 effective date.

---

## SECTION 4.5 - Obsolescence Instructions

### 4.5.1 SOPs to Obsolete

Upon DCO095 approval and the confirmed effective date, the following seven SOPs must be transitioned from Released to Obsolete status in the SILQ eQMS:

QM.SLQ004 Rev B Design Control Program SOP - Obsolete, superseded by QM.SLQ052 Rev A
QM.SLQ005 Rev B Design Project Planning SOP - Obsolete, superseded by QM.SLQ052 Rev A
QM.SLQ006 Rev A Design Input SOP - Obsolete, superseded by QM.SLQ052 Rev A
QM.SLQ007 Rev A Design Output SOP - Obsolete, superseded by QM.SLQ052 Rev A
QM.SLQ008 Rev A Design Review SOP - Obsolete, superseded by QM.SLQ052 Rev A
QM.SLQ009 Rev A Design V&V SOP - Obsolete, superseded by QM.SLQ052 Rev A
QM.SLQ010 Rev A Design Transfer SOP - Obsolete, superseded by QM.SLQ052 Rev A

Procedure in SILQ eQMS:
For each of the seven SOPs: open the current Released version, select the lifecycle transition action "Obsolete," enter the effective date matching the DCO095 effective date, and enter a superseded-by note: "Superseded by QM.SLQ052 Rev A, effective [DCO095 effective date], per DCO095."

### 4.5.2 Forms and Templates to Obsolete

Upon DCO095 approval and the confirmed effective date, the following 13 forms and templates must be transitioned from Released to Obsolete status in the SILQ eQMS:

FM1-QM.SLQ004 Rev A Design Project Scope Form - Obsolete, superseded by FM1-QM.SLQ052 Rev A
TMP1-QM.SLQ005 Rev A Design Project Plan Template - Obsolete, superseded by FM1-QM.SLQ052 Rev A
TMP1-QM.SLQ006 Rev A User Needs Template - Obsolete, superseded by TMP1-QM.SLQ052 Rev A
TMP2-QM.SLQ006 Rev A Product Requirements Template - Obsolete, superseded by TMP1-QM.SLQ052 Rev A
TMP1-QM.SLQ007 Rev A Source Control Spec Template - Obsolete, content folded into QM.SLQ048 and component specifications; no standalone replacement
TMP2-QM.SLQ007 Rev A Design Input-Output Matrix Template - Obsolete, superseded by TMP1-QM.SLQ052 Rev A
FM1-QM.SLQ008 Rev A Design Review Minutes Form - Obsolete, superseded by FM3-QM.SLQ052 Rev A
FM1-QM.SLQ009 Rev A Design V&V Deviation Form - Obsolete, superseded by FM4-QM.SLQ052 Rev A
TMP1-QM.SLQ009 Rev A V&V Test Plan Template - Obsolete, superseded by TMP2-QM.SLQ052 Rev A
TMP2-QM.SLQ009 Rev A V&V Protocol Template - Obsolete, superseded by TMP2-QM.SLQ052 Rev A
TMP3-QM.SLQ009 Rev A V&V Final Report Template - Obsolete, superseded by TMP2-QM.SLQ052 Rev A
TMP1-QM.SLQ010 Rev A Clinical Transfer Checklist Template - Obsolete, superseded by TMP3-QM.SLQ052 Rev A
TMP2-QM.SLQ010 Rev A Design Transfer Checklist Template - Obsolete, superseded by TMP3-QM.SLQ052 Rev A

Procedure in SILQ eQMS:
For each of the 13 forms and templates: open the current Released version, select the lifecycle transition action "Obsolete," enter the effective date matching the DCO095 effective date, and enter a superseded-by note referencing the applicable new QM.SLQ052 family document.

### 4.5.3 Validity of Records Created Under Superseded SOPs

Records, deliverables, and approvals created under QM.SLQ004 through QM.SLQ010 before the DCO095 effective date remain valid quality records and are not required to be reformatted or recreated. This includes:

(a) All DC.SLQ001 deliverables (retrospective valve assessment under CAPA 2025-003): these records were created under QM.SLQ004 Rev B and remain valid. DC.SLQ001 should be closed under the old SOPs.

(b) DC.SLQ002 Phase 0 design review minutes and all Phase 0 deliverables: these records were created under QM.SLQ004 Rev B and remain valid. DC.SLQ002 continues under the transition plan described in Section 4.7.

(c) Any other records created before the DCO095 effective date: remain valid and are retained in the respective DHFs.

### 4.5.4 Timing Note

All obsolescence actions should occur on or after the DCO095 effective date, not before. Publishing QM.SLQ052 Rev A and obsoleting the old SOPs should be simultaneous so there is no gap in design control procedure coverage.

---

## SECTION 4.6 - Finding-Closure Traceability

The table below maps each finding to the specific QM.SLQ052 section, form, or process that closes it. This table should be retained in the DCO095 package in the SILQ eQMS.

### IA-2025 mNC 1 - Nine Sub-Issues (QM.SLQ004 Design Control Program SOP)

Sub-Issue 1: Design changes lack formal control with documented determination of required V&V.
Closed by: QM.SLQ052 Sections 8, 9, 16; FM2-QM.SLQ052 Sections E, G; FM3-QM.SLQ052 Fast-Track section. Every Pathway B and C change now requires documented V&V determination before implementation.

Sub-Issue 2: Absence of defined minimum planning requirements for design and development activities.
Closed by: QM.SLQ052 Section 7.2; FM1-QM.SLQ052 Section C. A defined deliverable table with documented rationale for any omission replaces discretionary planning.

Sub-Issue 3: Plan revisions not change-controlled.
Closed by: QM.SLQ052 Section 7.4; FM1-QM.SLQ052 Section E (Plan Revision Change-Control Log). Section E is a mandatory field on FM1-QM.SLQ052 operationalizing this requirement.

Sub-Issue 4: Conflict resolution authority undefined; no documented rationale or traceable approval required.
Closed by: QM.SLQ052 Section 5.7. Named authority (Director of R&D, QA, RA) with required documentation: conflict description, resolution rationale, and traceable approval by authority and QA.

Sub-Issue 5: Design outputs not consistently required to be formally controlled.
Closed by: QM.SLQ052 Section 11.1. Formal control of all design outputs is stated as a mandatory requirement with explicit criteria for what does and does not require control.

Sub-Issue 6: DHF capture criteria undefined; criteria and responsibility for determining when work product must be captured in DHF not defined.
Closed by: QM.SLQ052 Section 11.3 (DHF Entry Criteria) and Section 18.2 (DHF Contents). Specific criteria for when a document enters the DHF are defined.

Sub-Issue 7: V&V planning optional; not ensuring required V&V activities are formally planned and controlled.
Closed by: QM.SLQ052 Section 13.1; FM1-QM.SLQ052 Section D (V&V Planning Determination field). Section D is a mandatory field on FM1-QM.SLQ052 with required QA approval when V&V is limited or omitted, operationalizing this requirement.

Sub-Issue 8: Validation equivalence criteria and methodology not defined.
Closed by: QM.SLQ052 Section 13.4. Four specific equivalence criteria are defined (materials, manufacturing method, dimensional and mechanical configuration, other safety-relevant characteristics). Documentation reviewed and approved by QA.

Sub-Issue 9: Transfer sign-off via checklist in lieu of final design review.
Closed by: QM.SLQ052 Section 15.2. Explicit requirement that the transfer checklist (TMP3-QM.SLQ052) does not substitute for a final design review (Gate 3 FM3-QM.SLQ052 for Pathway A; Fast-Track FM3-QM.SLQ052 for Pathways B and C).

CAPA 004-2025 Action 5 (mNC 1): DCO095 release completes CAPA 004-2025 Action 5 (revise design control program). The effective date of QM.SLQ052 Rev A is the completion date for Action 5. CAPA 004-2025 effectiveness check 1 (prospective review of all supplier change notifications for 6 months following implementation) is supported by the QM.SLQ052 Pathway C mandatory trigger; the effectiveness check itself proceeds as defined in CAPA 004-2025 Section VI.

### IA-2025 mNC 3 - QM.SLQ013 Risk Analysis SOP

Finding: QM.SLQ013 does not clearly state the mandatory minimum requirement for hazard identification and risk analysis for design changes where systematic risk evaluation must occur even if a full Hazard Analysis is not required.

Closed by: QM.SLQ052 Section 14.2 (Risk Evaluation Required for Every Change); FM2-QM.SLQ052 Section F (Risk Determination field); QM.SLQ013 Rev C (added paragraph in Procedure: Overall Risk Assessment Process per Section 4.4.3 of this guide).

### IA-2025 OFI 2 - QM.SLQ013 Traceability to Design Controls

Finding: QM.SLQ013 does not explicitly require traceability of risk analysis outputs to design inputs and V&V activities.

Closed by: QM.SLQ052 Section 14.3 (Traceability of Risk to Design Inputs and V&V); TMP1-QM.SLQ052 (risk mitigation reference column in traceability matrix); QM.SLQ013 Rev C (added traceability paragraph per Section 4.4.3 of this guide).

### IA-2025 OFI 10 - QM.SLQ012 Risk Management - FDA QMS Expectations

Finding: QM.SLQ012 does not explicitly define linkage to FDA quality system expectations.

Closed by: QM.SLQ052 Section 14 (explicit risk-design integration throughout); QM.SLQ012 Rev C (added FDA QMS integration statement per Section 4.4.4 of this guide).

### FDA 483 Observation 2 and CAPA 2025-003 Supplier Trigger

Finding: SILQ distributed approximately 280 urological catheters after a supplier-initiated valve modification without completing required regulatory processes. Procedures did not mandate that supplier change notifications trigger mandatory design review, risk assessment, and regulatory evaluation.

Closed by: QM.SLQ052 Section 9 (Pathway C - Supplier or CMO-Initiated Change; mandatory trigger; hold decision before continued manufacturing or distribution; regulatory assessment for every Pathway C change); FM2-QM.SLQ052 Sections B, D, F, G, H (all required assessment elements for Pathway C); QM.SLQ020 Rev E Section 6.3.1 equivalent (mandatory supplier notification requirement, link to QM.SLQ052 Pathway C and FM2-QM.SLQ052).

DCO095 completes the CAPA 2025-003 design-control corrective action (procedure revision). Design-control retraining (CAPA 2025-003 effectiveness confirmation) is planned as a separate training project and is out of scope for DCO095. The training project should cover QM.SLQ052 Rev A and replaces the previously planned retraining on QM.SLQ004 through QM.SLQ006.

### 2026 Quality Plan Design Action Items

Supplier Modification Trigger in Design Control: Closed by QM.SLQ052 Section 9 (Pathway C mandatory trigger). The 2026 Quality Plan action item "Revise QM.SLQ004, QM.SLQ005, and QM.SLQ006 to add an explicit requirement that any notification of a supplier-initiated component or process modification triggers mandatory design review, risk assessment, and regulatory evaluation prior to continued manufacturing" is satisfied by QM.SLQ052 as a whole, replacing the three individual procedure revisions with a consolidated, stronger requirement.

Medical Device File Framework: Closed by QM.SLQ052 Section 18.3 (Medical Device File Framework), which ties the DHF to the DMR (QM.SLQ048) and DHR (QM.SLQ029) under ISO 13485:2016 clause 4.2.3. The MDF framework was also implemented in QM.SLQ027 and QM.SLQ048 under DCO094.

Design Control Procedure Revisions (CAPA 2025-003 Corrective Action): Closed by DCO095 release of QM.SLQ052 Rev A.

CAPA 2025-003 Corrective Action Completion: DCO095 completes the procedural corrective action. The effectiveness confirmation (retraining of all applicable employees) is a separate training activity and is the CAPA 2025-003 effectiveness confirmation, not within DCO095 scope.

Design-Control Retraining (CAPA 2025-003): As noted in the 2026 Quality Plan and CAPA 2025-003, retraining of all applicable employees on design control policies is required. With DCO095, the training content is QM.SLQ052 Rev A (and FM1 through TMP3-QM.SLQ052), not the old QM.SLQ004 through QM.SLQ006 series. The training project lead (Ethan Rao) should update the training plan to reflect QM.SLQ052 as the basis for the CAPA 2025-003 effectiveness training. Successful completion of the training constitutes the CAPA 2025-003 effectiveness confirmation. Training delivery is out of scope for DCO095.

### Summary

Note: DCO095 release closes CAPA 004-2025 Action 5 (design control program revision for mNC 1). The effective date of QM.SLQ052 Rev A is the Action 5 completion date. CAPA 004-2025 effectiveness check 1 proceeds per the CAPA record after DCO095 goes effective.

---

## SECTION 4.7 - DC.SLQ002 Phase 2 Closure Statement

DC.SLQ002 (SilqQMS EDMS Transition, initiated under QM.SLQ032) is organized in four phases: Phase 1A (procedure mapping), Phase 1B (procedure revision preparation), Phase 2 (procedure revision execution), Phase 3 (data migration from FileHold), and Phase 4 (training).

Phase 1B and Phase 2 of DC.SLQ002 included as deliverables the revision of all FileHold-referencing procedures and all design-control SOPs. DCO095 completes the design-control portion of that commitment:

(a) QM.SLQ052 Rev A contains zero FileHold references. All DHF storage references in QM.SLQ052 direct records to the SILQ eQMS.

(b) FM1 through TMP3-QM.SLQ052 and FM4-QM.SLQ052 contain zero FileHold references.

(c) QM.SLQ020 Rev E (edited in Section 4.4.2) removes the remaining FileHold references from the Purchasing Controls SOP.

Accordingly, the design-document items in DC.SLQ002 Phase 1B and Phase 2 are complete with DCO095 release. The remaining open phases of DC.SLQ002 are:

Phase 3 - Data migration: Moving existing DHF, DMR, and other legacy records from FileHold into the SILQ eQMS. This activity is out of scope for DCO095 and is managed as a separate DC.SLQ002 project deliverable.

Phase 4 - Training: Post-migration training on the SILQ eQMS for all users. This activity is out of scope for DCO095 and is managed as a separate DC.SLQ002 project deliverable.

DCO095 itself does not trigger the DC.SLQ002 closure process; it satisfies the design-procedure portion of DC.SLQ002 Phase 2. The DC.SLQ002 Project Leader should update the DC.SLQ002 project plan to mark Phase 2 design-document deliverables as complete, referencing DCO095.

---

End of DCO095 Design Control Editing Guide.

Prepared by: QMS management agent, June 30, 2026.
All document numbers, revision levels, and change descriptions are based on the source documents read as part of this agent session and are verified against the SilqQMS project folder readable texts.
