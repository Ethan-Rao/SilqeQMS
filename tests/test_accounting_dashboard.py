"""Accounting status on the sales dashboard and the NRE dashboard."""

from datetime import date
from decimal import Decimal

import pytest

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.accounting_display import accounting_for_page
from app.eqms.modules.rep_traceability.models import (
    AccountingInvoice,
    AccountingInvoiceGroup,
    SalesOrder,
)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for key in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(key, raising=False)
    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True
    return application


def _customer(session, name, key):
    customer = Customer(facility_name=name, company_key=key, customer_type="catheter")
    session.add(customer)
    session.flush()
    return customer


def _order(session, customer, number, day, amount, order_type):
    order = SalesOrder(
        order_number=number,
        order_date=day,
        customer_id=customer.id,
        source="manual",
        status="completed",
        order_amount=amount,
        order_type=order_type,
    )
    session.add(order)
    session.flush()
    return order


def _group(session, order, status, quote, invoices):
    group = AccountingInvoiceGroup(
        sales_order_id=order.id if order else None,
        order_number=order.order_number if order else None,
        status=status,
        quote_history_order_total=quote,
    )
    session.add(group)
    session.flush()
    for number, day, total, payment, balance in invoices:
        session.add(
            AccountingInvoice(
                group_id=group.id,
                invoice_number=number,
                invoice_date=day,
                invoice_total=total,
                payment=payment,
                open_balance=balance,
            )
        )
    session.flush()
    return group


def test_order_date_lists_the_order_and_leaves_the_invoice_out_of_the_total(app):
    with session_scope(app) as session:
        catheter = _customer(session, "Catheter Co", "cath-co")
        nre = _customer(session, "NRE Co", "nre-co")
        cath_order = _order(session, catheter, "C-1", date(2026, 3, 1), Decimal("100"), "cleartract_distribution")
        nre_order = _order(session, nre, "N-1", date(2026, 3, 2), Decimal("200"), "nre_project")
        _group(session, cath_order, "Paid", Decimal("100"), [("CINV", date(2026, 4, 1), Decimal("100"), "Paid", None)])
        _group(session, nre_order, "Paid", Decimal("200"), [("NINV", date(2026, 4, 2), Decimal("200"), "Paid", None)])
        window = dict(start=date(2026, 3, 1), end=date(2026, 3, 31))
        sales = accounting_for_page(session, page="catheter", **window)
        nre_page = accounting_for_page(session, page="nre", **window)
        assert [row["order_number"] for row in sales["orders"]] == ["C-1"]
        assert [row["order_number"] for row in nre_page["orders"]] == ["N-1"]
        assert sales["invoice_total"] == Decimal("0")
        assert nre_page["invoice_total"] == Decimal("0")


def test_invoice_date_is_in_the_total_and_the_order_is_not_listed(app):
    with session_scope(app) as session:
        customer = _customer(session, "Later Co", "later-co")
        order = _order(session, customer, "C-2", date(2026, 1, 15), Decimal("50"), "cleartract_distribution")
        _group(session, order, "Paid", Decimal("50"), [("CINV2", date(2026, 5, 1), Decimal("50"), "Paid", None)])
        sales = accounting_for_page(session, start=date(2026, 5, 1), end=date(2026, 5, 31), page="catheter")
        assert sales["orders"] == []
        assert sales["invoice_total"] == Decimal("50")


def test_no_invoice_order_is_listed_and_adds_nothing_to_the_total(app):
    with session_scope(app) as session:
        customer = _customer(session, "Open Co", "open-co")
        order = _order(session, customer, "C-3", date(2026, 6, 1), Decimal("80"), "cleartract_in_process")
        _group(session, order, "No Invoice", Decimal("80"), [])
        sales = accounting_for_page(session, start=date(2026, 6, 1), end=date(2026, 6, 30), page="catheter")
        assert [row["order_number"] for row in sales["orders"]] == ["C-3"]
        assert sales["orders"][0]["status"] == "No Invoice"
        assert sales["invoice_total"] == Decimal("0")
        assert sales["needs_invoice"][0]["order_number"] == "C-3"


def test_order_0000420_contributes_both_invoices_and_is_open(app):
    with session_scope(app) as session:
        customer = _customer(session, "Neptune", "neptune")
        order = _order(session, customer, "0000420", date(2026, 9, 28), Decimal("4830"), "nre_project")
        _group(
            session,
            order,
            "Open",
            Decimal("4830"),
            [
                ("0000442", date(2026, 10, 6), Decimal("2415.00"), "Paid", None),
                ("0000456", date(2026, 10, 29), Decimal("2415.00"), "Open", Decimal("2415.00")),
            ],
        )
        page = accounting_for_page(session, start=date(2026, 10, 1), end=date(2026, 10, 31), page="nre")
        assert page["invoice_total"] == Decimal("4830.00")
        assert page["orders"] == []
        listed = accounting_for_page(session, start=date(2026, 9, 1), end=date(2026, 10, 31), page="nre")
        match = next(row for row in listed["orders"] if row["order_number"] == "0000420")
        assert match["status"] == "Open"
        assert listed["invoice_total"] == Decimal("4830.00")


def test_catheter_invoice_stays_off_the_nre_total_and_0000305_stays_off_sales(app):
    with session_scope(app) as session:
        customer = _customer(session, "Sales Co", "sales-co")
        order = _order(session, customer, "C-4", date(2026, 2, 1), Decimal("10"), "cleartract_distribution")
        _group(session, order, "Paid", Decimal("10"), [("CATH", date(2026, 2, 2), Decimal("10"), "Paid", None)])
        group = AccountingInvoiceGroup(
            sales_order_id=None,
            order_number=None,
            status="No sales order",
            quote_history_order_total=None,
        )
        session.add(group)
        session.flush()
        session.add(
            AccountingInvoice(
                group_id=group.id,
                invoice_number="0000305",
                invoice_date=date(2026, 2, 3),
                invoice_total=Decimal("1890.00"),
                payment="Paid",
                open_balance=None,
            )
        )
        session.flush()
        window = dict(start=date(2026, 2, 1), end=date(2026, 2, 28))
        nre_page = accounting_for_page(session, page="nre", **window)
        sales = accounting_for_page(session, page="catheter", **window)
        assert nre_page["invoice_total"] == Decimal("1890.00")
        assert sales["invoice_total"] == Decimal("10")
        assert all(row["order_number"] != "0000305" for row in sales["orders"])
        assert nre_page["unlinked"][0]["status"] == "No sales order"
        assert nre_page["needs_invoice"] == []
