"""
Central constants for the EQMS application.
"""
from __future__ import annotations

# Valid SKUs for SILQ products. 20 Fr and 22 Fr are box-of-10 catalogs.
VALID_SKUS = frozenset({
    "211410SPT",
    "211610SPT",
    "211810SPT",
    "212010SPT",
    "212210SPT",
})

# Excluded SKUs (IFUs, non-device items)
EXCLUDED_SKUS = frozenset({"SLQ-4007", "NRE", "IFU"})

# Item code to SKU mapping.
# 003 is a box of 10. 004 is one unit. Confirmed for 20 Fr and 22 Fr on 27 October 2026.
ITEM_CODE_TO_SKU = {
    "21400101003": "211410SPT",
    "21400101004": "211410SPT",
    "21600101003": "211610SPT",
    "21600101004": "211610SPT",
    "21800101003": "211810SPT",
    "21800101004": "211810SPT",
    "22000101003": "212010SPT",
    "22000101004": "212010SPT",
    "22200101003": "212210SPT",
    "22200101004": "212210SPT",
    "211410SPT": "211410SPT",
    "211610SPT": "211610SPT",
    "211810SPT": "211810SPT",
    "212010SPT": "212010SPT",
    "212210SPT": "212210SPT",
}

# Box-label GTINs. Both new GTINs contain the digits 14. They are not SKUs.
# The older 14/16/18 Fr box GTINs are listed too so the digit heuristic cannot
# record them as 14 Fr.
UNMAPPED_GTINS = frozenset({
    "10850041415137",
    "10850041415151",
    "10850041415168",
    "10850041415175",
    "10850041415182",
})

DISTRIBUTION_SKU_CHECK_SQL = (
    "sku IN ('211410SPT','211610SPT','211810SPT','212010SPT','212210SPT')"
)
