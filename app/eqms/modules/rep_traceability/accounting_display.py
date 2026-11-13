"""Accounting invoice figures for the sales dashboard, the NRE dashboard, and the weekly brief.

An order is listed from its order date. An invoice counts in the total from its
invoice date. Those two sets are not required to match.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from app.eqms.modules.rep_traceability.models import AccountingInvoiceGroup, SalesOrder
from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_NRE_PROJECT

NRE_UNLINKED = frozenset({"0000305", "0000306"})
CATHETER_UNLINKED = frozenset({"0000301", "0000302"})
NEEDS_INVOICE = frozenset({"No Invoice", "Partly invoiced"})
NOT_FULLY_PAID = frozenset({"Open", "Partly invoiced", "No Invoice"})
TRACKER_PAID = frozenset({"Paid", "Payment Received"})
SALES_ORDER_PDF_TYPES = ("sales_order_page", "sales_order", "matched_upload")


def format_whole_dollars(value) -> str:
    """Whole dollars for the sales dashboard, the NRE dashboard, and the weekly brief.

    Half rounds up. A blank stays blank. Stored amounts are not changed.
    """
    if value is None:
        return "—"
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").strip()
        if not cleaned:
            return "—"
        value = cleaned
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return "—"
    rounded = amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"${rounded:,.0f}"


def date_in_range(day: date | None, start: date | None, end: date | None) -> bool:
    if day is None:
        return False
    if start is not None and day < start:
        return False
    if end is not None and day > end:
        return False
    return True


def _dec(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def remainder_to_invoice(group: AccountingInvoiceGroup) -> Decimal:
    """Amount still to invoice. No Invoice uses the quote total. Partly invoiced uses the remainder."""
    quote = _dec(group.quote_history_order_total)
    if group.status == "No Invoice":
        return quote
    if group.status == "Partly invoiced":
        invoiced = sum((_dec(inv.invoice_total) for inv in group.invoices), Decimal("0"))
        gap = quote - invoiced
        return gap if gap > 0 else Decimal("0")
    return Decimal("0")


def page_for_group(group: AccountingInvoiceGroup, order: SalesOrder | None) -> str | None:
    if group.sales_order_id is None:
        numbers = {inv.invoice_number for inv in group.invoices}
        if numbers & NRE_UNLINKED:
            return "nre"
        if numbers & CATHETER_UNLINKED:
            return "catheter"
        return None
    if order is None:
        return None
    if order.order_type == ORDER_TYPE_NRE_PROJECT:
        return "nre"
    return "catheter"


def page_for_order(order: SalesOrder) -> str:
    if order.order_type == ORDER_TYPE_NRE_PROJECT:
        return "nre"
    return "catheter"


def _invoice_rows(group: AccountingInvoiceGroup) -> list[dict]:
    rows = []
    for inv in sorted(group.invoices, key=lambda item: item.invoice_number):
        rows.append({
            "number": inv.invoice_number,
            "date": inv.invoice_date,
            "total": inv.invoice_total,
            "payment": inv.payment,
            "open_balance": inv.open_balance,
        })
    return rows


def accounting_for_page(session, *, start: date | None, end: date | None, page: str) -> dict:
    """Catheter or NRE figures for one date window."""
    groups = session.query(AccountingInvoiceGroup).all()
    orders = (
        session.query(SalesOrder)
        .filter(SalesOrder.status != "cancelled")
        .all()
    )
    orders_by_id = {order.id: order for order in orders}
    group_by_order = {group.sales_order_id: group for group in groups if group.sales_order_id}

    invoice_total = Decimal("0")
    open_balance = Decimal("0")
    for group in groups:
        order = orders_by_id.get(group.sales_order_id) if group.sales_order_id else None
        if page_for_group(group, order) != page:
            continue
        for inv in group.invoices:
            if not date_in_range(inv.invoice_date, start, end):
                continue
            invoice_total += _dec(inv.invoice_total)
            open_balance += _dec(inv.open_balance)

    listed = []
    for order in orders:
        if page_for_order(order) != page:
            continue
        if not date_in_range(order.order_date, start, end):
            continue
        group = group_by_order.get(order.id)
        status = group.status if group else ""
        quote = group.quote_history_order_total if group else None
        unpaid = (
            sum((_dec(inv.open_balance) for inv in group.invoices), Decimal("0"))
            if group
            else Decimal("0")
        )
        not_yet_invoiced = remainder_to_invoice(group) if group else Decimal("0")
        listed.append({
            "order_id": order.id,
            "order_number": order.order_number,
            "customer_name": order.customer.facility_name if order.customer else "",
            "order_date": order.order_date,
            "order_amount": order.order_amount,
            "amount": quote if quote is not None else order.order_amount,
            "status": status,
            "invoices": _invoice_rows(group) if group else [],
            "needs_invoice": status in NEEDS_INVOICE,
            "is_open": status == "Open",
            "not_yet_invoiced": not_yet_invoiced,
            "open_balance": unpaid,
            "not_yet_received": unpaid + not_yet_invoiced,
        })
    listed.sort(key=lambda row: (row["order_date"], row["order_number"] or ""), reverse=True)

    still = Decimal("0")
    for row in listed:
        group = group_by_order.get(row["order_id"])
        if group and group.status in NEEDS_INVOICE:
            still += remainder_to_invoice(group)

    unlinked = []
    for group in groups:
        if group.sales_order_id is not None:
            continue
        if page_for_group(group, None) != page:
            continue
        invoices = [inv for inv in group.invoices if date_in_range(inv.invoice_date, start, end)]
        if not invoices:
            continue
        unlinked.append({
            "status": group.status,
            "invoices": _invoice_rows(group),
        })

    return {
        "invoice_total": invoice_total,
        "open_balance": open_balance,
        "still_to_invoice": still,
        "orders": listed,
        "needs_invoice": [row for row in listed if row["needs_invoice"]],
        "open_orders": [row for row in listed if row["is_open"]],
        "unlinked": unlinked,
    }


def accounting_by_order_id(session) -> dict[int, dict]:
    """Status and invoices for every linked group, independent of the date window."""
    groups = (
        session.query(AccountingInvoiceGroup)
        .filter(AccountingInvoiceGroup.sales_order_id.isnot(None))
        .all()
    )
    return {
        group.sales_order_id: {
            "status": group.status,
            "invoices": _invoice_rows(group),
        }
        for group in groups
    }


def open_not_yet_received(page: dict) -> Decimal:
    """Open tile: unpaid invoice balances plus the amount still to invoice."""
    return _dec(page.get("open_balance")) + _dec(page.get("still_to_invoice"))


def orders_still_needing_invoice(*order_lists) -> list[dict]:
    """Catheter and NRE orders whose accounting status is No Invoice or Partly invoiced."""
    rows = []
    for order_list in order_lists:
        for row in order_list:
            if not row.get("needs_invoice"):
                continue
            rows.append(row)
    rows.sort(key=lambda row: (row.get("order_date") or date.min, row.get("order_number") or ""))
    return rows


def open_nre_projects(rows: list[dict]) -> list[dict]:
    """Open NRE projects with no date window.

    Accounting status Open, Partly invoiced, or No Invoice qualifies. A paid
    project stays on the list when its tracker says Open.
    """
    chosen = []
    for row in rows:
        status = row.get("status") or ""
        tracker = (row.get("tracker_status") or "").strip()
        if status in NOT_FULLY_PAID or tracker.lower() == "open":
            chosen.append(row)
    chosen.sort(
        key=lambda row: (row.get("order_date") or date.min, row.get("order_number") or ""),
        reverse=True,
    )
    return chosen


def open_nre_card_amounts(rows: list[dict]) -> tuple[Decimal, Decimal]:
    """Still to invoice, then Open, for every open project."""
    projects = open_nre_projects(rows)
    still = sum((_dec(row.get("not_yet_invoiced")) for row in projects), Decimal("0"))
    opened = sum((_dec(row.get("not_yet_received")) for row in projects), Decimal("0"))
    return still, opened


def nre_projects_not_fully_paid(rows: list[dict]) -> list[dict]:
    """Open, partly invoiced, or not invoiced. A paid project stays off unless the tracker says otherwise."""
    chosen = []
    for row in rows:
        status = row.get("status") or ""
        tracker = (row.get("tracker_status") or "").strip()
        if status in NOT_FULLY_PAID:
            chosen.append(row)
        elif status == "Paid" and tracker and tracker not in TRACKER_PAID:
            chosen.append(row)
    chosen.sort(key=lambda row: (row.get("order_date") or date.min, row.get("order_number") or ""))
    return chosen
