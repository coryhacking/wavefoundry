# Upgrade-time shared constants go in a new stdlib-only module

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24av2-mem upgrade-time-shared-constants-go-in-a-new-stdlib-only-module`
Kind: `decision`
Confidence: 0.8
Created: 2026-11-25
Updated: 2026-11-25
Source exploration cost: 97308
Supersedes: `1zyhu-mem decision-the-shared-constant-lives-in-a-new-stdlib-only-hist`

## Summary

When upgrade-time code needs a new shared constant or helper, put it in a new stdlib-only module (as wave 1zyb2 did with .wavefoundry/framework/scripts/history_paths.py) rather than as a new attribute on a module an older process may already hold in sys.modules, such as record_paths.py. Why: during an upgrade the running process may hold an old record_paths (a 1.27 RecordRoots without archive), so a new attribute could raise AttributeError at the upgrade_extensions.py call sites; a new module imports fresh, and upgrade_extensions.py imports is_history_path function-locally.

## Evidence

- `1zxnt-maint correctness-and-test-hygiene-round`
- `1zyb2`

## Targets

- `.wavefoundry/framework/scripts/history_paths.py`
- `.wavefoundry/framework/scripts/record_paths.py`
- `.wavefoundry/framework/scripts/upgrade_extensions.py`
