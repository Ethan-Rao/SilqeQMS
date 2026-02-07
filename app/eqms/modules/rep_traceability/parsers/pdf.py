"""
PDF parser for 2025 Sales Orders PDF ingestion.

Parses SILQ-specific Sales Order format to extract:
- Order Number (SO #)
- Order Date (Document Date)
- Ship To (Customer Name)
- Item Codes and Quantities
- Lot Numbers (if present)

Also handles shipping label PDFs for tracking number extraction.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


def _extract_text(pdf_bytes: bytes) -> str:
    try:
        import pdfplumber
    except Exception as e:
        logger.warning("pdfplumber not available: %s", e)
        return ""

    from io import BytesIO

    text = []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                text.append(page.extract_text() or "")
    except Exception as e:
        logger.warning("PDF text extraction failed: %s", e)
        return ""
    return "\n".join(text)


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
    orders: list[dict[str, Any]]
    lines: list[ParsedOrderLine]
    labels: list[dict[str, Any]]
    errors: list[ParseError]
    total_rows_processed: int


from app.eqms.constants import ITEM_CODE_TO_SKU, VALID_SKUS
SKIP_ITEM_CODES = {'NRE', 'SLQ-4007', 'IFU'}
MAX_REASONABLE_QUANTITY = 50000


def _normalize_sku(raw_sku: str, item_description: str = "") -> str | None:
    s = (raw_sku or "").strip().upper().replace(" ", "")
    desc = (item_description or "").upper()
    for skip in SKIP_ITEM_CODES:
        if skip in s or skip in desc:
            return None
    if s in ITEM_CODE_TO_SKU:
        return ITEM_CODE_TO_SKU[s]
    if s in VALID_SKUS:
        return s
    item_match = re.search(r'(2[14-8][4-8]00101003|2[14-8][4-8]00101004)', s)
    if item_match:
        code = item_match.group(1)
        if code in ITEM_CODE_TO_SKU:
            return ITEM_CODE_TO_SKU[code]
    sku_map = {
        '18FR': '211810SPT', '16FR': '211610SPT', '14FR': '211410SPT',
        'SLQ-4001-18': '211810SPT', 'SLQ-4001-16': '211610SPT', 'SLQ-4001-14': '211410SPT',
    }
    for pattern, sku in sku_map.items():
        if pattern in s:
            return sku
    if len(s) >= 5 and s.startswith('21'):
        fr_code = s[2:4]
        if fr_code == '18':
            return '211810SPT'
        elif fr_code == '16':
            return '211610SPT'
        elif fr_code == '14':
            return '211410SPT'
    return None


def _normalize_lot(raw_lot: str) -> str | None:
    s = (raw_lot or "").strip().upper()
    if not s or s in ('', 'N/A', 'NA', 'UNKNOWN', '-'):
        return None
    if s.startswith('SLQ-'):
        return s
    if re.match(r'^\d{6,10}$', s):
        return f'SLQ-{s}'
    return s


def _parse_date(raw_date: str) -> date | None:
    s = (raw_date or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', s)
    if match:
        try:
            return date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except ValueError:
            pass
    match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{2})$', s)
    if match:
        try:
            year = int(match.group(3))
            year = year + 2000 if year < 50 else year + 1900
            return date(year, int(match.group(1)), int(match.group(2)))
        except ValueError:
            pass
    return None


def _parse_quantity(raw_qty: str) -> int:
    s = (raw_qty or "").strip()
    if not s:
        return 1
    if _is_lot_number(s):
        return 1
    match = re.search(r'(\d+)', s)
    if match:
        try:
            qty = int(match.group(1))
            if qty > MAX_REASONABLE_QUANTITY:
                logger.warning("Quantity %s exceeds max (%s); flagging parse error", qty, MAX_REASONABLE_QUANTITY)
                return 0
            return qty if qty > 0 else 1
        except ValueError:
            pass
    return 1


def _is_lot_number(value: str) -> bool:
    v = (value or "").strip().upper()
    if not v:
        return False
    if v.startswith("SLQ"):
        return True
    if re.match(r'^\d{8,}$', v):
        return True
    return False


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u00a0", " ")
    return t


def _parse_ship_to_block(text: str) -> dict[str, str | None]:
    """
    Parse SHIP TO block from SILQ Sales Order PDF.

    Expected format:
    SHIP TO:
    Recipient Name
    Company Name (optional)
    123 Street Address
    City, ST 12345
    """
    result = {
        "ship_to_name": None,
        "ship_to_address1": None,
        "ship_to_city": None,
        "ship_to_state": None,
        "ship_to_zip": None,
    }

    ship_to_match = re.search(
        r"Ship\s*To\s*[:\n](.+?)(?=\n\s*\n|Bill\s+To|Sold\s+To|Shipping\s+Method|Salesperson:|F\.?O\.?B\.?|TERMS|P\.?O\.?\s*#|Order\s+Date|Item|Qty|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not ship_to_match:
        return result

    lines = [l.strip() for l in ship_to_match.group(1).strip().split("\n") if l.strip()]

    for line in lines:
        if line and len(line) > 2 and not re.match(r"^\d+\s", line):
            result["ship_to_name"] = line
            break

    for line in lines:
        if re.match(r"^\d+\s+\w", line) or any(
            x in line.lower()
            for x in ["street", "st.", "ave", "blvd", "road", "rd.", "drive", "dr.", "lane", "ln."]
        ):
            result["ship_to_address1"] = line
            break

    city_state_zip_pattern = re.compile(
        r"^([A-Za-z\s\.]+)[,\s]+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)(?:\s+[A-Z]{2})?$"
    )
    for line in lines:
        match = city_state_zip_pattern.match(line)
        if match:
            result["ship_to_city"] = match.group(1).strip()
            result["ship_to_state"] = match.group(2)
            result["ship_to_zip"] = match.group(3)
            break

    return result


def _parse_customer_email(text: str) -> str | None:
    # Prefer explicit field label if present
    m = re.search(r"Customer\s*e-?mail\s*[:\s]*([^\s]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Fallback: first email-like token
    m = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
    if m:
        return m.group(1).strip()
    return None


def _parse_customer_number(text: str) -> str | None:
    patterns = [
        r"CUSTOMER\s*NUMBER\s*[:\s]+([A-Z0-9\-]+)",
        r"ACCOUNT\s*(?:NUMBER|#)\s*[:\s]+([A-Z0-9\-]+)",
        r"CUST\s*(?:NO|#|CODE)\s*[:\s]+([A-Z0-9\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            code = match.group(1).strip().upper()
            if code and len(code) >= 2 and code not in ("NA", "N/A", "NONE", "TBD"):
                return code
    return None


def _parse_bill_to_block(text: str) -> dict[str, str | None]:
    """
    Parse BILL TO block from SILQ Sales Order PDF.
    Uses Sold To as fallback if no Bill To section exists.
    """
    result = {
        "bill_to_name": None,
        "bill_to_address1": None,
        "bill_to_city": None,
        "bill_to_state": None,
        "bill_to_zip": None,
    }

    bill_to_match = re.search(
        r"Bill\s*To\s*[:\n](.+?)(?=\n\s*\n|Ship\s*To|Salesperson:|Terms|P\.?O\.?\s*#|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not bill_to_match:
        bill_to_match = re.search(
            r"Sold\s*To\s*[:\n](.+?)(?=\n\s*\n|Ship\s*To|Salesperson:|$)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
    if not bill_to_match:
        return result

    lines = [l.strip() for l in bill_to_match.group(1).strip().split("\n") if l.strip()]

    for line in lines:
        if line and len(line) > 2 and not re.match(r"^\d+\s", line):
            result["bill_to_name"] = line
            break

    for line in lines:
        if re.match(r"^\d+\s+\w", line) or any(
            x in line.lower()
            for x in ["street", "st.", "ave", "blvd", "road", "rd.", "drive", "dr.", "lane", "ln.", "suite", "ste"]
        ):
            result["bill_to_address1"] = line
            break

    city_state_zip_pattern = re.compile(
        r"^([A-Za-z\s\.]+)[,\s]+([A-Z]{2})\s+(\d{5}(?:-\d{4})?)(?:\s+[A-Z]{2})?$"
    )
    for line in lines:
        match = city_state_zip_pattern.match(line)
        if match:
            result["bill_to_city"] = match.group(1).strip()
            result["bill_to_state"] = match.group(2)
            result["bill_to_zip"] = match.group(3)
            break

    return result


def _parse_sold_to_block(text: str) -> str | None:
    """
    Parse SOLD TO block to get the primary customer/facility name.
    This is the canonical customer name (first line under SOLD TO).
    """
    sold_to_match = re.search(
        r"Sold\s*To\s*[:\n](.+?)(?=\n\s*\n|Ship\s*To|Salesperson:|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not sold_to_match:
        return None

    lines = [l.strip() for l in sold_to_match.group(1).strip().split("\n") if l.strip()]
    for line in lines:
        if line and len(line) > 2 and not re.match(r"^\d+\s", line):
            return line
    return None


def _parse_silq_sales_order_page(page, text: str, page_num: int) -> dict[str, Any] | None:
    has_sales_header = bool(re.search(r"SALES\s+ORDER|ORDER\s+NUMBER", text, re.IGNORECASE))
    order_patterns = [
        r'SO\s*#?\s*[:\s]*(\d{4,10})',
        r'Order\s*(?:#|Number|No\.?)?\s*[:\s]*(\d{4,10})',
        r'(?:Sales\s+Order|SO)\s*[:\s]*(\d{4,10})',
    ]
    if has_sales_header:
        order_patterns.append(r'(\d{4,10})')
    order_match = None
    for pattern in order_patterns:
        order_match = re.search(pattern, text, re.IGNORECASE)
        if order_match:
            break
    if not order_match:
        return None
    order_number = order_match.group(1).strip()
    date_match = re.search(r'(?:Document\s+Date|Order\s+Date|Date)\s*[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
    order_date = _parse_date(date_match.group(1)) if date_match else date.today()
    if not order_date:
        order_date = date.today()
    customer_code = _parse_customer_number(text)
    customer_name = _parse_sold_to_block(text) or "Unknown Customer"
    if not customer_name or customer_name == "Unknown Customer":
        if customer_code:
            customer_name = f"Customer {customer_code}"
    bill_to = _parse_bill_to_block(text)
    ship_to = _parse_ship_to_block(text)
    contact_email = _parse_customer_email(text)

    items = []

    # Try table extraction first (if available)
    try:
        tables = page.extract_tables() or []
        for table in tables:
            for row in table or []:
                if not row or len(row) < 3:
                    continue
                raw_code = (row[0] or "").strip()
                raw_desc = (row[1] or "").strip() if len(row) > 1 else ""
                raw_qty = (row[2] or "").strip() if len(row) > 2 else ""
                sku = _normalize_sku(raw_code, raw_desc)
                if not sku:
                    continue
                lot_number = None
                if _is_lot_number(raw_qty):
                    lot_number = _normalize_lot(raw_qty)
                    raw_qty = next(
                        (str(c).strip() for c in row[3:] if c and not _is_lot_number(str(c))),
                        "",
                    )
                quantity = _parse_quantity(raw_qty)
                if lot_number is None and len(row) > 3:
                    lot_number = _normalize_lot(row[3] or "")
                items.append({"sku": sku, "quantity": quantity, "lot_number": lot_number})
    except Exception as e:
        logger.debug("Table extraction failed on page %s: %s", page_num, e)

    # Fallback to text regex if no items parsed from tables
    if not items:
        item_pattern = re.compile(r'(2[14-8][0-9]{9}|211[46]10SPT|211810SPT)\s+(.+?)\s+(\d+)\s*(?:EA|Each)?', re.IGNORECASE)
        for match in item_pattern.finditer(text):
            item_code = match.group(1).strip()
            description = match.group(2).strip()
            qty_str = match.group(3).strip()
            sku = _normalize_sku(item_code, description)
            if not sku:
                continue
            quantity = _parse_quantity(qty_str)
            lot_number = None
            context = text[match.start():min(match.end() + 120, len(text))]
            lot_match = re.search(r'(?:Lot|LOT)\s*[:#]?\s*(SLQ-?\d+|\d{6,10})', context, re.IGNORECASE)
            if lot_match:
                lot_number = _normalize_lot(lot_match.group(1))
            items.append({"sku": sku, "quantity": quantity, "lot_number": lot_number})

    return {
        "order_number": order_number,
        "order_date": order_date,
        "ship_date": order_date,
        "customer_name": customer_name,
        "customer_code": customer_code,
        "address1": bill_to.get("bill_to_address1"),
        "city": bill_to.get("bill_to_city"),
        "state": bill_to.get("bill_to_state"),
        "zip": bill_to.get("bill_to_zip"),
        "contact_name": ship_to.get("ship_to_name"),
        "contact_email": contact_email,
        "ship_to_name": ship_to.get("ship_to_name"),
        "ship_to_address1": ship_to.get("ship_to_address1"),
        "ship_to_city": ship_to.get("ship_to_city"),
        "ship_to_state": ship_to.get("ship_to_state"),
        "ship_to_zip": ship_to.get("ship_to_zip"),
        "lines": items,
    }


def _parse_label_page(text: str, page_num: int) -> dict[str, Any] | None:
    packing = _parse_packing_slip_page(text, page_num)
    if packing:
        return packing
    tracking = _extract_tracking_number(text)
    ship_to = _extract_ship_to_name(text)
    if tracking:
        return {"tracking_number": tracking, "ship_to": ship_to or "Unknown", "page": page_num}
    return None


def _extract_tracking_number(text: str) -> str | None:
    patterns = [
        r'(1Z[0-9A-Z]{16,20})',  # UPS
        r'(\d{20,22})',  # FedEx
        r'(\d{12,15})',  # USPS
        r'(9\d{15,21})',  # FedEx alternate
        r'([A-Z]{2}\d{9}[A-Z]{2})',  # International
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def _extract_order_number(text: str) -> str | None:
    patterns = [
        r'(?:Order|PO|SO)\s*#?\s*[:\s]*(\d{4,10})',
        r'(?:Sales\s+Order|Order\s+Number)\s*[:\s]*(\d{4,10})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _parse_packing_slip_page(text: str, page_num: int) -> dict[str, Any] | None:
    result: dict[str, Any] = {
        "order_number": _extract_order_number(text),
        "tracking_number": _extract_tracking_number(text),
        "ship_to": _extract_ship_to_name(text),
        "items": [],
        "page": page_num,
    }
    item_pattern = re.compile(
        r'(211[468]10SPT|2[14-8]\d{9})\s+.*?(\d{1,4})\s*(?:EA|Each|Units?)?',
        re.IGNORECASE,
    )
    for match in item_pattern.finditer(text):
        sku = _normalize_sku(match.group(1), "")
        qty_str = match.group(2)
        if not sku:
            continue
        qty = _parse_quantity(qty_str)
        if qty <= 10000:
            result["items"].append({"sku": sku, "quantity": qty})
    if result["order_number"] or result["tracking_number"] or result["items"]:
        return result
    return None


def _extract_ship_to_name(text: str) -> str | None:
    ship_to_patterns = [
        r'Ship\s+To\s*:?\s*(.+?)(?:\n\n|\Z)',
        r'Delivery\s+To\s*:?\s*(.+?)(?:\n\n|\Z)',
        r'Recipient\s*:?\s*(.+?)(?:\n\n|\Z)',
    ]
    for pattern in ship_to_patterns:
        ship_to_section = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if not ship_to_section:
            continue
        lines = [l.strip() for l in ship_to_section.group(1).split('\n') if l.strip()]
        if lines:
            return lines[0]
    return None


def parse_sales_orders_pdf(file_bytes: bytes) -> ParseResult:
    try:
        import pdfplumber
    except ImportError:
        return ParseResult(orders=[], lines=[], labels=[], errors=[ParseError(row_index=None, message="pdfplumber not installed")], total_rows_processed=0)
    import io
    errors, orders, labels, lines, total_pages = [], [], [], [], 0
    try:
        logger.info("PDF parse start: size=%s bytes", len(file_bytes))
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                total_pages += 1
                text = _normalize_text(page.extract_text() or "")
                logger.debug("PDF page %s: text_length=%s preview=%s", page_num, len(text), text[:200])
                if not text.strip():
                    if getattr(page, "images", None):
                        errors.append(ParseError(row_index=page_num, message=f"Page {page_num}: Image-based PDF (no text layer). OCR required."))
                    else:
                        errors.append(ParseError(row_index=page_num, message=f"Page {page_num}: No text extracted."))
                    continue
                # Prefer label parsing if no obvious sales order header
                if not re.search(r"SALES\s+ORDER|ORDER\s+NUMBER", text, re.IGNORECASE):
                    label = _parse_label_page(text, page_num)
                    if label:
                        labels.append(label)
                        continue

                order = _parse_silq_sales_order_page(page, text, page_num)
                if order:
                    orders.append(order)
                    for ld in order.get("lines", []):
                        lines.append(ParsedOrderLine(order_number=order["order_number"], order_date=order["order_date"], customer_name=order["customer_name"], sku=ld["sku"], quantity=ld["quantity"], lot_number=ld.get("lot_number")))
                    continue
                label = _parse_label_page(text, page_num)
                if label:
                    labels.append(label)
                    continue
                errors.append(ParseError(row_index=page_num, message=f"Page {page_num}: Unknown format.", raw_data=text[:200]))
    except Exception as e:
        logger.error(f"PDF parse error: {e}", exc_info=True)
        errors.append(ParseError(row_index=None, message=f"Failed to open PDF: {e}"))
    return ParseResult(orders=orders, lines=lines, labels=labels, errors=errors, total_rows_processed=total_pages)


def split_pdf_into_pages(pdf_bytes: bytes) -> list[tuple[int, bytes]]:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        return [(1, pdf_bytes)]
    import io
    pages = []
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page_num in range(len(reader.pages)):
            writer = PdfWriter()
            writer.add_page(reader.pages[page_num])
            buf = io.BytesIO()
            writer.write(buf)
            buf.seek(0)
            pages.append((page_num + 1, buf.getvalue()))
    except Exception:
        return [(1, pdf_bytes)]
    return pages


def parse_single_page_pdf(page_bytes: bytes, page_num: int = 1) -> ParseResult:
    return parse_sales_orders_pdf(page_bytes)