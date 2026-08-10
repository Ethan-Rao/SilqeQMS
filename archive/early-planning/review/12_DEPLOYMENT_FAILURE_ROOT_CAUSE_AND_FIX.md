# 12 DEPLOYMENT FAILURE ROOT CAUSE AND FIX

**Date:** 2026-01-23  
**Focus:** Deployment reliability + Runtime 500 fix + Sales Order ↔ Distribution contract

---

## 1) Executive Summary

The deployment failures are most likely caused by **DigitalOcean's readiness probe not being configured with the correct path (`/healthz`) and/or insufficient initial delay**. The app is starting correctly (logs show "Listening at: http://0.0.0.0:8080"), but the readiness probe either hits the wrong endpoint or starts checking before the app is fully ready.

Additionally, there is a **confirmed runtime 500 error** on `/admin/sales-orders/<id>` caused by a **missing import of `OrderPdfAttachment`** in the `sales_order_detail` function.

The Sales Order ↔ Distribution linkage is partially implemented (`sales_order_id` FK exists but is nullable). The business rule that "every distribution must have a matching sales order" requires making this FK NOT NULL after backfilling existing data.

---

## 2) Evidence & Findings

### Deployment Symptoms
- **Release phase completes successfully**: Alembic migrations run, permissions seeded
- **Gunicorn starts and binds**: Logs show `Listening at: http://0.0.0.0:8080` and workers boot
- **Intermittent readiness failures**: `Readiness probe failed: dial tcp <pod-ip>:8080: connect: connection refused`
- **App serves requests after startup**: Admin pages load successfully once up

### Health Endpoints (Verified)
- **`/health`** — `app/eqms/routes.py:11-14` — Returns `{"ok": true}`, no DB access
- **`/healthz`** — `app/eqms/routes.py:17-23` — Returns `"ok"` with 200, explicitly designed for k8s/DO probes, no DB access

### Runtime 500 Bug (Confirmed)
- **Route**: `GET /admin/sales-orders/115` (any order ID)
- **Error**: `NameError: name 'OrderPdfAttachment' is not defined`
- **Location**: `app/eqms/modules/rep_traceability/admin.py:1134`
- **Root cause**: Function `sales_order_detail` (line 1113) imports only `SalesOrder`:
  ```python
  from app.eqms.modules.rep_traceability.models import SalesOrder
  ```
  But then uses `OrderPdfAttachment` (line 1134) without importing it.

### Data Model (Verified)
- **`DistributionLogEntry.sales_order_id`** — FK exists, nullable (`app/eqms/modules/rep_traceability/models.py:205`)
- **`SalesOrder.customer_id`** — FK to customers, NOT NULL (`models.py:41`)
- **Customer canonical identity** — `customers.company_key` is unique; address/facility from sales orders

---

## 3) Root Cause Analysis (Deployment)

### Candidate 1: Readiness Probe Path Not Configured
| | |
|---|---|
| **Symptom** | "connection refused" despite app listening |
| **Mechanism** | DO probes default path `/` or undefined path; app may return redirect or slow response |
| **Evidence** | User showed "Readiness check" exists but path not specified |
| **Confidence** | **HIGH** — Most likely cause |
| **Fix** | Configure readiness probe path to `/healthz` |

### Candidate 2: No Initial Delay on Readiness Probe
| | |
|---|---|
| **Symptom** | Probe fails before app binds to port |
| **Mechanism** | Release script runs ~3-5 seconds; probe may start during that time |
| **Evidence** | Health check failure timestamp (00:42:44) before release done (00:43:14) in prior logs |
| **Confidence** | **HIGH** — Compounding factor |
| **Fix** | Set initial delay to 10-15 seconds |

### Candidate 3: `--preload` Causes Slow Startup
| | |
|---|---|
| **Symptom** | Workers slow to boot |
| **Mechanism** | Preload loads entire app before forking; any import error kills all workers |
| **Evidence** | `--preload` is in run command |
| **Confidence** | **LOW** — Preload is generally beneficial; no evidence of import crashes |
| **Fix** | Keep `--preload` for now; it catches import errors early |

### Candidate 4: Schema Health Check Blocks First Request
| | |
|---|---|
| **Symptom** | First request slow (1-3s) |
| **Mechanism** | `_schema_health_guardrail` in `__init__.py:82-136` inspects DB on first request |
| **Evidence** | Code confirmed; check runs once then caches |
| **Confidence** | **LOW** — Not blocking readiness since `/healthz` bypasses DB |
| **Fix** | No change needed; `/healthz` doesn't trigger this |

