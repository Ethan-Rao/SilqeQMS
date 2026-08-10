# Repo Cleanup Phase 1: Legacy/Dead Code Removal

**Date:** 2026-01-26  
**Priority:** P1 (High)  
**Scope:** Identify and safely remove legacy/dead code that interferes with maintainability. **No functional changes.**

---

## Inventory of Legacy/Dead Code

### Confirmed Legacy Files

| Path | Status | Action | Risk if Kept | Verification |
|------|--------|--------|--------------|--------------|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/` | Clearly marked legacy | **DELETE** folder | Confusion, accidental use | `grep -r "legacy/DO_NOT_USE" app/` → Should return nothing |
| `legacy/DO_NOT_USE__REFERENCE_ONLY/README.md` | Documents legacy status | **DELETE** with folder | None | N/A |

### Potentially Unused Scripts

| Path | Purpose | Status | Action | Verification |
|------|---------|--------|--------|--------------|
| `scripts/attach_admin_role.py` | One-time admin role assignment | **KEEP** (may be needed for new deployments) | Monitor | Check if referenced in docs/README |
| `scripts/backfill_sales_order_matching.py` | One-time backfill | **KEEP** (useful for data fixes) | Monitor | Check if referenced in docs |
| `scripts/cleanup_zero_order_customers.py` | Cleanup script | **KEEP** (useful utility) | Monitor | Check if referenced in docs |
| `scripts/import_equipment_and_suppliers.py` | Equipment import | **KEEP** (active feature) | Monitor | Verify equipment module uses this |
| `scripts/refresh_customers_from_sales_orders.py` | Customer refresh | **KEEP** (needed for Phase 1) | Monitor | Will be used in Phase 1 |
| `scripts/release.py` | Migrations + seed | **KEEP** (canonical, used by `start.py`) | Critical | Verify `start.py` imports this |
| `scripts/start.py` | Production startup | **KEEP** (canonical, DO run command) | Critical | Verify DO uses this |

**Recommendation:** All scripts appear to be in use. **No deletions needed.**

### Duplicate Entrypoints

| Path | Purpose | Status | Action | Notes |
|------|---------|--------|--------|-------|
| `app/wsgi.py` | WSGI entrypoint | **CANONICAL** | Keep | Used by gunicorn in `start.py` |
| `app/eqms/__init__.py::create_app()` | Flask app factory | **CANONICAL** | Keep | Called by `wsgi.py` |
| `scripts/start.py` | Production startup | **CANONICAL** | Keep | DO run command |

**Verification:**
- `app/wsgi.py` imports `create_app()` from `app.eqms` ✅
- `scripts/start.py` runs `release.py` then starts gunicorn with `app.wsgi:app` ✅
- **No duplicate entrypoints found** — all are canonical and in use.

### Unused Routes/Templates

**Check for orphaned routes:**
```bash
# Find all routes
grep -rn "@bp.get\|@bp.post" app/eqms/modules/*/admin.py

# Find all templates
find app/eqms/templates -name "*.html"

# Cross-reference: routes should have templates, templates should be rendered
```

**Known Routes (Verified in Use):**
- Distribution Log routes → Templates exist ✅
- Sales Orders routes → Templates exist ✅
- Customer Profiles routes → Templates exist ✅
- Sales Dashboard routes → Templates exist ✅
- Tracing routes → Templates exist ✅

**Recommendation:** No orphaned routes identified. **No deletions needed.**

### Old Parsing Code

| Location | Purpose | Status | Action |
|----------|---------|--------|--------|
| `app/eqms/modules/rep_traceability/parsers/pdf.py` | PDF parsing | **ACTIVE** | Keep |
| `app/eqms/modules/rep_traceability/parsers/csv.py` | CSV parsing | **ACTIVE** | Keep |
| `app/eqms/modules/shipstation_sync/parsers.py` | LotLog parsing | **ACTIVE** | Keep |

**Recommendation:** All parsers are in use. **No deletions needed.**

### Abandoned Data Models

**Check for unused models:**
```bash
# Find all models
grep -rn "class.*Base" app/eqms/modules/*/models.py

