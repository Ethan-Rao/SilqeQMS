# NRE dashboard dates, status, and save

Code commit `f47eade` on `main`. Sales-order PDFs were not re-imported. ShipStation was not synced.

## List

Before Apply, and after Clear dates, the date fields are 1 July 2026 through the last day of the current quarter. On 2 November 2026 that end date is 31 December 2026. The table includes every NRE sales order in the range, including `100% Invoiced`. `Payment Received` is omitted from the table and still appears on the customer card. Apply uses the dates in the query and still omits `Payment Received`. The sentences under the tiles and the earlier-period sections stay gone.

## Save

Invoice date and status on a dashboard row, and on an order row inside a customer card, no longer submit on change. Each of those rows has a Save button on the right. The row is written when Save is pressed, and the page reloads. A row saved as `Payment Received` leaves the table and remains under that customer.

## Live data

Every NRE sales order dated before 1 July 2026 was already `Payment Received`. That was 21 orders. Rows updated: 0.

0000429 is dated 16 October 2026 and is `Awaiting PO`. 0000434 is dated 27 October 2026 and is `100% Invoiced`. Both are on or after 1 July 2026, so neither was changed.
