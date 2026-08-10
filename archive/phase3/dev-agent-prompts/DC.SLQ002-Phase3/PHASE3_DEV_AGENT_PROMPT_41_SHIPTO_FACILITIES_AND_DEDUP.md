# Prompt 41 — Ship-To facility identity, distribution dedupe, NRE orphan cleanup

## Context

Prompt 40 is live (`77c5686` / `62516fd`). Alembic parent: **`d6e7f8a9b0c1`** (single head). Chain any new migration from it.

Ethan paused regenerating the cumulative distribution Excel until this prompt lands. Do **not** regenerate the Excel as part of this work.

### Problems observed

1. **Distribution Log duplicates** for SO `0000312` (Harbor UCLA / `HARBOR-UCLA MEDICAL CENTER`) and SO `0000302` (Riverside / `RCRMC`): two ShipStation rows per SO — one linked to the PDF sales order (canonical name), one unmatched with the raw ship-to string. These two cases are **true duplicates**; the unmatched orphan row should be **deleted**.
2. **Facility identity is wrong for multi-site payers** (esp. Marathon Medical): one company pays for many Ship-To sites. The system must treat distinct Ship-To locations as distinct catheter facilities. **No Customer Profile for “Marathon Medical” as a single entity.**
3. **NRE orphan after SO delete:** Catheter SO `0000366` (Day Kimball Health) was imported from `July26SalesOrders.pdf` **without** a matching distribution, so `_nre_customers` auto-classified it as NRE. Ethan deleted the sales order, but the **Day Kimball NRE customer profile / dashboard row still appears**. NRE must refresh when the last qualifying SO is gone; remediate Day Kimball now.

Auto-deploy after green suite. Coordinator will re-export the distribution log and regenerate the Excel afterward.

---

## Decisions (do not re-ask)

| # | Decision |
|---|---|
| Facility key | Ship-To **`address1 + city + state + zip`**. **Ignore `address2` entirely** for matching (suite/floor variants stay one facility). If address is incomplete, use normalized facility/company name as a **tie-break** (with city/state/zip when present). |
| Marathon / multi-site | **One facility Customer per distinct Ship-To.** Do not keep a single Marathon parent profile. |
| True duplicate dists | When two rows look like the same shipment (see Task C), **delete the unmatched orphan**; keep the row linked to the sales order. |
| Legitimate multi-shipment | Some SOs really have multiple distributions — **keep both** when they are not true duplicates (different lines/qty/lots and/or meaningfully different ship-to). |
| Auto-dedupe rule | Auto-dedupe when same normalized SO + same ship date + **identical line SKUs/qtys/lots** even if `ss_shipment_id` differs → delete unmatched orphan. |
| Remap scope | **Full catheter facility rebuild** by Ship-To rules + merge/split customers + relink distributions. |
| Alias cleanup | Merge alias customers (`RCRMC`→Riverside, Harbor case variants, etc.), re-point FKs, **delete empty shells**. |
| NRE vs catheter | Ship-To facility model applies to **catheter / distribution customers only**. **NRE stays company-level** (current Sold-To / company behavior). |
| Durable code | Normalize order-number matching in ShipStation sync; rematch unmatched dists on PDF upsert; one-shot remediation script; NRE orphan cleanup on SO delete. |
| Excel | Out of scope — Ethan regenerates after this ships. |

---

## Task A — Ship-To facility key (catheter)

**Files:** `app/eqms/modules/customer_profiles/utils.py` (extend; there is already `compute_customer_key_from_sales_order` — revise to match decisions), plus call sites in PDF import / distribution matching / ShipStation sync.

### A1. Key algorithm (catheter facilities)

Build a stable key for catheter facility Customers:

1. Normalize `address1` (trim, collapse whitespace, uppercase for key material). **Do not include `address2`.**
2. Normalize city / state / zip (zip: first 5 digits when US ZIP+4).
3. If `address1 + city + state + zip` are all present →  
   `canonical_customer_key(f"{address1}|{city}|{state}|{zip}")`  
   (or equivalent; document the exact format in code comments).
4. If address incomplete → append / fall back with normalized facility name + whatever address parts exist (name as tie-break per decision 1B).
5. **Do not** use a payer account / customer number alone as the sole key when that would collapse multiple Ship-To sites (Marathon). Prefer Ship-To address key for catheter facilities.

Display `facility_name` for the facility Customer: prefer Ship-To name / company string from the shipment or SO, cleaned; include city in the display name when useful for Marathon-style sites (e.g. `Marathon Medical Corporation — Long Beach`) **or** keep legal ship-to name and rely on address fields — pick one consistent approach and document it. Cards/lists should make sites distinguishable.

