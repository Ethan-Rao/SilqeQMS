# Rep System UI Map / Sitemap

**Date:** 2025-01-XX  
**Purpose:** Navigation structure and minimal screens for Rep QMS in SilqeQMS

---

## Overview

This document defines the UI structure for the new SilqeQMS system. All users access the same site (no rep-specific pages). Access is controlled via RBAC (Admin, Quality, Ops, ReadOnly roles).

**Key Principles:**
- Single-site experience (all users access `/admin/...` routes)
- Minimal screens only (no dashboards, no analytics)
- Clean admin usability (boring, functional UI)
- Reuse existing `eqms_starter` template structure

---

## Navigation Structure

### Top-Level Navigation

**All screens under `/admin/...`** (protected by RBAC):

```
/admin
├── /distribution-log          (Distribution Log: browse, upload, edit, export)
├── /tracing                   (Tracing Reports: generate, list, view/download)
└── (existing admin routes)    (users, roles, audit log, etc.)
```

---

## Minimal Screens

### 1. Distribution Log (`/admin/distribution-log`)

**Purpose:** Browse, create, edit, and export device distributions.

**Routes:**
- `GET /admin/distribution-log` - List all distributions (with filters)
- `POST /admin/distribution-log/manual-entry` - Create manual entry
- `GET /admin/distribution-log/<id>/edit` - Edit form
- `POST /admin/distribution-log/<id>/edit` - Update entry
- `POST /admin/distribution-log/import-csv` - Upload CSV file
- `POST /admin/distribution-log/import-pdf` - Upload PDF file
- `GET /admin/distribution-log/export` - Download CSV (filtered view)

**UI Components:**

#### Screen 1.1: Distribution Log List (`GET /admin/distribution-log`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Distribution Log                                    [Export] │
├─────────────────────────────────────────────────────────────┤
│ Filters:                                                     │
│ Date From: [2025-01-01] Date To: [2025-01-31]              │
│ Source: [All ▼] Rep: [All ▼] Customer: [All ▼]            │
│ SKU: [All ▼]                                                │
│ [Apply Filters] [Clear]                                     │
├─────────────────────────────────────────────────────────────┤
│ [Manual Entry] [Import CSV] [Import PDF]                    │
├─────────────────────────────────────────────────────────────┤
│ Ship Date │ Order # │ Facility │ Rep │ SKU │ Lot │ Qty │... │
├─────────────────────────────────────────────────────────────┤
│ 2025-01-15│ 12345   │ Hospital A│John│211810│SLQ-1│10  │[Edit]│
│ 2025-01-14│ 12344   │ Hospital B│Jane│211610│SLQ-2│5   │[Edit]│
│ ...                                                          │
└─────────────────────────────────────────────────────────────┘
```

**Filters:**
- Date range (from/to)
- Source (All, ShipStation, Manual, CSV Import, PDF Import)
- Rep (dropdown of active users with rep role)
- Customer (dropdown of customers)
- SKU (All, 211810SPT, 211610SPT, 211410SPT)

**Actions:**
- Click row → Expand details (ship date, facility, SKU/lot/qty, tracking, evidence file)
- Click [Edit] → Edit form modal
- Click [Export] → Download CSV of filtered results

**Permissions:**
- View: All authenticated users
- Create/Edit/Delete: Admin, Quality, Ops roles
- Import: Admin, Ops roles

---

#### Screen 1.2: Manual Entry Form (`POST /admin/distribution-log/manual-entry`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Manual Distribution Entry                                    │
├─────────────────────────────────────────────────────────────┤
│ Ship Date *:      [2025-01-15]                               │
│ Order Number:     [12345] (leave blank to auto-generate)    │
│ Facility Name *:  [Hospital A]                               │
│ Rep:              [John Doe ▼]                               │
│ Source *:         [Manual ▼]                                 │
│                                                                │
│ SKU *:            [211810SPT ▼]                              │
│ Lot Number *:     [SLQ-12345] (format: SLQ-#####)           │
│ Quantity *:       [10]                                       │
│                                                                │
│ Address:          [123 Main St]                              │
│ City:             [Springfield]                              │
│ State:            [IL]                                       │
│ Zip:              [62701]                                    │
│                                                                │
│ Contact Name:     [Dr. Smith]                                │
│ Contact Phone:    [555-1234]                                 │
│ Contact Email:    [dr@hospital.com]                          │
│                                                                │
│ Tracking Number:  [1Z999AA10123456784]                       │
│                                                                │
│ Evidence File:    [Choose File] (PDF/image)                  │
│                                                                │
│ [Cancel] [Save Distribution]                                 │
└─────────────────────────────────────────────────────────────┘
```

