# Phase 3 Implementation Notes

## Summary

Phase 3 focused on data correctness and PDF import improvements, ensuring the Sales Dashboard and related features only process properly matched data.

## Files Changed

### P0-1: Fix Sales Dashboard to Use Only Matched Sales Orders
- **File**: `app/eqms/modules/rep_traceability/service.py`
- **Change**: Added `.filter(DistributionLogEntry.sales_order_id.isnot(None))` to all queries in `compute_sales_dashboard()`:
  - `lifetime_rows` query
  - `window_entries` query (windowed metrics)
  - `total_units_all_time` query
  - `all_entries` query (lot tracking)
  - `orders_by_order_number` loop now skips entries without `sales_order_id`

### P0-2: Verify ShipStation Sync Does Not Create Customers
- **File**: `app/eqms/modules/shipstation_sync/service.py`
- **Status**: Already fixed in Phase 2. ShipStation sync only finds existing customers, never creates them.

### P0-3: Fix PDF Import Error Handling
- **File**: `app/eqms/modules/rep_traceability/admin.py`
- **Change**: Added comprehensive `try-except` blocks around:
  - `split_pdf_into_pages()` calls
  - `parse_sales_orders_pdf()` calls
  - Customer creation in PDF imports
- **Behavior**: Unparsed/failed pages stored as `pdf_type="unparsed"` or `pdf_type="unmatched"`

### P0-4: Fix Single-Page PDF Upload from Distribution Detail
- **File**: `app/eqms/modules/rep_traceability/admin.py`
- **Function**: `distribution_log_upload_pdf()`
- **Change**: If `entry.customer_id` is None, creates customer from parsed PDF data or entry's facility_name before creating SalesOrder

### P0-5: Add Label PDF Upload Route
- **File**: `app/eqms/modules/rep_traceability/admin.py`
- **Route**: `POST /admin/distribution-log/<id>/upload-label`
- **Behavior**: Stores label PDFs as `pdf_type="shipping_label"` linked to distribution

### P1-1: Customer Deduplication Script
- **File**: `scripts/dedupe_customers.py`
- **Commands**:
  - `python scripts/dedupe_customers.py --list` - List candidates
  - `python scripts/dedupe_customers.py --merge --master=X --duplicate=Y` - Merge pair
  - `python scripts/dedupe_customers.py --merge-strong --confirm` - Merge all strong matches

### P1-2: Cleanup Zero-Order Customers
- **File**: `scripts/cleanup_zero_order_customers.py`
- **Status**: Already exists and working. Use with `--delete` flag to remove customers with no orders.

### P1-3: Fix Customer Creation Race Condition
- **File**: `app/eqms/modules/customer_profiles/service.py`
- **Function**: `find_or_create_customer()`
- **Change**: Added `try-except IntegrityError` with SAVEPOINT (`begin_nested()`) for retry logic

### P1-4: Fix Distribution Detail Attachments
- **File**: `app/eqms/modules/rep_traceability/admin.py`
- **Function**: `distribution_log_entry_details()`
- **Change**: Query attachments using `or_(sales_order_id, distribution_entry_id)` to show both SO-level and distribution-level attachments

## DB Migrations

No new migrations were required for Phase 3. All schema is already in place from previous phases.

## How to Run Maintenance Scripts

### Dedupe Customers
```bash
# List potential duplicates (dry run)
python scripts/dedupe_customers.py --list

# Merge specific pair
python scripts/dedupe_customers.py --merge --master=123 --duplicate=456

# Merge all strong matches (careful!)
python scripts/dedupe_customers.py --merge-strong --confirm
```

### Cleanup Zero-Order Customers
```bash
# List customers with no orders (dry run)
python scripts/cleanup_zero_order_customers.py

# Actually delete them
python scripts/cleanup_zero_order_customers.py --delete
```

## Manual Verification Steps

1. **Sales Dashboard Only Shows Matched Data**
   - Go to `/admin/sales-dashboard`
   - Verify totals match only distributions with linked Sales Orders
   - Check lot tracking shows only matched distributions

2. **PDF Import Error Handling**
   - Upload a malformed PDF at `/admin/sales-orders/import-pdf`
   - Verify no crash, pages stored as "unmatched"
   - Check `/admin/sales-orders/unmatched-pdfs` for stored pages

3. **Distribution Detail Shows All Attachments**
   - View a distribution with both SO PDF and label PDF
   - Click "Details" modal
   - Verify both attachments appear

4. **Customer Race Condition**
   - Concurrent PDF imports should not crash with "duplicate company_key"
   - Check logs for any IntegrityError that was successfully retried

## Data Invariants (from spec)

1. **INVARIANT 1**: Customer profile exists only after Sales Order links to it
2. **INVARIANT 2**: Sales Dashboard aggregates ONLY from `sales_order_id IS NOT NULL`
3. **INVARIANT 3**: Distribution Log entries can exist without Sales Order (ShipStation raw)
4. **INVARIANT 4**: Sales Order is the source of truth for customer identity
5. **INVARIANT 5**: Label PDFs link to distribution, not necessarily to Sales Order
