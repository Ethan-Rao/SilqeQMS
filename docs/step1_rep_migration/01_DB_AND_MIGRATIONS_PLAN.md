# Database and Migrations Plan for REP Traceability

**Date:** 2026-01-15  
**Purpose:** Plan for adding REP traceability tables (Distribution Log, Tracing Reports, Approval Evidence) to SilqeQMS database using Alembic

---

## Decision: Alembic Now (Recommended)

**Status:** ✅ Alembic is already present and configured in the codebase.

**Evidence:**
- `alembic.ini` exists and is configured for `migrations/` directory
- `migrations/env.py` exists with proper Base metadata import
- `migrations/versions/56a470f9ee55_initial_schema.py` baseline migration exists
- `scripts/init_db.py` already runs `alembic upgrade head` before seeding

**Recommendation:** Use Alembic now to add REP tables. This ensures:
- Version-controlled schema changes
- Reversible migrations (downgrade support)
- Consistency with existing document_control module
- Production-ready deployment path

---

## Migration Strategy

### Migration File Creation

**Command:**
```bash
alembic revision -m "add rep traceability tables"
```

This creates a new migration file in `migrations/versions/` with a unique revision ID.

**Prerequisites:**
- Ensure `DATABASE_URL` is set (or defaults to `sqlite:///eqms.db` for local dev)
- Alembic can read `app.eqms.models.Base.metadata` (models must be imported in `app/eqms/models.py`)

---

## Migration Contents: REP Tables

### Table 1: `distribution_log_entries`

**Source:** `docs/REP_SYSTEM_MINIMAL_SCHEMA.md` (lines 22-76)

**SQL (Postgres-compatible, works on SQLite via `render_as_batch`):**

```python
def upgrade() -> None:
    # Distribution Log Entries
    op.create_table(
        "distribution_log_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        
        # Required fields
        sa.Column("ship_date", sa.Date(), nullable=False),
        sa.Column("order_number", sa.Text(), nullable=False),
        sa.Column("facility_name", sa.Text(), nullable=False),
        sa.Column("rep_id", sa.Integer(), nullable=True),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("lot_number", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        
        # Optional fields
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("address1", sa.Text(), nullable=True),
        sa.Column("address2", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("zip", sa.Text(), nullable=True),
        sa.Column("country", sa.Text(), nullable=True, server_default="USA"),
        sa.Column("contact_name", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("tracking_number", sa.Text(), nullable=True),
        sa.Column("ss_shipment_id", sa.Text(), nullable=True),
        sa.Column("evidence_file_storage_key", sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(["rep_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),  # If customers table exists
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        
        # Constraints
        sa.CheckConstraint("sku IN ('211810SPT', '211610SPT', '211410SPT')", name="ck_distribution_log_sku"),
        sa.CheckConstraint("lot_number ~ '^SLQ-\\d{5}$'", name="ck_distribution_log_lot"),  # Postgres regex
        # SQLite: use Python validation instead, or remove CHECK constraint for SQLite compatibility
        sa.CheckConstraint("quantity > 0", name="ck_distribution_log_quantity"),
        sa.CheckConstraint("source IN ('shipstation', 'manual', 'csv_import', 'pdf_import')", name="ck_distribution_log_source"),
        
        # Unique constraints
        sa.UniqueConstraint("ss_shipment_id", name="uq_distribution_log_ss_shipment_id", postgresql_where=sa.text("ss_shipment_id IS NOT NULL")),
    )
    
    # Indexes
    op.create_index("idx_distribution_log_ship_date", "distribution_log_entries", ["ship_date"])
    op.create_index("idx_distribution_log_source", "distribution_log_entries", ["source"])
    op.create_index("idx_distribution_log_rep_id", "distribution_log_entries", ["rep_id"])
    op.create_index("idx_distribution_log_customer_id", "distribution_log_entries", ["customer_id"])
    op.create_index("idx_distribution_log_sku", "distribution_log_entries", ["sku"])
    op.create_index("idx_distribution_log_order_number", "distribution_log_entries", ["order_number"])
```

**Note:** SQLite does not support PostgreSQL CHECK constraints with regex or partial unique constraints. Use `render_as_batch=True` in `env.py` (already configured) to handle these gracefully. For SQLite, validation must be enforced in application code.

---

### Table 2: `tracing_reports`

**Source:** `docs/REP_SYSTEM_MINIMAL_SCHEMA.md` (lines 114-176)

**SQL:**

