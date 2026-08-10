# Prompt 39 — Purchasing & NRE Module Enhancements

## Context

Ethan will hand this prompt to the dev agent. Auto-deploy to production after a green suite (same pattern as prior Phase 3 prompts). Do **not** wait for further approval unless something fails.

**Alembic parent revision:** `b4c5d6e7f8a9` (single head). New migration(s) must chain from this head.

**Ignore Prompt 29** if referenced historically — that work was done outside this series.

---

## Decisions already made (do not re-ask)

| Topic | Decision |
|---|---|
| Top nav | Put **Purchasing** in the top menu **in place of Equipment**. Keep Equipment reachable from the Dashboard (and any Operations links). Do **not** remove the Equipment dashboard card. |
| Payment line items | Optional per entry via an **"Add line items"** control. Most entries stay simple (zero line items). |
| Parent Amount vs line items | Parent **Amount stays manually edited**. Line items are informational; do **not** auto-sum or lock the parent. |
| Line-item files | **Multiple files** per line item. |
| Order Date column | **Rename label only** → **Expected Invoice Date**. Keep the same DB column (`PaymentEntry.order_date`). No data migration / backfill. |
| Invoices Received layout | **Two stacked cards** that look continuous (Upcoming Payments card, then Invoices Received card immediately below). Not tabs; not one shared card chrome. |
| Invoices Received fields | Date Received, Payee, Description, Amount, Due Date + invoice file attachment(s). **No status field.** Free-text Payee — **no** vendor/supplier matching or pre-seeding. |
| Weekly Brief | **Include** a condensed **Invoices Received** section. Also include payment **line items** under Upcoming Payments. |
| NRE tracker name | Rename UI label to **Upcoming NRE Invoice Tracker**. |
| NRE status | Add **`50% Invoiced`** between `Pending Invoice` and `Invoiced`. |
| SO interpretation | Extend parsing beyond customer matching: **order date, amount, PO/ref, description** when present. |
| Invoice Date | Stored on each **sales order**; editable on the **customer profile**. Same value shown in expanded view and anywhere else SO invoice date is displayed. |
| Expanded view | **Inline expand/collapse** on the NRE index under each customer card. |
| Expanded rows | Always show **all** sales orders for that customer. Invoice Date blank if not set. |
| Dashboard filter | Filter by **Order Date**; default = **current calendar quarter**. |
| Dashboard revenue | Sum **sales order amounts** for SOs in the filtered period. |

---

## Task A — Top menu: Purchasing replaces Equipment

**File:** `app/eqms/templates/_layout.html`

1. Remove the Equipment top-nav link (currently gated on `equipment.view`).
2. Add a Purchasing top-nav link in that position, gated on `purchasing.view`, pointing to `url_for('purchasing.purchasing_list')`.
3. Do **not** change dashboard cards: Equipment and Purchasing both remain on the admin dashboard.

---

## Task B — Upcoming Payments: rename + optional line items

### B1. Label rename only

In `app/eqms/templates/admin/purchasing/list.html` (and any related JS/labels):

- Change the column header **Order Date** → **Expected Invoice Date**.
- Keep form field name / API key `order_date` (no DB rename). Update visible labels in create/edit rows and the Weekly Brief email column header for payments to **Expected Invoice Date** as well.

### B2. Models + migration

Add (suggested names — match repo style):

**`PaymentLineItem`**
- `id`, `payment_entry_id` (FK → `payment_entries.id`, CASCADE)
- `description` (`String(512)`, nullable)
- `amount` (`Numeric(12,2)`, nullable)
- `sort_order` (int, default 0) — optional but useful for stable UI order
- `created_at`, `updated_at`, `created_by_user_id` (follow existing audit patterns)

**`PaymentLineItemAttachment`**
- Same shape as `PaymentEntryAttachment`: `payment_line_item_id` CASCADE, `filename`, `storage_key`, `content_type`, `size_bytes`, `uploaded_at`, `uploaded_by_user_id`
- Storage key pattern: `purchasing/payment_line_files/{line_item_id}/{secure_filename}`

