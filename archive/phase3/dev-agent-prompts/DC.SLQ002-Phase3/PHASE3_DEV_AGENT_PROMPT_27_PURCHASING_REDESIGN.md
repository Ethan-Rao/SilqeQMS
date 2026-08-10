# Prompt 27 — Purchasing Module Redesign

## Context

The Purchasing page needs two distinct changes:

1. **New "Upcoming Payments" ledger at the top** — a simple, fully-editable table replacing the colored summary cards. Ethan manually maintains this list to show the team what payments are pending. Entries can come from open POs or be completely ad-hoc.
2. **Enhanced PO tracking table below** — the existing PO table stays but gets cleaned up: status simplified to Open/Closed, amounts formatted as dollars, "(unlinked)" removed from vendor names, attachment dropdowns for Quotes/Verifications, and data corrected from the PO Log.

Read the following files in full before starting:
- `app/eqms/modules/purchasing/admin.py`
- `app/eqms/modules/purchasing/models.py`
- `app/eqms/modules/purchasing/service.py`
- `app/eqms/templates/admin/purchasing/list.html`
- `app/eqms/templates/admin/purchasing/detail.html`
- `app/eqms/templates/admin/purchasing/edit.html`
- `app/eqms/templates/admin/purchasing/new.html`

---

## Task A — New Model: `PaymentEntry`

Create a new lightweight model in `app/eqms/modules/purchasing/models.py`:

```python
class PaymentEntry(Base):
    __tablename__ = "payment_entries"
    id            = Column(Integer, primary_key=True)
    order_date    = Column(Date, nullable=True)
    vendor        = Column(String(256), nullable=True)   # free text
    description   = Column(String(512), nullable=True)
    amount        = Column(Numeric(12, 2), nullable=True)
    payment_due_date = Column(Date, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at    = Column(DateTime, default=utcnow)
    updated_at    = Column(DateTime, default=utcnow, onupdate=utcnow)
```

Create an Alembic migration (`payment_entries` table + `payment_due_date DATE` column on `purchase_orders`).

---

## Task B — Upcoming Payments Ledger (Top Section)

Replace the four colored summary cards in `list.html` with an **Upcoming Payments** section.

### Layout

```
[Upcoming Payments]                              [+ Add Payment]  (admin only)
──────────────────────────────────────────────────────────────────────────────
 Order Date  |  Vendor / Supplier  |  Description  |  Amount  |  Due Date  |  [✎ Edit]
─────────────────────────────────────────────────────────────────────────────
 (rows from payment_entries, sorted by due date ASC, nulls last)
```

### Inline Editing

Rows are **directly editable** for admin users (`purchasing.edit`):
- Each row shows an **✎** (pencil) icon button. Clicking it switches that row's cells to `<input>` fields (JS-powered, no page reload). A **Save** and **Cancel** button appear.
- A **✕** (delete) icon per row (admin only) — posts to a DELETE endpoint.
- Staff see the table read-only (no edit/delete icons).

### Add Payment

The **+ Add Payment** button (admin only) appends a new blank editable row at the top of the table — same inline pattern. Required fields: none (all optional so partial entries are allowed).

### Routes needed (all gated `purchasing.edit`):

```
POST   /purchasing/payments          → create PaymentEntry
POST   /purchasing/payments/<id>     → update PaymentEntry (accepts JSON or form)
DELETE /purchasing/payments/<id>     → delete PaymentEntry
GET    /purchasing/payments          → returns JSON list (for JS reload, optional)
```

The main `purchasing_list()` GET route should include all `PaymentEntry` rows in the template context.

---

## Task C — PO Table Status Simplification

Simplify the PO status to **Open** or **Closed** throughout:

- In `list.html` and `detail.html`: render the badge as **Open** (amber) when `status in ('pending', 'partial')` and **Closed** (muted grey) when `status in ('received', 'cancelled')`. Do not change the underlying stored values.
- In the Status filter dropdown: replace the four values with **Open** and **Closed** (map to the appropriate DB values in the route).
- The New/Edit form status dropdown: keep the four granular values (`Pending`, `Partial`, `Received`, `Cancelled`) for data entry precision, but label the section "Status (Open/Closed)" for clarity.

---

## Task D — Vendor Display: Remove "(unlinked)"

