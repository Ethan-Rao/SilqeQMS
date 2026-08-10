# DEBUG AGENT: Final System Review & Purchasing Implementation
**Date:** February 8, 2026  
**Priority:** HIGH  
**Mode:** Autonomous - implement all changes and push

---

## MISSION OVERVIEW

1. **Push all uncommitted changes** to main
2. **Review all admin dashboard subsystems** for functionality
3. **Implement new Purchasing module** (Purchase Orders with PDF import + confirmation files)
4. **Output findings** to `docs/audits/SUBSYSTEM_REVIEW_2026_02_08.md`
5. **Push final implementation** to main

---

## PHASE 1: COMMIT CURRENT CHANGES

### 1.1 Current Uncommitted Changes

```
Modified:
- app/eqms/modules/shipstation_sync/service.py
- app/eqms/modules/suppliers/models.py
- app/eqms/templates/admin/sales_orders/unmatched_pdfs.html
- app/eqms/templates/public/index.html

New files to add:
- docs/audits/SYSTEM_AUDIT_FINDINGS_2026_02_08.md
- docs/plans/*.md (multiple planning documents)
```

### 1.2 Commit and Push

```bash
git add -A
git status

git commit -m "$(cat <<'EOF'
System audit and planning documents

Changes:
- ShipStation sync service updates
- Supplier models updates
- Unmatched PDFs template fixes
- Public index updates

Documentation:
- System audit findings
- Multiple planning and debug agent prompts
- Equipment requirements and specifications docs
EOF
)"

git push origin main
```

---

## INITIAL REVIEW FINDINGS (Pre-Debug)

The following has already been verified during initial review:

### VERIFIED WORKING:
1. **CSRF Token Bug** - FIXED. All templates now use `{{ csrf_token }}` (no parentheses)
2. **Supplies Permissions** - FIXED. Now uses `supplies.view`, `supplies.create`, etc.
3. **Permission Seeding** - VERIFIED. `scripts/init_db.py` has all supplies permissions defined and assigned to admin
4. **Reset Data Page** - VERIFIED. Template renders correctly with proper CSRF token

### NAVIGATION MENU ALIGNMENT:
The top navigation currently includes:
- Home, Admin, Distribution Log, Customers, Sales Dashboard, Equipment, Manufacturing

This does NOT fully align with the dashboard columns. Consider simplifying to just:
- Home, Admin (with dropdown or rely on dashboard)

Or expand to include the three column categories as dropdowns.

**Recommendation for Debug Agent**: The navigation menu update is a lower priority - focus on functionality first.

---

## PHASE 2: SUBSYSTEM REVIEW

Review each admin dashboard card/module for:
- [ ] Route exists and loads without error
- [ ] CRUD operations work (if applicable)
- [ ] Permissions are correct
- [ ] Templates render properly
- [ ] Data persistence works

### 2.1 Quality Management Column

| Card | Route | Status | Review Notes |
|------|-------|--------|--------------|
| Quality Management Documents | `admin.qms_documents` | STUB | Placeholder - "Coming Soon" |
| Document Control (DCOs) | `doc_control.list_documents` | IMPLEMENTED | Full CRUD + file upload |
| Employee Training | `admin.employee_training` | STUB | Placeholder - "Coming Soon" |
| Management Reviews | `admin.management_reviews` | STUB | Placeholder - "Coming Soon" |
| Admin Tools | `admin.diagnostics` | IMPLEMENTED | System status, data reset, accounts |
| My Account | `admin.me` | IMPLEMENTED | Profile view |

**Review Tasks:**
- [ ] Verify Document Control list/create/detail/release/obsolete cycle
- [ ] Verify Admin Tools → Reset Data works
- [ ] Verify Admin Tools → Accounts works
- [ ] Confirm stub pages display "Coming Soon" properly

### 2.2 Silq Operations Column

