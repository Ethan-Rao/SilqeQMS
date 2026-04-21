# Dev agent prompt: temporary Auditor Files portal (read-only)

**Status:** NEW module. No existing auditor code. Parallel to but isolated from the main admin system. **Do not change** any existing admin module routes/permissions unless explicitly required here.

---

## 1. Product summary

- An **internal/external auditor** logs in and browses **QMS files we place under a controlled folder**. They must be able to **see content** of every file type we load, without leaving the app.
- **Dashboard** = card grid, **one card per immediate subfolder** of the root, styled to match the existing admin dashboard.
- **File types:** `.pdf`, `.docx`, `.doc` (best-effort), `.xlsx`, `.xls`, plus common images/csv if they show up.
- **Editing:** disabled. **Download:** no explicit UI button, but the system doesn’t need to hard-block downloads the browser performs.
- **Isolation:** auditor identity sees **only** the Auditor Files portal. No access to distribution log, doc control, sales, ShipStation, or other admin modules.
- **Temporary:** ship behind a feature flag so it can be turned off after the audit.

---

## 2. Credentials and secrets (critical)

Environment variables are **already set in DigitalOcean App Platform**. Use **exactly these names** (do **not** rename to `AUDITOR_SEED_*`):

| Env var | Meaning |
|--------|----------|
| `AUDITOR_EMAIL` | Auditor login (seed if missing; never overwrite existing user password). |
| `AUDITOR_PASSWORD` | Initial password, seeded at startup/seed script; **never** log, template, or commit. |
| `AUDITOR_FILES_ROOT` *(new)* | Absolute path to the Auditor Files root. Default if unset: `<repo_root>/Auditor Files`. |
| `AUDITOR_PORTAL_ENABLED` *(new)* | `1`/`true` to enable; otherwise routes respond **404**. |

**Do NOT:** commit passwords, print them in logs, render them in templates, or reference them in tests. The portal must never emit `AUDITOR_PASSWORD` through any endpoint.

**Operator note:** Credentials shared during design review were exposed in chat and should be **rotated** before the auditor uses them.

---

## 3. Non-negotiable isolation rules

1. New **permission key** `auditor_portal.access` (and `auditor_portal.admin` if admin needs to view the access log; see §7).
2. New **role** `auditor` — carries **only** `auditor_portal.access`. No inheritance from other roles.
3. Admin users (existing `admin` role) gain **`auditor_portal.admin`** via seed for the access-log viewer (see §7). They do **not** gain `auditor_portal.access` automatically; admins can visit the portal only if explicitly given that perm — optional.
4. **Post-login redirect:** a user whose **only** permission is `auditor_portal.access` must be redirected to **`/auditor/`** on login or when hitting `/`, `/admin`, or `/admin/*`. Return **403** on direct hits to admin URLs by auditor-only users (defense in depth in addition to per-route `require_permission`).
5. **Navigation chrome:** auditor templates must not link to `/admin/*` endpoints. No admin sidebar/top-nav on auditor pages.
6. Auditor portal must **not** query or expose `DistributionLogEntry`, `SalesOrder`, `Customer`, `Document` (doc control), etc. Its only data source is the filesystem under `AUDITOR_FILES_ROOT` plus its own audit log table.

---

## 4. Filesystem contract

- Root: `AUDITOR_FILES_ROOT` (absolute). Resolve once at app start: `ROOT = Path(env).resolve()`; abort startup with a clear log message if not a directory (but don’t crash non-auditor routes — just disable the portal).
- **Directory layout:**
  - `<root>/<SubfolderA>/…files…`
  - `<root>/<SubfolderB>/<maybe nested>/…files…`
  - Operators will add more subfolders over time.
