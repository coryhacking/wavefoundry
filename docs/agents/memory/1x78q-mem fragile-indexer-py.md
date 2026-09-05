# Fragile: indexer.py

Owner: Engineering
Status: superseded
Last verified: 2026-09-04

Memory ID: `1x78q-mem fragile-indexer-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 1539381
Source event: `repeated-repairs:1x54z:indexer.py`
Validation: rewrite
Validated by: agent
Action delta: A guard on what the walk yields must be threaded to change detection, the Lance reap, the orphan reconcile and the graph merge, each pinned by a guard-deletion mutant; a guard placed in the reap alone misses four earlier deleters.
Validation rationale: The draft counted repairs without the mechanism. The verified mechanism (plan review Level 2 finding, CODE-DEL-1, RED-DEL-1, ARCH-RV1-1) is that the incremental Lance write, the layer-hash commit and the secrets ledger delete on the removal set before the reap runs and the graph merge derives its own removal set from the walk, so preservation must be threaded through every consumer of the walk output.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1x78p-mem indexer-py-the-reap-is-not-the-first-deleter-so-walk-output-`
## Summary

indexer.py required 2 separate repairs during wave 1x54z; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `ARCH-DEL-2`
- `RED-DEL-1`
- `1x54z`

## Targets

- `indexer.py`
