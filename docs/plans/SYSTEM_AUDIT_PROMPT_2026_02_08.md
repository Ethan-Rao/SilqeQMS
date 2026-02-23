# SYSTEM-WIDE AUDIT PROMPT
**Date:** February 8, 2026  
**Type:** Comprehensive System Audit  
**Agent:** Debugging Agent

---

## AUDIT OBJECTIVES

Perform a complete system-wide audit of the SilqQMS application to:

1. **Identify all bugs and errors** - Runtime, logic, and template errors
2. **Verify module completeness** - Check each module is fully implemented
3. **Review code quality** - Identify legacy code, duplication, and anti-patterns
4. **Validate database schema** - Ensure models match migrations
5. **Test all routes** - Verify every route is accessible and functional
6. **Check template consistency** - Ensure all templates use correct patterns
7. **Audit security** - Review authentication, authorization, and CSRF
8. **Document findings** - Create actionable fix list

---

## PART 1: KNOWN CRITICAL ISSUES

### 1.1 CSRF Token Bug (CRITICAL)
**Status:** BROKEN - Multiple pages return 500 error

**Problem:** Templates use `{{ csrf_token() }}` but context processor injects it as a string.

**Affected Files:**
```
app/eqms/templates/admin/reset_data.html:35
app/eqms/templates/admin/equipment/bulk_import.html:19
app/eqms/templates/admin/supplies/new.html:7
app/eqms/templates/admin/supplies/edit.html:7
app/eqms/templates/admin/distribution_log/edit.html:175
app/eqms/templates/admin/nre_projects/detail.html:54,81,102
```

**Fix:** Replace `{{ csrf_token() }}` with `{{ csrf_token }}`

**Audit Task:** Search ALL templates for this pattern:
```bash
grep -rn "csrf_token()" app/eqms/templates --include="*.html"
```

---

## PART 2: MODULE-BY-MODULE AUDIT

### Audit Checklist Per Module

For each module, verify:
- [ ] Models defined and migrated
- [ ] Admin routes implemented
- [ ] Service layer exists (if needed)
- [ ] Templates exist and are functional
- [ ] Blueprint registered in `__init__.py`
- [ ] No orphaned/dead code

---

### 2.1 Core Application (`app/eqms/`)

| File | Purpose | Audit Status |
|------|---------|--------------|
| `__init__.py` | App factory, blueprint registration | Check all blueprints registered |
| `admin.py` | Admin routes (diagnostics, reset, stubs) | Check all routes work |
| `auth.py` | Authentication (login/logout) | Verify login flow |
| `audit.py` | Audit event logging | Check events are recorded |
| `config.py` | Configuration loading | Verify env vars |
| `constants.py` | SKU mappings, exclusions | Check completeness |
| `db.py` | Database session management | Check connection pooling |
| `models.py` | Base models (User, Role, AuditEvent) | Verify relationships |
| `rbac.py` | Permission checking | Test all permissions |
| `routes.py` | Public routes | Check what's exposed |
| `security.py` | CSRF protection | Verify token handling |
| `storage.py` | File storage (S3/local) | Test upload/download |
| `utils.py` | Utility functions | Check for dead code |

**Audit Commands:**
```bash
# Check all blueprints are registered
grep -n "register_blueprint" app/eqms/__init__.py

# Find all route definitions in admin.py
grep -n "@bp\." app/eqms/admin.py | head -50

# Check RBAC permissions defined
grep -n "require_permission" app/eqms/admin.py
```

---

### 2.2 Customer Profiles (`modules/customer_profiles/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` | ✓ | Customer, CustomerNote, CustomerRep |
| `admin.py` | ✓ | List, detail, edit, merge |
| `service.py` | ✓ | find_or_create_customer |
| `utils.py` | ? | Check usage |

**Audit Tasks:**
- [ ] Verify `customer_code` column exists and is indexed
- [ ] Check customer list filters work
- [ ] Test customer merge functionality
- [ ] Verify NRE customers don't appear in main list

---

### 2.3 Rep Traceability (`modules/rep_traceability/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` | ✓ | SalesOrder, DistributionLogEntry, TracingReport |
| `admin.py` | ✓ | Large file - many routes |
| `service.py` | ✓ | Distribution matching, lot tracking |
| `parsers/pdf.py` | ✓ | Sales order PDF parsing |
| `parsers/csv.py` | ✓ | CSV import |
| `utils.py` | ? | Check usage |