| Card | Route | Status | Review Notes |
|------|-------|--------|--------------|
| Manufacturing | `manufacturing.manufacturing_index` | IMPLEMENTED | Lot tracking, documents |
| Equipment | `equipment.equipment_list` | IMPLEMENTED | Full CRUD + documents |
| Supplies | `supplies.supplies_list` | IMPLEMENTED | Full CRUD + documents |
| NCRs | `admin.ncrs` | STUB | Placeholder - "Coming Soon" |
| CAPAs | `admin.capas` | STUB | Placeholder - "Coming Soon" |

**Review Tasks:**
- [ ] Verify Equipment list/create/edit/detail works
- [ ] Verify Equipment document upload/download
- [ ] Verify Equipment bulk import page loads
- [ ] Verify Supplies list/create/edit/detail works
- [ ] Verify Manufacturing lot list/create/edit
- [ ] Verify Manufacturing document upload

### 2.3 External Relationships Column

| Card | Route | Status | Review Notes |
|------|-------|--------|--------------|
| Distribution Log | `rep_traceability.distribution_log_list` | IMPLEMENTED | Full CRUD + CSV import |
| Sales Dashboard | `rep_traceability.sales_dashboard` | IMPLEMENTED | Metrics and tracking |
| Customers | `customer_profiles.customers_list` | IMPLEMENTED | Full CRUD + merge |
| Suppliers | `suppliers.suppliers_list` | IMPLEMENTED | Full CRUD + documents |
| NRE Projects | `nre_projects.nre_projects_index` | IMPLEMENTED | Customer orders without distributions |

**Review Tasks:**
- [ ] Verify Distribution Log list/create/edit
- [ ] Verify Sales Order PDF import works
- [ ] Verify Sales Dashboard loads with correct data
- [ ] Verify Customers list/detail/edit
- [ ] Verify Suppliers list/create/edit/detail
- [ ] Verify NRE Projects shows correct customers

---

## PHASE 3: IMPLEMENT PURCHASING MODULE

### 3.1 Module Overview

**Purchasing** will track purchase orders from suppliers, similar to Distribution Log but for incoming goods.

**Features:**
- Purchase Order list with filters
- PO creation (manual entry)
- PDF import (similar to Sales Order PDF import)
- Confirmation file attachment (PDF or .eml)
- .eml file viewing capability

### 3.2 Database Models

**File:** `app/eqms/modules/purchasing/models.py`

```python
from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Index, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.eqms.models import Base


class PurchaseOrder(Base):
    """Purchase order from a supplier."""
    __tablename__ = "purchase_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','received','partial','cancelled')",
            name="ck_purchase_orders_status",
        ),
        Index("idx_purchase_orders_supplier_id", "supplier_id"),
        Index("idx_purchase_orders_po_number", "po_number"),
        Index("idx_purchase_orders_order_date", "order_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # PO identification
    po_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Supplier
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)
    
    # Status
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    
    # Details
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier", lazy="selectin")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="purchase_order", cascade="all, delete-orphan", lazy="selectin"
    )
    attachments: Mapped[list["PurchaseOrderAttachment"]] = relationship(
        "PurchaseOrderAttachment", back_populates="purchase_order", cascade="all, delete-orphan", lazy="selectin"
    )


class PurchaseOrderLine(Base):
    """Line item on a purchase order."""
    __tablename__ = "purchase_order_lines"
    __table_args__ = (
        Index("idx_po_lines_purchase_order_id", "purchase_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    
    item_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")


class PurchaseOrderAttachment(Base):
    """Attachment (PDF, EML) for a purchase order."""
    __tablename__ = "purchase_order_attachments"
    __table_args__ = (
        CheckConstraint(
            "attachment_type IN ('po_pdf','confirmation_pdf','confirmation_eml','other')",
            name="ck_po_attachments_type",
        ),
        Index("idx_po_attachments_purchase_order_id", "purchase_order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    
    # File metadata
    attachment_type: Mapped[str] = mapped_column(String(32), nullable=False)  # po_pdf, confirmation_pdf, confirmation_eml
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="attachments")
```

