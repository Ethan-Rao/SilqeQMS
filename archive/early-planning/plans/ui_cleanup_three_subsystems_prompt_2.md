# Dev Agent Prompt — UI Cleanup: Three More Subsystems

## Project Context

You are working on **SilqQMS**, a Flask/Python 3.12 app with server-rendered Jinja2 templates. Production is at `https://silqeqms.com`, auto-deployed on push to `main` at `https://github.com/Ethan-Rao/SilqeQMS.git`.

Read every file fully before modifying it. Do not modify files outside those listed for each subsystem.

---

## Subsystem 1 — Customers List

### Files to modify
- `app/eqms/templates/admin/customers/list.html`
- `app/eqms/modules/customer_profiles/admin.py`

### Problems being fixed
1. **No back link** — the header has no way to return to the Admin dashboard
2. **Year filter hardcoded to 2025/2026** — it will be wrong every year and is currently missing years before 2025
3. **Client-side sort is misleading** — sorting column headers only re-orders the current page of 50, not the full dataset; users naturally expect a column sort to sort everything, which it silently does not
4. **Pagination shows no page number** — the footer card shows "Showing 1–50 of 120" but no "Page X of Y"

### Changes to make

**1a. Python route — make year filter dynamic.**

In `customer_profiles/admin.py`, find the `customers_list()` route function. Read it fully. Near the top of the function, after the database session is established, add a query to compute the distinct years with distribution activity:

```python
from sqlalchemy import extract as sa_extract
from app.eqms.modules.rep_traceability.models import DistributionLogEntry

year_rows = (
    s.query(sa_extract("year", DistributionLogEntry.ship_date).label("yr"))
    .filter(DistributionLogEntry.ship_date.isnot(None))
    .distinct()
    .order_by(sa_extract("year", DistributionLogEntry.ship_date).desc())
    .all()
)
available_years = [int(r.yr) for r in year_rows if r.yr]
```

Then add `available_years=available_years` to the `render_template()` call at the end of the function.

**1b. Template — update the year filter dropdown.**

Replace the hardcoded year options:

```html
<option value="2026" ...>2026</option>
<option value="2025" ...>2025</option>
```

with a dynamically generated list from `available_years`:

```html
{% for y in available_years|default([]) %}
  <option value="{{ y }}" {% if year == y|string %}selected{% endif %}>{{ y }}</option>
{% endfor %}
```

**1c. Template — remove the client-side sort.**

The client-side sort reorders only the current page of 50 rows, not the full dataset. This is misleading. Remove it entirely:

- Remove `id="customersTable"` from the `<table>` element
- Change all five `<th class="sortable" data-sort="..." style="...cursor:pointer;">` elements to plain headers without `class="sortable"`, without `data-sort`, and without `cursor:pointer` in their inline style. Remove the `<span class="sort-icon">↕</span>` from each header
- Remove the `data-facility`, `data-location`, `data-orders`, `data-units`, `data-lastorder` attributes from all `<tr>` elements in the `<tbody>`
- Delete the entire `<script>` block at the bottom of the file (the IIFE that attaches click listeners)

**1d. Template — add back link and page number.**

In the header card action row (`<div style="display:flex; gap:10px;">`), add a back link as the first element before "+ New Customer":

```html
<a class="button button--secondary" href="{{ url_for('admin.index') }}">← Back to Admin</a>
```

In the pagination footer card, change the muted range text to include the page number:

```html
<div class="muted" style="font-size:12px;">
  Page {{ page }} · Showing {{ ((page - 1) * 50) + 1 }}–{{ [page * 50, total]|min }} of {{ total }} customers
</div>
```

Also make the pagination footer card always visible (even on page 1 with no prev/next), so the total count is always shown. Currently the pagination card is always rendered, so just ensure the range text is present regardless of `has_prev`/`has_next`.

---

## Subsystem 2 — Sales Orders List

### Files to modify
- `app/eqms/templates/admin/sales_orders/list.html`
- `app/eqms/modules/rep_traceability/admin.py`

### Problems being fixed
1. **Order number is not clickable** — displayed as plain `<code>` text; every other list in the app makes the primary identifier a direct link to the detail page
2. **Two redundant action buttons per row** — "Details" (modal) and "View" (full page) both appear. The modal partially duplicates the full page with no link to navigate there. Two options for one record creates unnecessary decision friction
3. **No status filter** — the Status column shows colored badges but the filter form has no Status field, so users cannot filter to e.g. all `pending` orders
4. **Result count hidden on single-page results** — the pagination card only renders when `total_pages > 1`, so on a single-page view there is no count indicator at all
5. **Customer name truncated without ellipsis** — `facility_name[:40]` cuts names abruptly with no visual indication of truncation

### Changes to make

**2a. Python route — add status filter.**

In `rep_traceability/admin.py`, find the `sales_orders_list()` function. Read the full function. After parsing the existing filter parameters (`source`, `customer_id`, `start_date`, `end_date`, `search`), add:

```python
status_filter = normalize_text(request.args.get("status")) or ""
```

In the section that builds the SQLAlchemy query, add a filter for status when it is provided. Find the block that applies `source` and other filters and add:

```python
if status_filter:
    q = q.filter(SalesOrder.status == status_filter)
```

Add `status_filter=status_filter` to the `render_template()` call. Also ensure the existing `filters` dict passed to the template includes `status_filter` or pass it separately — look at how `filters` is constructed and add `"status": status_filter` to it so the template can read `filters.status`.

**2b. Template — make order number a link and remove the redundant Details button.**

