# Decision: Shared helpers EXTRACTED ALONGSIDE the graph store (new `in…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-shared-helpers-extracted-alongside-the-graph-store-`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1rq4h-enh sqlite-index-state-store:98f55a77417ca4de`
Validation: reject
Validated by: agent
Action delta: None; inspect the current module boundaries and wiring tests before considering any future refactor.
Validation rationale: The extract-alongside choice was wave-local risk containment, not a durable prohibition; current source and tests are authoritative.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1rsh9): Shared helpers EXTRACTED ALONGSIDE the graph store (new `index_state_store.py` modeled on `GraphStateStore`) rather than refactoring `graph_indexer.py` to use a common module.. Rationale: Zero risk to the landed, reviewed graph store (AC-7 satisfied by construction: zero edits to `graph_indexer.py`); the module documents the graph-store provenance, and a wiring-lock test pins the duplicated graph-store path constant to `graph_indexer`'s values..

## Evidence

- `1rq4h-enh sqlite-index-state-store`
- `1rsh9`

## Targets

- `index_state_store.py`
- `graph_indexer.py`
