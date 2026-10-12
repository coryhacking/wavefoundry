# Make the combined log-tail regression deterministic

Change ID: `20gz6-bug deterministic-combined-log-tail-check`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-10-12
Wave: 20h6q combined-log-tail-check

## Rationale

The operator requested a separate follow-up for the declared-profile release failure in the large two-pipe child-log fixture, then authorized proceeding with the 1.29.0 release. The fixture expects both stream endings in a combined bounded log even though reader scheduling can place more than the retained suffix after one stream's ending. Make the fixture test the existing retention contract deterministically, without changing production logging or drawing performance conclusions from a concurrently loaded machine.

## Requirements

1. Align the large two-pipe fixture with combined arrival-order retention: a capped opening plus final suffix, rather than guaranteed independent suffixes for both streams.
2. Where the test asserts that a marker survives in the combined suffix, establish the relevant output ordering through bounded synchronization, not a fixed sleep or assumed drain speed.
3. Preserve real two-pipe multibyte output above the cap, nonzero/check=True behavior, finalization and timeout cleanup coverage, and separate real-deadline checks.
4. Keep the existing 1 MiB log cap, 64 KiB combined suffix and production child_tee.py unchanged. Retain concise evidence in wave.md and canonical tests, with no routine evidence folder.

## Scope

**Problem statement:** A release regression test asserts a stronger per-stream retention property than the combined log provides.

**In scope:** The large two-pipe fixture and directly supporting test helpers in tests/test_child_tee.py; focused controls for supported ordering and finalization; a terse release note when implemented.

**Out of scope:** Production logging policy, independent per-stream file tails, uv, performance budgets, host-load diagnosis, broad test-runner changes, and repeating release qualification solely for timing.

## Acceptance Criteria

- [ ] AC-1: The two-pipe regression uses a bounded deterministic arrangement for any required combined-tail markers, and tolerates supported reader interleavings without assuming per-stream suffix retention; a controlled ordering variation is the oracle.
- [ ] AC-2: Cap, truncation notice, multibyte boundaries, real nonzero/check=True behavior and timeout finalization remain checked; an intentionally broken finalization or suffix-retention control is detected by a meaningful assertion.
- [ ] AC-3: The affected child-log tests and existing real-deadline controls pass, the change's documents validate, and production logger bytes and retention policy remain unchanged.

## Tasks

- [ ] T-1: Prepare and independently review the scoped fixture plan before editing test source.
- [ ] T-2: Make marker placement deterministic across the applicable nonzero, check=True and injected-timeout cases without weakening retention checks.
- [ ] T-3: Run focused ordering and known-bad controls plus affected tests; obtain independent code and QA delivery review.
- [ ] T-4: Record concise results and limitations in wave.md and add the implementation release note; retain no routine evidence folder.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Fixture repair | implementer | readiness | One source writer |
| Independent verification | code-reviewer, qa-reviewer | implementation | Bounded ordering controls; no host performance conclusions |

## Serialization Points

Planning only for now. Prepare wave and readiness approval precede source edits. No simultaneous source writes or qualification probes.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/tests/test_child_tee.py`

Production `.wavefoundry/framework/scripts/child_tee.py` is a read-only contract reference. Root CHANGELOG.md receives a terse note only when implemented.

## Affected Architecture Docs

N/A: fixture correction preserves the existing logging contract. If investigation instead requires a production retention change, return to the operator for that distinct scope.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Remove the unsupported ordering assumption |
| AC-2 | required | Preserve meaningful bounded-log regression coverage |
| AC-3 | required | Keep the repair confined to its own tests and contract |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-12 | Planned at operator request; no implementation or readiness approval. Declared qualification failed the unchanged first nonzero-exit leg's saved-log assertion. Both in-memory stream markers had passed. Saved log was 1,048,572 bytes with opening, truncation notice and FINAL-STDERR; FINAL-STDOUT was absent. Exact reader scheduling was not captured. | ChildTeeTests.test_large_two_pipe_logs_finalize_on_nonzero_exit_and_timeout; child_tee._BoundedLog; complete declared qualification report |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-12 | Select bounded deterministic marker ordering in the test | Preserves the existing combined-tail contract and detects actual finalization defects | Give each stream a production suffix: expands policy and changes the cap allocation. Remove ending assertions or increase waits: weakens the oracle or preserves scheduling assumptions. |
| 2026-10-12 | Track separately from wave 20gz5 and release 1.29.0 now with the documented exception | Explicit operator request for a follow-up wave followed by release authorization | Reopen release-day source work: would extend the current qualification cycle against operator direction. |

## Risks

| Risk | Mitigation |
| --- | --- |
| Synchronization hides a finalization defect | Keep a meaningful known-bad control and real process cleanup |
| Marker observation is mistaken for guaranteed combined-tail retention | Establish ordering of the retained suffix explicitly |
| Concurrent host load is treated as a product regression | No timing conclusions or unrelated performance changes in this wave |

## Session Handoff

See `docs/agents/session-handoff.md` for release continuation and deferred work.
