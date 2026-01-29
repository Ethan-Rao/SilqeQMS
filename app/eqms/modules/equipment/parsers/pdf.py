"""PDF parsing utilities for equipment and supplier documents."""
from __future__ import annotations

import logging
import re
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
                page_text = page.extract_text() or ""
                text.append(page_text)
    except Exception as e:
        logger.warning("PDF text extraction failed: %s", e)
        return ""
    return "\n".join(text)


def extract_equipment_fields_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract equipment-related fields from a PDF document.

    Returns a dict of field_name -> extracted_value.
    Values are suggestions only - admin can override all of them.
    """
    full_text = _extract_text(pdf_bytes)
    if not full_text:
        return {}

    extracted: dict[str, Any] = {}

    patterns = {
        "equip_code": [
            r"(?:Equipment\s*ID|Equip\.?\s*ID|Asset\s*ID)[:\s]*([A-Z]{1,4}-?\d{2,6})",
            r"(?:ID)[:\s]*([A-Z]{1,4}-\d{2,6})",
        ],
        "description": [
            r"(?:Equipment\s*Type|Equipment\s*Name)[:\s]*([^\n]{3,100})",
            r"(?:Description)[:\s]*([^\n]{3,100})",
            r"(Weighing\s+Scale|Balance|Thermometer|Timer|Incubator)[^\n]*",
        ],
        "mfg": [
            r"(?:Manufacturer|Mfg|Make)[:\s]*([^\n]{2,100})",
        ],
        "model_no": [
            r"(?:Model\s*(?:No\.?|Number)?|Model)[:\s]*([^\n]{2,50})",
        ],
        "serial_no": [
            r"(?:Serial\s*(?:No\.?|Number)?|S/N)[:\s]*([^\n]{2,50})",
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


def extract_supplier_fields_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Extract supplier-related fields from a PDF document.

    Returns a dict of field_name -> extracted_value.
    Values are suggestions only - admin can override all of them.
    """
    full_text = _extract_text(pdf_bytes)
    if not full_text:
        return {}

    extracted: dict[str, Any] = {}

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
            r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
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