Relationships:
- `PaymentEntry.line_items` → cascade `all, delete-orphan`
- `PaymentLineItem.attachments` → cascade `all, delete-orphan`

Migration: new revision after `b4c5d6e7f8a9`. Confirm single Alembic head.

### B3. API routes (follow existing payment attachment pattern)

Under `purchasing` blueprint, `purchasing.edit` for mutating routes:

| Method | Path | Behavior |
|---|---|---|
| GET | `/purchasing/payments/<entry_id>/lines` | JSON list of line items (+ attachment metadata) |
| POST | `/purchasing/payments/<entry_id>/lines` | Create line item (`description`, `amount`) |
| POST | `/purchasing/payments/<entry_id>/lines/<line_id>` | Update line item (partial-friendly) |
| DELETE | `/purchasing/payments/<entry_id>/lines/<line_id>` | Delete line item (+ attachments) |
| POST | `.../lines/<line_id>/files` | Attach file (multi allowed) |
| GET | `.../lines/<line_id>/files/<att_id>/view\|download` | View/download |
| POST | `.../lines/<line_id>/files/<att_id>/delete` | Delete attachment |

Reuse `_parse_amount` for amounts. Audit events consistent with payment attach/delete.

**Do not** auto-update parent `PaymentEntry.amount` from line items.

### B4. UI (Upcoming Payments card)

In the Upcoming Payments section of `list.html`:

1. Keep the existing entry table/inline edit as-is (with Expected Invoice Date label).
2. For each entry, add a compact control: **"+ Line items"** / **"Hide line items"** (or equivalent).
3. When expanded, show an editable sub-table:
   - Description | Amount | Files | Actions (edit/save/cancel/delete)
   - Ability to add a new line item
   - Multi-file attach per line item (same 📎 / Files UX pattern as parent entry Files column)
4. Empty state when expanded with no lines: short muted "No line items."

CSRF: same working pattern as the existing payments ledger.

---

## Task C — Invoices Received (new ledger)

### C1. Models + migration

**`InvoiceReceivedEntry`** (name may be `ReceivedInvoice` — pick one clear name and stick to it):

| Field | Type |
|---|---|
| `date_received` | `date \| None` |
| `payee` | `String(256) \| None` — free text |
| `description` | `String(512) \| None` |
| `amount` | `Numeric(12,2) \| None` |
| `due_date` | `date \| None` |
| audit fields | same style as `PaymentEntry` |

**`InvoiceReceivedAttachment`** — same pattern as `PaymentEntryAttachment`.  
Storage: `purchasing/invoice_received_files/{entry_id}/{secure_filename}`

No status. No FK to suppliers/POs.

### C2. Routes

Mirror the Upcoming Payments CRUD + file routes under e.g.:

- `GET/POST /purchasing/invoices-received`
- `POST/DELETE /purchasing/invoices-received/<id>`
- file attach/view/download/delete routes

Permission: `purchasing.view` for read; `purchasing.edit` for mutate.

### C3. UI

Immediately **below** the Upcoming Payments card on `/admin/purchasing`, add a second card titled **Invoices Received**.

Columns: **Date Received | Payee | Description | Amount | Due Date | Files | Actions**

Behavior: same inline create/edit/delete + file attach UX as Upcoming Payments (without line items). Empty state: "No invoices received yet."

Visual note: stacked cards should feel continuous (tight spacing / consistent card styling) — not a distant separate module.

---

## Task D — Weekly Brief email updates

**Files:** `app/eqms/admin.py` (`weekly_brief_send`), `app/eqms/templates/email/weekly_brief.html`, admin preview if present.

1. **Upcoming Payments section**
   - Rename date column label to **Expected Invoice Date**.
   - Eager-load line items. Under each payment row that has line items, render a compact indented list: description + amount (and optionally filename count). Keep email clean — no file binaries in email.

