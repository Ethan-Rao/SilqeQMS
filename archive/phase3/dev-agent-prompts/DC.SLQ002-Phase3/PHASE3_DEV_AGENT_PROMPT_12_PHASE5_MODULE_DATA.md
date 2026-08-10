# Phase 3 — Prompt 12: Phase 5 Module Data Population (Equipment, Suppliers, Purchasing)

## Context and state

The Equipment, Suppliers, and Purchasing modules have comprehensive data models and full
UI (list, detail, edit, document upload, cross-links) already deployed. Production state
as of 2026-07-09:

- **Equipment**: 17 records seeded from `Silq Equipment Master List.xlsx` (coordinator ran
  `import_equipment_master()` directly). No document attachments yet.
- **Suppliers**: 0 records. No xlsx-format approved supplier list exists — only a PDF
  (`Suppliers/SILQ Approved Supplier List 13 Mar 2026.pdf`). Records must be created from
  the folder structure (`Suppliers/<CompanyName>/` → one record per company).
- **Purchasing**: 0 POs in the database. `Purchasing/` folder has ~150 files. PO log may
  be importable if a structured xlsx exists there.

Source folders at workspace root (confirmed file counts from Phase 4 scan):
- `Equipment/` — 126 files in `ST-001/` through `ST-017/` subfolders (plus xlsx)
- `Suppliers/` — 101 files in per-company subfolders (BioMDg, ColePalmer, Culligan, etc.)
- `Purchasing/` — ~150 files (inspect and report structure before loading)
- `Supplies/` — 18 files

---

## Task A — Equipment file attachment import

Write `scripts/_import_equipment_files.py` (same prod-credential pattern as previous
one-off scripts; uncommitted/gitignored). The script:

1. Walks `Equipment/ST-XXX/` subfolders recursively.
2. For each subdirectory, extracts the equipment code from the folder name (regex
   `r"(ST-\d+)"` on the top-level subfolder).
3. Looks up the equipment record by `equip_code` (e.g. `ST-001`).
4. For each file in the subfolder (and nested sub-subfolders), classify it into a
   `ManagedDocument.category` using filename heuristics:

   | Filename pattern | Category | `document_type` |
   |---|---|---|
   | `Equipment Requirements Form*` | `requirements_form` | `Requirements Form` |
   | `Equipment Service Log*` | `calibration` | `Service Log` |
   | `SP-E.*` or `SP-ST-*` (specifications) | `spec_document` | `Specification` |
   | `*Calibration*` or `*CAL*` or `*CoC*` | `calibration` | `Calibration Certificate` |
   | `*Manual*` or `*Datasheet*` | `manual` | `Manual` |
   | `*Qualification*` | `qualification` | `Qualification` |
   | All others | `general` | `General` |

5. Skip unsupported extensions (`.dymo`, `.msg`). Skip files already present on the record
   (match by `original_filename` + `equipment_id`; use `sha256` from `file_digest_and_bytes`
   for dedup if the service has it, otherwise filename-based is fine).
6. Use `upload_equipment_document()` from `app.eqms.modules.equipment.service` for each file.
7. Include a `DRY_RUN = True` guard at the top. Print counts by equipment code.
8. `is_primary = True` for the first Requirements Form and first Specification per
   equipment (clear any existing primary flag first, same as the existing UI route does).

Run with `DRY_RUN = True`, paste the output (file counts per equipment code) for coordinator
review, then set `DRY_RUN = False` and run live.

---

## Task B — Supplier record creation + file attachment

Write `scripts/_import_supplier_files.py`:

**B1 — Create supplier records from folder structure**

The `Suppliers/` folder is organized as `<CompanyName>/` (one subfolder per supplier).
Create one `Supplier` record per top-level subfolder if it doesn't already exist. Map
folder names to clean company names (strip common suffixes, preserve case). Initial status:
`Approved` for all (the fact they have a folder in the ASL implies they are approved).
Use `create_supplier()` from `app.eqms.modules.suppliers.service`.

