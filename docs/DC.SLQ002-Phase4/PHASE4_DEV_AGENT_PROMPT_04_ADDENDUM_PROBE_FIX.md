# Addendum to P4-04 — The ShipStation probe page hangs; rewrite it to bulk fetch

## Do this inside the P4-04 change set

Complete this in the **same commit series as P4-04**, not as a separate concurrent effort. It touches
only `shipstation_sync`, so it will not collide with the tracker work, but two agents pushing to
`main` at once would. If you have already pushed P4-04, do this as an immediate follow-up commit.

## The defect

The operator tried to open `/admin/shipstation/probe-in-process` and his browser hung indefinitely.
The page cannot work as written.

`shipstation_probe_in_process` (`modules/shipstation_sync/admin.py` lines 145-247) loops over all 26
`cleartract_in_process` sales orders and, for each one, calls `list_orders_by_order_number` once per
candidate order-number spelling, then pages `list_shipments_for_order`. That is up to roughly a
hundred sequential HTTP requests inside a single web request. Worse, `request_json`
(`shipstation_client.py` lines 31-63) retries three times with `time.sleep` backoff of up to 10
seconds on a 429 and up to 5 seconds on any other error, against a 60-second socket timeout.
ShipStation rate-limits aggressively, so a single order can consume a minute or more and the whole
page can take many minutes. The browser and the platform give up long before it returns.

This is a design error, not a tuning problem. **Do not fix it by raising a timeout.**

## The fix: fetch in bulk, match in memory

The module already has the right primitives, and `run_sync` already uses them:

- `ShipStationClient.list_orders(create_date_start, create_date_end, page, page_size)` —
  `shipstation_client.py` line 65
- `ShipStationClient.list_shipments_by_date(ship_date_start, ship_date_end, page, page_size)` —
  line 103, whose docstring already says it is "much more efficient than per-order fetching"

Rewrite the probe to:

1. Compute the date window from the data: earliest `order_date` among the in-process orders (the
   oldest is 2025-01-08) through today. Do **not** use `_get_sync_config()`'s `since_date`, which
   defaults to the start of the current calendar year and would silently exclude every 2025 order —
   that blind spot is half the reason we are running this probe.
2. Page through `list_orders` once across that window and build an index keyed by
   `normalize_order_number(order["orderNumber"])`. Reuse `normalize_order_number` from
   `modules/rep_traceability/service.py`; do not reimplement it.
3. Page through `list_shipments_by_date` once across the same window and index shipments by their
   ShipStation `orderId`, and also by normalized order number where the shipment carries one.
4. Then resolve all 26 orders from those in-memory indexes with **zero further API calls**.
5. Cap the work and degrade honestly:
   - a hard wall-clock budget of about 25 seconds; when it is exhausted, render what you have and
     state plainly at the top that the result is partial and which orders were not resolved
   - a page cap on both loops, reported when hit
   - pass a lower `retries` value for this probe so one stuck call fails fast instead of stalling the
     page
6. Keep every existing constraint: **read-only, no DB writes, no `run_sync`, no distribution
   creation, no sync-run row.** Credentials stay on App Platform and are never requested from the
   operator.

## Also report what the sync's own history already tells us

While you are in this module, surface two facts on the probe page. I established both read-only from
the production database, so they need no API access and must be shown even when the API is
unreachable:

1. **`ShipStationSkippedOrder` is a cumulative set of ShipStation orders seen with no shipment.** Of
   198 rows, 197 carry `reason="no_shipments"` and one is `duplicate_external_key`. Three of our 26
   in-process orders are in it: `0000179` (ShipStation `order_id` 584051980), `0000184` (588776999)
   and `0000186` (591748749), all recorded 2026-04-20. For those three the upstream order exists and
   genuinely has no shipment.
   State the per-order skipped status on each row so the operator can see this without the API.
2. **The routine sync only looks at the current calendar year.** `_get_sync_config` (lines 67-83)
   defaults `since_date` to `{current_year}-01-01`, so ordinary runs never examine 2025 orders. Show
   the effective window on the page, because "no ShipStation order found" means something entirely
   different inside the window than outside it.

Do **not** change the sync's default window in this change set. It is a real issue, it is recorded
for P4-08, and altering ingestion behaviour belongs in the reconciliation work where its effects can
be reviewed deliberately.

## Tests

Add to `tests/test_p4_04_nre_tracker_match.py` or a sibling file, with the ShipStation client stubbed
— never hit the network in a test:

1. The probe issues a **bounded** number of API calls that does not scale with the number of
   in-process orders: with a stubbed client counting calls, assert the count stays constant when the
   number of in-process orders goes from 3 to 30.
2. Orders are resolved from the bulk index, including a normalized-number match such as
   `SO 0000290` upstream against `0000290` locally.
3. The three-bucket summary counts correctly across all three outcomes.
4. Exhausting the time budget renders a partial result flagged as incomplete rather than raising.
5. The probe performs no writes: no `ShipStationSyncRun` row, no `ShipStationSkippedOrder` row, no
   distribution created.
6. With credentials absent, the page still renders and still shows the skipped-table and
   effective-window information.

## Report

State the number of API calls the page now makes, the date window it used, and the three-bucket
summary if you can reach production. If you cannot authenticate, say so — the operator will open the
page once, and it now needs to return in seconds rather than minutes.
