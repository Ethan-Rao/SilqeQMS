"""
P4-02 — Import relocation to Admin Tools; packing-slip-only distribution import.
"""
from datetime import date
from io import BytesIO

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User

PW = "pw"
ADMIN_PERMS = [
    "admin.view", "admin.edit",
    "sales_orders.view", "sales_orders.edit", "sales_orders.import",
    "distribution_log.view", "distribution_log.import",
    "customers.view",
]
STAFF_PERMS = ["admin.view", "sales_orders.view", "staff.view"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path / "storage"))
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    Base.metadata.create_all(bind=application.extensions["sqlalchemy_engine"])
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        all_keys = sorted(set(ADMIN_PERMS) | set(STAFF_PERMS))
        perms = {k: Permission(key=k, name=k) for k in all_keys}
        admin_role = Role(key="admin", name="Administrator")
        for k in ADMIN_PERMS:
            admin_role.permissions.append(perms[k])
        staff_role = Role(key="staff", name="Staff")
        for k in STAFF_PERMS:
            staff_role.permissions.append(perms[k])
        admin = User(
            email="admin@silq.tech",
            display_name="Admin",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        admin.roles.append(admin_role)
        staff = User(
            email="staff@silq.tech",
            display_name="Staff",
            password_hash=generate_password_hash(PW),
            is_active=True,
        )
        staff.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, staff])

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@silq.tech"):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets

    with client.session_transaction() as sess:
        token = sess.get("csrf_token") or secrets.token_urlsafe(32)
        sess["csrf_token"] = token
        return token


def test_admin_tools_has_imports_card_with_both_forms(client):
    _login(client)
    r = client.get("/admin/diagnostics")
    assert r.status_code == 200
    body = r.data.decode()
    assert 'id="imports"' in body
    assert "/admin/sales-orders/import-pdf-bulk" in body or "sales_orders_import_pdf_bulk" in body
    # Form actions resolve via url_for; check path fragments
    assert 'name="pdf_files"' in body
    assert 'name="csv_file"' in body
    assert 'action="' in body
    assert "sales-orders/import-pdf-bulk" in body
    assert "distribution-log/import-csv" in body


def test_imports_card_before_system_status(client):
    _login(client)
    body = client.get("/admin/diagnostics").data.decode()
    assert body.index('id="imports"') < body.index("System Status")


def test_legacy_sales_order_import_get_redirects(client):
    _login(client)
    r = client.get("/admin/sales-orders/import-pdf", follow_redirects=False)
    assert r.status_code in (301, 302)
    loc = r.headers.get("Location") or ""
    assert "/admin/diagnostics" in loc
    assert "imports" in loc or loc.endswith("/admin/diagnostics") or "#imports" in loc


def test_distribution_import_is_packing_slips_only(client):
    _login(client)
    r = client.get("/admin/distribution-log/import")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Import Packing Slips" in body
    assert "packing-slips/import-bulk" in body or "packing_slips" in body.lower()
    assert 'name="csv_file"' not in body
    assert "packing-slips" in body or "packing_slips_import_bulk" in body
    # Confirm packing form action
    assert "/admin/packing-slips/import-bulk" in body or "packing-slips/import" in body


def test_sales_order_bulk_upload_redirects_to_admin_tools(client, app):
    """End-to-end guard: daily upload must land back on Admin Tools."""
    _login(client)
    token = _csrf(client)
    # Minimal PDF bytes; parser may fail but redirect path must still work
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    r = client.post(
        "/admin/sales-orders/import-pdf-bulk",
        data={
            "csrf_token": token,
            "pdf_files": (BytesIO(pdf), "test.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code in (301, 302)
    loc = r.headers.get("Location") or ""
    assert "/admin/diagnostics" in loc


def test_staff_does_not_see_import_pdf_on_sales_orders_list(client):
    _login(client, email="staff@silq.tech")
    r = client.get("/admin/sales-orders")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Import PDF" not in body


def test_admin_tools_imports_sync_column_has_packing_slips_not_old_cards(client):
    _login(client)
    body = client.get("/admin/diagnostics").data.decode()
    assert "Import CSV (Distributions)" not in body
    assert "Import Sales Order PDFs" not in body
    assert "Packing Slips" in body
