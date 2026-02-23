# DEVELOPER AGENT PROMPT: Comprehensive System Overhaul
**Date:** February 8, 2026  
**Priority:** HIGH  
**Scope:** Full system audit, data reset improvements, equipment/supplies redesign

---

## CRITICAL PRINCIPLE

**The admin MUST be able to do everything from the web UI.**  
Do NOT require the admin to use the DigitalOcean console, SSH, or command line unless absolutely necessary (e.g., initial deployment). All data management, document uploads, edits, and resets should be accessible through the admin panel.

---

## OVERVIEW

This prompt covers three major areas:
1. **Recent Changes Verification** - Ensure all recent deployments work correctly
2. **Data Reset Process** - Improve the existing admin UI reset page (NO CONSOLE)
3. **Equipment & Supplies Redesign** - Major enhancement for document management

**Goal:** Create a robust, reliable system with full admin editing capabilities.

---

## ADMIN CAPABILITY SUMMARY

After implementation, the admin should be able to:

### Customers & Sales
- [ ] Reset all customer/sales data from `/admin/reset-data` (selective options)
- [ ] View and edit any customer profile
- [ ] View and edit NRE projects
- [ ] Upload/download/delete PDFs for any entity
- [ ] Sort customer lists by any column

### Equipment
- [ ] Create new equipment from admin panel
- [ ] Edit all equipment fields
- [ ] Upload Requirements Form (one per equipment)
- [ ] Upload Specification Document (one per equipment)
- [ ] Upload additional documents to categorized folders (calibration, manuals, quals)
- [ ] Download any document
- [ ] Delete documents
- [ ] Associate equipment with suppliers

### Supplies
- [ ] Create new supply from admin panel
- [ ] Edit all supply fields
- [ ] Upload Specification Document (one per supply)
- [ ] Upload additional documents (COAs, SDSs, etc.)
- [ ] Download/delete documents
- [ ] Associate supplies with suppliers

### System Administration
- [ ] Create/manage user accounts
- [ ] View system diagnostics
- [ ] Reset data (selective or full) via web UI
- [ ] Run ShipStation sync
- [ ] Import sales order PDFs

---

## SECTION 1: RECENT CHANGES VERIFICATION

### 1.1 Migration Fix
The migration `l2m3n4o5p6_shipstation_salesorder_redesign.py` was fixed to point to correct parent `k1l2m3n4o5`.

**Verify:**
- [ ] Deployment succeeded
- [ ] Migration applied (adds `customer_code` column, removes SKU constraint)
- [ ] No migration errors in logs

### 1.2 Customer List Changes
- Removed TYPE column (redundant)
- Added sortable columns
- Now only shows customers with distributions
- NRE customers appear in NRE Projects

**Test:**
- [ ] Customer list loads without errors
- [ ] Column sorting works (click headers)
- [ ] Customers with no distributions don't appear here

### 1.3 NRE Projects
- Added customer edit functionality
- Added PDF upload/download per sales order
- Added PDF delete capability

**Test:**
- [ ] NRE Projects page loads at `/admin/nre-projects/`
- [ ] Can edit customer name and customer_code
- [ ] Can upload PDF to a sales order
- [ ] Can download and delete PDFs

### 1.4 PDF Handling
- Distribution edit page now has PDF attachments section
- PDF upload/download added to distributions

**Test:**
- [ ] Distribution edit page shows PDF section
- [ ] Can upload PDF to distribution
- [ ] Can download PDFs

---

## SECTION 2: DATA RESET IMPROVEMENTS

### Current State
The reset data page exists at `/admin/reset-data` but needs enhancement.

### 2.1 Improve Reset Data Page

**File:** `app/eqms/templates/admin/reset_data.html`

Add these features:
1. **Selective Reset Options** - Allow resetting specific data types
2. **Pre-Reset Counts** - Show current counts before deletion
3. **Progress Indication** - Show what's being deleted
4. **Storage Cleanup** - Option to also delete stored PDFs

**Enhanced Template:**

