# server_impl.py tool responses: success-branch assignment and `data` nesting

Owner: Engineering
Status: archived
Last verified: 2026-07-25

Memory ID: `1tlaa-mem server-impl-py-tool-responses-success-branch-assignment-and-`
Superseded by: `1u8q1-mem server-impl-file-playbook`
Kind: `fragile_file`
Confidence: 0.85
Created: 2026-07-25
Updated: 2026-08-02
Source exploration cost: 1048595
Source event: `repeated-repairs:1ti11:.wavefoundry/framework/scripts/server_impl.py`
Validation: promote
Validated by: agent
Action delta: When adding or documenting a response field on a server_impl.py MCP tool, assign it only on the success branch (never after a swallowed except) and document it nested under `data`, because `_context_data` returns `response["data"]`.
Validation rationale: The generated draft says only that server_impl.py "required 2 separate repairs", which is near-useless for a 27k-line chokepoint file that is touched by most waves; it would fire on every future edit without changing any action. The two repairs share a specific, recurring seam worth remembering instead. (1) `reopen-reports-unapplied-focus`: `focus_stage` was assigned OUTSIDE the try, so a swallowed `set_focus` failure still reported success. (2) `reopen-failure-envelope-undocumented-and-unpinned` and its council follow-up: the documented envelope was flat while `_context_data` (server_impl.py:21701-21707) returns `response["data"]`, so the docs contradicted the tests. I verified both against the current tree: the assignment now sits on the success branch, and the docstring plus tool-surface spec now show `data` nesting. An existing memory (1t1wx-mem) already covers server_impl.py's context-efficiency INSTRUMENTATION, which is a different seam, so this supplements rather than duplicates it.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

Archived: 2026-08-02
Archive reason: Superseded by a verified consolidated file playbook after retention review.
Archive path: `docs/agents/memory/archive/1tlaa-mem server-impl-py-tool-responses-success-branch-assignment-and-.md`
## Summary

Two seams in server_impl.py MCP tool responses were each got wrong in wave 1ti11. First, a response field assigned outside its `try` reports success even when the operation it describes raised and was swallowed; `wf_reopen_wave` claimed `focus_stage: "review"` while the focus write had failed. Assign such fields only on the success branch and surface the failure explicitly. Second, tool responses nest payload under `data` because `_context_data` returns `response["data"]`, so any documented literal showing a field at top level is wrong; that mismatch shipped three times in one documentation block before a council caught it. When documenting a new response field, show it nested and state that a top-level read finds nothing.

## Evidence

- `reopen-reports-unapplied-focus`
- `reopen-failure-envelope-undocumented-and-unpinned`
- `1ti11`

## Targets

- `.wavefoundry/framework/scripts/server_impl.py`
