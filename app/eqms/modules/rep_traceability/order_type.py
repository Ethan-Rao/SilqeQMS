"""Sales-order type classification — single source of truth for P4-01.

Stored values and display labels live only here. Callers must import these
constants; do not hardcode the four type strings elsewhere.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

ORDER_TYPE_CLEARTRACT_DISTRIBUTION = "cleartract_distribution"
ORDER_TYPE_CLEARTRACT_IN_PROCESS = "cleartract_in_process"
ORDER_TYPE_CLEARTRACT_DELIVERY = "cleartract_delivery"
ORDER_TYPE_NRE_PROJECT = "nre_project"

ORDER_TYPE_LABELS: dict[str, str] = {
    ORDER_TYPE_CLEARTRACT_DISTRIBUTION: "ClearTract Distribution",
    ORDER_TYPE_CLEARTRACT_IN_PROCESS: "ClearTract In Process Order",
    ORDER_TYPE_CLEARTRACT_DELIVERY: "ClearTract Delivery",
    ORDER_TYPE_NRE_PROJECT: "NRE Project",
}

ORDER_TYPE_CHOICES: list[tuple[str, str]] = [
    (ORDER_TYPE_CLEARTRACT_DISTRIBUTION, ORDER_TYPE_LABELS[ORDER_TYPE_CLEARTRACT_DISTRIBUTION]),
    (ORDER_TYPE_CLEARTRACT_IN_PROCESS, ORDER_TYPE_LABELS[ORDER_TYPE_CLEARTRACT_IN_PROCESS]),
    (ORDER_TYPE_CLEARTRACT_DELIVERY, ORDER_TYPE_LABELS[ORDER_TYPE_CLEARTRACT_DELIVERY]),
    (ORDER_TYPE_NRE_PROJECT, ORDER_TYPE_LABELS[ORDER_TYPE_NRE_PROJECT]),
]

VALID_ORDER_TYPES = frozenset(ORDER_TYPE_LABELS)


def classify_order_type(s, order) -> tuple[str, bool]:
    """Return (order_type, needs_review) from linked distribution / line evidence.

    Rule order:
      1. any linked distribution with source == shipstation -> cleartract_distribution
      2. any other linked distribution -> cleartract_delivery
      3. no distribution but at least one catheter-SKU line -> cleartract_in_process
      4. otherwise -> nre_project (needs_review=True)
    """
    from app.eqms.modules.rep_traceability.models import DistributionLogEntry
    from app.eqms.modules.rep_traceability.service import sales_order_has_catheter_sku

    dists = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.sales_order_id == order.id)
        .all()
    )
    if any(d.source == "shipstation" for d in dists):
        return ORDER_TYPE_CLEARTRACT_DISTRIBUTION, False
    if dists:
        return ORDER_TYPE_CLEARTRACT_DELIVERY, False
    if sales_order_has_catheter_sku(order):
        return ORDER_TYPE_CLEARTRACT_IN_PROCESS, False
    return ORDER_TYPE_NRE_PROJECT, True


def apply_order_type(s, order, *, user=None) -> bool:
    """Recompute order_type unless the operator set it manually.

    Returns True if order_type or order_type_needs_review changed.
    Emits sales_order.order_type_auto only when changing a previously set type
    (not on the initial assignment for a brand-new order).
    """
    if getattr(order, "order_type_is_manual", False):
        return False

    new_type, needs_review = classify_order_type(s, order)
    before_type = order.order_type
    before_review = bool(getattr(order, "order_type_needs_review", False))

    changed = (before_type != new_type) or (before_review != needs_review)
    if not changed:
        return False

    order.order_type = new_type
    order.order_type_needs_review = needs_review

    # Initial assignment on a new order is not audited (noise).
    if before_type is not None:
        from app.eqms.audit import record_event

        record_event(
            s,
            actor=user,
            action="sales_order.order_type_auto",
            entity_type="SalesOrder",
            entity_id=str(order.id),
            metadata={
                "before": before_type,
                "after": new_type,
                "needs_review": needs_review,
            },
        )
    return True


def set_order_type_manual(s, order, new_type: str, *, user) -> None:
    """Operator override: lock the type and clear the review flag."""
    if new_type not in VALID_ORDER_TYPES:
        raise ValueError(f"Invalid order_type: {new_type!r}")

    before = order.order_type
    order.order_type = new_type
    order.order_type_is_manual = True
    order.order_type_needs_review = False

    from app.eqms.audit import record_event

    record_event(
        s,
        actor=user,
        action="sales_order.order_type_set",
        entity_type="SalesOrder",
        entity_id=str(order.id),
        metadata={"before": before, "after": new_type},
    )


def safe_apply_order_type(s, order_or_id, *, user=None) -> None:
    """Call apply_order_type; log and continue on any failure."""
    if order_or_id is None:
        return
    try:
        from app.eqms.modules.rep_traceability.models import SalesOrder

        if isinstance(order_or_id, int):
            order = s.get(SalesOrder, order_or_id)
        else:
            order = order_or_id
        if order is None:
            return
        apply_order_type(s, order, user=user)
    except Exception:
        logger.exception(
            "apply_order_type failed for order=%s",
            getattr(order_or_id, "id", order_or_id),
        )
