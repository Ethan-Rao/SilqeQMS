# Dev agent prompt — temporary Auditor Files portal (read-only)

> **Status:** NEW module. Temporary. Must be completely isolated from the existing admin system. All relevant patterns already exist in this repo; reuse them rather than reinventing.

---

## 0. TL;DR for the agent

You are adding a **read-only, auditor-only portal** at `/auditor/*` that lets a single external auditor browse files the operator drops into `<repo_root>/Auditor Files/`. The auditor signs in with credentials supplied via env vars and sees an admin-dashboard-style grid whose cards are the **immediate subfolders** of that directory. Inside a folder they see files; clicking a file shows it **viewable in-browser** (PDFs inline; `.docx` → HTML text via existing `mammoth` integration with an extra **“View as PDF”** button; `.xlsx/.xls` → **auto PDF view** with an optional table fallback). Every folder/file access is logged to a new table that the **admin** can browse and export from the existing admin shell.

**You must not:**

- change any existing admin/auth/RBAC/storage code paths in a way that affects current users,
- give the auditor any permission outside `auditor_portal.access`,
- hard-code the auditor password or commit any secret,
- expose `/admin/*` routes to the auditor,
- add SaaS-based viewers (Office Online, Google Docs, etc.).

---

## 1. Product requirements (confirmed with stakeholder)

1. **Temporary module**, runs alongside the existing app, behind a feature flag.
2. **Who has access:** exactly one auditor account (seeded from env vars), plus the admin (who sees the access log only — not the portal pages unless they also get the perm).
3. **What they can do:** view content of QMS files the operator places into the `Auditor Files` tree. No edit, no delete. Download UI is not provided, but the system doesn’t actively block downloads the browser performs.
4. **Dashboard layout:** mirrors the admin dashboard (`app/eqms/templates/admin/index.html`, already uses a 4-column grid of `.card.card--link.dash-card` tiles). Cards here = **immediate subfolders** of `AUDITOR_FILES_ROOT`. Operator creates additional subfolders over time.
5. **File types supported:** `.pdf`, `.docx`, `.doc` (best-effort), `.xlsx`, `.xls`, `.csv`, `.txt`, `.png`, `.jpg`, `.jpeg`, `.gif`.
6. **View behaviour by type (stakeholder-confirmed):**
   - **PDF** → inline browser view.
   - **DOCX** → text-based HTML view (same look as the existing `/admin/admin-docs/documents/<id>/view` page) **with a “View PDF version” button** that serves a server-converted PDF.
   - **XLSX / XLS** → **server-converted PDF view is the default**. (“pdfs/excels can automatically be pdfs.”) Provide a secondary “View as table” fallback for spreadsheets that paginate poorly.
   - **DOC (legacy)** → mammoth can’t handle these. Show a clean “please re-save as `.docx`” message page. Do **not** add LibreOffice/wkhtmltopdf.
   - Images → inline `<img>`.
   - `.csv` / `.txt` → reuse existing CSV renderer / monospaced text view.
7. **No third parties.** Pure-Python conversion stack. `weasyprint` preferred; `xhtml2pdf` fallback if `weasyprint` can’t be installed on the current Docker image without system-lib gymnastics. Do **not** add `libreoffice`, `unoconv`, or `wkhtmltopdf`.
8. **Access logging:** each folder/file access is logged to a new table and is reviewable from the admin shell with filters and CSV export.
9. **Isolation:** an auditor-only user must never reach any `/admin/*` URL and must not see any admin chrome/nav.

---

## 2. Environment variables (exact names)

These are **already configured in DigitalOcean App Platform** under the existing app. Do **not** rename them.

| Var | Purpose | Notes |
|-----|---------|-------|
| `AUDITOR_EMAIL` | Auditor login email. | Lower-cased on seed. |
| `AUDITOR_PASSWORD` | Seed password. | Seeded only if user row is missing. **Never** overwrite an existing user’s password. **Never** log, template, or return in any response. |
| `AUDITOR_FILES_ROOT` *(new)* | Absolute path to the Auditor Files tree. | Default if unset: `<repo_root>/Auditor Files` (the folder already exists). |
| `AUDITOR_PORTAL_ENABLED` *(new)* | `"1"` / `"true"` / `"yes"` enables the portal. Any other value disables it. | When disabled, every `/auditor/*` route returns **404** and the admin access-log page says “portal disabled.” |
| `AUDITOR_MAX_FILE_MB` *(new, optional)* | Per-file rendering cap. | Default 50. Oversized files short-circuit with a friendly message instead of hanging. |
| `AUDITOR_PDF_BACKEND` *(new, optional)* | `"weasyprint"` (default) or `"xhtml2pdf"`. | Chooses the HTML→PDF engine at runtime. |

