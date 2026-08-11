# P4-07 — One way to count units, and an honest ShipStation counter

You are the Phase 4 dev agent on Silq eQMS. Read `docs/SYSTEM_OVERVIEW.md` and
`docs/DC.SLQ002-Phase4/PHASE4_PLAN.md` first. P4-06B is deployed at `j2d3e4f5a6b7` (no migration since
then); this change set chains from there. **A small migration is not expected — see Task C.**

The theme: the same question — "how many units went to this customer?" — currently gets different
answers on different pages, and a counter on the ShipStation page reads like an error report when it
is nothing of the kind.

## Production facts, verified read-only on 2026-08-11

- **223 distribution entries, 5,728 units.** Every entry has `DistributionLine` rows; 112 have more
  than one.
- **`entry.quantity` equals `sum(line.quantity)` on all 223 entries.** Totals agree exactly, 5,728
  either way. So the line-aware-versus-entry-quantity inconsistency between pages is **latent, not
  live** — do not describe it as a bug or claim to have fixed wrong numbers. It is worth unifying so it
  cannot drift, nothing more.
- **The live divergence is matched-only versus all-rows.** Customer pages filter
  `sales_order_id IS NOT NULL`; the sales dashboard counts every row. **35 unmatched distributions
  carry 850 units**, invisible on **17 customer profiles** but present in the dashboard total.
  Worked example: customer 628, VAMC - Loma Linda, has 9 distributions of which 6 are matched — the
  profile shows **200** units while the dashboard counts **320**.
- **Three distributions have `customer_id` NULL:** ids **1037, 1038, 1039**, order numbers
  `SO 0000379`, `SO 0000380`, `SO 0000381`, all carrying the name `HARBOR-UCLA MEDICAL CENTER`. None
  dangle — they are genuinely unassigned. They are the only rows that can reach the name-based fallback
  in the dashboard's customer keying.
- **The ShipStation skipped counter is not an error signal.** Of 198 `shipstation_skipped_orders` rows,
  **197 are `no_shipments`** and one is `duplicate_external_key`. Recent runs report `skipped` around
  190 against `orders_seen` around 191, so the number is essentially "upstream orders that have not
  shipped yet" — the normal state of an order-entry system.

## Frozen decisions (confirmed by Ethan; do not re-ask)

- **D40 — Customer profiles count all distributions, matched or not.** A shipment that physically
  happened counts toward that customer whether or not its sales order PDF has been imported. Show the
  total, and alongside it show how much of that total is still unmatched so Ethan can see what needs a
  PDF.
- **D41 — Attach the three orphaned Harbor-UCLA distributions to the existing Harbor UCLA customer
  record** in this change set, with a preview of exactly what will change before anything is written.
  That retires the name-based fallback.
- **D18 still applies:** no lateness, aging, overdue or stale logic. "Unmatched" is a state, never a
  measure of elapsed time.

## Task A — One unit-counting helper, used everywhere

Today four call sites compute units four slightly different ways:

| Site | File | Logic |
| --- | --- | --- |
| Sales dashboard | `rep_traceability/service.py:999-1031` | all rows, line-aware with entry fallback |
| Customer list | `customer_profiles/admin.py:84-98` | matched only, `entry.quantity` only |
| Customer detail | `customer_profiles/admin.py:351-358` | matched only, line-aware |
| Distribution modal | `rep_traceability/admin.py:1042-1049` | matched only, line-aware |

Write **one** helper — put it in `rep_traceability/service.py` next to the dashboard computation, since
that is where the distribution domain lives — that takes a set of distribution entries and returns
units, preferring `DistributionLine.quantity` when line rows exist and falling back to
`DistributionLogEntry.quantity` when they do not. Have all four sites call it. Do not leave a second
implementation behind.

The fallback matters even though every current row has lines: a manually created distribution or a
future import could arrive without them, and that is exactly when the two implementations would start
disagreeing silently.

## Task B — Customer unit totals include unmatched distributions (D40)

- Customer list and customer detail count **all** of that customer's distributions.
- On both, show the unmatched portion as a plain factual note next to the total — for example
  `320 units (120 on 3 distributions not yet matched to a sales order)`. Wording is yours, but it must
  read as a fact, not a warning, and must contain no notion of lateness (D18).
- Where the unmatched count is non-zero, link through to the existing unmatched-distributions view so
  the operator can act.
