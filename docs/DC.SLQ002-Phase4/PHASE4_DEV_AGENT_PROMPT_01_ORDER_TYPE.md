# Prompt P4-01 — Explicit sales-order type, NRE classification fix, re-import data-loss fix

## Context

You are the Phase 4 Dev Agent for the Silq eQMS platform (Flask + SQLAlchemy modular monolith,
DigitalOcean App Platform, Postgres, Spaces). You have full repository access. You own the
entire mechanical pipeline for this change set: writing code, writing tests, creating the
migration, running the local gate, committing, pushing to `main`, and running the data scripts
(dry-run first, then `--execute`). **The operator is not a coder and will perform no
code-level actions.** Do not ask him to run anything, commit anything, or execute a script.

Deployment is push to `main`. DigitalOcean builds the image, runs `python scripts/release.py`
as the pre-deploy step (`alembic upgrade head`, then idempotent permission/role/admin seeding),
then rolls the component. **There is no CI.** The local gate below is the only thing standing
between your commit and production.

**Current Alembic head: `e7f8a9b0c1d2`.** Your migration must chain from exactly this revision.

### The problem this fixes

Catheter vs NRE classification is currently *inferred*, in two places, by rules that disagree:

- At import time, `_is_catheter_order` in `app/eqms/modules/rep_traceability/admin.py` treats
  an order with **no parsed line items** as a catheter order ("parse error, not NRE").
- At dashboard time, `_nre_customers` in `app/eqms/modules/nre_projects/admin.py` treats a
  customer with orders, no matched distribution, and no catheter-SKU order lines as NRE, and
  excludes `customer_type == "catheter"` unconditionally.

**NRE sales-order PDFs are free text and contain no parseable line-item table.** This is a
confirmed fact about the source documents, not a parser defect. So every NRE order imports
with zero lines, is classified as *catheter*, is given a Ship-To facility identity, is stamped
`customer_type = "catheter"`, and is then permanently invisible to the NRE dashboard. This is
why the NRE dashboard went empty after the operator's most recent import.

It is compounded by the re-import path, which overwrites `SalesOrder.customer_id`
unconditionally. When the recomputed facility key does not match an existing name-keyed NRE
customer, a new catheter customer is created and the order is moved to it, leaving the original
customer with zero orders and therefore also absent from the dashboard.

Separately, both import paths delete **every** `OrderPdfAttachment` row matching
`sales_order_id`, including packing slips (which carry both `sales_order_id` and
`distribution_entry_id`), and delete the Spaces blob too. Packing slips are device-traceability
evidence under 21 CFR 820 / ISO 13485. This is data loss and it stops in this change set.

The fix is to stop inferring and store the classification explicitly on the sales order, kept
current automatically but always overridable by the operator.

---

## Decisions (do not re-ask)

| Topic | Decision |
| --- | --- |
| Where the type lives | A new `order_type` column on `sales_orders`. Not on `Customer`. |
| Stored values | `cleartract_distribution`, `cleartract_in_process`, `cleartract_delivery`, `nre_project` |
| Display labels (exact) | "ClearTract Distribution", "ClearTract In Process Order", "ClearTract Delivery", "NRE Project" |
| Dropdown order | ClearTract Distribution, ClearTract In Process Order, ClearTract Delivery, NRE Project |
| Automatic maintenance | The system recomputes `order_type` whenever the evidence changes, **unless** the operator has set it manually. |
| Manual override | Once the operator sets the type by hand, `order_type_is_manual` becomes true and automation must never change that order's type again. |
| Classification rule (in order) | 1. any linked distribution with `source == "shipstation"` -> `cleartract_distribution`; 2. any other linked distribution -> `cleartract_delivery`; 3. no linked distribution but at least one catheter-SKU line -> `cleartract_in_process`; 4. otherwise -> `nre_project` |
| Review flag | `order_type_needs_review = True` only in case 4 (classified NRE purely by absence of evidence). Cases 1-3 are confident and set it False. |
| Clearing the review flag | Cleared automatically when the order reclassifies to any ClearTract type, and cleared when the operator sets the type manually. |
| Backfill | Every existing sales order gets a type, using the same rule. Dry-run first, then `--execute`. |
| `customer_type` column | Stays in the schema. Stops being the classification mechanism. Do **not** drop it, do not migrate it away. |
| NRE dashboard source of truth | `SalesOrder.order_type == "nre_project"`. The dashboard must no longer consult `customer_type` or infer from matched distributions. |
| NRE dashboard date default | Unchanged: current calendar quarter to today. Additionally show how many NRE orders fall outside the selected range. |
| Re-import and `customer_id` | Never repoint an existing order's `customer_id`. If the parsed customer differs from the stored one, record an audit event and surface a count in the flash message. |
| Re-import and attachments | Delete only attachments where `pdf_type == "sales_order_page"` **and** `distribution_entry_id IS NULL`. Preserve everything else, including packing slips. |
| `source` column | Keep it in the database. Remove it from the Sales Orders list table and filters. Keep it visible on the sales-order detail page. |
| Permissions | No new permissions. Viewing uses `sales_orders.view`, changing the type uses `sales_orders.edit`. Do **not** add anything to `scripts/init_db.py`. |
| Tracker recovery | Investigate via the audit trail and report. Do not fabricate values. |

