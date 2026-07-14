# 12dzj-adr — Embedding Model: BAAI/bge-base-en-v1.5 via fastembed ONNX INT8

Owner: Engineering
Status: accepted
Last verified: 2026-07-14

## Context

Wavefoundry uses a local semantic search index to help agents navigate docs and code without knowing exact filenames or keywords. The embedding model is the core dependency for this: it produces the vectors stored at index build time and the query vectors at search time.

The original model was `BAAI/bge-small-en-v1.5` (384d, ONNX INT8), chosen pragmatically when the MCP foundation was built. Two signals prompted a re-evaluation in wave `12br9`:

1. **Code search quality.** `bge-small` is a general-purpose English text model with no code-specific training. Measured retrieval accuracy on a 32-query ground-truth set drawn from this repository was 88.2% code-intent top-3 accuracy — structurally limited by the model's lack of code semantics, not by the index or the query path.

2. **Apple Silicon throughput.** Benchmarking showed that `CoreMLExecutionProvider` via ONNX Runtime is a no-op for INT8 quantized ONNX models on Apple Silicon — the ANE cannot execute INT8 ops and silently falls back to CPU. FP32 models ran 2–3× *slower* with CoreML EP due to layer-boundary fragmentation between ANE and CPU. The real throughput bottleneck was padding waste in ONNX batching, not model choice or provider.

A benchmark harness (`embed_bench.py`) and 32-query retrieval ground truth set (`retrieval_eval.json`) were produced before any code changes, with decision thresholds fixed in advance.

## Decision

Use `BAAI/bge-base-en-v1.5` (768d, ONNX INT8 via fastembed) for both `DOCS_MODEL` and `CODE_MODEL`. The CoreML execution provider is removed from `_onnx_providers()`. Throughput is improved by sorting input texts by length before batching (eliminates padding waste) rather than by switching provider or model format.

## Consequences

**Positive:**
- Code retrieval accuracy improved from 88.2% to 100% on the ground-truth set (top-3, code-intent queries). Overall accuracy improved from 81.2% to 90.6%.
- Docs accuracy improved from 80% to 90%.
- No split-model architecture required: bge-base achieves comparable accuracy on both docs and code, removing complexity.
- Sorted batching gives 2.4× throughput improvement over naive batching, independent of model choice. Incremental updates (5 chunks) take ~633ms.
- `local_files_only=True` and `HF_HUB_OFFLINE=1` guarantees remain fully intact — bge-base is a first-class fastembed offline model (`qdrant/bge-base-en-v1.5-onnx-q`).
- Cross-platform: ONNX INT8 runs on Linux x86_64, Linux arm64, and macOS arm64 without platform-specific code paths.

**Negative / tradeoffs:**
- Full rebuild time increased from ~85s (bge-small) to ~280s (bge-base) on this repository's ~3,100-chunk corpus. This only matters on first install or forced re-index; incremental updates are unaffected.
- Model cache size increased from ~67MB (bge-small INT8) to ~210MB (bge-base INT8).
- All existing indexes are invalidated by the dimension change (384d → 768d). The recorded `model_versions` (originally in `meta.json`; in the `index-state.sqlite` build state since wave 1sed7) detects this and forces a full rebuild automatically.
- CoreML acceleration path deferred. The native Core ML path (coremltools FP16 conversion to `.mlpackage`) was not adopted: it requires `coremltools` + `torch` + `transformers` as build-time dependencies, a custom inference path bypassing fastembed, and tokenizer parity validation. The engineering cost exceeds the benefit given that CPU performance after sorted batching is acceptable.

**Constraints imposed:**
- `DOCS_MODEL` and `CODE_MODEL` constants in `indexer.py` must remain `"BAAI/bge-base-en-v1.5"` unless a new ADR supersedes this one.
- `_EXPECTED_DOCS_MODEL` and `_EXPECTED_EMBEDDING_DIM` in `SemanticEmbeddingRegressionTests` are the single update point for a future model change — see `docs/architecture/embedding-model.md` for the upgrade checklist.
- Any future model change must go through the benchmark harness in `.wavefoundry/framework/scripts/benchmarks/` and produce retrieval accuracy ≥ this baseline before adoption.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| Stay on `BAAI/bge-small-en-v1.5` | 12pp code retrieval gap (88.2% → 100%) is significant; bge-small has no code-specific training and the gap is structural |
| `jinaai/jina-embeddings-v2-base-code` (code model) | No INT8 fastembed export exists; FP32 ONNX too slow (~0.8 chunks/s); fastembed offline compatibility unverified |
| `nomic-ai/nomic-embed-text-v1.5-Q` | fastembed registry broken — `model_quantized.onnx` absent from HF snapshot; cleared cache twice, same result |
| `nomic-ai/nomic-embed-code` | 28GB 7B-parameter model; disqualified on memory grounds |
| `BAAI/bge-small-en-v1.5` + CoreML FP16 via coremltools | Requires torch + transformers + coremltools as build deps; custom inference path needed; tokenizer parity nontrivial to validate; deferred, not rejected permanently |
| Split-model architecture (separate docs and code models) | bge-base achieves 90% docs and 100% code accuracy; adding a second model doubles index complexity and setup time for no measured benefit |
| `CoreMLExecutionProvider` via ONNX Runtime | Proven no-op for INT8 ONNX (ANE cannot run INT8 ops); 2–3× slower for FP32 ONNX (ANE/CPU fragmentation at layer boundaries) |

## References

- `docs/architecture/embedding-model.md` — current model rationale, regression test guide, upgrade checklist
- `.wavefoundry/framework/scripts/benchmarks/embed_bench.py` — benchmark harness
- `.wavefoundry/framework/scripts/benchmarks/retrieval_eval.json` — 32-query ground truth set
- Wave `12br9 code-search-language-filter` — the evaluation was conducted here
