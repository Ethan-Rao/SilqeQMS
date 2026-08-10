# Developer Agent Prompt: System Fixes & Enhancements

**Date:** 2026-01-29  
**Priority:** P0/P1 Mixed  
**Focus:** Lot Tracking Fix, Customer Profile Cleanup, PDF Auto-Populate, Rep System Clarification

---

## Executive Summary

This prompt addresses several issues identified during system review:

1. **P0**: Lot Tracking table showing raw lots instead of corrected lot names - needs to show only 3 rows (most recent lot per SKU)
2. **P0**: Customer Profile "Orders" tab not functional - remove it entirely (redundant with Sales Orders and Distributions tabs)
3. **P1**: Equipment/Supplier PDF upload with auto-field-population
4. **P2**: Clarify and document rep system source (currently seeded from `users` table)

---

## P0-1: Lot Tracking Table Fix (CRITICAL)

### Problem

The Lot Tracking table on the Sales Dashboard is:
1. Showing raw/uncorrected lot numbers (legacy behavior we do NOT want)
2. Showing too many rows
3. Not applying the `Correct Lot Name` corrections from LotLog.csv

### Required Behavior

The Lot Tracking table should display **exactly 3 rows** - one for each SKU:
- **211410SPT** (14Fr): Most recently distributed lot
- **211610SPT** (16Fr): Most recently distributed lot  
- **211810SPT** (18Fr): Most recently distributed lot

Each row should show:
- **SKU** (not the lot as the primary identifier)
- **Current Lot** (the CORRECTED lot name from LotLog.csv)
- **Units Distributed** (from this lot)
- **Active Inventory** (Total in Lot - Distributed)
- **Last Ship Date**

### Root Cause Analysis

Looking at `app/eqms/modules/rep_traceability/service.py` lines 795-895, the lot tracking logic:

1. Loads `lot_corrections` from LotLog.csv via `load_lot_log_with_inventory()` ✅
2. Applies corrections: `corrected_lot = lot_corrections.get(normalized_lot, normalized_lot)` ✅
3. But then builds `lot_map` keyed by lot number, not by SKU
4. Returns ALL qualifying lots, not just the most recent per SKU

### Fix Required

**File:** `app/eqms/modules/rep_traceability/service.py`

Replace the lot tracking section (approximately lines 795-895) with this simplified version:

```python
    # Lot tracking - SIMPLIFIED: Show only the most recently distributed lot per SKU
    from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory, normalize_lot, VALID_SKUS
    lotlog_path = (os.environ.get("SHIPSTATION_LOTLOG_PATH") or os.environ.get("LotLog_Path") or "app/eqms/data/LotLog.csv").strip()
    lot_to_sku, lot_corrections, lot_inventory, lot_years = load_lot_log_with_inventory(lotlog_path)
    
    # Track most recent lot per SKU
    sku_latest_lot: dict[str, dict[str, Any]] = {}
    
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
    
    # Aggregate by corrected lot, track most recent per SKU
    lot_stats: dict[str, dict[str, Any]] = {}  # corrected_lot -> stats
    
    for line, entry in all_lines:
        raw_lot = (line.lot_number or "").strip()
        if not raw_lot:
            continue
        
        # Apply correction from LotLog
        normalized_lot = normalize_lot(raw_lot)
        corrected_lot = lot_corrections.get(normalized_lot, normalized_lot)
        
        # Get SKU for this lot from LotLog (or from the line itself)
        sku = lot_to_sku.get(corrected_lot) or lot_to_sku.get(normalized_lot) or line.sku
        if not sku or sku not in VALID_SKUS:
            continue
        
        # Aggregate stats for this corrected lot
        if corrected_lot not in lot_stats:
            lot_stats[corrected_lot] = {
                "lot": corrected_lot,
                "sku": sku,
                "units": 0,
                "last_date": entry.ship_date,
            }
        lot_stats[corrected_lot]["units"] += int(line.quantity or 0)
        if entry.ship_date and entry.ship_date > lot_stats[corrected_lot]["last_date"]:
            lot_stats[corrected_lot]["last_date"] = entry.ship_date
        
        # Track most recent lot per SKU (first occurrence is most recent due to ORDER BY desc)
        if sku not in sku_latest_lot:
            sku_latest_lot[sku] = {
                "sku": sku,
                "lot": corrected_lot,
                "units": 0,
                "last_date": entry.ship_date,
            }
    
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
            sku = lot_to_sku.get(corrected_lot) or lot_to_sku.get(normalized_lot) or e.sku
            if not sku or sku not in VALID_SKUS:
                continue
            
            if corrected_lot not in lot_stats:
                lot_stats[corrected_lot] = {
                    "lot": corrected_lot,
                    "sku": sku,
                    "units": 0,
                    "last_date": e.ship_date,
                }
            lot_stats[corrected_lot]["units"] += int(e.quantity or 0)
            if e.ship_date and e.ship_date > lot_stats[corrected_lot]["last_date"]:
                lot_stats[corrected_lot]["last_date"] = e.ship_date
            
            if sku not in sku_latest_lot:
                sku_latest_lot[sku] = {
                    "sku": sku,
                    "lot": corrected_lot,
                    "units": 0,
                    "last_date": e.ship_date,
                }
    
    # Build final lot_tracking list - ONE ROW PER SKU (most recent lot)
    lot_tracking = []
    for sku in VALID_SKUS:  # Ensures consistent order: 211810SPT, 211610SPT, 211410SPT
        if sku in sku_latest_lot:
            info = sku_latest_lot[sku]
            corrected_lot = info["lot"]
            
            # Get aggregated stats for this lot
            stats = lot_stats.get(corrected_lot, {})
            total_units_distributed = stats.get("units", 0)
            last_date = stats.get("last_date")
            
            # Get inventory from LotLog
            total_produced = lot_inventory.get(corrected_lot)
            active_inventory = None
            if total_produced is not None:
                active_inventory = int(total_produced) - total_units_distributed
            
            lot_tracking.append({
                "sku": sku,
                "lot": corrected_lot,
                "units": total_units_distributed,
                "last_date": last_date,
                "active_inventory": active_inventory,
            })
    
    # Sort by SKU for consistent display (or reverse for 18/16/14 order)
    lot_tracking = sorted(lot_tracking, key=lambda x: x["sku"], reverse=True)
```

### Update Template

**File:** `app/eqms/templates/admin/sales_dashboard/index.html`

Update the Lot Tracking table (around lines 172-212) to show SKU as the primary column:

```html
<!-- Lot Tracking -->
<div class="card">
  <h2 style="margin-top:0; font-size:16px;">Current Lots by SKU</h2>
  {% if lot_tracking %}
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">SKU</th>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Current Lot</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Distributed</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Remaining</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Last Ship</th>
          </tr>
        </thead>
        <tbody>
          {% for row in lot_tracking %}
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
              <td style="padding:10px 12px;"><code style="background:rgba(255,255,255,0.05); padding:2px 6px; border-radius:4px;">{{ row.sku|e }}</code></td>
              <td style="padding:10px 12px;"><code style="background:rgba(102,163,255,0.1); padding:2px 6px; border-radius:4px; color:var(--primary);">{{ row.lot|e }}</code></td>
              <td style="padding:10px 12px; text-align:right; font-weight:600;">{{ row.units }}</td>
              <td style="padding:10px 12px; text-align:right; font-weight:600;">
                {% if row.active_inventory is not none %}
                  {% if row.active_inventory < 0 %}
                    <span style="color:var(--danger);">⚠️ {{ row.active_inventory }}</span>
                  {% elif row.active_inventory < 50 %}
                    <span style="color:#f59e0b;">{{ row.active_inventory }}</span>
                  {% else %}
                    {{ row.active_inventory }}
                  {% endif %}
                {% else %}
                  <span class="muted">N/A</span>
                {% endif %}
              </td>
              <td style="padding:10px 12px; text-align:right; font-size:12px; color:var(--muted);">{{ row.last_date }}</td>
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

### Verification
1. Go to `/admin/sales-dashboard`
2. Lot Tracking table shows exactly 3 rows (one per SKU)
3. Each row shows the CORRECTED lot name (e.g., `SLQ-11202024` not `SLQ-112020024`)
4. "Remaining" column shows accurate inventory based on LotLog.csv

---

## P0-2: Remove "Orders" Tab from Customer Profile

### Problem

The "Orders" tab at `/admin/customers/{id}?tab=orders` is:
1. Not functional (causes Internal Server Error)
2. Redundant - the same information is available in "Sales Orders" and "Distributions" tabs

### Fix Required

#### 1. Remove the tab link from navigation

**File:** `app/eqms/templates/admin/customers/detail.html`

Delete lines 30-33 (the Orders tab link):

```html
<!-- DELETE THESE LINES -->
<a href="{{ url_for('customer_profiles.customer_detail', customer_id=customer.id) }}?tab=orders"
   style="flex:1; padding:12px 16px; text-align:center; text-decoration:none; font-weight:500; {% if tab == 'orders' %}background:rgba(102,163,255,0.1); color:var(--primary); border-bottom:2px solid var(--primary);{% else %}color:var(--muted);{% endif %}">
  Orders ({{ customer_stats.total_orders }})
