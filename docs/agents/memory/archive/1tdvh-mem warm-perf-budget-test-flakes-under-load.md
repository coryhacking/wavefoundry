# warm-perf-budget-test-flakes-under-load

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1tdvh-mem warm-perf-budget-test-flakes-under-load`
Superseded by: `24be9-mem warm-perf-budget-test-can-still-fail-under-concurrent-load`
Kind: `environment_gotcha`
Confidence: 0.8
Created: 2026-07-23
Updated: 2026-11-25
Archived: 2026-11-25
Archive reason: Superseded by 24be9-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1tdvh-mem warm-perf-budget-test-flakes-under-load.md`

## Summary

test_repeated_warm_estimator_and_projection_budgets (warm flush/projection p95 budget, 25ms) fails under concurrent machine load: two full-suite failures reproduced while other suites or live MCP probes ran alongside (29.7ms observed), passing in isolation and in quiet full runs. Run the canonical suite without concurrent heavy activity before treating a failure there as a regression, and consider a load-aware or contention-safe budget as a follow-up.

## Evidence

- `tests/test_server_context_efficiency.py`
- `1tbt7`
- `1tg55`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
