## DigitalOcean App Platform deployment

### Recommended approach

- Use **DigitalOcean App Platform** connected to GitHub repo `Ethan-Rao/SilqeQMS`.
- Build using the provided `Dockerfile`.

### App settings

- **Run command**: handled by `Dockerfile` (gunicorn binds to `${PORT:-8080}`)
- **HTTP port**: App Platform sets `PORT`; container listens on that value.
- **Health check**: configure path to `/health` (expects `{ "ok": true }`)

### Required env vars (minimum)

- `SECRET_KEY`: long random secret
- `DATABASE_URL`: Postgres connection string (DigitalOcean managed DB or external)
- `ADMIN_EMAIL`: initial admin seed email (first deploy)
- `ADMIN_PASSWORD`: initial admin seed password (first deploy; rotate after)

Optional (Spaces storage):
- `STORAGE_BACKEND=s3`
- `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`

### Database

- For production use Postgres (DO Managed Database recommended).
- Run the init/seed step once:
  - Easiest: add a one-time “run command” job or temporarily run `python scripts/init_db.py` in a console.
  - `scripts/init_db.py` runs `alembic upgrade head` and then performs an idempotent seed (admin role/user + permissions).

## Cloudflare DNS (authoritative) → DigitalOcean App Platform

Cloudflare remains authoritative for `silqeqms.com`. Do **not** change nameservers.

### Domains to plan for

- **Prod**: `silqeqms.com`
- **Alias**: `www.silqeqms.com` (redirect or alias)
- **Future**: `staging.silqeqms.com`

### DNS record strategy

- In App Platform, add the custom domain(s); DO will provide an app hostname/target.
- In Cloudflare, create:
  - **CNAME** `www` → DO app hostname (**DNS-only** initially)
  - **Apex** `@`:
    - Prefer **CNAME flattening** in Cloudflare (CNAME @ → DO app hostname), or
    - Use DO-provided apex guidance if they require A records (follow DO’s custom domain instructions)

Recommendation: keep Cloudflare proxy **off** (“DNS only”) until the app is stable, then optionally enable proxy if desired.

### Staging suggestion

- Create a separate DO App for staging.
- Map `staging.silqeqms.com` to the staging app.
- Deploy from a `staging` branch (or PR previews if you later choose).

