# Upgrade Lock Survives Docs-Gate Failure On A Half-Replaced Tree

Change ID: `1p44o-bug upgrade-lock-survives-gate-failure`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-08
Wave: 1p44n framework-1p6-hardening

## Rationale

The upgrade lock is a data-safety guard: while it is present, downstream consumers (the dashboard watcher, `--cleanup`/resume) treat the tree as mid-upgrade and avoid acting on it. Today that guard is removed in exactly the wrong case.

In `upgrade_wavefoundry.py:1607-1616`, the `except SystemExit:` handler unconditionally calls `upgrade_lib.remove_upgrade_lock(root)` (line 1614) and re-raises — even though the `try` body has already mutated the tree: it extracted the zip (`upgrade_wavefoundry.py:1538-1543`, `zf.extractall`), rendered surfaces (`upgrade_wavefoundry.py:1572`, `phase_surface_rendering`), and pruned files (`upgrade_wavefoundry.py:1577`, `phase_pruning`). `phase_docs_gate` raises `sys.exit(1)` on gate failure (`upgrade_wavefoundry.py:1151`), which lands in this handler. Meanwhile the SUCCESS path (`upgrade_wavefoundry.py:1618-1626`) never removes the lock — only `--cleanup` / `phase_cleanup` (line 1254) does. The behavior is inverted: a docs-gate FAILURE tears down the guard on a half-replaced tree, while success keeps it.

Two downstreams act on the prematurely removed lock:

- **Dashboard** — `dashboard_server.py:705-734` `_watch_loop` polls every `_WATCH_INTERVAL = 3.0` (`dashboard_server.py:31`). When the lock disappears while `_upgrade_paused` (line 720), it sets paused `False`, calls `_rebuild(force_git=True)` (line 726), and `signal_startup('post-upgrade reindex')` (lines 730-733) — reindexing a gate-failed tree. (Timing-conditional: the 3s poll must catch the lock window.)
- **Cleanup** — `--cleanup` reads all fields from the lock (`upgrade_wavefoundry.py:1466-1472`); if the lock is gone, `read_upgrade_lock` returns `None`, `update_upgrade_lock` is a no-op (`upgrade_lib.py:75-77`), and `_print_operator_summary` (`upgrade_wavefoundry.py:1266-1299`) prints `Version: (none) -> (unknown)` (lines 1273-1274) and `Files pruned: 0` (line 1285). Separately, line 1286 prints a HARDCODED `Docs gate: PASSED` — a constant string with no parameter, a latent always-PASSED bug independent of the lock.

This is a DATA-SAFETY fix and should be implemented first in the wave.

## Requirements

1. Track a `tree_mutated` flag, set to true immediately after `zf.extractall` succeeds (`upgrade_wavefoundry.py:1542-1543`), so the handler can distinguish pre-mutation from post-mutation failures.
2. In the `except SystemExit:` handler (`upgrade_wavefoundry.py:1607-1616`), when `tree_mutated` is true, do NOT call `remove_upgrade_lock`; instead call `update_upgrade_lock` with failure markers (`failed_phase`, `failed_at`) so the lock is RETAINED in a known-failed state.
3. When `tree_mutated` is false (failure before any tree mutation), preserve current behavior and remove the lock.
4. The dashboard watch loop must not trigger `_rebuild(force_git=True)` / `signal_startup` reindex when the tree is gate-failed; treat a retained lock bearing a failure marker as still-paused rather than as upgrade success.
5. `phase_cleanup` / `_print_operator_summary` must reflect the real lock state: warn when `read_upgrade_lock` returns `None` instead of printing an all-defaults summary.
6. The `Docs gate:` summary line (`upgrade_wavefoundry.py:1286`) must reflect the actual gate result read from the lock, never a hardcoded `PASSED` constant.
7. Regression tests must cover the SystemExit handler (mutated vs pre-mutation) and the summary-line gate-result rendering.

## Scope

**Problem statement:** On a post-extract docs-gate failure, the upgrade lock is unconditionally removed on a half-replaced tree, inverting the guard's intent (failure removes the guard, success keeps it). Two downstreams then act on the missing lock: the dashboard force-reindexes a gate-failed tree, and `--cleanup` prints an all-defaults summary including a separately hardcoded always-`PASSED` docs-gate line.

**In scope:**

- Adding a `tree_mutated` flag and making the `except SystemExit:` handler conditional (`upgrade_wavefoundry.py:1538-1616`).
- Writing failure markers (`failed_phase`, `failed_at`) to the lock on post-mutation failure via `update_upgrade_lock`.
- Fixing the hardcoded `Docs gate: PASSED` line to reflect actual state (`upgrade_wavefoundry.py:1286`).
- Making `phase_cleanup` warn when the lock is absent rather than printing all-defaults (`upgrade_wavefoundry.py:1266-1299`, `1466-1472`).
- Belt-and-suspenders: dashboard watch loop checks for a failure marker before treating lock-removal/retention as upgrade success (`dashboard_server.py:705-734`).
- Regression tests for the handler and the summary line.

**Out of scope:**

- Automatic rollback/restore of the half-replaced tree (this change only preserves the guard and real state; operator-driven recovery is separate).
- Broader refactor of the upgrade phase pipeline or lock schema beyond adding failure-marker fields.
- Changes to other failure paths not routed through `phase_docs_gate` / `SystemExit`.

## Acceptance Criteria

