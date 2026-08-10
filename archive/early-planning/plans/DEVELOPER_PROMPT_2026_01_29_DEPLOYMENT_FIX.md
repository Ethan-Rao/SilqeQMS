# Developer Agent Prompt: Deployment Fix + Equipment/Supplier PDF Parsing

**Date:** 2026-01-29  
**Priority:** P0 - Deployment is blocked  
**Focus:** Fix migration failure, then implement PDF field extraction for Equipment & Suppliers

---

## CRITICAL: Deployment Blocked - Migration Failure (P0)

### Error
```
Release failed: (psycopg2.errors.UndefinedColumn) column "is_active" of relation "reps" does not exist
LINE 2:         INSERT INTO reps (id, name, email, is_active, create...
```

### Root Cause
The `reps` table **already exists** in production (from a previous partial deployment), but it was created **without the `is_active` column**. The migration checks `if not insp.has_table("reps")` which returns FALSE (table exists), so table creation is skipped. But the subsequent INSERT statement references `is_active`, which doesn't exist.

### Fix Required

**File:** `migrations/versions/h2i3j4k5l6m_create_reps_table.py`

Replace the `upgrade()` function with this more robust version that handles partial states:

```python
def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Create table if it doesn't exist
    if not insp.has_table("reps"):
        op.create_table(
            "reps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("phone", sa.Text(), nullable=True),
            sa.Column("territory", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        )
    else:
        # Table exists - ensure all columns exist (handles partial state from failed deployments)
        existing_columns = {col["name"] for col in insp.get_columns("reps")}
        
        if "is_active" not in existing_columns:
            op.add_column("reps", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        
        if "phone" not in existing_columns:
            op.add_column("reps", sa.Column("phone", sa.Text(), nullable=True))
        
        if "territory" not in existing_columns:
            op.add_column("reps", sa.Column("territory", sa.Text(), nullable=True))
        
        if "created_at" not in existing_columns:
            op.add_column("reps", sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")))
        
        if "updated_at" not in existing_columns:
            op.add_column("reps", sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")))

    # Ensure index exists
    existing_indexes = {idx["name"] for idx in insp.get_indexes("reps")} if insp.has_table("reps") else set()
    if "idx_reps_name" not in existing_indexes:
        op.create_index("idx_reps_name", "reps", ["name"])

    # Seed reps from users referenced by rep assignments.
    # Only insert if the user id doesn't already exist in reps
    op.execute(
        """
        INSERT INTO reps (id, name, email, is_active, created_at, updated_at)
        SELECT DISTINCT u.id, u.email, u.email, u.is_active, NOW(), NOW()
        FROM users u
        WHERE u.id IN (
            SELECT DISTINCT primary_rep_id FROM customers WHERE primary_rep_id IS NOT NULL
            UNION
            SELECT DISTINCT rep_id FROM customer_reps WHERE rep_id IS NOT NULL
            UNION
            SELECT DISTINCT rep_id FROM distribution_log_entries WHERE rep_id IS NOT NULL
        )
        ON CONFLICT (id) DO NOTHING
        """
    )

    # Repoint foreign keys to reps (Postgres-safe).
    op.execute("ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_primary_rep_id_fkey")
    op.execute(
        """
        DO $$
        BEGIN
          ALTER TABLE customers
          ADD CONSTRAINT customers_primary_rep_id_fkey
          FOREIGN KEY (primary_rep_id) REFERENCES reps (id) ON DELETE SET NULL;
        EXCEPTION WHEN duplicate_object THEN
          NULL;
        END $$;
        """
    )

    op.execute("ALTER TABLE customer_reps DROP CONSTRAINT IF EXISTS customer_reps_rep_id_fkey")
    op.execute(
        """
        DO $$
        BEGIN
          ALTER TABLE customer_reps
          ADD CONSTRAINT customer_reps_rep_id_fkey
          FOREIGN KEY (rep_id) REFERENCES reps (id) ON DELETE CASCADE;
        EXCEPTION WHEN duplicate_object THEN
          NULL;
        END $$;
        """
    )

    op.execute("ALTER TABLE distribution_log_entries DROP CONSTRAINT IF EXISTS distribution_log_entries_rep_id_fkey")
    op.execute(
        """
        DO $$
        BEGIN
          ALTER TABLE distribution_log_entries
          ADD CONSTRAINT distribution_log_entries_rep_id_fkey
          FOREIGN KEY (rep_id) REFERENCES reps (id) ON DELETE SET NULL;
        EXCEPTION WHEN duplicate_object THEN
          NULL;
        END $$;
        """
    )
```

### Verification After Fix
1. Commit and push the migration fix
2. Redeploy
3. Check deploy logs - should show migration success
4. Verify `/admin/reps` page loads

