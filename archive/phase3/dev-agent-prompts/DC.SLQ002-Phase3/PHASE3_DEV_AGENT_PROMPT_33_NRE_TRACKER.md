# Prompt 33 — NRE Projects: Invoice Tracker + Document Subfolders

## Context

The NRE Projects module (`/admin/nre_projects/`) currently shows a grid of NRE customer cards.
Clicking a customer opens their detail page, which lists their sales orders and lets you attach
PDFs to individual orders.

This prompt adds two things:

1. **NRE Invoice Tracker** — a new manual-entry card at the top of the NRE Projects index page,
   modelled exactly on the "Upcoming Payments" ledger in Purchasing.  Entries are entirely
   free-form (not auto-generated from sales orders).

2. **Per-order admin_docs subfolders** — every NRE customer gets a top-level folder in the
   `nre_projects` admin_docs library, and every one of their sales orders gets a subfolder
   inside it.  The customer detail page exposes a link into that subfolder so documents can be
   uploaded there.

The existing customer-cards grid and customer detail page must be **preserved unchanged**, except
for the subfolder links added to the detail page.

---

## Part A — Model migration

### A1. Alter `nre_project_entries` table

The current model has `sales_order_id NOT NULL` (required FK).  The tracker must support
free-form entries that are not necessarily tied to a specific sales order record.

Create a new Alembic migration `e1f2a3b4c5d6_nre_tracker_freeform.py` with `down_revision`
pointing at `c9d0e1f2a3b4`:

```python
def upgrade():
    op.alter_column("nre_project_entries", "sales_order_id", nullable=True)
    op.add_column("nre_project_entries", sa.Column("entry_date",  sa.Date(),   nullable=True))
    op.add_column("nre_project_entries", sa.Column("customer_name", sa.Text(), nullable=True))
    op.add_column("nre_project_entries", sa.Column("order_ref",   sa.Text(),   nullable=True))
    op.add_column("nre_project_entries", sa.Column("description", sa.Text(),   nullable=True))

def downgrade():
    op.drop_column("nre_project_entries", "description")
    op.drop_column("nre_project_entries", "order_ref")
    op.drop_column("nre_project_entries", "customer_name")
    op.drop_column("nre_project_entries", "entry_date")
    op.alter_column("nre_project_entries", "sales_order_id", nullable=False)
```

### A2. Update `NREProjectEntry` model (`app/eqms/modules/nre_projects/models.py`)

Add the four new fields and make `sales_order_id` nullable:

```python
sales_order_id: Mapped[int | None] = mapped_column(
    ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True, unique=False
)
entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
customer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
order_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
description: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Note: Remove `unique=True` from the FK mapping since entries are no longer 1-per-order;
the table's uniqueness constraint `uq_nre_project_entries_sales_order_id` must also be dropped
in the migration:
```python
op.drop_constraint("uq_nre_project_entries_sales_order_id", "nre_project_entries", type_="unique")
```
(add this line inside `upgrade()` before altering the column).

---

## Part B — NRE Invoice Tracker card on the index page

### B1. Index route (`app/eqms/modules/nre_projects/admin.py`)

In `nre_projects_index()`, load all tracker entries (most recent first) to pass to the template:

```python
tracker_entries = (
    s.query(NREProjectEntry)
    .filter(NREProjectEntry.sales_order_id.is_(None) | NREProjectEntry.sales_order_id.isnot(None))
    .order_by(NREProjectEntry.entry_date.desc().nullslast(), NREProjectEntry.created_at.desc())
    .all()
)
return render_template(
    "admin/nre_projects/index.html",
    nre_customers=nre_customers,
    order_counts=order_counts,
    tracker_entries=tracker_entries,
    invoice_statuses=INVOICE_STATUSES,
)
```

(Simplified: `s.query(NREProjectEntry).order_by(NREProjectEntry.created_at.desc()).all()`)

### B2. New CRUD routes for the tracker

Add the following routes to `admin.py` (replace the old `nre_tracker_upsert` and
`nre_tracker_patch` routes that required a `customer_id` or `sales_order_id`; keep
`nre_tracker_patch` and `nre_tracker_delete` but update them to handle the new fields):

#### Create  `POST /tracker/create`
```python
@bp.post("/tracker/create")
@require_permission("sales_orders.edit")
def nre_tracker_create():
```
Accepts JSON or form data with keys: `entry_date`, `customer_name`, `order_ref`,
`description`, `invoice_amount`, `expected_invoice_date`, `invoice_status`, `notes`.
Creates a new `NREProjectEntry` (all fields nullable).
Returns `{"ok": True, "entry": {...}}` with the full entry dict.

The `_entry_to_dict` helper must be extended to include the four new fields.

#### Update  `PATCH /tracker/<int:entry_id>` — keep existing route, extend `_apply_entry_fields`
The `_apply_entry_fields` helper must accept and persist `entry_date`, `customer_name`,
`order_ref`, `description` in addition to the existing fields.

#### Delete  `DELETE /tracker/<int:entry_id>` — unchanged.

### B3. Template — add tracker card to `app/eqms/templates/admin/nre_projects/index.html`

Insert a new card **above** the existing customer-cards section.  Model it on the
"Upcoming Payments" card in `app/eqms/templates/admin/purchasing/list.html`.

**Columns:**

| Column | Input type | Width |
|---|---|---|
| Date | `<input type="date">` | 120px |
| Customer | `<input type="text">` | 160px |
| Project / Order Ref | `<input type="text">` | 140px |
| Description | `<input type="text">` | flex |
| Invoice Amount | `<input type="text">` | 110px |
| Expected Invoice Date | `<input type="date">` | 120px |
| Status | `<select>` (INVOICE_STATUSES) | 130px |
| Notes | `<input type="text">` | 160px |
| Actions | edit / save / cancel / delete | 120px |

**Behaviour (identical to Upcoming Payments):**
- Rows render in read-only view mode by default.
- Edit button (`✎`) switches a row to edit mode (show inputs, hide spans).
- Save button posts a PATCH to `/admin/nre_projects/tracker/<id>`.
- Cancel button restores read-only mode without saving.
- Delete button (✕) sends a DELETE to `/admin/nre_projects/tracker/<id>` and removes the row.
- "+ Add Entry" button appends a new blank editable row; on Save it POSTs to
  `/admin/nre_projects/tracker/create`.  On success the new row's `data-id` is populated from
  the response.

**Status color-coding** (left border on the status `<select>` or status badge in read mode):
- Pending Invoice → amber `#9a6700`
- Invoiced → blue `#0d6efd`
- Paid → green `#198754`
- Cancelled → gray `#6c757d`

