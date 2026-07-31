# Fragile: .wavefoundry/framework/scripts/upgrade_bundle.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-30

Memory ID: `1tyn3-mem fragile-wavefoundry-framework-scripts-upgrade-bundle-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-30
Updated: 2026-07-30
Source exploration cost: 1297806
Source event: `repeated-repairs:1tz6l:.wavefoundry/framework/scripts/upgrade_bundle.py`
Validation: rewrite
Validated by: agent
Action delta: When editing upgrade_bundle.py, test Windows and POSIX payload names plus spawn-failure, bridge-failure, and primary-success cleanup as one recovery matrix.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tz9e-mem upgrade-bundle-handoff-needs-cross-platform-containment-and-`
## Summary

.wavefoundry/framework/scripts/upgrade_bundle.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `bundle-windows-backslash-payload-escape`
- `combined-hop-recovery-not-terminal-or-total`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/upgrade_bundle.py`