```html
{% extends "_layout.html" %}
{% block title %}Reset Data{% endblock %}
{% block content %}
<div class="card" style="max-width: 800px; margin: 40px auto;">
    <h1 style="margin-top:0;">Data Reset Center</h1>
    <p class="muted">Reset system data to start fresh. This is a controlled process - no database console needed.</p>
    
    {# Current Data Counts #}
    <div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:16px; margin:20px 0;">
        <h3 style="margin-top:0;">Current Data</h3>
        <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:12px;">
            <div><strong>{{ counts.customers }}</strong> Customers</div>
            <div><strong>{{ counts.distributions }}</strong> Distributions</div>
            <div><strong>{{ counts.sales_orders }}</strong> Sales Orders</div>
            <div><strong>{{ counts.pdf_attachments }}</strong> PDF Attachments</div>
        </div>
    </div>
    
    {% if message %}
    <div style="border:1px solid {% if success %}#34d399{% else %}#f87171{% endif %}; border-radius:8px; padding:16px; margin:20px 0; background:{% if success %}rgba(52,211,153,0.1){% else %}rgba(248,113,113,0.1){% endif %};">
        <p style="margin:0;">{{ message }}</p>
        {% if deleted %}
        <details style="margin-top:12px;">
            <summary style="cursor:pointer;">Deletion Details</summary>
            <ul style="margin:10px 0 0 0; font-size:14px;">
                {% for key, value in deleted.items() %}
                <li>{{ key }}: {{ value if value >= 0 else 'truncated' }}</li>
                {% endfor %}
            </ul>
        </details>
        {% endif %}
    </div>
    {% endif %}
    
    {# Reset Options #}
    <form method="post" action="{{ url_for('admin.reset_data_post') }}" onsubmit="return confirmReset();">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        
        <h3>Reset Options</h3>
        <div style="margin:16px 0;">
            <label style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <input type="checkbox" name="reset_customers" value="1" checked>
                <span>Customers (includes notes and rep assignments)</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <input type="checkbox" name="reset_distributions" value="1" checked>
                <span>Distributions (includes distribution lines)</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <input type="checkbox" name="reset_sales_orders" value="1" checked>
                <span>Sales Orders (includes order lines)</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <input type="checkbox" name="reset_pdfs" value="1" checked>
                <span>PDF Attachments (database records)</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <input type="checkbox" name="reset_storage" value="1">
                <span>Also delete PDF files from storage</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                <input type="checkbox" name="reset_shipstation" value="1" checked>
                <span>ShipStation sync history</span>
            </label>
        </div>
        
        <div style="border-top:1px solid var(--border); padding-top:20px; margin-top:20px;">
            <div class="label">Type "DELETE ALL DATA" to confirm:</div>
            <input type="text" name="confirm_phrase" required placeholder="DELETE ALL DATA" style="margin-bottom:12px;">
            
            <label style="display:flex; align-items:center; gap:8px; margin-bottom:16px;">
                <input type="checkbox" name="dry_run" value="true">
                <span>Dry run only (preview what would be deleted)</span>
            </label>
            
            <div style="display:flex; gap:12px;">
                <a href="{{ url_for('admin.index') }}" class="button button--secondary">Cancel</a>
                <button type="submit" class="button button--danger">Reset Selected Data</button>
            </div>
        </div>
    </form>
</div>

<div class="card" style="max-width:800px; margin:20px auto;">
    <h3 style="margin-top:0;">After Reset</h3>
    <ol style="margin:0; padding-left:20px;">
        <li><strong>ShipStation Sync:</strong> Admin → ShipStation → Run Full Sync</li>
        <li><strong>Sales Order PDFs:</strong> Admin → Sales Orders → Import PDF</li>
        <li><strong>Verify:</strong> Check Customers and NRE Projects pages</li>
    </ol>
</div>

<script>
function confirmReset() {
    const phrase = document.querySelector('input[name="confirm_phrase"]').value;
    if (phrase !== 'DELETE ALL DATA') {
        alert('Please type "DELETE ALL DATA" exactly to confirm.');
        return false;
    }
    const dryRun = document.querySelector('input[name="dry_run"]').checked;
    if (!dryRun) {
        return confirm('Are you ABSOLUTELY SURE? This action cannot be undone!');
    }
    return true;
}
</script>
{% endblock %}
```

### 2.2 Update Reset Backend

**File:** `app/eqms/admin.py`

Update `reset_data_get` and `reset_data_post` to:

1. Pass current counts to template
2. Support selective reset options
3. Support storage cleanup (delete actual PDF files)

