# Developer Prompt: System Enhancements Phase 2
**Date**: January 29, 2026  
**Priority**: HIGH  
**Scope**: Admin UI, Lot Tracking, PDF Naming, UI Consistency, Customer Data Population

---

## Executive Summary

This document addresses user-reported enhancements and 10 additional identified improvements. The focus areas are: admin panel redesign, enhanced lot tracking with manufacturing year filtering, equipment PDF naming conventions, supplier UI consistency, and customer address auto-population from sales orders.

---

## USER REQUEST 1: Admin Panel Redesign

### Requirements
1. **Remove** the "Field Configuration" card (with "Coming soon" text)
2. **Remove** the System Status bar completely
3. **Replace** Field Configuration with a new "Admin Tools" card
4. **Make** the admin panel larger (take up more screen space)

### Implementation

**File**: `app/eqms/templates/admin/index.html`

Replace the entire file with:

```html
{% extends "_layout.html" %}
{% block title %}Admin{% endblock %}
{% block content %}
  <div class="card" style="max-width: 1400px; margin: 0 auto;">
    <h1>Admin</h1>
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
      {% if has_perm("docs.view") %}
        <a class="card card--link" href="{{ url_for('doc_control.list_documents') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Document Control & QMS</h2>
        </a>
      {% endif %}
      {% if has_perm("distribution_log.view") %}
        <a class="card card--link" href="{{ url_for('rep_traceability.distribution_log_list') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Distribution Log</h2>
        </a>
      {% endif %}
      {% if has_perm("tracing_reports.view") %}
        <a class="card card--link" href="{{ url_for('rep_traceability.tracing_list') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Tracing Reports</h2>
        </a>
      {% endif %}
      {% if has_perm("customers.view") %}
        <a class="card card--link" href="{{ url_for('customer_profiles.customers_list') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Customers</h2>
        </a>
      {% endif %}
      {% if has_perm("sales_dashboard.view") %}
        <a class="card card--link" href="{{ url_for('rep_traceability.sales_dashboard') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Sales Dashboard</h2>
        </a>
      {% endif %}
      {% if has_perm("sales_orders.view") %}
        <a class="card card--link" href="{{ url_for('rep_traceability.sales_orders_list') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Sales Orders</h2>
        </a>
      {% endif %}
      {% if has_perm("equipment.view") %}
        <a class="card card--link" href="{{ url_for('equipment.equipment_list') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Equipment & Supplies</h2>
        </a>
      {% endif %}
      {% if has_perm("manufacturing.view") %}
        <a class="card card--link" href="{{ url_for('manufacturing.manufacturing_index') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Manufacturing</h2>
        </a>
      {% endif %}
      {% if has_perm("suppliers.view") %}
        <a class="card card--link" href="{{ url_for('suppliers.suppliers_list') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Suppliers</h2>
        </a>
      {% endif %}
      {% if has_perm("admin.view") %}
        <a class="card card--link" href="{{ url_for('admin.diagnostics') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
          <h2 style="margin: 0;">Admin Tools</h2>
        </a>
      {% endif %}
      <a class="card card--link" href="{{ url_for('admin.me') }}" style="min-height: 100px; display: flex; align-items: center; justify-content: center;">
        <h2 style="margin: 0;">My Account</h2>
      </a>
    </div>
  </div>
{% endblock %}
```

**Key Changes**:
- Removed Field Configuration card entirely
- Removed System Status bar entirely
- Added new "Admin Tools" card linking to diagnostics
- Increased card min-width from implicit to 280px
- Added `min-height: 100px` to cards for consistent sizing
- Added `max-width: 1400px` to container for larger panel
- Centered card content with flexbox

---

## USER REQUEST 2: Enhanced Lot Tracking by SKU

### Requirements
- Show **all lots manufactured since 2025** (per LotLog manufacturing date)
- Keep one SKU per row (current behavior)
- Show **total distributed** and **total remaining** for each SKU
- **Only include lots manufactured since 2025** - exclude lots manufactured prior to 2025 even if distributed in 2025

### Implementation

**File**: `app/eqms/modules/rep_traceability/service.py`

