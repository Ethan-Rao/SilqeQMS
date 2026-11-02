# NRE totals and pre-Q3 invoice dates

Code commit `7f0ca97` on `main`. Sales-order PDFs were not re-imported. ShipStation was not synced.

## Tiles

The date window is unchanged. The table under the tiles is still the orders in that window whose status is not `Payment Received`.

The tiles count every NRE sales order in the window, including `Payment Received`.

- Total NRE projects is that count.
- Customers is the distinct customers on those orders.
- Total Payments Received is the sum of `order_amount` where the status is `Payment Received`.
- Total Invoiced/Awaiting Payment replaces Total Amount Invoiced. It is the invoiced portion of `50% Invoiced` and `100% Invoiced` only.
- Still to invoice is the uninvoiced remainder of the table rows only.

Paid amounts are not included in Total Invoiced/Awaiting Payment. `Payment Received` orders stay out of the table and remain on the customer card.

## Invoice dates

Every NRE sales order dated before 1 July 2026 had `invoice_date` set to 60 days after its order date. That overwrote the date already stored. Invoice dates set: 21. No order in that set was missing an order date.

0000429 (16 October 2026) and 0000434 (27 October 2026) were not changed.
