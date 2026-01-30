# Developer Prompt: CRITICAL Database Connection Fix & System Audit
**Date:** 2026-01-30  
**Priority:** 🔴 CRITICAL - Production Down

---

## CRITICAL ISSUE: Internal Server Error on Login

### Error Summary

After successful login, users receive a 500 Internal Server Error. The application is completely unusable.

**Error from logs:**
```
psycopg2.OperationalError: SSL error: decryption failed or bad record mac
psycopg2.OperationalError: SSL SYSCALL error: EOF detected
```

**Location:** `app/eqms/auth.py`, line 45 (`load_current_user`)

---

## Root Cause Analysis

### The Problem: PostgreSQL SSL + Gunicorn `--preload` + Connection Pooling

This is a **well-known issue** with PostgreSQL SSL connections in multi-process environments:

1. **`--preload` in Dockerfile:** Gunicorn loads the app **before** forking workers
2. **Engine created at app init:** `create_engine()` is called in `init_db()` during `create_app()`
3. **Connection pool shared after fork:** When Gunicorn forks worker processes, they inherit the same connection pool
4. **SSL state corruption:** PostgreSQL SSL connections cannot be safely shared across forked processes - the SSL handshake state gets corrupted

**Sequence of events:**
```
1. scripts/start.py runs → create_app() called
2. create_app() → init_db() → create_engine() [CONNECTION POOL CREATED]
3. gunicorn --preload → App loaded in master process
4. gunicorn forks → Worker 1 inherits connection pool
5. gunicorn forks → Worker 2 inherits connection pool
6. User logs in → Worker 1 tries to use inherited SSL connection → FAILS
```

---

## CRITICAL FIX #1: Add Connection Pool Health Checks

**File:** `app/eqms/db.py`

**Current code (BROKEN):**
```python
def init_db(app: Flask) -> None:
    engine = create_engine(app.config["DATABASE_URL"], future=True)
    app.extensions["sqlalchemy_engine"] = engine
    # ...
```

**Fixed code:**
```python
from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Generator

from flask import Flask, g
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


def init_db(app: Flask) -> None:
    """
    Initialize database with proper connection pooling for Gunicorn + PostgreSQL SSL.
    
    CRITICAL: Uses pool_pre_ping=True to detect and discard stale connections.
    This is required when using --preload with Gunicorn, as forked workers
    inherit connections that may have corrupted SSL state.
    """
    db_url = app.config["DATABASE_URL"]
    
    # Detect if we're using PostgreSQL (needs special handling for SSL)
    is_postgres = db_url.startswith("postgres")
    
    engine_kwargs = {
        "future": True,
        # CRITICAL: Check connection health before each use
        # This catches SSL corruption from forked processes
        "pool_pre_ping": True,
    }
    
    if is_postgres:
        # Additional settings for PostgreSQL in production
        engine_kwargs.update({
            # Recycle connections every 30 minutes (before they go stale)
            "pool_recycle": 1800,
            # Use QueuePool (default) with conservative settings
            "pool_size": 5,
            "max_overflow": 10,
            # Timeout waiting for connection from pool
            "pool_timeout": 30,
        })
    
    engine = create_engine(db_url, **engine_kwargs)
    
    # Optional: Log connection checkouts for debugging
    if app.config.get("ENV") != "production":
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            app.logger.debug("DB connection checkout from pool")
    
    app.extensions["sqlalchemy_engine"] = engine
    app.extensions["sqlalchemy_sessionmaker"] = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


def db_session(app: Flask | None = None) -> Session:
    """
    Request-scoped session. Use inside request handlers.
    """
    if hasattr(g, "db_session") and g.db_session is not None:
        return g.db_session
    if app is None:
        from flask import current_app
        app = current_app
    sm = app.extensions["sqlalchemy_sessionmaker"]
    g.db_session = sm()
    return g.db_session


def teardown_db_session(_exc: BaseException | None) -> None:
    """
    Clean up session at end of request.
    Always close, even on exception, to return connection to pool.
    """
    s: Session | None = getattr(g, "db_session", None)
    if s is not None:
        try:
            s.close()
        except Exception:
            pass  # Connection may already be invalid
        g.db_session = None


@contextmanager
def session_scope(app: Flask) -> Generator[Session, None, None]:
    """
    Non-request helper for scripts: yields a session and commits/rolls back.
    """
    sm = app.extensions["sqlalchemy_sessionmaker"]
    s: Session = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
```

