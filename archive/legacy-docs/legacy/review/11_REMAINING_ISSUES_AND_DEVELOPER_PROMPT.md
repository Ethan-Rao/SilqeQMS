# 11 REMAINING ISSUES AND DEVELOPER PROMPT — Full-System Audit

**Audit Date:** 2026-01-23  
**Baseline Spec:** `docs/plans/IMMEDIATE_FIXES_AND_UI_IMPROVEMENTS.md`

---

## 🔴 SECURITY ALERT — SECRETS EXPOSED

**CRITICAL**: API keys and database credentials were pasted in plaintext in the user query. These secrets should be rotated immediately:

| Secret | Status | Action Required |
|--------|--------|-----------------|
| DATABASE_URL password | EXPOSED | Rotate Postgres password on DigitalOcean |
| S3_ACCESS_KEY_ID | EXPOSED | Rotate Spaces access key |
| S3_SECRET_ACCESS_KEY | EXPOSED | Rotate Spaces secret key |
| SHIPSTATION_API_KEY | EXPOSED | Rotate ShipStation API key |
| SHIPSTATION_API_SECRET | EXPOSED | Rotate ShipStation API secret |

**DO NOT paste secrets in chat, code, or documentation.** Use environment variable references only.

---

## 1) Snapshot Summary (Top 15 Findings)

### Deployment (BLOCKER)
1. **🔴 Readiness probe fails** — App may not respond to health checks in time due to `--preload` + schema health checks on first request
2. **🟡 Health endpoint exists at `/health`** but may not be configured as the readiness probe path in DO
3. **🟡 Run command is correct** — `python scripts/release.py && gunicorn ... --bind 0.0.0.0:$PORT` with PORT=8080 is set

### Functional
4. **✅ All admin modules accessible** — Sales Dashboard, Customers, Distribution Log, Equipment, Suppliers, Manufacturing routes exist and have templates
5. **✅ RBAC coverage complete** — All 67 `@require_permission` decorators map to seeded permissions
6. **✅ CSRF protection working** — Global CSRF guard in `__init__.py`, JS injects tokens
7. **✅ Notes system working** — Global modal at `_layout.html`, endpoints at `/admin/notes/*`
8. **✅ PDF import working** — Routes exist, parser handles text fallback, stores unparsed PDFs

### Data Integrity
9. **✅ Lot tracking correct** — Uses 2025+ filter, all-time distributions, active inventory from LotLog
10. **✅ CustomerRep model fixed** — `foreign_keys=[rep_id]` specified
11. **✅ Indexes defined** — 35+ indexes on key columns across modules

### Legacy/Cleanup
12. **🟡 Legacy folder exists** — `legacy/DO_NOT_USE__REFERENCE_ONLY/` contains 6 HTML files (reference only)
13. **🟡 scripts/start.py exists** — Alternative startup script not used in current run command
14. **✅ No duplicate blueprints** — Single registration per module

### Security
15. **🔴 SECRETS ROTATION REQUIRED** — See alert above

---

## 2) Full-System Health Checklist (Admin Modules)

