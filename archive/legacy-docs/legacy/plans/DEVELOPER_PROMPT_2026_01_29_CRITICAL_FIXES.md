# Developer Agent Prompt: Critical Fixes & UI Improvements

**Date:** 2026-01-29  
**Priority:** P0 - Critical functionality is broken  
**Focus:** Customer Profile Bugs, Rep System Overhaul, Sales Dashboard Polish, Distribution Details UX

---

## Executive Summary

This prompt addresses **critical bugs** preventing core functionality from working, plus UI/UX improvements identified in the latest system audit. The customer profile pages are completely broken due to a code structure bug. Additionally, the Rep system needs to be decoupled from User accounts, and several UI polish items are required.

---

## CRITICAL BUG #1: Customer Profile Edit Form Does Not Save (P0)

### Symptom
- Clicking "Save Changes" on the customer Edit tab does nothing
- No error message appears
- Customer data is not updated
- Internal Server Error occurs when switching tabs

### Root Cause
**File:** `app/eqms/modules/customer_profiles/admin.py`

The `customer_update_post()` function at line 432-447 is **incomplete** - it returns nothing after validating the reason. The actual update logic (lines 495-527) is **dead code** that appears AFTER the `customer_reps_update()` function's return statement.

```python
# Current broken code structure (lines 432-493):
@bp.post("/customers/<int:customer_id>")
def customer_update_post(customer_id: int):
    ...
    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for change is required.", "danger")
        return redirect(...)
    # FUNCTION ENDS HERE - NO UPDATE LOGIC!


@bp.post("/customers/<int:customer_id>/reps")
def customer_reps_update(customer_id: int):
    ...
    return redirect(...)  # <-- This return ends customer_reps_update

    # DEAD CODE BELOW - This is orphaned and never executes!
    payload = {...}
    errs = validate_customer_payload(payload)
    ...
    update_customer(s, c, payload, user=u, reason=reason)
```

### Fix Required
Move the dead code (lines 495-527) back into `customer_update_post()` function:

```python
@bp.post("/customers/<int:customer_id>")
@require_permission("customers.edit")
def customer_update_post(customer_id: int):
    s = db_session()
    u = _current_user()
    c = get_customer_by_id(s, customer_id)
    if not c:
        flash("Customer not found.", "danger")
        return redirect(url_for("customer_profiles.customers_list"))

    reason = (request.form.get("reason") or "").strip()
    if not reason:
        flash("Reason for change is required.", "danger")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id, tab="edit"))

    # === ADD THIS BLOCK (moved from dead code) ===
    payload = {
        "facility_name": request.form.get("facility_name"),
        "address1": request.form.get("address1"),
        "address2": request.form.get("address2"),
        "city": request.form.get("city"),
        "state": request.form.get("state"),
        "zip": request.form.get("zip"),
        "contact_name": request.form.get("contact_name"),
        "contact_phone": request.form.get("contact_phone"),
        "contact_email": request.form.get("contact_email"),
        "primary_rep_id": request.form.get("primary_rep_id"),
    }
    errs = validate_customer_payload(payload)
    if errs:
        flash("; ".join([f"{e.field}: {e.message}" for e in errs]), "danger")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id, tab="edit"))

    # Validate primary rep if provided
    if (payload.get("primary_rep_id") or "").strip():
        try:
            rep_id = int(payload["primary_rep_id"])
            # Check Rep table instead of User table (see Rep System changes below)
            from app.eqms.modules.customer_profiles.models import Rep
            rep = s.query(Rep).filter(Rep.id == rep_id, Rep.is_active.is_(True)).one_or_none()
            if not rep:
                flash("Rep not found or inactive.", "danger")
                return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id, tab="edit"))
        except ValueError:
            flash("Invalid rep ID.", "danger")
            return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id, tab="edit"))

    try:
        update_customer(s, c, payload, user=u, reason=reason)
        s.commit()
        flash("Customer updated.", "success")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id))
    except Exception as e:
        s.rollback()
        flash(str(e), "danger")
        return redirect(url_for("customer_profiles.customer_detail", customer_id=c.id, tab="edit"))
```

