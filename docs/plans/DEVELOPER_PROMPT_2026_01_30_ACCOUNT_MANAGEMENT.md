# Developer Prompt: Account Management & System Review Phase 4
**Date:** 2026-01-30  
**Priority:** High

---

## Executive Summary

This document covers:
1. **New Feature:** Account Management in Admin Tools - Simple, reliable user account creation and management for the admin
2. **10 Additional System Issues** identified during code review

---

## FEATURE: Account Management System

### Requirements

The admin needs a simple, reliable way to:
1. **Create new user accounts** for coworkers (admin enters email + password)
2. **Reset passwords** for existing users (admin enters new password)
3. **Activate/Deactivate** user accounts
4. **View all users** with their roles and status

**Important:** This is admin-only functionality. Users will NOT have self-service password reset or account creation. The admin manually manages all accounts.

---

### Implementation Plan

#### 1. Add Account Management Routes

**File:** `app/eqms/admin.py`

Add the following routes after the existing maintenance routes:

```python
# ============================================================================
# ACCOUNT MANAGEMENT (Admin Only)
# ============================================================================

@bp.get("/accounts")
@require_permission("admin.edit")
def accounts_list():
    """List all user accounts."""
    s = db_session()
    users = s.query(User).order_by(User.email.asc()).all()
    roles = s.query(Role).order_by(Role.name.asc()).all()
    return render_template("admin/accounts/list.html", users=users, roles=roles)


@bp.get("/accounts/new")
@require_permission("admin.edit")
def accounts_new_get():
    """Show create account form."""
    s = db_session()
    roles = s.query(Role).order_by(Role.name.asc()).all()
    return render_template("admin/accounts/new.html", roles=roles)


@bp.post("/accounts/new")
@require_permission("admin.edit")
def accounts_new_post():
    """Create a new user account."""
    from werkzeug.security import generate_password_hash
    from app.eqms.audit import record_event
    
    s = db_session()
    u = _current_user()
    
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    role_ids = request.form.getlist("role_ids")
    
    # Validation
    errors = []
    if not email:
        errors.append("Email is required.")
    elif not _is_valid_email(email):
        errors.append("Invalid email format.")
    else:
        existing = s.query(User).filter(User.email == email).one_or_none()
        if existing:
            errors.append("An account with this email already exists.")
    
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif password != password_confirm:
        errors.append("Passwords do not match.")
    
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("admin.accounts_new_get"))
    
    # Create user
    new_user = User(
        email=email,
        password_hash=generate_password_hash(password),
        is_active=True,
    )
    s.add(new_user)
    s.flush()  # Get the ID
    
    # Assign roles
    if role_ids:
        roles = s.query(Role).filter(Role.id.in_([int(r) for r in role_ids])).all()
        for role in roles:
            if role not in new_user.roles:
                new_user.roles.append(role)
    
    record_event(
        s,
        actor=u,
        action="user.create",
        entity_type="User",
        entity_id=str(new_user.id),
        metadata={"email": email, "roles": [r.key for r in new_user.roles]},
    )
    
    s.commit()
    flash(f"Account created for {email}.", "success")
    return redirect(url_for("admin.accounts_list"))


@bp.get("/accounts/<int:user_id>")
@require_permission("admin.edit")
def accounts_detail(user_id: int):
    """View/edit a user account."""
    s = db_session()
    user = s.get(User, user_id)
    if not user:
        abort(404)
    roles = s.query(Role).order_by(Role.name.asc()).all()
    return render_template("admin/accounts/detail.html", account=user, roles=roles)


@bp.post("/accounts/<int:user_id>/update")
@require_permission("admin.edit")
def accounts_update(user_id: int):
    """Update user account (active status, roles)."""
    from app.eqms.audit import record_event
    
    s = db_session()
    u = _current_user()
    user = s.get(User, user_id)
    if not user:
        abort(404)
    
    # Prevent admin from deactivating themselves
    if user.id == u.id:
        flash("You cannot modify your own account from this page.", "danger")
        return redirect(url_for("admin.accounts_detail", user_id=user_id))
    
    before = {
        "is_active": user.is_active,
        "roles": [r.key for r in user.roles],
    }
    
    # Update active status
    is_active = request.form.get("is_active") == "1"
    user.is_active = is_active
    
    # Update roles
    role_ids = request.form.getlist("role_ids")
    user.roles.clear()
    if role_ids:
        roles = s.query(Role).filter(Role.id.in_([int(r) for r in role_ids])).all()
        for role in roles:
            user.roles.append(role)
    
    after = {
        "is_active": user.is_active,
        "roles": [r.key for r in user.roles],
    }
    
    record_event(
        s,
        actor=u,
        action="user.update",
        entity_type="User",
        entity_id=str(user.id),
        metadata={"before": before, "after": after},
    )
    
    s.commit()
    flash(f"Account updated for {user.email}.", "success")
    return redirect(url_for("admin.accounts_detail", user_id=user_id))


@bp.post("/accounts/<int:user_id>/reset-password")
@require_permission("admin.edit")
def accounts_reset_password(user_id: int):
    """Reset a user's password (admin sets new password)."""
    from werkzeug.security import generate_password_hash
    from app.eqms.audit import record_event
    
    s = db_session()
    u = _current_user()
    user = s.get(User, user_id)
    if not user:
        abort(404)
    
    password = request.form.get("password") or ""
    password_confirm = request.form.get("password_confirm") or ""
    
    # Validation
    errors = []
    if not password:
        errors.append("Password is required.")
    elif len(password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif password != password_confirm:
        errors.append("Passwords do not match.")
    
    if errors:
        for e in errors:
            flash(e, "danger")
        return redirect(url_for("admin.accounts_detail", user_id=user_id))
    
    user.password_hash = generate_password_hash(password)
    
    record_event(
        s,
        actor=u,
        action="user.password_reset",
        entity_type="User",
        entity_id=str(user.id),
        metadata={"target_email": user.email, "reset_by": u.email},
    )
    
    s.commit()
    flash(f"Password reset for {user.email}.", "success")
    return redirect(url_for("admin.accounts_detail", user_id=user_id))


def _is_valid_email(email: str) -> bool:
    """Basic email validation."""
    import re
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))
```

