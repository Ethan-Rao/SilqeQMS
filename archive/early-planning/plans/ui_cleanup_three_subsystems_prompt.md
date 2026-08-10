# Dev Agent Prompt — UI Cleanup: Three Subsystems

## Project Context

You are working on **SilqQMS**, a Flask/Python 3.12 app with server-rendered Jinja2 templates. The production app is at `https://silqeqms.com`, hosted on **DigitalOcean App Platform** connected to `https://github.com/Ethan-Rao/SilqeQMS.git`. Commits pushed to `main` automatically deploy to production.

Read every file fully before modifying it. Make no changes outside the files listed for each subsystem.

---

## Subsystem 1 — Purchasing List (`purchasing/list.html`)

### File to modify
`app/eqms/templates/admin/purchasing/list.html`

### Problems being fixed
1. No navigation back to Admin
2. When no status filter is active, open POs appear in **both** "Open purchase orders" AND "All purchase orders" — the same records are listed twice, creating confusion about counts
3. Status values (`pending`, `partial`, `received`, `cancelled`) are raw database strings — not visually distinct
4. The "View" link in the Actions column is redundant — the PO number is already a link to the same page
5. Search placeholder says "PO number..." but supplier is also useful to search — wording is limiting

### Changes to make

**1. Add a back link to the header.**

In the header card's action row (the `<div style="display:flex; gap:10px;">` that currently holds "New PO" and "Import PDF"), add a back link as the first element:

```html
<a class="button button--secondary" href="{{ url_for('admin.index') }}">← Back to Admin</a>
```

**2. Remove the "Open purchase orders" section entirely.**

Delete the entire `{% if show_open_section %}` block — the spacer div, the card with heading "Open purchase orders", and its table. This removes the duplication. Open orders will still be visible in the "All purchase orders" table; the status badge changes below will make them stand out visually.

**3. Add status badges to the "All purchase orders" table.**

In both tables (only one will remain after step 2), replace the plain `{{ po.status|e }}` status cell with a colored inline badge. Apply this pattern everywhere status is displayed:

```html
{% if po.status == 'pending' %}
  <span style="font-size:11px; padding:3px 9px; border-radius:4px; background:rgba(245,158,11,0.15); color:#f59e0b; font-weight:600;">Pending</span>
{% elif po.status == 'partial' %}
  <span style="font-size:11px; padding:3px 9px; border-radius:4px; background:rgba(102,163,255,0.15); color:var(--primary); font-weight:600;">Partial</span>
{% elif po.status == 'received' %}
  <span style="font-size:11px; padding:3px 9px; border-radius:4px; background:rgba(61,220,151,0.15); color:var(--success); font-weight:600;">Received</span>
{% elif po.status == 'cancelled' %}
  <span style="font-size:11px; padding:3px 9px; border-radius:4px; background:rgba(255,255,255,0.05); color:var(--muted);">Cancelled</span>
{% else %}
  <span style="font-size:11px; padding:3px 9px; border-radius:4px; background:rgba(255,255,255,0.05); color:var(--muted);">{{ po.status|e }}</span>
{% endif %}
```

**4. Remove the redundant "View" link.**

In the Actions column, remove the `<a href="...">View</a>` link — the PO number in the first column already links to the detail page. Keep the "Edit" link. The result:

```html
<td>
  <a href="{{ url_for('purchasing.purchasing_edit_get', po_id=po.id) }}" style="font-size:13px;">Edit</a>
</td>
```

**5. Add a count summary below the table heading.**

After `<h2 style="margin-top:0;">All purchase orders</h2>`, add:

```html
{% set open_count = purchase_orders | selectattr('status', 'in', ['pending', 'partial']) | list | length %}
{% if open_count > 0 and not status_filter %}
  <p class="muted" style="margin-top:0; font-size:12px;">{{ open_count }} open (pending or partial) · {{ purchase_orders|length }} total</p>
{% else %}
  <p class="muted" style="margin-top:0; font-size:12px;">{{ purchase_orders|length }} result{{ 's' if purchase_orders|length != 1 else '' }}</p>
{% endif %}
```

**6. Update the search placeholder** from `"PO number..."` to `"PO number or supplier..."`.

---

## Subsystem 2 — Audit Trail (`audit/list.html`)

### File to modify
`app/eqms/templates/admin/audit/list.html`

### Problems being fixed
1. No result count — users don't know how many events matched or if they hit the silent 500-row cap
2. The "Action contains" field is a free-text input with a technical example in the placeholder — non-technical users don't know what action codes look like
3. The Entity column is plain text — no links to the referenced record even when the entity is a navigable model with a known numeric ID
4. Table styling is inconsistent with newer pages (no border-bottom on header row, plain padding, no row hover distinction)

