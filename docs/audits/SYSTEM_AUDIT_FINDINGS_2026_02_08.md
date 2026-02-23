# System Audit Findings - 2026-02-08

## Critical Issues (Must Fix)
None found in this pass. The previously reported `csrf_token()` template bug is not present in the current templates (no matches in `app/eqms/templates`).

## High Priority Issues
1. **Supplies module uses equipment permissions**
   - Location: `app/eqms/modules/supplies/admin.py`
   - Impact: RBAC may unintentionally grant/deny supplies access based on equipment permissions.
   - Fix: Confirm intended permissions. If supplies should be distinct, replace `equipment.*` with `supplies.*` and update roles/permissions accordingly.

2. **Local Alembic verification could not be run**
   - Location: Local tooling
   - Impact: Unable to confirm migration head state from this environment.
   - Fix: Install Alembic in the runtime (`pip install -r requirements.txt`) and run `alembic heads`.

## Medium Priority Issues
1. **Templates without `{% extends %}`**
   - Location: `app/eqms/templates/_layout.html`, `app/eqms/templates/admin/_notes_modal_content.html`
   - Impact: None. These are expected base/partial templates.
   - Fix: None required.

## Low Priority / Cleanup
1. **Search tools missing in shell**
   - Location: Local tooling (`rg` not available)
   - Impact: Slower audits and inconsistent verification.
   - Fix: Install ripgrep if desired for local audits.

## Modules Status
| Module | Status | Notes |
|--------|--------|-------|
| Core (`app/eqms/`) | OK | Blueprints registered; CSRF guard in place |
| Customer Profiles | OK | Models/admin/service present |
| Rep Traceability | OK | Parser/service/admin present |
| ShipStation Sync | OK | Models/admin/service present |
| Equipment | OK | Models/admin/service/parser present |
| Supplies | OK (RBAC review) | Uses equipment permissions |
| Suppliers | OK | Models/admin/service present |
| Manufacturing | OK | Models/admin/service present |
| NRE Projects | OK | Templates and admin routes present |
| Document Control | OK | Templates and admin routes present |

## Recommendations
1. Decide whether Supplies should have distinct RBAC keys and update permissions accordingly.
2. Re-run Alembic checks (`alembic heads`, `alembic current`) in a fully provisioned environment.
3. Keep CSRF token usage as string (`{{ csrf_token }}`) across templates; re-scan if new templates are added.