Known folder names and suggested `name` mapping (update if the actual folder differs):

| Folder | Company name | Category |
|---|---|---|
| `BioMDg` | BioMDg | Contract Manufacturer |
| `ColePalmer` | Cole-Palmer | Component Supplier |
| `Culligan` | Culligan | Service Provider |
| `DevineGuidance` | Devine Guidance | Consulting Service |
| `FGL Environmental` | FGL Environmental | Testing/Calibration Lab |
| `FireFlySci` | FireFlySci | Component Supplier |
| `FisherScientific` | Fisher Scientific (Thermo Fisher) | Component Supplier |
| `GlacierTanks` | Glacier Tanks | Component Supplier |
| `IndependentAirGroups` | Independent Air Groups | Service Provider |
| `McMasterCarr` | McMaster-Carr | Component Supplier |
| `MedReg` | MedReg Associates | Consulting Service |
| `MicroPrecision` | Micro-Precision Calibration | Testing/Calibration Lab |
| `Ningbo` | Ningbo (catheter supplier) | Component Supplier |
| `Pathway` | Pathway Medical | Contract Manufacturer |
| `Raglen` | Raglen | Component Supplier |
| `Repligen` | Repligen | Component Supplier |
| `RichmanChemical` | Richman Chemical | Chemical Supplier |
| `Steripax` | Steripax | Contract Manufacturer |
| `SupplierAssesmentSchedules` | *(skip — not a supplier, schedules only)* | — |
| `TokyoChemicalIndustry` | Tokyo Chemical Industry (TCI) | Chemical Supplier |
| `ULine` | Uline | Component Supplier |
| `UnitedStatesPlasticCorp` | United States Plastic Corp | Component Supplier |
| `VWR` | VWR International | Component Supplier |

**B2 — Attach files to supplier records**

For each file in a supplier's folder (and nested sub-subfolders), attach via
`upload_supplier_document()`. Classify by filename heuristics:

| Filename pattern | `document_type` |
|---|---|
| `*ISO*` or `*Certificate*` or `*Cert*` | ISO Certificate |
| `*Supplier Assessment*` or `*SQ SA*` | Supplier Assessment |
| `*ReEvaluation*` or `*Re-Evaluation*` | Re-Evaluation |
| `*Quality Manual*` or `*Business System*` | Quality Manual |
| `*Quality Agreement*` or `*QA-SLQ*` | Quality Agreement |
| `*Audit*` (but not assessment) | Audit Report |
| All others | General |

Idempotency: skip if `original_filename` + `supplier_id` already present.

Include `DRY_RUN = True` guard. Dry-run output: file counts per supplier.

---

## Task C — Purchasing folder inspection and import decision

Before writing a PO import script:

1. Print a recursive file listing of `Purchasing/` (first 30 items) and count by extension.
2. Check if there is a structured xlsx PO log in `Purchasing/` — if yes, inspect its
   headers and report whether `import_from_csv_xlsx()` or the existing
   `purchasing/admin.py` import route can handle it directly.
3. Report the finding so the coordinator can decide how to proceed. Do NOT write a PO
   import script yet — just the inspection report.

---

## Task D — Deploy / run discipline

Tasks A and B are one-off production data scripts (same as cleanup and equipment master
scripts). No code change, no git commit, no deploy needed. Write the scripts, dry-run
locally (they can run against local SQLite for format validation), then the coordinator
runs against prod.

If anything requires a code change (e.g., `upload_equipment_document` signature differs
from what you expect), fix the code, commit, and note the change. Otherwise stay in
script-only mode.

---

## Deliverables

1. `scripts/_import_equipment_files.py` — dry-run output (file counts per ST-XXX).
2. `scripts/_import_supplier_files.py` — dry-run output (file counts per supplier).
3. Task C inspection report (Purchasing folder structure + xlsx header if found).
4. Coordinator runs both scripts live. No deploy required for Tasks A–C.
