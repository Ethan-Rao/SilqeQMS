# Prompt P4-03B — Customer identity: fix the keying rule, then re-key and merge

## Context

You are the Phase 4 Dev Agent for the Silq eQMS platform (Flask + SQLAlchemy modular monolith,
DigitalOcean App Platform, Postgres, Spaces). You own the entire mechanical pipeline: code, tests,
the local gate, commit, push, and running scripts. **The operator is not a coder and performs no
code-level actions.** Never ask him to run, commit, execute, or edit anything — including
environment files. If you need a credential you do not have, see Task E; do not ask for it.

Deployment is push to `main`. DigitalOcean builds, runs `python scripts/release.py` pre-deploy, then
rolls the component. **There is no CI** — the local gate is the only thing between your commit and
production.

**Current Alembic head: `f8a9b0c1d2e3`.** This change set needs **no migration**: it changes data
and behaviour, not schema. `Customer.customer_type` is plain `Text` with no check constraint, so
storing `"nre"` is already legal.

**Baseline gate: 406 passed, 1 skipped.**

### Why this work exists

This is the change set P4-03 deliberately deferred, because customer identity is the most dangerous
thing in this phase to get wrong. Here is the confirmed production picture, gathered read-only:

- **104 customers: 91 `catheter`, 13 `auto`, and zero `nre`.** The NRE customer type has never once
  been assigned.
- **18 customers hold at least one `nre_project` order, and 17 of them are keyed by street address
  or an address hybrid** instead of by company name. Only `Fearsome Limited` (`FEARSOMELIMITED`) is
  keyed correctly. So Boston Scientific, AbbVie, New World Medical and a dozen others will each
  fork into a second customer record the moment an order arrives from a different address.
- **Advanced Bionics already forked.** `id=530` is named `AB` with 3 NRE orders and key
  `30625HANNOVER|CA|91355`; `id=764` is `Advanced Bionics Gmbh` with 1 NRE order and key
  `ADVANCEDBIONICSGMBH|30625HANNOVER`. Both keys carry the Hannover postcode. They are one company.

**Root cause.** `_is_catheter_order` in `modules/rep_traceability/admin.py` line 248 delegates to
`order_data_is_catheter`, and its rule is:

> "If order has NO lines at all -> assume catheter (True) — parse error, not NRE"

That assumption is wrong and the operator has confirmed it: **NRE sales-order PDFs are mostly free
text with no line-item table, so zero parsed lines is the normal state for an NRE order.** Because
`_find_or_create_customer_for_order_data` (line 260) branches on that function, every line-less NRE
order took the catheter path — facility keying by ship-to address, and `customer_type="catheter"`.
That is precisely how Advanced Bionics GmbH ended up with a facility key.

P4-01 fixed the *order* classification and left this deliberately. Now fix it, then repair the data.

---

## Decisions (do not re-ask)

| Topic | Decision |
| --- | --- |
| Company-level identity | Ignores division and corporate suffix. Advanced Bionics GmbH, Advanced Bionics and AB are **one customer**, and all of their sales orders belong to it. A different division at a different address is not a new customer. |
| Merge policy | **Merge on best guess.** Do not demand confirmation for the unambiguous cases. Guard only the ambiguous ones — see Task D. |
| Catheter identity | Unchanged. Facility-level (ship-to address) keying for catheter customers is intentional and correct. |
| The five catheter name clusters | **Leave alone.** Aspirus Rhinelander Urology, Health Products For You, Santa Clara Valley Medical Center, Temple University Health System and University of Michigan each have two rows sharing a canonical name. Those are distinct facilities within a system and facility-level identity is deliberate. Do not merge them. |
| `"AB"` as a corporate suffix | **Never.** `AB` is a Swedish corporate form, but here it is the operator's abbreviation for Advanced Bionics. Adding it to the suffix-stripping list would corrupt real names. Do not add it. |
| Scope of suffix work | Add `GmbH` and its common tails only. Do not speculatively add every international suffix; exactly one non-US-suffixed customer exists in the whole database. |
| No lateness logic | Standing rule from P4-03: **no overdue / aging / late / stale features anywhere**, no thresholds, no warning states. The operator's customers place orders long before they expect delivery. |
| Retroactive behaviour | The import-rule fix in Task A applies to **future** imports only. Existing rows are repaired by the explicit backfill in Task D, never by a silent side effect. |

---

## Task A — Drive customer identity from the order, not from a bad assumption

**Files:** `app/eqms/modules/rep_traceability/service.py`,
`app/eqms/modules/rep_traceability/admin.py`

