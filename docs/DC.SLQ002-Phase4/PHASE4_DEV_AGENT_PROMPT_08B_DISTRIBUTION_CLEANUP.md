# P4-08B — Distribution cleanup (no new features)

You are the Phase 4 dev agent on Silq eQMS. Read `docs/SYSTEM_OVERVIEW.md` and
`docs/DC.SLQ002-Phase4/PHASE4_PLAN.md` first. Current head is whatever `alembic heads` prints;
chain any migration from that single head. **A migration is not expected.** If you think you need
one, stop and say so.

This is **data cleanup**. Do not add screens, fields, order types, or workflows. Use the import,
match, manual-distribution, and attachment paths that already exist. Every write is preview-first,
then `--execute`. Ethan approves numbers before data changes; that has been the rule all phase.

Local files live under `Distribution/` in the repo (OneDrive). Production Spaces credentials do not
exist on this machine — put bytes through the existing storage helper inside an app context, same as
every other import. If `GetObject`/`put_bytes` fails, stop and say so; do not pretend the file was
attached.

## Frozen decisions (do not re-ask)

- **D18** — no lateness, aging, overdue, or stale logic.
- **D62** — Sales order PDF is the source of truth for **unit quantities**. Device Distribution
  Record photos are the source of truth for **delivery date** and **lot numbers**.
- **D63** — Every 2025+ distribution should have exactly one sales order and exactly one shipment
  verification file (packing slip **or** trunk-stock photo, not both). 2024 unmatched rows are out
  of scope.
- **D64** — Do not invent a sales order for `0000145` or `0000164`. Leave them unmatched and list
  them. Their PDFs are missing or have no text layer.
- **D65** — Packing-slip display filename: `{Customer}_{YYYY-MM-DD}_SO{order}.pdf`
  example `HarborUCLA_2026-05-19_SO0000336.pdf`. Change the `OrderPdfAttachment.filename` (what the
  UI shows). Do not rename the storage object unless you must.
- **D66 — Duplicates, exactly as Ethan said (updated 2026-08-21):**
  - `0000203` — **keep both**. Confirmed by the sales-order quantity: two real Harbor shipments
    of 60 on 2025-07-25 (ids 789 and 1032).
  - `0000251` — **keep both** (two real 100-unit shipments; SO is 200).
  - `0000302`, `0000312`, `0000346`, `0000353` — delete the **later** row (higher id) in each pair:
    **1033, 1034, 1035, 1036**.
- **D69** — On the customer Sales Orders tab, **Total Units** is the sum of that order's linked
  distributions (same helper as P4-07), not `sum(sales_order_lines.quantity)`. Harbor 0000312 is
  the worked example: the tab shows **6** today because the PDF parser stored three lines of 2;
  the Distributions tab shows **30**. After deleting the duplicate 1034, that order's Total Units
  must read **30**. An order with no linked distributions (still in-process) may fall back to the
  sales-order line sum.
- **D67** — Linehan lots: `SLQ-05012025` × 4 and `SLQ-05022025` × 4.
- **D68** — Lyn Hopkins delivery date is **2026-02-26** (form + customer PO `02262026`). The
  filename `2.2.26` is wrong.

## Production facts, verified read-only 2026-08-21

| | Count |
| --- | --- |
| Sales orders | 218 (highest number **0000378**) |
| Distributions | 228 |
| Unmatched distributions | 40 (30 are 2024 — ignore those) |
| 2025+ unmatched | 10 |

2025+ unmatched ShipStation rows:

| Dist | Order | Ship | Qty | Customer |
| --- | --- | --- | --- | --- |
| 753 | 0000145 | 2025-02-21 | 30 | VAMC-San Diego (635) |
| 760 | 0000164 | 2025-03-19 | 80 | VAMC-Loma Linda (628) |
| 1037 | 0000379 | 2026-08-10 | 30 | Harbor UCLA (610) |
| 1038 | 0000380 | 2026-08-10 | 30 | Harbor UCLA (610) |
| 1039 | 0000381 | 2026-08-10 | 30 | Harbor UCLA (610) |
| 1040 | 0000382 | 2026-08-12 | 20 | Harbor UCLA, `customer_id` NULL |
| 1041 | 0000384 | 2026-08-12 | 5 | Cleveland Clinic, `customer_id` NULL |
| 1042 | 0000391 | 2026-08-18 | 60 | CoMedical Inc., `customer_id` NULL |
| 1043 | 0000392 | 2026-08-20 | 20 | Aspirus Wausau, `customer_id` NULL |
| 1044 | 0000393 | 2026-08-21 | 40 | Harbor UCLA, `customer_id` NULL |

`0000145` / `0000164` stay unmatched (D64). The other eight should match once
`Distribution/SalesOrders2025-Aug2126.pdf` is imported (it contains 0000153–0000394, including every
one of those numbers).

