# Developer Agent Prompt: Equipment & Supplier Management Implementation

**Reference Spec:** [docs/planning/06_EQUIPMENT_AND_SUPPLIERS_SPEC.md](docs/planning/06_EQUIPMENT_AND_SUPPLIERS_SPEC.md)

---

## Task

Implement the Equipment module and Supplier Management enhancements as specified in `docs/planning/06_EQUIPMENT_AND_SUPPLIERS_SPEC.md`.

---

## Critical Requirements

### Code Quality & Organization

1. **Follow Existing Patterns:**
   - Use `app/eqms/modules/document_control/` as the reference pattern for module structure
   - Reuse existing primitives: `app/eqms/storage.py`, `app/eqms/audit.py`, `app/eqms/rbac.py`
   - Match naming conventions, file structure, and code style from existing modules

2. **No Legacy Code:**
   - Do NOT port any code from legacy systems unless explicitly specified in the spec
   - Do NOT add features beyond what's in the spec (no extra dashboards, analytics, or "nice-to-have" features)
   - Keep implementations minimal and focused on the spec requirements

3. **Clean Folder Structure:**
   - Create modules under `app/eqms/modules/equipment/` and `app/eqms/modules/suppliers/`
   - Each module should have: `__init__.py`, `models.py`, `admin.py`, `service.py`
   - Templates go in `app/eqms/templates/admin/equipment/` and `app/eqms/templates/admin/suppliers/`
   - Do NOT create top-level folders or files outside the module structure

4. **Storage Keys Must Be Deterministic:**
   - Equipment: `equipment/<equip_code>/<yyyy-mm-dd>/<sanitized_filename>`
   - Suppliers: `suppliers/<supplier_id>/<yyyy-mm-dd>/<sanitized_filename>`
   - Use `secure_filename()` from Werkzeug (already used in document_control)
   - Store canonical `storage_key` in DB (never trust user input for paths)

5. **Idempotent Import Scripts:**
   - Import script must be safe to re-run without creating duplicates
   - Use natural keys: `equip_code` for equipment, normalized `name` for suppliers
   - Check for existing records before inserting

---

## Implementation Order

Follow the dependency-ordered checklist in Section 8 of the spec:

1. **Models & Migrations** (Phase 1)
   - Create models first
   - Create migration
   - Test migration up/down

2. **Permissions & Seed** (Phase 2)
   - Add permissions to `scripts/init_db.py`
   - Test permissions seed

3. **Service Layer** (Phase 3)
   - Implement service functions (CRUD, document upload/download, associations)
   - Add validation helpers

4. **Routes/Controllers** (Phase 4)
   - Create blueprints and routes
   - Register blueprints in `app/eqms/__init__.py`
   - Add RBAC decorators

5. **Templates/UI** (Phase 5)
   - Create templates following existing design system
   - Update `admin/index.html` (PLM → Equipment, Suppliers link)

6. **Storage Integration** (Phase 6)
   - Implement storage key builders
   - Test with local and S3 backends

7. **Import Scripts** (Phase 7)
   - Create `scripts/import_equipment_and_suppliers.py`
   - Add dependencies: `openpyxl`, `python-docx` to `requirements.txt`

8. **Tests** (Phase 8)
   - Create smoke tests
   - Test permissions and audit trail

9. **Documentation** (Phase 9)
   - Update README.md (PLM → Equipment)
   - Update docs/03_MODULE_SPECS.md (PLM → Equipment)

---

## Key Implementation Details

### Models

- **Equipment:** Must have `equip_code` unique constraint
- **Suppliers:** Must have `name` (normalize for uniqueness checks)
- **EquipmentSupplier:** Unique constraint on `(equipment_id, supplier_id)`
- **ManagedDocument:** Polymorphic entity linkage (`entity_type` + `entity_id`)

### Storage

- Use `storage_from_config(current_app.config)` to get storage instance
- Build storage keys using helper functions (see spec Section 4)
- Never construct storage paths from user input directly

### Audit Trail

- Use `record_event()` from `app.eqms.audit` for all operations
- Include `reason=...` for controlled operations (edits, deletes, association removals)
- Log all document uploads/downloads/deletes

### Permissions

- Follow existing naming: `equipment.view`, `equipment.create`, `equipment.edit`, `equipment.upload`
- Same pattern for suppliers: `suppliers.view`, `suppliers.create`, `suppliers.edit`, `suppliers.upload`
- Grant all to `admin` role in `scripts/init_db.py`

### UI Patterns

