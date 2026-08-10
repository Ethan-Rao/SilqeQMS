# Immediate Fixes & UI/UX Improvements — Implementation Spec

**Date:** 2026-01-19  
**Purpose:** Developer-ready implementation plan for immediate fixes and UI/UX improvements across Silq eQMS admin pages.

---

## Executive Summary

This document specifies immediate fixes and UI/UX improvements to address critical usability issues, data accuracy problems, and system reliability gaps in the Silq eQMS admin portal. The focus is on **readability, reliability, and professional presentation** without adding new analytics or complex features.

**Key Changes:**
1. **Distribution Log modal readability** — Fix cramped spacing, low contrast, overlapping text in detail modals
2. **Sales Dashboard layout** — Reorganize to two-column layout with New/Repeat customer lists, move SKU/Lot to right column
3. **Lot Tracking accuracy** — Show only lots built in 2025+, account for ALL distributions (not year-limited), calculate Active Inventory
4. **Customers page crash fix** — Diagnose and fix Internal Server Error, add rep assignment UI
5. **PDF import robustness** — Text-based extraction with heuristic parsing, support bulk uploads, store PDFs with orders/distributions
6. **Notes system** — Fix broken note creation, make notes global (accessible from all pages via modal), ensure cross-surface visibility
7. **Professional aesthetics** — Consistent spacing, typography, component styles across all pages

**Impact:** Improved admin productivity, reduced errors, professional appearance, reliable data tracking.

---

## Prioritized Issue List

### P0 (Critical — Must Fix Immediately)

1. **Distribution Log Modal Readability** — Users cannot read distribution details due to cramped layout
2. **Customers Page Internal Server Error** — Page is completely broken, blocks customer management
3. **Lot Tracking Shows Wrong Data** — Only shows 2026, doesn't account for all distributions, missing Active Inventory
4. **Notes Not Working** — "Add Note" functionality is broken, notes not accessible globally
5. **PDF Import Fails** — Parser too table-dependent, fails on shipping labels and sales orders without tables

### P1 (High Priority — Fix Soon)

6. **Sales Dashboard Layout** — Needs reorganization for better usability
7. **Rep Assignment Missing** — Cannot assign reps to customers, no UI for multi-rep support
8. **PDF Storage Not Linked** — PDFs uploaded but not accessible from order/distribution detail pages

### P2 (Medium Priority — Nice to Have)

9. **Professional Aesthetics** — Consistent styling improvements across all pages

---

## A) Distribution Log — "Details" Modal Readability (P0)

### Problem Statement

The "Distribution Details" modal has severe readability issues:
- Cramped spacing (content too close together)
- Low contrast (text hard to read)
- Overlapping text (content spills outside containers)
- Poor scrolling behavior (content overlaps page behind modal)
- Missing section headers (unclear organization)

### Requirements

**Modal Structure:**
```
[Modal Header: "Distribution Details" + Close Button]
[Scrollable Content Area]
  [Section: Distribution Entry]
    - Ship Date, Order #, SKU, Lot, Quantity, Source
  [Section: Linked Sales Order] (if exists)
    - Order #, Order Date, Ship Date, Status
  [Section: Customer]
    - Facility Name (linked), Address, Contact Info
  [Section: Customer Stats]
    - First Order, Last Order, Total Orders, Total Units, Top SKUs, Recent Lots
  [Section: Notes] (if any)
    - List of notes (newest first)
  [Section: Attachments] (if any)
    - List of PDFs with download links
  [Section: Quick Actions]
    - View Customer Profile, Add Note, Edit Entry
[Modal Footer: Close Button]
```

**Typography & Spacing:**
- Section headers: `font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--text);`
- Field labels: `font-size: 12px; color: var(--muted); margin-bottom: 4px;`
- Field values: `font-size: 14px; line-height: 1.6; margin-bottom: 12px;`
- Section spacing: `margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border);`
- Modal padding: `padding: 24px;` (not 20px)

**Modal Sizing:**
- Max width: `700px` (not 600px)
- Max height: `80vh` (not 60vh)
- Scroll containment: Content area has `overflow-y: auto; max-height: calc(80vh - 120px);`
- Backdrop: `background: rgba(0,0,0,0.5);` (semi-transparent overlay)

**Contrast & Readability:**
- Text color: `color: var(--text);` (ensure high contrast)
- Muted text: `color: var(--muted);` (but still readable)
- Background: `background: var(--card-bg);` (consistent with page)
- Borders: `border: 1px solid var(--border);` (visible but subtle)

**Responsive Behavior:**
- Desktop (≥768px): Modal centered, max-width 700px
- Mobile (<768px): Modal full-width with 16px margins
- No horizontal scrolling: Content wraps, long text uses `word-wrap: break-word;`

**Keyboard Support:**
- ESC key closes modal
- Tab navigation works within modal
- Focus trap: Tab cycles within modal, doesn't escape to page behind

### Implementation

**File:** `app/eqms/templates/admin/distribution_log/list.html`

