# Phase 3 — Dev Agent Prompt 4: Controlled-Document Housecleaning & Staging Assembly (pre-import)

**Status:** This is a **reconciliation + organizing** task. **Do NOT run the document importer or load anything into the database.** The output is a clean, human-reviewable determination of *active vs. obsolete* for every controlled document, plus an assembled staging tree, for coordinator + Ethan review. The actual import is a later checkpoint that runs only after this is reviewed and after one more system-enhancement pass.

---

## 1. Why this exists

Ethan (sole QA/RA) needs a thorough housecleaning of active-vs-obsolete controlled documents before migrating them into the eQMS Document Control module. The existing indexes are **stale**:

- `QM_DOCUMENT_REGISTER.csv` and the `QM Documents\` folder are roughly **one full revision behind** for ~35 SOPs/WIs.
- The official `DCOs\SILQ DCO Log.xlsx` only records through **DCO091**. DCO092–095 are **signed/executed and physically present in `QMSInProcess\`** but were never written back to the DCO log or the Document Number log.
- The `Forms, Templates, and Travelers\` folder is likewise partially stale (some DCO095 forms present; DCO091–094 form updates missing).

**Authoritative rule (from Ethan):** `QMSInProcess\` holds the current, source-of-truth active versions. Any older revision found elsewhere is **obsolete/superseded** and must be preserved as a prior-revision record (never deleted).

## 2. Authoritative inputs (read these; do not mutate)

- `DCOs\SILQ DCO Log.xlsx` — change history (originator, curr rev → new rev, release/effective dates). Authoritative **through DCO091 only**.
- `DCOs\SILQ Document Number Log.xlsx` — per-document current rev + assigning DCO. **Also stale** (does not reflect DCO091's `QM.SLQ001→B`, and omits DCO092–095). Use as corroboration, not ground truth.
- `QM_DOCUMENT_REGISTER.csv` — the previous manual register. Stale; use only for titles / ISO clause mapping / folder hints.
- `QMSInProcess\DCO0xx\` — **current released packages** (DCO087–095). Each contains the new-revision file(s) (usually `.docx`), redlines (`*_RedLine*.docx`), and a signed DCO PDF.
- Controlled-document folders to scan for current + superseded files: `QM Documents\`, `Forms, Templates, and Travelers\` (Forms / Templates / Travelers), `DCOs\Previous Revisions\**`, `DCOs\CompletedDCOs\`, `DMR\`, `DHF\`, `SLQ-DHF\`, `RiskManagement\`, `Administration\`.

## 3. Precedence rules (implement exactly)

For each controlled document number, the **current released revision** = the **highest revision** found across, in this priority order:

1. `QMSInProcess\DCO0xx\` package files (newest completed DCOs — **treated as released even if not in the DCO log**).
2. The `DCO log` new-rev entries (through DCO091).
3. The "clean" folders (`QM Documents\`, `Forms, Templates, and Travelers\`).

Revision ordering is Excel-style base-26 (A < B < … < Z < AA), matching `document_control.service.next_revision`. Every revision **below** the current one that has a physical file anywhere = a **superseded/obsolete** record to preserve. The **current file** is the newest package's file; prefer the native master (`.docx`/`.xlsx`) as the released copy and attach the signed DCO PDF as supporting evidence (see §8 flag).

## 4. Reconciled current-revision determination (coordinator's analysis — verify, don't blindly trust)

This is my hand-reconciliation from the DCO log + `QMSInProcess`. Your script must **regenerate this programmatically** and **report any divergence** from this table so we catch errors on both sides.

**QM SOPs / WIs — current revision:**

| Doc | Current | Source DCO | Stale folder had |
|---|---|---|---|
| QM.SLQ001 | B | 091 | A |
| QM.SLQ002 | B | 028 | B ✓ |
| QM.SLQ003 | C | 092 | B |
| QM.SLQ004 | B | 089 | B ✓ |
| QM.SLQ005 | B | 070 | B ✓ |
| QM.SLQ006–010 | A | 007 | A ✓ |
| QM.SLQ011 | B | 094 | A |
| QM.SLQ012 | C | 093 | B |
| QM.SLQ013 | C | 093 | B |
| QM.SLQ014 | C | 091 | B |
| QM.SLQ015 | C | 092 | B |
| QM.SLQ016 | D | 093 | C |
| QM.SLQ017 | B | 092 | A |
| QM.SLQ018 | B | 093 | A ⚠️ on-disk file mislabeled "C"; correct rev is B |
| QM.SLQ019 | C | 039 | C ✓ |
| QM.SLQ020 | E | 092 | D |
| QM.SLQ021 | E | 093 | D |
| QM.SLQ022 | C | 093 | B |
| QM.SLQ023 | B | 093 | A |
| QM.SLQ025 | A | 007 | A ✓ |
| QM.SLQ026 | D | 094 | C |
| QM.SLQ027 | F | 094 | E |
| QM.SLQ028 | B | 093 | A |
| QM.SLQ029 | B | 094 | A |
| QM.SLQ030 | B | 093 | A |
| QM.SLQ032 | A | 007 | A ✓ |
| QM.SLQ033 | B | 094 | A |
| QM.SLQ034 | G | 088 | G ✓ |
| QM.SLQ035 | D | 085 | D ✓ |
| QM.SLQ036 | F | 092 | E |
| QM.SLQ037 | B | 094 | A |
| QM.SLQ038 | C | 094 | B |
| QM.SLQ039 | C | 094 | B |
| QM.SLQ040 | C | 094 | B |
| QM.SLQ043 | B | 094 | A |
| QM.SLQ045 | B | 094 | A |
| QM.SLQ046 | B | 094 | A |
| QM.SLQ047 | B | 094 | A |
| QM.SLQ048 | B | 094 | A |
| QM.SLQ049 | B | 094 | A |
| QM.SLQ050 | B | 094 | A |
| QM.SLQ051 | B | 094 | A |
| QM.SLQ052 | A | 095 | (new) |

**Forms / Templates with revisions newer than the clean folder** (current → source): FM1-QM.SLQ001→B (091), FM2-QM.SLQ001→C (088), FM1-QM.SLQ014→B (091), FM1-QM.SLQ015→B (092), FM2-QM.SLQ015→B (092), FM7-QM.SLQ015→B (092), FM2-QM.SLQ017→B (092), FM1-QM.SLQ016→B (093), FM1-QM.SLQ018→B (093), FM1-QM.SLQ040→B (094), FM4-QM.SLQ050→B (094); new in 095: FM1/FM2/FM3-QM.SLQ052, TMP1/TMP2-QM.SLQ052. All other FM/TMP remain at their register revision.

## 5. Deliverable A — reconciliation engine (`scripts/reconcile_controlled_docs.py`)

Build a deterministic, report-only script (unit-tested) that:

1. Parses both `.xlsx` logs (openpyxl; it's already a dependency) into a normalized change history.
2. Recursively scans the folders in §2, parsing each filename into `(doc_number, revision, title, ext, path)`. Handle real-world messiness seen on disk: mixed case extensions (`.DOCX`), `_RedLine`/`_Redlined`/`_RL` suffixes (exclude redlines from "released file" candidates — they are working artifacts, not releases), duplicate names (`DCO077B (2).docx`), and `Rev C`-style suffixes.
3. Computes, per document number, the **current revision + current file** and the ordered list of **superseded revisions + files**, applying the §3 precedence.
4. Emits (all text, safe to commit):
   - `eQMS_Upload_Staging/reconciliation/document_register_v2.csv` — one row per doc: number, title, doc_type, current_rev, current_source_dco, current_file_path, superseded_revs, intended_destination (§6), status, flags.
   - `eQMS_Upload_Staging/reconciliation/manifests/<doc_number>.json` — importer-ready manifest per document (ordered revisions with file path, effective_date from the DCO log, change_summary, released flag). These are the inputs the existing `import_document_with_revisions()` / `scripts/import_document_control.py` will consume **later**.
   - `eQMS_Upload_Staging/reconciliation/discrepancies.md` — every anomaly: divergence from §4, docs with no locatable current file, revision gaps, log-vs-disk conflicts, redline-only revisions, the known flags in §8.

## 6. Deliverable B — staging assembly (`eQMS_Upload_Staging/`)

**Copy (never move/delete)** the resolved files into a clean tree:

```
eQMS_Upload_Staging/
  document_control/            # QM.SLQxxx SOPs/WIs + FM#/TMP# forms & templates
    <DOC_NUMBER>/
      current/<current file>
      superseded/<prior-revision files>
  reconciliation/              # the text outputs from Deliverable A (committable)
