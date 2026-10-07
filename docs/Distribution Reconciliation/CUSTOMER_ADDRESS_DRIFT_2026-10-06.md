# Customer address drift — follow-up list

Generated 2026-10-06 after the customer profile alignment pass.

## Why this matters

Customer identity is keyed on the Ship To address, never on the facility
name. When a profile's stored address does not normalise to the same key as
the address its shipments actually carry, two things follow:

1. Importing a future sales order for that site creates a **second profile**
   instead of matching the existing one. Every duplicate merged in this pass
   was created that way.
2. The admin tool that attaches an unmatched distribution to a customer
   cannot resolve the site and has to be done by hand.

None of this changes any current dashboard figure — the shipments are already
attached to the right profiles. It is about preventing the duplicates from
coming back.

**Updated 7 Oct 2026.** 24 profiles had drifted. The 18 whose correct
address the shipping record could prove have been corrected and are listed
under 'Resolved' at the end. What remains is the set where the stored
address and the shipped address genuinely disagree.

5 profiles are still drifted.

## A. Stored address is not a street address

0 profiles have a person's or practice's name in the street field,
so they have no usable address key at all.

None remaining — all were corrected on 7 Oct 2026.

## B. Same building, different spelling

0 profiles carry the same street number and ZIP as their shipments
but a different spelling — abbreviations (Turnpike vs TPKE, Third vs 3RD), a
suite suffix, or a typo.

None remaining — all were corrected on 7 Oct 2026.

## C. Conflicting address — needs your confirmation

5 profiles disagree with their shipments on the street number or
the town, so one of the two is wrong and the data cannot say which. These are
left untouched.

| # | Profile | Stored Ship To | Address on shipments | Shipments |
|---|---|---|---|---|
| 610 | Harbor UCLA Medical Center | 1000 W Carson Street, Torrance 90509 | 1000 W CARSON ST, TORRANCE 90502-2059 | 42 of 44 |
| 611 | Juistine Delmastro | 38 Powel Avenue, Newport 02840 | 70 KENYON AVE STE 210, WAKEFIELD 02879-4253 | 1 of 1 |
| 636 | Rio Grande Primary | 2201 North Stanton Street, El Paso 79902 | 2210 N STANTON ST, EL PASO 79902-3212 | 1 of 1 |
| 653 | Onawa | 222 15th Street, West Des Moines 50266 | 222 15TH ST, ONAWA 51040-1025 | 1 of 1 |
| 666 | Ethan Rao | 607 Charles E Yound Drive E, Los Angeles 90095 | MSB 2224, LOS ANGELES 90095-0001 | 3 of 3 |

Notes on group C:

- **#611 Juistine Delmastro** — stored `38 Powel Avenue, Newport RI`, shipped
  `70 KENYON AVE STE 210, WAKEFIELD RI`. Different towns entirely.
- **#636 Rio Grande Primary** — `2201` vs `2210 N Stanton St`, a likely digit
  transposition, but either could be the real one.
- **#653 Onawa** — same street number but stored as `West Des Moines IA 50266`
  against a shipment to `ONAWA IA 51040`. The profile name matches the
  shipment, so the stored city and ZIP are probably the wrong ones.
- **#658 Carolinas Rehabilitation** — stored `1100 Blythe Blvd.`, shipped
  `1000 BLYTHE BLVD`, which is also where #652 Carolinas Healthcare System
  shipped. If those two profiles are one site they should be merged.
- **#666 Ethan Rao** — shipped to `MSB 2224, LOS ANGELES 90095`, a UCLA
  building code rather than a street. The stored `607 Charles E Yound Drive E`
  also misspells `Young`.

## Resolved on 7 Oct 2026

Eighteen profiles took the USPS-validated address from their own shipping
records, and their address keys were recomputed to match. Nine of them had a
person's name where the street should be; where that name was not already the
profile name it was kept as the contact. Carolinas Rehabilitation was merged
into Carolinas Healthcare System, both having shipped to 1000 Blythe Blvd.

The practical effect is that importing a future order for any of these sites
now matches the existing profile instead of creating a duplicate. Distributions
whose ship-to cannot be resolved to a unique customer fell from 49 to 28.

## Profiles that drifted on only some shipments

Two Aspirus profiles already key correctly for part of their history, so they
are not in the tables above, but their shipments are inconsistent:

- **#614 Aspirus Urology Wausau** — stored `3300 Westhill Dr.`; ten shipments
  say `330 Westhill Drive` with no ZIP+4, one says `3300 WESTHILL DR` with
  ZIP+4 `54401-4710`. Only the `3300` form carries USPS validation, so the
  stored address is most likely right and the repeated `330` is a copied typo.
  This is the drift that produced the duplicate profile merged in this pass.
- **#625 Aspirus Wisconsin Rapids** — three shipments to `400 DEWEY ST` and
  three to `410 DEWEY ST`, both with ZIP+4 `54494-4715`. Needs confirmation of
  which building, or whether both are in use.

## Separate observation: profiles named after people

Twenty-two profiles are filed under an individual's name rather than the
facility. One of them, `Gina Koehler`, turned out to be a duplicate of
Cleveland Clinic Foundation and was merged in this pass. The rest each have
their own address and are not duplicates of anything, so they were left
alone — but they read oddly on the sales dashboard, where they appear as
customers alongside hospital names.

## Closed: Health Products For You orders without shipments

HPFY (#620) has 32 sales orders, of which 20 have no shipment attached. The
orders with shipments are round bulk quantities (10, 20, 30, 40, 50 units)
while the orders without are irregular (5, 6, 8, 9, 11, 12, 13, 14, 15, 16,
19 units), and the two kinds are interleaved under consecutive order numbers.

Confirmed 7 Oct 2026 that these orders are not relevant to distribution
tracking and can be disregarded. They are not missing distribution records.

## Left for manual review

- **#610 Harbor UCLA Medical Center** — stored ZIP `90509` against `90502` on
  all 43 shipments, same street. 90509 is the PO box ZIP and 90502 the street
  ZIP, so this is very likely safe to adopt, but it was held back because the
  ZIP differs rather than just the spelling.
- Distribution with order number `SO 00001129` — eight digits, no sales order
  link, and the intended order cannot be determined from the data.
- 30 distributions from 2024 orders still have no sales order. Confirmed
  7 Oct 2026 that pre-2025 records need no remediation. Sales order 0000145
  was recovered from its PDF and its two shipments linked; 0000164 is still
  outstanding.