```python
@bp.get("/reset-data")
@require_permission("admin.edit")
def reset_data_get():
    """Show the reset data confirmation page with current counts."""
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote
    from app.eqms.modules.rep_traceability.models import (
        SalesOrder, DistributionLogEntry, OrderPdfAttachment
    )
    
    s = db_session()
    counts = {
        "customers": s.query(Customer).count(),
        "distributions": s.query(DistributionLogEntry).count(),
        "sales_orders": s.query(SalesOrder).count(),
        "pdf_attachments": s.query(OrderPdfAttachment).count(),
    }
    return render_template("admin/reset_data.html", counts=counts, message=None, success=False, deleted=None)


@bp.post("/reset-data")
@require_permission("admin.edit")
def reset_data_post():
    """Handle selective data reset."""
    from sqlalchemy import text
    from app.eqms.modules.customer_profiles.models import Customer, CustomerNote, CustomerRep
    from app.eqms.modules.rep_traceability.models import (
        SalesOrder, SalesOrderLine, DistributionLogEntry, DistributionLine,
        OrderPdfAttachment, TracingReport, ApprovalEml
    )
    from app.eqms.modules.shipstation_sync.models import ShipStationSyncRun, ShipStationSkippedOrder
    from app.eqms.storage import storage_from_config
    
    confirm_phrase = (request.form.get("confirm_phrase") or "").strip()
    if confirm_phrase != "DELETE ALL DATA":
        flash("You must type 'DELETE ALL DATA' exactly to confirm.", "danger")
        return redirect(url_for("admin.reset_data_get"))
    
    dry_run = request.form.get("dry_run") == "true"
    reset_customers = request.form.get("reset_customers") == "1"
    reset_distributions = request.form.get("reset_distributions") == "1"
    reset_sales_orders = request.form.get("reset_sales_orders") == "1"
    reset_pdfs = request.form.get("reset_pdfs") == "1"
    reset_storage = request.form.get("reset_storage") == "1"
    reset_shipstation = request.form.get("reset_shipstation") == "1"
    
    s = db_session()
    user = _current_user()
    deleted = {}
    errors = []
    
    if dry_run:
        # Just count what would be deleted
        if reset_pdfs:
            deleted["pdf_attachments"] = s.query(OrderPdfAttachment).count()
        if reset_distributions:
            deleted["distribution_lines"] = s.query(DistributionLine).count()
            deleted["distributions"] = s.query(DistributionLogEntry).count()
        if reset_sales_orders:
            deleted["sales_order_lines"] = s.query(SalesOrderLine).count()
            deleted["sales_orders"] = s.query(SalesOrder).count()
        if reset_customers:
            deleted["customer_notes"] = s.query(CustomerNote).count()
            deleted["customer_reps"] = s.query(CustomerRep).count()
            deleted["customers"] = s.query(Customer).count()
        if reset_shipstation:
            deleted["shipstation_sync_runs"] = s.query(ShipStationSyncRun).count()
            deleted["shipstation_skipped"] = s.query(ShipStationSkippedOrder).count()
        
        return render_template(
            "admin/reset_data.html",
            counts=deleted,
            message="DRY RUN - No data deleted. Counts show what would be deleted.",
            success=True,
            deleted=deleted,
        )
    
    # Actual deletion (order matters for FK constraints)
    try:
        # 1. Delete storage files if requested
        if reset_storage and reset_pdfs:
            storage = storage_from_config(current_app.config)
            attachments = s.query(OrderPdfAttachment).all()
            storage_deleted = 0
            for att in attachments:
                try:
                    storage.delete(att.storage_key)
                    storage_deleted += 1
                except Exception:
                    pass
            deleted["storage_files"] = storage_deleted
        
        # 2. PDF attachments
        if reset_pdfs:
            deleted["pdf_attachments"] = s.query(OrderPdfAttachment).delete()
        
        # 3. Distribution lines, then distributions
        if reset_distributions:
            deleted["distribution_lines"] = s.query(DistributionLine).delete()
            deleted["distributions"] = s.query(DistributionLogEntry).delete()
        
        # 4. Sales order lines, then sales orders
        if reset_sales_orders:
            deleted["sales_order_lines"] = s.query(SalesOrderLine).delete()
            deleted["sales_orders"] = s.query(SalesOrder).delete()
        
        # 5. Customer relations, then customers
        if reset_customers:
            deleted["customer_notes"] = s.query(CustomerNote).delete()
            deleted["customer_reps"] = s.query(CustomerRep).delete()
            deleted["customers"] = s.query(Customer).delete()
        
        # 6. ShipStation history
        if reset_shipstation:
            deleted["shipstation_skipped"] = s.query(ShipStationSkippedOrder).delete()
            deleted["shipstation_sync_runs"] = s.query(ShipStationSyncRun).delete()
        
        s.commit()
        
        # Audit
        from app.eqms.audit import record_event
        record_event(
            s, actor=user, action="maintenance.selective_reset",
            entity_type="System", entity_id="reset",
            metadata={"deleted": deleted},
        )
        s.commit()
        
        message = "Data reset completed successfully!"
        success = True
        
    except Exception as e:
        s.rollback()
        message = f"Reset failed: {str(e)}"
        success = False
        errors.append(str(e))
    
    # Get new counts
    counts = {
        "customers": s.query(Customer).count(),
        "distributions": s.query(DistributionLogEntry).count(),
        "sales_orders": s.query(SalesOrder).count(),
        "pdf_attachments": s.query(OrderPdfAttachment).count(),
    }
    
    return render_template(
        "admin/reset_data.html",
        counts=counts,
        message=message,
        success=success,
        deleted=deleted,
    )
```