---

## Task A — Schema and migration

**Files:** `app/eqms/modules/rep_traceability/models.py`, new file under `migrations/versions/`

1. Add three columns to `SalesOrder`:
   - `order_type: Mapped[str | None] = mapped_column(String(32), nullable=True)`
   - `order_type_is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")`
   - `order_type_needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")`
2. Add `Index("idx_sales_orders_order_type", "order_type")` to `__table_args__`.
3. Create one Alembic migration with `down_revision = "e7f8a9b0c1d2"`. Additive only: the two
   booleans are NOT NULL **with a server default** (safe against live data); `order_type` is
   nullable and is populated by the backfill script in Task C, not by the migration.
4. `python -m alembic heads` must print exactly one head afterwards.

Do not add a CHECK constraint on `order_type`. Validation lives in the service layer so that
adding a value later does not require a migration against live data.

---

## Task B — Classification service

**Files:** new `app/eqms/modules/rep_traceability/order_type.py`

Create the single source of truth for order typing. Nothing else may hardcode these strings.

1. Module constants:

```python
ORDER_TYPE_CLEARTRACT_DISTRIBUTION = "cleartract_distribution"
ORDER_TYPE_CLEARTRACT_IN_PROCESS = "cleartract_in_process"
ORDER_TYPE_CLEARTRACT_DELIVERY = "cleartract_delivery"
ORDER_TYPE_NRE_PROJECT = "nre_project"

ORDER_TYPE_LABELS = {...}          # stored value -> exact display label
ORDER_TYPE_CHOICES = [...]         # list of (value, label) in the dropdown order above
VALID_ORDER_TYPES = frozenset(ORDER_TYPE_LABELS)
```

2. `classify_order_type(s, order) -> tuple[str, bool]` returning `(order_type, needs_review)`,
   implementing the rule in the Decisions table exactly. Use `CATHETER_SKUS` and
   `sales_order_has_catheter_sku` from `app/eqms/modules/rep_traceability/service.py` rather
   than re-deriving the SKU set. Query linked distributions via
   `DistributionLogEntry.sales_order_id == order.id`; do not rely on a lazy relationship being
   loaded and fresh.

3. `apply_order_type(s, order, *, user=None) -> bool` — the automatic path:
   - Return `False` immediately if `order.order_type_is_manual` is true.
   - Compute the classification, assign `order_type` and `order_type_needs_review`.
   - If either value changed **and** the order previously had a non-null `order_type`, record
     an audit event `sales_order.order_type_auto` with metadata
     `{"before": ..., "after": ..., "needs_review": ...}`. Do not emit an event for the initial
     assignment on a brand-new order; that is noise.
   - Return whether anything changed.

4. `set_order_type_manual(s, order, new_type, *, user) -> None` — the operator path:
   - Raise `ValueError` if `new_type` not in `VALID_ORDER_TYPES`.
   - Set `order_type = new_type`, `order_type_is_manual = True`,
     `order_type_needs_review = False`.
   - Record an audit event `sales_order.order_type_set` with `{"before": ..., "after": ...}`.

Import lazily inside functions where needed to avoid circular imports with `service.py`.

---

## Task C — Automatic maintenance hooks

`apply_order_type` must be called at every point where the evidence for a classification can
change. Add the call at **all** of these sites, each guarded so a failure cannot abort the
surrounding operation (log and continue):

**Files:** `app/eqms/modules/rep_traceability/service.py`,
`app/eqms/modules/rep_traceability/admin.py`,
`app/eqms/modules/shipstation_sync/service.py`, `app/eqms/admin.py`

