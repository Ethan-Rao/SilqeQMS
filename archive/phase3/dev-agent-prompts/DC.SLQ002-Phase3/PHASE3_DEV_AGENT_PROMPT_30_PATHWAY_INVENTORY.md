# Prompt 30 — Pathway Available Inventory Table on Supplies Page

## Overview

Add a **"Pathway Available Inventory"** read-only table at the top of the Supplies list page
(`/admin/supplies`), populated from a Pathway Inventory Excel file stored in S3.

The file is a dated snapshot (`Pathway Inventory 7.15.26.xlsx`). It will be uploaded to a
fixed S3 storage key by a coordinator script. The route reads and parses it on each page load
and passes the rows to the template. If the file is absent, the section is silently hidden.

---

## Files to Change

| File | Change |
|---|---|
| `app/eqms/modules/supplies/admin.py` | Parse inventory snapshot in `supplies_list()` |
| `app/eqms/templates/admin/supplies/list.html` | Add inventory table above existing supply list |
| `scripts/_upload_pathway_inventory.py` | Coordinator script (new, gitignored) |

No migration, no model change, no admin_docs registration needed.

---

## A. Storage Key Convention

Use a fixed S3 storage key for the latest inventory snapshot:

```
supplies/inventory/pathway_inventory_latest.xlsx
```

When a newer snapshot is available, the coordinator script simply overwrites this key.
The "as of" date label comes from the file's metadata (stored alongside it).

To carry the snapshot date without coupling to a filename, store a companion metadata record
in the DB as a single `AdminDocFile` row — **or** more simply, store the "as of" date string
in the file itself via the existing `AdminDocFile.description` field.

**Simplest approach**: Store the file as an `AdminDocFile` record in a new library key
`"supplies_inventory"` at root level. The `description` field holds the formatted date string
`"Jul 15, 2026"`. The route queries for this file by library key, reads bytes from storage,
parses it, and uses `description` as the label.

---

## B. Register `supplies_inventory` Library

File: `app/eqms/modules/admin_docs/admin.py`

1. Add to `LIBRARIES`:
   ```python
   "supplies_inventory": "Supplies Inventory Snapshots",
   ```

2. Add to `LIBRARY_ENDPOINTS`:
   ```python
   "supplies_inventory": "admin_docs.supplies_inventory",
   ```

3. Add route (staff/admin view only — no manufacturing permission needed):
   ```python
   @bp.get("/supplies-inventory")
   @require_any_permission("admin.view", "staff.view")
   def supplies_inventory():
       return _render_library("supplies_inventory")
   ```

   Do NOT add to `ACCORDION_LIBRARIES`.

---

## C. `supplies_list()` Route Update

File: `app/eqms/modules/supplies/admin.py`

At the top of `supplies_list()`, before the existing query, add:

```python
# ── Pathway Inventory Snapshot ──────────────────────────────────────────────
pathway_inventory = []
pathway_inventory_date = None
try:
    from app.eqms.modules.admin_docs.models import AdminDocFile
    inv_file = (
        s.query(AdminDocFile)
        .filter(
            AdminDocFile.library_key == "supplies_inventory",
            AdminDocFile.folder_id.is_(None),
        )
        .order_by(AdminDocFile.id.desc())
        .first()
    )
    if inv_file:
        import io
        import openpyxl
        storage = storage_from_config(current_app.config)
        raw = storage.get_bytes(inv_file.storage_key)
        wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                continue  # skip header
            item_code = row[1]   # col B (0-indexed: 1)
            description = row[2] # col C
            vendor = row[3]      # col D
            uom = row[6]         # col G (for qty context)
            qty = row[7]         # col H
            if item_code is None and description is None:
                continue
            pathway_inventory.append({
                "item_code": str(item_code) if item_code is not None else "—",
                "description": description or "—",
                "vendor": vendor or "—",
                "qty": qty,
                "uom": uom or "",
            })
        wb.close()
        pathway_inventory_date = inv_file.description  # set by coordinator script
except Exception:
    pass  # Gracefully degrade — table is hidden if file unavailable
```

Pass to template:
```python
return render_template(
    "admin/supplies/list.html",
    supplies=supplies,
    search=search,
    pathway_inventory=pathway_inventory,
    pathway_inventory_date=pathway_inventory_date,
)
```

---

## D. Template Update

File: `app/eqms/templates/admin/supplies/list.html`

Add the following block **immediately before** the existing supply list table / search bar.
Only render if `pathway_inventory` is non-empty:

