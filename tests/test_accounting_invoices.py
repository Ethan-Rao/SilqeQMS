"""A fresh load of the accounting invoice CSV has to satisfy the order checks."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.accounting_invoices import load_accounting_invoices
from app.eqms.modules.rep_traceability.models import AccountingInvoice, AccountingInvoiceGroup, SalesOrder

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "SalesOrg" / "InvoiceResources" / "outputs" / "03_order_status.csv"

NO_INVOICE = {
    "0000445",
    "0000447",
    "0000448",
    "0000449",
    "0000450",
}


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


def test_fresh_load_matches_the_accounting_checks(app):
    if not CSV_PATH.exists():
        pytest.skip("Accounting CSV stays out of git. The check runs where the file is present.")

    with session_scope(app) as session:
        customer = Customer(company_key="ACCTTEST", facility_name="Accounting Test", customer_type="catheter")
        session.add(customer)
        session.flush()
        order_numbers = set()
        import csv

        with CSV_PATH.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row["order_number"]:
                    order_numbers.add(row["order_number"])
        for number in sorted(order_numbers):
            session.add(
                SalesOrder(
                    order_number=number,
                    order_date=date(2026, 1, 1),
                    customer_id=customer.id,
                    source="manual",
                    status="completed",
                    order_amount=Decimal("1.00"),
                )
            )
        session.flush()
        load_accounting_invoices(session, CSV_PATH)
        load_accounting_invoices(session, CSV_PATH)

        invoices = session.query(AccountingInvoice).all()
        numbers = [row.invoice_number for row in invoices]
        assert len(numbers) == 171
        assert len(set(numbers)) == 171
        assert sum((row.invoice_total or Decimal("0")) for row in invoices) == Decimal("213672.21")
        assert sum((row.open_balance or Decimal("0")) for row in invoices) == Decimal("32841.38")
        assert "0000462" not in numbers
        assert "0000463" not in numbers

        groups = {row.order_number: row for row in session.query(AccountingInvoiceGroup).all() if row.order_number}
        assert groups["0000429"].status == "Paid"
        paid_invoices = {row.invoice_number: row.payment for row in groups["0000429"].invoices}
        assert paid_invoices == {"0000453": "Paid"}

        assert groups["0000420"].status == "Open"
        open_invoices = {row.invoice_number: row.payment for row in groups["0000420"].invoices}
        assert open_invoices == {"0000442": "Paid", "0000456": "Open"}

        assert groups["0000385"].status == "Partly invoiced"
        assert groups["0000419"].status == "Partly invoiced"

        no_invoice = {number for number, group in groups.items() if group.status == "No Invoice"}
        assert no_invoice == NO_INVOICE

        invoice_0391 = session.query(AccountingInvoice).filter(AccountingInvoice.invoice_number == "0000391").one()
        assert invoice_0391.payment == "Paid"
        assert invoice_0391.invoice_total == Decimal("2120.00")
        assert invoice_0391.open_balance is None

        for order in session.query(SalesOrder).all():
            assert order.order_amount == Decimal("1.00")


def test_loader_skips_nih_orders_and_invoices(app, tmp_path):
    path = tmp_path / "nih.csv"
    path.write_text(
        "order_number,status,quote_history_order_total,invoice_number,invoice_date,invoice_total,payment,open_balance\n"
        "0000437,Open,7073.60,0000462,2026-11-02,7073.60,Open,7073.60\n"
        "0000446,No Invoice,13717.52,,,,,\n"
        ",No sales order,,0000463,2026-11-16,13717.52,Open,13717.52\n"
        "0000447,No Invoice,325.00,,,,,\n",
        encoding="utf-8",
    )
    with session_scope(app) as session:
        customer = Customer(company_key="NIHTEST", facility_name="Clinic", customer_type="catheter")
        session.add(customer)
        session.flush()
        session.add(
            SalesOrder(
                order_number="0000447",
                order_date=date(2026, 11, 17),
                customer_id=customer.id,
                source="manual",
                status="pending",
                order_amount=Decimal("325.00"),
            )
        )
        session.flush()
        load_accounting_invoices(session, path)
        numbers = [row.invoice_number for row in session.query(AccountingInvoice).all()]
        assert numbers == []
        groups = {row.order_number: row.status for row in session.query(AccountingInvoiceGroup).all()}
        assert groups == {"0000447": "No Invoice"}
