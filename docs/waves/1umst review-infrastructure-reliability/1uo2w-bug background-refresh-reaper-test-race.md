# Deterministic Background Refresh Reaper Test

Change ID: `1uo2w-bug background-refresh-reaper-test-race`
Change Status: `implemented`
Owner: framework maintainers
Status: implemented
Last verified: 2026-08-07
Wave: `1umst`

## Rationale

The background-refresh stale-child recovery test assumes a child process exits within
50 ms. On a loaded host, that assumption is false: the child is still live when the
nonblocking reaper runs, so the production guard correctly suppresses a refresh and
the test fails intermittently.

## Requirements

1. The POSIX-only test must wait until its child has exited without consuming the
   child's wait status before invoking the server refresh logic.
2. The test must continue to prove that the server's own nonblocking reaper removes
   the completed child and permits a stale refresh to start.
3. Production process-liveness and reaping behavior must not change.

## Scope

**Problem statement:** The timing-sensitive test does not deterministically create
the completed-but-unreaped child state it intends to exercise.

**In scope:**

- The stale-child recovery test in `test_server_tools.py`.
- Repeated targeted verification of that test and the enclosing test module.

**Out of scope:**

- `server_impl.py` process lifecycle behavior.
- Windows test coverage; the test is already POSIX-only.

## Acceptance Criteria

- [x] AC-1: The test observes its child as exited without reaping it before it calls
  `_maybe_refresh_if_stale`.
- [x] AC-2: The test verifies that `_maybe_refresh_if_stale` starts the project
  refresh and that the server registry no longer contains the child's PID.
- [x] AC-3: The focused test is stable across repeated execution and
  `test_server_tools.py` passes.

## Tasks

- [x] Replace the fixed sleep with a POSIX non-reaping child-exit barrier.
- [x] Run repeated focused and module-level verification.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Test fix | implementer | -- | Preserve the server reaper as the actor that consumes the child. |
| Verification | QA | Test fix | Exercise the focused case repeatedly and the enclosing module. |

## Serialization Points

.wavefoundry/framework/scripts/tests/test_server_tools.py

## Affected Architecture Docs

N/A. This change only removes test timing nondeterminism and does not alter a
production boundary, flow, or verification architecture.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The fixture must establish the intended completed-but-unreaped state. |
| AC-2 | required | The existing stale-child recovery contract must remain covered. |
| AC-3 | required | The regression must demonstrate that the intermittent failure is removed. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-07 | Planned deterministic test synchronization. | Failure analysis identified `time.sleep(0.05)` as the race. |
| 2026-08-07 | Replaced the fixed sleep with a non-reaping POSIX child-exit barrier. | Focused test passed 20 consecutive runs; `test_server_tools.py` and the framework harness passed. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-07 | Use `waitid(..., WNOWAIT)` in the POSIX test. | It blocks until exit while leaving the child available for the server's `waitpid(..., WNOHANG)` reaper. | Fixed sleep, which does not establish the precondition. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `waitid` is unavailable on a supported POSIX runtime. | Skip the POSIX-only test with an explicit reason when the required API or flags are unavailable. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