```python
def upgrade() -> None:
    # Tracing Reports
    op.create_table(
        "tracing_reports",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        
        # Report generation metadata
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("generated_by_user_id", sa.Integer(), nullable=True),
        
        # Filters used to generate report
        sa.Column("filters_json", sa.JSON(), nullable=False),  # JSON on SQLite, JSONB on Postgres
        
        # Report file metadata
        sa.Column("report_storage_key", sa.Text(), nullable=False),
        sa.Column("report_format", sa.Text(), nullable=False, server_default="csv"),
        
        # Report status
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        
        # Foreign keys
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        
        # Constraints
        sa.CheckConstraint("report_format = 'csv'", name="ck_tracing_reports_format"),
        sa.CheckConstraint("status IN ('draft', 'final')", name="ck_tracing_reports_status"),
    )
    
    # Indexes
    op.create_index("idx_tracing_reports_generated_at", "tracing_reports", ["generated_at"])
    op.create_index("idx_tracing_reports_status", "tracing_reports", ["status"])
    # Note: GIN index on filters_json for Postgres JSONB queries (not supported on SQLite)
    # For SQLite, use application-level filtering
```

**Note:** JSONB GIN indexes are Postgres-only. For SQLite, use application-level JSON filtering. The `filters_json` column stores JSON as TEXT on SQLite, JSONB on Postgres.

---

### Table 3: `approvals_eml`

**Source:** `docs/REP_SYSTEM_MINIMAL_SCHEMA.md` (lines 179-232)

**SQL:**

```python
def upgrade() -> None:
    # Approval EML Files
    op.create_table(
        "approvals_eml",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        
        # Link to tracing report
        sa.Column("report_id", sa.Integer(), nullable=False),
        
        # File metadata
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        
        # Extracted email metadata (from .eml file headers)
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("from_email", sa.Text(), nullable=True),
        sa.Column("to_email", sa.Text(), nullable=True),
        sa.Column("email_date", sa.DateTime(timezone=True), nullable=True),
        
        # Upload metadata
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        
        # Foreign keys
        sa.ForeignKeyConstraint(["report_id"], ["tracing_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    
    # Indexes
    op.create_index("idx_approvals_eml_report_id", "approvals_eml", ["report_id"])
    op.create_index("idx_approvals_eml_uploaded_at", "approvals_eml", ["uploaded_at"])
```

---

## Complete Migration `upgrade()` Function

**File:** `migrations/versions/<revision>_add_rep_traceability_tables.py`

```python
"""add rep traceability tables

Revision ID: <revision>
Revises: 56a470f9ee55
Create Date: <timestamp>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '<revision>'
down_revision: Union[str, Sequence[str], None] = '56a470f9ee55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create distribution_log_entries table (see above SQL)
    # Create tracing_reports table (see above SQL)
    # Create approvals_eml table (see above SQL)
    pass


def downgrade() -> None:
    op.drop_table("approvals_eml")
    op.drop_table("tracing_reports")
    op.drop_table("distribution_log_entries")
```

---

## Downgrade Strategy

**Command:**
```bash
alembic downgrade -1
```

**Implementation:**
- Drop tables in reverse order (approvals_eml → tracing_reports → distribution_log_entries)
- Indexes are automatically dropped with tables

---

## Model Import Chain (for Alembic Autogenerate)

**Step 1:** Create `app/eqms/modules/rep_traceability/models.py` with SQLAlchemy models

**Step 2:** Import models in `app/eqms/models.py` tail:

```python
# Ensure module models are imported so Base.metadata includes their tables.
from app.eqms.modules.rep_traceability.models import (
    DistributionLogEntry,
    TracingReport,
    ApprovalEml,
)
```

**Why:** Alembic `env.py` imports `Base` from `app.eqms.models`, so all module models must be imported there for autogenerate to detect schema changes.

---

## Seed Actions: Permissions & Roles

### Update `scripts/init_db.py`

**Add permission creation (idempotent):**

```python
# REP Traceability Permissions
p_dist_log_view = ensure_perm("distribution_log.view", "Distribution Log: view")
p_dist_log_create = ensure_perm("distribution_log.create", "Distribution Log: create")
p_dist_log_edit = ensure_perm("distribution_log.edit", "Distribution Log: edit")
p_dist_log_delete = ensure_perm("distribution_log.delete", "Distribution Log: delete")
p_dist_log_export = ensure_perm("distribution_log.export", "Distribution Log: export")

p_tracing_view = ensure_perm("tracing_reports.view", "Tracing Reports: view")
p_tracing_generate = ensure_perm("tracing_reports.generate", "Tracing Reports: generate")
p_tracing_download = ensure_perm("tracing_reports.download", "Tracing Reports: download")

p_approvals_view = ensure_perm("approvals.view", "Approvals: view")
p_approvals_upload = ensure_perm("approvals.upload", "Approvals: upload")
```

**Grant all REP permissions to `admin` role:**

```python
# Grant all REP permissions to admin role
for p in (
    p_dist_log_view, p_dist_log_create, p_dist_log_edit, p_dist_log_delete, p_dist_log_export,
    p_tracing_view, p_tracing_generate, p_tracing_download,
    p_approvals_view, p_approvals_upload,
):
    if p not in role_admin.permissions:
        role_admin.permissions.append(p)
```

