# DEV AGENT: Critical System Fixes — March 10, 2026

> **Priority**: CRITICAL  
> **Scope**: Customer naming, NRE classification, PDF storage/naming, inventory tracking, admin docs  
> **After completing all changes**: Run verification, then `git add -A && git commit -m "fix: critical customer naming, NRE classification, inventory tracking, PDF handling, admin docs" && git push`

---

## TABLE OF CONTENTS

1. [Issue 1: NRE Mislabeling — All Orders Showing as NRE](#issue-1)
2. [Issue 2: Customer Names Must Come From Sold To Field](#issue-2)
3. [Issue 3: PDF Naming — Use Sales Order Number, Not Bulk Filename](#issue-3)
4. [Issue 4: Customer Address Not Populating From Sales Orders](#issue-4)
5. [Issue 5: NRE Tab — PDFs Not Found in Storage](#issue-5)
6. [Issue 6: Customer Profile — PDF Download on Sales Orders Tab](#issue-6)
7. [Issue 7: Sales Dashboard — Replace "Current Lot" With Per-Lot Tracking](#issue-7)
8. [Issue 8: Lot Name Correction — ShipStation Typos](#issue-8)
9. [Issue 9: Admin Docs — Root Folder Designation for Uploaded Files](#issue-9)
10. [Verification Checklist](#verification)

---

<a name="issue-1"></a>
## Issue 1: NRE Mislabeling — All Orders Showing as NRE

### Problem
ALL customers are showing up labeled as "NRE" in the system, even customers with catheter orders that have matched ShipStation distributions. The NRE Projects page (`/admin/nre-projects`) is defined as "customers with sales orders but no distributions." However, when new catheter sales orders are imported via PDF and auto-matched to ShipStation distributions, the customer still appears in NRE Projects because the NRE classification is based on whether the customer has **any** distribution entries — not whether the **specific** sales order matched.

**Root Cause**: The NRE Projects query in `app/eqms/modules/nre_projects/admin.py` lines 34-53 finds customers who have sales orders but NO distributions at all. This is incorrect because:
1. A customer may have a catheter sales order that was just imported but the ShipStation distribution hasn't been synced yet.
2. The `_is_catheter_order()` function in `app/eqms/modules/rep_traceability/admin.py` line 153-157 determines NRE based on whether the order has catheter SKUs. But if the PDF parser fails to extract any line items, the order will have 0 lines and `_is_catheter_order()` returns `False` (flagging it as NRE incorrectly).
3. The auto-match logic only runs for non-NRE orders (line 2163: `if not is_nre:`), so incorrectly classified NRE orders never get matched.

### Required Changes

#### A. Fix NRE Classification Logic  
**File**: `app/eqms/modules/rep_traceability/admin.py`

The `_is_catheter_order()` function currently checks if any line SKU matches catheter SKUs. This is too fragile — if the PDF parser fails to extract lines, the order is flagged NRE.

**Change**: An order should be classified as NRE ONLY if it has NO catheter SKUs AND has at least one non-catheter line item (like NRE service charges). If the order has NO lines at all, it should NOT be classified as NRE — it should be treated as a catheter order with a parse error.

```python
def _is_catheter_order(order_data: dict) -> bool:
    """
    Determine if a sales order is a catheter order.
    
    Rules:
    - If ANY line has a catheter SKU -> catheter order (True)
    - If order has NO lines at all -> assume catheter (True) — parse error, not NRE
    - If order has lines but NONE are catheter SKUs -> NRE (False)
    """
    lines = order_data.get("lines", [])
    if not lines:
        return True  # No lines = assume catheter (parse may have failed)
    for line in lines:
        if line.get("sku") in {"211810SPT", "211610SPT", "211410SPT"}:
            return True
    return False
```

#### B. Always Attempt Auto-Match (Remove NRE Skip)  
**File**: `app/eqms/modules/rep_traceability/admin.py`, around line 2163

Currently, auto-matching only runs `if not is_nre`. Change this so auto-matching runs for ALL orders. Even if an order is classified as NRE, it might still match a ShipStation distribution (the user said "NRE projects are those with sales orders that DO NOT match any shipstation orders"). The NRE classification should be a RESULT of not matching, not a CAUSE of skipping the match attempt.

**Change**: Remove the `if not is_nre:` guard around the auto-match block. Always attempt to match.

```python
# REMOVE: if not is_nre:
# Auto-match existing ShipStation distributions to this sales order (ALWAYS attempt)
from app.eqms.modules.rep_traceability.service import match_distribution_to_sales_order, normalize_order_number

normalized_order = normalize_order_number(order_number)
unmatched_q = (
    s.query(DistributionLogEntry)
    .filter(
        DistributionLogEntry.source == "shipstation",
        DistributionLogEntry.sales_order_id.is_(None),
    )
)
if normalized_order:
    unmatched_q = unmatched_q.filter(DistributionLogEntry.order_number.ilike(f"%{normalized_order}%"))
unmatched_dists = unmatched_q.all()
for udist in unmatched_dists:
    match_distribution_to_sales_order(s, udist, sales_order)
```

Also remove the `notes="NRE Project" if is_nre else None` from the SalesOrder creation. NRE classification should be dynamic (based on whether the customer has matched distributions), not static metadata.

#### C. Fix NRE Projects Query  
**File**: `app/eqms/modules/nre_projects/admin.py`

The NRE Projects dashboard should show customers whose sales orders have **no matched ShipStation distributions**. Currently it checks if the customer has ANY distributions at all. It should instead check whether the customer's sales orders are matched to distributions.

**Change the query**: A customer is an NRE project if they have at least one sales order AND none of their sales orders are linked to any distribution log entry via `sales_order_id`.

```python
@bp.get("/")
@require_permission("sales_orders.view")
def nre_projects_index():
    """
    NRE Projects dashboard.
    Shows customers whose sales orders have NO matched ShipStation distributions.
    A customer is NRE if: they have sales orders, but NONE of those sales orders
    are referenced by any distribution_log_entry.sales_order_id.
    """
    s = db_session()

    # Customers that have at least one sales order
    customers_with_orders = (
        s.query(Customer.id)
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .distinct()
        .subquery()
    )

    # Customers that have at least one sales order matched to a distribution
    customers_with_matched_distributions = (
        s.query(Customer.id)
        .join(SalesOrder, SalesOrder.customer_id == Customer.id)
        .join(DistributionLogEntry, DistributionLogEntry.sales_order_id == SalesOrder.id)
        .distinct()
        .subquery()
    )

    nre_customers = (
        s.query(Customer)
        .filter(Customer.id.in_(customers_with_orders))
        .filter(~Customer.id.in_(customers_with_matched_distributions))
        .order_by(Customer.facility_name.asc())
        .all()
    )
    # ... rest stays the same
```

---

<a name="issue-2"></a>
## Issue 2: Customer Names Must Come From Sold To Field

### Problem
Customer names are showing as things like "NRE - ASPIRUS" instead of the actual name from the Sold To field (e.g., "Aspirus Medical Group"). The PDF parser at `app/eqms/modules/rep_traceability/parsers/pdf.py` line 365-373 uses `_parse_sold_to_block()` correctly but falls back to `NRE - {customer_code}` when parsing fails.

The issue is the fallback at line 370 creates customer names with "NRE -" prefix. This is wrong. The customer name should ALWAYS come from the first line of the "Sold To" block of the PDF.

### Required Changes

#### A. Fix Fallback Customer Name Logic  
**File**: `app/eqms/modules/rep_traceability/parsers/pdf.py`, function `_parse_silq_sales_order_page`, around lines 365-373

The current code:
```python
customer_name = _parse_sold_to_block(text)
if not customer_name or customer_name.strip() == "":
    if customer_code:
        customer_name = f"NRE - {customer_code}"
    else:
        customer_name = f"NRE Order {order_number}"
```

**Change to**: Never prefix "NRE -" in the customer name. Use the customer_code or Bill To name as fallback. If Sold To fails, try Bill To. If both fail, use customer code without prefix.

```python
customer_name = _parse_sold_to_block(text)

# Fallback: try Bill To name if Sold To fails
if not customer_name or customer_name.strip() == "":
    customer_name = bill_to.get("bill_to_name")

# Fallback: use customer code as plain name (NO "NRE -" prefix)
if not customer_name or customer_name.strip() == "":
    if customer_code:
        customer_name = customer_code  # e.g., "ASPIRUS" — NOT "NRE - ASPIRUS"
    else:
        customer_name = f"Order {order_number}"
```

**NOTE**: Move the `bill_to = _parse_bill_to_block(text)` call BEFORE the customer_name resolution so it's available as fallback. Currently `bill_to` is parsed after `customer_name` is set (line 374). Move lines 374-376 (bill_to, ship_to, contact_email parsing) above line 365.

#### B. Also Fix the _parse_sold_to_block Parser
**File**: `app/eqms/modules/rep_traceability/parsers/pdf.py`, function `_parse_sold_to_block`

Looking at the actual PDF content (e.g., `SO_Sales Order February.pdf_page_10.pdf`):
```
SOLD TO:
Aspirus Medical Group
Aspirus Urology Clinic
3300 Westhill Drive
Wausau, WI 54401
```

The function should return "Aspirus Medical Group" (first non-address line). Review the regex `Sold\s*To\s*[:\n]` — it should handle the `SOLD TO:` format in the actual PDFs. The current implementation looks correct but verify it works with real PDF text extraction output.

Also ensure the "Sold To" regex termination is not too aggressive. The current stopper `(?=\n\s*\n|Ship\s*To|Salesperson:|$)` may clip the block too early if there's no blank line between Sold To and Ship To in the extracted text.

---

<a name="issue-3"></a>
## Issue 3: PDF Naming — Use Sales Order Number, Not Bulk Filename

### Problem
When bulk importing PDFs, the parsed page PDFs are named `{original_filename}_page_{page_num}.pdf` (e.g., `SO_Sales Order February.pdf_page_10.pdf`). They should be renamed according to their sales order number (e.g., `SO_0000299.pdf`).

### Required Changes

**File**: `app/eqms/modules/rep_traceability/admin.py`

In the `sales_orders_import_pdf_bulk()` function, every call to `_store_and_track()` or `_store_pdf_attachment()` uses `filename=f"{original_filename}_page_{page_num}.pdf"`. After the order number is parsed, the filename should be based on the order number.

Find all occurrences of:
```python
filename=f"{original_filename}_page_{page_num}.pdf"
```

And change them as follows:

1. **For successfully parsed orders** (around line 2182-2189): Use the order number:
```python
filename=f"SO_{order_number}.pdf"
```

2. **For duplicate/existing orders** (around line 2132-2140): Use the existing order's order number:
```python
filename=f"SO_{existing_order.order_number}.pdf"
```

3. **For unparsed/unmatched/label pages**: Keep the original naming (`{original_filename}_page_{page_num}.pdf`) since there's no order number to use.

Also update the `OrderPdfAttachment.filename` field — this is what's displayed to the user. Make sure the attachment record stores the new name.

---

<a name="issue-4"></a>
## Issue 4: Customer Address Not Populating From Sales Orders

### Problem
Many customers have matched sales orders but no location (city, state) listed in the Customers page. The PDF parser extracts address data from both Sold To and Ship To blocks, but this data may not be propagating to the Customer record correctly.

### Root Cause Analysis
In `app/eqms/modules/rep_traceability/admin.py` around line 2106-2116, `find_or_create_customer` is called with:
```python
customer = find_or_create_customer(
    s,
    facility_name=customer_name,
    customer_code=customer_code,
    address1=order_data.get("address1") or order_data.get("ship_to_address1"),
    city=order_data.get("city") or order_data.get("ship_to_city"),
    state=order_data.get("state") or order_data.get("ship_to_state"),
    zip=order_data.get("zip") or order_data.get("ship_to_zip"),
    ...
)
```

The address fields in `order_data` are sourced from `_parse_bill_to_block()` (bill_to_city, etc.) and `_parse_ship_to_block()` (ship_to_city, etc.). The PDF parser returns:
- `order_data["city"]` = `bill_to.get("bill_to_city")` 
- `order_data["ship_to_city"]` = `ship_to.get("ship_to_city")`

The `_parse_bill_to_block()` and `_parse_ship_to_block()` use a city/state/zip regex that may be too strict. It requires:
```regex
^([A-Za-z\s\.]+)[,\s]+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)
```

This requires the state abbreviation to be uppercase in the extracted text, which should be fine. But the `_parse_sold_to_block` function only returns a name — NOT an address. So when the Sold To block contains address info, it's not being captured for the customer address.

### Required Changes

#### A. Improve Address Extraction
**File**: `app/eqms/modules/rep_traceability/parsers/pdf.py`

Add a new function `_parse_sold_to_address()` that extracts address data (address1, city, state, zip) from the Sold To block, similar to how `_parse_bill_to_block()` works:

```python
def _parse_sold_to_address(text: str) -> dict[str, str | None]:
    """Parse address from SOLD TO block."""
    result = {
        "sold_to_address1": None,
        "sold_to_city": None,
        "sold_to_state": None,
        "sold_to_zip": None,
    }
    
    sold_to_match = re.search(
        r"Sold\s*To\s*[:\n](.+?)(?=\n\s*\n|Ship\s*To|Salesperson:|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not sold_to_match:
        return result
    
    lines = [l.strip() for l in sold_to_match.group(1).strip().split("\n") if l.strip()]
    
    for line in lines:
        if re.match(r"^\d+\s+\w", line) or any(
            x in line.lower()
            for x in ["street", "st.", "ave", "blvd", "road", "rd.", "drive", "dr.", "lane", "ln.", "suite", "ste"]
        ):
            result["sold_to_address1"] = line
            break
    
    city_state_zip_pattern = re.compile(
        r"^([A-Za-z\s\.]+)[,\s]+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)(?:\s+[A-Z]{2})?$"
    )
    for line in lines:
        match = city_state_zip_pattern.match(line)
        if match:
            result["sold_to_city"] = match.group(1).strip()
            result["sold_to_state"] = match.group(2)
            result["sold_to_zip"] = match.group(3)
            break
    
    return result
```

#### B. Use Sold To Address as Primary, Bill To / Ship To as Fallback
**File**: `app/eqms/modules/rep_traceability/parsers/pdf.py`, in `_parse_silq_sales_order_page()`

Call `_parse_sold_to_address()` and use it as the primary address source in the returned dict:

```python
sold_to_addr = _parse_sold_to_address(text)

return {
    ...
    "address1": sold_to_addr.get("sold_to_address1") or bill_to.get("bill_to_address1"),
    "city": sold_to_addr.get("sold_to_city") or bill_to.get("bill_to_city"),
    "state": sold_to_addr.get("sold_to_state") or bill_to.get("bill_to_state"),
    "zip": sold_to_addr.get("sold_to_zip") or bill_to.get("bill_to_zip"),
    ...
}
```

This ensures the Sold To address (which corresponds to the customer's billing address) is used as the primary location for the customer record.

---

<a name="issue-5"></a>
## Issue 5: NRE Tab — PDFs Not Found in Storage

### Problem
On the NRE customer detail page, clicking "View" on a PDF attachment shows "PDF not found in storage." The download uses `storage.get_bytes()` while the view route uses `storage.open()`.

### Root Cause
In `app/eqms/modules/nre_projects/admin.py`, the `nre_download_pdf` function (line 203) uses `storage.get_bytes()` and wraps in `io.BytesIO`. The `nre_view_pdf` function (line 228) uses `storage.open()`. Both should handle the case where the file doesn't exist gracefully.

However, the real problem may be that the storage key used during bulk PDF import includes a `sales_order_id` in the path:
```python
storage_key = f"sales_orders/{sales_order_id}/pdfs/{pdf_type}_{timestamp}_{safe_name}"
```

But after a data reset + reimport, the sales_order_id changes, making old storage keys invalid. This means the `OrderPdfAttachment.storage_key` in the DB points to a path that no longer exists in storage.

### Required Changes

#### A. Check if Storage Backend Has the File Before Serving
Both download and view routes should handle storage errors gracefully. The current code already has try/except but verify it works properly.

#### B. Ensure Storage Keys Are Stable
The storage key should not depend on auto-incremented IDs that change after data reset. Consider using the order number instead:

**File**: `app/eqms/modules/rep_traceability/admin.py`, function `_store_pdf_attachment`

Change the storage key generation to use order_number instead of sales_order_id:

```python
def _store_pdf_attachment(
    s,
    *,
    pdf_bytes: bytes,
    filename: str,
    pdf_type: str,
    sales_order_id: int | None,
    distribution_entry_id: int | None,
    user: User,
    order_number: str | None = None,  # ADD THIS PARAMETER
) -> str:
    from werkzeug.utils import secure_filename
    from datetime import datetime
    from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
    from app.eqms.storage import StorageError

    storage = storage_from_config(current_app.config)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = secure_filename(filename) or "document.pdf"
    
    if order_number:
        storage_key = f"sales_orders/SO_{order_number}/pdfs/{pdf_type}_{timestamp}_{safe_name}"
    elif sales_order_id:
        storage_key = f"sales_orders/{sales_order_id}/pdfs/{pdf_type}_{timestamp}_{safe_name}"
    else:
        storage_key = f"sales_orders/unlinked/{pdf_type}_{timestamp}_{safe_name}"
    # ... rest stays the same
```

Then update all callers of `_store_pdf_attachment` / `_store_and_track` to pass `order_number` where available.

---

<a name="issue-6"></a>
## Issue 6: Customer Profile — PDF Download on Sales Orders Tab

### Problem  
On the Customer Profile page (`/admin/customers/<id>?tab=sales_orders`), the Sales Orders tab shows order numbers but there's no way to download the PDF attachment directly from that tab. The distributions tab has download links but the sales orders tab does not.

### Required Changes

#### A. Pass PDF Attachments to Customer Detail Template
**File**: `app/eqms/modules/customer_profiles/admin.py`, function `customer_detail`

After querying `sales_orders`, also query the associated `OrderPdfAttachment` records:

```python
from app.eqms.modules.rep_traceability.models import OrderPdfAttachment
from collections import defaultdict

# Get PDF attachments grouped by sales order
order_ids = [so.id for so in sales_orders]
attachments_by_order: dict[int, list] = defaultdict(list)
if order_ids:
    attachments = (
        s.query(OrderPdfAttachment)
        .filter(OrderPdfAttachment.sales_order_id.in_(order_ids))
        .order_by(OrderPdfAttachment.uploaded_at.desc())
        .all()
    )
    for att in attachments:
        attachments_by_order[att.sales_order_id].append(att)
```

Pass `attachments_by_order` to the template:
```python
return render_template(
    "admin/customers/detail.html",
    ...
    attachments_by_order=attachments_by_order,
    ...
)
```

#### B. Add Download Links to Sales Orders Tab
**File**: `app/eqms/templates/admin/customers/detail.html`

In the Sales Orders tab section, after the order row, add a PDF attachments column or sub-section:

Add a new `<th>` column header "PDFs" and for each sales order row, display download links:

```html
<td style="padding:10px 12px;">
  {% set atts = attachments_by_order.get(so.id, []) %}
  {% for att in atts %}
    <a href="{{ url_for('rep_traceability.sales_order_pdf_download', attachment_id=att.id) }}"
       class="button button--secondary" style="font-size:11px; padding:3px 8px;">
      ↓ PDF
    </a>
  {% endfor %}
  {% if not atts %}
    <span class="muted" style="font-size:11px;">—</span>
  {% endif %}
</td>
```

---

<a name="issue-7"></a>
## Issue 7: Sales Dashboard — Replace "Current Lot" With Per-Lot Tracking

### Problem
The Inventory by SKU section on the Sales Dashboard currently shows one row per SKU with a "Current Lot" column. The user wants this replaced with a view that shows **every unique Correct Lot Name** from the LotLog with its manufacturing date, expiration date, produced/distributed/remaining quantities.

### The Relevant Lots
These are the actual lots that should appear (each is a unique "Correct Lot Name" in the LotLog):
- `SLQ-05022025`
- `SLQ-81020515241`
- `SLQ-01242025`
- `SLQ-11202024`
- `SLQ-05012025`
- `SLQ-11192024`

Each lot may appear on MULTIPLE rows in the LotLog due to ShipStation typos, but there is only ONE actual lot per unique Correct Lot Name. The `lot_corrections` mapping handles the typo→correct mapping.

### Required Changes

#### A. Restructure the Lot Tracking Computation  
**File**: `app/eqms/modules/rep_traceability/service.py`, function `compute_sales_dashboard`, starting around line 809

Replace the current per-SKU lot tracking (lines 809-946) with per-lot tracking:

```python
# === NEW LOT TRACKING: Per-lot rows with mfg/exp dates ===
from app.eqms.modules.shipstation_sync.parsers import load_lot_log_with_inventory, normalize_lot, VALID_SKUS
lotlog_path = (
    os.environ.get("LOTLOG_PATH")
    or os.environ.get("SHIPSTATION_LOTLOG_PATH")
    or os.environ.get("LotLog_Path")
    or "app/eqms/data/LotLog.csv"
).strip()

lot_to_sku, lot_corrections, lot_inventory, lot_years = load_lot_log_with_inventory(lotlog_path)
lotlog_missing = not lot_to_sku
min_year = int(os.environ.get("DASHBOARD_LOT_MIN_YEAR", "2025"))

# Also load manufacturing and expiration dates per lot
lot_mfg_dates, lot_exp_dates = _load_lot_dates(lotlog_path)  # NEW HELPER

# Build set of unique canonical lots (Correct Lot Names) manufactured since min_year
canonical_lots: dict[str, dict] = {}
for lot, year in lot_years.items():
    if year < min_year:
        continue
    sku = lot_to_sku.get(lot)
    if not sku or sku not in VALID_SKUS:
        continue
    if lot not in canonical_lots:
        canonical_lots[lot] = {
            "lot": lot,
            "sku": sku,
            "total_produced": lot_inventory.get(lot, 0),
            "total_distributed": 0,
            "mfg_date": lot_mfg_dates.get(lot),
            "exp_date": lot_exp_dates.get(lot),
            "year": year,
        }

# Aggregate distributions per corrected lot
all_lines = (
    s.query(DistributionLine, DistributionLogEntry)
    .join(DistributionLogEntry, DistributionLogEntry.id == DistributionLine.distribution_entry_id)
    .filter(
        DistributionLogEntry.sales_order_id.isnot(None),
        DistributionLine.lot_number.isnot(None),
    )
    .all()
)
for line, entry in all_lines:
    raw_lot = (line.lot_number or "").strip()
    if not raw_lot:
        continue
    normalized = normalize_lot(raw_lot)
    corrected = lot_corrections.get(normalized, normalized)
    if corrected in canonical_lots:
        canonical_lots[corrected]["total_distributed"] += int(line.quantity or 0)

# Also handle legacy entries without distribution_lines
if line_entry_ids_all:
    entry_fallbacks = (
        s.query(DistributionLogEntry)
        .filter(
            DistributionLogEntry.sales_order_id.isnot(None),
            DistributionLogEntry.lot_number.isnot(None),
            ~DistributionLogEntry.id.in_(line_entry_ids_all),
        )
        .all()
    )
    for e in entry_fallbacks:
        raw_lot = (e.lot_number or "").strip()
        if not raw_lot:
            continue
        normalized = normalize_lot(raw_lot)
        corrected = lot_corrections.get(normalized, normalized)
        if corrected in canonical_lots:
            canonical_lots[corrected]["total_distributed"] += int(e.quantity or 0)

# Calculate remaining and build sorted list
lot_tracking = []
for lot_data in canonical_lots.values():
    lot_data["remaining"] = lot_data["total_produced"] - lot_data["total_distributed"]
    lot_tracking.append(lot_data)

lot_tracking.sort(key=lambda x: (x["sku"], x.get("mfg_date") or "", x["lot"]))
```

#### B. Add Helper Function to Load Lot Dates
**File**: `app/eqms/modules/shipstation_sync/parsers.py`

Add a new function to extract manufacturing and expiration dates per canonical lot:

```python
def load_lot_dates(path_str: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Load manufacturing and expiration dates per canonical lot from LotLog.csv.
    Returns (lot_mfg_dates, lot_exp_dates) where keys are canonical lot names
    and values are date strings (as-is from CSV).
    """
    p = Path(path_str.replace("\\", "/"))
    if not p.exists():
        return {}, {}
    
    lot_mfg_dates: dict[str, str] = {}
    lot_exp_dates: dict[str, str] = {}
    
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            correct_lot = (str(row.get("Correct Lot Name") or "")).strip().upper()
            raw_lot = (str(row.get("Lot") or "")).strip().upper()
            
            canonical = normalize_lot(correct_lot) if correct_lot else normalize_lot(raw_lot)
            if not canonical:
                continue
            
            mfg = (str(row.get("Manufacturing Date") or "")).strip()
            exp = (str(row.get("Expiration Date") or row.get("Exp Date") or "")).strip()
            
            if mfg and canonical not in lot_mfg_dates:
                lot_mfg_dates[canonical] = mfg
            if exp and canonical not in lot_exp_dates:
                lot_exp_dates[canonical] = exp
    
    return lot_mfg_dates, lot_exp_dates
```

Also import this function in `service.py` where it's used.

#### C. Update the Dashboard Template
**File**: `app/eqms/templates/admin/sales_dashboard/index.html`

Replace the Inventory by SKU table (around lines 177-222) with a per-lot table:

```html
<div class="card">
  <h2 style="margin-top:0; font-size:16px;">Lot Inventory (Since {{ lot_min_year }})</h2>
  {% if lot_tracking %}
    <div style="overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Lot</th>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">SKU</th>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Mfg Date</th>
            <th style="text-align:left; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Exp Date</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Produced</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Distributed</th>
            <th style="text-align:right; padding:10px 12px; border-bottom:1px solid var(--border); font-size:11px; text-transform:uppercase; color:var(--muted);">Remaining</th>
          </tr>
        </thead>
        <tbody>
          {% for row in lot_tracking %}
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
              <td style="padding:10px 12px;"><code style="background:rgba(102,163,255,0.1); padding:2px 6px; border-radius:4px; color:var(--primary);">{{ row.lot|e }}</code></td>
              <td style="padding:10px 12px;"><code style="background:rgba(255,255,255,0.05); padding:2px 6px; border-radius:4px;">{{ row.sku|e }}</code></td>
              <td style="padding:10px 12px; font-size:12px;">{{ row.mfg_date or "—" }}</td>
              <td style="padding:10px 12px; font-size:12px;">{{ row.exp_date or "—" }}</td>
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

<a name="issue-8"></a>
## Issue 8: Lot Name Correction — ShipStation Typos

### Problem
The lot correction system exists in `load_lot_log_with_inventory()` via the `lot_corrections` dict, which maps typo lots to correct lot names. This is working for the dashboard aggregation. However, the ShipStation sync module should ALSO correct lot names when creating distribution entries, so the corrected lot name is stored in the DB directly.

### Required Changes

#### A. Apply Lot Correction During ShipStation Sync  
**File**: `app/eqms/modules/shipstation_sync/service.py` (or wherever ShipStation distributions are created)

When creating a new distribution entry from ShipStation data, after extracting the lot number, apply the lot correction:

```python
from app.eqms.modules.shipstation_sync.parsers import normalize_lot, load_lot_log

# After extracting lot_number:
lot_to_sku, lot_corrections = load_lot_log(lotlog_path)
normalized = normalize_lot(raw_lot)
corrected = lot_corrections.get(normalized, normalized)
# Use corrected as the lot_number for the distribution entry
```

This ensures all distribution entries store the **Correct Lot Name** regardless of ShipStation typos.

#### B. Also Apply During CSV Import
**File**: `app/eqms/modules/rep_traceability/parsers/csv.py` or in the import handler

Same logic: after parsing lot_number from CSV, normalize and correct it before storing.

---

<a name="issue-9"></a>
## Issue 9: Admin Docs — Root Folder Designation for Uploaded Files

### Problem
The user needs the ability to designate which root-level library folder a document belongs to, both at upload time and after upload. Currently, documents are uploaded to a specific library (QMS Documents, Employee Training, etc.) and optionally into a subfolder. But there's no way to:
1. Choose the library/root folder during upload if uploading from a different context
2. Change the library/folder assignment after a document is uploaded

### Required Changes

#### A. Add "Move Document" / "Change Folder" Functionality
**File**: `app/eqms/modules/admin_docs/admin.py`

Add a new route to change a document's folder assignment:

```python
@bp.post("/admin-docs/documents/<int:doc_id>/move")
@require_permission("admin.view")
def admin_docs_move_document(doc_id: int):
    s = db_session()
    u = _current_user()
    doc = s.get(AdminDocFile, doc_id)
    if not doc:
        abort(404)
    
    new_library_key = (request.form.get("library_key") or "").strip()
    new_folder_id = request.form.get("folder_id", type=int)
    
    # Validate library
    if new_library_key and new_library_key not in LIBRARIES:
        flash("Invalid library.", "danger")
        return redirect(request.referrer or url_for("admin.index"))
    
    # Validate folder
    new_folder = None
    if new_folder_id:
        new_folder = s.get(AdminDocFolder, new_folder_id)
        if not new_folder:
            flash("Folder not found.", "danger")
            return redirect(request.referrer or url_for("admin.index"))
        # Use the folder's library_key if not explicitly provided
        if not new_library_key:
            new_library_key = new_folder.library_key
    
    if new_library_key:
        doc.library_key = new_library_key
    doc.folder_id = new_folder_id  # Can be None (root of library)
    
    s.commit()
    flash(f"Document moved to {LIBRARIES.get(doc.library_key, doc.library_key)}.", "success")
    return redirect(url_for(LIBRARY_ENDPOINTS.get(doc.library_key, "admin.index"), folder_id=new_folder_id))
```

#### B. Add Library/Folder Selector to Upload Form
**File**: `app/eqms/templates/admin/admin_docs/index.html`

Update the upload form to include a dropdown for selecting the target library and optionally a different folder within that library. Also add a "Move" action next to each document.

In the documents table, add a "Move" button for each document that opens a modal with library + folder selectors:

```html
<td>
  <a href="{{ url_for('admin_docs.admin_docs_document_view', doc_id=doc.id) }}">View</a>
  <a href="{{ url_for('admin_docs.admin_docs_document_download', doc_id=doc.id) }}">Download</a>
  <button type="button" onclick="document.getElementById('moveModal{{ doc.id }}').style.display='flex'" 
          class="button button--secondary" style="font-size:11px; padding:3px 8px;">Move</button>
</td>
```

And add a move modal for each document:
```html
<div id="moveModal{{ doc.id }}" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.7); justify-content:center; align-items:center; z-index:1000;">
  <div class="card" style="max-width:400px; width:90%;">
    <h3 style="margin-top:0;">Move Document</h3>
    <form method="post" action="{{ url_for('admin_docs.admin_docs_move_document', doc_id=doc.id) }}">
      <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
      <div class="label">Library</div>
      <select name="library_key" style="margin-bottom:12px;">
        {% for key, label in libraries.items() %}
          <option value="{{ key }}" {% if key == library_key %}selected{% endif %}>{{ label }}</option>
        {% endfor %}
      </select>
      <div class="label">Folder (leave empty for root)</div>
      <select name="folder_id" style="margin-bottom:16px;">
        <option value="">— Root —</option>
        {% for folder in all_folders %}
          <option value="{{ folder.id }}">{{ folder.name|e }}</option>
        {% endfor %}
      </select>
      <div style="display:flex; gap:10px; justify-content:flex-end;">
        <button type="button" onclick="this.closest('[id^=moveModal]').style.display='none'" class="button button--secondary">Cancel</button>
        <button type="submit" class="button">Move</button>
      </div>
    </form>
  </div>
</div>
```

Pass the `LIBRARIES` dict and all folders to the template so the move modal can populate dropdowns.

#### C. Pass Extra Data to Template
**File**: `app/eqms/modules/admin_docs/admin.py`, in `_render_library()`

Query all folders across all libraries for the move modal:

```python
all_folders = (
    s.query(AdminDocFolder)
    .order_by(AdminDocFolder.library_key.asc(), AdminDocFolder.name.asc())
    .all()
)

return render_template(
    "admin/admin_docs/index.html",
    ...
    libraries=LIBRARIES,
    all_folders=all_folders,
)
```

---

<a name="verification"></a>
## Verification Checklist

After implementing all changes, verify:

1. **Import a test PDF**: Upload `SO_Sales Order February.pdf` and verify:
   - [ ] Customer name is "Aspirus Medical Group" (from Sold To), NOT "NRE - ASPIRUS"
   - [ ] Customer address (Wausau, WI) is populated
   - [ ] PDF is stored as `SO_0000299.pdf`, not `SO_Sales Order February.pdf_page_10.pdf`
   - [ ] Customer does NOT appear in NRE Projects (it should have matching ShipStation distributions)

2. **NRE Projects page**: Verify only customers with NO matched distributions appear

3. **Customer Profile → Sales Orders tab**: Verify PDF download links are present

4. **Sales Dashboard → Lot Inventory**:
   - [ ] Shows rows per lot (not per SKU)
   - [ ] Each of the 6 lots listed above appears
   - [ ] Manufacturing date and expiration date are shown
   - [ ] "Current Lot" column is removed
   - [ ] Produced, Distributed, Remaining are correct per lot

5. **ShipStation lot correction**: Verify that typo lots in ShipStation are corrected to Correct Lot Names

6. **Admin Docs**: Verify ability to move documents between libraries/folders

7. **No regressions**: Verify the app starts without errors

## Files to Modify

| File | Changes |
|------|---------|
| `app/eqms/modules/rep_traceability/admin.py` | Fix `_is_catheter_order`, remove NRE skip for auto-match, fix PDF naming |
| `app/eqms/modules/rep_traceability/parsers/pdf.py` | Fix customer name fallback (no NRE prefix), add Sold To address parser |
| `app/eqms/modules/rep_traceability/service.py` | Restructure lot tracking to per-lot, add lot date loading |
| `app/eqms/modules/nre_projects/admin.py` | Fix NRE classification query |
| `app/eqms/modules/customer_profiles/admin.py` | Add PDF attachments to customer detail |
| `app/eqms/templates/admin/customers/detail.html` | Add PDF download column to Sales Orders tab |
| `app/eqms/templates/admin/sales_dashboard/index.html` | Replace lot tracking table with per-lot view |
| `app/eqms/modules/shipstation_sync/parsers.py` | Add `load_lot_dates()` function |
| `app/eqms/modules/shipstation_sync/service.py` | Apply lot correction during sync |
| `app/eqms/modules/admin_docs/admin.py` | Add move document route |
| `app/eqms/templates/admin/admin_docs/index.html` | Add move document UI |

## Critical Constraints

- **DO NOT delete any existing data or tables**
- **DO NOT change database schema** (no new migrations needed for these fixes — they are logic/template changes only)
- **DO NOT remove any existing routes or templates** — only modify them
- **DO NOT change the VALID_SKUS or EXCLUDED_SKUS constants**
- **Commit message**: `fix: critical customer naming, NRE classification, inventory tracking, PDF handling, admin docs`
- **Push to main when done**
