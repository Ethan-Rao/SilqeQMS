# Prompt P4-03 — The sales-order detail page becomes the control surface

## Context

You are the Phase 4 Dev Agent for the Silq eQMS platform (Flask + SQLAlchemy modular monolith,
DigitalOcean App Platform, Postgres, Spaces). You own the entire mechanical pipeline: code, tests,
the local gate, commit, push, and running scripts. **The operator is not a coder and performs no
code-level actions.** Never ask him to run, commit, or execute anything.

Deployment is push to `main`. DigitalOcean builds, runs `python scripts/release.py` pre-deploy,
then rolls the component. **There is no CI** — the local gate is the only thing between your
commit and production.

**Current Alembic head: `f8a9b0c1d2e3`.** This change set needs **no migration** — see Task C for
why the one new stored value is already permitted by an existing check constraint.

**Baseline gate: 394 passed, 1 skipped.**

### Why this work exists

P4-01 made order type explicit. P4-02 moved the imports to Admin Tools. A read-only reconciliation
pass against production then produced the numbers below, and they define this change set.

**26 sales orders are typed `cleartract_in_process`** — real catheter line items, no linked
distribution. Every one is dated 2025 or later. Not one of them has a distribution anywhere in the
system sharing its order number, and there are no duplicate sales orders. So these are not
mislinked records; the distribution rows do not exist. Only four are recent (July–August 2026). The
operator has confirmed he still has **manual deliveries to upload** that will account for some of
them, which is exactly what the `cleartract_delivery` type is for.

**35 distributions have no sales order.** 31 are 2024 shipments and the system holds only one 2024
sales order, so those PDFs were simply never imported — the operator has explicitly said pre-2025
mismatches are not a concern. Three are Harbor-UCLA shipments that went out on 2026-08-10 and will
resolve when their PDFs are imported. The remaining one matters:

> Distribution `id=760`, ship date 2025-03-19, order number `SO 0000164`, facility
> `VAMC - LOMA LINDA`, SKU `211610SPT`. Sales order **`0000165`**, dated 2025-03-18, customer
> `VAMC - Loma Linda`, is sitting in `cleartract_in_process`. These are almost certainly one
> transaction with an off-by-one order number.

There is no way to fix that today from the sales-order page, and that is the gap this prompt
closes. Also note distribution `id=753` (ship 2025-02-21, `SO 0000145`) duplicates an order number
whose original shipment went out 2024-12-27 as `id=887`.

The operator's requirement, in his words: from the sales-order detail page *"I should be able to
edit the matched distributions or matched customers as necessary and have the rest of the system
update accordingly."*

---

## Decisions (do not re-ask)

| Topic | Decision |
| --- | --- |
| **No lateness logic** | **Do not build any "overdue", "aging", "late", "stale" or "should have shipped by now" feature.** No day thresholds, no derived warning states, no new dashboard tiles or counters of that kind. The operator's customers routinely place sales orders long before they expect delivery, so elapsed time carries no meaning here. Make the unmatched cases *easy to find and act on*, nothing more. This was an explicit instruction and it overrides any instinct to add a warning. |
| Cancelled orders | Add a **Cancelled** lifecycle state the operator can set on an order. A cancelled order stops being presented as awaiting shipment. |
| Where the work happens | The sales-order detail page (`/admin/sales-orders/<id>`). Do not build a new workspace page. The existing Admin Tools unmatched-distributions workspace stays as it is. |
| Customer editing scope | **Reassignment only** in this prompt: point the order at a different existing customer, or create a new one. |
| Customer merging and re-keying | **Out of scope here — it is P4-03B.** Do not merge customers, do not change `normalize_facility_name`, `canonical_customer_key`, `compute_facility_key_from_ship_to`, or `_is_catheter_order`. Changing customer identity rules in the same deploy as this UI work is the one combination most likely to damage regulated data, so it gets its own change set. |
| Order type on the detail page | Promote the read-only Type text to the same live dropdown the list already has. The operator has two misclassified orders to retype by hand. |
| Sales order is source of truth | When the order's customer changes, linked distributions follow it via the existing `sync_distribution_customer_from_sales_order`. |
| ShipStation probe | Read-only diagnostic. **No writes, no sync run, no `--execute`.** |

---

## Task A — Reassign the matched customer

**Files:** `app/eqms/modules/rep_traceability/admin.py`,
`app/eqms/templates/admin/sales_orders/detail.html`

1. New route `POST /admin/sales-orders/<int:order_id>/customer`, endpoint
   `rep_traceability.sales_order_set_customer`, permission `sales_orders.edit`.
2. Accepts either an existing `customer_id`, or `new_customer_name` to create one. When creating,
   use the existing `find_or_create_customer` service so keying stays consistent with the rest of
   the system — do not write a `Customer` row by hand.
