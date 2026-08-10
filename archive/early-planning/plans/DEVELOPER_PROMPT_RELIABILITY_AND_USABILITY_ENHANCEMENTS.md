# Developer Prompt: System Reliability and Usability Enhancements

**Date:** 2026-01-27  
**Priority:** P0 (Critical)  
**Scope:** Enhance reliability, usability, PDF parsing, multi-SKU manual entry, two-file slots per distribution, detailed views, data reset. **No new features beyond specified requirements.**

---

## Executive Summary

This prompt addresses critical usability and reliability issues identified through system review. The focus is on making the system work reliably for daily operations, ensuring PDF parsing succeeds, enabling multi-SKU manual entries, providing clear file slot management, and ensuring all information is accessible via detailed views without navigation.

**Key Objectives:**
1. **Reliability:** Fix PDF parsing failures (never seen successful)
2. **Usability:** All information accessible via detailed views (no page navigation needed)
3. **Multi-SKU Support:** Manual distribution entry handles multiple SKUs/QTYs
4. **Two File Slots:** Clear Sales Order PDF + Delivery Verification label slots per distribution
5. **Admin Editability:** Full edit capability on all components
6. **Data Reset:** Verify and fix data reset process for clean system start

---

## Part 1: System Architecture and Canonical Pipeline

### Current System State

**Technology Stack:**
- Flask (Python 3.12+)
- PostgreSQL (production) / SQLite (dev)
- Alembic migrations
- Gunicorn (production) / Flask dev server (local)
- S3-compatible storage (production) / Local filesystem (dev)
- DigitalOcean App Platform deployment

**Canonical Data Pipeline (MUST ENFORCE):**
```
ShipStation API
    ↓
Distribution Log Entry (clean, normalized, sales_order_id = NULL, customer_id = NULL)
    ↓
PDF Import (bulk or single) → Sales Order (creates Customer from ship-to)
    ↓
Distribution matched to Sales Order (sales_order_id set, customer_id = SO.customer_id)
    ↓
Sales Dashboard (ONLY aggregates WHERE sales_order_id IS NOT NULL)
```

**Critical Invariants:**
1. Customers created **only** from Sales Orders (not ShipStation)
2. Dashboard aggregates **only** from matched distributions (`sales_order_id IS NOT NULL`)
3. Distributions can exist unmatched temporarily (excluded from aggregations)
4. Sales Order is source-of-truth for customer identity

---

## Part 2: Critical Issues to Fix

### Issue 1: PDF Parsing Never Succeeds (P0)

**Problem:** PDF import has never been observed to work successfully. Users report failures when uploading Sales Order PDFs (`2025_1SOs.pdf`) and shipping label PDFs (`Label1.pdf`).

**Root Causes (Likely):**
1. **Regex patterns too strict:** `_parse_silq_sales_order_page()` may not match actual PDF text format
2. **Text extraction issues:** `pdfplumber` may not extract text correctly from PDFs
3. **Missing error visibility:** Errors may be logged but not shown to user
4. **Label parsing too simple:** `_parse_label_page()` may miss FedEx label formats

**Files to Review/Change:**
- `app/eqms/modules/rep_traceability/parsers/pdf.py` (entire file)
- `app/eqms/modules/rep_traceability/admin.py:1361` (`sales_orders_import_pdf_bulk()`)
- `app/eqms/modules/rep_traceability/admin.py:1469` (`sales_orders_import_pdf()`)

**Required Actions:**
1. **Add comprehensive logging:** Log extracted text (first 500 chars) for debugging
2. **Improve regex patterns:** Make patterns more flexible, handle variations
3. **Add fallback parsing:** If table extraction fails, try text-based extraction
4. **Test with provided PDFs:** Use `Label1.pdf` and `2025_1SOs.pdf` as test cases
5. **Show parse errors clearly:** Display parse errors in UI with page numbers

**Implementation:**
```python
# In _parse_silq_sales_order_page():
# Add logging
logger.info(f"Parsing page {page_num}, text preview: {text[:200]}")

# Make order number pattern more flexible
order_patterns = [
    r'SO\s*#?\s*[:\s]*(\d{4,10})',
    r'Order\s*(?:#|Number|No\.?)?\s*[:\s]*(\d{4,10})',
    r'(\d{4,10})',  # Fallback: any 4-10 digit number
]

# Improve item extraction (handle table and text formats)
# Try table extraction first, fallback to text regex
```

---

### Issue 2: Manual Distribution Entry Only Handles One SKU (P0)

**Problem:** Current manual entry form only accepts one SKU, one lot, one quantity. Real distributions often have multiple SKUs (e.g., 10x 18Fr, 5x 16Fr, 3x 14Fr).

**Current Implementation:**
- Form fields: `sku`, `lot_number`, `quantity` (single values)
- Creates one `DistributionLogEntry` per submission

**Required Change:**
- Form must accept **multiple SKU/Lot/Quantity combinations**
- Each combination creates a separate `DistributionLogEntry` record
- All entries share: ship_date, order_number, facility_name, customer_id, rep_id, source
- Each entry has unique: sku, lot_number, quantity

**Files to Change:**
- `app/eqms/templates/admin/distribution_log/new.html` (or `edit.html` if used for new)
- `app/eqms/modules/rep_traceability/admin.py:162` (`distribution_log_new_post()`)
- `app/eqms/modules/rep_traceability/service.py:131` (`create_distribution_entry()`)

**Implementation:**

