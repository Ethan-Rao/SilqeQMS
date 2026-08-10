# DCO091 — QM.SLQ001 Document Control SOP (editing order)

Working file: redlined Word in `QMSInProcess\DCO091` (not stored in this repo).

## Part A — Silq eQMS transition (complete first unless already done in your redline)

Follow every PASTE block and token replacement in:

`docs/design-assessment/Output/QM_SLQ001_REV_A_DOCUMENT_CONTROL_SOP_EDITING_GUIDE.md`

Work top to bottom. Resolve every FileHold and legacy path string. Replace tokens (for example `{{SILQ_EQMS_URL}}`, `{{QM_SLQ014_WI_TITLE}}`, folder tokens) with values approved on DCO091.

If a PASTE section is already applied in your redline, confirm with Word Find (FileHold, edms009, LibraryQA) that nothing remains.

## Part B — NC #15 effective date (apply after Part A or merge during same edit pass)

Open in parallel:

`docs/DCO091/MASTER_EFFECTIVE_DATE_NC15_EDITING_GUIDE.md`

Apply only sections E.1.1 through E.1.6 (Definitions Effective or Release; Releasing Documents opening and three-day default; Responsibilities approver sentence; Completing DCO form Proposed effective date bullet; Originator attestation insert; DCO log column header).

Paste blocks in MASTER use triple-backtick fenced lines in the master document; copy the inner text without the fences into Word.

## Part C — Cross-check against FM1-QM.SLQ001

After Part B, QM.SLQ001 Completing DCO form text must reference:

- Proposed effective date (calendar, GMP use) per row on the form.
- Originator attestation block on the form.

Ensure internal cross-references to the Completing DCO form procedure and Releasing procedure match final Word section numbers.

## Part D — Verification (QM.SLQ001 only)

Run Word Find on the saved SOP for:

- FileHold, filehold, edms009, LibraryQA, Routing DCOs, My Tasks, check-in, check-out, Send to email, External Documents drawer, Standards Folder, DCO Complete folder (all absent in normative body).
- `By default, if no date is specified` (absent).
- `three days` or `3 days` as automatic effective date after approval (absent as normative rule).
- `R+` or `R +` as primary effective-date control in normative body (absent).
- `Proposed effective date (calendar` (present in Completing DCO section or equivalent title you approved).
- Originator attestation title or equivalent (present in Completing DCO section).

## Part E — DCO091 record

List QM.SLQ001 on DCO091 with the new revision letter. Note in the DCO reason line that the package includes Silq eQMS transition and NC #15 effective date closure.
