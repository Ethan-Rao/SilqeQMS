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
| D18 | **No lateness logic, ever** | Ethan's customers routinely place sales orders long before they expect delivery, so elapsed time carries no meaning. **No overdue / aging / late / stale features, thresholds, tiles or warning states.** Unmatched cases must be easy to find and act on, nothing more. |
| D19 | Orders that will never ship | Add a **Cancelled** lifecycle state on `SalesOrder.status` (already legal under the existing check constraint, so no migration). Cancelled orders stop being presented as awaiting shipment. |
| D20 | Customer merge behaviour | **Merge on best guess.** Identity at company level ignores division and corporate suffix: Advanced Bionics GmbH, Advanced Bionics and AB are one customer, and all their sales orders belong to it. Show what moves; the operator confirms. |
| D21 | Merge safety sequencing | Customer identity rule changes and merging are split out of P4-03 into **P4-03B**, so UI work and identity work never land in the same deploy. Identity changes are the single most dangerous thing in this phase for regulated customer data. |
| D22 | Secrets never move to a workstation | ShipStation credentials live only on App Platform. When a diagnostic needs them, it runs **server-side** behind the existing admin page — the operator is never asked to paste a secret into a chat or edit `.env`. Applies to any future credentialed diagnostic. |
| D17 | Where the imports live | Sales Order PDF import and Distribution CSV import move to an `Imports` card at the top of Admin Tools. `/admin/distribution-log/import` becomes packing slips only. Old import URLs stay alive as redirects. |

---

## 3. Prompt sequence

| Prompt | Scope | Status |
| --- | --- | --- |
| **P4-01** | Explicit order type on `SalesOrder`; classification service with auto-maintenance and manual override; backfill of existing orders; order-type dropdown replaces the Source column on the Sales Orders list; NRE dashboard driven by order type; re-import no longer destroys packing slips or repoints customers; NRE tracker audit-history investigation and audit-metadata gap closed | **Complete** |
| **P4-02** | Navigation and information architecture: move Sales Order PDF import to the top of Admin Tools, move distribution CSV import to Admin Tools, reduce the distribution import page to packing slips only. Plus a read-only reconciliation report sizing P4-03 and P4-08 | **Complete** |
| **P4-03** | Sales Order detail page as the control surface: reassign the matched customer with distributions following, link and unlink distributions (including across an order-number mismatch), Cancelled state, live Type dropdown, read-only ShipStation probe of the 26 unmatched catheter orders | **Complete** |
| **P4-03B** | Customer identity: order-type-driven keying at import (retires the line-less-equals-catheter rule), GmbH suffix normalisation, re-key facility-keyed NRE customers to company identity, merge on best guess with a preview, plus the server-side ShipStation probe (D8, D20, D21, D22) | **Complete** |
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
- **Coordinator verification:** local suite **394 passed, 1 skipped** (matches the report); single
  alembic head; `admin/sales_orders/import.html` deleted with no remaining code reference (only
  archived planning docs mention it); Imports card present at `diagnostics.html` line 16,
  immediately after the header card and above System Status, CSRF token on both forms.
  **P4-02 verified.**

### Coordinator data probe — 2026-08-10 (read-only, production)

Run directly by the coordinator to close gaps the P4-02 report left open. Temporary scripts were
deleted after use; nothing was written.

**The 35 unmatched distributions are mostly benign.**
- 31 are 2024 shipments (`SO 0000102`–`SO 0000145`) and only **one** 2024 sales order exists, so
  those PDFs were never imported. Ethan has confirmed pre-2025 mismatches are not a concern.
- 3 are Harbor-UCLA shipments dated 2026-08-10; they resolve when those PDFs are imported.
- 1 is a genuine mismatch: distribution `id=760`, 2025-03-19, `SO 0000164`, VAMC Loma Linda, against
  sales order `0000165` dated 2025-03-18 for the same customer. Off-by-one order number.
- Also noted: distribution `id=753` (2025-02-21, `SO 0000145`) reuses an order number whose original
  shipment was `id=887` on 2024-12-27.

**The 26 in-process orders are the real finding.** All 2025 or later, all with genuine catheter line
items, **zero duplicate sales orders**, and **no distribution anywhere in the system shares any of
their order numbers** — so the distribution rows do not exist at all. Only four are recent (Jul–Aug
2026). Ethan has confirmed some are covered by manual deliveries he has yet to upload. P4-03 Task E
probes ShipStation read-only to separate sync gaps from genuinely unshipped orders.

