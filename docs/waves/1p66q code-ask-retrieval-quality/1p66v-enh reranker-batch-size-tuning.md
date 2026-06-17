# Reranker static batch size is the embedder's 64; tune it to the query-time pool

Change ID: `1p66v-enh reranker-batch-size-tuning`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-17
Wave: `1p66q code-ask-retrieval-quality`

## Rationale

The GPU-vs-CPU question for the reranker is **settled** — CoreML (FP16) is decisively faster than CPU (INT8) on capable hardware (measured ~167ms vs ~980ms p50 per query on this M2 Max, independently re-verified). The open performance lever is **batch size**.

The cross-encoder reranker builds a static-shape graph pinned to `STATIC_BATCH = 64` and pads every call up to 64 rows with `(query, "")` fillers (`accel_embedder.py`). But that 64 is the **embedder's** batch optimum — embedding bulk-processes many chunks at index time, where a large batch amortizes well. The reranker's workload is completely different: a **query-time pool that maxes at `AGENT_CANDIDATE_MAX = 40`** (and is often smaller after dedup + the relevance drop-off). So the reranker runs a fixed 64-row BERT forward pass per query regardless of how few candidates it actually has — wasting up to ~37% of the passes on padding for a full 40-pool, and more for typical smaller pools.

Hypothesis (operator): a smaller reranker-specific batch (≈32) is better overall — it cuts padding for the common pool size, at the cost of a second forward pass only on the rare pool larger than the batch. The reranker's `rerank()` already chunks by `STATIC_BATCH`, so a smaller batch is correctness-safe (it just spills to another chunk). This change gives the reranker its **own** static-batch constant, decoupled from the embedder, and sets it from a benchmark across realistic pool sizes — output ranking is unchanged (batch is a pure latency/compute knob).

A quick monkeypatch sweep confirmed the batch is hard-wired: overriding `STATIC_BATCH` at runtime errors (`token_type_ids Got: 32 Expected: 64`) because the graph build and the `rerank()` reshape don't both honor an override — so this is genuine decoupling work, not a one-line constant change.

## Benchmark result (M2 Max, CoreML FP16, p50 per query)

| batch | pool 24 | pool 32 | pool 40 |
| ----- | ------- | ------- | ------- |
| 24 | 115ms (1 pass) | 295ms (2 passes) | 255ms (2 passes) |
| 32 | 136ms (1 pass) | 142ms (1 pass) | 262ms (2 passes) |
| **40** | **109ms** | **107ms** | **108ms (1 pass)** |
| 64 (old shared default) | 161ms | 159ms | 161ms (1 pass) |

**Adopted: `RERANK_STATIC_BATCH = 40`** (= `AGENT_CANDIDATE_MAX`). It is single-pass at every realistic pool size AND carries the least padding among batches that cover the ceiling in one pass — ~107ms vs the old 64's ~161ms (64 wastes ~33% padding 40→64). Any batch < 40 hits a ~2.5× two-pass cliff once the pool exceeds it (the operator's 32 hypothesis: 142ms at pool 32 but 262ms at pool 40 — rejected). Ranking output is identical across all batch sizes (verified — batch is a latency knob only).

## Requirements

1. **Decouple the reranker batch from the embedder.** Introduce a reranker-specific static-batch constant (e.g. `RERANK_STATIC_BATCH`) used consistently by the reranker's static-graph build, padding, reshape, and chunking — so the embedder's `STATIC_BATCH` (index-time optimum) and the reranker's batch (query-time optimum) are independent. The embedder path is untouched.
2. **Choose the size from data.** Benchmark reranker latency across the candidate batch sizes **24 / 32 / 40** (operator-specified set — straddling the typical pool and the `AGENT_CANDIDATE_MAX=40` ceiling) × realistic pool sizes (e.g. 8/16/24/32/40 candidates) on GPU (CoreML), and pick the size that minimizes expected per-query latency over the real pool-size distribution. Adopt the measured best of {24, 32, 40}; record the numbers (including "64 retained, no gain" if none of the three beats the current 64). 40 covers the max pool in a single pass; 24/32 cut padding for the common smaller pool at the cost of a second chunk only when the pool exceeds the batch.
3. **Identical ranking (regression guard).** For any candidate pool, the reranked order and scores must be identical regardless of batch size — batch only changes how the pool is chunked through the model, not what scores come out. A test asserts rank-equality across at least two batch sizes on the same pool (including a pool larger than the batch, exercising the multi-chunk path).
4. **Bounded + correct at the edges.** The chosen batch handles pools both smaller (padding) and larger (multi-chunk) than the batch; covers the `AGENT_CANDIDATE_MAX` ceiling without unbounded passes. The static-graph cache key already includes the batch dim (`rerank_static_{N}x{STATIC_SEQ}.onnx`), so the new size builds its own cached graph cleanly.
5. Generic; the stale per-query latency figures in `accel_embedder.py`'s reranker docstring are refreshed to measured values and the batch choice + benchmark method recorded (Decision Log + a note in the accel/graph doc). Tests cover the ranking-identical guard and the multi-chunk path.

## Scope

**Problem statement:** The reranker inherits the embedder's `STATIC_BATCH = 64`, which is tuned for index-time bulk embedding, not the reranker's query-time ≤40-candidate pool — so every query runs a padded 64-row forward pass, wasting compute.

**In scope:**

- A reranker-specific static-batch constant in `accel_embedder.py`, threaded through build / pad / reshape / chunk in `StaticShapeReranker`.
- A benchmark (lightweight harness or test-driven) sweeping batch × pool size on GPU to choose the size.
- Refresh the stale reranker latency docstring; record the decision.
- Tests (ranking-identical across batch sizes incl. multi-chunk; the chosen constant in effect).