### 2.3 Add Reset Link to Admin Tools

Ensure `/admin/reset-data` is accessible from Admin Tools page.

---

## SECTION 3: EQUIPMENT & SUPPLIES REDESIGN

### 3.1 Current State

Equipment and Supplies exist but need enhancement:
- Equipment has basic fields (code, description, manufacturer, etc.)
- ManagedDocument model exists for file attachments
- Supplier associations exist

### 3.2 New Requirements

#### Document Types

| Item Type | Requirements Form | Spec Document | Additional Docs Folder |
|-----------|-------------------|---------------|------------------------|
| Equipment | YES | YES | YES (calibration, manuals, quals, etc.) |
| Supplies  | NO  | YES | YES (COAs, specs, etc.) |

#### Folder Structure (Conceptual)
```
Equipment/
  ST-001 - PEDI System/
    Requirements Form.pdf
    Spec Document.pdf
    Calibration/
      Cal_2025-01-15.pdf
      Cal_2024-01-10.pdf
    Manuals/
      User Manual.pdf
    Qualification/
      IQ_OQ.pdf

Supplies/
  SP-S.SLQ001 - High Purity Water/
    Spec Document.pdf
    COAs/
      COA_Lot_12345.pdf
```

### 3.3 Database Changes

#### Update ManagedDocument Model

Add new fields for document categorization:

```python
# In app/eqms/modules/equipment/models.py

class ManagedDocument(Base):
    # ... existing fields ...
    
    # NEW: Document category for folder organization
    category: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default="general"
    )
    # Categories: "requirements_form", "spec_document", "calibration", 
    #             "manual", "qualification", "coa", "general"
    
    # NEW: Flag for primary documents
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # is_primary=True for Requirements Form and Spec Document
```

#### Create Migration

```python
# migrations/versions/xxxx_add_document_categories.py
"""Add document categories and is_primary flag.

Revision ID: n1o2p3q4r5
Revises: l2m3n4o5p6
Create Date: 2026-02-08
"""
from alembic import op
import sqlalchemy as sa

revision = "n1o2p3q4r5"
down_revision = "l2m3n4o5p6"


def upgrade():
    op.add_column(
        "managed_documents",
        sa.Column("category", sa.String(64), nullable=True, server_default="general")
    )
    op.add_column(
        "managed_documents",
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.create_index("idx_managed_docs_category", "managed_documents", ["category"])


def downgrade():
    op.drop_index("idx_managed_docs_category", table_name="managed_documents")
    op.drop_column("managed_documents", "is_primary")
    op.drop_column("managed_documents", "category")
```

### 3.4 Create Supplies Module

Currently equipment and supplies may be combined. Create a proper Supplies module:

#### Models

```python
# app/eqms/modules/supplies/models.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.eqms.models import Base


class Supply(Base):
    __tablename__ = "supplies"
    __table_args__ = (
        Index("idx_supplies_code", "supply_code"),
        Index("idx_supplies_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Required
    supply_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="Active")
    
    # Metadata
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    part_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    # Inventory
    min_stock_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_of_measure: Mapped[str | None] = mapped_column(String(32), nullable=True)
    
    # Notes
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Custom fields
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    supplier_associations: Mapped[list["SupplySupplier"]] = relationship(
        "SupplySupplier", back_populates="supply", cascade="all, delete-orphan"
    )
    documents: Mapped[list["SupplyDocument"]] = relationship(
        "SupplyDocument", back_populates="supply", cascade="all, delete-orphan"
    )


class SupplySupplier(Base):
    __tablename__ = "supply_suppliers"
    __table_args__ = (
        Index("idx_supply_suppliers_supply", "supply_id"),
        Index("idx_supply_suppliers_supplier", "supplier_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    
    supply: Mapped["Supply"] = relationship("Supply", back_populates="supplier_associations")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="supply_associations")


class SupplyDocument(Base):
    __tablename__ = "supply_documents"
    __table_args__ = (
        Index("idx_supply_docs_supply", "supply_id"),
        Index("idx_supply_docs_category", "category"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    supply_id: Mapped[int] = mapped_column(ForeignKey("supplies.id", ondelete="CASCADE"), nullable=False)
    
    # File info
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/pdf")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Categorization
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    # Categories: "spec_document", "coa", "sds", "general"
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    supply: Mapped["Supply"] = relationship("Supply", back_populates="documents")
```