### Candidate 5: Missing PORT Environment Variable
| | |
|---|---|
| **Symptom** | Gunicorn binds to wrong port |
| **Mechanism** | `--bind 0.0.0.0:$PORT` fails if PORT not set |
| **Evidence** | User confirmed PORT=8080 is now set |
| **Confidence** | **RESOLVED** — No longer an issue |
| **Fix** | Already fixed |

---

## 4) Fix Plan

### P0 — Must Do Now

#### P0-1: Configure DigitalOcean Readiness Probe
**Location:** DO App Platform → Settings → Health Checks  
**Changes:**
- Path: `/healthz`
- Initial Delay: `15` seconds
- Timeout: `5` seconds
- Period: `10` seconds
- Failure Threshold: `3` attempts

#### P0-2: Fix OrderPdfAttachment Import (500 Bug)
**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Line:** 1117  
**Current:**
```python
from app.eqms.modules.rep_traceability.models import SalesOrder
```
**Fix:**
```python
from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
```

**Verification:**
```bash
curl -s https://<app>/admin/sales-orders/115 | grep -q "500\|NameError" && echo "FAIL" || echo "PASS"
```

#### P0-3: Separate Release Phase from Run Phase (Recommended)
**Current Run Command:**
```bash
python scripts/release.py && gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload
```

**Recommended Split:**

**Release Command** (in DO "Release Phase"):
```bash
python scripts/release.py
```

**Run Command** (in DO "Run Command"):
```bash
gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload --access-logfile - --error-logfile -
```

**Why:** Clearer separation; release failures don't affect run command; easier to debug.

#### P0-4: Add Smoke Test for Import Errors
Before each deploy, run:
```bash
python -c "from app.wsgi import app; print('Import OK')"
```
This catches NameError/ImportError before deploy reaches production.

### P1 — Hardening

#### P1-1: Add Structured Startup Logging
**File:** `app/eqms/__init__.py` — Add at end of `create_app()`:
```python
import logging
logging.getLogger(__name__).info("create_app() complete; app ready to serve")
```

**File:** `scripts/release.py` — Already has good logging (keep as-is)

#### P1-2: Guard Against Missing Env Vars
**File:** `app/eqms/config.py` — Already has `_getenv()` with defaults  
**File:** `scripts/release.py` — Already has `_require_env()` that fails fast  
**Status:** ✅ Already implemented

#### P1-3: Consider Removing --preload (Only If Issues Persist)
**Current:** Keep `--preload` for now  
**If issues persist:** Try without preload:
```bash
gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60
```
**Tradeoff:** Slower cold starts but may be more reliable in some edge cases.

### P2 — Cleanups

#### P2-1: Remove Unused scripts/start.py
**File:** `scripts/start.py`  
**Status:** Not used in current run command  
**Action:** DELETE or add deprecation comment

#### P2-2: Add Deploy Checklist Documentation
**File:** `docs/DEPLOY_CHECKLIST.md` (new)  
**Contents:** Health check config, verification steps, rollback procedure

---

## 5) Exact DigitalOcean App Platform Settings

### Readiness Probe (Copy/Paste)
```
Path: /healthz
Initial Delay Seconds: 15
Timeout Seconds: 5
Period Seconds: 10
Failure Threshold: 3
```

### Liveness Probe (Optional but Recommended)
```
Path: /healthz
Initial Delay Seconds: 30
Timeout Seconds: 5
Period Seconds: 30
Failure Threshold: 3
```

### Release Command (DO Release Phase)
```bash
python scripts/release.py
```

### Run Command (DO Run Command)
```bash
gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload --access-logfile - --error-logfile -
```

### Required Environment Variables
```
PORT=8080
ENV=production
DATABASE_URL=postgresql://...
SECRET_KEY=<64-char-hex>
ADMIN_EMAIL=...
ADMIN_PASSWORD=...
STORAGE_BACKEND=s3
S3_ENDPOINT=...
S3_REGION=...
S3_BUCKET=...
S3_ACCESS_KEY_ID=...
S3_SECRET_ACCESS_KEY=...
```

**⚠️ SECURITY NOTE:** If any secrets were exposed in logs/chat, rotate them immediately.

---

## 6) Sales Order ↔ Distribution Contract (Developer Notes)

### Business Rules (MUST BE ENFORCED)