---

#### 2. Create Account Management Templates

**File:** `app/eqms/templates/admin/accounts/list.html`

```html
{% extends "_layout.html" %}
{% block title %}User Accounts{% endblock %}
{% block content %}
  <div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
      <h1 style="margin-top:0;">User Accounts</h1>
      <div style="display:flex; gap:10px;">
        <a class="button" href="{{ url_for('admin.accounts_new_get') }}">+ New Account</a>
        <a class="button button--secondary" href="{{ url_for('admin.diagnostics') }}">← Back to Admin Tools</a>
      </div>
    </div>
  </div>

  <div style="height:14px;"></div>

  <div class="card">
    <table style="width:100%; border-collapse:collapse;">
      <thead>
        <tr>
          <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Email</th>
          <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Status</th>
          <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Roles</th>
          <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Created</th>
          <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for user in users %}
          <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:10px 12px;">
              <a href="{{ url_for('admin.accounts_detail', user_id=user.id) }}" style="font-weight:500;">{{ user.email|e }}</a>
            </td>
            <td style="padding:10px 12px;">
              {% if user.is_active %}
                <span style="color:var(--success); font-weight:600;">Active</span>
              {% else %}
                <span style="color:var(--danger); font-weight:600;">Inactive</span>
              {% endif %}
            </td>
            <td style="padding:10px 12px;">
              {% if user.roles %}
                {% for role in user.roles %}
                  <span style="display:inline-block; background:rgba(102,163,255,0.15); color:var(--primary); padding:2px 8px; border-radius:4px; font-size:12px; margin-right:4px;">{{ role.name|e }}</span>
                {% endfor %}
              {% else %}
                <span class="muted">No roles</span>
              {% endif %}
            </td>
            <td style="padding:10px 12px; color:var(--muted); font-size:13px;">
              {{ user.created_at|dateformat('%Y-%m-%d') }}
            </td>
            <td style="padding:10px 12px; text-align:right;">
              <a class="button button--secondary" style="font-size:12px; padding:4px 10px;" href="{{ url_for('admin.accounts_detail', user_id=user.id) }}">Manage</a>
            </td>
          </tr>
        {% else %}
          <tr>
            <td colspan="5" style="padding:20px; text-align:center;" class="muted">No user accounts found.</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div style="height:14px;"></div>

  <div class="card" style="background:rgba(102,163,255,0.05); border:1px solid rgba(102,163,255,0.2);">
    <h3 style="margin-top:0; color:var(--primary);">Account Management Info</h3>
    <p class="muted" style="margin-bottom:0;">
      As admin, you can create accounts, reset passwords, and activate/deactivate users.
      Users cannot reset their own passwords - contact an administrator for password assistance.
    </p>
  </div>
{% endblock %}
```

