# Silq eQMS — System Overview

Authoritative orientation document. Current as of the start of **Phase 4** (August 2026).
If anything here conflicts with older files in `docs/` or `archive/`, this document wins.

---

## 1. What the system is

Silq eQMS is the electronic quality management system and business-operations platform for
Silq Technologies (Class II urological catheters — ClearTract Foley, plus a suspension
sub-assembly). It replaced a FileHold-based EDMS plus a pile of Excel logs.

It is a **modular monolith**: one Flask + SQLAlchemy application, one Postgres database,
one deployable container. Modules are separated by directory and blueprint, not by service
boundary. There is no separate frontend build — templates are server-rendered Jinja2 with a
single hand-written stylesheet.

It serves two purposes that are worth keeping distinct in your head:

1. **Regulated QMS records** — controlled documents, DCOs, training, CAPAs/NCRs, equipment
   calibration and PM, suppliers, manufacturing lots, distribution traceability. These carry
   FDA 21 CFR 820 / ISO 13485 obligations. Audit trails and record integrity matter more
   than convenience.
2. **Commercial operations** — customers, sales orders, the sales dashboard, NRE projects,
   purchasing, payment and invoice tracking. This half is a business tool. It is where
   Phase 4 work is focused, and it is far more forgiving of iteration.

The validation project covering the system itself is **DC.SLQ002** (working documents in
`QMSInProcess/`). Phase 3 design review has been held; Phase 4 changes continue under that
project, so material changes still need design/validation traceability.

### Users

Roughly seven people. One administrator (Ethan Rao, also the Management Representative),
five to six staff on read-mostly access, plus a temporary external auditor account.
Everything runs behind login at `/admin/*`; there is no public or customer-facing surface.

---

## 2. Deployment topology

| Concern | Implementation |
| --- | --- |
| Host | DigitalOcean App Platform, Docker component built from `Dockerfile` |
| Server | gunicorn, `--preload`, 2 workers, 60s timeout, binds `${PORT:-8080}` |
| Database | DigitalOcean Managed Postgres (`DATABASE_URL`) |
| File storage | DigitalOcean Spaces, S3-compatible (`STORAGE_BACKEND=s3`) |
| DNS / TLS | Cloudflare, domain `silqeqms.com` |
| Outbound email | Resend, sender `reports@silqeqms.com` |
| Migrations + seed | `python scripts/release.py` as the App Platform **pre-deploy command** |
| Health checks | `/health`, `/healthz`, and `/health/deep` (touches the DB) |
| CI | None. There is no GitHub Actions workflow — tests run locally, deploys trigger on push to `main`. |

The image also installs LibreOffice (Writer + Calc) because the auditor portal converts
Word/Excel to PDF on the fly. That is the single largest contributor to build time.

Local development uses SQLite (`sqlite:///eqms.db`) and local-filesystem storage. **Some
migrations do not run cleanly on SQLite** (a known Phase 3 issue with `NOW()` and
`ON CONFLICT` in an ancestor revision). Postgres is the only supported target for
`alembic upgrade head`; locally, prefer running the test suite over rebuilding the DB.

---

## 3. Repository layout

```
SilqQMS/
├── app/eqms/              Application code (see §4)
├── migrations/            Alembic revisions — single linear chain
├── tests/                 pytest suite (~350 tests)
├── scripts/               Operational scripts still relevant to current work
├── docs/                  Current documentation + QMS readable-text corpus
├── archive/               Phase 1-3 history. Not read by the app. Ignore it.
├── working-files/         Local scratch: data exports, documents staged for upload
├── eQMS_Upload_Staging/   Legacy import staging. `reconciliation/DCO_Log_v2.csv` is
│                          still read at runtime by the DCO log module.
├── Auditor Files/         Empty mount point for the auditor portal. The 2026 audit set was
│                          archived off-repo — see `Auditor Files/README.md`
├── Dockerfile, alembic.ini, requirements.txt, .env.example
└── <QMS document folders> QM Documents/, DCOs/, CAPAs/, DHF/, Equipment/, Manufacturing/,
                           Purchasing/, Suppliers/, Supplies/, RiskManagement/, NCMR/,
                           Audits/, Distribution/, QMSInProcess/, EmployeeTraining/, …
```

