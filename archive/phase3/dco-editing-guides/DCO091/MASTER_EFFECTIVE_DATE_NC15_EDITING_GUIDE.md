# DCO091 — Effective date and NC #15 closure (master editing guide)

## 0. DCO091 package and working files

Controlled Word for this DCO lives under `QMSInProcess\DCO091`. Those drafts are redlined. When a FIND string in this guide does not match your open document because the Silq eQMS redline already removed or rewrote that paragraph, skip the literal FIND and apply the REPLACE intent only (definitions, releasing section, no automatic three-day default, per-row calendar dates, Silq Effective date equals DCO row). Use short distinctive substrings in Word Find. Baseline FIND text remains recoverable from the repository mirrors listed below.

This file is the master for NC #15 effective-date edits. Use it together with `README.md` and each `EDITOR_` file in this folder, plus the Silq transition guides referenced in `README.md`.

This guide closes internal audit NC #15 (document control: effective date model) through controlled updates to QM.SLQ001, QM.SLQ014, and FM1-QM.SLQ001. **DCO091 does not include TMP1-QM.SLQ001**; optional TMP1 header or footer alignment applies only if a later DCO revises the template. FM1-QM.SLQ014 is on DCO091 for the Silq attestation update per `EDITOR_FM1_SLQ014_DCO091.md`; NC15 does not add DCO-style date columns to that form. The guide implements SILQ decisions already taken (per-row calendar effective dates, release separate from effective, no new RA-only approval step, originator accounts for regulatory timing, training, and implementation readiness on the DCO).

