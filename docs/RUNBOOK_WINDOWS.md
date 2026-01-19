# Windows Runbook: SilqeQMS Setup & Operations

**Purpose:** Copy/paste PowerShell commands for Ethan to run SilqeQMS locally without guessing.

**Prerequisites:**
- Python 3.12+ installed
- PowerShell (Windows 10/11)

---

## Fresh Clone → Running Server

**Copy/paste this entire block into PowerShell (run from repo root):**

```powershell
# Step 1: Create virtual environment
python -m venv .venv

# Step 2: Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Step 3: Install dependencies
pip install -r requirements.txt

# Step 4: Create .env file (edit values if needed)
$envContent = @"
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///eqms.db
ADMIN_EMAIL=admin@silqeqms.com
ADMIN_PASSWORD=change-me
STORAGE_BACKEND=local
"@
$envContent | Out-File -FilePath .env -Encoding utf8

# Step 5: Run database migrations
alembic upgrade head

# Step 6: Initialize database (seed permissions and admin user)
python scripts\init_db.py

# Step 7: Start the server
python -m flask --app app.wsgi run --port 8080
```

---

## DigitalOcean App Platform (Production) — Required Setup

**Goal:** ensure production uses Postgres, runs migrations, and seeds permissions/admin user **without any local commands**.

### Required Environment Variables (App-level)

- `ENV=production`
- `DATABASE_URL` (from DO managed Postgres connection string)
- `SECRET_KEY` (strong random string, 32+ chars)
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`

### One-time Migration Toggle (Recommended)

Set this temporarily to run migrations/seed on boot:

- `RUN_MIGRATIONS_ON_START=1`

After a successful deploy/migration, remove it (or set to `0`).

### Optional: Release command (If your DO UI supports it)

If you see a “Run command before deploy / release phase” field, set it to:

```powershell
python scripts/release.py
```

**Expected output:**
- Virtual environment created in `.venv/`
- Dependencies installed (Flask, gunicorn, SQLAlchemy, etc.)
- `.env` file created
- Database migrations run successfully
- Admin user created (email: `admin@silqeqms.com`, password: `change-me`)
- Server starts and shows: ` * Running on http://127.0.0.1:8080`

**Open in browser:**
- `http://localhost:8080/auth/login`
- Login with: `admin@silqeqms.com` / `change-me`

---

## Verify It Works

**After server starts, run these checks:**

```powershell
# Check 1: Health endpoint (from another PowerShell window)
curl http://localhost:8080/health
# Expected: {"ok":true}

# Check 2: Database exists
Test-Path eqms.db
# Expected: True

# Check 3: Admin user exists (if you have sqlite3 installed)
sqlite3 eqms.db "SELECT email FROM users WHERE email = 'admin@silqeqms.com';"
# Expected: admin@silqeqms.com

# Check 4: Permissions seeded
sqlite3 eqms.db "SELECT COUNT(*) FROM permissions;"
# Expected: Number > 0 (should have permissions like 'admin.view', 'docs.view', etc.)
```

**Manual browser checks:**
1. Open `http://localhost:8080/`
2. Click "Login" or go to `http://localhost:8080/auth/login`
3. Enter credentials: `admin@silqeqms.com` / `change-me`
4. Should redirect to `/admin` dashboard
5. Verify you can see navigation (if Step 1 implemented: "Distribution Log", "Tracing Reports")

---

## Daily Start (After Initial Setup)

**If virtual environment and database already exist:**

```powershell
# Navigate to repo root (if not already there)
cd C:\Users\Ethan\OneDrive\Desktop\SilqQMS

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start server
python -m flask --app app.wsgi run --port 8080
```

**If port 8080 is in use:**
```powershell
# Option 1: Use different port
python -m flask --app app.wsgi run --port 5000

# Option 2: Kill process on port 8080
$port = 8080
$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($process) {
    Stop-Process -Id $process -Force
    Write-Host "Killed process on port $port"
}
# Then start server again
python -m flask --app app.wsgi run --port 8080
```

---

## Reset Database (Development Only)

**⚠️ WARNING: This deletes all data. Only use in development.**

```powershell
# Stop the Flask server first (Ctrl+C in the terminal running the server)

# Navigate to repo root
cd C:\Users\Ethan\OneDrive\Desktop\SilqQMS

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Delete SQLite database
Remove-Item eqms.db -ErrorAction SilentlyContinue

# Recreate schema
alembic upgrade head

# Re-seed permissions and admin user
python scripts\init_db.py

# Restart server
python -m flask --app app.wsgi run --port 8080
```

**Verify reset:**
```powershell
# Check database file exists
Test-Path eqms.db
# Expected: True

# Check admin user exists
sqlite3 eqms.db "SELECT email FROM users WHERE email = 'admin@silqeqms.com';"
# Expected: admin@silqeqms.com
```

