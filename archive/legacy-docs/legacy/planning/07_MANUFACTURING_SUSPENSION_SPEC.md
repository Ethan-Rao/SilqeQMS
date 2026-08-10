# Manufacturing Module - Suspension Implementation Spec

**Date:** 2026-01-15  
**Phase:** 1 (Manufacturing module structure + Suspension lot tracking)  
**Purpose:** Developer-ready specification for Manufacturing module with Suspension lot records and per-lot document management

---

## 1) Executive Summary

### What Is Being Added

**Manufacturing Module (New):**
- New Manufacturing module with product-specific subfolders
- **Suspension** submodule: Production lot tracking with per-lot document storage
- **ClearTract Foley Catheters** placeholder: Structure created, workflows deferred

**Suspension Lot Management:**
- Lot creation and tracking (lot numbers, status workflow)
- Per-lot document storage (Traveler, QC reports, COAs, labels, release evidence)
- Status workflow: Draft → In-Process → Quarantined → Released/Rejected
- Linkage to equipment and materials (from Equipment & Supplies module)

### Global Naming Change

**Important:** The module currently titled **"Equipment"** must be renamed to **"Equipment & Supplies"** in:
- Navigation labels
- Module documentation
- UI cards/links
- README module list

**Rationale:** This module stores documentation for both equipment AND supplies/materials (COAs, receiving inspections, supplier docs, etc.).

---

## 2) Information Architecture + Admin Navigation

### Proposed Admin Routes

**Manufacturing Landing:**
- `GET /admin/manufacturing` → Manufacturing landing page (product selection: Suspension, ClearTract Foley Catheters)

**Suspension Routes:**
- `GET /admin/manufacturing/suspension` → Suspension lot list (search, filters)
- `GET /admin/manufacturing/suspension/new` → Create lot form
- `POST /admin/manufacturing/suspension/new` → Create lot
- `GET /admin/manufacturing/suspension/<lot_id>` → Lot detail (metadata + documents + equipment/materials)
- `GET /admin/manufacturing/suspension/<lot_id>/edit` → Edit lot form
- `POST /admin/manufacturing/suspension/<lot_id>/edit` → Update lot
- `POST /admin/manufacturing/suspension/<lot_id>/status` → Change status (with validation)
- `POST /admin/manufacturing/suspension/<lot_id>/documents/upload` → Upload document
- `GET /admin/manufacturing/suspension/<lot_id>/documents/<doc_id>/download` → Download document
- `POST /admin/manufacturing/suspension/<lot_id>/documents/<doc_id>/delete` → Delete document (soft-delete)

**ClearTract Foley Catheters (Placeholder):**
- `GET /admin/manufacturing/cleartract-foley-catheters` → Placeholder page ("Coming soon" or similar)

**Blueprint Registration:**
- Manufacturing: `app/eqms/modules/manufacturing/admin.py` → `bp = Blueprint("manufacturing", __name__)`
  - Register in `app/eqms/__init__.py`: `app.register_blueprint(manufacturing_bp, url_prefix="/admin/manufacturing")`

---

### Sidebar Navigation

**Update:** `app/eqms/templates/admin/index.html`:

**Manufacturing:**
- Link: `{{ url_for('manufacturing.manufacturing_index') }}`
- Label: "Manufacturing"

**Equipment & Supplies (Renamed):**
- Link: `{{ url_for('equipment.equipment_list') }}` (or existing route)
- Label: "Equipment & Supplies" (changed from "Equipment")

---

## 3) Data Model (SQLAlchemy) + Migrations (Alembic)

### Table: `manufacturing_lots`

**Purpose:** Suspension production lot records (and future product lots)

**Schema:**
```python
class ManufacturingLot(Base):
    __tablename__ = "manufacturing_lots"
    __table_args__ = (
        Index("idx_manufacturing_lots_lot_number", "lot_number"),
        Index("idx_manufacturing_lots_status", "status"),
        Index("idx_manufacturing_lots_product", "product_code"),
        Index("idx_manufacturing_lots_manufacture_date", "manufacture_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Required
    lot_number: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)  # e.g., "C.SLQ001-2026-001"
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, default="Suspension")  # "Suspension" or future products
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Draft")  # Draft, In-Process, Quarantined, Released, Rejected
    
    # Optional metadata
    work_order: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manufacture_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Start date or completion date
    manufacture_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Completion date (if different)
    
    # Operators (free text for now; can add FK to users later if needed)
    operator: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Primary operator
    operator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # Additional operator info
    
    # QA Disposition (for Quarantined → Released/Rejected transition)
    disposition: Mapped[str | None] = mapped_column(String(32), nullable=True)  # "Released", "Rejected"
    disposition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disposition_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    disposition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # QA review notes
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    documents: Mapped[list["ManufacturingLotDocument"]] = relationship(
        "ManufacturingLotDocument",
        back_populates="lot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    equipment_used: Mapped[list["ManufacturingLotEquipment"]] = relationship(
        "ManufacturingLotEquipment",
        back_populates="lot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    materials_used: Mapped[list["ManufacturingLotMaterial"]] = relationship(
        "ManufacturingLotMaterial",
        back_populates="lot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
```

**Fields:**
- `id`: Primary key
- `lot_number`: Lot identifier (required, unique, indexed) - e.g., "C.SLQ001-2026-001"
- `product_code`: Product identifier (required, defaults to "Suspension", indexed)
- `status`: Workflow status (required, indexed)
- `work_order`: Optional work order number
- `manufacture_date`: Start or completion date (optional, indexed)
- `manufacture_end_date`: Completion date if different from start (optional)
- `operator`: Primary operator name (optional, free text)
- `operator_notes`: Additional operator info (optional)
- `disposition`: QA disposition ("Released" or "Rejected", optional)
- `disposition_date`: When disposition was recorded (optional)
- `disposition_by_user_id`: Who recorded disposition (optional, FK to users)
- `disposition_notes`: QA review notes (optional)
- `notes`: General notes (optional)
- Timestamps and audit fields