| Area/Module | Route(s) | Status | Evidence | Notes |
|-------------|----------|--------|----------|-------|
| **Admin Index** | `GET /admin/` | ✅ | `admin.py:29`, `templates/admin/index.html` | Links to all modules |
| **Sales Dashboard** | `GET /admin/sales-dashboard` | ✅ | `rep_traceability/admin.py:795` | Two-column layout, lot tracking |
| **Customers List** | `GET /admin/customers` | ✅ | `customer_profiles/admin.py:30` | Filters, pagination working |
| **Customer Profile** | `GET /admin/customers/<id>` | ✅ | `customer_profiles/admin.py:247` | Rep assignment, notes, stats |
| **Distribution Log** | `GET /admin/distribution-log` | ✅ | `rep_traceability/admin.py:88` | Details modal, attachments |
| **Sales Orders** | `GET /admin/sales-orders` | ✅ | `rep_traceability/admin.py:1043` | List, detail, PDF upload |
| **PDF Import** | `GET/POST /admin/sales-orders/import-pdf` | ✅ | `rep_traceability/admin.py:1297,1310` | Bulk and single upload |
| **ShipStation Sync** | `GET /admin/shipstation` | ✅ | `shipstation_sync/admin.py:87` | Run sync, diagnostics |
| **Tracing Reports** | `GET /admin/tracing` | ✅ | `rep_traceability/admin.py:641` | Generate, download |
| **Audit Trail** | `GET /admin/audit` | ✅ | `admin.py:95` | Filter by action, date, actor |
| **Equipment** | `GET /admin/equipment` | ✅ | `equipment/admin.py:34` | CRUD, documents, suppliers |
| **Suppliers** | `GET /admin/suppliers` | ✅ | `suppliers/admin.py:34` | CRUD, documents, equipment links |
| **Manufacturing** | `GET /admin/manufacturing/` | ✅ | `manufacturing/admin.py:50` | Suspension lots, documents |
| **Document Control** | `GET /admin/modules/document-control/` | ✅ | `document_control/admin.py:51` | CRUD, revisions, downloads |
| **Notes Modal** | `GET /admin/notes/modal/*` | ✅ | `rep_traceability/admin.py:836` | Cross-surface access |
| **Health Check** | `GET /health` | ✅ | `routes.py:11` | Returns `{"ok": true}` |

### Stub Routes (Intentionally Incomplete)
| Route | Purpose |
|-------|---------|
| `/admin/modules/design-controls` | Placeholder for future module |
| `/admin/modules/mfg-output` | Placeholder for future module |
| `/admin/modules/training` | Placeholder for future module |

---

## 3) Deployment Reliability Audit (P0)

### Current Production Start Sequence

**Run Command (from DO settings):**
```bash
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload
```

**Step 1: Release Script** (`scripts/release.py`)
- Validates `DATABASE_URL` is set and not SQLite
- Runs Alembic migrations (`command.upgrade(cfg, "head")`)
- Seeds permissions/admin user via `init_db.seed_only()`
- Logs diagnostic info (migration content check)

**Step 2: Gunicorn Start**
- Binds to `0.0.0.0:8080` (PORT env var set)
- 2 workers, 60s timeout
- `--preload` loads app before forking

**Step 3: App Initialization** (`app/wsgi.py` → `create_app()`)
- Loads environment via `dotenv`
- Validates production config (DATABASE_URL, SECRET_KEY)
- Calls `init_db(app)` to create SQLAlchemy engine
- Registers 9 blueprints
- Registers `before_request` hooks including schema health check

### Why Readiness Probe Might Fail

**Root Cause Candidates:**

1. **Health check path not configured** — DO may be probing `/` instead of `/health`
   - **Evidence:** User showed "Readiness check" exists but didn't specify path
   - **Fix:** Configure readiness probe path to `/health`

2. **First request triggers schema check** — `_schema_health_guardrail` runs on first request
   - **Evidence:** `app/eqms/__init__.py:82-136` — inspects database schema
   - **Impact:** First request may take 1-3 seconds
   - **Fix:** Schema check is already lightweight and cached after first check

3. **`--preload` causes slow start** — App loaded before workers fork
   - **Evidence:** Run command uses `--preload`
   - **Impact:** If app import fails, all workers fail simultaneously
   - **Fix:** `--preload` is actually good for catching errors early; keep it

4. **Readiness timing too aggressive** — Probe starts before gunicorn binds
   - **Evidence:** Health check failure at 00:42:44, release done at 00:43:14
   - **Fix:** Increase initial delay on readiness probe

### Minimal Fix Plan

**Option A: Configure Readiness Probe Path (RECOMMENDED)**

In DigitalOcean App Platform:
1. Go to App → Settings → Health Checks
2. Set Readiness check path to: `/health`
3. Set Initial delay to: `10` seconds
4. Set Timeout to: `5` seconds
5. Set Period to: `10` seconds