### A2. Wire into create/match paths

- PDF SO import `find_or_create_customer` (or successor): for **catheter** orders, create/match facility Customers by the Ship-To key above (using SO ship-to fields / parse dict).
- ShipStation distribution create: when matching/creating facility association, use distribution ship-to address fields with the same key.
- **NRE / non-catheter company customers:** leave existing company-level identity (do not force Ship-To splitting on pure NRE accounts).

Use `_is_catheter_order` / catheter SKU detection already in the codebase to decide which path applies.

---

## Task B — Durable import / sync fixes

### B1. ShipStation: normalize order number when linking SalesOrder

**File:** `app/eqms/modules/shipstation_sync/service.py` (and any exact `order_number ==` lookups).

Resolve `SalesOrder` via `normalize_order_number` (same helper as PDF path in `rep_traceability/service.py`) so `SO 0000312`, `0000312`, and spaced variants match.

When a match is found: set `sales_order_id`, `customer_id`, and set `facility_name` from the facility Customer (or SO customer when appropriate) — same as `match_distribution_to_sales_order` behavior.

### B2. PDF upsert: rematch unmatched distributions

**File:** `app/eqms/modules/rep_traceability/admin.py`

On PDF import **CREATE and UPSERT**, after the SO exists, run the unmatched-distribution rematch loop (today CREATE does this; UPSERT often `continue`s without it). Rematch all `DistributionLogEntry` rows whose normalized order number matches and `sales_order_id` is null.

### B3. `create_distribution_entry`

Use `normalize_order_number` for SO auto-link (not exact string only).

---

## Task C — Duplicate distribution remediation

### C1. Coordinator script (dry-run default)

`scripts/_remediate_distribution_facilities.py`

**Phase 1 — True-duplicate deletion (SO 302, 312, and general rule)**

For each normalized order number that has ≥2 `shipstation` distribution rows:

- Load lines (SKU/qty/lot) for each row.
- If ship dates match (or both null-safe equal) **and** line multisets of (sku, qty, lot) are identical **and** one row has `sales_order_id` and another does not → **delete the unmatched orphan** (and its lines / packing-slip attachments / storage blobs). Keep the linked row.
- Always include SO `0000302` and `0000312` in the report; they are confirmed true duplicates.
- If both are linked or both unmatched but still identical lines/date → keep the row with `sales_order_id` if any; else keep the lower `id`; delete the other. Log clearly.
- If lines/qty differ → **keep both** (legitimate multi-shipment). Report as `KEEP_MULTI`.

**Phase 2 — Relink remaining unmatched**

For every distribution with `sales_order_id IS NULL` whose normalized order number matches a `SalesOrder`: link `sales_order_id` / `customer_id` / refresh `facility_name` (do **not** create customers from raw `RCRMC` / `HARBOR-UCLA` strings alone).

**Phase 3 — Full catheter facility rebuild**

1. Compute Ship-To facility keys for all catheter-related distributions and catheter SOs.
2. Ensure one Customer per facility key (create missing; merge aliases that normalize to the same key).
3. Re-point `DistributionLogEntry.customer_id` and catheter `SalesOrder.customer_id` to the correct facility Customer.
4. Merge obvious alias shells (`RCRMC` into Riverside facility, Harbor case variants, etc.) using existing `merge_customers()` if available (`customer_profiles/service.py` / `scripts/dedupe_customers.py` patterns).
5. Delete empty customer shells (no SOs, no distributions, no notes worth keeping — if notes exist, merge notes onto survivor first).
6. **Do not** invent a single Marathon Medical customer. Distinct Ship-Tos stay distinct.

CLI:

```text
python scripts/_remediate_distribution_facilities.py            # dry-run report
python scripts/_remediate_distribution_facilities.py --execute  # apply
```

Print counts: deleted dupes, relinked, merged customers, deleted shells, KEEP_MULTI list.

**Safety:** Audit log important deletes/merges. Prefer dry-run clarity. No `--force` that deletes multi-shipment keepers.

---

## Task D — NRE refresh after sales order delete (+ Day Kimball)

### D1. Why Day Kimball appeared

SO `0000366` had catheter SKU `211610SPT` but **no** distribution → `_nre_customers` treated the customer as auto-NRE (`has SO` and `no matched distribution`). That is the wrong classification for catheter product.

### D2. Durable classification tweak

Update `_nre_customers` (and any parallel helpers) so **auto** NRE excludes customers whose sales orders are **catheter orders** (existing `_is_catheter_order` / SKU rules), even when no distribution is linked.

