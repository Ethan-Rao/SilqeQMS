# Dev Agent Prompt — Two Tasks: Commit Sales Dashboard + Consolidate System Status

## Project Context

You are working on **SilqQMS**, a Flask/Python 3.12 app with server-rendered Jinja2 templates. The production app is at `https://silqeqms.com`, hosted on **DigitalOcean App Platform** connected to the GitHub repository `Ethan-Rao/SilqeQMS` (remote: `https://github.com/Ethan-Rao/SilqeQMS.git`). Any commit pushed to `main` automatically triggers a new production deployment. You must commit and push your work at the end of this task.

**Read each file before modifying it.**

---

## TASK 1 — Commit the Sales Dashboard Changes (Already Implemented, Not Yet Committed)

A previous dev agent correctly implemented three enhancements to the sales dashboard but forgot to commit them. The changes are sitting as uncommitted modifications in the working tree right now. Your first job is to verify they are correct and commit them.

### Step 1a — Verify the changes are present

Run `git diff HEAD -- app/eqms/modules/rep_traceability/service.py app/eqms/modules/rep_traceability/admin.py app/eqms/templates/admin/sales_dashboard/index.html` and confirm the following are all present:

**`service.py`** — `compute_sales_dashboard()`:
- Signature is `compute_sales_dashboard(s, *, start_date: date | None, end_date: date | None = None)`
- `end_date` filter (`ship_date <= end_date`) applied to all five windowed queries: `window_entries`, `line_window_q`, `line_ids_window_q`, `sku_rows`, `entry_line_rows`
- `"entry_line_totals": entry_line_totals` present in the `return` dict

**`admin.py`** — `sales_dashboard()` route:
- Parses `end_date` query param with the same ISO validation pattern as `start_date`
- Passes `end_date=end_date` to `compute_sales_dashboard()`
- Passes `end_date=str(end_date) if end_date else ""` to `render_template()`
- Audit event metadata includes `end_date`

**`admin.py`** — `sales_dashboard_export()` route:
- Parses `end_date` query param identically
- Passes `end_date=end_date` to `compute_sales_dashboard()`
- CSV body is rewritten to one row per customer (not one row per distribution entry) with columns: `Customer Type`, `Customer Key`, `Facility`, `City`, `State`, `Customer ID`, `Total Units ({period_label})`, `Total Orders Lifetime`
- Lot Inventory appendix preserved
- Filename uses `_to_{end_date or 'present'}` pattern
- Audit metadata includes `end_date` and `row_count` reflects customer count

**`index.html`** — Sales Dashboard template:
- Date filter form has both `From:` (`start_date`) and `To:` (`end_date`) inputs
- Upload Sales Orders and Upload Packing Slips buttons are removed
- Export CSV link passes both `start_date` and `end_date`
- Total Units and Total Orders metric cards show a muted date-range subtext

If any of these are missing, apply them now following the descriptions above before committing.

### Step 1b — Stage and commit the sales dashboard changes

```bash
git add app/eqms/modules/rep_traceability/service.py
git add app/eqms/modules/rep_traceability/admin.py
git add app/eqms/templates/admin/sales_dashboard/index.html
git commit -m "feat(sales-dashboard): date range filter, per-customer CSV export, remove upload buttons"
```

**Important:** Do NOT stage any other modified files. The working tree also has unrelated modifications to `app/eqms/__init__.py`, purchasing files, document control files, scripts, and docs — leave all of those untouched and unstaged.

---

## TASK 2 — Consolidate the System Status Section on the Admin Tools Page

### File to modify

`app/eqms/templates/admin/diagnostics.html`

Read the full file first. The navigation grid at the top of the file (the four groups: Accounts & Access, Data Uploads, Data & Tracing, System), the header card, and the `<style>` block at the bottom must **not change**. You are only replacing the System Status section that begins after the navigation grid ends and before the `<style>` block.

The route handler in `app/eqms/admin.py` already provides all necessary data in the `diag` dict. **Do not modify any Python files.**

### What to remove

Delete the entire current System Status section — everything from the `<div style="height:24px;"></div>` spacer that follows the navigation grid down to (but not including) the `<style>` block:

- The `height:24px` spacer div
- The blue-border "System Status" label card
- The `height:14px` spacer
- The three-card row: Environment, Database, Health Endpoint
- The `height:14px` spacer
- The Data Counts card (inside `{% if diag.db_connected %}`)
- The `height:14px` spacer
- The ShipStation Sync card
- The `{% endif %}` closing the `diag.db_connected` block
- The `height:14px` spacer
- The PDF Import Dependencies card

### What to add in its place

Add a single `<details>` card element. Use the native HTML `<details>`/`<summary>` disclosure pattern — no JavaScript needed.

#### Status logic

Compute three Jinja2 boolean variables at the top of the replacement section:

```jinja2
{% set sys_red = not diag.db_connected or not diag.pdf_dependencies.pdfplumber or not diag.pdf_dependencies.PyPDF2 %}
{% set sys_yellow = not sys_red and diag.unmatched_distributions > 0 %}
{% set sys_green = not sys_red and not sys_yellow %}
```

**Status colors:**
- RED (`var(--danger)`): DB not connected OR either PDF library missing
- YELLOW (`#f59e0b`): All critical checks pass but unmatched distributions > 0
- GREEN (`var(--success)`): Everything clean

**Auto-open behavior:** Add `open` attribute to `<details>` when `sys_red or sys_yellow` so problems are never hidden.

#### Full replacement HTML