1. Correct `order_data_is_catheter` so that **an order with no parsed lines is not catheter**. The
   rule becomes: catheter if and only if at least one line carries a SKU in `CATHETER_SKUS`. Update
   the docstring, which currently states the opposite reasoning explicitly.
2. Audit every caller before you change it and state in your report what each one does now:
   - `_is_catheter_order` (`admin.py` line 248)
   - `_find_or_create_customer_for_order_data` (line 260) — the identity decision
   - `_note_catheter_no_dist` (lines 2526 and 3285) — this currently warns "catheter order with no
     distribution" for line-less NRE orders, which is noise the fix removes
   - any other caller you find; search, do not assume this list is complete
3. In `_find_or_create_customer_for_order_data`, make the branch explicit:
   - catheter → `identity="facility"`, `customer_type="catheter"` (unchanged behaviour)
   - otherwise → `identity="company"`, and **pass `customer_type="nre"`**. It currently passes no
     `customer_type` at all, which is why zero customers have ever been typed `nre`.
4. Keep `_is_catheter_order` as a thin named wrapper if it aids readability, but there must be
   exactly one rule implementation. Two disagreeing classifiers is the defect P4-01 was created to
   remove; do not reintroduce it.
5. This changes behaviour for the operator's **next** import. Do not backfill from here, and do not
   touch existing customer rows in this task.

---

## Task B — Corporate suffix normalisation

**File:** `app/eqms/modules/customer_profiles/utils.py`

1. `normalize_facility_name` (line 6) strips Inc, LLC, Corp, Corporation, Ltd, Limited, Co, Company,
   PC, PA, PLLC, LP and LLP. **Add `GmbH`**, plus the common tails `mbH` and `GmbH & Co. KG` /
   `GmbH und Co KG` (tolerate the ampersand, the word "und", and missing periods). Case-insensitive,
   trailing position only, consistent with the existing patterns.
2. **Do not add `AB`.** See the decisions table.
3. Confirm in your report whether `normalize_facility_name` feeds anything user-visible or only
   key computation. Its docstring claims key computation via `canonical_customer_key`, but verify by
   searching for callers — if it also drives a display name anywhere, say so rather than changing
   what the operator sees.
4. Add unit tests proving `Advanced Bionics Gmbh`, `Advanced Bionics GmbH & Co. KG` and
   `Advanced Bionics` all produce the canonical key `ADVANCEDBIONICS`, and that a name ending in
   `AB` is left intact.

---

## Task C — Re-key and merge tool on the customer page

**Files:** `app/eqms/modules/customer_profiles/` (service + admin),
`app/eqms/templates/admin/customers/detail.html`

Give the operator a way to convert a customer to company-level identity, merging into an existing
company record when one already holds that key.

### C1. Preview

Route `GET` or `POST` producing a preview, permission `customers.edit` (use whatever the module
already requires for customer mutation — check and match, do not invent a permission or touch
`scripts/init_db.py`). The preview must state:

- the computed company-level key from the customer's name
- whether another customer already holds that key, and if so which (id and name) — that is the
  merge target
- exact counts of what would move: sales orders, distribution entries, customer notes, rep
  assignments
- the surviving display name, **editable by the operator** before applying. `Aniq Darr` (`id=608`)
  is a person's name standing in for a company, so the operator must be able to correct it here.
- the resulting `customer_type`

### C2. Apply

A single transaction. **These four foreign keys point at `customers.id` and they do not behave the
same way — getting this wrong destroys data:**

| Table | Column | On delete | Consequence |
| --- | --- | --- | --- |
| `sales_orders` | `customer_id` | **RESTRICT**, NOT NULL | You cannot delete the losing customer until every sales order is repointed |
| `distribution_log_entries` | `customer_id` | SET NULL, nullable | Repoint explicitly; letting it null out loses the link |
| `customer_notes` | `customer_id` | **CASCADE**, NOT NULL | **Notes are silently destroyed** if you delete before moving them |
| `customer_reps` | `customer_id` | **CASCADE**, NOT NULL | **Rep assignments are silently destroyed** if you delete before moving them |

Search for any further reference to `customers.id` before you write this and report what you find;
the four above are what I located, but confirm rather than trust.

Order of operations:

1. Repoint sales orders, distributions, notes and rep assignments from the loser to the survivor.
2. When moving rep assignments, **de-duplicate** — if both customers reference the same rep you will
   otherwise violate the `customer_reps` uniqueness. Drop the redundant row rather than failing.
