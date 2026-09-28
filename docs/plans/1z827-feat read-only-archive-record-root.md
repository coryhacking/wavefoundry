# Read-Only Archive Record Root

Change ID: `1z827-feat read-only-archive-record-root`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-27
Wave: TBD

## Rationale

The RFC "Vocabulary profiles and an optional parent tier" (section 6) asks for a read-only archive of closed records frozen under older names: a fork's rename history, or Wavefoundry's own future renames. Once record names come from a profile (change `1z826`), a repository that switches vocabulary either renames every historical record or loses them from lookup, id-collision scanning and memory backfill. An archive root with its own profile keeps the history readable without rewriting it.

## Requirements

1. `record_paths` gains an optional `ARCHIVE_ROOT`, default unset. When set, it has its own vocabulary profile, declared through the `1z826` profile module as a second named profile. Validation requires that it differs from `WAVES_ROOT` and `PLANS_ROOT` and nests in neither, in either direction.
2. Lookup by id (`wf_get_change`, wave resolution, the dashboard document view) consults the live root first and the archive second, and labels an archive hit as archived.
3. `lifecycle_id` includes archive records in its id-collision scan, and memory backfill reads them as evidence.
4. Nothing writes under the archive root. Every lifecycle writer refuses an archive path with a named diagnostic, and a test proves that by attempting each writer.
5. Live-record lint does not run on the archive; a lint pass only checks that the archive is readable under its profile.

## Scope

**Problem statement:** after a vocabulary change, older records become invisible to lookup, collision scanning and memory.

**In scope:**

- the archive root constant and validation;
- the read paths above;
- the writer refusal;
- lint exemption.

**Out of scope:**

- migration tooling that moves records;
- archive-specific UI beyond the "archived" label.

## Acceptance Criteria

- [ ] AC-1: with no archive root set, behavior is unchanged.
- [ ] AC-2: with an archive root under a second profile, an archived change and wave are found by id and labeled archived, a new id colliding with an archived one is rejected, and memory backfill reads an archived record.
- [ ] AC-3: every lifecycle writer refuses an archive path, and no file under the archive changes during a full lifecycle run in the live root.
- [ ] AC-4: an archive root equal to, inside, or containing a live root refuses to load with a named diagnostic.
- [ ] AC-5: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [ ] `ARCHIVE_ROOT` and its profile binding; validation.
- [ ] Lookup order, id-collision scan and memory backfill.
- [ ] Writer refusal; lint exemption.
- [ ] Tests; `docs/architecture/current-state.md`; the fork guide; CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Archive root | implementer | `1z826` delivered | Needs the profile module |
| Review | combined reviewer | Archive root | Code, QA, architecture |

## Serialization Points

- `.wavefoundry/framework/scripts/record_paths.py`, `.wavefoundry/framework/scripts/lifecycle_id.py`, `.wavefoundry/framework/scripts/memory_backfill.py`, `.wavefoundry/framework/scripts/wf_server/`, `docs/architecture/current-state.md`

## Affected Architecture Docs

`docs/architecture/current-state.md`: a third record root with read-only semantics.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | No change for users who do not opt in |
| AC-2 | required | The feature's purpose |
| AC-3 | required | Read-only is the safety property |
| AC-4 | required | Fail closed on overlapping roots |
| AC-5 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Planned from RFC section 6; depends on `1z826` | RFC |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | A separate change after `1z826` | The archive needs a second profile, which only exists once the profile module does | Bundle into `1z826` |

## Risks

| Risk | Mitigation |
| --- | --- |
| A writer path is missed and writes into the archive | AC-3 exercises every writer and diffs the archive tree |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
