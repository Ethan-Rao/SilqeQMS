# DCO091 — Combined editing guide (QM.SLQ001 B, QM.SLQ014 C, FM1-QM.SLQ001)

This single guide gives **specific instructions** for the two QM documents at revisions **B** (SLQ001) and **C** (SLQ014), and for the **FM1-QM.SLQ001** Document Change Order form you will create or revise **after** the QM text is stable. DCO091 does **not** include TMP1-QM.SLQ001.

**Order of work (recommended):**

1. QM.SLQ001 B — Silq transition, then NC #15 text, then cross-refs and cleanup.
2. QM.SLQ014 C — Silq transition, then NC #15 deltas, then align every URL and label to QM.SLQ001 B.
3. FM1-QM.SLQ001 — Apply table and attestation layout when you build the form; wording must match QM.SLQ001 “Completing DCO form” exactly for the new column title.

**Upstream detail (use when this guide says “full paste blocks”):**

- Silq transition for SLQ001: `docs/design-assessment/Output/QM_SLQ001_REV_A_DOCUMENT_CONTROL_SOP_EDITING_GUIDE.md`
- Silq transition for SLQ014: `docs/design-assessment/Output/QM_SLQ014_REV_B_ELECTRONIC_DOC_SYSTEM_WI_EDITING_GUIDE.md`
- NC #15 master (Silq publication steps G–H, verification table): `docs/DCO091/MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md`

**Tokens:** Before final PDF, replace any `{{QM_SLQ001_DCO_SECTION}}`, `{{QM_SLQ001_RELEASING_SECTION}}`, and `{{SILQ_EQMS_URL}}` in QM.SLQ014 with the **final section numbers and titles** and the **production URL** from QM.SLQ001 B (same values in both documents).

---

## Part 1 — QM.SLQ001 B Document Control SOP

Working file: `QMSInProcess\DCO091\QM.SLQ001 B Document Control SOP.docx` (or your controlled filename).

### 1.1 Silq eQMS transition (do first unless already complete)

1. Open `docs/design-assessment/Output/QM_SLQ001_REV_A_DOCUMENT_CONTROL_SOP_EDITING_GUIDE.md`.
2. Apply every PASTE block and token replacement **from top to bottom** (definitions, procedures, retention table, external documents, DCO workflow, appendix cross-refs).
3. Resolve **all** legacy system strings. Run Word **Find** (include **headers, footers, and hidden text**) for: `FileHold`, `filehold`, `edms009`, `LibraryQA`, `Routing DCO`, `My Tasks`, `check-in`, `check-out`, `Send to email`, `Take a copy`, `ver link`, `Sign off sheet`, `Local FileHold Account`, `External Documents drawer`, `Standards Folder`, `DCO Complete` (as legacy folder names). Normative body must be **zero** hits.

### 1.2 NC #15 — definitions (Release vs Effective)

Under **General Definitions**, locate the two paragraphs that define Effective Date and Release Date in the **old** short form.

**FIND (two paragraphs):**

`### Effective Date: The date an approved document is effective for use at the company.`

`### Release Date:  The date a document has been released for use at the company. Note: Release Date may not be the same as the Effective Date.`

**REPLACE WITH:**

`### Release Date: The calendar date on which all required DCO approvals are complete and the document administrator may publish the approved revision to the controlled system. Release date is recorded by completion of the approval path and publication steps in QM.SLQ014 and this SOP.`

`### Effective Date: The first calendar date on which the released revision of a given document number may be used for GMP purposes at SILQ for that line item. Each document line on a DCO has its own effective date unless the originator documents a deliberate same-date choice for multiple lines. The effective date is proposed by the originator, may be adjusted during DCO review with recorded agreement on the DCO, and is entered into the controlled system at publication per the procedure titled Releasing Documents into Electronic Document Management System (insert the final section number and title from this SOP after renumbering).`

### 1.3 NC #15 — Procedure: Releasing Documents (remove three-day default)

**FIND (three blocks in sequence):**

`## Upon approval of a DCO, the document administrator is to indicate the effective date and provide their signature as the person responsible for release.`

`### Please see Electronic Document System Work Instruction, QM.SLQ014 for detailed steps.`

