# Dev Agent Prompt 7 — QMS Document Index + In-App DCO Log / Change-History View (E2)

**Type:** Standalone, self-contained work order. Complete all tasks, then deploy.
**Owner:** Ethan (sole QA/RA/R&D, SILQ Technologies) — the coordinator reviews your output.
**Scope discipline:** Build exactly what's below. Everything is **read-only** surfacing of
data that already exists; introduce no write paths and no staff-visible mutations.

---

## 0. Context you need (read these first)

- App: Flask + SQLAlchemy modular monolith ("Silq eQMS") on DigitalOcean App Platform.
  Push to `main` → auto-build → `scripts/start.py` → `release.py` (alembic upgrade +
  idempotent seed) → gunicorn. A green deploy ends with `=== SilqQMS release done ===`,
  gunicorn `Listening at ...`, `/healthz` 200.
- Prod is healthy on `a674d54`. Roles are now just `admin` + `staff` (+ external `auditor`).
  Staff = full **read-only** dashboard.
- Files central to this work order:
  - `app/eqms/modules/document_control/dco_log.py` — **already built**, cached read-only
    loader over `eQMS_Upload_Staging/reconciliation/DCO_Log_v2.csv`. Public API:
    `load_rows()`, `changes_for_document(doc_number)`, `change_by_revision(doc_number)`,
    `rev_order_key(rev)`, and the `DcoLogRow` dataclass (fields: `dco_number`,
    `document_number`, `document_title`, `from_rev`, `to_rev`, `change_description`,
    `originator`, `date_requested`, `effective_date`, `impact_assessments`). It degrades to
    empty results if the CSV is absent — never raises.
  - `app/eqms/modules/document_control/admin.py` — `doc_control` blueprint; `list_documents`
    groups by `category`, supports `q`/`category`/`show_obsolete`, and doc-type/status
    filters (E1). `Document` has `doc_number`, `title`, `doc_type`, `category`, `status`.
  - `app/eqms/search.py` — global search (E1) at `/admin/search`.
  - Permissions: `docs.view` (already granted to admin + staff) gates Document Control views.

---

## Task A — QMS Document Index (by ISO 13485 clause + by subsystem)

**Intent:** A single "map of the QMS" page so a user (or auditor) can navigate the
controlled document set by **ISO 13485:2016 clause** and by **QMS subsystem**, instead of
only the flat category grouping. Read-only; reuses existing `Document` data.

**Deliverables:**
1. New read-only page (e.g. `GET /admin/documents/index`, `doc_control` blueprint, gated by
   `docs.view`) titled "QMS Document Index" with **two grouping modes** (tabs or a toggle):
   - **By ISO 13485 clause** (e.g. 4.2 Documentation, 7.5 Production, 8.2 Monitoring, 8.5
     Improvement, etc.), and
   - **By subsystem** (e.g. Document Control, Design Control, CAPA, Purchasing/Supplier,
     Production, Risk Management, Post-Market — align to the existing categories/modules).
   Each controlled document appears under its clause/subsystem as a link to its Document
   Control detail page, showing doc number, title, current revision, and status badge
   (RELEASED/OBSOLETE). Obsolete hidden by default with a show-toggle (match E1 behavior).
2. **Maintainable mapping.** Do NOT hardcode the clause mapping inline in a template. Drive
   it from a single maintainable source — a committed config (Python dict or a small CSV
   under `eQMS_Upload_Staging/` or `app/eqms/.../data/`) mapping document number (or
   category) → {iso_clause, subsystem}. Documents with no mapping fall into an
   "Unclassified" bucket that is clearly visible (so gaps are obvious, not hidden). Provide
   a sensible starting mapping for the current controlled set (QM.SLQ001–052 and their
   FM/TMP), using the existing `category` values where possible; it's fine for the mapping
   to be partial as long as unmapped docs surface under "Unclassified".
3. Link to this index from the Document Control list page and from the dashboard QMS System
   column (a card or a link), visible to `docs.view` (staff included).

---

## Task B — In-app DCO Log / Change-History view

**Intent:** Surface the consolidated change history (`DCO_Log_v2.csv`) inside the app as a
browsable, filterable log — the in-app replacement for the old spreadsheet DCO log — reusing
the existing `dco_log` loader (no schema change).

**Deliverables:**
1. New read-only page (e.g. `GET /admin/dco-log`, `doc_control` blueprint, gated by
   `docs.view`) titled "DCO Log / Change History" that lists all rows from
   `dco_log.load_rows()` in a clean table: DCO #, document number (link to the doc detail),
   document title, `from_rev → to_rev`, change description, originator, date requested,
   effective date, impact assessments.
2. **Filters/search (GET params):** by DCO number, by document number, and a free-text `q`
   across doc number/title/change description. Default sort by DCO number (or effective
   date) descending; make revision ordering use `dco_log.rev_order_key` where relevant.
   If the CSV is absent, render an empty-state message ("No change-history log found"), never
   error.
3. **Cross-link both directions:** on a Document Control **detail** page, ensure the
   existing per-revision timeline (E1) links out to this DCO Log filtered to that document
   (`?document_number=QM.SLQxxx`); and each DCO Log row links back to the document detail.
4. Add a link/card to the DCO Log from the dashboard QMS System column and/or the Document
   Control list, visible to `docs.view`.

---

## Task C — Deploy discipline (unchanged from Prompt 6)

1. **Continue auto-deployment:** commit and push to `main` yourself.
2. A checkpoint is "shipped" only when the DO deploy log reaches
   `=== SilqQMS release done ===` + gunicorn listening + `/healthz` 200.
3. **Run the clean-checkout import guard** (`scripts/check_clean_import.py`) before pushing
   and confirm `[import-guard] OK`. It's also a CI job — keep it green.

---

## Acceptance criteria (Definition of Done)

- [ ] QMS Document Index page renders both groupings (ISO clause + subsystem), links each doc
      to its detail, badges status, hides obsolete by default, and surfaces unmapped docs
      under a visible "Unclassified" bucket.
- [ ] Clause/subsystem mapping lives in one maintainable committed source (not inline).
- [ ] DCO Log page lists `DCO_Log_v2.csv` rows with DCO#/document/rev/description filters and
      free-text search; empty-state if CSV missing; no errors.
- [ ] Bidirectional cross-linking between the DCO Log and Document Control detail timelines.
- [ ] Both new pages gated by `docs.view` (staff can view read-only) with no write paths;
      linked from the dashboard/Document Control list.
- [ ] Test suite green; single alembic head (no migration expected — both features are
      read-only over existing data/CSV).
- [ ] Clean-checkout import guard green.
- [ ] Pushed to `main` and **DO deploy confirmed green** — report the deploy log tail.

## Out of scope (do NOT start these here)
- The document/record data **load** (Track A) — importing the actual controlled documents.
- Any change to controlled documents themselves (e.g. SW.SLQ010 DCO — that's a QA task).
- Editing/authoring DCOs in-app (this is a read-only log view only).

## What to report back
1. The QMS Document Index: routes, grouping UX, where the mapping lives, and how many of the
   current controlled docs are mapped vs. "Unclassified".
2. The DCO Log view: route, filters, and the cross-linking behavior.
3. Dashboard/list entry points added.
4. Import-guard result + the DO deploy log tail proving `=== SilqQMS release done ===`.
