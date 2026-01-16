# Minimal Data Model Extensions

**Date:** 2026-01-15  
**Purpose:** Schema additions for Customer Profiles, dashboard aggregates, and distribution-customer linking

---

## Overview

This document proposes minimal schema additions to support:
1. **Customer Profiles** (facility/customer master data)
2. **Customer-Distribution Linking** (FK from `distribution_log_entries` to `customers`)
3. **Dashboard Aggregates** (computed on-demand, no separate table initially)

**Key Principle:** Keep it lean - no materialized views or cached summaries initially. Add caching later if performance becomes an issue.

---

## Table 1: `customers`

**Purpose:** Facility/customer master data for CRM and distribution linking

**Source:** Legacy Rep QMS `customers` table (lines 1023-1038 in `Proto1.py`)

**Schema (Postgres-compatible, works on SQLite via `render_as_batch`):**

```sql
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    
    -- Canonical key (normalized facility name for deduplication)
    company_key TEXT NOT NULL UNIQUE,
    
    -- Required fields
    facility_name TEXT NOT NULL,
    
    -- Optional address fields
    address1 TEXT,
    address2 TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    
    -- Optional contact fields
    contact_name TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    
    -- Rep assignment
    primary_rep_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_customers_company_key (company_key),
    INDEX idx_customers_facility_name (facility_name),
    INDEX idx_customers_state (state),
    INDEX idx_customers_primary_rep_id (primary_rep_id)
);
```

**Fields:**
- `id`: Primary key (auto-increment)
- `company_key`: Canonical key (normalized facility name, uppercase, special chars removed)
  - Used for deduplication (e.g., "Hospital A" → "HOSPITALA")
  - Unique constraint ensures no duplicate customers
- `facility_name`: Customer facility name (required)
- `address1`, `address2`, `city`, `state`, `zip`: Facility address (optional)
- `contact_name`, `contact_phone`, `contact_email`: Contact info (optional)
- `primary_rep_id`: FK to `users` table (primary rep assigned, nullable)
- `created_at`, `updated_at`: Timestamps (auto-set)

**Constraints:**
- `company_key` must be unique (prevents duplicate customers)
- `facility_name` must be non-empty (required)

**Indexes:**
- `company_key`: For finding existing customers (deduplication)
- `facility_name`: For search/filtering
- `state`: For state filtering
- `primary_rep_id`: For rep filtering

**Migration Command:**
```bash
alembic revision -m "add customers table"
```

---

## Table 2: `customer_notes` (Optional)

**Purpose:** CRM-style notes/activity log for customers

**Source:** Legacy Rep QMS `customer_notes` table (lines 1055-1065 in `Proto1.py`)

**Schema:**

```sql
CREATE TABLE customer_notes (
    id SERIAL PRIMARY KEY,
    
    -- Link to customer
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Note content
    note_text TEXT NOT NULL,
    note_date DATE DEFAULT CURRENT_DATE,
    author TEXT,  -- Optional author name (defaults to current user email)
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    INDEX idx_customer_notes_customer_id (customer_id, created_at DESC)
);
```

**Fields:**
- `id`: Primary key (auto-increment)
- `customer_id`: FK to `customers` table (CASCADE delete if customer deleted)
- `note_text`: Note content (required)
- `note_date`: Date of note (defaults to today, optional)
- `author`: Author name (optional, defaults to current user email from audit)
- `created_at`, `updated_at`: Timestamps (auto-set)

**Constraints:**
- `customer_id` must reference existing `customers` record
- `note_text` must be non-empty (required)

**Indexes:**
- `customer_id, created_at DESC`: For finding all notes for a customer (sorted by date)

**Priority:** P1 (optional CRM feature, can be added later if needed)

**Migration Command:**
```bash
alembic revision -m "add customer_notes table"
```

---

## Table 3: `customer_rep_assignments` (Optional)

**Purpose:** Many-to-many relationship between customers and reps (for secondary rep assignments)

**Source:** Legacy Rep QMS `customer_rep_assignments` table (lines 1043-1052 in `Proto1.py`)

**Schema:**

```sql
CREATE TABLE customer_rep_assignments (
    id SERIAL PRIMARY KEY,
    
    -- Links
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    rep_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Primary rep flag
    is_primary BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    UNIQUE(customer_id, rep_id),
    
    -- Indexes
    INDEX idx_customer_rep_assignments_customer_id (customer_id),
    INDEX idx_customer_rep_assignments_rep_id (rep_id)
);
```

**Fields:**
- `id`: Primary key (auto-increment)
- `customer_id`: FK to `customers` table (CASCADE delete)
- `rep_id`: FK to `users` table (CASCADE delete)
- `is_primary`: Boolean flag (defaults to FALSE, syncs with `customers.primary_rep_id`)
- `created_at`: Timestamp (auto-set)

**Constraints:**
- Unique constraint on `(customer_id, rep_id)` prevents duplicate assignments

