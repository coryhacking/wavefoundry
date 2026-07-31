# Decision: Build both legacy presentation and guided actions from one…

Owner: Engineering
Status: superseded
Last verified: 2026-07-29

Memory ID: `1tyy5-mem decision-build-both-legacy-presentation-and-guided-actions-f`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-29
Updated: 2026-07-29
Source exploration cost: 1293653
Source event: `decision-log:1ttp6-enh review-workflow-ergonomics:fab16015b02b8c21`
Validation: rewrite
Validated by: agent
Action delta: When adding a review-state presentation, derive it from review_authority_projection in review_evidence.py; do not parse review_status_rows prose or recompute signoff effects in server_impl.py.
Validation rationale: The decision is durable and current, but the draft targets server_impl.py even though review_evidence.py owns _finding_affects_signoff, review_authority_projection, and review_status_rows. Rewriting corrects the authority target and removes generated punctuation noise.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1tx82-mem decision-keep-review-presentations-on-one-structured-authori`
## Summary

Decision (wave 1tvbs): Build both legacy presentation and guided actions from one structured authority projection.. Rationale: `review_status_rows` is currently presentation-shaped and cannot safely be reparsed for affected approvals; duplicating `_finding_affects_signoff` would recreate the drift this wave is meant to remove..

## Evidence

- `1ttp6-enh review-workflow-ergonomics`
- `1tvbs`

## Targets

- `server_impl.py`
