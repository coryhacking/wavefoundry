# Replace numpy cosine scan with LanceDB embedded vector store

Change ID: `12nb2-enh hnsw-vector-index`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-15
Wave: 12nbr code-intelligence-expansion

## Rationale

The current vector search loads full embedding matrices (`.npy` files) into RAM and scans every row on every query — O(n) exact cosine similarity. This works at current corpus sizes but has no incremental update path, no deletion path, and grows linearly in both memory and query latency.

This change replaces the numpy cosine scan with **LanceDB** — an Apache 2.0 embedded vector database that runs in-process with no service dependency. LanceDB stores vectors and chunk metadata together in Lance columnar format, builds and manages HNSW indexes natively, supports true deletion via `table.delete()`, and uses memory-mapped files rather than loading the full matrix into RAM.

**Key simplifications over a raw hnswlib approach:**

- **True deletion** — `table.delete("path = 'src/foo.py'")` removes records permanently. No soft-delete tombstones, no rebuild threshold formula, no `mark_deleted` + counter tracking.
- **Unified storage** — vectors and chunk metadata live in one Lance table. The current multi-file layout (`docs.npy` + `docs.json` + `code.npy` + `code.json` + `meta.json`) collapses to two Lance tables per corpus layer.
- **Native filtering** — metadata predicates (`language`, `kind`, `tags`) push into the vector query rather than filtering results in Python post-search.
- **MVCC** — Lance uses multi-version concurrency control; partial writes cannot corrupt the table. The `_save_npy_atomic` temp-file-rename pattern is no longer needed.

LanceDB is Apache 2.0 licensed, runs fully embedded in-process, and handles 50K–100K+ chunks comfortably — query latency at that scale is 2–5ms with an HNSW index, versus 20–50ms for the numpy O(n) scan.

Query results are not meaningfully affected: LanceDB's HNSW index at `ef=200` approaches 100% exact recall on corpora of this size, and the cross-encoder reranker absorbs any marginal approximation error at the 40→7 compression ratio.

## Requirements

1. `lancedb` (Apache 2.0) is added to `setup_index.py`'s install step. It is an in-process library; no service or daemon is required.
2. `indexer.py` writes two Lance tables per corpus layer: `docs` and `code`. Each table stores all chunk fields (`path`, `text`, `language`, `kind`, `lines`, `tags`, etc.) plus a `vector` column of float32 arrays. The tables are written to `.wavefoundry/index/lancedb/` (project) and `.wavefoundry/framework/index/lancedb/` (framework).
3. The `.npy` and `.json` index files are no longer written for new builds. **On a full rebuild** (`setup_index.py`), after the Lance tables are successfully written and verified, `indexer.py` deletes any legacy `.npy` and `.json` files present in the same index directory. The LanceDB tables must be confirmed non-empty before deletion. Deletion is best-effort: a failure to remove legacy files is logged as a warning but does not fail the build.
4. `WaveIndex._ensure_loaded` opens the LanceDB tables when present. When only legacy `.npy` + `.json` files are present (user has not yet rebuilt), it falls back to the existing numpy load path and emits a one-time migration warning: `"[wavefoundry] Legacy .npy index detected — rebuild with setup_index.py to enable LanceDB."`.
5. **HNSW index:** after initial table population, `indexer.py` calls `table.create_index(metric="cosine", index_type="IVF_HNSW_SQ")` when the table exceeds `LANCEDB_INDEX_THRESHOLD = 1000` rows. Below that threshold, LanceDB performs an exact flat scan automatically — no explicit index needed for small corpora (e.g. the framework seed/doc index).
6. **Query:** `WaveIndex._hnsw_search` is replaced by `_lance_search(table, query_vec, top_n, where=None)`: calls `table.search(query_vec).metric("cosine").limit(top_n).where(where).to_list()`. Sets `nprobes` and `refine_factor` for recall tuning via named constants. Returns chunk dicts with `score` field.
7. **Native filtering:** the `kind`, `language`, and `tags` filters currently applied post-search in `search_docs` and `search_code` are pushed into the LanceDB `where` predicate at query time.
8. **Incremental addition:** `indexer.py`'s per-file update path calls `table.add(new_rows)` for new or changed chunks. LanceDB appends atomically via Lance's MVCC.
9. **Deletion:** when chunks are removed (file deleted, renamed, or changed), `indexer.py` calls `table.delete(f"path = '{file_path}'")`. This is a true delete — no tombstones, no rebuild threshold, no counter tracking. Lance's MVCC handles concurrent safety.
10. **MVCC cleanup lifecycle:** `table.delete()` writes a deletion vector masking rows from queries immediately, but the underlying data bytes remain on disk until compaction runs. The full cleanup is a single call:

    ```python
    table.optimize(cleanup_older_than=timedelta(seconds=0))
    ```

    `optimize()` (modelled after PostgreSQL `VACUUM`) combines: (1) compaction — merges fragments, rewrites data files excluding deleted rows, space reclaimed here; (2) version pruning — removes old manifest and delta files no longer referenced; (3) index optimization — folds new additions into the existing HNSW index without a full rebuild. `cleanup_older_than=timedelta(seconds=0)` must be passed explicitly — the default is 7 days, which would leave old version files accumulating between runs.

    `indexer.py` calls `table.optimize(cleanup_older_than=timedelta(seconds=0))` after add/delete operations when the fragment count exceeds `LANCEDB_COMPACT_THRESHOLD = 20`. This call is **synchronous and blocking** in the `indexer.py` subprocess — it does not affect query latency on the MCP server, which reads the updated version automatically via Lance's versioned manifest on its next query. Until `optimize()` runs, deleted rows occupy disk but are invisible to queries.