# Check if models are imported/used
grep -rn "from.*models import" app/eqms/modules/
```

**Known Models (Verified in Use):**
- `SalesOrder`, `SalesOrderLine`, `OrderPdfAttachment` → Used in admin routes ✅
- `DistributionLogEntry` → Used in admin routes ✅
- `Customer`, `CustomerNote` → Used in admin routes ✅
- `TracingReport`, `ApprovalEml` → Used in admin routes ✅

**Recommendation:** No abandoned models identified. **No deletions needed.**

---

## Single Source of Entrypoint Truth

### Canonical Entrypoints (Verified)

**Production:**
- **WSGI:** `app/wsgi.py` → `from app.eqms import create_app; app = create_app()`
- **Startup:** `scripts/start.py` → Runs `release.py`, then `gunicorn app.wsgi:app`
- **App Factory:** `app/eqms/__init__.py::create_app()` → Creates Flask app, registers blueprints

**Development (if different):**
- Should also use `app.wsgi:app` or `create_app()` directly
- No separate dev entrypoint needed

### Files That Should Be Canonical

| File | Status | Notes |
|------|--------|-------|
| `app/wsgi.py` | ✅ Canonical | Used by gunicorn |
| `app/eqms/__init__.py` | ✅ Canonical | App factory, blueprint registration |
| `scripts/start.py` | ✅ Canonical | DO run command |
| `scripts/release.py` | ✅ Canonical | Migrations + seed, called by `start.py` |

**Recommendation:** All entrypoints are already canonical. **No changes needed.**

---

## What to Delete vs Deprecate

### Safe to Delete

| Item | What to Remove | Why Safe | How to Validate Nothing Broke |
|------|----------------|----------|------------------------------|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/` folder | Entire folder | Clearly marked as legacy, not referenced | 1. Run: `grep -r "DO_NOT_USE" app/` → Should return nothing<br>2. Run: `grep -r "legacy" app/` → Should return nothing<br>3. Verify app starts: `python scripts/start.py`<br>4. Verify all routes work (smoke test) |

### Should Not Delete (Keep)

| Item | Why Keep |
|------|----------|
| All scripts in `scripts/` | All appear to be in use (release, start, backfill, refresh, etc.) |
| All templates | All appear to be rendered by routes |
| All models | All appear to be used by routes |
| All parsers | All appear to be used by import routes |

---

## Validation Steps

### Before Deletion

1. **Search for references:**
   ```bash
   grep -r "DO_NOT_USE" app/
   grep -r "legacy/DO_NOT_USE" .
   grep -r "legacy" app/eqms/
   ```

2. **Verify app still works:**
   ```bash
   python scripts/start.py
   # Or test locally:
   python -c "from app.wsgi import app; print('OK')"
   ```

3. **Check routes:**
   - Verify all routes in `admin.py` files have corresponding templates
   - Verify no 404 errors for deleted files

### After Deletion

1. **Verify app starts:**
   ```bash
   python scripts/start.py
   ```

2. **Smoke test routes (browser):**
   - `/admin/` → Admin dashboard
   - `/admin/distribution-log` → Distribution Log
   - `/admin/sales-orders` → Sales Orders
   - `/admin/customers` → Customers
   - `/admin/sales-dashboard` → Sales Dashboard

3. **Verify no broken imports:**
   ```bash
   python -c "from app.wsgi import app; print('Import OK')"
   ```

---

## Cleanup Execution Plan

### Step 1: Verify No References

**Command:**
```bash
grep -r "DO_NOT_USE" app/
grep -r "legacy/DO_NOT_USE" .
```

**Expected:** No results (or only in this cleanup doc).

### Step 2: Delete Legacy Folder

**Command:**
```bash
rm -rf legacy/DO_NOT_USE__REFERENCE_ONLY/
```

**Or if using Git:**
```bash
git rm -r legacy/DO_NOT_USE__REFERENCE_ONLY/
```

### Step 3: Verify App Still Works

**Commands:**
```bash
# Test import
python -c "from app.wsgi import app; print('Import OK')"

# Test startup (if local)
python scripts/start.py
# (Stop with Ctrl+C after verifying it starts)
```

### Step 4: Commit Changes

**If using Git:**
```bash
git add .
git commit -m "Remove legacy/DO_NOT_USE__REFERENCE_ONLY folder (cleanup)"
```

---

## Files to Delete

**Safe Deletions:**
- `legacy/DO_NOT_USE__REFERENCE_ONLY/` (entire folder)

**Total:** 1 folder deletion

---

## Regression Checklist

After cleanup:
- [ ] App imports without errors: `python -c "from app.wsgi import app; print('OK')"`
- [ ] App starts: `python scripts/start.py` (or test locally)
- [ ] All routes accessible (smoke test in browser):
  - [ ] `/admin/` loads
  - [ ] `/admin/distribution-log` loads
  - [ ] `/admin/sales-orders` loads
  - [ ] `/admin/customers` loads
  - [ ] `/admin/sales-dashboard` loads
- [ ] No 404 errors for deleted files
- [ ] No broken template references

---

## Summary

**Safe to Delete:**
- ✅ `legacy/DO_NOT_USE__REFERENCE_ONLY/` folder

**Keep (All in Use):**
- ✅ All scripts in `scripts/`
- ✅ All templates
- ✅ All models
- ✅ All parsers
- ✅ All routes

**Canonical Entrypoints (Already Correct):**
- ✅ `app/wsgi.py` → `app.eqms.create_app()`
- ✅ `scripts/start.py` → `release.py` + `gunicorn app.wsgi:app`
- ✅ `app/eqms/__init__.py::create_app()`

**Recommendation:** Minimal cleanup needed. Only delete the clearly marked legacy folder. All other code appears to be in active use.

---

**End of Repo Cleanup Phase 1**
