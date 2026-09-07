# Performance Budget

Owner: Engineering
Status: active
Last verified: 2026-09-06

Budgets cite recorded measurements (1sc7c hook-cost design pass, 1sbfk/1seiz
live probes, 1sed7 structural budgets) — no unquantified claims. Reference
hardware is an M2 Max; slower machines scale these numbers, which is why
operational bounds (docs-lint, short-op subprocesses) are config-tunable
rather than hard-coded.

## Model and Format Constants (lint-bound)

These documented facts are bound to their code constants by the
docs-constants lint (wave 1seau) — if this table drifts from the code, the
docs gate fails:

- docs embedding model `Snowflake/snowflake-arctic-embed-s`
- code embedding model `Snowflake/snowflake-arctic-embed-s`
- reranker model `cross-encoder/ms-marco-MiniLM-L-6-v2`
- chunker version `42`

Both embedding selectors currently reuse one Arctic S instance. Embedding
inference is FP16 on supported GPU providers and INT8 on CPU at static forward
batch 32. The L6 reranker remains FP16 GPU / INT8 CPU at its independent batch
40.

## Measured Budgets

| Operation | Budget | Measured basis |
| --------- | ------ | -------------- |
| Full semantic rebuild (docs + code) | minutes-class (~2–10 min by corpus/hardware) | this repo: docs full rebuild ~100 s; code rebuild ~4 min incl. graph merge (2026-07-20 live builds, prior model set). Arctic S encodes at a wave-measured 350.51 chunks/s versus 581.73 for the prior XS default (same-machine FP16 MPS, batch 32), a ~1.63x indexing slowdown accepted inside the 2.0x ceiling recorded in `docs/references/model-selection.md`. The model-set v1-to-v2 upgrade triggers a one-time full re-embed of both semantic layers. |
| Incremental post-edit hook build | zero-change ~1.2 s; docs edit ~4 s; code edit ~12 s | 1sc7c hook-cost measurements |
| Heal pass (false-stale repair) | tens of seconds on a large corpus | 38 s / 1,330 files (recorded) |
| FTS derived rebuild (`content='fts'`) | seconds-class | ~3.4 s (recorded) |
| `code_ask` end-to-end | sub-second to low seconds; envelope carries `vector_ms` / `rerank_ms` components | live envelopes; reranker session cold-load dominates first call |
| Codebase map refresh (`content='map'`) | ~0.1 s | 1p601 measurement (~0.09 s) |
| Graph-only rebuild (`content='graph'`), incremental merge | ~10–20 s | this repo: 19.4 s (2026-07-20 build log) |
| Graph-only rebuild after a BUILDER VERSION bump (full re-extraction) | ~40–60 s | this repo: 52 s at graph builder 48 / cluster builder 13 (2026-09-03). A version bump invalidates every per-file artifact by design, so this is the one-time cost OF the bump, not a recurring per-build figure. Compare against the incremental row above only after the first post-bump build. |
| Graph-only rebuild COMMAND, wall clock (`index_build(content='graph', mode='rebuild')`) | ~50–60 s after a version bump; graph phase plus a few seconds | this repo, 2026-09-04, same machine, both after graph builder 49: **before** wave `1x4ol`, 203 s, of which the secrets scan was 198.5 s (`full`, 0 cache-skipped) because the graph's `full` flag was forwarded to the scanner; **after** `1x4oj`, 52 s, secrets 6.4 s (`incremental`, 2,069 cache-skipped, 1 scanned). The two phase rows above measure the graph alone and never showed this cost; an operator waits on the command, so this row is the one to compare against. |
| Secrets full scan (`wf_scan_secrets(mode='full')`, or any escalation to full) | tens of seconds on this corpus | this repo, 2026-09-04, same machine, 8 workers, isolated (no concurrent build): **before** wave `1x4ol`, 198.8 s over 2,373 files, of which one 1.15 MB identifier-dense evidence artifact was 173.6 s; **after** `1x4ok`, 18.2 s over 2,377 files, zero findings both sides. The saving is the load-time collapse of a redundant nested lazy prefix in eleven rules, proven language-preserving by differential test; no file is skipped and no time bound exists. A serial (1-worker) run of the unmodified engine measured 369.1 s, so the pool bought only 1.85x before the fix because a single file pinned one worker. |
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
| Markdown table decomposition (chunker 42, wave 1xa00) | One ordered scan plus emitted text linear in input size. A compacted header below the 2,000-character target may repeat across bounded row groups; a header still at or above the target is emitted once with all complete rows, preventing row-count × header-width amplification | public irreducible-header regression grows header width and row count together and asserts byte-exact single-copy output; performance review measured the rejected branch at 293.63× amplification for 54,908 input characters |
| Chunk-id collision census (derived rebuild, wave 1wpif) | One dict pass over the SAME materialized rows the rebuild already consumes: row visits linear in chunk count, zero chunker invocations, zero embedding calls, no second repository pass; wall-clock overhead at most 10% versus the identical rebuild with the census patched out | paired same-process runs on one temp store, 3 interleaved repetitions, median declared before measurement: 53.6 ms vs 52.0 ms on 8,000 synthetic rows (ratio 1.03, M2 Max) |
| Warmed public lexical read (`code_lexical`, the hybrid FTS half of `code_search` / `code_ask`, the degraded FTS fallbacks; wave 1wpif `1wpag`) | Zero `COUNT(*)`, zero `quick_check` / `integrity_check`, zero corpus-sized FTS or registry scans, zero store writes: one dict lookup of the epoch-keyed verdict cache, the `build_state` row read, and the MATCH query itself (the former per-call `_state_store_health_summary` coverage tie-in is now the same epoch-cached read) | asserted by `test_fts_query_honesty.ProbedServingTests.test_warmed_healthy_read_runs_no_counts_no_health_scan_no_probe` through a sqlite trace hook (`set_trace_callback` on every read-only store connection) plus seam spies on `fts_state_verdict` and `_state_store_health_summary`; `code_lexical` warm p95 stays under its standing relative gate (the `1sear` pair's second run: 673 ms baseline, 841 ms threshold); the chunker-40 pair recorded 25 ms |
| Bounded candidate refill (`code_search` with `max_per_file` or a non-allowlisted language, and the lexical fallback; wave 1wpif `1wpah`) | Monotonic nested windows 30, 60, 120, 240 per source/table; at most 4 substrate queries and 240 examined rows per source per public call (`code_search`: 8 / 480; `code_ask`: 16 / 960 over its four fused sources, 20 / 1200 when the live keyword pass fires); an exhausted source is not re-queried; the cross-encoder input stays at the pre-refill window `max(4 * limit, 30)`; the accounting ledger adds zero substrate queries | asserted by `test_retrieval_candidate_generation.HostileSkewTests` (exactly four windows on a 250-chunk single-file skew, then a typed ceiling exit) and `CodeAskAggregateAccountingTests` (the aggregate over a full `code_ask` call) |
| FTS probe boundary (reconcile / open / build-state transition / serving error; wave 1wpif `1wpag`) | Exactly one bounded probe per table per boundary, then cached for the epoch: one MATCH liveness query, four `COUNT(*)` parity reads (FTS, registry, `_docsize`, `_content`), one linear keyed-digest scan of the FTS table; a serving error triggers exactly one re-probe; the query path at most schedules healing (never executes it) and a damaged table heals once per epoch under the build lock | full verdict 28.6 ms median (digest scan 23.1 ms) on 8,000 synthetic rows / 4.6 MB of chunk text, 5 repetitions (M2 Max) |
| Serving-coverage computation (probe boundary, wave 1wpif `1wpag` delivery repair) | The `chunk_index` compare `index_health` reports, from the shared `_chunk_index_coverage` producer: one Lance metadata row count and one indexed registry `count(*)` per table, cached per table for the epoch. It must NOT route through `_state_store_health_summary`, whose `probe_state_store` structural quick_check re-establishes for the same epoch what `fts_state_verdict` already established. The two hybrid halves that never read coverage (`_fts5_lexical_search`, `_lexical_candidates`) request none at all (`include_coverage=False`), so the first hybrid `code_search` / `code_ask` of an epoch computes zero coverage | `probe_state_store` measured 674 ms on the live store (26,567 docs / 8,269 code rows) against about 2 ms for the Lance and registry counts, M2 Max; asserted by `test_fts_query_honesty.ProbedServingTests.test_coverage_is_computed_without_the_probing_health_summary` and `test_retrieval_candidate_generation.ColdEpochHybridCostTests` |

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
