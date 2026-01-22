from __future__ import annotations

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.eqms.db import db_session
from app.eqms.models import User
from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
from app.eqms.modules.customer_profiles.service import (
    add_customer_note,
    create_customer,
    delete_customer_note,
    edit_customer_note,
    get_customer_by_id,
    validate_customer_payload,
    update_customer,
)
from app.eqms.modules.rep_traceability.models import DistributionLogEntry
from app.eqms.rbac import require_permission

bp = Blueprint("customer_profiles", __name__)


def _current_user() -> User:
    u = getattr(g, "current_user", None)
    if not u:
        raise RuntimeError("No current user")
    return u


@bp.get("/customers")
@require_permission("customers.view")
def customers_list():
    from sqlalchemy import func, extract
    from datetime import date
    
    s = db_session()
    q = (request.args.get("q") or "").strip()
    state = (request.args.get("state") or "").strip()
    rep_id = (request.args.get("rep_id") or "").strip()
    year = (request.args.get("year") or "").strip()
    cust_type = (request.args.get("type") or "").strip()
    page = int(request.args.get("page") or "1")
    if page < 1:
        page = 1
    per_page = 50

    query = s.query(Customer)
    if q:
        like = f"%{q}%"
        query = query.filter((Customer.facility_name.ilike(like)) | (Customer.company_key.ilike(like)) | (Customer.city.ilike(like)))
    if state:
        query = query.filter(Customer.state == state)
    if rep_id:
        try:
            query = query.filter(Customer.primary_rep_id == int(rep_id))
        except Exception:
            flash("rep_id must be numeric", "danger")

    # Get customer IDs with their order stats (for year filter and type filter)
    customer_stats: dict[int, dict] = {}
    dist_query = s.query(
        DistributionLogEntry.customer_id,
        func.count(func.distinct(DistributionLogEntry.order_number)).label("order_count"),
        func.sum(DistributionLogEntry.quantity).label("total_units"),
        func.min(DistributionLogEntry.ship_date).label("first_order"),
        func.max(DistributionLogEntry.ship_date).label("last_order"),
    ).filter(DistributionLogEntry.customer_id.isnot(None)).group_by(DistributionLogEntry.customer_id)
    
    for row in dist_query.all():
        customer_stats[row.customer_id] = {
            "order_count": row.order_count or 0,
            "total_units": int(row.total_units or 0),
            "first_order": row.first_order,
            "last_order": row.last_order,
        }

    # Note counts for customer list indicator
    note_counts: dict[int, int] = {}
    note_rows = (
        s.query(CustomerNote.customer_id, func.count(CustomerNote.id))
        .group_by(CustomerNote.customer_id)
        .all()
    )
    note_counts = {int(cid): int(cnt or 0) for cid, cnt in note_rows}

    # Year filter: only customers with ANY order in that specific year
    if year:
        try:
            year_int = int(year)
            # Use subquery to find customers with orders in that year (exact match, not >=)
            # This is Option B from the spec: "has orders in that year" semantics
            from sqlalchemy import and_
            year_start = f"{year_int}-01-01"
            year_end = f"{year_int}-12-31"
            customer_ids_for_year = set(
                row[0] for row in s.query(DistributionLogEntry.customer_id)
                .filter(
                    DistributionLogEntry.customer_id.isnot(None),
                    DistributionLogEntry.ship_date >= year_start,
                    DistributionLogEntry.ship_date <= year_end,
                )
                .distinct()
                .all()
            )
            if customer_ids_for_year:
                query = query.filter(Customer.id.in_(customer_ids_for_year))
            else:
                # No customers for this year, return empty
                query = query.filter(Customer.id == -1)
        except Exception:
            pass

    # Type filter: first-time (1 order) vs repeat (2+ orders)
    if cust_type == "first":
        first_time_ids = {cid for cid, stats in customer_stats.items() if stats["order_count"] == 1}
        if first_time_ids:
            query = query.filter(Customer.id.in_(first_time_ids))
        else:
            query = query.filter(Customer.id == -1)
    elif cust_type == "repeat":
        repeat_ids = {cid for cid, stats in customer_stats.items() if stats["order_count"] >= 2}
        if repeat_ids:
            query = query.filter(Customer.id.in_(repeat_ids))
        else:
            query = query.filter(Customer.id == -1)

    total = query.count()
    
    # Sort by most recent order date (customers with orders first, then alphabetically)
    # Create subquery for max ship_date per customer
    last_order_subq = (
        s.query(
            DistributionLogEntry.customer_id,
            func.max(DistributionLogEntry.ship_date).label("last_order_date")
        )
        .filter(DistributionLogEntry.customer_id.isnot(None))
        .group_by(DistributionLogEntry.customer_id)
        .subquery()
    )
    
    # Join and sort by last_order_date DESC NULLS LAST, then facility_name ASC
    customers = (
        query
        .outerjoin(last_order_subq, Customer.id == last_order_subq.c.customer_id)
        .order_by(
            last_order_subq.c.last_order_date.desc().nullslast(),
            Customer.facility_name.asc(),
            Customer.id.asc()
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    has_prev = page > 1
    has_next = page * per_page < total

    # Get unique states for filter dropdown
    all_states = s.query(Customer.state).filter(Customer.state.isnot(None), Customer.state != "").distinct().order_by(Customer.state.asc()).all()
    state_options = [row[0] for row in all_states]

    # Rep options for filter dropdown
    reps = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()

    return render_template(
        "admin/customers/list.html",
        customers=customers,
        customer_stats=customer_stats,
        note_counts=note_counts,
        q=q,
        state=state,
        state_options=state_options,
        reps=reps,
        rep_id=rep_id,
        year=year,
        cust_type=cust_type,
        page=page,
        total=total,
        has_prev=has_prev,
        has_next=has_next,
    )


@bp.get("/customers/new")
@require_permission("customers.create")
def customers_new_get():
    s = db_session()
    reps = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()
    return render_template("admin/customers/detail.html", customer=None, notes=[], orders=[], reps=reps)


@bp.post("/customers/new")
@require_permission("customers.create")
def customers_new_post():
    s = db_session()
    u = _current_user()
    payload = {
        "facility_name": request.form.get("facility_name"),
        "address1": request.form.get("address1"),
        "address2": request.form.get("address2"),
        "city": request.form.get("city"),
        "state": request.form.get("state"),
        "zip": request.form.get("zip"),
        "contact_name": request.form.get("contact_name"),
        "contact_phone": request.form.get("contact_phone"),
        "contact_email": request.form.get("contact_email"),
        "primary_rep_id": request.form.get("primary_rep_id"),
    }
    errs = validate_customer_payload(payload)
    if errs:
        flash("; ".join([f"{e.field}: {e.message}" for e in errs]), "danger")
        return redirect(url_for("customer_profiles.customers_new_get"))
    # Validate primary rep exists and is active
    if (payload.get("primary_rep_id") or "").strip():
        rep = s.query(User).filter(User.id == int(payload["primary_rep_id"]), User.is_active.is_(True)).one_or_none()
        if not rep:
            flash("Primary rep not found or inactive.", "danger")
            return redirect(url_for("customer_profiles.customers_new_get"))
    try:
        c = create_customer(s, payload, user=u)
        s.commit()
        flash("Customer saved.", "success")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))
    except Exception as e:
        s.rollback()
        flash(str(e), "danger")
        return redirect(url_for("customer_profiles.customers_new_get"))


