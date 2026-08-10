# Prompt 37 — Training Records Library Overhaul + My Training Fixes

## Background

The training infrastructure now has two distinct surfaces:

1. **The new `/training` module** (Prompt 36) — assignment queue, matrix, effectiveness reviews. This is the *operational* training system. Its user-facing page is `/my-training`.
2. **The `employee_training` admin_docs library** — a file-store for formal *training records* (PDFs, legacy paper scans, CSV exports, acknowledgement forms, job descriptions).

These need to be renamed, restructured, access-scoped, and populated correctly. Additionally, a new `Haley Shomo` user account must be created, the My Training view needs display fixes, and a DCO Batch Qualification tool is needed.

---

## Task 1 — Rename library: "Employee Training" → "Training Records"

In `app/eqms/modules/admin_docs/admin.py`:

- Change `"employee_training": "Employee Training"` → `"employee_training": "Training Records"` in `LIBRARIES`
- Update any page title, breadcrumb, or heading text that says "Employee Training" to say "Training Records"
- The route URL and internal key stay as `employee_training` / `/employee-training` — no URL change, no migration needed

Update the dashboard card in `app/eqms/templates/admin/index.html` (if it references "Employee Training") to say "Training Records".

---

## Task 2 — Rename Training module: nav link and page titles → "My Training"

The operational training module (`/my-training`, `/training`) already works. Clean up labels:

- Any nav link or dashboard card that says "Training" (without "My") pointing to `/my-training` → change label to "My Training"
- The `<title>` and `<h1>` on `admin/training/my_training.html` should read "My Training"
- The admin management page at `/training` should be titled "Training Administration" (not "My Training")
- Breadcrumbs: `Dashboard > My Training` for employees; `Dashboard > Training Administration` for admins

---

## Task 3 — Access control: Training Records scoped by user

Currently the `employee_training` accordion shows all folders to all authenticated users. Staff (read-only) users should only see their own folder.

**In `app/eqms/modules/admin_docs/admin.py`**, update the `employee_training` route:

```python
@bp.get("/employee-training")
@require_any_permission("admin.view", "staff.view")
def employee_training():
    u = _current_user()
    is_admin = user_has_permission(u, "admin.edit")
    return _render_library("employee_training", restrict_to_user=None if is_admin else u)
```

Update `_render_library` (or the accordion template path) to accept an optional `restrict_to_user` parameter. When set, filter the top-level folders shown to only those whose `name` case-insensitively matches the user's `display_name` (with spaces removed) or contains a fragment of the user's email local part.

**Matching logic** (in the route or template context):

```python
def _folder_visible_to_user(folder_name: str, user: User) -> bool:
    """True if this top-level Training Records folder belongs to this user."""
    name_norm = folder_name.lower().replace(" ", "").replace("_", "")
    # Match against display_name fragments (e.g. "EthanRao" matches display_name "Ethan Rao")
    if user.display_name:
        dn_norm = user.display_name.lower().replace(" ", "")
        if dn_norm in name_norm or name_norm in dn_norm:
            return True
    # Match against email local part (e.g. "ethanr" matches "EthanRao")
    local = user.email.split("@")[0].lower()
    if local in name_norm or name_norm[:6] in local:
        return True
    return False
```

Pass this filter into the accordion template context so only matching root folders are rendered for non-admin users.

---

## Task 4 — Haley Shomo user account

Add Haley to `scripts/_create_team_accounts.py` and run it, OR create her account directly in this script:

Create `scripts/_create_haley_account.py`:

```python
EMAIL = "Haleys@silq.tech"
DISPLAY_NAME = "Haley Shomo"
ROLE_KEY = "staff"
TEMP_PASSWORD = "Silq2026!"
```

Run with `--execute` as part of the deployment steps for this prompt.

After creation, also run `scripts/_init_training_matrix.py --execute` so Haley gets her training assignments (the script is idempotent).

---

## Task 5 — Training Records folder structure (coordinator script)

Create `scripts/_scaffold_training_records.py`.

This script (dry-run by default, `--execute` to apply) performs the following against the `employee_training` admin_docs library:

### 5A. Delete unwanted folders

Delete the following top-level folders **and all their contents** from the `employee_training` library:
- `VerneSharma` (and all subfolders/files)
- Any other top-level folder whose name does not match any of the 7 active employees listed below

Active employees to KEEP (match case-insensitively, spaces stripped):
`EthanRao`, `BrianMcVerry`, `ChrisTurner`, `ChuckGreiner`, `TomDowney`, `NaHe`, `HaleyShomo`

The `JobDescriptions` folder at root level is **retained** (do not delete).

### 5B. Ensure top-level employee folders exist

For each of the 7 active employees, ensure a top-level folder exists named exactly:
- `EthanRao`
- `BrianMcVerry`
- `ChrisTurner`
- `ChuckGreiner`
- `TomDowney`
- `NaHe`
- `HaleyShomo`

Create any that are missing.

### 5C. Ensure standard subfolders within each employee folder

For each employee folder, ensure these subfolders exist (create if missing):
- `Silq eQMS Training Records` — will hold auto-generated training CSV
- `Historical Records` — for legacy paper training record uploads

Do NOT delete or modify any existing files in subfolders.

### 5D. Top-level library folders (non-employee)

Ensure these top-level folders exist in the `employee_training` library:
- `Training Matrix` — for the Appendix 1 training matrix document (QM.SLQ053)
- `Effectiveness Reviews` — for annual review records