- Expected effect on production: 17 customers' totals rise, by 850 units in aggregate. VAMC - Loma
  Linda goes 200 -> 320. **Report the before and after per affected customer.**
- The dashboard total must not change. It already counts all rows, so if your refactor moves it by even
  one unit, something is wrong — assert this in a test.

## Task C — Attach the three orphaned distributions (D41)

- Find the existing Harbor UCLA customer record by its keyed identity rather than by string-matching
  the name — the whole point of the identity work in P4-03B was that names are unreliable. Confirm you
  have exactly one candidate before proceeding.
- **Preview first.** Print or render exactly which distribution ids move, to which customer id, and what
  the customer's unit total becomes, and stop. Writing happens only on an explicit second step. Ethan
  approves numbers before data changes; that has been the rule all phase.
- Set `customer_id` on distributions 1037, 1038, 1039 and record an audit event per row with a full
  before/after snapshot.
- Do **not** invent a sales-order link. These rows stay unmatched until the PDFs are imported; only the
  customer is being assigned.
- Once they are assigned, **remove the name-based fallback** in the dashboard's `_customer_key`
  (`rep_traceability/service.py:976-980`) or, if you would rather keep a guard, make it raise or log
  loudly rather than silently keying on a canonicalized name. A silent name fallback next to
  address-based identity is how the first-time customer count drifts. Say which you chose and why.
- No migration is expected for any of this. If you think one is needed, stop and explain first.

## Task D — Make the ShipStation counter honest

- Rename the displayed counter so it says what it means. `skipped` currently reads as "we dropped
  something"; it means "upstream orders with no shipment to import". Change the label and the
  `message` string built in `shipstation_sync/service.py`, not the database column — a column rename is
  a migration for no benefit.
- On the ShipStation page, show the **reason breakdown** from `shipstation_skipped_orders` — today that
  is 197 `no_shipments` and 1 `duplicate_external_key` — so the number is self-explaining rather than
  needing someone to remember what it counts.
- Add one line of explanatory text stating that orders with no shipment are normal and are not errors.
- Do not change sync behaviour, the `since_date` window (still P4-08), or what gets recorded.

## Do not do these

- Do not claim the line-versus-entry unification fixed incorrect totals. It did not; the numbers already
  agree on all 223 rows. Accuracy about what you changed matters more than an impressive report.
- Do not alter the sales dashboard's unit total (Task B).
- Do not link the three orphaned distributions to sales orders (Task C).
- Do not change the ShipStation sync window or add a column rename migration (Task D).
- No lateness, aging or overdue logic anywhere (D18).

## Tests

New file `tests/test_p4_07_unit_truth.py`:

1. The shared helper prefers line quantities when lines exist and falls back to entry quantity when
   they do not.
2. All four call sites return the same number for the same set of entries — the regression guard that
   makes the unification meaningful.
3. A customer's total includes unmatched distributions, and the unmatched portion is reported
   separately with the correct count.
4. A customer with no unmatched distributions shows no unmatched note.
5. **The sales dashboard total is unchanged** by the refactor, for a fixture containing matched and
   unmatched entries and both single-line and multi-line entries.
6. An entry with multiple lines is counted once, by line sum, not double-counted by adding the entry
   quantity as well.
7. An entry with no lines still counts via its entry quantity.
8. Assigning a customer to a previously unassigned distribution records an audit event with a
   before/after snapshot and does not create or alter any sales-order link.
9. The ShipStation page shows the reason breakdown and the counter's new label.
10. No wording introduced in this change set implies lateness or overdue state.

Keep the existing suite green. **Baseline is 491 passed, 1 skipped**, which I verified locally after
your P4-06B push.

## Gate before pushing

1. Full suite green, **run after your final edit**, and report the count.
2. `alembic heads` prints a single head, expected to still be `j2d3e4f5a6b7`.
3. `python -c "import app.wsgi"` succeeds; a local Spaces `HeadBucket 403` is the known stale-credential
   condition, not a failure.
4. Push to `main` and confirm `/health` returns `{"ok":true}`.

## Report back

- The Task C preview numbers first, then the executed result.
- Per-customer before and after unit totals for the 17 affected customers, and confirmation that the
  aggregate rise is 850.
- Confirmation, with the test name, that the sales dashboard total did not move.
- Which option you took on the name-based fallback, and why.
- Anything you found where two pages still disagree about a number.
