# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-06

wave-id: `1rvfy release-1p11-preship-hardening`
Title: Release 1P11 Preship Hardening

## Objective

**Land two small hardening fixes into 1.11.0 before it ships (operator direction 2026-07-06).** Both came out of the closed `1rtnn` wave — one an accepted delivery-review residual, one a flagged latent issue — and both improve the exact surfaces 1.11.0 is about (dashboard lifecycle + upgrade). `1rvfw` — `wave_dashboard_stop` reports `already_stopped` and deletes metadata for a recorded PID that is still alive but not cmdline-verifiable (a false success + state loss); make it honest (don't claim stopped, don't delete metadata, emit a `dashboard_pid_unverified` diagnostic) without touching the `1rswx` never-kill-an-unverified-PID security control. `1rvfx` — the upgrade's pre-extract graph-builder snapshot reads a retired `framework-graph-state.json` path, so the "GRAPH_BUILDER_VERSION X → Y" transition line never fires in production (even on the real 40 → 43 bump this release ships); read the installed version from the real project graph state so the line surfaces alongside 1.11.0's new mandatory-reload guidance. When this wave closes: stop no longer lies about an unverifiable instance, the upgrade log shows the graph-builder transition, and 1.11.0 is re-packaged for ship.

## Changes

Change ID: `1rvfw-bug dashboard-stop-unverified-pid-safe-report`
Change Status: `implemented`

Change ID: `1rvfx-bug upgrade-graph-version-transition-log`
Change Status: `implemented`

Completed At: 2026-07-06

## Wave Summary

Wave `1rvfy` (Release 1P11 Preship Hardening) delivered two changes: Dashboard stop: honest report for an alive-but-unverified recorded PID and Upgrade log: surface the GRAPH_BUILDER_VERSION transition (fix dead-path pre-extract read).

**Changes delivered:**

- **Dashboard stop: honest report for an alive-but-unverified recorded PID** (`1rvfw-bug dashboard-stop-unverified-pid-safe-report`) — 5 ACs completed. Key decisions: Make stop honest (don't claim stopped, don't delete metadata, emit a diagnostic) in the unverified-alive case; leave the kill decision untouched.
- **Upgrade log: surface the GRAPH_BUILDER_VERSION transition (fix dead-path pre-extract read)** (`1rvfx-bug upgrade-graph-version-transition-log`) — 5 ACs completed. Key decisions: Inline a small stdlib `sqlite3` + `json` reader in `upgrade_wavefoundry.py` rather than import `graph_indexer.read_state_builder_version`.
## Journal Watchpoints

- Watchpoint (`1rvfw` — keep the security control): the fix must NOT reintroduce killing an `os.kill`-alive-but-unverified recorded PID (the `1rswx` AC-3 defect). It only changes the *reporting* (honest `already_stopped: False` + `dashboard_pid_unverified` diagnostic + retain metadata) for the ambiguous case; the kill decision (`targets` → `_terminate_dashboard_pid`) is untouched. The `1rswx` zombie path (reaped-on-entry → not `os.kill`-alive → genuinely stopped) must stay clean.
- Watchpoint (`1rvfx` — import-light): do NOT import `graph_indexer` into `upgrade_wavefoundry.py` (heavy / dep-fragile at upgrade time, and the module is replaced during extraction). Inline a stdlib `sqlite3` (read-only URI) + `json`-fallback reader mirroring `read_state_builder_version`; fail-safe to no-entry so the probe never aborts the upgrade.
- Watchpoint (disjoint surfaces): `1rvfw` (`server_impl.py`) and `1rvfx` (`upgrade_wavefoundry.py`) share no files — no merge seam. Tests live in `test_dashboard_server.py`/`test_server_tools.py` (1rvfw) vs `test_upgrade_wavefoundry.py` (1rvfx).
- Watchpoint (release timing): this wave ships under the SAME 1.11.0 tag as `1rtnn` (multi-wave version release); its close triggers a package rebuild, and the operator commits `1rtnn` + `1rvfy` together. VERSION is already `1.11.0+…`; no further version bump.

## Participants

