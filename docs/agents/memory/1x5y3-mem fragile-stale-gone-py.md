# Fragile: stale/gone.py

Owner: Engineering
Status: rejected
Last verified: 2026-09-04

Memory ID: `1x5y3-mem fragile-stale-gone-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-04
Updated: 2026-09-04
Source exploration cost: 1539381
Source event: `repeated-repairs:1x54z:stale/gone.py`
Validation: reject
Validated by: agent
Action delta: No durable action: stale/gone.py is the stranded-residue fixture path in the retirement-seam test, not a repository file.
Validation rationale: ARCH-RV1-1 and QA-RV1-1 cite stale/gone.py as the residue seeded to force retire_orphaned_graph_paths to run; the repository has no such file.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

stale/gone.py required 2 separate repairs during wave 1x54z; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `ARCH-RV1-1`
- `QA-RV1-1`
- `1x54z`

## Targets

- `stale/gone.py`
