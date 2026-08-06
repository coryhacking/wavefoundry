# Decision: Carry the current judgment template and a blocking constrai…

Owner: Engineering
Status: active
Last verified: 2026-08-05

Memory ID: `1uj4o-mem decision-carry-the-current-judgment-template-and-a-blocking-`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-05
Updated: 2026-08-05
Source exploration cost: 625845
Source event: `decision-log:1ug68-enh guided-review-action-carries-its-schema:bdf7291c622f2a0c`
Validation: promote
Validated by: agent
Action delta: When a review action describes an existing finding, carry its current judgment template and blocking constraint instead of reconstructing either from prose.
Validation rationale: The decision is reusable at the review-action boundary, verified in the current target, and the focused search found no active canonical duplicate.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

Decision (wave 1ui1d): Carry the current judgment template and a blocking constraint; change neither `derive_blocking` nor the retention rule. Rationale: Both are correct. The template is more useful than paraphrasing a predicate: it tells the caller exactly which existing judgment to preserve while the constraint explains why the lanes remain.

## Evidence

- `1ug68-enh guided-review-action-carries-its-schema`
- `1ui1d`

## Targets

- `review_evidence.py`
