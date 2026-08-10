# DEV AGENT: Final System Preparation for Document Upload
**Date:** February 23, 2026  
**Priority:** HIGH  
**Objective:** Verify system is fully functional and ready for content upload

---

## CONTEXT

A deployment fix has just been pushed that resolves:
- SQLAlchemy backref conflict in `SupplySupplier.supplier` relationship (changed `backref` to `back_populates`)

The Purchasing module has been implemented by the previous debug agent and needs runtime verification.

---

## PHASE 1: VERIFY DEPLOYMENT SUCCESS

After the auto-deploy completes, verify the system is running:

1. Check the live site loads: `https://silqeqms.com/`
2. Verify admin login works: `https://silqeqms.com/admin/`
3. Confirm no 500 errors on the main dashboard

If deployment fails, check logs and report the specific error.

---

## PHASE 2: RUNTIME VERIFICATION OF ALL MODULES

Test each module by actually navigating to the routes (not just code review). Mark PASS or FAIL for each.

### 2.1 Quality Management Column

| Module | Route | Test |
|--------|-------|------|
| QMS Documents | `/admin/qms-documents` | Page loads (stub OK) |
| Document Control | `/admin/modules/document-control/` | List page loads |
| Employee Training | `/admin/employee-training` | Page loads (stub OK) |
| Management Reviews | `/admin/management-reviews` | Page loads (stub OK) |
| Admin Tools | `/admin/diagnostics` | Page loads |
| Reset Data | `/admin/reset-data` | Page loads, shows counts |
| Accounts | `/admin/accounts` | Page loads |
| My Account | `/admin/me` | Page loads |

### 2.2 Silq Operations Column

| Module | Route | Test |
|--------|-------|------|
| Manufacturing | `/admin/manufacturing/` | Index loads |
| Manufacturing - Suspension | `/admin/manufacturing/suspension` | List loads |
| Equipment | `/admin/equipment` | List loads |
| Equipment - New | `/admin/equipment/new` | Form loads |
| Equipment - Bulk Import | `/admin/equipment/bulk-import` | Page loads |
| Supplies | `/admin/supplies` | List loads |
| Supplies - New | `/admin/supplies/new` | Form loads |
| **Purchasing** | `/admin/purchasing` | List loads |
| **Purchasing - New** | `/admin/purchasing/new` | Form loads, shows suppliers |
| **Purchasing - Import** | `/admin/purchasing/import-pdf` | Page loads |
| NCRs | `/admin/ncrs` | Page loads (stub OK) |
| CAPAs | `/admin/capas` | Page loads (stub OK) |

### 2.3 External Relationships Column

| Module | Route | Test |
|--------|-------|------|
| Distribution Log | `/admin/distribution-log` | List loads |
| Sales Dashboard | `/admin/sales-dashboard` | Dashboard loads |
| Customers | `/admin/customers` | List loads |
| Suppliers | `/admin/suppliers` | List loads |
| Suppliers - New | `/admin/suppliers/new` | Form loads |
| NRE Projects | `/admin/nre-projects` | Page loads |

---

## PHASE 3: CRITICAL FUNCTIONALITY TESTS

These are the key workflows that must work for document upload:

### 3.1 Data Reset (CRITICAL)

1. Navigate to `/admin/reset-data`
2. Verify current counts display
3. Enable "Dry run only" checkbox
4. Type "DELETE ALL DATA"
5. Click "Reset Selected Data"
6. Verify dry run shows what would be deleted
7. **DO NOT run actual reset yet** - just verify the page works

### 3.2 Sales Order PDF Import

1. Navigate to `/admin/sales-orders/import-pdf`
2. Verify page loads without error
3. Verify file upload form appears

### 3.3 Equipment Bulk Import

1. Navigate to `/admin/equipment/bulk-import`
2. Verify page loads without error
3. Verify import instructions are clear

### 3.4 Purchasing Module (NEW)

