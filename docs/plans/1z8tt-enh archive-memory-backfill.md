# Memory Backfill From the Read-Only Archive

Change ID: `1z8tt-enh archive-memory-backfill`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-28
Wave: [wave-id or TBD]

## Rationale

Wave `1z8ts` added a read-only archive root (`record_paths.ARCHIVE_ROOT`, read with `vocabulary_profile.ARCHIVE_PROFILE`) that lookup by id and id-collision scanning consult. The original plan (`1z827`) also asked memory backfill to read archived records as evidence, but its readiness review found that backfill assumes the live root throughout, so that part was split out here. Without it, a fork that archives its history loses those records as a source for memory.

## Requirements

1. `memory_backfill.inventory_closed_waves` includes archived waves whose status is closed, read with the archive profile's record filename; its source-containment check (`_canonical_waves_dir`, `_contained_source_file`) accepts the archive root for those rows.
2. Rows distinguish live and archived waves: the row key or schema carries the root, so a live and an archived folder with the same name never share a row.
3. The claim flow that re-resolves a claimed wave (`memory_handlers` via `memory_supply.resolve_wave_dir`, `memory_propose`, `draft_candidates`) resolves an archived row in the archive, and `memory_supply`'s member parsing uses the archive profile for archived waves.
4. Nothing is written under the archive root; evidence references point at archived paths.

## Scope

**Problem statement:** archived closed records are not a memory-backfill source.

**In scope:**

- backfill inventory, containment, row identity and the claim flow for archived waves.

**Out of scope:**

- the archive root and its readers (delivered in `1z8ts`).

## Acceptance Criteria

- [ ] AC-1: with the archive unset, backfill behavior and rows are unchanged.
- [ ] AC-2: with an archive under a second profile, an archived closed wave is inventoried, claimed, drafted from, and completed, with evidence pointing at the archived paths, and the archive tree stays byte-identical.
- [ ] AC-3: a live and an archived wave with the same folder name produce two distinct rows.
- [ ] AC-4: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [ ] Inventory, containment and row identity.
- [ ] Claim-flow resolution and profile-aware parsing.
- [ ] Tests; docs and CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Backfill | implementer | `1z8ts` delivered | Needs a schema or key decision first |
| Review | combined reviewer | Backfill | Code, QA, architecture |

## Serialization Points

- `.wavefoundry/framework/scripts/memory_backfill.py`, `.wavefoundry/framework/scripts/memory_supply.py`, `.wavefoundry/framework/scripts/wf_server/`, `.wavefoundry/framework/scripts/tests/`

## Affected Architecture Docs

`docs/architecture/layering-rules.md`: the archive paragraph's note that memory backfill does not read the archive.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | No change for users who do not opt in |
| AC-2 | required | The feature's purpose |
| AC-3 | required | Row identity must not merge history |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Split from `1z827` by its readiness review (finding F4): the claim flow re-resolves waves in the live root, `memory_supply` parses with the live profile at import, and backfill rows are keyed by folder name | `1z827` readiness review |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | A separate change after `1z8ts` | Backfill touches its own schema and claim flow; bundling it would have doubled `1z827` | Bundle into `1z827` |

## Risks

| Risk | Mitigation |
| --- | --- |
| A schema change to backfill rows needs a migration | Decide the key before implementation; AC-1 pins unchanged rows when the archive is unset |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