**Frontend (Template):**
```html
<!-- Replace single SKU/Lot/Qty fields with repeatable section -->
<div id="sku-rows">
  <div class="sku-row" data-row="0">
    <div class="grid" style="grid-template-columns: 1fr 1fr 1fr 40px; gap: 12px;">
      <div>
        <div class="label">SKU *</div>
        <select name="skus[0]" required>
          <option value="">Select SKU</option>
          <option value="211810SPT">211810SPT (18Fr)</option>
          <option value="211610SPT">211610SPT (16Fr)</option>
          <option value="211410SPT">211410SPT (14Fr)</option>
        </select>
      </div>
      <div>
        <div class="label">Lot Number *</div>
        <input name="lots[0]" placeholder="SLQ-12345" required />
      </div>
      <div>
        <div class="label">Quantity *</div>
        <input name="quantities[0]" type="number" min="1" required />
      </div>
      <div style="display:flex; align-items:flex-end;">
        <button type="button" class="button button--secondary" onclick="removeSkuRow(0)" style="padding:10px;">×</button>
      </div>
    </div>
  </div>
</div>
<button type="button" class="button button--secondary" onclick="addSkuRow()">+ Add Another SKU</button>
```

**Backend (Route Handler):**
```python
@bp.post("/distribution-log/new")
@require_permission("distribution_log.create")
def distribution_log_new_post():
    # ... existing customer validation ...
    
    # Get multiple SKU/Lot/Qty combinations
    skus = request.form.getlist("skus[]")  # or "skus[0]", "skus[1]", etc.
    lots = request.form.getlist("lots[]")
    quantities = request.form.getlist("quantities[]")
    
    if not skus or not all(skus):
        flash("At least one SKU is required.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_new_get"))
    
    # Validate all combinations
    for i, (sku, lot, qty) in enumerate(zip(skus, lots, quantities)):
        if not sku or not lot or not qty:
            flash(f"Row {i+1}: SKU, Lot, and Quantity are all required.", "danger")
            return redirect(url_for("rep_traceability.distribution_log_new_get"))
    
    # Create base payload (shared fields)
    base_payload = {
        "ship_date": request.form.get("ship_date"),
        "order_number": request.form.get("order_number"),
        "facility_name": c.facility_name,  # From customer
        "rep_id": request.form.get("rep_id"),
        "customer_id": str(c.id),
        "source": "manual",
        # ... other shared fields ...
    }
    
    # Create one distribution entry per SKU/Lot/Qty combination
    created_count = 0
    for sku, lot, qty in zip(skus, lots, quantities):
        payload = base_payload.copy()
        payload.update({
            "sku": sku,
            "lot_number": lot,
            "quantity": qty,
        })
        
        errs = validate_distribution_payload(payload)
        if errs:
            flash(f"Row {created_count+1} validation failed: {'; '.join([f'{e.field}: {e.message}' for e in errs])}", "danger")
            continue
        
        create_distribution_entry(s, payload, user=u, source_default="manual")
        created_count += 1
    
    s.commit()
    flash(f"Created {created_count} distribution entry/entries.", "success")
    return redirect(url_for("rep_traceability.distribution_log_list"))
```

**Acceptance Criteria:**
- [ ] Form accepts multiple SKU/Lot/Qty rows
- [ ] User can add/remove rows dynamically
- [ ] Each combination creates separate `DistributionLogEntry`
- [ ] All entries share same order_number, ship_date, customer
- [ ] Validation works for each row individually

---

### Issue 3: Two File Slots Per Distribution (P0)

**Problem:** Each distribution needs two clearly marked file slots:
1. **Sales Order PDF** (parsed from bulk or manually uploaded on detail view)
2. **Delivery Verification** (FedEx label - parsed from bulk or individual upload)

**Current State:**
- `OrderPdfAttachment` table exists with `distribution_entry_id` FK
- No clear distinction between SO PDF and label PDF
- No UI indication of which slot is filled/empty

**Required Changes:**

**A. Data Model Enhancement:**
- Add `pdf_slot_type` field to `OrderPdfAttachment` (or use existing `pdf_type` with specific values)
- Values: `"sales_order"` or `"delivery_verification"` (for distribution-level attachments)
- Ensure `pdf_type` values are consistent across system

**B. UI Enhancement (Distribution Detail View):**
- Show two clearly marked sections:
  - **"Sales Order PDF"** section with:
    - Status indicator: ✅ "Uploaded" or ⚠️ "Not Uploaded"
    - Upload button (if not uploaded)
    - Download button (if uploaded)
    - Filename and upload date (if uploaded)
  - **"Delivery Verification (Label)"** section with:
    - Status indicator: ✅ "Uploaded" or ⚠️ "Not Uploaded"
    - Upload button (if not uploaded)
    - Download button (if uploaded)
    - Filename and upload date (if uploaded)

**C. Bulk PDF Import Logic:**
- When parsing bulk PDF:
  - Sales Order pages → Store with `pdf_type="sales_order"`, `distribution_entry_id` set after matching
  - Label pages → Store with `pdf_type="delivery_verification"`, `distribution_entry_id` set after address matching

**Files to Change:**
- `app/eqms/modules/rep_traceability/models.py` (verify `OrderPdfAttachment.pdf_type` supports these values)
- `app/eqms/modules/rep_traceability/admin.py:349` (`distribution_log_entry_details()`)
- `app/eqms/templates/admin/distribution_log/list.html` (modal JS for detail view)
- `app/eqms/modules/rep_traceability/admin.py:479` (`distribution_log_upload_pdf()` - mark as SO)
- `app/eqms/modules/rep_traceability/admin.py` (new route: `distribution_log_upload_label()`)