@bp.get("/customers/<int:customer_id>")
@require_permission("customers.view")
def customer_detail(customer_id: int):
    from sqlalchemy import func
    from collections import defaultdict
    
    s = db_session()
    c = get_customer_by_id(s, customer_id)
    if not c:
        flash("Customer not found.", "danger")
        return redirect(url_for("customer_profiles.customers_list"))
    notes = s.query(CustomerNote).filter(CustomerNote.customer_id == c.id).order_by(CustomerNote.created_at.desc()).all()
    
    # Get all distributions for this customer (no limit for tabbed view)
    all_distributions = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.customer_id == c.id)
        .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
        .all()
    )
    
    # Compute stats for overview tab
    total_orders = len({e.order_number for e in all_distributions if e.order_number})
    total_units = sum(int(e.quantity or 0) for e in all_distributions)
    first_order = min((e.ship_date for e in all_distributions), default=None)
    last_order = max((e.ship_date for e in all_distributions), default=None)
    
    # SKU breakdown
    sku_totals: dict[str, int] = {}
    for e in all_distributions:
        sku_totals[e.sku] = sku_totals.get(e.sku, 0) + int(e.quantity or 0)
    sku_breakdown = [{"sku": sku, "units": units} for sku, units in sorted(sku_totals.items(), key=lambda kv: kv[1], reverse=True)]
    
    # Group orders by (order_number, ship_date) for Orders tab (Fix 8)
    order_groups: dict[tuple, dict] = defaultdict(lambda: {
        "order_number": None,
        "ship_date": None,
        "source": None,
        "items": [],
        "total_qty": 0,
        "lots": set(),
    })
    for e in all_distributions:
        key = (e.order_number or f"entry-{e.id}", e.ship_date)
        grp = order_groups[key]
        grp["order_number"] = e.order_number
        grp["ship_date"] = e.ship_date
        grp["source"] = e.source
        grp["items"].append({
            "sku": e.sku,
            "lot": e.lot_number,
            "qty": int(e.quantity or 0),
        })
        grp["total_qty"] += int(e.quantity or 0)
        if e.lot_number:
            grp["lots"].add(e.lot_number)
    
    # Convert to list sorted by ship_date desc
    grouped_orders = sorted(
        [
            {
                "order_number": v["order_number"],
                "ship_date": v["ship_date"],
                "source": v["source"],
                "items": v["items"],
                "total_qty": v["total_qty"],
                "lots": ", ".join(sorted(v["lots"])),
            }
            for v in order_groups.values()
        ],
        key=lambda x: (x["ship_date"] or "", x["order_number"] or ""),
        reverse=True,
    )
    
    # Customer stats dict
    customer_stats = {
        "total_orders": total_orders,
        "total_units": total_units,
        "first_order": first_order,
        "last_order": last_order,
        "sku_breakdown": sku_breakdown,
    }
    
    # Default tab
    tab = request.args.get("tab", "overview")
    
    reps = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()

    return render_template(
        "admin/customers/detail.html",
        customer=c,
        notes=notes,
        orders=grouped_orders,  # Fix 8: grouped orders for Orders tab
        distributions=all_distributions,  # Fix 7: raw distributions for Distributions tab
        customer_stats=customer_stats,
        tab=tab,
        reps=reps,
    )


