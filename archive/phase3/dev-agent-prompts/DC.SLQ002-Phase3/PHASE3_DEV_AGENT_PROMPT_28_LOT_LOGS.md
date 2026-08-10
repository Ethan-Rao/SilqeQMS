# Prompt 28 — Lot Log Integration, ClearTract Lots, Equipment Download, CAPA Section Dates

## Overview

This prompt covers five related changes driven by newly uploaded Excel/CSV logs:

| Section | Scope |
|---|---|
| A | DB model migration — new columns on `ManufacturingLot` and `CAPARecord` |
| B | Suspension Manufacturing — import Lot Numbering Log, redesign index lot display |
| C | ClearTract — import Lot Log CSV, add lot table to Manufacturing index |
| D | Equipment — register `equipment_files` admin_docs library, upload master list, add download button |
| E | CAPA — import section completion dates from CAPA Log, update tracker UI |

**Coordinator scripts run before deploy (after migration).** All scripts are in `scripts/`.

---

## SECTION A — Alembic Migration

### A1. `ManufacturingLot` — add 3 columns

File: `app/eqms/modules/manufacturing/models.py`

Add after the existing `operator_notes` field:
```python
quantity: Mapped[str | None] = mapped_column(String(128), nullable=True)      # "101.9 kg", "1298 units"
expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)     # ClearTract lots only
part_revision: Mapped[str | None] = mapped_column(String(16), nullable=True)  # "B", "C", etc.
```

### A2. `CAPARecord` — add 9 columns

File: `app/eqms/modules/capas/models.py`

