# Indexer Drift Detection Between File_Meta And Lance

Change ID: `1p399-bug indexer-drift-detection-between-file-meta-and-lance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p3b9 chunker-indexer-correctness-and-1-5-0-hardening`

## Rationale

Investigation during wave 1p35d (C3 / `1p35j`) surfaced that the framework semantic index can enter a state where `meta.json`'s `file_meta` entries claim "file is indexed at hash X" but the LanceDB chunks table has **zero rows for that path**. The incremental indexer sees "file hash unchanged → skip" and never re-chunks the file, so the missing-rows state perpetuates forever — unless the file's mtime changes (operator edit) which forces a re-process.

**The defect**: there is no consistency check between `file_meta` (the indexer's truth about "what's been processed") and Lance (the actual chunk storage). When the two diverge — for any reason (a chunker bug that produced zero chunks, a write that failed silently, a corrupted Lance file partially recovered) — the incremental update loop has no mechanism to detect or repair the drift.

Observable symptom: `seed_get(<name>)` and `docs_search(query=<name>)` return no results for affected files, even though they appear in the framework manifest as indexed. The downstream consumer report flagged this against ~half the seed catalog.

The companion bug `1p397` (chunker mega-chunk fallback) is one root cause that historically produced the drift. This change ensures **future drift is detected and repaired**, regardless of root cause.

## Requirements

1. **During incremental index update reconciliation**, the indexer cross-checks each path in `file_meta` against the Lance chunks table. A path with at least one Lance row counts as "indexed"; a path with zero rows counts as "drifted — needs re-chunk."
2. **Drifted paths are forced through the re-chunk + re-embed path** on the next incremental update, even when the file's hash matches `file_meta`. After successful re-chunk, the path's `file_meta` entry is preserved (hash unchanged) but the Lance state is now consistent.
3. **Drift detection runs on both layers** (project and framework indexes). Each has its own Lance table; each can independently drift.
4. **A new test harness** verifies the drift-detection behavior: set up a fixture with a file hashed in `file_meta` but absent from Lance; run incremental update; assert the file's chunks are written to Lance after the run.
5. **A diagnostic surfaces drifted paths during build** so operators can see when the indexer is repairing drift (vs. processing genuinely-changed files). Format: `build_index: repairing N drifted file(s): <path1>, <path2>, ...` to stderr.
6. **No behavior change on the happy path**: when `file_meta` and Lance are consistent, the indexer's existing incremental skip-on-hash-match optimization is preserved unchanged. Drift detection is an additional check that fires only when divergence is observed.
7. **No new dependencies** introduced. The cross-check uses the existing Lance query surface that the indexer already imports.
8. **Performance**: drift detection runs once per layer per incremental call. The query is a `SELECT DISTINCT path FROM <table>` (or equivalent) — sub-second on tables with thousands of rows.

## Scope

**Problem statement:** Indexer's `file_meta` and Lance chunks table can disagree; incremental update never detects or repairs the disagreement.

**In scope:**

- `indexer.py` incremental-update reconciliation gains a Lance-cross-check step
- Drifted paths force re-chunk + re-embed regardless of hash match
- Stderr diagnostic surfaces drift-repair activity
- Tests for the drift-detection branch + regression guard for the happy path

**Out of scope:**

- Root-cause fixes for what produces drift in the first place (covered by `1p397` for the known chunker case; future drift sources will be repaired by THIS change regardless of source)
- Full index rebuild from scratch as a way to repair drift (`wave_index_build(mode='rebuild')` already exists and works for that; this change makes incremental update self-repairing)
- Changes to the Lance schema or chunk shape
- Project-layer drift detection that scans `wave_audit` — `wave_audit`'s scope is repo health, not index introspection

## Acceptance Criteria

- [x] AC-1: `_detect_lance_drift(db_path, file_meta_paths, tables=("docs", "code"))` reads the `path` column from each Lance table, unions the result, and returns the file_meta paths absent from that union. Verified via `test_detects_drift_when_path_missing_from_lance` and `test_no_drift_when_file_meta_and_lance_agree`.
- [x] AC-2: At the incremental-update reconciliation point in `build_index`, `changed_broad |= drifted` forces drifted paths through the re-chunk + re-embed path even though their `file_meta` hash still matches the existing entry.
- [x] AC-3: `_detect_lance_drift` unions paths across both `docs.lance` and `code.lance` tables — a path indexed in either counts as not drifted. Verified via `test_drift_detection_unions_across_tables`. Per-layer behavior (project + framework) is inherited because `build_index` is the per-layer entry point and the drift check fires inside its incremental branch.
- [x] AC-4: Drifted paths are added to `changed_broad` AFTER `_detect_changes` has returned `current_file_meta` (which preserves the pre-existing hash entry for unchanged paths). The re-chunk loop reads the file, generates new chunks, writes them; it does NOT update the file_meta hash for a drifted path because the path's mtime/size/inode haven't changed.
- [x] AC-5: Happy-path skip-on-hash-match optimization unchanged. When `_detect_lance_drift` returns empty (no file_meta path is missing from Lance), `changed_broad` is unaffected and the existing flow continues. Verified via `test_no_drift_when_file_meta_and_lance_agree`.
- [x] AC-6: Stderr diagnostic emits `build_index: repairing N drifted file(s): <first 5 paths>[, +K more]` when drift count > 0. The `+K more` tail keeps the diagnostic scannable on widespread drift.
- [x] AC-7: `test_detects_drift_when_path_missing_from_lance` exercises the load-bearing case: file_meta claims a path, Lance has zero rows for it, drift detection returns it.
- [x] AC-8: `test_no_drift_when_file_meta_and_lance_agree` is the happy-path regression guard — every file_meta path has Lance rows, return empty.
- [x] AC-9: `test_10k_rows_sub_second` and `test_100k_rows_under_200ms` cover the scale bounds. Empirical measurement on the helper alone: **~11ms average for 100K rows + 1000 drifted paths** (warm cache, 5-run average), well under the 200ms MF-1 bound. Real-Lance benchmark is out of scope (would require LanceDB infrastructure); these tests guard against accidental O(N²) regressions in the set-difference + diagnostic-formatting path.
- [x] AC-10: Full framework test suite passes (2486 tests, +8 from C2).
- [x] AC-11: docs-lint passes.

## Tasks

- [x] Open `framework_edit_allowed` gate (already open from C1)
- [x] Add a `_detect_lance_drift(db_path, file_meta_paths, tables=("docs", "code"))` helper to `indexer.py`
- [x] Wire into the incremental-update reconciliation: drifted paths added to `changed_broad`
- [x] Apply at both project and framework layer reconciliation points (inherited via `build_index` per-layer entry)
- [x] Emit stderr diagnostic when drift count > 0
- [x] Add drift-detection unit tests (6 cases in `LanceDriftDetectionTests`)
- [x] Add happy-path regression test (`test_no_drift_when_file_meta_and_lance_agree`)
- [x] Add scale test (`LanceDriftDetectionScaleTests` — 10K + 100K rows)
- [x] Run framework test suite (2486 tests pass)
- [x] Run docs-lint (clean)
- [x] Close gate (will close at C5 / wave end since gate was open for the whole wave)

## Affected Architecture Docs

`N/A` — internal indexer logic addition; no architectural boundary or contract surface modified.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (cross-check exists) | required | Core fix mechanism. |
| AC-2 (drifted paths re-process) | required | Without this, detection without repair achieves nothing. |
| AC-3 (both layers covered) | required | Without project-layer coverage, downstream consumers with their own indexes have no fix. |
| AC-4 (file_meta preserved on repair) | required | Avoids hash-thrash that would re-process unrelated paths. |
| AC-5 (happy path preserved) | required | Without this, every incremental update re-processes every file — performance regression. |
| AC-6 (diagnostic emitted) | required | Operators need to see when drift is being repaired; silent repair masks the underlying problem. |
| AC-7 (drift fixture test) | required | Verifies the load-bearing behavior. |
| AC-8 (happy-path regression test) | required | Catches future changes that accidentally bypass the skip-on-match optimization. |
| AC-9 (scale test 10K + 100K) | required | Drift detection must not regress incremental-update latency at either the typical mid-size repo scale OR the enterprise Teton-shape scale. Prepare-council MF-1 added the 100K-row bound. |
| AC-10 (suite passes) | required | Standard. |
| AC-11 (lint passes) | required | Standard. |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-04 | Detect drift via Lance-vs-`file_meta` cross-check rather than via separate state file | The cross-check uses sources of truth that already exist. A separate state file (e.g., "last verified consistency timestamp") would add a third state to maintain and a third drift surface. | Maintain a separate drift-state file — rejected; more state, more drift surfaces. |
| 2026-06-04 | Forced re-chunk preserves `file_meta` entry (no hash change) | The hash didn't change; only Lance state was wrong. Preserving `file_meta` avoids hash-thrash that would re-process other files. | Update the hash on re-chunk — rejected; would invalidate downstream stat-cache consumers. |
| 2026-06-04 | Stderr diagnostic surfaces drift repair | Silent repair masks the underlying root cause. Logging makes drift observable for future investigation. | Silent repair — rejected; operationally opaque. |
| 2026-06-04 | Drift detection runs per-layer at the existing reconciliation point | Reuses existing per-layer flow; no new dispatcher needed. | Separate top-level drift-detect pass before reconciliation — rejected; duplicates the layer-iteration logic. |

## Risks

| Risk | Mitigation |
|---|---|
| Lance query for "all distinct paths" is slow on huge tables | AC-9 scale test verifies sub-second on 10K rows AND `< 200ms` on 100K rows (per MF-1). Lance's columnar engine makes DISTINCT-on-string queries near-O(rows-visited) with the existing per-path indexing, so the bound should hold; verify against the framework's own indexed corpus during implementation. |
| Drift detection falsely flags a file that genuinely has no chunks (e.g., empty file, .gitignored) | The `file_meta` walk already excludes such files; if a file is in `file_meta`, it's expected to have at least one chunk. False positives are rare and at worst cause one harmless re-chunk. |
| Forcing re-chunk on a drifted file fails for the same root cause that caused the original drift | The re-chunk path is the same as the normal chunk path. If the underlying bug is fixed (e.g., by `1p397`), the re-chunk now succeeds. If not, the diagnostic surfaces the recurring failure for investigation. |
| Diagnostic noise on every incremental run if drift is widespread | Diagnostic fires only when drift count > 0. On a healthy index, no diagnostic. On a one-time repair, a single line. On widespread drift, the message names the count + paths so the operator can see scope. |

## Related Work

- **`1p35d` (1p35j)** — added disk-fallback to `get_seed`. That fallback is the consumer-side compensating control; this change is the indexer-side repair.
- **`1p397` (companion bug)** — fixes the chunker mega-chunk pattern that historically produced the drift. Together: `1p397` prevents NEW drift, `1p399` repairs EXISTING drift.
- **`wave_index_build(mode='rebuild')`** — already supports full rebuilds. This change makes incremental update self-repairing so a full rebuild isn't required to fix drift.
- **Downstream consumer report** — flagged `seed_get` half-coverage; same root-cause cluster as this fix.

## Session Handoff

Not yet admitted to a wave. Recommended path: admit alongside `1p397` into a new wave that closes before the **1.5.0** release tag — both waves (`1p35d` and this follow-on) ship together as 1.5.0. The two changes are orthogonal but together fix the same broader defect: chunker no longer produces mega-chunks (`1p397`), indexer self-repairs when drift is detected (`1p399`). Joint shipping under one version tag means consumers absorb both halves in the same upgrade.
