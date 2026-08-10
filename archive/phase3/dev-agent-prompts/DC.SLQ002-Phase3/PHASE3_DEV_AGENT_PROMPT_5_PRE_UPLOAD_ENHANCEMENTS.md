# Phase 3 — Dev Agent Prompt 5: Reconciliation Corrections + Pre-Upload System Enhancements

**Context:** You completed the Prompt 4 reconciliation (229 docs; 114 Document Control + 115 records; `DCO_Log_v2.csv` with 440 rows; suite green, single head, nothing imported). This prompt has two parts: **Part A** applies Ethan's corrections and regenerates the reconciliation; **Part B** is the pre-upload enhancement series to make the system intuitive before ~219 documents are loaded. The actual production document load (Track A) remains a **separate, later, gated** step — **do not run the production import here.**

## Operating rhythm (unchanged)

- Ship each checkpoint to `main`, deploy without waiting for Ethan's sign-off; the coordinator reviews and greenlights the next.
- Keep the suite green; keep the **staff read-only** model intact on every new surface (view/search = `admin.view`/`staff.view`; all writes gated by the relevant `*.edit`/`*.manage`).
- Preserve single Alembic head; migrations additive/nullable.

---

# Part A — Reconciliation regeneration with Ethan's corrections

Apply these to `scripts/reconcile_controlled_docs.py` and regenerate all reconciliation artifacts (`document_register_v2.csv`, `manifests/`, `discrepancies.md`, `DCO_Log_v2.csv`), then push the branch for coordinator review. These are all confirmed by Ethan after the first run:

1. **Include the `Equipment\` folder (essential — was omitted).** It holds the `SP-E.*` (and related `SP-S`) source-control equipment specifications. Add it to the folder scan (§2 of Prompt 4) and **review and include all** documents in that subfolder as **records** (not `document_control` items). This should resolve most of the first run's 35 "no locatable current file" entries (the SP-E/SP-S specs).

2. **Add the title-named-file matcher.** Many controlled files are named by title rather than doc-number (e.g., `Authorized Approvers Form Rev C.pdf` = `FM2-QM.SLQ001` Rev C; `Electronic Signature Acknowledgement Form Rev B.pdf` = `FM1-QM.SLQ014` Rev B). Build a title→doc-number index from the register/logs and auto-link title-named files (parsing the trailing `Rev X`) so they're included instead of dropped. **Use judgment on whether each title-named PDF is an appropriate controlled QMS item**; when a match is ambiguous or clearly not a controlled doc, catalog it as unmatched in `discrepancies.md` rather than force-linking. Prefer such a signed evidence PDF as the current released file when it is the newest signed copy.

3. **FM1-QM.SLQ018 stays at Rev A.** It was mistakenly placed in the DCO093 folder — **remove it from the DCO093 scope**; there is no B revision. This clears its first-run "released master missing" divergence.

4. **FM1-QM.SLQ016 → B is real** and its filename has now been corrected on disk, so the released B master exists — re-verify it links and clear that first-run divergence.

5. **Web-content (`WC.*`) items** will be revised later — do not block on them; leave them catalogued/obsolete as-is.

6. **Re-report** in `discrepancies.md`: the remaining (shrunken) "no locatable file" list after the above, and confirm the DCO085 typo fix (QM.SLQ024→QM.SLQ034) and HX→SLQ normalization still hold. Keep everything **report-only** — no DB writes, no production import.

---

# Part B — Pre-upload system enhancements

## Build against realistic data (important)

So these features are validated against real content rather than empty pages: perform a **local, non-production** import of the reconciliation manifests into your dev/test database (`import_document_control.py` + the `manifests/`, plus a representative set of records into admin_docs). This is local only — **do not push data, do not run the import against production.** It gives you 114 real controlled docs with multi-revision history to build and screenshot against.

## Checkpoint E1 — Unified document discovery + Document Control at scale (priority 1)

Once populated, users must find any document without knowing whether it lives in Document Control or admin_docs.

1. **Global document search / landing** spanning both `document_control` and `admin_docs`. A single search box matching doc number (`QM.SLQ016`), title/keywords (`CAPA`, `purchasing`), and category/library; results deep-link to the correct viewer. Read-only, available to staff.
2. **Document Control list at scale (114 docs):** group by category/subsystem with counts; columns for current rev, effective date, doc type (SOP/WI/Form/Template), status; fast filters (type, status, category) and a "show obsolete" toggle (default off). Ensure pagination/indexing performs.
3. **Revision-history timeline on the detail page:** render the full A→…→F lineage we now have (per-revision effective date, change summary, and DCO reference from `DCO_Log_v2.csv`). Make the current/active revision unmistakable.
4. **Obsolete clarity:** obsolete/superseded revisions get a clear banner ("Superseded by Rev X — retained for history") and visual treatment so no one mistakes a prior revision for current.

## Checkpoint E2 — QMS index & change-history traceability (priority 2)

1. **QMS Document Index** (read-only, staff/auditor friendly): the clean register grouped by **ISO 13485 clause** and by **subsystem**, linking to each current document. Use the ISO-clause mapping from the register.
2. **Change History / DCO Log view** (read-only): surface `DCO_Log_v2.csv` as an in-app, filterable traceability view (by DCO, by document). Admin/auditor-facing; strong for audits and a natural home for the new consolidated log.

## Checkpoint E3 — Cross-linking & training integration (priority 3)

1. **Training ↔ documents:** now that controlled docs exist, let training assignments target a specific controlled document/revision (read-and-acknowledge "QM.SLQ016 D"), and show the doc's current revision in the My Training item.
2. **Related documents:** from a document, surface its related controlled forms/templates (e.g., `QM.SLQ015` ↔ its `FM#-QM.SLQ015` forms) via the shared SLQ number.

## Checkpoint E4 — Usability & readiness sweep (priority 4, fold in as time allows)

Consistent search boxes, breadcrumbs, and empty states; a mobile/responsive pass on the document and dashboard views; accessibility basics (labels, focus, contrast); and a quick performance check against the populated corpus.

## Guidance

- Do Part A first and push for review; then treat E1 as the highest-value work. E2–E4 can be additional series if scope grows — use judgment and tell the coordinator if you want to split further.
- Do not modify the reconciliation logic beyond Part A, and do not run the production load.
- Report per checkpoint: what shipped, screenshots against the locally-imported data, suite status, migration head, and confirmation the staff read-only model holds.
