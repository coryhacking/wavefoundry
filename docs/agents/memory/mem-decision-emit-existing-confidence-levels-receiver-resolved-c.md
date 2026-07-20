# Decision: Emit existing confidence levels (`RECEIVER_RESOLVED`/`CONST…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-emit-existing-confidence-levels-receiver-resolved-c`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9q4-enh python-receiver-annotation-resolution:c1f2e761fcabba2a`
Validation: reject
Validated by: agent
Action delta: None; use the current graph confidence taxonomy and its tests.
Validation rationale: The confidence-tier choice is a canonical graph schema detail, not a supplemental memory.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p9q8): Emit existing confidence levels (`RECEIVER_RESOLVED`/`CONSTRUCTION_RESOLVED`), no new tier.. Rationale: The taxonomy already distinguishes exactly these two evidence classes; downstream weights (`graph_query.py`) work unchanged..

## Evidence

- `1p9q4-enh python-receiver-annotation-resolution`
- `1p9q8`

## Targets

- `graph_query.py`
