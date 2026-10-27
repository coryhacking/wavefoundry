# Retire orphaned context-efficiency pending rows

Change ID: `21s1t-enh retire-orphaned-ce-pending-rows`
Change Status: `implemented`
Owner: implementer
Status: planned
Last verified: 2026-10-26
Wave: 21s1u retire-orphaned-ce-pending-rows

## Rationale

The context-efficiency store keeps a `wave_state` row per wave id that received telemetry. A row stays `pending=1` until a projection publishes it into the wave's record. When the id matches no wave record (the wave folder was deleted, never created, or renamed so its full id changed), nothing can ever publish it, and nothing in the framework removes or retires the row (`execution_status: executed`: a census of the framework scripts finds `wave_state.pending` cleared only by `mark_checkpoint_published` and `reconcile_checkpoint_authority`, and both start from a resolved wave record's checkpoint, so neither applies to an unresolvable id).

This repository has five such rows today, from a one-off probe, deleted waves and one renamed wave (`1yzj9 ac-locality-sensor-blocking`, now the closed `1yzj9 sensor-advisory-decisions`). Their last telemetry is 2026-07-27, 2026-07-31, 2026-08-12, 2026-09-25 and 2026-10-14 (`telemetry_event.created_at`). Wave 21s91 stopped the background monitor from re-attempting them every tick, but they stay in the pending census forever, are re-attempted once by every server process's monitor, and appear as `skipped_unknown_waves` on every all-pending hard-boundary pass. That pass is `project_pending_context_efficiency_root` with `automatic=False`, reached only from `wf_reload_mcp` and `wf_upgrade` through `project_pending_context_efficiency`; close projects only its own wave.

A separate class is out of scope here: 22 short-id alias rows (for example `1tis8` beside the published `1tis8 memory-eval-mcp-tool-and-decision-log-target`). They resolve to a real wave by prefix, but projection publishes under the folder's full id, so the alias row never clears (`execution_status: executed`, read-only store query). They need folding onto their canonical id, which is a follow-up change.

## Product Intent

- Beneficiary: operators and agents reading the context-efficiency pending census and hard-boundary results in long-lived repositories.
- Before: a pending row for a wave that no longer exists stays pending forever and is re-reported and re-attempted indefinitely.
- After: at a reload or upgrade, a pending row whose id resolves to no wave record and that has had no activity for 30 days is retired: it leaves the pending census, its telemetry is kept, and the result names it once.
- Boundary: this covers ids that resolve to no wave record only; short-id alias rows that resolve to a real wave stay pending (separate follow-up). Rows for existing waves, rows with recent activity, sealed rows, and any row when wave records cannot be read reliably are never retired. Telemetry is never deleted. A retired id that receives new telemetry becomes pending again. AC-1 and AC-4 together test the intent.

## Requirements

1. The all-pending hard-boundary pass (`project_pending_context_efficiency_root` with `automatic=False`, from reload and upgrade) retires each row matching `pending=1 AND sealed=0` whose wave id resolves to no wave record and whose last activity is at least 30 days before `now`. Last activity is the latest `created_at` (epoch seconds) across that id's `telemetry_event` and `phase_state` rows; a row with neither counts as stale. `now` is an injectable parameter defaulting to `time.time()`. Retirement runs only after the projection loop completes without an early failure return.
2. Retiring sets `pending=0` on that row only. The generation, `pending`, `sealed` and last-activity reads and the `UPDATE ... WHERE wave_id=? AND pending=1 AND sealed=0 AND generation=?` run in one `BEGIN IMMEDIATE` transaction on the store's existing write path, after the projection loop and outside `project_state_publication_lock` (retirement writes no wave record). No telemetry, phase, credit or evaluation row is deleted or re-keyed. A row whose generation changed before the transaction is left alone.
3. A candidate is an id whose projection returned `wave_not_found`. Wave directories are discovered once per pass with `record_paths.discover_wave_dirs`, and each candidate is re-resolved with `_find_wave_md_detailed` against that list; it is unresolvable only with no match and no unreadable siblings. Retirement is skipped for the whole pass when discovery finds no wave directories, when any candidate reports unreadable siblings, or when discovery or resolution raises (an ambiguous id included); a raise never retires anything. Archived waves are not searched, so an unsealed row for an archived wave can retire, which loses nothing.
4. The hard-boundary result reports retired ids in a new `retired_orphan_waves` list, present only when non-empty. Ids skipped as unknown but not retired (too recent, or retirement skipped) stay in `skipped_unknown_waves` as today.
5. The automatic background monitor never retires rows.
6. Behavior is the same on Windows, macOS, Linux and WSL2: the change uses the store's existing SQLite write path and existing wave resolution, with no new filesystem, process or locking behavior.