**Audit Tasks:**
- [ ] Test sales order PDF import with sample files
- [ ] Verify quantity parsing doesn't overflow (MAX_REASONABLE_QUANTITY)
- [ ] Check lot number extraction patterns
- [ ] Test distribution log CRUD
- [ ] Verify tracing report generation
- [ ] Check sales dashboard metrics

**Known Issues to Verify:**
```python
# In parsers/pdf.py - check these exist:
MAX_REASONABLE_QUANTITY = 50000  # Should exist
_is_lot_number()  # Function should exist
_parse_customer_number()  # Should extract CUSTOMER NUMBER field
```

---

### 2.4 ShipStation Sync (`modules/shipstation_sync/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` | ✓ | ShipStationSyncRun, SkippedOrder |
| `admin.py` | ✓ | Sync UI |
| `service.py` | ✓ | Sync logic |
| `parsers.py` | ✓ | SKU/quantity parsing |
| `shipstation_client.py` | ✓ | API client |

**Audit Tasks:**
- [ ] Verify API credentials handling
- [ ] Test SKU canonicalization for all patterns
- [ ] Check quantity inference (box of 10, etc.)
- [ ] Verify lot extraction from item notes
- [ ] Test incremental sync

**Check in parsers.py:**
```python
# Verify these patterns are handled:
- "211410SPT", "211610SPT", "211810SPT"
- "box of 10", "case of 5"
- Lot patterns: "SLQ-XXXXX", "LOT: XXXXX"
```

---

### 2.5 Equipment (`modules/equipment/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` | ✓ | Equipment, EquipmentSupplier, ManagedDocument |
| `admin.py` | ✓ | CRUD, bulk import, document upload |
| `service.py` | ✓ | Equipment operations |
| `parsers/pdf.py` | ✓ | Requirements form parsing |

**Audit Tasks:**
- [ ] Test equipment list and filters
- [ ] Test bulk import from docs folder
- [ ] Verify PDF parsing extracts equipment code
- [ ] Check document upload/download
- [ ] Test supplier association

---

### 2.6 Supplies (`modules/supplies/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` | ✓ | Supply, SupplySupplier, SupplyDocument |
| `admin.py` | ✓ | CRUD |
| `service.py` | ✓ | Supply operations |

**Audit Tasks:**
- [ ] Test supplies list
- [ ] Test create/edit (CSRF bug here)
- [ ] Verify document upload
- [ ] Check supplier association

---

### 2.7 Suppliers (`modules/suppliers/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` | ✓ | Supplier model |
| `admin.py` | ✓ | CRUD |
| `service.py` | ✓ | Supplier operations |

**Audit Tasks:**
- [ ] Test supplier list
- [ ] Test create/edit
- [ ] Verify PDF extraction for supplier info
- [ ] Check relationships to Equipment/Supplies

---

### 2.8 Manufacturing (`modules/manufacturing/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` | ✓ | SuspensionBatch, etc. |
| `admin.py` | ✓ | Batch tracking |
| `service.py` | ✓ | Manufacturing operations |

**Audit Tasks:**
- [ ] Test manufacturing index page
- [ ] Verify suspension batch CRUD
- [ ] Check lot log integration

---

### 2.9 NRE Projects (`modules/nre_projects/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `admin.py` | ✓ | NRE customer list, detail |
| No models.py | - | Uses Customer model |

**Audit Tasks:**
- [ ] Test NRE projects list (customers with orders but no distributions)
- [ ] Test customer edit modal
- [ ] Test PDF upload to orders (CSRF bug here)
- [ ] Verify download/delete PDFs

---

### 2.10 Document Control (`modules/document_control/`)

| Component | Status | Notes |
|-----------|--------|-------|
| `models.py` | ? | Check if complete |
| `admin.py` | ? | Check if functional |
| `service.py` | ? | Check if used |

**Audit Tasks:**
- [ ] Determine if this module is complete or a stub
- [ ] Check if routes work
- [ ] If incomplete, mark as "Coming Soon" or remove

---

## PART 3: TEMPLATE AUDIT

### 3.1 Check All Templates Exist

```bash
# List all templates
find app/eqms/templates -name "*.html" | sort
```

### 3.2 Template Pattern Verification

**Check for CSRF Token Pattern:**
```bash
# WRONG (must fix):
grep -rn "csrf_token()" app/eqms/templates --include="*.html"

# CORRECT:
grep -rn '{{ csrf_token }}' app/eqms/templates --include="*.html"
grep -rn "csrf_token }}" app/eqms/templates --include="*.html"
```

