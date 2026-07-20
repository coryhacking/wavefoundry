# Decision: Default artifact placement: clusters artifact.

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-default-artifact-placement-clusters-artifact`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9q1-enh graph-buildtime-betweenness:f2edffe9df914dad`
Validation: reject
Validated by: agent
Action delta: None; inspect the current graph artifact schema and consumer paths before placing new analysis fields.
Validation rationale: The old placement decision is fully represented by current artifact ownership and does not supply independent next-action guidance.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p9q3): Default artifact placement: clusters artifact.. Rationale: `graph_cluster.py` already owns build-time igraph analysis, has its own version field, and keeps the payload (read by every query tool) lean — report-only data belongs with report-shaped analysis..

## Evidence

- `1p9q1-enh graph-buildtime-betweenness`
- `1p9q3`

## Targets

- `graph_cluster.py`
