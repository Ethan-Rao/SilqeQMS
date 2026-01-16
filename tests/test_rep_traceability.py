import io

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import AuditEvent, Base, Permission, Role, User
from app.eqms.modules.rep_traceability.models import ApprovalEml, DistributionLogEntry, TracingReport


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")

    app = create_app()
    engine = app.extensions["sqlalchemy_engine"]
    Base.metadata.create_all(bind=engine)

    with session_scope(app) as s:
        perms = [
            Permission(key="admin.view", name="Admin: view shell"),
            Permission(key="distribution_log.view", name="Distribution Log: view"),
            Permission(key="distribution_log.create", name="Distribution Log: create"),
            Permission(key="distribution_log.edit", name="Distribution Log: edit"),
            Permission(key="distribution_log.delete", name="Distribution Log: delete"),
            Permission(key="distribution_log.import", name="Distribution Log: import"),
            Permission(key="distribution_log.export", name="Distribution Log: export"),
            Permission(key="tracing_reports.view", name="Tracing Reports: view"),
            Permission(key="tracing_reports.generate", name="Tracing Reports: generate"),
            Permission(key="tracing_reports.download", name="Tracing Reports: download"),
            Permission(key="approvals.view", name="Approvals: view"),
            Permission(key="approvals.upload", name="Approvals: upload"),
            Permission(key="approvals.download", name="Approvals: download"),
        ]
        r = Role(key="admin", name="Administrator")
        r.permissions.extend(perms)
        u = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        u.roles.append(r)
        s.add_all(perms + [r, u])

    return app.test_client()


def test_rep_traceability_vertical_slice(client):
    # Login
    r = client.post("/auth/login", data={"email": "admin@example.com", "password": "pw"}, follow_redirects=False)
    assert r.status_code == 302

    # Create a manual distribution entry
    r = client.post(
        "/admin/distribution-log/new",
        data={
            "ship_date": "2025-01-15",
            "order_number": "",
            "facility_name": "Hospital A",
            "rep_id": "",
            "rep_name": "John Doe",
            "customer_name": "Hospitals Inc",
            "sku": "211810SPT",
            "lot_number": "SLQ-12345",
            "quantity": "10",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701",
            "tracking_number": "1Z999AA10123456784",
        },
        follow_redirects=False,
    )
    assert r.status_code == 302

    app = client.application
    with session_scope(app) as s:
        entry = s.query(DistributionLogEntry).filter(DistributionLogEntry.facility_name == "Hospital A").one()
        assert entry.source == "manual"

    # CSV import (2 rows)
    csv_bytes = b"""Ship Date,Order Number,Facility Name,SKU,Lot,Quantity,City,State,Zip\n2025-01-14,SO-12344,Hospital B,211610SPT,SLQ-23456,5,Chicago,IL,60601\n2025-01-13,SO-12343,Hospital C,211410SPT,SLQ-34567,8,Peoria,IL,61601\n"""
    r = client.post(
        "/admin/distribution-log/import-csv",
        data={"csv_file": (io.BytesIO(csv_bytes), "test.csv")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code in (200, 302)

    with session_scope(app) as s:
        count = s.query(DistributionLogEntry).count()
        assert count >= 3

    # Export CSV
    r = client.get("/admin/distribution-log/export")
    assert r.status_code == 200
    assert b"Ship Date,Order #" in r.data

    # Generate tracing report for 2025-01
    r = client.post(
        "/admin/tracing/generate",
        data={"month": "2025-01", "rep_id": "", "source": "all", "sku": "all", "customer": ""},
        follow_redirects=False,
    )
    assert r.status_code == 302

    with session_scope(app) as s:
        tr = s.query(TracingReport).order_by(TracingReport.id.desc()).first()
        assert tr is not None
        report_id = tr.id

    # Download tracing report CSV
    r = client.get(f"/admin/tracing/{report_id}/download")
    assert r.status_code == 200
    assert b"Ship Date,Order #,Facility" in r.data

    # Upload approval .eml
    eml = b"From: approver@example.com\nTo: admin@silqeqms.com\nSubject: Approval: Tracing Report 2025-01\nDate: Mon, 15 Jan 2025 10:30:00 -0500\n\nApproved.\n"
    r = client.post(
        f"/admin/tracing/{report_id}/approvals/upload",
        data={"eml_file": (io.BytesIO(eml), "test_approval.eml"), "notes": "Approved by QA"},
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code == 302

    with session_scope(app) as s:
        a = s.query(ApprovalEml).filter(ApprovalEml.report_id == report_id).order_by(ApprovalEml.id.desc()).first()
        assert a is not None
        approval_id = a.id

    # Download approval
    r = client.get(f"/admin/approvals/{approval_id}/download")
    assert r.status_code == 200
    assert b"Subject: Approval: Tracing Report 2025-01" in r.data

    # Audit events exist
    with session_scope(app) as s:
        actions = [e.action for e in s.query(AuditEvent).order_by(AuditEvent.id.asc()).all()]
        assert "distribution_log_entry.create" in actions
        assert "distribution_log_entry.import_csv" in actions
        assert "distribution_log_entry.export" in actions
        assert "tracing_report.generate" in actions
        assert "tracing_report.download" in actions
        assert "approval_eml.upload" in actions
        assert "approval_eml.download" in actions

