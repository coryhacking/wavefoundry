# Streaming Embed-Write for Full Rebuild Path

Change ID: `12pr7-enh streaming-embed-write`
Change Status: `implemented`
Owner: framework-engineer
Status: implemented
Last verified: 2026-05-18
Wave: 12pn3 search-retrieval-quality

## Rationale

The current full rebuild path in `_build_index_locked` collects all chunks into memory, embeds them all into a single large numpy array, then writes the entire array to LanceDB in one call. This buffers `all_chunks × dim × 4 bytes` — for a 4038-chunk docs index at 768 dims that's ~12 MB of vectors plus the chunk text and metadata. More importantly, the full embedding array must be held in memory alongside the ONNX inference working buffers, doubling peak memory during the write phase.

LanceDB's `table.add()` accepts incremental appends — there is no reason to buffer everything. The ideal flow is: chunk batch → embed → `table.add(batch)` → next batch. Peak memory drops from the full corpus size to one batch at a time (`EMBED_BATCH_SIZE × dim × 4 bytes` ≈ 0.8 MB at 256 vs ~12 MB for the full corpus, with no large intermediate array held in memory alongside live inference buffers).

This is a holdover from when the index was written to numpy/JSON files and a single contiguous array was required.

## Requirements

1. In the full rebuild path, the caller no longer pre-computes a single large `(n, dim)` numpy array. Instead, chunks stream through embed→write in `EMBED_BATCH_SIZE` batches.
2. Batch composition uses a **sliding sort buffer**: a `SORT_WINDOW_SIZE`-chunk buffer is maintained in sorted-by-length order. Each iteration pops the `EMBED_BATCH_SIZE` shortest chunks from the buffer, embeds and writes them, then refills the buffer with the next `EMBED_BATCH_SIZE` chunks from the corpus and re-sorts. This gives each batch the tightest possible length grouping from the available pool — better padding efficiency than per-batch sorting alone, at negligible cost (re-sorting 2048 items ≈ 22k comparisons per batch).
3. The internal length-sort in `_embed_texts` is removed. Callers are responsible for presenting pre-sorted inputs; the function becomes a pure embed-and-return helper.
4. For the first batch of each table, the table is created via `db.create_table(table_name, data=rows, mode="overwrite")`. Subsequent batches use `table.add(rows)`.
5. After all batches are written, the vector index (`IVF_HNSW_SQ`) and FTS index are created once — not per batch. The IVF threshold check uses `len(chunks)` counted before the loop (O(1), already available).
6. The incremental write path (`_lance_incremental_write`) is unchanged — it already operates per-file and is effectively batched.
7. `_embed_chunks` is retained for the incremental path (which still needs it to embed per-file chunks into `new_doc_vecs`/`new_code_vecs`). Only the full-rebuild call to `_embed_chunks` is removed.
8. Progress logging emits per-batch position: `"embedding doc chunks 1–256/4038"`, `"257–512/4038"`, etc.

## Scope

**Problem statement:** Full rebuild accumulates all chunk embeddings into one large array before writing, holding the entire corpus in memory unnecessarily. LanceDB supports incremental appends.

**In scope:**

- Sliding sort buffer with `SORT_WINDOW_SIZE = 2048`, `EMBED_BATCH_SIZE = 256`
- Remove per-corpus `_embed_chunks` call from full rebuild path; replace with inline streaming loop
- Remove internal length-sort from `_embed_texts`
- Remove `_build_lance_tables` (no longer called from full rebuild path; incremental path has its own write logic)
- Retain `_embed_chunks` for incremental path
- FTS and vector index creation once, after all batches written

**Out of scope:**

- Changing `_lance_incremental_write`
- Changing `EMBED_BATCH_SIZE` value
- Applying the sliding buffer to the incremental path

## Acceptance Criteria

- AC-1: A full rebuild (`--full`) completes successfully and produces the same doc and code chunk counts as before.
- AC-2: The `new_doc_vecs` and `new_code_vecs` large intermediate arrays no longer exist in the full rebuild code path.
- AC-3: `_build_lance_tables` no longer exists.
- AC-4: `_embed_texts` no longer contains an internal sort; it embeds and returns in input order.
- AC-5: FTS and IVF_HNSW_SQ indexes are created once per table after all batches land, not per batch.
- AC-6: Progress log emits chunk range per batch during embedding.
- AC-7: 1326 tests pass after the refactor.

## Tasks