Add after the existing `effectiveness_result` field:
```python
initiated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
section_1_date: Mapped[date | None] = mapped_column(Date, nullable=True)
section_2_date: Mapped[date | None] = mapped_column(Date, nullable=True)
section_3_date: Mapped[date | None] = mapped_column(Date, nullable=True)
section_4_date: Mapped[date | None] = mapped_column(Date, nullable=True)
section_5_date: Mapped[date | None] = mapped_column(Date, nullable=True)
section_6_date: Mapped[date | None] = mapped_column(Date, nullable=True)
closed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
on_time_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

### A3. Generate and apply migration

```
flask db migrate -m "add lot quantity expiration, capa section dates"
flask db upgrade
```

---

## SECTION B — Suspension Manufacturing Lots

### B1. Coordinator script: `scripts/_import_suspension_lots.py`

Read `Manufacturing/C.SLQ001/SILQ Lot Numbering Log.xlsx`, sheet `"Coating"`. Skip row 0 (title) and row 1 (header). Import the following 6 lots into `ManufacturingLot`. Skip any lot whose `lot_number` already exists.

```
lot_number    | manufacture_date | work_order | quantity    | operator | part_revision | product_code | status
--------------+------------------+------------+-------------+----------+---------------+--------------+---------
2209-01-1     | 2022-09-28       | 2209-01    | 101.9 kg    | CT       | B             | Suspension   | Released
2209-01-2     | 2022-09-29       | 2209-01    | 130.4 kg    | CT       | B             | Suspension   | Released
2302-01-1     | 2023-03-30       | 2302-01    | 129.6 kg    | BW       | B             | Suspension   | Released
2302-01-2     | 2023-03-30       | 2302-01    | 114.0 kg    | BW       | B             | Suspension   | Released
2502-01-1     | 2025-02-13       | 2502-01    | 81.2 kg     | ER       | B             | Suspension   | Released
2502-01-2     | 2025-02-13       | 2502-01    | 165.0 kg    | ER       | B             | Suspension   | Released
```

Derive `work_order` by taking the lot number up to (but not including) the final `-Z` digit: e.g., `"2209-01-1"[:7]` = `"2209-01"`. Alternatively, read column 0 and strip the last two characters (`[:-2]`).

The `operator` value is the initials portion of the "Assigned by" field (split on space, take `[0]`).

### B2. Coordinator script: `scripts/_upload_wo_log.py`

Upload `Manufacturing/C.SLQ001/C.SLQ001WorkOrders/SILQ Work Order Log.xlsx` to the `work_orders` admin_docs library. Target folder path: `Work Orders → C.SLQ001 → C.SLQ001WorkOrders`. Find the target folder by walking the `AdminDocFolder` tree from root by name (case-insensitive). Use the same S3 upload pattern as `_upload_manufacturing_files.py`. Skip if a file with the same name already exists in that folder.

### B3. Manufacturing index route update

File: `app/eqms/modules/manufacturing/admin.py` → `manufacturing_index()`

**Current:** queries `recent_suspension_lots` (last 3 by `updated_at`).

**Replace with:**
1. Load ALL Suspension lots ordered `manufacture_date ASC, lot_number ASC`:
   ```python
   suspension_lots = (
       s.query(ManufacturingLot)
       .filter(ManufacturingLot.product_code == "Suspension")
       .order_by(ManufacturingLot.manufacture_date.asc(), ManufacturingLot.lot_number.asc())
       .all()
   )
   ```

2. Add hardcoded RI-folder mapping (after the query):
   ```python
   WO_RI_FOLDER = {
       "2209-01": "LotCRYLK",
       "2302-01": "LotLBSEE",
       "2502-01": "LotMY27B",
   }
   ```

3. Pre-resolve folder IDs using the already-loaded `children_by_parent` and `files_by_folder` dicts:

   - Find `dhr_root` folder: child of `suspension_root` named `"C.SLQ001DHRs"`.
   - Find `ri_root` folder: child of `suspension_root` named `"M.SLQ001RIs"`.
   - Build `lot_dhr_files: dict[str, list[AdminDocFile]]` — key is `lot_number`, value is files inside the child of `dhr_root` named `"Lot" + lot.lot_number`.
   - Build `lot_ri_files: dict[str, list[AdminDocFile]]` — key is `lot.work_order`, value is files inside the child of `ri_root` named `WO_RI_FOLDER.get(lot.work_order)`.

   Helper pattern (already in scope: `children_by_parent`, `files_by_folder`):
   ```python
   def _find_child(parent_id, *names):
       wanted = {n.lower() for n in names}
       for f in children_by_parent.get(parent_id, []):
           if (f.name or "").lower() in wanted:
               return f
       return None

   dhr_root = _find_child(suspension_root.id, "C.SLQ001DHRs") if suspension_root else None
   ri_root  = _find_child(suspension_root.id, "M.SLQ001RIs")  if suspension_root else None

   lot_dhr_files = {}
   for lot in suspension_lots:
       folder = _find_child(dhr_root.id, "Lot" + lot.lot_number) if dhr_root else None
       lot_dhr_files[lot.lot_number] = files_by_folder.get(folder.id, []) if folder else []

   lot_ri_files = {}
   for wo_num, ri_folder_name in WO_RI_FOLDER.items():
       folder = _find_child(ri_root.id, ri_folder_name) if ri_root else None
       lot_ri_files[wo_num] = files_by_folder.get(folder.id, []) if folder else []
   ```

4. Pass to template:
   ```python
   suspension_lots=suspension_lots,
   lot_dhr_files=lot_dhr_files,
   lot_ri_files=lot_ri_files,
   wo_ri_folder=WO_RI_FOLDER,
   ```

   Remove the old `recent_suspension_lots` key.

### B4. Manufacturing index template — Suspension section redesign

File: `app/eqms/templates/admin/manufacturing/index.html`

Replace the current "Production Lots" compact row in the Suspension accordion section with a **production lots table**. Design spec:

- The table header columns: **Lot #**, **Date**, **Work Order**, **Quantity**, **Status**, **Documents**
- One row per lot, ordered by date
- A subtle horizontal divider between different work orders (i.e., between the `2209-01` pair and the `2302-01` pair, etc.)
- **Lot # cell**: styled as a monospace badge, e.g. `<code>2209-01-1</code>`
- **Date cell**: formatted as `Sep 28, 2022` (use Jinja's `strftime` filter or a custom filter)
- **Work Order cell**: rendered as the WO number `2209-01`
- **Quantity cell**: `lot.quantity` (e.g., "101.9 kg")
- **Status cell**: Bootstrap badge colored by status (Released = success, In-Process = warning, etc.)
- **Documents cell**: contains two small pill buttons that toggle Bootstrap collapse panels below the row:
  - `DHR` — collapse anchor opens the DHR file list for this lot (from `lot_dhr_files[lot.lot_number]`)
  - `RI` — collapse anchor opens the RI file list for this lot's work order (from `lot_ri_files[lot.work_order]`)

For the collapsed file panels:
- Each panel appears as a sub-row spanning all columns
- It shows a simple `<ul>` of files, each with:
  - `<a href="{{ url_for('admin_docs.admin_docs_document_view', doc_id=f.id) }}">{{ f.filename }}</a>`
- If no files are found, show "No documents uploaded yet."

Keep the existing `"+ New Lot"` button and the "View All Lots" link to `manufacturing.suspension_list`.

Remove the old compact 3-lot "Production Lots" badge row.

---

## SECTION C — ClearTract Production Lots

### C1. Coordinator script: `scripts/_import_cleartract_lots.py`

Read `Manufacturing/ClearTract Foley Catheters/ClearTractLotLog.csv`. Headers: `Lot, SKU, Manufacturing Date, Expiration Date, Total Units in Lot`. Import into `ManufacturingLot`. Skip if `lot_number` already exists.

Field mapping:
```
CSV Lot         -> lot_number
"SLQ-" + SKU    -> product_code   (e.g., SKU "211610SPT" -> product_code "SLQ-211610SPT")
Manufacturing Date -> manufacture_date
Expiration Date -> expiration_date
str(Total Units in Lot) + " units" -> quantity
"Released"      -> status
```

Full data (7 rows):
```
Lot              | SKU       | Mfg Date   | Exp Date   | Units
-----------------+-----------+------------+------------+-------
SLQ-01242025     | 211810SPT | 2025-01-31 | 2028-01-31 | 369
SLQ-05012025     | 211610SPT | 2025-05-31 | 2028-05-31 | 1298
SLQ-05022025     | 211810SPT | 2025-05-31 | 2028-05-31 | 3268
SLQ-11192024     | 211410SPT | 2024-11-30 | 2027-11-30 | 221
SLQ-11202024     | 211610SPT | 2024-11-30 | 2027-11-30 | 944
SLQ-81020515241  | 211810SPT | 2024-05-15 | 2027-05-15 | 380
SLQ-05132026     | 211610SPT | 2026-05-13 | 2029-05-13 | 1910
```

### C2. Manufacturing index route update — ClearTract lots

In `manufacturing_index()`, add:

```python
cleartract_lots = (
    s.query(ManufacturingLot)
    .filter(ManufacturingLot.product_code.like("SLQ-%"))
    .order_by(ManufacturingLot.product_code.asc(), ManufacturingLot.manufacture_date.asc())
    .all()
)

