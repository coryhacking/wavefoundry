# Roles and Doc Metadata

Owner: Engineering
Status: active
Last verified: 2026-04-28

Defines how canonical docs under `docs/` use frontmatter-style metadata fields.

## Metadata Fields

| Field | Required on | Meaning |
|-------|-------------|---------|
| `Owner:` | All canonical docs | Team or role responsible for keeping this doc accurate. Use `Engineering` for technical docs, a role name for role-specific docs (e.g. `wave-coordinator`), or `N/A` for automatically generated artifacts. |
| `Status:` | All canonical docs | `active` (current and in use), `draft` (not yet final), `deprecated` (replaced by another doc), or `archived` (historical reference only). |
| `Last verified:` | All canonical docs | ISO date (YYYY-MM-DD) of the last human or agent review that confirmed the doc reflects current reality. Used by `docs-gardener` to surface stale docs. |

## Usage Rules

- Every file under `docs/` that is a canonical policy, reference, architecture, or contributing doc should carry all three fields near the top, after the title.
- Machine-generated refreshable artifacts (session-handoff.md, journals, prompt-surface-manifest.json) may omit `Owner:` / `Status:` / `Last verified:` when the generation timestamp is embedded differently — document the exception in the artifact itself.
- `Owner:` names a team or role, not an individual person.
- `Status: deprecated` requires a "Replaced by: `<path>`" note in the body.

## Alignment

This definition is the single source of truth for metadata field semantics across `docs/`. When `docs/contributing/docs-maintenance.md` exists, it cross-references this file rather than redefining these fields.
