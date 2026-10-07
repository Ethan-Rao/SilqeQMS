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


# ── Candidate matching ───────────────────────────────────────────────────────
# Tracker entries are written before the sales order exists, so Project/Order
# Ref is usually blank and the amount is an estimate. Matching therefore leans
# on customer identity, with the amount as a guard rather than a key.

# An estimate this far from the order total still identifies the same job.
MATCH_AMOUNT_TOLERANCE_PCT = Decimal("0.03")
MATCH_AMOUNT_TOLERANCE_FLOOR = Decimal("75")

# Dropped when comparing company names; they vary by who typed the row.
_LEGAL_SUFFIXES = frozenset(
    {"inc", "llc", "ltd", "limited", "gmbh", "corp", "corporation", "co",
     "company", "plc", "ag", "bv", "nv", "lp", "llp", "sa", "srl", "pty"}
)


def normalize_company_name(name: str | None) -> str:
    """Lowercase, strip punctuation and legal suffixes for comparison."""
    import re

    cleaned = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    words = [w for w in cleaned.split() if w and w not in _LEGAL_SUFFIXES]
    return " ".join(words)


def names_refer_to_same_company(a: str | None, b: str | None) -> bool:
    """True when one name is the other, or a leading part of it.

    'Neptune' and 'Neptune Medical, Inc.' are the same account; 'Aspero' and
    'Aspirus' are not.
    """
    na, nb = normalize_company_name(a), normalize_company_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = sorted((na, nb), key=len)
    return longer.startswith(shorter + " ")


def entry_matches_customer(entry: NREProjectEntry, customer) -> bool:
    if customer is None:
        return False
    return names_refer_to_same_company(entry.customer_name, customer.facility_name)


def amount_tolerance(amount) -> Decimal | None:
    """How far a tracker estimate may sit from an order total and still match."""
    if amount is None:
        return None
    pct = abs(Decimal(str(amount))) * MATCH_AMOUNT_TOLERANCE_PCT
    return max(pct, MATCH_AMOUNT_TOLERANCE_FLOOR)


def _amount_gap(order: SalesOrder, entry: NREProjectEntry) -> Decimal | None:
    if order.order_amount is None or entry.invoice_amount is None:
        return None
    return abs(Decimal(str(order.order_amount)) - Decimal(str(entry.invoice_amount)))


def _open_entries(s) -> list[NREProjectEntry]:
    return (
        s.query(NREProjectEntry)
        .filter(NREProjectEntry.sales_order_id.is_(None))
        .all()
    )


def _ref_contradicts(entry: NREProjectEntry, order: SalesOrder) -> bool:
    """True when the operator named a different order on the tracker row.

    An order ref that was typed deliberately outranks any guess we would make
    from customer and amount.
    """
    ref = normalize_order_number(entry.order_ref)
    if not ref:
        return False
    return ref != normalize_order_number(order.order_number)


def _pick_confident(order: SalesOrder, candidates: list[NREProjectEntry]):
    """Choose one entry from same-customer candidates, or None if ambiguous.

    A single candidate is enough when there is nothing to confuse it with.
    Otherwise the amounts must separate them: exactly one inside tolerance.
    """
    if not candidates:
        return None, None
    if len(candidates) == 1:
        gap = _amount_gap(order, candidates[0])
        tol = amount_tolerance(order.order_amount)
        if gap is not None and tol is not None and gap > tol:
            return None, None
        return candidates[0], "customer_unique"

    tol = amount_tolerance(order.order_amount)
    if tol is None:
        return None, None
    within = []
    for e in candidates:
        gap = _amount_gap(order, e)
        if gap is not None and gap <= tol:
            within.append((gap, e))
    if len(within) != 1:
        return None, None
    return within[0][1], "customer_amount"


def find_automatch_entry_for_order(s, order: SalesOrder):
    """Entry to auto-match to a newly imported order, with the reason why."""
    by_ref = find_unmatched_entry_by_order_number(s, order.order_number)
    if by_ref is not None:
        return by_ref, "order_ref"

    from app.eqms.modules.customer_profiles.models import Customer

    customer = s.get(Customer, order.customer_id) if order.customer_id else None
    candidates = [
        e
        for e in _open_entries(s)
        if entry_matches_customer(e, customer) and not _ref_contradicts(e, order)
    ]
    return _pick_confident(order, candidates)


def find_automatch_order_for_entry(s, entry: NREProjectEntry):
    """Mirror of find_automatch_entry_for_order, driven from the tracker row."""
    by_ref = find_unmatched_nre_order_by_ref(s, entry.order_ref)
    if by_ref is not None:
        return by_ref, "order_ref"

    candidates = [
        o
        for o in unmatched_nre_orders(s)
        if entry_matches_customer(entry, o.customer) and not _ref_contradicts(entry, o)
    ]
    if not candidates:
        return None, None
    if len(candidates) == 1:
        order = candidates[0]
        gap = _amount_gap(order, entry)
        tol = amount_tolerance(order.order_amount)
        if gap is not None and tol is not None and gap > tol:
            return None, None
        return order, "customer_unique"

    within = []
    for o in candidates:
        gap = _amount_gap(o, entry)
        tol = amount_tolerance(o.order_amount)
        if gap is not None and tol is not None and gap <= tol:
            within.append((gap, o))
    if len(within) != 1:
        return None, None
    return within[0][1], "customer_amount"


def unmatched_nre_orders(s) -> list[SalesOrder]:
    """NRE-typed, live, dashboard-eligible orders with no tracker entry yet."""
    rows = (
        s.query(SalesOrder)
        .outerjoin(NREProjectEntry, NREProjectEntry.sales_order_id == SalesOrder.id)
        .filter(
            SalesOrder.order_type == ORDER_TYPE_NRE_PROJECT,
            SalesOrder.status != "cancelled",
            NREProjectEntry.id.is_(None),
        )
        .order_by(SalesOrder.order_date.desc(), SalesOrder.order_number.desc())
        .all()
    )
    return [o for o in rows if is_nre_dashboard_order(o)]


