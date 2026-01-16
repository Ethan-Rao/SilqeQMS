## Decisions log

### Included: Flask app factory + session auth

- **Decision**: Use Flask with an app factory and signed session cookies for auth scaffolding.
- **Rationale**: “Boring tech”, minimal dependencies, easy to deploy on DigitalOcean App Platform, matches the platform patterns seen in Rep QMS.

### Included: RBAC primitives (roles + permissions)

- **Decision**: Implement roles and permissions as DB tables with many-to-many relationships.
- **Rationale**: Simple, explicit, auditable access model; supports future module permissions without code rewrites.

### Included: Append-only audit events

- **Decision**: Use a generic `audit_events` table with reason-for-change and request correlation.
- **Rationale**: ISO-aligned audit trail foundation and consistent cross-module logging.

### Included: Storage abstraction (local + S3-compatible)

- **Decision**: Provide a local storage backend and an S3-compatible backend (DigitalOcean Spaces).
- **Rationale**: Keeps dev simple while supporting production-grade object storage patterns.

### Excluded: Rep QMS domain workflows and routes

- **Decision**: Exclude distribution logs, rep portals, tracing workflows, ShipStation sync, customer targeting/caches, and related DB schema.
- **Rationale**: Not reusable; would bloat the new eQMS and risk dragging in incorrect domain assumptions.

### Excluded: Rep QMS data bootstrap/caching systems

- **Decision**: Exclude hospital/doctor cache bootstrapping and any dataset handling.
- **Rationale**: Rep-domain specific and not part of an eQMS platform foundation.

### Deferred: Electronic signatures (Part 11-style)

- **Decision**: Defer advanced e-signature features.
- **Rationale**: Needs explicit requirements and validation planning; starter keeps extension points only.