**Implementation:**

**Backend: Add Label Upload Route**
```python
@bp.post("/distribution-log/<int:entry_id>/upload-label")
@require_permission("distribution_log.edit")
def distribution_log_upload_label(entry_id: int):
    """Upload delivery verification (label) PDF to distribution entry."""
    s = db_session()
    u = _current_user()
    
    entry = s.get(DistributionLogEntry, entry_id)
    if not entry:
        flash("Distribution entry not found.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))
    
    f = request.files.get("label_file")
    if not f or not f.filename:
        flash("Please select a label PDF file.", "danger")
        return redirect(url_for("rep_traceability.distribution_log_list"))
    
    pdf_bytes = f.read()
    filename = f.filename or "label.pdf"
    
    # Store as delivery_verification type
    _store_pdf_attachment(
        s,
        pdf_bytes=pdf_bytes,
        filename=filename,
        pdf_type="delivery_verification",  # Clear slot type
        sales_order_id=None,  # Not linked to SO
        distribution_entry_id=entry.id,  # Linked to distribution
        user=u,
    )
    
    s.commit()
    flash(f"Delivery verification label uploaded.", "success")
    return redirect(url_for("rep_traceability.distribution_log_list"))
```

**Backend: Update SO Upload Route**
```python
# In distribution_log_upload_pdf():
# Mark as sales_order type
_store_pdf_attachment(
    s,
    pdf_bytes=pdf_bytes,
    filename=filename,
    pdf_type="sales_order",  # Clear slot type
    sales_order_id=order.id if order else None,
    distribution_entry_id=entry.id,
    user=u,
)
```

**Frontend: Distribution Detail Modal**
```javascript
// In distribution detail modal JS:
function renderFileSlots(attachments) {
    let html = '<div class="section-header">File Attachments</div>';
    
    // Find SO PDF and label PDF
    const soPdf = attachments.find(a => a.pdf_type === 'sales_order' || a.pdf_type === 'sales_order_page');
    const labelPdf = attachments.find(a => a.pdf_type === 'delivery_verification' || a.pdf_type === 'shipping_label');
    
    // Sales Order PDF Slot
    html += '<div style="margin-bottom:16px; padding:12px; border:1px solid var(--border); border-radius:8px;">';
    html += '<div style="font-weight:600; margin-bottom:8px;">Sales Order PDF</div>';
    if (soPdf) {
        html += '<div style="color:#10b981;">✅ Uploaded</div>';
        html += `<div style="font-size:12px; color:var(--muted); margin:4px 0;">${soPdf.filename}</div>`;
        html += `<a href="/admin/sales-orders/pdf/${soPdf.id}/download" class="button button--secondary" style="margin-top:8px;">Download</a>`;
    } else {
        html += '<div style="color:#f59e0b;">⚠️ Not Uploaded</div>';
        html += '<form method="post" action="/admin/distribution-log/' + entryId + '/upload-pdf" enctype="multipart/form-data" style="margin-top:8px;">';
        html += '<input type="file" name="pdf_file" accept=".pdf" required />';
        html += '<button type="submit" class="button">Upload Sales Order PDF</button>';
        html += '</form>';
    }
    html += '</div>';
    
    // Delivery Verification Slot
    html += '<div style="padding:12px; border:1px solid var(--border); border-radius:8px;">';
    html += '<div style="font-weight:600; margin-bottom:8px;">Delivery Verification (Label)</div>';
    if (labelPdf) {
        html += '<div style="color:#10b981;">✅ Uploaded</div>';
        html += `<div style="font-size:12px; color:var(--muted); margin:4px 0;">${labelPdf.filename}</div>`;
        html += `<a href="/admin/sales-orders/pdf/${labelPdf.id}/download" class="button button--secondary" style="margin-top:8px;">Download</a>`;
    } else {
        html += '<div style="color:#f59e0b;">⚠️ Not Uploaded</div>';
        html += '<form method="post" action="/admin/distribution-log/' + entryId + '/upload-label" enctype="multipart/form-data" style="margin-top:8px;">';
        html += '<input type="file" name="label_file" accept=".pdf" required />';
        html += '<button type="submit" class="button">Upload Label PDF</button>';
        html += '</form>';
    }
    html += '</div>';
    
    return html;
}
```

**Acceptance Criteria:**
- [ ] Two clearly marked file slots in distribution detail view
- [ ] Status indicators show uploaded/not uploaded
- [ ] Upload buttons work for both slots
- [ ] Download buttons work for uploaded files
- [ ] Bulk PDF import correctly categorizes SO vs label pages

---

### Issue 4: PDF Download from Detail Views and Customer Profile (P0)

**Problem:** Users need to download specific PDF pages from:
1. Distribution detail view (modal)
2. Customer profile page (distributions section)

**Current State:**
- Download route exists: `GET /admin/sales-orders/pdf/<attachment_id>/download`
- May not be accessible from distribution detail modal
- May not be accessible from customer profile

