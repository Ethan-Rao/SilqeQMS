# Phase 3 — Prompt 20: QM Documents Browse View + Library Restructure

## Context

This prompt redesigns how users navigate to and within controlled QM documents.
The 94 released controlled documents (SOPs, forms, templates, travelers) are already
in the Document Control EDMS. This prompt surfaces them in a new, user-friendly browse
view organized by QMS subsystem with expandable accordion groups, replaces the current
admin_docs "qms_documents" library as the primary navigation target, renames the DHF
library, and moves two dashboard cards.

A separate coordinator-run script (Task E) will migrate folder records in the database
(no S3 changes needed for any of the data moves — storage keys are unchanged).

---

## Task A — New `/admin/documents/browse` route and template

### Route

Add `GET /admin/documents/browse` to `app/eqms/modules/document_control/admin.py`,
gated by `docs.view` (staff + admin). This is a read-only page — no write actions.

### Data model

Query all `Document` records whose `status == "Released"`. For each document:
- Use `classify(doc.doc_number)` from `qms_index.py` to get its `subsystem`
- Use `slq_family(doc.doc_number)` to get its SLQ family number
- Use the `doc_type` field to distinguish parent SOPs/WIs/Policies from child forms,
  templates, and travelers

**Grouping logic:**
1. Within each subsystem, identify **parent documents** (doc_type NOT IN
   `["Form", "Template", "Traveler"]`) and **child documents** (doc_type IN
   `["Form", "Template", "Traveler"]`).
2. Group children under their parent by shared SLQ family number. A child with no
   matching parent in the same subsystem is treated as a "standalone child" and listed
   without nesting.
3. Within a subsystem, order parent groups by: (a) number of children descending
   (most forms first — these are the most-used workflows), then (b) SLQ family number
   ascending.
4. Each document links to its existing `doc_control.document_detail` page.

**Subsystem order** (configure this as an ordered list in the route, not in qms_index,
so it can be tuned without changing the classification map):

```python
BROWSE_SUBSYSTEM_ORDER = [
    "Production & Service",
    "Equipment & Calibration",
    "Purchasing & Suppliers",
    "Nonconforming Material",
    "CAPA",
    "Post-Market",
    "Audits",
    "Management",
    "Quality Planning",
    "Training",
    "Design Control",
    "Risk Management",
    "Document Control",
    "Sales & Customer",
    "Regulatory",
    "Administration Forms",
    "Unclassified",
]
```

Any subsystem returned by `classify()` that is not in this list should be appended at
the end before "Unclassified".

**Administration Forms subsystem — special handling:**

The `forms_templates_travelers` admin_docs library contains administration forms
(files with `AD.` prefix) that are not in Document Control. Include these in the
"Administration Forms" section of the browse page by also querying
`AdminDocFile` records from the `forms_templates_travelers` library where the filename
does NOT contain "Completed" in the folder path (i.e. skip files inside any folder
whose name contains "Completed" — those are filled records, not blank templates).

Each admin_docs file in this section renders as a flat row (no parent SOP accordion)
with: filename, folder name, and a View/Download link pointing to
`url_for('admin_docs.admin_docs_document_view', doc_id=f.id)`.

Also add `_BY_DOC_NUMBER` overrides in `qms_index.py` for any `AD.` prefix documents
that already exist in Document Control (if any), mapping them to
`QmsClassification("Administration", "Administration Forms")`.

### Template: `admin/document_control/browse.html`

Layout:
- Breadcrumb: Dashboard / QM Documents
- Page title: "QM Documents" with a subtitle "Active controlled documents — click any
  SOP to view, expand to see associated forms and templates"
- Optional inline search box (`?q=`) that filters the visible groups client-side (JS
  only, no server round-trip needed for a ~100 doc set)
- One card per subsystem, initially **collapsed**. Clicking the subsystem header
  expands it to reveal its document groups.
- Within a subsystem card, each parent SOP is a row. If it has children, the row has
  an expand toggle (`▶ / ▼` or `+/-`) that reveals the child documents indented
  beneath it inline (no page navigation).
- Each document row shows: doc number, title, current revision badge, status badge.
  The doc number/title is a hyperlink to `doc_control.document_detail`.
- Standalone children (no parent in subsystem) are shown in a final "Other" group
  within the subsystem.
- Subsystem sections with zero documents are omitted entirely.
- Empty state if `?q=` produces no matches.

**Accessibility**: use `<details>/<summary>` HTML elements for both the subsystem
cards and the individual SOP expand rows. This is keyboard-navigable natively, requires
no JS for basic expand/collapse, and works cleanly with the existing dark-theme CSS.
Add JS only for the optional client-side search filter.

**Performance**: eager-load `current_revision` with `selectinload`. This is a
constant-query page (2 queries: documents + revisions).

**Staff-accessible**: all document links open the existing detail/viewer routes, which
are already gated by `docs.view`. No new permissions needed.

