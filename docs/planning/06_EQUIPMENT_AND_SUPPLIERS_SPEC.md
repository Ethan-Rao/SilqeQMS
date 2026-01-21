# Equipment & Supplier Management Implementation Spec

**Date:** 2026-01-15  
**Phase:** 1 (Equipment module + Supplier Management enhancements)  
**Purpose:** Developer-ready specification for Equipment module and Supplier Management foldering + associations

---

## 1) Executive Summary

### What Is Being Added/Changed

**Equipment Module (New):**
- New Equipment module to replace "PLM" label in UI navigation
- Equipment master data management (equipment codes, status, calibration/PM tracking)
- Per-equipment document storage (calibration certs, PM records, manuals, photos)
- Equipment ↔ Supplier associations (many-to-many)

**Supplier Management Enhancements:**
- Per-supplier document storage (audits, approvals, certs, quality agreements, COIs)
- Equipment ↔ Supplier association management
- Enhanced supplier detail pages with associated equipment and documents

**Why:**
- Equipment tracking is core to eQMS compliance (calibration, PM schedules)
- Supplier management requires document storage for audits and approvals
- Equipment-supplier associations enable traceability (which suppliers provide parts/services for which equipment)

---

## 2) Information Architecture + Navigation

### Module Naming Update

**Change:** Rename "PLM" to **Equipment** in:
- `app/eqms/templates/admin/index.html` (line 26-28): Change "PLM" card to "Equipment"
- `README.md` (line 17): Update module list: "PLM" → "Equipment"
- `docs/01_ARCHITECTURE_OVERVIEW.md` (line 14): Update module list if present
- `docs/03_MODULE_SPECS.md` (line 19): Update section header "PLM" → "Equipment"

**No code changes needed** - only UI labels and documentation.

---

### Proposed Admin Routes

**Equipment Routes:**
- `GET /admin/equipment` → Equipment list (search, filters)
- `GET /admin/equipment/new` → Create equipment form
- `POST /admin/equipment/new` → Create equipment
- `GET /admin/equipment/<equipment_id>` → Equipment detail (metadata + suppliers + documents)
- `GET /admin/equipment/<equipment_id>/edit` → Edit equipment form
- `POST /admin/equipment/<equipment_id>/edit` → Update equipment
- `POST /admin/equipment/<equipment_id>/documents/upload` → Upload document
- `GET /admin/equipment/<equipment_id>/documents/<doc_id>/download` → Download document
- `POST /admin/equipment/<equipment_id>/documents/<doc_id>/delete` → Delete document (soft-delete or hard delete)
- `POST /admin/equipment/<equipment_id>/suppliers` → Add supplier association
- `POST /admin/equipment/<equipment_id>/suppliers/<supplier_id>/remove` → Remove supplier association

**Supplier Routes (New/Enhanced):**
- `GET /admin/suppliers` → Supplier list (search, filters) - **NEW**
- `GET /admin/suppliers/new` → Create supplier form - **NEW**
- `POST /admin/suppliers/new` → Create supplier - **NEW**
- `GET /admin/suppliers/<supplier_id>` → Supplier detail (metadata + equipment + documents) - **NEW**
- `GET /admin/suppliers/<supplier_id>/edit` → Edit supplier form - **NEW**
- `POST /admin/suppliers/<supplier_id>/edit` → Update supplier - **NEW**
- `POST /admin/suppliers/<supplier_id>/documents/upload` → Upload document - **NEW**
- `GET /admin/suppliers/<supplier_id>/documents/<doc_id>/download` → Download document - **NEW**
- `POST /admin/suppliers/<supplier_id>/documents/<doc_id>/delete` → Delete document - **NEW**

**Blueprint Registration:**
- Equipment: `app/eqms/modules/equipment/admin.py` → `bp = Blueprint("equipment", __name__)`
  - Register in `app/eqms/__init__.py`: `app.register_blueprint(equipment_bp, url_prefix="/admin")`
- Suppliers: `app/eqms/modules/suppliers/admin.py` → `bp = Blueprint("suppliers", __name__)`
  - Register in `app/eqms/__init__.py`: `app.register_blueprint(suppliers_bp, url_prefix="/admin")`

---

### Sidebar Navigation

**Update:** `app/eqms/templates/_layout.html` (if sidebar exists) or `app/eqms/templates/admin/index.html`:

**Equipment:**
- Link: `{{ url_for('equipment.equipment_list') }}`
- Label: "Equipment"

**Supplier Management:**
- Link: `{{ url_for('suppliers.suppliers_list') }}`
- Label: "Suppliers"

**Note:** If navigation is card-based (as in `admin/index.html`), add cards for Equipment and Suppliers.

---

## 3) Data Model (SQLAlchemy) + Migrations (Alembic)

### Table: `suppliers`

**Purpose:** Supplier master data

**Schema:**
```python
class Supplier(Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        Index("idx_suppliers_name", "name"),
        Index("idx_suppliers_status", "status"),
        Index("idx_suppliers_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Required
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="Pending")  # Approved, Conditional, Pending, Rejected
    
    # Optional metadata
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g., "Component Supplier", "Service Provider"
    product_service_provided: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Address (single text blob for simplicity, or separate fields)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)  # Full address as text
    
    # Dates
    initial_listing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    certification_expiration: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    equipment_associations: Mapped[list["EquipmentSupplier"]] = relationship(
        "EquipmentSupplier",
        back_populates="supplier",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[list["ManagedDocument"]] = relationship(
        "ManagedDocument",
        back_populates="supplier",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="ManagedDocument.supplier_id",
    )
```

**Fields:**
- `id`: Primary key
- `name`: Supplier name (required, indexed for search)
- `status`: Approval status (required, indexed)
- `category`: Supplier category (optional, indexed)
- `product_service_provided`: Description of products/services (optional)
- `address`: Full address as text (optional, can be split into address1/city/state/zip later)
- `initial_listing_date`: When supplier was first added (optional)
- `certification_expiration`: Expiration date for certifications (optional)
- `notes`: Free-text notes/comments (optional)
- Timestamps and audit fields (created_at, updated_at, created_by_user_id, updated_by_user_id)

**Constraints:**
- `name` must be non-empty (enforced in service layer)
- `status` should be one of: "Approved", "Conditional", "Pending", "Rejected" (enforced in service layer or CHECK constraint)

