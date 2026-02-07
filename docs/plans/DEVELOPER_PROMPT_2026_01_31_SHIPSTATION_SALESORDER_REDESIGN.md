# DEVELOPER PROMPT: ShipStation Import & Sales Order Matching Redesign
**Date:** January 31, 2026  
**Priority:** CRITICAL  
**Scope:** Major refactor of customer profiling and sales order handling

---

## EXECUTIVE SUMMARY

This document addresses critical issues with the current ShipStation import and sales order matching system:

1. **Duplicate Sales Orders** - Multiple SOs being created for the same order number
2. **Unknown Customer Problem** - NRE (Non-Recurring Engineering) orders creating "Unknown Customer" entries
3. **Customer Code as Source of Truth** - Implement customer grouping by CUSTOMER NUMBER field
4. **Quantity Handling** - Box of 10 vs individual unit inconsistencies
5. **NRE Projects Feature** - New admin section for non-catheter customers

---

## PART 1: SALES ORDER DEDUPLICATION

### Current Problem
When the same sales order PDF is uploaded multiple times, or when a sales order has multiple pages, the system creates duplicate `SalesOrder` records. This breaks the data model where one order should be able to link to multiple distributions.

### Business Rule
**ONE sales order record per order_number.** If the same order_number is imported again:
- Attach the new PDF to the existing SalesOrder
- Update the existing SalesOrder's metadata if new data is available
- Do NOT create a new SalesOrder record

### Code Changes Required

#### 1.1 Modify PDF Import Logic
**File:** `app/eqms/modules/rep_traceability/admin.py`

Find the `sales_orders_import_pdf_bulk()` function and update the order processing:

```python
# In the order processing loop (around line 1895-1950)
# BEFORE creating a new SalesOrder, check for existing by order_number (not external_key)

for order_data in result.orders:
    order_number = order_data["order_number"]
    order_date = order_data["order_date"]
    customer_name = order_data["customer_name"]
    customer_code = order_data.get("customer_code")  # NEW: Extract from PDF
    
    # Check if sales order already exists BY ORDER NUMBER (not external_key)
    existing_order = (
        s.query(SalesOrder)
        .filter(SalesOrder.order_number == order_number)
        .first()
    )
    
    if existing_order:
        # Attach PDF to existing order
        _store_pdf_attachment(
            s,
            pdf_bytes=page_bytes,
            filename=f"{original_filename}_page_{page_num}.pdf",
            pdf_type="sales_order_page",
            sales_order_id=existing_order.id,
            distribution_entry_id=None,
            user=u,
        )
        
        # Update customer info if we have better data now
        if customer_code and not existing_order.customer.customer_code:
            existing_order.customer.customer_code = customer_code
        
        skipped_duplicates += 1
        continue
    
    # ... rest of order creation logic
```

#### 1.2 Remove External Key Uniqueness for Duplicate Detection
The current code uses `external_key = f"pdf:{order_number}:{order_date.isoformat()}"` which allows duplicates when dates differ. Change to use only order_number.

---

## PART 2: CUSTOMER CODE AS SOURCE OF TRUTH

### Current Problem
Customers are matched by facility name, which is unreliable. The Sales Order PDFs contain a "CUSTOMER NUMBER" field (e.g., "RANCHO", "PEARSCINE") that should be the primary identifier.

### Business Rule
**Customer Code is the canonical identifier.** All sales orders with the same CUSTOMER NUMBER should link to the same Customer record.

### Code Changes Required

#### 2.1 Add `customer_code` Field to Customer Model
**File:** `app/eqms/modules/customer_profiles/models.py`

```python
class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("idx_customers_company_key", "company_key"),
        Index("idx_customers_facility_name", "facility_name"),
        Index("idx_customers_state", "state"),
        Index("idx_customers_primary_rep_id", "primary_rep_id"),
        Index("idx_customers_customer_code", "customer_code"),  # NEW
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # NEW: Customer code from Sales Orders (e.g., "RANCHO", "PEARSCINE")
    customer_code: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)
    
    company_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    facility_name: Mapped[str] = mapped_column(Text, nullable=False)
    # ... rest unchanged
```

