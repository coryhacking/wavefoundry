# Report index size (total + per-component) in wave_index_health

Change ID: `1p9a9-enh index-size-in-health`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p99p expose-index-build-lock-status`

## Rationale

`wave_index_health` reports readiness, file/chunk counts, and graph node/edge counts, but not the
**on-disk size** of the index. Size is the signal that makes LanceDB bloat diagnosable at a glance (the
1p95j work chased a docs table that ballooned from ~43 MB of useful data to 400 MB+ of stale FTS
artifacts). Surface a `size` object on `wave_index_health` — a total plus a per-component breakdown —
so an operator/agent can see index growth without shelling out to `du`.

## Requirements

1. `wave_index_health` returns a `size` object for the project index: `total_bytes` (int) + a
   `components` map of the top-level entries under `.wavefoundry/index/` (e.g. `docs.lance`, `code.lance`,
   `graph`, `__manifest`, `meta.json`) to their byte size. Include a human-readable `total_human`.
2. Computed by summing `st_size` over the index dir (read-only; off the search hot path). Missing dir
   or any stat error degrades gracefully — `size` is `null`/omitted, never an exception.
3. Additive/backward-compatible — a new field on `wave_index_health`; no new tool, no signature change,
   no reconnect. Documented in `docs/specs/mcp-tool-surface.md`.

## Scope

**In scope:** `server_impl.wave_index_health_response` — a `_index_dir_size(index_dir)` helper + the
`size` object; `mcp-tool-surface.md` note; a test.

**Out of scope:** mirroring size into `wave_index_build_status` (health is the inventory home); a size
budget / alert threshold (report-only); per-table internal breakdown (`_indices`, `_versions`) beyond
the top-level entries.

## Acceptance Criteria

- [x] AC-1: `wave_index_health` includes `size` = `{total_bytes, total_human, components: {name: bytes}}`
      for the project index. Evidence: `IndexSizeHealthTests.test_index_dir_size_total_and_components`,
      `test_health_includes_size`; live call shows `docs.lance`/`code.lance`/`graph` breakdown.
- [x] AC-2: computed by summing on-disk file sizes; a missing/unreadable index dir yields `size: null`
      and never raises. Evidence: `test_index_dir_size_missing_returns_none` (+ best-effort `os.walk`/stat).
- [x] AC-3: additive/backward-compatible; documented in `mcp-tool-surface.md` + the tool docstring;
      `run_tests.py` (3,805) + `wave_validate` pass. Evidence: suite + docs gate + diffs.

## Tasks

- [x] Added `_index_dir_size(index_dir)` + `_path_size_bytes`/`_human_bytes` in `server_impl.py`;
      attached `size` to `wave_index_health_response`. Done.
- [x] Documented the `size` field in `docs/specs/mcp-tool-surface.md` + the `wave_index_health` docstring. Done.
- [x] Tests (`IndexSizeHealthTests`, 4); `run_tests.py` 3,805 OK + `wave_validate` ok. Done.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single small lane in `server_impl.wave_index_health_response` + spec + test. |

## Serialization Points

- Touches `wave_index_health_response`, adjacent to `1p99o`'s `lock` addition in the same function —
  additive, disjoint keys (`size` vs `lock`); no conflict.

## Affected Architecture Docs

N/A — additive observability field; no boundary/flow change.

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The feature — index size visible in health. |
| AC-2 | required   | Must never break the health call; graceful on error. |
| AC-3 | required   | Backward-compatible, documented, no regression. |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-07-01 | Planned (operator: "add index size to the status"). New change admitted into the existing wave `1p99p` (not a new wave); ships in 1.10.0. Home = `wave_index_health` (inventory metric), not `wave_index_build_status`. | operator request; `1p95j` bloat context. |
| 2026-07-01 | Implemented. `_index_dir_size`/`_path_size_bytes`/`_human_bytes` + `health["size"]`; spec + docstring; 4 tests; prepare-council PASS. **The feature immediately caught a real bloat**: a live call showed `docs.lance` at **1.68 GB** (working index re-bloated by this session's post-edit-hook rebuilds — the exact 1p95j FTS-artifact accumulation) — flagged to the operator; a fresh rebuild reclaims it. AC-1..3 met. | `server_impl.py` diff; `IndexSizeHealthTests` (4); 3,805 tests OK; docs-lint ok; live `_index_dir_size` output. |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-07-01 | Put `size` on `wave_index_health`, not `wave_index_build_status`. | Size is an inventory/health metric; build-status is "is a build running / lock held". | Mirror into build-status (deferred — health is the home). |
| 2026-07-01 | Report total + top-level component breakdown. | The per-component split (docs.lance vs code.lance vs graph) is what makes bloat diagnosable. | Total only (rejected — hides which table grew). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Walking the index dir adds latency to health. | A few hundred `stat()`s over the index dir; health is a diagnostic tool, not the hot path. |
| Stat errors on an odd filesystem break the health call. | AC-2: sum is best-effort; any error yields `size: null`, never raises. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