1. **Every distribution must have a matching parsed Sales Order**
   - `distribution_log_entries.sales_order_id` should be NOT NULL (after backfill)
   - Manual entry UI must require selecting a sales order
   - CSV/PDF import must match or create sales order first

2. **Sales orders can exist with no shipment**
   - A sales order may have 0 distributions (e.g., pending order)
   - This is valid; do not enforce distribution existence

3. **Customer profile is derived from Sales Orders facility data**
   - `customers` table stores canonical customer identity
   - `sales_orders.customer_id` links order to customer
   - Customer address/facility comes from sales order ship-to data
   - ShipStation data is for assignment/linking only, not source of truth

### Current Schema (Verified)

**DistributionLogEntry** (`app/eqms/modules/rep_traceability/models.py:143-214`):
```python
sales_order_id: Mapped[int | None] = mapped_column(
    ForeignKey("sales_orders.id", ondelete="SET NULL"), 
    nullable=True  # ← Currently nullable; should become NOT NULL
)
```

**SalesOrder** (`models.py:12-83`):
```python
customer_id: Mapped[int] = mapped_column(
    ForeignKey("customers.id", ondelete="RESTRICT"), 
    nullable=False  # ✅ Already enforced
)
```

### Schema Change Plan (P1)

**Step 1: Backfill existing distributions**
```sql
-- Identify distributions without sales_order_id
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NULL;

-- Match by order_number if possible
UPDATE distribution_log_entries d
SET sales_order_id = (
    SELECT s.id FROM sales_orders s 
    WHERE s.order_number = d.order_number 
    LIMIT 1
)
WHERE d.sales_order_id IS NULL;
```

**Step 2: Create migration to make NOT NULL (only after backfill complete)**
```python
# migrations/versions/xxx_make_sales_order_id_not_null.py
def upgrade():
    # First verify no NULLs remain
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM distribution_log_entries WHERE sales_order_id IS NULL) THEN
                RAISE EXCEPTION 'Cannot make sales_order_id NOT NULL: NULL values exist';
            END IF;
        END $$;
    """)
    op.alter_column('distribution_log_entries', 'sales_order_id',
                    existing_type=sa.Integer(),
                    nullable=False)

def downgrade():
    op.alter_column('distribution_log_entries', 'sales_order_id',
                    existing_type=sa.Integer(),
                    nullable=True)
```

### Validation Requirements

**Manual Entry** (`admin.py:145-225`):
- Already validates `sales_order_id` if provided (line 191-199)
- Should require `sales_order_id` for manual source entries

**CSV/PDF Import**:
- Must match or create sales order before creating distribution
- Already partially implemented (import creates orders first)

### Verification SQL

```sql
-- Distributions without sales order (should be 0 after enforcement)
SELECT COUNT(*) FROM distribution_log_entries WHERE sales_order_id IS NULL;

-- Distributions with mismatched customer_id
SELECT d.id, d.customer_id, s.customer_id 
FROM distribution_log_entries d
JOIN sales_orders s ON d.sales_order_id = s.id
WHERE d.customer_id != s.customer_id;

-- Orphan sales orders (OK to have; just informational)
SELECT COUNT(*) FROM sales_orders s
LEFT JOIN distribution_log_entries d ON d.sales_order_id = s.id
WHERE d.id IS NULL;
```

---

## 7) Verification Steps

### Local Verification

```bash
# 1. Start app in prod-like mode
export PORT=8080
export ENV=development
export DATABASE_URL="postgresql://..."
export SECRET_KEY="test-key-32-chars-or-more"

# Run release (migrations + seed)
python scripts/release.py

# Start gunicorn
gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload

# 2. Test health endpoints (in another terminal)
curl -s http://localhost:8080/healthz
# Expected: ok

curl -s http://localhost:8080/health
# Expected: {"ok":true}

# 3. Test the fixed route
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/admin/sales-orders/1
# Expected: 200 (or 302 redirect to login, but not 500)

# 4. Verify no import errors
python -c "from app.wsgi import app; print('OK')"
# Expected: OK
```

### DigitalOcean Deploy Verification

1. **Configure Health Checks** (see Section 5)
2. **Deploy**
3. **Check Logs:**
   ```
   === SilqeQMS release start ===
   Running Alembic migrations...
   Migrations complete.
   Seed complete.
   === SilqeQMS release done ===
   [INFO] Listening at: http://0.0.0.0:8080
   [INFO] Booting worker with pid: XXX
   ```
