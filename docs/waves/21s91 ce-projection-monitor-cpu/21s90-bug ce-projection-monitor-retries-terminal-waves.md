# CE projection monitor retries closed and unknown waves on every tick

Change ID: `21s90-bug ce-projection-monitor-retries-terminal-waves`
Change Status: `implemented`
Owner: implementer
Status: planned
Last verified: 2026-10-26
Wave: 21s91 ce-projection-monitor-cpu

## Rationale

On 2026-10-26 a long-running Wavefoundry MCP server (started by another agent host about 28 hours earlier) held one CPU core at 80 to 100 percent. A 25-second `sample` placed the work in the `wavefoundry-ce-projection-monitor` thread, in `lstat`, `stat` and directory reads. When that process was killed, three other long-running servers on the same repository rose to about 99 percent at once.

Cause, verified on this repository's tree and telemetry store (`execution_status: executed`):

- `context_efficiency.pending_wave_ids` reports 27 pending waves: 23 closed waves and 4 ids that match no wave folder (`1u12h upgrade-root-extraction-hygiene`, `1v4ms reranker-order-invariance`, `20np3 worker-startup-diagnostics`, `zzzz-council-probe-nonexistent`).
- The monitor (`_maybe_project_context_efficiency` in `wf_server/context_efficiency_handlers.py`) polls every 15 seconds. A wave becomes eligible once its generation is unchanged for the quiet period. The automatic projection of a closed wave returns `closed_wave_requires_hard_boundary`, and an unknown id returns `wave_not_found`. Neither removes the wave from the monitor's `observed` map nor resets its timestamp, so all 27 are eligible again on every later tick, forever.
- Each attempt resolves the wave through `_find_wave_md`, which reads every one of the 465 wave records. Timed here, the 27 lookups take 11.5 seconds per 15-second tick.

Why only one server was hot at a time is `inferred`: the automatic path fails fast on the shared publication lock, so concurrent servers losing that race do less work. It is not load-bearing for the fix.

## Product Intent

- Beneficiary: anyone running Wavefoundry MCP servers for long sessions, on any host.
- Before: a server that stays up past the quiet period with a closed or unknown wave pending spends most of a CPU core re-attempting projections that cannot succeed, and the load moves to the next server when one is killed.
- After: the monitor attempts such a wave once per pending generation and then leaves it alone until that generation changes; an idle server's projection monitor costs a few cheap reads per tick.
- Boundary: hard-boundary projection (reload, upgrade, close) and the meaning of "pending" in the telemetry store are unchanged. AC-1 and AC-4 together test the intent.

## Requirements

1. When an automatic projection attempt for an eligible wave returns a terminal result, the monitor does not attempt that wave again while its pending generation is unchanged. A terminal result is one the automatic path cannot change by retrying without new telemetry: `closed_wave_requires_hard_boundary`, or the wave being reported in `skipped_unknown_waves` (`wave_not_found`). Results are classified per wave from `project_pending_context_efficiency_root`'s `projected`, `skipped_unknown_waves` and `automatic_failures` lists, not from its first-failure `failed_wave` and `detail` fields.
2. When the wave's pending generation changes, the wave is treated as newly observed: it waits the quiet period and is then attempted once more.
3. Any other unsuccessful automatic attempt restarts that wave's quiet period, so it is retried after the quiet period rather than on the next tick. This includes lock contention (`index_source_busy`, `publication_lock_busy`, which are reported before a closed status is read), a failed read or publication, and an exception raised during the pass (for example an ambiguous id from `_find_wave_md`): every eligible wave's quiet period is restarted before the pass runs, so a raise leaves them re-armed rather than eligible. Under sustained contention a closed wave therefore still costs one lookup per quiet period until an attempt reaches its status.
4. Successful projections, the quiet-period rule for never-attempted generations, hard-boundary projection, and the `index_health` monitor status row keep their current behavior.
5. The behavior is the same on Windows, macOS, Linux and WSL2: the change is in-memory bookkeeping in the monitor thread with no filesystem, process or locking difference by platform.

## Scope

**Problem statement:** the automatic CE projection monitor re-attempts waves it cannot project on every 15-second tick, and each attempt scans every wave record.

**In scope:**

- The monitor's per-wave bookkeeping in `_maybe_project_context_efficiency`.
- Tests in `tests/test_server_context_efficiency.py`.
- A CHANGELOG Unreleased bullet.

**Out of scope:**

- Making `_find_wave_md` cheaper (it reads every record by design, wave 1v0lw); with terminal waves parked the monitor no longer calls it per tick.
- Removing the four phantom pending rows from the telemetry store, or tracing where they came from.
- Changing hard-boundary projection or which waves count as pending.

## Acceptance Criteria

