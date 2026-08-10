# Phase 3 — Prompt 15: Phase 7 — Training Activation (DC.SLQ002 Phase 4)

## Context

DC.SLQ002 Phase 4 is "employee training" — the next formal phase after file migration.
Two training items for Ethan (ethanr@silq.tech) are already overdue as of July 2026:

1. **Design control retraining on QM.SLQ052** (CAPA 2025-003 effectiveness confirmation,
   target July 1 2026)
2. **DCO091–095 document revisions** — training on all 40 document changes from Q2

Employee accounts for the broader team are deferred to a future prompt; for now all
assignments target `ethanr@silq.tech`.

---

## Task A — Training workflow improvements (code + deploy)

The training module shipped in Prompt 8. Now that real documents are live, improve the
workflow so it is actually usable day-to-day.

### A1 — My Training page improvements

- **Progress indicator**: Show "X of Y acknowledged" at the top as a progress bar
  (use the existing `.table-wrap` / design-system CSS, no new styles needed).
- **Grouping by document**: If a user has multiple assignments for documents in the same
  SLQ family, group them under a collapsible heading (e.g. "QM.SLQ052 Design Control").
- **Direct open button**: The "Open" link on each row should open the document in a new
  tab (`target="_blank"`) so acknowledging on return is smoother.
- **Acknowledge confirmation**: After acknowledging, flash a specific message:
  "Acknowledged: <document title> Rev <revision>." so the user knows exactly what was
  recorded.
- **Overdue badge**: Items where `due_date < today` and `acknowledged_at IS NULL` render
  a pulsing red "Overdue" badge (CSS animation: `@keyframes pulse-badge` on `.badge--overdue`).

### A2 — Admin training overview improvements

- **Export to CSV**: Add a `GET /admin/training/export.csv` route gated by
  `training.manage` that exports all assignments as a CSV:
  columns = `user_email, document, revision, assigned_date, due_date, acknowledged_at,
  status`. This is the management review / audit evidence export.
- **Completion percentage per user**: In the admin overview table, add a
  "Completion" column showing "acknowledged / total" for each user.
- **Filter by document**: Add a `?doc_number=QM.SLQ052` filter so an admin can quickly
  see who has/hasn't completed training on a specific document.

### A3 — Assign Training page improvements

- **Bulk assign by document list**: Add an optional textarea `bulk_doc_numbers` to the
  existing `/admin/training/new` form. When populated with newline-separated doc numbers
  (e.g. `QM.SLQ001\nQM.SLQ052`), create one assignment per doc per selected user rather
  than a single free-text item. Resolve each doc number to the current released revision
  automatically using `service.get_current_revision()` (or the equivalent query).
- **Select all users checkbox**: A "Select all staff" checkbox that toggles all user
  checkboxes in the user picker.

---

## Task B — Bulk training assignment for Ethan (script, coordinator runs)

Write `scripts/_assign_training_ethan.py`. Creates training assignments for
`ethanr@silq.tech` covering:

**Group 1 — DCO091 (Phase 1A: document control rewrite)**
- QM.SLQ001 Rev B, QM.SLQ014 Rev C

**Group 2 — DCO092 (Phase 1B: targeted SOPs)**
- QM.SLQ003, QM.SLQ015, QM.SLQ017, QM.SLQ020, QM.SLQ036 (current revisions)

**Group 3 — DCO093 (Phase 2 batch 1)**
- QM.SLQ012, QM.SLQ013, QM.SLQ016, QM.SLQ018, QM.SLQ021, QM.SLQ022, QM.SLQ023,
  QM.SLQ028, QM.SLQ030

**Group 4 — DCO094 (Phase 2 batch 2)**
- QM.SLQ025, QM.SLQ026, QM.SLQ027, QM.SLQ029, QM.SLQ033, QM.SLQ037, QM.SLQ038,
  QM.SLQ039, QM.SLQ040, QM.SLQ043, QM.SLQ045, QM.SLQ046, QM.SLQ047, QM.SLQ048,
  QM.SLQ049, QM.SLQ050, QM.SLQ051

**Group 5 — DCO095 (Design Control redesign — CAPA 2025-003 effectiveness confirmation)**
- QM.SLQ052 Rev A  ← PRIORITY, due date: 2026-07-15

For each document, look up the current released `DocumentRevision` by doc_number.
Use the existing `TrainingAssignment` model:
- `assigned_to_user_id` = Ethan's user ID
- `document_revision_id` = the current revision's ID
- `due_date` = Group 5: `2026-07-15`; Groups 1–4: `2026-07-31`
- `instructions` = "DC.SLQ002 Phase 4 — read and acknowledge current revision"
- Idempotent: skip if an open (unacknowledged) assignment already exists for that
  revision + user.

Include `DRY_RUN = True`. Print the list of assignments that would be created (doc number,
revision, due date).

---

## Task C — Training matrix import infrastructure (code, no script execution yet)

Parse `SILQ Training Matrix.xlsx` (at workspace root) and build the infrastructure for
bulk assignment when new employee accounts are added.

**C1**: Write `scripts/parse_training_matrix.py` — a read-only utility (committed,
no prod creds) that:
1. Reads the `Matrix` sheet (columns = employees, rows = documents; `X` = required).
2. Outputs a JSON file `docs/training_matrix_parsed.json` with structure:
   ```json
   {
     "employees": ["CEO [verne]", "Dir R&D/Eng [ethan]", ...],
     "assignments": [
       {"doc_number": "QM.SLQ001", "required_for": ["CEO [verne]", "Dir R&D/Eng [ethan]", ...]},
       ...
     ]
   }
   ```
3. This becomes the reference that future bulk-assign scripts read from when employee
   accounts are created. Commit the script and the parsed JSON output.

**C2**: Write `scripts/bulk_assign_by_matrix.py` (committed, no creds, `DRY_RUN = True`
hardcoded) that:
- Reads `training_matrix_parsed.json`
- Accepts `--user-email ethan@silq.tech` and `--role "Dir R&D/Eng [ethan]"` CLI args
- Prints all assignments that would be created for that user based on the matrix

This gives Ethan a one-command way to onboard any new employee once their account and
role are known.

---

## Task D — Deploy discipline

Task A is a code change — commit, push, confirm DO green. Tasks B and C are scripts:
B is gitignored (embeds creds); C is committed (read-only utilities). No migration for
Task A (all UI/route changes). Continue single-migration-head and import-guard rules.

Tests for Task A:
- `/admin/training/export.csv` returns 200 with `text/csv` content-type and correct
  column headers for a training.manage user; 403 for staff.
- Bulk-assign form with `bulk_doc_numbers` creates N assignments for N valid doc numbers;
  unknown doc numbers are skipped with a warning flash.
- My Training shows overdue badge when `due_date < today` and not acknowledged.

---

## Deliverables

1. Task A deployed (training UX improvements).
2. `scripts/_assign_training_ethan.py` — dry-run output (list of assignments to create).
3. Coordinator runs Task B live.
4. `scripts/parse_training_matrix.py` + `docs/training_matrix_parsed.json` committed.
5. `scripts/bulk_assign_by_matrix.py` committed with `--help` usage example in docstring.
