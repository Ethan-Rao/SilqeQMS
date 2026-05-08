# Editing Guide: SW.SLQ012 A Requirements Traceability Matrix, SilqQMS

Document: SW.SLQ012 A Requirements Traceability Matrix, SilqQMS  
Project: DC.SLQ002 -- SilqQMS EDMS Transition  
Structural model: SW.SLQ006 A Requirements Traceability Matrix, FileHold  
Output location: `QMSInProcess/DC.SLQ002/`  
Readable-text reference (SRS and test-case definitions):  
`docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ008 A Product Requirements Specification, SilqQMS.md`  
`docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ009 A Software Verification Test Plan, SIlqQMS.md`  
`docs/QMS-Readable-Texts/12-DHF-Software/SW.SLQ010 A Software Verification Test Procedure, SilqQMS.md`

## How to use this guide

SW.SLQ012 is the **design-input → design-output → verification** map for SilqQMS. It must account for **every** software requirement **SRS-1.1** through **SRS-8.3** in SW.SLQ008 A. Use **SW.SLQ006 A** (FileHold) as the **table layout** model: front matter sections (Purpose, Scope, Reference Documents, Definitions) in the same plain-text style as FileHold, then a single **I/O Matrix** table.

SW.SLQ011 A explicitly points readers here for detailed requirement-to-test-case traceability; do **not** duplicate the full matrix inside SW.SLQ011.

Assume **SW.SLQ010 A** has been **executed and closed with all eleven test cases passing**, unless you are documenting a real deviation.

---

## Section order (match SW.SLQ006)

1. Title block / cover page  
2. Purpose  
3. Scope  
4. Reference Documents  
5. Definitions (abbreviations + short SilqQMS / verification definitions)  
6. Input / Output Matrix (single Word table)  
7. Revision / approval blocks per QM.SLQ001  

Do **not** add attachments inside SW.SLQ012; the **executed** SW.SLQ010 and **SW.SLQ011** are the verification records cross-referenced in the matrix.

---

## Title block / cover page

Align with other DC.SLQ002 SW deliverables:

- Title: **Requirements Traceability Matrix, SilqQMS**  
- Document ID: **SW.SLQ012**  
- Revision: **A**  
- Project: **DC.SLQ002 -- SilqQMS EDMS Transition**  

Author, reviewer, and approver signature blocks per **QM.SLQ001 A**.

---

## Purpose

Paste verbatim (adapt only if your controlled template mandates different wording):

The purpose of this document is to provide a link between verifiable product requirements (design inputs), the implemented software (design output), and the verification methods used to demonstrate that each design input is satisfied.

---

## Scope

Paste verbatim:

The scope of this document incorporates all product requirements (design inputs), design output, and verification testing related to the validation of the electronic document management system **SilqQMS** under **DC.SLQ002** and **SW.SLQ007 A**.

---

## Reference Documents

List in this order, one designation per line (tab or monospace alignment is optional):

SW.SLQ007 A   Software Validation Plan, SilqQMS  
SW.SLQ008 A   Product Requirements Specification, SilqQMS  
SW.SLQ009 A   Software Verification Test Plan, SilqQMS  
SW.SLQ010 A   Software Verification Test Procedure, SilqQMS (executed)  
SW.SLQ011 A   Software Validation Report, SilqQMS  
QM.SLQ032 A   Software Validation SOP  
QM.SLQ001 A   Document Control SOP  

If SW.SLQ011 is not yet approved when SW.SLQ012 is signed, mark SW.SLQ011 “pending approval” in the matrix’s Validation column only where you would otherwise cite it—for example, use “Test report: SW.SLQ011 (pending)” until the report is released, then update on the next revision.

---

## Definitions

Mirror SW.SLQ006 structure (short subsections):

**Abbreviations / Acronyms**

- I/O: Input/Output  
- SRS: Software (Product) Requirement Specification requirement identifier in SW.SLQ008  
- DHF: Design History File  

**General definitions**

- **SilqQMS:** Custom web application used as SILQ’s electronic document management system for controlled QMS documents and records (Document Control module, Admin Docs Libraries, authentication, roles, audit trail, storage).  
- **Verification:** Confirmation, by examination and objective evidence, that specified requirements have been fulfilled by the product design.  
- **Validation (context):** Overall conclusion documented in SW.SLQ011; this matrix supports validation by tracing each SRS to executed verification.  
- **Design output (for this matrix):** The deployed SilqQMS application build identified on the SW.SLQ010 cover page (Git commit SHA and/or release tag, deployment environment).

---

## Input / Output Matrix (the Word table)

### Column headers (match SW.SLQ006)

Use **exactly** these column headers, left to right:

| Column | Header text |
|--------|-------------|
| A | Item |
| B | Attribute / Characteristic |
| C | Verifiable Product Requirement (Design Input) |
| D | Design Output |
| E | Verification / Validation |
| F | Test Method |

### Row grain

Use **one row per SRS ID** from **SRS-1.1** through **SRS-8.3** (33 rows). This keeps traceability one-to-one with SW.SLQ008 and avoids ambiguous combined rows.

**Column A (Item):** Sequential integers 1–33 in SRS order (1 = SRS-1.1, …).

**Column B (Attribute / Characteristic):** A short grouping label for readability. Use the groupings below (repeat the same label for all SRS in that group):

- SRS-1.1–1.11 → `Document Control — Lifecycle and files`  
- SRS-2.1–2.5 → `Document Control — Obsolete safeguards`  
- SRS-3.1–3.8 → `Admin Docs Libraries`  
- SRS-4.1–4.5 → `Authentication and session security`  
- SRS-5.1–5.3 → `Access control (RBAC)`  
- SRS-6.1–6.6 → `Audit trail`  
- SRS-7.1–7.2 → `Security controls (CSRF and HTTP headers)`  
- SRS-8.1–8.3 → `Data integrity — no delete; obsolete retention`