`## Although documents are considered released with the final approval signature, documents are not effective until the date entered into the DCO by the document administrator.  By default, if no date is specified, released documents are effective as of 3 days of their approval.`

If the middle **Please see QM.SLQ014** line was already merged into one paragraph with different wording, replace only the first and third **ideas**: publication uses **per-line calendar dates** from the executed DCO; **no** automatic three-day rule.

**REPLACE WITH:**

`## Upon approval of a DCO, the document administrator publishes each approved line item using the calendar effective date recorded for that line on the executed DCO and provides signature or equivalent controlled-system attribution as the person responsible for publication.`

`### Please see Electronic Document System Work Instruction, QM.SLQ014 for detailed steps.`

`## Documents are not effective for GMP use until the approved calendar effective date for each line item. The document administrator does not apply a default offset from approval. If a line item lacks an originator-proposed calendar effective date and required attestation, the document administrator returns the DCO to the originator before publication. If approvers change an effective date during review, the executed DCO shows the final calendar date per line before publication.`

### 1.4 NC #15 — Responsibilities (approvers)

**FIND:**

`## It is the responsibility of all document reviewers and approvers, especially within their expertise, to consider the effects adding or making changes to a document will have on product safety and efficacy.  In addition, consideration must be given on how additions or changes can affect function of the QMS to maintain product safety and quality.`

**REPLACE WITH (same paragraph plus one new sentence):**

`## It is the responsibility of all document reviewers and approvers, especially within their expertise, to consider the effects adding or making changes to a document will have on product safety and efficacy.  In addition, consideration must be given on how additions or changes can affect function of the QMS to maintain product safety and quality. Approvers review each line item proposed calendar effective date and the originator attestation for risk, training, regulatory timing, implementation readiness, and material disposition consistency before approval.`

### 1.5 NC #15 — Completing DCO form (replace R-plus bullet)

**FIND:**

`### Required Effective Date:  Indicate the date the document(s) are required to be effective upon their release date.  Indicate the numbers of days past the release date as such ‘R + X days’.  For example R+0 would indicate the effective date is the same as the release date, whereas R+7 would indicate the effective date is 7 days after the release date.`

**REPLACE WITH:**

`### Proposed effective date (calendar) per document row: For each row in the document table, enter the calendar date when the new or revised revision is to become effective for GMP use. The same DCO may use different dates on different rows. The originator proposes the date; approvers may require a different final date, which is recorded on the DCO before execution. The document administrator enters the same final calendar date into the controlled system effective date field for that document number and revision at publication.`

### 1.6 NC #15 — Originator attestation (insert on SOP narrative)

**INSERT** immediately after the new bullet in 1.5 (or after the paragraph that describes the document table, if that reads better):

`### Originator attestation for proposed effective dates (one response per DCO, covers all lines unless the form adds a per-row narrow column): The originator confirms that each proposed calendar effective date allows controlled implementation, including consideration of patient and product risk, completion of required training before GMP use where training applies or documented justification when training is not applicable before use, regulatory or notified-body notification or filing minimum timelines when applicable, supplier or contract manufacturer readiness, field or inventory implementation when applicable, and alignment with material disposition when material disposition applies.`

`### Check all that apply and attach brief notes on the DCO or referenced project record when any item needs explanation: [ ] Risk level and any needed mitigation timing reviewed for the change. [ ] Training required before GMP use is scheduled to complete before the earliest proposed effective date for affected roles, or justification recorded when use before training is not applicable. [ ] Regulatory or certification timing constraints considered. [ ] Supplier, CMO, or internal implementation readiness considered. [ ] Field or distribution implementation considered when relevant.`

### 1.7 NC #15 — DCO log column header

Under **Document Change Order Log**, find:

`#### Release date / Effective date`

**REPLACE WITH:**

`#### Release date and effective date (per document line as listed on DCO)`

### 1.8 Word quality pass (QM.SLQ001 B)

After global replace for Silq, run **Find** for glued fragments and fix manually:

- `Silq eQMSSilq`, `Silq eQMSThe`, `Silq eQMSIn`, `QM.SLQ014It`, `)Silq`, `PDFSilq`, `Silq eQMSto`, `matrixSilq`

