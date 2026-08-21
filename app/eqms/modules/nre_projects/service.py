"""NRE Invoice Tracker <-> Sales Order matching (P4-04).

One match implementation; all entry points call these helpers.
Files MOVE (same storage_key) — never copy or delete Spaces objects.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from app.eqms.audit import record_event
from app.eqms.modules.nre_projects.models import (
    NREProjectEntry,
    NRETrackerAttachment,
    nre_invoiced_amount,
    nre_remaining_to_invoice,
)
from app.eqms.modules.rep_traceability.models import OrderPdfAttachment, SalesOrder
from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_NRE_PROJECT
from app.eqms.modules.rep_traceability.service import (
    find_sales_order_by_normalized_number,
    normalize_order_number,
    sales_order_has_catheter_sku,
)


def is_nre_dashboard_order(order) -> bool:
    """NRE-typed, not cancelled, and no catheter SKU lines (D72)."""
    if getattr(order, "order_type", None) != ORDER_TYPE_NRE_PROJECT:
        return False
    if (getattr(order, "status", None) or "") == "cancelled":
        return False
    return not sales_order_has_catheter_sku(order)

logger = logging.getLogger(__name__)

PDF_TYPE_NRE_TRACKER_FILE = "nre_tracker_file"

# Tracker legacy status -> SalesOrder.nre_invoice_status (Cancelled is special).
TRACKER_STATUS_TO_DASHBOARD: dict[str, str | None] = {
    "Pending Invoice": "Pending Invoice",
    "50% Invoiced": "50% Invoiced",
    "Invoiced": "100% Invoiced",
    "Paid": "Payment Received",
    "Cancelled": None,  # set SalesOrder.status = cancelled instead
}


class MatchError(ValueError):
    """Refused match/unmatch — flash this message."""


def _amount_decision(order: SalesOrder, entry: NREProjectEntry) -> dict[str, Any]:
    """Apply amount rules; return decision metadata for audit/UI."""
    so_amt = order.order_amount
    tr_amt = entry.invoice_amount
    if so_amt is None and tr_amt is not None:
        order.order_amount = tr_amt
        return {"action": "copied_from_tracker", "order_amount": str(tr_amt), "tracker_amount": str(tr_amt)}
    if so_amt is not None and tr_amt is not None and Decimal(str(so_amt)) != Decimal(str(tr_amt)):
        return {
            "action": "disagreement",
            "order_amount": str(so_amt),
            "tracker_amount": str(tr_amt),
        }
    return {
        "action": "unchanged",
        "order_amount": str(so_amt) if so_amt is not None else None,
        "tracker_amount": str(tr_amt) if tr_amt is not None else None,
    }


def _status_decision(order: SalesOrder, entry: NREProjectEntry) -> dict[str, Any]:
    """Map tracker status onto the sales order per Task D."""
    raw = (entry.invoice_status or "").strip()
    current = (order.nre_invoice_status or "Pending Invoice").strip() or "Pending Invoice"
    if raw not in TRACKER_STATUS_TO_DASHBOARD:
        return {
            "action": "unrecognized_tracker_status",
            "tracker_status": raw,
            "order_nre_invoice_status": current,
            "applied": False,
        }

    if raw == "Cancelled":
        before_status = order.status
        if current != "Pending Invoice":
            return {
                "action": "cancelled_skipped_operator_status",
                "tracker_status": raw,
                "order_nre_invoice_status": current,
                "order_status_before": before_status,
                "applied": False,
            }
        order.status = "cancelled"
        return {
            "action": "set_order_cancelled",
            "tracker_status": raw,
            "order_status_before": before_status,
            "order_status_after": "cancelled",
            "applied": True,
        }

    mapped = TRACKER_STATUS_TO_DASHBOARD[raw]
    if current != "Pending Invoice":
        return {
            "action": "skipped_operator_status",
            "tracker_status": raw,
            "mapped": mapped,
            "order_nre_invoice_status": current,
            "applied": False,
            "disagreement": current != mapped,
        }
    order.nre_invoice_status = mapped
    return {
        "action": "mapped",
        "tracker_status": raw,
        "mapped": mapped,
        "order_nre_invoice_status_before": current,
        "applied": True,
    }


def match_tracker_to_sales_order(
    s,
    *,
    entry: NREProjectEntry,
    order: SalesOrder,
    user=None,
    how: str = "manual",
) -> dict[str, Any]:
    """Match a tracker entry to an NRE sales order and move attachments.

    Raises MatchError when refused. Idempotent for the same pair.
    """
    if order.order_type != ORDER_TYPE_NRE_PROJECT:
        raise MatchError("Sales order must be typed NRE Project to match.")

    if entry.sales_order_id and entry.sales_order_id != order.id:
        raise MatchError("Tracker entry is already matched to a different sales order.")

    already = entry.sales_order_id == order.id
    files_moved: list[str] = []

    if not already:
        entry.sales_order_id = order.id
        # Move every attachment (reuse storage_key; do not touch Spaces).
        for att in list(entry.attachments or []):
            # Skip if an SO attachment already references this exact storage_key
            exists = (
                s.query(OrderPdfAttachment)
                .filter(
                    OrderPdfAttachment.sales_order_id == order.id,
                    OrderPdfAttachment.storage_key == att.storage_key,
                )
                .first()
            )
            if not exists:
                s.add(
                    OrderPdfAttachment(
                        sales_order_id=order.id,
                        distribution_entry_id=None,
                        storage_key=att.storage_key,
                        filename=att.filename,
                        pdf_type=PDF_TYPE_NRE_TRACKER_FILE,
                        content_type=att.content_type,
                        size_bytes=att.size_bytes,
                        uploaded_by_user_id=att.uploaded_by_user_id,
                    )
                )
                files_moved.append(att.filename)
            s.delete(att)
        # Clear relationship so cascade delete-orphan does not re-DELETE moved rows.
        entry.attachments = []
    else:
        # Idempotent re-match: ensure no leftover tracker attachments for this entry.
        for att in list(entry.attachments or []):
            exists = (
                s.query(OrderPdfAttachment)
                .filter(
                    OrderPdfAttachment.sales_order_id == order.id,
                    OrderPdfAttachment.storage_key == att.storage_key,
                )
                .first()
            )
            if not exists:
                s.add(
                    OrderPdfAttachment(
                        sales_order_id=order.id,
                        distribution_entry_id=None,
                        storage_key=att.storage_key,
                        filename=att.filename,
                        pdf_type=PDF_TYPE_NRE_TRACKER_FILE,
                        content_type=att.content_type,
                        size_bytes=att.size_bytes,
                        uploaded_by_user_id=att.uploaded_by_user_id,
                    )
                )
                files_moved.append(att.filename)
            s.delete(att)
        entry.attachments = []

    amount_meta = _amount_decision(order, entry)
    status_meta = _status_decision(order, entry)
    s.flush()

    meta = {
        "entry_id": entry.id,
        "sales_order_id": order.id,
        "order_number": order.order_number,
        "how": how,
        "files_moved": files_moved,
        "files_moved_count": len(files_moved),
        "amount": amount_meta,
        "status": status_meta,
        "idempotent": already and not files_moved,
    }
    record_event(
        s,
        actor=user,
        action="nre_tracker.matched_sales_order",
        entity_type="NREProjectEntry",
        entity_id=str(entry.id),
        metadata=meta,
    )
    s.flush()
    return meta


def unmatch_tracker_from_sales_order(
    s,
    *,
    entry: NREProjectEntry,
    user=None,
) -> dict[str, Any]:
    """Clear match and move nre_tracker_file attachments back onto the entry."""
    if not entry.sales_order_id:
        raise MatchError("Tracker entry is not matched.")

    order = s.get(SalesOrder, entry.sales_order_id)
    order_id = entry.sales_order_id
    order_number = order.order_number if order else None
    files_returned: list[str] = []

    if order:
        moved = (
            s.query(OrderPdfAttachment)
            .filter(
                OrderPdfAttachment.sales_order_id == order.id,
                OrderPdfAttachment.pdf_type == PDF_TYPE_NRE_TRACKER_FILE,
            )
            .all()
        )
        for att in moved:
            s.add(
                NRETrackerAttachment(
                    nre_entry_id=entry.id,
                    filename=att.filename,
                    storage_key=att.storage_key,
                    content_type=att.content_type,
                    size_bytes=att.size_bytes,
                    uploaded_by_user_id=att.uploaded_by_user_id,
                )
            )
            files_returned.append(att.filename)
            s.delete(att)

    entry.sales_order_id = None
    s.flush()

    meta = {
        "entry_id": entry.id,
        "sales_order_id": order_id,
        "order_number": order_number,
        "how": "manual",
        "files_moved": files_returned,
        "files_moved_count": len(files_returned),
    }
    record_event(
        s,
        actor=user,
        action="nre_tracker.unmatched_sales_order",
        entity_type="NREProjectEntry",
        entity_id=str(entry.id),
        metadata=meta,
    )
    s.flush()
    return meta


def find_unmatched_entry_by_order_number(s, order_number: str | None) -> NREProjectEntry | None:
    target = normalize_order_number(order_number)
    if not target:
        return None
    entries = (
        s.query(NREProjectEntry)
        .filter(NREProjectEntry.sales_order_id.is_(None))
        .all()
    )
    for e in entries:
        if normalize_order_number(e.order_ref) == target:
            return e
    return None


def find_unmatched_nre_order_by_ref(s, order_ref: str | None) -> SalesOrder | None:
    so = find_sales_order_by_normalized_number(s, order_ref)
    if not so:
        return None
    if so.order_type != ORDER_TYPE_NRE_PROJECT:
        return None
    if so.status == "cancelled":
        return None
    # Already matched to another entry?
    existing = (
        s.query(NREProjectEntry)
        .filter(NREProjectEntry.sales_order_id == so.id)
        .first()
    )
    if existing:
        return None
    return so


def safe_auto_match_order(s, order, *, user=None) -> None:
    """Never-abort wrapper: match an NRE sales order to an unmatched tracker entry."""
    if order is None:
        return
    try:
        if getattr(order, "order_type", None) != ORDER_TYPE_NRE_PROJECT:
            return
        entry = find_unmatched_entry_by_order_number(s, order.order_number)
        if entry is None:
            return
        match_tracker_to_sales_order(
            s, entry=entry, order=order, user=user, how="auto_order_number"
        )
    except MatchError:
        logger.info(
            "auto_match_order refused for order=%s",
            getattr(order, "id", order),
        )
    except Exception:
        logger.exception(
            "auto_match_order failed for order=%s",
            getattr(order, "id", order),
        )


def safe_auto_match_entry(s, entry, *, user=None) -> None:
    """Never-abort wrapper: match a tracker entry to an existing NRE sales order."""
    if entry is None:
        return
    try:
        if entry.sales_order_id:
            return
        order = find_unmatched_nre_order_by_ref(s, entry.order_ref)
        if order is None:
            return
        match_tracker_to_sales_order(
            s, entry=entry, order=order, user=user, how="auto_order_number"
        )
    except MatchError:
        logger.info(
            "auto_match_entry refused for entry=%s",
            getattr(entry, "id", entry),
        )
    except Exception:
        logger.exception(
            "auto_match_entry failed for entry=%s",
            getattr(entry, "id", entry),
        )


def compute_nre_dashboard(s, *, start_date, end_date) -> dict[str, Any]:
    """NRE dashboard metrics for order_date in [start_date, end_date].

    Same rules as the NRE Projects page: ``nre_project`` type, not cancelled,
    Total Amount Invoiced uses ``nre_invoiced_amount()``.
    """
    from app.eqms.modules.customer_profiles.models import Customer

    typed = (
        s.query(SalesOrder)
        .filter(
            SalesOrder.order_type == ORDER_TYPE_NRE_PROJECT,
            SalesOrder.status != "cancelled",
        )
        .all()
    )
    eligible = [o for o in typed if is_nre_dashboard_order(o)]
    nre_ids = sorted({o.customer_id for o in eligible if o.customer_id is not None})
    nre_customers = s.query(Customer).filter(Customer.id.in_(nre_ids)).all() if nre_ids else []
    customers_by_id = {c.id: c for c in nre_customers}

    filtered_orders: list[SalesOrder] = []
    orders_outside_range = 0
    if nre_ids:
        filtered_orders = [
            o
            for o in eligible
            if o.customer_id in set(nre_ids)
            and o.order_date is not None
            and start_date <= o.order_date <= end_date
        ]
        filtered_orders.sort(key=lambda o: (o.order_date or start_date, o.order_number or ""), reverse=True)
        orders_outside_range = sum(
            1
            for o in eligible
            if o.customer_id in set(nre_ids)
            and (o.order_date is None or o.order_date < start_date or o.order_date > end_date)
        )

    project_count = len(filtered_orders)
    amounts = [o.order_amount for o in filtered_orders if o.order_amount is not None]
    rows = []
    for o in filtered_orders:
        cust = customers_by_id.get(o.customer_id)
        rows.append(
            {
                "customer_name": cust.facility_name if cust else None,
                "order_number": o.order_number,
                "order_date": o.order_date,
                "order_amount": o.order_amount,
                "invoice_date": o.invoice_date,
                "status": o.nre_invoice_status or "Pending Invoice",
            }
        )
    return {
        "orders": filtered_orders,
        "rows": rows,
        "customers_by_id": customers_by_id,
        "project_count": project_count,
        "customer_count": len({o.customer_id for o in filtered_orders}),
        "revenue": sum(
            (nre_invoiced_amount(o.nre_invoice_status, o.order_amount) for o in filtered_orders),
            Decimal("0"),
        ),
        "still_to_invoice": sum(
            (nre_remaining_to_invoice(o.nre_invoice_status, o.order_amount) for o in filtered_orders),
            Decimal("0"),
        ),
        "missing_amounts": project_count - len(amounts),
        "orders_outside_range": orders_outside_range,
    }


def amount_disagreement(order: SalesOrder, entry: NREProjectEntry | None) -> dict[str, str] | None:
    if not entry or entry.sales_order_id != order.id:
        return None
    if order.order_amount is None or entry.invoice_amount is None:
        return None
    if Decimal(str(order.order_amount)) == Decimal(str(entry.invoice_amount)):
        return None
    return {
        "order_amount": str(order.order_amount),
        "tracker_amount": str(entry.invoice_amount),
    }


def status_disagreement(order: SalesOrder, entry: NREProjectEntry | None) -> dict[str, str] | None:
    if not entry or entry.sales_order_id != order.id:
        return None
    raw = (entry.invoice_status or "").strip()
    if raw not in TRACKER_STATUS_TO_DASHBOARD or raw == "Cancelled":
        return None
    mapped = TRACKER_STATUS_TO_DASHBOARD[raw]
    current = (order.nre_invoice_status or "Pending Invoice").strip()
    if current == mapped:
        return None
    return {"tracker_status": raw, "mapped": mapped or "", "order_status": current}
