"""Load the accounting invoice CSV onto sales orders.

Replaces the invoice rows as a set. Does not delete sales orders and does not
write quote-history totals into sales_orders.order_amount.
"""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from app.eqms.modules.rep_traceability.models import AccountingInvoice, AccountingInvoiceGroup
from app.eqms.modules.rep_traceability.service import find_sales_order_by_normalized_number

ORDER_STATUSES = frozenset(
    {"No Invoice", "Partly invoiced", "Open", "Paid", "No sales order"}
)


class AccountingInvoiceLoadError(RuntimeError):
    pass


def _money(value: str | None) -> Decimal | None:
    text = (value or "").strip()
    if not text:
        return None
    return Decimal(text).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _invoice_date(value: str | None) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    return date.fromisoformat(text)


def load_accounting_invoices(session, csv_path: str | Path) -> None:
    path = Path(csv_path)
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    session.query(AccountingInvoice).delete(synchronize_session=False)
    session.query(AccountingInvoiceGroup).delete(synchronize_session=False)
    session.flush()

    grouped: dict[str, list[dict]] = {}
    unlinked: list[dict] = []
    for row in rows:
        order_number = (row.get("order_number") or "").strip()
        status = (row.get("status") or "").strip()
        if status not in ORDER_STATUSES:
            raise AccountingInvoiceLoadError(f"Unknown status {status!r} on {order_number or row.get('invoice_number')}")
        if order_number:
            grouped.setdefault(order_number, []).append(row)
        else:
            unlinked.append(row)

    for order_number, order_rows in grouped.items():
        sales_order = find_sales_order_by_normalized_number(session, order_number)
        if sales_order is None:
            raise AccountingInvoiceLoadError(f"No sales order for {order_number}")
        statuses = {(row.get("status") or "").strip() for row in order_rows}
        if len(statuses) != 1:
            raise AccountingInvoiceLoadError(f"{order_number} has more than one status: {sorted(statuses)}")
        group = AccountingInvoiceGroup(
            sales_order_id=sales_order.id,
            order_number=order_number,
            status=statuses.pop(),
            quote_history_order_total=_money(order_rows[0].get("quote_history_order_total")),
        )
        session.add(group)
        session.flush()
        for row in order_rows:
            invoice_number = (row.get("invoice_number") or "").strip()
            if not invoice_number:
                continue
            session.add(
                AccountingInvoice(
                    group_id=group.id,
                    invoice_number=invoice_number,
                    invoice_date=_invoice_date(row.get("invoice_date")),
                    invoice_total=_money(row.get("invoice_total")),
                    payment=(row.get("payment") or "").strip(),
                    open_balance=_money(row.get("open_balance")),
                )
            )

    for row in unlinked:
        invoice_number = (row.get("invoice_number") or "").strip()
        if not invoice_number:
            raise AccountingInvoiceLoadError("A row has no order number and no invoice number.")
        group = AccountingInvoiceGroup(
            sales_order_id=None,
            order_number=None,
            status=(row.get("status") or "").strip(),
            quote_history_order_total=None,
        )
        session.add(group)
        session.flush()
        session.add(
            AccountingInvoice(
                group_id=group.id,
                invoice_number=invoice_number,
                invoice_date=_invoice_date(row.get("invoice_date")),
                invoice_total=_money(row.get("invoice_total")),
                payment=(row.get("payment") or "").strip(),
                open_balance=_money(row.get("open_balance")),
            )
        )
    session.flush()