4. **Verify Health:**
   ```bash
   curl -s https://<app-url>/healthz
   # Expected: ok
   ```
5. **Verify No 500 on Sales Orders:**
   ```bash
   # After login
   curl -s https://<app-url>/admin/sales-orders/1
   # Expected: HTML page (not 500 error)
   ```
6. **Smoke Test Routes:**
   - `/admin/` — Admin dashboard
   - `/admin/sales-dashboard` — Sales Dashboard
   - `/admin/customers` — Customers list
   - `/admin/distribution-log` — Distribution Log
   - `/admin/sales-orders` — Sales Orders list
   - `/admin/sales-orders/<id>` — Sales Order detail (the fixed route)

---

## 8) Developer Agent Prompt (Copy/Paste Marching Orders)

```markdown
# Developer Task: Fix Deployment + Runtime 500 + Sales Order Contract

## Context
Deployment has been failing intermittently due to health check configuration. 
There is also a confirmed 500 error on `/admin/sales-orders/<id>`.
The Sales Order ↔ Distribution linkage needs enforcement.

## P0 Tasks (Do Immediately, In Order)

### 1. Fix OrderPdfAttachment Import Error (500 Bug)
**File:** `app/eqms/modules/rep_traceability/admin.py`
**Line:** 1117
**Change:** Add `OrderPdfAttachment` to import:
```python
# FROM:
from app.eqms.modules.rep_traceability.models import SalesOrder
# TO:
from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
```
**Acceptance Criteria:**
- `GET /admin/sales-orders/<id>` returns 200 (not 500)
- PDF attachments section renders on order detail page

**Verification:**
```bash
python -c "from app.eqms.modules.rep_traceability.admin import sales_order_detail; print('OK')"
```

### 2. Configure DigitalOcean Health Checks
**Location:** DO App Platform → Settings → Health Checks
**Settings:**
- Readiness Path: `/healthz`
- Initial Delay: `15` seconds
- Timeout: `5` seconds
- Period: `10` seconds
- Failure Threshold: `3`

**Acceptance Criteria:**
- Health checks pass within 30 seconds of deploy
- No "connection refused" errors

### 3. Separate Release from Run (Recommended)
**Release Command:** `python scripts/release.py`
**Run Command:** `gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload --access-logfile - --error-logfile -`

**Acceptance Criteria:**
- Release phase completes before run phase starts
- Logs clearly show release vs run phases

## P1 Tasks (After Deploy Succeeds)

### 4. Add Pre-Deploy Smoke Test
Add to CI/CD or manual deploy checklist:
```bash
python -c "from app.wsgi import app; print('Import OK')"
```

### 5. Plan Sales Order Linkage Enforcement
- Audit distributions without `sales_order_id`
- Backfill via SQL matching on `order_number`
- Create migration to make `sales_order_id` NOT NULL (only after backfill)
- Update manual entry form to require sales order selection

## Files Likely Touched
- `app/eqms/modules/rep_traceability/admin.py` (import fix)
- DO App Platform settings (health check config)
- `scripts/start.py` (DELETE if unused)

## Regression Checks
- [ ] `/healthz` returns 200
- [ ] `/health` returns `{"ok":true}`
- [ ] `/admin/sales-orders/<id>` returns 200
- [ ] `/admin/sales-orders` list loads
- [ ] `/admin/distribution-log` loads
- [ ] Login as admin works
- [ ] No Python tracebacks in DO logs after deploy

## Do NOT
- Add new features
- Change database schema yet (backfill first)
- Remove `--preload` unless issues persist
- Log any secrets
```

---

## Appendix: Key File Reference

| Component | File | Line(s) |
|-----------|------|---------|
| Health endpoints | `app/eqms/routes.py` | 11-23 |
| App factory | `app/eqms/__init__.py` | 21-176 |
| Release script | `scripts/release.py` | 1-81 |
| WSGI entry | `app/wsgi.py` | 1-4 |
| Sales order detail (500 bug) | `app/eqms/modules/rep_traceability/admin.py` | 1113-1145 |
| OrderPdfAttachment model | `app/eqms/modules/rep_traceability/models.py` | 124-141 |
| DistributionLogEntry model | `app/eqms/modules/rep_traceability/models.py` | 143-214 |
| Customer model | `app/eqms/modules/customer_profiles/models.py` | 11-52 |
| Dockerfile | `Dockerfile` | 1-17 |
