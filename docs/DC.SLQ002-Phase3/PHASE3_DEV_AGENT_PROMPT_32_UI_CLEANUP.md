# Prompt 32 — UI Language & Display Cleanup

## Overview

This prompt covers a set of focused, high-value UI cleanup tasks with no database migrations
required. Every change is in templates or Python view helpers.  Deploy when done.

---

## Task 1 — Rename "Admin" to "Dashboard" everywhere in the UI

### 1A. Top-nav link (`app/eqms/templates/_layout.html`, line 24)

**Current:**
```jinja2
<a href="{{ url_for('admin.index') }}">{{ "Admin" if has_perm("admin.edit") else "Dashboard" }}</a>
```
**Replace with:**
```jinja2
<a href="{{ url_for('admin.index') }}">Dashboard</a>
```
All roles now see "Dashboard".

### 1B. Dashboard page `<title>` and heading (`app/eqms/templates/admin/index.html`)

- Line 2: `{% block title %}Admin{% endblock %}` → `{% block title %}Dashboard{% endblock %}`
- Line 6: `<h1 style="margin: 0;">Admin Dashboard</h1>` → `<h1 style="margin: 0;">Dashboard</h1>`

### 1C. "Back to Admin" buttons — rename to "← Back to Dashboard"

In every template listed below, find the button/link with text "Back to Admin" or "← Back to Admin"
and change the visible text to "← Back to Dashboard" (add the arrow if it is missing; the
`href` target stays unchanged):

- `app/eqms/templates/admin/nre_projects/index.html`
- `app/eqms/templates/admin/supplies/list.html`
- `app/eqms/templates/admin/audit/list.html`
- `app/eqms/templates/admin/modules/document_control/list.html`
- `app/eqms/templates/admin/admin_docs/index.html`
- `app/eqms/templates/admin/diagnostics.html`
- `app/eqms/templates/admin/search.html`
- `app/eqms/templates/admin/customers/list.html`
- `app/eqms/templates/admin/auditor_access/list.html`
- `app/eqms/templates/errors/404.html`
- `app/eqms/templates/errors/405.html`
- `app/eqms/templates/errors/403.html`
- `app/eqms/templates/errors/400.html`
- `app/eqms/templates/admin/debug_permissions.html`
- `app/eqms/templates/admin/tracing/list.html`
- `app/eqms/templates/errors/schema_out_of_date.html`

> Leave `app/eqms/templates/admin/accounts/list.html` unchanged — it already reads "← Back to Admin Tools" which is the correct target.

---

## Task 2 — Dashboard card subtitle rewrite (`app/eqms/templates/admin/index.html`)

Replace **every** `<p class="muted dash-card-desc">` subtitle with the short, noun-phrase
versions below.  Do NOT use document-number references, procedural language ("tracked against"),
or meta-commentary ("Full library", "all folders shown on one page").

| Card title | New subtitle text |
|---|---|
| QM Documents | SOPs, forms, templates, and travelers |
| Design & Development Records | Design history files, device master record, and project archives |
| Quality Planning | Quality objectives, plans, and reports |
| Management Reviews & Audits | Management reviews, internal audits, and external audits |
| Post Market Surveillance | Product complaints, eMDRs, and clinical data |
| Risk Management | PFMEA, risk analyses, and risk management files |
| Manufacturing | Production lots, DHRs, and work orders |
| Equipment | Equipment registry and calibration records |
| Purchasing | Purchase orders, payment tracking, and vendor documents |
| Supplies | Pathway inventory and consumable supplies |
| NCRs | Non-conformance reports |
| Employee Training | Training records and certifications |
| Training (manage role) | Training assignments and completion tracking |
| Training (staff role) | Training assignments |
| Distribution Log | Device distribution records |
| Sales Dashboard | Sales metrics, inventory, and analytics |
| Customers | Customer profiles and order history |
| Suppliers | Approved supplier profiles |
| NRE Projects | Invoice tracking and project documents |
| Document Control | QMS documents, revisions, and DCO log |
| CAPAs | Corrective and preventive actions |
| Regulatory Standards | ISO standards, ASTM, and regulatory filings |
| Reports | What's Due and management review reports |
| Admin Tools | System diagnostics and account management |
| My Account | Account settings |