Duplicate pairs (same order + ship date + qty + facility):

| Order | Ids | Action |
| --- | --- | --- |
| 0000203 | 789, 1032 | **keep both** |
| 0000251 | 833, 834 | keep both |
| 0000302 | 871, 1033 | delete 1033 |
| 0000312 | 879, 1034 | delete **1034** |
| 0000346 | 940, 1035 | delete 1035 |
| 0000353 | 983, 1036 | delete 1036 |

In-process catheter SOs after this work should remain unshipped unless a trunk-stock photo exists:
`0000165`, `0000179`, `0000184`, `0000186`, `0000371`, `0000372`, `0000376`. Do not invent deliveries
for them. `0000275` and `0000366` **do** have photos and will become `cleartract_delivery`.

Existing SO lines that **disagree with the PDF** (parser residue — correct as cleanup, preview first):

| SO | Stored | PDF meaning | Use |
| --- | --- | --- | --- |
| 0000275 | 2 × 211810SPT | 1 × box of 10 (21800101003) | **10** |
| 0000366 | 2 × 211610SPT, customer `Urology` (763) | 4 × 16 Fr each, Day Kimball Health | **4**, customer Day Kimball |

~66 of 2025+ distributions have a sales order but no packing-slip attachment. The monthly
`*PackingSlips.pdf` files in `Distribution/` are the source. 149 attachments are still named
`May26PackingSlips.pdf_page_7.pdf` and similar.

## Task A — Import the missing sales orders

Authoritative file: `Distribution/SalesOrders2025-Aug2126.pdf` (226 pages, 225 orders).
`Distribution/2025Sales Orders.pdf` only runs through 0000279; do not prefer it.

Use the existing sales-order PDF import. Existing P4-01 guards stay in force: do not delete packing
slips on re-import; do not repoint an already-set `customer_id`. After import, **preview then
correct** the two stored-quantity errors in the table above, and re-key `0000366` / `0000376` from
customer `Urology` (763) to a Day Kimball customer created from that SO's ship-to (or the existing
one if import created it). `0000376` stays in-process (no trunk-stock photo).

If the live parser still stores `0000275` as qty 2, fix the stored line. Do not add a new
classification feature; a parser correction is in scope only if a fixture from this PDF page fails
today. Say which you did.

## Task B — Import packing slips and match them

Import every `Distribution/*PackingSlips.pdf` through the existing packing-slip bulk import. Match
by normalized order number to the distribution. One sales order may have many distributions
(`0000125` is the standing example) — each distribution gets **its own** slip, never a second copy
of the SO PDF as the verification file.

After import, list every 2025+ distribution that still has no packing slip and no trunk-stock photo.
Do not invent files for them.

## Task C — Five trunk-stock manual distributions

Create one **manual** distribution per photo, using the existing manual-entry path
(`source="manual"`). Attach the photo as the single verification file (`pdf_type` already used for
manual uploads is fine — do not add a type). Link to the sales order. Delivery date and lots come
from the form; quantities come from the **sales order** (D62). `safe_apply_order_type` will move
`0000275` and `0000366` to `cleartract_delivery`; the three new SOs will classify the same way once
linked.

| File | SO | Delivery date | Customer | Lots and qty on the form | SO qty to store |
| --- | --- | --- | --- | --- | --- |
| `TrunkStockDistributions/Harbor 12.5.25SO 0000275.JPG` | 0000275 (exists, id 1338, Harbor 610) | 2025-12-05 | Harbor UCLA (610) | SLQ-05022025 × 10 of 211810SPT | **10** |
| `TrunkStockDistributions/DayKimball7726. SO0000366.jpeg` | 0000366 (exists, currently `Urology`) | 2026-07-07 | Day Kimball Health Urology | SLQ-05012025 × 4 of 211610SPT | **4** |
| `TrunkStockDistributions/UnivUtah12826 SO 000387.jpeg` | 0000387 (import in Task A) | 2026-01-28 | University of Utah Health | SLQ-05022025 × 4, SLQ-05012025 × 4 | **8** (4+4) |
| `TrunkStockDistributions/LinehanProvidenceStJohns 8.7.26 SO 388.JPG` | 0000388 (import in Task A) | 2026-08-07 | Providence Saint John's | SLQ-05012025 × 4, SLQ-05022025 × 4 (D67) | **8** (4+4) |
| `TrunkStockDistributions/Lyn Hopkins 2.2.26 390.JPG` | 0000390 (import in Task A) | **2026-02-26** (D68) | UCLA Urology (Lynn Hopkins) | SLQ-05012025 × 2 of 211610SPT, SLQ-05022025 × 2 of 211810SPT | **4** (2+2) |

All five lots were readable. SKU codes on the forms: 211810SPT / 211610SPT (Day Kimball wrote
`2116105PT` — that is 211610SPT). Valid SKUs are only `211810SPT`, `211610SPT`, `211410SPT`.

