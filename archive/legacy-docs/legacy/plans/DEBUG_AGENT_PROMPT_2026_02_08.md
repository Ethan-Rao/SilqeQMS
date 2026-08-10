# DEBUG AGENT PROMPT: Comprehensive System Audit & Reorganization
**Date:** February 8, 2026  
**Priority:** HIGH  
**Scope:** Full system debug, admin reorganization, legacy cleanup, upload compatibility

---

## MISSION STATEMENT

Perform a comprehensive audit of the SilqQMS system to:
1. Fix all known bugs (especially CSRF token issue)
2. Reorganize admin dashboard into 3 logical columns
3. Verify compatibility with all data upload sources
4. Delete unnecessary legacy code
5. Add missing module stubs

---

## PART 1: CRITICAL BUG FIXES

### Issue 1.1: CSRF Token TypeError

**Error:** `TypeError: 'str' object is not callable` on multiple pages

**Root Cause:** Templates use `{{ csrf_token() }}` but `csrf_token` is injected as a string.

**Fix:** Change `{{ csrf_token() }}` → `{{ csrf_token }}` in these files:

| File | Lines |
|------|-------|
| `app/eqms/templates/admin/reset_data.html` | 35 |
| `app/eqms/templates/admin/equipment/bulk_import.html` | 19 |
| `app/eqms/templates/admin/supplies/new.html` | 7 |
| `app/eqms/templates/admin/supplies/edit.html` | 7 |
| `app/eqms/templates/admin/distribution_log/edit.html` | 175 |
| `app/eqms/templates/admin/nre_projects/detail.html` | 54, 81, 102 |

**Verification:**
```bash
# After fix, this should return 0 results:
grep -r "csrf_token()" app/eqms/templates --include="*.html"
```

---

## PART 2: ADMIN DASHBOARD REORGANIZATION

### Current State
Cards are listed in a single flat grid with no logical grouping.

### Target Organization
Reorganize into **3 columns** with clear categories:

| Quality Management | Silq Operations | External Relationships |
|-------------------|-----------------|----------------------|
| Quality Management Documents | Manufacturing | Distribution Log |
| Document Control (DCOs) | Equipment | Sales Dashboard |
| Employee Training | Supplies | Customers |
| Admin Tools | NCRs | Suppliers |
| My Account | CAPAs | NRE Projects |

### Implementation

**File:** `app/eqms/templates/admin/index.html`

Replace entire content with:

```html
{% extends "_layout.html" %}
{% block title %}Admin{% endblock %}
{% block content %}
<div style="max-width: 1400px; margin: 0 auto;">
  <div class="card" style="margin-bottom: 20px;">
    <h1 style="margin: 0;">Admin Dashboard</h1>
    <p class="muted" style="margin-top: 8px;">Silq eQMS Administration Center</p>
  </div>

  <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
    
    {# Column 1: Quality Management #}
    <div>
      <h2 style="font-size: 14px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; padding-left: 4px;">
        Quality Management
      </h2>
      <div style="display: flex; flex-direction: column; gap: 12px;">
        {% if has_perm("docs.view") %}
        <a class="card card--link" href="{{ url_for('admin.qms_documents') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Quality Management Documents</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">QMS policies, procedures, and work instructions</p>
        </a>
        {% endif %}
        {% if has_perm("docs.view") %}
        <a class="card card--link" href="{{ url_for('doc_control.list_documents') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Document Control (DCOs)</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Document change orders and version control</p>
        </a>
        {% endif %}
        {% if has_perm("admin.view") %}
        <a class="card card--link" href="{{ url_for('admin.employee_training') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Employee Training</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Training records and certifications</p>
        </a>
        {% endif %}
        {% if has_perm("admin.view") %}
        <a class="card card--link" href="{{ url_for('admin.diagnostics') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Admin Tools</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">System diagnostics, data reset, accounts</p>
        </a>
        {% endif %}
        <a class="card card--link" href="{{ url_for('admin.me') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">My Account</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Profile settings and preferences</p>
        </a>
      </div>
    </div>

    {# Column 2: Silq Operations #}
    <div>
      <h2 style="font-size: 14px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; padding-left: 4px;">
        Silq Operations
      </h2>
      <div style="display: flex; flex-direction: column; gap: 12px;">
        {% if has_perm("manufacturing.view") %}
        <a class="card card--link" href="{{ url_for('manufacturing.manufacturing_index') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Manufacturing</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Lot tracking and production records</p>
        </a>
        {% endif %}
        {% if has_perm("equipment.view") %}
        <a class="card card--link" href="{{ url_for('equipment.equipment_list') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Equipment</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Equipment inventory and calibration</p>
        </a>
        {% endif %}
        {% if has_perm("equipment.view") %}
        <a class="card card--link" href="{{ url_for('supplies.supplies_list') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Supplies</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Consumables and supply inventory</p>
        </a>
        {% endif %}
        {% if has_perm("admin.view") %}
        <a class="card card--link" href="{{ url_for('admin.ncrs') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">NCRs</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Non-Conformance Reports</p>
        </a>
        {% endif %}
        {% if has_perm("admin.view") %}
        <a class="card card--link" href="{{ url_for('admin.capas') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">CAPAs</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Corrective and Preventive Actions</p>
        </a>
        {% endif %}
      </div>
    </div>

    {# Column 3: External Relationships #}
    <div>
      <h2 style="font-size: 14px; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; padding-left: 4px;">
        External Relationships
      </h2>
      <div style="display: flex; flex-direction: column; gap: 12px;">
        {% if has_perm("distribution_log.view") %}
        <a class="card card--link" href="{{ url_for('rep_traceability.distribution_log_list') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Distribution Log</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Device distribution tracking</p>
        </a>
        {% endif %}
        {% if has_perm("sales_dashboard.view") %}
        <a class="card card--link" href="{{ url_for('rep_traceability.sales_dashboard') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Sales Dashboard</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Sales metrics and lot tracking</p>
        </a>
        {% endif %}
        {% if has_perm("customers.view") %}
        <a class="card card--link" href="{{ url_for('customer_profiles.customers_list') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Customers</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Customer profiles and history</p>
        </a>
        {% endif %}
        {% if has_perm("suppliers.view") %}
        <a class="card card--link" href="{{ url_for('suppliers.suppliers_list') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">Suppliers</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Approved supplier management</p>
        </a>
        {% endif %}
        {% if has_perm("sales_orders.view") %}
        <a class="card card--link" href="{{ url_for('nre_projects.nre_projects_index') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">NRE Projects</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Non-recurring engineering projects</p>
        </a>
        {% endif %}
      </div>
    </div>

  </div>
</div>

<style>
@media (max-width: 1000px) {
  div[style*="grid-template-columns: repeat(3"] {
    grid-template-columns: repeat(2, 1fr) !important;
  }
}
@media (max-width: 700px) {
  div[style*="grid-template-columns: repeat(3"] {
    grid-template-columns: 1fr !important;
  }
}
</style>
{% endblock %}
```

