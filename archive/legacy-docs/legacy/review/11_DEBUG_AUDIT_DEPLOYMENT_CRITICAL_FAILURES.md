# 11 DEBUG AUDIT — Deployment Critical Failures + Unfinished P0s (Lean Fixes & UX Polish)

Baseline spec used (source of truth): `docs/plans/IMMEDIATE_FIXES_AND_UI_IMPROVEMENTS.md`

This report follows the same structure as `docs/review/10_DEBUG_AUDIT_LEAN_FIXES_AND_UX_POLISH.md`, but is focused on **deployment blockers** plus any **P0 items still not fully addressed**.

Deployment runtime evidence provided (DigitalOcean release step):
- 2026-01-23 00:04:56: Alembic upgrade `d1e2f3a4b5c6 -> e4f5a6b7c8d9` failed with:  
  `psycopg2.errors.DatatypeMismatch: column "is_primary" is of type boolean but default expression is of type integer`  
  Generated DDL snippet shows: `is_primary BOOLEAN DEFAULT 0 NOT NULL`
- 2026-01-23 00:04:57: Readiness probe failed (connection refused) because the release step exited non-zero and the app never came up.

---

## A) Snapshot Summary (Top 10 findings)

1) **Deployment Blocker**: Migration `e4f5a6b7c8d9_add_customer_reps_table.py` is attempting to create `customer_reps.is_primary BOOLEAN DEFAULT 0` on Postgres, which hard-fails (`DatatypeMismatch`).  
2) **Process/Artifact Blocker**: The migration file in this workspace currently uses `server_default=sa.text("false")`, so the runtime log implies **the deployed image is not running the same code** (stale build cache, wrong branch, or outdated container).  
3) **Blast radius**: Because DO runs migrations during release (`scripts/release.py`), this single DDL issue prevents *all deployments* and results in readiness probe failures.  
4) **P0 correctness gap**: Lot Tracking in `compute_sales_dashboard()` still needs to meet spec: **2025+ lots + all-time distribution totals + Active Inventory** (not just a “current-year” slice).  
5) **P0 correctness gap**: PDF parsing still cannot extract line items from `2025 Sales Orders.pdf` and cannot reliably parse `Label1.pdf` shipping labels without text normalization / label-specific heuristics.  
6) **Maintainability risk**: Notes currently have two UX paths (global modal + dashboard inline), which increases test surface and regression risk.  
7) **Performance risk**: Several endpoints still use `.all()` with Python-side aggregation (dashboard and detail modals), which will degrade as history grows.  
8) **Security/UX risk**: CSRF is enforced globally; any JS endpoints must consistently send `X-CSRF-Token`. Consolidating notes into one UI reduces the chance of CSRF regressions.  
9) **Observability gap**: Release step logs do not show which revision/file content was executed; add a tiny diagnostic print to confirm migration content in the container to prevent “wrong artifact” confusion.  
10) **Immediate action**: Fix the boolean default DDL **and** force a clean rebuild/redeploy to ensure the corrected migration ships.

---

## B) Spec Compliance Matrix (from IMMEDIATE_FIXES_AND_UI_IMPROVEMENTS.md)

Legend: ✅ Implemented correctly • 🟡 Partially implemented / buggy • ❌ Missing

| Spec item | Status | Evidence (file/route/function/model) | Fix note |
|---|---:|---|---|
| Customers crash fix | 🟡 | Model: `app/eqms/modules/customer_profiles/models.py::CustomerRep` | Code now specifies `foreign_keys=[rep_id]` for `CustomerRep.rep` (good), but deployment is currently blocked before this can matter. |
| Rep assignment join table exists | 🟡 | Migration: `migrations/versions/e4f5a6b7c8d9_add_customer_reps_table.py`; Model: `CustomerRep` | Deployment migration currently failing in production due to boolean default mismatch. |
| Notes modal global access | 🟡 | `app/eqms/templates/_layout.html` + `rep_traceability.admin` notes routes | Needs consolidation to one UI path to avoid regressions. |
| PDF import robustness (sales orders + labels) | 🟡 | Parser: `rep_traceability/parsers/pdf.py`; routes: `/admin/sales-orders/import-pdf*` | Still failing against provided example PDFs; needs label-specific logic + text normalization; sales order line items may be non-extractable without OCR. |
| Lot tracking accuracy (2025+ lots, all-time totals, active inventory) | 🟡 | `rep_traceability/service.py::compute_sales_dashboard` + LotLog helpers | Must ensure inclusion rule is 2025+ and aggregation is all-time. |
| Distribution details modal readability | 🟡 | `templates/admin/distribution_log/list.html` + `distribution_log_entry_details` | Styling improved; still missing Notes/Attachments sections per spec. |

