# Developer prompt: Purchasing — “Open POs” table + PDF import fixes (auxiliary / non-validation scope)

## Executive summary

Implement two changes under **`app/eqms/modules/purchasing/`**:

1. **UI:** On the Purchasing list page (`/admin/purchasing`), add a dedicated **“Open purchase orders”** table **above** the existing **“All purchase orders”** list (filters/search unchanged).  
2. **Import:** Fix **`POST /admin/purchasing/import-pdf`** so imports like  
   `PO 0000161 BENTEC 15JAN2025.pdf` populate **PO number**, **order date**, and **supplier** correctly instead of mis-parsing the PDF body (e.g. PO number showing **“Silq”**, wrong date, blank supplier).

**Scope note:** Purchasing is an **auxiliary operational module**, **outside** DC.SLQ002 software validation (Document Control, Admin Docs, audit, etc.). Do **not** frame changes as SRS/QMS validation tasks; keep edits localized to purchasing templates, parser, and routes.

---

## Context — current behavior (investigate in repo)

| Area | Location |
|------|----------|
| List route | `app/eqms/modules/purchasing/admin.py` — `purchasing_list()` |
| List template | `app/eqms/templates/admin/purchasing/list.html` |
| PDF parse | `app/eqms/modules/purchasing/parsers/pdf.py` — `parse_purchase_order_pdf()` |
| Import route | `app/eqms/modules/purchasing/admin.py` — `purchasing_import_pdf_post()` |
| Models | `app/eqms/modules/purchasing/models.py` — `PurchaseOrder.status` constraint: `pending`, `received`, `partial`, `cancelled` |

**Observed bug:** After importing `@Purchasing/POs/PO 0000161 BENTEC 15JAN2025.pdf`, the UI showed PO **“Silq”**, date **2025-01-27**, supplier **—**.

**Likely causes:**

1. **`parse_purchase_order_pdf`** only scans **PDF text** with regexes. Layout/order of tokens can produce a false **PO** match (e.g. company name **Silq** adjacent to “Purchase Order” text) or pick the wrong date line.
2. **Original filename is ignored** — it encodes **PO number**, **supplier token**, and **date** in a predictable pattern but is never merged into `parsed`.

---

## Requirement 1 — “Open purchase orders” section

### Definition of “open”

Use business logic aligned with existing statuses:

- **Open** = `status IN ('pending', 'partial')` — PO is not fully closed out (`received` / `cancelled` treated as not open).

Document this definition in a one-line comment next to the query or in the template subtitle.

### UI / UX

- Add a **second card** **above** the main table card on `list.html`.
- Title: **Open purchase orders** (or equivalent consistent with app tone).
- Subtitle (muted): one line explaining these are pending/partial (not fully received/cancelled).
- Table columns should **match** the main list for consistency: **PO Number**, **Order Date**, **Supplier**, **Status**, **Attachments**, **Actions** (links to View/Edit same as today).
- Sort: recommend **`order_date` descending** (newest first), same as main list unless product prefers oldest-first for “open” — pick one and document.
- **Do not duplicate rows** in the lower table when filters are “All”: lower table remains the **full filtered list**; upper table is **only** the open subset **for the same filter context**.

**Filter interaction (required clarity):**

- When the user applies **Search (`q`)** or **Status** on the form, decide explicitly:
  - **Recommended:** Upper “Open POs” section shows **open POs that also match `q`** (if search set). If **status** filter is set to something other than empty, either:
    - **Option A:** Hide the open section when `status` is `received` or `cancelled` (no open rows possible), **or**
    - **Option B:** Show open section only when `status` is empty, `pending`, or `partial`.
- Pick one behavior, implement consistently, note it in the PR description.

### Backend

- Extend `purchasing_list()` to pass e.g. `open_purchase_orders` (query result) plus existing `purchase_orders`.
- Keep DB access efficient (single page: two queries acceptable; avoid N+1 — existing `selectin` on supplier should still apply if using same pattern).

---

## Requirement 2 — PDF import: filename-aware metadata

### Filename pattern (SILQ convention from example)

Example: `PO 0000161 BENTEC 15JAN2025.pdf`

Interpret as:

| Field | Example |
|-------|---------|
| Literal prefix | `PO` |
| PO number | `0000161` (digits; preserve leading zeros in stored `po_number` string) |
| Supplier token | `BENTEC` (single token or extend to multi-word — see below) |
| Date | `15JAN2025` → **2025-01-15** |

Implement a dedicated helper, e.g. in `parsers/pdf.py` or `purchasing/service.py`:

```text
parse_po_hints_from_filename(filename: str) -> dict | None
```

Return `None` if the pattern does not match (caller falls back to PDF-only behavior).

**Suggested regex / parsing strategy:**

- Strip path / `secure_filename` normalize `f.filename`.
- Case-insensitive match on basename.
- Patterns to support at minimum:
  - `PO\s+(\d+)\s+([A-Za-z0-9][A-Za-z0-9\s\-]*?)\s+(\d{1,2})([A-Z]{3})(\d{4})\.pdf`  
    with month tokens `JAN|FEB|...|DEC` mapped to month numbers.
- **Supplier token:** For the sample, **BENTEC** is one word. If multi-word suppliers appear in filenames later, document extension points (e.g. stop before date token).

### Merge policy (critical)

In `purchasing_import_pdf_post`:

1. Call `parse_po_hints_from_filename(f.filename)` **first**.
2. Call existing `parse_purchase_order_pdf(file_bytes)`.
3. **Merge** with explicit precedence:
   - **If filename hints exist:** use filename for **`po_number`**, **`order_date`**, and **`supplier_name`** (supplier token string) **unless** you choose “PDF overrides when confident” — **default required:** **filename wins for these three fields when the filename pattern matches**, because SILQ naming is authoritative for this workflow.
   - **If filename does not match:** keep current PDF-only extraction.
4. **Supplier resolution:** Existing logic matches `Supplier.name` with `ilike`; imported token **BENTEC** may not exist — leave `supplier_id` **NULL** but set **`notes`** or **`description`** on the PO to `"Supplier from import: BENTEC"` **optional** — only if it doesn’t violate existing UX; otherwise supplier column stays **—** until master data exists (product decision).

### PDF regex hardening (recommended)

Even with filename hints, reduce garbage PO detection:

- Prefer PO patterns that capture **numeric-heavy** PO numbers (`\d{4,}` or explicit **only digits** after normalization).
- Avoid accepting a token like **Silq** as `po_number` when it comes from header/footer noise — e.g. if PDF-derived PO is alphabetic-only and filename gives digits, **prefer filename**.
- Add unit tests for merge precedence.

### Regression test file

Add **`tests/test_purchasing_import_filename.py`** (or similar) with:

- `parse_po_hints_from_filename("PO 0000161 BENTEC 15JAN2025.pdf")` → po `0000161`, supplier `BENTEC`, date `2025-01-15`.
- Merge test: PDF returns junk PO “Silq”, filename hints present → final PO number `0000161`.

Use **small synthetic PDF bytes** only if needed; filename tests should not require the real PDF.

---

## Non-goals

- No changes to SRS, validation docs, or DigitalOcean validation tags.
- No new permissions unless strictly necessary (reuse `purchasing.view` / `purchasing.create`).
- No database migrations unless you discover a schema gap (unlikely).

---

## Acceptance criteria

- [ ] Purchasing list shows **Open purchase orders** table **above** full list; **open** = `pending` + `partial` (unless product explicitly changes).
- [ ] Importing a file named like **`PO 0000161 BENTEC 15JAN2025.pdf`** yields PO **`0000161`**, order date **2025-01-15**, supplier display consistent with chosen policy (match master or show token in notes).
- [ ] Existing imports without matching filename pattern still behave **no worse** than today (PDF-only path).
- [ ] Unit tests cover filename parse + merge precedence.
- [ ] Brief note in PR: auxiliary module, not validation scope.

---

## Files you will likely touch

- `app/eqms/modules/purchasing/admin.py`
- `app/eqms/modules/purchasing/parsers/pdf.py` (+ new helper)
- `app/eqms/templates/admin/purchasing/list.html`
- `tests/test_purchasing_import_filename.py` (new)

---

## Reference asset

Example PDF path in workspace (if present): `Purchasing/POs/PO 0000161 BENTEC 15JAN2025.pdf` — use for **manual QA** after implementation; do not commit secrets.
