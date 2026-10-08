# Fragile: .wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py

Owner: Engineering
Status: rejected
Last verified: 2026-10-08

Memory ID: `20375-mem fragile-wavefoundry-framework-scripts-tests-test-server-tool`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 1072877
Source event: `repeated-repairs:200ey:.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
Validation: reject
Validated by: agent
Action delta: No three-repair fragility claim; preserve the current exact actor-normalization and historical hash contract.
Validation rationale: Only F-TEST-ACTOR changed this file in cycle 2; other shared findings repaired other files. Existing exact current-actor assertions, original hashes and unrelated-byte control document the bounded compatibility rule.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py required 3 separate repairs during wave 200ey; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `F-TEST-LAYOUT`
- `F-TEST-MODULE`
- `F-TEST-ACTOR`
- `200ey`

## Targets

- `.wavefoundry/framework/scripts/tests/test_server_tools_lifecycle.py`