---

## Task 6 — Per-employee training record CSV generation

Create `scripts/_export_training_records.py`.

This script generates a training record CSV for each active employee and uploads it to their `Silq eQMS Training Records` subfolder in the `employee_training` library.

### CSV columns per employee

```
Document Number | Document Title | Revision | Required (per QM.SLQ053 Matrix) | Status | Acknowledged Date | Training Type | Source Reference
```

**Data source**: `TrainingAssignment` table, filtered to each user.

**Required column**: `Yes` if the document is in `matrix_required_for_doc_numbers(user.email)`, else `No`.

**Status**: `Acknowledged` / `Pending` / `Overdue` / `Not Assigned` (compute from `acknowledged_at` and `due_date`).

**Acknowledged Date**: `acknowledged_at.strftime("%Y-%m-%d")` or blank.

**Training Type**: human-readable version of `training_type` field:
- `read_acknowledge` → "Read and Acknowledge"
- `dco_auto_qualified` → "DCO Auto-Qualified"
- `document_originator` → "Document Originator"
- `interactive` → "Interactive"

**Source Reference**: `source_reference` if present, else blank.

### File naming

`[DisplayName]_Training_Record_[YYYY-MM-DD].csv` — e.g., `EthanRao_Training_Record_2026-07-16.csv`

### Upload behavior

- Upload to S3 and register as an `AdminDocFile` in the user's `Silq eQMS Training Records` subfolder
- If a file with the same base name already exists in that folder, **delete** the old one before uploading the new one (replace-in-place pattern, keep only the most recent)

Run with `--execute` to upload. Default is dry-run (prints what would be generated).

---

## Task 7 — DCO Batch Qualification tool

Add a new section to `app/eqms/templates/admin/training/manage.html` (or a new page at `GET /training/dco-qualify`) — an admin-only form for quickly creating DCO auto-qualification records in bulk.

### Form fields

- **DCO Number** (text, required) — e.g., `DCO-091`
- **Documents covered** (multi-select or comma-separated text box of doc numbers) — e.g., `QM.SLQ001, QM.SLQ014`
- **Approvers** (multi-select from active users)
- **DCO Approval Date** (date picker, required)
- **Submit** → "Record DCO Qualification"

### POST handler

For each (document, approver) pair:
1. Resolve the document's current revision
2. Call `create_assignments(...)` with:
   - `training_type="dco_auto_qualified"`
   - `source_reference=dco_number`
   - `acknowledged_at=datetime(approval_date.year, approval_date.month, approval_date.day, 12, 0, 0)`
3. Flash a summary: "Created N DCO qualification records for DCO-XXX."

Add a link to this tool from the Training Administration manage page.

---

## Task 8 — My Training display fixes

In `app/eqms/templates/admin/training/my_training.html`:

1. **Document title truncation**: Ensure document titles and revision labels are not clipped. Use `word-break: break-word` and ensure the item title column has adequate width or wraps naturally. Do not use `text-overflow: ellipsis` on the primary title.

2. **DCO auto-qualified entries**: Add a distinct visual treatment for assignments with `training_type == "dco_auto_qualified"`:
   - Show a blue "DCO Auto" badge next to the document title
   - Show the `source_reference` (e.g., "DCO-091") as a small muted subtitle below the title
   - These rows should appear in the "Acknowledged" section, not "Pending", since they are pre-acknowledged

3. **Document originator entries**: Show a purple "Originator" badge similarly.

4. **Section headings**: Ensure the two sections ("Pending" / "Acknowledged") have clear visual dividers and headings.

---

## Task 9 — Update admin dashboard Training Records card

On the dashboard (`admin/index.html`), the Training Records card (currently "Employee Training") should:
- Link to `/employee-training` (unchanged)
- Show subtitle: "Formal training records, historical files, and acknowledgement documentation"

---

## Deployment steps (in order)

1. Deploy code changes (rename, access control, My Training fixes, DCO batch qualification tool)
2. Run `python scripts/_create_haley_account.py --execute`
3. Run `python scripts/_init_training_matrix.py --execute` (idempotent — adds Haley's assignments only)
4. Run `python scripts/_scaffold_training_records.py --execute`
5. Run `python scripts/_export_training_records.py --execute`

---

## Verification checklist

- [ ] Training Records library shows title "Training Records" (not "Employee Training") everywhere
- [ ] My Training page shows title "My Training"
- [ ] Staff user (e.g., log in as Brianm@silq.tech) → Training Records shows only `BrianMcVerry` folder
- [ ] Admin (ethanr@silq.tech) → Training Records shows all employee folders
- [ ] `VerneSharma` folder is gone; all 7 employee folders + `JobDescriptions` + `Training Matrix` + `Effectiveness Reviews` exist
- [ ] Each employee folder has `Silq eQMS Training Records` and `Historical Records` subfolders
- [ ] Each `Silq eQMS Training Records` folder contains a CSV file named with today's date
- [ ] DCO Batch Qualification form at `/training/dco-qualify` (or inline on manage page) works end-to-end
- [ ] My Training: no text truncation on document titles; DCO Auto-Qualified entries show badge + source
- [ ] Haley Shomo account created (Haleys@silq.tech, staff role, temp password Silq2026!)
- [ ] `_init_training_matrix.py` adds Haley's assignments after her account is created
- [ ] All existing tests pass; add smoke tests for the scoped library view and DCO batch tool
