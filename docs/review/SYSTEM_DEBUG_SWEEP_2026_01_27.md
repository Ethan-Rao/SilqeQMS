# System Debug Sweep — Full Audit

**Date:** 2026-01-27  
**Purpose:** Comprehensive system audit documenting intended behavior, identified issues, and fixes for developer implementation.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Core Modules & Intended Behavior](#2-core-modules--intended-behavior)
3. [Identified Issues (Prioritized)](#3-identified-issues-prioritized)
4. [Developer Implementation Guide](#4-developer-implementation-guide)
5. [Verification Checklist](#5-verification-checklist)

---

## 1. System Architecture Overview

### Technology Stack
- **Framework:** Flask (Python 3.12)
- **Database:** PostgreSQL (production) / SQLite (development)
- **Migrations:** Alembic
- **Storage:** S3-compatible (DigitalOcean Spaces) / Local filesystem
- **Deployment:** DigitalOcean App Platform with Gunicorn

### Module Structure
```
app/eqms/
├── modules/
│   ├── rep_traceability/     # Distribution Log, Sales Orders, Dashboard, Tracing
│   ├── customer_profiles/    # Customer management
│   ├── shipstation_sync/     # ShipStation API integration
│   ├── equipment/            # Equipment management
│   ├── suppliers/            # Supplier management
│   ├── manufacturing/        # Production lot tracking
│   └── document_control/     # QMS document management
├── templates/admin/          # Jinja2 templates
├── static/                   # CSS
├── auth.py                   # Authentication
├── rbac.py                   # Role-Based Access Control
├── audit.py                  # Audit trail
├── storage.py                # Storage abstraction (S3/local)
└── admin.py                  # Admin routes, diagnostics, maintenance
```

### Canonical Data Pipeline
```
ShipStation API → Distribution Log (customer_id=NULL, sales_order_id=NULL)
                         ↓
Sales Order PDF Import → Sales Order (creates Customer from ship-to)
                         ↓
Distribution matched → sales_order_id set, customer_id = SO.customer_id
                         ↓
Sales Dashboard (ONLY aggregates WHERE sales_order_id IS NOT NULL)
```

---

## 2. Core Modules & Intended Behavior

### 2.1 Rep Traceability Module

#### Distribution Log (`/admin/distribution-log`)
| Feature | Route | Intended Behavior |
|---------|-------|-------------------|
| List | `GET /distribution-log` | Paginated list with filters (date, customer, SKU, lot) |
| Create | `POST /distribution-log/new` | Manual entry creates distribution |
| Edit | `GET/POST /distribution-log/<id>/edit` | Edit existing distribution |
| Delete | `POST /distribution-log/<id>/delete` | Soft delete with reason |
| Details Modal | `GET /distribution-log/entry-details/<id>` | JSON for in-page modal |
| CSV Import | `POST /distribution-log/import-csv` | Bulk import from CSV |
| PDF Upload | `POST /distribution-log/<id>/upload-pdf` | Upload SO PDF to match distribution |
| Label Upload | `POST /distribution-log/<id>/upload-label` | Upload shipping label |
| Export | `GET /distribution-log/export` | Export filtered results to CSV |

#### Sales Orders (`/admin/sales-orders`)
| Feature | Route | Intended Behavior |
|---------|-------|-------------------|
| List | `GET /sales-orders` | Paginated list with filters |
| Detail | `GET /sales-orders/<id>` | Show SO with lines, attachments, linked distributions |
| PDF Import | `POST /sales-orders/import-pdf-bulk` | Multi-page PDF split, parse, create SO + distributions |
| Unmatched PDFs | `GET /sales-orders/unmatched-pdfs` | List PDFs that couldn't be parsed |
| PDF Download | `GET /sales-orders/pdf/<id>/download` | Download attachment |
| Upload PDF | `POST /sales-orders/<id>/upload-pdf` | Attach additional PDF to existing SO |

#### Sales Dashboard (`/admin/sales-dashboard`)
| Feature | Route | Intended Behavior |
|---------|-------|-------------------|
| Dashboard | `GET /sales-dashboard` | Aggregated stats: orders, units, customers, SKU breakdown, lot tracking |
| Export | `GET /sales-dashboard/export` | Export to CSV |
| Order Details | `GET /sales-dashboard/order-details/<order_number>` | JSON details for modal |

**CRITICAL INVARIANT:** Dashboard MUST only aggregate from distributions WHERE `sales_order_id IS NOT NULL`.

#### Tracing Reports (`/admin/tracing`)
| Feature | Route | Intended Behavior |
|---------|-------|-------------------|
| List | `GET /tracing` | List generated reports |
| Generate | `POST /tracing/generate` | Generate tracing CSV for lot number |
| Detail | `GET /tracing/<id>` | View report details, download, upload approval |
| Download | `GET /tracing/<id>/download` | Download tracing CSV |
| Upload Approval | `POST /tracing/<id>/approvals/upload` | Upload .eml approval file |

### 2.2 Customer Profiles Module

| Feature | Route | Intended Behavior |
|---------|-------|-------------------|
| List | `GET /customers` | Paginated list with stats (order count, units) |
| Detail | `GET /customers/<id>` | Customer details, orders, distributions, notes |
| Create | `POST /customers/new` | Manual customer creation |
| Edit | `POST /customers/<id>/edit` | Update customer fields |
| Notes | `POST /notes/create` | Add note to customer |
| Merge | `POST /customers/merge` | Merge duplicate customers |

**CRITICAL INVARIANT:** Customer stats MUST only count distributions WHERE `sales_order_id IS NOT NULL`.

### 2.3 ShipStation Sync Module

| Feature | Route | Intended Behavior |
|---------|-------|-------------------|
| Index | `GET /shipstation` | Sync status, recent runs, skipped orders |
| Run Sync | `POST /shipstation/run` | Trigger sync with date range |
| Diagnostics | `GET /shipstation/diag` | Detailed diagnostics |

**CRITICAL INVARIANT:** ShipStation sync MUST NOT create customers. It creates distributions with `customer_id=NULL` and `sales_order_id=NULL`. Customer linking happens when a Sales Order is imported/matched.

### 2.4 Admin & Maintenance Module

| Feature | Route | Intended Behavior |
|---------|-------|-------------------|
| Diagnostics | `GET /admin/diagnostics` | DB connectivity, counts, last sync |
| Storage Diagnostics | `GET /admin/diagnostics/storage` | S3 config check (no secrets exposed) |
| List Duplicates | `GET /admin/maintenance/customers/duplicates` | JSON list of duplicate customers |
| List Zero-Orders | `GET /admin/maintenance/customers/zero-orders` | JSON list of customers with 0 SOs |
| Merge Customers | `POST /admin/maintenance/customers/merge` | Merge with confirmation token |
| Delete Zero-Orders | `POST /admin/maintenance/customers/delete-zero-orders` | Delete customers with no SOs |
| Reset All Data | `POST /admin/maintenance/reset-all-data` | Nuclear option: clear all data |
| Debug Permissions | `GET /admin/debug/permissions` | Show current user's permissions |

---

## 3. Identified Issues (Prioritized)

### P0 — Critical (Must Fix Immediately)

#### P0-1: ~~Unmatched PDFs Page 500 Error~~ ✅ FIXED
- **Location:** `templates/admin/sales_orders/unmatched_pdfs.html:72`
- **Problem:** Template used `url_for('rep_traceability.download_pdf_attachment')` but route is `sales_order_pdf_download`
- **Status:** Fixed in commit `65f79a7`

#### P0-2: ~~Customer Delete Foreign Key Violation~~ ✅ FIXED
- **Location:** `admin.py:maintenance_delete_zero_orders()`
- **Problem:** Didn't delete `CustomerRep` records before deleting customers
- **Status:** Fixed in commit `bb35cfd`

#### P0-3: ~~Missing admin.edit Permission~~ ✅ FIXED
- **Location:** `scripts/init_db.py`
- **Problem:** `admin.edit` permission never created, maintenance endpoints returned 403
- **Status:** Fixed in commit `3abe593`

#### P0-4: ~~CSRF Token Not Checked in JSON Body~~ ✅ FIXED
- **Location:** `security.py:validate_csrf()`
- **Problem:** CSRF validation only checked form fields and headers, not JSON body
- **Status:** Fixed in commit `a0e73b7`

### P1 — High Priority

#### P1-1: PDF Import Storage Errors Not Clearly Surfaced
- **Location:** `modules/rep_traceability/admin.py:1495` (`sales_orders_import_pdf_bulk`)
- **Current Behavior:** Storage errors tracked in `storage_errors` variable and shown in flash
- **Status:** ✅ Already implemented — shows warning if storage fails
- **Verification:** Upload PDF when S3 misconfigured → should see "WARNING: X PDFs failed to store"

#### P1-2: ShipStation Sync Error Handling
- **Location:** `modules/shipstation_sync/service.py`
- **Current Behavior:** Errors logged but sync continues
- **Status:** ✅ Acceptable — partial sync is better than total failure
- **Improvement:** Consider adding summary of skipped orders to UI

#### P1-3: CSV Import Does NOT Create Customers (Correct)
- **Location:** `modules/rep_traceability/admin.py:787-803`
- **Current Behavior:** CSV import only looks up existing customers, doesn't create new ones
- **Status:** ✅ Correct per canonical pipeline

### P2 — Medium Priority

#### P2-1: Notes Modal Entity Type Validation
- **Location:** `modules/rep_traceability/admin.py:1168` (`notes_create`)
- **Current Behavior:** Accepts any entity_type string
- **Improvement:** Validate entity_type is one of: "customer", "distribution", "sales_order"

#### P2-2: Audit Trail Pagination
- **Location:** `admin.py:audit_list()`
- **Current Behavior:** Limited to 200 events, no pagination
- **Improvement:** Add proper pagination for audit trail

#### P2-3: Customer Search Performance
- **Location:** `modules/customer_profiles/admin.py:52-54`
- **Current Behavior:** Uses ILIKE for search which is slow on large tables
- **Improvement:** Add database index on `facility_name`, `company_key`

### P3 — Low Priority / Polish

#### P3-1: Favicon Missing (404)
- **Location:** `/favicon.ico`
- **Status:** Returns 404
- **Fix:** Add favicon to static folder

#### P3-2: Hardcoded Dates
- **Location:** `modules/shipstation_sync/admin.py:75`
- **Current Behavior:** Default since_date is "2025-01-01"
- **Improvement:** Make dynamic based on current year

---

## 4. Developer Implementation Guide

### No Fixes Currently Required

All P0 issues have been resolved. The system is functional.

### Recommended Improvements (Optional)

#### Improvement 1: Add Favicon
```
File: app/eqms/static/favicon.ico
Action: Add a 32x32 or 64x64 .ico file
```

#### Improvement 2: Add Database Indexes
```sql
-- Add to a new migration
CREATE INDEX IF NOT EXISTS idx_customers_facility_name ON customers(facility_name);
CREATE INDEX IF NOT EXISTS idx_customers_company_key ON customers(company_key);
CREATE INDEX IF NOT EXISTS idx_distribution_log_ship_date ON distribution_log_entries(ship_date);
CREATE INDEX IF NOT EXISTS idx_distribution_log_sales_order_id ON distribution_log_entries(sales_order_id);
```

#### Improvement 3: Validate Notes Entity Type
```python
# In admin.py notes_create()
VALID_ENTITY_TYPES = {"customer", "distribution", "sales_order"}
if entity_type not in VALID_ENTITY_TYPES:
    return jsonify({"error": f"Invalid entity_type. Must be one of: {VALID_ENTITY_TYPES}"}), 400
```

---

## 5. Verification Checklist

### Core Functionality Tests

| Test | URL | Expected Result |
|------|-----|-----------------|
| Health Check | `GET /healthz` | `ok` (200) |
| Diagnostics | `GET /admin/diagnostics` | Page loads with DB stats |
| Storage Diagnostics | `GET /admin/diagnostics/storage` | JSON with `accessible: true` |
| Distribution Log | `GET /admin/distribution-log` | List loads (may be empty after reset) |
| Sales Orders | `GET /admin/sales-orders` | List loads |
| Sales Dashboard | `GET /admin/sales-dashboard` | Dashboard loads with stats |
| Customers | `GET /admin/customers` | List loads |
| Unmatched PDFs | `GET /admin/sales-orders/unmatched-pdfs` | Page loads (no 500 error) |
| ShipStation | `GET /admin/shipstation` | Sync status page loads |

### Data Pipeline Tests

| Test | Steps | Expected Result |
|------|-------|-----------------|
| ShipStation Sync | Run sync via `/admin/shipstation` | Distributions created, NO customers created |
| PDF Import | Upload SO PDF via `/admin/sales-orders/import-pdf` | SO + Customer created, distributions linked |
| Dashboard Accuracy | Compare dashboard totals to SQL | Only matched distributions counted |
| Customer Stats | Check customer detail page | Stats only from matched distributions |

### Maintenance Endpoint Tests

| Test | Steps | Expected Result |
|------|-------|-----------------|
| List Zero-Orders | `GET /admin/maintenance/customers/zero-orders` | JSON list |
| List Duplicates | `GET /admin/maintenance/customers/duplicates` | JSON list |
| Reset All Data | POST with confirm phrase | All data cleared |

### SQL Verification Queries

```sql
-- Unmatched distributions (should exist after ShipStation sync, before PDF import)
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NULL;

-- Matched distributions (should only exist after PDF import)
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NOT NULL;

-- Dashboard total should match this:
SELECT COUNT(DISTINCT order_number) FROM distribution_log_entries WHERE sales_order_id IS NOT NULL;

-- No duplicate customers by company_key
SELECT company_key, COUNT(*) FROM customers GROUP BY company_key HAVING COUNT(*) > 1;

-- No customers without sales orders (after cleanup)
SELECT COUNT(*) FROM customers c 
LEFT JOIN sales_orders so ON so.customer_id = c.id 
WHERE so.id IS NULL;
```

---

## 6. Current System State

### Environment Variables Required for Production

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Flask session encryption | (random string, min 32 chars) |
| `ENV` | Environment flag | `production` |
| `STORAGE_BACKEND` | Storage type | `s3` |
| `S3_ENDPOINT` | Spaces endpoint | `sfo3.digitaloceanspaces.com` |
| `S3_BUCKET` | Bucket name | `silq-eqms-files` |
| `S3_ACCESS_KEY_ID` | Spaces access key | `DO00...` |
| `S3_SECRET_ACCESS_KEY` | Spaces secret | (secret) |
| `S3_REGION` | Spaces region | `sfo3` |
| `ADMIN_EMAIL` | Initial admin email | `admin@example.com` |
| `ADMIN_PASSWORD` | Initial admin password | (strong password) |
| `SHIPSTATION_API_KEY` | ShipStation API key | (from ShipStation) |
| `SHIPSTATION_API_SECRET` | ShipStation API secret | (from ShipStation) |
| `SHIPSTATION_SINCE_DATE` | Sync start date | `2025-01-01` |

### Deployment Configuration

**Run Command:**
```bash
python scripts/start.py
```

**start.py does:**
1. Runs `scripts/release.py` (migrations + seed)
2. Starts Gunicorn on `$PORT` (default 8080)

**Health Check:**
- Path: `/healthz`
- Expected: `ok` (200)

---

## 7. Summary

### All Critical Issues Resolved ✅

| Issue | Commit | Status |
|-------|--------|--------|
| Unmatched PDFs 500 | `65f79a7` | ✅ Fixed |
| Customer Delete FK | `bb35cfd` | ✅ Fixed |
| Missing admin.edit | `3abe593` | ✅ Fixed |
| CSRF in JSON | `a0e73b7` | ✅ Fixed |
| Reset endpoint | `3a8bb2b` | ✅ Added |

### System Ready For

1. **Data Reset** — Use `/admin/maintenance/reset-all-data` to clear all data
2. **Fresh Start** — Run ShipStation sync, then import Sales Order PDFs
3. **Production Use** — All core workflows functional

---

**End of System Debug Sweep**
