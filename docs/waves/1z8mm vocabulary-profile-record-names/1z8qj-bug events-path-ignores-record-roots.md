# Review Ledger Path Check Ignores Configured Record Roots

Change ID: `1z8qj-bug events-path-ignores-record-roots`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-27
Wave: 1z8mm vocabulary-profile-record-names

## Rationale

`review_evidence.is_canonical_wave_events_path` decides whether an `events.jsonl` path is a canonical wave review ledger. The callers are `machine_authority.py` and `indexer.py`, which keep raw ledgers out of retrieval. It hard-codes `parts[0] == "docs"`, `parts[1] == "waves"` and a depth of four, and ignores `record_paths` (`WAVES_ROOT`, `NESTED`, `MAX_DEPTH`). A repository that relocates or nests its waves root therefore gets its raw review ledgers indexed. The function is deliberately content-free: it consults no record, so a removed record never admits a raw ledger (wave `1to78`). The fix must keep that property. Found by the readiness review of wave `1z8mm`.

## Requirements

1. The check derives the waves root's relative path, the nesting flag and the depth from `record_paths.unvalidated_record_roots` (pure string handling of the layout constants, no I/O, so resolving it per path is cheap; it never raises, so an invalid layout is judged by its constants rather than refusing retrieval). `root` may be `None`; the relative layout does not depend on it. It accepts `<waves root>/<folder>/events.jsonl` at depth 1 for a flat layout, and at depths 1 through `MAX_DEPTH` for a nested layout.
2. It still reads no record and no file content; the decision stays position-only.
3. Over-excluding the `events.jsonl` of a nested grouping folder is accepted, and the docstring records it.

## Scope

**Problem statement:** relocated or nested waves roots leak raw review ledgers into retrieval.

**In scope:**

- `is_canonical_wave_events_path` and its tests.

**Out of scope:**

- the vocabulary profile (`1z826`, `1z8qi`);
- other layout leaks.

## Acceptance Criteria

- [x] AC-1: the default layout gives the same result as today for every ledger in this repository.
- [x] AC-2: under a relocated `WAVES_ROOT`, and under a nested layout, a ledger at an in-range depth is recognized, and one outside the root or beyond `MAX_DEPTH` is not.
- [x] AC-3: removing a wave's record file does not change the decision for its ledger.
- [x] AC-4: the change's own suites and every test it adds pass, and the documents this change edits validate.

## Tasks

- [x] Derive root and depth from `record_paths`; keep the check content-free.
- [x] Tests for AC-1 to AC-3; CHANGELOG `[Unreleased]` Fixed bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fix | implementer | readiness | Small and independent |
| Review | combined reviewer | Fix | |

## Serialization Points

- `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/tests/`
- `CHANGELOG.md` (shared by the changes in this wave)

## Affected Architecture Docs

`N/A`: a helper stops ignoring the existing record-root owner.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | No change for the default layout |
| AC-2 | required | The fix |
| AC-3 | required | Preserves the wave `1to78` property |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-27 | Implemented: the waves root and depth come from `record_paths.unvalidated_record_roots`, which never raises, so the first draft's fallback to a literal default root was removed (the record-layout census flagged it) | `test_indexer.test_ledger_role_follows_relocated_and_nested_record_roots` (relocated flat, nested in range, beyond `MAX_DEPTH`, outside the root) and `test_ledger_role_reads_no_record` (a removed record file leaves the decision unchanged); all 173 ledgers in this repository keep their role, checked against the pre-change rule by script |
| 2026-09-27 | Split from `1z826` per the readiness review (B4, N7); kept content-free | readiness review |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-27 | Position-only, root from `record_paths` | A record-presence check would reopen the removed-record hole closed in wave `1to78` | Use the record name from the profile |

## Risks

| Risk | Mitigation |
| --- | --- |
| Nested grouping folders' ledgers are over-excluded | Accepted and documented; they are not canonical ledgers |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
