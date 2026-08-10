# Phase 4 Plan and Progress Log

Coordinator working document. Tracks the agreed Phase 4 scope, the prompt sequence, frozen
decisions, and status. Updated after every dev-agent round trip.

**Phase goal:** a systematic overhaul of the sales order, invoice, NRE and purchasing
workflow, informed by several months of using the current version in production.

**Alembic head at phase start:** `e7f8a9b0c1d2`
**Current Alembic head:** `f8a9b0c1d2e3` (P4-01)
**Test baseline at phase start:** 375 passed, 1 skipped (verified locally 2026-08-10)
**Current test baseline:** 387 passed, 1 skipped (verified locally after P4-01)

---

## 1. Why this phase exists (findings from the initial system review)

The commercial half of the platform works, but the sales order to invoice chain has four
structural defects that cause real data damage:

1. **Catheter vs NRE is inferred, three times, by three different rules that disagree.**
   Import-time classification (`_is_catheter_order`) treats an order with no parsed line
   items as a *catheter* order. Dashboard-time classification (`_nre_customers`) treats a
   customer with orders, no matched distribution and no catheter-SKU lines as *NRE*. Because
   NRE sales-order PDFs are free text and contain no parseable line items, every NRE order
   imports as a catheter order with `customer_type = "catheter"`, and the NRE dashboard
   excludes `"catheter"` unconditionally. **This is the root cause of the NRE dashboard
   going empty after the most recent import.**

2. **Re-importing a sales-order PDF silently repoints the customer.** The re-import path
   overwrites `customer_id` unconditionally. When the recomputed Ship-To facility key does
   not match the existing (name-keyed) NRE customer, a new catheter customer is created and
   the order moves to it, leaving the original customer with zero orders. The NRE dashboard
   only lists customers holding at least one order, so previously-correct NRE customers
   dropped off as well. This is the second half of the same incident.

3. **Re-importing a sales-order PDF destroys packing slips.** Both import paths delete every
   `OrderPdfAttachment` matching `sales_order_id`, and packing slips carry both
   `sales_order_id` and `distribution_entry_id`. The database row and the Spaces blob are
   both deleted. Packing slips are device-traceability evidence.

4. **Money lives in disconnected ledgers with no reconciliation.** `PaymentEntry`,
   `InvoiceReceivedEntry`, `NREProjectEntry` and `SalesOrder.nre_invoice_status` do not derive
   from one another. The NRE dashboard and the Weekly Brief compute NRE totals from
   *different* ledgers and can disagree silently.

Secondary issues carried into the plan: `_find_sales_order_by_number` loads every sales order
into memory on each normalized lookup; the ShipStation `skipped` counter conflates normal
idempotency with dropped shipments; the sales dashboard keys customers by *name* when
`customer_id` is absent while catheter identity is *address*-based, inflating the first-time
customer count; NRE tracker audit events carry no row snapshot, so deleted entries are not
recoverable.

---

## 2. Frozen decisions (do not re-ask)

Confirmed by Ethan. Carry these into every prompt.