### 3.3 Admin Routes

**File:** `app/eqms/modules/purchasing/admin.py`

Create routes for:
- `GET /purchasing/` - List purchase orders
- `GET /purchasing/new` - New PO form
- `POST /purchasing/new` - Create PO
- `GET /purchasing/<id>` - PO detail
- `GET /purchasing/<id>/edit` - Edit PO form
- `POST /purchasing/<id>/edit` - Update PO
- `POST /purchasing/<id>/upload` - Upload attachment (PDF or EML)
- `GET /purchasing/attachments/<id>/download` - Download attachment
- `GET /purchasing/attachments/<id>/view` - View EML file (render as HTML)
- `GET /purchasing/import-pdf` - PDF import page
- `POST /purchasing/import-pdf` - Process PDF import

### 3.4 EML File Viewing

For .eml files, create a viewer that renders the email content:

```python
import email
from email import policy

def parse_eml_file(eml_bytes: bytes) -> dict:
    """Parse EML file and extract viewable content."""
    msg = email.message_from_bytes(eml_bytes, policy=policy.default)
    
    result = {
        "from": msg.get("From", ""),
        "to": msg.get("To", ""),
        "cc": msg.get("Cc", ""),
        "subject": msg.get("Subject", ""),
        "date": msg.get("Date", ""),
        "body_text": "",
        "body_html": "",
        "attachments": [],
    }
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                result["body_text"] = part.get_content()
            elif content_type == "text/html":
                result["body_html"] = part.get_content()
            elif part.get_filename():
                result["attachments"].append({
                    "filename": part.get_filename(),
                    "content_type": content_type,
                })
    else:
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            result["body_text"] = msg.get_content()
        elif content_type == "text/html":
            result["body_html"] = msg.get_content()
    
    return result
```

### 3.5 Templates

Create these templates:
- `app/eqms/templates/admin/purchasing/list.html`
- `app/eqms/templates/admin/purchasing/new.html`
- `app/eqms/templates/admin/purchasing/detail.html`
- `app/eqms/templates/admin/purchasing/edit.html`
- `app/eqms/templates/admin/purchasing/import.html`
- `app/eqms/templates/admin/purchasing/view_eml.html`

### 3.6 Add Permissions

**File:** `scripts/init_db.py`

Add purchasing permissions:
```python
# Purchasing (P0)
p_purchasing_view = ensure_perm("purchasing.view", "Purchasing: view")
p_purchasing_create = ensure_perm("purchasing.create", "Purchasing: create")
p_purchasing_edit = ensure_perm("purchasing.edit", "Purchasing: edit")
p_purchasing_upload = ensure_perm("purchasing.upload", "Purchasing: upload")
```

Add to admin role.

### 3.7 Add to Dashboard

**File:** `app/eqms/templates/admin/index.html`

Add Purchasing card to **Silq Operations** column (after Supplies):

```html
{% if has_perm("purchasing.view") %}
<a class="card card--link" href="{{ url_for('purchasing.purchasing_list') }}" style="padding: 20px;">
  <h3 style="margin: 0; font-size: 16px;">Purchasing</h3>
  <p class="muted" style="margin: 6px 0 0; font-size: 13px;">Purchase orders and supplier confirmations</p>
</a>
{% endif %}
```

### 3.8 Register Blueprint

**File:** `app/eqms/__init__.py`

Add:
```python
from app.eqms.modules.purchasing.admin import bp as purchasing_bp
# ...
app.register_blueprint(purchasing_bp, url_prefix="/admin")
```

### 3.9 PDF Import Parser

The PO PDFs will be similar to Sales Order PDFs. Create a parser that extracts:
- PO Number
- Date
- Supplier name
- Line items (if parseable)

