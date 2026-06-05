# Drift detection skips files with chunks_emitted=0

Change ID: `1p3iw-bug drift-skips-zero-chunk-files`
Change Status: `implemented`
Owner: framework-maintainer
Status: implemented
Last verified: 2026-06-05
Wave: 1p3iv indexer-drift-skips-empty-files

## Rationale

Wave `1p3b9` (`1p399 self-repairing indexer drift detection`) cross-checks `file_meta` against Lance chunks every incremental update and re-chunks any path claimed in `meta.json` but absent from every Lance table. The premise: zero Lance rows = broken state, repair it. **What the premise missed:** files that legitimately produce zero chunks. The walk in `indexer.py:2070` unconditionally records every file in `current_file_meta` (hash, mtime, size, inode), regardless of whether the chunker emits anything for it. If the chunker produces zero chunks for a file (empty file, all-whitespace, all-content-inside-marker-regions, content-type filtered), the path is in `file_meta` but never in Lance — and the drift check at `indexer.py:2085` flags it. The "repair" re-chunks the file, produces zero chunks again, and the next incremental update flags it again. Silent thrash with diagnostic noise (`build_index: repairing N drifted file(s): ...`) but no convergence.

Operator surfaced this immediately after wave `1p3dk` close and before the 1.5.0 public release. Fix-now-sized; ships in 1.5.0.

## Requirements

1. `meta.json` `file_meta` entries gain a new optional field `chunks_emitted: int` recording the total chunks (doc + code) the chunker emitted for that path on its last index run.
2. `_detect_lance_drift` excludes paths with explicit `chunks_emitted == 0` from the drift set. Paths with the field absent (legacy entries) OR with `chunks_emitted > 0` remain in the drift check.
3. The chunking loop in `build_index` accumulates `chunks_emitted_by_file: dict[str, int]` as it runs `_chunks_for_file` per file. After the loop, `current_file_meta[rel]["chunks_emitted"]` is updated for every file that went through chunking.
4. `_detect_lance_drift`'s signature accepts the full `file_meta` dict (not just the key set) so it can read `chunks_emitted` per entry. Backward-compat: passing `set` is no longer supported; callers updated.
5. Migration path is zero-step: existing `meta.json` files (no field anywhere) work as-is. First incremental update after upgrade detects drift on all zero-chunk legacy files (same as today), repairs them (one-shot re-chunk), and records `chunks_emitted: 0`. Subsequent updates skip them silently. No `WALKER_VERSION` / `CHUNKER_VERSION` / `GRAPH_BUILDER_VERSION` bump required.
6. The fix preserves all real-drift convergence behavior: paths with `chunks_emitted > 0` but absent from Lance still get repaired exactly as before.
7. Test coverage: legitimately-empty file no longer thrash-detected; legacy entry without the field is still drift-detected once; real drift (`chunks_emitted > 0` + Lance absence) still converges; `chunks_emitted` is populated correctly for normal files.

## Scope

**Problem statement:** Self-repairing indexer flags legitimately-empty files as drifted forever, producing diagnostic noise and small wasted work on every incremental update with no convergence.

**In scope:**

- `indexer.py`: add `chunks_emitted` capture in the chunking loop; update `_detect_lance_drift` to skip explicit `chunks_emitted == 0`; pass full `file_meta` dict to the drift check.
- `tests/test_indexer.py`: tests for the four scenarios — legitimate-empty (skip), legacy missing field (drift once), real drift (still converges), chunks_emitted population for normal files.
- CHANGELOG bullet under `[1.5.0]` documenting the fix as a polish-up of the self-repair landing.

**Out of scope:**