---

**File:** `app/eqms/templates/admin/accounts/new.html`

```html
{% extends "_layout.html" %}
{% block title %}New Account{% endblock %}
{% block content %}
  <div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
      <h1 style="margin-top:0;">Create New Account</h1>
      <a class="button button--secondary" href="{{ url_for('admin.accounts_list') }}">← Back to Accounts</a>
    </div>
  </div>

  <div style="height:14px;"></div>

  <div class="card">
    <form class="form" method="post" action="{{ url_for('admin.accounts_new_post') }}" style="max-width:500px;">
      <div>
        <div class="label">Email *</div>
        <input type="email" name="email" required placeholder="user@company.com" autocomplete="off" />
      </div>
      
      <div>
        <div class="label">Password *</div>
        <input type="password" name="password" required minlength="8" placeholder="Minimum 8 characters" autocomplete="new-password" />
        <div class="muted" style="font-size:11px; margin-top:4px;">Must be at least 8 characters</div>
      </div>
      
      <div>
        <div class="label">Confirm Password *</div>
        <input type="password" name="password_confirm" required minlength="8" placeholder="Re-enter password" autocomplete="new-password" />
      </div>
      
      <div style="margin-top:16px;">
        <div class="label">Roles</div>
        <div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
          {% for role in roles %}
            <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
              <input type="checkbox" name="role_ids" value="{{ role.id }}" {% if role.key == 'admin' %}checked{% endif %} />
              <span>{{ role.name|e }}</span>
              <span class="muted" style="font-size:12px;">({{ role.key }})</span>
            </label>
          {% endfor %}
        </div>
      </div>
      
      <div style="display:flex; gap:10px; margin-top:20px;">
        <button class="button" type="submit">Create Account</button>
        <a class="button button--secondary" href="{{ url_for('admin.accounts_list') }}">Cancel</a>
      </div>
    </form>
  </div>
{% endblock %}
```

---

**File:** `app/eqms/templates/admin/accounts/detail.html`

```html
{% extends "_layout.html" %}
{% block title %}Account: {{ account.email }}{% endblock %}
{% block content %}
  <div class="card">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
      <h1 style="margin-top:0;">Account: {{ account.email|e }}</h1>
      <a class="button button--secondary" href="{{ url_for('admin.accounts_list') }}">← Back to Accounts</a>
    </div>
  </div>

  <div style="height:14px;"></div>

  <div class="grid" style="grid-template-columns: 1fr 1fr; gap:14px;">
    <!-- Account Details -->
    <div class="card">
      <h2 style="margin-top:0;">Account Details</h2>
      <form class="form" method="post" action="{{ url_for('admin.accounts_update', user_id=account.id) }}">
        <dl class="dl">
          <dt>Email</dt>
          <dd>{{ account.email|e }}</dd>
          <dt>Created</dt>
          <dd>{{ account.created_at|dateformat('%Y-%m-%d %H:%M') }}</dd>
        </dl>
        
        <div style="margin-top:16px;">
          <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
            <input type="checkbox" name="is_active" value="1" {% if account.is_active %}checked{% endif %} />
            <span style="font-weight:500;">Account Active</span>
          </label>
          <div class="muted" style="font-size:11px; margin-top:4px;">Inactive accounts cannot log in</div>
        </div>
        
        <div style="margin-top:16px;">
          <div class="label">Roles</div>
          <div style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
            {% for role in roles %}
              <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
                <input type="checkbox" name="role_ids" value="{{ role.id }}" {% if role in account.roles %}checked{% endif %} />
                <span>{{ role.name|e }}</span>
                <span class="muted" style="font-size:12px;">({{ role.key }})</span>
              </label>
            {% endfor %}
          </div>
        </div>
        
        <div style="margin-top:20px;">
          <button class="button" type="submit">Save Changes</button>
        </div>
      </form>
    </div>
    
    <!-- Password Reset -->
    <div class="card">
      <h2 style="margin-top:0;">Reset Password</h2>
      <p class="muted" style="margin-bottom:16px;">Set a new password for this user. They will need to use this password to log in.</p>
      
      <form class="form" method="post" action="{{ url_for('admin.accounts_reset_password', user_id=account.id) }}">
        <div>
          <div class="label">New Password *</div>
          <input type="password" name="password" required minlength="8" placeholder="Minimum 8 characters" autocomplete="new-password" />
        </div>
        
        <div>
          <div class="label">Confirm Password *</div>
          <input type="password" name="password_confirm" required minlength="8" placeholder="Re-enter password" autocomplete="new-password" />
        </div>
        
        <div style="margin-top:16px;">
          <button class="button button--secondary" type="submit" style="background:rgba(220,53,69,0.15); color:var(--danger); border-color:var(--danger);">Reset Password</button>
        </div>
      </form>
    </div>
  </div>

  <div style="height:14px;"></div>

  <!-- Current Permissions -->
  <div class="card">
    <h2 style="margin-top:0;">Current Permissions</h2>
    {% set user_perms = [] %}
    {% for role in account.roles %}
      {% for perm in role.permissions %}
        {% if perm.key not in user_perms %}
          {% set _ = user_perms.append(perm.key) %}
        {% endif %}
      {% endfor %}
    {% endfor %}
    
    {% if user_perms %}
      <div style="display:flex; flex-wrap:wrap; gap:6px;">
        {% for perm in user_perms|sort %}
          <span style="display:inline-block; background:rgba(255,255,255,0.05); padding:4px 10px; border-radius:4px; font-size:12px; font-family:monospace;">{{ perm }}</span>
        {% endfor %}
      </div>
    {% else %}
      <p class="muted">No permissions (no roles assigned).</p>
    {% endif %}
  </div>
{% endblock %}
```