**Validation:**
- Ship Date: Required, valid date (not future)
- Facility Name: Required, non-empty string
- SKU: Required, one of valid values
- Lot Number: Required, format `SLQ-\d{5}`
- Quantity: Required, positive integer

**Permissions:**
- Create: Admin, Quality, Ops roles

---

#### Screen 1.3: Import CSV (`POST /admin/distribution-log/import-csv`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Import Distribution Log from CSV                             │
├─────────────────────────────────────────────────────────────┤
│ Upload CSV file: [Choose File]                               │
│                                                                │
│ Expected columns:                                             │
│ - Ship Date, Order Number, Facility Name, SKU, Lot, Quantity│
│                                                                │
│ [Cancel] [Import CSV]                                        │
└─────────────────────────────────────────────────────────────┘
```

**After upload:**
- Show import results (success count, errors)
- List validation errors (invalid SKU, lot format, etc.)
- List duplicates (warn if order_number + ship_date + facility_name already exists)

**Permissions:**
- Import: Admin, Ops roles

---

#### Screen 1.4: Import PDF (`POST /admin/distribution-log/import-pdf`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Import Distribution Log from PDF                             │
├─────────────────────────────────────────────────────────────┤
│ Upload PDF file: [Choose File]                               │
│                                                                │
│ Supported formats:                                            │
│ - Master Sales Order PDF (extracts order number, facility)   │
│ - Shipping Label PDF (extracts tracking, facility)           │
│                                                                │
│ [Cancel] [Import PDF]                                        │
└─────────────────────────────────────────────────────────────┘
```

**After upload:**
- Show import results (pages processed, entries created)
- List extraction errors (order number not found, etc.)
- List duplicates (warn if order_number already exists)

**Permissions:**
- Import: Admin, Ops roles

---

### 2. Tracing Reports (`/admin/tracing`)

**Purpose:** Generate, list, and download tracing reports from Distribution Log.

**Routes:**
- `GET /admin/tracing` - List all generated reports
- `POST /admin/tracing/generate` - Generate new report (with filters)
- `GET /admin/tracing/<id>` - View report detail (with download link, approval upload)
- `GET /admin/tracing/<id>/download` - Download CSV file

**UI Components:**

#### Screen 2.1: Tracing Reports List (`GET /admin/tracing`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Tracing Reports                                   [Generate] │
├─────────────────────────────────────────────────────────────┤
│ Generated At │ Filters │ Status │ Actions                   │
├─────────────────────────────────────────────────────────────┤
│ 2025-01-15   │ Jan 2025│ Draft  │ [View] [Download]         │
│              │ All Reps│        │                            │
├─────────────────────────────────────────────────────────────┤
│ 2025-01-10   │ Jan 2025│ Final  │ [View] [Download]         │
│              │ John Doe│        │                            │
└─────────────────────────────────────────────────────────────┘
```

**Actions:**
- Click [Generate] → Generate form modal
- Click [View] → Report detail page
- Click [Download] → Download CSV file

**Permissions:**
- View: All authenticated users
- Generate: Admin, Quality, Ops roles
- Download: All authenticated users

---

#### Screen 2.2: Generate Report Form (`POST /admin/tracing/generate`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Generate Tracing Report                                      │
├─────────────────────────────────────────────────────────────┤
│ Month *:        [2025-01 ▼] (YYYY-MM format)                │
│ Rep:            [All Reps ▼]                                 │
│ Source:         [All ▼] (All, ShipStation, Manual)          │
│ SKU:            [All ▼] (All, 211810SPT, 211610SPT, ...)    │
│ Customer:       [All ▼]                                      │
│                                                                │
│ [Cancel] [Generate Report]                                   │
└─────────────────────────────────────────────────────────────┘
```

**After generation:**
- Redirect to report detail page
- Show success message: "Report generated successfully"

**Permissions:**
- Generate: Admin, Quality, Ops roles

---

