# Developer Spec: Deployment Fixes + Sales System Contract + UX Fixes

**Date:** 2026-01-23  
**Purpose:** Developer-ready implementation plan combining deployment root-cause fixes, Sales Order ↔ Distribution contract, **system-wide view-details readability**, **customer name from sales orders** (not ShipStation), and **unmatched-shipment icon + manual upload**.

**Source:** Enhances `docs/review/12_DEPLOYMENT_FAILURE_ROOT_CAUSE_AND_FIX.md` with additional requirements below.

**References:**
- Full deployment root-cause analysis, verification SQL, and Sales Order ↔ Distribution contract (backfill SQL, migration snippet, validation): **`docs/review/12_DEPLOYMENT_FAILURE_ROOT_CAUSE_AND_FIX.md`** (Sections 3, 6, 7).
- View-details readability aligns with **`docs/plans/IMMEDIATE_FIXES_AND_UI_IMPROVEMENTS.md`** (Distribution Log modal, etc.); this spec extends that to **all** detail surfaces system-wide.

---

## 1) Executive Summary

Deployment failures are likely caused by **DigitalOcean readiness probe path/delay** misconfiguration. There is a **confirmed runtime 500** on `/admin/sales-orders/<id>` due to a **missing `OrderPdfAttachment` import**. The Sales Order ↔ Distribution linkage exists but needs enforcement.

**Additional scope (this spec):**

1. **System-wide view-details readability** — All "View Details" modals and detail screens (Distribution Log modal, Sales Dashboard Order Details modal, Sales Order detail page, Customer profile, etc.) remain too hard to read. Apply consistent, high-readability styling **everywhere**.
2. **Customer name from matched sales orders** — Customer profile information, including **the name of each customer displayed**, must be based on **matched sales orders**, not ShipStation details (which are inconsistently spelled or abbreviated). ShipStation is for linking only; sales orders are source of truth for display.
3. **Unmatched shipments** — Any distribution/shipment **without a matched sales order** must show a **warning icon** and an **option to manually upload** (e.g. PDF to match/link an order).

---

## 2) Evidence & Findings (from Doc 12)

### Deployment Symptoms
- Release phase completes; Gunicorn binds to 8080; logs show `Listening at: http://0.0.0.0:8080`.
- Intermittent readiness failures: `Readiness probe failed: dial tcp <pod-ip>:8080: connect: connection refused`.
- App serves requests after startup.

### Health Endpoints
- **`/health`** — Returns `{"ok": true}`, no DB.
- **`/healthz`** — Returns `"ok"` 200, for k8s/DO probes, no DB.

### Runtime 500 (Confirmed)
- **Route:** `GET /admin/sales-orders/<id>`
- **Error:** `NameError: name 'OrderPdfAttachment' is not defined`
- **Location:** `app/eqms/modules/rep_traceability/admin.py` — `sales_order_detail` uses `OrderPdfAttachment` but only imports `SalesOrder`.

### Data Model
- `DistributionLogEntry.sales_order_id` — FK exists, **nullable**.
- `SalesOrder.customer_id` — FK to customers, NOT NULL.
- Customer canonical identity via `customers.company_key`; address/facility should come from **sales orders**, not ShipStation.

---

## 3) Root Cause Analysis — Deployment (from Doc 12)

| Candidate | Symptom | Fix | Confidence |
|-----------|---------|-----|------------|
| Readiness path wrong | connection refused | Use `/healthz`, set path explicitly | **HIGH** |
| No initial delay | Probe before app binds | Initial delay **15 s** | **HIGH** |
| `--preload` slow startup | Workers slow | Keep for now; remove only if issues persist | LOW |
| Schema health check | First request slow | `/healthz` bypasses; no change | LOW |
| PORT missing | Wrong bind | Resolved (PORT=8080 set) | N/A |

---

## 4) Fix Plan

### P0 — Must Do Now

#### P0-1: Fix `OrderPdfAttachment` Import (500 Bug)

**File:** `app/eqms/modules/rep_traceability/admin.py`  
**Change:** Add `OrderPdfAttachment` to the import used in `sales_order_detail`:

