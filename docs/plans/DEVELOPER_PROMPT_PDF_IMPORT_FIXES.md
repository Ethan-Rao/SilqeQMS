# Developer Prompt: PDF Import Failure Diagnosis and Fixes

**Date:** 2026-01-27  
**Priority:** P0 (Critical)  
**Scope:** Fix PDF import failures (bulk and single-file), add comprehensive error handling and logging.

---

## Problem Statement

**Observed Behavior:**
- User accessed `/admin/sales-orders/import-pdf-bulk` at 17:11:59
- No POST request appears in logs after page load
- No error messages visible to user
- PDF import appears to fail silently

**Likely Failure Modes:**
1. **Client-side failure:** Form submission blocked (JavaScript error, file size limit, browser issue)
2. **Early server-side failure:** Request rejected before route handler (413 Payload Too Large, 400 Bad Request)
3. **Route handler failure:** Exception thrown but not logged/caught (500 Internal Server Error not visible)
4. **Missing dependencies:** `pdfplumber` or `PyPDF2` not installed in production

---

## Root Cause Analysis

### Current Code Issues

**File:** `app/eqms/modules/rep_traceability/admin.py:1361` (`sales_orders_import_pdf_bulk()`)

**Issue 1: No Request Size Validation**
- Flask default `MAX_CONTENT_LENGTH` may be too small for bulk PDF uploads
- No explicit size check before processing
- Large files may be rejected with 413 before route handler executes

**Issue 2: Missing Error Handling**
- PDF parsing errors not caught (line 1379: `parse_sales_orders_pdf(pdf_bytes)`)
- PDF splitting errors not caught (if `split_pdf_into_pages()` called)
- Customer creation errors not caught (line 1413: `find_or_create_customer()`)
- Database errors not caught (line 1452: `s.commit()`)

**Issue 3: Silent Failures**
- Exceptions may be logged but not shown to user
- Flash messages may not appear if exception occurs before `flash()`
- No user-visible error feedback

**Issue 4: Missing Dependency Checks**
- Route assumes `pdfplumber` and `PyPDF2` are installed
- No graceful fallback if dependencies missing
- Import errors may cause route to fail entirely

---

## Required Fixes

### P0-1: Add Request Size Validation and Error Handling

**File:** `app/eqms/modules/rep_traceability/admin.py`

