# Reopen by short id creates context-efficiency alias rows that never clear

Change ID: `21s8u-bug ce-short-id-alias-pending-rows`
Change Status: `implemented`
Owner: implementer
Status: planned
Last verified: 2026-10-26
Wave: 21s8v ce-short-id-alias-rows

## Rationale

The context-efficiency store holds 22 pending rows keyed by a bare five-character wave id (for example `1tis8`) next to the wave's real, published row keyed by its full folder id (`1tis8 memory-eval-mcp-tool-and-decision-log-target`). Every one of the 22 rows begins with a `wf_reopen_wave` event (`execution_status: executed`, read-only store query of `telemetry_event.tool_name` per key).

Cause, verified in the code (`execution_status: executed` by reading the success path):

- `wf_reopen_wave` (`wf_server/server_impl.py`) takes `canonical = _context_data(result).get("wave_id") or wave_id`, but `wf_reopen_wave_response` returns the caller's argument as `data.wave_id`. Reopening with a short id therefore calls `context_efficiency.unseal_wave` and sets focus on the short id, not the folder id.
- Focus then attributes every later tool call to the short id, creating and growing the alias row. `unseal_wave` updates no row (the real wave's row stays sealed).
- Projection resolves the alias to the real wave and publishes under the folder id (`canonical_wave = wave_md.parent.name` in `_project_context_efficiency_wave`), so the alias row is never cleared. Each reload or upgrade re-publishes the canonical wave, and for an open canonical wave the background monitor re-attempts it every quiet period.

21 of the 22 canonical waves are closed and one (`21fgr`) is paused.

No other producer creates such keys (`execution_status: executed`, code read): the lifecycle focus path sets focus only on `wave_md.parent.name` after resolution, and `wf_context_efficiency_eval` writes only when a `phase_state` row already exists under the key (`attach_evaluation` refuses an unknown phase).

## Product Intent

- Beneficiary: anyone reopening a wave by short id, and anyone reading the context-efficiency pending census or reload and upgrade results.
- Before: reopening by short id splits the wave's telemetry onto a key that never publishes, leaves the real row sealed, and leaves a permanently pending alias row.
- After: reopening by any accepted id unseals and focuses the wave's canonical folder id, so new work lands on the real row; existing alias rows are retired at the next reload or upgrade, keeping their telemetry.
- Boundary: rows keyed by the canonical folder id are never retired by this change; alias telemetry is not merged into canonical records (closed records are not rewritten); retirement uses the same guards as wave 21s1u. AC-1 and AC-4 together test the intent.

## Requirements

1. After a successful reopen, `wf_reopen_wave` resolves the wave record with `_find_wave_md` inside its existing `try`, under the publication lock it already holds, and uses the record's folder name as the canonical id for both `unseal_wave` and the focus set. If the record cannot be resolved, neither unseal nor focus runs and the existing `focus_stage_not_applied` reporting applies. The tool's response fields and docstring are unchanged.
2. At the all-pending hard boundary (`project_pending_context_efficiency_root` with `automatic=False`), the retirement step runs on every pass that completes the loop, not only when unknown ids exist. It receives the skipped-unknown ids (orphan candidates, unchanged from wave 21s1u) and the projected ids (alias candidates); an alias projects successfully because projection resolves it and publishes under the folder name, so it lands in `projected`. A projected key is an alias when, in the same single discovery pass, it resolves to a wave record whose folder name differs from the key by exact string comparison. `projected` is left unchanged. Alias rows matching `pending=1 AND sealed=0` are retired with no idle wait, generation-conditioned, in the same transaction mechanism as orphan retirement (`retire_orphan_pending_waves` with no minimum idle time). Telemetry is kept.
3. The same pass-level guards apply: nothing is retired when discovery finds no wave directories, when any resolved candidate reports unreadable siblings, or when resolution raises. Retirement runs only after the projection loop completes.
4. The hard-boundary result lists retired aliases in a new `retired_alias_waves` list, present only when non-empty. The automatic background monitor never retires rows.
5. Behavior is the same on Windows, macOS, Linux and WSL2 and under the downstream Set/Wave vocabulary profile: the change uses existing resolution and store write paths only.

## Scope

**Problem statement:** reopening by short id attributes telemetry to an alias key, and alias rows never clear.

**In scope:**

- The canonical-id resolution in the `wf_reopen_wave` tool wrapper.
- Alias detection in `_retire_orphan_waves` (`wf_server/context_efficiency_handlers.py`) and a minimum-idle argument use of `retire_orphan_pending_waves`.
- Tests in `tests/test_server_context_efficiency.py`, and the pinned handler digest refresh in `tests/fixtures/register-surface-handler-digests.json`.
- A CHANGELOG bullet.

**Out of scope:**

- Merging alias telemetry into canonical rows or records.
- Changing `wf_reopen_wave`'s response shape.
- Other focus paths: the lifecycle path already focuses only on a resolved target.

## Acceptance Criteria

- [x] AC-1: A test reopens a closed wave by its five-character id and shows that focus is set on the wave's full folder id and that the folder-id row's `sealed` flag is cleared; a tool call recorded afterwards lands on the folder-id row and creates no short-id row. Without the change focus is on the short id and the folder-id row stays sealed. A second test shows that when the record cannot be resolved after the reopen, focus does not move and `focus_stage_not_applied` is reported.
- [x] AC-2: A test with a real store and no orphan rows shows that a hard-boundary pass retires a pending short-id alias row of an existing wave regardless of its age: it leaves the pending census, its events remain keyed by the alias, and it is listed in `retired_alias_waves`, while the canonical wave's own row is not retired. Without the change the alias row stays pending.
- [x] AC-3: Tests show that nothing is retired as an alias, and `retired_alias_waves` is absent, when a wave record is unreadable, when resolution raises, or on the automatic path; each fixture also shows the same alias row does retire in an unguarded hard-boundary pass (positive control), so the test fails if the retirement never runs.
- [x] AC-4: On a scratch copy of this repository's store and `docs/waves` tree, with `now` fixed at 2026-10-26T00:00:00Z, one hard-boundary pass lists exactly the 22 short-id rows in `retired_alias_waves`, retires no row whose key is an existing wave's folder name, and reports the wave-21s1u orphan retirements separately in `retired_orphan_waves`; pending goes from 27 to 1 (`20np3 worker-startup-diagnostics`). The counts are recorded in the Progress Log.
- [x] AC-5: The change's own suites and every test it adds pass, including under `run_tests.py --profile second`; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Resolve the canonical folder id in the `wf_reopen_wave` wrapper for unseal and focus.
- [x] Add alias detection and retirement to `_retire_orphan_waves`, reporting `retired_alias_waves`.
- [x] Add the AC-1 to AC-3 tests.
- [x] Run the AC-4 scratch measurement and the second-profile run, and record them.
- [x] Refresh the pinned handler digest for the edited `wf_reopen_wave` tool handler.
- [x] CHANGELOG bullet.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| alias-fix | implementer | — | reopen wrapper, retirement helper, tests |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_server/context_efficiency_handlers.py`, `.wavefoundry/framework/scripts/context_efficiency.py`, `.wavefoundry/framework/scripts/tests/test_server_context_efficiency.py`, `.wavefoundry/framework/scripts/tests/fixtures/register-surface-handler-digests.json`
- The root CHANGELOG gains one bullet.

## Affected Architecture Docs

N/A: the change corrects which id an existing tool passes to existing primitives and extends an existing hard-boundary retirement step; no boundary, data flow or verification seam changes.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The root cause |
| AC-2 | required | Clears existing aliases |
| AC-3 | required | Guards against retiring on unreliable resolution |
| AC-4 | required | Shows the outcome on the real data |
| AC-5 | required | Change-local verification, including the downstream profile |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-26 | Planned after wave 21s1u named the alias class as a follow-up; operator asked for the fix | Store query: 22 short-id rows, each starting with `wf_reopen_wave`; 21 canonical waves closed, 1 paused |
| 2026-10-26 | Readiness repair pass from all four reviewers: aliases arrive in `projected`, so retirement runs on every completed hard-boundary pass and checks projected keys; exact-string alias test; reopen resolves with `_find_wave_md` inside the existing `try` with an unresolvable branch tested; AC-3 positive controls and absent-list assertions; AC-4 reworded with separate orphan accounting and 27 -> 1; producer census recorded | Reviewer reports |
| 2026-10-26 | Implemented: the `wf_reopen_wave` wrapper resolves `_find_wave_md` inside its existing `try` and uses `parent.name` for unseal and focus (unresolved raises inside the `try`, so `focus_stage_not_applied` applies); `_retire_orphan_waves` now takes `alias_candidates=projected`, runs on every completed hard-boundary pass, returns `(orphans, aliases)`, skips keys equal to a discovered folder name before per-key resolution, and makes two `retire_orphan_pending_waves` calls (30-day orphans, zero-idle aliases), so two transactions; handler-digest pin refreshed for `wf_reopen_wave` only | tests `test_reopen_by_short_id_focuses_and_unseals_the_folder_id`, `test_reopen_leaves_focus_when_the_record_is_not_resolved`, `test_hard_boundary_retires_a_short_id_alias_row`, `test_alias_retirement_guards_with_positive_controls`; context-efficiency, census and registry suites OK |
| 2026-10-26 | Known-bad on scratch copies: the old reopen id, the old call condition, no alias detection, a prefilter that skips everything, and focusing an unresolved record each fail at least one new test | scratch copy, `python3 -m unittest` |
| 2026-10-26 | AC-4 on a scratch copy of the store and `docs/waves`, `now` = 2026-10-26T00:00Z: pending 27 -> 1 (`20np3`); `retired_alias_waves` lists exactly the 22 short ids; `retired_orphan_waves` lists the four wave-21s1u orphans; no folder-name key retired (none were pending, so that clause is vacuous on today's data); pass ok in 10.6 s | ad hoc run on the session scratch copy |
| 2026-10-26 | Downstream Set/Wave profile: `run_tests.py --profile second` over the context-efficiency and registry suites, 0 of 2 files failed | second-profile run |
| 2026-10-26 | Full suite: 12244 tests OK. Delivery finding 21S8V-DEL-UNREADABLE-ALIAS-VACUOUS (qa-reviewer, do_now): the AC-3 unreadable subtest stubbed no match, so the guard-removed mutant survived. Stub now keeps the real resolution and adds an unreadable sibling; the mutant now fails it. The unresolved-reopen test now starts with focus on another wave and asserts it is unchanged (code-reviewer note) | scratch mutant run; context-efficiency suite 136 OK |
| 2026-10-26 | Final full suite after the repair: 12244 tests OK, receipt written; docs validate clean | `run_tests.py`, 564 s |
| 2026-10-26 | Gapfill: mutant, AC-4 and pin-refresh runs used shell scripts, as executed probes and a mechanical fixture edit | — |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-26 | Fix the reopen wrapper to use the canonical folder id, and retire existing alias rows at the hard boundary with no idle wait, keeping telemetry. Efficacy: replaying today's data, all 22 alias rows retire at the next reload or upgrade and no new ones are created by reopen; it controls the outcome directly; it could wrongly retire a row only if a key that differs from its wave's folder name could still publish, which projection never does because it publishes under the folder name; success is AC-1 and AC-4 | Fixes the producer and clears the backlog with the mechanism wave 21s1u already reviewed | (a) Merge alias telemetry into canonical rows: rewrites closed waves' accounting and needs phase-ordinal re-keying. (d) Retire inside the projection loop when the published canonical differs from the key: avoids a second resolution pass but bypasses the pass-level unreadable and empty-discovery guards. (b) Retire aliases only after 30 idle days: no benefit, since an alias key can never publish. (c) Fix reopen only: leaves the 22 existing rows pending forever |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Alias telemetry for the paused wave `21fgr` (two reopen events) never reaches its record | Accepted: small, and the events stay in the store |
| A session still focused on an alias from before the fix keeps writing to it | The next reload or upgrade retires it again; restarted servers use the fixed reopen |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
