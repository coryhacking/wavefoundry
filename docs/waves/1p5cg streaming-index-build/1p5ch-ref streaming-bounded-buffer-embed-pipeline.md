# Stream the full-rebuild embed/write path through a bounded buffer

Change ID: `1p5ch-ref streaming-bounded-buffer-embed-pipeline`
Change Status: `planned`
Owner: Engineering
Status: planned
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

- [ ] AC-1: full rebuild streams — peak buffered chunks ≤ the configured threshold (asserted by test), independent of corpus size.
- [ ] AC-2: the vector + FTS index is built once after all appends; row count and index presence match the batch path.
- [ ] AC-3: parity — a fixture-corpus rebuild via the streamed path yields rows (ids, text, vectors) identical to the current batch path.
- [ ] AC-4: build progress logs "file N / M files" with no total-chunk pre-count.
- [ ] AC-5: incremental (non-rebuild) updates + content-hash vector reuse unchanged (existing tests green).
- [ ] AC-6: full framework suite + docs-lint green; a real full rebuild on this repo stays GPU-accelerated and comparable in wall-time to the current ~2 min.

## Tasks

- [ ] Extract a streaming writer: create-or-open the Lance table, append row batches, build the index once at the end.
- [ ] Replace the `chunk-all → _embed_to_rows → write-all` full-rebuild flow with the file→buffer→embed→append loop; thread the buffer threshold from config.
- [ ] File-oriented progress logging; remove the total-chunk dependency on the rebuild path.
- [ ] Tests: parity (stream vs batch), memory-bound (peak buffer), progress format; verify incremental path untouched. Update the pipeline doc.

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
|      |        |          |


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