---

## CRITICAL FIX #2: Dispose Engine After Fork (Alternative/Additional)

If `pool_pre_ping` alone doesn't resolve the issue, add engine disposal after fork.

**File:** `app/eqms/__init__.py`

Add after `init_db(app)` (around line 86):

```python
init_db(app)

# CRITICAL: Dispose connection pool after Gunicorn forks workers
# This ensures each worker creates fresh connections
def _dispose_engine_on_fork():
    """Dispose engine connections when process forks (Gunicorn workers)."""
    import os
    if hasattr(os, 'register_at_fork'):
        def _after_fork_child():
            engine = app.extensions.get("sqlalchemy_engine")
            if engine:
                engine.dispose()
                app.logger.info("Disposed DB engine after fork (pid=%s)", os.getpid())
        
        os.register_at_fork(after_in_child=_after_fork_child)

_dispose_engine_on_fork()
```

---

## CRITICAL FIX #3: Update Gunicorn Configuration (Alternative)

If the above fixes don't work, remove `--preload` from Gunicorn. This causes each worker to load the app independently, avoiding the shared connection pool issue.

**File:** `Dockerfile`

**Current:**
```dockerfile
CMD ["sh", "-c", "gunicorn app.wsgi:app --preload --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60"]
```

**Option A - Remove preload (last resort):**
```dockerfile
CMD ["sh", "-c", "gunicorn app.wsgi:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60"]
```

**Option B - Keep preload with worker class (recommended if Option A needed):**
```dockerfile
CMD ["sh", "-c", "gunicorn app.wsgi:app --preload --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 60 --worker-class gthread --threads 2"]
```

**Note:** Try Fixes #1 and #2 first. Removing `--preload` is a last resort as it slows cold starts and loses the benefit of catching import errors early.

---

## Testing the Fix

### Local Testing (Simulating Production)

```bash
# 1. Set up environment
export DATABASE_URL="postgresql://user:pass@localhost:5432/eqms"
export SECRET_KEY="test-secret-key-32-chars"
export ENV="development"
export PORT=8080

# 2. Start with Gunicorn (simulating production)
gunicorn app.wsgi:app --preload --bind 0.0.0.0:8080 --workers 2 --timeout 60

# 3. Test login in another terminal
curl -c cookies.txt -X POST http://localhost:8080/auth/login \
  -d "email=admin@silqeqms.com&password=yourpassword"

# 4. Access admin page with session
curl -b cookies.txt http://localhost:8080/admin/

# Should return 200, not 500
```

### Production Verification