11. The project and framework corpus layers are each stored in separate LanceDB databases and opened independently. Merged search queries both and concatenates results before reranking — same logic as `_merge_layers` today.
12. `LANCEDB_INDEX_THRESHOLD = 1000`, `LANCEDB_COMPACT_THRESHOLD = 20`, `LANCEDB_NPROBES = 20`, `LANCEDB_REFINE_FACTOR = 10` are named constants in `indexer.py` and `server.py`. No magic numbers appear at LanceDB call sites.
13. No change to the embedding models, reranker, `VECTOR_TOP_K`, two-hop expansion, or any tool above `WaveIndex`. The swap is confined to the vector storage and retrieval layer.

## Scope

**Problem statement:** The numpy cosine scan is O(n), loads the full matrix into RAM, and has no incremental add or delete path. Any file change rewrites the entire matrix. There is no way to remove stale chunks from deleted or renamed files without a full rebuild.

**In scope:**

- `indexer.py`: add `lancedb` to install step; `_build_lance_tables(docs_chunks, docs_vecs, code_chunks, code_vecs, db_path)` for full build; `_update_lance_table(db_path, table_name, file_path, new_rows)` for incremental add; `_delete_lance_chunks(db_path, table_name, file_path)` for deletion; compaction check after add/delete; HNSW index creation above threshold
- `server.py` `WaveIndex`: replace `self._docs_vecs` / `self._code_vecs` numpy arrays with `self._docs_table` / `self._code_table` LanceDB Table objects; update `_ensure_loaded`; replace `_cosine_search` with `_lance_search`; push metadata filters into where predicates; retain `_cosine_search` as legacy fallback
- All LanceDB constants named in `indexer.py` and `server.py`
- Tests covering: full build writes Lance tables, query returns correct results with scores, legacy `.npy` fallback triggers warning, incremental add visible in results, deletion removes chunks from results, metadata filter pushed to where clause, compaction triggered at threshold, project+framework merge
- `docs/architecture/search-architecture.md` — update vector search description
- `docs/architecture/domain-map.md` — add `lancedb` to inbound dependencies

**Out of scope:**

- Live filesystem watcher (`watchdog`) — incremental add/delete is the foundation; watcher is a follow-on
- Changing embedding models or `VECTOR_TOP_K` values
- Replacing or modifying the reranker, two-hop expansion, or any MCP tool above `WaveIndex`
- Auto-migrating existing `.npy` indexes — users rebuild via `setup_index.py`