# Group by product_code (SKU)
from collections import defaultdict
cleartract_by_sku = defaultdict(list)
for lot in cleartract_lots:
    cleartract_by_sku[lot.product_code].append(lot)

# Pre-resolve DHR folder files for each ClearTract lot
# DHR folder structure in work_orders:
#   Work Orders / ClearTract Foley Catheters / SLQ-211610SPT DHRs / LotSLQ-05012025
# Folder name of individual lot = "Lot" + lot.lot_number  (e.g., "LotSLQ-05012025")
# Parent folder name = lot.product_code + " DHRs"  (e.g., "SLQ-211610SPT DHRs")

cleartract_dhr_files = {}  # keyed by lot.lot_number
if cleartract_root:
    for lot in cleartract_lots:
        sku_dhr_folder = _find_child(cleartract_root.id, lot.product_code + " DHRs")
        lot_folder = _find_child(sku_dhr_folder.id, "Lot" + lot.lot_number) if sku_dhr_folder else None
        cleartract_dhr_files[lot.lot_number] = files_by_folder.get(lot_folder.id, []) if lot_folder else []
```

Pass `cleartract_lots=cleartract_lots`, `cleartract_by_sku=cleartract_by_sku`, `cleartract_dhr_files=cleartract_dhr_files` to the template.

### C3. Manufacturing index template — ClearTract section redesign

File: `app/eqms/templates/admin/manufacturing/index.html`

Replace the current ClearTract accordion body (which shows the work_orders document tree) with a **production lots table by SKU**, followed by the existing document tree below it. The structure:

For each SKU group in `cleartract_by_sku` (display name map: `SLQ-211410SPT` → "10 Fr (211410SPT)", `SLQ-211610SPT` → "16 Fr (211610SPT)", `SLQ-211810SPT` → "18 Fr (211810SPT)"):

```
[SKU subtitle row]
Lot #  |  Mfg Date  |  Expiration  |  Units  |  Documents
...
```

- **Lot # cell**: monospace badge with the lot number (e.g., `SLQ-05132026`)
- **Mfg Date**: formatted date
- **Expiration**: formatted date (with color if expired or within 6 months: yellow/red)
- **Units**: quantity field (e.g., "1910 units")
- **Documents cell**: a `DHR` pill button that collapses open the file list for this lot from `cleartract_dhr_files`

Keep the existing ClearTract document tree (DMRs, Labeling, Specifications, etc.) below the lots table, collapsed under a "Document Library" toggle so the page isn't too long.

---

## SECTION D — Equipment Master List Download

### D1. Register `equipment_files` admin_docs library

File: `app/eqms/modules/admin_docs/admin.py`

1. Add to `LIBRARIES` dict:
   ```python
   "equipment_files": "Equipment Documents",
   ```

2. Add to `LIBRARY_ENDPOINTS` dict:
   ```python
   "equipment_files": "admin_docs.equipment_files",
   ```

3. Add route:
   ```python
   @bp.get("/equipment-files")
   @require_any_permission("admin.view", "staff.view")
   def equipment_files():
       return _render_library("equipment_files")
   ```

   Do NOT add `"equipment_files"` to `ACCORDION_LIBRARIES` — use the standard folder-by-folder view.

### D2. Coordinator script: `scripts/_upload_equipment_master.py`

Upload `Equipment/Silq Equipment Master List.xlsx` to the `equipment_files` library at root level (no subfolder). Use the same S3 upload + `AdminDocFile` insert pattern as other upload scripts. Skip if a file with the same name already exists in this library at root.

### D3. Equipment list page — add download button

File: `app/eqms/modules/equipment/admin.py` → `equipment_list()` route

At the bottom of the route, query for the master file:
```python
from app.eqms.modules.admin_docs.models import AdminDocFile
equipment_master_file = (
    s.query(AdminDocFile)
    .filter(
        AdminDocFile.library_key == "equipment_files",
        AdminDocFile.folder_id.is_(None),
        AdminDocFile.filename.ilike("%Equipment Master%"),
    )
    .first()
)
```

Pass `equipment_master_file=equipment_master_file` to the template.

File: `app/eqms/templates/admin/equipment/list.html`

Add at the very top of the page content (above the existing filter bar / status cards), a right-aligned download button:
```html
{% if equipment_master_file %}
<div class="d-flex justify-content-end mb-3">
  <a href="{{ url_for('admin_docs.admin_docs_document_download', doc_id=equipment_master_file.id) }}"
     class="btn btn-outline-secondary btn-sm">
    <i class="bi bi-file-earmark-spreadsheet"></i> Download Equipment Master List
  </a>
