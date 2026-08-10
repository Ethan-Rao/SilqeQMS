# Phase 3 — Prompt 14: Phase 6 — Cross-Links, Live Dashboard & Library Intelligence

## Context and goals

The system is fully populated. The focus now shifts from loading data to making it
**actionable**. The three goals for Phase 6:

1. **Cross-link the data** — POs linked to supplier records; equipment linked to service
   providers; admin_docs CAPA and audit records surfaced next to the relevant module pages.
2. **Live dashboard** — replace static cards with counts of items that need attention
   (overdue calibrations, expiring supplier certs, open training, etc.).
3. **Library intelligence** — in-library search + folder/file counts so 1,029 admin_docs
   files are navigable without the global search.

---

## Task A — PO-Supplier auto-reconciliation (script, coordinator runs)

Write `scripts/_reconcile_po_suppliers.py`. For each of the 156 `PurchaseOrder` rows
where `supplier_id IS NULL`, attempt to match the freetext vendor column value to a
`Supplier` record using case-insensitive substring matching.

Use a hand-curated mapping for the known aliases that won't substring-match cleanly:

| PO vendor string (contains) | Supplier name |
|---|---|
| Shopify | *(skip — not a QMS supplier)* |
| Wuxi | *(skip)* |
| Nelson | *(skip)* |
| Penguin | *(skip)* |
| Pathway | Pathway Medical |
| Repligen | Repligen |
| Cole-Parmer | Cole-Palmer |
| Fisher | Fisher Scientific (Thermo Fisher) |
| VWR | VWR International |
| McMaster | McMaster-Carr |
| Glacier | Glacier Tanks |
| Richman | Richman Chemical |
| Tokyo | Tokyo Chemical Industry (TCI) |
| TCI | Tokyo Chemical Industry (TCI) |
| Uline | Uline |
| US Plastic | United States Plastic Corp |
| Micro-Precision | Micro-Precision Calibration |
| MicroPrecision | Micro-Precision Calibration |
| Culligan | Culligan |
| Steripax | Steripax |
| Ningbo | Ningbo (catheter supplier) |
| IAG | Independent Air Groups |
| FGL | FGL Environmental |
| FireFly | FireFlySci |

Print matched and unmatched counts. Include `DRY_RUN = True`. On live run, set
`purchase_orders.supplier_id` to the matched supplier's ID and commit.

---

## Task B — Equipment-Supplier service associations (script, coordinator runs)

Write `scripts/_seed_equipment_supplier_links.py`. Seed
`equipment_suppliers` join-table rows using known service relationships derivable from
the calibration certificate filenames already attached to equipment records:

| Equipment code(s) | Supplier name | `relationship_type` |
|---|---|---|
| ST-006, ST-007, ST-012, ST-015 | Micro-Precision Calibration | Calibration Service Provider |
| ST-011 | Independent Air Groups | Calibration Service Provider |
| ST-005 | Repligen | Equipment Manufacturer |
| ST-001 | Culligan | Equipment Manufacturer |
| ST-008 | *(no service supplier evident — skip)* | — |

Use `add_supplier_to_equipment()` from `app.eqms.modules.equipment.service`. Skip if the
association already exists. Include `DRY_RUN = True`.

---

## Task C — Live dashboard summary cards (code + deploy)

Replace the generic static dashboard sections with data-driven summary panels. The
dashboard route (`admin.index`) already renders `admin/index.html`. Add a server-side
`dashboard_stats` dict with these counts (all are single-query aggregations — no N+1):

```python
dashboard_stats = {
    "equipment_overdue_cal": count of Equipment where cal_due_date < today and status != "Retired",
    "equipment_overdue_pm":  count of Equipment where pm_due_date < today and status != "Retired",
    "equipment_due_soon":    count in the next 30 days (cal or pm),
    "suppliers_attention":   count where cert_expiration < today+90 or reevaluation < today+90,
    "training_open":         count of TrainingAssignment where acknowledged_at IS NULL,
    "training_overdue":      count of above where due_date < today,
    "docs_released_30d":     count of DocumentRevision released in last 30 days,
    "pos_pending":           count of PurchaseOrder where status = 'pending',
}
```

Render a **"System Status"** strip at the top of the dashboard (above the module cards)
showing coloured tiles for each non-zero count with a link to the relevant module.
Zero-count tiles render as a neutral "All good" state (not hidden — so the strip is
always present as a health indicator).

Only render the strip to users with `admin.view` (staff + admin), same gate as the
existing search box. Use the existing design-system colour tokens (`.badge--danger`,
`.badge--warning`, `.badge--ok`) so no new CSS is needed.

---

## Task D — Admin_docs in-library search (code + deploy)

Add a search box to each admin_docs library list page (`/admin/libraries/<library_key>`).
The search should filter the current folder's files and all descendant files by filename
(case-insensitive substring). Implement as a simple GET param `?q=` on the existing
route — query `AdminDocFile` rows where `library_key = X AND filename ILIKE %q%`, then
show results as a flat list with the folder path as context (`folder / subfolder / filename`),
bypassing the normal folder-tree view when `q` is non-empty.

Also add **file and subfolder counts** to each folder card in the tree view (the count of
direct files, not recursive — just "5 files, 2 subfolders").

---

## Task E — Supplier detail: linked POs panel (code + deploy)

On the supplier detail page (`/admin/suppliers/<id>`), add a collapsible **"Purchase
Orders"** panel below the existing documents section. Query `PurchaseOrder` where
`supplier_id = supplier.id`, order by `order_date DESC`, limit 20 for the initial render.
Show: PO number (linked to PO detail if that route exists, otherwise plain text),
order date, status badge, total amount.

If `supplier.documents` already contains a supplier assessment or quality agreement, add
a quick-link "Assessment on file" badge next to the supplier name in the list view.

---

## Task F — Deploy discipline

Tasks A and B are script-only (coordinator runs). Tasks C, D, E are code changes —
commit and push together as one deployment. No migration needed (all UI/route changes).
Continue single-migration-head and import-guard rules. Run full test suite before pushing.

Add tests for the `dashboard_stats` query (assert expected keys present, values are
integers ≥ 0) and the in-library search (assert results contain the expected filename,
assert folder-tree view when `q` is empty).

---

## Deliverables

1. `scripts/_reconcile_po_suppliers.py` — dry-run output (matched/unmatched counts).
2. `scripts/_seed_equipment_supplier_links.py` — dry-run output.
3. Tasks C, D, E deployed. Coordinator confirms dashboard strip and library search on
   the live site.
4. Coordinator runs A and B live after reviewing dry-run output.
