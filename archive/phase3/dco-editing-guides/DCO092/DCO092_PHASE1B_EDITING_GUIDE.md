# DCO092 Phase 1B — Document Editing Guide

**Prepared by:** QMS Agent  
**Date:** May 28, 2026  
**Design Project:** DC.SLQ002 — Silq eQMS EDMS Transition  
**DCO Number:** DCO092  
**Phase:** Phase 1B  
**Document originator:** Ethan Rao

---

## OVERVIEW

This guide provides a complete, document-by-document set of instructions for revising the five SOPs and their associated forms included in DCO092. Every required change is specified verbatim: the originator can open each Word document and make every edit directly from this guide without ambiguity.

> **Scope note:** QM.SLQ004 (Design Control Program SOP) and FM1-QM.SLQ004 have been **deferred from DCO092**. They will be addressed in a dedicated Design Controls DCO covering QM.SLQ004, QM.SLQ005, and QM.SLQ006. Section 7 of this guide (QM.SLQ004 editing instructions) is retained for reference and may be incorporated into that future DCO package.

Each document revision is driven by **two independent requirements:**

1. **DC.SLQ002 EDMS Transition** — Replace all FileHold references with Silq eQMS equivalents, consistent with the language established in QM.SLQ001 Rev B and QM.SLQ014 Rev C.
2. **IA-2025 Internal Audit / CAPA004** — Implement procedural changes to address Minor Non-Compliances (mNCs) and applicable Opportunities for Improvement (OFIs) from the April 2026 internal audit.

QM.SLQ004 had a **third driver** (CAPA003 corrective actions from October 2025 FDA 483 Observation 2), but that document is deferred to a dedicated Design Controls DCO.

---

## SECTION 1 — DCO092 DOCUMENT TABLE

*For use on FM1-QM.SLQ001 Rev B (Document Change Order form). If a form has no required changes after review, it is noted as "No revision required."*

| Document Title | Document Number | Current Rev | Target Rev | Primary Change Drivers |
|---|---|---|---|---|
| Employee Training SOP | QM.SLQ003 | B | C | DC.SLQ002 EDMS Transition; OFI #7 (training effectiveness language); OFI #8 (regulatory refs) |
| Employee Training Program Form | FM1-QM.SLQ003 | A | A | No revision required |
| Employee Training Record Form | FM2-QM.SLQ003 | B | B | No revision required |
| Internal Audits SOP | QM.SLQ017 | A | B | DC.SLQ002 EDMS Transition; OFI #8 |
| Internal Quality Audit Schedule | FM1-QM.SLQ017 | B | B | No revision required |
| Internal Quality Audit Checklist | FM2-QM.SLQ017 | A | B | OFI #8 (regulatory reference header update) |
| Internal Quality Audit Final Report | FM3-QM.SLQ017 | A | A | No revision required |
| Certificate of Internal Audit | FM4-QM.SLQ017 | A | A | No revision required |
| Auditor Qualification Record | FM5-QM.SLQ017 | A | A | No revision required |
| Purchasing Controls SOP | QM.SLQ020 | D | E | DC.SLQ002 EDMS Transition; mNC #5 (mandatory supplier change notification); OFI #8 |
| Purchase Order Form | FM1-QM.SLQ020 | B | B | No revision required (see note in Section 4.5) |
| Sales Order SOP | QM.SLQ036 | E | F | DC.SLQ002 EDMS Transition; OFI #8 |
| Sales Order Form | FM1-QM.SLQ036 | A | A | No revision required |
| Supplier Quality Assurance SOP | QM.SLQ015 | B | C | DC.SLQ002 EDMS Transition; mNC #4 (risk-based frequencies); OFI #4 (self-assessment justification); OFI #8 |
| Supplier Quality Self-Assessment Survey – Mfg | FM1-QM.SLQ015 | A | B | OFI #4 (add risk justification field in Results section) |
| Supplier Quality Self-Assessment Survey – Test Services | FM2-QM.SLQ015 | A | B | OFI #4 (add risk justification field in Results section) |
| Category II Supplier Assessment Form | FM3-QM.SLQ015 | A | A | No revision required |
| Supplier Re-Evaluation Form | FM4-QM.SLQ015 | A | A | No revision required |
| Certificate of Audit Form | FM5-QM.SLQ015 | A | A | No revision required |
| SILQ Approved Supplier List Form | FM6-QM.SLQ015 | B | B | No revision required |
| Supplier Assessment Schedule / Status Form | FM7-QM.SLQ015 | A | B | mNC #4 (add Category and Risk Basis columns) |
| Supplier Corrective Action Request Form | FM8-QM.SLQ015 | A | A | No revision required |
| ~~Design Control Program SOP~~ | ~~QM.SLQ004~~ | ~~B~~ | ~~C~~ | **DEFERRED — excluded from DCO092. Will be addressed in a dedicated Design Controls DCO covering QM.SLQ004, QM.SLQ005, and QM.SLQ006.** |
| ~~Design Project Scope Form~~ | ~~FM1-QM.SLQ004~~ | ~~A~~ | ~~B~~ | **DEFERRED — excluded from DCO092. Covered in dedicated Design Controls DCO.** |

---

## SECTION 2 — QM.SLQ003 Employee Training SOP (Rev B → Rev C)

### Summary of Changes Required

This document requires fourteen changes to FileHold and legacy paper-based language. All scan-and-import instructions are replaced with direct electronic upload to Silq eQMS Admin Docs, Training Records. The in-FileHold sign-off feature is removed (Silq eQMS has no in-system sign-off — records are signed outside the system and uploaded as signed documents). Three "Sign-off sheet window" date-location clauses in Section 10 are deleted entirely. The Section 12 monthly print-initial-scan workflow is replaced with a streamlined electronic review-and-upload process. Two body-text "hard copy" references in the interactive training instructions are simplified. The Section 5 Training Coordinator responsibility statement is updated to remove reference to physical archival. The revision also includes two regulatory reference updates per OFI #8, a definition section overhaul, and one training effectiveness language strengthening per OFI #7. No associated forms require revision.

**ISO 13485:2016 basis for streamlining:** §6.2 requires maintaining records of education, training, skills, and experience and that such records "can be as simple or complex as necessary" with no requirement to maintain physical hard copies. §4.2.5 states that "records can be stored or copied in any suitable form (e.g. hardcopy or electronic media)" — electronic-only records fully satisfy this requirement. There is no ISO 13485 requirement to print, date-stamp, or physically archive training matrices or discrepancy reports.

---

### 1. FileHold Reference Replacements

**Change 1 of 14**
- **Location:** Section 5 (Definitions) — General Definitions
- **Current text (verbatim):** `"FileHold:  Software based document management system used to electronically store controlled documents."`
- **Replace with:** `"Silq eQMS:  Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."`
- **Notes:** This replaces the entire FileHold definition entry. The new entry uses "Silq eQMS" as the defined term.

---

**Change 2 of 14**
- **Location:** Section 5 (Responsibilities) — Training Coordinator paragraph (parent sentence)
- **Current text (verbatim):** `"It is the responsibility of the SILQ Training Coordinator to maintain the training matrix to ensure that hard copy training plans and training records are complete, accurate, and archived in storage."`
- **Replace with:** `"It is the responsibility of the SILQ Training Coordinator to maintain the training matrix in Silq eQMS and ensure that training plans and training records are complete, accurate, and uploaded to Silq eQMS Admin Docs, Training Records."`
- **Notes:** Removes the reference to physical "hard copy" archival. ISO 13485:2016 §4.2.5 permits records in any medium; electronic records in Silq eQMS fully satisfy this requirement.

---

**Change 3 of 14**
- **Location:** Section 5 (Responsibilities) — Training Coordinator sub-bullet
- **Current text (verbatim):** `"The Training Coordinator is responsible for scanning and importing pdf of completed training records into appropriate employee training files within FileHold."`
- **Replace with:** `"The Training Coordinator is responsible for uploading completed training records to Silq eQMS Admin Docs, Training Records."`

---

**Change 4 of 14**
- **Location:** Section 6 (Procedure: Identification of Qualifications and Training Requirements) — fifth paragraph
- **Current text (verbatim):** `"Once completed, the training program is signed by both the employee and the department management. The signed record is forwarded to the Training Coordinator and scanned and imported into the employee training file within FileHold."`
- **Replace with:** `"Once completed, the training program is signed by both the employee and the department management. The signed record is forwarded to the Training Coordinator and uploaded to Silq eQMS Admin Docs, Training Records."`

---

**Change 5 of 14**
- **Location:** Section 8 (Procedure: Training) — training sign-off paragraph (subsection 8.3.1 in the formatted SOP)
- **Current text (verbatim):** `"Sign off on training records may be done electronically in FileHold or manually."`
- **Replace with:** `"Completed and signed training records shall be uploaded to Silq eQMS Admin Docs, Training Records."`
- **Notes:** The FileHold in-system electronic sign-off feature does not exist in Silq eQMS. All training records are signed outside of the system (whether on paper or as electronically signed documents) and uploaded as signed documents. Remove the reference to signing "in" the document management system entirely.