- **Supported file extensions** (lowercased): `.pdf`, `.docx`, `.doc`, `.xlsx`, `.xls`, `.csv`, `.txt`, `.png`, `.jpg`, `.jpeg`, `.gif`.
- **Ignored:** hidden files (`.*`), `~$*.docx` Office lock files, files > configurable size limit (default 50 MB — env `AUDITOR_MAX_FILE_MB`).
- **Path safety:** every requested path must be canonicalized with `Path(ROOT, rel_path).resolve()` and then verified via `resolved.is_relative_to(ROOT)`. Reject symlinks that escape the root. Return 404 on failure — never 500, never leak the real path.

---

## 5. Viewer spec (reuse existing pattern)

Use the existing centralized viewer: **`app/eqms/document_viewer.py`** — it already ships **mammoth** (docx → HTML) and **openpyxl** (xlsx/xls → HTML tables) and renders via **`templates/admin/document_viewer.html`**. See `app/eqms/modules/admin_docs/admin.py::admin_docs_document_view` for the canonical integration the user referenced (`/admin/admin-docs/documents/<id>/view`).

**Per file type in the auditor portal:**

| Extension | In-browser primary view | Extra button |
|-----------|---------------------------|---------------|
| `.pdf` | **Inline PDF** via `send_file(..., as_attachment=False)` + correct `mimetype="application/pdf"`. | — |
| `.docx` | **HTML text view** via `render_document_to_response` (mammoth). | **“View PDF version”** button → `/auditor/file/<rel>?as=pdf` (server converts HTML → PDF, see §6). |
| `.xlsx` / `.xls` | **PDF version shown automatically** (per product requirement “pdfs/excels can automatically be pdfs”). A “View as table” toggle/link that falls back to the existing HTML-table render is acceptable and recommended for large spreadsheets that don’t paginate well. | — |
| `.csv`, `.txt` | Simple monospaced HTML view (reuse existing CSV renderer if straightforward). | Optional PDF version. |
| `.doc` (legacy) | Mammoth **cannot** parse legacy `.doc`. Show a clear message: “Legacy .doc format — please re-save as .docx.” Log the event. **Do not** add a binary converter for legacy `.doc` (out of scope). | — |
| Images (`.png/.jpg/.jpeg/.gif`) | Inline `<img>` via `send_file`. | — |

Use the existing **HTML sanitization** already present in `document_viewer.py` (`_sanitize_html`) for mammoth output. Do not bypass it.

---

## 6. Server-side PDF conversion pipeline (new; no third-party services)

We need `.docx` and `.xlsx/.xls` to be viewable as PDF in the browser. Constraints from the stakeholder: **no third-party SaaS** (so no Office Online, no Google Docs).

**Pipeline (pure-Python):**

1. **DOCX → HTML** via existing `mammoth` conversion in `document_viewer.py` (already sanitized).
2. **XLSX/XLS → HTML** via existing `openpyxl` path (HTML tables — reuse `_render_excel`/`_spreadsheet_response` minus the HTTP response: factor a function that returns HTML string).
3. **HTML → PDF** via **`weasyprint`** (preferred) or **`xhtml2pdf`** (fallback if `weasyprint` system libs cannot be installed on the DO App Platform image).
   - Add to `requirements.txt` (pin a version). If choosing `weasyprint`, confirm it installs on the current buildpack/Dockerfile; if not, switch to `xhtml2pdf` without blocking.
   - Do **not** add `wkhtmltopdf` (external binary) or `libreoffice` (heavy system dep) unless the simpler pure-Python options are proven inadequate and the stakeholder is consulted.
4. **Caching converted PDFs:** to avoid reconverting on every auditor click, cache the PDF bytes keyed by **(relative path + file size + mtime)**:
   - **Storage layer:** write cached PDF to S3/Spaces (`STORAGE_BACKEND=s3`) under a dedicated prefix **`auditor-cache/pdf/…`** so it does not collide with existing `sales_orders/…` keys. Invalidate cache entry when mtime/size changes.
   - **In-process guard:** use a short (e.g. 60 s) in-memory LRU cache for the last few conversions to cushion quick re-views.
