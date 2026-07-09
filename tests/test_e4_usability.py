"""
E4 — Usability & readiness sweep (Phase 3 Prompt 9).

Rendered-HTML assertions for the shared breadcrumb macro and consistent empty
states on the in-scope views, plus a performance guard: against a populated
corpus (~114 docs / ~228 revisions) the Document Control list, QMS Index, DCO
Log, and global search must each issue a *bounded* number of SQL statements
(no per-row N+1 — the models eager-load revisions via selectin).
"""
import datetime as dt
import time

import pytest
from sqlalchemy import event
from werkzeug.security import generate_password_hash

from app.eqms import create_app
from app.eqms.db import session_scope
from app.eqms.models import Base, Permission, Role, User
from app.eqms.modules.document_control import dco_log
from app.eqms.modules.document_control.models import Document, DocumentRevision


ADMIN_PERMS = ["admin.view", "admin.edit", "docs.view", "docs.download",
               "training.view", "training.manage"]
STAFF_PERMS = ["admin.view", "docs.view", "docs.download", "training.view"]

N_DOCS = 114  # matches the real controlled-document corpus size


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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

    # DCO log CSV with one row per doc, so the log view has a populated corpus.
    csv_path = tmp_path / "DCO_Log_v2.csv"
    lines = ["dco_number,document_number,document_title,from_rev,to_rev,change_description,"
             "originator,date_requested,effective_date,impact_assessments"]
    for i in range(N_DOCS):
        lines.append(f"DCO{i:03d},QM.SLQ{i:03d},Doc {i},A,B,Update {i},Ethan,2025-01-01,2025-02-01,")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(dco_log, "_DEFAULT_CSV", csv_path)
    dco_log._cache.clear()

    with session_scope(application) as s:
        all_keys = sorted(set(ADMIN_PERMS + STAFF_PERMS))
        perms = {k: Permission(key=k, name=k) for k in all_keys}
        admin_role = Role(key="admin", name="Administrator")
        admin_role.permissions.extend(perms[k] for k in ADMIN_PERMS)
        staff_role = Role(key="staff", name="Staff")
        staff_role.permissions.extend(perms[k] for k in STAFF_PERMS)
        admin = User(email="admin@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        admin.roles.append(admin_role)
        staff = User(email="staff@example.com", password_hash=generate_password_hash("pw"), is_active=True)
        staff.roles.append(staff_role)
        s.add_all(list(perms.values()) + [admin_role, staff_role, admin, staff])
        s.flush()
        owner = admin.id

        # ~114 docs, each with 2 revisions (A -> B), current = B.
        for i in range(N_DOCS):
            d = Document(doc_number=f"QM.SLQ{i:03d}", title=f"Doc {i}", doc_type="SOP",
                         category=f"Subsystem {i % 8}", owner_user_id=owner, status="Released")
            s.add(d)
            s.flush()
            last = None
            for j, label in enumerate(("A", "B")):
                r = DocumentRevision(document_id=d.id, revision=label, change_summary="",
                                     effective_date=dt.date(2024 + j, 1, 1), created_by_user_id=owner,
                                     released_at=dt.datetime(2024 + j, 1, 2), released_by_user_id=owner)
                s.add(r)
                s.flush()
                last = r
            d.current_revision_id = last.id

    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, email="admin@example.com"):
    client.post("/auth/login", data={"email": email, "password": "pw"}, follow_redirects=True)


class _QueryCounter:
    """Count SQL statements executed on the engine within a `with` block."""

    def __init__(self, engine):
        self.engine = engine
        self.count = 0

    def _on_exec(self, *args, **kwargs):
        self.count += 1

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._on_exec)
        return self

    def __exit__(self, *exc):
        event.remove(self.engine, "before_cursor_execute", self._on_exec)


# Bounded number of statements regardless of corpus size. selectin adds a fixed
# number of extra queries (revisions, current_revision) — never one per row.
QUERY_BUDGET = 40


@pytest.mark.parametrize("url", [
    "/admin/modules/document-control/",
    "/admin/modules/document-control/index",
    "/admin/modules/document-control/dco-log",
    "/admin/search?q=Doc",
])
def test_views_have_no_n_plus_one(client, app, url):
    engine = app.extensions["sqlalchemy_engine"]
    _login(client)
    # Warm any first-request caches so we measure steady-state query count.
    client.get(url)
    with _QueryCounter(engine) as qc:
        t0 = time.perf_counter()
        resp = client.get(url)
        elapsed_ms = (time.perf_counter() - t0) * 1000
    assert resp.status_code == 200
    assert qc.count <= QUERY_BUDGET, f"{url}: {qc.count} queries (budget {QUERY_BUDGET})"
    print(f"[E4 perf] {url}: {qc.count} queries, {elapsed_ms:.0f} ms for {N_DOCS} docs")


def test_breadcrumbs_present_on_in_scope_views(client, app):
    _login(client)
    for url in ("/admin/modules/document-control/",
                "/admin/modules/document-control/index",
                "/admin/modules/document-control/dco-log",
                "/admin/my-training",
                "/admin/training"):
        html = client.get(url).get_data(as_text=True)
        assert 'aria-label="Breadcrumb"' in html, url
        assert "Dashboard" in html, url


def test_empty_states_distinguish_no_match(client, app):
    _login(client)
    # DC list with an impossible filter -> "no match" (docs exist).
    html = client.get("/admin/modules/document-control/?q=zzzznotfound").get_data(as_text=True)
    assert "No documents match these filters" in html
    # DCO log with an impossible filter -> "no match" (log rows exist).
    html = client.get("/admin/modules/document-control/dco-log?dco=NOPE").get_data(as_text=True)
    assert "No change records match these filters" in html
    # Search with no hits -> single friendly empty state.
    html = client.get("/admin/search?q=zzzznotfound").get_data(as_text=True)
    assert "No results found" in html


def test_focus_styles_and_labels_shipped(client, app):
    _login(client)
    # Filter inputs carry real labels (a11y).
    html = client.get("/admin/modules/document-control/").get_data(as_text=True)
    assert 'for="dc-q"' in html and 'id="dc-q"' in html
    # Global focus-visible style is served in the stylesheet.
    css = client.get("/static/design-system.css").get_data(as_text=True)
    assert ":focus-visible" in css
    assert ".breadcrumbs" in css


def test_staff_sees_breadcrumbs_read_only(client, app):
    c = app.test_client()
    _login(c, "staff@example.com")
    resp = c.get("/admin/modules/document-control/index")
    assert resp.status_code == 200
    assert 'aria-label="Breadcrumb"' in resp.get_data(as_text=True)