- [x] AC-1: A unit test drives the monitor over ticks with one closed-wave response and one unknown-wave response at an unchanged generation. After the first attempt past the quiet period, further ticks (including ticks past another quiet period) make no projection call for either wave. Without the fix the same test sees an attempt on every tick after the quiet period and fails.
- [x] AC-2: A unit test shows that after a terminal result, a change in that wave's generation makes it eligible again after one quiet period, and exactly one further attempt is made. This is a regression guard: re-arming on a generation change is current behavior, so it passes without the fix too.
- [x] AC-3: A unit test shows that a retryable failure (a non-published result that is not terminal, and separately a projection pass that raises) is not re-attempted on the next tick, and is attempted again once the quiet period has elapsed. Without the fix both are re-attempted on the next tick.
- [x] AC-4: On a scratch copy of this repository's telemetry store and `docs/waves` tree, three monitor ticks run in one process with injected times (observe, then past the quiet period, then past it again) attempt the stuck waves only on the second tick; a spy on `_find_wave_md` counts zero lookups on the third tick, which finishes in well under one second. The measured counts and timings are recorded in the Progress Log. The scratch copy keeps the run from publishing into live wave records.
- [x] AC-5: The change's own suites (`test_server_context_efficiency.py`, `test_index_source_guard.py`) and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Classify each eligible wave's automatic result as projected, terminal or retryable from the per-wave `projected`, `skipped_unknown_waves` and `automatic_failures` lists.
- [x] Park terminal waves in `observed` at their generation; restart the quiet period for retryable ones.
- [x] Add the AC-1 to AC-3 tests.
- [x] Run the AC-4 live measurement and record it.
- [x] CHANGELOG Unreleased bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| monitor-fix | implementer | — | one function plus tests |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`, `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`, `.wavefoundry/framework/scripts/tests/test_index_source_guard.py`
- The root CHANGELOG gains one Unreleased bullet.

## Affected Architecture Docs

N/A: the change is confined to the monitor's in-memory retry bookkeeping inside one module; no boundary, data flow or verification seam changes.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The defect itself |
| AC-2 | required | Parking must not hide later telemetry for the wave |
| AC-3 | required | Retryable failures must back off, not spin |
| AC-4 | required | Shows the observed CPU cost is gone on the real data |
| AC-5 | required | Change-local verification |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-26 | Planned from a live diagnosis of a hot server | `sample` of the process; 27 pending waves; 11.5 s of lookups per tick |
| 2026-10-26 | Readiness repair pass from the red-team and security seats: raise counts as retryable, contention bound stated, per-wave lists named, reopen risk, AC-4 on a scratch copy, AC-2 labelled a regression guard, index-source-guard suite added, unverified hard-boundary claim removed | Council seat reports |
| 2026-10-26 | Implemented in `_maybe_project_context_efficiency`: every eligible wave is re-armed at `(generation, now)` before the pass; projected waves are popped; terminal waves (`skipped_unknown_waves`, or `automatic_failures` with reason `closed_wave_requires_hard_boundary`) are parked at `(generation, inf)`. Readiness lane notes carried in as tests: a mixed terminal and retryable pass, and a parked closed wave staying pending until a hard boundary projects it | `test_terminal_waves_are_attempted_once_per_generation`, `test_mixed_pass_parks_only_the_terminal_wave`, `test_parked_wave_rearms_when_its_generation_changes`, `test_retryable_failure_and_raise_wait_out_the_quiet_period`, `test_parked_closed_wave_stays_pending_for_the_hard_boundary`; focused run of both suites 134 tests OK |
| 2026-10-26 | Known-bad: on a scratch copy with both new blocks removed, all five new tests fail; with only parking removed, the AC-1, AC-2, mixed-pass and hard-boundary tests fail | scratch copy under the session scratchpad, `python3 -m unittest` |
| 2026-10-26 | AC-4 on a scratch copy of the real store and `docs/waves` (28 pending): tick 1 0.02 s, 0 lookups; tick 2 7.01 s, 28 lookups, 2 open waves projected, 26 parked; tick 3 0.02 s, 0 lookups | `_find_wave_md` spy; the remaining failures were all terminal (closed, or 5 unknown ids) |
| 2026-10-26 | Full suite: first run 12233 tests passed but was refused only for this wave's own ledger writes during the run; rerun with no concurrent writes OK, receipt written. Docs validate clean | `run_tests.py`, 12233 tests OK in 686 s; `wf_validate_docs` ok |
| 2026-10-26 | Gapfill: AC-4 and known-bad runs used shell scripts on scratch copies, since they are executed probes, not retrieval | — |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-26 | Park terminal waves in the monitor's `observed` map until their generation changes; restart the quiet period after a retryable failure. Efficacy: replaying the incident, the 27 waves are attempted once and then cost one snapshot read each per tick; it controls the outcome directly; it can wrongly park a wave that is reopened (`unseal_wave` leaves the generation unchanged) or whose folder appears later, until its next telemetry event or a hard boundary (see Risks); whether hard boundaries clear closed waves from pending is `unverified`, since 23 remain pending here, and the fix does not rely on it; success is measured by AC-4 and by servers staying idle | Smallest change at the point of the defect; uses the generation the monitor already tracks | (a) Resolve wave folders once per tick: each lookup still reads all 465 records, so a tick stays seconds long and keeps repeating. (b) Exclude closed waves from `pending_wave_ids`: changes the authority census that hard boundaries rely on. (c) Only restart the quiet period after any failure: cuts the cost about eightfold but still repeats forever |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A parked wave's telemetry stays unprojected until a hard boundary | This is the existing contract for closed waves; a generation change re-arms the wave (AC-2) |
| Parking is per process, so each server restart attempts the stuck waves once | One attempt per pending generation per process is bounded and acceptable |
| A closed wave parked and then reopened (`wf_reopen_wave` leaves the generation unchanged) stays unprojected until its next telemetry event or a hard boundary | Rows stay pending, so nothing is lost; the reopened wave's next tool call raises the generation and re-arms it |
| Parked waves leave the monitor status row reporting `quiet_period_pending` | Accepted; the row's `pending_count` is unchanged and no new status field is added |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