**Customer identity is worse than the P4-02 report suggested** — it found 3 only because it filtered
on `customer_type == 'catheter'`.
- 104 customers: 91 `catheter`, 13 `auto`, **0 `nre`**.
- 18 customers hold at least one `nre_project` order and **17 of the 18 carry address-derived or
  hybrid keys** instead of company-name keys. Only `Fearsome Limited` (`FEARSOMELIMITED`) is right.
- **Advanced Bionics exists twice:** `id=530` named `AB` (3 NRE orders, key
  `30625HANNOVER|CA|91355`) and `id=764` `Advanced Bionics Gmbh` (1 NRE order, key
  `ADVANCEDBIONICSGMBH|30625HANNOVER`). Both keys carry the Hannover postcode. Per D20 they are one
  customer.
- `normalize_facility_name` strips Inc/LLC/Corp/Ltd/Co/PC/PA/PLLC/LP/LLP but **not GmbH**, which is
  why the two AB rows never collided. **"AB" must never be added as a strippable suffix** — here it
  is Ethan's abbreviation for Advanced Bionics, not a Swedish corporate form.
- `Aniq Darr` (`id=608`) is a person's name used as a customer; its company name needs operator
  input, so the re-key UI must allow editing the surviving name.
- Two `nre_project` orders almost certainly belong to real catheter facilities and are
  misclassifications inside the needs-review set: `Wiscosin Rapids` (`id=625`, 7 orders / 6
  distributions) and `Aspirus Urology Wausau` (`id=614`, 10 / 9). Ethan can retype these once P4-03
  puts the Type dropdown on the detail page.
- 5 catheter customers share a canonical name with another row (Aspirus Rhinelander Urology, Health
  Products For You, Santa Clara Valley Medical Center, Temple University Health System, University
  of Michigan). Facility-level identity is intentional for catheter, so **do not auto-merge these**.
  Health Products For You is worth a look: `id=620` holds 31 orders / 18 distributions, `id=741`
  holds 0 / 1.

**Root cause confirmed.** `_is_catheter_order` still documents "If order has NO lines at all ->
assume catheter (True) — parse error, not NRE", which D6 refuted. It drives
`_find_or_create_customer_for_order_data`, so every line-less NRE order took the facility-keying
path with `customer_type="catheter"`. That is exactly how Advanced Bionics GmbH acquired a facility
key. Fixed in P4-03B.

### P4-03 - Sales-order detail control surface
- **Issued:** 2026-08-10
- **File:** `PHASE4_DEV_AGENT_PROMPT_03_ORDER_CONTROL_SURFACE.md`
- **Chains from:** `f8a9b0c1d2e3` (no migration; `cancelled` is already legal under
  `ck_sales_orders_status`)
- **Report received:** 2026-08-10 (dev agent completion)
- **Deploy status:** green — no migration; push `ac6e41d`; `/health` ok
- **Gate:** **406 passed, 1 skipped**; alembic head still `f8a9b0c1d2e3`
- **Coordinator verification:** local suite **406 passed, 1 skipped** (matches); single alembic head;
  commits `ac6e41d` and `9fd54be` present. The dev agent's own catch is the notable item: the session
  runs `autoflush=False`, so `classify_order_type` queried the database before the pending link or
  unlink was visible and silently computed the wrong type. `safe_apply_order_type` now flushes first
  (`order_type.py` lines 129-131). Without it every link and unlink would have appeared to do
  nothing. **P4-03 verified.**
- **Open item — resolved differently than the dev agent proposed.** The ShipStation probe listed all
  26 in-process orders from the production database but could not reach the API: the credentials
  live only on App Platform, and the agent asked for them to be pasted into chat or written into
  local `.env`. **Declined** per D22. `doctl` is not installed locally, so P4-03B Task E moves the
  probe server-side behind the existing ShipStation admin page, where the credentials already are.

### P4-03B - Customer identity
- **Issued:** 2026-08-10
- **File:** `PHASE4_DEV_AGENT_PROMPT_03B_CUSTOMER_IDENTITY.md`
- **Chains from:** `f8a9b0c1d2e3` (no migration; `customer_type` is unconstrained `Text`)
- **Report received:** 2026-08-10 (dev agent completion)
- **Deploy status:** green — no migration; `/health` ok after push
- **Gate:** **418 passed, 1 skipped**; alembic head still `f8a9b0c1d2e3`
- **Highest-risk item of the phase:** the merge touches four foreign keys with mixed delete
  behaviour — `sales_orders` is `RESTRICT`, `customer_notes` and `customer_reps` are `CASCADE`. A
  merge that deletes before moving would silently destroy notes and rep assignments, so the prompt
  specifies the order of operations and requires tests proving both survive.
- **ShipStation probe:** `/admin/shipstation/probe-in-process` (permission `shipstation.run`);
  operator opens once on production to see the three-bucket summary (credentials stay on App Platform).

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