Update the lot tracking section in `compute_sales_dashboard()` (around line 809):

```python
# Lot tracking - aggregate all lots manufactured since 2025
from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory, normalize_lot, VALID_SKUS
lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv").strip()
lot_to_sku, lot_corrections, lot_inventory, lot_years = load_lot_log_with_inventory(lotlog_path)
min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2025"))

# Filter to only lots manufactured since min_year
lots_since_min_year = {
    lot: inventory 
    for lot, inventory in lot_inventory.items() 
    if lot_years.get(lot, 0) >= min_year
}

# Aggregate total produced per SKU (from lots manufactured since min_year only)
sku_total_produced: dict[str, int] = {}
sku_lots: dict[str, list[str]] = {}  # Track which lots belong to each SKU
for lot, inventory in lots_since_min_year.items():
    sku = lot_to_sku.get(lot)
    if sku and sku in VALID_SKUS:
        sku_total_produced[sku] = sku_total_produced.get(sku, 0) + inventory
        if sku not in sku_lots:
            sku_lots[sku] = []
        sku_lots[sku].append(lot)

# Aggregate total distributed per SKU (from lots manufactured since min_year only)
sku_total_distributed: dict[str, int] = {}
sku_latest_lot: dict[str, str] = {}
sku_last_date: dict[str, date] = {}

# Query all distribution lines with lots - ONLY MATCHED DISTRIBUTIONS
all_lines = (
    s.query(DistributionLine, DistributionLogEntry)
    .join(DistributionLogEntry, DistributionLogEntry.id == DistributionLine.distribution_entry_id)
    .filter(
        DistributionLogEntry.sales_order_id.isnot(None),
        DistributionLine.lot_number.isnot(None),
    )
    .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
    .all()
)

for line, entry in all_lines:
    raw_lot = (line.lot_number or "").strip()
    if not raw_lot:
        continue

    # Apply correction from LotLog
    normalized_lot = normalize_lot(raw_lot)
    corrected_lot = lot_corrections.get(normalized_lot, normalized_lot)

    # Skip if lot was not manufactured since min_year
    lot_year = lot_years.get(corrected_lot)
    if lot_year is None or lot_year < min_year:
        continue

    # Get SKU for this lot from LotLog
    sku = lot_to_sku.get(corrected_lot) or lot_to_sku.get(normalized_lot) or line.sku
    if not sku or sku not in VALID_SKUS:
        continue

    # Aggregate distributed units
    sku_total_distributed[sku] = sku_total_distributed.get(sku, 0) + int(line.quantity or 0)

    # Track most recent lot per SKU
    if sku not in sku_latest_lot or (entry.ship_date and entry.ship_date > sku_last_date.get(sku, date.min)):
        sku_latest_lot[sku] = corrected_lot
        sku_last_date[sku] = entry.ship_date

# Also check entry-level fallbacks for entries without DistributionLines
if line_entry_ids_all:
    entry_fallbacks = (
        s.query(DistributionLogEntry)
        .filter(
            DistributionLogEntry.sales_order_id.isnot(None),
            DistributionLogEntry.lot_number.isnot(None),
            ~DistributionLogEntry.id.in_(line_entry_ids_all),
        )
        .order_by(DistributionLogEntry.ship_date.desc(), DistributionLogEntry.id.desc())
        .all()
    )
    for e in entry_fallbacks:
        raw_lot = (e.lot_number or "").strip()
        if not raw_lot:
            continue
        normalized_lot = normalize_lot(raw_lot)
        corrected_lot = lot_corrections.get(normalized_lot, normalized_lot)
        
        lot_year = lot_years.get(corrected_lot)
        if lot_year is None or lot_year < min_year:
            continue
            
        sku = lot_to_sku.get(corrected_lot) or lot_to_sku.get(normalized_lot) or e.sku
        if not sku or sku not in VALID_SKUS:
            continue

        sku_total_distributed[sku] = sku_total_distributed.get(sku, 0) + int(e.quantity or 0)
        
        if sku not in sku_latest_lot or (e.ship_date and e.ship_date > sku_last_date.get(sku, date.min)):
            sku_latest_lot[sku] = corrected_lot
            sku_last_date[sku] = e.ship_date

# Build final lot_tracking list - ONE ROW PER SKU with totals
lot_tracking = []
for sku in VALID_SKUS:
    total_produced = sku_total_produced.get(sku, 0)
    total_distributed = sku_total_distributed.get(sku, 0)
    current_lot = sku_latest_lot.get(sku, "—")
    last_date = sku_last_date.get(sku)
    remaining = total_produced - total_distributed if total_produced > 0 else None
    
    lot_tracking.append({
        "sku": sku,
        "lot": current_lot,  # Most recently distributed lot
        "total_produced": total_produced,
        "total_distributed": total_distributed,
        "remaining": remaining,
        "last_date": last_date,
    })

lot_tracking = sorted(lot_tracking, key=lambda x: x["sku"], reverse=True)
```

