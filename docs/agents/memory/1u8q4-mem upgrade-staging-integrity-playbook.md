# Upgrade staging and bridge integrity playbook

Owner: Engineering
Status: active
Last verified: 2026-08-02

Memory ID: `1u8q4-mem upgrade-staging-integrity-playbook`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-08-02
Updated: 2026-08-02

## Summary

For upgrade bundle and bridge changes, review path containment, lock acquisition, staged-file retention, and recovery as one integrity matrix: validate identifiers before path construction, test POSIX and Windows path syntax, require exclusive regular-file staging, and cover spawn failure, bridge failure, lock contention, and successful cleanup together.

## Evidence

- `1tz9e-mem`
- `1tzgi-mem`

## Targets

- `.wavefoundry/framework/scripts/upgrade_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
