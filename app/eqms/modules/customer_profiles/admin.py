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
    s = db_session()
    q = (request.args.get("q") or "").strip()
    state = (request.args.get("state") or "").strip()
    rep_id = (request.args.get("rep_id") or "").strip()
    page = int(request.args.get("page") or "1")
    if page < 1:
        page = 1
    per_page = 50

    query = s.query(Customer)
    if q:
        like = f"%{q}%"
        query = query.filter((Customer.facility_name.like(like)) | (Customer.company_key.like(like)))
    if state:
        query = query.filter(Customer.state == state)
    if rep_id:
        try:
            query = query.filter(Customer.primary_rep_id == int(rep_id))
        except Exception:
            flash("rep_id must be numeric", "danger")

    total = query.count()
    customers = (
        query.order_by(Customer.facility_name.asc(), Customer.id.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    has_prev = page > 1
    has_next = page * per_page < total
    return render_template(
        "admin/customers/list.html",
        customers=customers,
        q=q,
        state=state,
        rep_id=rep_id,
        page=page,
        total=total,
        has_prev=has_prev,
        has_next=has_next,
    )


@bp.get("/customers/new")
@require_permission("customers.create")
def customers_new_get():
    return render_template("admin/customers/detail.html", customer=None, notes=[], orders=[])


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
    c = create_customer(s, payload, user=u)
    flash("Customer saved.", "success")
    return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))


@bp.get("/customers/<int:customer_id>")
@require_permission("customers.view")
def customer_detail(customer_id: int):
    s = db_session()
    c = get_customer_by_id(s, customer_id)
    if not c:
        flash("Customer not found.", "danger")
        return redirect(url_for("customer_profiles.customers_list"))
    notes = s.query(CustomerNote).filter(CustomerNote.customer_id == c.id).order_by(CustomerNote.created_at.desc()).all()
    orders = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.customer_id == c.id)
        .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
        .limit(25)
        .all()
    )
    return render_template("admin/customers/detail.html", customer=c, notes=notes, orders=orders)


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

    update_customer(s, c, payload, user=u, reason=reason)
    flash("Customer updated.", "success")
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
        flash("Note added.", "success")
    except Exception as e:
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
        flash("Note updated.", "success")
    except Exception as e:
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
    delete_customer_note(s, note, user=u)
    flash("Note deleted.", "success")
    return redirect(url_for("customer_profiles.customer_detail", customer_id=customer_id))