**Change 1: Add size validation at route start**
```python
@bp.post("/sales-orders/import-pdf-bulk")
@require_permission("sales_orders.import")
def sales_orders_import_pdf_bulk():
    """Bulk PDF import (multiple files)."""
    from flask import jsonify
    import logging
    logger = logging.getLogger(__name__)
    
    s = db_session()
    u = _current_user()
    
    # Validate request has files
    files = request.files.getlist("pdf_files")
    if not files or not any(f.filename for f in files if f):
        flash("Please select one or more PDF files to upload.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    # Validate file sizes (10MB per file, 50MB total)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB
    total_size = 0
    
    for f in files:
        if not f or not f.filename:
            continue
        # Read file to check size
        f.seek(0, 2)  # Seek to end
        file_size = f.tell()
        f.seek(0)  # Reset to start
        
        if file_size > MAX_FILE_SIZE:
            flash(f"File '{f.filename}' is too large ({file_size / 1024 / 1024:.1f}MB). Maximum size is {MAX_FILE_SIZE / 1024 / 1024}MB per file.", "danger")
            return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
        
        total_size += file_size
    
    if total_size > MAX_TOTAL_SIZE:
        flash(f"Total upload size ({total_size / 1024 / 1024:.1f}MB) exceeds maximum ({MAX_TOTAL_SIZE / 1024 / 1024}MB).", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    # Validate dependencies
    try:
        import pdfplumber
        import PyPDF2
    except ImportError as e:
        logger.error(f"PDF dependencies missing: {e}", exc_info=True)
        flash("PDF parsing libraries are not installed. Please contact support.", "danger")
        return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
    
    # Process files with comprehensive error handling
    total_orders = 0
    total_errors = 0
    total_pages = 0
    total_unmatched = 0
    skipped_duplicates = 0
    
    try:
        for f in files:
            if not f or not f.filename:
                continue
            
            try:
                pdf_bytes = f.read()
                if not pdf_bytes:
                    logger.warning(f"Empty file: {f.filename}")
                    total_errors += 1
                    continue
                
                # Split PDF into pages
                try:
                    from app.eqms.modules.rep_traceability.parsers.pdf import split_pdf_into_pages, parse_sales_orders_pdf
                    pages = split_pdf_into_pages(pdf_bytes)
                    total_pages += len(pages)
                except Exception as e:
                    logger.error(f"PDF split failed for {f.filename}: {e}", exc_info=True)
                    # Store entire PDF as unmatched
                    _store_pdf_attachment(
                        s,
                        pdf_bytes=pdf_bytes,
                        filename=f.filename,
                        pdf_type="unparsed",
                        sales_order_id=None,
                        distribution_entry_id=None,
                        user=u,
                    )
                    total_errors += 1
                    total_unmatched += 1
                    continue
                
                # Process each page
                for page_num, page_bytes in pages:
                    try:
                        result = parse_sales_orders_pdf(page_bytes)
                    except Exception as e:
                        logger.error(f"PDF parse failed for {f.filename} page {page_num}: {e}", exc_info=True)
                        # Store page as unmatched
                        _store_pdf_attachment(
                            s,
                            pdf_bytes=page_bytes,
                            filename=f"{f.filename}_page_{page_num}.pdf",
                            pdf_type="unmatched",
                            sales_order_id=None,
                            distribution_entry_id=None,
                            user=u,
                        )
                        total_errors += 1
                        total_unmatched += 1
                        continue
                    
                    # Process parsed orders
                    if not result.orders:
                        # No orders parsed - store as unmatched
                        _store_pdf_attachment(
                            s,
                            pdf_bytes=page_bytes,
                            filename=f"{f.filename}_page_{page_num}.pdf",
                            pdf_type="unmatched",
                            sales_order_id=None,
                            distribution_entry_id=None,
                            user=u,
                        )
                        total_unmatched += 1
                        continue
                    
                    for order_data in result.orders:
                        try:
                            order_number = order_data.get("order_number")
                            if not order_number:
                                logger.warning(f"Order data missing order_number: {order_data}")
                                total_errors += 1
                                continue
                            
                            order_date = order_data.get("order_date")
                            if not order_date:
                                logger.warning(f"Order data missing order_date: {order_data}")
                                total_errors += 1
                                continue
                            
                            customer_name = order_data.get("customer_name") or "UNKNOWN"
                            
                            # Create or find customer
                            try:
                                from app.eqms.modules.customer_profiles.service import find_or_create_customer
                                customer = find_or_create_customer(
                                    s,
                                    facility_name=customer_name,
                                    address1=order_data.get("address1"),
                                    city=order_data.get("city"),
                                    state=order_data.get("state"),
                                    zip=order_data.get("zip"),
                                )
                            except Exception as e:
                                logger.error(f"Customer creation failed for {customer_name}: {e}", exc_info=True)
                                total_errors += 1
                                continue
                            
                            # Check for existing order
                            external_key = f"pdf:{order_number}:{order_date.isoformat()}"
                            existing_order = (
                                s.query(SalesOrder)
                                .filter(SalesOrder.source == "pdf_import", SalesOrder.external_key == external_key)
                                .first()
                            )
                            if existing_order:
                                skipped_duplicates += 1
                                continue
                            
                            # Create sales order
                            try:
                                sales_order = SalesOrder(
                                    order_number=order_number,
                                    order_date=order_date,
                                    ship_date=order_data.get("ship_date") or order_date,
                                    customer_id=customer.id,
                                    source="pdf_import",
                                    external_key=external_key,
                                    status="completed",
                                    created_by_user_id=u.id,
                                    updated_by_user_id=u.id,
                                )
                                s.add(sales_order)
                                s.flush()
                                total_orders += 1
                            except Exception as e:
                                logger.error(f"Sales order creation failed for {order_number}: {e}", exc_info=True)
                                s.rollback()
                                total_errors += 1
                                continue
                            
                            # Store PDF attachment
                            try:
                                _store_pdf_attachment(
                                    s,
                                    pdf_bytes=page_bytes,
                                    filename=f"{f.filename}_page_{page_num}.pdf",
                                    pdf_type="sales_order_page",
                                    sales_order_id=sales_order.id,
                                    distribution_entry_id=None,
                                    user=u,
                                )
                            except Exception as e:
                                logger.error(f"PDF attachment storage failed for {order_number}: {e}", exc_info=True)
                                # Non-fatal - continue
                            
                            # Auto-match distributions
                            try:
                                unmatched_dists = (
                                    s.query(DistributionLogEntry)
                                    .filter(
                                        DistributionLogEntry.order_number == order_number,
                                        DistributionLogEntry.sales_order_id.is_(None)
                                    )
                                    .all()
                                )
                                for udist in unmatched_dists:
                                    udist.sales_order_id = sales_order.id
                                    udist.customer_id = customer.id
                            except Exception as e:
                                logger.error(f"Distribution matching failed for {order_number}: {e}", exc_info=True)
                                # Non-fatal - continue
                            
                        except Exception as e:
                            logger.error(f"Order processing failed: {e}", exc_info=True)
                            total_errors += 1
                            continue
                
            except Exception as e:
                logger.error(f"File processing failed for {f.filename}: {e}", exc_info=True)
                total_errors += 1
                continue
        
        # Commit all changes
        try:
            s.commit()
        except Exception as e:
            logger.error(f"Database commit failed: {e}", exc_info=True)
            s.rollback()
            flash("Database error occurred. Some data may not have been saved.", "danger")
            return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
        
        # Success message
        msg = f"Bulk PDF import completed: {total_pages} pages processed, {total_orders} orders created."
        if skipped_duplicates:
            msg += f" {skipped_duplicates} duplicates skipped."
        if total_unmatched:
            msg += f" {total_unmatched} pages could not be parsed (stored as unmatched)."
        if total_errors:
            msg += f" {total_errors} errors occurred (check logs for details)."
        
        flash(msg, "success" if total_errors == 0 else "warning")
        
    except Exception as e:
        logger.error(f"Bulk PDF import failed: {e}", exc_info=True)
        s.rollback()
        flash(f"Import failed: {str(e)}. Please check logs for details.", "danger")
    
    return redirect(url_for("rep_traceability.sales_orders_import_pdf_get"))
```

