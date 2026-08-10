# Prompt 35 — Weekly Brief Email Tool

## Background

We need an admin-only tool that pulls live data from three sources and sends a clean HTML email via the Resend API to a user-specified list of recipients.

The tool lives under the existing Reports section (`/admin/reports/weekly-brief`) and is protected by `require_permission("admin.edit")`.

---

## Task 1 — Add Resend dependency

In `requirements.txt`, append:

```
resend>=2.0.0
```

---

## Task 2 — Environment variables

The feature reads two env vars (already expected to exist on the production server):

| Variable | Purpose |
|---|---|
| `RESEND_API_KEY` | Resend API secret key |
| `EMAIL_FROM` | Verified sender address (default `reports@silqeqms.com` if var absent) |

No migration needed — no new DB models are required.

---

## Task 3 — Backend routes

Add two routes to `app/eqms/admin.py` (the existing `bp` blueprint):

### 3A. GET /admin/reports/weekly-brief

```python
@bp.get("/reports/weekly-brief")
@require_permission("admin.edit")
def weekly_brief_index():
    ...
```

Renders `admin/reports/weekly_brief.html` with no extra context (the form is static).

### 3B. POST /admin/reports/weekly-brief/send

```python
@bp.post("/reports/weekly-brief/send")
@require_permission("admin.edit")
def weekly_brief_send():
    ...
```

Processing steps:

1. **Parse recipients** from `request.form["to_emails"]`.
   - Accept comma-separated and/or newline-separated email addresses.
   - Strip whitespace and skip blank tokens.
   - If the resulting list is empty, flash an error and redirect back.

2. **Compute sales snapshot** — call `compute_sales_dashboard` with the current quarter's start date:
   ```python
   from app.eqms.modules.rep_traceability.service import compute_sales_dashboard

   today = date.today()
   quarter_month_start = ((today.month - 1) // 3) * 3 + 1   # 1, 4, 7, or 10
   quarter_start = date(today.year, quarter_month_start, 1)
   data = compute_sales_dashboard(db_session(), start_date=quarter_start, end_date=None)
   stats  = data["stats"]
   sku_breakdown = data["sku_breakdown"]
   ```
   Compute `sku_total` as sum of `s["units"] for s in sku_breakdown` for percentage calculation in the template.

3. **Load Upcoming Payments** — all `PaymentEntry` rows, ordered by `payment_due_date` ASC (NULLs last):
   ```python
   from app.eqms.modules.purchasing.models import PaymentEntry
   from sqlalchemy import nulls_last
   payments = s.query(PaymentEntry).order_by(nulls_last(PaymentEntry.payment_due_date.asc())).all()
   ```

4. **Load NRE Invoice Tracker** — all `NREProjectEntry` rows where `invoice_status` is NOT `"Paid"` and NOT `"Cancelled"`, ordered by `entry_date` DESC (NULLs last):
   ```python
   from app.eqms.modules.nre_projects.models import NREProjectEntry
   nre_entries = (
       s.query(NREProjectEntry)
       .filter(~NREProjectEntry.invoice_status.in_(["Paid", "Cancelled"]))
       .order_by(nulls_last(NREProjectEntry.entry_date.desc()))
       .all()
   )
   ```

5. **Build subject** from `request.form.get("subject")` stripped, or default to `"Silq eQMS — Weekly Brief"`.

6. **Render HTML email** using Jinja2's `render_template`:
   ```python
   email_html = render_template(
       "email/weekly_brief.html",
       generated_at=datetime.utcnow(),
       quarter_start=quarter_start,
       stats=stats,
       sku_breakdown=sku_breakdown,
       sku_total=sku_total,
       payments=payments,
       nre_entries=nre_entries,
   )
   ```

