## URL conventions

- **Public**: `/`, `/health`
- **Auth**: `/auth/login`, `/auth/logout`
- **Admin shell**: `/admin/*`
- **Modules** (suggested): `/admin/<module_key>/*` or `/modules/<module_key>/*` (pick one and stay consistent)

## API naming (when added)

- JSON APIs under `/api/v1/...`
- Resource naming: plural nouns (`/api/v1/documents`, `/api/v1/capas`)
- Use stable IDs (UUID recommended for externally-referenced entities)

## Error handling

- HTML: render friendly error pages for 403/404/500
- API: consistent JSON errors:
  - `{ "error": { "code": "...", "message": "...", "details": {...} } }`

## UI structure

- Shared layout: `_layout.html`
- Module navigation lives in admin shell
- Avoid embedding business logic in templates; templates should render prepared view models

## Audit + reason enforcement

- Any state-changing endpoint should:
  - require authentication + appropriate permission
  - capture a reason-for-change (form field or structured reason)
  - write an `audit_events` record

