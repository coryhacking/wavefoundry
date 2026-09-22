# Decision: Wave-level before-and-after receipt pair, not a conditional…

Owner: Engineering
Status: rejected
Last verified: 2026-09-22

Memory ID: `1yldr-mem decision-wave-level-before-and-after-receipt-pair-not-a-cond`
Kind: `decision`
Confidence: 0.6
Created: 2026-09-21
Updated: 2026-09-21
Source exploration cost: 394325
Source event: `decision-log:1ymzj-ref memory-handler-module:02bf225705d17a73`
Validation: reject
Validated by: agent
Action delta: No additional memory action: apply the existing production-retrieval before/after evaluation policy to composition-root changes.
Validation rationale: Verified Decision Log, retrieval_eval.PRODUCTION_RETRIEVAL_MODULES includes server_impl.py, and docs/contributing/review-and-evals.md states the production-change before/after obligation and moved-evaluator handling. Candidate repeats that maintained canonical policy with a wave-local justification and basename target. High confidence in duplication; reject to avoid a second policy authority.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 1ymzk): Wave-level before-and-after receipt pair, not a conditional rerun.. Rationale: `server_impl.py` is a production retrieval module and both changes edit it; the obligation is documented and does not depend on the new module's membership..

## Evidence

- `1ymzj-ref memory-handler-module`
- `1ymzk`

## Targets

- `server_impl.py`
