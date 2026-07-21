# Contention-Safe Performance-Test Budgets

Change ID: `1t3zv-debt contention-safe-performance-test-budgets`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
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

- [ ] AC-1: Every framework-suite wall-clock assertion is inventoried with its
      worker/concurrency exposure and current threshold.
- [ ] AC-2: Each modified budget or execution policy has recorded isolated and
      contended evidence; the selected headroom is sufficient for repeated
      six-worker runs on the supported slower-machine baseline.
- [ ] AC-3: The known 200ms- and 3s-class flakes no longer fail solely from
      scheduler contention, while a deliberately injected meaningful slowdown
      still fails the relevant performance guard.
- [ ] AC-4: Only affected tests are changed; unrelated suite parallelism and
      functional assertions are unchanged.
- [ ] AC-5: The performance-test policy is documented and framework tests plus
      docs validation pass.

## Tasks

- [ ] Inventory timing assertions and characterize isolation versus contention.
- [ ] Choose and implement the narrowest evidence-backed mitigation per affected test.
- [ ] Add regression and diagnostic coverage, including a meaningful-slowdown guard.
- [ ] Document the contention-safe performance-budget policy.
- [ ] Run framework tests and docs validation.

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
