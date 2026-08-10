# AGENT PROMPT: Comprehensive System Audit

**Objective:** Perform a thorough audit of the SilqQMS codebase to identify non-functional components, describe correction strategies, and flag legacy code for deletion.

---

## INSTRUCTIONS FOR AGENT

You are tasked with auditing the SilqQMS Flask application. This is an electronic Quality Management System (eQMS) for medical device traceability. Your audit should be systematic and thorough.

---

## PART 1: NON-FUNCTIONAL COMPONENT IDENTIFICATION

### Priority Focus: PDF Upload & Parsing System

The PDF import system is experiencing critical failures. Investigate the following areas:

#### 1.1 PDF Import Routes
**Files to examine:**
- `app/eqms/modules/rep_traceability/admin.py` - Look for routes containing `import_pdf`, `sales_orders`, `shipping_labels`
- `app/eqms/templates/admin/sales_orders/import.html`

**Check for:**
- [ ] Routes that return 404 or 500 errors
- [ ] Missing template references
- [ ] Broken form actions
- [ ] Missing CSRF token handling

#### 1.2 PDF Parser Logic
**Files to examine:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py`

**Known Issue to Verify:**
The `_parse_quantity()` function may be parsing lot numbers (e.g., `81000412231`) as quantities, causing `integer out of range` PostgreSQL errors.

**Check for:**
- [ ] `_parse_quantity()` - Does it validate that quantities are reasonable (< 100,000)?
- [ ] `_parse_silq_sales_order_page()` - Does table column parsing correctly distinguish between:
  - Item codes (column 0)
  - Descriptions (column 1)
  - Quantities (column 2)
  - Lot numbers (column 3+)
- [ ] Are lot number patterns (SLQ-XXXXXXXX, 8-11 digit numbers) being mistakenly parsed as quantities?

**Test with these known lot numbers from LotLog.csv:**
```
SLQ-81000412231 → 211410SPT
SLQ-81020403231 → 211810SPT
SLQ-81020515241 → 211810SPT
```

#### 1.3 PDF Storage System
**Files to examine:**
- `app/eqms/storage.py`
- `app/eqms/modules/rep_traceability/admin.py` (function `_store_pdf_attachment`)

**Check for:**
- [ ] Does `storage.put_bytes()` handle failures gracefully?
- [ ] Is there a `storage.delete()` method implemented?
- [ ] Are storage errors being logged and reported to users?

#### 1.4 PDF Dependencies
**Check in production:**
- [ ] Is `pdfplumber` installed and importable?
- [ ] Is `PyPDF2` installed and importable?
- [ ] Check `requirements.txt` for correct versions

---

### Secondary Focus: Admin Tools & Diagnostics

#### 1.5 Admin Diagnostics Page
**Files to examine:**
- `app/eqms/admin.py` - function `_diagnostics_allowed()` and route `/diagnostics`
- `app/eqms/templates/admin/diagnostics.html`

**Known Issue:**
The `/admin/diagnostics` route returns 404 in production because `_diagnostics_allowed()` checks for `ENV != "production"` or `ADMIN_DIAGNOSTICS_ENABLED=1`.

**Check for:**
- [ ] Is this intentional security behavior or a bug?
- [ ] Should admin users with `admin.edit` permission always have access?

#### 1.6 Account Management
**Files to examine:**
- `app/eqms/admin.py` - routes `/accounts`, `/accounts/new`, `/accounts/<id>`
- `app/eqms/templates/admin/accounts/` directory

**Check for:**
- [ ] Do all account management routes exist and function?
- [ ] Is password hashing using secure methods (werkzeug)?
- [ ] Are audit events recorded for account changes?

---

### Tertiary Focus: Sales Dashboard & Lot Tracking

#### 1.7 Lot Tracking Display
**Files to examine:**
- `app/eqms/modules/rep_traceability/service.py` - function `compute_sales_dashboard()`
- `app/eqms/templates/admin/sales_dashboard/index.html`

**Check for:**
- [ ] For SKUs without lots manufactured since 2025, does the fallback logic find the most recent lot?
- [ ] Is `lot_years` dict being populated correctly from LotLog.csv?
- [ ] Does the "Current Lot" column show valid data for all SKUs?

#### 1.8 LotLog CSV Parsing
**Files to examine:**
- `app/eqms/modules/shipstation_sync/parsers.py` - function `load_lot_log_with_inventory()`
- `app/eqms/data/LotLog.csv`

**Check for:**
- [ ] Are manufacturing dates being parsed correctly (M/D/YYYY and YYYY-MM-DD formats)?
- [ ] Are lot corrections being applied (Correct Lot Name column)?
- [ ] Is inventory data (Total Units in Lot) being loaded?

---

## PART 2: CORRECTION STRATEGY DOCUMENTATION

For each non-functional component identified, document:

### Template for Each Issue:

```markdown
### ISSUE: [Brief Title]

