# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-02

wave-id: `1p9j0 windows-portability-round-3`
Title: Windows Portability Round 3

## Objective

Close the native-Windows portability gaps that the round-2 audit surfaced but wave `1p9hn` (windows-portability-round-2) did not cover. When this wave closes, the `wf setup` Phase-1 child chain can no longer hang indefinitely (the likely mechanism behind the 1.9.8 field install stall), the server-side docs-lint timeout is configurable so lifecycle tools stop failing on large repos, rendered hooks decode host stdin as UTF-8, metadata writes survive a Windows sharing violation, and the remaining path/newline and dev/test-infra stragglers are fixed.

## Changes

Change ID: `1p9it-bug setup-phase1-child-deadlines`
Change Status: `planned`

Change ID: `1p9iu-bug mcp-docs-lint-timeout-configurable`
Change Status: `planned`

Change ID: `1p9iv-bug rendered-hook-stdio-utf8`
Change Status: `planned`

Change ID: `1p9iw-bug atomic-write-windows-share-retry`
Change Status: `planned`

Change ID: `1p9ix-bug windows-path-newline-stragglers`
Change Status: `planned`

Change ID: `1p9iy-bug dev-test-infra-windows-hardening`
Change Status: `planned`

## Wave Summary

Six bug fixes sourced from the round-2 Windows-compatibility audit (`wf_eab9a03d-004`) and the fix-delta comparison (`wf_33ca6bdb-757`) — the findings confirmed NOT fixed by wave `1p9hn`. Core: setup Phase-1 deadlines/heartbeats (F8), configurable MCP docs-lint timeout (F2), rendered-hook stdin UTF-8 (F10/F3), atomic-write Windows sharing-violation retry (F17). Low batch: path/newline stragglers (F14/F18) and dev/test-infra hardening (F12/F13/F16).

## Journal Watchpoints

- Sequencing: `1p9it` (setup Phase-1 deadlines — the likely field-install-hang mechanism) and `1p9iu` (docs-lint timeout) carry the highest user-facing value; the straggler batch (`1p9ix`) and dev/test-infra batch (`1p9iy`) are independent and can proceed in parallel.
- Shared-file coordination: changes land in mostly-independent files (`setup_index.py`, `server_impl.py`, `render_platform_surfaces.py` + `cli_stdio.py`, `indexer.py`, `render_agent_surfaces.py` + `secrets_validators.py`, `run_tests.py` + `build_pack.py`); only `1p9iv` spans two shared files.
- Watchpoint (`1p9iv`): touches `HOOK_BOOTSTRAP`/`configure_utf8_stdio` — after the change, re-render platform surfaces and confirm rendered hooks decode a non-ASCII stdin payload correctly.
- Guard (`1p9iy`): edits `run_tests.py` (the test runner itself) — verify the suite still launches on POSIX after the `fcntl`/`msvcrt` guard.
- Dependency: this wave builds on the currently-uncommitted wave `1p9hn` in the working tree; line numbers in the change docs are anchored to the post-`1p9hn` tree. Implement after `1p9hn` is committed to avoid tangling the diff.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-02: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; rotating-seat: reality-checker; strongest-challenge: `1p9it`'s setup-deadline defaults could false-trip slow-but-legit environments (corp proxy, low-RAM WSL2) — mitigated by conservative, per-stage configurable defaults plus the AC-5 within-deadline non-regression gate, and the honestly-recorded limit that a daemon-thread watchdog cannot truly interrupt a parked native fastembed call (the abort fails loud and returns control; the process may need to exit rather than resume); strongest-alternative: split the `1p9iy` dev/test-infra batch (F12/F13/F16) out of a shipped-runtime wave — declined because the items are low-risk and F16 blocks native-Windows contributors from running the suite at all. No required council lanes beyond `implementer`: no MCP endpoint additions, no architecture-boundary change, and the `1p9ix` secrets gitignore-filter fix is Windows/POSIX parity, not a detection narrowing. All ACs are deterministically testable.)

## Review Evidence

- wave-council-readiness: approved 2026-07-02 — READY. Six bug fixes drawn from the round-2 Windows-audit delta (findings confirmed not covered by wave `1p9hn`), each confined to individual functions with verified current-tree sites, deterministic ACs, and explicit out-of-scope boundaries. Residual risk is concentrated in `1p9it` (setup deadlines) and is bounded by conservative configurable defaults and an AC-5 non-regression gate. Dependency: implement after the currently-uncommitted `1p9hn` lands so line anchors hold. No security-sensitive data path and no architecture-boundary change.
- operator-signoff: pending operator confirmation at close.

## Dependencies

- No external wave dependencies.
