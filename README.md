# SilqeQMS

**SilqeQMS** is the electronic quality management system and business-operations platform for
Silq Technologies, built as a **modular monolith** using Flask + SQLAlchemy.

> **Start here:** [`docs/SYSTEM_OVERVIEW.md`](docs/SYSTEM_OVERVIEW.md) is the authoritative
> description of the system — architecture, module map, the sales-order/invoice domain,
> deployment procedure, and known issues. This README covers local setup and troubleshooting
> only.

Platform foundations:

- Auth/session + RBAC (roles and permissions, seeded by `scripts/init_db.py`)
- Append-only audit events
- Storage abstraction (local filesystem in dev, DigitalOcean Spaces in production)
- Admin shell hosting every module UI under `/admin/*`
- Alembic migrations for database versioning

Feature modules: document control, rep traceability (sales orders, distribution log, tracing
reports, sales dashboard), customer profiles, ShipStation sync, NRE projects, purchasing,
equipment, suppliers, supplies, manufacturing, CAPAs/NCRs, training, document libraries, and
a temporary auditor portal.

---

## Quick Setup (Windows PowerShell)

### Prerequisites

- Python 3.12+ installed
- PowerShell (Windows 10/11)

### Step-by-Step Setup

**1. Create virtual environment:**
```powershell
python -m venv .venv
```

**2. Activate virtual environment:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**3. Install dependencies:**
```powershell
pip install -r requirements.txt
```

**4. Create environment file:**
```powershell
# Copy this template or create .env manually:
$envContent = @"
SECRET_KEY=your-secret-key-here-change-this-in-production
DATABASE_URL=sqlite:///eqms.db
ADMIN_EMAIL=admin@silqeqms.com
ADMIN_PASSWORD=change-me
STORAGE_BACKEND=local
"@
$envContent | Out-File -FilePath .env -Encoding utf8
```

Or manually create `.env` with:
```
SECRET_KEY=your-secret-key-here-change-this-in-production
DATABASE_URL=sqlite:///eqms.db
ADMIN_EMAIL=admin@silqeqms.com
ADMIN_PASSWORD=change-me
STORAGE_BACKEND=local
```

**5. Run database migrations:**
```powershell
alembic upgrade head
```

**6. Initialize database (seed permissions and admin user):**
```powershell
python scripts\init_db.py
```

**7. Start the server:**
```powershell
python -m flask --app app.wsgi run --port 8080
```

**8. Access the application:**
- Landing page: `http://localhost:8080/`
- Health check: `http://localhost:8080/health`
- Login: `http://localhost:8080/auth/login`
- Admin dashboard: `http://localhost:8080/admin` (requires login)

**9. First login:**
- Email: Use the value from `ADMIN_EMAIL` in your `.env` file (default: `admin@silqeqms.com`)
- Password: Use the value from `ADMIN_PASSWORD` in your `.env` file (default: `change-me`)
- After login, you'll be redirected to `/admin` dashboard

---

## Where to Click (Rep Traceability)

After logging in as admin, navigate to:

### Distribution Log
- **URL:** `http://localhost:8080/admin/distribution-log`
- **What it does:** Browse, create, edit, and export device distribution entries
- **Key actions:**
  - **[Manual Entry]** - Create a new distribution entry manually
  - **[Import CSV]** - Bulk import distributions from CSV file
  - **[Edit]** - Click on any row to edit an entry
  - **[Export]** - Download filtered entries as CSV

### Tracing Reports
- **URL:** `http://localhost:8080/admin/tracing`
- **What it does:** Generate CSV reports from Distribution Log for regulatory compliance
- **Key actions:**
  - **[Generate]** - Create a new tracing report (select month, rep, source, SKU filters)
  - **[View]** - See report details and upload approval evidence
  - **[Download]** - Download the generated CSV report

### Approval Evidence
- **Where:** On any tracing report detail page (`/admin/tracing/<id>`)
- **What it does:** Upload `.eml` files (email exports) as proof of approval
- **Key actions:**
  - **Upload .eml** - Choose a `.eml` file and upload (links to the report)
  - **[Download]** - Download uploaded approval `.eml` files

---

## Environment Variables

### Minimum Required (Production)

These **must** be set for production deployment:

```
SECRET_KEY=long-random-secret-string-minimum-32-characters
DATABASE_URL=postgresql://user:pass@host:port/dbname
ADMIN_EMAIL=admin@silqeqms.com
ADMIN_PASSWORD=strong-password-here
ENV=production
```

