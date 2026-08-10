# Dev Agent Prompt 6 — Staff Dashboard Parity + Dashboard Search Bar

**Type:** Standalone, self-contained work order. Complete all tasks, then deploy.
**Owner:** Ethan (sole QA/RA/R&D, SILQ Technologies) — the coordinator reviews your output.
**Do not** open-endedly refactor beyond this scope. This prompt is intentionally bounded.

---

## 0. Context you need (read these first)

- App: Flask + SQLAlchemy modular monolith ("Silq eQMS"), deployed on DigitalOcean App
  Platform. Push to `main` → auto-build → `scripts/start.py` runs `release.py`
  (alembic upgrade + idempotent seed) → gunicorn. A green deploy ends with
  `=== SilqQMS release done ===` then gunicorn `Listening at ...` and `/healthz` 200.
- Live prod is currently **healthy** on commit `8249067`. Checkpoints 3, 4, and E1 are live.
- RBAC: `User` ↔ `Role` ↔ `Permission`. Helpers: `user_has_permission`,
  `user_has_any_permission`, template globals `has_perm(...)` / `has_any_perm(...)`.
- Files central to this work order:
  - `app/eqms/templates/admin/index.html` — the dashboard (4-column card grid).
  - `app/eqms/templates/_layout.html` — topbar; `Search` link is at ~line 26,
    gated by `has_perm("admin.view")`.
  - `scripts/init_db.py` — role/permission seeding (idempotent, re-runs every deploy).
  - `app/eqms/search.py` — `search.global_search`, a **GET** route at `/admin/search`
    reading `request.args.get("q")`.
  - Admin Tools account management (under the `admin` blueprint / diagnostics area).

---

## Task A — Retire the `readonly` role; consolidate to `admin` + `staff` (+ `auditor`)

**Confirmed root cause of the "staff view unchanged" report:** The `staff` role is seeded
correctly (in `init_db.py` the `staff` role already carries `admin.view`,
`docs.view/download`, and every operational + external module `*.view`/`*.export`, plus
`training.view`). The dashboard renders operational/external cards gated on those specific
perms. However, the real team account `silqrepservice@gmail.com` is assigned the **legacy
`readonly`** role (defined as only `{admin.view, docs.view}`), so it only sees the
`admin.view`/`docs.view` cards. **The account is on an outdated role — the code is fine.**

**Decision (from Ethan):** The `readonly` role is outdated and redundant with `staff`.
**Delete the `readonly` role entirely.** Internal personas going forward are exactly
**`admin`** (full) and **`staff`** (full read-only). **Keep the `auditor` role** — it backs
the external auditor portal and the live `stephen.medreg@gmail.com` account; do NOT remove
it. (If Ethan later wants auditor gone too, that will be a separate instruction.)

**Intent:** Every SILQ employee account (non-admin) uses the **`staff`** role and sees the
*entire* dashboard — Quality Management, Silq Operations, External Relationships, and QMS
System — in **read-only** form. Admin-only tools (`Admin Tools`, all
create/edit/delete/upload/import/release/obsolete actions) stay hidden/403 for staff.

**Deliverables:**
1. **Remove `readonly` from seeding.** In `scripts/init_db.py`, delete the `readonly` role
   definition, its `allowed_readonly_keys` prune block, and any `readonly`-specific
   permission wiring. Do not leave a dangling `readonly` role or orphaned associations.
2. **Auto-migrate existing users off `readonly` (idempotent).** As part of the seed (runs
   every deploy), before/while deleting the role: find every user whose roles include
   `readonly` and ensure they have `staff` instead, then remove the `readonly` role and its
   user/permission associations. This automatically moves the live `silqrepservice@gmail.com`
   account to `staff` on the next deploy — **no manual reassignment required.** Keep the
   `staff.view` marker permission; leave the `staff.view`-less permission `readonly` gone.
   (Ordering must respect FK/association-table constraints so the delete succeeds cleanly on
   Postgres.)
3. **Preserve SW.SLQ010 access-control validation on the `staff` role.** Two tests currently
   assert the `readonly` role carries exactly `{admin.view, docs.view}`:
   `tests/test_staff_readonly.py` (~line 393) and
   `tests/test_edms_improvements.py::test_init_db_seeds_readonly_role_with_minimal_permissions`
   (~line 322). Update these so the SW.SLQ010 Test Case 8 (Access Control, SRS-5.2)
   coverage is demonstrated with the **`staff`** role instead — i.e. a `staff`-role user is
   authenticated but every `docs.create` / `docs.edit` / `docs.release` / `docs.obsolete`
   (and other mutation) action returns a real **403**. Remove the assertions that the
   `readonly` role exists. Net: no loss of access-control validation evidence; the read-only
   tester persona is now `staff`. **Flag for QA:** SW.SLQ010 is a controlled document that
   names the read-only tester role; Ethan may need a doc update/DCO to reflect `readonly →
   staff`. Note this in your report; do not edit controlled documents yourself.
