# Repaired defect slowdown-guard-does-not-exercise-real-budgets

Owner: Engineering
Status: superseded
Last verified: 2026-07-21

Memory ID: `mem-repaired-defect-slowdown-guard-does-not-exercise-real-budget`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-21
Updated: 2026-07-21
Source exploration cost: 87497
Source event: `finding:1seax:slowdown-guard-does-not-exercise-real-budgets`
Validation: rewrite
Validated by: agent
Action delta: A guard that protects thresholds must exercise the REAL registered thresholds, never a synthetic stand-in, and should carry an invariant that bounds the thresholds themselves so inflation fails the guard.
Validation rationale: The drafted summary names only the repair verdict; the durable lesson is the guard-vacuity shape: a meaningful-slowdown test against synthetic numbers proves nothing about the real budgets it exists to protect.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-threshold-guards-must-bite-the-real-registered-thresholds`
## Summary

Real defect fixed in wave 1seax: Repair confirmed against the actual thresholds the finding named.

## Evidence

- `slowdown-guard-does-not-exercise-real-budgets`
- `ev-slowdown-guard-does-not-exercise-real-budgets-3`
- `1seax`

## Targets

- `tests/perf_budget_policy.py`
