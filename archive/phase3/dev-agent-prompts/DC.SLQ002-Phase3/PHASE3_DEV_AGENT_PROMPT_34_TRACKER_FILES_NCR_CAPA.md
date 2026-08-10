# Prompt 34 — Tracker File Attachments, NRE Detail Cleanup, NCR→CAPA Integration

## Overview

Four focused changes, no cross-dependencies:

1. **NRE customer detail page** — remove the per-customer "Project Tracker" card; tighten the Sales Orders section into a clean summary card per order.
2. **File attachments on the NRE Invoice Tracker** — "Notes" column → "Files" column with per-entry attach/download.
3. **File attachments on the Purchasing Upcoming Payments ledger** — same treatment; add a "Files" column.
4. **NCR accordion embedded in CAPAs** — the CAPAs list page gains an NCR document section at the bottom; the dashboard NCRs card is redirected to the CAPAs page.

---

## Part A — NRE Customer Detail: remove Project Tracker, clean up Sales Orders

### A1. Remove the Project Tracker card from `app/eqms/templates/admin/nre_projects/detail.html`

Delete the entire block marked `{# ── Project Tracker ── #}` (the `<div class="card">` containing
the per-SO inline-edit table with `tk-amount`, `tk-date`, `tk-status`, `tk-notes` inputs and
the `tk-save` buttons). Also remove the `<script>` block at the bottom of the template that
drives those save buttons (the block using `nre_tracker_upsert` and `nre_tracker_patch`).

Remove the `<div style="height:14px;"></div>` spacer that followed the removed card.

### A2. Clean up the `nre_customer_detail` route (`app/eqms/modules/nre_projects/admin.py`)

Remove the loading of `tracker_by_order` and `invoice_statuses` from the detail route since
neither is referenced after the card deletion.  Keep `order_folder_ids` (used for the
📁 Documents links in the Sales Orders section).

### A3. Enhance the Sales Orders section in `detail.html`

Replace the existing per-order `<div>` block with a cleaner summary card for each order:

```
┌─────────────────────────────────────────────────────────┐
│  Order #0000315   2026-04-13   ● completed              │
│                                                         │
│  📁 Documents  |  + Upload PDF   (existing buttons)    │
│                                                         │
│  PDF Attachments (if any — existing list)               │
└─────────────────────────────────────────────────────────┘
```

Specifically:
- The order number, date, and status badge should be styled to stand out (16px bold for number,
  muted date, coloured status pill).  These are already present — just ensure the layout is
  readable with the new minimal card style.
- Show an attachment count badge next to the order number: `({{ attachments|length }} PDF{{ 's' if attachments|length != 1 }})` when there are attachments, muted.
- No other data fields (there are no order lines for NRE orders).

---

## Part B — File attachments on tracker entries (NRE + Purchasing)

### B1. New DB models and migration

Create migration `f2a3b4c5d6e7_tracker_file_attachments.py` (down_revision `e1f2a3b4c5d6`):

```python
def upgrade():
    op.create_table(
        "payment_entry_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_entry_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["payment_entry_id"], ["payment_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_pay_att_entry", "payment_entry_attachments", ["payment_entry_id"])

    op.create_table(
        "nre_tracker_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nre_entry_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["nre_entry_id"], ["nre_project_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_nre_att_entry", "nre_tracker_attachments", ["nre_entry_id"])
```

Add the corresponding SQLAlchemy models:

**`app/eqms/modules/purchasing/models.py`** — add `PaymentEntryAttachment`:
```python
class PaymentEntryAttachment(Base):
    __tablename__ = "payment_entry_attachments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_entry_id: Mapped[int] = mapped_column(ForeignKey("payment_entries.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    entry: Mapped["PaymentEntry"] = relationship("PaymentEntry", back_populates="attachments")
```
Also add `attachments: Mapped[list["PaymentEntryAttachment"]] = relationship("PaymentEntryAttachment", back_populates="entry", cascade="all, delete-orphan", lazy="selectin")` to `PaymentEntry`.

**`app/eqms/modules/nre_projects/models.py`** — add `NRETrackerAttachment`:
```python
class NRETrackerAttachment(Base):
    __tablename__ = "nre_tracker_attachments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nre_entry_id: Mapped[int] = mapped_column(ForeignKey("nre_project_entries.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    entry: Mapped["NREProjectEntry"] = relationship("NREProjectEntry", back_populates="attachments")
```
Also add `attachments: Mapped[list["NRETrackerAttachment"]] = relationship(...)` to `NREProjectEntry`.

Register both new models with a `# noqa: F401` import in `app/eqms/__init__.py`.

### B2. File attachment routes — Purchasing (`app/eqms/modules/purchasing/admin.py`)