3. Set the survivor's `company_key` to the new company-level key, `customer_type` to `"nre"`, and
   `facility_name` to the operator's chosen name.
4. `company_key` is **`unique=True`** (`customer_profiles/models.py` line 55). The loser's key must
   be released in the same transaction as the survivor's key change, so never leave two rows
   holding the same value even transiently. Delete the loser last.
5. Record one audit event, `customer.rekeyed_merged`, whose metadata carries: both customer ids and
   names, both before-keys, the after-key, the moved counts per table, and the chosen surviving
   name. P4-01 had to close a gap where deletions recorded no metadata and the data became
   unrecoverable — this event is the only record that the losing row ever existed, so make it
   complete.
6. Pick the survivor as the customer with the most linked records (sales orders plus distributions).
   For Advanced Bionics that is `id=530`. Default the proposed surviving name to the most complete
   candidate name rather than the shortest, so `AB` does not win over `Advanced Bionics Gmbh`.

### C3. UI

On the customer detail page, a plainly-labelled action that opens the preview and then applies.
Short, list-like language. No self-describing subtitles. Do not add any warning or badge implying a
customer is wrong or stale — offer the action, nothing more.

---

## Task D — Backfill: repair the existing customers

**File:** new `scripts/backfill_customer_identity.py`

Dry-run by default, `--execute` to apply, following the established pattern in
`scripts/_remediate_customer_profiles.py` and `scripts/backfill_order_types.py`. Reuse the Task C
service function — do not write a second merge implementation.

### Selection rule

A customer is a re-key candidate when **all** of these hold:

- it has at least one sales order, and **every** one of its sales orders is typed `nre_project`
- it has **zero** linked distribution entries
- its `company_key` is not already a pure name-derived key (i.e. it differs from
  `canonical_customer_key(facility_name)`)

The distribution condition matters. `Wiscosin Rapids` (`id=625`, 7 sales orders / 6 distributions)
and `Aspirus Urology Wausau` (`id=614`, 10 / 9) each have one order typed `nre_project`, but they
are obviously real catheter facilities and that order is a misclassification inside the 26
needs-review set. **They must not be re-keyed.** The rule above excludes them; verify that it does
and report the exclusion explicitly.

### Ambiguity guard

Apply automatically when the name looks like a company. **Hold, and list for the operator, when the
name looks like a person** — no corporate suffix, no company-ish token, and a first-name/last-name
shape. `Aniq Darr` (`id=608`) is the known case. Report held rows with their orders so the operator
can supply a company name through the Task C UI. State your heuristic plainly in the report; a
crude, transparent rule the operator can audit beats a clever one he cannot.

### Output

ASCII only — non-ASCII has crashed scripts mid-run under PowerShell with `UnicodeEncodeError`. For
every candidate print: id, current name, current key, proposed key, merge target if any, and the
per-table move counts. Summarise re-keyed, merged, held, and skipped counts.

Run dry-run first and paste the output. Then run `--execute` and paste that too, followed by a
verification pass showing the resulting `customer_type` distribution and confirming no customer with
an `nre_project` order still holds an address-derived key.

---

## Task E — Run the ShipStation probe where the credentials already live

The P4-03 probe script could not complete: `SHIPSTATION_API_KEY` and `SHIPSTATION_API_SECRET` exist
only on App Platform. **Do not ask the operator to paste secrets into a chat or edit `.env`** — he
performs no code-level actions, and moving live credentials onto a workstation is not an acceptable
answer. Instead, run the probe where the credentials already are.

**File:** `app/eqms/modules/shipstation_sync/admin.py` and its template

1. Add a read-only probe to the existing ShipStation admin page (`/admin/shipstation`,
   `shipstation_index`, template `admin/shipstation/index.html`). Permission: match the existing
   `shipstation.run`, since it calls the external API. Do not create a new permission.
2. It selects every sales order typed `cleartract_in_process`, queries ShipStation read-only for
   each order number using the existing client and credential handling in this module (there is
   already a credentials-present check at lines 81-82 and an error path at line 213 — follow those
   patterns), and renders a table plus a three-bucket summary:
   - a ShipStation order exists **with** at least one shipment → **the distribution record should
     exist in our log and does not**
   - a ShipStation order exists with **no** shipment → consistent with not yet shipped
   - **no** ShipStation order → consistent with a manual delivery the operator has not uploaded yet,
     or an order placed well ahead of fulfilment
3. Absolute constraints: **no writes, no `run_sync` call, no distribution creation, no sync-run
   row.** If credentials are absent or the API errors, report it per order and keep going.