In the `<tbody>` row, change the Order # cell from:

```html
<td style="padding:10px 12px;"><code style="font-size:12px; font-weight:600;">{{ o.order_number }}</code></td>
```

to:

```html
<td style="padding:10px 12px;">
  <a href="{{ url_for('rep_traceability.sales_order_detail', order_id=o.id) }}" style="font-weight:600;">
    <code style="font-size:12px;">{{ o.order_number }}</code>
  </a>
</td>
```

In the actions column, remove the "Details" modal button entirely. Keep only the "View" link:

```html
<td style="padding:10px 12px; text-align:center;">
  <a class="button button--secondary" style="padding:4px 10px; font-size:11px;" href="{{ url_for('rep_traceability.sales_order_detail', order_id=o.id) }}">View</a>
</td>
```

Remove the `<dialog id="order-details-modal">` element and the entire `<script>` block containing `showOrderDetails()` — they are no longer needed.

**2c. Template — add status filter to the filter form.**

In the filter form's grid, add a new Status field after the existing Search field:

```html
<div>
  <div class="label">Status</div>
  <select name="status" style="width:100%; padding:10px 12px; border-radius:10px; border:1px solid var(--border); background:rgba(0,0,0,0.25); color:var(--text);">
    <option value="">All Statuses</option>
    <option value="pending"   {% if filters.status == 'pending' %}selected{% endif %}>Pending</option>
    <option value="shipped"   {% if filters.status == 'shipped' %}selected{% endif %}>Shipped</option>
    <option value="completed" {% if filters.status == 'completed' %}selected{% endif %}>Completed</option>
    <option value="cancelled" {% if filters.status == 'cancelled' %}selected{% endif %}>Cancelled</option>
  </select>
</div>
```

Also ensure the "Clear" link passes `status=` as empty (it should already clear by navigating to the base URL, so no change needed there).

**2d. Template — always show result count.**

Above the results table card (after the filter card and its spacer), always show a result count line:

```html
<div class="muted" style="font-size:12px; padding: 0 4px;">
  {{ total }} order{{ 's' if total != 1 else '' }}{% if total_pages > 1 %} · Page {{ page }} of {{ total_pages }}{% endif %}
</div>
<div style="height: 8px;"></div>
```

Place this between the `<div style="height: 14px;"></div>` after the filter card and the results `<div class="card">`.

Remove or leave the existing `{% if total_pages > 1 %}` pagination footer block at the bottom as-is — it still serves navigation purposes when there are multiple pages.

**2e. Template — fix customer name truncation.**

In the Customer column cell:

```html
<a href="..." style="font-weight:500;">{{ o.customer.facility_name[:40] }}</a>
```

Change to:

```html
<a href="..." style="font-weight:500; display:inline-block; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; vertical-align:bottom;">{{ o.customer.facility_name|e }}</a>
```

Apply the same change to the customer dropdown `[:40]` truncation in the filter form — change `{{ c.facility_name[:40] }}` to `{{ c.facility_name|e }}`.

---

## Subsystem 3 — Distribution Log

### File to modify
`app/eqms/templates/admin/distribution_log/list.html`

### Problems being fixed
1. **"Upload Sales Orders" and "Upload Packing Slips" header buttons are clutter** — both are navigation links to the same route (`sales_orders_import_pdf_get`), only differentiated by a hash anchor. PDF imports are an admin workflow that belongs under Admin Tools → Data Uploads, not cluttering the distribution log header with five competing buttons
2. **No page number in pagination** — the pagination footer shows "Showing X–Y of Z" but not which page number the user is on
3. **No CSV import shortcut** — importing distributions from CSV is a common operation but is only accessible via Admin Tools → Import CSV (Distributions), requiring extra navigation; a direct link in the distribution log header closes the workflow gap

### Changes to make

**3a. Remove the two upload buttons from the header.**

In the header action row, delete these two lines:

```html
<a class="button" href="{{ url_for('rep_traceability.sales_orders_import_pdf_get') }}">Upload Sales Orders</a>
<a class="button button--secondary" href="{{ url_for('rep_traceability.sales_orders_import_pdf_get') }}#packing-slips">Upload packing slips</a>
```

**3b. Add Import CSV link to the header.**

In the same header action row, add an "Import CSV" link after the Export button and before "+ New Entry":

```html
<a class="button button--secondary" href="{{ url_for('rep_traceability.distribution_log_import_get') }}">Import CSV</a>
```

The final header action row should contain (in order): `← Back`, `Export`, `Import CSV`, `+ New Entry`.

**3c. Add page number to the pagination footer.**

The current pagination card shows:

```html
<div class="muted" style="font-size:12px;">
  Showing {{ ((page - 1) * per_page) + 1 }}–{{ [page * per_page, total]|min }} of {{ total }} entries
</div>
```

Change to:

```html
<div class="muted" style="font-size:12px;">
  Page {{ page }} · Showing {{ ((page - 1) * per_page) + 1 }}–{{ [page * per_page, total]|min }} of {{ total }} entries
</div>
```

---

## Commit and Deploy

After completing all three subsystems, commit and push:

```bash
git add app/eqms/templates/admin/customers/list.html
git add app/eqms/modules/customer_profiles/admin.py
git add app/eqms/templates/admin/sales_orders/list.html
git add app/eqms/modules/rep_traceability/admin.py
git add app/eqms/templates/admin/distribution_log/list.html
git commit -m "feat(ui): customers sort/year fix, sales orders clickable+status filter, distlog header cleanup"
git push origin main
```

DigitalOcean App Platform will automatically deploy on push to `main`.
