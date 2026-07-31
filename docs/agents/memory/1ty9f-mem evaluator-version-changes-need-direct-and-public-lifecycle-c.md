# Evaluator-version changes need direct and public lifecycle convergence pins

Owner: Engineering
Status: active
Last verified: 2026-07-30

Memory ID: `1ty9f-mem evaluator-version-changes-need-direct-and-public-lifecycle-c`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `finding:1tz6l:evaluator-v2-transition-unpinned`
Validation: promote
Validated by: agent
Action delta: For evaluator-version changes, require both byte-level policy tests and a public lifecycle vN-to-vN+1 convergence test.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Bumping the review-policy evaluator is not covered by testing the evaluator in isolation. Pin the new version and closed-ledger bytes directly, then exercise a real public prepare transition from the prior evaluator receipt to the new one and prove one-time convergence.

## Evidence

- `evaluator-v2-transition-unpinned`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