### P0-2: Add Flask Request Size Configuration

**File:** `app/eqms/__init__.py` (or wherever Flask app is created)

**Change:** Set `MAX_CONTENT_LENGTH` to allow larger uploads:
```python
def create_app():
    app = Flask(__name__)
    # ... existing config ...
    
    # Allow up to 50MB uploads (for bulk PDF imports)
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
    
    # ... rest of app setup ...
```

**Alternative:** If using nginx/gunicorn, configure there instead:
- Nginx: `client_max_body_size 50M;`
- Gunicorn: No direct config, but Flask setting should work

### P0-3: Add Client-Side Validation and Feedback

**File:** `app/eqms/templates/admin/sales_orders/import.html`

**Change:** Add JavaScript validation and better error display:
```html
<script>
document.addEventListener('DOMContentLoaded', function() {
    const bulkForm = document.querySelector('form[action*="import-pdf-bulk"]');
    if (bulkForm) {
        bulkForm.addEventListener('submit', function(e) {
            const files = this.querySelector('input[type="file"]').files;
            const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
            const MAX_TOTAL_SIZE = 50 * 1024 * 1024; // 50MB
            let totalSize = 0;
            
            for (let i = 0; i < files.length; i++) {
                if (files[i].size > MAX_FILE_SIZE) {
                    e.preventDefault();
                    alert(`File "${files[i].name}" is too large (${(files[i].size / 1024 / 1024).toFixed(1)}MB). Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB per file.`);
                    return false;
                }
                totalSize += files[i].size;
            }
            
            if (totalSize > MAX_TOTAL_SIZE) {
                e.preventDefault();
                alert(`Total upload size (${(totalSize / 1024 / 1024).toFixed(1)}MB) exceeds maximum (${MAX_TOTAL_SIZE / 1024 / 1024}MB).`);
                return false;
            }
            
            // Show loading indicator
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Uploading...';
            }
        });
    }
});
</script>
```