### Changes to make

**1. Add a result count + truncation warning above the table.**

Between the filter card and the table card, insert:

```html
{% if events %}
  <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; font-size:13px; color:var(--muted);">
    <span>{{ events|length }} event{{ 's' if events|length != 1 else '' }} found
      {% if events|length == 500 %}<span style="color:#f59e0b; margin-left:8px;">⚠ Limit of 500 reached — refine your filters to see more</span>{% endif %}
    </span>
  </div>
{% endif %}
```

Place this between the existing `<div style="height: 14px;"></div>` and the table `<div class="card">`.

**2. Add an action reference helper below the action filter input.**

Immediately after the `<input name="action" ...>` element, add a collapsible hint:

```html
<details style="margin-top:4px;">
  <summary style="font-size:11px; color:var(--muted); cursor:pointer; list-style:none;">Common action codes ▾</summary>
  <div style="font-size:11px; color:var(--muted); margin-top:6px; line-height:1.9;">
    <code>sales_dashboard.view</code> · <code>sales_dashboard.export</code><br>
    <code>distribution_log_entry.create</code> · <code>distribution_log_entry.edit</code><br>
    <code>customer.edit</code> · <code>customer.note.add</code><br>
    <code>purchasing.create</code> · <code>purchasing.edit</code><br>
    <code>equipment.create</code> · <code>equipment.edit</code><br>
    <code>sales_orders.import</code> · <code>document.view</code>
  </div>
</details>
```

**3. Add entity deep-links in the Entity column.**

Replace the current entity cell content with a version that creates a clickable link when the entity type is a known navigable model and the entity ID is a valid positive integer. Use `namespace` to avoid Jinja2 scoping issues. Apply this logic:

```html
<td style="padding: 8px 12px;">
  {% if e.entity_type and e.entity_id %}
    {% set eid = e.entity_id | int(default=0) %}
    {% if eid > 0 %}
      {% if e.entity_type == 'Customer' %}
        <a href="{{ url_for('customer_profiles.customer_detail', customer_id=eid) }}" style="font-size:12px;">{{ e.entity_type }} #{{ e.entity_id }}</a>
      {% elif e.entity_type == 'DistributionLogEntry' %}
        <a href="{{ url_for('rep_traceability.distribution_log_edit_get', entry_id=eid) }}" style="font-size:12px;">{{ e.entity_type }} #{{ e.entity_id }}</a>
      {% elif e.entity_type == 'PurchaseOrder' %}
        <a href="{{ url_for('purchasing.purchasing_detail', po_id=eid) }}" style="font-size:12px;">{{ e.entity_type }} #{{ e.entity_id }}</a>
      {% elif e.entity_type == 'SalesOrder' %}
        <a href="{{ url_for('rep_traceability.sales_order_detail', order_id=eid) }}" style="font-size:12px;">{{ e.entity_type }} #{{ e.entity_id }}</a>
      {% elif e.entity_type == 'Equipment' %}
        <a href="{{ url_for('equipment.equipment_detail', equipment_id=eid) }}" style="font-size:12px;">{{ e.entity_type }} #{{ e.entity_id }}</a>
      {% else %}
        <span style="font-size:12px;">{{ e.entity_type }} #{{ e.entity_id }}</span>
      {% endif %}
    {% else %}
      <span style="font-size:12px; color:var(--muted);">{{ e.entity_type }}{% if e.entity_id %} · {{ e.entity_id }}{% endif %}</span>
    {% endif %}
  {% else %}
    <span class="muted">—</span>
  {% endif %}
</td>
```

**4. Update the table header row styling** to be consistent with the rest of the app:

Replace the current `<thead><tr>` with:

```html
<thead>
  <tr style="border-bottom:2px solid var(--border);">
    <th style="text-align:left; padding:10px 12px; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted);">Time</th>
    <th style="text-align:left; padding:10px 12px; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted);">Actor</th>
    <th style="text-align:left; padding:10px 12px; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted);">Action</th>
    <th style="text-align:left; padding:10px 12px; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted);">Entity</th>
    <th style="text-align:left; padding:10px 12px; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted);">Reason</th>
    <th style="text-align:left; padding:10px 12px; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted);">Details</th>
  </tr>
</thead>
```

And update each `<td>` in the body rows from `style="padding: 8px;"` to `style="padding: 10px 12px; font-size:13px;"`. Update the `<tr>` style from `style="border-top: 1px solid var(--border);"` to `style="border-bottom:1px solid rgba(255,255,255,0.05);"`.

---

## Subsystem 3 — Customer Detail (`customers/detail.html`)

### File to modify
`app/eqms/templates/admin/customers/detail.html`

