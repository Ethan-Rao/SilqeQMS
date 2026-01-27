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


ITEM_CODE_TO_SKU = {
    '21400101003': '211410SPT',
    '21400101004': '211410SPT',
    '21600101003': '211610SPT',
    '21600101004': '211610SPT',
    '21800101003': '211810SPT',
    '21800101004': '211810SPT',
    '211410SPT': '211410SPT',
    '211610SPT': '211610SPT',
    '211810SPT': '211810SPT',
}

VALID_SKUS = {'211810SPT', '211610SPT', '211410SPT'}
SKIP_ITEM_CODES = {'NRE', 'SLQ-4007', 'IFU'}


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
    match = re.search(r'(\d+)', s)
    if match:
        try:
            qty = int(match.group(1))
            return qty if qty > 0 else 1
        except ValueError:
            pass
    return 1


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u00a0", " ")
    return t


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
    customer_name = "Unknown Customer"
    ship_to_match = re.search(r'Ship\s+To\s*[:\n](.+?)(?=\n\s*\n|Bill\s+To|Shipping\s+Method|$)', text, re.IGNORECASE | re.DOTALL)
    if ship_to_match:
        for line in ship_to_match.group(1).strip().split('\n'):
            line = line.strip()
            if line and not re.match(r'^\d+\s+\w', line) and len(line) > 2:
                customer_name = line
                break

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
                quantity = _parse_quantity(raw_qty)
                lot_number = None
                if len(row) > 3:
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

    return {"order_number": order_number, "order_date": order_date, "ship_date": order_date, "customer_name": customer_name, "lines": items}


def _parse_label_page(text: str, page_num: int) -> dict[str, Any] | None:
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
                logger.info("PDF page %s: text_length=%s preview=%s", page_num, len(text), text[:200])
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