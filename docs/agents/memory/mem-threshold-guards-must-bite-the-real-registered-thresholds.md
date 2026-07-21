# Threshold guards must bite the real registered thresholds

Owner: Engineering
Status: active
Last verified: 2026-07-21

Memory ID: `mem-threshold-guards-must-bite-the-real-registered-thresholds`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-21
Updated: 2026-07-21
Source event: `finding:1seax:slowdown-guard-does-not-exercise-real-budgets`
Validation: promote
Validated by: agent
Action delta: A guard that protects thresholds must exercise the REAL registered thresholds, never a synthetic stand-in, and should carry an invariant that bounds the thresholds themselves so inflation fails the guard.
Validation rationale: The drafted summary names only the repair verdict; the durable lesson is the guard-vacuity shape: a meaningful-slowdown test against synthetic numbers proves nothing about the real budgets it exists to protect.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1seax (1t3zv): the meaningful-slowdown guard initially exercised only the generic assertion helper with a synthetic 1-second threshold, proving nothing about the real 1.0s and 10s budgets it existed to protect. Repair pattern: hoist the per-operation budgets into one registered table (PERF_BUDGETS) that both the guarded tests and the guard consume, inject a slowdown just past each REAL threshold, pin the guarded tests as carrying no local numbers, and add a permissiveness invariant (budget within 3x-50x of its isolated reference) so inflating a budget fails the guard itself.

## Evidence

- `1seax`
- `slowdown-guard-does-not-exercise-real-budgets`
- `test_injected_slowdown_fails_each_real_budget`
- `test_permissiveness_invariant_bounds_every_budget`

## Targets

- `.wavefoundry/framework/scripts/tests/perf_budget_policy.py`
