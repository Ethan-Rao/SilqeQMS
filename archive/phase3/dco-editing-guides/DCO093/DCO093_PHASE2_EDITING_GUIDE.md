# DCO093 Phase 2 — Detailed Document Editing Guide

**Prepared by:** QMS management agent
**Date:** June 9, 2026
**Design Project:** DC.SLQ002 — Silq eQMS EDMS Transition
**DCO Number:** DCO093
**For use by:** Ethan Rao (Document Originator)

---

## About This Guide

This guide provides line-by-line, section-by-section editing instructions for the nine documents in the DCO093 Phase 2 revision package. Every change is supported by: (1) verbatim current text so the originator can locate the exact passage in Word, (2) exact replacement or addition text ready to paste, and (3) the regulatory or quality system basis for the change.

**Three drivers apply to every document:**
- **Driver 1 — EDMS Transition (DC.SLQ002):** Replace FileHold references with Silq eQMS equivalents
- **Driver 2 — Audit Compliance (IA-2025/CAPA004):** Implement mNC and applicable OFI findings
- **Driver 3 — 2026 Quality Plan:** Implement identified procedure additions

**A fourth, document-specific driver applies to QM.SLQ016 (CAPA SOP), its form, and the CAPA Log:**
- **Driver 4 — CAPA Process Streamlining (review of CAPA 001-003):** Separate the timeliness of the corrective/preventive action from the timeliness of the verification of effectiveness; allow QA to investigate and determine root cause up front rather than waiting for CAPA Team approval; eliminate the redundant Section IV; and revise the CAPA Log accordingly. See Document 3 for the full revision.

---

## DCO093 Document Package Table

*(For use on FM1-QM.SLQ001 Rev B DCO form)*

| Document Title | Document Number | Current Rev | Target Rev | Primary Change Drivers |
|---|---|---|---|---|
| Risk Management SOP | QM.SLQ012 | B | C | DC.SLQ002 EDMS Transition; OFI #1 (Risk Management Report consolidation); OFI #10 (FDA QMS linkage); 2026 Quality Plan (post-production trigger criteria); OFI #8 |
| Risk Management Plan Template | TMP1-QM.SLQ012 | B | No revision required | — |
| Risk Analysis SOP | QM.SLQ013 | B | C | DC.SLQ002 EDMS Transition; mNC #3 (mandatory risk eval for design changes); OFI #2 (traceability to design controls); OFI #8 |
| PHA Template | TMP1-QM.SLQ013 | B | No revision required | — |
| Hazards Analysis Table Template | TMP2-QM.SLQ013 | B | No revision required | — |
| FMEA Worksheet Template | TMP3-QM.SLQ013 | A | No revision required | — |
| CAPA SOP | QM.SLQ016 | C | D | DC.SLQ002 EDMS Transition; OFI #8; CAPA Process Streamlining (review of CAPA001-003): action vs. effectiveness timeliness separation, root cause moved to enhanced Section II, Section IV elimination, log restructure |
| CAPA Report Form | FM1-QM.SLQ016 | A | B | CAPA Process Streamlining: eliminate Section IV, enhance Section II, renumber Sections V-VII to IV-VI, add action and effectiveness on-time fields |
| SILQ CAPA Log | (controlled log) | — | Revised | CAPA Process Streamlining: align columns with six-section form; track action completion timeliness separately from effectiveness-check timeliness |
| Management Review SOP | QM.SLQ018 | A | B | DC.SLQ002 EDMS Transition; OFI #3 (annual input coverage); OFI #9 (Management Representative designation); OFI #8 |
| Management Review Meeting Minutes | FM1-QM.SLQ018 | A | B | OFI #3 (annual input coverage field) |
| Product Complaint System SOP | QM.SLQ021 | D | E | DC.SLQ002 EDMS Transition; mNC #6 (CAPA escalation criteria); 2026 Quality Plan (non-investigation rationale, escalation pathway); OFI #8 |
| Product Complaint File Form | FM1-QM.SLQ021 | B | No revision required | — |
| Complaint Response Letter Template | TMP1-QM.SLQ021 | A | No revision required | — |
| Medical Device Reporting SOP | QM.SLQ022 | B | C | No FileHold references confirmed; OFI #5 (reportability methodology, UDI); 2026 Quality Plan (QMSR framing); OFI #8 (HIPAA typo correction) |
| eMDR Submission Work Instruction | QM.SLQ023 | A | B | DC.SLQ002 EDMS Transition; software/URL currency advisory |
| Protection of Confidential Patient Information SOP | QM.SLQ028 | A | B | DC.SLQ002 EDMS Transition; mNC #8 (internet prohibition removal, secure transmission, RBAC, data breach) |
| Advisory Notices and Recalls SOP | QM.SLQ030 | A | B | DC.SLQ002 EDMS Transition; OFI #6 (recall metrics trending); 2026 Quality Plan (QMSR framing); OFI #8 |
| Recall Report to FDA Form | FM1-QM.SLQ030 | A | No revision required | — |
| FSCA Report (EU) Form | FM2-QM.SLQ030 | A | No revision required | — |
| Field Safety Notice Form | FM3-QM.SLQ030 | A | No revision required | — |
| Advisory and Recall Notices Distribution Log | FM4-QM.SLQ030 | A | No revision required | — |

---

## Document 1: QM.SLQ012 Risk Management SOP (Rev B → Rev C)

### Summary of Changes Required