---

## Task B — Dashboard updates

### B1 — QM Documents card

The "QM Documents" card in the Quality Management column currently links to
`url_for('admin_docs.qms_documents')`. Change it to `url_for('doc_control.browse')`.

Update the card description to: "Active SOPs, forms, templates, and travelers — 
grouped by workflow area."

### B2 — Quality Objectives → rename to Quality Planning

In the dashboard template, rename the "Quality Objectives" card in the QMS System
column to **"Quality Planning"**. Move the card from the QMS System column to the
**Quality Management column** (at the bottom of that column, after Risk Management).

The URL stays `url_for('admin.quality_objectives')` — route/view unchanged. Update only
the dashboard card label, description, and column placement.

Update the Quality Objectives page title from "Quality Objectives" to
"Quality Planning (QM.SLQ037)".

### B3 — Remove the stale QM Documents admin_docs library card

After this change, the `qms_documents` admin_docs library is no longer a primary
navigation target (its remaining contents will be accessed via search or direct URL).
There is no new card needed — the browse view replaces it. No code deletion required,
just the card link change in B1.

---

## Task C — Rename Design History Files library to "Design & Development Records"

In `app/eqms/modules/admin_docs/admin.py`, update the `LIBRARIES` dict:
```python
"dhfs": "Design & Development Records",
```

Update the `LIBRARY_ENDPOINTS` dict entry label (if any). Update the dashboard card in
`index.html`:
- Title: **"Design & Development Records"**
- Description: "DHFs, DMR, project archives, and design control records"

No migration needed — the database `library_key` stays `"dhfs"`.

---

## Task D — Remove "QM Documents" from Quality Management column description note

Since the `qms_documents` library is now navigated via browse, update the existing
"Management Reviews & Audits" and other Quality Management column cards to ensure none
reference the old admin_docs library by name in their descriptions (a minor text-only
cleanup pass).

---

## Task E — Coordinator-run data migration scripts (do NOT commit)

Write two gitignored one-off scripts with `DRY_RUN = True` guards:

### `scripts/_migrate_qm_library_folders.py`

Move the following admin_docs folder trees from `library_key = "qms_documents"` to
`library_key = "dhfs"` by updating the `library_key` field on all affected
`AdminDocFolder` and `AdminDocFile` records. No S3 operations needed.

Folders to move (by current name, verify by name before moving — do not hardcode IDs):
- `"Device Master Record"` (top-level folder in qms_documents) + all its descendant
  folders and files
- `"Project Archives"` (top-level folder in qms_documents) + all descendant folders
  and files

Folders to leave in place (do NOT move):
- `"DCO Log and Change Orders"` — stays in qms_documents, accessible via search
- `"Quality Planning"` — move its 2 files to a new subfolder called "Quality Planning"
  inside the `management_reviews` library's root, then delete the empty folder
- Any other folders not in the above list

Script must print a clear dry-run report and commit on `DRY_RUN = False`.

---

## Task F — qms_index.py extension

The browse view will surface all 94 released documents. After implementing the route,
run the dev local import corpus and check which documents land in "Unclassified".
Update `_BY_SLQ_FAMILY` in `qms_index.py` to cover any SLQ families that exist in the
released corpus but are currently unmapped (i.e., return `UNCLASSIFIED`).

Also check whether `doc_type` values in the database are consistent. The types needed
are: `"SOP"`, `"Work Instruction"`, `"Policy"`, `"Form"`, `"Template"`, `"Traveler"`,
`"Manual"`. If any documents have an unusual or missing `doc_type`, add them to
`_BY_DOC_NUMBER` overrides with the correct classification so they appear in the right
group.

---

## Deploy Discipline

- Tasks A–D: code changes, no migration
- Task E: coordinator-run scripts, gitignored, not deployed
- Task F: `qms_index.py` edit, no migration
- Full test suite must pass
- Single migration head unchanged
- Import guard must pass

Tests to add (in `tests/test_p20_qm_browse.py`):
- `GET /admin/documents/browse` returns 200 for admin and staff (`docs.view`)
- Page contains at least one `<details>` element for subsystem sections
- Query `?q=SLQ016` returns content including the CAPA SOP row
- "Production & Service" section appears before "Design Control" section in the response
  (verifying subsystem ordering)
- Staff user can reach the page and see document links (read-only confirmed)

---

## Deliverables

1. `/admin/documents/browse` live — accordion grouped by subsystem, forms expandable
   under parent SOPs.
2. Dashboard QM Documents card → new browse view.
3. Quality Planning card moved to Quality Management column.
4. Design History Files library renamed "Design & Development Records".
5. `scripts/_migrate_qm_library_folders.py` ready for coordinator dry-run + execution.
6. qms_index.py covers all released documents (no gaps in Unclassified after task F).
7. Full suite green; coordinator runs migration script and confirms both the browse
   page and the Design & Development Records library on the live site before Prompt 21.
