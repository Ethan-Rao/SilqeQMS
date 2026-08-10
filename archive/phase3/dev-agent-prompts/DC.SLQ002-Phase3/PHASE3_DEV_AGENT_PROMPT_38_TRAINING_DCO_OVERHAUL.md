# Prompt 38 — Training Module Overhaul: Historical Records, DCO Auto-Qualification, and UI Fixes

## Background

Prompt 37 deployed successfully but revealed several issues that need to be corrected:
- The Training Records library subtitle is too verbose.
- Historical training record PDFs (193 files) were inadvertently deleted from DigitalOcean Spaces by the P37 scaffold script. The source files exist locally at `EmployeeTraining/` (workspace root) and must be re-uploaded.
- DCO qualification should be automatic — never manual. Retroactive records must be seeded from DCO087–096 (Word docs in `QMSInProcess/`), and going forward the document release flow must capture DCO number + approvers and auto-create training records.
- The Training Administration page needs access-control enforcement and a streamlined header.
- My Training button styling is poor.

---

## Part A — Training Records Library

### A1: Subtitle
In `app/eqms/modules/admin_docs/admin.py`, find wherever the `employee_training` library subtitle is rendered and change it to:

> **Training Record Archive**

Also update the subtitle in `app/eqms/templates/admin/index.html` (the dashboard card for Training Records) to match.

### A2: CSV Placement — Move to Employee Folder Top Level

Currently `_export_training_records.py` uploads CSVs into `<EmployeeName>/Silq eQMS Training Records/`. Change the destination so the CSV lands **directly inside the employee's top-level folder** (i.e., `<EmployeeName>/`), not in the subfolder. The subfolder `Silq eQMS Training Records/` stays — it is reserved for DCO form copies and effectiveness review attachments.

Update the stale-file prefix check and the storage key accordingly. Re-run the export as part of the deployment steps.

### A3: Historical Records Upload Script

Write `scripts/_upload_historical_training.py`. This script re-uploads the historical training PDFs from the local `EmployeeTraining/` directory (workspace root) to the `employee_training` admin_docs library.

**Folder mapping:**

| Local source | Target in library |
|---|---|
| `EmployeeTraining/BrianMcVerry/*.pdf` | `BrianMcVerry/Historical Records/` |
| `EmployeeTraining/ChrisTurner/*.pdf` | `ChrisTurner/Historical Records/` |
| `EmployeeTraining/ChuckGreiner/*.pdf` | `ChuckGreiner/Historical Records/` |
| `EmployeeTraining/EthanRao/*.pdf` | `EthanRao/Historical Records/` |
| `EmployeeTraining/HaleyShomo/*.pdf` | `HaleyShomo/Historical Records/` |
| `EmployeeTraining/NaHe/*.pdf` | `NaHe/Historical Records/` |
| `EmployeeTraining/TomDowney/*.pdf` | `TomDowney/Historical Records/` |
| `EmployeeTraining/VerneSharma/*` | Top-level `Historical Records/` folder (Verne is a former employee — create this folder if absent) |
| `EmployeeTraining/JobDescriptions/*` | Top-level `Job Descriptions/` folder (create if absent) |
| `EmployeeTraining/Silq Training Matrix.pdf` | Top-level `Training Matrix/` folder |
| `EmployeeTraining/SILQ Training Matrix.xlsx` | Top-level `Training Matrix/` folder |

