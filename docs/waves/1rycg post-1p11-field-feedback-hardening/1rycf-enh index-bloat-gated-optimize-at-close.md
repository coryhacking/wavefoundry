# Index bloat: bloat-gated wave_index_optimize at wave close (interim FTS-version reclaim)

Change ID: `1rycf-enh index-bloat-gated-optimize-at-close`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1rycg post-1p11-field-feedback-hardening`

## Rationale

Observed this session: `docs.lance` grew to **698 MB** (640 MB reclaimed by `wave_index_optimize` → 58 MB) while `code.lance` stayed tight at 34 MB (0 reclaimed). Root cause traced in `indexer.py`: the incremental refresh rebuilds the FTS index with `replace=True` (`_create_fts_index`, `indexer.py:2357`) on every pass that changed a table, and it **deliberately does not GC the prior index version** (the comment at `:2350-2353`: *"a duplicate whose stale copy can't be GC'd without pylance"*). The only in-path reclaim is the fragment-gated `optimize` (`:2306`, `LANCEDB_COMPACT_THRESHOLD = 20`), which triggers on **data-fragment count**, not on the accumulated **index-version** count. In a framework-dev session, `docs` is churned constantly (every `wave.md`/change-doc/AC/seed/journal edit) and its FTS is large (~40 MB), so hundreds of docs FTS rebuilds pile up hundreds of ~40 MB stale `_indices/` versions that the fragment-gate never reclaims. `code` churns rarely and has a smaller FTS, so it stays tight. `wave_index_optimize` runs `cleanup_older_than=0` and reclaims all of it — but it only runs at install/upgrade end + on demand, never between them.

The durable structural fix is the SQLite FTS5 migration (`1rq4h` → `1rrr0`, planned) which does in-place incremental segment updates (no version pileup). This change is the **interim bridge**: run a bloat-gated `wave_index_optimize` at wave close (a natural batch boundary at the end of a doc-heavy work unit) so `docs.lance` cannot balloon to 700 MB between the rare deep optimizes. `1rrr0` later supersedes it.

## Requirements

1. **Bloat-gated optimize at wave close (`mode="create"`).** After a successful close, when the index is bloated beyond a threshold AND the index build lock is free, run `wave_index_optimize` (tier-1 in-place compaction) to reclaim the accumulated index-version bloat. Fail-safe: an optimize error must NEVER affect the close result.
2. **A real bloat gate — do not optimize every close.** Compute a cheap bloat signal from the data `wave_index_health` already exposes: the on-disk size of a Lance table vs a conservative logical floor (row count × a per-row byte floor covering the fixed-size embedding). Only optimize when the ratio exceeds a configurable threshold (a named constant, default chosen so a tight ~1–1.5× table never triggers and a 3×+ bloat does). A no-op close on a tight index does zero optimize work.
3. **Never block or slow close on a running build.** The close already triggers a background index refresh for `wave.md`/handoff. Run the bloat check + optimize **before** triggering that refresh (so the lock is free), and skip the optimize if the lock is held (`wave_index_build_status.lock.held`) — the next close/optimize catches it. Never spawn a synchronous tier-3 full rebuild at close (tier-1 only inline; if optimize reports `needs_rebuild`, log it and defer — do not block).
4. **Bounded + observable.** Log what was reclaimed (before/after/reclaimed bytes) so the close output shows the reclaim. No busy-loop, no polling.
5. **Configurable + kill-switchable.** The bloat-ratio threshold and an enable flag live in `docs/workflow-config.json` (or a module constant with a config override), so an operator can tune or disable the close-time optimize.
6. Local-only, stdlib + existing LanceDB only; no new dependency.

## Scope

**Problem statement:** LanceDB's incremental FTS rebuild leaks stale index versions that only a deep `optimize` reclaims, and that deep optimize runs only at install/upgrade — so a doc-heavy session balloons `docs.lance` unbounded (698 MB observed) between them.

**In scope:**

- A bloat-ratio helper (on-disk size vs logical floor per Lance table) reusing the size + row-count data already available.
- A bloat-gated, fail-safe, lock-aware `wave_index_optimize` (tier-1) invocation wired into `wave_close_response(mode="create")` before the close's background refresh.
- Config: bloat-ratio threshold + enable flag.
- Tests: gate fires when bloated + lock free; no-op when tight; skipped when lock held; optimize error does not fail close; `needs_rebuild` deferred (not spawned) at close.

**Out of scope:**

- The SQLite FTS5 migration (`1rrr0`) — the structural fix that removes the leak; this is the interim bridge it supersedes.
- Turn-end optimize (a separate, more-frequent trigger point — deferred; close is the chosen boundary here).
- Changing the incremental refresh's FTS-rebuild behavior in `indexer.py` (that is the `1rrr0` territory / a deeper fix).
- Any change to search quality — optimize is lossless (compaction + version GC only).

## Acceptance Criteria

- [x] AC-1: When a table's on-disk size exceeds the configured bloat ratio over its logical floor and the build lock is free, `wave_close(mode="create")` runs `wave_index_optimize` and reclaims space; a deterministic test (stubbed size/rows + a stubbed optimize) asserts optimize is invoked and the reclaim is logged. — `_maybe_optimize_index_on_close` (server_impl.py) optimizes only the bloated tables via `idx.optimize_index_tables`; test `test_fires_on_bloated_table_and_reports_reclaim` asserts optimize called on `('docs',)` only and `reclaimed_bytes == 640_000_000`.
- [x] AC-2: When the index is tight (ratio below threshold), close does NOT invoke optimize; a test asserts no optimize call. — `test_noop_when_no_table_bloated` asserts `_load_script` (indexer load) is never called when all ratios are below `CLOSE_OPTIMIZE_BLOAT_RATIO`.
- [x] AC-3: When the build lock is held, close skips the optimize (no error, no wait); a test asserts skip-on-lock-held. — `optimize_index_tables` raises `IndexBuildAlreadyRunning` when the lock is held; helper catches it and returns `{ran: False, skipped: 'index_build_lock_held'}`. Test `test_skips_when_build_lock_held`.
- [x] AC-4: An optimize failure (or a `needs_rebuild` tier-3 result) never fails the close and never spawns a synchronous rebuild at close — it is logged and deferred; a test asserts the close still returns ok and no rebuild was spawned. — Outer try swallows all errors (`test_optimize_error_is_swallowed_and_reported`, `test_never_raises_on_internal_failure`); `needs_rebuild` is reported as `needs_rebuild_deferred` and `run_index_rebuild` is asserted NOT called (`test_needs_rebuild_is_deferred_never_spawned`) — the tier-3 spawn lives only in the response wrapper.
- [x] AC-5: The behavior is enabled by default but disablable via config; a test asserts the kill-switch skips the optimize entirely. — `_close_optimize_enabled` reads `indexing.close_optimize_enabled` (default True); `test_kill_switch_disables_even_when_bloated` asserts the indexer is never loaded when disabled, plus `test_enabled_*` cover default/false/corrupt.
- [x] AC-6: Full framework tests run bytecode-free and docs validation passes. — `run_tests.py`: 4725 tests OK (bytecode-free); `wave_validate` clean (pending, run at wave verification).

## Tasks

- [x] Add a bloat-ratio helper (per-table on-disk size vs logical floor from row count + fixed embedding bytes). — `_index_table_bloat_ratios` (reuses `_index_dir_size` + `lancedb count_rows`; fail-safe `{}`).
- [x] Wire a bloat-gated, lock-aware, fail-safe tier-1 `wave_index_optimize` into `wave_close_response(mode="create")` before the background refresh; log the reclaim. — `_maybe_optimize_index_on_close(root)` called before `_trigger_background_index_refresh_for_paths`; summary attached to the close response as `index_optimize`.
- [x] Add the bloat-ratio threshold + enable flag to config (workflow-config / constant override). — `CLOSE_OPTIMIZE_BLOAT_RATIO`/`CLOSE_OPTIMIZE_MIN_ROW_BYTES` constants; `indexing.close_optimize_enabled` kill-switch in `docs/workflow-config.json` (default True).
- [x] Tests: gate-fires, tight-no-op, lock-held-skip, optimize-error-safe, needs-rebuild-deferred, kill-switch. — `CloseTimeOptimizeTests` (12 tests, all green) in `test_server_tools.py`, incl. a source-assertion wiring lock (optimize runs before the refresh).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`. — suite 4725 OK; `wave_validate` at wave verification.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| bloat-gate | implementer | — | Bloat-ratio helper from size + rows |
| close-wiring | implementer | bloat-gate | Lock-aware fail-safe optimize in `wave_close_response` |
| tests | qa-reviewer | close-wiring | Fires/tight/lock/error/rebuild/kill-switch |


