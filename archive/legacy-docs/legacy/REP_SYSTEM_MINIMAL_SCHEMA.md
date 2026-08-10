# Rep System Minimal Database Schema

**Date:** 2025-01-XX  
**Purpose:** Database schema for essential Rep QMS functionality in SilqeQMS

---

## Overview

This document defines the minimal database schema for Distribution Log, Tracing Reports, and Approval Evidence (.eml uploads). All tables use PostgreSQL (compatible with new system's database).

**Key Principles:**
- Single source of truth: `distribution_log_entries` table
- Immutable artifacts: Tracing reports stored as versioned files (metadata only in DB)
- Audit trail: All changes logged via `audit_events` table (reuse existing)
- RBAC: Use existing `users`, `roles`, `permissions` tables (reuse existing)

---

## Core Tables

### 1. `distribution_log_entries`

**Purpose:** Single source of truth for all device distributions.

**Schema:**

```sql
CREATE TABLE distribution_log_entries (
    id SERIAL PRIMARY KEY,
    
    -- Required fields
    ship_date DATE NOT NULL,
    order_number TEXT NOT NULL,
    facility_name TEXT NOT NULL,
    rep_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    sku TEXT NOT NULL CHECK (sku IN ('211810SPT', '211610SPT', '211410SPT')),
    lot_number TEXT NOT NULL CHECK (lot_number ~ '^SLQ-\d{5}$'),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    source TEXT NOT NULL CHECK (source IN ('shipstation', 'manual', 'csv_import', 'pdf_import')),
    
    -- Optional fields
    customer_id INTEGER REFERENCES customers(id) ON DELETE SET NULL,
    address1 TEXT,
    address2 TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    country TEXT DEFAULT 'USA',
    contact_name TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    tracking_number TEXT,
    ss_shipment_id TEXT,  -- ShipStation shipment ID (unique if source='shipstation')
    
    -- File attachments (stored via storage.py, this is just metadata)
    evidence_file_storage_key TEXT,  -- Key for uploaded PDF/image evidence
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id),
    updated_by_user_id INTEGER REFERENCES users(id),
    
    -- Deduplication constraints
    UNIQUE(ss_shipment_id) WHERE ss_shipment_id IS NOT NULL,
    
    -- Indexes for filtering
    INDEX idx_distribution_log_ship_date (ship_date),
    INDEX idx_distribution_log_source (source),
    INDEX idx_distribution_log_rep_id (rep_id),
    INDEX idx_distribution_log_customer_id (customer_id),
    INDEX idx_distribution_log_sku (sku),
    INDEX idx_distribution_log_order_number (order_number)
);
```

**Fields:**
- `id`: Primary key (auto-increment)
- `ship_date`: Date devices were shipped (required, YYYY-MM-DD)
- `order_number`: Order identifier (ShipStation order ID, SO number, or generated)
- `facility_name`: Customer facility name (required)
- `rep_id`: FK to `users` table (rep assigned, nullable)
- `sku`: Device SKU (one of: 211810SPT, 211610SPT, 211410SPT)
- `lot_number`: Lot identifier (format: SLQ-#####, validated by CHECK constraint)
- `quantity`: Number of units distributed (positive integer)
- `source`: How entry was created ('shipstation', 'manual', 'csv_import', 'pdf_import')
- `customer_id`: FK to `customers` table (nullable, for future CRM integration)
- `address1`, `address2`, `city`, `state`, `zip`, `country`: Facility address (optional)
- `contact_name`, `contact_phone`, `contact_email`: Contact info (optional)
- `tracking_number`: Shipping tracking number (optional)
- `ss_shipment_id`: ShipStation shipment ID (unique if source='shipstation', nullable)
- `evidence_file_storage_key`: Storage key for uploaded PDF/image evidence (optional)
- `created_at`, `updated_at`: Timestamps (auto-set)
- `created_by_user_id`, `updated_by_user_id`: FK to `users` table (audit trail)

**Constraints:**
- `ss_shipment_id` must be unique if not NULL (prevents duplicate ShipStation imports)
- `sku` must be one of valid values (CHECK constraint)
- `lot_number` must match pattern `SLQ-\d{5}` (CHECK constraint)
- `quantity` must be positive (CHECK constraint)
- `source` must be one of valid values (CHECK constraint)

**Indexes:**
- `ship_date`: For date range filtering
- `source`: For filtering by ShipStation/manual
- `rep_id`: For filtering by rep
- `customer_id`: For filtering by customer
- `sku`: For filtering by SKU
- `order_number`: For searching by order number

---

### 2. `tracing_reports`

**Purpose:** Metadata for generated tracing reports (reports themselves are immutable files in storage).

**Schema:**

```sql
CREATE TABLE tracing_reports (
    id SERIAL PRIMARY KEY,
    
    -- Report generation metadata
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    generated_by_user_id INTEGER REFERENCES users(id),
    
    -- Filters used to generate report
    filters_json JSONB NOT NULL,  -- {rep_id, source, month, sku, customer_id}
    
    -- Report file metadata
    report_storage_key TEXT NOT NULL,  -- Key in storage.py (versioned path)
    report_format TEXT NOT NULL DEFAULT 'csv' CHECK (report_format = 'csv'),
    
    -- Report status
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'final')),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for filtering
    INDEX idx_tracing_reports_generated_at (generated_at),
    INDEX idx_tracing_reports_status (status),
    INDEX idx_tracing_reports_filters (filters_json)  -- GIN index for JSONB queries
);
```

**Fields:**
- `id`: Primary key (auto-increment)
- `generated_at`: When report was generated (timestamp)
- `generated_by_user_id`: FK to `users` table (who generated the report)
- `filters_json`: JSON object with filters used to generate report:
  ```json
  {
    "rep_id": 123,  // optional, FK to users
    "source": "shipstation",  // optional: "shipstation", "manual", or "all"
    "month": "2025-01",  // required, YYYY-MM format
    "sku": "211810SPT",  // optional, filter by SKU
    "customer_id": 456  // optional, FK to customers
  }
  ```
- `report_storage_key`: Storage key for generated CSV file (versioned path, e.g., `tracing_reports/2025-01/filters_hash_2025-01-15T10-30-00.csv`)
- `report_format`: Always 'csv' (CHECK constraint ensures no PDF/HTML)
- `status`: Report status ('draft' or 'final')
- `created_at`, `updated_at`: Timestamps (auto-set)

**Constraints:**
- `report_format` must be 'csv' (no PDF/HTML reports)
- `status` must be 'draft' or 'final'

**Indexes:**
- `generated_at`: For sorting reports by date
- `status`: For filtering by status
- `filters_json`: GIN index for efficient JSONB queries (e.g., find reports by month)

---

### 3. `approvals_eml`

**Purpose:** Metadata for uploaded .eml approval files (files themselves stored via storage.py).

**Schema:**

```sql
CREATE TABLE approvals_eml (
    id SERIAL PRIMARY KEY,
    
    -- Link to tracing report
    report_id INTEGER NOT NULL REFERENCES tracing_reports(id) ON DELETE CASCADE,
    
    -- File metadata
    storage_key TEXT NOT NULL,  -- Key in storage.py (e.g., approvals/123/timestamp_subject.eml)
    original_filename TEXT NOT NULL,  -- Original filename from upload
    
    -- Extracted email metadata (from .eml file headers)
    subject TEXT,
    from_email TEXT,
    to_email TEXT,
    email_date TIMESTAMP WITH TIME ZONE,  -- Parsed from email header "Date:"
    
    -- Upload metadata
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    uploaded_by_user_id INTEGER REFERENCES users(id),
    notes TEXT,  -- Admin notes about approval
    
    -- Indexes for filtering
    INDEX idx_approvals_eml_report_id (report_id),
    INDEX idx_approvals_eml_uploaded_at (uploaded_at)
);
```

**Fields:**
- `id`: Primary key (auto-increment)
- `report_id`: FK to `tracing_reports` table (which report this approval is for)
- `storage_key`: Storage key for .eml file (versioned path, e.g., `approvals/123/2025-01-15T10-30-00_Approval.eml`)
- `original_filename`: Original filename from upload (for display)
- `subject`: Extracted from email header "Subject:" (optional, may be NULL if parsing fails)
- `from_email`: Extracted from email header "From:" (optional)
- `to_email`: Extracted from email header "To:" (optional)
- `email_date`: Parsed from email header "Date:" (optional, may be NULL if parsing fails)
- `uploaded_at`: When .eml file was uploaded (server timestamp)
- `uploaded_by_user_id`: FK to `users` table (who uploaded the approval)
- `notes`: Admin notes about approval (optional)

**Constraints:**
- `report_id` must reference existing `tracing_reports` record (CASCADE delete if report deleted)

**Indexes:**
- `report_id`: For finding all approvals for a report
- `uploaded_at`: For sorting approvals by date

---

## Link Tables

### None Required

All relationships are via foreign keys in the main tables:
- `distribution_log_entries.rep_id` → `users.id`
- `distribution_log_entries.customer_id` → `customers.id` (optional, for future CRM)
- `tracing_reports.generated_by_user_id` → `users.id`
- `approvals_eml.report_id` → `tracing_reports.id`
- `approvals_eml.uploaded_by_user_id` → `users.id`

---

## Audit Trail (Reuse Existing)

**Use existing `audit_events` table** from `eqms_starter` foundation:

```sql
-- Already exists in new system
CREATE TABLE audit_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,  -- 'create', 'update', 'delete'
    entity_type TEXT NOT NULL,  -- 'distribution_log_entry', 'tracing_report', 'approval_eml'
    entity_id INTEGER NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changes_json JSONB  -- Before/after values for updates
);
```

**Required audit events:**
- `distribution_log_entry`: 'create', 'update', 'delete' (log all changes)
- `tracing_report`: 'create' (report generation), 'delete' (report deletion)
- `approval_eml`: 'create' (upload), 'delete' (deletion)

---

## Revisioning Rules

### Distribution Log Entries

**Mutable:** Entries can be edited (rep reassignment, quantity/lot corrections).

**Revisioning:** Track changes via `audit_events` table:
- Every update logs before/after values in `changes_json`
- Original values preserved in audit log (never overwrite)

**Example audit log:**
```json
{
  "action": "update",
  "entity_type": "distribution_log_entry",
  "entity_id": 123,
  "changes_json": {
    "before": {"quantity": 10, "lot_number": "SLQ-12345"},
    "after": {"quantity": 15, "lot_number": "SLQ-12346"},
    "fields_changed": ["quantity", "lot_number"]
  }
}
```

---

### Tracing Reports

**Immutable:** Reports are immutable once generated (never overwrite).

**Revisioning:** Generate new report with new timestamp:
- Each generation creates new `tracing_reports` record with new `report_storage_key`
- Old reports kept for audit (cleanup policy: keep last 12 months, archive older)
- Report files stored as: `tracing_reports/{month}/{filters_hash}_{generated_at_iso}.csv`

**Example storage keys:**
- First generation: `tracing_reports/2025-01/abc123def_2025-01-15T10-30-00.csv`
- Regeneration (same filters): `tracing_reports/2025-01/abc123def_2025-01-20T14-45-00.csv` (new file, new timestamp)

---

### Approval .eml Files

**Immutable:** .eml files are immutable once uploaded (never overwrite).

**Revisioning:** Upload new .eml file to replace old:
- Old .eml file kept in storage (not deleted)
- New upload creates new `approvals_eml` record
- UI shows most recent approval for a report (or all approvals if needed)

**Example storage keys:**
- First upload: `approvals/123/2025-01-15T10-30-00_Approval.eml`
- Second upload: `approvals/123/2025-01-20T14-45-00_Approval_v2.eml` (new file, new timestamp)

---

## Migration from Old System

### Export Script (Old System)

```python
# Export from old devices_distributed + device_distribution_records tables
# Map to new distribution_log_entries schema

OLD_TABLES = {
    "devices_distributed": {
        "id": "dist_id",
        "order_number": "order_number",
        "ship_date": "ship_date",
        "rep_id": "rep_id",
        "source": "source",
        "ss_shipment_id": "ss_shipment_id",
        "tracking_number": "tracking_number",
    },
    "device_distribution_records": {
        "dist_id": "dist_id",
        "fields_json": "fields_json",  # Parse JSON to extract SKU, Lot, Quantity, Facility, etc.
    }
}

# Normalize fields_json to new schema
# Group by dist_id (multiple SKU/Lot combinations per distribution = multiple rows)
```

### Import Script (New System)

```python
# Import into new distribution_log_entries table
# Validate required fields (SKU, lot format, quantity)
# Handle duplicates (warn on duplicate ss_shipment_id)
# Set created_by_user_id = system_migration_user_id
```

---

## Sample Queries

### Distribution Log Queries

**Find all distributions in date range:**
```sql
SELECT * FROM distribution_log_entries
WHERE ship_date >= '2025-01-01' AND ship_date < '2025-02-01'
ORDER BY ship_date DESC;
```

**Find all ShipStation distributions for a rep:**
```sql
SELECT * FROM distribution_log_entries
WHERE source = 'shipstation' AND rep_id = 123
ORDER BY ship_date DESC;
```

**Find all distributions for a customer:**
```sql
SELECT * FROM distribution_log_entries
WHERE customer_id = 456
ORDER BY ship_date DESC;
```

---

### Tracing Report Queries

**Find all reports for a month:**
```sql
SELECT * FROM tracing_reports
WHERE filters_json->>'month' = '2025-01'
ORDER BY generated_at DESC;
```

**Find all reports for a rep:**
```sql
SELECT * FROM tracing_reports
WHERE filters_json->>'rep_id' = '123'
ORDER BY generated_at DESC;
```

**Find all reports with ShipStation filter:**
```sql
SELECT * FROM tracing_reports
WHERE filters_json->>'source' = 'shipstation'
ORDER BY generated_at DESC;
```

---

### Approval Queries

**Find all approvals for a report:**
```sql
SELECT * FROM approvals_eml
WHERE report_id = 789
ORDER BY uploaded_at DESC;
```

**Find most recent approval for a report:**
```sql
SELECT * FROM approvals_eml
WHERE report_id = 789
ORDER BY uploaded_at DESC
LIMIT 1;
```

---

**End of Minimal Schema**
