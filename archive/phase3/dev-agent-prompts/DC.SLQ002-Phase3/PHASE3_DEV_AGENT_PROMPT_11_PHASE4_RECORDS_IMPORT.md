# Phase 3 — Prompt 11: Phase 4 Records Import

## Context and state

- Production cleanup is complete (test users, test docs, FileHold folders all removed).
- S3 Spaces key `[REDACTED_SPACES_KEY]` is confirmed working as of 2026-07-09.
- `bulk_import_admin_docs.py` is the approved import tool, but it is **non-recursive**.
  This is the main blocker. Fix it first, then execute the full records import.
- Reference docs:
  - `docs/DC.SLQ002-Phase3/PHASE4_RECORDS_MAPPING.md` — source → library mapping
  - `docs/DC.SLQ002-Phase3/PHASE4_DRY_RUN_REPORT.md` — file counts and dry-run output

---

## Task A — Add `--recursive` flag to `bulk_import_admin_docs.py`

Enhance the importer with a new `--recursive` boolean flag. When set, the script:

1. Walks the source `--directory` recursively.
2. For each subdirectory found (depth-first), mirrors the relative path as a subfolder
   hierarchy inside the target library, creating parent folders as needed
   (`service.create_folder` with `parent_id`).
3. Imports only the direct files of each directory into the corresponding target folder
   (same `select_new_files()` skip logic, same idempotency).
4. Respects `--dry-run` at every level.

Example of expected behavior:

```
python scripts/bulk_import_admin_docs.py \
  --library employee_training \
  --folder "Employee Training" \
  --directory EmployeeTraining \
  --recursive \
  --dry-run
```

Expected output sketch:

```
[DRY RUN] Would create folder: employee_training / Employee Training / BrianMcVerry
  [DRY RUN] Would upload: ...
[DRY RUN] Would create folder: employee_training / Employee Training / ChrisTurner
  ...
[DRY RUN] Total: 193 files across N folders
```

Update `tests/test_bulk_import.py` (or add `tests/test_bulk_import_recursive.py`) with at
least one test that creates a two-level directory tree, runs the recursive importer, and
asserts the correct folder hierarchy and file assignments in the DB (no S3 call needed —
use the local storage fixture).

Deploy this change before running any real imports. Confirm single migration head
(no schema change needed — the folder model already supports nesting via `parent_id`).

---

## Task B — Execute the records import to production

Use the S3 credentials in the environment (same ones used for Track A). Run in two passes
per source: dry-run first (pipe to a report), then live. All sources should be idempotent
so re-runs are safe.

**S3 credentials to use** (set as environment variables before running):

```
DATABASE_URL  = "postgresql://[REDACTED_USER]:[REDACTED_PASSWORD]@app-a369a03f-8c1d-4001-b47c-7a55b0e1c88c-do-user-29847674-0.g.db.ondigitalocean.com:25060/defaultdb?sslmode=require"
STORAGE_BACKEND       = s3
S3_ENDPOINT           = sfo3.digitaloceanspaces.com
S3_REGION             = sfo3
S3_BUCKET             = raoeqms-files
S3_ACCESS_KEY_ID      = [REDACTED_SPACES_KEY]
S3_SECRET_ACCESS_KEY  = [REDACTED_SPACES_SECRET]
```

Write a single shell script `scripts/_phase4_import.ps1` (PowerShell) that sets the
environment variables and runs each import command in order. Include the `--dry-run` version
commented out above each live run so any future re-run can be easily tested first.

### Import commands (use --recursive for all nested sources)

Run in this order (flat/simple first, large/overlap-sensitive last):

**Group 1 — flat folders (no subfolders; no --recursive needed)**

```
bulk_import_admin_docs.py --library risk_management  --folder "Risk Management"    --directory "RiskManagement"
bulk_import_admin_docs.py --library ncrs             --folder "NCRs"               --directory "NCMR"
bulk_import_admin_docs.py --library dhfs             --folder "SLQ-DHF"            --directory "SLQ-DHF"
```

**Group 2 — nested sources (require --recursive)**

```
bulk_import_admin_docs.py --library dhfs                    --folder "DHF"                               --directory "DHF"                          --recursive
bulk_import_admin_docs.py --library capas                   --folder "CAPAs"                             --directory "CAPAs"                        --recursive
bulk_import_admin_docs.py --library management_reviews      --folder "Internal Audits"                   --directory "Audits"                       --recursive
bulk_import_admin_docs.py --library management_reviews      --folder "Management Review Meetings"        --directory "ManagementReviewMeetings"      --recursive
bulk_import_admin_docs.py --library post_market_surveillance --folder "Post-Market Surveillance"         --directory "PostMarketSurviellance"        --recursive
bulk_import_admin_docs.py --library employee_training       --folder "Employee Training"                 --directory "EmployeeTraining"             --recursive
bulk_import_admin_docs.py --library work_orders             --folder "Work Orders"                       --directory "Manufacturing"                --recursive
bulk_import_admin_docs.py --library regulatory_standards    --folder "Regulatory Standards"              --directory "RegulatoryStandards&Approvals" --recursive
```

