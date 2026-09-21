# Decision: Modules never import `server_impl` at top level

Owner: Engineering
Status: rejected
Last verified: 2026-09-20

Memory ID: `1yj4e-mem decision-modules-never-import-server-impl-at-top-level`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-20
Updated: 2026-09-20
Source exploration cost: 177322
Source event: `decision-log:1y0bf-ref codenav-graph-handler-modules:b4bf429cadde6b95`
Validation: reject
Validated by: agent
Action delta: No additional durable action: preserve the explicit architecture/change contract and native regression tests; do not promote this malformed duplicate.
Validation rationale: Verified the decision in 1y0bf and current handler modules. docs/architecture/current-state.md:83 and domain-map.md:34 already state the no-module-top composition-root import contract. Generated target techdocs_audit_lib.py does not exist at repository root and points at an analogy, not these handlers.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Decision (wave 1y0h2): Modules never import `server_impl` at top level. Rationale: Prevents a cycle and keeps each module testable in isolation; matches the existing `techdocs_audit_lib.py` rule.

## Evidence

- `1y0bf-ref codenav-graph-handler-modules`
- `1y0h2`

## Targets

- `techdocs_audit_lib.py`