---

## Task 3 — Remove generic filler subtitles from module pages

The following subtitle strings appear on module landing pages and should simply be
**removed** (delete the entire `<p>` tag containing them):

| File | String to remove |
|---|---|
| `app/eqms/templates/admin/admin_docs/index.html` | `Organize folders and store documents.` |
| `app/eqms/templates/admin/admin_docs/accordion.html` | `Full library — all folders shown on one page.` |
| `app/eqms/templates/admin/capas/list.html` | `Corrective and Preventive Action tracker (QM.SLQ016).` |
| `app/eqms/templates/admin/quality_objectives.html` | `QM.SLQ037 Rev B — quality objectives, the quarterly Quality Plan scorecard, and plan documents.` |
| `app/eqms/templates/admin/purchasing/list.html` | `Purchase orders and confirmations.` |

---

## Task 4 — Folder contents: show total file count only, drop subfolder count

### 4A. Accordion libraries (`app/eqms/templates/admin/admin_docs/accordion.html`)

The `render_folder` macro currently renders:
```
{{ files|length }} file(s) · {{ kids|length }} subfolder(s)
```

**Change this to show only the total file count** (files directly in the folder PLUS all files
in any descendant subfolders).

To enable this, add a `total_files_by_folder` dict to `_render_library_accordion` in
`app/eqms/modules/admin_docs/admin.py`.  After building `files_by_folder` and
`children_by_parent`, compute it with a simple post-order traversal:

```python
# Build a mapping from folder_id -> total descendant file count (recursive)
def _total_files(fid, children_by_parent, files_by_folder):
    direct = len(files_by_folder.get(fid, []))
    return direct + sum(
        _total_files(child.id, children_by_parent, files_by_folder)
        for child in children_by_parent.get(fid, [])
    )

total_files_by_folder = {
    fid: _total_files(fid, children_by_parent, files_by_folder)
    for fid in folders_by_id
}
```

Pass `total_files_by_folder` to the template via `render_template(...)`.

In `accordion.html`, in the `render_folder` macro, replace the summary count span:
```jinja2
{# old #}
<span class="muted" style="font-size:12px; font-weight:400;">
  {{ files|length }} file{{ '' if files|length == 1 else 's' }} · {{ kids|length }} subfolder{{ '' if kids|length == 1 else 's' }}
</span>
```
**with:**
```jinja2
{# new #}
{% set total = total_files_by_folder.get(fid, files|length) %}
<span class="muted" style="font-size:12px; font-weight:400;">
  {{ total }} file{{ '' if total == 1 else 's' }}
</span>
```

### 4B. Paginated (non-accordion) library view (`app/eqms/templates/admin/admin_docs/index.html`)

In the Folders table, column "Contents":
```jinja2
{# old #}
{{ fc }} file{{ 's' if fc != 1 else '' }}, {{ sc }} subfolder{{ 's' if sc != 1 else '' }}
```
**Replace with:**
```jinja2
{{ fc }} file{{ 's' if fc != 1 else '' }}
```
(The `subfolder_counts` variable can remain computed server-side for now; it simply won't be
displayed.)

---

## Task 5 — Additional site-wide cleanup

### 5A. Breadcrumb label "Dashboard" consistency

`app/eqms/templates/_macros.html` (or wherever `breadcrumbs` is defined) — verify that the
first breadcrumb label used in all templates reads `"Dashboard"` not `"Admin"`.  If any
template passes `{"label": "Admin", ...}` as the first crumb, change it to `"Dashboard"`.

