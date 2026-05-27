# Single-Run Guard for `run_tests.py`

Change ID: `0rld3-bug test-runner-single-run-guard`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

`run_tests.py` intentionally fans out one subprocess per test file, but overlapping top-level invocations can multiply that fan-out and flood the machine with duplicate test trees. This change adds a single-run guard so only one suite execution can hold the runner at a time.

## Requirements

1. Prevent concurrent top-level `run_tests.py` executions from running at the same time.
2. Fail fast with a clear diagnostic when another runner already holds the guard.
3. Keep the existing per-file parallelism unchanged for the one active run that is allowed to proceed.
4. Avoid leaving stale lock state behind after normal completion or failure.

## Scope

**Problem statement:** The multiprocess runner works, but without a single-run guard multiple invocations can overlap and amplify the process count instead of reducing wall-clock time.

**In scope:**

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/tests/test_run_tests_cache.py`

**Out of scope:**

- changing the per-file fan-out model itself
- making the suite globally sequential
- changes to unrelated test files

## Acceptance Criteria

- [x] AC-1: A second simultaneous `run_tests.py` invocation exits quickly with a clear "already running" style diagnostic.
- [x] AC-2: The active run still executes test files in parallel as before.
- [x] AC-3: Automated tests cover the lock acquisition and busy-lock failure path.

## Tasks

- [x] Add a process lock or lock file around the top-level runner.
- [x] Surface a concise diagnostic when the lock cannot be acquired.
- [x] Add regression tests for both the happy path and the contention path.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| runner guard | code-reviewer | — | Top-level lock around `run_tests.py` |
| regression tests | qa-reviewer | runner guard | Verify contention behavior |

## Serialization Points

- `run_tests.py`

## Affected Architecture Docs

N/A. This is a runner reliability fix with no architecture boundary change.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Core safety property |
| AC-2 | required  | Preserve existing performance win |
| AC-3 | required  | Prevent regression |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-26 | Added after observing overlapping framework test invocations flood the machine. | Process inspection |
| 2026-05-27 | Verified the top-level runner lock and regression coverage already present in the current tree; documented the change as complete. | `run_tests.py` lock helpers and `test_run_tests_cache.py` lock tests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-26 | Guard top-level runs rather than removing parallel file execution. | The performance benefit comes from per-file fan-out; the problem is only concurrent suite invocations. | Make the suite sequential |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Lock implementation leaks on abnormal exit | Use an OS-level lock and release it automatically when the process exits |
| The guard blocks legitimate nested test calls | Scope the lock to the top-level runner only |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
