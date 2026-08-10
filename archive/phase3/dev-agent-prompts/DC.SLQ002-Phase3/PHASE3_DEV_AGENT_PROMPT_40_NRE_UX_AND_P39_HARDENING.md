# Prompt 40 — NRE UX polish + P39 hardening (before SO backfill)

## Context

Prompt 39 (`32dd14e`, migration `c5d6e7f8a9b0`) shipped Purchasing line items, Invoices Received, NRE tracker/dashboard, and SO parse fields. Ethan will import **`July26SalesOrders.pdf`** this afternoon, then run the SO field backfill. **Do not run or require the backfill as part of this prompt.** Implement code/parser/import fixes first so the afternoon import + later backfill land correctly.

Auto-deploy to production after a green suite. Parent Alembic revision: **`c5d6e7f8a9b0`** (single head). New migration(s) must chain from it.

---

## Decisions (do not re-ask)

| Topic | Decision |
|---|---|
| Backfill | **Out of scope for this prompt.** Leave `scripts/_backfill_nre_sales_order_fields.py` as-is (or improve it), but do **not** execute against prod. Coordinator will import July26SalesOrders.pdf then backfill. |
| Expanded View control | Replace the **Expanded View** text button with a **down-pointing arrow** control (toggle to up-arrow when expanded). |
| NRE Dashboard placement | Move **above** the customer card grid. |
| Dashboard project rows | Below the three metric tiles, show a **table/list of every NRE sales order in the filtered date range** with the same columns as the card Expanded View (Order #, Order Date, Amount, Invoice Date, Status — plus customer name so rows are readable at page level). |
| Customer cards | **Reduce height.** Show customer name + order count + the two actions only. **Hide** town/city and customer abbreviation/code on the card (those belong on the profile). |
| Profile addresses | Show **Sold To** and **Ship To** from the **most recent sales order** (by `order_date`, then `id`). |
| Company contacts | Optional manual **Name** + **Email** on the customer, edited via **Edit Customer**. Use existing `Customer.contact_name` / `Customer.contact_email` (already on the model) — expose in the edit modal and display on the profile. Do **not** invent a second parallel contact model unless those columns are insufficient. |

---

## Task A — P39 hardening (recommended fixes)

### A1. Stop clobbering non-null SO fields on re-import

**File:** `app/eqms/modules/rep_traceability/admin.py` (both PDF upsert paths that set P39 fields — around the existing `order_amount` / `po_reference` / `order_description` assignments).

On update of an existing `SalesOrder`:

- Only set `order_amount` if the existing value is `None` **or** the new parsed value is non-null **and** you choose an explicit “fill-nulls-only” policy matching the backfill script.
- **Required policy:** never overwrite a non-null `order_amount`, `po_reference`, or `order_description` with a newly parsed value (same as backfill without `--force`).
- Never write `invoice_date` from the parser (already correct — keep that).

Apply consistently to every import path that updates existing orders.

### A2. Tighten PDF amount / PO / description extraction

**File:** `app/eqms/modules/rep_traceability/parsers/pdf.py`

Improve best-effort extraction used by P39:

1. **Amount:** Prefer labeled totals in order: `Order Total`, `Grand Total`, `Amount Due`, `Total Due`, then a cautious final `Total` that is not a line-item subtotal. Accept whole dollars **and** cents (`$1,500` and `$1,500.00`).
2. Avoid grabbing tax-only or page footer noise when a better label exists.
3. **PO / description:** Keep best-effort; trim obvious header junk; do not fail parse if missing.
4. Add **2–3 fixture-based unit tests** (small text fixtures or minimal PDF text strings) covering: cents total, whole-dollar total, PO number present.

### A3. Storage cleanup on ledger delete

When deleting:

- `InvoiceReceivedEntry`
- parent `PaymentEntry` (Upcoming Payments)

Delete associated attachment blobs from storage (same pattern already used for `PaymentLineItem` delete). Keep DB cascade. Do not fail the whole delete if a single blob delete errors — log and continue, or match the line-item pattern exactly.

### A4. Purchasing UI polish

In `app/eqms/templates/admin/purchasing/list.html`:

- Format line-item amounts as currency (same helper / style as parent Amount).
- Prefer `url_for(...)` (or data attributes from the template) over hardcoded `/admin/purchasing/...` paths in line-item JS.

### A5. (Optional small) Invoice Date from Expanded View

If low-cost: allow editing Invoice Date in the card Expanded View via the same `nre_order_invoice_date` route (or a tiny JSON PATCH). If this risks scope creep, skip — profile edit remains sufficient. Prefer implementing if the dashboard project table (Task B) makes inline edit natural.

---

## Task B — NRE index UX

**Files:** `app/eqms/modules/nre_projects/admin.py`, `templates/admin/nre_projects/index.html`

### B1. Expanded View → down arrow

- Replace the “Expanded View” button label with a **↓** (or chevron-down) control.
- When that card is expanded, show **↑** (or chevron-up).
- Keep accessible `title` / `aria-label` (e.g. “Expand orders” / “Collapse”).
- Keep **Customer Profile** as a normal text/button link.
- Preserve one-card-at-a-time expand behavior unless multi-expand becomes trivial.

### B2. Slim customer cards

Each card should show approximately:

- Customer **name** (primary)
- Sales order **count** (e.g. “2 sales orders”)
- Actions: **Customer Profile** + **↓** expand

**Remove from the card:**

- Customer code / abbreviation badge
- City / state (“town”)

Keep sort by most recent `order_date` (desc). Reduce padding so cards are visually shorter.

### B3. Move NRE Dashboard above the customer grid

Page order on `/admin/nre-projects/`:

1. Upcoming NRE Invoice Tracker (unchanged aside from any status polish)
2. **NRE Dashboard** (metrics + date filter + project rows)
3. Customer cards grid

### B4. Dashboard project rows (filtered period)

Keep the three metric tiles:

- Total NRE projects (SO count in filter)
- Customers (distinct)
- Total revenue (sum of non-null `order_amount`; muted note for missing amounts)

**Add** below the tiles a table of projects in the filtered window:

| Customer | Order # | Order Date | Amount | Invoice Date | Status |

- Same filter as metrics: **Order Date** between `start` and `end` (default: current calendar quarter start → today).
- One row per sales order (each SO = one project).
- Invoice Date blank if null; Amount formatted or blank/`—` if null.
- Sort: most recent Order Date first (then order number).
- Customer name links to the NRE customer profile (optional but preferred).
- Empty state when no SOs in range.

Do **not** filter the customer card grid by the dashboard date range unless trivial — metrics + project table are the filtered surface.

---

## Task C — NRE customer profile: addresses + contacts

**Files:** `detail.html`, `nre_customer_edit`, possibly a small migration **only if** SO-level address columns are added.

### C1. Sold To / Ship To from most recent sales order

`Customer` already has:

- Ship To: `address1`, `address2`, `city`, `state`, `zip`
- Sold To: `sold_to_address1`, `sold_to_city`, `sold_to_state`, `sold_to_zip`

The SO PDF parser already extracts sold-to / ship-to into the parse dict, but **`SalesOrder` does not currently store per-order addresses**.

**Implement:**

1. Add nullable address fields on `SalesOrder` (migration) for both Sold To and Ship To, e.g.:

   - `sold_to_address1`, `sold_to_city`, `sold_to_state`, `sold_to_zip`
   - `ship_to_name` (optional), `ship_to_address1`, `ship_to_city`, `ship_to_state`, `ship_to_zip`

2. On PDF import create/update: persist these from the parse dict using the **same fill-nulls-only** rule as Task A1 (do not clobber non-null SO address fields on re-import).

3. Extend the backfill script to also fill null SO address fields from re-parse (still coordinator-run later — do not execute now).

4. On the NRE customer profile (`detail.html`), above or beside the sales-order list header, show a compact **two-column address block**:

   - **Sold To** — from the most recent SO (`order_date` desc, `id` desc). If that SO has no sold-to fields, fall back to `Customer.sold_to_*`.
   - **Ship To** — from the same most recent SO’s ship-to fields; fall back to `Customer.address1/city/state/zip`.

5. Also show customer **code/abbreviation** on the profile (already present) — cards no longer show it.

### C2. Company Contacts (Name + Email) via Edit Customer

`Customer` already has `contact_name` and `contact_email`.

1. On the profile header area, display **Company Contacts** when either field is set (Name / Email). If both empty, show a muted “No company contacts on file.”
2. Extend the **Edit Customer** modal + `nre_customer_edit` POST handler to accept optional:

   - `contact_name`
   - `contact_email`

3. Validate email lightly (strip; optional basic format check; allow blank to clear).
4. Include before/after in the existing audit metadata for `nre_customer.update`.
5. Do **not** require phone. Do not remove existing name/code/classification fields from the modal.

---

## Task D — Tests

Extend or add `tests/test_p40_*.py` (or append to P39 tests if cleaner):

1. Re-import does not overwrite non-null `order_amount` / `po_reference` / `order_description`.
2. Parser fixtures: whole-dollar + cents amounts; PO extraction.
3. NRE index: dashboard appears before customer grid; project rows respect `start`/`end`.
4. Expand control is present (arrow / aria) without “Expanded View” text.
5. Customer card HTML does not include city/abbreviation in the card body (profile still can).
6. Edit customer persists `contact_name` / `contact_email`.
7. Profile renders Sold To / Ship To from most recent SO when SO address fields are set.
8. Deleting an Invoices Received entry invokes storage delete for its attachments (mock storage if needed).

Full suite green; single Alembic head; `import app.wsgi` OK.

---

## Task E — Deploy + handoff notes

1. Commit + push to `main`.
2. Completion report must state clearly:

   > **Do not run the SO backfill yet.** Ethan will import `July26SalesOrders.pdf` first, then run:
   >
   > ```text
   > python scripts/_backfill_nre_sales_order_fields.py
   > python scripts/_backfill_nre_sales_order_fields.py --execute
   > ```

3. List migration id(s), routes touched, and any judgment calls (arrow glyph choice, dashboard table density, address fallback rules).

---

## Out of scope

- Running the production backfill or importing July26SalesOrders.pdf
- Changing Upcoming Payments / Invoices Received field sets (beyond A3/A4 polish)
- Putting Equipment back in the top nav
- Linking Invoices Received to POs/suppliers
- Auto-summing payment parent Amount from line items
- Weekly Brief date-window filtering (defer)

---

## Reference

- P39 prompt: `docs/DC.SLQ002-Phase3/PHASE3_DEV_AGENT_PROMPT_39_PURCHASING_NRE_ENHANCEMENTS.md`
- NRE index/detail: `app/eqms/modules/nre_projects/admin.py`, `templates/admin/nre_projects/`
- Customer model (contacts + sold_to_* + ship address): `app/eqms/modules/customer_profiles/models.py`
- SO model / PDF parse / import: `app/eqms/modules/rep_traceability/models.py`, `parsers/pdf.py`, `admin.py`
- Backfill: `scripts/_backfill_nre_sales_order_fields.py`
- Purchasing delete/attach patterns: `app/eqms/modules/purchasing/admin.py`

---

End of Prompt 40.