**Indexes:**
- `idx_suppliers_name`: For search/filtering
- `idx_suppliers_status`: For status filtering
- `idx_suppliers_category`: For category filtering

---

### Table: `equipment`

**Purpose:** Equipment master data

**Schema:**
```python
class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        Index("idx_equipment_code", "equip_code"),
        Index("idx_equipment_status", "status"),
        Index("idx_equipment_location", "location"),
        Index("idx_equipment_cal_due", "cal_due_date"),
        Index("idx_equipment_pm_due", "pm_due_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Required
    equip_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # e.g., "ST-001"
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="Active")  # Active, Inactive, Retired, Calibration Overdue, PM Overdue
    
    # Optional metadata
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mfg: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Manufacturer
    model_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    serial_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    
    # Dates
    date_in_service: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Location
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)  # e.g., "Lab A", "Production Floor"
    
    # Calibration tracking
    cal_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Days between calibrations
    last_cal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cal_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # PM tracking
    pm_interval: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Days between PMs
    last_pm_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    pm_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # Notes
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    supplier_associations: Mapped[list["EquipmentSupplier"]] = relationship(
        "EquipmentSupplier",
        back_populates="equipment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    documents: Mapped[list["ManagedDocument"]] = relationship(
        "ManagedDocument",
        back_populates="equipment",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="ManagedDocument.equipment_id",
    )
```

**Fields:**
- `id`: Primary key
- `equip_code`: Equipment code (required, unique, indexed) - e.g., "ST-001" from spreadsheet
- `status`: Equipment status (required, indexed)
- `description`: Equipment description (optional)
- `mfg`: Manufacturer name (optional, used for supplier auto-linking)
- `model_no`, `serial_no`: Model and serial numbers (optional)
- `date_in_service`: When equipment was put into service (optional)
- `location`: Physical location (optional, indexed)
- `cal_interval`, `last_cal_date`, `cal_due_date`: Calibration tracking (optional, `cal_due_date` indexed)
- `pm_interval`, `last_pm_date`, `pm_due_date`: PM tracking (optional, `pm_due_date` indexed)
- `comments`: Free-text comments (optional)
- Timestamps and audit fields

**Constraints:**
- `equip_code` must be unique (enforced by unique constraint)
- `equip_code` must be non-empty (enforced in service layer)

**Indexes:**
- `idx_equipment_code`: For lookup by code
- `idx_equipment_status`: For status filtering
- `idx_equipment_location`: For location filtering
- `idx_equipment_cal_due`: For "CAL overdue" filter
- `idx_equipment_pm_due`: For "PM overdue" filter

---

### Table: `equipment_suppliers`

**Purpose:** Many-to-many relationship between equipment and suppliers

**Schema:**
```python
class EquipmentSupplier(Base):
    __tablename__ = "equipment_suppliers"
    __table_args__ = (
        UniqueConstraint("equipment_id", "supplier_id", name="uq_equipment_supplier"),
        Index("idx_equipment_suppliers_equipment", "equipment_id"),
        Index("idx_equipment_suppliers_supplier", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    
    # Optional relationship metadata
    relationship_type: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g., "Manufacturer", "Service Provider", "Parts Supplier"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="supplier_associations", lazy="selectin")
    supplier: Mapped["Supplier"] = relationship("Supplier", back_populates="equipment_associations", lazy="selectin")
```

**Fields:**
- `id`: Primary key
- `equipment_id`: FK to equipment (required, CASCADE delete)
- `supplier_id`: FK to suppliers (required, CASCADE delete)
- `relationship_type`: Type of relationship (optional)
- `notes`: Free-text notes (optional)
- `created_at`: When association was created
- `created_by_user_id`: Who created the association

**Constraints:**
- Unique constraint on `(equipment_id, supplier_id)` prevents duplicate associations

**Indexes:**
- `idx_equipment_suppliers_equipment`: For finding all suppliers for an equipment
- `idx_equipment_suppliers_supplier`: For finding all equipment for a supplier

---

### Table: `managed_documents`

**Purpose:** Generic document storage for equipment and suppliers (reusable pattern)

**Schema:**
```python
class ManagedDocument(Base):
    __tablename__ = "managed_documents"
    __table_args__ = (
        Index("idx_managed_docs_entity", "entity_type", "entity_id"),
        Index("idx_managed_docs_uploaded_at", "uploaded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Entity linkage (polymorphic)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)  # "equipment" or "supplier"
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)  # FK to equipment.id or suppliers.id
    
    # Optional explicit FKs for referential integrity (if needed)
    equipment_id: Mapped[int | None] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=True)
    
    # File metadata
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)  # Storage abstraction key
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="application/octet-stream")
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)  # File digest
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Document metadata
    description: Mapped[str | None] = mapped_column(String(512), nullable=True)  # User-provided description/tag
    document_type: Mapped[str | None] = mapped_column(String(128), nullable=True)  # e.g., "Calibration Cert", "PM Record", "Audit Report", "COI"
    
    # Soft delete (if deletion is allowed)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    deleted_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    uploaded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    # Relationships
    equipment: Mapped["Equipment | None"] = relationship("Equipment", foreign_keys=[equipment_id], lazy="selectin")
    supplier: Mapped["Supplier | None"] = relationship("Supplier", foreign_keys=[supplier_id], lazy="selectin")
```

**Fields:**
- `id`: Primary key
- `entity_type`: "equipment" or "supplier" (required, indexed)
- `entity_id`: ID of the entity (required, indexed with entity_type)
- `equipment_id`, `supplier_id`: Optional explicit FKs for referential integrity (one must match entity_type/entity_id)
- `storage_key`: Storage abstraction key (required)
- `original_filename`: Original filename (required)
- `content_type`: MIME type (required)
- `sha256`: File digest (required)
- `size_bytes`: File size (required)
- `description`: User-provided description (optional)
- `document_type`: Type of document (optional)
- `is_deleted`, `deleted_at`, `deleted_by_user_id`: Soft delete fields (if deletion allowed)
- `uploaded_at`, `uploaded_by_user_id`: Upload tracking

**Constraints:**
- `entity_type` must be "equipment" or "supplier" (enforced in service layer or CHECK constraint)
- If `entity_type == "equipment"`, then `equipment_id` must match `entity_id` (enforced in service layer)
- If `entity_type == "supplier"`, then `supplier_id` must match `entity_id` (enforced in service layer)