Search all templates for: `"label": "Admin"` and replace with `"label": "Dashboard"`.

### 5B. Standardize back-button arrow prefix

Any `Back to …` button on any page that is **missing** the left-arrow prefix should have `← `
prepended to its label for visual consistency.  Specifically scan:
- `app/eqms/templates/admin/supplies/list.html` ("Back to Admin" → "← Back to Dashboard")
- `app/eqms/templates/admin/audit/list.html`
- `app/eqms/templates/admin/modules/document_control/list.html`
- `app/eqms/templates/admin/admin_docs/index.html`
- `app/eqms/templates/admin/search.html`
- `app/eqms/templates/admin/auditor_access/list.html`
- Error pages (400, 403, 404, 405, schema_out_of_date)
- `app/eqms/templates/admin/tracing/list.html`

### 5C. `<title>` tag for the dashboard

In `app/eqms/templates/admin/index.html`, set `{% block title %}Dashboard{% endblock %}` (Task 1B above covers this, but confirm it is done).

### 5D. "Training" card subtitle conditional

The Training card in `index.html` uses an inline `{% if … %}{% else %}{% endif %}` inside the
`<p class="muted dash-card-desc">` tag.  Refactor so both branches produce the short phrases
from Task 2 above with no trailing whitespace/blank lines between the tags.

### 5E. Accordion library subtitle — replace with useful count

After removing the "Full library — all folders shown on one page." text (Task 3), add a brief
dynamic count in its place so the header is not completely bare.  If `root_folders|length` > 0
OR `root_files|length` > 0, show a small muted count:

```jinja2
<p class="muted" style="margin:0; font-size:13px;">
  {{ (root_folders|length) + (root_files|length) }} top-level item{{ '' if (root_folders|length + root_files|length) == 1 else 's' }}
</p>
```

### 5F. Document-number reference sweep

Users should never need to see internal document control numbers (e.g. `QM.SLQ016`,
`QM.SLQ037`, `QM.SLQ001`) in UI copy unless they are genuinely meaningful in context
(e.g. a download button for a file whose name includes the number is fine; a subtitle that
reads "tracked per QM.SLQ037" is not).

Search every template under `app/eqms/templates/` for patterns matching `QM\.SLQ\d+` and
`C\.SLQ\d+` in visible UI text (subtitles, descriptions, section headers, `<title>` tags,
breadcrumb labels). For each match:

- If it is in a subtitle or description string: **remove** the doc-number fragment and
  rewrite the sentence without it.
- If it is in a `<title>` block, `<h1>`, or heading: **remove** the parenthetical
  `(QM.SLQxxx)` suffix.
- If it is inside a filename, a download link text, or a `<code>` tag: **leave it unchanged**
  — those are intentional references to actual documents.

Known instances to address (verified at time of writing; the agent must also check for any
others):

| File | Current text | Action |
|---|---|---|
| `admin/capas/list.html` | `Corrective and Preventive Action tracker (QM.SLQ016).` | Already removed in Task 3 above |
| `admin/capas/detail.html` | Any `QM.SLQ016` in a subtitle or label | Remove |
| `admin/capas/form.html` | Any `QM.SLQ016` in a subtitle or label | Remove |
| `admin/modules/document_control/list.html` | Any `QM.SLQ001` subtitle text | Remove |
| `admin/manufacturing/index.html` | `Suspension (C.SLQ001)` in summary label | Change to `Suspension` |
| `admin/nre_projects/index.html` | None currently | No action |

For the Manufacturing section: the `<summary>` label `Suspension (C.SLQ001)` and any
similar `(X.SLQxxx)` suffixes on accordion/details headers should drop the parenthetical.

---

## Commit

Commit all changes in a single commit:

```
P32: UI cleanup — "Dashboard" rename, subtitle rewrite, folder file counts, doc-number removal
```

Then push to `main` to trigger the production deploy.
