# Developer Prompt: Document Number Log Reconciliation and DCO Creation

**Date:** 2026-03-31

---

## Objective

Compare the QMS Document Register (`QM_DOCUMENT_REGISTER.csv`) against the historical Silq Document Number Log and DCO Log to: (1) verify that no controlled documents are missing from the register, and (2) identify which new or revised documents require Document Change Orders (DCOs) that have not yet been created. Then draft the required DCO forms. **Omit anything related to employee training.**

---

## Context

SILQ maintains two administrative logs per QM.SLQ001 (Document Control SOP):

1. **Document Number Log** — a master list of every assigned document number, including: assigned document number, document title, date assigned, and used/not-used status. This log is organized by document code (QM, SW, DC, VV, FM, TMP, etc.). Per QM.SLQ001 Section 7.3, only the document administrator may assign document numbers, and numbers of obsolete documents are never reused.

2. **DCO Log** — a record of every approved Document Change Order, including: DCO#, listed document/part numbers, release date/effective date, revision, document originator, and whether risk assessment, validation, training, material disposition, and/or regulatory assessment was required.

These logs were historically maintained in FileHold. The user has exported them and placed them in the project for your review.

### What has happened recently

- SILQ has built a new custom EDMS called SilqQMS to replace FileHold
- Software validation documents (SW.SLQ007–009) have been created for SilqQMS
- A Design Project Plan (DC.SLQ002) and Design Project Scope Form (FM1-QM.SLQ004 executed for DC.SLQ002) have been created
- The QM Document Register has been updated to include all SW, DC, VV, FM, and TMP document series
- Some QM documents have newer revisions in the source files than what may be captured on the DCO Log (e.g., QM.SLQ034 is now Rev G)

### Additional document series in the Document Number Log

The Document Number Log contains document series beyond the QM, SW, DC, and VV series currently in the Register. The agent should review and reconcile these as well:

- **AD** — Administrative (1 document: AD.SLQ001)
- **OM** — Operations Manufacturing (4 documents: OM.SLQ001–004)
- **RM** — Risk Management (RM.SLQ012 and related files)
- **SP** — Specifications (SP-C.SLQ001–003, SP-M.SLQ001, and component labeling specs SP-L.SLQ002–010)
- **QC** — Quality Control (QC-C.SLQ001, QC-E.SLQ015)
- **BOM** — Bills of Materials (BOM-C.SLQ001)
- **BOR** — Bills of Reference (BOR-C.SLQ001)
- **MP** — Manufacturing Procedures (MP-C.SLQ001)
- **L** — Labeling (L.SLQ001, L.SLQ011–013)

These are located in the DMR folder (`docs/QMS-Readable-Texts/18-DMR/`) and Administration folder (`docs/QMS-Readable-Texts/19-Administration/`). The agent should verify that ALL document series in the Document Number Log are represented in the reconciliation, not just the QM/SW/DC/VV series.

---

## Log Locations

Both logs have been extracted to readable markdown:

1. **Document Number Log** (original Excel): `DCOs/SILQ Document Number Log.xlsx`
   - Readable markdown: `docs/QMS-Readable-Texts/17-DCOs/SILQ Document Number Log.md`
   - Contains 6 sheets organized by document code: AD (Admin), OM (Operations Manufacturing), QM (Quality Management System), RM (Risk Management), SW (Software), VV (Verification & Validation)
   - Each sheet lists: Assigned Document Number, Document Title, Requestor, Date Assigned, Rev, DCO #, Filed By, Effective Date, Used/Not-used
   - **Important:** Early entries use the legacy `QM.HX` prefix (e.g., `QM.HX001`) which was later renamed to `QM.SLQ` (e.g., `QM.SLQ001`). Treat `QM.HX###` and `QM.SLQ###` as the same document when reconciling.

2. **DCO Log** (original Excel): `DCOs/SILQ DCO Log.xlsx`
   - Readable markdown: `docs/QMS-Readable-Texts/17-DCOs/SILQ DCO Log.md`
   - Single sheet (2020-2025) containing all 88+ completed DCOs
   - Each row lists: DCO Number, line item, affected document/part number, current rev, new rev, title, originator, date requested, filed by, release date, effective date, and assessment flags (training, risk, validation, regulatory, material disposition)
   - **Important:** Early DCO entries also use the `QM.HX` prefix.

3. **Completed DCO forms**: `DCOs/CompletedDCOs/` contains 90 individual DCO .docx files (DCO001–DCO088, plus some with letter suffixes like DCO042A, DCO053B, DCO077B)
   - Readable markdown versions: `docs/QMS-Readable-Texts/17-DCOs/CompletedDCOs/` (all 90 extracted)

