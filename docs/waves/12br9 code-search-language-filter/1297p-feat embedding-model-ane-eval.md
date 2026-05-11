# Embedding Model Evaluation and ANE Acceleration

Change ID: `1297p-feat embedding-model-ane-eval`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-08
Wave: `12br9 code-search-language-filter`

## Rationale

Wavefoundry currently uses `BAAI/bge-small-en-v1.5` (ONNX INT8) for both docs and code embeddings. It works, but two specific signals motivate revisiting model choice and acceleration path:

**1. The 512-token truncation is invisible.** Markdown sections can exceed 512 tokens; Python AST chunks for long functions also exceed it. The current model silently truncates without warning. Long-context candidates (`nomic-embed-text-v1.5`, `jina-embeddings-v2-small-en`) handle 8192 tokens but were 3–24× slower in initial testing — eliminating jina, leaving nomic as a real candidate if quantization works.

**2. Apple Silicon is not being used.** The benchmark in this session showed CoreML provider via ONNX Runtime is statistically indistinguishable from CPU (1.36s vs 1.38s) because INT8 ONNX ops largely fall back to CPU rather than dispatch to the Neural Engine. The ANE prefers FP16 or Apple's palettized quantization in native Core ML format. The hardware capability is sitting idle; the question is whether the engineering cost to use it is justified.

**3. The model is not trained on code.** `bge-small-en-v1.5` is a general-purpose English text embedding model. It treats TypeScript, Python, and shell scripts as token sequences with no understanding of code semantics — function signatures, type relationships, call patterns, or language-specific idioms. A query like "handle authentication errors and return 403" should match a Lambda authorizer handler, but the model has no structural knowledge of what a 403 or a handler means. This compounds the language filter bug fixed in this session: even with filtering working correctly, semantic code search quality is fundamentally limited by the model. Code-specific models (`jinaai/jina-embeddings-v2-base-code`, `microsoft/codebert-base`) are explicitly trained on source code across multiple languages including TypeScript, and are expected to return materially better results for code-intent queries.

The naive answer (just convert the model to Core ML) skips three questions: (a) is `bge-small` the right model in the first place, or would a different model be a better target for conversion? (b) should docs and code use separate models? (c) what is the actual workload-weighted speedup, given that incremental indexing — the dominant operation — is already sub-second?

This plan establishes a measurement-driven decision before code is written. The output is a documented choice across three axes (model family, format, acceleration path) with reproducible benchmarks and a quality-parity gate.

## Requirements

1. The evaluation must measure three workloads explicitly, not just batched throughput:
  - **Incremental update**: 1–5 changed files, ~5–30 chunks, end-to-end including model load if cold.
  - **Full rebuild**: realistic project-scale corpus (≥1000 chunks), end-to-end.
  - **Query embedding**: single-query latency (P50, P95) — this is the user-facing tool-call critical path.
2. The evaluation must include a quality-parity check on a hand-curated retrieval ground-truth set drawn from this repository (≥20 query/expected-result pairs covering both code and docs).
3. The evaluation must report peak resident memory for each candidate, measured during full rebuild — OOM was a real failure mode and re-introducing it is unacceptable.
4. The evaluation must remain cross-platform: any chosen primary path must work on Linux x86_64 and Linux arm64, not only macOS arm64. Acceleration on Apple Silicon is a layered optimization, not a replacement.
5. Candidate matrix must include at minimum:
  - `BAAI/bge-small-en-v1.5` ONNX INT8 (current baseline)
  - `BAAI/bge-small-en-v1.5` Core ML FP16 (converted via `coremltools`)
  - `BAAI/bge-small-en-v1.5` Core ML palettized (Apple LUT quantization)
  - `nomic-ai/nomic-embed-text-v1.5` Core ML FP16 — only candidate that addresses the 512-token issue
  - `jinaai/jina-embeddings-v2-base-code` — explicitly trained on code across 30 languages including TypeScript; primary candidate for improving code search quality
  - `BAAI/bge-base-en-v1.5` — same family as current baseline, larger, not code-specific; included as a quality upper-bound for general-purpose models
  - One static-embedding option (`model2vec` distillation of bge-small) as an upper-bound speed reference
  - The evaluation must consider whether a split-model architecture (one model for docs, one for code) is preferable to a single model for both; if split models are viable, the candidate matrix applies independently to each surface