#### 2.2 Create Migration
**File:** `migrations/versions/xxxx_add_customer_code.py`

```python
"""Add customer_code to customers table

Revision ID: xxxx
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('customers', sa.Column('customer_code', sa.Text(), nullable=True))
    op.create_index('idx_customers_customer_code', 'customers', ['customer_code'])
    # Note: unique constraint added after data cleanup
    # op.create_unique_constraint('uq_customers_customer_code', 'customers', ['customer_code'])

def downgrade():
    op.drop_index('idx_customers_customer_code')
    op.drop_column('customers', 'customer_code')
```

#### 2.3 Update PDF Parser to Extract Customer Code
**File:** `app/eqms/modules/rep_traceability/parsers/pdf.py`

Add new function to extract customer number:

```python
def _parse_customer_number(text: str) -> str | None:
    """
    Extract CUSTOMER NUMBER from SILQ Sales Order PDF.
    
    Format: "CUSTOMER NUMBER: RANCHO" or "CUSTOMER NUMBER: PEARSCINE"
    """
    patterns = [
        r"CUSTOMER\s*NUMBER\s*[:\s]+([A-Z0-9\-]+)",
        r"ACCOUNT\s*(?:NUMBER|#)\s*[:\s]+([A-Z0-9\-]+)",
        r"CUST\s*(?:NO|#|CODE)\s*[:\s]+([A-Z0-9\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            code = match.group(1).strip().upper()
            # Filter out obviously wrong values
            if code and len(code) >= 2 and code not in ('NA', 'N/A', 'NONE', 'TBD'):
                return code
    return None
```

Update `_parse_silq_sales_order_page()` to include customer_code:

```python
def _parse_silq_sales_order_page(page, text: str, page_num: int) -> dict[str, Any] | None:
    # ... existing code ...
    
    customer_code = _parse_customer_number(text)  # NEW
    customer_name = _parse_sold_to_block(text) or "Unknown Customer"
    
    # ... rest of function ...
    
    return {
        "order_number": order_number,
        "order_date": order_date,
        "ship_date": order_date,
        "customer_name": customer_name,
        "customer_code": customer_code,  # NEW
        # ... rest of fields
    }
```

#### 2.4 Update Customer Matching to Prioritize Customer Code
**File:** `app/eqms/modules/customer_profiles/service.py`

Update `find_or_create_customer()`:

```python
def find_or_create_customer(
    s,
    *,
    facility_name: str,
    customer_code: str | None = None,  # NEW PARAMETER
    address1: str | None = None,
    # ... other params
) -> Customer:
    """
    Enhanced find-or-create with customer_code as primary identifier.
    
    Priority:
    1. customer_code (if provided and exists) - HIGHEST priority
    2. company_key (normalized facility name)
    3. address/email matching
    4. Create new
    """
    now = datetime.utcnow()
    
    # Priority 1: Match by customer_code (source of truth)
    if customer_code:
        customer_code_clean = customer_code.strip().upper()
        c = s.query(Customer).filter(Customer.customer_code == customer_code_clean).one_or_none()
        if c:
            # Update fields if needed
            _update_customer_fields(c, facility_name, address1, city, state, zip, contact_name, contact_email)
            return c
    
    # Priority 2: Exact match by company_key
    # ... existing code ...
    
    # Priority 3: Create new (set customer_code if provided)
    c = Customer(
        company_key=ck,
        facility_name=facility_name,
        customer_code=customer_code.strip().upper() if customer_code else None,  # NEW
        # ... rest of fields
    )
```

---

## PART 3: NRE PROJECTS (NON-CATHETER ORDERS)