Baseline mirrors for FIND strings: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ001 A Document Control SOP.md`, `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ014 B Electronic Doc System WI.md`, `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ001 A Document Change Order Form.md`. NC acceptance text: `docs/IA 2025 Questions, Responses/Response to NC list -- Editing Guide.md` (NC #15). The Word file `docs/IA 2025 Questions, Responses/Response to NC list.docx` was not extracted here; wording above matches the markdown editing guide.

Tone and token discipline: match `docs/design-assessment/Output/QM_SLQ001_REV_A_DOCUMENT_CONTROL_SOP_EDITING_GUIDE.md` and `docs/design-assessment/Output/QM_SLQ014_REV_B_ELECTRONIC_DOC_SYSTEM_WI_EDITING_GUIDE.md`. Do not type asterisk characters in paste blocks or controlled document bodies (SILQ preference). Use hyphen bullets in new procedure text unless the template forces numbered lists.

---

## A. Title and scope of this guide

Title: DCO effective date redesign for NC #15 (controlled, risk-aware implementation).

Scope: Revision instructions for QM.SLQ001 Document Control SOP, QM.SLQ014 Electronic Document System WI, and FM1-QM.SLQ001 Document Change Order form. TMP1-QM.SLQ001 applies only when a DCO revises the template and normative header or footer text references release or effective dates; **DCO091 does not revise TMP1.** Cross-reference QM.SLQ003 Employee Training SOP where training timing interacts with document use. No new approval role; RA remains within the existing approver set per Document Approvals Index.

---

## B. ISO 13485 trace (short)

Source for all clause text below: `docs/QMS-Readable-Texts/11-RegulatoryStandards/ISO -- ISO_13485_2016.md`.

- Document identification, review, approval, change control, distribution, and prevention of unintended use of obsolete documents
  - 4.2.4: "A documented procedure shall define the controls needed to:"
  - 4.2.4 a): "review and approve documents for adequacy prior to issue;"
  - 4.2.4 b): "review, update as necessary and re-approve documents;"
  - 4.2.4 c): "ensure that the current revision status of and changes to documents are identified;"
  - 4.2.4 d): "ensure that relevant versions of applicable documents are available at points of use;"
  - 4.2.4 h): "prevent the unintended use of obsolete documents and apply suitable identification to them."
  - 4.2.4 (paragraph after list): "The organization shall ensure that changes to documents are reviewed and approved either by the original approving function or another designated function that has access to pertinent background information upon which to base its decisions."
- Training, competence, and awareness where document changes drive personnel qualification
  - 6.2: "Personnel performing work affecting product quality shall be competent on the basis of appropriate education, training, skills and experience."
  - 6.2: "The organization shall document the process(es) for establishing competence, providing needed training, and ensuring awareness of personnel."
  - 6.2 b): "provide training or take other actions to achieve or maintain the necessary competence;"
  - NOTE under 6.2: "The methodology used to check effectiveness is proportionate to the risk associated with the work for which the training or other action is being provided."

---

## Background (NC #15)

The prior SOP allowed a default effective time of three days after approval when no date was specified, which did not force a documented, per-line decision about training completion, regulatory or certification lead time, supplier or CMO readiness, field implementation, or material disposition. The DCO form expressed timing mainly as R-plus-X relative to release, which pushed offset arithmetic instead of one explicit calendar first-GMP-use date per controlled document row. Work instructions described populating system metadata from that R-plus field rather than from a single approved calendar date aligned to each line item. Internal audit NC #15 (accepted per `docs/IA 2025 Questions, Responses/Response to NC list -- Editing Guide.md`) records that the three-day default did not incorporate risk, training, or implementation readiness and did not ensure changes were implemented in a controlled, risk-based manner. Closing the finding requires per-row calendar dates, originator attestation, approver review of dates and attestation without new approval roles, removal of the automatic three-day rule, and a fixed rule that the system effective date at publication matches the executed DCO for each line.

---

## C. Target process summary (at most 25 lines)

- Each row in the DCO document table represents one controlled document or part number line item. Each row has one calendar Proposed effective date (GMP use) proposed by the originator and subject to the same DCO review and approval cycle as today.
- Release is completion of all required approvals and signatures on the DCO for that package. Effective is the first calendar date on which the released revision may be used for GMP purposes for that line item. Release may occur before the effective date; the released revision must not be used for GMP work until the effective date.
- The originator proposes the calendar effective date per row and completes a short, combined attestation on the DCO that the date accounts for risk, required training completion or justified exception, regulatory or notified-body timing if applicable, supplier or CMO readiness, field implementation, and material disposition where relevant. No separate Regulatory Affairs-only approval step is added; the same approver set defined in Appendix 1 reviews the DCO including reasonableness of each proposed date and attestation.
- The document administrator enters the Silq eQMS Effective date at Release revision for each document number and revision to match the final approved calendar effective date for that same row on the executed DCO after any changes during review are recorded on the DCO.
- The legacy default "effective three days after approval if no date specified" is removed. If the originator leaves a row date blank, the document administrator returns the DCO to the originator for completion before routing; there is no automatic numeric offset.
- The legacy single header field "Req. Effective Date: R + X" is removed as the primary control. R-plus-X may appear only as optional explanatory note in training materials if SILQ chooses to retire it entirely from the form; this guide recommends removal from the form and SOP to avoid dual models.
- QM.SLQ003 continues to govern training methodology; the DCO links proposed effective date to training by originator confirmation and existing Training required block. Training coordinator notification remains per QM.SLQ001 and QM.SLQ003 after release when training is required.

---

## D. Token table

Use only if your DCO package already introduced these tokens in QM.SLQ001 or QM.SLQ014; otherwise omit the table from the released Word files.

| Token | Replace with |
| --- | --- |
| {{QM_SLQ001_DCO_SECTION}} | Final section number and title for Completing DCO form in QM.SLQ001 |
| {{QM_SLQ001_RELEASING_SECTION}} | Final section number and title for releasing documents (Silq eQMS / EDMS) in QM.SLQ001 |
| {{SILQ_EQMS_URL}} | Production Silq eQMS URL (same as companion QM.SLQ014 editing guide) |

---

## E. Per-artifact sections

### E.1 QM.SLQ001 Document Control SOP

Repository mirror: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ001 A Document Control SOP.md`

#### E.1.1 Definitions — General Definitions — Effective Date and Release Date

FIND (two definition paragraphs under General Definitions):

`### Effective Date: The date an approved document is effective for use at the company.`

`### Release Date:  The date a document has been released for use at the company. Note: Release Date may not be the same as the Effective Date.`

REPLACE WITH:

`### Release Date: The calendar date on which all required DCO approvals are complete and the document administrator may publish the approved revision to the controlled system. Release date is recorded by completion of the approval path and publication steps in QM.SLQ014 and this SOP.`