**Behavior:**
- Dry-run by default; `--execute` to commit.
- Idempotent: if a file with the same filename already exists in the target folder, skip it (log `SKIP`).
- After uploading, print a summary: files uploaded, files skipped, files not found locally.
- Use `storage_from_config(current_app.config)` and the `AdminDocFile`/`AdminDocFolder` models (same pattern as `_export_training_records.py`).
- Content-type: `application/pdf` for .pdf, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` for .xlsx.

---

## Part B — DCO Auto-Qualification

### B1: Retroactive Backfill Script

Write `scripts/_backfill_dco_qualifications.py`. This script reads the DCO Word documents in `QMSInProcess/` to extract approver names, effective dates, and covered document numbers, then creates `dco_auto_qualified` `TrainingAssignment` records.

**Parsing approach:**

For each DCO (087–096) that has a `.docx` file in its subdirectory, parse it with `python-docx`:
- **DCO number**: from the first table, cell where label is "DCO #:"
- **Effective date**: from the first table, cell where label is "Req. Effective Date:"
- **Covered documents**: from the second table (rows after the header): extract column "Document / Part Number", filter to only values starting with `QM.SLQ` (ignore FM*, TMP*, DC.*, notes, etc.)
- **Approvers**: from the approvals table (the table containing "Printed Name" as a header): extract all values in the "Printed Name" column (skip header row and empty rows)

If a `.docx` is absent (DCO090, DCO091 had signed PDFs only), fall back to the hardcoded data below.

**Hardcoded fallback data** (use this data even if the docx parses successfully — verify parsed values match, log a warning if they differ):

```python
DCO_DATA = {
    "DCO087": {
        "date": "2025-12-10",
        "docs": ["QM.SLQ022"],
        "approvers": ["Ethan Rao", "Brian McVerry"],  # Verne Sharma no longer active — omit
    },
    "DCO088": {
        "date": "2026-03-13",
        "docs": ["QM.SLQ034"],
        "approvers": ["Ethan Rao", "Brian McVerry"],
    },
    "DCO089": {
        "date": "2026-04-30",
        "docs": ["QM.SLQ004"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chris Turner", "Na He"],
    },
    "DCO090": {
        # Design review DCO covering DC.SLQ002 (internal project) — no QM.SLQ docs.
        # Skip entirely: no training assignments created.
        "date": None,
        "docs": [],
        "approvers": [],
    },
    "DCO091": {
        "date": "2026-05-28",
        "docs": ["QM.SLQ001", "QM.SLQ014"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chris Turner", "Na He"],
    },
    "DCO092": {
        "date": "2026-06-09",
        "docs": ["QM.SLQ003", "QM.SLQ015", "QM.SLQ017", "QM.SLQ020", "QM.SLQ036"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner"],
    },
    "DCO093": {
        "date": "2026-07-08",
        "docs": [
            "QM.SLQ012", "QM.SLQ013", "QM.SLQ016", "QM.SLQ018",
            "QM.SLQ021", "QM.SLQ022", "QM.SLQ023", "QM.SLQ028", "QM.SLQ030",
        ],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner", "Tom Downey"],
    },
    "DCO094": {
        "date": "2026-06-25",
        "docs": [
            "QM.SLQ011", "QM.SLQ026", "QM.SLQ027", "QM.SLQ029",
            "QM.SLQ033", "QM.SLQ037", "QM.SLQ038", "QM.SLQ039",
            "QM.SLQ040", "QM.SLQ043", "QM.SLQ045", "QM.SLQ046",
            "QM.SLQ047", "QM.SLQ048", "QM.SLQ049", "QM.SLQ050", "QM.SLQ051",
        ],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner", "Tom Downey"],
    },
    "DCO095": {
        "date": "2026-07-09",
        "docs": ["QM.SLQ052"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner", "Tom Downey"],
    },
    "DCO096": {
        "date": "2026-07-16",
        "docs": ["QM.SLQ053"],
        "approvers": ["Ethan Rao", "Brian McVerry", "Chuck Greiner", "Tom Downey"],
    },
}
```

**Assignment creation logic:**

For each DCO entry:
1. Skip if `docs` is empty.
2. For each doc number in `docs`:
   - Call `resolve_current_revision(s, doc_number)` to get `(Document, DocumentRevision|None)`.
   - If not found, log `SKIP  {dco_id}  {doc_number} — document not found in DB` and continue.
3. For each approver name:
   - Match to a `User` by `display_name` (case-insensitive, stripped). If no match, log `SKIP  {dco_id}  {approver_name} — no matching user`.
   - If the user is inactive, skip.
4. For each `(user, document)` pair:
   - Check if a `TrainingAssignment` already exists with `assigned_to_user_id == user.id`, `document_id == doc.id`, `training_type == 'dco_auto_qualified'`, and `source_reference == dco_id`. If so, skip (idempotent).
   - Otherwise, create:
     ```python
     TrainingAssignment(
         item_type="document",
         item_title=f"{doc.doc_number} Rev {rev.revision if rev else '?'} — {doc.title}",
         document_id=doc.id,
         document_revision_id=rev.id if rev else None,
         assigned_to_user_id=user.id,
         assigned_by_user_id=actor.id,
         training_type="dco_auto_qualified",
         source_reference=dco_id,
         acknowledged_at=datetime.combine(date.fromisoformat(dco_date), time(0, 0)),
         assigned_at=utcnow(),
         created_at=utcnow(),
     )
     ```

Print a full summary at the end:
- Total records created
- Per-DCO breakdown
- Skipped items

### B2: DCO Auto-Qualification on Document Release (Going Forward)

Modify the document release flow so that when Ethan releases a document revision, he can record the approving DCO and who approved it, automatically creating training assignments.

**Model change — `DocumentRevision`:**

Add a nullable column:
```python
dco_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
```

Create an Alembic migration for this column. It is a simple `ALTER TABLE document_revisions ADD COLUMN dco_number VARCHAR(32)`.

**Release form update — `app/eqms/modules/document_control/admin.py` `release_revision` route:**

The current route is `POST /<int:doc_id>/revisions/<int:rev_id>/release`. It accepts `reason` and `effective_date`. Extend it to also accept:

- `dco_number` (optional text, e.g. "DCO097")
- `dco_approvers` (optional multi-value form field — list of user IDs who approved this DCO)

After committing the document release, if `dco_number` is provided and `dco_approvers` is non-empty:
- For each `user_id` in `dco_approvers`:
  - Check for existing `dco_auto_qualified` record for this user + document + source_reference. Skip if present.
  - Create a `TrainingAssignment` with:
    - `training_type = 'dco_auto_qualified'`
    - `source_reference = dco_number`
    - `acknowledged_at = utcnow()`
    - `document_id = d.id`, `document_revision_id = r.id`
    - `assigned_to_user_id = user_id`
    - `assigned_by_user_id = current_user.id`

**Release form UI — `app/eqms/templates/admin/modules/document_control/detail.html`:**

In the release modal/form, add below the existing "Reason" and "Effective Date" fields:

```
DCO Number (optional):
[text input: dco_number, placeholder "e.g. DCO097"]

DCO Approvers (optional — check all who approved this DCO):
[checkbox list of all active, non-service users]
  ☐ Ethan Rao
  ☐ Brian McVerry
  ☐ Chris Turner
  ☐ Chuck Greiner
  ☐ Tom Downey
  ☐ Na He
  ☐ Haley Shomo
```

Pre-check users who are required to be trained on this document per the MATRIX (call `matrix_users_for_doc(s, doc.doc_number)`). If the MATRIX has no entry for this document, show all active users unchecked.

If `dco_number` is blank, the approver checkboxes are ignored (no training records created). If `dco_number` is filled but no approvers are checked, flash a warning but still release the document.

**Import note:** Import `matrix_users_for_doc` from `app.eqms.modules.training.service` inside the function (avoid circular imports at module level).

---

## Part C — Training Administration Access Control

### C1: Redirect Non-Admins to My Training

In `manage_index` (`GET /training`), check if the current user has `training.manage` permission. If not, redirect to `url_for('training.my_training')`. This is a fallback for users who navigate directly to the URL — the `require_permission` decorator may already return 403, but replace it with a redirect:

```python
@bp.get("/training")
@require_permission("training.view")   # allow anyone who can view training
def manage_index():
    u = _current_user()
    if not u.has_permission("training.manage"):
        return redirect(url_for("training.my_training"))
    # ... existing admin code
```

Verify that `User` has a `has_permission` helper (or use the RBAC check equivalent). If the helper does not exist, check the user's role permissions against `"training.manage"` directly.

### C2: Simplified Header Buttons

In `app/eqms/templates/admin/training/manage.html`, reduce the top action button bar to three buttons only:

```
[ My Training → ]   [ Training Matrix ]   [ Annual Reviews ]
```

Remove these buttons entirely: **DCO Batch Qualify**, **Export CSV**, **New Assignment**.

Also remove the "DCO Batch Qualify" navigation link from anywhere else it appears (sidebar, breadcrumbs, etc.). The DCO qualification is now fully automatic (via the release flow + backfill script) and no manual tool is needed.

Keep the `dco_qualify_get`/`dco_qualify_post` routes in `admin.py` for now (do not delete them — they may be useful for edge-case manual overrides), but remove them from all navigation and templates.

---

## Part D — My Training UI Fixes

In `app/eqms/templates/admin/training/my_training.html`:

1. **Button styling fix**: The "Open" and "Acknowledge" action buttons are rendering poorly. Replace them with:
   - "Open" link: a plain text link styled `btn btn-sm btn-outline-secondary` or equivalent — "View Document"
   - "Acknowledge" button: styled as a primary action button `btn btn-sm btn-primary` — "Acknowledge"
   Make sure both are visually distinct and not cramped. If using Bootstrap classes, use `d-flex gap-2` or a `btn-group` wrapper.

2. **Remove "Manage Assignments" button/link** from `my_training.html` if present. Staff should not see any admin navigation from the My Training page. The only navigation should be "← Dashboard".

3. **Ensure "Acknowledged" section header is clear**: the section showing pre-acknowledged DCO auto-qualified records should read "Acknowledged" not "Completed" or anything else.

---

## Part E — Remove Inactive Accounts from Per-Employee Cards

In `manage_index()` in `app/eqms/modules/training/admin.py`, when building the per-employee completion cards, filter out users whose email matches any of these patterns:
- `earao72419@gmail.com`
- `silqrepservice@gmail.com`
- `stephen.medreg@gmail.com`

These are service/legacy accounts, not real employees. Filter them from the `users` query used to build the cards. Specifically: only include users whose `email` ends with `@silq.tech` **or** `display_name` is not None. (Do not hard-code emails — use the `display_name IS NOT NULL` heuristic instead, since all real employee accounts have display names set.)

---

## Deployment Steps (Run in Order After Code Deploy)

```
# 1. Apply DB migration (adds dco_number to document_revisions)
flask db upgrade

# 2. Re-export training record CSVs to new location (top of employee folder)
python scripts/_export_training_records.py --execute

# 3. Re-upload historical training PDFs from local EmployeeTraining/ folder
python scripts/_upload_historical_training.py --execute

# 4. Backfill DCO087–096 qualification records
python scripts/_backfill_dco_qualifications.py --execute
```

---

## Verification Checklist

- [ ] Training Records library subtitle shows "Training Record Archive"
- [ ] Each employee folder has the CSV at top level (not in subfolder)
- [ ] Each employee's `Historical Records` subfolder has their historical PDFs
- [ ] Top-level `Historical Records` folder contains VerneSharma files
- [ ] Top-level `Training Matrix` folder has the matrix PDFs/xlsx
- [ ] Top-level `Job Descriptions` folder has job description PDFs
- [ ] DCO087–096 backfill created `dco_auto_qualified` records for all matched users
- [ ] Per-employee completion cards on Training Administration do not show service accounts
- [ ] Document release form shows DCO# field + approver checkboxes
- [ ] Training Administration header shows only: My Training, Training Matrix, Annual Reviews
- [ ] Non-admin users are redirected from `/admin/training` to `/admin/my-training`
- [ ] My Training Open/Acknowledge buttons are visually clean
- [ ] No "Manage Assignments" or "DCO Batch Qualify" in My Training view
- [ ] Full test suite green; single Alembic head; `import app.wsgi` clean