### Current Problem
Sales orders that don't contain catheter products (211810SPT, 211610SPT, 211410SPT) are creating "Unknown Customer" entries that pollute the customer database. These are NRE (Non-Recurring Engineering) projects.

### Business Rule
- Sales orders without catheter SKUs are **NRE Projects**
- NRE customers should have sales orders but NO distributions
- Display NRE projects in a separate admin section

### Code Changes Required

#### 3.1 Identify NRE Orders During Import
**File:** `app/eqms/modules/rep_traceability/admin.py`

```python
# In sales_orders_import_pdf_bulk(), after parsing order items:

def _is_catheter_order(order_data: dict) -> bool:
    """Check if order contains any catheter SKUs."""
    CATHETER_SKUS = {'211810SPT', '211610SPT', '211410SPT'}
    for line in order_data.get("lines", []):
        if line.get("sku") in CATHETER_SKUS:
            return True
    return False

# Then in the processing loop:
is_nre = not _is_catheter_order(order_data)

if is_nre:
    # Create customer + sales order, but don't try to match distributions
    # Mark the customer or order somehow (e.g., order.notes = "NRE Project")
    pass
```

#### 3.2 Add NRE Projects Admin Page
**File:** `app/eqms/modules/nre_projects/__init__.py` (new module)

Create a new blueprint:

```python
# app/eqms/modules/nre_projects/__init__.py
from flask import Blueprint

bp = Blueprint("nre_projects", __name__, url_prefix="/admin/nre-projects")
```

**File:** `app/eqms/modules/nre_projects/admin.py`

```python
from flask import Blueprint, render_template
from sqlalchemy import func

from app.eqms.db import db_session
from app.eqms.rbac import require_permission
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import DistributionLogEntry, SalesOrder

bp = Blueprint("nre_projects", __name__, url_prefix="/admin/nre-projects")


@bp.get("/")
@require_permission("sales_orders.view")
def nre_projects_index():
    """
    NRE Projects dashboard.
    
    Shows customers who have sales orders but NO distributions.
    These are engineering/development customers, not product sales.
    """
    s = db_session()
    
    # Find customers with sales orders but no distributions
    customers_with_orders = (
        s.query(Customer.id)
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .distinct()
        .subquery()
    )
    
    customers_with_distributions = (
        s.query(Customer.id)
        .join(DistributionLogEntry, DistributionLogEntry.customer_id == Customer.id)
        .distinct()
        .subquery()
    )
    
    nre_customers = (
        s.query(Customer)
        .filter(Customer.id.in_(customers_with_orders))
        .filter(~Customer.id.in_(customers_with_distributions))
        .order_by(Customer.facility_name.asc())
        .all()
    )
    
    # Get order counts per customer
    order_counts = {}
    for c in nre_customers:
        count = s.query(SalesOrder).filter(SalesOrder.customer_id == c.id).count()
        order_counts[c.id] = count
    
    return render_template(
        "admin/nre_projects/index.html",
        nre_customers=nre_customers,
        order_counts=order_counts,
    )


@bp.get("/<int:customer_id>")
@require_permission("sales_orders.view")
def nre_customer_detail(customer_id: int):
    """Show sales orders for an NRE customer."""
    s = db_session()
    customer = s.query(Customer).filter(Customer.id == customer_id).one_or_none()
    if not customer:
        abort(404)
    
    orders = (
        s.query(SalesOrder)
        .filter(SalesOrder.customer_id == customer_id)
        .order_by(SalesOrder.order_date.desc())
        .all()
    )
    
    return render_template(
        "admin/nre_projects/detail.html",
        customer=customer,
        orders=orders,
    )
```

#### 3.3 Create NRE Templates
**File:** `app/eqms/templates/admin/nre_projects/index.html`