---

## P1: Equipment & Supplier PDF Field Extraction

### Overview

Ethan will upload PDF documents to Equipment and Supplier records. The system should:

1. **Parse uploaded PDFs** and extract field values automatically
2. **Auto-populate form fields** with extracted data
3. **Allow admin full control** - admin can:
   - Edit any auto-populated values
   - Add custom fields dynamically
   - Define their own categories (NOT use legacy classifications like I, II, III, IV)

### Example Documents

#### Equipment Requirements Form (ST-012 - Weighing Scale)
This form contains fields like:
- Equipment ID (e.g., "ST-012")
- Equipment Name (e.g., "Weighing Scale")
- Manufacturer
- Model Number
- Serial Number
- Department/Location
- Calibration Requirements
- PM Schedule
- Various checkboxes and approvals

**Note:** The form has legacy categorizations (Production, Engineering, Quality, Regulatory) that should be **IGNORED**. Admin will define their own categories in the system.

#### Supplier TCI Form (SAS)
This form contains fields like:
- Supplier Name
- Address
- Contact Information
- Products/Services Provided
- Quality certifications
- Approval dates

**Note:** The form has legacy classifications (I, II, III, IV) that should be **IGNORED**. Admin will define their own status values.

### Implementation Plan

#### Phase 1: PDF Text Extraction Utility

**File:** `app/eqms/modules/equipment/parsers/pdf.py`

```python
"""PDF parsing utilities for equipment documents."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_equipment_fields_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract equipment-related fields from a PDF document.
    
    Returns a dict of field_name -> extracted_value.
    Values are suggestions only - admin can override all of them.
    """
    try:
        import pdfplumber
        from io import BytesIO
        
        extracted = {}
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"
        
        # Common field patterns (case-insensitive)
        patterns = {
            "equip_code": [
                r"(?:Equipment\s*ID|Equip\.?\s*ID|Asset\s*ID)[:\s]*([A-Z]{1,4}-?\d{2,6})",
                r"(?:ID)[:\s]*([A-Z]{1,4}-\d{2,6})",
            ],
            "description": [
                r"(?:Equipment\s*Name|Description|Name)[:\s]*([^\n]{3,100})",
            ],
            "mfg": [
                r"(?:Manufacturer|Mfg|Make)[:\s]*([^\n]{2,100})",
            ],
            "model_no": [
                r"(?:Model\s*(?:No\.?|Number)?|Model)[:\s]*([^\n]{2,50})",
            ],
            "serial_no": [
                r"(?:Serial\s*(?:No\.?|Number)?|S/N)[:\s]*([^\n]{2,50})",
            ],
            "location": [
                r"(?:Location|Department|Dept\.?)[:\s]*([^\n]{2,100})",
            ],
            "cal_interval": [
                r"(?:Calibration\s*(?:Interval|Frequency)|Cal\.?\s*(?:Interval|Freq))[:\s]*(\d+)\s*(?:months?|days?|years?)?",
            ],
            "pm_interval": [
                r"(?:PM\s*(?:Interval|Frequency)|Maintenance\s*(?:Interval|Frequency))[:\s]*(\d+)\s*(?:months?|days?|years?)?",
            ],
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    # Clean up common artifacts
                    value = re.sub(r"\s+", " ", value)
                    if value and len(value) > 1:
                        extracted[field] = value
                        break
        
        logger.info("Extracted equipment fields: %s", list(extracted.keys()))
        return extracted
        
    except Exception as e:
        logger.warning("PDF equipment extraction failed: %s", e)
        return {}


def extract_supplier_fields_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract supplier-related fields from a PDF document.
    
    Returns a dict of field_name -> extracted_value.
    Values are suggestions only - admin can override all of them.
    """
    try:
        import pdfplumber
        from io import BytesIO
        
        extracted = {}
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"
        
        patterns = {
            "name": [
                r"(?:Supplier\s*Name|Company\s*Name|Vendor\s*Name)[:\s]*([^\n]{2,150})",
                r"^([A-Z][A-Za-z\s&,\.]+(?:Inc\.?|LLC|Ltd\.?|Corp\.?))",
            ],
            "address": [
                r"(?:Address)[:\s]*([^\n]{5,200})",
            ],
            "product_service_provided": [
                r"(?:Products?|Services?|Provides?)[:\s]*([^\n]{5,300})",
            ],
            "contact_name": [
                r"(?:Contact|Rep(?:resentative)?)[:\s]*([A-Z][a-z]+\s+[A-Z][a-z]+)",
            ],
            "contact_email": [
                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            ],
            "contact_phone": [
                r"(?:Phone|Tel|Telephone)[:\s]*([\d\-\(\)\s\.]{10,20})",
            ],
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    value = re.sub(r"\s+", " ", value)
                    if value and len(value) > 1:
                        extracted[field] = value
                        break
        
        logger.info("Extracted supplier fields: %s", list(extracted.keys()))
        return extracted
        
    except Exception as e:
        logger.warning("PDF supplier extraction failed: %s", e)
        return {}
```