### 3.5 Equipment Detail Page Redesign

**File:** `app/eqms/templates/admin/equipment/detail.html`

Create a tabbed interface showing:
1. **Overview** - Basic equipment info
2. **Requirements Form** - Single primary document
3. **Specification** - Single primary document  
4. **Documents** - Categorized folders (Calibration, Manuals, Qualification, etc.)
5. **Suppliers** - Associated suppliers
6. **Edit** - Edit equipment details

Key features:
- Upload buttons for each document category
- Download buttons for all documents
- Delete capability with confirmation
- Drag-and-drop upload support

### 3.6 Equipment Admin Routes

Add routes for document management:

```python
# In app/eqms/modules/equipment/admin.py

DOCUMENT_CATEGORIES = {
    "requirements_form": "Requirements Form",
    "spec_document": "Specification",
    "calibration": "Calibration",
    "manual": "Manual",
    "qualification": "Qualification",
    "general": "General",
}

@bp.post("/equipment/<int:equipment_id>/documents/<category>")
@require_permission("equipment.edit")
def equipment_upload_document(equipment_id: int, category: str):
    """Upload a document to a specific category."""
    if category not in DOCUMENT_CATEGORIES:
        flash("Invalid document category.", "danger")
        return redirect(url_for("equipment.equipment_detail", equipment_id=equipment_id))
    
    # ... upload logic with category and is_primary flag ...
    
    # For requirements_form and spec_document, mark as primary
    is_primary = category in ("requirements_form", "spec_document")
    
    # If uploading a primary doc, remove is_primary from existing docs of same category
    if is_primary:
        s.query(ManagedDocument).filter(
            ManagedDocument.equipment_id == equipment_id,
            ManagedDocument.category == category,
            ManagedDocument.is_primary == True,
        ).update({"is_primary": False})
    
    # ... rest of upload logic ...


@bp.get("/equipment/<int:equipment_id>/documents/<int:doc_id>/download")
@require_permission("equipment.view")
def equipment_download_document(equipment_id: int, doc_id: int):
    """Download a document."""
    # ... existing download logic ...


@bp.post("/equipment/<int:equipment_id>/documents/<int:doc_id>/delete")
@require_permission("equipment.edit")
def equipment_delete_document(equipment_id: int, doc_id: int):
    """Delete a document."""
    # ... existing delete logic ...
```

### 3.7 Document Naming Conventions

#### Equipment Requirements Forms
**Location:** `docs/EquipmentRequirementsForm/`
**Format:** `Equipment Requirements Form, Equip ID ST-XXX - Description.pdf`

Examples:
- `Equipment Requirements Form, Equip ID ST-001 - Portable Exchange Deionizers (PEDI) System.pdf`
- `Equipment Requirements Form, Equip ID ST-012 - Weighing Scale.pdf`

#### Specification Documents
**Location:** `docs/step1_rep_migration/`
**Format:** `SP-[Type].SLQ[Number] [Revision] Source Control Specification, Description.docx`

**Types:**
- `SP-E` = Equipment specs (matches to ST-XXX equipment)
- `SP-S` = Supplies specs (standalone supplies)
- `SP-C` = Components/Consumables (supplies)
- `SP-M` = Materials (supplies)

Examples:
- `SP-E.SLQ001 A Source Control Specification, Portable Exchange Deionizer (PEDI) System.docx` → Equipment ST-001
- `SP-E.SLQ013 B Source Control Specification, Weighing Scale.docx` → Equipment ST-012
- `SP-S.SLQ001 B Source Control Specification, High Purity Water.docx` → Supply (no equipment)

