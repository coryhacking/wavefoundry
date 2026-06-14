# Wave Record

Owner: Engineering
Status: planned
Last verified: 2026-06-13

wave-id: `1p5cg streaming-index-build`
Title: Streaming Index Build

## Objective

Bound indexer memory and make build progress file-oriented by streaming the embed/write pipeline. Today a full rebuild materializes every chunk and every vector for a layer in memory before writing (peak ≈ the whole corpus), and progress reads "chunk X / total" because the total is counted upfront. When this wave closes, a full rebuild streams files through a bounded buffer (chunk → embed a full GPU batch → append → flush), so peak memory is bounded by the buffer (not corpus size) — very large repos index without OOM — and progress reports "file N / M files".

## Changes

Change ID: `1p5ch-ref streaming-bounded-buffer-embed-pipeline`
Change Status: `planned`

## Wave Summary

One refactor (`1p5ch`) restructures the indexer's full-rebuild path from "chunk-all → embed-all → write-all" to a bounded-buffer stream: files are chunked into a buffer; when it fills (≥ a chunk threshold), a full GPU batch embeds and rows append to LanceDB, then the buffer flushes; the HNSW/FTS index is built once at the end. Memory is bounded to the buffer; progress is per-file; the total-chunk pre-count is gone. The produced index is equivalent to today's (same chunks, same vectors, same rows) — this is an internal restructure, not a retrieval change.

## Journal Watchpoints

- **Sequencing (blocking follow-up):** this wave is **blocked** on `1p58z` closing — implementation is **deferred** until the single-OPEN-wave slot frees. Scope is independent (indexer internals only).
- **Correctness (load-bearing):** the streamed path MUST produce an index identical to the current batch path — same chunk set, same vectors, same row contents/ids. Gate with a parity test (stream vs batch on a fixture corpus → identical rows) before anything else.
- **LanceDB write:** switch the full-rebuild create-with-all-rows to create-(empty/first-batch)-then-append; build the vector (HNSW) + FTS index ONCE after all appends, not per flush. Confirm index quality/row count unchanged.
- **GPU batch efficiency:** the buffer flush threshold must be ≥ `STATIC_BATCH` (64) so streaming doesn't shrink to tiny per-file batches and lose GPU throughput. Measure that a full rebuild stays comparable to the current ~2 min on this repo.
- **Don't regress the incremental path:** the non-rebuild path already reuses vectors by content hash — keep that intact; streaming targets the full-rebuild path.
- **Framework-edit gate** before editing `indexer.py`.

## Review Evidence

- operator-signoff: <approved when operator confirms closure>

## Dependencies

- No external wave dependencies.
