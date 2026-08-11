# P4-04B — Distributor billing orders (Health Products For You)

You are the Phase 4 dev agent on Silq eQMS. Read `docs/SYSTEM_OVERVIEW.md` and
`docs/DC.SLQ002-Phase4/PHASE4_PLAN.md` before starting. P4-04 is complete and deployed at
`g9a0b1c2d3e4`; this change set chains from there.

## The business rule you are encoding

Health Products For You (HPFY) is a **distributor**, not a treating facility. The commercial process
has two steps and produces two sales orders:

1. Silq ships units to HPFY under a **$0 sales order**. This is the real distribution and it matches
   a ShipStation shipment normally.
2. Later, Silq raises **non-$0 sales orders** against HPFY for billing. These are accounting
   documents. **No shipment exists for them and none ever will.**

Today the second kind lands in `cleartract_in_process`, so the operator's "awaiting shipment" queue is
19/26 noise. Those orders must stay filed under the HPFY customer profile — they are real orders and
real revenue — but they must stop being presented as unshipped.

## The data, verified read-only against production on 2026-08-11

HPFY is customer **id 620**. Its 31 sales orders split with **zero exceptions**:

| `order_amount` | Count | Current `order_type` | Linked distributions |
| --- | --- | --- | --- |
| $0 | 12 | `cleartract_distribution` | all 12 linked |
| above $0 | 19 | `cleartract_in_process` | none linked |

The 19 billing orders are `0000146, 0000158, 0000169, 0000177, 0000183, 0000199, 0000217, 0000221,
0000237, 0000252, 0000277, 0000282, 0000292, 0000319, 0000325, 0000337, 0000347, 0000363, 0000377`.

Two facts that shape the design:

- **The amount rule is only safe for a distributor.** Of the 7 non-HPFY in-process orders, 6 have
  `order_amount = 0` and are genuine pending or manual-delivery shipments. A system-wide "non-zero
  means billing" rule would be badly wrong. Scope strictly to flagged customers.
- **The billing orders do carry catheter SKU lines**, which is why they classify as in-process today.
  So "has no line items" is *not* available as a discriminator. The amount is.

## Frozen decisions (confirmed by Ethan; do not re-ask)

- **D27 — Represent it as a fifth order type**, `distributor_billing`, labelled
  **"Distributor Billing"**, driven by a **customer-level `Distributor` flag**. Not a hardcoded
  customer name: a renamed or merged record must not silently change classification behaviour. When
  the next distributor appears, Ethan ticks a box.
- **D28 — Classification is automatic.** For a customer flagged as a distributor, an order with no
  linked distribution and `order_amount > 0` is a billing order. $0 orders keep their existing
  behaviour because those are the real shipments. Manual per-order override still wins.
- **D29 — HPFY is one customer.** Merge id **741** (`487FEDERALRD|CT|06804`, 0 sales orders, 1
  distribution) into id **620** (`14DRFAIRFIELD|CT|06804`, 31 sales orders, 18 distributions) using
  the existing merge tool, with the comparison screen reviewed before executing.
- **D18 still applies — no lateness logic.** No overdue, aging, stale or late anything.

## Tasks

### Task A — `Customer.is_distributor`

Additive migration chaining from `g9a0b1c2d3e4`. Suggested revision id `h0b1c2d3e4f5`.

- `customers.is_distributor`: `Boolean`, `nullable=False`, `server_default=false()`, so existing rows
  are safe and the column is backfill-free.
- Add the field to the `Customer` model.
- Expose it as a checkbox on the customer edit form
  (`templates/admin/customers/detail.html`, edit tab around lines 424-516; POST handler
  `customer_update_post` in `customer_profiles/admin.py:420-476`, permission `customers.edit`).
  There are no booleans on that form yet — parse it as `request.form.get("is_distributor") == "1"`
  and thread it through the `payload` dict into `update_customer()` in `customer_profiles/service.py`
  alongside the existing fields. **A checkbox that is absent from the POST means false**, so make
  sure an unticked box actually clears the flag rather than being read as "unchanged".
- That form requires a `reason`; leave that requirement alone.
- Label it in the UI so its effect is obvious, for example
  *"Distributor — non-$0 sales orders are billing documents and expect no shipment"*.
