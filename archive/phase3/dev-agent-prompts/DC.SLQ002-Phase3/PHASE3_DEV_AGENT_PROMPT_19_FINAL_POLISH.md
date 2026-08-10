# Phase 3 — Prompt 19: Final Polish Before Walkthrough

## Context

Prompt 18 shipped cleanly (b48b480). The dashboard is now lean and the three confirmed-dead
doctor tables have been dropped. This is the last pre-walkthrough prompt. It is
deliberately small: three targeted tasks and no new features.

---

## Task A — Drop three additional legacy tables

The dev agent's own Prompt 18 audit confirmed that `quality_docs`, `training_docs`, and
`rep_documents` have zero references in any active model or blueprint. Verify this once
more with a quick codebase search, then:

1. If confirmed dead: generate a single additive migration (chained off d4e5f6a7b8c9)
   that drops all three tables via `DROP TABLE IF EXISTS ... CASCADE` with proper
   `downgrade()` stubs for reversibility.
2. If any of the three has even one active import: leave it and flag it to the coordinator.
3. Run `alembic heads` to confirm single head after the migration.

---

## Task B — Breadcrumbs on module list and detail pages

The `breadcrumbs()` macro in `_macros.html` is consistently used on Document Control,
QMS Index, DCO Log, Global Search, Admin Docs, and Training pages. The following pages
still use plain `<- Back` links and should be upgraded to the macro:

- **Equipment**: list page and detail page
- **Suppliers**: list page and detail page
- **Purchasing**: list page and detail page
- **Supplies**: list page and detail page
- **CAPAs**: list page, detail page, new page, edit page
- **Quality Objectives**: the page (`/admin/quality-objectives`)
- **Reports**: the new landing page (`/admin/reports`) and both sub-pages

Pattern for list pages: `Dashboard` (linking to `url_for('admin.index')`) > `Module Name`
Pattern for detail pages: `Dashboard` > `Module Name` (linking to list) > `Item identifier`

No route changes. Template-only work. Staff read-only model is unaffected.

---

## Task C — User account deletion

Delete the account with email `earao72419@gmail.com`. This is a duplicate admin account
that is no longer needed.

Procedure:
1. Look up the user by email in the database.
2. Reassign or delete any records owned by this user (check foreign keys: `opened_by`,
   `created_by_id`, `acknowledged_by_id`, etc. in CAPAs, training assignments, audit
   events). If any exist, reassign them to `ethanr@silq.tech` before deleting the user.
3. Delete the user record.

This should be implemented as a one-off script `scripts/_delete_user.py` (gitignored),
following the same DRY_RUN guard pattern as previous scripts. Run it against production
after dry-run confirmation.

Do NOT commit this script. Coordinator will run it and confirm.

---

## Task D — Quality Objectives page: empty-state guidance

The `system_settings` table is currently empty — the Quality Objectives page renders
with blank input fields and no context, which looks broken on first visit.

Update the Quality Objectives page (`/admin/quality-objectives`) so that:
1. Each objective shows its full title and target from QM.SLQ037 Rev B even when no
   value has been saved yet, rather than showing a blank field with no label.
2. Objective 4 (Employee Training) auto-populates with the live count even on first visit
   (it already does this by design; confirm it still renders correctly with zero saved settings).
3. Add a brief note at the top: "Enter current values to track progress against QM.SLQ037
   targets. Values are saved per submission and shown in the Management Review report."

---

## Task E — Admin Tools page: equipment overdue context note

The Admin Tools page (`/admin/diagnostics`) now hosts the System Status strip. The strip
correctly shows red tiles for 6 overdue calibrations and 4 overdue PMs, which is real
service backlog data.

Add a one-line note below the strip (visible only when any equipment tile is non-zero):
"Equipment overdue items reflect the current service backlog. Use the Equipment Cal/PM
Schedule to log completed services."

Hyperlink "Equipment Cal/PM Schedule" to `url_for('equipment.equipment_schedule')`.
This prevents the strip from appearing alarming on first admin visit.

---

## Deploy Discipline

- Tasks A (if tables confirmed dead) and D/E: no migration vs. one migration
- Task B: template-only, no migration
- Task C: coordinator-run script, not committed
- Full test suite must pass
- Import guard must pass
- Single migration head enforced

Tests to add/update:
- Quality Objectives page: assert objective titles and targets are visible even with
  empty system_settings (i.e., the page does not render blank labels).
- Breadcrumbs: spot-check one list and one detail page from Equipment, Suppliers, and
  CAPAs for the presence of `class="breadcrumbs"` in the response.
- Admin Tools page: assert the equipment context note appears when overdue counts > 0.

---

## Deliverables

1. Legacy tables dropped (if confirmed dead), single migration head.
2. All module pages use `breadcrumbs()` macro consistently.
3. `_delete_user.py` script ready for coordinator to dry-run, then execute.
4. Quality Objectives page shows objective labels/targets even before first save.
5. Admin Tools page has equipment overdue context note.
6. Full suite green; coordinator runs _delete_user.py and confirms live site before
   Ethan's manual walkthrough.