## Serialization Points

- Single production surface in `server_impl.py` (`wave_close_response` + a bloat helper). Disjoint from `1ryce` (upgrade script). Supersedable by `1rrr0` (FTS5) later.

## Affected Architecture Docs

- `docs/architecture/` index-lifecycle doc (if present) gains a note that wave close runs a bloat-gated optimize as an interim reclaim pending the FTS5 migration; otherwise N/A (confined to `server_impl.py` + config).

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix — reclaim the accumulated bloat at the close batch boundary. |
| AC-2 | required | Must not do gratuitous optimize work on a tight index. |
| AC-3 | required | Must not race/slow close on a running build. |
| AC-4 | required | Optimize must never fail close or block on a tier-3 rebuild. |
| AC-5 | important | Operator tunability / kill-switch. |
| AC-6 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-06 | Diagnosed: `docs.lance` 698→58 MB on optimize (640 MB reclaimed) vs `code.lance` tight; cause = incremental FTS `replace=True` rebuild leaves un-GC'd `_indices/` versions that the fragment-gate never reclaims; deep optimize only runs at install/upgrade. Interim fix = bloat-gated optimize at close; structural fix deferred to `1rrr0` (SQLite FTS5 in-place segments). | `wave_index_optimize` result; `indexer.py:2306` (fragment gate), `:2350-2357` (FTS-rebuild-no-GC comment); `wave_close_response` (`server_impl.py:10037`, refresh at `:10191`). |
| 2026-07-06 | Implemented: `_close_optimize_enabled` / `_index_table_bloat_ratios` / `_maybe_optimize_index_on_close` helpers + wave-close wiring (optimize before the background refresh, tier-1 only, lock-aware, fail-safe); `CloseTimeOptimizeTests` (12) green; full suite 4725 OK. | `server_impl.py` (`_maybe_optimize_index_on_close`, wave_close_response `index_optimize`); `test_server_tools.py::CloseTimeOptimizeTests`. |
| 2026-07-06 | Gate calibration validated against the LIVE index: tight `docs` = **1.7×** (19,309 rows / 65.8 MB), tight `code` = **1.4×** (12,568 rows / 35.3 MB) — both below the 3.0 trigger → no-op; the observed 698 MB `docs` bloat = **17.6×** → fires. `MIN_ROW_BYTES=2048` + `BLOAT_RATIO=3.0` has ~1.3× headroom below the trigger for a tight table and 5.8× above it for the leaked state. | Live `lancedb count_rows` + `docs.lance`/`code.lance` on-disk sizes. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-06 | Interim bloat-gated optimize at wave close (before the close's background refresh, lock-aware, tier-1 only). | Close is a natural batch boundary at the end of a doc-heavy work unit; running optimize before the close's own refresh avoids racing its lock; gating on a bloat ratio makes it a no-op on a tight index; tier-1-only keeps close fast and never spawns an expensive rebuild. | Turn-end optimize (deferred — more frequent, needs tighter gating; close is cleaner semantics). Fix the incremental FTS-rebuild GC in `indexer.py` (rejected here — that is `1rrr0` territory / riskier). Do nothing until `1rrr0` (rejected — `docs.lance` balloons to 700 MB between deep optimizes meanwhile). |
| 2026-07-06 | Superseded-by-design note: `1rrr0` (SQLite FTS5) removes the leak at the source; this change is the bridge until it lands and can be retired then. | Avoids two permanent maintenance surfaces; the interim optimize is cheap and lossless. | Skip the interim and wait for `1rrr0` (rejected — the substrate work is larger; the bloat is live now). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Optimize at close slows the close | Gated on bloat ratio (no-op when tight); tier-1 in-place only; run before the background refresh so the lock is free; skip if lock held. |
| Optimize races the close's own background index refresh | Run the check + optimize BEFORE triggering the refresh; additionally skip if `wave_index_build_status.lock.held`. |
| A tier-3 (`needs_rebuild`) result spawns an expensive synchronous rebuild at close | Never spawn at close — log `needs_rebuild` and defer to the on-demand/install/upgrade optimize path; AC-4 locks this. |
| The bloat-ratio floor mis-estimates and never/always fires | Floor is a conservative per-row byte estimate (fixed embedding size dominates); threshold is configurable + kill-switchable; tune against the observed 12× docs bloat vs ~1× code. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