3. On change:
   - set `order.customer_id`
   - for **every** distribution linked to this order, call
     `sync_distribution_customer_from_sales_order(distribution, order)` so `customer_id` and
     `facility_name` follow the order
   - record `sales_order.customer_reassigned` with metadata carrying
     `before_customer_id`, `before_customer_name`, `after_customer_id`, `after_customer_name`,
     and `distributions_resynced` (a count)
   - no reason-for-change prompt; this is a routine correction
4. In the Order Details card, replace the static Customer value with a form: a `<select>` of
   existing customers (reuse the helper at `admin.py` line ~245, which already orders by facility
   name and caps at 500), plus a text input to create a new customer, plus a Save button. Keep the
   link to the customer profile next to it.
5. Redirect back to the detail page with a flash naming both the old and new customer.

---

## Task B — Link and unlink distributions from the order

**Files:** `app/eqms/modules/rep_traceability/admin.py`,
`app/eqms/templates/admin/sales_orders/detail.html`

The "Linked Distributions" card (detail template lines 165-218) currently only lists rows with an
Edit link. Make it the place where matching gets fixed.

1. New route `POST /admin/sales-orders/<int:order_id>/distributions/link`, endpoint
   `rep_traceability.sales_order_link_distribution`, permission `distribution_log.edit`.
   - Accepts a `distribution_id`.
   - **It must link regardless of whether the order numbers agree** — that is the entire point;
     see the `SO 0000164` / `0000165` case above. Do not validate the numbers against each other.
   - Calls `sync_distribution_customer_from_sales_order`, then `safe_apply_order_type` for the
     order so the type recomputes (a newly linked ShipStation row should flip the order from
     `cleartract_in_process` to `cleartract_distribution`, and a manual one to
     `cleartract_delivery`, unless the type was manually locked).
   - If the distribution is already linked to a **different** order, re-point it, and call
     `safe_apply_order_type` for the previous order too so it stops claiming a distribution it no
     longer has.
   - Records `distribution.link_sales_order` with metadata including `sales_order_id`,
     `order_number`, the distribution's own `order_number`, whether the numbers differed, and any
     `previous_sales_order_id`. Reuse that existing action name — see
     `app/eqms/admin.py` line 1239 for the established shape.
2. New route `POST /admin/sales-orders/<int:order_id>/distributions/<int:entry_id>/unlink`,
   endpoint `rep_traceability.sales_order_unlink_distribution`, permission
   `distribution_log.edit`. Clears `sales_order_id`, records `distribution.clear_sales_order` with
   the previous order id in metadata (the existing route at `app/eqms/admin.py` line 1268 records
   empty metadata — do better here), then `safe_apply_order_type` for the order.
3. UI in the Linked Distributions card:
   - An `Unlink` button on each linked row, next to the existing Edit link.
   - Below the table, a **Link a distribution** control: a `<select>` of distributions with
     `sales_order_id IS NULL`, ordered by ship date descending, each option labelled with ship
     date, order number, facility, SKU and tracking number so the operator can recognise the row.
     There are about 35 of these in production, so a plain select is fine; do not build search.
   - When the order has no linked distributions, say so plainly and show the same control. **Do
     not** add any warning, colour, icon or wording implying the order is late or overdue — see
     the decisions table.
4. Both new routes redirect back to the detail page with a flash.

---

## Task C — Cancelled orders

**Files:** `app/eqms/modules/rep_traceability/admin.py`, detail and list templates

1. `SalesOrder.status` is `Text` and the table already carries
   `CheckConstraint("status IN ('pending','shipped','cancelled','completed')")` at
   `models.py` lines 21-23. **`cancelled` is therefore already a legal value and no migration is
   required.** Do not add one.
2. New route `POST /admin/sales-orders/<int:order_id>/status`, endpoint
   `rep_traceability.sales_order_set_status`, permission `sales_orders.edit`. Accepts one of the
   four constraint values, rejects anything else with a flash rather than a 500, and records
   `sales_order.status_changed` with before and after in metadata.
3. Expose it as a dropdown in the Order Details card, replacing the static Status badge. Keep the
   existing badge styling for the current value.
4. Cancelled orders stop being presented as awaiting shipment:
   - On the sales-orders list, exclude `status == 'cancelled'` when the Type filter is
     `cleartract_in_process`, unless a new `include_cancelled` checkbox is ticked.
   - Show a plain `Cancelled` marker on cancelled rows in the list.
   - The NRE Projects dashboard excludes cancelled orders from its customers, orders and metrics.
5. Do **not** change `classify_order_type`. Cancellation is a lifecycle fact, not a fifth order
   type; the operator fixed the type vocabulary at four values.

---

## Task D — Order type dropdown on the detail page

**File:** `app/eqms/templates/admin/sales_orders/detail.html`

