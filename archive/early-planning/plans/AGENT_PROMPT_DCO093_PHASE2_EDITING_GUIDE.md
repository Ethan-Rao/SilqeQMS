# Agent Prompt: DCO093 Phase 2 — Detailed Document Editing Guide

**For use by:** New agent session
**Prepared by:** QMS management agent, June 9, 2026
**Context document:** `docs/plans/AGENT_PROMPT_DCO093_PHASE2_EDITING_GUIDE.md`

---

## YOUR TASK

You are a quality management system (QMS) expert agent working within the SilqQMS project folder (`c:\Users\Ethan\OneDrive\Desktop\SilqQMS`).

Your task is to produce a **very detailed, specific, document-by-document editing guide** for DCO093 — the Phase 2 document revision package under design project DC.SLQ002 ("Silq eQMS EDMS Transition"). This guide will be used by the document originator (Ethan Rao) to write the actual revised documents.

**Do not create or modify any actual SOP documents.** Your only output is the editing guide itself, which you will write to:

```
docs/DCO093/DCO093_PHASE2_EDITING_GUIDE.md
```

If the `docs/DCO093/` folder does not exist, create it.

---

## BACKGROUND CONTEXT (read this carefully)

### Design Project: DC.SLQ002

SILQ is executing design project DC.SLQ002, "Silq eQMS Electronic Document Management System Transition Plan." This project transitions SILQ's quality document operations from the legacy **FileHold** document management system to the **Silq eQMS** system (a custom-developed web-based EDMS at silqeqms.com, validated per SW.SLQ007–012).

**Phase 1A** (DCO091, currently in process) completed major rewrites of:
- QM.SLQ001 Rev A → B (Document Control SOP)
- QM.SLQ014 Rev B → C (Electronic Document System WI)
- FM1-QM.SLQ014 Rev A → B (Electronic Signature Acknowledgement Form)

**Phase 1B** (DCO092, in process) revises six SOPs (QM.SLQ003, QM.SLQ004, QM.SLQ015, QM.SLQ017, QM.SLQ020, QM.SLQ036).

**Phase 2 (DCO093 — this is the work you are guiding)** requires line-by-line review and revision of nine documents, covering risk management, CAPA, management review, complaint handling, MDR reporting, and confidential patient information. Every document must be updated for all three drivers described below.

**Note on design control documents:** QM.SLQ004 through QM.SLQ010 (design control procedure series) will undergo a separate contained DCO revision in the future. For DCO093, the risk management SOPs (QM.SLQ012 and QM.SLQ013) are **in scope** for Phase 2 and must be revised now.

### Three Drivers for Every Phase 2 Document

Every document in Phase 2 must be assessed for **three distinct revision drivers**, and the editing guide must address all three:

**Driver 1 — EDMS Transition (DC.SLQ002):** Replace all references to "FileHold" (including FileHold-specific workflows, scan/import procedures, drawer/folder names) with Silq eQMS–equivalent operations, consistent with the language established in QM.SLQ001 Rev B and QM.SLQ014 Rev C.

**Driver 2 — Audit Compliance (IA-2025, CAPA004):** Implement specific procedural changes to address the Minor Non-Compliances (mNCs) and applicable Opportunities for Improvement (OFIs) from the IA-2025 internal audit (conducted April 23–24, 2026 by Stephen Page, MedReg Associates Inc.). The full audit report is at: `docs/QMS-Readable-Texts/20-QMSInProcess/CAPA004/IA-2025 Final Report Readable.md`

**Driver 3 — 2026 Quality Plan (QM.SLQ025):** Implement specific procedural additions identified in the Silq 2026 Quality Plan (prepared April 19, 2026 by Ethan Rao). Several Quality Plan action items require single-sentence or short paragraph additions to DCO093 documents. These are minimal-effort, high-compliance-value edits. The full Quality Plan readable text is at: `docs/QMS-Readable-Texts/20-QMSInProcess/Quality Planning Documents/Silq 2026 Quality Plan.md`

### FileHold → Silq eQMS Translation Rules (from Phase 1A)

The following is the approved translation language from QM.SLQ001 Rev B and QM.SLQ014 Rev C. Apply these consistently:

| Old (FileHold) | New (Silq eQMS) |
|---|---|
| "FileHold" (in Definitions) | "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ." |
| "scan and import into FileHold" | "upload to Silq eQMS" |
| "scanned and imported into FileHold" | "uploaded to Silq eQMS" |
| "import into [Folder] within FileHold" | "upload to Silq eQMS Admin Docs, [library name], [subfolder]" |
| "checked in/out of FileHold" | "uploaded to / retrieved from Silq eQMS" |
| "file within appropriate [X] folder within FileHold" | "file in Silq eQMS Admin Docs, [appropriate library], [subfolder]" |
| "maintained in FileHold" | "maintained in Silq eQMS" |
| "FileHold drawer" | "Silq eQMS Admin Docs library" |
| "appropriate FileHold folder" | "Silq eQMS Admin Docs, [appropriate library]" |
| Regulatory references to "21 CFR 820" / "QSR" alone | Update to include "21 CFR Part 820 Quality Management System Regulation (QMSR)" |
| "QSR: FDA Quality System Regulation" | "QMSR: Quality Management System Regulation (21 CFR Part 820, as revised)" |
| "FDA Quality System Regulation (QSR)" in Purpose/Scope | "FDA Quality Management System Regulation (QMSR)" |

The Silq eQMS Admin Docs library structure (use for file placement guidance):
- QM Documents
- Design History Files
- Supplier Quality Records
- Purchasing Records
- Sales Order Records
- Internal Audit Records
- Training Records
- CAPA Records
- Calibration and Maintenance Records
- Regulatory Standards and Approvals
- Environmental Monitoring

For **Risk Management Files** specifically: Risk management documents are part of the Design History File (DHF). The replacement filing instruction should reference: "uploaded to Silq eQMS Admin Docs, Design History Files, [product/project name] Risk Management File."

For **CAPA records**: "uploaded to Silq eQMS Admin Docs, CAPA Records."

For **Management Review records**: "uploaded to Silq eQMS Admin Docs, QM Documents, Management Review Records."

For **Complaint files**: "uploaded to Silq eQMS Admin Docs, Complaint Records."

For **MDR files**: "uploaded to Silq eQMS Admin Docs, Complaint Records, MDR Files."

For **Advisory Notice / Recall files**: "uploaded to Silq eQMS Admin Docs, CAPA Records, Advisory Notice and Recall Files."

---

## IA-2025 AUDIT FINDINGS RELEVANT TO DCO093 DOCUMENTS

The findings relevant specifically to Phase 2 DCO093 documents are:

**mNC #3 (QM.SLQ013 — Risk Analysis SOP)**
QM.SLQ013 does not clearly state the mandatory minimum requirement for hazard identification and risk analysis particularly for design changes where systematic risk evaluation must still occur and be documented even if a Hazard Analysis is not required.

