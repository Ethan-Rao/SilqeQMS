# Dev agent prompt: temporary “Auditor Files” read-only portal

**Goal:** Add a **small, isolated** area of the eQMS web app so an **external/internal auditor** can log in and **browse** materials you place under a dedicated folder tree (**`Auditor Files/`** at the repository root, or a configurable absolute path). The experience should **resemble the admin dashboard** (card grid) where **each card is a subfolder** of that root. The auditor is **read-only**: no edits to QMS records in the main system; scope is **only** the files you copy into this folder.

**Explicit non-goals:** No access to distribution log, document control module data, ShipStation, customer DB, sales orders, or any existing admin feature **unless** you deliberately reuse shared login infrastructure (Flask session) with **strict permission isolation** (recommended).

---

## 1. Product answers (from stakeholder — fill gaps marked TBD)

| Item | Decision |
|------|-----------|
| **Content root** | Operator-maintained folder **`Auditor Files/`** (subfolders = dashboard cards; more subfolders may be added over time). Support a configurable path (env var) so production can point outside the repo. |
| **File types** | **PDF, Word (.doc/.docx), Excel (.xls/.xlsx)** — auditor must be able to **view** content; editing not required. |
| **Download** | **Not required** as a product feature; **no need to hard-block** downloads if the browser receives bytes for preview. |
| **Isolation** | Subsystem must be **logically separate**: auditor identity must **not** receive permissions used elsewhere; navigation must not expose other modules. |
| **Credentials** | Intended auditor email: **`stephen.medreg@gmail.com`**. **Initial password must NOT be committed to git or stored in markdown.** Supply at deploy time via environment variables (see §6). |
| **Lifetime** | **Temporary** component — implement behind a **feature flag** so it can be turned off without redeploying code (optional but strongly recommended). |

### TBD — confirm with stakeholder before locking viewer UX

1. **Office formats in-browser:** True in-browser rendering of Word/Excel without a third-party document service is limited. Pick one approach for v1 and document trade-offs:
   - **A)** Server-side conversion to **PDF** on upload or on first view (deterministic preview; extra dependencies).
   - **B)** **Inline PDF only**; for Office, show metadata + “open” using `Content-Disposition: inline` where the browser allows (often still downloads or opens externally).
   - **C)** Integrate an external viewer (Microsoft Office Online / Google Docs) — usually requires **publicly reachable URLs** or enterprise agreements — **likely unacceptable** for confidential QMS copies unless approved.

**Default recommendation for v1:** **PDF** = inline `send_file` with `as_attachment=False` where safe; **Office** = best-effort inline + clear fallback message, **or** (A) if product approves conversion pipeline.

2. **Access logging:** Log each **folder open** and **file view** (filename, path relative to root, timestamp, user id) to **`audit_events`** or a dedicated lightweight table — **recommended** for internal audit defensibility.

---

## 2. Security and compliance (mandatory)

1. **Secrets:** Do **not** hard-code the auditor password in source, fixtures, or docs. Use **`AUDITOR_SEED_EMAIL`** / **`AUDITOR_SEED_PASSWORD`** (or similar) read **only** by `scripts/init_db.py` (or a one-off `scripts/seed_auditor.py`) in deployment environments. After handoff, **rotate** the password if it was ever shared in chat/email logs.
2. **Path traversal:** Resolve the real root with `Path(...).resolve()`; every requested subpath must be **`relative_to(root)`** validated — reject `..`, absolute paths, and symlinks escaping the root if feasible.
3. **Authorization:** A dedicated permission key, e.g. **`auditor_portal.access`**, attached **only** to a dedicated **`auditor`** role (or equivalent). No other permissions for that role.
4. **Post-login routing:** If `current_user` has only auditor permission(s), **`/` or `/admin` should redirect** to the auditor dashboard — avoid accidental exposure of admin shell links.
5. **HTTPS:** Assume production TLS; never send seed passwords over HTTP in production.
6. **Rate limiting / lockout (optional):** Basic Flask-limiter or failed-login backoff if trivial to add without new infra.

---

## 3. UX specification

