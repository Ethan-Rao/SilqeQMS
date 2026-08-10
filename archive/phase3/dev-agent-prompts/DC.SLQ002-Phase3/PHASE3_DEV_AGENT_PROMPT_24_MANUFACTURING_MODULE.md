# Phase 3 — Prompt 24: Manufacturing Module Redesign

## Context

Ethan's feedback: the Manufacturing landing page should show two accordion sections
(Suspension and ClearTract Foley Catheters) directly — no separate Work Orders card,
no "Coming soon" placeholder. The work_orders admin_docs library already holds the
product document trees from the Phase 4 import; the Manufacturing page should surface
this content inline alongside the structured lot-tracking module.

---

## Task A — Remove Work Orders card from dashboard

In `index.html`, remove the Work Orders card that was added in Prompt 23 from the
Silq Operations column. The work_orders admin_docs library remains in the system and
is accessible via search — it is just no longer featured as a top-level dashboard card.

Update the Operations column card count from 8 to 7 (Work Orders removed).

---

## Task B — Redesign Manufacturing landing page

### B1 — Route change

`manufacturing_index()` now needs data. Change it from a bare `render_template` call
to a route that:

1. Loads all `AdminDocFolder` and `AdminDocFile` records for `library_key = "work_orders"`
   in two queries.
2. Builds an in-memory tree: `folders_by_id`, `children_by_parent`, `files_by_folder`
   (same pattern as `accordion.html` / `_render_library_accordion`).
3. Finds the top-level folder whose name matches `"Work Orders"` (the single root
   folder of the work_orders library).
4. From its immediate children, finds and passes:
   - `suspension_root`: the folder named `"C.SLQ001"` (or equivalent — match by name,
     not hardcoded ID)
   - `cleartract_root`: the folder named `"ClearTract Foley Catheters"`
5. Also queries the most recent 3 `ManufacturingLot` records for the Suspension product
   to show a quick-glance recent-lots panel.
6. Passes all of this to a redesigned `admin/manufacturing/index.html` template.

Keep the existing route URL `/admin/manufacturing/` unchanged.

### B2 — Template redesign: `admin/manufacturing/index.html`

Replace the current three-card layout with a two-section accordion page.

**Page structure:**
```
Breadcrumb: Dashboard / Manufacturing
H1: Manufacturing

▼ [SECTION 1] Suspension (C.SLQ001)
   ┌── Production Lots panel (last 3 lots, quick status)
   └── Document tree (recursive accordion from suspension_root)

▼ [SECTION 2] ClearTract Foley Catheters
   └── Document tree (recursive accordion from cleartract_root)
```

**Section 1 — Suspension:**

Use `<details open>` so it starts expanded. Inside:

- A compact "Production Lots" row at the top:
  ```
  Production Lots:  Lot 2502-01-2 [Released]  Lot 2502-01-1 [Released]  Lot 2302-01-2 [Released]
  [View all lots →]
  ```
  Each lot number links to `manufacturing.suspension_detail`; "View all lots →" links
  to `manufacturing.suspension_list`. Admin users also see a small [+ New Lot] link.

- Then the full document tree rendered via the same recursive macro pattern as
  `accordion.html` (define the macro inline in this template or import it):
  `render_folder(suspension_root.id, depth=0)`.

  The accordion renders all descendant folders and files from the work_orders library
  using the `folders_by_id`, `children_by_parent`, `files_by_folder` data already
  loaded in the route. File view/download links use `admin_docs.admin_docs_document_view`
  and `admin_docs.admin_docs_document_download`.

**Section 2 — ClearTract Foley Catheters:**

Use `<details>` (starts collapsed). Inside:
- The full document tree from `cleartract_root` rendered the same way.

**Remove** the `cleartract_placeholder.html` template and the
`manufacturing.cleartract_placeholder` route — this page replaces it. Update any
`url_for('manufacturing.cleartract_placeholder')` references.

### B3 — Remove the stale Work Orders card from the Manufacturing index

The current `index.html` has a card linking to `admin_docs.work_orders`. This was the
"Work Orders" sub-card on the Manufacturing landing page. Remove it — the document
content is now embedded directly in the accordion sections.

---

## Task C — Coordinator-run script (gitignored): upload missing Manufacturing files

Write `scripts/_upload_manufacturing_files.py` to upload files present in the local
`Manufacturing/` folder that are either:
(a) A new lot not yet in the work_orders library, or
(b) Root-level product files (BOM, BOR) not yet uploaded.

**Specific files to upload:**

**New lot — SLQ-211610SPT, LotSLQ-05132026** (3 files):
Target folder in work_orders: inside `ClearTract Foley Catheters` → find the subfolder
whose name matches `"SLQ-211610SPT DHRs"` → create a new subfolder `"LotSLQ-05132026"`
inside it if it doesn't exist → upload these three files:
- `Manufacturing/ClearTract Foley Catheters/SLQ-211610SPT DHRs/LotSLQ-05132026/DHR_SLQ-211610SPT_Rev B_LN SLQ-05132026_Qty 1910.pdf`
- `Manufacturing/ClearTract Foley Catheters/SLQ-211610SPT DHRs/LotSLQ-05132026/OM.SLQ003 SLQ05132026.pdf`
- `Manufacturing/ClearTract Foley Catheters/SLQ-211610SPT DHRs/LotSLQ-05132026/OM.SLQ004 SLQ05132026.pdf`

**Suspension root files** (2 files — upload to the C.SLQ001 root folder in work_orders):
- `Manufacturing/C.SLQ001/BOM-C.SLQ001 C Bill of Materials, Suspension.xlsx`
- `Manufacturing/C.SLQ001/BOR-C.SLQ001 A Bill of Reference, Suspension.pptx`

Skip any file that already exists by filename in the target folder (idempotent).
Include standard DRY_RUN guard and --execute flag. Use S3 storage env vars as in
prior upload scripts.

---

## Task D — Update test fixtures

Remove the Work Orders dashboard card assertion from `tests/test_p23_operations.py`
(or wherever the dashboard test asserts its presence). Add:
- Dashboard: "Work Orders" card NOT present.
- Manufacturing index: contains `<details` (accordion sections present).
- Manufacturing index: "Production Lots" link present for admin user.
- Manufacturing index: "ClearTract Foley Catheters" `<details>` present.

---

## Deploy Discipline

- No migration. No new routes other than removal of `cleartract_placeholder`.
- Full test suite must pass. Single migration head unchanged. Import guard passes.
- After deploy: coordinator runs Task C script (dry-run then --execute).

---

## Deliverables

1. Work Orders card removed from dashboard Operations column.
2. Manufacturing landing page shows Suspension (open) + ClearTract (collapsed) accordions.
   Suspension panel includes last-3-lots quick view and "View all / New Lot" links.
3. ClearTract section renders full DHR / procedures / labeling / specs document tree.
4. `cleartract_placeholder` route and template deleted.
5. New LotSLQ-05132026 + Suspension BOM/BOR files uploaded via coordinator script.
6. Full suite green; coordinator confirms Manufacturing page on live site.
