# Make the large child-log timeout check deterministic

Change ID: `20gz4-bug deterministic-child-log-timeout-check`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-12

## Rationale

Release qualification exposed a timing-sensitive assertion in the large two-pipe log test. A two-second real deadline may stop the stderr reader before its final marker is consumed. The test nevertheless requires that marker in every retained log. A finite delayed-read probe reproduces this failure. Production intentionally stops readers at the deadline; it cannot promise output that has not reached the retention writer.

## Requirements

1. Make the large-output timeout-finalization fixture establish that both final markers reached the presentation sinks before injecting TimeoutExpired at the process-wait boundary.
2. Keep real child processes, both pipes, multibyte output over the log cap, nonzero and check=True behavior, timeout cleanup and bounded final-log assertions.
3. Preserve the separate real elapsed-time/withheld-pipe tests. Change no production logging behavior, deadlines, caps or uv policy.

## Scope

**Problem statement:** The timeout fixture confuses a wall-clock performance assumption with the finalization contract.

**In scope:** Only `tests/test_child_tee.py`, its large two-pipe timeout fixture and a terse release note. Use bounded events to observe both final markers, inject TimeoutExpired through the live child's wait boundary, then allow the real cleanup wait to reap that child. Verify delayed reader scheduling no longer causes the false assertion.

**Out of scope:** Production child_tee.py, per-stream retention guarantees, increasing production timeouts, weakening cap/tail assertions, new test dependencies, uv behavior or upgrade work.

## Acceptance Criteria

- [x] AC-1: The large-output timeout fixture triggers its timeout only after both final markers have been observed; a finite delayed-stderr control passes without relying on a two-second throughput assumption.
- [x] AC-2: Real nonzero exits and check=True remain covered; the test still verifies cap, elision and retained endings, and a missing finalization control fails.
- [x] AC-3: Existing real deadline/withheld-descendant-pipe tests and the complete child_tee test file pass; production source is unchanged.

## Tasks

- [x] T-1: Replace the timing assumption with bounded output observation and an injected wait-boundary timeout; add the release note.
- [x] T-2: Run delayed-reader and missing-finalization controls, real deadline tests and the full test file; obtain independent delivery review.
- [x] T-3: Record compact results and resume the shared release qualification on final source; retain no routine evidence folder.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixture repair | implementer | readiness | Coordinator is sole source writer |
| Independent checks | code-reviewer, qa-reviewer | implementation | Bounded fixtures, temporary reports |
| Release continuation | wave-coordinator | final source | One default and two profile runs shared with the release wave |

## Serialization Points

No concurrent source edits. Finish fixture and changelog before qualification. Review tests run only in disposable roots with telemetry disabled; no concurrent review probes during full qualification.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_child_tee.py`

Production `.wavefoundry/framework/scripts/child_tee.py` is inspected only to verify its wait/cleanup boundary and unchanged bytes.

## Affected Architecture Docs

N/A: test scheduling correction only; no production contract changes.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Remove the demonstrated false failure |
| AC-2 | required | Preserve the finalization regression oracle |
| AC-3 | required | Retain actual timeout coverage and bound scope |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Independent code and QA delivery approved with no findings. Both reproduced the delayed-read pass and timeout-only missing-finalization failure; QA also executed both real deadline controls. Shared release qualification resumes in wave 20gz3; no routine evidence folder retained. | Named test fixtures and typed delivery approvals in wave.md/events.jsonl |
| 2026-10-12 | Applied the readied fixture and release note. Canonical focused child_tee run passed all 20 tests, zero skips, in 8.081 seconds, including unchanged real deadline controls. Production child_tee.py blob remains c115cc5b31841f55c420b9771edc0259a4d3fb01. Fresh code and QA delivery checks are running before full qualification. | test_child_tee.py; run_tests.py --file test_child_tee.py |
| 2026-10-12 | Default release qualification ran 12,402 tests; the only failure was the final stderr assertion in the large two-pipe timeout test. A 2.1-second delay on the third FINAL-STDERR read reproduces the single failure. | test_child_tee.ChildTeeTests.test_large_two_pipe_logs_finalize_on_nonzero_exit_and_timeout; child_tee.run timeout exception branch |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Observe delivered endings, then inject timeout at the process wait boundary in this finalization test | Separates finalization from scheduler throughput while keeping real pipes and cleanup | Merely raise the timeout: leaves a timing race. Drop terminal assertions: weakens the intended regression. Change production drain behavior: expands scope and changes the deadline contract. Separate existing tests continue exercising real wall-clock expiry. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Mocked timeout hides real deadline regression | Leave the separate real timeout tests unchanged and execute them |
| Observation hangs if a marker is lost | Finite event deadline, fail loudly, real child cleanup still runs |
| Fixture fails to detect missing log finalization | Explicit negative control removes finalization and must fail |

## Session Handoff

See `docs/agents/session-handoff.md` for release continuation.
