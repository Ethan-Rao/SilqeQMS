# P4-06C — Make uploading a PO actually fill in the PO

You are the Phase 4 dev agent on Silq eQMS. Read `docs/SYSTEM_OVERVIEW.md` and
`docs/DC.SLQ002-Phase4/PHASE4_PLAN.md` first. P4-07 is deployed at `45f81b6`, alembic head
`j2d3e4f5a6b7`. This change set chains from there. **No migration is expected — see Task F.**

The theme: Ethan is about to upload a batch of purchase orders and invoices. Today, uploading a PO PDF
whose filename does not follow the SILQ convention **fails outright** rather than filling anything in,
because PDF-text PO-number detection almost never succeeds. He has asked for this to work regardless of
filename. Line items are never extracted at all.

**Read Task A before you write a single regex.** There is a real possibility that these PDFs carry no
text layer, in which case no amount of parsing will ever work and the correct deliverable is that
finding, clearly reported. Evidence first, code second.

## Production facts, verified read-only

- **150 `po_pdf` attachments**, 160 purchase orders (56 open / 104 closed after the P4-06 backfill).
- The P4-06 parse-check, over the first 60 documents, reported:

| Field | Agree | Disagree | Not found |
| --- | --- | --- | --- |
| `po_number` | 1 | 1 | 58 |
| `order_date` | 54 | 3 | 3 |
| `supplier_name` | 0 | 56 | ~4 |

- That measurement was taken **before** P4-06B corrected it, and the corrected figures were never put on
  record. Task A closes that.
- `parse_purchase_order_pdf` (`purchasing/parsers/pdf.py:124-174`) hard-codes `"items": []` and never
  populates it. **Line items have never been extracted from a PO PDF.**
- Its three regexes are generic keyword scans (`Vendor|Supplier|Sold To`, `Date|Order Date`,
  `PO|P.O.|Purchase Order`) that were never anchored to Silq's actual PO template.
- `purchasing_import_pdf_post` (`admin.py:1623-1625`) aborts with "Unable to detect PO number from PDF"
  when no number is found. Given 58 of 60 not-found, a non-conforming filename means the upload is
  refused and the operator's file is discarded.
- P4-06B closed the supplier trust gate (`admin.py:1627-1638`): `supplier_id` and `notes` are filled
  only when the supplier came from a conforming filename. That gate stays closed unless Task D earns
  opening it.
- Known-bad rows from the P4-06 cleanup list, useful as test subjects: order dates of 1931 on POs
  `0000038`, `0000039`, `0000040`; no reference file on `0000115`, `0000119`, `0000120`, `0000124`,
  `0000131`, `0000145`.

## Frozen decisions (confirmed by Ethan; do not re-ask)

- **D50 — A missing PO number must never discard the upload.** Show a review form pre-filled with
  whatever was extracted; the operator supplies the PO number; the file attaches on save.
- **D51 — Review only when needed.** Stop for confirmation when a field is missing or conflicts with
  what is already on the PO. Otherwise fill silently and list the filled fields in the confirmation
  message. Do not add a mandatory confirmation step to every upload; Ethan does this often and friction
  is the thing he asked to remove.
- **D52 — Line items are written only when the PO has none.** An upload must never duplicate, merge into,
  or overwrite existing lines.
- **D53 — Never auto-create suppliers.** An extracted supplier name with no matching `Supplier` row
  leaves `supplier_id` blank, records the extracted name in notes, and is visibly flagged so Ethan can
  set it.
- **D18 still applies:** no lateness, aging, overdue or stale logic anywhere.

## Task A — Find out what is actually in these PDFs, and report it

Build a server-side, read-only diagnostic alongside the existing parse-check — production Spaces
credentials only exist on App Platform, so this cannot be done from a local script.

- Route it under `/admin/purchasing/pdf-text`, `purchasing.view` permission, bounded the same way the
  parse-check is (document cap plus a wall-clock budget, partial results rendered rather than hanging —
  see `admin.py:1225-1226, 1266-1267`). A page that hangs is a page Ethan cannot use; that lesson cost
  us the ShipStation probe once already.
- For each sampled document report: filename, whether the filename conforms, **the character count of
  extracted text**, page count, and the **first ~40 lines of raw text verbatim**.
- Across all 150, report the distribution of text length — specifically **how many documents yield
  essentially no text** (say under 50 characters), which is the signature of a scan with no text layer.

**Then read your own output and report what the documents actually look like** before writing extraction
rules: are they Silq-generated POs on one consistent template, supplier-generated confirmations in many
layouts, scans, or a mix? Where do the PO number, date, supplier and line items actually sit, and under
what labels?

If a large share have no text layer, **stop and say so.** The honest deliverable is then "these cannot
be parsed; naming files by convention or typing the details is the only path", and you should implement
Task E's review form so uploads at least stop failing. Do not fabricate regexes against documents you
have confirmed are images. **No OCR** — that is a dependency and a scope decision Ethan has not made.

## Task B — Anchored extraction, driven by Task A's evidence

Only for the layouts Task A shows are actually parseable:

- Replace the generic keyword scans with rules anchored to the real template — label text with position,
  or `pdfplumber`'s word/table extraction where the layout is tabular. Cite in comments which observed
  layout each rule targets.
- Extract `po_number`, `order_date`, `supplier_name`, and **line items** (item code, description,
  quantity, unit price) where the layout provides them.
- Keep the function signature and the `raw_text` key intact; the parse-check and its tests depend on
  them.
- Handle multiple date formats including the spaced form P4-06 added, and keep rejecting alphabetic-only
  PO tokens (`pdf.py:152-154`) — that guard exists because company names sit next to the words
  "Purchase Order".
