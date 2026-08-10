# Phase 3 — Prompt 10: Production Cleanup + Phase 4 Preparation

## Context

Track A is complete. 119 controlled documents, 210 revisions, and 209 files are live in the
Document Control module. The system is now ready for a production cleanup pass followed by
Phase 4 (records upload — CAPAs, audits, equipment, suppliers, etc. into admin_docs libraries).

**This prompt covers two tasks:**

- **Task A — Production data cleanup** (run a one-off script against prod)
- **Task B — Phase 4 readiness code changes** (deploy then run the records import)

---

## Task A — Production cleanup script

Write a script at `scripts/_cleanup_prod.py` (same pattern as `scripts/_run_prod_import.py`).
The script sets prod credentials directly and performs the following deletions. It must
print what it is about to delete, then delete, then commit, and report totals.

### Confirmed items to delete

**Test user accounts** — delete these two accounts entirely (rows from `users` table and all
join-table associations). Do NOT delete any other accounts.

| Email | Role |
|-------|------|
| `qa_tester@silq.test` | admin |
| `readonly_tester@silq.test` | staff |

Keep: `earao72419@gmail.com`, `ethanr@silq.tech`, `silqrepservice@gmail.com`,
`stephen.medreg@gmail.com`.

**Test documents in Document Control** — hard-delete the following document rows plus their
revisions, files (DB rows AND S3 objects), and audit events. The doc numbers to delete are:

- `SRS-TEST-001`
- `SRS-TEST-002`
- `SRS-TEST-003`
- `SRS-TEST-004`
- `Test001`

Use the storage backend abstraction (`from app.eqms.storage import get_storage; storage =
get_storage()`) to delete the S3 objects before removing DB rows. For each `DocumentFile`,
call `storage.delete(file.storage_key)` (catch and log if the key is already absent, don't
abort). Then delete related `audit_events`, `document_files`, `document_revisions`, and
`documents` rows in order.

**Admin_docs folders** — cascade-delete the following folders and all their files (both DB
rows and S3 objects). Use the same storage delete pattern for each `AdminDocFile`.

| Library key | Folder name |
|-------------|-------------|
| `qms_documents` | `FileHoldImports` |
| `qms_documents` | `SRS Test Folder` |

To find them: `s.query(AdminDocFolder).filter_by(library_key="qms_documents", parent_id=None, name="FileHoldImports").first()`.
Walk the tree recursively (subfolders first) to delete all descendant files and folders.

### Guard rails

- Confirm the exact set of items to delete at the top of the script (print IDs + names).
- If any expected item is NOT found (already deleted), log a warning and continue.
- Wrap everything in a single transaction. Commit only if zero errors.
- Add a `DRY_RUN = True` flag at the top of the script (flip to `False` to actually execute).

### After writing the script

Run `python scripts/_cleanup_prod.py` with `DRY_RUN = True` and paste the output so the
coordinator can verify the target list, then set `DRY_RUN = False` and run again to commit.

---

## Task B — Phase 4 readiness: records import infrastructure

The next phase uploads records into the 11 `admin_docs` libraries. The existing
`scripts/bulk_import_admin_docs.py` does the heavy lifting. Prepare the following:

### B1 — Folder-to-library mapping document

Create `docs/DC.SLQ002-Phase3/PHASE4_RECORDS_MAPPING.md`. For each source folder in the
workspace root, propose the target `admin_docs` library and any sub-folder structure to create
inside it. Use this as the definitive mapping:

| Source folder (workspace root) | Target library key | Notes |
|---|---|---|
| `QMSInProcess/CAPAs/` | `capas` | Subfolder per CAPA number (CAPA001, CAPA002, …) |
| `QMSInProcess/DCOs/` | `qms_documents` | Subfolder `DCO Log and Change Orders` |
| `QMSInProcess/Audits/` | `management_reviews` | Subfolder `Internal Audits` |
| `QMSInProcess/ManReviewMeetings/` | `management_reviews` | Subfolder `Management Review Meetings` |
| `QMSInProcess/NCMR/` or root `NCMR/` | `ncrs` | Subfolder per NCMR number |
| `QMSInProcess/PostMarketSurv/` | `post_market_surveillance` | — |
| `QMSInProcess/RiskMan/` | `risk_management` | — |
| `QMSInProcess/DHF/` or `SLQ-DHF/` | `dhfs` | — |
| `QMSInProcess/EmployeeTraining/` | `employee_training` | Subfolder per year |
| `QMSInProcess/Manufacturing/` | `work_orders` | — |
| `RegStandardsandApprov/` | `regulatory_standards` | — |

Equipment, Suppliers, Purchasing, Distribution records belong in their respective module
tables (or already have dedicated admin_docs mapping — leave those for Phase 5).

Scan the actual workspace to see what folders/files are present under each source path and
refine the mapping if you find unexpected layouts. List any folders with no matching library
under a "Needs manual triage" section.

### B2 — Dry-run report

For each mapped source path, run `bulk_import_admin_docs.py` with `--dry-run` and capture the
output. Write the summary (file counts, file types, subfolders found) to
`docs/DC.SLQ002-Phase3/PHASE4_DRY_RUN_REPORT.md`.

**Do NOT import anything to production in this prompt.** The coordinator will review the
dry-run report and issue Prompt 11 to execute the actual import.

### B3 — Storage key: confirm new Spaces credentials still work

Before the dry-run, quickly verify S3 connectivity using the same ping pattern from
`_run_prod_import.py`:

```python
s3.put_object(Bucket=..., Key="_phase4_ping", Body=b"ping")
s3.delete_object(Bucket=..., Key="_phase4_ping")
```

If the keys have been revoked by Ethan (as was recommended after Track A), note this in the
report and ask the coordinator for new keys before proceeding.

---

## Deployment discipline

- Task A is a **one-off script** — no code to deploy, no git commit needed.
- Task B creates new files under `docs/` and `scripts/` — commit them but this is not a
  deployable change. No migration.
- Continue following the single-head migration rule and import guard for any code changes.

---

## Deliverables

1. `scripts/_cleanup_prod.py` — dry-run output pasted into reply.
2. `scripts/_cleanup_prod.py` executed with `DRY_RUN = False`, totals reported.
3. `docs/DC.SLQ002-Phase3/PHASE4_RECORDS_MAPPING.md` — source → library map.
4. `docs/DC.SLQ002-Phase3/PHASE4_DRY_RUN_REPORT.md` — per-library dry-run file counts.
5. Confirmation of S3 connectivity (or a note if keys need to be refreshed).