**File:** `app/eqms/modules/purchasing/parsers/pdf.py`

```python
import re
from datetime import date
import pdfplumber

def parse_purchase_order_pdf(pdf_bytes: bytes) -> dict:
    """Parse a purchase order PDF and extract key fields."""
    result = {
        "po_number": None,
        "order_date": None,
        "supplier_name": None,
        "items": [],
        "raw_text": "",
    }
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            result["raw_text"] += text + "\n"
            
            # Look for PO Number patterns
            po_match = re.search(r'(?:PO|P\.O\.|Purchase\s*Order)\s*(?:#|No\.?|Number)?\s*:?\s*(\d+)', text, re.I)
            if po_match and not result["po_number"]:
                result["po_number"] = po_match.group(1)
            
            # Look for date patterns
            date_match = re.search(r'(?:Date|Order\s*Date)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.I)
            if date_match and not result["order_date"]:
                # Parse date string to date object
                result["order_date"] = _parse_date(date_match.group(1))
    
    return result


def _parse_date(date_str: str) -> date | None:
    """Parse common date formats."""
    import re
    from datetime import datetime
    
    patterns = [
        (r'(\d{1,2})/(\d{1,2})/(\d{4})', '%m/%d/%Y'),
        (r'(\d{1,2})-(\d{1,2})-(\d{4})', '%m-%d-%Y'),
        (r'(\d{1,2})/(\d{1,2})/(\d{2})', '%m/%d/%y'),
    ]
    
    for pattern, fmt in patterns:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    return None
```

### 3.10 Create Migration

Create Alembic migration for new tables:
```bash
alembic revision --autogenerate -m "Add purchasing module tables"
```

**IMPORTANT**: After creating the migration, verify it has the correct `down_revision` pointing to the latest existing migration to avoid multiple heads.

---

## PHASE 4: CRITICAL FUNCTIONALITY CHECKS

Before completing the review, verify these specific high-risk areas:

### 4.1 Sales Order PDF Import
**Route:** `/admin/sales-orders/import-pdf`

Check:
- [ ] Page loads without error
- [ ] File upload accepts PDF
- [ ] Multi-page PDFs are split correctly
- [ ] Order numbers are extracted
- [ ] Customer matching works (by customer_code)
- [ ] Duplicate order numbers attach PDF to existing order (not create new)

### 4.2 ShipStation Sync
**Route:** `/admin/shipstation`

Check:
- [ ] Page loads without error
- [ ] Connection status displays correctly
- [ ] "Run Full Sync" button works
- [ ] Quantity inference handles "box of 10" patterns
- [ ] Distributions are created with correct quantities

### 4.3 Equipment Bulk Import
**Route:** `/admin/equipment/bulk-import`

Check:
- [ ] Page loads without error
- [ ] Requirements Form PDFs are parsed
- [ ] Specification PDFs are matched
- [ ] Equipment records are created with documents attached

### 4.4 Data Reset
**Route:** `/admin/reset-data`

Check:
- [ ] Page loads without error
- [ ] Dry run shows correct counts
- [ ] Actual reset deletes selected data
- [ ] Confirmation phrase validation works

### 4.5 NRE Projects
**Route:** `/admin/nre-projects`

Check:
- [ ] Page loads without error
- [ ] Shows customers with sales orders but no distributions
- [ ] Customer details are viewable

---

## PHASE 5: OUTPUT FINDINGS

Create findings document at: `docs/audits/SUBSYSTEM_REVIEW_2026_02_08.md`

This document will be reviewed by the planning agent, enhanced/corrected, and then passed to the dev agent for implementation.

### Document Format

