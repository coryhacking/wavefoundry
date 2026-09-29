# Host edit-gate tool lists are allowlists that drift

Owner: Engineering
Status: active
Last verified: 2026-09-28

Memory ID: `1z99f-mem host-edit-gate-tool-lists-are-allowlists-that-drift`
Kind: `fragile_file`
Confidence: 0.8
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 181396
Source event: `finding:1z8ot:DEL-F1`
Validation: promote
Validated by: agent
Action delta: When adding or renaming a host edit tool, add its name to the host's edit-tool list in render_platform_surfaces with a fixture (the coverage assertion enforces it), and probe the rendered hook with that name before trusting the gate.
Validation rationale: DEL-F1 evidence (ev-del-f1, ev-del-f1-3): the Copilot gate is an allowlist of tool names; unlisted names (insert_edit_into_file, write) passed with the gate closed until added. The generated candidate targeted the rendered hook and carried no action; the source of truth is render_platform_surfaces.COPILOT_EDIT_TOOL_NAMES and its fixture test.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

The Copilot pre-tool-use gate only blocks tool names in COPILOT_EDIT_TOOL_NAMES; an unlisted or renamed file-writing tool passes ungated. Keep one fixture per listed name (test_host_payload_fixtures_reach_the_gate asserts coverage), probe the rendered hook in a scratch root with its own guard-overrides, and re-render the hook surfaces after changing the list.

## Evidence

- `DEL-F1`
- `ev-del-f1`
- `ev-del-f1-3`
- `1z8ot`

## Targets

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/tests/test_render_platform_surfaces.py`
