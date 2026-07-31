# Fragile: .wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-30

Memory ID: `1tx0a-mem fragile-wavefoundry-framework-scripts-upgrade-bridge-bootstr`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `repeated-repairs:1tz6l:.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
Validation: rewrite
Validated by: agent
Action delta: When editing upgrade_bridge_bootstrap.py, rerun invalid-ID/no-mutation, contended-Windows-lock, and preexisting-link retention probes together.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tzgi-mem upgrade-bridge-bootstrap-spans-three-fragile-integrity-bound`
## Summary

.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py required 3 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `bridge-build-id-path-escape`
- `windows-bridge-lock-mutates-before-acquire`
- `retained-feature-staging-follows-existing-link`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