@bp.post("/customers/<int:customer_id>")
@require_permission("customers.edit")
def customer_update_post(customer_id: int):
    s = db_session()
    u = _current_user()
    c = get_customer_by_id(s, customer_id)
    if not c:
        flash("Customer not found.", "danger")
        return redirect(url_for("customer_profiles.customers_list"))

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for change is required.", "danger")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))

    payload = {
        "facility_name": request.form.get("facility_name"),
        "address1": request.form.get("address1"),
        "address2": request.form.get("address2"),
        "city": request.form.get("city"),
        "state": request.form.get("state"),
        "zip": request.form.get("zip"),
        "contact_name": request.form.get("contact_name"),
        "contact_phone": request.form.get("contact_phone"),
        "contact_email": request.form.get("contact_email"),
        "primary_rep_id": request.form.get("primary_rep_id"),
    }
    errs = validate_customer_payload(payload)
    if errs:
        flash("; ".join([f"{e.field}: {e.message}" for e in errs]), "danger")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))
    # Validate primary rep exists and is active
    if (payload.get("primary_rep_id") or "").strip():
        rep = s.query(User).filter(User.id == int(payload["primary_rep_id"]), User.is_active.is_(True)).one_or_none()
        if not rep:
            flash("Primary rep not found or inactive.", "danger")
            return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))

    try:
        update_customer(s, c, payload, user=u, reason=reason)
        s.commit()
        flash("Customer updated.", "success")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))
    except Exception as e:
        s.rollback()
        flash(str(e), "danger")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))


@bp.post("/customers/<int:customer_id>/notes")
@require_permission("customers.notes")
def customer_note_add(customer_id: int):
    s = db_session()
    u = _current_user()
    c = get_customer_by_id(s, customer_id)
    if not c:
        flash("Customer not found.", "danger")
        return redirect(url_for("customer_profiles.customers_list"))
    try:
        add_customer_note(
            s,
            c,
            note_text=request.form.get("note_text") or "",
            note_date=request.form.get("note_date"),
            user=u,
        )
        s.commit()
        flash("Note added.", "success")
    except Exception as e:
        s.rollback()
        flash(str(e), "danger")
    return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))