**Check All Templates Extend Layout:**
```bash
grep -L "extends" app/eqms/templates/**/*.html
```

**Check for Broken url_for Calls:**
```bash
# List all url_for calls for manual review
grep -rn "url_for(" app/eqms/templates --include="*.html" | head -100
```

### 3.3 Template-Route Mapping

Verify each template has a corresponding route:

| Template | Expected Route | Verify |
|----------|---------------|--------|
| `admin/index.html` | `admin.index` | [ ] |
| `admin/reset_data.html` | `admin.reset_data_get` | [ ] |
| `admin/diagnostics.html` | `admin.diagnostics` | [ ] |
| `admin/employee_training.html` | `admin.employee_training` | [ ] |
| `admin/capas.html` | `admin.capas` | [ ] |
| `admin/ncrs.html` | `admin.ncrs` | [ ] |
| `admin/qms_documents.html` | `admin.qms_documents` | [ ] |
| `admin/equipment/list.html` | `equipment.equipment_list` | [ ] |
| `admin/supplies/list.html` | `supplies.supplies_list` | [ ] |
| `admin/suppliers/list.html` | `suppliers.suppliers_list` | [ ] |
| ... | ... | ... |

---

## PART 4: DATABASE AUDIT

### 4.1 Check Migrations

```bash
# List all migrations
ls -la migrations/versions/

# Check current database head
# (Run in production console or local)
alembic current
alembic heads
```

**Verify No Multiple Heads:**
If `alembic heads` shows multiple revisions, migrations need to be fixed.

### 4.2 Model-Table Verification

For each model, verify the table exists with correct columns:

| Model | Table | Key Columns to Verify |
|-------|-------|----------------------|
| User | users | id, email, password_hash, is_active |
| Role | roles | id, name, permissions |
| Customer | customers | id, facility_name, customer_code |
| SalesOrder | sales_orders | id, order_number, customer_id |
| DistributionLogEntry | distribution_log_entries | id, customer_id, sales_order_id |
| Equipment | equipment | id, equip_code, status |
| Supply | supplies | id, supply_code, status |
| Supplier | suppliers | id, name, status |

### 4.3 Check Indexes

```sql
-- Run in database console
SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public';
```

Verify indexes exist on:
- `customers.customer_code`
- `sales_orders.order_number`
- `distribution_log_entries.customer_id`
- `equipment.equip_code`

---

## PART 5: ROUTE AUDIT

### 5.1 List All Routes

Create a route map by examining all blueprints:

```python
# Run in Flask shell or create a script
from app.eqms import create_app
app = create_app()
for rule in app.url_map.iter_rules():
    print(f"{rule.methods} {rule.rule} -> {rule.endpoint}")
```

### 5.2 Test Critical Routes

| Route | Method | Expected | Test |
|-------|--------|----------|------|
| `/` | GET | Public home page | [ ] |
| `/admin/` | GET | Admin dashboard | [ ] |
| `/admin/reset-data` | GET | Reset data page | [ ] |
| `/admin/reset-data` | POST | Execute reset | [ ] |
| `/admin/equipment/` | GET | Equipment list | [ ] |
| `/admin/equipment/bulk-import` | GET | Bulk import page | [ ] |
| `/admin/supplies/` | GET | Supplies list | [ ] |
| `/admin/supplies/new` | GET | New supply form | [ ] |
| `/admin/distribution-log/` | GET | Distribution list | [ ] |
| `/admin/sales-orders/import-pdf` | GET | PDF import | [ ] |
| `/admin/nre-projects/` | GET | NRE projects | [ ] |
| `/admin/shipstation/` | GET | ShipStation sync | [ ] |

### 5.3 Check for Dead Routes

Routes that exist but may not be used:
```bash
# Find route definitions
grep -rn "@bp\.(get|post|put|delete)" app/eqms --include="*.py"

# Cross-reference with url_for calls in templates
grep -rn "url_for(" app/eqms/templates --include="*.html"
```

---

## PART 6: SECURITY AUDIT

### 6.1 Authentication

- [ ] Login page works
- [ ] Password hashing is secure (werkzeug)
- [ ] Session management is secure
- [ ] Logout properly clears session

### 6.2 Authorization (RBAC)

- [ ] All admin routes have `@require_permission` decorator
- [ ] Permission checks are correct
- [ ] No routes bypass auth checks

