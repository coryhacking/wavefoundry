# Performance Budget

Owner: Engineering
Status: active
Last verified: 2026-07-21

Budgets cite recorded measurements (1sc7c hook-cost design pass, 1sbfk/1seiz
live probes, 1sed7 structural budgets) — no unquantified claims. Reference
hardware is an M2 Max; slower machines scale these numbers, which is why
operational bounds (docs-lint, short-op subprocesses) are config-tunable
rather than hard-coded.

## Model and Format Constants (lint-bound)

These documented facts are bound to their code constants by the
docs-constants lint (wave 1seau) — if this table drifts from the code, the
docs gate fails:

- docs embedding model `Snowflake/snowflake-arctic-embed-xs`
- code embedding model `BAAI/bge-small-en-v1.5`
- reranker model `cross-encoder/ms-marco-MiniLM-L-6-v2`
- chunker version `32`

## Measured Budgets

| Operation | Budget | Measured basis |
| --------- | ------ | -------------- |
| Full semantic rebuild (docs + code) | minutes-class (~2–10 min by corpus/hardware) | this repo: docs full rebuild ~100 s; code rebuild ~4 min incl. graph merge (2026-07-20 live builds) |
| Incremental post-edit hook build | zero-change ~1.2 s; docs edit ~4 s; code edit ~12 s | 1sc7c hook-cost measurements |
| Heal pass (false-stale repair) | tens of seconds on a large corpus | 38 s / 1,330 files (recorded) |
| FTS derived rebuild (`content='fts'`) | seconds-class | ~3.4 s (recorded) |
| `code_ask` end-to-end | sub-second to low seconds; envelope carries `vector_ms` / `rerank_ms` components | live envelopes; reranker session cold-load dominates first call |
| Codebase map refresh (`content='map'`) | ~0.1 s | 1p601 measurement (~0.09 s) |
| Graph-only rebuild (`content='graph'`) | ~10–20 s | this repo: 19.4 s incremental merge (2026-07-20 build log) |
| `wf docs-lint` full corpus | < 300 s bound (config-tunable `docs_lint.full_scan_timeout_seconds`) | typically seconds; the bound guards the subprocess |
| Gardener / surface render subprocesses | < 180 s bound (config-tunable `subprocess_ops.*_timeout_seconds`, wave 1seax) | typically seconds; generous bound for slow machines |
| Framework script test suite | ~4.5 min full (6 workers, ~6,000 tests) | 2026-07-20 runs: 260–320 s |

## Semantic-Index State Budgets (wave 1sed7)

Structural budgets, not brittle timings — the invariants are about *shape*
(how many probes, which durability class), with locally measured reference
numbers:

| Operation | Budget (structural) | Reference measurement |
|-----------|--------------------|----------------------|
| Reader epoch probe (`build_epoch_token`) | Exactly two short read-only queries per indexed operation (one pre, one post); no state held across the operation | ~0.31 ms median / ~0.38 ms p95 per probe (M2 Max) |
| Build boundary commits | Exactly two small `FULL`-synchronous commits per mutating build (fence + completion CAS); everything else stays `synchronous=NORMAL` | sub-millisecond each; invisible next to embedding time |
| True no-op build | Zero epoch writes, generation unchanged (read-only reap/heal preflight only) | — |
| Dashboard index stats | Cached/event-driven collection; the store read is `read_build_summary` (scalars + one COUNT) and Lance reads are `count_rows` metadata only — no per-file rows and no table materialization. Exception: the daemon's periodic staleness timer reads the full per-file snapshot because it IS the input-hash compare; it never runs on the HTTP request path | — |
| Whole-store reset convergence | One all-layer re-chunk pass with Lance vector reuse (no re-embedding of unchanged chunks) | minutes-class worst case, same as a `--rechunk` pass |

## Performance Hotspots and Guards

The real hotspots, with their standing guards:

- **Embedding** (model inference): the dominant cost of every build.
  Guards: incremental hash-based updates, content-hash vector reuse on
  re-chunk, GPU/CoreML acceleration where available (~8.75× on M2 Max),
  detached background builds that defer to a running test suite.
- **Reranker session initialization** (cold load): dominates the first
  `code_ask` after a reload. Guard: session reuse for the process lifetime;
  the envelope reports `rerank_ms` so regressions are visible.
- **O(corpus) walks** (full lint scans, heal passes, secrets scans):
  seconds-to-tens-of-seconds on large corpora. Guards: incremental modes
  (`--changed` hook lint, per-file index state, content-keyed secrets
  cache) and config-tunable subprocess bounds with truncation-flagged
  captured output.
- **Suite/indexer contention**: back-to-back six-worker suite runs contend
  with background builds. Guard: mutual exclusion with atomic rechecks
  (wave 1t72b); performance-test budgets carry contention headroom
  (wave 1seax, 1t3zv policy in `docs/architecture/testing-architecture.md`).
