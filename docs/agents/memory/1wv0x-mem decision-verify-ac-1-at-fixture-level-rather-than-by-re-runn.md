# Decision: Verify AC-1 at fixture level rather than by re-running the…

Owner: Engineering
Status: rejected
Last verified: 2026-09-01

Memory ID: `1wv0x-mem decision-verify-ac-1-at-fixture-level-rather-than-by-re-runn`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-01
Updated: 2026-09-01
Source exploration cost: 125943
Source event: `decision-log:1wtpl-bug retrieval-eval-store-identity-binding:666dc027db28224a`
Validation: reject
Validated by: agent
Action delta: No durable action: this was a wave-local verification choice forced by the evaluator's own identity binding, and the general lesson (a receipt recorded before an evaluator change cannot be replayed after it) is already stated in docs/contributing/review-and-evals.md and the CHANGELOG discontinuity note.
Validation rationale: Evidence followed: the 1wtpl Decision Log row (readiness CODE-RDY-5, QA-RDY-4) and the fixture-level tests in test_retrieval_eval.py that AC-1 relies on. Current target verified: retrieval_eval.py binds evaluator_identity unconditionally at the compatibility check, as the row states. The choice does not generalize beyond this wave's verification plan.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1wur7): Verify AC-1 at fixture level rather than by re-running the receipts it names (readiness CODE-RDY-5, QA-RDY-4).. Rationale: Landing this change alters `retrieval_eval.py`'s bytes and therefore `evaluator_identity`, which the compatibility rule binds unconditionally, so the `1wpif` pair is refused for a different reason before the identity rule is reached. The recorded inode values remain the fixture's provenance..

## Evidence

- `1wtpl-bug retrieval-eval-store-identity-binding`
- `1wur7`

## Targets

- `retrieval_eval.py`