**Column C (Design Input):** For each row, copy the **full requirement text** for that SRS from SW.SLQ008 A (Rev A), preceded by the SRS ID on its own clause—for example: `SRS-1.1: SilqQMS shall allow authorized users…` Do not paraphrase; controlled text must match the approved SRS.

**Column D (Design Output):** For every row, use the **same** implementation reference tied to the validated build—for example:

`SilqQMS software at Git commit [SHA] (release [tag if any]), deployed per SW.SLQ010 cover page; application codebase per DC.SLQ002.`

Replace brackets with values from the **executed SW.SLQ010**.

**Column E (Verification / Validation):** For each row, cite:

1. The **SilqQMS verification test case** from SW.SLQ009/SW.SLQ010 (Test Case 1–11) that covers that SRS (see mapping table below).  
2. Wording of the form: `Test procedure: SW.SLQ010 A, Test Case [N]` and, after execution, add `Steps [x-y] as recorded in executed SW.SLQ010` where the executed procedure lists step numbers. If step ranges differ after a procedure revision, follow the **as-executed** document, not this guide.  
3. Add: `Test report / validation summary: SW.SLQ011 A` (or “pending” until issued).

Where SW.SLQ009 lists **supplementary automated tests**, you may append a second clause in Column E, for example: `Supplementary automated evidence: pytest [node id] (see SW.SLQ009 Additional Info).` Do **not** state that pytest replaces manual execution.

**Column F (Test Method):** Use `Software test` for all rows. If you attach formal automated test output as supplementary evidence only, you may use `Software test (manual); supplementary automated test` for rows where SW.SLQ009 explicitly names a pytest node.

---

## SRS → SilqQMS test case mapping (for Column E)

Use this table when filling Column E. **Test Case numbers** match SW.SLQ010 (and the editing guide `SW_SLQ010_VERIFICATION_TEST_PROCEDURE_EDITING_GUIDE.md`).

| SRS IDs | SW.SLQ010 test case | Title (short) |
|---------|---------------------|---------------|
| SRS-1.1, SRS-1.2, SRS-1.3, SRS-1.4, SRS-1.8, SRS-1.10, SRS-1.11 | 1 | Document Creation and Lifecycle |
| SRS-1.5 | 2 | Document Obsoleting |
| SRS-1.6, SRS-1.7 | 3 | Document Download and View |
| SRS-1.9 | 4 | File Integrity (SHA-256 / metadata) |
| SRS-2.1, SRS-2.2, SRS-2.3, SRS-2.4, SRS-2.5 | 5 | Obsolete Document Safeguards |
| SRS-3.1, SRS-3.2, SRS-3.3, SRS-3.4, SRS-3.5, SRS-3.6, SRS-3.7, SRS-3.8 | 6 | Admin Docs Library Operations |
| SRS-4.1, SRS-4.2, SRS-4.3, SRS-4.4, SRS-4.5 | 7 | Authentication and Session Security |
| SRS-5.1, SRS-5.2, SRS-5.3 | 8 | Access Control |
| SRS-6.1, SRS-6.2, SRS-6.3, SRS-6.4, SRS-6.5, SRS-6.6 | 9 | Audit Trail |
| SRS-7.1, SRS-7.2 | 10 | Security Controls |
| SRS-8.1, SRS-8.2, SRS-8.3 | 11 | Data Integrity — No-Delete Verification |

**Coverage rule:** Every SRS from **SRS-1.1** through **SRS-8.3** appears in exactly one row and maps to **at least one** test case in Column E. There are no orphan SRS rows.

---

## Consistency checks before approval

1. **Count:** The matrix has **33** data rows (one per SRS in SW.SLQ008).  
2. **Text parity:** Column C text matches SW.SLQ008 Rev A for each SRS.  
3. **Build identity:** Column D matches the SW.SLQ010 cover page configuration item (commit SHA / tag / environment).  
4. **Executed procedure:** Column E references **executed** SW.SLQ010 (not a blank template).  
5. **Validation report:** Column E references SW.SLQ011 once released; SW.SLQ011’s Reference Documents list includes SW.SLQ012.  
6. **No forward gaps:** If a requirement is deferred or not implemented, do **not** mark PASS—either revise SW.SLQ008 first or record a formal deviation; SW.SLQ012 is not the document to waive requirements.

---

## Drafting reminders

- Prefer **one Word table** for the whole matrix; avoid splitting SRS groups into separate tables unless your template forces pagination (if split, repeat column headers on each page).  
- Keep narrative sections **plain text** like SW.SLQ006; the only large table is the I/O matrix.  
- Do not paste application source code into SW.SLQ012; design output is the **released software build**, described in Column D.  
- After SW.SLQ012 is approved and the docx is filed under `QMSInProcess/DC.SLQ002/`, add its filename to `FILE_MAP` in `scripts/refresh_dc_slq002_readable_texts.py` and run `python scripts/refresh_dc_slq002_readable_texts.py` so `docs/QMS-Readable-Texts/12-DHF-Software/` stays aligned (until then, the script may not list SW.SLQ012).  
- Release per **QM.SLQ001 A**: paper DCO approval, then upload the approved PDF into SilqQMS Document Control and release as Rev A.

---

## QM.SLQ032 A alignment

SW.SLQ012 supports **QM.SLQ032 A** by demonstrating traceability from each specified requirement (SW.SLQ008) through implementation (SilqQMS build) to executed verification (SW.SLQ010) and summarized validation (SW.SLQ011). This satisfies the expectation that validation evidence can be traced to design inputs without relying on informal knowledge.
