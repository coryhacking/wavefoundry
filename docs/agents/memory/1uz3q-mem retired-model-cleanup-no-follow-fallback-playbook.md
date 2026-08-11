# Retired-model cleanup no-follow fallback playbook

Owner: Engineering
Status: active
Last verified: 2026-08-11

Memory ID: `1uz3q-mem retired-model-cleanup-no-follow-fallback-playbook`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-11
Updated: 2026-08-11

## Summary

When changing the non-fd retired-model cleanup fallback, do not rely on os.walk(followlinks=False): it can follow a swapped top-level symlink, and Windows junctions are not reported as symlinks. Re-lstat the target immediately before descent, classify symlinks and junctions as nodes, never descend them, and mutation-test both the top-level swap window and junction non-descent with external sentinels.

## Evidence

- `1v0r0-f9-fallback-toctou-top-symlink-follow`
- `1v0r0-f10-fallback-junction-traversal`
- `test_fallback_refuses_top_level_dir_to_symlink_swap_before_descent`
- `test_fallback_classifies_junction_entry_as_node_not_descended`
- `1v0r0`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
- `.wavefoundry/framework/scripts/tests/test_upgrade_wavefoundry.py`
- `symbol:_remove_retired_component_no_follow`
