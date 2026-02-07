# DEBUG AGENT PROMPT: System Audit & Git Cleanup
**Date:** January 31, 2026  
**Priority:** HIGH  
**Scope:** Full system audit, resolve uncommitted changes, verify recent deployment

---

## SITUATION OVERVIEW

The dev agent completed the ShipStation/Sales Order redesign and pushed to main, but left uncommitted local changes in the working tree. The user needs:

1. A comprehensive audit of the system to catch any issues
2. Resolution of the uncommitted changes (commit or discard)
3. Step-by-step instructions for next actions

---

## PART 1: GIT STATUS ANALYSIS

### Current State
Run `git status` to see the current state. You should find:

**Modified files (not staged):**
- `app/eqms/admin.py`
- `app/eqms/config.py`
- `app/eqms/data/LotLog.csv`
- `app/eqms/modules/rep_traceability/service.py`
- `app/eqms/modules/shipstation_sync/service.py`
- `app/eqms/storage.py`
- `app/eqms/templates/admin/sales_dashboard/index.html`
- `app/eqms/templates/admin/sales_orders/unmatched_pdfs.html`
- `app/eqms/templates/public/index.html`

**Untracked files:**
- `docs/audits/`
- `docs/plans/AGENT_PROMPT_COMPREHENSIVE_SYSTEM_AUDIT.md`
- `docs/plans/DEVELOPER_PROMPT_2026_01_31_COMPREHENSIVE_AUDIT.md`
- `docs/plans/DEVELOPER_PROMPT_2026_01_31_SHIPSTATION_SALESORDER_REDESIGN.md`

### Analysis of Each Change

#### SHOULD COMMIT (Useful improvements):

1. **`app/eqms/admin.py`** - Permission fix
   - Changed `admin.edit` to `admin.view` for diagnostics access
   - **Verdict: COMMIT** - Makes diagnostics accessible to more admin users

2. **`app/eqms/config.py`** - New config option
   - Added `storage_local_root` setting and `STORAGE_LOCAL_ROOT` env var
   - **Verdict: COMMIT** - Useful for configurable storage paths

3. **`app/eqms/storage.py`** - Storage path improvement
   - Added support for `STORAGE_LOCAL_ROOT` override
   - Changed default from `os.getcwd()` to path relative to module
   - **Verdict: COMMIT** - Fixes potential path issues

4. **`app/eqms/modules/rep_traceability/service.py`** - Error handling
   - Added `lotlog_missing` flag when LotLog.csv fails to load
   - **Verdict: COMMIT** - Better error visibility

5. **`app/eqms/templates/admin/sales_dashboard/index.html`** - Warning UI
   - Added warning banner when LotLog is not loaded
   - **Verdict: COMMIT** - Helpful user feedback

6. **Documentation files** (untracked)
   - Planning and audit documents
   - **Verdict: COMMIT** - Useful documentation

#### SHOULD DISCARD (Potentially problematic):

7. **`app/eqms/data/LotLog.csv`** - Data change
   - Changed `05012025` to `5012025` (removed leading zero)
   - **Verdict: DISCARD** - This might break lot matching; leading zeros may be significant

#### SHOULD INVESTIGATE (Line ending changes only):

8. **`app/eqms/templates/admin/sales_orders/unmatched_pdfs.html`**
9. **`app/eqms/templates/public/index.html`**
   - Git shows warnings about LF → CRLF conversion
   - Run `git diff` on these files to check if they have actual content changes
   - **Verdict: If only line endings, DISCARD**

---

## PART 2: GIT CLEANUP INSTRUCTIONS

Execute these steps in order:

### Step 1: Discard unwanted changes
```bash
# Discard the LotLog.csv change (keep original with leading zeros)
git restore app/eqms/data/LotLog.csv

# If template files have no real changes, discard them too
git restore app/eqms/templates/admin/sales_orders/unmatched_pdfs.html
git restore app/eqms/templates/public/index.html
```

### Step 2: Stage the good changes
```bash
git add app/eqms/admin.py
git add app/eqms/config.py
git add app/eqms/storage.py
git add app/eqms/modules/rep_traceability/service.py
git add app/eqms/templates/admin/sales_dashboard/index.html
```

### Step 3: Stage documentation
```bash
git add docs/plans/
git add docs/audits/
```

### Step 4: Commit
```bash
git commit -m "$(cat <<'EOF'
Add storage config, diagnostics permission fix, and LotLog warning

- Add STORAGE_LOCAL_ROOT env var for configurable local storage path
- Change diagnostics permission from admin.edit to admin.view
- Add lotlog_missing flag and warning banner on sales dashboard
- Add planning and audit documentation
EOF
)"
```

### Step 5: Push
```bash
git push origin main
```

### Step 6: Verify clean state
```bash
git status
# Should show "nothing to commit, working tree clean"
```

---

## PART 3: SYSTEM AUDIT CHECKLIST

After resolving git issues, perform these checks:

### 3.1 Database Schema Verification
```bash
# Run migrations to ensure schema is up to date
alembic upgrade head

# Check for pending migrations
alembic current
alembic heads
```

### 3.2 New Features Verification