```python
# FROM:
from app.eqms.modules.rep_traceability.models import SalesOrder

# TO:
from app.eqms.modules.rep_traceability.models import SalesOrder, OrderPdfAttachment
```

Ensure **every** route that uses `OrderPdfAttachment` (e.g. `distribution_log_entry_details`, `sales_order_detail`, etc.) either imports it locally or receives it via a shared import at top of file.

**Verification:**
```bash
python -c "from app.eqms.modules.rep_traceability.admin import sales_order_detail; print('OK')"
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/admin/sales-orders/1
# Expect 200 or 302, not 500.
```

#### P0-2: Configure DigitalOcean Readiness Probe

**Location:** DO App Platform → Settings → Health Checks  

| Setting | Value |
|---------|--------|
| Path | `/healthz` |
| Initial Delay | `15` seconds |
| Timeout | `5` seconds |
| Period | `10` seconds |
| Failure Threshold | `3` |

#### P0-3: Separate Release Phase from Run Phase

**Release Command (DO Release Phase):**
```bash
python scripts/release.py
```

**Run Command (DO Run Command):**
```bash
gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload --access-logfile - --error-logfile -
```

#### P0-4: System-Wide View-Details Readability

**Problem:** View-details modals and detail screens (Distribution Log Details modal, Sales Dashboard Order Details modal, Sales Order detail page, Customer profile, etc.) are still too hard to read: cramped spacing, low contrast, overlapping text, poor scroll behavior.

**Requirement:** Apply **one shared readability standard** to all detail surfaces.

**Scope:**
- Distribution Log **Details** modal (`#entry-details-modal`)
- Sales Dashboard **Order Details** modal (`#order-details-modal`)
- Sales Order **detail page** (`/admin/sales-orders/<id>`)
- Customer **profile** page (`/admin/customers/<id>`)
- Any other "view details" modal or full-page detail view (e.g. tracing report detail, etc.)

**Readability rules (apply everywhere):**

| Rule | Value |
|------|--------|
| Section headers | `font-size: 14px; font-weight: 600; margin-bottom: 12px; color: var(--text);` |
| Field labels | `font-size: 12px; color: var(--muted); margin-bottom: 4px;` |
| Field values | `font-size: 14px; line-height: 1.6; margin-bottom: 12px;` |
| Section spacing | `margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border);` |
| Modal/content padding | `24px` (not 16px or 20px) |
| Modal max-width | `700px` |
| Modal max-height | `80vh` |
| Scroll area | `max-height: calc(80vh - 120px); overflow-y: auto; overflow-x: hidden;` |
| Backdrop | `rgba(0,0,0,0.5)`; modal properly stacked above |
| Contrast | Body text ≥ 4.5:1; muted ≥ 3:1 |
| ESC | Close modal on Escape |
| No overlap | Content must not overlap page behind modal; scroll contained inside modal |

**Implementation:**
- Introduce a shared **CSS class** (e.g. `.detail-panel` or `.view-details-readability`) and apply to all detail modals and detail-page main content.
- Optionally add a shared **base template** or **Jinja include** for detail modals so structure and styles are consistent.
- **Files to touch:**  
  - `app/eqms/templates/admin/distribution_log/list.html` (entry-details modal)  
  - `app/eqms/templates/admin/sales_dashboard/index.html` (order-details modal)  
  - `app/eqms/templates/admin/sales_orders/detail.html` (full page)  
  - `app/eqms/templates/admin/customers/detail.html` (full page)  
  - `_layout.html` or `admin-styles.css` (shared styles)

**Acceptance criteria:**
- [ ] All view-details modals use the same typography/spacing/scroll rules.
- [ ] All full-page detail views use the same rules for main content.
- [ ] No overlapping text; scroll contained; ESC closes modals.
- [ ] Readable on desktop widths ≥768px without horizontal scroll.

#### P0-5: Customer Name from Matched Sales Orders (Not ShipStation)