- code-reviewer — both single-file production changes (`server_impl.py` stop-path; `upgrade_wavefoundry.py` pre-extract read)
- qa-reviewer — required for bug fixes (`review_policies.require_qa_reviewer_for_bug_fixes`); AC priority tables present on both changes
- security-reviewer / red-team — `1rvfw` must preserve the never-kill-an-unverified-PID control from `1rswx` AC-3 (adversarial check that the kill decision is unchanged)

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, security-reviewer, qa-reviewer, reality-checker; rotating-seat: security-reviewer; strongest-challenge: for `1rvfw`, whether making the ambiguous stop report `already_stopped: False` breaks `wave_dashboard_restart` recovery — resolved because the unverified-alive case stays `status: ok`, so restart still proceeds to start unchanged, and the recycled-PID-vs-scan-missed-live ambiguity is inherent and intentionally left to the operator rather than resolved by killing an unverified PID; strongest-alternative: abort restart on the ambiguous case to avoid a scan-miss duplicate — rejected because it changes the recycled-PID recovery contract, and the duplicate case is the pre-existing port-guarded 1p8pf behaviour out of scope here)
- Council seat notes: security-reviewer / red-team (`1rvfw`) — confirmed the kill decision is untouched: only the cmdline-verified `targets` set reaches `_terminate_dashboard_pid`; the unverified-alive PID is never signalled, so the `1rswx` AC-3 never-kill-a-recycled-PID control is preserved; the change is reporting-only (`already_stopped`/`stopped` values + one additive `dashboard_pid_unverified` diagnostic + retain-metadata). reality-checker — re-verified against source: the empty-`targets` branch at `server_impl.py:7993-7995` reports `already_stopped: True` + removes metadata today; `_pid_is_running` and the `1rswx` reap-on-entry both exist; for `1rvfx`, `_snapshot_pre_extract_versions` reads the dead `framework-graph-state.json` (`:647`), `read_state_builder_version` (`graph_indexer.py:1414`) reads the real `project-graph-state.sqlite` + legacy JSON, and `_write_graph_state` (test) writes the dead path. qa-reviewer — both bug fixes carry AC priority tables and deterministic-test plans (mock-based for `1rvfw`; real-path fixtures + fail-safe for `1rvfx`); qa-reviewer required and rostered. seat_agreement: unanimous; no challenge round; both changes are small, disjoint, single-file, and preserve the load-bearing controls.
- AC priority: confirmed at prepare as proposed in each doc (1rvfw AC-1..5 required; 1rvfx AC-1/3/4/5 required, AC-2 important). qa-reviewer assigned per `review_policies.require_qa_reviewer_for_bug_fixes`. Product-owner acknowledgment: both defects surfaced from the `1rtnn` delivery review and the operator directed landing them before the 1.11.0 ship.

## Review Evidence

- wave-council-readiness: approved 2026-07-06 — prepare council synthesis verdict READY. Both changes' load-bearing claims verified against source (not just the plan prose): the mishandled stop branch, the retired graph-state path, and the canonical readers all resolve as described. `1rvfw` preserves the `1rswx` security control (reporting-only change); `1rvfx` stays import-light with a fail-safe read. Seats unanimous; no amendment required. Full synthesis in Review Checkpoints.
- wave-council-delivery: approved (2026-07-06 — moderator: wave-council; adversarial delivery review of both changes against the actual code paths, canonical references, and tests; no blocking findings, no fixes required. `1rvfw`: the kill set `targets` is genuinely unchanged — the new logic lives entirely inside the `if not targets:` branch and only affects reporting; there is NO path where an unverified-alive PID reaches `_terminate_dashboard_pid`, so the `1rswx` AC-3 never-kill-unverified control is intact; restart proceeds on the `ok` result identically to pre-1rvfw (no new duplicate-spawn regression — start's reconcile cannot false-adopt a recycled PID and overwrites metadata on respawn); the reaped-zombie model (`_pid_is_running=False` post-reap) is faithful; `test_stop_unverified_alive_pid_reports_honestly` is strongly revert-sensitive. `1rvfx`: every error path returns "" (corrupt/locked/permission/missing-table/missing-row all caught → the upgrade never aborts on the probe); the read-only URI open is non-creating and non-locking; the inlined reader matches the canonical `read_state_builder_version` (same filenames, SQL, sqlite-then-JSON order, ""-on-absence) and is strictly more fail-safe; no `graph_indexer` import added; the sqlite fixture matches production's `meta(key,value)` shape and the tests drive the real entry point and are revert-sensitive. Two recorded non-defects: (1) `test_stop_genuinely_stopped_dead_pid_clears_metadata` is a boundary guard — the dead-PID outcome is unchanged by the diff, so it is not independently revert-sensitive by design, but it locks the split against a future regression; (2) a cross-process not-yet-reaped zombie — spawned by a now-dead prior server, not in this server's `_DASHBOARD_CHILD_PIDS` — would land in the new unverified branch rather than the clean already-stopped path, an inherent `1rswx` OS-semantics window (init reaps re-parented zombies near-instantly) unchanged by `1rvfw`. Full framework suite green: 4707 tests.)
- operator-signoff: approved 2026-07-06 — operator directed landing both fixes before the 1.11.0 ship and confirmed close.

## Dependencies

- No external wave dependencies.
