# Phase 4 — Records Import Dry-Run Report

Prepared for coordinator review before Prompt 11 (actual import). **Nothing was
imported.** File counts are a recursive filesystem scan of the workspace on
2026-07-09; representative `bulk_import_admin_docs.py --dry-run` runs were
executed against a throwaway local SQLite (offline) to capture genuine tool
behavior.

---

## ⚠️ Key finding — the importer is non-recursive (blocks a naive bulk load)

`scripts/bulk_import_admin_docs.py` imports only the **direct files** of the
`--directory` into a **single** `--folder`. It does **not** descend into
subfolders. Proof (real dry-run output):

```
=== Audits (nested) ===
Found 2 files to import into management_reviews/Internal Audits
  [DRY RUN] Would upload: Silq Audit Log.xlsx (47.3 KB)
  [DRY RUN] Would upload: Silq Technologies Corp EIR_reviewed FDA insp rep 11.17.25.pdf (1398.4 KB)
[DRY RUN] Total: 2 files
```

`Audits/` actually contains **62** supported files — the other 60 live inside
`IA2022/`, `IA2023/`, `IA2024/`, `IA2025/`, `FDA2025/`, and `SupplierAudits/`
and are invisible to a single top-level run.

**Action for Prompt 11 (pick one):**
- **(a)** Run the importer once per leaf subfolder, mapping each to a target
  subfolder (more invocations, no code change), **or**
- **(b)** Add a `--recursive` option to `bulk_import_admin_docs.py` that walks
  subfolders and recreates the folder tree under the target library (one run
  per source root). Recommended for the folders with many subfolders
  (`EmployeeTraining`, `Audits`, `DCOs`, `Equipment`-style trees).

Idempotency/dry-run themselves are solid: `select_new_files()` skips
already-present filenames (by `secure_filename`) and unsupported extensions, and
`--dry-run` performs no writes. Re-runs are safe.

---

## Verified importer behavior on flat folders (real dry-run output)

**`RiskManagement/` → `risk_management`** — flat, imports cleanly:

```
Found 11 files to import into risk_management/Risk Management
  [DRY RUN] Would upload: PS-0006 Rev H_signed.pdf (1090.0 KB)
  ... (11 total: RM-0018..RM-0155, PS-0006) ...
[DRY RUN] Total: 11 files
```

**`SLQ-DHF/` → `dhfs`** — flat, imports cleanly:

```
Found 20 files to import into dhfs/SLQ-DHF
  [DRY RUN] Would upload: DHF File Index.pdf (51.2 KB)
  ... (20 total: Project#00017/00047/00049/00053/00056 design reviews, TR-SLQ-0015) ...
[DRY RUN] Total: 20 files
```

---

## Per-source file inventory (recursive scan; supported types only)

| Source folder | Target library | Supported files | By type | Immediate subfolders |
|---|---|---|---|---|
| `CAPAs/` | `capas` | 11 | docx 3, pdf 7, xlsx 1 | CAPA 001-2025, CAPA 002-2025 |
| `Audits/` | `management_reviews` | 62 | doc 1, docx 3, pdf 57, xlsx 1 | FDA2025, IA2022, IA2023, IA2024, IA2025, SupplierAudits |
| `ManagementReviewMeetings/` | `management_reviews` | 9 | docx 1, pdf 5, pptx 3 | MR2022, MR2023, MR2024, MR2025 |
| `NCMR/` | `ncrs` | 1 | pdf 1 | (none) |
| `PostMarketSurviellance/` | `post_market_surveillance` | 45 | pdf 44, xlsx 1 | ProductComplaints, STC001, eMDRs |
| `RiskManagement/` | `risk_management` | 11 | docx 6, pdf 5 | (none) |
| `DHF/` | `dhfs` | 80 | docx 43, pdf 35, xlsx 2 | Software |
| `SLQ-DHF/` | `dhfs` | 20 | pdf 20 | (none) |
| `EmployeeTraining/` | `employee_training` | 193 | pdf 192, xlsx 1 | 9 (per person + JobDescriptions) |
| `Manufacturing/` | `work_orders` | 111 | docx 21, pdf 87, pptx 1, xlsx 2 | C.SLQ001, ClearTract Foley Catheters |
| `RegulatoryStandards&Approvals/` | `regulatory_standards` | 39 | docx 1, pdf 37, xlsx 1 | 510(K)s, ASTM, FDARegistration, ISO, MAF |
| `DCOs/` | `qms_documents` | 223 | docx 168, pdf 52, xlsx 3 | CompletedDCOs, Previous Revisions |
| `QMSInProcess/` | `capas` + `qms_documents` | 176 | docx 133, pdf 42, xlsx 1 | CAPA001-004, DCO087-095, DC.SLQ001/002, Quality Planning Documents, Lot SLQ-05132026 |

**Total supported files across mapped sources: ~981** (excludes module-owned
folders below). Unsupported types encountered and skipped by the importer:
`.html`, `.xml`, `.msg`, `.zip`, `.dymo`.

### Deferred to Phase 5 (module tables — not imported here)
`Equipment/` 126 · `Suppliers/` 101 · `Purchasing/` 150 · `Supplies/` 18 ·
`Distribution/` 35.

### Needs manual triage before load
`Administration/` 6 · `DMR/` 44 · `FDA Registration Information/` 4 ·
`DesignSOPDocExamples/` 7 · `Report/` 0 · plus `QMSInProcess/DC.SLQ001`,
`DC.SLQ002`, `Quality Planning Documents`, `Lot SLQ-05132026`. See
`PHASE4_RECORDS_MAPPING.md`.

---

## B3 — S3 / Spaces connectivity

**Not verified from this environment.** No `.env` and no prod Spaces
credentials are present in the sandbox (the `S3_*` env vars are unset and there
is no committed `_run_prod_import.py`), so the ping

```python
s3.put_object(Bucket=..., Key="_phase4_ping", Body=b"ping")
s3.delete_object(Bucket=..., Key="_phase4_ping")
```

could not be executed here. Per the Track-A follow-up recommendation, the keys
may have been revoked.

**Action:** the coordinator/Ethan should confirm (or issue fresh) Spaces
credentials and run the ping from a machine with prod access before Prompt 11.
The storage abstraction is ready (`storage_from_config(app.config)` →
`S3Storage`); it just needs valid `S3_ENDPOINT / S3_REGION / S3_BUCKET /
S3_ACCESS_KEY_ID / S3_SECRET_ACCESS_KEY`.

---

## Recommendation

Do **not** proceed to a bulk import until:
1. The non-recursive importer gap is resolved (option (a) per-subfolder runs, or
   (b) add `--recursive`). **(b) is recommended** given the subfolder counts.
2. The "Needs manual triage" folders are dispositioned with Ethan.
3. Spaces credentials are confirmed working via the ping.