## Acceptance Criteria

- AC-1: After running `setup_index.py` on a repo, a LanceDB database directory exists at `.wavefoundry/index/lancedb/` containing `docs` and `code` tables; `.npy` and `.json` index files are absent.
- AC-2: `WaveIndex.search_docs` and `WaveIndex.search_code` return results with correct `score` values and the same chunk field shape as before. No caller-visible response shape change.
- AC-3: A repo with only legacy `.npy` + `.json` files still loads and searches correctly; a migration warning is emitted to stderr exactly once per `_ensure_loaded` call.
- AC-4: After adding one new chunk to an existing Lance table, a query matching that chunk's content returns it in results.
- AC-5: After deleting all chunks for a file path, no result from that path appears in subsequent queries.
- AC-6: `search_code(language="python")` issues a LanceDB query with a `where="language = 'python'"` predicate rather than post-filtering results in Python (verified by test patching `table.search` and asserting the where clause).
- AC-7: When a Lance table's fragment count exceeds `LANCEDB_COMPACT_THRESHOLD`, all three cleanup steps fire in sequence: `compact_files()`, then `cleanup_old_versions(older_than=timedelta(seconds=0))`. After compaction, query results are unchanged and previously deleted rows are absent from the data files.
- AC-7b: On a full rebuild (`setup_index.py`), after Lance tables are confirmed non-empty, legacy `.npy` and `.json` files in the same index directory are deleted. If no legacy files are present, the step is a no-op. A failure to delete legacy files emits a warning but does not fail the build.
- AC-8: A table with fewer than `LANCEDB_INDEX_THRESHOLD` rows is queried without an explicit HNSW index (flat scan); a table at or above the threshold has `create_index()` called after population.
- AC-9: A query matching a chunk in the framework table and a chunk in the project table returns both, in combined score order.
- AC-10: `LANCEDB_INDEX_THRESHOLD`, `LANCEDB_COMPACT_THRESHOLD`, `LANCEDB_NPROBES`, `LANCEDB_REFINE_FACTOR` are defined in `indexer.py` and `server.py`; no magic numbers at LanceDB call sites.
- AC-11: All existing `search_docs`, `search_code`, and `search_combined` tests pass unchanged.

## Tasks

- Open `framework_edit_allowed` gate
- Add `lancedb` to `setup_index.py` install step
- In `indexer.py`:
  - Add all LanceDB constants
  - Add `_build_lance_tables(docs_chunks, docs_vecs, code_chunks, code_vecs, db_path)`: open `lancedb.connect(db_path)`; create/overwrite `docs` and `code` tables with schema `{**chunk_fields, "vector": vector_column}`; call `table.create_index()` for tables above `LANCEDB_INDEX_THRESHOLD`
  - Add `_update_lance_table(db_path, table_name, file_path, new_rows)`: open db; delete existing rows for `file_path`; add new rows; check and run compaction if fragment count exceeds threshold
  - Add `_delete_lance_chunks(db_path, table_name, file_path)`: open db; `table.delete(f"path = '{file_path}'")`; check and run compaction
  - Add `_optimize_lance_table(table)`: calls `table.optimize(cleanup_older_than=timedelta(seconds=0))` — called after add/delete when fragment count exceeds `LANCEDB_COMPACT_THRESHOLD`; synchronous, runs in `indexer.py` subprocess only
  - Add `_cleanup_legacy_index_files(index_dir)`: after successful Lance build, delete `docs.npy`, `code.npy`, `docs.json`, `code.json`, `meta.json` if present; verify Lance tables non-empty first; log warning on deletion failure, do not raise
  - Replace `_save_npy_atomic` calls with `_build_lance_tables`; call `_cleanup_legacy_index_files` after successful build
  - Update incremental per-file path to call `_update_lance_table` (add) and `_delete_lance_chunks` (remove)