1. `create_distribution_entry` — after the entry is flushed, if it has a `sales_order_id`,
   apply to that order. This covers manual entry, CSV import and ShipStation in one place.
2. `update_distribution_entry` — if `sales_order_id` changed, apply to both the previous and
   the new order.
3. `delete_distribution_entry` — capture `sales_order_id` before deletion and apply to that
   order after the delete is flushed (an order can drop from Distribution back to In Process).
4. `rematch_unmatched_distributions_for_order` — apply to the order at the end.
5. Both sales-order PDF import paths in `admin.py` (bulk at approximately line 2395 and single
   at approximately line 3140) — apply after the order and its lines are created or updated.
   For a newly created order this is what sets the initial type.
6. `run_sync` in `shipstation_sync/service.py` — after a distribution insert succeeds, apply to
   the linked sales order.
7. `admin.unmatched_distribution_link` and `admin.unmatched_distribution_clear` in
   `app/eqms/admin.py` — apply to the affected order(s).

---

## Task D — Backfill script

**Files:** new `scripts/backfill_order_types.py`

1. Dry-run by default; writes only with an explicit `--execute` flag. Add `--force` to
   recompute orders that already have a type (default is to fill only `order_type IS NULL`).
2. Use `classify_order_type` — do not reimplement the rule.
3. Never overwrite an order where `order_type_is_manual` is true.
4. Report, in ASCII only (no arrows, no em-dashes — non-ASCII output has caused
   `UnicodeEncodeError` crashes mid-run on PowerShell):
   - mode line (`DRY RUN` or `EXECUTE`)
   - orders considered
   - a count per resulting type
   - the number flagged `needs_review`
   - **a list of every customer with `customer_type == "nre"` whose orders did not classify as
     `nre_project`** (order number, customer name, resulting type). These are cases where the
     operator's earlier manual override disagrees with the evidence and he needs to see them.
5. Follow the existing pattern in `scripts/_backfill_nre_sales_order_fields.py` for engine and
   session setup.
6. Run the dry-run, report the counts in your completion report, then run with `--execute`
   against production and report the final counts.

---

## Task E — Sales Orders list: type dropdown replaces Source

**Files:** `app/eqms/modules/rep_traceability/admin.py`,
`app/eqms/templates/admin/sales_orders/list.html`

This page is the operator's hub for triaging orders. It is at `/admin/sales-orders`.

1. New route `POST /admin/sales-orders/<int:order_id>/order-type`, endpoint
   `rep_traceability.sales_order_set_type`, `@require_permission("sales_orders.edit")`.
   Read `order_type` from the form, call `set_order_type_manual`, commit, flash a short
   confirmation, and redirect back preserving the current query string (accept a `next` form
   field carrying the filter query string, as the NRE templates already do). Invalid values
   flash an error and change nothing.
2. In `list.html`, replace the **Source** column with a **Type** column. The cell is an inline
   dropdown following the working pattern in
   `app/eqms/templates/admin/nre_projects/index.html` around line 201: a `<form method="post">`
   containing `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">` and a
   `<select ... onchange="this.form.submit()">`. No new JavaScript, no fetch. Render plain text
   instead of the dropdown when `has_perm("sales_orders.edit")` is false.
3. All URLs via `url_for(...)`. Hardcoded `/admin/...` strings have broken repeatedly.
4. Replace the **Source** filter dropdown with a **Type** filter using the same labels, plus an
   "All Types" option. Remove `source` from the filter dict and from the pagination query
   strings; add `order_type` and `needs_review` in their place.
5. Add a **Needs review** filter (a checkbox or an option on the Type filter — your choice,
   keep it plain) that shows only orders with `order_type_needs_review` true, and show the
   count of flagged orders near the top of the page as short plain text, for example
   `12 need review`. No subtitle, no explanatory sentence.
6. On flagged rows, show a short plain marker next to the dropdown. The word "Needs review" is
   sufficient. Do not invent an icon language.
7. Add `order_type` and `needs_review` to the `sales_orders_list` query filters, and keep the
   existing status, customer, date and search filters working.
8. UI language: short, plain, list-like. No internal document numbers in labels. No
   self-describing subtitles.

Also, on `app/eqms/templates/admin/sales_orders/detail.html`, show the order type and, if it is
not already displayed, the `source` value. Read-only on the detail page is fine for this prompt.

---

## Task F — NRE dashboard driven by order type

