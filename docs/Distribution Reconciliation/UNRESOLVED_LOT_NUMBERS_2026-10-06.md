# Unresolved lot numbers — distribution reconciliation, 6 Oct 2026

15 `distribution_lines` rows hold a value that is not a lot number. None could be
repaired from a packing slip, because no slip for that order records a lot for
that SKU. They were deliberately left uncorrected rather than inferred: a lot
guessed from a neighbouring shipment would misdirect a recall.

To fix each one, enter the lot that was actually picked for that SKU on that ship
date from the manufacturing/shipping records, then update the
`distribution_lines` row (and the parent `distribution_log_entries.lot_number`
where it is the entry's primary SKU).

Valid lot format is `SLQ-` followed by either 8 digits (MMDDYYYY) or an 11-digit
code.

| Dist | Line | Order | Ship date | SKU | Qty | Current (invalid) | Ship-to | Correct lot |
|-----:|-----:|-------|-----------|-----|----:|-------------------|---------|-------------|
| 913 | 1441 | 0000116 | 2024-07-29 | 211410SPT | 20 | `SLQ-211410SPT` | Olive View UCLA Medical Center | |
| 913 | 1442 | 0000116 | 2024-07-29 | 211610SPT | 20 | `SLQ-211410SPT` | Olive View UCLA Medical Center | |
| 913 | 1443 | 0000116 | 2024-07-29 | 211810SPT | 20 | `SLQ-211410SPT` | Olive View UCLA Medical Center | |
| 899 | 1426 | 0000125 | 2024-09-20 | 211810SPT | 20 | `SLQ-000125` | Rancho Los Amigos National Rehab | |
| 896 | 1420 | 0000125 | 2024-10-23 | 211810SPT | 20 | `SLQ-0000125` | Rancho Los Amigos National Rehab | |
| 892 | 1412 | 0000125 | 2024-11-22 | 211810SPT | 20 | `UNKNOWN` | Rancho Los Amigos National Rehab | |
| 888 | 1404 | 0000125 | 2024-12-20 | 211810SPT | 20 | `UNKNOWN` | Rancho Los Amigos National Rehab | |
| 887 | 1402 | 0000145 | 2024-12-27 | 211810SPT | 20 | `UNKNOWN` | VAMC San Diego Healthcare | |
| 748 | 1181 | 0000125 | 2025-02-21 | 211810SPT | 20 | `SLQ-0000125` | Rancho Los Amigos National Rehab | |
| 776 | 1223 | 0000125 | 2025-06-27 | 211810SPT | 10 | `UNKNOWN` | Rancho Los Amigos National Rehab | |
| 802 | 1257 | 0000216 | 2025-09-02 | 211410SPT | 3 | `SLQ-211410SPT` | Hackensack University Medical Center | |
| 807 | 1266 | 0000223 | 2025-09-16 | 211810SPT | 20 | `SLQ-211810SPT` | Health Products For You | |
| 923 | 1456 | 0000323 | 2026-05-05 | 211810SPT | 30 | `UNKNOWN` | Health Products For You | |
| 1042 | 1614 | 0000391 | 2026-08-18 | 211610SPT | 20 | `SLQ-` | Tom Lamb (Comedical) | |
| 1061 | 1649 | 0000403 | 2026-09-04 | 211610SPT | 20 | `SLQ-` | Harbor UCLA Medical Center | |

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

## Separate observation: a suspected typo left alone

Lot `SLQ-05021025` appears on 2 lines (dist 826 order 0000243, dist 847 order
0000267). It is almost certainly a typo for `SLQ-05022025`, but the packing slip
itself also reads `SLQ-05021025`, so the error is in the source document. It was
not silently corrected. Confirm against the manufacturing record and correct both
the slip and the record together.
