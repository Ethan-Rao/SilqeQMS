# Developer Prompt: System Review Fixes and Enhancements
**Date**: January 29, 2026  
**Priority**: HIGH  
**Scope**: Customer Address Population, PDF Storage & Extraction, Legacy Code Cleanup

---

## Executive Summary

This document addresses 13 identified issues from a comprehensive system review, including 3 user-reported critical issues and 10 additional enhancement/cleanup opportunities. The fixes span customer data integrity, PDF document management, and code quality improvements.

---

## CRITICAL ISSUE 1: Customer Address Not Populated from Sales Orders

### Problem
Customers created from PDF-imported Sales Orders have no address information. The `facility_name` is captured from the "Ship To" section, but `address1`, `city`, `state`, and `zip` are not being parsed or stored.

### Root Cause
The PDF parser (`app/eqms/modules/rep_traceability/parsers/pdf.py`) only extracts the first line from the "Ship To" block as `customer_name`. The full address structure is ignored.

**Current code (lines 180-187):**
```python
customer_name = "Unknown Customer"
ship_to_match = re.search(r'Ship\s+To\s*[:\n](.+?)(?=\n\s*\n|Bill\s+To|Shipping\s+Method|$)', text, re.IGNORECASE | re.DOTALL)
if ship_to_match:
    for line in ship_to_match.group(1).strip().split('\n'):
        line = line.strip()
        if line and not re.match(r'^\d+\s+\w', line) and len(line) > 2:
            customer_name = line
            break  # PROBLEM: Only takes first line, ignores address
```

### Business Rule
For any given customer, from the first matched sales order:
- **Customer Name**: First line under "SOLD TO" 
- **Address**: Most recent "SHIP TO" address

### Required Changes

#### 1. Update PDF Parser to Extract Full Ship-To Address
**File**: `app/eqms/modules/rep_traceability/parsers/pdf.py`

Replace the ship_to parsing logic to extract:
- `customer_name` (first non-address line)
- `ship_to_address1` (street address line)
- `ship_to_city`, `ship_to_state`, `ship_to_zip` (from city/state/zip line)

```python
def _parse_ship_to_block(text: str) -> dict[str, str | None]:
    """
    Parse SHIP TO block from SILQ Sales Order PDF.
    
    Expected format:
    SHIP TO:
    Recipient Name
    Company Name (optional)
    123 Street Address
    City, ST 12345
    
    Returns dict with: ship_to_name, ship_to_address1, ship_to_city, ship_to_state, ship_to_zip
    """
    result = {
        "ship_to_name": None,
        "ship_to_address1": None,
        "ship_to_city": None,
        "ship_to_state": None,
        "ship_to_zip": None,
    }
    
    # Match Ship To block
    ship_to_match = re.search(
        r'Ship\s*To\s*[:\n](.+?)(?=\n\s*\n|Bill\s+To|Shipping\s+Method|Salesperson:|F\.?O\.?B\.?|TERMS|$)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if not ship_to_match:
        return result
    
    lines = [l.strip() for l in ship_to_match.group(1).strip().split('\n') if l.strip()]
    
    # First valid line is the name/company
    for i, line in enumerate(lines):
        if line and len(line) > 2 and not re.match(r'^\d+\s', line):
            result["ship_to_name"] = line
            break
    
    # Look for street address (starts with number or contains common street indicators)
    for line in lines:
        if re.match(r'^\d+\s+\w', line) or any(x in line.lower() for x in ['street', 'st.', 'ave', 'blvd', 'road', 'rd.', 'drive', 'dr.', 'lane', 'ln.']):
            result["ship_to_address1"] = line
            break
    
    # Look for city, state zip (pattern: "City, ST 12345" or "City ST 12345")
    city_state_zip_pattern = re.compile(
        r'^([A-Za-z\s\.]+)[,\s]+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)$'
    )
    for line in lines:
        match = city_state_zip_pattern.match(line)
        if match:
            result["ship_to_city"] = match.group(1).strip()
            result["ship_to_state"] = match.group(2)
            result["ship_to_zip"] = match.group(3)
            break
    
    return result


def _parse_sold_to_block(text: str) -> str | None:
    """
    Parse SOLD TO block to get the primary customer/facility name.
    This is the canonical customer name (first line under SOLD TO).
    """
    sold_to_match = re.search(
        r'Sold\s*To\s*[:\n](.+?)(?=\n\s*\n|Ship\s*To|Salesperson:|$)',
        text,
        re.IGNORECASE | re.DOTALL
    )
    if not sold_to_match:
        return None
    
    lines = [l.strip() for l in sold_to_match.group(1).strip().split('\n') if l.strip()]
    for line in lines:
        if line and len(line) > 2 and not re.match(r'^\d+\s', line):
            return line
    
    return None
```