**Location:** [File path and line numbers]

**Severity:** CRITICAL / HIGH / MEDIUM / LOW

**Symptoms:** 
[What the user observes - error messages, broken UI, etc.]

**Root Cause:**
[Technical explanation of why this is happening]

**Correction Strategy:**
1. [Step 1]
2. [Step 2]
3. [Step n]

**Code Changes Required:**
```python
# Before:
[existing code]

# After:
[corrected code]
```

**Testing Steps:**
1. [How to verify the fix works]
```

---

## PART 3: LEGACY CODE IDENTIFICATION

Search for and document code that should be deleted:

### 3.1 Deprecated Functions
**Search patterns:**
- Functions with `# TODO: remove` or `# DEPRECATED` comments
- Functions that are defined but never called
- Duplicate implementations of the same logic

### 3.2 Dead Routes
**Check for:**
- Routes in blueprints that have no corresponding template
- Routes that are never linked from any UI
- Commented-out route definitions

### 3.3 Unused Imports
**In each Python file, check:**
- Imports at the top that are never used in the file
- Conditional imports that are no longer needed

### 3.4 Obsolete Templates
**Check for:**
- HTML templates not referenced by any route
- Template fragments (`_partial.html`) not included anywhere
- Templates for features that were removed

### 3.5 Redundant Configuration
**Check for:**
- Environment variables that are defined but never read
- Config values that have no effect
- Duplicate constant definitions across files

### 3.6 Stale Migration Code
**Check:**
- `migrations/versions/` for migrations that could be squashed
- Migration scripts with TODO comments
- Rollback code that will never be used

---

## PART 4: OUTPUT FORMAT

Produce a comprehensive report with the following structure:

```markdown
# SYSTEM AUDIT REPORT
**Date:** [Current Date]
**Auditor:** AI Agent

## Executive Summary
[2-3 paragraph overview of findings]

## Critical Issues (Immediate Action Required)
[List with full details per template above]

## High Priority Issues
[List with full details]

## Medium Priority Issues
[List with full details]

## Low Priority Issues
[List with full details]

## Legacy Code for Deletion
| File | Lines | Description | Safe to Delete? |
|------|-------|-------------|-----------------|
| ... | ... | ... | Yes/No/Needs Review |

## Recommended Implementation Order
1. [First fix - usually critical security or data integrity]
2. [Second fix]
...

## Testing Checklist
- [ ] [Test case 1]
- [ ] [Test case 2]
...
```

---

## PART 5: SPECIFIC AREAS TO INVESTIGATE

Based on recent production issues, pay special attention to:

### 5.1 Database Connection Handling
- Check `app/eqms/db.py` for `pool_pre_ping` and `pool_recycle` settings
- Verify connections are properly disposed after Gunicorn forks
- Check for any raw SQL that might leak connections

### 5.2 Error Handling Patterns
- Look for bare `except:` clauses that swallow errors
- Check if errors are being logged with full tracebacks
- Verify user-facing error messages don't expose internals

### 5.3 CSRF Protection
- Verify all POST/PUT/DELETE routes check CSRF tokens
- Check AJAX calls include the token in headers
- Look for routes that bypass CSRF validation

### 5.4 Permission Checks
- Verify all admin routes use `@require_permission()` decorator
- Check for routes that should be protected but aren't
- Look for permission checks that reference non-existent permissions

### 5.5 Data Validation
- Check all form handlers validate input before database operations
- Look for SQL injection vulnerabilities (raw string formatting in queries)
- Verify file upload handlers check file types and sizes

---

## EXECUTION INSTRUCTIONS

1. **Start with PDF parsing** - This is the most critical current issue
2. **Use grep/search tools** to find all references to functions before marking as unused
3. **Check git history** if unsure whether code is intentionally disabled vs. broken
4. **Test hypotheses** by reading related code, not just the suspicious code
5. **Document everything** - Even if you're unsure, note it for human review

---

## DELIVERABLE

Save your audit report to:
```
docs/audits/SYSTEM_AUDIT_[DATE].md
```

The report should be actionable - a developer should be able to read it and immediately start fixing issues without needing additional context.

---

**END OF AGENT PROMPT**