**Problem:** Customer names and profile information are often taken from ShipStation (e.g. `facility_name` on distribution, or customer created from ShipStation ship-to). ShipStation data is inconsistently spelled or abbreviated.

**Rule:** **Customer profile information, including the displayed name of each customer, must be based on matched sales orders.** ShipStation is for **linking** only; **sales orders are source of truth** for display.

**Requirements:**

1. **Display logic**
   - **When a distribution has `sales_order_id`:**  
     - Prefer **customer/facility name from the linked Sales Order** (e.g. `order.customer.facility_name` where that customer was created/updated from **sales order** data, or a dedicated `order.ship_to_name` if you add it).
   - **When an order has `customer_id`:**  
     - Prefer **customer name** from the **sales order context** (e.g. parsed ship-to from PDF, or SO-backed customer), **not** from ShipStation.
   - **When there is no matched sales order:**  
     - Fall back to existing `facility_name` / `customer_name` only for display; treat as "unmatched" (see P0-6).

2. **Data model / backend**
   - Ensure **sales orders** store canonical ship-to / customer info (from PDF import, manual entry, etc.).  
   - When creating/updating **customers** from import or manual flows, **use sales order (or parsed) data**, not ShipStation, for `facility_name` and address.  
   - ShipStation sync: use ShipStation **only** to **link** orders/distributions to existing customers or to **match** by order number; **do not** overwrite customer `facility_name` or profile fields from ShipStation.

3. **Surfaces to update**
   - **Distribution Log** list and **Details** modal: show customer name from linked sales order when `sales_order_id` present; otherwise fallback.
   - **Sales Dashboard** recent orders and **Order Details** modal: same rule.
   - **Sales Orders** list and **detail** page: use sales-order–derived customer name.
   - **Customer** list and **profile**: names must reflect sales-order–sourced data (e.g. customer updated from SO imports), not ShipStation.

**Implementation notes:**
- Add helpers, e.g. `display_facility_name(entry)` / `display_customer_name(order)` that prefer SO-derived name when available.
- Where dashboard or distribution logic uses `e.facility_name` or `e.customer_name` for **display**, switch to SO-based name when `e.sales_order_id` is set.
- **Files to touch:**  
  - `app/eqms/modules/rep_traceability/service.py` (dashboard aggregates, recent orders)  
  - `app/eqms/modules/rep_traceability/admin.py` (entry-details JSON, order-details JSON, sales order detail context)  
  - `app/eqms/templates/admin/distribution_log/list.html`  
  - `app/eqms/templates/admin/sales_dashboard/index.html`  
  - `app/eqms/templates/admin/sales_orders/list.html`  
  - `app/eqms/templates/admin/sales_orders/detail.html`  
  - `app/eqms/templates/admin/customers/list.html`  
  - `app/eqms/templates/admin/customers/detail.html`

**Acceptance criteria:**
- [ ] Whenever a distribution or order has a matched sales order, displayed customer name comes from sales-order–backed data.
- [ ] ShipStation is not used as source of truth for customer name or profile display.
- [ ] Customer profile name matches the sales-order–derived name where applicable.

#### P0-6: Unmatched Shipments — Icon + Manual Upload

**Problem:** Some distributions have **no** linked sales order (`sales_order_id` IS NULL). These are hard to notice and there is no clear way to fix them.

**Requirements:**

1. **Icon**
   - For **every** distribution/shipment **without** a matched sales order (`sales_order_id` IS NULL), show a **warning icon** (e.g. `⚠` or a distinct icon) in the Distribution Log table and in any list that shows distributions (e.g. dashboard, customer profile distributions tab).
   - Use `title`/`aria-label` such as: `No matched sales order. Upload PDF to link.`

2. **Manual upload**
   - Provide an **option to manually upload** (e.g. PDF) for that distribution:
     - **In Distribution Log:** per-row action **"Upload PDF"** or **"Match order"** when `sales_order_id` is NULL.  
       - Flow: upload PDF → parse → create or match sales order → link distribution to that order → clear "unmatched" state.
     - **In Distribution Details modal:** when entry has no `sales_order_id`, show the same warning icon and an **"Upload PDF to match"** (or similar) button that opens upload flow for that entry.

