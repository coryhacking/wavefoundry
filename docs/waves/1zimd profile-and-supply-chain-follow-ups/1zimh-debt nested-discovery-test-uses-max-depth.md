# Nested Discovery Tests Take Their Depth From MAX_DEPTH

Change ID: `1zimh-debt nested-discovery-test-uses-max-depth`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zimd profile-and-supply-chain-follow-ups

## Rationale

A downstream distribution reported that `NestedDiscoveryTests.test_nested_finds_waves_at_depth_one_two_and_three` in `scripts/tests/test_record_paths.py` fails under a profile with `record_paths.MAX_DEPTH` 2. Verified: the test's `_nested()` helper patches only `NESTED`, so the walk keeps the live `MAX_DEPTH`, and the test then expects a wave at depth 3. Both committed profiles (shipped and `second.json`) use 4, so the framework's own runs never see it. Running the file in memory with `MAX_DEPTH` 2 fails that test only; with `MAX_DEPTH` 1 (inside the allowed `MAX_DEPTH_RANGE` of 1 to 8) the two ambiguity tests also fail, because they place a duplicate id at depth 2.

## Requirements

1. **Depth from the live constant.** The nested discovery test builds waves at depths 1, `min(2, MAX_DEPTH)` and exactly `MAX_DEPTH` (deduplicated) and asserts they are all found, plus one wave at depth `MAX_DEPTH + 1` that is not found. It is renamed to say so (for example `test_nested_finds_waves_down_to_max_depth_and_none_beyond`).
2. **Ambiguity tests state their own depth.** `test_duplicate_ids_at_two_depths_are_reported_with_both_paths` and `test_ambiguity_diagnostics_tolerate_a_resolved_path_against_an_unresolved_root` test ambiguity, not the depth bound, so they call `_nested(max_depth=2)` and hold under any `MAX_DEPTH`.
3. **Shipped behaviour unchanged.** `test_default_max_depth_is_four_and_finds_a_depth_four_wave` stays `default_profile_only`; `test_max_depth_bounds_the_walk_and_no_directory_beyond_it_is_visited` keeps its explicit bound of 2. No non-test code changes.
4. **Platforms.** Windows, macOS, Linux and WSL2 behave the same: the test builds short relative folder names in a temporary directory, and depth `MAX_DEPTH + 1` is at most 9 short segments, well inside the Windows path limit.

## Scope

**Problem statement:** three tests in `test_record_paths.py` assume a nesting depth the profile may not have.

**In scope:**

- `NestedDiscoveryTests` in `.wavefoundry/framework/scripts/tests/test_record_paths.py`.

**Out of scope:**

- Other test modules (none failed in the downstream report; a census of every module under every `MAX_DEPTH` is not part of this change).
- Adding a committed profile with a different `MAX_DEPTH`.

## Acceptance Criteria

- [x] AC-1: run in memory with `record_paths.MAX_DEPTH` patched to 1, 2, 3, 4 and 8 before the module loads, every test in `test_record_paths.py` passes or is skipped by `default_profile_only`; the renamed test asserts the depth `MAX_DEPTH + 1` wave is absent.
- [x] AC-2: in a scratch copy, changing `walk_wave_candidates`'s bound from `depth >= roots.max_depth` to `depth > roots.max_depth` fails the renamed test under the shipped `MAX_DEPTH` and under 2.
- [x] AC-3: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Rewrite and rename the nested discovery test to derive its depths from `rp.MAX_DEPTH`.
- [x] Pass `max_depth=2` in the two ambiguity tests.
- [x] Run the file under each `MAX_DEPTH` value in AC-1, the default run, and the AC-2 mutation in a scratch copy.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Depth-portable tests | implementer | readiness | one test file |
| Review | code-reviewer, qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_record_paths.py`

## Affected Architecture Docs

N/A: one test file; no boundary, flow or verification-architecture change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The reported failure, and the sibling failure at depth 1 |
| AC-2 | required | The beyond-depth assertion must discriminate |
| AC-3 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Implemented. `test_nested_finds_waves_at_depth_one_two_and_three` renamed `test_nested_finds_waves_down_to_max_depth_and_none_beyond`: waves at depths 1, `min(2, MAX_DEPTH)` and `MAX_DEPTH` are found and a wave at `MAX_DEPTH + 1` is not; the two ambiguity tests call `_nested(max_depth=2)`. Before: in-memory runs failed 3 tests at `MAX_DEPTH` 1 and 1 at 2. After: 45 tests pass at 1, 2, 3, 4 and 8 (two `default_profile_only` skips off the shipped profile). Mutation `depth >= roots.max_depth` to `>` fails the renamed test at the shipped depth and at 2; with the beyond-depth wave removed the renamed test no longer fails; without `max_depth=2` both ambiguity tests fail at depth 1 | `tests/test_record_paths.py`; scratchpad `1zimd-failing.txt`, `1zimd-mutations.txt` |
| 2026-10-01 | Planned from the downstream report. Verified: `_nested()` passes no `max_depth`, so `patch_layout` keeps the live value (`_values` sets only named keys); `walk_wave_candidates` stops descending at `depth >= roots.max_depth`; in-memory runs of the module fail one test at `MAX_DEPTH` 2 and three at 1 | `record_paths.py`, `tests/record_layout_support.py`, `tests/test_record_paths.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Derive the depths from `MAX_DEPTH` and assert one beyond it | The test then checks the profile's own bound instead of skipping it | Mark the test `default_profile_only`, which would leave a distribution's depth untested; patch an explicit depth of 3, which tests the mechanism but not the profile |
| 2026-10-01 | Fix the two ambiguity tests with an explicit depth of 2 | They test ambiguity; depth 1 is a valid profile value that fails them | Leave them, since no distribution uses depth 1 today |

## Risks

| Risk | Mitigation |
| --- | --- |
| A test that adapts to the constant stops catching a broken walk | The beyond-depth wave must be absent, and AC-2's mutation proves that assertion discriminates |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
