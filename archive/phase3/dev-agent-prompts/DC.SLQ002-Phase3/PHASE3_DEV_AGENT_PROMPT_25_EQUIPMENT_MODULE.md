# Prompt 25 — Equipment Module Enhancements

## Context

The Equipment page has been reviewed by Ethan. The following targeted changes are required.  
Read `app/eqms/modules/equipment/admin.py` and `app/eqms/templates/admin/equipment/list.html` in full before starting.

---

## Task A — Combine CAL and PM Status into a Single Column

In `list.html` (the equipment table), replace the separate **CAL Status** and **PM Status** columns with a single **Service Status** column.

Rules for the combined cell:
- Compute both `cal_st = due_status(e.cal_due_date, e.cal_interval_text, today)` and `pm_st = due_status(e.pm_due_date, e.pm_interval_text, today)`.
- Pick the **worst-case** state (precedence: `overdue` > `due_soon` > `unscheduled` > `ok` > `none`).
- Show one combined badge reflecting the worst-case state.
- Below the badge, show a small (font-size: 11px, muted color) secondary line:
  - If CAL is scheduled: `CAL: <due date or "N/A">`
  - If PM is scheduled: `PM: <due date or "N/A">`
  - Omit a line entirely if both the interval text and due date are N/A/null.

This reduces the column count and surfaces the most-critical status at a glance.

Also update the filter section (currently two separate checkboxes "CAL overdue" / "PM overdue") to a single **"Service overdue"** checkbox that applies `cal_overdue OR pm_overdue` logic. Keep the existing query-param structure for backward compatibility (send both `cal_overdue=1` and `pm_overdue=1` when the single checkbox is checked).

---

## Task B — Remove Unused Buttons

In `list.html`, remove the following buttons from the header action bar:
- **Cal/PM Schedule** (`equipment_schedule` route)
- **Import Master List** (`equipment_import_master_get` route)
- **Bulk Import** (`equipment_bulk_import_get` route)

Keep only the **New Equipment** button (gated by `equipment.create` as today).

The Cal/PM Schedule page still exists and is reachable via Admin Tools — it does not need to be deleted, just removed from this header.

**Do not** delete the `equipment_import_master_get` or `equipment_bulk_import_get` routes or templates — just hide the buttons.

---

## Task C — Status Cards: List Equipment Codes and Due Dates

The at-a-glance summary cards (currently showing bare counts for Overdue CAL, Overdue PM, and Due Soon) should include a tooltip or inline listing of the affected equipment.

Update `equipment_list()` in `admin.py`:
1. Extend the `summary` dict to carry detail lists:
   - `summary["cal_overdue_items"]` — list of `{"code": e.equip_code, "due": e.cal_due_date}` for overdue CAL items (active equipment only)
   - `summary["pm_overdue_items"]` — list of `{"code": e.equip_code, "due": e.pm_due_date}` for overdue PM items (active equipment only)
   - `summary["due_soon_items"]` — list of `{"code": e.equip_code, "cal_due": e.cal_due_date, "pm_due": e.pm_due_date}` for due-soon items (active equipment only)

   **Important**: Compute these summaries over **all** equipment (not just the current page). Add a second query that loads all non-retired equipment ordered by equip_code for summary computation; use `.with_entities(Equipment.equip_code, Equipment.cal_due_date, Equipment.pm_due_date, Equipment.cal_interval_text, Equipment.pm_interval_text, Equipment.status)` to avoid loading full ORM objects.

2. In `list.html`, below the count in each status card, render a small item list:
   ```
   ST-006  — due 2025-12-11
   ST-007  — due 2025-12-11
   ...
   ```
   - Font size 11px, monospace for the code, muted for the date.
   - Show at most 8 items inline; if more, append `+ N more`.
   - For the **Due Soon** card, show the soonest applicable due date per item (min of cal_due and pm_due where applicable).
   - The Overdue CAL and Overdue PM cards remain separate (as-is) but now show their respective item lists.

---

## Task D — Equipment Data Update (Coordinator Script)

Create `scripts/_update_equipment_data.py` (gitignored, DRY_RUN = True, --execute flag).

The revised `Silq Equipment Master List.xlsx` (at workspace root `Silq Equipment Master List.xlsx`) contains two changes vs. the current DB:

1. **ST-013 status change**: The row `('ST-013', 'Inactive', ...)` should update the existing ST-013 record's `status` field from `'Active'` to `'Inactive'`. It also has a `comments` field: `'Tagged out 11 Dec 2024'` — store this in `Equipment.notes` if that field exists, or in a `comments` column if present (check the model; fall back to a print note if neither exists).

2. **ST-017 is a new record**: `('ST-017', None, 'Temperature and Humidity Monitor', 'Traceable', '90080-06', 240721382, 2024-12-13, 'Mfg', 'Biennial', '9/25/24', 2026-09-25, 'N/A', 'N/A', 'N/A', None)`. The `Equip Status` cell is blank/None — treat as `'Active'`. Create this record using the `Equipment` model (same field mapping as `import_equipment_master`).

The script should:
- Load `Silq Equipment Master List.xlsx` using openpyxl.
- For ST-013: find by `equip_code = 'ST-013'`, update `status = 'Inactive'`.
- For ST-017: upsert by `equip_code = 'ST-017'` (create if absent, skip if already present).
- Print a dry-run summary, then commit if `--execute` is passed.

---

## Task E — Additional Enhancements

### E1 — Description Truncation
The current description truncates at 40 characters. Increase to **60 characters** in the table to reduce truncation on common descriptions.

### E2 — Remove "#Docs" and "#Suppliers" columns from the list
These columns add noise without being actionable from the list view. The detail page already shows documents and suppliers. Remove both columns from the equipment list table.

### E3 — Table sorting headers
Add client-side sort capability to the equipment table. The **Equip Code**, **Status**, and **Service Status** column headers should be clickable to toggle ascending/descending sort using a small JS sort helper (no server round-trip). Add a `▲`/`▼` indicator to the active sort column.

---

## Task F — Tests

Update/extend `tests/test_p25_equipment.py`:
- Combined Service Status column present, CAL/PM columns absent.
- Summary cards: at least one item detail visible (mock an overdue equipment row).
- New Equipment button present; Import Master List button absent.
- Admin list page responds 200 for admin and staff.
- (Coordinator script has its own dry-run assertion if straightforward; otherwise skip.)

Full suite must remain green (`pytest -q`). Single Alembic head unchanged (no migration needed for any of the above — the data update is done via coordinator script, not migration).

---

## Deployment

Commit all code changes (Tasks A, B, C, E, F) and push to `main`. The coordinator will run the Task D script against production. Per the operating rhythm, do not wait for explicit approval — push once the suite is green and the import guard passes.

Tag the commit with the summary: `"P25: equipment list UX — combined service status, status card details, remove unused buttons"`.
