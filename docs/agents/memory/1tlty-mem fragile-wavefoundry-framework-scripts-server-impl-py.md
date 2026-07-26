# Fragile: .wavefoundry/framework/scripts/server_impl.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-25

Memory ID: `1tlty-mem fragile-wavefoundry-framework-scripts-server-impl-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-25
Updated: 2026-07-25
Source exploration cost: 1048595
Source event: `repeated-repairs:1ti11:.wavefoundry/framework/scripts/server_impl.py`
Validation: rewrite
Validated by: agent
Action delta: When adding or documenting a response field on a server_impl.py MCP tool, assign it only on the success branch (never after a swallowed except) and document it nested under `data`, because `_context_data` returns `response["data"]`.
Validation rationale: The generated draft says only that server_impl.py "required 2 separate repairs", which is near-useless for a 27k-line chokepoint file that is touched by most waves; it would fire on every future edit without changing any action. The two repairs share a specific, recurring seam worth remembering instead. (1) `reopen-reports-unapplied-focus`: `focus_stage` was assigned OUTSIDE the try, so a swallowed `set_focus` failure still reported success. (2) `reopen-failure-envelope-undocumented-and-unpinned` and its council follow-up: the documented envelope was flat while `_context_data` (server_impl.py:21701-21707) returns `response["data"]`, so the docs contradicted the tests. I verified both against the current tree: the assignment now sits on the success branch, and the docstring plus tool-surface spec now show `data` nesting. An existing memory (1t1wx-mem) already covers server_impl.py's context-efficiency INSTRUMENTATION, which is a different seam, so this supplements rather than duplicates it.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tlaa-mem server-impl-py-tool-responses-success-branch-assignment-and-`
## Summary

.wavefoundry/framework/scripts/server_impl.py required 2 separate repairs during wave 1ti11; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `reopen-reports-unapplied-focus`
- `reopen-failure-envelope-undocumented-and-unpinned`
- `1ti11`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