**Indexes:**
- `customer_id`: For finding all reps for a customer
- `rep_id`: For finding all customers for a rep

**Priority:** P1 (optional, can use `customers.primary_rep_id` alone initially)

**Migration Command:**
```bash
alembic revision -m "add customer_rep_assignments table"
```

**Note:** If implementing P0 only (minimal), can skip this table and use `customers.primary_rep_id` alone. Add `customer_rep_assignments` table later if secondary rep assignments are needed.

---

## Migration: Add customer_id FK to distribution_log_entries

**Purpose:** Link distribution entries to customer master data

**Current State:**
- `distribution_log_entries` has `customer_name` text field (free-text)
- Schema doc references `customer_id` FK but not implemented yet

**Migration:**

```sql
-- Add customer_id column (nullable for backward compatibility)
ALTER TABLE distribution_log_entries
ADD COLUMN customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL;

-- Add index for filtering
CREATE INDEX idx_distribution_log_customer_id ON distribution_log_entries(customer_id);

-- Optional: Migrate existing customer_name values to customers table
-- (Can be done manually later or via script)
```

**Migration Command:**
```bash
alembic revision -m "add customer_id fk to distribution_log_entries"
```

**Backward Compatibility:**
- Keep `customer_name` text field for now (deprecated, can be removed later)
- `customer_id` is nullable, so existing entries remain valid
- Forms can populate `customer_name` from `customers.facility_name` for display

---

## Dashboard Aggregates: No Separate Table (Initially)

**Decision:** Compute aggregations on-demand from `distribution_log_entries` (no materialized views or cached summaries initially)

**Rationale:**
- Keeps schema lean
- Data is always up-to-date (no cache invalidation)
- Query performance should be acceptable for small-to-medium datasets
- Can add caching/materialized views later if needed (P2)

**If Performance Becomes Issue (P2):**
- Add `dashboard_aggregates` table with columns:
  - `period` (e.g., "2026-01", "2026-Q1")
  - `total_orders`, `total_units`, `total_customers`, `first_time_customers`, `repeat_customers`
  - `sku_breakdown` (JSONB)
  - `computed_at` (timestamp)
- Update via background job or on-demand with TTL

**For Now (P1):**
- Compute aggregations on-demand in `sales_dashboard()` route
- Query `distribution_log_entries` directly
- Use SQL GROUP BY for aggregations

---

## Complete Migration Upgrade Function

**File:** `migrations/versions/<revision>_add_customers_table.py`

```python
"""add customers table

Revision ID: <revision>
Revises: <previous_revision>
Create Date: <timestamp>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '<revision>'
down_revision: Union[str, Sequence[str], None] = '<previous_revision>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("company_key", sa.Text(), nullable=False),
        sa.Column("facility_name", sa.Text(), nullable=False),
        sa.Column("address1", sa.Text(), nullable=True),
        sa.Column("address2", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("zip", sa.Text(), nullable=True),
        sa.Column("contact_name", sa.Text(), nullable=True),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.Text(), nullable=True),
        sa.Column("primary_rep_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["primary_rep_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("company_key", name="uq_customers_company_key"),
    )
    
    # Create indexes
    op.create_index("idx_customers_company_key", "customers", ["company_key"])
    op.create_index("idx_customers_facility_name", "customers", ["facility_name"])
    op.create_index("idx_customers_state", "customers", ["state"])
    op.create_index("idx_customers_primary_rep_id", "customers", ["primary_rep_id"])
    
    # Optional: customer_notes table (P1)
    op.create_table(
        "customer_notes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("note_text", sa.Text(), nullable=False),
        sa.Column("note_date", sa.Date(), nullable=True, server_default=sa.func.current_date()),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )
    
    op.create_index("idx_customer_notes_customer_id", "customer_notes", ["customer_id", "created_at"], postgresql_ops={"created_at": "DESC"})
    
    # Optional: customer_rep_assignments table (P1)
    op.create_table(
        "customer_rep_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("rep_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rep_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("customer_id", "rep_id", name="uq_customer_rep_assignments"),
    )
    
    op.create_index("idx_customer_rep_assignments_customer_id", "customer_rep_assignments", ["customer_id"])
    op.create_index("idx_customer_rep_assignments_rep_id", "customer_rep_assignments", ["rep_id"])


def downgrade() -> None:
    op.drop_table("customer_rep_assignments")
    op.drop_table("customer_notes")
    op.drop_table("customers")
```

---

## Migration: Add customer_id FK to distribution_log_entries

**File:** `migrations/versions/<revision>_add_customer_id_fk_to_distribution_log.py`

