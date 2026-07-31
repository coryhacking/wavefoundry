# Upgrade bridge bootstrap spans three fragile integrity boundaries

Owner: Engineering
Status: active
Last verified: 2026-07-30

Memory ID: `1tzgi-mem upgrade-bridge-bootstrap-spans-three-fragile-integrity-bound`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `repeated-repairs:1tz6l:.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
Validation: promote
Validated by: agent
Action delta: When editing upgrade_bridge_bootstrap.py, rerun invalid-ID/no-mutation, contended-Windows-lock, and preexisting-link retention probes together.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

The bridge bootstrap must validate bridge_build_id before any path construction, acquire the Windows lock without first mutating its carrier, and retain feature bundles through an exclusively created regular file inside upgrade-assets. A repair at one boundary must be checked against the other two.

## Evidence

- `bridge-build-id-path-escape`
- `windows-bridge-lock-mutates-before-acquire`
- `retained-feature-staging-follows-existing-link`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