- Show the flag on the customer detail overview so it is visible without opening the edit tab.

### Task B — The fifth order type

In `rep_traceability/order_type.py`, which is the documented single source of truth:

- `ORDER_TYPE_DISTRIBUTOR_BILLING = "distributor_billing"`
- Add it to `ORDER_TYPE_LABELS` as `"Distributor Billing"` and to `ORDER_TYPE_CHOICES`.
  `VALID_ORDER_TYPES` derives from the labels dict, so manual selection starts working for free.
- `order_type` is `String(32)` with **no** database check constraint, so **no migration is needed for
  the type itself** — the only migration in this change set is Task A's column.

Because `ORDER_TYPE_CHOICES` drives both the list and detail dropdowns, the new option appears in the
UI automatically. Verify that rather than assuming it.

### Task C — The classification rule

Extend `classify_order_type` (`order_type.py:34-57`). The existing rule order must be preserved, with
the new rule inserted **after both distribution checks and before the catheter-SKU check**:

1. any linked distribution with `source == "shipstation"` -> `cleartract_distribution`
2. any other linked distribution -> `cleartract_delivery`
3. **customer is flagged `is_distributor`, no linked distribution, and `order_amount > 0`
   -> `distributor_billing`, `needs_review=False`**
4. no distribution but at least one catheter-SKU line -> `cleartract_in_process`
5. otherwise -> `nre_project`, `needs_review=True`

Placement matters: a linked distribution still wins, so if a shipment ever does arrive against a
billing order the truth of the shipment takes precedence and the operator sees it.

Required behaviours:

- `order_amount` that is **NULL** must **not** classify as billing. It falls through to the existing
  rules, which leaves the order visible in the in-process queue for manual handling. That is the
  correct failure mode — a parse failure must never silently hide an order.
- `order_amount == 0` for a distributor behaves exactly as today.
- `order_type_is_manual` still short-circuits everything in `apply_order_type`.
- Update the `classify_order_type` docstring, since it enumerates the rule order.
- Handle a missing customer (`customer_id` NULL) without raising.

### Task D — Flag HPFY and reclassify

- Set `is_distributor = True` on customer **620**, and on **741** as well if you do this before the
  merge, so the flag cannot be lost either way.
- Reclassify HPFY's existing orders using the existing `scripts/backfill_order_types.py` (it already
  calls `classify_order_type` and already has dry-run / execute semantics — extend it if needed
  rather than writing a new script). Skip any order with `order_type_is_manual = True`.
- **Dry run first and report the numbers before executing.** Expected: 19 orders move
  `cleartract_in_process -> distributor_billing`; the 12 $0 orders are untouched; nothing else in the
  database changes; the in-process count falls **26 -> 7**.
- Record an audit event per changed order through the existing `apply_order_type` audit path.

### Task E — Merge the duplicate HPFY record

Using the existing tool at `GET /admin/customers/merge?c1=&c2=` and `merge_post`
(`customer_profiles/admin.py:691-774`, service `merge_customers(s, *, master_id, duplicate_id, user)`):

- `master_id = 620`, `duplicate_id = 741`. Master keeps its `company_key`.
- Confirm afterwards that 741's single distribution now points at 620, that any notes or rep
  assignments on 741 survived, and that total distribution and sales-order counts across the database
  are unchanged (**218 sales orders, 223 distributions** as of P4-03B, plus anything imported since —
  report the before and after numbers).

**Known limitation, do not fix here.** Catheter identity is address-keyed, so a future HPFY shipment
to 487 Federal Rd would create a fresh duplicate. The durable fix is to give distributor customers
company-level identity, which is recorded for P4-08 where identity rule changes land on their own per
D21. Note the limitation in the merge audit metadata so the next reader understands why the duplicate
existed.

## Do not do these