```python
"""add customer_id fk to distribution_log_entries

Revision ID: <revision>
Revises: <previous_revision>  # Should be the customers table migration
Create Date: <timestamp>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '<revision>'
down_revision: Union[str, Sequence[str], None] = '<customers_table_revision>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add customer_id column (nullable for backward compatibility)
    op.add_column("distribution_log_entries", sa.Column("customer_id", sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        "fk_distribution_log_entries_customer_id",
        "distribution_log_entries",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    
    # Add index for filtering
    op.create_index("idx_distribution_log_customer_id", "distribution_log_entries", ["customer_id"])


def downgrade() -> None:
    op.drop_index("idx_distribution_log_customer_id", "distribution_log_entries")
    op.drop_constraint("fk_distribution_log_entries_customer_id", "distribution_log_entries", type_="foreignkey")
    op.drop_column("distribution_log_entries", "customer_id")
```

---

## SQLAlchemy Models

**File:** `app/eqms/modules/customer_profiles/models.py`

```python
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.eqms.models import Base, User


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        # Indexes
        Index("idx_customers_company_key", "company_key"),
        Index("idx_customers_facility_name", "facility_name"),
        Index("idx_customers_state", "state"),
        Index("idx_customers_primary_rep_id", "primary_rep_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    company_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    facility_name: Mapped[str] = mapped_column(Text, nullable=False)
    
    address1: Mapped[str | None] = mapped_column(Text, nullable=True)
    address2: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(Text, nullable=True)
    zip: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    contact_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    primary_rep_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    
    # Relationships
    primary_rep: Mapped[User | None] = relationship("User", foreign_keys=[primary_rep_id], lazy="selectin")
    notes: Mapped[list["CustomerNote"]] = relationship("CustomerNote", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")
    rep_assignments: Mapped[list["CustomerRepAssignment"]] = relationship("CustomerRepAssignment", back_populates="customer", cascade="all, delete-orphan", lazy="selectin")


class CustomerNote(Base):
    __tablename__ = "customer_notes"
    __table_args__ = (
        Index("idx_customer_notes_customer_id", "customer_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    note_date: Mapped[date | None] = mapped_column(Date, nullable=True, default=date.today)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    
    # Relationships
    customer: Mapped[Customer] = relationship("Customer", back_populates="notes", lazy="selectin")


class CustomerRepAssignment(Base):
    __tablename__ = "customer_rep_assignments"
    __table_args__ = (
        Index("idx_customer_rep_assignments_customer_id", "customer_id"),
        Index("idx_customer_rep_assignments_rep_id", "rep_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    rep_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    
    # Relationships
    customer: Mapped[Customer] = relationship("Customer", back_populates="rep_assignments", lazy="selectin")
    rep: Mapped[User] = relationship("User", foreign_keys=[rep_id], lazy="selectin")
```

---

## Update DistributionLogEntry Model

**File:** `app/eqms/modules/rep_traceability/models.py`

Add to `DistributionLogEntry` class:

```python
# Add customer_id FK (after existing fields)
customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)

# Add relationship (optional)
customer: Mapped["Customer | None"] = relationship("Customer", foreign_keys=[customer_id], lazy="selectin")
```

**Note:** Import `Customer` at top of file (or use forward reference string `"Customer"`).

---

## Migration from Existing Data

**Option 1: Manual Migration (Recommended for P0)**

1. Create `customers` table
2. Manually create customer records from unique `customer_name` values in `distribution_log_entries`
3. Update `distribution_log_entries.customer_id` FK via SQL:

```sql
-- Example (adjust based on actual data)
UPDATE distribution_log_entries dle
SET customer_id = (
    SELECT c.id
    FROM customers c
    WHERE c.company_key = UPPER(REPLACE(REPLACE(dle.customer_name, ' ', ''), '-', ''))
    LIMIT 1
)
WHERE dle.customer_name IS NOT NULL;
```

**Option 2: Automatic Migration Script**

Create script `scripts/migrate_customers.py`:
- Query all unique `customer_name` values from `distribution_log_entries`
- Create `customers` records via `find_or_create_customer()`
- Update `distribution_log_entries.customer_id` FK

**Priority:** Can be done after schema migration, before production use.

---

## Verification Checklist

After migrations:

- [ ] `customers` table exists with correct columns and constraints
- [ ] `customer_notes` table exists (if P1 implemented)
- [ ] `customer_rep_assignments` table exists (if P1 implemented)
- [ ] `distribution_log_entries.customer_id` column exists
- [ ] FK constraint exists: `distribution_log_entries.customer_id` → `customers.id`
- [ ] Indexes created: all indexes from schema
- [ ] Models import without errors
- [ ] Alembic autogenerate detects no differences

---

## References

- **Schema Source:** [docs/REP_SYSTEM_MINIMAL_SCHEMA.md](docs/REP_SYSTEM_MINIMAL_SCHEMA.md)
- **Legacy Schema:** `C:\Users\Ethan\OneDrive\Desktop\UI\RepsQMS\Proto1.py` lines 1023-1086
- **Migration Plan:** [docs/review/03_LEAN_MIGRATION_PLAN.md](docs/review/03_LEAN_MIGRATION_PLAN.md)
