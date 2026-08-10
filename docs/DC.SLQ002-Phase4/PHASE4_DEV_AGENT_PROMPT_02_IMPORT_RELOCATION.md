# Prompt P4-02 — Relocate imports to Admin Tools; reduce the distribution import page to packing slips

## Context

You are the Phase 4 Dev Agent for the Silq eQMS platform (Flask + SQLAlchemy modular monolith,
DigitalOcean App Platform, Postgres, Spaces). You own the entire mechanical pipeline for this
change set: code, tests, the local gate, commit, push, and running any scripts. **The operator
is not a coder and performs no code-level actions.** Never ask him to run, commit, or execute
anything.

Deployment is push to `main`. DigitalOcean builds, runs `python scripts/release.py` pre-deploy,
then rolls the component. **There is no CI** — the local gate is the only thing between your
commit and production.

**Current Alembic head: `f8a9b0c1d2e3`** (set by P4-01). **This change set requires no schema
change and no migration.** If you believe you need one, stop and re-read the tasks.

### Why this work exists

Importing sales-order PDFs is one of the operator's most frequent actions, and it is currently
buried three clicks deep behind a page that has nothing to do with it: Distribution Log ->
Import PDF -> Import Sales Orders. Sales orders are the entry point for the entire commercial
chain (they are triaged into catheter distributions or NRE projects, which P4-01 made explicit
via `SalesOrder.order_type`), so the import belongs somewhere prominent and stable.

The target information architecture:

| Page | Contains after this change |
| --- | --- |
| Admin Tools (`/admin/diagnostics`) | An **Imports** card as the very first card: Sales Order PDF import and Distribution CSV import |
| `/admin/distribution-log/import` | **Packing slips only** |
| `/admin/sales-orders/import-pdf` | Kept alive as a redirect to the Admin Tools Imports card |

The existing combined "PDF Import" page (`app/eqms/templates/admin/sales_orders/import.html`)
currently holds *both* the sales-order form and the packing-slip form. It is being split: the
sales-order form moves to Admin Tools, the packing-slip form moves to the distribution import
page.

---

## Decisions (do not re-ask)

| Topic | Decision |
| --- | --- |
| Where the sales-order import lives | An **Imports** card, positioned as the first card on the Admin Tools page, immediately after the "Admin Tools" header card and **above** the System Status band. |
| Anchor | The card carries `id="imports"`. Link to it with `url_for('admin.diagnostics', _anchor='imports')`. |
| What the Imports card contains | Sales Order PDFs (multi-file upload) first, Distribution CSV second, plus a link to Unmatched PDFs. Nothing else. |
| Where packing slips live | `/admin/distribution-log/import`, which becomes the packing-slip page. |
| CSV import forms | Reuse the existing POST endpoints. Do **not** create new POST routes for either import. |
| Old URLs | `sales_orders_import_pdf_get` stays as a route and redirects to the Admin Tools Imports anchor, so existing links and bookmarks keep working. Do not delete it. |
| Post-import destination | After a sales-order import or a CSV import, land back on the Admin Tools Imports card. After a packing-slip import, land back on the distribution import page. |
| Permission gating | Unchanged. Do **not** modify `_diagnostics_allowed`, `require_permission` decorators, or `scripts/init_db.py`. Import forms render conditionally on `has_perm('sales_orders.import')` and `has_perm('distribution_log.import')`. |
| Template file naming | Rename the distribution import template's purpose in place (`admin/distribution_log/import.html` keeps its path but its content becomes packing slips). Delete `admin/sales_orders/import.html` only if nothing renders it any more. |
| Reconciliation report | Read-only diagnostics in this change set. **Write nothing, change no data.** |

---

## Task A — Imports card at the top of Admin Tools

**Files:** `app/eqms/templates/admin/diagnostics.html`, `app/eqms/admin.py`

1. Insert a new card with `id="imports"` immediately after the existing "Admin Tools" header
   card (currently lines 4-11) and **before** the System Status band. It is the first thing the
   operator sees.
