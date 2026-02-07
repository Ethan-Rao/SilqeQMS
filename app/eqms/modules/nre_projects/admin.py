from __future__ import annotations

from flask import abort, render_template

from app.eqms.db import db_session
from app.eqms.rbac import require_permission
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder
from app.eqms.modules.nre_projects import bp


@bp.get("/")
@require_permission("sales_orders.view")
def nre_projects_index():
    """
    NRE Projects dashboard.
    Customers with sales orders but no distributions.
    """
    s = db_session()

    customers_with_orders = (
        s.query(Customer.id)
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .distinct()
        .subquery()
    )

    customers_with_distributions = (
        s.query(Customer.id)
        .join(DistributionLogEntry, DistributionLogEntry.customer_id == Customer.id)
        .distinct()
        .subquery()
    )

    nre_customers = (
        s.query(Customer)
        .filter(Customer.id.in_(customers_with_orders))
        .filter(~Customer.id.in_(customers_with_distributions))
        .order_by(Customer.facility_name.asc())
        .all()
    )

    order_counts: dict[int, int] = {}
    for c in nre_customers:
        order_counts[c.id] = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()

    return render_template(
        "admin/nre_projects/index.html",
        nre_customers=nre_customers,
        order_counts=order_counts,
    )


@bp.get("/<int:customer_id>")
@require_permission("sales_orders.view")
def nre_customer_detail(customer_id: int):
    s = db_session()
    customer = s.query(Customer).filter(Customer.id == customer_id).one_or_none()
    if not customer:
        abort(404)

    orders = (
        s.query(SalesOrder)
        .filter(SalesOrder.customer_id == customer_id)
        .order_by(SalesOrder.order_date.desc())
        .all()
    )

    return render_template(
        "admin/nre_projects/detail.html",
        customer=customer,
        orders=orders,
    )
