# indexer.py: the reap is not the first deleter, so walk-output guards must reach every consumer

Owner: Engineering
Status: active
Last verified: 2026-09-04

Memory ID: `1x78p-mem indexer-py-the-reap-is-not-the-first-deleter-so-walk-output-`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 1539381
Source event: `repeated-repairs:1x54z:indexer.py`
Validation: promote
Validated by: agent
Action delta: A guard on what the walk yields must be threaded to change detection, the Lance reap, the orphan reconcile and the graph merge, each pinned by a guard-deletion mutant; a guard placed in the reap alone misses four earlier deleters.
Validation rationale: The draft counted repairs without the mechanism. The verified mechanism (plan review Level 2 finding, CODE-DEL-1, RED-DEL-1, ARCH-RV1-1) is that the incremental Lance write, the layer-hash commit and the secrets ledger delete on the removal set before the reap runs and the graph merge derives its own removal set from the walk, so preservation must be threaded through every consumer of the walk output.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

In _build_index_locked the incremental Lance write deletes the removal set, the layer-hash commit and the secrets ledger drop removed_broad, and the graph merge derives its own removal set from the walk, all before or beside the eligibility reap. Wave 1x54z's walk-shadow preservation therefore lives at change detection (carry the bookkeeping forward, withhold from removal), in the reap and the orphan reconcile (classify shadowed candidates without a stat), and in the graph merge through unreadable_dirs at both entry points; the delivery review caught the graph seam only because a pre-wave control re-graphed on recovery. When changing what walk_repo yields or how removal is derived, enumerate those consumers and pin each with a guard-deletion mutant in a scratch copy.

## Evidence

- `CODE-DEL-1`
- `RED-DEL-1`
- `ARCH-RV1-1`
- `test_walk_dropped_subtree_survives_a_build_path_run`
- `test_retirement_seam_keeps_the_shadowed_subtree`
- `1x54z`

## Targets

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/graph_indexer.py`