#### 2. Update `_parse_silq_sales_order_page` to Use New Parsers
**File**: `app/eqms/modules/rep_traceability/parsers/pdf.py`

```python
def _parse_silq_sales_order_page(page, text: str, page_num: int) -> dict[str, Any] | None:
    # ... existing order number/date parsing ...
    
    # Parse SOLD TO (canonical customer name)
    customer_name = _parse_sold_to_block(text) or "Unknown Customer"
    
    # Parse SHIP TO (address for customer + shipping details)
    ship_to = _parse_ship_to_block(text)
    
    # ... existing line item parsing ...
    
    return {
        "order_number": order_number,
        "order_date": order_date,
        "ship_date": order_date,
        "customer_name": customer_name,  # From SOLD TO
        # New address fields from SHIP TO
        "ship_to_name": ship_to.get("ship_to_name"),
        "ship_to_address1": ship_to.get("ship_to_address1"),
        "ship_to_city": ship_to.get("ship_to_city"),
        "ship_to_state": ship_to.get("ship_to_state"),
        "ship_to_zip": ship_to.get("ship_to_zip"),
        "lines": items,
    }
```

#### 3. Update PDF Import to Pass Address to Customer Creation
**File**: `app/eqms/modules/rep_traceability/admin.py` (around line 1884)

```python
# Find or create customer WITH ADDRESS DATA
try:
    customer = find_or_create_customer(
        s,
        facility_name=customer_name,
        address1=order_data.get("ship_to_address1"),
        city=order_data.get("ship_to_city"),
        state=order_data.get("ship_to_state"),
        zip=order_data.get("ship_to_zip"),
    )
except Exception as e:
    logger.warning(f"Error creating customer '{customer_name}': {e}")
    continue
```

### Testing
1. Import a Sales Order PDF with full SOLD TO and SHIP TO blocks
2. Verify the customer is created with:
   - `facility_name` from SOLD TO (first line)
   - `address1`, `city`, `state`, `zip` from SHIP TO
3. Import a second order for same customer - verify address is updated if different

---

## CRITICAL ISSUE 2: Equipment PDF Storage and Raw Text Preservation

### Problem
When a user uploads an Equipment Requirements Form PDF for field extraction:
1. The PDF itself is NOT stored in the system
2. The raw text content is NOT preserved for future reference
3. Once equipment is created, there's no document folder associated

### Required Changes

#### 1. Create New Model Column for Raw Extracted Text
**File**: `app/eqms/modules/equipment/models.py`

Add to `ManagedDocument` model:
```python
# Raw text content extracted from PDF (for future reference/search)
extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
```

#### 2. Update Equipment Extraction to Store PDF and Text
**File**: `app/eqms/modules/equipment/admin.py`

Modify `equipment_extract_from_pdf_new` to:
1. Store the uploaded PDF immediately to temp storage
2. Extract and return the raw text along with field values
3. Pass storage reference to the frontend for inclusion in form submission

```python
@bp.post("/equipment/extract-from-pdf")
@require_permission("equipment.create")
def equipment_extract_from_pdf_new():
    """Extract field values from uploaded PDF and prepare for storage."""
    from app.eqms.modules.equipment.parsers.pdf import extract_equipment_fields_from_pdf, _extract_text
    from werkzeug.utils import secure_filename
    import hashlib

    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf_file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    pdf_bytes = file.read()
    
    # Extract text content (for raw storage)
    raw_text = _extract_text(pdf_bytes)
    
    # Extract structured fields
    extracted = extract_equipment_fields_from_pdf(pdf_bytes)
    
    # Store PDF temporarily with hash-based key for retrieval at form submit
    sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    temp_key = f"temp_equipment_pdf/{sha256[:16]}"
    
    from flask import current_app, session
    from app.eqms.storage import storage_from_config
    storage = storage_from_config(current_app.config)
    storage.put_bytes(temp_key, pdf_bytes, content_type="application/pdf")
    
    # Store reference in session for form submission
    session[f"equipment_pdf_{sha256[:16]}"] = {
        "filename": secure_filename(file.filename),
        "storage_key": temp_key,
        "raw_text": raw_text,
        "content_type": "application/pdf",
        "size_bytes": len(pdf_bytes),
    }
    
    return jsonify({
        "success": True,
        "extracted_fields": extracted,
        "pdf_ref": sha256[:16],  # Reference for form submission
        "message": f"Extracted {len(extracted)} field(s) from PDF. Review and edit as needed.",
    })
```

