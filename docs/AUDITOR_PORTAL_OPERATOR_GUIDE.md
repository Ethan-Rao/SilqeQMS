# Auditor Files Portal — operator guide

> **Status:** code and migration shipped on `main` (commit `e601a32`). This guide lists every remaining action the operator needs to take to go live and to keep the portal fed with documents.

## 1. One-time cutover

Complete these **in DigitalOcean** before the auditor logs in.

### 1.1 Set / confirm env vars

In DigitalOcean App Platform → your app → **Settings → App-level env vars**, confirm these are present:

| Var | Value | Purpose |
|-----|-------|----------|
| `AUDITOR_EMAIL` | `stephen.medreg@gmail.com` (or your chosen auditor email) | Seed email; lower-cased on seed. |
| `AUDITOR_PASSWORD` | (strong new password — see §1.2) | Seeded once; never overwritten. |
| `AUDITOR_PORTAL_ENABLED` | `1` | Gate for every `/auditor/*` route. `0` or unset → portal returns 404 everywhere. |
| `AUDITOR_FILES_ROOT` | *(leave unset)* | Defaults to `/app/Auditor Files` in the container, which is where `Auditor Files/` in this repo ends up. Only set this if you choose a custom mount. |
| `AUDITOR_MAX_FILE_MB` | `50` (default) | Per-file size cap for in-browser preview. |
| `AUDITOR_PDF_BACKEND` | `xhtml2pdf` (default) | HTML→PDF engine. Do not change unless you add the WeasyPrint system libs to the Docker image. |

### 1.2 Rotate the credentials shared in chat

The following were exposed in design chat and should be rotated **before** the auditor uses the portal:

- `AUDITOR_PASSWORD` — pick a new strong value.
- `SECRET_KEY` (Flask session signer).
- DigitalOcean Spaces access key pair (`S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY`).
- ShipStation API key / secret.
- DigitalOcean managed-DB password in `DATABASE_URL`.

### 1.3 Confirm the deploy runs migrations and seeds

Production already runs:

- `alembic upgrade head` — applies `u3v4w5x6y7z8_add_auditor_access_events` to create `auditor_access_events`.
- `python scripts/init_db.py` (idempotent) — creates the `auditor` role, attaches `auditor_portal.access`, grants admin the `auditor_portal.admin` perm, and creates the auditor user from `AUDITOR_EMAIL` / `AUDITOR_PASSWORD` **if the user row does not exist**. Existing users’ passwords are never overwritten.

If your DO deploy pipeline does **not** include these two steps, add them as a **pre-deploy command** in the DO console:

```sh
alembic upgrade head && python scripts/init_db.py
```

### 1.4 Smoke-test the auditor login (you, not the auditor)

1. Open an incognito window to `https://silqeqms.com/auth/login`.
2. Sign in with `AUDITOR_EMAIL` + `AUDITOR_PASSWORD`.
3. You should land at `/auditor/` — not `/admin/`.
4. Visit `https://silqeqms.com/admin/` — should return **403** (auditor-only users are blocked).
5. Log out and confirm redirect.
6. Log back in as the admin, go to **Admin → Auditor Access Log**. You should see rows for the smoke-test above.

If any step fails, leave `AUDITOR_PORTAL_ENABLED=0` and flag the issue.

---

## 2. Day-to-day workflow (you ↔ me)

### 2.1 Adding files

1. You drop files into local `Auditor Files/<subfolder>/…` on your machine.
2. Tell me **“push the Auditor Files update”** (or similar).
3. I will run `git add "Auditor Files/"`, commit, and push. DigitalOcean will auto-rebuild and redeploy.
4. After the deploy finishes, the auditor sees the new files in the portal.

### 2.2 Folder structure inside `Auditor Files/`

- Each **immediate subfolder** of `Auditor Files/` becomes a tile on the auditor dashboard.
- Nested subfolders appear when the auditor drills into a tile.
- Supported file types for in-browser preview: `.pdf`, `.docx`, `.xlsx`, `.xls`, `.csv`, `.txt`, `.png`, `.jpg`, `.jpeg`, `.gif`.
- Unsupported types (including legacy `.doc`) show a “cannot preview” page.
- Files larger than `AUDITOR_MAX_FILE_MB` (default 50) show a size-limit page.

### 2.3 Replacing a file

Drop the new copy over the old file (same name and path). Git tracks the change; redeploy refreshes it. The PDF cache is keyed by `(rel_path, size, mtime)`; redeploy invalidates it automatically.

### 2.4 Removing access after the audit

Either:

- **Fastest:** set `AUDITOR_PORTAL_ENABLED=0` in DO env and redeploy. Every `/auditor/*` returns 404 immediately; the auditor user and files remain but are unreachable.
- **Permanent:** also disable the auditor user via `/admin/diagnostics` (or delete from the DB) and remove `Auditor Files/` from the repo (`git rm -r`) when done.

---

## 3. `.gitignore` note

`.gitignore` has a global `*.pdf` / `*.docx` / `*.xlsx` ignore (used by other upload workflows in this repo). The Auditor Files portal overrides that with:

```
!Auditor Files/
!Auditor Files/**
```

so anything you drop into `Auditor Files/` is tracked. Do **not** remove that override while the audit is in progress.

---

## 4. What the admin sees

- `/admin/auditor-access-log` — filterable table of every folder / file the auditor opens (action, path, size, timestamp, IP, user-agent).
- **Export CSV** button on the same page.
- A summary card on the admin dashboard (visible only when you have the `auditor_portal.admin` permission — admins have it by default after seeding).
- Coarse events (`auditor_portal.view_*`) are **also** written to the general audit log at `/admin/audit`, so the main audit trail surfaces auditor activity.

---

## 5. Files you will **not** have to touch

- The portal blueprint (`app/eqms/modules/auditor_portal/`).
- The Alembic migration.
- `scripts/init_db.py`.
- `requirements.txt` / `Dockerfile`.
- The dev-agent prompt at `docs/DEV_AGENT_PROMPT_AUDITOR_FILES_PORTAL.md` — kept as a record of product decisions; can be archived or deleted after the audit.

---

## 6. Open questions to close before the auditor logs in

1. Is `AUDITOR_PORTAL_ENABLED=1` set in DO? *(Not set yet per current env vars shown in chat.)*
2. Are the exposed credentials in §1.2 rotated?
3. Did the post-deploy `alembic upgrade head` + `python scripts/init_db.py` run successfully? *(Confirm by checking DO deploy logs for the strings “Seeded auditor user” or “Auditor user already exists”.)*

Once those three are done you can flip `AUDITOR_PORTAL_ENABLED` to `1`, redeploy, and hand credentials to the auditor.
