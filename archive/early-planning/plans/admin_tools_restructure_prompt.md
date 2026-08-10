# Dev Agent Prompt — Admin Tools Page Restructure + Auditor Access Log Migration

## Project Context

You are working on **SilqQMS**, a Flask-based eQMS (Electronic Quality Management System). The stack is Python 3.12, Flask 3.1.2, SQLAlchemy, server-rendered Jinja2 templates. No React/Vue.

The production app is live at `https://silqeqms.com`. It is hosted on **DigitalOcean App Platform** and is connected to the GitHub repository `Ethan-Rao/SilqeQMS` (remote: `https://github.com/Ethan-Rao/SilqeQMS.git`). **Any commit pushed to `main` automatically triggers a new deployment on DigitalOcean.** You must commit and push your changes to `main` at the end of this task so changes are deployed.

---

## Files You Will Be Modifying

You will only touch these two files. Do **not** modify any other files in the project.

| File | Role |
|------|------|
| `app/eqms/templates/admin/diagnostics.html` | The Admin Tools page template (161 lines) |
| `app/eqms/templates/admin/index.html` | The main Admin Dashboard template (216 lines) |

Read both files in full before making any changes.

---

## What This Task Is

The Admin Tools page (`/admin/diagnostics`) currently has a poor layout:
- It is titled "System Diagnostics" but is linked from the main dashboard as "Admin Tools"
- Its Quick Links (navigation buttons) are buried at the **bottom** as a flat, undifferentiated blob of 14 buttons
- It does not function as a useful second dashboard

This task restructures the Admin Tools page so it feels like a purposeful dashboard — with grouped navigation cards at the top, followed by system status information below. It also moves the **Auditor Access Log** from the main dashboard into the Admin Tools page where it belongs.

---

## Change 1: Restructure `diagnostics.html`

### 1a. Update the page title

Change the `<h1>` from "System Diagnostics" to **"Admin Tools"**.

Remove the `{% block title %}System Diagnostics{% endblock %}` and change it to `{% block title %}Admin Tools{% endblock %}`.

Remove the `Reset Data` button from the header — it will appear in the grouped links section below. Keep the `← Back to Admin` button in the header.

### 1b. Add grouped navigation cards — at the TOP, immediately after the header card

Replace the current flat "Quick Links" card entirely with a new **grouped navigation section** that appears **above** the system status cards. This section should visually resemble the main admin dashboard: column headings with clickable cards beneath them.

Use a 4-column responsive grid (matching the main dashboard style) with these four groups:

---

**Group 1 — Accounts & Access**

Cards (each a `<a class="card card--link dash-card">` identical in style to main dashboard cards):
- **My Account** → `url_for('admin.me')` — desc: "Profile, password, and preferences"
- **User Accounts** → `url_for('admin.accounts_list')` — desc: "Manage users and roles"
- **Debug Permissions** → `url_for('admin.debug_permissions')` — desc: "Inspect permission assignments"
- **Auditor Access Log** → `url_for('admin.auditor_access_log_list')` — desc: "Records of files the external auditor has opened" — wrap with `{% if has_perm("auditor_portal.admin") %}`

---

**Group 2 — Data Uploads**

Cards:
- **Upload LotLog** → `url_for('admin.upload_lotlog_get')` — desc: "Update the active LotLog.csv"
- **Upload Disposition Log** → `url_for('admin.upload_disposition_log_get')` — desc: "Update the active DispositionLog.xlsx"
- **Import CSV (Distributions)** → `url_for('rep_traceability.distribution_log_import_get')` — desc: "Bulk-import distribution log entries from CSV"
- **Import Sales Order PDFs** → `url_for('rep_traceability.sales_orders_import_pdf_get')` — desc: "Upload and parse sales order and packing slip PDFs"
- **Equipment Import** → `url_for('equipment.equipment_bulk_import_get')` — desc: "Bulk-import equipment records"

---

**Group 3 — Data & Tracing**

Cards:
- **+ Distribution Entry** → `url_for('rep_traceability.distribution_log_new_get')` — desc: "Manually add a new distribution entry"
- **Sales Orders** → `url_for('rep_traceability.sales_orders_list')` — desc: "Browse and manage sales orders"
- **Tracing Reports** → `url_for('rep_traceability.tracing_list')` — desc: "Generate lot traceability reports"

---

**Group 4 — System**