---

**Change 6 of 14**
- **Location:** Section 8 (Procedure: Training) — External Training paragraph
- **Current text (verbatim):** `"Hard copies are to be scanned and imported into employee's training file within FileHold."`
- **Replace with:** `"Records are to be uploaded to Silq eQMS Admin Docs, Training Records."`
- **Notes:** This appears in the paragraph beginning "Any external training attended will be documented upon return…"

---

**Change 7 of 14**
- **Location:** Section 9 (Procedure: Completing Employee Training Program Forms) — Training Coordinator paragraph
- **Current text (verbatim):** `"the training coordinator scans the form, and imports into employee file folder within FileHold."`
- **Replace with:** `"the training coordinator uploads the form to Silq eQMS Admin Docs, Training Records."`
- **Notes:** This appears in the paragraph beginning "The training coordinator reviews the form for completeness and resolves any issues with the employee's supervisor. Once complete, the training coordinator scans the form, and imports into employee file folder within FileHold."

---

**Change 8 of 14**
- **Location:** Section 10 (Procedure: Completing the Employee Training Record) — Date of Training field instruction
- **Current text (verbatim):** `"Date of Training: Enter the date of training was conducted. Note: this may be different (earlier) from the date the record is signed. If training signoffs are done electronically, the date of training is located within the "Sign-off sheet" window in FileHold."`
- **Replace with:** `"Date of Training: Enter the date training was conducted. Note: this may be different (earlier) from the date the record is signed."`
- **Notes:** Delete the entire final sentence ("If training signoffs are done electronically…"). Since Silq eQMS does not provide an in-system sign-off feature, that clause is obsolete. All training records are signed outside of Silq eQMS and uploaded as completed signed documents. The instruction is complete without it.

---

**Change 9 of 14**
- **Location:** Section 10 (Procedure: Completing the Employee Training Record) — employee Date field instruction
- **Current text (verbatim):** `"Date: The employee enters the date they signed the record. Note: if training signoffs are done electronically, the date is located within the "Sign-off sheet" window in FileHold."`
- **Replace with:** `"Date: The employee enters the date they signed the record."`
- **Notes:** Delete the trailing "Note: if training signoffs are done electronically…" sentence in full. Since Silq eQMS has no in-system sign-off, this clause is obsolete. The employee date is always the date the employee applied their signature to the record (whether manually or via digital signature outside of Silq eQMS).

---

**Change 10 of 14**
- **Location:** Section 10 (Procedure: Completing the Employee Training Record) — Trainer Date field instruction
- **Current text (verbatim):** `"Date: The trainer enters the date they signed the record. If no trainer was required, enter 'N/A'. Note: if training signoffs are done electronically, the date is located within the "Sign-off sheet" window in FileHold."`
- **Replace with:** `"Date: The trainer enters the date they signed the record. If no trainer was required, enter 'N/A'."`
- **Notes:** Delete the trailing "Note: if training signoffs are done electronically…" sentence in full. This is the Trainer Date field instruction — the second occurrence of this sentence (identical wording to Change 8). Both must be updated. Since Silq eQMS has no in-system sign-off, the note is obsolete.

---

**Change 11 of 14**
- **Location:** Section 10 (Procedure: Completing the Employee Training Record) — final paragraph of Section 10
- **Current text (verbatim):** `"The training coordinator reviews the form for completeness and resolves any issues with the employee. Once complete, the training coordinator scans and imports into employee file folder within FileHold."`
- **Replace with:** `"The training coordinator reviews the form for completeness and resolves any issues with the employee. Once complete, the training coordinator uploads the form to Silq eQMS Admin Docs, Training Records."`

---

**Change 12 of 14**
- **Location:** Section 11 (Retrieval of Training Programs and Training Records) — two sentences
- **Current text (verbatim):** `"Employee training programs and training records are maintained in FileHold."`  
  *and* (separate sentence, same paragraph or following):  
  `"See QM.SLQ014 for instructions on how to retrieve/access employee training programs and training records."`
- **Replace with:**  
  `"Employee training programs and training records are maintained in Silq eQMS."`  
  `"Accessed in Silq eQMS per QM.SLQ014."`
- **Notes:** Both sentences in Section 11 must be updated. The second sentence may be retained almost verbatim or replaced with the shorter approved form.

---

**Change 13 of 14 (three sub-instances in Section 12 — fully revised)**
- **Location:** Section 12 (Procedure: Training Coordinator) — three separate legacy instructions for the monthly training matrix workflow
- **ISO 13485:2016 basis:** §6.2(e) requires maintaining records of training; §4.2.5 states records "can be stored or copied in any suitable form (e.g. hardcopy or electronic media)." There is no requirement to print a snapshot, initial it, and archive it monthly. The live training matrix in Silq eQMS is itself the maintained record.

*Sub-instance A — Monthly matrix review and filing:*
- **Current text (verbatim):** `"the training coordinator is to print a hard copy (or electronic copy) of the training matrix, initial/date, scan and import into FileHold."`
- **Replace with:** `"The training coordinator shall review and update the training matrix in Silq eQMS at least monthly to confirm it reflects current employee training status. The date of each review shall be recorded in the training matrix."`
- **Notes:** Eliminates the print-initial-scan cycle entirely. The training matrix maintained in Silq eQMS is the record of competence; a monthly dated review entry satisfies the ISO 13485:2016 §6.2 record-keeping requirement without generating a separate archived snapshot.

*Sub-instance B — Discrepancy identification and notification:*
- **Current text (verbatim):** `"the training coordinator is to identify training discrepancies, print a hard copy (or electronic copy) of the file, initial/date, scan and import into FileHold."`
- **Replace with:** `"The training coordinator shall identify any training discrepancies and notify the applicable department supervisors via email or written notification. Documentation of the discrepancy review and any notifications sent shall be uploaded to Silq eQMS Admin Docs, Training Records."`
- **Notes:** Removes print-initial-scan requirement. An email or written notification confirming the discrepancy and the action taken is a sufficient and auditable record under ISO 13485:2016 §4.2.5.

*Sub-instance C — Notification action confirmation:*
- **Current text (verbatim):** `"The training coordinator will initial note on the hard copy (or electronic copy) file indicating the notification action has been performed. Scan and import into FileHold."`
- **Replace with:** Delete this sentence in its entirety. The notification documentation requirement is fully addressed in the revised Sub-instance B instruction above. Initialing a separate physical (or electronic) file is redundant when the copy of the notification email or written record is itself uploaded to Silq eQMS.
- **Notes:** Sub-instance C is an artifact of the paper-based "initial the hard copy to confirm action taken" workflow. That workflow is unnecessary in an electronic system where the uploaded notification record is the evidence of action.

---

**Change 14 of 14 (two sub-instances — body-text hard copy references)**
- **Location:** Section 8 (Procedure: Training) — interactive training procedure instructions
- **ISO 13485:2016 basis:** No provision of ISO 13485:2016 requires training materials to be provided in hard copy. "Hard copy (or an electronic copy)" language is legacy paper-era phrasing; simplifying to "a copy" accepts either format and reduces unnecessary specification.

*Sub-instance A — Interactive training document provision:*
- **Current text (verbatim):** `"Provide a hard copy (or an electronic copy) of the associated document to the trainee(s)."`
- **Replace with:** `"Provide a copy of the associated document to the trainee(s)."`
- **Notes:** Removes format specification entirely. Either printed or electronic format is acceptable; the QMS does not mandate one over the other.

*Sub-instance B — Presentation material attachment:*
- **Current text (verbatim):** `"If the training is a presentation (e.g., PowerPoint) a hardcopy (or an electronic copy) of the presentation material is to be attached to the associated training record(s)."`
- **Replace with:** `"If the training is a presentation (e.g., PowerPoint), a copy of the presentation material shall be attached or linked to the associated training record(s)."`
- **Notes:** Removes the "hardcopy or electronic copy" dual specification. An electronic copy linked or attached to the training record in Silq eQMS is the preferred and sufficient approach.

---

### 2. Audit Compliance Edits

**Finding:** OFI #7 — Training effectiveness evaluation language inconsistency  
**Regulatory basis:** ISO 13485:2016 §6.2; 21 CFR Part 820 §820.25

The IA-2025 audit identified that while Section 8.11 of QM.SLQ003 uses mandatory language ("will be conducted"), the instructions for completing the Employee Training Program Form (Section 9) allow a supervisor to check "No" for Effectiveness Evaluation Required without any requirement to document justification. This discretion is inconsistent with the risk-based mandate in Section 8.11 for complex or high-risk tasks.