**File**: `app/eqms/templates/admin/sales_dashboard/index.html`

Update the lot tracking table (around line 168):

```html
<!-- Lot Tracking -->
<div class="card">
  <h2 style="margin-top:0; font-size:16px;">Inventory by SKU (Lots Manufactured Since {{ lot_min_year }})</h2>
  {% if lot_tracking %}
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">SKU</th>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Current Lot</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Total Produced</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Total Distributed</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Remaining</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Last Ship</th>
          </tr>
        </thead>
        <tbody>
          {% for row in lot_tracking %}
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
              <td style="padding:10px 12px;"><code style="background:rgba(255,255,255,0.05); padding:2px 6px; border-radius:4px;">{{ row.sku|e }}</code></td>
              <td style="padding:10px 12px;"><code style="background:rgba(102,163,255,0.1); padding:2px 6px; border-radius:4px; color:var(--primary);">{{ row.lot|e }}</code></td>
              <td style="padding:10px 12px; text-align:right; font-weight:600;">{{ row.total_produced }}</td>
              <td style="padding:10px 12px; text-align:right; font-weight:600;">{{ row.total_distributed }}</td>
              <td style="padding:10px 12px; text-align:right; font-weight:600;">
                {% if row.remaining is not none %}
                  {% if row.remaining < 0 %}
                    <span style="color:var(--danger);">{{ row.remaining }}</span>
                  {% elif row.remaining < 50 %}
                    <span style="color:#f59e0b;">{{ row.remaining }}</span>
                  {% else %}
                    {{ row.remaining }}
                  {% endif %}
                {% else %}
                  <span class="muted">N/A</span>
                {% endif %}
              </td>
              <td style="padding:10px 12px; text-align:right; font-size:12px; color:var(--muted);">{{ row.last_date or "—" }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% else %}
    <p class="muted">No lot data available.</p>
  {% endif %}
</div>
```

---

## USER REQUEST 3: Equipment PDF Naming Convention

### Requirements
- Equipment codes always start with `ST-`
- Description is extracted from filename: text between code and `.pdf`
- Example: `ST-012 - Weighing Scale.pdf` → code=`ST-012`, description=`Weighing Scale`

### Implementation

**File**: `app/eqms/modules/equipment/parsers/pdf.py`

Add a new function to parse equipment info from filename:

```python
def extract_equipment_from_filename(filename: str) -> dict[str, str]:
    """
    Extract equipment code and description from standardized PDF filename.
    
    Expected format: "ST-XXX - Description.pdf" or "ST-XXX_Description.pdf"
    Examples:
        "ST-012 - Weighing Scale.pdf" → {"equip_code": "ST-012", "description": "Weighing Scale"}
        "ST-001_Digital Thermometer.pdf" → {"equip_code": "ST-001", "description": "Digital Thermometer"}
    """
    import re
    
    result = {}
    
    # Remove .pdf extension (case insensitive)
    name = re.sub(r'\.pdf$', '', filename, flags=re.IGNORECASE).strip()
    
    # Pattern: ST-XXX followed by separator (-, _, or space) and description
    pattern = r'^(ST-\d{2,4})\s*[-_]\s*(.+)$'
    match = re.match(pattern, name, re.IGNORECASE)
    
    if match:
        result["equip_code"] = match.group(1).upper()
        result["description"] = match.group(2).strip()
    elif name.upper().startswith("ST-"):
        # Fallback: just extract the code if no description separator
        code_match = re.match(r'^(ST-\d{2,4})', name, re.IGNORECASE)
        if code_match:
            result["equip_code"] = code_match.group(1).upper()
    
    return result
```