Extend `app/eqms/config.py::load_config` to surface these values as Flask config keys with the same names. Do not read `os.environ` directly inside blueprint handlers — keep config loading in `config.py` and read from `current_app.config` at request time.

**Operator security note** (already communicated to stakeholder): credentials pasted during design review were exposed and should be rotated before handing them to the auditor. Do not embed any leaked value in code or docs.

---

## 3. Repo tour — what to read before writing code

Read these files; they show the exact patterns to reuse.

### 3.1 App factory and blueprint registration
- `app/eqms/__init__.py::create_app` — registers all blueprints, sets up CSRF, CSP, schema-health gate, error handlers. You will register a new `auditor_portal_bp` with `url_prefix="/auditor"` **in this file** (do not auto-discover). You will also register the new admin log viewer inside the existing `admin_bp` (no separate mount point).

### 3.2 Config
- `app/eqms/config.py` — `Settings` dataclass + `load_config()` dict. Add your new env vars here.

### 3.3 Auth and sessions
- `app/eqms/auth.py` — `/auth/login` (GET/POST), `/auth/logout`, `load_current_user()`, IP-based rate limiting. Critically, **`login_post` currently hard-codes a redirect to `url_for("admin.index")`** on success unless a local `next` is supplied. You need to change this so that users with the `auditor` role (and no admin perms) are redirected to `/auditor/`. Do it cleanly via a helper like `_post_login_redirect(user)` rather than sprinkling conditionals.
- Sessions use Flask signed cookies (`PERMANENT_SESSION_LIFETIME = 8h`). Secure / HttpOnly / SameSite=Lax already enforced via `config.py` in production.

### 3.4 RBAC
- `app/eqms/rbac.py` — `require_permission(key)` decorator. If unauthenticated → redirect to `auth.login_get?next=...`. If authenticated but missing perm → `abort(403)` and sets `g.missing_permission`. Reuse this unchanged.
- `user_has_permission(user, key)` — plain list traversal.

### 3.5 Models and seed
- `app/eqms/models.py` — `User`, `Role`, `Permission`, `UserRole`, `RolePermission`, `AuditEvent`. Note: the bottom imports module models so `Base.metadata` sees them (used by the schema-health check in `create_app`). **You must add your new `AuditorAccessEvent` model’s import there** or the schema-health check in production will flag it as drift, blocking admin routes.
- `scripts/init_db.py::seed_only` — the canonical place to add permissions, roles, users. Must remain **idempotent**: it runs on every deploy via `scripts/_db_utils.script_session`. Use its `ensure_perm(key, name)` helper and the `if p not in role.permissions: role.permissions.append(p)` pattern.

### 3.6 Audit trail
- `app/eqms/audit.py::record_event(s, *, actor, action, entity_type, entity_id, reason, metadata)` — append-only. Call this from **both** `auditor_portal` login/logout (for the coarse `auth.*` trail) and from the access-log helper (optional; primary log goes to the new dedicated table).

### 3.7 Existing file viewer (REUSE, don’t rewrite)
- `app/eqms/document_viewer.py` — `needs_server_render(filename)`, `render_document_to_response(bytes, filename, content_type, download_url, back_url)`. Mammoth for `.docx`, openpyxl for `.xlsx/.xls`, csv.reader for `.csv`. Includes `_sanitize_html` (strips `<script>/<iframe>/on*=`).
- `app/eqms/templates/admin/document_viewer.html` — the template the renderer uses. It takes `filename`, `rendered_html`, `sheets`, `download_url`, `back_url`. **Reuse this template directly**; do not fork it. If you need an extra “View PDF version” button for the auditor, pass an additional context var (e.g. `pdf_url`) and extend the template with a `{% if pdf_url %}` block.
- `app/eqms/modules/admin_docs/admin.py::admin_docs_document_view` — canonical integration example: handles `needs_server_render` branch, falls back to `send_file` with `allow_inline_view` for PDFs/images.
- `app/eqms/utils.py::allow_inline_view` — decides inline vs attachment for native-renderable types.

### 3.8 Storage
- `app/eqms/storage.py` — abstract `Storage` with `LocalStorage` and `S3Storage` backends. Instantiate via `storage_from_config(current_app.config)`. **Note:** the production env already has `STORAGE_BACKEND=s3` pointing at DO Spaces (`raoeqms-files`). Cached-PDF writes under a **new prefix** `auditor-cache/pdf/` must never collide with existing keys like `sales_orders/…` or `admin_docs/…`.

