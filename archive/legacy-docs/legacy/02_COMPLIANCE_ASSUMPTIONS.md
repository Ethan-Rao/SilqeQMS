## Audit trail principles

- **Append-only**: audit events are never edited or deleted (only add new events).
- **Attribution**: every meaningful event records who (user), when, and what.
- **Reason-for-change**: controlled changes require a free-text reason (or selected reason code).
- **Event coverage**: at minimum record create/update/release/obsolete, approvals, exports, access/downloads.
- **Correlate requests**: attach a `request_id` for linking multiple events from one action.

## Record revisioning assumptions

- **Controlled docs**: a released revision is immutable; edits create a new revision.
- **Released artifacts**: a released “output” (e.g., DMR/DHR export bundle, label packet) is immutable.
- **Links are stable**: trace links should reference specific revisions, not mutable “latest”.

## Electronic signatures stance (v1)

**Deferred** for v1.

What we do in v1:
- Standard authentication + audit trail
- Approval records with attributed user + timestamp
- Reason-for-change captured for controlled operations

What is deferred:
- Formal “Part 11 style” e-signature flows (two-factor signing, meaning-of-signature prompts, signature manifestations, etc.)

Reason:
- Implementing a robust e-signature system needs careful requirements, validation planning, and often broader security controls. For a minimal v1 starter, we keep the platform clean and leave an explicit extension point.