#### Mapping Equipment to Specs
| Equipment Code | Requirements Form | Spec Code | Description |
|----------------|-------------------|-----------|-------------|
| ST-001 | Yes | SP-E.SLQ001 | PEDI System |
| ST-002 | Yes | SP-E.SLQ002 | DI Water Tank |
| ST-003 | Yes | SP-E.SLQ004 | Waste Tank |
| ST-004 | Yes | SP-E.SLQ003 | Waste Diaphragm Pump |
| ST-005 | Yes | SP-E.SLQ006 | Diafiltration System |
| ST-006 | Yes | SP-E.SLQ010 | Floor Scale, Concentrate |
| ST-007 | Yes | SP-E.SLQ012 | Floor Scale, Suspension |
| ST-008 | Yes | SP-E.SLQ011 | Peristaltic Pump |
| ST-009 | Yes | SP-E.SLQ007 | Pneumatic Drum Stirrer |
| ST-010 | Yes | SP-E.SLQ009 | Concentrate Reactor |
| ST-011 | Yes | SP-E.SLQ008 | Fume Hood |
| ST-012 | Yes | SP-E.SLQ013 | Weighing Scale |
| ST-013 | Yes | SP-E.SLQ014 | Temp/Humidity Monitor |
| ST-014 | Yes | SP-E.SLQ015 | Spectrophotometer |
| ST-015 | Yes | (calibration std) | VIS Calibration Standard |
| ST-016 | Yes | SP-E.SLQ016 | Freeze Dry System |

### 3.8 File Parsing Functions

**File:** `app/eqms/modules/equipment/parsers/pdf.py` (create if needed)

```python
import re
from pathlib import Path

def parse_requirements_form_filename(filename: str) -> dict:
    """Parse Equipment Requirements Form filename.
    
    Args:
        filename: e.g. "Equipment Requirements Form, Equip ID ST-012 - Weighing Scale.pdf"
        
    Returns:
        {"equip_code": "ST-012", "description": "Weighing Scale"}
    """
    pattern = r"Equipment Requirements Form[,\s]+Equip ID (ST-\d+)\s*[-–]\s*(.+?)\.pdf$"
    match = re.search(pattern, filename, re.IGNORECASE)
    if match:
        return {
            "equip_code": match.group(1).upper(),
            "description": match.group(2).strip(),
        }
    return {}


def parse_spec_document_filename(filename: str) -> dict:
    """Parse Specification Document filename.
    
    Args:
        filename: e.g. "SP-E.SLQ013 B Source Control Specification, Weighing Scale.docx"
        
    Returns:
        {"spec_code": "SP-E.SLQ013", "revision": "B", "description": "Weighing Scale", 
         "type": "equipment"}
    """
    # Pattern: SP-[Type].SLQ[Number] [Revision] [Title], Description.docx
    pattern = r"(SP-[ESCM]\.SLQ\d+)\s+([A-Z])\s+(?:Source Control )?Specification[,\s]+(.+?)\.docx$"
    match = re.search(pattern, filename, re.IGNORECASE)
    if match:
        spec_code = match.group(1).upper()
        spec_type = "equipment" if "SP-E" in spec_code else "supply"
        return {
            "spec_code": spec_code,
            "revision": match.group(2).upper(),
            "description": match.group(3).strip(),
            "type": spec_type,
        }
    return {}


# Mapping between Equipment Codes and Spec Codes
EQUIPMENT_SPEC_MAP = {
    "ST-001": "SP-E.SLQ001",
    "ST-002": "SP-E.SLQ002",
    "ST-003": "SP-E.SLQ004",
    "ST-004": "SP-E.SLQ003",
    "ST-005": "SP-E.SLQ006",
    "ST-006": "SP-E.SLQ010",
    "ST-007": "SP-E.SLQ012",
    "ST-008": "SP-E.SLQ011",
    "ST-009": "SP-E.SLQ007",
    "ST-010": "SP-E.SLQ009",
    "ST-011": "SP-E.SLQ008",
    "ST-012": "SP-E.SLQ013",
    "ST-013": "SP-E.SLQ014",
    "ST-014": "SP-E.SLQ015",
    "ST-016": "SP-E.SLQ016",
}
```

### 3.9 Supplier Association

Equipment and Supplies should be linkable to Suppliers (optional). The relationship already exists in the Equipment model but needs UI support.

**UI Requirements:**
1. Equipment/Supply detail page shows associated suppliers
2. "Link Supplier" button opens modal with supplier dropdown
3. Can set relationship type (Manufacturer, Service Provider, Parts Supplier)
4. Can remove associations
5. Changes are audited

**Template snippet for supplier association:**