**Required Changes:**
- Ensure download links work in distribution detail modal
- Add download links to customer profile distributions section
- Verify download route handles both SO-level and distribution-level attachments

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py:1479` (`sales_order_pdf_download()`)
- `app/eqms/templates/admin/distribution_log/list.html` (modal JS)
- `app/eqms/templates/admin/customers/detail.html` (distributions section)

**Implementation:**

**Verify Download Route:**
```python
@bp.get("/sales-orders/pdf/<int:attachment_id>/download")
@require_permission("sales_orders.view")
def sales_order_pdf_download(attachment_id: int):
    """Download PDF attachment (works for both SO and distribution attachments)."""
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
    from app.eqms.storage import storage_from_config
    from flask import current_app, send_file
    
    s = db_session()
    attachment = s.get(OrderPdfAttachment, attachment_id)
    if not attachment:
        from flask import abort
        abort(404)
    
    # Read from storage
    storage = storage_from_config(current_app.config)
    try:
        with storage.open(attachment.storage_key, "rb") as f:
            pdf_bytes = f.read()
    except Exception as e:
        current_app.logger.error(f"Failed to read PDF {attachment_id}: {e}")
        from flask import abort
        abort(500)
    
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=attachment.filename,
    )
```

**Add to Customer Profile Template:**
```html
<!-- In customers/detail.html, distributions section: -->
{% for dist in distributions %}
  <tr>
    <!-- ... existing columns ... -->
    <td>
      {% for att in dist.attachments %}
        <a href="{{ url_for('rep_traceability.sales_order_pdf_download', attachment_id=att.id) }}" 
           class="button button--secondary" style="font-size:11px; padding:4px 8px;">
          Download {{ att.pdf_type }}
        </a>
      {% endfor %}
    </td>
  </tr>
{% endfor %}
```

**Acceptance Criteria:**
- [ ] Download links work in distribution detail modal
- [ ] Download links work in customer profile distributions section
- [ ] Downloads return correct PDF files
- [ ] Filenames are preserved

---

### Issue 5: Detailed Views Must Show All Information (P0)

**Problem:** Users don't want to navigate to new pages. All information must be accessible via detailed views (modals, dropdowns, expandable sections).

**Current State:**
- Distribution detail modal exists (`distribution_log_entry_details()`)
- May be missing some information
- Customer profile may not show all distribution details

**Required Changes:**

**A. Distribution Detail Modal Enhancement:**
- Show **all** distribution fields (ship date, order number, facility, customer, rep, SKU, lot, quantity, source, tracking, address, contact info)
- Show linked Sales Order (if matched) with link to SO detail
- Show customer stats (if customer linked)
- Show **both file slots** (SO PDF + Label PDF) with upload/download
- Show notes (if any)
- Show audit trail (who created/modified, when)

**B. Customer Profile Enhancement:**
- Show all distributions for customer (with expandable details)
- Show download links for all PDFs
- Show notes
- Show order history

**C. Sales Order Detail Enhancement:**
- Show all linked distributions (with expandable details)
- Show all PDF attachments (with download links)
- Show customer info

**Files to Change:**
- `app/eqms/modules/rep_traceability/admin.py:349` (`distribution_log_entry_details()`)
- `app/eqms/templates/admin/distribution_log/list.html` (modal JS)
- `app/eqms/templates/admin/customers/detail.html`
- `app/eqms/templates/admin/sales_orders/detail.html`

**Implementation:**

**Enhance Distribution Detail JSON Response:**
```python
# In distribution_log_entry_details():
return jsonify({
    "entry": {
        # ... existing fields ...
        "address1": entry.address1,
        "address2": entry.address2,
        "city": entry.city,
        "state": entry.state,
        "zip": entry.zip,
        "contact_name": entry.contact_name,
        "contact_phone": entry.contact_phone,
        "contact_email": entry.contact_email,
        "tracking_number": entry.tracking_number,
        "rep_name": entry.rep_name,
        "created_at": str(entry.created_at) if entry.created_at else None,
        "created_by": entry.created_by.email if entry.created_by else None,
        "updated_at": str(entry.updated_at) if entry.updated_at else None,
        "updated_by": entry.updated_by.email if entry.updated_by else None,
    },
    "order": order_data,
    "customer": customer_data,
    "customer_stats": customer_stats,
    "attachments": [
        {
            "id": a.id,
            "filename": a.filename,
            "pdf_type": a.pdf_type,
            "uploaded_at": str(a.uploaded_at) if a.uploaded_at else None,
            "download_url": url_for("rep_traceability.sales_order_pdf_download", attachment_id=a.id),
        }
        for a in attachments
    ],
    "notes": [
        {
            "id": n.id,
            "note_text": n.note_text,
            "created_at": str(n.created_at) if n.created_at else None,
            "created_by": n.created_by.email if n.created_by else None,
        }
        for n in notes
    ],
})
```

**Enhance Modal JS to Render All Info:**
```javascript
// In distribution_log/list.html modal JS:
function renderDistributionDetails(data) {
    let html = '<div class="modal-content">';
    
    // Entry Details Section
    html += '<div class="section-header">Distribution Entry</div>';
    html += `<div><strong>Ship Date:</strong> ${data.entry.ship_date}</div>`;
    html += `<div><strong>Order Number:</strong> ${data.entry.order_number}</div>`;
    html += `<div><strong>Facility:</strong> ${data.entry.facility_name}</div>`;
    html += `<div><strong>SKU:</strong> ${data.entry.sku}</div>`;
    html += `<div><strong>Lot:</strong> ${data.entry.lot_number}</div>`;
    html += `<div><strong>Quantity:</strong> ${data.entry.quantity}</div>`;
    html += `<div><strong>Source:</strong> ${data.entry.source}</div>`;
    if (data.entry.tracking_number) {
        html += `<div><strong>Tracking:</strong> ${data.entry.tracking_number}</div>`;
    }
    
    // Customer Section
    if (data.customer) {
        html += '<div class="section-header">Customer</div>';
        html += `<div><strong>Name:</strong> ${data.customer.facility_name}</div>`;
        html += `<div><strong>Location:</strong> ${data.customer.city}, ${data.customer.state}</div>`;
        if (data.customer_stats) {
            html += `<div><strong>Total Orders:</strong> ${data.customer_stats.total_orders}</div>`;
            html += `<div><strong>Total Units:</strong> ${data.customer_stats.total_units}</div>`;
        }
    }
    
    // Sales Order Section
    if (data.order) {
        html += '<div class="section-header">Linked Sales Order</div>';
        html += `<div><strong>Order #:</strong> ${data.order.order_number}</div>`;
        html += `<div><strong>Date:</strong> ${data.order.order_date}</div>`;
        html += `<a href="/admin/sales-orders/${data.entry.sales_order_id}" class="button button--secondary">View Sales Order</a>`;
    }
    
    // File Slots Section (from Issue 3)
    html += renderFileSlots(data.attachments);
    
    // Notes Section
    if (data.notes && data.notes.length > 0) {
        html += '<div class="section-header">Notes</div>';
        for (const note of data.notes) {
            html += `<div style="margin-bottom:8px; padding:8px; background:var(--panel); border-radius:4px;">`;
            html += `<div>${note.note_text}</div>`;
            html += `<div style="font-size:11px; color:var(--muted); margin-top:4px;">${note.created_by} - ${note.created_at}</div>`;
            html += `</div>`;
        }
    }
    
    // Audit Trail Section
    html += '<div class="section-header">Audit Trail</div>';
    html += `<div><strong>Created:</strong> ${data.entry.created_at} by ${data.entry.created_by || 'System'}</div>`;
    html += `<div><strong>Updated:</strong> ${data.entry.updated_at} by ${data.entry.updated_by || 'System'}</div>`;
    
    html += '</div>';
    return html;
}
```

**Acceptance Criteria:**
- [ ] Distribution detail modal shows all entry fields
- [ ] Customer info visible in modal
- [ ] Sales Order link visible (if matched)
- [ ] File slots visible with upload/download
- [ ] Notes visible
- [ ] Audit trail visible
- [ ] No navigation needed to see all information

---

### Issue 6: Admin Full Editability (P0)

**Problem:** Admin should be able to edit all components without restrictions.

**Current State:**
- RBAC system exists with permissions
- Admin role should have all permissions
- Some edit forms may require "reason" fields (acceptable, but ensure admin can edit)

**Required Verification:**
- Verify admin role has all permissions (`admin.view`, `admin.edit`, `distribution_log.*`, `sales_orders.*`, `customers.*`, etc.)
- Ensure edit forms work for admin
- Ensure delete operations work for admin (with confirmation)

**Files to Verify:**
- `scripts/init_db.py` (permission seeding)
- All `@require_permission` decorators (ensure admin has access)

**Acceptance Criteria:**
- [ ] Admin can edit all distributions
- [ ] Admin can edit all sales orders
- [ ] Admin can edit all customers
- [ ] Admin can delete (with confirmation)
- [ ] No 403 errors for admin user

---

### Issue 7: Data Reset Process Review and Fix (P0)

**Problem:** Data reset process must work correctly for clean system start.

**Current Implementation:**
- Route: `POST /admin/maintenance/reset-all-data`
- Requires: `{"confirm": true, "confirm_phrase": "DELETE ALL DATA"}`
- Deletes: Customers, Distributions, Sales Orders, PDF attachments, etc.

**Required Verification:**
1. **Verify deletion order:** Children before parents (FK constraints)
2. **Verify storage cleanup:** PDF files in storage should be deleted (or at least orphaned files identified)
3. **Verify audit trail:** Reset operation logged
4. **Verify no FK violations:** All deletes succeed without constraint errors
5. **Verify system still works:** After reset, system should be functional (empty but working)

**Files to Review/Change:**
- `app/eqms/admin.py:635` (`maintenance_reset_all_data()`)
- `app/eqms/storage.py` (add storage cleanup if needed)

**Implementation:**

**Enhance Reset to Clean Storage:**
```python
# In maintenance_reset_all_data():
# After deleting all DB records, clean up orphaned storage files
try:
    from app.eqms.storage import storage_from_config
    storage = storage_from_config(current_app.config)
    
    # List all files in distribution_log/ and sales_orders/ prefixes
    # Delete files that no longer have DB records
    # (This is optional - orphaned files don't hurt, but cleanup is nice)
    
    # For now, just log that storage cleanup should be done manually if needed
    current_app.logger.info("Data reset complete. Orphaned storage files may exist and can be cleaned manually if needed.")