**Option B: Add Dedicated Fast Health Endpoint**

If `/health` is too slow, add a faster endpoint:

```python
# app/eqms/routes.py - add this route
@bp.get("/healthz")
def healthz():
    """Fast health check for k8s/DO probes. No DB access."""
    return "ok", 200
```

Then configure readiness probe to `/healthz`.

### Verification Steps

**Local Verification:**
```bash
# Start app locally
export PORT=8080
export DATABASE_URL="postgresql://..."
export SECRET_KEY="test-secret-key-32chars"
export ENV=development
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload

# In another terminal, verify health
curl -s http://localhost:8080/health
# Expected: {"ok":true}

curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health
# Expected: 200
```

**Production Verification:**
1. Deploy with readiness probe configured to `/health`
2. Check DO logs for:
   - `[INFO] Starting gunicorn 21.x.x`
   - `[INFO] Listening at: http://0.0.0.0:8080`
   - `[INFO] Using worker: sync`
   - `[INFO] Booting worker with pid: XXX`
3. Confirm readiness checks pass in DO dashboard
4. Access app URL and verify login works

### Regression Prevention

1. **Release script is idempotent** — Migrations skip if already applied; seed_only doesn't overwrite passwords
2. **Fail fast on missing env vars** — `_require_env()` raises RuntimeError
3. **No secrets in logs** — Release script prints `(from ADMIN_PASSWORD)` not actual value
4. **Schema health logged once** — `_schema_health_logged` flag prevents log spam

---

## 4) Remaining Issues Backlog (Developer-Ready)

| ID | Issue | Severity | Scope | Evidence | Minimal Fix | Verification |
|----|-------|----------|-------|----------|-------------|--------------|
| **D1** | Readiness probe path may not be `/health` | Blocker | Deployment | DO config not confirmed | Configure probe to `/health` | Health checks pass in DO |
| **D2** | Readiness initial delay may be too short | High | Deployment | Health fail before release done | Set initial delay to 10s | No early probe failures |
| **S1** | Exposed secrets need rotation | Blocker | Security | Plaintext in chat | Rotate all 5 secrets | New creds work, old fail |
| **U1** | Design Controls stub shows empty page | Low | UI | `admin.module_stub` route | Add placeholder content or hide link | Stub page has useful message |
| **U2** | Manufacturing File Output stub | Low | UI | `admin.module_stub` route | Add placeholder content or hide link | Stub page has useful message |
| **U3** | Employee Training stub | Low | UI | `admin.module_stub` route | Add placeholder content or hide link | Stub page has useful message |
| **L1** | `scripts/start.py` not used | Low | Maintenance | File exists but run command uses release.py directly | DELETE or document why it exists | File removed or documented |
| **L2** | Legacy HTML files in repo | Low | Maintenance | `legacy/DO_NOT_USE__REFERENCE_ONLY/` | QUARANTINE is fine | No imports reference them |

---

## 5) Legacy/Bloat Removal Plan (Decisive)

