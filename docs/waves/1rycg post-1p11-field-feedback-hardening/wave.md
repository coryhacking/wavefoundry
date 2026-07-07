# Wave Record

Owner: Engineering
Status: closed
Last verified: 2026-07-06

wave-id: `1rycg post-1p11-field-feedback-hardening`
Title: Post 1P11 Field Feedback Hardening

## Objective

**Two hardening fixes from post-1.11.0 field testing, bundled for a quick 1.11.1 release (operator direction 2026-07-06).** `1ryce` — an MCP `wave_upgrade` from a version **before 1.10.1** never auto-provisions the lifecycle scheme-v2 policy (the orchestrator runs pre-upgrade code that predates Phase 2c + the cleanup backstop), so the repo silently keeps minting collision-prone v1 IDs; add the idempotent provisioning to the new-code `--update-index` phase so a from-old-version upgrade self-heals. `1rycf` — `docs.lance` balloons unbounded (698 MB observed, 640 MB reclaimable) because LanceDB's incremental FTS rebuild leaks un-GC'd index versions that only a deep optimize reclaims (run only at install/upgrade); add a bloat-gated `wave_index_optimize` at wave close as an interim reclaim until the SQLite FTS5 migration (`1rrr0`) removes the leak at the source. When this wave closes: from-old-version upgrades provision v2 automatically, and heavy-doc sessions no longer balloon the docs index between deep optimizes. **(B — external `implements`/`extends` graph modeling — was intentionally deferred to its own dedicated graph wave; the field finding is logged in `docs/references/wavefoundry-graph-tools-feedback.md`.)**

## Changes

Change ID: `1ryce-bug upgrade-v2-provision-from-new-code`
Change Status: `implemented`

Change ID: `1rycf-enh index-bloat-gated-optimize-at-close`
Change Status: `implemented`

Completed At: 2026-07-06

## Wave Summary

Wave `1rycg` (Post 1P11 Field Feedback Hardening) delivered two changes: Upgrade: provision lifecycle scheme-v2 from new code so a from-<1.10.1 MCP upgrade self-heals and Index bloat: bloat-gated wave_index_optimize at wave close (interim FTS-version reclaim).

**Changes delivered:**