except Exception as e:
    current_app.logger.warning(f"Storage cleanup skipped: {e}")
```

**Verify Deletion Order:**
```python
# Current order (verify this is correct):
# 1. ApprovalEml (FK to TracingReport)
# 2. TracingReport
# 3. OrderPdfAttachment (FK to SalesOrder, DistributionLogEntry)
# 4. SalesOrderLine (FK to SalesOrder)
# 5. DistributionLogEntry (FK to SalesOrder, Customer)
# 6. SalesOrder (FK to Customer - RESTRICT constraint!)
# 7. CustomerNote (FK to Customer)
# 8. CustomerRep (FK to Customer)
# 9. Customer
# 10. ShipStationSkippedOrder
# 11. ShipStationSyncRun

# This order should work, but verify RESTRICT constraint on SalesOrder.customer_id
# If RESTRICT, SalesOrder MUST be deleted before Customer
```

**Add Verification After Reset:**
```python
# After commit, verify system is clean
counts_after = {
    "customers": s.query(Customer).count(),
    "distributions": s.query(DistributionLogEntry).count(),
    "sales_orders": s.query(SalesOrder).count(),
}

if any(counts_after.values()):
    current_app.logger.warning(f"Reset incomplete: {counts_after}")
    return jsonify({"error": "Reset incomplete", "remaining": counts_after}), 500