```html
{# Supplier Associations #}
<div class="card-section">
    <h3>Suppliers</h3>
    {% if equipment.supplier_associations %}
    <table class="table">
        <thead>
            <tr>
                <th>Supplier</th>
                <th>Relationship</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {% for assoc in equipment.supplier_associations %}
            <tr>
                <td>
                    <a href="{{ url_for('suppliers.supplier_detail', supplier_id=assoc.supplier_id) }}">
                        {{ assoc.supplier.name }}
                    </a>
                </td>
                <td>{{ assoc.relationship_type or 'General' }}</td>
                <td>
                    <form method="post" 
                          action="{{ url_for('equipment.remove_supplier', equipment_id=equipment.id, assoc_id=assoc.id) }}"
                          style="display:inline;">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        <button type="submit" class="button button--small button--danger"
                                onclick="return confirm('Remove this supplier association?')">
                            Remove
                        </button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <p class="muted">No suppliers linked.</p>
    {% endif %}
    
    <button type="button" class="button button--secondary" onclick="showLinkSupplierModal()">
        Link Supplier
    </button>
</div>

{# Link Supplier Modal #}
<div id="link-supplier-modal" class="modal" style="display:none;">
    <div class="modal-content">
        <h3>Link Supplier</h3>
        <form method="post" action="{{ url_for('equipment.add_supplier', equipment_id=equipment.id) }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            
            <label class="label">Supplier</label>
            <select name="supplier_id" required>
                <option value="">-- Select Supplier --</option>
                {% for supplier in all_suppliers %}
                <option value="{{ supplier.id }}">{{ supplier.name }}</option>
                {% endfor %}
            </select>
            
            <label class="label">Relationship Type</label>
            <select name="relationship_type">
                <option value="">General</option>
                <option value="Manufacturer">Manufacturer</option>
                <option value="Service Provider">Service Provider</option>
                <option value="Parts Supplier">Parts Supplier</option>
                <option value="Calibration Provider">Calibration Provider</option>
            </select>
            
            <div style="margin-top:16px;">
                <button type="button" class="button button--secondary" onclick="hideLinkSupplierModal()">Cancel</button>
                <button type="submit" class="button">Link Supplier</button>
            </div>
        </form>
    </div>
</div>
```

### 3.10 Bulk Import from docs Folder

Create admin route to import documents from the `docs/EquipmentRequirementsForm` and `docs/step1_rep_migration` folders:

```python
@bp.get("/equipment/bulk-import")
@require_permission("equipment.edit")
def equipment_bulk_import_get():
    """Show bulk import page."""
    import os
    
    # Scan docs folders for available files
    requirements_forms = []
    spec_documents = []
    
    req_folder = "docs/EquipmentRequirementsForm"
    if os.path.exists(req_folder):
        for f in os.listdir(req_folder):
            if f.endswith(".pdf"):
                requirements_forms.append(f)
    
    spec_folder = "docs/step1_rep_migration"
    if os.path.exists(spec_folder):
        for f in os.listdir(spec_folder):
            if f.endswith(".docx"):
                spec_documents.append(f)
    
    return render_template(
        "admin/equipment/bulk_import.html",
        requirements_forms=requirements_forms,
        spec_documents=spec_documents,
    )


@bp.post("/equipment/bulk-import")
@require_permission("equipment.edit")
def equipment_bulk_import_post():
    """Process bulk import of documents."""
    # For each file:
    # 1. Parse filename to extract equipment code
    # 2. Find or create equipment record
    # 3. Upload document to storage
    # 4. Create ManagedDocument record with appropriate category
    ...
```

---

## SECTION 4: ADMIN EDITING CAPABILITIES

### 4.1 Universal Edit Pattern

All admin pages should follow this pattern:
- View mode shows data in read-only format
- Edit button switches to edit mode or shows modal
- Changes require confirmation
- All changes are audited

### 4.2 Customer Editing

Already implemented. Verify:
- [ ] Can edit customer name (facility_name)
- [ ] Can edit customer_code
- [ ] Can edit address fields
- [ ] Can edit contact info
- [ ] Changes are audited

### 4.3 NRE Project Editing

Enhanced in recent changes:
- [ ] Can edit NRE customer name
- [ ] Can edit NRE customer code
- [ ] Can upload/download/delete PDFs per sales order

### 4.4 Distribution Editing

Enhanced in recent changes:
- [ ] Can edit distribution fields
- [ ] Can link to different sales order
- [ ] Can upload/download PDFs

### 4.5 Equipment/Supply Editing

Full CRUD operations:
- [ ] Create new equipment/supply
- [ ] Edit all fields
- [ ] Upload documents to categories
- [ ] Associate/remove suppliers
- [ ] Delete with confirmation

---

## SECTION 5: IMPLEMENTATION ORDER

### Phase 1: Verification (Immediate)
1. Verify recent deployment works
2. Test customer list sorting
3. Test NRE projects edit/upload
4. Test distribution PDF upload

### Phase 2: Data Reset Enhancement
1. Update reset_data.html template
2. Update reset_data_get() to pass counts
3. Update reset_data_post() for selective reset
4. Test dry run and actual reset