2. Heading: `Imports`. No subtitle, no explanatory sentence. UI language is short, plain and
   list-like; the operator has repeatedly rejected self-describing subtitles.
3. Inside, two sections in this order:
   - **Sales Order PDFs** — multi-file upload posting to
     `url_for('rep_traceability.sales_orders_import_pdf_bulk')`, `enctype="multipart/form-data"`,
     field name `pdf_files`, `accept=".pdf,application/pdf"`, `multiple required`. Keep the
     existing one-line helper text: "Multi-page PDFs are auto-split. Existing orders with
     matching numbers are replaced."
     Render only when `has_perm('sales_orders.import')`.
   - **Distribution CSV** — single-file upload posting to
     `url_for('rep_traceability.distribution_log_import_csv_post')`, field name `csv_file`,
     `accept=".csv,text/csv"`, `required`. Keep the existing expected-columns line and the
     dedupe-behaviour line from `admin/distribution_log/import.html` (lines 19 and 27-29).
     Render only when `has_perm('distribution_log.import')`.
4. Add a link to `url_for('rep_traceability.sales_orders_unmatched_pdfs')` labelled
   `Unmatched PDFs`, and a link to the packing-slip page
   (`url_for('rep_traceability.distribution_log_import_get')`) labelled `Packing slips`.
5. Carry over the pdfplumber guard: when `diag.pdf_dependencies.pdfplumber` is false, show the
   existing "PDF parsing unavailable" warning in place of the sales-order form rather than
   rendering a form that cannot work.
6. Carry over the submit-button disable-on-submit script from `sales_orders/import.html`
   (lines 51-70), adapted to the new form ids. Keep it plain and inline; no new dependencies.
7. `diagnostics()` in `app/eqms/admin.py` already passes `diag`, which carries
   `pdf_dependencies`. Add any additional template context you need there. Do not change the
   route's permission or the `_diagnostics_allowed()` check.

---

## Task B — Distribution import page becomes packing slips only

**Files:** `app/eqms/templates/admin/distribution_log/import.html`,
`app/eqms/modules/rep_traceability/admin.py`