- Reuse `_layout.html` base template
- Use `design-system.css` for styling
- Match existing admin UI patterns (cards, tables, forms)
- Keep it minimal - no extra charts, dashboards, or analytics

---

## Files to Create

**Equipment Module:**
- `app/eqms/modules/equipment/__init__.py`
- `app/eqms/modules/equipment/models.py`
- `app/eqms/modules/equipment/admin.py`
- `app/eqms/modules/equipment/service.py`
- `app/eqms/templates/admin/equipment/list.html`
- `app/eqms/templates/admin/equipment/detail.html`
- `app/eqms/templates/admin/equipment/edit.html`
- `app/eqms/templates/admin/equipment/new.html`

**Suppliers Module:**
- `app/eqms/modules/suppliers/__init__.py`
- `app/eqms/modules/suppliers/models.py`
- `app/eqms/modules/suppliers/admin.py`
- `app/eqms/modules/suppliers/service.py`
- `app/eqms/templates/admin/suppliers/list.html`
- `app/eqms/templates/admin/suppliers/detail.html`
- `app/eqms/templates/admin/suppliers/edit.html`
- `app/eqms/templates/admin/suppliers/new.html`

**Import Script:**
- `scripts/import_equipment_and_suppliers.py`

**Migration:**
- `migrations/versions/<revision>_add_equipment_and_suppliers.py` (generated by Alembic)

---

## Files to Modify

- `app/eqms/models.py` (add model imports at bottom)
- `app/eqms/__init__.py` (register blueprints)
- `scripts/init_db.py` (add permissions, grant to admin role)
- `app/eqms/templates/admin/index.html` (PLM → Equipment, Suppliers link)
- `README.md` (PLM → Equipment in module list)
- `docs/03_MODULE_SPECS.md` (PLM → Equipment section header)
- `requirements.txt` (add `openpyxl` and `python-docx` if not present)

---

## Validation Checklist

Before marking complete, verify:

- [ ] All models import without errors
- [ ] Migration runs: `alembic upgrade head` and `alembic downgrade -1`
- [ ] Permissions seeded: `python scripts/init_db.py` (check database)
- [ ] All routes require correct permissions (test with user missing permission → 403)
- [ ] Equipment list page loads and filters work
- [ ] Supplier list page loads and filters work
- [ ] Equipment detail page shows metadata, suppliers, documents
- [ ] Supplier detail page shows metadata, equipment, documents
- [ ] Document upload works (file appears in storage)
- [ ] Document download works (file downloads correctly)
- [ ] Equipment-supplier associations work (add/remove)
- [ ] Import script runs without errors and is idempotent
- [ ] Audit events logged for all operations
- [ ] Navigation updated (PLM → Equipment, Suppliers link works)
- [ ] No linter errors
- [ ] All acceptance criteria from spec Section 9 pass

---

## What NOT to Do

- ❌ Do NOT add features beyond the spec (no dashboards, analytics, charts)
- ❌ Do NOT port legacy code unless explicitly specified
- ❌ Do NOT create files outside the module structure
- ❌ Do NOT skip validation or error handling
- ❌ Do NOT hardcode storage paths (use storage abstraction)
- ❌ Do NOT forget to add RBAC decorators to routes
- ❌ Do NOT forget to log audit events
- ❌ Do NOT create duplicate associations (enforce unique constraint)

---

## Testing

After implementation:

1. **Manual Browser Tests:**
   - Create equipment → Upload document → Download document
   - Create supplier → Upload document → Download document
   - Associate equipment with supplier → Verify on both detail pages
   - Test filters on list pages
   - Test permissions (403 when missing permission)

2. **Import Script Test:**
   - Run import script → Verify equipment and suppliers created
   - Re-run import script → Verify idempotency (no duplicates)
   - Verify auto-linking (equipment mfg matches supplier name)

3. **Storage Test:**
   - Upload document with `STORAGE_BACKEND=local` → Verify file in `storage/` directory
   - If S3 configured: Upload document → Verify file in S3 bucket

---

## Questions?

If anything in the spec is unclear:
- Check existing modules (`document_control`, `rep_traceability`) for patterns
- Follow the spec exactly - it's the source of truth
- Keep it minimal - only implement what's specified

---

## Deliverables

When complete, you should have:
- ✅ Equipment module fully functional (CRUD, documents, associations)
- ✅ Supplier module fully functional (CRUD, documents, associations)
- ✅ Import script working (idempotent, auto-links equipment ↔ suppliers)
- ✅ All acceptance criteria passing
- ✅ Clean, organized code following existing patterns
- ✅ No legacy code or bloat

Begin with Phase 1 (Models & Migrations) and work through the checklist in order.
