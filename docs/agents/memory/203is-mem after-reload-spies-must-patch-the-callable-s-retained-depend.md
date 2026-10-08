# After reload, spies must patch the callable's retained dependency owner

Owner: Engineering
Status: active
Last verified: 2026-10-08

Memory ID: `203is-mem after-reload-spies-must-patch-the-callable-s-retained-depend`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 1072877
Source event: `repeated-repairs:200ey:.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
Validation: promote
Validated by: agent
Action delta: After module reload, patch the dependency owned by the callable under test and include the real preceding reload/import in the regression order.
Validation rationale: The generated three-repair fragility count is false because shared artifact references include distinct findings. The actual MODULE defect is a durable spy-ownership failure: a retained function called its old module dependency while the test patched a reimported module. Current _sv ownership repair and ordered prerequisite prove the specific lesson.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When a test retains a callable across server module eviction/reload, a new import can expose a different module object. Patch the dependency in the retained callable's owning module or globals, and test the reachable ordered reload/import prerequisite; an isolated test can pass while the owner-file run misses every spy call.

## Evidence

- `200ey`
- `F-TEST-MODULE`
- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py:2131`
- `.wavefoundry/framework/scripts/wf_server/server_impl.py`

## Targets

- `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
- `.wavefoundry/framework/scripts/tests/test_distribution_seams.py`
