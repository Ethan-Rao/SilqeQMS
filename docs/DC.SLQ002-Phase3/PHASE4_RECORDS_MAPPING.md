# Phase 4 — Records → admin_docs Library Mapping

Source → target mapping for the records upload into the 11 `admin_docs`
libraries. **Refined against the actual workspace layout** (the folders on disk
differ from the layout assumed in Prompt 10 — records live at the **workspace
root**, not under `QMSInProcess/`, and `QMSInProcess/` holds per-CAPA and
per-DCO working folders). File counts are recursive and were captured by a
filesystem scan on 2026-07-09.

The 11 libraries (keys): `qms_documents`, `employee_training`,
`management_reviews`, `ncrs`, `capas`, `post_market_surveillance`,
`regulatory_standards`, `work_orders`, `risk_management`, `dhfs`,
`forms_templates_travelers`.

> **Critical importer note (see dry-run report):** `bulk_import_admin_docs.py`
> is **non-recursive** — it imports only the *direct* files of one directory
> into one target folder. Every source below that has subfolders must be
> imported **once per leaf subfolder** (mapping each subfolder to a target
> subfolder), or the importer must be enhanced to recurse. This is the main
> Prompt 11 action item.

---

## Confirmed mappings

| # | Source folder (workspace root) | Files (recursive) | Target library | Target subfolder(s) | Notes |
|---|---|---|---|---|---|
| 1 | `CAPAs/` | 11 | `capas` | one subfolder per CAPA (`CAPA 001-2025`, `CAPA 002-2025`) | Root also has 1 `.html` + 2 `.xml` (unsupported types — skipped). |
| 2 | `QMSInProcess/CAPA001/` … `CAPA004/` | (subset of QMSInProcess 176) | `capas` | `CAPA001`…`CAPA004` | In-process CAPAs; keep numbered per-CAPA subfolders. |
| 3 | `Audits/` | 62 | `management_reviews` | `Internal Audits/` with year subfolders `IA2022`–`IA2025`, plus `FDA2025`, `SupplierAudits` | Files live *inside* the year subfolders. |
| 4 | `ManagementReviewMeetings/` | 9 | `management_reviews` | `Management Review Meetings/` with `MR2022`–`MR2025` | 3 `.pptx` + 5 `.pdf` + 1 `.docx`. |
| 5 | `NCMR/` | 1 | `ncrs` | (root of library) | Single PDF; only 1 NCMR on disk. |
| 6 | `PostMarketSurviellance/` (sic) | 45 | `post_market_surveillance` | keep `ProductComplaints`, `STC001`, `eMDRs` | Also 2 `.html`, 6 `.xml`, 1 `.msg` (unsupported — skipped). |
| 7 | `RiskManagement/` | 11 | `risk_management` | (root of library) | Flat folder — importer works directly. |
| 8 | `DHF/` | 80 | `dhfs` | keep `Software/` subfolder | 43 docx / 35 pdf / 2 xlsx. |
| 9 | `SLQ-DHF/` | 20 | `dhfs` | `SLQ-DHF/` (or merge into DHF) | Flat folder of design-review PDFs. |
| 10 | `EmployeeTraining/` | 193 | `employee_training` | per-person subfolders (`BrianMcVerry`, `ChrisTurner`, …) + `JobDescriptions` | 192 pdf / 1 xlsx. |
| 11 | `Manufacturing/` | 111 | `work_orders` | keep `C.SLQ001`, `ClearTract Foley Catheters` | 1 `.zip` unsupported (skipped). |
| 12 | `RegulatoryStandards&Approvals/` | 39 | `regulatory_standards` | keep `510(K)s`, `ASTM`, `FDARegistration`, `ISO`, `MAF` | 1 `.msg` unsupported. |
| 13 | `DCOs/` | 223 | `qms_documents` | `DCO Log and Change Orders/` with `CompletedDCOs`, `Previous Revisions` | 168 docx / 52 pdf / 3 xlsx. Large — confirm overlap with Track-A Document Control before loading. |
| 14 | `QMSInProcess/DCO087/` … `DCO095/` | (subset of QMSInProcess 176) | `qms_documents` | `DCO Log and Change Orders/In Process/` | In-process DCO working folders. |

---

## Needs manual triage (no clean library match / deferred)

| Source folder | Files | Observation / proposed handling |
|---|---|---|
| `Administration/` | 6 | `Completed AD.SLQ001 Forms` (admin forms). No dedicated library — candidate for `forms_templates_travelers` or a new library. **Decide before load.** |
| `DMR/` | 44 | Device Master Record (`SP-L.SLQ007`–`010`). No `device_master_record` library exists among the 11. Triage — likely Phase 5 (module) or a new library. |
| `FDA Registration Information/` | 4 | Overlaps `RegulatoryStandards&Approvals/FDARegistration`. Fold into `regulatory_standards` or triage. |
| `QMSInProcess/DC.SLQ001/`, `DC.SLQ002/` | part of 176 | Design-project (EDMS transition) working docs — belong with DHF/software history; confirm target. |
| `QMSInProcess/Quality Planning Documents/` | part of 176 | Quality plans — candidate `qms_documents`; confirm. |
| `QMSInProcess/Lot SLQ-05132026/` | part of 176 | Manufacturing lot record — candidate `work_orders`; confirm. |
| `DesignSOPDocExamples/` | 7 | Example/template docs (`FutureProjectInformation`). Likely **skip** (not a record) or `forms_templates_travelers`. |
| `Report/` | 0 | Empty — skip. |

## Explicitly out of scope for Phase 4 (module tables / Phase 5)

Per Prompt 10, these belong in their dedicated module tables and are **left for
Phase 5**, not imported into `admin_docs`:

| Source folder | Files | Module |
|---|---|---|
| `Equipment/` | 126 | Equipment module (calibration/PM) |
| `Suppliers/` | 101 | Suppliers module (approved supplier list) |
| `Purchasing/` | 150 | Purchasing module (PO log) |
| `Supplies/` | 18 | Supplies module |
| `Distribution/` | 35 | Distribution / rep-traceability module |

---

## Recommended load order (Prompt 11)

1. Flat folders first (importer works as-is): `RiskManagement`, `SLQ-DHF`, `NCMR`.
2. Single-level nested (one importer run per subfolder): `EmployeeTraining/*`,
   `Audits/*`, `ManagementReviewMeetings/*`, `RegulatoryStandards&Approvals/*`,
   `PostMarketSurviellance/*`, `Manufacturing/*`, `DHF/Software`, `CAPAs/*`.
3. Large / overlap-sensitive last, after triage: `DCOs/*`, `QMSInProcess/*`.
4. Resolve the "Needs manual triage" rows with Ethan before loading them.