return jsonify({
    "success": True,
    "message": "All data has been reset",
    "deleted": counts_before,
    "verified_clean": True,
})
```

**Acceptance Criteria:**
- [ ] Reset deletes all data without FK violations
- [ ] System still works after reset (empty but functional)
- [ ] Reset operation logged in audit trail
- [ ] Admin can access reset endpoint
- [ ] Confirmation phrase required (safety)

---

## Part 3: PDF Parsing Deep Dive

### Current Parser Analysis

**File:** `app/eqms/modules/rep_traceability/parsers/pdf.py`

**Sales Order Parser (`_parse_silq_sales_order_page`):**
- Looks for: `SO #`, `Order #`, `Order Number`
- Extracts: order number (4-10 digits), order date, customer name, items
- Item pattern: `(2[14-8][0-9]{9})\s+(.+?)\s+(\d+)\s*(?:EA|Each)?`

**Label Parser (`_parse_label_page`):**
- Looks for: tracking number (UPS/FedEx patterns)
- Extracts: tracking number, ship-to name

**Likely Issues:**
1. **Text extraction may fail:** PDFs may be image-based (no text layer)
2. **Regex too strict:** Actual PDF format may differ
3. **No fallback:** If table extraction fails, no text-based fallback
4. **Error visibility:** Errors logged but not shown to user

### Required Fixes

**1. Add Comprehensive Logging:**
```python
import logging
logger = logging.getLogger(__name__)

def parse_sales_orders_pdf(file_bytes: bytes) -> ParseResult:
    logger.info(f"Starting PDF parse, size: {len(file_bytes)} bytes")
    # ... existing code ...
    for page_num, page in enumerate(pdf.pages, start=1):
        text = _normalize_text(page.extract_text() or "")
        logger.info(f"Page {page_num} text length: {len(text)}, preview: {text[:200]}")
        # ... rest of parsing ...
```

**2. Improve Regex Patterns:**
```python
# Make order number more flexible
order_patterns = [
    r'SO\s*#?\s*[:\s]*(\d{4,10})',
    r'Order\s*(?:#|Number|No\.?)?\s*[:\s]*(\d{4,10})',
    r'(?:Sales\s+Order|SO)\s*[:\s]*(\d{4,10})',
    r'(\d{4,10})',  # Last resort: any 4-10 digit number
]

# Make item extraction more flexible
# Try table extraction first (if pdfplumber supports it)
tables = page.extract_tables()
if tables:
    for table in tables:
        # Parse table rows for items
        # Look for SKU column, quantity column, etc.
        pass

# Fallback to text regex
if not items:
    # Use existing regex patterns
    pass
```

**3. Add Text Extraction Diagnostics:**
```python
# If text extraction fails, try OCR hint or return helpful error
if not text.strip():
    # Check if PDF has images
    images = page.images
    if images:
        errors.append(ParseError(
            row_index=page_num,
            message=f"Page {page_num}: Image-based PDF (no text layer). OCR required.",
        ))
    else:
        errors.append(ParseError(
            row_index=page_num,
            message=f"Page {page_num}: No text extracted.",
        ))
```

**4. Improve Label Parsing:**
```python
def _parse_label_page(text: str, page_num: int) -> dict[str, Any] | None:
    # Try multiple tracking number patterns (UPS, FedEx, USPS)
    tracking_patterns = [
        r'(1Z[0-9A-Z]{16,20})',  # UPS
        r'(\d{20,22})',  # FedEx
        r'(\d{12,15})',  # USPS
        r'(9\d{15,21})',  # FedEx alternative
        r'([A-Z]{2}\d{9}[A-Z]{2})',  # International
    ]
    
    tracking = None
    for pattern in tracking_patterns:
        match = re.search(pattern, text)
        if match:
            tracking = match.group(1)
            break
    
    # Extract ship-to (more flexible)
    ship_to_patterns = [
        r'Ship\s+To\s*:?\s*(.+?)(?:\n\n|Ship\s+Date|\Z)',
        r'Delivery\s+To\s*:?\s*(.+?)(?:\n\n|\Z)',
        r'Recipient\s*:?\s*(.+?)(?:\n\n|\Z)',
    ]
    
    ship_to = None
    for pattern in ship_to_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            lines = [l.strip() for l in match.group(1).split('\n') if l.strip()]
            ship_to = lines[0] if lines else None
            break
    
    if tracking:
        return {"tracking_number": tracking, "ship_to": ship_to or "Unknown", "page": page_num}
    return None
```

**5. Show Parse Errors in UI:**
```python
# In sales_orders_import_pdf_bulk():
if result.errors:
    error_messages = [f"Page {e.row_index}: {e.message}" for e in result.errors]
    flash(f"Parse errors: {'; '.join(error_messages[:5])}", "warning")
```

**Acceptance Criteria:**
- [ ] PDF parsing logs extracted text for debugging
- [ ] Parse errors shown clearly in UI
- [ ] Regex patterns handle variations in PDF format
- [ ] Label parsing works for FedEx/UPS/USPS formats
- [ ] Test with `Label1.pdf` and `2025_1SOs.pdf` succeeds

---

## Part 4: Implementation Checklist

### P0 Critical (Must Do First)

