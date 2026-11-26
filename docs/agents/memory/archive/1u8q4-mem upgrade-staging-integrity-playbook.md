# Upgrade staging and bridge integrity playbook

Owner: Engineering
Status: archived
Last verified: 2026-08-02

Memory ID: `1u8q4-mem upgrade-staging-integrity-playbook`
Superseded by: `24aav-mem upgrade-staging-and-bridge-integrity-playbook`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-08-02
Updated: 2026-11-25
Archived: 2026-11-25
Archive reason: Superseded by 24aav-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1u8q4-mem upgrade-staging-integrity-playbook.md`

## Summary

For upgrade bundle and bridge changes, review path containment, lock acquisition, staged-file retention, and recovery as one integrity matrix: validate identifiers before path construction, test POSIX and Windows path syntax, require exclusive regular-file staging, and cover spawn failure, bridge failure, lock contention, and successful cleanup together.

## Evidence

- `1tz9e-mem`
- `1tzgi-mem`

## Targets

- `.wavefoundry/framework/scripts/upgrade_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