- In `server.py` `WaveIndex`:
  - Add LanceDB constants
  - Replace `self._docs_vecs` / `self._code_vecs` with `self._docs_table` / `self._code_table`
  - Update `_ensure_loaded`: connect to LanceDB when present; fall back to `.npy` path with one-time warning; retain `_cosine_search` for legacy path
  - Add `_lance_search(table, query_vec, top_n, where=None)`: `table.search(query_vec).metric("cosine").limit(top_n).where(where).nprobes(LANCEDB_NPROBES).refine_factor(LANCEDB_REFINE_FACTOR).to_list()`; map results to chunk dicts with `score` field
  - Update `search_docs`, `search_code` to push `kind`, `language`, `tags` filters into `where` predicate
  - Update `search_combined` to call `_lance_search` on both project and framework tables and merge
- Write tests covering AC-1 through AC-11 in `test_server_tools.py` / `test_indexer.py`
- Update `docs/architecture/search-architecture.md`
- Update `docs/architecture/domain-map.md`
- Close `framework_edit_allowed` gate
- Run full test suite

## Agent Execution Graph

| Workstream                     | Owner       | Depends On           | Notes                                                         |
| ------------------------------ | ----------- | -------------------- | ------------------------------------------------------------- |
| `indexer.py` build + add/delete | Engineering | —                   | `_build_lance_tables`, `_update_lance_table`, `_delete_lance_chunks` |
| `server.py` load + search      | Engineering | indexer table schema | `_ensure_loaded`, `_lance_search`, predicate pushdown, merge  |
| legacy fallback                | Engineering | server.py load       | `.npy` detection + warning; `_cosine_search` retained         |
| tests                          | Engineering | all above            | Needs implementation complete                                 |
| arch doc updates               | Engineering | —                    | Can run in parallel                                           |
| verification                   | Engineering | all above            | Full test suite pass required                                 |

## Serialization Points

- `indexer.py` and `server.py` must agree on the LanceDB database path and table schema (column names matching chunk dict keys) before either is implemented.
- `_ensure_loaded` must be complete before `_lance_search` is wired into `search_docs` / `search_code`.
- Index creation (`create_index`) must happen after table population in `_build_lance_tables`; creating an index on an empty table is a no-op or error.

## Affected Architecture Docs

- `docs/architecture/search-architecture.md` — update vector retrieval: O(n) numpy cosine scan → LanceDB embedded vector store (Lance columnar format, HNSW index, native predicate pushdown); document add/delete/compaction lifecycle; note legacy `.npy` fallback
- `docs/architecture/domain-map.md` — add `lancedb` to MCP Server inbound dependencies
- `docs/architecture/mcp-tool-surface.md` — no change (tool surface unchanged)

## AC Priority

