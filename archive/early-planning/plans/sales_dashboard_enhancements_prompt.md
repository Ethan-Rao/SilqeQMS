# Dev Agent Prompt — Sales Dashboard Enhancements

## Context: Project Overview

You are working on **SilqQMS**, a Flask-based eQMS (Electronic Quality Management System) for a medical device company. The stack is:

- **Backend**: Python 3.12, Flask 3.1.2, SQLAlchemy 2.0, PostgreSQL (prod) / SQLite (dev)
- **Templates**: Server-rendered Jinja2 (no React/Vue)
- **Auth/RBAC**: Session-based login with `@require_permission` decorator

The sales-related data lives in `app/eqms/modules/rep_traceability/`. The dashboard aggregates from the `distribution_log_entries` and `distribution_lines` tables — **not** directly from `sales_orders`. This distinction matters.

---

## Files You Will Be Modifying

You will only touch these files. Do **not** modify any other part of the system.

| File | Role |
|------|------|
| `app/eqms/templates/admin/sales_dashboard/index.html` | Dashboard UI template (382 lines) |
| `app/eqms/modules/rep_traceability/admin.py` | Route handlers: `sales_dashboard()` (~line 1750), `sales_dashboard_export()` (~line 1948) |
| `app/eqms/modules/rep_traceability/service.py` | Business logic: `compute_sales_dashboard()` (~line 756) |

Read all three files in full before making any changes.

---

## Enhancement 1: Add End Date to the Date Period Filter

### Problem

The dashboard currently filters by `ship_date >= start_date` only (an open-ended range). There is no way to define an upper bound, making it impossible to answer questions like "how many 14Fr units were sold in Q1 2026?"

### What to Change

**`service.py` — `compute_sales_dashboard()`**

- Change the function signature from `compute_sales_dashboard(s, *, start_date: date | None)` to `compute_sales_dashboard(s, *, start_date: date | None, end_date: date | None = None)`.
- Wherever `start_date` is used to filter `DistributionLogEntry.ship_date`, also apply `end_date` if provided:
  ```python
  if end_date:
      q = q.filter(DistributionLogEntry.ship_date <= end_date)
  ```
  Apply this to **all** windowed queries in the function: the main `window_entries` query, `line_window_q`, `line_ids_window_q`, `sku_rows`, and `entry_line_rows`. The all-time queries and `compute_lot_inventory_snapshot()` must **not** be date-filtered.
- Pass `end_date` through in the returned dict as needed by the export route.

**`admin.py` — `sales_dashboard()` route (~line 1750)**

- Parse a new `end_date` query param using the same pattern as `start_date`:
  ```python
  end_date_s = normalize_text(request.args.get("end_date")) or None
  end_date = None
  if end_date_s:
      try:
          end_date = date.fromisoformat(end_date_s)
      except Exception:
          flash("Invalid end_date. Use YYYY-MM-DD.", "danger")
          return redirect(url_for("rep_traceability.sales_dashboard"))
  ```
- Pass `end_date=end_date` to `compute_sales_dashboard()`.
- Add `end_date=str(end_date) if end_date else ""` to the `render_template()` call so the template has access to it.
- Update the `record_event` metadata to include `end_date`.

**`admin.py` — `sales_dashboard_export()` route (~line 1948)**

- Apply the same `end_date` parsing logic as in the view route.
- Pass `end_date=end_date` to `compute_sales_dashboard()`.
- Pass `end_date` through to the export URL in the filename: change the filename from `sales_dashboard_{start_date}.csv` to `sales_dashboard_{start_date}_to_{end_date or 'present'}.csv`.
- Update the audit event metadata to include `end_date`.

**`index.html` — Date filter form**

- The current form has a single `Since:` date input. Replace this UI block with a date-range form showing two labeled inputs side by side:
  - **"From:"** → `<input type="date" name="start_date" value="{{ start_date|e }}">`
  - **"To:"** → `<input type="date" name="end_date" value="{{ end_date|e }}">`  (leave blank = open-ended/present)
  - Keep the existing "Apply" submit button.
- Update the Export CSV link to also pass `end_date`:
  ```html
  <a class="button button--secondary"
     href="{{ url_for('rep_traceability.sales_dashboard_export', start_date=start_date, end_date=end_date) }}">
    Export CSV
  </a>
  ```
- Update the metric card labels that say "Total Units" and "Total Orders" to show the active date range, e.g. the muted subtext below the number should read something like `{{ start_date }}{% if end_date %} – {{ end_date }}{% else %} – present{% endif %}`.

---

## Enhancement 2: Fix the CSV Export

### Problem

The current export emits **one row per `DistributionLogEntry`** record. Each `DistributionLogEntry` stores only one SKU/Lot at the entry level (the `sku` and `lot_number` columns on the entry itself). However, multi-SKU shipments are broken out into `DistributionLine` child records, which the export ignores entirely. The result is that multi-SKU orders show only the entry-level SKU/Lot, which is incomplete and misleading.

Additionally, the export should not show raw SKU/Lot granularity — that level of detail is already on the Distribution Log page. The sales dashboard export should be a **customer-order summary**: one row per unique order, not one row per distribution entry.

### What to Change

**`admin.py` — `sales_dashboard_export()` route**