```python
# POST /admin/purchasing/payments/<entry_id>/files  — upload
@bp.post("/payments/<int:entry_id>/files")
@require_permission("purchasing.edit")
def payment_attach_file(entry_id: int): ...

# GET  /admin/purchasing/payments/files/<att_id>/view
@bp.get("/payments/files/<int:att_id>/view")
@require_permission("purchasing.view")
def payment_file_view(att_id: int): ...

# GET  /admin/purchasing/payments/files/<att_id>/download
@bp.get("/payments/files/<int:att_id>/download")
@require_permission("purchasing.view")
def payment_file_download(att_id: int): ...

# POST /admin/purchasing/payments/files/<att_id>/delete
@bp.post("/payments/files/<int:att_id>/delete")
@require_permission("purchasing.edit")
def payment_file_delete(att_id: int): ...
```

Upload implementation: read `request.files["file"]`, enforce 50 MB limit, store to S3 at key
`purchasing/payment_files/<entry_id>/<filename>`, create `PaymentEntryAttachment` row.
Use `allow_inline_view` from `app.eqms.utils` for the view route (same pattern as
`nre_view_pdf`/`nre_download_pdf` in the NRE module).
After upload or delete, redirect back to `url_for('purchasing.purchasing_list')`.

### B3. File attachment routes — NRE (`app/eqms/modules/nre_projects/admin.py`)

Same pattern, prefixed differently:
```
POST  /admin/nre_projects/tracker/<entry_id>/files   → nre_tracker_attach_file
GET   /admin/nre_projects/tracker/files/<att_id>/view → nre_tracker_file_view
GET   /admin/nre_projects/tracker/files/<att_id>/download → nre_tracker_file_download
POST  /admin/nre_projects/tracker/files/<att_id>/delete  → nre_tracker_file_delete
```
Storage key: `nre/tracker_files/<entry_id>/<filename>`.
After upload or delete, redirect to `url_for('nre_projects.nre_projects_index')`.

### B4. Load attachments in the index routes

**Purchasing `purchasing_list()`** — after loading `payment_entries`, load a dict:
```python
from app.eqms.modules.purchasing.models import PaymentEntryAttachment
entry_ids = [e.id for e in payment_entries]
atts = s.query(PaymentEntryAttachment).filter(PaymentEntryAttachment.payment_entry_id.in_(entry_ids)).all()
attachments_by_payment: dict[int, list[PaymentEntryAttachment]] = defaultdict(list)
for a in atts:
    attachments_by_payment[a.payment_entry_id].append(a)
```
Pass `attachments_by_payment` to the template.

**NRE `nre_projects_index()`** — same pattern with `NRETrackerAttachment`:
```python
entry_ids = [e.id for e in tracker_entries]
atts = s.query(NRETrackerAttachment).filter(NRETrackerAttachment.nre_entry_id.in_(entry_ids)).all()
attachments_by_nre: dict[int, list[NRETrackerAttachment]] = defaultdict(list)
for a in atts:
    attachments_by_nre[a.nre_entry_id].append(a)
```
Pass `attachments_by_nre` to the template.

### B5. Template changes — Purchasing `list.html`

In the Upcoming Payments table:
- **Add a new "Files" column header** (after "Due Date", before "Actions").
- In each existing row's data cells, add a "Files" `<td>` containing:
  - For each attachment: `📄 <a href=view_url>filename</a> <a href=dl_url>↓</a>` (one per line, small font).
  - Below the files list, a small inline upload form (always visible, not gated on edit mode):
    ```html
    <form method="post" action="{{ url_for('purchasing.payment_attach_file', entry_id=e.id) }}"
          enctype="multipart/form-data" style="display:inline;">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <input type="file" name="file" style="display:none;" id="pf-{{ e.id }}"
             onchange="this.form.submit()">
      <label for="pf-{{ e.id }}" class="button button--small button--secondary"
             style="cursor:pointer;">📎</label>
    </form>
    ```
    (The label acts as the trigger; selecting a file auto-submits. This avoids a modal.)
  - For each attachment, also a delete form:
    ```html
    <form method="post" action="{{ url_for('purchasing.payment_file_delete', att_id=a.id) }}"
          style="display:inline;" onsubmit="return confirm('Delete file?')">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <button class="link-btn" style="color:#b42318; font-size:11px;">×</button>
    </form>
    ```
- Update the `<template id="pay-row-template">` (used for new rows) to include the
  Files `<td>` with just the `📎` upload form (using a placeholder entry id of `0`; after save
  the page reloads so the real id becomes available).
- Adjust all `colspan` values in empty-state rows to account for the new column.

### B6. Template changes — NRE `index.html`