4. **Account management UX:** In the Admin Tools account management screen, for each user
   the admin can clearly (a) *see* the currently assigned role(s), and (b) *change* the role
   via an obvious control (dropdown/select) offering exactly **`admin`**, **`staff`**, and
   **`auditor`** (no `readonly`), each with a one-line description. Present **`staff`** as
   the default for a new non-admin team member. Role changes are admin-only (`admin.edit`),
   CSRF-protected, and audit-logged.
5. **Verify (local, realistic):** With a user on the `staff` role, the rendered dashboard
   shows cards in **all four** columns (including Manufacturing, Equipment, Supplies,
   Purchasing, My Training, Distribution Log, Sales Dashboard, Customers, Suppliers, NRE
   Projects) and **does not** show `Admin Tools`. Seeding no longer creates a `readonly`
   role; a pre-existing `readonly` user ends up on `staff` after seed. Add/extend a test
   asserting the staff dashboard renders operational + external cards and hides admin-only
   controls, and that seeding leaves no `readonly` role.

---

## Task B — Put the search box on the dashboard (no menu click required)

**Intent:** Users should search from the dashboard directly, not by clicking a menu item.

**Deliverables:**
1. Add a prominent **global search box** at the top of the admin dashboard
   (`admin/index.html`), directly under/inside the "Admin Dashboard" header card, above the
   4-column grid. It is a simple **GET** form:
   - `action="{{ url_for('search.global_search') }}"`, `method="get"`, text input
     `name="q"`, placeholder like *"Search documents, forms, records… (e.g. QM.SLQ016, CAPA)"*,
     and a Search button. Pressing Enter submits.
2. Visible to everyone who can see the dashboard (`has_perm("admin.view")`, which includes
   staff). Style it to match the existing design system (`design-system.css`, card look).
3. The existing topbar `Search` link may remain, but the dashboard box is the primary entry
   point and must not require navigating a menu.

---

## Task C — Deploy discipline (keep auto-deploying, but verify it lands)

1. **Continue auto-deployment:** commit and push to `main` yourself; do not wait for
   manual approval to deploy.
2. **A checkpoint is only "shipped" when the DO deploy log reaches
   `=== SilqQMS release done ===` and gunicorn is listening** — not when local tests pass.
   (Context: every deploy from Checkpoint 3 until `8249067` silently rolled back because
   committed `purchasing/admin.py` imported `merge_import_metadata` whose definition in
   `parsers/pdf.py` was left uncommitted. Local tests were green the whole time.)
3. **Add a pre-push guard** that would have caught that: a small CI step (and/or a
   documented `make`/script target) that, from a **clean checkout of committed code**
   (e.g. `git archive HEAD` into a temp dir, or a clean clone), runs
   `python -c "import app.wsgi"` and fails if it errors. This ensures no committed caller
   can depend on an uncommitted/undeclared symbol again. Keep it lightweight.

---

## Acceptance criteria (Definition of Done)

- [ ] A `staff`-role user sees all four dashboard columns read-only; no `Admin Tools`, no
      write controls; every mutation route returns 403 for staff.
- [ ] The `readonly` role is gone from seeding; any user previously on `readonly` (incl.
      `silqrepservice@gmail.com`) is auto-migrated to `staff` by the idempotent seed.
- [ ] SW.SLQ010 Test Case 8 (Access Control, SRS-5.2) coverage is preserved using the
      `staff` role; the old `readonly`-role assertions are removed/retargeted. QA note about
      the controlled SW.SLQ010 doc flagged in the report.
- [ ] Admin Tools account management clearly shows each user's role and lets an admin
      change it (CSRF-protected, audit-logged, `admin.edit`-gated), offering exactly
      `admin` / `staff` / `auditor`; `staff` is the default for team members.
- [ ] Dashboard has a working search box at the top (GET → `search.global_search?q=`),
      visible to staff, no menu click required.
- [ ] Clean-checkout `import app.wsgi` guard added to CI/scripts.
- [ ] Test suite green; single alembic head.
- [ ] Pushed to `main` and **DO deploy confirmed green** (`=== SilqQMS release done ===`
      + gunicorn listening + `/healthz` 200). Report the deploy log tail.

## Out of scope (do NOT start these here)
- E2 (QMS Document Index by ISO 13485 clause/subsystem, in-app DCO Log / change-history
  view). That will be issued as its own prompt after this one is confirmed live.
- The document/record data load (Track A).

## What to report back
1. Confirmation the `readonly` role is deleted, how many users were auto-migrated to
   `staff`, and how the SW.SLQ010 access-control coverage was retargeted (+ the QA flag
   about the controlled SW.SLQ010 doc naming the read-only tester role).
2. Files changed + the account-management role-assignment behavior (`admin`/`staff`/
   `auditor` only), with a screenshot or description of the control.
3. The dashboard search box location/behavior.
4. The clean-checkout import guard.
5. The DO deploy log tail proving `=== SilqQMS release done ===`.
