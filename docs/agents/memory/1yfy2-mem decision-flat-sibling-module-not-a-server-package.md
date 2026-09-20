# Decision: Flat sibling module, not a `server/` package

Owner: Engineering
Status: rejected
Last verified: 2026-09-19

Memory ID: `1yfy2-mem decision-flat-sibling-module-not-a-server-package`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-19
Updated: 2026-09-19
Source exploration cost: 384402
Source event: `decision-log:1y0be-ref tool-registry-and-wrapper-chain:7b615ca09dc0f3de`
Validation: reject
Validated by: agent
Action delta: No separate memory: the decision and its reload and packaging reasoning are carried by the accepted decision record 1ye5y-adr, which is the canonical source.
Validation rationale: The candidate restates the Decision Log row that became 1ye5y-adr flat-sibling-tool-registry, which states the same reasoning with its constraints and revisit trigger and is linked from the architecture hub. A memory would duplicate a canonical record.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1y0h1): Flat sibling module, not a `server/` package. Rationale: Hot reload purges named sibling modules and `_load_script` caches flat files; `build_pack.py` tree-walks the scripts directory; both work unchanged with a flat module.

## Evidence

- `1y0be-ref tool-registry-and-wrapper-chain`
- `1y0h1`

## Targets

- `build_pack.py`
