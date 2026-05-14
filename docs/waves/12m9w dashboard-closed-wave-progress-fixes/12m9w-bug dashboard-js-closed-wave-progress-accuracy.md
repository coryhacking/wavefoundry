# Dashboard JS: Progress Bar Accuracy for Closed/Completed Waves

Change ID: `12m9w-bug dashboard-js-closed-wave-progress-accuracy`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12m9w dashboard-closed-wave-progress-fixes`

## Rationale

Three client-side bugs in `dashboard.js` caused the Waves, Changes, and ACs progress bars to show incorrect counts when closed or completed waves were present. The Waves bar showed 2/3 instead of 3/3 when a "completed" wave existed. The Changes and ACs bars silently dropped staged plan docs whose `wave_id` referenced a closed wave — they appeared in neither the done nor total counts. The `pendingChanges` scope included staged plans from closed/completed waves unconditionally, inflating the tile's pending count vs. the bar.

## Requirements

1. The Waves progress bar must count both "closed" and "completed" waves as done.
2. Staged plan docs in `progressChanges` whose `wave_id` is in a closed/completed wave must be counted as done in Changes, Tasks, and ACs — not silently dropped.
3. `pendingChanges` must exclude staged plan docs whose `wave_id` references an active, closed, or completed wave so the tile and bar agree.

## Scope

**Problem statement:** Three distinct counting bugs in `ProgressCard` and `Dashboard` in `dashboard.js`.

**In scope:**

- `closedWaves` filter extended to include `waveStatus(w) === "completed"` (line 325).
- `closedWaveIds` extended to include "completed" waves (line 327).
- `closedWaveProgressChanges` introduced to count closed-wave staged plan docs as done for Changes, Tasks, and ACs (lines 329–341).
- `openOrClosedIds` extended to include "completed" (line 1118).
- `staged` filter in `pendingChanges` restricted to `!openOrClosedIds.has(c.wave_id)` (line 1125).

**Out of scope:**

- Server-side (Python) metric fixes — covered in the companion change.

## Acceptance Criteria

- AC-1: Waves bar shows 3/3 when one wave has status "completed".
- AC-2: Changes bar total includes staged plan docs from closed waves (counted as done).
- AC-3: ACs bar total includes ACs from staged plan docs in closed waves (counted as done).
- AC-4: Tile pending count for Changes matches bar pending count for the `1n3dq` plan doc scenario.

## Tasks

- [x] Extend `closedWaves` filter to include "completed".
- [x] Introduce `closedWaveProgressChanges` and credit to Changes/Tasks/ACs as done.
- [x] Extend `openOrClosedIds` to include "completed"; filter staged docs against it.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| js-fixes   | implementer | — | Three targeted edits to dashboard.js |

## Serialization Points

- N/A

## Affected Architecture Docs

N/A — confined to dashboard client-side rendering logic; no boundary, flow, or test topology changes.

## AC Priority

| AC   | Priority  | Rationale |
|------|-----------|-----------|
| AC-1 | required  | Waves bar directly visible to all users |
| AC-2 | required  | Changes bar accuracy — core dashboard correctness |
| AC-3 | required  | ACs bar accuracy — core dashboard correctness |
| AC-4 | required  | Tile/bar agreement eliminates user confusion |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | All three JS fixes applied; 1161 tests pass; verified in 14b–14d packages | `python3 run_tests.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Extend `openOrClosedIds` rather than a separate `closedIds` set | Reuses existing set; keeps filter logic co-located | Separate set — more explicit but redundant |

## Risks

| Risk | Mitigation |
|------|------------|
| Double-counting if admitted in-wave changes also appear in staged | In-wave changes are excluded from `pendingChanges` by `openOrClosedIds`; staged and in-wave are disjoint |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
