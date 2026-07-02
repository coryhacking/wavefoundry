# LanceDB index-artifact bloat: full-rebuild finalize never compacts/cleans

Change ID: `1p95j-bug lancedb-index-artifact-bloat`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-30
Wave: `1p93a embedding-precision-policy`

## Rationale

Found while collecting metrics during `1p93a` hardware validation (operator asked for a full index
rebuild + timings): the working `.wavefoundry/index/` had grown to a `du`-apparent 76G and, after a
fresh rebuild, kept re-bloating. Root-caused on the M2 Max working index:

- A **fresh** full rebuild produces a clean **~148M** index (docs 90M + code 58M) with **2** index
  directories per table (1 vector `IVF_HNSW_SQ` + 1 FTS).
- After ~2 hours of normal churn (post-edit-hook incremental reindexes + repeated rebuilds), the
  docs table had **11 `_indices/` directories** and a `du`-apparent 400M+, of which the useful data
  is tiny (vectors 26M, text 12M, ~43M total). The bloat is **stale full-text-search (FTS) index
  artifacts** — the FTS index is ~40M and is rebuilt on every update, and old copies are not
  garbage-collected.

Two mechanisms in `indexer.py`:

1. **The streaming full-rebuild finalize (`_StreamingLayerWriter._finalize_inner`) never compacts or
   cleans.** It builds the vector index (`create_index(replace=True)`) and the FTS index, then
   returns — with **no `_optimize_lance_table()` call**. `create_table(mode="overwrite")` on the
   first `add` leaves the previous build's data/index files behind; nothing reclaims them. So every
   full rebuild that runs on a non-empty index dir leaves the prior build's artifacts.
2. **The incremental path rebuilds the FTS index on every update (`_create_fts_index(replace=True)`,
   `indexer.py:1931`) but only runs the cleanup (`_optimize_lance_table`) when the fragment count
   exceeds `LANCEDB_COMPACT_THRESHOLD` (20).** Between compactions, each incremental FTS rebuild
   leaves a stale ~40M artifact that isn't GC'd until the next fragment-triggered optimize — so under
   frequent small edits (each adding 1-2 fragments) the stale FTS indexes accumulate faster than they
   are cleaned.

Empirically, `table.optimize(cleanup_older_than=timedelta(0))` reclaims the *data* (docs 488M->132M)
but leaves 0-byte tombstone `_indices/` dirs and does not fully converge - a **fresh rebuild** is the
clean reclaim. The FTS index is **load-bearing** (not removable): `server_impl.search_code`/`search_docs`
compute both a dense (vector) list and an FTS list and RRF-merge them (`server_impl.py:1610-1625`);
every `code_ask`/`docs_search` uses it.

