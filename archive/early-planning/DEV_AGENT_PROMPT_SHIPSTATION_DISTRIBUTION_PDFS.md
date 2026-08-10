# ShipStation sync, distribution log, and packing-slip PDFs

**Audience:** Operators preparing a data load, and developers maintaining traceability.  
**Product goal:** After ShipStation sync and PDF upload from the `Distribution/` corpus, you can **export an accurate distribution log** and **download stored PDFs** per distribution (sales order + packing slip).

**Critical domain rule:** A **single sales order** may link to **several** `DistributionLogEntry` rows (multiple shipments). Export, matching, and storage paths must preserve that.

---

## 0. Implementation status (verified in codebase; aligns with `f2382d0` and follow-ups)

The following is implemented in `app/eqms/modules/rep_traceability/` and related modules:

| Area | What shipped |
|------|----------------|
| **Routes (blueprint prefix `/admin`)** | Bulk: `POST /admin/packing-slips/import-bulk` → `packing_slips_import_bulk`. Per distribution: `POST /admin/distribution-log/<id>/upload-packing-slip` (replaces `upload-label`). Optional form fields: `packing_slip_file` or legacy `label_file`. |
| **Audit** | `packing_slips.import_bulk`; per-entry `distribution_log_entry.upload_packing_slip`. |
| **`pdf_type`** | Canonical **`packing_slip`**. Alembic revision **`t2u3v4w5x6`** updates existing rows from `shipping_label` / `delivery_verification` → `packing_slip`. Code still recognizes legacy types via `is_packing_slip_pdf_type()` in `rep_traceability/utils.py`. |
| **Parser / split** | Multi–packing-slip text segments per page (`split_text_into_packing_slip_segments`, `_parse_packing_slip_segment`), improved SKU/qty handling, U+FFFD normalized in slip text for lots. `split_pdf_into_pages(..., strict_multi_page=True)` raises **`PdfSplitError`** if a multi-page PDF cannot be split (e.g. PyPDF2 missing or split failure)—bulk import surfaces a clear error instead of silently treating the whole file as one page. |
| **Matching** | `_match_distribution_for_label`: tracking first; normalized order number with bounded candidates and disambiguation; optional `ss_shipment_id` on parsed labels when present. Avoids naive leading `ILIKE` on order number as the first rule. |
| **Re-uploads** | `_delete_packing_slip_attachments_for_distribution` removes prior packing-slip attachments for that distribution (DB + storage) before storing a new one (bulk matched path and per-entry upload). |
| **Storage keys** | When `order_number` is used for keys, path includes **`_de{distribution_entry_id}`** so multiple distributions under the same order do not overwrite each other’s blobs. |
| **Download / RBAC** | `GET /admin/distribution-log/pdf/<attachment_id>/download?entry_id=<distribution_id>` with **`distribution_log.view`**—distribution modal `download_url` uses this route so downloads do **not** require `sales_orders.view`. Sales-order pages still use `/admin/sales-orders/pdf/<id>/download`. **`entry_id` is required** (400 if omitted). |
| **CSV export** | `distribution_log_export`: one row per `DistributionLogEntry`; columns include `sku_1..3`, `lot_1..3`, `qty_1..3`, `tracking_number`, `ss_shipment_id`, `sales_order_id`, `line_quantity_total`, **`overflow_lines`** (semicolon-separated `sku/lot/qty` for lines beyond three), plus ship/facility/source columns. |
| **UI** | Distribution log source filter includes **`pdf_import`**. Import page anchor `#packing-slips` (and `#shipping-labels` still scrolls for old bookmarks). |
| **Docs in repo** | `MANIFEST.md` — short operator note (SO PDFs → ShipStation → packing slips; PyPDF2). |
| **Tests** | `tests/test_packing_slip_and_distribution_export.py`; export header assertions may appear in `tests/test_rep_traceability.py` where DB setup allows. |

**Corrections vs. dev-agent prose (minor):**

- Routes live under the **`/admin`** prefix because `rep_traceability` is registered with `url_prefix="/admin"`.
- Bulk packing slip import is gated by **`sales_orders.import`**, not `distribution_log.import`.
- If a single PDF page yields **both** matched and unmatched parsed segments, the bulk importer may also store an **unmatched** copy of the page in addition to matched attachments—worth spot-checking in QA so orphan rows in “unmatched” views are understood.

---

## 1. Business context

- **ShipStation sync** (`app/eqms/modules/shipstation_sync/service.py::run_sync`) creates `DistributionLogEntry` rows (`source='shipstation'`) and `DistributionLine` children when applicable. It links to an existing `SalesOrder` when `order_number` matches; customer/SO creation rules follow comments in `run_sync`.
- **`Distribution/` PDFs:** Sales order PDFs establish customers and lines; packing slips attach to distributions (and optionally tie to the same `sales_order_id` as the shipment).

---

## 2. Reference inventory: `Distribution/` PDFs (repo root)