`### Effective Date: The first calendar date on which the released revision of a given document number may be used for GMP purposes at SILQ for that line item. Each document line on a DCO has its own effective date unless the originator documents a deliberate same-date choice for multiple lines. The effective date is proposed by the originator, may be adjusted during DCO review with recorded agreement on the DCO, and is entered into the controlled system at publication per {{QM_SLQ001_RELEASING_SECTION}}.`

#### E.1.2 Procedure: Releasing Documents into Electronic Document Management System (Section 13 in baseline mirror)

FIND:

`## Upon approval of a DCO, the document administrator is to indicate the effective date and provide their signature as the person responsible for release.`

`### Please see Electronic Document System Work Instruction, QM.SLQ014 for detailed steps.`

`## Although documents are considered released with the final approval signature, documents are not effective until the date entered into the DCO by the document administrator.  By default, if no date is specified, released documents are effective as of 3 days of their approval.`

REPLACE WITH:

`## Upon approval of a DCO, the document administrator publishes each approved line item using the calendar effective date recorded for that line on the executed DCO and provides signature or equivalent controlled-system attribution as the person responsible for publication.`

`### Please see Electronic Document System Work Instruction, QM.SLQ014 for detailed steps.`

`## Documents are not effective for GMP use until the approved calendar effective date for each line item. The document administrator does not apply a default offset from approval. If a line item lacks an originator-proposed calendar effective date and required attestation, the document administrator returns the DCO to the originator before publication. If approvers change an effective date during review, the executed DCO shows the final calendar date per line before publication.`

#### E.1.3 Responsibilities — document reviewers and approvers (add one mandatory sentence)

FIND:

`## It is the responsibility of all document reviewers and approvers, especially within their expertise, to consider the effects adding or making changes to a document will have on product safety and efficacy.  In addition, consideration must be given on how additions or changes can affect function of the QMS to maintain product safety and quality.`

REPLACE WITH (append one new sentence after the existing paragraph, same heading):

`## It is the responsibility of all document reviewers and approvers, especially within their expertise, to consider the effects adding or making changes to a document will have on product safety and efficacy.  In addition, consideration must be given on how additions or changes can affect function of the QMS to maintain product safety and quality. Approvers review each line item proposed calendar effective date and the originator attestation for risk, training, regulatory timing, implementation readiness, and material disposition consistency before approval.`

#### E.1.4 Procedure: Completing DCO form — replace Required Effective Date bullet

FIND:

`### Required Effective Date:  Indicate the date the document(s) are required to be effective upon their release date.  Indicate the numbers of days past the release date as such ‘R + X days’.  For example R+0 would indicate the effective date is the same as the release date, whereas R+7 would indicate the effective date is 7 days after the release date.`

REPLACE WITH:

`### Proposed effective date (calendar) per document row: For each row in the document table, enter the calendar date when the new or revised revision is to become effective for GMP use. The same DCO may use different dates on different rows. The originator proposes the date; approvers may require a different final date, which is recorded on the DCO before execution. The document administrator enters the same final calendar date into the controlled system effective date field for that document number and revision at publication.`

#### E.1.5 Procedure: Completing DCO form — add originator attestation block immediately after the new bullet in E.1.4 or after the document table instruction

INSERT after the Proposed effective date bullet (new subheading and one short paragraph plus five checkboxes as a single paste):

`### Originator attestation for proposed effective dates (one response per DCO, covers all lines unless the form adds a per-row narrow column): The originator confirms that each proposed calendar effective date allows controlled implementation, including consideration of patient and product risk, completion of required training before GMP use where training applies or documented justification when training is not applicable before use, regulatory or notified-body notification or filing minimum timelines when applicable, supplier or contract manufacturer readiness, field or inventory implementation when applicable, and alignment with material disposition when material disposition applies.`

`### Check all that apply and attach brief notes on the DCO or referenced project record when any item needs explanation: [ ] Risk level and any needed mitigation timing reviewed for the change. [ ] Training required before GMP use is scheduled to complete before the earliest proposed effective date for affected roles, or justification recorded when use before training is not applicable. [ ] Regulatory or certification timing constraints considered. [ ] Supplier, CMO, or internal implementation readiness considered. [ ] Field or distribution implementation considered when relevant.`