---

## C) P0 Breakages (must-fix now)

### C1) Deployment failure: boolean default mismatch in migration

- **Symptom (what ops sees)**: Release phase fails; deployment never becomes ready.
- **Evidence**: Postgres error during Alembic upgrade:
  - `DatatypeMismatch: column "is_primary" is of type boolean but default expression is of type integer`
  - DDL shows `is_primary BOOLEAN DEFAULT 0 NOT NULL`
- **Root cause (specific)**:
  - The migration executed in the deployed environment is defining `customer_reps.is_primary` with an integer default (`0`) instead of a Postgres boolean default (`false`).
  - In this workspace, the migration file currently reads:
    - `server_default=sa.text("false")` in `migrations/versions/e4f5a6b7c8d9_add_customer_reps_table.py`
  - Therefore, the runtime failure strongly suggests **artifact mismatch** (an older image/version is being deployed).
- **Minimal fix (lean)**:
  1) Ensure `e4f5a6b7c8d9_add_customer_reps_table.py` uses a Postgres-safe boolean default:
     - `sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false"))`
     - (Optionally) follow with `op.alter_column(..., server_default=None)` if you want to avoid a permanent server default and rely on app default.
  2) Force a **no-cache rebuild** / ensure DO is deploying the commit that contains this exact migration.
  3) Add a tiny release diagnostic (one-time) to print the migration line or package version to confirm the deployed artifact:
     - e.g. in `scripts/release.py` print the first ~40 lines of the migration file before `command.upgrade`.
- **How to verify**:
  - Redeploy; release step should print “Migrations complete.” and exit 0.
  - Confirm in DB:
```sql
SELECT column_default
FROM information_schema.columns
WHERE table_name='customer_reps' AND column_name='is_primary';
```
  - Expected default should be `false` (or NULL if removed).

### C2) Customers page 500

- **Status**: likely masked by deployment failure; must be re-verified after deploy.
- **Known historical root cause**: `AmbiguousForeignKeysError` on `CustomerRep.rep`.
- **Current code state**: in this workspace `CustomerRep.rep` already specifies `foreign_keys=[rep_id]` (good).
- **Verify after deploy**:
  - Login and load `/admin/customers` and `/admin/me`
  - Check logs for any ORM mapper errors.

### C3) Notes broken (“Add note” not working)

- **Status**: likely coupled to customer/ORM issues and UX duplication.
- **Current implementation**:
  - Global modal: `_layout.html` → `/admin/notes/modal/*` and `/admin/notes/create`
  - Dashboard inline: `/admin/sales-dashboard/order-note-form/*` and `/admin/sales-dashboard/order-note`
- **Minimal fix (lean)**:
  - Keep one (recommended: global modal) and remove the other UI entrypoints to prevent future regressions.

### C4) PDF import broken (“no tables found” / label parsing)

- **Evidence**:
  - `Label1.pdf` text extraction includes reversed/garbled segments and Unicode dash variants; naive regex will be brittle.
  - `2025 Sales Orders.pdf` header text extracts, but SKUs/line items are not present in extracted text for many pages, so table/text heuristics fail.
- **Lean direction**:
  - Always store PDFs (already implemented) and mark “needs manual line entry” when extraction fails.
  - Add label-specific parsing + normalization (unicode dash normalization, reversed-text heuristic) to satisfy AC37 without OCR.

### C5) Lot tracking wrong

- **Spec requirement**: 2025+ lots; all-time distribution totals; active inventory = produced − distributed (all-time).
- **Lean direction**:
  - Ensure lot inclusion rules and aggregation are aligned to spec; avoid year-limited subtraction.