</div>
{% endif %}
```

---

## SECTION E — CAPA Section Completion Dates

### E1. Coordinator script: `scripts/_import_capa_log.py`

Read `CAPAs/SILQ CAPA Log.xlsx`, sheet `"2023"`. Skip rows 0–3 (title block). The data header is row 3 (0-indexed). Data starts at row 4.

Match to existing `CAPARecord` by mapping the log's `CAPA # YY-XXX` format (e.g., `"001-2025"`) to the DB's `capa_number` format `"CAPA001-2025"`:
```python
# log_num e.g. "001-2025"
num, year = log_num.split("-")
db_capa_number = f"CAPA{num.zfill(3)}-{year}"
```

For each matched record, update:
| Log column | DB field |
|---|---|
| Summary of Issue / Opportunity | `title` |
| Initiated By | `initiated_by` |
| Initiation Date | `opened_date` |
| Date CAPA Section 1 Complete | `section_1_date` |
| Date CAPA Section 2 Complete | `section_2_date` |
| Date CAPA Section 3 Complete | `section_3_date` |
| Date CAPA Section 4 Complete | `section_4_date` |
| Date CAPA Section 5 Complete | `section_5_date` |
| Date CAPA Section 6 Complete | `section_6_date` |
| Date CAPA Closed | `closed_date` |
| Closed By | `closed_by` |
| On time/Late | `on_time_status` |

Note: Some section date cells contain strings like `"Expected 17 Nov 2026"` — store these in `notes` or skip (do not try to parse as a date). Only set the date field if the value is an actual `datetime` object from openpyxl.

Anticipated data for the 4 known CAPAs:
- `CAPA001-2025`: title = "Inspection of SLQ-211610SPT Finished Goods", sections 1-5 complete (section 6 = expected Nov 2026)
- `CAPA002-2025`: title = "MDR Reporting", sections 1-5 complete (section 6 = expected Jun 2026)
- `CAPA003-2025` and `CAPA004-2025`: read directly from the log