---

#### 3. Update Admin Tools / Diagnostics Page

**File:** `app/eqms/templates/admin/diagnostics.html`

Add a link to Account Management in the "Quick Links" section (around line 144):

```html
<div class="card">
  <h2 style="margin-top:0;">Quick Links</h2>
  <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:12px;">
    <a class="button" href="{{ url_for('admin.accounts_list') }}">User Accounts</a>
    <a class="button button--secondary" href="{{ url_for('admin.audit_list') }}">Audit Trail</a>
    <a class="button button--secondary" href="{{ url_for('admin.debug_permissions') }}">Debug Permissions</a>
    <a class="button button--secondary" href="{{ url_for('admin.diagnostics_storage') }}" target="_blank">Storage Diagnostics (JSON)</a>
    <a class="button button--secondary" href="/health" target="_blank">/health (JSON)</a>
    <a class="button button--secondary" href="/healthz" target="_blank">/healthz (Text)</a>
  </div>
</div>
```

---

#### 4. Required Imports

Add to `app/eqms/admin.py` at the top:

```python
from app.eqms.models import AuditEvent, User, Role
```

---

### Testing the Account Management Feature

1. Navigate to `/admin/diagnostics` → Click "User Accounts"
2. Click "+ New Account"
3. Enter email, password (8+ chars), confirm password
4. Select role(s) - default should be "Administrator"
5. Submit → Should redirect to account list with success message
6. Click "Manage" on the new account
7. Test password reset
8. Test deactivating the account
9. Verify deactivated user cannot log in

---

## System Review: 10 Additional Issues

### ISSUE 1: Storage.delete() Method Missing in LocalStorage

**Severity:** HIGH

**File:** `app/eqms/storage.py`

**Problem:** The `LocalStorage` class doesn't implement a `delete()` method, but the code attempts to call `storage.delete()` in equipment and supplier admin modules.

**Current Code:**
```python
class LocalStorage(Storage):
    # Missing: delete() method
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

### ISSUE 2: Schema Health Check Runs on Every Request

**Severity:** MEDIUM

**File:** `app/eqms/__init__.py` (lines 123-186)

**Problem:** The schema health check runs on EVERY request, even after it's already passed. This adds unnecessary overhead.

**Current Behavior:**
```python
@app.before_request
def _schema_health_guardrail():
    if not app.config.get("_schema_health_checked"):
        # ... run check ...
```

The check only runs once, but the `before_request` decorator still executes the function for every request.

**Fix - Move check to app initialization:**
```python
# In create_app(), after init_db(app):
_run_schema_health_check(app)

