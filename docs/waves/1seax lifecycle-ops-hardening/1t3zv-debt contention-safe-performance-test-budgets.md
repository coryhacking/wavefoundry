# Contention-Safe Performance-Test Budgets

Change ID: `1t3zv-debt contention-safe-performance-test-budgets`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-21
Wave: `1seax lifecycle-ops-hardening`

## Rationale

Back-to-back six-worker framework-suite runs can saturate the machine and make
tight wall-clock performance assertions flake even when the affected test
passes in isolation. The observed class includes a 120ms isolated result under
a 200ms budget and a separate 3s-budget failure after roughly a dozen suite
runs. These are scheduler/contention failures, not evidence that the measured
operation regressed. The suite needs enough contention headroom to remain
trustworthy without turning real performance regressions into green tests.

## Requirements

1. Inventory every wall-clock performance budget exercised by the framework
   suite and identify whether it can run under `run_tests.py`'s parallel worker
   model.
2. For each affected assertion, collect comparable isolated and contended
   measurements after repeated suite activity. A change must name its measured
   basis; do not relax a threshold solely because it failed once.
3. Retain meaningful regression detection: use measured contention headroom,
   a bounded retry/warm-up policy, or serialization of only the affected test
   module. Do not globally serialize the suite or broadly multiply all budgets.
4. Preserve deterministic functional assertions independently of timing, and
   make failures report the observed timing, threshold, and execution mode.
5. Document the chosen performance-test policy and when a new timing budget
   must include a contention-safe measurement.

## Scope

**Problem statement:** tight performance budgets flake under sustained
six-worker contention, making suite-green evidence unreliable.

**In scope:**

- The affected timing assertions and their test-runner execution policy
- Measured isolated-versus-contended characterization
- Narrow threshold, retry, warm-up, or serialization changes justified by that evidence
- Regression fixtures and diagnostic output
- Testing-policy documentation

**Out of scope:**

- Product-runtime performance changes
- A global reduction of suite parallelism
- Blanket budget inflation without measured evidence
- Hardware-specific baselines that cannot run on slower developer machines

## Acceptance Criteria

- [x] AC-1: Every framework-suite wall-clock assertion is inventoried with its
      worker/concurrency exposure and current threshold.
- [x] AC-2: Each modified budget or execution policy has recorded isolated and
      contended evidence; the selected headroom is sufficient for repeated
      six-worker runs on the supported slower-machine baseline.
- [x] AC-3: The known 200ms- and 3s-class flakes no longer fail solely from
      scheduler contention, while a deliberately injected meaningful slowdown
      still fails the relevant performance guard.
- [x] AC-4: Only affected tests are changed; unrelated suite parallelism and
      functional assertions are unchanged.
- [x] AC-5: The performance-test policy is documented and framework tests plus
      docs validation pass (6,081 tests across 59 files, OK, 2026-07-20).

## Tasks

- [x] Inventory timing assertions and characterize isolation versus contention.
- [x] Choose and implement the narrowest evidence-backed mitigation per affected test.
- [x] Add regression and diagnostic coverage, including a meaningful-slowdown guard.
- [x] Document the contention-safe performance-budget policy.
- [x] Run framework tests and docs validation.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| characterization | qa-reviewer | — | Inventory and measure before choosing mitigation |
| mitigation | implementer | characterization | Narrow per-test change only |
| policy and verification | qa-reviewer | mitigation | Regression evidence and documentation |


## Serialization Points

- Characterization evidence is required before any threshold or execution-policy edit.

## Affected Architecture Docs

`docs/architecture/testing-architecture.md` — timing-policy and parallel-suite
verification contract.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority                                             | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Complete census prevents hidden future flakes. |
| AC-2 | required | Measured headroom distinguishes contention from a regression. |
| AC-3 | required | Reliability without losing the performance signal. |
| AC-4 | required | Scope control; no global suite slowdown. |
| AC-5 | required | Durable verification policy and delivery gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-20 | Planned from recurring same-day performance flakes after sustained six-worker suite activity; an isolated 120ms result passed under the 200ms budget, pointing to contention rather than functional regression. | Operator observation; isolated verification. |
| 2026-07-20 | AC-1 inventory (8 wall-clock assertions): test_indexer 100K-drift 0.2s (FLAKED 3x; isolated 0.120s, worst contended 0.276s); test_graph_indexer line-scan 3s (FLAKED; isolated 0.240s, contended 3.215s); test_indexer 10K-drift 1.0s (same class, no observed flake, left unchanged per AC-4); test_context_efficiency poison-path 1.0s (no flakes); test_indexer lock-liveness 2.0s-vs-3s-holder (liveness discriminator, not perf; noted); test_memory_records 0.5s pair (no flakes); test_indexer age<5.0 (timestamp sanity); test_chunker 2.6x RELATIVE bound (contention-immune exemplar, adopted into policy). | grep inventory + today's suite history |
| 2026-07-20 | Mitigation: the two flaked budgets rebudgeted through the shared assert_within_budget helper — drift 0.2s to 1.0s (8.3x isolated / 3.6x worst-contended headroom), line-scan 3s to 10s (41x / 3.1x); failure messages now carry observed/threshold/isolated-reference triage guidance; meaningful-slowdown guard pinned in test_perf_budget_policy.py; policy documented in testing-architecture.md. | perf_budget_policy.py; rebudgeted assertions; live re-observation of contention (1,805ms line-scan during a concurrent server-tools run, within the new budget) |
| 2026-07-21 | Operator independent review (P2): the slowdown guard only exercised the helper with a synthetic 1s threshold. Repaired: PERF_BUDGETS is now the single registered table both tests consume (inline numbers removed and pinned absent); the guard injects 1.1x past each REAL budget (the 10s line-scan included), and a permissiveness invariant bounds every budget to 3x-50x of its isolated reference so inflation fails the guard itself | `ev-slowdown-guard-does-not-exercise-real-budgets*`; test_injected_slowdown_fails_each_real_budget; test_permissiveness_invariant_bounds_every_budget |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Characterize before mitigation; then choose measured headroom, a bounded retry/warm-up, or per-module serialization. | The suite needs trustworthy performance signals without global serialization or blanket threshold inflation. | Globally serialize suite / broadly relax all budgets (rejected: unnecessary loss of coverage or signal). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Threshold masks a real regression | Require a meaningful-slowdown guard and evidence-backed, per-test headroom. |
| Slow hardware still flakes | Use a supported slower-machine baseline and make contention diagnostics explicit. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
