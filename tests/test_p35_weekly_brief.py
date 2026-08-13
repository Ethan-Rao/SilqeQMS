"""
Prompt 35 — Weekly Brief email tool.

Covers:
- GET /admin/reports/weekly-brief renders the form for admins (200) and is
  blocked for read-only staff (403).
- POST with empty recipients → error flash, no send attempt.
- POST with recipients but no RESEND_API_KEY → meaningful error, no crash.
- Reports index links to the tool.
"""
import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User

PW = "pw"
ADMIN_PERMS = ["admin.view", "admin.edit"]
STAFF_PERMS = ["admin.view", "staff.view"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        keys = sorted(set(ADMIN_PERMS + STAFF_PERMS))
        perms = {k: Permission(key=k, name=k) for k in keys}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms[k] for k in ADMIN_PERMS)
        staff_role = Role(key="staff", name="Staff")
        staff_role.permissions.extend(perms[k] for k in STAFF_PERMS)
        admin = User(email="admin@example.com", password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(admin_role)
        staff = User(email="staff@example.com", password_hash=generate_password_hash(PW), is_active=True)
        staff.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, staff])

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


def test_get_renders_form_for_admin(client):
    _login(client, "admin@example.com")
    r = client.get("/admin/reports/weekly-brief")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Weekly Brief" in body
    assert 'name="to_emails"' in body


def test_get_blocked_for_staff(client):
    _login(client, "staff@example.com")
    assert client.get("/admin/reports/weekly-brief").status_code == 403


def test_reports_index_links_tool(client):
    _login(client, "admin@example.com")
    body = client.get("/admin/reports").data.decode()
    assert "/admin/reports/weekly-brief" in body


def test_send_empty_recipients_errors(client):
    _login(client, "admin@example.com")
    token = _csrf(client)
    r = client.post("/admin/reports/weekly-brief/send",
                    data={"csrf_token": token, "to_emails": "  \n , "},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "at least one recipient" in r.data.decode().lower()


def test_send_without_api_key_errors_gracefully(client):
    _login(client, "admin@example.com")
    token = _csrf(client)
    r = client.post("/admin/reports/weekly-brief/send",
                    data={"csrf_token": token, "to_emails": "person@example.com"},
                    follow_redirects=True)
    assert r.status_code == 200
    assert "RESEND_API_KEY is not configured" in r.data.decode()


def test_weekly_brief_nre_dashboard_current_quarter(app):
    from datetime import date, datetime
    from decimal import Decimal

    from flask import render_template

    from app.eqms.modules.customer_profiles.models import Customer
    from app.eqms.modules.nre_projects.service import compute_nre_dashboard
    from app.eqms.modules.rep_traceability.models import SalesOrder
    from app.eqms.modules.rep_traceability.order_type import ORDER_TYPE_NRE_PROJECT

    today = date.today()
    quarter_month_start = ((today.month - 1) // 3) * 3 + 1
    quarter_start = date(today.year, quarter_month_start, 1)
    quarter_label = (quarter_month_start - 1) // 3 + 1
    if quarter_month_start == 1:
        prior_date = date(today.year - 1, 12, 15)
    else:
        prior_date = date(today.year, quarter_month_start - 1, 15)

    with session_scope(app) as s:
        cust = Customer(
            facility_name="Brief NRE Co",
            company_key="brief-nre-co",
            customer_type="nre",
        )
        s.add(cust)
        s.flush()
        s.add_all(
            [
                SalesOrder(
                    order_number="NRE-Q-IN",
                    order_date=quarter_start,
                    customer_id=cust.id,
                    source="manual",
                    status="completed",
                    order_amount=Decimal("1000.00"),
                    nre_invoice_status="100% Invoiced",
                    order_type=ORDER_TYPE_NRE_PROJECT,
                ),
                SalesOrder(
                    order_number="NRE-Q-HALF",
                    order_date=today,
                    customer_id=cust.id,
                    source="manual",
                    status="completed",
                    order_amount=Decimal("200.00"),
                    nre_invoice_status="50% Invoiced",
                    order_type=ORDER_TYPE_NRE_PROJECT,
                ),
                SalesOrder(
                    order_number="NRE-PRIOR",
                    order_date=prior_date,
                    customer_id=cust.id,
                    source="manual",
                    status="completed",
                    order_amount=Decimal("9999.00"),
                    nre_invoice_status="100% Invoiced",
                    order_type=ORDER_TYPE_NRE_PROJECT,
                ),
                SalesOrder(
                    order_number="NRE-CANCELLED",
                    order_date=quarter_start,
                    customer_id=cust.id,
                    source="manual",
                    status="cancelled",
                    order_amount=Decimal("500.00"),
                    nre_invoice_status="100% Invoiced",
                    order_type=ORDER_TYPE_NRE_PROJECT,
                ),
            ]
        )
        s.flush()
        dash = compute_nre_dashboard(s, start_date=quarter_start, end_date=today)
        assert dash["project_count"] == 2
        assert dash["customer_count"] == 1
        assert dash["revenue"] == Decimal("1100.00")
        numbers = {r["order_number"] for r in dash["rows"]}
        assert numbers == {"NRE-Q-IN", "NRE-Q-HALF"}
        with app.app_context():
            with app.test_request_context("/"):
                html = render_template(
                    "email/weekly_brief.html",
                    generated_at=datetime(today.year, today.month, today.day),
                    quarter_start=quarter_start,
                    quarter_label=quarter_label,
                    stats={
                        "total_units_window": 0,
                        "total_orders": 0,
                        "total_customers": 0,
                        "first_time_customers": 0,
                        "repeat_customers": 0,
                    },
                    recent_customers=[],
                    payment_rows=[],
                    nre_entries=[],
                    nre_dash_project_count=dash["project_count"],
                    nre_dash_customer_count=dash["customer_count"],
                    nre_dash_revenue=dash["revenue"],
                    nre_dash_rows=dash["rows"],
                )
    assert f"Current Quarter NRE — Q{quarter_label} {today.year}" in html
    assert html.index("Current Quarter NRE") < html.index("Upcoming NRE Invoice Tracker")
    assert html.index("Upcoming NRE Invoice Tracker") < html.index("Upcoming Payments")
    assert "Brief NRE Co" in html
    assert "NRE-Q-IN" in html
    assert "NRE-Q-HALF" in html
    assert "NRE-PRIOR" not in html
    assert "NRE-CANCELLED" not in html
    assert "$1,100.00" in html
    assert "Total NRE projects" in html
    assert "Total Amount Invoiced" in html