The top-level QMS document folders are the operator's own native filesystem workspace, kept
in sync by OneDrive and mostly git-ignored. **Do not reorganise, rename, or delete them.**
They are how Ethan works with source documents outside the app.

---

## 4. Application architecture

`app/eqms/__init__.py` is the app factory. It loads config from the environment, initialises
the SQLAlchemy engine and request-scoped session, installs auth/CSRF/audit hooks, and
registers every blueprint.

Cross-cutting pieces:

| File | Responsibility |
| --- | --- |
| `config.py` | Environment-driven config loading |
| `db.py` | Engine, request-scoped session, teardown |
| `models.py` | `User`, `Role`, `Permission`, `AuditEvent`, declarative `Base` |
| `auth.py` | Session login/logout, `load_current_user`. Email lookup is case-insensitive. |
| `rbac.py` | `require_permission`, `require_any_permission`, `user_has_permission` |
| `audit.py` | Append-only audit events |
| `storage.py` | Storage abstraction — local filesystem or S3/Spaces |
| `security.py` | CSRF token issue + validation |
| `search.py` | Cross-module search |
| `admin.py` | Admin shell, dashboard, Admin Tools/diagnostics, Reports incl. Weekly Brief email |

Every feature module lives in `app/eqms/modules/<name>/` with `admin.py` (blueprint +
routes), `models.py`, and often `service.py` for business logic. Templates are in
`app/eqms/templates/admin/<module>/`.

### Module map

| Module | Mounted at | Purpose |
| --- | --- | --- |
| `document_control` | `/admin/modules/document-control` | Controlled documents, revisions, release workflow, DCO log. `DocumentRevision.dco_number` drives automatic training qualification on release. |
| `rep_traceability` | `/admin` | Sales orders (incl. PDF import/parsing), distribution log, tracing reports, approval `.eml` evidence, sales dashboard |
| `customer_profiles` | `/admin` | Customers, reps, notes. Catheter customers are **facility-level**, identified by Ship-To address. |
| `shipstation_sync` | `/admin` | Pulls shipments from ShipStation into distribution log entries |
| `nre_projects` | `/admin/nre-projects` | NRE (non-recurring engineering) projects grouped by customer, invoice tracker, NRE dashboard |
| `purchasing` | `/admin` | Purchase orders, Upcoming Payments (with line items), Invoices Received |
| `equipment` | `/admin` | Equipment master list, calibration/PM scheduling, documents |
| `suppliers` | `/admin` | Approved supplier list, documents, equipment links |
| `supplies` | `/admin` | Materials/consumables, Pathway inventory table |
| `manufacturing` | `/admin/manufacturing` | Production lots (suspension + ClearTract), materials, equipment usage, QA disposition |
| `capas` | `/admin` | CAPAs, with the NCR/NCMR accordion nested below |
| `training` | `/admin` | `My Training` (own queue + acknowledge) and Training Administration (matrix, per-user records, annual effectiveness reviews) |
| `admin_docs` | `/admin` | Generic folder/file document libraries backed by Spaces (Training Records, NRE Projects, Quality Planning, Design & Development, etc.) — configured by a `LIBRARIES` map |
| `auditor_portal` | `/auditor` | Temporary read-only external-auditor portal, gated by `AUDITOR_PORTAL_ENABLED` |

### RBAC

Permissions are `<area>.<action>` strings (`docs.release`, `sales_orders.import`,
`training.manage`, …), seeded idempotently by `scripts/init_db.py`. Three roles:

- **admin** — everything.
- **staff** — read-mostly, plus `training.view` so they can acknowledge their own training.
  Staff must not reach Training Administration; they are redirected to `My Training`.
- **auditor** — `auditor_portal.access` only.

New routes need an explicit `@require_permission(...)`. New permissions must be added to
`init_db.py` seeding, or they will not exist in production after deploy.

---

## 5. The Phase 4 domain: order → shipment → invoice