### Problems being fixed
1. **Primary Rep name displays as numeric ID** — a Jinja2 scoping bug where `{% set rep_name = '' %}` set inside a `{% for %}` loop does not update the outer scope variable, so `rep_name` is always `''` outside the loop and the fallback `customer.primary_rep_id` (an integer) is shown instead of the rep's name
2. **"Edit" is a navigation tab** — mixing navigation with an edit form is an unusual, cluttered UX pattern. The Edit tab wastes one of five tab slots; editing should be accessed via a dedicated button in the page header
3. **Notes deletion has no confirmation** — one misclick permanently deletes a note with no warning
4. **Distributions tab is missing context** — users comparing the "Distributions" tab count against the Overview stat cards may be confused because the stats are computed from matched distributions only, while the tab shows all distributions

### Changes to make

**1. Fix the Primary Rep name bug using Jinja2 `namespace`.**

Find this block (lines ~114–125) in the Contact & Location card:

```jinja2
{% if customer.primary_rep_id %}
  <dt>Primary Rep</dt>
  <dd>
    {% set rep_name = '' %}
    {% for r in reps or [] %}
      {% if r.id == customer.primary_rep_id %}
        {% set rep_name = r.name %}
      {% endif %}
    {% endfor %}
    {{ rep_name if rep_name else customer.primary_rep_id }}
  </dd>
{% endif %}
```

Replace it with:

```jinja2
{% if customer.primary_rep_id %}
  <dt>Primary Rep</dt>
  <dd>
    {% set ns = namespace(rep_name='') %}
    {% for r in reps or [] %}
      {% if r.id == customer.primary_rep_id %}
        {% set ns.rep_name = r.name %}
      {% endif %}
    {% endfor %}
    {{ ns.rep_name if ns.rep_name else customer.primary_rep_id }}
  </dd>
{% endif %}
```

**2. Remove the "Edit" tab from the tab navigation bar and add an Edit button to the page header instead.**

In the tab bar (the `<div class="card" style="padding:0; display:flex; gap:0; overflow:hidden;">` block), remove the Edit tab link entirely — the `<a href="...?tab=edit">Edit</a>` entry. The tab bar should have four tabs only: Overview, Sales Orders, Distributions, Notes.

In the page header (the `<div style="display:flex; gap:10px; flex-wrap:wrap;">` that contains "← Back to List" and "+ Add Note"), add an Edit button as the third element:

```html
{% if customer %}
  <a class="button button--secondary" href="{{ url_for('customer_profiles.customer_detail', customer_id=customer.id) }}?tab=edit">Edit Customer</a>
{% endif %}
```

The edit form content (`{% elif tab == 'edit' %}` block) stays in place — only the tab navigation entry is removed and the header button is added.

**3. Add a delete confirmation to note delete buttons.**

Find the note delete form submit button in the Notes tab:

```html
<button class="button button--secondary" type="submit" style="font-size:12px; padding:6px 10px; color:var(--danger);">Delete</button>
```

Add an `onclick` confirmation:

```html
<button class="button button--secondary" type="submit" style="font-size:12px; padding:6px 10px; color:var(--danger);" onclick="return confirm('Delete this note? This cannot be undone.');">Delete</button>
```

**4. Add a clarifying subtitle to the Distributions tab.**

The Distributions tab card has `<h2 style="margin-top:0; font-size:16px;">All Distributions</h2>`. Change the heading and add an explanatory subtitle:

```html
<h2 style="margin-top:0; font-size:16px;">All Distributions</h2>
<p class="muted" style="margin-top:-8px; font-size:12px;">All shipment records linked to this customer. Note: Overview stats reflect matched orders only.</p>
```

Also add a "View in Distribution Log →" link after the heading area, giving admins a quick way to navigate to the full filtered view:

```html
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
  <div>
    <h2 style="margin-top:0; margin-bottom:4px; font-size:16px;">All Distributions</h2>
    <p class="muted" style="margin:0; font-size:12px;">All shipment records linked to this customer. Overview stats reflect matched orders only.</p>
  </div>
  <a class="button button--secondary" style="font-size:12px; white-space:nowrap;" href="{{ url_for('rep_traceability.distribution_log_list', q=customer.facility_name) }}">View in Distribution Log →</a>
</div>
```

Remove the old standalone `<h2>All Distributions</h2>` line after making this change.

---

## Commit and Deploy

After completing all three subsystems, commit and push:

```bash
git add app/eqms/templates/admin/purchasing/list.html
git add app/eqms/templates/admin/audit/list.html
git add app/eqms/templates/admin/customers/detail.html
git commit -m "feat(ui): purchasing dedup+badges, audit deep-links+count, customer detail rep fix"
git push origin main
```

DigitalOcean App Platform will automatically deploy on push to `main`.