---

## Common Operations

### Update Dependencies

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Reinstall requirements
pip install -r requirements.txt --upgrade
```

### Create New Migration

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Create new migration (replace "description" with actual description)
alembic revision -m "description"

# Apply migration
alembic upgrade head
```

### Check Migration Status

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Show current migration
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic heads
```

### Re-seed Permissions (Without Deleting Data)

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run init script (idempotent - won't duplicate existing permissions/users)
python scripts\init_db.py
```

### View Logs (If Using File Logging)

```powershell
# If logs are written to a file (check app config)
Get-Content app.log -Tail 50  # Last 50 lines
```

---

## Troubleshooting Quick Reference

### Port Already in Use
```powershell
# Find process using port 8080
netstat -ano | findstr :8080

# Kill process (replace <PID> with actual process ID from above)
taskkill /PID <PID> /F

# Or use different port
python -m flask --app app.wsgi run --port 5000
```

### Module Not Found
```powershell
# Ensure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt

# Verify you're in repo root
pwd
# Should show: C:\Users\Ethan\OneDrive\Desktop\SilqQMS
```

### Database Locked
```powershell
# Stop all Flask servers
Get-Process python | Where-Object {$_.Path -like "*SilqQMS*"} | Stop-Process -Force

# Restart server
python -m flask --app app.wsgi run --port 8080
```

### Migration Errors
```powershell
# Check current state
alembic current

# Upgrade to latest
alembic upgrade head

# If stuck, check migration files exist
Get-ChildItem migrations\versions\*.py
```

### Environment Variables Not Loading
```powershell
# Verify .env file exists
Test-Path .env
# Expected: True

# View .env contents (mask passwords)
Get-Content .env | Select-String -Pattern "SECRET_KEY|DATABASE_URL|ADMIN_EMAIL"

# Recreate .env if needed (see "Fresh Clone" section)
```

---

## Production Deployment Checklist (DigitalOcean)

**Before deploying, verify these env vars are set in DO App Platform:**

- [ ] `SECRET_KEY` - Long random string (minimum 32 characters)
- [ ] `DATABASE_URL` - PostgreSQL connection string (not SQLite)
- [ ] `ADMIN_EMAIL` - Initial admin email
- [ ] `ADMIN_PASSWORD` - Strong password (change after first login)
- [ ] `PORT` - Set automatically by DO (app binds to `${PORT:-8080}`)

**Optional (if using Spaces storage):**
- [ ] `STORAGE_BACKEND=s3`
- [ ] `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`
- [ ] `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`

**After deployment:**
- [ ] Run `python scripts/init_db.py` once (via DO console or one-time job)
- [ ] Verify health check at `/health` endpoint
- [ ] Test login with `ADMIN_EMAIL` / `ADMIN_PASSWORD`

---

## File Locations Reference

**Important files:**
- `.env` - Environment variables (create this manually, not in git)
- `eqms.db` - SQLite database (local dev only)
- `alembic.ini` - Alembic configuration
- `migrations/versions/` - Migration files
- `scripts/init_db.py` - Database seed script
- `app/wsgi.py` - Application entry point

**Configuration:**
- `app/eqms/config.py` - Config loading logic
- `Dockerfile` - Production container build
- `requirements.txt` - Python dependencies

**Documentation:**
- `README.md` - Main project README
- `docs/step1_rep_migration/` - Step 1 implementation plan
- `docs/07_DEPLOYMENT_DIGITALOCEAN_CLOUDFLARE.md` - Deployment guide

---

## Quick Command Reference

```powershell
# Start server
python -m flask --app app.wsgi run --port 8080

# Stop server
# Press Ctrl+C in the terminal

# Activate venv
.\.venv\Scripts\Activate.ps1

# Deactivate venv (if needed)
deactivate

# Run migrations
alembic upgrade head

# Seed database
python scripts\init_db.py

# Check Python version
python --version

# Check pip version
pip --version

# List installed packages
pip list
```

---

## Next Steps After Setup

1. **Verify login works** - Go to `http://localhost:8080/auth/login`
2. **Check admin dashboard** - After login, should see `/admin` page
3. **Review Step 1 docs** - See `docs/step1_rep_migration/` for implementation plan
4. **Test manual workflows** - Once Step 1 is implemented, test Distribution Log and Tracing Reports

For implementation details, see:
- [docs/step1_rep_migration/00_STEP1_CHECKLIST.md](docs/step1_rep_migration/00_STEP1_CHECKLIST.md)
- [docs/step1_rep_migration/04_TEST_PLAN.md](docs/step1_rep_migration/04_TEST_PLAN.md)
