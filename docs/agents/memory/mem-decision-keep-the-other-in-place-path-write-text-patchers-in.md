# Decision: Keep the other in-place `path.write_text(...)` patchers in…

Owner: Engineering
Status: superseded
Last verified: 2026-07-18

Memory ID: `mem-decision-keep-the-other-in-place-path-write-text-patchers-in`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9ix-bug windows-path-newline-stragglers:4c6909d24b66cfaa`
Validation: rewrite
Validated by: agent
Action delta: Use byte-stable LF writes for fully generated surfaces but preserve existing newline style when patching operator-authored files.
Validation rationale: The renderer still intentionally separates generated-file writes from in-place patchers, and collapsing them would create cross-platform churn or rewrite operator content.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `mem-separate-generated-file-newline-policy-from-in-place-patchin`
## Summary

Decision (wave 1p9j0): Keep the other in-place `path.write_text(...)` patchers in `render_agent_surfaces.py` out of scope.. Rationale: F14 names only the `write_text` render helper for freshly generated surfaces; the patchers modify existing operator-authored files whose on-disk line endings should be preserved..

## Evidence

- `1p9ix-bug windows-path-newline-stragglers`
- `1p9j0`

## Targets

- `render_agent_surfaces.py`