**Note:** DigitalOcean App Platform sets `PORT` automatically, and the app binds to `${PORT:-8080}`.

### DigitalOcean: Migrations + Seed (No local commands)

DigitalOcean App Platform does **not** automatically run Alembic migrations unless you wire it.

This repo ships:
- `scripts/release.py` (runs `alembic upgrade head` + seeds permissions/admin idempotently)

**Recommended approach (Release / Pre-deploy command):**
- In DigitalOcean App Platform, set the component **Pre-deploy / Release command** to:
  - `python scripts/release.py`

**Manual approach (via DO Console):**
- If the release command isn't available, run migrations manually via the DigitalOcean Console:
  ```bash
  alembic upgrade head
  python scripts/init_db.py
  ```

**Note:** The `RUN_MIGRATIONS_ON_START` toggle has been disabled in the code due to deployment issues with Gunicorn workers. Use the release command or manual approach instead.

### Optional (Storage - S3/Spaces)

If using DigitalOcean Spaces or S3-compatible storage:

```
STORAGE_BACKEND=s3
S3_ENDPOINT=nyc3.digitaloceanspaces.com
S3_REGION=nyc3
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
```

### Development Defaults

If `.env` is missing or variables are unset, the app uses these defaults:
- `DATABASE_URL=sqlite:///eqms.db` (SQLite for local dev)
- `STORAGE_BACKEND=local` (local filesystem storage)
- `SECRET_KEY=change-me` (CHANGE THIS IN PRODUCTION)

---

## Troubleshooting

### 1. Port Already in Use

**Error:** `OSError: [Errno 98] Address already in use` or `Address already in use`

**Solution:**
```powershell
# Find what's using port 8080:
netstat -ano | findstr :8080

# Kill the process (replace PID with actual process ID):
taskkill /PID <PID> /F

# Or use a different port:
python -m flask --app app.wsgi run --port 5000
```

### 2. Missing Environment Variables

**Error:** `KeyError: 'SECRET_KEY'` or database connection fails

**Solution:**
- Ensure `.env` file exists in the repo root
- Verify all required variables are set (see "Environment Variables" section above)
- Check file encoding (should be UTF-8)

### 3. Migration Errors

**Error:** `alembic.util.exc.CommandError: Can't locate revision identified by '...'`

**Solution:**
```powershell
# Check current migration state:
alembic current

# Upgrade to latest:
alembic upgrade head

# If still failing, reset database (DEV ONLY - deletes all data):
Remove-Item eqms.db -ErrorAction SilentlyContinue
alembic upgrade head
python scripts\init_db.py
```

### 4. Permission Denied (403) on Admin Routes

**Error:** You see "403 Forbidden" when accessing `/admin/*` routes

**Solution:**
- Ensure you're logged in (`/auth/login`)
- Verify your user has the `admin` role with all permissions
- Check database: `SELECT * FROM user_roles WHERE user_id = <your_user_id>;`
- Re-run seed script: `python scripts\init_db.py`

### 5. Database Locked (SQLite)

**Error:** `sqlite3.OperationalError: database is locked`

**Solution:**
- Close any other processes accessing `eqms.db`
- Stop the Flask server and restart
- If persistent, check for hanging database connections

### 6. Module Import Errors

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solution:**
- Ensure virtual environment is activated: `.\.venv\Scripts\Activate.ps1`
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python path: Run commands from repo root directory

### 7. Alembic Can't Find Models

**Error:** `alembic.util.exc.CommandError: Target database is not up to date`

**Solution:**
```powershell
# Ensure models are imported in app/eqms/models.py
# Run upgrade:
alembic upgrade head

# Verify migration status:
alembic current
```

### 8. CSV Import Fails

**Error:** CSV import shows validation errors or "invalid SKU"

**Solution:**
- Verify CSV columns match expected format (case-sensitive):
  - Required: `Ship Date`, `Order Number`, `Facility Name`, `SKU`, `Lot`, `Quantity`
- Check SKU values are one of: `211810SPT`, `211610SPT`, `211410SPT`
- Check Lot format: `SLQ-#####` (e.g., `SLQ-12345`)
- Ensure dates are `YYYY-MM-DD` format

---

## Docker

### Build and Run Locally

```powershell
docker build -t silqe-eqms .
docker run --rm -p 8080:8080 --env-file .env silqe-eqms
```

**Note:** Docker uses `gunicorn` for production-grade serving (see `Dockerfile`). For local development, `flask run` is sufficient.

---

## Deployment (DigitalOcean App Platform + Cloudflare DNS)