- **Do not touch the sales dashboard maths.** I checked it: `compute_sales_dashboard`
  (`rep_traceability/service.py:958-1170`) counts **units only**, from `DistributionLine.quantity`
  with a `DistributionLogEntry.quantity` fallback, filtered by `ship_date`, and it never joins
  `SalesOrder` or filters on `order_type` or `status`. There is **no ClearTract revenue total
  anywhere in the application** — the only revenue figure is the NRE dashboard's, which is scoped to
  `nre_project` orders and so cannot see HPFY. HPFY therefore already counts correctly: units come
  from the 12 $0 shipment orders' distributions, and the 19 billing orders contribute no units and no
  double count. Adding a fifth order type cannot change any of this. If you believe you have found a
  double count, stop and report it instead of changing the calculation.
- **Do not change customer identity keying or `compute_facility_key_from_ship_to`.** Task E is a data
  merge with existing reviewed tooling, not a rule change.
- **Do not change the ShipStation sync's default `since_date`.** Still P4-08.
- **Do not add the new type to any NRE surface.** The NRE module filters `== nre_project` throughout
  and must keep doing so.
- No lateness, aging or overdue logic of any kind (D18).

## Places that reference the order-type constants

Review each and state in your report what you did or why nothing was needed:

- `rep_traceability/admin.py:2156-2250` — list filter and dropdown population
- `rep_traceability/admin.py:2179-2180` — the cancelled-order exclusion that is currently special-cased
  to `cleartract_in_process`. Decide deliberately whether `distributor_billing` needs the same
  treatment and say which way you went.
- `rep_traceability/admin.py:2266-2296` — `sales_order_set_type`, flash text via `ORDER_TYPE_LABELS`
- `templates/admin/sales_orders/list.html:26-29,128-133,141` and `detail.html:106-123,200`
- `shipstation_sync/admin.py:148-169` and `templates/admin/shipstation/probe_in_process.html` — the
  probe filters in-process only, so the 19 should drop off with no code change. Confirm they do.
- `customer_profiles/service.py:881-886` — `is_nre_rekey_candidate`; confirm unaffected
- `scripts/_report_order_reconciliation.py` — add the new type to its counts so the report stays
  complete

## Tests

New file `tests/test_p4_04b_distributor_billing.py`:

1. Distributor customer, no linked distribution, amount $145 -> `distributor_billing`,
   `needs_review` False.
2. Distributor customer, amount $0 -> unchanged behaviour (`cleartract_in_process` given catheter
   lines).
3. Distributor customer, amount **NULL** -> **not** billing; stays in the in-process queue.
4. **Non**-distributor customer, amount $2654.40, no distribution -> `cleartract_in_process`. This is
   the VAMC Loma Linda case and it guards the blast radius of the whole feature.
5. Distributor customer, amount $500, **with** a linked ShipStation distribution ->
   `cleartract_distribution`. Rule precedence.
6. Billing order with catheter SKU lines still classifies as billing — proves the amount rule beats
   the line-item rule for distributors.
7. `order_type_is_manual = True` is never overwritten by the new rule.
8. Clearing the checkbox sets `is_distributor` false and reclassification returns the order to
   `cleartract_in_process`.
9. The new type appears in the list-page dropdown and filters correctly, and
   `?order_type=distributor_billing` returns only those orders.
10. Manual selection of `distributor_billing` via `POST /admin/sales-orders/<id>/order-type` succeeds.
11. `distributor_billing` orders are absent from the ShipStation probe page's order set.
12. `distributor_billing` orders are absent from every NRE surface.
13. Units regression: a distribution-derived unit total is unchanged when an order is reclassified to
    `distributor_billing`, proving the dashboard is untouched.

Keep the existing suite green (**440 passed, 1 skipped** at P4-04).

## Gate before pushing

1. Full suite green, and report the new count.
2. `alembic heads` prints a **single** head.
3. `python -c "import app.wsgi"` succeeds. A local Spaces `HeadBucket 403` is a known stale-credential
   condition and is not a failure.
4. Push to `main`, confirm the production migration applied, and confirm `/health` returns
   `{"ok":true}`.

## Report back

- Migration revision id and confirmed production head.
- Task D dry-run numbers, then the executed numbers: in-process before and after (expect 26 -> 7),
  and the 19 order numbers that moved.
- Task E before and after counts for customers, sales orders and distributions.
- The decision you made on the cancelled-order exclusion at `admin.py:2179`.
- Anything you found that contradicts the data above — particularly any HPFY order that breaks the
  clean $0 / non-$0 split, since the entire rule rests on it.
