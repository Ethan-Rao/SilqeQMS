# Prompt 42 — Usability / reliability sweep + Admin Tools cleanup

## Context

Auto-deploy after a green suite (same pattern as prior Phase 3 prompts).

**Alembic parent:** current single head (expected `d6e7f8a9b0c1` if P41 added no migration; if P41 landed a newer head, chain from that). Confirm single head after any new migration.

This prompt is **usability and reliability focused** — not greenfield features. Ethan’s must-haves are Purchasing line-item visibility, NRE tracker/dashboard status behavior, Equipment fixes, Admin Tools cleanup (including an unmatched-distributions workspace), plus a short list of reliability polish items.

---

## Decisions (do not re-ask)

| Topic | Decision |
|---|---|
| Purchasing line items | Always show a **compact summary** under each Upcoming Payments row (description + amount). Click summary (or a clear control) to expand the full editor. |
| NRE Tracker Status | **Free-text** field (no dropdown). Keep existing stored values as-is (no status migration). |
| NRE Dashboard Status | **New persisted field** on `SalesOrder` (or NRE-only side table keyed by SO — prefer column on `SalesOrder`). Preset dropdown only. |
| Dashboard status options (exact labels) | `Pending Invoice` · `50% Invoiced` · `100% Invoiced` · `Payment Received` |
| Defaults | SOs with `order_date` **before today** → default `100% Invoiced`. **New** uploads / newly created SOs → default `Pending Invoice`. |
| Total Amount Invoiced math | Pending = 0%; 50% Invoiced = 0.5 × `order_amount`; 100% Invoiced = 100%; Payment Received = 100%. Null amount = 0 for the sum; show `$—` (not `$0.00`) when amount is null in the table. |
| Dashboard Status column | **Replace** the SO lifecycle badge (`completed` etc.) with the invoice-status dropdown only. |
| Equipment | Fix Cal/PM **schedule 500** and list **“16 Active / Showing 0 of 0”** mismatch. |
| Admin Tools | Primary focus: clean up the messy page; add unmatched-distributions mini workspace with full manual control. |
| Hardcoded paths | Replace remaining hardcoded `/admin/...` JS paths with `url_for` / data attributes. |
| Catheter SO without distribution | Surface a **clear warning** on Sales Order import (do not silently treat as NRE without notice). |
| Weekly Brief payments | Merge **Invoices Received** into the **same table** as Upcoming Payments. In the first column, append a muted note **`(Received)`** for rows that come from Invoices Received. Remove the separate Invoices Received section. |
| Spelling | Use corrected UI labels: **100% Invoiced**, **Payment Received**, and **`(Received)`** (not “Recieved”). |

---

## Task A — Purchasing: always-visible line item summary

**File:** `app/eqms/templates/admin/purchasing/list.html` (+ any JS helpers)

1. For each Upcoming Payments entry that has line items, always render a compact muted summary under the main row (e.g. `• Desc — $1,234.00` lines, or a one-line “3 line items · $x,xxx” plus first few descriptions).
2. Clicking the summary (or a **Line items (N)** control) expands the existing full editor panel (same CRUD/files as today).
3. Entries with zero line items: show muted “No line items” + control to add (do not force an empty expanded panel).
4. Toggle label when expanded: **Hide line items**. Count in the collapsed control: **Line items (N)**.
5. Currency-format amounts consistently with the parent Amount column.

No schema change required unless you need a denormalized count (prefer loading line items with the list query / existing JSON endpoint).

---

## Task B — NRE Tracker: free-text Status

**Files:** `nre_projects/models.py`, `admin.py`, `index.html`, weekly brief email badge handling if needed.

