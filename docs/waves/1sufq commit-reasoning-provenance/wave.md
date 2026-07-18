# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-07-17
review-evidence-source: events.jsonl

wave-id: `1sufq commit-reasoning-provenance`
Title: Commit Reasoning Provenance

## Objective

Add a reverse-provenance lookup: from a commit SHA or a blamed line, resolve back to the wave that produced it and surface its Decision Log and change-doc rationale. A local, read-only tool over data we already track forward (wave→commit), so "why is this line here" is answered from the recorded reasoning instead of re-derived. Surfaced by a field user; no new infra, no network.

## Changes

Change ID: `1sufp-feat commit-to-reasoning-provenance`
Change Status: `planned`

## Wave Summary

One change (`1sufp`): a `code_commit_provenance` tool that resolves a commit SHA (or file+line via contained `git blame`) to its producing wave(s) by two local paths (commit-message `Land wave` parse and reverse-search of wave records/review-evidence for a cited commit SHA), and surfaces the wave's Decision Log + change-doc rationale. Local-only, read-only, honest on absence.

## Journal Watchpoints

- `server_impl.py` edited under `framework_edit_allowed`; open before editing, close immediately after.
- Watchpoint: strictly read-only and local-only — never mutates git or wave state, never makes a network call; reuse the existing contained/bounded git wrappers.
- Watchpoint: honest absence — a commit with no wave association returns a clear no-provenance result, never a fabricated mapping; conflicting message-parse vs evidence-search results are reported, not silently reconciled.
- Follow-up: any derived cache must be rebuildable and non-authoritative (git + wave records remain source of truth).

## Finding Synthesis

<!-- waveframework:finding-synthesis begin -->
| Current finding | Disposition | Open block | Repair | Approval recheck |
| --- | --- | --- | --- | --- |
| — | — | — | — | — |

<details class="wavefoundry-review-evidence">
<summary>Machine review evidence — 1 records; 1 runs; 0 findings; current: do_now 0, maybe_later 0, dont_do_later 0, not_issue 0</summary>
</details>
<!-- waveframework:finding-synthesis end -->

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-17: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer; rotating-seat: security-reviewer; strongest-challenge: there is no dedicated Decision-Log parser to reuse — resolved: the existing change-doc parsers (`parse_change_doc`, `_resolve_change_doc_matches`) cover the doc, and the tool extracts the Decision Log section (a small addition, not a new subsystem); strongest-alternative: a persistent per-line provenance store — rejected as heavy and redundant with on-demand git + wave records.)
- prepare-council seat — red-team: verified both resolution paths are grounded — the `Land wave(s) <id>` commit convention is present in history (`git log`: "Land waves 1shv4, 1sq4a, 1sq9i…", "Land wave 1sed7…"), and wave records cite landing commit SHAs (e.g. `commit \`11b3af4\`` in `1p3b9`/wave.md), so the reverse-search path is feasible. Change-doc/wave parsers exist (`parse_change_doc` dashboard_lib.py:939, `_parse_wave_record` server_impl.py:2509). Squashed/rebased/non-conventional commits are handled by the second path + honest absence (AC-5).
- prepare-council seat — security-reviewer: the trust surface is git subprocess execution over user input (SHA, file path, line range). Verified the safe primitive exists: `_run_git` (index_state_store.py:2669) invokes git via an argv list (no shell) and `_sanitized_git_env` (:2648) strips sensitive env, so a hostile SHA/path cannot inject a command. Constraint recorded for implementation: reuse `_run_git`/`_sanitized_git_env`, validate the SHA format, and confine the file-path input to the repo root (path-traversal guard) before `git blame`. Read-only (blame/log/rev-parse only) and no-network hold; no new external surface.

## Review Evidence

- wave-council-readiness: approved 2026-07-17 — small, self-contained, local-only read-only tool over data we already track forward (wave→commit); core risks (mutation, network, fabricated provenance) are gated by ACs (AC-4 read-only/local, AC-5 honest absence). Reuses existing git wrappers + wave-record parsers. No blocking concerns.
- operator-signoff: pending operator closure confirmation

## Dependencies

- No external wave dependencies.
