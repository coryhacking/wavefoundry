# Copilot edit-gate classification: keep tool lists and command reads in sync

Owner: Engineering
Status: active
Last verified: 2026-10-26

Memory ID: `21rnt-mem copilot-edit-gate-classification-keep-tool-lists-and-command`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-10-26
Updated: 2026-10-26
Source exploration cost: 181396
Supersedes: `1z99f-mem host-edit-gate-tool-lists-are-allowlists-that-drift`

## Summary

`render_platform_surfaces.copilot_tool_classification` feeds both Copilot pre and post hooks, and its tool-name lists are allowlists that drift. When adding or renaming a host edit tool, add it to `COPILOT_EDIT_TOOL_NAMES` with one fixture per name (`test_host_payload_fixtures_reach_the_gate` enforces this); an unlisted tool is reported as unknown and is gated only when it carries a file path. For text-editor tools classify on the command too: only exact read commands such as `view` are non-edits, and missing or unfamiliar commands stay edits. Re-render the hooks, probe the rendered hook in a scratch root with its own guard overrides, and test that the pre hook blocks and the post hook does not lint or reindex reads.

## Evidence

- `consolidated from 1z99f-mem host-edit-gate-tool-lists-are-allowlists-that-drift`
- `consolidated from 1zbio-mem edit-gate-classification-needs-the-command-not-just-the-tool`

## Targets

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
