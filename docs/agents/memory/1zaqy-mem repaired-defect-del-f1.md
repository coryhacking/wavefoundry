# Repaired defect DEL-F1

Owner: Engineering
Status: superseded
Last verified: 2026-09-28

Memory ID: `1zaqy-mem repaired-defect-del-f1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 181396
Source event: `finding:1z8ot:DEL-F1`
Validation: rewrite
Validated by: agent
Action delta: When adding or renaming a host edit tool, add its name to the host's edit-tool list in render_platform_surfaces with a fixture (the coverage assertion enforces it), and probe the rendered hook with that name before trusting the gate.
Validation rationale: DEL-F1 evidence (ev-del-f1, ev-del-f1-3): the Copilot gate is an allowlist of tool names; unlisted names (insert_edit_into_file, write) passed with the gate closed until added. The generated candidate targeted the rendered hook and carried no action; the source of truth is render_platform_surfaces.COPILOT_EDIT_TOOL_NAMES and its fixture test.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1z99f-mem host-edit-gate-tool-lists-are-allowlists-that-drift`

## Summary

Real defect fixed in wave 1z8ot: Resolved: the original failure scenario is now caught.

## Evidence

- `DEL-F1`
- `ev-del-f1-3`
- `1z8ot`

## Targets

- `.github/hooks/pre-tool-use.py`
