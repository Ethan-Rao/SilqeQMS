# DEV AGENT: Implementation Prompt
**Date:** February 8, 2026  
**Action:** Implement all fixes and push to main  
**Mode:** Autonomous - no user input required

---

## SUMMARY

Based on the system audit findings, implement these fixes:

1. **Add Supplies permissions** to init_db.py
2. **Update Supplies module** to use its own permissions instead of equipment.*
3. **Update Admin Dashboard template** to use supplies.view for Supplies card
4. **Add "My Account" card** to the dashboard (currently missing)
5. **Verify and commit** all changes

---

## TASK 1: Add Supplies Permissions to init_db.py

**File:** `scripts/init_db.py`

### 1.1 Add Permission Definitions

After line 99 (after manufacturing permissions), add:

```python
        # Supplies (P0)
        p_supplies_view = ensure_perm("supplies.view", "Supplies: view")
        p_supplies_create = ensure_perm("supplies.create", "Supplies: create")
        p_supplies_edit = ensure_perm("supplies.edit", "Supplies: edit")
        p_supplies_upload = ensure_perm("supplies.upload", "Supplies: upload documents")
```

### 1.2 Add to Admin Role

In the permissions tuple (around line 111-155), add these after `p_manufacturing_disposition`:

```python
            p_supplies_view,
            p_supplies_create,
            p_supplies_edit,
            p_supplies_upload,
```

---

## TASK 2: Update Supplies Admin Module

**File:** `app/eqms/modules/supplies/admin.py`

Replace ALL occurrences of equipment permissions with supplies permissions:

| Line | Current | Replace With |
|------|---------|--------------|
| 51 | `@require_permission("equipment.view")` | `@require_permission("supplies.view")` |
| 64 | `@require_permission("equipment.create")` | `@require_permission("supplies.create")` |
| 70 | `@require_permission("equipment.create")` | `@require_permission("supplies.create")` |
| 110 | `@require_permission("equipment.view")` | `@require_permission("supplies.view")` |
| 138 | `@require_permission("equipment.edit")` | `@require_permission("supplies.edit")` |
| 148 | `@require_permission("equipment.edit")` | `@require_permission("supplies.edit")` |
| 184 | `@require_permission("equipment.upload")` | `@require_permission("supplies.upload")` |
| 228 | `@require_permission("equipment.view")` | `@require_permission("supplies.view")` |
| 240 | `@require_permission("equipment.upload")` | `@require_permission("supplies.upload")` |
| 258 | `@require_permission("equipment.edit")` | `@require_permission("supplies.edit")` |
| 292 | `@require_permission("equipment.edit")` | `@require_permission("supplies.edit")` |

**Quick sed-like replacement:**
```python
# Replace all occurrences:
# "equipment.view" -> "supplies.view"
# "equipment.create" -> "supplies.create"
# "equipment.edit" -> "supplies.edit"
# "equipment.upload" -> "supplies.upload"
```

---

## TASK 3: Update Admin Dashboard Template

**File:** `app/eqms/templates/admin/index.html`

### 3.1 Fix Supplies Permission Check

Find (around line 69):
```html
{% if has_perm("equipment.view") %}
<a class="card card--link" href="{{ url_for('supplies.supplies_list') }}" style="padding: 20px;">
  <h3 style="margin: 0; font-size: 16px;">Supplies</h3>
```

Replace with:
```html
{% if has_perm("supplies.view") %}
<a class="card card--link" href="{{ url_for('supplies.supplies_list') }}" style="padding: 20px;">
  <h3 style="margin: 0; font-size: 16px;">Supplies</h3>
```

### 3.2 Add "My Account" Card

Add to the end of **Column 1 (Quality Management)**, after Admin Tools (around line 47):

```html
        <a class="card card--link" href="{{ url_for('admin.me') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">My Account</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Profile settings and preferences</p>
        </a>
```

**Note:** This card should NOT be wrapped in a permission check - all logged-in users should see their account.

---

## TASK 4: Verification

After making changes, verify:

### 4.1 Permissions in init_db.py
```bash
grep -n "supplies" scripts/init_db.py
```
Should show 8 lines (4 permission definitions + 4 role assignments).

### 4.2 Supplies admin permissions
```bash
grep -n "require_permission" app/eqms/modules/supplies/admin.py
```
All lines should show `supplies.*` permissions, NOT `equipment.*`.

### 4.3 Dashboard template
```bash
grep -n "supplies.view" app/eqms/templates/admin/index.html
```
Should show at least 1 match.

```bash
grep -n "admin.me" app/eqms/templates/admin/index.html
```
Should show 1 match (My Account card).

---

## TASK 5: Commit and Push

After all changes verified:

```bash
git add -A
git status

git commit -m "$(cat <<'EOF'
Add supplies permissions and fix RBAC

Permissions:
- Add supplies.view, supplies.create, supplies.edit, supplies.upload
- Update admin role to include supplies permissions

Supplies Module:
- Replace equipment.* permissions with supplies.* permissions
- All 11 routes now use correct supplies.* RBAC keys

Dashboard:
- Fix Supplies card to check supplies.view (was equipment.view)
- Add missing "My Account" card to Quality Management column

This ensures proper separation of concerns between Equipment and
Supplies modules, allowing distinct access control if needed.
EOF
)"

git push origin main
```

---

## COMPLETE FILE CHANGES

### File 1: `scripts/init_db.py`

After line 99 (after `p_manufacturing_disposition`), insert:

```python
        # Supplies (P0)
        p_supplies_view = ensure_perm("supplies.view", "Supplies: view")
        p_supplies_create = ensure_perm("supplies.create", "Supplies: create")
        p_supplies_edit = ensure_perm("supplies.edit", "Supplies: edit")
        p_supplies_upload = ensure_perm("supplies.upload", "Supplies: upload documents")
```

In the role permissions tuple (after `p_manufacturing_disposition,`), add:

```python
            p_supplies_view,
            p_supplies_create,
            p_supplies_edit,
            p_supplies_upload,
```

### File 2: `app/eqms/modules/supplies/admin.py`

Find and replace (all occurrences):
- `"equipment.view"` → `"supplies.view"`
- `"equipment.create"` → `"supplies.create"`
- `"equipment.edit"` → `"supplies.edit"`
- `"equipment.upload"` → `"supplies.upload"`

### File 3: `app/eqms/templates/admin/index.html`

1. Change line ~69 from `has_perm("equipment.view")` to `has_perm("supplies.view")`

2. Add My Account card after Admin Tools (inside Column 1, after line ~47):
```html
        <a class="card card--link" href="{{ url_for('admin.me') }}" style="padding: 20px;">
          <h3 style="margin: 0; font-size: 16px;">My Account</h3>
          <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Profile settings and preferences</p>
        </a>
```

---

## POST-DEPLOYMENT NOTE

After deployment, the new permissions will be added to the database on the next run of `init_db.py` (which happens during release). Existing admin users will automatically get the new supplies permissions because they're added to the admin role.

---

**END OF IMPLEMENTATION PROMPT**