Preview the five rows, then execute. Audit each create and each link.

## Task D — Delete the four confirmed duplicate distributions

Preview, then delete ids **1033, 1034, 1035, 1036** only. Snapshot each row in the audit event.
Do not delete attachments' storage objects that are still referenced by the surviving row.

Do **not** delete 789 or 1032 (`0000203`) or 833 or 834 (`0000251`).

## Task E — Rename packing-slip filenames (D65)

For every `pdf_type` that `is_packing_slip_pdf_type` accepts, set `filename` to
`{Customer}_{YYYY-MM-DD}_SO{normalized 7-digit}.pdf`. Customer token: letters/digits from the
distribution's customer facility name (or ship-to name), no spaces. Date = that distribution's
`ship_date`. If two slips would collide, append `_2`. Preview the rename list; execute.

Do not rename sales-order PDFs (`SO_0000336.pdf` is already fine).

## Task F — Coverage report (read-only, after the writes)

Print, ASCII only:

1. Every 2025+ distribution with no sales order (expected: 0000145, 0000164, and nothing else).
2. Every 2025+ distribution with a sales order but no verification file.
3. Every 2025+ distribution with more than one verification file.
4. The five trunk-stock rows: dist id, SO, date, lots, qty, customer, filename.
5. Remaining `cleartract_in_process` orders.
6. Confirmation that dashboard unit total moved only by the five new deliveries (10+4+8+8+4 = **34**)
   minus units on the four deleted duplicates (30+30+40+30 = **130**). Show the arithmetic.
   Harbor 0000203 must still contribute **120** (two 60-unit rows).

## Task G — Customer Sales Orders tab units match Distributions (D69)

`templates/admin/customers/detail.html:226` currently prints
`{{ so.lines|sum(attribute='quantity') }}`. That is why Harbor 0000312 shows 6 and 0000203 shows 2
while the Distributions tab shows 30 and 60 (×2).

For each sales order on that tab, Total Units = `sum_distribution_units` of its linked
`DistributionLogEntry` rows. Same helper the overview and Distributions tab already use. If the
order has no linked distributions, fall back to the line-item sum so in-process orders still show
a number.

Do not add a second column and do not add helper text. The overview customer total must still
count **all** of that customer's distributions (P4-07 / D40), matched or not — Task G only changes
the per-order number on the Sales Orders tab.

Worked checks after Task D:
- Harbor 0000312 Total Units = **30** (one remaining distribution: 10+10+10).
- Harbor 0000203 Total Units = **120** (both 60-unit distributions).
- Harbor 0000275 Total Units = **10** once the trunk-stock row exists.

## Do not do these

- Do not add UI, fields, types, or a new import page.
- Do not invent sales orders for 0000145 / 0000164 (D64).
- Do not delete either 0000203 row or either 0000251 row (D66).
- Do not touch 2024 unmatched rows.
- Do not create deliveries for in-process orders that have no trunk-stock photo.
- Do not start customer-identity re-key beyond Day Kimball on 0000366 / 0000376.
- Do not start P4-08A_2 or P4-06D.
- No lateness/aging (D18).

## Tests

New file `tests/test_p4_08b_distribution_cleanup.py` — only what this change set could break:

1. Packing-slip import still matches by normalized order number and does not delete sales-order PDFs.
2. Re-import of a sales-order PDF does not delete a packing-slip or manual-upload attachment.
3. Filename helper produces `HarborUCLA_2026-05-19_SO0000336.pdf` from the obvious inputs.
4. Manual distribution linked to an in-process SO becomes `cleartract_delivery`.
5. Deleting a duplicate distribution does not delete a storage object still referenced by the
   surviving row.
6. Customer Sales Orders tab: an order with linked distributions shows the distribution unit sum,
   not the sales-order line sum, when those two numbers differ. An order with no distributions
   still shows the line sum.

Keep the existing suite green. Report the count after the **final** edit.

## Gate before pushing

1. Full suite green after the final edit.
2. `alembic heads` still a single head (no migration unless you stopped and explained).
3. `python -c "import app.wsgi"` succeeds; local Spaces `HeadBucket 403` is known.
4. Push to `main` and confirm `/health` returns `{"ok":true}`.

## Report back

- Task A: orders created vs already present; the 0000275 / 0000366 quantity corrections.
- Task B: slips imported, matched, still unmatched.
- Task C preview then executed rows.
- Task D: deleted ids 1033–1036; confirmation 0000203 still has both rows.
- Task G: Harbor 0000312 and 0000203 Total Units after the change.
- Task E: rename count.
- Task F coverage list, especially anything 2025+ that is still missing a file or a sales order.
- Anything you could not read or would have had to guess — stop and list it instead of guessing.