```html
{% extends "_layout.html" %}
{% block title %}NRE Projects{% endblock %}
{% block content %}
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
    <div>
      <h1 style="margin-top:0;">NRE Projects</h1>
      <p class="muted">Engineering customers with sales orders but no catheter distributions.</p>
    </div>
    <a class="button button--secondary" href="{{ url_for('admin.index') }}">← Back to Admin</a>
  </div>
</div>

<div style="height:14px;"></div>

{% if nre_customers %}
<div class="grid" style="grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px;">
  {% for customer in nre_customers %}
  <a href="{{ url_for('nre_projects.nre_customer_detail', customer_id=customer.id) }}" 
     class="card card--link" style="display:block; text-decoration:none;">
    <h3 style="margin:0 0 8px 0;">{{ customer.facility_name|e }}</h3>
    {% if customer.customer_code %}
    <div style="margin-bottom:8px;">
      <code style="background:rgba(102,163,255,0.1); padding:2px 8px; border-radius:4px; color:var(--primary);">
        {{ customer.customer_code|e }}
      </code>
    </div>
    {% endif %}
    <div class="muted" style="font-size:13px;">
      {{ order_counts.get(customer.id, 0) }} sales order{{ 's' if order_counts.get(customer.id, 0) != 1 else '' }}
    </div>
    {% if customer.city and customer.state %}
    <div class="muted" style="font-size:12px; margin-top:4px;">
      {{ customer.city|e }}, {{ customer.state|e }}
    </div>
    {% endif %}
  </a>
  {% endfor %}
</div>
{% else %}
<div class="card">
  <p class="muted" style="text-align:center; padding:40px;">No NRE projects found.</p>
</div>
{% endif %}
{% endblock %}
```

#### 3.4 Add NRE Card to Admin Home
**File:** `app/eqms/templates/admin/index.html`

Add after the Admin Tools card:

```html
{% if has_perm("sales_orders.view") %}
  <a class="card card--link" href="{{ url_for('nre_projects.nre_projects_index') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
    <h2 style="margin: 0;">NRE Projects</h2>
  </a>
{% endif %}
```

#### 3.5 Register Blueprint
**File:** `app/eqms/__init__.py`

```python
from app.eqms.modules.nre_projects.admin import bp as nre_projects_bp

# In create_app(), add:
app.register_blueprint(nre_projects_bp)
```

---

## PART 4: QUANTITY HANDLING (BOX OF 10)

### Current Problem
ShipStation entries may list quantities in boxes (e.g., "Box of 10") or individual units. The current `infer_units()` function handles some cases but may miss others.

### Current Implementation
```python
# app/eqms/modules/shipstation_sync/parsers.py
def infer_units(item_name: str, quantity: int) -> int:
    name = (item_name or "").lower()
    qty = int(quantity or 0)
    if qty <= 0:
        return 0
    if "10-pack" in name or "10 pack" in name or "10pk" in name:
        return qty * 10
    return qty
```

### Enhancement
**File:** `app/eqms/modules/shipstation_sync/parsers.py`

```python
def infer_units(item_name: str, quantity: int) -> int:
    """
    Convert ordered quantity to individual units.
    
    ShipStation item names may indicate:
    - "Box of 10" / "10-pack" → multiply by 10
    - "Case of 100" → multiply by 100
    - Individual units → return as-is
    
    Examples:
    - "Balloon Straight Tip, Box of 10" qty=5 → 50 units
    - "Balloon Catheter 18Fr" qty=5 → 5 units
    """
    name = (item_name or "").lower()
    qty = int(quantity or 0)
    if qty <= 0:
        return 0
    
    # Box of 10 patterns
    box_10_patterns = [
        "10-pack", "10 pack", "10pk", "box of 10", "bx of 10",
        "pack of 10", "pk of 10", "10/box", "10/pk",
    ]
    for pattern in box_10_patterns:
        if pattern in name:
            return qty * 10
    
    # Box of 5 patterns (less common)
    if "box of 5" in name or "5-pack" in name or "5 pack" in name:
        return qty * 5
    
    # Case of 100 (wholesale)
    if "case of 100" in name or "100/case" in name:
        return qty * 100
    
    # Default: individual units
    return qty
```