### 3.9 Admin dashboard look & feel
- `app/eqms/templates/admin/index.html` — 4-column grid, `.dash-col-heading` + `.dash-card-title` + `.dash-card-desc` styles, responsive breakpoints. Mirror this styling for `/auditor/`.
- `app/eqms/templates/_layout.html` — global layout with top bar. **Do not use this layout for auditor pages**; it links to admin modules (`Distribution Log`, `Customers`, etc.) via `{% if has_perm(...) %}` gates. Even gated, the auditor should never see admin nav. Create a **new base layout** `templates/auditor_portal/base.html` that reuses the design-system CSS but has a minimal top bar: brand + auditor email + Logout.

### 3.10 Alembic migrations
- `migrations/versions/*.py` — revision IDs are arbitrary strings; `down_revision` chains to the previous. See `t2u3v4w5x6_migrate_packing_slip_pdf_types.py` and `r1s2t3u4v5_add_admin_docs_library.py` for format. Pick a new short-hex revision id that doesn’t collide and `down_revision` from the current head (run `alembic heads` locally or inspect the most recent file). **The deploy pipeline runs `alembic upgrade head` automatically**; your migration must be idempotent-safe (don’t crash re-applying).

### 3.11 Security posture (what already exists)
- **CSRF:** see `app/eqms/security.py`. All non-login POST/PUT/PATCH/DELETE require `csrf_token` form field or `X-CSRF-Token` header. Login page (`login_post`) is explicitly exempt. Your portal has **no POSTs** (it’s read-only) — no new CSRF work needed, but any form you add must include `{{ csrf_token }}`.
- **CSP:** `app/eqms/__init__.py::_security_headers` sets `frame-src 'none'; object-src 'none'`. **This affects you:** embedding PDFs via `<iframe>` or `<object>` will be blocked. Use a plain `<a href="..." target="_blank">` or serve the PDF on its own URL so Chrome’s native PDF viewer handles it, or use `<embed type="application/pdf">` (also blocked under `object-src 'none'`). **Preferred:** the PDF view route returns the PDF directly (`application/pdf`, `Content-Disposition: inline`) — the browser displays its own PDF viewer, no iframe needed. For docx’s “View as PDF” button, the button is just a link to that route.
- **Cookie flags:** already Secure/HttpOnly/SameSite=Lax in prod.
- **Rate limiting:** shared login rate limit (5 attempts / 5 min / IP) already applies since the auditor uses the existing `/auth/login`. Don’t build a separate login page.

### 3.12 Schema health check
- `create_app` runs `_run_schema_health_check()` which walks `Base.metadata.tables` and verifies every expected table exists in the DB. If drift is detected, **all `/admin/*` routes are blocked for logged-in users** with a 500 page until `alembic upgrade head` runs. To avoid blocking production on first deploy:
  1. Add `AuditorAccessEvent` to the bottom-of-file imports in `models.py` so `Base.metadata` sees it.
  2. Ship the Alembic migration in the same PR that adds the model.
  3. Confirm `alembic upgrade head` succeeds locally against SQLite before merging.

---

## 4. Filesystem contract

- **Root resolution (once, at blueprint import / app startup):**
  ```python
  root_raw = (current_app.config.get("AUDITOR_FILES_ROOT") or "").strip()
  if not root_raw:
      root = Path(__file__).resolve().parents[3] / "Auditor Files"
  else:
      root = Path(root_raw).expanduser()
  ROOT = root.resolve(strict=False)
  ```
- If `ROOT` is missing or not a directory, do **not** crash the app; just treat the portal as effectively empty and log a warning once at startup.
- **Safe-resolve every user-supplied relative path:**
  ```python
  def _safe_resolve(rel: str) -> Path:
      # Normalize: strip leading slashes, disallow drive letters
      rel = (rel or "").strip().lstrip("/\\")
      candidate = (ROOT / rel).resolve(strict=False)
      try:
          candidate.relative_to(ROOT)
      except ValueError:
          abort(404)  # leak nothing
      return candidate
  ```
  Use `Path.relative_to` instead of the 3.9+ `is_relative_to` for broader compatibility.