**Indexes:**
- `idx_managed_docs_entity`: For finding all documents for an entity
- `idx_managed_docs_uploaded_at`: For sorting by upload date

**Note:** This table follows the same pattern as `DocumentFile` in document_control, but is generic for equipment/suppliers.

---

### Migration Strategy

**File:** `migrations/versions/<revision>_add_equipment_and_suppliers.py`

**Steps:**
1. Run `alembic revision -m "add equipment and suppliers tables"`
2. Implement `upgrade()`:
   - Create `suppliers` table
   - Create `equipment` table
   - Create `equipment_suppliers` join table
   - Create `managed_documents` table
   - Create all indexes
3. Implement `downgrade()`:
   - Drop tables in reverse order (managed_documents, equipment_suppliers, equipment, suppliers)

**PostgreSQL Compatibility:**
- Use `render_as_batch=True` in Alembic config for SQLite compatibility
- All constraints/indexes work on both SQLite and PostgreSQL

---

### Model Imports

**File:** `app/eqms/models.py`

**Add at bottom (after existing imports):**
```python
from app.eqms.modules.equipment.models import Equipment, EquipmentSupplier  # noqa: E402,F401
from app.eqms.modules.suppliers.models import Supplier  # noqa: E402,F401
from app.eqms.modules.equipment.models import ManagedDocument  # noqa: E402,F401
```

**Note:** `ManagedDocument` can live in either `equipment/models.py` or a shared `app/eqms/modules/shared/models.py`. For simplicity, put it in `equipment/models.py` and import from there.

---

### Required Permissions

**File:** `scripts/init_db.py`

**Add to `seed_only()` function:**

```python
# Equipment (P0)
p_equipment_view = ensure_perm("equipment.view", "Equipment: view")
p_equipment_create = ensure_perm("equipment.create", "Equipment: create")
p_equipment_edit = ensure_perm("equipment.edit", "Equipment: edit")
p_equipment_upload = ensure_perm("equipment.upload", "Equipment: upload documents")

# Suppliers (P0)
p_suppliers_view = ensure_perm("suppliers.view", "Suppliers: view")
p_suppliers_create = ensure_perm("suppliers.create", "Suppliers: create")
p_suppliers_edit = ensure_perm("suppliers.edit", "Suppliers: edit")
p_suppliers_upload = ensure_perm("suppliers.upload", "Suppliers: upload documents")
```

**Grant to `admin` role:**
```python
for p in (
    # ... existing permissions ...
    p_equipment_view,
    p_equipment_create,
    p_equipment_edit,
    p_equipment_upload,
    p_suppliers_view,
    p_suppliers_create,
    p_suppliers_edit,
    p_suppliers_upload,
):
    if p not in role_admin.permissions:
        role_admin.permissions.append(p)
```

---

## 4) Storage / Folder Structure (CRITICAL)

### Storage Key Conventions

**Equipment Documents:**
- Pattern: `equipment/<equip_code>/<yyyy-mm-dd>/<sanitized_filename>`
- Example: `equipment/ST-001/2026-01-15/calibration_cert_2026.pdf`
- Rationale:
  - `equip_code` is unique and human-readable (better than ID)
  - Date prefix enables chronological organization
  - Sanitized filename prevents path traversal

**Supplier Documents:**
- Pattern: `suppliers/<supplier_id>/<yyyy-mm-dd>/<sanitized_filename>`
- Example: `suppliers/42/2026-01-15/audit_report_2026.pdf`
- Rationale:
  - `supplier_id` is numeric (supplier names may have special chars)
  - Date prefix enables chronological organization
  - Sanitized filename prevents path traversal

**Implementation:**

**File:** `app/eqms/modules/equipment/service.py` (or `app/eqms/modules/shared/storage_helpers.py`)

```python
from datetime import date
from werkzeug.utils import secure_filename

def build_equipment_storage_key(equip_code: str, filename: str, upload_date: date | None = None) -> str:
    """Build deterministic storage key for equipment document."""
    if upload_date is None:
        upload_date = date.today()
    safe_code = equip_code.replace("/", "_").replace("\\", "_")  # Prevent path traversal
    safe_filename = secure_filename(filename) or "document.bin"
    return f"equipment/{safe_code}/{upload_date.isoformat()}/{safe_filename}"

def build_supplier_storage_key(supplier_id: int, filename: str, upload_date: date | None = None) -> str:
    """Build deterministic storage key for supplier document."""
    if upload_date is None:
        upload_date = date.today()
    safe_filename = secure_filename(filename) or "document.bin"
    return f"suppliers/{supplier_id}/{upload_date.isoformat()}/{safe_filename}"
```

**Usage in upload routes:**
```python
from app.eqms.modules.equipment.service import build_equipment_storage_key
from app.eqms.storage import storage_from_config
from flask import current_app

storage_key = build_equipment_storage_key(equipment.equip_code, filename)
storage = storage_from_config(current_app.config)
storage.put_bytes(storage_key, file_bytes, content_type=content_type)
```