# Remove the @app.before_request decorator from _schema_health_guardrail
# Or change to:
@app.before_request
def _schema_health_guardrail():
    if app.config.get("_schema_health_ok"):
        return None
    # Only show error if check failed
    if request.path.startswith("/admin") and getattr(g, "current_user", None):
        return render_template("errors/schema_out_of_date.html", 
                              missing=app.config.get("_schema_health_missing") or []), 500
    return None
```

---

### ISSUE 3: No Session Timeout / Expiration

**Severity:** MEDIUM (Security)

**File:** `app/eqms/auth.py`, `app/eqms/__init__.py`

**Problem:** User sessions never expire. Once logged in, users stay logged in indefinitely (until browser cookies are cleared).

**Fix - Add session lifetime:**

In `app/eqms/__init__.py`, add to `create_app()`:

```python
from datetime import timedelta

# Session configuration
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)  # 8-hour session
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

@app.before_request
def _make_session_permanent():
    session.permanent = True
```

---

### ISSUE 4: No Rate Limiting on Login Endpoint

**Severity:** MEDIUM (Security)

**File:** `app/eqms/auth.py`

**Problem:** The login endpoint has no rate limiting, making it vulnerable to brute-force attacks.

**Fix - Add simple rate limiting:**

```python
# In app/eqms/auth.py

from datetime import datetime, timedelta
from collections import defaultdict

# Simple in-memory rate limiter (use Redis in production for multi-instance)
_login_attempts: dict[str, list[datetime]] = defaultdict(list)
_LOGIN_RATE_LIMIT = 5  # Max attempts
_LOGIN_RATE_WINDOW = 300  # 5 minutes

