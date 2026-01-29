"""
Central constants for the EQMS application.
"""
from __future__ import annotations

# Valid SKUs for SILQ products
VALID_SKUS = frozenset({"211810SPT", "211610SPT", "211410SPT"})

# Excluded SKUs (IFUs, non-device items)
EXCLUDED_SKUS = frozenset({"SLQ-4007", "NRE", "IFU"})

# Item code to SKU mapping
ITEM_CODE_TO_SKU = {
    "21400101003": "211410SPT",
    "21400101004": "211410SPT",
    "21600101003": "211610SPT",
    "21600101004": "211610SPT",
    "21800101003": "211810SPT",
    "21800101004": "211810SPT",
    "211410SPT": "211410SPT",
    "211610SPT": "211610SPT",
    "211810SPT": "211810SPT",
}
