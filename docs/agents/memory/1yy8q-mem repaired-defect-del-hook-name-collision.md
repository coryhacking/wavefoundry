# Repaired defect DEL-HOOK-NAME-COLLISION

Owner: Engineering
Status: active
Last verified: 2026-09-24

Memory ID: `1yy8q-mem repaired-defect-del-hook-name-collision`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-24
Updated: 2026-09-24
Source exploration cost: 165164
Source event: `finding:1yzcz:DEL-HOOK-NAME-COLLISION`
Validation: promote
Validated by: agent
Action delta: Name every new rendered host hook in the wf- namespace and test a render over operator files with the common unprefixed name; a hook registry name is an ownership claim over those target files.
Validation rationale: Delivery red-team reproduced operator hook deletion and overwrite through the real renderer; the rename plus a regression test that fails against the old name was independently reverified by two lanes.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

A rendered host hook's registry name is also an ownership claim over target files. `write_hook_bundle` deletes `<name>`, `<name>.sh` and `<name>.cmd` and overwrites `<name>.py`, and `render_claude_settings` drops any settings command containing `.claude/hooks/<name>.py`. A new Claude hook named `session-start` (wave 1yzcz) would therefore have deleted or overwritten an operator's own common `session-start` hook in every target on `wf setup` or upgrade; every readiness and implementation lane missed it, and the delivery red-team found it by rendering over operator files. Name new rendered hooks in the framework-owned `wf-` namespace, never add a common operator name to stale-file cleanup, and pin it with a render-over-operator-files test.

## Evidence

- `DEL-HOOK-NAME-COLLISION`
- `ev-del-hook-name-collision-3`
- `1yzcz`

## Targets

- `.wavefoundry/framework/scripts/tests/test_session_start_hook.py`
- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