See [docs/07_DEPLOYMENT_DIGITALOCEAN_CLOUDFLARE.md](docs/07_DEPLOYMENT_DIGITALOCEAN_CLOUDFLARE.md) for:
- DigitalOcean App Platform setup
- Environment variable configuration
- Cloudflare DNS configuration
- Database setup (PostgreSQL)

**Quick deployment checklist:**
1. Set required env vars in DO App Platform (see "Minimum Required" above)
2. Build using provided `Dockerfile` (gunicorn binds to `${PORT:-8080}`)
3. Configure health check path: `/health`
4. Run `python scripts/init_db.py` once (via console or one-time job) to seed permissions

---

## Database Reset (Development Only)

**⚠️ WARNING:** This deletes all data. Only use in development.

```powershell
# Stop the Flask server first!

# Delete SQLite database:
Remove-Item eqms.db -ErrorAction SilentlyContinue

# Recreate schema:
alembic upgrade head

# Re-seed permissions and admin user:
python scripts\init_db.py
```

---

## Project Structure

```
SilqQMS/
├── app/                          # Application code
│   ├── eqms/
│   │   ├── modules/              # Feature modules (one folder per module)
│   │   ├── templates/            # Jinja2 templates
│   │   ├── static/               # design-system.css
│   │   ├── auth.py               # Authentication
│   │   ├── rbac.py               # Role-Based Access Control
│   │   ├── audit.py              # Audit trail
│   │   ├── storage.py            # Storage abstraction
│   │   └── ...
│   └── wsgi.py                   # WSGI entry point
├── migrations/                   # Alembic migrations (single linear chain)
├── tests/                        # pytest suite
├── scripts/                      # Operational scripts (init_db.py, release.py, backfills)
├── docs/                         # Documentation — start with SYSTEM_OVERVIEW.md
├── archive/                      # Phase 1-3 history; not used by the app
├── working-files/                # Local scratch: exports, documents staged for upload
├── Dockerfile                    # Production container
├── requirements.txt              # Python dependencies
└── alembic.ini                   # Alembic configuration
```

Top-level folders such as `QM Documents/`, `DCOs/`, `CAPAs/`, `DHF/`, and `QMSInProcess/` are
the operator's native document workspace, synced by OneDrive and mostly git-ignored. Leave
their structure alone.

---

## Next Steps

- [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) — architecture, modules, domain model,
  deployment, known issues
- [docs/RUNBOOK_WINDOWS.md](docs/RUNBOOK_WINDOWS.md) — copy/paste Windows runbook
- [docs/07_DEPLOYMENT_DIGITALOCEAN_CLOUDFLARE.md](docs/07_DEPLOYMENT_DIGITALOCEAN_CLOUDFLARE.md) — hosting and DNS
- [archive/README.md](archive/README.md) — where the Phase 1-3 record went

---

## Constraints & Design Decisions

### Standing Constraints

- **Admin shell only**: all functionality lives under `/admin/*` (plus `/auditor/*` for the
  temporary auditor portal). There is no customer- or rep-facing surface.
- **Tracing reports are CSV only**: no PDF generation.
- **Admin has full editability**: RBAC is enforced, but the admin role can do everything; no
  multi-step approval gates.
- **Outbound email is report-only**: the Weekly Brief digest sends through Resend. Document
  approvals are still evidenced by uploaded `.eml` files, not generated mail.

### Technical Stack

- **Framework**: Flask (modular monolith)
- **Database**: SQLite (dev) / PostgreSQL (production)
- **Migrations**: Alembic
- **Server**: Flask dev server (local) / Gunicorn (production Docker)
- **Storage**: Local filesystem (dev) / S3-compatible (production)

---

## References

- **System overview:** [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md)
- **Architecture notes:** [docs/01_ARCHITECTURE_OVERVIEW.md](docs/01_ARCHITECTURE_OVERVIEW.md)
- **Compliance assumptions:** [docs/02_COMPLIANCE_ASSUMPTIONS.md](docs/02_COMPLIANCE_ASSUMPTIONS.md)
- **Deployment:** [docs/07_DEPLOYMENT_DIGITALOCEAN_CLOUDFLARE.md](docs/07_DEPLOYMENT_DIGITALOCEAN_CLOUDFLARE.md)
- **Auditor portal:** [docs/AUDITOR_PORTAL_OPERATOR_GUIDE.md](docs/AUDITOR_PORTAL_OPERATOR_GUIDE.md)

Historical Phase 1-3 specs (original rep-migration master spec, minimal schema, UI map,
per-feature plans) are under `archive/early-planning/`.
