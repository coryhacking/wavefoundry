# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-05-01

wave-id: `12awg mcp-tool-cleanup`
Title: Mcp Tool Cleanup

## Changes

Change ID: `12awg-maint remove-wave-change-create`
Change Status: `complete`

Change ID: `12ax9-maint edit-gate-tools`
Change Status: `complete`

Change ID: `12axd-bug wave-close-overwrites-metadata`
Change Status: `complete`

Change ID: `12ayn-maint wave-close-operator-gate`
Change Status: `complete`

Completed At: 2026-05-01

## Wave Summary

Remove the deprecated `wave_change_create` tool now that the one-wave migration window from `12ahv` has elapsed; add a proper MCP interface (`wave_open_gate` / `wave_close_gate`) for managing the `seed_edit_allowed` and `framework_edit_allowed` guards, with automatic gate close enforced at `wave_pause` and `wave_close` boundaries; fix two `wave_close` bugs where the close summary was missing required metadata fields and the session handoff was fully overwritten rather than surgically updated; and add a hard operator-approval gate for `wave_close(mode="create")` to `AGENTS.md`, the run-contract seed, and the finalize-feature seed — mirroring the existing `git commit` policy.

## Journal Watchpoints

- `12awg-maint remove-wave-change-create` must land before `12ax9-maint edit-gate-tools` tests are finalized — both touch `test_all_tools_registered`.
- `12ax9` `CLAUDE.md` edit requires `framework_edit_allowed` open; this is the last direct JSON gate edit — restore immediately after.
- `wave_close` dry-run must remain fully read-only: `_force_gates_closed` must not write in dry-run mode.
- `12axd` handoff targeted-update helper must fall back to writing a minimal scaffold if the "Active wave" pattern is not found — never silently fail.

## Review Signoff Evidence

- 550 tests passing (`run_tests.py`) — approved and signoff complete.
- `wave_validate` clean (lint pass, no errors).
- Dead code (`_merge_pause_into_session_handoff`) removed; no remaining callers confirmed via grep.
- `12ayn`: `AGENTS.md`, `020-run-contract.prompt.md`, and `190-finalize-feature.prompt.md` updated with `wave_close` operator-owned rule; `wave_validate` clean after edits.

## Dependencies

- No external wave dependencies.
