# Decision: No before-and-after standing evaluation across this change;…

Owner: Engineering
Status: rejected
Last verified: 2026-09-20

Memory ID: `1yia6-mem decision-no-before-and-after-standing-evaluation-across-this`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-20
Updated: 2026-09-20
Source exploration cost: 177322
Source event: `decision-log:1y0bf-ref codenav-graph-handler-modules:21a382fd0b874690`
Validation: reject
Validated by: agent
Action delta: No additional durable action: preserve the explicit architecture/change contract and native regression tests; do not promote this malformed duplicate.
Validation rationale: Verified 1y0bf Requirement 11 and Decision Log own this deliberately wave-scoped baseline restart. It is not a general exemption from before/after evaluation. Generated server_impl.py target does not exist at repository root and is not the compatibility guard owner; no durable additional action.
Evidence verified: true
Current target verified: false
Canonical overlap: duplicates
## Summary

Decision (wave 1y0h2): No before-and-after standing evaluation across this change; the post-move run becomes the new baseline. Rationale: `_validate_baseline_compatibility` already refuses every recorded report at `f4063a85`, on fixture schema v1 against the current v2 and on a digest the evaluator's own normalization has moved, so the chain was broken before this change; the corpus edit and the production-identity change each break it again.

## Evidence

- `1y0bf-ref codenav-graph-handler-modules`
- `1y0h2`

## Targets

- `server_impl.py`