Print a diff summary showing what was updated.

### E2. CAPA list template — section progress indicator

File: `app/eqms/templates/admin/capas/list.html`

For each CAPA row in the list table, add a **Section Progress** mini-indicator. Show 6 small circles (or step dots) — filled (green) if the date is set, hollow (gray) if not:

```html
<div class="d-flex gap-1 align-items-center">
  {% for field in ['section_1_date','section_2_date','section_3_date','section_4_date','section_5_date','section_6_date'] %}
  <span class="badge rounded-circle {% if capa[field] %}bg-success{% else %}bg-light border{% endif %}"
        style="width:14px; height:14px; display:inline-block;"
        title="Section {{ loop.index }}: {% if capa[field] %}{{ capa[field].strftime('%b %d, %Y') }}{% else %}Incomplete{% endif %}">
  </span>
  {% endfor %}
</div>
```

Note: Access fields via `capa.section_1_date` etc. (the model attributes).

### E3. CAPA detail template — section dates panel

File: `app/eqms/templates/admin/capas/detail.html`

Add a new card/panel below the existing CAPA metadata section titled **"Section Completion Dates (QM.SLQ016)"**. Show a 2-column grid:

| Section | Date | Status |
|---|---|---|
| Section 1 — Immediate Containment | `section_1_date` or "—" | ✓ Complete / Pending |
| Section 2 — Problem Description | `section_2_date` or "—" | |
| Section 3 — Root Cause Analysis | `section_3_date` or "—" | |
| Section 4 — Corrective Actions | `section_4_date` or "—" | |
| Section 5 — Preventive Actions | `section_5_date` or "—" | |
| Section 6 — Effectiveness Verification | `section_6_date` or "—" | |

Include **Initiated By**, **Closed By**, and **On-Time Status** fields in this same card.

### E4. CAPA form/edit route — expose new fields

File: `app/eqms/modules/capas/admin.py` (CAPA edit routes)

Add the new fields to the GET (pre-populate) and POST (save) handlers:
- `initiated_by` — text input
- `section_1_date` through `section_6_date` — date inputs (format `%Y-%m-%d`)
- `closed_by` — text input
- `on_time_status` — text input or small select (`"On time"`, `"Late"`, `""`)

File: `app/eqms/templates/admin/capas/form.html` (CAPA create/edit form)

Add the new fields grouped under a "Section Completion Dates" fieldset.

---

## EXECUTION ORDER

1. **Dev agent**: Apply migration (A1–A3) and deploy.
2. **Coordinator** (you/Ethan run locally after migration):
   - `python scripts/_import_suspension_lots.py`
   - `python scripts/_upload_wo_log.py`
   - `python scripts/_import_cleartract_lots.py`
   - `python scripts/_upload_equipment_master.py`
   - `python scripts/_import_capa_log.py`
3. **Dev agent**: Make all template/route code changes (B3–B4, C2–C3, D1/D3, E2–E4).
4. Deploy and verify.

---

## Key Technical Notes

- **Existing `work_orders` accordion library**: The `_render_library` function ignores `folder_id` for accordion libraries. Therefore, file links on the manufacturing page should link directly to `admin_docs.admin_docs_document_view` (or `download`) using the `doc_id`, NOT to the work_orders browser with a folder_id. All file data is pre-loaded in `files_by_folder` in the `manufacturing_index()` route.
- **`admin_docs.admin_docs_document_view` route**: URL `/admin/admin-docs/documents/<int:doc_id>/view`. This is the correct route for inline viewing.
- **`admin_docs.admin_docs_document_download` route**: URL `/admin/admin-docs/documents/<int:doc_id>/download`. For direct download.
- **Date formatting in Jinja**: Use `{{ lot.manufacture_date.strftime('%b %d, %Y') if lot.manufacture_date }}` or add a `dateformat` Jinja filter.
- **Status badge colors**: Released → `bg-success`, In-Process → `bg-warning text-dark`, Quarantined → `bg-danger`, Draft → `bg-secondary`.
- **ClearTract lot number format in folder names**: The admin_docs folder is named `"LotSLQ-01242025"` (i.e., `"Lot" + lot.lot_number`). The lot_number stored in DB will be `"SLQ-01242025"`.
- **Suspension lot folder names**: The folder is named `"Lot2209-01-1"` (i.e., `"Lot" + lot.lot_number`). Lot number stored in DB = `"2209-01-1"`.