---

## PART 5: DATA RESET INSTRUCTIONS

### Before Running Import

1. **Backup Current Database** (if needed):
```bash
# On local:
cp eqms.db eqms_backup_$(date +%Y%m%d).db

# On DigitalOcean (via Console):
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

2. **Clear Existing Data** (choose appropriate level):

**Option A: Full Reset (recommended for clean start)**
```sql
-- Run via psql or database console
TRUNCATE distribution_lines CASCADE;
TRUNCATE distribution_log_entries CASCADE;
TRUNCATE sales_order_lines CASCADE;
TRUNCATE sales_orders CASCADE;
TRUNCATE order_pdf_attachments CASCADE;
TRUNCATE customer_notes CASCADE;
TRUNCATE customers CASCADE;

-- Reset sequences
ALTER SEQUENCE customers_id_seq RESTART WITH 1;
ALTER SEQUENCE sales_orders_id_seq RESTART WITH 1;
ALTER SEQUENCE distribution_log_entries_id_seq RESTART WITH 1;
```

**Option B: Clear Sales Orders + Distributions Only (keep customers)**
```sql
TRUNCATE distribution_lines CASCADE;
TRUNCATE distribution_log_entries CASCADE;
TRUNCATE sales_order_lines CASCADE;
TRUNCATE order_pdf_attachments CASCADE;
TRUNCATE sales_orders CASCADE;
```

3. **Run Migrations**:
```bash
alembic upgrade head
```

4. **Re-seed Admin User** (if using full reset):
```bash
python scripts/init_db.py
```

### Import Order

After reset, import data in this order:

1. **Sales Order PDFs First** - This creates customers with customer_codes
2. **ShipStation Sync** - This creates distributions and matches to existing orders/customers
3. **Any Additional PDFs** - Shipping labels, packing slips, etc.

### Verification Steps

After import, verify:

1. **No Duplicate Sales Orders**:
```sql
SELECT order_number, COUNT(*) as cnt 
FROM sales_orders 
GROUP BY order_number 
HAVING COUNT(*) > 1;
-- Should return 0 rows
```

2. **Customers Have Customer Codes**:
```sql
SELECT COUNT(*) as total, 
       COUNT(customer_code) as with_code,
       COUNT(*) - COUNT(customer_code) as without_code
FROM customers;
```

3. **NRE Customers Identified**:
```sql
SELECT c.id, c.facility_name, c.customer_code, 
       COUNT(DISTINCT so.id) as order_count,
       COUNT(DISTINCT d.id) as dist_count
FROM customers c
LEFT JOIN sales_orders so ON so.customer_id = c.id
LEFT JOIN distribution_log_entries d ON d.customer_id = c.id
GROUP BY c.id, c.facility_name, c.customer_code
HAVING COUNT(DISTINCT d.id) = 0 AND COUNT(DISTINCT so.id) > 0
ORDER BY c.facility_name;
```

---

## PART 6: ADDITIONAL ISSUES TO FIX

### 6.1 Remove SKU Constraint from SalesOrderLine
NRE orders may have non-catheter item codes (like "NRE"). Update the check constraint:

**File:** `app/eqms/modules/rep_traceability/models.py`

```python
class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"
    __table_args__ = (
        # REMOVE this constraint to allow NRE item codes:
        # CheckConstraint(
        #     "sku IN ('211810SPT','211610SPT','211410SPT')",
        #     name="ck_sales_order_lines_sku",
        # ),
        CheckConstraint(
            "quantity > 0",
            name="ck_sales_order_lines_quantity",
        ),
        # ... rest
    )
```

**Migration:**
```python
def upgrade():
    op.drop_constraint('ck_sales_order_lines_sku', 'sales_order_lines', type_='check')