Update `extract_equipment_fields_from_pdf`:

```python
def extract_equipment_fields_from_pdf(pdf_bytes: bytes, filename: str = "") -> dict[str, Any]:
    """
    Extract equipment-related fields from a PDF document.
    
    First tries to extract from filename (standardized naming convention),
    then falls back to PDF text extraction.
    """
    extracted: dict[str, Any] = {}
    
    # Try filename extraction first (ST-XXX - Description.pdf convention)
    if filename:
        filename_fields = extract_equipment_from_filename(filename)
        extracted.update(filename_fields)
    
    # Then extract from PDF text for additional fields
    full_text = _extract_text(pdf_bytes)
    if not full_text:
        return extracted

    patterns = {
        "equip_code": [
            r"(?:Equipment\s*ID|Equip\.?\s*ID|Asset\s*ID)[:\s]*([A-Z]{1,4}-?\d{2,6})",
            r"(?:ID)[:\s]*([A-Z]{1,4}-\d{2,6})",
        ],
        "description": [
            r"(?:Equipment\s*Type|Equipment\s*Name)[:\s]*([^\n]{3,100})",
            r"(?:Description)[:\s]*([^\n]{3,100})",
        ],
        "mfg": [
            r"(?:Manufacturer|Mfg|Make)[:\s]*([^\n]{2,100})",
        ],
        "model_no": [
            r"(?:Model\s*(?:No\.?|Number|#)?)[:\s]*([^\n]{2,50})",
        ],
        "serial_no": [
            r"(?:Serial\s*(?:No\.?|Number|#)?|S/N)[:\s]*([^\n]{2,50})",
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
        # Don't overwrite filename-extracted values
        if field in extracted:
            continue
        for pattern in field_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                value = re.sub(r"\s+", " ", value)
                if value and len(value) > 1:
                    extracted[field] = value
                    break

    logger.info("Extracted equipment fields: %s", list(extracted.keys()))
    return extracted
```

**File**: `app/eqms/modules/equipment/admin.py`

Update the extraction endpoint to pass filename:

```python
@bp.post("/equipment/extract-from-pdf")
@require_permission("equipment.create")
def equipment_extract_from_pdf_new():
    """Extract field values from uploaded PDF for new equipment forms."""
    from app.eqms.modules.equipment.parsers.pdf import extract_equipment_fields_from_pdf

    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["pdf_file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "File must be a PDF"}), 400

    pdf_bytes = file.read()
    # Pass filename for convention-based extraction
    extracted = extract_equipment_fields_from_pdf(pdf_bytes, filename=file.filename)
    return jsonify(
        {
            "success": True,
            "extracted_fields": extracted,
            "message": f"Extracted {len(extracted)} field(s) from PDF. Review and edit as needed.",
        }
    )
```

---

## USER REQUEST 4: Supplier UI Consistency

### Requirements
- Supplier Address and Products/Services fields should look like Customer profile fields
- Use consistent styling with definition list (`<dl>`) layout

### Implementation

**File**: `app/eqms/templates/admin/suppliers/detail.html`

Replace the Metadata table (lines 15-37) with:

```html
<div class="grid" style="grid-template-columns: 1fr 1fr; gap: 14px;">
  <!-- Supplier Info -->
  <div class="card">
    <h3 style="margin-top:0; font-size:16px;">Supplier Information</h3>
    <div class="dl" style="font-size:14px;">
      <dt>Name</dt>
      <dd>{{ supplier.name|e }}</dd>
      
      <dt>Status</dt>
      <dd>
        <span class="badge {% if supplier.status == 'Approved' %}badge--success{% elif supplier.status == 'Pending' %}badge--warning{% elif supplier.status == 'Conditional' %}badge--info{% else %}badge--danger{% endif %}">
          {{ supplier.status|e }}
        </span>
      </dd>
      
      <dt>Category</dt>
      <dd>{{ (supplier.category or "—")|e }}</dd>
      
      <dt>Initial Listing Date</dt>
      <dd>{{ supplier.initial_listing_date or "—" }}</dd>
      
      <dt>Certification Expiration</dt>
      <dd {% if supplier.certification_expiration and supplier.certification_expiration < today %}style="color: var(--danger); font-weight:600;"{% endif %}>
        {{ supplier.certification_expiration or "—" }}
        {% if supplier.certification_expiration and supplier.certification_expiration < today %}(EXPIRED){% endif %}
      </dd>
    </div>
  </div>

  <!-- Contact & Address -->
  <div class="card">
    <h3 style="margin-top:0; font-size:16px;">Contact & Location</h3>
    <div class="dl" style="font-size:14px;">
      {% if supplier.address %}
        <dt>Address</dt>
        <dd style="white-space: pre-line;">{{ supplier.address|e }}</dd>
      {% endif %}
      {% if supplier.contact_name %}
        <dt>Contact</dt>
        <dd>{{ supplier.contact_name|e }}</dd>
      {% endif %}
      {% if supplier.contact_phone %}
        <dt>Phone</dt>
        <dd>{{ supplier.contact_phone|e }}</dd>
      {% endif %}
      {% if supplier.contact_email %}
        <dt>Email</dt>
        <dd>{{ supplier.contact_email|e }}</dd>
      {% endif %}
    </div>
    {% if not supplier.address and not supplier.contact_name %}
      <p class="muted">No contact information on file.</p>
    {% endif %}
  </div>
</div>

<div style="height: 14px;"></div>

<div class="card">
  <h3 style="margin-top:0; font-size:16px;">Products & Services</h3>
  {% if supplier.product_service_provided %}
    <p style="margin:0; white-space: pre-line;">{{ supplier.product_service_provided|e }}</p>
  {% else %}
    <p class="muted">No products/services listed.</p>
  {% endif %}
</div>

{% if supplier.notes %}
<div style="height: 14px;"></div>
<div class="card">
  <h3 style="margin-top:0; font-size:16px;">Notes</h3>
  <p style="margin:0; white-space: pre-line;">{{ supplier.notes|e }}</p>
</div>
{% endif %}

<div style="height: 14px;"></div>
<div class="card" style="padding:10px 16px;">
  <div class="muted" style="font-size:12px;">
    Created: {{ supplier.created_at.strftime('%Y-%m-%d %H:%M') }} · 
    Updated: {{ supplier.updated_at.strftime('%Y-%m-%d %H:%M') }}
  </div>
</div>
```

---

## USER REQUEST 5: Customer Address Auto-Population from Sales Orders

### Problem
Customer profiles appear empty because address fields are not being populated from PDF-imported Sales Orders. Only manually uploaded customers have address data.

### Root Cause
The PDF parser extracts only `customer_name` from the Ship To block, not the full address. The `find_or_create_customer` call in the PDF import doesn't receive address parameters.

### Solution
This was addressed in the previous developer prompt (`DEVELOPER_PROMPT_2026_01_29_SYSTEM_REVIEW_FIXES.md`). Ensure those changes are implemented:

1. **PDF Parser** (`app/eqms/modules/rep_traceability/parsers/pdf.py`):
   - Add `_parse_ship_to_block()` to extract full address
   - Add `_parse_sold_to_block()` to get customer name
   - Return `ship_to_address1`, `ship_to_city`, `ship_to_state`, `ship_to_zip`

2. **PDF Import** (`app/eqms/modules/rep_traceability/admin.py`):
   - Pass address fields to `find_or_create_customer()`

### Additional: Backfill Existing Customers

Create a one-time backfill script to populate addresses for existing customers from their first sales order:

**File**: `scripts/backfill_customer_addresses.py`