**Files:** `app/eqms/modules/nre_projects/admin.py`,
`app/eqms/templates/admin/nre_projects/index.html`

1. Reimplement `_nre_customers(s)` to return customers having at least one `SalesOrder` with
   `order_type == "nre_project"`, ordered by `facility_name`. **Remove** the dependence on
   `Customer.customer_type`, on "has orders but no matched distribution", and on the
   catheter-SKU subquery. Keep the function name and docstring accurate to the new rule.
2. Everywhere the NRE page lists a customer's orders (the index expand panels, the dashboard
   table, and `nre_customer_detail`), restrict to `order_type == "nre_project"` orders. A
   customer must never show a ClearTract order on the NRE page.
3. Dashboard metrics (`dash_project_count`, `dash_customer_count`, `dash_revenue`,
   `dash_missing_amounts`) count only `nre_project` orders inside the date window. Keep the
   current-quarter default and the existing `nre_invoiced_amount` weighting untouched.
4. Add a count of `nre_project` orders that fall **outside** the selected date range, and
   render it as one short plain line when the in-range table is empty, for example
   `No orders in this range. 24 NRE orders outside it.` This exists so an empty dashboard is
   never mistaken for missing data again.
5. `nre_refresh_folders` uses `_nre_customers`, so it inherits the new rule. Confirm it still
   only creates folders for NRE customers and their `nre_project` orders.

---

## Task G — Stop the re-import from destroying data

**Files:** `app/eqms/modules/rep_traceability/admin.py`

Three fixes, in both the bulk import path (existing attachment deletion at approximately line
2665) and the single-file import path (approximately line 3303).

1. **Preserve packing slips.** Narrow the attachment deletion to
   `pdf_type == "sales_order_page"` **and** `distribution_entry_id IS NULL`. Everything else
   survives, in the database and in Spaces. This is the highest-priority fix in this prompt.
2. **Never repoint the customer.** Remove the unconditional
   `existing_order.customer_id = customer.id` on re-import. If `existing_order.customer_id` is
   already set and differs from the newly matched customer, leave the order alone and record an
   audit event `sales_order.customer_mismatch_on_reimport` with metadata
   `{"order_number": ..., "stored_customer_id": ..., "stored_customer_name": ...,
   "parsed_customer_id": ..., "parsed_customer_name": ...}`. Count these and add a short
   sentence to the import flash message when the count is non-zero. Only assign `customer_id`
   when it is currently null.
3. **Remove the full-table scan.** `_find_sales_order_by_number` currently calls
   `s.query(SalesOrder).all()` and normalizes every row in Python, once per parsed page. Make
   it delegate to `find_sales_order_by_normalized_number` in
   `app/eqms/modules/rep_traceability/service.py`, so there is one lookup implementation.

Leave `order_date`, `ship_date` and the delete-and-recreate of order lines exactly as they are.
The PDF is authoritative for those and changing them is out of scope.

---

## Task H — NRE tracker history investigation and audit gap

**Files:** new `scripts/_diagnose_nre_tracker_history.py`,
`app/eqms/modules/nre_projects/admin.py`

The operator reports that the Upcoming NRE Invoice Tracker was emptied. Nothing in the import
path touches `NREProjectEntry`; the only code that deletes one is the explicit delete route,
which records an `nre_tracker.delete` audit event. **However, that event currently passes no
`metadata`, so the row contents were not captured.** Establish what happened and close the gap.

1. Write a **read-only** diagnostic script (no writes at all, no `--execute` flag). It must
   query `audit_events` for `entity_type == "NREProjectEntry"` and report, in ASCII only:
   action, actor email, timestamp, entity id, and any metadata, ordered oldest first; plus the
   current row count of `nre_project_entries` and of `nre_tracker_attachments`.
2. Run it against production and report the findings verbatim in your completion report. State
   plainly whether the deleted values are recoverable. **Do not fabricate or approximate any
   tracker values.** If orphaned `nre_tracker_attachments` rows survive, say so and list them —
   the attached files may still be in Spaces even if the ledger row is gone.
3. Close the gap: add a metadata snapshot to the tracker mutation audit events in
   `nre_projects/admin.py`. `nre_tracker_delete` and `nre_tracker_patch` must capture the
   before-state via the existing `_entry_to_dict(entry)` helper; `nre_tracker_create` and
   `nre_tracker_upsert` must capture the resulting state. This makes a future deletion
   recoverable.