Also **delete the orphaned dead code** (lines 495-527) that follows `customer_reps_update()`.

### Verification
1. Go to `/admin/customers/{id}?tab=edit`
2. Change any field (e.g., city)
3. Enter reason "Test update"
4. Click "Save Changes"
5. ✅ Flash message "Customer updated." appears
6. ✅ Changes are persisted

---

## CRITICAL BUG #2: Rep System Overhaul (P0)

### Problem
Reps are currently tied to User accounts (`users.id`). This is wrong because:
- Reps will never log into or use this system
- Reps are just names for assignment tracking
- Creating a rep requires creating a full User account (unnecessary complexity)

### Required Changes

#### 1. Create New `Rep` Model

**File:** `app/eqms/modules/customer_profiles/models.py`

Add after the existing models:

```python
class Rep(Base):
    """
    Simple rep entity for assignment tracking.
    Reps do NOT log into the system - they are just names/identifiers.
    """
    __tablename__ = "reps"
    __table_args__ = (
        Index("idx_reps_name", "name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)  # Optional, for reference only
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)  # Optional
    territory: Mapped[str | None] = mapped_column(Text, nullable=True)  # Optional, e.g., "West Coast"
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)

    # Assignments
    customer_assignments: Mapped[list["CustomerRep"]] = relationship(
        "CustomerRep",
        back_populates="rep",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
```

#### 2. Update `CustomerRep` Model

Change the `rep_id` foreign key to point to the new `reps` table:

```python
class CustomerRep(Base):
    __tablename__ = "customer_reps"
    ...
    rep_id: Mapped[int] = mapped_column(ForeignKey("reps.id", ondelete="CASCADE"), nullable=False)  # Changed from users.id
    ...
    rep: Mapped["Rep"] = relationship("Rep", back_populates="customer_assignments", lazy="selectin")  # Changed type
```

#### 3. Update `Customer` Model

Change `primary_rep_id` to reference the new `reps` table:

```python
class Customer(Base):
    ...
    primary_rep_id: Mapped[int | None] = mapped_column(ForeignKey("reps.id", ondelete="SET NULL"), nullable=True)  # Changed from users.id
    primary_rep = relationship("Rep", foreign_keys=[primary_rep_id], lazy="selectin")  # Changed type
```

#### 4. Update `DistributionLogEntry` Model

**File:** `app/eqms/modules/rep_traceability/models.py`

If there's a `rep_id` field, update it to reference `reps.id`:

```python
rep_id: Mapped[int | None] = mapped_column(ForeignKey("reps.id", ondelete="SET NULL"), nullable=True)
```

#### 5. Create Alembic Migration

**File:** `migrations/versions/xxxx_create_reps_table.py`

```python
"""Create reps table and migrate rep references

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Create reps table
    op.create_table(
        'reps',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('email', sa.Text(), nullable=True),
        sa.Column('phone', sa.Text(), nullable=True),
        sa.Column('territory', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('idx_reps_name', 'reps', ['name'])
    
    # 2. Migrate existing user-based reps to new table
    # Insert unique users who are referenced as reps
    op.execute("""
        INSERT INTO reps (name, email, is_active, created_at, updated_at)
        SELECT DISTINCT u.email, u.email, u.is_active, NOW(), NOW()
        FROM users u
        WHERE u.id IN (
            SELECT DISTINCT primary_rep_id FROM customers WHERE primary_rep_id IS NOT NULL
            UNION
            SELECT DISTINCT rep_id FROM customer_reps WHERE rep_id IS NOT NULL
        )
    """)
    
    # 3. Create mapping table for migration
    # This is a temporary step - in production, manually verify the mapping
    
    # 4. Update foreign keys (run manually after verifying data)
    # Note: This requires careful data migration - see migration notes below

def downgrade():
    op.drop_index('idx_reps_name', table_name='reps')
    op.drop_table('reps')
```