**mNC #6 (QM.SLQ021 — Product Complaint System SOP)**
The Complaint Handling procedure includes provisions for complaint trending; however, it does not define criteria or requirements for when identified trends must be escalated to the CAPA system. The procedure does not ensure effective linkage between complaint trending and CAPA initiation.

**mNC #8 (QM.SLQ028 — Protection of Confidential Patient Information)**
The procedure includes a blanket prohibition on transmission of information over the Internet, which is not aligned with current operational practices (e.g., electronic MDR submissions). Additionally, the procedure does not define requirements for secure transmission methods, data breach response, or role-based access controls.

**OFI #1 (QM.SLQ012 — Risk Management File consolidation)**
Risk management outputs are distributed across multiple documents. Establishing a consolidated Risk Management Report that summarizes analyses and documents overall residual risk acceptability and benefit-risk determination at the system level could improve clarity, traceability, and completeness of the Risk Management File.

**OFI #2 (QM.SLQ013 — Risk Analysis, traceability to design controls)**
The Risk Analysis procedure does not explicitly require traceability of risk analysis outputs to design inputs and verification/validation activities. Incorporating this requirement directly within QM.SLQ013 could improve clarity and integration.

**OFI #3 (QM.SLQ018 — Management Review, annual input coverage)**
The Management Review procedure states that not all required inputs need to be reviewed at each meeting; however, management reviews are conducted annually. Management review records are not directly required to demonstrate that all required inputs were reviewed annually.

**OFI #5 (QM.SLQ022 — Medical Device Reporting, decision methodology and UDI)**
The MDR procedure does not establish a clear and consistent decision methodology for determining reportability, such as defined criteria or decision logic. Additionally, the procedure does not explicitly address inclusion of required data elements (e.g., UDI) in MDR submissions.

**OFI #6 (QM.SLQ030 — Advisory Notices and Recalls, recall metrics trending)**
The procedure does not include requirements to track and trend recall-related metrics over time.

**OFI #8 (All DCO093 documents)**
Outdated regulatory references to pre-QMSR 21 CFR Part 820 exist throughout QMS documentation. All documents in DCO093 must update "Quality System Regulation (QSR)" to "Quality Management System Regulation (QMSR)" and update old 21 CFR 820 section number references.

**OFI #9 (QM.SLQ018 — Management Representative role)**
The QMS does not formally designate a Management Representative role, which remains a requirement under ISO 13485 and is referenced within organizational procedures.

**OFI #10 (QM.SLQ012 — Risk Management, linkage to FDA QMS expectations)**
The Risk Management procedure is well aligned with ISO 14971; however, the linkage to broader FDA quality system expectations (design controls, V&V, CAPA, production) is not explicitly defined.

---

## PHASE 2 DOCUMENTS IN SCOPE FOR DCO093

