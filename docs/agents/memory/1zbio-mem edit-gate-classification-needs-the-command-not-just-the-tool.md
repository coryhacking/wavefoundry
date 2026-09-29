# Edit-gate classification needs the command, not just the tool name

Owner: Engineering
Status: active
Last verified: 2026-09-28

Memory ID: `1zbio-mem edit-gate-classification-needs-the-command-not-just-the-tool`
Kind: `fragile_file`
Confidence: 0.8
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 311829
Source event: `repeated-repairs:1z8ot:.github/hooks/pre-tool-use.py`
Validation: promote
Validated by: agent
Action delta: When a gated host tool carries a sub-command (text-editor view vs str_replace), classify on the command as well as the tool name, fail closed on unknown commands, and test both the pre hook (block) and the post hook (no lint or reindex on reads).
Validation rationale: DEL-F4 evidence (ev-del-f4-3): classifying str_replace_editor by name blocked read-only view and made the post hook lint and reindex reads. The generated candidate named the rendered hook and gave generic advice; the source is render_platform_surfaces.copilot_is_edit shared by both hooks. Supplements 1z99f (allowlist drift) with the command dimension.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

render_platform_surfaces.copilot_is_edit is shared by the Copilot pre and post hooks. Text-editor tools (str_replace_editor, str_replace_based_edit_tool) run both reads (view) and writes, so name-only classification blocks reads and makes the post hook lint and reindex them. Read the command from the same place as the path, treat only exact view as a read, keep unknown or missing commands as edits, and test both hooks.

## Evidence

- `DEL-F4`
- `ev-del-f4-3`
- `1z8ot`

## Targets

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