```

- **Classification / intended destination** (record it in `document_register_v2.csv`, follow Ethan's system-of-record decision):
  - **Document Control module:** `QM.SLQ*` SOPs/WIs and their controlled `FM#-QM.SLQ*` forms and `TMP#-QM.SLQ*` templates.
  - **admin_docs libraries (records, later):** everything else (SW/DC/VV/SP/QC/BOM/BOR/MP/L/OM/RM/DMR design & DHF docs, CAPAs, audits, etc.). Still reconcile active-vs-obsolete for these and list them, but stage them separately (e.g., a `records/` subtree) or just catalog them — do not intermix with `document_control/`.
- Binary files copied into staging must **not** be committed (add `eQMS_Upload_Staging/**` binaries to `.gitignore` if not already ignored; keep the `reconciliation/` text outputs committable).

## 7. Deliverable C — rebuilt consolidated DCO log (`eQMS_Upload_Staging/reconciliation/DCO_Log_v2.csv`)

Ethan is replacing the existing DCO log — he dislikes its format (merged header rows, blank filler columns, one-Y/N-column-per-assessment sprawl). Produce **one clean CSV** that captures everything necessary without being excessive. This becomes the canonical DCO log going forward.

- **Grain:** one row per (DCO, affected document / line item) — the same natural grain as today, just clean.
- **Sources:** the current `DCOs\SILQ DCO Log.xlsx` is source-of-truth **through DCO091**. For **DCO092–095**, derive rows from the DCO Word docs in `QMSInProcess\DCO09x\DCO09x.docx` (and pull the human-readable change description/reason from those Word files). For DCO001–091, populate `change_description` from `DCOs\CompletedDCOs\*.docx` where cleanly parseable; otherwise leave it blank rather than guessing.
- **Columns (exactly these — compact, no merged headers, no blank spacer columns):**
  1. `dco_number`
  2. `document_number` — normalized to current SLQ numbering (map legacy `QM.HX###` / `FM#-SLQ###` tokens to their `QM.SLQ###` / `FM#-QM.SLQ###` equivalents; the 2021 DCO007 re-baseline is the HX→SLQ transition). Flag any token that can't be confidently mapped instead of dropping it.
  3. `document_title`
  4. `from_rev` (current rev before the change; `-`/`N/A` for initial release)
  5. `to_rev` (new rev)
  6. `change_description` (reason for change, from the DCO Word doc; blank if unavailable)
  7. `originator`
  8. `date_requested`
  9. `effective_date`
  10. `impact_assessments` — a single semicolon-delimited list of only the assessments that apply, drawn from {Training, Risk, Validation, Regulatory, Material Disposition}; blank if none. (This replaces the five separate Y/N columns. If Ethan later wants them explicit, it's a trivial switch.)
- **Corrections to bake in (and note in `discrepancies.md`):**
  - **QM.SLQ018:** the DCO093 revision was mislabeled `C`; the correct revision is **B**. Record `A → B` in the rebuilt log and treat the on-disk `QM.SLQ018 C …` file as revision **B** everywhere (stage it as B; flag that the source master filename should be corrected to `B`).
  - **DCO085:** `QM.SLQ024` is a typo for **QM.SLQ034** (Organization Chart E→F) — record it as QM.SLQ034.
- **Sort** by DCO number, then line item, so the file diffs cleanly on re-run.

## 8. Known flags to resolve in `discrepancies.md` (surface, don't silently fix)

1. **QM.SLQ018 mislabel (resolved by Ethan):** the DCO093 file `QM.SLQ018 C …` is a labeling mistake; the correct revision is **B**. Treat/stage as B and record `A → B`; flag that the source master filename should be renamed to B. Do not create a separate `C`.
2. **DCO085 typo (resolved):** `QM.SLQ024` → **QM.SLQ034** (E→F).
3. **DCO092–095 not in the legacy DCO log.** Treated as released (per Ethan) and now captured in `DCO_Log_v2.csv`; flag that the legacy `.xlsx` and the Document Number log remain out of date (Ethan's QA action, not yours).
4. **Released-file format:** current masters in `QMSInProcess` are `.docx`, not signed PDFs (only the *DCO* is signed as PDF). Use the `.docx` master as the released file with the signed DCO PDF referenced as evidence — flag any document where neither a master nor an evidence PDF can be found.
5. Any document number in the logs/register with **no locatable file** anywhere (e.g., obsolete-only or missing).

## 9. Constraints

- **No database writes, no import, no deploy.** This checkpoint ends at reviewable artifacts.
- **Source documents are read-only**: copy into staging, never move or delete originals.
- Deterministic output (stable ordering) so re-runs diff cleanly.
- Commit only: the script(s), their tests, and the `reconciliation/` text outputs (`document_register_v2.csv`, `manifests/`, `discrepancies.md`, `DCO_Log_v2.csv`). Do not commit copied binaries. Continue to leave the pre-existing unrelated working-tree changes untouched.

## 10. Report back to the coordinator

- Counts: total controlled docs, # current-revision changes vs. the stale register, # superseded files staged, # docs routed to Document Control vs. records, and # DCO log rows (with a note on how many DCO092–095 rows were reconstructed from the Word docs).
- The full `discrepancies.md` (most important output — reviewed before anything is imported) and a sample of `DCO_Log_v2.csv`.
- Confirm the suite stays green and the reconciliation script has tests (include a test for the HX→SLQ normalization and the QM.SLQ018/DCO085 corrections).
- Do **not** proceed to import; stop here for review.