2. **Invoices Received section** (new)
   - Include **all** received-invoice entries (no status to filter).
   - Suggested columns: Date Received, Payee, Description, Amount, Due Date.
   - Place after Upcoming Payments (or after NRE — prefer: Sales snapshot → Upcoming NRE Invoice Tracker → Upcoming Payments → Invoices Received).

3. Rename the NRE email section heading to **Upcoming NRE Invoice Tracker** (match UI). Include the new status badge color for `50% Invoiced` (see Task E).

---

## Task E — Upcoming NRE Invoice Tracker

**Files:** `app/eqms/modules/nre_projects/models.py`, templates, admin validation, email badges.

1. Rename visible title **NRE Invoice Tracker** → **Upcoming NRE Invoice Tracker** on the index page (and email).
2. Update `INVOICE_STATUSES` to:

```python
INVOICE_STATUSES = [
    "Pending Invoice",
    "50% Invoiced",
    "Invoiced",
    "Paid",
    "Cancelled",
]
```

3. Status dropdown + badge colors: insert **50% Invoiced** between Pending and Invoiced. Suggest a distinct mid-progress color (e.g. teal/amber-blue `#0d9488` or `#c2410c` — pick one readable on the dark theme; do not reuse Paid green or Cancelled gray).
4. Weekly brief continues to exclude `Paid` and `Cancelled`; **include** `50% Invoiced` and `Pending Invoice` / `Invoiced`.

---

## Task F — NRE Projects module improvements

### F1. Sales order fields + parsing

`SalesOrder` currently has no order-level amount / invoice date / PO-ref / description for NRE display.

Add nullable columns (migration after Task B/C or combined carefully — still one linear head):

| Column | Purpose |
|---|---|
| `order_amount` | `Numeric(12,2)` — order total |
| `invoice_date` | `date` — manually entered on customer profile |
| `po_reference` | `String(128)` — PO / customer ref if parsed |
| `order_description` | `String(512)` — short project/description if parsed |

**Parser extension** (`app/eqms/modules/rep_traceability/parsers/pdf.py`):

Extend `_parse_silq_sales_order_page` (and persistence path that creates/updates `SalesOrder`) to extract when present:

- Order date (already largely handled)
- Order total / amount (common labels: Total, Order Total, Amount Due, etc.)
- PO / customer reference (PO Number, Customer PO, etc.)
- Short description / project line if clearly present

Best-effort parsing: never fail the import if these fields are missing. Persist into the new columns on create/update.

**Backfill script** (coordinator-runnable, dry-run default):

- `scripts/_backfill_nre_sales_order_fields.py`
- Re-parse existing NRE-related sales order PDFs (or all SO PDFs) and fill null `order_amount` / `po_reference` / `order_description` when extractable.
- Do **not** overwrite non-null `invoice_date` (manual). Prefer not overwriting non-null amounts unless `--force`.
- Document how to run with `--execute` after deploy.

### F2. Customer card sort + two buttons + inline expand

**Index** (`nre_projects_index` + `index.html`):

1. Sort customer cards by **most recent sales order `order_date`** (desc). Customers with no orders last.
2. Each card keeps name / abbreviation / order count / location as today.
3. Add two buttons on each card:
   - **Customer Profile** → existing detail route
   - **Expanded View** → toggles inline expand/collapse for that card (not a modal, not a separate page)
4. Expanded panel columns for each SO:
   - Order # | Order Date | Amount (`order_amount`, blank/formatted if null) | Invoice Date (`invoice_date`, blank if null) | Status (existing SO status ok)
5. Always list **all** SOs for that customer; never hide rows missing invoice date.
6. Only one card expanded at a time is fine (or allow multiple — pick simplest). Collapse button / click again to close.

### F3. Invoice Date edit on customer profile

On `detail.html` Sales Orders list:

- Add an editable **Invoice Date** control per sales order (date input + save, or inline patch).
- Route e.g. `POST /admin/nre-projects/<customer_id>/orders/<order_id>/invoice-date` with `sales_orders.edit` (or existing NRE edit perm used on that blueprint).
- Saving updates `SalesOrder.invoice_date` only.
- Show Amount / PO ref / description if available (read-only from parsed fields); Ethan can still use Documents / Upload PDF as today.