- [ ] **P0-1: Fix PDF Parsing**
  - Add comprehensive logging
  - Improve regex patterns
  - Add fallback parsing
  - Show parse errors in UI
  - Test with provided PDFs

- [ ] **P0-2: Multi-SKU Manual Entry**
  - Update form template (repeatable SKU rows)
  - Update route handler (create multiple entries)
  - Add JavaScript for add/remove rows
  - Validate each row individually

- [ ] **P0-3: Two File Slots Per Distribution**
  - Add label upload route
  - Update SO upload route (mark as sales_order type)
  - Update detail modal UI (show both slots)
  - Update bulk import (categorize SO vs label)

- [ ] **P0-4: PDF Download from Detail Views**
  - Verify download route works
  - Add download links to distribution modal
  - Add download links to customer profile

- [ ] **P0-5: Enhanced Detailed Views**
  - Add all fields to distribution detail JSON
  - Update modal JS to render all info
  - Add file slots to modal
  - Add notes to modal
  - Add audit trail to modal

- [ ] **P0-6: Verify Admin Editability**
  - Verify admin has all permissions
  - Test edit operations
  - Test delete operations

- [ ] **P0-7: Fix Data Reset Process**
  - Verify deletion order (no FK violations)
  - Add storage cleanup (optional)
  - Add verification after reset
  - Test reset end-to-end

### P1 High Priority (Do After P0)

- [ ] **P1-1: Improve Error Messages**
  - All errors shown clearly to user
  - Parse errors include page numbers
  - Storage errors include helpful hints

- [ ] **P1-2: Add Validation Feedback**
  - Form validation shows field-level errors
  - Multi-SKU form validates each row
  - Clear error messages for invalid inputs

---

## Part 5: Data Reset Sequence (For Ethan)

### Pre-Reset Checklist

**Before running data reset, verify:**
- [ ] All critical data backed up (if needed)
- [ ] You have admin login credentials
- [ ] System is accessible (not in use)

### Reset Steps (Ethan's Actions)

**Step 1: Access Reset Page**
1. Log in as admin
2. Navigate to: `/admin/reset-data` (or `/admin/maintenance/reset-all-data` via API)
3. Review what will be deleted

**Step 2: Confirm Reset**
1. Type exactly: `DELETE ALL DATA` (case-sensitive)
2. Click "Reset All Data" button
3. Confirm browser dialog

**Step 3: Verify Reset**
1. Check that page shows success message
2. Verify counts show 0 for all entities
3. Navigate to Distribution Log → Should be empty
4. Navigate to Sales Orders → Should be empty
5. Navigate to Customers → Should be empty

**Step 4: Verify System Still Works**
1. Go to `/admin/diagnostics` → Should load without errors
2. Try creating a test distribution → Should work
3. Try importing a test PDF → Should work

### Post-Reset Sequence (Developer Should Implement)

**After reset, system should be ready for:**
1. **ShipStation Sync** (creates unmatched distributions)
2. **PDF Import** (creates Sales Orders + matches distributions)
3. **Manual Entry** (creates distributions with multiple SKUs)

**Expected Flow:**
```
1. Run ShipStation sync → Creates distributions (unmatched)
2. Import Sales Order PDFs → Creates SOs + Customers + matches distributions
3. Upload label PDFs → Links labels to distributions
4. Manual entry (multi-SKU) → Creates multiple distribution entries
5. Sales Dashboard → Shows only matched distributions
```

---

## Part 6: Testing Plan

### Test 1: PDF Parsing with Provided Files

**Test Files:**
- `Label1.pdf` (shipping label)
- `2025_1SOs.pdf` (sales orders)

**Steps:**
1. Go to `/admin/sales-orders/import-pdf`
2. Upload `2025_1SOs.pdf`
3. **Expected:** Sales Orders created, distributions linked
4. Upload `Label1.pdf` (or bulk upload with both)
5. **Expected:** Labels parsed and linked to distributions

**Verification:**
- Check logs for parse errors
- Verify Sales Orders created
- Verify distributions matched
- Verify labels linked

### Test 2: Multi-SKU Manual Entry

**Steps:**
1. Go to `/admin/distribution-log/new`
2. Fill shared fields (date, customer, order number)
3. Add 3 SKU rows:
   - Row 1: 211810SPT, SLQ-12345, Qty 10
   - Row 2: 211610SPT, SLQ-12346, Qty 5
   - Row 3: 211410SPT, SLQ-12347, Qty 3
4. Submit form
5. **Expected:** 3 distribution entries created with same order_number

**Verification:**
- Go to Distribution Log
- Filter by order number
- Should see 3 entries (one per SKU)

### Test 3: Two File Slots

**Steps:**
1. Go to Distribution Log → Click "Details" on any entry
2. **Expected:** See two file slot sections (SO PDF + Label)
3. Upload Sales Order PDF → **Expected:** SO slot shows "✅ Uploaded"
4. Upload Label PDF → **Expected:** Label slot shows "✅ Uploaded"
5. Click Download on each → **Expected:** PDFs download correctly

**Verification:**
- Both slots show status indicators
- Upload buttons work
- Download buttons work
- Files are correct PDFs

### Test 4: Detailed Views Show All Info

**Steps:**
1. Go to Distribution Log → Click "Details"
2. **Expected:** Modal shows:
   - All entry fields
   - Customer info
   - Sales Order link (if matched)
   - File slots
   - Notes
   - Audit trail
3. Go to Customer Profile → **Expected:** Shows all distributions with download links

**Verification:**
- No navigation needed to see all information
- All fields visible
- Links work correctly

### Test 5: Data Reset