Completely rewrite the CSV body section. The new export must:

1. **Group by customer** — produce one row per unique customer (identified by the same `customer_key_fn` logic already in the code).
2. **Columns** (in this order):

   | Column | Value |
   |--------|-------|
   | `Customer Type` | `First-Time` or `Repeat` (existing logic) |
   | `Customer Key` | The canonical customer key |
   | `Facility` | Facility/customer name |
   | `City` | City |
   | `State` | State |
   | `Customer ID` | DB customer ID if linked, else blank |
   | `Total Units ({start_date} to {end_date or 'present'})` | Sum of units for this customer in the selected date window (sum across all their distribution entries in `window_entries`, using the same `entry_line_totals` logic already computed in `compute_sales_dashboard`) |
   | `Total Orders Lifetime` | Count of distinct `order_number` values across **all time** for this customer (use `orders_by_customer[key]`) |

3. **Remove the SKU and Lot columns entirely** from the customer rows.
4. **Retain the Lot Inventory appendix** section at the bottom of the CSV exactly as it is now.
5. Update the `record_event` metadata: change `row_count` to be the number of customer rows written.

To compute per-customer unit totals for the window, you need access to per-entry unit totals. The `compute_sales_dashboard()` service function already computes `entry_line_totals` (a dict mapping `entry_id → int units`). You will need to either:
  - Return `entry_line_totals` from the service function (add it to the returned dict), **or**
  - Recompute it locally inside the export route.

Prefer returning it from the service. Add `"entry_line_totals": entry_line_totals` to the `return` dict in `compute_sales_dashboard()`.

The export loop should look roughly like this:

```python
# Build per-customer aggregates from window_entries
from collections import defaultdict
customer_units: dict[str, int] = defaultdict(int)
customer_meta: dict[str, dict] = {}

entry_line_totals = data["entry_line_totals"]

for e in window_entries:
    key = customer_key_fn(e.customer_id, e.facility_name, e.customer_name)
    if key == "k:":
        continue
    unit_count = entry_line_totals.get(e.id, int(e.quantity or 0))
    customer_units[key] += unit_count
    if key not in customer_meta:
        customer_meta[key] = {
            "facility_name": e.facility_name or e.customer_name or "",
            "city": e.city or "",
            "state": e.state or "",
            "customer_id": e.customer_id or "",
        }
    elif e.customer_id and not customer_meta[key]["customer_id"]:
        customer_meta[key]["customer_id"] = e.customer_id

period_label = f"{start_date} to {end_date}" if end_date else f"{start_date} to present"

w.writerow([
    "Customer Type",
    "Customer Key",
    "Facility",
    "City",
    "State",
    "Customer ID",
    f"Total Units ({period_label})",
    "Total Orders Lifetime",
])

for key, meta in sorted(customer_meta.items(), key=lambda kv: kv[1]["facility_name"].lower()):
    lifetime_orders = len({o for o in orders_by_customer.get(key, set()) if o})
    cust_type = "First-Time" if lifetime_orders <= 1 else "Repeat"
    w.writerow([
        cust_type,
        key,
        meta["facility_name"],
        meta["city"],
        meta["state"],
        meta["customer_id"],
        customer_units[key],
        lifetime_orders,
    ])
```

---

## Enhancement 3: Remove Upload Buttons from the Dashboard UI

### Problem

The "Upload Sales Orders" and "Upload Packing Slips" buttons in the dashboard header belong to distribution log workflows. They create visual clutter on the sales dashboard.

### What to Change

**`index.html` — header action row (~lines 17–18)**

Remove these two lines entirely:

```html
<a class="button" href="{{ url_for('rep_traceability.sales_orders_import_pdf_get') }}">Upload Sales Orders</a>
<a class="button button--secondary" href="{{ url_for('rep_traceability.sales_orders_import_pdf_get') }}#packing-slips">Upload packing slips</a>
```

After removal, the header action row should contain only:
1. The date range filter form (From / To inputs + Apply button) — from Enhancement 1
2. The Export CSV link

Do **not** remove these links from the Distribution Log pages — they should remain there.

---

## Summary of All Changes

| File | What Changes |
|------|-------------|
| `service.py` | `compute_sales_dashboard()` gains `end_date` param; all windowed queries filtered by `end_date <= ship_date`; `entry_line_totals` added to return dict |
| `admin.py` | Both `sales_dashboard()` and `sales_dashboard_export()` parse `end_date` param; export logic rewritten to one-row-per-customer with new columns; export filename includes date range |
| `index.html` | Date filter expanded to From/To range; Upload buttons removed; Export CSV link passes `end_date` |

---

## Constraints

- Do **not** modify any other files.
- Do **not** change any database migrations or models.
- Do **not** change the Distribution Log pages, Sales Orders pages, or any other route.
- The Lot Inventory appendix in the CSV export must remain unchanged.
- All-time queries in `compute_sales_dashboard()` (lifetime order counts, `compute_lot_inventory_snapshot()`) must **not** be affected by `end_date`.
- Preserve all existing `@require_permission` decorators and audit event recording.
- The `end_date` filter is inclusive (`ship_date <= end_date`).
- If `end_date` is not provided, behavior must be identical to the current system (open-ended).