</a>
```

#### 2. Remove the tab content section

**File:** `app/eqms/templates/admin/customers/detail.html`

Delete lines 166-218 (the entire `{% elif tab == 'orders' %}` block):

```html
<!-- DELETE THIS ENTIRE BLOCK -->
{% elif tab == 'orders' %}
  <!-- Orders Tab (Grouped by order_number + ship_date) -->
  <div class="card">
    ... entire content ...
  </div>
```

#### 3. Remove the `orders` variable from the route

**File:** `app/eqms/modules/customer_profiles/admin.py`

In the `customer_detail()` function, remove the code that builds `grouped_orders` (lines 360-410 approximately) and remove `orders=grouped_orders` from the `render_template()` call.

#### 4. Update default tab if user navigates to `?tab=orders`

The template should gracefully handle invalid tab values by defaulting to `overview`.

### Verification
1. Go to `/admin/customers/{id}`
2. Only 5 tabs visible: Overview, Sales Orders, Distributions, Notes, Edit
3. No "Orders" tab
4. Navigating to `?tab=orders` redirects to Overview (or shows Overview content)

---

## P1: Equipment & Supplier PDF Auto-Populate

### Overview

When uploading a PDF (like an Equipment Requirements Form) to an Equipment or Supplier record, the system should:

1. Extract text from the PDF
2. Parse common field values (ID, name, manufacturer, model, serial, etc.)
3. Auto-fill the form fields with extracted values
4. Let admin review/edit before saving

### Important: Admin Control

- **Do NOT enforce legacy classifications** (Production/Engineering/Quality/Regulatory for equipment, or I/II/III/IV for suppliers)
- Admin will define their own categories in the system
- PDF parsing extracts values as *suggestions* only
- Admin can override any extracted value

### Implementation

#### 1. Create PDF Parser Utility

**File:** `app/eqms/modules/equipment/parsers/__init__.py`

```python
"""PDF parsing utilities for equipment and supplier documents."""
```

**File:** `app/eqms/modules/equipment/parsers/pdf.py`

```python
"""PDF field extraction for equipment documents."""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_equipment_fields(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract equipment fields from PDF.
    Returns dict of field_name -> extracted_value (all optional).
    """
    try:
        import pdfplumber
        from io import BytesIO
        
        extracted = {}
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
        
        # Field extraction patterns
        patterns = {
            "equip_code": [
                r"(?:Equipment\s*ID|Equip\.?\s*ID|Asset\s*(?:ID|#)|ID)[:\s]*([A-Z]{1,4}[\-\s]?\d{2,6})",
            ],
            "description": [
                r"(?:Equipment\s*(?:Name|Description)|Description|Name)[:\s]*([^\n\r]{3,100})",
            ],
            "mfg": [
                r"(?:Manufacturer|Mfg\.?|Make|Brand)[:\s]*([^\n\r]{2,80})",
            ],
            "model_no": [
                r"(?:Model\s*(?:No\.?|Number|#)?)[:\s]*([^\n\r]{2,50})",
            ],
            "serial_no": [
                r"(?:Serial\s*(?:No\.?|Number|#)?|S/?N)[:\s]*([^\n\r]{2,50})",
            ],
            "location": [
                r"(?:Location|Dept\.?|Department)[:\s]*([^\n\r]{2,80})",
            ],
        }
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    value = re.sub(r"\s+", " ", value)  # Normalize whitespace
                    if value and len(value) > 1:
                        extracted[field] = value
                        break
        
        logger.info("Extracted equipment fields from PDF: %s", list(extracted.keys()))
        return extracted
        
    except Exception as e:
        logger.warning("Equipment PDF extraction failed: %s", e)
        return {}


def extract_supplier_fields(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract supplier fields from PDF (TCI forms, etc.).
    Returns dict of field_name -> extracted_value (all optional).
    """
    try:
        import pdfplumber
        from io import BytesIO
        
        extracted = {}
        
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
        
        patterns = {
            "name": [
                r"(?:Supplier|Vendor|Company)\s*(?:Name)?[:\s]*([^\n\r]{2,100})",
            ],
            "address": [
                r"(?:Address)[:\s]*([^\n\r]{5,150})",
            ],
            "product_service_provided": [
                r"(?:Products?|Services?|Provides?|Description)[:\s]*([^\n\r]{5,200})",
            ],
        }
        
        # Email extraction
        email_match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", full_text)
        if email_match:
            extracted["contact_email"] = email_match.group(1)
        
        # Phone extraction
        phone_match = re.search(r"(?:Phone|Tel)[:\s]*([\d\-\(\)\s\.]{10,20})", full_text, re.IGNORECASE)
        if phone_match:
            extracted["contact_phone"] = phone_match.group(1).strip()
        
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    value = re.sub(r"\s+", " ", value)
                    if value and len(value) > 1:
                        extracted[field] = value
                        break
        
        logger.info("Extracted supplier fields from PDF: %s", list(extracted.keys()))
        return extracted
        
    except Exception as e:
        logger.warning("Supplier PDF extraction failed: %s", e)
        return {}
```

#### 2. Add Extract-from-PDF Routes

**File:** `app/eqms/modules/equipment/admin.py`

Add route:

```python
@bp.post("/equipment/extract-from-pdf")
@require_permission("equipment.create")
def equipment_extract_from_pdf():
    """Extract fields from uploaded PDF for auto-populate."""
    from app.eqms.modules.equipment.parsers.pdf import extract_equipment_fields
    from flask import jsonify
    
    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["pdf_file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Must be a PDF file"}), 400
    
    pdf_bytes = file.read()
    extracted = extract_equipment_fields(pdf_bytes)
    
    return jsonify({
        "success": True,
        "fields": extracted,
        "message": f"Extracted {len(extracted)} field(s). Review and edit as needed.",
    })
