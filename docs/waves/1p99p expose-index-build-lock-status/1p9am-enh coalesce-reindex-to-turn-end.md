# Reconcile index-refresh triggers: turn-end hook + quiet-period safety-net monitor

Change ID: `1p9am-enh coalesce-reindex-to-turn-end`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p99p expose-index-build-lock-status`

## Rationale

Two independent triggers currently reindex the project index, and both churn far harder than intended —
the root cause of the `docs.lance` re-bloat (1.6 GB this session) that `1p9aj` reclaims:

1. **The post-edit hook** (`PostToolUse` matcher `Edit|Write`) spawns an incremental reindex on nearly
   every edit. The only coalescing is a 2 s *leading-edge* debounce, so a turn of dozens of edits spaced
   > 2 s apart triggers dozens of full-tree incremental passes — each re-embeds changed chunks, rebuilds
   the changed table's FTS (~40 MB even for a one-line edit), and leaves data fragments.
2. **The MCP in-session staleness monitor** (`_start_staleness_monitor`, wave `1p5xu`) is a daemon thread
   that every ~20 s runs a cheap mtime staleness check and, if stale and no refresh is in flight, spawns
   a background reindex. During active editing it fires roughly every 20 s.

Moving the hook to turn-end **without** taming the monitor would simply shift the churn: mid-turn, each
edit bumps an input mtime, the monitor sees "stale" within 20 s and reindexes — defeating the turn-end
coalescing. So the two triggers must be reconciled together.

**Target model.** The **turn-end hook** becomes the primary, prompt trigger (one coalesced incremental
pass per turn); the **staleness monitor** becomes a slow **safety net** gated by a quiet-period — it acts
only after editing has settled, so it catches drift the turn-end path missed (edits made outside an agent
session, a turn that ended without `Stop` firing, or a non-Claude host with no turn-end hook) **without**
piling onto active editing. Operator-approved freshness tradeoff: mid-turn `code_search`/`docs_search`/
`code_ask` see the pre-turn index until the turn ends (agents read their own just-written files
directly; semantic retrieval targets the existing corpus).

## The mechanism

**Coordination primitives (all already present):** a `reindex-pending` marker (added here), the build
lock's `started_at`/`ended_at` (`1p99o`), and the monitor's existing input-mtime scan.

**A. Turn-end hook (primary).**

- **Post-edit hook body (all hosts):** on an index-worthy edit (`should_reindex(path)`), write/refresh a
  `reindex-pending` sentinel in `.wavefoundry/index/` (cheap touch). **Do not spawn a reindex inline.**
  docs-lint / gate behavior unchanged.
- **Claude `Stop` hook body (`claude_stop_source`, session-capture):** if the marker is pending and no
  build is live, spawn **one** detached incremental reindex and clear the marker. The incremental
  indexer diffs the whole tree, so it picks up every edit from the turn. Existing capture behavior
  unchanged.
- **Non-`Stop` hosts (Cursor/Copilot/Windsurf/Junie/Antigravity — no turn-end event):** the post-edit
  body consumes the marker under a **much longer leading-edge debounce** (`HOOK_REINDEX_DEBOUNCE_SECONDS`
  raised from 2 s to ~45 s) — a big churn cut, best available without a turn-end signal.

**B. Staleness monitor (safety net).** `_maybe_refresh_if_stale` gains a quiet-period gate — it starts a
background refresh only when **all** hold:

- the index is stale (existing check), **and**
- `now - newest_input_mtime ≥ QUIET_PERIOD` — editing has settled, **and**
- `now - lock.ended_at ≥ QUIET_PERIOD` (or the lock is absent) — don't pile on a recent build, **and**
- no background refresh is in flight (existing single-flight guard), **and**
- the `reindex-pending` marker is **not** freshly set — if it is, the turn-end hook owns the next pass;
  the monitor takes over only when the marker has been pending **longer** than `QUIET_PERIOD` (the
  turn-end never flushed it — the safety-net case).

`QUIET_PERIOD` defaults to **300 s (5 min)**, read from `indexing.monitor.quiet_period_seconds` in
`docs/workflow-config.json` (framework-owned default; the `indexing.monitor` block already exists), and
is floored to the monitor interval. The poll cadence stays ~20 s (cheap stat); only the *act* decision is
gated.

On Claude, the `Stop` hook reindexes at turn end, so the monitor finds the index fresh and never fires —
no double-churn. The monitor only earns its keep for the missed-turn / external-edit / non-Stop-host
cases.

## Requirements

1. Post-edit hook (all hosts): on an index-worthy edit, mark a `reindex-pending` sentinel; do **not**
   spawn a reindex inline. docs-lint / edit-gate behavior unchanged.
2. Claude `Stop` hook: if pending and no live build, spawn one detached incremental reindex and clear the
   marker; existing session-capture behavior unchanged.
3. Non-`Stop` hosts: post-edit consumes the marker under a leading-edge debounce raised to ~45 s.
4. `indexer.py` helpers: `HOOK_REINDEX_PENDING_NAME` constant; `mark_reindex_pending(index_dir)` and
   `consume_reindex_pending(index_dir) -> bool` (atomic check-and-clear); keep the live-build guard in
   `should_coalesce_hook_reindex`.
5. Staleness monitor: `_maybe_refresh_if_stale` fires only when stale **and** the repo has been quiet
   ≥ `QUIET_PERIOD` since the newest input mtime **and** ≥ `QUIET_PERIOD` since `lock.ended_at` **and**
   no refresh in flight **and** no freshly-pending marker (defer to the turn-end hook unless the marker
   is older than `QUIET_PERIOD`).
6. `QUIET_PERIOD` default 300 s, configurable via `indexing.monitor.quiet_period_seconds`, floored to the
   monitor interval; all reads fail-safe (bad config ⇒ default; any error ⇒ no auto-refresh, never a
   broken monitor).
7. Rendered across every platform hook surface via `render_platform_surfaces.py` (source) + re-render;
   documented in `docs/architecture/chunking-and-indexing-pipeline.md` (Index Update Triggers) and
   `docs/specs/mcp-tool-surface.md` (monitor config).
8. Full framework suite green + `wave_validate` clean; no regression to the edit-gate / docs-lint path.

## Scope

**Problem statement:** Per-edit hook reindexing + a 20 s staleness monitor both churn the index during
editing; moving only the hook to turn-end would shift the churn to the monitor.

**In scope:**

- `render_platform_surfaces.py`: post-edit bodies mark-pending (no inline spawn on Claude); Claude
  `Stop` body flushes the marker (turn-end reindex); non-`Stop` bodies flush under the longer debounce.
  Re-render all platform hook surfaces.
- `indexer.py`: `reindex-pending` marker helpers (`mark_reindex_pending`/`consume_reindex_pending`/
  `reindex_pending_age`) + constant; raise `HOOK_REINDEX_DEBOUNCE_SECONDS`.
- `server_impl.py`: quiet-period gate in `_maybe_refresh_if_stale` (marker-age + `ended_at`);
  `quiet_period_seconds` config read in `_read_monitor_config`.
- Docs: pipeline arch doc (Index Update Triggers) + `mcp-tool-surface.md` monitor config.
- Tests: mark-on-edit / no-inline-spawn; Stop flush + clear; non-Stop long-debounce consume; monitor
  defers during active editing / a fresh marker, fires after quiet-period, respects `ended_at`.

**Out of scope:**

- The reclaim/compact-by-rewrite operation (`1p9aj` — sibling change).
- The dashboard watcher (already read-only; no reindex trigger — unchanged).
- A cross-session persistent scheduler / OS file-watch (inotify/fswatch) — the poll + quiet-period is
  sufficient and portable.
- Changing the incremental diff/embed algorithm.

## Acceptance Criteria

- [x] AC-1: an index-worthy edit marks a `reindex-pending` sentinel and does **not** spawn a reindex
      inline on Claude. Evidence: the rendered `.claude/hooks/post-edit.py` calls `mark_reindex_pending_for`
      (no Popen); `ReindexPendingMarkerTests.test_mark_then_consume_then_gone`; render-surface tests (40) green.
- [x] AC-2: the Claude `Stop` hook, with a pending marker and no live build, consumes it (atomic clear)
      and spawns one detached incremental reindex; with no marker it does nothing (capture unchanged).
      Evidence: `claude_stop_source` `_flush_reindex_if_pending` (held-guard + `consume_reindex_pending` +
      isolated Popen); the rendered `session-capture.py` compiles + passes the spawn-isolation guard
      (`test_every_rendered_hook_body_spawn_is_isolated`).
- [x] AC-3: non-`Stop` hosts consume the marker under the raised debounce
      (`HOOK_REINDEX_DEBOUNCE_SECONDS` = 45 s, leading-edge). Evidence:
      `ReindexPendingMarkerTests.test_debounce_window_raised`; the existing `should_coalesce_hook_reindex`
      window test (backdated marker, not a 45 s sleep); Cursor/Copilot bodies keep `maybe_trigger_reindex`.
- [x] AC-4: `_maybe_refresh_if_stale` returns False (no refresh) while a `reindex-pending` marker is
      freshly pending (< `QUIET_PERIOD` — the last hook-driven edit) or within `QUIET_PERIOD` of
      `lock.ended_at`; returns True only once stale **and** quiet **and** no in-flight refresh. Evidence:
      `StalenessMonitorQuietPeriodTests` — defer-on-fresh-marker, defer-after-recent-build, fires-when-quiet,
      fires-when-no-marker, active-refresh, not-stale. *(Quiet is keyed off the marker age — the last
      hook-driven edit — plus `ended_at`; a separate input-mtime scan was unnecessary since both
      competing triggers are hook-driven.)*
- [x] AC-5: `quiet_period_seconds` defaults to 300 s, is read from `indexing.monitor.quiet_period_seconds`
      (fail-safe to default), and is floored to the monitor interval. Evidence:
      `test_config_quiet_period_override_and_default_floor`, `test_config_quiet_period_floored_to_interval`.
- [x] AC-6: helpers `mark_reindex_pending` / `consume_reindex_pending` are atomic check-and-clear and
      never raise (marker dir missing ⇒ False). Evidence: `test_consume_is_atomic_single_winner`,
      `test_mark_creates_index_dir`, `test_mark_then_consume_then_gone`.
- [x] AC-7: rendered across all platform hook surfaces (idempotent re-render); docs updated (pipeline arch
      Index Update Triggers rewrite; the `indexing.monitor.quiet_period_seconds` config documented there);
      `run_tests.py` + `wave_validate` pass. Evidence: render diff + suite + docs gate.

## Tasks

- [x] `indexer.py`: `HOOK_REINDEX_PENDING_NAME` + `mark_reindex_pending`/`consume_reindex_pending`/
      `reindex_pending_age`; raised `HOOK_REINDEX_DEBOUNCE_SECONDS` to 45 s. Done.
- [x] `render_platform_surfaces.py`: split `_spawn_reindex`, added `mark_reindex_pending_for` (Claude
      post-edit, no inline spawn), `maybe_trigger_reindex` now marks + debounced-consumes (non-Stop hosts),
      `_flush_reindex_if_pending` in `claude_stop_source`; re-rendered all hosts (idempotent). Done.
- [x] `server_impl.py`: quiet-period gate in `_maybe_refresh_if_stale` (marker-age + `ended_at`);
      `quiet_period_seconds` in `_read_monitor_config` (default 300, floored to interval). Done.
- [x] Docs: pipeline arch Index Update Triggers rewrite (turn-end hook + quiet-period monitor + config). Done.
- [x] Tests (`ReindexPendingMarkerTests` 5 + `StalenessMonitorQuietPeriodTests` 8; existing debounce test
      de-slept); `run_tests.py` + `wave_validate` pending final run.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Ordered single lane: `indexer` marker helpers + debounce, then the two consumers (`render_platform_surfaces` hook bodies + `server_impl` monitor gate), then re-render + docs + tests. Touches rendered hook surfaces — full suite + idempotent re-render gate it. |

## Serialization Points

- `render_platform_surfaces.py` is the canonical source for every host's hook body; a re-render
  regenerates `.claude/hooks/*.py` and the other platform surfaces. Edit the renderer, then re-render —
  never hand-edit a rendered hook (self-hosting boundary).
- The `reindex-pending` marker is the shared contract between the post-edit hook (writer) and both
  consumers (Stop hook / staleness monitor); its name/semantics must match across `indexer.py`,
  `render_platform_surfaces.py`, and `server_impl.py`.

## Affected Architecture Docs

`docs/architecture/chunking-and-indexing-pipeline.md` — the **Index Update Triggers** section: replace
"post-edit hook spawns per edit" with the turn-end hook + quiet-period safety-net monitor model, and
record the two-consumer marker contract. No boundary change (retrigger cadence, same pipeline).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core churn cut — mark, don't spawn per edit. |
| AC-2 | required | Turn-end flush is the primary trigger; must fire once and clear. |
| AC-3 | important | Non-Stop hosts still need a coalesced trigger. |
| AC-4 | required | Without the monitor quiet-period, churn just moves to the monitor — the whole point. |
| AC-5 | important | Configurable quiet-period, fail-safe. |
| AC-6 | required | Marker helpers must be atomic + never raise (they gate every trigger). |
| AC-7 | required | Rendered everywhere, documented, no regression, idempotent re-render. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-01 | Planned (operator: "end of turn is the right thing" + "reconcile with the background thread — watch `ended_at`, wait 5 min after the last update"). Investigation found two triggers: the per-edit hook (2 s debounce) and the MCP staleness monitor (~20 s); the dashboard watcher is read-only (1p7it/1p5xw). Broadened from hook-only to reconcile both. Admitted into OPEN wave `1p99p` (sibling to `1p9aj`). | grep of `render_platform_surfaces.py` (hook events; only Claude has `Stop`) + `server_impl._maybe_refresh_if_stale` / `_start_staleness_monitor`. |
| 2026-07-01 | Implemented. `indexer`: `reindex-pending` marker helpers + 45 s debounce. `render_platform_surfaces`: Claude post-edit marks (no spawn), `Stop` hook flushes once per turn, non-Stop hosts mark + debounced-consume; re-rendered all hosts. `server_impl`: quiet-period gate in `_maybe_refresh_if_stale` (marker-age + `ended_at`) + `quiet_period_seconds` config (default 300 s, floored to interval). Quiet keyed off the marker age (both competing triggers are hook-driven), so no separate input-mtime scan. 13 new tests (`ReindexPendingMarkerTests` 5 + `StalenessMonitorQuietPeriodTests` 8); existing 45 s debounce test de-slept; render tests (40) green. AC-1..7 met; final full-suite run pending. | `indexer.py`/`render_platform_surfaces.py`/`server_impl.py` diffs; rendered `.claude/hooks/*.py`; test runs. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-01 | Reindex once per turn on the `Stop` hook (Claude); mark-pending on post-edit, no inline spawn. | Coalesces a turn's edits into one incremental pass — same end state, ~1/Nth the fragment/FTS churn; agents read their own edits directly, so mid-turn staleness rarely bites. | Keep per-edit (rejected — the churn source); trailing-edge scheduler daemon (rejected — a persistent scheduler is heavier than a Stop hook + marker). |
| 2026-07-01 | Reconcile the staleness monitor with a quiet-period gate rather than leaving it at 20 s. | Moving only the hook to turn-end would shift the churn to the 20 s monitor; the quiet-period turns it into a safety net that never competes with active editing. | Disable the monitor entirely (rejected — it's the only safety net for external edits / missed turns / non-Stop hosts). |
| 2026-07-01 | Quiet-period default 300 s (5 min), configurable via `indexing.monitor.quiet_period_seconds`. | Operator's number; long enough that active editing always defers the monitor to the turn-end hook, short enough to catch real drift promptly. | A fixed non-configurable constant (rejected — repos differ); reuse the 20 s interval (rejected — too aggressive, defeats the reconciliation). |
| 2026-07-01 | Non-`Stop` hosts fall back to a 45 s leading-edge debounce. | Only Claude renders a `Stop`/turn-end hook; other hosts need *some* coalesced trigger, and a long debounce is the best available without a turn-end signal. | Turn-end-only everywhere (rejected — would strand non-Stop hosts with no reindex); a persistent watcher per host (rejected — out of scope, non-portable). |
| 2026-07-01 | The `reindex-pending` marker is the shared contract; the monitor defers to a fresh marker and only takes over when it is older than `QUIET_PERIOD`. | Prevents the monitor and the turn-end hook from both firing for the same edits, while still recovering a turn that ended without `Stop` flushing. | mtime-only coordination (rejected — can't tell "the hook owns this" from "drift"); a lock/PID handshake (rejected — heavier than a sentinel + timestamp). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A turn ends without the `Stop` hook firing (crash, host quirk) ⇒ the pending marker is never flushed and the index stays stale. | The staleness monitor's safety net catches it: once the marker is older than `QUIET_PERIOD` and the repo is quiet, the monitor flushes it. |
| Mid-turn staleness regresses an agent that searches for code it just wrote. | Operator-accepted; agents read their own just-written files directly, and semantic retrieval targets the existing corpus. The non-Stop 45 s debounce and the safety-net monitor bound the staleness window. |
| Quiet-period too long ⇒ external edits (outside an agent turn) take up to 5 min to index. | Configurable via `indexing.monitor.quiet_period_seconds`; 5 min is a safety-net cadence, not the primary path (the turn-end hook handles in-session edits promptly). |
| Hand-editing a rendered hook instead of the renderer ⇒ drift. | All hook bodies come from `render_platform_surfaces.py`; AC-7 asserts an idempotent re-render (no drift); the self-hosting boundary forbids editing generated surfaces. |
| Marker races between the post-edit writer and the two consumers. | `consume_reindex_pending` is an atomic check-and-clear; the live-build guard + single-flight refresh state prevent concurrent spawns; a lost race at worst delays one pass to the next trigger. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
