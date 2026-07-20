# Decision: Interim bloat-gated optimize at wave close (before the clos…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-interim-bloat-gated-optimize-at-wave-close-before-t`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1rycf-enh index-bloat-gated-optimize-at-close:c18f076a7e9c25f9`
Validation: reject
Validated by: agent
Action delta: None; inspect the current close-time optimize implementation and current index substrate before changing reclamation.
Validation rationale: The candidate is explicitly interim and tied to an earlier FTS migration rationale; preserving it as durable memory could bias work toward superseded assumptions.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1rycg): Interim bloat-gated optimize at wave close (before the close's background refresh, lock-aware, tier-1 only).. Rationale: Close is a natural batch boundary at the end of a doc-heavy work unit; running optimize before the close's own refresh avoids racing its lock; gating on a bloat ratio makes it a no-op on a tight index; tier-1-only keeps close fast and never spawns an expensive rebuild..

## Evidence

- `1rycf-enh index-bloat-gated-optimize-at-close`
- `1rycg`

## Targets

- `indexer.py`