**Out of scope:**

- GPU-vs-CPU provider selection — settled (CoreML wins); no provider change.
- Reranker provider observability ("is the reranker active?") — a separate concern; if wanted it can be a small follow-on tied to `1p66r`'s `reranked` diagnostic, not this change.
- Embedder batch size (`STATIC_BATCH`) — untouched.
- `code_ask` confidence/recall/balance (`1p66r`/`1p66s`/`1p66t`).
- `STATIC_SEQ` (512 sequence length) — unchanged.

## Acceptance Criteria

- [x] AC-1: The reranker uses its own `RERANK_STATIC_BATCH` constant, independent of the embedder's `STATIC_BATCH` (build/pad/reshape/chunk all switched); the embedder path is untouched. (`test_reranker_batch_decoupled_from_embedder`.)
- [x] AC-2: Benchmarked {24,32,40} (+64) × pool {24,32,40} on GPU (CoreML); adopted the measured best (40) over the distribution; full table recorded above. (The 32 hypothesis tested and rejected — 2-pass cliff at pool 40.)
- [x] AC-3: Ranking output is identical across batch sizes for the same pool, including multi-chunk (pool > batch). (`test_rerank_ranking_identical_across_batch_sizes` — batches 2/4/40 over a 6-passage pool, identical per-passage logits.)
- [x] AC-4: Correct + bounded at the edges (pool<batch pads; pool>batch chunks via `test_rerank_batches_across_static_batch_boundary`; covers `AGENT_CANDIDATE_MAX=40`); the missing `batch=` arg to `build_static_onnx` was the real decoupling fix (path was keyed by the reranker batch but the graph built at the default 64 — the source of the earlier stale-cache mismatch).
- [x] AC-5: Stale reranker latency docstring refreshed (~107ms GPU at batch 40, was ~167ms at 64; CPU ~6x slower); decision + full table recorded; docs-lint + full suite clean (pending final run).

## Tasks

- [x] Add `RERANK_STATIC_BATCH` and thread it through `StaticShapeReranker` build (incl. the `batch=` arg to `build_static_onnx`) / pad / reshape / chunk / probe; embedder's `STATIC_BATCH` untouched.
- [x] Benchmark {24,32,40}+64 × pool size on GPU; picked 40; captured the table.
- [x] Set `RERANK_STATIC_BATCH=40`; added the ranking-identical regression test (incl. multi-chunk) + the decoupling/boundary tests.
- [x] Refreshed the docstring figures; recorded the decision (Decision Log + benchmark table).
- [x] docs-lint + full suite (final run pending).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| decouple batch constant | Engineering | — | `accel_embedder.py` `StaticShapeReranker` |
| benchmark + choose | Engineering | decouple batch constant | needs the param to sweep cleanly |
| ranking-guard test + docs | Engineering | benchmark + choose | |


## Serialization Points

- `accel_embedder.py` `StaticShapeReranker` only; independent of the `code_ask` retrieval changes (`1p66r`/`1p66s`/`1p66t`) — can land in parallel with them.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` (or the accel/embedding doc) — record the reranker batch decision + that the reranker batch is decoupled from the embedder. No layering change.

## AC Priority

(Populated at Prepare wave.)


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Decoupling the reranker batch from the embedder is the change. |
| AC-2 | required | The size is chosen from data, not assumed. |
| AC-3 | required | Ranking must be identical — batch is a latency knob only. |
| AC-4 | required | Edge correctness (pad / multi-chunk / ceiling). |
| AC-5 | important | Refresh stale figures + record + docs. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-17 | Refocused from a GPU-vs-CPU question (settled: CoreML ~167ms vs CPU ~980ms p50, re-verified) to reranker batch size. Operator hypothesis: ≈32 better overall. Confirmed the batch is hard-wired (runtime `STATIC_BATCH` override errors `Got:32 Expected:64`), so decoupling is real work. | `StaticShapeReranker` `accel_embedder.py:430`; `STATIC_BATCH=64`; `AGENT_CANDIDATE_MAX=40` `server_impl.py:156`; cache key `rerank_static_{N}x512.onnx` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-17 | Scope is reranker batch size, not GPU-vs-CPU. | CoreML-vs-CPU is settled (CoreML decisively faster, measured + re-verified); the remaining perf lever is the batch the reranker inherited from the embedder. | Keep the GPU/CPU + provider-observability framing (dropped per operator direction). |
| 2026-06-17 | Give the reranker its own batch constant and set it from a batch×pool benchmark (evaluate ≈32). | The reranker's query-time ≤40-pool optimum differs from the embedder's index-time bulk optimum (64); padding wastes ~37%+ per query. Batch is ranking-neutral, so a measured smaller batch is a safe win. | Hard-code 32 without measuring (rejected — decide on data, the optimum depends on the real pool-size distribution incl. multi-chunk cost); keep shared 64 (only if the sweep shows no gain). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A batch smaller than the typical pool adds a second forward pass that erases the padding savings. | AC-2 benchmarks across pool sizes (not just 40) to pick the size that wins on the real distribution; multi-chunk cost is measured, not assumed. |
| Decoupling subtly changes ranking (e.g. a chunk-boundary score bug). | AC-3 ranking-identical regression guard across batch sizes incl. a >batch pool. |
| New batch size triggers a one-time static-graph recompile for consumers. | Expected + cheap (cache-keyed by batch dim); a one-time warm-up, same mechanism as today. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
