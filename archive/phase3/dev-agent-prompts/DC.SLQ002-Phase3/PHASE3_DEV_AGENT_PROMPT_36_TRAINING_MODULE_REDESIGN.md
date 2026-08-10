# Prompt 36 — Training Module Redesign

## Background and Goals

The training module needs a major redesign to align with the newly released QM.SLQ053 Employee Training Program SOP (effective under DCO096). The current module handles basic read-and-acknowledge assignments but lacks three critical capabilities:

1. **DCO Signer Auto-Qualification** — when someone approves a DCO, the system must record that as a training record. Currently there is no training type to distinguish this from a regular assignment, and it cannot be created in a pre-acknowledged state with a backdated date.
2. **Historical record entry** — admin must be able to create already-acknowledged training records (backdated) to capture training that was completed before this system existed.
3. **Visibility** — there is no per-employee training profile, no matrix view showing trained/untrained status at a glance, and no Annual Effectiveness Review tracker.

**Admin full editing authority is required** per QM.SLQ053 §5.4: during the initial alignment period the admin has full authority to create, modify, and backdate training records for any user.

---

## Task 1 — DB model changes (migration required)

### 1A. Add fields to `TrainingAssignment`

In `app/eqms/modules/training/models.py`, add two new columns to `TrainingAssignment`:

```python
# How the training was completed / qualified.
# read_acknowledge (default) | interactive | dco_auto_qualified | document_originator
training_type: Mapped[str] = mapped_column(
    String(32), nullable=False, default="read_acknowledge"
)
# Free-text reference for the training source, e.g. "DCO-096", "Authored QM.SLQ053 Rev A"
source_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
```

### 1B. New `EffectivenessReview` model

Add a new model to `app/eqms/modules/training/models.py`:

```python
class EffectivenessReview(Base):
    """Annual Effectiveness Review record per QM.SLQ053 Section 11."""
    __tablename__ = "effectiveness_reviews"
    __table_args__ = (
        Index("idx_eff_review_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    review_year: Mapped[int] = mapped_column(Integer, nullable=False)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    score: Mapped[float | None] = mapped_column(nullable=True)        # e.g. 9.0 (of 10)
    passed: Mapped[bool] = mapped_column(nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="selectin")
    reviewed_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[reviewed_by_user_id], lazy="selectin"
    )
```

### 1C. Alembic migration

Generate one migration with a descriptive name like `add_training_type_source_and_effectiveness_review`.

- Add `training_type` (String(32), not null, server_default `'read_acknowledge'`) to `training_assignments`
- Add `source_reference` (String(128), nullable) to `training_assignments`
- Create `effectiveness_reviews` table

---

## Task 2 — Service layer changes

In `app/eqms/modules/training/service.py`:

### 2A. Add `training_type` and `source_reference` to `create_assignments`

Add parameters:
```python
training_type: str = "read_acknowledge",
source_reference: str | None = None,
acknowledged_at: datetime | None = None,   # admin override for historical/backdated records
```

When creating each `TrainingAssignment`:
- Set `a.training_type = training_type`
- Set `a.source_reference = (source_reference or "").strip() or None`
- If `acknowledged_at` is provided (admin backdating / DCO auto-qualification):
  - Set `a.acknowledged_at = acknowledged_at`
  - The deduplication check must also account for already-acknowledged assignments when `acknowledged_at` is provided — do NOT skip creating a pre-acknowledged record just because an open assignment exists. (An acknowledged record and a pending record are different things.)

### 2B. Add `TRAINING_MATRIX` config

Add a constant at the top of `service.py` (or a new `training_matrix.py` imported by `service.py`):