**Group 3 — triage resolved (coordinator decisions)**

```
# Administration forms → forms_templates_travelers
bulk_import_admin_docs.py --library forms_templates_travelers --folder "Administration Forms"  --directory "Administration"  --recursive

# FDA Registration Information → fold into regulatory_standards/FDARegistration
bulk_import_admin_docs.py --library regulatory_standards --folder "Regulatory Standards/FDARegistration" --directory "FDA Registration Information" --recursive

# DMR → qms_documents under Device Master Record subfolder (no dedicated module yet)
bulk_import_admin_docs.py --library qms_documents --folder "Device Master Record" --directory "DMR" --recursive

# QMSInProcess CAPAs (CAPA001–CAPA004)
bulk_import_admin_docs.py --library capas --folder "CAPAs/CAPA001" --directory "QMSInProcess/CAPA001" --recursive
bulk_import_admin_docs.py --library capas --folder "CAPAs/CAPA002" --directory "QMSInProcess/CAPA002" --recursive
bulk_import_admin_docs.py --library capas --folder "CAPAs/CAPA003" --directory "QMSInProcess/CAPA003" --recursive
bulk_import_admin_docs.py --library capas --folder "CAPAs/CAPA004" --directory "QMSInProcess/CAPA004" --recursive

# QMSInProcess Quality Planning
bulk_import_admin_docs.py --library qms_documents --folder "Quality Planning" --directory "QMSInProcess/Quality Planning Documents" --recursive

# QMSInProcess Lot record
bulk_import_admin_docs.py --library work_orders --folder "Lot Records" --directory "QMSInProcess/Lot SLQ-05132026" --recursive

# QMSInProcess project archives (DC.SLQ001, DC.SLQ002 working folders)
bulk_import_admin_docs.py --library qms_documents --folder "Project Archives/DC.SLQ001" --directory "QMSInProcess/DC.SLQ001" --recursive
bulk_import_admin_docs.py --library qms_documents --folder "Project Archives/DC.SLQ002" --directory "QMSInProcess/DC.SLQ002" --recursive
```

**Group 4 — DCOs (large, run last)**

```
# Completed DCOs and prior revisions
bulk_import_admin_docs.py --library qms_documents --folder "DCO Log and Change Orders/Completed DCOs"     --directory "DCOs/CompletedDCOs"     --recursive
bulk_import_admin_docs.py --library qms_documents --folder "DCO Log and Change Orders/Previous Revisions" --directory "DCOs/Previous Revisions" --recursive

# In-process DCOs from QMSInProcess (DCO087–DCO095)
# Import each in-process DCO subfolder individually to keep them organized
# (QMSInProcess/DCO087 → qms_documents/DCO Log and Change Orders/In Process/DCO087, etc.)
for dco in DCO087 DCO088 DCO089 DCO090 DCO091 DCO092 DCO093 DCO094 DCO095:
    bulk_import_admin_docs.py --library qms_documents --folder "DCO Log and Change Orders/In Process/$dco" --directory "QMSInProcess/$dco" --recursive
```

**Skip entirely (not records):**
- `DesignSOPDocExamples/` — example/template reference docs, not a QMS record. Skip.
- `Report/` — empty.
- `Equipment/`, `Suppliers/`, `Purchasing/`, `Supplies/`, `Distribution/` — deferred to Phase 5.

### After running all imports

Report the total file count per library (a quick query: `SELECT library_key, COUNT(*) FROM admin_doc_files GROUP BY library_key`) and paste it in the reply.

---

## Task C — Deploy discipline

Task A is a code change (importer enhancement + tests). Commit and push, confirm
DO deploy green, then proceed to Task B (the import run). Task B is production data only
— no further git commit needed.

Continue following single-migration-head and import-guard rules for Task A.

---

## Deliverables

1. `scripts/bulk_import_admin_docs.py` — updated with `--recursive` flag.
2. Test for `--recursive` behavior (creates correct folder hierarchy, assigns files).
3. `scripts/_phase4_import.ps1` — the full sequenced import script.
4. DO deploy confirmation for Task A.
5. Task B: per-library file count query result from production.
