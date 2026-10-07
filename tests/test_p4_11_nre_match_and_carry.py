"""NRE tracker matching on customer + amount, and dashboard carry-forward.

Tracker rows are written before the sales order exists, so Project/Order Ref is
normally blank and the amount is an estimate. These cover the matcher that
replaces order-number-only matching, and the rule that keeps unsettled work on
the dashboard after the quarter rolls over.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.nre_projects.models import NREProjectEntry
from app.eqms.modules.nre_projects.service import (
    compute_nre_dashboard,
    find_automatch_entry_for_order,
    names_refer_to_same_company,
    rank_orders_for_entry,
    safe_auto_match_order,
    unmatched_nre_orders,
)
from app.eqms.modules.rep_traceability.models import SalesOrder
from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_NRE_PROJECT

PW = "pw"
PERMS = ["admin.view", "sales_orders.view", "sales_orders.edit", "customers.view"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path / "storage"))
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID",
              "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        perms = {k: Permission(key=k, name=k) for k in PERMS}
        role = Role(key="admin", name="Administrator")
        role.permissions.extend(perms.values())
        u = User(
            email="admin@silq.tech",
            display_name="Admin",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        u.roles.append(role)
        s.add_all(list(perms.values()) + [role, u])

    return application


def _customer(s, name: str) -> Customer:
    c = Customer(facility_name=name, company_key=name.lower(), customer_type="nre")
    s.add(c)
    s.flush()
    return c


def _order(s, customer, *, number, amount, order_date=date(2026, 9, 28),
           nre_status="Pending Invoice") -> SalesOrder:
    so = SalesOrder(
        order_number=number,
        order_date=order_date,
        customer_id=customer.id,
        source="pdf_import",
        status="completed",
        order_type=ORDER_TYPE_NRE_PROJECT,
        order_amount=Decimal(amount) if amount is not None else None,
        nre_invoice_status=nre_status,
    )
    s.add(so)
    s.flush()
    return so


def _entry(s, *, customer_name, amount, description="job", order_ref=None,
           entry_date=date(2026, 9, 4), invoice_status="Quote Under Review"):
    e = NREProjectEntry(
        entry_date=entry_date,
        customer_name=customer_name,
        order_ref=order_ref,
        description=description,
        invoice_amount=Decimal(amount) if amount is not None else None,
        invoice_status=invoice_status,
    )
    s.add(e)
    s.flush()
    return e


# ── company-name comparison ──────────────────────────────────────────────────

@pytest.mark.parametrize(
    "a,b,expected",
    [
        ("Neptune", "Neptune Medical, Inc.", True),
        ("Fearsome", "Fearsome Limited", True),
        ("Advanced Bionics Gmbh", "Advanced Bionics GmbH", True),
        ("Aspero Medical Inc.", "Aspero Medical Inc.", True),
        ("Aspero Medical", "Aspirus Urology Wausau", False),
        ("Neptune", "Neptunia Devices", False),
        ("", "Neptune", False),
        (None, None, False),
    ],
)
def test_company_name_comparison(a, b, expected):
    assert names_refer_to_same_company(a, b) is expected


# ── auto-match ───────────────────────────────────────────────────────────────

def test_matches_on_customer_when_estimate_is_slightly_off(app):
    """The Neptune case: tracker says $4,880, the order totals $4,830."""
    with session_scope(app) as s:
        cust = _customer(s, "Neptune")
        entry = _entry(s, customer_name="Neptune", amount="4880.00",
                       description="PMMA Coupons")
        order = _order(s, cust, number="0000420", amount="4830.00")

        found, how = find_automatch_entry_for_order(s, order)
        assert found is not None and found.id == entry.id
        assert how == "customer_unique"


def test_no_match_when_amount_is_far_from_the_order(app):
    with session_scope(app) as s:
        cust = _customer(s, "Neptune")
        _entry(s, customer_name="Neptune", amount="19000.00")
        order = _order(s, cust, number="0000420", amount="4830.00")

        found, how = find_automatch_entry_for_order(s, order)
        assert found is None and how is None


def test_amount_separates_two_entries_for_one_customer(app):
    """Advanced Bionics has an open quote and a live job; only one fits."""
    with session_scope(app) as s:
        cust = _customer(s, "Advanced Bionics Gmbh")
        live = _entry(s, customer_name="Advanced Bionics Gmbh", amount="4962.00",
                      description="Electrochemical Testing II")
        _entry(s, customer_name="Advanced Bionics Gmbh", amount="4640.00",
               description="10 SlimJ Devices")
        order = _order(s, cust, number="0000400", amount="4982.50")

        found, how = find_automatch_entry_for_order(s, order)
        assert found is not None and found.id == live.id
        assert how == "customer_amount"


def test_refuses_when_two_entries_are_both_plausible(app):
    with session_scope(app) as s:
        cust = _customer(s, "Fearsome Limited")
        _entry(s, customer_name="Fearsome", amount="7570.00")
        _entry(s, customer_name="Fearsome", amount="7580.00")
        order = _order(s, cust, number="0000419", amount="7570.00")

        found, how = find_automatch_entry_for_order(s, order)
        assert found is None and how is None


def test_order_ref_still_wins_over_customer(app):
    with session_scope(app) as s:
        cust = _customer(s, "Neptune")
        by_ref = _entry(s, customer_name="Someone Else", amount="1.00",
                        order_ref="0000420")
        _entry(s, customer_name="Neptune", amount="4830.00")
        order = _order(s, cust, number="0000420", amount="4830.00")

        found, how = find_automatch_entry_for_order(s, order)
        assert found is not None and found.id == by_ref.id
        assert how == "order_ref"


def test_other_customers_entries_are_never_matched(app):
    with session_scope(app) as s:
        cust = _customer(s, "Neptune")
        _customer(s, "Mayo Clinic")
        _entry(s, customer_name="Mayo Clinic", amount="4830.00")
        order = _order(s, cust, number="0000420", amount="4830.00")

        found, _ = find_automatch_entry_for_order(s, order)
        assert found is None


def test_auto_match_on_upload_keeps_the_order_amount(app):
    """The sales order is authoritative; the tracker estimate must not win."""
    with session_scope(app) as s:
        cust = _customer(s, "Neptune")
        entry = _entry(s, customer_name="Neptune", amount="4880.00")
        order = _order(s, cust, number="0000420", amount="4830.00")

        safe_auto_match_order(s, order)
        s.flush()

        assert entry.sales_order_id == order.id
        assert order.order_amount == Decimal("4830.00")


def test_match_fills_an_amount_the_order_is_missing(app):
    with session_scope(app) as s:
        cust = _customer(s, "Neptune")
        _entry(s, customer_name="Neptune", amount="4880.00")
        order = _order(s, cust, number="0000420", amount=None)

        safe_auto_match_order(s, order)
        s.flush()
        assert order.order_amount == Decimal("4880.00")


# ── dropdown ranking ─────────────────────────────────────────────────────────

def test_matching_order_is_suggested_first(app):
    with session_scope(app) as s:
        neptune = _customer(s, "Neptune")
        other = _customer(s, "Mayo Clinic")
        _order(s, other, number="0000401", amount="8200.00")
        wanted = _order(s, neptune, number="0000420", amount="4830.00")
        entry = _entry(s, customer_name="Neptune", amount="4880.00")

        ranked = rank_orders_for_entry(entry, unmatched_nre_orders(s))
        assert ranked[0]["order"].id == wanted.id
        assert ranked[0]["suggested"] is True
        assert "customer" in ranked[0]["reason"]
        assert ranked[-1]["suggested"] is False


# ── dashboard carry-forward ──────────────────────────────────────────────────

def test_unsettled_earlier_order_is_carried_into_the_quarter(app):
    """The Abryx case: a Q3 order at 50% invoiced must stay visible in Q4."""
    with session_scope(app) as s:
        cust = _customer(s, "Abryx, Inc.")
        _order(s, cust, number="0000385", amount="7590.00",
               order_date=date(2026, 8, 11), nre_status="50% Invoiced")
        in_range = _order(s, cust, number="0000430", amount="1000.00",
                          order_date=date(2026, 10, 5))

        dash = compute_nre_dashboard(
            s, start_date=date(2026, 10, 1), end_date=date(2026, 12, 31)
        )
        assert [o.id for o in dash["orders"]] == [in_range.id]
        assert [o.order_number for o in dash["carried_to_invoice"]] == ["0000385"]
        # Carried work is listed, not folded into the quarter's totals.
        assert dash["project_count"] == 1
        assert dash["still_to_invoice"] == Decimal("1000.00")
        assert dash["carried_still_to_invoice"] == Decimal("3795.00")


def test_paid_earlier_orders_are_not_carried(app):
    with session_scope(app) as s:
        cust = _customer(s, "Abryx, Inc.")
        _order(s, cust, number="0000370", amount="2810.00",
               order_date=date(2026, 7, 22), nre_status="Payment Received")

        dash = compute_nre_dashboard(
            s, start_date=date(2026, 10, 1), end_date=date(2026, 12, 31)
        )
        assert dash["carried_orders"] == []


def test_fully_invoiced_but_unpaid_is_carried_separately(app):
    """Awaiting payment is grouped apart so it cannot bury work needing an invoice."""
    with session_scope(app) as s:
        cust = _customer(s, "Abryx, Inc.")
        _order(s, cust, number="0000378", amount="4743.30",
               order_date=date(2026, 8, 5), nre_status="100% Invoiced")
        _order(s, cust, number="0000385", amount="7590.00",
               order_date=date(2026, 8, 11), nre_status="50% Invoiced")

        dash = compute_nre_dashboard(
            s, start_date=date(2026, 10, 1), end_date=date(2026, 12, 31)
        )
        assert [o.order_number for o in dash["carried_to_invoice"]] == ["0000385"]
        assert [o.order_number for o in dash["carried_awaiting_payment"]] == ["0000378"]
        assert dash["carried_awaiting_payment_total"] == Decimal("4743.30")
        assert dash["carried_still_to_invoice"] == Decimal("3795.00")


def test_tracker_context_is_available_for_rows_on_screen(app):
    with session_scope(app) as s:
        cust = _customer(s, "Neptune")
        order = _order(s, cust, number="0000420", amount="4830.00",
                       order_date=date(2026, 10, 2))
        e = _entry(s, customer_name="Neptune", amount="4880.00",
                   description="PMMA Coupons", invoice_status="50% Invoiced")
        e.sales_order_id = order.id
        s.flush()

        dash = compute_nre_dashboard(
            s, start_date=date(2026, 10, 1), end_date=date(2026, 12, 31)
        )
        tracked = dash["tracker_by_order"][order.id]
        assert tracked.description == "PMMA Coupons"
        assert tracked.invoice_status == "50% Invoiced"