Cards:
- **Audit Trail** → `url_for('admin.audit_list')` — desc: "Full system event log"
- **Reset Data** → `url_for('admin.reset_data_get')` — desc: "⚠ Wipe and reseed development data" — style this card with a subtle red left-border (`border-left: 4px solid var(--danger)`) to signal it is destructive
- **Storage Info** → `url_for('admin.diagnostics_storage')`, `target="_blank"` — desc: "View storage backend configuration (JSON)"
- **ShipStation Sync** → `url_for('shipstation_sync.shipstation_index')` — desc: "Sync shipments from ShipStation"

---

### 1c. Move status cards BELOW the navigation groups

Keep all existing status sections (Environment / Database / Health, Data Counts, ShipStation Sync, PDF Import Dependencies) but move them **below** the new grouped navigation section. Add a visual separator heading before this section, e.g.:

```html
<div style="height:24px;"></div>
<div class="card" style="padding:12px 20px; border-left:4px solid var(--primary);">
  <h2 style="margin:0; font-size:14px; text-transform:uppercase; letter-spacing:0.05em; color:var(--muted);">System Status</h2>
</div>
<div style="height:14px;"></div>
```

Then the existing status cards follow below that heading.

### 1d. Remove the old Quick Links card entirely

The flat "Quick Links" card at the bottom (the `<div class="card"><h2>Quick Links</h2>...`) must be completely deleted. Its links are now represented by the grouped navigation cards at the top.

### 1e. Re-use the same CSS classes as the main dashboard

The grouped navigation sections should use the same CSS classes and layout as `admin/index.html`. Copy the relevant styles into a `<style>` block at the bottom of `diagnostics.html`:

```css
.dash-col-heading {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  margin-bottom: 12px;
  padding-left: 4px;
}
.dash-col-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.dash-card {
  padding: 18px 20px;
}
.dash-card-title {
  margin: 0;
  font-size: 15px;
}
.dash-card-desc {
  margin: 5px 0 0;
  font-size: 12px;
  line-height: 1.4;
}
@media (max-width: 1200px) {
  .admin-tools-grid {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
@media (max-width: 700px) {
  .admin-tools-grid {
    grid-template-columns: 1fr !important;
  }
}
```

Use `class="admin-tools-grid"` (not an inline style selector) on the navigation grid `<div>` so the media queries work.

---

## Change 2: Update `admin/index.html` — Remove Auditor Access Log Card

In `admin/index.html`, find and **delete** the Auditor Access Log card from Column 4 (QMS System). It is currently at lines 163–168:

```html
{% if has_perm("auditor_portal.admin") %}
<a class="card card--link dash-card" href="{{ url_for('admin.auditor_access_log_list') }}">
  <h3 class="dash-card-title">Auditor Access Log</h3>
  <p class="muted dash-card-desc">Records of files the external auditor has opened.</p>
</a>
{% endif %}
```

Remove those 6 lines entirely. The Auditor Access Log is now accessible from the Admin Tools page. Do not make any other changes to `admin/index.html`.

---

## Final Page Layout (after changes)

The completed `diagnostics.html` should render in this top-to-bottom order:

1. **Header card**: "Admin Tools" title + "← Back to Admin" button
2. `<div style="height:14px;"></div>`
3. **Navigation grid** (4 columns, `class="admin-tools-grid"`):
   - Column 1: "Accounts & Access" heading + 3–4 cards
   - Column 2: "Data Uploads" heading + 5 cards
   - Column 3: "Data & Tracing" heading + 3 cards
   - Column 4: "System" heading + 4 cards
4. `<div style="height:24px;"></div>`
5. **System Status heading card** (separator, primary left border)
6. `<div style="height:14px;"></div>`
7. **Status row** (Environment, Database, Health — 3 cards in `grid--cards`)
8. `<div style="height:14px;"></div>`
9. **Data Counts** card (existing, unchanged)
10. `<div style="height:14px;"></div>`
11. **ShipStation Sync** card (existing, unchanged)
12. `<div style="height:14px;"></div>`
13. **PDF Import Dependencies** card (existing, unchanged)
14. `<style>` block with dashboard CSS

---

## Commit and Deploy

After completing both file changes, commit and push to `main` to trigger automatic DigitalOcean deployment.

Run these exact commands:

```bash
git add app/eqms/templates/admin/diagnostics.html app/eqms/templates/admin/index.html
git commit -m "feat(admin-tools): restructure admin tools as dashboard, move auditor access log"
git push origin main
```

Do **not** run `git push --force`. A standard `git push origin main` is all that is needed. DigitalOcean App Platform is connected to the `main` branch and will automatically pick up the new commit and begin a deployment.