**Change A — Section 9 (Effectiveness Evaluation instruction):**

- **Location:** Section 9, Effectiveness Evaluation field instruction (subsection within the numbered form completion instructions)
- **Current text (verbatim):** `"Effectiveness Evaluation:  Indicate if an effectiveness evaluation is required for the initial training."`  
  (followed by) `"In determining what training effectiveness evaluation is appropriate, the complexity of the document along with the trainee's prior experience is to be considered."`
- **Required change:** Strengthen this instruction to make effectiveness evaluation mandatory for higher-risk or complex training, and require documented justification when it is not required. Replace with:

> `"Effectiveness Evaluation: Indicate if an effectiveness evaluation is required for the initial training. For training involving complex tasks, safety-critical procedures, or personnel new to the subject matter, an effectiveness evaluation shall be required. If 'No' is selected, the basis for this determination (e.g., low-risk task, experienced personnel, read-and-acknowledge of minor administrative update) shall be documented in the training program or on an accompanying note retained with the training record."`

- **Notes:** This change brings the Section 9 completion instruction into alignment with the mandatory risk-based language of Section 8.11, closing the discretionary gap identified in OFI #7. No change to Section 8.11 itself is required — that section already uses mandatory language and should be retained as-is.

---

### 3. Regulatory Reference Updates (OFI #8)

**Change A — Section 3 (Documents / Reference Documents):**
- **Location:** Reference Documents table, 21 CFR 820 row
- **Current text:** `"21 CFR 820	Quality System Regulation (820.25 – Personnel)"`
- **Replace with:** `"21 CFR Part 820	Quality Management System Regulation (QMSR) (820.25 – Personnel)"`

**Change B — Section 5 (Abbreviations/Acronyms):**
- **Location:** Abbreviations/Acronyms table, QSR entry
- **Current text:** `"QSR:  FDA Quality System Regulation"`
- **Replace with:** `"QMSR:  Quality Management System Regulation (21 CFR Part 820, as revised)"`

**Change C — Body text: all instances of "QSR" abbreviation**
Search the document for each occurrence of "QSR" in the body text and replace as follows:

| Location | Current text | Replace with |
|---|---|---|
| Section 2 (Purpose), second paragraph | `"21 CFR 820 and ISO 13485 requirements"` | `"21 CFR Part 820 Quality Management System Regulation (QMSR) and ISO 13485 requirements"` |
| Section 6.4 Base Training Requirements | `"General Quality System Regulation (QSR) / Quality Management System (QMS) training"` | `"General Quality Management System Regulation (QMSR) / Quality Management System (QMS) training"` |
| Section 8.2 General QSR/QMS training sub-bullet | `"General QSR / QMS and SILQ Quality Policy training is to include:"` | `"General QMSR / QMS and SILQ Quality Policy training is to include:"` |
| Section 8.2.1 first sub-bullet | `"The underlying reasons for and incorporation of the QSR/Quality System."` | `"The underlying reasons for and incorporation of the QMSR/Quality Management System."` |
| Section 8 Retraining | `"Retraining for general QSR/QMS will occur annually."` | `"Retraining for general QMSR/QMS will occur annually."` |

- **Notes:** Use Word's Find & Replace to catch any additional "QSR" instances in the document. Verify each replacement does not change a proper reference to a specific regulatory citation.

---

### 4. Definition Section Updates

| Action | Details |
|---|---|
| **Remove** the "FileHold" definition entry | Replaced by Change 1 above with "Silq eQMS" definition |
| **Add "Silq eQMS" definition** | Added in Change 1 above: *"Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."* |
| **Update "QSR" abbreviation to "QMSR"** | Covered by Regulatory Reference Update Change B above |

---

### 5. Associated Forms

**FM1-QM.SLQ003 A (Employee Training Program Form):** No FileHold references found. No revision required for EDMS transition. However, consistent with OFI #7 (Section 2.2 above), the originator should consider whether the Effectiveness Evaluation "Yes / No" checkbox on the form should be supplemented with a "Justification if No" line. This is an optional enhancement — if implemented, update to Rev B. If the OFI #7 fix is limited to the SOP instruction text only, no form revision is required.

**FM2-QM.SLQ003 B (Employee Training Record Form):** No FileHold references found. No revision required.

---

## SECTION 3 — QM.SLQ017 Internal Audits SOP (Rev A → Rev B)

### Summary of Changes Required

This document requires six FileHold reference replacements (covering filing of audit forms, schedules, and records), one regulatory reference update per OFI #8, and a definition section update. No audit compliance mNCs or OFIs are directly assigned to this procedure. Only FM2-QM.SLQ017 (Audit Checklist) requires a minor form header update for OFI #8; all other associated forms are clean.

---

### 1. FileHold Reference Replacements

**Change 1 of 6**
- **Location:** Section 5 (Definitions) — General Definitions
- **Current text (verbatim):** `"FileHold: Software based document management system used to electronically store controlled documents."`
- **Replace with:** `"Silq eQMS:  Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."`

---

**Change 2 of 6**
- **Location:** Section 7 (Procedure: Auditor Requirements) — FM5 filing instructions
- **Current text (verbatim):** `"Auditor Qualification Record, FM5-QM.SLQ017, shall be completed, scanned, imported into FileHold, and filed as follows:"`  
  *(sub-bullets that follow):*  
  `"For internal auditors: File in employee's training folder."`  
  `"For external auditors: File within the auditor's Supplier Quality folder in the Supplier QA drawer."`  
  `"Name the record with the name of the auditor. For example: "Auditor Qualification Record – First Name Last Name"."`
- **Replace with:** `"Auditor Qualification Record, FM5-QM.SLQ017, shall be completed, uploaded to Silq eQMS, and filed as follows:"`  
  `"For internal auditors: File in Silq eQMS Admin Docs, Training Records."`  
  `"For external auditors: File in Silq eQMS Admin Docs, Supplier Quality Records."`  
  `"Name the record with the name of the auditor. For example: "Auditor Qualification Record – First Name Last Name"."`
- **Notes:** The "Supplier QA drawer" language (FileHold drawer concept) is replaced with the correct Silq eQMS Admin Docs library and subfolder.

---

**Change 3 of 6**
- **Location:** Section 10 (Procedure: Post Audit) — Certificate of Internal Audit filing
- **Current text (verbatim):** `"A Certificate of Internal Audit, Form FM4-QM.SLQ017, shall be completed, scanned, imported into FileHold, and filed with the associated internal audit documents."`
- **Replace with:** `"A Certificate of Internal Audit, Form FM4-QM.SLQ017, shall be completed, uploaded to Silq eQMS Admin Docs, Internal Audit Records, and filed with the associated internal audit documents."`

---

**Change 4 of 6**
- **Location:** Section 12 (Procedure: Internal Quality Audit Schedule) — two edits required in the same paragraph

*Sub-instance A — Parent sentence:*
- **Current text (verbatim):** `"The schedule shall be reviewed and approved by SILQ Quality Assurance (QA) Management and hardcopy file maintained."`
- **Replace with:** `"The schedule shall be reviewed and approved by SILQ Quality Assurance (QA) Management and uploaded to Silq eQMS Admin Docs, Internal Audit Records."`
- **Notes:** Removes the legacy "hardcopy file maintained" requirement. ISO 13485:2016 §8.2.4 and §4.2.5 require audit records to be maintained but do not require physical hard copies. An approved electronic schedule in Silq eQMS fully satisfies this requirement.

*Sub-instance B — Sub-bullet:*
- **Current text (verbatim):** `"Hardcopy schedule shall be scanned and imported into appropriate Internal Audit folder within FileHold."`
- **Replace with:** Delete this sub-bullet entirely. The upload instruction is now captured in the revised parent sentence above. Retaining a separate sub-bullet would be redundant.

---

**Change 5 of 6**
- **Location:** Section 12 (Procedure: Internal Quality Audit Schedule) — schedule update filing
- **Current text (verbatim):** `"Quality Assurance shall scan and import into appropriate Internal Audit folder within FileHold."`
- **Replace with:** `"Quality Assurance shall upload the updated schedule to Silq eQMS Admin Docs, Internal Audit Records."`
- **Notes:** This sentence appears in the sub-bullet under "Quality Assurance shall update the annual audit schedule form as audits are completed by entering the applicable audit completion date." Update the sub-bullet accordingly.

---

**Change 6 of 6**
- **Location:** Section 14 (Procedure: Internal Quality Audit Records) — records retention instruction
- **Current text (verbatim):** `"Scan all completed internal audit records and import into FileHold; file within appropriate Internal Audit folder."`
- **Replace with:** `"Upload all completed internal audit records to Silq eQMS Admin Docs, Internal Audit Records."`

---

### 2. Audit Compliance Edits

No mNCs or OFIs from IA-2025 are directly assigned to QM.SLQ017. This revision is EDMS transition and OFI #8 regulatory reference updates only.