**IMPORTANT:** Due to existing data, run migration in steps:
1. Create `reps` table
2. Migrate existing rep data (users who are assigned as reps)
3. Create new FK columns with different names temporarily
4. Copy data
5. Drop old FK columns
6. Rename new columns

#### 6. Add Rep Admin Routes

**File:** `app/eqms/modules/customer_profiles/admin.py`

Add new routes for rep management:

```python
# ============================================================================
# Rep Management (Simple CRUD)
# ============================================================================

@bp.get("/reps")
@require_permission("customers.view")
def reps_list():
    s = db_session()
    reps = s.query(Rep).order_by(Rep.name.asc()).all()
    return render_template("admin/reps/list.html", reps=reps)


@bp.get("/reps/new")
@require_permission("customers.edit")
def reps_new_get():
    return render_template("admin/reps/edit.html", rep=None)


@bp.post("/reps/new")
@require_permission("customers.edit")
def reps_new_post():
    s = db_session()
    u = _current_user()
    
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Rep name is required.", "danger")
        return redirect(url_for("customer_profiles.reps_new_get"))
    
    rep = Rep(
        name=name,
        email=(request.form.get("email") or "").strip() or None,
        phone=(request.form.get("phone") or "").strip() or None,
        territory=(request.form.get("territory") or "").strip() or None,
        is_active=True,
    )
    s.add(rep)
    
    from app.eqms.audit import record_event
    record_event(s, actor=u, action="rep.create", entity_type="Rep", entity_id="new", metadata={"name": name})
    
    s.commit()
    flash(f"Rep '{name}' created.", "success")
    return redirect(url_for("customer_profiles.reps_list"))


@bp.get("/reps/<int:rep_id>/edit")
@require_permission("customers.edit")
def reps_edit_get(rep_id: int):
    s = db_session()
    rep = s.query(Rep).filter(Rep.id == rep_id).one_or_none()
    if not rep:
        flash("Rep not found.", "danger")
        return redirect(url_for("customer_profiles.reps_list"))
    return render_template("admin/reps/edit.html", rep=rep)


@bp.post("/reps/<int:rep_id>/edit")
@require_permission("customers.edit")
def reps_edit_post(rep_id: int):
    s = db_session()
    u = _current_user()
    rep = s.query(Rep).filter(Rep.id == rep_id).one_or_none()
    if not rep:
        flash("Rep not found.", "danger")
        return redirect(url_for("customer_profiles.reps_list"))
    
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Rep name is required.", "danger")
        return redirect(url_for("customer_profiles.reps_edit_get", rep_id=rep_id))
    
    rep.name = name
    rep.email = (request.form.get("email") or "").strip() or None
    rep.phone = (request.form.get("phone") or "").strip() or None
    rep.territory = (request.form.get("territory") or "").strip() or None
    rep.is_active = request.form.get("is_active") == "1"
    rep.updated_at = datetime.utcnow()
    
    from app.eqms.audit import record_event
    record_event(s, actor=u, action="rep.update", entity_type="Rep", entity_id=str(rep_id), metadata={"name": name})
    
    s.commit()
    flash(f"Rep '{name}' updated.", "success")
    return redirect(url_for("customer_profiles.reps_list"))
```

#### 7. Create Rep Templates

**File:** `app/eqms/templates/admin/reps/list.html`