## Scope

**Problem statement:** pending rows for nonexistent waves are never retired.

**In scope:**

- A retirement function in `context_efficiency.py` and its call from the hard-boundary branch of `project_pending_context_efficiency_root`.
- Tests in `tests/test_server_context_efficiency.py`.
- A CHANGELOG bullet.

**Out of scope:**

- Re-keying a renamed wave's telemetry onto its current folder: the renamed wave here is closed, and closed records are not rewritten.
- Short-id alias rows that resolve to a real wave (22 today): a follow-up change.
- The close path, which projects only its own wave.
- A new MCP tool or CLI command, or a configurable threshold.
- Deleting store rows.

## Acceptance Criteria

- [x] AC-1: A test with a real store shows that a hard-boundary projection retires an unsealed pending row for an unknown id whose last activity is older than 30 days: it is absent from `pending_wave_ids` afterwards, its `telemetry_event` rows remain, and it is listed in `retired_orphan_waves`. Without the change the row is still pending.
- [x] AC-2: The same test setup shows that each of these is not retired, each in a pass that also contains a stale unknown row so the negative is not vacuous: an unknown id with activity inside 30 days (it stays in `skipped_unknown_waves`), a pending row for an existing wave, a sealed unknown row, a row whose generation changes between the decision read and the update, a pass where a wave record is unreadable (nothing in that pass retires), a pass that discovers no wave directories (nothing retires), and the automatic monitor path (nothing retires).
- [x] AC-3: A test shows that a retired id that records new telemetry is pending again. This is a regression guard: `_touch_wave` already re-pends unconditionally.
- [x] AC-4: On a scratch copy of this repository's store and `docs/waves` tree, with `now` fixed at 2026-10-26T00:00:00Z, a hard-boundary projection retires the four unknown ids whose last activity predates 2026-09-26 and leaves `20np3 worker-startup-diagnostics` (last activity 2026-10-14) pending and reported in `skipped_unknown_waves`; the short-id alias rows stay pending. The pending counts before and after are recorded in the Progress Log.
- [x] AC-5: The change's own suites (`test_server_context_efficiency.py`) and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Add the retirement function to `context_efficiency.py`.
- [x] Call it from the hard-boundary branch with the resolution guards, and add `retired_orphan_waves` to the result.
- [x] Add the AC-1 to AC-3 tests.
- [x] Run the AC-4 scratch measurement and record it.
- [x] CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| retire-orphans | implementer | — | one function, one call site, tests |

## Serialization Points

- `.wavefoundry/framework/scripts/context_efficiency.py`, `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`, `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`
- The root CHANGELOG gains one bullet.

## Affected Architecture Docs