#### Phase 2: Auto-populate UI on Document Upload

**File:** `app/eqms/modules/equipment/admin.py`

Add a new route that extracts fields from an uploaded PDF and returns them as JSON:

```python
@bp.post("/equipment/<int:equipment_id>/extract-from-pdf")
@require_permission("equipment.upload")
def equipment_extract_from_pdf(equipment_id: int):
    """Extract field values from uploaded PDF and return as JSON for form auto-fill."""
    from app.eqms.modules.equipment.parsers.pdf import extract_equipment_fields_from_pdf
    
    if "pdf_file" not in request.files:
        return {"error": "No file uploaded"}, 400
    
    file = request.files["pdf_file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"error": "File must be a PDF"}, 400
    
    pdf_bytes = file.read()
    extracted = extract_equipment_fields_from_pdf(pdf_bytes)
    
    return {
        "success": True,
        "extracted_fields": extracted,
        "message": f"Extracted {len(extracted)} field(s) from PDF. Review and edit as needed.",
    }
```

Similar route for suppliers:

```python
@bp.post("/suppliers/<int:supplier_id>/extract-from-pdf")
@require_permission("suppliers.upload")
def supplier_extract_from_pdf(supplier_id: int):
    """Extract field values from uploaded PDF and return as JSON for form auto-fill."""
    from app.eqms.modules.equipment.parsers.pdf import extract_supplier_fields_from_pdf
    
    if "pdf_file" not in request.files:
        return {"error": "No file uploaded"}, 400
    
    file = request.files["pdf_file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"error": "File must be a PDF"}, 400
    
    pdf_bytes = file.read()
    extracted = extract_supplier_fields_from_pdf(pdf_bytes)
    
    return {
        "success": True,
        "extracted_fields": extracted,
        "message": f"Extracted {len(extracted)} field(s) from PDF. Review and edit as needed.",
    }
```

#### Phase 3: Dynamic Custom Fields (Foundation)

This is a bigger feature that allows admin to add custom fields. For now, create the foundation:

**File:** `app/eqms/modules/equipment/models.py`

Add a `custom_fields` JSON column to Equipment and Supplier models:

```python
from sqlalchemy.dialects.postgresql import JSONB

class Equipment(Base):
    ...
    # Existing fields
    
    # Custom fields (admin-defined, stored as JSON)
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
```

Similarly for Supplier:

```python
class Supplier(Base):
    ...
    custom_fields: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
```

**Migration:**

```python
def upgrade():
    # Add custom_fields to equipment
    op.add_column("equipment", sa.Column("custom_fields", JSONB, nullable=True))
    
    # Add custom_fields to suppliers
    op.add_column("suppliers", sa.Column("custom_fields", JSONB, nullable=True))
```

#### Phase 4: Admin Custom Field Management (Future)

**Scope for later:** Build a UI where admin can:
1. Define new field names and types
2. Mark fields as required/optional
3. Set field display order
4. Create field groups/categories

For now, the `custom_fields` JSON column allows storing arbitrary key-value pairs that admin can edit via the Equipment/Supplier edit forms.

---

## P2: UI for PDF Upload with Auto-Populate

### Equipment Detail Page Enhancement

**File:** `app/eqms/templates/admin/equipment/detail.html`

Add a "Smart Upload" feature that:
1. Accepts a PDF upload
2. Extracts fields via AJAX
3. Shows extracted values in a preview
4. Lets admin confirm/edit before saving