- **Reject** symlinks that resolve outside ROOT (the `relative_to` check covers this after `.resolve()`).
- **Ignore:** hidden dotfiles, Office lock files (`~$*`), files larger than `AUDITOR_MAX_FILE_MB`, unsupported extensions (return 415 or a friendly page).
- **Listings** are non-recursive: a folder page shows immediate subfolders + files only.
- **Encoding:** on Windows dev, `Path.resolve` returns Windows paths; always transport URLs as forward-slash `rel_path` and `Path`-join on the server.

---

## 5. Routes

All under the new blueprint `auditor_portal_bp` with `url_prefix="/auditor"`. Every route is gated by `@require_permission("auditor_portal.access")` **and** a feature-flag gate helper:

```python
def _portal_enabled() -> bool:
    v = (current_app.config.get("AUDITOR_PORTAL_ENABLED") or "").strip().lower()
    return v in ("1", "true", "yes", "on")

@bp.before_request
def _gate():
    if not _portal_enabled():
        abort(404)
```

| Method | Path | Perm | Purpose |
|--------|------|------|---------|
| GET | `/auditor/` | `auditor_portal.access` | Dashboard: one tile per top-level subfolder of `ROOT`. Tile title = folder name, subtitle = N files (non-recursive count). |
| GET | `/auditor/browse/<path:rel_path>` | `auditor_portal.access` | Folder listing + breadcrumbs. Rows are subfolders then files. Each file row links to `/auditor/file/<rel>`. |
| GET | `/auditor/file/<path:rel_path>` | `auditor_portal.access` | Primary view per §6. Query params: `as=pdf` (force PDF for docx/xlsx), `as=table` (force HTML table for xlsx). Without param, use per-type default. |

Admin log routes (added inside existing `admin_bp`):

| Method | Path | Perm | Purpose |
|--------|------|------|---------|
| GET | `/admin/auditor-access-log` | `auditor_portal.admin` | Filters (user email, action, path contains, date from/to) + paginated list. |
| GET | `/admin/auditor-access-log/export` | `auditor_portal.admin` | CSV export of filtered rows. |

Auditor login uses the existing `/auth/login` (no new login page). Update `auth.login_post` so that after successful login the redirect target comes from a new helper `_post_login_redirect(user)` that returns `/auditor/` if the user has `auditor_portal.access` and **no** `admin.view`; otherwise falls back to the current `admin.index`. Respect the existing local-`next` override.

Add a `before_request` in `auth.py` or `admin.py` that 403s authenticated users whose only perm is `auditor_portal.access` if they hit `/admin/*`. Defense in depth on top of `require_permission`. The existing 403 error page template handles the rest.

---

## 6. View implementation per type

```
/auditor/file/<rel>  → _safe_resolve → inspect extension → dispatch
```

| Ext | Default action | ?as=pdf | ?as=table |
|-----|----------------|---------|-----------|
| `.pdf` | `send_file(fobj, mimetype="application/pdf", as_attachment=False, download_name=name)` | same | n/a |
| `.docx` | `render_document_to_response(bytes, filename, content_type, download_url=None, back_url=<folder>)`. Pass an extra `pdf_url=...` into a lightly extended `document_viewer.html` so the template renders a “View PDF version” button. | Run the docx→HTML step (mammoth), feed HTML into the PDF backend, return `application/pdf`. | n/a |
| `.doc` | Render `templates/auditor_portal/file_not_viewable.html` with a clear message about re-saving as `.docx`. Log `view_unsupported`. | same | n/a |
| `.xlsx` / `.xls` | Build HTML table via the existing Excel renderer (factor its HTML-building step into a helper that returns an HTML string); hand HTML to the PDF backend; return `application/pdf`. (Default view is PDF per §1.) | same as default | return the existing HTML-table render (`document_viewer.html` with `sheets=...`). |
| `.csv` | Reuse existing CSV renderer (HTML table). | Optional, not required; if implementing, same HTML→PDF path. | n/a |
| `.txt` | `<pre>`-wrapped escaped text in the auditor layout. | Optional. | n/a |
| Images | `send_file(..., mimetype=<image/...>, as_attachment=False)`. | n/a | n/a |
| Unsupported | Render `file_not_viewable.html`. Log and return 200 (not 404) so the user sees the reason. | n/a | n/a |

### 6.1 HTML → PDF pipeline (new code, ~100 lines)

Create `app/eqms/modules/auditor_portal/pdf_convert.py` with:

- `html_to_pdf_bytes(html: str, base_url: str | None = None) -> bytes` — dispatches to the configured backend. Both backends:
  - **WeasyPrint** path: `from weasyprint import HTML; HTML(string=html, base_url=base_url).write_pdf()`. Check at import time that system libs are available; on ImportError, log once and fall back.
  - **xhtml2pdf** path: `from xhtml2pdf import pisa; pisa.CreatePDF(io.StringIO(html), dest=buf)`. Limited CSS support but installs everywhere.