- **Upgrade: provision lifecycle scheme-v2 from new code so a from-<1.10.1 MCP upgrade self-heals** (`1ryce-bug upgrade-v2-provision-from-new-code`) — 4 ACs completed. Key decisions: Add the idempotent provisioning to the new-code `--update-index` phase.
- **Index bloat: bloat-gated wave_index_optimize at wave close (interim FTS-version reclaim)** (`1rycf-enh index-bloat-gated-optimize-at-close`) — 6 ACs completed. Key decisions: Interim bloat-gated optimize at wave close (before the close's background refresh, lock-aware, tier-1 only).; Superseded-by-design note: `1rrr0` (SQLite FTS5) removes the leak at the source; this change is the bridge until it lands and can be retired then.
## Journal Watchpoints

- Watchpoint (`1ryce` — new-code execution point): the fix MUST run in the extracted-pack (new) code — the only new code during a from-old-version MCP upgrade is the `upgrade_wavefoundry.py` subprocess post-extract. The `--update-index` phase is the reliably-invoked new-code phase; do NOT try to fix this in the MCP server / `wave_mcp_reload` (that's old code during a from-old upgrade). Provisioning stays idempotent + fail-safe (never fails the index phase).
- Watchpoint (`1rycf` — don't race the close's own refresh): `wave_close(mode="create")` triggers a background index refresh; run the bloat-check + optimize BEFORE that trigger (lock free) and skip if `wave_index_build_status.lock.held`. Tier-1 in-place ONLY — never spawn a synchronous tier-3 rebuild at close; log `needs_rebuild` and defer. Optimize failure must never affect the close.
- Watchpoint (`1rycf` — interim, superseded): this is a bridge until `1rrr0` (SQLite FTS5 in-place segments) removes the FTS-version leak; do not build a permanent parallel maintenance surface — reuse `wave_index_optimize` and keep it retire-able.
- Watchpoint (disjoint surfaces): `1ryce` (`upgrade_wavefoundry.py`) and `1rycf` (`server_impl.py`) share no files; tests in `test_upgrade_wavefoundry.py` vs `test_server_tools.py`. No merge seam.
- Watchpoint (release): ships as 1.11.1 with the closed `1rycd`; VERSION bump + CHANGELOG + package happen at the release step (not inside a change here) — `1ryce`/`1rycf` are the fixes, the release mechanics are a close/release-time step.

## Participants

- code-reviewer — both single-surface production changes (`upgrade_wavefoundry.py` `--update-index` provisioning; `server_impl.py` close-time optimize)
- qa-reviewer — required for bug fixes (`review_policies.require_qa_reviewer_for_bug_fixes`); AC priority tables present on both changes
- performance-reviewer — `1rycf` must not slow close / race the refresh / spawn a synchronous rebuild (lock-aware, tier-1, bloat-gated)

## Review Checkpoints

- **Prepare-phase Wave Council [prepare-council] — 2026-07-06: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, performance-reviewer, qa-reviewer, reality-checker; rotating-seat: performance-reviewer; strongest-challenge: for `1rycf`, the close-time optimize could race the close's own background index refresh or block close on an expensive rebuild — resolved by running the bloat-check + optimize BEFORE the refresh trigger (lock free), skipping if `lock.held`, tier-1-only inline, and deferring any `needs_rebuild` instead of spawning it; for `1ryce`, whether provisioning in `--update-index` could re-epoch an already-v2 repo — resolved by the inherited idempotence guard (`scheme_version == "v2"` no-op); strongest-alternative: fix `1ryce` in the MCP `wave_upgrade`/`wave_mcp_reload` handler — rejected because those run the OLD server code during a from-old-version upgrade, so only the extracted-pack `--update-index` subprocess is new code)
- Council seat notes: reality-checker — verified against source + git: Phase 2c (`materialize_lifecycle_policy`) + the cleanup backstop landed in `f39d9221` (wave 1p9q0) at VERSION 1.10.1, the target was 1.9.7 (predates both), and the MCP upgrade runs the old orchestrator until reload; `upgrade_wavefoundry.py:2458` `--update-index` runs the extracted new code post-extract; `indexer.py:2306` fragment-gated optimize + `:2350-2357` FTS-rebuild-no-GC comment confirm the `docs.lance` bloat mechanism; `wave_close_response` triggers the background refresh at `server_impl.py:10191`. performance-reviewer — `1rycf` gate must be cheap (size + row-count already exposed) and tier-1 inline only; no busy-loop; no synchronous rebuild at close (AC-3/AC-4). qa-reviewer — deterministic tests for both: `1ryce` v1→v2 / v2-no-op / RuntimeError-fail-safe; `1rycf` fires/tight/lock-held/error-safe/needs-rebuild-deferred/kill-switch; qa-reviewer required and rostered. red-team — `1ryce`'s only real risk is re-epoching a valid v2 repo (closed by idempotence) or failing the index phase (closed by fail-safe); `1rycf`'s is slowing/racing close (closed by pre-refresh ordering + lock-skip + tier-1). seat_agreement: unanimous; two small disjoint single-surface changes; no challenge round.
- AC priority: confirmed at prepare as proposed (`1ryce` AC-1..4 required; `1rycf` AC-1..4/6 required, AC-5 important). qa-reviewer assigned per `review_policies.require_qa_reviewer_for_bug_fixes`. Product-owner acknowledgment: both are operator-reported field findings and operator-directed for a 1.11.1 bundle.

## Review Evidence

- wave-council-readiness: approved 2026-07-06 — prepare council synthesis verdict READY. Load-bearing claims verified against source + git history (old-code provisioning window at 1.10.1 vs the 1.9.7 target; the `docs.lance` FTS-version-leak mechanism; the close-time refresh/lock ordering). `1ryce` provisions from the only new-code phase (`--update-index`), idempotent + fail-safe; `1rycf` is bloat-gated, lock-aware, tier-1-only, superseded later by `1rrr0`. Seats unanimous; no amendment. Full synthesis in Review Checkpoints.
- wave-council-delivery: approved (2026-07-06 — moderator: wave-council; adversarial delivery review against the actual code, tests, and the LIVE index. No blocking findings on either change. **code-reviewer** — `1ryce`: the `--update-index` branch calls `_ensure_lifecycle_policy_backstop(root)` right after `phase_index_update(root)` (`upgrade_wavefoundry.py:2479`), reusing the existing fail-safe wrapper (catches `RuntimeError` → logs the `wf upgrade --materialize-lifecycle-policy` pointer → returns), so AC-1/2/3 are satisfied by the wrapper's inherited idempotence + fail-safe rather than a bare `materialize` call — the cleaner choice; the call sits inside the phase's `try/finally` so a genuine index-update failure short-circuits it (moot — the upgrade itself failed) while Phase 2c + the cleanup backstop still cover the from-≥1.10.1 path. `1rycf`: `_maybe_optimize_index_on_close` calls `idx.optimize_index_tables` directly (never the response wrapper), so tier-3 `run_index_rebuild` is unreachable from close — verified by test and by the fact the spawn logic lives only in `_wave_index_optimize_response`; the lock skip is a genuine atomic acquire-or-raise (`IndexBuildAlreadyRunning`), no TOCTOU; the helper is invoked only on a real close transition (inside the `!= "closed"` guard), after the wave.md write + `cache.invalidate()` and before the background-refresh trigger, and the whole body is wrapped so it can never raise into the close. **performance-reviewer** — the gate is cheap (on-disk size already walked by `_index_dir_size`; two `count_rows` metadata reads) and correctly ordered before the refresh so it never contends the build lock; calibration validated on the LIVE index: tight `docs` 1.7× and `code` 1.4× are both below the 3.0 trigger (no gratuitous optimize on a tight index — AC-2 holds in the real world, not just under stubs), while the observed 698 MB `docs` bloat is 17.6× and fires; tier-1-only means no synchronous re-embed at close. **qa-reviewer** — deterministic coverage on both: `1ryce` wiring-lock (`test_update_index_phase_wires_the_lifecycle_backstop`) + behavior (`test_cleanup_backstop_heals_unprovisioned_repo`/`_noop_when_already_v2`/`_never_raises_on_corrupt_config`); `1rycf` `CloseTimeOptimizeTests` (12) covering fires-on-bloat, tight-no-op (asserts the indexer is never even loaded), lock-held-skip, optimize-error-swallowed, never-raises, needs-rebuild-deferred-never-spawned (asserts `run_index_rebuild` not called), kill-switch, config default/false/corrupt, and a source-assertion that the optimize runs before the refresh; full framework suite 4725 OK bytecode-free; `wave_validate` clean. Synthesis verdict: SHIP — two small disjoint single-surface interim/hardening fixes, fully tested, live-data-validated; `1rycf` is explicitly retire-able once `1rrr0` lands.)
- operator-signoff: approved when operator confirms closure

## Dependencies

- No external wave dependencies.