**Optional: Create additional roles per UI map:**

```python
# Quality role (full access, same as admin)
role_quality = s.query(Role).filter(Role.key == "quality").one_or_none()
if not role_quality:
    role_quality = Role(key="quality", name="Quality")
    s.add(role_quality)
# Grant all REP permissions to quality role
for p in (p_dist_log_view, p_dist_log_create, ..., p_approvals_upload):
    if p not in role_quality.permissions:
        role_quality.permissions.append(p)

# Ops role (limited: all REP permissions, no user management)
role_ops = s.query(Role).filter(Role.key == "ops").one_or_none()
if not role_ops:
    role_ops = Role(key="ops", name="Operations")
    s.add(role_ops)
# Grant all REP permissions to ops role
for p in (p_dist_log_view, p_dist_log_create, ..., p_approvals_upload):
    if p not in role_ops.permissions:
        role_ops.permissions.append(p)

# ReadOnly role (view-only access)
role_readonly = s.query(Role).filter(Role.key == "readonly").one_or_none()
if not role_readonly:
    role_readonly = Role(key="readonly", name="Read Only")
    s.add(role_readonly)
# Grant view-only permissions to readonly role
for p in (p_dist_log_view, p_tracing_view, p_tracing_download, p_approvals_view):
    if p not in role_readonly.permissions:
        role_readonly.permissions.append(p)
```

---

## Execution Steps

### Step 1: Create Models

```bash
# Create module directory
mkdir -p app/eqms/modules/rep_traceability

# Create models.py (see Task 1.2 in checklist)
```

### Step 2: Import Models in Base

Edit `app/eqms/models.py` to import REP models at bottom.

### Step 3: Create Migration

```bash
alembic revision -m "add rep traceability tables"
```

Edit the generated migration file with SQL from above.

### Step 4: Test Migration

```bash
# Upgrade
alembic upgrade head

# Verify tables exist (SQLite)
sqlite3 eqms.db ".tables"

# Downgrade
alembic downgrade -1

# Verify tables dropped
sqlite3 eqms.db ".tables"

# Upgrade again
alembic upgrade head
```

### Step 5: Update Seed Script

Edit `scripts/init_db.py` to add REP permissions and role grants.

### Step 6: Run Seed Script

```bash
python scripts/init_db.py
```

Verify permissions and roles in database.

---

## SQLite Compatibility Notes

**Known Limitations:**
- PostgreSQL CHECK constraints with regex (`lot_number ~ '^SLQ-\\d{5}$'`) are not supported on SQLite. Use `render_as_batch=True` in `env.py` (already configured) or remove CHECK constraint and validate in application code.
- PostgreSQL partial unique constraints (`UNIQUE(ss_shipment_id) WHERE ss_shipment_id IS NOT NULL`) are not supported on SQLite. Use application-level uniqueness checks or remove constraint.
- JSONB GIN indexes are Postgres-only. For SQLite, use application-level JSON filtering.

**Recommendation:** Keep schema Postgres-compatible, enforce validation in application code for SQLite compatibility. Use `render_as_batch=True` in Alembic `env.py` (already configured).

---

## Production Deployment

**For PostgreSQL production:**
- Set `DATABASE_URL=postgresql://user:pass@host:port/dbname` in environment
- Run `alembic upgrade head` before starting application
- GIN indexes on `filters_json` will be created automatically (Postgres-only)

**For SQLite development:**
- Default `DATABASE_URL=sqlite:///eqms.db` works out of the box
- `render_as_batch=True` handles SQLite constraints gracefully
- Validation enforced in application code

---

## Verification Checklist

After migration and seed:

- [ ] All three tables exist: `distribution_log_entries`, `tracing_reports`, `approvals_eml`
- [ ] Foreign keys created: `rep_id`, `customer_id`, `generated_by_user_id`, `report_id`, `uploaded_by_user_id`
- [ ] Indexes created: all indexes from schema doc exist
- [ ] Permissions seeded: all REP permission keys exist in `permissions` table
- [ ] Admin role has all REP permissions
- [ ] Optional roles created (quality/ops/readonly) with correct permissions
- [ ] Migration downgrade works (tables dropped)
- [ ] Migration upgrade works again (tables recreated)

---

## References

- **Schema Source:** [docs/REP_SYSTEM_MINIMAL_SCHEMA.md](docs/REP_SYSTEM_MINIMAL_SCHEMA.md)
- **Existing Migration:** [migrations/versions/56a470f9ee55_initial_schema.py](migrations/versions/56a470f9ee55_initial_schema.py)
- **Seed Script:** [scripts/init_db.py](scripts/init_db.py)
- **Alembic Config:** [alembic.ini](alembic.ini)