- A field you cannot extract confidently must come back `None`. A wrong value is worse than a blank one,
  because a blank prompts a review under D51 while a wrong value is written silently.

## Task C — Supplier resolution (D53)

- Match an extracted supplier name against existing `Supplier` rows on a normalized comparison, not the
  bare `ilike` at `admin.py:1632`. Reuse or extend the existing name-normalization helpers rather than
  writing a fourth one; `customer_profiles/utils.py` already strips corporate suffixes.
- Set `supplier_id` **only on a unique match.** Zero matches or several leave it blank, put the extracted
  name in notes, and flag it in the response to the operator.
- Never insert a `Supplier` row from extracted text.

## Task D — Earn the right to trust PDF text, with measurement

The supplier gate is closed for a reason: PDF-text supplier agreed with the stored value **0 times out of
56**. Re-run the parse-check after Task B and report the corrected table.

A PDF-text field may be trusted for automatic filling only if, over at least 60 documents, it agrees on
**95% or more of the documents where it found a value**, and you can explain every remaining
disagreement individually. State the numbers you are relying on.

- If `supplier_name` clears that bar, open the P4-06B gate and say what the measurement was.
- If it does not, **leave the gate closed** and report the number. Do not relax it because the new code
  feels better than the old code.
- The filename remains the highest-trust source when it conforms. Provenance ordering does not change.

## Task E — Upload behaviour (D50, D51, D52)

- **No PO number found:** render a review form pre-filled with everything that was extracted, so the
  operator types only the number. **The uploaded bytes must survive the round trip** — stage the object
  in storage and carry its key through the form; do not ask the operator to re-select the file, and do
  not hold the file in the session. Clean up staging objects that are never confirmed, and say how.
- **Something missing or conflicting** with what is already on the PO: show the same review form with the
  conflict spelled out, old value beside new. The operator decides.
- **Everything found and consistent:** fill and commit, and name the filled fields in the flash message
  exactly as the current code does at `admin.py:1692-1695`.
- **Fill blanks only, always.** `apply_po_blank_fills` stays the only path onto an existing PO; extraction
  never overwrites an operator's value.
- **Line items:** write extracted lines only when the PO has zero lines (D52). If it has lines and
  extraction found different ones, say so in the message and change nothing.
- Preserve the existing rollback behaviour on `admin.py:1680-1690`: a failed DB write deletes the objects
  this request uploaded. It must never delete a pre-existing attachment.

## Task F — Cleanup

- P4-07 introduced a `SAWarning` at `customer_profiles/admin.py:69` — a `Subquery` coerced into `IN()`.
  Pass an explicit `select()`. Behaviour must not change; the P4-07 tests stay green.
- No migration is expected anywhere in this change set. If you believe one is needed, stop and explain
  before writing it.

## Do not do these

- Do not add a dependency, and do not add OCR (Task A).
- Do not invent extraction rules for documents you have confirmed carry no text (Task A).
- Do not open the supplier trust gate without the measurement that justifies it (Task D).
- Do not auto-create `Supplier` rows (Task C).
- Do not overwrite any non-blank PO field, and do not touch existing line items (Task E).
- Do not make confirmation mandatory on every upload (D51).
- Do not change the PO Log export layout or the closure semantics from P4-06.
- No lateness, aging or overdue logic (D18).

## Tests

New file `tests/test_p4_06c_po_extraction.py`:

1. Extraction against a fixture built to the layout Task A actually observed returns the expected
   po_number, order_date, supplier and line items.
2. A PDF with no text layer returns all-`None` fields and raises nothing.
3. A conforming filename still wins over PDF text for po_number, order_date and supplier.
4. Upload with no detectable PO number renders the review form, does **not** create a PO, and the staged
   file is still retrievable from storage afterward.
5. Confirming that review form creates the PO and attaches the staged file exactly once.
6. Abandoning the review form leaves no orphaned PO and no unreachable storage object.
7. Upload against an existing PO fills only blank fields; a populated `order_date` and `supplier_id` are
   left untouched, and the response names what was filled.
8. A conflicting extracted value triggers the review form rather than a silent write.
9. Line items are written when the PO has none.
10. Line items are **not** written, altered or duplicated when the PO already has lines, and the response
    says so.
11. A supplier name matching exactly one `Supplier` sets `supplier_id`; zero and multiple matches leave it
    blank, note the name, and create no `Supplier` row.
12. A failed DB write during upload deletes only the object this request staged, leaving pre-existing
    attachments intact.
13. The `pdf-text` diagnostic renders within its budget and reports partial results when capped.

Keep the existing suite green. **Baseline is 501 passed, 1 skipped**, which I verified locally at
`45f81b6`.

## Gate before pushing

1. Full suite green, **run after your final edit**, and report the count.
2. `alembic heads` prints a single head, expected to still be `j2d3e4f5a6b7`.
3. `python -c "import app.wsgi"` succeeds; a local Spaces `HeadBucket 403` is the known stale-credential
   condition, not a failure.
4. Push to `main` and confirm `/health` returns `{"ok":true}`.

## Report back

- **Task A first, before anything else:** the text-length distribution across all 150 documents, how many
  have no usable text layer, and verbatim raw text from at least six documents spanning different
  suppliers and years. Then your reading of what these documents are.
- The corrected parse-check table from Task D, before and after your changes, including how many of the
  150 filenames conform.
- Per field, whether you now trust PDF text for automatic filling, and the number behind that call.
- Whether line-item extraction is viable on these layouts, honestly. "Not on these documents" is an
  acceptable answer; a plausible-looking parser that has never matched a real PO is not.
- Anything you found that suggests uploading will damage existing PO data, however small.