**CSRF:** Use the meta tag (`document.querySelector('meta[name="csrf-token"]')`) for all
fetch calls, exactly as in the purchasing payments JavaScript.

**Empty state:** If `tracker_entries` is empty, show a muted "No invoice entries yet." line
inside the table body (do not hide the table header).

The tracker card header:
```html
<h2 style="margin:0;">NRE Invoice Tracker</h2>
```
No subtitle / description line.

After the tracker card, render the existing customer-cards grid exactly as before.

---

## Part C — Per-order admin_docs subfolders

### C1. Scaffold on "Refresh Folders"

The existing `nre_refresh_folders` POST route in `admin.py` (and the `_scaffold_nre_folders.py`
coordinator script) should create the following folder structure in the `nre_projects`
admin_docs library:

```
nre_projects/
  <Customer Facility Name>/          ← AdminDocFolder, parent=None
    SO-<order_number>/               ← AdminDocFolder, parent=customer folder
    SO-<order_number>/
    ...
  <Customer Facility Name>/
    ...
```

The route must be **idempotent** — re-running it must not create duplicate folders.
Look up or create each folder by `(library_key, parent_id, name)`.

The scaffold should run against **all current NRE customers** (as returned by `_nre_customers`),
not only customers in the admin_docs table.

### C2. Customer detail page — subfolder links

In `app/eqms/templates/admin/nre_projects/detail.html`, the code to find per-order folder IDs
and render "📁 Docs" links is already present inside the Project Tracker section.

Ensure the same folder-lookup logic also renders a "📁 Documents" link in the **Sales Orders**
section (below the Project Tracker card), next to the existing "+ Upload PDF" button for each
order.  If a subfolder exists for that sales order, show:
```html
<a href="{{ url_for('admin_docs.nre_project_docs', folder_id=order_folder_ids[order.id]) }}"
   class="button button--secondary" style="font-size:12px; padding:6px 12px;">
  📁 Documents
</a>
```
If no subfolder exists yet, show a small muted hint: "Run Refresh Folders to create."

The route `admin_docs.nre_project_docs` is already registered in
`app/eqms/modules/admin_docs/admin.py`; confirm it exists and creates it if missing.

---

## Part D — Register the new route in `__init__.py` / blueprint

The new route `nre_tracker_create` is on the `nre_projects` blueprint, which is already
registered.  Confirm the blueprint `url_prefix` is `/admin/nre_projects` so that
`POST /admin/nre_projects/tracker/create` resolves correctly with `url_for('nre_projects.nre_tracker_create')`.

---

## Commit

Single commit message:
```
P33: NRE Invoice Tracker (free-form ledger) + per-order document subfolders
```

Then push to `main`.

---

## Reference: existing NRE customers and sales orders (as of 2026-07-15)

These were the NRE customers and their SOs at time of writing.  The scaffold and tracker
columns are designed around this data:

| Customer | Sales Orders |
|---|---|
| AbbVie Inc. | SO-0000151 |
| Advanced Bionics GmbH | SO-0000315, SO-0000173, SO-0000160 |
| Aspero Medical Inc. | SO-0000288 |
| Boston Scientific Corporation | SO-0000303, SO-0000187 |
| Childrens Hospital of Orange County | SO-0000228, SO-0000147 |
| Fearsome Limited | SO-0000289, SO-0000207 |
| Hybron Technologies | SO-0000274 |
| Momentum LLC | SO-0000276 |
| Neptune | SO-0000294 |
| New World Medical | SO-0000214, SO-0000181, SO-0000163 |
| Pathway Medtech | SO-0000170 |
| Richman Chemical Inc | SO-0000322 |
| Supira Medical | SO-0000281 |
| Scionti Prostate Center | SO-0000202 |
| Tingo Medical LTD | SO-0000154 |