```html
{% extends "_layout.html" %}
{% block title %}Reps{% endblock %}
{% block content %}
  <div class="card">
    <div style="display:flex; justify-content:space-between; gap:12px; align-items:center;">
      <h1 style="margin:0;">Reps</h1>
      <a class="button" href="{{ url_for('customer_profiles.reps_new_get') }}">+ Add Rep</a>
    </div>
  </div>
  
  <div style="height:14px;"></div>
  
  <div class="card">
    {% if reps %}
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border);">Name</th>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border);">Territory</th>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border);">Email</th>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border);">Status</th>
            <th style="text-align:center; padding:10px 12px; border-bottom:1px solid var(--border);">Actions</th>
          </tr>
        </thead>
        <tbody>
          {% for rep in reps %}
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
              <td style="padding:10px 12px; font-weight:500;">{{ rep.name|e }}</td>
              <td style="padding:10px 12px;">{{ rep.territory or '—' }}</td>
              <td style="padding:10px 12px;">{{ rep.email or '—' }}</td>
              <td style="padding:10px 12px;">
                {% if rep.is_active %}
                  <span style="color:var(--success);">Active</span>
                {% else %}
                  <span class="muted">Inactive</span>
                {% endif %}
              </td>
              <td style="padding:10px 12px; text-align:center;">
                <a href="{{ url_for('customer_profiles.reps_edit_get', rep_id=rep.id) }}" class="button button--secondary" style="font-size:12px; padding:4px 10px;">Edit</a>
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    {% else %}
      <p class="muted" style="text-align:center; padding:40px;">No reps yet. Click "+ Add Rep" to create one.</p>
    {% endif %}
  </div>
{% endblock %}
```

**File:** `app/eqms/templates/admin/reps/edit.html`

```html
{% extends "_layout.html" %}
{% if rep %}{% set page_title = "Edit Rep" %}{% else %}{% set page_title = "New Rep" %}{% endif %}
{% block title %}{{ page_title }}{% endblock %}
{% block content %}
  <div class="card">
    <div style="display:flex; justify-content:space-between; gap:12px; align-items:center;">
      <h1 style="margin:0;">{{ page_title }}</h1>
      <a class="button button--secondary" href="{{ url_for('customer_profiles.reps_list') }}">← Back to List</a>
    </div>
  </div>
  
  <div style="height:14px;"></div>
  
  <div class="card">
    <form class="form" method="post" style="max-width:500px;">
      <div>
        <div class="label">Name *</div>
        <input name="name" required value="{{ rep.name|e if rep else '' }}" placeholder="e.g., John Smith" />
      </div>
      <div>
        <div class="label">Territory</div>
        <input name="territory" value="{{ rep.territory|e if rep and rep.territory else '' }}" placeholder="e.g., West Coast" />
      </div>
      <div>
        <div class="label">Email (optional)</div>
        <input type="email" name="email" value="{{ rep.email|e if rep and rep.email else '' }}" placeholder="For reference only" />
      </div>
      <div>
        <div class="label">Phone (optional)</div>
        <input name="phone" value="{{ rep.phone|e if rep and rep.phone else '' }}" />
      </div>
      {% if rep %}
        <div>
          <label style="display:flex; align-items:center; gap:8px; cursor:pointer;">
            <input type="checkbox" name="is_active" value="1" {% if rep.is_active %}checked{% endif %} />
            <span>Active</span>
          </label>
        </div>
      {% endif %}
      <button class="button" type="submit">{% if rep %}Save Changes{% else %}Create Rep{% endif %}</button>
    </form>
  </div>
{% endblock %}
```

#### 8. Add Rep Assignment to Detail Views

On customer profile detail views and distribution log detail modals, add a dropdown to assign reps directly from the detail view. This should be a simple select dropdown that updates via AJAX or form submission.

Add to customer detail Edit tab (replace the current multi-select for reps):

```html
<div>
  <div class="label">Assigned Rep</div>
  <select name="primary_rep_id" style="width:100%; ...">
    <option value="">(None)</option>
    {% for r in reps %}
      <option value="{{ r.id }}" {% if customer.primary_rep_id == r.id %}selected{% endif %}>{{ r.name }}</option>
    {% endfor %}
  </select>
</div>
```

#### 9. Update All Templates Using Reps

Update all places that display `r.email` to display `r.name`:
- `admin/customers/detail.html` - lines 106-112, 416-420, 480-484
- `admin/customers/list.html` - rep filter dropdown
- `admin/distribution_log/list.html` - rep filter (line 44-46)
- `admin/distribution_log/edit.html` - rep dropdown if exists

---

## P1: Sales Dashboard Polish

### Issue 1: Remove "All Time" Wording

**File:** `app/eqms/templates/admin/sales_dashboard/index.html`

Change lines 28-31:

```html
<!-- BEFORE -->
<div class="muted" style="font-size:12px; ...">Total Units (All Time)</div>
<div style="font-size:32px; ...">{{ stats.total_units_all_time }}</div>
<div class="muted" style="font-size:11px;">all time</div>

<!-- AFTER -->
<div class="muted" style="font-size:12px; ...">Total Units</div>
<div style="font-size:32px; ...">{{ stats.total_units_all_time }}</div>
<!-- Remove the subtitle entirely -->
```

### Issue 2: Remove All Subtitles

Remove the subtitle `<div class="muted" style="font-size:11px;">...</div>` from ALL metric cards (lines 30, 35, 40, 45, 50).

**Before:**
```html
<div class="muted" style="font-size:11px;">all time</div>
<div class="muted" style="font-size:11px;">distinct orders</div>
<div class="muted" style="font-size:11px;">unique facilities</div>
<div class="muted" style="font-size:11px;">new customers</div>
<div class="muted" style="font-size:11px;">returning customers</div>
```

**After:** Delete all these lines entirely.

### Issue 3: Sales by SKU Should Show Percentages

**File:** `app/eqms/templates/admin/sales_dashboard/index.html`

Update the SKU breakdown table (lines 148-165):

```html
{% if sku_breakdown %}
  {% set total_sku_units = sku_breakdown|sum(attribute='units') %}
  <div style="overflow-x:auto;">
    <table style="width:100%; border-collapse:collapse;">
      <thead>
        <tr>
          <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">SKU</th>
          <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">%</th>
        </tr>
      </thead>
      <tbody>
        {% for row in sku_breakdown %}
          {% set pct = ((row.units / total_sku_units) * 100)|round(1) if total_sku_units > 0 else 0 %}
          <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:10px 12px;"><code style="background:rgba(255,255,255,0.05); padding:2px 6px; border-radius:4px;">{{ row.sku|e }}</code></td>
            <td style="padding:10px 12px; text-align:right; font-weight:600;">{{ pct }}%</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
{% else %}
  <p class="muted">No SKU data in selected window.</p>
{% endif %}
```

---

## P1: Distribution Details Modal - Two Column Layout

### Problem
The distribution details modal has important info (SKUs, Lots, Qtys, Files) at the bottom. Users want this info prominent at the top in a two-column layout.

### Fix

**File:** `app/eqms/templates/admin/distribution_log/list.html`

Reorganize the modal content JS (lines 238-450) to use two columns:

```javascript
let html = `
  <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
    <!-- LEFT COLUMN: Primary Info (SKUs, Lots, Files) -->
    <div>
      <section>
        <div class="section-header">Distribution Lines</div>
        ${lineItems.length ? `
          <table class="table" style="font-size:13px;">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Lot</th>
                <th style="text-align:right;">Qty</th>
              </tr>
            </thead>
            <tbody>
              ${lineItems.map(l => `
                <tr>
                  <td><code>${l.sku || '—'}</code></td>
                  <td><code>${l.lot_corrected || l.lot_number || '—'}</code></td>
                  <td style="text-align:right; font-weight:600;">${l.quantity || 0}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        ` : `
          <div style="display:grid; grid-template-columns: auto 1fr; gap:4px 12px;">
            <div class="field-label">SKU</div><div class="field-value"><code>${data.entry.sku || '—'}</code></div>
            <div class="field-label">Lot</div><div class="field-value"><code>${data.entry.lot_number || '—'}</code></div>
            <div class="field-label">Qty</div><div class="field-value" style="font-weight:600;">${data.entry.quantity || 0}</div>
          </div>
        `}
      </section>
      
      <section>
        <div class="section-header">File Attachments</div>
        <div style="display:flex; flex-direction:column; gap:12px;">
          <div style="padding:12px; border:1px solid var(--border); border-radius:8px;">
            <div style="font-weight:600; margin-bottom:6px;">📄 Sales Order PDF</div>
            ${soPdf ? `
              <div style="color:#10b981;">✅ Uploaded</div>
              <a class="button button--secondary" style="font-size:11px; padding:4px 8px; margin-top:8px;" href="${soPdf.download_url}">Download</a>
            ` : `
              <div style="color:#f59e0b;">⚠️ Not Uploaded</div>
            `}
          </div>
          <div style="padding:12px; border:1px solid var(--border); border-radius:8px;">
            <div style="font-weight:600; margin-bottom:6px;">📦 Delivery Label</div>
            ${labelPdf ? `
              <div style="color:#10b981;">✅ Uploaded</div>
              <a class="button button--secondary" style="font-size:11px; padding:4px 8px; margin-top:8px;" href="${labelPdf.download_url}">Download</a>
            ` : `
              <div style="color:#f59e0b;">⚠️ Not Uploaded</div>
            `}
          </div>
        </div>
      </section>
    </div>
    
    <!-- RIGHT COLUMN: Distribution & Customer Info -->
    <div>
      <section>
        <div class="section-header">Distribution Entry</div>
        <div style="display:grid; grid-template-columns: auto 1fr; gap:4px 12px;">
          <div class="field-label">Ship Date</div><div class="field-value">${data.entry.ship_date || '—'}</div>
          <div class="field-label">Order #</div><div class="field-value"><code>${data.entry.order_number || '—'}</code></div>
          <div class="field-label">Facility</div><div class="field-value">${data.entry.facility_name || '—'}</div>
          <div class="field-label">Source</div><div class="field-value">${data.entry.source}</div>
          <div class="field-label">Tracking</div><div class="field-value">${data.entry.tracking_number || '—'}</div>
        </div>
      </section>
      
      ${data.customer ? `
        <section>
          <div class="section-header">Customer</div>
          <a href="/admin/customers/${data.customer.id}" style="font-weight:600;">${data.customer.facility_name}</a>
          <div class="muted" style="font-size:12px;">${data.customer.city || ''} ${data.customer.state || ''}</div>
          ${data.customer_stats ? `
            <div style="margin-top:12px; display:grid; grid-template-columns: auto 1fr; gap:4px 12px; font-size:13px;">
              <div class="field-label">Orders</div><div class="field-value">${data.customer_stats.total_orders}</div>
              <div class="field-label">Units</div><div class="field-value">${data.customer_stats.total_units}</div>
            </div>
          ` : ''}
        </section>
      ` : ''}
      
      <section>
        <div class="section-header">Rep Assignment</div>
        <div>${data.entry.rep_name || 'Not assigned'}</div>
        <!-- Add quick-assign dropdown here if desired -->
      </section>
    </div>
  </div>
`;
```

---

## P1: Lot Tracking Filter Fix

### Problem
Lot tracking shows "(2026)" in the header but should show lots from 2025+.

### Fix

**File:** `app/eqms/modules/rep_traceability/service.py`

Change line 799:
```python
# BEFORE
min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2026"))

# AFTER  
min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2025"))
```

Also update the template header:

**File:** `app/eqms/templates/admin/sales_dashboard/index.html` line 173:

```html
<!-- BEFORE -->
<h2 style="margin-top:0; font-size:16px;">Lot Tracking{% if lot_min_year %} ({{ lot_min_year }}+){% endif %}</h2>

<!-- AFTER - Remove year display entirely or show "Since 2025" -->
<h2 style="margin-top:0; font-size:16px;">Lot Tracking</h2>
```

---

## P2: Equipment & Suppliers Alignment

### Problem
Equipment and Suppliers are related via `EquipmentSupplier` join table, but:
- Supplier profile pages don't show associated equipment
- The relationship should be displayed bidirectionally

### Fix

**File:** `app/eqms/templates/admin/suppliers/detail.html`

Add a section to show associated equipment:

```html
<!-- Add after existing supplier details -->
<div style="height:14px;"></div>
<div class="card">
  <h2 style="margin-top:0; font-size:16px;">Associated Equipment</h2>
  {% if supplier.equipment_associations %}
    <table style="width:100%; border-collapse:collapse;">
      <thead>
        <tr>
          <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border);">Equipment Code</th>
          <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border);">Description</th>
          <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border);">Relationship</th>
        </tr>
      </thead>
      <tbody>
        {% for assoc in supplier.equipment_associations %}
          <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:10px 12px;">
              <a href="{{ url_for('equipment.equipment_detail', equipment_id=assoc.equipment.id) }}">
                <code>{{ assoc.equipment.equip_code|e }}</code>
              </a>
            </td>
            <td style="padding:10px 12px;">{{ assoc.equipment.description or '—' }}</td>
            <td style="padding:10px 12px;">{{ assoc.relationship_type or '—' }}</td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
  {% else %}
    <p class="muted">No equipment associated with this supplier.</p>
  {% endif %}