```python
# Training matrix per QM.SLQ053 Appendix 1.
# Maps doc_number → list of user email prefixes (or email suffixes) that require it.
# Using email as the key avoids hardcoding user IDs.
# Format: {doc_number: [email_fragment, ...]}
# "all" means every active user.
MATRIX: dict[str, list[str]] = {
    # BASE — all employees
    "QM.SLQ035": ["all"],
    "QM.SLQ027": ["all"],
    "QM.SLQ002": ["all"],
    "QM.SLQ053": ["all"],
    # Quality System Management
    "QM.SLQ001": ["ethan", "nah", "christ", "haley"],
    "QM.SLQ014": ["ethan", "nah", "christ", "haley"],
    "QM.SLQ016": ["ethan", "brianm", "christ", "tomd"],
    "QM.SLQ017": ["ethan", "brianm", "tomd"],
    "QM.SLQ018": ["ethan", "brianm", "tomd"],
    "QM.SLQ037": ["ethan", "brianm", "tomd"],
    "QM.SLQ025": ["ethan", "brianm", "tomd"],
    "QM.SLQ038": ["ethan", "brianm", "tomd"],
    "QM.SLQ028": ["ethan", "brianm", "nah", "chuckg", "tomd", "haley"],
    # Design & Development
    # QM.SLQ004–QM.SLQ010 obsoleted by DCO095; replaced by QM.SLQ052 Design Control SOP
    "QM.SLQ052": ["ethan", "brianm", "nah"],
    "QM.SLQ012": ["ethan", "brianm", "nah"],
    "QM.SLQ013": ["ethan", "brianm", "nah"],
    "QM.SLQ011": ["ethan", "nah"],
    "QM.SLQ032": ["ethan", "brianm", "nah"],
    "QM.SLQ033": ["ethan", "brianm", "nah"],
    "QM.SLQ048": ["ethan", "nah", "christ"],
    "QM.SLQ029": ["ethan", "christ"],
    "QM.SLQ047": ["ethan", "nah", "christ"],
    # Manufacturing & Operations
    "QM.SLQ019": ["ethan", "christ"],
    "QM.SLQ040": ["ethan", "christ"],
    "QM.SLQ039": ["ethan", "christ"],
    "QM.SLQ043": ["ethan", "christ"],
    "QM.SLQ045": ["ethan", "christ", "haley"],
    "QM.SLQ046": ["ethan", "christ", "chuckg"],
    "QM.SLQ049": ["ethan", "christ"],
    "QM.SLQ050": ["ethan", "christ"],
    "QM.SLQ051": ["ethan", "christ"],
    "QM.SLQ026": ["ethan", "nah", "christ"],
    # Supplier & Purchasing
    "QM.SLQ015": ["ethan", "christ", "haley"],
    "QM.SLQ020": ["ethan", "christ", "chuckg", "tomd", "haley"],
    # Commercial & Post-Market
    "QM.SLQ036": ["ethan", "chuckg", "haley"],
    "QM.SLQ021": ["ethan", "chuckg"],
    "QM.SLQ022": ["ethan", "chuckg"],
    "QM.SLQ023": ["ethan"],
    "QM.SLQ030": ["ethan", "brianm", "chuckg"],
}
```

**Note on email matching:** Match users by checking if any fragment in the list appears in `user.email.lower()`. The fragment `"all"` matches every active user. Make this matching logic a helper function `matrix_users_for_doc(s, doc_number) -> list[User]`.

### 2C. Add `matrix_required_for_user` helper

```python
def matrix_required_for_doc_numbers(user_email: str) -> list[str]:
    """Return all doc numbers the user is required to be trained on per the matrix."""
    email = user_email.lower()
    return [
        doc_num
        for doc_num, fragments in MATRIX.items()
        if "all" in fragments or any(f in email for f in fragments)
    ]
```

---

## Task 3 — Route changes in `app/eqms/modules/training/admin.py`

### 3A. Update `new_post` (POST /training/new)

Read two new form fields:
```python
training_type = (request.form.get("training_type") or "read_acknowledge").strip()
source_reference = (request.form.get("source_reference") or "").strip() or None
acknowledged_date_s = (request.form.get("acknowledged_date") or "").strip()
acknowledged_at = None
if acknowledged_date_s:
    from app.eqms.modules.training.service import parse_date
    d = parse_date(acknowledged_date_s)
    if d:
        from datetime import datetime
        acknowledged_at = datetime(d.year, d.month, d.day, 12, 0, 0)
```

Pass `training_type`, `source_reference`, and `acknowledged_at` to `create_assignments`.