- `docx_bytes_to_pdf(file_bytes: bytes) -> bytes` — mammoth convert → sanitize → wrap in minimal HTML shell (basic CSS to keep tables readable) → `html_to_pdf_bytes`.
- `xlsx_bytes_to_pdf(file_bytes: bytes) -> bytes` — reuse the existing Excel-to-HTML helper (see §6.2) → wrap → `html_to_pdf_bytes`. Target portrait A4 by default; wrap each sheet in a `<section style="page-break-after: always;">`. Truncate any sheet to the first **2000 data rows** and prepend a banner “showing first N of M rows” when truncation occurs.
- `CachedPdfStore` — adapter backed by `storage_from_config(current_app.config)`. API:
  - `get(namespace: str, cache_key: str) -> bytes | None`
  - `put(namespace: str, cache_key: str, data: bytes) -> None`
  - Storage key: `f"auditor-cache/{namespace}/{cache_key}.pdf"`
  - `cache_key = sha256(f"{rel_path}|{size}|{mtime_ns}".encode()).hexdigest()`
  - On `get`, swallow `StorageError` / any boto exception and return `None` (treat as cache miss).

### 6.2 Refactor the Excel HTML step

The existing `document_viewer._render_excel` builds a `sheets` dict and hands it to `document_viewer.html`. Add a sibling helper:

```python
def render_excel_to_html(file_bytes: bytes) -> str | None:
    """Return a standalone HTML string (no viewer chrome) for PDF conversion."""
```

Do **not** inline this into `document_viewer.py`’s response builders; place it in the new `auditor_portal/pdf_convert.py` so the viewer stays unchanged. Reach into `openpyxl` directly the same way `_render_excel` does.

### 6.3 Failure handling

If any conversion raises:

1. `current_app.logger.warning("PDF conversion failed for %s: %s", rel_path, exc)` (no stack trace at INFO; debug level only for full trace).
2. Fall back:
   - DOCX `?as=pdf` → redirect to the text view with a flash “PDF rendering temporarily unavailable.”
   - XLSX default (auto-PDF) → render the HTML table view (`?as=table` behaviour) and flash.
3. **Never 500**; the auditor session must stay interactive.

---

## 7. Access logging

### 7.1 Model

Create `app/eqms/modules/auditor_portal/models.py`:

```python
class AuditorAccessEvent(Base):
    __tablename__ = "auditor_access_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)  # view_dashboard | view_folder | view_file | view_pdf | view_table | view_unsupported
    rel_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

Register the import in `app/eqms/models.py`’s bottom-of-file block so `Base.metadata` includes it for the schema-health gate.

### 7.2 Migration

`migrations/versions/<new_id>_add_auditor_access_events.py` creates `auditor_access_events` with the same column set plus indexes on `(user_id, created_at)` and `(rel_path)`. Do **not** add a separate index for `created_at` if you already index `(user_id, created_at)` — keep it lean.

### 7.3 Helper

```python
def record_access(
    s: Session, *, user: User | None, action: str, rel_path: str,
    file_size: int | None = None,
) -> None:
    from flask import request as _req, g as _g
    ev = AuditorAccessEvent(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        rel_path=rel_path,
        file_size=file_size,
        ip=_req.remote_addr if _req else None,
        user_agent=(_req.headers.get("User-Agent") or "")[:512] if _req else None,
        request_id=getattr(_g, "request_id", None),
    )
    s.add(ev)
    s.commit()
