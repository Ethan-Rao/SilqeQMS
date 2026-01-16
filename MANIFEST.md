# MANIFEST (eqms_starter)

## Included (clean, reusable platform foundation)

- `app/wsgi.py`: WSGI entrypoint (`create_app()` factory)
- `app/eqms/config.py`: env-driven configuration
- `app/eqms/db.py`: SQLAlchemy engine/session (request-scoped)
- `app/eqms/models.py`: generic `User`, `Role`, `Permission`, `AuditEvent`
- `app/eqms/auth.py`: session-based auth scaffolding (login/logout, decorators)
- `app/eqms/rbac.py`: RBAC primitives (`require_permission`)
- `app/eqms/audit.py`: append-only audit event helper
- `app/eqms/storage.py`: storage abstraction (local + optional S3-compatible/Spaces)
- `app/eqms/admin.py`: generic admin UI shell (navigation frame)
- `app/eqms/routes.py`: `/` and `/health`
- `app/eqms/templates/*`: minimal UI shell + login + landing
- `app/eqms/static/design-system.css`: minimal styling
- `scripts/init_db.py`: initialize DB + seed admin user/roles
- `tests/test_smoke.py`: minimal smoke tests
- `docs/*.md`: scope, architecture, module specs, deployment

## Explicitly excluded (rep-specific / not reusable)

The following Rep QMS concepts are **intentionally not copied**:

- Distribution logs, rep portals, tracing reports/workflows, receiving inspections, ShipStation sync, customer database quirks, targeting caches, and related admin pages/routes.
- Any SQL/migrations embedding rep-domain schema (customers, shipments, distributions, etc.).
- Any dataset bootstrap/caching subsystems (hospital/doctor targeting caches).

### Reasons

- They are **domain-specific** to Rep operations and would create “bloat” and carry compliance risk if reused incorrectly.
- They mix operational workflows with platform concerns; the new eQMS needs clean module boundaries.

## Known tech debt not brought forward

- Rep QMS mixes platform concerns and domain workflows in large single-file modules; the starter is intentionally modularized for maintainability.
- Rep QMS contains environment examples/scripts referencing third-party credentials; starter keeps secrets out of repo via `.env`.

