# Dev Agent Prompt 8 — E3: Cross-Linking & Training Integration

**Type:** Standalone, self-contained work order. Complete all tasks, then deploy.
**Owner:** Ethan (sole QA/RA/R&D, SILQ Technologies) — the coordinator reviews your output.
**Scope discipline:** Build exactly what's below. Preserve the **staff read-only** model on
every surface. Do **not** run the production document load (Track A remains gated).

---

## 0. Context you need (read these first)

- App: Flask + SQLAlchemy modular monolith ("Silq eQMS") on DigitalOcean App Platform.
  Push to `main` → auto-build → `scripts/start.py` → `release.py` (alembic upgrade +
  idempotent seed) → gunicorn. Green deploy ends with `=== SilqQMS release done ===`,
  gunicorn `Listening at ...`, `/healthz` 200.
- Prod is healthy on `07639d2`. Live: Checkpoints 3–5, E1 (discovery/DC-at-scale),
  E2 (QMS Index + DCO Log). Roles: `admin` + `staff` (read-only) + external `auditor`.
- **Build/test against a local import** of the reconciliation manifests (114 controlled
  docs with multi-revision history) as prior checkpoints did — local/SQLite only, never push
  data, never import to production. This gives real docs/revisions to build and screenshot
  against.
- Files central to this work order:
  - `app/eqms/modules/training/models.py` — `TrainingAssignment` (one row per item-per-user).
    Has `item_type` (`document`/`admin_doc`/`free_text`), `document_id` (FK → `documents.id`,
    nullable), `admin_doc_file_id`, cached `item_title`, `assigned_to_user_id`, `due_date`,
    `acknowledged_at`. **No revision reference exists yet.**
  - `app/eqms/modules/training/admin.py` / `service.py` — assignment creation (gated
    `training.manage`, admin-only), the `/admin/my-training` queue (gated `training.view`,
    staff hold it), and the acknowledge handler (assignee-only, 403 otherwise).
  - `app/eqms/modules/document_control/models.py` — `Document`, `DocumentRevision`
    (per-revision label/effective date/status), `DocumentFile`. A document has a
    current/active revision.
  - `app/eqms/modules/document_control/qms_index.py` — contains `_SLQ_RE` (`SLQ0*(\d+)`)
    that extracts the SLQ family number from a doc number. **Reuse this** for related docs.
  - `app/eqms/modules/document_control/admin.py` — `doc_control` blueprint; the document
    **detail** page (revision timeline from E1).

---

## Task A — Training ↔ specific controlled document & revision

**Intent (QM.SLQ003):** Now that controlled documents exist, an admin can assign a
read-and-acknowledge item that targets a **specific controlled document and revision**
(e.g. "acknowledge **QM.SLQ016 Rev D**"), and the assignee's "My Training" item shows both
the assigned revision and the document's **current** revision so a stale acknowledgement is
obvious.

**Deliverables:**
1. **Schema (additive, nullable, single head):** add `document_revision_id` (nullable FK →
   `document_revisions.id`, `ondelete="SET NULL"`) to `training_assignments`. One additive
   Alembic migration; keep a single head; nullable so existing rows are unaffected.
2. **Assignment UI (`training.manage`, admin-only):** when the admin picks a controlled
   document as the item, let them optionally pick a **specific revision** of that document
   (default: the current/active revision). Store `document_revision_id`; keep `item_title`
   cached as e.g. `"QM.SLQ016 Rev D — <title>"`. Re-assigning the same (document, revision,
   user) stays idempotent (matches the existing open-item behavior).
3. **My Training queue (`training.view`, staff):** for a document-linked item show the
   **assigned revision** and the document's **current revision**; when they differ, show a
   clear "a newer revision (Rev X) is now current" indicator. The "open" link goes to the
   document detail (existing viewer). Acknowledgement behavior/audit is unchanged and remains
   assignee-only (403 for anyone else).
4. **Admin overview (`training.manage`):** show the targeted revision in the assignment list.

---

## Task B — Related documents (shared SLQ family)

**Intent:** From any controlled document, surface its related controlled documents — its
parent SOP and the SOP's forms/templates/travelers — via the shared SLQ family number (e.g.
`QM.SLQ015` ↔ `FM1-QM.SLQ015`, `FM2-QM.SLQ015`, `TMP1-QM.SLQ015`).

**Deliverables:**
1. **Extract a shared helper** for the SLQ family (don't duplicate the regex): factor the
   `SLQ0*(\d+)` logic (currently `_SLQ_RE` in `qms_index.py`) into a reusable
   `slq_family(doc_number) -> int | None` used by both `qms_index.py` and this feature.
2. **"Related documents" section on the document detail page:** list other controlled
   documents sharing the same SLQ family (exclude the current doc), each linking to its
   detail, showing doc number, title, current revision, and status badge. Order sensibly
   (parent SOP first, then forms/templates by number). Hide obsolete by default consistent
   with existing behavior; if there are no related docs, render nothing (or a quiet empty
   state) — no error.
3. Read-only; visible to `docs.view` (staff included). No new write paths.

---

## Task C — Deploy discipline (unchanged)

1. Auto-deploy: commit and push to `main` yourself.
2. A checkpoint is "shipped" only when the DO deploy log shows `=== SilqQMS release done ===`
   + gunicorn listening + `/healthz` 200.
3. Run `scripts/check_clean_import.py` before pushing and confirm `[import-guard] OK`; keep
   the CI import-guard job green. Keep a **single alembic head**.

---

## Acceptance criteria (Definition of Done)

- [ ] `training_assignments` has a nullable `document_revision_id` via one additive migration;
      single alembic head; existing rows unaffected.
- [ ] Admin can assign a specific document **and revision** (defaulting to current); title is
      cached with the revision; re-assign stays idempotent.
- [ ] My Training shows assigned vs. current revision and flags when a newer revision exists;
      acknowledgement stays assignee-only (403 otherwise) and audited.
- [ ] Document detail shows a "Related documents" section grouping docs of the same SLQ
      family, linked, with current rev + status; quiet empty state; obsolete hidden by default.
- [ ] Shared `slq_family()` helper reused by `qms_index.py` (no duplicated regex).
- [ ] Staff read-only intact: no new write paths; training assignment/manage stays
      `training.manage` (admin-only); related-docs + queue are read-only for staff.
- [ ] Suite green; clean-checkout import guard green; single head.
- [ ] Pushed to `main` and **DO deploy confirmed green** — report the deploy log tail.

## Out of scope (do NOT start here)
- E4 (usability & readiness sweep) — separate later prompt.
- Track A — the actual controlled-document production load (still gated).
- Editing/authoring documents or DCOs in-app.

## What to report back
1. The training revision-targeting behavior (assignment UI + My Training assigned-vs-current
   display) and the migration added.
2. The related-documents section behavior and the shared `slq_family()` refactor.
3. Suite status, single-head confirmation, import-guard result.
4. The DO deploy log tail proving `=== SilqQMS release done ===`.