**Do NOT invent or fabricate log data.** If any data appears inconsistent, flag it for user review.

---

## Task 1: Reconcile Register Against Document Number Log

### 1A. Register → Log comparison (find unregistered numbers)

For every document number in the Document Number Log, check whether it appears in `QM_DOCUMENT_REGISTER.csv`. Flag any document numbers that are:

- **In the Log but NOT in the Register** — these are documents that were formally assigned numbers but may not be in the project folders. Report each one with its log entry details. Note: some may be legitimately obsoleted or cancelled.
- **Sequence gaps** — document numbers that were skipped (e.g., QM.SLQ024, QM.SLQ031, QM.SLQ041, QM.SLQ042, QM.SLQ044 are not in the register). Check whether these appear in the Document Number Log as "not used" or assigned to documents we don't have.

### 1B. Register → Log comparison (find undocumented documents)

For every entry in the Register, check whether it appears in the Document Number Log. Flag any documents that are:

- **In the Register but NOT in the Log** — these are documents that exist in the project but were never formally assigned a number through the log. This is expected for the new SW.SLQ007–009 and DC.SLQ002 documents (they haven't been through the DCO process yet). But if older documents (QM series, VV series) are missing from the log, that is a discrepancy worth noting.

### 1C. Revision comparison

For every document that appears in BOTH the Register and the DCO Log, compare the revision letter:

- **Register revision > DCO Log revision** — the document has been revised since its last DCO. This means a new DCO is needed.
- **Register revision < DCO Log revision** — the register may be stale. Flag for user review.
- **Register revision = DCO Log revision** — no action needed.

### 1D. Output

Produce a reconciliation summary as a markdown table in your output:

```
| Document ID | In Register? | In Doc Number Log? | Register Rev | Last DCO Rev | Status |
|---|---|---|---|---|---|
| QM.SLQ001 | Yes | Yes | A | A | Current |
| SW.SLQ007 | Yes | No | A | N/A | Needs number assignment + DCO |
| ... | ... | ... | ... | ... | ... |
```

---

## Task 2: Identify and Draft DCOs

### 2A. Documents requiring DCOs

Based on the reconciliation (or, if logs are unavailable, based on known project state), the following documents are expected to need DCOs:

**New documents (never had a DCO):**

| Document ID | Rev | Title | Rationale |
|---|---|---|---|
| DC.SLQ002 | A | Design Project Plan, SilqQMS EDMS Transition | New design project plan |
| SW.SLQ007 | A | Software Validation Plan, SilqQMS | New validation deliverable |
| SW.SLQ008 | A | Product Requirements Specification, SilqQMS | New validation deliverable |
| SW.SLQ009 | A | Software Verification Test Plan, SilqQMS | New validation deliverable |

Note: SW.SLQ001–006 (FileHold) should already have DCOs from when they were originally released. Verify against the DCO Log. If they don't, flag them but do NOT create new DCOs for historical FileHold documents — that is a user decision.

**Previously revised documents — DCOs now confirmed to exist:**

| Document ID | Register Rev | DCO # | Status |
|---|---|---|---|
| QM.SLQ022 | B (A→B) | 087 | Completed Dec 2025. DCO form in `DCOs/CompletedDCOs/DCO087.docx`. Package in `QMSInProcess/DCO087/`. **Not yet in DCO Log Excel — needs to be added.** |
| QM.SLQ034 | G (F→G) | 088 | Completed Mar 2026. DCO form in `DCOs/CompletedDCOs/DCO088.docx`. Package in `QMSInProcess/DCO088/`. **Not yet in DCO Log Excel — needs to be added.** |
| QM.SLQ004 | B (A→B) | 089 | In process. Package in `QMSInProcess/DCO089/`. Driven by CAPA 003-2025 (FDA 483 Obs. 2 — unauthorized supplier design change). **Not yet in DCO Log Excel.** |

**No additional DCOs are needed for QM document revisions.** All three revisions have DCOs assigned.

### 2B. DCO form drafting

For each document (or group of documents) requiring a DCO, draft the DCO form content. The DCO form is FM1-QM.SLQ001 (Document Change Order Form). Read the extracted version at `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ001 A Document Change Order Form.md` for the form structure.

**DCO to draft:**
- **DCO 090 — Phase 0 package**: DC.SLQ002, SW.SLQ007, SW.SLQ008, SW.SLQ009 should be on a single DCO since they are being released together as the SilqQMS EDMS validation and transition planning package.
- **No additional DCOs needed for QM revisions** — DCOs 087 (QM.SLQ022), 088 (QM.SLQ034), and 089 (QM.SLQ004) already exist.

For each DCO, provide the following information in a clearly formatted markdown section:

```
### DCO #: 090 (next available — 089 is taken by QM.SLQ004 A→B)

**Change Priority:** Medium
**DCO Type:** Permanent DCO
**Document Category:** [Design Document / SOP / etc.]
**Required Effective Date:** R+0 (or as appropriate)
**Originator:** Ethan Rao

| Document Title | Document / Part Number | Current Revision | Description of / Reason for Change |
|---|---|---|---|
| [Title] | [ID] | New | Description: [what the document is] / Reason: [why it's being created/changed] |

**Additional Risk Assessment Required?** No
Justification: [brief justification]

**Verification or Validation Required?** [Yes/No]
[If Yes, reference the applicable V&V documents]

**Training Required?** No
Justification: [brief justification]

**Material Disposition Required?** No
Justification: [brief justification]

**Potential Regulatory Impact?** No
Justification: [brief justification]

**Approval Group:** [Per QM.SLQ001 Appendix 1 — look up the correct group based on document code and category]
```

### 2C. DCO 090 — Phase 0 package

**Important:** DCO 089 is already taken (QM.SLQ004 A→B). The Phase 0 package is **DCO 090**.

This is the primary DCO to draft. It should include:

| Document Title | Document / Part Number | Current Revision |
|---|---|---|
| Design Project Plan, SilqQMS EDMS Transition | DC.SLQ002 | New (Rev A) |
| Software Validation Plan, SilqQMS | SW.SLQ007 | New (Rev A) |
| Product Requirements Specification, SilqQMS | SW.SLQ008 | New (Rev A) |
| Software Verification Test Plan, SilqQMS | SW.SLQ009 | New (Rev A) |

**Description of change:** Initial release of the SilqQMS EDMS validation and transition planning document package. This package includes the design project plan for the FileHold-to-SilqQMS transition (DC.SLQ002) and the first three software validation deliverables for SilqQMS (SW.SLQ007–009) per QM.SLQ032 (Software Validation SOP).

**Reason for change:** SILQ is transitioning its electronic document management system from FileHold to SilqQMS. These documents define the transition plan and initiate the software validation process required by ISO 13485:2016 clause 4.1.6 and QM.SLQ032.

**DCO form fields:**
- **Risk Assessment Required?** No — SilqQMS is an EDMS that does not directly affect product safety. Risk analysis is included within SW.SLQ008 per QM.SLQ032.
- **V&V Required?** Yes — The software validation is documented in SW.SLQ007–012. SW.SLQ007 (Validation Plan), SW.SLQ008 (Requirements Specification with risk analysis), and SW.SLQ009 (Verification Test Plan) are included in this DCO. SW.SLQ010–012 will follow in a subsequent DCO upon completion.
- **Training Required?** No — System training will occur in Phase 4 of DC.SLQ002 after all procedure revisions are complete.
- **Material Disposition Required?** No — No product impact.
- **Potential Regulatory Impact?** No — This is an internal QMS infrastructure change. The EDMS transition does not affect product design, clinical data, or regulatory submissions.
- **Approval Group:** Per QM.SLQ001 Appendix 1:
  - DC Design Documents → Group C (Originator, QA, RA, R&D/Engineering, Manufacturing)
  - SW Design Documents → Group A (Originator, QA, RA, R&D/Engineering)
  - Since the DCO includes both DC and SW documents, use the more inclusive **Group C**.

### 2D. Document Number Log updates

For each new document that needs a number formally assigned, draft the Document Number Log entry:

| Assigned Document Number | Document Title | Date Assigned | Used/Not-Used |
|---|---|---|---|
| DC.SLQ002 | Design Project Plan, SilqQMS EDMS Transition | `[User to fill: date]` | Used |
| SW.SLQ007 | Software Validation Plan, SilqQMS | `[User to fill: date]` | Used |
| SW.SLQ008 | Product Requirements Specification, SilqQMS | `[User to fill: date]` | Used |
| SW.SLQ009 | Software Verification Test Plan, SilqQMS | `[User to fill: date]` | Used |

Note: SW.SLQ010–012 should also be reserved (assigned but marked as "In Progress" or "Reserved") so the numbers are locked in for the remaining validation deliverables.

---

## Task 3: Summary Output

Provide a structured summary including:

1. **Reconciliation results** — the full comparison table from Task 1D
2. **Missing documents** — any document numbers in the log that are not in the project
3. **Sequence gap explanations** — what the log says about skipped numbers
4. **DCOs drafted** — list of DCOs with their document contents
5. **Document Number Log additions** — entries for new document numbers
6. **Open questions** — anything requiring user decision before proceeding

---

## Resources

| Resource | Location |
|---|---|
| Document Register | `QM_DOCUMENT_REGISTER.csv` |
| QM.SLQ001 (Document Control SOP) | `docs/QMS-Readable-Texts/01-QM-Documents/QM.SLQ001 A Document Control SOP.md` |
| FM1-QM.SLQ001 (DCO Form) | `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/Forms -- FM1-QM.SLQ001 A Document Change Order Form.md` |
| QM.SLQ001 Appendix 1 (Approval Groups) | Included at the end of the QM.SLQ001 readable text |
| Document Number Log (readable) | `docs/QMS-Readable-Texts/17-DCOs/SILQ Document Number Log.md` |
| DCO Log (readable) | `docs/QMS-Readable-Texts/17-DCOs/SILQ DCO Log.md` |
| Completed DCO Forms (readable) | `docs/QMS-Readable-Texts/17-DCOs/CompletedDCOs/` (90 files: DCO001.md–DCO088.md) |
| QMS In-Process Documents (readable) | `docs/QMS-Readable-Texts/20-QMSInProcess/` (CAPAs, DCO packages, supplier docs) |
| Previous Revisions (readable) | `docs/QMS-Readable-Texts/17-DCOs/PreviousRevisions/` (12 archived prior revision files) |
| DMR Documents (readable) | `docs/QMS-Readable-Texts/18-DMR/` (specs, BOMs, labeling, mfg procedures) |
| Administration Documents (readable) | `docs/QMS-Readable-Texts/19-Administration/` (AD.SLQ001) |

### QMS-Readable-Texts Folder Structure

All QMS content has been extracted into readable markdown. The full folder index:

| # | Folder | Source | Contents |
|---|---|---|---|
| 01 | `01-QM-Documents` | `QM Documents/` | QM SOPs and work instructions |
| 02 | `02-Forms-Templates-Travelers` | `Forms, Templates, and Travelers/` | FM, TMP, and TRV forms |
| 03 | `03-Audits` | `Audits/` | Audit records |
| 04 | `04-CAPAs` | `CAPAs/` | CAPA records |
| 05 | `05-DHF` | `DHF/` (root VV docs) | Verification & Validation protocols/reports |
| 06 | `06-Equipment` | `Equipment/` | Equipment records |
| 07 | `07-ManagementReview` | `ManagementReviewMeetings/` | Management review meeting records |
| 08 | `08-Manufacturing` | `Manufacturing/` | Manufacturing records |
| 09 | `09-NCMR` | `NCMR/` | Non-conformance reports |
| 10 | `10-PostMarketSurveillance` | `PostMarketSurviellance/` | Post-market surveillance records |
| 11 | `11-RegulatoryStandards` | `RegulatoryStandards&Approvals/` | ISO standards, FDA guidance |
| 12a | `12-DHF-Software` | `DHF/Software/` | SW.SLQ001–009, DC.SLQ002, FM1 scope forms |
| 12b | `12-RiskManagement` | `RiskManagement/` | Risk management files |
| 13 | `13-Suppliers` | `Suppliers/` | Supplier records |
| 14 | `14-Supplies` | `Supplies/` | Supply records |
| 15 | `15-Purchasing` | `Purchasing/` | Purchasing records |
| 16 | `16-EmployeeTraining` | `EmployeeTraining/` | Employee training (excluded from this task) |
| 17 | `17-DCOs` | `DCOs/` | DCO Log, Document Number Log, and all 90 completed DCO forms |
| 18 | `18-DMR` | `DMR/` | Device Master Record (BOMs, specs, labeling, manufacturing/QC procedures) |
| 19 | `19-Administration` | `Administration/` | Administrative documents (AD.SLQ001) |

---

## Constraints

- Do NOT modify any source `.docx`, `.pdf`, or application code files
- Do NOT fabricate log data — if a log cannot be found, say so
- Do NOT create DCOs for historical FileHold documents (SW.SLQ001–006) unless explicitly confirmed missing from the DCO Log
- Do NOT include employee training documents or training-related DCO entries
- Output all DCO drafts as markdown in your response (the user will transfer them to Word/PDF for signing)
- Use the QM.SLQ001 Appendix 1 approval group table to determine correct approval groups — do not guess
