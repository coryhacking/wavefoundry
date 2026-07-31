# Repaired defect evaluator-v2-transition-unpinned

Owner: Engineering
Status: superseded
Last verified: 2026-07-30

Memory ID: `1twon-mem repaired-defect-evaluator-v2-transition-unpinned`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `finding:1tz6l:evaluator-v2-transition-unpinned`
Validation: rewrite
Validated by: agent
Action delta: For evaluator-version changes, require both byte-level policy tests and a public lifecycle vN-to-vN+1 convergence test.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1ty9f-mem evaluator-version-changes-need-direct-and-public-lifecycle-c`
## Summary

Real defect fixed in wave 1tz6l: The required-AC defect was valid and the bounded repair was independently verified.

## Evidence

- `evaluator-v2-transition-unpinned`
- `ev-evaluator-v2-transition-unpinned-4`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