```bash
# Find routes without permission checks
grep -rn "def \w\+(" app/eqms/admin.py | head -20
# Compare with:
grep -rn "@require_permission" app/eqms/admin.py | head -20
```

### 6.3 CSRF Protection

- [ ] All POST forms include CSRF token
- [ ] CSRF validation runs on all POST requests
- [ ] Token is properly regenerated

### 6.4 Input Validation

- [ ] File uploads are validated (size, type)
- [ ] SQL injection prevention (parameterized queries via SQLAlchemy)
- [ ] XSS prevention (Jinja2 auto-escaping)

---

## PART 7: CODE QUALITY AUDIT

### 7.1 Find Dead Code

```bash
# Commented-out code
grep -rn "^#.*def " app/eqms --include="*.py"
grep -rn "^#.*class " app/eqms --include="*.py"

# TODO/FIXME markers
grep -rn "TODO\|FIXME\|XXX\|HACK" app/eqms --include="*.py"

# Debug prints
grep -rn "print(" app/eqms --include="*.py"

# Unused imports (requires pyflakes or similar)
```

### 7.2 Check for Duplication

- [ ] No duplicate route definitions
- [ ] No duplicate model definitions
- [ ] Shared utilities are in `utils.py`

### 7.3 Code Consistency

- [ ] Consistent naming (snake_case for functions, PascalCase for classes)
- [ ] Consistent import ordering
- [ ] Consistent error handling patterns

---

## PART 8: PERFORMANCE AUDIT

### 8.1 Database Queries

- [ ] No N+1 query patterns
- [ ] Proper use of `selectin` loading for relationships
- [ ] Pagination on list views

### 8.2 File Handling

- [ ] Large file uploads stream properly
- [ ] PDF parsing doesn't load entire file into memory unnecessarily

### 8.3 Session Management

- [ ] Database connections are properly pooled
- [ ] Sessions are closed after requests

---

## PART 9: DOCUMENTATION AUDIT

### 9.1 Code Documentation

- [ ] All modules have docstrings
- [ ] Complex functions are documented
- [ ] API endpoints are documented

### 9.2 User Documentation

- [ ] README is current
- [ ] Deployment docs exist
- [ ] Admin user guide exists (or is planned)

---

## PART 10: AUDIT OUTPUT FORMAT

### Create Findings Document

After completing the audit, create a findings document with:

```markdown
# System Audit Findings - [DATE]

## Critical Issues (Must Fix)
1. [Issue description]
   - Location: [file:line]
   - Impact: [what breaks]
   - Fix: [how to fix]

## High Priority Issues
1. ...

## Medium Priority Issues
1. ...

## Low Priority / Cleanup
1. ...

## Modules Status
| Module | Status | Notes |
|--------|--------|-------|
| ... | ... | ... |

## Recommendations
1. ...
```

---

## PART 11: FIX IMPLEMENTATION ORDER

After audit, implement fixes in this order:

1. **Critical bugs** (CSRF, 500 errors)
2. **Security issues** (auth bypass, missing validations)
3. **Broken features** (routes that don't work)
4. **Missing features** (stub modules)
5. **Code cleanup** (dead code, duplication)
6. **Performance** (query optimization)
7. **Documentation** (code comments, user docs)

---

## PART 12: COMMIT AND DEPLOYMENT

After all fixes:

```bash
git add -A
git status

# Commit with detailed message
git commit -m "$(cat <<'EOF'
System-wide audit fixes

Critical:
- Fix CSRF token template errors (8 files)
- [Other critical fixes]

Security:
- [Security fixes]

Features:
- [Feature fixes]

Cleanup:
- Remove dead code
- Fix code duplication
- Update documentation
EOF
)"

git push origin main
```

---

## APPENDIX: QUICK REFERENCE

### File Counts
```
Python files: 56
Template files: ~50
Modules: 10
Routes: ~100+
```

### Key Files for Each Area
```
Auth:           app/eqms/auth.py, security.py
Admin:          app/eqms/admin.py
Database:       app/eqms/db.py, models.py
Templates:      app/eqms/templates/
Modules:        app/eqms/modules/*/
Migrations:     migrations/versions/
Config:         app/eqms/config.py
```

### Common Issues Found in Past Audits
1. CSRF token pattern errors
2. Missing permission checks
3. Unused imports
4. Debug print statements
5. Commented-out code blocks
6. Duplicate route definitions
7. Missing database indexes
8. N+1 query patterns

---

**END OF SYSTEM AUDIT PROMPT**
