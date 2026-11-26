# Upgrade staging and bridge integrity playbook

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24aav-mem upgrade-staging-and-bridge-integrity-playbook`
Kind: `fragile_file`
Confidence: 0.9
Created: 2026-11-25
Updated: 2026-11-26
Supersedes: `1u8q4-mem upgrade-staging-integrity-playbook`
Checked at: 2026-11-26T06:32:43Z
Check note: Upgrade staging and bridge bootstrap both process package members; check member containment and bootstrapping constraints together. Reviewed .wavefoundry/framework/scripts/tests/test_upgrade_protocol.py:483.
Check flags: none

## Summary

When changing upgrade bundle staging or the bridge bootstrap (.wavefoundry/framework/scripts/upgrade_bundle.py, upgrade_bridge_bootstrap.py), review path containment, lock acquisition, staged-file retention and recovery as one integrity matrix: validate identifiers before building paths, test POSIX and Windows path syntax (_safe_artifact_basename checks both), require exclusive regular-file staging (open('xb')), and cover spawn failure, bridge failure, lock contention and successful cleanup together in tests/test_upgrade_protocol.py. The source findings each fixed one corner and reopened another when reviewed alone.

## Evidence

- `1tz9e-mem upgrade-bundle-handoff-needs-cross-platform-containment-and-`
- `1tzgi-mem`
- `test_spawn_failure_after_bridge_swap_returns_bounded_recovery`
- `test_bridge_refuses_symlinked_lock_paths_and_creates_nothing_outside`

## Targets

- `.wavefoundry/framework/scripts/upgrade_bundle.py`
- `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_protocol.py`
