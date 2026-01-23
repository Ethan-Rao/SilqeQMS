"""
PDF parser for 2025 Sales Orders PDF ingestion.

Parses table data from PDF files to extract:
- Order Number
- Order Date
- Customer Name
- SKU
- Quantity
- Lot Number (if present)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ParsedOrderLine:
    """Single parsed order line from PDF."""
    order_number: str
    order_date: date
    customer_name: str
    sku: str
    quantity: int
    lot_number: str | None


@dataclass(frozen=True)
class ParseError:
    """Parse error for a specific row or section."""
    row_index: int | None
    message: str
    raw_data: str | None = None


@dataclass(frozen=True)
class ParseResult:
    """Result of parsing a PDF file."""
    orders: list[dict[str, Any]]  # Grouped by order_number
    lines: list[ParsedOrderLine]  # All parsed lines
    labels: list[dict[str, Any]]
    errors: list[ParseError]
    total_rows_processed: int


# Valid SKUs for validation
VALID_SKUS = {'211810SPT', '211610SPT', '211410SPT'}


def _normalize_sku(raw_sku: str) -> str | None:
    """Normalize raw SKU to standard format."""
    s = (raw_sku or "").strip().upper()
    
    # Direct match
    if s in VALID_SKUS:
        return s
    
    # Common variations
    sku_map = {
        '18': '211810SPT',
        '16': '211610SPT',
        '14': '211410SPT',
        '18FR': '211810SPT',
        '16FR': '211610SPT',
        '14FR': '211410SPT',
        'SLQ-4001-18': '211810SPT',
        'SLQ-4001-16': '211610SPT',
        'SLQ-4001-14': '211410SPT',
        'SLQ400118': '211810SPT',
        'SLQ400116': '211610SPT',
        'SLQ400114': '211410SPT',
    }
    
    for pattern, sku in sku_map.items():
        if pattern in s:
            return sku
    
    # Check for French size numbers
    if '18' in s and ('SUSPENSION' in s or 'SILQ' in s or 'SLQ' in s):
        return '211810SPT'
    if '16' in s and ('SUSPENSION' in s or 'SILQ' in s or 'SLQ' in s):
        return '211610SPT'
    if '14' in s and ('SUSPENSION' in s or 'SILQ' in s or 'SLQ' in s):
        return '211410SPT'
    
    return None


def _normalize_lot(raw_lot: str) -> str | None:
    """Normalize lot number to SLQ-XXXXXXXX format."""
    s = (raw_lot or "").strip().upper()
    if not s or s in ('', 'N/A', 'NA', 'UNKNOWN', '-'):
        return None
    
    # Already has SLQ- prefix
    if s.startswith('SLQ-'):
        return s
    
    # Add SLQ- prefix if it's a numeric lot
    if re.match(r'^\d{6,10}$', s):
        return f'SLQ-{s}'
    
    return s


def _parse_date(raw_date: str) -> date | None:
    """Parse date from various formats."""
    s = (raw_date or "").strip()
    if not s:
        return None
    
    # Try ISO format first (YYYY-MM-DD)
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    
    # Try MM/DD/YYYY
    match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except ValueError:
            pass
    
    # Try MM-DD-YYYY
    match = re.match(r'^(\d{1,2})-(\d{1,2})-(\d{4})$', s)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except ValueError:
            pass
    
    # Try Month DD, YYYY (e.g., "January 15, 2025")
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
    }
    match = re.match(r'^([a-zA-Z]+)\s+(\d{1,2}),?\s+(\d{4})$', s)
    if match:
        month_name = match.group(1).lower()
        if month_name in months:
            try:
                return date(int(match.group(3)), months[month_name], int(match.group(2)))
            except ValueError:
                pass
    
    return None


def _parse_quantity(raw_qty: str) -> int | None:
    """Parse quantity from string."""
    s = (raw_qty or "").strip()
    if not s:
        return None
    
    # Remove any non-numeric prefix/suffix
    s = re.sub(r'[^\d]', '', s)
    if not s:
        return None
    
    try:
        qty = int(s)
        return qty if qty > 0 else None
    except ValueError:
        return None


def _extract_order_number(text: str) -> str | None:
    patterns = [
        r'Order\s*#?\s*:?\s*(\d+)',
        r'SO\s+(\d+)',
        r'Order\s+Number\s*:?\s*(\d+)',
        r'Sales\s+Order\s*:?\s*(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_ship_date(text: str) -> date | None:
    patterns = [
        r'Ship\s+Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        r'Shipped\s*:?\s*(\d{4}-\d{2}-\d{2})',
        r'Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            parsed = _parse_date(match.group(1))
            if parsed:
                return parsed
    return None


def _extract_ship_to_name(text: str) -> str | None:
    ship_to_section = re.search(r'Ship\s+To\s*:?\s*(.+?)(?:\n\n|\Z)', text, re.IGNORECASE | re.DOTALL)
    if not ship_to_section:
        return None
    section = ship_to_section.group(1)
    lines = [l.strip() for l in section.split('\n') if l.strip()]
    return lines[0] if lines else None


def _extract_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    sku_pattern = r'(211810SPT|211610SPT|211410SPT|18FR|16FR|14FR|SLQ-4001-18|SLQ-4001-16|SLQ-4001-14)'
    for match in re.finditer(sku_pattern, text, re.IGNORECASE):
        raw_sku = match.group(1)
        sku = _normalize_sku(raw_sku)
        if not sku:
            continue
        context = text[max(0, match.start()-60):match.end()+80]
        qty_match = re.search(r'(?:Qty|Quantity)\s*:?\s*(\d+)', context, re.IGNORECASE)
        lot_match = re.search(r'(SLQ-\d{5,12})', context, re.IGNORECASE)
        qty = int(qty_match.group(1)) if qty_match else 1
        items.append({
            "sku": sku,
            "quantity": qty,
            "lot_number": lot_match.group(1) if lot_match else None,
        })
    return items


def _parse_text_page(text: str, page_num: int) -> tuple[list[ParsedOrderLine], list[ParseError], dict[str, Any] | None]:
    lines: list[ParsedOrderLine] = []
    errors: list[ParseError] = []
    order_number = _extract_order_number(text)
    ship_date = _extract_ship_date(text) or date.today()
    customer_name = _extract_ship_to_name(text) or "Unknown Customer"
    items = _extract_items(text)

    if not order_number:
        return lines, errors, None

    if not items:
        errors.append(ParseError(row_index=page_num, message="Missing items in text-based parse", raw_data=text[:200]))
        return lines, errors, {
            "order_number": order_number,
            "order_date": ship_date,
            "ship_date": ship_date,
            "customer_name": customer_name,
            "lines": [],
        }

    for item in items:
        lines.append(ParsedOrderLine(
            order_number=order_number,
            order_date=ship_date,
            customer_name=customer_name,
            sku=item["sku"],
            quantity=item["quantity"],
            lot_number=item.get("lot_number"),
        ))
    return lines, errors, None


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2012", "-").replace("\u2212", "-")
    t = t.replace("\u00a0", " ")
    return t


def _parse_label_page(text: str, page_num: int) -> dict[str, Any] | None:
    tracking = _extract_tracking_number(text)
    ship_to = _extract_ship_to_name(text)
    if tracking and ship_to:
        return {"tracking_number": tracking, "ship_to": ship_to, "page": page_num}
    # Try reversed line heuristic
    reversed_lines = "\n".join([line[::-1] for line in text.splitlines()])
    tracking = _extract_tracking_number(reversed_lines)
    ship_to = _extract_ship_to_name(reversed_lines)
    if tracking and ship_to:
        return {"tracking_number": tracking, "ship_to": ship_to, "page": page_num}
    return None


def _extract_tracking_number(text: str) -> str | None:
    patterns = [
        r'(1Z[0-9A-Z]{16,20})',  # UPS
        r'(\d{20,22})',          # USPS
        r'(\d{12,15})',          # FedEx common
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def parse_sales_orders_pdf(file_bytes: bytes) -> ParseResult:
    """
    Parse 2025 Sales Orders PDF.
    
    Extracts table data and groups by order number.
    
    Returns:
        ParseResult with:
        - orders: List of order dicts grouped by order_number
        - lines: All parsed line items
        - errors: List of parse errors
        - total_rows_processed: Count of rows attempted
    """
    try:
        import pdfplumber
    except ImportError:
        return ParseResult(
            orders=[],
            lines=[],
            labels=[],
            errors=[ParseError(row_index=None, message="pdfplumber not installed. Run: pip install pdfplumber")],
            total_rows_processed=0,
        )
    
    import io
    
    errors: list[ParseError] = []
    lines: list[ParsedOrderLine] = []
    header_orders: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    total_rows = 0
    
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract tables from page
                tables = page.extract_tables()
                
                if not tables:
                    # Text-based fallback (order or label)
                    text = page.extract_text() or ""
                    normalized = _normalize_text(text)
                    parsed_lines, parsed_errors, header_order = _parse_text_page(normalized, page_num)
                    lines.extend(parsed_lines)
                    errors.extend(parsed_errors)
                    if header_order:
                        header_orders.append(header_order)
                    label = _parse_label_page(normalized, page_num)
                    if label:
                        labels.append(label)
                    if not normalized:
                        errors.append(ParseError(
                            row_index=None,
                            message=f"Page {page_num}: No extractable text.",
                            raw_data=None,
                        ))
                    continue
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # First row is usually headers
                    headers = [str(h or "").strip().lower() for h in (table[0] or [])]
                    
                    # Try to identify column indices
                    order_col = _find_column(headers, ['order', 'order #', 'order number', 'order_number', 'ordernum'])
                    date_col = _find_column(headers, ['date', 'order date', 'order_date', 'orderdate', 'ship date'])
                    customer_col = _find_column(headers, ['customer', 'facility', 'customer name', 'company', 'ship to'])
                    sku_col = _find_column(headers, ['sku', 'item', 'product', 'item sku', 'part', 'part number'])
                    qty_col = _find_column(headers, ['qty', 'quantity', 'units', 'amount', 'count'])
                    lot_col = _find_column(headers, ['lot', 'lot #', 'lot number', 'lot_number', 'batch'])
                    
                    # Skip if we can't identify required columns
                    if order_col is None or customer_col is None:
                        errors.append(ParseError(
                            row_index=None,
                            message=f"Page {page_num}: Cannot identify required columns (order, customer). Headers: {headers}",
                            raw_data=str(headers),
                        ))
                        continue
                    
                    # Process data rows
                    for row_idx, row in enumerate(table[1:], start=2):
                        total_rows += 1
                        
                        if not row or len(row) <= max(filter(lambda x: x is not None, [order_col, date_col, customer_col, sku_col, qty_col, lot_col])):
                            continue
                        
                        try:
                            raw_order = str(row[order_col] or "").strip() if order_col is not None and order_col < len(row) else ""
                            raw_date = str(row[date_col] or "").strip() if date_col is not None and date_col < len(row) else ""
                            raw_customer = str(row[customer_col] or "").strip() if customer_col is not None and customer_col < len(row) else ""
                            raw_sku = str(row[sku_col] or "").strip() if sku_col is not None and sku_col < len(row) else ""
                            raw_qty = str(row[qty_col] or "").strip() if qty_col is not None and qty_col < len(row) else "1"
                            raw_lot = str(row[lot_col] or "").strip() if lot_col is not None and lot_col < len(row) else ""
                            
                            # Skip empty rows
                            if not raw_order and not raw_customer:
                                continue
                            
                            # Validate required fields
                            if not raw_order:
                                errors.append(ParseError(row_index=total_rows, message="Missing order number", raw_data=str(row)))
                                continue
                            
                            if not raw_customer:
                                errors.append(ParseError(row_index=total_rows, message="Missing customer name", raw_data=str(row)))
                                continue
                            
                            # Parse date (default to today if missing)
                            order_date = _parse_date(raw_date)
                            if not order_date:
                                from datetime import date as date_type
                                order_date = date_type.today()
                            
                            # Parse SKU
                            sku = _normalize_sku(raw_sku)
                            if not sku:
                                errors.append(ParseError(row_index=total_rows, message=f"Invalid SKU: {raw_sku}", raw_data=str(row)))
                                continue
                            
                            # Parse quantity
                            quantity = _parse_quantity(raw_qty)
                            if not quantity:
                                quantity = 1  # Default to 1 if not specified
                            
                            # Parse lot
                            lot_number = _normalize_lot(raw_lot)
                            
                            lines.append(ParsedOrderLine(
                                order_number=raw_order,
                                order_date=order_date,
                                customer_name=raw_customer,
                                sku=sku,
                                quantity=quantity,
                                lot_number=lot_number,
                            ))
                            
                        except Exception as e:
                            errors.append(ParseError(row_index=total_rows, message=f"Parse error: {e}", raw_data=str(row)))
    
    except Exception as e:
        errors.append(ParseError(row_index=None, message=f"Failed to open PDF: {e}"))
        return ParseResult(orders=[], lines=[], labels=[], errors=errors, total_rows_processed=0)
    
    # Group lines by order_number
    orders_dict: dict[str, dict[str, Any]] = {}
    for line in lines:
        if line.order_number not in orders_dict:
            orders_dict[line.order_number] = {
                "order_number": line.order_number,
                "order_date": line.order_date,
                "customer_name": line.customer_name,
                "lines": [],
            }
        orders_dict[line.order_number]["lines"].append({
            "sku": line.sku,
            "quantity": line.quantity,
            "lot_number": line.lot_number,
        })
    
    orders = list(orders_dict.values())
    for hdr in header_orders:
        if hdr["order_number"] not in orders_dict:
            orders.append(hdr)
    
    return ParseResult(
        orders=orders,
        lines=lines,
        labels=labels,
        errors=errors,
        total_rows_processed=total_rows,
    )


def _find_column(headers: list[str], candidates: list[str]) -> int | None:
    """Find column index matching any of the candidate names."""
    for i, h in enumerate(headers):
        h_clean = h.lower().strip()
        for c in candidates:
            if c in h_clean or h_clean in c:
                return i
    return None
