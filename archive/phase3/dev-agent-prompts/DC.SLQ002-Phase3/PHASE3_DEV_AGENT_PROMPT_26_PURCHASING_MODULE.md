# Prompt 26 — Purchasing Module Enhancements

## Context

The Purchasing module holds ~150 imported POs linked to Supplier records. Following the Equipment module cleanup pattern, apply targeted improvements for usability and clarity.

Read `app/eqms/modules/purchasing/admin.py` and `app/eqms/templates/admin/purchasing/list.html` in full before starting.

---

## Task A — Remove Unused Import Buttons

In `list.html`, remove:
- **Import PDF** (`purchasing_import_pdf_get`) button
- **Import PO Log** (`purchasing_import_log_get`) button

Keep only:
- **New PO** (gated by `purchasing.create` as today)

Do **not** delete the underlying routes or templates — just hide the buttons from the header.

---

## Task B — Summary Cards

Above the PO table, add a row of at-a-glance summary cards (styled consistently with the Equipment list cards). Compute these in the `purchasing_list()` route using a single lightweight aggregation query (not from the paginated page results).

Cards:
1. **Open** — count of POs with status `pending` or `partial`. Links to `?status=pending` (or a combined open filter — see below).
2. **Received (YTD)** — count of POs with status `received` and `order_date` in the current calendar year. No link.
3. **Total** — total PO count (no filter). Links to the unfiltered list.
4. **Unlinked** — count of POs where `supplier_id IS NULL`. Links to `?unlinked=1`. Show this card with a warning color when count > 0.

For the **Unlinked** filter: add `?unlinked=1` support in the route — when set, filter to `supplier_id IS NULL`.

---

## Task C — Year and Supplier Filters

Add two new filter controls to the filter form (alongside the existing search + status filters):

1. **Year** dropdown — populated from the distinct `order_date` years present in the table, descending. Default: blank (all years). Query param: `year`.
2. **Supplier** dropdown — populated from all `Supplier` records ordered by name, with a blank "All" option. Query param: `supplier_id`. When selected, filters `PurchaseOrder.supplier_id == supplier_id`.

Apply these new filters in `purchasing_list()`.

---

## Task D — Column Cleanup

In the PO table:

1. **Remove the "Verified" column** (`meets_requirements` field). This field is rarely populated and adds noise. The detail page still shows it.
2. **Remove the "Attachments" column** (bare count). The detail page shows attachments; the count is not actionable from the list. Replace with a small paper clip icon (📎 or a CSS icon) shown only when `po.attachments|length > 0`, inline next to the PO number — no separate column.
3. **Remove the "← Back to Admin" button** from the header — breadcrumbs already handle navigation.
4. The **Supplier** column should show the raw vendor text (from notes) for unlinked POs, as it does today — keep this behavior.

---

## Task E — Open POs Section Fix

Currently the route computes `open_purchase_orders` (a separate all-pages query of pending/partial POs) but the template never renders it. Fix this inconsistency:

- **Option**: Drop the separate `open_purchase_orders` query from the route entirely (it's unused). The summary card from Task B provides the open-count.
- Also fix the `open_count` in the template — it currently counts only the current page. Remove it and rely on the Task B summary card instead.

---

## Task F — Tests

Add `tests/test_p26_purchasing.py`:
- List page responds 200 for admin and staff.
- Import PDF button absent; New PO button present.
- Summary cards present (open, received-ytd, total, unlinked).
- Year and supplier filter params accepted without error.
- Unlinked filter (`?unlinked=1`) returns only POs with no supplier.
- Verified and Attachments columns absent from the table headers.

Full suite must remain green (`pytest -q`). No migration needed — all changes are UI/route.

---

## Deployment

Commit code changes (Tasks A–F) and push to `main`. Per the operating rhythm, push once the suite is green. Tag the commit: `"P26: purchasing list UX — summary cards, year/supplier filters, column cleanup"`.
