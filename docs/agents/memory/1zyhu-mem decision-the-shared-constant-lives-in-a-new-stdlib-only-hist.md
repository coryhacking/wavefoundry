# Decision: The shared constant lives in a new stdlib-only `history_pat…

Owner: Engineering
Status: active
Last verified: 2026-10-07

Memory ID: `1zyhu-mem decision-the-shared-constant-lives-in-a-new-stdlib-only-hist`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-07
Updated: 2026-10-07
Source exploration cost: 97308
Source event: `decision-log:1zxnt-maint correctness-and-test-hygiene-round:5004633e5a7207f0`
Validation: promote
Validated by: agent
Action delta: Put a new constant needed by upgrade-time code in a new stdlib-only module, not as a new attribute on a module an older process may already hold in sys.modules.
Validation rationale: history_paths.py exists, is stdlib-only and is imported function-locally in upgrade_extensions; the old-record_paths-in-sys.modules hazard is real and recurs.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Decision (wave 1zyb2): The shared constant lives in a new stdlib-only `history_paths.py`, not `record_paths.py`.. Rationale: During an upgrade the running process may hold an old `record_paths` in `sys.modules` (the memory bootstrap comment at `upgrade_extensions.py` records exactly this, a 1.27 `RecordRoots` without `archive`), so a new attribute on `record_paths` could raise `AttributeError` at the two `upgrade_extensions` sites; a new module imports fresh. `agent_surface_integrity` also does not import `record_paths` today..

## Evidence

- `1zxnt-maint correctness-and-test-hygiene-round`
- `1zyb2`

## Targets

- `history_paths.py`
- `record_paths.py`
- `upgrade_extensions.py`
