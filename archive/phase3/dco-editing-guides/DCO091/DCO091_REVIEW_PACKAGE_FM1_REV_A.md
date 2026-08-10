# DCO091 — Review package (use FM1-QM.SLQ001 Rev A until form revision is approved)

Use this file to build the **Document Change Order** you give reviewers **before** NC #15 layout exists on FM1. Complete the fields in controlled Word using **`FM1-QM.SLQ001 A` (Rev A)** — see mirror: `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ001 A Document Change Order Form.md`.

**What reviewers receive**

1. This DCO completed on **Rev A** (or a PDF export of it).
2. **Draft** controlled files for each line item (native Word/PDF as your process requires), for example:
   - `QM.SLQ001 B Document Control SOP` (draft)
   - `QM.SLQ014 C Electronic Doc System WI` (draft)
   - `FM1-QM.SLQ014 B Electronic Signature Acknowledgement Form` (draft)
   - When available: draft **`FM1-QM.SLQ001`** next revision (NC #15 column and attestation) — if not ready, state that in the table and attach it when circulated for re-review or final sign-off.

**Rev A limitation (be explicit to reviewers)**

Rev A still has **Req. Effective Date: R +** and no **Proposed effective date (calendar, GMP use)** column. Until FM1 is revised and approved, put **each document’s intended first GMP-use calendar date** (or “TBD — originator to confirm before execution”) in the **Description of / Reason for Change** text for that row, and use **R +** only in the sense your process allows for the **overall** DCO (for example **R + 0** if all lines are effective on release date). After FM1 next rev is approved, a follow-up redline or administrative correction can align the executed DCO layout to QM.SLQ001 if your QA model requires it; if not, keep narrative dates in the Rev A PDF for audit.

---

## Paste block — header (Rev A fields)

| Field | Suggested text |
| --- | --- |
| **DCO #** | `091` (assign from live DCO log if different) |
| **Change Priority** | Select per schedule (often **Medium** or **High** for QMS core). |
| **DCO Type** | **Permanent DCO** |
| **Document category** | Mark **Standard Operating Procedure (SOP)**, **Work Instruction (WI)**, and **Form** as applicable to the rows below. |
| **Req. Effective Date / R +** | Per Rev A only: e.g. **R + 0** if effective on release, or **R + N** if policy allows delay; mirror the **earliest** line you describe in the table, or note “see per-document dates in Description.” |
| **Originator** | Printed name, department, contact. |

---

## Paste block — document table (add one Rev A row per line item)

Copy each logical row into the Rev A **Document Title / Document / Part Number / Current Revision / Description** table. Expand rows in Word if you need more lines.

| Document Title (as on document) | Document / Part Number | Current Rev | Description of change | Reason for change |
| --- | --- | --- | --- | --- |
| Document Control SOP | QM.SLQ001 | A → **B** (draft attached) | Transition normative text from legacy EDMS to **Silq eQMS**; align DCO workflow, storage, retention, and external document handling with validated system and QM.SLQ014. **NC #15:** Replace default effective-date behavior with **per–document-line calendar** proposed effective dates and approver review; update definitions of **Release date** vs **Effective date**; update releasing narrative and Completing DCO instructions to match forthcoming FM1 (no automatic three-day rule; no R-plus as primary model in SOP after FM1 aligns). | IA NC #15 closure; Silq eQMS go-live documentation; reduce ambiguity between release and GMP-effective use. |
| Electronic Document System Work Instruction | QM.SLQ014 | B → **C** (draft attached) | Replace legacy EDMS procedures with **Silq eQMS** steps (access, DCO filing, Document Control publication, Admin Docs, training record filing, e-signatures). **NC #15:** Require **Silq Effective date at Release revision** to match **final calendar date** for that document line on executed DCO; remove R-plus–based metadata instructions. | Same as QM.SLQ001; WI must match SOP and production UI labels. |
| Electronic Signature Acknowledgement Form | FM1-QM.SLQ014 | A → **B** (draft attached) | Attestation and definitions updated for **Silq eQMS**, SW.SLQ008 / SW.SLQ011, and DCO approvals **outside** Silq per QM.SLQ001. | Same package; Part 11 alignment to current system. |
| Document Change Order Form | FM1-QM.SLQ001 | A → **B** (draft when available; else “TBD”) | **NC #15:** Remove **Req. Effective Date / R +** as primary control; add column **Proposed effective date (calendar, GMP use)** per document row; add **originator attestation** block; Silq blank-form sourcing in instructions. | Closes NC #15 on form; aligns with QM.SLQ001 B. |

**Per-document calendar effective date (Rev A workaround)**  
For each row, add a final sentence in **Description** or **Reason**, for example:  
`Proposed first GMP-use date for this line item: [DD-MMM-YYYY] or TBD pending training / RA input.`

---

## Supporting sections (Rev A checkboxes and tables)

| Block | Suggested handling |
| --- | --- |
| **Additional Risk Assessment** | **Yes** if QM/DCO changes affect product or QMS risk; summarize (document control effective dating, training readiness, wrong-version use). Reference risk file IDs if required. |
| **Verification or Validation** | **Yes** if Silq eQMS release tied to validated app (SW.SLQ008/011); cite relevant protocol or summary statement per your template. |
| **Training** | **Yes** for QM.SLQ001, QM.SLQ014, FM1-QM.SLQ014, and FM1-QM.SLQ001 when released; list notification type (Read and Acknowledge vs Interactive) per QM.SLQ003. |
| **Material disposition** | **No** unless this DCO also changes part numbers or specs that affect stock (adjust if applicable). |
| **Potential regulatory impact** | **Yes/No** per your RA rule set; if Yes, short regulatory assessment or “RA concurrence on DCO.” |

---

## Attachments checklist (for the review email or binder)

- [ ] Completed **FM1-QM.SLQ001 Rev A** DCO091 (Word or PDF).
- [ ] **QM.SLQ001** draft revision B (Word/PDF).
- [ ] **QM.SLQ014** draft revision C (Word/PDF).
- [ ] **FM1-QM.SLQ014** draft revision B (Word/PDF).
- [ ] **FM1-QM.SLQ001** draft next revision when ready (or second circulation).
- [ ] Links or pointers to editing guides reviewers may use optionally: `docs/DCO091/EDITOR_COMBINED_QM001B_QM014C_FM1_DCO091.md`, `docs/DCO091/MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md`.

---

## After approval (for your records only)

When FM1-QM.SLQ001 **next revision** is approved, you may re-issue the executed DCO on the **new** form layout so row layout matches QM.SLQ001, or retain the Rev A executed PDF and file the approved FM1 separately per your document administrator procedure.