- [ ] AC-1: On a docs-gate failure that occurs after `zf.extractall` (post-extract), the upgrade lock is RETAINED and carries a failure marker (`failed_phase` set to the failing phase, `failed_at` timestamp); `remove_upgrade_lock` is not called.
- [ ] AC-2: On a failure that occurs before any tree mutation, the lock is removed (existing behavior preserved).
- [ ] AC-3: The dashboard `_watch_loop` does not call `_rebuild(force_git=True)` or `signal_startup` post-upgrade reindex when the lock is retained with a failure marker (gate-failed tree stays paused).
- [ ] AC-4: `phase_cleanup` / `_print_operator_summary` warns when `read_upgrade_lock` returns `None` and does not emit an all-defaults summary (`Version: (none) -> (unknown)`, `Files pruned: 0`) as if it were a real completed upgrade.
- [ ] AC-5: The `Docs gate:` summary line reflects the actual gate result read from a lock field (PASSED only when the gate passed, FAILED otherwise) and is never a hardcoded constant.
- [ ] AC-6: Regression tests assert (a) the SystemExit handler retains the lock with a failure marker on a post-mutation failure and removes it on a pre-mutation failure, and (b) the summary line renders the gate result from lock state rather than a constant.
- [ ] AC-7: `python3 .wavefoundry/framework/scripts/run_tests.py` passes with the new tests included.

## Tasks

- [ ] Introduce a `tree_mutated` flag in `do_upgrade` and set it `True` immediately after `zf.extractall` succeeds (`upgrade_wavefoundry.py:1542-1543`).
- [ ] Rewrite the `except SystemExit:` handler (`upgrade_wavefoundry.py:1607-1616`) to branch on `tree_mutated`: post-mutation → `update_upgrade_lock(root, failed_phase=..., failed_at=...)` and keep the lock; pre-mutation → `remove_upgrade_lock(root)`.
- [ ] Capture the failing phase name for `failed_phase` (e.g. `docs_gate`) so markers are meaningful.
- [ ] Add `failed_phase` / `failed_at` handling to the lock read/update path so `update_upgrade_lock` persists them and `read_upgrade_lock` surfaces them (`upgrade_lib.py:75-77`).
- [ ] Replace the hardcoded `Docs gate: PASSED` line (`upgrade_wavefoundry.py:1286`) with a value derived from lock state (passed vs failed marker).
- [ ] Make `phase_cleanup` / `_print_operator_summary` (`upgrade_wavefoundry.py:1266-1299`, `1466-1472`) emit a warning when `read_upgrade_lock` returns `None` instead of an all-defaults summary.
- [ ] Add the dashboard belt-and-suspenders check in `_watch_loop` (`dashboard_server.py:705-734`): inspect the lock for a failure marker before treating lock state as upgrade completion.
- [ ] Add regression tests for the SystemExit handler (mutated/pre-mutation) and the gate-result summary line.
- [ ] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and confirm green.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| handler-and-flag | Engineering | — | `tree_mutated` flag + conditional `except SystemExit:` handler in `upgrade_wavefoundry.py` |
| lock-markers | Engineering | — | `failed_phase` / `failed_at` persistence in `upgrade_lib.py`; co-design with handler-and-flag |
| cleanup-summary | Engineering | lock-markers | Gate-result line fix + absent-lock warning in `_print_operator_summary` / `phase_cleanup` |
| dashboard-guard | Engineering | lock-markers | `_watch_loop` failure-marker check in `dashboard_server.py` |
| tests | Engineering | handler-and-flag, cleanup-summary | Regression tests for handler + summary line |

## Serialization Points

- `upgrade_wavefoundry.py` — shared with 1p44p / 1p44q / 1p44r / 1p454; coordinate edits to avoid conflicting changes in the upgrade pipeline.
- `upgrade_lib.py` — lock read/update schema change (`failed_phase` / `failed_at`); coordinate with any other consumer of the lock.
- `dashboard_server.py` — `_watch_loop` change; coordinate with any concurrent dashboard work.

## Affected Architecture Docs

N/A — this is a bugfix to existing control flow within the upgrade pipeline and lock lifecycle; it introduces no new module boundary, layering change, or data-flow surface beyond two additive lock fields. Reviewer to confirm no `docs/architecture/` update is warranted.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core data-safety fix: the guard must survive a half-replaced tree. |
| AC-2 | required | Preserving pre-mutation cleanup prevents stale locks blocking healthy retries. |
| AC-3 | required | Prevents the dashboard from force-reindexing a gate-failed tree. |
| AC-4 | important | Correct operator signal; absent-lock warning avoids misleading all-defaults summary. |
| AC-5 | required | Fixes the latent always-`PASSED` bug; operators must see true gate state. |
| AC-6 | required | Locks the regression so the inversion cannot silently return. |
| AC-7 | required | Test suite must pass as the verification gate for the change. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-08 | Keep the lock on a post-mutation (tree_mutated) failure and write a failure marker, rather than always removing it | The lock is the data-safety guard; it must survive the dangerous half-replaced state so downstreams stay paused and `--cleanup`/resume can read real state | Remove-always (current behavior — rejected, inverts the guard); auto-rollback the tree (out of scope, higher risk) |
| 2026-06-08 | Derive the `Docs gate:` summary line from a lock field instead of a hardcoded `PASSED` constant | Line 1286 always reports PASSED regardless of actual outcome — a separate latent bug that misleads operators | Leave hardcoded (rejected); remove the line entirely (rejected — operators rely on the signal) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Retaining the lock blocks a clean re-run if the operator expects a fresh start | Failure marker is operator-visible and `--cleanup`/resume read it; document that resume clears the marker on success |
| Lock schema change (`failed_phase`/`failed_at`) breaks other lock consumers | Make fields additive/optional; `read_upgrade_lock` tolerates their absence on older locks |
| Dashboard marker check races with the 3s poll window | Guard checks the marker on each poll before acting; retained lock means default branch is "stay paused" |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