def downgrade():
    op.create_check_constraint(
        'ck_sales_order_lines_sku',
        'sales_order_lines',
        "sku IN ('211810SPT','211610SPT','211410SPT')"
    )
```

### 6.2 Handle "Unknown Customer" Name
When customer name cannot be parsed, use customer_code as fallback:

```python
# In PDF parser:
customer_name = _parse_sold_to_block(text)
customer_code = _parse_customer_number(text)

if not customer_name or customer_name == "Unknown Customer":
    if customer_code:
        customer_name = f"Customer {customer_code}"
    else:
        customer_name = "Unknown Customer"
```

### 6.3 Link Multiple Distributions to Single Sales Order
The data model already supports this (SalesOrder has `distributions` relationship). Verify matching logic uses order_number, not just external_key.

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Database Schema
- [ ] Add `customer_code` column to `customers` table
- [ ] Create migration for `customer_code`
- [ ] Remove/relax SKU constraint on `sales_order_lines`
- [ ] Run `alembic upgrade head`

### Phase 2: PDF Parser Updates
- [ ] Add `_parse_customer_number()` function
- [ ] Update `_parse_silq_sales_order_page()` to return `customer_code`
- [ ] Update `_is_catheter_order()` helper function

### Phase 3: Customer Matching Logic
- [ ] Update `find_or_create_customer()` to prioritize `customer_code`
- [ ] Update PDF import to pass `customer_code` to customer creation

### Phase 4: Sales Order Deduplication
- [ ] Change duplicate detection from `external_key` to `order_number`
- [ ] Update PDF import to attach to existing orders rather than create duplicates

### Phase 5: NRE Projects Feature
- [ ] Create `app/eqms/modules/nre_projects/` module
- [ ] Create `admin.py` with routes
- [ ] Create templates (`index.html`, `detail.html`)
- [ ] Register blueprint in `__init__.py`
- [ ] Add NRE card to admin homepage

### Phase 6: Testing
- [ ] Clear test database
- [ ] Import sample Sales Order PDFs
- [ ] Verify customer_code is extracted
- [ ] Verify no duplicate sales orders
- [ ] Run ShipStation sync
- [ ] Verify distributions match to orders
- [ ] Check NRE Projects page

### Phase 7: Deploy
- [ ] Commit all changes: `git add . && git commit -m "Redesign customer profiling with customer_code support and NRE projects"`
- [ ] Push to remote: `git push origin main`
- [ ] Run migrations on production
- [ ] (Optional) Clear production data and re-import

---

## FILES MODIFIED SUMMARY

| File | Changes |
|------|---------|
| `app/eqms/modules/customer_profiles/models.py` | Add `customer_code` field |
| `app/eqms/modules/customer_profiles/service.py` | Prioritize `customer_code` in matching |
| `app/eqms/modules/rep_traceability/models.py` | Remove SKU constraint on order lines |
| `app/eqms/modules/rep_traceability/parsers/pdf.py` | Add `_parse_customer_number()` |
| `app/eqms/modules/rep_traceability/admin.py` | Deduplicate sales orders, pass customer_code |
| `app/eqms/modules/shipstation_sync/parsers.py` | Enhance `infer_units()` |
| `app/eqms/modules/nre_projects/__init__.py` | NEW: Blueprint |
| `app/eqms/modules/nre_projects/admin.py` | NEW: Routes |
| `app/eqms/templates/admin/nre_projects/index.html` | NEW: Template |
| `app/eqms/templates/admin/nre_projects/detail.html` | NEW: Template |
| `app/eqms/templates/admin/index.html` | Add NRE card |
| `app/eqms/__init__.py` | Register NRE blueprint |
| `migrations/versions/xxxx_add_customer_code.py` | NEW: Migration |
| `migrations/versions/xxxx_remove_sku_constraint.py` | NEW: Migration |

---

**END OF DEVELOPER PROMPT**
