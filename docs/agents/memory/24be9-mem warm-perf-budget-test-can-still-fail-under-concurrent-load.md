# Warm perf budget test can still fail under concurrent load

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24be9-mem warm-perf-budget-test-can-still-fail-under-concurrent-load`
Kind: `environment_gotcha`
Confidence: 0.75
Created: 2026-11-25
Updated: 2026-11-25
Supersedes: `1tdvh-mem warm-perf-budget-test-flakes-under-load`

## Summary

When test_repeated_warm_estimator_and_projection_budgets in .wavefoundry/framework/scripts/tests/test_server_context_efficiency.py fails in a full run while other suites, index builds or live MCP probes run alongside, rerun the canonical suite on a quiet machine before treating it as a regression. The test scales its budgets by a measured CPU contention factor (1v1c6) and checks the lifecycle flush row by median against 50 ms (242yr), but the contention probe does not measure disk stalls; set WAVEFOUNDRY_BUDGET_DIAG to print observed, nominal and effective budgets.

## Evidence

- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- `1tbt7`
- `1tg55`
- `1v1c6-maint perf-budget-tests-flake-under-parallel-suite-load`
- `242yr-bug flush-projection-budget-disk-contention`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
