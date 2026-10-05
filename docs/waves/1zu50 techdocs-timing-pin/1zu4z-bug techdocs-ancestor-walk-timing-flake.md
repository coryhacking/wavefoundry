# Pin The Techdocs Ancestor-Walk Skip By Match Count Instead Of Wall Clock

Change ID: `1zu4z-bug techdocs-ancestor-walk-timing-flake`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-04
Wave: 1zu50 techdocs-timing-pin

## Rationale

`test_a_segment_local_pattern_skips_the_ancestor_walk` in `test_techdocs_audit_lib.py` asserts that one `excluded()` call finishes in under 0.15 s. During the wave 1zrak receipt run it measured 0.163 s under full parallel load and failed the whole suite, then passed three of three times in isolation. The cap is a wall-clock proxy for the property the test names: a segment-local pattern is matched against the first ancestor only, not all 1900. A proxy that a busy machine can trip blocks the close-time test receipt for no defect.

## Requirements

1. The test proves the skip by counting the probe pattern's regex `match` calls during one `excluded()` call: at most 2 (the direct check and the first ancestor).
2. The wall-clock assertion is removed from this test; the count replaces it.
3. The test still fails when `excluded()` walks every ancestor for a segment-local pattern (`reachable = ancestors` unconditionally).
4. No change to `techdocs_audit_lib.py`.

## Scope

**Problem statement:** a wall-clock cap in one test fails under load although the code under test is correct.

**In scope:**

- `test_a_segment_local_pattern_skips_the_ancestor_walk` only.

**Out of scope:**

- The other wall-clock caps in the same module (0.05 s and 0.5 s). They have not failed and guard different properties; the operator asked for this one.
- Any library behavior change.

## Acceptance Criteria

- [x] AC-1: The test asserts at most 2 `match` calls on the probe pattern's compiled regex during `excluded(catastrophic, [worst])`, and holds no wall-clock assertion.
- [x] AC-2: A mutant of `techdocs_audit_lib.excluded` that walks every ancestor for every pattern fails the test, shown in a scratch copy.
- [x] AC-3: The module passes on Python 3.14 and 3.13, and the full suite passes in the repo with a current receipt.

## Tasks

- [x] Replace the wall-clock assertion with a match-count assertion
- [x] Show the walk-every-ancestor mutant fails in a scratch copy
- [x] Run the module on 3.14 and 3.13, then the full suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                         |
| ---------- | ----------- | ---------- | ----------------------------- |
| test-pin   | implementer | —          | one test method, no lib edits |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_techdocs_audit_lib.py`

## Affected Architecture Docs

N/A: one test method changes how it observes an existing property; no boundary, flow or verification-architecture impact.

## AC Priority


| AC   | Priority | Rationale                                         |
| ---- | -------- | ------------------------------------------------- |
| AC-1 | required | the fix itself                                    |
| AC-2 | required | the replacement must still catch the regression   |
| AC-3 | required | close-time receipt and cross-version behavior     |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-04 | Planned after the 1zrak receipt run failed once on this cap | 0.163 s vs 0.15 s under load; 3/3 green in isolation |
| 2026-10-04 | Implemented: `CountingRegex` proxy via `unittest.mock.patch.object(audit, "_pattern_regex", ...)` keyed on `raw == worst`; asserts 1 <= matches <= 2; unused `import time` dropped | module OK on 3.14 (86 tests) and the method OK on 3.13; walk-every-ancestor mutant in a scratch copy fails with 1901 matches; the module's 71 worker errors on 3.13 also occur at HEAD (the worker refuses a 3.13 interpreter against the 3.14 tool venv, by design) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-04 | Count regex `match` calls instead of raising the cap | the count is exact and load-independent; the test's name states a structural property | raise the cap to 1-2 s (still a proxy, still load-sensitive in principle) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| The counting wrapper misses a call path and the count is vacuous | AC-2 mutant must fail; also assert the count is at least 1 |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