def _check_rate_limit(ip: str) -> bool:
    """Returns True if rate limited, False if OK."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=_LOGIN_RATE_WINDOW)
    
    # Clean old entries
    _login_attempts[ip] = [t for t in _login_attempts[ip] if t > cutoff]
    
    # Check limit
    if len(_login_attempts[ip]) >= _LOGIN_RATE_LIMIT:
        return True
    
    return False

def _record_attempt(ip: str) -> None:
    _login_attempts[ip].append(datetime.utcnow())


@bp.post("/login")
def login_post():
    ip = request.remote_addr or "unknown"
    
    if _check_rate_limit(ip):
        flash("Too many login attempts. Please wait 5 minutes.", "danger")
        return redirect(url_for("auth.login_get"))
    
    _record_attempt(ip)
    # ... rest of login logic ...
```

---

### ISSUE 5: Audit Events Don't Capture Client IP

**Severity:** LOW (Security Enhancement)

**File:** `app/eqms/audit.py`, `app/eqms/models.py`

**Problem:** Audit events don't record the client IP address, making security investigations harder.

**Fix:**

1. Add column to AuditEvent model:
```python
# In app/eqms/models.py
class AuditEvent(Base):
    # ... existing fields ...
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max length
```

2. Update record_event:
```python
# In app/eqms/audit.py
def record_event(s, *, actor, action, entity_type=None, entity_id=None, reason=None, metadata=None):
    from flask import request, g
    
    client_ip = request.remote_addr if request else None
    
    event = AuditEvent(
        request_id=getattr(g, "request_id", None),
        actor_user_id=actor.id if actor else None,
        actor_user_email=actor.email if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        reason=reason,
        metadata_json=json.dumps(metadata) if metadata else None,
        client_ip=client_ip,  # NEW
    )
    s.add(event)
```

3. Create migration for new column.

---

### ISSUE 6: User Model Missing Display Name Field

**Severity:** LOW (Enhancement)

**File:** `app/eqms/models.py`

**Problem:** Users only have email as identifier. A display name would improve UX.

**Fix:**
```python
class User(Base):
    # ... existing fields ...
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
```

Update templates to show `display_name or email` where user names are displayed.

---

### ISSUE 7: Multiple s.commit() Patterns Without Transaction Guards

**Severity:** MEDIUM (Reliability)

**File:** Multiple files (70+ s.commit() calls)

**Problem:** Many routes call `s.commit()` directly without proper error handling, which can leave the database in an inconsistent state.

**Pattern to avoid:**
```python
# Do something
s.commit()
# Do another thing
s.commit()  # If this fails, first change is already committed
```

**Fix - Use context manager pattern:**
```python
from contextlib import contextmanager

@contextmanager
def atomic(session):
    """Wrap operations in a savepoint for atomicity."""
    try:
        yield
    except Exception:
        session.rollback()
        raise
```

Or consolidate to single commit at end of request handler.

---

### ISSUE 8: Missing Database Indexes on Frequently Queried Columns

**Severity:** MEDIUM (Performance)

**Problem:** Several frequently-queried columns lack indexes:
- `distribution_log_entries.order_number`
- `distribution_log_entries.customer_id`
- `customers.company_key`
- `sales_orders.order_number`

**Fix - Add indexes in migration:**
```python
from alembic import op

def upgrade():
    op.create_index('ix_distribution_log_entries_order_number', 
                    'distribution_log_entries', ['order_number'])
    op.create_index('ix_distribution_log_entries_customer_id', 
                    'distribution_log_entries', ['customer_id'])
    op.create_index('ix_sales_orders_order_number', 
                    'sales_orders', ['order_number'])
```

---

### ISSUE 9: Rep Model Duplicates User Address Fields

**Severity:** LOW (Data Model Inconsistency)

**File:** `app/eqms/modules/customer_profiles/models.py`

**Problem:** The `Rep` model has its own address fields, but reps are often users who also have address fields on the User model. This creates data duplication.

**Observation:** The `User` model has `address1, address2, city, state, zip` and the "My Account" page allows users to update these fields. If reps are users, their Rep record duplicates this data.

**Recommendation:** Consider whether Rep should be a separate entity or if User should have a `is_rep` flag. For now, document the relationship clearly.

---

### ISSUE 10: Error Handler for 413 Redirects Incorrectly

**Severity:** LOW

**File:** `app/eqms/__init__.py` (lines 210-215)

**Problem:** The 413 error handler uses `request.referrer`, which may be None or an external URL, and redirects to `admin.admin_index` which doesn't exist.

**Current:**
```python
@app.errorhandler(413)
def _err_413(e):
    from flask import flash, redirect, url_for
    flash("File too large. Maximum size is 25MB.", "danger")
    return redirect(request.referrer or url_for("admin.admin_index")), 302
```

**Fix:**
```python
@app.errorhandler(413)
def _err_413(e):
    from flask import flash, redirect, url_for
    flash("File too large. Maximum size is 50MB.", "danger")
    referrer = request.referrer
    # Only use referrer if it's a local URL
    if referrer and referrer.startswith(request.host_url):
        return redirect(referrer), 302
    return redirect(url_for("admin.index")), 302  # Fixed: admin.index not admin.admin_index
```

---

## Implementation Order

### Phase 1: Account Management (Critical Path)
1. Add routes to `admin.py`
2. Create template files in `templates/admin/accounts/`
3. Update diagnostics.html with link to accounts
4. Test full workflow

### Phase 2: Security Enhancements
5. Add session timeout configuration
6. Implement login rate limiting
7. Add client IP to audit events

### Phase 3: Reliability & Performance
8. Add Storage.delete() method
9. Optimize schema health check
10. Fix 413 error handler
11. Add database indexes (migration)

### Phase 4: Enhancements (Lower Priority)
12. Add display_name to User model
13. Document Rep/User relationship

---

## Testing Checklist

- [ ] Create new user account via UI
- [ ] Verify new user can log in
- [ ] Reset user password via UI
- [ ] Verify password reset works
- [ ] Deactivate user account
- [ ] Verify deactivated user cannot log in
- [ ] Reactivate user account
- [ ] Verify audit events are created for all account actions
- [ ] Test session timeout (set to 1 minute temporarily)
- [ ] Test login rate limiting (attempt 6+ rapid logins)

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `app/eqms/admin.py` | Add account management routes |
| `app/eqms/storage.py` | Add delete() method |
| `app/eqms/__init__.py` | Add session config, fix error handlers |
| `app/eqms/auth.py` | Add rate limiting |
| `app/eqms/audit.py` | Add client_ip capture |
| `app/eqms/models.py` | Add client_ip to AuditEvent, display_name to User |
| `app/eqms/templates/admin/accounts/list.html` | NEW |
| `app/eqms/templates/admin/accounts/new.html` | NEW |
| `app/eqms/templates/admin/accounts/detail.html` | NEW |
| `app/eqms/templates/admin/diagnostics.html` | Add link to accounts |
| `migrations/versions/xxx_add_account_fields.py` | NEW migration |

---

## Notes

- Password requirements: Minimum 8 characters (can be enhanced later)
- All account actions are audited
- Admin cannot deactivate their own account (safety check)
- Consider adding email notifications for password resets in future iteration
