"""
E3 — Cross-linking & training integration (Phase 3 Prompt 8).

Covers: training assignments targeting a specific controlled-document revision
(default = current), the My Training assigned-vs-current display with a stale
flag, idempotent re-assignment per (document, revision, user), the "Related
documents" section on the document detail page (shared SLQ family, obsolete
hidden, parent-first ordering), and the shared slq_family() helper.
"""
import datetime as dt

import pytest
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.document_control.models import Document, DocumentRevision
from app.eqms.modules.document_control.qms_index import slq_family
from app.eqms.modules.training.models import TrainingAssignment


PW = "pw"
ADMIN_PERMS = ["admin.view", "admin.edit", "docs.view", "docs.download",
               "training.view", "training.manage"]
STAFF_PERMS = ["admin.view", "docs.view", "docs.download", "training.view"]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for k in ("S3_ENDPOINT", "S3_REGION", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.delenv(k, raising=False)

    application = create_app()
    engine = application.extensions["sqlalchemy_engine"]
    Base.metadata.create_all(bind=engine)
    application.config["_schema_health_ok"] = True

    with session_scope(application) as s:
        all_keys = sorted(set(ADMIN_PERMS + STAFF_PERMS))
        perms = {k: Permission(key=k, name=k) for k in all_keys}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms[k] for k in ADMIN_PERMS)
        staff_role = Role(key="staff", name="Staff")
        staff_role.permissions.extend(perms[k] for k in STAFF_PERMS)
        admin = User(email="admin@example.com", password_hash=generate_password_hash(PW), is_active=True)
        admin.roles.append(admin_role)
        staff = User(email="staff@example.com", password_hash=generate_password_hash(PW), is_active=True)
        staff.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, staff])
        s.flush()
        owner = admin.id

        def _doc(number, title, doc_type, status="Released", revs=("A",)):
            d = Document(doc_number=number, title=title, doc_type=doc_type,
                         category=None, owner_user_id=owner, status=status)
            s.add(d)
            s.flush()
            last = None
            for i, label in enumerate(revs):
                r = DocumentRevision(document_id=d.id, revision=label, change_summary="",
                                     effective_date=dt.date(2021 + i, 1, 1), created_by_user_id=owner,
                                     released_at=dt.datetime(2021 + i, 1, 2), released_by_user_id=owner)
                s.add(r)
                s.flush()
                last = r
            d.current_revision_id = last.id
            return d

        # SLQ family 15: parent SOP (A->B, current B) + form + template + obsolete form.
        _doc("QM.SLQ015", "Supplier QA SOP", "SOP", revs=("A", "B"))
        _doc("FM1-QM.SLQ015", "Supplier Survey Form", "Form", revs=("A",))
        _doc("TMP1-QM.SLQ015", "Supplier Template", "Template", revs=("A",))
        _doc("FM2-QM.SLQ015", "Retired Supplier Form", "Form", status="Obsolete", revs=("A",))
        # Unrelated family.
        _doc("QM.SLQ099", "Lonely SOP", "SOP", revs=("A",))

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@example.com"):
    client.post("/auth/login", data={"email": email, "password": PW}, follow_redirects=True)


def _csrf(client):
    import secrets
    with client.session_transaction() as sess:
        token = sess.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            sess["csrf_token"] = token
        return token


def _ids(app, doc_number):
    with session_scope(app) as s:
        d = s.query(Document).filter(Document.doc_number == doc_number).one()
        revs = {r.revision: r.id for r in d.revisions}
        return d.id, d.current_revision_id, revs


def _uid(app, email):
    with session_scope(app) as s:
        return s.query(User).filter(User.email == email).one().id


# --- slq_family helper ------------------------------------------------------
def test_slq_family_shared_across_derivatives():
    assert slq_family("QM.SLQ015") == 15
    assert slq_family("FM1-QM.SLQ015") == 15
    assert slq_family("TMP1-QM.SLQ015") == 15
    assert slq_family("QM.SLQ099") == 99
    assert slq_family("NO-SLQ-HERE") is None
    assert slq_family(None) is None


# --- Task A: training targets a specific document revision ------------------
def test_assign_defaults_to_current_revision(client, app):
    _login(client)
    doc_id, current_rev_id, _ = _ids(app, "QM.SLQ015")
    staff_uid = _uid(app, "staff@example.com")
    r = client.post("/admin/training/new", data={
        "item_type": "document", "document_id": str(doc_id),
        "document_revision_id": "",  # default -> current
        "user_ids": [str(staff_uid)], "csrf_token": _csrf(client),
    }, follow_redirects=True)
    assert r.status_code == 200
    with session_scope(app) as s:
        a = s.query(TrainingAssignment).filter(TrainingAssignment.assigned_to_user_id == staff_uid).one()
        assert a.document_revision_id == current_rev_id
        assert "Rev B" in a.item_title  # current revision cached in title


