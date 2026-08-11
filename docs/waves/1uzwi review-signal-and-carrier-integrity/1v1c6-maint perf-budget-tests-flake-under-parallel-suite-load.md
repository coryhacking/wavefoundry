# Perf-Budget Tests Flake Under Parallel Suite Load

Change ID: `1v1c6-maint perf-budget-tests-flake-under-parallel-suite-load`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-08-10
Wave: 1uzwi review-signal-and-carrier-integrity

## Rationale

`test_repeated_warm_estimator_and_projection_budgets` asserts wall-clock p95 budgets (10ms/25ms tiers) that fail under `run_tests.py`'s parallel execution (`ThreadPoolExecutor`, six workers) on a loaded machine — **including at unmodified `HEAD`**, proven during `1uwpf`'s reverification from a clean `git archive` extract (41.6ms observed there against the 25ms budget). The test passes 3/3 in isolation, every time. During `1uwpf` this single test produced four spurious full-suite failures across one day, each consuming an investigation, and its failure mode (whole-file FAILED with the name buried) made it look like a regression in whatever wave was in flight.

A wall-clock assertion in a parallel suite measures the machine, not the code. The budget itself is worth keeping — it caught nothing this time but exists to catch real regressions — so the fix is isolation or normalization, not deletion.

## Requirements

1. **The budget assertion stops failing on scheduler contention.** Preferred shape, decided at implementation with a measurement: serialize that test file in `run_tests.py` (run it outside the parallel pool), or gate the assertion on a contention probe (re-measure once serially before failing), or scale the budget by a measured calibration factor. Deleting the assertion is not an option.
2. **A real regression still fails.** Whatever ships must demonstrably fail on an injected slowdown (a deliberate sleep in the measured path on a scratch copy).
3. **The `test_indexer` epoch flake is triaged in the same pass.** `test_true_noop_never_opens_the_epoch` failed once under the same load spike ("2 != 1" generation) and passed 3/3 in isolation; determine whether it shares the contention mechanism or was a distinct one-off, and record the disposition either way.

## Scope

**Problem statement:** the suite's green/red signal is hostage to machine load, and the failure presentation buries which test flaked.

**In scope:** `run_tests.py` scheduling or the budget-test assertion mechanics; the epoch-flake triage; nothing in `context_efficiency` measurement itself.

**Out of scope:** changing what the estimator/projection code does; raising budgets without a calibration argument; the external load source.

## Acceptance Criteria

- [x] AC-1: Ten consecutive runs of the affected test file inside the parallel pool under artificial CPU load (a documented load generator) produce zero failures from the budget test, where the same file-scope procedure against current code reproduces at least one — the red-first half is a **reproduction protocol**, since the failure is environmental. File-scope runs carry the evidentiary weight; full-suite runs may substitute but are not required (a readiness-council rescope: ten full-suite runs is disproportionate protocol for a maintenance change and invites shortcuts that then read as violations).
- [x] AC-2: An injected slowdown in the measured path still fails the budget test, demonstrated on a scratch copy **with the magnitude pinned near the shipped threshold**: a slowdown at roughly 1.5x the effective budget fails, and a control at roughly 0.5x passes. An unbounded slowdown cannot distinguish preserved teeth from an inflated budget, which is the outcome the Decision Log forbids.
- [x] AC-3: The epoch-flake triage is recorded here with its disposition.
- [x] AC-4: The full framework suite and docs-lint pass.

## Tasks

- [x] Reproduce under controlled load; pick the mechanism from measurement.
- [x] Implement; verify AC-2's injected-slowdown kill.
- [x] Triage the epoch flake; record.
- [x] Full suite; docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reproduce | implementer | — | Controlled-load protocol, AC-1 |
| mechanism | implementer | reproduce | Measurement decides among the three shapes |
| epoch-triage | implementer | — | AC-3; independent of the budget fix |

## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`

## Affected Architecture Docs

