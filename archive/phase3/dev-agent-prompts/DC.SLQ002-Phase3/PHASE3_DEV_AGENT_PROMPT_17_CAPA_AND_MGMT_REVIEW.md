# Phase 3 — Prompt 17: CAPA Tracker + Management Review Report

## Context

The system is operationally complete. Two significant compliance gaps remain:

1. **CAPA tracking**: Four active CAPAs (CAPA001–CAPA004) exist as file collections in
   the `capas` admin_docs library but have no structured status fields, dates, or workflow
   in the system. Compliance requires knowing at a glance: what is the current status of
   each CAPA, what is the target close date, and has effectiveness been verified?

2. **Management review report**: ISO 13485 requires management reviews to be supported
   by documented input data across all QMS areas. The system now holds all this data but
   there is no single view or export to support the quarterly/annual review meeting.

---

## Task A — CAPA Tracker (new lightweight model + views + migration)

### A1 — Model

Add a `CAPARecord` model to a new module `app/eqms/modules/capas/` (or add to the
existing admin_docs module — dev agent's call for best fit). Minimal schema:

```
id, capa_number (unique, e.g. "CAPA001-2025"), title,
status (Open / Pending Effectiveness / Closed / Cancelled),
opened_date, target_close_date, closed_date,
root_cause_category (varchar, e.g. "Process", "Equipment", "Supplier", "Documentation",
                     "Training", "Design", "Other"),
description (text), corrective_actions (text),
effectiveness_check_date, effectiveness_result (text),
linked_doc_number (nullable, links to e.g. QM.SLQ016 CAPA SOP),
created_by_user_id (FK users), updated_by_user_id (FK users),
created_at, updated_at
```

Additive migration. Single head enforced.

### A2 — Seed the four known CAPAs

After the migration, seed the four known CAPAs via a post-migration data seed in
`scripts/init_db.py` or a separate idempotent seeder (coordinator will run it).

| `capa_number` | `title` | `status` | `opened_date` |
|---|---|---|---|
| CAPA001-2025 | Supplier CAPA — Pathway catheter geometry nonconformance | Pending Effectiveness | 2025-01-01 |
| CAPA002-2025 | CAPA for IA-2024 audit findings | Closed | 2024-09-01 |
| CAPA003-2025 | Valve modification — unauthorized design change (FDA 483 Obs 2) | Pending Effectiveness | 2025-02-11 |
| CAPA004-2025 | IA-2025 Internal Audit Remediation (15 mNCs + 10 OFIs) | Open | 2025-12-15 |

Use `target_close_date = None` and `closed_date = None` for now — Ethan will fill these
in via the UI. Effectiveness check date for CAPA003 = 2026-10-01 (Q3 milestone).

If the seeder writes to the DB directly (not via `init_db.py`) write a one-off script
`scripts/_seed_capas.py` using the same prod-credential pattern; coordinator will run it.

### A3 — Views

- `GET /admin/capas` — list with status badges (Open = warning, Pending Effectiveness = info,
  Closed = success), target close date, and days overdue if past target. Gated `admin.view`.
- `GET /admin/capas/<id>` — detail: all fields, link to the `capas` admin_docs library
  subfolder (e.g. CAPA001-2025 → `/admin/libraries/capas/CAPA%20001-2025`), and a
  tab/section for linked admin_docs files (if the library subfolder name matches the
  CAPA number prefix).
- `GET /admin/capas/<id>/edit` + `POST` — edit form for admin only (`admin.edit`).
- `GET /admin/capas/new` + `POST` — create new CAPA.

Add a **"CAPAs"** card to the dashboard Status strip (count of open + pending-effectiveness
CAPAs). Link to `/admin/capas`.

### A4 — Tests

- List view renders correct status badge for each status value.
- Edit requires `admin.edit`; list/detail requires `admin.view`.
- New CAPA creates a DB row; duplicate `capa_number` is rejected.

---

## Task B — Management Review Report (code + deploy, no migration)

Add `GET /admin/reports/management-review` (gated `admin.edit`), accessible from the
Reports section. The page is a formatted HTML report (printable, also exportable as CSV
via `?format=csv`) covering the standard ISO 13485 management review input sections:

### Section 1 — Document Control Activity
Pull from `Document` and `DocumentRevision`: count of documents released in the last
12 months, by category; list of the 10 most recently released revisions with revision
label and effective date.

### Section 2 — Customer Feedback & Complaints
Count of `AdminDocFile` rows in `post_market_surveillance` library uploaded in the last
12 months. Note any `eMDRs` subfolder files. (No structured complaint model exists; this
is a file-count proxy.)

### Section 3 — Process Performance / Quality Objectives
Pull live from the `system_settings` quality objectives values (saved in Task C of
Prompt 16) and display current vs. target for each of the five objectives.

### Section 4 — Equipment Status
Pull from `Equipment`: count Active / Overdue CAL / Overdue PM / Due-Soon; list any
currently overdue items.

### Section 5 — Supplier Status
Pull from `Supplier`: count Approved / Conditional / Pending; count with
`next_reevaluation_date` in the past; list any expired certifications.

### Section 6 — CAPAs
Pull from `CAPARecord` (Task A): count Open / Pending Effectiveness / Closed in the last
12 months; list all Open and Pending-Effectiveness CAPAs with target close dates.

### Section 7 — Training
Pull from `TrainingAssignment`: total acknowledged in the current year (objective 4
metric); count of open/overdue items for all users; list users with overdue training.

### Section 8 — Purchasing / Supplier Performance
Pull from `PurchaseOrder`: count by status (pending / received / partial / cancelled);
count in the last 12 months.

### Formatting
- HTML version: clean print-ready layout with section headings, data tables, and a
  "Report generated: {datetime}" header. A `?print=1` param triggers auto-print.
- CSV version: flat table with `section` and `item` columns (same pattern as the
  "What's Due" report from Prompt 16).
- Link this report from the dashboard and from the existing Reports section.

---

## Task C — Deploy discipline

Both tasks result in code changes. Deploy together in one commit.
Migration for Task A must be additive, single head. Import guard must pass.
Tests for Task B: management review page renders 200 for admin, 403 for staff; CSV
exports correct `section` values. Full suite must stay green.

Write `scripts/_seed_capas.py` if the four-CAPA seed is not handled by `init_db.py`.
Coordinator will run the seeder after deploy.

---

## Deliverables

1. CAPA model + migration deployed (single head confirmed).
2. CAPA list/detail/edit/new views live at `/admin/capas`.
3. Dashboard status strip includes CAPA count tile.
4. `scripts/_seed_capas.py` ready (or CAPA seed wired into `init_db.py`).
5. Management review report live at `/admin/reports/management-review`.
6. Coordinator runs CAPA seeder and confirms `/admin/capas` shows four records.
