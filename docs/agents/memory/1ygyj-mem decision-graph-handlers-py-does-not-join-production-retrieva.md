# Decision: `graph_handlers.py` does not join `PRODUCTION_RETRIEVAL_MOD…

Owner: Engineering
Status: rejected
Last verified: 2026-09-20

Memory ID: `1ygyj-mem decision-graph-handlers-py-does-not-join-production-retrieva`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-20
Updated: 2026-09-20
Source exploration cost: 177322
Source event: `decision-log:1y0bf-ref codenav-graph-handler-modules:e1d8a44e37882956`
Validation: reject
Validated by: agent
Action delta: No additional durable action: preserve the explicit architecture/change contract and native regression tests; do not promote this malformed duplicate.
Validation rationale: Verified retrieval_eval.py PRODUCTION_RETRIEVAL_MODULES contains codenav_handlers.py and excludes graph_handlers.py; 1y0bf Requirement 9 owns the measured-reachability rule. This generated record adds no action beyond that rule and is conditional on the current measured tool set. graph_handlers.py is not a valid root-relative target.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Decision (wave 1y0h2): `graph_handlers.py` does not join `PRODUCTION_RETRIEVAL_MODULES`. Rationale: An AST reachability closure from the four measured tools in `retrieval_eval.TOOLS` reaches none of the seven graph response functions, and a helper moves only when the moved set is its only caller, so no measured path can reach the module.

## Evidence

- `1y0bf-ref codenav-graph-handler-modules`
- `1y0h2`

## Targets

- `graph_handlers.py`