`N/A` with rationale: test-infrastructure scheduling; no product behavior changes.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect: four spurious investigations in one day. |
| AC-2 | required | The budget must keep its teeth or this is deletion by another name. |
| AC-3 | important | Same load spike, unknown mechanism; cheap to settle now. |
| AC-4 | required | Standard gate. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-10 | Planned from wave `1uwpf`'s carried-forward findings. Premises verified before authoring: budgets at the (10, 10.0)/(50, 25.0) tiers; six-worker `ThreadPoolExecutor` in `run_tests.py`; the failure reproduced at unmodified `HEAD` from a clean extract (architecture lane); 3/3 green in isolation | executed at HEAD and working tree during `1uwpf` reverification |
| 2026-08-10 | Readiness council (red-team and docs-contract seats): AC-2 gained a magnitude bound (an unbounded injected slowdown passes under exactly the inflated-budget outcome the Decision Log forbids, so it could not falsify a lobotomized budget); AC-1 rescoped to file-scope runs under load, equal evidence at a fraction of the protocol cost | red-team seat report, 2026-08-10 |
| 2026-08-10 | Thought: delegated to a dedicated implementer lane owning only `run_tests.py` and `test_server_context_efficiency.py`, measurement-first on scratch `git archive HEAD` extracts, with the readiness lanes' obligations in the brief: match AC-1's procedure to the chosen mechanism (stop and report if only serialization works), record the effective-budget definition, and cover ALL budget assertions including the flush p95 the plan text did not separately name | implementer brief, 2026-08-10 |
| 2026-08-10 | Mechanism chosen by measurement: (c) calibration factor. Contention re-probe (b) refuted by data: under sustained 12-worker load a back-to-back retry pass itself breached (tier-50 retry p95 25.742ms vs 25.0 where the first pass read 15.5ms), and at 24 workers the original test failed 5 of 5, so retry-once cannot yield ten-run zero failures. Probe wall/cpu ratio tracked contention exactly (1.005-1.014 quiet, 1.7-6.2 at 12 workers, 7.8-11.0 at 24). Serialization (a) not needed; the test stays inside the parallel pool, so AC-1's wording holds unmodified. Fix: `_contention_probe()` interleaved with every timed sample across all three loops, pooled p95 wall/cpu ratio as the run factor (floor 1.0), each budget asserted against nominal x factor with a self-documenting failure message and opt-in `WAVEFOUNDRY_BUDGET_DIAG=1` diagnostic. Nominal budgets unchanged at (10, 10.0)/(50, 25.0)/flush 25.0; `run_tests.py` untouched | implementer report with run logs at scratchpad/1v1c6/, 2026-08-10 |
| 2026-08-10 | AC-1 executed (documented load generator: N pure-python busy-loop processes, script preserved with logs). RED at N=12, current code: 10 file-scope runs, 1 failure (50-source warm p95 29.742ms vs 25.0). GREEN at N=12, fixed code: 10 runs, 0 failures (factors 1.902-4.587; green run 3 shows the mechanism directly: 10-source p95 10.022ms would have breached the raw 10.0 budget, effective 23.188 passed). Supplementary N=24 escalation strengthens the thin 1-in-10 red rate: original code 5/5 FAIL, fixed code 5/5 PASS | implementer run tallies, 2026-08-10 |
| 2026-08-10 | AC-2 executed with the magnitude bound, effective budget defined as nominal x measured factor (quiet-machine factors 1.009-1.201, printed per run): kills at ~1.5x effective FAILED all three assertions (16.251 vs 10.155; 43.046 vs 25.230; 43.655 vs 25.306) and controls at ~0.5x PASSED (6.294; 18.249; 18.926). Deviation recorded: exact spin-waits instead of `time.sleep` for the pinned magnitudes, because macOS sleep overshoot (~1.7x at the 12.5ms scale) breached the 0.5x control through injection imprecision, not budget tightness; sleep-based kills retained as supplementary evidence and also failed | implementer kill/control table, scratch injections restored and diff-verified, 2026-08-10 |
| 2026-08-10 | AC-3 epoch triage disposition: DISTINCT ONE-OFF, does not share the contention mechanism. `test_true_noop_never_opens_the_epoch` asserts logical invariants only (generation and epoch-token equality; no wall-clock measurement), and the only route to "2 != 1" with up_to_date true is the zero-change idle-maintenance branch, gated by four flags computed from durable local state, none clock-derived. Plausible cause of the single observed failure: a fail-soft I/O hiccup in the test's unasserted first build under the load-average-74 spike, leaving recovery work for the incremental. Empirical: 0 failures in 15 single-test runs at N=24/N=36 plus 3 full class runs at N=36 (load average ~55). No code change; if it recurs, capture build 1's result dict and `read_build_state` status before the incremental | implementer code reading (indexer.py idle-maintenance branch) and load runs, 2026-08-10 |
| 2026-08-10 | Canonical full suite on the delivered tree: 7087/62 OK (222s) with the calibrated budget test inside the parallel pool. Delivery code lane observed it pass under genuine full-suite load at measured factor 1.408 while an injected 20ms slowdown in the measured path still FAILED at factor 1.009: a regression cannot move the probe to hide itself. Delivery qa lane verified every recorded AC-1/AC-2 number against the preserved run logs (exact matches), re-executed fresh kill/control injections consistently, confirmed the factor is not load-bearing on quiet runs (nominal-only scratch variant passes quiet at p95 1.3/5.4/5.5ms), and ran the file 3x stable | delivery lane reports; scratchpad/1v1c6 run logs, 2026-08-10 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-10 | Keep the budget, fix the measurement conditions | The assertion exists to catch real regressions; it failed on the machine, not the code | Delete or 10x the budget (rejected: deletion by another name); mark expected-flaky (rejected: a permanently-yellow test trains everyone to ignore it) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Serializing the file lengthens the suite | Measure first; the file runs in ~8s alone |
| The controlled-load protocol does not reproduce on a quiet CI-class machine | The protocol documents the load generator; AC-1 counts only runs where the control (current code) reproduces |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
