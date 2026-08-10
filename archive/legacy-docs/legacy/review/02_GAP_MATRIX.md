# Gap Matrix: Rep QMS vs SilqeQMS

**Date:** 2026-01-15  
**Purpose:** Comparison matrix showing what exists, what's partial, and what's missing

---

## Legend

- ✅ **Already exists** - Feature is fully implemented in SilqeQMS
- 🟡 **Partial** - Feature is partially implemented or needs enhancement
- ❌ **Missing** - Feature does not exist in SilqeQMS
- 🔵 **Not needed** - Feature exists in legacy but excluded from migration (rep pages, email sending)

---

## Core Features

### Distribution Log

| Capability | Legacy Rep QMS | SilqeQMS | Status | Risk if Missing |
|------------|----------------|----------|--------|-----------------|
| Manual entry | ✅ | ✅ | ✅ Implemented | None |
| CSV import | ✅ | ✅ | ✅ Implemented | None |
| PDF import | ✅ | 🟡 | 🟡 P1 stub route | Low (manual entry fallback) |
| Edit entry | ✅ | ✅ | ✅ Implemented | None |
| Delete entry | ✅ | ✅ | ✅ Implemented | None |
| List with filters | ✅ | ✅ | ✅ Implemented | None |
| CSV export | ✅ | ✅ | ✅ Implemented | None |
| Customer linking | ✅ (FK) | 🟡 (text field) | 🟡 Partial | Medium (can't filter/aggregate by customer reliably) |
| Rep assignment | ✅ (FK) | ✅ (FK) | ✅ Implemented | None |
| Audit trail | ❌ | ✅ | ✅ Implemented | None (SilqeQMS is better) |
| Deduplication | ✅ | ✅ | ✅ Implemented | None |
| Evidence file upload | ✅ | ✅ | ✅ Implemented | None |

**Overall Status:** ✅ Complete (except PDF import P1)

---

### Tracing Reports

| Capability | Legacy Rep QMS | SilqeQMS | Status | Risk if Missing |
|------------|----------------|----------|--------|-----------------|
| Generate report | ✅ | ✅ | ✅ Implemented | None |
| Filter by month | ✅ | ✅ | ✅ Implemented | None |
| Filter by rep | ✅ | ✅ | ✅ Implemented | None |
| Filter by source | ✅ | ✅ | ✅ Implemented | None |
| Filter by SKU | ✅ | ✅ | ✅ Implemented | None |
| Filter by customer | ✅ | 🟡 | 🟡 (text filter, not FK) | Low (can filter by name) |
| CSV format | ✅ | ✅ | ✅ Implemented | None |
| Immutable storage | ✅ | ✅ | ✅ Implemented | None |
| Report metadata | ✅ | ✅ | ✅ Implemented | None |
| Report download | ✅ | ✅ | ✅ Implemented | None |
| Email sending | ✅ | 🔵 | 🔵 Explicitly excluded | None (replaced with .eml upload) |

**Overall Status:** ✅ Complete

---

### Approval Evidence (.eml Upload)

| Capability | Legacy Rep QMS | SilqeQMS | Status | Risk if Missing |
|------------|----------------|----------|--------|-----------------|
| Upload .eml file | ❌ | ✅ | ✅ Implemented | None |
| Link to report | ❌ | ✅ | ✅ Implemented | None |
| Extract headers | ❌ | ✅ | ✅ Implemented | None |
| Store immutably | ❌ | ✅ | ✅ Implemented | None |
| Download .eml | ❌ | ✅ | ✅ Implemented | None |
| Email sending | ✅ | 🔵 | 🔵 Explicitly excluded | None (replaced with .eml upload) |

**Overall Status:** ✅ Complete (new feature, better than legacy)

---

### Customer Profiles

| Capability | Legacy Rep QMS | SilqeQMS | Status | Risk if Missing |
|------------|----------------|----------|--------|-----------------|
| Customers table | ✅ | ❌ | ❌ Missing | **HIGH** (can't link distributions to customers reliably) |
| Customer CRUD | ✅ | ❌ | ❌ Missing | **HIGH** (can't manage customer master data) |
| Customer list | ✅ | ❌ | ❌ Missing | Medium (can see customers in distribution log) |
| Customer profile | ✅ | ❌ | ❌ Missing | Medium (can see in distribution log entry) |
| Customer notes | ✅ | ❌ | ❌ Missing | Low (nice-to-have CRM feature) |
| Rep assignments | ✅ | ❌ | ❌ Missing | Medium (can assign rep per distribution entry, not per customer) |
| Customer search/filter | ✅ | ❌ | ❌ Missing | Low (can search in distribution log) |
| Customer-distribution link | ✅ (FK) | 🟡 (text field) | 🟡 Partial | **HIGH** (can't aggregate by customer, unreliable filtering) |

**Overall Status:** ❌ Missing (Critical gap for production use)

**Risk Assessment:**
- **HIGH Risk:** Without `customers` table and FK linking, Distribution Log entries use free-text `customer_name`, making customer-based filtering, aggregation, and reporting unreliable
- **Impact:** Sales Dashboard cannot accurately show first-time vs repeat customers without proper customer linking

---

### Sales Dashboard

| Capability | Legacy Rep QMS | SilqeQMS | Status | Risk if Missing |
|------------|----------------|----------|--------|-----------------|
| Dashboard route | ✅ | ❌ | ❌ Missing | Medium (reduces business visibility) |
| Total orders | ✅ | ❌ | ❌ Missing | Low (can count in distribution log) |
| Total units | ✅ | ❌ | ❌ Missing | Low (can sum in distribution log) |
| Total customers | ✅ | ❌ | ❌ Missing | Medium (requires customer linking) |
| First-time customers | ✅ | ❌ | ❌ Missing | Medium (requires customer linking) |
| Repeat customers | ✅ | ❌ | ❌ Missing | Medium (requires customer linking) |
| SKU breakdown | ✅ | ❌ | ❌ Missing | Low (can filter by SKU in distribution log) |
| Lot tracking | ✅ | ❌ | ❌ Missing | Low (can see lots in distribution log) |
| Date window filter | ✅ | ❌ | ❌ Missing | Low (can filter in distribution log) |
| Export CSV | ✅ | ❌ | ❌ Missing | Low (can export distribution log) |

**Overall Status:** ❌ Missing (P1/P2 feature)

**Risk Assessment:**
- **Medium Risk:** Missing analytics/reporting reduces business visibility
- **Impact:** Admin cannot quickly see sales metrics (first-time vs repeat customers, SKU totals, etc.)
- **Workaround:** Can compute manually from Distribution Log export, but inefficient

---

### Infrastructure

| Capability | Legacy Rep QMS | SilqeQMS | Status | Risk if Missing |
|------------|----------------|----------|--------|-----------------|
| RBAC | ❌ (admin-only routes) | ✅ | ✅ Implemented | None (SilqeQMS is better) |
| Audit trail | ❌ (minimal) | ✅ | ✅ Implemented | None (SilqeQMS is better) |
| Storage abstraction | ❌ (filesystem) | ✅ | ✅ Implemented | None (SilqeQMS is better) |
| Migrations | ❌ (manual SQL) | ✅ | ✅ Alembic | None (SilqeQMS is better) |
| Session auth | ✅ | ✅ | ✅ Implemented | None |

**Overall Status:** ✅ Complete (SilqeQMS infrastructure is superior)

---

## Excluded Features (Not in Migration)

| Feature | Legacy Rep QMS | SilqeQMS | Status | Justification |
|---------|----------------|----------|--------|---------------|
| Rep pages | ✅ | 🔵 | 🔵 Explicitly excluded | No rep-specific UI |
| Email sending | ✅ | 🔵 | 🔵 Explicitly excluded | Replaced with .eml upload |
| Hospital targeting | ✅ | 🔵 | 🔵 Not core | Not essential for distribution tracking |
| Facility search | ✅ | 🔵 | 🔵 Not core | Can use distribution log filters |
| ShipStation sync | ✅ | ❌ | ❌ P1 deferred | Can be added later |

---

## Critical Gaps (Must Fix Before Production)

### 1. Customer Profiles Missing (HIGH Risk)

**Impact:**
- Distribution Log entries cannot reliably link to customer master data
- Customer-based filtering/aggregation unreliable (using free-text `customer_name`)
- Sales Dashboard cannot accurately show first-time vs repeat customers

**Required Fix:**
- Implement `customers` table
- Add `customer_id` FK to `distribution_log_entries`
- Implement customer CRUD routes
- Update Distribution Log forms to select/create customers

**Priority:** P0 (if customer linking required) or P1 (if standalone CRM acceptable)

---

### 2. Sales Dashboard Missing (MEDIUM Risk)

**Impact:**
- Admin cannot quickly see sales metrics (orders, units, customers, first-time vs repeat)
- Manual calculation required from Distribution Log export

**Required Fix:**
- Implement `/admin/sales-dashboard` route
- Compute aggregations on-demand from `distribution_log_entries`
- Basic stats: total orders, units, customers, first-time vs repeat, SKU breakdown
- Export functionality

**Priority:** P1 (important for business visibility) or P2 (nice-to-have)

---

## Medium-Risk Gaps

### 3. Customer Linking Partial (MEDIUM Risk)

**Current State:**
- `distribution_log_entries` uses `customer_name` text field
- Schema doc references `customer_id` FK, but not implemented
- No FK constraint ensures data integrity

**Impact:**
- Customer names may be inconsistent (typos, variations)
- Cannot reliably filter/aggregate by customer
- Customer updates don't cascade to distribution entries

**Required Fix:**
- Add `customer_id` FK column to `distribution_log_entries`
- Migrate existing `customer_name` values to `customers` table
- Update forms to select/create customers (not free-text)

**Priority:** P0 (if Customer Profiles is P0) or P1 (if Customer Profiles is P1)

---

## Low-Risk Gaps (Acceptable for Now)

### 4. PDF Import Missing (LOW Risk)

**Impact:**
- Cannot bulk import from PDF files
- Manual entry fallback exists

**Required Fix:**
- Implement PDF parser (P1)

**Priority:** P1 (deferred, not critical)

### 5. ShipStation Sync Missing (LOW Risk)

**Impact:**
- Cannot automatically sync orders from ShipStation
- Manual/CSV import fallback exists

**Required Fix:**
- Extract ShipStation API client
- Background job integration (P1)

**Priority:** P1 (deferred, not critical)

---

## Summary by Status

**✅ Already Exists (No Action Needed):**
- Distribution Log CRUD
- Tracing Reports generation
- Approval .eml uploads
- Infrastructure (RBAC, audit, storage, migrations)

**🟡 Partial (Needs Enhancement):**
- Customer linking (text field, needs FK)
- Customer filter in Tracing Reports (text filter, needs FK)

**❌ Missing (Must Implement):**
- Customer Profiles (P0/P1)
- Sales Dashboard (P1/P2)
- PDF import (P1)
- ShipStation sync (P1)

---

## Risk Prioritization

### Must Fix Before Production (P0)

1. **Customer Profiles** - If required for Distribution Log customer linking
2. **Customer-Distribution FK** - If Customer Profiles is P0

### Important (P1)

3. **Customer Profiles** - If standalone CRM acceptable
4. **Sales Dashboard** - Business visibility/analytics
5. **PDF Import** - Bulk import workflow

### Nice to Have (P2)

6. **Sales Dashboard** - If simple aggregations not sufficient
7. **Advanced filters** - Full-text search, complex queries

### Deferred (Later)

8. **ShipStation Sync** - Background job integration
9. **Dashboard caching** - Materialized views if performance needed

---

## References

- **Legacy Rep QMS:** `C:\Users\Ethan\OneDrive\Desktop\UI\RepsQMS\Proto1.py`
- **SilqeQMS Implementation:** `app/eqms/modules/rep_traceability/`
- **Progress Summary:** [docs/review/00_PROGRESS_SUMMARY.md](docs/review/00_PROGRESS_SUMMARY.md)
- **Feature Map:** [docs/review/01_REP_QMS_FEATURE_MAP.md](docs/review/01_REP_QMS_FEATURE_MAP.md)
