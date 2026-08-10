# Phase 3: Data Correctness and PDF Import Fixes — Executive Summary

**Date:** 2026-01-27  
**Priority:** P0 (Critical)  
**Audience:** Developer Agent, Project Stakeholders

---

## What's Broken

### 1. Sales Dashboard Shows Wrong Data
**Problem:** Dashboard aggregates from **all** distributions (including unmatched), not just matched Sales Orders.

**Impact:** Metrics are inflated. Unmatched distributions (from ShipStation sync) are counted as orders/customers, making the dashboard unreliable.

**Evidence:**
- Dashboard reads from `DistributionLogEntry` without filtering `sales_order_id IS NOT NULL`
- Unmatched distributions appear in totals, customer counts, and first-time/repeat classification

### 2. PDF Import Failing (Internal Server Error)
**Problem:** Bulk PDF import route throws 500 errors.

**Impact:** Cannot import Sales Orders from PDFs, blocking the canonical pipeline (PDF → SO → Customer).

**Likely Causes:**
- PDF parsing errors (corrupted files, missing dependencies)
- Customer creation failures (duplicate `company_key`, race conditions)
- Missing error handling (exceptions not caught)

### 3. Customer Database Has Duplicates and Artifacts
**Problem:** 
- Duplicate customers due to inconsistent ShipStation naming (abbreviations, punctuation)
- Customers with 0 orders from development/backfills

**Impact:** Customer database is unreliable, making reporting and CRM features unusable.

**Evidence:**
- Multiple customers with same `company_key` (should be unique)
- Customers with no linked Sales Orders (should not exist)

### 4. ShipStation Sync Still Creates Customers (Partially Fixed)
**Problem:** Phase 2 attempted to fix this, but code review shows `_get_existing_customer_from_ship_to()` is still called as fallback.

**Impact:** Customers created from ShipStation raw data (not Sales Orders), violating canonical pipeline.

**Evidence:**
- `shipstation_sync/service.py:358` calls `_get_existing_customer_from_ship_to()` if no SO match found
- This creates customers directly from ShipStation `ship_to` data

### 5. Distribution Detail Views Broken
**Problem:**
- Single-page PDF upload fails if distribution has no `customer_id` (SO creation requires customer)
- Label PDF upload route missing
- Attachments not shown for unmatched distributions

**Impact:** Cannot match distributions to Sales Orders via PDF upload, blocking data correction workflow.

---

## Why It's Broken

### Root Cause: Pipeline Violations

**Intended Pipeline:**
```
ShipStation → Distribution (unmatched) → PDF Import → Sales Order → Customer → Dashboard
```

**Current Broken Flow:**
```
ShipStation → Customer (direct) ❌
ShipStation → Distribution (unmatched) → Dashboard (counted) ❌
PDF Import → Error (no error handling) ❌
Distribution Detail → PDF Upload → Fails (no customer) ❌
```

**Key Violations:**
1. **ShipStation creates customers directly** (should only create distributions)
2. **Dashboard counts unmatched distributions** (should only count matched SOs)
3. **PDF import has no error handling** (fails silently or crashes)
4. **Distribution upload requires customer** (but unmatched distributions have no customer)

---

## What We're Doing

### Phase 1: Stop the Bleeding (P0)
1. **Fix Sales Dashboard:** Filter to only matched Sales Orders (`sales_order_id IS NOT NULL`)
2. **Fix ShipStation Sync:** Remove all customer creation, set `customer_id = NULL` initially
3. **Fix PDF Import:** Add comprehensive error handling, validate dependencies, enforce size limits
4. **Fix Distribution Upload:** Create customer from PDF data before creating SO
5. **Add Label Upload:** Implement route for label PDF upload from distribution detail

### Phase 2: Clean Existing Data (P1)
1. **Deduplicate Customers:** Merge customers with same `company_key`, update all FKs
2. **Delete 0-Order Customers:** Remove customers with no matched Sales Orders
3. **Fix Race Conditions:** Add retry logic for concurrent customer creation

### Phase 3: Improve Matching (P2)
1. **Matching Service:** Implement deterministic matching logic (order number, date+address+SKU, label address)
2. **Admin Review Queue:** Add UI for reviewing suggested matches

---

## How We'll Confirm It's Correct

### Verification Queries

**1. Dashboard Correctness:**
```sql
-- Unmatched distributions should NOT be counted
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NULL;
-- Dashboard totals should match:
SELECT COUNT(DISTINCT order_number) FROM distribution_log_entries WHERE sales_order_id IS NOT NULL;
```

**2. Customer Cleanliness:**
```sql
-- No duplicates
SELECT company_key, COUNT(*) FROM customers GROUP BY company_key HAVING COUNT(*) > 1;
-- No 0-order customers
SELECT COUNT(*) FROM customers c LEFT JOIN sales_orders so ON so.customer_id = c.id WHERE so.id IS NULL;
```

**3. Pipeline Enforcement:**
```sql
-- Customers created from Sales Orders (not ShipStation)
SELECT c.id, c.facility_name, c.created_at, so.created_at
FROM customers c
JOIN sales_orders so ON so.customer_id = c.id
WHERE c.created_at < so.created_at;
-- Should return 0 rows (customers created with or after SOs)
```

### Browser Verification

**1. Sales Dashboard:**
- Go to `/admin/sales-dashboard`
- Verify totals match SQL query results (only matched distributions)
- Verify unmatched distributions do not appear in customer lists

**2. PDF Import:**
- Upload bulk PDFs via `/admin/sales-orders/import-pdf`
- Verify no 500 errors (graceful error messages if parse fails)
- Verify Sales Orders created and linked to distributions
- Verify unmatched PDFs stored (if parse fails)

**3. Distribution Detail:**
- Go to Distribution Log → Click "Details" on unmatched distribution
- Upload PDF → Verify SO created and distribution matched
- Upload label PDF → Verify label linked to distribution
- Verify attachments shown (both SO-level and distribution-level)

**4. Customer Database:**
- Go to `/admin/customers`
- Verify no duplicates (same facility name appears only once)
- Verify all customers have ≥1 matched Sales Order
- Verify customer details come from Sales Orders (not ShipStation)

---

## Success Criteria

**Phase 3 is complete when:**
- ✅ Sales dashboard shows only matched Sales Orders (unmatched excluded)
- ✅ PDF import works reliably (no 500 errors, proper error handling)
- ✅ Customer database is clean (no duplicates, no 0-order customers)
- ✅ ShipStation sync creates distributions only (no direct customer creation)
- ✅ Distribution detail views work (PDF upload, label upload, attachments)
- ✅ All verification queries pass (SQL + browser)

**Expected Timeline:**
- P0 fixes: 1-2 days (critical path)
- P1 cleanup: 1 day (script development + execution)
- P2 improvements: 1 day (optional, can defer)

---

**End of Executive Summary**
