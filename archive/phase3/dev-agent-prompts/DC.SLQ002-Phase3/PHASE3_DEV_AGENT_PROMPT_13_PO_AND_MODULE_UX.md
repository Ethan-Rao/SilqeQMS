# Phase 3 — Prompt 13: PO Import, Supplies, and Module UI/Usability

## Context and production state (as of 2026-07-09)

All Phase 5 module data is now populated:
- **Equipment**: 17 records + 125 document attachments (calibration certs, specs, req forms,
  service logs).
- **Suppliers**: 22 supplier records + 95 document attachments (ISO certs, assessments,
  re-evals, audit reports, quality manuals).
- **Purchasing**: 0 POs in DB. `Purchasing/POs/` has 149 PDFs; `Purchasing/SILQ PO Log.xlsx`
  (sheet `2019 - 2024`, header at row 3) is confirmed importable via `import_po_log()`.
- **Supplies**: 18 files in `Supplies/` — module exists, no data populated yet.

The modules are functionally complete but now that they contain real data we can identify
usability gaps. This prompt covers: (A) PO metadata import, (B) PO PDF attachment,
(C) Supplies data, and (D) module-level UX improvements across Equipment, Suppliers,
and Purchasing.

---

## Task A — PO log metadata import (script, coordinator runs)

Write `scripts/_import_po_log.py` (same one-off credential pattern; uncommitted/gitignored).

The script calls `import_po_log()` from `app.eqms.modules.purchasing.service`, passing the
bytes of `Purchasing/SILQ PO Log.xlsx`. It should:
1. Print the import summary (created, updated, skipped, errors).
2. Include `DRY_RUN = True` guard (no commits when True).
3. Commit only if zero errors.

If `import_po_log()` does not yet exist or its signature differs from what the service
file shows, adapt as needed and note the change.

---

## Task B — PO PDF attachment (script, coordinator runs)

Write `scripts/_import_po_pdfs.py` to attach each PDF in `Purchasing/POs/` to its
matching `PurchaseOrder` record.

**Matching logic**: PO PDFs are named `PO <7-digit-number> <Supplier> <date>.pdf`.
Extract the integer PO number with regex `r"PO\s+(\d+)"` from the filename, then look up
the purchase order by `po_number` in the DB. The existing `po_number` format in the DB
is likely `PO-XXXXXXX` (7 digits, left-padded) — confirm by querying the first few rows
and adjust the lookup accordingly.

For each matched PO, attach the PDF as a `PurchaseOrderAttachment` (type `po_pdf`) using
`storage.put_bytes(storage_key, file_bytes)` + DB row creation (same pattern as the
equipment/supplier file scripts). Skip if a `po_pdf` attachment already exists for that PO.

Include `DRY_RUN = True`. Print match stats: matched/unmatched PDFs, per-PO attachment count.

---

## Task C — Supplies data population (script, coordinator runs)

Inspect `Supplies/` and write `scripts/_import_supplies.py`:
1. Print the file listing (name and subfolder structure) first.
2. Create `Supply` records from the `Supplies/` folder if a structured format exists
   (xlsx or subfolders by supply code), or attach files to a general "Supplies" subfolder
   in the `qms_documents` admin_docs library if the folder is flat.
3. Use `create_supply()` and `upload_supply_document()` from
   `app.eqms.modules.supplies.service` if structured records make sense.
4. Include `DRY_RUN = True`.

---

## Task D — Module UI and usability improvements (code change + deploy)

Now that all four modules have real data, do a targeted usability pass on each:

### D1 — Equipment list: due-date dashboard summary

Add a small status summary bar at the top of the Equipment list (`/admin/equipment`)
showing counts: **Active | Overdue (cal) | Overdue (PM) | Due soon (cal or PM)**. Each
count is a quick-filter link (appends `cal_overdue=1` / `pm_overdue=1` to the URL).
Use the existing `due_status()` helper — don't add any new DB queries, just aggregate
from the already-loaded equipment list.

### D2 — Equipment detail: document section grouping

The detail page currently shows all `ManagedDocument` rows in a flat table. Improve it:
group by `category` using the `DOCUMENT_CATEGORIES` dict and render each group as a
named subsection. Put `requirements_form` and `spec_document` first (primary docs),
then `calibration`, `manual`, `general`. Within calibration, sort by `uploaded_at` desc
so the most recent cert is first.

### D3 — Suppliers list: expiry/re-eval status indicators

Suppliers have `certification_expiration` and `next_reevaluation_date`. Add a status
badge on the list view for each supplier using the existing `date_status()` helper:
- `certification_expiration` < today → **Cert Expired** (danger)
- `next_reevaluation_date` < today → **Re-eval Due** (warning)
- Both OK → nothing shown

Also add a filter shortcut "Attention needed" that shows suppliers where either date is
past or within 90 days.

### D4 — Purchasing list: supplier name in the list

The PO list should show the supplier name alongside the PO number. If `purchase_order.supplier`
is already eager-loaded (it is, per the model), just render `po.supplier.name` in the
list template. If the supplier was not linked during the PO log import (likely — the xlsx
has a freetext vendor column), add a note about manual reconciliation and skip the join
for now.

### D5 — Global search: include Equipment and Suppliers

Extend the global search (`/admin/search`) to also search equipment (`equip_code`,
`description`, `mfg`) and suppliers (`name`, `product_service_provided`), with results
grouped separately. This makes it the single entry point for finding anything in the system.

---

## Task E — Deploy discipline

Tasks A, B, C are script-only (coordinator runs). Task D is a code change — commit,
push, confirm DO deploy green. No migration needed for D1–D5 (all UI/template changes).
Continue single-migration-head and import-guard rules.

---

## Deliverables

1. `scripts/_import_po_log.py` — coordinator runs (dry-run output first).
2. `scripts/_import_po_pdfs.py` — coordinator runs (dry-run output first).
3. `scripts/_import_supplies.py` — coordinator runs or skipped if Supplies is flat/trivial.
4. Task D deployed to production. Coordinator confirms `/admin/equipment` and
   `/admin/suppliers` show improved views.
