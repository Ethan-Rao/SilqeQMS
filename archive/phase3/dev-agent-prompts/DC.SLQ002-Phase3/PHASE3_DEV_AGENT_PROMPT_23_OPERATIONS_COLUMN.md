# Phase 3 — Prompt 23: Operations Column — Accordion + Reorganisation

## Context

Applies the same improvements made to the Quality Management column to the
Silq Operations column. Three task groups: accordion views for file libraries,
dashboard restructure, and a consolidated Training card.

---

## Task A — Accordion view for three Operations libraries

Add three library keys to `ACCORDION_LIBRARIES` in
`app/eqms/modules/admin_docs/admin.py`:

```python
ACCORDION_LIBRARIES: frozenset[str] = frozenset({
    "management_reviews",
    "post_market_surveillance",
    "risk_management",
    "dhfs",
    "work_orders",       # add
    "employee_training", # add
    "ncrs",              # add
})
```

No template changes needed — `accordion.html` is already generic. The three
libraries each have different characteristics; confirm the accordion renders
correctly for each:

- **work_orders**: 43 folders / 117 files, up to 4 levels deep
  (e.g. Work Orders → ClearTract Foley Catheters → SLQ-211410SPT → LotXXX).
  Confirm the recursive macro handles depth ≥ 3 without visual overflow.
- **employee_training**: 10 folders / 193 files, 2 levels
  (Employee Training → PersonName → files). Confirm per-person folders expand cleanly.
- **ncrs**: 1 root folder + 5 year subfolders / 1 file. Confirm year folders render.

Tests to add (in `tests/test_p23_operations.py`):
- `GET /admin/work-orders` returns 200 and contains `<details` for admin + staff.
- `GET /admin/employee-training` returns 200 and contains `<details` for admin + staff.
- `GET /admin/ncrs` returns 200 and contains `<details` for admin + staff.

---

## Task B — Dashboard: Silq Operations column restructure

Replace the Operations column block in `index.html` with the new card order below.
Two changes from the current layout:
1. **Work Orders card added** (currently no dashboard card despite being a populated
   library — linked from the Manufacturing module only).
2. **Cards reordered** so the most-used operational tools appear first.
3. **"My Training" and "Training Assignments" consolidated** into a single
   **"Training"** card (see design below).

### New Operations column order (7 cards):

```
1. Manufacturing        → url_for('manufacturing.manufacturing_index')
2. Work Orders          → url_for('admin_docs.work_orders')          [NEW]
3. Equipment            → url_for('equipment.equipment_list')
4. Purchasing           → url_for('purchasing.purchasing_list')
5. Supplies             → url_for('supplies.supplies_list')
6. NCRs                 → url_for('admin_docs.ncrs')
7. Employee Training    → url_for('admin_docs.employee_training')
8. Training             → [see B1 below]
```

### B1 — Consolidated Training card

Replace the two separate "My Training" and "Training Assignments" cards with a single
**"Training"** card. The link destination depends on the viewer's permissions:

- If `has_perm("training.manage")` (admin): link to `training.manage_index`
  (the assignment overview), description: "Assign training and track team completion"
- Else if `has_perm("training.view")` (staff): link to `training.my_training`,
  description: "Your read-and-acknowledge training queue"

In Jinja2:
```html
{% if has_perm("training.view") or has_perm("training.manage") %}
<a class="card card--link dash-card" href="{{ url_for('training.manage_index') if has_perm('training.manage') else url_for('training.my_training') }}">
  <h3 class="dash-card-title">Training</h3>
  <p class="muted dash-card-desc">
    {% if has_perm('training.manage') %}Assign training and track team completion
    {% else %}Your read-and-acknowledge training queue{% endif %}
  </p>
</a>
{% endif %}
```

The My Training page (`/admin/my-training`) and Training Assignments page
(`/admin/training`) themselves are unchanged — only the dashboard card consolidates
them. Admins can still navigate to My Training from within the Training Assignments
page if needed; add a "My Training →" quick link to the top of the training manage
page if it isn't already there.

### B2 — Work Orders card text

```html
<h3 class="dash-card-title">Work Orders</h3>
<p class="muted dash-card-desc">Manufacturing procedures, DHRs, and lot documentation</p>
```

---

## Task C — Work Orders library: pre-open root folder in accordion

The Work Orders library has a single top-level root folder called "Work Orders" that
contains everything. In the current accordion template, root-level `<details>` are not
pre-opened. Add a small UX improvement: if a library has **exactly one root-level
folder** and **zero root-level files**, automatically set `open` on that single root
`<details>` so the user isn't greeted with a single collapsed line. This applies
specifically to work_orders today, but the logic is generic enough to help any library
with the same structure.

Implement in the template: check `children_by_parent[None] | length == 1 and
files_by_folder.get(None, []) | length == 0` and conditionally add `open` to the first
root-level `<details>`.

---

## Task D — Employee Training accordion: add a "Search by person" hint

The employee_training library is structured as one folder per employee. In the accordion
view it shows all employees collapsed. Since staff users can only VIEW (not upload), and
they will typically be looking for their own folder, add a small hint line below the
search box:
"Tip: Search by employee name to jump directly to their folder."

This is a template-only note inside the accordion template when `library_key ==
"employee_training"` (use a Jinja2 `{% if library_key == "employee_training" %}` block).

---

## Deploy Discipline

- No migrations.
- Full test suite must pass (add `tests/test_p23_operations.py`).
- Single migration head unchanged. Import guard passes.

Additional tests:
- Dashboard: "Work Orders" card is present in the response for admin users.
- Dashboard: "My Training" and "Training Assignments" cards are NOT present separately
  (replaced by single "Training" card).
- Dashboard: "Training" card link is `manage_index` for admin, `my_training` for staff
  (can test both with the existing admin + staff test fixtures).
- Dashboard: "Work Orders" card appears before "NCRs" card in the response.

---

## Deliverables

1. Work Orders, Employee Training, and NCRs all render full-tree accordion views.
2. Dashboard Operations column: 8 cards in new order (Manufacturing, Work Orders,
   Equipment, Purchasing, Supplies, NCRs, Employee Training, Training).
3. Work Orders accordion auto-opens its single root folder.
4. Employee Training accordion shows search hint.
5. Full suite green; coordinator confirms the four affected library pages and the
   updated dashboard column on the live site.