---

## D) Data Integrity Audit

### D1) customer_reps table existence (post-migration)
- **Verify**:
```sql
SELECT to_regclass('public.customer_reps');
```

### D2) `is_primary` default correctness
- **Verify**:
```sql
SELECT column_default
FROM information_schema.columns
WHERE table_name='customer_reps' AND column_name='is_primary';
```

### D3) Lot inventory correctness (all-time distributed)
- **Verify** (example lot):
```sql
SELECT lot_number, MIN(ship_date) AS first_ship, MAX(ship_date) AS last_ship, SUM(quantity) AS units_all_time
FROM distribution_log_entries
WHERE lot_number = 'SLQ-05012025'
GROUP BY lot_number;
```

---

## E) Parsing Pipeline Audit (PDF)

### Current pipeline
- `rep_traceability/parsers/pdf.py` tries `extract_tables()` then falls back to `extract_text()` heuristics.
- Routes store PDFs as attachments even on parse fail (good), but extraction expectations in spec are not met for the example PDFs.

### Why it fails (concrete)
- `Label1.pdf`: extracted text is present but contains reversed text / encoding artifacts and Unicode dash variants (`SLQ�05012025`).
- `2025 Sales Orders.pdf`: extracted text contains header anchors but line items are not reliably extractable as text; table extraction returns empty.

### Leanest robust approach
- Treat label PDFs as a separate parse class; focus on tracking + ship-to and normalize Unicode.
- For sales orders, extract headers when possible; store PDFs always; avoid pretending line items were parsed if they’re not extractable.

---

## F) Notes System Audit

- **Key risk**: Two parallel note creation paths.
- **Lean recommendation**: Keep global notes modal only, route all “Add note” actions to `openNotesModal()` and remove/disable inline dashboard note form to reduce bloat and CSRF regressions.

---

## G) UI/UX Lean Polish Recommendations

- Consolidate modal styling into `design-system.css` so Distribution Details, Notes, and Order Details share one readable pattern.
- Add “Attachments” and “Notes” sections to Distribution Details modal (no new analytics).

---

## H) Legacy/Bloat Removal Plan (Decisive)

| File/Module | Action | Why | Verification steps |
|---|---|---|---|
| `legacy/DO_NOT_USE__REFERENCE_ONLY/*.py` | DELETE | Prevent accidental reuse/port | `grep -R \"DO_NOT_USE__REFERENCE_ONLY\" app/eqms -n` |
| Notes UX duplication (dashboard inline + global modal) | REFACTOR (delete one path) | Reduce regression surface | Search for `toggleNoteForm(` and remove UI entrypoints if global modal chosen |
| Any unused PDF parsing helpers or legacy parsers | DELETE/QUARANTINE | Keep parsing lean and testable | grep for imports; confirm only one parser module is used |

---

## I) Developer Fix Plan (Dependency ordered)

### P0 (deployment + stability)
1) **Unblock migrations on Postgres**
   - **Files**: `migrations/versions/e4f5a6b7c8d9_add_customer_reps_table.py`, `scripts/release.py` (optional diagnostic)
   - **AC**: Release step completes migrations successfully; app becomes ready.
   - **Verify**: DO logs show “Migrations complete.” and readiness probe passes.

2) **Force correct artifact deployment**
   - **Owner**: DevOps/Dev
   - **Action**: Ensure DO builds from the commit containing the corrected migration; disable cache for one deploy.
   - **Verify**: Print migration snippet in release logs (temporary) to confirm `server_default false`.

3) **Post-deploy smoke**
   - **Verify**: `/admin/me`, `/admin/customers`, `/admin/sales-dashboard`, `/admin/sales-orders/import-pdf`

### P1 (correctness)
4) Lot tracking: 2025+ lots + all-time distributed subtraction + Active Inventory correctness.
5) PDF parsing: label-specific parser + normalization; sales-order “store even if parse fails” with clear UI messaging.

### P2 (lean UX polish)
6) Remove duplicate note UI path; use one global modal.
7) Consolidate modal CSS and add attachments/notes sections to Distribution Details.

