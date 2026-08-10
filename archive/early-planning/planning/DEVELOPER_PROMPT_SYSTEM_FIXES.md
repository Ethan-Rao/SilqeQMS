# Developer Agent Prompt: System Fixes & Stabilization

**Reference Reports:**
- [docs/review/06_SYSTEM_DEBUG_AUDIT_REPORT.md](docs/review/06_SYSTEM_DEBUG_AUDIT_REPORT.md)
- [docs/review/SYSTEM_EVALUATION_REPORT.md](docs/review/SYSTEM_EVALUATION_REPORT.md)

---

## Task

Fix critical bugs, security issues, and UX problems identified in the system audit and evaluation reports. Prioritize blockers first, then high-severity issues.

---

## Critical Requirements

### Code Quality & Safety

1. **Follow Existing Patterns:**
   - Use `app/eqms/modules/document_control/` and `app/eqms/modules/rep_traceability/` as reference patterns
   - Match storage API usage: `storage_from_config(current_app.config)` and `storage.put_bytes()`/`storage.open()`
   - Match flash categories: `"danger"` and `"success"` (not `"error"` or `"warning"`)

2. **No New Dependencies:**
   - Do NOT add Flask-WTF or other heavy dependencies unless explicitly required
   - Keep fixes minimal and surgical

3. **Test After Each Fix:**
   - Verify the fix works before moving to the next item
   - Use manual browser tests or pytest where applicable

---

## Priority 1: Blockers (Must Fix Immediately)

### Fix 1: Manufacturing Storage API Mismatch (BLOCKER)

**Severity:** Blocker  
**Issue:** Manufacturing document upload/download uses non-existent storage API

**Files to Fix:**
- `app/eqms/modules/manufacturing/service.py` (line 373, 387)
- `app/eqms/modules/manufacturing/admin.py` (line 513, 515)

**Current (Broken) Code:**
```python
# service.py line 373
storage = storage_from_config()  # Missing config parameter

# service.py line 387
storage.put(storage_key, file_bytes, content_type=content_type)  # Method doesn't exist

# admin.py line 513
storage = storage_from_config()  # Missing config parameter

# admin.py line 515
data = storage.get(doc.storage_key)  # Method doesn't exist
```

**Fix:**
```python
# service.py - upload_lot_document()
from flask import current_app
storage = storage_from_config(current_app.config)
storage.put_bytes(storage_key, file_bytes, content_type=content_type)

# admin.py - suspension_document_download()
from flask import current_app
storage = storage_from_config(current_app.config)
fobj = storage.open(doc.storage_key)
return send_file(fobj, mimetype=doc.content_type, as_attachment=True, download_name=doc.original_filename, max_age=0)
```

**Reference Pattern:** See `app/eqms/modules/document_control/admin.py` lines 169-171 and 349-367

**Acceptance Test:**
- Create manufacturing lot → Upload document → Download document (200 OK)
- Verify file appears in storage at correct path
- Verify audit event `manufacturing.lot.document_upload` is logged

---

### Fix 2: Manufacturing Flash Categories Not Supported

**Severity:** High  
**Issue:** Manufacturing uses `"error"` and `"warning"` but CSS only supports `"danger"` and `"success"`

**File to Fix:**
- `app/eqms/modules/manufacturing/admin.py`

**Fix:**
- Replace all `flash(..., "error")` with `flash(..., "danger")`
- Replace all `flash(..., "warning")` with `flash(..., "danger")` (or add `flash--warning` CSS class if needed)

**Search Pattern:**
```bash
grep -n 'flash.*"error"\|flash.*"warning"' app/eqms/modules/manufacturing/admin.py
```

**Acceptance Test:**
- Trigger a validation error in manufacturing (e.g., invalid lot number)
- Verify flash message displays with red border (danger styling)

---

### Fix 3: Duplicate Manufacturing Card in Admin Index

**Severity:** Medium  
**Issue:** Manufacturing appears twice in admin index (real module + stub)

**File to Fix:**
- `app/eqms/templates/admin/index.html`

**Fix:**
- Remove the duplicate stub card (lines 35-37):
```html
<a class="card card--link" href="{{ url_for('admin.module_stub', module_key='manufacturing') }}">
  <h2>Manufacturing</h2>
</a>
```
- Keep only the real module card (lines 29-31)

**Acceptance Test:**
- Navigate to `/admin/`
- Verify "Manufacturing" appears only once
- Click it → Routes to `/admin/manufacturing` (real module)

---

## Priority 2: High-Severity Issues

### Fix 4: Distribution Log Customer Validation