| # | Topic | Decision |
| --- | --- | --- |
| D1 | Can a customer be both catheter and NRE? | **No.** A customer is always one or the other. Classification nonetheless moves to the *order*, because that is where the evidence lives. |
| D2 | Which NRE money ledger is authoritative today? | **Neither.** Both `SalesOrder.nre_invoice_status` and `NREProjectEntry` are open for redesign; nothing needs to be preserved for its own sake. |
| D3 | Packing-slip deletion bug | Fix it inside the sales-order work rather than as a standalone prompt. Landed in P4-01. |
| D4 | Is the order-type dropdown live or a static label? | **Live.** The system keeps it current automatically and Ethan can always override; a manual override is never overwritten by automation. |
| D5 | Default order type on import | **Best guess, flagged for review when not confident.** |
| D6 | Do NRE sales-order PDFs contain line items? | **No** - mostly free text, no line-item table. Zero parsed lines is the *normal* state for an NRE order, not a parse failure. |
| D7 | Backfill of the 218 existing orders | **Infer a type for all of them**; Ethan corrects what is wrong. |
| D8 | Customer identity when an order becomes NRE | **Preview and confirm** before re-keying a customer from facility to company identity. Deferred to P4-03. |
| D9 | NRE dashboard default date range | **Keep the current calendar quarter.** Additionally show a count of NRE orders falling outside the range so an empty result is never mistaken for missing data. |
| D10 | Wiped Invoice Tracker entries | **Closed.** Confirmed unrecoverable — all 15 historical tracker audit events carry empty metadata, and no orphan attachments survive. Ethan will re-enter the tracker manually. The audit gap is closed in P4-01 so this cannot recur. No restoration work is planned. |
| D11 | Order type values | Stored: `cleartract_distribution`, `cleartract_in_process`, `cleartract_delivery`, `nre_project`. Labels: "ClearTract Distribution", "ClearTract In Process Order", "ClearTract Delivery", "NRE Project". |
| D12 | Classification rule | Linked ShipStation distribution wins, then any other linked distribution, then catheter-SKU lines, then NRE by absence of evidence (flagged for review). |
| D13 | `customer_type` column | Stays in the schema, but stops being the classification mechanism. Not dropped in this phase. |
| D14 | New permissions | None needed for the order-type work; `sales_orders.view` / `sales_orders.edit` already cover it. |
| D15 | Existing data reconciliation | Ethan wants existing sales orders **and distributions** brought into agreement with the corrected model once the feature prompts land. Scoped as **P4-08**, sized by the read-only report in P4-02 Task D. |
| D16 | Operator site checks | Ethan wants only a couple of checks this phase. The coordinator verifies locally (tests, migration chain, code inspection, production `/health`) and advises explicitly when a check is worth his time. |
| D17 | Where the imports live | Sales Order PDF import and Distribution CSV import move to an `Imports` card at the top of Admin Tools. `/admin/distribution-log/import` becomes packing slips only. Old import URLs stay alive as redirects. |

---

## 3. Prompt sequence

| Prompt | Scope | Status |
| --- | --- | --- |
| **P4-01** | Explicit order type on `SalesOrder`; classification service with auto-maintenance and manual override; backfill of existing orders; order-type dropdown replaces the Source column on the Sales Orders list; NRE dashboard driven by order type; re-import no longer destroys packing slips or repoints customers; NRE tracker audit-history investigation and audit-metadata gap closed | **Complete** |
| **P4-02** | Navigation and information architecture: move Sales Order PDF import to the top of Admin Tools, move distribution CSV import to Admin Tools, reduce the distribution import page to packing slips only. Plus a read-only reconciliation report sizing P4-03 and P4-08 | **Complete** |
| **P4-03** | Sales Order detail page as the control surface: edit the matched customer and matched distributions with the rest of the system updating accordingly; customer re-key preview and confirm (D8) | Planned |
| **P4-04** | NRE tracker integration: match a sales order to an existing Invoice Tracker entry, auto-pair files previously uploaded to that tracker entry onto the new sales order, unify tracker and dashboard so NRE totals come from one place (D2) | Planned |
| **P4-05** | Purchasing part 1: invoice upload on Upcoming Payments, automatic migration of the entry to Invoices Received, PO matching field on Invoices Received with file pairing to the PO, "Other Payments" archive section for entries with no PO | Planned |
| **P4-06** | Purchasing part 2 - PO Log reversal: the system becomes the source of truth, uploaded PO PDFs populate details, open/closed selection, no reason-for-change on PO detail, "document as closed" action, Export PO Log, reference files on historical POs | Planned |
| **P4-07** | Residual seams: sales-dashboard customer keying, ShipStation skipped-counter clarity | Planned |
| **P4-08** | Existing-data reconciliation (D15): link linkable unmatched distributions, re-key customers left facility-keyed by the old classification bug, retire empty customer shells. Dry-run first, Ethan approves the numbers before anything is written | Planned |
| **P4-09** | DC.SLQ002 design and validation traceability for the phase | Planned |

