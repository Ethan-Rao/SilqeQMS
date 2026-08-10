# DEVELOPER AGENT PROMPT: Critical Bug Fixes & System Enhancement
**Date:** February 8, 2026  
**Priority:** CRITICAL  
**Status:** Deployment successful but multiple pages broken

---

## CRITICAL ISSUE #1: CSRF Token Template Error

### Error Message
```
TypeError: 'str' object is not callable
File: admin/reset_data.html line 35
{{ csrf_token() }}
```

### Root Cause
The application injects `csrf_token` as a **string** via context processor:

```python
# In app/eqms/__init__.py line 39-40
@app.context_processor
def _inject_csrf() -> dict:
    return {"csrf_token": ensure_csrf_token()}  # Returns STRING, not function
```

But many templates incorrectly call it as a function: `{{ csrf_token() }}`

### Fix Required
Change `{{ csrf_token() }}` to `{{ csrf_token }}` (remove parentheses) in ALL these files:

| File | Line | Current | Fix To |
|------|------|---------|--------|
| `app/eqms/templates/admin/reset_data.html` | 35 | `{{ csrf_token() }}` | `{{ csrf_token }}` |
| `app/eqms/templates/admin/equipment/bulk_import.html` | 19 | `{{ csrf_token() }}` | `{{ csrf_token }}` |
| `app/eqms/templates/admin/supplies/new.html` | 7 | `{{ csrf_token() }}` | `{{ csrf_token }}` |
| `app/eqms/templates/admin/supplies/edit.html` | 7 | `{{ csrf_token() }}` | `{{ csrf_token }}` |
| `app/eqms/templates/admin/distribution_log/edit.html` | 175 | `{{ csrf_token() }}` | `{{ csrf_token }}` |
| `app/eqms/templates/admin/nre_projects/detail.html` | 54 | `{{ csrf_token() }}` | `{{ csrf_token }}` |
| `app/eqms/templates/admin/nre_projects/detail.html` | 81 | `{{ csrf_token() }}` | `{{ csrf_token }}` |
| `app/eqms/templates/admin/nre_projects/detail.html` | 102 | `{{ csrf_token() }}` | `{{ csrf_token }}` |

### Verification After Fix
Test these URLs work without 500 error:
- [ ] `/admin/reset-data`
- [ ] `/admin/equipment/bulk-import`
- [ ] `/admin/supplies/new`
- [ ] `/admin/supplies/1/edit` (any supply)
- [ ] `/admin/distribution-log/1/edit` (any distribution)
- [ ] `/admin/nre-projects/1` (any NRE customer)

---

## ISSUE #2: Admin Dashboard Cards - Add New Modules

### Current Admin Cards
```
Document Control & QMS | Distribution Log | Tracing Reports
Customers | Sales Dashboard | Sales Orders
Equipment & Supplies | Manufacturing | Suppliers
Supplies | Admin Tools | NRE Projects | My Account
```

### Required New Cards
Add these new cards to the admin dashboard:

1. **Employee Training** - Stub module for future training records
2. **CAPAs** - Corrective and Preventive Actions module
3. **Quality Management Documents** - Core QMS documents

### Update Admin Index Template

**File:** `app/eqms/templates/admin/index.html`

Add these cards after the existing ones:

```html
{% if has_perm("admin.view") %}
  <a class="card card--link" href="{{ url_for('admin.employee_training') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
    <h2 style="margin: 0;">Employee Training</h2>
  </a>
{% endif %}
{% if has_perm("admin.view") %}
  <a class="card card--link" href="{{ url_for('admin.capas') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
    <h2 style="margin: 0;">CAPAs</h2>
  </a>
{% endif %}
{% if has_perm("docs.view") %}
  <a class="card card--link" href="{{ url_for('admin.qms_documents') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
    <h2 style="margin: 0;">Quality Management Documents</h2>
  </a>
{% endif %}
```

### Add Stub Routes in admin.py

**File:** `app/eqms/admin.py`

Add these placeholder routes:

```python
@bp.get("/employee-training")
@require_permission("admin.view")
def employee_training():
    """Employee Training module - placeholder."""
    return render_template("admin/employee_training.html")


@bp.get("/capas")
@require_permission("admin.view")
def capas():
    """CAPAs module - placeholder."""
    return render_template("admin/capas.html")


@bp.get("/qms-documents")
@require_permission("docs.view")
def qms_documents():
    """Quality Management Documents - placeholder."""
    return render_template("admin/qms_documents.html")
```

### Create Placeholder Templates

**File:** `app/eqms/templates/admin/employee_training.html`
```html
{% extends "_layout.html" %}
{% block title %}Employee Training{% endblock %}
{% block content %}
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
    <div>
      <h1 style="margin-top:0;">Employee Training</h1>
      <p class="muted">Manage employee training records, certifications, and competency tracking.</p>
    </div>
    <a class="button button--secondary" href="{{ url_for('admin.index') }}">← Back to Admin</a>
  </div>
</div>
<div style="height:14px;"></div>
<div class="card">
  <div style="text-align:center; padding:40px;">
    <h2 style="margin:0 0 12px;">Coming Soon</h2>
    <p class="muted">This module is under development.</p>
    <p class="muted">Features will include:</p>
    <ul style="display:inline-block; text-align:left; margin-top:12px;">
      <li>Training records management</li>
      <li>Certification tracking</li>
      <li>Due date reminders</li>
      <li>Training matrix</li>
    </ul>
  </div>
</div>
{% endblock %}
```

**File:** `app/eqms/templates/admin/capas.html`
```html
{% extends "_layout.html" %}
{% block title %}CAPAs{% endblock %}
{% block content %}
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
    <div>
      <h1 style="margin-top:0;">CAPAs</h1>
      <p class="muted">Corrective and Preventive Actions management.</p>
    </div>
    <a class="button button--secondary" href="{{ url_for('admin.index') }}">← Back to Admin</a>
  </div>
</div>
<div style="height:14px;"></div>
<div class="card">
  <div style="text-align:center; padding:40px;">
    <h2 style="margin:0 0 12px;">Coming Soon</h2>
    <p class="muted">This module is under development.</p>
    <p class="muted">Features will include:</p>
    <ul style="display:inline-block; text-align:left; margin-top:12px;">
      <li>CAPA initiation and tracking</li>
      <li>Root cause analysis</li>
      <li>Effectiveness checks</li>
      <li>Compliance reporting</li>
    </ul>
  </div>
</div>
{% endblock %}
```

**File:** `app/eqms/templates/admin/qms_documents.html`
```html
{% extends "_layout.html" %}
{% block title %}Quality Management Documents{% endblock %}
{% block content %}
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
    <div>
      <h1 style="margin-top:0;">Quality Management Documents</h1>
      <p class="muted">Core QMS policies, procedures, and work instructions.</p>
    </div>
    <a class="button button--secondary" href="{{ url_for('admin.index') }}">← Back to Admin</a>
  </div>
</div>
<div style="height:14px;"></div>
<div class="card">
  <div style="text-align:center; padding:40px;">
    <h2 style="margin:0 0 12px;">Coming Soon</h2>
    <p class="muted">This module is under development.</p>
    <p class="muted">Document types to be managed:</p>
    <ul style="display:inline-block; text-align:left; margin-top:12px;">
      <li>Quality Manual</li>
      <li>Standard Operating Procedures (SOPs)</li>
      <li>Work Instructions</li>
      <li>Forms and Templates</li>
      <li>Policies</li>
    </ul>
  </div>
</div>
{% endblock %}
```

---

## ISSUE #3: Menu Alignment with Admin Dashboard

### Current Problem
The top navigation menu doesn't match the admin dashboard cards.

### Required Changes

**File:** `app/eqms/templates/_layout.html`

Update the navigation to align with admin dashboard. The menu should include primary categories only:

```html
<nav class="topbar__nav">
  <a href="{{ url_for('routes.index') }}">Home</a>
  {% if has_perm("admin.view") %}
    <a href="{{ url_for('admin.index') }}">Admin</a>
  {% endif %}
  {% if g.current_user %}
    {# Core Distribution & Traceability #}
    {% if has_perm("distribution_log.view") %}
      <a href="{{ url_for('rep_traceability.distribution_log_list') }}">Distribution Log</a>
    {% endif %}
    {% if has_perm("customers.view") %}
      <a href="{{ url_for('customer_profiles.customers_list') }}">Customers</a>
    {% endif %}
    {% if has_perm("sales_dashboard.view") %}
      <a href="{{ url_for('rep_traceability.sales_dashboard') }}">Sales Dashboard</a>
    {% endif %}
    {# Equipment & Manufacturing #}
    {% if has_perm("equipment.view") %}
      <a href="{{ url_for('equipment.equipment_list') }}">Equipment</a>
    {% endif %}
    {% if has_perm("equipment.view") %}
      <a href="{{ url_for('supplies.supplies_list') }}">Supplies</a>
    {% endif %}
    {% if has_perm("suppliers.view") %}
      <a href="{{ url_for('suppliers.suppliers_list') }}">Suppliers</a>
    {% endif %}
    {% if has_perm("manufacturing.view") %}
      <a href="{{ url_for('manufacturing.manufacturing_index') }}">Manufacturing</a>
    {% endif %}
  {% endif %}
  {% if g.current_user %}
    <span class="muted">{{ g.current_user.email }}</span>
    <a href="{{ url_for('auth.logout') }}">Logout</a>
  {% else %}
    <a href="{{ url_for('auth.login_get') }}">Login</a>
  {% endif %}
</nav>
```

**Note:** Remove these from top menu (they should be accessible via Admin dashboard only):
- Sales Orders (under Admin Tools)
- Tracing Reports (under Admin Tools)
- Audit (under Admin Tools)
- ShipStation (under Admin Tools)

---

## ISSUE #4: Admin Tools (Diagnostics Page) Enhancement

### Current State
The diagnostics page at `/admin/diagnostics` exists and shows system status. It has a "Quick Links" section that needs Tracing Reports and Sales Orders links.

### Required Change
**File:** `app/eqms/templates/admin/diagnostics.html`

Find the "Quick Links" section (around line 147) and add Tracing Reports and Sales Orders links:

**Current (line 145-155):**
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

**Replace with:**
```html
<div class="card">
  <h2 style="margin-top:0;">Quick Links</h2>
  <div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:12px;">
    <a class="button" href="{{ url_for('admin.accounts_list') }}">User Accounts</a>
    <a class="button button--secondary" href="{{ url_for('admin.audit_list') }}">Audit Trail</a>
    <a class="button button--secondary" href="{{ url_for('rep_traceability.tracing_list') }}">Tracing Reports</a>
    <a class="button button--secondary" href="{{ url_for('rep_traceability.sales_orders_list') }}">Sales Orders</a>
    <a class="button button--secondary" href="{{ url_for('rep_traceability.sales_orders_import_get') }}">Import PDFs</a>
    <a class="button button--secondary" href="{{ url_for('equipment.equipment_bulk_import_get') }}">Equipment Import</a>
    <a class="button button--secondary" href="{{ url_for('admin.debug_permissions') }}">Debug Permissions</a>
    <a class="button button--secondary" href="{{ url_for('admin.diagnostics_storage') }}" target="_blank">Storage (JSON)</a>
  </div>
</div>
```

---

## ISSUE #5: Legacy Code Cleanup

### Check and Remove
Search for and remove any of these legacy patterns:

1. **Unused routes** - Routes that aren't linked from any template
2. **Commented-out code blocks** - Large sections of commented code
3. **Debug print statements** - Remove any `print()` calls meant for debugging
4. **TODO comments** - Document or remove TODO items

### Search Commands
```bash
# Find print statements (potential debug code)
grep -r "print(" app/eqms --include="*.py"

# Find TODO comments
grep -r "TODO\|FIXME\|XXX\|HACK" app/eqms --include="*.py"

# Find unused imports
# (use a tool like autoflake or manually review)
```

### Known Legacy Code to Check
1. Check if `document_control` module is fully implemented or just a stub
2. Check if there are any duplicate route definitions
3. Check for any routes that redirect to non-existent pages

---

## ISSUE #6: Template Reference Check in reset_data.html