---

### 3. Regulatory Reference Updates (OFI #8)

**Change A — Section 3 (Documents / Reference Documents):**
- **Location:** Reference Documents table, 21 CFR 820 row
- **Current text:** `"21 CFR 820	Quality System Regulation (820.22 – Quality Audits)"`
- **Replace with:** `"21 CFR Part 820	Quality Management System Regulation (QMSR) (820.22 – Quality Audits)"`

- **Notes:** The ISO 13485:2016 §8.2.4 reference is current and accurate — retain as-is.

---

### 4. Definition Section Updates

| Action | Details |
|---|---|
| **Remove** "FileHold" definition entry | Replaced by Change 1 above with "Silq eQMS" definition |
| **Add "Silq eQMS" definition** | Added in Change 1 above |
| **No "QSR" abbreviation** present in QM.SLQ017 | No abbreviation change needed |

---

### 5. Associated Forms

**FM1-QM.SLQ017 B (Internal Quality Audit Schedule):** No FileHold references. No revision required.

**FM2-QM.SLQ017 A (Internal Quality Audit Checklist):** No FileHold references. However, the form header row reads: `"Quality Management System (ISO 13485:2016 Section 4; 21 CFR 820 Subpart A, B, D, M; …)"` — this "21 CFR 820" reference should be updated to "21 CFR Part 820 QMSR" per OFI #8. **This requires a form revision to Rev B.** Specific change:
- **Location:** Checklist header table cell (appears in each major section header of the form)
- **Current text:** `"21 CFR 820 Subpart A, B, D, M"` (and similar citations throughout checklist sections)
- **Replace with:** `"21 CFR Part 820 QMSR"` (for each occurrence; retain applicable subpart references where present)
- The originator should perform a global Find & Replace on "21 CFR 820" → "21 CFR Part 820 QMSR" within the checklist form, reviewing each instance to ensure the citation is contextually correct.

**FM3-QM.SLQ017 A (Internal Quality Audit Final Report):** No FileHold references. No revision required.

**FM4-QM.SLQ017 A (Certificate of Internal Audit):** No FileHold references. No revision required.

**FM5-QM.SLQ017 A (Auditor Qualification Record):** No FileHold references. No revision required.

---

## SECTION 4 — QM.SLQ020 Purchasing Controls SOP (Rev D → Rev E)

### Summary of Changes Required

This document requires five FileHold reference replacements (covering P.O. filing and record imports), one critical mandatory language change per mNC #5 (supplier change notification), one new subsection addition addressing response to supplier change notifications, and regulatory reference updates per OFI #8. The associated FM1-QM.SLQ020 Purchase Order Form already contains mandatory supplier change notification language in its NOTES field — no form revision is required, but the originator should verify this language is highlighted prominently.

---

### 1. FileHold Reference Replacements

**Change 1 of 5**
- **Location:** Section 4 (Definitions) — General Definitions
- **Current text (verbatim):** `"FileHold:  Software based document management system used to electronically store controlled documents."`
- **Replace with:** `"Silq eQMS:  Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."`

---

**Change 2 of 5**
- **Location:** Section 6 (Procedure: Purchasing) — P.O. filing sub-bullet
- **Current text (verbatim):** `"Completed purchase orders are to be scanned and imported into the appropriate Purchasing folder within FileHold."`
- **Replace with:** `"Completed purchase orders are to be uploaded to Silq eQMS Admin Docs, Purchasing Records."`

---

**Change 3 of 5**
- **Location:** Section 7 (Procedure: Closing Purchase Orders) — first closing sub-bullet
- **Current text (verbatim):** `"Closed purchase order is checked in to FileHold."`
- **Replace with:** `"Closed purchase order is uploaded to Silq eQMS Admin Docs, Purchasing Records."`

---

**Change 4 of 5**
- **Location:** Section 7 (Procedure: Closing Purchase Orders) — P.O. log sub-bullet
- **Current text (verbatim):** `"Purchase order log is checked out of FileHold, updated with closure information and checked back in to FileHold."`
- **Replace with:** `"The purchase order log is updated in Silq eQMS with closure information and re-uploaded to Silq eQMS Admin Docs, Purchasing Records."`

---

**Change 5 of 5**
- **Location:** Section 11 (Procedure: Purchasing Records) — records import instruction
- **Current text (verbatim):** `"Import all completed purchasing records into FileHold; file within appropriate Purchasing folder."`
- **Replace with:** `"Upload all completed purchasing records to Silq eQMS Admin Docs, Purchasing Records."`

---

### 2. Audit Compliance Edits

**Finding:** mNC #5 — Permissive supplier change notification language (MANDATORY)  
**Regulatory basis:** ISO 13485:2016 §7.4.1; 21 CFR Part 820 §820.50  
**Background:** The IA-2025 audit found that Section 6.3 contains the phrase "wherever possible," which makes supplier change notification a best-effort rather than a mandatory requirement. This contributed to CAPA 2025-003. The phrase must be eliminated and replaced with mandatory language.

