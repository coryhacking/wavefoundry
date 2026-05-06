# Index Build Stats Persistence

Change ID: `12ec1-enh index-build-stats-persistence`
Change Status: `done`
Owner: Engineering
Status: done
Last verified: 2026-05-06
Wave: TBD

## Rationale

After a background index rebuild, the operator or agent has no way to estimate how long the next rebuild will take. Build duration varies significantly by repository size. Persisting stats from completed builds allows the next `wave_index_build` call to include a timing estimate in its `notice`, and `wave_index_build_status` to surface the estimate while a build is in progress.

## Requirements

1. After a background build completes, persist stats to `.wavefoundry/index/index-build-stats.json` (project layer) or `.wavefoundry/framework/index/index-build-stats.json` (framework layer). Stats include: `elapsed_seconds`, `files_indexed`, `doc_chunks`, `code_chunks`, `built_at` (ISO timestamp), `content`, `mode`.
2. Stats are written by `run_index_rebuild` when it detects a completed previous build before spawning the next one — parsed from the existing log using the `"done —"` completion line and the state file's `started_at`.
3. `wave_index_build` `notice` must include a timing estimate when previous stats are available: e.g., "Last build took ~7 minutes for 386 files — expect similar."
4. `wave_index_build_status` must include `previous_stats` (the persisted stats object) in its response when available.
5. Stats are best-effort — missing or unparseable stats must never block a build or cause an error.

## Scope

**Problem statement:** No timing history means no estimate for how long a rebuild will take.

**In scope:**

- `index-build-stats.json` written by `run_index_rebuild` before spawning
- Timing estimate included in `wave_index_build` `notice`
- `previous_stats` field in `wave_index_build_status` response
- Helper: `_read_index_build_stats(root, layer)` → dict or None
- Helper: `_write_index_build_stats(root, layer, stats)` → None

**Out of scope:**

- Build history beyond the most recent completed build (one record only)
- Stats written by the indexer script itself
- Surfacing stats on any call other than `wave_index_build` and `wave_index_build_status`

## Acceptance Criteria

- AC-1: After a build completes, `index-build-stats.json` exists in the index directory with `elapsed_seconds`, `files_indexed`, `doc_chunks`, `code_chunks`, `built_at`, `content`, `mode`.
- AC-2: A subsequent `wave_index_build` call includes a timing estimate in `notice` when stats are available.
- AC-3: `wave_index_build_status` response includes `previous_stats` when `index-build-stats.json` exists.
- AC-4: Missing or corrupt `index-build-stats.json` does not cause an error in any call path.
- AC-5: Stats are written for both `project` and `framework` layers.

## Tasks

- [x] Add `_index_build_stats_path(root, layer)` helper
- [x] Add `_read_index_build_stats(root, layer)` — returns dict or None, never raises
- [x] Add `_write_index_build_stats(root, layer, stats)` — never raises
- [x] In `run_index_rebuild`: before spawning, check if previous build log has completion marker; if so, compute stats and write to stats file
- [x] Update `run_index_rebuild` notice to include timing estimate when previous stats available
- [x] Update `wave_index_build_status_response` to include `previous_stats` in response
- [x] Add tests: stats written after completed build, notice includes estimate, status includes previous_stats, missing stats handled gracefully

## Agent Execution Graph

| Workstream  | Owner       | Depends On | Notes |
| ----------- | ----------- | ---------- | ----- |
| server impl | implementer | —          |       |
| tests       | implementer | server impl |      |

## Serialization Points

- `server.py` is the only file changed; no cross-workstream coordination needed.

## Affected Architecture Docs

N/A — confined to MCP tool surface and local index directory; no boundary or data-flow impact.

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Stats file is the core deliverable |
| AC-2 | required  | Timing estimate in notice is the operator-facing benefit |
| AC-3 | important | previous_stats in status response enables polling with context |
| AC-4 | required  | Missing stats must never break anything |
| AC-5 | important | Framework layer parity |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-06 | Write stats in `run_index_rebuild` before spawn, not in the indexer script | Keeps indexer script independent; server already has the log and state file at that point | Write stats in indexer.py at completion |
| 2026-05-06 | One record only (most recent build) | Simple; history beyond one build not needed for estimate | Rolling history file |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Stats from a partial/crashed build are misleading | Stats only written when log contains the `"done —"` completion marker |
| Log or state file absent on first run | `_read_index_build_stats` returns None; notice omits estimate gracefully |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