- Add `SORT_WINDOW_SIZE = 2048` and `EMBED_BATCH_SIZE = 256` constants to indexer.py
- Remove the internal sort (and its inverse) from `_embed_texts`; update docstring to state callers must pre-sort for padding efficiency
- In `_build_index_locked`, replace the `_embed_chunks(...) + _build_lance_tables(...)` full-rebuild block with an inline streaming loop per table (`"docs"`, `"code"`):
  - Count `total = len(chunks)` upfront for IVF threshold check and progress logging
  - Initialise `buffer = sorted(chunks[:SORT_WINDOW_SIZE], key=lambda c: len(c["text"]))`, `read_pos = SORT_WINDOW_SIZE`, `table = None`
  - While buffer is non-empty:
    - Pop `batch_chunks = buffer[:EMBED_BATCH_SIZE]`, `buffer = buffer[EMBED_BATCH_SIZE:]`
    - Refill: extend buffer with `chunks[read_pos : read_pos + EMBED_BATCH_SIZE]`, advance `read_pos`, re-sort buffer
    - Emit progress: `"embedding {label} chunks {start}–{end}/{total}"`
    - `vecs = _embed_texts(embedder, [c["text"] for c in batch_chunks])`
    - `rows = _make_lance_rows(batch_chunks, vecs)`
    - First batch: `table = db.create_table(table_name, data=rows, mode="overwrite")`; subsequent: `table.add(rows)`
  - After loop: if `total >= LANCEDB_INDEX_THRESHOLD` create IVF_HNSW_SQ index; then `_create_fts_index(table, table_name)`
- Remove `_build_lance_tables` function
- Verify test callsites of `_build_lance_tables` and update or remove them
- Run full test suite

## Agent Execution Graph

| Workstream      | Owner              | Depends On      | Notes                                               |
| --------------- | ------------------ | --------------- | --------------------------------------------------- |
| embed-texts     | framework-engineer | —               | Remove internal sort from _embed_texts              |
| streaming-loop  | framework-engineer | embed-texts     | Inline sliding-buffer loop in _build_index_locked   |
| cleanup         | framework-engineer | streaming-loop  | Remove _build_lance_tables; fix test callsites      |
| test            | framework-engineer | cleanup         | Full test suite                                     |

## Serialization Points

- `_embed_texts` sort removal must land before streaming-loop (callers must pre-sort their input)

## Affected Architecture Docs

N/A — internal indexer memory management; no boundary, data-flow, or API impact.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  |           |
| AC-2 | required  |           |
| AC-3 | required  |           |
| AC-4 | required  |           |
| AC-5 | required  |           |
| AC-6 | nice-to-have |        |
| AC-7 | required  |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-17 | Implemented. `SORT_WINDOW_SIZE = 2048` and `EMBED_BATCH_SIZE = 256` constants added. Internal sort removed from `_embed_texts`; sort-and-invert moved to `_embed_chunks` for incremental path. `_build_lance_tables` removed; full rebuild path replaced with `_stream_embed_write` sliding-buffer loop. IVF_HNSW_SQ and FTS indexes created once per table after all batches. `test_build_lance_tables_row_counts` replaced with `test_stream_embed_write_row_counts`. 1326 tests pass. | `run_tests.py` OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-18 | Stream in EMBED_BATCH_SIZE=256 batches; create table on first batch | table.add() accepts incremental appends; eliminates full-corpus vector array | Pre-compute full array (current, wasteful) |
| 2026-05-18 | Sliding sort buffer (SORT_WINDOW_SIZE=2048) with re-sort after each refill | Gives best possible batch composition — each batch draws the 256 shortest from a 2048-chunk pool; re-sort cost is ~22k comparisons per batch (negligible) | Fixed 2048-window (one hard boundary per window); per-batch sort only (loses cross-batch quality) |
| 2026-05-18 | Remove internal sort from _embed_texts | Callers now pre-sort via sliding buffer; internal re-sort would be redundant O(n log n) on already-sorted input | Keep internal sort (redundant but harmless) |
| 2026-05-18 | FTS and vector index once after all batches | Index creation is expensive; per-batch rebuild multiplies cost with no benefit | Per-batch index rebuild (wasteful) |
| 2026-05-18 | IVF threshold uses len(chunks) counted before loop | O(1), already known; avoids post-write table.count_rows() call | Query table after writes (extra LanceDB round-trip) |
| 2026-05-18 | Retain _embed_chunks for incremental path | Incremental path still needs per-file embedding into new_doc_vecs/new_code_vecs | Remove entirely and inline both paths (unnecessary complexity) |
| 2026-05-18 | Leave _lance_incremental_write unchanged | Already per-file batched; not the memory problem | Unify both paths |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| First-batch table creation vs subsequent appends adds branching | Track `table = None` before loop; assign on first batch — clean, one branch |
| Removing _embed_texts internal sort could break callers that pass unsorted input | Audit all callsites: _embed_chunks (incremental path) passes raw texts — add sort there; streaming loop pre-sorts via buffer |
| _build_lance_tables may have test callsites | Check test files before removing; update or replace with direct LanceDB calls |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