**Constraints:**
- `lot_number` must be unique (enforced by unique constraint)
- `status` must be one of: "Draft", "In-Process", "Quarantined", "Released", "Rejected" (enforced in service layer or CHECK constraint)
- `product_code` should be one of: "Suspension", "ClearTract Foley Catheter" (or other future products)

**Indexes:**
- `idx_manufacturing_lots_lot_number`: For lookup by lot number
- `idx_manufacturing_lots_status`: For status filtering (especially "Quarantined")
- `idx_manufacturing_lots_product`: For product filtering
- `idx_manufacturing_lots_manufacture_date`: For date range filtering

---

### Table: `manufacturing_lot_documents`

**Purpose:** Documents linked to manufacturing lots (reuses storage pattern)

**Schema:**
```python
class ManufacturingLotDocument(Base):
    __tablename__ = "manufacturing_lot_documents"
    __table_args__ = (
        Index("idx_manufacturing_lot_docs_lot", "lot_id"),
        Index("idx_manufacturing_lot_docs_type", "document_type"),
        Index("idx_manufacturing_lot_docs_uploaded_at", "uploaded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    lot_id: Mapped[int] = mapped_column(ForeignKey("manufacturing_lots.id", ondelete="CASCADE"), nullable=False)
    
    # File metadata
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Document categorization
    document_type: Mapped[str | None] = mapped_column(String(128), nullable=True)  # "Traveler", "QC Report", "COA", "Label", "Release Evidence", etc.
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)  # User-provided description
    
    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    deleted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    # Relationships
    lot: Mapped["ManufacturingLot"] = relationship("ManufacturingLot", back_populates="documents", lazy="selectin")
```

**Fields:**
- `id`: Primary key
- `lot_id`: FK to manufacturing_lots (required, CASCADE delete)
- `storage_key`: Storage abstraction key (required)
- `original_filename`: Original filename (required)
- `content_type`: MIME type (required)
- `sha256`: File digest (required)
- `size_bytes`: File size (required)
- `document_type`: Category/type (optional, indexed) - e.g., "Traveler", "QC Report", "COA", "Label", "Release Evidence", "Environmental Monitoring"
- `description`: User-provided description (optional)
- `is_deleted`, `deleted_at`, `deleted_by_user_id`: Soft delete fields
- `uploaded_at`, `uploaded_by_user_id`: Upload tracking

**Indexes:**
- `idx_manufacturing_lot_docs_lot`: For finding all documents for a lot
- `idx_manufacturing_lot_docs_type`: For filtering by document type
- `idx_manufacturing_lot_docs_uploaded_at`: For sorting by upload date

---

### Table: `manufacturing_lot_equipment`

**Purpose:** Link lot to equipment used (if Equipment & Supplies module exists)

**Schema:**
```python
class ManufacturingLotEquipment(Base):
    __tablename__ = "manufacturing_lot_equipment"
    __table_args__ = (
        UniqueConstraint("lot_id", "equipment_id", name="uq_lot_equipment"),
        Index("idx_manufacturing_lot_equipment_lot", "lot_id"),
        Index("idx_manufacturing_lot_equipment_equipment", "equipment_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    lot_id: Mapped[int] = mapped_column(ForeignKey("manufacturing_lots.id", ondelete="CASCADE"), nullable=False)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True)  # FK if Equipment module exists
    
    # Fallback if Equipment module doesn't exist yet
    equipment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Free text fallback
    
    # Optional metadata
    usage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # How equipment was used
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    lot: Mapped["ManufacturingLot"] = relationship("ManufacturingLot", back_populates="equipment_used", lazy="selectin")
    equipment: Mapped["Equipment | None"] = relationship("Equipment", foreign_keys=[equipment_id], lazy="selectin")  # If Equipment module exists
```

**Fields:**
- `id`: Primary key
- `lot_id`: FK to manufacturing_lots (required, CASCADE delete)
- `equipment_id`: FK to equipment table (optional, if Equipment module exists)
- `equipment_name`: Free text fallback if Equipment module doesn't exist (optional)
- `usage_notes`: How equipment was used (optional)
- `created_at`, `created_by_user_id`: Creation tracking

**Constraints:**
- Unique constraint on `(lot_id, equipment_id)` prevents duplicate associations
- Either `equipment_id` or `equipment_name` should be populated (enforced in service layer)

**Indexes:**
- `idx_manufacturing_lot_equipment_lot`: For finding all equipment for a lot
- `idx_manufacturing_lot_equipment_equipment`: For finding all lots using an equipment

---

### Table: `manufacturing_lot_materials`

**Purpose:** Link lot to materials/supplies used (if Equipment & Supplies module exists)

**Schema:**
```python
class ManufacturingLotMaterial(Base):
    __tablename__ = "manufacturing_lot_materials"
    __table_args__ = (
        UniqueConstraint("lot_id", "material_identifier", name="uq_lot_material"),  # material_identifier is supplier name or material code
        Index("idx_manufacturing_lot_materials_lot", "lot_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    lot_id: Mapped[int] = mapped_column(ForeignKey("manufacturing_lots.id", ondelete="CASCADE"), nullable=False)
    
    # Material identification (flexible - can link to suppliers table if it exists, or free text)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True)  # FK if Suppliers module exists
    material_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Material/supply name (free text or from suppliers)
    material_identifier: Mapped[str] = mapped_column(String(255), nullable=False)  # Unique identifier (supplier name + material, or lot number)
    
    # Optional metadata
    quantity: Mapped[str | None] = mapped_column(String(128), nullable=True)  # Quantity used (free text: "5 kg", "2 drums", etc.)
    lot_number: Mapped[str | None] = mapped_column(String(128), nullable=True)  # Material lot number
    usage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    lot: Mapped["ManufacturingLot"] = relationship("ManufacturingLot", back_populates="materials_used", lazy="selectin")
    supplier: Mapped["Supplier | None"] = relationship("Supplier", foreign_keys=[supplier_id], lazy="selectin")  # If Suppliers module exists
```