**Severity:** Critical  
**Issue:** Distribution Log can link to non-existent customer_id, and facility_name not always overwritten

**Files to Fix:**
- `app/eqms/modules/rep_traceability/admin.py` (lines 126-138, and edit route)

**Current Code:**
```python
customer_id = normalize_text(payload.get("customer_id"))
if customer_id:
    c = s.query(Customer).filter(Customer.id == int(customer_id)).one_or_none()
    if not c:
        flash("Selected customer was not found. Please re-select and try again.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_new_get"))
    # ... continues with customer data
```

**Issue:** The validation exists but may not be enforced in edit route. Also, ensure facility_name is ALWAYS overwritten when customer_id is provided.

**Fix:**
- Verify edit route (`distribution_log_edit_post`) has same validation
- Ensure `facility_name` is ALWAYS set from customer record when `customer_id` is provided (even if customer.facility_name is None, set it explicitly)

**Acceptance Test:**
- Create customer "Test Hospital A"
- Create distribution entry with customer_id pointing to non-existent customer (e.g., 999)
- Verify entry is NOT created, error message shown
- Create distribution entry with valid customer_id
- Verify `facility_name` matches customer record exactly

---

### Fix 5: Equipment/Suppliers List Pagination

**Severity:** Medium  
**Issue:** Equipment and Suppliers list views use `.all()` without pagination

**Files to Fix:**
- `app/eqms/modules/equipment/admin.py` (line 71)
- `app/eqms/modules/suppliers/admin.py` (line 59)

**Current Code:**
```python
# equipment/admin.py
equipment = q.order_by(Equipment.equip_code.asc()).all()

# suppliers/admin.py
suppliers = q.order_by(Supplier.name.asc()).all()
```

**Fix:**
- Add pagination matching Distribution Log pattern (50 items per page)
- Add `page` query parameter handling
- Add `has_prev`/`has_next` flags
- Update templates to show pagination controls

**Reference Pattern:** See `app/eqms/modules/rep_traceability/admin.py` lines 52-73

**Acceptance Test:**
- Add 100+ equipment items
- Navigate to `/admin/equipment`
- Verify pagination controls appear (Next/Previous)
- Verify only 50 items per page shown

---

### Fix 6: Storage Key Sanitization Hardening

**Severity:** Medium  
**Issue:** Storage key builders don't fully protect against path traversal (`..` segments)

**Files to Fix:**
- `app/eqms/modules/manufacturing/service.py` (line 354-355)
- `app/eqms/modules/equipment/service.py` (if exists)
- `app/eqms/storage.py` (add defensive check in `LocalStorage._path`)

**Current Code:**
```python
# manufacturing/service.py
safe_lot = lot_number.replace("/", "_").replace("\\", "_").replace(" ", "_")
```

**Fix:**
1. **Manufacturing:** Apply `secure_filename()` to lot_number segment:
```python
from werkzeug.utils import secure_filename
safe_lot = secure_filename(lot_number.replace("/", "_").replace("\\", "_")) or "lot_unknown"
```

2. **LocalStorage defensive check:** Add to `app/eqms/storage.py::LocalStorage._path`:
```python
def _path(self, key: str) -> Path:
    safe_key = key.lstrip("/").replace("\\", "/")
    # Reject keys containing path traversal attempts
    if ".." in safe_key:
        raise StorageError(f"Invalid storage key (path traversal detected): {key}")
    return self.root / safe_key
```

**Acceptance Test:**
- Attempt to create lot with lot_number containing `../` or `..\\`
- Verify lot_number is sanitized (no `..` in storage key)
- Verify file upload succeeds and is stored in correct location

---

### Fix 7: README Migration Instructions Update

**Severity:** High  
**Issue:** README documents `RUN_MIGRATIONS_ON_START=1` but code disables it

**Files to Fix:**
- `README.md` (lines 146-162)

**Current State:**
- Code: `app/eqms/__init__.py` lines 33-38 explicitly disables migration-on-start
- README: Still documents the toggle as a fallback option

**Fix:**
- Update README to remove `RUN_MIGRATIONS_ON_START=1` guidance
- Clearly state: "Run migrations via `python scripts/release.py` in DO release step (preferred) or manually via DO console"
- Remove or update the "Fallback" section to match actual code behavior

**Acceptance Test:**
- README accurately reflects that migration-on-start is disabled
- README provides clear instructions for DO deployment

---

## Priority 3: Medium-Severity Issues

### Fix 8: Add MAX_CONTENT_LENGTH for File Uploads

**Severity:** Medium  
**Issue:** No file size limits on uploads (DoS risk)