```html
<!-- Add to equipment detail page -->
<div class="card">
  <h2 style="margin-top:0; font-size:16px;">Upload Document with Auto-Extract</h2>
  <p class="muted" style="font-size:12px;">Upload an Equipment Requirements Form and we'll extract field values automatically.</p>
  
  <form id="smart-upload-form" enctype="multipart/form-data" style="margin-top:12px;">
    <input type="file" id="pdf-upload" name="pdf_file" accept=".pdf" />
    <button type="button" class="button button--secondary" onclick="extractFromPdf()">Extract Fields</button>
  </form>
  
  <div id="extracted-preview" style="display:none; margin-top:16px; padding:16px; background:rgba(255,255,255,0.03); border-radius:8px;">
    <h3 style="margin-top:0; font-size:14px;">Extracted Fields (Review & Edit)</h3>
    <div id="extracted-fields"></div>
    <div style="margin-top:12px;">
      <button class="button" onclick="applyExtracted()">Apply to Form</button>
      <button class="button button--secondary" onclick="cancelExtract()">Cancel</button>
    </div>
  </div>
</div>

<script>
let extractedData = {};

async function extractFromPdf() {
  const fileInput = document.getElementById('pdf-upload');
  if (!fileInput.files[0]) {
    alert('Please select a PDF file first.');
    return;
  }
  
  const formData = new FormData();
  formData.append('pdf_file', fileInput.files[0]);
  
  try {
    const res = await fetch(`/admin/equipment/{{ equipment.id }}/extract-from-pdf`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    
    if (data.error) {
      alert(data.error);
      return;
    }
    
    extractedData = data.extracted_fields;
    showExtractedPreview(extractedData);
  } catch (e) {
    alert('Failed to extract fields from PDF.');
  }
}

function showExtractedPreview(fields) {
  const container = document.getElementById('extracted-fields');
  let html = '<table style="width:100%; border-collapse:collapse;">';
  html += '<tr><th style="text-align:left; padding:8px;">Field</th><th style="text-align:left; padding:8px;">Extracted Value</th></tr>';
  
  for (const [field, value] of Object.entries(fields)) {
    html += `<tr>
      <td style="padding:8px; font-weight:500;">${field}</td>
      <td style="padding:8px;"><input type="text" id="ext-${field}" value="${value}" style="width:100%;" /></td>
    </tr>`;
  }
  
  html += '</table>';
  container.innerHTML = html;
  document.getElementById('extracted-preview').style.display = 'block';
}

function applyExtracted() {
  // Map extracted field names to form input names
  const fieldMap = {
    'equip_code': 'equip_code',
    'description': 'description',
    'mfg': 'mfg',
    'model_no': 'model_no',
    'serial_no': 'serial_no',
    'location': 'location',
    'cal_interval': 'cal_interval',
    'pm_interval': 'pm_interval',
  };
  
  for (const [extField, formField] of Object.entries(fieldMap)) {
    const extInput = document.getElementById(`ext-${extField}`);
    const formInput = document.querySelector(`[name="${formField}"]`);
    if (extInput && formInput) {
      formInput.value = extInput.value;
    }
  }
  
  document.getElementById('extracted-preview').style.display = 'none';
  alert('Fields applied! Review and save when ready.');
}

function cancelExtract() {
  document.getElementById('extracted-preview').style.display = 'none';
  extractedData = {};
}
</script>
```

---

## Important Notes

### Legacy Classifications to IGNORE

The uploaded PDF forms contain legacy classifications that should **NOT** be enforced by the system:

**Equipment Form:**
- Categories: Production, Engineering, Quality, Regulatory
- **Ignore these** - admin will define their own categories

**Supplier Form:**
- Classifications: I, II, III, IV
- **Ignore these** - admin will define their own status values

The system should:
1. Extract the raw text/values from these fields
2. Present them to admin as "suggested" values
3. Let admin accept, modify, or ignore them
4. Admin has full control over what categories/statuses exist in the system

### Admin Full Control

The guiding principle is: **Admin has full editability on all components.**

- Admin can edit any auto-populated value
- Admin can add custom fields (via `custom_fields` JSON)
- Admin can define their own categories/statuses
- Admin can override any system-suggested classification

---

## Implementation Order

1. **P0: Fix Migration (IMMEDIATE)**
   - [ ] Update `h2i3j4k5l6m_create_reps_table.py` with the robust version
   - [ ] Commit and push
   - [ ] Trigger redeploy
   - [ ] Verify migration succeeds

2. **P1: PDF Field Extraction**
   - [ ] Create `app/eqms/modules/equipment/parsers/pdf.py`
   - [ ] Add extraction routes to equipment and supplier admin
   - [ ] Test with the example PDFs

3. **P2: Custom Fields Foundation**
   - [ ] Add `custom_fields` JSONB column via migration
   - [ ] Update edit forms to display/edit custom fields

4. **P3: Smart Upload UI**
   - [ ] Add PDF upload with auto-extract to equipment detail
   - [ ] Add PDF upload with auto-extract to supplier detail
   - [ ] Test end-to-end flow

---

## Verification Checklist

After deployment fix:
- [ ] Deploy logs show successful migration
- [ ] `/admin/reps` page loads
- [ ] Existing customer-rep assignments still work

After PDF parsing:
- [ ] Upload Equipment Requirements Form PDF
- [ ] Fields are extracted and displayed
- [ ] Admin can edit extracted values before applying
- [ ] Admin can save equipment with applied values

After custom fields:
- [ ] Can add arbitrary key-value pairs to equipment
- [ ] Can add arbitrary key-value pairs to suppliers
- [ ] Custom fields persist after save