### 3B. New route: GET /training/user/<user_id> — per-user training record

```python
@bp.get("/training/user/<int:user_id>")
@require_permission("training.manage")
def user_training(user_id: int):
    ...
```

Loads:
- The `User` object (404 if not found or not active)
- All `TrainingAssignment` rows for that user, ordered: pending first (acknowledged_at IS NULL), then acknowledged (most recent first)
- All `EffectivenessReview` rows for that user, ordered by `review_year` DESC
- Required doc numbers from `matrix_required_for_doc_numbers(user.email)`
- All `Document` objects matching the required doc numbers (for display)
- Status per assignment via `assignment_status`
- `document_revision_status` per assignment
- Today's date

Renders `admin/training/user_detail.html`.

### 3C. New route: GET /training/matrix — training matrix view

```python
@bp.get("/training/matrix")
@require_permission("training.manage")
def training_matrix():
    ...
```

Builds a data structure for the matrix grid:

```python
from app.eqms.modules.training.service import MATRIX, resolve_current_revision
from app.eqms.modules.document_control.models import Document

s = db_session()
users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()

# For each doc number in MATRIX, resolve the Document record (or None if not found).
# Build a list of rows: {doc_number, doc_title, doc_obj, category, cells: {user_id: status}}
# Status for each cell: "acknowledged" | "dco_qualified" | "assigned" | "overdue" | "not_assigned"

# Categories are derived from the MATRIX order using a CATEGORY_GROUPS list defined
# in service.py that maps doc numbers to their category label.
```

Add a `MATRIX_CATEGORIES` ordered list to `service.py`:
```python
MATRIX_CATEGORIES = [
    ("Base Requirements", ["QM.SLQ035", "QM.SLQ027", "QM.SLQ002", "QM.SLQ053"]),
    ("Quality System Management", ["QM.SLQ001", "QM.SLQ014", "QM.SLQ016", "QM.SLQ017",
                                    "QM.SLQ018", "QM.SLQ037", "QM.SLQ025", "QM.SLQ038", "QM.SLQ028"]),
    # QM.SLQ004–QM.SLQ010 obsoleted by DCO095; replaced by QM.SLQ052
    ("Design and Development", ["QM.SLQ052", "QM.SLQ012", "QM.SLQ013",
                                  "QM.SLQ011", "QM.SLQ032", "QM.SLQ033", "QM.SLQ048", "QM.SLQ029", "QM.SLQ047"]),
    ("Manufacturing and Operations", ["QM.SLQ019", "QM.SLQ040", "QM.SLQ039", "QM.SLQ043",
                                       "QM.SLQ045", "QM.SLQ046", "QM.SLQ049", "QM.SLQ050", "QM.SLQ051", "QM.SLQ026"]),
    ("Supplier and Purchasing", ["QM.SLQ015", "QM.SLQ020"]),
    ("Commercial and Post-Market", ["QM.SLQ036", "QM.SLQ021", "QM.SLQ022", "QM.SLQ023", "QM.SLQ030"]),
]
```

Cell status logic:
- If user is not in the matrix for this doc → `"not_required"` (empty, no indicator)
- If user has an acknowledged assignment with `training_type == "dco_auto_qualified"` → `"dco_qualified"` (special badge)
- If user has any acknowledged assignment for this doc → `"acknowledged"`
- If user has an open (unacknowledged) assignment → `"assigned"` or `"overdue"` per due date
- Otherwise (required but no assignment) → `"not_assigned"`

Renders `admin/training/matrix.html`.

### 3D. New routes: GET + POST /training/effectiveness — Annual Effectiveness Review tracker

```python
@bp.get("/training/effectiveness")
@require_permission("training.manage")
def effectiveness_index():
    s = db_session()
    reviews = (
        s.query(EffectivenessReview)
        .order_by(EffectivenessReview.review_year.desc(), EffectivenessReview.review_date.desc())
        .all()
    )
    users = s.query(User).filter(User.is_active.is_(True)).order_by(User.email.asc()).all()
    return render_template("admin/training/effectiveness.html", reviews=reviews, users=users)


@bp.post("/training/effectiveness/create")
@require_permission("training.manage")
def effectiveness_create():
    ...  # Create EffectivenessReview, redirect back

@bp.post("/training/effectiveness/<int:review_id>/delete")
@require_permission("training.manage")
def effectiveness_delete(review_id: int):
    ...  # Delete, redirect back
```