**Customer Code Feature:**
- [ ] Check `customers` table has `customer_code` column
- [ ] Verify index exists on `customer_code`

```sql
-- Run in database console
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'customers' AND column_name = 'customer_code';

-- Check for customers with codes populated
SELECT customer_code, COUNT(*) 
FROM customers 
WHERE customer_code IS NOT NULL 
GROUP BY customer_code;
```

**NRE Projects Module:**
- [ ] Verify `/admin/nre-projects` route works
- [ ] Check blueprint is registered in `app/eqms/__init__.py`
- [ ] Verify template exists at `app/eqms/templates/admin/nre_projects/index.html`

**Sales Order Deduplication:**
- [ ] Check for duplicate order_numbers in sales_orders table

```sql
SELECT order_number, COUNT(*) as cnt 
FROM sales_orders 
GROUP BY order_number 
HAVING COUNT(*) > 1;
```

### 3.3 File Existence Checks
```bash
# Check NRE module exists
ls app/eqms/modules/nre_projects/

# Check templates exist
ls app/eqms/templates/admin/nre_projects/

# Check LotLog.csv is accessible
head -5 app/eqms/data/LotLog.csv
```

### 3.4 Import/Syntax Check
```bash
# Verify Python files have no syntax errors
python -c "from app.eqms import create_app; app = create_app(); print('App created successfully')"
```

### 3.5 Common Issues to Look For

1. **Missing imports** - New modules may need imports in `__init__.py`
2. **Blueprint registration** - Check `nre_projects` blueprint is registered
3. **Template paths** - Verify templates are in correct directories
4. **Migration conflicts** - Check alembic history for issues
5. **Constraint violations** - The SKU constraint removal migration must be applied

---

## PART 4: SPECIFIC ISSUES TO INVESTIGATE

### 4.1 PDF Parser - Customer Code Extraction
**File:** `app/eqms/modules/rep_traceability/parsers/pdf.py`

Check that `_parse_customer_number()` function was added:
```python
# Should exist and extract "CUSTOMER NUMBER: XXXX" from PDFs
def _parse_customer_number(text: str) -> str | None:
    ...
```

If missing, add it per the DEVELOPER_PROMPT_2026_01_31_SHIPSTATION_SALESORDER_REDESIGN.md instructions.

### 4.2 Customer Service - customer_code Parameter
**File:** `app/eqms/modules/customer_profiles/service.py`

Check that `find_or_create_customer()` accepts and uses `customer_code`:
```python
def find_or_create_customer(
    s,
    *,
    facility_name: str,
    customer_code: str | None = None,  # Should be present
    ...
):
```

### 4.3 Sales Order Import - Deduplication Logic
**File:** `app/eqms/modules/rep_traceability/admin.py`

In `sales_orders_import_pdf_bulk()`, verify deduplication uses `order_number`:
```python
# Should check by order_number, not external_key
existing_order = (
    s.query(SalesOrder)
    .filter(SalesOrder.order_number == order_number)
    .first()
)
```

### 4.4 Quantity Inference Enhancement
**File:** `app/eqms/modules/shipstation_sync/parsers.py`

Check `infer_units()` handles multiple box patterns:
```python
def infer_units(item_name: str, quantity: int) -> int:
    # Should check for: "10-pack", "box of 10", "case of 100", etc.
```

---

## PART 5: OUTPUT FOR USER

After completing the audit, provide the user with:

### Summary Report
```markdown
## Git Cleanup Summary
- Committed: [list files]
- Discarded: [list files]
- Push status: [success/failed]

## System Audit Results
- Database schema: [OK/ISSUES]
- NRE Projects module: [OK/MISSING/PARTIAL]
- Customer code feature: [OK/MISSING/PARTIAL]
- Sales order deduplication: [OK/ISSUES]
- PDF parser updates: [OK/MISSING/PARTIAL]

## Issues Found
1. [Issue description and fix status]
2. [Issue description and fix status]

## Next Steps for User
1. [Specific action]
2. [Specific action]
```

### Step-by-Step User Instructions
Provide clear, numbered instructions for what the user should do next, such as:

1. **Deploy to production** (if changes are pushed)
2. **Run migrations** on production
3. **Test specific features** with listed verification steps
4. **Reset data** if needed (with exact SQL commands)
5. **Re-import PDFs** in correct order

---

## PART 6: EXECUTION CHECKLIST FOR DEBUG AGENT

- [ ] Run `git status` and analyze all changes
- [ ] Run `git diff` on each modified file to understand changes
- [ ] Execute git cleanup commands (restore unwanted, stage wanted, commit, push)
- [ ] Verify working tree is clean
- [ ] Check database schema is up to date
- [ ] Verify all new modules/routes exist and work
- [ ] Check for missing code from the dev agent's changes
- [ ] Test critical paths (PDF import, customer matching, NRE projects)
- [ ] Document all findings
- [ ] Provide clear next steps for user

---

## CRITICAL: DO NOT

- Do NOT force push or rebase without user approval
- Do NOT delete any data without explicit confirmation
- Do NOT modify production database without backup instructions
- Do NOT commit sensitive data (passwords, API keys, etc.)

---

**END OF DEBUG AGENT PROMPT**