4. Per-order output: order number, order date, customer, ShipStation order found, its status,
   shipment count, tracking numbers.
5. Keep the P4-03 script `scripts/_probe_shipstation_for_in_process.py`, but have it print a clear
   pointer to this page when the environment variables are absent, so the dead end is
   self-documenting.
6. **Report the rendered result.** Run the probe against production yourself if you can reach the
   page with an authenticated session; if you cannot, say so plainly and state that the operator
   needs to open the page once. Do not silently leave it unanswered.

---

## Task F — Tests

**File:** new `tests/test_p4_03b_customer_identity.py`, plus additions where noted

Follow the established fixture pattern (no shared `conftest.py`): per-test SQLite file DB via
`monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'test.db'}")`, `create_app()`,
`Base.metadata.create_all`, `application.config["_schema_health_ok"] = True`, permissions / roles /
users seeded inline.

Cover at minimum:

1. An order with **no lines** is no longer treated as catheter, and its customer is created with
   `identity="company"` and `customer_type="nre"`.
2. An order with a catheter SKU still produces a facility-keyed `customer_type="catheter"` customer.
3. An order with lines but no catheter SKU produces a company-keyed NRE customer.
4. `_note_catheter_no_dist` no longer fires for a line-less order.
5. The suffix tests from Task B4.
6. Merge moves sales orders, distributions, notes and rep assignments, then deletes the loser —
   assert **notes and rep assignments survive**, since CASCADE would destroy them if ordered wrongly.
7. Merge de-duplicates a rep assignment held by both customers without raising.
8. Merge does not leave two customers holding the same `company_key`, and does not fail the
   `RESTRICT` constraint on `sales_orders`.
9. Re-key without a merge target updates the key and type in place.
10. The audit event carries both ids, both before-keys, the after-key and the moved counts.
11. Backfill selection: a customer with distributions and one NRE-typed order is **excluded**
    (the Wisconsin Rapids / Aspirus Wausau shape).
12. Backfill ambiguity guard: a person-shaped name is held, not auto-merged.
13. Backfill dry-run writes nothing.
14. Permission and CSRF enforcement on every new route.
15. The ShipStation probe performs no writes — assert no `ShipStationSyncRun` row and no
    distribution is created, with the API layer stubbed.

---

## Task G — Deploy and completion report