N/A: the change adds a guarded state transition inside the existing context-efficiency store and its existing hard-boundary caller; no module boundary, data flow or verification seam changes.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The behavior itself |
| AC-2 | required | Guards against retiring live or unverifiable rows |
| AC-3 | required | Retirement must not lose later activity |
| AC-4 | required | Shows the outcome on the real data |
| AC-5 | required | Change-local verification |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-26 | Planned after wave 21s91; operator chose the 30-day threshold | Store census of the five ids and their last `telemetry_event.created_at` |
| 2026-10-26 | Readiness repair pass from the red-team and security seats and the code and QA lanes: callers corrected to reload and upgrade, alias rows named out of scope, pass-level discovery guard with `_find_wave_md_detailed`, one transaction outside the publication lock, exact row predicate, injectable `now`, retirement only after a complete loop, AC-2 negatives made non-vacuous with sealed and generation-race cases, AC-3 labelled a regression guard, AC-4 pinned instant and alias counts, three new Risks | Seat and lane reports |
| 2026-10-26 | Implemented `retire_orphan_pending_waves` in `context_efficiency.py` (one `BEGIN IMMEDIATE`, last activity over `telemetry_event` and `phase_state`, `UPDATE ... pending=1 AND sealed=0 AND generation=?`) and `_retire_orphan_waves` in `context_efficiency_handlers.py` (one `discover_wave_dirs` pass, `_find_wave_md_detailed`, skip on empty discovery, unreadable siblings or any raise), called after the hard-boundary loop | six new tests in `test_server_context_efficiency.py`; focused run 131 tests OK |
| 2026-10-26 | Known-bad on a scratch copy: removing the call, the idle cutoff, the generation guard, the sealed guard, the unreadable guard or the empty-discovery guard, or retiring on the automatic path, each fails at least one new test | scratch copy, `python3 -m unittest` |
| 2026-10-26 | AC-4 on a scratch copy of the store and `docs/waves`, `now` = 2026-10-26T00:00Z: pending 27 -> 23; retired `1u12h`, `1v4ms`, `1yzj9 ac-locality-sensor-blocking`, `zzzz-council-probe-nonexistent`; `20np3` stayed in `skipped_unknown_waves`; all 22 short-id alias rows still pending; pass `ok` | ad hoc run on the session scratch copy |
| 2026-10-26 | Full suite: 12239 tests, one failure in `test_profile_literal_census.py`: the unreadable-record mock in `test_unreliable_resolution_retires_nothing` returned a literal default-layout path. Rebuilt from `_waves_dir` and `_RECORD` so it holds under the downstream Set/Wave vocabulary profile | suite log; census and context-efficiency suites 140 tests OK after the fix |
| 2026-10-26 | Operator asked for compatibility with the downstream Waveforge model (waves become sets): the new code resolves records only through `discover_wave_dirs` and `_find_wave_md_detailed`, which honor the profile's record filename and nested root; `run_tests.py --profile second --file test_server_context_efficiency.py` (Set records in nested `docs/delivery/sets`, archive at `docs/waves`) passes. Under that profile, rows for pre-adoption archive records already resolve as unknown and can retire after 30 days, as Requirement 3 states | second-profile run: 0 of 1 files failed |
| 2026-10-26 | Delivery finding 21S1U-DEL-PHASE-ACTIVITY (qa-reviewer, do_now): no test covered `phase_state` activity. Added `test_recent_phase_activity_keeps_an_unknown_row`; the phase_state-branch mutant now fails it | scratch mutant run |
| 2026-10-26 | Implementation note: the caller captures each candidate's generation just before the transaction and the guarded `UPDATE` compares it, which also catches a change between capture and transaction. Busy contention on `BEGIN IMMEDIATE` returns no retirements, like the store's other writers; the rows retire at the next reload or upgrade | code-reviewer and security delivery notes |
| 2026-10-26 | Final full suite after the census fix and the repair: 12240 tests OK, receipt written; docs validate clean | `run_tests.py`, 560 s |
| 2026-10-26 | Gapfill: mutant and AC-4 runs used shell scripts on scratch copies, as executed probes | — |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-26 | Retire at the hard boundary by setting `pending=0`, guarded by 30 days of inactivity, unresolvable id, readable and non-empty wave discovery, and the generation; keep all telemetry. Efficacy: replaying today's data, four of the five unknown-id rows retire at the next reload or upgrade and the fifth after 2026-11-13, while the 22 alias rows are untouched (named as a follow-up); it controls the outcome directly; it could wrongly retire a row only if a wave record is missing without an unreadable signal for 30 days while its telemetry is real, and then new telemetry re-pends it and no data is lost; success is AC-4 and a pending census without them | Smallest change on the path that already identifies unknown ids; no new tool surface; reversible by any new event | (a) Operator-run maintenance tool with dry run: new MCP surface, handler-digest pin and docs for a rare housekeeping step. (b) Delete the rows: loses accounting history and is not reversible. (c) Re-key renamed waves onto the current folder: would rewrite a closed wave's accounting. (d) An explicit `retired` marker so a reappearing folder re-pends deterministically: a new state for a rare case that the next telemetry event already recovers |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A checkout missing wave folders for 30 days retires their rows | Telemetry is kept and any new event re-pends the row; empty discovery and unreadable records skip retirement |
| A retired renamed wave's numbers never reach its current record | Accepted: the renamed wave is closed; its events remain in the store |
| Accounting-gap recovery re-pends every unsealed row, retired ones included | Harmless: the next reload or upgrade retires them again |
| A retired wave's folder reappears (branch switch, restore) | Its record is not refreshed until new telemetry or close; nothing is lost |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
