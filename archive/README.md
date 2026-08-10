# Archive

Historical material from Phases 1–3 of the SilqeQMS build (Jan–Aug 2026). Nothing in
here is executed, imported, deployed, or read by the running application.

**Agents working on Phase 4 do not need to read this folder.** It exists so that
decisions and one-off data migrations remain traceable for audit purposes. Start from
`docs/SYSTEM_OVERVIEW.md` instead.

## Contents

| Folder | What it holds |
| --- | --- |
| `phase3/dev-agent-prompts/` | The Phase 3 dev-agent prompt series (P1–P42) and the coordinator log. This is the narrative record of how the system reached its current state. |
| `phase3/dco-editing-guides/` | Editing guides produced for DCO091–DCO096 (released document change orders). The released documents themselves live in `QM Documents/` and in the app. |
| `phase3/scripts/` | One-shot migration and rollout scripts that have already been executed against production: training rollout, CAPA/lot/equipment imports, initial customer rebuilds, document-control import. |
| `legacy-docs/` | Documentation inherited from the pre-eQMS Rep system. |
| `early-planning/` | Original scope, schema drafts, per-feature implementation plans, review notes, and the Step 1 rep-migration plan. |
| `local-only/scripts/` | Retired operator scripts, kept out of git because several embed live production credentials. |

## If you need to resurrect a script

Archived scripts resolve the repo root with `Path(__file__).resolve().parents[1]`,
which was correct when they lived in `scripts/`. From `archive/phase3/scripts/` that
now points one level too shallow, so fix the parent index before running anything.

Treat every archived script as already applied. Re-running an import is the fastest way
to create duplicate production records.