3. **Persistence**
   - Store uploaded PDFs per order/distribution (reuse existing `OrderPdfAttachment` / storage pattern).  
   - After successful match, the distribution gains `sales_order_id` and the icon is no longer shown.

**Implementation:**
- **Backend:**  
  - `GET /admin/distribution-log/entry-details/<id>` JSON must include `has_sales_order: true | false` (e.g. `entry.has_sales_order = entry.sales_order_id is not None`).  
  - Add route `POST /admin/distribution-log/<entry_id>/upload-pdf` (or equivalent) to accept PDF, parse, create/match sales order, set `distribution_log_entries.sales_order_id`, and store attachment. Reuse existing PDF parsing and `OrderPdfAttachment` / storage where applicable.
- **Templates:**  
  - Distribution Log list: add icon + "Upload PDF" (or "Match order") in Actions column for rows with `e.sales_order_id is none`.  
  - Entry-details modal: when `data.entry.has_sales_order === false`, show icon + "Upload PDF to match" control.
- **Files to touch:**  
  - `app/eqms/modules/rep_traceability/admin.py` (entry-details JSON, upload route)  
  - `app/eqms/templates/admin/distribution_log/list.html`  
  - Any other list/detail views that show distribution rows.

**Acceptance criteria:**
- [ ] Rows with `sales_order_id` NULL show a clear warning icon.
- [ ] "Upload PDF" / "Match order" (or equivalent) available for unmatched shipments in list and in Details modal.
- [ ] Upload → match → link flow updates `sales_order_id` and removes the icon.

---

### P1 — Hardening

#### P1-1: Pre-Deploy Smoke Test

Before each deploy, run:
```bash
python -c "from app.wsgi import app; print('Import OK')"
```

#### P1-2: Sales Order ↔ Distribution Contract

- **Backfill:** Match distributions to sales orders by `order_number` where possible; set `sales_order_id`.
- **Migration:** After backfill, add migration to make `distribution_log_entries.sales_order_id` **NOT NULL** (with guard to fail if any NULLs remain).
- **Manual entry:** Require sales order selection when creating manual distribution entries.
- **CSV/PDF import:** Create or match sales order first, then create distributions with `sales_order_id` set.

#### P1-3: Structured Startup Logging

In `create_app()` (e.g. `app/eqms/__init__.py`), add:
```python
import logging
logging.getLogger(__name__).info("create_app() complete; app ready to serve")
```

---

### P2 — Cleanups

- **Remove or deprecate** `scripts/start.py` if unused.
- **Add** `docs/DEPLOY_CHECKLIST.md`: health check config, verification steps, rollback.

---

## 5) DigitalOcean App Platform Settings (Copy-Paste)

**Readiness probe:**
```
Path: /healthz
Initial Delay Seconds: 15
Timeout Seconds: 5
Period Seconds: 10
Failure Threshold: 3
```

**Liveness (optional):**
```
Path: /healthz
Initial Delay Seconds: 30
Timeout Seconds: 5
Period Seconds: 30
Failure Threshold: 3
```

**Release command:** `python scripts/release.py`  
**Run command:**  
`gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload --access-logfile - --error-logfile -`

**Required env vars:** `PORT`, `ENV`, `DATABASE_URL`, `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `STORAGE_BACKEND`, S3-related vars as in Doc 12. **Do not log secrets.**

---

## 6) Verification Steps

### Local

```bash
export PORT=8080
export ENV=development
export DATABASE_URL="postgresql://..."
export SECRET_KEY="test-key-32-chars-or-more"

python scripts/release.py
gunicorn app.wsgi:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60 --preload