This is the chain Phase 4 will overhaul, so it is worth understanding in detail. It is also
the most subtle part of the system, because a single sales order does not map cleanly to a
single anything else.

**`SalesOrder`** (`rep_traceability/models.py`) is the source of truth for customer identity
and order assignment. Beyond `order_number` / `order_date` / `customer_id` / `source`
(`shipstation` | `manual` | `csv_import` | `pdf_import`), it carries fields added during
Phase 3:

- `order_amount`, `po_reference`, `order_description` — best-effort extraction from the
  sales-order PDF. On re-import these are **fill-nulls-only**; a re-import must never
  clobber a value already present.
- `invoice_date` — manually entered by the operator; never auto-filled.
- `nre_invoice_status` — preset dropdown (`Pending Invoice`, `50% Invoiced`,
  `100% Invoiced`, `Payment Received`) driving the NRE dashboard's "Total Amount Invoiced".
  Independent of the lifecycle `status` column.
- `sold_to_*` / `ship_to_*` address columns captured per order from the PDF.

**How records come into being:**

1. Ethan uploads a sales-order PDF. The parser splits pages per order, extracts customer,
   addresses, amount, PO reference and description, then upserts `SalesOrder` +
   `SalesOrderLine` and creates or matches a `Customer`.
2. ShipStation sync pulls shipments and creates `DistributionLogEntry` rows, linking to a
   `SalesOrder` by normalised order number. **One sales order can produce several
   distribution rows** (multi-shipment orders) — this is legitimate and must not be
   deduplicated away.
   Order matters: **import sales-order PDFs before running ShipStation sync**, so customer
   records exist to match against. Packing-slip bulk import matches on tracking number or
   normalised order number; a slip can also be attached or replaced per shipment from the
   distribution log modal. `PyPDF2` must stay in `requirements.txt` for multi-page PDF
   splitting to work in the deployed image.
3. Classification is implicit rather than a stored flag: a sales order with linked catheter
   distributions is a catheter order; one without is treated as **NRE**. This inference is
   the root of most historical data problems — a catheter order whose distribution failed to
   match silently becomes a phantom NRE project with a phantom customer.

**Customer identity differs by business line:**

- **Catheter** customers are *facilities*, keyed on Ship-To `address1 + city + state + zip`
  (deliberately ignoring `address2`, so different floors/suites of one building collapse
  into one facility), with the normalised facility name as tie-breaker. A distributor such
  as Marathon Medical that pays for many hospitals therefore yields one facility customer
  per distinct Ship-To — not one customer named "Marathon".
- **NRE** customers stay company-level.

**Money is tracked in three separate, manually-maintained places** — none of them derive
from each other, which is precisely the fragmentation Phase 4 is meant to address:

| Where | Model | Meaning |
| --- | --- | --- |
| Purchasing → Upcoming Payments | `PaymentEntry` + `PaymentLineItem` (+ attachments) | Money Silq expects to pay out. Parent amount is manual; line items are informational and never auto-summed. |
| Purchasing → Invoices Received | `InvoiceReceivedEntry` (+ attachments) | Invoices actually received. No line items. |
| NRE → Upcoming NRE Invoice Tracker | `NREProjectEntry` (+ attachments) | Free-form ledger of NRE invoices Silq expects to send. Free-text status. |

The Weekly Brief email (`/admin/reports/weekly-brief`) renders the NRE tracker, the payments
table (with Invoices Received merged in and flagged `(Received)`), and a current-quarter
sales snapshot, then sends via Resend.

---

## 6. Deploying

