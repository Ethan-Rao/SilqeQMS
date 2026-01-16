## Recommended architecture

**Modular monolith** (single deployable web service) with clear internal module boundaries.

Rationale:
- Small team, small product surface area (1 product family / 3 SKUs)
- ISO alignment benefits from a single source of truth and consistent audit trail
- Avoid microservice operational overhead early

## Module boundaries (domain)

- **Design Controls**
- **Document Control & QMS** (CAPA/NCR/Change Control submodules)
- **PLM**
- **Supplier Management**
- **Manufacturing**
- **Manufacturing File Output**
- **Employee Training**

## Shared platform services (cross-cutting)

- **Auth**: session auth (web UI), optional API tokens later
- **RBAC**: roles + permissions, enforced in routes and service layer
- **Audit**: append-only audit events; reason-for-change on controlled operations
- **Storage**: storage abstraction (local dev + S3-compatible/Spaces in prod)
- **Database**: transactional persistence with migrations (add Alembic when building the real repo)
- **Admin shell**: common navigation/layout for modules

## Suggested internal code structure (within a single service)

- `app/eqms/auth/*`
- `app/eqms/rbac/*`
- `app/eqms/audit/*`
- `app/eqms/storage/*`
- `app/eqms/modules/<module_key>/*`

## Data access pattern

- One DB transaction per request (where appropriate)
- Domain services write through a single access layer so audit+reason enforcement is consistent
- Avoid “fat controllers”; keep logic in module service functions