def rank_orders_for_entry(entry: NREProjectEntry, orders: list[SalesOrder]) -> list[dict]:
    """Order the Match dropdown so the likely order is first.

    Returns one dict per order with a ``suggested`` flag and a short reason, so
    the operator can see why something is being proposed.
    """
    target_ref = normalize_order_number(entry.order_ref)
    ranked = []
    for o in orders:
        score = 0
        reasons = []
        if target_ref and normalize_order_number(o.order_number) == target_ref:
            score += 100
            reasons.append("order ref")
        if entry_matches_customer(entry, o.customer):
            score += 50
            reasons.append("customer")
        gap = _amount_gap(o, entry)
        tol = amount_tolerance(o.order_amount)
        if gap is not None and tol is not None and gap <= tol:
            score += 30
            reasons.append("amount")
        if entry.entry_date and o.order_date:
            days = abs((o.order_date - entry.entry_date).days)
            if days <= 45:
                score += 10
                reasons.append("date")
        ranked.append(
            {
                "order": o,
                # The customer alone is too weak to promote: a repeat client has
                # many past orders. Require a second signal.
                "suggested": score > 50,
                "score": score,
                "reason": ", ".join(reasons),
            }
        )
    ranked.sort(
        key=lambda r: (-r["score"], -(r["order"].order_date.toordinal()
                                      if r["order"].order_date else 0))
    )
    return ranked


def _amount_decision(order: SalesOrder, entry: NREProjectEntry) -> dict[str, Any]:
    """The sales order is authoritative; only fill an amount it does not have."""
    so_amt = order.order_amount
    tr_amt = entry.invoice_amount
    if so_amt is None and tr_amt is not None:
        order.order_amount = tr_amt
        return {
            "action": "copied_from_tracker",
            "order_amount": str(tr_amt),
            "tracker_amount": str(tr_amt),
        }
    return {
        "action": "kept_order_amount",
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
        entry, how = find_automatch_entry_for_order(s, order)
        if entry is None:
            return
        match_tracker_to_sales_order(
            s, entry=entry, order=order, user=user, how=f"auto_{how}"
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
        order, how = find_automatch_order_for_entry(s, entry)
        if order is None:
            return
        match_tracker_to_sales_order(
            s, entry=entry, order=order, user=user, how=f"auto_{how}"
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


SETTLED_STATUS = "Payment Received"


def is_settled(order: SalesOrder) -> bool:
    """Nothing left to chase: invoiced in full and paid."""
    return (order.nre_invoice_status or "").strip() == SETTLED_STATUS


def compute_nre_dashboard(s, *, start_date, end_date) -> dict[str, Any]:
    """NRE dashboard metrics for order_date in [start_date, end_date].

    Same rules as the NRE Projects page: ``nre_project`` type, not cancelled,
    Total Amount Invoiced uses ``nre_invoiced_amount()``.

    Orders dated before the range that are still unsettled come back as
    ``carried_orders``. They are listed so open work is not lost when the
    quarter rolls over, but they stay out of the metrics, which describe the
    selected range only.
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
    eligible = [
        o for o in typed if is_nre_dashboard_order(o) and o.customer_id is not None
    ]
    nre_ids = sorted({o.customer_id for o in eligible})
    nre_customers = s.query(Customer).filter(Customer.id.in_(nre_ids)).all() if nre_ids else []
    customers_by_id = {c.id: c for c in nre_customers}

    def in_range(o: SalesOrder) -> bool:
        return o.order_date is not None and start_date <= o.order_date <= end_date

    filtered_orders = sorted(
        (o for o in eligible if in_range(o)),
        key=lambda o: (o.order_date, o.order_number or ""),
        reverse=True,
    )
    outside = [o for o in eligible if not in_range(o)]
    orders_outside_range = len(outside)

    # Unsettled work from before the range, split by what it actually needs.
    # Lumping them together buries the few jobs that need an invoice raised
    # under every historical order still waiting on payment.
    carried_orders = sorted(
        (o for o in outside if not is_settled(o)),
        key=lambda o: (o.order_date or start_date, o.order_number or ""),
    )
    carried_to_invoice = [
        o for o in carried_orders
        if nre_remaining_to_invoice(o.nre_invoice_status, o.order_amount) > 0
    ]
    carried_awaiting_payment = [
        o for o in carried_orders
        if nre_remaining_to_invoice(o.nre_invoice_status, o.order_amount) <= 0
    ]

    # Tracker context for every order on screen, so the free-text status and
    # description the operator wrote stay visible after the entry is matched.
    on_screen = {o.id for o in filtered_orders} | {o.id for o in carried_orders}
    tracker_by_order: dict[int, NREProjectEntry] = {}
    if on_screen:
        for e in (
            s.query(NREProjectEntry)
            .filter(NREProjectEntry.sales_order_id.in_(on_screen))
            .all()
        ):
            tracker_by_order[e.sales_order_id] = e

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
        "carried_orders": carried_orders,
        "carried_to_invoice": carried_to_invoice,
        "carried_awaiting_payment": carried_awaiting_payment,
        "carried_awaiting_payment_total": sum(
            (Decimal(str(o.order_amount)) for o in carried_awaiting_payment
             if o.order_amount is not None),
            Decimal("0"),
        ),
        "carried_still_to_invoice": sum(
            (nre_remaining_to_invoice(o.nre_invoice_status, o.order_amount)
             for o in carried_orders),
            Decimal("0"),
        ),
        "tracker_by_order": tracker_by_order,
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