6. Conversion artifacts must be deterministic and reproducible from a checked-in script — not a one-off notebook. The script must take the upstream model identifier and produce a `.mlpackage` with a recorded SHA-256 of the resulting weights.
7. The chosen Core ML path must coexist with the ONNX path: the indexer continues to load ONNX on non-Apple-Silicon hosts and on Apple Silicon hosts where the Core ML cache is absent. No platform must regress.
8. Any model swap (independent of acceleration) must trigger a full index rebuild via the existing `model_versions` change-detection in `meta.json`. Mixed-model indices are not allowed.
9. The decision criteria must be written down in this doc *before* the benchmark runs, not retrofitted afterward. Threshold values for go/no-go are stated explicitly under Decision Criteria.
10. The benchmark harness itself must be checked in under `.wavefoundry/framework/scripts/benchmarks/` so it is rerunnable when fastembed, coremltools, or hardware changes.

## Scope

**Problem statement:** Embedding model choice and acceleration path were inherited from the MCP foundation feature without explicit comparison. Latency data captured in this session reveals (a) ONNX CoreML provider gives no speedup for our quantized model, (b) the 512-token limit silently truncates real chunks, and (c) we have not measured query-time latency, which is the agent-facing critical path. Without a documented evaluation, future "should we change the model" questions have no anchor.

**In scope:**