</div>
```

Ensure the `Supplier` model has `equipment_associations` relationship loaded (already exists in models.py).

---

## P2: Legacy Code Cleanup

### Files/Code to Review and Potentially Remove

1. **`eqms_starter/` folder** - This appears to be a template/scaffold that's no longer needed. Verify it's not used and delete.

2. **`app/eqms/modules/document_control/`** - Check if this module is actually used. If not, remove or mark for future implementation.

3. **Dead code in `customer_profiles/admin.py`** - Lines 495-527 are orphaned (see Critical Bug #1). Delete after fixing.

4. **Unused imports** - Run a linter to identify unused imports across the codebase.

### 404 Errors in Logs - NOT Bugs

The runtime logs show many 404 errors like:
- `/src/env.d.ts`
- `/app.js.map`
- `/build/static/js/main.js`
- `/_nuxt/vendors.app.js`

These are **scanner bots** probing for common JS frameworks (React, Vue, Next.js, Nuxt, etc.). This is normal internet traffic and NOT a bug. The Flask app correctly returns 404 for these non-existent paths.

**No action required** - these are external probes, not application errors.

---

## Implementation Order

1. **P0 Critical (Do First)**
   - [ ] Fix `customer_update_post()` function (Bug #1)
   - [ ] Verify customer edit works before proceeding

2. **P0 Rep System (After Bug #1)**
   - [ ] Create `Rep` model
   - [ ] Create Alembic migration
   - [ ] Update `CustomerRep` and `Customer` models
   - [ ] Add rep admin routes
   - [ ] Create rep templates
   - [ ] Update all templates using reps

3. **P1 UI Polish**
   - [ ] Sales Dashboard: Remove "All Time" and subtitles
   - [ ] Sales Dashboard: SKU percentages
   - [ ] Distribution Details: Two-column layout
   - [ ] Lot Tracking: Fix min year to 2025

4. **P2 Enhancements**
   - [ ] Supplier detail: Show associated equipment
   - [ ] Legacy code cleanup

---

## Verification Checklist

After implementation, verify:

1. **Customer Edit**
   - [ ] Can edit customer details on Edit tab
   - [ ] Changes persist after save
   - [ ] Reason is required
   - [ ] Flash message confirms success

2. **Rep Management**
   - [ ] Can create new rep (just name, no User account)
   - [ ] Can edit rep
   - [ ] Can assign rep to customer
   - [ ] Rep appears in dropdowns across system

3. **Sales Dashboard**
   - [ ] No "All Time" text anywhere
   - [ ] No subtitles under metric cards
   - [ ] SKU breakdown shows percentages (e.g., "42.5%")
   - [ ] Lot tracking shows 2025+ lots

4. **Distribution Details**
   - [ ] Modal opens without error
   - [ ] Two-column layout with SKUs/Lots/Files on left
   - [ ] File status clearly visible (✅ or ⚠️)

5. **Equipment & Suppliers**
   - [ ] Supplier detail page shows associated equipment
   - [ ] Equipment detail page shows associated suppliers

---

## Notes for Ethan

After the developer completes these fixes:

1. Go to `/admin/customers` and click on any customer
2. Click the "Edit" tab
3. Try changing the city and entering a reason
4. Click "Save Changes"
5. If successful, the page should refresh with "Customer updated." message
6. Go to `/admin/reps` (new page) to manage reps
7. Check Sales Dashboard for the UI improvements