1. Upcoming NRE Invoice Tracker **Status** column: replace `<select>` of `INVOICE_STATUSES` with a plain text `<input>`.
2. Validation: accept any non-empty or empty string as stored; stop rejecting values not in `INVOICE_STATUSES`.
3. Keep `INVOICE_STATUSES` only if still useful elsewhere, or retire from tracker UI. Do **not** bulk-rewrite existing tracker rows.
4. Weekly Brief: render tracker status as plain text (or a neutral badge), not a fixed color map that breaks on free text.
5. Rename is already “Upcoming NRE Invoice Tracker” — leave title unless inconsistent.

---

## Task C — NRE Dashboard: invoice status + Total Amount Invoiced

### C1. Model + migration

Add nullable-or-default column on `SalesOrder`, e.g.:

```text
nre_invoice_status: String(32), nullable=False,
  server_default / app default handled carefully for existing rows
```

Allowed values (enforce in apply/patch):

```python
NRE_DASHBOARD_STATUSES = [
    "Pending Invoice",
    "50% Invoiced",
    "100% Invoiced",
    "Payment Received",
]
```

**Backfill on migrate or in upgrade data step:**

- If `order_date < date.today()` → `100% Invoiced`
- Else → `Pending Invoice`

**On create** (PDF import / manual SO create): default **`Pending Invoice`** (new work), regardless of backfill rule for historical rows.

### C2. Dashboard UI

**File:** `templates/admin/nre_projects/index.html` + `nre_projects/admin.py`

1. Rename tile **Total revenue** → **Total Amount Invoiced**.
2. Recompute tile using filtered SOs in the date window:

   | Status | Contribution |
   |---|---|
   | Pending Invoice | `0` |
   | 50% Invoiced | `0.5 * order_amount` (null amount → 0) |
   | 100% Invoiced | `1.0 * order_amount` |
   | Payment Received | `1.0 * order_amount` |

3. Project table **Status** column: dropdown with the four options only (replace lifecycle `completed` badge). Saving updates `nre_invoice_status` (inline POST/PATCH; CSRF; `sales_orders.edit`).
4. Null `order_amount` display as **$—**, not `$0.00`.
5. Keep Invoice Date edit as today.

### C3. Optional small route

`POST /admin/nre-projects/<customer_id>/orders/<order_id>/invoice-status` or a dashboard-scoped patch — mirror the existing invoice-date route pattern.

---

## Task D — Equipment reliability

### D1. List: “16 Active / Showing 0 of 0”

**Files:** `equipment/admin.py`, `list.html`

Known issues:

- Default `status_filter = "Active"` even when user selects **All** (`""` coerced back to Active).
- Exact `status == "Active"` excludes rows whose lifecycle status is `Calibration Overdue` / `PM Overdue` while summary/overdue tiles still count them.
- Admin Tools overdue links often pass `cal_overdue=1` without clearing status → empty list.

Fix:

1. Treat missing status query param as default Active; treat explicit `status=` empty as **All**.
2. Fix template selected-state for All vs Active.
3. When `cal_overdue` / `pm_overdue` / `service_overdue` is set, **do not** force Active-only unless the user also chose Active — prefer All + overdue filter so rows appear.
4. Normalize any non-canonical status strings found in DB to `VALID_STATUSES` if a quick query shows drift (optional one-shot in a tiny script or migrate data step — only if needed).
5. Verify: with Active selected, list count matches summary Active; overdue deep-links show overdue rows.

### D2. Schedule 500 at `/admin/equipment/schedule`

**File:** `equipment/admin.py` → `equipment_schedule`

Harden:

- Avoid crashing on missing supplier associations / null suppliers / document load failures.
- Eager-load safely or lazy-load with guards in template/`_cal_provider`.
- Add a focused test or at least ensure the route returns 200 with empty/fixture equipment in the test suite.
- If the root cause is a specific bug (AttributeError, etc.), fix that root cause — don’t just swallow all exceptions silently without logging.

---

## Task E — Admin Tools cleanup (focus)

**Files:** `app/eqms/templates/admin/diagnostics.html`, `app/eqms/admin.py` (`diagnostics` / `_dashboard_stats`)

### E1. Page reorganization (cleanup, not a new product)