1. Replace the contents of `admin/distribution_log/import.html` with a packing-slip page:
   - Title and heading: `Import Packing Slips`.
   - One form posting to `url_for('rep_traceability.packing_slips_import_bulk')`,
     `enctype="multipart/form-data"`, field name `pdf_files`, multiple, required. Keep the
     existing helper line from `sales_orders/import.html` line 44 ("Matched to distributions by
     tracking number or normalized order number. Does not create new orders. Re-upload replaces
     the prior packing slip for each matched distribution.").
   - A `Back` link to `url_for('rep_traceability.distribution_log_list')`.
   - Remove the CSV form, the "CSV Import" / "PDF Import (Sales Orders)" button row, and the
     `mode="csv"` concept.
2. The CSV error and duplicate blocks (current lines 32-55) are still rendered by
   `distribution_log_import_csv_post` on failure. Move those blocks to a **new** template
   `app/eqms/templates/admin/distribution_log/import_csv_result.html` and have
   `distribution_log_import_csv_post` render that on error or when duplicates were skipped,
   with a link back to `url_for('admin.diagnostics', _anchor='imports')`. Successful imports
   with no duplicates redirect to the Admin Tools Imports anchor with the existing flash.
3. `distribution_log_import_get` keeps its route and its `distribution_log.import` permission,
   and now renders the packing-slip page. Drop the `mode="csv"` argument.
4. `distribution_log_import_csv_get` currently redirects to `distribution_log_import_get`.
   Repoint it to `url_for('admin.diagnostics', _anchor='imports')`, since the CSV form now
   lives there.

---

## Task C — Repoint navigation and redirects

**Files:** `app/eqms/modules/rep_traceability/admin.py`, several templates

1. `sales_orders_import_pdf_get` (approximately line 3127): stop rendering
   `admin/sales_orders/import.html` and instead
   `return redirect(url_for('admin.diagnostics', _anchor='imports'))`. Keep the route and its
   permission so existing links and bookmarks continue to work.
2. Inside `sales_orders_import_pdf_bulk` and `sales_orders_import_pdf_post`, replace every
   `redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))` with a redirect to
   `url_for('admin.diagnostics', _anchor='imports')`, so the operator lands back where he
   started with the flash message intact rather than bouncing through a second redirect.
3. Inside `packing_slips_import_bulk`, replace every redirect to
   `sales_orders_import_pdf_get` with `url_for('rep_traceability.distribution_log_import_get')`.
4. `distribution_log_import_pdf_get` and `distribution_log_import_pdf_post` currently redirect
   to `sales_orders_import_pdf_get`. Repoint both to
   `url_for('admin.diagnostics', _anchor='imports')`.
5. Template link updates. In each case use `url_for(...)`; never a hardcoded `/admin/...`
   string, which has broken repeatedly when blueprints moved:
   - `admin/sales_orders/list.html` line 12: the `Import PDF` button points to the Admin Tools
     Imports anchor, and is wrapped in `{% if has_perm('sales_orders.import') %}`.
   - `admin/sales_orders/unmatched_pdfs.html` line 12: same treatment.
   - `admin/customers/detail.html` line 249: same treatment.
   - `admin/distribution_log/list.html` line 12: the `Import CSV` button becomes
     `Packing slips` pointing at `distribution_log_import_get`, wrapped in
     `{% if has_perm('distribution_log.import') %}`. The CSV import is now reached from Admin
     Tools.
   - `admin/diagnostics.html` lines 200-207, in the existing "Imports & Sync" column: remove
     the two now-duplicative cards ("Import CSV (Distributions)" and "Import Sales Order PDFs")
     and add a single card `Packing Slips` pointing at `distribution_log_import_get`. The
     LotLog, Disposition Log, ShipStation Sync and Equipment Import cards stay untouched.
6. Delete `app/eqms/templates/admin/sales_orders/import.html` once nothing renders it. Confirm
   by searching the repository for the filename before deleting.
7. Search the whole repository for any remaining reference to the endpoints you have changed and
   confirm none is left dangling. `python -c "import app.wsgi"` will not catch a bad
   `url_for` inside a template.

---

## Task D — Read-only reconciliation report

**Files:** new `scripts/_report_order_reconciliation.py`

The operator wants a later prompt to bring existing sales orders and distributions into
agreement. This script sizes that work. It is **read-only**: no writes, no `--execute` flag, no
session commit. ASCII output only — non-ASCII has caused `UnicodeEncodeError` crashes mid-run on
PowerShell.

Report all of the following:

1. Count of sales orders per `order_type`, plus the count with `order_type IS NULL` and the
   count with `order_type_needs_review` true.
2. For every order typed `cleartract_in_process` (catheter SKUs but no linked distribution):
   order number, order date, customer name, and **whether an unmatched distribution exists whose
   normalized order number matches**. Use `normalize_order_number` from
   `app/eqms/modules/rep_traceability/service.py`; do not reimplement it. Summarise as
   "N of M in-process orders have a candidate unmatched distribution".
3. Count of distributions with `sales_order_id IS NULL`, and how many of those have a sales
   order whose normalized order number matches (i.e. are linkable).
4. Count of customers with zero sales orders and zero distributions (empty shells), listing up
   to 40 with id and facility name.
5. Count of customers whose `customer_type == "catheter"` but whose only sales orders are typed
   `nre_project` — these are the identity mismatches left behind by the classification bug
   P4-01 fixed. List up to 40 with id, facility name and `company_key`. This sizes the customer
   re-keying work in P4-03.
6. Count of `nre_project` orders with a null `order_amount`.

Follow the engine and session setup pattern in
`scripts/_diagnose_nre_tracker_history.py`. Run it against production and paste the full output
into your completion report.

---

## Task E — Tests

**Files:** new `tests/test_p4_02_import_relocation.py`

Follow the existing fixture pattern (there is no shared `conftest.py`): per-test SQLite file DB
via `monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")`, `create_app()`,
`Base.metadata.create_all`, `application.config["_schema_health_ok"] = True`, seed permissions
/ roles / users inline. `tests/test_p4_01_order_type.py` and `tests/test_p14_phase6.py` are
good models, and `tests/test_p34_tracker_files_ncr.py` shows the file-upload pattern
(set `LOCAL_STORAGE_DIR`).

Cover at minimum:

1. Admin Tools renders an element with `id="imports"`, and the response body contains form
   actions for both `sales_orders_import_pdf_bulk` and `distribution_log_import_csv_post`.
2. The Imports card appears **before** the System Status band in the response body (compare
   string indexes).
3. `GET /admin/sales-orders/import-pdf` returns a redirect whose `Location` is the Admin Tools
   URL.
4. `GET /admin/distribution-log/import` renders the packing-slip form (action is
   `packing_slips_import_bulk`) and does **not** contain a `csv_file` input.
5. **End-to-end guard against a silently broken upload:** POST a small generated PDF to
   `sales_orders_import_pdf_bulk` with a valid CSRF token and assert the response redirects to
   the Admin Tools URL. This is the regression that matters most — the operator's daily action
   must not break because a form moved.
6. A staff user (who lacks `sales_orders.import`) does not see the sales-order form. Note that
   staff cannot reach Admin Tools at all, so assert this at the template-context level or via
   the sales-orders list page's `Import PDF` button being absent for staff.
7. Update any existing test that asserts against the old import pages or the old button labels.
   Expect `tests/test_p14_phase6.py` to reference Admin Tools content. Preserve each test's
   intent; do not delete coverage.

---

## Task F — Deploy and completion report

1. Run the full gate and report the actual output:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m alembic heads
python -c "import app.wsgi"
```

Baseline before your change is **387 passed, 1 skipped**. Report the new totals.
`alembic heads` must print exactly one head and it must still be `f8a9b0c1d2e3` — this change
set adds no migration.

2. Commit and push to `main`. Confirm the build, the pre-deploy `release.py` step, and the
   health check all succeeded. The operator cannot see the build banner, so state the deploy
   status explicitly.
3. Run the Task D reconciliation report against production and paste its full output.
4. Your completion report must contain:
   - every route whose behaviour changed, with endpoint names, and every route left as a redirect
   - every template changed, and the exact file you deleted (if any)
   - where in the UI each import now appears, and what the operator's new click path is
   - the full reconciliation report output
   - every judgment call you made, and anything you chose not to do
   - final test totals and deploy status

---

## Out of scope

Each of these is a later Phase 4 prompt. Do not start any of them.

- Editing the matched customer or matched distributions from the sales-order detail page, and
  any customer re-keying or merging. (P4-03)
- Pairing NRE Invoice Tracker entries or their files to sales orders. (P4-04)
- Anything in Purchasing: invoice upload, Invoices Received, PO matching, "Other Payments", the
  PO Log reversal, PO open/closed, or the PO Log export. (P4-05, P4-06)
- **Actually reconciling any data.** Task D reports only. Linking distributions, re-keying
  customers or deleting shells happens in a later prompt after the operator has seen the numbers.
- Any restructuring of the Admin Tools page beyond inserting the Imports card and adjusting the
  "Imports & Sync" cards named in Task C. The operator has further plans for this page.
- Changing `_diagnostics_allowed`, any `require_permission` decorator, or `scripts/init_db.py`.
- Changing the parsing behaviour of any import, the dedupe rules, or `order_type` classification.
- The auditor portal and the `Auditor Files/` ignore rules.

---

## Reference

**Routes involved** (all in `app/eqms/modules/rep_traceability/admin.py` unless noted)

| Endpoint | Current behaviour | After |
| --- | --- | --- |
| `admin.diagnostics` (`app/eqms/admin.py`) | Admin Tools page | Hosts the Imports card at the top |
| `rep_traceability.sales_orders_import_pdf_get` | Renders the combined PDF import page | Redirects to Admin Tools `#imports` |
| `rep_traceability.sales_orders_import_pdf_bulk` | Multi-file sales-order import POST | Unchanged logic; redirects to Admin Tools |
| `rep_traceability.sales_orders_import_pdf_post` | Single-file sales-order import POST | Unchanged logic; redirects to Admin Tools |
| `rep_traceability.packing_slips_import_bulk` | Packing-slip import POST | Unchanged logic; redirects to the packing-slip page |
| `rep_traceability.distribution_log_import_get` | Renders the CSV import page | Renders the packing-slip page |
| `rep_traceability.distribution_log_import_csv_get` | Redirects to the CSV import page | Redirects to Admin Tools `#imports` |
| `rep_traceability.distribution_log_import_csv_post` | CSV import POST | Unchanged logic; renders the new result template or redirects to Admin Tools |
| `rep_traceability.distribution_log_import_pdf_get` / `_post` | Redirect to the PDF import page | Redirect to Admin Tools `#imports` |
| `rep_traceability.sales_orders_unmatched_pdfs` | Unmatched PDF workspace | Unchanged; linked from the Imports card |

**Templates involved**
- `app/eqms/templates/admin/diagnostics.html` — Admin Tools; header card at lines 4-11, System
  Status band begins line 38, "Imports & Sync" column at lines 190-217
- `app/eqms/templates/admin/sales_orders/import.html` — source of both forms; deleted at the end
- `app/eqms/templates/admin/distribution_log/import.html` — becomes the packing-slip page
- `app/eqms/templates/admin/sales_orders/list.html`,
  `app/eqms/templates/admin/sales_orders/unmatched_pdfs.html`,
  `app/eqms/templates/admin/customers/detail.html`,
  `app/eqms/templates/admin/distribution_log/list.html` — link updates

**Conventions**
- `url_for(...)` for every URL, including inside inline JavaScript. Use
  `url_for('admin.diagnostics', _anchor='imports')` for the anchor form.
- CSRF token on every state-changing form: inline `<input type="hidden" name="csrf_token"
  value="{{ csrf_token }}">`. Both relocated forms are POSTs and both need it.
- `MAX_CONTENT_LENGTH` is 100MB app-wide; the bulk sales-order import additionally enforces
  10MB per file and 50MB total in the route. Do not change those limits.
- UI language: short, plain, list-like. No internal document numbers in labels. No
  self-describing subtitles.
- Windows/PowerShell: no `&&` chaining, no bash heredocs, no non-ASCII in script output.
- Postgres is the deploy target; the local SQLite migration chain is broken at a Phase 3
  ancestor, so never try to prove anything by rebuilding SQLite from scratch. Tests build their
  schema with `Base.metadata.create_all`.

---

## Acceptance checklist

- [ ] No migration added; `alembic heads` still prints exactly `f8a9b0c1d2e3`
- [ ] Admin Tools shows an `id="imports"` card as the first card, above System Status
- [ ] Imports card holds the Sales Order PDF form, then the Distribution CSV form, plus links to Unmatched PDFs and Packing slips
- [ ] Both relocated forms carry a CSRF token and post to the existing endpoints (no new POST routes)
- [ ] pdfplumber-unavailable warning replaces the sales-order form when the dependency is missing
- [ ] `/admin/distribution-log/import` is the packing-slip page and contains no CSV input
- [ ] CSV errors and skipped duplicates render via the new result template with a link back to Admin Tools
- [ ] `sales_orders_import_pdf_get` still resolves and redirects to Admin Tools `#imports`
- [ ] Sales-order and CSV imports land back on Admin Tools; packing-slip imports land back on the packing-slip page
- [ ] All four template link updates done via `url_for`, permission-gated where specified
- [ ] Duplicative "Imports & Sync" cards removed; a `Packing Slips` card added
- [ ] `admin/sales_orders/import.html` deleted and no reference to it remains
- [ ] Repository searched for dangling references to every changed endpoint
- [ ] Reconciliation script is read-only, ASCII-only, and its production output is in the report
- [ ] New tests cover all seven cases in Task E, including the end-to-end upload guard
- [ ] Existing tests touching the old import pages updated with intent preserved
- [ ] Full gate run and reported; pushed to `main`; deploy confirmed green explicitly
