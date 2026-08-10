# DCO091 — FM1-QM.SLQ001 Document Change Order (Rev A → next revision)

**Before the next FM1 revision exists:** use `docs/DCO091/DCO091_REVIEW_PACKAGE_FM1_REV_A.md` to fill **DCO091 on Rev A** for reviewers (paste blocks and attachment list).

**Baseline:** Rev A layout and text are captured in `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ001 A Document Change Order Form.md` (exported from controlled Word). Edit the live `.docx`; use that mirror only to confirm row labels before you change them.

**Goal:** Remove R-plus as the primary effective-date control, add one **calendar date per document row**, add **originator attestation**, align blank-form sourcing with **Silq eQMS** and QM.SLQ001 B on the same DCO091 package.

---

## 1. Header table (row with `Req. Effective Date` / `R +`)

Rev A row 13 is:

`| Req. Effective Date: | R + | R + | Originator: | ... |`

**Do:** Delete the **`Req. Effective Date:`** and both **`R +`** cells (or the merged equivalent). Keep **Originator** and all other header fields (**DCO #**, **Change Priority**, **DCO Type**, **Document Category**) unchanged unless your style guide requires relayout.

**Do not:** Leave any header field that tells users to compute effective date from **R + X** after release.

---

## 2. Main document table — new column

Rev A columns (row 15–16) are:

`Document Title | Document / Part Number | Current Revision | Description of / Reason for Change`

**Do:** Insert one column **immediately after** `Current Revision`. Set the header text **exactly** (must match QM.SLQ001 Completing DCO form):

`Proposed effective date (calendar, GMP use)`

**Do:** Add one body cell per row under that header; do **not** merge the date column across multiple document rows.

**Do:** In form instructions or footer (if present), state that the originator enters a **single calendar date** per populated row; approvers adjust and initial per GDP; the document administrator enters the **same final date** into Silq eQMS at Release revision for that document number and revision.

---

## 3. Originator attestation (new block)

**Do:** Below the main document table (above “Additional Risk Assessment” is typical), insert one subheading and one short paragraph plus **five** checkbox lines. Use the exact wording from `docs/DCO091/MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md` section **E.1.5** (INSERT block under Completing DCO form), or the same block repeated in `docs/DCO091/EDITOR_COMBINED_QM001B_QM014C_FM1_DCO091.md` Part 1.6.

**Do:** Title the block so auditors can tie it to QM.SLQ001 (for example **Originator attestation for proposed effective dates**).

---

## 4. Silq eQMS and legacy EDMS (instructions, footers, hidden text)

**Do:** Turn on **Show hidden text** and search the whole form for: `FileHold`, `filehold`, `edms009`, `LibraryQA`, `Routing`, `check-in`, `check-out`, `R+`, `R +`, `Req. Effective`.

**Do:** Replace blank-form sourcing with: obtain current FM1 from **Silq eQMS Admin Docs** (library and folder names **identical** to QM.SLQ014 C / QM.SLQ001 B) or from the document administrator.

---

## 5. Revision metadata

**Do:** Bump form revision letter (for example **A → B**), revision history table or title block per SILQ template rules, and list on **DCO091** with QM.SLQ001 B and QM.SLQ014 C.

**Do:** After Word is final, optionally add the basename to `FILE_MAP` in `scripts/refresh_dco091_readable_texts.py` and run `python scripts/refresh_dco091_readable_texts.py` to refresh `docs/QMS-Readable-Texts/`.

---

## 6. Quick verification

| Check | Pass |
| --- | --- |
| Header has no `Req. Effective Date` / `R +` primary control | |
| Document table has column **Proposed effective date (calendar, GMP use)** | |
| Attestation block with five checkboxes present | |
| No FileHold or legacy URL in body, footer, hidden text | |
| Instructions describe calendar per row, not R-plus arithmetic | |

For Silq publication steps after execution, use **MASTER** section **G** in `docs/DCO091/MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md`.