@bp.post("/customers/<int:customer_id>/notes/<int:note_id>/edit")
@require_permission("customers.notes")
def customer_note_edit(customer_id: int, note_id: int):
    s = db_session()
    u = _current_user()
    note = s.query(CustomerNote).filter(CustomerNote.id == note_id, CustomerNote.customer_id == customer_id).one_or_none()
    if not note:
        flash("Note not found.", "danger")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=customer_id))
    try:
        edit_customer_note(s, note, note_text=request.form.get("note_text") or "", user=u)
        s.commit()
        flash("Note updated.", "success")
    except Exception as e:
        s.rollback()
        flash(str(e), "danger")
    return redirect(url_for("customer_profiles.customer_detail", customer_id=customer_id))


@bp.post("/customers/<int:customer_id>/notes/<int:note_id>/delete")
@require_permission("customers.notes")
def customer_note_delete(customer_id: int, note_id: int):
    s = db_session()
    u = _current_user()
    note = s.query(CustomerNote).filter(CustomerNote.id == note_id, CustomerNote.customer_id == customer_id).one_or_none()
    if not note:
        flash("Note not found.", "danger")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=customer_id))
    try:
        delete_customer_note(s, note, user=u)
        s.commit()
        flash("Note deleted.", "success")
    except Exception as e:
        s.rollback()
        flash(str(e), "danger")
    return redirect(url_for("customer_profiles.customer_detail", customer_id=customer_id))


# ============================================================================
# Customer Merge Routes
# ============================================================================

@bp.get("/customers/merge-candidates")
@require_permission("customers.edit")
def merge_candidates():
    """List potential duplicate customers for review."""
    from app.eqms.modules.customer_profiles.service import find_merge_candidates
    
    s = db_session()
    candidates = find_merge_candidates(s, limit=50)
    
    return render_template(
        "admin/customers/merge_candidates.html",
        candidates=candidates,
    )


@bp.get("/customers/merge")
@require_permission("customers.edit")
def merge_get():
    """Show merge form for two specific customers."""
    s = db_session()
    
    c1_id = request.args.get("c1")
    c2_id = request.args.get("c2")
    
    if not c1_id or not c2_id:
        flash("Two customer IDs required for merge.", "danger")
        return redirect(url_for("customer_profiles.merge_candidates"))
    
    try:
        c1 = s.query(Customer).filter(Customer.id == int(c1_id)).one()
        c2 = s.query(Customer).filter(Customer.id == int(c2_id)).one()
    except Exception:
        flash("One or both customers not found.", "danger")
        return redirect(url_for("customer_profiles.merge_candidates"))
    
    # Get distribution counts for each
    c1_dist_count = s.query(DistributionLogEntry).filter(DistributionLogEntry.customer_id == c1.id).count()
    c2_dist_count = s.query(DistributionLogEntry).filter(DistributionLogEntry.customer_id == c2.id).count()
    
    return render_template(
        "admin/customers/merge.html",
        customer1=c1,
        customer2=c2,
        c1_dist_count=c1_dist_count,
        c2_dist_count=c2_dist_count,
    )


@bp.post("/customers/merge")
@require_permission("customers.edit")
def merge_post():
    """Execute the merge of two customers."""
    from app.eqms.modules.customer_profiles.service import merge_customers
    
    s = db_session()
    u = _current_user()
    
    master_id = request.form.get("master_id")
    duplicate_id = request.form.get("duplicate_id")
    
    if not master_id or not duplicate_id:
        flash("Both master and duplicate IDs are required.", "danger")
        return redirect(url_for("customer_profiles.merge_candidates"))
    
    try:
        master_id = int(master_id)
        duplicate_id = int(duplicate_id)
    except ValueError:
        flash("Invalid customer IDs.", "danger")
        return redirect(url_for("customer_profiles.merge_candidates"))
    
    if master_id == duplicate_id:
        flash("Cannot merge a customer with itself.", "danger")
        return redirect(url_for("customer_profiles.merge_candidates"))
    
    try:
        master = merge_customers(s, master_id=master_id, duplicate_id=duplicate_id, user=u)
        s.commit()
        flash(f"Customers merged successfully. Master: {master.facility_name}", "success")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=master_id))
    except Exception as e:
        s.rollback()
        flash(f"Merge failed: {e}", "danger")
        return redirect(url_for("customer_profiles.merge_candidates"))