**Changes:**
1. Update modal HTML structure with proper sections
2. Add CSS for spacing, typography, contrast
3. Ensure scroll containment (content doesn't overlap backdrop)
4. Add keyboard event handlers (ESC to close)

**Code Example:**
```html
<dialog id="entry-details-modal" style="max-width:700px; width:90%; padding:0; border-radius:12px; border:1px solid var(--border); background:var(--card-bg); color:var(--text); box-shadow:0 8px 32px rgba(0,0,0,0.3);">
  <div style="padding:20px 24px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; background:var(--card-bg);">
    <h2 style="margin:0; font-size:18px; font-weight:600;">Distribution Details</h2>
    <button onclick="document.getElementById('entry-details-modal').close()" style="background:none; border:none; font-size:28px; cursor:pointer; color:var(--muted); line-height:1; padding:0; width:32px; height:32px; display:flex; align-items:center; justify-content:center;">&times;</button>
  </div>
  <div id="entry-details-content" style="padding:24px; max-height:calc(80vh - 120px); overflow-y:auto; overflow-x:hidden;">
    <!-- Content loaded via AJAX -->
  </div>
</dialog>

<style>
#entry-details-modal::backdrop {
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(2px);
}

#entry-details-modal section {
  margin-bottom:20px;
  padding-bottom:16px;
  border-bottom:1px solid var(--border);
}

#entry-details-modal section:last-child {
  border-bottom:none;
  margin-bottom:0;
}

#entry-details-modal .section-header {
  font-size:14px;
  font-weight:600;
  margin-bottom:12px;
  color:var(--text);
  text-transform:uppercase;
  letter-spacing:0.5px;
}

#entry-details-modal .field-label {
  font-size:12px;
  color:var(--muted);
  margin-bottom:4px;
  display:block;
}

#entry-details-modal .field-value {
  font-size:14px;
  line-height:1.6;
  margin-bottom:12px;
  color:var(--text);
  word-wrap:break-word;
}
</style>

<script>
document.getElementById('entry-details-modal').addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    this.close();
  }
});
</script>
```

### Acceptance Criteria

- [ ] **AC1:** Modal opens without overlapping page content
- [ ] **AC2:** All text is readable (font-size ≥ 12px, contrast ratio ≥ 4.5:1)
- [ ] **AC3:** Sections are clearly separated with headers
- [ ] **AC4:** Content scrolls within modal (doesn't overlap backdrop)
- [ ] **AC5:** Modal works on desktop widths ≥768px without horizontal scrolling
- [ ] **AC6:** ESC key closes modal
- [ ] **AC7:** Field labels and values have proper spacing (≥4px between label and value, ≥12px between fields)

---

## B) Sales Dashboard — Reorganize Layout (P0)

### Problem Statement

Current dashboard layout is cluttered. Need cleaner, more professional two-column layout with New/Repeat customer lists prominently displayed.

### Requirements

**New Layout Structure:**
```
[Header: Sales Dashboard + Filters]
[Metric Cards Row: 5 cards (Total Units All Time, Total Orders, Customers, First-Time, Repeat)]
[Two-Column Main Content]
  [Left Column: 50% width]
    [Card: Recent Orders from NEW Customers]
    [Card: Recent Orders from REPEAT Customers]
  [Right Column: 50% width]
    [Card: Sales by SKU]
    [Card: Lot Tracking]
```

**Left Column — Recent Orders Lists:**

**"Recent Orders from NEW Customers" Card:**
- Header: "Recent Orders from NEW Customers" (with green accent color)
- Subtitle: "First-time buyers"
- Scrollable list (max-height: 400px)
- Each row shows:
  - Customer name (linked to profile, bold, truncate with ellipsis if long)
  - Order date + Order number (muted, smaller font)
  - Total units (bold, larger font)
  - Quick actions: [+ Note] [View Details] [Profile →]
- Empty state: "No recent orders from new customers."

**"Recent Orders from REPEAT Customers" Card:**
- Same structure as NEW customers
- Header: "Recent Orders from REPEAT Customers" (with orange accent color)
- Subtitle: "Returning buyers"

**Right Column — SKU & Lot Tracking:**

**"Sales by SKU" Card:**
- Keep existing table structure
- Position in right column (not left)

**"Lot Tracking" Card:**
- Keep existing table structure
- Position in right column (not left)
- Show current year in header: "Lot Tracking (2026)"

**Styling:**
- Consistent card padding: `16px`
- Card gaps: `14px`
- Remove any "Sales by Month" table if it exists
- Remove "Top Customers" table if it exists
- Clean, minimal presentation

### Implementation

**File:** `app/eqms/templates/admin/sales_dashboard/index.html`

**Changes:**
1. Remove "Sales by Month" section (if exists)
2. Remove "Top Customers" section (if exists)
3. Reorganize into two-column grid layout
4. Move SKU and Lot Tracking to right column
5. Ensure Recent Orders lists are in left column

**Code Structure:**
```html
<!-- Main Two-Column Layout -->
<div class="grid" style="grid-template-columns: 1fr 1fr; gap: 14px;">
  <!-- Left Column -->
  <div style="display:flex; flex-direction:column; gap:14px;">
    <!-- Recent Orders from NEW Customers -->
    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <h2 style="margin:0; font-size:16px;">Recent Orders from <span style="color:#34d399;">NEW</span> Customers</h2>
        <span class="muted" style="font-size:11px;">First-time buyers</span>
      </div>
      <!-- List of orders -->
    </div>
    
    <!-- Recent Orders from REPEAT Customers -->
    <div class="card">
      <!-- Same structure -->
    </div>
  </div>
  
  <!-- Right Column -->
  <div style="display:flex; flex-direction:column; gap:14px;">
    <!-- Sales by SKU -->
    <div class="card">
      <!-- Existing SKU table -->
    </div>
    
    <!-- Lot Tracking -->
    <div class="card">
      <!-- Existing Lot Tracking table -->
    </div>
  </div>
</div>
```

### Acceptance Criteria

- [ ] **AC8:** Dashboard has two-column layout (50/50 split)
- [ ] **AC9:** Left column contains "Recent Orders from NEW Customers" and "Recent Orders from REPEAT Customers" cards
- [ ] **AC10:** Right column contains "Sales by SKU" and "Lot Tracking" cards
- [ ] **AC11:** "Sales by Month" table is removed (if it existed)
- [ ] **AC12:** "Top Customers" table is removed (if it existed)
- [ ] **AC13:** Layout is responsive (stacks on mobile, two columns on desktop)

---

## C) Lot Tracking — Filter & Aggregation Logic (P0)

### Problem Statement

Lot Tracking currently shows "(2026)" and appears to only account for distributions in 2026. We need:
- Show only lots built in 2025 or later
- Account for ALL devices distributed from those lots (lifetime totals, not year-limited)
- Calculate Active Inventory (Total Units Produced - Total Units Distributed)

### Requirements

**Lot Selection Rule:**
- Show only lots where lot number indicates manufacturing date ≥ 2025
- Lot format: `SLQ-#####` where digits may encode date
- Parse year from lot string: If lot contains "2025", "2026", etc., extract year
- If lot doesn't encode date, rely on Lot Log CSV "Manufacturing Date" column
- If no date available, include lot if it appears in distributions from 2025-01-01 onward

**Aggregation Logic:**
- **Total Units Distributed:** Sum ALL distributions for this lot (all-time, not limited to current year)
- **First Distribution Date:** Earliest `ship_date` for this lot (all-time)
- **Last Distribution Date:** Latest `ship_date` for this lot (all-time)
- **Active Inventory:** `Total Units Produced (from Lot Log)` - `Total Units Distributed (all-time)`

**Lot Log Integration:**
- Load Lot Log CSV: `/mnt/data/LotLog.csv` or `SHIPSTATION_LOTLOG_PATH` env var
- Match lot: `distribution_log_entries.lot_number` (normalized) → `LotLog.Lot` OR `LotLog."Correct Lot Name"` (normalized)
- Get "Total Units in Lot" from Lot Log for Active Inventory calculation
- Apply lot corrections: Use "Correct Lot Name" if raw lot doesn't match

**Table Columns:**
- Lot (corrected lot number)
- Total Units Distributed (all-time sum)
- First Distribution Date (earliest ship_date)
- Last Distribution Date (latest ship_date)
- Active Inventory (produced - distributed, or N/A if lot not in Lot Log)

### Implementation

**File:** `app/eqms/modules/rep_traceability/service.py::compute_sales_dashboard()`

**Changes:**
1. Filter lots by manufacturing date (≥ 2025)
2. Aggregate distributions ALL-TIME (not year-limited)
3. Load Lot Log and calculate Active Inventory
4. Apply lot corrections

**Code Logic:**
```python
def compute_lot_tracking_with_inventory(s, *, lot_log_path: str) -> list[dict[str, Any]]:
    """Compute lot tracking with Active Inventory from Lot Log."""
    from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory, normalize_lot
    import re
    
    # Load Lot Log
    lot_to_sku, lot_corrections, lot_inventory = load_lot_log_with_inventory(lotlog_path)
    
    # Extract lots built in 2025 or later
    # Rule: Parse year from lot string or use Manufacturing Date from Lot Log
    current_year = date.today().year
    min_year = 2025
    
    # Get ALL distributions (not year-limited) for lots that qualify
    all_distributions = (
        s.query(DistributionLogEntry)
        .filter(DistributionLogEntry.lot_number.isnot(None))
        .all()
    )
    
    # Filter lots by manufacturing date
    qualifying_lots: set[str] = set()
    for e in all_distributions:
        raw_lot = (e.lot_number or "").strip()
        if not raw_lot:
            continue
        normalized = normalize_lot(raw_lot)
        corrected = lot_corrections.get(normalized, normalized)
        
        # Check if lot qualifies (built in 2025+)
        lot_year = _extract_year_from_lot(corrected, lot_log_path)
        if lot_year and lot_year >= min_year:
            qualifying_lots.add(corrected)
    
    # Aggregate ALL-TIME distributions for qualifying lots
    lot_map: dict[str, dict[str, Any]] = {}
    for e in all_distributions:
        raw_lot = (e.lot_number or "").strip()
        if not raw_lot:
            continue
        normalized = normalize_lot(raw_lot)
        corrected = lot_corrections.get(normalized, normalized)
        
        if corrected not in qualifying_lots:
            continue
        
        rec = lot_map.get(corrected)
        if not rec:
            rec = {
                "lot": corrected,
                "units": 0,
                "first_date": e.ship_date,
                "last_date": e.ship_date,
            }
            lot_map[corrected] = rec
        rec["units"] += int(e.quantity or 0)
        if e.ship_date < rec["first_date"]:
            rec["first_date"] = e.ship_date
        if e.ship_date > rec["last_date"]:
            rec["last_date"] = e.ship_date
    
    # Calculate Active Inventory
    for lot_key, rec in lot_map.items():
        produced = lot_inventory.get(lot_key, 0)
        distributed = rec["units"]
        rec["active_inventory"] = produced - distributed if produced > 0 else None
    
    return sorted(lot_map.values(), key=lambda r: r["lot"])

def _extract_year_from_lot(lot: str, lot_log_path: str) -> int | None:
    """Extract manufacturing year from lot number or Lot Log."""
    # Try parsing from lot string (e.g., SLQ-05012025 → 2025)
    year_match = re.search(r'20(\d{2})', lot)
    if year_match:
        try:
            year = int(f"20{year_match.group(1)}")
            if 2025 <= year <= 2100:
                return year
        except ValueError:
            pass
    
    # Try Lot Log "Manufacturing Date" column
    # (Implementation: load Lot Log, find lot row, parse Manufacturing Date)
    # ...
    
    return None
```

**Enhance `load_lot_log_with_inventory()`:**
```python
# app/eqms/modules/shipstation_sync/parsers.py

def load_lot_log_with_inventory(path_str: str) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
    """Load Lot Log with inventory data.
    
    Returns:
        - lot_to_sku: {lot -> sku}
        - lot_corrections: {raw_lot -> correct_lot}
        - lot_inventory: {lot -> total_units_produced}
    """
    # ... existing logic ...
    
    lot_inventory: dict[str, int] = {}
    for row in reader:
        raw_lot = (str(row.get("Lot") or "")).strip().upper()
        correct_lot_name = (str(row.get("Correct Lot Name") or "")).strip().upper()
        total_units = str(row.get("Total Units in Lot") or "0").strip()
        
        canonical_lot = normalize_lot(correct_lot_name) if correct_lot_name else normalize_lot(raw_lot)
        
        try:
            units = int(total_units) if total_units else 0
            lot_inventory[canonical_lot] = units
        except ValueError:
            pass
    
    return lot_to_sku, lot_corrections, lot_inventory
```

### Acceptance Criteria

- [ ] **AC14:** Lot Tracking shows only lots built in 2025 or later
- [ ] **AC15:** "Total Units Distributed" is ALL-TIME sum (not limited to current year)
- [ ] **AC16:** Lot that started distribution in 2025 and continued in 2026 shows full lifetime distributed totals
- [ ] **AC17:** "Active Inventory" column appears in table
- [ ] **AC18:** Active Inventory = Total Units Produced (Lot Log) - Total Units Distributed (all-time)
- [ ] **AC19:** If lot not in Lot Log, Active Inventory shows "N/A"
- [ ] **AC20:** Lot corrections are applied (incorrect lot names mapped to correct names)

---

## D) Customers Database Page Crash + Rep Assignment (P0)

### Problem Statement

1. Customers page loads "Internal Server Error" — completely broken
2. No UI for assigning reps to customers (multi-rep support missing)

### Root Cause Analysis

**Likely Causes for 500 Error:**
1. **SQL Query Error:** Join/subquery issue in `customers_list()` (line 129-153)
2. **Missing Relationship:** `DistributionLogEntry.customer` relationship not loaded
3. **Type Error:** Converting `None` to int or string
4. **Missing Index:** Slow query timing out
5. **Exception Not Caught:** Unhandled exception in template rendering

**Recommended Logging:**
```python
# Add to customers_list() function
import logging
logger = logging.getLogger(__name__)

try:
    # ... existing query logic ...
except Exception as e:
    logger.exception("Error in customers_list(): %s", e)
    flash(f"Error loading customers: {str(e)}", "danger")
    # Return empty list or redirect
```

### Requirements

**Fix Customers Page Crash:**
1. Add try/except around query logic
2. Add logging for exceptions
3. Validate all data before template rendering
4. Handle NULL values gracefully
5. Test with empty database state

**Rep Assignment UI:**
- Customers can have 0, 1, or multiple reps
- Use join table: `customer_reps` (many-to-many)
- UI: Multi-select dropdown or searchable tag input on customer profile page
- Display: Show assigned reps on customer profile, distribution log details, tracing reports

**Data Model:**
```sql
CREATE TABLE customer_reps (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    rep_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id),
    UNIQUE(customer_id, rep_id),
    INDEX idx_customer_reps_customer_id (customer_id),
    INDEX idx_customer_reps_rep_id (rep_id)
);
```

**UI Components:**
- Customer Profile: "Assigned Reps" section with multi-select dropdown
- Distribution Log Details: Show assigned reps for customer
- Tracing Reports: Filter by rep (already exists, but ensure it works with new model)

### Implementation

**File 1:** `app/eqms/modules/customer_profiles/admin.py::customers_list()`

**Fix Crash:**
```python
@bp.get("/customers")
@require_permission("customers.view")
def customers_list():
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # ... existing query logic ...
        
        # Wrap subquery join in try/except
        try:
            last_order_subq = (
                s.query(
                    DistributionLogEntry.customer_id,
                    func.max(DistributionLogEntry.ship_date).label("last_order_date")
                )
                .filter(DistributionLogEntry.customer_id.isnot(None))
                .group_by(DistributionLogEntry.customer_id)
                .subquery()
            )
            
            customers = (
                query
                .outerjoin(last_order_subq, Customer.id == last_order_subq.c.customer_id)
                .order_by(
                    last_order_subq.c.last_order_date.desc().nullslast(),
                    Customer.facility_name.asc(),
                    Customer.id.asc()
                )
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
        except Exception as e:
            logger.warning("Subquery join failed, using simple sort: %s", e)
            # Fallback: simple alphabetical sort
            customers = (
                query
                .order_by(Customer.facility_name.asc(), Customer.id.asc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
        
        # ... rest of function ...
        
    except Exception as e:
        logger.exception("Error in customers_list(): %s", e)
        flash(f"Error loading customers: {str(e)}", "danger")
        # Return empty state
        return render_template(
            "admin/customers/list.html",
            customers=[],
            customer_stats={},
            note_counts={},
            q="",
            state="",
            state_options=[],
            reps=[],
            rep_id="",
            year="",
            cust_type="",
            page=1,
            total=0,
            has_prev=False,
            has_next=False,
        )
```

**File 2:** Create migration for `customer_reps` table

**File 3:** `app/eqms/modules/customer_profiles/models.py`

**Add Model:**
```python
class CustomerRep(Base):
    __tablename__ = "customer_reps"
    __table_args__ = (
        Index("idx_customer_reps_customer_id", "customer_id"),
        Index("idx_customer_reps_rep_id", "rep_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    rep_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    customer: Mapped["Customer"] = relationship("Customer", back_populates="rep_assignments", lazy="selectin")
    rep: Mapped["User"] = relationship("User", lazy="selectin")
```

**Update Customer Model:**
```python
# In Customer class, add:
rep_assignments: Mapped[list["CustomerRep"]] = relationship(
    "CustomerRep",
    back_populates="customer",
    cascade="all, delete-orphan",
    lazy="selectin",
)
```

**File 4:** `app/eqms/templates/admin/customers/detail.html`

**Add Rep Assignment UI:**
```html
<div class="card">
  <h2 style="margin-top:0; font-size:16px;">Assigned Reps</h2>
  <form method="post" action="{{ url_for('customer_profiles.customer_reps_update', customer_id=customer.id) }}">
    <div>
      <div class="label">Select Reps</div>
      <select name="rep_ids" multiple style="width:100%; min-height:120px; padding:8px;">
        {% for rep in reps %}
          <option value="{{ rep.id }}" {% if rep.id in assigned_rep_ids %}selected{% endif %}>{{ rep.email }}</option>
        {% endfor %}
      </select>
      <p class="muted" style="font-size:11px; margin-top:4px;">Hold Ctrl/Cmd to select multiple reps</p>
    </div>
    <div style="margin-top:12px;">
      <button class="button" type="submit">Save Rep Assignments</button>
    </div>
  </form>
  
  {% if customer.rep_assignments %}
    <div style="margin-top:16px; padding-top:16px; border-top:1px solid var(--border);">
      <div class="muted" style="font-size:12px; margin-bottom:8px;">Currently Assigned:</div>
      {% for assignment in customer.rep_assignments %}
        <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0;">
          <span>{{ assignment.rep.email }}</span>
          {% if assignment.is_primary %}
            <span style="font-size:11px; padding:2px 8px; border-radius:4px; background:rgba(102,163,255,0.15); color:var(--primary);">Primary</span>
          {% endif %}
        </div>
      {% endfor %}
    </div>
  {% endif %}
</div>
```

**File 5:** `app/eqms/modules/customer_profiles/admin.py`

**Add Route:**
```python
@bp.post("/customers/<int:customer_id>/reps")
@require_permission("customers.edit")
def customer_reps_update(customer_id: int):
    """Update rep assignments for a customer."""
    s = db_session()
    u = _current_user()
    c = get_customer_by_id(s, customer_id)
    if not c:
        flash("Customer not found.", "danger")
        return redirect(url_for("customer_profiles.customers_list"))
    
    # Get selected rep IDs from form
    rep_ids_str = request.form.getlist("rep_ids")  # Multi-select returns list
    rep_ids = [int(rid) for rid in rep_ids_str if rid.strip()]
    
    # Delete existing assignments
    s.query(CustomerRep).filter(CustomerRep.customer_id == customer_id).delete()
    
    # Create new assignments
    for rep_id in rep_ids:
        # Validate rep exists
        rep = s.query(User).filter(User.id == rep_id, User.is_active.is_(True)).one_or_none()
        if not rep:
            continue
        
        assignment = CustomerRep(
            customer_id=customer_id,
            rep_id=rep_id,
            is_primary=(rep_id == c.primary_rep_id) if c.primary_rep_id else False,
            created_by_user_id=u.id,
        )
        s.add(assignment)
    
    record_event(
        s,
        actor=u,
        action="customer.reps_update",
        entity_type="Customer",
        entity_id=str(customer_id),
        metadata={"rep_ids": rep_ids},
    )
    s.commit()
    flash("Rep assignments updated.", "success")
    return redirect(url_for("customer_profiles.customer_detail", customer_id=customer_id))
```

### Acceptance Criteria

- [ ] **AC21:** Customers page loads without Internal Server Error
- [ ] **AC22:** Error logging captures exceptions (check logs for details)
- [ ] **AC23:** Customer profile page has "Assigned Reps" section
- [ ] **AC24:** Multi-select dropdown shows all active users
- [ ] **AC25:** Saving rep assignments updates `customer_reps` table
- [ ] **AC26:** Assigned reps appear on customer profile
- [ ] **AC27:** Distribution Log details modal shows assigned reps for customer
- [ ] **AC28:** Tracing reports can filter by rep (using new `customer_reps` table)

---

## E) PDF Import + Parsing System (P0)

### Problem Statement

PDF import fails with "No tables found, only text… Consider manually entering." Current parser is too table-dependent. Need robust extraction from:
- Bulk sales orders / packing slips
- Shipping labels

### Requirements

**Core Requirement:**
System must read both bulk sales orders/packing slips AND shipping labels, even when "tables" aren't detected.

**Workflows:**

**1. Bulk Upload:**
- Admin can upload multiple PDFs at once (sales order PDFs and shipping label PDFs)
- System parses them and associates them with correct order/distribution entry
- Route: `POST /admin/sales-orders/import-pdf-bulk` (accepts multiple files)

**2. Per-Order Upload:**
- On order detail page, admin can upload individual PDFs to that specific order
- Route: `POST /admin/sales-orders/<id>/upload-pdf`
- PDFs stored and linked to that order

**Storage & Access:**
- Each distribution/order must retain:
  - Associated sales order PDF(s)
  - Associated shipping label PDF(s)
- PDFs must always be downloadable from UI
- Storage key format: `sales_orders/{order_id}/pdfs/{type}_{timestamp}_{filename}` or `distribution_log/{entry_id}/pdfs/{type}_{timestamp}_{filename}`

**Parsing Details to Extract (Minimum Viable):**
- Order number (e.g., "SO 0000278", "Order #: 278")
- Ship date
- Ship-to name + facility + address
- Items: SKU(s), quantity, lot(s) if present
- Email if present
- Tracking number if present (label)

**Multi-Page Handling:**
- If PDF has multiple pages/orders, parser should split/iterate by page
- Each page treated as separate order if order number changes

### Implementation

**Parser Design — Step-by-Step Algorithm:**

**Phase 1: Text Extraction (Primary Method)**
```python
def parse_pdf_text_based(file_bytes: bytes) -> ParseResult:
    """Parse PDF using text extraction (not table detection)."""
    import pdfplumber
    
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        orders: list[dict] = []
        errors: list[ParseError] = []
        
        for page_num, page in enumerate(pdf.pages, start=1):
            # Extract all text from page
            text = page.extract_text()
            if not text:
                errors.append(ParseError(
                    row_index=page_num,
                    message="Page has no extractable text",
                ))
                continue
            
            # Normalize text (remove extra whitespace, normalize line breaks)
            text = re.sub(r'\s+', ' ', text)
            
            # Extract order number using anchors
            order_number = _extract_order_number(text)
            
            # Extract ship date
            ship_date = _extract_ship_date(text)
            
            # Extract ship-to info
            ship_to = _extract_ship_to(text)
            
            # Extract items (SKU, quantity, lot)
            items = _extract_items(text)
            
            # Extract tracking number
            tracking = _extract_tracking_number(text)
            
            if order_number and items:
                orders.append({
                    "order_number": order_number,
                    "order_date": ship_date or date.today(),
                    "ship_date": ship_date,
                    "customer_name": ship_to.get("name"),
                    "address": ship_to.get("address"),
                    "city": ship_to.get("city"),
                    "state": ship_to.get("state"),
                    "zip": ship_to.get("zip"),
                    "items": items,
                    "tracking_number": tracking,
                })
            else:
                errors.append(ParseError(
                    row_index=page_num,
                    message=f"Missing required fields: order_number={order_number}, items={len(items)}",
                ))
        
        return ParseResult(orders=orders, lines=[], errors=errors, total_rows_processed=len(pdf.pages))
```

**Heuristic Parsing Functions:**
```python
def _extract_order_number(text: str) -> str | None:
    """Extract order number using anchor patterns."""
    # Patterns: "Order #: 278", "SO 0000278", "Order Number: 278", "Order: 278"
    patterns = [
        r'Order\s*#?\s*:?\s*(\d+)',
        r'SO\s+(\d+)',
        r'Order\s+Number\s*:?\s*(\d+)',
        r'Sales\s+Order\s*:?\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def _extract_ship_date(text: str) -> date | None:
    """Extract ship date using anchor patterns."""
    # Patterns: "Ship Date: 01/15/2025", "Shipped: 2025-01-15"
    patterns = [
        r'Ship\s+Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        r'Shipped\s*:?\s*(\d{4}-\d{2}-\d{2})',
        r'Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _parse_date(match.group(1))
    return None

def _extract_ship_to(text: str) -> dict[str, str]:
    """Extract ship-to information."""
    # Look for "Ship To:" anchor, then extract name, address, city, state, zip
    ship_to_section = re.search(r'Ship\s+To\s*:?\s*(.+?)(?:\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
    if not ship_to_section:
        return {}
    
    section = ship_to_section.group(1)
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    
    name = lines[0] if lines else None
    address = lines[1] if len(lines) > 1 else None
    city_state_zip = lines[2] if len(lines) > 2 else None
    
    # Parse city, state, zip
    city = state = zip_code = None
    if city_state_zip:
        # Pattern: "City, ST 12345"
        match = re.match(r'(.+?),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)', city_state_zip)
        if match:
            city, state, zip_code = match.groups()
    
    return {
        "name": name,
        "address": address,
        "city": city,
        "state": state,
        "zip": zip_code,
    }

def _extract_items(text: str) -> list[dict]:
    """Extract SKU, quantity, lot from text."""
    items = []
    
    # Look for item table or list
    # Pattern 1: "SKU: 211810SPT Qty: 10 Lot: SLQ-12345"
    # Pattern 2: Table-like structure with columns
    
    # Try table extraction first (if pdfplumber can detect)
    # Fallback to regex patterns
    
    sku_pattern = r'(?:SKU|Item)\s*:?\s*(\d{6,10}SPT)'
    qty_pattern = r'(?:Qty|Quantity)\s*:?\s*(\d+)'
    lot_pattern = r'(?:Lot|Lot\s+Number)\s*:?\s*(SLQ-\d{5,12})'
    
    # Find all SKU mentions
    sku_matches = list(re.finditer(sku_pattern, text, re.IGNORECASE))
    for match in sku_matches:
        sku = match.group(1).upper()
        # Find quantity near this SKU (within 50 chars)
        context = text[max(0, match.start()-50):match.end()+50]
        qty_match = re.search(qty_pattern, context, re.IGNORECASE)
        lot_match = re.search(lot_pattern, context, re.IGNORECASE)
        
        items.append({
            "sku": sku,
            "quantity": int(qty_match.group(1)) if qty_match else 1,
            "lot_number": lot_match.group(1) if lot_match else None,
        })
    
    return items

def _extract_tracking_number(text: str) -> str | None:
    """Extract tracking number."""
    # Patterns: "Tracking: 1Z999AA10123456784", "TRACKING #: 9400111899223197428490"
    patterns = [
        r'Tracking\s*#?\s*:?\s*([A-Z0-9]{10,30})',
        r'Tracking\s+Number\s*:?\s*([A-Z0-9]{10,30})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None
```

**Fallback Logic:**
```python
def parse_sales_orders_pdf(file_bytes: bytes) -> ParseResult:
    """Main parser with fallback logic."""
    # Try text-based extraction first
    result = parse_pdf_text_based(file_bytes)
    
    # If extraction failed completely, store PDF anyway for manual entry
    if not result.orders and result.errors:
        # Still return result (with errors), but don't fail completely
        # Admin can manually enter data while PDF is stored
        pass
    
    return result
```

**Storage Integration:**
```python
# In PDF import route
def store_pdf_for_order(s, order_id: int, pdf_bytes: bytes, filename: str, pdf_type: str, user: User) -> str:
    """Store PDF and return storage key."""
    from app.eqms.storage import storage_from_config
    from datetime import datetime
    
    storage = storage_from_config(current_app.config)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = re.sub(r'[^\w.-]', '_', filename)
    storage_key = f"sales_orders/{order_id}/pdfs/{pdf_type}_{timestamp}_{safe_filename}"
    
    storage.put_bytes(storage_key, pdf_bytes, content_type="application/pdf")
    
    # Create database record
    pdf_record = OrderPdfAttachment(
        sales_order_id=order_id,
        storage_key=storage_key,
        filename=filename,
        pdf_type=pdf_type,  # 'sales_order' or 'shipping_label'
        uploaded_by_user_id=user.id,
    )
    s.add(pdf_record)
    
    return storage_key
```

**Data Model for PDF Attachments:**
```sql
CREATE TABLE order_pdf_attachments (
    id SERIAL PRIMARY KEY,
    sales_order_id INTEGER REFERENCES sales_orders(id) ON DELETE CASCADE,
    distribution_entry_id INTEGER REFERENCES distribution_log_entries(id) ON DELETE SET NULL,
    storage_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    pdf_type TEXT NOT NULL CHECK (pdf_type IN ('sales_order', 'shipping_label')),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    uploaded_by_user_id INTEGER REFERENCES users(id),
    INDEX idx_order_pdf_attachments_sales_order_id (sales_order_id),
    INDEX idx_order_pdf_attachments_distribution_entry_id (distribution_entry_id)
);
```

### Acceptance Criteria

- [ ] **AC29:** PDF parser extracts order number from text (not just tables)
- [ ] **AC30:** PDF parser extracts ship date, ship-to info, items, tracking number
- [ ] **AC31:** Parser handles multi-page PDFs (splits by page/order)
- [ ] **AC32:** If structured extraction fails, PDF is still stored for manual entry
- [ ] **AC33:** Bulk upload accepts multiple PDFs
- [ ] **AC34:** Per-order upload stores PDF linked to specific order
- [ ] **AC35:** PDFs are downloadable from order detail page
- [ ] **AC36:** Test with `/mnt/data/2025 Sales Orders.pdf` — extracts expected orders
- [ ] **AC37:** Test with `/mnt/data/Label1.pdf` — extracts tracking number and ship-to info

---

## F) Notes — Fix and Make Global (P0)

### Problem Statement

"Add note" is not working. Also notes should be accessible without leaving current page and should be cross-surface (visible on all relevant pages).

### Requirements

**Note Entity Model:**
```sql
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id),
    body TEXT NOT NULL,
    note_date DATE DEFAULT CURRENT_DATE,
    
    -- Associations (optional, can link to multiple entities)
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    order_id INTEGER REFERENCES sales_orders(id) ON DELETE SET NULL,
    distribution_id INTEGER REFERENCES distribution_log_entries(id) ON DELETE SET NULL,
    rep_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Indexes
    INDEX idx_notes_customer_id (customer_id, created_at DESC),
    INDEX idx_notes_order_id (order_id, created_at DESC),
    INDEX idx_notes_distribution_id (distribution_id, created_at DESC),
);
```

**Note-Taking Workflow:**
- Notes accessible from: Sales Dashboard, Distribution Log, Customer Database page
- Add note via modal/drawer (doesn't navigate away)
- View previous notes in same modal/drawer
- Notes are cross-surface: If note added on Distribution Log for a customer, it appears on Sales Dashboard and Customer page

**UI Components:**

**1. Notes Modal/Drawer:**
- Opens from "Add Note" button or "View Notes" link
- Shows list of existing notes (newest first)
- Has form to add new note
- Closes without navigation

**2. Notes Indicator:**
- Small badge/icon showing note count on order rows, customer rows
- Click badge → Opens notes modal

### Implementation

**File 1:** Create migration for `notes` table

**File 2:** `app/eqms/modules/rep_traceability/models.py`

**Add Model:**
```python
class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        Index("idx_notes_customer_id", "customer_id", "created_at"),
        Index("idx_notes_order_id", "order_id", "created_at"),
        Index("idx_notes_distribution_id", "distribution_id", "created_at"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    note_date: Mapped[date | None] = mapped_column(Date, nullable=True, default=date.today)
    
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id", ondelete="SET NULL"), nullable=True)
    distribution_id: Mapped[int | None] = mapped_column(ForeignKey("distribution_log_entries.id", ondelete="SET NULL"), nullable=True)
    rep_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_user_id], lazy="selectin")
    customer: Mapped["Customer | None"] = relationship("Customer", lazy="selectin")
    order: Mapped["SalesOrder | None"] = relationship("SalesOrder", lazy="selectin")
```

**File 3:** `app/eqms/modules/rep_traceability/admin.py`

**Add Routes:**
```python
@bp.get("/notes/modal/<entity_type>/<int:entity_id>")
@require_permission("customers.notes")  # Reuse existing permission
def notes_modal(entity_type: str, entity_id: int):
    """Return HTML for notes modal (AJAX)."""
    s = db_session()
    
    # Get notes based on entity type
    notes = []
    if entity_type == "customer":
        notes = s.query(Note).filter(Note.customer_id == entity_id).order_by(Note.created_at.desc()).all()
    elif entity_type == "order":
        notes = s.query(Note).filter(Note.order_id == entity_id).order_by(Note.created_at.desc()).all()
    elif entity_type == "distribution":
        notes = s.query(Note).filter(Note.distribution_id == entity_id).order_by(Note.created_at.desc()).all()
    
    return render_template("admin/_notes_modal.html", 
        entity_type=entity_type,
        entity_id=entity_id,
        notes=notes,
    )

@bp.post("/notes/create")
@require_permission("customers.notes")
def notes_create():
    """Create note via AJAX."""
    s = db_session()
    u = _current_user()
    
    payload = request.get_json() or {}
    customer_id = payload.get("customer_id")
    order_id = payload.get("order_id")
    distribution_id = payload.get("distribution_id")
    body = (payload.get("body") or "").strip()
    note_date = payload.get("note_date")
    
    if not body:
        return jsonify({"error": "Note body is required"}), 400
    
    note = Note(
        created_by_user_id=u.id,
        body=body,
        note_date=date.fromisoformat(note_date) if note_date else date.today(),
        customer_id=int(customer_id) if customer_id else None,
        order_id=int(order_id) if order_id else None,
        distribution_id=int(distribution_id) if distribution_id else None,
    )
    s.add(note)
    
    record_event(
        s,
        actor=u,
        action="note.create",
        entity_type="Note",
        entity_id=str(note.id),
        metadata={"customer_id": customer_id, "order_id": order_id, "distribution_id": distribution_id},
    )
    s.commit()
    
    return jsonify({"success": True, "note_id": note.id})

@bp.get("/notes/list/<entity_type>/<int:entity_id>")
@require_permission("customers.notes")
def notes_list(entity_type: str, entity_id: int):
    """Get notes as JSON (AJAX)."""
    s = db_session()
    
    notes = []
    if entity_type == "customer":
        notes = s.query(Note).filter(Note.customer_id == entity_id).order_by(Note.created_at.desc()).all()
    elif entity_type == "order":
        notes = s.query(Note).filter(Note.order_id == entity_id).order_by(Note.created_at.desc()).all()
    elif entity_type == "distribution":
        notes = s.query(Note).filter(Note.distribution_id == entity_id).order_by(Note.created_at.desc()).all()
    
    return jsonify({
        "notes": [
            {
                "id": n.id,
                "body": n.body,
                "note_date": n.note_date.isoformat() if n.note_date else None,
                "created_at": n.created_at.isoformat(),
                "created_by": n.created_by.email if n.created_by else None,
            }
            for n in notes
        ]
    })
```

**File 4:** `app/eqms/templates/admin/_notes_modal.html` (new)

**Create Reusable Notes Modal:**
```html
<dialog id="notes-modal" style="max-width:600px; width:90%; padding:0; border-radius:12px; border:1px solid var(--border); background:var(--card-bg);">
  <div style="padding:20px 24px; border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center;">
    <h2 style="margin:0; font-size:18px;">Notes</h2>
    <button onclick="document.getElementById('notes-modal').close()" style="background:none; border:none; font-size:28px; cursor:pointer; color:var(--muted);">&times;</button>
  </div>
  <div style="padding:24px; max-height:60vh; overflow-y:auto;">
    <!-- Add Note Form -->
    <form id="note-form" style="margin-bottom:24px; padding-bottom:20px; border-bottom:1px solid var(--border);">
      <div style="margin-bottom:12px;">
        <div class="label">Note Text *</div>
        <textarea name="body" required style="width:100%; min-height:80px; padding:10px; border-radius:8px; border:1px solid var(--border); background:var(--card-bg); color:var(--text);" placeholder="Enter note..."></textarea>
      </div>
      <div style="margin-bottom:12px;">
        <div class="label">Date</div>
        <input type="date" name="note_date" style="width:100%;" />
      </div>
      <button class="button" type="submit">Save Note</button>
    </form>
    
    <!-- Notes List -->
    <div id="notes-list">
      {% if notes %}
        {% for note in notes %}
          <div style="padding:12px 0; border-bottom:1px solid rgba(255,255,255,0.05);">
            <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
              <strong style="font-size:13px;">{{ note.note_date or note.created_at.strftime('%Y-%m-%d') }}</strong>
              <span class="muted" style="font-size:11px;">{{ note.created_by.email if note.created_by else 'System' }}</span>
            </div>
            <div style="font-size:14px; line-height:1.6; color:var(--text);">{{ note.body|e }}</div>
          </div>
        {% endfor %}
      {% else %}
        <p class="muted" style="text-align:center; padding:20px;">No notes yet.</p>
      {% endif %}
    </div>
  </div>
</dialog>

<script>
async function openNotesModal(entityType, entityId) {
  const modal = document.getElementById('notes-modal');
  const form = document.getElementById('note-form');
  const notesList = document.getElementById('notes-list');
  
  // Load notes
  const res = await fetch(`/admin/notes/list/${entityType}/${entityId}`);
  const data = await res.json();
  
  // Render notes
  if (data.notes && data.notes.length > 0) {
    notesList.innerHTML = data.notes.map(n => `
      <div style="padding:12px 0; border-bottom:1px solid rgba(255,255,255,0.05);">
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
          <strong style="font-size:13px;">${n.note_date || n.created_at.split('T')[0]}</strong>
          <span class="muted" style="font-size:11px;">${n.created_by || 'System'}</span>
        </div>
        <div style="font-size:14px; line-height:1.6;">${escapeHtml(n.body)}</div>
      </div>
    `).join('');
  } else {
    notesList.innerHTML = '<p class="muted" style="text-align:center; padding:20px;">No notes yet.</p>';
  }
  
  // Set up form submission
  form.onsubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const payload = {
      [entityType + '_id']: entityId,
      body: formData.get('body'),
      note_date: formData.get('note_date'),
    };
    
    const resp = await fetch('/admin/notes/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    
    if (resp.ok) {
      form.reset();
      // Reload notes
      openNotesModal(entityType, entityId);
    } else {
      alert('Failed to save note');
    }
  };
  
  modal.showModal();
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
</script>
```

**File 5:** Update templates to include notes modal and "Add Note" buttons

### Acceptance Criteria

- [ ] **AC38:** "Add Note" button works on Sales Dashboard
- [ ] **AC39:** "Add Note" button works on Distribution Log
- [ ] **AC40:** "Add Note" button works on Customer Database page
- [ ] **AC41:** Notes modal opens without navigation
- [ ] **AC42:** Notes are sorted newest-first
- [ ] **AC43:** Note created on Distribution Log appears on Sales Dashboard and Customer page
- [ ] **AC44:** Success toast appears after note creation
- [ ] **AC45:** Notes are visible across pages for same entity (customer/order/distribution)

---

## G) Professional Aesthetics (P0 Across the Board)

### Problem Statement

UI looks cluttered and inconsistent. Need professional, clean admin UI with consistent spacing, typography, and component styles.

### UI Style Guide

**Typography Scale:**
- Page titles: `font-size: 24px; font-weight: 700; line-height: 1.2;`
- Section headers: `font-size: 16px; font-weight: 600; margin-top: 0;`
- Table headers: `font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted);`
- Body text: `font-size: 14px; line-height: 1.6;`
- Muted text: `font-size: 12px; color: var(--muted);`
- Small text: `font-size: 11px;`

**Spacing:**
- Card gaps: `14px` (consistent across all pages)
- Card padding: `16px` (not 12px or 20px)
- Form field gaps: `12px` (between form fields)
- Section spacing: `margin-bottom: 20px;` (between major sections)
- Table cell padding: `10px 12px` (not 8px or 14px)

**Table Styling:**
- Row height: `min-height: 44px;` (touch-friendly)
- Hover state: `background: rgba(255,255,255,0.05);` (subtle highlight)
- Striped rows: `tr:nth-child(even) { background: rgba(255,255,255,0.02); }`
- Sticky headers: `position: sticky; top: 0; background: var(--card-bg); z-index: 10;`
- Border: `border-bottom: 1px solid rgba(255,255,255,0.05);` (subtle, not harsh)

**Button Hierarchy:**
- Primary: `.button` — `background: var(--primary); color: white; padding: 10px 16px;`
- Secondary: `.button--secondary` — `background: rgba(255,255,255,0.1); color: var(--text); padding: 10px 16px;`
- Small: Add `.button--small` — `padding: 6px 12px; font-size: 12px;`
- Danger: `.button--danger` — `background: var(--danger); color: white;`

**Modal Sizing:**
- Max width: `700px` (not 600px)
- Max height: `80vh` (not 60vh)
- Padding: `24px` (not 20px)
- Scroll containment: Content area has `overflow-y: auto; max-height: calc(80vh - 120px);`

**Responsive Behavior:**
- Desktop (≥768px): Two-column layouts, full-width tables
- Mobile (<768px): Single column, stacked cards, horizontal scroll for tables

**Contrast:**
- Text: `color: var(--text);` (ensure high contrast, ≥4.5:1 ratio)
- Muted: `color: var(--muted);` (still readable, ≥3:1 ratio)
- Background: `background: var(--card-bg);` (consistent with page)

**Remove Clutter:**
- No debug blocks (`{{ debug }}`, `{{ request }}` dumps)
- No unnecessary stats panels
- No raw JSON dumps
- No internal IDs in UI (use human-readable labels)

### Implementation

**File:** `app/eqms/templates/_layout.html` (or create `app/eqms/static/admin-styles.css`)

**Add Global Styles:**
```css
/* Typography */
h1 { font-size: 24px; font-weight: 700; line-height: 1.2; margin-top: 0; }
h2 { font-size: 16px; font-weight: 600; margin-top: 0; }
.table th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
.table td { font-size: 14px; line-height: 1.6; }

/* Spacing */
.card { padding: 16px; }
.card + .card { margin-top: 14px; }
.form > div + div { margin-top: 12px; }

/* Tables */
.table { width: 100%; border-collapse: collapse; }
.table th { padding: 10px 12px; border-bottom: 1px solid var(--border); position: sticky; top: 0; background: var(--card-bg); z-index: 10; }
.table td { padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); min-height: 44px; }
.table tbody tr:hover { background: rgba(255,255,255,0.05); }
.table tbody tr:nth-child(even) { background: rgba(255,255,255,0.02); }

/* Buttons */
.button { padding: 10px 16px; font-size: 14px; border-radius: 8px; }
.button--small { padding: 6px 12px; font-size: 12px; }
.button--danger { background: var(--danger); color: white; }

/* Modals */
dialog { max-width: 700px; width: 90%; padding: 0; border-radius: 12px; }
dialog .modal-content { padding: 24px; max-height: calc(80vh - 120px); overflow-y: auto; }
```

### Acceptance Criteria

- [ ] **AC46:** All pages use consistent card padding (16px)
- [ ] **AC47:** All tables use consistent cell padding (10px 12px)
- [ ] **AC48:** All modals use consistent sizing (max-width 700px, padding 24px)
- [ ] **AC49:** All text meets contrast requirements (≥4.5:1 for body, ≥3:1 for muted)
- [ ] **AC50:** No debug blocks or unnecessary stats panels visible
- [ ] **AC51:** Responsive behavior works (stacks on mobile, two columns on desktop)

---

## Data Model Changes

### New Tables

**1. `notes` Table:**
```sql
CREATE TABLE notes (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    body TEXT NOT NULL,
    note_date DATE DEFAULT CURRENT_DATE,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    order_id INTEGER REFERENCES sales_orders(id) ON DELETE SET NULL,
    distribution_id INTEGER REFERENCES distribution_log_entries(id) ON DELETE SET NULL,
    rep_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_notes_customer_id (customer_id, created_at DESC),
    INDEX idx_notes_order_id (order_id, created_at DESC),
    INDEX idx_notes_distribution_id (distribution_id, created_at DESC)
);
```

**2. `customer_reps` Table:**
```sql
CREATE TABLE customer_reps (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    rep_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_user_id INTEGER REFERENCES users(id),
    UNIQUE(customer_id, rep_id),
    INDEX idx_customer_reps_customer_id (customer_id),
    INDEX idx_customer_reps_rep_id (rep_id)
);
```

**3. `order_pdf_attachments` Table:**
```sql
CREATE TABLE order_pdf_attachments (
    id SERIAL PRIMARY KEY,
    sales_order_id INTEGER REFERENCES sales_orders(id) ON DELETE CASCADE,
    distribution_entry_id INTEGER REFERENCES distribution_log_entries(id) ON DELETE SET NULL,
    storage_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    pdf_type TEXT NOT NULL CHECK (pdf_type IN ('sales_order', 'shipping_label')),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    uploaded_by_user_id INTEGER REFERENCES users(id),
    INDEX idx_order_pdf_attachments_sales_order_id (sales_order_id),
    INDEX idx_order_pdf_attachments_distribution_entry_id (distribution_entry_id)
);
```

### Modified Tables

**None** — All changes are additive (new tables, new fields are nullable or have defaults).

---

## Backend/API Changes

### New Routes

**Notes:**
- `GET /admin/notes/modal/<entity_type>/<entity_id>` — Returns HTML for notes modal (AJAX)
- `POST /admin/notes/create` — Creates note via AJAX (JSON)
- `GET /admin/notes/list/<entity_type>/<entity_id>` — Returns notes as JSON (AJAX)

**PDF Attachments:**
- `POST /admin/sales-orders/import-pdf-bulk` — Bulk PDF upload (multiple files)
- `POST /admin/sales-orders/<id>/upload-pdf` — Upload PDF to specific order
- `GET /admin/sales-orders/<id>/pdfs` — List PDFs for order (JSON)
- `GET /admin/sales-orders/pdf/<attachment_id>/download` — Download PDF

**Rep Assignment:**
- `POST /admin/customers/<id>/reps` — Update rep assignments (multi-select)

### Modified Routes

**Distribution Log:**
- `GET /admin/distribution-log/entry-details/<entry_id>` — Enhanced to show notes, PDFs, rep assignments

**Customers:**
- `GET /admin/customers` — Add error handling, logging
- `GET /admin/customers/<id>` — Add rep assignment UI, notes display

**Sales Dashboard:**
- `GET /admin/sales-dashboard` — Update lot tracking logic (all-time aggregation, Active Inventory)

---

## Frontend Changes

### New Components

**1. Notes Modal (`app/eqms/templates/admin/_notes_modal.html`):**
- Reusable modal component
- Shows note list + add note form
- AJAX-based (no page reload)

**2. PDF Attachment Panel:**
- Shows list of PDFs for order/distribution
- Upload button + download links
- Display in order detail page, distribution detail modal

**3. Rep Assignment Widget:**
- Multi-select dropdown
- Shows currently assigned reps
- Save button

### Modified Templates

**1. `app/eqms/templates/admin/distribution_log/list.html`:**
- Fix modal readability (spacing, typography, scroll containment)
- Add "Add Note" button that opens notes modal
- Add notes indicator badge

**2. `app/eqms/templates/admin/sales_dashboard/index.html`:**
- Reorganize layout (two-column)
- Move SKU/Lot to right column
- Add notes modal integration

**3. `app/eqms/templates/admin/customers/list.html`:**
- Add error handling display
- Add notes indicator badges

**4. `app/eqms/templates/admin/customers/detail.html`:**
- Add rep assignment section
- Add notes display
- Add PDF attachments section

**5. `app/eqms/templates/admin/sales_orders/detail.html`:**
- Add PDF attachments section
- Add notes display

---

## Parsing Approach

### Step-by-Step Algorithm

**1. Text Extraction (Primary):**
- Use `pdfplumber` to extract all text from each page
- Normalize whitespace (collapse multiple spaces, normalize line breaks)

**2. Anchor-Based Extraction:**
- Look for anchor patterns: "Order #:", "Ship To:", "Ship Date:", "SKU:", "LOT:", "Qty:"
- Extract values following anchors using regex

**3. Multi-Page Handling:**
- Iterate through each page
- If order number changes between pages, treat as separate order
- If order number same, combine items from multiple pages

**4. Fallback Logic:**
- If structured extraction fails completely, store PDF anyway
- Allow admin to manually enter data while PDF is attached
- PDF remains accessible for reference

**5. Validation:**
- Validate extracted SKU (must be one of: 211810SPT, 211610SPT, 211410SPT)
- Validate quantity (must be positive integer)
- Validate lot format (if present, should match SLQ-##### pattern)
- Validate date format (try multiple formats)

**6. Error Reporting:**
- Collect parse errors per page
- Display errors in import results page
- Allow admin to review and correct

### Failure Handling

**If PDF has no extractable text:**
- Store PDF anyway
- Return error: "PDF has no extractable text. Please enter data manually."
- PDF remains attached for reference

**If required fields missing:**
- Store PDF anyway
- Return error listing missing fields
- Allow admin to complete manually

**If multiple pages with same order number:**
- Combine items from all pages
- Use earliest date as order date
- Use most complete ship-to info

---

## Test Plan

### Unit Tests

**PDF Parsing:**
```python
# tests/test_pdf_parsing.py

def test_extract_order_number():
    """Test order number extraction from text."""
    text = "Order #: 278"
    assert _extract_order_number(text) == "278"
    
    text = "SO 0000278"
    assert _extract_order_number(text) == "278"

def test_extract_ship_date():
    """Test ship date extraction."""
    text = "Ship Date: 01/15/2025"
    assert _extract_ship_date(text) == date(2025, 1, 15)

def test_extract_items():
    """Test item extraction."""
    text = "SKU: 211810SPT Qty: 10 Lot: SLQ-12345"
    items = _extract_items(text)
    assert len(items) == 1
    assert items[0]["sku"] == "211810SPT"
    assert items[0]["quantity"] == 10
    assert items[0]["lot_number"] == "SLQ-12345"
```

**Lot Tracking:**
```python
# tests/test_lot_tracking.py

def test_lot_tracking_all_time_aggregation():
    """Verify lot tracking sums ALL distributions, not year-limited."""
    # Create distributions in 2025 and 2026 for same lot
    # Verify total units = sum of both years
    pass

def test_active_inventory_calculation():
    """Verify Active Inventory = produced - distributed."""
    # Load Lot Log, create distributions
    # Verify calculation
    pass
```

### Integration Tests

**PDF Upload + Download:**
```python
# tests/test_pdf_attachments.py

def test_upload_pdf_to_order():
    """Test uploading PDF to specific order."""
    # Create order, upload PDF
    # Verify PDF stored, linked to order, downloadable
    pass

def test_bulk_pdf_upload():
    """Test bulk PDF upload."""
    # Upload multiple PDFs
    # Verify all parsed, orders created, PDFs stored
    pass
```

**Notes Cross-Surface:**
```python
# tests/test_notes.py

def test_note_visible_across_pages():
    """Verify note created on one page appears on others."""
    # Create note for customer on Distribution Log
    # Verify note appears on Sales Dashboard and Customer page
    pass
```

### UI Smoke Tests (Manual)

**Test 1: Distribution Log Modal Readability**
1. Navigate to `/admin/distribution-log`
2. Click "Details" on any row
3. **Expected:** Modal opens, all text readable, proper spacing, scrolls within modal
4. **Expected:** ESC key closes modal

**Test 2: Sales Dashboard Layout**
1. Navigate to `/admin/sales-dashboard`
2. **Expected:** Two-column layout, New/Repeat customer lists in left, SKU/Lot in right
3. **Expected:** No "Sales by Month" or "Top Customers" tables

**Test 3: Lot Tracking Accuracy**
1. Navigate to `/admin/sales-dashboard`
2. Check "Lot Tracking" table
3. **Expected:** Shows only lots from 2025+
4. **Expected:** "Total Units Distributed" is all-time sum (not year-limited)
5. **Expected:** "Active Inventory" column appears with correct values

**Test 4: Customers Page**
1. Navigate to `/admin/customers`
2. **Expected:** Page loads without error
3. **Expected:** Customers sorted by most recent order

**Test 5: Rep Assignment**
1. Navigate to `/admin/customers/<id>`
2. **Expected:** "Assigned Reps" section appears
3. Select multiple reps, save
4. **Expected:** Reps assigned, visible on customer profile

**Test 6: PDF Import**
1. Navigate to `/admin/sales-orders/import-pdf`
2. Upload `/mnt/data/2025 Sales Orders.pdf`
3. **Expected:** Orders extracted, PDFs stored, downloadable

**Test 7: Notes Global**
1. Navigate to `/admin/distribution-log`
2. Click "Add Note" on a distribution row
3. Enter note, save
4. Navigate to customer profile
5. **Expected:** Note appears in notes list

---

## Logging/Observability

### Recommended Logging

**For Customers Page Crash:**
```python
# In customers_list() function
import logging
logger = logging.getLogger(__name__)

try:
    # ... query logic ...
except Exception as e:
    logger.exception(
        "Error in customers_list(): query=%s, filters=%s, error=%s",
        str(query),
        {"q": q, "state": state, "year": year},
        str(e),
    )
    # ... error handling ...
```

**For PDF Parsing:**
```python
logger.info("PDF parsing started: filename=%s, pages=%d", filename, len(pdf.pages))
logger.warning("PDF parse error on page %d: %s", page_num, error_message)
logger.info("PDF parsing completed: orders=%d, errors=%d", len(orders), len(errors))
```

**For Notes:**
```python
logger.info("Note created: id=%d, entity_type=%s, entity_id=%d, user=%s", 
    note.id, entity_type, entity_id, user.email)
```

### Error Monitoring

- Log all exceptions with full context (query, filters, user, timestamp)
- Include stack traces for debugging
- Log warnings for recoverable errors (e.g., PDF parse failures)
- Log info for important operations (note creation, PDF upload, rep assignment)

---

## Definition of Done (DoD) Checklist

### P0 Critical Fixes

- [ ] **DoD1:** Distribution Log modal is readable (proper spacing, contrast, scroll containment)
- [ ] **DoD2:** Customers page loads without Internal Server Error
- [ ] **DoD3:** Lot Tracking shows only lots from 2025+, accounts for ALL distributions (all-time), shows Active Inventory
- [ ] **DoD4:** Notes work on Sales Dashboard, Distribution Log, Customer Database
- [ ] **DoD5:** Notes are cross-surface (visible on all relevant pages)
- [ ] **DoD6:** PDF import works with text-based extraction (not just tables)
- [ ] **DoD7:** PDFs are stored and downloadable from order/distribution detail pages

### P1 High Priority

- [ ] **DoD8:** Sales Dashboard has two-column layout (New/Repeat lists left, SKU/Lot right)
- [ ] **DoD9:** Rep assignment UI exists on customer profile (multi-select)
- [ ] **DoD10:** Rep assignments visible in distribution log details and tracing reports

### P2 Medium Priority

- [ ] **DoD11:** All pages use consistent spacing, typography, component styles
- [ ] **DoD12:** All modals meet readability standards (font-size ≥12px, contrast ≥4.5:1)
- [ ] **DoD13:** No debug blocks or unnecessary stats panels visible

---

## Implementation Order (Recommended)

**Phase 1: Critical Fixes (P0)**
1. Fix Customers page crash (add error handling, logging)
2. Fix Distribution Log modal readability
3. Fix Lot Tracking logic (all-time aggregation, Active Inventory)
4. Fix Notes system (create notes table, global modal, cross-surface visibility)
5. Enhance PDF parser (text-based extraction, fallback logic)

**Phase 2: High Priority (P1)**
6. Reorganize Sales Dashboard layout
7. Add rep assignment UI and data model

**Phase 3: Polish (P2)**
8. Apply professional aesthetics across all pages

---

## Files to Create/Modify

### New Files

- `migrations/versions/XXXXX_add_notes_table.py`
- `migrations/versions/XXXXX_add_customer_reps_table.py`
- `migrations/versions/XXXXX_add_order_pdf_attachments_table.py`
- `app/eqms/modules/rep_traceability/models.py` (add `Note`, `OrderPdfAttachment` models)
- `app/eqms/modules/customer_profiles/models.py` (add `CustomerRep` model)
- `app/eqms/templates/admin/_notes_modal.html` (reusable notes modal)
- `app/eqms/static/admin-styles.css` (optional, or add to `_layout.html`)

### Modified Files

- `app/eqms/modules/customer_profiles/admin.py` (fix crash, add rep assignment route)
- `app/eqms/modules/rep_traceability/admin.py` (add notes routes, PDF attachment routes)
- `app/eqms/modules/rep_traceability/service.py` (fix lot tracking logic)
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (enhance text-based extraction)
- `app/eqms/templates/admin/distribution_log/list.html` (fix modal, add notes)
- `app/eqms/templates/admin/sales_dashboard/index.html` (reorganize layout)
- `app/eqms/templates/admin/customers/list.html` (add error handling display)
- `app/eqms/templates/admin/customers/detail.html` (add rep assignment, notes, PDFs)
- `app/eqms/templates/admin/sales_orders/detail.html` (add PDF attachments, notes)

---

## Risks & Mitigation

### Risk 1: PDF Parsing Still Fails on Some PDFs

**Mitigation:**
- Always store PDF even if parsing fails
- Provide clear error messages
- Allow manual data entry with PDF attached for reference

### Risk 2: Customers Page Crash Root Cause Not Found

**Mitigation:**
- Add comprehensive logging
- Add try/except with fallback (simple sort if subquery fails)
- Test with empty database state

### Risk 3: Notes Performance with Many Notes

**Mitigation:**
- Limit notes list to 50 most recent (paginate if needed)
- Use indexes on `customer_id`, `order_id`, `distribution_id`
- Lazy-load notes in modals (only fetch when opened)

### Risk 4: Lot Tracking Calculation Slow

**Mitigation:**
- Use SQL aggregates (GROUP BY) instead of Python loops
- Add indexes on `distribution_log_entries.lot_number`, `ship_date`
- Cache Lot Log data (load once per request, not per lot)

---

## Summary

This implementation spec provides a complete, developer-ready plan for:
1. **Distribution Log modal readability** — Professional, readable detail modals
2. **Sales Dashboard reorganization** — Clean two-column layout
3. **Lot Tracking accuracy** — 2025+ lots, all-time aggregation, Active Inventory
4. **Customers page crash fix** — Error handling, logging, rep assignment
5. **PDF import robustness** — Text-based extraction, bulk uploads, storage
6. **Notes system** — Global, cross-surface, modal-based
7. **Professional aesthetics** — Consistent styling across all pages

All changes are incremental, safe, and maintain data integrity. The plan includes specific file paths, code examples, acceptance criteria, and test plans.