```markdown
# Subsystem Review Findings - 2026-02-08

## Summary
[Brief summary of overall system status]

## Quality Management Column

### Quality Management Documents
- **Status:** STUB
- **Route:** `/admin/qms-documents`
- **Functionality:** Placeholder page displays correctly
- **Issues:** None (intentional placeholder)

### Document Control (DCOs)
- **Status:** IMPLEMENTED
- **Route:** `/admin/doc-control/`
- **Functionality:** 
  - [ ] List documents - PASS/FAIL
  - [ ] Create document - PASS/FAIL
  - [ ] Upload file - PASS/FAIL
  - [ ] Release revision - PASS/FAIL
  - [ ] Create new revision - PASS/FAIL
  - [ ] Obsolete document - PASS/FAIL
  - [ ] Download file - PASS/FAIL
- **Issues:** [List any issues found]

[Continue for each card...]

## Silq Operations Column
[...]

## External Relationships Column
[...]

## New Purchasing Module

### Implementation Status
- [ ] Models created
- [ ] Migration created and applied
- [ ] Admin routes implemented
- [ ] Templates created
- [ ] Permissions added
- [ ] Blueprint registered
- [ ] Dashboard card added

### Functionality Verified
- [ ] List POs
- [ ] Create PO
- [ ] Edit PO
- [ ] Upload PDF attachment
- [ ] Upload EML confirmation
- [ ] View EML file
- [ ] Download attachments

## Recommendations
1. [List any recommendations]

## Issues Requiring Dev Agent Attention
1. [List any issues that need implementation fixes]
```

---

## PHASE 6: FINAL COMMIT AND PUSH

After all implementation and review:

```bash
git add -A
git status

git commit -m "$(cat <<'EOF'
Add Purchasing module and complete subsystem review

Purchasing Module:
- New module for tracking purchase orders
- PDF import functionality (similar to sales orders)
- Confirmation file support (PDF and EML)
- EML file viewer for email confirmations
- Full CRUD operations

Database:
- purchase_orders table
- purchase_order_lines table
- purchase_order_attachments table
- New purchasing.* permissions

Dashboard:
- Add Purchasing card to Silq Operations column

Documentation:
- Complete subsystem review findings
EOF
)"

git push origin main
```

---

## FILE STRUCTURE FOR NEW MODULE

```
app/eqms/modules/purchasing/
├── __init__.py
├── admin.py          # Flask routes
├── models.py         # SQLAlchemy models
├── service.py        # Business logic, EML parsing
└── parsers/
    └── pdf.py        # PO PDF parsing (if needed)

app/eqms/templates/admin/purchasing/
├── list.html
├── new.html
├── detail.html
├── edit.html
├── import.html
└── view_eml.html
```

---

## VERIFICATION CHECKLIST

Before final push, verify:

- [ ] All uncommitted changes pushed
- [ ] Purchasing module fully implemented
- [ ] All routes load without 500 errors
- [ ] Permissions work correctly
- [ ] EML viewer renders email content
- [ ] PDF upload/download works
- [ ] Dashboard card appears for users with permission
- [ ] Migration applies cleanly
- [ ] Findings document is complete

---

---

## EXPECTED WORKFLOW

1. **Debug Agent** executes this prompt:
   - Commits and pushes current changes
   - Reviews all subsystems
   - Implements Purchasing module
   - Creates `docs/audits/SUBSYSTEM_REVIEW_2026_02_08.md` with findings
   - Commits and pushes final implementation

2. **Planning Agent** (me) reviews the findings document:
   - Enhances/corrects any issues found
   - Adds implementation details as needed
   - Creates `docs/plans/DEV_AGENT_FIXES_2026_02_08.md`

3. **Dev Agent** implements any remaining fixes from the findings

---

## CRITICAL NOTES

1. **DO NOT** skip the uncommitted changes push - this must happen first
2. **DO** create the migration with correct `down_revision` to avoid multiple heads
3. **DO** test each route loads before marking as PASS
4. **DO** include code snippets in findings for any issues requiring fixes
5. **DO** use proper CSRF token handling: `{{ csrf_token }}` (not `{{ csrf_token() }}`)

---

**END OF DEBUG AGENT PROMPT**
