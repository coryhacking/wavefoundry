# Fragile: graph_indexer.py

Owner: Engineering
Status: superseded
Last verified: 2026-09-04

Memory ID: `1x84w-mem fragile-graph-indexer-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 1539381
Source event: `repeated-repairs:1x54z:graph_indexer.py`
Validation: rewrite
Validated by: agent
Action delta: When a merge-side preservation widens the current set, widen it in the finalize prune, in _current_paths for link and memory resolution, and skip the record in the impacted-docs rescan; test with scandir denied AND os.stat raising EACCES for the subtree's children.
Validation rationale: The draft counted repairs without the mechanism. The verified mechanism (CODE-DEL-1, RED-RV1-1, ARCH-RV2-1) is that GraphIndexSession reads the walk-derived current set in three places and touches disk in the impacted-docs pass, where Path.exists raises EACCES under a real mode-000 directory on Python 3.13; the class's scandir-only injection left stat succeeding and missed the crash until a lane ran a real chmod.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1x70q-mem graph-indexer-py-three-readers-of-the-walk-derived-current-s`
## Summary

graph_indexer.py required 2 separate repairs during wave 1x54z; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `ARCH-DEL-2`
- `RED-DEL-1`
- `1x54z`

## Targets

- `graph_indexer.py`