#### Screen 2.3: Report Detail (`GET /admin/tracing/<id>`)

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Tracing Report #123                                          │
├─────────────────────────────────────────────────────────────┤
│ Generated: 2025-01-15 10:30 AM by John Doe                  │
│ Filters: January 2025, All Reps, All Sources                │
│ Status: Draft                                                │
│                                                                │
│ [Download CSV]                                               │
├─────────────────────────────────────────────────────────────┤
│ Approval Evidence                                            │
├─────────────────────────────────────────────────────────────┤
│ Upload .eml file: [Choose File]                              │
│                                                                │
│ Uploaded Approvals:                                          │
│ - 2025-01-16: Approval_Tracing_Report_2025-01.eml [Download]│
│ - 2025-01-15: approval_v1.eml [Download]                    │
│                                                                │
│ [Upload Approval]                                            │
└─────────────────────────────────────────────────────────────┘
```

**Actions:**
- Click [Download CSV] → Download CSV file
- Upload .eml file → Store approval evidence
- Click [Download] on approval → Download .eml file

**Permissions:**
- View: All authenticated users
- Upload Approval: Admin, Quality, Ops roles
- Download: All authenticated users

---

## Access Control (RBAC)

### Required Roles

**Minimal roles (reuse existing `eqms_starter` roles):**
- `Admin`: Full access (create/edit/delete distributions, generate reports, upload approvals)
- `Quality`: Full access (same as Admin, for compliance audits)
- `Ops`: Limited access (create/edit distributions, generate reports, upload approvals; no user management)
- `ReadOnly`: View-only access (browse distributions, view/download reports)

### Required Permissions

**Permission keys:**
- `distribution_log.view` - View distribution log list
- `distribution_log.create` - Create manual entry, import CSV/PDF
- `distribution_log.edit` - Edit distribution entries
- `distribution_log.delete` - Delete distribution entries
- `distribution_log.export` - Export CSV
- `tracing_reports.view` - View tracing reports list
- `tracing_reports.generate` - Generate new reports
- `tracing_reports.download` - Download CSV files
- `approvals.view` - View approval evidence
- `approvals.upload` - Upload .eml files

**Permission → Role Mapping:**
- `Admin`: All permissions
- `Quality`: All permissions (same as Admin)
- `Ops`: All except user management permissions
- `ReadOnly`: `distribution_log.view`, `tracing_reports.view`, `tracing_reports.download`, `approvals.view`

---

## Template Structure

### Reuse Existing `eqms_starter` Templates

**Base template:** `app/eqms/templates/_layout.html` (reuse existing)

**Module-specific templates:**
- `app/eqms/templates/admin/distribution_log/list.html` - Distribution log list
- `app/eqms/templates/admin/distribution_log/edit.html` - Manual entry / edit form
- `app/eqms/templates/admin/distribution_log/import.html` - CSV/PDF import forms
- `app/eqms/templates/admin/tracing/list.html` - Tracing reports list
- `app/eqms/templates/admin/tracing/generate.html` - Generate report form
- `app/eqms/templates/admin/tracing/detail.html` - Report detail with approvals

**Template patterns:**
- Use existing `eqms_starter` design system (`design-system.css`)
- Use existing form components (reuse existing form patterns)
- Use existing table components (reuse existing table patterns)
- Minimal styling (boring, functional UI)

---

## Navigation Menu

### Admin Navigation (Top Bar)

```
[Home] [Distribution Log] [Tracing Reports] [Users] [Audit Log]
```

**Menu items:**
- `Home`: Existing admin dashboard (`/admin`)
- `Distribution Log`: Distribution log list (`/admin/distribution-log`)
- `Tracing Reports`: Tracing reports list (`/admin/tracing`)
- `Users`: User management (existing)
- `Audit Log`: Audit log viewer (existing)

---

## User Workflows

### Workflow 1: Create Distribution Entry

1. Navigate to `/admin/distribution-log`
2. Click [Manual Entry]
3. Fill form (Ship Date, Facility, SKU, Lot, Quantity)
4. Optionally upload evidence file (PDF/image)
5. Click [Save Distribution]
6. Entry appears in list

---

### Workflow 2: Import Distributions from CSV

1. Navigate to `/admin/distribution-log`
2. Click [Import CSV]
3. Upload CSV file
4. Review import results (success count, errors)
5. Fix errors and re-import if needed
6. Entries appear in list

---

### Workflow 3: Generate Tracing Report

1. Navigate to `/admin/tracing`
2. Click [Generate]
3. Select filters (Month, Rep, Source, SKU, Customer)
4. Click [Generate Report]
5. Report generated, redirects to detail page
6. Click [Download CSV] to download

---

### Workflow 4: Upload Approval Evidence

1. Navigate to `/admin/tracing/<report_id>`
2. In "Approval Evidence" section, click [Choose File]
3. Select .eml file (email export from email client)
4. Click [Upload Approval]
5. Approval appears in "Uploaded Approvals" list
6. Click [Download] to view .eml file

---

## Non-Goals / Explicitly Excluded UI

1. **Rep Pages**: No `/rep/<slug>` routes, no rep-specific dashboards, no rep login/logout
2. **Analytics Dashboards**: No stats pages, no charts/graphs (beyond basic counts in filters)
3. **Email Sending UI**: No email compose forms, no SMTP configuration UI
4. **Complex Filters**: No advanced search, no full-text search (basic dropdown filters only)
5. **Bulk Operations**: No bulk edit, no bulk delete (individual operations only)
6. **Report Templates**: No custom CSV formats, no PDF reports (CSV only)

---

**End of UI Map**
