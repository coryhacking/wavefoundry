# Separate generated-file newline policy from in-place patching

Owner: Engineering
Status: active
Last verified: 2026-07-18

Memory ID: `mem-separate-generated-file-newline-policy-from-in-place-patchin`
Kind: `successful_pattern`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-07-18
Source event: `decision-log:1p9ix-bug windows-path-newline-stragglers:4c6909d24b66cfaa`
Validation: promote
Validated by: agent
Action delta: Use byte-stable LF writes for fully generated surfaces but preserve existing newline style when patching operator-authored files.
Validation rationale: The renderer still intentionally separates generated-file writes from in-place patchers, and collapsing them would create cross-platform churn or rewrite operator content.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When changing renderers, write fully generated surfaces with explicit byte-stable line endings, but preserve the existing file's newline behavior when patching operator-authored content in place.

## Evidence

- `1p9ix-bug windows-path-newline-stragglers`
- `1p9j0`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py:725`
- `.wavefoundry/framework/scripts/render_agent_surfaces.py:786`

## Targets

- `.wavefoundry/framework/scripts/render_agent_surfaces.py`