Forced `customer_type == "nre"` still included; `customer_type == "catheter"` still excluded.

### D3. Sales order delete → NRE/customer cleanup

There may be no first-class SO delete route today (verify). Implement or harden delete so that when a `SalesOrder` is deleted:

1. Cascades behave safely (lines, PDF attachments, storage cleanup).
2. If the SO’s Customer then has **zero remaining SalesOrders** and **zero distributions** and `customer_type == "auto"`:
   - Delete the orphan Customer (and empty NRE folder scaffolding only if safe / unused), **or** equivalent cleanup so it **cannot** appear on `/admin/nre-projects/`.
3. Flash a clear message. Audit the delete.

If delete UI only exists in one module (NRE detail / sales admin), wire cleanup there. If missing entirely, add a permission-gated delete on the NRE order card and/or sales order detail — minimal UI.

### D4. Immediate remediation for Day Kimball

In the remediation script (or a small dedicated section):

1. Find Customer Day Kimball / `DAYKIMBALL` / SO number `0000366`.
2. If SO `0000366` still exists → delete it (user-confirmed intent) with storage cleanup.
3. If Customer remains with no SOs and no distributions → delete customer shell.
4. Confirm it no longer appears in `_nre_customers` / NRE dashboard.

Dry-run must print what would happen to Day Kimball before `--execute`.

---

## Task E — Tests

Add `tests/test_p41_shipto_facilities.py` (name flexible):

1. Facility key: same address1/city/state/zip with different address2 → **same** key.
2. Same Marathon payer name, different cities/addresses → **different** keys.
3. Duplicate dist deletion: identical lines + one linked + one unmatched → orphan deleted.
4. Multi-shipment keep: different qty/SKU sets → both kept.
5. `normalize_order_number` ShipStation-style link finds PDF SO.
6. Auto-NRE excludes catheter SKU SO with no distribution.
7. After deleting last SO on an auto customer with no dists, customer gone / not in `_nre_customers`.
8. Harbor / RCRMC-style relink: unmatched row with raw name links to SO customer after rematch helper.

Full suite green; single Alembic head; `import app.wsgi` OK.

---

## Task F — Deploy + handoff

1. Commit + push `main`.
2. Completion report must include:
   - Migration id (if any — may be none if key logic is code-only; schema only if you add columns/flags)
   - How to run remediation dry-run / execute on production
   - Counts from a local dry-run against fixtures or a safe local DB if available
   - Explicit note: **Day Kimball / SO 0000366 cleanup steps**
   - Explicit note: **Ethan should re-export distribution log and regenerate cumulative Excel after `--execute` on prod**
3. Do **not** run production `--execute` unless the environment is clearly production and the prompt runner is the coordinator with credentials — prefer shipping the script and documenting the command for the coordinator (Ethan). If the agent routinely runs prod scripts with `--execute` for remediations (as with training backfills), dry-run first, then execute, and paste the summary.

---

## Out of scope

- Regenerating `catheter_distributions_cumulative_by_customer_20260801.xlsx`
- Changing Upcoming Payments / Invoices Received
- Forcing NRE customers onto Ship-To facility identity
- Creating a Marathon parent/child ORM hierarchy (flat per-Ship-To Customers only)

---

## Reference

- Duplicate evidence: `distribution_log_export_20260730.csv` (SO 0000302, SO 0000312)
- NRE classifier: `app/eqms/modules/nre_projects/admin.py` → `_nre_customers`
- Customer key utils: `app/eqms/modules/customer_profiles/utils.py`
- Merge helpers: `app/eqms/modules/customer_profiles/service.py`, `scripts/dedupe_customers.py`
- ShipStation: `app/eqms/modules/shipstation_sync/service.py`
- PDF import / match: `app/eqms/modules/rep_traceability/admin.py` (`match_distribution_to_sales_order`, upsert gaps)
- Order normalize: `normalize_order_number` in `rep_traceability/service.py`
- Prior Excel alias logic (reporting only): `scripts/_build_cumulative_distributions_xlsx.py`

---

## Acceptance checklist

- [ ] SO 302 and 312 show **one** distribution row each (or two only if truly different shipments — these two should be one after dedupe)
- [ ] Harbor / Riverside facility labels consistent on remaining rows
- [ ] Marathon sites are separate facility Customers (no single Marathon profile required for distributions)
- [ ] Day Kimball gone from NRE index + dashboard
- [ ] New catheter SO without distribution does **not** appear as auto-NRE
- [ ] Deleting a lone auto-NRE SO removes the orphan customer from NRE
- [ ] Remediation script dry-run / execute documented

---

End of Prompt 41.
