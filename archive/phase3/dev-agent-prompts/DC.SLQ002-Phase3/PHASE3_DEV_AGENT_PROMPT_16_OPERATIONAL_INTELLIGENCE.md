# Phase 3 — Prompt 16: Phase 8 — Operational Intelligence

## Context

The eQMS is fully populated and the training module is activated. Ethan has 34 open
training items due by July 31 (priority: QM.SLQ052 due July 15). Phase 8 focuses on
making the system **proactively useful** — surfacing upcoming obligations and tracking
quality objectives against real data. No new content migrations are needed.

---

## Task A — Equipment Calibration/PM Schedule (code + deploy)

Add a **Calendar view** at `/admin/equipment/schedule` (linked from the Equipment list
page header, gated by `equipment.view`).

The schedule page shows all equipment with a non-retired status that has a
`cal_due_date` or `pm_due_date`. Layout:

1. **Overdue** section — items where either date is in the past, sorted soonest-overdue
   first. Render with `.badge--danger`.
2. **This month** section — items due within the current calendar month.
3. **Next 90 days** section — items due 31–90 days from today, grouped by month heading.
4. **Beyond 90 days / no schedule** section — collapsed by default.

Each row shows: equipment code (linked to detail), description, last cal date / last PM
date, cal due / PM due, supplier (calibration service provider from `equipment_suppliers`
where `relationship_type = 'Calibration Service Provider'`), and a quick-link "Log service"
button (links to the equipment detail page's document upload section).

Compute everything from the already-loaded equipment rows — no new model changes or
migrations. Use `due_status()` for the per-cell colouring.

Add a **"Print schedule"** link that renders a print-friendly version
(`?print=1` → stripped layout, black-and-white, page title = "Equipment Cal/PM Schedule
— {today}"). This is the document Ethan can hand to a service contractor.

---

## Task B — Supplier Re-evaluation Schedule (code + deploy)

Add a **Re-evaluation schedule** tab or section to the Suppliers list page
(`/admin/suppliers` with `?view=schedule`). Layout mirrors the Equipment schedule:
overdue → this month → next 90 days. Fields per row: supplier name (linked), status,
`next_reevaluation_date`, `certification_expiration`, linked assessment documents count,
a quick-link "Log re-evaluation" (links to supplier document upload).

No model changes. Compute from existing supplier rows using `date_status()`.

---

## Task C — Quality Objectives Tracking page (code + deploy, no migration)

Add `/admin/quality-objectives` (gated by `admin.view`), linked from the dashboard
"System Status" strip and the sidebar.

The page shows the five quality objectives from QM.SLQ037 Rev B with:
- The objective name + target threshold
- A manually-entered current value input (text or number) saved to a new lightweight
  `QualityObjectiveEntry` model (or use `custom_fields` on an existing model if zero
  migration is achievable)

**Schema decision**: If adding a new table requires a migration, use a simpler approach:
store the objective entries as a flat JSON blob in the app config (a `system_settings`
key-value table, one row per setting key). Add a `SystemSetting` model + migration only
if the model doesn't already exist. The migration should be small and additive.

The five objectives (from QM.SLQ037 Rev B / DCO094):
1. Incoming material quality: lot acceptance rate ≥ 90%
2. Finished product complaint rate: < 1% of distributed product
3. Active post-market surveillance: ≥ 12 activities per year
4. Employee training program: ≥ 10 training activities per year
5. Quarterly QP execution: ≥ 80% of action items on or ahead of schedule (min 5 items)

For objectives 4 and 5, auto-populate from live data where possible:
- Objective 4: pull the count of `TrainingAssignment` rows with
  `acknowledged_at IS NOT NULL` and `acknowledged_at` in the current year
  (this is a live computed value, not manually entered).
- For the rest, display a "Last updated: <date>" note alongside the manual entry field.

The page allows admin users to save updated values (POST, `admin.edit` gated). A
simple read-only summary view is shown to staff (`admin.view`).

---

## Task D — "What's Due" report export (code + deploy)

Add `GET /admin/reports/due-this-period.csv` (gated by `admin.edit`), accessible from
a new **Reports** link in the admin sidebar. The CSV contains three sections interleaved
with a `section` column:

| section | item | due_date | status | notes |
|---|---|---|---|---|
| Equipment CAL | ST-006 — Floor Scale | 2026-12-11 | OK | Micro-Precision Calibration |
| Equipment PM | ST-011 — Fume Hood | 2026-12-09 | Due soon | Independent Air Groups |
| Supplier Re-eval | Pathway Medical | 2026-03-01 | Overdue | Next re-eval date |
| Training | QM.SLQ052 Rev A | 2026-07-15 | Overdue | ethanr@silq.tech |

Query parameters: `?months=3` (default, exports items due in the next N months plus all
overdue). This is the monthly action-item report Ethan can pull for management review.

---

## Task E — Deploy discipline

All tasks are code/UI changes. A small migration is only acceptable if Task C genuinely
requires a `SystemSetting` model. If so: single new table with `key` (varchar PK) and
`value` (text); the migration must be additive only.

Tests:
- Schedule page renders with correct section groupings (one overdue item in a fixture,
  one this-month item, one beyond-90 item; assert HTML contains the right badges).
- Quality objectives page: admin can POST a new value; staff can GET but not POST.
- Report CSV: assert correct `section` column values for a fixture set.
- Full suite must stay green; single migration head enforced.

---

## Deliverables

1. Equipment schedule page live at `/admin/equipment/schedule` with print view.
2. Supplier re-evaluation schedule tab live at `/admin/suppliers?view=schedule`.
3. Quality objectives page live at `/admin/quality-objectives`.
4. "What's Due" report export at `/admin/reports/due-this-period.csv`.
5. Optional `SystemSetting` migration if needed (coordinator will verify head).
6. Coordinator confirms all four pages on the live site before Prompt 17.