| AC    | Priority    | Rationale                                                                       |
| ----- | ----------- | ------------------------------------------------------------------------------- |
| AC-1  | required    | Verifies index build writes Lance format                                        |
| AC-2  | required    | Response contract unchanged — callers must not be broken                        |
| AC-3  | required    | Legacy fallback — existing repos must keep working without a rebuild            |
| AC-4  | required    | Incremental add — foundation of the update path                                 |
| AC-5  | required    | Deletion — stale chunks from deleted/renamed files must not appear in results   |
| AC-6  | required    | Predicate pushdown — filter correctness and efficiency                          |
| AC-7  | important   | `optimize()` — full MVCC cycle via single call; prevents fragment/manifest accumulation and keeps HNSW index current |
| AC-7b | required    | Legacy file cleanup on rebuild — clean state after upgrade; no dual-index confusion       |
| AC-8  | important   | Index threshold — flat scan for small tables, HNSW for large                   |
| AC-9  | required    | Project + framework merge correctness                                           |
| AC-10 | important   | Named constants — no magic numbers at call sites                                |
| AC-11 | required    | No regression on existing search behavior                                       |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-15 | Planned |          |
| 2026-05-16 | Follow-up: JSON-free write path. Lance stores chunks+vectors together, making the legacy `.json` chunk files also redundant. Restructured `_build_index_locked` into two fully separate paths: **LanceDB-native** (full build: `_build_lance_tables`; incremental: `_lance_incremental_write` — delete stale rows per file, add new rows) and **numpy fallback** (JSON + npy, only when lancedb unavailable or failed). Added `_make_lance_rows` helper (shared by both write paths). Added `_lance_incremental_write`. `_cleanup_legacy_files` now deletes both `.npy` and `.json`. Upgrade-path guard added: if lancedb importable but no lance tables exist (legacy npy index), forces full rebuild to create complete tables. model_changed detection updated to use `meta["content"]` as presence signal so empty lance tables (e.g. Python-only repos with no doc chunks) don't trigger spurious full rebuilds. Added `_read_index_chunks` helper to test file; updated all tests that read from JSON to use it (Lance or JSON adaptively). 1325 tests pass. | indexer.py, test_indexer.py |
| 2026-05-16 | Follow-up: npy-free write path. Restructured `_build_index_locked` write block: JSON chunk files are always written (incremental state store); LanceDB is attempted first for vectors; npy is written only as fallback when Lance fails. `_cleanup_legacy_index_files` replaced by `_cleanup_legacy_npy_files` (deletes only `*.npy`, not `*.json` — json retained for incremental tracking). `cleanup_legacy` parameter and `--cleanup-legacy` CLI flag removed (cleanup now runs automatically after every successful Lance write). Model-changed detection updated to accept `docs.lance`/`code.lance` dirs as proof vectors are present (prevents spurious full rebuilds when npy is absent). 1325 tests pass. | indexer.py, setup_index.py |
| 2026-05-16 | Follow-up: flat table layout. Removed `LANCEDB_DIR_NAME = "lancedb"` constant from both `indexer.py` and `server.py`. LanceDB now connects to the index directory directly (`lancedb.connect(str(index_dir))`), so tables land at `index_dir/docs.lance/` and `index_dir/code.lance/` — no `lancedb/` subdirectory. Updated `_ensure_loaded` in `server.py` (`project_lance_dir = self.index_dir`, `framework_lance_dir = self.framework_index_dir`). Updated `TestLanceDBIndex` to drop `LANCEDB_DIR_NAME` assertions. 1325 tests pass. | indexer.py, server.py, test_server_tools.py |
| 2026-05-16 | Follow-up: lancedb auto-install. Added `_auto_install_lancedb()` to `indexer.py` — when lancedb is missing at build time, automatically runs `pip install lancedb` (with `--break-system-packages` retry for Homebrew envs) instead of silently falling back to numpy. Added `--cleanup-legacy` CLI flag to `indexer.py`; `setup_index.py` passes it on full builds so legacy `.npy`/`.json` cleanup is explicit and controlled. Server-side `_load_lance_layer` emits a clear install-hint message when lance tables exist but lancedb is not importable. `subprocess` import added to `indexer.py`. 1325 tests pass. | indexer.py, setup_index.py, server.py |
| 2026-05-16 | Implemented. Added `lancedb` to `setup_index.py` `REQUIRED_IMPORTS`. Added `LANCEDB_DIR_NAME`, `LANCEDB_INDEX_THRESHOLD`, `LANCEDB_COMPACT_THRESHOLD`, `LANCEDB_NPROBES`, `LANCEDB_REFINE_FACTOR` constants to both `indexer.py` and `server.py`. Added `_build_lance_tables`, `_optimize_lance_table`, `_lance_fragment_count`, `_update_lance_table`, `_delete_lance_chunks`, `_cleanup_legacy_index_files` to `indexer.py`; wired into `_build_index_locked` after numpy write, with legacy file cleanup on full rebuild. Added `_lance_search` method and `_using_lance` branch to `WaveIndex` in `server.py`; `_ensure_loaded` detects `.lance/` dirs and falls back to numpy with one-time warning. `search_docs`, `search_code`, `search_combined` push metadata filters into LanceDB `where` predicates. Arch docs updated (`search-architecture.md`, `domain-map.md`). 1325 tests pass (1 skipped: live LanceDB test gated on lancedb install). | indexer.py, server.py, setup_index.py, test_server_tools.py, test_setup_index.py |

