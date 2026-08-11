# Prompt P4-04 — Integrate the NRE Invoice Tracker with sales orders

## Context

You are the Phase 4 Dev Agent for the Silq eQMS platform (Flask + SQLAlchemy modular monolith,
DigitalOcean App Platform, Postgres, Spaces). You own the entire mechanical pipeline: code, tests,
the local gate, commit, push, and running scripts. **The operator is not a coder and performs no
code-level actions.** Never ask him to run, commit, execute, or edit anything — including
environment files or credentials. If a diagnostic needs a secret, run it server-side behind an
existing admin page, as P4-03B Task E did.

Deployment is push to `main`. DigitalOcean builds, runs `python scripts/release.py` pre-deploy, then
rolls the component. **There is no CI** — the local gate is the only thing between your commit and
production.

**Current Alembic head: `f8a9b0c1d2e3`.** This change set **does need one additive migration** — see
Task A.

**Baseline gate: 418 passed, 1 skipped.**

### Why this work exists

The Upcoming NRE Invoice Tracker is an isolated, manually-entered ledger that knows nothing about
sales orders. The operator wants it integrated with the NRE dashboard and the sales-order content
below it, in his words:

> "These entries will still start manually, however once a sales order is uploaded either from here
> or from elsewhere in the system, the system should automatically pair any associated files
> previously uploaded to that Invoice Tracker entry to the new sales order entry below. I will still
> handle the deletion of anything from the invoice tracker, I just want the automatic pairing of the
> files."

And from the sales-order side: once an order is typed NRE Project, he wants the option to match it to
an existing tracker entry.

**The tracker is currently empty.** `nre_project_entries` and `nre_tracker_attachments` both hold
zero rows — the previous contents were deleted before P4-01 and are unrecoverable. The operator will
re-enter entries by hand. So there is **no historical tracker data to migrate**, and your matching
logic must work for entries he creates from now on, against the 26 NRE sales orders that already
exist.

### The trap that shapes the design

`NRETrackerAttachment.nre_entry_id` is `ondelete="CASCADE"` and the relationship carries
`cascade="all, delete-orphan"` (`modules/nre_projects/models.py` lines 78-80, 92). The operator
deletes tracker entries himself and expects to keep doing so. If "pairing" merely pointed a sales
order at files that still belonged to the tracker entry, then deleting that entry later would
destroy the files the sales order depends on — silently. That is why files **move**.

---

## Decisions (do not re-ask)

| Topic | Decision |
| --- | --- |
| Files on match | **Move** the tracker entry's attachments onto the sales order. After a successful match the tracker entry owns no files, so deleting it can never take them. Do not copy, do not reference in place. |
| Money authority | **The sales order is the record.** `SalesOrder.order_amount`, parsed from the PDF, is authoritative for a matched job. Fall back to the tracker's `invoice_amount` **only** when the sales order has no parsed amount. Never silently overwrite one with the other — when they disagree, show the disagreement. |
| Automatic matching key | **Normalized order number only.** Use `normalize_order_number` from `modules/rep_traceability/service.py`. No fuzzy matching on customer or amount, ever — a wrong automatic match moves files onto the wrong regulated record. |
| Matched entry display | A matched entry **drops off the Upcoming list**; the sales order row below becomes the single row for that job. Each job is counted exactly once. |
| Deletion | The operator keeps sole control of deleting tracker entries. Do not auto-delete, auto-archive or hide entries on any rule other than being matched. |
| No lateness logic | Standing rule: **no overdue / aging / late / stale features**, no thresholds, no derived warning states. `expected_invoice_date` is displayed as data, never evaluated against today. |
| Tracker statuses | The legacy tracker vocabulary and the dashboard vocabulary differ. Map them explicitly — see Task D. |

---

## Task A — Migration: let sales-order attachments carry any file type

**Files:** new migration in `migrations/versions/`,
`app/eqms/modules/rep_traceability/models.py`

`NRETrackerAttachment` carries `content_type` and `size_bytes` (models.py lines 95-96).
`OrderPdfAttachment` does not (`modules/rep_traceability/models.py` lines 152-168). Moving a tracker
file into `order_pdf_attachments` would therefore drop that metadata, and tracker files are not
necessarily PDFs — spreadsheets, images and documents are all plausible.

1. Add two **nullable** columns to `order_pdf_attachments`: `content_type` (String(128)) and
   `size_bytes` (Integer). Nullable with no server default, so existing rows are untouched and the
   migration is safe against live data.