4. Note that the local `.env` Spaces credentials are stale (`HeadBucket` returns 403), so verify
   credentials before trusting any storage-backed result. This script only reads the database,
   so it should be unaffected — but say so explicitly in your report.

---

## Task I — Tests

**Files:** new `tests/test_p4_01_order_type.py`, plus updates to existing tests

Follow the existing fixture pattern (no shared `conftest.py`): per-test SQLite file DB via
`monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")`, `create_app()`,
`Base.metadata.create_all`, `application.config["_schema_health_ok"] = True`, seed rows inline.
See `tests/test_p41_shipto_facilities.py` and `tests/test_p31_nre_projects.py` for models.

New coverage, at minimum:

1. `classify_order_type` returns `cleartract_distribution` for a linked ShipStation
   distribution; `cleartract_delivery` for a linked manual distribution;
   `cleartract_in_process` for a catheter-SKU line with no distribution; and
   `(nre_project, True)` for an order with no lines and no distribution.
2. An order with lines but no catheter SKU and no distribution classifies as `nre_project`.
3. `apply_order_type` does **not** change an order where `order_type_is_manual` is true.
4. `set_order_type_manual` sets the manual flag, clears the review flag, and rejects an invalid
   value.
5. Linking a distribution to an In Process order flips it to a ClearTract type and clears the
   review flag; deleting the last distribution moves it back to `cleartract_in_process`.
6. The NRE dashboard lists a customer whose order is typed `nre_project`, and does **not** list
   a customer whose only order is typed `cleartract_in_process` — including the case where that
   customer's `customer_type` is `"catheter"`, which is the exact production bug.
7. **Regression test for the data loss:** a sales order with a packing-slip attachment
   (`pdf_type="packing_slip"`, `distribution_entry_id` set) retains that attachment after a
   re-import, while the `sales_order_page` attachment is replaced.
8. **Regression test:** re-importing an order whose `customer_id` is already set does not change
   `customer_id`.
9. The order-type POST route requires `sales_orders.edit` (staff gets 403) and rejects a request
   with no CSRF token.

Existing tests that assert the **old** classification rule will fail and must be updated to the
new rule, not deleted. Expect at least `tests/test_p31_nre_projects.py::test_index_classification`
and `tests/test_p41_shipto_facilities.py::test_auto_nre_excludes_catheter_sku_without_distribution`
to need rewriting in terms of `order_type`. Preserve the intent of each test.

---

## Task J — Deploy and completion report