Apply the identical Files column treatment to the NRE Invoice Tracker table:
- The existing "Notes" column header (8th column) becomes **"Files"**.
- The existing `<input class="te" data-field="notes">` in the row and in
  `<template id="nre-row-template">` is **removed** (the notes free-text field is dropped;
  if any existing entries have notes text, it will remain in the DB but not be displayed).
- The Files `<td>` shows attachments + `📎` upload form exactly as in B5.
- Routes: `nre_tracker_attach_file` / `nre_tracker_file_delete`.
- Adjust `colspan` on the empty-state row.

---

## Part C — NCR accordion embedded in CAPAs

### C1. Extract NCR library data in `capas_list()` (`app/eqms/modules/capas/admin.py`)

Import the admin_docs models and replicate the accordion data-loading logic inline
(do not import from admin_docs.admin — that module calls render_template directly):

```python
from collections import defaultdict
from app.eqms.modules.admin_docs.models import AdminDocFolder, AdminDocFile

# Load NCR accordion data
ncr_folders = s.query(AdminDocFolder).filter(AdminDocFolder.library_key == "ncrs").order_by(AdminDocFolder.name).all()
ncr_files_all = s.query(AdminDocFile).filter(AdminDocFile.library_key == "ncrs").all()
ncr_folders_by_id = {f.id: f for f in ncr_folders}
ncr_children_by_parent = defaultdict(list)
for f in ncr_folders:
    ncr_children_by_parent[f.parent_id].append(f)
ncr_files_by_folder = defaultdict(list)
for fi in ncr_files_all:
    ncr_files_by_folder[fi.folder_id].append(fi)
    ncr_files_by_folder[fi.folder_id].sort(key=lambda x: (x.filename or "").lower())
ncr_root_folders = ncr_children_by_parent.get(None, [])
ncr_root_files = ncr_files_by_folder.get(None, [])
```

Pass these six variables to the template: `ncr_folders_by_id`, `ncr_children_by_parent`,
`ncr_files_by_folder`, `ncr_root_folders`, `ncr_root_files`.

### C2. Render NCR accordion in `app/eqms/templates/admin/capas/list.html`

After the existing CAPA table card, add a separator and a new section:

```html
<div style="height:14px;"></div>

<div class="card">
  <h2 style="margin-top:0;">Non-Conformance Reports</h2>

  {# Reuse the same render_folder macro from accordion.html, or inline a simplified version #}
  {% macro ncr_file_row(f) %}
    <li style="display:flex; align-items:center; gap:8px; padding:4px 0;">
      <a href="{{ url_for('admin_docs.admin_docs_document_view', doc_id=f.id) }}">📄 {{ f.filename|e }}</a>
      <a class="button button--small button--secondary"
         href="{{ url_for('admin_docs.admin_docs_document_download', doc_id=f.id) }}" title="Download">↓</a>
    </li>
  {% endmacro %}

  {% macro ncr_render_folder(fid, depth) %}
    {% set folder = ncr_folders_by_id.get(fid) %}
    {% set kids = ncr_children_by_parent.get(fid, []) %}
    {% set files = ncr_files_by_folder.get(fid, []) %}
    <details class="accordion-folder" style="margin-left: {{ depth * 16 }}px;"
             {% if depth == 0 %}open{% endif %}>
      <summary class="accordion-summary">
        <span class="accordion-label">📁 {{ folder.name|e }}</span>
        <span class="muted" style="font-size:12px; font-weight:400;">{{ files|length }} file{{ '' if files|length == 1 else 's' }}</span>
      </summary>
      {% if files %}
        <ul class="accordion-files" style="list-style:none; padding:0 0 0 8px; margin:4px 0;">
          {% for f in files %}{{ ncr_file_row(f) }}{% endfor %}
        </ul>
      {% endif %}
      {% for child in kids %}{{ ncr_render_folder(child.id, depth + 1) }}{% endfor %}
    </details>
  {% endmacro %}

  {% if ncr_root_files %}
    <ul class="accordion-files" style="list-style:none; padding:0; margin:0 0 8px;">
      {% for f in ncr_root_files %}{{ ncr_file_row(f) }}{% endfor %}
    </ul>
  {% endif %}
  {% for folder in ncr_root_folders %}{{ ncr_render_folder(folder.id, 0) }}{% endfor %}
  {% if not ncr_root_files and not ncr_root_folders %}
    <p class="muted" style="margin:0;">No NCR documents uploaded yet.</p>
  {% endif %}
</div>
```

### C3. Update the dashboard NCRs card (`app/eqms/templates/admin/index.html`)

Change the NCRs card `href` from `url_for('admin_docs.ncrs')` to
`url_for('capas.capas_list')` so the card navigates directly to the integrated view.
The card title and subtitle stay the same.

---

## Commit

Single commit:
```
P34: tracker file attachments, NRE detail cleanup, NCR embedded in CAPAs
```

Then push to `main`.