**Fields:**
- `id`: Primary key
- `lot_id`: FK to manufacturing_lots (required, CASCADE delete)
- `supplier_id`: FK to suppliers table (optional, if Suppliers module exists)
- `material_name`: Material/supply name (optional)
- `material_identifier`: Unique identifier for the material (required) - used for uniqueness constraint
- `quantity`: Quantity used (optional, free text)
- `lot_number`: Material lot number (optional)
- `usage_notes`: Usage notes (optional)
- `created_at`, `created_by_user_id`: Creation tracking

**Constraints:**
- Unique constraint on `(lot_id, material_identifier)` prevents duplicate materials per lot
- `material_identifier` must be non-empty (required)

**Indexes:**
- `idx_manufacturing_lot_materials_lot`: For finding all materials for a lot

---

### Migration Strategy

**File:** `migrations/versions/<revision>_add_manufacturing_lots.py`

**Steps:**
1. Run `alembic revision -m "add manufacturing lots tables"`
2. Implement `upgrade()`:
   - Create `manufacturing_lots` table
   - Create `manufacturing_lot_documents` table
   - Create `manufacturing_lot_equipment` table
   - Create `manufacturing_lot_materials` table
   - Create all indexes
3. Implement `downgrade()`:
   - Drop tables in reverse order

**PostgreSQL Compatibility:**
- Use `render_as_batch=True` in Alembic config for SQLite compatibility
- All constraints/indexes work on both SQLite and PostgreSQL

---

### Model Imports

**File:** `app/eqms/models.py`

**Add at bottom (after existing imports):**
```python
from app.eqms.modules.manufacturing.models import (  # noqa: E402,F401
    ManufacturingLot,
    ManufacturingLotDocument,
    ManufacturingLotEquipment,
    ManufacturingLotMaterial,
)
```

**Optional (if Equipment & Supplies module exists):**
- Import `Equipment` and `Supplier` models if they exist
- If they don't exist, use forward references or string type hints

---

## 4) Lot Folder + Document Storage Conventions (CRITICAL)

### Storage Key Structure

**Pattern:** `manufacturing/<product_code>/<lot_number>/<document_type>/<yyyy-mm-dd>/<sanitized_filename>`

**Examples:**
- `manufacturing/suspension/C.SLQ001-2026-001/traveler/2026-01-15/tr-c.slq001-2026-001.pdf`
- `manufacturing/suspension/C.SLQ001-2026-001/qc-report/2026-01-16/qc_report_2026-01-16.pdf`
- `manufacturing/suspension/C.SLQ001-2026-001/coa/2026-01-17/coa_c.slq001-2026-001.pdf`
- `manufacturing/suspension/C.SLQ001-2026-001/labels/2026-01-15/label_printout.pdf`
- `manufacturing/suspension/C.SLQ001-2026-001/release-evidence/2026-01-18/qa_release_approval.pdf`

**Simplified Pattern (if subfolders by document_type are too complex):**
- `manufacturing/suspension/<lot_number>/<yyyy-mm-dd>/<sanitized_filename>`
- Use `document_type` field in DB for categorization instead of folder structure

**Recommendation:** Use simplified pattern (date-based only, categorize via `document_type` field).

---

### Storage Key Builder

**File:** `app/eqms/modules/manufacturing/service.py`

```python
from datetime import date
from werkzeug.utils import secure_filename

def build_lot_document_storage_key(
    product_code: str,
    lot_number: str,
    filename: str,
    upload_date: date | None = None,
) -> str:
    """Build deterministic storage key for manufacturing lot document."""
    if upload_date is None:
        upload_date = date.today()
    
    # Normalize product_code and lot_number for path safety
    safe_product = product_code.lower().replace(" ", "-").replace("/", "_").replace("\\", "_")
    safe_lot = lot_number.replace("/", "_").replace("\\", "_").replace(" ", "_")
    safe_filename = secure_filename(filename) or "document.bin"
    
    return f"manufacturing/{safe_product}/{safe_lot}/{upload_date.isoformat()}/{safe_filename}"
```