```python
"""
One-time script to backfill customer addresses from their first matched Sales Order PDF.

Run: python scripts/backfill_customer_addresses.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.eqms.db import db_session
from app.eqms.modules.customer_profiles.models import Customer
from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment

def backfill_addresses():
    app = create_app()
    with app.app_context():
        s = db_session()
        
        # Find customers with no address
        customers_without_address = (
            s.query(Customer)
            .filter(Customer.address1.is_(None) | (Customer.address1 == ""))
            .all()
        )
        
        print(f"Found {len(customers_without_address)} customers without addresses")
        
        updated = 0
        for customer in customers_without_address:
            # Find their first sales order
            first_order = (
                s.query(SalesOrder)
                .filter(SalesOrder.customer_id == customer.id)
                .order_by(SalesOrder.order_date.asc())
                .first()
            )
            
            if not first_order:
                continue
            
            # Find PDF attachment for this order
            attachment = (
                s.query(OrderPdfAttachment)
                .filter(OrderPdfAttachment.sales_order_id == first_order.id)
                .filter(OrderPdfAttachment.pdf_type == "sales_order_page")
                .first()
            )
            
            if not attachment:
                continue
            
            # Extract address from PDF
            from app.eqms.storage import storage_from_config
            from flask import current_app
            from app.eqms.modules.rep_traceability.parsers.pdf import _parse_ship_to_block, _extract_text
            
            try:
                storage = storage_from_config(current_app.config)
                pdf_bytes = storage.get_bytes(attachment.storage_key)
                text = _extract_text(pdf_bytes)
                ship_to = _parse_ship_to_block(text)
                
                if ship_to.get("ship_to_address1"):
                    customer.address1 = ship_to["ship_to_address1"]
                    customer.city = ship_to.get("ship_to_city")
                    customer.state = ship_to.get("ship_to_state")
                    customer.zip = ship_to.get("ship_to_zip")
                    updated += 1
                    print(f"Updated: {customer.facility_name} with address from SO#{first_order.order_number}")
            except Exception as e:
                print(f"Error processing {customer.facility_name}: {e}")
                continue
        
        s.commit()
        print(f"\nBackfill complete: {updated} customers updated")

if __name__ == "__main__":
    backfill_addresses()
```

---

## ADDITIONAL ISSUE 1: Notes Modal Not Implemented in Sales Dashboard

### Problem
The Sales Dashboard has `openNotesModal()` JavaScript calls but the modal/script is not included in the template.

### Solution
Add the notes modal include to `sales_dashboard/index.html`:

```html
{% include "admin/_notes_modal_content.html" %}
```

Or implement the modal inline if the include doesn't exist.

---

## ADDITIONAL ISSUE 2: Supplier Model Missing Contact Fields

### Problem
The Supplier model doesn't have dedicated `contact_name`, `contact_email`, `contact_phone` columns - these need to be added via migration.

### Solution
Already covered in previous prompt. Ensure migration is created and run:

```bash
alembic revision -m "add supplier contact fields"
alembic upgrade head
```

---

## ADDITIONAL ISSUE 3: `load_lot_log_with_inventory` Returns Wrong Tuple

### Problem
The function signature returns `tuple[..., dict[str, int], dict[str, int]]` but line 182 has:
```python
return {}, {}, {}  # Missing fourth element
```

### Solution
**File**: `app/eqms/modules/shipstation_sync/parsers.py` (line 182)

Change:
```python
return {}, {}, {}
```
To:
```python
return {}, {}, {}, {}
```

---

## ADDITIONAL ISSUE 4: Duplicate Admin Routes

### Problem
The admin index route may be defined in multiple places, leading to confusion.

### Recommendation
Consolidate all admin routes in `app/eqms/admin.py` and remove any duplicates.

---

## ADDITIONAL ISSUE 5: Missing `extracted_text` Column on ManagedDocument

### Problem
Previous prompt suggested adding `extracted_text` to ManagedDocument but migration wasn't included.

### Solution
Create migration:

```python
def upgrade():
    op.add_column('managed_documents', sa.Column('extracted_text', sa.Text, nullable=True))

def downgrade():
    op.drop_column('managed_documents', 'extracted_text')
```

---

## ADDITIONAL ISSUE 6: CSS Design System Missing `.dl` Styles

### Problem
The customer profile uses `<div class="dl">` for definition lists but the CSS may not be defined.

### Solution
Add to design system CSS:

```css
.dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 16px;
}
.dl dt {
  font-weight: 500;
  color: var(--muted);
}
.dl dd {
  margin: 0;
}
```