Replace the read-only Type value (lines 54-65) with the same inline dropdown pattern the list uses,
posting to the existing `rep_traceability.sales_order_set_type`. Keep the `Needs review` and
`(manual)` markers. Pass a `next` value so the operator returns to the detail page rather than the
list — check how `sales_order_set_type` builds its redirect (`admin.py` lines 2284-2287); it
currently only ever returns to the list, so extend it to honour a detail-page return without
breaking the list's existing behaviour.

---

## Task E — Read-only ShipStation probe for the unmatched catheter orders

**File:** new `scripts/_probe_shipstation_for_in_process.py`

The question this answers: for the catheter orders with no distribution record, does a shipment
exist upstream in ShipStation that our sync never turned into a distribution row? The answer
decides whether the later reconciliation is a linking job or a sync-repair job, so it must be
evidence, not inference.

1. Select every sales order with `order_type == 'cleartract_in_process'`. Report the count and
   process them all.
2. For each, query the ShipStation API **read-only** for that order number. Reuse the existing
   client and credential handling in `app/eqms/modules/shipstation_sync/` — do not write a new HTTP
   layer and do not hardcode credentials. Look up orders by order number, and shipments for any
   order found.
3. For each sales order print one line: order number, order date, customer, whether a ShipStation
   order exists, its ShipStation status if so, how many shipments it has, and the tracking numbers.
4. Summarise at the end:
   - how many have a ShipStation order with at least one shipment (**these are the sync gaps — the
     distribution record should exist and does not**)
   - how many have a ShipStation order with no shipment (consistent with genuinely not yet shipped)
   - how many have no ShipStation order at all (consistent with a manual delivery the operator has
     yet to upload, or an order placed well ahead of fulfilment)
5. Absolute constraints: no writes to the database, no `run_sync` call, no distribution creation,
   no `--execute` flag. If credentials are missing or the API errors, say so plainly per order and
   keep going rather than aborting the run.
6. **ASCII-only output.** Non-ASCII has crashed scripts mid-run under PowerShell with
   `UnicodeEncodeError`.
7. Run it against production and paste the full output into your completion report.

Note for interpretation, not for code: the operator has said some of these will be accounted for by
manual deliveries he has not uploaded yet. Do not act on any finding — report it.

---

## Task F — Tests

**File:** new `tests/test_p4_03_order_control_surface.py`

Follow the established fixture pattern (there is no shared `conftest.py`): per-test SQLite file DB
via `monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")`, `create_app()`,
`Base.metadata.create_all`, `application.config["_schema_health_ok"] = True`, permissions / roles /
users seeded inline. `tests/test_p4_01_order_type.py` and `tests/test_p4_02_import_relocation.py`
are the closest models.

Cover at minimum:

1. Reassigning the customer moves the order **and** re-syncs `customer_id` and `facility_name` on
   every linked distribution.
2. Reassigning to a newly created customer works via `find_or_create_customer`.
3. Linking a distribution whose order number **differs** from the order's succeeds — assert on the
   `SO 0000164` / `0000165` shape specifically, since that is the real case driving this.
4. Linking a ShipStation distribution to an order typed `cleartract_in_process` flips it to
   `cleartract_distribution`; linking a manual one yields `cleartract_delivery`.
5. Linking a distribution already attached to another order re-points it and recomputes the type of
   **both** orders.
6. A manually locked `order_type` (`order_type_is_manual`) survives a link and an unlink.
7. Unlinking clears `sales_order_id`, recomputes the type, and records the previous order id in the
   audit metadata.
8. Setting status to `cancelled` succeeds; an invalid status is rejected with a flash and no change.
9. A cancelled `cleartract_in_process` order is absent from the list's in-process filter by default
   and present when `include_cancelled` is ticked.
10. A cancelled NRE order is excluded from the NRE Projects dashboard.
11. Every new route rejects a user without the required permission.
12. CSRF is enforced on every new POST.
13. Update any existing test that asserts the detail page's static Customer, Status or Type markup.
    Preserve each test's intent; do not delete coverage.

---

## Task G — Deploy and completion report