Restore missing periods, spaces, and line breaks so each sentence reads normally. Remove duplicate product name in one sentence (for example only one “Silq eQMS” where two were concatenated).

Replace instruction placeholder if still present: the DCO instructions line that says **update this cross-reference to the final Word section number** — insert the real **Document Categories** section number and title.

### 1.9 Final checks (QM.SLQ001 B)

- **Find:** `By default, if no date is specified`, `three days` / `3 days` (as automatic effective), `R+`, `R +`, `Required Effective Date`, `Req. Effective` as **normative** effective-date control — all **absent** except as noted for historical log PDFs in MASTER.
- **Find:** `Proposed effective date` — **present** in Completing DCO section; attestation title or equivalent **present**.
- **Reference Documents** table: QM.SLQ014 title and revision **C** (or final revision letter on DCO091).
- **Update TOC** and all internal “Section NN” cross-references after renumbering.

---

## Part 2 — QM.SLQ014 C Electronic Document System WI

Working file: `QMSInProcess\DCO091\QM.SLQ014 C Electronic Doc System WI.docx`.

### 2.1 Silq eQMS transition (do first unless already complete)

1. Open `docs/design-assessment/Output/QM_SLQ014_REV_B_ELECTRONIC_DOC_SYSTEM_WI_EDITING_GUIDE.md`.
2. Apply PASTE blocks through the full procedure set (including the long tail from section 13.7 onward if your file still matches the guide’s baseline).
3. Same **Find** sweep as 1.1 — **zero** FileHold and legacy URL strings in normative text, footers, hidden text.

### 2.2 NC #15 — Release procedure (metadata / Silq Effective date)

Locate **Procedure: Release of documents (Document Administrator only)** and any legacy block that tied Effective date to **Req. Effective Date: R +** or FileHold metadata.

**FIND (baseline-style; adapt if your C revision already shortened the paragraph):**

`## Effective Date to be entered into the metadata of the DCO form and each document listed on the DCO. Right click on the DCOxxx form and click on "Metadata and file properties". The Metadata fields window opens on right side of browser. Click Edit. Select the Effective Date so that it is added within the appropriate metadata field (Effective Date is filled in on DCO form by the Originator in the field "Req. Effective Date: R +". In this example, the R+ is "2"; Release Date is the date the final approver signs) Repeat for all documents attached to DCO.`

**REPLACE WITH:**

`## For each document line on the executed DCO, enter the Effective date in Silq eQMS Document Control at Release revision so it matches the final approved calendar Proposed effective date for that same document number and revision row. Release records completion of approvals and publication; Effective date is the first GMP-use calendar day for that line. The DCO form uses per-row calendar dates per QM.SLQ001 (use the final section number and title for Completing DCO form). Do not derive Effective date from R-plus offset arithmetic.`

### 2.3 NC #15 — Initiating DCO workflow (Due by reminders)

**FIND:**

`## Update the "Due by" sections accordingly so that email alerts are generated according to DCO's effective date (so approvers get timely reminders).`

**REPLACE WITH:**

`## Update the "Due by" sections so approvers receive timely reminders relative to the originator change priority and the earliest proposed calendar effective date on the DCO, when that date is within the routing window.`

### 2.4 Consistency with QM.SLQ001 B

- Production URL, **Document Control (DCOs)** card name, **Admin Docs** library names, and **Completed DCO** filing path must match QM.SLQ001 B **verbatim** where both documents name the same object.
- In **Release of documents**, remove wording that calls Silq **Effective date** “optional” if that contradicts the rule: **must equal** the executed DCO row date for each numbered document at publication.
- Under **Review DCO Contents**, add a short bullet if needed: approvers confirm **proposed calendar dates** and **originator attestation** are reasonable before signing (QM.SLQ001 carries the primary responsibility sentence; WI may echo for DA and approver tasks).

### 2.5 Word quality pass (QM.SLQ014 C)

Fix known spacing and break issues:

- After “Silq eQMS” before “Open a supported browser” — insert period or paragraph break.
- `Document Administrator only` followed immediately by `When all approvals` — insert period or new paragraph.
- `workflow. .` — single period and normal spacing.
- `corporate email.After` — space after first sentence.
- `Download.Procedure:` — line break before **Procedure: Quality System Electronic Signatures**.