5. **Response:** `send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=False, download_name=<original_name>.pdf, max_age=0)`.

**Failure modes:** if conversion raises, log at warning level, **do not 500**. Return the text-based view (for docx) or the HTML-table view (for xlsx) with a flash: “PDF view is temporarily unavailable; showing text/table view.”

---

## 7. Access logging (admin-visible)

**Requirement:** the admin can see what the auditor has opened.

1. **New table** (small, focused): `auditor_access_events`
   - `id` (int PK)
   - `user_id` (FK `users.id`, nullable for future)
   - `user_email` (string snapshot)
   - `action` (string — `view_folder`, `view_file`, `view_pdf`, `download` — use `download` if a download URL is ever exposed)
   - `rel_path` (string — relative to `AUDITOR_FILES_ROOT`)
   - `file_size` (int, nullable)
   - `ip` (string, nullable)
   - `user_agent` (string, nullable)
   - `created_at` (UTC datetime)
   - Alembic migration required; index on `(user_id, created_at)` and `(rel_path)`.
2. **Every** `/auditor/*` file/folder access writes one row (use a helper; batch writes are not necessary).
3. **Admin page:** `GET /admin/auditor-access-log` — simple table with filters (user_email contains, action, date_from/date_to, rel_path contains) and **CSV export** (`/admin/auditor-access-log/export`). Gate with `auditor_portal.admin`. Reuse the audit-list template pattern from `templates/admin/audit/list.html`.
4. **Nav link:** add an “Auditor Access Log” card on the admin dashboard (`templates/admin/index.html`) visible only to users with `auditor_portal.admin`.
5. **Also** append a coarse-grained `auditor_portal.access` entry to the global `audit_events` table on login/logout (via the existing `record_event`) so the standard audit list surfaces auditor sessions.

---

## 8. Routes (summary)

All under the blueprint prefix **`/auditor`**, feature-gated by `AUDITOR_PORTAL_ENABLED`:

| Method | Path | Permission | Purpose |
|--------|------|------------|----------|
| GET | `/auditor/` | `auditor_portal.access` | Dashboard: one card per top-level subfolder of `AUDITOR_FILES_ROOT`. Card title = folder name; subtitle = file count (non-recursive). |
| GET | `/auditor/browse/<path:rel_path>` | `auditor_portal.access` | Folder listing with breadcrumbs (files + subfolders at that depth). |
| GET | `/auditor/file/<path:rel_path>` | `auditor_portal.access` | Primary view per §5. Supports `?as=pdf` to force PDF conversion when applicable. |
| GET | `/auditor/login` | — | Dedicated login page for auditor (optional; may reuse global `/login` with role-based redirect). |
| GET | `/admin/auditor-access-log` | `auditor_portal.admin` | Admin log viewer (see §7). |
| GET | `/admin/auditor-access-log/export` | `auditor_portal.admin` | CSV export of filtered log. |

Templates:

- `templates/auditor_portal/base.html` (minimal chrome: logo, greeting, logout, nothing else)
- `templates/auditor_portal/dashboard.html`
- `templates/auditor_portal/folder.html`
- `templates/auditor_portal/file_not_viewable.html` (for legacy `.doc` etc.)
- Reuse `templates/admin/document_viewer.html` for docx/xlsx HTML views (do not duplicate; pass a `back_url` pointing at the originating folder).

---

## 9. Seeding and migrations

1. **Alembic migration:** create `auditor_access_events` table.
2. **`scripts/init_db.py`** additions (idempotent):
   - `ensure_perm("auditor_portal.access", "Auditor Portal: access")`
   - `ensure_perm("auditor_portal.admin", "Auditor Portal: admin log access")`
   - Ensure role `auditor` exists; role has only `auditor_portal.access`.
   - Ensure role `admin` has `auditor_portal.admin` added (keep all existing perms).
   - Seed **auditor user** from `AUDITOR_EMAIL` / `AUDITOR_PASSWORD` if the env vars are set:
     - If user doesn’t exist: create with hashed password, assign **only** role `auditor`, `is_active=True`.
     - If user exists: **do not overwrite password or roles**; ensure `auditor` role is attached; log a notice.
   - Under no circumstance log the password value.
