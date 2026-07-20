# Subprocess diagnostics must not fail UTF-8 decoding

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-subprocess-diagnostics-must-not-fail-utf-8-decoding`
Kind: `environment_gotcha`
Confidence: 0.9
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1p9iy-bug dev-test-infra-windows-hardening:6698822b47133610`
Validation: promote
Validated by: agent
Action delta: Use tolerant UTF-8 decoding at framework subprocess-capture boundaries so diagnostic bytes cannot crash the orchestrator.
Validation rationale: The behavior has since become a shared subprocess utility contract, confirming the lesson while changing its current target.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When capturing framework child stdout or stderr, decode as UTF-8 with replacement rather than strict errors so one stray byte cannot crash the test runner or lifecycle orchestrator while reporting the real child failure.

## Evidence

- `1p9iy-bug dev-test-infra-windows-hardening`
- `1p9j0`
- `.wavefoundry/framework/scripts/subprocess_util.py:24`
- `.wavefoundry/framework/scripts/tests/test_subprocess_util.py:193`

## Targets

- `.wavefoundry/framework/scripts/subprocess_util.py`