7. **Send via Resend**:
   ```python
   import resend, os
   resend.api_key = os.environ.get("RESEND_API_KEY", "")
   from_addr = os.environ.get("EMAIL_FROM", "reports@silqeqms.com")
   if not resend.api_key:
       flash("RESEND_API_KEY is not configured.", "danger")
       return redirect(url_for("admin.weekly_brief_index"))
   try:
       resend.Emails.send({
           "from": f"Silq eQMS <{from_addr}>",
           "to": recipients,
           "subject": subject,
           "html": email_html,
       })
       flash(f"Brief sent to {len(recipients)} recipient(s).", "success")
   except Exception as e:
       flash(f"Send failed: {e}", "danger")
   return redirect(url_for("admin.weekly_brief_index"))
   ```

---

## Task 4 — Admin tool page template

Create `app/eqms/templates/admin/reports/weekly_brief.html`:

```
{% extends "_layout.html" %}
{% from "_macros.html" import breadcrumbs %}
{% block title %}Weekly Brief{% endblock %}
{% block content %}
  {{ breadcrumbs([
    {"label": "Dashboard", "url": url_for("admin.index")},
    {"label": "Reports", "url": url_for("admin.reports_index")},
    {"label": "Weekly Brief", "url": None},
  ]) }}

  <!-- Header card -->
  <div class="card">
    <h1 style="margin-top:0;">Weekly Brief</h1>
    <p class="muted" style="margin:0;">Sends an email containing the NRE Invoice Tracker, Upcoming Payments, and current-quarter sales snapshot.</p>
  </div>

  <div style="height:14px;"></div>

  <!-- Send form card -->
  <div class="card" style="max-width:640px;">
    <form method="post" action="{{ url_for('admin.weekly_brief_send') }}">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

      <label style="display:block; margin-bottom:6px; font-size:13px; font-weight:600;">Recipients</label>
      <textarea name="to_emails" rows="4" placeholder="One address per line, or comma-separated"
        style="width:100%; box-sizing:border-box; background:var(--bg-card); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:8px 10px; font-size:13px; resize:vertical;"></textarea>
      <p class="muted" style="font-size:12px; margin:4px 0 16px;">Accepts comma-separated or one-per-line email addresses.</p>

      <label style="display:block; margin-bottom:6px; font-size:13px; font-weight:600;">Subject <span class="muted" style="font-weight:400;">(optional — leave blank for default)</span></label>
      <input type="text" name="subject" placeholder="Silq eQMS — Weekly Brief"
        style="width:100%; box-sizing:border-box; background:var(--bg-card); color:var(--text); border:1px solid var(--border); border-radius:6px; padding:8px 10px; font-size:13px; margin-bottom:20px;">

      <button type="submit" class="button">Send Brief</button>
    </form>
  </div>
{% endblock %}
```

---

## Task 5 — HTML email template

Create `app/eqms/templates/email/weekly_brief.html`.

This must be a **self-contained HTML file with all styles inlined** — no external CSS references. Email clients do not support linked stylesheets or most modern CSS.

### Design specification

- White background (`#ffffff`), `font-family: -apple-system, Arial, sans-serif`, max-width 620px, centered
- Top header bar: dark background (`#0d1117`), white Silq logo text + subtitle "Weekly Brief", right-aligned generated date
- Three sections separated by `<hr>` dividers, each with a section heading
- All tables: full width, `border-collapse: collapse`, alternating row shading (`#f8f9fa` / `#ffffff`), header row with `#1e2a38` background and white text
- Status badges: inline `<span>` with `border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600`:
  - "Pending Invoice" → amber `#b45309` on `#fef3c7`
  - "Invoiced" → blue `#1d4ed8` on `#dbeafe`
  - "Paid" → green `#15803d` on `#dcfce7`
  - "Cancelled" → gray `#6b7280` on `#f3f4f6`
- Footer: light gray background, "Silq eQMS · Generated {date}" centered text
- Currency: format amounts as `$X,XXX.XX` using a Jinja filter or inline format

### Section 1 — Sales Snapshot

Heading: `Current Quarter Sales — Q{{ quarter_label }} {{ generated_at.year }}`

Where `quarter_label` is computed in the route or template as:
```
Q1=Jan 1 – Mar 31, Q2=Apr 1 – Jun 30, Q3=Jul 1 – Sep 30, Q4=Oct 1 – Dec 31
```
Pass `quarter_label` (integer 1-4) from the route to the template.