Deployment is push-to-`main`. There is no CI gate, so the local checks below **are** the gate.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q                      # expect ~350 passed, 1 skipped
python -m alembic heads                  # must print exactly ONE head
python -c "import app.wsgi"              # import smoke test
git add -A
git commit -m "..."
git push origin main
```

DigitalOcean then builds the image, runs `python scripts/release.py` as the pre-deploy step
(`alembic upgrade head`, then idempotent permission/role/admin seeding), and rolls the
component. `release.py` refuses to run against a SQLite `DATABASE_URL` when `ENV=production`.

### Migration rules

- One migration per change set, `down_revision` pointing at the current head. **Never leave
  two heads** — the release command fails and the deploy aborts mid-way.
- Additive changes only on a live database: new nullable columns, new tables, backfill
  afterwards. Adding a `NOT NULL` column requires a server default.
- Postgres is the deploy target. Do not rely on SQLite-specific behaviour, and don't be
  surprised when a fresh local SQLite build fails at an old revision.
- New permissions go into `scripts/init_db.py` seeding in the same change set.

### If a deploy fails

Read the DigitalOcean build and deploy logs first, and distinguish the phase:

- **Build failure** — usually `requirements.txt` or the LibreOffice apt layer.
- **Pre-deploy (release) failure** — almost always Alembic: multiple heads, a missing
  revision, or a migration that is invalid against real Postgres data. The previous version
  keeps serving, so fix forward and push again.
- **Health-check failure** — the app booted but `/health` did not answer. Check for an
  import-time error (`--preload` means an exception at import kills every worker).

Ethan cannot see the build banner from his side; report deploy status explicitly, and
confirm green before telling him to review.

---

## 7. Conventions and guardrails

- **URLs:** always `url_for(...)`, including inside inline JavaScript. Hardcoded
  `/admin/...` strings have broken repeatedly when blueprints moved.
- **CSRF:** state-changing routes require the token. The working pattern in existing
  templates is an inline `{{ csrf_token }}` in the form or fetch body.
- **Storage:** go through `app/eqms/storage.py`. To write bytes, the method is
  `storage.put_bytes` (there is no `storage.put`). Deleting a record that owns an
  attachment must also delete the blob.
- **Audit:** record audit events for state changes on regulated records.
- **Tests:** every change set adds tests under `tests/`, named for the work item.
- **Language in the UI:** short, plain, list-like. No document numbers in user-facing labels
  unless the number is genuinely what the user is looking for. No self-describing subtitles
  ("Full library — all folders shown on one page" is exactly what not to write).
- **Windows/PowerShell:** the operator is on PowerShell. `&&` chaining and bash heredocs do
  not work; use `;` and separate commands. Avoid non-ASCII characters in script output —
  arrows and em-dashes have caused `UnicodeEncodeError` crashes mid-run.
- **Operator scripts** that embed live credentials must be added to `.gitignore`
  individually, and support a dry-run mode by default with an explicit `--execute` flag.

---

## 8. Known issues and open decisions

- **The auditor portal cannot currently serve documents, by design.** The 2026 audit set
  (683 files, ~649 MB) was baked into git and therefore into every Docker build. On
  2026-08-10 it was archived off-repo, the folder contents were git-ignored and
  Docker-ignored, and only the folder skeleton remains. Ethan wants to reuse the portal for
  a future audit with new documents, so **reworking it to read from DigitalOcean Spaces (the
  way `admin_docs` libraries already do) is an open Phase 4 candidate.** Dropping files into
  `Auditor Files/` will not work until then. A manifest of the archived 2026 set is committed
  at `docs/AUDITOR_PORTAL_2026_FILE_MANIFEST.csv`, and the portal access log is preserved in
  `auditor_access_events`.
- **The ~649 MB still exists in git history.** Removing it from `HEAD` stopped it entering
  new builds, but a full clone still fetches the old blobs. Shrinking the repository would
  require rewriting history and force-pushing `main`, which has not been done.
- **The local `.env` Spaces credentials are stale** (`InvalidAccessKeyId` on bucket
  listing), so storage-backed operations fail from a dev machine even though production is
  healthy. Refresh the keys before running any script that writes to Spaces.
- **SQLite migration chain is broken** at a Phase 3 ancestor revision. Postgres only.
- **No CI.** Nothing verifies a push except discipline.
- **Sales-order → distribution matching is best-effort.** Failures degrade silently into
  phantom NRE customers. Phase 4 should make this explicit and reviewable.
- **`eQMS_Upload_Staging/reconciliation/DCO_Log_v2.csv` is read at runtime** by
  `document_control/dco_log.py`, so that folder cannot simply be deleted.
