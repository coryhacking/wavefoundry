# Fragile: .wavefoundry/framework/scripts/tests/test_secrets_validators.py

Owner: Engineering
Status: superseded
Last verified: 2026-10-08

Memory ID: `204mo-mem fragile-wavefoundry-framework-scripts-tests-test-secrets-val`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 1072877
Source event: `repeated-repairs:200ey:.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
Validation: rewrite
Validated by: agent
Action delta: After module reload, patch the dependency owned by the callable under test and include the real preceding reload/import in the regression order.
Validation rationale: The generated three-repair fragility count is false because shared artifact references include distinct findings. The actual MODULE defect is a durable spy-ownership failure: a retained function called its old module dependency while the test patched a reimported module. Current _sv ownership repair and ordered prerequisite prove the specific lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `203is-mem after-reload-spies-must-patch-the-callable-s-retained-depend`

## Summary

.wavefoundry/framework/scripts/tests/test_secrets_validators.py required 3 separate repairs during wave 200ey; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `F-TEST-LAYOUT`
- `F-TEST-MODULE`
- `F-TEST-ACTOR`
- `200ey`

## Targets

- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