Prompts are issued one at a time. The next prompt is not composed until the dev agent's
completion report for the previous one has been reviewed.

---

## 4. Round-trip log

### P4-01 - Order type and NRE classification fix
- **Issued:** 2026-08-10
- **File:** `PHASE4_DEV_AGENT_PROMPT_01_ORDER_TYPE.md`
- **Chains from:** `e7f8a9b0c1d2`
- **Report received:** 2026-08-10 (dev agent completion)
- **Deploy status:** green — alembic head `f8a9b0c1d2e3` live; `/health` ok; backfill executed
- **Follow-ups raised:** NRE tracker values not recoverable (deletes had empty metadata); gap closed going forward
- **Coordinator verification (independent of the dev agent's report):** `git log` shows both
  commits; `alembic heads` prints the single head `f8a9b0c1d2e3`; the migration is additive with
  `down_revision = "e7f8a9b0c1d2"` and both booleans carry server defaults; local suite
  re-run gives **387 passed, 1 skipped**; production `https://silqeqms.com/health` returns
  `200 {"ok":true}`; all seven `safe_apply_order_type` hook sites present; both import paths
  narrow attachment deletion to `pdf_type == "sales_order_page"` **and**
  `distribution_entry_id IS NULL`; both paths record
  `sales_order.customer_mismatch_on_reimport` instead of repointing; `_find_sales_order_by_number`
  now delegates to the service helper. **P4-01 verified.**
- **Backfill result:** 218 orders - 166 `cleartract_distribution`, 26 `cleartract_in_process`,
  26 `nre_project`, 0 `cleartract_delivery`; 26 flagged needs-review; no `customer_type == "nre"`
  disagreements.
- **Signal to follow up:** the 26 `cleartract_in_process` orders are catheter orders with **no
  linked distribution**. Some are genuinely awaiting shipment; others are the silent
  matching failures described in section 1. P4-02 Task D quantifies the split, and P4-08 acts on it.

### P4-02 - Import relocation and reconciliation report
- **Issued:** 2026-08-10
- **File:** `PHASE4_DEV_AGENT_PROMPT_02_IMPORT_RELOCATION.md`
- **Chains from:** `f8a9b0c1d2e3` (no migration in this change set)
- **Report received:** 2026-08-10 (dev agent completion)
- **Deploy status:** green — no migration; `/health` ok after push
- **Follow-ups raised:** reconciliation numbers size P4-03 / P4-08 (see completion report)

---

## 5. Open questions for Ethan (not yet needed)

Raise these when the relevant prompt comes up, not before.

- P4-04: should an NRE invoice amount live on the sales order, on the tracker entry, or in one
  merged record? D2 says neither current ledger is sacred, so this is a clean design choice.
- P4-05: when an invoice is uploaded against an Upcoming Payment, should the payment row
  disappear from Upcoming Payments entirely or remain visible with a received marker? The
  Weekly Brief currently merges both tables and flags received rows.
- P4-06: which columns must the exported PO Log contain, and must the export match the current
  `SILQ PO Log.xlsx` layout exactly, or is a clean equivalent acceptable?
- P4-07: are the first-time vs repeat customer counts on the sales dashboard something Ethan
  relies on? They are currently unreliable when unmatched distributions exist.

---

## 6. Standing constraints

- Deploy is push to `main`; DigitalOcean runs `python scripts/release.py` pre-deploy. No CI.
- The dev agent owns the entire mechanical pipeline: code, tests, migrations, commits, pushes,
  and running data scripts (dry-run first, then `--execute`). Ethan performs no code-level
  actions.
- One migration per change set, `down_revision` set to the current single head. Additive only.
- Local SQLite migration chain is broken at a Phase 3 ancestor. Postgres only.
- Local `.env` Spaces credentials are stale (confirmed: `HeadBucket` returns 403). Any
  storage-backed script must verify credentials before its result is trusted.
- Windows/PowerShell: no `&&`, no bash heredocs, no non-ASCII in script output.