1. Run the full gate and report actual output:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m alembic heads
python -c "import app.wsgi"
```

`alembic heads` must print exactly one head, still `f8a9b0c1d2e3`. Baseline is 394 passed, 1
skipped. Note that `python -c "import app.wsgi"` reports a Spaces `HeadBucket 403` locally because
the local object-storage credentials are stale; that is pre-existing and unrelated. Any
storage-dependent result must not be trusted from a local run.

2. Commit and push to `main`. Confirm the build, the pre-deploy `release.py` step and the health
   check succeeded. The operator cannot see the build banner, so state deploy status explicitly.

3. Run the Task E probe against production and paste the full output.

4. Your completion report must contain:
   - every new route with its endpoint name and permission
   - every audit action name you emit, and the metadata keys on each
   - what changed on the detail page, the list, and the NRE dashboard
   - the full ShipStation probe output plus your reading of the three summary buckets
   - confirmation that you did **not** touch customer identity rules or `_is_catheter_order`
   - confirmation that you added **no** lateness, aging or overdue logic anywhere
   - every judgment call, and anything you chose not to do
   - final test totals and deploy status

---

## Out of scope

- **Customer merging, re-keying, corporate-suffix normalisation, and `_is_catheter_order`.** All
  P4-03B. For your awareness only, so you do not "helpfully" pre-empt it: production has two
  customer rows for Advanced Bionics (`id=530` named `AB` with 3 NRE orders, and `id=764`
  `Advanced Bionics Gmbh` with 1), and fifteen further NRE-order customers carry address-derived
  keys instead of company-name keys. Leave every one of them alone.
- The NRE Invoice Tracker: pairing entries or files to sales orders. (P4-04)
- All of Purchasing: invoice upload, Invoices Received, PO matching, Other Payments, the PO Log
  reversal, PO open/closed, the PO Log export. (P4-05, P4-06)
- Acting on any reconciliation finding: creating distributions, running a sync to backfill,
  merging or deleting customers. (P4-08)
- Changing parsing, dedupe rules, or `classify_order_type`.
- Changing `_diagnostics_allowed`, any permission decorator, or `scripts/init_db.py`.
- The Admin Tools Imports card and the packing-slip page delivered in P4-02.
- The auditor portal and the `Auditor Files/` ignore rules.

---

## Reference

**Existing code to reuse rather than reinvent**

| Thing | Where |
| --- | --- |
| `sync_distribution_customer_from_sales_order` | `modules/rep_traceability/service.py` line 106 |
| `safe_apply_order_type` | `modules/rep_traceability/order_type.py` line 122 |
| `find_sales_order_by_normalized_number` | `modules/rep_traceability/service.py` line 56 |
| `find_or_create_customer` | `modules/customer_profiles` service |
| Customer choice list helper | `modules/rep_traceability/admin.py` line ~245 |
| Established link / clear routes to mirror | `app/eqms/admin.py` lines 1208-1279 |
| Inline dropdown UI pattern | `templates/admin/nre_projects/index.html`, and the Type dropdown in `templates/admin/sales_orders/list.html` |
| Detail page being modified | `templates/admin/sales_orders/detail.html` — Order Details card lines 17-89, Linked Distributions card lines 165-218 |
| `sales_order_set_type` and its redirect handling | `modules/rep_traceability/admin.py` lines 2265-2297 |
| `sales_order_detail` route and its template context | `modules/rep_traceability/admin.py` lines 2300-2334 |

**Conventions**
- `url_for(...)` for every URL, including inside inline JavaScript. Hardcoded `/admin/...` strings
  have broken repeatedly when blueprints moved.
- CSRF token on every state-changing form: `<input type="hidden" name="csrf_token"
  value="{{ csrf_token }}">`.
- `record_event` for every state change on a regulated record, with a metadata snapshot. P4-01 had
  to close a gap where tracker deletions recorded no metadata and the data became unrecoverable;
  do not recreate that gap.
- UI language: short, plain, list-like. No internal document numbers in labels. No self-describing
  subtitles.
- Windows/PowerShell: no `&&` chaining, no bash heredocs, no non-ASCII in script output.
- Postgres is the deploy target. The local SQLite migration chain is broken at a Phase 3 ancestor,
  so never try to prove anything by rebuilding SQLite from scratch; tests build schema with
  `Base.metadata.create_all`.

---

## Acceptance checklist

- [ ] No migration added; `alembic heads` still prints exactly `f8a9b0c1d2e3`
- [ ] Customer reassignment works for an existing customer and for a newly created one
- [ ] Reassignment re-syncs every linked distribution and audits the count
- [ ] A distribution can be linked to an order whose number differs, with no validation blocking it
- [ ] Linking and unlinking recompute `order_type` for every affected order, including the previous one
- [ ] A manual `order_type` override survives linking and unlinking
- [ ] Unlink records the previous sales order id in audit metadata
- [ ] Status dropdown sets `cancelled`; invalid values are refused without a 500
- [ ] Cancelled orders drop out of the in-process view and the NRE dashboard, with an include toggle on the list
- [ ] `classify_order_type` unchanged; still exactly four order types
- [ ] Type dropdown live on the detail page and returns there after saving
- [ ] **No aging, overdue, late or "should have shipped" logic anywhere in the change set**
- [ ] Customer identity rules and `_is_catheter_order` untouched
- [ ] ShipStation probe is read-only, ASCII-only, and its production output is in the report
- [ ] All thirteen test areas covered, including permission and CSRF enforcement
- [ ] Full gate run and reported; pushed to `main`; deploy confirmed green explicitly