**File to Fix:**
- `app/eqms/config.py`

**Fix:**
- Add `MAX_CONTENT_LENGTH` to config (e.g., 25MB = 25 * 1024 * 1024)
- Add error handler for 413 (Request Entity Too Large) with friendly flash message

**Code:**
```python
# config.py - load_config()
return {
    # ... existing config ...
    "MAX_CONTENT_LENGTH": 25 * 1024 * 1024,  # 25MB
}

# app/eqms/__init__.py - add error handler
@app.errorhandler(413)
def _err_413(e):
    flash("File too large. Maximum size is 25MB.", "danger")
    return redirect(request.referrer or url_for("admin.index")), 413
```

**Acceptance Test:**
- Attempt to upload file > 25MB
- Verify 413 error with friendly message
- Upload file < 25MB → succeeds

---

### Fix 9: Production Cookie Security (SESSION_COOKIE_SECURE)

**Severity:** Medium  
**Issue:** Session cookie not marked Secure in production

**File to Fix:**
- `app/eqms/config.py`

**Fix:**
```python
# config.py - load_config()
env = s.env
return {
    # ... existing config ...
    "SESSION_COOKIE_SECURE": env in ("prod", "production"),
}
```

**Acceptance Test:**
- Set `ENV=production` in .env
- Start server, login
- Check browser dev tools: session cookie has `Secure` flag
- Set `ENV=development`: cookie does NOT have `Secure` flag (for local HTTP)

---

### Fix 10: ShipStation Sync Hard Limits

**Severity:** Medium  
**Issue:** Sync can run indefinitely and block worker threads

**File to Fix:**
- `app/eqms/modules/shipstation_sync/service.py`

**Fix:**
- Add env-driven caps: `SHIPSTATION_MAX_PAGES` (default 50), `SHIPSTATION_MAX_ORDERS` (default 500)
- Check limits in `run_sync()` before each page/order iteration
- Stop gracefully when limit reached (log message, return run summary)

**Code:**
```python
# service.py - run_sync()
max_pages = int(os.environ.get("SHIPSTATION_MAX_PAGES", "50"))
max_orders = int(os.environ.get("SHIPSTATION_MAX_ORDERS", "500"))

for page in range(1, max_pages + 1):  # Use max_pages instead of hardcoded 51
    # ... fetch orders ...
    for o in orders:
        if orders_seen >= max_orders:
            break  # Stop if max orders reached
```

**Acceptance Test:**
- Set `SHIPSTATION_MAX_PAGES=5` and `SHIPSTATION_MAX_ORDERS=10`
- Run sync
- Verify sync stops after 5 pages or 10 orders (whichever comes first)
- Verify sync run record shows correct counts

---

## Priority 4: Cleanup & Maintenance

### Fix 11: Quarantine Legacy Code

**Severity:** High (maintenance risk)  
**Issue:** `legacy/` contains large prototype files with conflicting architecture

**Files to Handle:**
- `legacy/repqms_Proto1_reference.py.py`
- `legacy/repqms_shipstation_sync.py.py`

**Fix:**
- Create `legacy/_archive/` directory
- Move legacy files to `legacy/_archive/`
- Create `legacy/_archive/README.md`:
```markdown
# Legacy Archive

These files are **NOT imported** and **NOT supported**.

They are kept for historical reference only.

Do NOT copy code from these files into the main codebase.
```

**Acceptance Test:**
- Verify no imports reference legacy files: `grep -r "from legacy\|import legacy" app/`
- Application still runs after moving files
- Legacy files are clearly marked as archived

---

### Fix 12: Add Missing Tests

**Severity:** Medium  
**Issue:** Equipment, Suppliers, Manufacturing modules have no test coverage

**Files to Create:**
- `tests/test_equipment.py`
- `tests/test_suppliers.py`
- `tests/test_manufacturing.py`

**Minimal Test Coverage:**
- Create equipment/supplier/lot
- Upload document
- Download document
- Verify audit events logged

**Reference Pattern:** See `tests/test_rep_traceability.py`

**Acceptance Test:**
- Run `pytest -q tests/test_equipment.py tests/test_suppliers.py tests/test_manufacturing.py`
- All tests pass

---

## Implementation Order