Goals: less duplicate “System Status”, clearer grouping, fewer dead ends.

1. Single top **System Status** band (merge the tile strip + collapse deep diagnostics into one accordion or details block).
2. Group the card grid into clearer sections with short headings:
   - **Accounts & Access**
   - **Imports & Sync** (uploads, ShipStation, CSV/PDF imports)
   - **Records & Tracing** (Distribution Entry, Sales Orders, Tracing Reports)
   - **System** (Audit Trail, Storage Info)
3. **Danger zone** footer: Reset Data only (visually separated).
4. Fix Equipment schedule / overdue links so they work after Task D (correct query params).
5. Copy: page title / heading consistently **Admin Tools** (route may stay `/admin/diagnostics` for bookmarks).

Do **not** rebuild the main Dashboard (`/admin/`). This task is the Admin Tools page only.

### E2. Unmatched Distributions mini workspace

Add a dedicated section on Admin Tools (or `/admin/diagnostics/unmatched-distributions` linked from Admin Tools) for rows where `DistributionLogEntry.sales_order_id IS NULL`.

**Ethan needs total manual control.** Minimum capabilities:

| Capability | Behavior |
|---|---|
| List | Table: Ship Date, Order #, Facility, City/State, Units, Source, `ss_shipment_id`, Actions |
| Open | Link to existing distribution detail/edit |
| Link to Sales Order | Manual control: pick/search SO by normalized order number (or enter SO id) and set `sales_order_id` + `customer_id` + refresh `facility_name` from SO customer |
| Clear link | Unset `sales_order_id` / optionally clear customer if desired |
| Delete | Delete distribution entry with confirm + reason if existing delete flow requires it |
| Create / edit | Link out to “+ Distribution Entry” or inline edit of facility/address fields if already supported on detail page — do not block on building a full second editor if detail page already allows edits |

Also add `unmatched=1` (or equivalent) filter support on the main Distribution Log list so the Admin Tools count can deep-link there as a secondary path.

Show the current unmatched count prominently; empty state when zero.

Permissions: reuse `distribution_log.view` / `.edit` / `.delete` (or closest existing perms).

---

## Task F — Sales Order import warning (catheter without distribution)

**Files:** PDF import paths in `rep_traceability/admin.py` (bulk + single)

When an imported/updated SO is classified as **catheter** (existing `_is_catheter_order` / SKU rules) and **no** distribution is linked to that SO after rematch:

1. Flash (or import summary line) a clear warning, e.g.  
   `Warning: Sales Order 0000366 looks like a catheter order but has no matching distribution. It will not be treated as NRE, but no distribution was linked.`
2. Do **not** silently classify it as NRE (P41 classification tweak should already exclude catheter SOs from auto-NRE — keep/verify that).
3. If import processes many orders, aggregate warnings in the result flash / report (cap list length).

---

## Task G — Weekly Brief: merge Invoices Received into Upcoming Payments table

**Files:** `app/eqms/admin.py` (`weekly_brief_send` / preview context), `app/eqms/templates/email/weekly_brief.html`, admin weekly-brief preview if it mirrors the email.

1. **Remove** the separate email section headed **Invoices Received**.
2. Keep a single section (title may stay **Upcoming Payments**, or become **Payments & Invoices** if that reads cleaner — prefer keeping **Upcoming Payments** unless empty-state copy needs a tweak).
3. Build one combined row list for the table:
   - Upcoming Payments rows: first column = Expected Invoice Date (`order_date`), as today. Include payment line-item sub-lines as today.
   - Invoices Received rows: map into the **same columns**:
     | Column | Source |
     |---|---|
     | First (date) | `date_received`, with muted suffix **`(Received)`** on the same cell (e.g. `Jul 13, 2026 (Received)`) |
     | Vendor | `payee` |
     | Description | `description` |
     | Amount | `amount` |
     | Due Date | `due_date` |
