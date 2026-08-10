# Prompt 31 — NRE Projects: Fix Misclassification, Tracker, Admin_docs Integration

> **Note**: Disregard Prompt 29 — it was executed separately and its changes are already live.
> This is the active prompt. Begin here.

---

## Overview

Four work areas:

| Section | Scope |
|---|---|
| A | DB migration — `customer_type` on `Customer`, new `NREProjectEntry` model |
| B | Fix 3 misclassified customers (coordinator scripts) |
| C | NRE admin_docs library + folder scaffold (coordinator script) |
| D | NRE module redesign — tracker inline on detail page, admin_docs folder links |

---

## SECTION A — Alembic Migration

### A1. `Customer` model — add `customer_type`

File: `app/eqms/modules/customer_profiles/models.py`

Add one column after `customer_code`:
```python
customer_type: Mapped[str] = mapped_column(
    Text, nullable=False, server_default="auto", default="auto"
)
```

Valid values: `"auto"`, `"catheter"`, `"nre"`.
- `"auto"` (default): NRE classification determined by whether any linked SalesOrder has a matched DistributionLogEntry (existing logic).
- `"catheter"`: Always shown in catheter distributions views; excluded from NRE regardless of distribution entries.
- `"nre"`: Always shown in NRE Projects; never auto-promoted to catheter even if distributions are later linked.

### A2. New model: `NREProjectEntry`

File: `app/eqms/modules/nre_projects/models.py` (create new file)

```python
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.eqms.models import Base
from app.eqms.utils import utcnow

INVOICE_STATUSES = ["Pending Invoice", "Invoiced", "Paid", "Cancelled"]

class NREProjectEntry(Base):
    __tablename__ = "nre_project_entries"
    __table_args__ = (
        Index("idx_nre_entries_order", "sales_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sales_order_id: Mapped[int] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    invoice_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    expected_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    invoice_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="Pending Invoice"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=utcnow, onupdate=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    sales_order: Mapped["SalesOrder"] = relationship("SalesOrder", lazy="selectin")
```

Import `NREProjectEntry` in `app/eqms/modules/nre_projects/__init__.py` and register with `Base.metadata` by importing the model in `app/eqms/__init__.py` alongside other module imports.

### A3. Generate migration

```
flask db migrate -m "add customer_type, nre_project_entries"
flask db upgrade
```

---

## SECTION B — Fix 3 Misclassified Customers

### B1. Coordinator script: `scripts/_fix_nre_scionti.py`

**Root cause**: The PDF parser read Scionti's address line `6600 UNIVERSITY PKWY STE 203` and stored the order number as `"6600"` instead of the actual sales order number. The correct SO is `0000202` — confirmed by a DistributionLogEntry (id=788) with `order_number='SO 0000202'`, `facility_name='SCIONTI PROSTATE CENTER'`, `sales_order_id=None`.

**Logic (dry-run by default, `--execute` to write)**:

1. Find `SalesOrder` where `order_number == "6600"` and `customer.facility_name ILIKE '%scionti%'`.
2. Check that no other SO with `order_number == "0000202"` exists for this customer (to avoid duplicate).
3. Update that SalesOrder:
   - `order_number = "0000202"`
   - `external_key = "pdf:0000202"`
4. Find `DistributionLogEntry` with `id == 788` (confirm it has `sales_order_id IS NULL` and `order_number == 'SO 0000202'`).
5. Link it: set `dist_entry.sales_order_id = so.id`, `dist_entry.customer_id = customer.id`.
6. Commit. Print summary.

After this fix, Scionti will have a matched distribution entry and will automatically be excluded from the NRE index (no `customer_type` override needed).

### B2. Coordinator script: `scripts/_fix_nre_acaring_swchest.py`

