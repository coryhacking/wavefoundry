# Retired-model cleanup no-follow fallback playbook

Owner: Engineering
Status: archived
Last verified: 2026-08-11

Memory ID: `1uz3q-mem retired-model-cleanup-no-follow-fallback-playbook`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-11
Updated: 2026-11-25
Checked at: 2026-11-25T16:09:20Z
Check note: Item 7 review: encoded elsewhere. Both halves of the lesson fail a named test on regression. tests/test_upgrade_wavefoundry.py:5443 test_fallback_refuses_top_level_dir_to_symlink_swap_before_descent covers the top-level swap re-check. tests/test_upgrade_wavefoundry.py:5506 test_fallback_classifies_junction_entry_as_node_not_descended covers junction non-descent. The docstring of _remove_retired_c.
Check flags: target_churn
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, encoded in Both halves of the lesson fail a named test on regression. tests/test_upgrade_wavefoundry.py:5443 test_fallback_refuses_top_level_dir_to_symlink_swap_before_descent covers the top-level swap re-check. tests/test_upgrade_wavefoundry.py:5506 test_fallbac.
Archive path: `docs/agents/memory/archive/1uz3q-mem retired-model-cleanup-no-follow-fallback-playbook.md`

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