def test_assign_specific_revision_and_my_training_stale_flag(client, app):
    _login(client)
    doc_id, _, revs = _ids(app, "QM.SLQ015")
    staff_uid = _uid(app, "staff@example.com")
    # Assign the OLD revision A (current is B) -> should be flagged stale.
    client.post("/admin/training/new", data={
        "item_type": "document", "document_id": str(doc_id),
        "document_revision_id": str(revs["A"]),
        "user_ids": [str(staff_uid)], "csrf_token": _csrf(client),
    }, follow_redirects=True)

    with session_scope(app) as s:
        a = s.query(TrainingAssignment).filter(TrainingAssignment.assigned_to_user_id == staff_uid).one()
        assert a.document_revision_id == revs["A"]

    # The assignee's My Training shows assigned vs current + a stale warning.
    c = app.test_client()
    _login(c, "staff@example.com")
    html = c.get("/admin/my-training").get_data(as_text=True)
    assert "Assigned revision:" in html
    assert "Rev A" in html
    assert "newer revision (Rev B) is now current" in html


def test_reassign_same_revision_idempotent_but_new_revision_creates_row(client, app):
    _login(client)
    doc_id, _, revs = _ids(app, "QM.SLQ015")
    staff_uid = _uid(app, "staff@example.com")

    def _assign(rev_id):
        client.post("/admin/training/new", data={
            "item_type": "document", "document_id": str(doc_id),
            "document_revision_id": str(rev_id),
            "user_ids": [str(staff_uid)], "csrf_token": _csrf(client),
        }, follow_redirects=True)

    _assign(revs["A"])
    _assign(revs["A"])  # idempotent: same (doc, rev, user) open item
    with session_scope(app) as s:
        assert s.query(TrainingAssignment).filter(
            TrainingAssignment.assigned_to_user_id == staff_uid).count() == 1

    _assign(revs["B"])  # a different revision is a distinct item
    with session_scope(app) as s:
        assert s.query(TrainingAssignment).filter(
            TrainingAssignment.assigned_to_user_id == staff_uid).count() == 2


def test_manage_list_shows_targeted_revision(client, app):
    _login(client)
    doc_id, _, revs = _ids(app, "QM.SLQ015")
    staff_uid = _uid(app, "staff@example.com")
    client.post("/admin/training/new", data={
        "item_type": "document", "document_id": str(doc_id),
        "document_revision_id": str(revs["A"]),
        "user_ids": [str(staff_uid)], "csrf_token": _csrf(client),
    }, follow_redirects=True)
    html = client.get("/admin/training").get_data(as_text=True)
    assert "Rev A" in html


# --- Task B: related documents (shared SLQ family) --------------------------
def test_related_documents_lists_family_hides_obsolete(client, app):
    _login(client)
    doc_id, _, _ = _ids(app, "QM.SLQ015")
    html = client.get(f"/admin/modules/document-control/{doc_id}").get_data(as_text=True)
    assert "Related documents" in html
    assert "FM1-QM.SLQ015" in html
    assert "TMP1-QM.SLQ015" in html
    assert "FM2-QM.SLQ015" not in html   # obsolete hidden
    assert "QM.SLQ099" not in html       # different family


def test_related_documents_parent_sop_first(client, app):
    _login(client)
    form_id, _, _ = _ids(app, "FM1-QM.SLQ015")
    parent_id, _, _ = _ids(app, "QM.SLQ015")
    tmpl_id, _, _ = _ids(app, "TMP1-QM.SLQ015")
    html = client.get(f"/admin/modules/document-control/{form_id}").get_data(as_text=True)
    # Related detail links appear only in the related section; the parent SOP
    # (no FM/TMP prefix) is ordered before the template.
    assert html.index(f"document-control/{parent_id}") < html.index(f"document-control/{tmpl_id}")


def test_no_related_section_when_family_alone(client, app):
    _login(client)
    doc_id, _, _ = _ids(app, "QM.SLQ099")
    html = client.get(f"/admin/modules/document-control/{doc_id}").get_data(as_text=True)
    assert "Related documents" not in html


def test_related_documents_visible_to_staff_read_only(client, app):
    c = app.test_client()
    _login(c, "staff@example.com")
    doc_id, _, _ = _ids(app, "QM.SLQ015")
    resp = c.get(f"/admin/modules/document-control/{doc_id}")
    assert resp.status_code == 200
    assert "Related documents" in resp.get_data(as_text=True)