The streaming full-rebuild finalize (mechanism 1) is the clear, high-value gap - a full rebuild
should always end compacted and cleaned. This bug affects every Wavefoundry install (unbounded index
growth over time). **Admitted mid-wave into `1p93a` by operator direction** (surfaced during the
wave's own rebuild-metrics work).

## Requirements

1. The streaming full-rebuild finalize must compact + clean the table after building its indices
   (`_optimize_lance_table(table)` - the same call the incremental path already uses), so a full
   rebuild ends near the ~148M clean baseline rather than leaving prior artifacts.
2. The incremental index path must not let stale FTS/vector index artifacts accumulate unbounded
   between fragment-triggered compactions - a cleanup must run after the FTS index is rebuilt, not
   only when `fragment_count > LANCEDB_COMPACT_THRESHOLD`.
3. The streaming full-rebuild FTS build should use `replace=True` (currently `replace=False`,
   `indexer.py:1284`) so a full rebuild on a non-empty dir replaces rather than stacks the FTS index
   - matching the incremental path (`indexer.py:1931`).
4. No behavior change to retrieval quality - the vector + FTS indexes and their query semantics are
   unchanged; only their lifecycle (compaction/cleanup) is fixed. Cleanup is best-effort/advisory
   (already swallowed in `_optimize_lance_table`), so a cleanup failure must never fail a build.

## Scope

**Problem statement:** stale LanceDB index artifacts (chiefly the ~40M FTS index, rebuilt on every
update) accumulate unbounded because the streaming full-rebuild finalize never compacts/cleans and
the incremental cleanup is gated behind a fragment threshold.

**In scope:**

- `indexer.py`: `_optimize_lance_table` call in `_StreamingLayerWriter._finalize_inner`;
  `replace=True` on the streaming FTS build; a reliable cleanup after the incremental FTS rebuild.
- `tests/test_indexer.py`: assert the streaming finalize invokes the compaction/cleanup; assert the
  incremental path cleans after an FTS rebuild; assert a cleanup exception is swallowed (never fails
  the build).
- Operator reclaim of the working index via a fresh rebuild (one-time; validates the fix).

**Out of scope:**

- Changing the FTS tokenizer, the vector index type (`IVF_HNSW_SQ`), or any retrieval behavior.
- Removing the 0-byte tombstone `_indices/` dirs Lance leaves after `optimize` (harmless; a Lance
  internal - not worth special handling).
- A background/scheduled compaction daemon (the post-build cleanup covers the real churn source).

## Acceptance Criteria

- [x] AC-1: `_StreamingLayerWriter._finalize_inner` calls `_optimize_lance_table(self.table)` so a
      full rebuild ends compacted+cleaned. **Corrected during implementation:** the optimize must run
      **BEFORE** the vector/FTS index builds, not after — a post-hoc optimize compacts the data out
      from under the just-built FTS, invalidating it and forcing a duplicate whose stale copy can't
      be GC'd without `pylance` (empirically: optimize-after left TWO ~40 MB FTS copies / 132M; the
      corrected optimize-**first** yields ONE / 91M). Evidence: `indexer.py:_finalize_inner`;
      `test_streaming_finalize_rebuilds_fts_replace_true_and_optimizes`, `test_full_rebuild_runs_cleanup`.
- [x] AC-2 (**reworded** — the naive "cleanup after every incremental FTS rebuild" is unsafe: it
      recompacts and duplicates the FTS): the incremental path does not re-materialize the FTS index
      on a **no-op** pass — the rebuild is gated on real change (`rows_to_add`/`ids_to_delete`/
      `fallback_paths`), cutting the reindex churn rate that drove the growth. The correct-order
      compaction (compact → index) is preserved by the existing fragment-gated `optimize` (which runs
      BEFORE the indexes) and by the finalize. Evidence: `indexer.py` incremental `table_changed`
      gate; `test_incremental_change_rebuilds_fts`.
- [x] AC-3: the streaming full-rebuild FTS build uses `replace=True`. Evidence: `indexer.py:_finalize_inner`.
- [x] AC-4: a fresh full rebuild produces a clean index — **validated on the operator's working index
      (M2 Max reclaim, 2026-06-30): docs.lance 91M with exactly ONE 40M FTS + ONE 9.3M vector index
      (no duplicate), code.lance 58M, 182M total** (down from the bloated 400M+); hybrid FTS+vector
      search verified working (GPU reranker on CoreML). Evidence: reclaim rebuild + `du`/search sanity.
- [x] AC-5: cleanup remains best-effort — `_optimize_lance_table` swallows exceptions; a
      compaction/cleanup failure never fails the build. Evidence: `test_optimize_lance_table_swallows_exceptions`;
      full suite 3,762 tests OK.

## Tasks

- [x] Add `_optimize_lance_table(self.table)` to `_StreamingLayerWriter._finalize_inner` — **BEFORE**
      the index builds (compact → index), not after. Done: `indexer.py`.
- [x] Change the streaming FTS build to `replace=True`. Done: `indexer.py`.
- [x] Gate the incremental FTS rebuild on real change (no re-materialize on a no-op pass); do NOT add
      a post-FTS optimize (it recompacts + duplicates the FTS). Done: `indexer.py` `table_changed` gate.