### P0-4: Add Structured Logging

**File:** `app/eqms/modules/rep_traceability/admin.py` (at module level)

**Change:** Ensure logger is configured:
```python
import logging
logger = logging.getLogger(__name__)
```

**File:** `scripts/start.py` (or app config)

**Change:** Configure logging to write to file and stderr:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/eqms.log'),
        logging.StreamHandler()  # Also log to stderr (captured by DO)
    ]
)
```

### P0-5: Add Health Check for Dependencies

**File:** `app/eqms/routes.py` (or create new diagnostic route)

**Change:** Add dependency check endpoint:
```python
@bp.get("/admin/diagnostics")
@require_permission("admin.view")
def diagnostics():
    """Diagnostic information for troubleshooting."""
    diagnostics = {
        "pdfplumber": False,
        "PyPDF2": False,
        "pdfplumber_version": None,
        "PyPDF2_version": None,
    }
    
    try:
        import pdfplumber
        diagnostics["pdfplumber"] = True
        diagnostics["pdfplumber_version"] = getattr(pdfplumber, "__version__", "unknown")
    except ImportError:
        pass
    
    try:
        import PyPDF2
        diagnostics["PyPDF2"] = True
        diagnostics["PyPDF2_version"] = getattr(PyPDF2, "__version__", "unknown")
    except ImportError:
        pass
    
    return render_template("admin/diagnostics.html", diagnostics=diagnostics)
```

---

## Testing Plan

### Test 1: Large File Upload
1. Create a 15MB PDF file
2. Attempt to upload via bulk import
3. **Expected:** Error message shown: "File is too large (15.0MB). Maximum size is 10MB per file."

### Test 2: Missing Dependencies
1. Temporarily remove `pdfplumber` from environment
2. Attempt to upload PDF
3. **Expected:** Error message: "PDF parsing libraries are not installed. Please contact support."

### Test 3: Corrupted PDF
1. Create a corrupted/invalid PDF file
2. Attempt to upload via bulk import
3. **Expected:** PDF stored as "unparsed", error logged, success message shows "X pages could not be parsed"

### Test 4: Valid PDF Upload
1. Upload a valid multi-page PDF with orders
2. **Expected:** Orders created, distributions matched, success message shows counts

### Test 5: Database Error
1. Simulate database error (e.g., duplicate key)
2. **Expected:** Error logged, rollback performed, user sees error message

---

## Acceptance Criteria

- [ ] Bulk PDF import handles file size limits (10MB per file, 50MB total)
- [ ] Missing dependencies detected and user-friendly error shown
- [ ] All exceptions caught and logged with stack traces
- [ ] User sees clear error messages for all failure modes
- [ ] Unmatched/unparsed PDFs stored for later review
- [ ] Success message shows accurate counts (pages, orders, errors, unmatched)
- [ ] Client-side validation prevents oversized uploads
- [ ] Logs contain detailed error information for debugging

---

## Files to Change

1. `app/eqms/modules/rep_traceability/admin.py` - Add error handling to `sales_orders_import_pdf_bulk()`
2. `app/eqms/__init__.py` - Add `MAX_CONTENT_LENGTH` config
3. `app/eqms/templates/admin/sales_orders/import.html` - Add client-side validation
4. `scripts/start.py` - Configure structured logging (if not already)
5. `app/eqms/routes.py` - Add diagnostics endpoint (optional, P1)

---

## Deployment Notes

**DigitalOcean:**
- No environment variable changes required
- Ensure `pdfplumber` and `PyPDF2` are in `requirements.txt` and installed
- Verify logs are accessible via DO dashboard or CLI

**Verification:**
1. Check logs after deploy for any import errors
2. Test bulk upload with valid PDF
3. Test bulk upload with oversized file (should show error)
4. Check diagnostics endpoint (if added) to verify dependencies

---

**End of Developer Prompt**