Display as two rows of metric tiles (styled `<td>` cells, 50% width each, or a 3+2 layout):

Row 1: TOTAL UNITS | TOTAL ORDERS | CUSTOMERS
Row 2: FIRST-TIME CUSTOMERS | REPEAT CUSTOMERS

Below the metrics, a Sales by SKU table:

| SKU | Units | % of Total |
|-----|-------|-----------|
| 211610SPT | 70 | 53.8% |
| **Total** | **130** | **100%** |

SKU values come from `sku_breakdown` list (each item: `{"sku": str, "units": int}`).
Percentage = `(units / sku_total * 100)` — format to one decimal place.
Show a bold Total row at the bottom.

If `sku_breakdown` is empty, show `<p><em>No sales data for this quarter.</em></p>`.

### Section 2 — Upcoming Payments

Heading: `Upcoming Payments`

Table columns: Date | Vendor | Description | Amount | Due Date

If `payments` is empty, show `<em>No payment entries.</em>`.

Rows:
- Date: `entry.order_date` formatted as `MMM D, YYYY`, or `—` if null
- Vendor: `entry.vendor or "—"`
- Description: `entry.description or "—"`
- Amount: `$X,XXX.XX` or `—`
- Due Date: `entry.payment_due_date` formatted as `MMM D, YYYY`, or `—` if null

### Section 3 — NRE Invoice Tracker

Heading: `NRE Invoice Tracker`

Table columns: Date | Customer | Ref | Description | Invoice Amount | Exp. Date | Status

If `nre_entries` is empty, show `<em>No active NRE invoice entries.</em>`.

Rows:
- Date: `entry.entry_date` formatted as `MMM D, YYYY`, or `—`
- Customer: `entry.customer_name or "—"`
- Ref: `entry.order_ref or "—"`
- Description: `entry.description or "—"`
- Invoice Amount: `$X,XXX.XX` or `—`
- Exp. Date: `entry.expected_invoice_date` formatted as `MMM D, YYYY`, or `—`
- Status: status badge (use the colors defined above)

---

## Task 6 — Reports index card

In `app/eqms/templates/admin/reports/index.html`, append a new card after the existing "Management Review Report" card:

```html
<div style="height:14px;"></div>
<div class="card">
  <div style="display:flex; justify-content:space-between; gap:12px; align-items:flex-start; flex-wrap:wrap;">
    <div>
      <h2 style="margin:0 0 4px; font-size:16px;">Weekly Brief</h2>
      <p class="muted" style="margin:0; font-size:13px;">Email snapshot of NRE invoices, upcoming payments, and current-quarter sales.</p>
    </div>
    <a class="button" href="{{ url_for('admin.weekly_brief_index') }}">Open tool</a>
  </div>
</div>
```

---

## Verification checklist

- [ ] `GET /admin/reports/weekly-brief` renders the form (no errors)
- [ ] `POST /admin/reports/weekly-brief/send` with empty recipients → flashes error, no send attempt
- [ ] With valid recipients and `RESEND_API_KEY` set → Resend API is called, success flash shown
- [ ] If `RESEND_API_KEY` is not set → meaningful error flash, no crash
- [ ] Email HTML contains all three sections
- [ ] Sales by SKU percentage math is correct (sums to 100%)
- [ ] Quarter label is correct for the current date (Jul 2026 → Q3 2026)
- [ ] `NREProjectEntry` with status "Paid" or "Cancelled" are excluded from email
- [ ] Route is protected by `require_permission("admin.edit")`
- [ ] No existing tests broken; add a basic route-smoke test for the GET endpoint

---

## Deploy notes

After deploying, set the following on DigitalOcean App Platform:

- `RESEND_API_KEY` → your Resend secret key (from resend.com dashboard → API Keys)
- `EMAIL_FROM` → `reports@silqeqms.com` (domain verified in Resend via Cloudflare DNS)

No database migrations are needed for this prompt.