### Phase 3: Equipment Enhancement
1. Add migration for document categories
2. Update ManagedDocument model
3. Update equipment detail template with tabs
4. Add category-based upload routes
5. Test document organization

### Phase 4: Supplies Module
1. Create supplies models
2. Create supplies admin routes
3. Create supplies templates
4. Register blueprint
5. Add migration for new tables

### Phase 5: Bulk Import
1. Create bulk import page
2. Implement file scanning
3. Implement document parsing
4. Test with sample files

---

## SECTION 6: TESTING CHECKLIST

After implementation:

### Data Reset
- [ ] Can access /admin/reset-data
- [ ] Current counts display correctly
- [ ] Dry run shows what would be deleted
- [ ] Selective reset works (only checked items deleted)
- [ ] Storage cleanup works (optional)
- [ ] Audit event recorded

### Equipment
- [ ] Equipment list loads
- [ ] Can create new equipment
- [ ] Can edit equipment
- [ ] Can upload Requirements Form
- [ ] Can upload Specification
- [ ] Can upload to document categories
- [ ] Can download documents
- [ ] Can delete documents
- [ ] Can associate suppliers

### Supplies
- [ ] Supplies list loads
- [ ] Can create new supply
- [ ] Can edit supply
- [ ] Can upload Specification
- [ ] Can upload COAs and other docs
- [ ] Can associate suppliers

---

## SECTION 7: COMMIT INSTRUCTIONS

After implementing all changes:

```bash
git add -A
git commit -m "Comprehensive system overhaul: data reset, equipment/supplies

Data Reset:
- Enhanced reset page with selective options
- Pre-reset counts display
- Dry run capability
- Optional storage cleanup

Equipment:
- Document category system
- Tabbed detail page
- Requirements Form / Spec sections
- Categorized document folders

Supplies:
- New supplies module
- Full CRUD operations
- Document management
- Supplier associations

Admin Capabilities:
- Full editing on all entities
- Audit trail for all changes
"

git push origin main
```

---

## SECTION 8: POST-DEPLOYMENT

After deployment (migrations run automatically via release phase):

1. **Verify Migration Applied:**
   - Check runtime logs for "Running Alembic migrations..." success
   - If migration fails, check for duplicate head revisions (fix `down_revision`)

2. **Test Reset Page:**
   - Navigate to `/admin/reset-data`
   - Verify current counts display
   - Do a dry run first (checkbox)
   - Then actual reset if needed

3. **Test Equipment:**
   - Navigate to `/admin/equipment/`
   - Try bulk import from docs folder
   - Verify documents are categorized correctly

4. **Upload Fresh Data:**
   - Navigate to Admin homepage
   - ShipStation → Run Full Sync
   - Sales Orders → Import PDF
   - Verify customer/NRE classification on respective pages

---

## SECTION 9: KNOWN FILE LOCATIONS

### Source Documents (for bulk import reference)
```
docs/EquipmentRequirementsForm/
├── Equipment Requirements Form, Equip ID ST-001 - Portable Exchange Deionizers (PEDI) System.pdf
├── Equipment Requirements Form, Equip ID ST-002 - DI Water Tank Assembly, 750 gallon.pdf
├── ...
├── Equipment Requirements Form, Equip ID ST-016, Freeze Dry System, 2.5 Liter.pdf
└── Silq Equipment Master List.xlsx

docs/step1_rep_migration/
├── SP-E.SLQ001 A Source Control Specification, Portable Exchange Deionizer (PEDI) System.docx
├── SP-E.SLQ002 A Source Control Specification, High Purity Water Tank Assembly, 750 gallon.docx
├── ...
├── SP-S.SLQ001 B Source Control Specification, High Purity Water.docx
├── SP-S.SLQ002 A Source Control Specification, Centrifuge Tube, 50mL, Polypropylene, Flat Cap.docx
└── ... (many more supplies)
```

### Key Application Files
```
app/eqms/admin.py                           # Reset data routes, admin tools
app/eqms/modules/equipment/admin.py         # Equipment CRUD, document upload
app/eqms/modules/equipment/models.py        # Equipment, ManagedDocument models
app/eqms/modules/supplies/                  # To be created (new module)
app/eqms/modules/customer_profiles/admin.py # Customer list, edit
app/eqms/modules/nre_projects/admin.py      # NRE projects
app/eqms/modules/rep_traceability/admin.py  # Sales orders, distributions
app/eqms/templates/admin/reset_data.html    # Reset data page template
app/eqms/templates/admin/equipment/         # Equipment templates
```

---

**END OF DEVELOPER PROMPT**
