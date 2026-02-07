# DEBUG AGENT PROMPT: Critical Migration Fix
**Date:** February 7, 2026  
**Priority:** CRITICAL - PRODUCTION DEPLOYMENT BLOCKED  
**Scope:** Fix Alembic migration head conflict

---

## CRITICAL ISSUE: DEPLOYMENT FAILURE

### Error Message (from DigitalOcean release logs)
```
Feb 07 22:08:24
 INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
Feb 07 22:08:24
 INFO  [alembic.runtime.migration] Will assume transactional DDL.
Feb 07 22:08:24
 Release failed: Multiple head revisions are present for given argument 'head'; 
 please specify a specific target revision, '<branchname>@head' to narrow to a 
 specific head, or 'heads' for all heads
Feb 07 22:08:57
 ERROR component terminated with non-zero exit code: 1
```

### Root Cause
The previous dev agent created migration `l2m3n4o5p6_shipstation_salesorder_redesign.py` with an **incorrect parent revision**.

**Current broken state:**
```
g1h2i3j4k5l6 (merge migration)
    │
    ├── h2i3j4k5l6m (create reps table)
    │       │
    │       └── i3j4k5l6m7 (add custom fields)
    │               │
    │               └── j4k5l6m7n8 (supplier contacts)
    │                       │
    │                       └── k1l2m3n4o5 (account management) ← HEAD #1
    │
    └── l2m3n4o5p6 (shipstation redesign) ← HEAD #2 (WRONG PARENT!)
```

The migration `l2m3n4o5p6` points to `g1h2i3j4k5l6` but should point to `k1l2m3n4o5`.

---

## FIX: SINGLE LINE CHANGE

### File to Edit
`migrations/versions/l2m3n4o5p6_shipstation_salesorder_redesign.py`

### Change Required (Line 15)
```python
# CURRENT (WRONG):
down_revision: Union[str, Sequence[str], None] = "g1h2i3j4k5l6"

# CHANGE TO:
down_revision: Union[str, Sequence[str], None] = "k1l2m3n4o5"
```

### Why This Works
This creates a linear migration chain:
```
... → j4k5l6m7n8 → k1l2m3n4o5 → l2m3n4o5p6 (single head)
```

---

## EXECUTION STEPS

### Step 1: Edit the Migration File
Open `migrations/versions/l2m3n4o5p6_shipstation_salesorder_redesign.py` and change line 15:
- FROM: `down_revision: Union[str, Sequence[str], None] = "g1h2i3j4k5l6"`
- TO: `down_revision: Union[str, Sequence[str], None] = "k1l2m3n4o5"`

### Step 2: Commit and Push
```bash
git add migrations/versions/l2m3n4o5p6_shipstation_salesorder_redesign.py
git commit -m "Fix migration head conflict - correct down_revision to k1l2m3n4o5"
git push origin main
```

### Step 3: Wait for Auto-Deploy
DigitalOcean will auto-deploy. The release phase will now succeed because there's only one migration head.

---

## VERIFICATION AFTER DEPLOYMENT

1. **Check the site loads:** Navigate to https://silqeqms.com/admin/
2. **Check NRE Projects:** Navigate to https://silqeqms.com/admin/nre-projects/
3. **Check login works:** Log in with admin credentials

---

## IF THE MIGRATION ALREADY RAN PARTIALLY ON PRODUCTION

If the `alembic upgrade head` was run manually in the DO console and only one branch was applied, you may need to:

1. Check current revision: `alembic current`
2. If at `k1l2m3n4o5`, run: `alembic upgrade l2m3n4o5p6` (after fixing the down_revision)
3. If at `l2m3n4o5p6`, no further action needed after fixing

---

## ADDITIONAL SYSTEM CHECKS (VERIFY BUT LIKELY ALREADY WORKING)

### NRE Module Files (CONFIRMED EXIST)
These files exist and should work:
- ✅ `app/eqms/modules/nre_projects/__init__.py`
- ✅ `app/eqms/modules/nre_projects/admin.py`
- ✅ `app/eqms/templates/admin/nre_projects/index.html`
- ✅ `app/eqms/templates/admin/nre_projects/detail.html`

### Customer Code Field (FROM MIGRATION)
The migration `l2m3n4o5p6` adds:
- `customer_code` column to `customers` table
- Index `idx_customers_customer_code`
- Drops SKU check constraint from `sales_order_lines`

These changes will apply once the migration runs successfully.

---

## SUMMARY

| Item | Status | Action |
|------|--------|--------|
| Migration head conflict | ❌ BROKEN | Fix down_revision in l2m3n4o5p6 |
| NRE module code | ✅ EXISTS | Verify after deploy |
| Customer code logic | ✅ EXISTS | Verify after migration runs |
| All other systems | ✅ OK | No changes needed |

---

## EXPECTED OUTCOME

After fixing the migration and pushing:
1. DigitalOcean auto-deploy succeeds
2. Migration `l2m3n4o5p6` applies (adds customer_code, removes SKU constraint)
3. Site works normally
4. NRE Projects page accessible at `/admin/nre-projects/`

---

**END OF DEBUG AGENT PROMPT**