```html
{% if pathway_inventory %}
<section class="pathway-inventory-section" style="margin-bottom: 2rem;">
  <div style="display: flex; align-items: baseline; gap: 1rem; margin-bottom: 0.75rem;">
    <h2 style="margin: 0; font-size: 1.1rem; font-weight: 600;">Pathway Available Inventory</h2>
    {% if pathway_inventory_date %}
    <span style="font-size: 0.82rem; color: var(--text-muted, #6c757d);">As of {{ pathway_inventory_date }}</span>
    {% endif %}
  </div>
  <div style="overflow-x: auto;">
    <table class="table" style="font-size: 0.88rem;">
      <thead>
        <tr>
          <th>Item Code</th>
          <th>Description</th>
          <th>Vendor</th>
          <th style="text-align: right;">Available Qty</th>
        </tr>
      </thead>
      <tbody>
        {% for item in pathway_inventory %}
        <tr>
          <td><code style="font-size: 0.82rem;">{{ item.item_code }}</code></td>
          <td>{{ item.description }}</td>
          <td>{{ item.vendor }}</td>
          <td style="text-align: right; font-variant-numeric: tabular-nums;">
            {% if item.qty is not none %}
              {{ "{:,}".format(item.qty | int) }}
              {% if item.uom %}<span style="font-size: 0.78rem; color: var(--text-muted, #6c757d);"> {{ item.uom }}</span>{% endif %}
            {% else %}—{% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endif %}
```

Key formatting decisions:
- Quantities are right-aligned with thousands separators (`"{:,}".format(qty | int)`).
- The UOM (Each / Liters) is shown in muted text after the number — this is important because the Suspension row shows `46 L` while catheter rows show quantities in Each.
- Item codes are rendered in a `<code>` tag (monospace).
- The table is in the app's existing `.table` style.
- Section degrades silently (not rendered) if no file is uploaded yet.

---

## E. Coordinator Script: `scripts/_upload_pathway_inventory.py`

```python
"""Upload a Pathway Inventory Excel snapshot to the supplies_inventory admin_docs library.

Usage:
    python scripts/_upload_pathway_inventory.py                    # dry run
    python scripts/_upload_pathway_inventory.py --execute          # write to S3 + DB
    python scripts/_upload_pathway_inventory.py --file "path/to/Pathway Inventory X.xlsx" --execute
"""
```

Logic:
1. Accept `--file` argument (default: `Supplies/Pathway Inventory 7.15.26.xlsx`).
2. Extract the "as of" date from the filename using regex `r'(\d+\.\d+\.\d+)'`:
   - `7.15.26` → parse as `MM.DD.YY` → `Jul 15, 2026`.
3. In dry-run mode: print what would be uploaded and what date string would be stored.
4. In `--execute` mode:
   - Upload file bytes to S3 at key `supplies/inventory/pathway_inventory_latest.xlsx`
     using `storage.put(key, data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")`.
   - Delete any existing `AdminDocFile` rows for `library_key="supplies_inventory"` and `folder_id=None`.
   - Insert a new `AdminDocFile` with:
     - `library_key = "supplies_inventory"`
     - `folder_id = None`
     - `storage_key = "supplies/inventory/pathway_inventory_latest.xlsx"`
     - `filename = "Pathway Inventory.xlsx"`
     - `description = "Jul 15, 2026"` (formatted date from filename)
     - `content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"`
     - `sha256` / `size_bytes` as normal

---

## F. Exact Inventory Data (10 rows)

For reference — this is what will be displayed from the current file:

| Item Code | Description | Vendor | Qty | UOM |
|---|---|---|---|---|
| 22000100001 | 20 Fr Straight Tip 10mL Balloon Foley Catheters Uncoated, Unsterilized | Ningbo | 985 | Each |
| 22200100001 | 22 Fr Straight Tip 10mL Balloon Foley Catheters Uncoated, Unsterilized | Ningbo | 985 | Each |
| 22400100001 | 24 Fr Straight Tip 10mL Balloon Foley Catheters Uncoated, Unsterilized | Ningbo | 985 | Each |
| 21400100001 | 14 Fr Straight Tip 10mL Balloon Foley Catheters Uncoated, Unsterilized | Ningbo | 480 | Each |
| 21800100001 | 18F Straight Tip 10ml Balloon Foley Catheters Uncoated, Unsterilized | Ningbo | 1,400 | Each |
| 21600100001 | 16 Fr Straight Tip 10mL Balloon Foley Catheters Uncoated, Unsterilized | Ningbo | 18,500 | Each |
| C.SLQ001 | Suspension | Silq | 46 | Liters |
| YNGMDSLEEVE0010 | Catheter Sleeves | Ningbo | 20,859 | Each |
| POUCH0010 | Sterilization Pouch | SteriPax | 4,700 | Each |
| LDSBGPOUCH0010 | Cartons (10-up white catheter) 3.25 x 2.5 x 19.75, .024 SBS | Landsberg | 880 | Each |
| 200020 | Catheter 10 pk Boxes | SL Packaging | 1,060 | Each |

---

## Execution Order

1. **Dev agent**: implement code changes (B, C, D) and write coordinator script (E). Deploy.
2. **After deploy**: run `python scripts/_upload_pathway_inventory.py --execute`.
3. Verify the table appears at the top of `/admin/supplies`.

No migration needed.