2. Chain the revision from `f8a9b0c1d2e3`. One head only.
3. Update the model to match.
4. The sales-order attachment view and download routes (`sales_order_pdf_view`,
   `sales_order_pdf_download`) currently assume PDF. Make them honour `content_type` when it is
   present and fall back to the existing PDF behaviour when it is null. A moved `.xlsx` must not be
   served as `application/pdf`.
5. Introduce the `pdf_type` value `nre_tracker_file` for moved files. `pdf_type` is a NOT NULL free
   text column, so no constraint work is needed. **Do not** reuse `sales_order_page` — P4-01
   narrowed re-import deletion to exactly that value plus a null distribution, so a moved tracker
   file tagged `sales_order_page` would be destroyed the next time the operator re-imports that
   order's PDF. This matters; get it right.

---

## Task B — The match operation

**Files:** `app/eqms/modules/nre_projects/` (service + admin),
`app/eqms/modules/rep_traceability/admin.py`

Write **one** service function that matches a tracker entry to a sales order, and call it from every
entry point. Two implementations that drift apart is the exact defect P4-01 existed to remove.

It must:

1. Refuse to match when the sales order is not typed `nre_project`, and refuse when the entry is
   already matched to a different order. Flash a clear message rather than raising.
2. Set `NREProjectEntry.sales_order_id`.
3. **Move every attachment**: for each `NRETrackerAttachment` on the entry, create an
   `OrderPdfAttachment` on the sales order with the same `storage_key`, `filename`, `content_type`,
   `size_bytes` and `uploaded_by_user_id`, `pdf_type="nre_tracker_file"`, then delete the
   `NRETrackerAttachment` row. **Reuse the same `storage_key` — do not copy, re-upload or delete the
   object in Spaces.** The blob does not move; only ownership of the row does. Deleting the blob
   would destroy the file, and the local Spaces credentials are stale so you cannot verify object
   operations from a local run anyway.
4. Carry the amount per the decisions table: if `SalesOrder.order_amount` is null and the entry has
   an `invoice_amount`, copy it to the sales order. If both are present and differ, change neither
   and record the disagreement so the UI can show it (Task E).
5. Map the tracker status onto the sales order per Task D.
6. Record `nre_tracker.matched_sales_order` with metadata carrying the entry id, the sales order id
   and order number, how the match was made (`manual` or `auto_order_number`), the number of files
   moved with their filenames, the amount decision taken, and the status mapping applied. This event
   is the only record that those files ever belonged to the tracker entry.
7. Be idempotent: matching an entry that is already matched to *this* sales order must not duplicate
   attachments.

### Entry points that must call it

- **Automatic, on sales-order arrival.** When a sales order typed `nre_project` is created or its
  order number becomes known, look for an unmatched tracker entry whose `order_ref` normalizes to the
  same value and match it. Hook every path: the bulk PDF import, the single PDF import, and the NRE
  page upload (`nre_order_upload_pdf`). Follow the P4-01 precedent and wrap the call so a matching
  failure can never abort the surrounding import — see `safe_apply_order_type` in
  `modules/rep_traceability/order_type.py` line 122 for the shape.
- **Automatic, on tracker entry arrival.** The 26 NRE sales orders already exist and the operator is
  about to re-enter tracker entries by hand, so the reverse direction matters just as much: when an
  entry is created or its `order_ref` is edited, look for a matching `nre_project` sales order and
  match it. Without this, every entry he types for an existing order would need a manual step.
- **Manual, from the sales-order detail page.** When the order is typed `nre_project`, offer a
  select of unmatched tracker entries and a button to match. This is the operator's explicit request.
- **Manual, from the NRE Projects page.** On an Upcoming row, offer a select of unmatched
  `nre_project` sales orders.

Also provide an **unmatch** action that clears `sales_order_id` and returns the moved files to the
tracker entry, reversing the move symmetrically. Record `nre_tracker.unmatched_sales_order` with the
same metadata shape. Without this, a mistaken match is unrecoverable through the UI.

---

## Task C — Avoid double counting

**File:** `app/eqms/modules/nre_projects/admin.py` and its template

1. The **Upcoming** list shows tracker entries with `sales_order_id IS NULL` only.
2. Matched jobs appear once, as the sales-order row.
3. `nre_invoiced_amount` (`modules/nre_projects/models.py` line 34) stays the basis for
   **Total Amount Invoiced**, computed from sales orders only. Unmatched tracker entries are a
   forecast and must **not** be added into invoiced totals.
4. If you surface a forecast total from unmatched entries, label it distinctly (for example
   `Expected`) and keep it visually and arithmetically separate from invoiced money. Do not blend the
   two into one number.
5. Cancelled orders remain excluded from the dashboard, as P4-03 established.

---

## Task D — Status mapping