**Path Traversal Prevention:**
- Use `secure_filename()` from Werkzeug
- Normalize `product_code` and `lot_number` (replace `/`, `\`, spaces)
- Store canonical `storage_key` in DB (never construct from user input)

---

### Document Types (Categorization)

**Standard Document Types for Suspension:**
- `"Traveler"` - TR-C.SLQ001 Traveler form
- `"QC Report"` - QC-C.SLQ001 QC report
- `"COA"` - Certificate of Analysis for finished lot
- `"Label"` - Label copies/printouts
- `"Release Evidence"` - QA disposition/release approval
- `"Receiving"` - Material receiving inspections/COAs
- `"Environmental Monitoring"` - Environmental monitoring records (if attached)
- `"In-Process Record"` - In-process monitoring records
- `"Other"` - Generic/uncategorized

**Implementation:**
- Document type stored in `document_type` field (optional, but recommended)
- UI dropdown for document type on upload form
- Filter documents by type on lot detail page

---

### Document Listing

**For Lot Detail Page:**
```python
# In lot detail route
documents = (
    s.query(ManufacturingLotDocument)
    .filter(ManufacturingLotDocument.lot_id == lot.id)
    .filter(ManufacturingLotDocument.is_deleted == False)
    .order_by(ManufacturingLotDocument.uploaded_at.desc())
    .all()
)

# Group by document_type for display
documents_by_type = {}
for doc in documents:
    doc_type = doc.document_type or "Other"
    if doc_type not in documents_by_type:
        documents_by_type[doc_type] = []
    documents_by_type[doc_type].append(doc)
```

---

## 5) Workflow States + Required Outputs (Suspension)

### State Machine

**States:**
1. **Draft** - Lot created, not yet started
2. **In-Process** - Production in progress
3. **Quarantined** - Production complete, awaiting QC/QA review
4. **Released** - QA approved, lot released
5. **Rejected** - QA rejected lot

**Transitions:**

**Draft → In-Process:**
- Required: Lot created (minimal)
- Optional: Traveler uploaded
- Action: Admin changes status (permission: `manufacturing.edit`)

**In-Process → Quarantined:**
- Required:
  - Transfer complete (manufacture_date set)
  - Label generated (document type "Label" uploaded)
  - QC samples taken (document type "QC Report" uploaded, or notes indicate samples taken)
  - Product tank sealed (can be notes)
- Validation: Check that at least one "Label" document exists
- Action: Admin changes status (permission: `manufacturing.edit`)

**Quarantined → Released:**
- Required:
  - QC report uploaded (document type "QC Report")
  - COA uploaded (document type "COA")
  - QA disposition recorded (`disposition="Released"`, `disposition_notes` populated, `disposition_by_user_id` set)
  - Release evidence uploaded (document type "Release Evidence", optional but recommended)
- Validation: Check for QC Report and COA documents; check that disposition is recorded
- Action: Admin records disposition (permission: `manufacturing.disposition`)

**Quarantined → Rejected:**
- Required:
  - QA disposition recorded (`disposition="Rejected"`, `disposition_notes` populated, `disposition_by_user_id` set)
- Validation: Check that disposition notes are non-empty
- Action: Admin records disposition (permission: `manufacturing.disposition`)

**Note:** No reverse transitions (Draft/In-Process cannot go back; Quarantined cannot go back to In-Process). If correction needed, create new lot or add notes.

---

### Required Outputs (Evidence)

**Per Suspension Lot, system must capture:**

1. **Traveler (TR-C.SLQ001):**
   - Document type: "Traveler"
   - Required for: In-Process → Quarantined (recommended, not strictly enforced)

2. **Receiving / Material Traceability:**
   - Document type: "Receiving"
   - COAs for materials, receiving inspection records
   - Linked via `manufacturing_lot_materials` table

3. **In-Process Records:**
   - Document type: "In-Process Record"
   - Environmental monitoring (if attached per run)
   - Workstation practices evidence (if captured)

4. **QC Records:**
   - Document type: "QC Report"
   - QC-C.SLQ001 QC report
   - Raw data, sample IDs
   - Required for: Quarantined → Released

5. **COA:**
   - Document type: "COA"
   - Certificate of Analysis for finished suspension lot
   - Required for: Quarantined → Released

6. **Labels:**
   - Document type: "Label"
   - Label copies/printouts
   - Required for: In-Process → Quarantined

7. **QA Disposition / Release Evidence:**
   - Document type: "Release Evidence"
   - QA review/release approval
   - Stored in `disposition` fields + optional document
   - Required for: Quarantined → Released/Rejected

---

### Validation Logic

**Service Layer Functions:**

**File:** `app/eqms/modules/manufacturing/service.py`

```python
def can_transition_to_quarantined(s, lot: ManufacturingLot) -> tuple[bool, list[str]]:
    """Check if lot can transition to Quarantined."""
    errors = []
    
    if not lot.manufacture_date:
        errors.append("Manufacture date is required")
    
    # Check for label document
    has_label = any(
        doc.document_type == "Label" and not doc.is_deleted
        for doc in lot.documents
    )
    if not has_label:
        errors.append("Label document is required")
    
    return len(errors) == 0, errors

def can_transition_to_released(s, lot: ManufacturingLot) -> tuple[bool, list[str]]:
    """Check if lot can transition to Released."""
    errors = []
    
    if lot.status != "Quarantined":
        errors.append("Lot must be Quarantined before release")
    
    # Check for QC Report
    has_qc = any(
        doc.document_type == "QC Report" and not doc.is_deleted
        for doc in lot.documents
    )
    if not has_qc:
        errors.append("QC Report is required")
    
    # Check for COA
    has_coa = any(
        doc.document_type == "COA" and not doc.is_deleted
        for doc in lot.documents
    )
    if not has_coa:
        errors.append("COA is required")
    
    # Check for disposition
    if not lot.disposition or lot.disposition != "Released":
        errors.append("QA disposition must be 'Released'")
    
    if not lot.disposition_notes:
        errors.append("Disposition notes are required")
    
    if not lot.disposition_by_user_id:
        errors.append("Disposition must be recorded by a user")
    
    return len(errors) == 0, errors

def can_transition_to_rejected(s, lot: ManufacturingLot) -> tuple[bool, list[str]]:
    """Check if lot can transition to Rejected."""
    errors = []
    
    if lot.status != "Quarantined":
        errors.append("Lot must be Quarantined before rejection")
    
    if not lot.disposition or lot.disposition != "Rejected":
        errors.append("QA disposition must be 'Rejected'")
    
    if not lot.disposition_notes:
        errors.append("Disposition notes are required")
    
    if not lot.disposition_by_user_id:
        errors.append("Disposition must be recorded by a user")
    
    return len(errors) == 0, errors
```

---

## 6) UI/UX (Admin-First, Minimal)

### Manufacturing Landing Page

**Route:** `GET /admin/manufacturing`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Manufacturing                                      [Back]   │
├─────────────────────────────────────────────────────────────┤
│ Product Areas:                                              │
│                                                             │
│ [Suspension]                                                │
│ Manage suspension production lots                           │
│                                                             │
│ [ClearTract Foley Catheters]                               │
│ Coming soon                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

### Suspension Lot List Page

**Route:** `GET /admin/manufacturing/suspension`

**Table Columns:**
- Lot # (link to detail)
- Status (badge: Draft/In-Process/Quarantined/Released/Rejected)
- Manufacture Date
- #Docs (count of non-deleted documents)
- Last Updated
- Actions: [View] [Edit]

**Filters:**
- Search box (searches lot_number, work_order, operator)
- Status dropdown (All, Draft, In-Process, Quarantined, Released, Rejected)
- **"Quarantined" filter** (highlight this - important for QA workflow)
- Date range (manufacture_date from/to)

**Pagination:**
- 50 items per page

**Actions:**
- [New Lot] button (top right)
- [Export] button (CSV export of filtered list)

**Status Badge Colors:**
- Draft: Gray
- In-Process: Blue
- Quarantined: Yellow (warning - needs attention)
- Released: Green
- Rejected: Red

---

### Suspension Lot Detail Page

**Route:** `GET /admin/manufacturing/suspension/<lot_id>`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Lot: C.SLQ001-2026-001  [Quarantined]              [Edit]  │
├─────────────────────────────────────────────────────────────┤
│ Metadata Card:                                              │
│ - Lot Number: C.SLQ001-2026-001                            │
│ - Product: Suspension                                       │
│ - Status: Quarantined                                       │
│ - Work Order: WO-2026-001                                   │
│ - Manufacture Date: 2026-01-15                              │
│ - Operator: John Doe                                        │
│ - QA Disposition: (not set)                                 │
│ - Notes: ...                                                │
│                                                             │
│ [Change Status] button (if permission: manufacturing.edit) │
│ [Record Disposition] button (if Quarantined, permission:   │
│   manufacturing.disposition)                                │
├─────────────────────────────────────────────────────────────┤
│ Equipment Used:                                             │
│ - KrosFlo KTF-2000 System (Equipment #EQ-001) [View]       │
│ - Water Tank Assembly (Equipment #EQ-002) [View]           │
│ [Add Equipment] button (if Equipment module exists)        │
│ OR                                                          │
│ Equipment Used (free text):                                 │
│ - KrosFlo KTF-2000 System                                  │
│ [Add Equipment] button                                      │
├─────────────────────────────────────────────────────────────┤
│ Materials Used:                                             │
│ - Material A (Supplier: Acme Corp, Lot: MA-001) [View]     │
│ [Add Material] button                                       │
├─────────────────────────────────────────────────────────────┤
│ Documents:                                                  │
│                                                             │
│ Traveler (1):                                               │
│ - tr-c.slq001-2026-001.pdf [Download] [Delete]            │
│                                                             │
│ QC Report (1):                                              │
│ - qc_report_2026-01-16.pdf [Download] [Delete]            │
│                                                             │
│ COA (1):                                                    │
│ - coa_c.slq001-2026-001.pdf [Download] [Delete]           │
│                                                             │
│ Label (1):                                                  │
│ - label_printout.pdf [Download] [Delete]                   │
│                                                             │
│ [Upload Document] button                                    │
└─────────────────────────────────────────────────────────────┘
```

**Sections:**
1. **Metadata Card:** All lot fields (read-only, unless in edit mode)
2. **Status Actions:** [Change Status] and [Record Disposition] buttons (permission-based)
3. **Equipment Used:** List of equipment (linked if Equipment module exists, or free text)
4. **Materials Used:** List of materials/supplies
5. **Documents:** Grouped by document type, with [Download] and [Delete] buttons

---

### Suspension Lot Edit Page

**Route:** `GET /admin/manufacturing/suspension/<lot_id>/edit` (form)  
**Route:** `POST /admin/manufacturing/suspension/<lot_id>/edit` (submit)

**Form Fields:**
- Lot Number (read-only, cannot change)
- Product Code (read-only or dropdown: "Suspension", "ClearTract Foley Catheter")
- Status (read-only - use separate "Change Status" action)
- Work Order (text input)
- Manufacture Date (date input)
- Manufacture End Date (date input, optional)
- Operator (text input)
- Operator Notes (textarea)
- Notes (textarea)

**Validation:**
- Lot Number must be unique (if creating new)
- Status must be valid
- Dates must be valid

**On Submit:**
- Update lot record
- Log audit event: `manufacturing.lot.edit`
- Require reason-for-change if critical fields change

---

### Change Status Form

**Route:** `POST /admin/manufacturing/suspension/<lot_id>/status`

**Form Fields:**
- New Status (dropdown: valid transitions only)
- Reason (textarea, required)

**Validation:**
- Check transition is valid (Draft → In-Process → Quarantined → Released/Rejected)
- If transitioning to Quarantined: Call `can_transition_to_quarantined()`
- If transitioning to Released: Call `can_transition_to_released()`
- If transitioning to Rejected: Call `can_transition_to_rejected()`

**On Submit:**
- Update lot status
- If Released/Rejected: Also set `disposition`, `disposition_date`, `disposition_by_user_id`, `disposition_notes`
- Log audit event: `manufacturing.lot.status_change`

---

### Record Disposition Form

**Route:** `POST /admin/manufacturing/suspension/<lot_id>/disposition`

**Form Fields:**
- Disposition (dropdown: "Released", "Rejected")
- Disposition Notes (textarea, required)
- Disposition Date (date input, defaults to today)

**Validation:**
- Lot must be in "Quarantined" status
- Disposition notes must be non-empty
- If "Released": Check `can_transition_to_released()`
- If "Rejected": Check `can_transition_to_rejected()`

**On Submit:**
- Update lot: `disposition`, `disposition_date`, `disposition_by_user_id`, `disposition_notes`
- If "Released": Set `status="Released"`
- If "Rejected": Set `status="Rejected"`
- Log audit event: `manufacturing.lot.disposition`

---

### Document Upload Form

**Route:** `POST /admin/manufacturing/suspension/<lot_id>/documents/upload`

**Form Fields:**
- File (file input, required)
- Document Type (dropdown: "Traveler", "QC Report", "COA", "Label", "Release Evidence", "Receiving", "Environmental Monitoring", "In-Process Record", "Other")
- Description (text input, optional)

**On Submit:**
- Validate file (size limits, file type if needed)
- Compute SHA256 digest
- Build storage key using `build_lot_document_storage_key()`
- Upload to storage
- Create `ManufacturingLotDocument` record
- Log audit event: `manufacturing.lot.document_upload`

---

### ClearTract Foley Catheters Placeholder

**Route:** `GET /admin/manufacturing/cleartract-foley-catheters`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ ClearTract Foley Catheters                          [Back]  │
├─────────────────────────────────────────────────────────────┤
│ This product area is not yet implemented.                   │
│                                                             │
│ Coming soon.                                                │
└─────────────────────────────────────────────────────────────┘
```

**No functionality required** - just a placeholder page.

---

## 7) Permissions + Audit Trail

### Required Permissions

**File:** `scripts/init_db.py`

**Add to `seed_only()` function:**

```python
# Manufacturing (P0)
p_manufacturing_view = ensure_perm("manufacturing.view", "Manufacturing: view")
p_manufacturing_create = ensure_perm("manufacturing.create", "Manufacturing: create lots")
p_manufacturing_edit = ensure_perm("manufacturing.edit", "Manufacturing: edit lots")
p_manufacturing_upload = ensure_perm("manufacturing.upload", "Manufacturing: upload documents")
p_manufacturing_disposition = ensure_perm("manufacturing.disposition", "Manufacturing: record QA disposition")
```

**Grant to `admin` role:**
```python
for p in (
    # ... existing permissions ...
    p_manufacturing_view,
    p_manufacturing_create,
    p_manufacturing_edit,
    p_manufacturing_upload,
    p_manufacturing_disposition,
):
    if p not in role_admin.permissions:
        role_admin.permissions.append(p)
```

**Permission Mapping:**
- List/View: `manufacturing.view`
- Create: `manufacturing.create`
- Edit: `manufacturing.edit`
- Change Status: `manufacturing.edit`
- Upload Document: `manufacturing.upload`
- Record Disposition: `manufacturing.disposition`
- Download Document: `manufacturing.view` (same as view)
- Delete Document: `manufacturing.edit` (same as edit)

---

### Audit Trail Requirements

**Required Audit Events:**

**Lot Events:**
- `manufacturing.lot.create` - Lot created
  - Entity: `ManufacturingLot`
  - Entity ID: `lot.id`
  - Metadata: `{"lot_number": "...", "product_code": "...", "status": "..."}`
- `manufacturing.lot.edit` - Lot updated
  - Entity: `ManufacturingLot`
  - Entity ID: `lot.id`
  - Reason: Required (reason-for-change)
  - Metadata: `{"lot_number": "...", "changes": {...}}`
- `manufacturing.lot.status_change` - Status changed
  - Entity: `ManufacturingLot`
  - Entity ID: `lot.id`
  - Reason: Required (why status changed)
  - Metadata: `{"lot_number": "...", "from": "...", "to": "...", "status": "..."}`
- `manufacturing.lot.disposition` - QA disposition recorded
  - Entity: `ManufacturingLot`
  - Entity ID: `lot.id`
  - Reason: Required (disposition notes)
  - Metadata: `{"lot_number": "...", "disposition": "...", "status": "..."}`
- `manufacturing.lot.document_upload` - Document uploaded
  - Entity: `ManufacturingLotDocument`
  - Entity ID: `document.id`
  - Metadata: `{"lot_id": ..., "lot_number": "...", "filename": "...", "document_type": "..."}`
- `manufacturing.lot.document_download` - Document downloaded (optional)
  - Entity: `ManufacturingLotDocument`
  - Entity ID: `document.id`
  - Metadata: `{"lot_id": ..., "filename": "..."}`
- `manufacturing.lot.document_delete` - Document deleted
  - Entity: `ManufacturingLotDocument`
  - Entity ID: `document.id`
  - Reason: Required
  - Metadata: `{"lot_id": ..., "filename": "..."}`
- `manufacturing.lot.equipment_added` - Equipment added to lot
  - Entity: `ManufacturingLotEquipment`
  - Entity ID: `association.id`
  - Metadata: `{"lot_id": ..., "equipment_id": ..., "equipment_name": "..."}`
- `manufacturing.lot.material_added` - Material added to lot
  - Entity: `ManufacturingLotMaterial`
  - Entity ID: `association.id`
  - Metadata: `{"lot_id": ..., "material_identifier": "...", "supplier_id": ...}`

**Implementation:**
- Use `record_event()` from `app.eqms.audit`
- Call in service layer (not routes) for consistency
- Always include `actor=user`, `action=...`, `entity_type=...`, `entity_id=...`
- Include `reason=...` for controlled operations (edits, status changes, disposition, deletes)

---

## 8) Implementation Checklist (Developer Task List)

### Phase 0: Global Naming Change

- [ ] **Task 0.1:** Rename "Equipment" → "Equipment & Supplies" in navigation
  - `app/eqms/templates/admin/index.html` (update card label)
  - `README.md` (update module list)
  - `docs/01_ARCHITECTURE_OVERVIEW.md` (if present)
  - `docs/03_MODULE_SPECS.md` (update section header)

---

### Phase 1: Models & Migrations

- [ ] **Task 1.1:** Create `app/eqms/modules/manufacturing/models.py`
  - Define `ManufacturingLot` model
  - Define `ManufacturingLotDocument` model
  - Define `ManufacturingLotEquipment` model
  - Define `ManufacturingLotMaterial` model
  - Add relationships

- [ ] **Task 1.2:** Update `app/eqms/models.py`
  - Import manufacturing models at bottom

- [ ] **Task 1.3:** Create Alembic migration
  - Run `alembic revision -m "add manufacturing lots tables"`
  - Implement `upgrade()` with all tables and indexes
  - Implement `downgrade()`
  - Test: `alembic upgrade head` and `alembic downgrade -1`

- [ ] **Task 1.4:** Verify models import correctly
  - Run `alembic autogenerate` (should detect no differences)

---

### Phase 2: Permissions & Seed

- [ ] **Task 2.1:** Update `scripts/init_db.py`
  - Add manufacturing permissions: `manufacturing.view`, `manufacturing.create`, `manufacturing.edit`, `manufacturing.upload`, `manufacturing.disposition`
  - Grant all permissions to `admin` role

- [ ] **Task 2.2:** Test permissions seed
  - Run `python scripts/init_db.py`
  - Verify permissions exist in database
  - Verify `admin` role has all permissions

---

### Phase 3: Service Layer

- [ ] **Task 3.1:** Create `app/eqms/modules/manufacturing/service.py`
  - `create_lot(s, payload, user) -> ManufacturingLot`
  - `update_lot(s, lot, payload, user, reason) -> ManufacturingLot`
  - `change_lot_status(s, lot, new_status, reason, user) -> ManufacturingLot`
  - `record_disposition(s, lot, disposition, notes, disposition_date, user) -> ManufacturingLot`
  - `build_lot_document_storage_key(product_code, lot_number, filename, upload_date) -> str`
  - `upload_lot_document(s, lot, file_bytes, filename, content_type, user, document_type, description) -> ManufacturingLotDocument`
  - `delete_lot_document(s, document, user, reason) -> None`
  - `add_equipment_to_lot(s, lot, equipment_id_or_name, usage_notes, user) -> ManufacturingLotEquipment`
  - `remove_equipment_from_lot(s, association, user, reason) -> None`
  - `add_material_to_lot(s, lot, material_identifier, material_name, supplier_id, quantity, lot_number, usage_notes, user) -> ManufacturingLotMaterial`
  - `remove_material_from_lot(s, association, user, reason) -> None`
  - `can_transition_to_quarantined(s, lot) -> tuple[bool, list[str]]`
  - `can_transition_to_released(s, lot) -> tuple[bool, list[str]]`
  - `can_transition_to_rejected(s, lot) -> tuple[bool, list[str]]`

- [ ] **Task 3.2:** Add validation helpers
  - Validate lot payload (lot_number required, status valid, dates valid)
  - Validate status transitions
  - Validate disposition requirements

---

### Phase 4: Routes/Controllers

- [ ] **Task 4.1:** Create `app/eqms/modules/manufacturing/admin.py`
  - Blueprint: `bp = Blueprint("manufacturing", __name__)`
  - Route: `GET /manufacturing` → `manufacturing_index()` (landing page)
  - Route: `GET /manufacturing/suspension` → `suspension_list()` (list with filters)
  - Route: `GET /manufacturing/suspension/new` → `suspension_new_get()`
  - Route: `POST /manufacturing/suspension/new` → `suspension_new_post()`
  - Route: `GET /manufacturing/suspension/<id>` → `suspension_detail(id)`
  - Route: `GET /manufacturing/suspension/<id>/edit` → `suspension_edit_get(id)`
  - Route: `POST /manufacturing/suspension/<id>/edit` → `suspension_edit_post(id)`
  - Route: `POST /manufacturing/suspension/<id>/status` → `suspension_change_status(id)`
  - Route: `POST /manufacturing/suspension/<id>/disposition` → `suspension_record_disposition(id)`
  - Route: `POST /manufacturing/suspension/<id>/documents/upload` → `suspension_document_upload(id)`
  - Route: `GET /manufacturing/suspension/<id>/documents/<doc_id>/download` → `suspension_document_download(id, doc_id)`
  - Route: `POST /manufacturing/suspension/<id>/documents/<doc_id>/delete` → `suspension_document_delete(id, doc_id)`
  - Route: `POST /manufacturing/suspension/<id>/equipment` → `suspension_equipment_add(id)`
  - Route: `POST /manufacturing/suspension/<id>/equipment/<equip_id>/remove` → `suspension_equipment_remove(id, equip_id)`
  - Route: `POST /manufacturing/suspension/<id>/materials` → `suspension_material_add(id)`
  - Route: `POST /manufacturing/suspension/<id>/materials/<material_id>/remove` → `suspension_material_remove(id, material_id)`
  - Route: `GET /manufacturing/cleartract-foley-catheters` → `cleartract_placeholder()` (placeholder page)

- [ ] **Task 4.2:** Register blueprint in `app/eqms/__init__.py`
  - Import: `from app.eqms.modules.manufacturing.admin import bp as manufacturing_bp`
  - Register: `app.register_blueprint(manufacturing_bp, url_prefix="/admin/manufacturing")`

- [ ] **Task 4.3:** Add RBAC decorators to all routes
  - Use `@require_permission("manufacturing.view")`, etc.
  - Ensure all routes check permissions

---

### Phase 5: Templates/UI

- [ ] **Task 5.1:** Create manufacturing templates
  - `app/eqms/templates/admin/manufacturing/index.html` (landing page)
  - `app/eqms/templates/admin/manufacturing/suspension/list.html` (list with filters, table)
  - `app/eqms/templates/admin/manufacturing/suspension/detail.html` (metadata + equipment + materials + documents)
  - `app/eqms/templates/admin/manufacturing/suspension/edit.html` (edit form)
  - `app/eqms/templates/admin/manufacturing/suspension/new.html` (create form)
  - `app/eqms/templates/admin/manufacturing/cleartract_placeholder.html` (placeholder)

- [ ] **Task 5.2:** Update `app/eqms/templates/admin/index.html`
  - Add "Manufacturing" card (link to `manufacturing.manufacturing_index`)
  - Update "Equipment" card label to "Equipment & Supplies"

- [ ] **Task 5.3:** Reuse existing design system
  - Use `_layout.html` base template
  - Use `design-system.css` for styling
  - Match existing admin UI patterns (cards, tables, forms)
  - Add status badge styling (Draft/In-Process/Quarantined/Released/Rejected)

---

### Phase 6: Storage Integration

- [ ] **Task 6.1:** Implement storage key builder
  - `build_lot_document_storage_key()` in `manufacturing/service.py`

- [ ] **Task 6.2:** Test storage integration
  - Upload document to lot (verify file appears in storage)
  - Download document (verify files are readable)
  - Test with both local and S3 backends (if S3 configured)

---

### Phase 7: Status Transition Validation

- [ ] **Task 7.1:** Implement transition validation functions
  - `can_transition_to_quarantined()`
  - `can_transition_to_released()`
  - `can_transition_to_rejected()`

- [ ] **Task 7.2:** Integrate validation into status change route
  - Check validation before allowing status change
  - Show clear error messages if validation fails

---

### Phase 8: Tests

- [ ] **Task 8.1:** Create smoke tests
  - `tests/test_manufacturing.py`: Test lot CRUD, document upload/download, status transitions

- [ ] **Task 8.2:** Test permissions
  - Verify routes require correct permissions
  - Verify 403 when permission missing

- [ ] **Task 8.3:** Test audit trail
  - Verify audit events logged for all operations
  - Verify reason-for-change required for edits/status changes/disposition

- [ ] **Task 8.4:** Test status transition validation
  - Verify Quarantined → Released requires QC Report + COA + disposition
  - Verify Quarantined → Rejected requires disposition notes

---

### Phase 9: Documentation Updates

- [ ] **Task 9.1:** Update `README.md`
  - Update module list: "Equipment" → "Equipment & Supplies"
  - Add "Manufacturing" to module list (if not already present)

- [ ] **Task 9.2:** Update `docs/03_MODULE_SPECS.md`
  - Update "Equipment" section header to "Equipment & Supplies"
  - Add/update Manufacturing section with Suspension workflow

---

## 9) Acceptance Criteria (Explicit)

### Manufacturing Module

- [ ] **AC1:** Admin can create a Suspension lot
  - Navigate to `/admin/manufacturing/suspension/new`
  - Fill form: Lot Number="C.SLQ001-2026-001", Product="Suspension", Status="Draft"
  - Submit
  - Redirected to `/admin/manufacturing/suspension/<id>` detail page
  - Lot appears in list at `/admin/manufacturing/suspension`

- [ ] **AC2:** Admin can upload documents to lot
  - Navigate to lot detail page
  - Click [Upload Document]
  - Select file (PDF), enter document type="Traveler", description="TR-C.SLQ001"
  - Submit
  - Document appears in documents list under "Traveler" section
  - File is stored in storage at `manufacturing/suspension/C.SLQ001-2026-001/2026-01-15/traveler.pdf`

- [ ] **AC3:** Admin can download lot document
  - Navigate to lot detail page
  - Click [Download] on a document
  - File downloads with correct filename and content

- [ ] **AC4:** Admin can change lot status
  - Navigate to lot detail page (status="Draft")
  - Click [Change Status]
  - Select new status="In-Process", enter reason
  - Submit
  - Status updated, audit event logged

- [ ] **AC5:** Status transition validation works
  - Create lot, set status="In-Process"
  - Try to change status to "Quarantined" without label document
  - Error: "Label document is required"
  - Upload label document
  - Try again → Success

- [ ] **AC6:** Admin can record QA disposition
  - Navigate to lot detail page (status="Quarantined")
  - Upload QC Report and COA documents
  - Click [Record Disposition]
  - Select disposition="Released", enter notes, date
  - Submit
  - Status changes to "Released", disposition fields populated, audit event logged

- [ ] **AC7:** Disposition validation works
  - Create lot, set status="Quarantined"
  - Try to record disposition="Released" without QC Report
  - Error: "QC Report is required"
  - Upload QC Report and COA
  - Try again → Success

- [ ] **AC8:** Lot list filters work
  - Navigate to `/admin/manufacturing/suspension`
  - Filter by Status="Quarantined"
  - Only quarantined lots shown
  - Filter by date range
  - Only lots in date range shown

- [ ] **AC9:** Each lot has its own folder
  - Create two lots: "C.SLQ001-2026-001" and "C.SLQ001-2026-002"
  - Upload document to each
  - Verify files stored in separate folders:
    - `manufacturing/suspension/C.SLQ001-2026-001/...`
    - `manufacturing/suspension/C.SLQ001-2026-002/...`

- [ ] **AC10:** Documents grouped by type on detail page
  - Upload multiple documents with different types (Traveler, QC Report, COA)
  - Navigate to lot detail page
  - Documents grouped under headers: "Traveler", "QC Report", "COA"

---

### Equipment & Supplies Rename

- [ ] **AC11:** Navigation shows "Equipment & Supplies"
  - Navigate to `/admin`
  - Verify card label is "Equipment & Supplies" (not "Equipment")

- [ ] **AC12:** README updated
  - Open `README.md`
  - Verify module list shows "Equipment & Supplies" (not "Equipment")

---

### Permissions & Security

- [ ] **AC13:** Permissions enforced
  - Log in as user without `manufacturing.view` permission
  - Navigate to `/admin/manufacturing`
  - Receive 403 Forbidden
  - Log in as admin (has all permissions)
  - Can access all routes

- [ ] **AC14:** Disposition requires special permission
  - Log in as user with `manufacturing.view` but not `manufacturing.disposition`
  - Navigate to quarantined lot detail page
  - [Record Disposition] button not visible or disabled

- [ ] **AC15:** Audit events logged
  - Create lot → Verify `manufacturing.lot.create` event in audit log
  - Change status → Verify `manufacturing.lot.status_change` event with reason
  - Record disposition → Verify `manufacturing.lot.disposition` event
  - Upload document → Verify `manufacturing.lot.document_upload` event

---

### ClearTract Placeholder

- [ ] **AC16:** ClearTract placeholder page loads
  - Navigate to `/admin/manufacturing/cleartract-foley-catheters`
  - Page loads without errors
  - Shows "Coming soon" or similar message

---

## Summary

**Scope:** Manufacturing module (Suspension lot tracking) + Equipment → Equipment & Supplies rename

**Files Created:** ~10 files (models, routes, templates)

**Files Modified:** ~5 files (models.py, init_db.py, __init__.py, admin/index.html, README.md)

**Migrations:** 1 migration (manufacturing_lots, manufacturing_lot_documents, manufacturing_lot_equipment, manufacturing_lot_materials tables)

**Permissions:** 5 new permissions (manufacturing.view, create, edit, upload, disposition)

**Risk:** Low (follows existing patterns, minimal scope)

**Estimated Effort:** 2-3 days for experienced developer

---

## References

- **Existing Patterns:** `app/eqms/modules/document_control/`, `app/eqms/modules/rep_traceability/` (storage, audit, RBAC)
- **Storage:** `app/eqms/storage.py` (storage abstraction)
- **Audit:** `app.eqms.audit` (audit trail)
- **RBAC:** `app.eqms.rbac` (permissions)
- **Procedure Document:** `MP-C.SLQ001 B Manufacturing Procedure. Suspension Processing.docx` (source of truth for workflow)
