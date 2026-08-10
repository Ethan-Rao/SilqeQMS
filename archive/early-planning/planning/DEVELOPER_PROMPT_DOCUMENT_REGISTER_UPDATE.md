# Developer Prompt: Update QMS Readable Texts and Document Register

**Date:** 2026-03-31

---

## Objective

Review all document source folders in this project, extract readable markdown versions for any new or updated files, and update the master document register (`QM_DOCUMENT_REGISTER.csv`) to reflect the current state of all controlled documents. **Omit anything related to employee training.**

---

## Context

This project is a medical device QMS (Quality Management System) for SILQ. The project contains:

1. **Source document folders** — contain the original `.docx`, `.pdf`, `.xlsx` files organized by QMS subsystem
2. **`docs/QMS-Readable-Texts/`** — contains extracted markdown versions of source documents for agent readability
3. **`QM_DOCUMENT_REGISTER.csv`** — a master register of all controlled documents with their IDs, revisions, titles, and ISO 13485 clause mappings

Recent activity has added new documents to the DHF/Software folder (software validation and transition plan documents) and potentially updated others. The readable texts and register have not been updated to reflect these changes.

---

## Task 1: Update QMS Readable Texts

### 1A. Scan for new or updated files in DHF/Software

Compare the contents of `DHF/Software/` against `docs/QMS-Readable-Texts/12-DHF-Software/`. Extract readable markdown versions for any files in the source that do not yet have a corresponding `.md` in the readable texts folder.

**Known new files (at minimum):**
- `FM1-QM.SLQ004 A Design Project Scope Form DC.SLQ002.docx`
- `Executed Design Project Scope Form DC.SLQ002 BM_CT signed.pdf`

**Known files that may need re-extraction** (source revision newer than readable text):
- Check if any SW.SLQ007–009 or DC.SLQ002 have been modified since their last extraction. If the source `.docx` modification date is newer than the `.md` file, re-extract.

### 1B. Scan for revision mismatches in QM Documents folder

Compare source files in `QM Documents/` against `docs/QMS-Readable-Texts/01-QM-Documents/`. Specifically check:
- `QM.SLQ004 B Design Control Program SOP.docx` — the readable text currently shows Rev A. If source is Rev B, re-extract.
- `QM.SLQ034 G Organization Chart.docx` — check if the readable text matches Rev G.
- `QM.SLQ022` — source folder contains both Rev A and Rev B. Ensure the latest revision (B) is in readable texts.

For any document where the source revision is newer than the readable text, re-extract.

### 1C. Scan Forms, Templates, and Travelers

Compare `Forms, Templates, and Travelers/` against `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/`. Extract any new or updated forms/templates not yet represented.

### 1D. Extraction method

Use the existing extraction script pattern from `scripts/extract_all_qms_to_md.py`. The Python virtual environment is at `.venv/` and has `python-docx`, `pdfplumber`, and `openpyxl` installed.

For `.docx` files:
```python
import docx
doc = docx.Document(filepath)
# Extract paragraphs and tables
```

For `.pdf` files:
```python
import pdfplumber
with pdfplumber.open(filepath) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
```

For `.xlsx` files:
```python
import openpyxl
wb = openpyxl.load_workbook(filepath)
```

**Important notes on file access:**
- Some files may be locked if open in Word. If you get a `PackageNotFoundError` or `PermissionError`, note the file as "locked — skip" and move on.
- Some filenames contain special characters (e.g., `^J` which is a newline character). Use `os.listdir()` with pattern matching to find the actual filename rather than constructing the path from the display name.
- Output markdown files go in the appropriate `docs/QMS-Readable-Texts/` subfolder with the same base name as the source file but with `.md` extension.

### 1E. Scope exclusion

**Do NOT extract or process any files from the `EmployeeTraining/` folder or `docs/QMS-Readable-Texts/16-EmployeeTraining/`.** Skip all employee training records entirely.

---

## Task 2: Update the Document Register

### 2A. Current register structure

The register is at `QM_DOCUMENT_REGISTER.csv` with this format:

```
#,Document ID,Rev,Title,ISO 13485 Clause(s)
1,QM.SLQ001,A,Document Control SOP,"4.2, 7.3"
```

It currently contains:
- Rows 1–46: QM-series SOPs and policies (QM.SLQ001 through QM.SLQ051)
- Rows 47–61: QMS Subsystem Folder entries (02-Forms-Templates-Travelers through 16-EmployeeTraining)

### 2B. Add new document series

Add the following document series to the register, continuing the row numbering after the existing QM documents (after row 46) but BEFORE the subsystem folder section. Insert a blank separator line and a section header row before each new series.

**SW series — Software documents (DHF/Software):**

| Document ID | Rev | Title | ISO 13485 Clause(s) |
|---|---|---|---|
| SW.SLQ001 | A | Software Validation Plan, FileHold | 4.1.6, 7.3 |
| SW.SLQ002 | A | Product Requirements Specification, FileHold | 4.1.6, 7.3 |
| SW.SLQ003 | A | Software Verification Test Plan, FileHold | 4.1.6, 7.3 |
| SW.SLQ004 | A | Software Verification Test Procedure, FileHold | 4.1.6, 7.3 |
| SW.SLQ005 | A | Software Validation Report, FileHold | 4.1.6, 7.3 |
| SW.SLQ006 | A | Requirements Traceability Matrix, FileHold | 4.1.6, 7.3 |
| SW.SLQ007 | A | Software Validation Plan, SilqQMS | 4.1.6, 7.3 |
| SW.SLQ008 | A | Product Requirements Specification, SilqQMS | 4.1.6, 7.3 |
| SW.SLQ009 | A | Software Verification Test Plan, SilqQMS | 4.1.6, 7.3 |

