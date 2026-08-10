# Track A — Production Document Load Runbook

**What this is:** the operational procedure to load the reconciled controlled documents (and
records) into the **production** Silq eQMS. This is a **data migration**, not a code deploy —
it writes rows to the prod Postgres DB and uploads files to prod S3 storage. It does **not**
go through git/DigitalOcean auto-deploy. Run it deliberately, with a backup and a dry-run.

**Who runs it:** whoever has all three of these at once — the **source files on disk**, the
**prod `DATABASE_URL`**, and the **prod S3 credentials**. The dev-agent sandbox cannot (it has
none of these).

---

## ⚠️ Blocker to clear first — source files are not present

As of this writing there are **zero `.docx`/`.pdf` files in the workspace**. The manifests
(`eQMS_Upload_Staging/reconciliation/manifests/*.json`, 114 controlled docs) reference files by
relative path, e.g.:

```
QM.SLQ016/current/QM.SLQ016 D CAPA SOP.docx
QM.SLQ016/superseded/QM.SLQ016 C CAPA SOP.docx
```

The importer's `--base-dir` must be a directory where those exact relative paths resolve to real
files. **Nothing loads until the files are assembled there.** Options:
- If the source files are on OneDrive but cloud-only/dehydrated, materialize (download) them.
- If they live elsewhere (another drive / FileHold export), assemble them into the
  `<doc_number>/current/…` + `<doc_number>/superseded/…` layout the manifests expect (or adjust
  the manifests' `file` paths to match where the files actually are).

**Pre-flight check** (run from repo root; must report the files exist):
```powershell
python scripts/import_document_control.py `
  --manifest-dir eQMS_Upload_Staging/reconciliation/manifests `
  --base-dir "<PATH-TO-ASSEMBLED-FILES>" `
  --enrich-dco --dry-run
```
A clean dry-run prints each doc's plan and ends with `0 errors`. Any `missing file …` line
means the base-dir/layout is wrong — fix before proceeding. **Dry-run writes nothing.**

---

## Prerequisites checklist
- [ ] Source files assembled so the manifest relative paths resolve under `--base-dir`.
- [ ] `.env` (or environment) points at **prod** `DATABASE_URL` and **prod** S3
      (`S3_ENDPOINT`/`S3_BUCKET`/`S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY`/`S3_REGION`),
      `STORAGE_BACKEND=s3`, `ENV=production`.
- [ ] Admin user exists in prod (already seeded — the importer attributes the load to it).
- [ ] **Fresh DigitalOcean Postgres backup/snapshot taken** (see Step 1).
- [ ] Confirm current prod is healthy (`/healthz` 200) and on the latest commit.

---

## Step 1 — Back up production Postgres (do NOT skip)
Take a manual snapshot/backup of the managed Postgres in the DigitalOcean console (Databases →
your DB → Backups / create snapshot), or `pg_dump` to a local file. This is the rollback path if
the load goes wrong. Record the snapshot time/id here: `__________`.

## Step 2 — Dry-run the controlled-document import (no writes)
```powershell
python scripts/import_document_control.py `
  --manifest-dir eQMS_Upload_Staging/reconciliation/manifests `
  --base-dir "<PATH-TO-ASSEMBLED-FILES>" `
  --enrich-dco --dry-run
```
Verify: every document lists its revisions, files resolve, and totals show `0 errors`. The
`--enrich-dco` flag fills change summaries / effective dates from `DCO_Log_v2.csv`.

## Step 3 — Load controlled documents (real run)
Same command **without** `--dry-run`:
```powershell
python scripts/import_document_control.py `
  --manifest-dir eQMS_Upload_Staging/reconciliation/manifests `
  --base-dir "<PATH-TO-ASSEMBLED-FILES>" `
  --enrich-dco
```
It's idempotent (re-running skips existing docs/revisions by `doc_number` + revision label) and
**rolls back the whole batch if any document errors** — so fix and re-run safely. Expect ~114
documents with full revision history (current + superseded), current revision set active,
obsolete docs marked with reason, and `doc.import` audit events written.

## Step 4 — Load records into admin_docs (per source folder → library)
Records (audits, CAPAs, DHFs, NCMRs, equipment, suppliers, etc.) are **not** controlled
documents; load them into the matching admin_docs library with `bulk_import_admin_docs.py`,
one source directory at a time. Dry-run first, then real:
```powershell
python scripts/bulk_import_admin_docs.py --directory "<SOURCE-FOLDER>" --library <library_key> --folder "<optional subfolder>" --dry-run
python scripts/bulk_import_admin_docs.py --directory "<SOURCE-FOLDER>" --library <library_key> --folder "<optional subfolder>"
```
Library keys: `qms_documents`, `employee_training`, `management_reviews`, `ncrs`, `capas`,
`post_market_surveillance`, `regulatory_standards`, `work_orders`, `risk_management`, `dhfs`,
`forms_templates_travelers`. Idempotent (skips files already present by filename).

## Step 5 — Post-load verification (on the live site)
- [ ] Document Control list shows ~114 docs; category/type/status filters + "show obsolete" work.
- [ ] Open a multi-revision doc (e.g. QM.SLQ016): revision timeline shows A→D, current is
      unmistakable, superseded revisions badged/retained.
- [ ] **QMS Document Index → review the "Unclassified" bucket.** Anything that shouldn't be there
      means extend `_BY_SLQ_FAMILY` / `_BY_DOC_NUMBER` in `qms_index.py` (a code change/deploy).
- [ ] **DCO Log back-links resolve** to the imported documents (depends on normalized doc numbers
      matching between `DCO_Log_v2.csv` and `documents.doc_number` — the reconciliation
      normalization, e.g. HX→SLQ, must hold). Spot-check a few.
- [ ] Records appear in their libraries and render in the viewer.
- [ ] Audit trail (admin-only) shows the `doc.import` events.

## Rollback
If the controlled-doc load fails mid-way it self-rolls-back (single transaction, commits only on
0 errors). If a completed load needs undoing, restore the Step 1 snapshot. S3 objects uploaded by
a partial run are harmless orphans (no DB rows reference them after a rollback); clean up later if
desired.

## Known follow-ups (post-load, code-side — separate small prompts)
- Extend `qms_index.py` mapping for any legitimately-unclassified controlled docs surfaced.
- Any DCO Log doc-number normalization mismatches found in Step 5.
