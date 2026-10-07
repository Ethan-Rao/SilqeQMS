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

24 profiles drifted, in three groups.

## A. Stored address is not a street address

9 profiles were created with a person's or practice's name in the
street field, so they have no usable address key at all. The real street is
known from the shipping record and can be adopted directly.

| # | Profile | Stored Ship To | Address on shipments | Shipments |
|---|---|---|---|---|
| 615 | Dr. Alex Nourian | Dr. Alex Nourian, Glendale 91208 | 1808 VERDUGO BLVD STE 110, GLENDALE 91208-1450 | 1 of 1 |
| 618 | Dr. Murphy | Dr. Murphy, Orange Park 32073 | 1895 KINGSLEY AVE STE 903, ORANGE PARK 32073-4410 | 2 of 2 |
| 632 | Dr. Kristy Borawski | Dr. Kristy Borawski, Chapel Hill 27514 | 102 MASON FARM RD FL 3, CHAPEL HILL 27514-4617 | 1 of 1 |
| 638 | Dr. Tomaszewski | Dr. Tomaszewski, Camden 08103 | 3 COOPER PLZ RM 411, CAMDEN 08103-1438 | 1 of 1 |
| 649 | Comprehensive Urology | Attn: Dr. Alex Nourian, Los Angeles 90048 | 8631 W 3RD ST STE 715 STE 1115E, LOS ANGELES 90048-5911 | 1 of 1 |
| 652 | Carolinas Healthcare System | Carolinas Healthcare System, Charlotte 28207 | 1000 BLYTHE BLVD, CHARLOTTE 28203-5812 | 1 of 1 |
| 670 | Dr. Aswani Naidu | Dr. Aswani Naidu, Cary 27518 | 115 KILDAIRE PARK DR STE 108, CARY 27518-8144 | 1 of 1 |
| 673 | Tower Urology/Dr. Matthew Bui | Tower Urology/Dr. Matthew Bui, Los Angeles 90048 | 8635 W 3RD ST STE 1, LOS ANGELES 90048-6102 | 2 of 2 |
| 686 | Dr. Jennifer Peters | Dr. Jennifer Peters, The Villages 32163 | 4989 CALLIHAN CT, THE VILLAGES 32163-5502 | 1 of 1 |

## B. Same building, different spelling

9 profiles carry the same street number as their shipments but a
different spelling — abbreviations (Turnpike vs TPKE, Third vs 3RD), a
suite suffix, or a typo. Adopting the USPS-validated form from the shipping
record is safe; these are the same address.

| # | Profile | Stored Ship To | Address on shipments | Shipments |
|---|---|---|---|---|
| 639 | Jess Velazquez | 1203 Langhorne-Newton Road, Langhorne 19047 | 1203 LANGHRN NWTWN RD STE 225, LANGHORNE 19047-1237 | 1 of 1 |
| 640 | Rio Grande Urology Seconday | 3100 Lee Trevino Suite G, El Paso 79936 | 3100 N LEE TREVINO DR STE G, EL PASO 79936-2116 | 1 of 1 |
| 642 | Siouxland Urology Dakota | 455 Sioux Point Rd., Dakota Dunes 57049 | 455 N SIOUX POINT RD, DAKOTA DUNES 57049-5327 | 1 of 1 |
| 663 | Maria Toucet | 1759 Straits Turnpike, Middlebury 06762 | 1759 STRAITS TPKE STE 2A, MIDDLEBURY 06762 | 1 of 1 |
| 669 | Molly | 13005 South Blvd Suite 135, Loxahatchee 33470 | 13005 SOUTHERN BLVD STE 135, LOXAHATCHEE 33470-9231 | 1 of 1 |
| 672 | Womens Care/Nicole Sultan | 14546 Old Saint Augustine Rd, Jacksonville 32258 | 14546 OLD ST AUG RD STE 402, JACKSONVILLE 32258-5473 | 1 of 1 |
| 674 | Debbie Brunelle | 2845 Hamlin Avenue N, Roseville 55113 | 2845 HAMLINE AVE N, ROSEVILLE 55113-1888 | 1 of 1 |
| 684 | Shaunn Wheaton | 360 Tolland Turnpike, Manchester 06042 | 360 TOLLAND TPKE STE 3B, MANCHESTER 06042-1770 | 1 of 1 |
| 690 | Taylor King | 423 Third Avenue, Suite B, Kingston 18704 | 423 3RD AVE STE B, KINGSTON 18704-5809 | 1 of 1 |

## C. Conflicting address — needs your confirmation

6 profiles disagree with their shipments on the street number or
the town, so one of the two is wrong and the data cannot say which. These are
left untouched.

| # | Profile | Stored Ship To | Address on shipments | Shipments |
|---|---|---|---|---|
| 610 | Harbor UCLA Medical Center | 1000 W Carson Street, Torrance 90509 | 1000 W CARSON ST, TORRANCE 90502-2059 | 42 of 44 |
| 611 | Juistine Delmastro | 38 Powel Avenue, Newport 02840 | 70 KENYON AVE STE 210, WAKEFIELD 02879-4253 | 1 of 1 |
| 636 | Rio Grande Primary | 2201 North Stanton Street, El Paso 79902 | 2210 N STANTON ST, EL PASO 79902-3212 | 1 of 1 |
| 653 | Onawa | 222 15th Street, West Des Moines 50266 | 222 15TH ST, ONAWA 51040-1025 | 1 of 1 |
| 658 | Carolinas Rehabilitation | 1100 Blythe Blvd., Charlotte 28203 | 1000 BLYTHE BLVD, CHARLOTTE 28203-5812 | 1 of 1 |
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

## Separate observation: Health Products For You

HPFY (#620) has 32 sales orders, of which 20 have no shipment attached. The
two streams look deliberate rather than broken: the orders with shipments are
round bulk quantities (10, 20, 30, 40, 50 units) while the orders without are
irregular (5, 6, 8, 9, 11, 12, 13, 14, 15, 16, 19 units), and the two kinds
are interleaved under consecutive order numbers. That is the shape of a
distributor placing per-patient drop-ship orders against bulk replenishments.
Worth confirming, but it does not look like missing distribution records.

## Left for manual review

- Distribution with order number `SO 00001129` — eight digits, no sales order
  link, and the intended order cannot be determined from the data.
- 32 distributions from orders 0000102–0000164 still have no sales order,
  pending the 2024 sales order PDFs.