1. **Login:** Reuse existing **email + password** login **or** a dedicated **`/auditor/login`** page that still authenticates against `User` — either is fine if isolation holds. Prefer **one login page** with **role-based redirect** to reduce confusion.
2. **Dashboard (`/auditor` or `/auditor/`):**
   - Layout visually consistent with **admin dashboard cards** (reuse CSS tokens / card components where possible).
   - **One card per immediate child directory** under the content root (non-recursive for the top level).
   - Card title = folder name; optional subtitle = file count (non-recursive or recursive — pick one and document).
3. **Folder view:** Clicking a card lists **files** in that folder (one level, or recursive with breadcrumbs — **pick one**; recommend **one level per route** + breadcrumbs for clarity).
4. **File view:**
   - **PDF:** Browser inline view (`send_file`, correct `mimetype`).
   - **Word/Excel:** Per §1 TBD; at minimum, do not execute macros — serve as static files with safe mimetype or converted PDF.
5. **No edit controls** in templates for this portal.

---

## 4. Technical implementation plan

### 4.1 Configuration

- Env var **`AUDITOR_FILES_ROOT`**: absolute path to the folder (default: `<repo_root>/Auditor Files` if present).
- Env var **`AUDITOR_PORTAL_ENABLED`**: if `0`/`false`, return **404** for all auditor routes (or disable blueprint registration).

### 4.2 Module layout (suggested)

- New blueprint: `app/eqms/modules/auditor_portal/` with `admin.py` (routes), `service.py` (filesystem listing, safe path join), `templates/auditor_portal/*.html`.
- Register blueprint with prefix **`/auditor`** (or `/auditor-portal`) in `app/eqms/__init__.py` behind the feature flag.

### 4.3 RBAC

- Add permission **`auditor_portal.access`** in `scripts/init_db.py` (idempotent `ensure_perm`).
- Add role **`auditor`** with **only** that permission (plus nothing else).
- Seed user when env vars set (same pattern as admin seeding): create user if missing; **do not overwrite password** if user already exists (mirror admin behavior).

### 4.4 Routes (minimum)

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/auditor/` | Dashboard of subfolder cards (requires `auditor_portal.access`) |
| GET | `/auditor/f/<path:rel_path>` | List folder contents OR show file — **prefer separate list vs view routes** e.g. `/auditor/browse/...` and `/auditor/file/...` |
| GET | `/auditor/file/<path:rel_path>` | Stream file for view/inline per mimetype rules |

Use `require_permission("auditor_portal.access")` on all routes.

### 4.5 Navigation isolation

- Auditor templates: **minimal chrome** (logo, logout, no links to `/admin` modules).
- Optional: middleware or `@app.before_request` to **block** users who **only** have auditor role from hitting `/admin/*` URLs (return 403) — defense in depth beyond missing permissions on individual routes.

### 4.6 Upload path for operators

- **Out of scope for auditor UI:** only Silq staff place files on disk (or SFTP). Document in `MANIFEST.md` or existing ops doc: “Copy requested QMS copies into `Auditor Files/<Subfolder>/`.”

### 4.7 Tests

- Unit tests for **path canonicalization** (reject traversal).
- Integration test with **temporary directory** fixture: two subfolders, mixed file types, GET dashboard lists cards, GET file returns 200 for allowed file.
- Test that user **without** `auditor_portal.access` cannot access `/auditor/...`.

---

## 5. Deliverables

1. Code + templates + RBAC + optional feature flag.
2. `scripts/init_db.py` (or companion script) updated for permission/role/user seeding via env.
3. `.env.example` keys documented (**no real passwords**).
4. Short operator note: folder layout, how to enable flag, how to seed auditor, how to disable after audit.

---

## 6. Handoff values (ops — not committed)

Set in the deployment environment (example names):

```bash
AUDITOR_PORTAL_ENABLED=1
AUDITOR_FILES_ROOT=/var/silq/auditor-files   # or repo path
AUDITOR_SEED_EMAIL=stephen.medreg@gmail.com
AUDITOR_SEED_PASSWORD=<use strong secret; communicate out-of-band>
```

**Do not** paste production passwords into GitHub issues, commits, or this repository.

---

## 7. Open questions for stakeholder (non-blocking for spike)

1. Should **subfolder names** or **filenames** ever be considered confidential on screen (e.g. watermarked “CONFIDENTIAL — INTERNAL AUDIT”)?
2. Maximum file size / total folder size guardrails?
3. Should the auditor see **version history** if you replace a file with the same name (probably no — OS filesystem is source of truth)?

---

*End of prompt.*