### 2.6 Final checks (QM.SLQ014 C)

- **Find:** `Req. Effective`, `R+`, `R +`, `three days`, `3 days` — not used as normative effective-date rules.
- **Sense-check:** Silq Release revision **Effective date** = DCO **Proposed effective date** row for that document (after any approver adjustment recorded on the DCO).
- **Update TOC** and appendix titles if section numbers shifted.
- Replace placeholder clauses such as **path to be mirrored in QM.SLQ001** with the **exact** Admin Docs path stated in released QM.SLQ001 B, or delete the placeholder phrase.

---

## Part 3 — FM1-QM.SLQ001 Document Change Order form (create or revise next)

Create or revise the form **after** QM.SLQ001 B and QM.SLQ014 C text is final, so column titles and instructions match the SOP.

### 3.1 Source of truth in MASTER

For table **FIND/REPLACE** sketches and numbered layout, also read `docs/DCO091/MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md` sections **E.3**, **F**, and **G**.

### 3.2 Header strip

1. Remove **Req. Effective Date:** and **R +** (or any single global R-plus field) as the **primary** effective-date control from the top metadata table.
2. Keep **DCO #**, **Change Priority**, **DCO Type**, **Document category**, **Originator** (and company-required fields) with clear labels.

### 3.3 Document listing table — new column

1. Locate the main table with columns through **Description of / Reason for Change** (or your current equivalent).

**Header row must become (exact new column title for match to QM.SLQ001):**

`| Document Title | Document / Part Number | Current Revision | Proposed effective date (calendar, GMP use) | Description of / Reason for Change |`

2. Insert the new column **immediately after** Current Revision.
3. Ensure **one date cell per document row**; do not merge the date column across multiple document rows.
4. Originator enters the calendar date per row; approvers record changes in that cell or per GDP margin notes; document administrator copies the **final** date into Silq eQMS at Release revision for that document number and revision.

### 3.4 Originator attestation on the form

Paste the **same** attestation subheading, paragraph, and five checkbox lines as in **Part 1.6** of this guide onto the form (typically **below** the document table). Use Word checkbox content controls or SILQ-approved “X in box” convention.

### 3.5 Form instructions and footer

- Instruct originators to obtain blank FM1 from **Silq eQMS Admin Docs**, library **Forms, Templates and Travelers** (use exact library string from QM.SLQ001 / QM.SLQ014), or from the document administrator — **same** wording as the SOP opening for Completing DCO.
- Replace any training text that says **R+0** or **R+7** as the primary rule with: **One calendar date per document row; approvers confirm or adjust dates before final signature.**
- **Find:** `FileHold` — **absent** in instructions and hidden text.

### 3.6 Silq publication alignment (form owner and DA)

When filing completed DCOs and releasing in Silq, follow **MASTER section G** (read each numbered step): for each DCO row, set Silq **Effective date** to the **same calendar date** as that row on the executed DCO; use **Reason** and **Change summary** per SW.SLQ008 and QM.SLQ001; file executed DCO PDF in the **Completed DCO** location named in QM.SLQ001 B.

### 3.7 Verification (FM1 only)

| Check | Expected |
| --- | --- |
| Header | No `Req. Effective Date:` plus `R +` as primary control |
| Document table | Column title exactly **Proposed effective date (calendar, GMP use)** |
| Attestation | Five checkbox lines present |
| Instructions | No R-plus as primary effective-date model |
| Hidden text | No legacy EDMS strings |

### 3.8 Repository mirror (optional after Word is saved)

Add the new docx basename to `FILE_MAP` in `scripts/refresh_dco091_readable_texts.py` and run `python scripts/refresh_dco091_readable_texts.py` so `docs/QMS-Readable-Texts/` receives a markdown mirror.

---

## Part 4 — Whole-package verification (all three)

Run **MASTER** section **H** verification table (`docs/DCO091/MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md`): each pattern’s “Expected after edit” column must be satisfied across QM.SLQ001 B, QM.SLQ014 C, and FM1-QM.SLQ001.

List all three documents plus FM1-QM.SLQ014 on DCO091 with consistent reason text (Silq eQMS transition and NC #15 effective date closure).

---

End of combined guide.