**Change A — Section 6.3 (mNC #5 — CRITICAL):**

- **Location:** Section 6 (Procedure: Purchasing), Subsection 6.3 — the paragraph on supplier change notification
- **Current text (verbatim):** `"Contracts, Supplier Agreements, and Purchase Orders shall include, wherever possible, that SILQ be notified of any changes made to the product and/or service prior to those changes becoming effective so that SILQ can determine the impact of changes to the quality of the final product or quality system."`
- **Replace with:**

> `"Contracts, Supplier Agreements, and Purchase Orders shall require, as a standard condition, that SILQ be notified of any changes made to the product and/or service prior to those changes becoming effective. This requirement is mandatory and shall not be omitted from any purchasing agreement. Supplier change notifications enable SILQ to determine the impact of changes on the quality of the final product or quality system prior to implementing or accepting such changes."`

**Change B — Section 6.3 (new subsection — addition):**

After the revised Change A paragraph above, add the following new subsection (6.3.1 or as a sub-bullet under 6.3):

> `"Upon receipt of a supplier change notification, the following actions shall be performed:"`  
> `"(a) The notification shall be reviewed by Quality Assurance and Engineering/R&D to determine whether the change constitutes a design change requiring formal evaluation under QM.SLQ004 Design Control Program SOP;"`  
> `"(b) If the change impacts any component, material, process, or service covered by the product's Design History File or Device Master Record, a formal design change assessment shall be initiated per QM.SLQ004;"`  
> `"(c) The assessment and any resulting actions shall be documented and retained in the applicable Supplier Quality file and, if applicable, in the Design History File;"`  
> `"(d) No product incorporating the supplier's change shall be manufactured, distributed, or accepted into inventory until the design change assessment is complete and any required approvals have been obtained."`

- **Notes:** This new subsection directly implements the CAPA003 corrective actions regarding supplier-initiated modifications and ensures alignment between QM.SLQ020 and the design change requirements of QM.SLQ004 Rev C. The language in (a)–(d) above should be placed as numbered items or sub-bullets as appropriate to the formatting style of the existing SOP.

---

### 3. Regulatory Reference Updates (OFI #8)

**Change A — Section 3 (Documents / Reference Documents):**
- **Location:** Reference Documents table, 21 CFR 820 row
- **Current text:** `"21 CFR 820 		Quality System Regulation (820.50 – Purchasing Controls)"`
- **Replace with:** `"21 CFR Part 820	Quality Management System Regulation (QMSR) (820.50 – Purchasing Controls)"`

**Change B — Body text check:**  
Search the document for any additional occurrences of "QSR" or "Quality System Regulation" (not in the reference documents section). QM.SLQ020 does not appear to contain "QSR" in the definitions abbreviations section, but confirm via Find and update any occurrences found.

---

### 4. Definition Section Updates

| Action | Details |
|---|---|
| **Remove** "FileHold" definition entry | Replaced by Change 1 above with "Silq eQMS" definition |
| **Add "Silq eQMS" definition** | Added in Change 1 above |
| **No "QSR" abbreviation** present in QM.SLQ020 Definitions | Confirm via Find; update if any present |

---

### 5. Associated Forms

**FM1-QM.SLQ020 B (Purchase Order Form):** No FileHold references found. The form's NOTES field already contains the following text: *"By accepting this PO, supplier agrees to notify Silq Technologies Corporation within at least 14 days in advance of any changes to the ordered items. No changes will be accepted without such advance notice and written approval by Silq Technologies Corporation."* This existing language in the NOTES template is consistent with the mandatory supplier change notification requirement being established in Section 6.3 by mNC #5. **No form revision is required for mNC #5 compliance**, as the PO form already captures this obligation. The originator should confirm this NOTE language is not inadvertently removed during editing. No revision required.

---

## SECTION 5 — QM.SLQ036 Sales Order SOP (Rev E → Rev F)

### Summary of Changes Required

This document requires four FileHold reference replacements, a definition section update, and a regulatory reference assessment per OFI #8. No audit mNCs or OFIs are directly assigned to this procedure (EDMS transition and OFI #8 only). An advisory note on the ShipStation UI section currency review is included. The associated FM1-QM.SLQ036 Sales Order Form requires no changes.

---

### 1. FileHold Reference Replacements

**Change 1 of 4**
- **Location:** Section 4 (Definitions) — General Definitions
- **Current text (verbatim):** `"FileHold: Software-based document management system used to electronically store controlled documents."`
- **Replace with:** `"Silq eQMS:  Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."`

---

**Change 2 of 4**
- **Location:** Section 6.2 (Sales Order Log)
- **Current text (verbatim):** `"Sales/Customer Service is to maintain a sales order log (filed in FileHold) which is to include but is not limited to: sales order number, date, customer name and contact information, target delivery date, overall cost information, and actual delivery date."`
- **Replace with:** `"Sales/Customer Service is to maintain a sales order log (maintained in Silq eQMS Admin Docs, Sales Order Records) which is to include but is not limited to: sales order number, date, customer name and contact information, target delivery date, overall cost information, and actual delivery date."`

---

**Change 3 of 4**
- **Location:** Section 6.3 (Sales Order/Contract Review and Approval) — final sub-bullet
- **Current text (verbatim):** `"The approved sales order is maintained in FileHold in accordance with Section 7."`
- **Replace with:** `"The approved sales order is maintained in Silq eQMS Admin Docs, Sales Order Records, in accordance with Section 7."`

---

**Change 4 of 4**
- **Location:** Section 8 (Procedure: Sales Order Records Retention) — two sentences
- **Current text (verbatim):** `"All sales orders and applicable documentation are filed and maintained in the Sales Order drawer of FileHold as a quality record in accordance with record retention policies defined in QM.SLQ001, Document Control SOP."`  
  *(followed by):*  
  `"Records are to be scanned and imported into FileHold and filed within appropriate Sales Order folder."`
- **Replace with:**  
  `"All sales orders and applicable documentation are filed and maintained in Silq eQMS Admin Docs, Sales Order Records, as quality records in accordance with record retention policies defined in QM.SLQ001, Document Control SOP."`  
  `"Records are to be uploaded to Silq eQMS Admin Docs, Sales Order Records."`

---

### 2. Regulatory Reference Updates (OFI #8)

**Assessment of existing references:**

- **ISO 13485:2016 §7.2** (Customer-related processes) — currently cited in Section 3 Reference Documents as: `"ISO 13485:2016  International Standards Organization – Medical Devices – Quality Management Systems (section 7.2 – Customer-related processes)"`. This reference is accurate, current, and should be retained as-is.
- **21 CFR Part 820 (QMSR)** — QM.SLQ036 currently does **not** include a 21 CFR Part 820 reference in its Reference Documents section. **Recommendation:** No 21 CFR Part 820 reference needs to be added to QM.SLQ036. The Sales Order SOP governs commercial order processing and customer contract review; the primary applicable regulatory standard for this process is ISO 13485:2016 §7.2. The QMSR does not have a specific section governing sales orders as a distinct process. Record retention requirements under QMSR are addressed through the parent reference to QM.SLQ001. Therefore, no QMSR citation addition is required for this document.
- **No "QSR" abbreviation** present in QM.SLQ036 — confirm via Find; no change expected.

---

### 3. Definition Section Updates

| Action | Details |
|---|---|
| **Remove** "FileHold" definition entry | Replaced by Change 1 above |
| **Add "Silq eQMS" definition** | Added in Change 1 above |
| **"Ship Station" definition** | Retain as-is — this is a current business tool reference, not a FileHold or QMSR issue |

---

### 4. Associated Forms

**FM1-QM.SLQ036 A (Sales Order Form):** No FileHold references found. No revision required.

---

### 5. Advisory Note — ShipStation Section Currency Review

**Location:** Section 6.5 (CMO Fulfillment/Shipping of approved sales order), including login URL `https://ship13.shipstation.com/`, Figures 1–5 references, and detailed field-by-field UI navigation instructions.

**Issue:** Section 6.5 contains detailed, UI-specific ShipStation instructions that are tied to a specific version of the ShipStation interface (login URL, navigation menus, field names, figure references). These are not FileHold-related and do not require EDMS transition changes. However, they create a maintenance burden: if ShipStation changes its UI, the controlled SOP becomes inaccurate without a revision being triggered.

**Recommendation to originator:** Before releasing QM.SLQ036 Rev F, the originator should:

1. Log into ShipStation at `https://ship13.shipstation.com/` and verify the current UI matches the step-by-step instructions in Section 6.5 (menu names, field names, button labels, and screen layouts described in Figures 1–5).
2. If the UI has changed materially, update Section 6.5 accordingly (this does not change the Rev F revision rationale — it is a scope expansion of the current revision cycle).
3. Consider whether Section 6.5 should reference a separate controlled Work Instruction (WI) for ShipStation operations rather than embedding the full UI procedure in the SOP. Embedding detailed software UI steps in a controlled SOP requires a DCO every time the software interface changes. A referenced WI would be easier to maintain and appropriate given that ShipStation is a third-party commercial tool.

---

## SECTION 6 — QM.SLQ015 Supplier Quality Assurance SOP (Rev B → Rev C)

### Summary of Changes Required

This document requires five FileHold reference replacements (self-assessment filing, re-evaluation filing, and records retention), two audit compliance changes per mNC #4 and OFI #4, a regulatory reference update per OFI #8, and a definition section update. Associated forms FM1, FM2 (self-assessment surveys), and FM7 (assessment schedule) require revisions; all other QM.SLQ015 forms are clean.

---

### 1. FileHold Reference Replacements

**Change 1 of 5**
- **Location:** Section 4 (Definitions) — General Definitions
- **Current text (verbatim):** `"FileHold: Software based document management system used to electronically store controlled documents."`
- **Replace with:** `"Silq eQMS:  Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."`

---

**Change 2 of 5**
- **Location:** Section 10 (Procedure: Completing Supplier Self-Assessments) — filing sub-bullet under paragraph 10.2.5
- **Current text (verbatim):** `"Scan and import into FileHold and file in the appropriate Supplier Quality folder."`
- **Replace with:** `"Upload to Silq eQMS Admin Docs, Supplier Quality Records."`

---

**Change 3 of 5**
- **Location:** Section 12 (Procedure: Supplier Re-Evaluation) — filing sub-bullet
- **Current text (verbatim):** `"Document is scanned and imported into FileHold and filed in appropriate Supplier Quality file."`
- **Replace with:** `"Document is uploaded to Silq eQMS Admin Docs, Supplier Quality Records."`

---

**Change 4 of 5**
- **Location:** Section 17 (Procedure: Supplier Assessment Records) — records retention sub-bullet
- **Current text (verbatim):** `"Records and applicable documentation are to be scanned and imported into FileHold and filed within appropriate Supplier Quality Record file folder."`
- **Replace with:** `"Records and applicable documentation are to be uploaded to Silq eQMS Admin Docs, Supplier Quality Records."`

---

**Change 5 of 5 (external auditor filing — QM.SLQ017 cross-reference)**
- **Notes:** No additional standalone FileHold reference was identified in QM.SLQ015 beyond Changes 1–4 above. Confirm by running a global Find for "FileHold" in the document after completing the above changes.

---

### 2. Audit Compliance Edits

#### mNC #4 — Risk-Based Supplier Assessment and Re-evaluation Frequencies (MANDATORY)

**Regulatory basis:** ISO 13485:2016 §7.4.1; 21 CFR Part 820 §820.50(a)

**Background:** Current Sections 8 and 15 assign fixed assessment intervals (Category I = annual, Categories III–V = biennial) without a mechanism to adjust based on supplier performance, risk level, or post-SCAR situations. The IA-2025 auditors found the fixed intervals are not linked to risk-based determination, which is required by the applicable standards.

**Change A — Section 8 (Supplier Qualification Requirements) — Add risk-adjustment language to each applicable category sub-section:**

For **Section 8, Category I Re-evaluation sub-paragraph**, after the existing sentence `"Ongoing qualification requirements consist of annual performance evaluation per FM4-QM.SLQ015 and updated copy of active industry recognized quality certificate or accreditation, if applicable. On-site audits may be required if the supplier's performance fails to meet re-evaluation requirements."`, add:

> `"The annual re-evaluation is a minimum frequency. QA may increase the assessment frequency for a Category I supplier based on a documented risk assessment considering supplier performance history, nature of products or services supplied, results of prior assessments, and SCAR status. The basis for any deviation from the minimum frequency shall be documented on the Supplier Assessment Schedule (FM7-QM.SLQ015) in the Risk Basis column."`

For **Section 8, Category III Re-evaluation sub-paragraph**, after the existing sentence `"Ongoing qualification requirements consist of biennial (every two years) performance evaluation per FM4-QM.SLQ015 and successful completion of self-assessment FM1-QM.SLQ015 or FM2-QM.SLQ015. Note: an active industry recognized quality certificate or accreditation may be used in lieu of the self-assessment. On-site audits may be required if the supplier's performance fails to meet re-evaluation requirements."`, add:

> `"The biennial re-evaluation is a minimum frequency. QA may increase the assessment frequency for a Category III supplier based on a documented risk assessment considering supplier performance history, safety-criticality of the supplied product, results of prior assessments, and SCAR status. The basis for any deviation from the minimum frequency shall be documented on the Supplier Assessment Schedule (FM7-QM.SLQ015) in the Risk Basis column."`

For **Section 8, Category IV Re-evaluation sub-paragraph**, after the existing sentence on biennial re-evaluation, add:

> `"The biennial re-evaluation is a minimum frequency. QA may increase the assessment frequency for a Category IV supplier as warranted by risk assessment. The basis for any increased frequency shall be documented on the Supplier Assessment Schedule (FM7-QM.SLQ015) in the Risk Basis column."`

**Change B — Section 15 (Procedure: Supplier Assessment Schedule) — Add explicit risk-basis requirement:**

- **Location:** Section 15, after the existing paragraph: `"On an annual basis, SILQ Quality Assurance will develop a schedule of supplier on-site audits and self-assessments for execution. Form FM7-QM.SLQ015, Supplier Assessment Schedule will be completed and is to include all suppliers that require an assessment and/or re-evaluation. Category V suppliers are not included on the assessment schedule. This schedule will be reviewed and approved by QA and may be revised at any time throughout the year."`
- **Add new sub-paragraph:**

> `"The assessment and re-evaluation frequency for each supplier on the schedule shall be determined based on a risk assessment that considers: (a) the supplier's category per Section 7; (b) the supplier's past performance record, including nonconformances, SCARs, and delivery history; (c) the nature of the products or services supplied and their potential impact on final product safety and performance; and (d) the results of prior assessments, including any open corrective actions. The minimum frequencies defined in Section 8 apply as floors, not ceilings. For each supplier, the assigned frequency and the basis for that frequency shall be documented in the Risk Basis column of FM7-QM.SLQ015."`

---

#### OFI #4 — Documented Risk Justification for Self-Assessment-Based Qualification of Higher-Risk Suppliers (recommended)

**Regulatory basis:** ISO 13485:2016 §7.4.1; 21 CFR Part 820 §820.50(a)

**Background:** OFI #4 identified that for Category I and III suppliers where initial qualification relies on self-assessment and certification rather than on-site audit, the procedure does not require documented justification explaining why self-assessment is sufficient given the supplier's risk level.

**Change A — Section 8, Category I Initial qualification sub-paragraph:**

- **Location:** Section 8, Category I, Initial sub-paragraph: `"An initial, on-site supplier evaluation with acceptable results; or completion of a self-assessment FM1-QM.SLQ015 or FM2-QM.SLQ015 with passing results and attachment of an active industry recognized quality certificate or accreditation."`
- **Add after this sentence:**

> `"When initial qualification of a Category I supplier is based on self-assessment and certification rather than an on-site audit, Quality Assurance shall document a written justification in the Results section of FM1-QM.SLQ015 or FM2-QM.SLQ015 explaining why self-assessment is appropriate given the supplier's risk level, the nature of the product or service supplied, and any compensating controls in place. This justification is subject to QA and Manufacturing management review and approval as part of the assessment sign-off."`

**Change B — Section 8, Category III Initial qualification sub-paragraph:**

- **Location:** Section 8, Category III, Initial sub-paragraph: `"Completion of a self-assessment survey FM1-QM.SLQ015 or FM2-QM.SLQ015 with passing results."`
- **Add after this sentence:**

> `"When initial qualification of a Category III supplier is based on self-assessment rather than an on-site audit, Quality Assurance shall document a written justification in the Results section of FM1-QM.SLQ015 or FM2-QM.SLQ015 explaining why self-assessment is appropriate given the supplier's risk level and the nature of the product or service supplied. This justification is subject to QA and Manufacturing management review and approval as part of the assessment sign-off."`

---

### 3. Regulatory Reference Updates (OFI #8)

**Change A — Section 3 (Documents / Reference Documents):**
- **Location:** Reference Documents table, 21 CFR 820 row
- **Current text:** `"21 CFR 820 	Quality System Regulation (820.50(a) – Evaluation of Suppliers, Contractors and Consultants)"`
- **Replace with:** `"21 CFR Part 820	Quality Management System Regulation (QMSR) (820.50(a) – Purchasing Controls)"`
- **Notes:** The parenthetical description is updated from the old QSR section heading "Evaluation of Suppliers, Contractors and Consultants" to the current QMSR heading "Purchasing Controls."

---

### 4. Definition Section Updates

| Action | Details |
|---|---|
| **Remove** "FileHold" definition entry | Replaced by Change 1 above |
| **Add "Silq eQMS" definition** | Added in Change 1 above |
| **"QSR" abbreviation** — QM.SLQ015 Definitions does not include a QSR abbreviation | Confirm via Find; no change expected |

---

### 5. Associated Forms

**FM1-QM.SLQ015 A (Supplier Quality Self-Assessment Survey Form — Manufacturer):** No FileHold references. Revision required per OFI #4. In the `FOR SILQ USE ONLY` Results section (which currently contains: Survey Score, Supplier Classification, Supplier Status, Notes, Manufacturing Approval, QA Approval), add the following new field below the existing "Notes" field:

> Add field: **"Risk Justification for Self-Assessment (required for Category I and III suppliers):"** [open text field]

Update the form to Rev B.

**FM2-QM.SLQ015 A (Supplier Quality Self-Assessment Survey Form — Testing Services):** No FileHold references. Same OFI #4 update as FM1. Add identical Risk Justification field to the `FOR SILQ USE ONLY` Results section. Update to Rev B.

**FM3-QM.SLQ015 A (Category II Supplier Assessment Form):** No FileHold references. No revision required.

**FM4-QM.SLQ015 A (Supplier Re-Evaluation Form):** No FileHold references. No revision required.

**FM5-QM.SLQ015 A (Certificate of Audit Form):** No FileHold references. No revision required.

**FM6-QM.SLQ015 B (SILQ Approved Supplier List Form):** No FileHold references. No revision required.

**FM7-QM.SLQ015 A (Supplier Assessment Schedule / Status Form):** No FileHold references. Revision required per mNC #4. The current form has columns: Supplier Name | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Current Status.

Add the following two columns (insertable between "Supplier Name" and "Jan," or after "Current Status"):

- **"Category"** — to capture the supplier's risk category (I, II, III, IV, V)
- **"Assess. Frequency & Risk Basis"** — a column for the assigned assessment frequency (e.g., Annual, Biennial) and the documented basis for that frequency (e.g., Cat I min; increased due to SCAR 2025-001; post-audit enhanced monitoring)

Updated column order recommendation:

| Supplier Name | Category | Assess. Freq. | Risk Basis for Frequency | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Current Status |

Update to Rev B.

**FM8-QM.SLQ015 A (Supplier Corrective Action Request Form):** No FileHold references. No revision required.

---

## SECTION 7 — QM.SLQ004 Design Control Program SOP (Rev B → Rev C)

### Summary of Changes Required

This is the most complex revision in DCO092. QM.SLQ004 Rev C must incorporate three distinct sets of changes, all in a single revision:

1. **DC.SLQ002 EDMS Transition** — 2 FileHold reference replacements (Definitions and DHF section)
2. **CAPA003 Corrective Actions** — Additions to Section 16 (Design Changes) to require mandatory evaluation of all supplier-initiated modifications (originated from FDA 483 Observation 2, October 2025)
3. **IA-2025 mNC #1** — Nine substantive procedural additions addressing gaps in design control planning, change control, conflict resolution, output control, DHF capture criteria, V&V planning, production-equivalent validation units, and design transfer requirements

All three sets of changes are additive and do not conflict with each other. OFI #8 regulatory reference updates round out the revision.

---

### Change Source Delineation

Every change in this section is labeled with its source:
- **[EDMS]** = DC.SLQ002 EDMS Transition
- **[CAPA003]** = CAPA003 Corrective Action
- **[mNC#1]** = IA-2025 Minor Non-Compliance #1
- **[OFI#8]** = OFI #8 Regulatory Reference Update

---

### 1. FileHold Reference Replacements **[EDMS]**

**Change 1 of 2**
- **Location:** Section 5 (Definitions) — General Definitions
- **Current text (verbatim):** `"FileHold: Software based document management system used to electronically store controlled documents."`
- **Replace with:** `"Silq eQMS:  Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ."`

---

**Change 2 of 2**
- **Location:** Section 11 (Procedure: Design History File) — DHF storage sub-bullet (first sub-bullet under Section 11.1)
- **Current text (verbatim):** `"DHF documents are to be scanned and imported into FileHold and filed in the appropriate DHF."`
- **Replace with:** `"DHF documents are to be uploaded to Silq eQMS Admin Docs, Design History Files."`

---

### 2. CAPA003 Corrective Action Edits **[CAPA003]**

**Background:** CAPA003 (initiated October 2025, approved March 2026) addresses an unauthorized design change implemented by Ningbo Yingmed, a supplier to SILQ's contract manufacturer Pathway. The corrective action required Silq to revise QM.SLQ004 to require mandatory evaluation of all supplier-initiated modifications, regardless of perceived significance. The CAPA003 verification plan requires the revised procedure to:
- Define mandatory evaluation of all supplier-initiated modifications
- Require documented design impact assessment prior to implementation
- Require risk analysis review and regulatory assessment before release to production
- Establish escalation requirements when supplier changes are communicated

**Change A — Section 7 (Procedure: Project Scope Definition, 1A) — Add supplier-initiated change source:**

- **Location:** Section 7, bullet list of design project sources (currently lists: Internal R&D, Concept/design proposal by strategic partner, Feedback from clinical/market surveillance, Result of a corrective action, Modification of any existing component or process by an approved supplier or supplier to an approved supplier)
- **Current text (verbatim) of last bullet:** `"Modification of any existing component or process by an approved supplier or supplier to an approved supplier that may impact the finished device"`
- **No text change needed to this bullet** — it already identifies this as a project source. However, add a new explanatory sub-bullet directly beneath it:

> `"Any modification communicated by a supplier, contract manufacturer, or a supplier to a contract manufacturer that affects a component, material, or process used in SILQ's finished device shall be treated as a design project source requiring a formal scope evaluation per this section, regardless of the perceived significance of the modification."`

---

**Change B — Section 16 (Procedure: Design Changes) — Add mandatory all-changes evaluation requirement [CAPA003 + mNC #1 Gap 1 combined]:**

This change addresses both the CAPA003 corrective action and mNC #1 Gap 1 simultaneously (they share the same substantive requirement). See **mNC #1 Gap 1** in Section 7.3 below for the complete text — the two requirements are satisfied by a single addition to Section 16.

---

### 3. IA-2025 mNC #1 Compliance Edits (Nine Gaps) **[mNC#1]**

#### Gap 1 — Design Changes: Formal Evaluation of ALL Changes (including supplier-initiated) [mNC#1 + CAPA003]

- **Location:** Section 16 (Procedure: Design Changes) — add new subsection at the beginning of Section 16, before the existing paragraph on "major changes"
- **Current opening text of Section 16 (verbatim):** `"Design changes to product lines after design V&V has been completed or has been transferred to production are to be handled based on the extent of change(s)."`
- **Add as new opening sub-paragraph or Section 16.1:**

> `"All design changes, regardless of perceived magnitude or origin — including but not limited to changes initiated by SILQ personnel, contract manufacturers, and suppliers or sub-suppliers to contract manufacturers — must be formally evaluated before implementation. The evaluation shall document: (a) whether the change constitutes a design change requiring a formal Document Change Order (DCO); (b) what verification and/or validation activities, if any, are required to confirm that the change does not adversely affect device safety, performance, or regulatory compliance; and (c) the regulatory impact of the change, including whether a new or amended regulatory submission is required. This evaluation shall be documented, reviewed by Quality Assurance and R&D/Engineering, and retained in the applicable Design History File or quality records. No product incorporating an unevaluated design change shall be manufactured, distributed, or accepted into commercial inventory."`

- **Source label:** This addition satisfies both **[CAPA003]** and **[mNC#1 Gap 1]**.

---

#### Gap 2 — Design Project Planning: Minimum Planning Requirements [mNC#1]

- **Location:** Section 8 (Procedure: Design Project Planning, 1B) — add a new sub-paragraph defining minimum plan content, after the existing paragraph: `"As part of the project planning, key resources and their subsequent responsibilities are to be defined in the project plan, with key interfaces between resources identified for the specific design control activities and deliverables."`
- **Add:**

> `"At a minimum, the design project plan shall include: (a) identification of all required design review stages (technical and phase reviews) and the deliverables to be reviewed at each stage; (b) the required verification and validation activities and the criteria that must be met for each; (c) design transfer responsibilities, including identification of the personnel or department responsible for confirming DHF completeness and initiating the design transfer checklist; and (d) the DHF deliverables required for each project phase, with ownership assignments. Projects of limited scope may tailor these elements with documented rationale, but may not omit them entirely."`

---

#### Gap 3 — Project Plan Change Control [mNC#1]

- **Location:** Section 8 (Procedure: Design Project Planning, 1B) — add a new sub-paragraph on plan change control, after the existing paragraph: `"The progression and status of the project plan is to be updated, reviewed, and approved as the project is executed and evolves."`
- **Add:**

> `"Significant changes to an approved design project plan — including changes to the defined scope of required design reviews, V&V activities, design transfer responsibilities, or DHF deliverables — shall be documented, reviewed, and approved through a Document Change Order (DCO) or equivalent change control mechanism before implementation. The rationale for the plan change shall be recorded and retained in the Design History File. Minor administrative updates (e.g., revised timeline dates with no scope impact) may be made with documented QA approval without requiring a full DCO, provided the basis for the update is noted in the project record."`

---

#### Gap 4 — Conflict Resolution Authority [mNC#1]

- **Location:** Section 10 (Procedure: User Needs, 2 and Design Inputs, 3) — add a new sub-paragraph on conflict resolution, after the existing paragraph: `"Design Input documents may be revised as necessary to address resolution of incomplete, ambiguous, or conflicting requirements. In the event that incomplete, ambiguous, or conflicting requirements are discovered, SILQ management or their representatives will have final authority to make necessary changes to resolve such conflicts. All revisions to design input documents are to be controlled through the DCO process."`
- **Add:**

> `"Design requirement conflicts shall be resolved through a documented functional review process. When a conflict in design requirements or design input interpretation cannot be resolved at the working level, the matter shall be escalated to a formal design review or QA management review. Final resolution authority for unresolved conflicts in design requirements rests with QA management in conjunction with R&D/Engineering management. All conflict resolutions shall be documented with the rationale for the decision retained in the Design History File, and any resulting changes to design input documents shall be processed through the DCO process."`

---

#### Gap 5 — Design Outputs: Formal Control Requirement [mNC#1]

- **Location:** Section 11 (Procedure: Design Outputs, 4) — add a new sub-paragraph on formal output control, after the existing paragraph on design output deliverables (the list of engineering drawings, specifications, etc.)
- **Add:**

> `"All design output documents, regardless of the phase in which they are generated, shall be released as formally controlled documents through the DCO process before use in verification or validation activities, manufacturing, packaging, labeling, or servicing activities. Preliminary or draft design output documents used for internal development purposes shall be clearly marked as uncontrolled drafts and may not be used as the basis for production, inspection, or regulatory submission until formally released. Design output release is a prerequisite for design transfer."`

---

#### Gap 6 — DHF Work Product Capture Criteria [mNC#1]

- **Location:** Section 13 (Procedure: Design History File) — add a new sub-paragraph defining DHF capture criteria, before or after the existing text on DHF storage
- **Add as a new sub-paragraph:**

> `"Not all work product generated during a design project is required to be captured in the DHF; however, the following categories of documents must be treated as DHF-controlled records from the point of creation: (a) any document that informs a design decision (including trade studies, engineering evaluations, and meeting minutes from technical discussions); (b) any document that supports or constitutes evidence for a verification or validation activity; (c) all design inputs, design outputs, design review records, and design change records; and (d) all risk management documents and risk mitigation evidence. Preliminary, exploratory, or brainstorming work product that does not fall into any of the above categories may remain as informal working documents. Once any such document becomes the basis for a design decision or design deliverable, it must be formalized and controlled through the DHF. QA management is responsible for confirming DHF completeness at each phase review."`

---

#### Gap 7 — V&V Planning: Mandatory, Not Optional [mNC#1]

- **Location:** Section 12 (Procedure: Design Verification, 5 and Validation, 6) — add a new mandatory V&V planning sub-paragraph, before the existing paragraph on V&V activities
- **Add as a new opening sub-paragraph to Section 12:**

> `"A verification and validation plan shall be established for all design projects prior to initiation of V&V activities. The V&V plan shall formally identify all required verification activities (confirming design outputs meet design inputs) and all required validation activities (confirming the design meets user needs and intended use), including the criteria for determining when each activity is complete. V&V activities shall not be omitted from the plan without documented justification approved by QA management; discretionary omission of required V&V based solely on project scope is not permitted. The V&V plan shall be a controlled DHF document released through the DCO process."`

---

#### Gap 8 — Production-Equivalent Unit Criteria for Validation [mNC#1]

- **Location:** Section 12 (Procedure: Design Verification, 5 and Validation, 6) — add a new sub-paragraph on production-equivalent unit criteria, after the existing sentence: `"Design validation activities are to be performed on initial production units or representative test units."`
- **Add:**

> `"When design validation activities are performed on representative test units rather than initial production units, the basis for claiming equivalence between the test units and production units shall be documented and approved. At a minimum, the equivalence documentation shall address: (a) the manufacturing processes used to produce the test units compared to the intended production process; (b) the materials and components used in the test units compared to the released production specification; and (c) any known differences between test units and production units and an assessment of whether those differences could affect the validation conclusions. This equivalence determination shall be reviewed by QA and R&D/Engineering and retained in the Design History File as part of the validation package."`

---

#### Gap 9 — Design Transfer: Mandatory Prior Design Review Requirement [mNC#1]

- **Location:** Section 14 (Procedure: Design/Clinical Transfer, 7) — add a new sub-paragraph clarifying the relationship between design transfer and design review, at the end of the existing Design Transfer section
- **Add as a new closing sub-paragraph of Section 14:**

> `"Design transfer may not be initiated or approved until at least one formal design review (as required by Section 16 / Section 8 of this procedure) has been conducted, documented, and retained in the Design History File. A design transfer checklist may be used to supplement the transfer process but may not substitute for a required design review. The transfer checklist shall include a confirmation field verifying that the required design review(s) have been completed and that the associated review records are present in the DHF. Where the project plan did not require a separate formal design review meeting (e.g., for limited-scope design changes), the design review requirement may be satisfied by a documented phase review that covers the design review criteria defined in Section 16 / Section 8, with this equivalence documented and approved by QA management."`

---

### 4. Regulatory Reference Updates (OFI #8) **[OFI#8]**

QM.SLQ004 does not list a 21 CFR Part 820 reference explicitly in the Reference Documents section (it references QM.SLQ001 and the procedural sub-SOPs). However:

- The Purpose section states compliance with `"21 CFR 820.30 and ISO 13485:2016"` — update this citation.

**Change A — Section 2 (Purpose):**
- **Location:** First paragraph of Purpose
- **Current text (verbatim):** `"to ensure design and development activities are in compliance with 21 CFR 820.30 and ISO 13485:2016."`
- **Replace with:** `"to ensure design and development activities are in compliance with 21 CFR Part 820.30 (Quality Management System Regulation) and ISO 13485:2016."`

**Change B — Definitions, Abbreviations:**
- QM.SLQ004 does not contain a "QSR" abbreviation in the Definitions section. Confirm via Find; no change expected.

---

### 5. Definition Section Updates

| Action | Details |
|---|---|
| **Remove** "FileHold" definition entry | Replaced by Change 1 of Section 7.1 above |
| **Add "Silq eQMS" definition** | Added in Change 1 of Section 7.1 above |
| **No "QSR" abbreviation** present | Confirm via Find |

---

### 6. Associated Forms

**FM1-QM.SLQ004 A (Design Project Scope Form):** No FileHold references. Revision required per mNC #1. The current form captures: Project Purpose, Endpoint, Regulatory Markets, Reason for Initiation, External Partner Constraints, Regulatory Constraints, Risk/Hazard Considerations, Additional Project Constraints, Conclusion, and Applicable Design Control Phases (with Yes/No checkboxes).

Add the following two new fields/rows to the form:

**Addition 1 — V&V Determination Field (per mNC #1 Gap 7):**

Add a new row after the Applicable Design Control Phases table:

> **"V&V Planning Requirement Determination:"** [check one]  
> ☐ V&V plan required — all applicable V&V activities to be formally planned and documented  
> ☐ V&V plan scope limited — Rationale: _______________________________________________  
> *(QA approval required if limited V&V scope selected)*  
> QA Approval for Limited V&V Scope: _________________________ Date: _________________

**Addition 2 — Project Plan Change Control Tracking (per mNC #1 Gap 3):**

Add a new row or footer section to the form:

> **"Project Plan Revision History"** (complete at time of any plan scope change):

| Plan Revision # | Date | Description of Scope Change | Change Control Reference (DCO# or equiv.) | QA Approval |
|---|---|---|---|---|
|  |  |  |  |  |

Update to Rev B.

---

## APPENDIX A — SILQ eQMS TRANSLATION REFERENCE TABLE

*Quick reference for originator during editing:*

| Old (FileHold) Language | New (Silq eQMS) Language |
|---|---|
| "FileHold" (in Definitions) | "Silq eQMS: Web-based electronic document management system used to store, organize, retrieve, and lifecycle-manage controlled QMS documents and records for SILQ." |
| "scan and import into FileHold" | "upload to Silq eQMS" |
| "import into [folder] within FileHold" | "upload to Silq eQMS Admin Docs, [library], [subfolder]" |
| "checked in/out of FileHold" | "uploaded to / retrieved from Silq eQMS" |
| "file within appropriate [X] folder within FileHold" | "file in Silq eQMS Admin Docs, [library], [subfolder]" |
| "Sign-off sheet window in FileHold" | Delete the clause entirely — Silq eQMS has no in-system sign-off. All records are signed outside the system and uploaded as signed documents. |
| "See QM.SLQ014 for instructions to retrieve" | "Accessed in Silq eQMS per QM.SLQ014" |
| "Maintained in FileHold" | "Maintained in Silq eQMS" |
| "FileHold drawer" | "Silq eQMS Admin Docs library" |
| "Supplier QA drawer" | "Silq eQMS Admin Docs, Supplier Quality Records" |
| "print a hard copy (or electronic copy)… initial/date, scan and import" | Delete print-initial-scan cycle entirely. Replace with electronic review and upload: "review/update in Silq eQMS" and "upload documentation to Silq eQMS Admin Docs, [subfolder]" |
| "hard copy training plans and training records… archived in storage" | "training plans and training records… uploaded to Silq eQMS Admin Docs, Training Records" |
| "hardcopy file maintained" | "uploaded to Silq eQMS Admin Docs, [subfolder]" |
| "Provide a hard copy (or an electronic copy) of the associated document" | "Provide a copy of the associated document" |
| "a hardcopy (or an electronic copy) of the presentation material is to be attached" | "a copy of the presentation material shall be attached or linked" |

**Silq eQMS Admin Docs library structure (approved storage locations):**

| Library | Use for |
|---|---|
| QM Documents | Controlled QMS documents |
| Design History Files | DHF documents |
| Supplier Quality Records | Supplier assessments, SCARs, self-assessments, re-evaluations |
| Purchasing Records | Purchase orders, P.O. logs |
| Sales Order Records | Sales orders, sales order logs |
| Internal Audit Records | Audit schedules, checklists, reports, certificates |
| Training Records | Employee training programs, training records, training matrix |
| CAPA Records | CAPA forms and records |
| Calibration & Maintenance Records | Calibration records |
| Regulatory Standards and Approvals | Regulatory submissions |
| Environmental Monitoring | Environmental records |

---

## APPENDIX B — AUDIT FINDINGS SUMMARY FOR DCO092

| Finding | Source | Applicable Document(s) | Required Action in DCO092 |
|---|---|---|---|
| mNC #1 | IA-2025 | QM.SLQ004 | Nine substantive additions — see Section 7.3 |
| mNC #4 | IA-2025 | QM.SLQ015 | Risk-based frequency language in Sections 8 and 15; FM7 column additions |
| mNC #5 | IA-2025 | QM.SLQ020 | Replace "wherever possible" with mandatory language in Section 6.3; add response subsection |
| OFI #4 | IA-2025 | QM.SLQ015 | Add risk justification requirement for Cat I/III self-assessment; update FM1, FM2 |
| OFI #7 | IA-2025 | QM.SLQ003 | Strengthen Section 9 effectiveness evaluation instruction |
| OFI #8 | IA-2025 | All Phase 1B documents | Update all "21 CFR 820 Quality System Regulation" → "21 CFR Part 820 Quality Management System Regulation (QMSR)"; update "QSR" abbreviation → "QMSR" |
| CAPA003 | FDA 483 Oct 2025 | QM.SLQ004 | Add mandatory supplier-initiated change evaluation to Section 16; add supplier source to Section 7 (combined with mNC #1 Gap 1) |

---

*This guide was prepared by the QMS Agent on May 28, 2026, and revised to remove all print/scan/hard-copy workflow requirements per editorial direction consistent with ISO 13485:2016 §4.2.5 (electronic records acceptable in any medium) and §6.2 (records "can be as simple or complex as necessary"). All verbatim current text quotations are drawn from the readable text versions of the controlled documents as they exist at the time of this preparation.*
