# Phase 3 — Prompt 21: Browse UX Fixes + Admin_docs Accordion + Dashboard Restructure

## Context

Three distinct, independent task groups. All are template/code changes — no migration,
no coordinator-run scripts.

---

## Task A — QM Documents browse view UX improvements (`browse.html`)

### A1 — Make document rows visibly clickable

The document number / title links within SOP `<summary>` elements and child rows
currently don't stand out enough as interactive. Update `browse.html` so that:

- SOP `<summary>` rows get a visible hover background (use the existing `var(--border)`
  or `var(--card-bg)` hover tone) and an explicit `cursor: pointer`.
- The `<summary>` text itself uses the existing `--accent` link color (same blue as
  other links in the system) and underlines on hover so it is unambiguous.
- Child document rows (forms/templates) within an open SOP group are indented and also
  use the link color with underline-on-hover.
- Add a small disclosure chevron (▶ / ▼, CSS only via `::marker` or a span) that
  rotates when the `<details>` is open. This applies to both the subsystem-level
  `<details>` and the SOP-group `<details>`.

### A2 — Auto-expand single-item subsystem sections

When a subsystem `<details>` section is opened by the user and it contains exactly one
child SOP group `<details>`, automatically open that inner group immediately. Implement
in JavaScript (listen to the `toggle` event on subsystem `<details>` elements; if
`e.target.open === true` and there is exactly one `<details>` child, set
`child.open = true`). This JS is small and should be inlined in the template.

### A3 — Fix Receiving SOP grouping (qms_index.py)

Currently `QM.SLQ045` (Receiving SOP, clause `7.4.3 / 7.5.1`) is mapped to
`"Production & Service"`. The Receiving Inspection SOP (`QM.SLQ039`) is already in
`"Purchasing & Suppliers"`. Both are part of the receiving workflow and should appear
in the same section.

Update `_BY_SLQ_FAMILY[45]` in `qms_index.py`:
```python
45: QmsClassification("7.4.3 / 7.5.1 Receiving", "Purchasing & Suppliers"),
```

While reviewing, do a broad pass: check all `_BY_SLQ_FAMILY` entries where `subsystem`
is `"Production & Service"` and confirm the grouping is logical for a user looking for
a form to fill out. Flag (comment in code) any groupings that feel debatable but leave
them as-is unless there is a clear correction; only change SLQ045 without coordinator
confirmation for others.

---

## Task B — Admin_docs accordion view for three libraries

### B1 — Architecture

Add a constant to `app/eqms/modules/admin_docs/admin.py`:

```python
ACCORDION_LIBRARIES: frozenset[str] = frozenset({
    "management_reviews",
    "post_market_surveillance",
    "risk_management",
})
```

In `_render_library()`, when `library_key in ACCORDION_LIBRARIES`:
1. Load ALL `AdminDocFolder` records for the library in one query (no folder_id filter).
2. Load ALL `AdminDocFile` records for the library in one query.
3. Build an in-memory tree:
   - `folders_by_id: dict[int, AdminDocFolder]`
   - `children_by_parent: dict[int | None, list[AdminDocFolder]]` (None key = root)
   - `files_by_folder: dict[int | None, list[AdminDocFile]]` (None key = root-level files)
4. Render `admin/admin_docs/accordion.html` (new template, see B2).

For all other libraries, continue rendering the existing `index.html` unchanged.

### B2 — New template: `admin/admin_docs/accordion.html`

The page shows the entire folder tree on a single page — no navigation to sub-pages.

**Structure:**
- Breadcrumb: `Dashboard / <Library Name>` using the `breadcrumbs()` macro.
- Page header: library title + "Search this library" box (`?q=`) as before.
- A Jinja2 recursive `macro render_folder(folder_id, depth)` that renders:

```
<details [open if depth==0 and only one root folder]>
  <summary>
    📁 Folder Name  (N files  |  M subfolders)
    [admin-only: inline New Subfolder button + Upload button]
  </summary>

  <!-- files in this folder -->
  <ul class="accordion-files">
    <li>
      <a href="view_url">📄 filename.pdf</a>
      <a href="download_url" class="button button--small">↓</a>
      [admin-only: Move button]
    </li>
  </ul>

  <!-- recursive child folders -->
  {{ render_folder(child_folder_id, depth+1) }}
</details>
```

- Root-level files (not in any folder) are shown first at the top of the page outside
  any `<details>`.