**Root cause**: A Caring Hand Home Health (SO #0000179) and Southern Westchester Urology (SO #0000184) are catheter customers whose orders came via PDF (not ShipStation), so no DistributionLogEntry was ever created. The auto-classification logic therefore treats them as NRE. The override field resolves this cleanly.

**Logic (dry-run by default, `--execute` to write)**:

1. For each of these two customer names (`'A Caring Hand Home Health'`, `'Southern Westchester Urology'`):
   - Find `Customer` by `facility_name` (exact or ILIKE).
   - Set `customer.customer_type = "catheter"`.
2. Commit. Print summary.

### B3. Update NRE classification query

File: `app/eqms/modules/nre_projects/admin.py` → `nre_projects_index()`

The current query finds customers with orders but no matched distributions. Update it to also:
- **Exclude** customers with `customer_type == "catheter"`
- **Always include** customers with `customer_type == "nre"` (even if they have distributions)

```python
from sqlalchemy import or_

# Build the query differently based on customer_type:
# "auto" customers: existing distribution-matching logic
# "catheter" customers: always excluded
# "nre" customers: always included

auto_nre_customer_ids = (
    s.query(Customer.id)
    .filter(Customer.customer_type == "auto")
    .filter(Customer.id.in_(customers_with_orders))
    .filter(~Customer.id.in_(customers_with_matched_distributions))
    .subquery()
)

forced_nre_customer_ids = (
    s.query(Customer.id)
    .filter(Customer.customer_type == "nre")
    .subquery()
)

nre_customers = (
    s.query(Customer)
    .filter(
        or_(
            Customer.id.in_(auto_nre_customer_ids),
            Customer.id.in_(forced_nre_customer_ids),
        )
    )
    .order_by(Customer.facility_name.asc())
    .all()
)
```

Also update the `nre_customer_detail()` route's edit form to expose the `customer_type` field (dropdown: Auto / Force Catheter / Force NRE).

---

## SECTION C — NRE Admin_docs Library + Folder Scaffold

### C1. Register `nre_projects` library

File: `app/eqms/modules/admin_docs/admin.py`

1. Add to `LIBRARIES`:
   ```python
   "nre_projects": "NRE Project Documents",
   ```

2. Add to `LIBRARY_ENDPOINTS`:
   ```python
   "nre_projects": "admin_docs.nre_project_docs",
   ```

3. Add route (standard folder-by-folder view, NOT accordion):
   ```python
   @bp.get("/nre-projects")
   @require_any_permission("sales_orders.view", "admin.view")
   def nre_project_docs():
       return _render_library("nre_projects")
   ```

### C2. Coordinator script: `scripts/_scaffold_nre_folders.py`

Create the admin_docs folder structure for all current NRE customers and their sales orders.

**Logic (dry-run by default, `--execute` to write)**:

1. Query all current NRE customers (same logic as `nre_projects_index()` — `customer_type == "nre"` OR auto-NRE).
2. For each customer:
   - Folder name: `"{facility_name}"` (e.g., `"AbbVie Inc."`)
   - Check if an `AdminDocFolder` with this name, `library_key="nre_projects"`, `parent_id=None` exists. If not, create it.
3. For each SalesOrder under that customer:
   - Subfolder name: `"SO-{order_number}"` (e.g., `"SO-0000XXX"`)
   - Check if this subfolder exists under the customer folder. If not, create it.
4. Print created/skipped counts.

**Also add a web route for in-app refresh**:

File: `app/eqms/modules/nre_projects/admin.py`

Add a POST route `/nre-projects/refresh-folders`:
```python
@bp.post("/refresh-folders")
@require_permission("sales_orders.edit")
def nre_refresh_folders():
    """Create any missing admin_docs folders for NRE customers + orders."""
    # ... same logic as the coordinator script, run inline ...
    flash(f"Folders refreshed: {created} created, {skipped} already existed.", "success")
    return redirect(url_for("nre_projects.nre_projects_index"))
```

---

## SECTION D — NRE Module Redesign

### D1. NRE Project Tracker — new routes in `nre_projects/admin.py`

Add CRUD routes for `NREProjectEntry`:

**Create/upsert** (POST `/nre-projects/<customer_id>/tracker`):
- Accepts `sales_order_id`, `invoice_amount`, `expected_invoice_date`, `invoice_status`, `notes`.
- If an `NREProjectEntry` already exists for this `sales_order_id`, update it. Otherwise create it.
- Returns JSON `{"ok": true, "entry": {...}}` for inline JS handling.

**Inline patch** (PATCH `/nre-projects/tracker/<entry_id>`):
- Accepts JSON body with any subset of fields to update.
- Returns JSON `{"ok": true}`.

**Delete** (DELETE `/nre-projects/tracker/<entry_id>`):
- Removes the entry.
- Returns JSON `{"ok": true}`.

### D2. NRE Index page update

File: `app/eqms/templates/admin/nre_projects/index.html`

Add two elements:
1. A **"Refresh Folders"** button (POST form) in the header action area, next to "← Back to Admin".
2. Update the subtitle from `"Engineering customers with sales orders but no catheter distributions."` to `"NRE projects and engineering engagements."` (removing the technical description).

### D3. NRE Customer Detail page redesign

File: `app/eqms/templates/admin/nre_projects/detail.html`

**Add a "Project Tracker" card** between the header and the SO cards:

The tracker is a table with one row per SalesOrder. Each row has:
- **Order #** (read-only): monospace badge `<code>SO-{order.order_number}</code>`
- **Date**: `order.order_date`
- **Invoice Amount**: inline-editable currency input (blank = TBD)
- **Expected Invoice Date**: inline-editable date input
- **Status**: dropdown (`Pending Invoice` / `Invoiced` / `Paid` / `Cancelled`) styled as a colored badge
- **Notes**: single-line text input
- **Documents**: link icon that navigates to the admin_docs subfolder for this SO (if it exists)

Inline editing behaviour (same pattern as purchasing payment ledger):
- All fields are editable in-place via `<input>` / `<select>` elements.
- A "Save" button per row submits a PATCH to `/nre-projects/tracker/<entry_id>` (or POST to create if no entry exists yet).
- On success, flash a brief inline confirmation.

The JS should auto-create an entry on first save if one doesn't exist, using the CREATE route.

Status badge colors:
- `Pending Invoice` → yellow/warning
- `Invoiced` → blue/info
- `Paid` → green/success
- `Cancelled` → gray/muted

**Admin_docs folder link per SO**:

The `nre_customer_detail()` route should also query for the admin_docs folder for each order:
```python
from app.eqms.modules.admin_docs.models import AdminDocFolder

# Find the customer-level folder
cust_folder = (
    s.query(AdminDocFolder)
    .filter(
        AdminDocFolder.library_key == "nre_projects",
        AdminDocFolder.parent_id.is_(None),
        AdminDocFolder.name == customer.facility_name,
    )
    .first()
)

# Find per-order subfolders
order_folder_ids: dict[int, int] = {}  # order.id -> folder.id
if cust_folder:
    for order in orders:
        subfolder = (
            s.query(AdminDocFolder)
            .filter(
                AdminDocFolder.library_key == "nre_projects",
                AdminDocFolder.parent_id == cust_folder.id,
                AdminDocFolder.name == f"SO-{order.order_number}",
            )
            .first()
        )
        if subfolder:
            order_folder_ids[order.id] = subfolder.id
```

Pass `cust_folder=cust_folder`, `order_folder_ids=order_folder_ids` to the template. In the tracker table row:

```html
{% if order.id in order_folder_ids %}
<a href="{{ url_for('admin_docs.nre_project_docs', folder_id=order_folder_ids[order.id]) }}"
   class="button button--secondary" style="font-size:11px; padding:4px 8px;" title="View Documents">
   📁 Docs
</a>
{% else %}
<span class="muted" style="font-size:11px;">No folder</span>
{% endif %}
```

**Edit Customer modal update**: Add a `customer_type` dropdown to the existing "Edit Customer" modal:

```html
<div class="label">Classification Override</div>
<select name="customer_type" style="margin-bottom:16px;">
  <option value="auto" {% if customer.customer_type == 'auto' %}selected{% endif %}>Auto (distribution-based)</option>
  <option value="nre" {% if customer.customer_type == 'nre' %}selected{% endif %}>Force NRE</option>
  <option value="catheter" {% if customer.customer_type == 'catheter' %}selected{% endif %}>Force Catheter</option>
</select>
```

Update `nre_customer_edit()` to save this field.

---

## EXECUTION ORDER

1. **Dev agent**: Apply migration (A1–A3), implement code changes (B3, C1, D1–D3). Deploy.
2. **After deploy** — run coordinator scripts:
   ```
   python scripts/_fix_nre_scionti.py --execute
   python scripts/_fix_nre_acaring_swchest.py --execute
   python scripts/_scaffold_nre_folders.py --execute
   ```
3. Verify: Scionti disappears from NRE index (now has distribution entry), ACARING and SWCHEST disappear (customer_type=catheter), remaining NRE customers have admin_docs folders.

---

## Key Technical Notes

- **`NREProjectEntry` uniqueness**: One entry per `sales_order_id` (enforced by DB UNIQUE constraint). The upsert route handles create-or-update.
- **`admin_docs.nre_project_docs` is NOT accordion**: This means `?folder_id=N` IS respected and can be used for deep-linking to per-order subfolders from the tracker table. The folder_id links work correctly here (unlike the work_orders accordion case).
- **Scionti's SO external_key**: Update from `"pdf:6600"` to `"pdf:0000202"` to keep the unique constraint valid. The `(source, external_key)` unique index on `sales_orders` must be satisfied.
- **NRE classification does NOT change for existing catheter customers**: Adding `customer_type` with `server_default="auto"` means all existing customers remain classified by the current distribution-matching logic unless explicitly overridden.
- **`NREProjectEntry` import**: Add `from app.eqms.modules.nre_projects.models import NREProjectEntry` to `app/eqms/__init__.py` near the other module model imports, to ensure Alembic detects the new table.
