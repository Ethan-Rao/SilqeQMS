# Lot numbers — distribution reconciliation, 6 Oct 2026

**Updated 7 Oct 2026** with the lots confirmed from the manufacturing records.

The reconciliation found 15 `distribution_lines` rows holding a value that was
not a lot number. None could be repaired from a packing slip, because no slip
for that order recorded a lot for that SKU, so they were left uncorrected rather
than inferred: a lot guessed from a neighbouring shipment would misdirect a
recall.

All seven from 2025 onward have since been confirmed and applied. The other
eight are pre-2025 and need no remediation, so nothing is left open.

Valid lot format is `SLQ-` followed by either 8 digits (MMDDYYYY) or an 11-digit
code.

## Resolved and applied

Each was checked against `LotLog.csv` before being written: the lot exists, is
registered to that line's SKU, and was manufactured before the shipment went
out. Where the line carried the entry's primary SKU, the entry header was
updated with it too.

| Dist | Line | Order | Ship date | SKU | Qty | Was | Lot applied |
|-----:|-----:|-------|-----------|-----|----:|-----|-------------|
| 1042 | 1614 | 0000391 | 2026-08-18 | 211610SPT | 20 | `SLQ-` | `SLQ-05132026` |
| 1061 | 1649 | 0000403 | 2026-09-04 | 211610SPT | 20 | `SLQ-` | `SLQ-05132026` |
| 748 | 1181 | 0000125 | 2025-02-21 | 211810SPT | 20 | `SLQ-0000125` | `SLQ-01242025` |
| 776 | 1223 | 0000125 | 2025-06-27 | 211810SPT | 10 | `UNKNOWN` | `SLQ-01242025` |
| 807 | 1266 | 0000223 | 2025-09-16 | 211810SPT | 20 | `SLQ-211810SPT` | `SLQ-01242025` |
| 802 | 1257 | 0000216 | 2025-09-02 | 211410SPT | 3 | `SLQ-211410SPT` | `SLQ-11192024` |
| 923 | 1456 | 0000323 | 2026-05-05 | 211810SPT | 30 | `UNKNOWN` | `SLQ-81020515241` |

The resulting lot consumption is consistent with the lot sizes on record, and
`SLQ-01242025` lands at 366 of its 369 units, which independently corroborates
that the 2025 18 Fr shipments came from it.

| Lot | SKU | Units shipped | Lot size |
|---|---|---:|---:|
| `SLQ-01242025` | 211810SPT | 366 | 369 |
| `SLQ-05132026` | 211610SPT | 520 | 1,910 |
| `SLQ-11192024` | 211410SPT | 161 | 221 |

## Nothing open

Every line from 2025 onward now carries a real lot.

## Pre-2025 — no remediation required

Confirmed 7 Oct 2026 that records before 2025 do not need to be remedied. These
eight lines are left as they are.

| Dist | Line | Order | Ship date | SKU | Qty | Current | Ship-to |
|-----:|-----:|-------|-----------|-----|----:|---------|---------|
| 913 | 1441 | 0000116 | 2024-07-29 | 211410SPT | 20 | `SLQ-211410SPT` | Olive View UCLA Medical Center |
| 913 | 1442 | 0000116 | 2024-07-29 | 211610SPT | 20 | `SLQ-211410SPT` | Olive View UCLA Medical Center |
| 913 | 1443 | 0000116 | 2024-07-29 | 211810SPT | 20 | `SLQ-211410SPT` | Olive View UCLA Medical Center |
| 899 | 1426 | 0000125 | 2024-09-20 | 211810SPT | 20 | `SLQ-000125` | Rancho Los Amigos National Rehab |
| 896 | 1420 | 0000125 | 2024-10-23 | 211810SPT | 20 | `SLQ-0000125` | Rancho Los Amigos National Rehab |
| 892 | 1412 | 0000125 | 2024-11-22 | 211810SPT | 20 | `UNKNOWN` | Rancho Los Amigos National Rehab |
| 888 | 1404 | 0000125 | 2024-12-20 | 211810SPT | 20 | `UNKNOWN` | Rancho Los Amigos National Rehab |
| 887 | 1402 | 0000145 | 2024-12-27 | 211810SPT | 20 | `UNKNOWN` | VAMC San Diego Healthcare |

## How the corruption happened

Three distinct failure modes, which is why a single pattern did not catch them:

1. **SKU written into the lot field** (`SLQ-211410SPT`, `SLQ-211810SPT`) — 4 rows.
   On dist 913 the same value was written to all three SKU lines, so the 16 Fr and
   18 Fr lines carry a 14 Fr-derived value.
2. **Order number written into the lot field** (`SLQ-0000125`, `SLQ-000125`) — 3 rows.
3. **Truncated prefix** (`SLQ-`) — 2 rows, both from the Aug/Sep 2026 ShipStation
   sync, and **`UNKNOWN`** — 6 rows.

Six of the fifteen are the 18 Fr line on Rancho order 0000125, the annual blanket
order, which ships monthly; the 16 Fr line on those same shipments was repaired
from slip evidence (`SLQ-11202024`).

## Resolved: the `SLQ-05021025` lot

Lot `SLQ-05021025` appeared on 2 lines (dist 826 order 0000243, 2025-10-22; dist
847 order 0000267, 2025-12-02) and on dist 826's entry header. It is not a real
lot.

It was first read as a typo for `SLQ-05022025`, which is one character away. That
turned out to be wrong: **both affected lines are 16 Fr (`211610SPT`) while
`SLQ-05022025` is registered to the 18 Fr (`211810SPT`)**. Confirmed as
`SLQ-05012025`, the 16 Fr lot of that vintage, which is what the SKU on the line
implies. Both lines and the entry header have been corrected.

The misspelling is now registered in `LotLog.csv` as a row whose `Correct Lot
Name` is `SLQ-05012025`, so any future occurrence is corrected automatically —
the same way `SLQ-050220` is already handled. The packing slip itself still
reads `SLQ-05021025`, so the source document is worth correcting too.