1. Run the full gate and report actual output:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m alembic heads
python -c "import app.wsgi"
```

`alembic heads` must print exactly one head, still `f8a9b0c1d2e3`. Baseline is 406 passed, 1
skipped. The local `HeadBucket 403` from stale Spaces credentials is pre-existing and unrelated; no
storage-dependent result from a local run can be trusted.

2. Commit and push to `main`. Confirm the build, the pre-deploy `release.py` step and the health
   check succeeded, explicitly — the operator cannot see the build banner.

3. Run the Task D backfill dry-run, then `--execute`, then the verification pass. Paste all three.

4. Your completion report must contain:
   - every caller of `order_data_is_catheter` and what each does after the change
   - whether `normalize_facility_name` affects anything user-visible
   - the complete list of tables carrying a `customers.id` foreign key that you found
   - the full backfill dry-run, execute, and verification output
   - which customers were re-keyed, which were merged into which, and which were **held** as
     ambiguous with the reason
   - explicit confirmation that Wisconsin Rapids and Aspirus Urology Wausau were excluded
   - explicit confirmation the five catheter name clusters were untouched
   - the ShipStation probe result, or a clear statement of what the operator must click
   - every judgment call, and anything you chose not to do
   - final test totals and deploy status

---

## Out of scope

- The NRE Invoice Tracker: pairing entries or files to sales orders. (P4-04)
- All of Purchasing: invoice upload, Invoices Received, PO matching, Other Payments, the PO Log
  reversal, PO open/closed, the PO Log export. (P4-05, P4-06)
- Linking distributions, creating missing distribution rows, or running a sync to backfill
  shipments. (P4-08, and only after the probe result is understood)
- Merging the five catheter name clusters, or any change to facility-level keying.
- Retyping the two misclassified NRE orders — the operator does that himself through the P4-03 Type
  dropdown.
- Changing `classify_order_type`, the four order-type values, or anything P4-03 delivered.
- Any lateness, aging or overdue feature.
- `_diagnostics_allowed`, permission decorators, `scripts/init_db.py`.
- The auditor portal and the `Auditor Files/` ignore rules.

---

## Reference

**Known production rows** (read-only probe, 2026-08-10)

| Customer | id | type | NRE orders | Distributions | Key | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| `AB` | 530 | auto | 3 | 0 | `30625HANNOVER\|CA\|91355` | Merge survivor for Advanced Bionics |
| `Advanced Bionics Gmbh` | 764 | catheter | 1 | 0 | `ADVANCEDBIONICSGMBH\|30625HANNOVER` | Merge into 530 |
| `Aspero Medical Inc.` | 590 | catheter | 2 | 0 | `10835DOVERST\|CO\|80021` | Re-key, no merge target |
| `Aniq Darr` | 608 | catheter | 1 | 0 | `700AVEFAIRFIELD\|CT\|06902` | **Hold** — person-shaped name |
| `Fearsome Limited` | 553 | auto | 2 | 0 | `FEARSOMELIMITED` | Already correct, skip |
| `Wiscosin Rapids` | 625 | catheter | 1 | 6 | `400DEWEYST\|WI\|54494` | **Exclude** — catheter facility |
| `Aspirus Urology Wausau` | 614 | catheter | 1 | 9 | `3300DRWESTHILL\|WI\|54401` | **Exclude** — catheter facility |

Eleven further address-keyed customers hold NRE orders and zero distributions: New World Medical
(533), Boston Scientific Corporation (543), Childrens Hospital of Orange County (522), AbbVie Inc.
(525), Tingo Medical LTD (527), Pathway Medtech (536), Hybron Technologies (585), Momentum LLC (586),
Neptune (588), Supira Medical (589), Richman Chemical Inc (597). Do not hardcode this list — derive
candidates from the selection rule and use the table only to check your output looks right.

**Code to reuse rather than reinvent**

| Thing | Where |
| --- | --- |
| `normalize_facility_name`, `canonical_customer_key` | `modules/customer_profiles/utils.py` lines 6 and 33 |
| `compute_facility_key_from_ship_to` | same file, line 197 |
| `find_or_create_customer` and its `identity` parameter | `modules/customer_profiles/service.py` line 109 |
| Existing merge / rekey precedent | `scripts/_remediate_customer_profiles.py` |
| Backfill script shape with dry-run / execute | `scripts/backfill_order_types.py` |
| `order_data_is_catheter`, `CATHETER_SKUS` | `modules/rep_traceability/service.py` |
| Identity decision at import | `modules/rep_traceability/admin.py` lines 248-300 |
| ShipStation credential checks and error path | `modules/shipstation_sync/admin.py` lines 81-82, 185-213 |

**Conventions**
- `url_for(...)` for every URL, including inside inline JavaScript.
- CSRF token on every state-changing form.
- `record_event` for every state change on a regulated record, with a full metadata snapshot.
- UI language: short, plain, list-like. No internal document numbers in labels.
- Windows/PowerShell: no `&&` chaining, no bash heredocs, no non-ASCII in script output.
- Postgres is the deploy target. The local SQLite migration chain is broken at a Phase 3 ancestor, so
  never try to prove anything by rebuilding SQLite from scratch; tests build schema with
  `Base.metadata.create_all`.

---

## Acceptance checklist

- [ ] No migration added; `alembic heads` still prints exactly `f8a9b0c1d2e3`
- [ ] A line-less order is no longer classified catheter, and one rule implementation exists
- [ ] NRE customers are created with `identity="company"` and `customer_type="nre"`
- [ ] Every caller of `order_data_is_catheter` audited and reported
- [ ] `GmbH` and its tails stripped; **`AB` not added**
- [ ] Merge moves sales orders, distributions, notes and rep assignments **before** deleting
- [ ] Notes and rep assignments provably survive a merge
- [ ] Rep assignments de-duplicated without raising
- [ ] No transient or final duplicate `company_key`; `RESTRICT` on `sales_orders` never hit
- [ ] `customer.rekeyed_merged` audit event carries the full snapshot
- [ ] Surviving name defaults to the most complete candidate and is operator-editable
- [ ] Backfill excludes Wisconsin Rapids and Aspirus Urology Wausau, and reports that it did
- [ ] Backfill holds person-shaped names rather than guessing
- [ ] Five catheter name clusters untouched
- [ ] Dry-run, execute and verification output all pasted
- [ ] ShipStation probe runs server-side, read-only, with **no credential ever requested from the operator**
- [ ] No lateness, aging or overdue logic anywhere
- [ ] All fifteen test areas covered, including permission and CSRF enforcement
- [ ] Full gate run and reported; pushed to `main`; deploy confirmed green explicitly
