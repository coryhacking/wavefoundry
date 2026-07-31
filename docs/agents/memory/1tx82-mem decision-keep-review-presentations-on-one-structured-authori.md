# Decision: Keep review presentations on one structured authority

Owner: Engineering
Status: active
Last verified: 2026-07-29

Memory ID: `1tx82-mem decision-keep-review-presentations-on-one-structured-authori`
Kind: `decision`
Confidence: 0.9
Created: 2026-07-29
Updated: 2026-07-29
Source exploration cost: 1293653
Source event: `decision-log:1ttp6-enh review-workflow-ergonomics:fab16015b02b8c21`
Validation: promote
Validated by: agent
Action delta: When adding a review-state presentation, derive it from review_authority_projection in review_evidence.py; do not parse review_status_rows prose or recompute signoff effects in server_impl.py.
Validation rationale: The decision is durable and current, but the draft targets server_impl.py even though review_evidence.py owns _finding_affects_signoff, review_authority_projection, and review_status_rows. Rewriting corrects the authority target and removes generated punctuation noise.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Review status rows, forensic listing, and guided actions must consume the single structured authority in review_evidence.py. Do not parse human-readable status prose or duplicate signoff-affect logic in server_impl.py.

## Evidence

- `1ttp6-enh review-workflow-ergonomics`
- `1tvbs`
- `review_evidence.py:review_authority_projection`

## Targets

- `.wavefoundry/framework/scripts/review_evidence.py`
- `.wavefoundry/framework/scripts/server_impl.py`