- Workload definition and benchmark harness covering incremental, full-rebuild, and query workloads
- Quality-parity ground-truth set authored from this repository
- Conversion script `convert_to_coreml.py` for ONNX → Core ML `.mlpackage` (FP16 and palettized variants)
- Tokenizer parity test (Hugging Face `tokenizers` reproducing fastembed's token IDs exactly for the chosen model)
- Indexer integration: format detection (`onnx` vs `coreml`), provider auto-selection, opt-in conversion command in `setup_index.py`
- `meta.json` extension to record format (`onnx`/`coreml`) alongside model name, so a Core ML cache going stale forces a rebuild
- Tests covering: format detection, conversion-script idempotency, tokenizer parity, fallback to ONNX when `.mlpackage` absent, model-version change triggers rebuild

**Out of scope:**

- MLX-native runtime — fails the cross-platform requirement and is not required to use the ANE
- Re-training or distilling new models — only off-the-shelf candidates considered
- GPU-accelerated indexing on Linux/Windows (CUDA path) — provider detection already routes correctly; explicit benchmarking deferred until we have a CUDA host to measure on
- Rebuilding the framework distribution index (`.wavefoundry/framework/index/`) in Core ML format — that index is consumed read-only and the format choice should match whatever the project-local indexer uses; covered transitively
- Replacing the embedding library entirely (e.g., switching off fastembed) — too large a blast radius for a model-choice decision

## Acceptance Criteria

- AC-1: A benchmark harness at `.wavefoundry/framework/scripts/benchmarks/embed_bench.py` runs each candidate against incremental/full/query workloads and emits a JSON report with P50, P95, peak RSS, and quality scores.
- AC-2: A retrieval ground-truth set at `.wavefoundry/framework/scripts/benchmarks/retrieval_eval.json` with ≥30 (query, expected_paths) entries: ≥15 code-intent queries (e.g. "function that parses wave IDs", "error handling for missing index") and ≥10 docs-intent queries, plus ≥5 cross-cutting queries that should match both. The code-intent set is the primary quality gate for code-specific model candidates.
- AC-3: A conversion script at `.wavefoundry/framework/scripts/convert_to_coreml.py` produces a `.mlpackage` from a fastembed-supported model name, deterministically, with conversion logs and weight SHA-256.
- AC-4: Tokenizer parity test confirms the standalone `tokenizers` pipeline emits identical token IDs to fastembed's internal tokenizer for ≥100 sample inputs spanning English prose, code, and edge cases (long inputs, unicode, code with `<` `>` `&`).
- AC-5: A decision document at `docs/architecture/decisions/12dzj-adr embedding-model-and-format.md` captures the chosen model, format, conversion provenance, measured numbers, and explicit rejection reasons for non-chosen candidates.
- AC-6: If Core ML path is adopted: `_get_embedder()` selects format based on cache presence + platform; existing tests still pass; new tests cover format selection logic.
- AC-7: `meta.json` records `format` alongside `model_name` so a model or format change forces a full rebuild via the existing `model_versions` mechanism.
- AC-8: Full-rebuild latency on this repository's corpus does not regress on Linux CI runners (which lack ANE); this is the cross-platform safety check.
- AC-9: Quality regression vs. baseline `bge-small-en-v1.5 ONNX` is ≤5% on top-3 retrieval accuracy; if any candidate violates this, it is rejected even if faster.
- AC-10: Documentation updated: `AGENTS.md` MCP Server section, `docs/architecture/data-and-control-flow.md` Path 5 (Semantic Index Build), and `docs/contributing/build-and-verification.md` to include the conversion command and platform behavior.

## Decision Criteria

These thresholds are fixed before measurement. The benchmark report mechanically produces a recommendation by applying them.


| Criterion                                | Threshold                                            | Action if violated                                |
| ---------------------------------------- | ---------------------------------------------------- | ------------------------------------------------- |
| Quality regression (top-3 retrieval, all queries) | ≤5% vs baseline                             | Reject candidate                                  |
| Code-intent retrieval improvement        | Code-specific models must show ≥15% improvement over baseline on the code-intent subset to justify the switch | Prefer bge-base or stay on bge-small |
| Full-rebuild speedup on Apple Silicon    | ≥3× vs current ONNX path to justify Core ML adoption | Stay on ONNX                                      |
| Query embedding speedup on Apple Silicon | ≥5× to justify warmed-model resident process         | Skip warm-process work                            |
| Cross-platform regression                | 0% on Linux/CI                                       | Block adoption regardless of mac speedup          |
| Peak memory growth                       | ≤2× baseline                                         | Reject candidate                                  |
| 512-token truncation rate on this corpus | If <2% of chunks exceed 512 tokens                   | Long-context model is not justified for this repo |


If no candidate meets the speedup threshold *and* quality gate, the recommendation is to **stay on the current model and current path** and revisit when fastembed or coremltools materially change.

## Tasks

**Phase 1 — Methodology (no code changes to runtime):**

- [x] Author retrieval ground-truth set (32 query/expected pairs: 17 code-intent, 10 docs-intent, 5 cross-cutting).
- [x] Build benchmark harness at `.wavefoundry/framework/scripts/benchmarks/embed_bench.py`.
- [x] Measure baseline (`bge-small-en-v1.5` ONNX INT8): 81.2% overall, 88.2% code, 15 chunks/s, 85s full rebuild.
- [x] Compute 512-token truncation rate: 1.7% — long-context model not justified.

**Phase 2 — Measurement (Core ML path eliminated; ONNX candidates only):**

- [x] Investigated CoreML EP: proven no-op for INT8 ONNX (same perf as CPU); FP32 models (nomic, gte-base) ran 2–3× *slower* with CoreML due to ANE/CPU fragmentation. CoreML EP removed from `_onnx_providers()`.
- [x] Discovered padding waste as real throughput bottleneck: naive batching 15 chunks/s, sorted batching 36 chunks/s (2.4× improvement).
- [x] Fixed `_embed_texts` to sort globally and pass `batch_size=256` explicitly; fixed `_embed_chunks` outer loop that was batching at 16/64 (defeating global sort).
- [x] Fixed benchmark harness to reuse corpus vectors from full rebuild for retrieval quality (eliminated second full embed pass).
- [x] Measured `bge-base-en-v1.5`: 90.6% overall, 100% code, 90% docs, 280s full rebuild, 11.1 chunks/s.
- [x] Evaluated jina-v2-base-code (no INT8 fastembed export, FP32 too slow), nomic-embed-text-v1.5-Q (fastembed registry broken — quantized file absent from HF snapshot), nomic-embed-code (28GB 7B model, disqualified). All eliminated.

**Phase 3 — Decision and integration:**

- [x] Decision: adopt `bge-base-en-v1.5` for both DOCS_MODEL and CODE_MODEL.
- [x] Updated `DOCS_MODEL` and `CODE_MODEL` constants in `indexer.py`.
- [x] Updated regression test constants (`_EXPECTED_DOCS_MODEL`, `_EXPECTED_EMBEDDING_DIM`) in `test_server_tools.py`.
- [x] Author `docs/architecture/decisions/12dzj-adr embedding-model-and-format.md` ADR.
- [x] Update architecture docs that name `bge-small-en-v1.5` (current-state.md, data-and-control-flow.md, search-architecture.md, embedding-model.md).
- [x] Rebuild index (required: bge-base produces 768d vectors vs bge-small's 384d; indexer model-change detection will force full rebuild).

## Agent Execution Graph


| Workstream          | Owner       | Depends On                                         | Notes                                                       |
| ------------------- | ----------- | -------------------------------------------------- | ----------------------------------------------------------- |
| ground-truth-set    | Engineering | —                                                  | Hand-curated; can run independently of any code             |
| bench-harness       | Engineering | ground-truth-set                                   | Pure measurement; no runtime changes                        |
| coreml-conversion   | Engineering | —                                                  | Self-contained; outputs `.mlpackage` artifacts              |
| tokenizer-parity    | Engineering | coreml-conversion                                  | Validates conversion before integration                     |
| measurement-pass    | Engineering | bench-harness, coreml-conversion, tokenizer-parity | Generates the report that feeds the decision                |
| decision-doc        | Engineering | measurement-pass                                   | Mechanical from the report + criteria                       |
| indexer-integration | Engineering | decision-doc                                       | Conditional: only runs if Core ML path is chosen            |
| docs-update         | Engineering | indexer-integration OR decision-doc                | If "no change", docs note the decision and harness location |


## Serialization Points

- `_get_embedder()` in `indexer.py` is a single-author surface for the integration phase; integration changes block other indexer work until merged.
- `meta.json` schema change requires a synchronized update of every reader/writer (`indexer.py`, `server.py`); cannot land piecewise.
- Adding a benchmark harness directory under `.wavefoundry/framework/scripts/benchmarks/` may overlap with the build_pack.py exclusion list; verify benchmarks are excluded from the framework distribution zip.

## Affected Architecture Docs

- `docs/architecture/current-state.md` — embedding model is named in the MCP topology; will need an update if the model or format changes
- `docs/architecture/data-and-control-flow.md` Path 5 (Semantic Index Build) — current text names `BAAI/bge-small-en-v1.5`; would need to reflect format detection if Core ML is adopted
- `docs/architecture/decisions/12dzj-adr embedding-model-and-format.md` — new ADR (does not exist yet); records the decision, even if the decision is "stay"
- `docs/contributing/build-and-verification.md` — would need to document the conversion command if Core ML is adopted

## AC Priority

(Populated at Prepare wave.)


| AC    | Priority       | Rationale |
| ----- | -------------- | --------- |
| AC-1  | required       | Benchmark harness is the foundation — nothing else can proceed without reproducible numbers |
| AC-2  | required       | Ground-truth set is the quality gate; code-intent queries are the primary motivation for this evaluation |
| AC-3  | important      | Core ML conversion is needed for the Apple Silicon path but not for model quality evaluation |
| AC-4  | important      | Tokenizer parity is required before any Core ML adoption; not needed for model-only decision |
| AC-5  | required       | Decision must be documented even if the decision is "stay" — the ADR is the deliverable |
| AC-6  | not-this-scope | Runtime integration only happens if decision criteria are met; deferred to Phase 3 |
| AC-7  | not-this-scope | meta.json format field only needed if Core ML is adopted; deferred to Phase 3 |
| AC-8  | required       | Cross-platform safety check — Linux regression would block adoption |
| AC-9  | required       | Quality regression gate — must be enforced regardless of speed gains |
| AC-10 | important      | Docs updates needed but not blocking for the measurement and decision phases |


## Progress Log


| Date       | Update                                                                                                                                                                                                                                                                                        | Evidence                 |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 2026-04-29 | Plan authored. Baseline numbers captured this session: bge-small ONNX INT8 1.36s for 64×150tok docs, 4.09s for 64×450tok docs; CoreML EP via ONNX statistically equal to CPU; nomic-Q registry entry broken (missing file in HF snapshot); jina-v2-small 24.5s for 64×450tok (disqualifying). | This conversation thread |
| 2026-05-02 | Code search quality identified as a third motivation. `bge-small` has no code-specific training; semantic code search queries against TypeScript/Python return poor results structurally, not just due to the language filter bug fixed this session. Added `jinaai/jina-embeddings-v2-base-code` and `bge-base` to candidate matrix; expanded ground-truth set requirement to skew toward code-intent queries; added code-intent retrieval improvement threshold (≥15%) to decision criteria; added split-model architecture as an evaluation question. | Language filter bug fix session |
| 2026-05-03 | Phase 1 complete: ground-truth set (32 queries) and benchmark harness authored. Baseline measured: bge-small 81.2% overall / 88.2% code / 85s rebuild. CoreML EP investigated thoroughly: proven no-op for INT8 (ANE can't run INT8 ops), 2–3× slower for FP32 (ANE/CPU fragmentation). CoreML EP removed from `_onnx_providers()`. Padding waste identified as real bottleneck: sorted batching gives 2.4× throughput improvement; inner batch loop (16/64) was defeating global sort — fixed. Benchmark harness fixed to reuse corpus vectors. bge-base measured: 90.6% / 100% code / 90% docs / 280s. jina FP32 too slow (no INT8 export), nomic-Q registry broken, nomic-embed-code disqualified (28GB). Decision: adopt `bge-base-en-v1.5` for both models. Constants updated, tests updated. | bench_report_final.json |


## Decision Log


| Date       | Decision                                                                                              | Reason                                                                                                                             | Alternatives                                                                                                                                                                  |
| ---------- | ----------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-29 | Defer model swap until benchmark methodology is in place                                              | Initial ad-hoc benchmarks are not a sufficient basis for a model decision; need ground-truth retrieval set and consistent harness. | Swap to `nomic-Q` immediately (rejected: registry broken, no quality data); ship Core ML conversion now (rejected: no proof it actually beats current path workload-weighted) |
| 2026-04-29 | Cross-platform constraint: Core ML is an optional acceleration layer, never a replacement             | Wavefoundry must work on Linux x86_64 and arm64. Apple-only paths cannot be the primary code path.                                 | Make MLX/Core ML the default and ship a separate Linux build (rejected: doubles the maintenance surface)                                                                      |
| 2026-04-29 | Static embeddings (`model2vec` etc.) included as upper-bound speed reference, not a primary candidate | Likely too lossy for semantic queries against prose docs, but useful as a sanity ceiling for what's achievable.                    | Exclude entirely (rejected: leaves a question unanswered)                                                                                                                     |
| 2026-05-02 | Code-specific models added to candidate matrix; split-model architecture added as open evaluation question | `bge-small` has no code training; semantic code search quality is a known gap independent of acceleration. `jina-v2-base-code` is the primary candidate for code; `bge-base` added as a general-purpose upper bound. Split-model architecture (separate models for docs vs code) not decided either way — the harness will inform it. | Add code-specific model immediately without measurement (rejected: need the harness to make a defensible decision) |
| 2026-05-03 | Adopt `bge-base-en-v1.5` for both DOCS_MODEL and CODE_MODEL | Quality improvement is decisive: 100% code retrieval accuracy vs 88.2% for bge-small; 90.6% overall vs 81.2%. Rebuild time 280s vs 85s is acceptable — full rebuilds are cold-start only; incremental updates (633ms/5 chunks) remain fast. Split-model architecture not adopted: bge-base already achieves 90% docs accuracy, comparable to its code performance, so a separate docs model adds complexity without benefit. Core ML path deferred: requires coremltools + torch install, custom inference path, tokenizer parity validation — significant effort with uncertain ANE utilization given dynamic shapes. | Stay on bge-small (rejected: 12pp code quality gap is significant); jina-v2-base-code as code model (rejected: no INT8 fastembed export, FP32 too slow); Core ML conversion (rejected: prerequisite complexity exceeds benefit given CPU performance is already acceptable) |


## Risks


| Risk                                                                                                                          | Mitigation                                                                                                                                       |
| ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `coremltools` conversion of attention/transformer ops can fail or silently produce wrong outputs on certain ONNX op patterns. | Tokenizer-parity test plus a numeric-similarity check (cosine ≥ 0.999 between ONNX and Core ML embeddings on a held-out set) before adopting.    |
| Tokenizer parity is hard: fastembed bundles tokenizer config we'd need to extract precisely.                                  | Extract `tokenizer.json` from the same HF snapshot fastembed uses; assert byte-identical token-ID outputs across ≥100 inputs before integration. |
| Apple `coremltools` and `fastembed` evolve independently; conversion script can break on version bumps.                       | Pin both versions in the conversion script; record versions + weight SHA-256 in conversion log; CI re-runs conversion on dependency bump.        |
| Quality regression invisible without a real eval set: synthetic benchmarks (MTEB) don't match wavefoundry's actual queries.   | Hand-curated retrieval set drawn from this repo's actual content is the gating criterion, not MTEB.                                              |
| Core ML cache file format may change between Apple OS versions, invalidating existing `.mlpackage` artifacts.                 | Record macOS major version + coremltools version in `meta.json`; on mismatch, treat the cache as stale and trigger reconversion.                 |
| Adopting Core ML masks the underlying issue if the chosen model is wrong for the workload.                                    | The decision-criteria table forces a comparison against the baseline; if Core ML doesn't deliver ≥3× full-rebuild speedup, we don't take it on.  |
| Benchmarks measured only on this 200-file repo may not generalize to large target repos.                                      | Harness accepts a `--corpus-path` argument so it can be re-run against a target repo before deciding to enable Core ML there.                    |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.