1. **Fix 1** (Manufacturing Storage) - BLOCKER, do first
2. **Fix 2** (Flash Categories) - Quick win, do next
3. **Fix 3** (Duplicate Card) - Quick win, do next
4. **Fix 4** (Customer Validation) - Critical for data integrity
5. **Fix 5** (Pagination) - Performance issue
6. **Fix 6** (Storage Sanitization) - Security hardening
7. **Fix 7** (README Update) - Documentation accuracy
8. **Fix 8** (MAX_CONTENT_LENGTH) - Security/DoS prevention
9. **Fix 9** (Cookie Secure) - Security hardening
10. **Fix 10** (ShipStation Limits) - Reliability
11. **Fix 11** (Legacy Cleanup) - Maintenance
12. **Fix 12** (Tests) - Quality assurance

---

## Files to Modify

**Priority 1 (Blockers):**
- `app/eqms/modules/manufacturing/service.py`
- `app/eqms/modules/manufacturing/admin.py`
- `app/eqms/templates/admin/index.html`

**Priority 2 (High):**
- `app/eqms/modules/rep_traceability/admin.py`
- `app/eqms/modules/equipment/admin.py`
- `app/eqms/modules/suppliers/admin.py`
- `app/eqms/modules/manufacturing/service.py` (sanitization)
- `app/eqms/storage.py` (defensive check)
- `README.md`

**Priority 3 (Medium):**
- `app/eqms/config.py`
- `app/eqms/__init__.py` (error handler)
- `app/eqms/modules/shipstation_sync/service.py`

**Priority 4 (Cleanup):**
- Create `legacy/_archive/` directory
- Move legacy files
- Create `tests/test_equipment.py`, `tests/test_suppliers.py`, `tests/test_manufacturing.py`

---

## Validation Checklist

After each fix, verify:

- [ ] **Fix 1:** Manufacturing document upload/download works end-to-end
- [ ] **Fix 2:** Manufacturing flash messages display with correct styling
- [ ] **Fix 3:** Admin index shows Manufacturing only once
- [ ] **Fix 4:** Distribution Log rejects invalid customer_id, always overwrites facility_name
- [ ] **Fix 5:** Equipment/Suppliers lists paginate correctly (50 items per page)
- [ ] **Fix 6:** Storage keys are safe (no `..` traversal possible)
- [ ] **Fix 7:** README accurately reflects migration approach
- [ ] **Fix 8:** File uploads > 25MB are rejected with friendly error
- [ ] **Fix 9:** Production cookies have `Secure` flag
- [ ] **Fix 10:** ShipStation sync respects max limits
- [ ] **Fix 11:** Legacy files are archived, no imports reference them
- [ ] **Fix 12:** New tests pass (`pytest -q`)

---

## What NOT to Do

- ❌ Do NOT add Flask-WTF or other heavy dependencies for CSRF (defer to later if needed)
- ❌ Do NOT refactor beyond fixing the specific issues
- ❌ Do NOT change working code patterns (only fix broken/inconsistent code)
- ❌ Do NOT delete legacy files without archiving (keep for reference)

---

## Testing

After all fixes:

1. **Manual Browser Tests:**
   - Manufacturing: Create lot → Upload doc → Download doc (verify Fix 1)
   - Equipment: Create equipment → Upload doc → Download doc
   - Suppliers: Create supplier → Upload doc → Download doc
   - Distribution Log: Create entry with invalid customer_id → Verify error (Fix 4)
   - Equipment/Suppliers: Add 100+ items → Verify pagination (Fix 5)

2. **Security Tests:**
   - Attempt storage key with `../` → Verify rejection (Fix 6)
   - Upload file > 25MB → Verify 413 error (Fix 8)
   - Check production cookie has `Secure` flag (Fix 9)

3. **Pytest:**
   - Run `pytest -q tests/` (all tests pass, including new ones)

---

## Notes

- **Customer Profiles commits:** The evaluation report indicates missing commits, but code review shows `s.commit()` is present in all routes. Verify in production if issue persists.
- **Audit Trail UI:** The route exists in `app/eqms/admin.py` line 58. If 404 occurs, check blueprint registration.
- **RBAC redirect:** Code already redirects to login (line 26-31 in `rbac.py`). If 403 occurs after logout, verify `load_current_user()` is called before `require_permission()`.

---

## Deliverables

When complete, you should have:
- ✅ Manufacturing document upload/download working
- ✅ All flash messages use supported categories
- ✅ No duplicate navigation cards
- ✅ Customer validation enforced in Distribution Log
- ✅ Equipment/Suppliers lists paginated
- ✅ Storage keys hardened against path traversal
- ✅ README matches actual code behavior
- ✅ File size limits enforced
- ✅ Production cookies secured
- ✅ ShipStation sync has hard limits
- ✅ Legacy code archived
- ✅ Test coverage for new modules

Begin with Fix 1 (Manufacturing Storage) - it's a blocker that prevents core functionality.