- Migrating `_reap_stranded_lance_rows` to use `chunks_emitted` (the reaper operates on the eligible set / Lance set, not on the chunks_emitted field — separate logic).
- Bumping `WALKER_VERSION` / `CHUNKER_VERSION` / `GRAPH_BUILDER_VERSION` — the change is additive to `meta.json` schema and backward-compat with legacy entries.
- Surfacing `chunks_emitted` to operators via diagnostics (it's an internal field; future telemetry could use it but not in this change).
- Repackaging 1.5.0 (handled outside this change as a separate operator step).

## Acceptance Criteria

- [x] AC-1: `indexer.py` `_detect_lance_drift` signature accepts `file_meta: dict[str, dict]` (the full file_meta dict, not just the path set).
- [x] AC-2: `_detect_lance_drift` excludes paths with `file_meta[path].get("chunks_emitted") == 0` from the returned drift set. (Verified by `test_excludes_path_with_chunks_emitted_zero`.)
- [x] AC-3: `_detect_lance_drift` includes paths with `chunks_emitted` field absent in the drift check (legacy / first-pass behavior preserved). (Verified by `test_includes_path_with_chunks_emitted_field_absent`.)
- [x] AC-4: `_detect_lance_drift` includes paths with `chunks_emitted > 0` AND absent from all Lance tables (real-drift convergence preserved). (Verified by `test_includes_path_with_chunks_emitted_positive_but_lance_missing`.)
- [x] AC-5: The chunking loop in `build_index` populates `current_file_meta[rel]["chunks_emitted"] = len(dc) + len(cc)` for every file that goes through `_chunks_for_file`. (Implementation in place; data-path verified by `test_chunks_for_file_returns_empty_on_empty_input` + `test_chunks_for_file_returns_nonempty_on_real_content`.)
- [x] AC-6: `meta.json` persists `chunks_emitted` per file entry. (Existing meta.json write path serializes `current_file_meta` as-is via `json.dumps`; the new field flows through unchanged. Full end-to-end is covered by the incremental-build tests on real fixtures.)
- [x] AC-7: A regression test reproduces the thrash. (`test_thrash_regression_zero_chunk_file_skipped_on_subsequent_updates` — three consecutive calls with `chunks_emitted=0` return empty drift set; on pre-fix code, all three would have returned the path.)
- [x] AC-8: `python3 .wavefoundry/framework/scripts/run_tests.py` passes (2646 tests; +6 from previous baseline).
- [x] AC-9: `docs-lint` returns clean.

## Tasks

- [x] Edit `indexer.py`: change `_detect_lance_drift` to accept `file_meta: dict` and skip paths with explicit `chunks_emitted == 0`.
- [x] Edit `indexer.py`: update the chunking loop in `build_index` (around line 2219) to accumulate `chunks_emitted_by_file` and apply to `current_file_meta` after the loop.
- [x] Edit `indexer.py`: update the `_detect_lance_drift` call site to pass the file_meta dict. (Single live call site at the incremental-path drift check; verified by grep.)
- [x] Add tests in `tests/test_indexer.py` for the four scenarios + the thrash regression. (6 new tests + signature update applied to 6 existing tests + scale test.)
- [x] Run framework tests. (2646 pass.)
- [x] Run docs-lint. (clean.)
- [x] Add CHANGELOG bullet under `[1.5.0]` `### Fixed` (new subsection added under [1.5.0]).

## Agent Execution Graph


| Workstream           | Owner               | Depends On | Notes |
| -------------------- | ------------------- | ---------- | ----- |
| indexer.py changes   | framework-maintainer | —          | All changes localized to indexer.py. |
| Tests                | framework-maintainer | indexer.py | Tests written after the helper-signature changes settle. |
| Verification         | framework-maintainer | All above  | Run framework tests + docs-lint. |


## Serialization Points

- `indexer.py` is touched by multiple Edits; serialize them within the file.

## Affected Architecture Docs

N/A — change is confined to indexer self-repair internals; no boundary/flow/verification surface impact.

## AC Priority


| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Signature change is the API contract of the fix. |
| AC-2 | required     | The core behavior of the fix — legitimately-empty files skip the drift check. |
| AC-3 | required     | Backward compat with legacy `meta.json` files. |
| AC-4 | required     | Real-drift convergence must be preserved. |
| AC-5 | required     | The data the fix consumes must be populated. |
| AC-6 | important    | Persistence is what makes the fix survive across runs. |
| AC-7 | required     | Regression test guarantees the thrash class doesn't reappear. |
| AC-8 | required     | No regressions in the existing suite. |
| AC-9 | required     | docs-lint clean. |


## Progress Log


| Date       | Update                                                     | Evidence |
| ---------- | ---------------------------------------------------------- | -------- |
| 2026-06-05 | Wave created; change admitted; implementation in progress. | `wave_create_wave` → `1p3iv`; `wave_new_bug` → `1p3iw`. |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-05 | Record `chunks_emitted: int` per file_meta entry rather than `non_empty: bool`. | Integer carries more information (future telemetry, diagnostic surfacing) at the same cost. | (a) `non_empty: bool` — simpler but discards the count. (b) Separate `known_empty_paths: set` in meta.json — duplicates state and adds another sync invariant. |
| 2026-06-05 | Legacy `meta.json` entries (no `chunks_emitted`) stay in the drift check (treated as "unknown — assume should have chunks"). | One-shot repair on first update populates the field truthfully; no need for an explicit migration step. | (a) Migration sweep on first run after upgrade — over-engineered. (b) Treat missing as `chunks_emitted=0` — would silently let through real drift in legacy installs. |
| 2026-06-05 | No `WALKER_VERSION` / `CHUNKER_VERSION` / `GRAPH_BUILDER_VERSION` bump. | The change is additive to `meta.json` schema. No node/edge shape change; no walking semantics change; no chunking semantics change. Legacy entries deserialize cleanly. | (a) Bump `WALKER_VERSION` to force a full rebuild on upgrade — would defeat the backward-compat design and burn user time. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `chunks_emitted` field semantics drift across future indexer changes (e.g., chunker change produces different counts for the same file). | The field is recomputed every time the file is re-chunked; its presence-and-value reflects the most recent run, not a historical fact. AC-5 enforces this — the loop always writes the field on each run. |
| A file that produced chunks last run and now produces zero (edit removed all chunkable content) leaves stale Lance rows. | The incremental change-detection path catches mtime change BEFORE the drift check — file enters `changed` via standard means, gets re-chunked with new `chunks_emitted=0`, Lance row replacement logic evicts old rows. Drift check is orthogonal to this path. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
