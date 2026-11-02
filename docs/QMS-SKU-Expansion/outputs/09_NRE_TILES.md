# NRE tiles include orders the table hides

Code commit `8edd246` on `main`. Sales-order PDFs were not re-imported. ShipStation was not synced. Statuses and invoice dates were not changed.

The upper table is unchanged. It lists NRE orders whose order date is in the selected window and whose status is not `Payment Received`. Still to invoice is the uninvoiced remainder of those rows only.

The five tiles use a wider set. An order is included when its order date is in the window or its invoice date is. Total NRE projects and Customers count that set. Total Payments Received sums `order_amount` for `Payment Received` in that set. Total Invoiced/Awaiting Payment sums the invoiced portion of `50% Invoiced` and `100% Invoiced` in that set, and does not include paid, Awaiting PO, or Pending Invoice amounts.

For 1 October 2026 through 31 December 2026, that adds 0000420 ($4,830.00, invoiced 30 October) to Total Invoiced/Awaiting Payment and 0000400 ($4,982.50, paid 9 October) to Total Payments Received. Orders whose invoice dates are before 1 October stay out. 0000434 stays in the upper table. `Payment Received` stays out of it.
