# Dev Agent Prompt 9 — E4: Usability & Readiness Sweep

**Type:** Standalone, self-contained work order. Complete all tasks, then deploy.
**Owner:** Ethan (sole QA/RA/R&D, SILQ Technologies) — the coordinator reviews your output.
**Scope discipline:** This is a **bounded** polish pass over a fixed list of high-traffic
views. Do NOT open-endedly refactor, restyle the whole app, or introduce new features. If a
change isn't in the list below, don't do it. Preserve the **staff read-only** model
everywhere. Expect **no migration** (this is UI/quality work); keep a single alembic head.

---

## 0. Context you need (read these first)

- App: Flask + SQLAlchemy modular monolith ("Silq eQMS") on DigitalOcean App Platform.
  Push to `main` → auto-build → `scripts/start.py` → `release.py` → gunicorn. Green deploy
  ends with `=== SilqQMS release done ===`, gunicorn `Listening at ...`, `/healthz` 200.
- Prod is healthy on `838f7d3`. Live: Checkpoints 3–5, E1, E2, E3. Roles: `admin` + `staff`
  (read-only) + external `auditor`.
- **Build/verify against the local import** (114 controlled docs w/ multi-revision history +
  representative records) as prior checkpoints did — local/SQLite only, never push data,
  never import to production.
- Design system: `app/eqms/static/design-system.css`; shared layout `templates/_layout.html`.

## Target views (the ONLY surfaces in scope — the highest-traffic ones)
1. Admin dashboard (`templates/admin/index.html`)
2. Document Control list + detail (`modules/document_control/.../list.html`, `detail.html`)
3. QMS Document Index (E2) and DCO Log (E2)
4. Global search results (E1)
5. Admin Docs library browse/viewer
6. My Training (E3) and Training Assignments (admin)

---

## Task A — Consistent navigation & breadcrumbs
- Add consistent **breadcrumbs** to the detail/list/index views in scope (e.g.
  `Dashboard / Document Control / QM.SLQ016`, `Dashboard / QMS Index`). Use one small shared
  partial/macro so markup is consistent; don't hand-roll per page.
- Ensure the primary **search entry point is consistent**: the dashboard search box (Prompt 6)
  is the canonical one; make sure list/index pages either have their local filter box or a
  visible link to global search — no dead-ends.

## Task B — Empty states
- Give every in-scope list/index/search view a friendly, consistent **empty state** (e.g.
  "No documents match these filters", "No training assigned", "No change-history log found")
  instead of a blank area or a bare table header. Distinguish "nothing exists yet" from
  "nothing matches your filter/search" where both are possible.

## Task C — Responsive pass (mobile/tablet)
- Verify and fix layout on narrow viewports (~375px phone and ~768px tablet) for the target
  views. The dashboard 4-column grid already collapses via media queries — confirm it and
  extend the same treatment to wide **tables** (Document Control list, DCO Log): make them
  horizontally scrollable or stack on small screens so content isn't clipped. No visual
  regressions on desktop.

## Task D — Accessibility basics
- Real `<label>`s (or `aria-label`) on all filter/search inputs and the training/role selects.
- Visible keyboard **focus** styles on links/buttons/inputs; logical heading order
  (`h1`→`h2`→`h3`) on the target pages.
- Check **color contrast** on status badges (RELEASED/OBSOLETE/CURRENT), links, and muted
  text against the dark theme; bump to meet WCAG AA (4.5:1 text / 3:1 large) where it fails.
- Ensure interactive controls are reachable and operable by keyboard (no click-only paths on
  the target views).

## Task E — Performance check against the populated corpus
- With the local corpus loaded (114 docs / ~199 revisions + records), sanity-check the
  target list/index/search queries for **N+1 / unindexed** patterns. Fix any obvious N+1
  (e.g. eager-load revisions/status where the list renders them) and confirm existing indexes
  cover the filters. Report rough render/query timings before/after for the Document Control
  list, QMS Index, DCO Log, and search. No premature optimization beyond clear wins.

---

## Task F — Deploy discipline (unchanged)
1. Auto-deploy: commit and push to `main` yourself.
2. "Shipped" only when the DO deploy log shows `=== SilqQMS release done ===` + gunicorn
   listening + `/healthz` 200.
3. Run `scripts/check_clean_import.py` before pushing (`[import-guard] OK`); keep the CI
   import-guard green; keep a **single alembic head** (no migration expected).

---

## Acceptance criteria (Definition of Done)
- [ ] Consistent breadcrumbs (shared partial/macro) on the in-scope detail/list/index views.
- [ ] Consistent, informative empty states on all in-scope list/index/search views;
      "empty" vs. "no match" distinguished where relevant.
- [ ] Target views usable at ~375px and ~768px (wide tables scroll/stack); no desktop regressions.
- [ ] Inputs labeled; visible focus styles; sane heading order; badge/link/muted contrast meets
      WCAG AA; target views keyboard-operable.
- [ ] No obvious N+1 on the in-scope list/index/search views; timings reported.
- [ ] Staff read-only intact; no new write paths.
- [ ] Suite green; single alembic head; clean-checkout import guard green.
- [ ] Pushed to `main` and **DO deploy confirmed green** — report the deploy log tail.

## Out of scope (do NOT start here)
- Track A — the actual controlled-document production load (this is the next phase after E4).
- New features, new modules, schema changes, or restyling views not in the target list.

## What to report back
1. Per target view: what changed for nav/breadcrumbs, empty states, responsive, a11y.
2. Performance findings + before/after timings and any N+1 fixes.
3. Suite status, single-head confirmation, import-guard result.
4. The DO deploy log tail proving `=== SilqQMS release done ===`.
5. A short note on readiness for Track A (anything you noticed that should be addressed
   before loading ~219 documents).