| File | Role (expected) |
|------|-------------------|
| `2025Sales Orders.pdf` | Large sales-order compilation. |
| `*SalesOrders.pdf` | Monthly sales order PDFs. |
| `*PackingSlips.pdf` | Monthly packing slip PDFs (often **~two slips per page**). |

Root `*.pdf` is gitignored; the `Distribution/` folder may still be visible in the working tree for local uploads.

---

## 3. Code map (current)

| Concern | Location |
|--------|----------|
| ShipStation sync | `app/eqms/modules/shipstation_sync/service.py`, `shipstation_client.py`, `parsers.py` |
| Distribution export, uploads, downloads | `app/eqms/modules/rep_traceability/admin.py` |
| PDF parsing / split | `app/eqms/modules/rep_traceability/parsers/pdf.py` |
| Packing slip type helper | `app/eqms/modules/rep_traceability/utils.py` (`is_packing_slip_pdf_type`) |
| Migration | `migrations/versions/t2u3v4w5x6_migrate_packing_slip_pdf_types.py` |

---

## 4. Historical review notes (context)

Early review identified: multi-slip pages, strict need for `distribution_lines` in exports, PyPDF2 dependency, and ambiguous label matching. Those items are largely addressed in §0; keep **overflow_lines** in mind when any distribution has **more than three** line rows.

---

## 5. Product decisions (confirmed)

| Topic | Decision |
|--------|-----------|
| **Layout** | Typically **~two packing slips per page**; multiple slips per page supported. Parser must associate the **correct** slip with the target distribution; another slip on the same page image is acceptable. |
| **Export** | **One row per distribution** with **three** SKU/lot/qty slot groups; additional lines in **`overflow_lines`**. |
| **Re-uploads** | **Replace** with the most recent upload (no version stack). |
| **Sales order ↔ distributions** | One sales order may map to **many** distributions. |
| **Legacy URLs** | `/shipping-labels/...` may be removed after release; `#shipping-labels` hash tolerance on import page is optional UX only. |

---

## 6. Suggested QA (after deploy + migration)

1. `alembic upgrade head` on the target DB.  
2. Import a small sales order PDF → customers / SOs as expected.  
3. ShipStation sync for a **narrow date window** → multiple distributions per order if applicable.  
4. Bulk packing slips from `Distribution/` → matched rows; check **unmatched** list for stragglers.  
5. Re-upload a packing slip on one distribution → single current attachment.  
6. Export CSV → columns `sku_1..3`, `overflow_lines`, totals.  
7. Modal **Download** on a packing slip without `sales_orders.view` but with **`distribution_log.view`**.

---

## 7. Before you run ShipStation sync and upload `Distribution/` PDFs

Do these **in order** on the environment where you will load data (local, staging, or production):

1. **Deploy / pull** the revision that contains the packing-slip work (e.g. **`f2382d0`** or later on `main`), with no pending hotfix that reverts these routes.
2. **Run database migrations:**  
   `alembic upgrade head`  
   This applies **`t2u3v4w5x6`** so legacy `pdf_type` values become **`packing_slip`**.
3. **Runtime dependencies:** Install app dependencies from **`requirements.txt`** so **`PyPDF2`** is available. Multi-page PDFs **must** split per page; otherwise import will error with **`PdfSplitError`** instead of silently corrupting page boundaries.
4. **Configure storage** (`app/eqms/storage` / env) so PDF bytes can be **written and read** (local path or S3-compatible). Confirm `/admin/diagnostics/storage` if you use that panel.
5. **ShipStation environment variables:** Set **`SHIPSTATION_API_KEY`** and **`SHIPSTATION_API_SECRET`**. Optionally tune **`SHIPSTATION_SINCE_DATE`**, **`SHIPSTATION_MAX_PAGES`**, **`SHIPSTATION_MAX_ORDERS`** for the date range you are backfilling (defaults may truncate large backfills).
6. **Lot normalization (optional but recommended):** Ensure **`LotLog.csv`** is present/updated where `resolve_lotlog_path()` expects it, so ShipStation internal-note lots align with shipped SKUs.
7. **RBAC:** Your user (or service account) needs permissions to: run ShipStation (`shipstation.run`), view/edit distribution log as required (`distribution_log.view` / `distribution_log.edit`), **import sales orders PDFs** (`sales_orders.import` — used for **bulk packing slips** too), and export (`distribution_log.export`) when you verify CSV output.
8. **Recommended load order (from `MANIFEST.md`):**  
   **Sales order PDFs first** (so customers and `SalesOrder` rows exist where PDF import creates them) → **ShipStation sync** (creates/links distributions; one order may create several rows) → **Bulk packing slips** from `Distribution/` (or per-row upload from the distribution log modal).  
   If you sync ShipStation before SO PDFs, more rows may remain temporarily unmatched until PDFs or manual customer matching catch up—that is expected per `run_sync` design.
9. **After sync + imports:** Spot-check **ShipStation skipped** / diagnostics if counts look wrong; review **unmatched packing slip** attachments; export **`distribution_log_export_*.csv`** and confirm **`overflow_lines`** for any heavy multi-line shipments.

---

*End of document.*