## Decision Log

| Date       | Decision                                                              | Reason                                                                                                           | Alternatives                                                                          |
| ---------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 2026-05-15 | LanceDB over raw hnswlib                                              | True deletion (`table.delete`) eliminates tombstone/rebuild-threshold complexity; unified storage eliminates multi-file layout; MVCC eliminates atomic temp-file writes; native filtering eliminates post-search Python loops | hnswlib (rejected: requires custom soft-delete + graph-rebuild infrastructure); ChromaDB (wraps hnswlib + sqlite, no advantage over LanceDB) |
| 2026-05-15 | Apache 2.0 license confirmed for both `lancedb` and `lance`          | Permissive; commercial use unrestricted; no copyleft or network-use clauses                                      | —                                                                                     |
| 2026-05-15 | In-process embedded — no service dependency                          | LanceDB runs as a Python library in the same process as the MCP server; same operational model as hnswlib        | Qdrant / Weaviate (rejected: require separate server process)                         |
| 2026-05-15 | `IVF_HNSW_SQ` index above `LANCEDB_INDEX_THRESHOLD = 1000` rows      | Flat scan is exact and fast enough below 1000 chunks (framework index); HNSW needed above for query latency     | Always build index (unnecessary overhead for tiny tables); never build (O(n) at scale) |
| 2026-05-15 | Use `table.optimize(cleanup_older_than=timedelta(seconds=0))` instead of separate `compact_files()` + `cleanup_old_versions()` | `optimize()` is the single canonical VACUUM-style call that combines compaction, version pruning, and index optimization; confirmed available in LanceDB Python API; `cleanup_older_than=timedelta(seconds=0)` required — default is 7 days which would leave version files accumulating | Two separate calls (functionally equivalent but `optimize()` also folds new rows into existing HNSW index, which the two-step approach misses) |
| 2026-05-15 | Compaction at `LANCEDB_COMPACT_THRESHOLD = 20` fragments             | Lance accumulates delta fragments on add/delete; compaction merges them without changing results; 20 is conservative and safe | Compact on every write (too frequent); never compact (fragment scan degrades at scale) |
| 2026-05-15 | Delete legacy `.npy`/`.json` files after successful full rebuild     | Clean state after upgrade; avoids confusion about which index is active; legacy fallback in `_ensure_loaded` only applies when `.hnsw`/Lance files are absent | Keep legacy files indefinitely (confusing dual-state); delete before build succeeds (data loss risk if build fails) |
| 2026-05-15 | Predicate pushdown for `kind`, `language`, `tags` filters            | LanceDB evaluates predicates before returning results, reducing data transferred to Python; consistent with how a columnar store should be used | Post-filter in Python (functionally equivalent but wastes bandwidth and scan work)    |
| 2026-05-15 | Legacy `.npy` fallback retained, not auto-migrated                   | Existing repos must not break silently; migration warning directs users to `setup_index.py`                      | Auto-migrate on load (rejected: writes during a read operation; unexpected side effect) |
| 2026-05-15 | File watcher out of scope                                             | Incremental add/delete is the prerequisite; watcher is independent and can ship separately                       | Bundle watcher in this change (rejected: increases scope)                             |

## Risks

| Risk                                              | Mitigation                                                                                      |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `lancedb` unavailable in offline/airgapped envs  | Same risk profile as fastembed; `setup_index.py` handles install; legacy `.npy` fallback keeps existing indexes working |
| Lance fragment accumulation without compaction    | `LANCEDB_COMPACT_THRESHOLD` triggers compaction automatically after add/delete operations       |
| Schema mismatch between chunk dicts and Lance table | Table schema derived from chunk dict keys at build time; validated by AC-2 (same field shape) |
| `nprobes` / `refine_factor` too low at large scale | Both tunable via named constants without code changes; document that higher values trade latency for recall |
| LanceDB API changes across versions               | Pin `lancedb` version in `setup_index.py` requirements; test suite covers query contract (AC-11) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
