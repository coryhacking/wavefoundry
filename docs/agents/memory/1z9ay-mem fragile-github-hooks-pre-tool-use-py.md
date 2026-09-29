# Fragile: .github/hooks/pre-tool-use.py

Owner: Engineering
Status: superseded
Last verified: 2026-09-28

Memory ID: `1z9ay-mem fragile-github-hooks-pre-tool-use-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-28
Updated: 2026-09-28
Source exploration cost: 311829
Source event: `repeated-repairs:1z8ot:.github/hooks/pre-tool-use.py`
Validation: rewrite
Validated by: agent
Action delta: When a gated host tool carries a sub-command (text-editor view vs str_replace), classify on the command as well as the tool name, fail closed on unknown commands, and test both the pre hook (block) and the post hook (no lint or reindex on reads).
Validation rationale: DEL-F4 evidence (ev-del-f4-3): classifying str_replace_editor by name blocked read-only view and made the post hook lint and reindex reads. The generated candidate named the rendered hook and gave generic advice; the source is render_platform_surfaces.copilot_is_edit shared by both hooks. Supplements 1z99f (allowlist drift) with the command dimension.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1zbio-mem edit-gate-classification-needs-the-command-not-just-the-tool`

## Summary

.github/hooks/pre-tool-use.py required 2 separate repairs during wave 1z8ot; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `DEL-F1`
- `DEL-F4`
- `1z8ot`

## Targets

- `.github/hooks/pre-tool-use.py`