### Add NCRs Route Stub

**File:** `app/eqms/admin.py`

Add this route (near the other placeholder routes):

```python
@bp.get("/ncrs")
@require_permission("admin.view")
def ncrs():
    """NCRs module - placeholder."""
    return render_template("admin/ncrs.html")
```

### Create NCRs Template

**File:** `app/eqms/templates/admin/ncrs.html`

```html
{% extends "_layout.html" %}
{% block title %}NCRs{% endblock %}
{% block content %}
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
    <div>
      <h1 style="margin-top:0;">Non-Conformance Reports (NCRs)</h1>
      <p class="muted">Track and manage product and process non-conformances.</p>
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
      <li>NCR initiation and tracking</li>
      <li>Disposition management (Use As Is, Rework, Scrap)</li>
      <li>Root cause documentation</li>
      <li>CAPA linkage</li>
      <li>Closure verification</li>
    </ul>
  </div>
</div>
{% endblock %}
```

---

## PART 3: UPLOAD COMPATIBILITY TESTING

### 3.1 Test Data Sources

The system must handle uploads from these sources:

| Source | Location | Type | Parser |
|--------|----------|------|--------|
| Equipment Requirements Forms | `docs/EquipmentRequirementsForm/*.pdf` | PDF | `equipment/parsers/pdf.py` |
| Specifications | `docs/SpecificationsForm/*.docx` | DOCX | `equipment/parsers/pdf.py` |
| 2025 Sales Orders | `2025 Sales Orders.pdf` | Multi-page PDF | `rep_traceability/parsers/pdf.py` |
| January 2026 Sales Orders | `SO_SalesOrder2_January 2026.pdf` | Multi-page PDF | `rep_traceability/parsers/pdf.py` |
| Packing Slips | `Packing Slips.pdf` | Multi-page PDF | `rep_traceability/parsers/pdf.py` |
| ShipStation API | External API | JSON | `shipstation_sync/parsers.py` |

### 3.2 Equipment/Supplies Bulk Import

**Route:** `/admin/equipment/bulk-import`

**Test Checklist:**
- [ ] Page loads without error (after CSRF fix)
- [ ] Can upload Equipment Requirements Forms (PDF)
- [ ] Can upload Specification documents (DOCX)
- [ ] Parser correctly extracts equipment code from filename (e.g., "ST-012")
- [ ] Parser correctly extracts spec code (e.g., "SP-E.SLQ013")
- [ ] Equipment is created with correct fields
- [ ] Supplies are created for SP-S.* specs