#### E.1.6 Document Change Order Log fields

FIND (under Document Change Order Log):

`#### Release date / Effective date`

REPLACE WITH:

`#### Release date and effective date (per document line as listed on DCO)`

Cross-reference search phrases after edit:

- Search `3 days`, `three days`, `By default`, `R+`, `R +`, `Required Effective Date`, `Req. Effective`. None shall remain as normative effective-date rules except historical log column headers in archived PDFs.
- Search `Section 13`, `Section 14`, `Appendix 1`. Update numbering in narrative cross-references if section numbers shift.

---

### E.2 QM.SLQ014 Electronic Document System WI

Repository mirror: `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ014 B Electronic Doc System WI.md`

#### E.2.1 Procedure: Release of documents — metadata effective date instruction

FIND:

`## Effective Date to be entered into the metadata of the DCO form and each document listed on the DCO. Right click on the DCOxxx form and click on "Metadata and file properties". The Metadata fields window opens on right side of browser. Click Edit. Select the Effective Date so that it is added within the appropriate metadata field (Effective Date is filled in on DCO form by the Originator in the field "Req. Effective Date: R +". In this example, the R+ is "2"; Release Date is the date the final approver signs) Repeat for all documents attached to DCO.`

REPLACE WITH (adapt UI labels to Silq eQMS if the WI revision already renamed FileHold; keep the rule):

`## For each document line on the executed DCO, enter the Effective date in document metadata or in Silq eQMS Document Control at publication so it matches the final approved calendar Proposed effective date for that same document number and revision row. Release timestamp records approval completion; Effective date records the first GMP-use day for that line. If the WI still describes a legacy R-plus field, delete that clause; the DCO form uses per-row calendar dates per QM.SLQ001 {{QM_SLQ001_DCO_SECTION}}.`

#### E.2.2 Procedure: Initiating DCO Approval workflow — Due by reminders

FIND:

`## Update the "Due by" sections accordingly so that email alerts are generated according to DCO's effective date (so approvers get timely reminders).`

REPLACE WITH:

`## Update the "Due by" sections so approvers receive timely reminders relative to the originator change priority and the earliest proposed calendar effective date on the DCO, when that date is within the routing window.`

Cross-reference search:

- `Req. Effective`, `R+`, `R +`, `three days`, `3 days`. Remove as normative instructions.

---

### E.3 FM1-QM.SLQ001 Document Change Order Form

Repository mirror (table excerpt): `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ001 A Document Change Order Form.md`

#### E.3.1 Header strip — remove single R-plus field

FIND table row containing:

`| Req. Effective Date: | R + | R + | Originator: | Originator: |`

REPLACE WITH a header row that removes R-plus and moves originator if needed, for example:

`| Originator: | (name) | | | |`

and relocate effective date columns into the document table per E.3.2.

#### E.3.2 Document listing table — add column

FIND header row:

`| Document Title | Document / Part Number | Current Revision | Description of / Reason for Change |`

REPLACE WITH:

`| Document Title | Document / Part Number | Current Revision | Proposed effective date (calendar, GMP use) | Description of / Reason for Change |`

Add one date cell per content row in the new column. Originator fills Proposed effective date for each populated row. Approvers initial or note changes in the same cell or in margin per company GDP if the date changes during review. Document administrator copies the final approved date into Silq eQMS at publication.

---

### E.4 TMP1-QM.SLQ001 Controlled Document Template

There is no `TMP1-QM.SLQ001` markdown mirror under `docs/QMS-Readable-Texts/` in this repository. Open the controlled Word template in the Forms, Templates, Travelers library.

- If the header or footer contains instructional text referencing R-plus-X or a single global effective date rule, replace with: "Effective date and revision are assigned at release per QM.SLQ001; see the executed DCO for the calendar effective date for this document number and revision."
- If the template only has blank fields for Revision and Date with no normative text, make no change beyond any global style update already on the DCO.

---

## F. FM1-QM.SLQ001 Word form layout