### 3E. Update `manage_index` (GET /training)

Add to the context:
- `users_summary`: list of `{user, total, acknowledged, overdue}` for the per-user summary cards at the top of the manage page
- Link to `/training/matrix` and `/training/effectiveness`

---

## Task 4 — Template changes

### 4A. Update `app/eqms/templates/admin/training/new.html`

Add three new fields to the assignment creation form, below the existing fields and above the submit button:

**Training Type** (select):
```
Read and Acknowledge (default)
Interactive
DCO Auto-Qualified
Document Originator
```

**Source Reference** (text input, optional):
```
Placeholder: "e.g. DCO-096, DCO-045, Authored QM.SLQ053 Rev A"
Help text: "For DCO auto-qualification, enter the DCO number. For originator records, enter the document number. Optional for Read and Acknowledge."
```

**Acknowledged Date** (date input, optional — admin override):
```
Label: "Acknowledgment Date (leave blank to require employee to acknowledge)"
Help text: "Set a date to create a pre-acknowledged record (for historical records and DCO auto-qualifications). If blank, the assignment is sent to the employee as pending."
```

### 4B. Update `app/eqms/templates/admin/training/manage.html`

At the top, before the assignments table, add:
- A row of per-user summary cards: each card shows user name, completion bar (e.g. "12/18 acknowledged"), and a "View Record" link to `/training/user/<id>`
- A row of action links: "Training Matrix" | "Annual Reviews" | "Export CSV" | "New Assignment"

Also: in the assignment list rows, show a small badge for `training_type`:
- `dco_auto_qualified` → "DCO Auto" badge (blue)
- `document_originator` → "Originator" badge (purple)
- `interactive` → "Interactive" badge (amber)
- `read_acknowledge` → no badge (default, no visual noise)

Show `source_reference` as a small muted subtitle under the assignment title when present.

### 4C. New `app/eqms/templates/admin/training/user_detail.html`

Layout:
```
Breadcrumb: Dashboard > Training > [User Name]

Card: User Training Record — [Full Name / Email]
  Sub-header: [N acknowledged] of [M required] documents | Annual Reviews: [count]
  "Export CSV" button

Card: Required Training (per QM.SLQ053 Training Matrix)
  Table: Document | Rev | Required | Status | Acknowledged Date | Source
  - Group by category (Base, QSM, Design, etc.)
  - Status badge: Acknowledged (green) / DCO Auto (blue) / Assigned (amber) / Overdue (red) / Not Assigned (gray)
  - For acknowledged rows, show the acknowledged_at date and source_reference if present
  - For not-assigned rows, show an "Assign" button that links to /training/new prefilled

Card: Annual Effectiveness Reviews
  Table: Year | Date | Score | Result | Notes
  - "Add Review" button linking to /training/effectiveness
```

### 4D. New `app/eqms/templates/admin/training/matrix.html`

Layout:
```
Breadcrumb: Dashboard > Training > Matrix

Card header: Training Matrix
  Subtitle: Per QM.SLQ053 Appendix 1 — current training status

Horizontal scroll table:
  Column 1: Document (doc number + title)
  Columns 2-N: One column per active user (abbreviated name in header)

  Cell values (color coded):
    ✓ green  = acknowledged (any type)
    ★ blue   = DCO auto-qualified
    ○ amber  = assigned, pending
    ! red    = overdue
    · gray   = not assigned (but required)
    — white  = not required

  Category rows are bold/shaded section headers (no data cells).

Legend below the table.
"Assign Missing" button: opens /training/new (general assign page).
```

### 4E. New `app/eqms/templates/admin/training/effectiveness.html`