4. Sort the combined table sensibly (recommend: by the displayed date ascending, nulls last; payments and received interleaved by date).
5. Empty state only when **both** ledgers are empty.
6. Do **not** change the on-site Purchasing UI (Upcoming Payments and Invoices Received remain separate cards there).

---

## Task H — Hardcoded `/admin/...` JS paths

Search templates/JS under `app/eqms/templates` for hardcoded `"/admin/` fetch/form URLs (especially Purchasing line-item file JS from P39). Replace with `url_for(...)` emitted into `data-*` attributes or a small JSON config blob in the template. Fix any you find in NRE/Equipment Admin Tools pages touched by this prompt.

---

## Task I — Tests

Add/extend tests (e.g. `tests/test_p42_usability.py`):

1. Payment list renders line-item summary when lines exist; expand still works.
2. NRE tracker accepts free-text status not in old enum.
3. Dashboard Total Amount Invoiced math for the four statuses.
4. New SO defaults `Pending Invoice`; backfilled historical default `100% Invoiced`.
5. Equipment list: All vs Active; overdue filter returns rows.
6. Equipment schedule returns 200 on basic fixture.
7. Unmatched distributions workspace lists `sales_order_id IS NULL` rows; manual link sets SO.
8. Catheter SO import without distribution produces warning (flash/summary).
9. Weekly Brief HTML contains a single payments table; Invoices Received rows show `(Received)` in the first column; no separate Invoices Received heading.

Full suite green; single Alembic head; `import app.wsgi` OK.

---

## Task J — Deploy + completion report

1. Commit + push `main`.
2. Report must list:
   - Migration id for `nre_invoice_status` (or equivalent)
   - Admin Tools UX changes (before/after section list)
   - Unmatched workspace URL
   - Equipment bugs root cause + fix
   - Weekly Brief combined payments table behavior
   - Any judgment calls (summary density, danger-zone placement, section title wording)

---

## Out of scope

- New financial accounting system beyond the status-weighted Amount Invoiced tile
- Regenerating the cumulative Excel chart
- Reversing Purchasing ↔ Equipment top-nav decision
- Large redesign of the main `/admin/` dashboard card grid
- Auto-deleting unmatched distributions without Ethan’s manual action in the new workspace

---

## Reference

- Admin Tools: `app/eqms/templates/admin/diagnostics.html`, `app/eqms/admin.py`
- Purchasing lines UI: `app/eqms/templates/admin/purchasing/list.html`
- Weekly Brief: `app/eqms/templates/email/weekly_brief.html`, `weekly_brief_send` in `app/eqms/admin.py`
- NRE: `app/eqms/modules/nre_projects/admin.py`, `models.py`, `templates/admin/nre_projects/index.html`
- Equipment: `app/eqms/modules/equipment/admin.py` (`equipment_list`, `equipment_schedule`)
- Unmatched count: `DistributionLogEntry.sales_order_id.is_(None)` in diagnostics
- P41 facility/dedup context: `PHASE3_DEV_AGENT_PROMPT_41_SHIPTO_FACILITIES_AND_DEDUP.md`

---

## Acceptance checklist

- [ ] Upcoming Payments shows line-item summaries without opening the editor first
- [ ] NRE Tracker Status is free text
- [ ] NRE Dashboard Status is the four-option dropdown; lifecycle badge gone from that column
- [ ] Tile reads **Total Amount Invoiced** and matches the weighting rules
- [ ] Historical SOs default 100% Invoiced; new SOs Pending Invoice
- [ ] Equipment list Active/All/overdue behave correctly; schedule page loads
- [ ] Admin Tools is cleaner; unmatched workspace lets Ethan link/clear/delete manually
- [ ] Catheter SO import without distribution warns clearly
- [ ] Weekly Brief: one payments table; Invoices Received rows marked `(Received)` in the first column; no separate Invoices Received section
- [ ] No critical hardcoded `/admin/` JS paths remain in touched ledgers

---

End of Prompt 42.