#### 3. Update Equipment Creation to Handle PDF Attachment
**File**: `app/eqms/modules/equipment/admin.py`

In `equipment_new_post`, after creating equipment:
```python
# Handle PDF attachment from extraction
pdf_ref = request.form.get("pdf_ref")
if pdf_ref and f"equipment_pdf_{pdf_ref}" in session:
    pdf_info = session.pop(f"equipment_pdf_{pdf_ref}")
    
    # Move from temp to permanent storage
    from app.eqms.modules.equipment.service import upload_equipment_document
    storage = storage_from_config(current_app.config)
    
    try:
        fobj = storage.open(pdf_info["storage_key"])
        file_bytes = fobj.read()
        
        upload_equipment_document(
            s,
            equipment,
            file_bytes,
            pdf_info["filename"],
            pdf_info["content_type"],
            u,
            description="Equipment Requirements Form (auto-attached from extraction)",
            document_type="Requirements Form",
            extracted_text=pdf_info.get("raw_text"),
        )
        
        # Clean up temp file
        storage.delete(pdf_info["storage_key"])
    except Exception as e:
        logger.warning(f"Failed to attach extracted PDF: {e}")
```

#### 4. Update Frontend to Pass PDF Reference
**File**: `app/eqms/templates/admin/equipment/new.html`

Add hidden input and update extract function:
```html
<!-- Add inside the form -->
<input type="hidden" name="pdf_ref" id="pdf-ref-input" />

<!-- Update JavaScript -->
<script>
async function extractFromPdf() {
    // ... existing code ...
    
    if (data.pdf_ref) {
        document.getElementById('pdf-ref-input').value = data.pdf_ref;
    }
    
    // ... rest of function ...
}
</script>
```

---

## CRITICAL ISSUE 3: Supplier PDF Extraction Improvements

### Problem
1. Supplier text extraction is primitive - contact info goes to Notes instead of dedicated fields
2. The Supplier model lacks `contact_name`, `contact_email`, `contact_phone` columns
3. Same PDF storage issues as Equipment

### Required Changes

#### 1. Add Contact Fields to Supplier Model
**File**: `app/eqms/modules/suppliers/models.py`

```python
class Supplier(Base):
    # ... existing fields ...
    
    # Contact information (NEW)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

#### 2. Create Alembic Migration
```bash
alembic revision -m "add supplier contact fields"
```

Migration content:
```python
def upgrade():
    op.add_column('suppliers', sa.Column('contact_name', sa.String(255), nullable=True))
    op.add_column('suppliers', sa.Column('contact_email', sa.String(255), nullable=True))
    op.add_column('suppliers', sa.Column('contact_phone', sa.String(64), nullable=True))

def downgrade():
    op.drop_column('suppliers', 'contact_phone')
    op.drop_column('suppliers', 'contact_email')
    op.drop_column('suppliers', 'contact_name')
