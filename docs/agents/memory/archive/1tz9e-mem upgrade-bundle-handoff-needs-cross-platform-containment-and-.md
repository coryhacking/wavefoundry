# Upgrade bundle handoff needs cross-platform containment and total recovery

Owner: Engineering
Status: archived
Last verified: 2026-07-30

Memory ID: `1tz9e-mem upgrade-bundle-handoff-needs-cross-platform-containment-and-`
Superseded by: `1u8q4-mem upgrade-staging-integrity-playbook`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-07-30
Updated: 2026-08-02
Source exploration cost: 1297806
Source event: `repeated-repairs:1tz6l:.wavefoundry/framework/scripts/upgrade_bundle.py`
Validation: promote
Validated by: agent
Action delta: When editing upgrade_bundle.py, test Windows and POSIX payload names plus spawn-failure, bridge-failure, and primary-success cleanup as one recovery matrix.
Validation rationale: The source finding is durable, but the generated draft was too generic or targeted only the test carrier; this rewrite states the reusable mechanism and verified implementation targets.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1tz9e-mem upgrade-bundle-handoff-needs-cross-platform-containment-and-.md`
## Summary

The combined upgrade bundle must treat both POSIX and Windows separators as path syntax and make feature-to-bridge recovery terminal across spawn failure, bridge failure, and primary success. Partial cleanup or host-native basename checks leave platform-specific escape and residue paths.

## Evidence

- `bundle-windows-backslash-payload-escape`
- `combined-hop-recovery-not-terminal-or-total`
- `1tz6l`

## Targets

- `.wavefoundry/framework/scripts/upgrade_bundle.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