---

## ADDITIONAL ISSUE 7: Equipment Edit Form Missing `pdf_ref` Hidden Field

### Problem
The equipment new form has `pdf_ref` for PDF attachment but edit form doesn't support adding PDFs via extraction.

### Recommendation
This is by design - equipment edit should use the document upload feature on the detail page, not PDF extraction.

---

## ADDITIONAL ISSUE 8: Inconsistent Date Formatting

### Problem
Some templates use `.strftime('%Y-%m-%d')`, others use `{{ date }}` directly (Python date object). This can cause inconsistent display.

### Recommendation
Create a Jinja filter for consistent date formatting:

**File**: `app/eqms/__init__.py` (in app factory)

```python
@app.template_filter('dateformat')
def dateformat_filter(value, format='%Y-%m-%d'):
    if value is None:
        return '—'
    if hasattr(value, 'strftime'):
        return value.strftime(format)
    return str(value)
```

Usage: `{{ some_date|dateformat }}`

---

## ADDITIONAL ISSUE 9: Sales Dashboard Export Missing New Lot Fields

### Problem
If we add `total_produced`, `total_distributed`, `remaining` to lot_tracking, the export endpoint needs to include these.

### Solution
Update the export function to include the new fields in the CSV output.

---

## ADDITIONAL ISSUE 10: Admin Tools Link Needs Permission Check

### Problem
The new "Admin Tools" card links to diagnostics which may require `admin.view` permission.

### Solution
Already handled in the template with `{% if has_perm("admin.view") %}` wrapper.

---

## Implementation Order

### Phase 1: UI Changes (Immediate)
1. Update admin index.html (remove status bar, add Admin Tools)
2. Update supplier detail.html (consistent styling)

### Phase 2: Lot Tracking Enhancement
3. Update `compute_sales_dashboard()` with new lot aggregation
4. Update sales_dashboard template with new columns
5. Fix `load_lot_log_with_inventory` return value

### Phase 3: Equipment PDF Naming
6. Add `extract_equipment_from_filename()` function
7. Update extraction endpoint

### Phase 4: Customer Address Backfill
8. Ensure PDF parser changes from previous prompt are implemented
9. Run backfill script for existing customers

### Phase 5: Migrations & Cleanup
10. Create/run migrations for new columns
11. Add `.dl` CSS styles if missing

---

## Testing Checklist

### Admin Panel
- [ ] Field Configuration card removed
- [ ] System Status bar removed
- [ ] Admin Tools card appears and links to diagnostics
- [ ] Panel is visually larger/takes more screen space

### Lot Tracking
- [ ] Shows all SKUs (211810SPT, 211610SPT, 211410SPT)
- [ ] Total Produced shows sum of all lots manufactured since 2025
- [ ] Total Distributed shows sum of distributed units from those lots
- [ ] Remaining = Total Produced - Total Distributed
- [ ] Lots manufactured before 2025 are excluded from totals

### Equipment PDF
- [ ] Upload `ST-012 - Weighing Scale.pdf`
- [ ] Verify equip_code = `ST-012`
- [ ] Verify description = `Weighing Scale`

### Supplier UI
- [ ] Detail page uses two-column card layout
- [ ] Address and contact info styled like customer profile
- [ ] Products/Services in separate card

### Customer Addresses
- [ ] New PDF imports populate customer address fields
- [ ] Backfill script runs without errors
- [ ] Previously empty customers now have addresses

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `app/eqms/templates/admin/index.html` | Complete redesign - remove status, add Admin Tools |
| `app/eqms/templates/admin/suppliers/detail.html` | Restructure with card layout like customer profile |
| `app/eqms/templates/admin/sales_dashboard/index.html` | Update lot tracking table columns |
| `app/eqms/modules/rep_traceability/service.py` | Rewrite lot aggregation logic |
| `app/eqms/modules/equipment/parsers/pdf.py` | Add filename extraction function |
| `app/eqms/modules/equipment/admin.py` | Pass filename to extraction |
| `app/eqms/modules/shipstation_sync/parsers.py` | Fix return value (line 182) |
| `scripts/backfill_customer_addresses.py` | New script |