curl -s http://localhost:8080/healthz   # ok
curl -s http://localhost:8080/health    # {"ok":true}
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/admin/sales-orders/1  # 200 or 302, not 500
python -c "from app.wsgi import app; print('OK')"
```

### Post-Deploy (DO)

1. Health checks use `/healthz`, 15s initial delay.
2. Logs show release complete then Gunicorn listening.
3. `curl -s https://<app>/healthz` → `ok`.
4. `/admin/sales-orders/<id>` returns 200 (or 302), not 500.
5. **UX checks:**  
   - View-details modals and detail pages are readable (spacing, contrast, scroll).  
   - Customer names match sales-order–derived data where orders exist.  
   - Unmatched shipments show icon and "Upload PDF" / "Match order".

---

## 7) Developer Agent Checklist (Marching Orders)

### P0 (Do Immediately, In Order)

1. **Fix `OrderPdfAttachment` import**  
   - In `rep_traceability/admin.py`, add `OrderPdfAttachment` to imports used by `sales_order_detail` (and any other route using it).  
   - Verify `/admin/sales-orders/<id>` returns 200/302.

2. **Configure DO health checks**  
   - Path `/healthz`, initial delay 15s, timeout 5s, period 10s, failure threshold 3.

3. **Separate release vs run**  
   - Release: `python scripts/release.py`.  
   - Run: `gunicorn ...` (as in Section 5).

4. **System-wide view-details readability**  
   - Apply shared readability rules to all detail modals and detail pages.  
   - Use shared CSS and/or includes; ensure no overlap, proper scroll, ESC close.

5. **Customer name from sales orders**  
   - Prefer SO-derived customer/facility name everywhere when a matched order exists.  
   - Do not use ShipStation as source of truth for display.  
   - Update dashboard, distribution log, sales orders, customer list/profile.

6. **Unmatched shipments**  
   - Show warning icon for `sales_order_id` NULL.  
   - Add "Upload PDF" / "Match order" for unmatched rows and in Details modal.  
   - Implement upload → parse → match → set `sales_order_id`.

### P1 (After P0)

7. Add pre-deploy smoke test (`python -c "from app.wsgi import app; print('Import OK')"`).  
8. Plan and execute Sales Order ↔ Distribution backfill + NOT NULL migration.  
9. Add startup logging in `create_app()`.

### P2

10. Remove or deprecate `scripts/start.py`.  
11. Add `docs/DEPLOY_CHECKLIST.md`.

### Regression Checks

- [ ] `/healthz` → 200, `/health` → `{"ok":true}`  
- [ ] `/admin/sales-orders/<id>` → 200/302  
- [ ] Distribution Log list and Details modal load  
- [ ] Sales Dashboard and Order Details modal load  
- [ ] Customer list and profile load  
- [ ] Unmatched rows show icon + upload option  
- [ ] Customer names reflect sales-order source where applicable  
- [ ] No Python tracebacks in DO logs

### Do NOT

- Add unrelated features.  
- Change schema (e.g. NOT NULL) before backfill.  
- Remove `--preload` unless deploy issues persist.  
- Log secrets.

---

## 8) Appendix: Key Files

| Component | File |
|-----------|------|
| Health | `app/eqms/routes.py` |
| App factory | `app/eqms/__init__.py` |
| Release | `scripts/release.py` |
| WSGI | `app/wsgi.py` |
| Sales order detail (500 fix) | `app/eqms/modules/rep_traceability/admin.py` |
| OrderPdfAttachment | `app/eqms/modules/rep_traceability/models.py` |
| DistributionLogEntry | `app/eqms/modules/rep_traceability/models.py` |
| Customer | `app/eqms/modules/customer_profiles/models.py` |
| Distribution list + Details modal | `app/eqms/templates/admin/distribution_log/list.html` |
| Dashboard + Order Details modal | `app/eqms/templates/admin/sales_dashboard/index.html` |
| Sales order detail page | `app/eqms/templates/admin/sales_orders/detail.html` |
| Customer profile | `app/eqms/templates/admin/customers/detail.html` |

---

*This spec enhances `docs/review/12_DEPLOYMENT_FAILURE_ROOT_CAUSE_AND_FIX.md` with system-wide view-details readability, customer-name-from–sales-orders, and unmatched-shipment icon + manual upload. Use this document as the single developer-ready reference for implementation.*