The nine documents below must be revised. For each document, your editing guide must provide:
1. A complete list of all FileHold references found in the document (quote exact current text)
2. The specific replacement text for each FileHold reference (exact new wording)
3. The specific audit compliance edits (location, current language verbatim, required new language)
4. The specific Quality Plan additions (location, exact new text to add)
5. All regulatory reference updates (OFI #8)
6. Definition section updates (remove "FileHold," add "Silq eQMS," update "QSR" to "QMSR")
7. Document revision number (next sequential letter)

---

### Document 1: QM.SLQ012 Risk Management SOP (Rev B → Rev C)

**Associated forms/templates:** TMP1-QM.SLQ012 Risk Management Plan Template

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ012 B Risk Management SOP.md`

**FileHold references to find and replace (2 confirmed):**

Reference 1:
- Location: Section 5 General Definitions
- Current text (verbatim): "FileHold: Software based document management system used to electronically store controlled documents."
- Replace with: "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."

Reference 2:
- Location: Section 8 Procedure: Risk Management File, last sub-bullet
- Current text (verbatim): "Risk Management documents are to be scanned and imported into FileHold and filed into the appropriate DHF."
- Replace with: "Risk Management documents are to be uploaded to Silq eQMS Admin Docs, Design History Files, within the applicable product or project Risk Management File folder."

**Audit compliance edits — OFI #1 (Risk Management Report consolidation, recommended):**
Current Section 6 (Procedure: Risk Management Report) describes summary report requirements. OFI #1 recommends establishing a consolidated Risk Management Report that explicitly summarizes all risk management analyses (PHA/Master Hazard Analysis, DFMEA, PFMEA) and documents overall residual risk acceptability and benefit-risk determination at the system level.
- Location: Section 6 Procedure: Risk Management Report — add to the end of the "The report contains sufficient information to ensure:" bullet list
- Addition: Add a fourth sub-bullet: "The Risk Management Report explicitly summarizes the outputs of all risk analysis activities performed (including Master Hazard Analysis, FMEA(s), and any supplemental analyses) and documents the overall residual risk acceptability and benefit-risk determination for the device or product family at the system level."
- Provide exact draft language for this sub-bullet.

**Audit compliance edits — OFI #10 (Linkage to FDA QMS expectations, recommended):**
Current Section 2 (Scope) and the Procedure sections do not explicitly state how risk management integrates into design controls, V&V, CAPA, and production processes from an FDA perspective.
- Location: Section 2 Scope — add a new sub-section following the existing scope statements
- Addition: Add a brief statement such as: "In accordance with FDA Quality Management System Regulation (QMSR) expectations, risk management activities at SILQ are integrated with design control activities (QM.SLQ004 through QM.SLQ010), verification and validation planning, CAPA processes (QM.SLQ016), and production and post-production information review. Risk management is not a standalone activity; it informs and is informed by all relevant quality system processes."
- Provide exact draft language for this addition.

**Quality Plan additions — Post-Production Risk File Update Triggers:**
The 2026 Quality Plan states: "QM.SLQ012 Section 14 requires evaluation of post-production information for impact on risk management but does not define explicit trigger criteria for when such information requires a formal risk file revision versus monitoring until the next scheduled review."
- Action: Add a short decision framework to Section 7 (Procedure: Production and Post-Production Information) — specifically following the sentence "SILQ evaluates the information for impact on previous risk management activities and provides it as an input back into the risk management process, revising risk management deliverables such as the Master Hazard Analysis as needed."
- The decision framework must define specific trigger criteria that require a formal risk file revision (not just monitoring). At minimum, triggers should include: (a) any new hazard identified that is not present in the current risk analysis; (b) any change in the probability rating of an existing hazard based on post-market data; (c) any complaint or adverse event resulting in a risk category increase; (d) any design change or supplier change affecting a hazard previously evaluated. When none of these triggers apply, continued monitoring until the next scheduled annual review is acceptable.
- Provide exact draft language for this decision framework, formatted as a new sub-section following the existing Section 7 body.

**Regulatory reference updates (OFI #8):**
- The document does not use "QSR" or "21 CFR 820" language in its Reference Documents section (it references ISO 14971 and ISO/TR 24971 primarily). No regulatory reference update is required unless any legacy 21 CFR 820 citations are found during document review.
- Confirm by reading the full document: if any "QSR," "21 CFR 820," or "Quality System Regulation" references are present, update per the translation table above.

**Associated template TMP1-QM.SLQ012 (Risk Management Plan Template):**
- Current readable text location: Search `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/` for TMP1-QM.SLQ012
- If found, read and identify any FileHold references in the template; specify required changes
- If no FileHold references are present, state "No revision required"

---

### Document 2: QM.SLQ013 Risk Analysis SOP (Rev B → Rev C)

**Associated forms/templates:** TMP1-QM.SLQ013 (PHA Template), TMP2-QM.SLQ013 (Hazards Analysis Table Template), TMP3-QM.SLQ013 (FMEA Worksheet Template)

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ013 B Risk Analysis SOP.md`

**FileHold references to find and replace (2 confirmed):**

Reference 1:
- Location: Section 4 General Definitions
- Current text (verbatim): "FileHold: Software based document management system used to electronically store controlled documents."
- Replace with: "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."

Reference 2:
- Location: Section 10 Procedure: Risk Management File, sub-bullet
- Current text (verbatim): "Risk Management documents are to be scanned and imported into FileHold and filed into the appropriate DHF."
- Replace with: "Risk Management documents are to be uploaded to Silq eQMS Admin Docs, Design History Files, within the applicable product or project Risk Management File folder."

**Audit compliance edits — mNC #3 (MANDATORY):**
Current text does not clearly state that systematic risk evaluation must occur and be documented for design changes even when a full Hazard Analysis is not required.

Current Section 2 (Scope) states: "The scope of risk analysis activities for any given product or project is defined in the Risk Management Plan or DCO, as directed by Risk Management process (QM.SLQ012)." This is accurate but insufficient to address mNC #3.

Required changes:
- Location: Section 2 Scope — add a new sub-bullet following the existing scope statements
- Add: "For design changes, systematic risk evaluation must occur and be documented regardless of whether a full Hazard Analysis or new Risk Management Plan is required. At minimum, the change must be evaluated to determine: (a) whether any new hazards are introduced; (b) whether the probability or severity of existing hazards is affected; and (c) whether risk mitigations remain effective. This evaluation must be documented and retained in the Risk Management File or the applicable DCO record."
- Provide exact draft language for this addition.

- Location: Section 5 Procedure: Overall Risk Assessment Process — add a sentence or sub-bullet clarifying the mandatory nature of risk evaluation for design changes
- Current text includes: "Various methods may be chosen for risk analysis. The methods described below are the primary methods recommended for SILQ products, however do not represent the only options allowed."
- Add after this paragraph: "For design changes processed through the DCO system, a documented risk evaluation is mandatory regardless of project scope or planning status. The responsible R&D/Engineering or QA personnel shall document the change's impact on previously identified hazards and confirm that no new unmitigated risks are introduced. This evaluation shall be referenced within the applicable DCO."
- Provide exact draft language.

**Audit compliance edits — OFI #2 (Traceability to design controls, recommended):**
The procedure does not explicitly require traceability of risk analysis outputs (identified hazards, mitigations, verification activities) to design inputs and V&V activities.

- Location: Section 6 Procedure: Preliminary Hazard Analysis — add to the existing instructions near the end of the PHA completion steps
- Current text ends with summarizing hazard analysis results and residual risks.
- Add: "Upon completion of the PHA or Master Hazard Analysis, all identified risk mitigations that require design or process verification shall be cross-referenced to the corresponding design inputs documented in the Design History File and to the applicable verification and validation activities planned or completed under QM.SLQ004 through QM.SLQ010. This traceability shall be documented within the risk analysis document or in a separate Risk Management File traceability table."
- Provide exact draft language.

**Regulatory reference updates (OFI #8):**
- The document references ISO 14971:2019 and ISO/TR 24971:2020. These are current and correct — retain as-is.
- If any "21 CFR 820" or "QSR" language is found in the document, update per translation table.

**Associated templates TMP1–TMP3-QM.SLQ013:**
- Search `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/` for each template
- Read each and identify any FileHold references
- Specify required changes or state "No revision required" for each

---

### Document 3: QM.SLQ016 CAPA SOP (Rev C → Rev D)

**Associated forms:** FM1-QM.SLQ016 Corrective and Preventive Action Report Form

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ016 C CAPA SOP.md`

**FileHold references to find and replace (2 confirmed):**

Reference 1:
- Location: Section 4 General Definitions
- Current text (verbatim): "FileHold:  Software based document management system used to electronically store controlled documents."
- Replace with: "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."

Reference 2:
- Location: Section 7 Procedure: CAPA Records Retention, sub-bullet
- Current text (verbatim): "Records are to be scanned and imported into FileHold and filed within appropriate CAPA folder."
- Replace with: "Records are to be uploaded to Silq eQMS Admin Docs, CAPA Records."

**No mNC directly assigned to QM.SLQ016** in IA-2025. This revision is primarily EDMS transition (Driver 1) and regulatory reference updates (OFI #8).

**Note on CAPA Log:** Section 6 (Procedure: CAPA Log) states "The CAPA Log is archived on a secure network server." This statement should be reviewed — if the CAPA Log is transitioning to Silq eQMS, this sentence may need updating to "The CAPA Log is maintained in Silq eQMS Admin Docs, CAPA Records." Advise the originator whether this applies based on current operational practice. If the log remains on a separate network server, retain existing language.

**Regulatory reference updates (OFI #8):**
- Location: Section 3 Reference Documents
- Current text (verbatim): "21 CFR 820 	Quality System Regulation (820.100 – Corrective and Preventive Action)"
- Replace with: "21 CFR Part 820 	Quality Management System Regulation (QMSR) (820.100 – Corrective and Preventive Action)"
- Also update the Abbreviations section if "QSR" is listed. In QM.SLQ016, the Abbreviations section does not appear to include QSR, but confirm during document review.

**Associated form FM1-QM.SLQ016 (CAPA Report Form):**
- Search `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/` for FM1-QM.SLQ016
- Read the form and identify any FileHold-specific instructions embedded in form fields or footer
- Specify required changes or state "No revision required"

---

### Document 4: QM.SLQ018 Management Review SOP (Rev A → Rev B)

**Associated forms:** FM1-QM.SLQ018 Management Review Meeting Minutes

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ018 A Management Review SOP.md`

**FileHold references to find and replace (2 confirmed):**

Reference 1:
- Location: Section 5 General Definitions
- Current text (verbatim): "FileHold:  Software based document management system used to electronically store controlled documents."
- Replace with: "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."

Reference 2:
- Location: Section 7 Procedure: Records/Documentation, last bullet
- Current text (verbatim): "Management Representative will scan and import all MR records into appropriate FileHold folder(s)."
- Replace with: "Management Representative will upload all MR records to Silq eQMS Admin Docs, QM Documents, Management Review Records."

**Audit compliance edits — OFI #3 (Annual input coverage documentation, recommended):**
Current Section 6 Procedure states: "The following running agenda shall be addressed throughout the course of a calendar year although not all items need be reviewed at each meeting." OFI #3 finds that because management reviews are conducted annually, the current language does not require documentation that all inputs were covered over the full year.

Required change:
- Location: Section 6 Procedure, following the running agenda bullet list
- Add: "Because SILQ conducts Management Reviews annually, the meeting record (FM1-QM.SLQ018) must include, or reference attached documentation confirming, that all required review inputs listed in this section were addressed during the calendar year covered by the review. If any required input was not available or not addressed during the annual review, the meeting minutes shall include a documented justification and identify when the input will be reviewed."
- Provide exact draft language for this addition.

**Audit compliance edits — OFI #9 (Management Representative role designation, recommended):**
The procedure references a "Management Representative" role throughout but the QMS does not formally define this designation. Under ISO 13485:2016 Section 5.5.2, the Management Representative must be formally designated with defined responsibilities.

Required change:
- Location: Section 5 Responsibilities — add or modify the Management Representative description
- Current text describes the Management Representative's responsibilities but does not state who holds this designation by title or how it is formally assigned.
- Add: "The Management Representative is formally designated by senior management and the designation is documented in the Quality Manual (QM.SLQ027). The Management Representative is responsible for ensuring that QMS processes are established, implemented, and maintained; reporting to senior management on QMS performance; and promoting awareness of customer and regulatory requirements throughout the organization, consistent with ISO 13485:2016 Section 5.5.2."
- Provide exact draft language.

**Regulatory reference updates (OFI #8):**

Update 1:
- Location: Section 1 Purpose, second bullet
- Current text (verbatim): "To ensure the activities conducted during Management Review (MR) encompass and fulfill the FDA Quality System Regulation (QSR) and ISO 13485:2016 requirements for periodic Management Review of the Quality System."
- Replace with: "To ensure the activities conducted during Management Review (MR) encompass and fulfill the FDA Quality Management System Regulation (QMSR) and ISO 13485:2016 requirements for periodic Management Review of the Quality System."

Update 2:
- Location: Section 3 Reference Documents
- Current text (verbatim): "21 CFR 820	Quality System Regulation (820.20 – Management Responsibility)"
- Replace with: "21 CFR Part 820	Quality Management System Regulation (QMSR) (820.20 – Management Responsibility)"

Update 3:
- Location: Section 4 Abbreviations
- If "QSR" is listed as an abbreviation (confirm during document review), add or replace with: "QMSR: Quality Management System Regulation (21 CFR Part 820, as revised)"

**Associated form FM1-QM.SLQ018 (Management Review Meeting Minutes):**
- Search `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/` for FM1-QM.SLQ018
- Read the form and identify any FileHold references or QSR references
- Determine if the form should be updated to include a field for documenting coverage of all required annual review inputs (to support OFI #3)
- Specify required changes or state "No revision required"

---

### Document 5: QM.SLQ021 Product Complaint System SOP (Rev D → Rev E)

**Associated forms/templates:** FM1-QM.SLQ021 Product Complaint File (PCF), TMP1-QM.SLQ021 Complaint Response Letter Template

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ021 D Product Complaint System SOP.md`

**FileHold references to find and replace (2 confirmed):**

Reference 1:
- Location: Section 4 General Definitions
- Current text (verbatim): "FileHold: Software based document management system used to electronically store controlled documents."
- Replace with: "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."

Reference 2:
- Location: Section 9 PCF Quality Records Retention, last sub-bullet
- Current text (verbatim): "Records are to be scanned and imported into FileHold by QA and filed within appropriate complaint folder."
- Replace with: "Records are to be uploaded to Silq eQMS Admin Docs, Complaint Records."

**Audit compliance edits — mNC #6 (MANDATORY — complaint trend escalation to CAPA):**
Current Section 7 (Procedure: Complaint Trending) defines trend reporting requirements but does not specify criteria for escalating complaint trends to the CAPA system.

Current language:
- "Complaint trends shall be generated on a quarterly basis and in conjunction with the Quality System Management Review meeting. At a minimum, trend reports shall include the following: Quantity of complaints received per quarter; Complaint frequencies per quarter; Top complaint issues; Complaint System Aging."

Required change: Add escalation criteria following the current trend report requirements. The new language must define specific, objective criteria that trigger mandatory CAPA initiation. Minimum criteria to include:
- Any single complaint type that represents 3 or more occurrences in a rolling 12-month period
- Any complaint trend showing a statistically significant increase in frequency over two or more consecutive quarters
- Any complaint involving a potential serious injury or death (regardless of MDR reportability determination)
- Any complaint category identified as increasing in frequency during management review

Draft language: Add a new sub-section immediately following the complaint trending bullet list:

"Complaint Trend Escalation to CAPA: When complaint trend analysis identifies any of the following conditions, QA shall initiate a CAPA in accordance with QM.SLQ016 within 30 calendar days of identification: (a) any single complaint category with three or more occurrences within a rolling 12-month period; (b) any complaint category demonstrating an increase in frequency across two or more consecutive quarterly trend reports; (c) any complaint involving a patient death or serious injury; or (d) any complaint trend identified by the Management Review committee as requiring corrective action. The rationale for initiating or not initiating a CAPA for each identified trend shall be documented in the quarterly trend report."

Provide the exact draft language for this sub-section.

**Quality Plan additions — Complaint Non-Investigation Rationale (MANDATORY, QMSR 820.35):**
The 2026 Quality Plan states: "ISO 13485 clause 8.2.2 and QMSR section 820.35 require that when a complaint is not investigated, the documented rationale must be retained. QM.SLQ021 does not currently contain an explicit requirement for this."

Required change:
- Location: Section 7 Procedure, following Section 7.5 (Complaint Investigation section) which states "Complaints shall be investigated in accordance with Section 7.4" and "The complaint investigation shall be completed within 30 calendar days from the date the complaint was reported."
- Add a new sub-section: "Complaints Not Requiring Investigation: If QA determines that a complaint does not require investigation, the rationale for the non-investigation decision shall be documented in FM1-QM.SLQ021 and retained in the complaint file. Non-investigation decisions are subject to QA management review. Documented rationale must reference applicable criteria (e.g., erroneous information, device not manufactured by SILQ, or confirmed user error with no device performance issue and no death or serious injury) consistent with the requirements of QMSR section 820.35."
- Provide exact draft language for this addition.

**Quality Plan additions — Complaint/Advisory/MDR Escalation Pathway:**
The 2026 Quality Plan states: "Ownership boundaries between complaint handling (QM.SLQ021), advisory notice/recall (QM.SLQ030), and MDR reporting (QM.SLQ022) are not consolidated in a single reference."

Required change (streamlined approach — single cross-reference table):
- Location: Add a new section to QM.SLQ021 — recommend placing it as a new Section 8 (before current Section 8 Complaint Log, renumbering as needed), titled "Event Escalation and Regulatory Pathway Cross-Reference"
- Add a brief introductory sentence and the following cross-reference table:

"The following table summarizes the escalation pathway from complaint receipt to regulatory action. Refer to the referenced procedures for full requirements.

| Event Type | Responsible Procedure | Decision Owner | Timing |
|---|---|---|---|
| Initial complaint receipt and investigation | QM.SLQ021 (this procedure) | QA | Within 30 calendar days |
| MDR reportability determination | QM.SLQ022 Medical Device Reporting | QA/RA | Within 20 days (5 days if urgent) |
| eMDR submission to FDA | QM.SLQ023 eMDR Submission Work Instruction | Regulatory Affairs | Within 30 days (5 days if urgent) |
| Advisory notice determination | QM.SLQ030 Advisory Notices and Recalls | QA + Executive Management | Based on risk analysis findings |
| Field Safety Corrective Action / Recall initiation | QM.SLQ030 Advisory Notices and Recalls | QA + Executive Management | Within 10 working days of FSCA initiation (FDA report) |
| CAPA initiation (complaint trend) | QM.SLQ016 Corrective and Preventive Action | QA | Per Section 7.10 criteria above |"

Provide the exact draft language for this section.

**Regulatory reference updates (OFI #8):**

Update 1:
- Location: Section 3 Reference Documents
- Current text (verbatim): "21 CFR 820.198	Complaint Files"
- Replace with: "21 CFR Part 820 (QMSR) Section 820.198	Complaint Files"

Update 2:
- Location: Section 4 Abbreviations
- Current text (verbatim): "HIPPA:  Health Insurance Portability and Accountability Act"
- Note: This is a persistent typo — "HIPPA" should be "HIPAA." Correct the spelling to: "HIPAA:  Health Insurance Portability and Accountability Act"
(Note to originator: this is a typo correction, not a substantive change. No mNC or OFI is associated with this; it is simply correct practice.)

**Associated form FM1-QM.SLQ021 and TMP1-QM.SLQ021:**
- Read each file in `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/`
- Identify any FileHold references in form instructions or fields
- For FM1-QM.SLQ021: Determine if a field or section should be added to capture non-investigation rationale (to support the QMSR 820.35 addition above)
- Specify required changes or state "No revision required" for each

---

### Document 6: QM.SLQ022 Medical Device Reporting SOP (Rev B → Rev C) [Logical Addition]

**Rationale for inclusion:** QM.SLQ022 is directly referenced by two other DCO093 documents (QM.SLQ021 and QM.SLQ023), has a specific audit finding (OFI #5) and a Quality Plan action item requiring addition of QMSR framing language. Revising these companion documents while leaving QM.SLQ022 unreferenced would create an inconsistency in the document cluster. This document is listed in DC.SLQ002 Phase 2 scope.

**Associated forms:** FM1-QM.SLQ021 Product Complaint File (PCF) — referenced but owned by QM.SLQ021

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ022 B Medical Device Reporting.md`

**FileHold references:**
The readable text of QM.SLQ022 B does not display a "FileHold" definition in the Definitions section or a filing instruction in the Quality Records section. Before concluding no changes are required for this driver, the agent must verify by searching the original document at `QMSDocuments/` or wherever the source docx is located.

Search instruction: Run a search for "FileHold" within the QM.SLQ022 B source documents. If any references are found, quote them verbatim and provide exact replacements per the translation table. If no FileHold references are confirmed in the original docx, state "No FileHold references confirmed — no EDMS transition edit required for this document."

**Audit compliance edits — OFI #5 (Decision methodology and UDI, recommended):**

Gap 1 — Reportability Decision Methodology:
Current Section 6.2 (Determination of Reportability) provides detailed criteria for what constitutes an MDR reportable event but does not establish a structured decision tool or step-by-step decision logic.

Required change:
- Location: Section 6.2 Determination of Reportability, following the existing list of MDR trigger criteria
- Add a decision logic summary: "When evaluating whether a complaint requires an MDR report, QA/RA shall apply the following sequential decision framework: (1) Was the device manufactured or imported by SILQ? If No — MDR not required. If Yes — proceed to (2). (2) Is there information reasonably suggesting the device may have caused or contributed to a death or serious injury, or that a reportable malfunction occurred? If No — MDR not required; document rationale. If Yes — proceed to (3). (3) Does a qualified person (per 21 CFR 803.3 definition) confirm the assessment? If the answer requires clinical expertise beyond internal resources, consult SILQ's Medical Safety Consultant or designee. Document the full determination in FM1-QM.SLQ021 Section 3 regardless of outcome."
- Provide exact draft language.

Gap 2 — UDI in MDR submissions:
Current Section 6.3 (Reporting MDRs to FDA) describes the reporting process but does not address UDI inclusion.

Required change:
- Location: Section 6.3 Reporting MDRs to FDA, following the instruction to prepare the eMDR per QM.SLQ023
- Add: "In accordance with 21 CFR 803.52(e), the MDR report shall include the Unique Device Identifier (UDI) for the affected device where available. QA/RA shall confirm that the correct UDI is included in the applicable section of the MedWatch 3500A form (FDA Form 3500A, Section D) prior to submission."
- Provide exact draft language.

**Quality Plan additions — Regulatory Reporting QMSR Framing:**
The 2026 Quality Plan states: "Add a brief 'applicable regulatory requirements' statement to QM.SLQ022 or QM.SLQ030 referencing the QMSR section 820.10(b) overlay and confirming Silq's reporting procedures satisfy this provision."

Required change:
- Location: Section 1 Purpose or Section 2 Scope — add a brief QMSR framing statement
- Add: "This procedure is implemented as part of SILQ's Quality Management System in compliance with the applicable regulatory requirements of the FDA Quality Management System Regulation (QMSR), 21 CFR Part 820 Section 820.10(b). SILQ's MDR reporting activities under this procedure satisfy the applicable regulatory reporting requirements imposed by 21 CFR Part 803 as referenced in the QMSR supplementary provisions framework."
- Provide exact draft language and specify the exact location within the document.

**Regulatory reference updates (OFI #8):**
- The document's Reference Documents section cites "21 CFR Parts 803 and 806" — these are correct regulatory citations and should be retained as-is.
- If any "21 CFR 820 Quality System Regulation" text is found in the document body, update to "21 CFR Part 820 Quality Management System Regulation (QMSR)."
- If "QSR" abbreviation appears, add/update "QMSR: Quality Management System Regulation (21 CFR Part 820, as revised)" to the Abbreviations section.

---

### Document 7: QM.SLQ023 eMDR Submission Work Instruction (Rev A → Rev B)

**Associated forms:** FM1-QM.SLQ021 Product Complaint File (PCF) — referenced but owned by QM.SLQ021

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ023 A eMDR Submission Work Instruction.md`

**FileHold references to find and replace (2 confirmed):**

Reference 1:
- Location: Section 4 General Definitions
- Current text (verbatim): "FileHold:  Software based document management system used to electronically store controlled documents."
- Replace with: "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."

Reference 2:
- Location: Section 6 Procedure — last sentence of the document (Section 6.18 or equivalent)
- Current text (verbatim): "QA/RA will import into appropriate complaint file and MDR file within FileHold."
- Replace with: "QA/RA will upload the completed eMDR PDF to Silq eQMS Admin Docs, Complaint Records, MDR Files, within the applicable complaint file."

**Practical consideration — FDA eSubmitter software currency:**
This work instruction contains detailed, step-by-step UI instructions for FDA's eSubmitter software (coffee cup icon, screen navigation, packaging steps) and multiple URLs to FDA websites. These instructions may not reflect the current state of the eSubmitter software, which FDA periodically updates, or the current FDA website URL structure.

Required advisory to originator:
- Location: Section 6 Procedure header or as a note at the beginning of Section 6
- Add a note: "Note: These work instructions describe the eMDR submission process as of the effective date of this document. The FDA eSubmitter software interface and the FDA ESG Web Trader Hosted Solution (WTHS) may be updated periodically. If the interface described in this work instruction does not match the current software, refer to the current eSubmitter User Manual available through the eSubmitter Help menu and the current FDA ESG instructions at www.fda.gov/esg for updated navigation guidance."
- Provide exact draft language for this note.

Additionally, advise the originator to verify that the following URLs referenced in the document are still active and current (these were accurate as of the original WI creation date but may have changed):
- https://www.fda.gov/Safety/MedWatch/HowToReport/DownloadForms/ucm149236.htm
- https://www.fda.gov/medicaldevices/deviceregulationandguidance/postmarketrequirements/reportingadverseevents/mdradverseeventcodes/default.htm
- https://www.fda.gov/forindustry/fdaesubmitter/ucm193862.htm

Advise the originator whether these FDA page URLs should be updated to current equivalents or replaced with the FDA's top-level MDR resources page (https://www.fda.gov/medical-devices/mandatory-reporting-requirements-manufacturers-importers-and-device-user-facilities/how-submit-medical-device-reports) and the current eSubmitter page. This is a practical compliance and usability consideration — outdated URLs in a controlled WI can cause user confusion.

**No mNC/OFI directly assigned to QM.SLQ023** in IA-2025. This revision is primarily EDMS transition and the practical URL/software advisory above.

**Regulatory reference updates (OFI #8):**
- The document's Reference Documents section does not list 21 CFR 820. No direct regulatory reference update is required.
- Confirm that no QSR or old Part 820 language exists in the document body.

---

### Document 8: QM.SLQ028 Protection of Confidential Patient Information (Rev A → Rev B)

**Associated forms:** None listed.

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ028 A Protection of Confidential Patient Information.md`

**FileHold references to find and replace (2 confirmed):**

Reference 1:
- Location: Section 4 General Definitions
- Current text (verbatim): "FileHold: Software based document management system used to electronically store controlled documents."
- Replace with: "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."

Reference 2:
- Location: Section 6 Procedure, second numbered step
- Current text (verbatim): "If the confidential patient information is computer-based information, e.g. images, electronic data, the confidential patient information shall be maintained in FileHold. Access is given to SILQ employees meeting the definition of Authorized Users."
- Replace with: "If the confidential patient information is computer-based information, e.g. images, electronic data, the confidential patient information shall be maintained in Silq eQMS. Access is restricted to SILQ employees meeting the definition of Authorized Users through role-based access controls administered within Silq eQMS."

**Audit compliance edits — mNC #8 (MANDATORY — internet transmission prohibition and information security):**

This is the most critical substantive edit in this document. Current Section 6 Procedure, third numbered step contains the following text:

Current text (verbatim): "All information obtained, generated or handled, whether paper-based or computer-based information and other electronic, visual or digital media is considered the property of SILQ. This information may not be physically removed from SILQ's facility or transmitted over the Internet. Employees will take the utmost care to protect the privacy and confidentiality of protected patient information. When reasonably possible, documents containing confidential patient information should be de-identified (removal of patient name and initials) so that the confidential information cannot be traced to that individual.  A patient ID number may be used in place of patient name or initials"

The phrase "may not be...transmitted over the Internet" is a blanket prohibition that directly conflicts with current regulatory operations (e.g., eMDR submission via FDA ESG portal per QM.SLQ023, complaint correspondence with clinicians via email). mNC #8 requires this to be corrected.

Required change — replace the blanket prohibition with risk-based, operationally accurate security language:

Replace the cited paragraph with: "All information obtained, generated, or handled — whether paper-based, computer-based, or in other electronic, visual, or digital media — is considered the property of SILQ. Such information shall not be transmitted, shared, or disclosed outside of SILQ except: (a) as required to fulfill regulatory reporting obligations (e.g., MDR submissions to FDA per QM.SLQ022 and QM.SLQ023); (b) as required for complaint investigation activities involving contract organizations or authorized representatives; or (c) as otherwise authorized under applicable HIPAA Privacy Rule requirements (45 CFR Parts 160 and 164). When transmitting confidential patient information electronically, SILQ personnel shall use secure, encrypted transmission methods. Unauthorized or unapproved transmission of confidential patient information is prohibited. Employees will take the utmost care to protect the privacy and confidentiality of protected patient information. When reasonably possible, documents containing confidential patient information should be de-identified (removal of patient name and initials). A patient ID number may be used in place of patient name or initials."

Additionally, add a new sub-section following the above paragraph to address the remaining gaps identified in mNC #8:

"Role-Based Access Controls: Access to confidential patient information maintained in Silq eQMS is controlled through role-based access permissions. Only Authorized Users (as defined in this procedure) are granted access to records containing confidential patient information. Access rights are administered by the Silq eQMS system administrator and are reviewed periodically to ensure access is limited to personnel with a current job-related need."

"Data Breach Response: In the event of an actual or suspected unauthorized access, disclosure, or loss of confidential patient information, the employee who becomes aware of the incident shall immediately notify QA management. QA management shall evaluate the incident to determine applicable notification obligations under HIPAA and any applicable state law, and shall document the evaluation and any resulting actions in accordance with QM.SLQ016 CAPA SOP."

Provide exact draft language for the full revised paragraph and both new sub-sections.

**Regulatory reference updates (OFI #8):**
- The document references "ISO 13485:2016" and "45 CFR Part 160 and Part 164 (Subparts A and E) HIPAA Privacy Rule" — these are correct and current. Retain as-is.
- Confirm during document review whether any "21 CFR 820" or "QSR" references are present. If so, update per translation table.

---

### Document 9: QM.SLQ030 Advisory Notices and Recalls SOP (Rev A → Rev B) [Logical Addition]

**Rationale for inclusion:** QM.SLQ030 is directly referenced by QM.SLQ021 (Product Complaint SOP) and QM.SLQ022 (MDR SOP), both of which are being revised in DCO093. The Advisory Notice and Recall procedure has two confirmed FileHold references, an applicable audit finding (OFI #6), and a Quality Plan action item (QMSR regulatory reporting framing). Including it in DCO093 avoids leaving an unrevised document in the same complaint/MDR procedural cluster. DCO094 will handle the remaining non-design related Phase 2 documents.

**Associated forms:** FM1-QM.SLQ030 (Recall Report to FDA), FM2-QM.SLQ030 (FSCA Report EU), FM3-QM.SLQ030 (Field Safety Notice), FM4-QM.SLQ030 (Advisory and Recall Notices Distribution Log)

Current readable text: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ030 A Advisory Notices and Recalls SOP.md`

**FileHold references to find and replace (2 confirmed):**

Reference 1:
- Location: Section 6 Procedure — Section 6.11.4 (Field Safety/Recall Notice distribution, return receipts)
- Current text (verbatim): "Distribution of Field Safety Notices may be electronic (email or fax) or via the mail. In all cases, return receipt for the notice is required and will be stored in a separate Advisory Notice/Recall file related to the issue in appropriate folder within FileHold."
- Replace with: "Distribution of Field Safety Notices may be electronic (email or fax) or via the mail. In all cases, return receipt for the notice is required and will be uploaded to Silq eQMS Admin Docs, CAPA Records, Advisory Notice and Recall Files, within the applicable CAPA file."

Reference 2:
- Location: Section 6 Procedure — Section 6.11.6 (FM4 distribution log)
- Current text (verbatim): "Use FM4-QM.SLQ030 Advisory and Recall Notices Distribution Log to track the status of the notice distribution activities. Once complete, scan and import the log with the Advisory Notice/Recall file in appropriate folder within FileHold."
- Replace with: "Use FM4-QM.SLQ030 Advisory and Recall Notices Distribution Log to track the status of the notice distribution activities. Once complete, upload the log to Silq eQMS Admin Docs, CAPA Records, Advisory Notice and Recall Files, within the applicable CAPA file."

**Note on Definitions:** QM.SLQ030 does not appear to have a "FileHold" entry in the Definitions section. Confirm during document review. If present, replace per translation table.

**Audit compliance edits — OFI #6 (Recall metrics trending, recommended):**
Current procedure does not include requirements to track and trend recall-related metrics over time.

Required change:
- Location: Add a new section to Section 6 Procedure or add a new standalone section titled "Recall Metrics and Trending," placed after the Quality Records section
- Add: "Recall and Advisory Notice Metrics: QA shall maintain a log of all advisory notices and recalls (Field Safety Corrective Actions) initiated by SILQ. At minimum, this log shall capture: (a) advisory notice or recall identifier; (b) associated CAPA number; (c) product(s) and lot numbers affected; (d) recall classification (if FDA recall); (e) date initiated; (f) date of FDA report submission (if applicable); (g) effectiveness check completion status and outcome; and (h) date of recall closure. Recall and advisory notice data shall be reported and trended at Management Review as part of the post-market surveillance input. Trend data shall include the number of advisory notices and recalls per period and any patterns identified in recall root causes. Trend data that indicates a recurring failure type shall be escalated to the CAPA system per QM.SLQ016."
- Provide exact draft language for this addition.

**Quality Plan additions — Regulatory Reporting QMSR Framing:**
The 2026 Quality Plan states that neither QM.SLQ022 nor QM.SLQ030 includes an explicit crosswalk to QMSR section 820.10(b).

Required change:
- Location: Section 1 Purpose or Section 2 Scope
- Add: "This procedure is implemented as part of SILQ's Quality Management System in compliance with the applicable regulatory requirements of the FDA Quality Management System Regulation (QMSR), 21 CFR Part 820 Section 820.10(b). SILQ's advisory notice and recall activities under this procedure satisfy applicable reporting requirements imposed by 21 CFR Part 806 (Reports of Corrections and Removals) and 21 CFR Part 810 (Medical Device Recall Authority) as referenced in the QMSR supplementary provisions framework."
- Provide exact draft language.

**Regulatory reference updates (OFI #8):**

Update 1:
- Location: Section 3 Reference Documents
- Current text (verbatim): "21 CFR 820.198	FDA Quality System Regulation – Complaint Files"
- Replace with: "21 CFR Part 820 (QMSR) Section 820.198	Complaint Files"

Update 2:
- Location: Section 3 Reference Documents
- Current text (verbatim): "EN ISO 14971:2012	Application of Risk Management to Medical Devices"
- Replace with: "ISO 14971:2019	Medical devices – Application of risk management to medical devices"
(The 2012 edition has been superseded by ISO 14971:2019, which QM.SLQ012 and QM.SLQ013 already reference correctly.)

Update 3:
- If any "QSR" abbreviation is used in the document body (confirm during review), update per translation table.

**Associated forms FM1–FM4-QM.SLQ030:**
- Search `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/` for each form
- Read each and identify any FileHold-specific instructions embedded in form fields, footer, or instructions
- Specify required changes or state "No revision required" for each form

---

## DCO093 DOCUMENT TABLE

Include the following table in your editing guide as the DCO093 document package table (for use on FM1-QM.SLQ001 Rev B, the DCO form):

| Document Title | Document Number | Current Rev | Target Rev | Primary Change Drivers |
|---|---|---|---|---|
| Risk Management SOP | QM.SLQ012 | B | C | DC.SLQ002 EDMS Transition; OFI #1 (Risk Management Report consolidation); OFI #10 (FDA QMS linkage); 2026 Quality Plan (post-production trigger criteria); OFI #8 |
| Risk Management Plan Template | TMP1-QM.SLQ012 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition |
| Risk Analysis SOP | QM.SLQ013 | B | C | DC.SLQ002 EDMS Transition; mNC #3 (mandatory risk eval for design changes); OFI #2 (traceability to design controls); OFI #8 |
| PHA Template | TMP1-QM.SLQ013 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition |
| Hazards Analysis Table Template | TMP2-QM.SLQ013 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition |
| FMEA Worksheet Template | TMP3-QM.SLQ013 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition |
| CAPA SOP | QM.SLQ016 | C | D | DC.SLQ002 EDMS Transition; OFI #8 |
| CAPA Report Form | FM1-QM.SLQ016 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition |
| Management Review SOP | QM.SLQ018 | A | B | DC.SLQ002 EDMS Transition; OFI #3 (annual input coverage); OFI #9 (Management Representative designation); OFI #8 |
| Management Review Meeting Minutes | FM1-QM.SLQ018 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition; OFI #3 |
| Product Complaint System SOP | QM.SLQ021 | D | E | DC.SLQ002 EDMS Transition; mNC #6 (CAPA escalation criteria); 2026 Quality Plan (non-investigation rationale, escalation pathway); OFI #8 |
| Product Complaint File Form | FM1-QM.SLQ021 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition; mNC #6 |
| Complaint Response Letter Template | TMP1-QM.SLQ021 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition |
| Medical Device Reporting SOP | QM.SLQ022 | B | C | DC.SLQ002 EDMS Transition (verify); OFI #5 (reportability methodology, UDI); 2026 Quality Plan (QMSR framing); OFI #8 |
| eMDR Submission Work Instruction | QM.SLQ023 | A | B | DC.SLQ002 EDMS Transition; software/URL currency advisory; OFI #8 |
| Protection of Confidential Patient Information SOP | QM.SLQ028 | A | B | DC.SLQ002 EDMS Transition; mNC #8 (internet prohibition removal, secure transmission, RBAC, data breach); OFI #8 |
| Advisory Notices and Recalls SOP | QM.SLQ030 | A | B | DC.SLQ002 EDMS Transition; OFI #6 (recall metrics trending); 2026 Quality Plan (QMSR framing); OFI #8 |
| Advisory and Recall Notices Distribution Log | FM4-QM.SLQ030 | (check current rev) | (next rev, if changes needed) | DC.SLQ002 EDMS Transition |

For any associated forms where no changes are required after reading the current form content, note this explicitly in the DCO table with "No revision required."

---

## WHAT YOUR EDITING GUIDE MUST CONTAIN

For each of the nine SOPs/WIs and all associated forms, provide a dedicated section with:

### Section Format for Each Document

```
## [Document Number] [Document Title] (Rev [X] → Rev [Y])

### Summary of Changes Required
[One paragraph overview of total change scope across all three drivers]

### 1. FileHold Reference Replacements
For each FileHold reference:
- Location: [Section number and name]
- Current text (verbatim): "[exact current text]"
- Replace with: "[exact new text]"
- Notes: [Any special considerations]

### 2. Audit Compliance Edits
For each mNC/OFI:
- Finding: [mNC #X or OFI #X — brief description]
- Location: [Section number and name]
- Current text (verbatim): "[exact current text, or 'No current text — addition required']"
- Required change: [Exact new language, or detailed description of addition]
- Regulatory basis: [ISO 13485:2016 clause, 21 CFR 820 / QMSR section, etc.]

### 3. Quality Plan Additions
For each Quality Plan item:
- Quality Plan Action: [Brief description of the action item]
- Location: [Section number and name]
- Current text (verbatim): "[exact current text anchor point, or 'New section']"
- Required addition: [Exact new language]

### 4. Regulatory Reference Updates (OFI #8)
For each regulatory reference:
- Location: [Section number and name]
- Current text: "[current]"
- Replace with: "[updated]"

### 5. Definition Section Updates
- Remove "FileHold" definition
- Add "Silq eQMS" definition (standard text from Phase 1A)
- Update "QSR" to "QMSR" if present
- Correct any other definition-level errors (e.g., HIPPA → HIPAA in QM.SLQ021)

### 6. Associated Forms
For each associated form, after reading the current form content:
- [Either specify required changes, or state "No revision required"]
```

---

## HOW TO BEGIN

1. Read all nine SOP/WI readable texts listed above from the `docs/QMS-Readable-Texts/01-QM-Documents/` folder. You may have access to some already; read all that you have not yet read in full.
2. Read all associated form and template readable texts from `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/`. Search for each form/template number.
3. Read the IA-2025 Final Report (already partially summarized in this prompt): `docs/QMS-Readable-Texts/20-QMSInProcess/CAPA004/IA-2025 Final Report Readable.md`
4. Read the 2026 Silq Quality Plan: `docs/QMS-Readable-Texts/20-QMSInProcess/Quality Planning Documents/Silq 2026 Quality Plan.md`
5. Read QM.SLQ001 Rev B at `docs/QMS-Readable-Texts/20-QMSInProcess/DCO091/QM.SLQ001 B Document Control SOP.md` to confirm the established Phase 1A Silq eQMS language.
6. Create the folder `docs/DCO093/` if it does not exist.
7. Write your complete editing guide to `docs/DCO093/DCO093_PHASE2_EDITING_GUIDE.md`.

---

## QUALITY EXPECTATIONS

- Every FileHold reference in every document must be identified and replaced. Do not miss any. Read each source document fully and search for the string "FileHold" (case-insensitive).
- For mNC #8 (QM.SLQ028), the substantive replacement of the internet prohibition with risk-based information security language is mandatory and critical. This addresses a direct compliance finding.
- For mNC #6 (QM.SLQ021), the CAPA escalation criteria must be specific and objective — not aspirational language. The criteria must be measurable so that trending QA personnel can apply them without interpretation.
- For mNC #3 (QM.SLQ013), the requirement for systematic risk evaluation on design changes must be stated as mandatory, not optional or "as needed."
- All new Silq eQMS storage location language must specify which Admin Docs library and appropriate subfolder for each document type (do not leave the filing destination vague).
- QMSR regulatory reference updates must be consistent across all documents.
- The Quality Plan additions are primarily single-sentence or short-paragraph additions that achieve meaningful compliance coverage with minimal procedural complexity. Keep these additions concise and actionable.
- For QM.SLQ023 (eMDR WI), the software currency advisory is a best-practice addition that protects the integrity of the WI over time. Note it clearly so the originator can make an informed decision.
- For QM.SLQ022, confirm whether FileHold references exist in the original docx before asserting no EDMS change is needed.
- The guide must be detailed enough that a reviewer can assess the adequacy of the proposed changes for regulatory compliance purposes. Quote verbatim current text for every change so the originator can locate the exact section in Word.

---

## NOTE ON DCO094

DCO094 will cover the remaining non-design-related Phase 2 documents from DC.SLQ002 that are not included in DCO093. These are expected to include documents such as QM.SLQ025, QM.SLQ027, QM.SLQ029, QM.SLQ033, QM.SLQ038, QM.SLQ039, QM.SLQ043, QM.SLQ045, QM.SLQ046, QM.SLQ047, QM.SLQ048, QM.SLQ049, QM.SLQ050, QM.SLQ051, and others in the Phase 2 scope list. DCO094 will also address the remaining audit mNCs not covered in DCO091, DCO092, or DCO093 (specifically mNCs #9, #10, #11, #12, #14, #15 and any applicable OFIs for those documents). This context is provided so that the editing guide for DCO093 does not inadvertently scope creep into DCO094 territory.

---

*This prompt was prepared by the QMS management agent on June 9, 2026. All source documents referenced are in the SilqQMS project folder at `c:\Users\Ethan\OneDrive\Desktop\SilqQMS`.*