**Known Issue to Check:**
The bulk import route at `equipment_bulk_import_post()` needs to handle:
1. PDF files for Requirements Forms
2. DOCX files for Specifications
3. Proper error handling for unsupported formats

**Verify in** `app/eqms/modules/equipment/admin.py`:
- Function `equipment_bulk_import_post()` should process both file types
- Check that DOCX parsing is implemented (or add stub)

### 3.3 Sales Order PDF Import

**Route:** `/admin/sales-orders/import-pdf`

**Test Checklist:**
- [ ] Page loads without error
- [ ] Can upload `2025 Sales Orders.pdf`
- [ ] Can upload `SO_SalesOrder2_January 2026.pdf`
- [ ] Parser splits multi-page PDF into individual orders
- [ ] Order numbers are correctly extracted
- [ ] Customer codes are correctly extracted
- [ ] SKUs and quantities are correctly parsed
- [ ] Duplicate order numbers are handled (update existing, attach new PDF page)

**Known Issues to Check:**
1. **Quantity overflow:** Large lot numbers being parsed as quantities (e.g., `81000412231`)
   - Check `MAX_REASONABLE_QUANTITY` constant is enforced
   - Check `_is_lot_number()` function exists and is used

2. **Customer code extraction:** Check `_parse_customer_number()` extracts "CUSTOMER NUMBER" field

3. **SKU normalization:** Check `_normalize_sku()` handles all valid formats

### 3.4 Shipping Labels (Packing Slips) Import

**Route:** `/admin/sales-orders/import-labels` (or similar)

**Test Checklist:**
- [ ] Dedicated upload route exists for shipping labels
- [ ] Parser handles Packing Slips format
- [ ] Tracking numbers are extracted
- [ ] Labels are matched to distributions (when possible)
- [ ] Unmatched labels are stored for manual review

**Verify:**
```python
# In rep_traceability/admin.py - check if these routes exist:
# - shipping_labels_import_bulk()
# - shipping_labels_import_get() / shipping_labels_import_post()
```

### 3.5 ShipStation Sync

**Route:** `/admin/shipstation/`

**Test Checklist:**
- [ ] Sync page loads
- [ ] API credentials are configured (check env vars)
- [ ] Full sync creates distribution entries
- [ ] Incremental sync works
- [ ] SKU canonicalization handles all patterns:
  - `211410SPT`, `211610SPT`, `211810SPT`
  - Box quantities (e.g., "box of 10") are expanded
- [ ] Lot numbers are extracted from item notes

### 3.6 Manual Order Entry

**Route:** `/admin/distribution-log/new`

**Test Checklist:**
- [ ] Form loads without error
- [ ] All required fields are present
- [ ] Customer dropdown populates
- [ ] Sales order linking works
- [ ] Can create entry without sales order (manual entry)
- [ ] Validation works (required fields, date formats)

---

## PART 4: LEGACY CODE CLEANUP

### 4.1 Search for Unused Code

Run these searches to identify legacy code:

```bash
# Find TODO/FIXME comments
grep -rn "TODO\|FIXME\|XXX\|HACK" app/eqms --include="*.py" --include="*.html"

# Find commented-out code blocks (Python)
grep -rn "^#.*def \|^#.*class " app/eqms --include="*.py"

# Find debug print statements
grep -rn "print(" app/eqms --include="*.py"

# Find unused imports (manual review needed)
# Use IDE or pyflakes to identify
```

### 4.2 Known Legacy Items to Review

1. **Tracing Reports** - Is this module actively used or legacy?
   - Route: `rep_traceability.tracing_list`
   - Check if it's linked from anywhere

2. **Sales Orders List** - Redundant with Sales Dashboard?
   - Route: `rep_traceability.sales_orders_list`
   - Should this be admin-only?

3. **Document Control module** - Check if fully implemented
   - `app/eqms/modules/document_control/`
   - May be a stub that needs completion or removal

4. **Duplicate route definitions** - Check for same path with different handlers

### 4.3 Files to Review for Cleanup

| File | Check For |
|------|-----------|
| `app/eqms/admin.py` | Unused routes, debug code |
| `app/eqms/routes.py` | Legacy public routes |
| `app/eqms/modules/*/admin.py` | Commented code, debug prints |
| `app/eqms/templates/admin/*.html` | Unused templates |

---

## PART 5: TOP NAVIGATION MENU UPDATE

### Current Problem
The top navigation doesn't match the admin dashboard organization.

### Update Navigation

**File:** `app/eqms/templates/_layout.html`

Simplify the navigation to match the 3-column organization:

```html
<nav class="topbar__nav">
  <a href="{{ url_for('routes.index') }}">Home</a>
  {% if has_perm("admin.view") %}
    <a href="{{ url_for('admin.index') }}">Admin</a>
  {% endif %}
  {% if g.current_user %}
    {# Primary quick links only #}
    {% if has_perm("distribution_log.view") %}
      <a href="{{ url_for('rep_traceability.distribution_log_list') }}">Distribution Log</a>
    {% endif %}
    {% if has_perm("customers.view") %}
      <a href="{{ url_for('customer_profiles.customers_list') }}">Customers</a>
    {% endif %}
    {% if has_perm("sales_dashboard.view") %}
      <a href="{{ url_for('rep_traceability.sales_dashboard') }}">Sales Dashboard</a>
    {% endif %}
    {% if has_perm("equipment.view") %}
      <a href="{{ url_for('equipment.equipment_list') }}">Equipment</a>
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

---

## PART 6: VERIFICATION CHECKLIST

### After All Fixes

#### Critical Pages (Must Load Without Error)
- [ ] `/admin/` - Dashboard with 3 columns
- [ ] `/admin/reset-data` - Data reset page
- [ ] `/admin/equipment/bulk-import` - Equipment import
- [ ] `/admin/supplies/new` - New supply form
- [ ] `/admin/distribution-log/new` - New distribution form
- [ ] `/admin/nre-projects/` - NRE projects list

#### New Module Stubs (Must Show Placeholder)
- [ ] `/admin/employee-training`
- [ ] `/admin/capas`
- [ ] `/admin/ncrs`
- [ ] `/admin/qms-documents`

#### Upload Functionality (Must Work)
- [ ] Equipment bulk import with PDF
- [ ] Sales order PDF import
- [ ] Shipping label import
- [ ] ShipStation sync

#### Admin Dashboard Organization
- [ ] 3 columns displayed
- [ ] All links work (no 404s)
- [ ] Responsive on mobile (columns stack)

---

## PART 7: COMMIT INSTRUCTIONS

After all changes:

```bash
git add -A
git status

git commit -m "$(cat <<'EOF'
Comprehensive system debug and admin reorganization

Bug Fixes:
- Fix csrf_token() -> csrf_token in all templates (8 locations)
- Remove parentheses from Jinja2 csrf_token calls

Admin Dashboard:
- Reorganize into 3 columns: Quality Management, Silq Operations, External Relationships
- Add NCRs placeholder module
- Add descriptions to all cards

Navigation:
- Simplify top menu to match dashboard categories
- Remove redundant links

Legacy Cleanup:
- Remove unused debug code
- Clean up commented-out sections
EOF
)"

git push origin main
```

---

## PART 8: POST-DEPLOYMENT VERIFICATION

After deployment succeeds:

1. **Test CSRF fix:**
   - Visit `/admin/reset-data`
   - Visit `/admin/supplies/new`
   - Should load without 500 error

2. **Test Dashboard:**
   - Visit `/admin/`
   - Verify 3-column layout
   - Click each card

3. **Test Uploads:**
   - Upload a test Equipment Requirements Form PDF
   - Upload a test Sales Order PDF
   - Run ShipStation sync

4. **Check Logs:**
   - No Python tracebacks
   - No 500 errors
   - No import errors

---

## APPENDIX A: FILE LOCATIONS REFERENCE

### Documents Folders
```
docs/EquipmentRequirementsForm/
├── Equipment Requirements Form, Equip ID ST-001 - Portable Exchange Deionizers (PEDI) System.pdf
├── ...
└── Equipment Requirements Form, Equip ID ST-016, Freeze Dry System, 2.5 Liter.pdf

docs/SpecificationsForm/
├── SP-E.SLQ001 A Source Control Specification, Portable Exchange Deionizer (PEDI) System.docx
├── SP-S.SLQ001 B Source Control Specification, High Purity Water.docx
├── ...
└── SP-S.SLQ011 A Source Control Specification, UV Cuvette.docx
```

### Key Application Files
```
app/eqms/
├── __init__.py                 # App factory, CSRF injection
├── admin.py                    # Admin routes (diagnostics, reset, stubs)
├── templates/
│   ├── _layout.html            # Base layout with navigation
│   └── admin/
│       ├── index.html          # Admin dashboard
│       ├── reset_data.html     # Data reset page
│       ├── employee_training.html
│       ├── capas.html
│       ├── ncrs.html           # NEW
│       └── qms_documents.html
└── modules/
    ├── equipment/admin.py      # Equipment routes + bulk import
    ├── supplies/admin.py       # Supplies CRUD
    ├── rep_traceability/
    │   ├── admin.py            # Distribution, sales orders, tracing
    │   └── parsers/pdf.py      # Sales order PDF parser
    └── shipstation_sync/
        ├── admin.py            # ShipStation sync UI
        └── parsers.py          # ShipStation data parser
```

---

**END OF DEBUG AGENT PROMPT**