**Steps:**
1. Go to `/admin/reset-data`
2. Type "DELETE ALL DATA"
3. Click "Reset All Data"
4. **Expected:** Success message, all counts = 0
5. Verify system still works (create test entry)

**Verification:**
- All data deleted
- System functional after reset
- Can create new entries

---

## Part 7: Files to Change

### Backend Files

1. `app/eqms/modules/rep_traceability/parsers/pdf.py`
   - Improve parsing logic
   - Add logging
   - Improve regex patterns

2. `app/eqms/modules/rep_traceability/admin.py`
   - Update `distribution_log_new_post()` (multi-SKU)
   - Add `distribution_log_upload_label()` route
   - Update `distribution_log_upload_pdf()` (mark as sales_order)
   - Enhance `distribution_log_entry_details()` (all fields)
   - Update `sales_orders_import_pdf_bulk()` (categorize SO vs label)

3. `app/eqms/modules/rep_traceability/service.py`
   - Verify `create_distribution_entry()` works for multiple calls

4. `app/eqms/admin.py`
   - Enhance `maintenance_reset_all_data()` (verification, storage cleanup)

### Frontend Files

1. `app/eqms/templates/admin/distribution_log/new.html` (or create if missing)
   - Add multi-SKU form (repeatable rows)
   - Add JavaScript for add/remove rows

2. `app/eqms/templates/admin/distribution_log/list.html`
   - Enhance modal JS (all fields, file slots, notes, audit trail)

3. `app/eqms/templates/admin/customers/detail.html`
   - Add download links to distributions section

4. `app/eqms/templates/admin/sales_orders/detail.html`
   - Verify shows all info (may already be good)

### Model Files

1. `app/eqms/modules/rep_traceability/models.py`
   - Verify `OrderPdfAttachment.pdf_type` supports required values

---

## Part 8: Definition of Done

**For Each Task:**
- [ ] Code changes implemented
- [ ] Manual browser verification completed
- [ ] PDF parsing tested with provided files
- [ ] Multi-SKU entry tested (3+ SKUs)
- [ ] File slots tested (upload + download)
- [ ] Detailed views show all information
- [ ] Data reset tested end-to-end
- [ ] No regressions (existing functionality works)

**Overall Success Criteria:**
- ✅ PDF parsing works reliably (tested with provided PDFs)
- ✅ Multi-SKU manual entry works (3+ SKUs per order)
- ✅ Two file slots clearly marked and functional
- ✅ PDF downloads work from all detail views
- ✅ All information accessible via detailed views (no navigation)
- ✅ Admin can edit all components
- ✅ Data reset works correctly (clean system start)

---

## Part 9: Developer Autonomy

### Work Autonomously

**The developer should:**
- Implement all changes without asking for clarification (unless absolutely necessary)
- Test changes locally before considering complete
- Make reasonable decisions about UI/UX (consistent with existing design)
- Add logging for debugging (can be removed later if too verbose)
- Document any assumptions made

### Only Ask If:

- **Critical decision required:** Something that affects data integrity or system behavior in a way that can't be inferred
- **Missing information:** Required file/route doesn't exist and needs to be created from scratch
- **Conflicting requirements:** Two requirements contradict each other

### Expected Deliverables

1. **All code changes implemented**
2. **All tests passing** (manual browser verification)
3. **Brief summary** of what was changed and any assumptions made

---

## Part 10: Clean System Sequence

### After Developer Completes Implementation

**Ethan's Sequence for Clean System Start:**

1. **Verify System is Working**
   - Go to `/admin/diagnostics` → Should show all green
   - Verify PDF dependencies installed (pdfplumber, PyPDF2)

2. **Run Data Reset** (if needed)
   - Go to `/admin/reset-data`
   - Type "DELETE ALL DATA"
   - Confirm reset
   - Verify all counts = 0

3. **Test PDF Import**
   - Go to `/admin/sales-orders/import-pdf`
   - Upload `2025_1SOs.pdf`
   - Verify Sales Orders created
   - Verify distributions matched

4. **Test Label Import**
   - Upload `Label1.pdf` (or bulk upload)
   - Verify labels parsed and linked

5. **Test Multi-SKU Manual Entry**
   - Go to `/admin/distribution-log/new`
   - Create entry with 3 SKUs
   - Verify 3 distribution entries created

6. **Test File Slots**
   - Go to Distribution Log → Click "Details"
   - Verify two file slots visible
   - Upload SO PDF → Verify slot shows uploaded
   - Upload label PDF → Verify slot shows uploaded
   - Download both → Verify PDFs download

7. **Test Detailed Views**
   - Click "Details" on any distribution
   - Verify all information visible (no navigation needed)
   - Verify download links work

8. **Verify Sales Dashboard**
   - Go to `/admin/sales-dashboard`
   - Verify only matched distributions counted
   - Verify totals match SQL queries

---

## Part 11: Reference Documents

**Planning Documents:**
- `docs/plans/PHASE3_DATA_CORRECTNESS_AND_PDF_IMPORT.md`
- `docs/plans/DEVELOPER_PROMPT_PDF_IMPORT_FIXES.md`
- `docs/review/SYSTEM_DEBUG_SWEEP_2026_01_27.md`

**System Documentation:**
- `README.md` - Setup guide
- `docs/REP_SYSTEM_MIGRATION_MASTER.md` - Master spec

**Test Files (Provided):**
- `uploads/Label1.pdf` - Shipping label example
- `uploads/2025_1SOs.pdf` - Sales orders example

---

**End of Developer Prompt**