This revision requires two FileHold reference replacements (one in Definitions, one in the Risk Management File procedure section); two substantive additions for audit compliance (OFI #1 — consolidating Risk Management Report content, and OFI #10 — adding explicit FDA QMS linkage to Scope); one Quality Plan addition establishing specific post-production trigger criteria for Risk Management File revision; and confirmation of regulatory reference currency (no QSR/legacy 820 references found in the document). The associated template TMP1-QM.SLQ012 requires no revision.

---

### 1. FileHold Reference Replacements

**Reference 1 of 2**
- **Location:** Section 5 General Definitions
- **Current text (verbatim):** `FileHold: Software based document management system used to electronically store controlled documents.`
- **Replace with:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`
- **Notes:** Remove the "FileHold" entry and replace with the "Silq eQMS" entry. Maintain alphabetical ordering of definitions if applicable.

**Reference 2 of 2**
- **Location:** Section 8 Procedure: Risk Management File — last sub-bullet under "The Risk Management File is a part of the appropriate Design History File."
- **Current text (verbatim):** `Risk Management documents are to be scanned and imported into FileHold and filed into the appropriate DHF.`
- **Replace with:** `Risk Management documents are to be uploaded to Silq eQMS Admin Docs, Design History Files, within the applicable product or project Risk Management File folder.`
- **Notes:** This is the only bullet under that sub-heading. The replacement specifies the exact Silq eQMS filing path.

---

### 2. Audit Compliance Edits

**Finding: OFI #1 — Risk Management Report consolidation (recommended)**
- **Location:** Section 6 Procedure: Risk Management Report — the bullet list beginning "The report contains sufficient information to ensure:"
- **Current text (verbatim):** The list contains three sub-bullets:
  1. `The activities defined in the Risk Management Plan have been appropriately implemented;`
  2. `The overall residual risk is acceptable;`
  3. `Appropriate methods are in place to collect and review relevant production and post-production information (see Section 14).`
- **Required change:** Add a fourth sub-bullet at the end of this list.
- **Exact new text to add:**
  > `The Risk Management Report explicitly summarizes the outputs of all risk analysis activities performed for the device or product family (including Master Hazard Analysis/PHA, FMEA(s), and any supplemental analyses), and documents the overall residual risk acceptability and benefit-risk determination at the system level, confirming that residual risks are acceptable in accordance with the criteria defined in the Risk Management Plan.`
- **Regulatory basis:** ISO 14971:2019 clause 9; IA-2025 OFI #1

---

**Finding: OFI #10 — Linkage to FDA QMS expectations (recommended)**
- **Location:** Section 2 Scope — add a new paragraph or sub-bullet following the existing scope statements.
- **Current text (verbatim — last existing scope bullet):** `In addition, all risk management activities performed by approved subcontractors for, or in support of, design control projects at SILQ must be in compliance with the requirements defined in this procedure.`
- **Required change:** Add the following new paragraph immediately following the above statement (as a new ### level bullet or new paragraph, consistent with document formatting):
- **Exact new text to add:**
  > `In accordance with FDA Quality Management System Regulation (QMSR) expectations, risk management activities at SILQ are integrated with design control activities (QM.SLQ004 through QM.SLQ010), verification and validation planning, CAPA processes (QM.SLQ016), and production and post-production information review. Risk management is not a standalone activity; it informs and is informed by all relevant quality system processes.`
- **Regulatory basis:** QMSR 21 CFR Part 820 §820.10(b); IA-2025 OFI #10

---

### 3. Quality Plan Additions

**Quality Plan Action: Post-Production Risk File Update Triggers**
- **Location:** Section 7 Procedure: Production and Post-Production Information — insert after the sentence: `SILQ evaluates the information for impact on previous risk management activities and provides it as an input back into the risk management process, revising risk management deliverables such as the Master Hazard Analysis as needed.`
- **Current text (verbatim — anchor sentence):** `SILQ evaluates the information for impact on previous risk management activities and provides it as an input back into the risk management process, revising risk management deliverables such as the Master Hazard Analysis as needed.`
- **Required addition:** Insert the following new sub-section immediately after the anchor sentence above:
  > **Risk File Revision Trigger Criteria:** A formal revision to the Risk Management File (including the Master Hazard Analysis or applicable FMEA) is required when any of the following trigger criteria are met based on post-production information review:
  > (a) A new hazard is identified that is not currently documented in the applicable risk analysis;
  > (b) Post-market data (including complaint trends, MDR data, or CAPA outcomes) indicate that the probability rating of an existing hazard should increase based on observed field experience;
  > (c) A complaint or adverse event results in an upward change in the risk category of a previously evaluated hazard;
  > (d) A design change or supplier change affects a hazard or risk mitigation that was previously documented in the Risk Management File.
  >
  > If none of these trigger criteria are met based on the current review period's information, continued monitoring until the next scheduled annual review is acceptable. The result of the trigger criteria evaluation shall be documented as part of the periodic post-production information review record.
- **Notes:** Format trigger criteria (a)–(d) as a lettered sub-list consistent with document style. The "Risk File Revision Trigger Criteria" heading may be formatted as bold text or a sub-heading depending on document style.

---

### 4. Regulatory Reference Updates (OFI #8)

**Confirmation:** After reading QM.SLQ012 B in full, no "QSR," "21 CFR 820," or "Quality System Regulation" references were found in the Reference Documents section or document body. The document cites ISO 14971:2019, ISO/TR 24971:2020, and other non-820 references. **No regulatory reference update is required for QM.SLQ012.**

---

### 5. Definition Section Updates

- **Remove:** `FileHold: Software based document management system used to electronically store controlled documents.`
- **Add:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`
- **QSR/QMSR check:** No "QSR" abbreviation present in the Abbreviations section. No update required.

---

### 6. Associated Forms

**TMP1-QM.SLQ012 B — Risk Management Plan Template**
After reading the full template: no FileHold references are present anywhere in the document body, section headings, or instructional text. The template is a planning document with placeholder fields and does not contain any document management system filing instructions.
**Determination: No revision required.**

---

## Document 2: QM.SLQ013 Risk Analysis SOP (Rev B → Rev C)

### Summary of Changes Required

This revision requires two FileHold reference replacements (one in Definitions, one in the Risk Management File procedure); two mandatory mNC #3 additions establishing that systematic risk evaluation for design changes is required; one recommended OFI #2 addition establishing traceability of risk outputs to design controls; and confirmation that regulatory references (ISO 14971:2019, ISO/TR 24971:2020) are current and require no update. The three associated templates require no revision.

---

### 1. FileHold Reference Replacements

**Reference 1 of 2**
- **Location:** Section 4 General Definitions
- **Current text (verbatim):** `FileHold: Software based document management system used to electronically store controlled documents.`
- **Replace with:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`

**Reference 2 of 2**
- **Location:** Section 10 Procedure: Risk Management File — sub-bullet under "The Risk Management File is included as part of the appropriate Design History File."
- **Current text (verbatim):** `Risk Management documents are to be scanned and imported into FileHold and filed into the appropriate DHF.`
- **Replace with:** `Risk Management documents are to be uploaded to Silq eQMS Admin Docs, Design History Files, within the applicable product or project Risk Management File folder.`

---

### 2. Audit Compliance Edits

**Finding: mNC #3 — Mandatory risk evaluation for design changes (MANDATORY)**

*Addition 1 of 2 — Section 2 Scope*
- **Location:** Section 2 Scope — insert as a new sub-bullet after the existing sub-bullet: `The scope of risk analysis activities for any given product or project is defined in the Risk Management Plan or DCO, as directed by Risk Management process (QM.SLQ012).`
- **Current text (verbatim — anchor):** `The scope of risk analysis activities for any given product or project is defined in the Risk Management Plan or DCO, as directed by Risk Management process (QM.SLQ012).`
- **Exact new text to add (insert as new sub-bullet immediately following):**
  > `For design changes, systematic risk evaluation must occur and be documented regardless of whether a full Hazard Analysis or new Risk Management Plan is required. At minimum, the design change must be evaluated to determine: (a) whether any new hazards are introduced by the change; (b) whether the probability or severity of existing hazards is affected by the change; and (c) whether previously implemented risk mitigations remain effective after the change. This evaluation must be documented and retained either in the Risk Management File or within the applicable DCO record.`
- **Regulatory basis:** ISO 14971:2019 clause 10; IA-2025 mNC #3

*Addition 2 of 2 — Section 5 Procedure: Overall Risk Assessment Process*
- **Location:** Section 5 Procedure: Overall Risk Assessment Process — insert after the paragraph: `Various methods may be chosen for risk analysis. The methods described below are the primary methods recommended for SILQ products, however do not represent the only options allowed. Other risk analysis methods are allowed to be used as necessary and when defined in the applicable risk management plan.`
- **Current text (verbatim — anchor):** `Various methods may be chosen for risk analysis. The methods described below are the primary methods recommended for SILQ products, however do not represent the only options allowed.  Other risk analysis methods are allowed to be used as necessary and when defined in the applicable risk management plan.`
- **Exact new text to add (insert as new paragraph immediately following):**
  > `For design changes processed through the DCO system, a documented risk evaluation is mandatory regardless of project scope or planning status. The responsible R&D/Engineering or QA personnel shall document the change's impact on previously identified hazards and confirm that no new unmitigated risks are introduced by the change. This evaluation shall be referenced within the applicable DCO and retained in the Risk Management File.`
- **Regulatory basis:** ISO 14971:2019 clause 10; IA-2025 mNC #3

---

**Finding: OFI #2 — Traceability of risk analysis outputs to design controls (recommended)**
- **Location:** Section 6 Procedure: Preliminary Hazard Analysis — insert after the final step: `Lastly, summarize the hazard analysis results. Discuss the impact of the mitigations on the entirety of identified risk, determining if all feasible control methods were exhausted and were sufficient to make the residual risks meet the criteria for risk acceptability. If there are any high residual risks, provide additional discussion on the cause for these residual risks.`
- **Current text (verbatim — anchor):** `Lastly, summarize the hazard analysis results. Discuss the impact of the mitigations on the entirety of identified risk, determining if all feasible control methods were exhausted and were sufficient to make the residual risks meet the criteria for risk acceptability. If there are any high residual risks, provide additional discussion on the cause for these residual risks.`
- **Exact new text to add (insert as new sub-bullet or paragraph immediately following):**
  > `Upon completion of the PHA or Master Hazard Analysis, all identified risk mitigations that require design or process verification shall be cross-referenced to the corresponding design inputs documented in the Design History File and to the applicable verification and validation activities planned or completed under QM.SLQ004 through QM.SLQ010. This traceability shall be documented within the risk analysis document itself (e.g., in the Mitigation Reference column of the Hazard Analysis Table using TMP2-QM.SLQ013) or in a separate Risk Management File traceability table referenced therein.`
- **Regulatory basis:** ISO 14971:2019 clause 7.4; IA-2025 OFI #2

---

### 3. Quality Plan Additions

No Quality Plan action items are assigned specifically to QM.SLQ013. The post-production trigger criteria addition is assigned to QM.SLQ012 (see Document 1). No additions required here.

---

### 4. Regulatory Reference Updates (OFI #8)

**Confirmation:** After reading QM.SLQ013 B in full, the Reference Documents section cites ISO 14971:2019 and ISO/TR 24971:2020 — both are current editions. No "QSR," "21 CFR 820," or "Quality System Regulation" references were found in the document. **No regulatory reference update is required for QM.SLQ013.**

---

### 5. Definition Section Updates

- **Remove:** `FileHold: Software based document management system used to electronically store controlled documents.`
- **Add:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`
- **QSR/QMSR check:** No "QSR" abbreviation in the Abbreviations section. No update required.

---

### 6. Associated Forms

**TMP1-QM.SLQ013 B — Preliminary Hazard Analysis Template**
After reading the full template: no FileHold references are present. The template contains instructional placeholders and table structures only.
**Determination: No revision required.**

**TMP2-QM.SLQ013 B — Hazards Analysis Table Template**
After reading the full template: no FileHold references are present. The template is a structured Excel table with column headers and rating definitions.
**Determination: No revision required.**

**TMP3-QM.SLQ013 A — FMEA Worksheet Template**
After reading the full template: no FileHold references are present. The template contains DFMEA and PFMEA worksheet structures with rating definitions.
**Determination: No revision required.**

---

## Document 3: QM.SLQ016 CAPA SOP (Rev C → Rev D)

### Summary of Changes Required

QM.SLQ016 receives the most substantive process revision in DCO093. In addition to the EDMS transition and regulatory reference updates, this revision restructures the CAPA workflow itself based on a detailed review of the three executed CAPAs (CAPA 001-2025, 002-2025, 003-2025). The four drivers for this document are:

- Driver 1 — EDMS Transition (DC.SLQ002): two FileHold reference replacements (one in Definitions, one in CAPA Records Retention).
- Driver 2 — Audit Compliance (IA-2025): no mNC is directly assigned to QM.SLQ016; OFI #8 regulatory reference update applies.
- Driver 3 — 2026 Quality Plan: no separate action item is assigned to QM.SLQ016.
- Driver 4 — CAPA Process Streamlining (review of CAPA 001-003): the substantive revision described below.

The streamlining revision accomplishes four objectives requested by the originator:

1. It separates the timeliness of the corrective/preventive action from the timeliness of the verification of effectiveness. The action plan (within 30 days) and action implementation (target 90 days, extensions permitted with documented justification) determine the CAPA's on-time status. The verification of effectiveness is judged separately and its evaluation period is not constrained to 90 days.
2. It eliminates the artificial sequential gate that required the CAPA Team to approve the proposal before root cause investigation could proceed. QA now performs the investigation and root cause determination up front, in an enhanced Section II, so the CAPA Team dispositions the proposal with full knowledge of the root cause.
3. It eliminates Section IV (Investigation and Determination of Root Cause) from the form and folds its content into the enhanced Section II, reducing the form from seven sections to six. Review of CAPA 001-003 confirmed that QA already performed the substantive root cause work in Section II in practice, making the standalone Section IV redundant.
4. It revises the CAPA Log to track action-completion timeliness separately from effectiveness-check timeliness.

The reasoning behind the timeliness model is grounded in the executed CAPAs: action implementation in CAPA 001, 002, and 003 each extended beyond 90 days with documented later target dates, and the effectiveness evaluation period in CAPA 001 spans a full year (Nov 2025 to Nov 2026). A rigid mandate that the entire CAPA, including effectiveness, close within 90 days is neither realistic nor compliant with how effectiveness must be demonstrated.

This document section is organized as: (1) FileHold replacements; (2) regulatory reference update; (3) definition updates; (4) the major workflow and timeliness revision to the SOP body; (5) the associated form revision (FM1-QM.SLQ016 Rev A to Rev B); and (6) the associated CAPA Log revision.

---

### 1. FileHold Reference Replacements

**Reference 1 of 2**
- **Location:** Section 4 General Definitions
- **Current text (verbatim):** `FileHold:  Software based document management system used to electronically store controlled documents.`
- **Replace with:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`
- **Notes:** Note the double-space after the colon in the current text — this is a formatting artifact; use single space in replacement.

**Reference 2 of 2**
- **Location:** Section 7 Procedure: CAPA Records Retention — sub-bullet at the end of the section
- **Current text (verbatim):** `Records are to be scanned and imported into FileHold and filed within appropriate CAPA folder.`
- **Replace with:** `Records are to be uploaded to Silq eQMS Admin Docs, CAPA Records.`

---

### 2. Regulatory Reference Update (OFI #8)

**Update 1 of 1**
- **Location:** Section 3 Reference Documents
- **Current text (verbatim):** `21 CFR 820 	Quality System Regulation (820.100 – Corrective and Preventive Action)`
- **Replace with:** `21 CFR Part 820 	Quality Management System Regulation (QMSR) (820.100 – Corrective and Preventive Action)`
- **Notes:** Also confirm during document review whether any additional 820 section number references appear in the document body. None were identified in the readable text review, but confirm on the original Word file.

---

### 3. Definition Section Updates

- **Remove:** `FileHold:  Software based document management system used to electronically store controlled documents.`
- **Add:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`
- **QSR/QMSR check:** The Abbreviations section contains only "CAPA" and "QMS." No "QSR" abbreviation is present. No update required.

**Two new General Definitions to add** (insert in the General Definitions sub-section, maintaining alphabetical order if the document is alphabetized):

- **Add:** `Action Plan: The documented set of corrective and/or preventive actions, assigned responsibilities, and estimated completion dates established to eliminate the root cause(s) identified during the QA investigation.`
- **Add:** `Effectiveness Evaluation Period: The period of time, defined and approved within the effectiveness check plan, over which objective evidence is collected to determine whether the implemented corrective/preventive action(s) have been effective. This period is established based on the nature of the action and the data required to demonstrate effectiveness, and is independent of the action plan and action implementation timeframes.`

---

### 4. Major Workflow and Timeliness Revision (Driver 4)

This is the substantive process revision. Each change below is a copy/paste find-and-replace or a deletion. Apply them in the order presented to keep section numbering consistent.

**Change 4.1 — Responsibilities: QA performs the investigation/root cause; Owner implements action and effectiveness**
- **Location:** Responsibilities section — the bullet describing the CAPA Owner's activities.
- **Current text (verbatim):** `The CAPA Owner is responsible for a variety of activities, including interim containment actions identified, root cause investigation, corrective/preventive action(s), and verification of effectiveness.  In addition, the CAPA Owner is responsible for communications to contract manufacturers, suppliers, and other service providers of CAPA affecting them and working to obtain corrective action replies in a timely manner.`
- **Replace with:**
  > `Quality Assurance is responsible for performing the initial investigation and root cause determination for each CAPA proposal, documented in Section II of FM1-QM.SLQ016, prior to CAPA Team disposition. The CAPA Owner, once assigned by the CAPA Team, is responsible for developing and implementing the corrective/preventive action plan, identifying any interim containment actions, and planning and completing the verification of effectiveness. In addition, the CAPA Owner is responsible for communications to contract manufacturers, suppliers, and other service providers of CAPA affecting them and working to obtain corrective action replies in a timely manner.`
- **Basis:** Streamlining objective 2; eliminates the requirement to defer root cause investigation until after CAPA Team approval.

**Change 4.2 — Responsibilities: QA records separate timeliness in the CAPA Log**
- **Location:** Responsibilities section — the bullet describing QA administration of the CAPA process.
- **Current text (verbatim):** `Quality Assurance is responsible for administering various elements of the CAPA process including CAPA # assignment, completion and maintenance of a Corrective and Preventive Action Log, CAPA activity reports, status of open CAPAs and trending for Management Review, and maintenance/retention of CAPA documentation.`
- **Replace with:**
  > `Quality Assurance is responsible for administering various elements of the CAPA process including CAPA # assignment, completion and maintenance of a Corrective and Preventive Action Log, CAPA activity reports, status of open CAPAs and trending for Management Review, and maintenance/retention of CAPA documentation. Quality Assurance records, in the CAPA Log, the on-time status of corrective/preventive action completion separately from the on-time status of the verification of effectiveness.`

**Change 4.3 — Three main phases of the CAPA process (redefine to separate action completion from effectiveness)**
- **Location:** Procedure: General Requirements — the "There are three main phases in the CAPA process:" list and its three sub-items.
- **Current text (verbatim):**
  > `There are three main phases in the CAPA process:`
  > `Initiation – A CAPA request is generated and assigned a CAPA number.`
  > `Completed – Root cause investigation and corrective/preventive action plan complete, and effectiveness check acceptance criteria are defined and approved.`
  > `Closed –Effectiveness check(s) are complete and found acceptable.`
- **Replace with:**
  > `There are three main phases in the CAPA process:`
  > `Initiation – A CAPA request is generated and assigned a CAPA number, Quality Assurance performs the initial investigation and root cause determination, and the CAPA Team dispositions the request (approved or rejected).`
  > `Action Complete – The corrective/preventive action plan has been documented and all planned actions have been implemented, and the effectiveness check plan and acceptance criteria are defined and approved. The on-time status of the CAPA is determined at this milestone, based on the action plan and action implementation timeframes, independent of the verification of effectiveness.`
  > `Closed – The verification of effectiveness is complete and the action(s) found acceptable, and the CAPA Team has approved closure.`

**Change 4.4 — Section II: enhance to include the QA investigation, root cause determination, and recommendation**
- **Location:** Procedure: Completing the CAPA Report Form — the paragraph describing Section II.
- **Current text (verbatim):** `Section II:  Quality Assurance (QA) will evaluate the problem/condition description to determine the validity of the CAPA. QA will either recommend approval of  the CAPA for completion or rejection with reason for rejection.`
- **Replace with:**
  > `Section II: Quality Assurance (QA) evaluates the problem/condition described in Section I, performs the investigation, and determines the root cause to the extent reasonably possible before the proposal is presented to the CAPA Team. QA need not wait for CAPA Team approval to investigate the root cause. Section II documents: (1) the investigation activity, investigative approach, data, and results; (2) the root cause determination; (3) a risk/hazard analysis summary if a potential or apparent safety issue is indicated; (4) a determination of whether the Risk Management Report needs to be updated; and (5) QA's recommendation to either approve the proposal for corrective/preventive action or reject it with rationale. The individual completing the investigation enters name and date when the investigation is complete, and indicates whether supporting data is attached. If additional investigation is necessary after CAPA Team disposition, the assigned CAPA Owner may supplement Section II; any additions made after original signatures shall be initialed and dated.`
- **Basis:** Streamlining objectives 2 and 3; consolidates the former Section IV content into Section II.

**Change 4.5 — Section III: reframe as disposition with root cause already established, and assignment of the Owner for action implementation**
- **Location:** Procedure: Completing the CAPA Report Form — Section III, first sub-bullet.
- **Current text (verbatim):** `The CAPA team will evaluate the request and QA’s recommendation.  The CAPA Team will indicate if the CAPA request is ‘approved’ or ‘rejected’.  If rejected, enter reason in space provided; and the CAPA Team signs the form.`
- **Replace with:**
  > `The CAPA Team will evaluate the request together with QA's Section II investigation, root cause determination, and recommendation. Because root cause has already been investigated and documented in Section II, the CAPA Team's disposition is a decision to commit resources to corrective/preventive action implementation. The CAPA Team will indicate if the CAPA request is approved or rejected. If rejected, enter reason in the space provided and the CAPA Team signs the form. If approved, the CAPA Team identifies the CAPA Owner responsible for implementing the action plan and verification of effectiveness, and the CAPA Team signs the form.`

**Change 4.6 — Delete Section IV (Investigation and Determination of Root Cause) from the SOP body**
- **Location:** Procedure: Completing the CAPA Report Form — the entire Section IV block.
- **Delete the following text in its entirety (verbatim):**
  > `Section IV Investigation and Determination of Root Cause: The issue will be investigated to the root cause level by the owner in a timely manner.`
  > `List the details of the root cause analysis including investigative approach (or reference to applicable documents), data, and conclusions of the investigation.`
  > `Risk/Hazard Analysis:  If a risk/hazard analysis is indicated due to a potential or apparent safety issue, the analysis will be performed and used in determination of appropriate action plan.`
  > `Risk Management Report:  Determine and indicate if the Risk Management Report needs to up be updated.`
  > `Analysis Completed By: The CAPA owner will enter name and date (may be typed into form) when the investigation is complete.`
- **Notes:** The regulatory requirement to investigate and document the cause of nonconformity (21 CFR 820.100 / ISO 13485 8.5.2) is fully preserved — it now lives in the enhanced Section II (Change 4.4). Do not delete this content without first confirming Change 4.4 has been applied.

**Change 4.7 — Renumber Section V to Section IV (heading and references)**
- **Location:** Procedure: Completing the CAPA Report Form — Section V Corrective Action or Preventive Action Plan.
- **Current text (verbatim — heading line):** `Section V Corrective Action or Preventive Action Plan: Determine the best plans to eliminate the root cause of the defect.   Appropriate corrective/preventive actions that may result from analysis may include (but are not limited to):`
- **Replace with:** `Section IV Corrective Action or Preventive Action Plan: Determine the best plans to eliminate the root cause of the defect.   Appropriate corrective/preventive actions that may result from analysis may include (but are not limited to):`
- **Also replace (verbatim):** `Section V:  Document the corrective/preventive action(s).  Number the actions sequentially; describe the action(s) to be taken; assign responsibility for implementation of action(s); enter the estimated date the action will be completed.`
- **With:** `Section IV:  Document the corrective/preventive action(s).  Number the actions sequentially; describe the action(s) to be taken; assign responsibility for implementation of action(s); enter the estimated date the action will be completed.`
- **Also replace (verbatim):** `Date Action Plan Implementation Complete:  Enter the date that all identified actions in the plan are complete.  The CAPA owner signs and dates section V.`
- **With:** `Date Action Plan Implementation Complete:  Enter the date that all identified actions in the plan are complete.  The CAPA owner signs and dates section IV.`

**Change 4.8 — Revise the action timeliness sub-bullets (the core of the requested change)**
- **Location:** Procedure: Completing the CAPA Report Form — the three sub-bullets currently under the Section V (now Section IV) action plan documentation step.
- **Current text (verbatim):**
  > `The corrective/preventive action plan should be determined and documented within 30 calendar days of CAPA initiation.`
  > `The estimated date of completion should be completed within 90 calendar days of CAPA initiation.`
  > `If required, the estimated date of completion may be extended. The justification for extension shall be documented.`
- **Replace with:**
  > `The corrective/preventive action plan should be determined and documented within 30 calendar days of CAPA initiation.`
  > `The corrective/preventive action(s) should be implemented in accordance with the documented action plan, with a target completion within 90 calendar days of CAPA initiation. The 90-day target applies to implementation of the action(s) and does not include the verification of effectiveness, which is evaluated separately under Section V.`
  > `If required, the estimated date of completion may be extended. The justification for the extension shall be documented and approved prior to the original estimated completion date.`
  > `On-time determination: A CAPA is considered on time with respect to its corrective/preventive action when the action plan is documented within 30 calendar days of initiation and all planned actions are implemented by the estimated completion date documented in the action plan, including any extension that has been documented with justification and approved prior to the original due date. The on-time status of the corrective/preventive action is recorded in the CAPA Log and is determined independently of the verification of effectiveness.`
- **Basis:** Requested differentiation between action completion and effectiveness evaluation. The 30-day plan and 90-day implementation targets are retained as targets, with documented extensions explicitly permitted; effectiveness is removed from the action on-time determination.

**Change 4.9 — Revise the "CAPA considered completed" statement**
- **Location:** Procedure: Completing the CAPA Report Form — the standalone statement following the Section V (now Section IV) content.
- **Current text (verbatim):** `The CAPA will be considered completed when the root cause investigation and corrective/preventive action plan is complete, and effectiveness check acceptance criteria are defined.`
- **Replace with:**
  > `The corrective/preventive action is considered complete (Action Complete phase) when all planned actions have been implemented in accordance with the action plan and the effectiveness check plan and acceptance criteria have been defined and approved. Completion of the corrective/preventive action does not require completion of the verification of effectiveness; the effectiveness evaluation is conducted over the Effectiveness Evaluation Period defined in Section V and the CAPA is closed thereafter.`

**Change 4.10 — Renumber Section VI to Section V and clarify the effectiveness evaluation period is independent of the action timeframe**
- **Location:** Procedure: Completing the CAPA Report Form — Section VI Verification of Effectiveness.
- **Current text (verbatim — heading line):** `Section VI Verification of Effectiveness:  Appropriate effectiveness checks will be defined to ensure the validity of the action in eliminating the root cause.  Acceptance criteria for effectiveness checks must be established prior to collection of effectiveness check data.`
- **Replace with:**
  > `Section V Verification of Effectiveness:  Appropriate effectiveness checks will be defined to ensure the validity of the action in eliminating the root cause.  Acceptance criteria for effectiveness checks must be established prior to collection of effectiveness check data. The Effectiveness Evaluation Period is defined and approved as part of the effectiveness check plan, is selected based on the nature of the action and the data required to demonstrate effectiveness, and is not constrained by the 30-day action plan target or the 90-day action implementation target. The Effectiveness Evaluation Period may extend well beyond the action implementation timeframe (for example, a defined period of complaint or field monitoring). The timeliness of the verification of effectiveness is assessed separately from the corrective/preventive action on-time determination; the effectiveness check is considered on time when it is completed within 30 calendar days following the close of the defined Effectiveness Evaluation Period.`
- **Also replace the next sub-bullet (verbatim):** `Section VI:  The respective CAPA owner documents the plan and time schedule / evaluation period for completing the effectiveness evaluation.  Number the effectiveness checks to correspond with actions listed in Section V; describe the method(s) to be used to confirm effectiveness; define the acceptance criteria.`
- **With:** `Section V:  The respective CAPA owner documents the plan and time schedule / evaluation period for completing the effectiveness evaluation.  Number the effectiveness checks to correspond with actions listed in Section IV; describe the method(s) to be used to confirm effectiveness; define the acceptance criteria.`

**Change 4.11 — Renumber Section VII to Section VI**
- **Location:** Procedure: Completing the CAPA Report Form — Section VII CAPA Team Approval to Close CAPA.
- **Current text (verbatim — heading line):** `Section VII CAPA Team Approval to Close CAPA:  Upon confirmation of effectiveness, the CAPA will be closed. The CAPA form will contain or reference all associated information and documentation.`
- **Replace with:** `Section VI CAPA Team Approval to Close CAPA:  Upon confirmation of effectiveness, the CAPA will be closed. The CAPA form will contain or reference all associated information and documentation.`
- **Also replace (verbatim):** `Section VII: When the CAPA team determines that the CAPA report should be closed, they will sign/date.  When all required signatures are complete, the CAPA is considered to be closed.`
- **With:** `Section VI: When the CAPA team determines that the CAPA report should be closed, they will sign/date.  When all required signatures are complete, the CAPA is considered to be closed.`

**Change 4.12 — Revise the CAPA Log procedure minimum-information list**
- **Location:** Procedure: CAPA Log — first sentence describing minimum log content.
- **Current text (verbatim):** `Quality Assurance is to create and maintain a CAPA Log containing the following minimum information: CAPA #, Initiation Date, Part or Document #, Initiated By, Date CAPA Complete, Date CAPA Closed and Closed By.`
- **Replace with:**
  > `Quality Assurance is to create and maintain a CAPA Log containing the following minimum information: CAPA #, Initiation Date, Part or Document #, Initiated By, Date the QA Investigation and Root Cause (Section II) is complete, Date the CAPA Team Disposition (Section III) is complete, Date the Action Plan is documented, Date Action Implementation is complete, the on-time status of the corrective/preventive action, the defined Effectiveness Evaluation Period, Date the Verification of Effectiveness (Section V) is complete, the on-time status of the verification of effectiveness, Date CAPA Closed, and Closed By.`
- **Notes:** This aligns the SOP's stated minimum log content with the revised CAPA Log structure described in section 6 below and with the separation of action timeliness from effectiveness timeliness.

---

### 5. Associated Form — FM1-QM.SLQ016 CAPA Report Form (Rev A → Rev B)

The form revision implements the same restructure as the SOP. The form is converted from seven sections to six: Section IV (Investigation and Determination of Root Cause) is eliminated and its content is folded into an enhanced Section II; Sections V, VI, and VII are renumbered to IV, V, and VI. Two small timeliness indicator fields are added.

**Determination: Revision required — Rev A → Rev B.** (The prior guide listed this form as "no revision required"; that determination is superseded by Driver 4.)

**Form Change 1 — Replace the Section II table block (enhance to absorb root cause content)**
- **Current Section II header row (verbatim):** `SECTION II:  INITIAL INVESTIGATION BY QA`
- **Replace the Section II header and its single content row with the following field set.** Rebuild the Section II table so that the section header reads `SECTION II:  QA INVESTIGATION, ROOT CAUSE DETERMINATION, AND RECOMMENDATION` and the body contains the following rows (row owner label remains QUALITY):
  > `INVESTIGATION (INCLUDE ACTIVITY, INVESTIGATIVE APPROACH, DATA, AND RESULTS):`
  > `ROOT CAUSE DETERMINATION:`
  > `RISK / HAZARD ANALYSIS SUMMARY (SAFETY ISSUE ONLY):`
  > `DOES THE RISK MANAGEMENT REPORT NEED TO BE UPDATED:   YES   NO (THERE ARE NO NEW FAILURE MODES, INCREASE IN INCIDENCE, OR HAZARDS)`
  > `QA RECOMMENDATION:   RECOMMEND APPROVAL FOR CORRECTIVE/PREVENTIVE ACTION   RECOMMEND REJECTION (INCLUDE RATIONALE):`
  > `INVESTIGATION COMPLETED BY: _______________   DATE: _______________   DATA ATTACHED:   YES   NO`
- **Notes:** The four content elements imported from the former Section IV are: ROOT CAUSE DETERMINATION; RISK / HAZARD ANALYSIS SUMMARY; DOES THE RISK MANAGEMENT REPORT NEED TO BE UPDATED; and INVESTIGATION COMPLETED BY / DATE / DATA ATTACHED. The INVESTIGATION field and the QA RECOMMENDATION field are the retained and reworded Section II elements.

**Form Change 2 — Delete the Section IV table block in its entirety**
- **Delete the entire table beginning with the header (verbatim):** `SECTION IV: INVESTIGATION AND DETERMINATION OF ROOT CAUSE`
- This includes the open-text root cause row, the `RISK / HAZARD ANALYSIS SUMMARY (SAFETY ISSUE ONLY):` row, the `DOES THE RISK MANAGEMENT REPORT NEED TO BE UPDATED:` row, and the `ANALYSIS COMPLETED BY: / DATE: / DATA ATTACHED:` row. All of these elements are now captured in the enhanced Section II per Form Change 1.

**Form Change 3 — Renumber the Section V table to Section IV and add an action on-time indicator**
- **Current header (verbatim):** `SECTION V: CORRECTIVE ACTION or PREVENTIVE ACTION PLAN`
- **Replace with:** `SECTION IV: CORRECTIVE ACTION or PREVENTIVE ACTION PLAN`
- **Add two rows** to this section near the existing `DATE ACTION PLAN IMPLEMENTATION COMPLETE:` row:
  > `DATE ACTION PLAN DOCUMENTED (TARGET: WITHIN 30 DAYS OF INITIATION): _______________`
  > `ACTION IMPLEMENTATION ON TIME:   YES   NO   EXTENSION APPROVED (JUSTIFICATION ATTACHED)`
- **Notes:** The existing `ACTION PLAN SUMMARY COMPLETED BY: / DATE:` and `DATE ACTION PLAN IMPLEMENTATION COMPLETE:` fields are retained. The two added fields make the action on-time determination explicit on the form and feed the CAPA Log.

**Form Change 4 — Renumber the Section VI table to Section V and add effectiveness period and on-time indicators**
- **Current header (verbatim):** `SECTION VI:  VERIFICATION OF EFFECTIVENESS`
- **Replace with:** `SECTION V:  VERIFICATION OF EFFECTIVENESS`
- **Add two rows** to this section near the existing `EFFECTIVENESS PLAN COMPLETED BY:` row:
  > `EFFECTIVENESS EVALUATION PERIOD (DEFINED PER ACTION; NOT CONSTRAINED BY THE 90-DAY ACTION TARGET): _______________`
  > `EFFECTIVENESS CHECK COMPLETED ON TIME (WITHIN 30 DAYS AFTER CLOSE OF EVALUATION PERIOD):   YES   NO`

**Form Change 5 — Renumber the Section VII table to Section VI**
- **Current header (verbatim):** `SECTION VII:  CAPA TEAM APPROVAL to CLOSE CAPA – ACTIONS EFFECTIVE`
- **Replace with:** `SECTION VI:  CAPA TEAM APPROVAL to CLOSE CAPA – ACTIONS EFFECTIVE`

**Implementation note for in-process CAPAs:** CAPA 001-2025, 002-2025, and 003-2025 were initiated under the Rev C SOP and Rev A form and may be completed under the version in effect at their initiation. New CAPAs initiated after the effective date of QM.SLQ016 Rev D and FM1-QM.SLQ016 Rev B use the revised six-section form. The CAPA Log tracks all CAPAs regardless of the version under which they were initiated.

---

### 6. Associated Log — SILQ CAPA Log

The CAPA Log requires revision to reflect the renumbered six-section form and to track the corrective/preventive action timeliness separately from the effectiveness-check timeliness. The current log header row (Sheet headers) is:

`CAPA # YY-XXX | Summary of Issue / Opportunity | Initiated By | Initiation Date | Part or Document # | CAPA Status | Date CAPA Section 1 Complete | Date CAPA Section 2 Complete | Date CAPA Section 3 Complete | Date CAPA Section 4 Complete | Date CAPA Section 5 Complete | Date CAPA Section 6 Complete | Date CAPA Closed | Closed By | On time/Late | Notes`

**Replace the header row with the following column set:**

`CAPA # YY-XXX | Summary of Issue / Opportunity | Initiated By | Initiation Date | Part or Document # | CAPA Status | Date Section I Complete | Date Section II (QA Investigation and Root Cause) Complete | Date Section III (CAPA Team Disposition) Complete | Date Action Plan Documented | Date Action Implementation Complete | Action Plan On Time (Yes / No / Extension Approved) | Effectiveness Evaluation Period | Date Section V (Effectiveness Check) Complete | Effectiveness Check On Time (Yes / No) | Date CAPA Closed | Closed By | Notes`

**Column mapping (old to new), for migrating the three existing CAPA rows:**

| Old column | New column |
|---|---|
| Date CAPA Section 1 Complete | Date Section I Complete |
| Date CAPA Section 2 Complete (QA initial investigation) and Date CAPA Section 4 Complete (root cause) | Consolidate into: Date Section II (QA Investigation and Root Cause) Complete |
| Date CAPA Section 3 Complete | Date Section III (CAPA Team Disposition) Complete |
| Date CAPA Section 5 Complete (action plan) | Split into: Date Action Plan Documented and Date Action Implementation Complete |
| Date CAPA Section 6 Complete (effectiveness) | Date Section V (Effectiveness Check) Complete |
| On time/Late (single column) | Split into: Action Plan On Time and Effectiveness Check On Time |

**Notes on populating the on-time columns:**
- "Action Plan On Time" is determined per Change 4.8: Yes if the plan was documented within 30 days of initiation and all actions were implemented by the documented estimated completion date (including any approved, justified extension); record "Extension Approved" where a documented extension applies; otherwise No.
- "Effectiveness Check On Time" is determined per Change 4.10: Yes if the effectiveness check was completed within 30 calendar days following the close of the defined Effectiveness Evaluation Period; otherwise No. The length of the Effectiveness Evaluation Period itself never makes a CAPA late.
- Using CAPA 001-2025 as a worked example: the Effectiveness Evaluation Period is "17 Nov 2025 to 17 Nov 2026"; "Effectiveness Check On Time" would be assessed after 17 Nov 2026 and is independent of the action implementation, which is tracked under the action columns.

**Archival location (originator decision required):** The current log states `The CAPA Log is archived on a secure network server.` (this text is in the SOP, Procedure: CAPA Log section, not in the spreadsheet). If the CAPA Log is transitioning to Silq eQMS as part of DC.SLQ002, update that SOP sentence to: `The CAPA Log is maintained in Silq eQMS Admin Docs, CAPA Records.` If the log remains on a separate network server or dedicated database, retain the existing language and no change is needed for this line.

---

## Document 4: QM.SLQ018 Management Review SOP (Rev A → Rev B)

### Summary of Changes Required

This revision requires two FileHold reference replacements (one in Definitions, one in Records/Documentation); three regulatory reference updates (OFI #8) including a QSR → QMSR update in the Purpose section and a reference document update; and two substantive audit compliance additions — OFI #3 (documenting annual input coverage in meeting minutes) and OFI #9 (formally designating the Management Representative role). The associated form FM1-QM.SLQ018 requires a minor addition to support OFI #3.

---

### 1. FileHold Reference Replacements

**Reference 1 of 2**
- **Location:** Section 5 General Definitions (under General Definitions sub-heading)
- **Current text (verbatim):** `FileHold:  Software based document management system used to electronically store controlled documents.`
- **Replace with:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`

**Reference 2 of 2**
- **Location:** Section 7 Procedure: Records/Documentation — last bullet
- **Current text (verbatim):** `Management Representative will scan and import all MR records into appropriate FileHold folder(s).`
- **Replace with:** `Management Representative will upload all MR records to Silq eQMS Admin Docs, QM Documents, Management Review Records.`

---

### 2. Audit Compliance Edits

**Finding: OFI #3 — Annual input coverage documentation (recommended)**
- **Location:** Section 6 Procedure — insert after the running agenda bullet list. The list ends with: `### Review of Resource Requirements and current staffing levels.`
- **Current text (verbatim — anchor, last item in the running agenda list):** `Review of Resource Requirements and current staffing levels.`
- **Exact new text to add (insert as a new paragraph immediately after the running agenda bullet list):**
  > `Because SILQ conducts Management Reviews on an annual basis, the meeting record (FM1-QM.SLQ018) must include, or reference attached documentation confirming, that all required review inputs listed in this section were addressed during the calendar year covered by the review. If any required input was not available or not addressed during the annual review, the meeting minutes shall include a documented justification and identify when the input will be reviewed.`
- **Regulatory basis:** ISO 13485:2016 clause 5.6.2; IA-2025 OFI #3

---

**Finding: OFI #9 — Management Representative role designation (recommended)**
- **Location:** Section 5 Responsibilities — add to or modify the description of the Quality Management Representative. The current text reads:
- **Current text (verbatim):** `The Quality Management Representative shall chair the Management Review (MR) meetings and is responsible for providing data and/or trend analysis of product complaints, product or manufacturing nonconformities, corrective and preventive action data, internal audits, and other quality related topics that affect the Quality System.  The Quality Management Representative is also responsible to communicate information to the organization regarding the suitability and effectiveness of the Quality Management System.`
- **Required change:** Insert the following text as a new paragraph immediately before the existing Quality Management Representative description above:
- **Exact new text to add:**
  > `The Management Representative is formally designated by senior management and the designation is documented in the Quality Manual (QM.SLQ027). The Management Representative is responsible for ensuring that QMS processes are established, implemented, and maintained; reporting to senior management on QMS performance; and promoting awareness of customer and regulatory requirements throughout the organization, consistent with ISO 13485:2016 Section 5.5.2.`
- **Notes:** This addition precedes the existing functional responsibilities description and establishes the formal designation context. The existing functional responsibilities paragraph is retained unchanged.
- **Regulatory basis:** ISO 13485:2016 clause 5.5.2; IA-2025 OFI #9

---

### 3. Quality Plan Additions

No Quality Plan action items are assigned specifically to QM.SLQ018 beyond the OFI #3 compliance edit addressed above.

---

### 4. Regulatory Reference Updates (OFI #8)

**Update 1 of 2**
- **Location:** Section 1 Purpose — second bullet
- **Current text (verbatim):** `To ensure the activities conducted during Management Review (MR) encompass and fulfill the FDA Quality System Regulation (QSR) and ISO 13485:2016 requirements for periodic Management Review of the Quality System.`
- **Replace with:** `To ensure the activities conducted during Management Review (MR) encompass and fulfill the FDA Quality Management System Regulation (QMSR) and ISO 13485:2016 requirements for periodic Management Review of the Quality System.`

**Update 2 of 2**
- **Location:** Section 3 Reference Documents
- **Current text (verbatim):** `21 CFR 820	Quality System Regulation (820.20 – Management Responsibility)`
- **Replace with:** `21 CFR Part 820	Quality Management System Regulation (QMSR) (820.20 – Management Responsibility)`

**Abbreviations check:** The document's Abbreviations section contains only "CAPA: Corrective Action and Preventive Action" and "MR: Management Review." No "QSR" abbreviation is present. No abbreviation update is required.

---

### 5. Definition Section Updates

- **Remove:** `FileHold:  Software based document management system used to electronically store controlled documents.`
- **Add:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`
- **QSR in body text:** The "QSR" reference in the Purpose section is addressed under regulatory reference updates above. No standalone "QSR:" definition entry was identified in the Definitions or Abbreviations sections.

---

### 6. Associated Forms

**FM1-QM.SLQ018 A — Management Review Meeting Minutes**
After reading the full form: no FileHold references are present. The form is a structured meeting minutes document with agenda checkboxes, topic discussion sections, and action item tracking. It does not contain any document management system filing instructions.

**However, to support OFI #3 (annual input coverage documentation):** The current form provides checkboxes for agenda items reviewed at the meeting but does not include a field or confirmation statement that all required annual inputs were addressed. To operationalize the OFI #3 addition in QM.SLQ018, the following change to FM1-QM.SLQ018 is recommended:

**Required change to FM1-QM.SLQ018:**
- **Location:** After the "Conclusions:" section checkboxes (which assess QMS effectiveness, suitability, and adequacy), add a new field or check item.
- **Exact new text to add:**
  > **Annual Review Input Coverage Confirmation:**
  > `[ ] All required Management Review inputs listed in QM.SLQ018 Section 6 were addressed during this calendar year's review (or through documented review at this meeting).`
  > `[ ] One or more required inputs were not addressed. Justification and schedule for review: ___________________________________`
- **Revision level:** FM1-QM.SLQ018 should be revised from Rev A to Rev B.
- **Determination: Revision required — Rev A → Rev B.**

---

## Document 5: QM.SLQ021 Product Complaint System SOP (Rev D → Rev E)

### Summary of Changes Required

This is the most extensively revised document in DCO093. It requires: two FileHold reference replacements; one mandatory mNC #6 addition establishing specific CAPA escalation criteria for complaint trends; two Quality Plan additions (non-investigation rationale requirement and event escalation cross-reference table); two regulatory reference updates including the HIPAA typo correction; and a note regarding the Complaint Log archival location. The associated form FM1-QM.SLQ021 requires no revision. TMP1-QM.SLQ021 requires no revision.

---

### 1. FileHold Reference Replacements

**Reference 1 of 2**
- **Location:** Section 4 General Definitions
- **Current text (verbatim):** `FileHold: Software based document management system used to electronically store controlled documents.`
- **Replace with:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`

**Reference 2 of 2**
- **Location:** PCF Quality Records Retention section (last section of the document) — last sub-bullet
- **Current text (verbatim):** `Records are to be scanned and imported into FileHold by QA and filed within appropriate complaint folder.`
- **Replace with:** `Records are to be uploaded to Silq eQMS Admin Docs, Complaint Records.`

---

### 2. Audit Compliance Edits

**Finding: mNC #6 — Complaint trend escalation to CAPA (MANDATORY)**
- **Location:** Section 7 Procedure — Complaint Trending sub-section. Insert after the existing trend report bullet list. The current list ends with: `#### Complaint System Aging`
- **Current text (verbatim — anchor, last item in trend list):** `Complaint System Aging`
- **Exact new text to add (insert as a new labeled sub-section immediately after the "Complaint System Aging" bullet):**
  > **Complaint Trend Escalation to CAPA:** When complaint trend analysis identifies any of the following conditions, QA shall initiate a CAPA in accordance with QM.SLQ016 within 30 calendar days of identification:
  > (a) any single complaint category with three or more occurrences within a rolling 12-month period;
  > (b) any complaint category demonstrating an increase in frequency across two or more consecutive quarterly trend reports;
  > (c) any complaint involving a patient death or serious injury;
  > (d) any complaint trend identified by the Management Review committee as requiring corrective action.
  >
  > The rationale for initiating or not initiating a CAPA for each identified trend shall be documented in the quarterly trend report.
- **Regulatory basis:** ISO 13485:2016 clause 8.2.2 and 8.5.2; QMSR 21 CFR Part 820 §820.35; IA-2025 mNC #6
- **Note to originator:** This sub-section establishes objective, measurable escalation criteria that can be applied by QA personnel without subjective interpretation. Criteria (a) and (b) are quantitative threshold-based; criteria (c) and (d) are event-triggered.

---

### 3. Quality Plan Additions

**Quality Plan Action 1: Complaint Non-Investigation Rationale (MANDATORY, QMSR 820.35)**
- **Location:** Section 7 Procedure — Complaint Investigation sub-section. Insert after the sub-bullet: `If the complaint investigation requires longer than 30 days, the justification for extending the timeframe shall be documented and a new timeframe proposed.`
- **Current text (verbatim — anchor):** `If the complaint investigation requires longer than 30 days, the justification for extending the timeframe shall be documented and a new timeframe proposed.`
- **Exact new text to add (insert as new labeled sub-section immediately following):**
  > **Complaints Not Requiring Investigation:** If QA determines that a complaint does not require investigation, the rationale for the non-investigation decision shall be documented in FM1-QM.SLQ021 and retained in the complaint file. Non-investigation decisions are subject to QA management review. Documented rationale must reference applicable criteria (e.g., erroneous information, device not manufactured by SILQ, or confirmed user error with no device performance issue and no death or serious injury) consistent with the requirements of QMSR section 820.35.
- **Notes:** FM1-QM.SLQ021 Rev B (the current form revision) already includes the field: "IS A COMPLAINT INVESTIGATION REQUIRED? YES ... NO — IF NO, EXPLAIN:" in Section IV. This field satisfies the documentation requirement when the originator is aware of the QMSR 820.35 obligation. The SOP addition ensures the requirement is formally stated in the procedure.

---

**Quality Plan Action 2: Event Escalation and Regulatory Pathway Cross-Reference**
- **Location:** Insert as a new sub-section within the main Procedure body of QM.SLQ021. Recommended placement: immediately after the Complaint Trend Escalation to CAPA text added above (mNC #6), and before the "Procedure: Complaint Log" section. Format this as a new headed sub-section (bold heading) within the Procedure section — do not create a new top-level numbered SOP section. No renumbering of top-level sections is needed; the Complaint Log remains the next section.
- **Exact new section text:**
  > **Event Escalation and Regulatory Pathway Cross-Reference**
  >
  > The following table summarizes the escalation pathway from complaint receipt to regulatory action. Refer to the referenced procedures for full requirements.
  >
  > | Event Type | Responsible Procedure | Decision Owner | Timing |
  > |---|---|---|---|
  > | Initial complaint receipt and investigation | QM.SLQ021 (this procedure) | QA | Within 30 calendar days |
  > | MDR reportability determination | QM.SLQ022 Medical Device Reporting | QA/RA | Within 20 days (5 days if urgent) |
  > | eMDR submission to FDA | QM.SLQ023 eMDR Submission Work Instruction | Regulatory Affairs | Within 30 days (5 days if urgent) |
  > | Advisory notice determination | QM.SLQ030 Advisory Notices and Recalls | QA + Executive Management | Based on risk analysis findings |
  > | Field Safety Corrective Action / Recall initiation | QM.SLQ030 Advisory Notices and Recalls | QA + Executive Management | Within 10 working days of FSCA initiation (FDA report) |
  > | CAPA initiation (complaint trend) | QM.SLQ016 Corrective and Preventive Action | QA | Per complaint trend escalation criteria above |

---

### Advisory Note: Complaint Log Archival Location

**Current text (verbatim):** `The Complaint Log is archived on a secure network server.`

**Originator decision required:** Same logic as the CAPA Log in QM.SLQ016. If the Complaints and Reportable Events Log is transitioning to Silq eQMS under DC.SLQ002, update to: `The Complaints and Reportable Events Log is maintained in Silq eQMS Admin Docs, Complaint Records.` If the log remains on a separate network server, retain existing language.

---

### 4. Regulatory Reference Updates (OFI #8)

**Update 1 of 2**
- **Location:** Section 3 Reference Documents
- **Current text (verbatim):** `21 CFR 820.198	Complaint Files`
- **Replace with:** `21 CFR Part 820 (QMSR) Section 820.198	Complaint Files`

**Update 2 of 2 — HIPAA Typo Correction**
- **Location:** Section 4 Abbreviations
- **Current text (verbatim):** `HIPPA:  Health Insurance Portability and Accountability Act`
- **Replace with:** `HIPAA:  Health Insurance Portability and Accountability Act`
- **Notes:** "HIPPA" is a long-standing persistent typo for "HIPAA." This is a spelling correction only; no substantive change to the definition. No mNC or OFI is associated with this — it is simply correct practice. The same typo exists in QM.SLQ022 B and should be corrected there as well (see Document 6).

---

### 5. Definition Section Updates

- **Remove:** `FileHold: Software based document management system used to electronically store controlled documents.`
- **Add:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`
- **HIPAA typo correction:** Correct "HIPPA" to "HIPAA" in Abbreviations section (see above).

---

### 6. Associated Forms

**FM1-QM.SLQ021 B — Product Complaint File Form**
After reading the full form: no FileHold references are present. The current form (Rev B) already includes a field in Section IV for non-investigation documentation: "IS A COMPLAINT INVESTIGATION REQUIRED? YES ... NO — IF NO, EXPLAIN:" which satisfies the QMSR 820.35 documentation requirement when the procedure directs its use. No additional form fields are required.
**Determination: No revision required.**

**TMP1-QM.SLQ021 A — Complaint Response Letter Template**
After reading the full template: no FileHold references are present. The template is a letter template with placeholder fields for response text and a complaint information summary table.
**Determination: No revision required.**

---

## Document 6: QM.SLQ022 Medical Device Reporting SOP (Rev B → Rev C)

### Summary of Changes Required

**FileHold status confirmed:** After reading QM.SLQ022 B in full, no FileHold references are present anywhere in the document — not in the Definitions section, Quality Records section, or document body. No EDMS transition edit is required for this document for the FileHold driver.

This revision requires: a HIPAA typo correction in Abbreviations; two substantive OFI #5 additions (reportability decision framework and UDI requirement); one Quality Plan addition (QMSR regulatory framing statement); and confirmation that regulatory citations are current (references to 21 CFR Parts 803 and 806 are correct and retained). No legacy 820 or QSR references were identified.

---

### 1. FileHold Reference Replacements

**No FileHold references confirmed in QM.SLQ022 B.** No EDMS transition edit required.

---

### 2. Audit Compliance Edits

**Finding: OFI #5, Gap 1 — Reportability Decision Methodology (recommended)**
- **Location:** Section 6.2 Determination of Reportability (or the "Determination of Reportability" sub-section within Section 6) — insert after the last item in the current MDR trigger criteria list. The list ends with: `FDA has made a written request for the submission of a 5-day report involving a particular type of medical device or type of event.`
- **Current text (verbatim — anchor, last MDR trigger criterion):** `FDA has made a written request for the submission of a 5-day report involving a particular type of medical device or type of event.`
- **Exact new text to add (insert as new labeled paragraph immediately following the trigger criteria list):**
  > **MDR Reportability Decision Framework:** When evaluating whether a complaint requires an MDR report, QA/RA shall apply the following sequential decision framework:
  > (1) Was the device manufactured or imported by SILQ? If No — MDR not required. If Yes — proceed to (2).
  > (2) Is there information reasonably suggesting the device may have caused or contributed to a death or serious injury, or that a reportable malfunction occurred? If No — MDR not required; document rationale in FM1-QM.SLQ021 Section 3. If Yes — proceed to (3).
  > (3) Does a qualified person (per 21 CFR 803.3 definition) confirm the assessment? If the determination requires clinical expertise beyond internal resources, consult SILQ's Medical Safety Consultant or designee.
  >
  > The full determination shall be documented in FM1-QM.SLQ021 Section 3 regardless of outcome.
- **Regulatory basis:** 21 CFR Part 803; IA-2025 OFI #5

---

**Finding: OFI #5, Gap 2 — UDI in MDR Submissions (recommended)**
- **Location:** Section 6.3 Reporting MDRs to FDA (or the "Reporting MDRs to FDA" sub-section within Section 6) — insert after the sentence: `The eMDR shall be prepared in accordance with the work instructions provided in QM.SLQ023 eMDR Submission Work Instruction.`
- **Current text (verbatim — anchor):** `The eMDR shall be prepared in accordance with the work instructions provided in QM.SLQ023 eMDR Submission Work Instruction.`
- **Exact new text to add (insert as new sub-bullet or sentence immediately following):**
  > `In accordance with 21 CFR 803.52(e), the MDR report shall include the Unique Device Identifier (UDI) for the affected device where available. QA/RA shall confirm that the correct UDI is included in the applicable section of the MedWatch 3500A form (FDA Form 3500A, Section D) prior to submission.`
- **Regulatory basis:** 21 CFR 803.52(e); IA-2025 OFI #5

---

### 3. Quality Plan Additions

**Quality Plan Action: Regulatory Reporting QMSR Framing**
- **Location:** Section 1 Purpose — add as a new sub-bullet after the last existing Purpose statement
- **Current text (verbatim — last Purpose statement):** `This procedure applies to all marketed medical devices that have been manufactured by, or for, SILQ.` *(Note: this is in Section 2 Scope — if no purpose bullet is present to anchor to, add at the end of Section 1 Purpose or the beginning of Section 2 Scope.)*
- **Exact new text to add:**
  > `This procedure is implemented as part of SILQ's Quality Management System in compliance with the applicable regulatory requirements of the FDA Quality Management System Regulation (QMSR), 21 CFR Part 820 Section 820.10(b). SILQ's MDR reporting activities under this procedure satisfy the applicable regulatory reporting requirements imposed by 21 CFR Part 803 as referenced in the QMSR supplementary provisions framework.`
- **Notes:** If added to Section 2 Scope, insert as the first sub-bullet of that section. If added to Section 1 Purpose, insert as a new sub-bullet at the end of the Purpose section. Either placement is acceptable; choose based on document formatting consistency.

---

### 4. Regulatory Reference Updates (OFI #8)

**Confirmation:** The Reference Documents section cites "US FDA Medical Device Reporting (MDR) Regulations, 21 CFR Parts 803 and 806" — these are current and correct regulatory citations. No legacy 21 CFR Part 820 or "QSR" language was found in the document body. **No regulatory reference update is required.**

**Typo correction in Abbreviations:**
- **Current text (verbatim):** `HIPPA:  Health Insurance Portability and Accountability Act`
- **Replace with:** `HIPAA:  Health Insurance Portability and Accountability Act`
- **Notes:** Same "HIPPA" → "HIPAA" correction as in QM.SLQ021.

---

### 5. Definition Section Updates

No FileHold definition present to remove. No Silq eQMS definition needed (no FileHold driver applies). HIPAA typo correction as noted above.

---

### 6. Associated Forms

QM.SLQ022 uses FM1-QM.SLQ021 (Product Complaint File) as a referenced form (owned by QM.SLQ021). No forms are owned by QM.SLQ022. No form revisions required under this document.

---

## Document 7: QM.SLQ023 eMDR Submission Work Instruction (Rev A → Rev B)

### Summary of Changes Required

This revision requires two FileHold reference replacements (one in Definitions, one at the end of the Section 6 Procedure) and two practical compliance advisories: a software currency note at the start of Section 6, and a URL review advisory. There are no audit mNCs/OFIs directly assigned and no Quality Plan additions. The document does not reference 21 CFR Part 820 and requires no regulatory reference update.

---

### 1. FileHold Reference Replacements

**Reference 1 of 2**
- **Location:** Section 4 General Definitions
- **Current text (verbatim):** `FileHold:  Software based document management system used to electronically store controlled documents.`
- **Replace with:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`

**Reference 2 of 2**
- **Location:** Section 6 Procedure — last step of the procedure (currently the final sentence of the entire document)
- **Current text (verbatim):** `QA/RA will import into appropriate complaint file and MDR file within FileHold.`
- **Replace with:** `QA/RA will upload the completed eMDR PDF to Silq eQMS Admin Docs, Complaint Records, MDR Files, within the applicable complaint file.`
- **Notes:** This sentence follows the step about creating a PDF file of the eMDR report.

---

### 2. Practical Compliance Additions (Non-mNC/OFI Advisory)

**Addition 1 — Software Currency Note**
- **Location:** Section 6 Procedure — insert as a NOTE box or italicized note at the beginning of Section 6, before the first procedure step (Step 6.1: "Click on the coffee cup icon...").
- **Current text (verbatim — anchor, first procedure step):** `Click on the coffee cup icon to launch the FDA's eSubmitter program, which is the FDA software that allows you to create an electronic MDR report (MedWatch 3500A form).`
- **Exact new text to add (insert immediately before the anchor sentence):**
  > **NOTE:** These work instructions describe the eMDR submission process as of the effective date of this document. The FDA eSubmitter software interface and the FDA ESG Web Trader Hosted Solution (WTHS) may be updated periodically. If the interface described in this work instruction does not match the current software, refer to the current eSubmitter User Manual available through the eSubmitter Help menu and the current FDA ESG instructions at www.fda.gov/esg for updated navigation guidance.
- **Notes:** Format as a bordered Note box or bold-italic text per document convention. This advisory protects the integrity of the WI over time and prevents user confusion when the FDA updates their eSubmitter interface.

**Addition 2 — URL Verification Advisory**
The following URLs are cited in Section 6 and were current as of the original WI creation date but should be verified for currency before Rev B is released:
1. `https://www.fda.gov/Safety/MedWatch/HowToReport/DownloadForms/ucm149236.htm`
2. `https://www.fda.gov/medicaldevices/deviceregulationandguidance/postmarketrequirements/reportingadverseevents/mdradverseeventcodes/default.htm`
3. `https://www.fda.gov/forindustry/fdaesubmitter/ucm193862.htm`

**Originator action required:** Test each URL before publishing Rev B. If any URL is broken or redirected, replace with the current equivalent. The recommended consolidated replacement for all FDA MDR/eMDR resources is the FDA's current MDR landing page and eSubmitter page. Consider replacing the three individual legacy URLs with:
- MDR resources: `https://www.fda.gov/medical-devices/mandatory-reporting-requirements-manufacturers-importers-and-device-user-facilities/how-submit-medical-device-reports`
- eSubmitter: `https://www.fda.gov/industry/electronic-submissions-gateway/esubmitter`

This is a practical usability update; outdated URLs in a controlled WI can cause user confusion and impede timely MDR submission.

---

### 3. Quality Plan Additions

No Quality Plan action items assigned to QM.SLQ023. No additions required.

---

### 4. Regulatory Reference Updates (OFI #8)

**Confirmation:** The Reference Documents section cites only QM.SLQ022 (internal reference) and FM1-QM.SLQ021 (associated form). No 21 CFR Part 820 or "QSR" references were found in the document. **No regulatory reference update is required.**

---

### 5. Definition Section Updates

- **Remove:** `FileHold:  Software based document management system used to electronically store controlled documents.`
- **Add:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`

---

### 6. Associated Forms

QM.SLQ023 references FM1-QM.SLQ021 (owned by QM.SLQ021). No forms are owned by QM.SLQ023. No form revisions required under this document.

---

## Document 8: QM.SLQ028 Protection of Confidential Patient Information SOP (Rev A → Rev B)

### Summary of Changes Required

This is the most critical compliance revision in DCO093. It requires: two FileHold reference replacements; one mandatory, substantive mNC #8 edit replacing the blanket internet prohibition with risk-based security language and adding two new sub-sections (role-based access controls and data breach response); and confirmation that existing regulatory references (ISO 13485:2016, HIPAA Privacy Rule) are current. There are no associated forms, no Quality Plan additions beyond the mNC #8 changes, and no legacy 820 references to update.

---

### 1. FileHold Reference Replacements

**Reference 1 of 2**
- **Location:** Section 4 General Definitions
- **Current text (verbatim):** `FileHold: Software based document management system used to electronically store controlled documents.`
- **Replace with:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`

**Reference 2 of 2**
- **Location:** Section 6 Procedure — second numbered step
- **Current text (verbatim):** `If the confidential patient information is computer-based information, e.g. images, electronic data, the confidential patient information shall be maintained in FileHold. Access is given to SILQ employees meeting the definition of Authorized Users. When possible, electronic data should be redacted so that patient name and identifying information is removed. An ID number may be used to replace patient name.`
- **Replace with:** `If the confidential patient information is computer-based information, e.g. images, electronic data, the confidential patient information shall be maintained in Silq eQMS. Access is restricted to SILQ employees meeting the definition of Authorized Users through role-based access controls administered within Silq eQMS. When possible, electronic data should be redacted so that patient name and identifying information is removed. An ID number may be used to replace patient name.`
- **Notes:** The replacement adds "through role-based access controls administered within Silq eQMS" to align with the mNC #8 RBAC requirement.

---

### 2. Audit Compliance Edits

**Finding: mNC #8 — Internet prohibition removal and information security upgrade (MANDATORY)**

This finding is the most critical in DCO093. The current blanket internet prohibition directly conflicts with SILQ's regulatory compliance operations (eMDR submission, clinical correspondence) and must be corrected.

*Change 1 of 3 — Replace the blanket prohibition paragraph:*
- **Location:** Section 6 Procedure — third numbered step
- **Current text (verbatim — full paragraph to be replaced):**
  > `All information obtained, generated or handled, whether paper-based or computer-based information and other electronic, visual or digital media is considered the property of SILQ. This information may not be physically removed from SILQ's facility or transmitted over the Internet. Employees will take the utmost care to protect the privacy and confidentiality of protected patient information. When reasonably possible, documents containing confidential patient information should be de-identified (removal of patient name and initials) so that the confidential information cannot be traced to that individual.  A patient ID number may be used in place of patient name or initials`
- **Replace the entire paragraph with:**
  > `All information obtained, generated, or handled — whether paper-based, computer-based, or in other electronic, visual, or digital media — is considered the property of SILQ. Such information shall not be transmitted, shared, or disclosed outside of SILQ except: (a) as required to fulfill regulatory reporting obligations (e.g., MDR submissions to FDA per QM.SLQ022 and QM.SLQ023); (b) as required for complaint investigation activities involving contract organizations or authorized representatives; or (c) as otherwise authorized under applicable HIPAA Privacy Rule requirements (45 CFR Parts 160 and 164). When transmitting confidential patient information electronically, SILQ personnel shall use secure, encrypted transmission methods. Unauthorized or unapproved transmission of confidential patient information is prohibited. Employees will take the utmost care to protect the privacy and confidentiality of protected patient information. When reasonably possible, documents containing confidential patient information should be de-identified (removal of patient name and initials). A patient ID number may be used in place of patient name or initials.`
- **Regulatory basis:** 45 CFR Parts 160 and 164 (HIPAA); ISO 13485:2016 clause 4.1.5; IA-2025 mNC #8

*Change 2 of 3 — Add Role-Based Access Controls sub-section:*
- **Location:** Insert immediately after the replaced paragraph above
- **Exact new text:**
  > **Role-Based Access Controls:** Access to confidential patient information maintained in Silq eQMS is controlled through role-based access permissions. Only Authorized Users (as defined in this procedure) are granted access to records containing confidential patient information. Access rights are administered by the Silq eQMS system administrator and are reviewed periodically to ensure access is limited to personnel with a current job-related need.
- **Regulatory basis:** 45 CFR Part 164 (HIPAA Security Rule); IA-2025 mNC #8

*Change 3 of 3 — Add Data Breach Response sub-section:*
- **Location:** Insert immediately after the Role-Based Access Controls sub-section above
- **Exact new text:**
  > **Data Breach Response:** In the event of an actual or suspected unauthorized access, disclosure, or loss of confidential patient information, the employee who becomes aware of the incident shall immediately notify QA management. QA management shall evaluate the incident to determine applicable notification obligations under HIPAA and any applicable state law, and shall document the evaluation and any resulting actions in accordance with QM.SLQ016 CAPA SOP.
- **Regulatory basis:** 45 CFR Part 164.400–414 (HIPAA Breach Notification Rule); IA-2025 mNC #8

---

### 3. Quality Plan Additions

The mNC #8 changes above (internet prohibition replacement, RBAC, and data breach response) constitute the substance of the quality plan-aligned improvements for this document. No separate Quality Plan action items are assigned.

---

### 4. Regulatory Reference Updates (OFI #8)

**Confirmation:** After reading QM.SLQ028 A in full, the Reference Documents section cites ISO 13485:2016 and "45 CFR Part 160 and Part 164 (Subparts A and E) HIPAA Privacy Rule" — both are current. No "QSR," "21 CFR 820," or "Quality System Regulation" references were found. **No regulatory reference update is required for QM.SLQ028.**

---

### 5. Definition Section Updates

- **Remove:** `FileHold: Software based document management system used to electronically store controlled documents.`
- **Add:** `Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ.`

---

### 6. Associated Forms

QM.SLQ028 has no associated forms (stated as "N/A" in the document). No form revisions required.

---

## Document 9: QM.SLQ030 Advisory Notices and Recalls SOP (Rev A → Rev B)

### Summary of Changes Required

This revision requires two FileHold reference replacements (both within the FSCA section of Section 6); confirmation that no FileHold entry is present in the Definitions section (confirmed — none present); two regulatory reference updates (OFI #8 — updating the QSR complaint files citation and updating the ISO 14971 edition); one substantive OFI #6 addition establishing recall metrics and trending requirements; and one Quality Plan addition (QMSR regulatory framing statement). All four associated forms (FM1–FM4-QM.SLQ030) require no revision.

---

### 1. FileHold Reference Replacements

**Reference 1 of 2**
- **Location:** Section 6 Procedure — Field Safety Corrective Action/Recall sub-section, paragraph describing distribution of Field Safety Notices (return receipt storage)
- **Current text (verbatim):** `Distribution of Field Safety Notices may be electronic (email or fax) or via the mail. In all cases, return receipt for the notice is required and will be stored in a separate Advisory Notice/Recall file related to the issue in appropriate folder within FileHold.`
- **Replace with:** `Distribution of Field Safety Notices may be electronic (email or fax) or via the mail. In all cases, return receipt for the notice is required and will be uploaded to Silq eQMS Admin Docs, CAPA Records, Advisory Notice and Recall Files, within the applicable CAPA file.`
- **Notes:** Locate this sentence by searching for "return receipt for the notice is required" in the FSCA section.

**Reference 2 of 2**
- **Location:** Section 6 Procedure — Field Safety Corrective Action/Recall sub-section, paragraph describing use of FM4-QM.SLQ030 for tracking distribution
- **Current text (verbatim):** `Use FM4-QM.SLQ030 Advisory and Recall Notices Distribution Log to track the status of the notice distribution activities. Once complete, scan and import the log with the Advisory Notice/Recall file in appropriate folder within FileHold.`
- **Replace with:** `Use FM4-QM.SLQ030 Advisory and Recall Notices Distribution Log to track the status of the notice distribution activities. Once complete, upload the log to Silq eQMS Admin Docs, CAPA Records, Advisory Notice and Recall Files, within the applicable CAPA file.`
- **Notes:** Locate this sentence by searching for "FM4-QM.SLQ030 Advisory and Recall Notices Distribution Log" in the FSCA section. Note that an earlier occurrence of the FM4 reference appears in the Advisory Notice sub-section (not FSCA) and uses different filing language — that earlier instance should be checked but does NOT reference FileHold: "Use FM4-QM.SLQ030...Once complete, store the log in the appropriate CAPA file." That earlier instance requires no change for the FileHold driver, but verify during review.

**Definitions section check:** Confirmed — no "FileHold" entry exists in the Definitions section of QM.SLQ030. No definition replacement is needed.

---

### 2. Audit Compliance Edits

**Finding: OFI #6 — Recall metrics tracking and trending (recommended)**
- **Location:** Add as a new section in the document. Recommended placement: as a new section following the Quality Records section at the end of Section 6, or as a new numbered standalone section titled "Recall and Advisory Notice Metrics and Trending."
- **Current text (verbatim — anchor: last sentence of Quality Records section):** `Records of advisory notices/recalls shall be maintained for a period of five years or a period of time equivalent to the expected life of the device, whichever is greater.`
- **Exact new text to add (insert as new sub-section or section immediately following the Quality Records section):**
  > **Recall and Advisory Notice Metrics and Trending**
  >
  > QA shall maintain a log of all advisory notices and recalls (Field Safety Corrective Actions) initiated by SILQ. At minimum, this log shall capture:
  > (a) advisory notice or recall identifier;
  > (b) associated CAPA number;
  > (c) product(s) and lot numbers affected;
  > (d) recall classification (if FDA recall: Class I, II, or III per 21 CFR 7.3(m));
  > (e) date initiated;
  > (f) date of FDA report submission (if applicable);
  > (g) effectiveness check completion status and outcome; and
  > (h) date of recall closure.
  >
  > Recall and advisory notice data shall be reported and trended at Management Review as part of the post-market surveillance input. Trend data shall include the number of advisory notices and recalls per period and any patterns identified in recall root causes. Trend data that indicates a recurring failure type shall be escalated to the CAPA system per QM.SLQ016.
- **Regulatory basis:** ISO 13485:2016 clause 8.2.3; IA-2025 OFI #6

---

### 3. Quality Plan Additions

**Quality Plan Action: Regulatory Reporting QMSR Framing**
- **Location:** Section 1 Purpose — add as a new sub-bullet or paragraph at the end of the Purpose section, after the last existing Purpose statement.
- **Current text (verbatim — last existing Purpose statement):** `SILQ will issue advisory notices and recall finished devices from its consignees when risk analyses indicate significant risk to public health or deviations from established specifications.`
- **Exact new text to add:**
  > `This procedure is implemented as part of SILQ's Quality Management System in compliance with the applicable regulatory requirements of the FDA Quality Management System Regulation (QMSR), 21 CFR Part 820 Section 820.10(b). SILQ's advisory notice and recall activities under this procedure satisfy applicable reporting requirements imposed by 21 CFR Part 806 (Reports of Corrections and Removals) and 21 CFR Part 810 (Medical Device Recall Authority) as referenced in the QMSR supplementary provisions framework.`

---

### 4. Regulatory Reference Updates (OFI #8)

**Update 1 of 2**
- **Location:** Section 3 Reference Documents
- **Current text (verbatim):** `21 CFR 820.198	FDA Quality System Regulation – Complaint Files`
- **Replace with:** `21 CFR Part 820 (QMSR) Section 820.198	Complaint Files`

**Update 2 of 2**
- **Location:** Section 3 Reference Documents
- **Current text (verbatim):** `EN ISO 14971:2012	Application of Risk Management to Medical Devices`
- **Replace with:** `ISO 14971:2019	Medical devices – Application of risk management to medical devices`
- **Notes:** The 2012 edition has been superseded by ISO 14971:2019, which QM.SLQ012 and QM.SLQ013 already reference correctly. This update aligns QM.SLQ030 with the current standard used throughout the SILQ QMS.

**QSR in body text check:** Confirm during document review whether "QSR" appears anywhere in the document body beyond the Reference Documents section. The visible text of the Definitions section includes a reference to "21 CFR 820" in the Corrective Action definition — verify on the Word file: `Corrective and Preventive Action (CAPA): A process and designated team that evaluates and provides quality and performance feedback to determine appropriate corrective and preventive actions to be performed. (21 CFR 820)` — if this reference appears, update to `(21 CFR Part 820 / QMSR)`.

---

### 5. Definition Section Updates

No FileHold definition to remove (none was present). No Silq eQMS definition addition required for the Definitions section of QM.SLQ030 (the FileHold references were in the procedure body only, not in a Definitions entry). If the originator prefers consistency across QMS documents, a Silq eQMS definition entry may optionally be added.

---

### 6. Associated Forms

**FM1-QM.SLQ030 A — Recall Report Submitted to FDA Form**
After reading the full form: no FileHold references are present. The form is a data entry template with fields for FDA recall report data elements.
**Determination: No revision required.**

**FM2-QM.SLQ030 A — FSCA Report (EU) Form**
After reading the full form: no FileHold references are present. The form is a structured EU FSCA notification template.
**Determination: No revision required.**

**FM3-QM.SLQ030 A — Field Safety Notice Form**
After reading the full form: no FileHold references are present. The form is a template for the Field Safety Notice document sent to customers.
**Determination: No revision required.**

**FM4-QM.SLQ030 A — Advisory and Recall Notices Distribution Log Form**
After reading the full form: no FileHold references are present. The form is a tracking log table for consignee distribution status.
**Determination: No revision required.**

---

## Appendix A: FileHold → Silq eQMS Translation Reference

For reference during editing, the complete approved translation table (from Phase 1A, QM.SLQ001 Rev B and QM.SLQ014 Rev C):

| Old (FileHold) | New (Silq eQMS) |
|---|---|
| "FileHold" (in Definitions) | "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ." |
| "scan and import into FileHold" | "upload to Silq eQMS" |
| "scanned and imported into FileHold" | "uploaded to Silq eQMS" |
| "import into [Folder] within FileHold" | "upload to Silq eQMS Admin Docs, [library name], [subfolder]" |
| "file within appropriate [X] folder within FileHold" | "file in Silq eQMS Admin Docs, [appropriate library], [subfolder]" |
| "maintained in FileHold" | "maintained in Silq eQMS" |
| Risk Management documents | Upload to: **Silq eQMS Admin Docs, Design History Files, [project] Risk Management File folder** |
| CAPA records | Upload to: **Silq eQMS Admin Docs, CAPA Records** |
| Management Review records | Upload to: **Silq eQMS Admin Docs, QM Documents, Management Review Records** |
| Complaint files | Upload to: **Silq eQMS Admin Docs, Complaint Records** |
| MDR files | Upload to: **Silq eQMS Admin Docs, Complaint Records, MDR Files** |
| Advisory Notice / Recall files | Upload to: **Silq eQMS Admin Docs, CAPA Records, Advisory Notice and Recall Files** |

---

## Appendix B: Regulatory Reference Update Summary (OFI #8)

All required updates across DCO093 documents:

| Document | Location | Current Text | Replace With |
|---|---|---|---|
| QM.SLQ016 | Section 3 Reference Documents | `21 CFR 820  Quality System Regulation (820.100 – Corrective and Preventive Action)` | `21 CFR Part 820  Quality Management System Regulation (QMSR) (820.100 – Corrective and Preventive Action)` |
| QM.SLQ018 | Section 1 Purpose, 2nd bullet | `FDA Quality System Regulation (QSR)` | `FDA Quality Management System Regulation (QMSR)` |
| QM.SLQ018 | Section 3 Reference Documents | `21 CFR 820  Quality System Regulation (820.20 – Management Responsibility)` | `21 CFR Part 820  Quality Management System Regulation (QMSR) (820.20 – Management Responsibility)` |
| QM.SLQ021 | Section 3 Reference Documents | `21 CFR 820.198  Complaint Files` | `21 CFR Part 820 (QMSR) Section 820.198  Complaint Files` |
| QM.SLQ021 | Section 4 Abbreviations | `HIPPA:  Health Insurance Portability and Accountability Act` | `HIPAA:  Health Insurance Portability and Accountability Act` |
| QM.SLQ022 | Section 4 Abbreviations | `HIPPA:  Health Insurance Portability and Accountability Act` | `HIPAA:  Health Insurance Portability and Accountability Act` |
| QM.SLQ030 | Section 3 Reference Documents | `21 CFR 820.198  FDA Quality System Regulation – Complaint Files` | `21 CFR Part 820 (QMSR) Section 820.198  Complaint Files` |
| QM.SLQ030 | Section 3 Reference Documents | `EN ISO 14971:2012  Application of Risk Management to Medical Devices` | `ISO 14971:2019  Medical devices – Application of risk management to medical devices` |

**No regulatory reference updates required in:** QM.SLQ012, QM.SLQ013, QM.SLQ023, QM.SLQ028 (all confirmed after full document review).

---

## Appendix C: mNC Compliance Summary

| mNC | Assigned Document | Change Type | Status in This Guide |
|---|---|---|---|
| mNC #3 | QM.SLQ013 | MANDATORY — add systematic design change risk evaluation requirements to Scope (Section 2) and Procedure (Section 5) | Addressed — see Document 2 |
| mNC #6 | QM.SLQ021 | MANDATORY — add specific CAPA escalation criteria to Complaint Trending sub-section | Addressed — see Document 5 |
| mNC #8 | QM.SLQ028 | MANDATORY — replace blanket internet prohibition with risk-based language; add RBAC and data breach response sections | Addressed — see Document 8 |

---

## Appendix D: OFI Compliance Summary

| OFI | Assigned Document | Status in This Guide |
|---|---|---|
| OFI #1 | QM.SLQ012 | Addressed — 4th sub-bullet added to Risk Management Report section |
| OFI #2 | QM.SLQ013 | Addressed — traceability requirement added to PHA completion steps |
| OFI #3 | QM.SLQ018 | Addressed — annual input coverage documentation requirement added; FM1-QM.SLQ018 updated |
| OFI #5 | QM.SLQ022 | Addressed — decision framework and UDI requirement added |
| OFI #6 | QM.SLQ030 | Addressed — Recall Metrics and Trending section added |
| OFI #8 | All documents | Addressed per Appendix B |
| OFI #9 | QM.SLQ018 | Addressed — Management Representative formal designation paragraph added |
| OFI #10 | QM.SLQ012 | Addressed — FDA QMS linkage statement added to Scope |

---

## Appendix E: Note on DCO094 Scope Boundary and Upcoming DCOs

This guide covers only the nine documents and associated forms in the DCO093 package. The following documents and mNCs are **out of scope for DCO093**:

**Dedicated Design Controls DCO (higher priority than DCO094 — target before Jul 2026):**
- QM.SLQ004 (4 drivers: mNC #1, CAPA003, EDMS, OFI #8) — see Appendix F.3 for full scope
- QM.SLQ005 and QM.SLQ006 (CAPA003 supplier modification trigger requirement, EDMS, OFI #8)

**DCO094 (remaining Phase 2 documents):**
- QM.SLQ025, QM.SLQ027, QM.SLQ029, QM.SLQ033, QM.SLQ038, QM.SLQ039, QM.SLQ043, QM.SLQ045, QM.SLQ046, QM.SLQ047, QM.SLQ048, QM.SLQ049, QM.SLQ050, QM.SLQ051, and others
- mNCs #9, #10, #11, #12, #14, #15 (assigned to documents not in this package)
- OFIs #4, #7 (assigned to documents not in this package)
- Quality Plan items for QM.SLQ027 (QMSR mapping, Medical Device File framework), QM.SLQ033 (feedback governance), QM.SLQ037 (quality objectives revision)

Do not incorporate DCO094-scope or Design Controls DCO-scope changes into the DCO093 package to avoid scope creep.

---

## Appendix F: Supplemental Review — Revisions Required in DCO091 and DCO092

**Prepared by:** QMS management agent, June 9, 2026
**Basis:** Cross-reference of DCO091 and DCO092 editing guides against the Silq 2026 Quality Plan and IA-2025 audit findings. The DCO091 and DCO092 guides were built with two drivers (DC.SLQ002 EDMS transition and IA-2025 audit findings). This supplemental review applies the **third driver (2026 Quality Plan)** retroactively to those packages.

---

### F.1 — DCO091 Supplemental Review

**Documents in DCO091:** QM.SLQ001 Rev A → B (Document Control SOP), QM.SLQ014 Rev B → C (Electronic Document System WI), FM1-QM.SLQ014 Rev A → B (Electronic Signature Acknowledgement Form), FM1-QM.SLQ001 Rev A → B (Document Change Order Form).

**Finding: No supplemental changes required.**

The DCO091 package correctly addressed Phase 1A EDMS transition and mNC #13 (effective date risk-based determination for QM.SLQ001). Review of the 2026 Quality Plan against each DCO091 document confirms:

- The Quality Plan items requiring updates to QM.SLQ027 (Quality Manual) — specifically the QMSR Supplementary Provision Mapping (§820.10(b), §820.35, §820.45) and the Medical Device File Framework (ISO 13485 clause 4.2.3) — are scoped to QM.SLQ027 and QM.SLQ048, both of which are Phase 2 documents assigned to DCO094. No changes to QM.SLQ001 or QM.SLQ014 are required on these grounds.
- The OFI #8 systemic legacy 820 reference updates for QM.SLQ001 Rev B and QM.SLQ014 Rev C were addressed within those documents during the Phase 1A rewrite.
- No other Quality Plan action items introduce requirements for the DCO091 documents.

**DCO091 is complete with respect to the three-driver framework.**

---

### F.2 — DCO092 Supplemental Review

**Documents in DCO092:** QM.SLQ003 Rev B → C, QM.SLQ015 Rev B → C, QM.SLQ017 Rev A → B, QM.SLQ020 Rev D → E, QM.SLQ036 Rev E → F. (QM.SLQ004 was deferred to a dedicated Design Controls DCO — see F.3.)

**Finding: One supplemental change required, assigned to QM.SLQ003 Rev C.**

---

#### F.2.1 — QM.SLQ003 Employee Training SOP (Rev C): Dynamic Employee Training Program Addition

**Source:** 2026 Quality Plan, Section 6 (Resource Management) — "Dynamic Employee Training Program (Owner: Ethan Rao, Q3 2026)"

**Quality Plan action item (verbatim):** "The current training system documents read-and-understand acknowledgments but does not assess comprehension of quality procedures or effectiveness of training delivery. Action Item: Establish a dynamic employee training program that assesses comprehension of existing quality procedures and procedure revisions, rather than relying solely on read-and-sign acknowledgment."

**What DCO092 addressed:** The DCO092 editing guide correctly addressed OFI #7 (strengthening discretionary "may be evaluated" training effectiveness evaluation language in Section 9). That change ensures effectiveness evaluation is risk-based and not freely waivable. However, OFI #7 pertained to the *consistency* of effectiveness evaluation language for individual training events. The Quality Plan action item requires an additional and distinct change: that a **comprehension assessment mechanism** be embedded in the procedure for applicable procedure categories — going beyond the read-and-sign model. This was not addressed in DCO092.

**Required addition to QM.SLQ003 Rev C:**

- Location: Section 8 (Procedure: Training) — add as a new sub-section at the end of the training procedure section, after the existing effectiveness evaluation language (Section 8.11 or equivalent).
- Current text (verbatim — anchor, last effectiveness evaluation sentence): `"Effectiveness evaluations will be conducted based on the complexity of the task/procedure and/or associated risk."`
- Exact new text to add (insert as new sub-section immediately following the anchor sentence):

  > "Comprehension Assessment Program: For training on safety-critical procedures, complex technical procedures, or procedures identified by QA management as requiring comprehension assessment, training shall include a comprehension evaluation component beyond read-and-acknowledge. The comprehension evaluation method shall be documented in the applicable Employee Training Program (FM1-QM.SLQ003) prior to training delivery, and may include, but is not limited to: written quiz or assessment with documented results; practical demonstration with observed performance evaluation; or structured verbal assessment with written summary by the trainer. Comprehension evaluation results shall be retained with the associated training record in Silq eQMS Admin Docs, Training Records. The Training Coordinator, in consultation with QA management, shall maintain a current list of procedures requiring comprehension assessment, reviewed and updated at least annually."

- Notes: This addition implements the Quality Plan Q3 2026 action item for establishing a dynamic employee training program. It does not require changes to FM1-QM.SLQ003 or FM2-QM.SLQ003, as the existing forms have sufficient space to document training method and results. The list of procedures requiring comprehension assessment is a living operational document maintained by the Training Coordinator and does not require a DCO to update — it is an administrative record analogous to the training matrix.

---

#### F.2.2 — Other DCO092 Documents: No Supplemental Changes Required

| Document | Quality Plan Items Reviewed | Finding |
|---|---|---|
| QM.SLQ015 Rev C | "Supplier Audit: Pathway MedTech (Q4 2026)" — this is an operational schedule update to FM7-QM.SLQ015 (add Pathway MedTech to the audit schedule data); it is a data entry update by the originator, not a procedure revision. FM7 is already being revised (Rev A → B) for mNC #4. | No additional procedure change required. Originator should add Pathway MedTech to the updated FM7-QM.SLQ015 Rev B schedule when publishing. |
| QM.SLQ017 Rev B | No Quality Plan action items assigned to this document. | No changes. |
| QM.SLQ020 Rev E | The mNC #5 mandatory supplier change notification fix (already addressed in DCO092) is the same issue referenced in the Quality Plan under "CAPA 2025-003 Corrective Action Completion." The DCO092 fix to QM.SLQ020 is consistent with and satisfies the Quality Plan action item. | No additional changes required. |
| QM.SLQ036 Rev F | No Quality Plan action items assigned to this document. | No changes. |

---

### F.3 — Dedicated Design Controls DCO: Required Scope Summary

QM.SLQ004 (Design Control Program SOP) was deferred from DCO092. It will be addressed in a dedicated Design Controls DCO covering QM.SLQ004, QM.SLQ005, and QM.SLQ006. For completeness, that future DCO must address **four drivers** for QM.SLQ004:

1. **DC.SLQ002 Phase 2 EDMS Transition:** Replace FileHold references in QM.SLQ004, QM.SLQ005, and QM.SLQ006.
2. **IA-2025 mNC #1:** Nine documented design control gaps (detailed in the DCO092 prompt at `docs/plans/AGENT_PROMPT_DCO092_PHASE1B_EDITING_GUIDE.md`).
3. **CAPA003 Corrective Actions:** Revise QM.SLQ004, QM.SLQ005, and QM.SLQ006 to add an explicit requirement that any notification of a supplier-initiated component or process modification triggers mandatory design review, risk assessment, and regulatory evaluation prior to continued manufacturing (Quality Plan action item, CAPA003 corrective action, target date 01 Jul 2026).
4. **OFI #8:** Regulatory reference updates.

The dedicated Design Controls DCO is a higher-priority package than DCO094 given CAPA003's July 2026 target date.

---

### F.4 — Full Three-Driver Coverage Summary Across All Phase 1 and Phase 2 DCOs

| DCO | Documents | Driver 1 (EDMS) | Driver 2 (IA-2025) | Driver 3 (Quality Plan) |
|---|---|---|---|---|
| DCO091 | QM.SLQ001, QM.SLQ014, FM1-QM.SLQ014, FM1-QM.SLQ001 | Complete | mNC #13 addressed | Complete — no QP items |
| DCO092 | QM.SLQ003, QM.SLQ015, QM.SLQ017, QM.SLQ020, QM.SLQ036 | Complete | mNCs #4, #5; OFIs #4, #7, #8 addressed | Partial — add QM.SLQ003 comprehension assessment per F.2.1 above |
| Design Controls DCO (future) | QM.SLQ004, QM.SLQ005, QM.SLQ006 | Required | mNC #1 + CAPA003 | CAPA003 procedure revisions (mandatory, Jul 2026) |
| DCO093 | 9 documents (this guide) | Complete | mNCs #3, #6, #8; OFIs #1, #2, #3, #5, #6, #8, #9, #10 addressed | Complete — all applicable QP items addressed (plus Driver 4 CAPA streamlining for QM.SLQ016, FM1-QM.SLQ016, and CAPA Log) |
| DCO094 | Remaining Phase 2 docs | Required | mNCs #9–#12, #14, #15; remaining OFIs | QM.SLQ027 (QMSR mapping, MDF framework), QM.SLQ033 (feedback governance), QM.SLQ037 (quality objectives), others |

---

*This editing guide was prepared by the QMS management agent on June 9, 2026, supplemented on the same date following cross-reference review of DCO091 and DCO092, and revised on June 10, 2026 to incorporate the CAPA process streamlining revision to QM.SLQ016, FM1-QM.SLQ016, and the SILQ CAPA Log (Driver 4) based on a detailed review of executed CAPA 001-2025, 002-2025, and 003-2025. All source documents were read in full from the SilqQMS project folder. Verbatim current text was transcribed directly from the readable text source files.*
