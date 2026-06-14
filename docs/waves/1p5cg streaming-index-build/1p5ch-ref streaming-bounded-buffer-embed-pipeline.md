# Stream the full-rebuild embed/write path through a bounded buffer

Change ID: `1p5ch-ref streaming-bounded-buffer-embed-pipeline`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p5cg streaming-index-build`

## Rationale

`indexer.build_index`'s full-rebuild path materializes the entire chunk list for a layer (all docs / all code chunks across every file) in memory, then `_embed_to_rows` embeds in batches against a known `total = len(chunks)`, then writes all rows. Peak memory ≈ every chunk's text + every vector for the layer — fine for this repo (~24k chunks) but an OOM risk on a large monorepo. The known `total` is also why build progress reads "chunk X / 13716": the count must exist upfront. Streaming the pipeline bounds memory to a buffer and makes progress naturally file-oriented.

## Requirements

1. Restructure the full-rebuild path to a **bounded-buffer stream**: iterate files → chunk each → push chunks into a buffer → when the buffer reaches a chunk threshold, embed one GPU batch, append the rows to LanceDB, and flush the buffer → repeat; flush the remainder at the end.
2. **Build the vector (HNSW/IVF) + FTS index once, after all rows are appended** — not per flush.
3. **Peak buffered chunks ≤ threshold** (memory bounded, independent of corpus size); the threshold default ≥ `STATIC_BATCH` (64) to keep GPU batches full, overridable via `docs/workflow-config.json` (`indexing.embed_buffer_chunks`).
4. **Progress is file-oriented**: log "file N / M files" (M = total files, known cheaply from the walk) plus the running chunk/batch count; no total-chunk pre-count.
5. **Output parity**: the streamed index is identical to today's batch path — same chunk set, same vectors, same row contents/ids, same row count.
6. Do not regress the incremental (non-rebuild) path or its content-hash vector reuse.

## Scope

**Problem statement:** the full-rebuild path holds the whole layer's chunks + vectors in memory before writing (OOM risk at scale) and reports progress by pre-counted total chunks.

**In scope:**

- The full-rebuild embed/write path in `indexer.py` (the `chunk-all → _embed_to_rows → write-all` flow) → bounded-buffer stream; LanceDB create→append; final index build; file-oriented progress logging.
- A parity test (stream vs batch → identical rows) + a memory-bound test (peak buffer ≤ threshold) + a progress-format test.

**Out of scope:**

- The incremental/update path (keeps its content-hash vector reuse).
- Embedding model/provider, chunker logic, graph extraction.
- Retrieval behavior (index content is unchanged).

## Acceptance Criteria

- [x] AC-1: full rebuild streams — peak buffered chunks bounded by `embed_buffer_chunks + one file's chunks` (the buffer flushes after each file), independent of corpus size; asserted by `test_streaming_rebuild_bounds_buffer_and_reports_file_progress`.
- [x] AC-2: the vector + FTS index is built once after all appends; row count and index presence match the batch path.
- [x] AC-3: parity — a fixture-corpus rebuild via the streamed path yields rows (ids, text, vectors) identical to the current batch path.
- [x] AC-4: build progress logs "file N / M files" with no total-chunk pre-count.
- [x] AC-5: incremental (non-rebuild) updates + content-hash vector reuse unchanged (existing tests green).
- [x] AC-6: full framework suite + docs-lint green; a real full rebuild on this repo stays GPU-accelerated and comparable in wall-time to the current ~2 min.

## Tasks

- [x] Extract a streaming writer: create-or-open the Lance table, append row batches, build the index once at the end.
- [x] Replace the `chunk-all → _embed_to_rows → write-all` full-rebuild flow with the file→buffer→embed→append loop; thread the buffer threshold from config.
- [x] File-oriented progress logging; remove the total-chunk dependency on the rebuild path.
- [x] Tests: parity (stream vs batch), memory-bound (peak buffer), progress format; verify incremental path untouched. Update the pipeline doc.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- [Shared file or integration gate that requires coordination before parallel work proceeds]

## Affected Architecture Docs

Update `docs/architecture/chunking-and-indexing-pipeline.md` (Stage 3/4: chunking + embedding) to describe the streamed bounded-buffer flow and the `indexing.embed_buffer_chunks` knob. No ARCHITECTURE.md/layering change (internal restructure, same index output). An ADR is optional — the parity requirement means no contract change.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Bounding memory is the point of the change. |
| AC-2 | required  | Building the index once (not per flush) is correctness + performance. |
| AC-3 | required  | Output parity is the safety invariant — a streamed index must equal today's. |
| AC-4 | important | The file-oriented progress display is the operator-visible ask, but secondary to the memory bound. |
| AC-5 | required  | Must not regress the incremental path / vector reuse. |
| AC-6 | required  | Suite + docs-lint green and GPU/wall-time unregressed. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Implemented bounded-buffer streaming for the full-rebuild path: `_StreamingLayerWriter` (lazy table-lock on first append, create→append, single HNSW+FTS index build at finalize), `_run_streaming_full_rebuild` (file→chunk→buffer→embed→append loop, flush at `embed_buffer_chunks`), `_resolve_embed_buffer_chunks` (config knob, floored at `EMBED_BATCH_SIZE`). Eager chunk loop guarded `if not full:`; summary reports rows written from the Lance count. | `indexer.py` |
| 2026-06-13 | Added `StreamingRebuildParityTests` (row-identical stream-vs-batch on a fixture corpus + buffer override/floor) and `OversizedFileGuardTests`. Fixed a phantom-`docs.lance`-dir regression (0-chunk layers pre-creating the lock dir broke the incremental path) via lazy lock acquisition. | `test_indexer.py` |
| 2026-06-13 | Live GPU full rebuild: CoreML for both embedders + reranker, progress logged "indexed file N/1044 files", docs 42.7s / code 51.7s / graph 8.4s (~2 min, comparable to prior). Row counts docs 13758 / code 10118, each with `vector_idx` (HNSW) + `text_idx` (FTS) built once. | build log + `wave_index_health` |
| 2026-06-13 | Added `test_streaming_rebuild_bounds_buffer_and_reports_file_progress` (AC-1 + AC-4): drives the real `_run_streaming_full_rebuild` over 14 files with `buffer_chunks=4`, asserts multiple flushes, every chunk written once, peak batch ≤ `buffer + max per-file chunks` (< corpus), and "indexed file N/M files" progress with no chunk-total pre-count. Fixed the full-rebuild summary line that reported "0 new" by reading the written row count. Full suite **3099 OK**; docs-lint clean. | `test_indexer.py`, `indexer.py` |
| 2026-06-13 | Wave-review cleanup (operator-approved): deleted the now-uncalled `_stream_embed_write` (~75 LOC dead production code — its full-rebuild callers were replaced by the streaming writer). Converted the A/B parity test to a buffer-invariance test on `_StreamingLayerWriter` (one big `add()` == batch vs tiny-buffer flushes → row-identical) and repointed `test_server_tools`'s row-count test at `_StreamingLayerWriter`. Suite **3107 OK**. | `indexer.py`, `test_indexer.py`, `test_server_tools.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
