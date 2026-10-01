# Index Status Tests Fail When the Test Process Is Younger Than About 28 Seconds

Change ID: `1zicp-bug index-status-test-process-age`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-09-30
Wave: 1zilw validation-correctness-fixes

## Rationale

A downstream validation of v1.28.0 (request 6), verified with a corrected threshold: `IndexBuildStatusTests.test_running_when_pid_active`, `test_previous_stats_included_in_running_response` and `ReapStateSurfaceTests.test_status_carries_the_reap_block_in_every_state_and_omits_it_without_a_record` in `tests/test_server_tools_retrieval.py` record the test process's own pid with `started_at = time.time() - 30`. The pid-reuse check `wf_server/index_handlers._pid_started_after` (2 s tolerance) compares the process's real creation time against that, so a test process created within the last ~28 s is read as a reused pid and the build reports `finished`. The tests pass only once the interpreter has run long enough, so a fresh or sharded runner fails them.

## Requirements

1. **Record the real start time.** The three tests record `started_at` from the test process's actual creation time (`process_info.create_time(os.getpid())`), so the pid-reuse check sees the recorded process as the same one regardless of the process's age. The production check is unchanged.
2. **Platforms.** Windows, macOS, Linux and WSL2 behave the same (test-only; `process_info` is psutil-backed).
3. **Transition.** Test-only; no CHANGELOG entry.

## Scope

**Problem statement:** three index-status tests depend on how long the test process has been running.

**In scope:**

- The three tests in `tests/test_server_tools_retrieval.py`.

**Out of scope:**

- The production pid-reuse tolerance.

## Acceptance Criteria

- [x] AC-1: the three tests pass in a fresh interpreter running only them (from `.wavefoundry/framework/scripts/tests`: `python -B -m unittest` with the three test ids; they fail that way today) and in the full suite; the whole file also passes in a fresh interpreter, so no other test depends on process age.
- [x] AC-2: the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Use the real creation time in the three tests.
- [x] Run them in a fresh interpreter.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Test fix | implementer | readiness | |
| Review | qa-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_server_tools_retrieval.py`

## Affected Architecture Docs

N/A: test fixtures only.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The flake |
| AC-2 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-30 | Delivery review: red-team and the four lanes (code, qa, release, security) approved, every mutation killed by the suite. Advisory taken: the code and test comments cited wave 1zicq instead of 1zilw (corrected). Not taken: a boundary test pinning the 2 s pid-reuse tolerance (pre-existing gap from 1zc7n, out of scope; follow-up); the shared custom-marker fixture uses symlinks, which can error on Windows without symlink privilege (pre-existing exposure shared with `test_custom_marker_requires_exact_legacy_inventory`). Full suite: 10200 tests OK | Full suite; delivery review |
| 2026-09-30 | Implemented. Module helper `_own_process_start()` returns `process_info.create_time(os.getpid())` (falls back to `time.time() - 30` only when unavailable); the three tests record it. Oracle: the three tests in a fresh interpreter run in 0.49 s, OK (readiness reproduced `'finished' != 'running'` before); whole file in a fresh process: 1043 OK | Fresh-interpreter runs |
| 2026-09-30 | Readiness round 1: approved; the fresh-interpreter oracle reproduced all three failures (`'finished' != 'running'`); notes folded in: exact oracle command, whole-file fresh run | Prepare council and lane review |
| 2026-09-30 | Planned from the v1.28.0 downstream validation (request 6), verified: the three tests record `os.getpid()` with `started_at = time.time() - 30`; `_pid_started_after` returns reused when creation time exceeds `started_at + 2.0`, so a process younger than ~28 s fails | Code reads |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-30 | Fix the fixtures, not the tolerance | The production check is correct; the fixtures misstate the start time | Widen the tolerance |

## Risks

| Risk | Mitigation |
| --- | --- |
| `process_info` unavailable in a test environment | It is a required dependency (ADR `1z9df`) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