```

Similar route for suppliers in `app/eqms/modules/suppliers/admin.py`.

#### 3. Add Upload + Auto-Fill UI to Equipment Form

**File:** `app/eqms/templates/admin/equipment/new.html` (and `edit.html`)

Add a section for PDF upload with auto-extract:

```html
<div class="card" style="margin-bottom:14px;">
  <h3 style="margin-top:0; font-size:14px;">Quick Fill from PDF</h3>
  <p class="muted" style="font-size:12px;">Upload an Equipment Requirements Form to auto-fill fields.</p>
  
  <div style="display:flex; gap:10px; align-items:center; margin-top:12px;">
    <input type="file" id="pdf-upload" accept=".pdf" />
    <button type="button" class="button button--secondary" onclick="extractFromPdf()">Extract Fields</button>
  </div>
  
  <div id="extract-status" style="margin-top:8px; font-size:12px;"></div>
</div>

<script>
async function extractFromPdf() {
  const fileInput = document.getElementById('pdf-upload');
  const status = document.getElementById('extract-status');
  
  if (!fileInput.files[0]) {
    status.innerHTML = '<span style="color:var(--danger);">Please select a PDF first.</span>';
    return;
  }
  
  status.innerHTML = '<span style="color:var(--muted);">Extracting...</span>';
  
  const formData = new FormData();
  formData.append('pdf_file', fileInput.files[0]);
  
  try {
    const res = await fetch('/admin/equipment/extract-from-pdf', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    
    if (data.error) {
      status.innerHTML = `<span style="color:var(--danger);">${data.error}</span>`;
      return;
    }
    
    // Auto-fill form fields
    const fieldMap = {
      'equip_code': 'equip_code',
      'description': 'description',
      'mfg': 'mfg',
      'model_no': 'model_no',
      'serial_no': 'serial_no',
      'location': 'location',
    };
    
    let filled = 0;
    for (const [extractedField, formField] of Object.entries(fieldMap)) {
      if (data.fields[extractedField]) {
        const input = document.querySelector(`[name="${formField}"]`);
        if (input && !input.value) {  // Only fill if empty
          input.value = data.fields[extractedField];
          filled++;
        }
      }
    }
    
    status.innerHTML = `<span style="color:var(--success);">✅ Filled ${filled} field(s). Review and save.</span>`;
  } catch (e) {
    status.innerHTML = '<span style="color:var(--danger);">Extraction failed.</span>';
  }
}
</script>
```

### Verification
1. Go to `/admin/equipment/new`
2. Upload the Equipment Requirements Form PDF
3. Click "Extract Fields"
4. Form fields auto-populate with extracted values
5. Admin can edit any value before saving

---

## P2: Rep System Source Clarification

### Current Behavior

Based on the migration at `migrations/versions/h2i3j4k5l6m_create_reps_table.py`:

1. The `reps` table is seeded from the `users` table
2. It pulls users who are referenced as reps in:
   - `customers.primary_rep_id`
   - `customer_reps.rep_id`
   - `distribution_log_entries.rep_id`

The rep names visible in the dropdown (Chuck, Ethan, ethan7, Ethan (Test), ShipStation Imports) come from email addresses in the `users` table from a previous system migration.

### How This Happened

When ShipStation syncs orders, it may have created "user" records for rep assignments. The migration then copied these into the `reps` table.

### Current State

Reps are now a **separate table** from users:
- `reps` table stores rep names/info
- `users` table stores actual login accounts
- They are no longer linked

### Adding New Reps

To add a new rep:
1. Go to `/admin/reps/new` (if this route exists)
2. Or directly insert into the `reps` table

### Sync from Another System?

If Ethan wants reps created in another system to automatically appear here, we would need to:

1. **Identify the other system** - Is it the old RepQMS? ShipStation? Another database?
2. **Create a sync mechanism** - Either:
   - A periodic job that queries the other system's API
   - A webhook receiver that listens for rep creation events
   - A manual import script

**Recommendation:** For now, manage reps directly in SilqeQMS via `/admin/reps`. If cross-system sync is needed, document which system and its API capabilities, then implement a targeted sync.

### If Reps Route Doesn't Exist

Check if `/admin/reps` exists. If not, create it:

**File:** `app/eqms/modules/customer_profiles/admin.py`

Add routes per the previous prompt (`DEVELOPER_PROMPT_2026_01_29_CRITICAL_FIXES.md`).

---

## Implementation Order

1. **P0: Lot Tracking Fix** (15-30 min)
   - Update `compute_sales_dashboard()` in service.py
   - Update sales dashboard template

2. **P0: Remove Orders Tab** (10 min)
   - Delete tab from navigation
   - Delete tab content block
   - Remove unused code from route

3. **P1: PDF Auto-Populate** (30-45 min)
   - Create parser module
   - Add extract routes
   - Update equipment/supplier templates

4. **P2: Rep Management** (15 min if routes missing)
   - Verify `/admin/reps` exists
   - Add routes if needed
   - Document source/sync options

---

## Verification Checklist

After all changes:

- [ ] **Lot Tracking**: Shows exactly 3 rows, one per SKU, with CORRECTED lot names
- [ ] **Customer Profile**: No "Orders" tab, only Overview/Sales Orders/Distributions/Notes/Edit
- [ ] **Equipment PDF**: Upload extracts and auto-fills form fields
- [ ] **Supplier PDF**: Upload extracts and auto-fills form fields  
- [ ] **Reps**: `/admin/reps` page loads and allows adding new reps