**DC series — Design Control documents (DHF/Software):**

| Document ID | Rev | Title | ISO 13485 Clause(s) |
|---|---|---|---|
| DC.SLQ002 | A | Design Project Plan, SilqQMS EDMS Transition | 7.3 |

**VV series — Verification/Validation documents (DHF root):**

Scan all `VV.SLQ*` files in the `DHF/` root folder. For each unique document number (ignoring attachments), add a register entry. The VV documents cover ISO 13485 clause 7.3 (Design and development) and 7.6 (Control of monitoring and measuring equipment) for IQ protocols/reports.

Use the document filename to determine the Document ID, Rev, and Title. For example:
- `VV.SLQ001 A Test Report, In-Vitro Bacterial Adhesion Comparative Study.docx` → ID: `VV.SLQ001`, Rev: `A`, Title: `Test Report, In-Vitro Bacterial Adhesion Comparative Study`
- Attachments (files with "Attachment" in the name) should NOT get their own register rows — they are part of their parent document.

### 2C. Fix revision discrepancies in existing QM entries

Compare the register's revision letters against the actual source files in `QM Documents/`. Fix any that are out of date. Known discrepancies to check:

| Register Entry | Register Rev | Source File Rev | Action |
|---|---|---|---|
| QM.SLQ004 | B | B | Verify match |
| QM.SLQ005 | C | B (source file) | Check — register may be ahead of source. Use the source file revision as truth. |
| QM.SLQ034 | F | G (source file) | Update register to G if source is G |
| QM.SLQ022 | B | A and B both in source | Confirm B is correct (latest) |

For any other discrepancy found, update the register to match the actual source file revision.

### 2D. Add FM/TMP controlled forms and templates

Scan `Forms, Templates, and Travelers/Forms/` and `Forms, Templates, and Travelers/Templates/` and add entries for each controlled form and template. Use the following format:

- Document ID: As shown in the filename (e.g., `FM1-QM.SLQ001`, `TMP1-QM.SLQ005`)
- Rev: From the filename
- Title: From the filename (e.g., `Document Change Order Form`, `Design Project Plan Template`)
- ISO 13485 Clause(s): Use the same clause(s) as the parent QM document. For example, FM1-QM.SLQ001 inherits QM.SLQ001's clauses.

**Also add** the executed scope form from DHF/Software:
- `FM1-QM.SLQ004 A Design Project Scope Form DC.SLQ002` — this is a specific executed instance of FM1-QM.SLQ004 for the DC.SLQ002 project.

Group these after the SW/DC/VV series and before the subsystem folders section.

### 2E. Exclusions

- **Do NOT add any employee training forms** (FM1-QM.SLQ003, FM2-QM.SLQ003, or any training records)
- **Do NOT add** the `Travelers/` documents (these are manufacturing travelers, not relevant here)
- **Do NOT add** the `SilqQMSTransitionPlanV1.docx` — this was a draft that has been superseded by DC.SLQ002

### 2F. Register formatting

- Maintain the existing CSV format with double-quoted values that contain commas
- Keep the sequential `#` column continuous (renumber if needed when inserting new sections)
- Use blank rows and section header rows (like the existing "QMS Subsystem Folders" header) to visually separate document series:
  - QM series (existing)
  - SW series (new)
  - DC series (new)
  - VV series (new)
  - FM/TMP series (new)
  - QMS Subsystem Folders (existing, moved to end)

---

## Task 3: Summary Report

After completing Tasks 1 and 2, provide a summary that includes:

1. **Files extracted** — list each new or re-extracted markdown file
2. **Files skipped** — list any files that could not be extracted (locked, unsupported format, etc.)
3. **Register changes** — list all rows added and any revision corrections made
4. **Discrepancies found** — note any issues discovered (e.g., source file revision doesn't match register, missing documents, duplicate files)

---

## File Locations Reference

| Source Folder | Readable Texts Folder | Contents |
|---|---|---|
| `QM Documents/` | `docs/QMS-Readable-Texts/01-QM-Documents/` | QM-series SOPs and policies |
| `Forms, Templates, and Travelers/` | `docs/QMS-Readable-Texts/02-Forms-Templates-Travelers/` | Controlled forms, templates, travelers |
| `DHF/` (root, VV files) | `docs/QMS-Readable-Texts/05-DHF/` | Design V&V documents |
| `DHF/Software/` | `docs/QMS-Readable-Texts/12-DHF-Software/` | Software validation and transition documents |
| `QM_DOCUMENT_REGISTER.csv` | (project root) | Master document register |

---

## Constraints

- Use the Python virtual environment at `.venv/` for all extraction
- Do not modify any source `.docx`, `.pdf`, or `.xlsx` files — only create/update `.md` files in readable texts
- Do not add, remove, or modify any application source code
- If a file is locked (PermissionError), skip it and note it in the summary
- Omit all employee training content