The tracker's legacy vocabulary (`INVOICE_STATUSES`, models.py lines 17-23) and the dashboard's
(`NRE_DASHBOARD_STATUSES`, lines 26-31) are different lists. On match, map explicitly:

| Tracker status | Sales order `nre_invoice_status` |
| --- | --- |
| `Pending Invoice` | `Pending Invoice` |
| `50% Invoiced` | `50% Invoiced` |
| `Invoiced` | `100% Invoiced` |
| `Paid` | `Payment Received` |
| `Cancelled` | Leave `nre_invoice_status` alone and set `SalesOrder.status = "cancelled"` instead, reusing the state P4-03 added |

Apply the mapped status **only when the sales order is still at the default `Pending Invoice`**. If
the operator has already advanced the order's status by hand, his value wins and you record the
difference in the match audit metadata rather than overwriting it. Tracker `invoice_status` is
`String(32)` and free text as of P42, so tolerate an unrecognised value: leave the order's status
untouched and note it.

---

## Task E — Surface disagreements

Where a matched entry and its sales order disagree on amount, show both plainly on the NRE page and
on the sales-order detail page — a short neutral line stating the two values. No colour, no icon, no
warning language, and nothing that implies lateness. The operator decides what to do; the system's
job is to stop the difference from being invisible.

Do the same for a status difference recorded per Task D.

---

## Task F — Tests

**File:** new `tests/test_p4_04_nre_tracker_match.py`

Established fixture pattern (no shared `conftest.py`): per-test SQLite file DB via
`monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")`, `create_app()`,
`Base.metadata.create_all`, `application.config["_schema_health_ok"] = True`, permissions / roles /
users seeded inline. `tests/test_p34_tracker_files_ncr.py` shows the tracker file-upload pattern and
`LOCAL_STORAGE_DIR` handling; `tests/test_p4_03b_customer_identity.py` is the most recent model.

Cover at minimum:

1. Manual match from the sales-order page moves every attachment: `OrderPdfAttachment` rows appear
   with `pdf_type="nre_tracker_file"`, the `NRETrackerAttachment` rows are gone, and **the
   `storage_key` values are unchanged**.
2. **Deleting a matched tracker entry afterwards does not remove the files from the sales order** —
   this is the whole point of moving rather than referencing, so assert it directly.
3. Moved files are not deleted when the sales order's PDF is re-imported (they are
   `nre_tracker_file`, not `sales_order_page`).
4. A moved non-PDF file is served with its own `content_type`, not `application/pdf`.
5. Automatic match on sales-order import by normalized order number (`SO 0000290` against `0000290`).
6. Automatic match on tracker entry creation when the sales order already exists.
7. No match is made on customer or amount alone when order numbers differ — assert nothing is
   matched and no file moves.
8. Matching refuses a sales order not typed `nre_project`.
9. Matching an already-matched entry to the same order is idempotent: no duplicate attachments.
10. Amount: null on the order and present on the entry copies across; both present and differing
    changes neither and records the disagreement.
11. Status mapping for all five tracker values, including `Cancelled` setting
    `SalesOrder.status = "cancelled"`, and an unrecognised free-text status leaving the order alone.
12. An operator-advanced order status is not overwritten by the mapping.
13. Matched entries leave the Upcoming list; totals count the job once; an unmatched entry's amount
    is absent from invoiced totals.
14. Unmatch returns the files to the tracker entry and clears `sales_order_id`.
15. A failure inside matching does not abort the surrounding import.
16. Permission and CSRF enforcement on every new route.
17. Update any existing NRE test affected by the Upcoming-list filter or the dashboard totals.
    Preserve intent; do not delete coverage.

---

## Task G — Deploy and completion report