**Path Traversal Prevention:**
- Use `secure_filename()` from Werkzeug (already used in document_control)
- Normalize `equip_code` (replace `/` and `\` with `_`)
- Use `supplier_id` (numeric) instead of supplier name
- Store canonical `storage_key` in DB (never trust user input for storage paths)

**Local vs S3:**
- Works identically for both backends (storage abstraction handles it)
- Local: Creates directory structure under `storage/equipment/...` or `storage/suppliers/...`
- S3: Creates "folders" via key prefixes (S3 doesn't have real folders, but keys with `/` work like folders)

---

### Document Listing

**For Equipment Detail Page:**
```python
# In equipment detail route
documents = (
    s.query(ManagedDocument)
    .filter(ManagedDocument.entity_type == "equipment")
    .filter(ManagedDocument.entity_id == equipment.id)
    .filter(ManagedDocument.is_deleted == False)  # Exclude soft-deleted
    .order_by(ManagedDocument.uploaded_at.desc())
    .all()
)
```

**For Supplier Detail Page:**
```python
# In supplier detail route
documents = (
    s.query(ManagedDocument)
    .filter(ManagedDocument.entity_type == "supplier")
    .filter(ManagedDocument.entity_id == supplier.id)
    .filter(ManagedDocument.is_deleted == False)
    .order_by(ManagedDocument.uploaded_at.desc())
    .all()
)
```

---

### Document Deletion

**Option 1: Soft Delete (Recommended)**
- Set `is_deleted=True`, `deleted_at=datetime.utcnow()`, `deleted_by_user_id=user.id`
- Keep file in storage (for audit trail)
- Filter out deleted documents in queries

**Option 2: Hard Delete**
- Delete `ManagedDocument` record (CASCADE deletes FK relationships)
- Optionally delete file from storage (may want to keep for audit)
- Log deletion in audit trail

**Recommendation:** Use soft delete for compliance (documents are evidence).

---

## 5) UI/UX Behavior (Admin-First, Minimal Clutter)

### Equipment List Page

**Route:** `GET /admin/equipment`

**Table Columns:**
- Equip Code (link to detail)
- Status (badge: Active/Inactive/Retired/Calibration Overdue/PM Overdue)
- Description (truncated if long)
- Location
- CAL Due Date (highlight red if overdue)
- PM Due Date (highlight red if overdue)
- #Docs (count of non-deleted documents)
- #Suppliers (count of associated suppliers)
- Actions: [View] [Edit]

**Filters:**
- Search box (searches equip_code, description, mfg, model_no, serial_no)
- Status dropdown (All, Active, Inactive, Retired, Calibration Overdue, PM Overdue)
- Location dropdown (All, or list of unique locations)
- "CAL overdue" checkbox (filters where `cal_due_date < today()`)
- "PM overdue" checkbox (filters where `pm_due_date < today()`)

**Pagination:**
- 50 items per page (configurable)

**Actions:**
- [New Equipment] button (top right)
- [Export] button (CSV export of filtered list)

---

### Equipment Detail Page

**Route:** `GET /admin/equipment/<equipment_id>`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Equipment: ST-001                                    [Edit] │
├─────────────────────────────────────────────────────────────┤
│ Metadata Card:                                              │
│ - Equip Code: ST-001                                        │
│ - Status: Active                                            │
│ - Description: Sterilization Chamber                        │
│ - Manufacturer: Acme Corp                                   │
│ - Model: ST-1000                                            │
│ - Serial: 12345                                             │
│ - Location: Lab A                                           │
│ - Date in Service: 2025-01-01                               │
│ - CAL Due: 2026-02-01 (highlight if overdue)               │
│ - PM Due: 2026-03-01 (highlight if overdue)                │
│ - Comments: ...                                             │
├─────────────────────────────────────────────────────────────┤
│ Associated Suppliers:                                       │
│ - Acme Corp (Manufacturer) [Remove]                        │
│ - Calibration Services Inc (Service Provider) [Remove]      │
│ [Add Supplier] button                                       │
├─────────────────────────────────────────────────────────────┤
│ Documents:                                                  │
│ - calibration_cert_2026.pdf (Calibration Cert) [Download] │
│ - pm_record_2026.pdf (PM Record) [Download] [Delete]      │
│ [Upload Document] button                                    │
└─────────────────────────────────────────────────────────────┘
```

**Sections:**
1. **Metadata Card:** All equipment fields (read-only, unless in edit mode)
2. **Associated Suppliers:** List of suppliers with relationship type, [Remove] button per supplier
3. **Documents:** List of documents with type, upload date, [Download] and [Delete] buttons

**Actions:**
- [Edit] button (top right) → Edit form
- [Add Supplier] button → Modal or separate page to select supplier
- [Upload Document] button → Upload form (file + description + document_type)

---

### Equipment Edit Page

**Route:** `GET /admin/equipment/<equipment_id>/edit` (form)  
**Route:** `POST /admin/equipment/<equipment_id>/edit` (submit)

**Form Fields:**
- Equip Code (read-only, cannot change)
- Status (dropdown)
- Description (text input)
- Manufacturer (text input)
- Model No (text input)
- Serial No (text input)
- Date in Service (date input)
- Location (text input)
- CAL Interval (number input, days)
- Last CAL Date (date input)
- CAL Due Date (date input, auto-calculated if interval provided)
- PM Interval (number input, days)
- Last PM Date (date input)
- PM Due Date (date input, auto-calculated if interval provided)
- Comments (textarea)

**Validation:**
- Equip Code must be unique (if creating new)
- Status must be valid value
- Dates must be valid (YYYY-MM-DD)
- CAL/PM intervals must be positive integers

**On Submit:**
- Update equipment record
- Log audit event: `equipment.edit`
- Require reason-for-change (if status changes or critical fields change)

---

### Supplier List Page

**Route:** `GET /admin/suppliers`

**Table Columns:**
- Name (link to detail)
- Status (badge: Approved/Conditional/Pending/Rejected)
- Category
- Certification Expiration (highlight red if expired)
- #Equipment (count of associated equipment)
- #Docs (count of non-deleted documents)
- Actions: [View] [Edit]

**Filters:**
- Search box (searches name, product_service_provided)
- Status dropdown (All, Approved, Conditional, Pending, Rejected)
- Category dropdown (All, or list of unique categories)

**Pagination:**
- 50 items per page

**Actions:**
- [New Supplier] button (top right)
- [Export] button (CSV export)

---

### Supplier Detail Page

**Route:** `GET /admin/suppliers/<supplier_id>`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Supplier: Acme Corp                                  [Edit] │
├─────────────────────────────────────────────────────────────┤
│ Metadata Card:                                              │
│ - Name: Acme Corp                                           │
│ - Status: Approved                                          │
│ - Category: Component Supplier                              │
│ - Products/Services: Sterilization equipment                │
│ - Address: 123 Main St, City, State 12345                  │
│ - Initial Listing Date: 2025-01-01                          │
│ - Certification Expiration: 2026-12-31                      │
│ - Notes: ...                                                │
├─────────────────────────────────────────────────────────────┤
│ Associated Equipment:                                       │
│ - ST-001 (Manufacturer) [Remove]                           │
│ - ST-002 (Manufacturer) [Remove]                           │
│ [Add Equipment] button                                      │
├─────────────────────────────────────────────────────────────┤
│ Documents:                                                  │
│ - audit_report_2026.pdf (Audit Report) [Download]          │
│ - coi_2026.pdf (COI) [Download] [Delete]                   │
│ [Upload Document] button                                    │
└─────────────────────────────────────────────────────────────┘
```

**Sections:**
1. **Metadata Card:** All supplier fields
2. **Associated Equipment:** List of equipment with relationship type, [Remove] button
3. **Documents:** List of documents with type, upload date, [Download] and [Delete] buttons

---

### Supplier Edit Page

**Route:** `GET /admin/suppliers/<supplier_id>/edit` (form)  
**Route:** `POST /admin/suppliers/<supplier_id>/edit` (submit)

**Form Fields:**
- Name (required)
- Status (dropdown: Approved, Conditional, Pending, Rejected)
- Category (text input, optional)
- Products/Services (textarea, optional)
- Address (textarea, optional)
- Initial Listing Date (date input, optional)
- Certification Expiration (date input, optional)
- Notes (textarea, optional)

**Validation:**
- Name must be non-empty
- Status must be valid value
- Dates must be valid

**On Submit:**
- Update supplier record
- Log audit event: `supplier.edit`
- Require reason-for-change (if status changes)

---

### Document Upload Forms

**Route:** `POST /admin/equipment/<equipment_id>/documents/upload`  
**Route:** `POST /admin/suppliers/<supplier_id>/documents/upload`

**Form Fields:**
- File (file input, required)
- Description (text input, optional)
- Document Type (dropdown, optional):
  - Equipment: "Calibration Cert", "PM Record", "Manual", "Photo", "Other"
  - Supplier: "Audit Report", "Approval Letter", "Certification", "Quality Agreement", "COI", "Other"

**On Submit:**
- Validate file (size limits, file type if needed)
- Compute SHA256 digest
- Build storage key
- Upload to storage
- Create `ManagedDocument` record
- Log audit event: `equipment.document_upload` or `supplier.document_upload`

---

### Add Association Forms

**Route:** `POST /admin/equipment/<equipment_id>/suppliers` (add supplier to equipment)  
**Route:** `POST /admin/suppliers/<supplier_id>/equipment` (add equipment to supplier)

**Form Fields:**
- Supplier (dropdown, if adding to equipment) or Equipment (dropdown, if adding to supplier)
- Relationship Type (dropdown: "Manufacturer", "Service Provider", "Parts Supplier", "Other")
- Notes (textarea, optional)

**On Submit:**
- Check for duplicate association (unique constraint prevents, but check first for better error)
- Create `EquipmentSupplier` record
- Log audit event: `equipment.supplier_added` or `supplier.equipment_added`

---

## 6) Import/Seed Plan from Provided Files

### Source Files

1. **Equipment:** `Silq Equipment Master List.xlsx`
2. **Suppliers:** `SILQ Approved Supplier List Feb 2025.docx`

---

### Import Script Structure

**File:** `scripts/import_equipment_and_suppliers.py`

**Dependencies:**
- `openpyxl` for Excel parsing (add to `requirements.txt` if not present)
- `python-docx` for Word doc parsing (add to `requirements.txt` if not present)

**Function: `import_equipment_from_excel(filepath: str, s: Session, user: User) -> dict`**

**Steps:**
1. Open Excel file
2. Read rows (skip header)
3. For each row:
   - Extract: Equip Code, Status, Description, Mfg, Model No, Serial No, Date in Service, Location, CAL Interval, Last CAL Date, CAL Due Date, PM Interval, Last PM Date, PM Due Date, Comments
   - Normalize equip_code (uppercase, strip)
   - Check if equipment exists (by `equip_code`)
   - If exists: Skip or update (idempotent strategy: skip if exists)
   - If not exists: Create `Equipment` record
   - Store `mfg` value for later supplier matching
4. Return: `{"created": count, "skipped": count, "errors": list}`

**Function: `import_suppliers_from_docx(filepath: str, s: Session, user: User) -> dict`**

**Steps:**
1. Open Word doc
2. Parse table or text (depends on doc structure)
3. For each supplier:
   - Extract: Name, Status, Category, Products/Services, Address, Initial Listing Date, Certification Expiration, Notes
   - Normalize supplier name (strip, title case)
   - Check if supplier exists (by normalized name)
   - If exists: Skip or update
   - If not exists: Create `Supplier` record
4. Return: `{"created": count, "skipped": count, "errors": list}`

**Function: `link_equipment_suppliers(s: Session, user: User) -> dict`**

**Steps:**
1. Query all equipment with `mfg` field populated
2. For each equipment:
   - Normalize `mfg` (strip, title case, remove common suffixes like "Inc", "LLC")
   - Query suppliers where normalized name matches normalized `mfg`
   - If match found:
     - Check if association already exists
     - If not: Create `EquipmentSupplier` with `relationship_type="Manufacturer"`
3. Return: `{"linked": count, "skipped": count}`

**Matching Strategy:**
- Normalize both equipment `mfg` and supplier `name`:
  - Strip whitespace
  - Title case
  - Remove common suffixes: "Inc", "LLC", "Corp", "Corporation", "Ltd", "Limited"
  - Remove punctuation
- If normalized strings match (case-insensitive), create association
- If no match, leave unlinked (admin can associate manually)

**Idempotency:**
- Equipment: Use `equip_code` as natural key (unique constraint prevents duplicates)
- Suppliers: Use normalized `name` as natural key (check before insert)
- Associations: Unique constraint on `(equipment_id, supplier_id)` prevents duplicates

**Usage:**
```bash
python scripts/import_equipment_and_suppliers.py
```

**Script Structure:**
```python
def main():
    database_url = os.environ.get("DATABASE_URL") or "sqlite:///eqms.db"
    admin_email = os.environ.get("ADMIN_EMAIL") or "admin@silqeqms.com"
    
    # ... setup session, get admin user ...
    
    # Import equipment
    equipment_file = "Silq Equipment Master List.xlsx"
    equipment_result = import_equipment_from_excel(equipment_file, s, admin_user)
    print(f"Equipment: {equipment_result}")
    
    # Import suppliers
    suppliers_file = "SILQ Approved Supplier List Feb 2025.docx"
    suppliers_result = import_suppliers_from_docx(suppliers_file, s, admin_user)
    print(f"Suppliers: {suppliers_result}")
    
    # Link equipment ↔ suppliers
    link_result = link_equipment_suppliers(s, admin_user)
    print(f"Associations: {link_result}")
    
    s.commit()
```

---

## 7) Audit Trail Requirements

### Required Audit Events

**Equipment Events:**
- `equipment.create` - Equipment created
  - Entity: `Equipment`
  - Entity ID: `equipment.id`
  - Metadata: `{"equip_code": "...", "status": "...", "description": "..."}`
- `equipment.edit` - Equipment updated
  - Entity: `Equipment`
  - Entity ID: `equipment.id`
  - Reason: Required (reason-for-change)
  - Metadata: `{"equip_code": "...", "changes": {...}}`
- `equipment.document_upload` - Document uploaded to equipment
  - Entity: `ManagedDocument`
  - Entity ID: `document.id`
  - Metadata: `{"equipment_id": ..., "equip_code": "...", "filename": "...", "document_type": "..."}`
- `equipment.document_download` - Document downloaded (optional)
  - Entity: `ManagedDocument`
  - Entity ID: `document.id`
  - Metadata: `{"equipment_id": ..., "filename": "..."}`
- `equipment.document_delete` - Document deleted (soft or hard)
  - Entity: `ManagedDocument`
  - Entity ID: `document.id`
  - Reason: Required
  - Metadata: `{"equipment_id": ..., "filename": "..."}`
- `equipment.supplier_added` - Supplier associated with equipment
  - Entity: `EquipmentSupplier`
  - Entity ID: `association.id`
  - Metadata: `{"equipment_id": ..., "supplier_id": ..., "relationship_type": "..."}`
- `equipment.supplier_removed` - Supplier association removed
  - Entity: `EquipmentSupplier`
  - Entity ID: `association.id` (before deletion)
  - Reason: Required
  - Metadata: `{"equipment_id": ..., "supplier_id": ...}`

**Supplier Events:**
- `supplier.create` - Supplier created
  - Entity: `Supplier`
  - Entity ID: `supplier.id`
  - Metadata: `{"name": "...", "status": "..."}`
- `supplier.edit` - Supplier updated
  - Entity: `Supplier`
  - Entity ID: `supplier.id`
  - Reason: Required (if status changes)
  - Metadata: `{"name": "...", "changes": {...}}`
- `supplier.document_upload` - Document uploaded to supplier
  - Entity: `ManagedDocument`
  - Entity ID: `document.id`
  - Metadata: `{"supplier_id": ..., "name": "...", "filename": "...", "document_type": "..."}`
- `supplier.document_download` - Document downloaded (optional)
  - Entity: `ManagedDocument`
  - Entity ID: `document.id`
  - Metadata: `{"supplier_id": ..., "filename": "..."}`
- `supplier.document_delete` - Document deleted
  - Entity: `ManagedDocument`
  - Entity ID: `document.id`
  - Reason: Required
  - Metadata: `{"supplier_id": ..., "filename": "..."}`
- `supplier.equipment_added` - Equipment associated with supplier
  - Entity: `EquipmentSupplier`
  - Entity ID: `association.id`
  - Metadata: `{"supplier_id": ..., "equipment_id": ..., "relationship_type": "..."}`
- `supplier.equipment_removed` - Equipment association removed
  - Entity: `EquipmentSupplier`
  - Entity ID: `association.id` (before deletion)
  - Reason: Required
  - Metadata: `{"supplier_id": ..., "equipment_id": ...}`

**Implementation:**
- Use `record_event()` from `app.eqms.audit`
- Call in service layer (not routes) for consistency
- Always include `actor=user`, `action=...`, `entity_type=...`, `entity_id=...`
- Include `reason=...` for controlled operations (edits, deletes, association removals)

---

## 8) Implementation Checklist (Developer Task List)

### Phase 1: Models & Migrations

- [ ] **Task 1.1:** Create `app/eqms/modules/equipment/models.py`
  - Define `Equipment` model
  - Define `EquipmentSupplier` model
  - Define `ManagedDocument` model (or put in shared location)
  - Add relationships

- [ ] **Task 1.2:** Create `app/eqms/modules/suppliers/models.py`
  - Define `Supplier` model
  - Add relationships to `EquipmentSupplier` and `ManagedDocument`

- [ ] **Task 1.3:** Update `app/eqms/models.py`
  - Import equipment and supplier models at bottom

- [ ] **Task 1.4:** Create Alembic migration
  - Run `alembic revision -m "add equipment and suppliers tables"`
  - Implement `upgrade()` with all tables and indexes
  - Implement `downgrade()`
  - Test: `alembic upgrade head` and `alembic downgrade -1`

- [ ] **Task 1.5:** Verify models import correctly
  - Run `alembic autogenerate` (should detect no differences)

---

### Phase 2: Permissions & Seed

- [ ] **Task 2.1:** Update `scripts/init_db.py`
  - Add equipment permissions: `equipment.view`, `equipment.create`, `equipment.edit`, `equipment.upload`
  - Add supplier permissions: `suppliers.view`, `suppliers.create`, `suppliers.edit`, `suppliers.upload`
  - Grant all permissions to `admin` role

- [ ] **Task 2.2:** Test permissions seed
  - Run `python scripts/init_db.py`
  - Verify permissions exist in database
  - Verify `admin` role has all permissions

---

### Phase 3: Service Layer

- [ ] **Task 3.1:** Create `app/eqms/modules/equipment/service.py`
  - `create_equipment(s, payload, user) -> Equipment`
  - `update_equipment(s, equipment, payload, user, reason) -> Equipment`
  - `build_equipment_storage_key(equip_code, filename, upload_date) -> str`
  - `upload_equipment_document(s, equipment, file_bytes, filename, content_type, user, description, document_type) -> ManagedDocument`
  - `delete_equipment_document(s, document, user, reason) -> None`
  - `add_supplier_to_equipment(s, equipment, supplier, relationship_type, notes, user) -> EquipmentSupplier`
  - `remove_supplier_from_equipment(s, association, user, reason) -> None`

- [ ] **Task 3.2:** Create `app/eqms/modules/suppliers/service.py`
  - `create_supplier(s, payload, user) -> Supplier`
  - `update_supplier(s, supplier, payload, user, reason) -> Supplier`
  - `build_supplier_storage_key(supplier_id, filename, upload_date) -> str`
  - `upload_supplier_document(s, supplier, file_bytes, filename, content_type, user, description, document_type) -> ManagedDocument`
  - `delete_supplier_document(s, document, user, reason) -> None`
  - `add_equipment_to_supplier(s, supplier, equipment, relationship_type, notes, user) -> EquipmentSupplier`
  - `remove_equipment_from_supplier(s, association, user, reason) -> None`

- [ ] **Task 3.3:** Add validation helpers
  - Validate equipment payload (equip_code required, status valid, dates valid)
  - Validate supplier payload (name required, status valid, dates valid)
  - Validate document upload (file size limits, content type if needed)

---

### Phase 4: Routes/Controllers

- [ ] **Task 4.1:** Create `app/eqms/modules/equipment/admin.py`
  - Blueprint: `bp = Blueprint("equipment", __name__)`
  - Route: `GET /equipment` → `equipment_list()` (list with filters)
  - Route: `GET /equipment/new` → `equipment_new_get()`
  - Route: `POST /equipment/new` → `equipment_new_post()`
  - Route: `GET /equipment/<id>` → `equipment_detail(id)`
  - Route: `GET /equipment/<id>/edit` → `equipment_edit_get(id)`
  - Route: `POST /equipment/<id>/edit` → `equipment_edit_post(id)`
  - Route: `POST /equipment/<id>/documents/upload` → `equipment_document_upload(id)`
  - Route: `GET /equipment/<id>/documents/<doc_id>/download` → `equipment_document_download(id, doc_id)`
  - Route: `POST /equipment/<id>/documents/<doc_id>/delete` → `equipment_document_delete(id, doc_id)`
  - Route: `POST /equipment/<id>/suppliers` → `equipment_supplier_add(id)`
  - Route: `POST /equipment/<id>/suppliers/<supplier_id>/remove` → `equipment_supplier_remove(id, supplier_id)`

- [ ] **Task 4.2:** Create `app/eqms/modules/suppliers/admin.py`
  - Blueprint: `bp = Blueprint("suppliers", __name__)`
  - Route: `GET /suppliers` → `suppliers_list()` (list with filters)
  - Route: `GET /suppliers/new` → `suppliers_new_get()`
  - Route: `POST /suppliers/new` → `suppliers_new_post()`
  - Route: `GET /suppliers/<id>` → `supplier_detail(id)`
  - Route: `GET /suppliers/<id>/edit` → `supplier_edit_get(id)`
  - Route: `POST /suppliers/<id>/edit` → `supplier_edit_post(id)`
  - Route: `POST /suppliers/<id>/documents/upload` → `supplier_document_upload(id)`
  - Route: `GET /suppliers/<id>/documents/<doc_id>/download` → `supplier_document_download(id, doc_id)`
  - Route: `POST /suppliers/<id>/documents/<doc_id>/delete` → `supplier_document_delete(id, doc_id)`
  - Route: `POST /suppliers/<id>/equipment` → `supplier_equipment_add(id)`
  - Route: `POST /suppliers/<id>/equipment/<equipment_id>/remove` → `supplier_equipment_remove(id, equipment_id)`

- [ ] **Task 4.3:** Register blueprints in `app/eqms/__init__.py`
  - Import: `from app.eqms.modules.equipment.admin import bp as equipment_bp`
  - Import: `from app.eqms.modules.suppliers.admin import bp as suppliers_bp`
  - Register: `app.register_blueprint(equipment_bp, url_prefix="/admin")`
  - Register: `app.register_blueprint(suppliers_bp, url_prefix="/admin")`

- [ ] **Task 4.4:** Add RBAC decorators to all routes
  - Use `@require_permission("equipment.view")`, etc.
  - Ensure all routes check permissions

---

### Phase 5: Templates/UI

- [ ] **Task 5.1:** Create equipment templates
  - `app/eqms/templates/admin/equipment/list.html` (list with filters, table)
  - `app/eqms/templates/admin/equipment/detail.html` (metadata + suppliers + documents)
  - `app/eqms/templates/admin/equipment/edit.html` (edit form)
  - `app/eqms/templates/admin/equipment/new.html` (create form)

- [ ] **Task 5.2:** Create supplier templates
  - `app/eqms/templates/admin/suppliers/list.html` (list with filters, table)
  - `app/eqms/templates/admin/suppliers/detail.html` (metadata + equipment + documents)
  - `app/eqms/templates/admin/suppliers/edit.html` (edit form)
  - `app/eqms/templates/admin/suppliers/new.html` (create form)

- [ ] **Task 5.3:** Update `app/eqms/templates/admin/index.html`
  - Change "PLM" card to "Equipment" (link to `equipment.equipment_list`)
  - Change "Supplier Management" card to link to `suppliers.suppliers_list` (remove stub)

- [ ] **Task 5.4:** Reuse existing design system
  - Use `_layout.html` base template
  - Use `design-system.css` for styling
  - Match existing admin UI patterns (cards, tables, forms)

---

### Phase 6: Storage Integration

- [ ] **Task 6.1:** Implement storage key builders
  - `build_equipment_storage_key()` in `equipment/service.py`
  - `build_supplier_storage_key()` in `suppliers/service.py` (or shared location)

- [ ] **Task 6.2:** Test storage integration
  - Upload document to equipment (verify file appears in storage)
  - Upload document to supplier (verify file appears in storage)
  - Download documents (verify files are readable)
  - Test with both local and S3 backends (if S3 configured)

---

### Phase 7: Import Scripts

- [ ] **Task 7.1:** Create `scripts/import_equipment_and_suppliers.py`
  - Implement `import_equipment_from_excel()`
  - Implement `import_suppliers_from_docx()`
  - Implement `link_equipment_suppliers()`
  - Add idempotency checks (skip if exists)

- [ ] **Task 7.2:** Add dependencies to `requirements.txt`
  - `openpyxl` (for Excel parsing)
  - `python-docx` (for Word doc parsing)

- [ ] **Task 7.3:** Test import scripts
  - Run import script
  - Verify equipment rows created
  - Verify supplier rows created
  - Verify associations created (where mfg matches supplier name)
  - Re-run script (verify idempotency - no duplicates)

---

### Phase 8: Tests

- [ ] **Task 8.1:** Create smoke tests
  - `tests/test_equipment.py`: Test equipment CRUD, document upload/download
  - `tests/test_suppliers.py`: Test supplier CRUD, document upload/download
  - `tests/test_equipment_suppliers.py`: Test associations

- [ ] **Task 8.2:** Test permissions
  - Verify routes require correct permissions
  - Verify 403 when permission missing

- [ ] **Task 8.3:** Test audit trail
  - Verify audit events logged for all operations
  - Verify reason-for-change required for edits/deletes

---

### Phase 9: Documentation Updates

- [ ] **Task 9.1:** Update `README.md`
  - Change "PLM" → "Equipment" in module list (line 17)

- [ ] **Task 9.2:** Update `docs/01_ARCHITECTURE_OVERVIEW.md`
  - Change "PLM" → "Equipment" in module list (if present)

- [ ] **Task 9.3:** Update `docs/03_MODULE_SPECS.md`
  - Change section header "PLM" → "Equipment" (line 19)
  - Update section content to reflect Equipment module (not PLM)

---

## 9) Acceptance Criteria (Very Explicit)

### Equipment Module

- [ ] **AC1:** Admin can create a new equipment item
  - Navigate to `/admin/equipment/new`
  - Fill form: Equip Code="TEST-001", Status="Active", Description="Test Equipment"
  - Submit
  - Redirected to `/admin/equipment/<id>` detail page
  - Equipment appears in list at `/admin/equipment`

- [ ] **AC2:** Admin can upload a document to equipment
  - Navigate to equipment detail page
  - Click [Upload Document]
  - Select file (PDF), enter description="Calibration Cert", type="Calibration Cert"
  - Submit
  - Document appears in documents list
  - File is stored in storage at `equipment/TEST-001/2026-01-15/calibration_cert.pdf`

- [ ] **AC3:** Admin can download equipment document
  - Navigate to equipment detail page
  - Click [Download] on a document
  - File downloads with correct filename and content

- [ ] **AC4:** Admin can associate supplier with equipment
  - Navigate to equipment detail page
  - Click [Add Supplier]
  - Select supplier from dropdown, relationship type="Manufacturer"
  - Submit
  - Supplier appears in "Associated Suppliers" section
  - Association appears on supplier detail page under "Associated Equipment"

- [ ] **AC5:** Equipment list filters work
  - Navigate to `/admin/equipment`
  - Filter by Status="Active"
  - Only active equipment shown
  - Filter by "CAL overdue"
  - Only equipment with `cal_due_date < today()` shown

- [ ] **AC6:** Equipment edit requires reason-for-change
  - Navigate to equipment edit page
  - Change status from "Active" to "Inactive"
  - Submit without reason
  - Error: "Reason is required for edits"
  - Enter reason, submit
  - Equipment updated, audit event logged with reason

---

### Supplier Module

- [ ] **AC7:** Admin can create a new supplier
  - Navigate to `/admin/suppliers/new`
  - Fill form: Name="Test Supplier", Status="Approved"
  - Submit
  - Redirected to `/admin/suppliers/<id>` detail page
  - Supplier appears in list at `/admin/suppliers`

- [ ] **AC8:** Admin can upload a document to supplier
  - Navigate to supplier detail page
  - Click [Upload Document]
  - Select file (PDF), enter description="Audit Report", type="Audit Report"
  - Submit
  - Document appears in documents list
  - File is stored in storage at `suppliers/42/2026-01-15/audit_report.pdf`

- [ ] **AC9:** Admin can download supplier document
  - Navigate to supplier detail page
  - Click [Download] on a document
  - File downloads with correct filename and content

- [ ] **AC10:** Admin can associate equipment with supplier
  - Navigate to supplier detail page
  - Click [Add Equipment]
  - Select equipment from dropdown, relationship type="Manufacturer"
  - Submit
  - Equipment appears in "Associated Equipment" section
  - Association appears on equipment detail page under "Associated Suppliers"

---

### Import/Seed

- [ ] **AC11:** Import script creates equipment from Excel
  - Run `python scripts/import_equipment_and_suppliers.py`
  - Verify equipment rows created (count matches Excel rows)
  - Verify `equip_code` values match Excel
  - Re-run script (verify idempotency - no duplicates)

- [ ] **AC12:** Import script creates suppliers from Word doc
  - Run import script
  - Verify supplier rows created (count matches doc rows)
  - Verify supplier names match doc
  - Re-run script (verify idempotency)

- [ ] **AC13:** Import script links equipment ↔ suppliers
  - Run import script
  - Verify associations created where equipment `mfg` matches supplier `name` (normalized)
  - Verify `relationship_type="Manufacturer"` for auto-linked associations

---

### Permissions & Security

- [ ] **AC14:** Permissions enforced
  - Log in as user without `equipment.view` permission
  - Navigate to `/admin/equipment`
  - Receive 403 Forbidden
  - Log in as admin (has all permissions)
  - Can access all routes

- [ ] **AC15:** Audit events logged
  - Create equipment → Verify `equipment.create` event in audit log
  - Edit equipment → Verify `equipment.edit` event with reason
  - Upload document → Verify `equipment.document_upload` event
  - Add supplier association → Verify `equipment.supplier_added` event

---

### Storage

- [ ] **AC16:** Storage works for both local and S3
  - Upload document with `STORAGE_BACKEND=local`
  - Verify file in `storage/equipment/...` directory
  - Change to `STORAGE_BACKEND=s3` (if S3 configured)
  - Upload document
  - Verify file in S3 bucket at `equipment/...` key

- [ ] **AC17:** Storage keys are deterministic
  - Upload same file twice (different dates)
  - Verify storage keys differ (date prefix different)
  - Verify both files accessible

---

### UI/UX

- [ ] **AC18:** Lists render without errors
  - Navigate to `/admin/equipment` (no errors, table renders)
  - Navigate to `/admin/suppliers` (no errors, table renders)
  - Apply filters (no errors, filtered results shown)

- [ ] **AC19:** Navigation updated
  - Navigate to `/admin`
  - Verify "Equipment" card exists (not "PLM")
  - Verify "Suppliers" card exists (not stub)
  - Click cards → Navigate to correct pages

---

## Summary

**Scope:** Equipment module (new) + Supplier Management enhancements (foldering + associations)

**Files Created:** ~15 files (models, services, routes, templates, import script)

**Files Modified:** ~5 files (models.py, init_db.py, __init__.py, admin/index.html, README.md)

**Migrations:** 1 migration (equipment, suppliers, equipment_suppliers, managed_documents tables)

**Permissions:** 8 new permissions (4 equipment, 4 suppliers)

**Risk:** Low (follows existing patterns, no new subsystems)

**Estimated Effort:** 2-3 days for experienced developer

---

## References

- **Existing Patterns:** `app/eqms/modules/document_control/` (models, routes, templates)
- **Storage:** `app/eqms/storage.py` (storage abstraction)
- **Audit:** `app/eqms/audit.py` (audit trail)
- **RBAC:** `app/eqms/rbac.py` (permissions)
- **Module Specs:** `docs/03_MODULE_SPECS.md`
- **Data Model Draft:** `docs/04_DATA_MODEL_DRAFT.md`