**Sync note (decision 11c):** Invoice Date lives on the SO. The free-form Upcoming NRE Invoice Tracker remains independent for invoicing workflow, but expanded view and customer profile must show the **same** `SalesOrder.invoice_date`. Do **not** invent a second invoice-date column on `NREProjectEntry` unless you also sync it — prefer single source of truth on `SalesOrder`.

### F4. Bottom dashboard (NRE index)

Below the customer grid, add a compact **NRE Dashboard** card:

- **Date filter:** start / end date inputs; **default = current calendar quarter** (same quarter math as weekly brief in `admin.weekly_brief_send`:

  ```python
  quarter_month_start = ((today.month - 1) // 3) * 3 + 1
  quarter_start = date(today.year, quarter_month_start, 1)
  # end default: today (or end of quarter — prefer today if simpler; document choice)
  ```

  Filter field: **Order Date** on sales orders belonging to NRE customers (same `_nre_customers` classification).

- Metrics (for filtered SOs):
  1. **Total NRE projects** = count of sales orders in filter
  2. **Customers** = distinct customers with ≥1 SO in filter
  3. **Total revenue** = sum of `order_amount` (treat null as 0 for the sum; show a muted note if some amounts are missing)

GET query params for filter preferred (`start`, `end`) so links are shareable. Apply filter refreshes the three metrics (customer grid sort can remain global by most recent order, unless filtering the grid is trivial — **do not** filter the customer grid unless easy; metrics are the priority).

---

## Task G — Tests

Add focused tests (new file e.g. `tests/test_p39_purchasing_nre.py`):

1. Payment line item create / update / delete; parent amount unchanged when lines change.
2. Multi-file attach on a line item.
3. Invoice Received CRUD + attach.
4. `INVOICE_STATUSES` includes `50% Invoiced`; create tracker entry with that status.
5. SalesOrder `invoice_date` patch via NRE detail route.
6. NRE index: expanded view markup / customer sort by recent order_date (smoke).
7. Dashboard metrics: quarter defaults; project count / customer count / revenue sum.
8. Weekly brief render includes Invoices Received + payment line items (template context smoke if full send is hard without Resend).

Run full suite; fix failures. Confirm single Alembic head; `import app.wsgi` OK.

---

## Task H — Deploy

1. Commit + push to `main` (auto-deploy).
2. Confirm release done in DO logs when possible.
3. Leave the backfill script for the coordinator; print dry-run instructions in the completion report.
4. Completion report must list:
   - Migration revision id(s)
   - Routes added
   - UI locations changed
   - How to run `_backfill_nre_sales_order_fields.py`
   - Any judgment calls (email section order, expand one-vs-many cards, quarter end date)

---

## Out of scope

- Changing Equipment dashboard card or Equipment module internals
- Matching Invoices Received to suppliers/POs
- Auto-summing Upcoming Payments parent Amount from line items
- Renaming `PaymentEntry.order_date` DB column
- Rebuilding the free-form Upcoming NRE Invoice Tracker into a per-SO-only model
- Fiscal-quarter logic (use calendar quarters)

---

## Reference files

- Nav: `app/eqms/templates/_layout.html`
- Purchasing UI/routes: `app/eqms/modules/purchasing/admin.py`, `models.py`, `templates/admin/purchasing/list.html`
- NRE: `app/eqms/modules/nre_projects/admin.py`, `models.py`, `templates/admin/nre_projects/index.html`, `detail.html`
- SO model/parser: `app/eqms/modules/rep_traceability/models.py`, `parsers/pdf.py`
- Weekly brief: `app/eqms/admin.py`, `templates/email/weekly_brief.html`
- Attachment pattern precedent: Prompt 34 / existing `PaymentEntryAttachment` + `NRETrackerAttachment`

---

End of Prompt 39.