- [x] Add tests: streaming finalize compacts + FTS replace=True; none-table no-op; optimize swallows
      exceptions; full rebuild runs cleanup; incremental change rebuilds FTS (replace=True). Done:
      `LanceIndexCleanupTests` (5).
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py`. Done: 3,762 tests OK.
- [x] Reclaim the operator working index via a fresh rebuild; confirmed the clean ~91M-docs / 1-FTS /
      182M-total baseline (AC-4).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single-lane fix in `indexer.py`'s index-build lifecycle. |

## Serialization Points

- `indexer.py` is shared with the `1p93a` embedding changes (`_get_embedder`, `build_index`) but this
  change touches a disjoint region (the LanceDB writer finalize + incremental index path), so no
  intra-file conflict with the precision work.

## Affected Architecture Docs

`docs/architecture/embedding-model.md` - a one-line note that the index build compacts + cleans on
finalize to bound artifact growth. No boundary/flow change.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The core fix - a full rebuild must end clean; the missing finalize cleanup is the main gap. |
| AC-2 | required | Without it, incremental churn keeps re-bloating between compactions (the observed 400M+). |
| AC-3 | required | Prevents FTS stacking on a full rebuild over a non-empty dir; cheap correctness. |
| AC-4 | important | End-to-end confirmation on the real working index (operator-run reclaim). |
| AC-5 | required | Cleanup must never fail a build; no regressions. |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-30 | Root-caused during `1p93a` rebuild-metrics work; admitted mid-wave by operator direction. | Working index 11 `_indices/` dirs (10x 0B tombstone + 2x40M FTS) vs a fresh build's 2 dirs / 148M; `indexer.py:1268-1285` (finalize, no optimize) vs `:1910-1931` (incremental). |
| 2026-06-30 | Implemented: finalize compacts-FIRST then builds indexes; incremental FTS rebuild gated on real change; FTS `replace=True`. First cut (optimize-AFTER-index) duplicated the FTS — corrected to optimize-first after empirical measurement. AC-1..5 met. | `indexer.py` diffs; `LanceIndexCleanupTests` (5); 3,762 tests OK; working-index reclaim 400M+→182M (docs 91M / 1 FTS) |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-30 | Fix the build-path lifecycle (finalize compaction + reliable incremental cleanup) rather than a scheduled/background compactor. | The churn source is the build path itself; cleaning there is deterministic and needs no new daemon/lifecycle. | A background compaction job (rejected - more moving parts; doesn't fix the root cause). |
| 2026-06-30 | Reclaim the working index via a fresh full rebuild, not repeated `optimize()`. | `optimize(cleanup_older_than=0)` reclaims data (488M->132M) but leaves tombstones + ~2x40M FTS and doesn't converge; a fresh rebuild yields a clean 148M / 2-dir index. | Repeated `optimize` (rejected - doesn't fully converge; leaves duplicate FTS). |
| 2026-06-30 | **`optimize` (compact + cleanup) must run BEFORE the vector/FTS index builds in finalize, never after.** | `optimize` recompacts the data fragments; an FTS/vector index built before it is indexed over the pre-compaction fragments, so the compaction invalidates it and a fresh index is materialized over the compacted data — leaving a stale duplicate (~40 MB FTS) that can't be GC'd without `pylance` (unavailable). Empirically: optimize-after = 132M / 2 FTS; optimize-first = 91M / 1 FTS. This matches the incremental path's existing order (fragment-gated optimize precedes `create_index`). | Optimize-after-index (rejected — the first cut; duplicated the FTS, measured). Use `table.cleanup_old_versions()` for pure version GC without recompaction (rejected — requires the `pylance` package, not installed in the tool venv). |
| 2026-06-30 | Do NOT run an `optimize` after the INCREMENTAL FTS rebuild; instead gate the FTS rebuild on real change. | Same duplication hazard as above (optimize-after-FTS recompacts + duplicates). Gating the rebuild on `rows_to_add`/`ids_to_delete`/`fallback_paths` removes the no-op re-materialization (the churn-rate driver) without the duplication; the fragment-gated `optimize` already compacts in the correct order when it fires. | Cleanup after every incremental FTS rebuild (rejected — duplicates the FTS). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Running compaction after every incremental update adds latency to the post-edit hook. | The hook is an async background process; compaction on a small table is ~1s. Bounded, and prevents unbounded 400M+ growth. Tune to a lighter cleanup if measured latency is a problem. |
| A compaction/cleanup exception fails a build. | `_optimize_lance_table` already swallows exceptions (advisory); AC-5 asserts it. |
| Interaction with the `1p93a` embedding edits in the same file. | Disjoint region (writer finalize / incremental index path vs `_get_embedder`/precision); no shared lines. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