```html
<div style="height:24px;"></div>

{% set sys_red = not diag.db_connected or not diag.pdf_dependencies.pdfplumber or not diag.pdf_dependencies.PyPDF2 %}
{% set sys_yellow = not sys_red and diag.unmatched_distributions > 0 %}
{% set sys_green = not sys_red and not sys_yellow %}

<details class="card" id="system-status-details" style="padding:0; overflow:hidden;" {% if sys_red or sys_yellow %}open{% endif %}>

  <summary style="list-style:none; cursor:pointer; padding:18px 20px; display:flex; align-items:center; justify-content:space-between; gap:16px; user-select:none;">
    <div style="display:flex; align-items:center; gap:14px;">
      <span style="width:13px; height:13px; border-radius:50%; flex-shrink:0; background:{% if sys_red %}var(--danger){% elif sys_yellow %}#f59e0b{% else %}var(--success){% endif %};"></span>
      <div>
        <div style="font-weight:600; font-size:15px;">System Status</div>
        <div class="muted" style="font-size:12px; margin-top:3px;">
          {% if sys_red %}
            {% if not diag.db_connected %}Database connection error{% elif not diag.pdf_dependencies.pdfplumber or not diag.pdf_dependencies.PyPDF2 %}PDF import dependency missing{% endif %}
          {% elif sys_yellow %}
            {{ diag.unmatched_distributions }} unmatched distribution{{ 's' if diag.unmatched_distributions != 1 else '' }} — action needed
          {% else %}
            All systems operational
          {% endif %}
        </div>
      </div>
    </div>
    <span class="muted" style="font-size:12px; white-space:nowrap; flex-shrink:0;">Details ▾</span>
  </summary>

  <div style="padding:4px 20px 20px 20px; border-top:1px solid var(--border);">

    {# ── Group 1: Connectivity ── #}
    <div style="display:grid; grid-template-columns:180px 1fr; gap:6px 16px; font-size:13px; margin-top:16px;">
      <div class="muted">Database</div>
      {% if diag.db_connected %}
        <div style="color:var(--success); font-weight:600;">✓ Connected</div>
      {% else %}
        <div style="color:var(--danger); font-weight:600;">✗ Error<span style="font-weight:400; margin-left:8px;">{{ diag.db_error }}</span></div>
      {% endif %}
    </div>

    {% if diag.db_connected %}

    {# ── Group 2: Data Counts ── #}
    <div style="display:grid; grid-template-columns:180px 1fr; gap:6px 16px; font-size:13px; margin-top:16px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.05);">
      <div class="muted">Customers</div>
      <div>{{ diag.counts.customers or 0 }}</div>
      <div class="muted">Distribution Entries</div>
      <div>{{ diag.counts.distributions or 0 }}</div>
      <div class="muted">Sales Orders</div>
      <div>{{ diag.counts.sales_orders or 0 }}</div>
      <div class="muted">Unmatched Distributions</div>
      <div {% if diag.unmatched_distributions > 0 %}style="color:var(--danger); font-weight:600;"{% endif %}>
        {{ diag.unmatched_distributions or 0 }}
        {% if diag.unmatched_distributions > 0 %}
          <a href="{{ url_for('rep_traceability.distribution_log_list') }}" style="font-size:12px; margin-left:8px; color:var(--danger);">View in Distribution Log →</a>
        {% endif %}
      </div>
    </div>

    {# ── Group 3: ShipStation Sync ── #}
    <div style="display:grid; grid-template-columns:180px 1fr; gap:6px 16px; font-size:13px; margin-top:16px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.05);">
      <div class="muted">Last ShipStation Sync</div>
      {% if diag.last_shipstation_sync %}
        <div>{{ diag.last_shipstation_sync.ran_at }}</div>
        <div class="muted">Synced</div>
        <div style="color:var(--success);">{{ diag.last_shipstation_sync.synced_count or 0 }} entries</div>
        <div class="muted">Skipped</div>
        <div>{{ diag.last_shipstation_sync.skipped_count or 0 }} entries</div>
        {% if diag.last_shipstation_sync.message %}
          <div class="muted">Message</div>
          <div>{{ diag.last_shipstation_sync.message }}</div>
        {% endif %}
      {% else %}
        <div class="muted">No sync runs recorded yet</div>
      {% endif %}
    </div>

    {% endif %}

    {# ── Group 4: PDF Dependencies ── #}
    <div style="display:grid; grid-template-columns:180px 1fr; gap:6px 16px; font-size:13px; margin-top:16px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.05);">
      <div class="muted">pdfplumber</div>
      {% if diag.pdf_dependencies.pdfplumber %}
        <div style="color:var(--success);">✓ Installed v{{ diag.pdf_dependencies.pdfplumber_version }}</div>
      {% else %}
        <div style="color:var(--danger); font-weight:600;">✗ Missing — required for PDF parsing</div>
      {% endif %}
      <div class="muted">PyPDF2</div>
      {% if diag.pdf_dependencies.PyPDF2 %}
        <div style="color:var(--success);">✓ Installed v{{ diag.pdf_dependencies.PyPDF2_version }}</div>
      {% else %}
        <div style="color:var(--danger); font-weight:600;">✗ Missing — required for PDF splitting</div>
      {% endif %}
      {% if not diag.pdf_dependencies.pdfplumber or not diag.pdf_dependencies.PyPDF2 %}
        <div></div>
        <div style="color:var(--muted); font-size:12px; margin-top:2px;">Install: <code>pip install pdfplumber PyPDF2</code></div>
      {% endif %}
    </div>

    {# ── Group 5: Application ── #}
    <div style="display:grid; grid-template-columns:180px 1fr; gap:6px 16px; font-size:13px; margin-top:16px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.05);">
      <div class="muted">Version</div>
      <div>{{ diag.app_version }}</div>
      <div class="muted">Environment</div>
      <div>{{ diag.env }}</div>
      <div class="muted">Port</div>
      <div>{{ diag.port }}</div>
      <div class="muted">Health Check</div>
      <div><a href="/healthz" target="_blank" style="color:var(--primary);">/healthz →</a></div>
    </div>

  </div>
</details>
```

### Final structure of the file after changes

From top to bottom:
1. `{% extends "_layout.html" %}` / `{% block title %}Admin Tools{% endblock %}`
2. `{% block content %}`
3. Header card ("Admin Tools" + "← Back to Admin" button) — **unchanged**
4. `height:14px` spacer — **unchanged**
5. Navigation grid with 4 groups — **unchanged**
6. `height:24px` spacer — **new** (part of replacement)
7. Single `<details>` System Status card — **new**
8. `<style>` block — **unchanged**
9. `{% endblock %}`

### Commit the admin tools change

```bash
git add app/eqms/templates/admin/diagnostics.html
git commit -m "feat(admin-tools): consolidate system status into single collapsible card"
```

---

## FINAL STEP — Push Both Commits to Deploy

After both commits are made, push to `main` to trigger automatic DigitalOcean deployment:

```bash
git push origin main
```

Do **not** use `--force`. A standard push is all that is needed. DigitalOcean App Platform will detect the new commits on `main` and automatically begin a new deployment to `https://silqeqms.com`.