In `list.html`, for POs with no `supplier` FK:
- If `po.notes` starts with `'Supplier from PO Log: '` → show the text **after that prefix**, plain text, no `(unlinked)` tag.
- Otherwise → show `—`.

Apply the same change to `detail.html`.

---

## Task E — Dollar Amount Formatting

Add a `format_currency` Jinja global (register in the blueprint or app factory) that:
- Accepts int, float, Decimal, or a string parseable as a number → returns `$X,XXX.XX`
- Returns `—` for None or non-parseable values

Apply to: the `amount` column in `list.html`, the Upcoming Payments ledger in `list.html`, and `detail.html`.

---

## Task F — Attachment Dropdown on PO Detail Page

On the **PO detail page**, add a collapsible **Documents** panel:

```html
<details>
  <summary>Documents (N)</summary>
  <!-- list of PurchaseOrderAttachment rows -->
</details>
```

- Each attachment shows filename + View + Download links (reuse existing attachment routes).
- Show the panel only when `po.attachments|length > 0`.
- Keep the existing upload form below the panel so new attachments can be added.

In the **list view**, show a small 📎 glyph next to the PO number (with a `title` tooltip showing the count) when the PO has at least one attachment. This already exists from Prompt 26 — verify it's still present.

---

## Task G — New and Edit Forms: Add `payment_due_date` Field

Add **Payment Due Date** as an optional date field to both `new.html` and `edit.html`. Place it after the Amount field. No other form changes needed.

---

## Task H — Data Correction (Coordinator Script)

Create `scripts/_sync_po_log.py` (gitignored, DRY_RUN = True, --execute flag).

The script re-reads `Purchasing/SILQ PO Log.xlsx` using openpyxl (column structure mirrors what `import_po_log()` already knows) and performs per-matching-PO updates:

1. **Amount normalization**: Strip `$`, commas, whitespace → parse as `Decimal`. Store as numeric. Skip if blank.
2. **Status mapping**: 
   - PO Log values that mean closed: `Received`, `Complete`, `Closed`, `Received/Closed` → set `status = 'received'`
   - PO Log values that mean open: `Open`, `Pending`, `Partial`, `In Progress` → set `status = 'pending'`
   - Blank → leave unchanged
3. **Description backfill**: If `purchase_order.description` is blank and the PO Log row has a description/item column → populate it.

Match rows by `po_number` (normalize: strip leading zeros in log vs model — handle both `180` and `0000180` forms).

Print a per-PO change summary. Only commit rows that actually differ. Single transaction on `--execute`.

---

## Task I — Upload Quotes & Verifications (Coordinator Script)

Create `scripts/_upload_purchasing_docs.py` (gitignored, DRY_RUN = True, --execute flag, S3-backed).

Upload into the `purchasing` admin_docs library:

**Folder "Quotes"** (create if absent under the library root):
- `Purchasing/Quotes/2025_12_Q_SIL-Q-111325-SAC-BRE PO 0000178.pdf`
- `Purchasing/Quotes/PO 0000180.xlsx`
- `Purchasing/Quotes/PO 0000181.xlsx`
- `Purchasing/Quotes/PO 0000182.xlsx`
- `Purchasing/Quotes/SIL-Q-071026-LA-LEN Microprecision PO 0000183.pdf`

**Folder "Verifications"** (create if absent):
- All files in `Purchasing/Verifications/` (3 files — check exact filenames at runtime with `Path.iterdir()`)

Idempotent by filename. Use the same `storage.upload()` + `AdminDocFile` ORM pattern as prior coordinator scripts.

---

## Task J — Tests

Add `tests/test_p27_purchasing.py`:
- List page 200 for admin and staff.
- Upcoming Payments section present in HTML.
- `+ Add Payment` button present for admin, absent for staff.
- "(unlinked)" text absent from supplier column.
- Amount shown with `$` when numeric.
- Status badge shows "Open" or "Closed" (not "Pending"/"Received").
- Year and supplier_id filter dropdowns absent (removed in P26 — verify still gone).
- Detail page: Documents panel present when attachments exist.

Full suite green (`pytest -q`). Single Alembic head (the new migration).

---

## Deployment

Commit code changes (Tasks A–G, J) and push to `main`. Coordinator runs Tasks H and I. Tag: `"P27: purchasing — payments ledger, open/closed status, dollar formatting, attachment panel"`.
