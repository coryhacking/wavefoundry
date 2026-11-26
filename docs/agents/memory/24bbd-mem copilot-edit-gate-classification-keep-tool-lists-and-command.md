# Copilot edit-gate classification: keep tool lists and command reads exact

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `24bbd-mem copilot-edit-gate-classification-keep-tool-lists-and-command`
Kind: `fragile_file`
Confidence: 0.7
Created: 2026-11-25
Updated: 2026-11-26
Source exploration cost: 181396
Supersedes: `21rnt-mem copilot-edit-gate-classification-keep-tool-lists-and-command`
Checked at: 2026-11-26T06:32:44Z
Check note: Copilot editor commands distinguish reads from writes. A host tool rename requires checking both lists and generated hooks. Reviewed .wavefoundry/framework/scripts/render_platform_surfaces.py:1497.
Check flags: none

## Summary

When adding or renaming a Copilot host edit tool, or changing how its text-editor commands are classified, add the tool to COPILOT_EDIT_TOOL_NAMES in .wavefoundry/framework/scripts/render_platform_surfaces.py with one fixture per name, and treat only exact read commands in COPILOT_TEXT_EDITOR_READ_COMMANDS (such as view) as non-edits; missing or unfamiliar commands stay edits. Then re-render the hooks, probe the rendered hook in a scratch root with its own guard overrides, and test that the pre hook blocks and the post hook does not lint or reindex reads. Why: copilot_tool_classification feeds both pre and post hooks and its lists are allowlists that drift; an unlisted tool is reported unknown and is gated only when it carries a file path. tests/test_render_platform_surfaces.py test_host_payload_fixtures_reach_the_gate enforces the per-name fixture.

## Evidence

- `consolidated from 1z99f-mem host-edit-gate-tool-lists-are-allowlists-that-drift`
- `consolidated from 1zbio-mem edit-gate-classification-needs-the-command-not-just-the-tool`
- `test_render_platform_surfaces.RenderedEditHookPathTests.test_host_payload_fixtures_reach_the_gate`

## Targets

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