After deploying the fix:
1. Check logs for: `Disposed DB engine after fork` (if using Fix #2)
2. Login should redirect to `/admin/` without 500 error
3. No SSL errors in logs

---

## Additional Issues Identified (10+)

### ISSUE 2: Scripts Use Hardcoded Engine Without pool_pre_ping

**Severity:** MEDIUM

**Files:**
- `scripts/init_db.py`
- `scripts/attach_admin_role.py`
- `scripts/cleanup_zero_order_customers.py`
- `scripts/cleanup_pdf_import_distributions.py`
- `scripts/import_equipment_and_suppliers.py`

**Problem:** All scripts create engines with `create_engine(db_url, future=True)` without `pool_pre_ping=True`.

**Fix:** Create a shared utility:

```python
# scripts/_db_utils.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager

def create_script_engine(db_url: str):
    """Create engine with proper settings for scripts."""
    return create_engine(
        db_url,
        future=True,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

@contextmanager
def script_session(db_url: str):
    """Context manager for script database sessions."""
    engine = create_script_engine(db_url)
    sm = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    s = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
        engine.dispose()
```

---

### ISSUE 3: Storage.delete() Method Missing

**Severity:** HIGH

**File:** `app/eqms/storage.py`

**Problem:** `LocalStorage` and `S3Storage` don't implement `delete()`, but code in `equipment/admin.py` and `suppliers/admin.py` calls `storage.delete()`.

**Current error location:**
```python
# app/eqms/modules/equipment/admin.py, line 176
storage.delete(pdf_info["storage_key"])  # AttributeError: 'LocalStorage' object has no attribute 'delete'
```

**Fix:**
```python
class Storage:
    # ... existing methods ...
    
    def delete(self, key: str) -> bool:
        """Delete a file. Returns True if deleted, False if not found."""
        raise NotImplementedError


class LocalStorage(Storage):
    # ... existing methods ...
    
    def delete(self, key: str) -> bool:
        p = self._path(key)
        if p.exists():
            p.unlink()
            return True
        return False


class S3Storage(Storage):
    # ... existing methods ...
    
    def delete(self, key: str) -> bool:
        try:
            self._client().delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False
```

---

### ISSUE 4: Escaped Regex Bug Prevents Lot Year Extraction

**Severity:** HIGH

**File:** `app/eqms/modules/shipstation_sync/parsers.py` (lines 227, 234)

**Problem:** Double-escaped backslashes break regex patterns.

**Current (BROKEN):**
```python
m = re.search(r"(20\\d{2})", canonical_lot)  # Wrong: looks for literal \d
digits = re.sub(r"\\D", "", canonical_lot or "")  # Wrong: looks for literal \D
```

**Fix:**
```python
m = re.search(r"(20\d{2})", canonical_lot)  # Correct: matches 2000-2099
digits = re.sub(r"\D", "", canonical_lot or "")  # Correct: removes non-digits
```

---

### ISSUE 5: load_current_user Doesn't Handle DB Errors Gracefully

**Severity:** HIGH

**File:** `app/eqms/auth.py`

**Problem:** If the database connection fails during `load_current_user`, the entire request crashes with a 500 error. This should fail gracefully by clearing the session.

**Current:**
```python
def load_current_user() -> None:
    # ...
    user = s.get(User, int(user_id))  # Can raise OperationalError
    if not user or not user.is_active:
        session.pop("user_id", None)
        g.current_user = None
        return
    g.current_user = user
```

**Fix:**
```python
def load_current_user() -> None:
    """
    Loads g.current_user from the signed session cookie.
    Also assigns a simple per-request request_id (for audit/log correlation).
    
    IMPORTANT: Gracefully handles DB errors to prevent total app failure.
    """
    if not getattr(g, "request_id", None):
        g.request_id = uuid.uuid4().hex

    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return

    try:
        s = db_session()
        user = s.get(User, int(user_id))
        if not user or not user.is_active:
            session.pop("user_id", None)
            g.current_user = None
            return
        g.current_user = user
    except Exception as e:
        # DB error - clear session and continue as unauthenticated
        # This prevents total app failure if DB is temporarily unavailable
        current_app.logger.error("load_current_user DB error (clearing session): %s", e)
        session.pop("user_id", None)
        g.current_user = None
```

---

### ISSUE 6: Static Files Trigger Database Queries

**Severity:** MEDIUM

**File:** `app/eqms/__init__.py`

**Problem:** The `load_current_user` before_request hook runs on ALL requests, including static files (`/static/design-system.css`). This causes unnecessary database queries and contributes to the SSL error cascade.

**Evidence from logs:**
```
Exception on /static/design-system.css [GET]
... SSL SYSCALL error: EOF detected
```

**Fix - Skip auth for static files:**

```python
# In app/eqms/auth.py
def load_current_user() -> None:
    # Skip for static files
    if request.path.startswith('/static/'):
        g.current_user = None
        return
    
    # ... rest of function
```

Or in `app/eqms/__init__.py`:
```python
@app.before_request
def _load_user_wrapper():
    if request.path.startswith('/static/'):
        g.current_user = None
        return
    load_current_user()

# Replace: app.before_request(load_current_user)
# With: _load_user_wrapper registered above
```

---

### ISSUE 7: CSRF Token Checked for Static Files

**Severity:** LOW

**File:** `app/eqms/__init__.py`

**Problem:** `ensure_csrf_token()` runs on every request including static files.

**Fix:**
```python
@app.before_request
def _csrf_guard():
    # Skip for static files and health checks
    if request.path.startswith(('/static/', '/health', '/healthz')):
        return None
    
    ensure_csrf_token()
    session.permanent = True
    # ... rest of function
```

---

### ISSUE 8: Health Endpoints Don't Skip Database

**Severity:** LOW

**File:** The health endpoints are fine (`/healthz` doesn't use DB), but `load_current_user` still runs.

**Fix:** Already covered in Issue 6 - skip auth for health endpoints too:
```python
if request.path.startswith(('/static/', '/health', '/healthz')):
    g.current_user = None
    return
```

---

### ISSUE 9: Error Handler References Non-Existent Route

**Severity:** LOW (already fixed in recent code, verify)

**File:** `app/eqms/__init__.py`

**Check:** The 413 error handler was referencing `admin.admin_index` which doesn't exist. Verify it now uses `admin.index`.

---

### ISSUE 10: WordPress Probe Attempts (Security)

**Severity:** LOW (Informational)

**From logs:**
```
GET /wp-admin/setup-config.php HTTP/1.1" 404
GET /wordpress/wp-admin/setup-config.php HTTP/1.1" 404
```

**Problem:** Automated scanners are probing for WordPress vulnerabilities.

**Recommendation:** Consider adding rate limiting or blocking these common probe patterns at the load balancer level.

---

### ISSUE 11: Missing display_name Migration May Not Have Run

**Severity:** MEDIUM

**From SQL in error:**
```sql
SELECT users.id AS users_id, ... users.display_name AS users_display_name, ...
```

**Observation:** The User model includes `display_name`, suggesting the migration ran. However, verify the migration `k1l2m3n4o5_account_management_fields.py` was applied:

```sql
-- Run in database console
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'display_name';
```

If missing, run: `alembic upgrade head`

---

### ISSUE 12: Concurrent Request Failures Cascade

**Severity:** MEDIUM

**From logs:** Both `/admin/` and `/static/design-system.css` failed at the same timestamp.

**Problem:** When the first request's DB connection fails, subsequent requests on the same worker also fail because they share the corrupted connection pool.

**Fix:** Already addressed by `pool_pre_ping=True` which validates connections before use.

---

## Implementation Order

### Immediate (Deploy ASAP)
1. **Fix #1:** Add `pool_pre_ping=True` to `db.py` - **THIS WILL FIX THE PRODUCTION OUTAGE**
2. **Fix #5:** Add try/except to `load_current_user`
3. **Fix #6:** Skip auth for static files

### Same Deployment (Recommended)
4. **Fix #3:** Add `Storage.delete()` method
5. **Fix #4:** Fix escaped regex in parsers.py

### Next Deployment
6. **Fix #2:** Update scripts to use shared db utils
7. **Fix #7:** Skip CSRF for static files
8. Clean up any other issues

---

## Deployment Checklist

- [ ] Update `app/eqms/db.py` with `pool_pre_ping=True` and other settings
- [ ] Update `app/eqms/auth.py` with try/except and static file skip
- [ ] Update `app/eqms/storage.py` with `delete()` method
- [ ] Fix regex in `app/eqms/modules/shipstation_sync/parsers.py`
- [ ] Run `alembic upgrade head` in production console
- [ ] Deploy new code
- [ ] Verify login works
- [ ] Verify no SSL errors in logs
- [ ] Test admin pages load correctly

---

## Quick Copy-Paste Fix

**Minimum viable fix for `app/eqms/db.py`:**

```python
def init_db(app: Flask) -> None:
    engine = create_engine(
        app.config["DATABASE_URL"],
        future=True,
        pool_pre_ping=True,  # <-- ADD THIS LINE
        pool_recycle=1800,   # <-- ADD THIS LINE
    )
    app.extensions["sqlalchemy_engine"] = engine
    app.extensions["sqlalchemy_sessionmaker"] = sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )
```

**This single change will likely fix the production outage.**

---

## References

- [SQLAlchemy Connection Pool FAQ](https://docs.sqlalchemy.org/en/20/core/pooling.html#dealing-with-disconnects)
- [Gunicorn + PostgreSQL Best Practices](https://docs.gunicorn.org/en/stable/design.html#how-many-workers)
- [psycopg2 SSL Error Discussion](https://github.com/psycopg/psycopg2/issues/930)