- The "New Subfolder" and "Upload" inline controls use the existing POST endpoints
  (`/admin-docs/folders/new` and `/admin-docs/documents/upload`) with hidden fields
  for `library_key` and `parent_id` / `folder_id`. These are inside `<form>` elements
  shown/hidden via a small JS toggle (a `+` button reveals the inline mini-form). No
  new backend routes needed.
- In-library search (`?q=`): when a query is present, bypass the tree rendering and
  show the flat search-results list instead (reuse the existing search_results logic
  and render a flat list as in the current template). A "Clear search" link resets to
  the tree view.

**Styling:**
- Indent each depth level by `calc(depth * 16px)` left padding.
- Use the same `<details>/<summary>` chevron CSS from the browse template (A1).
- `.accordion-files` is a plain `<ul style="list-style:none; padding:0; margin:4px 0;">`.
- Folder summary rows hover in `var(--border)` background.
- File rows show filename (linked) + download icon button side by side.

**Accessibility:** same `<details>/<summary>` native keyboard pattern as the browse view.

**Performance:** two queries (all folders + all files for the library). For the sizes
in scope (management_reviews ≈ 19 folders / 71 files; pms ≈ 15/45; rm ≈ 6/11) this
is negligible. Add a QUERY_BUDGET guard of 10 in the test.

### B3 — Preserve existing functionality

- The existing `?folder_id=` URL pattern still works for deep-links (e.g. from the
  move-document modal). In `_render_library()`, when accordion mode AND `folder_id`
  is present in the query string, just ignore `folder_id` and render the full tree
  (since the user can see the target folder expanded in the tree).
- Admin upload/create-folder still POSTs to the same endpoints — no new routes.
- Staff read-only model is unchanged: view/download only, no upload/create controls.

---

## Task C — Dashboard restructuring

### Quality Management column — new card order

Replace the entire Quality Management column block in `index.html` so cards appear in
this exact order:

1. **QM Documents** → `doc_control.browse` (unchanged)
2. **Design & Development Records** → `admin_docs.dhfs`
   (move up from position 5; description: "DHFs, DMR, project archives, and design
   control records")
3. **Quality Planning** → `admin.quality_objectives`
   (move up from position 7; description: "QM.SLQ037 quality objectives tracked
   against targets")
4. **Management Reviews & Audits** → `admin_docs.management_reviews`
5. **Post Market Surveillance** → `admin_docs.post_market_surveillance`
6. **Risk Management** → `admin_docs.risk_management`

**Remove** the Regulatory Standards card from this column entirely.

### QMS System column — add Regulatory Standards

Insert a **Regulatory Standards** card into the QMS System column after the CAPAs
card and before the Reports card:

```html
{% if has_any_perm("admin.view", "staff.view") %}
<a class="card card--link dash-card" href="{{ url_for('admin_docs.regulatory_standards') }}">
  <h3 class="dash-card-title">Regulatory Standards</h3>
  <p class="muted dash-card-desc">ISO 13485, ASTM, 510(k)s, and FDA registrations</p>
</a>
{% endif %}
```

---

## Deploy Discipline

- No migrations.
- Full test suite must pass.
- Import guard must pass.
- Single migration head unchanged.

Tests to add/update (`tests/test_p21_accordion_browse.py`):
- Browse view: document rows contain `class="...accent..."` or inline style confirming
  link color (or assert `<summary>` contains anchor tag).
- Browse view: subsection with one SOP group — JS auto-open attribute or `data-*` marker
  present (assert the JS block exists in the template).
- `qms_index.classify("QM.SLQ045")` returns subsystem `"Purchasing & Suppliers"`.
- Accordion: `GET /admin/management-reviews` returns 200 and contains `<details` for
  admin and staff.
- Accordion: `GET /admin/management-reviews?q=IA2025` returns flat search results (no
  `<details>` tree).
- Accordion: staff user can GET management-reviews (200), cannot POST create-folder
  (302 or 403).
- Dashboard: Quality Management column order — "Design & Development Records" card
  appears before "Management Reviews" card in the response.
- Dashboard: "Regulatory Standards" card appears in QMS System column.
- Dashboard: "Regulatory Standards" card does NOT appear in Quality Management column.

---

## Deliverables

1. Browse view: document rows visually "clickable"; single-item subsections auto-expand;
   Receiving SOP in Purchasing & Suppliers.
2. Management Reviews, Post-Market Surveillance, and Risk Management all render the
   accordion full-tree view — no folder-by-folder page navigation.
3. Dashboard Quality Management column: 6 cards in new order, no Regulatory Standards.
4. Dashboard QMS System column: Regulatory Standards added after CAPAs.
5. Full suite green; coordinator confirms all four affected pages on the live site.