1. Navigate to `/admin/purchasing`
2. Verify list page loads
3. Navigate to `/admin/purchasing/new`
4. Verify form displays with:
   - PO Number field
   - Order Date field
   - Supplier dropdown (populated from suppliers table)
   - Status dropdown
   - Description/Notes fields
5. Navigate to `/admin/purchasing/import-pdf`
6. Verify PDF import page loads

### 3.5 Supplier Creation

1. Navigate to `/admin/suppliers/new`
2. Verify form loads without error
3. Test creating a supplier with minimal data:
   - Name: "Test Supplier"
   - Status: "Pending"
4. Verify supplier appears in list
5. Delete the test supplier if created

---

## PHASE 4: FIX ANY ISSUES FOUND

If any tests fail, document the error and fix it. Common issues to check for:

1. **CSRF Token errors**: Ensure all forms use `{{ csrf_token }}` (not `{{ csrf_token() }}`)
2. **Missing permissions**: Check `scripts/init_db.py` has all permissions defined
3. **Template errors**: Check templates extend `_layout.html` correctly
4. **Missing routes**: Check blueprints are registered in `app/eqms/__init__.py`

---

## PHASE 5: COMMIT AND PUSH ANY FIXES

If you made any fixes:

```bash
git add -A
git status
git commit -m "Fix issues found during pre-upload verification"
git push origin main
```

---

## PHASE 6: OUTPUT VERIFICATION REPORT

Create a file at `docs/audits/UPLOAD_READINESS_2026_02_23.md` with this format:

```markdown
# Upload Readiness Report - 2026-02-23

## Deployment Status
- [ ] Deployment successful
- [ ] No runtime errors

## Module Verification

### Quality Management
- [ ] QMS Documents: PASS/FAIL
- [ ] Document Control: PASS/FAIL
- [ ] Employee Training: PASS/FAIL
- [ ] Management Reviews: PASS/FAIL
- [ ] Admin Tools: PASS/FAIL
- [ ] My Account: PASS/FAIL

### Silq Operations
- [ ] Manufacturing: PASS/FAIL
- [ ] Equipment: PASS/FAIL
- [ ] Equipment Bulk Import: PASS/FAIL
- [ ] Supplies: PASS/FAIL
- [ ] Purchasing: PASS/FAIL
- [ ] Purchasing Import: PASS/FAIL
- [ ] NCRs: PASS/FAIL
- [ ] CAPAs: PASS/FAIL

### External Relationships
- [ ] Distribution Log: PASS/FAIL
- [ ] Sales Dashboard: PASS/FAIL
- [ ] Customers: PASS/FAIL
- [ ] Suppliers: PASS/FAIL
- [ ] NRE Projects: PASS/FAIL

## Critical Functionality
- [ ] Data Reset (dry run): PASS/FAIL
- [ ] Sales Order PDF Import page: PASS/FAIL
- [ ] Equipment Bulk Import page: PASS/FAIL
- [ ] Purchasing Create: PASS/FAIL

## Issues Found
[List any issues and whether they were fixed]

## Ready for Upload
[ ] YES - System is ready for document upload
[ ] NO - Issues remain (list them)
```

---

## UPLOAD WORKFLOW (For User Reference)

Once the system is verified, the user can upload content in this order:

1. **Reset Data** (if needed): `/admin/reset-data`
2. **Create Suppliers**: `/admin/suppliers/new` (needed for equipment/supplies/purchasing)
3. **Import Equipment**: `/admin/equipment/bulk-import` (from Requirements Forms and Specs)
4. **Import Supplies**: Manual creation at `/admin/supplies/new`
5. **Import Sales Orders**: `/admin/sales-orders/import-pdf`
6. **ShipStation Sync**: `/admin/shipstation` → Run Full Sync
7. **Import Purchase Orders**: `/admin/purchasing/import-pdf`

---

## CRITICAL NOTES

1. **DO NOT reset production data** without explicit user confirmation
2. **Verify suppliers exist** before testing purchasing (PO creation needs suppliers)
3. **Check browser console** for JavaScript errors during testing
4. **Test in incognito** if you encounter caching issues

---

**END OF DEV AGENT PROMPT**
