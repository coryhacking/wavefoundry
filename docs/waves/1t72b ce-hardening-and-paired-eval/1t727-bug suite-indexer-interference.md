# Test Suite vs Background Indexer Interference

Change ID: `1t727-bug suite-indexer-interference`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

The full framework suite intermittently fails `test_indexer.py` when it runs
concurrently with background repository activity (the post-edit hook's detached
`indexer.py` refresh, or a live MCP server session). The pattern recurred three
times on 2026-07-20 alone: the failing run reports `FAILED (test_indexer.py)`,
the same file passes in isolation immediately afterward, and an uncontended
rerun of the full suite is clean. Each false FAILED costs a ~5-minute rerun and
erodes trust in the suite-green delivery gate. `run_tests.py` already excludes
concurrent copies of itself (`test-run.lock`); it does not exclude the indexer,
and the indexer does not defer to a test run.

## Requirements

1. **Root cause identified before any fix is accepted**: reproduce the
   interference (suite + concurrent index build) and name the exact shared
   resource or mechanism that makes hermetic `test_indexer` tests fail. A fix
   without an identified mechanism is not accepted (the 1t231 precedent).
2. **Mutual exclusion, both directions, matched to the identified mechanism**:
   a full-suite run must not race a background project index build. Direction A:
   `run_tests.py` waits (bounded) for a running index build to finish before
   starting. Direction B: hook-spawned background index refreshes defer or
   queue while a test run holds `test-run.lock`. Implement the direction(s) the
   root cause actually requires; record the choice in the Decision Log.
3. **No deadlock and no silent skip**: every wait is bounded with a clear
   timeout diagnostic naming the holder; a deferred index refresh must still
   happen after the suite finishes (deferral is not cancellation).
4. Existing single-runner exclusion (`test-run.lock` busy diagnostic) and the
   stray-artifact guard remain unchanged.

## Scope

**Problem statement:** The suite and the background indexer share a resource
that makes `test_indexer.py` flake under contention; nothing serializes them.

**In scope:**

- Root-cause reproduction and mechanism identification
- The exclusion mechanic in `run_tests.py` and/or the indexer spawn path
- Hermetic tests for the exclusion (lock-held simulation, bounded-wait timeout)

**Out of scope:**

- Reworking `test_indexer.py` internals beyond what the root cause demands
- Cross-process scheduling beyond the suite/indexer pair

## Acceptance Criteria

- [~] AC-1: Bounded reproduction stayed DRY — three configurations attempted on
      2026-07-20 (isolated test_indexer x3 vs live docs rebuild: OK; the full
      6,029-test suite vs live code rebuild: OK, 14% slower; six parallel
      test_indexer processes vs live docs rebuild: all OK at ~3.4x normal
      runtime). The historical failures involved a live MCP server session,
      which is not reproducible on demand. Recorded honestly per this AC's
      explicit fallback; the exclusion ships as defense-in-depth.
- [x] AC-2: With a project index build in progress, `run_tests.py` waits
      (bounded) and reports what it is waiting on; on timeout it fails with a
      diagnostic naming the holder rather than starting a contended run
      (`_wait_for_index_build`; SuiteIndexerExclusionTests).
- [x] AC-3: An index build requested while `test-run.lock` is held defers
      without being lost — bounded wait at the `_index_build_lock` chokepoint
      (all build callers), proceeding after the bound (deferral is never
      cancellation), verified by IndexerDeferralTests.
- [x] AC-4: Full framework test suite passes (6,036 tests across 56 files, OK, 2026-07-20).

## Tasks

- [~] Reproduce the interference and identify the shared mechanism — bounded effort dry; recorded per AC-1 fallback
- [x] Implement the exclusion, both directions (defense-in-depth)
- [x] Hermetic tests: bounded wait, timeout diagnostic, deferred refresh
- [x] Run full framework test suite

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| root-cause | Engineering | —          | Reproduction first; fix direction depends on it |
| exclusion  | Engineering | root-cause | run_tests.py and/or indexer spawn path |


## Serialization Points

- `run_tests.py` is shared with the stray-artifact guard (1t231); edits must
  keep that guard's snapshot semantics intact.

## Affected Architecture Docs

`N/A` — test-infrastructure exclusion confined to the runner and indexer spawn
path; no boundary, flow, or contract change.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | No fix without a mechanism (1t231 precedent) |
| AC-2 | required | The suite side of the exclusion |
| AC-3 | required | The indexer side; deferral must not lose refreshes |
| AC-4 | required | Suite-green delivery gate |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-20 | Operator independent static review found a TOCTOU race: both sides probed the other's lock BEFORE acquiring their own, so simultaneous starts could slip through. Repaired with an atomic-recheck discipline on both sides: each checks the other's lock only AFTER acquiring its own | `ev-suite-indexer-exclusion-toctou-race*`; ExclusionInterleavingTests, IndexerDeferralOrderingTests |
| 2026-07-20 | The first repair draft (build defers while HOLDING its lock) was live-refuted within the hour: a hook-spawned build deferring to the running suite presented as a phantom running build and made the unit-test file wait out its entire 600s budget. Revised to hold-nothing-while-waiting: the build checks atomically post-acquire, then RELEASES before waiting (bounded cycles; final cycle proceeds); the suite re-probes post-acquire and yields. Nobody ever waits while holding, so no phantom builds and no deadlock; livelock is bounded by both deadlines with safe endgames (suite fails loudly; build proceeds) | full-suite hang reproduction (test_run_tests_cache 600s, 0 tests); revised ordering pinned by source tests; cache tests hermetically isolated from the real repo lock |
| 2026-07-20 | Operator independent static RE-review: both prior blocking defects confirmed fixed (post-acquire re-probe on the suite side; acquire-check-release-wait on the build side; no phantom-lock hang; manifest repair intact; git diff --check clean). One non-functional cleanup applied in-session: the run_tests yield-loop comment still described the refuted defer-while-holding draft; corrected to the hold-nothing-while-waiting design | operator re-review verdict; corrected comment at run_tests.py main start sequence |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Both exclusion directions implemented as defense-in-depth after a dry bounded reproduction (3 configurations, all green) | The mechanism could not be named on demand (historical failures involved a live MCP server session); the exclusion is cheap, bounded, and cannot deadlock (suite-side timeout fails with a holder-naming diagnostic; build-side timeout proceeds) | Fix-on-mechanism-only (rejected: three same-day false FAILEDs justify insurance); suite-side only (rejected: hook-spawned builds would still race a running suite) |
| 2026-07-20 | Build-side deferral lives INSIDE `_index_build_lock` (the chokepoint), covering every build caller; timeout PROCEEDS rather than cancels | A lost refresh is worse than a contended one; the OS build lock remains the authority | Per-caller deferral (rejected: misses future callers); hook-spawn-site deferral (rejected: operator-requested builds contend identically) |
| 2026-07-20 | The POSIX flock probe momentarily acquires when free, so `_acquire_run_lock` retries 3x100ms before reporting busy | A microsecond probe window must never produce a spurious "already running" suite failure | Accept the race (rejected: it recreates the annoyance this change fixes) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Root cause not reproducible on demand (timing-dependent) | Bounded reproduction effort; if dry, record honestly and justify the exclusion as defense-in-depth per AC-1 |
| Bounded wait chosen too short/long | Workflow-config-style constant with a conservative default; timeout diagnostic names the holder so operators can decide |
| Deferral path silently drops a refresh | AC-3 hermetic test asserts the deferred refresh still runs |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