1. Open `FM1-QM.SLQ001` in Word from the controlled source (not an obsolete routing copy).
2. Identify the top metadata table that currently contains `Req. Effective Date:` and `R +`.
3. Delete the two cells that implement R-plus-X as the primary effective-date control. Keep `DCO #`, `Change Priority`, `DCO Type`, `Document Category`, and `Originator` in the header with clear labels.
4. Locate the main document listing table (columns Document Title through Description / Reason).
5. Insert one new column immediately after `Current Revision`. Title the column exactly: `Proposed effective date (calendar, GMP use)`. Set column width similar to Current Revision so the table still prints on one landscape or legal page if that is the current standard.
6. For each data row under that header, merge vertically only if the existing form merges description cells; do not merge the new date column across multiple document rows so each document line keeps its own date.
7. Add below the document table (or in the margin box used for attestations) the originator attestation text from E.1.5 with five checkbox lines. Use Word checkbox content controls or typed X-in-box per SILQ GDP.
8. In the form instructions page or footer note if present, replace any narrative that says R+0 or R+7 with: "Enter one calendar date per document row. Approvers confirm or adjust dates before final signature."
9. If any legacy export or integration still mapped a single R-plus field to a system Effective date field, remap so publication uses the per-row calendar Proposed effective date from the executed DCO for each document number and revision. Silq eQMS Document Control is the system of record after go-live.
10. Save the form revision on the same DCO091 package that releases QM.SLQ001, QM.SLQ014, FM1-QM.SLQ014, and this FM1-QM.SLQ001 change.

---

## G. Silq eQMS alignment

1. For each row on the executed DCO, read Document / Part Number, new revision, and final Proposed effective date (calendar, GMP use).
2. In Silq eQMS Document Control, open that document number. Create or select the draft revision matching the DCO.
3. On Release revision, set Effective date to the same calendar date as that row on the executed DCO after all approval adjustments.
4. Set Change summary and Reason per existing SW.SLQ008 and QM.SLQ001 requirements; do not substitute R-plus math for Effective date.
5. If one DCO releases multiple documents, repeat steps 1 through 4 per document; dates may differ per document per the DCO.
6. File the executed DCO PDF in the Completed DCO location named in QM.SLQ001 so auditors can compare DCO row dates to Silq eQMS revision effective dates.

---

## H. Verification checklist

After Word and Silq updates, search the controlled corpus for these strings. Normative documents and forms should show the Post column state.

| String or pattern | Expected after edit |
| --- | --- |
| `By default, if no date is specified` | Absent from QM.SLQ001 |
| `3 days` / `three days` (as automatic effective date) | Absent from QM.SLQ001 releasing section |
| `R+` / `R +` / `R plus` | Absent from normative SOP, WI, and form instructions; may exist only in historical completed DCO PDFs |
| `Req. Effective Date` | Absent from form header as primary control |
| `Proposed effective date (calendar` | Present on FM1 and referenced in QM.SLQ001 Section completing DCO |
| `Originator attestation` or equivalent titled block | Present on FM1 and referenced in QM.SLQ001 |
| `Effective date` in Silq release steps | Present with rule: matches DCO row calendar date |
| QM.SLQ014 metadata instruction | No linkage to R-plus; calendar per row |

---

## I. Assumptions

- SILQ does not maintain a mandatory fixed delay (for example thirty-day labeling-only delay) in this repository; if a product line later requires a regulatory minimum lead time, the originator records that constraint in the attestation notes and proposes a compliant calendar date without adding a new approver role.
- `Response to NC list.docx` was not parsed; NC #15 acceptance language is taken from `Response to NC list -- Editing Guide.md` only.
- QM.SLQ003 does not define a formula tying effective date to training completion; the closure model uses originator attestation plus approver review, consistent with QM.SLQ003 responsibilities and training requirements (for example documented training before performing a procedure when training is required, with supervised exception as stated in that SOP) and the Retraining section (document administrator and training coordinator notify employees prior to performing tasks to the revised document when retraining is required). Where training is required before GMP use, the proposed effective date is on or after the planned training completion date unless the Training required justification on the DCO documents a SILQ-accepted exception path supervised per QM.SLQ003.
- If Silq eQMS later adds per-approver due dates tied to workflow automation, that feature supplements but does not replace the calendar effective date on each DCO row.

End of guide.