```

#### 3. Improve Supplier PDF Extraction Patterns
**File**: `app/eqms/modules/equipment/parsers/pdf.py`

```python
def extract_supplier_fields_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract supplier-related fields from a Supplier Assessment PDF.
    
    Improved patterns for standard supplier assessment forms.
    """
    full_text = _extract_text(pdf_bytes)
    if not full_text:
        return {}

    extracted: dict[str, Any] = {}

    # Improved patterns for supplier forms
    patterns = {
        "name": [
            r"(?:Supplier|Vendor|Company)\s*Name\s*[:\-]?\s*([^\n]{2,150})",
            r"(?:Legal\s*Name|Business\s*Name)\s*[:\-]?\s*([^\n]{2,150})",
        ],
        "address": [
            r"(?:Business\s*)?Address\s*[:\-]?\s*([^\n]{5,200}(?:\n[^\n]{5,100})?)",
            r"(?:Street|Location)\s*[:\-]?\s*([^\n]{5,200})",
        ],
        "contact_name": [
            r"(?:Contact\s*(?:Person|Name)|Primary\s*Contact|Rep(?:resentative)?)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:Attn|Attention)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        ],
        "contact_email": [
            r"(?:E[-\s]?mail|Email\s*Address)\s*[:\-]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",  # Fallback: any email
        ],
        "contact_phone": [
            r"(?:Phone|Tel(?:ephone)?|Fax)\s*[:\-]?\s*([\d\-\(\)\s\.]{10,20})",
            r"(?:Cell|Mobile)\s*[:\-]?\s*([\d\-\(\)\s\.]{10,20})",
        ],
        "product_service_provided": [
            r"(?:Products?\s*(?:/|and)?\s*Services?|Provides?|Supplies?)\s*[:\-]?\s*([^\n]{5,300})",
            r"(?:Description\s*of\s*(?:Products?|Services?))\s*[:\-]?\s*([^\n]{5,300})",
        ],
        "category": [
            r"(?:Supplier\s*)?(?:Type|Category|Classification)\s*[:\-]?\s*([^\n]{2,100})",
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
```

#### 4. Update Supplier Form Templates

**File**: `app/eqms/templates/admin/suppliers/new.html`

Add contact fields to the form:
```html
<div>
  <div class="label">Contact Name</div>
  <input name="contact_name" placeholder="Primary contact person" />
</div>
<div>
  <div class="label">Contact Email</div>
  <input type="email" name="contact_email" placeholder="contact@example.com" />
</div>
<div>
  <div class="label">Contact Phone</div>
  <input name="contact_phone" placeholder="(555) 123-4567" />
</div>
```

Update the JavaScript `fieldMap`:
```javascript
const fieldMap = {
    'name': 'name',
    'address': 'address',
    'product_service_provided': 'product_service_provided',
    'contact_name': 'contact_name',
    'contact_email': 'contact_email',
    'contact_phone': 'contact_phone',
    'category': 'category',
};
```

#### 5. Update Supplier Service
**File**: `app/eqms/modules/suppliers/service.py`

Add contact fields to `create_supplier` and `update_supplier`:
```python
def create_supplier(s, payload: dict[str, Any], user: User) -> Supplier:
    supplier = Supplier(
        name=payload.get("name"),
        # ... existing fields ...
        contact_name=payload.get("contact_name"),
        contact_email=payload.get("contact_email"),
        contact_phone=payload.get("contact_phone"),
        # ...
    )
```

---

## ISSUE 4: Remove Custom Fields (JSON) from UI

### Problem
The "Custom Fields (JSON)" textarea should be removed from Equipment and Supplier forms per user request.

### Required Changes

Remove the Custom Fields section from:
- `app/eqms/templates/admin/equipment/new.html` (lines 86-90)
- `app/eqms/templates/admin/equipment/edit.html` (same section)
- `app/eqms/templates/admin/suppliers/new.html` (lines 57-61)
- `app/eqms/templates/admin/suppliers/edit.html` (lines 47-51)

Remove this block from each file:
```html
<!-- DELETE THIS SECTION -->
<div style="grid-column: 1 / -1;">
  <div class="label">Custom Fields (JSON)</div>
  <textarea name="custom_fields" rows="3" placeholder='{"key":"value"}'></textarea>
  <small class="muted">Optional key/value pairs. JSON object only.</small>
</div>
```

**Note**: Keep the `custom_fields` column in the model and backend - just remove from UI. This preserves data integrity for any existing records and allows future admin tooling.

---

## ISSUE 5: Consolidate Duplicate PDF Extraction Endpoints

### Problem
Both Equipment and Supplier modules have two nearly identical extraction endpoints:
- `equipment_extract_from_pdf_new()` and `equipment_extract_from_pdf()`
- `supplier_extract_from_pdf_new()` and `supplier_extract_from_pdf()`

### Required Changes

Consolidate to single endpoints. The "for new" vs "for existing" distinction is unnecessary since both do the same thing.

**File**: `app/eqms/modules/equipment/admin.py`

Delete `equipment_extract_from_pdf` (lines 323-344) and keep only `equipment_extract_from_pdf_new` renamed to `equipment_extract_from_pdf`.

**File**: `app/eqms/modules/suppliers/admin.py`

Delete `supplier_extract_from_pdf` (lines 294-315) and keep only `supplier_extract_from_pdf_new` renamed to `supplier_extract_from_pdf`.

Update all frontend fetch URLs to use the consolidated endpoints.

---

## ISSUE 6: ManagedDocument Model Redundancy

### Problem
`ManagedDocument` has both polymorphic fields (`entity_type`, `entity_id`) AND explicit FK fields (`equipment_id`, `supplier_id`). This is redundant.

### Recommendation
Keep both for now but ensure consistency:
1. When `entity_type="equipment"`, ensure `equipment_id=entity_id` and `supplier_id=None`
2. When `entity_type="supplier"`, ensure `supplier_id=entity_id` and `equipment_id=None`

Add validation in service layer:
```python
def _validate_managed_document(doc: ManagedDocument):
    if doc.entity_type == "equipment":
        assert doc.equipment_id == doc.entity_id
        assert doc.supplier_id is None
    elif doc.entity_type == "supplier":
        assert doc.supplier_id == doc.entity_id
        assert doc.equipment_id is None
```

---

## ISSUE 7: `customer_name` Field Deprecation Path

### Problem
`DistributionLogEntry.customer_name` is redundant with `DistributionLogEntry.customer_id` → `Customer.facility_name`.

### Recommendation
1. Keep `customer_name` for backward compatibility
2. Always populate from `Customer.facility_name` when `customer_id` is set
3. Mark as deprecated in model docstring
4. Future: migrate to use only `customer_id` relationship

---

## ISSUE 8: Document Control Module Status

### Current State
The `document_control` module exists but appears to be a basic placeholder. It provides:
- Document creation with revision tracking
- File upload per revision
- Release workflow with audit trail

### Recommendation
This module is functional for basic document control. Keep as-is unless user requests enhancements. It follows proper QMS patterns (draft → release → obsolete).

---

## ISSUE 9: Admin Index Page - Add Field Editing Card Placeholder

### User Request
Add a placeholder card on admin page for future "field editing" functionality.

**File**: `app/eqms/templates/admin/index.html`

Add after existing admin cards:
```html
<div class="card" style="opacity: 0.6;">
  <h3>Field Configuration</h3>
  <p class="muted">Configure custom fields for Equipment and Suppliers.</p>
  <p class="muted"><em>Coming soon</em></p>
</div>
```

---

## ISSUE 10: Equipment Parser - Operating Range Removal

### User Request
Do not extract or display "Operating Range" from Equipment Requirements Forms.

### Required Changes
**File**: `app/eqms/modules/equipment/parsers/pdf.py`

Ensure no "operating_range" pattern exists in `extract_equipment_fields_from_pdf`. Current code does not extract this, so no changes needed. Verified.

---

## ISSUE 11: Equipment Description Auto-Fill Improvement

### Problem
Based on the sample PDF, the equipment description is being filled with generic text instead of the actual equipment name.

### Current Pattern (line 51-52):
```python
"description": [
    r"(?:Equipment\s*Name|Description|Name)[:\s]*([^\n]{3,100})",
],
```

### Improved Pattern
```python
"description": [
    # SILQ Equipment Requirements Form format
    r"(?:Equipment\s*Type|Equipment\s*Name)[:\s]*([^\n]{3,100})",
    r"(?:Description)[:\s]*([^\n]{3,100})",
    # Fallback: line after "Weighing Scale" or similar equipment type
    r"(Weighing\s+Scale|Balance|Thermometer|Timer|Incubator)[^\n]*",
],
```

---

## ISSUE 12: Add `_parse_custom_fields` to Shared Module

### Problem
The `_parse_custom_fields` function is duplicated in both:
- `app/eqms/modules/equipment/admin.py`
- `app/eqms/modules/suppliers/admin.py`

### Required Changes
Move to shared utility:

**File**: `app/eqms/utils.py` (create if doesn't exist)
```python
import json

def parse_custom_fields(raw: str | None) -> tuple[dict | None, str | None]:
    """Parse JSON custom fields from form input."""
    if not raw or not raw.strip():
        return None, None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as e:
        return None, f"Custom fields JSON is invalid: {e}"
    if not isinstance(value, dict):
        return None, "Custom fields must be a JSON object."
    return value, None
```

Import from both admin modules:
```python
from app.eqms.utils import parse_custom_fields
```

---

## ISSUE 13: Supplies Module Missing

### User Context
User mentioned "Supplies" alongside Equipment and Suppliers for PDF storage. There is no `supplies` module currently.

### Recommendation
If a Supplies module is needed, it should be created following the same patterns as Equipment:
- `app/eqms/modules/supplies/models.py`
- `app/eqms/modules/supplies/admin.py`
- `app/eqms/modules/supplies/service.py`

Clarify with user whether this is needed or if they meant Equipment/Supplies as combined terminology.

---

## Implementation Order

### Phase 1: Critical Data Fixes (Immediate)
1. ISSUE 1: Customer address parsing from Sales Orders
2. ISSUE 3: Supplier contact fields and improved extraction
3. Database migration for new Supplier fields

### Phase 2: PDF Storage Infrastructure (High Priority)
4. ISSUE 2: Equipment PDF storage and raw text preservation
5. Apply same PDF storage pattern to Suppliers

### Phase 3: UI Cleanup (Medium Priority)
6. ISSUE 4: Remove Custom Fields JSON from UI
7. ISSUE 9: Add Field Editing placeholder card
8. ISSUE 5: Consolidate duplicate extraction endpoints

### Phase 4: Code Quality (Lower Priority)
9. ISSUE 12: Extract shared utilities
10. ISSUE 6: ManagedDocument validation
11. ISSUE 7: Document customer_name deprecation

---

## Testing Checklist

### Customer Address Testing
- [ ] Import Sales Order PDF with full SOLD TO / SHIP TO blocks
- [ ] Verify customer has address1, city, state, zip populated
- [ ] Import second order for same customer - verify address updates

### Equipment PDF Testing
- [ ] Upload Equipment Requirements Form PDF
- [ ] Verify PDF is stored after equipment creation
- [ ] Verify raw text is stored in document record
- [ ] Verify document appears in equipment detail page

### Supplier Testing
- [ ] Create migration and run it
- [ ] Upload Supplier Assessment PDF
- [ ] Verify contact_name, contact_email, contact_phone extracted
- [ ] Verify fields populate in form
- [ ] Verify PDF stored after supplier creation

### UI Testing
- [ ] Verify Custom Fields JSON removed from new/edit forms
- [ ] Verify Field Configuration card appears on admin page

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `app/eqms/modules/rep_traceability/parsers/pdf.py` | Add `_parse_ship_to_block`, `_parse_sold_to_block`, update `_parse_silq_sales_order_page` |
| `app/eqms/modules/rep_traceability/admin.py` | Pass address fields to `find_or_create_customer` |
| `app/eqms/modules/suppliers/models.py` | Add `contact_name`, `contact_email`, `contact_phone` |
| `app/eqms/modules/equipment/models.py` | Add `extracted_text` to `ManagedDocument` |
| `app/eqms/modules/equipment/admin.py` | Update extraction to store PDF, consolidate endpoints |
| `app/eqms/modules/equipment/parsers/pdf.py` | Improve supplier extraction patterns |
| `app/eqms/modules/suppliers/admin.py` | Add contact fields handling, consolidate endpoints |
| `app/eqms/modules/suppliers/service.py` | Add contact fields to create/update |
| `app/eqms/templates/admin/equipment/new.html` | Remove Custom Fields, add pdf_ref hidden input |
| `app/eqms/templates/admin/equipment/edit.html` | Remove Custom Fields |
| `app/eqms/templates/admin/suppliers/new.html` | Remove Custom Fields, add contact fields |
| `app/eqms/templates/admin/suppliers/edit.html` | Remove Custom Fields, add contact fields |
| `app/eqms/templates/admin/index.html` | Add Field Configuration placeholder |
| `migrations/versions/xxxx_add_supplier_contacts.py` | New migration |
| `app/eqms/utils.py` | New shared utilities file |
