# Decision: Handler modules reach shared helpers through a function-lev…

Owner: Engineering
Status: rejected
Last verified: 2026-09-20

Memory ID: `1yi3c-mem decision-handler-modules-reach-shared-helpers-through-a-func`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-20
Updated: 2026-09-20
Source exploration cost: 177322
Source event: `decision-log:1y0bf-ref codenav-graph-handler-modules:15f76633748e6cd6`
Validation: reject
Validated by: agent
Action delta: No additional durable action: preserve the explicit architecture/change contract and native regression tests; do not promote this malformed duplicate.
Validation rationale: Verified 1y0bf decision and current function-local server_impl lookups. Canonical current-state/domain-map documents already specify retained-helper ownership and invocation-time lookup; test_handler_modules pins late binding. Generated lifecycle_gates.py/lifecycle_gate_support.py targets do not exist at those root-relative paths and are not the changed handler boundary.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Decision (wave 1y0h2): Handler modules reach shared helpers through a function-level `import server_impl`; the any-scope import ban that `1y044-ref extract-lifecycle-gate-units` Requirement 3 set for `lifecycle_gates.py` is not extended to them. Rationale: An AST reachability census by the code-reviewer lane found that 113 of the 210 definitions reachable from the nineteen response functions have callers outside them, so an any-scope ban would require moving them into a new support module first, a larger change than this exemplar; the silent-failure risk the ban guards against is covered here by the name-resolution test and the ignore-rule fixture.

## Evidence

- `1y0bf-ref codenav-graph-handler-modules`
- `1y0h2`

## Targets

- `lifecycle_gates.py`
- `lifecycle_gate_support.py`
