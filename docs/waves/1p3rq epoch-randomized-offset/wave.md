# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-06-06

wave-id: `1p3rq epoch-randomized-offset`
Title: Epoch Randomized Offset

## Objective

The install epoch calculation changes from a fixed `first_commit_date` to `(first_commit_date - 5 years) + random(-365, +180) days`, making the epoch unpredictable without changing ID format or sort order. This prevents an observer from decoding approximate project age from a lifecycle ID prefix.

## Changes

Change ID: `1p3rr-enh epoch-randomized-offset`
Change Status: `implemented`

Completed At: 2026-06-06

## Wave Summary

Wave `1p3rq` (Epoch Randomized Offset) delivered one change: Epoch Randomized Offset.

**Changes delivered:**

- **Epoch Randomized Offset** (`1p3rr-enh epoch-randomized-offset`) — 8 ACs completed. Key decisions: Range [-365, +180] asymmetric; Base of 5 years before inception
## Journal Watchpoints

- **watchpoint — seed edit gate:** Both seed-011 and seed-160 require `wave_gate_open(gate="seed_edit_allowed")` before editing; close the gate after both edits complete in the same session.

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-06-06: PASS** (moderator: wave-council; primer-depth: lightweight; seats: red-team, docs-contract-reviewer; rotating-seat: docs-contract-reviewer; strongest-challenge: interrupted-install re-derivation — agent re-prompted mid-install could generate a different offset; addressed by Req 3 write-immediately instruction and AC-7; strongest-alternative: none stronger than one-liner offset formula for a seed-only change)

## Review Evidence

- wave-council-readiness: approved 2026-06-06 — PASS WITH IN-SESSION FIXES (moderator: wave-council; seats: architecture-reviewer, security-reviewer, qa-reviewer, reality-checker, docs-contract-reviewer; depth: lightweight; must-fix-count: 0; recommended-count: 3 all applied in-session [RC-1 dropped Req 7 untracked external output; RC-2 strengthened Req 3 + added AC-7 for one-time decision; Arch-ADV-1 corrected range precision to "approximately 4 years 6 months"]; verdict: PASS)
- wave-council-delivery: approved 2026-06-06 — PASS WITH IN-SESSION FIXES (moderator: wave-council; seats: red-team, docs-contract-reviewer; depth: lightweight; must-fix-count: 0; recommended-count: 2 both applied in-session [RC-1 added Python one-liner for safe 5-year date subtraction handling Feb-29 edge case; Arch-ADV-1 rewrote seed-160 note to be self-contained without requiring prior seed-011 context]; strongest-challenge: missing date arithmetic one-liner — agents computing manually hit leap-year edge cases; verdict: PASS)
- operator-signoff: approved 2026-06-06

## Dependencies

- No external wave dependencies.