1. Run the full gate and report the actual output:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m alembic heads
python -c "import app.wsgi"
```

The baseline before your change is 375 passed, 1 skipped. Report the new totals.
`alembic heads` must print exactly one head.

2. Commit and push to `main`. Confirm the DigitalOcean build, the pre-deploy `release.py` step,
   and the health check all succeeded. The operator cannot see the build banner, so state the
   deploy status explicitly.
3. Run the Task D backfill dry-run against production, report the counts, then run it with
   `--execute` and report the final counts.
4. Run the Task H diagnostic against production and report its output.
5. Your completion report must contain:
   - the migration revision id
   - new routes added, with their endpoint names
   - exactly where in the UI each change appears
   - the backfill counts per type, the `needs_review` count, and the list of `customer_type ==
     "nre"` disagreements
   - the tracker audit findings, and a plain statement of whether the values are recoverable
   - every judgment call you made, and anything you chose not to do
   - the final test totals and deploy status

---

## Out of scope

Do not do any of the following in this change set. Each is a later Phase 4 prompt.

- Moving the Sales Order PDF import or the distribution CSV import to Admin Tools, or changing
  the distribution import page. (P4-02)
- Editing the matched customer or matched distributions from the sales-order detail page, and
  any customer re-keying or merging. (P4-03)
- Pairing NRE Invoice Tracker entries or their files to sales orders, and any unification of
  the tracker with the dashboard totals. (P4-04)
- Anything in Purchasing: invoice upload, Invoices Received, PO matching, "Other Payments",
  the PO Log reversal, PO open/closed, or the PO Log export. (P4-05, P4-06)
- Dropping or migrating away the `Customer.customer_type` column.
- Changing `order_date` / `ship_date` re-import behaviour.
- The auditor portal, and the `Auditor Files/` ignore rules.
- Adding new permissions or touching `scripts/init_db.py`.
- Rewriting git history to shrink the repository.

---

## Reference

**Models** — `app/eqms/modules/rep_traceability/models.py`: `SalesOrder`, `SalesOrderLine`,
`DistributionLogEntry`, `DistributionLine`, `OrderPdfAttachment`.
`app/eqms/modules/customer_profiles/models.py`: `Customer` (`customer_type` is one of `"auto"`,
`"catheter"`, `"nre"`; `company_key` is unique).
`app/eqms/modules/nre_projects/models.py`: `NREProjectEntry`, `NRETrackerAttachment`,
`NRE_DASHBOARD_STATUSES`, `nre_invoiced_amount`.

**Existing helpers you must reuse, not reimplement**
- `CATHETER_SKUS`, `sales_order_has_catheter_sku`, `normalize_order_number`,
  `find_sales_order_by_normalized_number`, `rematch_unmatched_distributions_for_order`,
  `sync_distribution_customer_from_sales_order` — all in
  `app/eqms/modules/rep_traceability/service.py`
- `_fill_so_parsed_fields`, `_is_catheter_order`, `_store_pdf_attachment`,
  `is_packing_slip_pdf_type` — `app/eqms/modules/rep_traceability/admin.py` and `utils.py`
- `record_event(s, actor=..., action=..., entity_type=..., entity_id=..., reason=...,
  metadata=...)` — `app/eqms/audit.py`
- `storage_from_config(current_app.config)`, and the write method is `storage.put_bytes`
  (there is no `storage.put`) — `app/eqms/storage.py`
- `require_permission` — `app/eqms/rbac.py`

**Note on `_is_catheter_order`:** it stays where it is and keeps its current behaviour, because
it drives *customer identity* selection (facility vs company) at import time, not the dashboard.
Do not repoint it at `classify_order_type`; the two answer different questions. Changing customer
identity selection is P4-03.

**Inline dropdown pattern to copy** — `app/eqms/templates/admin/nre_projects/index.html`
around lines 200-210.

**Distribution SKU constraint** — both `distribution_log_entries.sku` and
`distribution_lines.sku` are CHECK-constrained to `211810SPT`, `211610SPT`, `211410SPT`. A
linked distribution is therefore definitive proof of a catheter order, which is why rules 1 and
2 outrank the line-item check.

**Conventions**
- `url_for(...)` for every URL, including inside inline JavaScript.
- CSRF token on every state-changing route; inline `{{ csrf_token }}` in the form.
- Audit events for state changes on regulated records.
- Windows/PowerShell: no `&&` chaining, no bash heredocs, no non-ASCII characters in script
  output.
- Postgres is the deploy target. The local SQLite migration chain is broken at a Phase 3
  ancestor revision, so do not try to prove the migration by rebuilding SQLite from scratch;
  the test suite creates its schema with `Base.metadata.create_all`.

---

## Acceptance checklist

- [ ] Migration created with `down_revision = "e7f8a9b0c1d2"`; `alembic heads` prints one head
- [ ] `sales_orders` has `order_type`, `order_type_is_manual`, `order_type_needs_review`, and an index on `order_type`
- [ ] `order_type.py` holds the only definition of the four values and their exact labels
- [ ] `classify_order_type` implements the four-step rule and flags review only in the NRE-by-absence case
- [ ] `apply_order_type` never overrides an order whose type was set manually
- [ ] All seven maintenance hooks call `apply_order_type`, and a failure there cannot abort the surrounding operation
- [ ] Backfill script is dry-run by default, ASCII-only output, and lists `customer_type == "nre"` disagreements
- [ ] Backfill dry-run counts reported, then `--execute` run and final counts reported
- [ ] Sales Orders list shows a Type dropdown instead of Source, saving inline via a CSRF-protected POST
- [ ] Sales Orders list has a Type filter, a needs-review filter, and a plain flagged count
- [ ] Sales order detail page shows the order type and the source
- [ ] NRE dashboard selects customers and orders solely by `order_type == "nre_project"`
- [ ] NRE dashboard shows how many NRE orders fall outside the selected date range
- [ ] Re-import preserves packing-slip attachments and their Spaces blobs
- [ ] Re-import never repoints `customer_id`, and records an audit event on mismatch
- [ ] `_find_sales_order_by_number` no longer loads every sales order into memory
- [ ] Tracker audit events now capture a row snapshot; diagnostic script written and its production output reported
- [ ] New tests cover all nine cases in Task I, including both data-loss regressions
- [ ] Existing classification tests updated to the new rule with their intent preserved
- [ ] Full gate run and reported; pushed to `main`; deploy confirmed green explicitly
