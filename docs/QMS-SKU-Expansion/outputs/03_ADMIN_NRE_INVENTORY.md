# Admin Tools, NRE list, and lot inventory

The three screens in `docs/QMS-SKU-Expansion/prompts/03_ADMIN_NRE_INVENTORY_PROMPT.md` are in this change, plus the manufacture and expiration dates Ethan supplied for the two new lots. Deploy is a push to `main`. Sales-order PDFs were not re-imported. ShipStation was not synced. The DCO log was not loaded.

## Lot inventory

`compute_lot_inventory_snapshot` in `app/eqms/modules/rep_traceability/service.py` still requires a manufacture date and an expiration date for 14, 16, and 18 Fr. A 212010SPT or 212210SPT lot with a produced quantity is included even when either date is blank. The Sales Dashboard card already prints an em dash when a date is missing (`lot.mfg_date or "—"`). A zero-quantity 20 Fr or 22 Fr lot stays off the card. The 60 units designated for destructive testing are not subtracted.

LotLog dates, as given:

| Lot | Catalog | Manufactured | Expires | Units |
| --- | --- | --- | --- | --- |
| SLQ-08272026 | 212010SPT | 8/27/2026 | 8/27/2029 | 494 |
| SLQ-08282026 | 212210SPT | 8/26/2026 | 8/26/2029 | 477 |

SLQ-08282026 was manufactured on 26 August 2026, not on the date in the lot number. Those dates are in `app/eqms/data/LotLog.csv`. Production reads `data/LotLog.csv` from storage before the repo file. `scripts/release.py` already published a lot only when storage lacked it. It now also fills a blank manufacture or expiration date from the repo copy and leaves any date storage already has. A later deploy fills these two rows if production still has them blank.

## NRE dashboard

The page opens on every NRE sales order that is not fully invoiced and whose order date is on or after 1 January 2026. The date fields are empty until Apply. Fully invoiced means `100% Invoiced` or `Payment Received`. After Apply, the same open-order rule is limited to the chosen dates, and orders before 2026 still do not appear. Clear dates returns to that default list. The cover sentences and the two extra tables are gone. One table. The metric tiles count that same list.

`Awaiting PO` is the first value in `NRE_DASHBOARD_STATUSES`. It is an open status. Its invoiced amount is zero, the same as Pending Invoice. The column is already `String(32)`. The weekly brief does not build its status list from that constant, so the email was not changed and the removed sentences were not added to it. The brief still uses the current-quarter snapshot.

## Admin Tools

Each of the three import boxes is a title, the control, and one short line. The distribution CSV note, the unmatched-distribution line, and the danger-zone line are one line each. No tools were added. Unmatched distributions stay limited to ship dates on or after 1 January 2026.

## Tests

109 passed on the NRE, lot-inventory, weekly-brief, and 20/22 Fr files. An undated 212010SPT lot with a produced quantity is in the snapshot and is not reduced by 60. An undated 211810SPT lot is not. A dated 18 Fr lot still is.