```

Call from every `/auditor/*` handler **after** serving the response is not an option (response is already sent). Call it **before** serving; commit immediately so rows are durable even on crash.

Also mirror each event coarsely to the existing `audit_events` table via `record_event(s, actor=user, action=f"auditor_portal.{action}", entity_type="AuditorFile", entity_id=rel_path[:128])` so the existing `/admin/audit` page surfaces auditor activity alongside everything else. Don’t duplicate fine-grained data — that’s what the new table is for.

### 7.4 Admin viewer UI

New template `app/eqms/templates/admin/auditor_access/list.html`. Structure mirrors `templates/admin/audit/list.html`: filter form on top (email contains, action dropdown, date from/to, rel_path contains), paginated table below (page size 100 by default, query param `page`). Export button links to `/admin/auditor-access-log/export` carrying the same filters. Add a new card to `templates/admin/index.html` under the **“QMS System”** column, gated by `has_perm("auditor_portal.admin")`:

```html
{% if has_perm("auditor_portal.admin") %}
<a class="card card--link dash-card" href="{{ url_for('admin.auditor_access_log_list') }}">
  <h3 class="dash-card-title">Auditor Access Log</h3>
  <p class="muted dash-card-desc">Records of files the external auditor has opened.</p>
</a>
{% endif %}
```

---

## 8. Seeding

Extend `scripts/init_db.py::seed_only` (idempotent — this runs on every deploy):

1. `p_auditor_access = ensure_perm("auditor_portal.access", "Auditor Portal: access")`.
2. `p_auditor_admin = ensure_perm("auditor_portal.admin", "Auditor Portal: admin log access")`.
3. Ensure `role_admin` has `p_auditor_admin` attached (use the existing `if p not in role_admin.permissions: role_admin.permissions.append(p)` pattern). **Do not** grant `auditor_portal.access` to admin by default — admins who want to preview the portal can be attached manually via the existing role-management tooling.
4. `role_auditor = s.query(Role).filter(Role.key == "auditor").one_or_none()`; create with `Role(key="auditor", name="Auditor")` if absent. Attach only `p_auditor_access`.
5. Seed user from env:
   ```python
   auditor_email = (os.environ.get("AUDITOR_EMAIL") or "").strip().lower()
   auditor_password = os.environ.get("AUDITOR_PASSWORD") or ""
   if auditor_email and auditor_password:
       u = s.query(User).filter(User.email == auditor_email).one_or_none()
       if not u:
           u = User(
               email=auditor_email,
               password_hash=generate_password_hash(auditor_password),
               is_active=True,
           )
           s.add(u)
           print(f"Seeded auditor user: {auditor_email}")
       else:
           print(f"Auditor user already exists: {auditor_email} — NOT overwriting password")
       if role_auditor not in u.roles:
           u.roles.append(role_auditor)
   else:
       print("AUDITOR_EMAIL / AUDITOR_PASSWORD not set — skipping auditor seed.")
   ```
   **Never** print the password value.

Also update `.env.example` with:
```
# Temporary Auditor Files portal
AUDITOR_PORTAL_ENABLED=0
AUDITOR_EMAIL=
AUDITOR_PASSWORD=
AUDITOR_FILES_ROOT=
AUDITOR_MAX_FILE_MB=50
AUDITOR_PDF_BACKEND=weasyprint
```
Comment that real values belong only in the deployment environment config, never in `.env` checked into git.

---

## 9. File layout to create

```
app/eqms/modules/auditor_portal/
    __init__.py                 # Blueprint("auditor_portal", __name__)
    admin.py                    # Route handlers (dashboard, browse, file)
    models.py                   # AuditorAccessEvent
    fs.py                       # ROOT resolution, _safe_resolve, listing helpers
    pdf_convert.py              # HTML→PDF + docx/xlsx→PDF + CachedPdfStore
    access_log.py               # record_access helper

app/eqms/templates/auditor_portal/
    base.html                   # Minimal chrome — NOT extends _layout.html
    dashboard.html
    folder.html
    file_not_viewable.html

app/eqms/templates/admin/auditor_access/
    list.html                   # Admin-facing access-log table

migrations/versions/
    <new_id>_add_auditor_access_events.py

tests/
    test_auditor_portal_paths.py
    test_auditor_portal_routes.py
    test_auditor_portal_pdf.py
    test_auditor_access_log.py
```

Modify:

- `app/eqms/__init__.py` — import and register `auditor_portal_bp` at `/auditor`; ensure it is gated by `AUDITOR_PORTAL_ENABLED` before anything else in its blueprint.
- `app/eqms/config.py` — add new config keys.
- `app/eqms/models.py` — add bottom-of-file import of `AuditorAccessEvent`.
- `app/eqms/auth.py::login_post` — factor `_post_login_redirect(user)` helper.
- `app/eqms/admin.py` — add `auditor_access_log_list` and `auditor_access_log_export` routes (permission `auditor_portal.admin`).
- `app/eqms/templates/admin/index.html` — add the Auditor Access Log card (gated).
- `app/eqms/templates/admin/document_viewer.html` — add optional `pdf_url` button block at the top (non-breaking: only renders if `pdf_url` is defined in context). All existing callers pass nothing and the button doesn’t appear for them.
- `scripts/init_db.py` — perms, role, user seed.
- `.env.example` — new keys.
- `requirements.txt` — `weasyprint==<pinned>` (and/or `xhtml2pdf==<pinned>`). Pin latest stable at time of implementation. If `weasyprint` requires apt packages that the existing `python:3.12-slim` Dockerfile doesn’t install, either: (a) add a minimal apt-get line to `Dockerfile` for `libpango-1.0-0 libpangoft2-1.0-0 libcairo2` etc., **or** (b) switch the default backend to `xhtml2pdf`. Do not silently fail in prod.

---

## 10. Template for `auditor_portal/base.html`

Use the same design-system.css; minimal top bar:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="csrf-token" content="{{ csrf_token }}">
    <title>{% block title %}Auditor Portal{% endblock %}</title>
    <link rel="icon" type="image/x-icon" href="{{ url_for('static', filename='favicon.ico') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='design-system.css') }}">
  </head>
  <body>
    <header class="topbar">
      <div class="container topbar__inner">
        <div class="brand">Silq eQMS — Auditor Portal</div>
        <nav class="topbar__nav">
          <a href="{{ url_for('auditor_portal.dashboard') }}">Home</a>
          {% if g.current_user %}
            <span class="muted">{{ g.current_user.email }}</span>
            <form method="POST" action="{{ url_for('auth.logout') }}" style="display:inline; margin:0;">
              <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
              <button type="submit" style="background:none;border:none;color:inherit;cursor:pointer;font:inherit;padding:0;text-decoration:underline;">Logout</button>
            </form>
          {% endif %}
        </nav>
      </div>
    </header>
    <main class="container">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="flash-stack">
            {% for category, message in messages %}
              <div class="flash flash--{{ category|e }}">{{ message }}</div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
```

**Deliberately excluded:** no link to `admin.index`, no `distribution_log`, `customers`, etc. The page never imports the admin nav.

---

## 11. Security hardening checklist

- [ ] `AUDITOR_PASSWORD` never appears in any response body, template, flash message, log line, or audit event.
- [ ] Path traversal rejected: unit tests cover `..`, `../../etc`, absolute paths, symlinks, Windows-style backslashes, percent-encoded `%2e%2e`.
- [ ] Feature flag off → every `/auditor/*` returns 404 (not an error page with portal chrome).
- [ ] Auditor role carries exactly `{"auditor_portal.access"}` — test asserts the set equality.
- [ ] Logged-in auditor (no admin.view) hitting `/admin`, `/admin/anything`, or any other admin blueprint returns 403.
- [ ] Existing admin user experience unchanged (regression test: admin can still reach `/admin/admin-docs/documents/<id>/view`).
- [ ] CSP `frame-src 'none'; object-src 'none'` is not regressed. PDFs are returned as `application/pdf` on their own URL — browser’s native viewer handles display without iframe/object.
- [ ] Cache keys for converted PDFs do not include user identity (same file, same bytes for any viewer).
- [ ] S3 `auditor-cache/pdf/*` objects are written with the same bucket and credentials — no separate bucket policy.
- [ ] File size over `AUDITOR_MAX_FILE_MB` short-circuits before conversion.
- [ ] Oversized Excel sheets truncate at 2000 rows with a banner.
- [ ] Mammoth HTML is passed through `_sanitize_html` before embedding (both viewer HTML and the HTML fed into the PDF conversion).
- [ ] `SECRET_KEY` strong-value check at app startup (already enforced by `create_app`) is not weakened.

---

## 12. Tests (pytest)

Conventions used in this repo: SQLite backing store via `script_session("sqlite:///:memory:")`; Flask test client from the `create_app()` factory with an override config. See `tests/test_rep_traceability.py` for a working example of how the suite spins up the engine.

### 12.1 `tests/test_auditor_portal_paths.py`

- `_safe_resolve` returns valid path under ROOT for clean input.
- `_safe_resolve` raises 404 for: `..`, `../../x`, absolute path `/etc/passwd`, Windows `\\..\\`, percent-encoded variants.
- Symlink escape is blocked (skip on Windows CI if necessary).

### 12.2 `tests/test_auditor_portal_routes.py`

Fixtures: `tmp_path` as ROOT, seed a tiny tree:
```
ROOT/
  Policies/
    policy.docx       (tiny valid docx)
    old_spec.doc      (legacy)
  Records/
    log.xlsx          (tiny valid xlsx)
    report.pdf        (tiny valid pdf)
```
Cases:
- Dashboard `/auditor/` lists `Policies` and `Records` tiles.
- `/auditor/browse/Policies` shows `policy.docx` and `old_spec.doc`.
- `GET /auditor/file/Records/report.pdf` returns `Content-Type: application/pdf` and `Content-Disposition: inline`.
- `GET /auditor/file/Policies/policy.docx` returns HTML with the file’s text content.
- `GET /auditor/file/Policies/policy.docx?as=pdf` returns PDF bytes starting with `%PDF-`.
- `GET /auditor/file/Records/log.xlsx` returns PDF by default.
- `GET /auditor/file/Records/log.xlsx?as=table` returns HTML with table rows.
- `.doc` returns the not-viewable page.
- No-permission user hitting any route → 403.
- Feature flag off → 404 on all routes.
- Admin-only user hitting `/auditor/` → 403.
- Auditor-only user hitting `/admin` → 403.

### 12.3 `tests/test_auditor_portal_pdf.py`

- `html_to_pdf_bytes` returns bytes starting with `%PDF-` for the selected backend.
- Cache: first call writes to S3-stub; second call reads without re-converting (monkeypatch the conversion to raise; second call still succeeds).
- Cache invalidates when `mtime_ns` changes.

### 12.4 `tests/test_auditor_access_log.py`

- Each auditor route call produces exactly one `AuditorAccessEvent` row with expected `action` and `rel_path`.
- `/admin/auditor-access-log` renders events; filter by action narrows results.
- `/admin/auditor-access-log/export` returns `text/csv` with correct header row.

All tests must pass locally with `pytest`. Note: the full-app SQLite `create_all` path has existing JSONB issues in some environments (see pre-existing `tests/test_rep_traceability.py`) — **do not** rewrite the global test infra to fix that; isolate this suite via targeted fixtures that construct just the minimum schema (`users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `audit_events`, `auditor_access_events`) with Alembic `op.create_table`-style direct calls or `Base.metadata.create_all(engine, tables=[...])`.

---

## 13. Acceptance criteria

1. With `AUDITOR_PORTAL_ENABLED=1`, `AUDITOR_EMAIL` / `AUDITOR_PASSWORD` set, and `AUDITOR_FILES_ROOT` pointing at a populated directory:
   - Login with auditor creds → lands on `/auditor/`.
   - Dashboard shows tiles matching immediate subfolders.
   - Opening any PDF renders inline; any `.docx` renders as HTML with a visible “View PDF version” button; `.xlsx` renders as PDF with a “View as table” link.
   - Trying to visit `/admin` or any admin URL → 403 page.
   - Admin (distinct session) can visit `/admin/auditor-access-log`, see each access row, filter, and export CSV.
   - `alembic upgrade head` runs cleanly on a fresh DB and on the existing prod schema.
2. With `AUDITOR_PORTAL_ENABLED` unset/`0`:
   - Every `/auditor/*` returns 404.
   - The admin access-log page renders an empty state (or a notice).
   - No route breaks for existing admin users.
3. `pytest` passes the four new suites.
4. No hard-coded secrets. No changes to sessions / CSRF / CSP headers for non-auditor routes. No new dependencies beyond the chosen PDF backend (and its system libs via Dockerfile if `weasyprint`).

---

## 14. Open decisions left to implementer (defaults in the prompt; stakeholder may revise)

1. **Legacy `.doc`** — treat as “re-save as `.docx`.” No converter dependency.
2. **Excel → PDF** — portrait A4, first 2000 rows per sheet with a banner, each sheet on its own page.
3. **Cache invalidation** — `(rel_path, size, mtime_ns)`. If the operator replaces files with identical size/mtime, they won’t see the new content until cache expiry. Document this in the module `__init__.py` docstring and the admin log page footer.
4. **Pagination of access log** — 100 rows/page default; `?page=` query param.

---

## 15. Deliverables summary

- New module `app/eqms/modules/auditor_portal/` + templates.
- Minimal edits to `__init__.py`, `config.py`, `auth.py`, `admin.py`, `models.py`, `scripts/init_db.py`, `templates/admin/index.html`, `templates/admin/document_viewer.html`.
- One Alembic migration adding `auditor_access_events`.
- New dependency pinned in `requirements.txt` (WeasyPrint or xhtml2pdf). If WeasyPrint, a focused `Dockerfile` patch adding the runtime libs.
- Four new test modules, all green.
- `.env.example` updated.
- A short operator note appended to `MANIFEST.md` explaining how to enable/disable after the audit.
- PR body summarizing: what changed, what was intentionally not changed, how to roll back (flip `AUDITOR_PORTAL_ENABLED=0` and the portal disappears; revoke the auditor user via the existing admin UI).

*End of prompt.*