Layout:
```
Breadcrumb: Dashboard > Training > Annual Reviews

Card: Annual Effectiveness Reviews

Inline-editable form at top (same style as Upcoming Payments ledger):
  + Add Review → shows input row: User (select) | Year | Date | Score (/10) | Pass/Fail (auto from score) | Notes | Save | Cancel

Table of existing reviews:
  Columns: Year | Employee | Date | Score | Result | Notes | Actions (delete)
  Result badge: Pass (green) / Fail (red)
  Group by year (most recent first).
```

---

## Task 5 — Update manage page link in `_layout.html` or dashboard

In the admin navigation (wherever the Training module link is), add a sub-link or badge showing the count of overdue training items.

---

## Task 6 — Coordinator script: create team accounts

A script `scripts/_create_team_accounts.py` already exists in the repository. Run it as part of deployment:

```bash
python scripts/_create_team_accounts.py           # dry-run (verify first)
python scripts/_create_team_accounts.py --execute # create accounts
```

This creates 5 read-only (`staff` role) accounts with temporary password `Silq2026!`:

| Name | Email |
|---|---|
| Brian McVerry | Brianm@silq.tech |
| Na He | Nah@silq.tech |
| Chris Turner | Christ@silq.tech |
| Tom Downey | Tomd@silq.tech |
| Chuck Greiner | Chuckg@silq.tech |

The script is idempotent — re-running it skips accounts that already exist.

After running, Ethan distributes the temp password and each user changes it via the Profile page (`/admin/me`).

---

## Task 7 — Coordinator script: initialize training records

Create `scripts/_init_training_matrix.py`.

This script does the following when run with `--execute`:

1. Queries all active users.
2. For each user, determines their required doc numbers via `matrix_required_for_doc_numbers(user.email)`.
3. For each required doc number:
   - Resolves the current document revision.
   - Checks whether the user already has ANY training record (acknowledged or pending) for that document (any revision).
   - If no record exists → creates a **pending** assignment (not pre-acknowledged) dated today with training_type `"read_acknowledge"`.
4. Prints a summary: assignments created, users covered, documents matched/unmatched.

In dry-run mode (default, no `--execute`), prints what would be created without touching the DB.

This gives Ethan a clean base — every required assignment exists, pending acknowledgment, and he can then backdate/pre-acknowledge specific ones (e.g., DCO-qualified docs) through the UI.

---

## Verification checklist

- [ ] Migration applies cleanly (`alembic upgrade head`, single head)
- [ ] `python scripts/_create_team_accounts.py --execute` creates 5 staff accounts without errors
- [ ] Each new user can log in with the temp password and sees the read-only QMS
- [ ] `GET /admin/training/matrix` renders without error; cells are correctly colored per existing acknowledgment records
- [ ] `GET /admin/training/user/<id>` shows the correct required docs for that user's email
- [ ] `POST /admin/training/new` with `acknowledged_date` set creates a pre-acknowledged record (not sent to employee queue)
- [ ] `POST /admin/training/new` with `training_type=dco_auto_qualified` and `source_reference=DCO-096` creates a record with that type/source
- [ ] `GET /admin/training` manage page shows per-user summary cards with correct completion counts
- [ ] `GET /admin/training/effectiveness` renders; create/delete work
- [ ] `GET /my-training` still works for regular employees — only shows pending (unacknowledged) items
- [ ] `_init_training_matrix.py --dry-run` prints expected output; `--execute` creates assignments without duplicates
- [ ] All new routes protected by `require_permission("training.manage")`
- [ ] Existing tests pass; add smoke tests for new routes

---

## Notes on DCO auto-qualification workflow (for Ethan's use post-deploy)

After deployment, to record that a DCO signer is trained on a document via DCO:

1. Go to Training → New Assignment
2. Select the document and revision
3. Select the user
4. Set **Training Type** = "DCO Auto-Qualified"
5. Set **Source Reference** = "DCO-096" (or whichever DCO)
6. Set **Acknowledgment Date** = the DCO approval date (e.g., 2026-07-16)
7. Submit → creates a pre-acknowledged record with that date and source

This satisfies QM.SLQ053 §8.1–8.2: the eQMS record of DCO approval date + DCO number is the training record. No further action needed by the employee for that document.