1. Run the full gate and report actual output:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m alembic heads
python -c "import app.wsgi"
```

`alembic heads` must print exactly **one** head, and it must be your new revision chained from
`f8a9b0c1d2e3`. Baseline is 418 passed, 1 skipped. The local Spaces `HeadBucket 403` is pre-existing
and unrelated — and it means **no object-storage behaviour can be validated from a local run**, so
lean on the fact that the blob never moves.

2. Commit and push to `main`. Confirm the migration applied in production, the build, the pre-deploy
   `release.py` step and the health check all succeeded, explicitly — the operator cannot see the
   build banner. State the production alembic head after deploy.

3. Your completion report must contain:
   - the migration revision id and the columns added
   - the single match service function, and every call site that invokes it
   - every audit action name and its metadata keys
   - what the operator sees on the NRE page and on the sales-order detail page
   - confirmation that moved files reuse the existing `storage_key` and that **no Spaces object is
     copied or deleted**
   - confirmation that moved files use `pdf_type="nre_tracker_file"` and therefore survive re-import
   - confirmation that no lateness, aging or overdue logic was added
   - every judgment call, and anything you chose not to do
   - final test totals and deploy status

---

## Out of scope

- All of Purchasing: invoice upload on Upcoming Payments, migration to Invoices Received, PO matching,
  Other Payments, the PO Log reversal, PO open/closed, the PO Log export. (P4-05, P4-06)
- Acting on reconciliation findings: creating missing distributions, running a sync to backfill
  shipments, linking the 2024 distributions. (P4-08)
- Further customer identity work. `Aniq Darr` (`id=608`) is deliberately still address-keyed and the
  operator will name the company himself through the P4-03B interface.
- Retyping the two misclassified NRE orders — `Wiscosin Rapids` (625) and `Aspirus Urology Wausau`
  (614) hold one `nre_project` order each and the operator corrects those by hand.
- Changing `classify_order_type`, the four order-type values, or the P4-01 re-import protections.
- Rebuilding or migrating historical tracker data. There is none.
- Any lateness, aging or overdue feature.
- `_diagnostics_allowed`, permission decorators, `scripts/init_db.py`.
- The auditor portal and the `Auditor Files/` ignore rules.

---

## Reference

| Thing | Where |
| --- | --- |
| `NREProjectEntry`, `NRETrackerAttachment`, `INVOICE_STATUSES`, `NRE_DASHBOARD_STATUSES`, `nre_invoiced_amount` | `modules/nre_projects/models.py` |
| Tracker CRUD, file upload / view / download / delete, `_entry_to_dict`, `_apply_entry_fields` | `modules/nre_projects/admin.py` lines 433-742 |
| NRE dashboard route and totals | `modules/nre_projects/admin.py` lines 53-189 |
| Sales order upload from the NRE page | `modules/nre_projects/admin.py` line 804 |
| `OrderPdfAttachment` | `modules/rep_traceability/models.py` lines 152-168 |
| `normalize_order_number`, `find_sales_order_by_normalized_number` | `modules/rep_traceability/service.py` lines 40 and 56 |
| Never-abort wrapper precedent | `modules/rep_traceability/order_type.py` line 122 |
| Re-import deletion predicate that moved files must avoid | `modules/rep_traceability/admin.py` around lines 2744-2752 and 3419-3427 |
| Sales-order detail page | `templates/admin/sales_orders/detail.html` — PDF Attachments card at lines 133-161 |
| NRE dashboard template and the inline dropdown pattern | `templates/admin/nre_projects/index.html` |

**Conventions**
- `url_for(...)` for every URL, including inside inline JavaScript.
- CSRF token on every state-changing form.
- `record_event` for every state change on a regulated record, with a full metadata snapshot. P4-01
  had to close a gap where tracker mutations recorded nothing and the data became unrecoverable —
  that is precisely why this tracker is empty today. Do not recreate it.
- UI language: short, plain, list-like. No internal document numbers in labels. No self-describing
  subtitles.
- Windows/PowerShell: no `&&` chaining, no bash heredocs, no non-ASCII in script output.
- Postgres is the deploy target. The local SQLite migration chain is broken at a Phase 3 ancestor, so
  never try to prove anything by rebuilding SQLite from scratch; tests build schema with
  `Base.metadata.create_all`.

---

## Acceptance checklist

- [ ] One additive migration, chained from `f8a9b0c1d2e3`, single head; `content_type` and `size_bytes` nullable
- [ ] Attachment view / download honour `content_type`, falling back to PDF when null
- [ ] Moved files use `pdf_type="nre_tracker_file"` and survive a re-import
- [ ] Moved files reuse the existing `storage_key`; **no Spaces object copied or deleted**
- [ ] One match service function; every entry point calls it
- [ ] Automatic match works in both directions — new sales order finds an entry, new entry finds an order
- [ ] Automatic matching keys on normalized order number only; never customer or amount
- [ ] Match failure cannot abort an import
- [ ] Match is idempotent; refuses non-NRE orders and already-matched entries
- [ ] Unmatch reverses the file move symmetrically
- [ ] Deleting a matched tracker entry leaves the sales order's files intact
- [ ] Amount: fallback only when the order has none; disagreements shown, never silently resolved
- [ ] Status mapped per the table; operator-set status never overwritten; `Cancelled` sets the order cancelled
- [ ] Matched entries leave the Upcoming list; each job counted once; forecast money kept separate from invoiced
- [ ] No lateness, aging or overdue logic anywhere
- [ ] All seventeen test areas covered, including permission and CSRF enforcement
- [ ] Full gate run and reported; pushed to `main`; production migration and head confirmed explicitly