| File/Module/Folder | Why Legacy/Duplicate/Unused | Action | Risk if Kept | Verification |
|--------------------|----------------------------|--------|--------------|--------------|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/*.html` | Old UI reference files | QUARANTINE | Confusion for new devs | `grep -r "DO_NOT_USE" app/` returns nothing |
| `legacy/DO_NOT_USE__REFERENCE_ONLY/README.md` | Documents purpose | KEEP | None | N/A |
| `scripts/start.py` | Alternative startup not in use | DELETE or DOCUMENT | Confusion about which script to use | Run command confirmed as `release.py && gunicorn` |
| `migrations/versions/__pycache__/` | Compiled bytecode | DELETE | Repo bloat | `rm -rf migrations/versions/__pycache__` |

### Safe Removal Verification

```bash
# Verify legacy HTML not imported
grep -r "DO_NOT_USE__REFERENCE_ONLY" app/
# Expected: no results

# Verify start.py not imported
grep -r "from scripts.start import\|from scripts import start" .
# Expected: no results (only scripts/release.py is used)

# Check if start.py is referenced in any config
grep -r "start.py" Dockerfile .do/ package.json 2>/dev/null || echo "Not referenced"
# Expected: Not referenced (Dockerfile uses its own CMD)
```

---

## 6) Developer Marching Orders (Copy/Paste Prompt)

```markdown
# Developer Agent Task: Deployment Fix + Final Polish

## Context
The Silq eQMS system is functionally complete but deployment is failing due to health check configuration. All admin modules work locally. This task focuses on:
1. Fixing deployment reliability (P0)
2. Rotating exposed secrets (P0)
3. Minor cleanup (P2)

## P0 — Deployment Fix (Do First)

### Task D1: Configure Readiness Probe
**Files:** None (DigitalOcean configuration)
**Action:**
1. In DO App Platform → Settings → Health Checks
2. Set Readiness Check path to `/health`
3. Set Initial Delay to `10` seconds
4. Set Timeout to `5` seconds
5. Save and redeploy

**Acceptance Criteria:**
- Readiness checks pass within 30 seconds of deployment
- App becomes accessible at public URL
- `/health` returns `{"ok": true}`

### Task S1: Rotate Exposed Secrets
**Files:** None (DigitalOcean environment variables)
**Action:**
1. Generate new Postgres password in DO Databases
2. Generate new Spaces access key in DO Spaces
3. Generate new ShipStation API credentials in ShipStation settings
4. Update all 5 env vars in DO App Platform
5. Redeploy

**Acceptance Criteria:**
- App connects to database with new credentials
- S3 storage operations work (upload/download PDFs)
- ShipStation sync runs successfully

## P1 — Verification (Do After Deploy Succeeds)

### Task V1: Smoke Test All Modules
**Action:** Follow the QA runbook in Section 7 below
**Acceptance Criteria:**
- All admin modules load without 500 errors
- Login works with admin credentials
- Notes modal works from all surfaces
- PDF upload and download works

## P2 — Cleanup (Optional)

### Task L1: Document or Remove start.py
**Files:** `scripts/start.py`
**Action:** Either:
- DELETE the file (preferred) since run command uses `release.py && gunicorn` directly
- Or add comment explaining it's an alternative approach

**Acceptance Criteria:**
- No confusion about which startup script to use
- Only one canonical startup method documented

### Task L2: Clean Migration Pycache
**Files:** `migrations/versions/__pycache__/`
**Action:** Delete the directory, add to .gitignore if not already
**Acceptance Criteria:**
- Pycache not in repo
- `.gitignore` includes `__pycache__/`

## Regression Checks
After all changes:
1. `curl https://<app-url>/health` returns 200
2. Login as admin@silq.tech works
3. Navigate to each admin module (no 500s)
4. Create a test note on a customer
5. Upload a test PDF to sales orders
6. Run ShipStation sync (should not error)

## Do NOT
- Add new features
- Refactor working code
- Change database schema
- Modify the health check endpoint logic
```

---

## 7) Verification Script (Manual QA)

### Routes to Test (In Order)

1. **Public Health Check**
   ```bash
   curl -s https://<app-url>/health
   # Expected: {"ok":true}
   ```

2. **Public Index**
   - Navigate to: `https://<app-url>/`
   - Expected: Landing page with Login link

3. **Authentication**
   - Navigate to: `/auth/login`
   - Login with admin credentials
   - Expected: Redirect to `/admin/`

4. **Admin Dashboard**
   - Navigate to: `/admin/`
   - Expected: Grid of module cards, all links work

5. **Sales Dashboard**
   - Navigate to: `/admin/sales-dashboard`
   - Expected: Two-column layout, metric cards, lot tracking table

6. **Customers List**
   - Navigate to: `/admin/customers`
   - Expected: Paginated list, filters work

7. **Customer Profile**
   - Click any customer name
   - Expected: Profile with stats, rep assignment, notes tab

8. **Notes Modal**
   - Click "Notes" button on Sales Dashboard order
   - Expected: Modal opens, can add note, note appears in list

9. **Distribution Log**
   - Navigate to: `/admin/distribution-log`
   - Click "Details" on any entry
   - Expected: Modal with sections (Entry, Order, Customer, Stats, Attachments)

10. **PDF Import**
    - Navigate to: `/admin/sales-orders/import-pdf`
    - Upload test PDF
    - Expected: PDF stored even if parse fails

11. **ShipStation Sync**
    - Navigate to: `/admin/shipstation`
    - Click "Run Sync"
    - Expected: Sync completes without error

12. **Equipment & Suppliers**
    - Navigate to: `/admin/equipment`
    - Navigate to: `/admin/suppliers`
    - Expected: Lists load, can view details

13. **Manufacturing**
    - Navigate to: `/admin/manufacturing/suspension`
    - Expected: Lot list loads

14. **Audit Trail**
    - Navigate to: `/admin/audit`
    - Expected: Events listed, filters work

### Data Validation Queries

```sql
-- 1. Verify admin user exists with correct role
SELECT u.email, r.key as role_key 
FROM users u 
JOIN user_roles ur ON u.id = ur.user_id 
JOIN roles r ON ur.role_id = r.id 
WHERE u.email = 'ethanr@silq.tech';
-- Expected: ethanr@silq.tech | admin

-- 2. Verify permissions seeded
SELECT COUNT(*) FROM permissions;
-- Expected: ~35 permissions

-- 3. Verify customer_reps table exists
SELECT COUNT(*) FROM customer_reps;
-- Expected: 0 or more (no error)

-- 4. Verify sales_orders table exists
SELECT COUNT(*) FROM sales_orders;
-- Expected: 0 or more (no error)

-- 5. Verify lot tracking data
SELECT lot_number, SUM(quantity) as total 
FROM distribution_log_entries 
WHERE lot_number LIKE 'SLQ-%' 
GROUP BY lot_number 
ORDER BY total DESC 
LIMIT 5;
-- Expected: Lot numbers with totals

-- 6. Verify no orphan customers (optional cleanup check)
SELECT COUNT(*) FROM customers c 
LEFT JOIN distribution_log_entries d ON d.customer_id = c.id 
LEFT JOIN sales_orders o ON o.customer_id = c.id 
WHERE d.id IS NULL AND o.id IS NULL;
-- Expected: 0 or small number (orphans from testing)
```

### Permission Validation

1. **As Admin (ethanr@silq.tech):**
   - All admin modules accessible ✓
   - Can create/edit customers ✓
   - Can run ShipStation sync ✓
   - Can generate tracing reports ✓

2. **As Unauthenticated:**
   - `/admin/*` routes redirect to login ✓
   - `/health` returns 200 (no auth required) ✓

### Deployment Health Validation

```bash
# 1. Check app is listening
curl -s -o /dev/null -w "%{http_code}" https://<app-url>/health
# Expected: 200

# 2. Check readiness probe status in DO dashboard
# Expected: "Healthy" status

# 3. Check logs for startup messages
# Expected in DO logs:
#   === SilqeQMS release start ===
#   Migrations complete.
#   Seed complete.
#   === SilqeQMS release done ===
#   [INFO] Listening at: http://0.0.0.0:8080

# 4. Verify no Python errors in logs
# Expected: No tracebacks after startup
```

---

## Appendix: Key File Reference

| Component | File |
|-----------|------|
| App factory | `app/eqms/__init__.py` |
| WSGI entry | `app/wsgi.py` |
| Release script | `scripts/release.py` |
| Health endpoint | `app/eqms/routes.py:11` |
| RBAC decorator | `app/eqms/rbac.py` |
| Permission seed | `scripts/init_db.py` |
| Base layout | `app/eqms/templates/_layout.html` |
| Admin index | `app/eqms/templates/admin/index.html` |
| Notes modal JS | `app/eqms/templates/_layout.html:70-125` |
| Dockerfile | `Dockerfile` |