3. **`.env.example`:** add `AUDITOR_EMAIL=`, `AUDITOR_PASSWORD=`, `AUDITOR_FILES_ROOT=`, `AUDITOR_PORTAL_ENABLED=0` with empty/placeholder values and a comment “do NOT commit real values”.

---

## 10. Security and hardening checklist

- [ ] Path traversal rejected (see §4).
- [ ] Feature flag disables **all** `/auditor/*` routes with 404 (not just empty pages).
- [ ] Auditor role carries no other permissions; integration test asserts this.
- [ ] `/admin/*` returns 403 for users whose only role is `auditor`.
- [ ] Templates never render `AUDITOR_PASSWORD` or any env secret.
- [ ] Converted PDF cache uses the authenticated request path only; cache keys don’t leak across users (they’re filesystem-pathed, so same content is shared — acceptable for single auditor).
- [ ] Mammoth HTML passes `_sanitize_html` before insertion into the viewer template (already implemented upstream — do not regress).
- [ ] File size cap enforced before attempting conversion (OOM protection on large xlsx).
- [ ] XLSX conversion paginated or truncated sensibly (warn “showing first N sheets/rows” rather than crash).
- [ ] S3 `auditor-cache/pdf/*` keys are write-read by the app role only; no public ACL.
- [ ] Rate limiting (optional): per-IP failed-login delay for `/auditor/login` or the global login.

---

## 11. Tests

Add under `tests/` (do not modify unrelated suites):

- `tests/test_auditor_portal_paths.py` — path traversal unit tests (various `../` and absolute-path inputs return 404).
- `tests/test_auditor_portal_routes.py` — with a `tmp_path` fixture as `AUDITOR_FILES_ROOT`:
  - Dashboard lists the subfolders.
  - PDF route returns `application/pdf` with `Content-Disposition` inline.
  - DOCX route renders HTML text; `?as=pdf` returns a `application/pdf` body.
  - XLSX route returns PDF by default; `?as=table` returns HTML.
  - Unknown file type returns the not-viewable page.
  - User without `auditor_portal.access` gets 403.
  - Feature flag off → 404 on all `/auditor/*` endpoints.
- `tests/test_auditor_access_log.py` — log row created on each access; admin log endpoint lists entries; CSV export returns rows.

Document how to run against SQLite for local dev.

---

## 12. Deliverables

- New blueprint module under `app/eqms/modules/auditor_portal/` (admin.py, service.py, templates/…).
- New Alembic migration.
- Updates to `scripts/init_db.py`, `.env.example`, `requirements.txt` (add `weasyprint` or `xhtml2pdf`; pinned).
- New admin log view page under existing admin blueprint, linked conditionally on the admin dashboard.
- Tests per §11, all green.
- Short operator note appended to `MANIFEST.md` (or existing ops doc): env vars, how to enable, how to disable after audit.

**Do not commit any secrets.** Passwords and API keys stay in DigitalOcean env config only.

---

## 13. Open questions (non-blocking; document your defaults if stakeholder is unavailable)

1. **DOC (legacy)** files: we are treating these as “please re-save as .docx.” Confirm OK or add a conversion dependency (out of current scope recommendation).
2. **Spreadsheet PDF layout:** large workbooks (many sheets, wide tables) will look ugly in PDF regardless of renderer. Default: portrait A4, autosize columns up to a cap, truncate to first 2000 rows per sheet with a banner — OK?
3. **PDF cache invalidation:** current plan uses `mtime+size`. If files are replaced atomically (same name, same size, different content) within one second, cache could stale. Add content hash if stakeholder flags it.

---

*End of prompt.*