### Additional Fix Needed
Line 87 in `reset_data.html` references a route that may not exist:

```html
<li><strong>Equipment & Supplies:</strong> <a href="{{ url_for('equipment.equipment_bulk_import_get') }}">Run Bulk Import</a></li>
```

Verify that `equipment.equipment_bulk_import_get` exists. If the route is named differently (e.g., `equipment_bulk_import`), update the template.

**Check in** `app/eqms/modules/equipment/admin.py`:
```python
@bp.get("/equipment/bulk-import")
def equipment_bulk_import_get():  # <- This is the function name
```

If the function is `equipment_bulk_import_get`, the url_for is correct.

---

## ISSUE #7: Comprehensive Template Audit

### Purpose
Ensure no other templates have the `csrf_token()` bug or other broken patterns.

### Search Commands
Run these searches to find any other issues:

```bash
# Find any remaining csrf_token() calls (should be 0 after fixes)
grep -r "csrf_token()" app/eqms/templates --include="*.html"

# Find templates that might have typos or broken url_for calls
# (manually review results)
grep -r "url_for(" app/eqms/templates --include="*.html" | head -50
```

### Check These Patterns Are Correct
1. All templates use `{{ csrf_token }}` (no parentheses)
2. All url_for references point to existing routes
3. All templates extend `_layout.html` correctly

---

## TESTING CHECKLIST

After all fixes, test these pages:

### Critical (Must Work)
- [ ] `/admin/reset-data` - No 500 error, shows counts
- [ ] `/admin/equipment/bulk-import` - No 500 error, shows upload form
- [ ] `/admin/supplies/new` - No 500 error, shows create form
- [ ] `/admin/supplies/1/edit` - No 500 error (test with any supply)
- [ ] `/admin/distribution-log/1/edit` - No 500 error (test with any entry)
- [ ] `/admin/nre-projects/1` - No 500 error, can upload PDF

### New Pages (Should Display Placeholder)
- [ ] `/admin/employee-training` - Shows "Coming Soon" placeholder
- [ ] `/admin/capas` - Shows "Coming Soon" placeholder
- [ ] `/admin/qms-documents` - Shows "Coming Soon" placeholder

### Admin Dashboard
- [ ] `/admin/` - Shows all cards including new ones
- [ ] All card links work (no 404s)

### Navigation
- [ ] Top menu items are correctly scoped
- [ ] Menu matches primary admin dashboard categories

---

## COMMIT INSTRUCTIONS

After implementing all fixes:

```bash
git add -A
git status  # Verify changes

git commit -m "Fix critical CSRF token bug and enhance admin dashboard

Critical Fixes:
- Fix csrf_token() -> csrf_token in 8 templates (TypeError bug)
- Templates: reset_data, bulk_import, supplies/new, supplies/edit,
  distribution_log/edit, nre_projects/detail

New Features:
- Add Employee Training placeholder module
- Add CAPAs placeholder module
- Add Quality Management Documents placeholder module
- Reorganize Admin Tools with links to Tracing Reports, Sales Orders

UI Improvements:
- Update top navigation to match admin dashboard
- Clean up menu structure
"

git push origin main
```

---

## FILE CHANGES SUMMARY

| File | Action |
|------|--------|
| `templates/admin/reset_data.html` | Fix csrf_token |
| `templates/admin/equipment/bulk_import.html` | Fix csrf_token |
| `templates/admin/supplies/new.html` | Fix csrf_token |
| `templates/admin/supplies/edit.html` | Fix csrf_token |
| `templates/admin/distribution_log/edit.html` | Fix csrf_token |
| `templates/admin/nre_projects/detail.html` | Fix csrf_token (3 places) |
| `templates/admin/index.html` | Add new module cards |
| `templates/admin/employee_training.html` | Create new |
| `templates/admin/capas.html` | Create new |
| `templates/admin/qms_documents.html` | Create new |
| `templates/admin/diagnostics.html` | Update with Admin Tools links |
| `templates/_layout.html` | Update navigation menu |
| `admin.py` | Add new stub routes |

---

**END OF DEVELOPER PROMPT**
